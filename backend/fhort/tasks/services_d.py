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


def _publica_maduresa(model):
    """RETORN-2 — el gate també és maduresa: la marca ha de saber que la peça ha canviat de fase.

    L'ESTUDI MANA EN LA FASE (decisió del Patró C): el bessó de la marca l'adopta sense
    negociar-la. Es crida amb el model ja desat, perquè el resum porti la fase nova.

    No-fatal per construcció (`sync_estat_segur`): un gate és una decisió humana de maduresa i
    no pot dependre de si el pont de federació està obert. `sync_estat` ja calla sol per als
    models INTERN, que són la immensa majoria.
    """
    from fhort.tenants.federation_service import SENTIT_MADURESA, sync_estat_segur
    sync_estat_segur(model, SENTIT_MADURESA)


@transaction.atomic
def advance_phase_gate(model, to_phase, by_profile, notes=None):
    """Gate del responsable: avança la fase d'un Model SENSE sessió de fitting.
    Guard de TOP. Escriu fase_actual + GateEvent + segella el grading (D-3 peça 2).
    Producció (TOP) és TERMINAL: marca estat → Tancat (D-3 peça 4)."""
    phases = _valid_phases()
    if to_phase not in phases:
        raise GateError(f'Fase no vàlida: {to_phase} (∈ {phases})')
    frm = model.fase_actual
    if frm == 'TOP':
        raise GateError('El model ja és a TOP; no es pot avançar més.')
    # 5B-fix v2: avançar fase NOMÉS canvia el marcador (fase_actual) + GateEvent. Les ModelTask
    # queden SEMPRE obertes (la fase va en paral·lel); cap anul·lació ni tancament de timers.
    model.fase_actual = to_phase
    # D-3 peça 4: producció (TOP) és terminal — segella el patrimoni del model (segellat del grading,
    # avall). Bloc 3 (estat→fase): la terminalitat la marca fase==TOP; el camp `estat` ja no es
    # superficia (es retira al pas de migració diferit), per això ja no s'escriu aquí.
    model.save(update_fields=['fase_actual'])
    GateEvent.objects.create(model=model, from_phase=frm, to_phase=to_phase,
                             kind='advance', by=by_profile, notes=notes)
    # D-3 peça 2: el segellat del grading és conseqüència de l'avanç de gate (decisió
    # humana de maduresa), no de tancar la sessió de fitting.
    from fhort.fitting.services import seal_model_grading
    sealed_version = seal_model_grading(
        model, user_profile_id=(by_profile.id if by_profile else None)
    )
    _publica_maduresa(model)
    return {'model_id': model.id, 'from_phase': frm, 'to_phase': to_phase,
            'sealed_version': sealed_version}


@transaction.atomic
def regress_phase(model, to_phase, by_profile, notes=None):
    """Simètric de l'avanç: RETROCEDIR la fase (reobrir feina d'una fase anterior). NOMÉS canvia
    fase_actual enrere + GateEvent kind='regress'. Les ModelTask queden obertes (el temps que es
    refaci suma sobre les mateixes tasques). Guard: cal una fase anterior vàlida."""
    phases = _valid_phases()
    if to_phase not in phases:
        raise GateError(f'Fase no vàlida: {to_phase} (∈ {phases})')
    frm = model.fase_actual
    if phases.index(to_phase) >= phases.index(frm):
        raise GateError(f"'{to_phase}' no és anterior a la fase actual '{frm}'.")
    model.fase_actual = to_phase
    model.save(update_fields=['fase_actual'])
    GateEvent.objects.create(model=model, from_phase=frm, to_phase=to_phase,
                             kind='regress', by=by_profile, notes=notes)
    _publica_maduresa(model)
    return {'model_id': model.id, 'from_phase': frm, 'to_phase': to_phase}


@transaction.atomic
def advance_phases_chain(model, to_phases, by_profile, notes=None):
    """Encadena diversos gates consecutius (p.ex. acceptar proto + demanar sample).
    Aplica en seqüència; cada salt és un GateEvent. Atura si topa amb el guard de TOP."""
    results = []
    for ph in to_phases:
        results.append(advance_phase_gate(model, ph, by_profile, notes))
    return results
