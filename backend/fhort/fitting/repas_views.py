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

from .models import PieceFitting, PieceFittingLine

# Contextos de `MeasurementChangeLog` que són algú MESURANT una peça. La resta (import,
# standard, calculated, item_standard, copied, federat) són moviments de dades, no preses.
CONTEXTOS_DE_FITTING = ('fitting', 'checked', 'manual')


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
    """
    from fhort.models_app.models import SizeCheckLine

    etiquetes = dict(SizeCheckLine.DECISIO_CHOICES)
    fora = {}
    for l in (SizeCheckLine.objects
              .filter(size_check__model_id=model_id)
              .only('size_check_id', 'pom_id', 'decisio', 'nota')):
        text = ' · '.join(filter(None, [
            etiquetes.get(l.decisio) if l.decisio else None,
            (l.nota or '').strip() or None,
        ]))
        if text:
            fora[(l.size_check_id, l.pom_id)] = text
    return fora


def _check_id_del_motiu(motiu):
    """`'Size check · check 42'` → 42. Qualsevol altra cosa → None (mai llança)."""
    m = re.search(r'check\s+(\d+)\s*$', motiu or '')
    return int(m.group(1)) if m else None


def _etapes_de_fitting(model_id):
    """Esdeveniments de fitting escrits a la TAULA DE MESURES.

    Retorna `(etapes, celles)`:
      · etapes  → [{key, context, at}] en ordre cronològic
      · celles → {key: {pom_id: {'valor_real', 'nota'}}}

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
            etapes.append({'key': clau, 'context': c.context, 'at': c.created_at})
            celles[clau] = {}
        check_id = _check_id_del_motiu(c.motiu)
        celles[clau][c.pom_id] = {
            'valor_real': float(c.valor_nou),
            'nota': notes.get((check_id, c.pom_id), '') if check_id else '',
        }
    return etapes, celles


class FittingRepasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, model_id):
        model = get_object_or_404(Model, pk=model_id)

        # Peces d'aquest model, en ordre CRONOLÒGIC de sessió (data; id com a desempat
        # estable per a dues sessions el mateix dia).
        peces = list(
            PieceFitting.objects
            .filter(model_id=model.id)
            .exclude(session__estat='Anullada')
            .select_related('session', 'session__responsable')
            .order_by('session__data', 'session__id')
        )
        peca_per_sessio = {p.session_id: p for p in peces}

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
        labels = {l.size_label for l in linies}
        if etapes and base:
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

        # Nomenclatura i ordre de fitxa: BaseMeasurement del model, el mateix camí que
        # l'editor G1 i la taula de mesures (una query, tres mapes).
        # R1 (31/07) — el BATEIG hi viatja també: és del MODEL, com `ordre` i `nom_fitxa`, i
        # sense ell la taula fitting_history de la fitxa imprimia el nom del catàleg d'un POM
        # que el tècnic havia rebatejat.
        bm_data = list(BaseMeasurement.objects.filter(model_id=model.id)
                       .values_list('pom_id', 'ordre', 'nom_fitxa', 'id',
                                    'nom_canonic_model', 'nom_traduit_model'))
        ordre_map = {p: o for p, o, _, _, _, _ in bm_data}
        nom_fitxa_map = {p: nf for p, _, nf, _, _, _ in bm_data}
        bm_id_map = {p: i for p, _, _, i, _, _ in bm_data}
        bateig_map = {p: (nc or '', nt or '') for p, _, _, _, nc, nt in bm_data}

        # Files = els POMs que s'han fitat en aquesta talla (no el cens sencer de POMs del
        # model: una fila buida a totes les sessions no és repàs, és soroll). Els POMs que
        # només apareixen a les etapes també fan fila: si no, un model sense cap sessió
        # tindria columnes i cap fila.
        files = {}

        def _fila(pom_id, pom):
            fila = files.get(pom_id)
            if fila is None:
                fila = files[pom_id] = {
                    'pom_id': pom_id,
                    'codi': nom_fitxa_map.get(pom_id) or (pom.pom_code if pom else ''),
                    'pom_code': pom.pom_code if pom else '',
                    'nom_en': pom.name_en if pom else '',
                    'nom_local': pom.name_cat if pom else '',
                    # CRUS i al costat del catàleg: '' = no batejat → mana el catàleg.
                    'nom_canonic_model': (bateig_map.get(pom_id) or ('', ''))[0],
                    'nom_traduit_model': (bateig_map.get(pom_id) or ('', ''))[1],
                    'nom_fitxa': nom_fitxa_map.get(pom_id),
                    'bm_id': bm_id_map.get(pom_id),
                    'is_key': pom.is_key_measure if pom else False,
                    'valors': {},
                    'ultim_comentari': None,
                }
            return fila

        for l in linies:
            if l.size_label != talla:
                continue
            _fila(l.pom_id, l.pom)['valors'][str(l.piece_fitting.session_id)] = {
                'valor_real': l.valor_real,
                'valor_teoric': l.valor_teoric,
                'nota': l.nota or '',
            }

        # Etapes: els POMs que hi surten poden no haver estat mai en cap sessió. Es resolen
        # d'una tacada (sense N+1) i només els que encara no tenen fila.
        poms_etapa = {pid for celles in etapa_celles.values() for pid in celles}
        if poms_etapa:
            from fhort.pom.models import POMMaster
            poms = {p.id: p for p in POMMaster.objects.filter(id__in=poms_etapa)
                    .select_related('pom_global')}
            for clau, celles in etapa_celles.items():
                for pom_id, dades in celles.items():
                    _fila(pom_id, poms.get(pom_id))['valors'][clau] = {
                        'valor_real': dades['valor_real'],
                        # Una etapa no porta valor teòric: el log guarda el que es va mesurar,
                        # no contra què. Null i prou — inventar-lo seria pitjor que no dir-ho.
                        'valor_teoric': None,
                        'nota': dades['nota'],
                    }

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

        rows = sorted(files.values(), key=lambda r: (ordre_map.get(r['pom_id'], 10 ** 9), r['pom_id']))

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
