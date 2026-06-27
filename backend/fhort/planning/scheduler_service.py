"""Sprint Backend B — motor d'scheduling DETERMINISTA (sense solver).

Col·loca les ModelTask assignades a tècnics sobre el calendari laboral de l'Sprint A.
Una cua independent per tècnic (paral·lel entre tècnics, sèrie dins d'un tècnic), sobre
la primitiva ja provada `calendar_service.add_working_minutes`.

Regles (memo v2, decisions tancades):
  - Durada = snapshot `ModelTask.estimated_minutes` (NO la cel·la TaskTimeEstimate en viu).
  - Ordre ENTRE models: `prioritat` (1=urgent) → `data_objectiu` (nulls al final) → `codi_intern`.
    Ordre DINS d'un model: `task_type.default_order`.
  - `planned_locked=True` = punt fix; les seves franges es respecten com a OCUPADES i la
    resta es col·loca al voltant (una tasca movible no se solapa amb un locked: si la seva
    col·locació temptativa xocaria, s'empeny ENTERA després del locked — no es parteix).
  - Deadline: warning si `planned_end > model.data_objectiu` (no bloqueja).
  - Tasca sense `estimated_minutes` o sense `assignee` → warning, no es planifica.

TZ: calendar_service treballa en NAÏF (rellotge local de l'empresa). Aquí calculem en naïf i
LOCALITZEM (make_aware) just en escriure `planned_start/end` (DateTimeField, USE_TZ=True).
`Model.predicted_start/end` són DateField → hi desem `.date()` del min start / max end de les
ModelTask planificades del model en aquesta passada.
"""
import datetime as _dt

from django.db import transaction
from django.utils import timezone

from .calendar_service import add_working_minutes, next_working_slot

_MAX_LOCKED_HOPS = 64   # límit dur de franges locked encavalcades a saltar per tasca


def _now_naive():
    """Ara, en hora local naïf (coherent amb calendar_service)."""
    return timezone.localtime(timezone.now()).replace(tzinfo=None)


def _to_naive(aware_dt):
    """Datetime aware (BD) → naïf local per comparar amb el calendari."""
    return timezone.localtime(aware_dt).replace(tzinfo=None)


def _to_aware(naive_dt):
    """Datetime naïf local → aware per desar (USE_TZ=True)."""
    return timezone.make_aware(naive_dt)


def _model_sort_key(model):
    """Ordre ENTRE models: prioritat asc (1=urgent) → data_objectiu (nulls al final)
    → codi_intern (desempat estable)."""
    prioritat = model.prioritat if model.prioritat is not None else 3
    has_deadline = 0 if model.data_objectiu is not None else 1   # nulls al final
    deadline = model.data_objectiu or _dt.date.max
    return (prioritat, has_deadline, deadline, model.codi_intern or '')


def _task_sort_key(task):
    """Ordre DINS d'un model: default_order del task_type, després id (estable)."""
    return (task.task_type.default_order, task.id)


def _manual_positions(profile_id, model_ids):
    """Ordre MANUAL {model_id: position} de la cua d'un tècnic (TechnicianQueueOrder), en UNA query.
    Només lectura (no crea files). Sense files → dict buit (ordre natural)."""
    if not model_ids:
        return {}
    from .models import TechnicianQueueOrder
    return dict(TechnicianQueueOrder.objects
               .filter(profile_id=profile_id, model_id__in=model_ids)
               .values_list('model_id', 'position'))


def _overlaps(start, end, busy):
    """Retorna el primer interval busy (s,e) que se solapa amb [start,end), o None."""
    for bs, be in busy:
        if start < be and bs < end:
            return (bs, be)
    return None


def _place(profile, cursor, minutes, busy):
    """Col·loca `minutes` minuts de feina a partir de >= `cursor`, evitant els intervals
    `busy` (franges locked). Una tasca no es parteix: si la col·locació temptativa xoca amb
    un busy, s'empeny ENTERA després d'aquest busy i es reintenta. Retorna (start, end) naïf."""
    cur = cursor
    for _ in range(_MAX_LOCKED_HOPS):
        start = next_working_slot(profile, cur)
        end = add_working_minutes(profile, start, minutes)
        hit = _overlaps(start, end, busy)
        if hit is None:
            return start, end
        cur = hit[1]   # saltar fins al final del locked que xoca i reintentar
    raise RuntimeError('scheduler: massa franges locked encavalcades en una sola tasca')


def _collect_busy_intervals(profile, now):
    """Franges de fitting de l'assistent (FittingSession.attendees): busy per al scheduler.
    Només sessions vives (no Tancada/Anullada) amb start_time i duracio_minuts informats, i
    a partir d'ahir (no carreguem historial infinit). Retorna [(start_naive, end_naive), ...]."""
    from fhort.fitting.models import FittingSession   # import local: evita cicle planning↔fitting
    import datetime as _dt
    cutoff = (now - _dt.timedelta(days=1)).date()
    sessions = FittingSession.objects.filter(
        attendees=profile,
        data__gte=cutoff,
        start_time__isnull=False,
        duracio_minuts__isnull=False,
    ).exclude(estat__in=['Tancada', 'Anullada'])
    intervals = []
    for s in sessions:
        start_naive = _to_naive(timezone.make_aware(
            _dt.datetime.combine(s.data, s.start_time)))
        end_naive = start_naive + _dt.timedelta(minutes=s.duracio_minuts)
        intervals.append((start_naive, end_naive))
    return intervals


def schedule(model_task_qs, now=None, save=True):
    """Planifica les ModelTask donades sobre el calendari laboral.

    Args:
        model_task_qs: queryset/iterable de ModelTask a planificar.
        now: instant naïf des del qual planificar (per defecte, ara local).
        save: si True, escriu planned_start/end a les tasques movibles i agrega
              predicted_start/end als models afectats. Si False (preview), NO desa res.

    Retorna dict:
        {'placements': [{task_id, model, task_type, assignee, planned_start, planned_end,
                         locked}, ...]  (ordenades per tècnic i inici),
         'warnings': [{task_id, model, task_type, warning}, ...],
         'models': {model_id: {predicted_start, predicted_end}}}
    """
    now = now or _now_naive()
    # Accepta un queryset (compute/apply) o una llista d'objectes ja modificats en memòria
    # (preview: la tasca moguda es fixa sense escriure a la BD).
    if hasattr(model_task_qs, 'select_related'):
        tasks = list(model_task_qs.select_related('model', 'task_type', 'assignee'))
    else:
        tasks = list(model_task_qs)
    # Blindatge: el motor MAI planifica ni toca tasques Done (cinturó-i-tirants, no depèn dels
    # cridadors). Les Done són immutables: conserven assignee/finished_at/planned_* tal com estan.
    tasks = [t for t in tasks if t.status != 'Done']
    warnings = []
    placements = []          # dicts de sortida
    save_ops = []            # (task, start_naive, end_naive) a desar si save
    model_bounds = {}        # model_id -> [min_start_naive, max_end_naive]
    model_codi = {}          # model_id -> codi_intern (per ordenar la sortida)

    def _warn(task, msg):
        warnings.append({'task_id': task.id, 'model': task.model.codi_intern,
                         'task_type': task.task_type.code, 'warning': msg})

    def _bump_bounds(mid, start, end):
        b = model_bounds.get(mid)
        if b is None:
            model_bounds[mid] = [start, end]
        else:
            if start < b[0]:
                b[0] = start
            if end > b[1]:
                b[1] = end

    # 1) Agrupar per tècnic; sense assignee → warning, no es planifica.
    by_tech = {}
    for t in tasks:
        if t.assignee_id is None:
            _warn(t, 'sense assignee')
            continue
        by_tech.setdefault(t.assignee_id, []).append(t)

    # 2) Per tècnic: locked (punts fixos) + resta ordenada.
    for tech_id in sorted(by_tech):
        tech_tasks = by_tech[tech_id]
        profile = next(t.assignee for t in tech_tasks)
        locked = [t for t in tech_tasks if t.planned_locked]
        movable = [t for t in tech_tasks if not t.planned_locked]

        # Franges ocupades pels locked (naïf). Es reporten tal qual; no es reescriuen.
        busy = []
        # Franges de fitting dels assistents (busy externes al motor de tasques).
        busy.extend(_collect_busy_intervals(profile, now))
        for t in locked:
            if not (t.planned_start and t.planned_end):
                _warn(t, 'locked sense dates planificades')
                continue
            s, e = _to_naive(t.planned_start), _to_naive(t.planned_end)
            busy.append((s, e))
            placements.append({'task_id': t.id, 'model': t.model.codi_intern,
                               'task_type': t.task_type.code,
                               'assignee': profile.nom_complet,
                               'planned_start': s, 'planned_end': e, 'locked': True})
            _bump_bounds(t.model_id, s, e)
            model_codi[t.model_id] = t.model.codi_intern
        busy.sort()

        # 3) Ordenar la resta: ordre MANUAL (TechnicianQueueOrder) si existeix, sinó natural.
        #    Clau composta: (0, position) per als models amb fila manual → primer, pel seu position;
        #    (1, *_model_sort_key) per als sense fila → al final, per ordre natural.
        models_seen = {}
        for t in movable:
            models_seen.setdefault(t.model_id, t.model)
        manual_pos = _manual_positions(tech_id, list(models_seen))   # {model_id: position}, 1 query

        def _order_key(m):
            p = manual_pos.get(m.id)
            return (0, p) if p is not None else (1,) + _model_sort_key(m)

        ordered_movable = []
        for m in sorted(models_seen.values(), key=_order_key):
            ordered_movable.extend(sorted([t for t in movable if t.model_id == m.id],
                                          key=_task_sort_key))

        # 4) Col·locar en sèrie des de max(now, fi última col·locada), saltant els busy.
        cursor = now
        for t in ordered_movable:
            if not t.estimated_minutes or t.estimated_minutes <= 0:
                _warn(t, 'sense estimació de temps (no planificable)')
                continue
            start, end = _place(profile, cursor, t.estimated_minutes, busy)
            placements.append({'task_id': t.id, 'model': t.model.codi_intern,
                               'task_type': t.task_type.code,
                               'assignee': profile.nom_complet,
                               'planned_start': start, 'planned_end': end, 'locked': False})
            save_ops.append((t, start, end))
            _bump_bounds(t.model_id, start, end)
            model_codi[t.model_id] = t.model.codi_intern
            cursor = end
            # 6) Warning de deadline (no bloqueja).
            if t.model.data_objectiu and end.date() > t.model.data_objectiu:
                _warn(t, f'planned_end {end.date().isoformat()} > data_objectiu '
                         f'{t.model.data_objectiu.isoformat()}')

    # 5) Agregar Model.predicted_start/end (min start / max end), .date() per al DateField.
    models_out = {mid: {'predicted_start': b[0].date().isoformat(),
                        'predicted_end': b[1].date().isoformat()}
                  for mid, b in model_bounds.items()}

    if save:
        from fhort.models_app.models import Model
        with transaction.atomic():
            for t, start, end in save_ops:
                t.planned_start = _to_aware(start)
                t.planned_end = _to_aware(end)
                t.save(update_fields=['planned_start', 'planned_end', 'updated_at'])
            for mid, b in model_bounds.items():
                Model.objects.filter(pk=mid).update(
                    predicted_start=b[0].date(), predicted_end=b[1].date())

    # Sortida ordenada per (codi_intern del model, inici) per llegibilitat estable.
    placements.sort(key=lambda p: (p['model'], p['planned_start']))
    for p in placements:
        p['planned_start'] = p['planned_start'].isoformat()
        p['planned_end'] = p['planned_end'].isoformat()

    return {'placements': placements, 'warnings': warnings, 'models': models_out}
