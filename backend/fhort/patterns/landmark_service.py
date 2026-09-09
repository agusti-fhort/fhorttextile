"""FASE B · LANDMARKS, DERIVED AND NOT STORED. The end of blocker A11.

`INFORME_CORPUS_I_AUTOANCORATGE_2026-08-24` closed on a blocker: *no data in the system
identifies the HPS*. It is answered here, and the answer is that the HPS was never a datum.
It is **the endpoint the neckline and the shoulder seam share** — structural, measured
2 371 of 2 371 — and the moment a piece's edges carry their roles, the point is a
consequence of them rather than something anybody has to click.

**A DERIVED VIEW, NOT A TABLE** (the spirit of D-INV-6). No model, no migration, no column.
A landmark is a pure function of geometry that is already in the file and of edge roles a
person already confirmed; persisting it would create a second copy that goes stale the
first time either input moves, and the staleness would be invisible. Consumers ask for it
when they need it.

── THE TWO THINGS THIS MODULE ADDS TO THE PURE RESOLVER ─────────────────────────
`pom.landmarks` does the reasoning and knows nothing about a database. What it cannot know:

1. **THE FRAME.** Its `highest_y` sanity check reads `p[1]`, and on this house's material
   that is the sheet's y, which is not the garment's up (`recognition.edge_frame`: 60 of 60
   pieces lie turned). Fed raw sheet coordinates the verifier REJECTS the 837's true HPS —
   the one production's own POM F recipe anchors on. So the graph is handed over in
   **garment coordinates**, `(across, up)`, and `highest_y` then means what it says.

2. **THE TWO SIDES.** A front cut in one flat piece has TWO shoulders, two armholes and
   **two HPS**, and `_shared_endpoint` is right to refuse a graph where the neckline and
   the shoulder touch twice. So a piece that spans its own axis is resolved once per side,
   and the landmark comes back as a mirrored pair. That is not a special case to be
   tolerated: it is what the piece is.
"""
from __future__ import annotations

from fhort.pom.landmarks import LandmarkNoResolt, Tram, resol_landmark

from .recognition.edge_frame import NoFrame, frame_of_grain
from .recognition.edge_service import edges_of_piece, NoCycle

#: Which end of the garment an edge role belongs to. This is how the frame's SIGN gets
#: fixed here: the labeller competes two hypotheses because it has no roles yet, but by the
#: time landmarks are being derived a human has confirmed them, and confirmed roles are a
#: better witness than any score. A hem below a neckline is the garment standing up.
UP_ROLES = frozenset({'neckline', 'shoulder_seam', 'armhole', 'sleeve_cap',
                      'collar_attach', 'band_attach_upper'})
DOWN_ROLES = frozenset({'hem', 'cuff_line', 'band_attach_lower', 'waistline'})

#: Endpoints are matched by equality, so they are rounded to a common grid first. Adjacent
#: segments share a vertex exactly, and 1 µm is far below anything a pattern means while
#: being far above float noise from the frame rotation.
GRID = 6


def _key(uv) -> tuple:
    """A frame point as a hashable, comparable identity: `(across, up)`.

    🚨 The ORDER is the whole point. `pom.landmarks._y` reads index 1, and every rule that
    speaks of height — `highest_y`, `lowest_y` — means height ON THE GARMENT. Putting `up`
    second is what makes the pure module's vocabulary true here.
    """
    return (round(uv[1], GRID), round(uv[0], GRID))


def _orient(frame, edges_by_role):
    """Fix the frame's sign from the confirmed roles. → `(frame, how)`.

    Falls back to the frame as drawn, and says so, when the piece carries neither an upper
    nor a lower edge — a waistband, a facing. A recorded assumption is not the same thing as
    a silent one.
    """
    ups, downs = [], []
    for slug, pts in edges_by_role.items():
        target = ups if slug in UP_ROLES else (downs if slug in DOWN_ROLES else None)
        if target is not None:
            target.extend(frame.to_frame(x, y)[0] for (x, y) in pts)
    if not ups or not downs:
        return frame, 'as drawn: the piece carries no upper/lower pair to orient it'
    if sum(ups) / len(ups) >= sum(downs) / len(downs):
        return frame, 'confirmed roles: the upper edges sit above the lower ones'
    return frame.flip(), 'confirmed roles: flipped, the lower edges were on top'


def _graph(rows, frame):
    """Confirmed segments → `[Tram]` in garment coordinates, plus the way back to the sheet.

    A segment becomes ONE `Tram` from end to end. Its interior is not part of the graph:
    the resolver reasons about which edges meet where, and a curve's middle meets nothing.
    """
    trams, back = [], {}
    for slug, pts in rows:
        a, b = frame.to_frame(*pts[0]), frame.to_frame(*pts[-1])
        ka, kb = _key(a), _key(b)
        back[ka], back[kb] = pts[0], pts[-1]
        trams.append(Tram(edge_role=slug, p0=ka, p1=kb))
    return trams, back


def _sides(rows, frame):
    """Split the confirmed edges by side of the axis. → `[(label, rows)]`.

    A piece that never crosses its own axis has one side and one of each landmark. One that
    does has a mirrored pair, and resolving the whole cycle at once would hand
    `_shared_endpoint` two shared endpoints and earn the refusal it is designed to give.

    An edge that CROSSES the axis — a back neckline runs from one shoulder to the other —
    belongs to both sides whole. Cutting it at the axis would invent a vertex that is not
    in the file, and the resolver only ever asks about endpoints anyway.
    """
    framed = [(slug, [frame.to_frame(x, y) for (x, y) in pts]) for slug, pts in rows]
    vs = [v for _, pts in framed for (_, v) in pts]
    if not vs or not (min(vs) < 0.0 < max(vs)):
        return [('', rows)]
    left, right = [], []
    for (slug, pts), (_, fpts) in zip(rows, framed):
        side_vs = [v for (_, v) in fpts]
        if min(side_vs) <= 0.0:
            left.append((slug, pts))
        if max(side_vs) >= 0.0:
            right.append((slug, pts))
    return [('L', left), ('R', right)]


def derive_landmarks(piece, roles: dict | None = None) -> dict:
    """Every derivable landmark of one piece. → `{piece, landmarks[…], skipped[…]}`.

    `roles` overrides what the database says, as `{segment_id: edge_role_slug}`. It is what
    the FASE D exam and the tests drive: the derivation can then be measured against
    production's own anchors **without a single write**, which is the difference between
    proving the rule and adopting it.

    Read-only, and every failure is a REASON rather than an absence: a landmark that cannot
    be resolved appears in `skipped` with the resolver's own sentence. A point silently
    missing and a point that could not be worked out look identical to a caller, and only
    one of them is worth anybody's time.
    """
    from fhort.pom.models import LandmarkRole

    from .models import PatternSegment

    out = {'piece': piece.pk, 'landmarks': [], 'skipped': [], 'frame': None}
    try:
        base = frame_of_grain(piece.grain)
    except NoFrame as e:
        out['skipped'].append({'landmark': None, 'why': str(e)})
        return out

    try:
        edges, _origin = edges_of_piece(piece)
    except NoCycle as e:
        out['skipped'].append({'landmark': None, 'why': str(e)})
        return out

    confirmed = dict(roles) if roles is not None else {
        s.pk: s.edge_role.slug for s in
        PatternSegment.objects.filter(piece=piece, edge_role__isnull=False)
        .select_related('edge_role')}
    rows = [(confirmed[e.segment_id], e.points)
            for e in edges if e.segment_id in confirmed]
    if not rows:
        out['skipped'].append(
            {'landmark': None,
             'why': 'no edge of this piece carries a confirmed role yet'})
        return out

    by_role = {}
    for slug, pts in rows:
        by_role.setdefault(slug, []).extend([pts[0], pts[-1]])
    frame, how = _orient(base, by_role)
    out['frame'] = {'oriented_by': how, 'flipped': frame.flipped,
                    'roles_confirmed': sorted(by_role)}

    regles = [r for r in LandmarkRole.objects.filter(derivable=True)
              .order_by('display_order', 'slug')]

    for side_label, side_rows in _sides(rows, frame):
        trams, back = _graph(side_rows, frame)
        resolved = {}
        for regla in regles:
            try:
                punt = resol_landmark(regla, trams, resolved)
            except LandmarkNoResolt as e:
                out['skipped'].append(
                    {'landmark': regla.slug, 'side': side_label, 'why': str(e)})
                continue
            resolved[regla.slug] = punt
            sheet = back.get(punt)
            if sheet is None:
                # 🚨 B2: a point the resolver produced but the frame cannot map back is not
                # published. It would be a landmark at coordinates nobody can check.
                out['skipped'].append(
                    {'landmark': regla.slug, 'side': side_label,
                     'why': 'the resolved point is not a vertex of this piece'})
                continue
            out['landmarks'].append({
                'landmark': regla.slug, 'side': side_label,
                'x': round(sheet[0], 4), 'y': round(sheet[1], 4),
                'op': regla.derivation_op, 'tiebreak': regla.derivation_tiebreak,
                'input': regla.derivation_input,
            })
    return out
