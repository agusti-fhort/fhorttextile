"""Where edge proposals meet the database — and the one place that must never confirm.

Twin of `service.py`, and for the same reason: `edge_labeler` is pure so it can be argued
with, and everything that knows what a `PatternSegment` is lives here. The law it enforces
is the one F4.1 wrote and this sprint inherits — **the machine writes proposals, a person
writes the truth** — with one difference of shape worth naming.

🚨 `PatternSegment` has NO `proposed_edge_role` column, and F4.2 does not add one. F4.1
needed persisted proposals because a piece's proposal has to survive the page reload that
sits between a recogniser run and a human's decision. An edge proposal has no such gap: it
is computed for the screen that is asking, handed over with its evidence, and thrown away
if nobody accepts it. Persisting it would be a second, staler copy of a pure function of
geometry that is already in the file — and a migration this sprint does not need.

What DOES get written is `edge_role`, and only when a human says so, and only through
`confirm_edge_roles` below. `UPDATE_FIELDS` is the enforcement and the test asserts the
list, exactly as `service.UPDATE_FIELDS` does.
"""
from __future__ import annotations

import time

from django.db import transaction

from .edge_labeler import EDGE_SCORE_MIN, RawEdge, label_piece

#: 🚨 The ONLY column a human's confirmation may write on a segment. `nom`, `origen`,
#: `tipus_vora`, `t_inici` and `t_fi` are the pattern maker's and the engine's; naming an
#: edge is not permission to move it.
UPDATE_FIELDS = ['edge_role']

#: The origins that carry a labellable cycle, best first. NATURAL is the granularity a
#: person recognises as one seam (`engine.natural_segments`); AUTO is the same outline cut
#: at every CAD corner, which fragments a single neckline into five. DECLARED segments are
#: excluded on purpose: they are the pattern maker's own arbitrary spans and they do not
#: form a cycle.
CYCLE_ORIGINS = ('natural', 'auto')


class NoCycle(Exception):
    """The piece carries no cycle of derived segments. A silence, not a failure."""


def confirmed_role_of(piece):
    """The piece's CONFIRMED role slug, or None. A proposal is not an identity.

    `rol_origen` is what separates the two: a role with no human origin came from the
    machine, and labelling its edges would be building a second storey on an unsigned
    first one.
    """
    from fhort.patterns.models import PatternPiece

    human = (PatternPiece.ROL_ORIGEN_ASSIGNAT, PatternPiece.ROL_ORIGEN_CONFIRMAT,
             PatternPiece.ROL_ORIGEN_CORREGIT)
    if piece.piece_role_id is None or piece.rol_origen not in human:
        return None
    return piece.piece_role.slug


def edge_vocabulary(piece_role: str, face: str = '', garment_type_item_id=None) -> list:
    """Which edge roles the CATALOGUE lets a piece of this role carry. Ordered, stable.

    Two sources, answering different questions. `SeamPairTemplate` says what this piece is
    sewn to somebody with — the seams. `GarmentTypeItemEdgeProfile` says what a garment of
    this type is expected to have, which is where the FINISHED edges live: the ones sewn to
    nothing, which therefore appear in no pair at all.

    🚨 **This function IS the `needs_piece_role` guard** (D3). Every slug it returns was
    read out of a catalogue row that already names the piece role, so a role impossible for
    this piece cannot reach the labeller in order to be proposed. That is a stronger
    guarantee than checking afterwards, and the tests prove the two agree.
    """
    from fhort.pom.models import GarmentTypeItemEdgeProfile, SeamPairTemplate

    slugs = {}

    def add(slug, order):
        if slug and slug not in slugs:
            slugs[slug] = order

    for slug, order in SeamPairTemplate.objects.filter(
            piece_role_a_slug=piece_role).values_list('edge_role_a_slug', 'display_order'):
        add(slug, order)
    for slug, order in SeamPairTemplate.objects.filter(
            piece_role_b_slug=piece_role).values_list('edge_role_b_slug', 'display_order'):
        add(slug, order)

    profiles = GarmentTypeItemEdgeProfile.objects.filter(piece_role_slug=piece_role)
    if garment_type_item_id is not None:
        profiles = profiles.filter(garment_type_item_id=garment_type_item_id)
    # No GTI on the model: every profile row for this piece role is the honest fallback.
    # A hem is a hem whichever garment type it closes, and dropping the finished edges
    # because the model has no type would silence the edge easiest to be sure about.
    for slug, order in profiles.values_list('edge_role_slug', 'display_order'):
        add(slug, order)

    return [s for s, _ in sorted(slugs.items(), key=lambda kv: (kv[1], kv[0]))]


def _points_of(boundary_points, seg) -> list:
    """The vertices a segment covers, walking the boundary forward from start to end.

    Forward and wrapping, because a closed boundary's last segment runs through the origin
    (`PatternSegment.t_fi < t_inici` is documented as exactly that case) and a slice would
    silently return the whole rest of the outline instead.
    """
    n = len(boundary_points)
    if n < 2:
        return []
    i = _index_at(boundary_points, seg.t_inici)
    j = _index_at(boundary_points, seg.t_fi)
    if i is None or j is None:
        return []
    out, k = [boundary_points[i]], i
    guard = 0
    while k != j and guard <= n:
        k = (k + 1) % n
        out.append(boundary_points[k])
        guard += 1
    return out


def _index_at(points, t: float, tol: float = 1e-6):
    """The vertex sitting at parameter `t`, or the nearest one. Never invents a point.

    A derived segment's `t` IS a cumulative length over the total, so it lands on a vertex
    exactly; the nearest-vertex fallback exists for segments whose boundary was rewritten
    under them, and it moves the edge by at most one vertex rather than dropping it.
    """
    n = len(points)
    cum, total = [0.0], 0.0
    for a, b in zip(points, points[1:] + points[:1]):
        total += ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        cum.append(total)
    if total <= 0:
        return None
    for i in range(n):
        if abs(cum[i] / total - t) <= tol:
            return i
    return min(range(n), key=lambda i: abs(cum[i] / total - t))


def edges_of_piece(piece) -> tuple:
    """A piece's derived cycle → `[RawEdge]` in cycle order, plus the origin used.

    Raises `NoCycle` when there is nothing derived to label: a piece imported before S6, or
    one whose only segments are the pattern maker's declared spans.
    """
    from fhort.patterns.models import PatternSegment

    for origin in CYCLE_ORIGINS:
        segs = list(PatternSegment.objects.filter(piece=piece, origen=origin)
                    .order_by('vora', 't_inici'))
        # Two edges ARE a cycle: a collar has exactly two, and requiring three sent the
        # 837's collar down to the `auto` fragments, where nine CAD corners stood in for
        # the two edges a person sees.
        if len(segs) < 2:
            continue
        # One cycle, not several: the outline the segments were derived from is a single
        # boundary, and mixing two of them would make a cycle that is not one.
        vora = segs[0].vora
        segs = [s for s in segs if s.vora == vora]
        pts = [(p.x, p.y) for p in sorted(
            (q for q in piece.points.all()
             if q.mena == 'vertex' and q.boundary_index == vora), key=lambda q: q.ordre)]
        if len(pts) < 3:
            continue
        edges = []
        for s in segs:
            sp = _points_of(pts, s)
            if len(sp) >= 2:
                edges.append(RawEdge(points=sp, segment_id=s.pk))
        if len(edges) >= 2:
            return edges, origin
    raise NoCycle('the piece has no derived cycle of segments to label')


def propose_edge_roles(piece, threshold: float = EDGE_SCORE_MIN) -> dict:
    """Run the grammar over one piece. → `{piece, piece_role, origin, proposals[…]}`.

    Read-only from beginning to end. This is what the screen calls; nothing it returns is
    in the database and nothing it does puts it there.
    """
    t0 = time.perf_counter()
    role = confirmed_role_of(piece)
    if role is None:
        return {'piece': piece.pk, 'piece_role': None, 'proposals': [],
                'silent_because': 'the piece has no human-confirmed role, and edges are '
                                  'only named under a signed identity',
                'ms': 0.0}
    try:
        edges, origin = edges_of_piece(piece)
    except NoCycle as e:
        return {'piece': piece.pk, 'piece_role': role, 'proposals': [],
                'silent_because': str(e), 'ms': 0.0}

    gti_id = getattr(getattr(piece.pattern_file, 'model', None), 'garment_type_item_id', None)
    vocab = edge_vocabulary(role, piece.face, gti_id)
    out = label_piece(edges, piece.grain, role, piece.face, vocab, threshold)

    return {
        'piece': piece.pk, 'piece_role': role, 'face': piece.face, 'origin': origin,
        'vocabulary': vocab, 'garment_type_item': gti_id,
        'silent_because': out.get('silent_because'),
        'orientation': out.get('orientation'),
        'proposals': [
            {'index': p.index, 'segment_id': p.segment_id, 'edge_role': p.edge_role,
             'score': p.score, 'evidence': p.evidence}
            for p in out['proposals']],
        'ms': round((time.perf_counter() - t0) * 1000, 1),
    }


class EdgeConfirmationRejected(ValueError):
    """A confirmation that cannot be applied. A 400 with a reason, never a crash."""


def confirm_edge_roles(*, piece, rows) -> list:
    """A HUMAN naming edges. `rows` = `[{segment_id, edge_role_slug|None}]`. → touched.

    In one gesture and not one call per edge, for the reason F4.1 gave about pieces: naming
    a cycle is a single act of reading, and twelve loose calls could fail at the ninth and
    leave half an outline named.

    🚨 Every slug is checked against `edge_vocabulary` before anything is written. That is
    D3 enforced at the door and not only in the proposer: the manual selector and the
    accepted proposal go through the same gate, so a role impossible for this piece cannot
    arrive by hand either.
    """
    from fhort.patterns.models import PatternSegment
    from fhort.pom.models import EdgeRole

    role = confirmed_role_of(piece)
    if role is None:
        raise EdgeConfirmationRejected(
            'the piece has no human-confirmed role: name the piece before its edges')

    gti_id = getattr(getattr(piece.pattern_file, 'model', None), 'garment_type_item_id', None)
    allowed = set(edge_vocabulary(role, piece.face, gti_id))
    segments = {s.pk: s for s in PatternSegment.objects.filter(piece=piece)}
    by_slug = {r.slug: r for r in EdgeRole.objects.all()}

    planned = []
    for row in rows:
        try:
            sid = int(row['segment_id'])
        except (KeyError, TypeError, ValueError):
            raise EdgeConfirmationRejected('every row needs a numeric `segment_id`')
        seg = segments.get(sid)
        if seg is None:
            raise EdgeConfirmationRejected(
                'segment {} does not belong to piece {}'.format(sid, piece.pk))
        slug = row.get('edge_role_slug') or None
        if slug is not None:
            if slug not in by_slug:
                raise EdgeConfirmationRejected('«{}» is not an edge role'.format(slug))
            if slug not in allowed:
                raise EdgeConfirmationRejected(
                    '«{}» is not possible on a piece whose role is «{}»: the catalogue '
                    'never pairs them'.format(slug, role))
        planned.append((seg, by_slug[slug] if slug else None))

    touched = []
    with transaction.atomic():
        for seg, edge_role in planned:
            if seg.edge_role_id == (edge_role.pk if edge_role else None):
                continue
            seg.edge_role = edge_role
            seg.save(update_fields=UPDATE_FIELDS)
            touched.append(seg)
    return touched
