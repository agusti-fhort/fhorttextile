"""The cascade: N1 exact → N2 kNN → N3 context → N4 silence.

🚨 **The corpus bank does not propose, and that is a measured decision, not an oversight.**
The real exam (`ops/recognition/lab_exam.py`, 2026-08-26) put 1,4 M GarmentCode panels
against the workshop's own DXF files and scored **4 of 30 = 13 %**, against a hard ceiling
of **15 of 30 = 50 %** — because GarmentCode has no word for half of what this house cuts
(yoke, lining, facing, neckband, ruffle, placket, interlining). Worse than the accuracy was
the shape of the error: **no threshold separates a corpus hit from a corpus miss**
(AUC 0,567 on vote share, 0,673 on distance), and 10 of the 26 misses arrived with ≥80 % of
the vote. A bank that is wrong 87 % of the time *and* loudest when it is wrong cannot be
allowed near a proposal. It stays built, cached and tested behind
`FTT_RECOGNITION_USE_CORPUS`, off by default, so the day somebody has a better idea the
measurement is there to argue with.

**What does work is the tenant's own bank**: 10 of 10 on the same exam, with a clean
separation — see `SCORE_MIN` below.

Nothing here ever confirms anything. The output is a proposal; the green is the human's.
"""
from __future__ import annotations

import collections
import time

from django.conf import settings

from .bank import build_tenant_bank
from .ftt_geometry import NoGeometry, features_of_piece

#: N1. Below this descriptor distance the piece IS a piece the bank already holds — the
#: re-import case. It is a tolerance for float noise, not for similarity: the measured
#: value on a real re-import of the same geometry is exactly 0,000.
EXACT_DIST = 1e-4
#: …and the areas must agree too. A descriptor is 40 numbers; two different pieces
#: colliding on all 40 is unlikely, not impossible, and "unlikely" is not a guarantee to
#: hand a pattern maker.
EXACT_AREA_REL = 1e-6

#: 🚨 **THE SILENCE THRESHOLD, calibrated on the REAL exam and not on the laboratory.**
#:
#: The score is a MARGIN: how much closer the winning role is than the best rival role.
#: Vote share was measured and rejected — with a ten-row bank it says nothing, and on the
#: corpus it was actively misleading.
#:
#: Measured over 45 pieces of four foreign patterns (TATE, CALLIE, MEREDITH, AMELIA) plus
#: both re-import cases of the 837:
#:
#: | population | margin |
#: |---|---|
#: | every piece whose truth is NOT in the bank (must stay silent) | **≤ 0,099** |
#: | every wrong proposal | ≤ 0,058 |
#: | correct proposals, re-import of a different version | 0,255 – 0,601 |
#: | correct proposals, identical geometry | 1,000 |
#:
#: The lowest threshold that keeps ZERO wrong proposals is just above **0,099**. The value
#: shipped is **0,20**: twice the loudest measured error, and still comfortably below the
#: quietest accepted true proposal (0,255). Two factors of safety on both sides, on a
#: sample small enough to deserve them.
SCORE_MIN = float(getattr(settings, 'FTT_RECOGNITION_MIN_SCORE', 0.20))

#: How much graph coherence (N3) may move a score. Deliberately small: the seam templates
#: INFORM, they do not rule (Agus, 26/08). A signal that can flip an answer on its own is
#: not a re-score, it is a second classifier hiding inside the first.
N3_MAX_BOOST = 0.10


# ═══════════════════════════════════════════════════════════════════════════════
# N3 · context
# ═══════════════════════════════════════════════════════════════════════════════

def _seam_pair_index():
    """`{(slug_a, slug_b) sorted: n_templates}` from the catalogue F3 seeded.

    Read by SLUG, never by pk (law G9), and read fresh: the catalogue is small and a
    cached copy would go stale the day somebody adds a template.
    """
    from fhort.pom.models import SeamPairTemplate

    idx = collections.Counter()
    for t in SeamPairTemplate.objects.all().only(
            'piece_role_a_slug', 'piece_role_b_slug'):
        idx[tuple(sorted((t.piece_role_a_slug, t.piece_role_b_slug)))] += 1
    return idx


def graph_support(slug: str, other_slugs, pair_index) -> tuple[int, list]:
    """How many other pieces of this pattern this role is known to be sewn to.

    The principle, and the reason this is worth its ten lines: **a piece is not identified
    by its shape alone, but by its shape and by what it is sewn to**
    (`INFORME_GIMNAS_N2_GARMENTCODEDATA_2026-08-25.md` §6.3). If the rest of the pattern
    already looks like a front and a sleeve, `collar` is a role the seam grammar expects
    to find there and `placket` is not — and the two are otherwise near-identical little
    strips.

    ⚠️ **Absence of support is not evidence against.** The catalogue is GarmentCode's
    grammar, and GarmentCode has no placket, no facing and no yoke: a real FTT piece can
    be perfectly correct and have zero templates. So this only ever ADDS, never subtracts.
    """
    hits = []
    for other in other_slugs:
        key = tuple(sorted((slug, other)))
        if pair_index.get(key):
            hits.append(other)
    return len(hits), sorted(set(hits))


# ═══════════════════════════════════════════════════════════════════════════════
# The cascade
# ═══════════════════════════════════════════════════════════════════════════════

def _margin(neighbours):
    """`(best, margin)` — how much closer the winner is than the best different role.

    `(d_rival - d_best) / (d_rival + d_best)`: scale-free, in [0, 1], and 1,0 exactly when
    there is no rival at all or the match is exact. A plain difference would mean something
    different at every bank size; a ratio does not.
    """
    best = neighbours[0]
    rival = next((n for n in neighbours
                  if (n['ftt_slug'], n['face']) != (best['ftt_slug'], best['face'])), None)
    if rival is None:
        return best, 1.0
    d1, d2 = best['dist'], rival['dist']
    if d1 + d2 <= 0:
        return best, 1.0
    return best, (d2 - d1) / (d2 + d1)


def recognize_pieces(pieces, tenant_bank=None, pair_index=None,
                     exclude_file_ids=(), k=10) -> dict:
    """Propose a role+face for each piece of ONE pattern. → `{piece_pk: proposal|None}`.

    Takes the whole pattern at once and not one piece at a time, because N3 needs the
    other pieces: the third stage is the only one that knows a pattern is a pattern.

    A proposal is `{'ftt_slug', 'face', 'score', 'evidence'}`. `None` is N4 — an honest
    silence, and the most common answer by design.
    """
    pieces = list(pieces)
    bank = tenant_bank if tenant_bank is not None else build_tenant_bank()
    pair_index = pair_index if pair_index is not None else _seam_pair_index()

    # ── pass 1: geometry and raw neighbours ──────────────────────────────────
    raw = {}
    for piece in pieces:
        t0 = time.perf_counter()
        try:
            feats = features_of_piece(piece)
        except (NoGeometry, ValueError, IndexError, StopIteration) as exc:
            raw[piece.pk] = {'error': str(exc), 'ms': 0}
            continue
        nb = bank.neighbours(feats['descriptor'], k=k,
                             exclude_file_ids=set(exclude_file_ids))
        raw[piece.pk] = {
            'feats': feats, 'nb': nb,
            'ms': round((time.perf_counter() - t0) * 1000, 1),
        }

    # ── pass 2: N1/N2 candidate per piece, before context ────────────────────
    draft = {}
    for piece in pieces:
        r = raw[piece.pk]
        if 'nb' not in r or not r['nb']:
            draft[piece.pk] = None
            continue
        best, margin = _margin(r['nb'])
        area = r['feats']['area_cm2']
        exact = (best['dist'] <= EXACT_DIST
                 and abs(best['area_cm2'] - area) <= EXACT_AREA_REL * max(area, 1e-9))
        draft[piece.pk] = {
            'ftt_slug': best['ftt_slug'], 'face': best['face'],
            'stage': 'N1' if exact else 'N2',
            'score': 1.0 if exact else margin,
            'margin': margin, 'best': best,
        }

    # ── pass 3: N3 context, then N4 silence ──────────────────────────────────
    # The context is read from the drafts that are ALREADY confident, not from every
    # draft: letting an unsure piece vouch for another unsure piece is how a pattern talks
    # itself into a story.
    confident = [d['ftt_slug'] for d in draft.values()
                 if d and d['score'] >= SCORE_MIN]

    out = {}
    for piece in pieces:
        d = draft[piece.pk]
        r = raw[piece.pk]
        if d is None:
            out[piece.pk] = None
            continue
        others = [s for s in confident]
        if d['ftt_slug'] in others:
            others.remove(d['ftt_slug'])
        n_support, supporters = graph_support(d['ftt_slug'], others, pair_index)
        boost = 0.0 if d['stage'] == 'N1' else min(
            N3_MAX_BOOST, N3_MAX_BOOST * n_support / 3.0)
        score = min(1.0, d['score'] + boost)

        evidence = {
            'stage': d['stage'],
            'n_neighbours': len(r['nb']),
            'nearest': [
                {'slug': n['ftt_slug'], 'face': n['face'], 'dist': round(n['dist'], 4),
                 'piece_id': n['piece_id'], 'nom_block': n['nom_block']}
                for n in r['nb'][:3]
            ],
            'margin': round(d['margin'], 4),
            'context': {
                'seam_templates_supporting': n_support,
                'sewn_with': supporters,
                'boost': round(boost, 4),
            },
            'geometry': {
                'boundary': r['feats']['boundary_source'],
                'area_cm2': round(r['feats']['area_cm2'], 1),
                'n_edges': r['feats']['n_edges'],
            },
            'bank': {'kind': 'tenant', 'size': len(bank)},
            'threshold': SCORE_MIN,
            'ms': r['ms'],
        }
        if score < SCORE_MIN:
            # N4. The silence carries its evidence too: "nothing was close enough" is a
            # finding, and the pattern maker deserves to see why rather than an empty box.
            evidence['stage'] = 'N4'
            evidence['silent_because'] = (
                'best margin {:.3f} is below the threshold {:.2f}'.format(
                    score, SCORE_MIN))
            out[piece.pk] = {'ftt_slug': None, 'face': '', 'score': round(score, 4),
                             'evidence': evidence}
            continue
        out[piece.pk] = {'ftt_slug': d['ftt_slug'], 'face': d['face'],
                         'score': round(score, 4), 'evidence': evidence}
    return out
