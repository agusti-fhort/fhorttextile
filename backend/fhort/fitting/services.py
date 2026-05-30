"""
fitting/services.py — Serveis per al cicle de fitting.
Flux:
  1. crear_fitting() → crea SFFitting + línies des de GradedSpec vigent
  2. L'usuari edita valor_nou en cada SFFittingLinia
  3. tancar_fitting() → actualitza GradedSpec + actualitza perfil client (Welford)
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def crear_fitting(size_fitting_id: int, tipus: str, user_id: int | None = None) -> tuple:
    """
    Crea un nou SFFitting amb les línies poblades des de GradedSpec vigent.

    Paràmetres:
      - size_fitting_id: pk del SizeFitting
      - tipus: "Proto" | "Sample" | "PPS"
      - user_id: pk de l'usuari responsable

    Retorna: (fitting_obj, linies_creades: int)
    """
    from fhort.fitting.models import SizeFitting, SFFitting, SFFittingLinia

    sf = SizeFitting.objects.select_related('model').get(pk=size_fitting_id)

    if sf.estat not in ('TallesGenerades', 'Tancat'):
        raise ValueError(
            f"Cal generar les talles primer (estat actual: '{sf.get_estat_display()}'). "
            "Tanca la base i genera les talles amb el botó corresponent."
        )

    # Número de fitting (autoincrement per SF)
    fitting_num = SFFitting.objects.filter(size_fitting=sf).count() + 1

    fitting = SFFitting.objects.create(
        size_fitting=sf,
        fitting_num=fitting_num,
        tipus=tipus,
        estat='Obert',
        responsable_id=user_id,
    )

    # Carregar GradedSpecs vigents
    graded_specs = _get_graded_specs(sf)

    if not graded_specs:
        raise ValueError(
            "No hi ha especificacions de grading generades per a aquest SF. "
            "Executa 'Generar talles' primer."
        )

    # Crear línies
    size_run = []
    if sf.model.size_run_model:
        size_run = [
            s.strip()
            for s in sf.model.size_run_model.replace(';', '·').split('·')
            if s.strip()
        ]

    linies_creades = 0
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
        linies_creades += 1

    logger.info(
        f"Fitting #{fitting_num} creat per SF {size_fitting_id}: "
        f"{linies_creades} línies"
    )
    return fitting, linies_creades


def tancar_fitting(fitting_id: int) -> dict:
    """
    Tanca el fitting i:
      1. Actualitza GradedSpec amb els valors nous
      2. Actualitza ClientMesuraPerfil (Welford) per a cada mesura nova
      3. Marca el fitting com a Tancat

    Retorna: {'modificades': int, 'ok': int, 'total': int}
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

    linies = list(SFFittingLinia.objects.filter(fitting=fitting).select_related('pom'))
    model = fitting.size_fitting.model

    modificades = 0
    ok = 0
    errors = []

    # Obtenir GradedSpec actiu
    graded_version = _get_active_grading_version(fitting.size_fitting)

    for linia in linies:
        if linia.valor_nou is None:
            linia.estat_cella = 'OK'
            ok += 1
        elif abs((linia.valor_nou or 0) - (linia.valor_vigent or 0)) < 0.001:
            linia.estat_cella = 'OK'
            ok += 1
        else:
            linia.estat_cella = 'Modificat'
            modificades += 1

            # Actualitzar GradedSpec
            if graded_version:
                try:
                    from fhort.pom.models import GradedSpec
                    GradedSpec.objects.filter(
                        grading_version=graded_version,
                        pom=linia.pom,
                        size_label=linia.talla,
                    ).update(graded_value_cm=linia.valor_nou)
                except Exception as e:
                    errors.append(f"GradedSpec pom={linia.pom_id} talla={linia.talla}: {e}")

            # Actualitzar perfil client (Welford)
            if model.client_id and model.garment_type_id and linia.valor_nou:
                try:
                    from fhort.pom.services import update_client_profile
                    update_client_profile(
                        client_id=model.client_id,
                        garment_type_id=model.garment_type_id,
                        pom_id=linia.pom_id,
                        size=linia.talla,
                        value_cm=linia.valor_nou,
                    )
                except Exception as e:
                    logger.warning(f"Welford update fallat: {e}")

        linia.save(update_fields=['estat_cella'])

    # Tancar el fitting
    fitting.estat = 'Tancat'
    fitting.data_fi = timezone.now()
    fitting.save(update_fields=['estat', 'data_fi'])

    if errors:
        logger.warning(f"Errors tancant fitting {fitting_id}: {errors}")

    result = {'modificades': modificades, 'ok': ok, 'total': len(linies)}
    logger.info(f"Fitting #{fitting.fitting_num} tancat: {result}")
    return result


def anullar_fitting(fitting_id: int, motiu: str = '') -> None:
    """Anul·la un fitting obert."""
    from fhort.fitting.models import SFFitting

    fitting = SFFitting.objects.get(pk=fitting_id)
    if fitting.estat != 'Obert':
        raise ValueError(f"Només es poden anul·lar fittings Oberts (estat: {fitting.estat}).")

    fitting.estat = 'Anullat'
    fitting.motiu_anulacio = motiu
    fitting.save(update_fields=['estat', 'motiu_anulacio'])


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_graded_specs(sf):
    """Obté els GradedSpec vigents ordenats per display_order i talla."""
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
        logger.error(f"Error carregant GradedSpecs: {e}")
        return []


def _get_active_grading_version(sf):
    """Obté la GradingVersion activa per al SizeFitting."""
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
