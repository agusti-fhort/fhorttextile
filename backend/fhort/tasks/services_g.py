"""Sprint G: lookup d'estimació de temps per a ModelTask (snapshot)."""


def lookup_estimated_minutes(model, task_type):
    """Retorna els minuts estimats per (garment_type_item del model × task_type), o None.
    None si el model no té garment_type_item o no hi ha cel·la TaskTimeEstimate."""
    from .models import TaskTimeEstimate
    item_id = getattr(model, 'garment_type_item_id', None)
    if not item_id:
        return None
    est = (TaskTimeEstimate.objects
           .filter(garment_type_item_id=item_id, task_type=task_type)
           .values_list('estimated_minutes', flat=True).first())
    return est
