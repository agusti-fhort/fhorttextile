"""Reagendament d'una ModelTask al calendari laboral.

Sprint Y — extret de `models_app/services_size_check.py` (`_reagenda_tasca_size_check`) i
parametritzat pel `task_type_code`, perquè la convocatòria (contenidor) el pugui reusar per a
la tasca de presa de mesures, no només per al camí del check. Mecànica interna IDÈNTICA:
`next_working_slot` + `add_working_minutes` + `planned_locked`. El fallback de 60 minuts es
conserva tal com era (anotat, no és acoblament al type).
"""
import datetime as _dt
import logging

logger = logging.getLogger(__name__)


def reagenda_tasca(model, data_represa, task_type_code='size_check') -> bool:
    """Fixa la tasca viva de `task_type_code` del model a `data_represa` al calendari laboral:
    planned_start (08:00 del primer instant hàbil) + planned_end (+estimated o 60') +
    planned_locked. Gate tou: sense tasca o data invàlida → False (no peta)."""
    try:
        from django.utils import timezone as djtz
        from .models import ModelTask
        from fhort.planning.calendar_service import next_working_slot, add_working_minutes

        task = (ModelTask.objects
                .filter(model=model, task_type__code=task_type_code)
                .exclude(status='Done').order_by('-id').first())
        if task is None:
            return False
        d = _dt.date.fromisoformat(data_represa) if isinstance(data_represa, str) else data_represa
        prof = task.assignee
        naive_start = next_working_slot(prof, _dt.datetime.combine(d, _dt.time(8, 0)))
        naive_end = add_working_minutes(prof, naive_start, task.estimated_minutes or 60)
        task.planned_start = djtz.make_aware(naive_start)
        task.planned_end = djtz.make_aware(naive_end)
        task.planned_locked = True
        task.save(update_fields=['planned_start', 'planned_end', 'planned_locked', 'updated_at'])
        return True
    except Exception as e:
        logger.warning(f"reagenda_tasca: no s'ha pogut reagendar {task_type_code} del model {model.pk}: {e}")
        return False
