"""Segmentació d'una vora: on comença i on acaba cada tram.

**De gir a gir.** Els punts de GIR són les cantonades que el patronista reconeix com a
fronteres —la sisa acaba on comença el costat, el costat acaba on comença la vora
inferior—, i entre dos girs hi ha una vora amb un nom i un sentit. Els punts de CORBA no
són frontera de res: flueixen per dins del tram, que és exactament el que la classificació
del CAD ja deia (i el que fa que el grading els mogui per reflow i no per regla).

Sense aquesta divisió, una costura s'hauria d'ancorar a un rang de vèrtexs, i el dia que
la geometria es mogués el rang ja no voldria dir el mateix. Amb ella, un tram continua
sent el mateix tram encara que els seus punts es moguin.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from .geometry import BoundaryData, LayerRole, PieceData, PointKind, SegmentRange


@dataclass(frozen=True)
class SegmentData:
    """Un tram derivat, amb el que cal per identificar-lo i per mesurar-lo."""
    vora: int                 # índex de la BoundaryData dins la peça
    t_inici: float            # 0.0–1.0 sobre la longitud de la vora
    t_fi: float
    tipus_vora: LayerRole
    #: Índexs dels punts del tram dins la vora (inclosos els dos girs dels extrems).
    index_inici: int
    index_fi: int
    longitud_mm: float


def longitud_poli(punts) -> float:
    """Longitud d'una polilínia (llista de punts amb .x/.y)."""
    total = 0.0
    for i in range(len(punts) - 1):
        total += hypot(punts[i + 1].x - punts[i].x, punts[i + 1].y - punts[i].y)
    return total


def longitud_vora(boundary: BoundaryData) -> float:
    """Longitud d'una vora (perímetre si és tancada)."""
    pts = list(boundary.points)
    if len(pts) < 2:
        return 0.0
    if boundary.closed:
        pts = pts + [pts[0]]
    return longitud_poli(pts)


def segmentar_vora(boundary: BoundaryData, index_vora: int) -> list[SegmentData]:
    """Talla una vora pels seus punts de gir.

    Casos que el material real obliga a tractar i que un algorisme ingenu erraria:

      · **Cap punt de gir** (una vora tota corba, com un cercle): el tram és la vora
        sencera. Retornar zero trams deixaria la vora fora de tot ancoratge.
      · **Un sol punt de gir** en una vora tancada: el tram va del gir a ell mateix,
        donant la volta. També és un tram.
      · Vora oberta: els extrems compten com a frontera encara que no siguin girs, o el
        primer i l'últim tros quedarien orfes.
    """
    pts = boundary.points
    n = len(pts)
    if n < 2:
        return []

    total = longitud_vora(boundary)
    if total <= 0:
        return []

    girs = [i for i, p in enumerate(pts) if p.kind is PointKind.TURN]

    if not girs:
        # Vora sense cap gir: un sol tram, la vora sencera.
        return [SegmentData(
            vora=index_vora, t_inici=0.0, t_fi=1.0, tipus_vora=boundary.role,
            index_inici=0, index_fi=n - 1 if not boundary.closed else 0,
            longitud_mm=total,
        )]

    if not boundary.closed:
        # En una vora oberta, els extrems són frontera encara que no siguin girs.
        fronteres = sorted(set(girs) | {0, n - 1})
        parells = list(zip(fronteres, fronteres[1:]))
    else:
        # Tancada: de cada gir al següent, i l'últim tanca contra el primer.
        fronteres = girs
        parells = list(zip(fronteres, fronteres[1:] + [fronteres[0]]))

    segments: list[SegmentData] = []
    acumulat = 0.0
    for ini, fi in parells:
        tram = _punts_del_tram(pts, ini, fi, boundary.closed)
        llarg = longitud_poli(tram)
        if llarg <= 0:
            continue
        segments.append(SegmentData(
            vora=index_vora,
            t_inici=acumulat / total,
            t_fi=(acumulat + llarg) / total,
            tipus_vora=boundary.role,
            index_inici=ini,
            index_fi=fi,
            longitud_mm=llarg,
        ))
        acumulat += llarg

    return segments


def segmentar_peca(piece: PieceData) -> list[SegmentData]:
    """Els trams d'una peça.

    Es deriven de la línia de COSIT si n'hi ha —és la que de debò es cus— i, si no n'hi
    ha, de la de TALL. L'AMELIA no porta capa 14, així que a la traçadora tots els trams
    surten del tall; el dia que arribi un fitxer amb cosit, sortiran d'allà sense tocar
    res.
    """
    vora_base = None
    index_base = 0
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
    return segmentar_vora(vora_base, index_base)


def _punts_del_tram(pts, ini: int, fi: int, closed: bool) -> list:
    """Els punts d'un tram, donant la volta si cal (vora tancada)."""
    n = len(pts)
    if ini == fi:
        # Un sol gir en una vora tancada: el tram és la volta sencera.
        return list(pts) + [pts[ini]]
    if ini < fi:
        return list(pts[ini:fi + 1])
    if not closed:
        return list(pts[fi:ini + 1])
    return list(pts[ini:]) + [pts[fi]] if fi == 0 else list(pts[ini:]) + list(pts[:fi + 1])


def segment_range(seg: SegmentData) -> SegmentRange:
    """SegmentData → el SegmentRange del model geomètric (contracte d'`engine/geometry`)."""
    return SegmentRange(
        boundary_index=seg.vora,
        t_inici=seg.t_inici,
        t_fi=seg.t_fi,
        tipus_vora=seg.tipus_vora,
    )
