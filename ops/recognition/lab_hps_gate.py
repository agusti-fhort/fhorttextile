"""FASE D2 · THE HARD GATE: the derived HPS against PRODUCTION's own anchor.

Not against our labelling — against the workshop's. POM **F, «Total length from HPS»** on
the 837's front is anchored on a vertex a person chose long before this sprint existed, and
so are E3, M, M3, E1 and S1. If the rule "the HPS is where the neckline meets the shoulder"
is true, it lands on those vertices. That is an EXTERNAL check: nothing in the chain being
tested had any say in where those anchors are.

**Nothing is written.** The edge roles come from the proposer and are passed to the
derivation in memory, exactly as a person's confirmation would arrive. Proving the rule
does not require adopting it.

    python3 ops/recognition/lab_hps_gate.py
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))

#: Production's HPS anchors, read out of `PatternPOM.definicio_mesura` (report §D2), by the
#: `PatternPoint` ids the recipes actually name. Written down rather than re-queried so the
#: gate says out loud which points it is trusting.
PRODUCTION_HPS = {
    '837.DELANTERO': {
        22704: (2019.298, 941.524),    # POM M · "Neck seam (left HPS)"
        22808: (2018.640, 1164.349),   # POM F · "Total length from HPS" · start
    },
    '837.ESPALDA': {
        23515: (2046.583, 1910.464),   # POM M3 · "Neck drop from HPS" · start · SNP (E1)
        23877: (2046.583, 1685.225),   # POM S1 · "Armhole depth from HPS" · start
    },
}

TOLERANCE_MM = 2.0


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
    os.chdir(REPO / 'backend')
    import django
    django.setup()
    from django_tenants.utils import schema_context

    from fhort.patterns.landmark_service import derive_landmarks
    from fhort.patterns.models import PatternFile
    from fhort.patterns.recognition.edge_service import propose_edge_roles

    worst = 0.0
    failures = []
    with schema_context('fhort'):
        fp = PatternFile.objects.get(pk=20)
        for piece in fp.pieces.select_related('piece_role').prefetch_related('points').order_by('id'):
            want = PRODUCTION_HPS.get(piece.nom_block)
            if not want:
                continue
            res = propose_edge_roles(piece)
            roles = {p['segment_id']: p['edge_role']
                     for p in res['proposals'] if p['edge_role']}
            out = derive_landmarks(piece, roles=roles)
            got = [lm for lm in out['landmarks'] if lm['landmark'] == 'hps']
            print('=' * 78)
            print('{}  ({} edges confirmed in memory)  frame: {}'
                  .format(piece.nom_block, len(roles), out['frame']['oriented_by']))
            for lm in got:
                d, near = min(
                    ((math.hypot(lm['x'] - x, lm['y'] - y), pid)
                     for pid, (x, y) in want.items()), key=lambda t: t[0])
                worst = max(worst, d)
                ok = 'PASS' if d <= TOLERANCE_MM else 'FAIL'
                print('  hps side {}  ({:.3f}, {:.3f})  →  PatternPoint#{}  Δ = {:.4f} mm  {}'
                      .format(lm['side'] or '-', lm['x'], lm['y'], near, d, ok))
                if d > TOLERANCE_MM:
                    failures.append((piece.nom_block, lm['side'], d))
            if len(got) != len(want):
                failures.append((piece.nom_block, 'count',
                                 '{} derived vs {} anchored'.format(len(got), len(want))))
                print('  🚨 {} HPS derived but production anchors {}'
                      .format(len(got), len(want)))
            for sk in out['skipped']:
                if sk.get('landmark') == 'hps':
                    print('  hps skipped ({}): {}'.format(sk.get('side'), sk['why']))
    print('=' * 78)
    print('D2 GATE: worst Δ = {:.4f} mm against a tolerance of {} mm → {}'
          .format(worst, TOLERANCE_MM, 'PASS' if not failures else 'FAIL {}'.format(failures)))
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
