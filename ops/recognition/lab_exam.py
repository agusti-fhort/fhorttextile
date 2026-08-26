"""The REAL exam: run the neighbour bank against the workshop's own DXF files.

Reads the fixture DXFs straight off disk through the engine — **no database, no import,
no domain write**. That is not a convenience: a recognizer measured on data it had a hand
in creating measures itself.

    venv/bin/python ops/recognition/lab_exam.py [--variant sew|cut] [--k 200]

Truth comes from the block names, which in this house are the pattern maker's own words
(`837.DELANTERO`, `TATE_SLEEVE`). Where a name does not resolve to a catalogue slug the
row is reported as `?` and counted apart — an unknown truth is not a wrong answer.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402
django.setup()

import numpy as np  # noqa: E402

from fhort.patterns.engine.aama_reader import AAMAReader, unfold_piece  # noqa: E402
from fhort.patterns.engine.geometry import LayerRole  # noqa: E402
from fhort.patterns.recognition import bank as B  # noqa: E402
from fhort.patterns.recognition.descriptor import MM_PER_CM, features_from_outline  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), '..', '..',
                        'backend', 'fhort', 'patterns', 'tests', 'fixtures')
MEDIA = '/var/www/ftt-staging/backend/media/fhort/pattern_files'

#: The exam papers. 837 is the one with CONFIRMED truth in the database; the rest carry
#: their truth in the block names the pattern maker typed.
EXAM = [
    ('837', os.path.join(MEDIA, '837_CORS_194_VESTIT_M3-4_AGUS.DXF')),
    ('TATE', os.path.join(FIXTURES, 'TATE_prova.dxf')),
    ('CALLIE', os.path.join(FIXTURES, 'CALLIE_prova.dxf')),
    ('MEREDITH', os.path.join(FIXTURES, 'MEREDITH_prova.dxf')),
    ('AMELIA', os.path.join(FIXTURES, 'AMELIA_AZUL_prova.dxf')),
]

#: Block name → catalogue slug. The pattern maker's vocabulary, in three languages,
#: mapped onto the 33 seeded slugs. Order matters: the first substring that matches wins,
#: so the more specific names come first.
TRUTH = [
    ('NECK_BAND_INTERLINING', 'interlining'), ('FACING_YOKE', 'facing'),
    ('FRONT_FACING', 'facing'), ('FRONT_YOKE', 'yoke'), ('NECK_BAND', 'neckband'),
    ('TAPETA', 'placket'), ('CUELLO', 'collar'), ('COLLAR', 'collar'),
    ('DELANTERO', 'front'), ('ESPALDA', 'back'), ('MANGA', 'sleeve'),
    ('SLEEVE', 'sleeve'), ('YOKE', 'yoke'), ('RUFFL', 'ruffle'),
    ('FRONT_LINI', 'lining'), ('BACK_LINI', 'lining'),
    ('FRONT', 'front'), ('BACK', 'back'), ('CUFF', 'cuff'), ('WAISTBAND', 'waistband'),
]


def truth_of(name: str) -> str:
    up = name.upper()
    for key, slug in TRUTH:
        if key in up:
            return slug
    return '?'


def outline_and_counts(piece, prefer):
    """Outline in cm plus (n_edges, n_curved), straight from the engine's PieceData."""
    order = ([LayerRole.SEW, LayerRole.CUT] if prefer == 'sew'
             else [LayerRole.CUT, LayerRole.SEW])
    for role in order:
        b = piece.boundary(role)
        if b is None or not b.closed or len(b.points) < 3:
            continue
        P = np.asarray([(p.x, p.y) for p in b.points], dtype=float) / MM_PER_CM
        n_turn = sum(1 for p in b.points if getattr(p.kind, 'value', '') == 'turn')
        n_curve = sum(1 for p in b.points if getattr(p.kind, 'value', '') == 'curve')
        n_edges = max(n_turn, 1)
        return P, n_edges, (n_edges if n_turn == 0 else min(n_edges, n_curve)), role.value
    return None, 0, 0, ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', default='sew', choices=['sew', 'cut'])
    ap.add_argument('--k', type=int, default=200)
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    bank = B.get_corpus_bank()
    print('corpus bank: {} panels, 1 in {}\n'.format(len(bank), bank.fraction))

    # gc_role -> ftt_slug, straight from the catalogue table F3 seeded.
    from django_tenants.utils import schema_context
    from fhort.pom.models import GCPieceRoleMap
    with schema_context('fhort'):
        gcmap = {m.gc_role: (m.ftt_slug, m.face)
                 for m in GCPieceRoleMap.objects.all()}

    tally = collections.Counter()
    rows = []
    for label, path in EXAM:
        if not os.path.exists(path):
            print('  {:9s} MISSING: {}'.format(label, path))
            continue
        doc = AAMAReader().read(open(path, 'rb').read())
        pieces = [unfold_piece(p) for p in doc.pieces]
        print('=== {} · {} pieces ==='.format(label, len(pieces)))
        for piece in pieces:
            P, ne, nc, src = outline_and_counts(piece, args.variant)
            if P is None:
                print('  {:28s} NO CLOSED OUTLINE'.format(piece.nom_block))
                tally['no_geometry'] += 1
                continue
            f = features_from_outline(P, ne, nc, mirror=False)
            nb = bank.neighbours(f['descriptor'], k=args.k)
            votes = collections.Counter()
            for n in nb:
                slug, face = gcmap.get(n['gc_role'], ('?', ''))
                votes[slug] += 1
            top, ntop = votes.most_common(1)[0]
            gt = truth_of(piece.nom_block)
            ok = (top == gt)
            tally['total'] += 1
            tally['known' if gt != '?' else 'unknown_truth'] += 1
            if gt != '?':
                tally['hit' if ok else 'miss'] += 1
            rows.append((label, piece.nom_block, gt, top, ntop / max(len(nb), 1),
                         f['area_cm2'], nb[0]['dist'] if nb else float('inf')))
            if not args.quiet:
                mark = '✓' if ok else ('·' if gt == '?' else '✗')
                print('  {} {:26s} truth={:11s} top={:11s} {:3d}/{:d}  area={:7.0f}  d0={:.2f}'
                      .format(mark, piece.nom_block[:26], gt, top, ntop, len(nb),
                              f['area_cm2'], nb[0]['dist'] if nb else -1))
        print()

    known = tally['known'] or 1
    print('── corpus bank alone, variant={} k={} ──'.format(args.variant, args.k))
    print('  pieces        : {}'.format(tally['total']))
    print('  known truth   : {}'.format(tally['known']))
    print('  unknown truth : {}'.format(tally['unknown_truth']))
    print('  HITS          : {}/{}  = {:.1f} %'.format(tally['hit'], known,
                                                       100 * tally['hit'] / known))
    return rows


if __name__ == '__main__':
    main()


# ═══════════════════════════════════════════════════════════════════════════════
# The calibration that actually decides the threshold
# ═══════════════════════════════════════════════════════════════════════════════

def tenant_exam(k=10, exclude_labels=('837',)):
    """Every exam piece against the TENANT bank. → rows of (label, block, truth, …).

    🚨 **The rows that decide the threshold are the ones whose truth is NOT in the bank.**
    A recogniser that scores well on pieces it has seen before is not the question; the
    question is what it says about a yoke when it has never been shown a yoke. Every one of
    those is a chance to be confidently wrong, and the threshold is set by the loudest of
    them.

    `exclude_labels` keeps 837 out by default: its pieces ARE the bank, so measuring on
    them measures nothing.
    """
    import django
    from django_tenants.utils import schema_context

    from fhort.patterns.recognition import bank as B

    with schema_context('fhort'):
        tb = B.build_tenant_bank()
        bank_slugs = sorted({r['ftt_slug'] for r in tb.rows})
        print('tenant bank: {} pieces, roles {}\n'.format(len(tb), bank_slugs))
        out = []
        for label, path in EXAM:
            if label in exclude_labels or not os.path.exists(path):
                continue
            doc = AAMAReader().read(open(path, 'rb').read())
            for piece in (unfold_piece(p) for p in doc.pieces):
                P, ne, nc, src = outline_and_counts(piece, 'sew')
                if P is None:
                    continue
                f = features_from_outline(P, ne, nc, mirror=False)
                nb = tb.neighbours(f['descriptor'], k=k)
                if not nb:
                    continue
                best = nb[0]
                other = next((n for n in nb if n['ftt_slug'] != best['ftt_slug']), None)
                d1 = best['dist']
                d2 = other['dist'] if other else float('inf')
                margin = 1.0 if d2 == float('inf') else (d2 - d1) / (d2 + d1)
                gt = truth_of(piece.nom_block)
                out.append({
                    'label': label, 'block': piece.nom_block, 'truth': gt,
                    'proposed': best['ftt_slug'], 'd1': d1, 'margin': margin,
                    'reachable': gt in bank_slugs,
                })
        return out, bank_slugs
