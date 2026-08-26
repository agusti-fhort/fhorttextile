"""Where proposals are written — and the one place that must never touch the confirmed.

The whole recogniser exists behind this function. If it ever writes `piece_role`, `face`,
`rol` or `rol_origen`, the guarantee the pattern maker was given is gone, and no amount of
UI colour puts it back. `UPDATE_FIELDS` is the enforcement: `save(update_fields=...)` with
a frozen list means a stray assignment elsewhere in this module cannot reach the database
even by accident, and the test asserts the list.
"""
from __future__ import annotations

import time

from django.db import transaction
from django.utils import timezone

from .bank import build_tenant_bank
from .recognizer import _seam_pair_index, recognize_pieces

#: 🚨 The ONLY columns this module may write. Confirmed identity is not on the list and
#: never will be: `piece_role`, `face`, `rol` and `rol_origen` belong to the human.
UPDATE_FIELDS = ['proposed_role', 'proposed_face', 'proposed_score',
                 'proposed_evidence', 'proposed_at']


def recognize_pattern_file(pattern_file, exclude_self: bool = True) -> dict:
    """Run the cascade over one `PatternFile` and store the proposals. → stats.

    Idempotent: running it twice rewrites the same `proposed_*` and touches nothing else,
    so the re-run button and the import hook are the same code path.

    `exclude_self` keeps this file's own pieces out of the bank. Without it a re-import
    would match itself at distance zero and report perfect confidence about nothing —
    the recogniser marking its own homework.
    """
    from fhort.patterns.models import PatternPiece
    from fhort.pom.models import PatternPieceRole

    t0 = time.perf_counter()
    pieces = list(
        PatternPiece.objects.filter(pattern_file=pattern_file).prefetch_related('points'))
    if not pieces:
        return {'pieces': 0, 'proposed': 0, 'silent': 0, 'ms': 0}

    bank = build_tenant_bank()
    result = recognize_pieces(
        pieces, tenant_bank=bank, pair_index=_seam_pair_index(),
        exclude_file_ids={pattern_file.pk} if exclude_self else set())

    roles = {r.slug: r for r in PatternPieceRole.objects.all()}
    now = timezone.now()
    proposed = silent = 0
    with transaction.atomic():
        for piece in pieces:
            r = result.get(piece.pk)
            if r is None:
                # No geometry at all. Clear any stale proposal rather than leave the
                # previous import's answer standing next to new geometry.
                piece.proposed_role = None
                piece.proposed_face = ''
                piece.proposed_score = None
                piece.proposed_evidence = {'stage': 'N4', 'silent_because': 'no geometry'}
                piece.proposed_at = now
                silent += 1
            elif r['ftt_slug'] is None:
                piece.proposed_role = None
                piece.proposed_face = ''
                piece.proposed_score = r['score']
                piece.proposed_evidence = r['evidence']
                piece.proposed_at = now
                silent += 1
            else:
                piece.proposed_role = roles.get(r['ftt_slug'])
                piece.proposed_face = r['face'] or ''
                piece.proposed_score = r['score']
                piece.proposed_evidence = r['evidence']
                piece.proposed_at = now
                proposed += int(piece.proposed_role is not None)
                silent += int(piece.proposed_role is None)
            piece.save(update_fields=UPDATE_FIELDS)

    return {'pieces': len(pieces), 'proposed': proposed, 'silent': silent,
            'bank': len(bank), 'ms': round((time.perf_counter() - t0) * 1000, 1)}
