"""Resolució d'una mesura sobre la geometria: quant fa, de debò, aquest POM.

El valor d'un POM ancorat **no s'escriu: es llegeix**. Aquí és on es llegeix.

Dos modes, i el segon existeix perquè el patronatge real el necessita:

  · `points`   — la mesura va d'un punt ancorat a un altre.
  · `landmark` — la mesura surt d'un punt DERIVAT: "1 cm sota el punt de sisa". El punt
                 no existeix a la geometria i no s'hi dibuixa; es calcula cada vegada
                 sobre la vora, de manera que si la sisa es mou, el punt derivat es mou
                 amb ella. Si es materialitzés com a vèrtex, seria una còpia que
                 envelliria.

I dos mètodes de mesurar, que no són intercanviables: la distància RECTA entre dos punts
(el que mesura una cinta estirada) i la longitud PER VORA (el que mesura una cinta que
resegueix la corba). Una sisa recta i una sisa resseguida es diferencien en centímetres.
`POMMaster` no diu quin toca —no té camp per dir-ho—, així que el mètode es desa a
`PatternPOM.metode` i per defecte és RECTA, dit i no assumit.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Optional

from .errors import PatternEngineError
from .geometry import BoundaryData, PieceData, PointData

MM_PER_CM = 10.0


class MeasureError(PatternEngineError):
    """La recepta no es pot resoldre sobre aquesta geometria."""


@dataclass(frozen=True)
class MeasureResult:
    valor_cm: float
    metode: str                       # 'recta' | 'vora'
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

    raise MeasureError(f"Mode de mesura desconegut: '{mode}'.")


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


def _punt(pid, punts_per_id) -> tuple[float, float]:
    if pid is None:
        raise MeasureError('La recepta de mesura no diu quins punts uneix.')
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
