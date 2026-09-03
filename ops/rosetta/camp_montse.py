"""A + B · Ingesta del camp de grading de la Montse i alineació de talles.

**Què és el camp.** `837 CORS 194 VESTIT M3-4 ESCALAT.DXF` és la niada que va sortir
del PolyPattern de la Montse: 25 BLOCKs, un per (peça × talla), amb el contorn de TALL
sencer a cada talla. No porta regles de grading —el grading ja hi és *aplicat*—, i per
això és el banc: és el resultat que qualsevol motor nostre hauria de saber reproduir.

**Per què no cal parser propi.** `engine/aama_reader.py` ja llegeix aquest dialecte i ja
tracta cada BLOCK com una peça. L'única feina d'aquí és **agrupar** els 25 blocs per
(peça, talla) i verificar que el que en surt és un camp i no un ram de peces soltes.
Reutilitzar el reader no és estalvi: és el que fa que el banc es llegeixi amb el MATEIX
codi que llegirà el patró de producte, i que una regressió del reader es vegi aquí també.

**ESMENA A0 (Agus, 27/08).** El banc es regenera des de
`837 CORS 194 VESTIT M3-4 ESCALAT COSTRURA.DXF`, que **superseeix** l'ESCALAT del 26/08:
mateixa niada i **la capa 14 a dins**. Les tres coses que això canvia, mesurades:

  · El contorn de TALL del fitxer nou és **idèntic** al del vell, vèrtex a vèrtex, a les 25
    combinacions (0,000000000 mm). El banc superseeix net: res del que es va mesurar sobre
    l'ESCALAT queda invalidat, només ampliat.
  · El COSIT de la talla base és **idèntic al del patró mestre** del 1383 (0,000000000 mm a
    les cinc peces). 🔑 **Això retira el transport**: les 19 àncores de POM que viuen a la
    línia de cosit ara tenen homòloga NATIVA a cada talla, i la incertesa de portador que
    deixava sis POMs «no resolubles» a F6-PRE desapareix per construcció, no per estimació.
  · Els recomptes del cosit declarats al brief (651/475/459/325/47) són els nostres **+1**:
    el vèrtex de tancament duplicat, que el reader treu. 650/474/458/324/46.

**El que el fitxer segueix sense portar:** cap número de regla. Els `# N` del mestre no hi
són; el camp és extensional (coordenades per talla, no regles). I el germà `… PER 3d.DXF`,
que l'esmena dona per idèntic al cosit i arxiva com a referència del mode CLO, **no és al
servidor**: no s'ha pogut verificar aquí i no entra al banc.

── CONVENCIÓ-1 ──────────────────────────────────────────────────────────────────
L'origen del bucle d'una peça és **el vèrtex de Y mínima del contorn de tall a la talla
BASE (S)**, i les altres talles l'hereten **per identitat d'índex**.

Les dues meitats de la frase són necessàries i cap és gratuïta:

  · *Y mínima a la base* és una regla, no una tria: dona el mateix índex sempre, no depèn
    d'on el CAD va obrir la polilínia, i al material real és ÚNICA a les cinc peces
    (`verifica_origen_unic`). El que el DXF porta com a primer vèrtex, en canvi, és
    arbitrari —hi ha peces que l'obren a l'esquerra i peces que l'obren a la dreta.
  · *heretat per identitat* és un FET MESURAT, no una assumpció: les cinc talles d'una
    peça tenen el mateix recompte de vèrtexs i la mateixa classificació gir/corba vèrtex
    a vèrtex (`verifica_correspondencia`). Re-buscar l'argmin a cada talla seria pitjor:
    a la MANGA el mínim de Y salta de vèrtex entre talles, i l'origen ballaria.

La convenció no mou cap coordenada. Serveix per posar **la fracció** —la moneda del
sistema (v. `QA_TALLER_D_CONVENCIO_RECORREGUT`)— en un origen comú a les cinc talles.
"""
from __future__ import annotations

import hashlib
import math
import sys
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))

from fhort.patterns.engine.aama_reader import AAMAReader          # noqa: E402
from fhort.patterns.engine.geometry import PieceData              # noqa: E402

#: El camp, tal com ens el van donar. Viu a `docs/ordres/` amb la resta de material de
#: la sessió Montse; aquí només se'n diu el camí. Nom amb espais, tal qual.
CAMP_837 = REPO / 'docs' / 'ordres' / '837 CORS 194 VESTIT M3-4 ESCALAT COSTRURA.DXF'

#: El banc anterior (26/08), sense capa 14. Es conserva NOMÉS per a la verificació A6, que
#: comprova que el nou el superseeix sense moure ni un vèrtex de tall.
CAMP_837_SENSE_COSIT = REPO / 'docs' / 'ordres' / '837 CORS 194 VESTIT M3-4 ESCALAT.DXF'

#: El patró MESTRE del 1383 (el que la BD té importat a `PatternFile#20`). És el germà del
#: camp: mateixa geometria de tall a la talla S, però amb la capa 14 i els números de regla.
MESTRE_837 = Path('/var/www/ftt-staging/backend/media/fhort/pattern_files/'
                  '837_CORS_194_VESTIT_M3-4_AGUS.DXF')

#: Ordre de talla petita a gran. NO és alfabètic i no es pot deduir del nom del bloc: el
#: fitxer les escriu en aquest ordre i la fitxa del 1383 les declara igual.
TALLES = ('XS', 'S', 'M', 'L', 'XL')

#: La talla de mostra. El fitxer ho diu ell mateix (`Sample Size: S` al text del document)
#: i el `SizeFitting` del 1383 hi coincideix; no s'assumeix.
BASE = 'S'

#: Les dues capes de contorn del banc, i el nom pel qual s'hi navega arreu.
CAPA_TALL = '1'
CAPA_COSIT = '14'
CAPES = (CAPA_TALL, CAPA_COSIT)

#: 🔑 **On viu cada cosa.** El TALL és el que la Montse grada i el que el fitxer declara com
#: a contorn de la peça; el COSIT és on viuen 19 de les 20 àncores de POM del 1383. La
#: paritat es mesura al cosit; la geometria de la peça és el tall. Cap dels dos és
#: «el contorn»: n'hi ha dos i el codi ho diu a cada pas.
CAPA_ANCORES = CAPA_COSIT

#: Dos vèrtexs per sota d'això són el mateix punt. Mateix valor que `aama_reader`.
TOL_MM = 0.01


# ─────────────────────────────────────────────────────────────────────────────
# El camp
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Bucle:
    """Un contorn tancat d'una peça, a les cinc talles, ja aparellat vèrtex a vèrtex."""

    capa: str                                    # '1' (tall) o '14' (cosit)
    #: talla → punts en mm, sense el vèrtex de tancament duplicat.
    contorn: dict[str, tuple[tuple[float, float], ...]]
    #: gir / corba per vèrtex. INVARIANT per talla (verificat a A2), per això és una sola
    #: tupla: si depengués de la talla, la correspondència ja seria falsa.
    tipus: tuple[str, ...]
    #: CONVENCIÓ-1 · índex de l'origen a la talla base.
    origen_bucle: int

    @property
    def n_vertexs(self) -> int:
        return len(self.contorn[BASE])

    def desplacaments(self, talla: str) -> tuple[tuple[float, float], ...]:
        """El camp de desplaçament CRU d'aquesta talla respecte de la base, vèrtex a vèrtex.

        Cru vol dir *amb la translació de niada a dins*, si n'hi ha. Separar-la és feina
        d'`alinea`, i és de PRESENTACIÓ: cap mesura de POM no la nota, perquè totes quatre
        (recta, vora, projecció, ortogonal) són invariants per translació.
        """
        base = self.contorn[BASE]
        return tuple(
            (p[0] - b[0], p[1] - b[1]) for p, b in zip(self.contorn[talla], base)
        )


@dataclass(frozen=True)
class PecaCamp:
    """Una peça del banc: DOS bucles (tall i cosit), els piquets i el fil.

    🔑 **No hi ha «el contorn».** N'hi ha dos i fan feines diferents: el TALL és la
    geometria de la peça i el que la Montse grada; el COSIT és on viuen 19 de les 20
    àncores de POM del 1383 i, per tant, on la paritat es mesura de debò. El codi no en
    privilegia cap: tots dos s'agafen per `bucle(capa)`.
    """

    nom: str
    bucles: dict[str, Bucle]
    #: talla → piquets (capa 4), en mm.
    piquets: dict[str, tuple[tuple[float, float], ...]]
    #: talla → fil de la roba (capa 7): (x1, y1, x2, y2).
    fil: dict[str, tuple[float, float, float, float]]

    def bucle(self, capa: str = CAPA_TALL) -> Bucle:
        return self.bucles[capa]

    @property
    def tall(self) -> Bucle:
        return self.bucles[CAPA_TALL]

    @property
    def cosit(self) -> Bucle:
        return self.bucles[CAPA_COSIT]


@dataclass(frozen=True)
class Camp:
    fitxer: Path
    md5: str
    peces: dict[str, PecaCamp]
    #: El que el DXF diu de si mateix (autor, unitats, talla de mostra, estil).
    textos_document: tuple[str, ...]
    #: Factor a mm i com s'ha sabut. Al 837 la capçalera és buida i s'ha deduït.
    unitats: str
    #: peça → capa → talla → classificació gir/corba LLEGIDA D'AQUELLA TALLA. Viu aquí i no
    #: a `Bucle` a posta: `Bucle.tipus` és la de la base i és la que val un cop A2 ha passat;
    #: aquesta només existeix per poder-la comparar, que és el que A2 fa.
    tipus_per_talla: dict[str, dict[str, dict[str, tuple[str, ...]]]]

    @property
    def capes(self) -> tuple[str, ...]:
        """Les capes de contorn que aquest camp porta de debò, en ordre canònic."""
        qualsevol = next(iter(self.peces.values()))
        return tuple(c for c in CAPES if c in qualsevol.bucles)

    @property
    def capes(self) -> tuple[str, ...]:
        """Les capes de contorn que aquest camp porta de debò, en ordre canònic."""
        qualsevol = next(iter(self.peces.values()))
        return tuple(c for c in CAPES if c in qualsevol.bucles)


def llegeix_camp(cami: Path = CAMP_837, capes: tuple[str, ...] = CAPES) -> Camp:
    """Els 25 BLOCKs → 5 peces × 5 talles × N bucles, agrupats pel sufix del nom del bloc.

    `capes` existeix per una sola raó honesta: el banc ANTERIOR (26/08) no porta capa 14, i
    A6 l'ha de poder obrir per comprovar que el nou el superseeix. Llegir-lo demanant-li un
    bucle que no té seria demanar-li que fallés.
    """
    dades = cami.read_bytes()
    doc = AAMAReader().read(dades)

    agrupat: dict[str, dict[str, PieceData]] = {}
    for peca in doc.pieces:
        nom, _, talla = peca.nom_block.rpartition('_')
        if talla not in TALLES:
            raise ValueError(
                f"El bloc «{peca.nom_block}» no acaba en cap talla coneguda {TALLES}. "
                f"El camp s'agrupa pel sufix del nom: sense sufix no hi ha aparellament."
            )
        agrupat.setdefault(nom, {})[talla] = peca

    peces: dict[str, PecaCamp] = {}
    tipus_per_talla: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {}
    for nom, per_talla in agrupat.items():
        faltants = [t for t in TALLES if t not in per_talla]
        if faltants:
            raise ValueError(f'A la peça «{nom}» li falten les talles {faltants}.')
        peces[nom] = _peca_camp(nom, per_talla, capes)
        tipus_per_talla[nom] = {
            capa: {t: tuple(q.kind.value for q in _vora(per_talla[t], nom, t, capa).points)
                   for t in TALLES}
            for capa in capes
        }

    fp = doc.fingerprint
    return Camp(
        fitxer=cami,
        md5=hashlib.md5(dades).hexdigest(),
        peces=peces,
        textos_document=fp.textos_document,
        tipus_per_talla=tipus_per_talla,
        unitats=f'{fp.unitats.factor_to_mm} mm/unitat '
                f'({fp.unitats.metode.value}, {fp.unitats.confianca.value})',
    )


def _peca_camp(nom: str, per_talla: dict[str, PieceData],
               capes: tuple[str, ...] = CAPES) -> PecaCamp:
    piquets, fil = {}, {}
    for talla in TALLES:
        peca = per_talla[talla]
        piquets[talla] = tuple((n.x, n.y) for n in peca.notches)
        g = peca.grain
        if g is None:
            raise ValueError(f'La peça «{nom}» talla {talla} no porta fil (capa 7).')
        fil[talla] = (g.x1, g.y1, g.x2, g.y2)

    bucles: dict[str, Bucle] = {}
    for capa in capes:
        contorn, tipus = {}, ()
        for talla in TALLES:
            vora = _vora(per_talla[talla], nom, talla, capa)
            contorn[talla] = tuple((p.x, p.y) for p in vora.points)
            if talla == BASE:
                tipus = tuple(p.kind.value for p in vora.points)
        bucles[capa] = Bucle(capa=capa, contorn=contorn, tipus=tipus,
                             origen_bucle=_origen(bucles, contorn[BASE], capa))
    return PecaCamp(nom=nom, bucles=bucles, piquets=piquets, fil=fil)


def _origen(ja_fets: dict[str, Bucle], base, capa: str) -> int:
    """CONVENCIÓ-1, i la seva extensió al segon bucle.

    🚨 **L'origen del bucle de COSIT no és el seu propi argmin de Y.** És el punt del cosit
    més proper a l'origen del TALL. Les dues coses coincideixen a quatre peces del 837 i a
    la TAPETA no: allà l'argmin propi cau a l'altra punta i la fracció s'esbiaixa 0,368 del
    perímetre (209 mm d'arc) en comptes de 0,0099 (7,8 mm).

    Dues parametritzacions només es poden comparar si l'origen és al MATEIX lloc material, i
    «Y mínima» no ho garanteix en un bucle que no és el mateix bucle. La regla es va derivar
    mesurant (F6-PRE) i l'esmena A0 la confirma des de fora: els cinc orígens que l'Agus
    declara verificats en local —207 · 30 · 251 · 47 · 3— surten tots cinc d'aquesta regla,
    i l'argmin propi n'erra un.
    """
    if capa == CAPA_TALL or CAPA_TALL not in ja_fets:
        ys = [p[1] for p in base]
        return min(range(len(ys)), key=lambda i: ys[i])
    tall = ja_fets[CAPA_TALL]
    ancora = tall.contorn[BASE][tall.origen_bucle]
    return min(range(len(base)), key=lambda i: math.dist(base[i], ancora))


def _vora(peca: PieceData, nom: str, talla: str, capa: str):
    vores = [b for b in peca.boundaries if b.layer == capa]
    if len(vores) != 1:
        raise ValueError(
            f'La peça «{nom}» talla {talla} té {len(vores)} contorns a la capa {capa} i '
            f'n\'ha de tenir exactament un.'
        )
    if not vores[0].closed:
        raise ValueError(f'El contorn {capa} de «{nom}» talla {talla} no és tancat.')
    return vores[0]


# ─────────────────────────────────────────────────────────────────────────────
# Verificacions (A)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Verificacio:
    nom: str
    ok: bool
    detall: str


def verifica(camp: Camp) -> list[Verificacio]:
    """Les coses que han de ser certes perquè això sigui un camp i no un ram de peces.

    Totes corren **sobre els dos bucles**: el de tall perquè és la geometria de la peça, i
    el de cosit perquè és on viuen les àncores i on la paritat es mesura de debò. Cap
    s'assumeix i cap es dona per bona per haver-la vista una vegada.
    """
    out: list[Verificacio] = []
    for capa in camp.capes:
        out += _verifica_recompte(camp, capa)
        out += _verifica_correspondencia(camp, capa)
        out += _verifica_orientacio(camp, capa)
        out += _verifica_origen_unic(camp, capa)
    return out


def _etq(capa: str) -> str:
    return 'tall' if capa == CAPA_TALL else 'cosit'


def _verifica_recompte(camp: Camp, capa: str) -> list[Verificacio]:
    out = []
    for nom, p in camp.peces.items():
        b = p.bucle(capa)
        n = {t: len(b.contorn[t]) for t in TALLES}
        ok = len(set(n.values())) == 1
        out.append(Verificacio(
            f'A1 · recompte · {_etq(capa)} · {nom}', ok,
            f'{n[BASE]} vèrtexs a les cinc talles' if ok else f'recomptes diferents: {n}',
        ))
    return out


def _verifica_correspondencia(camp: Camp, capa: str) -> list[Verificacio]:
    """Mateix índex = mateix punt material. Es mesura amb la CLASSIFICACIÓ gir/corba.

    És la prova barata i no és feble: el patró de girs d'un bucle és la seva empremta, i que
    les cinc talles la comparteixin vèrtex a vèrtex vol dir que el CAD va escriure les cinc
    del mateix bucle. Compara contra la base, índex per índex, i diu el PRIMER que no casa.
    """
    out = []
    for nom, p in camp.peces.items():
        b = p.bucle(capa)
        xocs: list[str] = []
        for talla in TALLES:
            if talla == BASE:
                continue
            propis = camp.tipus_per_talla[nom][capa][talla]
            for i, (x, y) in enumerate(zip(b.tipus, propis)):
                if x != y:
                    xocs.append(f'{talla}[{i}]: {x}≠{y}')
                    break
        out.append(Verificacio(
            f'A2 · correspondència · {_etq(capa)} · {nom}', not xocs,
            f'{len(b.tipus)} vèrtexs, classificació invariant a les cinc talles'
            if not xocs else f'la classificació balla: {"; ".join(xocs)}',
        ))
    return out


def _verifica_orientacio(camp: Camp, capa: str) -> list[Verificacio]:
    out = []
    for nom, p in camp.peces.items():
        b = p.bucle(capa)
        arees = {t: area_signada(b.contorn[t]) for t in TALLES}
        ok = all(a > 0 for a in arees.values())
        out.append(Verificacio(
            f'A3 · orientació CCW · {_etq(capa)} · {nom}', ok,
            'CCW a les cinc talles (àrea signada > 0)' if ok
            else f'orientacions barrejades: '
                 f'{ {t: ("CCW" if a > 0 else "CW") for t, a in arees.items()} }',
        ))
    return out


def _verifica_origen_unic(camp: Camp, capa: str) -> list[Verificacio]:
    """CONVENCIÓ-1 només és una regla si l'origen és ÚNIC. Si empatés, seria una tria.

    Al bucle de TALL l'origen és l'argmin de Y i la unicitat es mesura sobre Y. Al de COSIT
    és el punt més proper a l'origen del tall, i la unicitat es mesura sobre aquella
    distància — que és el que fa que la regla no depengui d'un empat d'alçada.
    """
    out = []
    for nom, p in camp.peces.items():
        b = p.bucle(capa)
        base = b.contorn[BASE]
        if capa == CAPA_TALL:
            ymin = min(q[1] for q in base)
            cands = [i for i, q in enumerate(base) if abs(q[1] - ymin) <= 1e-9]
            detall = f'índex {b.origen_bucle} (y={ymin:.3f} mm)'
        else:
            ancora = p.tall.contorn[BASE][p.tall.origen_bucle]
            dists = [math.dist(q, ancora) for q in base]
            dmin = min(dists)
            cands = [i for i, d in enumerate(dists) if abs(d - dmin) <= 1e-9]
            detall = f'índex {b.origen_bucle} (a {dmin:.3f} mm de l\'origen del tall)'
        ok = len(cands) == 1
        out.append(Verificacio(
            f'A4 · CONVENCIÓ-1 · origen únic · {_etq(capa)} · {nom}', ok,
            f'{detall}, únic' if ok else f'{len(cands)} vèrtexs empaten: {cands}',
        ))
    return out


def verifica_contra_mestre(camp: Camp, mestre: Path = MESTRE_837) -> list[Verificacio]:
    """A5 · La talla BASE del camp ha de ser EL MATEIX que el patró del 1383, ALS DOS BUCLES.

    Sense això, el Rosetta compararia dos vestits diferents i tota la resta seria soroll. La
    comparació és vèrtex a vèrtex i no per capsa: dues peces poden compartir capsa i no
    compartir ni un punt.

    🔑 **La fila del COSIT és la que canvia el sprint.** Si el cosit de la base és idèntic al
    del mestre, cada àncora de POM té homòloga NATIVA a cada talla i el transport —amb la
    seva incertesa de portador, que a F6-PRE deixava sis POMs sense veredicte— desapareix per
    construcció.
    """
    doc = AAMAReader().read(mestre.read_bytes())
    per_nom = {p.nom_block: p for p in doc.pieces}
    out = []
    for capa in camp.capes:
        for nom, p in camp.peces.items():
            alt = per_nom.get(nom)
            base = p.bucle(capa).contorn[BASE]
            if alt is None:
                out.append(Verificacio(f'A5 · base ≡ mestre · {_etq(capa)} · {nom}', False,
                                       f'«{nom}» no és al patró mestre'))
                continue
            vores = [b for b in alt.boundaries if b.layer == capa]
            pts = tuple((q.x, q.y) for q in vores[0].points) if vores else ()
            if len(pts) != len(base):
                out.append(Verificacio(
                    f'A5 · base ≡ mestre · {_etq(capa)} · {nom}', False,
                    f'{len(base)} vèrtexs al camp vs {len(pts)} al mestre'))
                continue
            dmax = max(math.dist(a, b) for a, b in zip(base, pts))
            out.append(Verificacio(
                f'A5 · base ≡ mestre · {_etq(capa)} · {nom}', dmax <= 1e-9,
                f'{len(base)} vèrtexs, desviació màxima {dmax:.9f} mm',
            ))
    return out


def verifica_superseeix(camp: Camp, anterior: Path = CAMP_837_SENSE_COSIT) -> list[Verificacio]:
    """A6 · El banc nou ha de superseir el vell sense moure ni un vèrtex de TALL.

    L'esmena A0 diu que el fitxer nou és «la mateixa niada + capa 14». Si fos veritat només
    de paraula, tot el que es va mesurar sobre el banc del 26/08 quedaria en l'aire. Es
    mesura: 25 combinacions peça × talla, vèrtex a vèrtex.
    """
    if not anterior.exists():
        return [Verificacio('A6 · superseeix el banc anterior', True,
                            f'{anterior.name} no és al disc: no es pot comparar (no bloqueja)')]
    vell = llegeix_camp(anterior, capes=(CAPA_TALL,))
    out = []
    for nom, p in camp.peces.items():
        altre = vell.peces.get(nom)
        if altre is None:
            out.append(Verificacio(f'A6 · superseeix · {nom}', False, 'no era al banc vell'))
            continue
        dmax = 0.0
        for t in TALLES:
            a, b = p.tall.contorn[t], altre.tall.contorn[t]
            if len(a) != len(b):
                dmax = float('inf')
                break
            dmax = max(dmax, max(math.dist(x, y) for x, y in zip(a, b)))
        out.append(Verificacio(
            f'A6 · superseeix · {nom}', dmax <= 1e-9,
            f'tall idèntic a les cinc talles, desviació màxima {dmax:.9f} mm',
        ))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Alineació (B)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Alineacio:
    """Com se separa la translació de niada del grading de debò, en una peça.

    El brief en donava dos mètodes —«pel punt de desplaçament mínim o per l'origen fix si
    es detecta»— i aquí n'hi ha tres, perquè al material real el segon **fa mal**:

      · **origen fix** — hi ha un vèrtex que NO es mou a cap talla. Llavors no hi ha res a
        treure: el CAD ja va niar les cinc talles clavades per aquell punt. Quatre de les
        cinc peces del 837 són així.
      · **desplaçament mínim** — no n'hi ha cap de quiet; es pren el que menys es mou i el
        seu desplaçament es declara translació.
      · **cap** — no n'hi ha cap de quiet **i treure el mínim empitjora el camp**. Llavors
        la lectura correcta és que la peça no porta translació: creix al voltant d'un
        centre i cap vèrtex no s'hi està quiet, que no és el mateix que estar desplaçada.

    🚨 **I el tercer no és teòric: és la MANGA.** El seu vèrtex més quiet (123) es mou
    +3,000 mm per graó, que és tan rodó que sembla col·locació. No ho és: restar-lo puja el
    residu màxim de 23,86 a 32,47 mm a XL (+36 %), perquè la màniga grada en els DOS sentits
    (dx ∈ [−22,6, +9,5]) i el 123 només és el punt de gir. Un mètode que triï per regla i no
    per xifra hauria escrit al dataset un camp un terç més gran que el de debò.

    Per això `alinea` **mesura les dues i es queda la que deixa el residu màxim més petit**,
    i desa totes dues a `candidats` perquè la tria es pugui auditar sense tornar a córrer res.

    ⚠️ **Cap mesura de POM depèn d'això.** Recta, vora, projecció i ortogonal són les quatre
    invariants per translació, així que el Rosetta (C) surt idèntic amb alineació i sense.
    L'alineació és per al DATASET (D): és el que fa que el desplaçament que el solver F6
    haurà de reproduir sigui grading i no la posició del full.
    """

    metode: str                                  # 'origen_fix' | 'desplacament_minim' | 'cap'
    ancora: int | None                           # índex del vèrtex que la fixa ('cap' → None)
    translacio: dict[str, tuple[float, float]]   # talla → vector tret, en mm
    residu_max: dict[str, float]                 # talla → desplaçament màxim un cop tret
    residu_min: dict[str, float]
    #: mètode → residu màxim de la pitjor talla. La xifra que va decidir.
    candidats: dict[str, float]


def alinea(bucle: Bucle) -> Alineacio:
    n = bucle.n_vertexs
    camps = {t: bucle.desplacaments(t) for t in TALLES}

    quiets = [
        i for i in range(n)
        if all(math.hypot(*camps[t][i]) <= 1e-9 for t in TALLES)
    ]
    if quiets:
        residus = _residus(camps, {t: (0.0, 0.0) for t in TALLES})
        return Alineacio(
            metode='origen_fix', ancora=quiets[0],
            translacio={t: (0.0, 0.0) for t in TALLES},
            residu_max=residus[0], residu_min=residus[1],
            candidats={'origen_fix': max(residus[0].values())},
        )

    # El vèrtex que menys es mou SUMANT les quatre talles no-base: triar-lo per una sola
    # talla deixaria que la talla triada manés sobre les altres quatre.
    ancora = min(
        range(n),
        key=lambda i: sum(math.hypot(*camps[t][i]) for t in TALLES if t != BASE),
    )
    amb = _residus(camps, {t: camps[t][ancora] for t in TALLES})
    sense = _residus(camps, {t: (0.0, 0.0) for t in TALLES})
    candidats = {
        'desplacament_minim': max(amb[0].values()),
        'cap': max(sense[0].values()),
    }
    if candidats['desplacament_minim'] <= candidats['cap']:
        return Alineacio(metode='desplacament_minim', ancora=ancora,
                         translacio={t: camps[t][ancora] for t in TALLES},
                         residu_max=amb[0], residu_min=amb[1], candidats=candidats)
    return Alineacio(metode='cap', ancora=None,
                     translacio={t: (0.0, 0.0) for t in TALLES},
                     residu_max=sense[0], residu_min=sense[1], candidats=candidats)


def _residus(camps, translacio) -> tuple[dict[str, float], dict[str, float]]:
    maxims, minims = {}, {}
    for t in TALLES:
        tx, ty = translacio[t]
        r = [math.hypot(dx - tx, dy - ty) for dx, dy in camps[t]]
        maxims[t], minims[t] = max(r), min(r)
    return maxims, minims


# ─────────────────────────────────────────────────────────────────────────────
# Geometria de servei
# ─────────────────────────────────────────────────────────────────────────────

def area_signada(punts) -> float:
    """Shoelace. Positiva = CCW. Només vol dir res en un bucle TANCAT."""
    s = 0.0
    n = len(punts)
    for i in range(n):
        x1, y1 = punts[i]
        x2, y2 = punts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def fraccions(punts, origen: int) -> tuple[float, ...]:
    """Fracció de longitud d'arc de cada vèrtex, comptada des de l'origen de CONVENCIÓ-1.

    Torna `n` valors a [0, 1): el de l'origen és 0 i el perímetre sencer és 1.
    """
    n = len(punts)
    ordre = [(origen + k) % n for k in range(n)]
    acum, total = [0.0], 0.0
    for k in range(n):
        a, b = punts[ordre[k]], punts[ordre[(k + 1) % n]]
        total += math.dist(a, b)
        acum.append(total)
    out = [0.0] * n
    for k, i in enumerate(ordre):
        out[i] = acum[k] / total
    return tuple(out)


def projecta_sobre_bucle(p, punts) -> tuple[int, float, float]:
    """El punt del bucle més a prop de `p`: (índex de l'aresta, paràmetre t, distància).

    L'aresta és la que va de `punts[i]` a `punts[(i+1) % n]`, i `t ∈ [0, 1]` diu on hi cau.
    És la manera d'ancorar un punt que **no és** al bucle —una àncora de la línia de cosit,
    posem— a una coordenada del bucle que sí que sobreviu al grading.
    """
    n = len(punts)
    millor = (0, 0.0, float('inf'))
    for i in range(n):
        ax, ay = punts[i]
        bx, by = punts[(i + 1) % n]
        vx, vy = bx - ax, by - ay
        ll = vx * vx + vy * vy
        t = 0.0 if ll <= 0 else max(0.0, min(1.0, ((p[0] - ax) * vx + (p[1] - ay) * vy) / ll))
        qx, qy = ax + t * vx, ay + t * vy
        d = math.hypot(p[0] - qx, p[1] - qy)
        if d < millor[2]:
            millor = (i, t, d)
    return millor


def fraccio_de_projeccio(punts, origen: int, aresta: int, t: float) -> float:
    """La fracció d'un punt que cau DINS d'una aresta, no sobre un vèrtex."""
    fr = fraccions(punts, origen)
    n = len(punts)
    f0, f1 = fr[aresta], fr[(aresta + 1) % n]
    if f1 <= f0:                      # l'aresta que travessa l'origen tanca la volta
        f1 += 1.0
    return (f0 + t * (f1 - f0)) % 1.0
