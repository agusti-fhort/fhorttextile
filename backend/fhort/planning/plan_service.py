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
