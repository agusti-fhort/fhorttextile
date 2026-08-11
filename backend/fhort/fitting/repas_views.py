"""Repàs de fittings d'un model — taula POM × esdeveniments de fitting (LECTURA PURA).

GET /api/v1/fitting/model/<model_id>/repas/?talla=<size_label>

La superfície de FER fittings ja existeix (l'editor G1: PieceFittingGridSerializer, eix =
versions de grading d'UNA sessió). Aquí no es reinventa: es gira l'eix. La de REPASSAR
recull TOT el que és fitting del model i ho posa en columnes cronològiques, amb els
COMENTARIS que algú va escriure però que després ningú tornava a llegir.

UN FITTING NO ÉS SEMPRE UNA FittingSession (decisió Agus, 28/07). Al despatx els fittings
s'escriuen a mà i s'entren a la TAULA DE MESURES, sense obrir cap sessió. El cens de `fhort`
ho confirma: 13 models tenen història de mesures i només 3 tenen PieceFitting — per a 10
models el Repàs deia «cap fitting registrat» mentre la feina hi era, escrita a l'altra
taula. Per això la font són DUES, fusionades cronològicament:

  A) FittingSession/PieceFitting — el fitting fet amb l'eina.
  B) MeasurementChangeLog — les preses escrites a la taula de mesures.

CRITERI D'INCLUSIÓ DE (B), en una sola regla: un canvi compta com a esdeveniment de fitting
si el seu context és de mesura humana (fitting/checked/manual) I RE-MESURA un valor que ja
existia (`valor_anterior` no nul). El segon tros és el que separa el gra de la palla:

  · `manual` amb valor_anterior NUL = algú donant d'alta la fitxa per primera vegada. No és
    un fitting, és l'espec inicial. Al cens de `fhort` són 23 de 28 events manuals.
  · `manual` amb valor_anterior = algú tornant a mesurar i corregint. AIXÒ és el fitting
    escrit a mà que la decisió d'Agus demana recollir.

`import`, `standard`, `calculated`, `item_standard` i `copied` queden fora sempre: cap d'ells
és algú mesurant una peça.

LA TAULA DE MESURES ÉS INTOCABLE (decisió Agus, innegociable: és l'eina d'impressió per als
fittings presencials). Aquest mòdul llegeix el MODEL `MeasurementChangeLog` directament i no
importa, crida ni modifica res de `base_stages_view` ni de cap serializer que aquella taula
faci servir. L'agrupació per (context, segon) es re-implementa aquí a posta: compartir-la
voldria dir tocar `models_app/views.py`, i el pin
`models_app/test_base_stages_no_regressio.py` és la xarxa que ho verifica.

Mapa de dades:
  · sessions      → FittingSession (model=…), ordenades per data
  · valors        → PieceFittingLine (per PieceFitting = (sessió, model)), clau (pom, talla)
  · etapes        → MeasurementChangeLog agrupat per (context, segon) — NOMÉS talla base
  · comentaris    → PieceFittingLine.nota   (per CEL·LA: pom+talla+sessió)
                  → FittingSession.notes    (per SESSIÓ)
                  → PieceFitting.gate_motiu (per SESSIÓ i model: motiu del gate)
                  → SizeCheckLine.decisio/.nota (per POM i check: la columna DECISIÓ·NOTA de
                    la taula de mesures) — enganxada a l'etapa pel `motiu` del log, que ja
                    porta l'id del check; el pont és exacte, no per proximitat de rellotge

Una sessió entra a la taula si té PieceFitting d'aquest model (la peça es materialitza en
OBRIR la graella: existir-hi vol dir que el fitting s'ha fet). Les anul·lades queden fora:
la taula diu què s'ha fet, no què es va programar.

L'eix de TALLA és una sola talla per vista (default: la base del model), com l'editor de
fitting, que treballa la base i deixa el multi-talla a Escalat. `talles_disponibles` viatja
al payload perquè un selector de talla sigui una peça de front, no un endpoint nou.
Les etapes (B) viuen NOMÉS a talla base: `MeasurementChangeLog` és història de
`BaseMeasurement`, que per definició és la base. Per això només s'afegeixen quan la vista
mira la talla base — a una altra talla, mostrar-les seria mentir sobre quina talla es va
mesurar.

Res d'escriptura: cap POST/PATCH, cap efecte lateral.
"""
import re

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fhort.models_app.models import BaseMeasurement, MeasurementChangeLog, Model

from .esdeveniments import peces_amb_contingut
from .models import PieceFittingLine

# Contextos de `MeasurementChangeLog` que són algú MESURANT una peça. La resta (import,
# standard, calculated, item_standard, copied, federat) són moviments de dades, no preses.
CONTEXTOS_DE_FITTING = ('fitting', 'checked', 'manual')

#: L'id de la columna d'ENTRADA DE POMs. String i amb prefix, com les claus d'etapa: els ids de
#: sessió són enters i la columna d'origen no és cap sessió — que no ho sembli mai.
COL_ENTRADA = 'entrada'


def _ordena_talles(labels, size_run_model):
    """Ordena les talles per l'ordre del run del model; les que no hi són, al final (alfabètic)."""
    run = [s.strip() for s in (size_run_model or '').split('·') if s.strip()]
    pos = {s: i for i, s in enumerate(run)}
    return sorted(labels, key=lambda s: (pos.get(s, len(run)), s))


def _notes_de_check(model_id):
    """La columna DECISIÓ · NOTA de la taula de mesures, indexada per (check, pom).

    On viu: `SizeCheckLine.decisio` + `SizeCheckLine.nota` — per POM i per CHECK, no per
    etapa. `MeasurementChangeLog` no té camp de nota propi.

    Com s'hi enllaça: NO pel rellotge. Quan un check es resol, `resolve_size_check` desa la
    BaseMeasurement amb `bm._motiu = f'Size check · check {sc.pk}'`
    (models_app/services_size_check.py:189) i el signal el persisteix a
    `MeasurementChangeLog.motiu` (models_app/signals.py:295,307). O sigui que la fila del log
    ja DIU de quin check ve, i el pont és exacte. Enganxar-ho per timestamp hauria estat
    fràgil per milisegons; això no falla.

    FASE_2/C1-ins — la clau és `(check, pom, capa, instancia)`. Aquest lector no havia
    crescut ni a `(check, pom, capa)`, i el `.only()` era part del problema: excloïa `capa`,
    o sigui que l'eix ni tan sols arribava de la BD. La fila que hi consulta —una
    `MeasurementChangeLog`— sí que porta els dos eixos, així que la clau pot ser completa
    sense tocar cap contracte (FORMA A). Amb la clau curta, la nota d'una decisió sobre la
    sisa esquerra sortiria al costat del valor de la dreta.
    """
    from fhort.models_app.models import SizeCheckLine

    etiquetes = dict(SizeCheckLine.DECISIO_CHOICES)
    fora = {}
    for l in (SizeCheckLine.objects
              .filter(size_check__model_id=model_id)
              .only('size_check_id', 'pom_id', 'capa', 'instancia', 'garment',
                    'decisio', 'nota')):
        text = ' · '.join(filter(None, [
            etiquetes.get(l.decisio) if l.decisio else None,
            (l.nota or '').strip() or None,
        ]))
        if text:
            fora[(l.size_check_id, l.pom_id, l.capa, l.instancia, l.garment)] = text
    return fora


def _check_id_del_motiu(motiu):
    """`'Size check · check 42'` → 42. Qualsevol altra cosa → None (mai llança)."""
    m = re.search(r'check\s+(\d+)\s*$', motiu or '')
    return int(m.group(1)) if m else None


def _sessio_del_motiu(motiu):
    """`'Fitting · sessió 152 · peça 37'` → 152. Qualsevol altra cosa → None (mai llança).

    B2 — LA COLUMNA DUPLICADA. Un fitting fet amb l'eina escriu DUES vegades: les seves línies
    (`PieceFittingLine`, que fan la columna de sessió) i el retorn a la taula de mesures
    (`MeasurementChangeLog` amb `context='fitting'`, que feia una columna d'etapa). El mateix
    acte sortia dos cops, amb els mateixos números i la mateixa data.

    El pont és EXACTE i no per rellotge: el `motiu` del log ja diu de quina sessió ve
    (`services_fitting`), igual que el de check ja deia de quin check venia. Una etapa la
    sessió de la qual ja té columna no s'ensenya: no és un segon fitting.
    """
    m = re.search(r'sessi[óo]\s+(\d+)', motiu or '')
    return int(m.group(1)) if m else None


def _etapes_de_fitting(model_id):
    """Esdeveniments de fitting escrits a la TAULA DE MESURES.

    Retorna `(etapes, celles)`:
      · etapes  → [{key, context, at}] en ordre cronològic
      · celles → {key: {(pom_id, capa, instancia): {'valor_real', 'nota'}}}   ← C4

    NO hi ha carry-forward, a diferència de `base_stages_view`. Allà cada columna és un
    SNAPSHOT de la fitxa sencera en aquell moment (per això arrossega); aquí cada columna és
    UN ESDEVENIMENT, i el que la taula ha de dir és què es va mesurar aquell dia. Arrossegar
    hi faria semblar que es van prendre POMs que ningú va tocar — que és exactament la
    mentida que el Repàs ha d'evitar.

    L'agrupació per (context, segon) sí que és la mateixa idea que la taula de mesures, i es
    re-implementa aquí A POSTA: compartir-la voldria dir tocar `models_app/views.py`, i la
    taula de mesures és intocable.
    """
    notes = _notes_de_check(model_id)

    # C4 — L'ÀNCORA SE'N VA I LA CEL·LA S'INDEXA PER LA IDENTITAT SENCERA.
    #
    # L'àncora existia perquè `celles[clau]` s'indexava per `c.pom_id` pelat i és el que `_fila`
    # consulta: dues germanes mesurades el mateix segon es fondrien a la mateixa cel·la. Ara la
    # clau és `(pom_id, capa, instancia)` a les dues bandes —aquí i a `_fila`—, o sigui que el
    # filtre ja no protegeix res: només amagaria la presa de la germana d'una etapa on SÍ que
    # es va prendre, i la columna sortiria buida com si ningú no l'hagués mesurada.
    #
    # El `MeasurementChangeLog` porta els dos eixos des del signal F1 (`signals.py:335-341`), o
    # sigui que la clau completa surt de la fila mateixa: no cal endevinar-la ni fer cap join.
    logs = (MeasurementChangeLog.objects
            .filter(model_id=model_id,
                    context__in=CONTEXTOS_DE_FITTING,
                    valor_anterior__isnull=False)   # re-mesura, no alta inicial
            .order_by('created_at', 'id'))

    etapes, vistes, celles = [], set(), {}
    for c in logs:
        if c.valor_nou is None:
            continue
        clau = f"etapa:{c.context}@{c.created_at.replace(microsecond=0).isoformat()}"
        if clau not in vistes:
            vistes.add(clau)
            # `sessions` = les sessions que aquesta etapa cita al `motiu`. Amb elles, la vista
            # pot descartar l'etapa que només és el retorn d'un fitting que ja té columna.
            etapes.append({'key': clau, 'context': c.context, 'at': c.created_at,
                           'sessions': set()})
            celles[clau] = {}
        sid = _sessio_del_motiu(c.motiu)
        if sid is not None:
            next(e for e in etapes if e['key'] == clau)['sessions'].add(sid)
        check_id = _check_id_del_motiu(c.motiu)
        celles[clau][(c.pom_id, c.capa, c.instancia, c.garment)] = {
            'valor_real': float(c.valor_nou),
            'nota': notes.get((check_id, c.pom_id, c.capa, c.instancia, c.garment), '')
                    if check_id else '',
        }
    return etapes, celles


def _entrada_de_poms(model_id):
    """LA PRIMERA COLUMNA: la base d'origen, tal com va entrar (ordre d'Agus, 10/08).

    El Repàs començava per la primera sessió de fitting, o sigui que la taula ensenyava contra
    què s'havia mesurat sense ensenyar mai d'on es partia: els canvis es llegien uns contra els
    altres i el primer no es llegia contra res.

    D'ON SURT. `MeasurementChangeLog` és append-only i la primera fila de cada mesura és
    l'entrada de POMs (`motiu='gravar_pom'`, `context='manual'`, `valor_anterior` NUL —el
    criteri que aquest mòdul ja fa servir per separar l'alta inicial de la re-mesura). Es
    llegeix `valor_anterior` si hi és i, si no, `valor_nou`: si la primera fila d'una mesura
    resulta ser una modificació, el valor d'entrada és el que hi havia ABANS.

    Una mesura sense cap fila de log (sembrada sense història) cau a la seva base vigent: és
    l'única cosa certa que se'n pot dir, i callar deixaria la columna d'origen amb un forat que
    es llegiria com «no es va entrar mai».
    """
    entrada = {}
    for c in (MeasurementChangeLog.objects
              .filter(model_id=model_id)
              .order_by('-created_at', '-id')):     # descendent: l'última assignació guanya
        if c.valor_anterior is not None:
            entrada[(c.pom_id, c.capa, c.instancia, c.garment)] = float(c.valor_anterior)
        elif c.valor_nou is not None:
            entrada[(c.pom_id, c.capa, c.instancia, c.garment)] = float(c.valor_nou)
    for pom_id, capa, instancia, garment, valor in (
            BaseMeasurement.objects
            .filter(model_id=model_id, is_active=True, base_value_cm__isnull=False)
            .values_list('pom_id', 'capa', 'instancia', 'garment', 'base_value_cm')):
        entrada.setdefault((pom_id, capa, instancia, garment), valor)
    # Un model on ningú no ha entrat cap valor no té columna d'origen: `{}` la fa desaparèixer
    # sencera. Una columna de guionets diria que l'entrada existeix i és buida, que és mentida.
    return entrada


class FittingRepasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, model_id):
        model = get_object_or_404(Model, pk=model_id)

        # Peces d'aquest model, en ordre CRONOLÒGIC de sessió (data; id com a desempat
        # estable per a dues sessions el mateix dia).
        #
        # B2 — I NOMÉS LES QUE TENEN CONTINGUT (ordre d'Agus, 10/08: «fora les columnes
        # duplicades sense contingut»). Al 1320 hi havia dues columnes «DEV @09/08»: el fitting
        # 152, que es va fer, i la graella de la sessió 153, que algú va obrir i no va tocar
        # —`valor_real == valor_teoric` a les 28 files, cap veredicte, cap nota. El predicat viu
        # a `esdeveniments.py` i el comparteix la Comprovació: què és un fitting que ha passat
        # no pot tenir dues respostes.
        peces = peces_amb_contingut(model.id)

        # Totes les línies de cop (sense N+1). Les talles disponibles surten d'aquí: són les
        # que realment s'han pres, no les que el run del model promet.
        linies = list(
            PieceFittingLine.objects
            .filter(piece_fitting__in=peces)
            .select_related('pom', 'pom__pom_global', 'piece_fitting')
        )
        # Etapes de la taula de mesures. Viuen NOMÉS a talla base (el log és història de
        # BaseMeasurement), així que la base ha de ser una talla oferible encara que cap
        # sessió l'hagi tocada mai: si no, un model amb només etapes no tindria on pintar-les.
        etapes, etapa_celles = _etapes_de_fitting(model.id)
        base = (model.base_size_label or '').strip()
        # L'ENTRADA DE POMs, resolta abans de triar la talla: com les etapes, viu NOMÉS a la
        # base, i per tant la base ha de ser una talla oferible encara que cap sessió l'hagi
        # tocada mai. Sense això, un model amb mesures entrades i CAP fitting es quedava sense
        # cap talla —i per tant sense cap columna—, i el Repàs deia «cap fitting fet» amagant
        # justament la columna d'origen que havia d'ensenyar.
        entrada_de_poms = _entrada_de_poms(model.id)
        labels = {l.size_label for l in linies}
        if (etapes or entrada_de_poms) and base:
            labels.add(base)
        talles = _ordena_talles(labels, model.size_run_model)

        # Talla de la vista: la demanada si existeix; si no, la base del model; si la base no
        # s'ha pres mai, la primera disponible (millor una taula amb dades que una buida).
        demanada = (request.query_params.get('talla') or '').strip()
        talla = next((s for s in (demanada, base) if s and s in talles),
                     talles[0] if talles else None)

        # Les etapes només es pinten quan la vista mira la talla BASE: a una altra talla,
        # ensenyar-les seria mentir sobre quina talla es va mesurar.
        if talla != base:
            etapes, etapa_celles = [], {}

        columnes_sessio = [{
            'id': p.session_id,
            'origen': 'SESSIO',                      # eina de fitting
            'piece_fitting_id': p.id,
            'data': p.session.data.isoformat() if p.session.data else None,
            'fase': p.session.fase,
            'estat': p.session.estat,
            'responsable': getattr(p.session.responsable, 'nom_complet', None),
            'notes': p.session.notes or '',          # comentari de SESSIÓ
            'gate': p.gate,
            'gate_motiu': p.gate_motiu or '',        # comentari de SESSIÓ (motiu del gate)
            '_ordre': (p.session.data, p.session_id),
        } for p in peces]

        # B2 — L'ETAPA QUE NOMÉS ÉS EL RETORN D'UN FITTING NO FA COLUMNA. Un fitting fet amb
        # l'eina escriu a les seves línies I a la taula de mesures; la segona escriptura sortia
        # com una columna pròpia, amb la mateixa data i els mateixos números que la sessió del
        # costat. El pont és el `motiu` del log, que diu de quina sessió ve: exacte, no per
        # rellotge. Les etapes escrites A MÀ (sense sessió) es queden: són la decisió d'Agus del
        # 28/07 —un fitting no és sempre una FittingSession— i no dupliquen res.
        sessions_amb_columna = {p.session_id for p in peces}
        etapes = [e for e in etapes if not (e['sessions'] & sessions_amb_columna)]
        etapa_celles = {e['key']: etapa_celles[e['key']] for e in etapes}

        # Columnes d'etapa: MATEIXA forma que les de sessió (id/data/fase/estat/notes…),
        # perquè el front les pinti amb el mateix camí i no calgui una segona anatomia de
        # taula. `origen` és el que les distingeix, i és el que el front tradueix.
        columnes_etapa = [{
            'id': e['key'],                          # string: la clau de l'etapa
            'origen': e['context'].upper(),          # FITTING | CHECKED | MANUAL
            'piece_fitting_id': None,
            'data': e['at'].isoformat(),
            'fase': None,                            # una etapa no té fase de sessió
            'estat': None,
            'responsable': None,
            'notes': '',
            'gate': None,
            'gate_motiu': '',
            '_ordre': (e['at'].date(), 0),
        } for e in etapes]

        # FUSIÓ CRONOLÒGICA: sessions i etapes barrejades per data. Les sessions porten `data`
        # (un DateField) i les etapes un instant; es comparen per DIA, i dins del mateix dia
        # l'etapa va primer (0) perquè el desempat sigui estable i no depengui de l'ordre en
        # què s'han llegit les dues fonts.
        sessions = sorted(columnes_sessio + columnes_etapa,
                          key=lambda c: (c['_ordre'][0] is None, c['_ordre']))
        for c in sessions:
            c.pop('_ordre')

        # …I DAVANT DE TOT, L'ENTRADA DE POMs (ordre d'Agus, 10/08). No és un esdeveniment de
        # fitting: és d'on es parteix. Va amb la mateixa forma que les altres columnes perquè el
        # front no n'hagi d'estrenar cap camí, i amb `origen='ENTRADA'`, que és el que la
        # distingeix. Només a la talla BASE: la columna d'origen és `BaseMeasurement`, i a una
        # altra talla ensenyar-la seria mentir sobre quina talla es va entrar.
        entrada_celles = entrada_de_poms if talla == base else {}
        if entrada_celles:
            sessions.insert(0, {
                'id': COL_ENTRADA, 'origen': 'ENTRADA', 'piece_fitting_id': None,
                'data': None, 'fase': None, 'estat': None, 'responsable': None,
                'notes': '', 'gate': None, 'gate_motiu': '',
            })

        # Nomenclatura i ordre de fitxa: BaseMeasurement del model, el mateix camí que
        # l'editor G1 i la taula de mesures (una query, tres mapes).
        # R1 (31/07) — el BATEIG hi viatja també: és del MODEL, com `ordre` i `nom_fitxa`, i
        # sense ell la taula fitting_history de la fitxa imprimia el nom del catàleg d'un POM
        # que el tècnic havia rebatejat.
        # C4 — ELS QUATRE MAPES CREIXEN A LA CLAU SENCERA, i tots quatre alhora (era la llei
        # de C2/Onada 1 i segueix sent-ho): un que cresqui i un altre que no dona files amb
        # l'ordre d'una capa i el nom d'una altra.
        #
        # L'àncora existia perquè la fila que els consulta (`_fila`, aquí sota) s'indexava per
        # `pom_id` i no portava capa. Ara la fila porta la identitat sencera i la publica, o
        # sigui que el filtre seria pèrdua: la germana es quedaria sense nomenclatura de
        # croquis, sense bateig i **sense `bm_id`** — i el `bm_id` és l'àncora per PK de fila
        # que fa servir el corpus de cotes `.ftt`, o sigui que perdre'l no és cosmètic.
        bm_data = list(BaseMeasurement.objects
                       .filter(model_id=model.id)
                       .values_list('pom_id', 'capa', 'instancia', 'garment',
                                    'ordre', 'nom_fitxa', 'id',
                                    'nom_canonic_model', 'nom_traduit_model', 'is_active'))
        # SET-2/T6a — la PEÇA entra a TOTS els mapes d'aquesta vista alhora. La identitat
        # d'una fila del Repàs és la de la mesura, i amb la clau curta les dues peces del
        # mateix POM es fonien en una fila: una prenda desapareixia sencera de la taula i
        # la supervivent ensenyava el `bm_id`, el `nom_fitxa`, el bateig i els valors per
        # sessió de l'altra. Creixen JUNTS o no creixen: és la llei de C2/Onada 1.
        ordre_map = {(p, c, i, g): o for p, c, i, g, o, _, _, _, _, _ in bm_data}
        nom_fitxa_map = {(p, c, i, g): nf for p, c, i, g, _, nf, _, _, _, _ in bm_data}
        bm_id_map = {(p, c, i, g): bid for p, c, i, g, _, _, bid, _, _, _ in bm_data}
        bateig_map = {(p, c, i, g): (nc or '', nt or '')
                      for p, c, i, g, _, _, _, nc, nt, _ in bm_data}
        # Les mesures VIVES del model, en ordre de fitxa. És el cens que la taula ha de portar
        # sencer (v. la sembra de files, aquí sota).
        actives = [(p, c, i, g) for p, c, i, g, _, _, _, _, _, act in bm_data if act]

        # B2 — LA TAULA PORTA SEMPRE TOTES LES MESURES DEL MODEL (ordre d'Agus, 10/08).
        #
        # Fins ara les files eren «els POMs que s'han fitat en aquesta talla», amb el raonament
        # que una fila buida a totes les columnes és soroll. El raonament no s'aguanta des que
        # hi ha columna d'ENTRADA: una mesura que es va entrar i que cap fitting no ha tocat NO
        # és una fila buida —diu que ningú no l'ha comprovada mai—, i era precisament el que el
        # Repàs amagava. Qui repassa ha de veure el cens sencer i que hi falta gent.
        #
        # Les files se sembren PRIMER i en ordre de fitxa, de manera que les que vinguin només
        # de les etapes (POMs que ja no són mesura viva del model) s'hi afegeixin darrere.
        files = {}

        def _fila(ident, pom):
            """`ident` és `(pom_id, capa, instancia, garment)` — la identitat de la mesura,
            no el POM."""
            fila = files.get(ident)
            if fila is None:
                pom_id, capa, instancia, garment = ident
                fila = files[ident] = {
                    'pom_id': pom_id,
                    # C4 — els dos eixos al contracte: `pom_id` ja no desempata dues germanes.
                    'capa': capa,
                    'instancia': instancia,
                    # SET-2/T6a — i el TERCER, l'eix de la peça.
                    'garment': garment,
                    'codi': nom_fitxa_map.get(ident) or (pom.pom_code if pom else ''),
                    'pom_code': pom.pom_code if pom else '',
                    'nom_en': pom.name_en if pom else '',
                    'nom_local': pom.name_cat if pom else '',
                    # CRUS i al costat del catàleg: '' = no batejat → mana el catàleg.
                    'nom_canonic_model': (bateig_map.get(ident) or ('', ''))[0],
                    'nom_traduit_model': (bateig_map.get(ident) or ('', ''))[1],
                    'nom_fitxa': nom_fitxa_map.get(ident),
                    'bm_id': bm_id_map.get(ident),
                    'is_key': pom.is_key_measure if pom else False,
                    'valors': {},
                    'ultim_comentari': None,
                }
            return fila

        # La sembra del cens: una query per la nomenclatura i les files ja hi són totes, tinguin
        # presa o no.
        from fhort.pom.models import POMMaster
        cataleg = {p.id: p for p in POMMaster.objects
                   .filter(id__in={ident[0] for ident in actives})
                   .select_related('pom_global')}
        for ident in sorted(actives, key=lambda x: (ordre_map.get(x, 10 ** 9), x[0], x[1], x[2])):
            _fila(ident, cataleg.get(ident[0]))

        # L'ENTRADA DE POMs a la seva columna. Va abans de les preses perquè és d'on parteixen.
        for ident, valor in entrada_celles.items():
            if ident not in files and ident not in set(actives):
                continue                              # mesura morta: no se li obre fila nova
            fila = files.get(ident)
            if fila is None:
                continue
            fila['valors'][COL_ENTRADA] = {
                'valor_real': valor,
                'valor_teoric': None,     # l'entrada no es mesura contra res: és l'origen
                'nota': '',
                'veredicte': '',
            }

        for l in linies:
            if l.size_label != talla:
                continue
            # La línia de fitting SAP de quina germana parla: porta els dos eixos des de C1 i
            # C1-ins. Abans es col·lapsaven aquí, a `files[pom_id]`, i l'última llegida
            # guanyava la cel·la de la sessió.
            _fila((l.pom_id, l.capa, l.instancia, l.garment), l.pom)['valors'][
                str(l.piece_fitting.session_id)] = {
                'valor_real': l.valor_real,
                'valor_teoric': l.valor_teoric,
                'nota': l.nota or '',
                # B2 — EL VEREDICTE DE LA MODISTA viatja: és qui decideix el color d'un canvi
                # (decisió d'Agus, 10/08). Dada de domini, no es tradueix.
                'veredicte': l.decisio or '',
            }

        # Etapes: els POMs que hi surten poden no haver estat mai en cap sessió. Es resolen
        # d'una tacada (sense N+1) i només els que encara no tenen fila.
        # C4 — les cel·les d'etapa ja venen indexades per la identitat sencera; el que es
        # resol contra `POMMaster` segueix sent el POM, que és qui té la nomenclatura.
        poms_etapa = {ident[0] for celles in etapa_celles.values() for ident in celles}
        if poms_etapa:
            from fhort.pom.models import POMMaster
            poms = {p.id: p for p in POMMaster.objects.filter(id__in=poms_etapa)
                    .select_related('pom_global')}
            for clau, celles in etapa_celles.items():
                for ident, dades in celles.items():
                    _fila(ident, poms.get(ident[0]))['valors'][clau] = {
                        'valor_real': dades['valor_real'],
                        # Una etapa no porta valor teòric: el log guarda el que es va mesurar,
                        # no contra què. Null i prou — inventar-lo seria pitjor que no dir-ho.
                        'valor_teoric': None,
                        'nota': dades['nota'],
                        # Ni veredicte: ningú no va decidir res sobre una cel·la, es va
                        # escriure a la taula. El canvi es marcarà, el color no.
                        'veredicte': '',
                    }

        # ── ELS CANVIS ES MARQUEN (ordre d'Agus, 10/08) ───────────────────────────────────
        # Es decideix AQUÍ i no a la pantalla: qui sap l'ordre de les columnes és qui les ha
        # muntades, i un front que ho recalculés seria un segon lloc capaç de dir una cosa
        # diferent sobre el mateix parell de números.
        #
        # Un canvi és respecte de la columna ANTERIOR AMB VALOR de la mateixa fila, no respecte
        # de la columna immediatament anterior: si un fitting no va tocar un POM, el següent que
        # el toqui s'ha de llegir contra l'últim número que se'n va dir, no contra un buit. La
        # primera columna amb valor no és mai un canvi —no hi ha res abans a què comparar-la.
        ordre_columnes = [str(c['id']) for c in sessions]
        for fila in files.values():
            anterior = None
            for cid in ordre_columnes:
                cel = fila['valors'].get(cid)
                if cel is None:
                    continue
                v = cel.get('valor_real')
                if v is None:
                    continue
                cel['canvi'] = anterior is not None and float(v) != float(anterior)
                anterior = v

        # Últim comentari per POM: es recorren les columnes en ordre cronològic (sessions I
        # etapes barrejades) i es reté l'ÚLTIM no buit. No és «el de l'última columna»: si
        # l'última no comenta un POM, el que val és el darrer que algú en va dir, i la
        # columna diu d'on ve.
        for sessio in sessions:
            sid = str(sessio['id'])
            for fila in files.values():
                nota = (fila['valors'].get(sid) or {}).get('nota') or ''
                if nota:
                    fila['ultim_comentari'] = {
                        'text': nota, 'session_id': sessio['id'], 'data': sessio['data'],
                    }

        # C4 — l'ordre es demana amb la clau sencera i desempata pels dos eixos: dues germanes
        # comparteixen `ordre` (és el del POM a la fitxa) i, sense desempat, qui va primer ho
        # decidiria l'ordre d'inserció al dict, que ve del pla de Postgres.
        # SET-2/T6a — la PEÇA encapçala el desempat (llei de T9: «la prenda a fora»), i sense
        # ella la clau tornava a ser parcial: dues peces comparteixen `ordre`.
        rows = sorted(files.values(),
                      key=lambda r: (0 if not r['garment'] else 1, r['garment'],
                                     ordre_map.get((r['pom_id'], r['capa'], r['instancia'],
                                                    r['garment']), 10 ** 9),
                                     r['pom_id'], r['capa'], r['instancia']))

        return Response({
            'model': {
                'id': model.id, 'codi': model.codi_intern, 'nom': model.nom_prenda,
                'base_size_label': model.base_size_label, 'size_run_model': model.size_run_model,
            },
            'talla': talla,
            'talles_disponibles': talles,
            'sessions': sessions,
            'rows': rows,
        })
