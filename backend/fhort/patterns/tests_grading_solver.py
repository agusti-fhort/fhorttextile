"""Tests for the grading solver core (F6.1, phase D).

Everything here runs on **synthetic** geometry, on purpose. The 837 is the bank and it
lives in `ops/rosetta/exam_solver.py`; what a unit test has to pin down is the behaviour
the bank cannot show — a conflict that no real pattern contains, a gauge deliberately left
open, an answer that is known in closed form.

These are Python-only: nothing here touches the database, and the engine does not import
Django.
"""
import numpy as np
from django.test import SimpleTestCase

from fhort.patterns.engine.grading_solver import (
    Anchor, AttachedPoint, FixedPom, GrainDirection, NoReduction, PieceProblem, PomDelta,
    SolverError, Weights, diagnose, solve, solve_all,
)


def square(side: float = 100.0, per_edge: int = 4) -> PieceProblem:
    """A square with `per_edge` curve points along each side, CCW from the origin.

    Turn points are the four corners, so the piece has 8 unknowns — small enough that a
    test can reason about the answer and big enough that the similarity rebuild of the
    curve points actually runs.
    """
    corners = [(0.0, 0.0), (side, 0.0), (side, side), (0.0, side)]
    pts, kinds = [], []
    for k, c in enumerate(corners):
        nxt = corners[(k + 1) % 4]
        pts.append(c)
        kinds.append('turn')
        for s in range(1, per_edge + 1):
            f = s / (per_edge + 1)
            pts.append((c[0] + f * (nxt[0] - c[0]), c[1] + f * (nxt[1] - c[1])))
            kinds.append('curve')
    return PieceProblem(name='SQUARE', base_points=tuple(pts), kinds=tuple(kinds),
                        grain=(0.0, side / 2, side, side / 2))


def on_vertex(piece: PieceProblem, index: int) -> AttachedPoint:
    """An attached point sitting exactly on a loop vertex (t=0 of the edge it starts)."""
    return AttachedPoint(base=piece.base_points[index], edge=index, t=0.0)


class DeformationTests(SimpleTestCase):
    def test_zero_displacement_is_the_identity(self):
        piece = square()
        pts = piece.deform(np.zeros((4, 2)))
        self.assertTrue(np.allclose(pts, np.array(piece.base_points)))

    def test_curves_follow_their_segment_frame(self):
        """Moving one corner carries that corner's two edges, and nothing else.

        This is the FASE A model in miniature: the curve points of an untouched edge must
        not move at all, and those of a touched edge must land on the straight line between
        the new endpoints (the base edge was straight, and a similarity keeps it straight).
        """
        piece = square()
        d = np.zeros((4, 2))
        d[1] = (10.0, 0.0)                       # corner (100, 0) → (110, 0)
        pts = piece.deform(d)
        base = np.array(piece.base_points)

        # the edge from (100,100) to (0,100) touches neither moved corner
        untouched = [i for i, k in enumerate(piece.kinds)
                     if k == 'curve' and base[i][1] == 100.0]
        self.assertTrue(np.allclose(pts[untouched], base[untouched]))

        # the bottom edge now runs (0,0) → (110,0): still straight, still on y=0
        bottom = [i for i, k in enumerate(piece.kinds)
                  if k == 'curve' and base[i][1] == 0.0]
        self.assertTrue(np.allclose(pts[bottom][:, 1], 0.0))
        self.assertAlmostEqual(float(pts[bottom][:, 0].max()), 110.0 * 4 / 5, places=9)


class DiagnosisTests(SimpleTestCase):
    def test_open_gauge_is_reported_not_raised(self):
        """No anchor, no grain: three degrees of freedom, and the solver still answers."""
        piece = square()
        cons = [PomDelta('W', 'recta', (on_vertex(piece, 0), on_vertex(piece, 5)), 110.0)]
        d = diagnose(piece, cons)
        self.assertEqual(d.n_unknowns, 8)
        self.assertEqual(d.rank, 1)
        self.assertEqual(d.dof, 7)
        self.assertEqual(d.conflicting, ())

        report = solve(piece, cons)
        self.assertTrue(report.success)
        self.assertTrue(report.converged)
        self.assertIn('degrees of freedom left open', report.message)

    def test_gauge_closes_the_rigid_null_space(self):
        """Anchor (2) + grain (1) remove exactly the three rigid degrees of freedom."""
        piece = square()
        free = diagnose(piece, [])
        self.assertEqual(free.dof, 8)
        gauged = diagnose(piece, [Anchor('A0', 0), GrainDirection()])
        self.assertEqual(gauged.rank, 3)
        self.assertEqual(gauged.dof, 5)
        self.assertEqual(gauged.conflicting, ())
        self.assertEqual(gauged.redundant, ())

    def test_redundant_row_is_named_and_is_not_a_conflict(self):
        piece = square()
        cons = [Anchor('A0', 0), Anchor('A0-again', 0)]
        d = diagnose(piece, cons)
        self.assertEqual(d.rank, 2)
        self.assertEqual(set(d.redundant), {'A0-again.x', 'A0-again.y'})
        self.assertEqual(d.conflicting, ())
        self.assertTrue(d.well_posed)

    def test_injected_conflict_is_named(self):
        """Two targets for the same measurement. The diagnosis has to say WHICH row.

        A residual norm cannot tell this apart from «hard but solvable»; the point of
        running QR first is that it can.
        """
        piece = square()
        a, b = on_vertex(piece, 0), on_vertex(piece, 5)
        cons = [
            PomDelta('width=110', 'recta', (a, b), 110.0),
            PomDelta('width=130', 'recta', (a, b), 130.0),
        ]
        d = diagnose(piece, cons)
        self.assertEqual(d.conflicting, ('width=130',))
        self.assertEqual(d.redundant, ())
        self.assertFalse(d.well_posed)

    def test_components_are_reported(self):
        piece = square()
        d = diagnose(piece, [Anchor('A0', 0), GrainDirection()])
        # The smoothing stencil links the whole closed loop, so this is one component and
        # the report says so rather than pretending to a partition it does not have.
        self.assertEqual(len(d.components), 1)
        self.assertEqual(set(d.components[0]), {'A0', 'grain'})


class SolveTests(SimpleTestCase):
    def test_simple_pom_delta_is_exact(self):
        """A square told to be 10 mm wider ends up exactly 10 mm wider."""
        piece = square()
        left, right = on_vertex(piece, 0), on_vertex(piece, 5)
        cons = [
            PomDelta('width', 'recta', (left, right), 110.0),
            Anchor('origin', 0),
            GrainDirection(),
        ]
        report = solve(piece, cons)
        self.assertTrue(report.success)
        self.assertTrue(report.converged)
        self.assertLess(report.worst_residual_mm, 1e-9)

        measured = cons[0].measure(piece, report.points)
        self.assertAlmostEqual(measured, 110.0, places=9)
        # the anchored corner really did not move
        self.assertTrue(np.allclose(report.points[0], piece.base_points[0], atol=1e-12))

    def test_fixed_pom_moves_zero(self):
        """A FIXED measurement stays put while the piece around it grows.

        The case that means something is this one, not a piece that does not grade: the
        square is told to widen by 20 mm AND to keep its height, and the height has to come
        back unchanged to the last decimal.
        """
        piece = square()
        bottom_left, bottom_right = on_vertex(piece, 0), on_vertex(piece, 5)
        top_left = on_vertex(piece, 15)
        cons = [
            PomDelta('width', 'recta', (bottom_left, bottom_right), 120.0),
            FixedPom('height', 'recta', (bottom_left, top_left), 100.0),
            Anchor('origin', 0),
            GrainDirection(),
        ]
        report = solve(piece, cons)
        self.assertTrue(report.converged)
        self.assertAlmostEqual(cons[0].measure(piece, report.points), 120.0, places=9)
        self.assertAlmostEqual(cons[1].measure(piece, report.points), 100.0, places=9)
        self.assertLess(abs(report.residuals_mm['height']), 1e-9)

    def test_success_and_converged_are_distinguished(self):
        """A contradiction must come back as success=True, converged=False — with names.

        Reporting it as a failure would lose the field the solver did compute, and
        reporting it as a success would hide that the targets cannot all be met.
        """
        piece = square()
        a, b = on_vertex(piece, 0), on_vertex(piece, 5)
        cons = [
            PomDelta('width=110', 'recta', (a, b), 110.0),
            PomDelta('width=130', 'recta', (a, b), 130.0),
            Anchor('origin', 0),
            GrainDirection(),
        ]
        report = solve(piece, cons)
        self.assertTrue(report.success)
        self.assertFalse(report.converged)
        self.assertIn('width=130', report.message)
        self.assertGreater(report.worst_residual_mm, 1.0)

    def test_no_constraints_gives_the_zero_field(self):
        piece = square()
        report = solve(piece, [])
        self.assertTrue(report.success)
        self.assertTrue(report.converged)
        self.assertTrue(np.allclose(report.displacement, 0.0))

    def test_projection_method_uses_its_axis(self):
        piece = square()
        a = AttachedPoint(base=(0.0, 0.0), edge=0, t=0.0)
        b = AttachedPoint(base=(100.0, 100.0), edge=10, t=0.0)
        h = PomDelta('h', 'projeccio', (a, b), 100.0, axis='H')
        v = PomDelta('v', 'projeccio', (a, b), 100.0, axis='V')
        pts = piece.deform(np.zeros((4, 2)))
        self.assertAlmostEqual(h.measure(piece, pts), 100.0, places=9)
        self.assertAlmostEqual(v.measure(piece, pts), 100.0, places=9)

    def test_vora_is_refused_by_name(self):
        """`vora` is absent, not approximated. The message has to say so."""
        piece = square()
        pom = PomDelta('S', 'vora', (on_vertex(piece, 0), on_vertex(piece, 5)), 100.0)
        with self.assertRaises(SolverError) as ctx:
            pom.measure(piece, piece.deform(np.zeros((4, 2))))
        self.assertIn('vora', str(ctx.exception))

    def test_solve_all_keeps_pieces_independent(self):
        one, two = square(), square(side=50.0)
        object.__setattr__(two, 'name', 'SMALL')
        cons_one = [PomDelta('w', 'recta', (on_vertex(one, 0), on_vertex(one, 5)), 110.0),
                    Anchor('o', 0), GrainDirection()]
        reports = solve_all([(one, cons_one), (two, [])])
        self.assertEqual(set(reports), {'SQUARE', 'SMALL'})
        self.assertTrue(np.allclose(reports['SMALL'].displacement, 0.0))
        self.assertGreater(float(np.abs(reports['SQUARE'].displacement).max()), 1.0)


class ReductionTests(SimpleTestCase):
    def test_no_reduction_is_the_identity(self):
        red = NoReduction(4)
        self.assertEqual(red.n_free, 8)
        z = np.arange(8, dtype=float)
        self.assertTrue(np.allclose(red.expand(z), z.reshape(4, 2)))
        j = np.ones((3, 8))
        self.assertTrue(np.allclose(red.project(j), j))


# ─────────────────────────────────────────────────────────────────────────────
# Regressions from the F6.1 diff review (27/08). Each of these failed before the fix.
# ─────────────────────────────────────────────────────────────────────────────

def octagon(r=400.0, cx=1500.0, cy=2000.0, per_edge=3) -> PieceProblem:
    """Eight turn points, so the bending stencil alone leaves a wide null space."""
    import math as _m
    corners = [(cx + r * _m.cos(2 * _m.pi * k / 8), cy + r * _m.sin(2 * _m.pi * k / 8))
               for k in range(8)]
    pts, kinds = [], []
    for k, c0 in enumerate(corners):
        c1 = corners[(k + 1) % 8]
        pts.append(c0)
        kinds.append('turn')
        for i in range(1, per_edge + 1):
            f = i / (per_edge + 1)
            pts.append((c0[0] + f * (c1[0] - c0[0]), c0[1] + f * (c1[1] - c0[1])))
            kinds.append('curve')
    return PieceProblem(name='OCTAGON', base_points=tuple(pts), kinds=tuple(kinds))


def collinear_piece(origin=(2000.0, 3000.0), angle_deg=37.0, side=1200.0):
    """A piece at real 837 coordinate scale with three COLLINEAR turn points.

    Collinear on purpose: it makes |AC| = |AB| + |BC| an exact algebraic identity, so three
    `recta` POMs over (A,B), (B,C), (A,C) have a rank-2 Jacobian. That is the cheapest way to
    hand `diagnose` a dependent row whose right-hand side can then be made to contradict.
    """
    import math as _m
    c, s_ = _m.cos(_m.radians(angle_deg)), _m.sin(_m.radians(angle_deg))
    def at(u, v):
        return (origin[0] + u * c - v * s_, origin[1] + u * s_ + v * c)
    pts, kinds = [], []
    corners = [at(0, 0), at(side / 2, 0), at(side, 0), at(side, side), at(0, side)]
    for k, corner in enumerate(corners):
        nxt = corners[(k + 1) % len(corners)]
        pts.append(corner)
        kinds.append('turn')
        for i in (1, 2):
            f = i / 3
            pts.append((corner[0] + f * (nxt[0] - corner[0]),
                        corner[1] + f * (nxt[1] - corner[1])))
            kinds.append('curve')
    return PieceProblem(name='COLLINEAR', base_points=tuple(pts), kinds=tuple(kinds))


class JacobianStepTests(SimpleTestCase):
    """BUG 1 · the differencing step must scale with the piece, not sit at 1e-6 mm.

    At 837 coordinates (1 000–2 500 mm) an absolute 1e-6 step leaves ~1e-7 of cancellation
    noise in every Jacobian entry, which is an order of magnitude ABOVE the threshold
    `diagnose` uses to decide whether a row adds rank. The detector then calls a genuine
    contradiction well-posed — the exact discrimination the diagnosis exists to provide.
    """

    def test_dependent_contradictory_row_is_named_at_real_coordinates(self):
        """The scale is the point: at 2 376 mm an absolute 1e-6 step hides this conflict.

        Measured while writing the test — `conflicting` under the old absolute step, by
        piece scale: 792 mm → ('AC',) · 1 584 mm → ('AC',) · **2 376 mm → ()** · 3 169 mm →
        (). The bank's own coordinates run to 2 553 mm, so the bench sits on the wrong side
        of that line. A version of this test at 400 mm passes either way and proves nothing.
        """
        piece = collinear_piece()
        self.assertGreater(piece.scale_mm(), 2000.0)
        a, b, c = (on_vertex(piece, i) for i in (0, 3, 6))
        half = 600.0
        ab = PomDelta('AB', 'recta', (a, b), half)
        bc = PomDelta('BC', 'recta', (b, c), half)
        # AC is algebraically AB + BC, and its target is 3 mm away from that sum.
        d = diagnose(piece, [ab, bc, PomDelta('AC', 'recta', (a, c), 2 * half + 3.0)])
        self.assertEqual(d.conflicting, ('AC',))
        self.assertFalse(d.well_posed)

    def test_dependent_consistent_row_is_redundant_not_conflicting(self):
        piece = collinear_piece()
        a, b, c = (on_vertex(piece, i) for i in (0, 3, 6))
        ok = diagnose(piece, [PomDelta('AB', 'recta', (a, b), 600.0),
                              PomDelta('BC', 'recta', (b, c), 600.0),
                              PomDelta('AC', 'recta', (a, c), 1200.0)])
        self.assertEqual(ok.conflicting, ())
        self.assertEqual(ok.redundant, ('AC',))

    def test_step_scales_with_the_piece(self):
        self.assertGreater(collinear_piece().scale_mm(), 10 * square(side=100.0).scale_mm())


class KKTRankTests(SimpleTestCase):
    """BUG 2 · a rank-deficient KKT must not come back as a confident answer.

    `np.linalg.solve` raises only on an exact zero pivot, so a singular system usually
    returns garbage silently. With no ridge and an open gauge that produced an 800 mm piece
    displaced by 1 218 mm, reported `success=True, converged=True`.
    """

    def test_no_ridge_open_gauge_takes_the_minimum_norm_step_and_says_so(self):
        """cond(KKT) = 3,4e22 and `np.linalg.solve` does NOT raise on it.

        Measured: `solve` returns a step of 22,5 mm where the minimum-norm one is 10,0 mm —
        a different answer, reached silently, with nothing in the report to say the system
        was deficient. The two assertions here are exactly those two facts.
        """
        piece = octagon()
        a = AttachedPoint(base=piece.base_points[0], edge=0, t=0.0)
        b = AttachedPoint(base=piece.base_points[16], edge=16, t=0.0)
        span = float(np.linalg.norm(np.array(piece.base_points[0])
                                    - np.array(piece.base_points[16])))
        cons = [PomDelta('w', 'recta', (a, b), span + 20.0)]
        report = solve(piece, cons, Weights(bend=1.0, stretch=0.0, ridge=0.0))
        self.assertTrue(report.success)
        self.assertLess(report.worst_residual_mm, 1e-6)
        # the minimum-norm field, not the arbitrary one a plain `solve` would hand back
        self.assertLess(float(np.abs(report.displacement).max()), 12.0)
        self.assertIn('rank-deficient', report.message)

    def test_duplicated_rows_still_solve(self):
        piece = square()
        a, b = on_vertex(piece, 0), on_vertex(piece, 5)
        cons = [PomDelta('w', 'recta', (a, b), 110.0),
                PomDelta('w-again', 'recta', (a, b), 110.0),
                Anchor('o', 0), GrainDirection()]
        report = solve(piece, cons)
        self.assertTrue(report.converged)
        self.assertLess(report.worst_residual_mm, 1e-9)


class VocabularyTests(SimpleTestCase):
    """BUG 7 · anything that is not «turn» silently became a curve point."""

    def test_unknown_vertex_kind_is_refused(self):
        with self.assertRaises(SolverError) as ctx:
            PieceProblem(name='TYPO', base_points=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0)),
                         kinds=('turn', 'banana', 'curve'))
        self.assertIn('banana', str(ctx.exception))

    def test_out_of_range_anchor_slot_is_a_solver_error(self):
        piece = square()
        with self.assertRaises(SolverError):
            solve(piece, [Anchor('nope', 99)])


class ProjectionAxisTests(SimpleTestCase):
    """BUG 3 · AUTO axis is a property of the cote, resolved once on the base geometry.

    Resolved on the deformed points instead, the `+eps` and `−eps` probes of the Jacobian can
    land on different branches and the difference quotient averages two different functions.
    At exactly 45° the measured derivative came back ±0,5 where the truth is ±1 or 0.
    """

    def test_auto_axis_does_not_flip_under_deformation(self):
        piece = square(side=100.0)
        a, b = on_vertex(piece, 0), on_vertex(piece, 10)      # exactly 45°
        pom = PomDelta('diag', 'projeccio', (a, b), 100.0)
        m = len(piece.turn_indices)
        base_value = pom.measure(piece, piece.deform(np.zeros((m, 2))))

        d = np.zeros((m, 2))
        d[2] = (0.0, 40.0)                    # push the far corner so V would win on-the-fly
        moved = pom.measure(piece, piece.deform(d))
        # H was chosen on the base (tie → H) and must stay chosen: dx is unchanged by d[2]y
        self.assertAlmostEqual(base_value, 100.0, places=9)
        self.assertAlmostEqual(moved, 100.0, places=9)


class DegenerateSegmentTests(SimpleTestCase):
    """BUG 4 · the degeneracy guard is a LENGTH and must trip before the frame explodes."""

    def test_near_coincident_turns_fall_back_to_rigid(self):
        gap = 1e-3
        pts = ((0.0, 0.0), (5.0, 1.0), (gap, 0.0), (0.0, 50.0), (-50.0, 50.0))
        kinds = ('turn', 'curve', 'turn', 'turn', 'turn')
        piece = PieceProblem(name='PINCH', base_points=pts, kinds=kinds)
        d = np.zeros((4, 2))
        d[0] = (1.0, 0.0)
        out = piece.deform(d)
        # the curve point rides rigidly with the start, it does not get thrown metres away
        self.assertLess(float(np.abs(out[1] - np.array([6.0, 1.0])).max()), 1e-9)


class TwoLoopTests(SimpleTestCase):
    """A0 · a piece has TWO contours (cut + sewing) and neither may wrap into the other.

    They share one displacement problem, so they live in one point array — but each cyclic
    wrap (segments, attached-point edges, the smoothing stencil) has to close inside its own
    contour. Wrapped globally, the last vertex of the cut line would be stitched to the first
    of the sewing line by a stencil term and nothing would ever say so.
    """

    @staticmethod
    def two_loops():
        def ring(side, x0, y0):
            corners = [(x0, y0), (x0 + side, y0), (x0 + side, y0 + side), (x0, y0 + side)]
            pts, kinds = [], []
            for k, c in enumerate(corners):
                nxt = corners[(k + 1) % 4]
                pts.append(c)
                kinds.append('turn')
                pts.append(((c[0] + nxt[0]) / 2, (c[1] + nxt[1]) / 2))
                kinds.append('curve')
            return pts, kinds
        a_pts, a_kinds = ring(100.0, 0.0, 0.0)          # "cut"
        b_pts, b_kinds = ring(80.0, 10.0, 10.0)         # "sewing", inset 10 mm
        return PieceProblem(name='TWO', base_points=tuple(a_pts + b_pts),
                            kinds=tuple(a_kinds + b_kinds),
                            loop_starts=(0, len(a_pts)))

    def test_segments_never_cross_loops(self):
        piece = self.two_loops()
        self.assertEqual(piece.loop_ranges, ((0, 8), (8, 16)))
        for seg in piece.segments:
            lo, hi = piece.loop_of(seg.start)
            self.assertTrue(lo <= seg.end < hi)
            for i in seg.interior:
                self.assertTrue(lo <= i < hi)
        self.assertEqual(len(piece.segments), 8)

    def test_next_index_wraps_inside_its_own_loop(self):
        piece = self.two_loops()
        self.assertEqual(piece.next_index(7), 0)        # end of loop 0 -> start of loop 0
        self.assertEqual(piece.next_index(15), 8)       # end of loop 1 -> start of loop 1

    def test_moving_one_loop_leaves_the_other_alone(self):
        piece = self.two_loops()
        d = np.zeros((len(piece.turn_indices), 2))
        d[0] = (5.0, 0.0)                                # a corner of the outer ring
        pts = piece.deform(d)
        base = np.array(piece.base_points)
        self.assertTrue(np.allclose(pts[8:], base[8:]))
        self.assertFalse(np.allclose(pts[:8], base[:8]))

    def test_the_smoothing_stencil_does_not_couple_the_loops(self):
        """The stencil is per contour. Anything that ties them must be explicit."""
        from fhort.patterns.engine.grading_solver import NoReduction, _regulariser
        piece = self.two_loops()
        h = _regulariser(piece, NoReduction(len(piece.turn_indices)),
                         Weights(couple=0.0))
        # turn slots 0-3 are the outer ring, 4-7 the inner one; unknowns interleave x,y
        self.assertLess(float(np.abs(h[:8, 8:]).max()), 1e-12)

    def test_the_coupling_term_ties_facing_turn_points_only(self):
        """A0 · the sewing line follows the cut line it offsets, and only its own facing corner."""
        from fhort.patterns.engine.grading_solver import NoReduction, _regulariser
        piece = self.two_loops()
        pairs = piece.coupled_turn_pairs()
        self.assertEqual(len(pairs), 4)
        # each inner corner pairs with the outer corner it faces, and each exactly once
        self.assertEqual(sorted(j for _i, j in pairs), [4, 5, 6, 7])
        self.assertEqual(sorted(i for i, _j in pairs), [0, 1, 2, 3])

        h = _regulariser(piece, NoReduction(len(piece.turn_indices)), Weights(couple=1.0))
        cross = h[:8, 8:]
        self.assertGreater(float(np.abs(cross).max()), 1e-6)
        # only the paired slots are tied: slot 0 must not reach the inner corner it does
        # not face (slot 6 is diagonally opposite slot 0)
        self.assertLess(abs(float(h[0, 12])), 1e-12)     # x of slot 0 vs x of slot 6

    def test_coupling_pulls_the_sewing_loop_after_the_cut_loop(self):
        piece = self.two_loops()
        outer = AttachedPoint(base=piece.base_points[0], edge=0, t=0.0)
        outer_b = AttachedPoint(base=piece.base_points[4], edge=4, t=0.0)
        cons = [PomDelta('w', 'recta', (outer, outer_b), 110.0),
                Anchor('o', 0), GrainDirection()]
        loose = solve(piece, cons, Weights(couple=0.0))
        tied = solve(piece, cons, Weights(couple=1.0))
        self.assertTrue(loose.converged and tied.converged)
        inner = slice(8, 16)
        # uncoupled, the sewing ring has no reason to move at all
        self.assertLess(float(np.abs(loose.points[inner]
                                     - np.array(piece.base_points)[inner]).max()), 1e-6)
        # coupled, it follows
        self.assertGreater(float(np.abs(tied.points[inner]
                                        - np.array(piece.base_points)[inner]).max()), 1.0)

    def test_a_loop_without_turn_points_is_refused(self):
        with self.assertRaises(SolverError) as ctx:
            PieceProblem(name='BAD',
                         base_points=((0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)),
                         kinds=('turn', 'curve', 'curve', 'curve'), loop_starts=(0, 2))
        self.assertIn('no turn point', str(ctx.exception))
