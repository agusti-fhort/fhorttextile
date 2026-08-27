"""C + D · El Rosetta: les receptes del 1383 mesurades damunt del camp de la Montse.

**La pregunta.** La fitxa del 1383 (GradedSpec de la GV201 v9, segellada) diu quant ha de
fer cada POM a cada talla. El camp de la Montse diu on és cada punt del patró a cada talla.
Són dues descripcions del MATEIX vestit fetes per camins que no s'han tocat mai. El Rosetta
és posar-les una al costat de l'altra i mirar quant es separen, en mil·límetres.

── ESMENA A0 (27/08) · EL FORAT QUE MANAVA SOBRE EL MÈTODE S'HA TANCAT ─────────
La primera versió d'aquest mòdul existia gairebé sencera per a un problema que ja no hi és.
El banc del 26/08 no portava capa 14 i **19 de les 20 àncores de POM del 1383 hi viuen**, de
manera que cada mesura s'havia de TRANSPORTAR des del contorn de tall — per tres portadors
alhora (projecció, vèrtex més proper, fracció homòloga), amb la dispersió entre ells com a
barra d'error. Sis POMs quedaven **no resolubles**: la seva xifra depenia més de quin
portador es triés que del vestit.

El banc nou porta la capa 14, i el seu cosit a la talla base és **idèntic al del patró
mestre del 1383, 0,000000000 mm a les cinc peces** (verificació A5). Per tant:

  🔑 **Cada àncora té homòloga NATIVA a cada talla, pel seu propi índex.** No hi ha
  transport, no hi ha portador, no hi ha barra d'error de portador. La `PatternPoint` diu
  `(boundary_index, ordre)`; `boundary_index` 0 és el tall i 1 el cosit; l'homòloga a la
  talla T és el vèrtex del MATEIX índex d'aquell bucle. Res més.

Tot el bastiment de portadors s'ha RETIRAT en comptes de deixar-lo desactivat. El que
mesurava —quant costava no tenir la capa 14— és història i viu a
`REPORT_ROSETTA_837_2026-08-27.md`; mantenir-lo viu seria mantenir dos camins per a la
mateixa pregunta i que el dia de demà algú n'agafés el dolent.

── LES DUES COMPARACIONS, I PER QUÈ EN CALEN DUES ───────────────────────────────
  · **absoluta** — `valor_camp(talla) − GradedSpec(talla)`. Inclou el desacord que ja hi ha
    a la BASE entre el que el patró MESURA i el que la fitxa DECLARA, que no és grading: és
    la distància entre el patró i la fitxa, i al 837 no és zero.
  · **de deltes** — `Δ_camp(talla) − Δ_fitxa(talla)`, amb Δ comptat des de la base. Aquí el
    desacord de base se'n va sol i el que queda és NOMÉS grading. **És la xifra del
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
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))
sys.path.insert(0, str(REPO / 'ops'))

from rosetta.camp_montse import (                                    # noqa: E402
    BASE, CAPA_COSIT, CAPA_TALL, CAPES, MESTRE_837, TALLES, Camp, alinea, fraccions,
    llegeix_camp, verifica, verifica_contra_mestre, verifica_superseeix,
)

#: El model del banc i la seva versió de grading segellada. Escrits i no descoberts: un
#: banc que es busqui sol el model «més recent» canvia de banc sense avisar.
MODEL_BANC = 1383
PATTERN_FILE = 20

#: La GV del banc. Per defecte la **201 (v9)**, que és la que està APROVADA; el que la fa
#: bona no és que sigui la darrera sinó que està segellada.
#:
#: 🚨 F6-CODA (27/08): l'Agus va corregir la fitxa i això va crear la **205 (v10)**, que és
#: `is_active=True` però `aprovada=False`. Una GV sense segellar no pot ser la referència
#: d'un banc de paritat —el segell és el gest que diu «aquests números són els bons»— però
#: tampoc es pot mesurar el que canviaria sense poder-la llegir. Sortida: la versió deixa de
#: ser una constant i passa a ser un **paràmetre de la correguda**, amb el mateix criteri que
#: `FTT_TEST_DB` a `settings_test`. El defecte segueix sent la segellada; llegir-ne una altra
#: és un gest explícit de qui la corre, i l'informe en diu el número i si està aprovada.
#:
#:     FTT_ROSETTA_GV=205 python3 ops/rosetta/rosetta_837.py     # previsualització
GRADING_VERSION = int(os.environ.get('FTT_ROSETTA_GV', '201'))

#: Per sobre d'això un Δ es destaca. És la tolerància que la fase va proposar (≤0,5 mm per
#: punt i talla) i que l'Agus encara ha de ratificar; viu aquí per poder-la moure en un lloc.
LLINDAR_MM = 0.5

#: `PatternPOM.valor_mesurat_cm` es desa amb DOS decimals de cm. La reproducció a la base
#: no pot ser millor que mig decimal, i exigir-li més seria exigir-li que menteixi.
TOL_ARRODONIMENT_MM = 0.05

#: `PatternPoint.boundary_index` → capa del camp. L'ordre de vores del patró mestre és
#: [0]=tall (capa 1), [1]=cosit (capa 14), i el camp el reprodueix exactament (A5).
CAPA_PER_BOUNDARY = {0: CAPA_TALL, 1: CAPA_COSIT}


# ─────────────────────────────────────────────────────────────────────────────
# La geometria d'una talla, tal com el motor de mesura la vol
# ─────────────────────────────────────────────────────────────────────────────

def peca_a_la_talla(pc, talla: str):
    """`PieceData` d'una peça del camp a una talla: els dos bucles i els piquets.

    Es construeix per poder cridar `engine/measure.resoldre` **tal qual**, que és el que fa
    que el valor mesurat aquí i el valor que el Taller ensenya siguin literalment la mateixa
    funció. El mètode `vora` necessita la vora sencera per resseguir-la: per això hi van els
    dos bucles i no només els punts que la recepta cita.
    """
    from fhort.patterns.engine.geometry import (BoundaryData, LayerRole, PieceData,
                                                PointData, PointKind)
    rols = {CAPA_TALL: LayerRole.CUT, CAPA_COSIT: LayerRole.SEW}
    vores = []
    for capa in CAPES:
        if capa not in pc.bucles:
            continue
        b = pc.bucle(capa)
        punts = tuple(
            PointData(x=x, y=y, kind=PointKind(k))
            for (x, y), k in zip(b.contorn[talla], b.tipus)
        )
        vores.append(BoundaryData(role=rols[capa], layer=capa, points=punts, closed=True))
    piquets = tuple(PointData(x=x, y=y, kind=PointKind.UNCLASSIFIED)
                    for x, y in pc.piquets[talla])
    return PieceData(nom_block=pc.nom, boundaries=tuple(vores), notches=piquets)


def posicio_ancora(pc, boundary_index, ordre, mena, talla) -> tuple[float, float]:
    """On és una àncora de `PatternPoint` a una talla del camp. Per ÍNDEX, sense transport.

    🔑 Això és tota la simplificació de l'esmena A0 en quatre línies. Abans calia projectar
    l'àncora sobre el contorn de tall, interpolar-hi el desplaçament i acceptar una barra
    d'error; ara el bucle on viu l'àncora existeix a totes cinc talles amb la mateixa
    numeració, i la resposta és el vèrtex del mateix índex.
    """
    if mena == 'notch':
        return pc.piquets[talla][ordre]
    capa = CAPA_PER_BOUNDARY.get(boundary_index)
    if capa is None or capa not in pc.bucles:
        raise KeyError(f'boundary_index {boundary_index} no té capa al camp')
    return pc.bucle(capa).contorn[talla][ordre]


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
    valor_camp: dict[str, float]            # talla → cm, mesurat damunt del camp
    valor_fitxa: dict[str, float]           # talla → cm, GradedSpec
    #: on viu cada àncora: 'cosit', 'tall' o 'mixt'. Ja no hi ha portador, però SÍ que
    #: importa saber-ho: un POM que travessa els dos bucles mesura la sagnadura, no la peça.
    bucles: str = ''
    motiu_exclusio: str = ''

    @property
    def mesurable(self) -> bool:
        return not self.motiu_exclusio

    def delta_absolut_mm(self, talla: str) -> float:
        return (self.valor_camp[talla] - self.valor_fitxa[talla]) * 10.0

    def delta_de_deltes_mm(self, talla: str) -> float:
        """La xifra del Rosetta: quant grada el camp menys quant diu la fitxa que grada."""
        d_camp = self.valor_camp[talla] - self.valor_camp[BASE]
        d_fitxa = self.valor_fitxa[talla] - self.valor_fitxa[BASE]
        return (d_camp - d_fitxa) * 10.0

    def desviacio_mm(self) -> float:
        return max(abs(self.delta_de_deltes_mm(t)) for t in TALLES)

    def veredicte(self) -> str:
        """Tres sortides, i ja no n'hi ha cap per «no se sap».

        A F6-PRE existia NO RESOLUBLE, que volia dir que la barra d'error del portador
        travessava la tolerància. El banc amb capa 14 la retira: cada mesura és exacta sobre
        la geometria que la Montse va dibuixar, i el que en surt és PARITAT o DESVIAT.
        """
        if not self.mesurable:
            return 'NO MESURABLE'
        return 'PARITAT' if self.desviacio_mm() <= LLINDAR_MM else 'DESVIAT'


def executa(camp: Camp | None = None) -> dict:
    from fhort.patterns.engine.measure import MeasureError, resoldre

    camp = camp or llegeix_camp()
    bd = llegeix_bd()
    mestre_bytes = MESTRE_837.read_bytes()

    geometria = {nom: {t: peca_a_la_talla(pc, t) for t in TALLES}
                 for nom, pc in camp.peces.items()}

    # Les àncores del patró han de casar amb el camp, o res del que segueix no val.
    incoherents = []
    for pid, (peca, bi, ordre, mena, x, y) in bd['punts'].items():
        try:
            q = posicio_ancora(camp.peces[peca], bi, ordre, mena, BASE)
        except (KeyError, IndexError):
            incoherents.append(pid)
            continue
        if math.dist(q, (x, y)) > 1e-9:
            incoherents.append(pid)

    files = [_fila(pom, bd, camp, geometria, resoldre, MeasureError) for pom in bd['poms']]

    ancorats = {f.codi for f in files}
    for codi, per_talla in sorted(bd['specs'].items()):
        if codi in ancorats:
            continue
        files.append(FilaPOM(
            codi=codi, nom=bd['noms_spec'].get(codi, codi), peca='—', metode='—',
            tipus_grading=per_talla[BASE]['tipus'], valor_patro_cm=None,
            valor_camp={}, valor_fitxa={t: per_talla[t]['valor_cm'] for t in TALLES},
            motiu_exclusio='sense recepta PatternPOM al 1383 (POM de fitxa, no ancorat)',
        ))

    return {
        'camp': camp, 'bd': bd,
        'files': sorted(files, key=lambda f: (f.peca, f.codi)),
        'mestre_md5': hashlib.md5(mestre_bytes).hexdigest(),
        'punts_incoherents': incoherents,
    }


def _fila(pom, bd, camp, geometria, resoldre, MeasureError) -> FilaPOM:
    codi, peca = pom['codi'], pom['peca']
    spec = bd['specs'].get(codi)
    tipus = spec[BASE]['tipus'] if spec else '—'
    fitxa = {t: spec[t]['valor_cm'] for t in TALLES} if spec else {}

    def exclos(motiu, bucles=''):
        return FilaPOM(codi, pom['nom'], peca, pom['metode'], tipus,
                       pom['valor_mesurat_cm'], {}, fitxa, bucles, motiu)

    if spec is None:
        return exclos(f'sense GradedSpec actiu a la GV{GRADING_VERSION}')

    pc = camp.peces[peca]
    ancores = [v for k, v in pom['definicio'].items()
               if k in ('a', 'b', 'p', 'ref_a', 'ref_b', 'landmark') and isinstance(v, int)]
    if not ancores:
        return exclos(f'recepta sense àncores: {pom["definicio"]}')

    capes = set()
    for pid in ancores:
        dades = bd['punts'].get(pid)
        if dades is None:
            return exclos(f'àncora #{pid} no existeix a la geometria del patró')
        capes.add(CAPA_PER_BOUNDARY.get(dades[1]))
    bucles = ('cosit' if capes == {CAPA_COSIT} else
              'tall' if capes == {CAPA_TALL} else 'mixt')

    valors = {}
    for t in TALLES:
        per_id = {}
        for pid in ancores:
            _, bi, ordre, mena, _, _ = bd['punts'][pid]
            try:
                per_id[pid] = posicio_ancora(pc, bi, ordre, mena, t)
            except (KeyError, IndexError):
                return exclos(f'àncora #{pid} sense homòloga al camp', bucles)
        try:
            valors[t] = resoldre(geometria[peca][t], pom['definicio'], per_id,
                                 pom['metode']).valor_cm
        except MeasureError as exc:
            return exclos(f'la recepta no resol: {exc}', bucles)

    return FilaPOM(codi, pom['nom'], peca, pom['metode'], tipus, pom['valor_mesurat_cm'],
                   valors, fitxa, bucles)


# ─────────────────────────────────────────────────────────────────────────────
# D · el dataset de paritat
# ─────────────────────────────────────────────────────────────────────────────

def dataset(res: dict) -> dict:
    """`parity_837.json` — el que el solver F6 carregarà com a banc.

    Porta els DOS bucles per peça × talla (esmena A0), cadascun alineat, amb els
    desplaçaments per vèrtex respecte de la base, el seu origen de CONVENCIÓ-1 i les
    fraccions que en surten. Coordenades a 4 decimals: el DXF en porta 3.
    """
    camp: Camp = res['camp']
    peces = {}
    for nom, pc in camp.peces.items():
        bucles = {}
        for capa in camp.capes:
            b = pc.bucle(capa)
            al = alinea(b)
            talles = {}
            for t in TALLES:
                tx, ty = al.translacio[t]
                desp = b.desplacaments(t)
                talles[t] = {
                    'contorn_alineat': [[round(x - tx, 4), round(y - ty, 4)]
                                        for x, y in b.contorn[t]],
                    'desplacament_vs_base': [[round(dx - tx, 4), round(dy - ty, 4)]
                                             for dx, dy in desp],
                    'residu_max_mm': round(al.residu_max[t], 4),
                }
            bucles[capa] = {
                'capa': capa,
                'rol': 'tall' if capa == CAPA_TALL else 'cosit',
                'n_vertexs': b.n_vertexs,
                'origen_bucle': b.origen_bucle,
                'tipus_vertex': list(b.tipus),
                'fraccio_vertex': [round(f, 8) for f in fraccions(b.contorn[BASE],
                                                                  b.origen_bucle)],
                'alineacio': {
                    'metode': al.metode, 'ancora': al.ancora,
                    'translacio': {t: [round(v, 4) for v in al.translacio[t]]
                                   for t in TALLES},
                    'candidats_mm': {k: round(v, 4) for k, v in al.candidats.items()},
                },
                'talles': talles,
            }
        peces[nom] = {
            'bucles': bucles,
            'piquets': {t: [[round(x, 4), round(y, 4)] for x, y in pc.piquets[t]]
                        for t in TALLES},
            'fil': {t: [round(v, 4) for v in pc.fil[t]] for t in TALLES},
        }

    poms = []
    for f in res['files']:
        poms.append({
            'codi': f.codi, 'nom': f.nom, 'peca': f.peca, 'metode': f.metode,
            'bucles_ancora': f.bucles,
            'tipus_grading': f.tipus_grading,
            'classe_restriccio': ('delta_zero_dur' if f.tipus_grading == 'FIXED'
                                  else 'delta_lliure' if f.tipus_grading == 'LINEAR'
                                  else f.tipus_grading.lower()),
            'veredicte': f.veredicte(),
            'motiu_exclusio': f.motiu_exclusio,
            'valor_patro_cm': f.valor_patro_cm,
            'valor_fitxa_cm': f.valor_fitxa,
            'valor_camp_cm': ({t: round(v, 6) for t, v in f.valor_camp.items()}
                              if f.mesurable else {}),
            'delta_de_deltes_mm': ({t: round(f.delta_de_deltes_mm(t), 4) for t in TALLES}
                                   if f.mesurable else {}),
            'delta_absolut_mm': ({t: round(f.delta_absolut_mm(t), 4) for t in TALLES}
                                 if f.mesurable else {}),
        })

    return {
        'meta': {
            'nom': 'parity_837',
            'proposit': 'Banc de paritat del solver F6: el grading real de la Montse '
                        'aparellat vèrtex a vèrtex amb el patró del model 1383.',
            'esmena': 'A0 (Agus, 27/08) — regenerat des del fitxer amb capa 14; '
                      'superseeix el banc del 26/08 sense moure cap vèrtex de tall.',
            'font_camp': camp.fitxer.name,
            'md5_camp': camp.md5,
            'font_mestre': MESTRE_837.name,
            'md5_mestre': res['mestre_md5'],
            'textos_document': list(camp.textos_document),
            'unitats': camp.unitats + ' · totes les coordenades i deltes del fitxer, en mm',
            'talles': list(TALLES),
            'talla_base': BASE,
            'capes': list(camp.capes),
            'model': MODEL_BANC,
            'pattern_file': res['bd']['pattern_file'],
            'grading_version': res['bd']['gv'],
            'convencio_1': ("bucle de TALL: origen = vèrtex de Y mínima a la talla base. "
                            "bucle de COSIT: origen = el punt més proper a l'origen del "
                            "tall (l'argmin de Y propi erra a la TAPETA). Les altres talles "
                            "l'hereten per identitat d'índex. Únic als dos bucles (A4)."),
            'correspondencia': ("vèrtex a vèrtex per identitat d'índex; recompte i "
                                "classificació gir/corba invariants a les cinc talles (A1, "
                                "A2) als DOS bucles; la base del camp és el MATEIX contorn "
                                "que el patró mestre del 1383, desviació 0,000000000 mm "
                                "als dos bucles (A5). Les àncores de POM no es transporten: "
                                "són vèrtexs natius."),
            'llindar_mm': LLINDAR_MM,
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

    out.append(_capcalera("A · VERIFICACIONS D'INGESTA (els dos bucles)"))
    vs = verifica(camp) + verifica_contra_mestre(camp) + verifica_superseeix(camp)
    dolentes = [v for v in vs if not v.ok]
    out.append(f'  {len(vs)} verificacions · {len(dolentes)} vermelles')
    for v in dolentes:
        out.append(f'  FAIL {v.nom} — {v.detall}')
    for v in vs:
        if v.nom.startswith(('A5 · base ≡ mestre · cosit', 'A6')):
            out.append(f'  {"OK  " if v.ok else "FAIL"} {v.nom} — {v.detall}')

    out.append(_capcalera('B · ALINEACIÓ (per bucle)'))
    for nom, pc in camp.peces.items():
        for capa in camp.capes:
            al = alinea(pc.bucle(capa))
            cand = ' · '.join(f'{k}={v:.2f}' for k, v in al.candidats.items())
            rol = 'tall ' if capa == CAPA_TALL else 'cosit'
            out.append(f'  {nom:16s} {rol} mètode={al.metode:18s} àncora={al.ancora} '
                       f'residu_max(XL)={al.residu_max["XL"]:6.2f} mm  [{cand}]')

    out.append(_capcalera('C0 · LES ÀNCORES SÓN NATIVES (cap transport)'))
    pitjor = max((abs(f.valor_camp[BASE] - f.valor_patro_cm) * 10.0
                  for f in mesurables if f.valor_patro_cm is not None), default=0.0)
    out.append(f'  {"OK  " if pitjor <= TOL_ARRODONIMENT_MM else "FAIL"} desviació màxima '
               f'base↔patró: {pitjor:.4f} mm sobre {len(mesurables)} POMs '
               f'(tolerància {TOL_ARRODONIMENT_MM} mm = mig decimal de com es desa '
               f'`valor_mesurat_cm`)')
    out.append(f'  {"OK  " if not res["punts_incoherents"] else "FAIL"} '
               f'{len(res["bd"]["punts"])} PatternPoint contra el camp: '
               f'{len(res["punts_incoherents"])} incoherents')

    out.append(_capcalera('C · PARITAT · Δ DE DELTES (mm)'))
    out.append(f'  {"POM":5s} {"peça":10s} {"tipus":6s} {"mèt.":9s} {"bucle":5s} '
               + ' '.join(f'{t:>7s}' for t in TALLES) + f' {"|Δ|max":>7s}  veredicte')
    for f in files:
        if not f.mesurable:
            continue
        ds = [f.delta_de_deltes_mm(t) for t in TALLES]
        out.append(f'  {f.codi:5s} {f.peca.replace("837.",""):10s} {f.tipus_grading:6s} '
                   f'{f.metode:9s} {f.bucles:5s} ' + ' '.join(f'{d:+7.2f}' for d in ds)
                   + f' {f.desviacio_mm():7.2f}  {f.veredicte()}')

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
                   + ' '.join(f'{f.valor_camp[t] - f.valor_camp[BASE]:+7.2f}'
                              for t in TALLES))

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
                       f'{f.peca.replace("837.",""):10s} |Δ|max={m:6.2f} mm')

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
    for v in ('PARITAT', 'DESVIAT', 'NO MESURABLE'):
        if v in per_v:
            out.append(f'  {v:13s} {len(per_v[v]):2d}/{len(files)}  '
                       f'{" ".join(sorted(per_v[v]))}')
    return '\n'.join(out)


if __name__ == '__main__':
    resultat = executa()
    print(informe(resultat))
    desti = escriu_dataset(resultat)
    print(f'\nDataset escrit: {desti} ({desti.stat().st_size / 1024:.0f} KB)')
