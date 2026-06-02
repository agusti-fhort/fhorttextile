"""Sprint E: confecció (Production) + regles dures gate↔confecció↔fitting."""
from django.db import transaction
from django.utils import timezone
from .models import Production, Supplier, GateEvent


class ProductionError(Exception):
    pass


def phase_passed_gate(model_id: int, phase: str) -> bool:
    """Regla dura: una fase només es pot enviar a confecció si ha passat el gate."""
    return GateEvent.objects.filter(model_id=model_id, to_phase=phase).exists()


@transaction.atomic
def request_production(model, phase, supplier, by_profile, expected_at=None, notes=None):
    """Enviar a confecció.
    Gap B (5B): la fase ACTUAL del model (model.fase_actual) es pot enviar a confecció SENSE
    GateEvent previ — el model ja "viu" en aquesta fase. Les fases FUTURES segueixen exigint
    que hagin passat el gate (GateEvent to_phase=phase)."""
    if phase != model.fase_actual and not phase_passed_gate(model.id, phase):
        raise ProductionError(
            f"La fase '{phase}' és futura i no ha passat el gate; no es pot enviar a confecció.")
    return Production.objects.create(
        model=model, phase=phase, supplier=supplier, status='Requested',
        requested_by=by_profile, expected_at=expected_at, notes=notes)


@transaction.atomic
def set_production_status(production, new_status):
    """Transició del cicle: Requested→InProgress→Delivered. Delivered posa delivered_at."""
    ALLOWED = {'Requested': {'InProgress', 'Delivered'},
               'InProgress': {'Delivered'},
               'Delivered': set()}
    if new_status not in ALLOWED.get(production.status, set()):
        raise ProductionError(f"Transició no permesa: {production.status} → {new_status}")
    production.status = new_status
    if new_status == 'Delivered' and production.delivered_at is None:
        production.delivered_at = timezone.now()
    production.save(update_fields=['status', 'delivered_at'])
    return production


def has_delivered_production(model_id: int, phase: str) -> bool:
    """Regla dura 2: existeix una confecció Delivered per a aquesta fase del model?"""
    return Production.objects.filter(model_id=model_id, phase=phase, status='Delivered').exists()
