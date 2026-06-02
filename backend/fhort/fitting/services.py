"""
fitting/services.py — Services for the fitting cycle.

The new cycle (FittingSession / PieceFitting / PieceFittingLine) lives below.
The legacy SFFitting cycle (create_fitting/close_fitting/cancel_fitting) was
removed in Sprint 5B.5 together with the SFFitting/SFFittingLinia models.
"""
from __future__ import annotations
import logging

from django.db import transaction

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Sprint 5B.3 — Fitting cycle (FittingSession / PieceFitting / PieceFittingLine)
# Open (create) + close with FUNCTIONAL versioning + brain stub. Gate is 5B.4.
# ═════════════════════════════════════════════════════════════════════════════

def create_session(
    *,
    fase: str,
    data,
    model_id: int | None = None,
    garment_set_id: int | None = None,
    responsable_id: int | None = None,
    model_persona: str = '',
    assistents: str = '',
    lloc: str = '',
    notes: str = '',
    created_by_id: int | None = None,
):
    """Create a FittingSession for a single Model OR a GarmentSet (XOR)."""
    from fhort.fitting.models import FittingSession

    if bool(model_id) == bool(garment_set_id):
        raise ValueError("Cal exactament un de model_id o garment_set_id (XOR).")

    return FittingSession.objects.create(
        fase=fase,
        data=data,
        model_id=model_id,
        garment_set_id=garment_set_id,
        responsable_id=responsable_id,
        model_persona=model_persona,
        assistents=assistents,
        lloc=lloc,
        notes=notes,
        created_by_id=created_by_id,
    )


def schedule_session(*, fase, data, responsable_id, model_id=None, garment_set_id=None,
                     lloc='', start_time=None, end_time=None):
    """Programa un fitting (estat Programada). El responsable fixa dia (i opcionalment hores).
    No s'executa fins que s'obre (open_session)."""
    if bool(model_id) == bool(garment_set_id):
        raise ValueError("Cal exactament un de model_id o garment_set_id (XOR).")
    # Pas 5B-fix: per a un MODEL, exigeix Production Delivered d'aquesta fase (recepció interna)
    # abans de programar el fitting. Bloqueig dur.
    if model_id:
        from fhort.tasks.services_e import has_delivered_production
        if not has_delivered_production(model_id, fase):
            raise ValueError(
                "Cal rebre la producció (Delivered) d'aquesta fase abans de programar el fitting.")
    from .models import FittingSession
    return FittingSession.objects.create(
        fase=fase, data=data, model_id=model_id, garment_set_id=garment_set_id,
        responsable_id=responsable_id, lloc=lloc,
        start_time=start_time, end_time=end_time, estat='Programada')


def open_session(session_id):
    """Obre una sessió Programada (acte del tècnic, el dia del fitting): Programada→Oberta."""
    from .models import FittingSession
    s = FittingSession.objects.get(pk=session_id)
    if s.estat != 'Programada':
        raise ValueError(f"Només es pot obrir una sessió Programada (estat actual: {s.estat}).")
    s.estat = 'Oberta'
    s.save(update_fields=['estat'])
    return s


def create_piece_fitting(session_id: int, model_id: int, *, created_by_id: int | None = None):
    """Create a PieceFitting for one piece and materialise its lines.

    Resolves the model's working SizeFitting → its active GradingVersion, then
    clones each active GradedSpec into a PieceFittingLine (valor_teoric = grading,
    valor_real = copy of the theoretical, editable). Returns (piece_fitting, n_lines).
    """
    from fhort.fitting.models import (
        FittingSession, PieceFitting, PieceFittingLine, GradedSpec,
    )
    from fhort.models_app.models import Model

    session = FittingSession.objects.get(pk=session_id)
    model = Model.objects.get(pk=model_id)

    sf = _resolve_working_size_fitting(model)
    if sf is None:
        raise ValueError(f"El model {model.codi_intern} no té cap SizeFitting de treball.")

    version = _active_grading_version(sf)
    if version is None:
        raise ValueError(
            f"El model {model.codi_intern} no té cap GradingVersion activa. "
            "Cal generar les talles primer."
        )

    pf = PieceFitting.objects.create(
        session=session,
        model=model,
        grading_version=version,
        created_by_id=created_by_id,
    )

    specs = GradedSpec.objects.filter(grading_version=version, is_active=True).select_related('pom')
    n = 0
    for spec in specs:
        PieceFittingLine.objects.create(
            piece_fitting=pf,
            pom=spec.pom,
            size_label=spec.size_label,
            valor_teoric=spec.graded_value_cm,
            valor_real=spec.graded_value_cm,  # copy, editable before close
        )
        n += 1

    logger.info(f"PieceFitting {pf.pk} created for model {model_id}: {n} lines")
    return pf, n


def close_piece_fitting(piece_fitting_id: int, *, user_profile_id: int | None = None) -> dict:
    """Close a PieceFitting, applying validated real values with FUNCTIONAL versioning.

    For each line where valor_real differs from valor_teoric:
      - BASE size  → promote to BaseMeasurement (root change) → F1 signal logs the
        change, measurements_version++, grading regenerated from the new base.
      - NON-base   → ModelGradingOverride (per-model, traceable), root untouched.
      - Welford fed with the real value (keyed by codi_client).
    Any validated change → a NEW GradingVersion (v+1) is created and the previous one
    deactivated (conserved). The brain stub is called once if anything changed.

    Returns: {'changed', 'base_changed', 'override_changed', 'new_version'}.
    """
    from django.db.models import F, Max
    from fhort.fitting.models import (
        PieceFitting, PieceFittingLine, GradingVersion,
    )
    from fhort.models_app.models import Model, BaseMeasurement, ModelGradingOverride

    pf = PieceFitting.objects.select_related(
        'model', 'grading_version', 'grading_version__size_fitting',
    ).get(pk=piece_fitting_id)
    model = pf.model
    sf = pf.grading_version.size_fitting
    base_size = (model.base_size_label or '').strip()

    # Resolve users: UserProfile (fitting layer) + its auth.User (F1 log layer).
    profile = None
    auth_user = None
    if user_profile_id:
        from fhort.accounts.models import UserProfile
        profile = UserProfile.objects.select_related('user').filter(pk=user_profile_id).first()
        auth_user = profile.user if profile else None

    lines = list(PieceFittingLine.objects.filter(piece_fitting=pf).select_related('pom'))

    changed = 0
    base_changed = False
    override_changed = False

    for line in lines:
        if line.valor_real is None:
            continue
        if abs(line.valor_real - line.valor_teoric) < 1e-6:
            continue  # no change on this line
        changed += 1
        is_base = line.size_label.strip() == base_size

        if is_base:
            # Root change → BaseMeasurement (the F1 signal writes the change log).
            bm, _created = BaseMeasurement.objects.get_or_create(
                model=model, pom=line.pom,
                defaults={'base_value_cm': line.valor_real, 'origen': 'FITTED'},
            )
            bm.base_value_cm = line.valor_real
            bm.origen = 'FITTED'
            bm._changed_by = auth_user
            bm._fitting_ref = sf            # MeasurementChangeLog.fitting_ref (→ SizeFitting)
            bm._motiu = f'Fitting · sessió {pf.session_id} · peça {pf.pk}'
            bm.save()
            base_changed = True
        else:
            # Per-model override (does NOT touch the shared rule_set or the root).
            ModelGradingOverride.objects.update_or_create(
                model=model, pom=line.pom, size_label=line.size_label,
                defaults={
                    'value_cm': line.valor_real,
                    'motiu': f'Fitting · sessió {pf.session_id} · peça {pf.pk}',
                    'fitting_ref': pf,
                    'created_by': profile,
                },
            )
            override_changed = True

        # Welford (keyed by codi_client within the tenant).
        if model.garment_type_id:
            try:
                from fhort.pom.services import update_client_profile
                update_client_profile(
                    codi_client=model.codi_client,
                    garment_type_id=model.garment_type_id,
                    pom_id=line.pom_id,
                    size=line.size_label,
                    value_cm=line.valor_real,
                )
            except Exception as e:
                logger.warning(f"Welford update failed: {e}")

    new_version_number = None
    if changed:
        # Functional versioning: deactivate ALL active versions (handles the
        # legacy multi-active anomaly), then create the new active one.
        GradingVersion.objects.filter(size_fitting=sf, is_active=True).update(is_active=False)
        max_num = GradingVersion.objects.filter(size_fitting=sf).aggregate(
            m=Max('version_number')
        )['m'] or 0
        new_version = GradingVersion.objects.create(
            size_fitting=sf,
            version_number=max_num + 1,
            is_active=True,
            creat_per=profile,
            nom=f'Fitting sessió {pf.session_id}',
        )
        new_version_number = new_version.version_number

        if base_changed:
            Model.objects.filter(pk=model.pk).update(
                measurements_version=F('measurements_version') + 1
            )

        # Regenerate grading into the NEW active version (reads new base + overrides).
        from fhort.pom.services import generate_graded_specs
        generate_graded_specs(sf.pk)

        # Brain stub (decoupled; no propagation yet).
        from fhort.fitting.brain import on_fitting_measurement_changed
        on_fitting_measurement_changed(
            piece_fitting_id=pf.pk,
            model_id=model.pk,
            base_changed=base_changed,
            new_grading_version_id=new_version.pk,
        )

    result = {
        'changed': changed,
        'base_changed': base_changed,
        'override_changed': override_changed,
        'new_version': new_version_number,
    }
    logger.info(f"PieceFitting {pf.pk} closed: {result}")
    return result


def discard_piece_fitting(piece_fitting_id: int) -> dict:
    """Revert a PieceFitting to its OPENING state: valor_real := valor_teoric for
    every line, atomically. Pure measurement revert — does NOT touch FittingSession,
    FittingPhoto, notes, gates, GradingVersion or grading. Returns {'reverted': N}.
    """
    from django.db import transaction
    from django.db.models import F
    from fhort.fitting.models import PieceFittingLine

    with transaction.atomic():
        reverted = (
            PieceFittingLine.objects
            .filter(piece_fitting_id=piece_fitting_id)
            .update(valor_real=F('valor_teoric'))
        )

    logger.info(f"PieceFitting {piece_fitting_id} discarded: {reverted} lines reverted")
    return {'reverted': reverted}


# ── Sprint 5B.3 helpers ──────────────────────────────────────────────────────

def _resolve_working_size_fitting(model):
    """The model's single working SizeFitting (prefer one with an active version)."""
    from fhort.fitting.models import SizeFitting, GradingVersion
    sfs = list(SizeFitting.objects.filter(model=model).order_by('numero'))
    if not sfs:
        return None
    for sf in sfs:
        if GradingVersion.objects.filter(size_fitting=sf, is_active=True).exists():
            return sf
    return sfs[0]


def _active_grading_version(sf):
    """Active GradingVersion of a SizeFitting (highest version_number wins)."""
    from fhort.fitting.models import GradingVersion
    return (
        GradingVersion.objects
        .filter(size_fitting=sf, is_active=True)
        .order_by('-version_number')
        .first()
    )


# ═════════════════════════════════════════════════════════════════════════════
# Sprint 5B.4 — Two-level gate + manual phase advance + production seal
# ═════════════════════════════════════════════════════════════════════════════

_GATE_RESULTS = ('OK', 'NO_OK', 'EXCEPCIO')
_GATE_ADVANCEABLE = ('OK', 'EXCEPCIO')  # EXCEPCIO = accepted exception → advances


def set_piece_gate(
    piece_fitting_id: int,
    resultat: str,
    motiu: str = '',
    *,
    user_profile_id: int | None = None,
):
    """Set the gate of a PieceFitting (a step AFTER close). Records who/when.

    resultat ∈ {OK, NO_OK, EXCEPCIO}. NO_OK fires the brain stub (future re-opening).
    """
    from django.utils import timezone
    from fhort.fitting.models import PieceFitting

    if resultat not in _GATE_RESULTS:
        raise ValueError(f"resultat ha de ser un de {_GATE_RESULTS} (rebut: {resultat!r}).")

    pf = PieceFitting.objects.select_related('model').get(pk=piece_fitting_id)
    pf.gate = resultat
    pf.gate_motiu = motiu or ''
    pf.gate_per_id = user_profile_id
    pf.gate_at = timezone.now()
    pf.save(update_fields=['gate', 'gate_motiu', 'gate_per', 'gate_at'])

    if resultat == 'NO_OK':
        # "Fallar és individual": signal the brain so it can later re-open this
        # piece's tasks. Stub today (no propagation).
        from fhort.fitting.brain import on_fitting_measurement_changed
        on_fitting_measurement_changed(
            piece_fitting_id=pf.pk,
            model_id=pf.model_id,
            base_changed=False,
            new_grading_version_id=None,
        )

    logger.info(f"PieceFitting {pf.pk} gate set to {resultat}")
    return pf


def session_can_advance(session_id: int) -> bool:
    """DERIVED (not stored): the session may advance iff every PieceFitting gate is
    in {OK, EXCEPCIO} and there is at least one piece (none Pendent/NO_OK)."""
    from fhort.fitting.models import PieceFitting

    gates = list(
        PieceFitting.objects.filter(session_id=session_id).values_list('gate', flat=True)
    )
    if not gates:
        return False
    return all(g in _GATE_ADVANCEABLE for g in gates)


@transaction.atomic
def advance_phase(session_id: int, nova_fase: str, *, user_profile_id: int | None = None) -> dict:
    """Manual phase advance: the responsible person CHOOSES nova_fase (may skip,
    repeat or go back — we do NOT compute "the next one").

    Guards: session Oberta + session_can_advance + nova_fase ∈ Model.FASE_CHOICES.
    For each PieceFitting: seal its vigent GradingVersion (aprovada + aprovada_per +
    data_aprovacio) and set its Model.fase_actual = nova_fase. Closes the session.

    Per-piece TOP guard: a piece already at 'TOP' asked to advance from TOP is a
    no-op (skipped, reported), not an error.
    """
    from django.utils import timezone
    from fhort.fitting.models import FittingSession, PieceFitting
    from fhort.models_app.models import Model

    valid_phases = {c[0] for c in Model.FASE_CHOICES}
    if nova_fase not in valid_phases:
        raise ValueError(f"nova_fase ha de ser ∈ {sorted(valid_phases)} (rebut: {nova_fase!r}).")

    session = FittingSession.objects.get(pk=session_id)
    if session.estat != 'Oberta':
        raise ValueError(f"La sessió ja està {session.estat}; només s'avança des d'Oberta.")
    if not session_can_advance(session_id):
        raise ValueError("La sessió no pot avançar: hi ha peces Pendent o NO_OK.")

    pieces = list(
        PieceFitting.objects.filter(session_id=session_id)
        .select_related('model', 'grading_version', 'grading_version__size_fitting')
    )

    # Regla dura (Sprint E): pre-check de confecció ABANS de cap mutació, per evitar estat
    # parcial en sessions multi-model. Els models a TOP se salten (no avancen, no s'exigeixen).
    from fhort.tasks.services_e import has_delivered_production
    missing = sorted({
        pf.model.pk for pf in pieces
        if pf.model.fase_actual != 'TOP'
        and not has_delivered_production(pf.model.pk, pf.model.fase_actual)
    })
    if missing:
        raise ValueError(
            f"No es pot avançar: cap confecció entregada per a la fase actual dels models {missing}."
        )

    now = timezone.now()
    sealed = []
    advanced = []
    skipped_top = []

    for pf in pieces:
        # TODO(§3.3 — deute conscient): Model.fase_actual el deriva avui tasks
        # (recalculate_current_phase via signal). Amb tasks=0 no hi ha conflicte;
        # la reconciliació múscul↔tasques és posterior. Escriptura directa a posta.
        model = pf.model
        if model.fase_actual == 'TOP':
            skipped_top.append(model.pk)
            continue

        # Seal the vigent (active) GradingVersion of this piece's SizeFitting.
        version = _active_grading_version(pf.grading_version.size_fitting)
        if version is not None:
            version.aprovada = True
            version.aprovada_per_id = user_profile_id
            version.data_aprovacio = now
            version.save(update_fields=['aprovada', 'aprovada_per', 'data_aprovacio'])
            sealed.append(version.pk)

        prev_phase = model.fase_actual
        Model.objects.filter(pk=model.pk).update(fase_actual=nova_fase)
        advanced.append(model.pk)

        try:
            from fhort.tasks.models import GateEvent
            GateEvent.objects.create(
                model_id=model.pk,
                from_phase=prev_phase,
                to_phase=nova_fase,
                by_id=user_profile_id,
                notes='(via fitting)',
            )
        except Exception:
            pass  # no trencar el fitting si el log falla

    session.estat = 'Tancada'
    session.save(update_fields=['estat'])

    result = {
        'nova_fase': nova_fase,
        'advanced_models': advanced,
        'sealed_versions': sealed,
        'skipped_top_models': skipped_top,
    }
    logger.info(f"Session {session_id} advanced: {result}")
    return result
