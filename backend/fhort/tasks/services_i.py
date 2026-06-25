"""Sprint I: temps evolucionables. En completar una tasca, el temps real alimenta
l'estadística Welford de la cel·la (garment_type_item × task_type). El planificador
usa la mitjana real quan hi ha prou mostres (§7: error mínim a la 2a temporada)."""
import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
logger = logging.getLogger(__name__)

WELFORD_MIN_SAMPLES = 5   # llindar seed→estadística


def _real_minutes(model_task):
    """Temps real d'una tasca = suma de tots els timers (inclou rectificacions)."""
    return model_task.timers.aggregate(s=Sum('minuts'))['s'] or 0


@transaction.atomic
def record_actual_time(model_task):
    """Alimenta l'estadística Welford de la cel·la (item × task_type) amb el temps real.
    Salta si el model no té garment_type_item (no hi ha cel·la). Defensiva: mai trenca
    el tancament de la tasca."""
    from .models import TaskTimeEstimate
    try:
        item_id = getattr(model_task.model, 'garment_type_item_id', None)
        if not item_id:
            return None   # sense variant assignada → no hi ha cel·la a alimentar
        x = Decimal(_real_minutes(model_task))
        if x <= 0:
            return None   # sense temps real registrat → res a aprendre
        cell, _ = TaskTimeEstimate.objects.select_for_update().get_or_create(
            garment_type_item_id=item_id, task_type=model_task.task_type)
        # Welford online (mateix patró que pom.update_client_profile)
        n = cell.n + 1
        delta = x - cell.mean_minutes
        new_mean = cell.mean_minutes + (delta / n)
        delta2 = x - new_mean
        new_m2 = cell.m2 + (delta * delta2)
        cell.n = n
        cell.mean_minutes = new_mean
        cell.m2 = new_m2
        cell.save(update_fields=['n', 'mean_minutes', 'm2'])
        return cell
    except Exception as e:
        logger.warning(f"record_actual_time fallit per ModelTask {model_task.pk}: {e}")
        return None


def effective_minutes(cell):
    """Temps que el planificador ha d'usar: mitjana real si n>=llindar, si no el seed.
    CONTRACTE: retorna SEMPRE un enter > 0, o None (sense dada). Mai 0/negatiu com a
    durada planificable (treu l'ambigüitat None-vs-0 aigües avall)."""
    if cell.n >= WELFORD_MIN_SAMPLES and cell.mean_minutes > 0:
        emp = int(round(cell.mean_minutes))
        if emp > 0:                      # arrodoniment pot caure a 0 si mean < 0.5 → sense dada
            return emp
    seed = cell.estimated_minutes        # seed (pot ser None o 0)
    return seed if (seed and seed > 0) else None
