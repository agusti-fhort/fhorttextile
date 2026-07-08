"""commerce/services.py — lògica de domini del mòdul comercial.

reserve_document_number calca el patró atòmic de models_app/services.py:38-64
(reserve_sequence_range): transaction.atomic() + select_for_update per bloquejar la fila del
comptador durant la reserva. És concurrency-safe i per-schema sota django-tenants. NO usa el
scan MAX(sequencial) del signal manual (models_app/signals.py) — confirmat NO concurrency-safe
al diagnòstic (R5/R6, DIAGNOSI_COMERCIAL_B2).
"""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from .models_base import DocumentSequence

_CENT = Decimal('0.01')

# Prefix de numeració per tipus de document (reinici anual, R5). Només Quote a B2.
# TODO B3-B5: 'sales_order':'SO', 'work_order':'WO', 'delivery_note':'DN', 'settlement':'ST'.
DOC_PREFIXES = {
    'quote': 'OF',   # oferta
}


def compute_document_totals(document, lines):
    """Càlcul fiscal compartit de tot document comercial (Quote, SalesOrder…). Un sol lloc de
    veritat fiscal: retorna (subtotal, tax_amount, total, tax_breakdown) sense persistir res.

    Lleis (B3a): Decimal sempre, quantize 0.01 (ROUND_HALF_UP) a cada pas. L'IVA es calcula
    sobre la BASE AGREGADA de cada tipus (product.tax_rate), mai línia a línia. Si el règim
    fiscal del client és INTRA_EU/EXPORT/EXEMPT, el tipus efectiu és 0 (bases visibles al
    breakdown). `tax_breakdown` és una llista [{rate, base, tax}] ordenada per tipus desc.
    """
    customer = getattr(document, 'customer', None)
    regime = getattr(customer, 'tax_regime', 'DOMESTIC') if customer is not None else 'DOMESTIC'
    exempt = regime in ('INTRA_EU', 'EXPORT', 'EXEMPT')
    # Agrupar les bases (Σ line_total) per tipus impositiu de l'article.
    groups = {}
    for line in lines:
        rate = Decimal(line.product.tax_rate).quantize(_CENT) if line.product_id else Decimal('0.00')
        groups[rate] = groups.get(rate, Decimal('0')) + Decimal(line.line_total or 0)
    breakdown, subtotal, tax_total = [], Decimal('0'), Decimal('0')
    for rate in sorted(groups, reverse=True):
        base = groups[rate].quantize(_CENT)
        eff = Decimal('0.00') if exempt else rate
        tax = (base * eff / 100).quantize(_CENT, rounding=ROUND_HALF_UP)
        breakdown.append({'rate': str(eff), 'base': str(base), 'tax': str(tax)})
        subtotal += base
        tax_total += tax
    subtotal = subtotal.quantize(_CENT)
    tax_amount = tax_total.quantize(_CENT)
    total = (subtotal + tax_amount).quantize(_CENT)
    return subtotal, tax_amount, total, breakdown


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


def effective_payment_terms(quote):
    """Condició de pagament efectiva: la del document, si no la del customer, si no cap."""
    if quote.payment_terms_id:
        return quote.payment_terms
    if quote.customer_id:
        return quote.customer.payment_terms
    return None


def generate_due_dates(quote):
    """Esborra i regenera els venciments materialitzats del quote des del payment_terms efectiu.

    Només genera si el quote té `issued_at` i una condició de pagament efectiva. Import de cada
    fracció = (total × pct / 100).quantize(0.01); la ÚLTIMA fracció = total − Σ anteriors (ajust
    del cèntim), de manera que la suma dels venciments SEMPRE quadra exacta amb el total.
    """
    from .models import DocumentDueDate
    quote.due_dates.all().delete()
    terms = effective_payment_terms(quote)
    if not terms or not quote.issued_at:
        return
    lines = list(terms.lines.all())
    if not lines:
        return
    total = Decimal(quote.total or 0)
    allocated = Decimal('0')
    objs = []
    for i, ln in enumerate(lines):
        if i < len(lines) - 1:
            amount = (total * ln.percentage / 100).quantize(_CENT, rounding=ROUND_HALF_UP)
        else:
            amount = total - allocated   # última fracció: la suma quadra exacta amb total
        allocated += amount
        objs.append(DocumentDueDate(
            quote=quote, due_date=quote.issued_at + timedelta(days=ln.days_offset),
            amount=amount, percentage=ln.percentage, position=ln.position))
    DocumentDueDate.objects.bulk_create(objs)
