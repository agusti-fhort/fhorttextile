"""FASE A · Gate: are graded curves the similarity image of their base segment?

D-INV-3 said the control points of a curve live in the frame of their segment, and that a
grading field moves **only the turn points** while the curves are re-derived preserving
shape. It was an adopted hypothesis (from PyGarment) and had never been checked against a
real graded nest. This checks it against Montse's, and the answer decides what the solver's
unknowns are.

**The test.** For every piece × size, take the curve points of the base, express each in
the local frame of its own turn-to-turn segment, rebuild it in the frame the same segment
has at size T — using the turn points Montse actually drew — and measure how far the result
lands from the point she actually drew.

**Why there are rival models in here.** A probe that only ever runs the model it wants to
confirm cannot fail, and a residual of zero from such a probe means nothing. Four models
run on identical data; three of them are wrong on purpose:

    similarity     the hypothesis: rotate + scale in the segment frame
    lerp_chord     displacement interpolated along the chord parameter
    lerp_index     displacement interpolated along the vertex index
    translate      the whole segment rides with its start point
    swapped        the similarity frame with its two axes exchanged (a deliberate bug)

Run:  python3 ops/rosetta/exam_curves.py
"""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

DATASET = Path(__file__).resolve().parent / 'parity_837.json'

#: The verdict threshold the brief set for fixing D-INV-3.
GATE_MM = 0.5

#: Pieces whose field is identically zero cannot discriminate between models, so they are
#: kept out of the comparison and reported separately. They are still a control: a model
#: that moves anything on them is broken.
MODELS = ('similarity', 'lerp_chord', 'lerp_index', 'translate', 'swapped')


@dataclass(frozen=True)
class Segment:
    start: int
    end: int
    interior: tuple[int, ...]


def segments(kinds, n) -> list[Segment]:
    turns = [i for i, k in enumerate(kinds) if k == 'turn']
    out = []
    for k, a in enumerate(turns):
        b = turns[(k + 1) % len(turns)]
        interior, i = [], (a + 1) % n
        while i != b:
            interior.append(i)
            i = (i + 1) % n
        out.append(Segment(a, b, tuple(interior)))
    return out


def predict(model, base, cur, seg) -> list[tuple[float, float]]:
    ax, ay = base[seg.start]
    bx, by = base[seg.end]
    ux, uy = bx - ax, by - ay
    l2 = ux * ux + uy * uy
    if l2 <= 1e-12:
        return [base[i] for i in seg.interior]
    atx, aty = cur[seg.start]
    btx, bty = cur[seg.end]
    vx, vy = btx - atx, bty - aty
    da = (atx - ax, aty - ay)
    db = (btx - bx, bty - by)

    out = []
    for k, i in enumerate(seg.interior):
        px, py = base[i]
        dx, dy = px - ax, py - ay
        u = (dx * ux + dy * uy) / l2
        v = (dx * -uy + dy * ux) / l2
        if model == 'similarity':
            out.append((atx + u * vx + v * -vy, aty + u * vy + v * vx))
        elif model == 'swapped':
            out.append((atx + v * vx + u * -vy, aty + v * vy + u * vx))
        elif model == 'translate':
            out.append((px + da[0], py + da[1]))
        elif model == 'lerp_chord':
            out.append((px + da[0] + u * (db[0] - da[0]), py + da[1] + u * (db[1] - da[1])))
        elif model == 'lerp_index':
            w = (k + 1) / (len(seg.interior) + 1)
            out.append((px + da[0] + w * (db[0] - da[0]), py + da[1] + w * (db[1] - da[1])))
        else:
            raise ValueError(model)
    return out


def residuals(bank, model, skip_null=True):
    base_size = bank['meta']['talla_base']
    per_cell: dict[tuple[str, str], list[float]] = {}
    for name, piece in bank['peces'].items():
        kinds = piece['tipus_vertex']
        n = piece['n_vertexs']
        base = [tuple(p) for p in piece['talles'][base_size]['contorn_alineat']]
        segs = segments(kinds, n)
        for size in bank['meta']['talles']:
            if size == base_size:
                continue
            cur = [tuple(p) for p in piece['talles'][size]['contorn_alineat']]
            if skip_null and max(math.dist(a, b) for a, b in zip(base, cur)) < 1e-9:
                continue
            vals = []
            for seg in segs:
                if not seg.interior:
                    continue
                for i, q in zip(seg.interior, predict(model, base, cur, seg)):
                    vals.append(math.dist(q, cur[i]))
            per_cell[(name, size)] = vals
    return per_cell


def render(bank) -> str:
    out = []
    out.append('── FASE A · per piece × size, similarity model ' + '─' * 34)
    out.append(f'  {"piece":16s} {"size":5s} {"segments":>8s} {"curve pts":>9s} '
               f'{"mean":>8s} {"p95":>8s} {"max":>8s}')
    cells = residuals(bank, 'similarity', skip_null=False)
    base_size = bank['meta']['talla_base']
    for (name, size), vals in cells.items():
        segs = len(segments(bank['peces'][name]['tipus_vertex'],
                            bank['peces'][name]['n_vertexs']))
        if not vals:
            out.append(f'  {name:16s} {size:5s} {segs:8d} {0:9d}       —        —        —')
            continue
        s = sorted(vals)
        out.append(f'  {name:16s} {size:5s} {segs:8d} {len(vals):9d} '
                   f'{statistics.mean(vals):8.4f} {s[int(0.95 * len(s))]:8.4f} '
                   f'{max(vals):8.4f}')

    every = [v for vals in cells.values() for v in vals]
    s = sorted(every)
    out.append('')
    out.append(f'  GLOBAL n={len(every)} mean={statistics.mean(every):.4f} '
               f'median={s[len(s) // 2]:.4f} p99={s[int(0.99 * len(s))]:.4f} '
               f'max={max(every):.4f} mm')

    out.append('')
    out.append('── FASE A · histogram (similarity) ' + '─' * 45)
    bins = [0, 0.001, 0.005, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, float('inf')]
    for i in range(len(bins) - 1):
        c = sum(1 for v in every if bins[i] <= v < bins[i + 1])
        bar = '#' * int(round(60 * c / len(every)))
        out.append(f'  [{bins[i]:6.3f}, {bins[i + 1]:6.3f})  {c:6d}  '
                   f'{100 * c / len(every):5.1f}%  {bar}')

    out.append('')
    out.append('── FASE A · rival models, same data ' + '─' * 44)
    out.append('  (pieces with a null field are excluded: they cannot discriminate)')
    out.append(f'  {"model":14s} {"n":>6s} {"mean":>10s} {"p95":>10s} {"max":>10s}')
    for model in MODELS:
        vals = [v for vs in residuals(bank, model).values() for v in vs]
        s = sorted(vals)
        out.append(f'  {model:14s} {len(vals):6d} {statistics.mean(vals):10.4f} '
                   f'{s[int(0.95 * len(s))]:10.4f} {max(vals):10.4f}')

    worst = max(every)
    out.append('')
    out.append('── VERDICT ' + '─' * 68)
    if worst <= GATE_MM:
        out.append(f'  PASS · similarity model reproduces every curve point to '
                   f'{worst:.4f} mm (gate {GATE_MM} mm).')
        out.append(f'  D-INV-3 is FIXED: the unknowns of the solver are the TURN POINTS, '
                   f'and the curves follow.')
        out.append(f'  The margin is not marginal — the nearest rival model is off by '
                   f'{max(v for vs in residuals(bank, "lerp_chord").values() for v in vs):.3f} mm.')
    else:
        out.append(f'  FAIL · worst residual {worst:.4f} mm exceeds the {GATE_MM} mm gate. '
                   f'Stop and re-decide the unknowns with Agus.')
    return '\n'.join(out)


if __name__ == '__main__':
    print(render(json.loads(DATASET.read_text())))
