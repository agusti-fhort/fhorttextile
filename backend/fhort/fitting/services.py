"""
fitting/services.py — Services for the fitting cycle.

The new cycle (FittingSession / PieceFitting / PieceFittingLine) lives below.
The legacy SFFitting cycle (create_fitting/close_fitting/cancel_fitting) was
removed in Sprint 5B.5 together with the SFFitting/SFFittingLinia models.
"""
from __future__ import annotations
import logging
import uuid as _uuid

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Guard d'edició — sessió segellada ────────────────────────────────────────
# Estats en què una FittingSession queda segellada: cap escriptura de línia
# (valor_real / nota) ni propagació. La UI ho amaga; AQUÍ és la guarda real.
SEALED_SESSION_ESTATS = ('Tancada', 'Anullada')


def fitting_line_is_locked(line) -> bool:
    """True si la sessió (FittingSession) del fitting de la línia està segellada
    (estat ∈ SEALED_SESSION_ESTATS) → escriptura prohibida. Predicat pur, sense DRF."""
    return line.piece_fitting.session.estat in SEALED_SESSION_ESTATS


# ── P1 — guard d'eix base ────────────────────────────────────────────────────
# DECISIONS.md §2: el fitting és un ESTADI de la taula base; tot treball multi-talla és
# Escalat. Fins ara la vista acceptava escriptures a QUALSEVOL talla i `close_piece_fitting`
# només consolidava la BASE (consolidate_base_from_fitting): les no-base morien amb la sessió,
# sense cap avís. El guard tanca el forat a la porta d'entrada.
NON_BASE_LINE_DETAIL = (
    'El fitting només edita la talla base del model. '
    'Les altres talles es treballen a Escalat.'
)


def fitting_line_is_non_base(line) -> bool:
    """True si la línia NO és de la talla base del seu model → escriptura prohibida (P1).

    MATEIXA font i MATEIXA normalització que `consolidate_base_from_fitting` (`model.
    base_size_label` amb `.strip()` als dos costats). Si divergissin, la vista acceptaria
    escriptures que el `close` descartaria en silenci — que és exactament el forat que es tapa.

    Model sense `base_size_label` (avui: cap): no es pot determinar la base → NO es bloqueja,
    per no deixar el fitting inservible. Aquelles línies ja no les consolidava ningú.
    """
    base = (line.piece_fitting.model.base_size_label or '').strip()
    if not base:
        return False
    return line.size_label.strip() != base


# ── E1/B1 — EL GUARD ES PARTEIX: PRENDRE ≠ DECIDIR ───────────────────────────
#
# P1 tancava TOTA escriptura de línia no-base, i era correcte mentre l'únic que es podia fer
# amb una línia fos decidir-la. El flux E1 hi separa dos gestos:
#
#   · PRENDRE  — anotar la xifra de la peça FÍSICA arribada en aquella talla. Dada
#                d'observació, i n'hi ha a totes les talles del run: és el pas 1.
#   · DECIDIR  — el veredicte (`decisio`). R2: **els ajustos només s'accepten a la TALLA
#                BASE**, i la propagació surt d'allà. Segueix sent 400.
#
# 🔑 EL GUARD ÉS PER CAMP, NO PER ENDPOINT, i el motiu és el payload mixt: un PATCH amb
# `valor_real` i `decisio` alhora entra per la porta legal de la presa i colaria el veredicte.
# Per això el predicat mira QUÈ es vol escriure, no per on ha entrat.
#
# ⚠️ OBRIR LA PRESA NO OBRE CAP ESCRIPTURA DE DOMINI, i està comprovat per cens (17/08): la
# presa no-base no arriba a `consolidate_base_from_fitting` (:515 `size_label != base →
# continue`), i per tant tampoc al `close`. Els lectors que sí que canvien de resposta ho han
# de fer: `esdeveniments.linia_te_contingut` (algú HA mesurat) i els exports S8/S10, que
# sempre han llistat totes les talles. El banc que ho congela és
# `test_e1_guard_partit.ConsolidacioIgnoraPresaNoBaseTest`.
#
# `propagar` NO entra aquí: l'ancoratge que escampa el delta és el gest de la base per
# definició (R2) i es queda amb el guard sencer, `fitting_line_is_non_base`.

#: Camps que constitueixen una DECISIÓ sobre la cel·la. La resta del serializer
#: (`valor_real`, `nota`) és PRESA. `decisio` hi és sola a posta: desdir-se (escriure `''`)
#: també és decidir, i per això el predicat mira la PRESÈNCIA de la clau i mai el seu valor.
CAMPS_DE_DECISIO = ('decisio',)

NON_BASE_DECISIO_DETAIL = (
    "Els ajustos només s'accepten a la talla base del model. "
    "A les altres talles s'hi pot anotar la presa, però no decidir-la."
)


def escriptura_es_decisio(camps) -> bool:
    """True si el payload declara algun camp de decisió. Predicat pur, sense DRF.

    `camps` és qualsevol iterable de noms (típicament `request.data.keys()`). Mira la
    presència de la clau i no el valor: `{'decisio': ''}` és el gest de TREURE el veredicte,
    que és una decisió tant com posar-n'hi un.
    """
    return any(c in CAMPS_DE_DECISIO for c in (camps or ()))


def fitting_line_decisio_fora_de_base(line, camps) -> bool:
    """True si aquest payload DECIDEIX sobre una línia que no és de la talla base (R2).

    Reusa `fitting_line_is_non_base` i no en duplica la normalització: si la font de la talla
    base divergís entre els dos predicats, la vista acceptaria veredictes que el `close`
    descartaria en silenci — el mateix forat que P1 va tapar, un gest més tard.
    """
    return escriptura_es_decisio(camps) and fitting_line_is_non_base(line)


# ── E1/B3 — LA PRESA DE L'ESCALAT ────────────────────────────────────────────
#
# Pas 1 del flux E1: quan arriben les peces FÍSIQUES del model, es mesura cada talla i s'anota
# a la columna «Fit actual» de l'Escalat. Fins avui aquella columna EDITAVA LA CORBA TEÒRICA
# (`escalat_ajustar_talla_view` → `BaseMeasurement`/`ModelGradingOverride` + re-derivació dels
# specs), i per això el pas 2 hidratava del que el pas 1 acabava d'escriure: desviació zero i
# acceptació buida. V. `docs/diagnosis/DIAGNOSI_E1_MESURA_ESCALAT.md` §3.2.
#
# 🔑 EL CANVI ÉS DE NATURALESA, NO DE DESTÍ: la presa és una DADA D'OBSERVACIÓ i va a
# `PieceFittingLine.valor_real`, que és el magatzem que ja té els cinc eixos
# (pom · capa · instancia · garment · size_label), el teòric al costat i el veredicte a sobre.
# **Aquesta porta NO toca `BaseMeasurement` i NO crida `generate_graded_specs`.** El dia que
# algú hi afegeixi qualsevol de les dues coses, el pas 2 tornarà a mirar-se al mirall.
#
# ⚠️ NO CREA SESSIÓ. Obrir una presa és un acte —crea `FittingSession` + `PieceFitting` + N
# línies— i fer-lo néixer d'una tecla en una cel·la seria el mateix error que aquesta peça
# arregla. Sense presa viva es retorna `PresaNoObertaError` i la pantalla ofereix el gest
# explícit, que és el mateix que obre «Mesurar prenda». (Decisió D5 de la diagnosi: OBERTA.)


class PresaNoObertaError(Exception):
    """No hi ha cap `PieceFitting` viva del model: no hi ha on anotar la presa."""


class PresaSenseLiniaError(Exception):
    """La presa viva no té línia per a aquesta mesura i talla (mesura morta o talla fora del
    run de la versió). No se n'inventa cap: una línia nova ha de néixer de la reconciliació,
    que sap què és una mesura viva del model."""


def peca_de_presa_del_model(model):
    """La `PieceFitting` VIVA del model, o `None`. Punt únic, i NO crea res.

    «Viva» = la seva sessió és `Programada` o `Oberta` (`SESSIONS_VIVES`), el mateix predicat
    que fa servir `reconcilia_linies` per decidir si una peça encara es pot posar al dia. Una
    sessió segellada és ACTA i no admet preses noves.

    Amb més d'una de viva mana LA MÉS RECENT per data de sessió (desempat per id), que és el
    mateix ordre cronològic que `esdeveniments.peces_amb_contingut` — mai per id de peça sol,
    que és l'ordre en què es van OBRIR les graelles.
    """
    from fhort.fitting.models import PieceFitting
    return (PieceFitting.objects
            .filter(model=model, session__estat__in=SESSIONS_VIVES)
            .select_related('session', 'model', 'grading_version__size_fitting')
            .order_by('-session__data', '-session__id', '-id')
            .first())


def darrera_peca_de_presa_segellada(model):
    """La `PieceFitting` de la DARRERA presa SEGELLADA del model, o `None`. NO crea res.

    🚨 EL FORAT QUE TANCA (E3a, `DIAGNOSI_QA_2054_REGRESSIO_O_FORAT.md`): sense això, el GET de
    presa serveix `session: null` per a una sessió `Tancada` EXACTAMENT IGUAL que per a un model
    que no n'ha tingut mai cap. Una presa segellada quedava **indistingible del no-res**, i d'aquí
    penjaven tres símptomes que semblaven tres bugs: la graella seguia editable i contestava 409
    per cel·la, el sub-tab «Decisió» no obria, i el racó oferia «obrir una presa» sobre un model
    que n'acabava de tancar una. Una acta que no es pot llegir no és una acta.

    Mateix ordre cronològic que `peca_de_presa_del_model` —`-session__data`, desempat per id— i
    pel mateix motiu: la que mana és LA MÉS RECENT, no la que es va obrir primer. Amb l'històric
    complet no s'hi arriba per aquí: això serveix l'ÚLTIMA, que és l'estat de la pantalla; el
    passat sencer és del Repàs.
    """
    from fhort.fitting.models import PieceFitting
    return (PieceFitting.objects
            .filter(model=model, session__estat__in=SEALED_SESSION_ESTATS)
            .select_related('session', 'model', 'grading_version__size_fitting')
            .order_by('-session__data', '-session__id', '-id')
            .first())


def desa_presa_escalat(model, *, pom_id, capa, instancia, garment, talla, valor, nota=None):
    """Anota la presa d'UNA mesura a UNA talla sobre la presa viva del model.

    Retorna la `PieceFittingLine` desada. Alça `PresaNoObertaError`, `PresaSenseLiniaError` o
    `ValueError` (sessió segellada) — la traducció a codis HTTP la fa la vista.

    ⚠️ ELS EIXOS ARRIBEN JA RESOLTS. Qui els llegeix del cos d'una petició els passa per
    `models_app.views._identitat_de_mesura`, que és el punt únic que decideix què rep qui no
    els diu (l'exterior de la instància única de la mare). Aquí NO s'hi torna a aplicar cap
    default: dos llocs decidint el mateix literal són dues lleis, i el dia que una canviés,
    aquesta porta escriuria a una fila que la resta del sistema no busca mai.

    `valor=None` esborra la presa: la línia torna al seu teòric, que és el mateix gest que
    «treure l'ancoratge» a `propagar` (`views.py:664`). No s'esborra la línia: la línia és de
    la peça, no de qui l'ha mesurada.

    🚨 LES DUES COSES QUE AQUESTA FUNCIÓ NO FA, i que la vista que substitueix SÍ feia:
      · no escriu `BaseMeasurement` (això és consolidar, i consolidar és del `close`);
      · no crida `generate_graded_specs` (això és propagar, i propagar té la seva porta).
    Si un dia calen, no van aquí: van al gest que les mereix.
    """
    from fhort.fitting.models import PieceFittingLine

    pf = peca_de_presa_del_model(model)
    if pf is None:
        raise PresaNoObertaError(
            "El model no té cap presa oberta: obre-la abans d'anotar mesures.")
    if pf.session.estat in SEALED_SESSION_ESTATS:      # cinturó: `peca_de_presa_del_model` ja
        raise ValueError('Sessió de fitting tancada; no es pot modificar.')   # les exclou

    linia = (PieceFittingLine.objects
             .filter(piece_fitting=pf, pom_id=pom_id, capa=capa,
                     instancia=instancia, garment=garment,
                     size_label=(talla or '').strip())
             .first())
    if linia is None:
        raise PresaSenseLiniaError(
            f"La presa oberta no té línia per a aquesta mesura a la talla {talla}.")

    # ── E2/B1 · LA MARCA DEL GEST ────────────────────────────────────────────────────────
    # Això deia: «escriure-hi el teòric és treure la presa, no anotar-ne una», i era una
    # conseqüència del predicat inferit, no una decisió. Amb E2b l'usuari pot CONFIRMAR el
    # pre-omplert tal qual —un gest legítim que dona `valor == valor_teoric`— i això SÍ que és
    # anotar una presa. Qui distingeix les dues coses ja no és el número: és `presa_at`.
    #
    #   · `valor` amb número (coincideixi o no amb la teòrica) → PRESA: marca posada.
    #   · `valor` buit → DESDIR-SE: la línia torna al teòric i la marca se'n va. Deixar-la
    #     seria dir que algú ha mesurat una cel·la que ja no té cap presa.
    #
    # `_now()` i no `timezone.now()` inline: la data la posa el servidor i mai el client.
    from django.utils import timezone
    linia.valor_real = linia.valor_teoric if valor is None else float(valor)
    linia.presa_at = None if valor is None else timezone.now()
    camps = ['valor_real', 'presa_at']
    if nota is not None:
        linia.nota = nota
        camps.append('nota')
    linia.save(update_fields=camps)
    return linia


# ── Peça 1 — guard de solapament ─────────────────────────────────────────────
class SessionOverlapError(Exception):
    """Conflicte DUR: ja hi ha una sessió viva del mateix model que solapa la franja
    (mateixa data i franja encavalcada, o alguna sense hora a la mateixa data).
    El `conflicts` és la llista d'ids de sessió en conflicte (per a la resposta 409)."""
    def __init__(self, message, conflicts):
        super().__init__(message)
        self.conflicts = conflicts


class SessionSoftConflict(Exception):
    """Conflicte SUAU: ja hi ha sessió viva del mateix model i mateixa fase en una
    franja DIFERENT. Requereix confirmació (force=True) per crear igualment."""
    def __init__(self, message, sessions):
        super().__init__(message)
        self.sessions = sessions


class SessionActionConflict(Exception):
    """409 — l'estat de la sessió (Oberta o amb peces) no permet l'acció directa
    (eliminació); cal anul·lar-la amb motiu via /discard/."""
    pass


def _slot_overlap(s_start, s_dur, n_start, n_dur):
    """True si [s_start, s_start+s_dur) ∩ [n_start, n_start+n_dur) ≠ ∅ (mateix dia)."""
    import datetime as _dt
    base = _dt.date(2000, 1, 1)
    a0 = _dt.datetime.combine(base, s_start)
    a1 = a0 + _dt.timedelta(minutes=s_dur or 0)
    b0 = _dt.datetime.combine(base, n_start)
    b1 = b0 + _dt.timedelta(minutes=n_dur or 0)
    return a0 < b1 and b0 < a1


def check_session_overlap(*, model_id, data, fase, start_time, duracio_minuts,
                          exclude_session_id=None):
    """Sessions vives (≠ Tancada/Anullada) del MATEIX model que xoquen amb la nova franja.

    Retorna (hard, soft) — dues llistes de FittingSession:
      hard → mateixa data i solapament de franja; o mateixa data amb alguna sense hora.
      soft → mateixa fase en una franja diferent (no dur).
    Només aplica a sessions de model (garment_set → ([], []), sense guard)."""
    from .models import FittingSession
    if not model_id:
        return [], []
    qs = (FittingSession.objects
          .filter(model_id=model_id)
          .exclude(estat__in=['Tancada', 'Anullada']))
    if exclude_session_id:
        qs = qs.exclude(pk=exclude_session_id)
    hard, soft = [], []
    for s in qs:
        if s.data == data:
            if s.start_time is None or start_time is None:
                hard.append(s)            # mateixa data, alguna sense hora → no desambiguable
            elif _slot_overlap(s.start_time, s.duracio_minuts, start_time, duracio_minuts):
                hard.append(s)            # franges encavalcades
            elif s.fase == fase:
                soft.append(s)            # mateix dia, franja diferent, mateixa fase
        elif s.fase == fase:
            soft.append(s)                # dia diferent, mateixa fase
    return hard, soft


# ═════════════════════════════════════════════════════════════════════════════
# Sprint 5B.3 — Fitting cycle (FittingSession / PieceFitting / PieceFittingLine)
# Open (create) + close with FUNCTIONAL versioning + brain stub. Gate is 5B.4.
# ═════════════════════════════════════════════════════════════════════════════

# C4 — create_session() (formulari lliure de fitting) JUBILAT: l'alta de fitting va sempre pel
# camí schedule (schedule_session / schedule_now), que és un superconjunt estricte (estat
# Programada + franja + attendees + recompute + guard de solapament). La validació XOR
# model/garment_set queda ÚNICA a schedule_session (a sota).


def schedule_session(*, fase, data, responsable_id, model_id=None, garment_set_id=None,
                     lloc='', start_time=None, end_time=None,
                     duracio_minuts=None, attendee_ids=None, created_by_id=None,
                     force=False, _skip_recompute=False, _skip_guard=False):
    """Programa un fitting (estat Programada). El responsable fixa dia (i opcionalment hores).
    No s'executa fins que s'obre (open_session).
    `duracio_minuts`: default 10 min × N (N=peces del set, o 1 per single).
    `attendee_ids`: assistents interns; si hi ha start_time → recompute de la seva cua.
    `created_by_id`: UserProfile.id de qui crea (traçabilitat).
    `force`: salta el bloqueig per conflicte SUAU (no el dur, que sempre bloqueja).
    `_skip_recompute`: inhibeix el recompute per sessió (ús intern de schedule_bulk, que en
    fa UN de sol al final sobre la unió d'attendees). Els attendees s'assignen igualment.
    `_skip_guard`: omet el guard de solapament (ús intern de schedule_bulk, que el fa per
    model abans i decideix ometre/avisar a banda)."""
    if bool(model_id) == bool(garment_set_id):
        raise ValueError("Cal exactament un de model_id o garment_set_id (XOR).")
    # Redisseny 5C: el fitting ja NO exigeix Production Delivered prèvia. La via adaptativa
    # (gestió de la recepció esperada) viu a la view schedule(), no com a bloqueig dur aquí.
    from .models import FittingSession
    if duracio_minuts is None:
        if garment_set_id:
            from fhort.models_app.models import GarmentSet
            n = GarmentSet.objects.get(pk=garment_set_id).num_pieces or 1
        else:
            n = 1
        duracio_minuts = 10 * n
    # Guard de solapament (Peça 1): dur → 409; suau sense force → requereix confirmació.
    if not _skip_guard and model_id:
        hard, soft = check_session_overlap(
            model_id=model_id, data=data, fase=fase,
            start_time=start_time, duracio_minuts=duracio_minuts)
        if hard:
            raise SessionOverlapError(
                f"Ja hi ha una sessió viva d'aquest model que solapa la franja del {data}.",
                [s.id for s in hard])
        if soft and not force:
            raise SessionSoftConflict(
                f"Ja hi ha {len(soft)} sessió(ns) viva(es) de fase {fase} d'aquest model "
                "en una altra franja. Confirma per crear-ne una de nova.",
                [s.id for s in soft])
    session = FittingSession.objects.create(
        fase=fase, data=data, model_id=model_id, garment_set_id=garment_set_id,
        responsable_id=responsable_id, lloc=lloc,
        start_time=start_time, end_time=end_time,
        duracio_minuts=duracio_minuts, estat='Programada',
        created_by_id=created_by_id)
    if attendee_ids:
        session.attendees.set(attendee_ids)
        if start_time and not _skip_recompute:   # recompute només si hi ha franja real i no s'inhibeix
            try:
                from fhort.planning.plan_service import recompute_for_technicians
                recompute_for_technicians(set(attendee_ids))
            except Exception:
                logger.exception('recompute post-schedule no-fatal')
    return session


def schedule_bulk(*, fase, data, start_time, model_ids,
                  duracio_minuts=None, attendee_ids=None,
                  responsable_id=None, lloc='', created_by_id=None):
    """Crea N FittingSessions ENCADENADES amb un `convocatoria` UUID compartit.

    Les sessions s'encadenen: la i+1 comença on acaba la i, via add_working_minutes(None, …)
    sobre el CALENDARI D'EMPRESA PUR (salta pauses/jornada/caps de setmana/festius). Si no hi
    ha `start_time`, NO s'encadena (totes queden sense hora, marcador de dia). El recompute es
    fa UN sol cop al final sobre la unió d'attendees (cada sessió s'inhibeix amb _skip_recompute).

    Peça 1: `model_ids` es DEDUPLICA preservant ordre. El guard de solapament s'aplica per
    model: els conflictes DURS s'OMETEN (no es crea) i es reporten a `skipped`; els SUAUS NO
    bloquegen (el bulk és una acció deliberada), només s'avisa a `warnings`.

    Retorna (sessions, convocatoria, skipped, warnings):
      sessions → FittingSession creades; convocatoria → UUID (None si no se'n crea cap);
      skipped  → [{'model_id', 'reason'}] (durs omesos);
      warnings → [{'model_id', 'reason'}] (suaus creats igualment)."""
    from fhort.planning.calendar_service import add_working_minutes
    import datetime as _dt

    model_ids = list(dict.fromkeys(model_ids))   # dedup preservant ordre
    convocatoria = _uuid.uuid4()
    sessions = []
    skipped = []
    warnings = []
    current_data = data          # pot avançar si l'encadenament creua fi de jornada
    current_start = start_time   # time object o None

    with transaction.atomic():
        for model_id in model_ids:
            dur = duracio_minuts if duracio_minuts is not None else 10

            hard, soft = check_session_overlap(
                model_id=model_id, data=current_data, fase=fase,
                start_time=current_start, duracio_minuts=dur)
            if hard:
                # Conflicte dur → ometre i reportar; NO consumeix la franja (no s'encadena).
                skipped.append({
                    'model_id': model_id,
                    'reason': f"Solapament amb sessió viva existent (ids {[s.id for s in hard]}).",
                })
                continue
            if soft:
                warnings.append({
                    'model_id': model_id,
                    'reason': f"Ja existeix sessió de fase {fase} en una altra franja "
                              f"(ids {[s.id for s in soft]}); creada igualment.",
                })

            session = schedule_session(
                fase=fase,
                data=current_data,
                start_time=current_start,
                duracio_minuts=dur,
                attendee_ids=attendee_ids or [],
                responsable_id=responsable_id,
                model_id=model_id,
                lloc=lloc,
                created_by_id=created_by_id,
                _skip_recompute=True,
                _skip_guard=True,   # el guard ja s'ha fet aquí per model
            )
            session.convocatoria = convocatoria
            session.save(update_fields=['convocatoria'])
            sessions.append(session)

            # Encadenar només si hi ha hora real (sense hora → marcador de dia, no s'encadena).
            if current_start is not None:
                start_dt = _dt.datetime.combine(current_data, current_start)
                end_dt = add_working_minutes(None, start_dt, dur)  # naïf in → naïf out
                current_data = end_dt.date()    # pot ser un altre dia (salta jornada/festius)
                current_start = end_dt.time()

        # Recompute ÚNIC al final (no N): unió d'attendees. No-fatal.
        if attendee_ids and start_time and sessions:
            try:
                from fhort.planning.plan_service import recompute_for_technicians
                recompute_for_technicians(set(attendee_ids))
            except Exception:
                logger.exception('recompute post-schedule-bulk no-fatal')

    if not sessions:
        convocatoria = None   # no s'ha creat res → no hi ha convocatòria
    return sessions, convocatoria, skipped, warnings


def open_session(session_id):
    """Obre una sessió Programada (acte del tècnic, el dia del fitting): Programada→Oberta."""
    from .models import FittingSession
    s = FittingSession.objects.get(pk=session_id)
    if s.estat != 'Programada':
        raise ValueError(f"Només es pot obrir una sessió Programada (estat actual: {s.estat}).")
    s.estat = 'Oberta'
    fields = ['estat']
    if s.started_at is None:        # Peça 1 — marca real d'obertura
        s.started_at = timezone.now()
        fields.append('started_at')
    s.save(update_fields=fields)
    return s


def create_piece_fitting(session_id: int, model_id: int, *, created_by_id: int | None = None):
    """Create a PieceFitting for one piece and materialise its lines.

    Resolves the model's working SizeFitting → its active GradingVersion, then
    clones each active GradedSpec into a PieceFittingLine (valor_teoric = grading,
    valor_real = copy of the theoretical, editable). Returns (piece_fitting, n_lines).
    """
    from fhort.fitting.models import (
        FittingSession, PieceFitting, PieceFittingLine, GradedSpec,
    )
    from fhort.models_app.models import Model

    session = FittingSession.objects.get(pk=session_id)
    model = Model.objects.get(pk=model_id)

    sf = _resolve_working_size_fitting(model)
    if sf is None:
        # CAMÍ LLIURE: materialitzem l'SF EN L'ACTE (creat_per = l'usuari de la
        # request, el responsable de facto) via la funció única de materialització,
        # en lloc de bloquejar. Cobreix els models creats abans del fix del signal.
        from fhort.pom.services import get_or_create_size_fitting
        sf = get_or_create_size_fitting(model, actor_profile_id=created_by_id)

    version = _active_grading_version(sf)
    if version is None:
        # ── S45/B — MESURAR PRENDA NO EXIGEIX PROPAGAT (regla d'Agus, Patró C) ──────────
        # El guard que hi havia aquí («cal generar les talles primer») era el guard de
        # PROPAGAR dit a la porta de MESURAR, i tancava el cas que el domini sí que
        # admet: un PROTOTIP que ha arribat a la sala sense graduació definida. La
        # modista el té a les mans i no el pot anotar enlloc.
        #
        # EL GUARD ES PARTEIX PER CAMÍ, no per endpoint (llei S43):
        #   · PROPAGAR segueix exigint graduació — `generate_grading_view` refusa amb 400
        #     si `not _te_regles(model)` (`models_app/views.py:3014-3016`). CAP CANVI.
        #   · MESURAR PRENDA no l'exigeix: aquí.
        #
        # 🔑 I NO CAL DECIDIR RES DEL DOMINI, perquè la resposta JA ESTÀ CONSTRUÏDA:
        # `reconcilia_linies` (:640-660) ja sap néixer sense spec —«el teòric d'una
        # mesura nova: l'spec de la versió activa si n'hi ha i, si no, la base del model
        # a la talla base»— i es crida tres línies més avall. Sense propagació la peça
        # neix, doncs, amb les línies de la TALLA BASE tretes de `BaseMeasurement`, que
        # és exactament el que es pot prendre d'un proto: hi ha una peça física, i és
        # d'una talla. Les altres talles no hi són perquè encara no existeixen.
        #
        # PER QUÈ ES MATERIALITZA LA VERSIÓ I NO ES FA NUL·LABLE EL FK: `PieceFitting.
        # grading_version` és NOT NULL (`fitting/models.py:395`) i penja d'ell mig
        # circuit (`consolidate_base_from_fitting:685`, `close_piece_fitting:765`). El
        # contenidor buit els deixa a tots vius sense migració i sense tocar-ne cap. És
        # el MATEIX camí lliure que aquesta funció ja fa amb el SizeFitting vint línies
        # amunt: materialitzar en l'acte en lloc de bloquejar.
        #
        # ⚠️ LA VERSIÓ NEIX BUIDA I HO DIU: cap `GradedSpec`. `te_taula` i `te_propagacio`
        # segueixen sent FALSOS (`grading_status_view:3858`) — obrir una presa NO és
        # propagar, i cap pantalla ha de dir que ho sigui. El segell ho respecta:
        # `seal_model_grading` no segella una versió sense specs (v. allà).
        from django.db.models import Max
        from fhort.fitting.models import GradingVersion
        version = GradingVersion.objects.create(
            size_fitting=sf,
            version_number=(GradingVersion.objects.filter(size_fitting=sf).aggregate(
                m=Max('version_number'))['m'] or 0) + 1,
            is_active=True,
            creat_per_id=created_by_id,
            nom='Presa sense propagació',
            notes=('Versió materialitzada en obrir una presa sobre un model sense '
                   'graduació propagada (S45/B). Neix BUIDA: les línies surten de la '
                   'talla base del model.'),
        )
        logger.info(
            'create_piece_fitting: model %s sense GradingVersion activa → v%s buida '
            '(camí lliure de presa)', model.pk, version.version_number)

    pf = PieceFitting.objects.create(
        session=session,
        model=model,
        grading_version=version,
        created_by_id=created_by_id,
    )

    specs = GradedSpec.objects.filter(grading_version=version, is_active=True).select_related('pom')
    n = 0
    for spec in specs:
        # FASE_3/C1-ins — la línia CLONA l'spec, i per tant n'ha de clonar els DOS EIXOS.
        # Aquesta és la propagació més literal del tram: si l'spec és del folre, la línia és
        # del folre; si és de la sisa esquerra, la línia és de la sisa esquerra. Copiant
        # només `pom`/`size_label`/`valor`, dos specs germans generaven dues línies
        # indistingibles que xocaven amb la unicitat
        # `(piece_fitting, pom, size_label, capa, instancia)` — i, mentre la comporta ho
        # impedia, la modista hauria pres dues vegades la mateixa mesura sense saber quina.
        PieceFittingLine.objects.create(
            piece_fitting=pf,
            pom=spec.pom,
            size_label=spec.size_label,
            capa=spec.capa,
            instancia=spec.instancia,
            # SET-2/T5c — i el TERCER eix, pel mateix argument literal: si l'spec és de la
            # segona peça, la línia és de la segona peça. La sembra i la reconciliació han de
            # dir el mateix o la reconciliació que ve tot seguit (Q3) retiraria el que la
            # sembra acaba de crear.
            garment=spec.garment,
            valor_teoric=spec.graded_value_cm,
            valor_real=spec.graded_value_cm,  # copy, editable before close
        )
        n += 1

    # Q3 — i tot seguit es reconcilia amb el model VIU. La sembra ve de l'spec, que és una foto
    # de l'últim grading generat: un POM entrat al model després d'aquella generació no hi és, i
    # un d'esborrat hi segueix sent. La peça neix, doncs, ja quadrada amb el model.
    reconcilia_linies(pf)
    n = pf.linies.count()

    logger.info(f"PieceFitting {pf.pk} created for model {model_id}: {n} lines")
    return pf, n


# ── Q3 (06/08) — LA PRESA ES RECONCILIA AMB EL MODEL EN OBRIR-LA ─────────────────────────────
#
# 🔴 EL DEFECTE: `create_piece_fitting` SEMBRA les línies de l'spec en CREAR la peça, i mai més
# se les torna a mirar. Amb el MILEY (06/08), l'Agus va esborrar els POMs del model i en va
# entrar dotze de nous una hora abans del fitting: la presa i el PDF seguien portant els VELLS
# (SK L, A.2, CF L TOT, CH, HI, SK SW) — un model que ja no existeix, imprès i portat a la sala.
#
# LA REGLA: en OBRIR una presa (sessió Programada/Oberta) les línies es reconcilien amb els
# BaseMeasurement ACTIUS del model EN AQUELL MOMENT. POM nou al model → línia nova a la presa;
# POM esborrat del model → la línia no es pinta.
#
# ⚠️ LES SESSIONS TANCADES NO ES RECONCILIEN MAI. Una sessió segellada és ACTA: diu què es va
# mesurar aquell dia, i el model d'avui no la pot reescriure. Per això el primer que fa la
# funció és mirar l'estat i tornar sense tocar res.
#
# PER QUÈ ES BORREN les línies sobreres i no es filtren a la lectura: perquè el que es GRAVA ha
# de ser l'estat reconciliat (Q4). Si la línia visqués amagada, en segellar la sessió tornaria a
# sortir a l'acta i al PDF —congelada— una mesura que el model ja no té. La reconciliació passa
# sempre amb la sessió VIVA, o sigui que no toca cap acta.
#
# EL LLINDAR D'UNA MESURA MESURABLE és el mateix que ja aplica el size check
# (`services_size_check._materialize_lines`): `is_active=True` i `base_value_cm` informat. Una
# mesura sense valor base no té contra què comparar-se, i `valor_teoric` no admet NULL.
SESSIONS_VIVES = ('Programada', 'Oberta')


def reconcilia_linies(pf) -> dict:
    """Posa les línies d'una PieceFitting al dia amb els BaseMeasurement actius del model.

    Retorna {'creades', 'retirades', 'congelada'}. Amb la sessió segellada no toca res i
    torna `congelada=True`.
    """
    from fhort.fitting.models import GradedSpec, PieceFittingLine
    from fhort.models_app.models import BaseMeasurement

    if pf.session.estat not in SESSIONS_VIVES:
        return {'creades': 0, 'retirades': 0, 'congelada': True}

    model = pf.model
    base_size = (model.base_size_label or '').strip()

    # SET-2/T5c (2026-08-11) — LA CLAU PORTA EL `garment`, A LES TRES BANDES ALHORA.
    # La identitat d'una línia és de sis camps (`fitting/0026`) i la del seu origen de
    # quatre; aquí se'n comparaven tres. El dany NO era esborrar de més —deixant caure
    # l'eix als DOS costats, el predicat de `sobreres` queda més AMPLI que la identitat i
    # la línia de la 02 troba recer a la germana de la mare—: era per ABSÈNCIA.
    #   · `actives` col·lapsava les dues peces en una entrada → `a_crear` no podia generar
    #     mai més d'una línia i la mesura de la segona peça no arribava al full de presa.
    #   · `ja_hi_son` col·lapsava igual → amb una línia de la 02 ja existent, la de la mare
    #     es donava per feta i no naixia.
    # Els tres conjunts creixen ALHORA, com les quatre mapes de `graded-table`: si un
    # cresqués i un altre no, la reconciliació esborraria el que acaba de crear.
    actives = {
        (bm.pom_id, bm.capa, bm.instancia, bm.garment): bm
        for bm in BaseMeasurement.objects.filter(
            model=model, is_active=True, base_value_cm__isnull=False)
    }

    linies = list(PieceFittingLine.objects.filter(piece_fitting=pf))
    sobreres = [l.pk for l in linies
                if (l.pom_id, l.capa, l.instancia, l.garment) not in actives]
    if sobreres:
        PieceFittingLine.objects.filter(pk__in=sobreres).delete()

    fora = set(sobreres)
    ja_hi_son = {(l.pom_id, l.capa, l.instancia, l.garment)
                 for l in linies if l.pk not in fora}
    a_crear = [clau for clau in actives if clau not in ja_hi_son]

    creades = 0
    if a_crear:
        # El teòric d'una mesura nova: l'spec de la versió activa si n'hi ha (llavors la línia
        # neix amb totes les seves talles, com les seves germanes) i, si no, la base del model a
        # la talla base — que és l'única talla que la presa i el full pinten.
        specs = {}
        for s in GradedSpec.objects.filter(
                grading_version=pf.grading_version, is_active=True).values(
                'pom_id', 'capa', 'instancia', 'garment', 'size_label', 'graded_value_cm'):
            clau = (s['pom_id'], s['capa'], s['instancia'], s['garment'])
            specs.setdefault(clau, {})[s['size_label']] = s['graded_value_cm']

        for clau in a_crear:
            bm = actives[clau]
            per_talla = specs.get(clau)
            if not per_talla:
                if not base_size:
                    logger.warning(
                        'reconcilia_linies: %s sense talla base ni spec per %s — no es crea línia',
                        pf.pk, clau)
                    continue
                per_talla = {base_size: bm.base_value_cm}
            for size_label, valor in per_talla.items():
                PieceFittingLine.objects.create(
                    piece_fitting=pf,
                    pom_id=bm.pom_id,
                    size_label=size_label,
                    capa=bm.capa,
                    instancia=bm.instancia,
                    # SET-2/T5c — la línia neix de la seva MESURA i n'hereta la peça, igual
                    # que ja n'heretava els dos eixos de germanor. Sense això la línia de la
                    # 02 naixeria a la mare i la reconciliació següent l'esborraria.
                    garment=bm.garment,
                    valor_teoric=valor,
                    # Mateix criteri que la sembra (`create_piece_fitting`): el real neix com a
                    # còpia del teòric i és editable. Canviar-lo aquí faria que dues línies de
                    # la mateixa presa es comportessin diferent segons quan van néixer.
                    valor_real=valor,
                )
                creades += 1

    if sobreres or creades:
        logger.info('PieceFitting %s reconciliada: +%s línies, -%s línies',
                    pf.pk, creades, len(sobreres))
    return {'creades': creades, 'retirades': len(sobreres), 'congelada': False}


def consolidate_base_from_fitting(pf, *, auth_user=None):
    """B3: consolida les línies de TALLA BASE d'un PieceFitting a BaseMeasurement.

    Per cada línia de la talla base amb valor_real informat i ≠ valor_teoric (una
    rectificació real), escriu BaseMeasurement(model, pom).base_value_cm = valor_real,
    origen='FITTED' (el senyal F1 registra el canvi). Retorna la llista de línies base
    consolidades — el cridador hi fa Welford/versionat si cal.

    Reusat pel `close` (comportament idèntic al bloc inline anterior) i per la propagació
    conscient (consolidar la realitat mesurada abans que el motor llegeixi la base).
    """
    from fhort.fitting.models import PieceFittingLine
    from fhort.models_app.models import BaseMeasurement
    from fhort.models_app.services_derivacio import aplica as aplica_derivacio
    model = pf.model
    sf = pf.grading_version.size_fitting
    base_size = (model.base_size_label or '').strip()
    consolidated = []
    # D-31.21 — «la darrera mesura VÀLIDA escrita». Una línia REJECTED es desa i es veu, però
    # NO sembra: el rebuig diu que la PRESA no val, i consolidar-la escriuria a la mesura base
    # un número que la modista acaba de declarar dolent. L'exclusió va al queryset i no a un
    # `continue` del cos perquè d'aquest helper en pengen TRES coses —la consolidació a
    # `BaseMeasurement`, la derivació a les germanes i el Welford del cridador, que menja
    # `consolidated`—: filtrant a la font cap de les tres no la pot veure, i cap refosa futura
    # del cos no la pot perdre.
    linies = (PieceFittingLine.objects
              .filter(piece_fitting=pf)
              .exclude(decisio=PieceFittingLine.DECISIO_REJECTED)
              .select_related('pom'))
    for line in linies:
        if line.valor_real is None:
            continue
        if abs(line.valor_real - line.valor_teoric) < 1e-6:
            continue  # no change on this line
        if line.size_label.strip() != base_size:
            continue  # PEÇA 4: la sessió de fitting toca NOMÉS la talla base
        # FASE_3/C1-ins — la consolidació torna el valor mesurat a la SEVA mesura base. La
        # línia sap dir els dos eixos (els va heretar de l'spec, aquí a sobre); el lookup
        # els ha de dir també, o la rectificació d'una germana aterraria sobre l'altra i el
        # `get()` intern petaria amb MultipleObjectsReturned el dia que n'hi hagi dues.
        bm, _created = BaseMeasurement.objects.get_or_create(
            # SET-2/T5 — el tercer eix, i la línia el sap dir com sap dir els altres dos
            # (l'ha heretat de l'spec): la rectificació d'una peça ha d'aterrar a la SEVA
            # mesura base, no a la de l'altra.
            model=model, pom=line.pom, capa=line.capa, instancia=line.instancia,
            garment=line.garment,
            defaults={'base_value_cm': line.valor_real, 'origen': 'FITTED'},
        )
        # C3/E1 — el valor d'ABANS, capturat abans de trepitjar-lo: és el que fa calculable
        # l'increment que han de rebre les germanes. En una creació és None i no es deriva
        # (una fila nova no és conseqüència de res).
        valor_anterior = None if _created else bm.base_value_cm
        bm.base_value_cm = line.valor_real
        bm.origen = 'FITTED'
        bm._changed_by = auth_user
        bm._fitting_ref = sf            # MeasurementChangeLog.fitting_ref (→ SizeFitting)
        bm._motiu = f'Fitting · sessió {pf.session_id} · peça {pf.pk}'
        bm.save()
        # C3/E1 — LA DERIVACIÓ. Aquest és un dels dos únics punts d'escriptura de mesura de tot
        # el backend que coneix els seus eixos per CÒPIA i no per literal (els hereta de la
        # línia), i on el valor anterior, el nou i la fila hi són alhora: l'increment ja és
        # calculable aquí, sense endevinar res. Es mou el VALOR de les germanes, mai el
        # grading; la folgança es conserva sola.
        # Amb les comportes de C1/C1-ins vives no hi ha cap germana i això és un no-op.
        aplica_derivacio(
            bm, valor_anterior, line.valor_real, auth_user=auth_user, fitting_ref=sf,
            motiu_origen=f'fitting sessió {pf.session_id}')
        consolidated.append(line)
    return consolidated


def close_piece_fitting(piece_fitting_id: int, *, user_profile_id: int | None = None,
                        allow_reopen_sealed: bool = False) -> dict:
    """Close a PieceFitting, applying validated BASE real values with FUNCTIONAL versioning.

    PEÇA 4: la sessió de fitting toca NOMÉS la talla base. Per cada línia de la talla
    BASE on valor_real difereix de valor_teoric:
      - promociona a BaseMeasurement (canvi d'arrel) → el senyal F1 registra el canvi,
        measurements_version++, i el grading es regenera des de la base nova.
      - Welford s'alimenta amb el valor_real base (keyed by codi_client).
    Les talles NO-base s'IGNOREN aquí: els breaks per talla es fan a l'editor propagat
    del model (ModelGradingOverride via set-size-override, PEÇA 1/2), no en tancar la
    sessió. Qualsevol canvi base → NOVA GradingVersion (v+1) i es desactiva l'anterior
    (conservada); re-propaga la base a totes les talles (override→exception→regla→FIXED).
    El brain stub es crida un cop si hi ha hagut canvi.

    Returns: {'changed', 'base_changed', 'override_changed', 'new_version'}.
    'override_changed' es manté per compat. de forma però SEMPRE és False (PEÇA 4).
    """
    from fhort.fitting.models import PieceFitting

    pf = PieceFitting.objects.select_related(
        'model', 'grading_version', 'grading_version__size_fitting',
    ).get(pk=piece_fitting_id)
    model = pf.model
    sf = pf.grading_version.size_fitting

    # Resolve users: UserProfile (fitting layer) + its auth.User (F1 log layer).
    profile = None
    auth_user = None
    if user_profile_id:
        from fhort.accounts.models import UserProfile
        profile = UserProfile.objects.select_related('user').filter(pk=user_profile_id).first()
        auth_user = profile.user if profile else None

    override_changed = False

    # XA (sprint fonaments-de-gravat): tot el cos escriptor —consolidació a BaseMeasurement
    # (+ senyal F1), Welford, versionat funcional (guard D-1) i seal— dins UNA transacció.
    # Si el guard D-1 (o qualsevol pas posterior) llança, el rollback desfà BaseMeasurement,
    # MeasurementChangeLog i el Welford junts: cap escriptura residual. El ValueError propaga
    # fora del `with` (rollback) i la view el converteix en 400. Cap reordenació interna.
    with transaction.atomic():
        # Q3/Q4 — EL QUE ES GRAVA ÉS L'ESTAT RECONCILIAT. La sessió encara és viva (el segell ve
        # al final d'aquesta mateixa transacció), o sigui que aquesta és l'última finestra per
        # quadrar-la amb el model abans que l'acta es congeli. Sense això, l'acta i el PDF d'una
        # sessió tancada podrien portar mesures que el model ja no té.
        reconcilia_linies(pf)

        # PEÇA 4 / B3: la consolidació de la talla base a BaseMeasurement viu al helper
        # consolidate_base_from_fitting (compartit amb la propagació conscient). Les talles
        # no-base s'ignoren (els breaks per talla van per ModelGradingOverride). Welford i el
        # versionat es fan aquí sobre les línies consolidades.
        consolidated = consolidate_base_from_fitting(pf, auth_user=auth_user)
        changed = len(consolidated)
        base_changed = bool(consolidated)

        for line in consolidated:
            # Welford (keyed by codi_client within the tenant).
            if model.garment_type_id:
                try:
                    from fhort.pom.services import update_client_profile
                    update_client_profile(
                        codi_client=model.codi_client,
                        garment_type_id=model.garment_type_id,
                        pom_id=line.pom_id,
                        size=line.size_label,
                        value_cm=line.valor_real,
                    )
                except Exception as e:
                    logger.warning(f"Welford update failed: {e}")

        new_version_number = None
        if changed:
            # D4 (2026-07-21) — AQUÍ hi havia una crida a bump_grading_version_and_generate.
            # Tancar una peça de fitting ja NO propaga: consolida la BASE i prou. Propagar és
            # un acte conscient de la tècnica i té una sola porta (el botó «Propagar a grading»
            # → generar-grading). Llei de domini DECISIONS.md §2, que declarava aquesta
            # auto-propagació codi a jubilar; fins avui seguia viva.
            #
            # EL QUE NO ES PERD: measurements_version++ el feia NOMÉS el helper. Sense ell, una
            # base que es mou sota una versió segellada deixaria de detectar-se com a estal
            # (fitting/staleness.py compara amb generated_from_version). La consolidació de base
            # segueix, doncs, incrementant-lo; el que desapareix és la propagació, no el rastre.
            if base_changed:
                from django.db.models import F
                from fhort.models_app.models import Model
                Model.objects.filter(pk=model.pk).update(
                    measurements_version=F('measurements_version') + 1
                )

            # Brain stub (decoupled; no propagation yet). Ja no hi ha versió nova que passar-li:
            # el hook segueix disparant-se perquè la MESURA ha canviat, que és el que li importa.
            from fhort.fitting.brain import on_fitting_measurement_changed
            on_fitting_measurement_changed(
                piece_fitting_id=pf.pk,
                model_id=model.pk,
                base_changed=base_changed,
                new_grading_version_id=None,
            )

        # Segellat correcte: single-model tanca en gravar; GarmentSet espera que totes les
        # peces estiguin resoltes (session_can_advance). _seal_session és idempotent i captura
        # la durada real al tancament.
        _seal_session(pf.session)

    result = {
        'changed': changed,
        'base_changed': base_changed,
        'override_changed': override_changed,
        'new_version': new_version_number,
    }
    logger.info(f"PieceFitting {pf.pk} closed: {result}")
    return result


def discard_piece_fitting(piece_fitting_id: int) -> dict:
    """Revert a PieceFitting to its OPENING state: valor_real := valor_teoric for
    every line, atomically. Pure measurement revert — does NOT touch FittingSession,
    FittingPhoto, notes, gates, GradingVersion or grading. Returns {'reverted': N}.
    """
    from django.db import transaction
    from django.db.models import F
    from fhort.fitting.models import PieceFittingLine

    with transaction.atomic():
        reverted = (
            PieceFittingLine.objects
            .filter(piece_fitting_id=piece_fitting_id)
            .update(valor_real=F('valor_teoric'))
        )

    logger.info(f"PieceFitting {piece_fitting_id} discarded: {reverted} lines reverted")
    return {'reverted': reverted}


# ── Sprint 5B.3 helpers ──────────────────────────────────────────────────────

def _resolve_working_size_fitting(model):
    """The model's single working SizeFitting (prefer one with an active version)."""
    from fhort.fitting.models import SizeFitting, GradingVersion
    sfs = list(SizeFitting.objects.filter(model=model).order_by('numero'))
    if not sfs:
        return None
    for sf in sfs:
        if GradingVersion.objects.filter(size_fitting=sf, is_active=True).exists():
            return sf
    return sfs[0]


def _active_grading_version(sf):
    """Active GradingVersion of a SizeFitting (highest version_number wins)."""
    from fhort.fitting.models import GradingVersion
    return (
        GradingVersion.objects
        .filter(size_fitting=sf, is_active=True)
        .order_by('-version_number')
        .first()
    )


def vigent_grading_version(sf):
    """GradingVersion VIGENT d'un SizeFitting per a SUPERFÍCIES DE LECTURA
    (graded-table, taula-mesures, resposta de generar-grading): criteri ÚNIC compartit
    perquè tots els lectors coincideixin en "quina versió mana".

    is_active prioritari (via _active_grading_version, que desempata per -version_number);
    si cap versió és activa (anomalia de dades), fallback a la més recent
    (-version_number, després -data). NO es muta _active_grading_version perquè
    seal_model_grading / close_piece_fitting / generate_grading_view n'exigeixen
    estrictament l'activa.
    """
    from fhort.fitting.models import GradingVersion
    gv = _active_grading_version(sf)
    if gv is None:
        gv = (
            GradingVersion.objects
            .filter(size_fitting=sf)
            .order_by('-version_number', '-data')
            .first()
        )
    return gv


def seal_grading_version(version, *, user_profile_id=None, now=None):
    """L'ÚNIC escriptor del segell (G6-B/T2). Segella UNA GradingVersion concreta.

    Els tres camps van SEMPRE junts: `aprovada` sense `aprovada_per`/`data_aprovacio` és una
    versió aprovada per ningú i quan sigui — i n'hi ha DUES a staging (gv 30 i gv 53), d'un camí
    de codi que ja no existeix, que és com sabem que això havia passat de debò.

    Idempotent: re-segellar una versió ja aprovada NO reescriu qui la va aprovar ni quan. El
    primer que la va segellar és el que la va segellar.

    Des-segellar NO existeix, ni aquí ni per API: una versió aprovada se supera creant-ne una de
    nova (el bump), no desdient-se de l'aprovació.
    """
    from django.utils import timezone
    if version.aprovada:
        return version
    version.aprovada = True
    version.aprovada_per_id = user_profile_id
    version.data_aprovacio = now or timezone.now()
    version.save(update_fields=['aprovada', 'aprovada_per', 'data_aprovacio'])
    return version


def seal_model_grading(model, *, user_profile_id=None, now=None):
    """Segella (aprovada=True) la GradingVersion activa del SizeFitting de treball del model.

    D-3: el segellat és CONSEQÜÈNCIA de l'avanç de gate (decisió humana de maduresa),
    no de tancar una sessió de fitting. Retorna el pk de la versió segellada, o None si
    el model no té SizeFitting de treball ni versió activa.

    El segell l'escriu `seal_grading_version` (font única); aquí només es tria QUINA versió.
    """
    sf = _resolve_working_size_fitting(model)
    if sf is None:
        return None
    version = _active_grading_version(sf)
    if version is None:
        return None
    # S45/B — UNA VERSIÓ BUIDA NO ES SEGELLA. Des que «mesurar prenda» no exigeix propagat
    # (`create_piece_fitting`), obrir una presa sobre un proto materialitza una
    # GradingVersion SENSE cap `GradedSpec`. Segellar-la seria signar el no-res, i el dany
    # no és cosmètic: `bump_grading_version_and_generate` refusa amb el guard D-1 si
    # l'activa està aprovada (`pom/services.py:1091-1095`), o sigui que un segell sobre el
    # buit BLOQUEJARIA la primera propagació de debò d'aquell model i obligaria a una
    # reobertura explícita per superar una versió que no promet res.
    #
    # El predicat és el FET, no la procedència: «hi ha alguna cosa propagada?». Retorna
    # None, que és el senyal que el cridador ja sap llegir (`tasks/services_d.py:61` el
    # posa tal qual a `sealed_version`): avançar de fase segueix funcionant, i el que no
    # passa és el segell.
    from fhort.fitting.models import GradedSpec
    if not GradedSpec.objects.filter(grading_version=version, is_active=True).exists():
        logger.info(
            'seal_model_grading: model %s · v%s no té cap GradedSpec activa — no es segella',
            model.pk, version.version_number)
        return None
    return seal_grading_version(version, user_profile_id=user_profile_id, now=now).pk


# ═════════════════════════════════════════════════════════════════════════════
# Sprint 5B.4 — Two-level gate + manual phase advance + production seal
# ═════════════════════════════════════════════════════════════════════════════

_GATE_RESULTS = ('OK', 'NO_OK', 'EXCEPCIO')
_GATE_ADVANCEABLE = ('OK', 'EXCEPCIO')  # EXCEPCIO = accepted exception → advances


def set_piece_gate(
    piece_fitting_id: int,
    resultat: str,
    motiu: str = '',
    *,
    user_profile_id: int | None = None,
):
    """Set the gate of a PieceFitting (a step AFTER close). Records who/when.

    resultat ∈ {OK, NO_OK, EXCEPCIO}. NO_OK fires the brain stub (future re-opening).
    """
    from django.utils import timezone
    from fhort.fitting.models import PieceFitting

    if resultat not in _GATE_RESULTS:
        raise ValueError(f"resultat ha de ser un de {_GATE_RESULTS} (rebut: {resultat!r}).")

    pf = PieceFitting.objects.select_related('model').get(pk=piece_fitting_id)
    pf.gate = resultat
    pf.gate_motiu = motiu or ''
    pf.gate_per_id = user_profile_id
    pf.gate_at = timezone.now()
    pf.save(update_fields=['gate', 'gate_motiu', 'gate_per', 'gate_at'])

    if resultat == 'NO_OK':
        # "Fallar és individual": signal the brain so it can later re-open this
        # piece's tasks. Stub today (no propagation).
        from fhort.fitting.brain import on_fitting_measurement_changed
        on_fitting_measurement_changed(
            piece_fitting_id=pf.pk,
            model_id=pf.model_id,
            base_changed=False,
            new_grading_version_id=None,
        )

    # 3r trigger: en gatejar, si la sessió (GarmentSet) ja té totes les peces resoltes
    # → es segella aquí (sense esperar advance_phase). Idempotent.
    _seal_session(pf.session)

    logger.info(f"PieceFitting {pf.pk} gate set to {resultat}")
    return pf


def session_can_advance(session_id: int) -> bool:
    """DERIVED (not stored): the session may advance iff every PieceFitting gate is
    in {OK, EXCEPCIO} and there is at least one piece (none Pendent/NO_OK)."""
    from fhort.fitting.models import PieceFitting

    gates = list(
        PieceFitting.objects.filter(session_id=session_id).values_list('gate', flat=True)
    )
    if not gates:
        return False
    return all(g in _GATE_ADVANCEABLE for g in gates)


def _seal_session(session):
    """Segella una FittingSession (→Tancada) i captura la durada real. Idempotent.
    GarmentSet: només segella si totes les peces estan resoltes (session_can_advance,
    gates ∈ {OK, EXCEPCIO}). Single-model: segella directament."""
    if session.estat == 'Tancada':
        return  # idempotent
    if session.garment_set_id and not session_can_advance(session.id):
        return  # peces pendents o NO_OK → encara no es tanca
    session.estat = 'Tancada'
    fields = ['estat']
    if session.finished_at is None:     # Peça 1 — marca real de tancament
        session.finished_at = timezone.now()
        fields.append('finished_at')
    session.save(update_fields=fields)
    # Allibera la franja de fitting de la cua dels assistents (no-fatal).
    try:
        attendee_ids = list(session.attendees.values_list('id', flat=True))
        if attendee_ids:
            from fhort.planning.plan_service import recompute_for_technicians
            recompute_for_technicians(set(attendee_ids))
    except Exception:
        logger.exception('recompute post-seal no-fatal')
    _capture_duration(session)


def _capture_duration(session):
    """Captura la durada real de la sessió cap a FittingDurationStat (Welford, per model).
    Sense start_time → no es mesura. Durada < 0 o > 240 min → descartada (soroll)."""
    if not session.start_time:
        return  # guard: sense hora d'inici no podem mesurar
    import datetime as _dt
    from django.utils import timezone
    start_dt = timezone.make_aware(_dt.datetime.combine(session.data, session.start_time))
    durada_real = (timezone.now() - start_dt).total_seconds() / 60
    if durada_real < 0 or durada_real > 240:
        return  # guard de soroll
    n = (session.piece_fittings.count() or 1) if session.garment_set_id else 1
    update_fitting_duration_stat(durada_real / n)


def update_fitting_duration_stat(value_minutes):
    """Welford incremental de durada real per model de sessió (singleton pk=1).
    Mateix patró que pom.services.update_client_profile."""
    from fhort.fitting.models import FittingDurationStat
    stat, _ = FittingDurationStat.objects.get_or_create(pk=1)
    n = stat.n_mostres + 1
    delta = value_minutes - stat.mitjana
    new_mean = stat.mitjana + delta / n
    delta2 = value_minutes - new_mean
    new_m2 = stat.m2_acum + delta * delta2
    stat.n_mostres = n
    stat.mitjana = round(new_mean, 2)
    stat.m2_acum = new_m2
    stat.desviacio = round((new_m2 / n) ** 0.5, 3) if n > 1 else 0.0
    stat.save()
    return stat


@transaction.atomic
def advance_phase(session_id: int, nova_fase: str, *, user_profile_id: int | None = None) -> dict:
    """Manual phase advance: the responsible person CHOOSES nova_fase (may skip,
    repeat or go back — we do NOT compute "the next one").

    Guards: session Oberta + session_can_advance + nova_fase ∈ Model.FASE_CHOICES.
    For each PieceFitting: seal its vigent GradingVersion (aprovada + aprovada_per +
    data_aprovacio) and set its Model.fase_actual = nova_fase. Closes the session.

    Per-piece TOP guard: a piece already at 'TOP' asked to advance from TOP is a
    no-op (skipped, reported), not an error.
    """
    from fhort.fitting.models import FittingSession, PieceFitting
    from fhort.models_app.models import Model

    valid_phases = {c[0] for c in Model.FASE_CHOICES}
    if nova_fase not in valid_phases:
        raise ValueError(f"nova_fase ha de ser ∈ {sorted(valid_phases)} (rebut: {nova_fase!r}).")

    session = FittingSession.objects.get(pk=session_id)
    if session.estat != 'Oberta':
        raise ValueError(f"La sessió ja està {session.estat}; només s'avança des d'Oberta.")
    if not session_can_advance(session_id):
        raise ValueError("La sessió no pot avançar: hi ha peces Pendent o NO_OK.")

    pieces = list(
        PieceFitting.objects.filter(session_id=session_id)
        .select_related('model', 'grading_version', 'grading_version__size_fitting')
    )

    # Regla dura (Sprint E): pre-check de confecció ABANS de cap mutació, per evitar estat
    # parcial en sessions multi-model. Els models a TOP se salten (no avancen, no s'exigeixen).
    from fhort.tasks.services_e import has_delivered_production
    missing = sorted({
        pf.model.pk for pf in pieces
        if pf.model.fase_actual != 'TOP'
        and not has_delivered_production(pf.model.pk, pf.model.fase_actual)
    })
    if missing:
        raise ValueError(
            f"No es pot avançar: cap confecció entregada per a la fase actual dels models {missing}."
        )

    # D-3: 'sealed' i 'advanced' queden SEMPRE buits a posta (fitting ja no segella ni
    # avança fase; vegeu peces 2 i 3). Es conserven al result per estabilitat de la forma.
    sealed = []
    advanced = []
    skipped_top = []

    for pf in pieces:
        model = pf.model
        if model.fase_actual == 'TOP':
            skipped_top.append(model.pk)
            continue

        # D-3 peça 2: el segellat del grading (aprovada=True) ja NO es fa en tancar la
        # sessió de fitting; és conseqüència de l'avanç de gate
        # (tasks.advance_phase_gate → fitting.seal_model_grading).
        # D-3 peça 3: fitting.advance_phase TAMPOC escriu Model.fase_actual ni crea
        # GateEvent. L'avanç de fase és competència EXCLUSIVA de l'avanç de gate
        # (tasks.advance_phase_gate, únic amo de fase_actual). La sessió de fitting és
        # només indicador de maduresa i es tanca amb _seal_session.

    _seal_session(session)

    result = {
        'nova_fase': nova_fase,
        'advanced_models': advanced,
        'sealed_versions': sealed,
        'skipped_top_models': skipped_top,
    }
    logger.info(f"Session {session_id} advanced: {result}")
    return result


# ═════════════════════════════════════════════════════════════════════════════
# Peça 2 — Gestió de convocatòria + segellat independent.
# Operacions de grup (per `convocatoria` UUID) i de cicle de vida de sessió.
# "Viu" = estat NOT IN (Tancada, Anullada).
# ═════════════════════════════════════════════════════════════════════════════
_DEAD_ESTATS = ['Tancada', 'Anullada']


def _group_live_qs(conv_uuid):
    """Sessions vives d'un grup (convocatoria), ordenades cronològicament."""
    from .models import FittingSession
    return (FittingSession.objects
            .filter(convocatoria=conv_uuid)
            .exclude(estat__in=_DEAD_ESTATS)
            .order_by('data', 'start_time', 'id'))


def _recompute_attendees(profile_ids):
    """Recompute no-fatal de la cua de planificació d'uns assistents."""
    if not profile_ids:
        return
    try:
        from fhort.planning.plan_service import recompute_for_technicians
        recompute_for_technicians(set(profile_ids))
    except Exception:
        logger.exception('recompute no-fatal')


def reschedule_group(conv_uuid, data, start_time=None):
    """(Op 1) Re-programa les sessions VIVES del grup. Manté l'interval relatiu
    original entre start_times (offset respecte la primera sessió amb hora). Si
    `start_time` és None, només canvia la data. Retorna [ids actualitzats]."""
    import datetime as _dt
    lives = list(_group_live_qs(conv_uuid))
    if not lives:
        return []
    aff_profiles = set()
    updated = []

    if start_time is None:
        for s in lives:
            s.data = data
            s.save(update_fields=['data'])
            updated.append(s.id)
            aff_profiles.update(s.attendees.values_list('id', flat=True))
        _recompute_attendees(aff_profiles)
        return updated

    # Re-encadenar mantenint l'offset relatiu respecte la primera start_time del grup.
    D0 = _dt.date(2000, 1, 1)
    bases = [s.start_time for s in lives if s.start_time is not None]
    base_dt = _dt.datetime.combine(D0, min(bases)) if bases else None
    new_base_dt = _dt.datetime.combine(D0, start_time)
    for s in lives:
        s.data = data
        if s.start_time is not None and base_dt is not None:
            offset = _dt.datetime.combine(D0, s.start_time) - base_dt
            s.start_time = (new_base_dt + offset).time()
            s.save(update_fields=['data', 'start_time'])
        else:
            s.save(update_fields=['data'])
        updated.append(s.id)
        aff_profiles.update(s.attendees.values_list('id', flat=True))
    _recompute_attendees(aff_profiles)
    return updated


def _delete_session_if_allowed(session, conflict_msg=None):
    """DELETE físic si Programada i sense PieceFitting. Si no:
       Oberta o amb peces → SessionActionConflict (409);
       Tancada/Anullada → ValueError (400). Retorna l'id esborrat."""
    if conflict_msg is None:
        conflict_msg = ("La sessió ja ha estat oberta; usa /discard/ per "
                        "anul·lar-la amb motiu.")
    if session.estat in _DEAD_ESTATS:
        raise ValueError("Estat no permet eliminació.")
    if session.estat == 'Oberta' or session.piece_fittings.exists():
        raise SessionActionConflict(conflict_msg)
    sid = session.id
    profiles = list(session.attendees.values_list('id', flat=True))
    session.delete()
    _recompute_attendees(profiles)
    return sid


def discard_session(session_id, motiu=''):
    """(Op 3) Anul·la una sessió des de Programada o Oberta → Anullada + motiu +
    finished_at. Des de Tancada/Anullada → ValueError (400)."""
    from .models import FittingSession
    s = FittingSession.objects.get(pk=session_id)
    if s.estat not in ('Programada', 'Oberta'):
        raise ValueError(
            f"La sessió està {s.estat}; només es pot anul·lar des de Programada o Oberta.")
    s.estat = 'Anullada'
    s.motiu_anullacio = motiu or ''
    s.finished_at = timezone.now()
    s.save(update_fields=['estat', 'motiu_anullacio', 'finished_at'])
    _recompute_attendees(list(s.attendees.values_list('id', flat=True)))
    return s


def add_model_to_group(conv_uuid, model_id, *, fase=None, created_by_id=None, force=False):
    """(Op 4) Afegeix un model nou al grup. 409 si el model ja hi té sessió viva.
    Encadena start_time al final de l'última sessió viva (start_time + duracio_minuts,
    calendari d'empresa). Aplica el guard de solapament existent (_skip_guard=False)."""
    import datetime as _dt
    from .models import FittingSession

    if not FittingSession.objects.filter(convocatoria=conv_uuid).exists():
        raise ValueError("Convocatòria no trobada.")
    if FittingSession.objects.filter(
            convocatoria=conv_uuid, model_id=model_id
            ).exclude(estat__in=_DEAD_ESTATS).exists():
        raise SessionActionConflict("Model ja és al grup.")

    last = _group_live_qs(conv_uuid).last()
    if fase is None:
        any_session = (FittingSession.objects.filter(convocatoria=conv_uuid)
                       .order_by('data', 'start_time', 'id').first())
        fase = (last or any_session).fase

    data = last.data if last else timezone.now().date()
    duracio = (last.duracio_minuts if last and last.duracio_minuts else 10)
    start_time = None
    if last and last.start_time is not None:
        from fhort.planning.calendar_service import add_working_minutes
        start_dt = _dt.datetime.combine(last.data, last.start_time)
        end_dt = add_working_minutes(None, start_dt, last.duracio_minuts or 10)
        data = end_dt.date()
        start_time = end_dt.time()

    responsable_id = last.responsable_id if last else None
    attendee_ids = list(last.attendees.values_list('id', flat=True)) if last else []

    session = schedule_session(
        fase=fase, data=data, responsable_id=responsable_id,
        model_id=model_id, start_time=start_time,
        duracio_minuts=duracio, attendee_ids=attendee_ids,
        created_by_id=created_by_id, force=force,
        _skip_guard=False,   # Op 4: guard de solapament ACTIU
    )
    session.convocatoria = conv_uuid
    session.save(update_fields=['convocatoria'])
    return session


def remove_model_from_group(conv_uuid, model_id):
    """(Op 5) Treu un model del grup. Programada sense peces → DELETE físic;
    Oberta o amb peces → 409 'Usa /discard/'; Tancada/Anullada → 400.
    Retorna l'id esborrat."""
    from .models import FittingSession
    qs = (FittingSession.objects
          .filter(convocatoria=conv_uuid, model_id=model_id)
          .order_by('id'))
    if not qs.exists():
        raise ValueError("El model no és al grup.")
    live = qs.exclude(estat__in=_DEAD_ESTATS).first()
    target = live or qs.first()
    return _delete_session_if_allowed(target, conflict_msg="Usa /discard/ per anul·lar-la amb motiu.")


def set_group_attendees(conv_uuid, attendee_ids):
    """(Op 6) Substitueix (set) el M2M attendees de TOTES les sessions vives del grup.
    Retorna [ids actualitzats]."""
    lives = list(_group_live_qs(conv_uuid))
    aff_profiles = set(int(a) for a in (attendee_ids or []))
    updated = []
    for s in lives:
        aff_profiles.update(s.attendees.values_list('id', flat=True))  # també els trets
        s.attendees.set(attendee_ids or [])
        updated.append(s.id)
    _recompute_attendees(aff_profiles)
    return updated


def seal_session(session_id):
    """(Op 7) Segellat INDEPENDENT: crida _seal_session (idempotent, marca finished_at,
    allibera franja). NO toca fase del model ni crida advance_phase. Anullada → 400."""
    from .models import FittingSession
    s = FittingSession.objects.get(pk=session_id)
    if s.estat == 'Anullada':
        raise ValueError("Una sessió anul·lada no es pot segellar.")
    _seal_session(s)
    s.refresh_from_db()
    return s


def delete_group(conv_uuid):
    """(Ajust 1) Elimina en BLOC totes les sessions d'una convocatòria — ATÒMIC.

    Conflicte = sessió Oberta o amb PieceFitting. Si n'hi ha cap → NO esborra res i
    retorna {'ok': False, 'conflicts': [{id, model_codi, model_nom}]}. Si no n'hi ha
    cap → esborra TOTES i retorna {'ok': True, 'removed': [ids]}."""
    from .models import FittingSession
    sessions = list(FittingSession.objects.filter(convocatoria=conv_uuid).select_related('model'))
    if not sessions:
        raise ValueError("Convocatòria no trobada.")
    conflicts = [s for s in sessions if s.estat == 'Oberta' or s.piece_fittings.exists()]
    if conflicts:
        return {'ok': False, 'conflicts': [
            {'id': s.id,
             'model_codi': (s.model.codi_intern if s.model_id else None),
             'model_nom': (s.model.nom_prenda if s.model_id else None)}
            for s in conflicts]}
    profiles = set()
    for s in sessions:
        profiles.update(s.attendees.values_list('id', flat=True))
    ids = [s.id for s in sessions]
    with transaction.atomic():
        FittingSession.objects.filter(id__in=ids).delete()
    _recompute_attendees(profiles)
    return {'ok': True, 'removed': ids}
