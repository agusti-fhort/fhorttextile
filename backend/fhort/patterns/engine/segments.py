"""Segmentació d'una vora: on comença i on acaba cada tram.

**De gir a gir.** Els punts de GIR són les cantonades que el patronista reconeix com a
fronteres —la sisa acaba on comença el costat, el costat acaba on comença la vora
inferior—, i entre dos girs hi ha una vora amb un nom i un sentit. Els punts de CORBA no
són frontera de res: flueixen per dins del tram, que és exactament el que la classificació
del CAD ja deia (i el que fa que el grading els mogui per reflow i no per regla).

Sense aquesta divisió, una costura s'hauria d'ancorar a un rang de vèrtexs, i el dia que
la geometria es mogués el rang ja no voldria dir el mateix. Amb ella, un tram continua
sent el mateix tram encara que els seus punts es moguin.

**I malgrat tot, la divisió gir→gir no és la veritat de la costura** (Taller de patró, W1).
El CAD marca les cantonades que li convenen; el patronista cus les que vol. Una costura
lateral pot acabar a mig tram derivat, i dos trams derivats poden ser una sola costura. Per
això `tram_entre_punts` resol un tram entre DOS PUNTS QUALSSEVOL de la mateixa vora: primer
es declara, després es cus.

Un tram declarat és una **REFERÈNCIA a la vora que ja hi és, mai geometria nova**: no
n'afegeix cap punt, no en mou cap. Només diu entre quins dos punts existents passa, i la
seva longitud és la de la vora entre ells.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from .errors import PatternEngineError
from .geometry import BoundaryData, LayerRole, PieceData, PointKind, SegmentRange


class SegmentError(PatternEngineError):
    """Un tram que no es pot resoldre sobre la vora que es demana."""


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


def acumulats_vora(boundary: BoundaryData) -> tuple[list[float], float]:
    """Longitud acumulada des del primer vèrtex fins a cadascun, i el total de la vora.

    És la taula que converteix un ÍNDEX de vèrtex en un paràmetre `t`: `t(i) = cum[i]/total`.
    En una vora tancada el total inclou l'aresta de tancament (l'últim punt cap al primer),
    perquè el recorregut hi dona la volta sencera.
    """
    pts = list(boundary.points)
    cum = [0.0]
    for i in range(len(pts) - 1):
        cum.append(cum[-1] + hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y))
    total = cum[-1]
    if boundary.closed and len(pts) >= 2:
        total += hypot(pts[0].x - pts[-1].x, pts[0].y - pts[-1].y)
    return cum, total


def fraccio_tram(t_inici: float, t_fi: float) -> float:
    """Quina fracció de la vora ocupa un tram.

    **`t_fi` < `t_inici` vol dir que el tram passa per l'origen de la vora** (només pot
    passar en una vora tancada: el punt on la polilínia tanca no és cap frontera natural, i
    una costura declarada el pot travessar tranquil·lament).

    Una resta pelada (`t_fi - t_inici`) donaria negatiu i, amb un `max(0, …)` al davant,
    donaria **zero**: el tram desapareixeria en silenci i la costura sortiria com si un
    costat no existís. Per això aquest càlcul viu en una funció i no repetit a mà.
    """
    if t_fi >= t_inici:
        return t_fi - t_inici
    return (1.0 - t_inici) + t_fi


def longitud_tram(boundary: BoundaryData, t_inici: float, t_fi: float) -> float:
    """Longitud (mm) d'un tram paramètric sobre una vora, donant la volta si cal."""
    return longitud_vora(boundary) * fraccio_tram(t_inici, t_fi)


def tram_entre_punts(
    boundary: BoundaryData,
    index_vora: int,
    index_a: int,
    index_b: int,
    arc_llarg: bool = False,
) -> SegmentData:
    """El tram de vora entre DOS PUNTS QUALSSEVOL: la primitiva del segment declarat.

    Els punts són vèrtexs que ja existeixen (índexs dins de `boundary.points`), i el tram
    els segueix **pel recorregut de la vora**, no en línia recta: una sisa entre dos punts
    fa la seva corba, i la seva longitud és la de la corba.

    **Dos punts d'una vora tancada defineixen DOS trams**, no un: l'arc que va de A a B i el
    que hi torna per l'altre costat. Cap dels dos és "el bo" en abstracte —depèn de quina
    costura estigui declarant el patronista—, així que:

      · per defecte es torna el **tram curt**, que és el que gairebé sempre es vol dir;
      · amb `arc_llarg=True` es torna l'altre, que és el que cal quan la costura fa la volta
        llarga (l'escot que passa per l'esquena, posem).

    En una vora OBERTA només hi ha un camí entre dos punts: demanar-hi l'arc llarg no és una
    preferència, és una contradicció, i es diu clar en comptes de tornar l'únic tram que hi
    ha fent veure que s'ha obeït.

    Si el tram curt travessa el punt on la polilínia tanca, es torna amb `t_fi < t_inici`
    (vegeu `fraccio_tram`). No es "corregeix" girant-lo: girar-lo canviaria de tram.
    """
    pts = boundary.points
    n = len(pts)
    if n < 2:
        raise SegmentError('La vora no té prou punts per definir cap tram.')
    if not (0 <= index_a < n) or not (0 <= index_b < n):
        raise SegmentError(
            f'Els punts del tram han de ser vèrtexs de la vora (0–{n - 1}): '
            f'han arribat {index_a} i {index_b}.')
    if index_a == index_b:
        raise SegmentError(
            'Els dos extrems del tram són el mateix punt: això no delimita cap tram.')

    cum, total = acumulats_vora(boundary)
    if total <= 0:
        raise SegmentError('La vora té longitud zero.')

    t_a = cum[index_a] / total
    t_b = cum[index_b] / total

    if not boundary.closed:
        if arc_llarg:
            raise SegmentError(
                'Una vora oberta només té un camí entre dos punts: no hi ha cap arc llarg '
                'per triar.')
        t_inici, t_fi = (t_a, t_b) if t_a <= t_b else (t_b, t_a)
        ini, fi = (index_a, index_b) if t_a <= t_b else (index_b, index_a)
        return SegmentData(
            vora=index_vora, t_inici=t_inici, t_fi=t_fi, tipus_vora=boundary.role,
            index_inici=ini, index_fi=fi,
            longitud_mm=(t_fi - t_inici) * total,
        )

    # Tancada: els dos arcs. L'endavant va de A a B seguint l'ordre dels vèrtexs (i pot
    # passar per l'origen); l'enrere és el complementari.
    fraccio_endavant = (t_b - t_a) % 1.0
    llarg_endavant = fraccio_endavant * total
    llarg_enrere = total - llarg_endavant

    # Empat exacte (els dos punts són antípodes): es tria l'endavant, per determinisme.
    endavant_es_curt = llarg_endavant <= llarg_enrere
    agafa_endavant = endavant_es_curt if not arc_llarg else not endavant_es_curt

    if agafa_endavant:
        return SegmentData(
            vora=index_vora, t_inici=t_a, t_fi=t_b, tipus_vora=boundary.role,
            index_inici=index_a, index_fi=index_b, longitud_mm=llarg_endavant,
        )
    return SegmentData(
        vora=index_vora, t_inici=t_b, t_fi=t_a, tipus_vora=boundary.role,
        index_inici=index_b, index_fi=index_a, longitud_mm=llarg_enrere,
    )


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
