"""Tests for the grading solver core (F6.1, phase D).

Everything here runs on **synthetic** geometry, on purpose. The 837 is the bank and it
lives in `ops/rosetta/exam_solver.py`; what a unit test has to pin down is the behaviour
the bank cannot show — a conflict that no real pattern contains, a gauge deliberately left
open, an answer that is known in closed form.

These are Python-only: nothing here touches the database, and the engine does not import
Django.
"""
import math

import numpy as np
from django.test import SimpleTestCase

from fhort.patterns.engine.grading_solver import (
    Anchor, AttachedPoint, Diagnosis, FixedPom, GrainDirection, NoReduction, PieceProblem,
    PomDelta, SolverError, Weights, diagnose, solve, solve_all,
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
