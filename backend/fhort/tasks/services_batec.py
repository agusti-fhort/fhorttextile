"""F1.3 · EL BATEC D'ESCRIPTURA — «en curs» vol dir «s'hi escriu» (D-2).

## El forat que tanca

El rellotge corria NOMÉS entre `enterEdit` i `exitEdit` de dues superfícies (Mesures i Escalat).
De 24 portes d'usuari censades, **11 no tocaven `ModelTask` en absolut**, i entre elles hi havia
les tres per on més s'escriu sobre un model: editar la fitxa `.ftt`, pujar fitxers i editar la
graella de mides. Mesurat: d'una hora de treball real en sortien registrats **entre 0 i 60
minuts**, i el que ho decidia no era quant s'havia treballat sinó **si la porta havia quedat
oberta**. Dos dies del corpus donen literalment **zero minuts** sobre finestres de 42 i 37 minuts.

A partir d'ara, **escriure és el senyal**. Cada escriptura d'usuari sobre un model bat:

  · tasca `Pending`/`Paused` → `InProgress` (obre tram)   ← el batec FORT
  · tasca `InProgress`       → renova `last_heartbeat` del tram obert  ← el batec normal
  · tasca `Done`             → **no-op**: reobrir és un acte humà, no l'efecte d'un PATCH
  · sense tasca              → no-op silenciós

## El que NO fa, i és deliberat

**No crea tasques.** Obre-si-cal vol dir «si la tasca EXISTEIX». La gènesi d'una tasca segueix
tenint una sola porta (`open-task` / `define-tasks`): un `PATCH` sobre una mesura no pot fer
néixer una tasca de POM que el PM no ha planificat.

**UN SOL BATEC.** `TimerEntrada.last_heartbeat` ja existia com a segell de vida del guard de tasca
oblidada, i el seu comentari a `models.py` ho deixava escrit: *«Qui escrigui aquí haurà d'escriure
els dos alhora, no inventar-se un segon batec.»* Això és el que fa aquest mòdul: el guard i
l'escriptura escriuen **el mateix camp**. No n'hi ha un de presència i un altre d'activitat.
"""
import logging

logger = logging.getLogger(__name__)

# Mapa SUPERFÍCIE → `TaskType.code` (G9: sempre per slug). És el vocabulari que les vistes
# passen a `batec_escriptura`; viu aquí perquè hi hagi UNA taula i no una constant per fitxer.
SUP_MESURES = 'pom'
SUP_PRESA = 'size_check'
SUP_ESCALAT = 'grading'
SUP_FITXA = 'tech_sheet'


def _meritar_si_cal(task):
    """F1.4 · D-10 — EL GALLET DE MERITACIÓ, al seu lloc nou.

    Abans vivia a `transition_task`: la primera `→InProgress` de qualsevol tasca meritava el
    model. El fet facturable era «algú ha obert una porta», i tocar-ne una tres segons per error
    facturava. Ara és «algú hi ha ESCRIT», que és el que aquest mòdul sap i la màquina d'estats
    no.

    Les funcions de meritació no s'han tocat (`services_c._meritar_model` / `_meritar_conjunt`):
    el seu guard d'idempotència és un `UPDATE ... WHERE consumption_started_at IS NULL` atòmic,
    de manera que cridar-les a cada batec és barat i segur — la segona vegada no fan res.

    No-fatal, igual que abans: el tècnic ja té la feina desada i un error de facturació no li
    pot tombar l'escriptura. El forat el recull `reconcile_consumption`.
    """
    from django.utils import timezone

    from fhort.models_app.models import Model

    from .services_c import _meritar_conjunt, _meritar_model

    try:
        model = Model.objects.select_related('customer', 'garment_set').get(pk=task.model_id)
        if model.consumption_started_at is not None:
            return   # ja meritat: ni una consulta més
        if model.garment_set_id:
            _meritar_conjunt(model, timezone.now())
        else:
            _meritar_model(model, timezone.now())
    except Exception:
        logger.exception('meritacio fallida (batec) model=%s task=%s', task.model_id, task.pk)


def batec_escriptura(model, code, profile):
    """Registra que algú ESTÀ TREBALLANT aquest model en aquesta superfície.

    `model`: instància de `models_app.Model` (o pk). `code`: slug de `TaskType`.
    `profile`: `UserProfile` de qui escriu. Sense perfil no hi ha batec (usuari de sistema,
    import, command): no és un error, és que no hi ha ningú a qui imputar-ho.

    Retorna un dict de traça `{'batec': bool, 'accio': str, 'task_id': int|None}`. **Mai llança**:
    el batec és observació, i una observació que trenca l'escriptura que observa no serveix.

    `accio` ∈ {`oberta`, `renovat`, `sense_tasca`, `sense_perfil`, `refusada`, `acabada`, `error`}.
    """
    from django.utils import timezone

    from .models import TimerEntrada
    from .services_c import TransitionError, te_paret_albara, transition_task
    from .services_r import tasca_vigent

    if profile is None:
        return {'batec': False, 'accio': 'sense_perfil', 'task_id': None}
    try:
        task = tasca_vigent(model, code)
        if task is None:
            # Deliberat: el batec no crea tasques (v. capçalera del mòdul).
            return {'batec': False, 'accio': 'sense_tasca', 'task_id': None}

        if task.status == 'Done':
            # 🔴 ESCRIURE NO REOBRE UNA TASCA ACABADA (06/08). `ALLOWED` permet `Done →
            # InProgress` perquè la REOBERTURA existeix com a acte —rectificació—, i el batec
            # se'n servia sense voler: un `PATCH` sobre una cel·la d'una tasca ja tancada la
            # tornava a obrir, li obria tram i li reiniciava el rellotge, tot en silenci. Només
            # se'n salvaven les ja FACTURADES, que topaven amb la paret d'albarà; totes les
            # altres queien.
            #
            # La capçalera d'aquest mòdul ja declarava el contracte —«tasca `Pending`/`Paused` →
            # `InProgress`»— i `Done` no hi era. Ara el codi ho diu igual que el comentari:
            # reobrir és un acte humà, i té la seva porta (`open-task` / ronda).
            #
            # La paret d'albarà es diu igualment i amb el seu codi: qui la toca ha de saber que
            # el que hi ha al davant no és «ja està feta» sinó «ja està facturada», que és una
            # altra conversa (obrir una RONDA).
            if te_paret_albara(task):
                return {'batec': False, 'accio': 'refusada', 'task_id': task.pk,
                        'code': 'tasca_albaranada'}
            return {'batec': False, 'accio': 'acabada', 'task_id': task.pk}

        if task.status != 'InProgress':
            try:
                transition_task(task, 'InProgress', profile)
            except TransitionError as e:
                # Paret d'albarà (D-5) o transició il·legal: el batec no hi insisteix. Qui vulgui
                # treballar-hi ha d'obrir una RONDA, i això és un acte humà, no un efecte d'un PATCH.
                return {'batec': False, 'accio': 'refusada', 'task_id': task.pk,
                        'code': getattr(e, 'code', None)}
            # El tram que `transition_task` acaba d'obrir neix amb `last_heartbeat` posat: qui
            # obre una tasca ESCRIVINT ja ha escrit. Si no s'estampés, un model on l'única
            # activitat fos aquest primer desat quedaria fora del criteri de forat de
            # `reconcile_consumption` (que ara mira precisament el batec), i el runtime i el
            # reconcile discreparien sobre el mateix fet.
            TimerEntrada.objects.filter(
                model_task=task, tecnic=profile, fi__isnull=True, actiu=True
            ).update(last_heartbeat=timezone.now())
            _meritar_si_cal(task)
            return {'batec': True, 'accio': 'oberta', 'task_id': task.pk}

        # Ja en curs: es renova el segell del tram obert d'AQUEST tècnic. Si el tram obert és
        # d'un altre (handoff a mitges), no se li toca: el seu rellotge és seu.
        n = (TimerEntrada.objects
             .filter(model_task=task, tecnic=profile, fi__isnull=True, actiu=True)
             .update(last_heartbeat=timezone.now()))
        _meritar_si_cal(task)
        return {'batec': bool(n), 'accio': 'renovat' if n else 'sense_tram', 'task_id': task.pk}
    except Exception:
        logger.exception('batec_escriptura fallit model=%s code=%s', getattr(model, 'pk', model), code)
        return {'batec': False, 'accio': 'error', 'task_id': None}


def batec_de_request(request, model, code):
    """Sucre per a les vistes: treu el `profile` del request i bat. Retorna el mateix dict."""
    return batec_escriptura(model, code, getattr(request.user, 'profile', None))


def bat_escriptura(code, arg='model_id'):
    """Decorador per a les vistes-funció que ja porten el model al camí.

    S'aplica SOTA `@api_view`/`@permission_classes` (els decoradors s'apliquen de baix a dalt),
    de manera que embolcalla la funció crua i veu la `Response` de DRF.

    Bat NOMÉS si la resposta és 2xx: una escriptura que ha fallat no és feina feta, i imputar-li
    temps seria mentir en la direcció fàcil.
    """
    from functools import wraps

    def deco(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            resposta = fn(request, *args, **kwargs)
            try:
                codi_http = getattr(resposta, 'status_code', 500)
                model_id = kwargs.get(arg)
                if 200 <= codi_http < 300 and model_id:
                    batec_de_request(request, model_id, code)
            except Exception:
                logger.exception('bat_escriptura fallit a %s', getattr(fn, '__name__', fn))
            return resposta
        return wrapper
    return deco
