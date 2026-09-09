"""FASE C · The exam: the four sizes solved as ONE rule, against Montse's field.

F6.1 solved each size on its own and reached 6,18 mm at vertex level against a 0,5 mm phase
criterion, and its own diagnosis said why: the front had 16 targets choosing among 101
degrees of freedom, four times over. F6.2 gives the four sizes a shared structure —
directions and per-size amplitudes — so the same 64 constraint rows bear on one problem
instead of four.

**Everything is measured at the same commit.** The ablation (C4) is not a comparison with
the previous report's numbers: it re-runs the F6.1 path here, now, with the same bank and
the same constraint sets, so that the improvement is a measurement and not a memory.

**Three metrics, and they answer different questions.**

  · **Contract** — every POM back at its target to ≤ 0,1 mm. A hard gate that is never
    traded for a better-looking field, at any rank.
  · **Vertex** — the solved field against the field Montse drew, with the F6.1 column beside
    it. This is the one the phase criterion is about.
  · **Structure** — how much LEAK each size needed, and what amplitudes came out. Zero leak
    means the garment really does grade by a rule of that rank. The amplitudes are the
    interesting part: if they match the fitxa's own size progression, the solver has
    recovered the rule the pattern-maker wrote rather than merely fitting numbers.

Run:  python3 ops/rosetta/exam_coupled.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))
sys.path.insert(0, str(REPO / 'ops'))
sys.path.insert(0, str(REPO / 'ops' / 'rosetta'))

from fhort.patterns.engine.grading_solver import (            # noqa: E402
    Weights, solve, solve_coupled,
)
import exam_solver as ex                                      # noqa: E402

DATASET = Path(__file__).resolve().parent / 'parity_837.json'

#: The contract gate. Not negotiable, at any rank.
POM_GATE_MM = 0.1

#: The phase criterion for the vertex metric. Reported, not gated here.
PHASE_MM = 0.5

#: Ranks to report. 1 is the interpretable one — it IS «the rule» — and FASE A already
#: measured that it cannot suffice; 2 and 3 are what the field's own SVD says it needs.
RANKS = (1, 2, 3)

#: 🚩 POMs the Rosetta found the fitxa wrong about (F6-PRE §A0.3). They stay in the targets —
#: the solver's job is to hit what it is told — but the vertex metric is also reported with
#: them removed, so that a rule the fitxa got wrong is not counted as the motor missing.
SOTA_SOSPITA = ('I', 'SLT')
C1_CLEAN = tuple(c for c in ex.C1_POMS if c not in SOTA_SOSPITA)


def header(title: str) -> str:
    return f'\n── {title} ' + '─' * max(4, 78 - len(title))


def build(bank, bd, codes):
    """Per piece: the problem, the per-size constraint sets, and Montse's answer."""
    base = bank['meta']['talla_base']
    sizes = [t for t in bank['meta']['talles'] if t != base]
    out = {}
    for name, piece in bank['peces'].items():
        problem = ex.build_problem(name, piece)
        offsets = ex.loop_offsets(piece)
        al = piece['bucles'][ex.LOOP_ORDER[0]]['alineacio']
        anchor = al['ancora'] if al['metode'] == 'origen_fix' else None
        per_size, targets = {}, {}
        for size in sizes:
            cons, used = ex.build_constraints(problem, name, size, bd, codes, anchor,
                                              offsets)
            per_size[size] = cons
            targets[size] = used
        montse = {size: np.concatenate([
            np.array(piece['bucles'][l]['talles'][size]['contorn_alineat'], dtype=float)
            for l in ex.LOOP_ORDER]) for size in sizes}
        out[name] = {'problem': problem, 'per_size': per_size, 'targets': targets,
                     'montse': montse, 'anchor': anchor}
    return out, sizes


def vertex_errors(points, montse, sizes):
    return {t: np.linalg.norm(points[t] - montse[t], axis=1) for t in sizes}


def run(bank, bd, codes, ranks=RANKS):
    built, sizes = build(bank, bd, codes)
    results = {}
    for name, item in built.items():
        # C4 · the F6.1 path, re-run here so the ablation is a measurement, not a memory.
        apart = {t: solve(item['problem'], item['per_size'][t]) for t in sizes}
        coupled = {r: solve_coupled(item['problem'], item['per_size'], rank=r, seed=apart)
                   for r in ranks}
        results[name] = {'apart': apart, 'coupled': coupled, **item}
    return results, sizes


def render(results, sizes, bank) -> str:
    out = []

    out.append(header('C1 · CONSTRAINT SETS AND THE JOINT DIAGNOSIS'))
    out.append(f'  {"piece":16s} {"targets":>7s} {"DoF apart":>10s} {"DoF joint":>10s} '
               f'{"collapse":>9s}   anchor')
    for name, r in results.items():
        apart_dof = sum(r['apart'][t].diagnosis.dof for t in sizes)
        joint = r['coupled'][2].diagnosis.dof
        n_t = len(r['targets'][sizes[0]])
        out.append(f'  {name:16s} {n_t:7d} {apart_dof:10d} {joint:10d} '
                   f'{apart_dof / max(joint, 1):8.1f}×   '
                   f'{r["anchor"] if r["anchor"] is not None else "NONE (open gauge)"}')

    out.append(header(f'C2 · CONTRACT — every POM at its target (gate ≤ {POM_GATE_MM} mm)'))
    out.append(f'  {"piece":16s} {"apart":>12s} ' + ' '.join(f'{"rank " + str(r):>12s}'
                                                            for r in RANKS))
    worst_all = 0.0
    for name, r in results.items():
        row = [max(abs(v) for t in sizes for v in r['apart'][t].residuals_mm.values())]
        row += [r['coupled'][k].worst_residual_mm for k in RANKS]
        worst_all = max(worst_all, max(row))
        out.append(f'  {name:16s} ' + ' '.join(f'{v:12.2e}' for v in row))
    out.append(f'  → worst over everything: {worst_all:.3e} mm '
               f'({"PASS" if worst_all <= POM_GATE_MM else "FAIL"})')

    out.append(header('C2 · VERTEX — F6.1 (apart) against F6.2 (coupled), same commit'))
    out.append(f'  {"piece":14s} {"size":4s} {"apart mean/max":>18s} '
               + ' '.join(f'{"rank " + str(k) + " mean/max":>18s}' for k in RANKS))
    per_piece = {}
    for name, r in results.items():
        for size in sizes:
            cells = []
            e_a = np.linalg.norm(r['apart'][size].points - r['montse'][size], axis=1)
            cells.append(f'{e_a.mean():8.2f} /{e_a.max():8.2f}')
            for k in RANKS:
                e = np.linalg.norm(r['coupled'][k].points[size] - r['montse'][size], axis=1)
                cells.append(f'{e.mean():8.2f} /{e.max():8.2f}')
                per_piece.setdefault((name, k), []).extend(e.tolist())
            per_piece.setdefault((name, 'apart'), []).extend(e_a.tolist())
            if e_a.max() < 1e-9 and all(c.startswith('    0.00') for c in cells[1:]):
                continue
            out.append(f'  {name.replace("837.", ""):14s} {size:4s} '
                       + ' '.join(f'{c:>18s}' for c in cells))

    out.append('')
    out.append(f'  {"":14s} {"apart":>10s} ' + ' '.join(f'{"rank " + str(k):>10s}'
                                                       for k in RANKS))
    for name in results:
        row = [statistics.mean(per_piece[(name, key)])
               for key in ('apart', *RANKS)]
        out.append(f'  {name:14s} ' + ' '.join(f'{v:10.3f}' for v in row))
    glob = {key: [v for name in results for v in per_piece[(name, key)]]
            for key in ('apart', *RANKS)}
    out.append(f'  {"GLOBAL mean":14s} '
               + ' '.join(f'{statistics.mean(glob[key]):10.3f}' for key in ('apart', *RANKS)))
    out.append(f'  {"GLOBAL max":14s} '
               + ' '.join(f'{max(glob[key]):10.3f}' for key in ('apart', *RANKS)))
    out.append(f'  {"≤" + str(PHASE_MM) + " mm":14s} '
               + ' '.join(f'{100 * sum(1 for v in glob[key] if v <= PHASE_MM) / len(glob[key]):9.1f}%'
                          for key in ('apart', *RANKS)))

    out.append(header('C2 · STRUCTURE — how much leak each rank needed (mm)'))
    out.append(f'  {"piece":16s} ' + ' '.join(f'{"rank " + str(k) + " rms/max":>20s}'
                                             for k in RANKS))
    for name, r in results.items():
        cells = []
        for k in RANKS:
            lk = r['coupled'][k].leak_mm
            rms = max(v[0] for v in lk.values())
            mx = max(v[1] for v in lk.values())
            cells.append(f'{rms:8.3f} /{mx:9.3f}')
        out.append(f'  {name:16s} ' + ' '.join(f'{c:>20s}' for c in cells))

    out.append(header('C2 · THE AMPLITUDES THE SOLVER FOUND, against the fitxa'))
    out.append('  normalised to the M step — the rule the solver recovered, in the fitxa\'s own terms')
    base = bank['meta']['talla_base']
    out.append(f'  {"piece":16s} {"src":10s} ' + ' '.join(f'{t:>8s}' for t in sizes))
    for name, r in results.items():
        amp = r['coupled'][1].amplitudes[0]
        ref = amp[sizes.index('M')]
        if abs(ref) < 1e-9:
            out.append(f'  {name:16s} {"solver r1":10s}   (null field — no rule to read)')
            continue
        out.append(f'  {name:16s} {"solver r1":10s} '
                   + ' '.join(f'{v:8.3f}' for v in amp / ref))
        seen = {}
        for code, kind, _b, _d in r['targets'][sizes[0]]:
            spec = None
            for pom in bank['poms']:
                if pom['codi'] == code and pom['peca'] == name:
                    spec = pom.get('valor_fitxa_cm')
            if not spec or kind != 'LINEAR':
                continue
            m = spec['M'] - spec[base]
            if abs(m) < 1e-9:
                continue
            key = tuple(round((spec[t] - spec[base]) / m, 3) for t in sizes)
            seen.setdefault(key, []).append(code)
        for key, codes in sorted(seen.items(), key=lambda kv: -len(kv[1])):
            out.append(f'  {"":16s} {"fitxa":10s} ' + ' '.join(f'{v:8.3f}' for v in key)
                       + f'   ← {", ".join(codes)}')

    out.append(header('C3 · CONTROLS'))
    for name in ('837.CUELLO', '837.TAPETA'):
        r = results[name]
        worst = max(float(np.abs(r['coupled'][k].points[t]
                                 - np.array(r['problem'].base_points)).max())
                    for k in RANKS for t in sizes)
        out.append(f'  {"OK  " if worst <= 1e-9 else "FAIL"} {name:16s} FIXED only → '
                   f'zero field at every rank and size: max |d| = {worst:.2e} mm')
    manga = results['837.MANGA']
    out.append(f'  {"OK  " if manga["anchor"] is None else "FAIL"} 837.MANGA        no still '
               f'point in Montse\'s field → open gauge, and the solver reports it rather '
               f'than failing')
    for k in RANKS:
        out.append(f'       rank {k}: {manga["coupled"][k].message[:96]}')

    out.append(header('SOLVER MESSAGES'))
    for name, r in results.items():
        for k in RANKS:
            msg = r['coupled'][k].message
            if msg:
                out.append(f'  {name:16s} rank {k}: {msg[:110]}')
    return '\n'.join(out)


if __name__ == '__main__':
    bank = json.loads(DATASET.read_text())
    ex.BANK_BASE = bank['meta']['talla_base']
    bd = ex.llegeix_bd()

    res, sizes = run(bank, bd, ex.C1_POMS)
    print(render(res, sizes, bank), flush=True)

    print(header('C1 · «FITXA SOTA SOSPITA» — the same exam without I and SLT'))
    print('  The Rosetta found the fitxa wrong about these two, so a rule the solver')
    print('  reproduces faithfully still scores as error. Removed from the targets:')
    clean, _ = run(bank, bd, C1_CLEAN, ranks=(2,))
    print(f'  {"piece":16s} {"with (r2)":>12s} {"without (r2)":>14s}')
    for name in res:
        a = [v for t in sizes for v in np.linalg.norm(
            res[name]['coupled'][2].points[t] - res[name]['montse'][t], axis=1)]
        b = [v for t in sizes for v in np.linalg.norm(
            clean[name]['coupled'][2].points[t] - clean[name]['montse'][t], axis=1)]
        print(f'  {name:16s} {statistics.mean(a):12.3f} {statistics.mean(b):14.3f}')
