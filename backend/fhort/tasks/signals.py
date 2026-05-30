"""
tasks/signals.py — Signals for ModelTasca.
Equivalent to Server Scripts:
  - after_save → recompute fase_actual
  - before_delete → recompute fase_actual (excluding the deleted task)
  - after_save (gate Feta) → unblock tasks
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


def _get_model_task():
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
def after_save_model_task(sender, instance, **kwargs):
    """Recompute the parent model's fase_actual when a task changes."""
    ModelTasca = _get_model_task()
    if ModelTasca is None or sender is not ModelTasca:
        return
    if not instance.model_id:
        return

    from fhort.tasks.services import recalculate_current_phase, process_gate
    recalculate_current_phase(instance.model_id)

    # If it just moved to Feta and it is a gate, unblock
    if instance.estat == 'Feta' and instance.es_gate:
        process_gate(instance.pk)


@receiver(post_delete)
def after_delete_model_task(sender, instance, **kwargs):
    """Recompute fase_actual excluding the deleted task."""
    ModelTasca = _get_model_task()
    if ModelTasca is None or sender is not ModelTasca:
        return
    if not instance.model_id:
        return

    from fhort.tasks.services import recalculate_current_phase
    recalculate_current_phase(instance.model_id, exclude_task_id=instance.pk)
