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
from .calendar_service import add_working_minutes, subtract_working_minutes
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
    `profile_ids`: iterable d'ids de UserProfile (es filtren els None i es deduplica).

    Re-resolució (decisió A, diagnosi §9.5): abans de planificar, refresca el snapshot de durada
    (estimated_minutes) de les tasques MOVIBLES des de la cascada en viu (lookup_estimated_minutes),
    perquè el recàlcul reflecteixi dades de temps que han madurat. NO toca les planned_locked
    (punts fixos) ni les Done (immutables; ja excloses de la cua)."""
    from fhort.accounts.models import UserProfile
    from fhort.tasks.services_g import lookup_estimated_minutes
    now = now or _now_naive()
    results = {}
    for pid in {p for p in profile_ids if p}:
        prof = UserProfile.objects.filter(pk=pid).first()
        if prof is None:
            continue
        queue = list(_technician_queue(prof))
        for t in queue:
            if t.planned_locked:
                continue   # punt fix: la durada snapshot es respecta tal qual
            if t.status != 'Pending':
                continue   # NOMÉS les no començades re-resolen; InProgress/Paused conserven el
                           # snapshot (Done ja excloses de la cua). Cap canvi espontani d'estimació.
            fresh = lookup_estimated_minutes(t.model, t.task_type)
            if fresh is not None and fresh != t.estimated_minutes:
                # No clobberem mai un valor amb None (peça 4: cap tasca NULL després de planificar).
                t.estimated_minutes = fresh
                t.save(update_fields=['estimated_minutes', 'updated_at'])
        results[pid] = schedule(queue, now=now, save=True)
    return results


def cleanup_queue_order(profile_ids, model_ids):
    """Esborra files TechnicianQueueOrder(profile, model) on el profile ja NO tingui cap ModelTask
    no-Done d'aquell model (el model ha sortit de la seva cua). Idempotent. Es crida en desassignar
    un model i en reassignar tasques entre tècnics."""
    from .models import TechnicianQueueOrder
    pids = {p for p in profile_ids if p}
    mids = {m for m in model_ids if m}
    if not pids or not mids:
        return
    for pid in pids:
        for mid in mids:
            still = (ModelTask.objects.filter(assignee_id=pid, model_id=mid)
                     .exclude(status='Done').exists())
            if not still:
                TechnicianQueueOrder.objects.filter(profile_id=pid, model_id=mid).delete()


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
    if not task.estimated_minutes or task.estimated_minutes <= 0:
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


ASSIGN_BATCH_CHUNK = 100


def assign_batch(*, model_ids, assignacions, actor=None, now=None):
    """Wizard multi-assignació: aplica `assignacions` (task_type × persona × data opcional)
    a cada model de `model_ids`. La tasca es CREA si no existeix (via canònica de
    define_model_tasks_view) i neix amb l'assignee. Recompute ÚNIC al final per a tots els
    tècnics afectats (nous + desplaçats).

    `model_ids`: llista explícita O queryset lazy d'ids (p.ex. `.values_list('id', flat=True)`
      d'un ModelFilter re-avaluat server-side, C2). Es materialitza a ints (barat fins i tot
      per a milers) i s'itera per LOTS de ASSIGN_BATCH_CHUNK amb **atomicitat per lot** (fora
      la transacció monolítica única) — un lot que peti no arrossega els ja aplicats. El
      recompute de la cua per tècnic és UN SOL COP al final (preservat de l'original).

    assignacions: [{task_type_code, assignee_profile_id, planned_start?, planned_end?}].
      - Mai planned_start I planned_end alhora (ValueError → 400 lot sencer).
      - Només start → planned_end = add_working_minutes; només end → planned_start =
        subtract_working_minutes; en ambdós casos planned_locked=True. Sense data → cua.
      - Sense estimated_minutes (o 0) amb data → warning, assigna sense dates (cua).
    Retorna {fets, creats, reassignats, omesos, warnings, resultats}."""
    from fhort.accounts.models import UserProfile
    from fhort.accounts.capabilities import get_allowed_task_types
    from fhort.tasks.models import TaskType
    from fhort.tasks.services_g import lookup_estimated_minutes
    from fhort.models_app.models import Model
    now = now or _now_naive()

    # Pas 0 — validació dura (abans de tocar BD).
    for a in assignacions:
        if a.get('planned_start') and a.get('planned_end'):
            raise ValueError('Una assignació no pot portar planned_start i planned_end alhora.')

    # Pas 1 — resolució d'entitats en bloc (sense N+1). Els task_type/perfil són fitats per
    # `assignacions` (no per model_ids) → una sola resolució per a tot el lot.
    tt_by_code = {tt.code: tt for tt in
                  TaskType.objects.filter(code__in={a['task_type_code'] for a in assignacions})}
    prof_by_id = {p.id: p for p in
                  UserProfile.objects.filter(pk__in={a['assignee_profile_id'] for a in assignacions})
                  .select_related('user')}
    # Materialitza els ids AQUÍ (re-avaluació del queryset filtrat al moment d'executar quan
    # `model_ids` és un QS lazy). Materialitzar ints és barat; NO es carreguen objectes Model.
    all_ids = list(model_ids)

    fets = creats = 0
    reassignats, omesos, warnings, touched = [], [], [], []
    needs_estimate, seen_needs = [], set()
    affected = set()

    # Pas 2 — per LOTS: cada lot carrega només els seus objectes Model i s'aplica dins la seva
    # PRÒPIA transacció. Fora la transacció monolítica única sobre milers de models.
    def _apply_one(mid, models_by_id):
        nonlocal fets, creats
        model = models_by_id.get(mid)
        if model is None:
            omesos.append({'model_id': mid, 'task_type_code': None, 'motiu': 'model no trobat'})
            return
        for a in assignacions:
            code = a['task_type_code']
            tt = tt_by_code.get(code)
            profile = prof_by_id.get(a['assignee_profile_id'])
            if tt is None:
                omesos.append({'model_id': mid, 'task_type_code': code, 'motiu': 'task_type desconegut'})
                continue
            if profile is None:
                omesos.append({'model_id': mid, 'task_type_code': code, 'motiu': 'perfil no trobat'})
                continue
            # a) allow-list (bypass admin per construcció a get_allowed_task_types).
            if code not in get_allowed_task_types(profile.user):
                omesos.append({'model_id': mid, 'task_type_code': code, 'motiu': 'permís negat'})
                continue
            # b) buscar / crear (via canònica: la prevista de recepta).
            mt = (ModelTask.objects.filter(model_id=mid, task_type=tt, origen='prevista')
                  .select_related('assignee__user').first())
            if mt is not None and mt.status == 'Done':
                omesos.append({'model_id': mid, 'task_type_code': code, 'motiu': 'Done immutable'})
                continue
            old_assignee = None
            if mt is None:
                order = ModelTask.objects.filter(model_id=mid).count()
                est = lookup_estimated_minutes(model, tt)
                if est is None:
                    # "O té valor o demana": no creem una tasca amb estimated_minutes NULL.
                    # Es recull per a la captura conscient del PM (llavor CAPTURA) i es reintenta.
                    if code not in seen_needs:
                        seen_needs.add(code)
                        needs_estimate.append({'task_code': code, 'fase': tt.fase})
                    omesos.append({'model_id': mid, 'task_type_code': code, 'motiu': 'needs_estimate'})
                    continue
                mt = ModelTask.objects.create(model_id=mid, task_type=tt, order=order,
                                              status='Pending', origen='prevista',
                                              estimated_minutes=est)
                creats += 1
            elif mt.assignee_id and mt.assignee_id != profile.id:
                old_assignee = mt.assignee   # tècnic anterior desplaçat
            # c) assignar.
            mt.assignee = profile
            if old_assignee is not None:
                reassignats.append({'model_id': mid, 'task_type_code': code,
                                    'abans_nom': (old_assignee.user.get_full_name()
                                                  or old_assignee.user.get_username())})
                affected.add(old_assignee.id)
            # d) dates.
            ps_raw, pe_raw = a.get('planned_start'), a.get('planned_end')
            est_min = mt.estimated_minutes
            if (ps_raw or pe_raw) and not est_min:
                warnings.append(f'{model.codi_intern}·{code}: sense estimació de temps; '
                                f'assignat sense dates (va a cua).')
                mt.planned_locked = False
            elif ps_raw:
                start_naive = _parse_naive(ps_raw)
                end_naive = add_working_minutes(profile, start_naive, est_min)
                mt.planned_start, mt.planned_end = _to_aware(start_naive), _to_aware(end_naive)
                mt.planned_locked = True
            elif pe_raw:
                end_naive = _parse_naive(pe_raw)
                start_naive = subtract_working_minutes(profile, end_naive, est_min)
                mt.planned_start, mt.planned_end = _to_aware(start_naive), _to_aware(end_naive)
                mt.planned_locked = True
            else:
                mt.planned_locked = False   # cua: recompute el col·loca com a movible
            # e) col·lisió locked (warning, no bloqueja) — el scheduler NO ho valida.
            if mt.planned_locked:
                ns, ne = _to_naive(mt.planned_start), _to_naive(mt.planned_end)
                others = (ModelTask.objects.filter(assignee=profile, planned_locked=True)
                          .exclude(pk=mt.pk).exclude(status='Done')
                          .select_related('task_type', 'model'))
                for o in others:
                    if not (o.planned_start and o.planned_end):
                        continue
                    os_, oe = _to_naive(o.planned_start), _to_naive(o.planned_end)
                    if ns < oe and os_ < ne:   # [ns,ne) ∩ [os_,oe) ≠ ∅
                        warnings.append(f'Solapament: {model.codi_intern}·{code} xoca amb '
                                        f'{o.model.codi_intern}·{o.task_type.code}.')
            # f) desar.
            mt.save(update_fields=['assignee', 'planned_start', 'planned_end',
                                   'planned_locked', 'updated_at'])
            affected.add(profile.id)
            touched.append((mid, code, profile.id, mt.id))
            fets += 1

    for start in range(0, len(all_ids), ASSIGN_BATCH_CHUNK):
        chunk = all_ids[start:start + ASSIGN_BATCH_CHUNK]
        models_by_id = {m.id: m for m in Model.objects.filter(pk__in=chunk)}
        with transaction.atomic():   # atomicitat PER LOT
            for mid in chunk:
                _apply_one(mid, models_by_id)

    # Pas 3 — neteja d'ordre manual + recompute ÚNIC dels afectats (una sola transacció al
    # final, sobre els tècnics tocats — no per model). Es neteja només els models realment
    # assignats (touched), no tot el conjunt d'entrada.
    touched_model_ids = {t[0] for t in touched}
    with transaction.atomic():
        cleanup_queue_order(affected, touched_model_ids)
        rec = recompute_for_technicians(affected, now=now)
    # Agrega el needs_estimate del scheduler (tasques EXISTENTS que segueixen sense estimació,
    # p.ex. creades abans per open-task) al de creació, deduplicant per task_code.
    for r in (rec or {}).values():
        for ne in r.get('needs_estimate', []):
            if ne['task_code'] not in seen_needs:
                seen_needs.add(ne['task_code'])
                needs_estimate.append({'task_code': ne['task_code'], 'fase': ne['fase']})

    # Pas 4 — rellegir planned_* finals (post-recompute) i calcular en_risc.
    fresh = {m.id: m for m in
             ModelTask.objects.filter(pk__in=[t[3] for t in touched]).select_related('model')}
    resultats = []
    for (mid, code, pid, mt_id) in touched:
        mt = fresh.get(mt_id)
        if mt is None:
            continue
        data_obj = mt.model.data_objectiu
        end_local = _to_naive(mt.planned_end).date() if mt.planned_end else None
        en_risc = bool(end_local and data_obj and end_local > data_obj)
        resultats.append({
            'model_id': mid, 'task_type_code': code, 'assignee_profile_id': pid,
            'planned_start': timezone.localtime(mt.planned_start).isoformat() if mt.planned_start else None,
            'planned_end': timezone.localtime(mt.planned_end).isoformat() if mt.planned_end else None,
            'en_risc': en_risc,
        })

    return {'fets': fets, 'creats': creats, 'reassignats': reassignats,
            'omesos': omesos, 'warnings': warnings, 'resultats': resultats,
            'needs_estimate': needs_estimate}


@transaction.atomic
def cleanup_after_pending_delete(*, model_id, assignee_id, now=None):
    """C3 — cua després d'ESBORRAR una ModelTask Pending assignada/planificada. Replica la
    cascada d'unassign_model REUTILITZANT les mateixes funcions (no les duplica):
      - cleanup_queue_order: treu TechnicianQueueOrder(assignee, model) si el tècnic ja no té
        cap no-Done d'aquell model.
      - Model.predicted_*: es neteja NOMÉS si el model queda sense cap tasca no-Done assignada
        (si en manté alguna d'un altre tècnic, la seva previsió la manté aquell pla).
      - recompute_for_technicians: recalcula la cua sencera del tècnic afectat, UN SOL COP.
    (La tasca JA s'ha esborrat abans de cridar-la; aquí només es reconcilia el pla.)"""
    from fhort.models_app.models import Model
    cleanup_queue_order([assignee_id], [model_id])
    still_assigned = (ModelTask.objects.filter(model_id=model_id)
                      .exclude(status='Done').filter(assignee__isnull=False).exists())
    if not still_assigned:
        Model.objects.filter(pk=model_id).update(predicted_start=None, predicted_end=None)
    return recompute_for_technicians([assignee_id], now=now)


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
    # El model surt de la cua dels tècnics afectats → esborra l'ordre manual desat (si n'hi havia).
    cleanup_queue_order(affected, [model_id])
    # El model torna a Pendents: sense tasques no-Done planificades → neteja la previsió del model.
    Model.objects.filter(pk=model_id).update(predicted_start=None, predicted_end=None)
    results = recompute_for_technicians(affected, now=now)
    return {'unassigned_count': count, 'technician_ids': sorted(affected), 'results': results}
