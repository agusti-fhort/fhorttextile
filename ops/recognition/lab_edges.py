"""FASE D · THE EDGE EXAM: the grammar against the 837, whose truth is written by hand.

Read-only. Prints one line per edge — proposal, margin, and whether it matches the truth
below — plus a PNG per piece so the reading can be audited by eye rather than believed.

The truth is TYPED OUT, not derived, and that is the point: a labeller graded against
anything the labeller itself produced grades its own homework. It was read off the
measured geometry of `PatternFile#20` (report §D1) and it is the dress the house knows.

    python3 ops/recognition/lab_edges.py [--svg DIR] [--pattern-file 20]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))

#: 🚨 THE HAND-WRITTEN TRUTH. Index = position in the cycle as `edges_of_piece` returns it
#: (segments ordered by `vora`, `t_inici`). `None` = this edge has no name in the catalogue
#: and the right answer is silence.
TRUTH_837 = {
    '837.DELANTERO': {
        0: 'side_seam', 1: 'side_seam', 2: 'side_seam',
        3: 'armhole', 4: 'shoulder_seam', 5: 'neckline',
        6: 'slit_edge', 7: None, 8: 'slit_edge',
        9: 'neckline', 10: 'shoulder_seam', 11: 'armhole',
        12: 'side_seam', 13: 'side_seam', 14: 'side_seam', 15: 'hem',
    },
    '837.ESPALDA': {
        0: 'shoulder_seam', 1: 'armhole',
        2: 'side_seam', 3: 'side_seam', 4: 'side_seam', 5: 'hem',
        6: 'side_seam', 7: 'side_seam', 8: 'side_seam',
        9: 'armhole', 10: 'shoulder_seam', 11: 'neckline',
    },
    '837.MANGA': {
        0: 'cuff_line', 1: 'sleeve_underarm_seam',
        2: 'sleeve_cap', 3: 'sleeve_underarm_seam',
    },
    '837.CUELLO': {0: 'collar_attach', 1: 'collar_outer_edge'},
    # The placket has no rows in either catalogue table: its whole cycle must stay silent.
    '837.TAPETA': {0: None, 1: None, 2: None, 3: None},
}

COLOURS = {
    'hem': '#c2410c', 'neckline': '#7c3aed', 'shoulder_seam': '#059669',
    'armhole': '#2563eb', 'side_seam': '#b45309', 'centre_front': '#0891b2',
    'centre_back': '#0891b2', 'slit_edge': '#db2777', 'waistline': '#65a30d',
    'sleeve_cap': '#2563eb', 'cuff_line': '#c2410c',
    'sleeve_underarm_seam': '#b45309', 'collar_attach': '#7c3aed',
    'collar_outer_edge': '#059669',
}


def draw(name, edges, proposals, truth, out_dir):
    """One SVG per piece: every edge in the colour of its role, labelled. Audit by eye.

    SVG and not PNG, and the reason is a house law rather than a preference: the only
    Python on this machine is the SHARED staging venv, and adding matplotlib to it to draw
    five pictures would change the interpreter every other session runs under. An SVG is
    written with the standard library, opens in any browser, and zooms — which for a 17 mm
    jog on a 1 100 mm piece is the difference between auditable and decorative.
    """
    xs = [q[0] for e in edges for q in e.points]
    ys = [q[1] for e in edges for q in e.points]
    pad = 40.0
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    w, h = x1 - x0, y1 - y0

    # The sheet's y grows upwards and SVG's grows down: the flip is applied once, here, so
    # the picture stands the way the pattern maker's screen does.
    def P(q):
        return '{:.2f},{:.2f}'.format(q[0] - x0, y1 - q[1])

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {:.0f} {:.0f}" '
             'width="{:.0f}" height="{:.0f}">'.format(w, h, min(w, 1100), min(w, 1100) * h / w),
             '<rect width="100%" height="100%" fill="#ffffff"/>',
             '<text x="8" y="20" font-family="sans-serif" font-size="16">{}</text>'
             .format(name)]
    for e, p in zip(edges, proposals):
        role = p['edge_role']
        col = COLOURS.get(role, '#9ca3af')
        ok = (role == truth.get(p['index']))
        parts.append(
            '<polyline points="{}" fill="none" stroke="{}" stroke-width="{}" {}/>'
            .format(' '.join(P(q) for q in e.points), col,
                    6 if role else 2, '' if role else 'stroke-dasharray="8 6"'))
        mid = e.points[len(e.points) // 2]
        mx, my = mid[0] - x0, y1 - mid[1]
        parts.append(
            '<text x="{:.1f}" y="{:.1f}" font-family="monospace" font-size="13" '
            'fill="{}">{} {}{}</text>'
            .format(mx + 6, my - 4, col if ok else '#dc2626', p['index'],
                    role or 'silent', '' if ok else '  MISMATCH'))
    parts.append('</svg>')
    path = Path(out_dir) / '{}.svg'.format(name.replace('.', '_'))
    path.write_text('\n'.join(parts), encoding='utf-8')
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--svg', default='', help='directori on desar un SVG per peça')
    ap.add_argument('--pattern-file', type=int, default=20)
    ap.add_argument('--schema', default='fhort')
    ap.add_argument('--threshold', type=float, default=None)
    args = ap.parse_args()

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
    os.chdir(REPO / 'backend')
    import django
    django.setup()
    from django_tenants.utils import schema_context

    from fhort.patterns.models import PatternFile
    from fhort.patterns.recognition.edge_labeler import EDGE_SCORE_MIN
    from fhort.patterns.recognition.edge_service import edges_of_piece, propose_edge_roles

    threshold = args.threshold if args.threshold is not None else EDGE_SCORE_MIN
    hit = miss = silent_ok = silent_bad = wrong = 0

    with schema_context(args.schema):
        fp = PatternFile.objects.get(pk=args.pattern_file)
        print('PatternFile#{}  model {}  v{}  threshold {}'
              .format(fp.pk, fp.model_id, fp.versio, threshold))
        for piece in fp.pieces.select_related('piece_role').prefetch_related('points').order_by('id'):
            truth = TRUTH_837.get(piece.nom_block, {})
            res = propose_edge_roles(piece, threshold=threshold)
            print('=' * 92)
            print('{}  role={}  origin={}  vocab={}'
                  .format(piece.nom_block, res['piece_role'], res.get('origin'),
                          ','.join(res.get('vocabulary') or []) or '(empty)'))
            if res.get('orientation'):
                print('   orientation: flipped={} lead={:.3f} totals={}'
                      .format(res['orientation']['flipped'], res['orientation']['lead'],
                              res['orientation']['totals']))
            if res['silent_because']:
                print('   SILENT: {}'.format(res['silent_because']))
            for p in res['proposals']:
                want = truth.get(p['index'], '?')
                got = p['edge_role']
                if want == '?':
                    tag = '  ·'
                elif got == want:
                    tag = ' OK'
                    hit += int(got is not None)
                    silent_ok += int(got is None)
                elif got is None:
                    tag = 'sil'
                    miss += 1
                else:
                    tag = '✗✗✗'
                    wrong += int(want is not None)
                    silent_bad += int(want is None)
                g = p['evidence'].get('geometry', {})
                print('  [{:2d}]{} got={:<22} want={:<22} m={:.3f} '
                      'un={:.2f} span={:.2f} vn={:.2f} au={:.2f} str={:.3f} len={:.0f}'
                      .format(p['index'], tag, str(got), str(want), p['score'],
                              g.get('un_mid', 0), g.get('un_span', 0), g.get('vn_mid', 0),
                              g.get('along_u', 0), g.get('straightness', 0),
                              g.get('length_mm', 0)))
                if got != want and want != '?':
                    print('        why: {}'.format(p['evidence'].get('why')))
                    print('        scores: {}'.format(p['evidence'].get('scores')))
            if args.svg:
                try:
                    edges, _ = edges_of_piece(piece)
                    print('   svg: {}'.format(
                        draw(piece.nom_block, edges, res['proposals'], truth, args.svg)))
                except Exception as e:                                # noqa: BLE001
                    print('   svg failed: {}'.format(e))

    total = hit + miss + wrong + silent_ok + silent_bad
    print('=' * 92)
    print('SCOREBOARD  named-right {} · silent-right {} · silent-but-nameable {} · '
          'WRONG {} · spoke-where-truth-is-silence {}  (of {})'
          .format(hit, silent_ok, miss, wrong, silent_bad, total))


if __name__ == '__main__':
    main()
