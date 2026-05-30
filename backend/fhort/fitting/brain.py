"""
fitting/brain.py — Entry point to the dependency "brain" (graph / stale propagation).

Sprint 5B.3: STUB only. The fitting CLOSE calls this when a measurement change is
validated, so the muscle (fitting) is already decoupled from the brain (the graph
that will later propagate stale and re-open tasks). This implementation does NOT
propagate anything — it only records the hook so the real propagation can be wired
later WITHOUT touching the fitting service again.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def on_fitting_measurement_changed(
    *,
    piece_fitting_id: int,
    model_id: int,
    base_changed: bool,
    new_grading_version_id: int | None = None,
) -> None:
    """Hook fired when a closed PieceFitting validated a measurement change.

    STUB: no propagation. Logs the event and returns. The future brain will read
    the dependency graph from here and mark derived nodes stale / re-open tasks.
    """
    logger.info(
        "brain hook (stub): piece_fitting=%s model=%s base_changed=%s new_version=%s",
        piece_fitting_id, model_id, base_changed, new_grading_version_id,
    )
    return None
