"""
tasks/services.py — Business logic for tasks.

La branca rígida del gate (generate_model_tasks / recalculate_current_phase /
process_gate) s'ha retirat a Sprint 0. Només queda _get_model_task, que encara
fa servir tasks_summary_view (action_views.py).
"""
from __future__ import annotations


def _get_model_task():
    """Lazy import to avoid circular imports."""
    try:
        from fhort.tasks.models import ModelTasca
        return ModelTasca
    except ImportError:
        from fhort.models_app.models import ModelTasca
        return ModelTasca
