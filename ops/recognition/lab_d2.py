"""D2 — THE REAL EXAM. The full cascade against the workshop's own patterns.

Not the laboratory: these are the DXF files this house actually works with, read off disk
through the engine, with **no import and no domain write**. The truth is the block names
the pattern maker typed.

    venv/bin/python ops/recognition/lab_d2.py [--threshold 0.20]

The hard criterion is not accuracy. It is **zero confident nonsense**: a proposal that is
wrong is worse than no proposal, because a silence costs a pattern maker nothing and a
wrong pre-fill costs them the one thing the screen was for.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402
django.setup()

from django_tenants.utils import schema_context  # noqa: E402

from fhort.patterns.engine.aama_reader import AAMAReader, unfold_piece  # noqa: E402
from fhort.patterns.engine.geometry import LayerRole  # noqa: E402
from fhort.patterns.recognition import bank as B, recognizer as R  # noqa: E402
from lab_exam import EXAM, truth_of  # noqa: E402


class PieceShim:
    """A `PieceData` from the engine, wearing a `PatternPiece`'s clothes.

    Exists so the exam runs the SAME cascade the product runs, not a re-implementation of
    it. A lab that re-implements the thing it measures measures the re-implementation —
    and the day the two drift, the exam keeps reporting the old one's score.
    """

    class _Points:
        def __init__(self, pts):
            self._pts = pts

        def all(self):
            return self._pts

    class _Pt:
        __slots__ = ('mena', 'boundary_index', 'ordre', 'x', 'y', 'tipus')

        def __init__(self, bi, ordre, p):
            self.mena = 'vertex'
            self.boundary_index = bi
            self.ordre = ordre
            self.x = p.x
            self.y = p.y
            self.tipus = getattr(p.kind, 'value', '')

    def __init__(self, pk, piece):
        self.pk = pk
        self.nom_block = piece.nom_block
        self.lateralitat = ''
        self.contorns = [
            {'index': i, 'role': b.role.value, 'closed': b.closed}
            for i, b in enumerate(piece.boundaries)
        ]
        pts = []
        for i, b in enumerate(piece.boundaries):
            for o, p in enumerate(b.points):
                pts.append(self._Pt(i, o, p))
        self.points = self._Points(pts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--threshold', type=float, default=None)
    args = ap.parse_args()
    if args.threshold is not None:
        R.SCORE_MIN = args.threshold

    with schema_context('fhort'):
        bank = B.build_tenant_bank()
        bank_slugs = sorted({r['ftt_slug'] for r in bank.rows})
        pair_index = R._seam_pair_index()
        print('tenant bank: {} confirmed pieces · roles {}'.format(len(bank), bank_slugs))
        print('threshold   : {:.2f}\n'.format(R.SCORE_MIN))

        tot = hit = wrong = silent = unknown = 0
        wrongs = []
        for label, path in EXAM:
            if not os.path.exists(path):
                continue
            doc = AAMAReader().read(open(path, 'rb').read())
            pieces = [PieceShim(i, unfold_piece(p))
                      for i, p in enumerate(doc.pieces, start=1)]
            # 837's own pieces ARE the bank. Recognising them against themselves would
            # measure nothing, so the exam always excludes the file under test — the same
            # `exclude_self` the product uses on a re-import.
            res = R.recognize_pieces(pieces, tenant_bank=bank, pair_index=pair_index,
                                     exclude_file_ids=())
            print('=== {} · {} pieces ==='.format(label, len(pieces)))
            for p in pieces:
                r = res.get(p.pk)
                gt = truth_of(p.nom_block)
                said = (r or {}).get('ftt_slug')
                score = (r or {}).get('score')
                tot += 1
                if said is None:
                    silent += 1
                    mark, verdict = '·', 'silent'
                elif gt == '?':
                    unknown += 1
                    mark, verdict = '?', 'unknown truth'
                elif said == gt:
                    hit += 1
                    mark, verdict = '✓', 'HIT'
                else:
                    wrong += 1
                    wrongs.append((label, p.nom_block, gt, said, score))
                    mark, verdict = '✗', 'WRONG'
                print('  {} {:28s} truth={:12s} said={:11s} score={:>6} {}'.format(
                    mark, p.nom_block[:28], gt, said or '—',
                    '{:.3f}'.format(score) if score is not None else '—', verdict))
            print()

        print('── D2 · REAL EXAM · threshold {:.2f} ──'.format(R.SCORE_MIN))
        print('  pieces          : {}'.format(tot))
        print('  proposed & RIGHT: {}'.format(hit))
        print('  proposed & WRONG: {}   <<< the hard criterion'.format(wrong))
        print('  proposed, truth unknown: {}'.format(unknown))
        print('  SILENT          : {}  ({:.0f} %)'.format(silent, 100 * silent / max(tot, 1)))
        if wrongs:
            print('\n  the wrong ones:')
            for w in wrongs:
                print('    {} · {} truth={} said={} score={}'.format(*w))
        return wrong


if __name__ == '__main__':
    sys.exit(0 if main() == 0 else 1)
