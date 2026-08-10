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
        # Els EXTERN (federació) conserven el sequencial del Brand, que viu en un altre espai
        # de numeració: excloure'ls del MAX perquè no enverinin el terra local (paritat amb
        # _real_max_seq de services.py; tanca el residual del signal vist a l'assaig).
        if getattr(instance, 'customer_id', None):
            cursor.execute(
                'SELECT MAX(sequencial) FROM models_app_model '
                "WHERE customer_id = %s AND \"any\" = %s AND temporada = %s AND origen <> 'EXTERN'",
                [instance.customer_id, instance.any, instance.temporada])
        else:
            # Cas degradat (sense self-customer sembrat encara): escopa pels orfes.
            cursor.execute(
                'SELECT MAX(sequencial) FROM models_app_model '
                "WHERE customer_id IS NULL AND \"any\" = %s AND temporada = %s AND origen <> 'EXTERN'",
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
    # Sprint B (2026-07-27) — sense aquesta entrada el context queia al fallback `origen.lower()`
    # (:273). El resultat hi coincidiria per casualitat ('copied'), però el mapa és la font
    # declarada del vocabulari del log i un origen viu no hi ha de faltar.
    'COPIED': 'copied',
    # C3/C (2026-08-02) — EL VALOR QUE DISTINGEIX UNA PRESA D'UNA DERIVACIÓ. Sense ell, una
    # auditoria exterior↔folre no pot saber si el folre el va mesurar algú o el va moure el
    # sistema en corregir la seva germana: es compara amb ella mateixa i sempre dona verd.
    # És l'entrada del REGISTRE la que ho ha de dir, perquè l'`origen` de la fila el
    # sobreescriu el canvi següent i aquesta taula és append-only.
    'DERIVAT': 'derivat',
    # C3/C — ELS QUATRE QUE FALTAVEN. Cap d'ells estava mapat i tots quatre queien al fallback
    # silenciós `origen.lower()`: el mapa deia ser «la font declarada del vocabulari del log» i
    # n'hi havia DOS vivint al registre de staging per la porta del darrere ('checked' ×17,
    # 'item_standard' ×2, comptats el 02/08). El valor resultant hi coincideix —el fallback fa
    # exactament el mateix `.lower()`— o sigui que això no canvia ni una fila existent; el que
    # canvia és que el vocabulari torna a estar declarat en un sol lloc.
    'TEMPLATE': 'template',
    'CHECKED': 'checked',
    'ITEM_STANDARD': 'item_standard',
    'FEDERAT': 'federat',
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
            # FASE_3/C1-ins — els DOS EIXOS surten de la `instance`, que ÉS la
            # `BaseMeasurement` podada. V. la nota llarga del log de canvi de valor, més
            # avall: aquí el motiu és el mateix i és més urgent, perquè una poda mal
            # atribuïda diu que s'ha esborrat una mesura que segueix viva.
            capa=instance.capa,
            instancia=instance.instancia,
            # SET-2/T5 — el garment es COPIA, igual que els altres dos eixos i pel mateix
            # motiu, que aquí és el més urgent de tots: aquesta taula és APPEND-ONLY i NO té
            # unicitat, o sigui que una fila escrita sense l'eix no es pot corregir després.
            # Una poda mal atribuïda diria que s'ha esborrat una mesura d'una peça que
            # segueix viva. El log no ha d'endevinar res: ha de copiar.
            garment=instance.garment,
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

    # 🚨 FASE_3/C1-ins — **AQUÍ ES TANCA EL FORAT QUE ARROSSEGA DES DE L'ONADA 1.**
    #
    # Aquest signal és l'ÚNIC escriptor automàtic del log, i fins avui no estampava cap dels
    # dos eixos: les files queien als defaults ('exterior', ''). Amb dues germanes vives, les
    # dues preses aterraven a la mateixa clau i `base_stages_view` —que és el node del pin—
    # arrossegava el valor d'una per la fila de l'altra: una base que aquella germana no ha
    # tingut mai. Els lectors ja s'havien adaptat a FASE_2; el que quedava era que l'escriptor
    # digués la veritat.
    #
    # I aquesta taula és APPEND-ONLY: una fila escrita amb l'eix equivocat NO es pot corregir
    # després. Per això no podia esperar a C4-ins.
    #
    # Els dos valors surten de la `instance` —que ÉS la `BaseMeasurement` que ha canviat—, no
    # de cap literal: el log no ha d'endevinar res, ha de copiar.
    MeasurementChangeLog.objects.create(
        model=instance.model,
        pom=instance.pom,
        capa=instance.capa,
        instancia=instance.instancia,
        # SET-2/T5 — el tercer eix, copiat de la `instance` com els altres dos. Append-only
        # i sense unicitat: sense això, el lector no podrà dir MAI de quina peça parlava un
        # canvi ja registrat, i la pèrdua és irreversible.
        garment=instance.garment,
        base_measurement=instance,
        valor_anterior=old_value,
        valor_nou=instance.base_value_cm,
        # C3/C — la germana de :297 protegia contra `origen` nul i aquesta no: feia
        # `instance.origen.lower()` pelat, que amb un NULL hauria petat amb AttributeError dins
        # d'un signal. Avui és inaccessible (la columna és NOT NULL amb default 'STANDARD'),
        # però dues línies que fan la mateixa feina no poden dir coses diferents.
        context=_ORIGEN_TO_CONTEXT.get(instance.origen, (instance.origen or '').lower()),
        created_by=changed_by,
        fitting_ref=fitting_ref,
        motiu=motiu,
        fora_de_tolerancia=fora_de_tolerancia,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RETORN-2 · el disparador MARCA → ESTUDI (prioritat i data_objectiu)
# ─────────────────────────────────────────────────────────────────────────────
#
# PER QUÈ UN SIGNAL I NO EL SERIALIZER. `prioritat` i `data_objectiu` no tenen un punt únic
# d'escriptura: hi arriben pel PATCH genèric de `ModelViewSet` (`ModelDetailSerializer` amb
# `fields='__all__'`), pel wizard de creació (`models_app/views.py:840,917`) i per qualsevol
# rutina que desi el model. Enganxar el sync al serializer cobriria una porta i deixaria les
# altres callades — exactament la forma de divergència que el docstring de `federation_service`
# descriu per a les dues boques del traspàs. El `pre_save`/`post_save` és l'ÚNIC lloc pel qual
# passen totes.
#
# LÍMIT DECLARAT (no és un forat, és la forma dels signals): un `queryset.update()` no dispara
# senyals i, per tant, no sincronitza. Avui cap escriptor de `prioritat`/`data_objectiu` ho fa
# per aquesta via; si algun dia n'hi ha un, ha de cridar `sync_estat` ell mateix.

#: Els dos camps que la MARCA mana i que viatgen a camps reals del bessó de l'estudi.
_CAMPS_QUE_MANA_LA_MARCA = ('prioritat', 'data_objectiu')


@receiver(pre_save)
def _snapshot_encarrec(sender, instance, **kwargs):
    """Desa els valors ANTERIORS de l'encàrrec per poder comparar-los al post_save.

    Només per a models JA assignats a un estudi: sense assignació no hi ha bessó a qui
    parlar i la consulta extra no la paga ningú.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return
    if sender is not Model or not instance.pk or not getattr(instance, 'studio_assignat', ''):
        return
    anterior = (Model.objects.filter(pk=instance.pk)
                .values(*_CAMPS_QUE_MANA_LA_MARCA).first())
    instance._encarrec_anterior = anterior


@receiver(post_save)
def sync_encarrec_a_l_estudi(sender, instance, **kwargs):
    """En canviar prioritat o data_objectiu a la MARCA, escriu-les al bessó de l'ESTUDI.

    La marca MANA en aquests dos camps (decisió del Patró C): no es comparen amb el que hi
    hagi a l'altra banda ni es negocia res — s'hi escriuen. El sync és no-fatal per construcció
    (`sync_estat_segur`): desar un model no pot dependre de si el pont està obert.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return
    if sender is not Model or not getattr(instance, 'studio_assignat', ''):
        return

    anterior = getattr(instance, '_encarrec_anterior', None)
    instance._encarrec_anterior = None
    if anterior is not None and all(
            anterior.get(c) == getattr(instance, c, None) for c in _CAMPS_QUE_MANA_LA_MARCA):
        return   # res de l'encàrrec ha canviat: no es molesta l'altra casa

    from fhort.tenants.federation_service import SENTIT_PRIORITAT, sync_estat_segur
    sync_estat_segur(instance, SENTIT_PRIORITAT)
