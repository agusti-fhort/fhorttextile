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


# ─────────────────────────────────────────────────────────────────────────────
# F6.2 · Inter-size coupling
# ─────────────────────────────────────────────────────────────────────────────

def big_square(side: float = 1400.0, x0: float = 900.0, y0: float = 700.0,
               per_edge: int = 4) -> PieceProblem:
    """A test piece at BANK SCALE, not at unit scale.

    🚨 «The scale was the bug» is a law here now: two F6.1 regression tests were caught
    passing on the broken code because their piece was 400 mm and the defect only bites past
    ~2 000. Anything that exercises the numerics gets built at the 837's own coordinates.
    """
    corners = [(x0, y0), (x0 + side, y0), (x0 + side, y0 + side), (x0, y0 + side)]
    pts, kinds = [], []
    for k, c in enumerate(corners):
        nxt = corners[(k + 1) % 4]
        pts.append(c)
        kinds.append('turn')
        for s in range(1, per_edge + 1):
            f = s / (per_edge + 1)
            pts.append((c[0] + f * (nxt[0] - c[0]), c[1] + f * (nxt[1] - c[1])))
            kinds.append('curve')
    return PieceProblem(name='BIG', base_points=tuple(pts), kinds=tuple(kinds),
                        grain=(x0, y0 + side / 2, x0 + side, y0 + side / 2))


def width_pom(piece: PieceProblem, target: float, name: str = 'w') -> PomDelta:
    return PomDelta(name, 'recta', (on_vertex(piece, 0), on_vertex(piece, 5)), target)


class RuleShapeTests(SimpleTestCase):
    def test_pack_unpack_round_trips(self):
        from fhort.patterns.engine.grading_solver import RuleShape
        shape = RuleShape(rank=2, n_turns=4, n_sizes=3)
        self.assertEqual(shape.size, 2 * 8 + 2 * 3 + 3 * 8)
        d = np.arange(16, dtype=float).reshape(2, 8)
        a = np.arange(6, dtype=float).reshape(2, 3)
        leak = np.arange(24, dtype=float).reshape(3, 8)
        d2, a2, l2 = shape.unpack(shape.pack(d, a, leak))
        self.assertTrue(np.allclose(d2, d) and np.allclose(a2, a) and np.allclose(l2, leak))

    def test_fields_is_the_composition(self):
        from fhort.patterns.engine.grading_solver import RuleShape
        shape = RuleShape(rank=1, n_turns=2, n_sizes=2)
        d = np.array([[1.0, 0.0, 0.0, 2.0]])
        a = np.array([[3.0, 5.0]])
        leak = np.zeros((2, 4))
        f = shape.fields(shape.pack(d, a, leak))
        self.assertTrue(np.allclose(f[0], 3.0 * d[0]))
        self.assertTrue(np.allclose(f[1], 5.0 * d[0]))

    def test_normalise_keeps_the_field_and_fixes_the_scale(self):
        from fhort.patterns.engine.grading_solver import RuleShape
        shape = RuleShape(rank=1, n_turns=2, n_sizes=2)
        z = shape.pack(np.array([[3.0, 4.0, 0.0, 0.0]]), np.array([[2.0, 6.0]]),
                       np.zeros((2, 4)))
        before = shape.fields(z)
        z2 = shape.normalise(z)
        d, a, _ = shape.unpack(z2)
        self.assertAlmostEqual(float(np.linalg.norm(d[0])), 1.0, places=12)
        self.assertTrue(np.allclose(shape.fields(z2), before))


class SvdStructureTests(SimpleTestCase):
    def test_a_pure_rule_field_is_exactly_rank_one(self):
        """The FASE A instrument, on a field built to be a rule."""
        direction = np.array([1.0, -0.5, 2.0, 0.25, -1.5, 0.75])
        amps = np.array([-0.5, 1.0, 2.0, 3.0])
        mat = np.outer(amps, direction)
        sv = np.linalg.svd(mat, compute_uv=False)
        self.assertGreater(sv[0], 1.0)
        self.assertLess(float(sv[1:].max()), 1e-12)

    def test_a_two_rule_field_is_exactly_rank_two(self):
        d1 = np.array([1.0, 0.0, 1.0, 0.0])
        d2 = np.array([0.0, 1.0, 0.0, -1.0])
        mat = np.outer([1.0, 2.0, 3.0, 4.0], d1) + np.outer([0.0, 1.0, 0.0, 2.0], d2)
        sv = np.linalg.svd(mat, compute_uv=False)
        self.assertGreater(sv[1], 1e-6)
        self.assertLess(float(sv[2:].max()), 1e-12)


class CoupledSolveTests(SimpleTestCase):
    @staticmethod
    def problem(targets, extra=None, piece=None):
        piece = piece or big_square()
        base = piece.deform(np.zeros((len(piece.turn_indices), 2)))
        span = float(np.linalg.norm(np.array(piece.base_points[5])
                                    - np.array(piece.base_points[0])))
        per_size = {}
        for size, grow in targets.items():
            cons = [width_pom(piece, span + grow), Anchor('o', 0), GrainDirection()]
            if extra and size in extra:
                cons.append(extra[size](piece, span))
            per_size[size] = cons
        return piece, per_size, span

    def test_proportional_targets_give_a_pure_rule_with_no_leak(self):
        """Targets in proportion 1:2:3 must come out as one direction scaled 1:2:3.

        This is the whole thesis of F6.2 in one assertion: when the garment really does grade
        by a rule, the coupled solver finds the rule and needs no leak at all.
        """
        from fhort.patterns.engine.grading_solver import solve_coupled
        piece, per_size, _span = self.problem({'M': 10.0, 'L': 20.0, 'XL': 30.0})
        rep = solve_coupled(piece, per_size, rank=1)
        self.assertTrue(rep.success and rep.converged)
        self.assertLess(rep.worst_residual_mm, 1e-8)
        # «zero» is a few thousandths of a millimetre: the leak is a soft penalty, so it buys
        # a little smoothness even where the rule suffices. Three orders of magnitude below
        # what a rule that does NOT suffice costs (8 mm) is what makes it an instrument.
        self.assertLess(rep.worst_leak_mm, 0.01)
        amps = rep.amplitudes[0]
        # ⚠️ not 2,000000 and 3,000000: a `recta` target is a DISTANCE, which is not linear
        # in the displacement unless the movement is collinear with the measurement. The
        # regulariser picks the direction, so a 0,03 % departure from the exact ratio is the
        # geometry being honest, not the solver being loose.
        self.assertAlmostEqual(float(amps[1] / amps[0]), 2.0, delta=2e-3)
        self.assertAlmostEqual(float(amps[2] / amps[0]), 3.0, delta=3e-3)
        base = np.array(piece.base_points)
        f_m = rep.points['M'] - base
        f_xl = rep.points['XL'] - base
        self.assertLess(float(np.abs(f_xl - 3.0 * f_m).max()), 0.05)

    def test_a_rule_breaking_target_shows_up_as_leak(self):
        """Targets that refuse one proportion. The leak must appear, and be large.

        The leak is the sprint's measuring device: if it stayed near zero here it would be
        decoration, and «zero leak = pure rule» would mean nothing. Note what makes the
        difference — a second POM at ONE size is absorbed by that size's own amplitude and
        costs 0,01 mm; a second POM at EVERY size with a different progression cannot be, and
        costs 8 mm. The first version of this test used the one-size fixture and passed for
        the wrong reason.
        """
        from fhort.patterns.engine.grading_solver import solve_coupled
        piece, per_size, _span = self.problem({'M': 10.0, 'L': 20.0, 'XL': 30.0})
        clean = solve_coupled(piece, per_size, rank=1)

        piece2 = big_square()
        span = float(np.linalg.norm(np.array(piece2.base_points[5])
                                    - np.array(piece2.base_points[0])))
        height = float(np.linalg.norm(np.array(piece2.base_points[10])
                                      - np.array(piece2.base_points[15])))
        per2 = {}
        for size, (gw, gh) in {'M': (10.0, 0.0), 'L': (20.0, 30.0),
                               'XL': (30.0, 5.0)}.items():
            per2[size] = [width_pom(piece2, span + gw),
                          PomDelta('h', 'recta', (on_vertex(piece2, 10),
                                                  on_vertex(piece2, 15)), height + gh),
                          Anchor('o', 0), GrainDirection()]
        dirty = solve_coupled(piece2, per2, rank=1)

        self.assertTrue(dirty.success)
        self.assertLess(dirty.worst_residual_mm, 1e-6)      # the contract still holds
        self.assertLess(clean.worst_leak_mm, 0.01)
        self.assertGreater(dirty.worst_leak_mm, 1.0)

    def test_one_off_target_is_absorbed_by_its_own_size(self):
        """The other side of the same coin, so the leak's meaning is pinned from both ends."""
        from fhort.patterns.engine.grading_solver import solve_coupled

        def second(p, span):
            height = float(np.linalg.norm(np.array(p.base_points[10])
                                          - np.array(p.base_points[15])))
            return PomDelta('h', 'recta', (on_vertex(p, 10), on_vertex(p, 15)),
                            height + 25.0)

        piece, per_size, _ = self.problem({'M': 10.0, 'L': 20.0, 'XL': 30.0},
                                          extra={'M': second})
        rep = solve_coupled(piece, per_size, rank=1)
        self.assertLess(rep.worst_residual_mm, 1e-6)
        self.assertLess(rep.worst_leak_mm, 0.1)

    def test_the_contract_guard_backs_the_leak_weight_off(self):
        """🚨 A leak weight that is too high BREAKS the contract, and the guard must catch it.

        Measured on this fixture: at a weight of 10⁶ the problem turns stiff enough that
        Gauss-Newton stops reaching feasibility and the POM residual jumps to 6,45 mm — the
        one thing this solver may never do. `solve_coupled` therefore checks afterwards and
        re-solves with a tenth of the weight until the contract holds. Without the guard this
        exact call returns geometry that does not measure what it was told to.
        """
        from fhort.patterns.engine.grading_solver import solve_coupled
        piece = big_square()
        span = float(np.linalg.norm(np.array(piece.base_points[5])
                                    - np.array(piece.base_points[0])))
        height = float(np.linalg.norm(np.array(piece.base_points[10])
                                      - np.array(piece.base_points[15])))
        per_size = {}
        for size, (gw, gh) in {'M': (10.0, 0.0), 'L': (20.0, 30.0),
                               'XL': (30.0, 5.0)}.items():
            per_size[size] = [width_pom(piece, span + gw),
                              PomDelta('h', 'recta', (on_vertex(piece, 10),
                                                      on_vertex(piece, 15)), height + gh),
                              Anchor('o', 0), GrainDirection()]
        rep = solve_coupled(piece, per_size, rank=1, weights=Weights(leak=1e6))
        self.assertLess(rep.worst_residual_mm, 1e-6)
        self.assertIn('backed off', rep.message)

    def test_the_contract_is_never_traded_for_structure(self):
        """Rank one on targets rank one cannot serve: the POMs must STILL be met exactly."""
        from fhort.patterns.engine.grading_solver import solve_coupled
        piece = big_square()
        span = float(np.linalg.norm(np.array(piece.base_points[5])
                                    - np.array(piece.base_points[0])))
        height = float(np.linalg.norm(np.array(piece.base_points[10])
                                      - np.array(piece.base_points[15])))
        per_size = {}
        for size, (gw, gh) in {'M': (10.0, 0.0), 'L': (20.0, 30.0),
                               'XL': (30.0, 5.0)}.items():
            per_size[size] = [width_pom(piece, span + gw),
                              PomDelta('h', 'recta', (on_vertex(piece, 10),
                                                      on_vertex(piece, 15)), height + gh),
                              Anchor('o', 0), GrainDirection()]
        rep = solve_coupled(piece, per_size, rank=1)
        self.assertLess(rep.worst_residual_mm, 1e-6)
        self.assertGreater(rep.worst_leak_mm, 1.0)

    def test_higher_rank_needs_less_leak(self):
        from fhort.patterns.engine.grading_solver import solve_coupled
        piece = big_square()
        span = float(np.linalg.norm(np.array(piece.base_points[5])
                                    - np.array(piece.base_points[0])))
        height = float(np.linalg.norm(np.array(piece.base_points[10])
                                      - np.array(piece.base_points[15])))
        per_size = {}
        for size, (gw, gh) in {'M': (10.0, 0.0), 'L': (20.0, 30.0),
                               'XL': (30.0, 5.0)}.items():
            per_size[size] = [width_pom(piece, span + gw),
                              PomDelta('h', 'recta', (on_vertex(piece, 10),
                                                      on_vertex(piece, 15)), height + gh),
                              Anchor('o', 0), GrainDirection()]
        one = solve_coupled(piece, per_size, rank=1)
        two = solve_coupled(piece, per_size, rank=2)
        self.assertLess(two.worst_leak_mm, one.worst_leak_mm)

    def test_coupling_collapses_the_degrees_of_freedom(self):
        """B4 · the whole thesis of F6.2, as one number.

        Four sizes solved apart are four independent problems and their freedoms add up.
        Coupled under a shared direction they are one problem, and the constraints of every
        size bear on the same unknowns.
        """
        from fhort.patterns.engine.grading_solver import RuleShape, _diagnose_coupled
        piece = big_square()
        span = float(np.linalg.norm(np.array(piece.base_points[5])
                                    - np.array(piece.base_points[0])))
        per_size = {t: [FixedPom('fix', 'recta',
                                 (on_vertex(piece, 0), on_vertex(piece, 5)), span)]
                    for t in ('M', 'L', 'XL')}
        apart = sum(diagnose(piece, per_size[t]).dof for t in per_size)

        shape = RuleShape(rank=1, n_turns=len(piece.turn_indices), n_sizes=3)
        d = np.zeros((1, shape.n_field))
        d[0, 0] = 1.0
        z = shape.pack(d, np.array([[1.0, 2.0, 3.0]]), np.zeros((3, shape.n_field)))
        joint = _diagnose_coupled(piece, per_size, shape, z)

        self.assertEqual(apart, 21)
        self.assertEqual(joint.dof, 8)
        self.assertLess(joint.dof, apart / 2)

    def test_coupling_makes_the_GAUGE_rows_redundant_but_not_the_POM_rows(self):
        """🚨 The brief predicted the redundancy in the wrong place, and the measurement says where.

        B4 expected that one FIXED measurement across four sizes would stop being four
        independent constraints once the sizes shared a direction. It does not: each size
        keeps its **own amplitude**, so its POM row touches a column no other row touches.

        What DOES collapse is the gauge. The anchor and the grain are homogeneous rows — they
        say «this does not move», with a right-hand side of zero — so applied to
        `amplitude[t] · direction` they say the same thing at every size, and only the first
        carries information. Measured here: twelve rows over three sizes come back rank 6,
        with the six gauge rows of L and XL named as redundant and no POM row among them.

        That is a better result than the one predicted: a gauge that has to be repeated per
        size would be a modelling error, and the diagnosis proves it is not one.
        """
        from fhort.patterns.engine.grading_solver import RuleShape, _diagnose_coupled
        piece = big_square()
        span = float(np.linalg.norm(np.array(piece.base_points[5])
                                    - np.array(piece.base_points[0])))
        per_size = {t: [FixedPom('fix', 'recta',
                                 (on_vertex(piece, 0), on_vertex(piece, 5)), span),
                        Anchor('o', 0), GrainDirection()]
                    for t in ('M', 'L', 'XL')}
        shape = RuleShape(rank=1, n_turns=len(piece.turn_indices), n_sizes=3)
        d = np.zeros((1, shape.n_field))
        d[0, 0] = 1.0
        z = shape.pack(d, np.array([[1.0, 2.0, 3.0]]), np.zeros((3, shape.n_field)))
        diag = _diagnose_coupled(piece, per_size, shape, z)

        self.assertEqual(diag.n_unknowns, shape.n_dir + shape.n_amp)   # structural only
        self.assertEqual(diag.n_rows, 12)
        self.assertEqual(diag.rank, 6)
        self.assertEqual(diag.dof, 5)
        self.assertEqual(set(diag.redundant),
                         {'L·o.x', 'L·o.y', 'L·grain', 'XL·o.x', 'XL·o.y', 'XL·grain'})
        self.assertFalse(any(n.endswith('·fix') for n in diag.redundant))
        self.assertEqual(diag.conflicting, ())

    def test_incompatible_targets_across_sizes_are_NOT_a_conflict(self):
        """And this is why: the amplitude of a size can always absorb its own target.

        Asking for +10, +20 and +20 mm at M, L and XL is not a contradiction under coupling —
        it is a statement that XL's amplitude equals L's. Reporting it as a conflict would be
        a false alarm, and the diagnosis does not.
        """
        from fhort.patterns.engine.grading_solver import RuleShape, _diagnose_coupled
        piece = big_square()
        span = float(np.linalg.norm(np.array(piece.base_points[5])
                                    - np.array(piece.base_points[0])))
        per_size = {'M': [width_pom(piece, span + 10.0, 'w')],
                    'L': [width_pom(piece, span + 20.0, 'w')],
                    'XL': [width_pom(piece, span + 20.0, 'w')]}
        shape = RuleShape(rank=1, n_turns=len(piece.turn_indices), n_sizes=3)
        d = np.zeros((1, shape.n_field))
        d[0, 0] = 1.0
        z = shape.pack(d, np.array([[1.0, 2.0, 3.0]]), np.zeros((3, shape.n_field)))
        self.assertEqual(_diagnose_coupled(piece, per_size, shape, z).conflicting, ())

    def test_a_within_size_conflict_is_surfaced_by_the_coupled_solve(self):
        """A contradiction inside ONE size must still be named, and by name.

        🚨 It cannot be found in the joint QR, and that is a property of the problem rather
        than an omission: the joint system is a linearisation of a BILINEAR map, and the
        dependency between «AB», «BC» and «AC» on three collinear points is exact at the base
        state and no longer exact once the seed has moved the piece. Measured on this very
        fixture — the conflict is named at amplitudes 10⁻⁶ and invisible at amplitudes 1.
        So the coupled report carries the PER-SIZE diagnoses too, and says so in its message.
        """
        from fhort.patterns.engine.grading_solver import solve_coupled
        piece = collinear_piece()
        a, b, c = (on_vertex(piece, i) for i in (0, 3, 6))
        rows = [PomDelta('AB', 'recta', (a, b), 600.0),
                PomDelta('BC', 'recta', (b, c), 600.0),
                PomDelta('AC', 'recta', (a, c), 1203.0),
                Anchor('o', 0), GrainDirection()]
        rep = solve_coupled(piece, {'M': rows, 'L': list(rows)}, rank=1)
        self.assertIn('M·AC', rep.message)
        self.assertIn('AC', rep.per_size_diagnosis['M'].conflicting)
        self.assertFalse(rep.per_size_diagnosis['M'].well_posed)

    def test_fixed_only_piece_gives_the_zero_field_at_every_size(self):
        """C3 · collar and placket in miniature: FIXED only, so nothing may move."""
        from fhort.patterns.engine.grading_solver import solve_coupled
        piece = big_square()
        span = float(np.linalg.norm(np.array(piece.base_points[5])
                                    - np.array(piece.base_points[0])))
        per_size = {t: [FixedPom('fix', 'recta',
                                 (on_vertex(piece, 0), on_vertex(piece, 5)), span),
                        Anchor('o', 0), GrainDirection()]
                    for t in ('M', 'L', 'XL')}
        rep = solve_coupled(piece, per_size, rank=1)
        self.assertTrue(rep.converged)
        base = np.array(piece.base_points)
        for t in ('M', 'L', 'XL'):
            self.assertLess(float(np.abs(rep.points[t] - base).max()), 1e-9)
        self.assertLess(rep.worst_leak_mm, 1e-9)
