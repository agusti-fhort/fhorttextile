"""Sprint G: lookup d'estimació de temps per a ModelTask (snapshot)."""


def lookup_estimated_minutes(model, task_type):
    """Retorna els minuts estimats per (garment_type_item del model × task_type), o None.
    None si el model no té garment_type_item o no hi ha cel·la TaskTimeEstimate."""
    from .models import TaskTimeEstimate
    from .services_i import effective_minutes
    item_id = getattr(model, 'garment_type_item_id', None)
    if not item_id:
        return None
    cell = (TaskTimeEstimate.objects
            .filter(garment_type_item_id=item_id, task_type=task_type)
            .first())
    if cell is None:
        return None
    return effective_minutes(cell)
