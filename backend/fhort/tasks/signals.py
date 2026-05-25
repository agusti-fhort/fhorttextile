"""
tasks/signals.py — Signals per a ModelTasca.
Equivalent als Server Scripts:
  - after_save → recalcula fase_actual
  - before_delete → recalcula fase_actual (exclou la tasca esborrada)
  - after_save (gate Feta) → desbloqueja tasques
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


def _get_model_tasca():
    try:
        from fhort.tasks.models import ModelTasca
        return ModelTasca
    except ImportError:
        try:
            from fhort.models_app.models import ModelTasca
            return ModelTasca
        except ImportError:
            return None


@receiver(post_save)
def after_save_model_tasca(sender, instance, **kwargs):
    """Recalcula fase_actual del model pare quan canvia una tasca."""
    ModelTasca = _get_model_tasca()
    if ModelTasca is None or sender is not ModelTasca:
        return
    if not instance.model_id:
        return

    from fhort.tasks.services import recalcular_fase_actual, processar_gate
    recalcular_fase_actual(instance.model_id)

    # Si acaba de passar a Feta i és un gate, desbloqueja
    if instance.estat == 'Feta' and instance.gate:
        processar_gate(instance.pk)


@receiver(post_delete)
def after_delete_model_tasca(sender, instance, **kwargs):
    """Recalcula fase_actual excloent la tasca esborrada."""
    ModelTasca = _get_model_tasca()
    if ModelTasca is None or sender is not ModelTasca:
        return
    if not instance.model_id:
        return

    from fhort.tasks.services import recalcular_fase_actual
    recalcular_fase_actual(instance.model_id, excloure_tasca_id=instance.pk)
