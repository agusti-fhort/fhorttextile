"""FTT pattern geometry → the shared descriptor space.

The corpus side of the bank was computed from GarmentCode specification JSON. This is the
other side: a `PatternPiece` as it came out of a DXF, projected into the same space by the
same function (`descriptor.features_from_outline`).

Three conversions happen here and each one is a way to be silently wrong:

1. **mm → cm.** FTT stores millimetres (`aama_reader` normalises everything through
   `factor_to_mm`); the corpus is centimetres. Channels 0-1 are absolute scale, so this is
   not a cosmetic difference — get it wrong and every neighbour is wrong.
2. **Which boundary.** A DXF piece carries several: the CUT line, the SEW line, internal
   marks. The corpus panel is a NET shape (GarmentCode panels have no seam allowance,
   `INFORME_GIMNAS` §6.3). So the comparable boundary is the **sewing line where the CAD
   drew one, and the cut line otherwise** — and which one was used travels in the evidence,
   because a piece measured on its cut line sits a centimetre outwards from its twin
   measured on the sew line, and channel 0 will say so.
3. **Which way round.** `canonical_frame` forces counter-clockwise, which is what makes
   CALLIE (the only clockwise material in the house) comparable with everything else at
   all. Nothing here should ever "fix" the winding beforehand.
"""
from __future__ import annotations

import numpy as np

from .descriptor import MM_PER_CM, features_from_outline

#: Boundary roles, as `PatternPiece.contorns[i]['role']` writes them (`LayerRole`).
ROLE_CUT = 'cut'
ROLE_SEW = 'sew'


class NoGeometry(Exception):
    """The piece has no usable closed outline. Not an error: a silence."""


def _points_of_boundary(piece, index: int) -> np.ndarray:
    """The vertices of one boundary, in file order, as an (M,2) array in mm."""
    pts = [
        (p.x, p.y) for p in sorted(
            (q for q in piece.points.all()
             if q.mena == 'vertex' and q.boundary_index == index),
            key=lambda q: q.ordre)
    ]
    return np.asarray(pts, dtype=float)


def outline_cm(piece, prefer_sew: bool = True):
    """The piece outline in CENTIMETRES, plus which boundary it came from.

    → `(points_cm, source)` where `source` is `'sew'` or `'cut'`.

    Prefers the sewing line because the corpus panels are net shapes: comparing a cut
    line against a net shape adds the seam allowance to the absolute-scale channels of
    every FTT query, which biases the match towards larger corpus panels. Falls back to
    the cut line, which every piece has.
    """
    contorns = piece.contorns or []
    ordre = ([ROLE_SEW, ROLE_CUT] if prefer_sew else [ROLE_CUT, ROLE_SEW])
    for role in ordre:
        for c in contorns:
            if c.get('role') != role or not c.get('closed'):
                continue
            P = _points_of_boundary(piece, c.get('index'))
            # Three points is the floor for an area; below that there is no shape to
            # describe, and a descriptor computed on a degenerate polygon is noise that
            # looks like data.
            if len(P) >= 3:
                return P / MM_PER_CM, role
    raise NoGeometry(
        'piece {} has no closed cut or sew boundary with at least 3 points'.format(
            getattr(piece, 'pk', '?')))


def edge_counts(piece, boundary_index: int) -> tuple[int, int]:
    """`(n_edges, n_curved)` for the descriptor's channels 6 and 7.

    🚨 **These two channels are NOT comparable with the corpus and the recognizer masks
    them for corpus queries** — see `bank.CORPUS_MASKED_CHANNELS`. Measured, 2026-08-26:

    | | corpus (1,4 M panels) | FTT (the five 837 pieces) |
    |---|---|---|
    | edges per piece | median **5**, mean 6,68 | turn points **8-28** |

    A GarmentCode edge is a PARAMETRIC edge: one cubic Bezier can be an entire armhole.
    A DXF turn point is a CAD CORNER, and the same armhole arrives as one turn-to-turn
    span with a hundred vertices inside it. The two numbers count different things, and
    feeding them to the same channel would put a constant bias on every corpus query
    without anybody noticing.

    So the count returned here is the count of **turn-to-turn spans** — the pattern
    maker's corners, which is the honest FTT analogue — and it is used for the TENANT
    bank, where both sides are DXF and therefore comparable.
    """
    punts = [p for p in piece.points.all()
             if p.mena == 'vertex' and p.boundary_index == boundary_index]
    n_turn = sum(1 for p in punts if p.tipus == 'turn')
    n_curve = sum(1 for p in punts if p.tipus == 'curve')
    # A closed loop with T turn points has T spans between them. No turns at all (a pure
    # curve, e.g. a circular piece) is one single span, not zero.
    n_edges = max(n_turn, 1)
    # "Curved" here is the fraction of spans that contain any curve vertex. Without turn
    # points every span is curved by construction.
    return n_edges, (n_edges if n_turn == 0 else min(n_edges, max(n_curve, 0)))


def features_of_piece(piece, prefer_sew: bool = True) -> dict:
    """A `PatternPiece` → the same dict the corpus ingest produced for a panel.

    `mirror` follows the corpus convention exactly: lefts are mirrored onto the right so
    a left sleeve and a right sleeve land on the same point. FTT carries the side in
    `lateralitat` (`L`/`R`/empty) rather than in the name, which is the same information
    in a better place.
    """
    P, source = outline_cm(piece, prefer_sew=prefer_sew)
    idx = next(c['index'] for c in (piece.contorns or []) if c.get('role') == source)
    n_edges, n_curved = edge_counts(piece, idx)
    mirror = (getattr(piece, 'lateralitat', '') == 'L')
    feats = features_from_outline(P, n_edges, n_curved, mirror=mirror)
    feats['boundary_source'] = source
    feats['n_edges'] = n_edges
    feats['n_curved'] = n_curved
    return feats
