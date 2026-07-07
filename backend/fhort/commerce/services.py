"""commerce/services.py — lògica de domini del mòdul comercial.

reserve_document_number calca el patró atòmic de models_app/services.py:38-64
(reserve_sequence_range): transaction.atomic() + select_for_update per bloquejar la fila del
comptador durant la reserva. És concurrency-safe i per-schema sota django-tenants. NO usa el
scan MAX(sequencial) del signal manual (models_app/signals.py) — confirmat NO concurrency-safe
al diagnòstic (R5/R6, DIAGNOSI_COMERCIAL_B2).
"""
from django.db import transaction
from django.utils import timezone

from .models_base import DocumentSequence

# Prefix de numeració per tipus de document (reinici anual, R5). Només Quote a B2.
# TODO B3-B5: 'sales_order':'SO', 'work_order':'WO', 'delivery_note':'DN', 'settlement':'ST'.
DOC_PREFIXES = {
    'quote': 'OF',   # oferta
}


def reserve_document_number(doc_type):
    """Reserva atòmicament el següent número per (doc_type, any actual) i el formata.

    Format de sortida: "{PREFIX}-{YEAR}-{NNNN}" (NNNN a 4 dígits zero-padded), p.ex.
    "OF-2026-0001". El reinici és anual: el comptador viu per (doc_type, year).
    """
    prefix = DOC_PREFIXES.get(doc_type)
    if not prefix:
        raise ValueError(f"Tipus de document sense prefix de numeració: {doc_type!r}")
    year = timezone.now().year
    with transaction.atomic():
        seq, _ = DocumentSequence.objects.select_for_update().get_or_create(
            doc_type=doc_type, year=year,
        )
        seq.last_seq = seq.last_seq + 1
        seq.save(update_fields=['last_seq'])
        n = seq.last_seq
    return f"{prefix}-{year}-{n:04d}"
