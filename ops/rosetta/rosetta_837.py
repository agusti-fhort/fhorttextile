"""C + D · El Rosetta: les receptes del 1383 mesurades damunt del camp de la Montse.

**La pregunta.** La fitxa del 1383 (GradedSpec de la GV201 v9, segellada) diu quant ha de
fer cada POM a cada talla. El camp de la Montse diu on és cada punt del patró a cada talla.
Són dues descripcions del MATEIX vestit fetes per camins que no s'han tocat mai. El Rosetta
és posar-les una al costat de l'altra i mirar quant es separen, en mil·límetres.

── EL FORAT QUE MANA SOBRE TOT EL MÈTODE ────────────────────────────────────────
Les receptes `PatternPOM` del 1383 ancoren **19 de 20 àncores a la línia de COSIT** (capa
14 del patró mestre). El camp de la Montse **no porta capa 14**: només el contorn de TALL.
Les àncores, tal com estan escrites, no es poden resoldre damunt del banc.

No es resol ni ignorant-ho ni re-ancorant els POMs a mà. Es resol **transportant**:

  1. El camp només grada el contorn de TALL, i el grada com un camp de desplaçament per
     vèrtex (`camp_montse.PecaCamp.desplacaments`).
  2. Tota la resta de la geometria de la peça —la línia de cosit, els piquets— és una
     OFFSET d'aquell contorn. Sota grading, una offset segueix el seu contorn.
  3. Així que cada punt del patró mestre s'ancora al contorn de tall de la BASE per
     projecció —(aresta, t), que sota CONVENCIÓ-1 és una FRACCIÓ— i es mou amb el
     desplaçament interpolat d'aquella fracció.

**Què costa, i com se sap què costa.** El transport és exacte per als punts que JA són al
contorn de tall. Per als de la línia de cosit és una hipòtesi —«la costura grada com el tall
que té al costat»— i «al costat» no vol dir una sola cosa. Per això se'n mesuren TRES, i la
taula no en tria una: les corre totes.

  · `projeccio` — el punt més proper del contorn de tall (peu de la perpendicular).
  · `vertex`    — el VÈRTEX de tall més proper. És el portador més cru i el més independent:
                  no interpola res.
  · `fraccio`   — el punt del tall a la MATEIXA fracció d'arc, comptada des de l'origen de
                  CONVENCIÓ-1 de cada bucle. És el més fidel al que és una offset.

🚨 **I les tres no diuen el mateix.** A la sisa del DELANTERO, la projecció d'una àncora de
cosit cau a l'aresta 301 i el vèrtex més proper és el 306: **cinc vèrtexs de distància**,
perquè en una corba «el més proper» i «el de la mateixa posició» divergeixen. Allà on
divergeixen, el Δ del POM depèn del portador i **no és una mesura del vestit**: és una
mesura de la tria. La dispersió entre les tres vies va a la taula com a `incertesa`, i el
POM que la té més gran que la tolerància queda declarat **no resoluble sobre aquest banc**
—no «desviat»—, que és una cosa diferent i s'ha de dir diferent.

🔑 **I té una porta d'entrada que no es podia demanar millor:** a la talla BASE el
desplaçament és zero per construcció, o sigui que el valor que en surt ha de reproduir
`PatternPOM.valor_mesurat_cm` —el que el motor va llegir del patró de debò— **a l'últim
decimal**. Si no el reprodueix, el transport està trencat i la resta de la taula no val
res. És la verificació C0 i és la primera que corre.

── LES DUES COMPARACIONS, I PER QUÈ EN CALEN DUES ───────────────────────────────
  · **absoluta** — `valor_camp(talla) − GradedSpec(talla)`. Inclou el desacord que ja hi ha
    a la BASE entre el que el patró MESURA i el que la fitxa DECLARA, que no és grading:
    és la distància entre el patró i la fitxa, i al 837 no és zero.
  · **de deltes** — `Δ_camp(talla) − Δ_fitxa(talla)`, amb Δ comptat des de la base. Aquí el
    desacord de base se'n va sol, i el que queda és NOMÉS grading. **És la xifra del
    Rosetta**: si la nostra GV i el camp de la Montse expliquen el mateix vestit, aquesta
    columna ha de ser zero.

── C2-BIS (esmena d'Agus, 27/08) ────────────────────────────────────────────────
Coll i tapeta sense graduar és VOLGUT: els seus POMs surten de regles FIXED. Els FIXED són,
doncs, el **cas positiu** del banc —han de donar delta 0,00— i no una excepció a tolerar.
I no són només els del coll i la tapeta: n'hi ha quatre al DELANTERO i dos a l'ESPALDA, que
són peces que SÍ graden. Aquests són la prova dura: la peça es mou i la mesura no s'ha de
moure. Per a F6, FIXED = restricció de delta zero DUR (classe pròpia al solver).
"""
from __future__ import annotations

import hashlib
import json
from bisect import bisect_right
import math
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))
sys.path.insert(0, str(REPO / 'ops'))

from rosetta.camp_montse import (                                    # noqa: E402
    BASE, CAMP_837, MESTRE_837, TALLES, Camp, alinea, fraccio_de_projeccio,
    fraccions, llegeix_camp, projecta_sobre_bucle, verifica, verifica_contra_mestre,
)

#: El model del banc i la seva versió de grading segellada. Escrits i no descoberts: un
#: banc que es busqui sol el model «més recent» canvia de banc sense avisar.
MODEL_BANC = 1383
PATTERN_FILE = 20
GRADING_VERSION = 201          # v9, aprovada 24/08, is_active

#: Per sobre d'això un Δ es destaca. És la tolerància que la fase va proposar (≤0,5 mm per
#: punt i talla) i que l'Agus encara ha de ratificar; viu aquí per poder-la moure en un lloc.
LLINDAR_MM = 0.5

#: Els tres portadors. El canònic és `projeccio` perquè és el determinista i el que
#: reprodueix la base exacta; els altres dos hi corren al costat per posar-hi la barra d'error.
PORTADORS = ('projeccio', 'vertex', 'fraccio')
PORTADOR_CANONIC = 'projeccio'

#: `PatternPOM.valor_mesurat_cm` es desa amb DOS decimals de cm. La reproducció a la base
#: no pot ser millor que mig decimal, i exigir-li més seria exigir-li que menteixi.
TOL_ARRODONIMENT_MM = 0.05

#: Per sobre d'això, l'àncora és massa lluny del contorn de tall perquè el transport
#: («la costura grada com el tall que té al costat») es pugui donar per bo sense mirar-s'ho.
#: El marge de la casa és ~8 mm; es dobla i s'hi posa un dit de marge.
CARRIER_SOSPITOS_MM = 18.0


# ─────────────────────────────────────────────────────────────────────────────
# Transport
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Carrier:
    """On s'agafa un punt al contorn de tall de la base, perquè el grading se l'endugui."""

    aresta: int
    t: float
    distancia_mm: float
    fraccio: float


def carrier_de(p, contorn_base, origen: int) -> Carrier:
    aresta, t, d = projecta_sobre_bucle(p, contorn_base)
    return Carrier(aresta=aresta, t=t, distancia_mm=d,
                   fraccio=fraccio_de_projeccio(contorn_base, origen, aresta, t))


def desplacament_a_fraccio(f: float, fr_ordenades, ordre, camp_desp) -> tuple[float, float]:
    """El desplaçament del contorn de tall a una FRACCIÓ del bucle.

    És el tercer portador i el més fidel a la naturalesa d'una offset: dos bucles paral·lels
    recorren la mateixa frontera, i el punt de la costura que correspon al punt del tall és
    **el que és a la mateixa fracció d'arc**, no el que té més a prop. En una corba les dues
    coses divergeixen, i divergeixen just on més importa (sisa, escot).
    """
    n = len(ordre)
    k = bisect_right(fr_ordenades, f) - 1
    if k < 0:
        k = n - 1
    i0, i1 = ordre[k % n], ordre[(k + 1) % n]
    f0 = fr_ordenades[k % n]
    f1 = fr_ordenades[(k + 1) % n] if (k + 1) < n else 1.0
    t = 0.0 if f1 <= f0 else (f - f0) / (f1 - f0)
    d0, d1 = camp_desp[i0], camp_desp[i1]
    return (d0[0] + t * (d1[0] - d0[0]), d0[1] + t * (d1[1] - d0[1]))


def fraccions_ordenades(contorn, origen: int):
    """(fraccions creixents, índexs de vèrtex en ordre de recorregut) — per a `bisect`."""
    n = len(contorn)
    ordre = [(origen + k) % n for k in range(n)]
    fr = fraccions(contorn, origen)
    return [fr[i] for i in ordre], ordre


def desplacament_a(carrier: Carrier, camp_desp) -> tuple[float, float]:
    """El desplaçament interpolat a la fracció del carrier.

    Lineal DINS de l'aresta i prou: la fracció d'arc dins d'una aresta recta ja és lineal
    en `t`, o sigui que interpolar per `t` i interpolar per fracció són la mateixa cosa.
    """
    n = len(camp_desp)
    d0 = camp_desp[carrier.aresta]
    d1 = camp_desp[(carrier.aresta + 1) % n]
    return (d0[0] + carrier.t * (d1[0] - d0[0]),
            d0[1] + carrier.t * (d1[1] - d0[1]))


def transporta_peca(mestre, contorn_base, origen: int, camp_desp, portador: str = 'projeccio'):
    """El `PieceData` del patró mestre, mogut a una talla del camp.

    Torna una peça sencera —les dues vores, els piquets— perquè el motor de mesura la pugui
    fer servir tal qual: el mètode `vora` resegueix la vora, i sense vora no hi ha res a
    resseguir.
    """
    fr_ord, ordre = fraccions_ordenades(contorn_base, origen)

    def per_projeccio(x, y):
        return desplacament_a(carrier_de((x, y), contorn_base, origen), camp_desp)

    def per_vertex(x, y):
        j = min(range(len(contorn_base)), key=lambda i: math.dist((x, y), contorn_base[i]))
        return camp_desp[j]

    vores = []
    for bi, b in enumerate(mestre.boundaries):
        if portador == 'fraccio':
            # 🚨 L'origen del bucle de la COSTURA no es busca amb l'argmin de Y: es pren el
            # punt de la costura més proper a l'origen del bucle de TALL. Les dues coses
            # coincideixen a quatre peces i a la TAPETA no: allà l'argmin de Y cau a l'altra
            # punta i la fracció s'esbiaixa 0,368 del perímetre (209 mm d'arc) en comptes de
            # 0,0099 (7,8 mm). Dues parametritzacions només es poden comparar si tenen
            # l'origen al MATEIX lloc material, i «Y mínima» no ho garanteix en un bucle que
            # no és el mateix bucle.
            propies = None
            if b.closed:
                pts = [(q.x, q.y) for q in b.points]
                ancora_cut = contorn_base[origen]
                oi = min(range(len(pts)), key=lambda i: math.dist(pts[i], ancora_cut))
                propies = fraccions(pts, oi)
            punts = tuple(
                replace(q, x=q.x + d[0], y=q.y + d[1])
                for q, d in (
                    (q, desplacament_a_fraccio(propies[k], fr_ord, ordre, camp_desp)
                        if propies is not None else per_projeccio(q.x, q.y))
                    for k, q in enumerate(b.points)
                )
            )
        else:
            mou = per_vertex if portador == 'vertex' else per_projeccio
            punts = tuple(
                replace(q, x=q.x + d[0], y=q.y + d[1])
                for q, d in ((q, mou(q.x, q.y)) for q in b.points)
            )
        vores.append(replace(b, points=punts))
    piquets = tuple(
        replace(nz, x=nz.x + d[0], y=nz.y + d[1])
        for nz, d in ((nz, per_projeccio(nz.x, nz.y)) for nz in mestre.notches)
    )
    return replace(mestre, boundaries=tuple(vores), notches=piquets)


# ─────────────────────────────────────────────────────────────────────────────
# Lectura de la BD (read-only: SELECT i prou)
# ─────────────────────────────────────────────────────────────────────────────

def llegeix_bd() -> dict:
    """Els POMs ancorats del 1383 i els specs de la GV segellada. Cap escriptura."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
    cwd = os.getcwd()
    os.chdir(REPO / 'backend')
    try:
        import django
        django.setup()
        from django_tenants.utils import schema_context
        with schema_context('fhort'):
            from fhort.fitting.models import GradedSpec, GradingVersion
            from fhort.patterns.models import PatternFile, PatternPoint

            gv = GradingVersion.objects.get(pk=GRADING_VERSION)
            pf = PatternFile.objects.get(pk=PATTERN_FILE)
            if pf.model_id != MODEL_BANC:
                raise AssertionError(
                    f'PatternFile#{PATTERN_FILE} és del model {pf.model_id}, no del '
                    f'{MODEL_BANC}. El banc s\'ha mogut sota els peus.'
                )

            poms, punts = [], {}
            for pc in pf.pieces.all().order_by('id'):
                for pt in PatternPoint.objects.filter(piece=pc):
                    punts[pt.id] = (pc.nom_block, pt.boundary_index, pt.ordre, pt.mena,
                                    pt.x, pt.y)
                for pom in pc.poms.all().order_by('id'):
                    poms.append({
                        'id': pom.id,
                        'peca': pc.nom_block,
                        'codi': str(pom.pom_master).split(' · ')[0].strip(),
                        'nom': str(pom.pom_master),
                        'metode': pom.metode,
                        'definicio': pom.definicio_mesura,
                        'valor_mesurat_cm': pom.valor_mesurat_cm,
                    })

            specs: dict[str, dict[str, dict]] = {}
            for sp in GradedSpec.objects.filter(grading_version=gv, is_active=True):
                codi = str(sp.pom).split(' · ')[0].strip()
                specs.setdefault(codi, {})[sp.size_label] = {
                    'valor_cm': sp.graded_value_cm,
                    'tipus': sp.grading_type_applied,
                    'increment_cm': sp.increment_applied_cm,
                }
            noms_spec = {str(sp.pom).split(' · ')[0].strip(): str(sp.pom)
                         for sp in GradedSpec.objects.filter(grading_version=gv)}
            return {
                'gv': {'id': gv.id, 'version_number': gv.version_number, 'nom': gv.nom,
                       'aprovada': gv.aprovada, 'is_active': gv.is_active,
                       'data_aprovacio': str(gv.data_aprovacio)},
                'pattern_file': {'id': pf.id, 'versio': pf.versio, 'nom': pf.nom_fitxer,
                                 'is_current': pf.is_current},
                'poms': poms, 'punts': punts, 'specs': specs, 'noms_spec': noms_spec,
            }
    finally:
        os.chdir(cwd)


# ─────────────────────────────────────────────────────────────────────────────
# El Rosetta
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FilaPOM:
    codi: str
    nom: str
    peca: str
    metode: str
    tipus_grading: str
    #: el que el motor va llegir del patró mestre (2 decimals de cm, com es desa)
    valor_patro_cm: float | None
    #: portador → talla → cm, mesurat damunt del camp
    valor_camp: dict[str, dict[str, float]]
    valor_fitxa: dict[str, float]
    #: distància màxima de les seves àncores al contorn de tall de la base
    carrier_max_mm: float
    motiu_exclusio: str = ''

    @property
    def mesurable(self) -> bool:
        return not self.motiu_exclusio

    def valor(self, talla: str, portador: str = PORTADOR_CANONIC) -> float:
        return self.valor_camp[portador][talla]

    def delta_absolut_mm(self, talla: str, portador: str = PORTADOR_CANONIC) -> float:
        return (self.valor(talla, portador) - self.valor_fitxa[talla]) * 10.0

    def delta_de_deltes_mm(self, talla: str, portador: str = PORTADOR_CANONIC) -> float:
        """La xifra del Rosetta: quant grada el camp menys quant diu la fitxa que grada."""
        v = self.valor_camp[portador]
        d_camp = v[talla] - v[BASE]
        d_fitxa = self.valor_fitxa[talla] - self.valor_fitxa[BASE]
        return (d_camp - d_fitxa) * 10.0

    def incertesa_mm(self) -> float:
        """Dispersió del Δ entre els tres portadors. És la barra d'error de la fila."""
        return max(
            max(self.delta_de_deltes_mm(t, p) for p in PORTADORS)
            - min(self.delta_de_deltes_mm(t, p) for p in PORTADORS)
            for t in TALLES
        )

    def desviacio_mm(self) -> float:
        return max(abs(self.delta_de_deltes_mm(t)) for t in TALLES)

    def veredicte(self) -> str:
        """Desviació i incertesa es comparen ENTRE ELLES, no cadascuna amb el llindar.

        Una barra d'error de 0,8 mm damunt d'una desviació de 75 mm no fa dubtosa la
        desviació: la deixa igual de certa. I una desviació de 0,01 mm amb una barra de
        0,93 mm no és paritat: és que no se sap. Les tres sortides, doncs:

          · **DESVIAT** — |Δ| − incertesa > llindar: el desacord sobreviu a l'error.
          · **PARITAT** — |Δ| + incertesa ≤ llindar: l'acord sobreviu a l'error.
          · **NO RESOLUBLE** — la barra travessa el llindar. Sobre AQUEST banc no es pot
            dir, i el que falta per poder-ho dir és la capa 14 graduada.
        """
        if not self.mesurable:
            return 'NO MESURABLE'
        d, u = self.desviacio_mm(), self.incertesa_mm()
        if d - u > LLINDAR_MM:
            return 'DESVIAT'
        if d + u <= LLINDAR_MM:
            return 'PARITAT'
        return 'NO RESOLUBLE'


def executa(camp: Camp | None = None) -> dict:
    from fhort.patterns.engine.aama_reader import AAMAReader
    from fhort.patterns.engine.measure import MeasureError, resoldre

    camp = camp or llegeix_camp()
    bd = llegeix_bd()
    mestre_bytes = MESTRE_837.read_bytes()
    mestre = {p.nom_block: p for p in AAMAReader().read(mestre_bytes).pieces}

    # ── el transport, peça × talla × portador ────────────────────────────────
    transportades: dict[str, dict[str, dict[str, object]]] = {}
    for nom, pc in camp.peces.items():
        base = pc.contorn[BASE]
        transportades[nom] = {
            port: {t: transporta_peca(mestre[nom], base, pc.origen_bucle,
                                      pc.desplacaments(t), port)
                   for t in TALLES}
            for port in PORTADORS
        }

    # ── els PatternPoint han de casar amb el patró mestre, o res no val ──────
    incoherents = [
        pid for pid, (peca, bi, ordre, mena, x, y) in bd['punts'].items()
        if (lambda q: q is None or math.dist((q.x, q.y), (x, y)) > 1e-6)(
            _punt_del_mestre(mestre[peca], bi, ordre, mena))
    ]

    files = [_fila(pom, bd, camp, transportades, resoldre, MeasureError)
             for pom in bd['poms']]

    ancorats = {f.codi for f in files}
    for codi, per_talla in sorted(bd['specs'].items()):
        if codi in ancorats:
            continue
        files.append(FilaPOM(
            codi=codi, nom=bd['noms_spec'].get(codi, codi), peca='—', metode='—',
            tipus_grading=per_talla[BASE]['tipus'], valor_patro_cm=None,
            valor_camp={}, valor_fitxa={t: per_talla[t]['valor_cm'] for t in TALLES},
            carrier_max_mm=float('nan'),
            motiu_exclusio='sense recepta PatternPOM al 1383 (POM de fitxa, no ancorat)',
        ))

    return {
        'camp': camp, 'bd': bd,
        'files': sorted(files, key=lambda f: (f.peca, f.codi)),
        'mestre_md5': hashlib.md5(mestre_bytes).hexdigest(),
        'punts_incoherents': incoherents,
    }


def _fila(pom, bd, camp, transportades, resoldre, MeasureError) -> FilaPOM:
    codi, peca = pom['codi'], pom['peca']
    spec = bd['specs'].get(codi)
    tipus = spec[BASE]['tipus'] if spec else '—'
    fitxa = {t: spec[t]['valor_cm'] for t in TALLES} if spec else {}

    def exclos(motiu, carrier=float('nan')):
        return FilaPOM(codi, pom['nom'], peca, pom['metode'], tipus,
                       pom['valor_mesurat_cm'], {}, fitxa, carrier, motiu_exclusio=motiu)

    if spec is None:
        return exclos(f'sense GradedSpec actiu a la GV{GRADING_VERSION}')

    pc = camp.peces[peca]
    ancores = [v for k, v in pom['definicio'].items()
               if k in ('a', 'b', 'p', 'ref_a', 'ref_b', 'landmark') and isinstance(v, int)]
    if not ancores:
        return exclos(f'recepta sense àncores: {pom["definicio"]}')

    carrier_max = 0.0
    for pid in ancores:
        dades = bd['punts'].get(pid)
        if dades is None:
            return exclos(f'àncora #{pid} no existeix a la geometria del patró')
        carrier_max = max(
            carrier_max,
            carrier_de((dades[4], dades[5]), pc.contorn[BASE], pc.origen_bucle).distancia_mm,
        )

    valors: dict[str, dict[str, float]] = {}
    for port in PORTADORS:
        valors[port] = {}
        for t in TALLES:
            peca_t = transportades[peca][port][t]
            per_id = {}
            for pid in ancores:
                _, bi, ordre, mena, _, _ = bd['punts'][pid]
                q = _punt_del_mestre(peca_t, bi, ordre, mena)
                if q is None:
                    return exclos(f'àncora #{pid} sense homòloga transportada', carrier_max)
                per_id[pid] = (q.x, q.y)
            try:
                valors[port][t] = resoldre(peca_t, pom['definicio'], per_id,
                                           pom['metode']).valor_cm
            except MeasureError as exc:
                return exclos(f'la recepta no resol: {exc}', carrier_max)

    return FilaPOM(codi, pom['nom'], peca, pom['metode'], tipus, pom['valor_mesurat_cm'],
                   valors, fitxa, carrier_max)


def _punt_del_mestre(peca, boundary_index, ordre, mena):
    if mena == 'notch':
        return peca.notches[ordre] if ordre < len(peca.notches) else None
    if boundary_index is None or boundary_index >= len(peca.boundaries):
        return None
    pts = peca.boundaries[boundary_index].points
    return pts[ordre] if ordre < len(pts) else None


# ─────────────────────────────────────────────────────────────────────────────
# D · el dataset de paritat
# ─────────────────────────────────────────────────────────────────────────────

def dataset(res: dict) -> dict:
    """`parity_837.json` — el que el solver F6 carregarà com a banc.

    Porta el camp ALINEAT (grading sense la posició del full), els desplaçaments per vèrtex
    respecte de la base, l'origen de bucle de CONVENCIÓ-1 i les fraccions que en surten, i
    la classe de restricció de cada POM. Les coordenades van a 4 decimals: el DXF en porta 3.
    """
    camp: Camp = res['camp']
    peces = {}
    for nom, pc in camp.peces.items():
        al = alinea(pc)
        base = pc.contorn[BASE]
        talles = {}
        for t in TALLES:
            tx, ty = al.translacio[t]
            desp = pc.desplacaments(t)
            talles[t] = {
                'contorn_alineat': [[round(x - tx, 4), round(y - ty, 4)]
                                    for x, y in pc.contorn[t]],
                'desplacament_vs_base': [[round(dx - tx, 4), round(dy - ty, 4)]
                                         for dx, dy in desp],
                'piquets': [[round(x, 4), round(y, 4)] for x, y in pc.piquets[t]],
                'fil': [round(v, 4) for v in pc.fil[t]],
                'residu_max_mm': round(al.residu_max[t], 4),
            }
        peces[nom] = {
            'n_vertexs': pc.n_vertexs,
            'origen_bucle': pc.origen_bucle,
            'tipus_vertex': list(pc.tipus),
            'fraccio_vertex': [round(f, 8) for f in fraccions(base, pc.origen_bucle)],
            'alineacio': {'metode': al.metode, 'ancora': al.ancora,
                          'translacio': {t: [round(v, 4) for v in al.translacio[t]]
                                         for t in TALLES},
                          'candidats_mm': {k: round(v, 4) for k, v in al.candidats.items()}},
            'talles': talles,
        }

    poms = []
    for f in res['files']:
        poms.append({
            'codi': f.codi, 'nom': f.nom, 'peca': f.peca, 'metode': f.metode,
            'tipus_grading': f.tipus_grading,
            'classe_restriccio': ('delta_zero_dur' if f.tipus_grading == 'FIXED'
                                  else 'delta_lliure' if f.tipus_grading == 'LINEAR'
                                  else f.tipus_grading.lower()),
            'veredicte': f.veredicte(),
            'motiu_exclusio': f.motiu_exclusio,
            'carrier_max_mm': None if math.isnan(f.carrier_max_mm) else round(f.carrier_max_mm, 4),
            'valor_patro_cm': f.valor_patro_cm,
            'valor_fitxa_cm': f.valor_fitxa,
            'valor_camp_cm': ({p: {t: round(v, 6) for t, v in f.valor_camp[p].items()}
                               for p in PORTADORS} if f.mesurable else {}),
            'delta_de_deltes_mm': ({t: round(f.delta_de_deltes_mm(t), 4) for t in TALLES}
                                   if f.mesurable else {}),
            'delta_absolut_mm': ({t: round(f.delta_absolut_mm(t), 4) for t in TALLES}
                                 if f.mesurable else {}),
            'incertesa_portador_mm': round(f.incertesa_mm(), 4) if f.mesurable else None,
        })

    return {
        'meta': {
            'nom': 'parity_837',
            'proposit': 'Banc de paritat del solver F6: el grading real de la Montse '
                        'aparellat vèrtex a vèrtex amb el patró del model 1383.',
            'font_camp': camp.fitxer.name,
            'md5_camp': camp.md5,
            'font_mestre': MESTRE_837.name,
            'md5_mestre': res['mestre_md5'],
            'textos_document': list(camp.textos_document),
            'unitats': camp.unitats + ' · totes les coordenades i deltes del fitxer, en mm',
            'talles': list(TALLES),
            'talla_base': BASE,
            'model': MODEL_BANC,
            'pattern_file': res['bd']['pattern_file'],
            'grading_version': res['bd']['gv'],
            'portador_canonic': PORTADOR_CANONIC,
            'portadors': list(PORTADORS),
            'convencio_1': ("origen del bucle = vèrtex de Y mínima del contorn de tall a la "
                            "talla base; les altres talles l'hereten per identitat d'índex. "
                            "Únic a les cinc peces (verificació A4)."),
            'correspondencia': ("vèrtex a vèrtex per identitat d'índex; recompte i "
                                "classificació gir/corba invariants a les cinc talles (A1, A2); "
                                "la base del camp és el MATEIX contorn que el patró mestre "
                                "del 1383, desviació 0,000000000 mm (A5)."),
            'llindar_mm': LLINDAR_MM,
            'avis_capa_14': ("El camp NO porta línia de cosit. Les receptes del 1383 hi "
                             "ancoren 19 de 20 àncores, i s'hi transporten. Els POMs amb "
                             "veredicte NO RESOLUBLE són els que depenen de quin portador "
                             "es triï més que del vestit."),
        },
        'peces': peces,
        'poms': poms,
    }


def escriu_dataset(res: dict, desti: Path | None = None) -> Path:
    desti = desti or (Path(__file__).resolve().parent / 'parity_837.json')
    desti.write_text(json.dumps(dataset(res), ensure_ascii=False, indent=1) + '\n')
    return desti


# ─────────────────────────────────────────────────────────────────────────────
# Sortida a consola
# ─────────────────────────────────────────────────────────────────────────────

def _capcalera(titol: str) -> str:
    return f'\n── {titol} ' + '─' * max(4, 76 - len(titol))


def informe(res: dict) -> str:
    out: list[str] = []
    camp: Camp = res['camp']
    files: list[FilaPOM] = res['files']
    mesurables = [f for f in files if f.mesurable]

    out.append(_capcalera("A · VERIFICACIONS D'INGESTA"))
    for v in verifica(camp) + verifica_contra_mestre(camp):
        out.append(f'  {"OK  " if v.ok else "FAIL"} {v.nom} — {v.detall}')

    out.append(_capcalera('B · ALINEACIÓ'))
    for nom, pc in camp.peces.items():
        al = alinea(pc)
        cand = ' · '.join(f'{k}={v:.2f}' for k, v in al.candidats.items())
        out.append(f'  {nom:16s} mètode={al.metode:18s} àncora={al.ancora} '
                   f'residu_max(XL)={al.residu_max["XL"]:6.2f} mm  [{cand}]')

    out.append(_capcalera('C0 · EL TRANSPORT REPRODUEIX EL PATRÓ A LA BASE'))
    pitjor = max((abs(f.valor(BASE, p) - f.valor_patro_cm) * 10.0
                  for f in mesurables if f.valor_patro_cm is not None
                  for p in PORTADORS), default=0.0)
    out.append(f'  {"OK  " if pitjor <= TOL_ARRODONIMENT_MM else "FAIL"} desviació màxima '
               f'base↔patró: {pitjor:.4f} mm sobre {len(mesurables)} POMs × '
               f'{len(PORTADORS)} portadors (tolerància {TOL_ARRODONIMENT_MM} mm = mig '
               f'decimal de com es desa `valor_mesurat_cm`)')
    out.append(f'  {"OK  " if not res["punts_incoherents"] else "FAIL"} '
               f'{len(res["bd"]["punts"])} PatternPoint contra el patró mestre: '
               f'{len(res["punts_incoherents"])} incoherents')

    out.append(_capcalera(f'C · PARITAT · Δ DE DELTES (mm) · portador «{PORTADOR_CANONIC}»'))
    out.append(f'  {"POM":5s} {"peça":10s} {"tipus":6s} {"mèt.":9s} '
               + ' '.join(f'{t:>7s}' for t in TALLES)
               + f' {"|Δ|max":>7s} {"incert.":>8s}  veredicte')
    for f in files:
        if not f.mesurable:
            continue
        ds = [f.delta_de_deltes_mm(t) for t in TALLES]
        out.append(f'  {f.codi:5s} {f.peca.replace("837.",""):10s} {f.tipus_grading:6s} '
                   f'{f.metode:9s} ' + ' '.join(f'{d:+7.2f}' for d in ds)
                   + f' {f.desviacio_mm():7.2f} {f.incertesa_mm():8.2f}  {f.veredicte()}')

    out.append(_capcalera('C · LES TRES VIES, allà on no diuen el mateix'))
    out.append('  (dispersió > llindar: el Δ és una propietat de la tria, no del vestit)')
    for f in sorted(mesurables, key=lambda f: -f.incertesa_mm()):
        if f.incertesa_mm() <= LLINDAR_MM:
            continue
        out.append(f'  {f.codi:5s} {f.peca.replace("837.",""):10s} incertesa='
                   f'{f.incertesa_mm():5.2f} mm')
        for p in PORTADORS:
            out.append(f'      {p:10s} ' + ' '.join(
                f'{f.delta_de_deltes_mm(t, p):+7.2f}' for t in TALLES))

    out.append(_capcalera('C · EL QUE LA FITXA DEMANA vs EL QUE EL CAMP GRADA (cm)'))
    out.append(f'  {"POM":5s} {"peça":10s} {"font":6s} '
               + ' '.join(f'{t:>7s}' for t in TALLES))
    for f in files:
        if not f.mesurable:
            continue
        out.append(f'  {f.codi:5s} {f.peca.replace("837.",""):10s} {"fitxa":6s} '
                   + ' '.join(f'{f.valor_fitxa[t] - f.valor_fitxa[BASE]:+7.2f}'
                              for t in TALLES))
        out.append(f'  {"":5s} {"":10s} {"camp":6s} '
                   + ' '.join(f'{f.valor(t) - f.valor(BASE):+7.2f}' for t in TALLES))

    out.append(_capcalera('C · PARITAT · Δ ABSOLUT camp − fitxa (mm)'))
    out.append(f'  {"POM":5s} {"peça":10s} {"patró":>8s} {"fitxa@S":>8s} '
               + ' '.join(f'{t:>7s}' for t in TALLES))
    for f in files:
        if not f.mesurable:
            continue
        out.append(f'  {f.codi:5s} {f.peca.replace("837.",""):10s} '
                   f'{(f.valor_patro_cm if f.valor_patro_cm is not None else 0):8.2f} '
                   f'{f.valor_fitxa[BASE]:8.2f} '
                   + ' '.join(f'{f.delta_absolut_mm(t):+7.2f}' for t in TALLES))

    out.append(_capcalera('C · RESUM PER PEÇA (Δ de deltes, talles no-base)'))
    per_peca: dict[str, list[float]] = {}
    for f in mesurables:
        per_peca.setdefault(f.peca, []).extend(
            abs(f.delta_de_deltes_mm(t)) for t in TALLES if t != BASE)
    for peca, ds in sorted(per_peca.items()):
        out.append(f'  {peca:16s} n={len(ds):3d}  mitjana={sum(ds)/len(ds):7.2f} mm  '
                   f'màx={max(ds):7.2f} mm  ≤{LLINDAR_MM} mm: '
                   f'{sum(1 for d in ds if d <= LLINDAR_MM)}/{len(ds)}')

    out.append(_capcalera('C2-BIS · CAS POSITIU · els FIXED han de donar delta 0,00'))
    for f in files:
        if f.mesurable and f.tipus_grading == 'FIXED':
            m = f.desviacio_mm()
            out.append(f'  {"OK  " if m <= LLINDAR_MM else "🚩  "} {f.codi:5s} '
                       f'{f.peca.replace("837.",""):10s} |Δ|max={m:6.2f} mm  '
                       f'({f.veredicte()})')

    out.append(_capcalera('C3 · NO MESURABLES SOBRE EL BANC'))
    exclosos = [f for f in files if not f.mesurable]
    for f in exclosos or []:
        out.append(f'  {f.codi:5s} {f.peca:14s} — {f.motiu_exclusio}')
    if not exclosos:
        out.append('  cap')

    out.append(_capcalera('VEREDICTE'))
    per_v: dict[str, list[str]] = {}
    for f in files:
        per_v.setdefault(f.veredicte(), []).append(f.codi)
    for v in ('PARITAT', 'DESVIAT', 'NO RESOLUBLE', 'NO MESURABLE'):
        if v in per_v:
            out.append(f'  {v:13s} {len(per_v[v]):2d}/{len(files)}  '
                       f'{" ".join(sorted(per_v[v]))}')
    return '\n'.join(out)


if __name__ == '__main__':
    resultat = executa()
    print(informe(resultat))
    desti = escriu_dataset(resultat)
    print(f'\nDataset escrit: {desti} ({desti.stat().st_size / 1024:.0f} KB)')
