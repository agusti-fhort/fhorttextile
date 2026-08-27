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
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol, Sequence

import numpy as np

from .errors import PatternEngineError

MM_PER_CM = 10.0

#: Below this an edge has no direction and cannot carry a local frame.
TOL_DEGENERATE_MM = 1e-9

#: Singular values below `rank_tol * largest` count as zero when measuring rank.
RANK_TOL = 1e-9

#: Gauss-Newton stops when the largest hard residual falls below this, in mm.
CONVERGENCE_MM = 1e-9

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
    """A piece as the solver sees it: a base loop, its turn points, and its grain."""

    name: str
    base_points: tuple[tuple[float, float], ...]
    kinds: tuple[str, ...]                       # 'turn' | 'curve' per vertex
    grain: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        if len(self.base_points) != len(self.kinds):
            raise SolverError(
                f'{self.name}: {len(self.base_points)} points but {len(self.kinds)} kinds.'
            )
        if not self.turn_indices:
            raise SolverError(
                f'{self.name}: no turn points. The unknowns of this solver ARE the turn '
                f'points; a loop without any has nothing to solve for.'
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
    def segments(self) -> tuple[Segment, ...]:
        turns = self.turn_indices
        n = self.n_points
        out = []
        for k, a in enumerate(turns):
            b = turns[(k + 1) % len(turns)]
            interior, i = [], (a + 1) % n
            while i != b:
                interior.append(i)
                i = (i + 1) % n
            out.append(Segment(a, b, tuple(interior)))
        return tuple(out)

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
            if l2 <= TOL_DEGENERATE_MM:
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
        n = self.n_points
        base = np.asarray(self.base_points, dtype=float)
        i0, i1 = point.edge % n, (point.edge + 1) % n
        delta = (1.0 - point.t) * (pts[i0] - base[i0]) + point.t * (pts[i1] - base[i1])
        return np.asarray(point.base, dtype=float) + delta

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

    def measure(self, piece: PieceProblem, pts: np.ndarray) -> float:
        p = [piece.resolve(a, pts) for a in self.anchors]
        if self.method == 'recta':
            _expect(self, p, 2)
            return float(np.linalg.norm(p[1] - p[0]))
        if self.method == 'projeccio':
            _expect(self, p, 2)
            axis = self.axis or _dominant_axis(p[0], p[1])
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
        i = piece.turn_indices[self.turn_slot]
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
    diagnosis that costs one Jacobian per row turns the exam from seconds into minutes for
    a partition that, on a closed loop, is known in advance.

    ⚠️ On a closed loop the smoothing stencil already links every turn point to its two
    neighbours all the way round, so **a closed piece is always one component** and this
    never splits it. It is reported anyway because it is the thing that would change the
    moment an open boundary or a multi-loop piece arrives, and a partition that silently
    always returns one bucket is indistinguishable from one that is broken.
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

    for iterations in range(1, MAX_ITERATIONS + 1):
        j, r = _jacobian(piece, constraints, red, z)
        if j.size == 0:
            converged = True
            break
        if float(np.max(np.abs(r))) <= CONVERGENCE_MM:
            converged = True
            break
        step = _kkt_step(h, j, r, z, w)
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
    _, r = _jacobian(piece, constraints, red, z)
    residuals = _named(constraints, r)
    worst = max((abs(v) for v in residuals.values()), default=0.0)
    converged = converged or worst <= CONVERGENCE_MM

    message = ''
    if not converged:
        message = (f'Gauss-Newton stopped at {MAX_ITERATIONS} iterations with a worst '
                   f'residual of {worst:.6f} mm.')
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
    """Central differences. With ≤56 unknowns an analytic Jacobian buys speed we do not
    need and costs a class of silent sign errors we cannot afford."""
    r0 = _residual_vector(piece, constraints, red, z)
    if r0.size == 0:
        return np.zeros((0, red.n_free)), r0
    eps = 1e-6
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
    h_arc = piece.arc_spacing()                  # segment k runs from turn k to turn k+1
    h_arc = np.where(h_arc > 0, h_arc, 1.0)

    rows_b, rows_d = [], []
    for k in range(m):
        hp = h_arc[(k - 1) % m]                  # before k
        hn = h_arc[k % m]                        # after k
        # non-uniform second difference
        cm = 2.0 / (hp * (hp + hn))
        cc = -2.0 / (hp * hn)
        cp = 2.0 / (hn * (hp + hn))
        weight = math.sqrt((hp + hn) / 2.0)
        row = np.zeros(m)
        row[(k - 1) % m] += cm
        row[k] += cc
        row[(k + 1) % m] += cp
        rows_b.append(row * weight)

        row = np.zeros(m)
        row[k] -= 1.0 / hn
        row[(k + 1) % m] += 1.0 / hn
        rows_d.append(row * math.sqrt(hn))

    b = np.array(rows_b)
    dmat = np.array(rows_d)
    hm = w.bend * (b.T @ b) + w.stretch * (dmat.T @ dmat)

    # Both coordinates of a turn point share the stencil; interleave into (2m, 2m).
    full = np.zeros((2 * m, 2 * m))
    full[0::2, 0::2] = hm
    full[1::2, 1::2] = hm
    full += w.ridge * np.eye(2 * m)

    if isinstance(red, NoReduction):
        return full
    basis = np.array([red.expand(e).ravel() for e in np.eye(red.n_free)])
    return basis @ full @ basis.T


def _kkt_step(h: np.ndarray, j: np.ndarray, r: np.ndarray, z: np.ndarray,
              w: Weights) -> np.ndarray | None:
    """One KKT solve: minimise ½sᵀHs + (Hz)ᵀs subject to J s = −r."""
    n = h.shape[0]
    m = j.shape[0]
    kkt = np.zeros((n + m, n + m))
    kkt[:n, :n] = h
    kkt[:n, n:] = j.T
    kkt[n:, :n] = j
    rhs = np.concatenate([-(h @ z), -r])
    try:
        sol = np.linalg.solve(kkt, rhs)
    except np.linalg.LinAlgError:
        sol, *_ = np.linalg.lstsq(kkt, rhs, rcond=None)
    if not np.all(np.isfinite(sol)):
        return None
    return sol[:n]
