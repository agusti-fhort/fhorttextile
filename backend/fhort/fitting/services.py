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
            if model.client_id and model.garment_type_id and line.valor_nou:
                try:
                    from fhort.pom.services import update_client_profile
                    update_client_profile(
                        client_id=model.client_id,
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
