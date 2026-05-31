"""Sprint H: planificador predictiu. Calcula dates previstes per model i campanya
a partir de la càrrega (estimated_minutes) i la capacitat, respectant seqüència i
dates bloquejades. Desa la previsió com a PlanSnapshot (previst-vs-real, §7)."""
import datetime
from django.db import transaction
from django.db.models import Sum
from .models import ModelTask, PlanSnapshot


def _model_load_minutes(model_id):
    """Càrrega pendent d'un model = suma estimated_minutes de ModelTask no-Done.
    null compta com 0. Retorna (load, has_unestimated)."""
    qs = ModelTask.objects.filter(model_id=model_id).exclude(status='Done')
    total = qs.aggregate(s=Sum('estimated_minutes'))['s'] or 0
    has_unestimated = qs.filter(estimated_minutes__isnull=True).exists()
    return total, has_unestimated


def _next_working_day(d, blocked):
    """Avança al següent dia laborable (salta caps de setmana i blocked)."""
    while d.weekday() >= 5 or d.isoformat() in blocked:
        d += datetime.timedelta(days=1)
    return d


def compute_plan(start_date, model_ids_ordered, technician_count=1,
                 working_minutes_per_day=420, blocked_dates=None):
    """Calcula la previsió. Models en SÈRIE (capacitat compartida); technician_count
    augmenta la capacitat diària. Retorna dict {models:{...}, campaign_end, warnings}."""
    if isinstance(start_date, str):
        start_date = datetime.date.fromisoformat(start_date)
    blocked = set(blocked_dates or [])
    daily_cap = max(1, technician_count * working_minutes_per_day)
    cursor = _next_working_day(start_date, blocked)
    models_out = {}
    warnings = []
    for mid in model_ids_ordered:
        load, has_un = _model_load_minutes(mid)
        if has_un:
            warnings.append({'model_id': mid, 'warning': 'té tasques sense estimació'})
        m_start = cursor
        remaining = load
        if remaining <= 0:
            # model sense càrrega: ocupa 0 dies, inici=fi=dia actual
            models_out[str(mid)] = {'predicted_start': m_start.isoformat(),
                                    'predicted_end': m_start.isoformat(),
                                    'load_minutes': 0}
            continue
        day = cursor
        while remaining > 0:
            day = _next_working_day(day, blocked)
            remaining -= daily_cap
            if remaining > 0:
                day += datetime.timedelta(days=1)
        m_end = day
        models_out[str(mid)] = {'predicted_start': m_start.isoformat(),
                                'predicted_end': m_end.isoformat(),
                                'load_minutes': load}
        # següent model comença el dia laborable següent
        cursor = _next_working_day(m_end + datetime.timedelta(days=1), blocked)
    campaign_end = max((v['predicted_end'] for v in models_out.values()), default=None)
    return {'models': models_out, 'campaign_end': campaign_end, 'warnings': warnings}


@transaction.atomic
def compute_and_save_plan(*, start_date, model_ids_ordered, technician_count=1,
                          working_minutes_per_day=420, blocked_dates=None,
                          campaign_filter=None, computed_by=None):
    """Calcula, DESA un PlanSnapshot immutable, i actualitza predicted_start/end dels models."""
    from fhort.models_app.models import Model
    result = compute_plan(start_date, model_ids_ordered, technician_count,
                          working_minutes_per_day, blocked_dates)
    snap = PlanSnapshot.objects.create(
        computed_by=computed_by,
        start_date=start_date if not isinstance(start_date, str) else start_date,
        technician_count=technician_count, working_minutes_per_day=working_minutes_per_day,
        blocked_dates=list(blocked_dates or []), model_sequence=list(model_ids_ordered),
        campaign_filter=campaign_filter or {}, result=result)
    # Actualitzar la data prevista vigent de cada model
    for mid, vals in result['models'].items():
        Model.objects.filter(pk=int(mid)).update(
            predicted_start=vals['predicted_start'], predicted_end=vals['predicted_end'])
    return snap
