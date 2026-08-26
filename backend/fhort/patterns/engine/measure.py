"""Resolució d'una mesura sobre la geometria: quant fa, de debò, aquest POM.

El valor d'un POM ancorat **no s'escriu: es llegeix**. Aquí és on es llegeix.

Tres modes, i cap dels dos últims és un caprici: el patronatge real els necessita.

  · `points`    — la mesura va d'un punt ancorat a un altre.
  · `landmark`  — la mesura surt d'un punt DERIVAT: "1 cm sota el punt de sisa". El punt
                  no existeix a la geometria i no s'hi dibuixa; es calcula cada vegada
                  sobre la vora, de manera que si la sisa es mou, el punt derivat es mou
                  amb ella. Si es materialitzés com a vèrtex, seria una còpia que
                  envelliria.
  · `ortogonal` — la CAIGUDA. Tres àncores: dues fan la línia de REFERÈNCIA i la tercera
                  és el punt que hi cau; el valor és la distància perpendicular del punt
                  a la línia. És el que demanen les mesures «des del nivell HPS» (escot
                  davant, caiguda d'espatlla, profunditat de sisa), que no són ni una
                  recta entre dos punts del patró ni una longitud per vora.
  · `projeccio` — la COTA D'EIX. Dues àncores i un eix (H o V): el valor és |Δ| de la
                  projecció sobre aquell eix. És el que un CAD dibuixa quan acota una
                  amplada o una alçada, i el que mesura una cinta estesa recta sobre la
                  taula.

I dos mètodes de mesurar, que no són intercanviables: la distància RECTA entre dos punts
(el que mesura una cinta estirada) i la longitud PER VORA (el que mesura una cinta que
resegueix la corba). Una sisa recta i una sisa resseguida es diferencien en centímetres.
`POMMaster` no diu quin toca —no té camp per dir-ho—, així que el mètode es desa a
`PatternPOM.metode` i per defecte és RECTA, dit i no assumit.

⚠️ **`ortogonal` i `projeccio` semblen contradir-se, i no.** La primera evita els eixos del
full i la segona hi viu. Són dues preguntes diferents sobre la mateixa geometria: «quant cau
respecte del NIVELL DE LA PEÇA» i «quant ocupa en amplada SOBRE LA TAULA». Qui tria és el
patronista, i el que no pot passar és que el motor decideixi per ell — per això són dos
mètodes i no un amb una bandera.

⚠️ **La caiguda ortogonal NO és ΔY.** Restar coordenades seria molt més curt i estaria
malament dues vegades: en una peça que al plànol seu girada, els eixos del full no són
els de la peça; i en un escot asimètric, els dos HPS no seuen a la mateixa alçada, o
sigui que no hi ha cap «nivell HPS» que un eix del full pugui representar. Qui ha de
posar la referència és la PEÇA —dues àncores seves—, i llavors el valor sobreviu a totes
dues coses perquè gira amb elles. El `metode` no hi juga cap paper: una perpendicular no
té variant recta ni variant per vora.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Optional

from .errors import PatternEngineError
from .geometry import BoundaryData, PieceData, PointData

MM_PER_CM = 10.0

#: Sota d'això, les dues àncores de referència són el mateix punt i la línia no té
#: direcció. Mateix valor que `grading_projection.TOL_DIRECCIO_MM`, que resol la mateixa
#: pregunta a l'altra punta del motor: dos punts separats per menys que això no orienten
#: res, i normalitzar-hi un vector dona un número sense sentit (o un NaN).
TOL_REFERENCIA_MM = 1e-6

#: Els eixos d'una cota de projecció. `''` és AUTO: el motor tria el de més recorregut.
EIX_AUTO = ''
EIX_H = 'H'
EIX_V = 'V'


class MeasureError(PatternEngineError):
    """La recepta no es pot resoldre sobre aquesta geometria."""


@dataclass(frozen=True)
class MeasureResult:
    valor_cm: float
    metode: str                       # 'recta' | 'vora' | 'ortogonal' | 'projeccio'
    punts: tuple[tuple[float, float], ...]   # els punts que la mesura toca, en mm
    derivat: bool = False             # ha calgut calcular algun punt que no existeix?


def resoldre(
    piece: PieceData,
    definicio: dict,
    punts_per_id: dict,
    metode: str = 'recta',
) -> MeasureResult:
    """Recepta + geometria → valor en cm.

    `punts_per_id` mapeja l'id de `PatternPoint` (la referència que la recepta desa) a la
    posició real. L'engine no sap què és un id de base de dades: l'hi donen fet.
    """
    mode = definicio.get('mode', 'points')

    if mode == 'points':
        a = _punt(definicio.get('a'), punts_per_id)
        b = _punt(definicio.get('b'), punts_per_id)
        return _mesura(piece, a, b, metode, derivat=False)

    if mode == 'landmark':
        base = _punt(definicio.get('landmark'), punts_per_id)
        a = _derivar(
            piece, base,
            offset_cm=float(definicio.get('offset_cm', 0.0)),
            direccio=definicio.get('direccio', 'down'),
        )
        b = _punt(definicio.get('b'), punts_per_id)
        return _mesura(piece, a, b, metode, derivat=True)

    if mode == 'ortogonal':
        return _ortogonal(
            _punt(definicio.get('ref_a'), punts_per_id, 'ref_a'),
            _punt(definicio.get('ref_b'), punts_per_id, 'ref_b'),
            _punt(definicio.get('p'), punts_per_id, 'p'),
        )

    if mode == 'projeccio':
        return _projeccio(
            _punt(definicio.get('a'), punts_per_id, 'a'),
            _punt(definicio.get('b'), punts_per_id, 'b'),
            definicio.get('eix', EIX_AUTO) or EIX_AUTO,
        )

    raise MeasureError(f"Mode de mesura desconegut: '{mode}'.")


def eix_dominant(a, b) -> str:
    """L'eix on aquests dos punts tenen més recorregut. El d'AUTO.

    Empat exacte → horitzontal. És arbitrari i està escrit a posta: una regla que ho
    resolgui sempre igual és preferible a una que depengui de com hagi arrodonit el CAD.
    Un empat de debò (una diagonal a 45° perfectes) no és cap cota real; qui la vulgui,
    que triï l'eix a mà, que és exactament per a això que la sub-opció existeix.
    """
    return EIX_H if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else EIX_V


def _projeccio(a, b, eix: str) -> MeasureResult:
    """|Δ| de la projecció d'a→b sobre l'eix horitzontal o el vertical.

    El SEGMENT que es torna no és a→b: és la cota, i una cota d'eix és paral·lela al seu
    eix. Es dibuixa a l'alçada (o a l'abscissa) MITJANA dels dos punts, que la deixa entre
    tots dos en lloc d'enganxada a un —la posició fina la mana després el desplaçament de
    presentació, que és l'únic que l'ha de manar.

    `derivat=True`: els dos extrems del segment són punts calculats. Un d'ells cau sobre
    una àncora només per casualitat, quan els dos punts ja compartien coordenada.
    """
    if eix not in (EIX_AUTO, EIX_H, EIX_V):
        raise MeasureError(
            f"Eix de projecció desconegut: '{eix}'. Ha de ser '{EIX_H}', '{EIX_V}' o buit "
            f"(automàtic)."
        )
    if eix == EIX_AUTO:
        eix = eix_dominant(a, b)

    if eix == EIX_H:
        mig_y = (a[1] + b[1]) / 2.0
        p0, p1 = (a[0], mig_y), (b[0], mig_y)
    else:
        mig_x = (a[0] + b[0]) / 2.0
        p0, p1 = (mig_x, a[1]), (mig_x, b[1])

    llarg = hypot(p1[0] - p0[0], p1[1] - p0[1])
    return MeasureResult(llarg / MM_PER_CM, 'projeccio', (p0, p1), derivat=True)


def _ortogonal(ref_a, ref_b, p) -> MeasureResult:
    """La distància PERPENDICULAR de `p` a la recta que passa per `ref_a` i `ref_b`.

    Es resol amb el producte vectorial 2D i no projectant sobre eixos, que és el que la
    fa immune al gir de la peça: |(b−a) × (p−a)| / |b−a| és l'àrea del paral·lelogram
    dividida per la base, i tant l'àrea com la base giren juntes.

    El PEU de la perpendicular és un punt derivat —no és a la geometria i no s'hi
    dibuixa—, exactament com el punt del mode `landmark`. Per això `derivat=True`.

    `punts` torna el segment (peu → p), i NOMÉS aquest: és la polilínia la longitud de la
    qual ÉS el valor, que és la invariant que compleixen també `recta` i `vora`. La línia
    de referència no hi entra perquè no forma part de la mesura; qui la vulgui dibuixar ja
    en té les dues àncores a la recepta.
    """
    vx, vy = ref_b[0] - ref_a[0], ref_b[1] - ref_a[1]
    base = hypot(vx, vy)
    if base <= TOL_REFERENCIA_MM:
        raise MeasureError(
            'Les dues àncores de referència són el mateix punt: no defineixen cap línia, '
            'i sense línia no hi ha perpendicular. Tria dos punts separats.'
        )

    wx, wy = p[0] - ref_a[0], p[1] - ref_a[1]
    # Producte vectorial 2D (l'àrea signada del paral·lelogram). El SIGNE diria de quin
    # costat de la línia cau el punt; una caiguda no en té, de costat, així que es descarta
    # aquí i no més amunt: qui llegeixi el valor no ha de saber que mai va existir.
    creuat = vx * wy - vy * wx
    distancia = abs(creuat) / base

    # El peu: `ref_a` + la projecció escalar de w sobre v. Pot caure FORA del segment
    # ref_a–ref_b, i és correcte que hi caigui: la referència és una RECTA (el nivell), no
    # un tram. L'escot d'una peça asimètrica cau sovint fora dels dos HPS.
    t = (wx * vx + wy * vy) / (base * base)
    peu = (ref_a[0] + t * vx, ref_a[1] + t * vy)

    return MeasureResult(distancia / MM_PER_CM, 'ortogonal', (peu, p), derivat=True)


def _mesura(piece, a, b, metode: str, derivat: bool) -> MeasureResult:
    if metode == 'vora':
        cami = _cami_per_vora(piece, a, b)
        if cami is None:
            raise MeasureError(
                'No hi ha cap vora que passi pels dos punts: la mesura per vora no es pot '
                'resseguir. Amb el mètode recte sí que es pot fer.'
            )
        llarg = _longitud_pts(cami)
        return MeasureResult(
            llarg / MM_PER_CM, 'vora',
            tuple((p.x, p.y) if isinstance(p, PointData) else (p[0], p[1]) for p in cami),
            derivat,
        )

    recta = hypot(b[0] - a[0], b[1] - a[1])
    return MeasureResult(recta / MM_PER_CM, 'recta', (a, b), derivat)


def _punt(pid, punts_per_id, nom: str = '') -> tuple[float, float]:
    if pid is None:
        # `nom` només el passa el mode ortogonal, que té TRES àncores amb papers
        # diferents: dir «falta un punt» no ajudaria a saber quin s'ha de tornar a clicar.
        raise MeasureError(
            f"La recepta de mesura no diu quina àncora és «{nom}»." if nom
            else 'La recepta de mesura no diu quins punts uneix.'
        )
    p = punts_per_id.get(pid)
    if p is None:
        raise MeasureError(
            f'El punt {pid} ja no és a la geometria. La recepta apunta a un punt que ha '
            f'desaparegut (una versió nova del patró?).'
        )
    return (p.x, p.y) if hasattr(p, 'x') else (p[0], p[1])


def _derivar(piece: PieceData, base, offset_cm: float, direccio: str) -> tuple[float, float]:
    """Un punt que no existeix: 'X cm sota/sobre/a la dreta/a l'esquerra' d'un altre.

    Es calcula, no es materialitza. El dia que el punt base es mogui, aquest el seguirà.
    """
    d = offset_cm * MM_PER_CM
    dx, dy = {
        'down': (0.0, -d),
        'up': (0.0, d),
        'left': (-d, 0.0),
        'right': (d, 0.0),
    }.get(direccio, (0.0, -d))
    return (base[0] + dx, base[1] + dy)


def _cami_per_vora(piece: PieceData, a, b) -> Optional[list]:
    """El tros de vora que va d'A a B, pel camí CURT.

    Si els dos punts són a la mateixa vora tancada hi ha dos camins possibles; es tria el
    curt, que és el que mesuraria qualsevol persona amb una cinta.
    """
    for boundary in piece.boundaries:
        ia = _index_de(boundary, a)
        ib = _index_de(boundary, b)
        if ia is None or ib is None:
            continue
        pts = list(boundary.points)
        n = len(pts)
        if boundary.closed:
            cami1 = _rang(pts, ia, ib)
            cami2 = _rang(pts, ib, ia)
            return cami1 if _longitud_pts(cami1) <= _longitud_pts(cami2) else list(reversed(cami2))
        i, j = (ia, ib) if ia <= ib else (ib, ia)
        return pts[i:j + 1]
    return None


def _rang(pts, ini, fi) -> list:
    n = len(pts)
    out = [pts[ini]]
    i = ini
    while i != fi:
        i = (i + 1) % n
        out.append(pts[i])
    return out


def _index_de(boundary: BoundaryData, punt, tol: float = 0.01) -> Optional[int]:
    for i, p in enumerate(boundary.points):
        if abs(p.x - punt[0]) <= tol and abs(p.y - punt[1]) <= tol:
            return i
    return None


def _longitud_pts(pts) -> float:
    total = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ax, ay = (a.x, a.y) if isinstance(a, PointData) else (a[0], a[1])
        bx, by = (b.x, b.y) if isinstance(b, PointData) else (b[0], b[1])
        total += hypot(bx - ax, by - ay)
    return total
