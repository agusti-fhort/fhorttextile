"""
pom/services.py — Serveis de grading i mesures.
Equivalent a les funcions de l'api.py de Frappe:
  - generar_graded_spec
  - tancar_base
  - actualitzar_perfil_client (Welford online)
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# GRADING
# ─────────────────────────────────────────────────────────────────────────────

def generar_graded_specs(size_fitting_id: int) -> int:
    """
    Genera GradedSpec per a totes les talles del Size & Fitting.

    Flux:
      1. Llegeix BaseMeasurement de la talla base del model
      2. Llegeix GradingRules del RuleSet assignat
      3. Per cada POM × talla, aplica la regla (LINEAR/STEP/FIXED/ZERO/EXCEPTION)
      4. Crea o actualitza GradedSpec
      5. Marca SF com a "Talles generades"

    Retorna el nombre de GradedSpec creats/actualitzats.
    """
    from fhort.fitting.models import SizeFitting

    sf = SizeFitting.objects.select_related(
        'model',
        'model__grading_rule_set',
        'model__size_system',
    ).get(pk=size_fitting_id)

    model = sf.model

    # Validacions prèvies
    if not model.grading_rule_set_id:
        raise ValueError(f"El model {model.codi} no té Grading Rule Set assignat.")
    if not model.size_system_id:
        raise ValueError(f"El model {model.codi} no té Size System assignat.")
    if not model.size_run_model:
        raise ValueError(f"El model {model.codi} no té size_run_model definit.")
    if not model.base_size_label:
        raise ValueError(f"El model {model.codi} no té base_size_label definit.")

    # Parse del run de talles (separador ·)
    size_run = [s.strip() for s in model.size_run_model.replace(';', '·').split('·') if s.strip()]
    base_size = model.base_size_label.strip()

    if base_size not in size_run:
        raise ValueError(
            f"La talla base '{base_size}' no és al size run: {size_run}"
        )

    base_idx = size_run.index(base_size)

    # Carregar regles del RuleSet
    rules = _load_grading_rules(model.grading_rule_set_id)
    exceptions = _load_grading_exceptions(model.grading_rule_set_id)

    # Carregar mesures base
    base_measurements = _load_base_measurements(model.pk)

    if not base_measurements:
        raise ValueError(
            f"No hi ha BaseMeasurements per al model {model.codi}. "
            "Cal entrar les mesures de la talla base primer."
        )

    # Crear nova versió de grading o reutilitzar l'activa
    grading_version = _get_or_create_grading_version(sf)

    # Generar specs
    created = 0
    for pom_id, base_val in base_measurements.items():
        rule = rules.get(pom_id)

        for i, size_label in enumerate(size_run):
            steps = i - base_idx  # negatiu = talla menor, positiu = major

            exc = exceptions.get((pom_id, size_label))
            if exc:
                graded_val = exc['value_cm']
                gt_applied = 'EXCEPTION'
            elif rule is None:
                graded_val = base_val  # sense regla = FIXED
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
            )
            created += 1

    # Marcar SF
    SizeFitting.objects.filter(pk=size_fitting_id).update(
        estat_mesures='Talles generades'
    )

    logger.info(f"Grading generat per SF {size_fitting_id}: {created} specs")
    return created


def tancar_base(size_fitting_id: int, user_id: int | None = None) -> int:
    """
    Tanca la talla base del Size & Fitting i genera les talles.
    Equivalent al botó 'Tancar base' de Frappe.
    """
    from django.utils import timezone
    from fhort.fitting.models import SizeFitting

    sf = SizeFitting.objects.get(pk=size_fitting_id)

    if sf.base_tancada:
        raise ValueError("La talla base ja està tancada.")

    if sf.estat_mesures not in ('Talla base oberta', 'Pendent'):
        raise ValueError(
            f"L'estat actual '{sf.estat_mesures}' no permet tancar la base."
        )

    # Tancar base
    SizeFitting.objects.filter(pk=size_fitting_id).update(
        base_tancada=True,
        data_tancament_base=timezone.now(),
        estat_mesures='Talla base tancada',
    )

    # Generar talles
    n = generar_graded_specs(size_fitting_id)

    return n


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT MESURA PERFIL (Welford online)
# ─────────────────────────────────────────────────────────────────────────────

def actualitzar_perfil_client(
    client_id: int,
    garment_type_id: int,
    pom_id: int,
    talla: str,
    valor_cm: float,
) -> object:
    """
    Actualitza l'estadística online de mesures per client/garment/POM/talla.
    Usa l'algorisme de Welford per calcular mitjana i desviació
    sense guardar tots els valors individuals.
    """
    from django.utils import timezone

    try:
        from fhort.pom.models import ClientMesuraPerfil
    except ImportError:
        logger.warning("ClientMesuraPerfil no trobat, s'omet actualització Welford")
        return None

    perfil, _ = ClientMesuraPerfil.objects.get_or_create(
        client_id=client_id,
        garment_type_id=garment_type_id,
        pom_id=pom_id,
        talla=talla,
    )

    # Welford online algorithm
    n = (perfil.n_mostres or 0) + 1
    old_mean = perfil.mitjana or 0.0
    delta = valor_cm - old_mean
    new_mean = old_mean + delta / n
    delta2 = valor_cm - new_mean
    new_m2 = (perfil.m2_acum or 0.0) + delta * delta2

    perfil.n_mostres = n
    perfil.mitjana = round(new_mean, 3)
    perfil.m2_acum = new_m2
    perfil.desviacio = round((new_m2 / n) ** 0.5, 3) if n > 1 else 0.0
    perfil.darrera_actualitzacio = timezone.now()
    perfil.save()

    return perfil


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS PRIVATS
# ─────────────────────────────────────────────────────────────────────────────

def _load_grading_rules(rule_set_id: int) -> dict:
    """Retorna {pom_id: rule_obj} per al RuleSet donat."""
    try:
        from fhort.pom.models import GradingRule
        return {r.pom_id: r for r in GradingRule.objects.filter(
            rule_set_id=rule_set_id, is_active=True
        )}
    except Exception as e:
        logger.warning(f"No s'han pogut carregar GradingRules: {e}")
        return {}


def _load_grading_exceptions(rule_set_id: int) -> dict:
    """Retorna {(pom_id, size_label): exc_obj}."""
    try:
        from fhort.pom.models import GradingException
        return {
            (e.pom_id, e.size_label): {'value_cm': e.value_cm}
            for e in GradingException.objects.filter(
                rule_set_id=rule_set_id, is_active=True
            )
        }
    except Exception as e:
        logger.warning(f"No s'han pogut carregar GradingExceptions: {e}")
        return {}


def _load_base_measurements(model_id: int) -> dict:
    """Retorna {pom_id: base_value_cm}."""
    try:
        from fhort.pom.models import BaseMeasurement
        return {
            bm.pom_id: bm.base_value_cm
            for bm in BaseMeasurement.objects.filter(
                model_id=model_id, is_active=True
            )
        }
    except Exception as e:
        logger.warning(f"No s'han pogut carregar BaseMeasurements: {e}")
        return {}


def _get_or_create_grading_version(sf):
    """Obté o crea la GradingVersion activa per al SizeFitting."""
    try:
        from fhort.pom.models import GradingVersion
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
        # Fallback si GradingVersion té una estructura diferent
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
            raise RuntimeError(f"No s'ha pogut obtenir/crear GradingVersion: {e}")


def _apply_rule(rule, base_val: float, steps: int, size_idx: int, base_idx: int):
    """Aplica la regla de grading i retorna (graded_value, grading_type_applied)."""
    grading_type = rule.grading_type
    increment = rule.increment_cm or 0

    if grading_type == 'LINEAR':
        return base_val + (steps * increment), 'LINEAR'

    elif grading_type == 'STEP':
        # Per a talles grans (>= base + 2 passos), pot aplicar increment diferent
        increment_above = getattr(rule, 'increment_above_xl', None) or increment
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
):
    """Crea o actualitza un GradedSpec."""
    try:
        from fhort.pom.models import GradedSpec
        GradedSpec.objects.update_or_create(
            grading_version_id=grading_version_id,
            pom_id=pom_id,
            size_label=size_label,
            defaults={
                'graded_value_cm': graded_value_cm,
                'grading_type_applied': grading_type_applied,
                'increment_applied_cm': increment_applied_cm,
                'is_active': True,
            }
        )
    except Exception as e:
        logger.error(f"Error creant GradedSpec pom={pom_id} talla={size_label}: {e}")
        raise
