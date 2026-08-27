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

## A0 · AMENDMENT (Agus, 27/08, same day) — READ THIS FIRST

The bank was **regenerated** from `837 CORS 194 VESTIT M3-4 ESCALAT COSTRURA.DXF`
(md5 `857f00057bbd26ff4cfb8cf1b95fda69`), which carries **layer 14**. That closes the gap
§7.3 called "the cheapest single unlock", and it moves more than that section predicted.

### A0.1 · What was verified before anything was built on it

| | result |
|---|---|
| **A6 · the new bank supersedes the old cleanly** | the CUT contour is identical to the 26/08 bank across all 25 piece × size combinations, **0,000000000 mm**. Nothing measured before is invalidated, only extended. |
| **A5 · the sewing base ≡ the 1383's master pattern** | **0,000000000 mm** on all five pieces. 🔑 **This retires the transport**: every POM anchor has a native homologue at every size, by its own index. |
| **A1–A4 on both loops** | 55 checks, none red. |
| declared sewing counts (651/475/459/325/47) | ours **+1** — the duplicated closing vertex, which the reader strips. 650/474/458/324/46. |
| `… PER 3d.DXF` | 🚩 **not on the server.** It is archived reference and does not enter the solver, so this did not block — but the amendment's claim that it is identical to the sewing line **could not be verified here**. |

🔑 **CONVENCIÓ-1 extends to the second loop, and the amendment confirms it from outside.**
The sewing loop's origin is **not** its own argmin of Y: it is the point nearest the cut
loop's origin. All five origins Agus verified locally — 207 · 30 · 251 · 47 · 3 — come out of
that rule; the own-argmin rule gets one wrong (TAPETA, 2 instead of 3). The rule was derived
by measurement in F6-PRE and now has independent confirmation.

### A0.2 · FASE A now runs on both contours, and passes on both

| loop | curve points | mean | p95 | max |
|---|---:|---:|---:|---:|
| cut | 7 060 | 0,0004 | 0,0012 | **0,0020** |
| **sewing** | 7 492 | 0,0003 | 0,0009 | **0,0016** |

The hypothesis holds **where the measurements are actually taken**, which is where it had to
hold. The rival models are unchanged and still 1 750× worse.

### A0.3 · The Rosetta, redone with native anchors

**PARITAT 15/21 · DESVIAT 5 · NO MESURABLE 1 · NO RESOLVABLE 0.** The five that could not be
decided (A, C, E, E1, E5) all enter parity, and **twelve POMs reproduce the fitxa's grading to
0,00 mm exactly**. The FIXED positive control gives exact zero on 7 of 8.

What is left deviating is a clean picture: **D** (75,00 mm, still pending Montse — now
confirmed a third time, with native anchors) · **S** (2,30) and **S2** (1,80), both `vora`, with
the same profile front and back — which is what you would expect if the fitxa's armhole rule is
what is wrong, not the pattern · **I** (1,50, a constant +5 %) · **SLT** (0,51, marginal).

All the carrier machinery — three carriers, the error bar, the NOT RESOLVABLE verdict —
was **deleted, not disabled**. It existed for a problem that is gone, and leaving two paths to
one question is how someone later takes the wrong one. What it measured is in the F6-PRE act.

### A0.4 · The solver had to learn that a piece has two contours

`G1` measures the seam allowance **between** the loops, so the C1 set cannot be expressed on a
single loop. `PieceProblem.loop_starts` now marks each closed contour, and every cyclic wrap —
segments, attached-point edges, the smoothing stencil — closes inside its own.

🔑 **And they must be coupled, which is measured, not assumed.** The two loops have exactly the
same turn count on all five pieces (28/28 · 24/24 · 10/10 · 9/9 · 8/8), and in Montse's field
the sewing displacement matches its facing cut displacement to **0,19 mm mean at M and 0,51 at
XL**, against field magnitudes of 11 and 32 mm. Left uncoupled the solver is not merely wrong,
it is **misleading**: every anchor is on the sewing loop, so the cut loop collects no constraint
and drifts wherever the regulariser prefers, while the exam reports a vertex error that is an
artefact of a model nobody believes. Measured both ways:

| piece | size | uncoupled mean / max | coupled mean / max |
|---|---|---:|---:|
| DELANTERO | XS | 3,20 / 10,61 | **0,90 / 2,02** |
| DELANTERO | XL | 26,02 / 61,05 | **13,41 / 42,33** |
| ESPALDA | XL | 28,76 / 60,38 | **22,75 / 53,57** |
| MANGA | XL | 14,65 / 23,86 | **13,82 / 20,95** |
| **global** | | 8,776 / 61,054 | **6,177 / 53,568** |

−30 % on the mean, and **it costs nothing in contract terms**: the worst POM residual is
6,68 · 10⁻¹⁰ mm either way. A *soft* penalty and not a hard reduction on purpose — the match is
0,19–0,51 mm, the same order as the tolerance, so forcing equality would inject the mismatch as
error rather than let the constraints arbitrate.

### A0.5 · The exam, redone

**POM gate: PASS at 6,679 · 10⁻¹⁰ mm over 64 rows** (was 40), all converged, on 16 targets.

| piece | unknowns | rows | DoF | targets |
|---|---:|---:|---:|---|
| DELANTERO | 112 | 11 | **101** | B C SLT F E E5 EK1 A |
| ESPALDA | 96 | 7 | **89** | G1 EK2 E1 SF |
| MANGA | 36 | 3 | **33** | J1 I |
| CUELLO | 40 | 4 | 36 | E7 |
| TAPETA | 32 | 4 | 28 | U |

Vertex level, coupled: DELANTERO **XS 0,90 mm mean / 2,02 max**, XL 13,41 / 42,33 with
**correlation +0,906** and magnitude 30,97 against Montse's 31,53 — **1,8 % off**. Global mean
**6,177 mm** over 15 184 points (twice the geometry of §4.3, which covered the cut loop only).

**Exclusion arithmetic**, since the brief states the count and the exclusions separately: 21 − D
− J − EK = 18, minus **S and S2** (`metode=vora`, not implemented) = **16, of which 7 FIXED** —
exactly what the brief declares. The two kinds are listed apart in the exam because they mean
different things: D/J/EK wait on **a person**, S/S2 wait on **our code**.

### A0.6 · What A0 changes in the sections below

| section | status |
|---|---|
| §1 (scipy), §2 (FASE A), §3 (the core), §6 (tests) | **current**, and extended by A0.2 and A0.4 |
| §4 (the exam, 10 targets, one loop) | **superseded by A0.5** |
| §5.1 information ladder | **superseded** — the `with_layer_14` rung was a simulation of a thing that has now happened |
| §5.2 growth budget | **current in kind**, new numbers: the back still asks 24 mm where the front asks 338 |
| §5.3–5.4 (TV refuted, feasibility, rank two) | **current** — and A0 sharpens it: 16 targets against 101 DoF on the front is still 8 numbers' worth of data choosing 101 |
| §7 recommendations | **current**, with §7.4 (layer 14) now **done** |

🚨 **The headline of §5.4 survives A0 intact and gets stronger.** The bank went from 10 targets
to 16 and from one loop to two, and the vertex mean went 7,788 → 6,177 mm — a 21 % gain against
a 0,5 mm criterion. More measurements are not what closes this. **Fewer unknowns is.**

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
5. 🚨 **And it is not the penalty's shape either.** Her field is sparse in first differences,
   which points straight at a total-variation prior — so it was run, and **it is worse**
   (sleeve XL: 15,45 mm against 13,21 for the committed bending prior). Meanwhile **her own
   field satisfies our constraints to 0,35 mm**, so the right answer is admissible and the gap
   is entirely which member of a **48-dimensional** family the prior picks.
6. 🔑 **The fix is fewer unknowns, and the data says how few.** A piece's whole grading field is
   **rank two to ~1 mm** across its four sizes, the dominant component being one shape scaled by
   a per-size scalar (1 · 2,00 · 2,69). This sprint solves the four sizes independently and
   thereby discards the strongest structure in the data. That, not the regulariser, is F6.2.

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

Her field is **sparse in first differences and dense in second differences**: five of
twenty-eight jumps carry 63 % of the front's total variation and half the jumps are under 2 mm —
the signature of a piece cut along a few lines and spread — while this solver minimises the
*second* difference, which in her field sums to 539 with a maximum of 52 mm. The prior is
fighting the data.

The obvious inference from that is «use a total-variation penalty». **It was run, and it is
wrong.** See §5.4.

### 5.4 · Three measurements that decide what F6.2 should change

Produced by [`ops/rosetta/exam_structure.py`](../../ops/rosetta/exam_structure.py).

**(a) Montse's own field IS admissible under our constraints.** Evaluating our constraint rows
on the field she drew:

| piece | size | worst row, `contract` set |
|---|---|---:|
| DELANTERO | M | SLT = −0,324 mm |
| DELANTERO | XL | F = −0,349 mm |
| ESPALDA | M | EK2 = +0,053 mm |
| ESPALDA | XL | grain = +0,143 mm |
| MANGA | XL | grain = +2,001 mm |

Her answer satisfies the constraint set to a third of a millimetre on the body pieces. (The
sleeve's 2,0 mm is the grain gauge, and expected: it has no still point, so her field carries
0,17° of net rotation and ours is forced to carry none.) **The constraints do not exclude the
right answer.** The entire 16,5 mm gap on the front is the prior choosing a different member of
a 48-dimensional admissible family.

**(b) A total-variation prior is WORSE, not better.** IRLS on the first difference, same
constraints, same bench, run on the sleeve — the piece whose field is exactly piecewise-affine,
so the best case a sparsity prior will ever get:

| size | bending (committed) mean / max | TV-IRLS mean / max | Montse mean \|d\| |
|---|---:|---:|---:|
| M | **4,36** / 7,72 | 5,10 / 7,65 | 5,21 |
| XL | **13,21** / 23,17 | 15,45 / 22,99 | 15,78 |

The mean gets worse. The reason is plain once measured: the *structure* of her field says what
the answer looks like; it does not follow that a prior of the matching family **recovers** that
answer from **one** measurement target. With 1 constraint and 18 unknowns, no penalty can.

🔑 **So the fix is not a better penalty. It is fewer unknowns.** No prior picks the right point
out of a 48-dimensional family from 8 numbers by preferring some shape of smoothness.

**(c) And the data says exactly how few.** SVD of the four size fields of each piece — worst
error, in mm, of rebuilding all four from `k` basis fields:

| piece | k=1 | k=2 | k=3 | k=4 | component-1 coefficients (XS, M, L, XL) |
|---|---:|---:|---:|---:|---|
| DELANTERO | 6,797 | **0,840** | 0,228 | 0,000 | −0,238 · 1 · 2,004 · 2,687 |
| ESPALDA | 6,399 | **1,015** | 0,175 | 0,000 | −0,226 · 1 · 1,997 · 2,671 |
| MANGA | 2,047 | **0,277** | 0,137 | 0,000 | −0,181 · 1 · 2,013 · 3,023 |

🚨 **A piece's whole grading is rank two to ~1 mm and rank three to ~0,23 mm**, and the dominant
component is one shape scaled by a per-size scalar that steps almost linearly (1 · 2,00 · 2,69).

**This sprint solves the four sizes as four independent problems, and that throws away the
strongest structure in the data.** Four sizes × 8 rows = 32 constraints are available; they are
currently spent 8 at a time on four separate 56-unknown problems.

### 5.5 · A warning about the `with_layer_14` rung

Evaluating the enriched constraint set on Montse's own field:

| piece | size | rows that HER field violates |
|---|---|---|
| DELANTERO | XL | E = −3,554 · A = −2,420 · E5 = −1,070 mm |
| ESPALDA | XL | E1 = −2,507 mm |

Those five are exactly the NOT RESOLVABLE POMs of F6-PRE. Their targets come from the fitxa, and
**the real pattern does not meet them**. Adding them as hard constraints therefore pushes the
solver *away* from her answer. So §5.1's ladder is not «what it would look like with layer 14»
in a clean sense — it is «what it looks like when you impose targets the real pattern violates»,
and the 22 % it bought is an understatement of what a *correct* layer-14 target set would buy.

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

1. 🚨 **Couple the sizes. This is the one change with measured evidence behind it.** A
   piece's grading field is rank two to ~1 mm (§5.4c), so the four sizes are not four problems:
   they are one shape plus a per-size scalar. Solving them jointly under a low-rank field model
   pools 32 constraint rows instead of spending 8 at a time, and it is **not circular** — it
   assumes low rank, it does not borrow Montse's basis. Do this before touching the penalty.
2. 🚨 **Do NOT spend the sprint tuning the regulariser.** Total variation — the obvious
   candidate from the sparsity of her field — was measured and is *worse* (§5.4b). The gap is
   dimensional, not a matter of the penalty's shape: 8 numbers cannot select a point from a
   48-dimensional family. The complementary reduction to (1) is an **interior** model for the
   body pieces — slash lines rather than boundary smoothing — which is a design question for
   Agus and Montse before it is code: *what does the 837's front actually get slashed along?*
3. 🚨 **The vertex criterion of ≤ 0,5 mm should be re-scoped before it is ratified.** With the
   current parametrisation it is out of reach on the body pieces. It becomes plausible only
   with (1) and (2); ratify it against a parametrisation, not against a motor.
4. **Layer 14 is still worth asking for**, but §5.5 changes what it buys: the five POMs it
   would unlock carry targets that **Montse's own pattern violates by up to 3,55 mm**. Before
   they become hard constraints, find out why — the F6-PRE carrier problem, or fitxa rules that
   are wrong the way D is wrong.
5. **`vora` needs the sewing loop as solver geometry.** Two POMs (S, S2) are unreachable until
   the solver carries more than the cut loop.
6. **Fold reduction** (`Reduction` protocol, `NoReduction` today) needs a piece on the fold to be
   built against. The 837 has none.
7. **`SewRelation` as a constraint** is what makes `solve_all`'s block-diagonal assumption false
   and the component partition real. Until then the partition honestly reports one bucket.
8. **Ask Agus:** is EK in or out? It moves the front by 4,30 mm at XL and the brief says both.
9. **Ask Agus:** `scipy` into `requirements` — only if F6.2 needs sparse/QP work. Not yet.
