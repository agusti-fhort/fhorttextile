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

**El que el fitxer NO porta**, i consta perquè mana sobre tot el que ve després:

  · **Cap capa 14.** El camp només té el contorn de TALL (capa 1). Les receptes de POM del
    1383 viuen quasi totes damunt de la línia de COSIT (capa 14 del germà `…_AGUS.DXF`),
    que aquí no existeix. Qui vulgui mesurar-hi un POM ha de TRANSPORTAR-HI la seva
    àncora; v. `rosetta_837.transporta_peca`.
  · **Cap número de regla.** Els `# N` de la capa 1 del fitxer mestre no hi són. El camp
    és extensional: coordenades per talla, no regles.

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
#: la sessió Montse; aquí només se'n diu el camí.
CAMP_837 = REPO / 'docs' / 'ordres' / '837 CORS 194 VESTIT M3-4 ESCALAT.DXF'

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

#: La capa del contorn de tall. L'única que el camp porta.
CAPA_TALL = '1'

#: Dos vèrtexs per sota d'això són el mateix punt. Mateix valor que `aama_reader`.
TOL_MM = 0.01


# ─────────────────────────────────────────────────────────────────────────────
# El camp
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PecaCamp:
    """Una peça del banc, amb les seves cinc talles ja aparellades vèrtex a vèrtex."""

    nom: str
    #: talla → contorn de tall, en mm, sense el vèrtex de tancament duplicat.
    contorn: dict[str, tuple[tuple[float, float], ...]]
    #: gir / corba per vèrtex. És INVARIANT per talla (verificat), per això és una sola
    #: tupla i no un diccionari: si depengués de la talla, la correspondència ja seria falsa.
    tipus: tuple[str, ...]
    #: talla → piquets (capa 4), en mm.
    piquets: dict[str, tuple[tuple[float, float], ...]]
    #: talla → fil de la roba (capa 7): (x1, y1, x2, y2).
    fil: dict[str, tuple[float, float, float, float]]
    #: CONVENCIÓ-1: índex del vèrtex de Y mínima a la talla base.
    origen_bucle: int

    @property
    def n_vertexs(self) -> int:
        return len(self.contorn[BASE])

    def desplacaments(self, talla: str) -> tuple[tuple[float, float], ...]:
        """El camp de desplaçament CRU d'aquesta talla respecte de la base, vèrtex a vèrtex.

        Cru vol dir *amb la translació de niada a dins*, si n'hi ha. Separar-la és feina
        d'`alinea`, i és una feina de PRESENTACIÓ: cap mesura de POM no la nota, perquè
        totes quatre (recta, vora, projecció, ortogonal) són invariants per translació.
        """
        base = self.contorn[BASE]
        return tuple(
            (p[0] - b[0], p[1] - b[1]) for p, b in zip(self.contorn[talla], base)
        )


@dataclass(frozen=True)
class Camp:
    fitxer: Path
    md5: str
    peces: dict[str, PecaCamp]
    #: El que el DXF diu de si mateix (autor, unitats, talla de mostra, estil).
    textos_document: tuple[str, ...]
    #: Factor a mm i com s'ha sabut. Al 837 la capçalera és buida i s'ha deduït.
    unitats: str
    #: peça → talla → classificació gir/corba LLEGIDA D'AQUELLA TALLA. Viu aquí i no a
    #: `PecaCamp` a posta: `PecaCamp.tipus` és la de la base i és la que val un cop A2 ha
    #: passat; aquesta només existeix per poder-la comparar, que és el que A2 fa.
    tipus_per_talla: dict[str, dict[str, tuple[str, ...]]]


def llegeix_camp(cami: Path = CAMP_837) -> Camp:
    """Els 25 BLOCKs → 5 peces × 5 talles, agrupades pel sufix del nom del bloc."""
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
    tipus_per_talla: dict[str, dict[str, tuple[str, ...]]] = {}
    for nom, per_talla in agrupat.items():
        faltants = [t for t in TALLES if t not in per_talla]
        if faltants:
            raise ValueError(f'A la peça «{nom}» li falten les talles {faltants}.')
        peces[nom] = _peca_camp(nom, per_talla)
        tipus_per_talla[nom] = {
            t: tuple(q.kind.value for q in _vora_de_tall(per_talla[t], nom, t).points)
            for t in TALLES
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


def _peca_camp(nom: str, per_talla: dict[str, PieceData]) -> PecaCamp:
    contorn, piquets, fil = {}, {}, {}
    tipus: tuple[str, ...] = ()
    for talla in TALLES:
        peca = per_talla[talla]
        vora = _vora_de_tall(peca, nom, talla)
        contorn[talla] = tuple((p.x, p.y) for p in vora.points)
        if talla == BASE:
            tipus = tuple(p.kind.value for p in vora.points)
        piquets[talla] = tuple((n.x, n.y) for n in peca.notches)
        g = peca.grain
        if g is None:
            raise ValueError(f'La peça «{nom}» talla {talla} no porta fil (capa 7).')
        fil[talla] = (g.x1, g.y1, g.x2, g.y2)

    ys = [p[1] for p in contorn[BASE]]
    origen = min(range(len(ys)), key=lambda i: ys[i])
    return PecaCamp(nom=nom, contorn=contorn, tipus=tipus, piquets=piquets,
                    fil=fil, origen_bucle=origen)


def _vora_de_tall(peca: PieceData, nom: str, talla: str):
    talls = [b for b in peca.boundaries if b.layer == CAPA_TALL]
    if len(talls) != 1:
        raise ValueError(
            f'La peça «{nom}» talla {talla} té {len(talls)} contorns de tall i n\'ha de '
            f'tenir exactament un.'
        )
    if not talls[0].closed:
        raise ValueError(f'El contorn de tall de «{nom}» talla {talla} no és tancat.')
    return talls[0]


# ─────────────────────────────────────────────────────────────────────────────
# Verificacions (A)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Verificacio:
    nom: str
    ok: bool
    detall: str


def verifica(camp: Camp) -> list[Verificacio]:
    """Les quatre coses que han de ser certes perquè això sigui un camp i no un ram.

    Cap d'elles s'assumeix i cap es dona per bona per haver-la vista una vegada: si el dia
    que la Montse ens passi el 838 alguna falla, el banc ho ha de dir abans de mesurar res.
    """
    out: list[Verificacio] = []
    out += _verifica_recompte(camp)
    out += _verifica_correspondencia(camp)
    out += _verifica_orientacio(camp)
    out += _verifica_origen_unic(camp)
    return out


def _verifica_recompte(camp: Camp) -> list[Verificacio]:
    out = []
    for nom, p in camp.peces.items():
        n = {t: len(p.contorn[t]) for t in TALLES}
        ok = len(set(n.values())) == 1
        out.append(Verificacio(
            f'A1 · recompte de vèrtexs · {nom}', ok,
            f'{n[BASE]} vèrtexs a les cinc talles' if ok else f'recomptes diferents: {n}',
        ))
    return out


def _verifica_correspondencia(camp: Camp) -> list[Verificacio]:
    """Mateix índex = mateix punt material. Es mesura amb la CLASSIFICACIÓ gir/corba.

    És la prova barata i no és feble: el patró de girs d'una peça és la seva empremta
    (28 girs al DELANTERO, 24 a l'ESPALDA, 9 a la MANGA…), i que les cinc talles la
    comparteixin vèrtex a vèrtex vol dir que el CAD va escriure les cinc del mateix bucle.

    Compara **contra la base**, índex per índex, i diu el PRIMER que no casa. Un empat de
    recomptes ja l'ha mirat A1; això mira que els vèrtexs siguin els mateixos, no que
    n'hi hagi els mateixos.
    """
    out = []
    for nom, p in camp.peces.items():
        xocs: list[str] = []
        for talla in TALLES:
            if talla == BASE:
                continue
            propis = camp.tipus_per_talla[nom][talla]
            for i, (a, b) in enumerate(zip(p.tipus, propis)):
                if a != b:
                    xocs.append(f'{talla}[{i}]: {a}≠{b}')
                    break
        out.append(Verificacio(
            f'A2 · correspondència vèrtex a vèrtex · {nom}', not xocs,
            f'{len(p.tipus)} vèrtexs, classificació invariant a les cinc talles'
            if not xocs else f'la classificació balla: {"; ".join(xocs)}',
        ))
    return out


def _verifica_orientacio(camp: Camp) -> list[Verificacio]:
    out = []
    for nom, p in camp.peces.items():
        arees = {t: area_signada(p.contorn[t]) for t in TALLES}
        ok = all(a > 0 for a in arees.values())
        out.append(Verificacio(
            f'A3 · orientació CCW · {nom}', ok,
            'CCW a les cinc talles (àrea signada > 0)' if ok
            else f'orientacions barrejades: { {t: ("CCW" if a > 0 else "CW") for t, a in arees.items()} }',
        ))
    return out


def _verifica_origen_unic(camp: Camp) -> list[Verificacio]:
    """CONVENCIÓ-1 només és una regla si l'argmin és ÚNIC. Si empatés, seria una tria."""
    out = []
    for nom, p in camp.peces.items():
        base = p.contorn[BASE]
        ymin = min(q[1] for q in base)
        cands = [i for i, q in enumerate(base) if abs(q[1] - ymin) <= 1e-9]
        ok = len(cands) == 1
        out.append(Verificacio(
            f'A4 · CONVENCIÓ-1 · origen únic · {nom}', ok,
            f'índex {p.origen_bucle} (y={ymin:.3f} mm), únic' if ok
            else f'{len(cands)} vèrtexs empaten a y mínima: {cands}',
        ))
    return out


def verifica_contra_mestre(camp: Camp, mestre: Path = MESTRE_837) -> list[Verificacio]:
    """A5 · La talla BASE del camp ha de ser EL MATEIX contorn que el patró del 1383.

    Sense això, el Rosetta compararia dos vestits diferents i tota la resta seria soroll.
    La comparació és vèrtex a vèrtex i no per bbox: dues peces poden compartir capsa i no
    compartir ni un punt.
    """
    doc = AAMAReader().read(mestre.read_bytes())
    per_nom = {p.nom_block: p for p in doc.pieces}
    out = []
    for nom, p in camp.peces.items():
        alt = per_nom.get(nom)
        if alt is None:
            out.append(Verificacio(f'A5 · base ≡ mestre · {nom}', False,
                                   f'«{nom}» no és al patró mestre'))
            continue
        talls = [b for b in alt.boundaries if b.layer == CAPA_TALL]
        pts = tuple((q.x, q.y) for q in talls[0].points) if talls else ()
        base = p.contorn[BASE]
        if len(pts) != len(base):
            out.append(Verificacio(f'A5 · base ≡ mestre · {nom}', False,
                                   f'{len(base)} vèrtexs al camp vs {len(pts)} al mestre'))
            continue
        dmax = max(math.dist(a, b) for a, b in zip(base, pts))
        out.append(Verificacio(
            f'A5 · base ≡ mestre · {nom}', dmax <= 1e-9,
            f'{len(base)} vèrtexs, desviació màxima {dmax:.9f} mm',
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


def alinea(peca: PecaCamp) -> Alineacio:
    n = peca.n_vertexs
    camps = {t: peca.desplacaments(t) for t in TALLES}

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
