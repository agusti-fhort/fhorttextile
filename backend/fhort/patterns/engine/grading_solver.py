"""Grading solver v2 — measurement targets in, displacement fields out.

Given the base size of a piece, a set of measurement targets (how much each POM must
grow) and a set of constraints (which measurements must not move, which point stays put,
which direction the grain keeps), this produces the displacement field that takes the base
geometry to the graded one.

It is the inverse of what `measure.py` does: `measure` reads a number off geometry, this
writes geometry that reads back that number.

── WHY THE UNKNOWNS ARE THE TURN POINTS, AND NOT EVERY VERTEX ───────────────────
Because it was measured, not assumed. On the Montse field of the 837 (`parity_837.json`,
7 060 curve points across 5 pieces × 4 non-base sizes) every curve point is the **similarity
image** of its base position in the frame of its own turn-to-turn segment, to a maximum
residual of **0,002 mm** — which is the rounding of the DXF itself. Three rival models
measured on the same data:

    similarity frame (this one)      max 0,002 mm
    lerp along the chord             max 3,510 mm
    lerp along the vertex index      max 25,431 mm
    rigid translation by the start   max 51,103 mm

So a piece with 498 vertices has **56 unknowns**, not 996, and the curves are not a modelling
choice: they are a consequence. This is D-INV-3 ("corbes relatives al marc del tram"),
which was an adopted hypothesis and is now a measured fact.

⚠️ The consequence that matters for the solver: the map from turn displacements to *curve*
positions is **non-linear** (the frame rotates and scales with its endpoints), so any target
that touches a curve point is a non-linear constraint. Hence Gauss-Newton, not one linear
solve.

── THE REGULARISER IS THE CHARACTER OF THE MOTOR ────────────────────────────────
A real grading problem is enormously underdetermined: on the 837's front there are 56
unknowns and three measurement targets. **The constraints pin a handful of numbers; the
regulariser draws everything in between.** Whatever it prefers *is* what the motor thinks
grading looks like, so it is a declared decision and not an implementation detail:

    E(d) = w_bend · Σ ‖second difference of d along the loop‖²      ← dominant
         + w_stretch · Σ ‖first difference of d along the loop‖²
         + w_ridge · Σ ‖d‖²                                          ← conditioning only

Second differences are taken in **arc length**, not in vertex index: turn points are unevenly
spaced (a corner and the four micro-turns of an armhole are not the same distance apart) and
an index-space stencil would quietly make crowded regions stiffer than open ones.

Minimising bending subject to equality constraints makes the displacement interpolate
**affinely in arc length** between the constrained points, which is close to how a
pattern-maker blends between marked points. It is not a claim that this is the right
prior — it is the prior we can name, measure and swap.

── GAUGE ───────────────────────────────────────────────────────────────────────
Measurements are invariant under rigid motion, so the constraint set alone always leaves the
translation (2) and rotation (1) of the piece free. Two constraints close that gauge:

  · `Anchor` — a turn point that does not move. On the 837 four of the five pieces have one
    in the Montse field itself (a vertex whose displacement is exactly zero at every size).
  · `GrainDirection` — zero mean rotation of the field. On the Montse field the grain line
    is at 0,000° at all five sizes of all five pieces, and the implied mean rotation of the
    displacement field is ≤0,0034° on the body pieces.

If the gauge is left open the solver **does not fail**: the diagnosis reports the remaining
degrees of freedom by name and the regulariser returns the minimum-norm member of the family.
A shape can be determined while its placement is not, and saying so is more useful than
refusing to answer.

── NUMPY, NOT SCIPY ────────────────────────────────────────────────────────────
The problems are small (≤56 unknowns, ≤20 constraint rows) and dense. `numpy` — already a
declared dependency of the backend and already used by `patterns/recognition/` — covers the
KKT solve, the least-squares fallback and the rank/null-space work. Adding `scipy` would put
a new dependency in `engine/`, which today imports nothing heavier than `ezdxf`, and buy
nothing at this size.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Iterable, Protocol, Sequence

import numpy as np

from .errors import PatternEngineError

#: Below this a chord has no direction and cannot carry a local frame.
#:
#: 🚨 It is a LENGTH and every site compares a length to it. The first version compared it
#: against `u @ u` — a squared length — which made the effective cut-off √1e-9 = 3,2·10⁻⁵ mm,
#: sixty times TIGHTER than the DXF's own rounding: a pair of turn points 10⁻³ mm apart took
#: the similarity branch and threw a curve point 5 metres away instead of falling back.
#: Measured on the bank, the shortest real turn-to-turn chord across all 25 pieces × 2 layers
#: is 6,11 mm, so 0,005 mm sits 1 200× below anything the material contains.
TOL_DEGENERATE_MM = 5e-3

#: Relative step for the central-difference Jacobian, as a fraction of the piece's own size.
#:
#: 🚨 An ABSOLUTE step is the bug that hides here. The residuals are O(1) in the unknowns and
#: the coordinates run to 2 500 mm, so a fixed 10⁻⁶ mm step leaves ~10⁻⁷ of cancellation noise
#: in every Jacobian entry — an order of magnitude ABOVE the threshold `diagnose` uses to
#: decide whether a row adds rank. The detector then reports a genuine 3 mm contradiction as
#: well-posed, which is exactly the discrimination the whole diagnosis exists to provide.
#: The optimum for central differences is ∛ε_mach · |x| ≈ 6·10⁻⁶ · scale; measured against the
#: analytic derivative of `recta`, this is ~1 600× more accurate than the absolute 10⁻⁶.
STEP_REL = 1e-5

#: Floor for that step, so a degenerate or tiny piece still gets a usable one.
STEP_MIN_MM = 1e-3

#: Singular values below `rank_tol * largest` count as zero when measuring rank.
RANK_TOL = 1e-9

#: Gauss-Newton stops when the largest hard residual falls below this, in mm.
CONVERGENCE_MM = 1e-9

#: 🚨 **Feasibility is not optimality, and the coupled solver has to test both.**
#: The single-size solve starts at zero, so «no residual left» and «nothing left to do» happen
#: together. The coupled solve starts from a SEED that already satisfies every constraint
#: (it is the four single-size answers), so a loop that stops on the residual alone stops on
#: iteration one and returns the seed — it reports the SVD of the F6.1 answer and calls it a
#: coupled solve. It has to keep stepping until the KKT step itself dies, which is the
#: stationarity condition. Relative to the piece's own size, so it means the same on any piece.
STEP_TOL_REL = 1e-12

#: 🚨 And a step that never dies is not the same as a solve that never finishes. The
#: factorisation keeps a rotational gauge inside the spanned subspace (see
#: `RuleShape.normalise`), so the solver can wander along it for ever while the field, the
#: residuals and the leak all sit still. Stationarity is therefore judged on the MERIT not
#: moving — a statement about the answer — rather than on the step being small, which is a
#: statement about the parametrisation. Measured: tightening it from 1e-5 to 1e-8 costs every
#: piece the full iteration budget and moves the leak by 2,5·10⁻³ mm, which is nothing.
MERIT_REL_TOL = 1e-5

#: 🚨 **The contract is structural, not a matter of tuning.** A leak weight high enough to
#: drive the leak to nothing can make the problem stiff enough that Gauss-Newton stops
#: reaching feasibility — measured, at 10⁶ on the test bench: leak 1,2·10⁻⁵ mm and a POM
#: residual of 6,45 mm. Rather than trust a constant to stay on the safe side of that cliff
#: on every piece anyone ever solves, `solve_coupled` checks the residual afterwards and
#: re-solves with a tenth of the weight until the contract holds. A slightly larger leak is
#: a worse REPORT; a missed POM is a wrong ANSWER.
CONTRACT_GUARD_MM = 1e-6
CONTRACT_BACKOFF = 6

#: How many times a coupled step may be halved before it is accepted anyway.
#:
#: 🚨 **Gauss-Newton overshoots here and a full step is not safe.** The composition
#: `amplitude · direction` is BILINEAR, so the linearised step is exact only nearby. Measured
#: on the first iteration of a 1 400 mm test piece: the KKT step satisfies the LINEARISED
#: constraints to 1,5·10⁻¹⁴ and has norm 33 — and at the far end the true residual is 19 mm.
#: The direction is right; the length is not. Backtracking on a merit function of (energy,
#: worst residual) keeps both honest.
MAX_BACKTRACK = 30

#: Price of one millimetre of constraint violation inside the merit function.
MERIT_MU = 1e6

#: The price used DURING backtracking, which is a different job. There the step has not been
#: restored yet, so its infeasibility is the O(t²) of a tangential move and not a real defect;
#: pricing it at MERIT_MU would reject every step and freeze the solver at its seed. Modest
#: here, absolute afterwards — the contract guard is what actually protects the contract.
MERIT_MU_SEARCH = 1e2

MAX_ITERATIONS = 40


class SolverError(PatternEngineError):
    """The problem is malformed — not merely hard, but not a problem."""


# ─────────────────────────────────────────────────────────────────────────────
# B1 · The problem
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Segment:
    """One turn-to-turn stretch of the loop: two endpoints and the curve points between."""

    start: int
    end: int
    interior: tuple[int, ...]


@dataclass(frozen=True)
class AttachedPoint:
    """A point that rides on the loop without being one of its vertices.

    POM recipes anchor to the sewing line, which is an offset of the cut line and is not
    part of the solver's unknowns. Such a point is pinned to the base loop by the edge it
    projects onto and where along that edge it lands, and it moves with that edge. It is
    the same carrier the Rosetta used, so a value measured here and a value measured there
    mean the same thing.
    """

    base: tuple[float, float]
    edge: int
    t: float


@dataclass(frozen=True)
class PieceProblem:
    """A piece as the solver sees it: a base loop and its turn points.

    `grain` is carried as PROVENANCE and is deliberately not read by the solver.
    `GrainDirection` derives its gauge from the turn-point centroid instead, because a grain
    line is an annotation inside the piece and not a boundary vertex — there is nothing on
    the loop to constrain it against. Keeping the line here means the report can quote the
    angle it was measured at (0,000° at every size of every piece of the 837); pretending the
    constraint reads it would be worse than carrying it unread.
    """

    name: str
    base_points: tuple[tuple[float, float], ...]
    kinds: tuple[str, ...]                       # 'turn' | 'curve' per vertex
    grain: tuple[float, float, float, float] | None = None
    #: Start index of each closed loop inside `base_points`. `(0,)` is the single-loop case.
    #:
    #: 🔑 A piece has TWO contours — the cut line and the sewing line — and since the A0
    #: amendment the bank carries both. They are concatenated into one point array because
    #: they share one displacement problem, but they are not one loop: the cyclic wrap of
    #: each segment, of each `AttachedPoint` edge and of the smoothing stencil has to close
    #: inside its own contour. Getting that wrong would sew the hem to the neckline with a
    #: stencil term and nothing would ever say so.
    loop_starts: tuple[int, ...] = (0,)

    def __post_init__(self) -> None:
        if len(self.base_points) != len(self.kinds):
            raise SolverError(
                f'{self.name}: {len(self.base_points)} points but {len(self.kinds)} kinds.'
            )
        unknown = sorted(set(self.kinds) - {'turn', 'curve'})
        if unknown:
            raise SolverError(
                f'{self.name}: unknown vertex kinds {unknown}. Anything that is not «turn» '
                f'silently becomes a curve point, so a typo in an upstream loader would '
                f'become a different problem with no complaint.'
            )
        if not self.turn_indices:
            raise SolverError(
                f'{self.name}: no turn points. The unknowns of this solver ARE the turn '
                f'points; a loop without any has nothing to solve for.'
            )
        if self.loop_starts[0] != 0 or list(self.loop_starts) != sorted(set(self.loop_starts)):
            raise SolverError(
                f'{self.name}: loop_starts must begin at 0 and be strictly increasing, '
                f'got {self.loop_starts}.'
            )
        if self.loop_starts[-1] >= self.n_points:
            raise SolverError(
                f'{self.name}: loop_starts {self.loop_starts} runs past the '
                f'{self.n_points} points.'
            )
        for lo, hi in self.loop_ranges:
            if not any(self.kinds[i] == 'turn' for i in range(lo, hi)):
                raise SolverError(
                    f'{self.name}: the loop [{lo}, {hi}) has no turn point, so nothing in '
                    f'it can move and its curve points have no frame to ride.'
                )

    @property
    def n_points(self) -> int:
        return len(self.base_points)

    @property
    def turn_indices(self) -> tuple[int, ...]:
        return tuple(i for i, k in enumerate(self.kinds) if k == 'turn')

    @property
    def n_unknowns(self) -> int:
        return 2 * len(self.turn_indices)

    @property
    def loop_ranges(self) -> tuple[tuple[int, int], ...]:
        bounds = list(self.loop_starts) + [self.n_points]
        return tuple((bounds[k], bounds[k + 1]) for k in range(len(self.loop_starts)))

    def loop_of(self, index: int) -> tuple[int, int]:
        for lo, hi in self.loop_ranges:
            if lo <= index < hi:
                return lo, hi
        raise SolverError(f'{self.name}: index {index} is in no loop.')

    def next_index(self, index: int) -> int:
        """The next vertex, wrapping inside the index's OWN loop."""
        lo, hi = self.loop_of(index)
        return lo + (index - lo + 1) % (hi - lo)

    @property
    def segments(self) -> tuple[Segment, ...]:
        out = []
        for lo, hi in self.loop_ranges:
            turns = [i for i in range(lo, hi) if self.kinds[i] == 'turn']
            for k, a in enumerate(turns):
                b = turns[(k + 1) % len(turns)]
                interior, i = [], self.next_index(a)
                while i != b:
                    interior.append(i)
                    i = self.next_index(i)
                out.append(Segment(a, b, tuple(interior)))
        return tuple(out)

    def coupled_turn_pairs(self) -> tuple[tuple[int, int], ...]:
        """Pairs (slot on loop 0, slot on loop k>0) of turn points that face each other.

        🔑 **Why this exists.** The cut line and the sewing line are an offset pair: they are
        the same frontier drawn twice, and under grading the offset follows its parent. On
        the 837 that is not a belief, it is a measurement — the two loops have EXACTLY the
        same turn count on all five pieces (28/28, 24/24, 10/10, 9/9, 8/8), and in Montse's
        own field the sewing displacement matches its facing cut displacement to **0,19 mm
        mean at M and 0,51 mm at XL**, against field magnitudes of 11 and 32 mm.

        Left uncoupled, the solver is worse than wrong, it is misleading: every POM anchor
        lives on the sewing loop, so the cut loop would collect no constraint at all and
        drift to whatever the regulariser prefers, while the report showed a vertex error
        that was an artefact of a model nobody believes.

        Pairing is by nearest base position, not by index: the two loops need not start at
        the same corner.
        """
        base = np.asarray(self.base_points, dtype=float)
        turns = self.turn_indices
        per_loop = self.turn_slots_per_loop
        if len(per_loop) < 2:
            return ()
        primary = per_loop[0]
        pairs = []
        for group in per_loop[1:]:
            for slot in group:
                near = min(primary, key=lambda k: float(
                    np.linalg.norm(base[turns[k]] - base[turns[slot]])))
                pairs.append((near, slot))
        return tuple(pairs)

    @property
    def turn_slots_per_loop(self) -> tuple[tuple[int, ...], ...]:
        """Positions in `turn_indices`, grouped by the loop they belong to."""
        turns = self.turn_indices
        return tuple(
            tuple(k for k, i in enumerate(turns) if lo <= i < hi)
            for lo, hi in self.loop_ranges
        )

    # ── the geometry map ────────────────────────────────────────────────────
    def deform(self, d: np.ndarray) -> np.ndarray:
        """Turn displacements → the whole loop.

        `d` is `(m, 2)`: one displacement per turn point, in the order of `turn_indices`.
        Curve points are rebuilt as the similarity image of their base position in the
        frame of their (now moved) segment — the model FASE A measured at 0,002 mm.
        """
        base = np.asarray(self.base_points, dtype=float)
        pts = base.copy()
        turns = self.turn_indices
        for k, i in enumerate(turns):
            pts[i] = base[i] + d[k]

        for seg in self.segments:
            if not seg.interior:
                continue
            a0, b0 = base[seg.start], base[seg.end]
            a1, b1 = pts[seg.start], pts[seg.end]
            u0 = b0 - a0
            l2 = float(u0 @ u0)
            if math.sqrt(l2) <= TOL_DEGENERATE_MM:
                # A segment whose endpoints coincide carries no frame. Its interior rides
                # rigidly with the start; saying so beats dividing by zero.
                for i in seg.interior:
                    pts[i] = base[i] + (a1 - a0)
                continue
            u1 = b1 - a1
            perp0 = np.array([-u0[1], u0[0]])
            perp1 = np.array([-u1[1], u1[0]])
            for i in seg.interior:
                w = base[i] - a0
                alpha = float(w @ u0) / l2
                beta = float(w @ perp0) / l2
                pts[i] = a1 + alpha * u1 + beta * perp1
        return pts

    def resolve(self, point: AttachedPoint, pts: np.ndarray) -> np.ndarray:
        """Where an attached point ends up, given the deformed loop."""
        base = np.asarray(self.base_points, dtype=float)
        i0 = point.edge % self.n_points
        i1 = self.next_index(i0)
        delta = (1.0 - point.t) * (pts[i0] - base[i0]) + point.t * (pts[i1] - base[i1])
        return np.asarray(point.base, dtype=float) + delta

    def scale_mm(self) -> float:
        """The piece's own size — the bounding-box diagonal. Sets the differencing step."""
        base = np.asarray(self.base_points, dtype=float)
        span = base.max(axis=0) - base.min(axis=0)
        return float(np.hypot(*span)) or 1.0

    def arc_spacing(self) -> np.ndarray:
        """Base arc length of each segment, in turn order. The stencil's `h`."""
        base = np.asarray(self.base_points, dtype=float)
        out = []
        for seg in self.segments:
            pts = [seg.start, *seg.interior, seg.end]
            out.append(sum(float(np.linalg.norm(base[pts[k + 1]] - base[pts[k]]))
                           for k in range(len(pts) - 1)))
        return np.array(out, dtype=float)


# ─────────────────────────────────────────────────────────────────────────────
# B1 · Fold / mirror reduction — INTERFACE ONLY
# ─────────────────────────────────────────────────────────────────────────────

class Reduction(Protocol):
    """Fewer unknowns by construction, which is how a fold must be modelled (planegcs I2).

    A piece cut on the fold has half its turn points constrained to be the mirror image of
    the other half. Written as equations, that is a constraint the solver can violate while
    it iterates; written as a **reduction of the parameter vector**, it is a constraint that
    cannot be violated because the violating states do not exist.

    ⚠️ Only the interface lives here. **The 837 has no piece on the fold** (`has_fold` is
    False on all five), so there is nothing on this bank to exercise an implementation
    against, and an unexercised implementation is a guess with tests around it. The real one
    lands in F6.2 together with the mirrored-anchor work.
    """

    @property
    def n_free(self) -> int:
        """How many free parameters remain after the reduction."""

    def expand(self, z: np.ndarray) -> np.ndarray:
        """Free parameters → the full `(m, 2)` displacement array."""

    def project(self, jacobian: np.ndarray) -> np.ndarray:
        """A Jacobian in full coordinates → the same in free coordinates."""


@dataclass(frozen=True)
class NoReduction:
    """The identity. What every piece of the 837 uses."""

    m: int

    @property
    def n_free(self) -> int:
        return 2 * self.m

    def expand(self, z: np.ndarray) -> np.ndarray:
        return np.asarray(z, dtype=float).reshape(self.m, 2)

    def project(self, jacobian: np.ndarray) -> np.ndarray:
        return jacobian


# ─────────────────────────────────────────────────────────────────────────────
# B1 · Constraints
# ─────────────────────────────────────────────────────────────────────────────

class Constraint(Protocol):
    name: str
    kind: str

    def row_names(self) -> tuple[str, ...]:
        """One name per scalar equation. Names are what the diagnosis reports."""

    def residuals(self, piece: PieceProblem, pts: np.ndarray) -> np.ndarray:
        """Zero when satisfied. In mm, so that every row is comparable."""


@dataclass(frozen=True)
class PomDelta:
    """A POM must measure exactly `base + delta` on the solved geometry.

    🔑 The target is **base measured value plus the increment**, never the absolute value
    off the fitxa. At the 837 the pattern and the fitxa already disagree at the base size
    (up to 30,5 mm on EK), and that disagreement is not grading: feeding the absolute value
    would order the solver to deform the base to close a gap that grading never opened.
    What GV201 v9 actually says, and what this takes, is the DELTA.
    """

    name: str
    method: str                       # 'recta' | 'projeccio' | 'ortogonal'
    anchors: tuple[AttachedPoint, ...]
    target_mm: float
    axis: str = ''                    # 'projeccio' only: 'H' | 'V' | '' (auto)
    kind: str = 'pom_delta'

    def row_names(self) -> tuple[str, ...]:
        return (self.name,)

    def residuals(self, piece: PieceProblem, pts: np.ndarray) -> np.ndarray:
        return np.array([self.measure(piece, pts) - self.target_mm])

    def _auto_axis(self, piece: PieceProblem) -> str:
        """AUTO resolved once, on the BASE geometry — never on the deformed points.

        🚨 Resolving it on the deformed points makes the residual a piecewise function whose
        branch can change between the `+eps` and `−eps` probes of the Jacobian. Measured on a
        POM running at exactly 45°, the difference quotient came back as ±0,5 where the true
        derivative is ±1 or 0 — the average of two different functions. Gauss-Newton absorbed
        it there, but a near-diagonal cote would stall or oscillate. Which axis a cote is on
        is a property of the cote, not of the size being solved.
        """
        base = np.asarray(piece.base_points, dtype=float)
        a, b = (piece.resolve(x, base) for x in self.anchors[:2])
        return _dominant_axis(a, b)

    def measure(self, piece: PieceProblem, pts: np.ndarray) -> float:
        p = [piece.resolve(a, pts) for a in self.anchors]
        if self.method == 'recta':
            _expect(self, p, 2)
            return float(np.linalg.norm(p[1] - p[0]))
        if self.method == 'projeccio':
            _expect(self, p, 2)
            axis = self.axis or self._auto_axis(piece)
            return abs(float(p[1][0] - p[0][0]) if axis == 'H' else float(p[1][1] - p[0][1]))
        if self.method == 'ortogonal':
            _expect(self, p, 3)
            v = p[1] - p[0]
            base = float(np.linalg.norm(v))
            if base <= TOL_DEGENERATE_MM:
                raise SolverError(
                    f'{self.name}: the two reference anchors coincide, so there is no line '
                    f'to drop a perpendicular onto.'
                )
            w = p[2] - p[0]
            return abs(float(v[0] * w[1] - v[1] * w[0])) / base
        raise SolverError(
            f'{self.name}: measurement method «{self.method}» is not implemented in the '
            f'solver. `vora` (length along the boundary) needs the deformed arc between the '
            f'two anchors and lands with F6.2; it is deliberately absent rather than '
            f'approximated by the straight distance, which would silently measure something '
            f'else.'
        )


@dataclass(frozen=True)
class FixedPom:
    """A POM that must not move at all: hard delta zero (C2-bis, Agus 27/08).

    Its own class and not `PomDelta(delta=0)` because it is a different statement about the
    garment. A LINEAR rule with increment zero says «this size happens not to grow here»; a
    FIXED rule says «this measurement is not a function of size». The solver treats it as a
    hard equality, and the F6-PRE bank verified 7 of 8 on the 837 — six of them on pieces
    that DO grade, which is the case that means something.
    """

    name: str
    method: str
    anchors: tuple[AttachedPoint, ...]
    base_mm: float
    axis: str = ''
    kind: str = 'fixed_pom'

    def row_names(self) -> tuple[str, ...]:
        return (self.name,)

    def residuals(self, piece: PieceProblem, pts: np.ndarray) -> np.ndarray:
        return PomDelta(self.name, self.method, self.anchors, self.base_mm,
                        self.axis).residuals(piece, pts)

    def measure(self, piece: PieceProblem, pts: np.ndarray) -> float:
        return PomDelta(self.name, self.method, self.anchors, self.base_mm,
                        self.axis).measure(piece, pts)


@dataclass(frozen=True)
class Anchor:
    """A turn point that does not move. Closes the translation gauge."""

    name: str
    turn_slot: int                    # index into `piece.turn_indices`
    kind: str = 'anchor'

    def row_names(self) -> tuple[str, ...]:
        return (f'{self.name}.x', f'{self.name}.y')

    def residuals(self, piece: PieceProblem, pts: np.ndarray) -> np.ndarray:
        turns = piece.turn_indices
        if not -len(turns) <= self.turn_slot < len(turns):
            raise SolverError(
                f'{self.name}: turn slot {self.turn_slot} is out of range; «{piece.name}» has '
                f'{len(turns)} turn points. (This is a malformed problem, so it raises '
                f'SolverError and not IndexError — a caller guarding on the module\'s own '
                f'error type has to be able to catch it.)'
            )
        i = turns[self.turn_slot]
        base = np.asarray(piece.base_points[i], dtype=float)
        return pts[i] - base


@dataclass(frozen=True)
class GrainDirection:
    """The piece keeps its grain: zero mean rotation of the displacement field.

    A grain line is an annotation, not a boundary vertex, so it cannot be constrained
    directly on a boundary-only model. What preserving it MEANS for the field is that the
    field carries no net rotation, and that is one linear equation:

        Σ_k (r_k × d_k) = 0,   r_k = base turn point − centroid of the turn points

    Measured on the Montse field: grain at 0,000° at every size of every piece, and the
    implied mean rotation ≤0,0034° on the body pieces (the sleeve, which has no still point,
    reaches 0,17° at XL — the one place where imposing this is visibly a choice).
    """

    name: str = 'grain'
    kind: str = 'grain'

    def row_names(self) -> tuple[str, ...]:
        return (self.name,)

    def residuals(self, piece: PieceProblem, pts: np.ndarray) -> np.ndarray:
        base = np.asarray(piece.base_points, dtype=float)
        turns = list(piece.turn_indices)
        c = base[turns].mean(axis=0)
        r = base[turns] - c
        d = pts[turns] - base[turns]
        scale = float(np.sum(r * r)) or 1.0
        return np.array([float(np.sum(r[:, 0] * d[:, 1] - r[:, 1] * d[:, 0])) / math.sqrt(scale)])


def _expect(constraint, points, n: int) -> None:
    if len(points) != n:
        raise SolverError(
            f'{constraint.name}: method «{constraint.method}» wants {n} anchors, '
            f'got {len(points)}.'
        )


def _dominant_axis(a, b) -> str:
    return 'H' if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else 'V'


# ─────────────────────────────────────────────────────────────────────────────
# B2 · Diagnosis before solving (planegcs I1)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Diagnosis:
    """What the constraint set is, before anyone asks it for an answer.

    A solver that goes straight to solving answers a question nobody checked was well
    posed. This runs first, always, and names names: a redundant row and a conflicting row
    look identical in a residual norm and are completely different problems.
    """

    n_unknowns: int
    n_rows: int
    rank: int
    dof: int
    redundant: tuple[str, ...]
    conflicting: tuple[str, ...]
    components: tuple[tuple[str, ...], ...]

    @property
    def well_posed(self) -> bool:
        return not self.conflicting

    def summary(self) -> str:
        parts = [f'{self.n_unknowns} unknowns', f'{self.n_rows} rows',
                 f'rank {self.rank}', f'DoF {self.dof}']
        if self.redundant:
            parts.append(f'redundant: {", ".join(self.redundant)}')
        if self.conflicting:
            parts.append(f'CONFLICTING: {", ".join(self.conflicting)}')
        return ' · '.join(parts)


def diagnose(piece: PieceProblem, constraints: Sequence[Constraint],
             reduction: Reduction | None = None) -> Diagnosis:
    """QR of the hard Jacobian at the base state: DoF, redundant rows, conflicting rows.

    Redundant and conflicting are the same algebraic event seen from two sides. A row that
    adds no rank is redundant — it says something already said. If, on top of that, its
    right-hand side disagrees with what the rows before it already fixed, it is not merely
    repeating: it is **contradicting**, and no displacement field satisfies both.

    The separation is done with modified Gram-Schmidt over the rows in order, carrying the
    right-hand side along: whatever survives orthogonalisation of the coefficients but
    leaves a right-hand side behind is a conflict.
    """
    red = reduction or NoReduction(len(piece.turn_indices))
    z0 = np.zeros(red.n_free)
    j, r0 = _jacobian(piece, constraints, red, z0)
    names = [n for c in constraints for n in c.row_names()]

    if j.size == 0:
        return Diagnosis(red.n_free, 0, 0, red.n_free, (), (), ())

    # Rows scaled to unit norm so that «adds rank» does not depend on the units of a row.
    scale = np.linalg.norm(j, axis=1)
    scale[scale == 0.0] = 1.0
    a = j / scale[:, None]
    b = -r0 / scale

    singular = np.linalg.svd(a, compute_uv=False)
    rank = int(np.sum(singular > (singular[0] * RANK_TOL))) if singular.size else 0

    basis: list[np.ndarray] = []
    basis_rhs: list[float] = []
    redundant: list[str] = []
    conflicting: list[str] = []
    tol = max(RANK_TOL, 1e-12) * max(1.0, float(singular[0]) if singular.size else 1.0)
    for i, name in enumerate(names):
        v = a[i].copy()
        rhs = float(b[i])
        for q, qr in zip(basis, basis_rhs):
            proj = float(v @ q)
            v -= proj * q
            rhs -= proj * qr
        norm = float(np.linalg.norm(v))
        if norm <= tol * 10:
            if abs(rhs) > 1e-7:
                conflicting.append(name)
            else:
                redundant.append(name)
            continue
        basis.append(v / norm)
        basis_rhs.append(rhs / norm)

    return Diagnosis(
        n_unknowns=red.n_free, n_rows=len(names), rank=rank, dof=red.n_free - rank,
        redundant=tuple(redundant), conflicting=tuple(conflicting),
        components=_components(constraints, j),
    )


def _components(constraints: Sequence[Constraint], j: np.ndarray
                ) -> tuple[tuple[str, ...], ...]:
    """Which constraints are coupled to which (planegcs I3).

    Sliced out of the Jacobian that was already built, not recomputed per constraint: a
    diagnosis that costs one Jacobian per row turns the exam from seconds into minutes.

    ⚠️ **This is the coupling of the CONSTRAINTS, not of the solve.** It reads the Jacobian
    and nothing else, so two POMs on disjoint turn points really do come back as two buckets
    — and they should, because that is what the caller wants to know. The regulariser then
    couples everything anyway (its stencil goes all the way round a closed loop), which is
    why a piece is never actually solved in pieces. On the 837 every constraint set contains
    `GrainDirection`, which touches every turn point, so the answer there is always one
    bucket for that reason and not for the loop's.
    """
    touched: list[set[int]] = []
    row = 0
    for c in constraints:
        k = len(c.row_names())
        block = j[row:row + k]
        touched.append({int(i) for i in np.nonzero(np.any(np.abs(block) > 1e-12, axis=0))[0]})
        row += k

    parent = list(range(len(constraints)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(constraints)):
        for k in range(i + 1, len(constraints)):
            if touched[i] & touched[k]:
                a, b = find(i), find(k)
                if a != b:
                    parent[a] = b

    buckets: dict[int, list[str]] = {}
    for i, c in enumerate(constraints):
        buckets.setdefault(find(i), []).append(c.name)
    return tuple(tuple(v) for v in buckets.values())


# ─────────────────────────────────────────────────────────────────────────────
# B3 · The solve
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Weights:
    """The regulariser, named so it can be argued with. See the module docstring."""

    bend: float = 1.0
    stretch: float = 0.0
    ridge: float = 1e-8
    #: How hard the sewing line is tied to the cut line it offsets. See
    #: `PieceProblem.coupled_turn_pairs` for why it must not be zero on a two-loop piece.
    #: A soft penalty and not a hard reduction on purpose: the match is 0,19–0,51 mm, which
    #: is the same order as the tolerance itself, so forcing equality would inject the
    #: mismatch as error instead of letting the constraints arbitrate.
    couple: float = 1.0
    #: How hard the per-size leak is pushed to zero. See the F6.2 block: the leak is a
    #: MEASURING DEVICE — how much structure was not enough — so it must be expensive enough
    #: that the solver reaches for it only when the rule genuinely cannot comply.
    #:
    #: The default is measured, not chosen — and the measurement found a cliff. On a 1 400 mm
    #: test piece the leak falls as the weight rises (10 → 1,5·10⁻² mm · 10² → 3,5·10⁻³ ·
    #: 10⁵ → 2,7·10⁻³) but at 10⁶ the problem turns so stiff that Gauss-Newton stops reaching
    #: feasibility and **the POM residual jumps to 6,45 mm**. That is the one thing this
    #: solver may never do, so 10⁵ is the default and `solve_coupled` backs the weight off by
    #: itself if the contract is ever missed — see CONTRACT_GUARD_MM.
    leak: float = 1e5


@dataclass
class SolveReport:
    """planegcs I6: `success` and `converged` are two different words on purpose.

    · **success** — the solve ran and produced a field. It can be True on a problem that
      never converged: an underdetermined piece has an answer, just not a unique one.
    · **converged** — every hard residual reached tolerance. It can be False while success
      is True, and that is the interesting case, because it means the targets contradict
      each other or the geometry cannot reach them.

    Collapsing the two into one boolean is how a solver ends up reporting «failed» for a
    piece it solved perfectly and «ok» for one it did not.
    """

    piece: str
    success: bool
    converged: bool
    iterations: int
    diagnosis: Diagnosis
    residuals_mm: dict[str, float]
    displacement: np.ndarray                     # (m, 2), turn order
    points: np.ndarray                           # (n, 2), the whole solved loop
    message: str = ''

    @property
    def worst_residual_mm(self) -> float:
        return max((abs(v) for v in self.residuals_mm.values()), default=0.0)


def solve(piece: PieceProblem, constraints: Sequence[Constraint],
          weights: Weights | None = None,
          reduction: Reduction | None = None) -> SolveReport:
    """Gauss-Newton on the constraints, minimum-bending in the null space.

    Each iteration solves the equality-constrained quadratic program

        min ½ zᵀHz + gᵀz   s.t.   J z = −r

    through its KKT system. `H` is the regulariser and never changes; `J` and `r` are
    relinearised at the current state because the curve rebuild is non-linear in the turn
    displacements. When the KKT matrix is singular — an open gauge, a redundant row — it is
    solved in least-squares, which picks the minimum-norm step instead of refusing.
    """
    w = weights or Weights()
    red = reduction or NoReduction(len(piece.turn_indices))
    diagnosis = diagnose(piece, constraints, red)

    h = _regulariser(piece, red, w)
    z = np.zeros(red.n_free)
    converged = False
    iterations = 0
    kkt_deficient = False

    for iterations in range(1, MAX_ITERATIONS + 1):
        j, r = _jacobian(piece, constraints, red, z)
        if j.size == 0:
            converged = True
            break
        if float(np.max(np.abs(r))) <= CONVERGENCE_MM:
            converged = True
            break
        step, full_rank = _kkt_step(h, j, r, h @ z)
        kkt_deficient = kkt_deficient or not full_rank
        if step is None:
            return SolveReport(
                piece.name, success=False, converged=False, iterations=iterations,
                diagnosis=diagnosis, residuals_mm=_named(constraints, r),
                displacement=red.expand(z), points=piece.deform(red.expand(z)),
                message='the KKT system could not be solved even in least squares',
            )
        z = z + step

    d = red.expand(z)
    pts = piece.deform(d)
    # Residuals only: a Jacobian here would be ~117x the cost and is thrown away.
    r = _residual_vector(piece, constraints, red, z)
    residuals = _named(constraints, r)
    worst = max((abs(v) for v in residuals.values()), default=0.0)
    converged = converged or worst <= CONVERGENCE_MM

    message = ''
    if not converged:
        message = (f'Gauss-Newton stopped at {MAX_ITERATIONS} iterations with a worst '
                   f'residual of {worst:.6f} mm. Worst rows: '
                   + ', '.join(f'{n}={v:+.3f}' for n, v in
                               sorted(residuals.items(), key=lambda kv: -abs(kv[1]))[:3])
                   + '.')
    if kkt_deficient:
        message = (f'{message} The KKT system was rank-deficient at least once; the step '
                   f'was taken in least squares (minimum norm).').strip()
    if diagnosis.conflicting:
        message = (f'{message} Constraints in conflict: '
                   f'{", ".join(diagnosis.conflicting)}.').strip()
    if diagnosis.dof > 0 and not message:
        message = (f'{diagnosis.dof} degrees of freedom left open; the regulariser chose '
                   f'the minimum-bending member of that family.')

    return SolveReport(piece.name, success=True, converged=converged, iterations=iterations,
                       diagnosis=diagnosis, residuals_mm=residuals, displacement=d,
                       points=pts, message=message)


def solve_all(problems: Iterable[tuple[PieceProblem, Sequence[Constraint]]],
              weights: Weights | None = None) -> dict[str, SolveReport]:
    """B5 · Independent pieces are independent problems, and are solved as such.

    No constraint in this model crosses a piece (a seam relation would, and does not exist
    here yet), so the global problem is block-diagonal by construction and solving it as one
    system would only make the KKT matrix bigger and the diagnosis less specific.
    """
    return {p.name: solve(p, cs, weights) for p, cs in problems}


# ─────────────────────────────────────────────────────────────────────────────
# internals
# ─────────────────────────────────────────────────────────────────────────────

def _named(constraints: Sequence[Constraint], r: np.ndarray) -> dict[str, float]:
    names = [n for c in constraints for n in c.row_names()]
    return {n: float(v) for n, v in zip(names, r)}


def _residual_vector(piece: PieceProblem, constraints: Sequence[Constraint],
                     red: Reduction, z: np.ndarray) -> np.ndarray:
    pts = piece.deform(red.expand(z))
    chunks = [np.asarray(c.residuals(piece, pts), dtype=float).ravel() for c in constraints]
    return np.concatenate(chunks) if chunks else np.zeros(0)


def _jacobian(piece: PieceProblem, constraints: Sequence[Constraint],
              red: Reduction, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Central differences, with the step scaled to the PIECE, not to 1 mm.

    With ≤56 unknowns an analytic Jacobian buys speed we do not need and costs a class of
    silent sign errors we cannot afford. What it does cost is step size: see `STEP_REL`.
    """
    r0 = _residual_vector(piece, constraints, red, z)
    if r0.size == 0:
        return np.zeros((0, red.n_free)), r0
    eps = max(STEP_MIN_MM, STEP_REL * piece.scale_mm())
    j = np.zeros((r0.size, red.n_free))
    for k in range(red.n_free):
        zp, zm = z.copy(), z.copy()
        zp[k] += eps
        zm[k] -= eps
        j[:, k] = (_residual_vector(piece, constraints, red, zp)
                   - _residual_vector(piece, constraints, red, zm)) / (2 * eps)
    return red.project(j), r0


def _regulariser(piece: PieceProblem, red: Reduction, w: Weights) -> np.ndarray:
    """H = w_bend·B'B + w_stretch·D'D + w_ridge·I, in free coordinates.

    Both stencils are built on the turn points in loop order and weighted by ARC LENGTH,
    so a crowded armhole is not stiffer than an open side seam just for being crowded.
    """
    m = len(piece.turn_indices)
    h_arc = np.where(piece.arc_spacing() > 0, piece.arc_spacing(), 1.0)

    want_stretch = w.stretch != 0.0
    rows_b, rows_d = [], []
    # 🔑 One cyclic stencil PER LOOP. `segments` are emitted loop by loop and in loop order,
    # so segment `offset + j` of a loop with `q` turn slots runs from its turn j to j+1.
    offset = 0
    for slots in piece.turn_slots_per_loop:
        q = len(slots)
        for j in range(q):
            hp = h_arc[offset + (j - 1) % q]
            hn = h_arc[offset + j]
            row = np.zeros(m)
            row[slots[(j - 1) % q]] += 2.0 / (hp * (hp + hn))
            row[slots[j]] += -2.0 / (hp * hn)
            row[slots[(j + 1) % q]] += 2.0 / (hn * (hp + hn))
            rows_b.append(row * math.sqrt((hp + hn) / 2.0))

            if want_stretch:
                row = np.zeros(m)
                row[slots[j]] -= 1.0 / hn
                row[slots[(j + 1) % q]] += 1.0 / hn
                rows_d.append(row * math.sqrt(hn))
        offset += q

    b = np.array(rows_b)
    hm = w.bend * (b.T @ b)
    if want_stretch:
        dmat = np.array(rows_d)
        hm = hm + w.stretch * (dmat.T @ dmat)

    pairs = piece.coupled_turn_pairs() if w.couple else ()
    if pairs:
        # Scaled by the typical arc spacing so the term is comparable to a first difference
        # and the weight stays a dimensionless knob.
        escala = 1.0 / max(float(np.mean(h_arc)), 1e-9)
        rows_c = []
        for i, j in pairs:
            row = np.zeros(m)
            row[i] += escala
            row[j] -= escala
            rows_c.append(row)
        c = np.array(rows_c)
        hm = hm + w.couple * (c.T @ c)

    # Both coordinates of a turn point share the stencil; interleave into (2m, 2m).
    full = np.zeros((2 * m, 2 * m))
    full[0::2, 0::2] = hm
    full[1::2, 1::2] = hm
    full += w.ridge * np.eye(2 * m)

    if isinstance(red, NoReduction):
        return full
    basis = np.array([red.expand(e).ravel() for e in np.eye(red.n_free)])
    return basis @ full @ basis.T


def _kkt_step(h: np.ndarray, j: np.ndarray, r: np.ndarray,
              grad: np.ndarray) -> tuple[np.ndarray | None, bool]:
    """One KKT solve: minimise ½sᵀHs + gradᵀs subject to J s = −r.

    `grad` is passed rather than computed as `H z` because the coupled solver's energy is
    not ½zᵀHz: its field is a bilinear function of the unknowns, so the gradient is
    `Bᵀ H d`, not `H z`. The single-size caller passes `H z` and gets the old behaviour.

    🚨 **Always least squares, never `solve` with an exception guard.** `np.linalg.solve`
    raises only on an EXACT zero pivot; a genuinely rank-deficient KKT usually gets a tiny
    non-zero pivot and returns garbage without raising. Measured: with `Weights(ridge=0)` and
    an open gauge, cond(KKT) = 1,6·10²³, no exception, and an 800 mm octagon asked to grow
    20 mm came back displaced by **1 218 mm** — flagged `success=True, converged=True`. A
    wrong answer returned confidently is the one failure mode this module claims to not have.

    `lstsq` returns the same answer as `solve` on a well-conditioned system and the
    minimum-norm one otherwise, at a cost that is nothing at this size. It also hands back the
    effective rank, which is how the caller learns the KKT was deficient instead of guessing.
    """
    n = h.shape[0]
    m = j.shape[0]
    kkt = np.zeros((n + m, n + m))
    kkt[:n, :n] = h
    kkt[:n, n:] = j.T
    kkt[n:, :n] = j
    rhs = np.concatenate([-grad, -r])
    sol, _res, rank, _sv = np.linalg.lstsq(kkt, rhs, rcond=None)
    if not np.all(np.isfinite(sol)):
        return None, False
    return sol[:n], rank == n + m


# ─────────────────────────────────────────────────────────────────────────────
# F6.2 · Inter-size coupling — solving the four sizes as ONE grading rule
# ─────────────────────────────────────────────────────────────────────────────
#
# F6.1 solved each size on its own and measured why that is wasteful: a piece's grading
# field is nearly low-rank across its sizes, so four independent problems throw away the
# strongest structure in the data. Here the four sizes become one system with the shape of a
# rule — **directions** that say WHERE the piece grows, **amplitudes** that say HOW MUCH at
# each size — plus a penalised **leak** for whatever that structure cannot reach.
#
# ── WHY THE RANK IS A PARAMETER AND NOT ONE ──────────────────────────────────────
# The brief asked for one direction and one amplitude per size, which is rank one. Measured
# on the bank (`ops/rosetta/exam_rank.py`), rank one is refuted twice and neither refutation
# is arguable:
#
#   · **geometrically** — one component leaves 6,80 mm on the front, thirteen times the
#     phase criterion. Two leave 1,02 mm, three leave 0,23 mm.
#   · **by the fitxa's own targets** — a rank-one field grows every measurement on a piece in
#     the SAME proportion, and the fitxa does not ask for that. On the front alone its LINEAR
#     POMs demand three different XS/M ratios: A, B, C want −0,667; D wants −0,500; E, F, S
#     want 0,000. No amplitude vector satisfies those at once, at any direction, at any rank
#     one. That is a fact about the targets, not the geometry.
#
# So `rank` is an input, the default is 2, and the exam reports 1, 2 and 3. Rank one remains
# worth printing because it is the interpretable one: it IS the rule, and how far it misses
# is how far the garment is from being gradeable by a single rule.
#
# ── THE LEAK IS A MEASURING DEVICE, NOT A SAFETY NET ─────────────────────────────
# `leak[t]` is a free displacement per size, penalised hard. It exists so the contract can
# always be met — the POM gate does not negotiate — and so that the report can say **how much
# structure was not enough, and where**. Zero leak means the rule sufficed. It is reported per
# size and per piece for exactly that reason.
#
# ── WHY THIS IS FAST ENOUGH ──────────────────────────────────────────────────────
# The unknown vector is large (the front: 224 direction + 8 amplitude + 448 leak = 680), and
# a finite-difference Jacobian over it would need 1 360 residual evaluations per iteration.
# It is never built. The residuals depend on the unknowns ONLY through the composed field of
# each size, so the chain rule does the work with exact factors:
#
#     ∂r_t/∂direction[k] = J_t · amplitude[k, t]      ∂r_t/∂amplitude[k, t] = J_t · direction[k]
#     ∂r_t/∂leak[t]      = J_t
#
# where `J_t` is the per-size field Jacobian — the same object F6.1 already computes, at the
# same cost. Four of those per iteration and some matrix products, instead of 1 360 deforms.


@dataclass(frozen=True)
class RuleShape:
    """How the unknown vector is laid out. All the index arithmetic lives here, once."""

    rank: int
    n_turns: int
    n_sizes: int

    @property
    def n_field(self) -> int:
        return 2 * self.n_turns

    @property
    def n_dir(self) -> int:
        return self.rank * self.n_field

    @property
    def n_amp(self) -> int:
        return self.rank * self.n_sizes

    @property
    def n_leak(self) -> int:
        return self.n_sizes * self.n_field

    @property
    def size(self) -> int:
        return self.n_dir + self.n_amp + self.n_leak

    def unpack(self, z: np.ndarray):
        d = z[:self.n_dir].reshape(self.rank, self.n_field)
        a = z[self.n_dir:self.n_dir + self.n_amp].reshape(self.rank, self.n_sizes)
        leak = z[self.n_dir + self.n_amp:].reshape(self.n_sizes, self.n_field)
        return d, a, leak

    def pack(self, d: np.ndarray, a: np.ndarray, leak: np.ndarray) -> np.ndarray:
        return np.concatenate([d.ravel(), a.ravel(), leak.ravel()])

    def fields(self, z: np.ndarray) -> np.ndarray:
        """(n_sizes, n_field) — the displacement each size ends up with."""
        d, a, leak = self.unpack(z)
        return a.T @ d + leak

    def normalise(self, z: np.ndarray) -> np.ndarray:
        """Unit-norm each direction, absorbing the scale into its amplitude.

        **The gauge, and why it is a projection and not a constraint.** The factorisation
        `amplitude · direction` is invariant under `(v/c, a·c)`, so the scale is free. Fixing
        it with an equation would add a row to a system whose answer does not depend on it;
        renormalising after each step fixes it by construction and costs nothing.

        ⚠️ For rank ≥ 2 a rotation inside the spanned subspace survives this, and that is
        left alone on purpose: the FIELD is unique, only its factorisation is not. The
        diagnosis reports those degrees of freedom rather than pretending they are gone.
        """
        d, a, leak = self.unpack(z)
        d, a = d.copy(), a.copy()
        for k in range(self.rank):
            s = float(np.linalg.norm(d[k]))
            if s > 1e-12:
                d[k] /= s
                a[k] *= s
        return self.pack(d, a, leak)


@dataclass
class CoupledReport:
    """Same vocabulary as `SolveReport`, one level up. planegcs I6 still applies."""

    piece: str
    rank: int
    success: bool
    converged: bool
    iterations: int
    #: The JOINT diagnosis: how much freedom the coupling leaves, at the seed.
    diagnosis: Diagnosis
    #: 🔑 And the per-size ones, which answer a different question and must not be dropped.
    #:
    #: A contradiction between two POMs of the SAME size is a fact about that size's
    #: constraint set and is visible in its own QR — F6.1 already finds it. In the joint
    #: system it can hide, because the diagnosis is a linearisation of a BILINEAR problem and
    #: a dependency that is exact at the base state stops being exact once the seed has moved
    #: the piece (measured: the same injected conflict is named at amplitudes 10⁻⁶ and
    #: invisible at amplitudes 1). Carrying both diagnoses is the honest answer: the joint one
    #: says how coupled the problem is, the per-size ones say whether each size is well posed.
    per_size_diagnosis: dict[str, Diagnosis]
    #: size → {constraint name → residual in mm}
    residuals_mm: dict[str, dict[str, float]]
    #: size → (n, 2) solved loop
    points: dict[str, np.ndarray]
    #: (rank, 2·n_turns) unit directions and (rank, n_sizes) amplitudes
    directions: np.ndarray
    amplitudes: np.ndarray
    #: size → RMS and max of the leak that size needed, in mm
    leak_mm: dict[str, tuple[float, float]]
    message: str = ''

    @property
    def worst_residual_mm(self) -> float:
        return max((abs(v) for rows in self.residuals_mm.values() for v in rows.values()),
                   default=0.0)

    @property
    def worst_leak_mm(self) -> float:
        return max((mx for _rms, mx in self.leak_mm.values()), default=0.0)


def field_jacobian(piece: PieceProblem, constraints: Sequence[Constraint],
                   field: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(∂residuals/∂field, residuals) at one size. The building block of the coupled solve."""
    return _jacobian(piece, constraints, NoReduction(len(piece.turn_indices)), field)


def _composition_matrix(shape: RuleShape, z: np.ndarray) -> np.ndarray:
    """B = ∂(all size fields)/∂z, at the current z. Exact, and cheap to write down."""
    d, a, _leak = shape.unpack(z)
    nf, ns, rk = shape.n_field, shape.n_sizes, shape.rank
    b = np.zeros((ns * nf, shape.size))
    eye = np.eye(nf)
    for t in range(ns):
        rows = slice(t * nf, (t + 1) * nf)
        for k in range(rk):
            b[rows, k * nf:(k + 1) * nf] = a[k, t] * eye
            b[rows, shape.n_dir + k * ns + t] = d[k]
        base = shape.n_dir + shape.n_amp + t * nf
        b[rows, base:base + nf] = eye
    return b


def solve_coupled(piece: PieceProblem,
                  per_size: dict,
                  rank: int = 2,
                  weights: Weights | None = None,
                  seed: dict | None = None) -> CoupledReport:
    """See `_solve_coupled_once`. This wrapper only protects the contract.

    The leak weight trades a smaller leak against numerical stiffness, and past a point the
    stiffness wins and the POM residual blows up. The contract does not negotiate, so if the
    solve comes back having missed it, the weight is cut tenfold and it runs again. What that
    costs is a slightly larger leak in the report; what it buys is that no caller ever
    receives geometry that does not measure what it was told to measure.
    """
    w = weights or Weights()
    report = None
    for attempt in range(CONTRACT_BACKOFF):
        report = _solve_coupled_once(piece, per_size, rank,
                                     replace(w, leak=w.leak / (10.0 ** attempt)), seed)
        if report.worst_residual_mm <= CONTRACT_GUARD_MM:
            if attempt:
                report.message = (
                    f'{report.message} Leak weight backed off {attempt}× (to '
                    f'{w.leak / (10.0 ** attempt):.0e}) to keep the contract.').strip()
            return report
    report.message = (f'{report.message} The contract was still missed after '
                      f'{CONTRACT_BACKOFF} back-offs of the leak weight.').strip()
    return report


def _solve_coupled_once(piece: PieceProblem,
                        per_size: dict,
                        rank: int = 2,
                        weights: Weights | None = None,
                        seed: dict | None = None) -> CoupledReport:
    """The four sizes as one grading rule: shared directions, per-size amplitudes.

    **The initial guess is our own answer, never Montse's.** Each size is first solved on its
    own — exactly the F6.1 path — and the four fields are then factorised by SVD to seed the
    directions and amplitudes. That keeps the structure honest: nothing about the bank's
    graded field enters the solve, only the targets do. Starting from zero directions would be
    worse than slow, it would be degenerate: with `direction = 0` the derivative with respect
    to every amplitude is zero and Gauss-Newton has nowhere to step.
    """
    w = weights or Weights()
    sizes = tuple(per_size)
    m = len(piece.turn_indices)
    shape = RuleShape(rank=rank, n_turns=m, n_sizes=len(sizes))

    seed = seed or {t: solve(piece, per_size[t], w) for t in sizes}
    per_size_diag = {t: seed[t].diagnosis for t in sizes}
    seeded = np.array([seed[t].displacement.ravel() for t in sizes])
    u, sv, vt = np.linalg.svd(seeded, full_matrices=False)
    k = min(rank, len(sv))
    directions = np.zeros((rank, shape.n_field))
    amplitudes = np.zeros((rank, len(sizes)))
    directions[:k] = vt[:k]
    amplitudes[:k] = (u[:, :k] * sv[:k]).T
    z = shape.normalise(shape.pack(directions, amplitudes,
                                   seeded - amplitudes.T @ directions))

    # 🔑 The bending energy of a real piece is of order 10⁻⁸ (its stencil is 1/length²),
    # while the leak is measured in millimetres. Normalising H by its own mean diagonal makes
    # every weight in `Weights` a dimensionless knob that means the same on any piece — and
    # it changes nothing: an equality-constrained QP has the same solution when H and the
    # gradient are scaled together.
    h_field = _regulariser(piece, NoReduction(m), w)
    escala_h = float(np.mean(np.diag(h_field))) or 1.0
    h_field = h_field / escala_h
    h_block = np.kron(np.eye(len(sizes)), h_field)
    leak_slice = slice(shape.n_dir + shape.n_amp, shape.size)

    diagnosis = _diagnose_coupled(piece, per_size, shape, z)
    converged, iterations, kkt_deficient, stalled = False, 0, False, False
    step_tol = STEP_TOL_REL * piece.scale_mm()

    for iterations in range(1, MAX_ITERATIONS + 1):
        fields = shape.fields(z)
        blocks, rs = [], []
        for t_i, t in enumerate(sizes):
            j_t, r_t = field_jacobian(piece, per_size[t], fields[t_i])
            blocks.append(j_t)
            rs.append(r_t)
        r = np.concatenate(rs) if rs else np.zeros(0)
        feasible = r.size == 0 or float(np.max(np.abs(r))) <= CONVERGENCE_MM
        if feasible and stalled:
            converged = True
            break

        b = _composition_matrix(shape, z)
        j_full = np.zeros((int(sum(x.shape[0] for x in blocks)), shape.size))
        row = 0
        for t_i, j_t in enumerate(blocks):
            if j_t.size:
                j_full[row:row + j_t.shape[0]] = j_t @ b[t_i * shape.n_field:
                                                         (t_i + 1) * shape.n_field]
            row += j_t.shape[0]

        h_z = b.T @ h_block @ b
        grad = b.T @ (h_block @ fields.ravel())
        h_z[leak_slice, leak_slice] += w.leak * np.eye(shape.n_leak)
        grad[leak_slice] += w.leak * z[leak_slice]
        h_z += w.ridge * np.eye(shape.size)
        grad += w.ridge * z

        step, full_rank = _kkt_step(h_z, j_full, r, grad)
        kkt_deficient = kkt_deficient or not full_rank
        if step is None:
            return _coupled_report(piece, shape, sizes, z, diagnosis, per_size_diag,
                                   per_size, False, False, iterations, kkt_deficient,
                                   'the KKT system could not be solved even in least squares')

        # 🚨 **Restore with the Jacobian this iteration ALREADY built.** Two wrong versions
        # came before this one and each was measured:
        #
        #  · restoring from scratch inside the search costs 30 × 4 × 4 field Jacobians per
        #    iteration — minutes per piece, and the exam produced no output in 300 s on the
        #    SMALLEST piece;
        #  · dropping the restoration and softening the merit instead made the search cheap
        #    and the solver WORSE: on targets a pure rule can serve with zero leak, it came
        #    back with 5,8 mm of leak. Speed bought by losing the answer is not speed.
        #
        # `j_full` is already in hand and is a perfectly good chord Jacobian for a step that
        # is, by construction, small. So each backtrack costs one residual evaluation and one
        # solve against a factorisation computed once — and the merit can go back to pricing
        # infeasibility at its true, absolute rate.
        pinv = np.linalg.pinv(j_full) if j_full.size else None
        merit0 = _coupled_merit(piece, per_size, shape, z, h_block, w)
        t, trial = 1.0, z
        for _ in range(MAX_BACKTRACK):
            trial = _restore_with(piece, per_size, shape,
                                  shape.normalise(z + t * step), pinv)
            if _coupled_merit(piece, per_size, shape, trial, h_block, w) <= merit0:
                break
            t *= 0.5
        merit_new = _coupled_merit(piece, per_size, shape, trial, h_block, w)
        stalled = (float(np.max(np.abs(trial - z))) <= step_tol
                   or merit0 - merit_new <= MERIT_REL_TOL * max(1.0, abs(merit0)))
        z = trial

    return _coupled_report(piece, shape, sizes, z, diagnosis, per_size_diag, per_size,
                           True, converged, iterations, kkt_deficient, '')


def _restore_with(piece: PieceProblem, per_size, shape: RuleShape, z: np.ndarray,
                  pinv: np.ndarray | None, rounds: int = 3) -> np.ndarray:
    """Pull a trial point back onto the constraint manifold with a GIVEN pseudo-inverse.

    The caller already built the coupled Jacobian for this iteration, so restoration costs a
    residual evaluation and a matrix-vector product per round. See the note at the call site
    for the two slower and less correct versions this replaced.
    """
    if pinv is None:
        return z
    for _ in range(rounds):
        fields = shape.fields(z)
        rs = [_residual_vector(piece, per_size[t], NoReduction(shape.n_turns), fields[t_i])
              for t_i, t in enumerate(per_size)]
        rs = [r for r in rs if r.size]
        if not rs:
            return z
        r = np.concatenate(rs)
        if float(np.max(np.abs(r))) <= CONVERGENCE_MM:
            return z
        z = shape.normalise(z + pinv @ (-r))
    return z


def _restore(piece: PieceProblem, per_size, shape: RuleShape, z: np.ndarray,
             rounds: int = 4) -> np.ndarray:
    """Pull a trial point back onto the constraint manifold, by the shortest way.

    🚨 **Without this the line search can never accept anything.** The KKT step is tangential:
    it satisfies the LINEARISED constraints, and the composition is bilinear, so leaving the
    manifold costs O(t²) — measured on the test piece, a step of t=0,03 already put the merit
    at 30 000 against a starting 800, and every halving still failed. The solver would sit at
    its seed for forty iterations and report it as an answer.

    The correction is the minimum-norm Newton step on the residual alone, `δ = J⁺(−r)`,
    applied a few times. It moves the point as little as possible, so the tangential progress
    the KKT step just made is kept while feasibility comes back.

    The Jacobian is built ONCE and reused for the later rounds — a chord method. Rebuilding
    it each round costs four field Jacobians a time and buys a convergence rate nobody needs
    here: the correction is already tiny by construction.
    """
    jac = None
    for _ in range(rounds):
        fields = shape.fields(z)
        rs, need = [], jac is None
        b = _composition_matrix(shape, z) if need else None
        rows = []
        for t_i, t in enumerate(per_size):
            if need:
                j_t, r_t = field_jacobian(piece, per_size[t], fields[t_i])
                if j_t.size:
                    rows.append(j_t @ b[t_i * shape.n_field:(t_i + 1) * shape.n_field])
                    rs.append(r_t)
            else:
                r_t = _residual_vector(piece, per_size[t], NoReduction(shape.n_turns),
                                       fields[t_i])
                if r_t.size:
                    rs.append(r_t)
        if not rs:
            return z
        if need:
            jac = np.vstack(rows)
        r = np.concatenate(rs)
        if float(np.max(np.abs(r))) <= CONVERGENCE_MM:
            return z
        delta, *_ = np.linalg.lstsq(jac, -r, rcond=None)
        z = shape.normalise(z + delta)
    return z


def _coupled_energy(shape: RuleShape, z: np.ndarray, h_block: np.ndarray,
                    w: Weights) -> float:
    """½ dᵀHd over all sizes + the leak penalty + the ridge. What the solve minimises."""
    fields = shape.fields(z).ravel()
    leak = z[shape.n_dir + shape.n_amp:]
    return float(0.5 * fields @ (h_block @ fields)
                 + 0.5 * w.leak * (leak @ leak)
                 + 0.5 * w.ridge * (z @ z))


def _coupled_merit(piece: PieceProblem, per_size, shape: RuleShape, z: np.ndarray,
                   h_block: np.ndarray, w: Weights, mu: float = None) -> float:
    """Energy plus a hard price on infeasibility.

    The price is not a taste: the contract gate is 0,1 mm and the energy of a real piece is
    of order 10⁻⁸, so anything less than an enormous multiplier would let the solver buy
    smoothness with millimetres of POM error. `MERIT_MU` is set so one millimetre of
    violation costs more than any reachable amount of bending.
    """
    fields = shape.fields(z)
    worst = 0.0
    for t_i, t in enumerate(per_size):
        r = _residual_vector(piece, per_size[t], NoReduction(shape.n_turns), fields[t_i])
        if r.size:
            worst = max(worst, float(np.max(np.abs(r))))
    return _coupled_energy(shape, z, h_block, w) + (MERIT_MU if mu is None else mu) * worst


def _coupled_report(piece, shape, sizes, z, diagnosis, per_size_diag, per_size, success,
                    converged, iterations, kkt_deficient, message) -> CoupledReport:
    d, a, leak = shape.unpack(z)
    fields = shape.fields(z)
    residuals, points, leak_mm = {}, {}, {}
    worst = 0.0
    for t_i, t in enumerate(sizes):
        r = _residual_vector(piece, per_size[t], NoReduction(shape.n_turns), fields[t_i])
        residuals[t] = _named(per_size[t], r)
        worst = max(worst, max((abs(v) for v in residuals[t].values()), default=0.0))
        points[t] = piece.deform(fields[t_i].reshape(shape.n_turns, 2))
        per_point = np.linalg.norm(leak[t_i].reshape(shape.n_turns, 2), axis=1)
        leak_mm[t] = (float(np.sqrt(np.mean(per_point ** 2))), float(per_point.max()))

    if not converged and not message:
        if worst <= CONTRACT_GUARD_MM:
            message = (f'Feasible ({worst:.2e} mm worst residual) but not stationary after '
                       f'{MAX_ITERATIONS} iterations: the energy was still improving, so the '
                       f'field satisfies every target but may not be the smoothest one that '
                       f'does.')
        else:
            message = (f'Gauss-Newton stopped at {MAX_ITERATIONS} iterations with a worst '
                       f'residual of {worst:.6f} mm.')
    if kkt_deficient:
        message = (f'{message} The KKT system was rank-deficient at least once; the step '
                   f'was taken in least squares (minimum norm).').strip()
    conflicts = sorted({f'{t}·{n}' for t, dg in per_size_diag.items()
                        for n in dg.conflicting})
    if conflicts:
        message = (f'{message} Contradictory constraints inside a size: '
                   f'{", ".join(conflicts)}.').strip()
    return CoupledReport(piece=piece.name, rank=shape.rank, success=success,
                         converged=converged, iterations=iterations, diagnosis=diagnosis,
                         per_size_diagnosis=per_size_diag,
                         residuals_mm=residuals, points=points, directions=d,
                         amplitudes=a, leak_mm=leak_mm, message=message)


def _diagnose_coupled(piece: PieceProblem, per_size, shape: RuleShape,
                      z: np.ndarray) -> Diagnosis:
    """B4 · QR of the JOINT system, which is not the four single-size ones stacked.

    🔑 **Coupling creates redundancy that did not exist before, and the diagnosis has to name
    it.** A FIXED measurement is one row per size when the sizes are independent — four rows,
    all of full rank. Under a shared direction those four rows say nearly the same thing:
    «this measurement does not move», applied to `amplitude[t] · direction`, differs between
    sizes only by the scalar `amplitude[t]`, so the later ones add nothing. Reported as
    redundant, by name and by size, rather than left to look like a well-posed system
    carrying four times the information it has.
    """
    b = _composition_matrix(shape, z)
    fields = shape.fields(z)
    rows, names, rhs = [], [], []
    for t_i, t in enumerate(per_size):
        j_t, r_t = field_jacobian(piece, per_size[t], fields[t_i])
        if not j_t.size:
            continue
        rows.append(j_t @ b[t_i * shape.n_field:(t_i + 1) * shape.n_field])
        rhs.append(-r_t)
        names += [f'{t}·{n}' for c in per_size[t] for n in c.row_names()]
    if not rows:
        return Diagnosis(shape.size, 0, 0, shape.size, (), (), ())
    # 🚨 The STRUCTURAL columns only — directions and amplitudes, never the leak.
    #
    # The leak gives every size its own private unknowns, so with it in the picture every
    # per-size row is independent again and the diagnosis would report a well-posed system
    # with no redundancy at all. That is true of the solve and useless as a diagnosis: the
    # question B4 asks is whether the RULE is over-determined or contradictory, and the leak
    # exists precisely to absorb the answer. Measured: a FIXED POM across three sizes comes
    # out rank 3 with the leak columns in, and rank 1 — two redundant rows, named — without.
    j = np.vstack(rows)[:, :shape.n_dir + shape.n_amp]
    b_vec = np.concatenate(rhs)

    scale = np.linalg.norm(j, axis=1)
    scale[scale == 0.0] = 1.0
    a = j / scale[:, None]
    b_vec = b_vec / scale
    singular = np.linalg.svd(a, compute_uv=False)
    rank = int(np.sum(singular > (singular[0] * RANK_TOL))) if singular.size else 0

    basis, basis_rhs = [], []
    redundant, conflicting = [], []
    tol = max(RANK_TOL, 1e-12) * max(1.0, float(singular[0])) * 10
    for i, name in enumerate(names):
        v, rv = a[i].copy(), float(b_vec[i])
        for q, qr in zip(basis, basis_rhs):
            proj = float(v @ q)
            v -= proj * q
            rv -= proj * qr
        norm = float(np.linalg.norm(v))
        if norm <= tol:
            (conflicting if abs(rv) > 1e-7 else redundant).append(name)
            continue
        basis.append(v / norm)
        basis_rhs.append(rv / norm)

    return Diagnosis(n_unknowns=shape.n_dir + shape.n_amp, n_rows=len(names), rank=rank,
                     dof=shape.n_dir + shape.n_amp - rank, redundant=tuple(redundant),
                     conflicting=tuple(conflicting),
                     components=_components([c for t in per_size for c in per_size[t]], j))
