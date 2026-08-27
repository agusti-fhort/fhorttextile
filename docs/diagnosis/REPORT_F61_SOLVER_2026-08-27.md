# REPORT F6.1 — Grading solver v2: core and bench

**Date:** 2026-08-27 · **Thread:** F6.1 · **Pattern:** B (build) · **Language:** English, per brief
**Bench:** model 1383 (`TRV-SS27-0001 · 837 VESTIT`) · `PatternFile#20` v3 · `GradingVersion#201` (v9, approved 24/08)
**Code:** [`engine/grading_solver.py`](../../backend/fhort/patterns/engine/grading_solver.py) · [`tests_grading_solver.py`](../../backend/fhort/patterns/tests_grading_solver.py) · [`ops/rosetta/exam_curves.py`](../../ops/rosetta/exam_curves.py) · [`ops/rosetta/exam_solver.py`](../../ops/rosetta/exam_solver.py)
**Input bench:** [`ops/rosetta/parity_837.json`](../../ops/rosetta/parity_837.json) (F6-PRE, 27/08)

> **Boundaries kept.** Database read-only (`SELECT` on `fhort` for `PatternPOM` and
> `GradedSpec`). No migration, no `systemctl`, no restart — the new module is on no request
> path and is imported from nowhere in the product. No `GradedSpec`, `GradingVersion` or
> writer touched. Tests run on the new file only. Own worktree `f61-grading-solver`, no push.

---

## 0 · Verdict in six lines

1. ✅ **FASE A passes, and not narrowly.** Over 7 060 curve points of the Montse field, the
   similarity-frame model reproduces every one to **0,0020 mm** — the rounding of the DXF
   itself. **D-INV-3 goes from adopted hypothesis to measured fact**, and the unknowns of the
   solver are the turn points: 56 for the front, not 996.
2. ✅ **The POM gate passes with nine orders of magnitude to spare.** Every constrained
   measurement comes back at its target to **≤ 3,0 · 10⁻¹⁰ mm** across 40 piece × size × POM
   rows, all converged. The gate was ≤ 0,1 mm.
3. ✅ **The controls hold.** Collar and placket, given only FIXED constraints, return the
   **exactly zero** field; the QR diagnosis names an injected conflict by row; five deliberate
   mutations of the solver each turn the test suite red.
4. 🚨 **The vertex-level metric is far from the phase criterion, and the reason is not the
   one that was expected.** Mean error 7,79 mm against a 0,5 mm phase criterion. It is **not**
   mainly missing information: feeding the solver every POM the bank can measure moves it only
   to 6,08 mm (−22 %). It is the regulariser.
5. 🚨 **And the field says what the regulariser should have been.** Montse's displacement is
   **sparse in first differences** — 5 of 28 jumps carry 63 % of the total variation on the
   front — while this solver minimises *second* differences, which in her field are large and
   dense. The prior is fighting the data. On the sleeve the structure is exact: her field is
   **piecewise-affine in arc length with 4 blocks, to 0,143 mm**.
6. 🚨 **But the body pieces are not a boundary problem at all.** Six affine blocks along the
   loop still leave 4,8 mm (front) and 6,9 mm (back). Their grading is organised by slash lines
   **across** the piece, and no boundary-only regulariser can express that. This is the design
   input for F6.2, and it is a bigger finding than the error number.

---

## 1 · A deviation from the brief, declared up front

**`scipy` is not in the venv.** The brief stated it was; it is not
(`/var/www/ftt-staging/backend/venv` has `numpy 2.5.1` and no `scipy`; the only `scipy` on the
machine is in `/root/n2_gym/venv`, the N2 gym scratchpad).

Nothing was installed. Installing into the venv that the live gunicorn runs from is a
deployment act, and agents do not deploy (`CLAUDE.md`, Governance).

**The core uses `numpy` only**, and this is not a workaround but the better answer:

- the problems are tiny — ≤ 56 unknowns, ≤ 13 constraint rows, dense — so the KKT solve, the
  least-squares fallback and the rank work are all one `numpy` call each;
- `numpy` is already a **declared dependency** (`requirements.lock:37`) and already imported by
  `patterns/recognition/`, so nothing new enters the backend;
- `engine/` today imports nothing heavier than `ezdxf`. Putting `scipy` in it for this would be
  the first heavy dependency in the motor, bought for no measurable gain.

If F6.2 needs sparse factorisation or a proper QP with inequalities, that is the moment to ask
Agus for `scipy` — with a reason, and as a deliberate change to `requirements`.

---

## 2 · FASE A — the entry gate

### 2.1 · The test

For each piece × size, every curve point of the base is written in the local frame of its own
turn-to-turn segment (origin at the start turn, axes along and across the chord, scaled by the
chord), then rebuilt in the frame that same segment has at size T **using the turn points
Montse actually drew**. The residual is the distance to the point she actually drew.

### 2.2 · Result

| piece | segments | curve pts (4 sizes) | mean | p95 | max |
|---|---:|---:|---:|---:|---:|
| 837.CUELLO | 10 | 2 224 | 0,0000 | 0,0000 | 0,0000 |
| 837.DELANTERO | 28 | 1 880 | 0,0006 | 0,0012 | 0,0018 |
| 837.ESPALDA | 24 | 1 752 | 0,0006 | 0,0012 | 0,0020 |
| 837.MANGA | 9 | 1 084 | 0,0007 | 0,0013 | 0,0018 |
| 837.TAPETA | 8 | 120 | 0,0000 | 0,0000 | 0,0000 |
| **global** | | **7 060** | **0,0004** | | **0,0020** |

Histogram: 89,4 % below 0,001 mm, the remaining 10,6 % below 0,005 mm, **nothing above**.

### 2.3 · The probe discriminates — which is the part that makes the number mean anything

A residual of zero from a probe that can only ever confirm itself is worth nothing. Four rival
models, same data, same code path:

| model | mean | p95 | max |
|---|---:|---:|---:|
| **similarity** (the hypothesis) | **0,0006** | **0,0013** | **0,0020** |
| lerp along the chord | 0,3342 | 1,7272 | **3,5100** |
| lerp along the vertex index | 0,8274 | 3,0535 | **25,4315** |
| rigid translation by the segment start | 3,9379 | 16,6407 | **51,1030** |
| similarity with its two axes swapped | 112,18 | 281,91 | **471,17** |

The nearest rival is **1 750× worse**. Collar and placket are excluded from this comparison
because their field is identically zero and cannot discriminate between any two models.

### 2.4 · Verdict

**PASS.** D-INV-3 is fixed. The unknowns are the turn points; curves are a consequence, not a
modelling choice. This is also what makes the rest cheap: the front is a 56-unknown problem.

⚠️ **One consequence that shapes the core:** the map from turn displacements to *curve*
positions is non-linear (the frame rotates and scales with its endpoints), so any target that
touches a curve point is a non-linear constraint. Hence Gauss-Newton, not a single linear solve.

---

## 3 · FASE B — the core

`backend/fhort/patterns/engine/grading_solver.py`, 0 Django imports, `numpy` only.

### 3.1 · Problem model (B1)

`PieceProblem` = base loop + per-vertex kind (turn/curve) + grain. Unknowns = 2 per turn point.
`deform(d)` maps turn displacements to the whole loop through the FASE A similarity rebuild.
`AttachedPoint` is the first-class answer to the layer-14 problem inherited from F6-PRE: a POM
anchor that rides on the loop without being one of its vertices, pinned by (edge, t) — the same
carrier the Rosetta used, so a value measured here and a value measured there mean the same.

**Constraint classes:**

| class | rows | linear? | meaning |
|---|---:|---|---|
| `PomDelta` | 1 | no | the measurement must read `base + delta` |
| `FixedPom` | 1 | no | hard delta zero (C2-bis) — its own class, see below |
| `Anchor` | 2 | yes | a turn point that does not move; closes the translation gauge |
| `GrainDirection` | 1 | yes | zero mean rotation of the field; closes the rotation gauge |

🔑 **`PomDelta` takes the DELTA, never the fitxa's absolute value.** At the 837 the pattern and
the fitxa already disagree at the base size (up to 30,5 mm on EK, F6-PRE §4). Feeding the
absolute value would order the solver to deform the base size to close a gap that grading never
opened. What GV201 v9 actually says is the increment, and that is what is taken.

🔑 **`FixedPom` is not `PomDelta(delta=0)`** because it is a different statement about the
garment: a LINEAR rule with increment zero says *this size happens not to grow here*; FIXED says
*this measurement is not a function of size*. F6-PRE verified 7 of 8 on the bench, six of them
on pieces that **do** grade — which is the case that means anything.

**Fold/mirror reduction: interface only, and deliberately.** `Reduction` is a Protocol with
`NoReduction` as the identity. The 837 has **no piece on the fold** (`has_fold` False on all
five), so there is nothing here to exercise an implementation against, and an unexercised
implementation is a guess with tests around it. It lands in F6.2. Not one speculative line.

### 3.2 · Diagnosis before solving (B2)

`diagnose()` runs before every solve and reports `{unknowns, rows, rank, DoF, redundant[],
conflicting[], components[]}` **by row name**.

Redundant and conflicting are the same algebraic event seen from two sides, and a residual norm
cannot tell them apart: a row that adds no rank repeats something already said; if on top of
that its right-hand side disagrees with what earlier rows fixed, it **contradicts**. Separated
with modified Gram-Schmidt over the rows in order, carrying the right-hand side along.

QR diagnosis of the 837 under the C1 constraint set:

| piece | unknowns | rows | rank | DoF | components |
|---|---:|---:|---:|---:|---:|
| 837.CUELLO | 20 | 4 | 4 | 16 | 1 |
| 837.DELANTERO | 56 | 8 | 8 | **48** | 1 |
| 837.ESPALDA | 48 | 5 | 5 | **43** | 1 |
| 837.MANGA | 18 | 2 | 2 | **16** | 1 |
| 837.TAPETA | 16 | 4 | 4 | 12 | 1 |

No redundant rows, no conflicts. **And the DoF column is the headline of this whole report:**
the front is pinned by 8 numbers and free in 48 directions. Whatever fills those 48 directions
is not the data — it is the regulariser.

`components` is always 1 and says so: on a closed loop the smoothing stencil links every turn
point to its two neighbours all the way round. It is reported anyway, because a partition that
silently always returns one bucket is indistinguishable from one that is broken.

### 3.3 · The solve (B3) and the regulariser — a declared decision

Gauss-Newton; each iteration is one equality-constrained QP solved through its KKT system,
relinearised because the curve rebuild is non-linear. Singular KKT falls back to least squares,
which picks the minimum-norm step instead of refusing.

    E(d) = w_bend · Σ ‖second difference of d along the loop‖²    (default 1.0)
         + w_stretch · Σ ‖first difference of d‖²                  (default 0.0)
         + w_ridge · Σ ‖d‖²                                        (default 1e-8, conditioning)

Both stencils are built in **arc length**, not vertex index: turn points are unevenly spaced
(a corner and the four micro-turns of an armhole are not the same distance apart) and an
index-space stencil would quietly make crowded regions stiffer than open ones.

**This is the character of the motor and it is written down so it can be argued with.**
Minimising bending subject to equality constraints makes the displacement interpolate affinely
in arc length between constrained points. §5 measures how well that matches the craft. It does
not match well, and §5.3 says what to replace it with.

### 3.4 · Output (B4)

`SolveReport{piece, success, converged, iterations, diagnosis, residuals_mm (named),
displacement, points, message}`.

**`success` and `converged` are two different words on purpose.** `success` means the solve ran
and produced a field — it is True on an underdetermined piece, which has an answer, just not a
unique one. `converged` means every hard residual reached tolerance — it is False when the
targets contradict each other. Collapsing them into one boolean is how a solver reports
«failed» for a piece it solved perfectly and «ok» for one it did not. No exception is swallowed:
an unimplemented measurement method raises with its own name in the message.

### 3.5 · Partition (B5)

No constraint in this model crosses a piece, so the global problem is block-diagonal by
construction and `solve_all` solves each piece separately: a bigger KKT matrix would buy nothing
and a joint diagnosis would be less specific. The moment `SewRelation` becomes a constraint this
stops being true, and that is F6.2.

---

## 4 · FASE C — the exam

### 4.1 · What was fed in

Per piece: the POMs the F6-PRE Rosetta put in parity, the anchor at Montse's own zero-displacement
vertex, and the grain.

| piece | targets | anchor |
|---|---|---|
| CUELLO | E7 (FIXED) | vertex 0 |
| DELANTERO | B (LINEAR), F (LINEAR), EK, EK1, SLT (FIXED) | vertex 242 |
| ESPALDA | G1, EK2 (FIXED) | vertex 0 |
| MANGA | J1 (LINEAR) | **none — open gauge** |
| TAPETA | U (FIXED) | vertex 0 |

The sleeve has no anchor because **Montse's field has no still point on it** (F6-PRE §2). The
solver does not fail on that: the diagnosis reports the open gauge and the regulariser returns
the minimum-bending member of the family. The vertex metric is therefore also reported after a
best-fit rigid motion, so the sleeve is scored on shape and not on placement.

🚩 **An ambiguity in the brief, resolved by running both.** The brief lists EK both inside «the
ten in parity» and among the exclusions («recipe under review»). It cannot be both. The primary
run uses all ten; a sensitivity run drops EK. **Dropping EK moves the front's field by up to
4,30 mm at XL and changes no residual** — so EK is load-bearing for the shape and the ambiguity
is worth Agus resolving before F6.2 uses this bench as a target.

### 4.2 · POM level — the contract · **PASS**

| | |
|---|---|
| rows (piece × size × POM) | 40 |
| worst residual | **2,978 · 10⁻¹⁰ mm** |
| gate | 0,1 mm |
| converged | 40 / 40 |

Every target hit, on all three constraint sets of the information ladder (worst across all
three: 7,74 · 10⁻¹⁰ mm). The solver does what it is told, exactly.

### 4.3 · Vertex level — the character · reported, **not** gated

| piece | size | mean | p95 | max | mean\* | max\* |
|---|---|---:|---:|---:|---:|---:|
| CUELLO | all | 0,000 | 0,000 | 0,000 | 0,000 | 0,000 |
| DELANTERO | XS | 1,911 | 4,814 | 5,689 | 1,897 | 5,711 |
| DELANTERO | M | 5,966 | 10,256 | 16,965 | 4,835 | 13,280 |
| DELANTERO | L | 12,021 | 20,495 | 34,608 | 9,721 | 27,165 |
| DELANTERO | XL | 16,532 | 28,204 | 42,931 | 13,419 | 32,723 |
| ESPALDA | XS | 5,490 | 10,018 | 10,082 | 5,559 | 10,344 |
| ESPALDA | M | 10,704 | 20,069 | 23,077 | 11,057 | 19,964 |
| ESPALDA | L | 21,398 | 40,140 | 46,156 | 22,082 | 39,897 |
| ESPALDA | XL | 31,014 | 50,249 | 60,621 | 31,850 | 52,807 |
| MANGA | XS | 0,778 | 1,581 | 1,651 | 0,700 | 1,297 |
| MANGA | M | 4,361 | 6,484 | 7,723 | 4,246 | 8,119 |
| MANGA | L | 8,804 | 12,940 | 15,445 | 8,565 | 16,276 |
| MANGA | XL | 13,214 | 19,480 | 23,170 | 12,880 | 24,264 |
| TAPETA | all | 0,000 | 0,000 | 0,000 | 0,000 | 0,000 |

\* after removing the best-fit rigid motion.

### 4.4 · C3 control · **PASS**

Collar and placket, constrained only by FIXED, return a solved field with max |d| **exactly
0,000 · 10⁰ mm**, matching Montse's own null field on those two pieces to the same exactness.

### 4.5 · Exclusions, with reason

| POM | reason |
|---|---|
| **D** | grading disagreement pending Montse (+0,50 cm/size on the field vs +3,00 asked by the fitxa, F6-PRE §4.1) |
| **A, C, E, E1, E5, S2** | no sewing line on the bench; carrier spread 0,93–3,45 mm exceeds tolerance (NOT RESOLVABLE, F6-PRE §3.2) |
| **S, S2** | method `vora`. The solver models the **cut loop only**, so the path along the boundary between two sewing-line anchors does not exist in its geometry. Refused by name rather than approximated by the straight distance, which would measure something else and report a number anyway. |
| **J** | no `PatternPOM` recipe on the 1383 (anchoring gap, not a data gap) |
| **I, SF** | measurable but outside the parity set (DEVIATED 1,53 and 1,25 mm). Kept out so the exam measures the solver, not a known disagreement. |

---

## 5 · Divergence analysis — the part that decides F6.2

### 5.1 · It is not, mostly, an information gap

The same solver, three constraint sets of increasing richness. `with_layer_14` is what the exam
would look like the day Montse sends the nest with layer 14.

| set | targets | vertex mean | vertex max | worst POM residual |
|---|---|---:|---:|---:|
| `contract` | 10 | **7,788 mm** | 60,621 | 2,98 · 10⁻¹⁰ |
| `with_layer_14` | 15 | **6,079 mm** | 58,032 | 7,74 · 10⁻¹⁰ |
| `all_measurable` | 17 | **6,115 mm** | 52,418 | 6,80 · 10⁻¹⁰ |

Per piece at XL (mean / max):

| piece | contract | with_layer_14 | all_measurable |
|---|---|---|---|
| DELANTERO | 16,53 / 42,93 | 12,87 / 43,01 | 12,87 / 43,01 |
| ESPALDA | 31,01 / 60,62 | 21,79 / 58,03 | 21,60 / 52,42 |
| MANGA | 13,21 / 23,17 | 13,21 / 23,17 | 14,03 / 21,13 |

**Every target the bench can supply buys 22 %, and leaves the result 12× above the phase
criterion.** The remaining gap belongs to the regulariser.

### 5.2 · The growth budget explains the table, and without it the table reads wrong

| piece | LINEAR targets | FIXED | growth asked at XL | solved mean \|d\| | Montse mean \|d\| | corr |
|---|---:|---:|---:|---:|---:|---:|
| DELANTERO | 2 | 3 | 140,0 mm | **31,01** | **31,44** | **+0,846** |
| ESPALDA | **0** | 2 | **0,0 mm** | **0,00** | 31,01 | −0,127 |
| MANGA | 1 | 0 | 7,5 mm | 3,29 | 15,78 | +0,857 |

- **The back is told nothing about growing.** Both of its parity POMs are FIXED, because every
  POM that carries its growth (E1, S2, SF) was excluded for want of a sewing line. A solver that
  returns a zero field there is not failing — it is obeying. Its 31 mm «error» is Montse's own
  field magnitude.
- **The front is told the right amount and puts it in the wrong place.** Mean displacement
  31,01 mm against her 31,44 — **1,4 % off in magnitude** — with correlation +0,846. The error
  splits 12,14 mm along the loop and 9,03 mm across it. The budget is right; the distribution is
  not.

### 5.3 · What shape her field actually has — the evidence for the next prior

Measured on Montse's field alone, no solver involved, at XL:

| piece | turns | Σ\|Δd\| | top-5 jumps | share | \|Δd\| < 2 mm | Σ\|Δ²d\| | blocks needed (cyclic, affine in arc) |
|---|---:|---:|---:|---:|---:|---:|---|
| DELANTERO | 28 | 309,9 | 195,7 | **63 %** | 14/28 | 539,0 | **>6** (k=6 still 4,81 mm) |
| ESPALDA | 24 | 309,0 | 180,7 | **58 %** | 10/24 | 509,1 | **>6** (k=6 still 6,88 mm) |
| MANGA | 9 | 119,6 | 105,5 | **88 %** | 2/9 | 172,9 | **k=4 → 0,143 mm** |

Two findings, and they point in different directions:

🚨 **The field is sparse in FIRST differences and dense in SECOND differences.** Five of
twenty-eight jumps carry 63 % of the front's total variation, and half the jumps are under 2 mm
— the signature of a piece cut along a few lines and spread. This solver minimises the *second*
difference, which in her field sums to 539 with a maximum of 52 mm. **The prior is fighting the
data**, and that is a fixable mistake: a sparsity-promoting (total-variation / L1) penalty on the
first difference prefers piecewise-constant displacement, which is what slash-and-spread is.

🚨 **But sparsity alone will not save the body pieces.** On the sleeve, her field is *exactly*
piecewise-affine in arc length — **four blocks, 0,143 mm** — so a boundary regulariser can nail
it. On the front and back, six blocks still leave 4,8 and 6,9 mm. Their grading is not a
one-dimensional object along the boundary at all: it is organised by slash lines **across** the
piece, and **no boundary-only regulariser can express that**, whatever its penalty. The body
prior needs an interior model.

That is the single most consequential result of this sprint, and it was not in the brief's
expectations: the vertex criterion is not reachable by tuning, on the pieces that matter.

---

## 6 · FASE D — tests

`backend/fhort/patterns/tests_grading_solver.py`, 15 tests, all synthetic geometry, no database.
`Ran 15 tests · OK`. `manage.py check` clean.

| what it pins | test |
|---|---|
| QR names an injected conflict | `test_injected_conflict_is_named` |
| a redundant row is named and is *not* a conflict | `test_redundant_row_is_named_and_is_not_a_conflict` |
| FIXED moves zero while the piece grows | `test_fixed_pom_moves_zero` |
| open gauge is reported, not raised | `test_open_gauge_is_reported_not_raised` |
| anchor + grain remove exactly 3 DoF | `test_gauge_closes_the_rigid_null_space` |
| a simple `pom_delta` solves exactly | `test_simple_pom_delta_is_exact` |
| `success` ≠ `converged` is exposed | `test_success_and_converged_are_distinguished` |
| `vora` is refused by name, not approximated | `test_vora_is_refused_by_name` |
| curves follow their segment frame | `test_curves_follow_their_segment_frame` |
| pieces stay independent | `test_solve_all_keeps_pieces_independent` |

**Every test was seen red.** Five mutations of the core, each reverted:

| mutation | tests turned red |
|---|---:|
| conflict treated as redundant (right-hand side ignored) | 2 |
| `FixedPom` residual forced to zero | 1 |
| grain gauge made a no-op | 3 |
| curves translated by their segment start (the model FASE A refuted) | 1 |
| `converged` hard-wired to True | 1 |

---

## 7 · What this opens — brief for F6.2

1. 🚨 **The regulariser is the work, not the solver.** Two changes, in this order:
   **(a)** total-variation penalty on the first difference along the loop (measured to be the
   right shape on the sleeve, k=4 → 0,143 mm); **(b)** an **interior** deformation model for the
   body pieces — slash lines, not boundary smoothing — because §5.3 shows no boundary prior can
   reach them. (b) is a design question for Agus and Montse before it is code: *what does the
   837's front actually get slashed along?*
2. 🚨 **The vertex criterion of ≤ 0,5 mm should be re-scoped before it is ratified.** It is
   reachable on a sleeve and, on this evidence, not reachable on a front by any boundary-only
   motor. Either the criterion becomes per-piece-class, or the phase commits to the interior
   model.
3. **Layer 14 is still the cheapest single unlock**, but now with a measured price: it is worth
   22 % of the vertex error, not the whole gap. Ask Montse for the nest with layer 14 anyway —
   it also converts six POMs from NOT RESOLVABLE to measurable.
4. **`vora` needs the sewing loop as solver geometry.** Two POMs (S, S2) are unreachable until
   the solver carries more than the cut loop.
5. **Fold reduction** (`Reduction` protocol, `NoReduction` today) needs a piece on the fold to be
   built against. The 837 has none.
6. **`SewRelation` as a constraint** is what makes `solve_all`'s block-diagonal assumption false
   and the component partition real. Until then the partition honestly reports one bucket.
7. **Ask Agus:** is EK in or out? It moves the front by 4,30 mm at XL and the brief says both.
8. **Ask Agus:** `scipy` into `requirements` — only if F6.2 needs sparse/QP work. Not yet.
