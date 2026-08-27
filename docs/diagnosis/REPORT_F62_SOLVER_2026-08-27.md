# REPORT F6.2 — Inter-size coupling: grading as a rule

**Date:** 2026-08-27 · **Thread:** F6.2 · **Pattern:** B (build) · **Language:** English, per brief
**Bench:** model 1383 · `PatternFile#20` v3 · `GradingVersion#201` (v9) · bank `parity_837.json` (A0, both loops)
**Code:** [`engine/grading_solver.py`](../../backend/fhort/patterns/engine/grading_solver.py) · [`tests_grading_solver.py`](../../backend/fhort/patterns/tests_grading_solver.py) · [`ops/rosetta/exam_rank.py`](../../ops/rosetta/exam_rank.py) · [`ops/rosetta/exam_coupled.py`](../../ops/rosetta/exam_coupled.py)

> **Boundaries kept.** Database read-only. No migration, no `systemctl`, no restart — the module
> is on no request path. No writer, `GradingVersion` or `GradedSpec` touched. Tests on the new
> and changed files only. Branch `f61-grading-solver`, no push.

> **Continued by [`REPORT_F63_RUL_2026-08-27.md`](REPORT_F63_RUL_2026-08-27.md) (same day).** §6.1
> of this report asked for the RUL of the 837; it arrived, and it answers §4's question. Nothing
> measured here is superseded — F6.3 re-runs the `apart` and rank-2 paths and reproduces 6,177
> and 7,185 exactly — but two of the *readings* are: the near-rank-2 structure is not emergent,
> it is X and Y grading on different schedules, and the front's three XS/M ratios are a fact
> about the garment rather than a doubt about the fitxa.

---

## 0 · The verdict, and it is not the one the brief hoped for

1. ✅ **The coupled solver is built, correct, and keeps the contract absolutely.** Every POM at
   its target to **≤ 5,49 · 10⁻⁷ mm** across 5 pieces × 4 sizes × 3 ranks — the gate was 0,1 mm.
   The structure is expressible: at rank ≥ 2 the **leak is exactly zero** on every piece, so the
   837 really can be graded by two shared directions with per-size amplitudes.
2. 🚨 **And it does not move the vertex metric at all.** Global mean against Montse's field:
   **6,177 mm apart (F6.1) → 7,185 at rank 2 → 6,140 at rank 3.** The phase criterion is 0,5 mm.
   Halving the free parameters bought nothing.
3. 🚨 **Rank one — the brief's actual structure — is worse, and FASE A said so first.** Global
   mean 9,19 mm against 6,18, the front alone going from 7,37 to 19,31, and it is the only rank
   that needs a leak at all (1,11 mm rms, 6,15 max on the front). Not a solver failure: the
   contract holds throughout. It is the fitxa's own targets demanding three different XS/M
   progressions on one piece, and one amplitude vector having to pick between them.
4. 🔑 **Together with F6.1 this eliminates two directions with evidence.** A different penalty
   (total variation) was measured *worse*; fewer unknowns is now measured *neutral*. The binding
   limitation was never the parameter count — F6.1 already showed Montse's answer is **inside**
   the feasible set, to 0,32 mm. What is missing is not freedom, and not smoothness.
5. 🔑 **And the CAD says what it is.** PolyPattern gives **every turn point its own rule number**
   — 28 distinct on the front, 24 on the back, 9 on the sleeve, and a single shared rule «1» on
   the collar and placket (which is exactly why those two do not grade). Grading is declared
   **per point**. The near-rank-2 structure we measured is *emergent*, not something the pattern
   carries, so there is nothing further of that kind left to exploit.
6. 🚨 **The concrete unlock is a file we do not have: the RUL of the 837.** The rule numbers are
   in the pattern; the deltas they index are in the RUL. `PatternFile#20` has none, and the only
   RUL on the bench (`PatternFile#18`) carries a single rule «1» with all deltas zero. With the
   real one, grading stops being something to infer from 16 measurements and becomes **data**.

---

## 1 · FASE A — the gate, and what it decided

Per piece and per loop, the SVD of the four non-base displacement fields over the turn points.
Energy is a ratio and the criterion is in millimetres, so **the mm column decides** — the first
version of this script decided on an energy epsilon and duly declared «rank ≤2 refuted» on a
field whose rank-2 residual is 1,0 mm.

| piece | loop | σ1 | σ2 | σ3 | σ4 | E(1) | E(2) |
|---|---|---:|---:|---:|---:|---:|---:|
| DELANTERO | cut | 286,10 | 27,57 | 3,12 | 0,43 | 0,99068 | 0,99988 |
| DELANTERO | sew | 286,29 | 27,47 | 2,96 | 0,00 | 0,99077 | 0,99989 |
| ESPALDA | cut | 281,40 | 26,85 | 3,02 | 0,41 | 0,99087 | 0,99988 |
| MANGA | cut | 80,54 | 5,72 | 0,40 | 0,20 | 0,99494 | 0,99997 |
| CUELLO, TAPETA | both | — | — | — | — | null field | |

**What k components leave behind, in millimetres:**

| piece | loop | k=1 | k=2 | k=3 | k=4 |
|---|---|---:|---:|---:|---:|
| DELANTERO | cut | **6,797** | 0,840 | 0,228 | 0,000 |
| DELANTERO | sew | 6,163 | 0,880 | 0,000 | 0,000 |
| ESPALDA | cut | 6,399 | **1,015** | 0,175 | 0,000 |
| MANGA | cut | 2,047 | 0,277 | 0,137 | 0,000 |

**Rank ≤2 holds** (1,0 mm on fields of 60 mm), so the brief's stop condition was not met.

### 1.1 · But rank ONE is refuted twice, and the second refutation is the interesting one

Geometrically it leaves 6,80 mm — thirteen times the criterion. And **the fitxa itself rules it
out**: a rank-one field grows every measurement on a piece in the same proportion, and the fitxa
does not ask for that.

| piece | XS/M ratio | POMs |
|---|---:|---|
| **837.DELANTERO** | **−0,667** | A, B, C |
| **837.DELANTERO** | **−0,500** | D |
| **837.DELANTERO** | **0,000** | E, F, S |
| 837.ESPALDA | 0,000 | E1, S2, SF |
| **837.MANGA** | **−1,000** | J1 |
| **837.MANGA** | **0,000** | I |

Two LINEAR POMs on one piece asking for different XS/M ratios cannot both be met by one amplitude
vector at any direction. **This is a fact about the targets, not the geometry**, and no solver can
argue with it. Hence `rank` is a parameter (default 2) and the leak is load-bearing.

---

## 2 · FASE B — the core

Unknowns per piece: **directions** (`rank × 2m`, shared across sizes) + **amplitudes**
(`rank × n_sizes`) + a penalised **leak** per size. The displacement of size *t* is
`Σ_k amplitude[k,t] · direction[k] + leak[t]`.

**Gauge (B1), and why it is a projection and not an equation.** Each direction is renormalised to
unit length after every step and the scale is absorbed into its amplitude — the field is
invariant, so fixing it with a constraint row would add an equation whose answer nothing depends
on. ⚠️ For rank ≥ 2 a rotation inside the spanned subspace survives, and it is **left alone on
purpose**: the field is unique, only its factorisation is not, and the diagnosis reports those
degrees of freedom rather than pretending they are gone.

**Why it is fast enough.** The unknown vector reaches 680 on the front and is never
finite-differenced. The residuals depend on it only through each size's composed field, so the
chain rule gives the coupled Jacobian exactly from the per-size field Jacobian F6.1 already
computes: `∂r_t/∂direction[k] = J_t · amplitude[k,t]`, `∂r_t/∂amplitude[k,t] = J_t · direction[k]`,
`∂r_t/∂leak[t] = J_t`. Four field Jacobians per iteration instead of 1 360 deforms.

### 2.1 · Five defects the tests caught, each real

| what was wrong | how it showed |
|---|---|
| **Feasibility is not optimality.** The seed is the four F6.1 answers, so it already satisfies every constraint. A loop that stops on the residual stopped on iteration one and **returned the seed** — the SVD of the F6.1 answer, called a coupled solve. | a leak of 0,0197 mm that no weight could move |
| **Gauss-Newton overshoots on a bilinear map.** The KKT step satisfies the *linearised* constraints to 1,5·10⁻¹⁴ and has norm 33; at the far end the true residual is 19 mm. | contract broken by 19 mm |
| **A leak weight that is too high breaks the contract.** At 10⁶ the problem turns stiff enough that Gauss-Newton stops reaching feasibility and the POM residual jumps to **6,45 mm**. | the contract test |
| **Restoring inside the line search** costs 30 × 4 × 4 field Jacobians per iteration. | the exam produced no output in 300 s on the *smallest* piece |
| 🚨 **And the first fix for that was a regression.** Dropping the restoration and softening the merit made the search cheap and the solver **worse**: on targets a pure rule can serve with zero leak it came back with **5,79 mm** of leak. Speed bought by losing the answer is not speed. The right fix restores with the pseudo-inverse of the Jacobian **the iteration already built** — correct *and* 30× faster than the original (0,6 s where it had been 43). | two suite tests, consistently red |

The contract is now protected structurally, not by a tuned constant: `solve_coupled` checks the
residual afterwards and re-solves with a tenth of the leak weight until it holds. **A bigger leak
is a worse report; a missed POM is a wrong answer.**

### 2.2 · B4 — the predicted redundancy is in the wrong place, and the measurement says where

The brief expected that one FIXED POM across four sizes would stop being four independent
constraints under coupling. **It does not**: each size keeps its own amplitude, so its row touches
a column no other row touches.

What *does* collapse is the **gauge**. `Anchor` and `GrainDirection` are homogeneous rows — they
say «this does not move», with a right-hand side of zero — so applied to `amplitude[t] · direction`
they say the same thing at every size. Measured: twelve rows over three sizes come back **rank 6**,
with the six gauge rows of L and XL named redundant and **no POM row among them**. That is a
better result than the one predicted: a gauge that had to be repeated per size would be a
modelling error, and the diagnosis proves it is not one.

⚠️ And a limit worth naming: **a contradiction inside one size cannot be found in the joint QR.**
The dependency is exact at the base state and stops being exact once the seed has moved the piece
— measured on the same fixture, named at amplitudes 10⁻⁶ and invisible at amplitudes 1. The
coupled report therefore carries the **per-size** diagnoses too, and names them in its message.

---

## 3 · FASE C — the exam

### 3.1 · The joint diagnosis

| piece | targets | DoF apart (4 sizes) | DoF joint | collapse | anchor |
|---|---:|---:|---:|---:|---|
| DELANTERO | 8 | 404 | 198 | **2,0×** | 242 |
| ESPALDA | 4 | 356 | 181 | 2,0× | 0 |
| MANGA | 2 | 132 | 70 | 1,9× | none (open gauge) |
| CUELLO | 1 | 144 | 80 | 1,8× | 0 |
| TAPETA | 1 | 112 | 64 | 1,8× | 0 |

🔑 **The collapse is 2×, not the 5–6× F6.1 assumed.** Rank 2 needs two directions of `2m` each,
which is twice a single size's field — so sharing them across four sizes halves the count and no
more. This number alone already predicted the result below.

### 3.2 · Contract — **PASS**, never traded

| piece | apart | rank 1 | rank 2 | rank 3 |
|---|---:|---:|---:|---:|
| DELANTERO | 6,4·10⁻¹⁰ | 5,5·10⁻⁷ | 3,0·10⁻¹² | 2,7·10⁻¹⁰ |
| ESPALDA | 6,7·10⁻¹⁰ | 6,4·10⁻¹³ | 2,3·10⁻¹³ | 8,4·10⁻¹² |
| MANGA | 4,2·10⁻¹⁰ | 5,9·10⁻¹⁰ | 3,4·10⁻¹⁰ | 2,7·10⁻¹² |
| CUELLO, TAPETA | 0 | 0 | 0 | 0 |

Worst over everything: **5,49 · 10⁻⁷ mm** against a 0,1 mm gate.

### 3.3 · Vertex — the answer, and it is flat

| piece | size | apart (F6.1) | rank 1 | rank 2 | rank 3 |
|---|---|---:|---:|---:|---:|
| DELANTERO | XS | **0,90 / 2,02** | 5,65 / 18,56 | 13,97 / 23,88 | 1,08 / 2,18 |
| DELANTERO | M | 5,07 / 16,82 | 12,32 / 48,51 | **4,56 / 13,24** | 4,74 / 12,66 |
| DELANTERO | L | 10,09 / 34,11 | 24,51 / 96,59 | **9,17 / 26,85** | 9,53 / 25,61 |
| DELANTERO | XL | **13,41 / 42,33** | 34,75 / 132,77 | 18,05 / 48,26 | 13,54 / 42,41 |
| ESPALDA | XL | 22,75 / 53,57 | 22,74 / 53,26 | 22,75 / 53,57 | 22,75 / 53,57 |
| MANGA | XL | 13,82 / 20,95 | **12,79 / 20,52** | 13,32 / 21,12 | 13,81 / 20,95 |

| | apart | rank 1 | rank 2 | rank 3 |
|---|---:|---:|---:|---:|
| **GLOBAL mean** | **6,177** | 9,190 | 7,185 | **6,140** |
| GLOBAL max | 53,568 | 132,774 | 53,568 | 53,568 |
| within 0,5 mm | 40,3 % | 37,3 % | 37,6 % | 38,8 % |

**Rank 3 reproduces F6.1 to two decimals; rank 2 is slightly worse; rank 1 is worse still.** The
back is *identical* at every rank, to the third decimal, because its four constraints are two
FIXED and two LINEAR that share one progression — there was never any inter-size information for
the coupling to exploit. The sleeve is the one place where rank 1 is marginally *better* than
solving apart (12,79 against 13,82 at XL), and it is also the piece with the fewest targets.

### 3.4 · Structure — the leak, and the amplitudes

| piece | rank 1 rms/max | rank 2 | rank 3 |
|---|---|---|---|
| DELANTERO | 1,109 / **6,146** | **0,000** | 0,000 |
| MANGA | 0,404 / **1,187** | 0,002 / 0,004 | 0,000 |
| ESPALDA, CUELLO, TAPETA | 0,000 | 0,000 | 0,000 |

🔑 **At rank ≥ 2 the leak is exactly zero.** The 837 *is* expressible as two shared directions with
per-size amplitudes — the structure is not what fails.

**The amplitudes the solver recovered, against the fitxa** (normalised to the M step):

| piece | source | XS | M | L | XL |
|---|---|---:|---:|---:|---:|
| ESPALDA | **solver, rank 1** | **−0,000** | 1,000 | **2,000** | **3,000** |
| | fitxa (E1, SF) | 0,000 | 1,000 | 2,000 | 3,000 |
| MANGA | solver, rank 1 | −0,058 | 1,000 | 2,003 | 3,008 |
| | fitxa (J1 / I) | −1,000 / 0,000 | 1,000 | 2,000 | 3,000 |
| DELANTERO | **solver, rank 1** | **−0,571** | 1,000 | 1,986 | 2,882 |
| | fitxa (A,B,C / F / E) | −0,667 / 0,000 / 0,000 | 1,000 | 2,000 | 3,000 / 2,500 |

✅ **On the back the solver recovers the fitxa's progression exactly** — 0 · 1 · 2 · 3, to three
decimals, from the geometry alone. The structure IS interpretable as the rule when a piece's
targets agree on one.

🔑 **And on the front it recovers −0,571 · 1 · 1,986 · 2,882, which is the FASE A prediction
arriving in its mildest form.** The front's POMs demand three different XS/M ratios — −0,667,
−0,500 and 0,000 — and one amplitude must serve all three. The solver lands at −0,571, between
them, and pays for the compromise in the only currency it has: **1,11 mm rms of leak, 6,15 mm at
worst**, and a vertex error on that piece of 19,31 mm against 7,37 solving apart. The contract
holds throughout. That is what «rank one is refuted by the targets» looks like when a solver is
made to try anyway.

### 3.5 · C3 controls — all pass

- **CUELLO / TAPETA** (FIXED only): zero field at every rank and size, max |d| ≤ 4,6·10⁻¹³ mm.
- **MANGA** (no still point in Montse's field): the open gauge is *reported*, not failed — the
  diagnosis names the free degrees of freedom and the regulariser returns a member of the family.

---

## 4 · Where the residual lives, and what it eliminates

Three directions have now been measured and closed:

| hypothesis | measured | verdict |
|---|---|---|
| a different penalty (total variation, F6.1 §5.4b) | sleeve XL 15,45 mm vs 13,21 for bending | **worse** |
| fewer unknowns by coupling the sizes (F6.1 §7.1, this sprint) | 6,177 → 6,140 mm | **neutral** |
| more measurement targets (F6.1 §5.1, and A0's 10 → 16) | 7,788 → 6,177 mm | **21 %, and it stops there** |

And F6.1 §5.4a established the other half: **Montse's own field satisfies our constraints to
0,32 mm.** The right answer is inside the feasible set. The gap is not freedom, not smoothness,
and not the number of POMs.

🔑 **It is information, and the CAD tells us in what form.** PolyPattern assigns a distinct rule
number to every turn point — 28 on the front, 24 on the back, 9 on the sleeve, and one shared rule
«1» on the collar and placket. Grading is declared *per point*; the near-rank-2 structure is an
emergent property of those 28 rules, not something the pattern carries.

🚨 **The file that closes this is the RUL of the 837, and we do not have it.** `PatternFile#20`
(the current AGUS pattern) has no RUL; the only one on the bench, `PatternFile#18`, carries a
single rule «1» with all deltas zero. With the real RUL, grading stops being inferred from 16
measurements and becomes data to apply and verify.

---

## 5 · Status of the phase criterion

| | |
|---|---|
| **Contract (POM ≤ 0,1 mm)** | ✅ met, by seven orders of magnitude, at every rank |
| **Vertex (≤ 0,5 mm)** | ❌ 6,140 mm, and now measured **not reachable** by penalty choice, by parameter reduction, or from the POM targets available |

**The recommendation is to re-scope it, and the evidence is now sufficient to say so.** The vertex
criterion asks the motor to reproduce a pattern-maker's per-point decisions from 16 measurements.
Two sprints have measured that it cannot, from three different directions. Either

- the criterion becomes **«reproduce the RUL»** — verifiable, and what the solver is already built
  for (the contract path is exact); or
- it is dropped at vertex level and kept as the **contract**, which is what the product actually
  promises: geometry that measures what the fitxa says.

## 6 · What this opens

1. 🚨 **Ask Montse for the RUL of the 837** (`…AGUS` / `…COSTRURA`). It is the one input that
   changes the problem rather than the method, and §4 is the argument.
2. **The coupled solver stays.** It is correct, it keeps the contract absolutely, and at rank ≥ 2
   it proves the 837 is expressible as a rule with zero leak. It costs nothing to keep and it is
   what a RUL-driven solve would build on.
3. 🚩 **The front's rank-1 amplitude of −28 is a standing alarm about the fitxa**, not about the
   solver: three XS/M progressions on one piece is either a deliberate design or an error, and it
   is the same question the **D** raised. Worth putting to Montse in the same conversation.
4. **`vora` (S, S2) is still unimplemented** — the sewing loop is now in the solver's geometry, so
   what is missing is the arc-length measure and its derivative, not the data.
5. **Speed**: a coupled solve is minutes per piece because the field Jacobian is finite-differenced
   over `2m` columns and each column re-deforms the whole loop. A localised deform (a turn point
   only moves its two adjacent segments) is a ~40× win, and is the obvious optimisation if this
   path continues.
