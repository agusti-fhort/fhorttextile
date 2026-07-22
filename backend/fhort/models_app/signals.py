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
    Genera sequencial + codi_intern {CUST}-{YY}-{TT}-{NNNN} en crear un Model nou.

    El prefix i l'abast de la seqüència vénen del CUSTOMER (helper customer_code_for),
    amb fallback al self-customer del tenant — ja NO depèn de codi_client ni de cap
    hardcode. Si el caller ja ha fixat codi_intern (p.ex. el wizard, que computa el seu
    propi codi i sequencial), el signal no hi toca res.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return

    if sender is not Model:
        return

    if instance.pk:  # Already exists, do not regenerate the code
        return

    # El caller ja mana el codi (i el seu sequencial) → no interferir.
    if getattr(instance, 'codi_intern', None):
        return

    if not getattr(instance, 'any', None) or not getattr(instance, 'temporada', None):
        return

    from fhort.models_app.services import resolve_customer_for, customer_code_for

    # Assigna el self-customer si no n'hi ha d'explícit: així la fila queda coherent
    # (customer_id no queda null quan existeix self-customer) i la seqüència s'escopa bé.
    if not getattr(instance, 'customer_id', None):
        cust = resolve_customer_for(instance)
        if cust is not None:
            instance.customer = cust

    client_code = customer_code_for(instance)

    # MAX sequencial escopat per customer_id (Pas 4/1b) + any + temporada.
    from django.db import connection
    with connection.cursor() as cursor:
        if getattr(instance, 'customer_id', None):
            cursor.execute(
                'SELECT MAX(sequencial) FROM models_app_model '
                'WHERE customer_id = %s AND "any" = %s AND temporada = %s',
                [instance.customer_id, instance.any, instance.temporada])
        else:
            # Cas degradat (sense self-customer sembrat encara): escopa pels orfes.
            cursor.execute(
                'SELECT MAX(sequencial) FROM models_app_model '
                'WHERE customer_id IS NULL AND "any" = %s AND temporada = %s',
                [instance.any, instance.temporada])
        row = cursor.fetchone()

    next_seq = 1 if (not row or row[0] is None) else int(row[0]) + 1

    year2 = str(instance.any)[-2:].zfill(2)
    seq4 = str(next_seq).zfill(4)

    instance.sequencial = next_seq
    # codi_tenant = còpia denormalitzada del codi de customer (només si no ve fixat).
    if not getattr(instance, 'codi_tenant', None):
        instance.codi_tenant = client_code
    instance.codi_intern = f"{client_code}-{year2}-{instance.temporada}-{seq4}"


@receiver(post_save)
def sync_size_fitting(sender, instance, created, **kwargs):
    """
    Automatically create the Size & Fitting when a new Model is created.
    Configuration fields (garment_type, size_system, etc.) are NOT duplicated
    on the SF: they live on the Model and are accessed via the FK sf.model.X.

    creat_per is a non-null PROTECT FK, so we resolve an actor from the model's
    own metadata: responsable → created_by → any UserProfile (last resort). The
    SF is created ALWAYS (a model sembrat sense responsable is the normal
    onboarding case for any new client; skipping the SF left the measurement /
    grading surface mute — the universal hole B2). Only a tenant with zero
    UserProfiles can't satisfy PROTECT; there we log and skip, never crash model
    creation.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return

    if sender is not Model:
        return

    if not created:
        return

    try:
        from fhort.fitting.models import SizeFitting
        if SizeFitting.objects.filter(model=instance).exists():
            return
        # Actor: responsable → created_by → primer perfil (tots són UserProfile,
        # igual que creat_per). Sense cap perfil al tenant, no es pot satisfer PROTECT.
        actor_id = instance.responsable_id or instance.created_by_id
        if actor_id is None:
            from fhort.accounts.models import UserProfile
            first = UserProfile.objects.first()
            actor_id = first.id if first else None
        if actor_id is None:
            import logging
            logging.getLogger(__name__).warning(
                f"No UserProfile available to create SF for {instance}"
            )
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
            creat_per_id=actor_id,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not create SF for {instance}: {e}")


@receiver(post_save)
def recompute_import_watchpoint(sender, instance, **kwargs):
    """F3 — Watchpoint d'import VIU: en desar un Model, recalcula quins camps de configuració
    falten i actualitza/resol el Watchpoint d'import obert (task IS NULL + dades not null).

    NO crea Watchpoints aquí (la creació viu a commit_import) ni re-desa el Model: només toca
    el Watchpoint via queryset .update() → cap recursió de post_save. Idempotent.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return
    if sender is not Model:
        return

    from fhort.models_app.models import Watchpoint
    from fhort.models_app.services import model_config_missing, config_missing_text

    open_wps = Watchpoint.objects.filter(
        model_id=instance.pk, task__isnull=True, dades__isnull=False, estat='open')
    if not open_wps.exists():
        return

    missing = model_config_missing(instance)
    if missing:
        open_wps.update(dades=missing, text=config_missing_text(missing))
    else:
        from django.utils import timezone
        open_wps.update(dades=[], text=config_missing_text([]),
                        estat='resolved', resolved_at=timezone.now())


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

    from fhort.models_app.models import MeasurementChangeLog

    # B1 (PRINCIPI DEL SOROLL, 2026-07-22) — LA PODA ES REGISTRA.
    # Una desactivació no canvia cap valor, i fins ara queia pels dos filtres de sota
    # (valor NULL → return; valor igual → return): desapareixia una mesura del model
    # sense deixar rastre enlloc. El log és la memòria d'auditoria del model, i el
    # patrimoni que s'esborra hi ha de constar.
    #
    # Gated per `_desactivat`, marca EXPLÍCITA que posa qui poda: no es registra cap
    # toggle d'is_active fet de passada per una altra raó (la promesa del docstring es
    # manté per a tota la resta).
    if getattr(instance, '_desactivat', False) and not created:
        MeasurementChangeLog.objects.create(
            model=instance.model,
            pom=instance.pom,
            base_measurement=instance,
            valor_anterior=instance.base_value_cm,
            # `valor_nou` no és nullable i la poda no canvia el valor: 0.0 vol dir
            # «aquesta mesura ja no compta per al model». El motiu ho explicita.
            valor_nou=0.0,
            context=_ORIGEN_TO_CONTEXT.get(instance.origen, (instance.origen or '').lower()),
            created_by=(getattr(instance, '_changed_by', None)
                        or getattr(instance, 'created_by', None)),
            motiu=getattr(instance, '_motiu', '') or 'desactivacio',
        )
        return

    # Materialització família→item: una fila sense valor (base_value_cm=None, p.ex. origen='TEMPLATE')
    # NO és un canvi de mesura → no genera log. Quan rebi un valor real (None→x) sí es registrarà.
    if instance.base_value_cm is None:
        return

    old_value = getattr(instance, '_old_value', None)
    if not created and old_value == instance.base_value_cm:
        return  # value unchanged → nothing to log

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
