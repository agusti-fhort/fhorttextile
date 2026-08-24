"""Sprint C: màquina d'estats del kanban del tècnic + timer server-side."""
import logging

from django.db import connection, transaction
from django.utils import timezone
from .models import ModelTask, TimerEntrada, TaskTransition

logger = logging.getLogger(__name__)

#: J-bis · LA MARCA DEL CAMÍ DE CONSULTA, en una constant i no en un literal repartit. És el
#: `auto` amb què surt del sistema una sortida sense escriptura, i alhora **la clau que obre
#: l'única transició guardada de la màquina** (v. `ALLOWED` i `transition_task`). Escrit dues
#: vegades, el dia que canviés només en canviaria una i el guard deixaria de tancar.
AUTO_CONSULTA = 'consulta_sense_escriptura'

# Transicions permeses (from -> {to})
ALLOWED = {
    'Pending':    {'InProgress'},
    # ⚠️ `Paused → Done` NO hi és, i és una DECISIÓ (Patró C · Agus · 28/07, fixada a
    # `test_stop_encadenat`): la màquina d'estats no es toca i el Stop sobre una tasca pausada
    # és play+stop ENCADENAT, dues transicions legals en un sol gest d'usuari.
    'Paused':     {'InProgress'},
    # 🔒 J-bis · `InProgress → Pending` HI ÉS, PERÒ NO ÉS UNA TRANSICIÓ HUMANA (decisió d'Agus).
    #
    # És **l'única entrada guardada d'aquesta taula**: ser-hi la fa POSSIBLE, no PERMESA. El
    # guard viu a `transition_task` i exigeix les dues coses alhora —marca `auto=AUTO_CONSULTA`
    # i tram SENSE escriptura—, o sigui que només la pot fer servir el camí de tornada d'una
    # consulta. Qualsevol altre cridador —un botó, un gest, una rutina— rep el mateix
    # `TransitionError` que rebia abans que existís.
    #
    # PER QUÈ CALIA. Sense ella, una tasca `Pending` on algú entrava a MIRAR i sortia sense tocar
    # res quedava `Paused`: el Pla deia «pausada» d'una feina que **ningú no ha començat mai**, i
    # `started_at` es quedava posat. La tornada de J era exacta per a `Paused` i mentidera per a
    # `Pending`; ara ho és per a totes dues.
    #
    # ⚠️ LA MÀQUINA D'ESTATS HUMANA NO CANVIA: cap botó nou, cap gest nou, cap camí d'usuari nou.
    'InProgress': {'Paused', 'Done', 'Pending'},
    'Done':       {'InProgress'},   # reobertura = rectificació
}


def _open_timer(task, profile, origen=TimerEntrada.ORIGEN_MESURAT):
    # Invariant ≤1 timer obert per tasca: tanca qualsevol obert previ abans d'obrir-ne un de nou
    # (defensa contra fuites; en condicions normals no n'hi ha cap d'obert en entrar a InProgress).
    #
    # T3 — `origen` viatja des de la porta: un tram DECLARAT neix declarat, no es converteix
    # després. El default deixa tots els camins d'abans exactament com estaven.
    _close_open_timer(task)
    # J — NEIX DECLARANT-SE JUTJABLE (`consulta=False`). No és el veredicte: és la marca que diu
    # que aquest tram ha nascut sota el règim nou i que, per tant, al tancament se li POT
    # preguntar si s'hi ha escrit. Els trams que ja eren oberts el dia del desplegament tenen
    # `None` i no se'ls pregunta mai: van néixer sense la marca d'escriptura i condemnar-los per
    # no tenir-la seria inventar-se que no s'hi va treballar.
    return TimerEntrada.objects.create(model_task=task, tecnic=profile,
                                       inici=timezone.now(), actiu=True, origen=origen,
                                       consulta=False)


def _close_open_timer(task):
    # Tanca TOTS els timers oberts de la tasca (no només .first()): si se n'havien acumulat 2+
    # per una fuita, abans en quedava un de penjat permanent. Cada timer tanca amb la SEVA durada.
    now = timezone.now()
    for t in TimerEntrada.objects.filter(model_task=task, fi__isnull=True, actiu=True):
        t.fi = now
        t.minuts = max(0, int((now - t.inici).total_seconds() // 60))
        t.actiu = False
        camps = ['fi', 'minuts', 'actiu']
        # J · EL VEREDICTE, I ES DÓNA AQUÍ PERQUÈ ÉS QUAN JA ES POT DONAR. Durant el tram la
        # pregunta encara no té resposta —qui no ha escrit ENCARA pot escriure—; al tancament sí.
        #
        # Només es jutja el que és jutjable (`consulta is False`, o sigui nascut sota el règim
        # nou). `None` es queda `None`: és l'històric i els trams que el desplegament va enxampar
        # oberts, i han de comptar exactament com sempre.
        #
        # ⚠️ EL CRITERI NO ÉS LA DURADA, i no pot ser-ho: «no hi ha hagut sessió» no vol dir «ha
        # durat poc» (decisió d'Agus, `ModelSheet.jsx`). Un tram de dues hores mirant sense tocar
        # res és una consulta, i un de dos minuts amb una mesura escrita és feina.
        if t.consulta is False and t.escriptura_at is None:
            t.consulta = True
            camps.append('consulta')
        t.save(update_fields=camps)


def te_paret_albara(task):
    """La tasca té línia en un albarà EMÈS? (D-5 · v2)

    Punt únic: la fan servir `transition_task` —que la converteix en rebuig de la reobertura— i
    el batec d'escriptura, que ha de poder DIR-LA sense intentar la transició. Escrita dues
    vegades, el dia que el criteri canviï (avui `ISSUED`/`INVOICED`) només en canviaria una.
    """
    return task.delivery_note_lines.filter(
        delivery_note__status__in=['ISSUED', 'INVOICED']).exists()


def hi_ha_volta_posterior(task):
    """M3 · FIT-11 — hi ha una VOLTA POSTERIOR a la d'aquesta tasca?

    🔒 **OBRIR UNA RONDA NOVA ELIMINA L'OPCIÓ DE RECTIFICAR L'ANTERIOR** (llei dura d'Agus,
    24/08). Rectificar és tornar a entrar en una feina que ja s'havia donat per acabada, i això
    només té sentit sobre la **darrera** volta: si el PM ja n'ha obert una de nova, la manera de
    refer aquella feina és la volta nova —que té identitat, genealogia (`mare`) i comptador
    propis—, no reobrir una tasca de dues voltes enrere i deixar el rastre repartit entre les
    dues. FIT-2 segueix intacte per a la darrera volta: allà rectificar és legal i deixa nota.

    Dos casos, i el segon és el que fa que això no es pugui escriure amb un `seq__gt` i prou:

      · **La tasca TÉ volta** → n'hi ha de posterior si existeix una `Ronda` del model amb
        `seq` més gran. Directe.
      · **La tasca NO en té** (`ronda` NULL) → n'hi ha dues menes i **no es poden tractar
        igual**: l'històric anterior a la primera volta del model (feina llegada, que la
        prohibició de backfill d'M1-bis deixa NULL a posta) i la feina nascuda al BUIT entre
        dues voltes, que encara no n'ha vist cap de posterior. El que les separa és el TEMPS,
        que és el mateix criteri que `services_r.tasques_del_buit` fa servir per adoptar-les:
        és posterior tota volta **oberta després que la tasca es creés**.

    Retorna la `Ronda` posterior més antiga (per dir-la al missatge), o None.
    """
    from .models import Ronda

    ronda = getattr(task, 'ronda', None)
    qs = Ronda.objects.filter(model_id=task.model_id)
    if ronda is not None:
        qs = qs.filter(seq__gt=ronda.seq)
    else:
        qs = qs.filter(oberta_el__gt=task.created_at)
    return qs.order_by('seq').first()


def _log(task, frm, to, profile, auto=None, nota=None):
    # `auto` viatja fins al log perquè digui la veritat: null = gest del tècnic, slug = guard.
    # `nota` (M1 · FIT-2) és el CONTEXT del gest en text, quan n'hi ha: null a la immensa
    # majoria de transicions, que no tenen res a dir.
    TaskTransition.objects.create(model_task=task, from_status=frm, to_status=to, by=profile,
                                  auto=auto, nota=nota)


def _nota_reobertura_post_entrega(task):
    """M1 · FIT-2 — «reoberta després d'entrega de R{n}», o None si no s'escau.

    🔒 **EL SEGELL SEGUEIX SENT TOU.** Això NO és un guard: `Done→InProgress` era legal ahir i ho
    és avui, i aquesta funció no pot rebutjar res. L'única cosa que canvia és que el log deixa
    dit que aquella feina ja s'havia entregat —que és una conversa diferent de la paret DURA de
    l'albarà (`te_paret_albara`), que sí que refusa.

    Només parla quan la tasca pertany a una ronda amb entrega INFORMADA. Una tasca de la volta 1
    (`ronda` NULL, la implícita) o d'una volta que ningú no ha entregat no té res a rastrejar.
    La CARA d'aquest rastre —qui el veu i com— és M2; aquí només hi ha la dada.
    """
    ronda = getattr(task, 'ronda', None)
    if ronda is None:
        return None
    entrega = getattr(ronda, 'entrega', None)   # OneToOne invers: None si no n'hi ha
    if entrega is None:
        return None
    return f"reoberta després d'entrega de R{ronda.seq}"


def _aplica_exclusio_tecnic(profile, task):
    """D-6 — UN TÈCNIC, UN SOL TRAM OBERT. Punt únic per a TOTES les portes que li'n obren un.

    F1.5 va ancorar l'exclusió a QUI TREBALLA (`TimerEntrada.tecnic`) i no a qui la té assignada
    (`assignee` és planificació), i la va tancar a `transition_task`. Però el RELLEU no hi passa:
    `claim` i la branca de handoff d'`open-task` criden `traspassa_tram` sense cap transició —«el
    relleu no canvia l'estat»—, i `_open_timer` només tanca els trams D'AQUESTA TASCA. Un tècnic
    amb feina oberta que es quedava la tasca d'un altre acabava amb DOS trams oberts: el mateix
    mal que F1.5 va matar, viu per l'altra porta, i el temps tornava a ser imputable a dos llocs
    alhora (que és el que contamina `record_actual_time` i el Welford, D-3).

    Tanca els trams oberts del tècnic en QUALSEVOL altra tasca i pausa les que estaven En curs.
    La pausa va MARCADA (`auto='exclusio_inprogress'`): no és un gest del tècnic sobre aquella
    tasca —ell n'ha obert una altra i el sistema li ha tancat aquesta—, i sense la marca el log
    li atribuiria una pausa que no va fer.

    Retorna el pk de l'última tasca pausada (o None), per a qui vulgui dir-ho a la resposta.
    """
    paused_task_id = None
    obertes = (ModelTask.objects
               .filter(timers__tecnic=profile, timers__fi__isnull=True, timers__actiu=True)
               .exclude(pk=task.pk).distinct())
    for other in obertes:
        _close_open_timer(other)
        if other.status == 'InProgress':
            other.status = 'Paused'
            other.save(update_fields=['status', 'updated_at'])
            _log(other, 'InProgress', 'Paused', profile, auto='exclusio_inprogress')
        paused_task_id = other.pk
    return paused_task_id


class TransitionError(Exception):
    """Rebuig d'una transició de tasca.

    Porta un `code` opcional perquè la porta HTTP el pugui reenviar i el client sàpiga QUINA
    paret ha tocat. Sense `code` el rebuig és genèric i el client cau al missatge de sempre:
    afegir-ne un no obliga ningú a canviar res.
    """

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


def _is_off_recipe(task, work_order):
    """Un extra és off_recipe si el seu task_type NO és a la recepta congelada del WO ORDER.
    Al col·lector —o si la recepta encara no s'ha congelat (B4b)— res no és off_recipe: no
    hi ha base contra què comparar."""
    if work_order.kind != 'ORDER':
        return False
    codes = (work_order.recipe_snapshot or {}).get('task_codes')
    if not codes:
        return False
    return task.task_type.code not in codes


def _resolve_work_order(task, when):
    """Resol l'encàrrec (WorkOrder) d'una tasca segons la regla B4a. Retorna
    (work_order, off_recipe). (None, False) si no es pot resoldre —model sense customer, o
    col·lector del mes ja tancat— i llavors es deixa per al reconcile.

    Regla: si el model té un WO ORDER obert → aquell (off_recipe segons recepta); si no →
    col·lector (customer, mes de `when`), on tot és off_recipe=False."""
    from fhort.commerce.models import WorkOrder
    model = task.model
    if not model.customer_id:
        return None, False
    order_wo = (WorkOrder.objects.filter(model=model, kind='ORDER', status='OPEN')
                .order_by('-created_at').first())
    if order_wo is not None:
        return order_wo, _is_off_recipe(task, order_wo)
    period = when.strftime('%Y-%m')
    collector, created = WorkOrder.objects.get_or_create(
        customer_id=model.customer_id, kind='COLLECTOR', period=period,
        defaults={'origin': 'MANUAL'})
    if not created and collector.status == 'CLOSED':
        return None, False   # el col·lector del mes ja s'ha tancat → resolució manual/reconcile
    return collector, False


def assign_work_order(task, when):
    """Assigna l'encàrrec a una tasca si encara no en té (IDEMPOTENT). Reutilitzat pel hook
    (primera InProgress) i pel reconcile. Si la tasca ja té work_order, no fa res."""
    if task.work_order_id is not None:
        return
    work_order, off_recipe = _resolve_work_order(task, when)
    if work_order is None:
        return
    task.work_order = work_order
    task.off_recipe = off_recipe
    task.save(update_fields=['work_order', 'off_recipe', 'updated_at'])


def _emetre_meritacio(record, codi_client, now):
    """L'event a `public`. UN sol event per albarà — la unitat facturable és l'event
    (`backoffice/recurring_service.py:87` en fa el `.count()` del període)."""
    from fhort.models_app.models import Model
    from fhort.tasks.signals import model_consumption_started

    model_consumption_started.send(
        sender=Model,
        codi_client=codi_client,
        period=record.period,
        opaque_ref=record.opaque_ref,
        merited_at=now,
        # P4 — ACTOR: el tenant actiu que obre la tasca (qui merita).
        actor_schema=connection.schema_name,
    )


def _meritar_model(model, now):
    """Meritació d'un model SOL. El guard d'idempotència ÉS el `filter(pk=…, isnull=True)`."""
    from fhort.models_app.models import ConsumptionRecord, Model

    rows = Model.objects.filter(
        pk=model.pk, consumption_started_at__isnull=True
    ).update(consumption_started_at=now)
    if not rows:
        return
    record = ConsumptionRecord.objects.create(
        model=model,
        code_snapshot=model.codi_intern,
        name_snapshot=model.nom_prenda or '',
        period=now.strftime('%Y-%m'),
        merited_at=now,
    )
    _emetre_meritacio(record, model.customer.codi, now)


def _meritar_conjunt(model, now):
    """SET-1 · A3 — meritació d'un CONJUNT: **SET = 1 mèrit** (decisió 2 del sprint SET).

    Dues coses que han de passar SEMPRE juntes:

    1. **Totes les germanes reben `consumption_started_at`.** Sense això, les peces 02 i 03
       compleixen exactament el criteri de forat de `reconcile_consumption:74-83` (activitat de
       tasca + cap marca) i la propera execució les merita: set=3 amb retard. Aquest UPDATE és
       idempotent i es fa a cada arrencada, no només a la primera.
    2. **UN sol `ConsumptionRecord`, ancorat al SET**, amb `code_snapshot` = `codi_base`. És
       l'única forma que no fa mentir l'albarà: amb l'albarà penjat d'una peça, el client (que
       el veu — `models.py:861`) llegiria un codi intern `…-0834-01` en comptes del codi
       comercial del producte que ha comprat (decisió 1: «el client veu el model sencer»).

    El guard d'idempotència viu al SET, mateixa forma que el de model
    (`filter(pk=…, consumption_started_at__isnull=True).update(...)`): la transició del flag és
    la que decideix qui merita, i és atòmica.
    """
    from fhort.models_app.models import ConsumptionRecord, GarmentSet, Model

    gs_id = model.garment_set_id
    rows = GarmentSet.objects.filter(
        pk=gs_id, consumption_started_at__isnull=True
    ).update(consumption_started_at=now)

    # (1) sempre, hagi meritat ara o fa un mes: cap germana sense marca.
    Model.objects.filter(
        garment_set_id=gs_id, consumption_started_at__isnull=True
    ).update(consumption_started_at=now)

    if not rows:
        return   # el conjunt ja havia meritat: cap albarà nou, cap event nou.

    gs = GarmentSet.objects.get(pk=gs_id)
    record = ConsumptionRecord.objects.create(
        garment_set=gs,
        code_snapshot=gs.codi_base,
        name_snapshot=gs.nom_comercial or (model.nom_prenda or ''),
        period=now.strftime('%Y-%m'),
        merited_at=now,
    )
    _emetre_meritacio(record, model.customer.codi, now)


@transaction.atomic
def transition_task(task, to_status, profile, force=False, auto=None,
                    origen=TimerEntrada.ORIGEN_MESURAT):
    """Aplica una transició d'estat. Imposa 'una sola InProgress per tècnic' (global):
    en entrar a InProgress, pausa l'altra InProgress del mateix tècnic (tanca timer + log).
    Retorna dict amb la tasca i, si escau, la pausada automàticament.

    `force=True` salta NOMÉS el guard d'albarà (reobertura): reservat a rutines internes de
    migració que reprocessen històric (retype command). La porta d'usuari mai el passa.

    `auto` és la marca del guard que ha provocat la transició ('guard_30min', 'cron_40min'…).
    Només viatja al log: NO obre cap camí alternatiu ni salta cap validació. Els guards passen
    per aquesta mateixa porta i per les mateixes regles — cap màquina d'estats paral·lela."""
    frm = task.status
    if to_status not in ALLOWED.get(frm, set()):
        raise TransitionError(f'Transició no permesa: {frm} → {to_status}')

    # ── J-bis · EL GUARD DE L'ÚNICA TRANSICIÓ NO-HUMANA ──────────────────────────────────────
    #
    # `InProgress → Pending` és a `ALLOWED` perquè el camí de tornada d'una consulta la
    # necessita, i **només ell**. Les dues condicions es demanen ALHORA i cap de les dues és
    # decorativa:
    #
    #   (a) `auto=AUTO_CONSULTA` — diu QUI la demana. La llei del log ja separa el gest del
    #       tècnic (`auto` null) del que fa el sistema (slug); aquí aquell mateix camp és a més
    #       la clau. Un gest humà no en porta cap, i per tant no pot passar per aquí ni per
    #       error ni a posta.
    #   (b) el tram obert **sense `escriptura_at`** — diu QUE ÉS VERITAT. La marca sola seria una
    #       paraula: qualsevol cridador podria escriure-la. Això no es pot fingir des de fora,
    #       perquè només `batec_escriptura` estampa aquell camp i només quan hi ha hagut
    #       escriptura de debò.
    #
    # Sense les dues, el rebuig és **el mateix que abans que la transició existís**: qui la
    # cridi des d'un botó veurà exactament l'error de sempre.
    if frm == 'InProgress' and to_status == 'Pending':
        if auto != AUTO_CONSULTA:
            raise TransitionError(f'Transició no permesa: {frm} → {to_status}')
        if TimerEntrada.objects.filter(model_task=task, fi__isnull=True, actiu=True,
                                       escriptura_at__isnull=False).exists():
            raise TransitionError(f'Transició no permesa: {frm} → {to_status}')

    # v2 — guard de reobertura: una tasca amb línia en albarà EMÈS (ISSUED/INVOICED) no es pot
    # reobrir (rectificació = extra nova que genera línia al proper albarà). DRAFT NO bloqueja
    # (encara es pot desfer esborrant el DRAFT). Limitat estrictament a Done→InProgress.
    if not force and frm == 'Done' and to_status == 'InProgress':
        # M3 · FIT-11 — LA PARET DE LA VOLTA. Va ABANS de la de l'albarà a posta: quan totes
        # dues hi són, el motiu que el tècnic ha de llegir és el que té sortida («fes-ho a la
        # volta nova»), no el que no en té. `force` la salta igual que l'altra: les rutines
        # internes que reprocessen històric no estan rectificant res.
        posterior = hi_ha_volta_posterior(task)
        if posterior is not None:
            raise TransitionError(
                f'Aquesta feina és d\'una volta anterior: la R{posterior.seq} ja està oberta. '
                f'El que s\'ha de refer es fa a la volta nova, no reobrint la vella.',
                code='volta_posterior')
        if te_paret_albara(task):
            # El `code` és el que fa que el client pugui dir el MOTIU. Sense ell, aquest rebuig
            # arribava com un 409 mut i el tècnic veia «no s'ha pogut obrir la tasca» sense saber
            # que la paret és l'albarà: 7 intents en dues hores sobre el mateix model (188), tots
            # amb el mateix toast (v. DIAGNOSI_CICLE_TASCA_COMPLET §M-2).
            raise TransitionError('No es pot reobrir una tasca ja albaranada (albarà emès).',
                                  code='tasca_albaranada')

    paused_task_id = None
    now = timezone.now()

    if to_status == 'InProgress':
        # F1.5 · D-6 — Regla: una sola InProgress per tècnic (a qualsevol model), i ara ancorada
        # a QUI TREBALLA i no a qui la té assignada.
        #
        # `assignee` és un camp de PLANIFICACIÓ; el rellotge s'ancora a `TimerEntrada.tecnic`, que
        # és qui hi és de debò. I com que aquesta funció només escriu `assignee` quan és `None`
        # (unes línies més avall), els dos eixos divergien sols: sempre que actor ≠ assignat, la
        # consulta d'exclusió no veia la tasca oberta i el tècnic n'acabava amb dues alhora.
        # No és teòric — hi ha el cas a la BD: timers 116 i 117, tècnic 1, 24/06, solapats
        # 122 min i 0 min (§Q5.2 de la diagnosi del cicle).
        #
        # Mirant els TRAMS OBERTS la invariant torna a ser certa per construcció: el que tanca
        # l'exclusió és exactament el que el rellotge considera «obert».
        # V3 (06/08) — el bucle viu ara a `_aplica_exclusio_tecnic`, perquè el RELLEU també hi
        # ha de passar i tenir-lo escrit dues vegades hauria deixat divergir les dues portes.
        paused_task_id = _aplica_exclusio_tecnic(profile, task)
        # Obrir timer de la tasca que entra (T3: `origen` el decideix qui obre la porta)
        _open_timer(task, profile, origen=origen)
        if task.started_at is None:
            task.started_at = now
        if frm == 'Done':
            # Reobrir torna la tasca a oberta; conserva started_at, neteja finished_at
            task.finished_at = None

    elif frm == 'InProgress' and to_status in ('Paused', 'Done', 'Pending'):
        _close_open_timer(task)
        if to_status == 'Done':
            task.finished_at = now
        if to_status == 'Pending':
            # «EXACTAMENT ON ERA» INCLOU EL `started_at`. Una `Pending` és, per definició, una
            # feina que ningú no ha començat mai: `started_at` era `None` abans d'entrar-hi —el
            # va posar aquesta mateixa entrada, tres línies més amunt— i deixar-l'hi faria una
            # tasca «no començada» amb data d'inici. Es torna enrere sencer o no es torna.
            task.started_at = None

    # Si entra una tasca sense assignee, l'assignem al tècnic que l'executa
    if to_status == 'InProgress' and task.assignee_id is None:
        task.assignee = profile

    task.status = to_status
    task.save()
    # M1 · FIT-2 — el rastre es calcula ABANS del log i només per a la reobertura: és l'únic
    # moment en què la frase té sentit i l'únic en què la tasca pot estar entregada.
    nota = (_nota_reobertura_post_entrega(task)
            if (frm == 'Done' and to_status == 'InProgress') else None)
    _log(task, frm, to_status, profile, auto=auto, nota=nota)

    # Pas 5B-fix: arrencar la PRIMERA tasca treu el model de Pending → Dev.
    if to_status == 'InProgress':
        from fhort.models_app.models import Model

        # MÓN TÈCNIC (sagrat): la fase passa a Dev com avui, fora de tota lògica de facturació.
        Model.objects.filter(pk=task.model_id, fase_actual='Pending').update(fase_actual='Dev')

        # F1.4 · D-10 — AQUÍ hi havia la MERITACIÓ SaaS, i ja no hi és.
        #
        # El fet facturable era «algú ha obert una porta»: la primera `→InProgress` de qualsevol
        # tasca meritava el model, emetia l'event a `public` i reancorava el pla. Tocar una porta
        # tres segons per error facturava (verificat: els 21 ConsumptionRecord del tenant tenien
        # `merited_at == started_at` de la primera tasca).
        #
        # Ara el fet facturable és «algú hi ha ESCRIT»: el gallet viu a
        # `services_batec.batec_escriptura`, que és l'únic lloc que sap que hi ha hagut feina
        # real i no només una pestanya oberta. Les funcions `_meritar_model` / `_meritar_conjunt`
        # / `_emetre_meritacio` NO s'han tocat: han canviat de gallet, no de disseny, i el guard
        # d'idempotència segueix sent el seu `UPDATE ... WHERE consumption_started_at IS NULL`.
        #
        # El que ES QUEDA aquí és el món tècnic (`fase_actual='Dev'`, a dalt) i l'encàrrec
        # (`assign_work_order`, a sota): ni l'un ni l'altre són facturació SaaS.

        # B4a — ENCÀRREC (mòdul comercial, studio→tercers). Món separat: savepoint propi, i
        # s'intenta encara que la meritació hagi fallat (són independents). Assigna work_order
        # a CADA primera InProgress de tasca (no només la del model): el col·lector és
        # per-model×mes però l'assignació és per-tasca. Idempotent.
        try:
            with transaction.atomic():
                assign_work_order(task, now)
        except Exception:
            logger.exception("assignacio work_order fallida model=%s task=%s", task.model_id, task.pk)
            # NO re-raise: el forat d'encàrrec es reconcilia amb `reconcile_work_orders`.

    if to_status == 'Done':
        # Sprint I: alimentar l'estadística Welford amb el temps real (timers ja tancats;
        # defensiu, no trenca el tancament de la tasca)
        from .services_i import record_actual_time
        record_actual_time(task)

    # RETORN-2 — CANAL D'ESTAT (estudi → marca). A CADA canvi d'estat de tasca, i no només a
    # l'inici o al final: el que la marca vol saber és el moviment («3 de 4 fetes»), i un
    # recompte que només s'actualitzés als extrems mentiria tota l'estona del mig.
    #
    # Va DESPRÉS del `fase_actual='Dev'` de dalt a posta: el resum ha de portar la fase que
    # queda, no la d'abans. Es rellegeix el model per això mateix — l'`update()` de dalt no
    # toca cap instància en memòria.
    #
    # No-fatal per construcció (`sync_estat_segur`, mateix patró que la meritació): si el pont
    # està tancat el tècnic no se n'ha d'assabentar. `sync_estat` ja calla sol si el model és
    # INTERN, així que aquí no cal cap guard de provinença.
    from fhort.models_app.models import Model as _Model
    from fhort.tenants.federation_service import SENTIT_MADURESA, sync_estat_segur
    _model = _Model.objects.filter(pk=task.model_id).first()
    if _model is not None:
        sync_estat_segur(_model, SENTIT_MADURESA)

    return {'task_id': task.pk, 'status': to_status, 'paused_task_id': paused_task_id}


def traspassa_tram(task, profile):
    """F1.5 · D-7 — El relleu d'una tasca EN CURS, fet visible.

    Fins avui, endur-se una tasca d'un altre (per `open-task` o per `claim`) reassignava
    l'`assignee` i prou: el tram del tècnic anterior **quedava obert**, seguint-li imputant temps
    a ell, i el nou treballava sense rellotge propi. Al log no en quedava cap fila — el relleu era
    l'únic moviment del sistema que no deixava rastre.

    Aquí es tanca el tram de qui la tenia, se n'obre un per a qui l'agafa, i s'escriu un
    `TaskTransition` marcat `auto='handoff'` perquè el log digui QUÈ ha passat sense atribuir a
    ningú un gest que no ha fet. L'estat de la tasca no es toca: seguia `InProgress` i hi segueix
    — el que canvia és de qui és el rellotge.

    V3 (06/08) — I L'EXCLUSIÓ TAMBÉ VAL PER AL QUE ARRIBA. `_open_timer` només tanca els trams
    D'AQUESTA TASCA: un tècnic que ja treballava en una altra i es quedava aquesta n'acabava amb
    DOS d'oberts, perquè el bucle d'exclusió vivia només a la branca `InProgress` de
    `transition_task` i el relleu no hi passa (no canvia l'estat, i és correcte que no el canviï).
    Ara el relleu crida el mateix `_aplica_exclusio_tecnic` que obrir una tasca: la feina que el
    tècnic tenia oberta queda PAUSADA i marcada (`auto='exclusio_inprogress'`), i el rastre del
    relleu (`auto='handoff'`) segueix intacte, que són dos fets diferents i s'han de poder llegir
    per separat.

    Retorna el pk del tècnic anterior (o None si la tasca no tenia cap tram obert).
    """
    anterior = (TimerEntrada.objects
                .filter(model_task=task, fi__isnull=True, actiu=True)
                .values_list('tecnic_id', flat=True).first())
    if anterior == profile.pk:
        return None                      # ja és seva: cap relleu
    _aplica_exclusio_tecnic(profile, task)   # la feina que el nou tenia oberta, pausada
    _open_timer(task, profile)           # tanca TOTS els oberts i n'obre un per al nou
    if anterior is not None:
        _log(task, task.status, task.status, profile, auto='handoff')
    return anterior


def rectification_count(task) -> int:
    """Nombre de rectificacions = transicions Done -> InProgress."""
    return TaskTransition.objects.filter(model_task=task, from_status='Done',
                                         to_status='InProgress').count()
