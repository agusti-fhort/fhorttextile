"""
models_app/signals.py — Django signals for the Model.
Equivalent to Frappe's Server Scripts:
  - before_insert: generates code + sequential number
  - after_save: syncs Size & Fitting
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


def _get_model_class():
    from fhort.models_app.models import Model
    return Model


@receiver(pre_save)
def generate_model_code(sender, instance, **kwargs):
    """
    Generate the sequential number and code {CLI}-{YY}-{TT}-{NNNN} when creating a new Model.
    Equivalent to the Server Script 'Model - Before Insert · Codificació'.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return

    if sender is not Model:
        return

    if instance.pk:  # Already exists, do not regenerate the code
        return

    # The real Model has no 'client' field (FK); it uses codi_client (CharField) directly.
    # Defensive: if fields are missing or empty, exit without doing anything.
    client_id = getattr(instance, 'client_id', None)
    client_code_raw = getattr(instance, 'codi_client', None)
    if not (client_id or client_code_raw) or not getattr(instance, 'any', None) or not getattr(instance, 'temporada', None):
        return

    # Client code: from the direct field (if present), or via the client FK (if the schema adds it later)
    client_code = client_code_raw
    if not client_code and client_id:
        try:
            from fhort.accounts.models import Client
            client = Client.objects.get(pk=client_id)
            client_code = getattr(client, 'codi_client', None) or getattr(client, 'code', None)
            if not client_code:
                client_code = str(client)[:3].upper()
        except Exception:
            client_code = None

    if not client_code:
        return

    client_code = client_code.strip().upper()

    # MAX sequential per (codi_client, any, temporada)
    # If a future schema adds a 'client' FK, migrate to client_id; for now
    # we use codi_client (CharField), which is the real business key on the Model.
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT MAX(sequencial)
            FROM models_app_model
            WHERE codi_client = %s
              AND "any" = %s
              AND temporada = %s
        """, [client_code, instance.any, instance.temporada])
        row = cursor.fetchone()

    next_seq = 1 if (not row or row[0] is None) else int(row[0]) + 1

    year2 = str(instance.any)[-2:].zfill(2)
    seq4 = str(next_seq).zfill(4)

    instance.sequencial = next_seq
    # The Model has no 'codi' field (it has 'codi_intern'). Generate codi_intern if empty
    # — if the user already provided it, do not overwrite it.
    if not getattr(instance, 'codi_intern', None):
        instance.codi_intern = f"{client_code}-{year2}-{instance.temporada}-{seq4}"


@receiver(post_save)
def sync_size_fitting(sender, instance, created, **kwargs):
    """
    Automatically create the Size & Fitting when a new Model is created.
    Configuration fields (garment_type, size_system, etc.) are NOT duplicated
    on the SF: they live on the Model and are accessed via the FK sf.model.X.

    Skip if Model.responsable is None (creat_per is required + PROTECT
    on SizeFitting). In that case the SF can be created manually later.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return

    if sender is not Model:
        return

    if not created:
        return

    if not instance.responsable_id:
        return  # We cannot create an SF without creat_per

    try:
        from fhort.fitting.models import SizeFitting
        if SizeFitting.objects.filter(model=instance).exists():
            return
        number = 1
        code = f"{instance.codi_intern}-SF{number}"
        SizeFitting.objects.create(
            model=instance,
            numero=number,
            codi=code,
            tipus='Proto',
            estat='Pendent',
            base_tancada=False,
            creat_per_id=instance.responsable_id,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not create SF for {instance}: {e}")


@receiver(post_save)
def update_last_activity(sender, instance, **kwargs):
    """
    On every Model save, update darrera_activitat = now().
    Uses queryset.update() to bypass signals → no infinite recursion.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return

    if sender is not Model:
        return

    from django.utils import timezone
    Model.objects.filter(pk=instance.pk).update(darrera_activitat=timezone.now())


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 3 / F1 — Append-only measurement change log
# ─────────────────────────────────────────────────────────────────────────────

# Maps BaseMeasurement.origen → MeasurementChangeLog.context.
_ORIGEN_TO_CONTEXT = {
    'IMPORTED': 'import',
    'MANUAL': 'manual',
    'FITTED': 'fitting',
    'CALCULATED': 'calculated',
    'STANDARD': 'standard',
}


def _get_base_measurement_class():
    from fhort.models_app.models import BaseMeasurement
    return BaseMeasurement


@receiver(pre_save)
def capture_old_measurement_value(sender, instance, **kwargs):
    """Stash the persisted base_value_cm so post_save can compare and log the delta."""
    try:
        BaseMeasurement = _get_base_measurement_class()
    except Exception:
        return
    if sender is not BaseMeasurement:
        return

    if instance.pk:
        old = BaseMeasurement.objects.filter(pk=instance.pk).values_list(
            'base_value_cm', flat=True
        ).first()
        instance._old_value = old
    else:
        instance._old_value = None


@receiver(post_save)
def log_measurement_change(sender, instance, created, raw=False, **kwargs):
    """
    Record an append-only MeasurementChangeLog entry on every value change.

    Only base_value_cm changes (or creations) are logged — reorders, is_active
    toggles or nom_fitxa edits do not produce an entry. created_by is resolved by
    priority: instance._changed_by (set on the request) → instance.created_by → null.
    """
    try:
        BaseMeasurement = _get_base_measurement_class()
    except Exception:
        return
    if sender is not BaseMeasurement:
        return
    if raw:  # loaddata / fixtures
        return

    # Materialització família→item: una fila sense valor (base_value_cm=None, p.ex. origen='TEMPLATE')
    # NO és un canvi de mesura → no genera log. Quan rebi un valor real (None→x) sí es registrarà.
    if instance.base_value_cm is None:
        return

    old_value = getattr(instance, '_old_value', None)
    if not created and old_value == instance.base_value_cm:
        return  # value unchanged → nothing to log

    from fhort.models_app.models import MeasurementChangeLog

    changed_by = getattr(instance, '_changed_by', None) or getattr(instance, 'created_by', None)

    # Sprint 5B.3: the fitting CLOSE may attach optional context before saving the
    # BaseMeasurement so the log row is traceable to the fitting that caused it.
    fitting_ref = getattr(instance, '_fitting_ref', None)
    motiu = getattr(instance, '_motiu', '') or ''
    fora_de_tolerancia = getattr(instance, '_fora_de_tolerancia', False) or False

    MeasurementChangeLog.objects.create(
        model=instance.model,
        pom=instance.pom,
        base_measurement=instance,
        valor_anterior=old_value,
        valor_nou=instance.base_value_cm,
        context=_ORIGEN_TO_CONTEXT.get(instance.origen, instance.origen.lower()),
        created_by=changed_by,
        fitting_ref=fitting_ref,
        motiu=motiu,
        fora_de_tolerancia=fora_de_tolerancia,
    )
