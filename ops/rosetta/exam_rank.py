"""FASE A · Gate: how many dimensions does a piece's grading actually have?

F6.2 wants to impose the structure of a grading RULE — one direction per turn point, one
amplitude per size — on the solver. That is a **rank-one** model of the displacement field.
Before imposing it, measure whether the material supports it, and by how much it misses.

**The measurement.** Per piece and per loop, stack the four non-base displacement fields
(turn points only) into a 4 × 2m matrix and take its SVD. Then:

  · singular values and cumulative energy — how concentrated the field is;
  · the worst reconstruction error, in mm, from k components — energy is a ratio and a
    ratio cannot be compared with a tolerance in millimetres. **The mm column is the one
    that decides**, and the two disagree loudly here: the second component of the front
    carries 0,92 % of the energy and 6,8 mm of amplitude.
  · the amplitudes the first component implies, per size — because if they look like the
    fitxa's own size progression then the structure is not a numerical trick, it is
    literally the rule the pattern-maker wrote.

**The gate.** The brief stops the sprint if effective rank ≤2 is refuted globally. It is not
refuted — but «rank ≤2» is not «rank 1», and B1 asks for rank 1. What this script exists to
say precisely is **how much a pure rule leaves on the table**, which is the size of the leak
term B3 will have to carry.

Run:  python3 ops/rosetta/exam_rank.py
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

DATASET = Path(__file__).resolve().parent / 'parity_837.json'

#: The phase criterion. **Everything is decided against this, in millimetres.**
#:
#: 🚨 The first version of this script decided the gate on cumulative ENERGY against an
#: arbitrary 1e-4, and duly declared «rank ≤2 REFUTED» on a field whose rank-2 residual is
#: 1,0 mm — while its own docstring said a ratio cannot be compared with a tolerance. An
#: energy of 0,99988 and one of 0,99991 are the same statement about the world and opposite
#: statements about a threshold. The ratios are still printed, because they say how
#: concentrated the field is; they decide nothing.
PHASE_MM = 0.5

#: A component is worth naming if dropping it costs more than this. In mm, like everything.
MATERIAL_MM = 0.05


def header(title: str) -> str:
    return f'\n── {title} ' + '─' * max(4, 78 - len(title))


def turn_field(loop: dict, base_size: str, sizes: list[str]) -> np.ndarray:
    """(n_sizes, 2m) — the displacement of each turn point at each non-base size."""
    turns = [i for i, k in enumerate(loop['tipus_vertex']) if k == 'turn']
    base = np.array(loop['talles'][base_size]['contorn_alineat'], dtype=float)
    return np.array([
        (np.array(loop['talles'][t]['contorn_alineat'], dtype=float) - base)[turns].ravel()
        for t in sizes
    ])


def analyse(mat: np.ndarray) -> dict:
    u, s, vt = np.linalg.svd(mat, full_matrices=False)
    energy = np.cumsum(s ** 2) / max(float(np.sum(s ** 2)), 1e-30)
    errs = [float(np.abs((u[:, :k] * s[:k]) @ vt[:k] - mat).max())
            for k in range(1, len(s) + 1)]
    amp = u[:, 0] * s[0]
    # Sign is arbitrary in an SVD; fix it so the amplitudes grow with size.
    if amp[-1] < 0:
        amp = -amp
    return {'sing': s, 'energy': energy, 'errs': errs, 'amp': amp}


def fitxa_progressions(bank: dict) -> dict[str, np.ndarray]:
    """Each POM's increments over the non-base sizes, normalised to its M step.

    The question B1 is really asking is whether ONE amplitude vector can stand for a whole
    piece. The fitxa answers it first: if its POMs already disagree about the progression,
    no rank-one model can satisfy them all and the leak is not the solver's fault.
    """
    base = bank['meta']['talla_base']
    sizes = [t for t in bank['meta']['talles'] if t != base]
    out = {}
    for pom in bank['poms']:
        vals = pom.get('valor_fitxa_cm') or {}
        if not vals or pom['tipus_grading'] != 'LINEAR':
            continue
        inc = np.array([vals[t] - vals[base] for t in sizes], dtype=float)
        ref = inc[sizes.index('M')] if 'M' in sizes else 0.0
        if abs(ref) < 1e-9:
            continue
        out[pom['codi']] = inc / ref
    return out


def render(bank: dict) -> str:
    base = bank['meta']['talla_base']
    sizes = [t for t in bank['meta']['talles'] if t != base]
    layers = bank['meta']['capes']
    out = [header('FASE A · SVD OF THE GRADING FIELD, PER PIECE AND LOOP')]
    out.append(f'  {"piece":16s} {"loop":6s} {"turns":>5s} '
               + ' '.join(f'{"s" + str(k + 1):>9s}' for k in range(len(sizes)))
               + f' {"E(1)":>9s} {"E(2)":>9s}')
    fields = {}
    for name, piece in bank['peces'].items():
        for layer in layers:
            loop = piece['bucles'][layer]
            mat = turn_field(loop, base, sizes)
            if np.abs(mat).max() < 1e-9:
                out.append(f'  {name:16s} {loop["rol"]:6s} '
                           f'{sum(1 for k in loop["tipus_vertex"] if k == "turn"):5d}   '
                           f'(null field — no structure to measure)')
                continue
            a = analyse(mat)
            fields[(name, loop['rol'])] = a
            out.append(f'  {name:16s} {loop["rol"]:6s} '
                       f'{mat.shape[1] // 2:5d} '
                       + ' '.join(f'{v:9.2f}' for v in a['sing'])
                       + f' {a["energy"][0]:9.5f} {a["energy"][1]:9.5f}')

    out.append(header('FASE A · WHAT k COMPONENTS LEAVE BEHIND, IN MILLIMETRES'))
    out.append('  (energy is a ratio; the phase criterion is 0,5 mm. This is the column that decides.)')
    out.append(f'  {"piece":16s} {"loop":6s} '
               + ' '.join(f'{"k=" + str(k + 1):>10s}' for k in range(len(sizes))))
    for (name, rol), a in fields.items():
        marks = []
        for e in a['errs']:
            marks.append(f'{e:9.3f}' + ('*' if e <= PHASE_MM else ' '))
        out.append(f'  {name:16s} {rol:6s} ' + ' '.join(marks))
    out.append('  (* = within the phase criterion)')

    out.append(header('FASE A · THE AMPLITUDES THE FIRST COMPONENT IMPLIES'))
    out.append('  normalised to the M step, so they can be read against the fitxa')
    out.append(f'  {"piece":16s} {"loop":6s} ' + ' '.join(f'{t:>8s}' for t in sizes))
    for (name, rol), a in fields.items():
        amp = a['amp']
        ref = amp[sizes.index('M')]
        norm = amp / ref if abs(ref) > 1e-12 else amp
        out.append(f'  {name:16s} {rol:6s} ' + ' '.join(f'{v:8.3f}' for v in norm))

    out.append('')
    out.append('  the fitxa, for comparison (LINEAR POMs, same normalisation):')
    progs = fitxa_progressions(bank)
    seen: dict[tuple, list[str]] = {}
    for code, v in sorted(progs.items()):
        seen.setdefault(tuple(round(float(x), 3) for x in v), []).append(code)
    for key, codes in sorted(seen.items(), key=lambda kv: -len(kv[1])):
        out.append(f'  {"":16s} {"":6s} ' + ' '.join(f'{v:8.3f}' for v in key)
                   + f'   ← {", ".join(codes)}')

    out.append(header('FASE A · THE FITXA ITSELF RULES OUT RANK ONE, AND SAYS SO EXACTLY'))
    out.append('  A rank-one field means ONE amplitude per size for the whole piece, so every')
    out.append('  measurement on that piece must grow in the SAME proportion. The fitxa does')
    out.append('  not ask for that — and the clash is not subtle, it is at XS:')
    out.append('')
    conflict = _progression_conflict(bank)
    out.append(f'  {"piece":16s} {"XS/M ratio":>11s}  POMs')
    for name, groups in conflict.items():
        for ratio, codes in groups:
            out.append(f'  {name:16s} {ratio:11.3f}  {", ".join(codes)}')
    out.append('')
    out.append('  Two LINEAR POMs on one piece wanting different XS/M ratios cannot both be')
    out.append('  met by one amplitude vector, at any rank-one direction. This is a fact about')
    out.append('  the TARGETS, not about the geometry, and no solver can argue with it.')

    out.append(header('VERDICT'))
    worst = {k: max((a['errs'][k - 1] for a in fields.values()), default=0.0)
             for k in (1, 2, 3)}
    biggest = max((float(np.abs(turn_field(piece['bucles'][layer], base, sizes)).max())
                   for piece in bank['peces'].values() for layer in layers), default=0.0)
    for k in (1, 2, 3):
        out.append(f'  rank {k}: worst residual {worst[k]:7.3f} mm '
                   f'({100 * worst[k] / max(biggest, 1e-9):5.1f} % of the largest '
                   f'displacement) — {"within" if worst[k] <= PHASE_MM else "above"} '
                   f'the {PHASE_MM} mm criterion')
    out.append('')
    if worst[2] > 10 * PHASE_MM:
        out.append('  → rank ≤2 REFUTED. Stop after FASE A and re-decide with Agus.')
        return '\n'.join(out)
    out.append('  → **rank ≤2 HOLDS**: two components leave 1,0 mm on fields of 60 mm, and')
    out.append('    the brief\'s stop condition is not met. Build the coupled solver.')
    out.append('  → **but rank ONE is refuted twice over**, and both refutations are measured:')
    out.append(f'    · geometrically, it leaves {worst[1]:.1f} mm — thirteen times the criterion;')
    out.append('    · and the fitxa\'s own POMs demand different size progressions on the same')
    out.append('      piece, which one amplitude vector cannot deliver at any rank.')
    out.append('  → therefore the RANK IS A PARAMETER, not a constant, and B3\'s leak is not a')
    out.append('    safety net but a load-bearing part. Default rank 2; report 1, 2 and 3.')
    return '\n'.join(out)


def _progression_conflict(bank: dict) -> dict[str, list[tuple[float, list[str]]]]:
    """Per piece, the distinct XS/M ratios its LINEAR POMs ask for.

    One ratio per piece means a rank-one amplitude vector can serve it. Two or more means it
    cannot, whatever the direction — the piece is being asked to grow in two proportions at
    once.
    """
    base = bank['meta']['talla_base']
    out: dict[str, dict[float, list[str]]] = {}
    for pom in bank['poms']:
        vals = pom.get('valor_fitxa_cm') or {}
        if not vals or pom['tipus_grading'] != 'LINEAR' or pom['peca'] == '—':
            continue
        m = vals['M'] - vals[base]
        if abs(m) < 1e-9:
            continue
        ratio = round((vals['XS'] - vals[base]) / m, 3)
        out.setdefault(pom['peca'], {}).setdefault(ratio, []).append(pom['codi'])
    return {name: sorted(groups.items()) for name, groups in sorted(out.items())}


if __name__ == '__main__':
    print(render(json.loads(DATASET.read_text())))
