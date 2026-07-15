"""Trams NATURALS: la vora llegida com l'ofici la llegeix, no com el CAD la va dibuixar.

**El problema.** `segmentar_vora` talla a cada punt de GIR, perquè és el que el CAD marca.
Però el CAD marca girs que no són cantonades: una sisa surt esmicolada en 4-5 micro-trams i
el selector de Cosir n'ofereix 25 on el patronista en veu 8. Els micro-trams no sobren —el
gest manual de precisió i l'aritmètica els necessiten—, però **no són la unitat de treball**.

**La llei: talla només on hi ha cantonada de debò.** Cantonada és una qüestió d'ANGLE, no de
la classificació del CAD (mateixa llei que A1 amb les pinces: angle, no forma). Un gir amb
desviació per sota del llindar és la corba que flueix, i es fusiona amb el veí.

**I els PIQUETS no tallen.** Aquesta és la peça que sosté tot el mòdul, i no és l'angle.
Als fitxers reals el piquet no és només una entitat de capa 4: està DIBUIXAT dins la
polilínia com una excursió en V (el Tate en té a la lateral, vèrtexs 69-71 i 101-103). Els
seus girs arriben a 63° —més forts que cantonades de debò com les de 28,5°— i, si es
tracten com a girs, **cap llindar d'angle separa res**: el rang del piquet i el de la
cantonada se solapen. Emmascarant-los, el buit és net i enorme (corbes ≤ 8,7° · cantonades
≥ 28,5° sobre Tate+AMELIA) i el llindar deixa de ser delicat: qualsevol valor entre 20° i
25° dona el mateix. Per això el piquet no és soroll a esquivar: és **metadada del tram**
(A2 se'n serveix per inferir frunzit) i viatja a dins.

**Els naturals són una VISTA derivada, no substitueixen els AUTO.** Es calculen a cada
lectura sobre la geometria; no es persisteixen. Els AUTO segueixen sent la granularitat fina
del motor (cobertura, aritmètica, gest manual A→B). Aquesta capa només diu, dels talls que
el CAD proposa, quins són frontera per a un humà.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, degrees, hypot

from .geometry import BoundaryData, LayerRole, NotchData, PieceData, PointKind
from .segments import acumulats_vora, longitud_poli, longitud_vora, _punts_del_tram

#: Llindar de desviació angular (graus) per sobre del qual un gir és CANTONADA.
#:
#: No és un número de reunió: surt del material real (T1b · Tate + AMELIA, 14 peces).
#: Amb els piquets emmascarats, la corba més forta fa 8,7° i la cantonada més feble 28,5°;
#: l'únic gir enmig és un (15,2°). 22° és el centre d'aquest buit, i tota la franja 20°–25°
#: dona resultats idèntics: TATE_FRONT surt amb 8 naturals (contra 25 AUTO), AMELIA amb 4.
LLINDAR_CANTONADA_GRAUS = 22.0

#: Com de lluny pot caure l'entitat de piquet del vèrtex que el dibuixa, en mm. Als fitxers
#: reals el piquet de la polilínia hi cau A SOBRE (0,00 mm); els que seuen a ~7,5 mm són
#: marques desplaçades que no toquen el contorn i no han d'emmascarar res.
TOL_PIQUET_MM = 0.5

#: Llargada màxima (mm) d'una excursió de piquet. El que hi ha entre dues potes de piquet
#: separades per menys d'això és el dent del piquet, no vora. Als fitxers reals les
#: excursions fan ~23 mm; una costura mai no és tan curta.
MAX_EXCURSIO_PIQUET_MM = 30.0


@dataclass(frozen=True)
class NaturalSegmentData:
    """Un tram natural: el que un patronista anomenaria UNA costura.

    Porta a dins de quins AUTO surt (`auto_index_inici`/`auto_index_fi` són índexs de vèrtex,
    igual que `SegmentData`) i quins piquets hi cauen, perquè la fusió sigui auditable: qui
    la miri ha de poder dir «aquest natural són aquells cinc micro-trams, i per això».
    """
    vora: int
    t_inici: float
    t_fi: float
    tipus_vora: LayerRole
    index_inici: int
    index_fi: int
    longitud_mm: float
    #: Índexs dels vèrtexs de GIR que s'han fusionat a dins (els que no eren cantonada).
    girs_fusionats: tuple[int, ...] = ()
    #: Piquets que cauen DINS el tram. Metadada, no frontera: A2 els llegeix per inferir
    #: frunzit (dos trams amb piquets que no casen en nombre = un dels dos va arrufat).
    piquets: tuple[NotchData, ...] = ()


def desviacio_angular(pts, i: int, closed: bool) -> float:
    """Quant gira la vora al vèrtex `i`, en graus. 0 = segueix recte · 180 = torna enrere.

    En una vora oberta els extrems no tenen dos costats i no es poden mesurar: són frontera
    per definició, i es retorna 180 perquè cap llindar no els deixi fora.
    """
    n = len(pts)
    if n < 3:
        return 180.0
    if not closed and (i == 0 or i == n - 1):
        return 180.0
    a, b, c = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
    if (a.x, a.y) == (b.x, b.y) or (b.x, b.y) == (c.x, c.y):
        # Vèrtex duplicat: no defineix cap direcció. No és cantonada de res.
        return 0.0
    d = degrees(atan2(c.y - b.y, c.x - b.x) - atan2(b.y - a.y, b.x - a.x))
    while d > 180.0:
        d -= 360.0
    while d < -180.0:
        d += 360.0
    return abs(d)


def _llarg_entre(pts, i: int, j: int) -> float:
    """Llargada recorrent la vora de `i` a `j` endavant (sense donar la volta)."""
    return sum(hypot(pts[k + 1].x - pts[k].x, pts[k + 1].y - pts[k].y) for k in range(i, j))


def vertexs_de_piquet(piece: PieceData, boundary: BoundaryData) -> set[int]:
    """Els vèrtexs que formen part d'una excursió de piquet: no poden tallar.

    El piquet real es reconeix perquè una entitat de capa 4 seu EXACTAMENT sobre un vèrtex
    del contorn. Dues potes de piquet a poca distància tanquen entre elles el dent, i tot el
    que hi ha al mig (el pic) també és piquet.
    """
    pts = boundary.points
    n = len(pts)
    if n < 2:
        return set()

    potes = {
        i for i, p in enumerate(pts)
        for k in (piece.notches or ())
        if hypot(p.x - k.x, p.y - k.y) <= TOL_PIQUET_MM
    }
    if not potes:
        return set()

    mask = set(potes)
    ordenades = sorted(potes)
    for a in ordenades:
        for b in ordenades:
            if b <= a:
                continue
            if _llarg_entre(pts, a, b) <= MAX_EXCURSIO_PIQUET_MM:
                mask.update(range(a, b + 1))
    return mask


def piquets_del_tram(piece: PieceData, boundary: BoundaryData, ini: int, fi: int) -> tuple[NotchData, ...]:
    """Els piquets que cauen sobre el recorregut `ini`→`fi` d'aquesta vora."""
    tram = _punts_del_tram(boundary.points, ini, fi, boundary.closed)
    dins = []
    for k in (piece.notches or ()):
        if any(hypot(p.x - k.x, p.y - k.y) <= TOL_PIQUET_MM for p in tram):
            dins.append(k)
    return tuple(dins)


def cantonades_naturals(
    piece: PieceData,
    boundary: BoundaryData,
    llindar_graus: float = LLINDAR_CANTONADA_GRAUS,
    talls_extra: tuple[int, ...] = (),
) -> list[int]:
    """Els vèrtexs on la vora es trenca de debò, en ordre.

    `talls_extra` són fronteres que no surten de l'angle sinó del domini: els EXTREMS DE
    PINÇA DECLARADA. Una pinça parteix la vora encara que hi arribi suau, perquè el que hi
    ha a banda i banda són dues costures diferents.
    """
    pts = boundary.points
    n = len(pts)
    if n < 2:
        return []

    mask = vertexs_de_piquet(piece, boundary)
    cantonades = {
        i for i, p in enumerate(pts)
        if p.kind is PointKind.TURN
        and i not in mask
        and desviacio_angular(pts, i, boundary.closed) >= llindar_graus
    }
    # Els extrems de pinça manen sobre la màscara i sobre l'angle: són domini, no geometria.
    cantonades.update(i for i in talls_extra if 0 <= i < n)

    if not boundary.closed:
        # Vora oberta: els extrems són frontera encara que hi arribi recta, o el primer i
        # l'últim tros quedarien orfes (mateixa llei que `segmentar_vora`).
        cantonades.update({0, n - 1})

    return sorted(cantonades)


def segmentar_vora_natural(
    piece: PieceData,
    boundary: BoundaryData,
    index_vora: int,
    llindar_graus: float = LLINDAR_CANTONADA_GRAUS,
    talls_extra: tuple[int, ...] = (),
) -> list[NaturalSegmentData]:
    """Els trams naturals d'una vora: de cantonada de debò a cantonada de debò.

    Els casos de vora que `segmentar_vora` ja tracta valen igual aquí, i per la mateixa raó:
    una vora sense cap cantonada (un coll rodó) és UN tram, no cap.
    """
    pts = boundary.points
    n = len(pts)
    if n < 2:
        return []
    total = longitud_vora(boundary)
    if total <= 0:
        return []

    cum, _ = acumulats_vora(boundary)
    cantonades = cantonades_naturals(piece, boundary, llindar_graus, talls_extra)

    def _fes(ini: int, fi: int) -> NaturalSegmentData | None:
        tram = _punts_del_tram(pts, ini, fi, boundary.closed)
        llarg = longitud_poli(tram)
        if llarg <= 0:
            return None
        recorregut = (
            list(range(ini, fi + 1)) if ini < fi
            else list(range(ini, n)) + list(range(0, fi + 1))
        )
        girs = tuple(
            i for i in recorregut[1:-1]
            if pts[i].kind is PointKind.TURN
        )
        return NaturalSegmentData(
            vora=index_vora,
            # El `t` es mesura des del vèrtex 0, com fa `tram_entre_punts`: és l'única
            # manera que un natural i un tram declarat parlin del mateix lloc.
            t_inici=cum[ini] / total,
            t_fi=cum[fi] / total,
            tipus_vora=boundary.role,
            index_inici=ini,
            index_fi=fi,
            longitud_mm=llarg,
            girs_fusionats=girs,
            piquets=piquets_del_tram(piece, boundary, ini, fi),
        )

    if not cantonades:
        # Cap cantonada: la vora sencera és un sol tram natural.
        fi = 0 if boundary.closed else n - 1
        un = _fes(0, fi) if boundary.closed else _fes(0, n - 1)
        return [un] if un else []

    if len(cantonades) == 1 and boundary.closed:
        # Una sola cantonada en una vora tancada: el tram va d'ella a ella, donant la volta.
        un = _fes(cantonades[0], cantonades[0])
        return [un] if un else []

    if boundary.closed:
        parells = list(zip(cantonades, cantonades[1:] + [cantonades[0]]))
    else:
        parells = list(zip(cantonades, cantonades[1:]))

    out = []
    for ini, fi in parells:
        seg = _fes(ini, fi)
        if seg is not None:
            out.append(seg)
    return out


def segmentar_peca_natural(
    piece: PieceData,
    llindar_graus: float = LLINDAR_CANTONADA_GRAUS,
    talls_extra: tuple[int, ...] = (),
) -> list[NaturalSegmentData]:
    """Els trams naturals d'una peça, sobre la mateixa vora base que els AUTO.

    Es deriven de la línia de COSIT si n'hi ha i, si no, de la de TALL — la mateixa tria que
    `segmentar_peca`, i a propòsit: si els naturals sortissin d'una vora i els AUTO d'una
    altra, no serien la mateixa lectura de la mateixa costura.
    """
    vora_base, index_base = None, 0
    for i, b in enumerate(piece.boundaries):
        if b.role is LayerRole.SEW:
            vora_base, index_base = b, i
            break
    if vora_base is None:
        for i, b in enumerate(piece.boundaries):
            if b.role is LayerRole.CUT:
                vora_base, index_base = b, i
                break
    if vora_base is None:
        return []
    return segmentar_vora_natural(piece, vora_base, index_base, llindar_graus, talls_extra)
