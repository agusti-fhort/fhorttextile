"""Sprint D: gate del responsable (avanç de fase sense sessió) + readiness."""
from django.db import transaction
from fhort.models_app.models import Model
from .models import ModelTask, GateEvent


class GateError(Exception):
    pass


def model_ready_for_gate(model_id: int) -> bool:
    """True si totes les ModelTask del model estan Done i n'hi ha com a mínim una."""
    qs = ModelTask.objects.filter(model_id=model_id)
    total = qs.count()
    if total == 0:
        return False
    return qs.exclude(status='Done').count() == 0


def _valid_phases():
    return [c[0] for c in Model.FASE_CHOICES]


@transaction.atomic
def advance_phase_gate(model, to_phase, by_profile, notes=None):
    """Gate del responsable: avança la fase d'un Model SENSE sessió de fitting.
    Guard de TOP. Escriu fase_actual + GateEvent. NO toca advance_phase de fitting."""
    phases = _valid_phases()
    if to_phase not in phases:
        raise GateError(f'Fase no vàlida: {to_phase} (∈ {phases})')
    frm = model.fase_actual
    if frm == 'TOP':
        raise GateError('El model ja és a TOP; no es pot avançar més.')
    model.fase_actual = to_phase
    model.save(update_fields=['fase_actual'])
    GateEvent.objects.create(model=model, from_phase=frm, to_phase=to_phase,
                             by=by_profile, notes=notes)
    return {'model_id': model.id, 'from_phase': frm, 'to_phase': to_phase}


@transaction.atomic
def advance_phases_chain(model, to_phases, by_profile, notes=None):
    """Encadena diversos gates consecutius (p.ex. acceptar proto + demanar sample).
    Aplica en seqüència; cada salt és un GateEvent. Atura si topa amb el guard de TOP."""
    results = []
    for ph in to_phases:
        results.append(advance_phase_gate(model, ph, by_profile, notes))
    return results
