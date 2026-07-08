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
# TODO B5: 'delivery_note':'DN', 'settlement':'ST'.
DOC_PREFIXES = {
    'quote': 'OF',          # oferta
    'sales_order': 'SO',    # comanda (B3b) — seqüència independent de la d'ofertes
    'work_order': 'WO',     # encàrrec / ordre de treball (B4a) — contenidor d'execució
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


def effective_payment_terms(document):
    """Condició de pagament efectiva: la del document, si no la del customer, si no cap.
    Genèric per a qualsevol document comercial (Quote, SalesOrder…)."""
    if document.payment_terms_id:
        return document.payment_terms
    if document.customer_id:
        return document.customer.payment_terms
    return None


def generate_due_dates(document):
    """Esborra i regenera els venciments materialitzats del document des del payment_terms efectiu.

    Genèric per a Quote (oferta) i SalesOrder (comanda): resol la FK correcta de DocumentDueDate
    segons el tipus. Només genera si el document té `issued_at` i una condició de pagament
    efectiva. Import de cada fracció = (total × pct / 100).quantize(0.01); la ÚLTIMA fracció =
    total − Σ anteriors (ajust del cèntim), de manera que la suma SEMPRE quadra exacta amb el total.
    """
    from .models import DocumentDueDate, Quote
    document.due_dates.all().delete()
    terms = effective_payment_terms(document)
    if not terms or not document.issued_at:
        return
    lines = list(terms.lines.all())
    if not lines:
        return
    fk = 'quote' if isinstance(document, Quote) else 'sales_order'
    total = Decimal(document.total or 0)
    allocated = Decimal('0')
    objs = []
    for i, ln in enumerate(lines):
        if i < len(lines) - 1:
            amount = (total * ln.percentage / 100).quantize(_CENT, rounding=ROUND_HALF_UP)
        else:
            amount = total - allocated   # última fracció: la suma quadra exacta amb total
        allocated += amount
        objs.append(DocumentDueDate(
            **{fk: document}, due_date=document.issued_at + timedelta(days=ln.days_offset),
            amount=amount, percentage=ln.percentage, position=ln.position))
    DocumentDueDate.objects.bulk_create(objs)


def convert_quote_to_order(quote, user=None):
    """Converteix una oferta ENVIADA en una comanda de venda (IRREVERSIBLE, B3b).

    Guards (tots abans de tocar res): l'oferta ha d'estar SENT, tenir ≥1 línia i no haver estat
    convertida encara (source_quote unique). Execució atòmica (patró clone_model_for_qa):
      1. crea la SalesOrder (customer, payment_terms EFECTIUS congelats com a override, issued_at
         = avui, source_quote, numeració SO nova),
      2. clona cada QuoteLine → SalesOrderLine amb pk=None i preus CONGELATS (còpia de valors),
      3. recalcula totals + venciments sobre la comanda,
      4. SEGELLA l'oferta (status=ACCEPTED; el guard DRAFT-only de QuoteLine bloqueja tota edició
         posterior de línies).
    NO hi ha reversió per disseny: l'única sortida és status=CANCELLED de la comanda (que NO
    reobre l'oferta). Retorna la SalesOrder creada.
    """
    from django.core.exceptions import ValidationError
    from .models import SalesOrder, SalesOrderLine
    if quote.status != 'SENT':
        raise ValidationError("Només es pot convertir en comanda una oferta enviada (SENT).")
    lines = list(quote.lines.all())
    if not lines:
        raise ValidationError("L'oferta no té cap línia; no es pot convertir en comanda.")
    if SalesOrder.objects.filter(source_quote=quote).exists():
        raise ValidationError("Aquesta oferta ja s'ha convertit en comanda.")
    with transaction.atomic():
        order = SalesOrder.objects.create(
            customer=quote.customer,
            payment_terms=effective_payment_terms(quote),
            issued_at=timezone.now().date(),
            source_quote=quote,
            created_by=getattr(user, 'profile', None) if user is not None else None,
        )
        for ln in lines:
            SalesOrderLine.objects.create(
                order=order, product=ln.product, description=ln.description,
                quantity=ln.quantity, unit_price=ln.unit_price)
        order.recalculate_totals()   # compute_document_totals + generate_due_dates sobre la comanda
        quote.status = 'ACCEPTED'
        quote.save(update_fields=['status', 'updated_at'])
    order.refresh_from_db()
    return order


def close_work_order(work_order, user=None, cancel_pending=False):
    """Tanca un WorkOrder. SEPARACIÓ DE DEPARTAMENTS (decisió Agus 2026-07-08): el TÈCNIC
    tanca quan la feina està feta; el comercial REVISA DESPRÉS (en preu de venda, endpoint
    /review/, B4b-P2). Per tant el close NOMÉS mira si la feina està acabada.

    RETORNA SEMPRE un dict estructurat (mai llança per bloqueig):
        { closed: bool, blockers: [...], pending_proposals: [...] }

    Política:
      - Tasques InProgress o Paused del WO → BLOQUEGEN (feina inacabada; es recullen TOTES).
      - Extres off_recipe: JA NO BLOQUEGEN. Existeixen com a ModelTask (off_recipe=True) amb
        temps/tècnic/cost registrats — prou per tancar. El preu de venda encara no existeix
        quan el tècnic tanca.
      - Pending: NO bloquegen. Es retornen com a proposta; si cancel_pending=True es
        cancel·len creant una DEDUCTION (marcador, amount=0) i es deslliguen del WO.

    TODO B4c: el gate d'extres sense resolució comercial viu a generate_delivery_note()
    (emissió de l'albarà), NO aquí. Un albarà no s'emet amb extres sense preu de venda fixat.
    """
    from .models import WorkOrderAdjustment
    if work_order.status == 'CLOSED':
        return {'closed': True, 'blockers': [], 'pending_proposals': [], 'already_closed': True}

    with transaction.atomic():
        tasks = list(work_order.tasks.select_related('task_type').all())

        # Bloquejos: NOMÉS feina inacabada (InProgress/Paused). Es recullen TOTS junts.
        blockers = [{'model_task': t.pk, 'reason': t.status, 'task_type': t.task_type.code}
                    for t in tasks if t.status in ('InProgress', 'Paused')]

        pending = [t for t in tasks if t.status == 'Pending']
        pending_proposals = [{'model_task': t.pk, 'task_type': t.task_type.code} for t in pending]

        if blockers:
            return {'closed': False, 'blockers': blockers, 'pending_proposals': pending_proposals}
        if pending and not cancel_pending:
            return {'closed': False, 'blockers': [], 'pending_proposals': pending_proposals}

        # Deducció de les Pending (si el caller ho decideix): DEDUCTION reté FK a la ModelTask
        # (model/tècnic/task_type/cost) + deslligar del WO. amount=0 = marcador; el preu real el
        # posa l'albarà (B4c) des del price_snapshot. L'Adjustment conserva el vincle malgrat
        # el deslligat (work_order=NULL a la tasca), perquè B4c pugui valorar la deducció.
        if pending and cancel_pending:
            for t in pending:
                WorkOrderAdjustment.objects.create(
                    work_order=work_order, model_task=t, kind='DEDUCTION', amount=Decimal('0.00'),
                    description=f"Recepta no executada: {t.task_type.code}", resolved_by=user)
                t.work_order = None
                t.save(update_fields=['work_order', 'updated_at'])

        # Tancar.
        work_order.status = 'CLOSED'
        work_order.closed_at = timezone.now()
        work_order.closed_by = user
        work_order.save(update_fields=['status', 'closed_at', 'closed_by', 'updated_at'])

    return {'closed': True, 'blockers': [], 'pending_proposals': []}


def apply_commercial_review(work_order, items, user=None):
    """Revisió COMERCIAL d'un WO tancat (B4b, decisió Agus 2026-07-08): el comercial fixa el
    PREU DE VENDA dels extres i deduccions. Acte posterior i separat del tancament del tècnic.

    NO toca cap COST: WorkOrderAdjustment.amount és preu de VENDA; el cost real (temps ×
    hourly_rate) viu a la tasca i als timers, i no es replica aquí.

    items = [{model_task_id, kind, amount}]. `kind` ∈ EXTRA_BILL|EXTRA_ABSORB|DEDUCTION.
    `amount` Decimal quantize(0.01); ZERO és vàlid a qualsevol kind (la intenció de negoci
    —facturar/absorbir— la porta el `kind`, no l'import). Cap default de kind ni d'amount.

    get_or_create per (work_order, model_task, kind): així una DEDUCTION marcador creada pel
    close (amount=0) es RETROBA i se li fixa el preu, i un extra estrena el seu adjustment.
    Retorna la llista d'adjustments. Llança ValidationError (missatge clar) als guards.
    """
    from django.core.exceptions import ValidationError
    from .models import WorkOrderAdjustment
    KINDS = {'EXTRA_BILL', 'EXTRA_ABSORB', 'DEDUCTION'}
    if work_order.status != 'CLOSED':
        raise ValidationError("La revisió comercial només s'aplica a un encàrrec tancat.")
    # Tasques reviewables: les que pengen del WO ara O que hi han pertangut (deduïdes al tancar,
    # ara amb work_order=NULL però amb el seu Adjustment ancorat al WO).
    valid_ids = set(work_order.tasks.values_list('id', flat=True)) | set(
        work_order.adjustments.filter(model_task__isnull=False).values_list('model_task_id', flat=True))
    out = []
    with transaction.atomic():
        for it in (items or []):
            mt_id = it.get('model_task_id')
            kind = it.get('kind')
            if kind not in KINDS:
                raise ValidationError(f"kind invàlid: {kind!r}.")
            if mt_id not in valid_ids:
                raise ValidationError(f"La tasca {mt_id} no pertany a aquest encàrrec.")
            if it.get('amount') is None:
                raise ValidationError(f"Falta l'import per a la tasca {mt_id}.")
            amount = Decimal(str(it['amount'])).quantize(_CENT, rounding=ROUND_HALF_UP)
            adj, _ = WorkOrderAdjustment.objects.get_or_create(
                work_order=work_order, model_task_id=mt_id, kind=kind,
                defaults={'resolved_by': user})
            adj.amount = amount
            adj.resolved_by = user
            adj.save(update_fields=['amount', 'resolved_by'])
            out.append(adj)
    return out
