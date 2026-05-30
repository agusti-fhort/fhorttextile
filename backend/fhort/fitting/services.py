"""
fitting/services.py — Services for the fitting cycle.
Flow:
  1. create_fitting() → creates SFFitting + lines from the current GradedSpec
  2. The user edits valor_nou on each SFFittingLinia
  3. close_fitting() → updates GradedSpec + updates the client profile (Welford)
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def create_fitting(size_fitting_id: int, fitting_type: str, user_id: int | None = None) -> tuple:
    """
    Create a new SFFitting with lines populated from the current GradedSpec.

    Parameters:
      - size_fitting_id: pk of the SizeFitting
      - fitting_type: "Proto" | "Sample" | "PPS"
      - user_id: pk of the responsible user

    Returns: (fitting_obj, lines_created: int)
    """
    from fhort.fitting.models import SizeFitting, SFFitting, SFFittingLinia

    sf = SizeFitting.objects.select_related('model').get(pk=size_fitting_id)

    if sf.estat not in ('TallesGenerades', 'Tancat'):
        raise ValueError(
            f"Cal generar les talles primer (estat actual: '{sf.get_estat_display()}'). "
            "Tanca la base i genera les talles amb el botó corresponent."
        )

    # Fitting number (autoincrement per SF)
    fitting_num = SFFitting.objects.filter(size_fitting=sf).count() + 1

    fitting = SFFitting.objects.create(
        size_fitting=sf,
        fitting_num=fitting_num,
        tipus=fitting_type,
        estat='Obert',
        responsable_id=user_id,
    )

    # Load the current GradedSpecs
    graded_specs = _get_graded_specs(sf)

    if not graded_specs:
        raise ValueError(
            "No hi ha especificacions de grading generades per a aquest SF. "
            "Executa 'Generar talles' primer."
        )

    # Create lines
    size_run = []
    if sf.model.size_run_model:
        size_run = [
            s.strip()
            for s in sf.model.size_run_model.replace(';', '·').split('·')
            if s.strip()
        ]

    lines_created = 0
    for spec in graded_specs:
        SFFittingLinia.objects.create(
            fitting=fitting,
            pom=spec.pom,
            nom_pom=spec.pom.name_cat or spec.pom.name_en or spec.pom.pom_code,
            talla=spec.size_label,
            valor_vigent=spec.graded_value_cm,
            valor_nou=None,
            estat_cella='Pendent',
        )
        lines_created += 1

    logger.info(
        f"Fitting #{fitting_num} created for SF {size_fitting_id}: "
        f"{lines_created} lines"
    )
    return fitting, lines_created


def close_fitting(fitting_id: int) -> dict:
    """
    Close the fitting and:
      1. Update GradedSpec with the new values
      2. Update ClientMesuraPerfil (Welford) for each new measurement
      3. Mark the fitting as Tancat

    Returns: {'modificades': int, 'ok': int, 'total': int}
    """
    from django.utils import timezone
    from fhort.fitting.models import SFFitting, SFFittingLinia

    fitting = SFFitting.objects.select_related(
        'size_fitting', 'size_fitting__model'
    ).get(pk=fitting_id)

    if fitting.estat != 'Obert':
        raise ValueError(
            f"El fitting #{fitting.fitting_num} ja està {fitting.estat}. "
            "Només es poden tancar fittings Oberts."
        )

    lines = list(SFFittingLinia.objects.filter(fitting=fitting).select_related('pom'))
    model = fitting.size_fitting.model

    modified = 0
    ok = 0
    errors = []

    # Get the active GradedSpec
    graded_version = _get_active_grading_version(fitting.size_fitting)

    for line in lines:
        if line.valor_nou is None:
            line.estat_cella = 'OK'
            ok += 1
        elif abs((line.valor_nou or 0) - (line.valor_vigent or 0)) < 0.001:
            line.estat_cella = 'OK'
            ok += 1
        else:
            line.estat_cella = 'Modificat'
            modified += 1

            # Update GradedSpec
            if graded_version:
                try:
                    from fhort.pom.models import GradedSpec
                    GradedSpec.objects.filter(
                        grading_version=graded_version,
                        pom=line.pom,
                        size_label=line.talla,
                    ).update(graded_value_cm=line.valor_nou)
                except Exception as e:
                    errors.append(f"GradedSpec pom={line.pom_id} talla={line.talla}: {e}")

            # Update client profile (Welford)
            if model.garment_type_id and line.valor_nou:
                try:
                    from fhort.pom.services import update_client_profile
                    update_client_profile(
                        codi_client=model.codi_client,
                        garment_type_id=model.garment_type_id,
                        pom_id=line.pom_id,
                        size=line.talla,
                        value_cm=line.valor_nou,
                    )
                except Exception as e:
                    logger.warning(f"Welford update failed: {e}")

        line.save(update_fields=['estat_cella'])

    # Close the fitting
    fitting.estat = 'Tancat'
    fitting.data_fi = timezone.now()
    fitting.save(update_fields=['estat', 'data_fi'])

    if errors:
        logger.warning(f"Errors closing fitting {fitting_id}: {errors}")

    result = {'modificades': modified, 'ok': ok, 'total': len(lines)}
    logger.info(f"Fitting #{fitting.fitting_num} closed: {result}")
    return result


def cancel_fitting(fitting_id: int, reason: str = '') -> None:
    """Cancel an open fitting."""
    from fhort.fitting.models import SFFitting

    fitting = SFFitting.objects.get(pk=fitting_id)
    if fitting.estat != 'Obert':
        raise ValueError(f"Només es poden anul·lar fittings Oberts (estat: {fitting.estat}).")

    fitting.estat = 'Anullat'
    fitting.motiu_anulacio = reason
    fitting.save(update_fields=['estat', 'motiu_anulacio'])


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_graded_specs(sf):
    """Get the current GradedSpec ordered by display_order and size."""
    grading_version = _get_active_grading_version(sf)
    if not grading_version:
        return []

    try:
        from fhort.pom.models import GradedSpec
        return list(
            GradedSpec.objects.filter(
                grading_version=grading_version, is_active=True
            ).select_related(
                'pom', 'pom__pom_global', 'pom__categoria'
            ).order_by('pom__categoria__display_order', 'size_label')
        )
    except Exception as e:
        logger.error(f"Error loading GradedSpecs: {e}")
        return []


def _get_active_grading_version(sf):
    """Get the active GradingVersion for the SizeFitting."""
    for module_path in ['pom.models', 'fitting.models']:
        try:
            import importlib
            m = importlib.import_module(module_path)
            GradingVersion = getattr(m, 'GradingVersion', None)
            if GradingVersion:
                return GradingVersion.objects.filter(
                    size_fitting=sf, is_active=True
                ).last()
        except Exception:
            continue
    return None


# ═════════════════════════════════════════════════════════════════════════════
# Sprint 5B.3 — New fitting cycle (FittingSession / PieceFitting / PieceFittingLine)
# Open (create) + close with FUNCTIONAL versioning + brain stub.
# Replaces the SFFitting cycle above (removed in 5B.5). Gate is 5B.4.
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
