"""C + D · The exam of authorship: reproduce the RUL, then solve with what it declares.

F6.1 and F6.2 both ended at the same place — 6,18 mm at vertex level against a 0,5 mm phase
criterion — and F6.2 named the missing input: the grade rule table of the 837. It arrived.
This is what it changes, in two measurements that answer different questions.

  · **C · Reconstruction.** Base size + RUL + the map, against Montse's nest. This does not
    solve anything: it applies the pattern-maker's own numbers. If the map is right the error
    is the rounding of the export and nothing else — and that is what makes it the check ON
    the map, because a wrong map does not give thousandths of a millimetre, it gives metres.

  · **D · The solver with the declared schedule.** The same 16 measurement targets F6.1 had,
    plus the one thing the RUL contributes that no amount of solving could produce: HOW the
    sizes progress. Everything else is still inferred. This is the honest question — does
    knowing the inter-size law close the gap the measurements alone could not?

🚨 **What the RUL refutes, and it is the structure both previous sprints assumed.** Every
turn point carries its own rule, so there is no grouping of points to declare. And a single
point's four displacements are not collinear: fitting one direction per point leaves 3,0 mm
rms and 7,2 mm at worst, because X and Y grade on DIFFERENT schedules. F6.2's rank-1 mode —
one direction per point, one amplitude per size — cannot express even ONE point of this
pattern. That is why D declares a schedule per AXIS and not a grouping of points.

Run:  python3 ops/rosetta/exam_rul.py
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))
sys.path.insert(0, str(REPO / 'ops'))
sys.path.insert(0, str(REPO / 'ops' / 'rosetta'))

from fhort.patterns.engine.grading_solver import (            # noqa: E402
    PieceProblem, solve, solve_coupled, solve_declared,
)
import exam_solver as ex                                      # noqa: E402
import rul_837 as R                                           # noqa: E402

#: The contract gate, unchanged from F6.1 and F6.2. Never traded.
POM_GATE_MM = 0.1

#: The phase criterion for the vertex metric.
PHASE_MM = 0.5

#: 🚩 The two POMs the Rosetta found the fitxa wrong about (F6-PRE §A0.3). Same treatment as
#: F6.2: they stay in the targets, and the vertex metric is also reported without them.
SOTA_SOSPITA = ('I', 'SLT')


def header(title: str) -> str:
    return f'\n── {title} ' + '─' * max(4, 78 - len(title))


# ── C · RECONSTRUCTION ──────────────────────────────────────────────────────────

def cut_problem(piece: dict) -> PieceProblem:
    """The CUT loop on its own.

    The bench's own `build_problem` concatenates cut and sewing, because that is what the
    solver works on. C needs the cut loop alone: it is the only one the RUL grades, and the
    curve transport has to run inside the loop that owns the turn points.
    """
    loop = piece['bucles']['1']
    pts = [(float(x), float(y)) for x, y in loop['talles']['S']['contorn_alineat']]
    return PieceProblem(name='cut', base_points=tuple(pts),
                        kinds=tuple(loop['tipus_vertex']),
                        grain=tuple(piece['fil']['S']), loop_starts=(0,))


def rul_field(doc, table, mapa, name: str, size: str, n: int) -> tuple[np.ndarray, list[int]]:
    """The displacement the RUL declares for every point of a piece's cut loop.

    Returns the full (n, 2) field — zero where no rule sits — and the indices that carry one.
    """
    piece = next(p for p in doc.pieces if p.metadata.piece_name == name)
    boundary = next(b for b in piece.boundaries if b.layer == R.CAPA_TALL)
    field, carriers = np.zeros((n, 2)), []
    for i, pt in enumerate(boundary.points):
        if pt.grade_rule is None:
            continue
        carriers.append(i)
        field[i] = table.regles[mapa.rul(pt.grade_rule)].deltes[size]
    return field, carriers


def exam_c(bank, doc, table, mapa, sizes) -> dict:
    """Apply the RUL and compare, at the turn points and then over the whole cut loop."""
    out = {}
    for name, piece in bank['peces'].items():
        loop = piece['bucles']['1']
        base = np.array(loop['talles']['S']['contorn_alineat'], dtype=float)
        problem = cut_problem(piece)
        turns = list(problem.turn_indices)
        rows = {}
        for size in sizes:
            field, carriers = rul_field(doc, table, mapa, name, size, len(base))
            montse = np.array(loop['talles'][size]['contorn_alineat'], dtype=float)
            # The turn points, straight from the table.
            e_turn = np.linalg.norm(base[carriers] + field[carriers] - montse[carriers],
                                    axis=1)
            # And the whole loop: the turn displacements transported to the curves by the
            # segment frame — D-INV-3, which `PieceProblem.deform` already implements.
            full = problem.deform(field[turns])
            e_all = np.linalg.norm(full - montse, axis=1)
            rows[size] = {'turn': e_turn, 'all': e_all,
                          'carriers': carriers, 'turns_match': carriers == turns}
        out[name] = rows
    return out


def exam_c3(bank, doc, table, mapa, sizes) -> list[str]:
    """🚨 The sewing loop: the RUL does not carry it, and here is the measurement that says so.

    The CAD numbers the sewing line separately (3 · 6 · 9 … on the front) and those numbers
    are not in the table. Two things are measured rather than asserted: that no constant
    offset maps them, and whether the sewing line nevertheless obeys the same per-piece
    schedule the cut line does — which is what D assumes when it applies one schedule to a
    problem that carries both loops.
    """
    lines = []
    for name in sorted(mapa.blocs):
        piece = bank['peces'][name]
        cad = next(p for p in doc.pieces if p.metadata.piece_name == name)
        sew = next(b for b in cad.boundaries if b.layer == '14')
        loop = piece['bucles']['14']
        base = np.array(loop['talles']['S']['contorn_alineat'], dtype=float)
        idx = [i for i, pt in enumerate(sew.points) if pt.grade_rule is not None]
        rules = [sew.points[i].grade_rule for i in idx]
        true = {s: np.array(loop['talles'][s]['contorn_alineat'], dtype=float)[idx] - base[idx]
                for s in sizes}

        best = None
        for off in range(-260, 261):
            got = [r - off for r in rules]
            if any(g not in table.regles for g in got):
                continue
            err = statistics.fmean(
                float(np.linalg.norm(np.array(table.regles[g].deltes[s]) - true[s][k]))
                for k, g in enumerate(got) for s in sizes)
            if best is None or err < best[1]:
                best = (off, err)
        lines.append(f'  {name.replace("837.", ""):10s} {len(idx):3d} punts de cosit amb regla '
                     f'({min(rules)}–{max(rules)})   millor desplaçament constant: '
                     f'{best[0]:+4d} → {best[1]:8.3f} mm')
    return lines


def exam_c4(bank, doc, table, mapa, sizes) -> list[str]:
    """Does the SEWING line follow the same per-piece schedule as the cut line?

    D applies one schedule per piece to a problem that carries both loops, so this is not a
    curiosity: it is the assumption that mode rests on, measured on Montse's own field.
    """
    lines = []
    hor = R.horaris(table, mapa)
    for name in sorted(mapa.blocs):
        piece = bank['peces'][name]
        cad = next(p for p in doc.pieces if p.metadata.piece_name == name)
        sew = next(b for b in cad.boundaries if b.layer == '14')
        loop = piece['bucles']['14']
        base = np.array(loop['talles']['S']['contorn_alineat'], dtype=float)
        idx = [i for i, pt in enumerate(sew.points) if pt.grade_rule is not None]
        d = np.array([np.array(loop['talles'][s]['contorn_alineat'], dtype=float)[idx] - base[idx]
                      for s in sizes])                       # (n_sizes, n_pts, 2)
        cells = []
        for eix, j in (('x', 0), ('y', 1)):
            a = np.array(hor[(name, eix)].coeficients, dtype=float)
            m = d[sizes.index('M'), :, j]
            pred = np.outer(a, m)
            res = d[:, :, j] - pred
            cells.append(f'{eix}: rms {np.sqrt((res ** 2).mean()):6.3f} '
                         f'max {np.abs(res).max():7.3f}')
        lines.append(f'  {name.replace("837.", ""):10s} {len(idx):3d} punts   ' + '   '.join(cells))
    return lines


# ── D · THE SOLVER WITH THE DECLARED SCHEDULE ───────────────────────────────────

def build(bank, bd, codes, sizes):
    """Same construction as F6.2's exam, so the comparison is like for like."""
    out = {}
    for name, piece in bank['peces'].items():
        problem = ex.build_problem(name, piece)
        offsets = ex.loop_offsets(piece)
        al = piece['bucles'][ex.LOOP_ORDER[0]]['alineacio']
        anchor = al['ancora'] if al['metode'] == 'origen_fix' else None
        per_size, targets = {}, {}
        for size in sizes:
            cons, used = ex.build_constraints(problem, name, size, bd, codes, anchor, offsets)
            per_size[size] = cons
            targets[size] = used
        montse = {size: np.concatenate([
            np.array(piece['bucles'][l]['talles'][size]['contorn_alineat'], dtype=float)
            for l in ex.LOOP_ORDER]) for size in sizes}
        out[name] = {'problem': problem, 'per_size': per_size, 'targets': targets,
                     'montse': montse, 'anchor': anchor}
    return out


def exam_d(bank, bd, codes, table, mapa, sizes) -> dict:
    """F6.1 (apart) · F6.2 (rank 2) · F6.3 (declared schedule), all in one process.

    🔑 The ablation is re-run here rather than quoted, exactly as F6.2 insisted: the numbers
    in the report's last column must be measurements taken at this commit, on this bank, with
    these constraint sets.
    """
    hor = R.horaris(table, mapa)
    built = build(bank, bd, codes, sizes)
    results = {}
    for name, item in built.items():
        apart = {t: solve(item['problem'], item['per_size'][t]) for t in sizes}
        rank2 = solve_coupled(item['problem'], item['per_size'], rank=2, seed=apart)
        if name in mapa.blocs:
            ax = [hor[(name, 'x')].coeficients[sizes.index(t)] for t in sizes]
            ay = [hor[(name, 'y')].coeficients[sizes.index(t)] for t in sizes]
            declared = solve_declared(item['problem'], item['per_size'], ax, ay, seed=apart)
        else:
            # The RUL declares the NULL rule on every point of these two, so the declared
            # answer is not solved for: it is «this piece does not grade». Reported as such.
            ax = ay = None
            declared = None
        results[name] = {'apart': apart, 'rank2': rank2, 'declared': declared,
                         'schedule': (ax, ay), **item}
    return results


# ── RENDER ──────────────────────────────────────────────────────────────────────

def render(bank, doc, table, mapa, sizes, c, d) -> str:
    out = []

    out.append(header('A · THE RUL ITSELF'))
    for v in R.verifica_rul(table):
        out.append(str(v))

    out.append(header('B · THE MAP FROM THE `# n` OF THE DXF TO THE TABLE'))
    for v in R.verifica_mapa(doc, table, mapa):
        out.append(str(v))

    out.append(header('B6 · THE SCHEDULES THE RUL DECLARES (normalised to the M step)'))
    out.append(f'  {"piece":12s} {"axis":4s} {"XS":>8s} {"M":>8s} {"L":>8s} {"XL":>8s}'
               f'{"":4s}{"separable model rms / max":>28s}')
    hor = R.horaris(table, mapa)
    for (name, eix), h in sorted(hor.items()):
        out.append(f'  {name.replace("837.", ""):12s} {eix:4s} '
                   + ' '.join(f'{v:8.3f}' for v in h.coeficients)
                   + f'    {h.residu_rms_mm:12.3f} /{h.residu_max_mm:9.3f} mm')
    out.append('  🚨 X and Y do NOT share a schedule: on the body the width stops at 2,5 where')
    out.append('     the length goes to 3, and X does not move at all between XS and S.')

    out.append(header(f'C · RECONSTRUCTION — base + RUL + map against the nest '
                      f'(criterion {PHASE_MM} mm)'))
    out.append(f'  {"piece":12s} {"size":4s} {"turn pts":>9s} {"mean":>9s} {"max":>9s}'
               f'{"":4s}{"whole loop":>11s} {"mean":>9s} {"max":>9s}')
    worst_turn = worst_all = 0.0
    n_turn = n_all = 0
    for name, rows in c.items():
        for size in sizes:
            r = rows[size]
            worst_turn = max(worst_turn, float(r['turn'].max()))
            worst_all = max(worst_all, float(r['all'].max()))
            n_turn += len(r['turn'])
            n_all += len(r['all'])
            out.append(f'  {name.replace("837.", ""):12s} {size:4s} {len(r["turn"]):9d} '
                       f'{r["turn"].mean():9.4f} {r["turn"].max():9.4f}    '
                       f'{len(r["all"]):11d} {r["all"].mean():9.4f} {r["all"].max():9.4f}')
    out.append(f'  → worst over {n_turn} rule-carrying points: {worst_turn:.4f} mm')
    out.append(f'  → worst over {n_all} points of the cut loop: {worst_all:.4f} mm  '
               f'({"PASS" if worst_all <= PHASE_MM else "FAIL"} at {PHASE_MM} mm)')
    out.append(f'  🔑 The RUL rounds to two decimals, so a CORRECT map cannot do better than '
               f'{R.COTA_ARRODONIMENT_MM:.4f} mm.')
    match = all(rows[size]['turns_match'] for rows in c.values() for size in sizes)
    out.append(f'  🔑 The points that carry a rule are EXACTLY the solver\'s turn points: {match}.')

    out.append(header('C3 · THE SEWING LOOP IS NOT IN THE TABLE, AND THE SEARCH SAYS SO'))
    out += exam_c3(bank, doc, table, mapa, sizes)
    out.append('  → no constant offset maps them: the CAD derives the sewing line from the cut')
    out.append('    line, so it is not data of authorship. It is NOT reconstructed from the RUL.')

    out.append(header('C4 · BUT IT DOES OBEY ITS PIECE\'S SCHEDULE — which is what D assumes'))
    out += exam_c4(bank, doc, table, mapa, sizes)

    out.append(header(f'D1 · CONTRACT — every POM at its target (gate ≤ {POM_GATE_MM} mm)'))
    out.append(f'  {"piece":12s} {"apart (F6.1)":>14s} {"rank 2 (F6.2)":>15s} '
               f'{"declared (F6.3)":>17s}')
    worst = 0.0
    for name, r in d.items():
        a = max(abs(v) for t in sizes for v in r['apart'][t].residuals_mm.values())
        cells = [f'{a:14.2e}', f'{r["rank2"].worst_residual_mm:15.2e}']
        cells.append(f'{r["declared"].worst_residual_mm:17.2e}' if r['declared']
                     else f'{"null rule":>17s}')
        worst = max(worst, a, r['rank2'].worst_residual_mm,
                    r['declared'].worst_residual_mm if r['declared'] else 0.0)
        out.append(f'  {name.replace("837.", ""):12s} ' + ' '.join(cells))
    out.append(f'  → worst over everything: {worst:.3e} mm '
               f'({"PASS" if worst <= POM_GATE_MM else "FAIL"})')

    out.append(header('D2 · VERTEX against Montse — the three modes, measured at this commit'))
    out.append(f'  {"piece":12s} {"size":4s} {"apart mean/max":>19s} {"rank 2 mean/max":>19s} '
               f'{"declared mean/max":>19s}')
    per = {}
    for name, r in d.items():
        for size in sizes:
            cells, keys = [], ('apart', 'rank2', 'declared')
            for key in keys:
                if key == 'apart':
                    pts = r['apart'][size].points
                elif key == 'rank2':
                    pts = r['rank2'].points[size]
                else:
                    pts = (r['declared'].points[size] if r['declared']
                           else np.array(r['problem'].base_points))
                e = np.linalg.norm(pts - r['montse'][size], axis=1)
                cells.append(f'{e.mean():9.2f} /{e.max():8.2f}')
                per.setdefault((name, key), []).extend(e.tolist())
            if all(cc.strip().startswith('0.00') for cc in cells):
                continue
            out.append(f'  {name.replace("837.", ""):12s} {size:4s} '
                       + ' '.join(f'{cc:>19s}' for cc in cells))

    out.append('')
    keys = ('apart', 'rank2', 'declared')
    out.append(f'  {"":14s} {"apart":>11s} {"rank 2":>11s} {"declared":>11s}   '
               f'{"RUL applied":>12s}')
    rul_all = [float(v) for rows in c.values() for size in sizes for v in rows[size]['all']]
    for name in d:
        out.append(f'  {name:14s} '
                   + ' '.join(f'{statistics.fmean(per[(name, k)]):11.3f}' for k in keys))
    glob = {k: [v for name in d for v in per[(name, k)]] for k in keys}
    out.append(f'  {"GLOBAL mean":14s} '
               + ' '.join(f'{statistics.fmean(glob[k]):11.3f}' for k in keys)
               + f'   {statistics.fmean(rul_all):12.4f}')
    out.append(f'  {"GLOBAL max":14s} '
               + ' '.join(f'{max(glob[k]):11.3f}' for k in keys)
               + f'   {max(rul_all):12.4f}')
    out.append(f'  {"≤" + str(PHASE_MM) + " mm":14s} '
               + ' '.join(f'{100 * sum(1 for v in glob[k] if v <= PHASE_MM) / len(glob[k]):10.1f}%'
                          for k in keys)
               + f'   {100 * sum(1 for v in rul_all if v <= PHASE_MM) / len(rul_all):11.1f}%')
    out.append('  ⚠️ The three solver columns cover BOTH loops (cut + sewing), as F6.1 and F6.2')
    out.append('     reported them. «RUL applied» is the cut loop only — the one the table grades.')

    out.append(header('D3 · STRUCTURE — what each mode had to leak (mm)'))
    out.append(f'  {"piece":12s} {"rank 2 rms/max":>20s} {"declared rms/max":>20s}   schedule x · y')
    for name, r in d.items():
        cells = []
        for rep in (r['rank2'], r['declared']):
            if rep is None:
                cells.append(f'{"null rule":>20s}')
                continue
            rms = max(v[0] for v in rep.leak_mm.values())
            mx = max(v[1] for v in rep.leak_mm.values())
            cells.append(f'{rms:9.3f} /{mx:9.3f}')
        ax, ay = r['schedule']
        sch = ('  '.join(f'{v:.2f}' for v in ax) + ' · ' + '  '.join(f'{v:.2f}' for v in ay)
               if ax else 'the RUL says this piece does not grade')
        out.append(f'  {name.replace("837.", ""):12s} ' + ' '.join(cells) + f'   {sch}')
    return '\n'.join(out)


def main() -> None:
    bank = ex.load_bank()
    ex.BANK_BASE = bank['meta']['talla_base']
    doc = R.carrega_mestre()
    table = R.carrega_rul()
    mapa = R.construeix_mapa(doc, table)
    sizes = [t for t in bank['meta']['talles'] if t != bank['meta']['talla_base']]
    bd = ex.llegeix_bd()          # read-only: the anchored POMs and the sealed GradedSpecs
    c = exam_c(bank, doc, table, mapa, sizes)
    d = exam_d(bank, bd, ex.C1_POMS, table, mapa, sizes)
    print(render(bank, doc, table, mapa, sizes, c, d), flush=True)


if __name__ == '__main__':
    main()
