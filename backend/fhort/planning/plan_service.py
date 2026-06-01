"""Sprint Backend B — orquestració dels endpoints de planificació sobre el motor
determinista (scheduler_service.schedule). Jubila la lògica per-model-en-sèrie de
fhort/tasks/services_h.py; CONSERVA PlanSnapshot (tasks) i el lookup Welford.

- compute_and_save: planifica un conjunt (filtre/campanya o tot el pendent) amb save=True,
  desa un PlanSnapshot i escriu planned_*/predicted_*.
- preview: simula una reposició (tasca + nova data inici) recalculant la cua del tècnic
  amb save=False → retorna l'impacte SENSE escriure res.
- apply: aplica una proposta acceptada → fixa la tasca moguda (planned_locked=True a la
  nova data) i desa el recàlcul de la cua (+ PlanSnapshot).
"""
import datetime as _dt

from django.db import transaction
from django.utils import timezone

from fhort.tasks.models import ModelTask, PlanSnapshot
from .calendar_service import add_working_minutes
from .scheduler_service import schedule, _now_naive, _to_naive, _to_aware


def _parse_naive(value):
    """ISO str o datetime → datetime NAÏF local (coherent amb el calendari)."""
    dt = value if isinstance(value, _dt.datetime) else _dt.datetime.fromisoformat(value)
    return _to_naive(dt) if dt.tzinfo is not None else dt


def _select_tasks(model_ids=None, campaign_filter=None):
    """Conjunt a planificar: ModelTask no-Done, filtrades per model_ids i/o campanya
    (temporada/any del Model). Sense filtre → tot el pendent."""
    qs = ModelTask.objects.exclude(status='Done')
    if model_ids:
        qs = qs.filter(model_id__in=model_ids)
    cf = campaign_filter or {}
    if cf.get('temporada'):
        qs = qs.filter(model__temporada=cf['temporada'])
    if cf.get('any'):
        qs = qs.filter(model__any=cf['any'])
    return qs


def _technician_queue(profile):
    """Cua de feina d'un tècnic: les seves ModelTask no-Done."""
    return (ModelTask.objects.filter(assignee=profile).exclude(status='Done')
            .select_related('model', 'task_type', 'assignee'))


def recompute_for_technicians(profile_ids, *, now=None):
    """Recalcula la cua SENCERA de cada tècnic afectat (totes les seves no-Done, com fa apply),
    NO només un model → evita solapaments amb la feina ja assignada del tècnic. Done intactes.
    `profile_ids`: iterable d'ids de UserProfile (es filtren els None i es deduplica)."""
    from fhort.accounts.models import UserProfile
    now = now or _now_naive()
    results = {}
    for pid in {p for p in profile_ids if p}:
        prof = UserProfile.objects.filter(pk=pid).first()
        if prof is not None:
            results[pid] = schedule(_technician_queue(prof), now=now, save=True)
    return results


def _save_snapshot(result, *, start_date, campaign_filter, computed_by, technician_count):
    """Desa la previsió com a PlanSnapshot immutable (conservat de l'Sprint H)."""
    return PlanSnapshot.objects.create(
        computed_by=computed_by, start_date=start_date,
        technician_count=technician_count,
        model_sequence=[int(mid) for mid in result['models'].keys()],
        campaign_filter=campaign_filter or {}, result=result)


@transaction.atomic
def compute_and_save(*, model_ids=None, campaign_filter=None, computed_by=None, now=None):
    """REFACTOR de plan/compute: planifica amb el motor determinista, escriu planned_*/
    predicted_* i desa un PlanSnapshot. Retorna {snapshot_id, result}."""
    now = now or _now_naive()
    qs = _select_tasks(model_ids, campaign_filter)
    technician_count = (qs.filter(assignee__isnull=False)
                          .values('assignee_id').distinct().count())
    result = schedule(qs, now=now, save=True)
    snap = _save_snapshot(result, start_date=now.date(), campaign_filter=campaign_filter,
                          computed_by=computed_by, technician_count=technician_count)
    return {'snapshot_id': snap.id, 'result': result}


def _pin_block(profile, task, new_start_naive):
    """Calcula la franja (start, end) naïf d'una tasca fixada a new_start (per la durada
    snapshot). Llança ValueError si la tasca no té estimació."""
    if task.estimated_minutes is None:
        raise ValueError('La tasca moguda no té estimació; no es pot reposicionar.')
    end_naive = add_working_minutes(profile, new_start_naive, task.estimated_minutes)
    return new_start_naive, end_naive


def preview(*, task_id, new_start, now=None):
    """Simula reposicionar la tasca `task_id` a `new_start`: recalcula la cua del seu tècnic
    amb save=False i retorna l'impacte (tasques que es mouen + dates noves + warnings) SENSE
    escriure res a la BD."""
    moved = ModelTask.objects.select_related('model', 'task_type', 'assignee').get(pk=task_id)
    if moved.assignee_id is None:
        raise ValueError('La tasca no té tècnic assignat.')
    profile = moved.assignee
    ns = _parse_naive(new_start)

    queue = list(_technician_queue(profile))
    if moved.id not in {t.id for t in queue}:   # tasca Done o fora: incloure-la igualment
        queue.append(moved)

    # Estat "abans" (naïf local) per detectar què es mou.
    before = {t.id: (_to_naive(t.planned_start).isoformat() if t.planned_start else None)
              for t in queue}

    # Fixar la tasca moguda en memòria (NO es desa): locked a la nova data.
    _, end_naive = _pin_block(profile, moved, ns)
    for t in queue:
        if t.id == moved.id:
            t.planned_locked = True
            t.planned_start = _to_aware(ns)
            t.planned_end = _to_aware(end_naive)

    result = schedule(queue, now=now, save=False)

    placed = {p['task_id']: p for p in result['placements']}
    impact = []
    for t in queue:
        new_start_iso = placed.get(t.id, {}).get('planned_start')
        if new_start_iso != before[t.id]:
            impact.append({'task_id': t.id, 'model': t.model.codi_intern,
                           'task_type': t.task_type.code,
                           'old_start': before[t.id], 'new_start': new_start_iso})
    return {'moved_task_id': moved.id, 'placements': result['placements'],
            'warnings': result['warnings'], 'impact': impact}


@transaction.atomic
def apply(*, task_id, new_start, computed_by=None, now=None):
    """Aplica una proposta acceptada: fixa la tasca moguda (planned_locked=True a new_start)
    i desa el recàlcul de la cua del tècnic (+ PlanSnapshot). Retorna {snapshot_id, result,
    locked_task_id}."""
    now = now or _now_naive()
    moved = ModelTask.objects.select_related('model', 'task_type', 'assignee').get(pk=task_id)
    if moved.assignee_id is None:
        raise ValueError('La tasca no té tècnic assignat.')
    profile = moved.assignee
    ns = _parse_naive(new_start)
    _, end_naive = _pin_block(profile, moved, ns)

    moved.planned_locked = True
    moved.planned_start = _to_aware(ns)
    moved.planned_end = _to_aware(end_naive)
    moved.save(update_fields=['planned_locked', 'planned_start', 'planned_end', 'updated_at'])

    qs = _technician_queue(profile)
    result = schedule(qs, now=now, save=True)
    snap = _save_snapshot(result, start_date=now.date(),
                          campaign_filter={'apply_task': task_id},
                          computed_by=computed_by, technician_count=1)
    return {'snapshot_id': snap.id, 'result': result, 'locked_task_id': moved.id}


@transaction.atomic
def assign_model(*, model_id, assignee_id, task_ids=None, now=None):
    """Assigna el tècnic `assignee_id` a les tasques no-Done del model (totes, o només `task_ids`)
    i recalcula la cua SENCERA de cada tècnic afectat (el nou + els que perdin tasques). Les Done
    NO es toquen. Retorna {assigned_count, technician_ids, results}.
    Llança ValueError si el tècnic no pot fer algun tipus de tasca (allow-list)."""
    from fhort.accounts.models import UserProfile
    from fhort.accounts.capabilities import get_allowed_task_types
    profile = UserProfile.objects.filter(pk=assignee_id).first()
    if profile is None:
        raise ValueError('Tècnic (assignee_id) no trobat en aquest tenant.')

    qs = (ModelTask.objects.filter(model_id=model_id).exclude(status='Done')
          .select_related('task_type', 'assignee'))
    if task_ids:
        qs = qs.filter(pk__in=task_ids)
    tasks = list(qs)
    if not tasks:
        raise ValueError('El model no té tasques no-Done per assignar.')

    # Allow-list: el tècnic ha de poder fer cada tipus (admin = bypass via get_allowed_task_types).
    allowed = get_allowed_task_types(profile.user)
    blocked = sorted({t.task_type.code for t in tasks if t.task_type.code not in allowed})
    if blocked:
        raise ValueError(f"El tècnic no té permès els tipus de tasca: {', '.join(blocked)}.")

    affected = {assignee_id}
    for t in tasks:
        if t.assignee_id:
            affected.add(t.assignee_id)   # el tècnic anterior també cal recalcular-lo
        t.assignee = profile
        t.save(update_fields=['assignee', 'updated_at'])

    results = recompute_for_technicians(affected, now=now)
    return {'assigned_count': len(tasks), 'technician_ids': sorted(affected),
            'results': results}


@transaction.atomic
def unassign_model(*, model_id, now=None):
    """Treu el tècnic i buida planned_* de TOTES les tasques no-Done assignades del model
    (endpoint de servidor: planned_* són read-only al serializer). Recalcula la cua dels tècnics
    que quedin afectats i neteja Model.predicted_*. Les Done NO es toquen.
    Retorna {unassigned_count, technician_ids, results}."""
    from fhort.models_app.models import Model
    qs = (ModelTask.objects.filter(model_id=model_id).exclude(status='Done')
          .filter(assignee__isnull=False))
    affected = set(qs.values_list('assignee_id', flat=True))
    count = qs.update(assignee=None, planned_start=None, planned_end=None,
                      planned_locked=False)
    # El model torna a Pendents: sense tasques no-Done planificades → neteja la previsió del model.
    Model.objects.filter(pk=model_id).update(predicted_start=None, predicted_end=None)
    results = recompute_for_technicians(affected, now=now)
    return {'unassigned_count': count, 'technician_ids': sorted(affected), 'results': results}
