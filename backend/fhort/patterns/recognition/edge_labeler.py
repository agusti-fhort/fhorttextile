"""A2 · THE GRAMMAR: naming the edges of a piece whose identity a human already fixed.

The catalogue that F3 built is not a glossary — it is a set of CONSTRAINTS, and this is the
module that spends them. `EdgeRole.zone` says where on the body an edge lives;
`needs_piece_role` says which edges cannot be read without knowing the piece;
`SeamPairTemplate` and `GarmentTypeItemEdgeProfile` say which edges a piece of this role is
even allowed to have. Together they cut a sixteen-edge cycle down from "any of 28 words"
to a handful, and the geometry picks between those.

**Nothing here confirms anything.** Same law as F4.1: the output is a proposal with its
evidence, the green belongs to a person, and the proposal is written to columns the
confirmed identity never shares.

── THE FOUR THINGS THAT DECIDE ──────────────────────────────────────────────────
1. **The frame** (`edge_frame`). Every rule below is about the GARMENT's vertical, and on
   this house's material that is never the sheet's. See that module: the finding is that
   60 of 60 pieces lie turned.
2. **The vocabulary** — what the catalogue permits this piece role to carry. A placket has
   no rows in either catalogue table, so a placket is silent on every edge, and that is the
   catalogue being honest rather than the labeller being weak.
3. **The geometry** — position along the garment, distance from the axis, curvature, and
   whether the edge runs along the body or across it. Measured in the frame, never raw.
4. **D-INV-8, which is a rule and not a vote** (`_apply_d_inv_8`). The shoulder is the ONE
   edge between the neckline and the armhole. Where geometry gives a slim margin, structure
   gives certainty, and the evidence says which of the two spoke.

── SILENCE IS PER EDGE, NOT PER PIECE (N4) ──────────────────────────────────────
A front whose hem, sides and armholes are obvious does not have to stay quiet because one
26 mm notch at the bottom of a placket slit has no name in the catalogue. Each edge carries
its own margin and each edge decides for itself.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .edge_frame import NoFrame, PieceFrame, frame_of_grain

#: The silence threshold for an EDGE. Deliberately the same shape of number as
#: `recognizer.SCORE_MIN` — a MARGIN, not a probability — and deliberately its own constant:
#: the two answer different questions over different populations, and one day the edge exam
#: will be big enough to move this one on its own evidence. Calibrated in FASE D.
EDGE_SCORE_MIN = 0.20

#: How much better the winning ORIENTATION must be before the piece is willing to say which
#: way up it stands. A grain line fixes the axis and not the sign (`edge_frame`); if the two
#: hypotheses score alike, the file genuinely does not answer and the whole piece is silent.
ORIENTATION_MIN = 0.05


def _ramp(x: float, lo: float, hi: float) -> float:
    """0 below `lo`, 1 above `hi`, straight line between. The only shape used below."""
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


@dataclass(frozen=True)
class PieceContext:
    """What a rule needs to know about the piece the edge belongs to."""

    piece_role: str
    face: str
    #: Extent of the piece along the garment vertical, in mm. Never zero.
    u_span: float
    #: Half-width: the largest distance any point reaches from the grain axis, in mm.
    v_half: float
    #: Does the outline cross the axis? A front cut in one flat piece does; a half-front
    #: cut on the fold does not, and its "centre" is an edge rather than an interior line.
    spans_axis: bool
    perimeter: float
    #: The longest edge of this cycle, in mm. A collar's attach edge is not "long", it is
    #: **the longer of the two**, and that is a fact about the piece, not about the edge.
    max_edge_mm: float = 0.0


@dataclass(frozen=True)
class EdgeFeature:
    """One edge of the cycle, measured in the piece frame. All ratios, no millimetres.

    Ratios and not lengths because a rule that fires at "300 mm from the top" would say
    something different about a child's bodice and a coat. Every field below is normalised
    against the piece's own extent, which is the only scale the piece itself provides.
    """

    index: int
    segment_id: int | None
    length_mm: float
    #: Mid-height along the garment: 0 at the lowest point of the piece, 1 at the highest.
    un_mid: float
    un_lo: float
    un_hi: float
    #: Mean and max distance from the grain axis, over the half-width. 0 = on the axis.
    vn_mid: float
    vn_max: float
    #: |Δu| / chord. 1 = the edge runs along the body, 0 = straight across it.
    along_u: float
    #: chord / arc length. 1 = straight, lower = curved.
    straightness: float
    #: Fraction of the piece's height this edge covers.
    un_span: float
    #: Fraction of the piece's WIDTH this edge covers. 🚨 This is what separates an edge
    #: that crosses the body from a 17 mm step in the middle of a side seam: both run
    #: across, and only one of them is as wide as the garment. Measured, after the first
    #: exam run called four such steps a hem.
    vn_span: float
    #: Does this edge itself cross the axis (a back neckline does, a side seam does not).
    crosses_axis: bool

    @property
    def across_u(self) -> float:
        return 1.0 - self.along_u


# ═════════════════════════════════════════════════════════════════════════════
# The rules. One function per edge role, returning a score in [0,1] — or None,
# which means IMPOSSIBLE and is not the same as zero: an impossible role is not
# a rival, so it does not eat into anybody's margin.
# ═════════════════════════════════════════════════════════════════════════════

def _hem(f: EdgeFeature, p: PieceContext):
    """The finished bottom: across the body, at the lowest end of it, and AS WIDE AS IT.

    The width term is not decoration. Without it the first exam run called four 17 mm steps
    in the middle of a side seam a hem: they are low, they run across, and nothing else in
    the rule disagreed. A hem closes the garment, so it spans the garment.
    """
    if f.un_mid > 0.5:
        return None
    return (1.0 - f.un_mid) * f.across_u * _ramp(f.vn_span, 0.15, 0.5)


def _neckline(f: EdgeFeature, p: PieceContext):
    """The opening at the top, near the axis and running across the body.

    Near the axis AND across: the shoulder is also at the top, and the placket slit is also
    near the axis. What only the neckline is, is both at once.
    """
    if f.un_mid < 0.55:
        return None
    # `across_u` MODULATES and no longer dominates: a boat neck runs across the body and a
    # deep V runs down it, and both are necklines. Weighting it 1,0 silenced the 837's own
    # front neckline at a margin of 0,153 — measured, then softened to 0,4 + 0,6·across.
    # The width floor is what keeps the 26 mm notch at the foot of a placket slit from
    # taking the word: it sits on the axis, at the top, and is no part of any opening.
    return (_ramp(f.un_mid, 0.55, 0.85) * (1.0 - f.vn_mid)
            * (0.4 + 0.6 * f.across_u) * _ramp(f.vn_span, 0.03, 0.15))


def _shoulder_seam(f: EdgeFeature, p: PieceContext):
    """The very top, off the axis, short. Geometry proposes it weakly on purpose.

    The shoulder is the edge D-INV-8 knows how to find with certainty, and letting geometry
    shout here would only mean overruling structure with a worse instrument.
    """
    if f.un_mid < 0.7:
        return None
    return _ramp(f.un_mid, 0.7, 0.95) * _ramp(f.vn_mid, 0.15, 0.5) * f.across_u


def _armhole(f: EdgeFeature, p: PieceContext):
    """Upper, lateral, and CURVED — the curve is what separates it from the side seam.

    An armhole that came out straight is not an armhole; a side seam that came out curved is
    a badly drawn side seam. The two live at the same distance from the axis and the shape
    is the honest discriminator between them.
    """
    if f.un_mid < 0.6:
        return None
    return (_ramp(f.un_mid, 0.6, 0.85) * _ramp(f.vn_mid, 0.2, 0.5)
            * _ramp(1.0 - f.straightness, 0.02, 0.08))


def _side_seam(f: EdgeFeature, p: PieceContext):
    """Away from the axis, along the body, straight, and NOT at the very top."""
    return (_ramp(f.vn_mid, 0.35, 0.7) * f.along_u
            * _ramp(f.straightness, 0.95, 0.99) * (1.0 - _ramp(f.un_mid, 0.85, 1.0)))


def _centre(f: EdgeFeature, p: PieceContext):
    """Centre front / centre back: ON the axis, along the body, and LONG.

    The span is what keeps this apart from a placket slit, which sits on the axis and runs
    along the body too but covers a fifth of the piece instead of most of it.
    """
    if f.vn_max > 0.25:
        return None
    return _ramp(f.un_span, 0.35, 0.7) * f.along_u * (1.0 - f.vn_mid)


def _slit_edge(f: EdgeFeature, p: PieceContext):
    """One side of an opening cut into the piece: on the axis, along the body, SHORT."""
    if f.vn_max > 0.25:
        return None
    return (1.0 - _ramp(f.un_span, 0.15, 0.45)) * f.along_u * (1.0 - f.vn_mid)


def _waistline(f: EdgeFeature, p: PieceContext):
    """Across the body at mid height — and, like the hem, as wide as the body."""
    return (f.across_u * (1.0 - min(1.0, abs(f.un_mid - 0.5) * 2.5))
            * _ramp(f.vn_span, 0.15, 0.5))


def _sleeve_cap(f: EdgeFeature, p: PieceContext):
    """A sleeve's top edge: across, at the top, and markedly curved."""
    if f.un_mid < 0.5:
        return None
    return (_ramp(f.un_mid, 0.5, 0.85) * f.across_u
            * _ramp(1.0 - f.straightness, 0.05, 0.2))


def _cuff_line(f: EdgeFeature, p: PieceContext):
    """A sleeve's bottom edge: across, at the bottom."""
    if f.un_mid > 0.5:
        return None
    return (1.0 - f.un_mid) * f.across_u


def _sleeve_underarm_seam(f: EdgeFeature, p: PieceContext):
    """The long sides of a sleeve: along the body, spanning most of it."""
    return f.along_u * _ramp(f.un_span, 0.4, 0.8)


def _collar_attach(f: EdgeFeature, p: PieceContext):
    """The collar edge that is sewn on: **the LONGER of the two** on a fall collar.

    Relative to the piece's own longest edge and not to the perimeter, because "long" is
    not a property an edge has on its own — with an absolute rule both edges of the 837's
    collar cleared it and the piece proposed `collar_attach` twice.
    """
    if p.max_edge_mm <= 0:
        return None
    return _ramp(f.length_mm / p.max_edge_mm, 0.9, 1.0)


def _collar_outer_edge(f: EdgeFeature, p: PieceContext):
    """The collar edge sewn to nothing: the one that is NOT the longest."""
    if p.max_edge_mm <= 0:
        return None
    return (1.0 - _ramp(f.length_mm / p.max_edge_mm, 0.9, 1.0)) * _ramp(
        f.length_mm / p.max_edge_mm, 0.5, 0.8)


def _dart_leg(f: EdgeFeature, p: PieceContext):
    """A dart arm. Only ever reached through a declared dart, never off a cut outline."""
    return None


#: The rule table. A role in the catalogue with no entry here is not proposed — it is
#: **recorded as unruled in the evidence** rather than scored zero, because "the grammar has
#: nothing to say about this word" and "the grammar looked and said no" are different facts
#: and only one of them is a reason to go and write a rule.
RULES = {
    'hem': _hem,
    'neckline': _neckline,
    'shoulder_seam': _shoulder_seam,
    'armhole': _armhole,
    'side_seam': _side_seam,
    'centre_front': _centre,
    'centre_back': _centre,
    'slit_edge': _slit_edge,
    'waistline': _waistline,
    'sleeve_cap': _sleeve_cap,
    'cuff_line': _cuff_line,
    'sleeve_underarm_seam': _sleeve_underarm_seam,
    'collar_attach': _collar_attach,
    'collar_outer_edge': _collar_outer_edge,
    'dart_leg': _dart_leg,
}


# ═════════════════════════════════════════════════════════════════════════════
# Measuring the cycle
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class RawEdge:
    """One edge as the caller hands it over: an id and its points in SHEET mm.

    Points and not a t-range, so the whole labeller can be exercised on a synthetic cycle
    typed into a test without a boundary, a piece or a database anywhere near it.
    """

    points: list[tuple[float, float]]
    segment_id: int | None = None


def _polyline_length(pts) -> float:
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def measure_cycle(edges: list[RawEdge], frame: PieceFrame, piece_role: str,
                  face: str = '') -> tuple[list[EdgeFeature], PieceContext]:
    """The cycle in sheet mm → its features in the frame, plus the piece's own context.

    The normalisation is against THIS piece and nothing else: `un` spans the piece's own
    height and `vn` its own half-width. A rule written in these units says the same thing
    about a size 34 and a size 52, which is the only way a rule about garments can be
    written once.
    """
    framed = [[frame.to_frame(x, y) for (x, y) in e.points] for e in edges]
    all_u = [u for e in framed for (u, _) in e]
    all_v = [v for e in framed for (_, v) in e]
    u_lo, u_hi = min(all_u), max(all_u)
    u_span = max(u_hi - u_lo, 1e-9)
    v_half = max(max(abs(v) for v in all_v), 1e-9)
    perimeter = max(sum(_polyline_length(e) for e in framed), 1e-9)

    feats = []
    for i, (raw, pts) in enumerate(zip(edges, framed)):
        us = [u for (u, _) in pts]
        vs = [v for (_, v) in pts]
        arc = max(_polyline_length(pts), 1e-9)
        (au, av), (bu, bv) = pts[0], pts[-1]
        chord = max(math.hypot(bu - au, bv - av), 1e-9)
        feats.append(EdgeFeature(
            index=i,
            segment_id=raw.segment_id,
            length_mm=arc,
            un_mid=((min(us) + max(us)) / 2 - u_lo) / u_span,
            un_lo=(min(us) - u_lo) / u_span,
            un_hi=(max(us) - u_lo) / u_span,
            vn_mid=sum(abs(v) for v in vs) / len(vs) / v_half,
            vn_max=max(abs(v) for v in vs) / v_half,
            along_u=min(1.0, abs(bu - au) / chord),
            straightness=min(1.0, chord / arc),
            un_span=(max(us) - min(us)) / u_span,
            vn_span=(max(vs) - min(vs)) / (2 * v_half),
            crosses_axis=(min(vs) < 0.0 < max(vs)),
        ))

    ctx = PieceContext(
        piece_role=piece_role, face=face, u_span=u_span, v_half=v_half,
        spans_axis=(min(all_v) < 0.0 < max(all_v)), perimeter=perimeter,
        max_edge_mm=max((f.length_mm for f in feats), default=0.0))
    return feats, ctx


# ═════════════════════════════════════════════════════════════════════════════
# Labelling one orientation
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class EdgeProposal:
    """What the labeller says about ONE edge. Silence is `edge_role is None`."""

    index: int
    segment_id: int | None
    edge_role: str | None
    score: float
    evidence: dict = field(default_factory=dict)


def _score_row(f: EdgeFeature, ctx: PieceContext, vocabulary) -> tuple[dict, list]:
    """Every permitted role scored against one edge. → (scores, unruled)."""
    scores, unruled = {}, []
    for slug in vocabulary:
        rule = RULES.get(slug)
        if rule is None:
            unruled.append(slug)
            continue
        s = rule(f, ctx)
        if s is not None:
            scores[slug] = round(float(s), 6)
    return scores, unruled


def _runs_of(labels: dict, slug: str, n: int) -> list[list[int]]:
    """The contiguous runs of one role around the cycle. Wrapping counts as contiguous."""
    hits = [i for i in range(n) if labels.get(i) == slug]
    if not hits:
        return []
    runs, current = [], [hits[0]]
    for a, b in zip(hits, hits[1:]):
        if b == a + 1:
            current.append(b)
        else:
            runs.append(current)
            current = [b]
    runs.append(current)
    # A run that wraps the seam of the list is one run, not two.
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == n - 1:
        runs[0] = runs[-1] + runs[0]
        runs.pop()
    return runs


def _apply_d_inv_8(labels: dict, n: int) -> dict:
    """🚨 D-INV-8 as a HARD RULE: the shoulder is the ONE edge between neck and armhole.

    Not a vote and not a tie-break. The rule is structural — the neckline and the armhole
    are cut at two disjoint corners of the same panel and there is exactly one edge between
    them, measured 2 371 of 2 371 (`LandmarkRole.hps.evidence`) — so where it applies it
    OVERRULES the geometry, and the evidence records that structure spoke and not shape.

    It fires only on the honest case: a neckline run and an armhole run with exactly one
    unlabelled-or-otherwise edge between them. Two edges in the gap means this piece is not
    the shape the rule describes, and the rule stands down rather than picking one.
    """
    forced = {}
    neck_runs = _runs_of(labels, 'neckline', n)
    arm_runs = _runs_of(labels, 'armhole', n)
    if not neck_runs or not arm_runs:
        return forced
    for nr in neck_runs:
        for ar in arm_runs:
            for a_end, n_start in ((ar[-1], nr[0]), (nr[-1], ar[0])):
                gap = [(a_end + k) % n for k in range(1, n)]
                cut = gap.index(n_start) if n_start in gap else -1
                if cut != 1:            # exactly one edge sits in between
                    continue
                middle = gap[0]
                if labels.get(middle) in ('neckline', 'armhole'):
                    continue
                forced[middle] = 'shoulder_seam'
    return forced


#: A fragment shorter than this share of the perimeter is a step in an edge, not an edge.
#: The 837 carries four of them — 17 mm jogs where the seam allowance changes — and every
#: one sits in the middle of a side seam it plainly belongs to.
BRIDGE_MAX_FRAC = 0.05


def _bridge_short_fragments(labels: dict, feats, ctx, n: int) -> dict:
    """A short fragment between two edges that AGREE inherits their role.

    Same family as `_apply_d_inv_8` and the same justification: where the shape of a
    17 mm step says nothing, the structure around it says everything. It is also the rule
    `pom.landmarks._extrems_de_rol` already lives by from the other side — sibling stretches
    of one role are treated as one edge, and the joints between them are interior points.

    Conservative on purpose: BOTH neighbours must carry the same role, and neither may be a
    bridge itself, so a chain of doubt cannot propagate a guess along the whole cycle.
    """
    if n < 3:
        return {}
    bridged = {}
    for f in feats:
        if labels.get(f.index) is not None:
            continue
        if f.length_mm / ctx.perimeter > BRIDGE_MAX_FRAC:
            continue
        before = labels.get((f.index - 1) % n)
        after = labels.get((f.index + 1) % n)
        if before is not None and before == after:
            bridged[f.index] = before
    return bridged


def _label_one_orientation(feats, ctx, vocabulary, threshold):
    """One frame sign → proposals + the total the orientations compete on."""
    n = len(feats)
    rows, unruled = {}, {}
    for f in feats:
        rows[f.index], unruled[f.index] = _score_row(f, ctx, vocabulary)

    # Provisional labels: the geometric winner, used only so the structural rule has a
    # neckline and an armhole to reason between. Nothing is committed at this point.
    provisional = {}
    for i, sc in rows.items():
        if sc:
            best = max(sc, key=sc.get)
            if sc[best] > 0:
                provisional[i] = best

    forced = _apply_d_inv_8(provisional, n)

    # The bridge reads the labels that would actually be PUBLISHED, not the provisional
    # winners: a fragment must not inherit a role from a neighbour that is itself unsure.
    published = {}
    for f in feats:
        sc = rows[f.index]
        ranked = sorted(sc.items(), key=lambda kv: -kv[1])
        if f.index in forced:
            published[f.index] = forced[f.index]
        elif ranked and ranked[0][1] > 0:
            m = ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0.0)
            if m >= threshold:
                published[f.index] = ranked[0][0]
    bridged = _bridge_short_fragments(published, feats, ctx, n)

    proposals, total = [], 0.0
    for f in feats:
        sc = rows[f.index]
        ranked = sorted(sc.items(), key=lambda kv: -kv[1])
        best, best_s = (ranked[0] if ranked else (None, 0.0))
        second_s = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = best_s - second_s

        if f.index in forced:
            role, score = forced[f.index], 1.0
            why = 'D-INV-8: the only edge between the neckline and the armhole'
        elif f.index in bridged:
            role, score = bridged[f.index], 1.0
            why = ('a {:.0f} mm fragment between two edges that both read «{}»'
                   .format(f.length_mm, bridged[f.index]))
        elif best is None or best_s <= 0.0:
            role, score = None, 0.0
            why = ('no rule in the grammar scores this edge above zero'
                   if ranked else 'the catalogue permits this piece no edge role with a rule')
        elif margin < threshold:
            role, score = None, margin
            why = ('the margin over «{}» is {:.3f}, under the silence threshold {:.2f}'
                   .format(ranked[1][0] if len(ranked) > 1 else '-', margin, threshold))
        else:
            role, score = best, margin
            why = 'geometry, in the piece frame'

        total += score if role else 0.0
        proposals.append(EdgeProposal(
            index=f.index, segment_id=f.segment_id, edge_role=role, score=round(score, 6),
            evidence={
                'why': why,
                'scores': dict(ranked[:4]),
                'margin': round(margin, 6),
                'unruled_roles': unruled[f.index],
                'geometry': {
                    'length_mm': round(f.length_mm, 1),
                    'un_mid': round(f.un_mid, 3), 'un_span': round(f.un_span, 3),
                    'vn_mid': round(f.vn_mid, 3), 'vn_max': round(f.vn_max, 3),
                    'along_u': round(f.along_u, 3),
                    'straightness': round(f.straightness, 3),
                    'crosses_axis': f.crosses_axis,
                },
            }))
    return proposals, total


def label_piece(edges: list[RawEdge], grain: dict | None, piece_role: str, face: str = '',
                vocabulary=(), threshold: float = EDGE_SCORE_MIN) -> dict:
    """THE ENTRY POINT. A cycle of edges + a grain line + a confirmed role → proposals.

    Pure: no database, no Django, no `PatternSegment`. `edge_service` is what turns rows
    into `RawEdge`s and proposals back into rows, and the split is what lets the exam, the
    tests and the synthetic cycles all drive the same code.

    **Both orientations are tried and the structure picks.** The grain fixes the axis, never
    the sign (`edge_frame`), so the labelling is run once each way and the better total
    wins. When the two totals are within `ORIENTATION_MIN` the piece stays wholly silent:
    a cycle that reads as well upside down has not been read.
    """
    if not edges:
        return {'proposals': [], 'silent_because': 'the piece has no edges', 'frame': None}
    vocabulary = tuple(vocabulary)
    if not vocabulary:
        return {'proposals': [EdgeProposal(i, e.segment_id, None, 0.0, {
                    'why': 'the catalogue gives the role «{}» no edge vocabulary at all'
                           .format(piece_role)})
                for i, e in enumerate(edges)],
                'silent_because': 'empty vocabulary for «{}»'.format(piece_role),
                'frame': None}
    try:
        base = frame_of_grain(grain)
    except NoFrame as e:
        return {'proposals': [EdgeProposal(i, ed.segment_id, None, 0.0,
                                           {'why': str(e)}) for i, ed in enumerate(edges)],
                'silent_because': str(e), 'frame': None}

    tried = []
    for frame in (base, base.flip()):
        feats, ctx = measure_cycle(edges, frame, piece_role, face)
        proposals, total = _label_one_orientation(feats, ctx, vocabulary, threshold)
        tried.append((total, frame, proposals))

    tried.sort(key=lambda t: -t[0])
    (best_total, best_frame, best_props), (rival_total, _, rival_props) = tried
    lead = best_total - rival_total

    # 🚨 The gate asks whether the reading DEPENDS on which way up the piece stands, not
    # whether the two totals differ. A collar is told apart by the length of its two edges
    # and reads identically either way up: there is no sign to be unsure about, and
    # silencing it for a zero lead would be answering a question nobody asked. Measured on
    # the 837, whose collar the first exam run silenced for exactly that reason.
    same_reading = ([p.edge_role for p in best_props] == [p.edge_role for p in rival_props])

    if lead < ORIENTATION_MIN and not same_reading:
        why = ('the piece reads as well upside down (totals {:.3f} vs {:.3f}): the grain '
               'line gives an axis and the file gives no sign for it'
               .format(best_total, rival_total))
        return {'proposals': [EdgeProposal(p.index, p.segment_id, None, 0.0,
                                           {**p.evidence, 'why': why}) for p in best_props],
                'silent_because': why, 'frame': None}

    orientation = {'flipped': best_frame.flipped, 'lead': round(lead, 6),
                   'totals': [round(t, 6) for t, _, _ in tried]}
    for p in best_props:
        p.evidence['orientation'] = orientation
    return {'proposals': best_props, 'silent_because': None, 'frame': best_frame,
            'orientation': orientation}
