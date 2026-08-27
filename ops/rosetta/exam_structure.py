"""Why the vertex metric is far, measured three ways — the design input for F6.2.

`exam_solver.py` says HOW FAR the solved field is from Montse's. This says WHY, and the
three measurements here point at three different answers. Only the third survives.

  1. **Is her answer even admissible?** Evaluate our own constraints on her field. If the
     residuals are small, the constraint set contains the right answer and the whole gap is
     the prior picking a different member of the feasible family. If they are large, the
     constraints exclude her and no prior can ever get there.
  2. **Would a different penalty help?** The field is sparse in first differences, which
     suggests total variation. Suggestion is not evidence: run it (IRLS on the first
     difference) against the committed bending prior, same constraints, same bench.
  3. **How many dimensions does a piece's grading actually have?** SVD over the four size
     fields of one piece. If it is low-rank, then solving the four sizes independently —
     which is what this sprint does — throws away the strongest structure in the data.

Read-only. Writes nothing, touches no database row.

Run:  python3 ops/rosetta/exam_structure.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))
sys.path.insert(0, str(REPO / 'ops'))
sys.path.insert(0, str(REPO / 'ops' / 'rosetta'))

from fhort.patterns.engine import grading_solver as gs      # noqa: E402
import exam_solver as ex                                    # noqa: E402

DATASET = Path(__file__).resolve().parent / 'parity_837.json'
GRADED = ('837.DELANTERO', '837.ESPALDA', '837.MANGA')


def header(title: str) -> str:
    return f'\n── {title} ' + '─' * max(4, 78 - len(title))


def problem(bank, name) -> gs.PieceProblem:
    return ex.build_problem(name, bank['peces'][name])


def anchor_of(bank, name):
    al = bank['peces'][name]['bucles'][ex.LOOP_ORDER[0]]['alineacio']
    return al['ancora'] if al['metode'] == 'origen_fix' else None


def truth(bank, name, size) -> np.ndarray:
    """Montse's field for a piece at a size, both loops concatenated in solver order."""
    return np.concatenate([
        np.array(bank['peces'][name]['bucles'][l]['talles'][size]['contorn_alineat'],
                 dtype=float)
        for l in ex.LOOP_ORDER])


# ─────────────────────────────────────────────────────────────────────────────
# 1 · feasibility
# ─────────────────────────────────────────────────────────────────────────────

def feasibility(bank, bd) -> str:
    """Our constraints, evaluated on MONTSE'S OWN field."""
    out = [header("1 · IS MONTSE'S FIELD ADMISSIBLE UNDER OUR CONSTRAINTS?")]
    out.append(f'  {"piece":12s} {"size":4s} {"set":9s} {"rows":>4s} {"worst row":>16s}   '
               f'all rows (mm)')
    for name in GRADED:
        piece = problem(bank, name)
        anchor = anchor_of(bank, name)
        for size in ('M', 'XL'):
            for label, codes in (('contract', ex.C1_POMS),
                                 ('with_EK', ex.LADDER['with_EK'])):
                cons, _used = ex.build_constraints(
                    piece, name, size, bd, codes, anchor, ex.loop_offsets(bank['peces'][name]))
                camp = truth(bank, name, size)
                named = {}
                for c in cons:
                    r = np.asarray(c.residuals(piece, camp), dtype=float).ravel()
                    named.update(dict(zip(c.row_names(), (float(v) for v in r))))
                worst = max(named, key=lambda k: abs(named[k]))
                out.append(f'  {name.replace("837.", ""):12s} {size:4s} {label:9s} '
                           f'{len(named):4d} {worst + "=" + f"{named[worst]:+.3f}":>16s}   '
                           + ' '.join(f'{k}={v:+.2f}' for k, v in named.items()))
    return '\n'.join(out)


# ─────────────────────────────────────────────────────────────────────────────
# 2 · would total variation help?
# ─────────────────────────────────────────────────────────────────────────────

def tv_matrix(piece: gs.PieceProblem, w: np.ndarray) -> np.ndarray:
    m = len(piece.turn_indices)
    h = np.where(piece.arc_spacing() > 0, piece.arc_spacing(), 1.0)
    rows = []
    offset = 0
    for slots in piece.turn_slots_per_loop:          # one cyclic stencil per contour
        q = len(slots)
        for j in range(q):
            r = np.zeros(m)
            r[slots[j]] -= 1.0 / h[offset + j]
            r[slots[(j + 1) % q]] += 1.0 / h[offset + j]
            rows.append(r * np.sqrt(h[offset + j]) * w[slots[j]])
        offset += q
    d = np.array(rows)
    hm = d.T @ d
    full = np.zeros((2 * m, 2 * m))
    full[0::2, 0::2] = hm
    full[1::2, 1::2] = hm
    return full + 1e-8 * np.eye(2 * m)


def solve_with(piece, cons, h, iters=4):
    red = gs.NoReduction(len(piece.turn_indices))
    z = np.zeros(red.n_free)
    for _ in range(iters):
        j, r = gs._jacobian(piece, cons, red, z)
        if j.size == 0 or float(np.max(np.abs(r))) <= 1e-10:
            break
        step = gs._kkt_step(h, j, r, z, gs.Weights())
        if step is None:
            break
        z = z + step
    d = red.expand(z)
    return d, piece.deform(d), float(np.max(np.abs(gs._jacobian(piece, cons, red, z)[1])))


def total_variation(bank, bd, name='837.MANGA') -> str:
    """IRLS on the first difference vs the committed bending prior.

    Only the sleeve: it is the piece whose field is EXACTLY piecewise-affine (four blocks,
    0,143 mm), so if a sparsity prior is ever going to win, it wins here. If it loses here
    it loses everywhere, and the experiment is cheap.
    """
    out = [header('2 · WOULD A TOTAL-VARIATION PRIOR DO BETTER? (sleeve, the best case)')]
    piece = problem(bank, name)
    anchor = anchor_of(bank, name)
    m = len(piece.turn_indices)
    out.append(f'  {"size":4s} {"targets":>7s} | {"bending mean/max":>19s} | '
               f'{"TV-IRLS mean/max":>19s} | {"Montse |d|":>10s}')
    for size in ('M', 'XL'):
        cons, used = ex.build_constraints(
            piece, name, size, bd, ex.C1_POMS, anchor, ex.loop_offsets(bank['peces'][name]))
        camp = truth(bank, name, size)
        base = np.array(piece.base_points)
        bend = gs.solve(piece, cons)
        e_b = np.linalg.norm(bend.points - camp, axis=1)
        w = np.ones(m)
        for _ in range(8):
            d, pts, _res = solve_with(piece, cons, tv_matrix(piece, w))
            jumps = np.linalg.norm(np.roll(d, -1, axis=0) - d, axis=1)
            w = 1.0 / np.sqrt(np.maximum(jumps, 0.05))
            w = w / w.mean()
        e_t = np.linalg.norm(pts - camp, axis=1)
        out.append(f'  {size:4s} {len(used):7d} | {e_b.mean():8.2f} /{e_b.max():9.2f} | '
                   f'{e_t.mean():8.2f} /{e_t.max():9.2f} | '
                   f'{np.linalg.norm(camp - base, axis=1).mean():10.2f}')
    return '\n'.join(out)


# ─────────────────────────────────────────────────────────────────────────────
# 3 · how many dimensions does a piece's grading have?
# ─────────────────────────────────────────────────────────────────────────────

def intrinsic_rank(bank) -> str:
    out = [header('3 · HOW MANY DIMENSIONS DOES A GRADING FIELD HAVE? (SVD over sizes)')]
    base_size = bank['meta']['talla_base']
    sizes = [t for t in bank['meta']['talles'] if t != base_size]
    out.append(f'  {"piece":16s} {"k=1":>9s} {"k=2":>9s} {"k=3":>9s} {"k=4":>9s}   '
               f'component-1 coefficients per size {sizes}')
    for name in GRADED:
        # The intrinsic-rank question is about the contour Montse grades: the CUT line.
        loop = bank['peces'][name]['bucles'][ex.LOOP_ORDER[0]]
        turns = [i for i, k in enumerate(loop['tipus_vertex']) if k == 'turn']
        base = np.array(loop['talles'][base_size]['contorn_alineat'])
        mat = np.array([(np.array(loop['talles'][t]['contorn_alineat']) - base)[turns].ravel()
                        for t in sizes])
        u, s, vt = np.linalg.svd(mat, full_matrices=False)
        errs = [float(np.abs((u[:, :k] * s[:k]) @ vt[:k] - mat).max()) for k in range(1, 5)]
        coef = u[:, 0] * s[0]
        coef = coef / coef[1]                      # normalised to the M step
        out.append(f'  {name:16s} ' + ' '.join(f'{e:8.3f}mm' for e in errs) + '   '
                   + np.array2string(coef, precision=3, suppress_small=True))
    out.append('')
    out.append('  Read: `k=2` is the worst error, in mm, of rebuilding ALL FOUR size fields')
    out.append('  from two basis fields. Rank two to ~1 mm, rank three to ~0,23 mm.')
    return '\n'.join(out)


if __name__ == '__main__':
    bank = json.loads(DATASET.read_text())
    ex.BANK_BASE = bank['meta']['talla_base']
    bd = ex.llegeix_bd()
    print(feasibility(bank, bd))
    print(total_variation(bank, bd))
    print(intrinsic_rank(bank))
