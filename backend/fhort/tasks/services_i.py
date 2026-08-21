"""Sprint I: temps evolucionables. En completar una tasca, el temps real alimenta
l'estadística Welford de la cel·la (garment_type_item × task_type). El planificador
usa la mitjana real quan hi ha prou mostres (§7: error mínim a la 2a temporada)."""
import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import Q, Sum
logger = logging.getLogger(__name__)

WELFORD_MIN_SAMPLES = 5   # llindar seed→estadística

# REGLA D'HIGIENE — cap tram de timer d'un tècnic dura més d'un dia seguit. Els que ho fan són
# fuites (timer deixat obert i tancat setmanes després en reobrir la tasca), i alimentaven el
# Welford amb mitjanes de 9-13 h que el planificador després feia servir com si fossin reals.
# El criteri viu AQUÍ i en un sol lloc: la data-op del 27/07, `recompute_welford` i TOTES les
# lectures de temps de cara a l'usuari el comparteixen.
MAX_MINUTS_TRAM = 24 * 60

# LA LLEI, en una sola expressió: un tram COMPTA si està tancat i no supera el llindar.
# El criteri és EXCLUSIÓ, no retall — el mateix que `recompute_welford:49-50`. Un tram de 3.710
# min no és una jornada llarga que calgui podar a 24 h: és una fuita, i no sabem quant s'hi va
# treballar de debò. Retallar-lo inventaria 1.440 minuts de feina que ningú no ha fet; excloure'l
# només diu "d'aquest tram no en tenim dada". Una sola llei, cap divergència.
# J · I UN TRAM DE CONSULTA TAMPOC NO COMPTA — mirar no és treballar.
#
# 🔒 EL LLINDAR DE PLAUSIBILITAT NO ES TOCA I NO SE'N FABRICA UN DE PARAL·LEL. `MAX_MINUTS_TRAM`
# segueix sent l'única constant de plausibilitat del sistema, i el descart de J **no n'és una
# segona**: no és un llindar, és una MARCA. La pregunta que fa no és «quant ha durat?» sinó
# «s'hi ha escrit?», que és una altra dimensió — i havia de ser-ho, perquè decidir-ho per durada
# contradiria la decisió d'Agus escrita a `ModelSheet.jsx` («no hi ha hagut sessió» no vol dir
# «ha durat poc»: una sessió de dos minuts amb la tasca oberta val igual que una de dues hores).
#
# Mateix criteri que el llindar, i per això entra a la MATEIXA expressió: **EXCLUSIÓ, no retall**.
# D'un tram de consulta no en tenim zero minuts de feina: en tenim minuts que no són feina.
#
# `~Q(consulta=True)` i no `Q(consulta=False)`, i la diferència és tot l'històric: `None` vol dir
# «no jutjat» —les files d'abans del camp i les que el desplegament va enxampar obertes— i ha de
# seguir comptant exactament com sempre. Amb `Q(consulta=False)` la clàusula hauria buidat el
# Welford, l'albarà i el consum de cop, en silenci i sense migració.
#
# Un sol punt, i per això n'hi ha prou amb aquesta línia: d'aquí pengen `record_actual_time`
# (Welford), `_real_minutes`, `minuts_per_model_task`, l'albarà (`commerce/services.py`), el
# registre de consum i tots els agregadors visibles.
TRAMS_SANS = Q(fi__isnull=False, minuts__lte=MAX_MINUTS_TRAM) & ~Q(consulta=True)


def tram_compta(timer):
    """Versió Python de `TRAMS_SANS`, per als bucles sobre timers ja prefetchats (albarà,
    registre de consum). Ha de dir SEMPRE el mateix que el filtre ORM.

    ⚠️ BESSONS DECLARATS I CAP GATE ELS COMPARA: qui toqui l'un ha de tocar l'altre. La clàusula
    de consulta de J hi entra alhora, i pel mateix motiu pel qual el llindar hi és.
    """
    return (timer.fi is not None
            and (timer.minuts or 0) <= MAX_MINUTS_TRAM
            and timer.consulta is not True)


def minuts_per_model_task(timer_qs):
    """{model_task_id: minuts sans} sobre un queryset de TimerEntrada, en 1 query.
    Font ÚNICA dels agregadors visibles (compositor del dashboard, anàlisi de temps): abans
    cadascun repetia el seu propi `Sum('minuts')` sense higiene i donaven xifres diferents."""
    return {r['model_task_id']: (r['s'] or 0)
            for r in timer_qs.filter(TRAMS_SANS).values('model_task_id').annotate(s=Sum('minuts'))}


def _real_minutes(model_task):
    """Temps real d'una tasca = suma dels trams SANS (inclou rectificacions).
    Mateixa llei que el recompute: els trams desbocats no són temps treballat i no hi entren."""
    return model_task.timers.filter(TRAMS_SANS).aggregate(s=Sum('minuts'))['s'] or 0


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
