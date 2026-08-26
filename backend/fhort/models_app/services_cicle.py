"""M3 · EL CICLE DE VIDA DEL MODEL — tancar, reobrir, jubilar (FIT-9 · FIT-10 · FIT-11).

🔒 **CAP D'AQUESTS TRES ÉS UNA DEDUCCIÓ.** Ni «totes les tasques Done», ni «l'última ronda
entregada», ni «fa sis mesos que ningú no hi toca» tanquen un model: el tancament és un **ACTE
HUMÀ SEPARAT** (FIT-10), i per això viu en un servei amb autor obligatori i deixa fila a
`ModelEstatEsdeveniment`. Un model acabat és una afirmació d'algú, no una conclusió del sistema.

🔑 **I EL COMERCIAL NO S'ASSABENTA PER CAP PUSH.** `commerce.get_billable_items` parteix de
`ModelTask` (`status='Done'` i sense línia d'albarà) i per tant ja llegeix el fet real: la feina
feta fins al tancament segueix sent albaranable exactament igual, i la que no s'ha fet no ho és.
Tancar un model **no crea, no anul·la i no notifica** res de comerç, i és a posta (FIT-10).
"""
from django.db import transaction
from django.utils import timezone

from .models import Model, ModelEstatEsdeveniment


class CicleVidaError(Exception):
    """Rebuig d'un acte del cicle de vida. `code` viatja a la resposta perquè la cara pugui
    dir el MOTIU i no un «no s'ha pogut» mut (mateix patró que `TransitionError.code`)."""

    def __init__(self, missatge, *, code='cicle_invalid', dades=None):
        super().__init__(missatge)
        self.code = code
        self.dades = dades or {}


def ronda_oberta(model):
    """La volta oberta del model, o None. Punt únic d'aquest fitxer: la definició d'«oberta»
    (`tancada_el IS NULL`) és de `tasks`, i no se'n fa una segona còpia aquí."""
    from fhort.tasks.services_r import _ronda_oberta   # import local: cicle models_app↔tasks
    return _ronda_oberta(model)


def _registra(model, de, a, *, motiu, profile):
    return ModelEstatEsdeveniment.objects.create(
        model=model, de_estat=de, a_estat=a, motiu=(motiu or '')[:200], per=profile)


def tancar_model(model, *, motiu, profile, confirmar=False,
                 destinatari='', descripcio='', confirmar_entrega=None):
    """FIT-10 — TANCA un model: `estat = 'acabat'`. Retorna l'`Entrega` creada, o None.

    `motiu` és una de `Model.MOTIU_TANCAMENT_CHOICES` i no és decoratiu: separa la decisió
    INTERNA (`acabat`, «ja està») del fet del CLIENT (`tret_de_cataleg`, «no es produirà»).
    Es persisteix al model i a la fila de rastre.

    🚨 **AMB RONDA OBERTA, EL SISTEMA AVISA I NO DECIDEIX** (FIT-10). Tancar un model amb una
    volta viva vol dir tancar feina que algú està fent, i això no pot passar per accident: la
    primera crida **refusa** amb `code='ronda_oberta'` i les dades de la volta, perquè la cara
    pugui preguntar-ho amb totes les lletres. Només la segona —amb `confirmar`— ho fa, i llavors
    ho fa SENCER i en **una sola transacció**.

    🔒 **I EL QUE FA AMB LA VOLTA DEPÈN DEL MOTIU** (decisió d'Agus · CODA d'M3):

    | motiu | què li passa a la volta oberta |
    |---|---|
    | `acabat` | **s'ENTREGA** (`informar_entrega`) → i l'entrega la tanca (FIT-13) amb la seva feina viva (FIT-6). Per això aquesta via demana `destinatari` |
    | `tret_de_cataleg` | **es TANCA i prou** (`tancar_ronda`) → cap `Entrega`, cap destinatari |

    **Per què la segona via no entrega: FIT-1.** L'`Entrega` registra un fet que **ha passat** —
    «això s'ha enviat a algú, aquest dia»—, i quan el client informa que la peça no es produirà
    no s'ha enviat res. Escriure-hi una entrega hauria fabricat un fet fals a la taula que
    justament serveix per saber què es va enviar i quan; i com que el comercial llegeix
    `ModelTask` i no `Entrega` (`get_billable_items`), no s'hi guanyava ni tan sols facturació.
    La feina viva es tanca igual —el model s'acaba— però es tanca **declarant que es tanca**,
    no declarant una entrega que ningú no ha fet.

    En les dues vies, l'acte és **d'M1 i no una segona implementació** (`informar_entrega` /
    `tancar_ronda`, `services_r`): així el tancament del model hereta FIT-13 i FIT-6 sense
    repetir-ne ni una línia.

    `confirmar_entrega` és el nom VELL del paràmetre i segueix acceptat: la porta HTTP el rebia
    així d'M3 i els fums escrits abans de la CODA el continuen enviant. Amb dues vies i una que
    no entrega res, el nom honest és `confirmar`.
    """
    if confirmar_entrega is not None:
        confirmar = confirmar or bool(confirmar_entrega)
    if profile is None:
        raise CicleVidaError('Cal un perfil per tancar un model.', code='no_profile')
    if motiu not in dict(Model.MOTIU_TANCAMENT_CHOICES):
        raise CicleVidaError(
            'El motiu del tancament ha de ser `acabat` o `tret_de_cataleg`.',
            code='motiu_invalid')
    if model.estat == Model.ESTAT_ACABAT:
        raise CicleVidaError('Aquest model ja està acabat.', code='ja_acabat')
    if model.estat == Model.ESTAT_JUBILAT:
        raise CicleVidaError('Un model jubilat no es torna a tancar: reobre\'l primer.',
                             code='jubilat')

    entrega_la_volta = (motiu == Model.MOTIU_TANCAMENT_ACABAT)

    r = ronda_oberta(model)
    if r is not None and not confirmar:
        raise CicleVidaError(
            (f'La ronda R{r.seq} està oberta. Tancar el model ara confirma l\'entrega d\'aquella '
             f'volta i tanca la feina que hi queda viva.') if entrega_la_volta else
            (f'La ronda R{r.seq} està oberta. Tancar el model ara la tanca —amb la feina que hi '
             f'queda viva— sense declarar cap entrega.'),
            code='ronda_oberta',
            # `requereix_entrega` diu a la cara QUINA pregunta ha de fer: amb `acabat` demana el
            # destinatari (l'acte d'entrega el necessita), amb `tret_de_cataleg` no hi ha res a
            # demanar perquè no s'entrega res.
            dades={'ronda': {'id': r.pk, 'seq': r.seq, 'motiu': r.motiu},
                   'requereix_entrega': entrega_la_volta})

    from fhort.tasks.services_r import EntregaError, RondaError, informar_entrega, tancar_ronda

    entrega = None
    with transaction.atomic():
        if r is not None:
            try:
                if entrega_la_volta:
                    entrega = informar_entrega(r, destinatari=destinatari, profile=profile,
                                               descripcio=descripcio)
                else:
                    # 🔒 FIT-1 — cap entrega: la volta es tanca DECLARANT que es tanca. `tancar_ronda`
                    # ja tanca la feina viva tasca per tasca i pel mecanisme únic (FIT-6).
                    tancar_ronda(r, profile=profile)
            except EntregaError as e:
                raise CicleVidaError(str(e), code='entrega_invalida')
            except RondaError as e:
                raise CicleVidaError(str(e), code='ronda_no_tancable')
        de = model.estat
        model.estat = Model.ESTAT_ACABAT
        model.motiu_tancament = motiu
        # `data_tancament` és un DateField que fins avui no escrivia ningú (cens FASE 0a).
        # La data de l'acte hi va: és la que el board ja sabia ordenar i no en calia una de nova.
        model.data_tancament = timezone.localdate()
        model.save(update_fields=['estat', 'motiu_tancament', 'data_tancament'])
        _registra(model, de, Model.ESTAT_ACABAT, motiu=motiu, profile=profile)
    return entrega


def reobrir_model(model, *, profile, motiu=''):
    """FIT-11 — un model tancat TORNA A SER OBERT (`estat='nou'`), amb rastre.

    🔑 **REOBRIR NO DECIDEIX RES MÉS.** No obre cap ronda, no reobre cap tasca i no toca la
    fase: només torna el model al tauler. El que es fa a dins —rectificar la darrera volta
    (FIT-2, sense facturació i amb rastre) o obrir-ne una de nova (+Ronda)— és una decisió
    posterior i separada, i **triar-ne una tanca l'altra**: obrir una volta nova elimina
    l'opció de rectificar l'anterior, i qui ho imposa és el guard de `transition_task`
    (`_guarda_darrera_volta`), no aquest servei.

    Serveix igual per a un `acabat` i per a un `jubilat`: desjubilar és tornar-lo a la vida, i
    partir el gest en dos («desjubilar» i «reobrir») hauria estat inventar un estat intermedi
    que ningú no ha demanat. El rastre diu de quin dels dos venia.
    """
    if profile is None:
        raise CicleVidaError('Cal un perfil per reobrir un model.', code='no_profile')
    if model.estat == Model.ESTAT_NOU:
        raise CicleVidaError('Aquest model ja és obert.', code='ja_obert')

    with transaction.atomic():
        de = model.estat
        model.estat = Model.ESTAT_NOU
        model.motiu_tancament = None
        model.data_tancament = None    # un model obert no té data de tancament; la història
        model.save(update_fields=['estat', 'motiu_tancament', 'data_tancament'])  # viu al log
        _registra(model, de, Model.ESTAT_NOU, motiu=motiu, profile=profile)
    return model


def jubilar_model(model, *, profile, motiu=''):
    """FIT-9 — ARXIVA un model acabat: `estat='jubilat'`. Fora de les vistes normals.

    ⚠️ **NOMÉS DES D'`acabat`, i només a mà.** Jubilar és el segon esglaó del cicle, no una
    drecera: un model viu no salta a l'històric sense passar pel tancament, que és l'acte que
    té motiu i autor. I no hi ha cap automatisme per temporada (decisió d'Agus per a la v1):
    «fa dues temporades» no és una raó per fer desaparèixer feina de la vista de ningú.
    """
    if profile is None:
        raise CicleVidaError('Cal un perfil per jubilar un model.', code='no_profile')
    if model.estat == Model.ESTAT_JUBILAT:
        raise CicleVidaError('Aquest model ja està jubilat.', code='ja_jubilat')
    if model.estat != Model.ESTAT_ACABAT:
        raise CicleVidaError('Només es jubila un model ACABAT: tanca\'l primer.',
                             code='no_acabat')

    with transaction.atomic():
        de = model.estat
        model.estat = Model.ESTAT_JUBILAT
        model.save(update_fields=['estat'])
        _registra(model, de, Model.ESTAT_JUBILAT, motiu=motiu, profile=profile)
    return model
