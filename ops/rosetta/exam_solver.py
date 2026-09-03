"""FASE C · The exam: solve the 837 from targets alone, then look at Montse's answer.

The solver never sees the graded field. It is given the base size, the deltas of GV201 v9
and the constraints, and it has to produce XS/M/L/XL by itself. Only afterwards is the
result laid next to `parity_837.json`.

**Two metrics, and they are not the same kind of thing.**

  · **POM level — the contract.** Re-measure every constrained POM on the solved geometry.
    It must come back at its target to ≤0,1 mm. This is a statement about the solver being
    correct, it is the hard gate of the sprint, and there is no excuse for missing it: the
    solver chose those numbers itself.
  · **Vertex level — the character.** The solved field against the field Montse drew, mean
    and max per piece × size. This is NOT a correctness gate and cannot be one: the front
    has 56 unknowns and three measurement targets, so **53 degrees of freedom are chosen by
    the regulariser, not by the data**. What this measures is whether the prior we wrote
    down behaves like the craft. Where it diverges, the shape of the divergence is the
    evidence for what the next regulariser should be.

Run:  python3 ops/rosetta/exam_solver.py
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))
sys.path.insert(0, str(REPO / 'ops'))

from fhort.patterns.engine.grading_solver import (            # noqa: E402
    Anchor, AttachedPoint, FixedPom, GrainDirection, PieceProblem, PomDelta, SolveReport,
    Weights, solve,
)
from rosetta.rosetta_837 import llegeix_bd                    # noqa: E402

DATASET = Path(__file__).resolve().parent / 'parity_837.json'

#: 🔑 **The C1 constraint set of the A0 amendment: 16 POMs, 7 of them FIXED.**
#:
#: The arithmetic, since the brief states the count and the exclusions separately and they
#: only reconcile one way. Of the 21 POMs on the fitxa, three are out for DOMAIN reasons —
#: `D` (grading disagreement pending Montse), `J` (no recipe at all), `EK` (recipe under
#: review) — leaving 18. Two more, `S` and `S2`, are out for a TOOLING reason: they are
#: `metode=vora` and the solver does not implement arc length along a deformed boundary.
#: 21 − 3 − 2 = **16**, and the FIXED among them are E5, E7, EK1, EK2, G1, SLT, U = **7**,
#: which is exactly what the brief declares. The two kinds of exclusion are listed apart
#: below because they mean different things: one waits on a person, the other on code.
C1_POMS = ('A', 'B', 'C', 'E', 'E1', 'E5', 'E7', 'EK1', 'EK2', 'F', 'G1', 'I', 'J1',
           'SF', 'SLT', 'U')

#: Sensitivity: the brief also lists EK inside the parity set elsewhere. Run both.
C1_POMS_AMB_EK = tuple(sorted(C1_POMS + ('EK',)))

#: Excluded because a PERSON has to decide something. Not silence: a list.
EXCLUSIONS_DOMAIN = {
    'D': 'grading disagreement pending Montse: +0,50 cm/size on her field against the '
         '+3,00 the fitxa asks for (75,0 mm at XL). Constraining it would order the solver '
         'to reproduce a rule the pattern does not follow.',
    'J': 'no PatternPOM recipe on the 1383. It has a GradedSpec at all five sizes but no '
         'anchor — an anchoring gap, not a data gap.',
    'EK': 'recipe under review: 30,5 mm between what the pattern measures (25,05 cm) and '
          'what the fitxa declares (22,00). Run as a sensitivity set, not as a target.',
}

#: Excluded because CODE is missing. A different kind of debt, and it is ours.
EXCLUSIONS_TOOLING = {
    'S': 'metode=vora. Arc length along a deformed boundary is not implemented in the '
         'solver; refused by name rather than approximated by the straight distance.',
    'S2': 'metode=vora, same as S.',
}

#: The two runs of C1: the declared 16, and the same plus EK (whose recipe is under review
#: and which the brief lists on both sides). Everything else measurable is already in.
#: ⚠️ S and S2 are absent from every rung: both are `metode=vora`, which the solver does not
#: implement. The sewing loop IS now in the solver's geometry (A0), so the path exists —
#: what is missing is the arc-length measurement and its derivative, not the data.
LADDER = {
    'contract': C1_POMS,
    'with_EK': C1_POMS_AMB_EK,
}

#: The hard gate of the sprint.
POM_GATE_MM = 0.1

#: The criterion of the whole F6 phase, reported but not gated here.
PHASE_CRITERION_MM = 0.5


@dataclass
class PieceExam:
    name: str
    problem: PieceProblem
    anchor_index: int | None
    reports: dict[str, SolveReport]
    montse: dict[str, np.ndarray]


def load_bank() -> dict:
    return json.loads(DATASET.read_text())


#: Order of the loops inside the concatenated point array. Matches `PatternPoint`'s own
#: `boundary_index`: 0 is the cut line, 1 is the sewing line.
LOOP_ORDER = ('1', '14')


def build_problem(name: str, piece: dict) -> PieceProblem:
    """Both contours, concatenated, with `loop_starts` marking where the second begins."""
    pts, kinds, starts = [], [], []
    for layer in LOOP_ORDER:
        loop = piece['bucles'][layer]
        starts.append(len(pts))
        pts += [(float(x), float(y))
                for x, y in loop['talles'][BANK_BASE]['contorn_alineat']]
        kinds += list(loop['tipus_vertex'])
    return PieceProblem(name=name, base_points=tuple(pts), kinds=tuple(kinds),
                        grain=tuple(piece['fil'][BANK_BASE]),
                        loop_starts=tuple(starts))


def loop_offsets(piece: dict) -> dict[int, int]:
    """`PatternPoint.boundary_index` → where that loop starts in the concatenated array."""
    off, out = 0, {}
    for bi, layer in enumerate(LOOP_ORDER):
        out[bi] = off
        off += piece['bucles'][layer]['n_vertexs']
    return out


def attach(problem: PieceProblem, index: int, xy) -> AttachedPoint:
    """A POM anchor. Since the A0 amendment it IS a vertex — no carrier, no projection.

    🔑 The whole reason `AttachedPoint` exists was that the bank had no sewing line and the
    anchors had to ride the cut contour. They now have native homologues, so every anchor is
    `t=0` on its own vertex and the class degenerates to an exact reference. It is kept
    because a landmark-mode recipe (a point derived at an offset along an edge) will need it
    again, and because keeping the type means the solver does not have to learn a second way
    to name a point.
    """
    return AttachedPoint(base=(float(xy[0]), float(xy[1])), edge=int(index), t=0.0)


def build_constraints(problem: PieceProblem, piece_name: str, size: str, bd: dict,
                      codes: tuple[str, ...], anchor_index: int | None,
                      offsets: dict[int, int]):
    """POM targets + gauge, for one piece at one size."""
    base_pts = np.array(problem.base_points, dtype=float)
    cons = []
    used = []
    for pom in bd['poms']:
        if pom['peca'] != piece_name:
            continue
        code = pom['codi']
        if code not in codes:
            continue
        spec = bd['specs'].get(code)
        if spec is None:
            continue
        definition = pom['definicio']
        order = {'recta': ('a', 'b'), 'vora': ('a', 'b'),
                 'projeccio': ('a', 'b'), 'ortogonal': ('ref_a', 'ref_b', 'p')}[pom['metode']]
        anchors = []
        for key in order:
            pid = definition.get(key)
            _peca, bi, ordre, _mena, x, y = bd['punts'][pid]
            anchors.append(attach(problem, offsets[bi] + ordre, (x, y)))
        anchors = tuple(anchors)
        axis = definition.get('eix', '') or ''

        probe = PomDelta(code, pom['metode'], anchors, 0.0, axis)
        base_mm = probe.measure(problem, base_pts)
        is_fixed = spec[size]['tipus'] == 'FIXED'
        if is_fixed:
            cons.append(FixedPom(code, pom['metode'], anchors, base_mm, axis))
        else:
            delta_mm = (spec[size]['valor_cm'] - spec[BANK_BASE]['valor_cm']) * 10.0
            cons.append(PomDelta(code, pom['metode'], anchors, base_mm + delta_mm, axis))
        used.append((code, 'FIXED' if is_fixed else 'LINEAR', base_mm,
                     0.0 if is_fixed else (spec[size]['valor_cm']
                                           - spec[BANK_BASE]['valor_cm']) * 10.0))

    if anchor_index is not None:
        slot = problem.turn_indices.index(anchor_index)
        cons.append(Anchor(f'anchor@{anchor_index}', slot))
    cons.append(GrainDirection())
    return cons, used


def best_rigid(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """`a` moved by the rigid motion that best fits `b` (Kabsch, 2-D).

    Used only for the gauge-free reading of the vertex metric: a piece whose gauge the
    solver was never told (the sleeve has no still point) would otherwise be scored on
    where it sits rather than on what shape it is.
    """
    ca, cb = a.mean(axis=0), b.mean(axis=0)
    h = (a - ca).T @ (b - cb)
    u, _s, vt = np.linalg.svd(h)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1] *= -1
        r = vt.T @ u.T
    return (a - ca) @ r.T + cb


def run(codes: tuple[str, ...] = C1_POMS, weights: Weights | None = None) -> dict:
    bank = load_bank()
    bd = llegeix_bd()
    global BANK_BASE
    BANK_BASE = bank['meta']['talla_base']
    sizes = [t for t in bank['meta']['talles'] if t != BANK_BASE]

    out: dict[str, PieceExam] = {}
    targets: dict[tuple[str, str], list] = {}
    for name, piece in bank['peces'].items():
        problem = build_problem(name, piece)
        offsets = loop_offsets(piece)
        # The gauge anchor is Montse's own still point, taken on the CUT loop: it is the
        # contour she grades, and A6 shows it is the one that did not move between banks.
        al = piece['bucles'][LOOP_ORDER[0]]['alineacio']
        anchor_index = al['ancora'] if al['metode'] == 'origen_fix' else None
        if anchor_index is not None and problem.kinds[anchor_index] != 'turn':
            raise SystemExit(f'{name}: anchor {anchor_index} is not a turn point.')

        reports, montse = {}, {}
        for size in sizes:
            cons, used = build_constraints(problem, name, size, bd, codes, anchor_index,
                                           offsets)
            targets[(name, size)] = used
            reports[size] = solve(problem, cons, weights)
            montse[size] = np.concatenate([
                np.array(piece['bucles'][l]['talles'][size]['contorn_alineat'], dtype=float)
                for l in LOOP_ORDER])
        out[name] = PieceExam(name, problem, anchor_index, reports, montse)
    return {'bank': bank, 'bd': bd, 'sizes': sizes, 'pieces': out, 'targets': targets,
            'codes': codes, 'weights': weights}


# ─────────────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────────────

def header(title: str) -> str:
    return f'\n── {title} ' + '─' * max(4, 78 - len(title))


def render(res: dict) -> str:
    out: list[str] = []
    sizes = res['sizes']
    pieces: dict[str, PieceExam] = res['pieces']

    out.append(header('C1 · CONSTRAINT SETS AND QR DIAGNOSIS'))
    for name, ex in pieces.items():
        rep = ex.reports[sizes[0]]
        d = rep.diagnosis
        used = res['targets'][(name, sizes[0])]
        poms = ', '.join(f'{c}({k[0]})' for c, k, _b, _d in used) or '—'
        out.append(f'  {name:16s} {d.summary()}')
        out.append(f'  {"":16s} targets: {poms} · anchor: '
                   f'{ex.anchor_index if ex.anchor_index is not None else "NONE (open gauge)"}'
                   f' · components: {len(d.components)}')

    out.append(header(f'C2 · POM LEVEL — THE CONTRACT (gate ≤ {POM_GATE_MM} mm)'))
    out.append(f'  {"piece":16s} {"size":4s} {"POM":5s} {"type":6s} {"target Δ":>9s} '
               f'{"residual":>10s}  conv')
    worst_pom = 0.0
    n_rows = 0
    for name, ex in pieces.items():
        for size in sizes:
            rep = ex.reports[size]
            for code, kind, _base, delta in res['targets'][(name, size)]:
                r = abs(rep.residuals_mm.get(code, float('nan')))
                worst_pom = max(worst_pom, r)
                n_rows += 1
                flag = '' if r <= POM_GATE_MM else '  🚩'
                out.append(f'  {name.replace("837.",""):16s} {size:4s} {code:5s} {kind:6s} '
                           f'{delta:+9.2f} {r:10.2e}  {"Y" if rep.converged else "N"}{flag}')
    out.append(f'  → worst POM residual over {n_rows} rows: {worst_pom:.3e} mm '
               f'({"PASS" if worst_pom <= POM_GATE_MM else "FAIL"})')

    out.append(header('C2 · VERTEX LEVEL — THE CHARACTER (reported, not gated)'))
    out.append(f'  {"piece":16s} {"size":4s} {"mean":>8s} {"p95":>8s} {"max":>8s} '
               f'{"mean*":>8s} {"max*":>8s}   (* = after best-fit rigid)')
    per_piece: dict[str, list[float]] = {}
    for name, ex in pieces.items():
        for size in sizes:
            solved = ex.reports[size].points
            truth = ex.montse[size]
            raw = np.linalg.norm(solved - truth, axis=1)
            aligned = np.linalg.norm(best_rigid(solved, truth) - truth, axis=1)
            s = np.sort(raw)
            per_piece.setdefault(name, []).extend(raw.tolist())
            out.append(f'  {name.replace("837.",""):16s} {size:4s} {raw.mean():8.3f} '
                       f'{s[int(0.95 * len(s))]:8.3f} {raw.max():8.3f} '
                       f'{aligned.mean():8.3f} {aligned.max():8.3f}')
    out.append('')
    for name, vals in per_piece.items():
        v = sorted(vals)
        ok = sum(1 for x in vals if x <= PHASE_CRITERION_MM)
        out.append(f'  {name:16s} n={len(vals):5d} mean={statistics.mean(vals):7.3f} '
                   f'median={v[len(v) // 2]:7.3f} max={max(vals):7.3f} '
                   f'≤{PHASE_CRITERION_MM} mm: {ok}/{len(vals)}')

    out.append(header('C3 · CONTROL — pieces with only FIXED must give the zero field'))
    for name in ('837.CUELLO', '837.TAPETA'):
        ex = pieces[name]
        worst = max(float(np.abs(ex.reports[s].displacement).max()) for s in sizes)
        montse_worst = max(float(np.abs(ex.montse[s] - np.array(ex.problem.base_points)).max())
                           for s in sizes)
        out.append(f'  {"OK  " if worst <= 1e-12 else "FAIL"} {name:16s} '
                   f'solved field max |d| = {worst:.3e} mm · Montse field max |d| = '
                   f'{montse_worst:.3e} mm')

    out.append(header('C1 · EXCLUSIONS — two kinds, and they are not the same debt'))
    out.append('  waiting on a PERSON:')
    for code, why in sorted(EXCLUSIONS_DOMAIN.items()):
        out.append(f'    {code:4s} {why}')
    out.append('  waiting on CODE (ours):')
    for code, why in sorted(EXCLUSIONS_TOOLING.items()):
        out.append(f'    {code:4s} {why}')

    out.append(header('SOLVER MESSAGES'))
    for name, ex in pieces.items():
        msgs = {ex.reports[s].message for s in sizes}
        for m in sorted(x for x in msgs if x):
            out.append(f'  {name:16s} {m}')
    return '\n'.join(out)


def divergence_analysis(res: dict) -> str:
    """Where the regulariser and the craft part company, and in what direction.

    Not «how big is the error» — that is the table above — but «what does the error look
    like», which is the only thing that tells us what to change. Two readings:

      · the error against the DISTANCE to the nearest constrained anchor (does the field
        drift where nothing holds it?),
      · the error split into along-loop and across-loop components (is the solver stretching
        the boundary where Montse translated it, or the other way round?).
    """
    out = [header('C2 · DIVERGENCE ANALYSIS')]
    sizes = res['sizes']
    for name, ex in res['pieces'].items():
        base = np.array(ex.problem.base_points)
        if max(float(np.abs(ex.montse[s] - base).max()) for s in sizes) < 1e-9:
            continue
        for size in sizes[-1:]:                        # the widest step tells the most
            solved = ex.reports[size].points
            truth = ex.montse[size]
            err = solved - truth
            mag = np.linalg.norm(err, axis=1)
            # along vs across the loop, using the base tangent
            nxt = np.roll(base, -1, axis=0) - base
            tang = nxt / np.maximum(np.linalg.norm(nxt, axis=1, keepdims=True), 1e-12)
            along = np.abs(np.sum(err * tang, axis=1))
            across = np.abs(err[:, 0] * -tang[:, 1] + err[:, 1] * tang[:, 0])
            d_solved = np.linalg.norm(solved - base, axis=1)
            d_truth = np.linalg.norm(truth - base, axis=1)
            out.append(f'  {name:16s} {size}  err mean={mag.mean():6.2f} max={mag.max():6.2f} '
                       f'| along={along.mean():6.2f} across={across.mean():6.2f} '
                       f'| |d| solved={d_solved.mean():6.2f} Montse={d_truth.mean():6.2f} '
                       f'| corr={float(np.corrcoef(d_solved, d_truth)[0, 1]):+.3f}')
    return '\n'.join(out)


def growth_budget(res: dict) -> str:
    """How much growth the targets ASK for, against how much the field HAS.

    🚨 This is the line that explains the vertex table, and without it that table is read
    wrong. A piece whose targets contain no LINEAR row has been told nothing about growing,
    so a solver that does not grow it is not failing — it is obeying. The back of the 837 is
    exactly that case: both of its POMs in the parity set are FIXED, because every POM that
    carries its growth (E1, S2, SF) was excluded for want of a sewing line.
    """
    out = [header('C2 · GROWTH BUDGET — what the targets ask vs what the field has')]
    out.append(f'  {"piece":16s} {"LINEAR":>6s} {"FIXED":>5s} {"asked(XL)":>10s} '
               f'{"solved |d|":>11s} {"Montse |d|":>11s} {"corr":>6s}')
    sizes = res['sizes']
    for name, ex in res['pieces'].items():
        used = res['targets'][(name, sizes[-1])]
        n_lin = sum(1 for _c, k, _b, _d in used if k == 'LINEAR')
        n_fix = sum(1 for _c, k, _b, _d in used if k == 'FIXED')
        asked = sum(abs(d) for _c, k, _b, d in used if k == 'LINEAR')
        base = np.array(ex.problem.base_points)
        solved = np.linalg.norm(ex.reports[sizes[-1]].points - base, axis=1)
        truth = np.linalg.norm(ex.montse[sizes[-1]] - base, axis=1)
        corr = (float(np.corrcoef(solved, truth)[0, 1])
                if solved.std() > 1e-12 and truth.std() > 1e-12 else float('nan'))
        out.append(f'  {name:16s} {n_lin:6d} {n_fix:5d} {asked:10.1f} {solved.mean():11.2f} '
                   f'{truth.mean():11.2f} {corr:+6.3f}')
    return '\n'.join(out)


def ladder(res_by_set: dict) -> str:
    out = [header('C2 · INFORMATION LADDER — the vertex metric against target richness')]
    out.append(f'  {"piece":16s} ' + ' '.join(f'{k:>22s}' for k in LADDER))
    out.append(f'  {"":16s} ' + ' '.join(f'{"mean / max (XL)":>22s}' for _ in LADDER))
    any_res = next(iter(res_by_set.values()))
    for name, ex in any_res['pieces'].items():
        cells = []
        for key in LADDER:
            r = res_by_set[key]['pieces'][name]
            size = res_by_set[key]['sizes'][-1]
            e = np.linalg.norm(r.reports[size].points - r.montse[size], axis=1)
            cells.append(f'{e.mean():9.2f} /{e.max():9.2f}')
        out.append(f'  {name:16s} ' + ' '.join(f'{c:>22s}' for c in cells))
    out.append('')
    for key in LADDER:
        r = res_by_set[key]
        vals = [float(v) for name, ex in r['pieces'].items() for s in r['sizes']
                for v in np.linalg.norm(ex.reports[s].points - ex.montse[s], axis=1)]
        worst = max(abs(v) for ex in r['pieces'].values() for s in r['sizes']
                    for v in ex.reports[s].residuals_mm.values())
        out.append(f'  {key:16s} n={len(vals):5d} mean={statistics.mean(vals):7.3f} mm  '
                   f'max={max(vals):7.3f} mm  ≤{PHASE_CRITERION_MM} mm: '
                   f'{sum(1 for v in vals if v <= PHASE_CRITERION_MM)}/{len(vals)}  '
                   f'· worst POM residual {worst:.2e} mm')
    return '\n'.join(out)


def field_structure(res: dict) -> str:
    """What SHAPE Montse's field has, which is the evidence for the next regulariser.

    The vertex table says how far off we are; this says in which direction to move. Two
    measurements on her own field, no solver involved:

      · **sparsity of the first difference** along the turn points. A field built by cutting
        the piece and spreading the blocks has a few big jumps and many near-zero ones. A
        field built by smooth blending has neither.
      · **how few piecewise-AFFINE blocks in arc length reproduce it**, cyclically, to the
        last decimal. This is the direct question: is the boundary displacement a simple
        object in the loop parameter, or is it not?
    """
    out = [header("C2 · THE SHAPE OF MONTSE'S FIELD (no solver involved)")]
    bank = res['bank']
    base_size = bank['meta']['talla_base']
    size = res['sizes'][-1]
    out.append(f'  {"piece":16s} {"turns":>5s} {"Σ|Δd|":>8s} {"top5":>8s} {"top5%":>6s} '
               f'{"|Δd|<2mm":>9s} {"Σ|Δ²d|":>8s}   blocks needed (cyclic, affine in arc)')
    for name, piece in bank['peces'].items():
        # The shape question is about the contour Montse grades: the CUT line.
        loop = piece['bucles'][LOOP_ORDER[0]]
        kinds = loop['tipus_vertex']
        turns = [i for i, k in enumerate(kinds) if k == 'turn']
        base = np.array(loop['talles'][base_size]['contorn_alineat'])
        cur = np.array(loop['talles'][size]['contorn_alineat'])
        d = (cur - base)[turns]
        if np.abs(d).max() < 1e-9:
            out.append(f'  {name:16s} {len(turns):5d}  (null field — nothing to describe)')
            continue
        jumps = np.linalg.norm(np.roll(d, -1, axis=0) - d, axis=1)
        second = np.linalg.norm(np.roll(d, -1, axis=0) - 2 * d + np.roll(d, 1, axis=0), axis=1)
        top5 = float(np.sort(jumps)[::-1][:5].sum())
        blocks = _blocks_needed(base, turns, d)
        out.append(f'  {name:16s} {len(turns):5d} {jumps.sum():8.1f} {top5:8.1f} '
                   f'{100 * top5 / max(jumps.sum(), 1e-9):5.0f}% '
                   f'{int((jumps < 2.0).sum()):4d}/{len(jumps):<4d} {second.sum():8.1f}   '
                   f'{blocks}')
    return '\n'.join(out)


def _blocks_needed(base: np.ndarray, turns: list[int], d: np.ndarray,
                   kmax: int = 6, tol: float = 0.5) -> str:
    """Fewest cyclic piecewise-affine blocks reproducing `d` to `tol`, or '>kmax'."""
    m = len(turns)
    seg = np.linalg.norm(np.diff(np.vstack([base, base[:1]]), axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    arc = np.array([cum[i] for i in turns])
    total = cum[-1]
    best = {}
    for rot in range(m):
        dr = np.roll(d, -rot, axis=0)
        ar = np.unwrap(np.roll(arc, -rot) / total * 2 * np.pi) / (2 * np.pi) * total

        def cost(i, j):
            x, y = ar[i:j], dr[i:j]
            if len(x) < 3:
                return 0.0
            a = np.vstack([x - x.mean(), np.ones(len(x))]).T
            return max(float(np.abs(a @ np.linalg.lstsq(a, y[:, k], rcond=None)[0] - y[:, k]).max())
                       for k in (0, 1))

        prev = [cost(0, j + 1) for j in range(m)]
        best[1] = min(best.get(1, 1e18), prev[m - 1])
        for k in range(2, kmax + 1):
            cur = [1e18] * m
            for j in range(m):
                for i in range(j + 1):
                    v = cost(0, j + 1) if i == 0 else max(prev[i - 1], cost(i, j + 1))
                    cur[j] = min(cur[j], v)
            prev = cur
            best[k] = min(best.get(k, 1e18), prev[m - 1])
    for k in sorted(best):
        if best[k] <= tol:
            return f'k={k} → {best[k]:.3f} mm'
    return f'>{kmax} (k={kmax} still {best[kmax]:.2f} mm)'


if __name__ == '__main__':
    by_set = {key: run(codes) for key, codes in LADDER.items()}
    primary = by_set['contract']
    print(render(primary))
    print(growth_budget(primary))
    print(divergence_analysis(primary))
    print(field_structure(primary))
    print(ladder(by_set))

    print(header('A0 · COUPLING THE TWO LOOPS — measured, not assumed'))
    loose = run(C1_POMS, Weights(couple=0.0))
    print(f'  {"piece":16s} {"size":4s} {"uncoupled mean/max":>22s} {"coupled mean/max":>22s}')
    for name, ex_c in primary['pieces'].items():
        for size in primary['sizes']:
            a = np.linalg.norm(loose['pieces'][name].reports[size].points
                               - loose['pieces'][name].montse[size], axis=1)
            b = np.linalg.norm(ex_c.reports[size].points - ex_c.montse[size], axis=1)
            if a.max() < 1e-9 and b.max() < 1e-9:
                continue
            print(f'  {name.replace("837.",""):16s} {size:4s} '
                  f'{a.mean():10.2f} /{a.max():10.2f} {b.mean():10.2f} /{b.max():10.2f}')
    for label, r in (('uncoupled', loose), ('coupled', primary)):
        vals = [float(v) for e in r['pieces'].values() for sz in r['sizes']
                for v in np.linalg.norm(e.reports[sz].points - e.montse[sz], axis=1)]
        worst = max(abs(v) for e in r['pieces'].values() for sz in r['sizes']
                    for v in e.reports[sz].residuals_mm.values())
        print(f'  {label:10s} n={len(vals):6d} mean={statistics.mean(vals):7.3f} mm  '
              f'max={max(vals):7.3f} mm  · worst POM residual {worst:.2e} mm')

    print(header('SENSITIVITY · same exam WITH EK (recipe under review)'))
    alt = run(C1_POMS_AMB_EK)
    for name, ex in alt['pieces'].items():
        for size in alt['sizes']:
            a = np.linalg.norm(primary['pieces'][name].reports[size].points
                               - ex.reports[size].points, axis=1).max()
            if a > 1e-9:
                print(f'  {name:16s} {size} field moves {a:.3f} mm when EK is added')
    worst = max(abs(v) for n, e in alt['pieces'].items() for s in alt['sizes']
                for v in e.reports[s].residuals_mm.values())
    print(f'  worst residual with EK: {worst:.3e} mm')
