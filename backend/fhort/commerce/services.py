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

# Prefix de numeració per tipus de document (reinici anual, R5). Cada tipus té seqüència pròpia.
# TODO B5: 'settlement':'ST'.
DOC_PREFIXES = {
    'quote': 'OF',          # oferta
    'sales_order': 'SO',    # comanda (B3b) — seqüència independent de la d'ofertes
    'work_order': 'WO',     # encàrrec / ordre de treball (B4a) — contenidor d'execució
    'delivery_note': 'DN',  # albarà (B4c) — document derivat que agrega WorkOrders CLOSED
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


def assign_model_to_order_line(model, order_line, user=None):
    """Assigna un model a una línia de comanda i crea el seu WorkOrder ORDER (B4b). Congela
    price_snapshot i recipe_snapshot del Product de la línia (cap FK viva). MIGRA les tasques
    del model que avui pengen d'un COLLECTOR al nou ORDER (cap albarà existeix encara, B4c: la
    feina contractada no s'ha de facturar al calaix mensual). Retorna (work_order, warnings).

    Llança ValidationError als guards durs. `warnings` = avisos no bloquejants (p.ex. GTI).
    """
    from django.core.exceptions import ValidationError
    from .models import WorkOrder
    from fhort.tasks.models import ModelTask
    from fhort.tasks.services_c import _is_off_recipe

    order = order_line.order
    if order.status != 'OPEN':
        raise ValidationError("La comanda no està oberta (OPEN): no s'hi poden assignar models.")
    if model.customer_id != order.customer_id:
        raise ValidationError("El model i la comanda han de ser del mateix client.")
    if Decimal(order_line.qty_allocated or 0) >= Decimal(order_line.quantity or 0):
        raise ValidationError("La línia ja té tota la quantitat imputada (qty_allocated = quantity).")
    if WorkOrder.objects.filter(model=model, kind='ORDER', status='OPEN').exists():
        raise ValidationError("El model ja té un encàrrec (WO ORDER) actiu.")

    warnings = []
    if model.garment_type_item_id is None:
        warnings.append("El model no té garment_type_item: no es pot comprovar la compatibilitat.")

    with transaction.atomic():
        product = order_line.product
        recipe_codes = list(product.recipe_lines.values_list('task_code', flat=True))
        wo = WorkOrder.objects.create(
            customer_id=model.customer_id, model=model, order_line=order_line,
            kind='ORDER', origin='MANUAL', created_by=user,
            price_snapshot={'unit_price': str(order_line.unit_price or '0'),
                            'product_code': getattr(product, 'code', None)},
            recipe_snapshot={'task_codes': recipe_codes})

        # Imputació de cartera: +1 unitat (quantize 0.01).
        order_line.qty_allocated = (Decimal(order_line.qty_allocated or 0) + Decimal('1')).quantize(_CENT)
        order_line.save(update_fields=['qty_allocated'])

        # Migració del col·lector: les tasques del model que pengen d'un COLLECTOR (i encara no
        # s'han albaranat — cap albarà existeix a B4b) es mouen al nou ORDER, amb off_recipe
        # recalculat contra la recepta congelada. TODO B4c: excloure aquí les tasques albaranades.
        migrated = 0
        for task in ModelTask.objects.filter(
                model=model, work_order__kind='COLLECTOR').select_related('task_type'):
            task.work_order = wo
            task.off_recipe = _is_off_recipe(task, wo)
            task.save(update_fields=['work_order', 'off_recipe', 'updated_at'])
            migrated += 1

    return wo, {'warnings': warnings, 'migrated_tasks': migrated}


def generate_delivery_note(work_orders, user=None):
    """Genera un albarà DRAFT amb línies PROPOSADES a partir d'1..N WorkOrder CLOSED del MATEIX
    customer (B4c, el cor del cas Brownie). El sistema PROPOSA; el comercial edita en DRAFT.

    GUARDS (es recopilen TOTS i es retornen junts com a ValidationError):
      - work_orders no buit · tots CLOSED · tots del mateix customer · cap ja albaranat.
      - GATE D'EXTRES (el TODO de B4b, ara viu AQUÍ): cap ModelTask off_recipe=True sense un
        WorkOrderAdjustment que la resolgui → si n'hi ha, bloqueja llistant-les ("pendent de
        revisió comercial"). Un albarà no s'emet amb extres sense preu de venda fixat.

    LÍNIES (per WO, en ordre TASK · EXTRA · DEDUCTION · EXPENSE):
      - TASK (Done, off_recipe=False): ORDER → unit_price del price_snapshot (preu contractat),
        quantity=1. COLLECTOR → unit_price PROPOSAT 0, quantity = minuts reals (Σ TimerEntrada);
        el Salva posa preu en DRAFT (NO s'inventa tarifa de venda per defecte).
      - EXTRA (Adjustment EXTRA_BILL): unit_price=amount, quantity=1. (EXTRA_ABSORB: cap línia.)
      - DEDUCTION (Adjustment DEDUCTION): línia NEGATIVA. Import proposat: ORDER+model_task →
        −(preu del price_snapshot); si no → −amount de l'Adjustment; si tots dos 0 → línia a 0.
      - EXPENSE (Expense del WO): unit_price=sale_price, quantity=quantity.

    El `product` de la línia (NULLABLE) porta el tipus d'IVA: ORDER → order_line.product;
    COLLECTOR/lliure → None (compute_document_totals tracta None com a 0%). L'albarà neix DRAFT,
    totals calculats (via signals), SENSE venciments. Marca cada WO com albaranat (ja en DRAFT,
    per evitar doble inclusió; esborrar el DRAFT allibera els WO via SET_NULL). Retorna la nota.
    """
    from django.core.exceptions import ValidationError
    from django.db.models import Sum
    from .models import DeliveryNote, DeliveryNoteLine, WorkOrderAdjustment

    wos = list(work_orders)
    errors = []
    if not wos:
        raise ValidationError("Cap encàrrec seleccionat per a l'albarà.")

    # ── GUARDS d'agregació (es recopilen tots) ──
    customers = {wo.customer_id for wo in wos}
    if len(customers) > 1:
        errors.append("Tots els encàrrecs han de ser del mateix client.")
    for wo in wos:
        if wo.status != 'CLOSED':
            errors.append(f"L'encàrrec {wo.number} no està tancat (CLOSED).")
        if wo.delivery_note_id is not None:
            errors.append(f"L'encàrrec {wo.number} ja està albaranat.")

    # ── GATE D'EXTRES: off_recipe=True sense Adjustment que la resolgui ──
    for wo in wos:
        resolved = set(wo.adjustments.filter(model_task__isnull=False)
                       .values_list('model_task_id', flat=True))
        pend = [t.task_type.code for t in wo.tasks.select_related('task_type')
                .filter(off_recipe=True).exclude(pk__in=resolved)]
        if pend:
            errors.append(
                f"L'encàrrec {wo.number} té extres pendents de revisió comercial: "
                f"{', '.join(pend)}.")

    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        dn = DeliveryNote.objects.create(
            customer_id=wos[0].customer_id,
            created_by=user,
        )
        pos = 0

        def _add(line_kind, unit_price, quantity, description, product=None,
                 work_order=None, model_task=None, expense=None, adjustment=None,
                 internal_minutes=None):
            nonlocal pos
            pos += 1
            DeliveryNoteLine(
                delivery_note=dn, line_kind=line_kind,
                unit_price=Decimal(unit_price).quantize(_CENT, rounding=ROUND_HALF_UP),
                quantity=Decimal(quantity).quantize(_CENT, rounding=ROUND_HALF_UP),
                description=description[:300], product=product, work_order=work_order,
                model_task=model_task, expense=expense, adjustment=adjustment, position=pos,
                internal_minutes=(Decimal(internal_minutes) if internal_minutes is not None else None),
            ).save()

        for wo in wos:
            order_product = wo.order_line.product if wo.order_line_id else None
            snap_price = Decimal(str(wo.price_snapshot.get('unit_price') or '0'))

            # TASK — tasques acabades de recepta (off_recipe=False).
            for t in wo.tasks.select_related('task_type', 'model').filter(
                    status='Done', off_recipe=False):
                label = f"{t.task_type.name} · {t.model.codi_intern}"
                if wo.kind == 'COLLECTOR':
                    # Temps intern = lògica comercial, FORA del document (decisió Agus). Els minuts
                    # es guarden a internal_minutes; la línia surt amb quantity=1 i sense "(N min)"
                    # a la descripció (el PDF mai els mostra). El Salva posa preu en DRAFT.
                    minutes = t.timers.aggregate(m=Sum('minuts'))['m'] or 0
                    _add('TASK', Decimal('0'), Decimal('1'), label,
                         product=None, work_order=wo, model_task=t,
                         internal_minutes=Decimal(minutes))
                else:
                    _add('TASK', snap_price, Decimal('1'), label,
                         product=order_product, work_order=wo, model_task=t)

            # EXTRA — extres facturables (EXTRA_ABSORB no genera línia).
            for adj in wo.adjustments.filter(kind='EXTRA_BILL'):
                _add('EXTRA', Decimal(adj.amount or 0), Decimal('1'),
                     adj.description or "Extra", product=order_product, work_order=wo,
                     model_task=adj.model_task, adjustment=adj)

            # DEDUCTION — línia negativa (recepta no executada / concepte lliure).
            for adj in wo.adjustments.filter(kind='DEDUCTION'):
                if adj.model_task_id and wo.kind == 'ORDER' and snap_price:
                    proposed = -snap_price
                else:
                    proposed = -abs(Decimal(adj.amount or 0))
                desc = adj.description or "Deducció"
                _add('DEDUCTION', proposed, Decimal('1'), desc,
                     product=order_product, work_order=wo, model_task=adj.model_task,
                     adjustment=adj)

            # EXPENSE — línies externes (servei extern / mercaderia).
            for exp in wo.expenses.select_related('product').all():
                desc = exp.description or (exp.product.name if exp.product_id else "Despesa")
                _add('EXPENSE', Decimal(exp.sale_price or 0), Decimal(exp.quantity or 0), desc,
                     product=exp.product, work_order=wo, expense=exp)

            wo.delivery_note = dn
            wo.save(update_fields=['delivery_note', 'updated_at'])

    dn.refresh_from_db()
    return dn


def issue_delivery_note(delivery_note, user=None):
    """Emet un albarà DRAFT→ISSUED (B4c). Guard: almenys 1 línia. Un cop ISSUED les línies queden
    congelades (guard DRAFT-only de DeliveryNoteLine, patró Quote). Llança ValidationError."""
    from django.core.exceptions import ValidationError
    if delivery_note.status != 'DRAFT':
        raise ValidationError("Només es pot emetre un albarà en esborrany (DRAFT).")
    if not delivery_note.lines.exists():
        raise ValidationError("L'albarà no té cap línia; no es pot emetre.")
    with transaction.atomic():
        delivery_note.status = 'ISSUED'
        delivery_note.issued_by = user
        if not delivery_note.issued_at:
            delivery_note.issued_at = timezone.now().date()
        delivery_note.save(update_fields=['status', 'issued_by', 'issued_at', 'updated_at'])
    return delivery_note


# ── Albarà v2 — safata d'albaranables per model ──────────────────────────────────────────

def _model_header(model):
    """Capçalera de bloc-model per a la safata i la fitxa (camps definitoris, diagnosi BLOC 2+3)."""
    if model is None:
        return {'id': None, 'codi_intern': '', 'codi_client': '', 'nom_prenda': '',
                'collection': '', 'temporada': '', 'any': None}
    return {
        'id': model.id,
        'codi_intern': model.codi_intern,
        'codi_client': model.codi_client or '',
        'nom_prenda': model.nom_prenda or '',
        'collection': model.collection or '',
        'temporada': model.temporada or '',
        'any': model.any,
    }


def get_billable_items(customer):
    """Safata d'albaranables d'un client (v2), agrupada per MODEL. Parteix de ModelTask (NO de
    WorkOrder): així recull també la feina amb work_order=NULL que el flux v1 no podia veure (R2
    de la diagnosi). Un ítem surt de la safata quan JA té una línia d'albarà (DRAFT o ISSUED):
    `delivery_note_lines__isnull=True` evita el doble comptatge; esborrar el DRAFT (CASCADE de
    línies) el retorna. NO filtra per `facturable` (descartat): "no cobrar" es decideix a la línia
    (preu 0). Lectura pura, no persisteix res. Els ítems sense model resoluble van a un bloc
    `model=None` (no es descarten silenciosament)."""
    from django.db.models import Sum
    from fhort.tasks.models import ModelTask
    from .models import WorkOrderAdjustment, Expense

    groups = {}  # key (model_id o None) -> {'model': header, 'items': [...]}

    def _bucket(model):
        key = model.id if model is not None else None
        g = groups.get(key)
        if g is None:
            g = {'model': _model_header(model), 'items': []}
            groups[key] = g
        return g

    # TASK — ModelTask Done sense línia d'albarà (el model FK mai és null).
    for t in (ModelTask.objects
              .filter(model__customer=customer, status='Done', delivery_note_lines__isnull=True)
              .select_related('task_type', 'model', 'work_order')):
        wo = t.work_order
        if wo is not None and wo.kind == 'ORDER':
            price = Decimal(str((wo.price_snapshot or {}).get('unit_price') or '0')).quantize(_CENT)
        else:
            price = Decimal('0.00')   # COLLECTOR o work_order=NULL: el Salva posa preu en DRAFT
        minutes = t.timers.aggregate(m=Sum('minuts'))['m'] or 0
        _bucket(t.model)['items'].append({
            'kind': 'TASK', 'ref': t.task_type.code,
            'description': f"{t.task_type.name} · {t.model.codi_intern}",
            'proposed_qty': str(Decimal('1.00')), 'proposed_unit': None,
            'proposed_price': str(price), 'internal_minutes': str(Decimal(minutes)),
            'source_dates': {'started_at': t.started_at.isoformat() if t.started_at else None,
                             'finished_at': t.finished_at.isoformat() if t.finished_at else None},
            'model_task_id': t.id, 'work_order_id': wo.id if wo else None,
        })

    # EXTRA / DEDUCTION — WorkOrderAdjustment sense línia, via model_task.model o wo.model.
    for adj in (WorkOrderAdjustment.objects
                .filter(work_order__customer=customer, kind__in=['EXTRA_BILL', 'DEDUCTION'],
                        delivery_note_lines__isnull=True)
                .select_related('work_order__model', 'model_task__model')):
        model = (adj.model_task.model if adj.model_task_id else None) or adj.work_order.model
        if adj.kind == 'EXTRA_BILL':
            kind, price = 'EXTRA', Decimal(adj.amount or 0).quantize(_CENT)
        else:
            kind, price = 'DEDUCTION', (-abs(Decimal(adj.amount or 0))).quantize(_CENT)
        _bucket(model)['items'].append({
            'kind': kind, 'ref': adj.kind,
            'description': adj.description or ('Extra' if kind == 'EXTRA' else 'Deducció'),
            'proposed_qty': str(Decimal('1.00')), 'proposed_unit': None,
            'proposed_price': str(price), 'internal_minutes': None,
            'source_dates': {'started_at': None,
                             'finished_at': adj.resolved_at.isoformat() if adj.resolved_at else None},
            'adjustment_id': adj.id, 'work_order_id': adj.work_order_id,
        })

    # EXPENSE — Expense sense línia, via wo.model. Preu = sale_price, qty = quantity.
    for exp in (Expense.objects
                .filter(work_order__customer=customer, delivery_note_lines__isnull=True)
                .select_related('work_order__model', 'product')):
        _bucket(exp.work_order.model)['items'].append({
            'kind': 'EXPENSE', 'ref': exp.product.code if exp.product_id else None,
            'description': exp.description or (exp.product.name if exp.product_id else 'Despesa'),
            'proposed_qty': str(Decimal(exp.quantity or 0).quantize(_CENT)), 'proposed_unit': None,
            'proposed_price': str(Decimal(exp.sale_price or 0).quantize(_CENT)),
            'internal_minutes': None,
            'source_dates': {'started_at': None,
                             'finished_at': exp.incurred_at.isoformat() if exp.incurred_at else None},
            'expense_id': exp.id, 'work_order_id': exp.work_order_id,
        })

    # Ordena per codi_intern (el bloc sense model, codi_intern='', queda primer).
    return sorted(groups.values(), key=lambda g: g['model']['codi_intern'] or '')


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
            # UN SOL ajust per (work_order, model_task): el kind és atribut mutable, no clau.
            # update_or_create retroba l'ajust existent (p.ex. la DEDUCTION marcador del close)
            # i n'actualitza kind + amount sense crear una segona fila.
            adj, _ = WorkOrderAdjustment.objects.update_or_create(
                work_order=work_order, model_task_id=mt_id,
                defaults={'kind': kind, 'amount': amount, 'resolved_by': user})
            out.append(adj)
    return out
