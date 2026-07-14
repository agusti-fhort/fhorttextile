"""De la geometria a la pinça proposada: el pont entre la BD i el detector.

Germà de `seam_proposals`, i amb la mateixa divisió de feina: l'`engine.dart_detection` és pur
—no sap què és un `PatternPoint`— i aquí és on el món real (files, FK, pinces ja declarades) es
tradueix a mesures i on el candidat torna a ser una cosa que la UI pot ensenyar i confirmar.

**Res del que hi ha aquí escriu.** I el que la UI confirma no és un endpoint nou: és el gest de
W4b (`SewRelationViewSet.pinca`), amb els tres punts que el candidat ja porta.
"""
from __future__ import annotations

from .adapters import DjangoGeometryStore
from .engine.dart_detection import LLINDAR_PINCA, clau_pinca, detectar
from .engine.geometry import PointKind
from .engine.seam_matching import piquets_de_la_vora
from .engine.segments import acumulats_vora, longitud_vora
from .engine.sew import solapament_t
from .models import (
    DartProposalRejection, PatternFile, PatternPoint, PatternSegment, SewRelation,
)

#: Una V que una pinça declarada ja ocupa (en rang `t`) per sobre d'aquesta fracció no es torna a
#: proposar. Com a A2: no és zero perquè dos trams veïns es toquen per un extrem.
SOLAPAMENT_MAX_REL = 0.10


def _pinces_declarades(model_id: int) -> dict[tuple[int, int], list[tuple[float, float]]]:
    """(peça, vora) → els rangs `t` que les pinces JA declarades ocupen.

    **Només les pinces**, no totes les costures: una costura lateral que passi pel damunt d'una V
    no vol dir que la V ja s'hagi decidit —al TATE, la lateral declarada CONTÉ la pinça i és
    justament per això que no casa fins que la pinça es marca (W4b). Excloure les V que una
    costura trepitja amagaria l'única pinça del fitxer.
    """
    from .annotation_views import es_pinca_de_vora

    ocupats: dict[tuple[int, int], list[tuple[float, float]]] = {}
    relacions = (SewRelation.objects
                 .filter(model_id=model_id, tipus=SewRelation.TIPUS_PINCA)
                 .prefetch_related('segments_a__piece', 'segments_b__piece'))
    for rel in relacions:
        if not es_pinca_de_vora(rel):
            continue
        for seg in list(rel.segments_a.all()) + list(rel.segments_b.all()):
            ocupats.setdefault((seg.piece_id, seg.vora), []).append((seg.t_inici, seg.t_fi))
    return ocupats


def _ja_declarada(
    piece_id: int, vora: int, t_a: float, t_b: float,
    ocupats: dict[tuple[int, int], list[tuple[float, float]]],
) -> bool:
    rangs = ocupats.get((piece_id, vora), [])
    if not rangs:
        return False
    propi = solapament_t(t_a, t_b, t_a, t_b)
    if propi <= 0:
        return False
    reclamat = max(solapament_t(t_a, t_b, i, f) for i, f in rangs)
    return (reclamat / propi) > SOLAPAMENT_MAX_REL


def rebuigs_del_model(model_id: int) -> frozenset[tuple[int, int, int]]:
    """Les pinces que ja s'han rebutjat, en clau canònica (ids de PatternPoint)."""
    return frozenset(
        clau_pinca(a, v, b) for a, v, b in
        DartProposalRejection.objects.filter(model_id=model_id)
        .values_list('punt_a_id', 'punt_vertex_id', 'punt_b_id')
    )


def candidats_del_patro(fp: PatternFile) -> dict:
    """Les pinces que el motor veu a totes les peces d'un patró.

    Els tres punts de cada candidat s'entreguen com a **ids de `PatternPoint`**, no com a índexs:
    el gest de W4b es fa amb punts, i el que es proposa ha de ser exactament el que després es
    confirma. Traduir índexs a ids a la UI seria demanar-li que sabés com el motor numera la vora.
    """
    store = DjangoGeometryStore()
    doc = store.load_from(fp)
    ocupats = _pinces_declarades(fp.model_id)
    exclosos = rebuigs_del_model(fp.model_id)

    candidats: list[dict] = []
    descartats = {'ja_declarades': 0, 'rebutjades': 0}
    peces_mirades = 0

    for piece_row in fp.pieces.all():
        piece = doc.piece(piece_row.nom_block)
        if piece is None:
            continue

        segments = list(piece_row.segments.filter(origen=PatternSegment.ORIGEN_AUTO))
        if not segments:
            continue
        vora_idx = segments[0].vora
        if vora_idx >= len(piece.boundaries):
            continue
        boundary = piece.boundaries[vora_idx]
        llarg = longitud_vora(boundary)
        if llarg <= 0:
            continue
        peces_mirades += 1

        pts = list(boundary.points)
        girs = [i for i, p in enumerate(pts) if p.kind is PointKind.TURN]
        acumulats, _ = acumulats_vora(boundary)
        piquets_t = piquets_de_la_vora(
            boundary.points, boundary.closed, piece.notches, llarg)

        # Els punts de la vora, per id: el candidat ha de sortir d'aquí amb els PUNTS del gest.
        punts_row = list(piece_row.points
                         .filter(mena=PatternPoint.MENA_VERTEX, boundary_index=vora_idx)
                         .order_by('ordre'))
        if len(punts_row) < len(pts):
            continue

        for c in detectar(
            pts, girs, llarg, piquets_t, acumulats,
            piece_id=piece_row.id, piece_nom=piece_row.nom_block, vora=vora_idx,
        ):
            t_a = acumulats[c.index_a] / llarg
            t_b = acumulats[c.index_b] / llarg
            if _ja_declarada(piece_row.id, vora_idx, t_a, t_b, ocupats):
                descartats['ja_declarades'] += 1
                continue

            punts = (punts_row[c.index_a].id, punts_row[c.index_vertex].id,
                     punts_row[c.index_b].id)
            if clau_pinca(*punts) in exclosos:
                descartats['rebutjades'] += 1
                continue

            candidats.append(_serialitzar(c, punts))

    candidats.sort(key=lambda c: -c['confianca'])
    return {
        'model': fp.model_id,
        'pattern_file': fp.id,
        'peces': peces_mirades,
        'candidats': candidats,
        'descartats': descartats,
        'llindar': LLINDAR_PINCA,
    }


def _serialitzar(c, punts: tuple[int, int, int]) -> dict:
    return {
        # La clau canònica: és el que el rebuig desa. Una pinça proposada no és cap fila, i no té
        # cap id — igual que una costura proposada (A2).
        'clau': list(clau_pinca(*punts)),
        'peca': c.piece_nom,
        'piece_id': c.piece_id,
        'vora': c.vora,
        # Els TRES PUNTS del gest de W4b. Confirmar és cridar `sew-relations/pinca/` amb aquests.
        'point_a': punts[0],
        'point_vertex': punts[1],
        'point_b': punts[2],
        'costat_a_cm': c.costat_a_cm,
        'costat_b_cm': c.costat_b_cm,
        # La tela que es menjarà: el número que després sortirà restat a la costura que la conté.
        'intake_cm': round(c.intake_cm, 2),
        'boca_cm': c.boca_cm,
        'profunditat_cm': c.profunditat_cm,
        'boca_rel': c.boca_rel,
        'ratio': c.ratio,
        'piquets_boca': c.piquets_boca,
        'confianca': c.confianca,
        'senyals': [
            {'mena': s.mena, 'punts': round(s.punts, 3), 'detall': s.detall, 'dades': s.dades}
            for s in c.senyals
        ],
    }
