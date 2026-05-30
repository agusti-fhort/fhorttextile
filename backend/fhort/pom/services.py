"""
pom/services.py — Grading and measurement services.
Equivalent to the functions in Frappe's api.py:
  - generate_graded_specs
  - close_base
  - update_client_profile (Welford online)
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# GRADING
# ─────────────────────────────────────────────────────────────────────────────

def generate_graded_specs(size_fitting_id: int) -> int:
    """
    Generate GradedSpec for every size of the Size & Fitting.

    Flow:
      1. Read BaseMeasurement of the model's base size
      2. Read GradingRules of the assigned RuleSet
      3. For each POM × size, apply the rule (LINEAR/STEP/FIXED/ZERO/EXCEPTION)
      4. Create or update GradedSpec
      5. Mark SF as "Talles generades"

    Returns the number of created/updated GradedSpec.
    """
    from fhort.fitting.models import SizeFitting

    sf = SizeFitting.objects.select_related(
        'model',
        'model__grading_rule_set',
        'model__size_system',
    ).get(pk=size_fitting_id)

    model = sf.model

    # Pre-checks
    if not model.grading_rule_set_id:
        raise ValueError(f"El model {model.codi_intern} no té Grading Rule Set assignat.")
    if not model.size_system_id:
        raise ValueError(f"El model {model.codi_intern} no té Size System assignat.")
    if not model.size_run_model:
        raise ValueError(f"El model {model.codi_intern} no té size_run_model definit.")
    if not model.base_size_label:
        raise ValueError(f"El model {model.codi_intern} no té base_size_label definit.")

    # Parse the size run (separator ·)
    size_run = [s.strip() for s in model.size_run_model.replace(';', '·').split('·') if s.strip()]
    base_size = model.base_size_label.strip()

    if base_size not in size_run:
        raise ValueError(
            f"La talla base '{base_size}' no és al size run: {size_run}"
        )

    base_idx = size_run.index(base_size)

    # Load the RuleSet rules
    rules = _load_grading_rules(model.grading_rule_set_id)
    exceptions = _load_grading_exceptions(model.grading_rule_set_id)
    # Sprint 5B.3: per-model overrides from validated fittings (highest priority).
    model_overrides = _load_model_overrides(model.pk)

    # Load base measurements
    base_measurements = _load_base_measurements(model.pk)

    if not base_measurements:
        raise ValueError(
            f"No hi ha BaseMeasurements per al model {model.codi_intern}. "
            "Cal entrar les mesures de la talla base primer."
        )

    # Create a new grading version or reuse the active one
    grading_version = _get_or_create_grading_version(sf)

    # Sprint 4 / F2: record which measurement version these specs are born from.
    current_version = model.measurements_version

    # Generate specs
    created = 0
    for pom_id, base_val in base_measurements.items():
        rule = rules.get(pom_id)

        for i, size_label in enumerate(size_run):
            steps = i - base_idx  # negative = smaller size, positive = larger

            override = model_overrides.get((pom_id, size_label))
            exc = exceptions.get((pom_id, size_label))
            if override is not None:
                # Per-model validated-fitting override wins over everything.
                graded_val = override
                gt_applied = 'EXCEPTION'
            elif exc:
                graded_val = exc['value_cm']
                gt_applied = 'EXCEPTION'
            elif rule is None:
                graded_val = base_val  # no rule = FIXED
                gt_applied = 'FIXED'
            else:
                graded_val, gt_applied = _apply_rule(rule, base_val, steps, i, base_idx)

            graded_val = round(graded_val, 2)
            increment = round(graded_val - base_val, 2)

            _upsert_graded_spec(
                grading_version_id=grading_version.pk,
                pom_id=pom_id,
                size_label=size_label,
                graded_value_cm=graded_val,
                grading_type_applied=gt_applied,
                increment_applied_cm=increment,
                generated_from_version=current_version,
            )
            created += 1

    # Mark SF
    SizeFitting.objects.filter(pk=size_fitting_id).update(
        estat='TallesGenerades'
    )

    logger.info(f"Grading generated for SF {size_fitting_id}: {created} specs")
    return created


def close_base(size_fitting_id: int, user_id: int | None = None) -> int:
    """
    Close the Size & Fitting base size and generate the sizes.
    Equivalent to Frappe's 'Tancar base' button.
    """
    from django.utils import timezone
    from fhort.fitting.models import SizeFitting

    sf = SizeFitting.objects.get(pk=size_fitting_id)

    if sf.base_tancada:
        raise ValueError("La talla base ja està tancada.")

    if sf.estat not in ('BaseOberta', 'Pendent'):
        raise ValueError(
            f"L'estat actual '{sf.get_estat_display()}' no permet tancar la base."
        )

    # Close base
    SizeFitting.objects.filter(pk=size_fitting_id).update(
        base_tancada=True,
        data_tancament_base=timezone.now(),
        estat='BaseTancada',
    )

    # Generate sizes
    n = generate_graded_specs(size_fitting_id)

    return n


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT MEASUREMENT PROFILE (Welford online)
# ─────────────────────────────────────────────────────────────────────────────

def update_client_profile(
    codi_client: str,
    garment_type_id: int,
    pom_id: int,
    size: str,
    value_cm: float,
) -> object:
    """
    Update the online measurement statistic per codi_client/garment/POM/size.
    Uses Welford's algorithm to compute mean and deviation without storing every
    individual value.

    Sprint 5B.3: keyed by `codi_client` (the brand-client within the tenant), not
    by the tenant-level Client FK.
    """
    from django.utils import timezone

    try:
        from fhort.pom.models import ClientMesuraPerfil
    except ImportError:
        logger.warning("ClientMesuraPerfil not found, skipping Welford update")
        return None

    profile, _ = ClientMesuraPerfil.objects.get_or_create(
        codi_client=codi_client or '',
        garment_type_id=garment_type_id,
        pom_id=pom_id,
        talla=size,
    )

    # Welford online algorithm
    n = (profile.n_mostres or 0) + 1
    old_mean = profile.mitjana or 0.0
    delta = value_cm - old_mean
    new_mean = old_mean + delta / n
    delta2 = value_cm - new_mean
    new_m2 = (profile.m2_acum or 0.0) + delta * delta2

    profile.n_mostres = n
    profile.mitjana = round(new_mean, 3)
    profile.m2_acum = new_m2
    profile.desviacio = round((new_m2 / n) ** 0.5, 3) if n > 1 else 0.0
    profile.darrera_actualitzacio = timezone.now()
    profile.save()

    return profile


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_grading_rules(rule_set_id: int) -> dict:
    """Return {pom_id: rule_obj} for the given RuleSet."""
    try:
        from fhort.pom.models import GradingRule
        return {r.pom_id: r for r in GradingRule.objects.filter(
            rule_set_id=rule_set_id, actiu=True
        )}
    except Exception as e:
        logger.warning(f"Could not load GradingRules: {e}")
        return {}


def _load_grading_exceptions(rule_set_id: int) -> dict:
    """Return {(pom_id, size_label): exc_obj}."""
    try:
        from fhort.pom.models import GradingException
        return {
            (e.pom_id, e.size_label): {'value_cm': e.value_cm}
            for e in GradingException.objects.filter(
                rule_set_id=rule_set_id, is_active=True
            )
        }
    except Exception as e:
        logger.warning(f"Could not load GradingExceptions: {e}")
        return {}


def _load_model_overrides(model_id: int) -> dict:
    """Return {(pom_id, size_label): value_cm} of per-model fitting overrides."""
    try:
        from fhort.models_app.models import ModelGradingOverride
        return {
            (o.pom_id, o.size_label): o.value_cm
            for o in ModelGradingOverride.objects.filter(model_id=model_id)
        }
    except Exception as e:
        logger.warning(f"Could not load ModelGradingOverride: {e}")
        return {}


def _load_base_measurements(model_id: int) -> dict:
    """Return {pom_id: base_value_cm}."""
    try:
        from fhort.models_app.models import BaseMeasurement
        return {
            bm.pom_id: bm.base_value_cm
            for bm in BaseMeasurement.objects.filter(
                model_id=model_id, is_active=True
            )
        }
    except Exception as e:
        logger.warning(f"Could not load BaseMeasurements: {e}")
        return {}


def _get_or_create_grading_version(sf):
    """Get or create the active GradingVersion for the SizeFitting."""
    try:
        from fhort.fitting.models import GradingVersion
        version = GradingVersion.objects.filter(
            size_fitting=sf, is_active=True
        ).last()
        if not version:
            num = GradingVersion.objects.filter(size_fitting=sf).count() + 1
            version = GradingVersion.objects.create(
                size_fitting=sf,
                version_number=num,
                is_active=True,
            )
        return version
    except Exception:
        # Fallback if GradingVersion has a different structure
        try:
            from fhort.fitting.models import GradingVersion
            version = GradingVersion.objects.filter(
                size_fitting=sf, is_active=True
            ).last()
            if not version:
                num = GradingVersion.objects.filter(size_fitting=sf).count() + 1
                version = GradingVersion.objects.create(
                    size_fitting=sf,
                    version_number=num,
                    is_active=True,
                )
            return version
        except Exception as e:
            raise RuntimeError(f"Could not get/create GradingVersion: {e}")


def _apply_rule(rule, base_val: float, steps: int, size_idx: int, base_idx: int):
    """Apply the grading rule and return (graded_value, grading_type_applied).

    Real Django fields: rule.logica (was grading_type), rule.increment (DecimalField,
    was increment_cm). The increment_above_xl field does not exist on the model —
    getattr falls back to the normal increment for STEP.
    """
    grading_type = rule.logica
    increment = float(rule.increment) if rule.increment else 0.0

    if grading_type == 'LINEAR':
        return base_val + (steps * increment), 'LINEAR'

    elif grading_type == 'STEP':
        # For large sizes (>= base + 2 steps), a different increment may apply.
        # increment_above_xl does not exist on the model — fall back to normal increment.
        increment_above = getattr(rule, 'increment_above_xl', None)
        increment_above = float(increment_above) if increment_above else increment
        if steps > 2:
            return base_val + (2 * increment) + ((steps - 2) * increment_above), 'STEP'
        return base_val + (steps * increment), 'STEP'

    elif grading_type == 'FIXED':
        return base_val, 'FIXED'

    elif grading_type == 'ZERO':
        return 0.0, 'ZERO'

    # Default: FIXED
    return base_val, 'FIXED'


def _upsert_graded_spec(
    grading_version_id: int,
    pom_id: int,
    size_label: str,
    graded_value_cm: float,
    grading_type_applied: str,
    increment_applied_cm: float,
    generated_from_version: int | None = None,
):
    """Create or update a GradedSpec."""
    try:
        from fhort.fitting.models import GradedSpec
        GradedSpec.objects.update_or_create(
            grading_version_id=grading_version_id,
            pom_id=pom_id,
            size_label=size_label,
            defaults={
                'graded_value_cm': graded_value_cm,
                'grading_type_applied': grading_type_applied,
                'increment_applied_cm': increment_applied_cm,
                'is_active': True,
                'generated_from_version': generated_from_version,
            }
        )
    except Exception as e:
        logger.error(f"Error creating GradedSpec pom={pom_id} size={size_label}: {e}")
        raise
