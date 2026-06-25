"""Sprint G + Cascada de temps: lookup d'estimació per a ModelTask (snapshot).

Cascada de resolució (diagnosi §9, choke-point únic):
  1) cel·la pròpia (item × task): empíric madur (n>=llindar) o, si no, seed de l'item.
  2) empíric_global del task_type: mitjana en viu de les cel·les madures de qualsevol item.
  3) llavor task/fase (TimeSeed)  — graó posterior.
  4) None (graó captura-PM)        — graó posterior.
CONTRACTE de retorn: enter > 0, o None (mai 0; vegeu services_i.effective_minutes)."""


def lookup_estimated_minutes(model, task_type):
    """Minuts estimats per a (model, task_type) seguint la cascada, o None si cap graó té dada."""
    from django.db.models import Avg
    from .models import TaskTimeEstimate
    from .services_i import effective_minutes, WELFORD_MIN_SAMPLES

    # Graó 1 — cel·la pròpia (item × task): empíric madur o seed de l'item (effective_minutes
    # ja aplica el contracte >0/None). Un valor específic de l'item té prioritat sobre el global.
    item_id = getattr(model, 'garment_type_item_id', None)
    if item_id:
        cell = (TaskTimeEstimate.objects
                .filter(garment_type_item_id=item_id, task_type=task_type)
                .first())
        if cell is not None:
            val = effective_minutes(cell)
            if val:                       # >0; None → continua avall
                return val

    # Graó 2 — empíric_global del task_type: mitjana de les cel·les MADURES (n>=llindar) de
    # QUALSEVOL item. Càlcul EN VIU (sense taula nova). Reusa WELFORD_MIN_SAMPLES de services_i.
    avg = (TaskTimeEstimate.objects
           .filter(task_type=task_type, n__gte=WELFORD_MIN_SAMPLES, mean_minutes__gt=0)
           .aggregate(v=Avg('mean_minutes'))['v'])
    if avg and avg > 0:
        return int(round(avg))

    # Graó 3 (llavor task/fase) i 4 (None): graons posteriors.
    return None
