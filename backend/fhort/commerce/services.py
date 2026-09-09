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
# Els minuts que acaben a `internal_minutes` (i d'aquí al cost intern) es llegeixen amb la
# MATEIXA regla d'higiene que la resta del sistema: un tram desbocat no és temps treballat.
from fhort.tasks.services_i import TRAMS_SANS

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
        if line.product_id:
            rate = Decimal(line.product.tax_rate).quantize(_CENT)
        else:
            # Línia sense article de catàleg: si ve d'un WorkOrder amb tax_rate congelat al
            # price_snapshot (cas del WO orfe, order_line buida → product None), usem aquell tipus
            # en lloc de caure a 0% (D2). Quote/SalesOrderLine no tenen work_order → cap canvi.
            snap_rate = None
            wo = getattr(line, 'work_order', None) if getattr(line, 'work_order_id', None) else None
            if wo is not None:
                snap_rate = (wo.price_snapshot or {}).get('tax_rate')
            rate = Decimal(str(snap_rate)).quantize(_CENT) if snap_rate is not None else Decimal('0.00')
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
    reobre l'oferta).

    PROPAGACIÓ DEL VINCLE PREPARATORI (E3): després de clonar les línies, cada
    QuoteLineModelIntent es projecta sobre la SalesOrderLine clonada corresponent, en ordre:
      - model LLIURE (cap WO ORDER OPEN) → assign_model_to_order_line normal,
      - model amb WO ORFE (order_line null, orphaned_from_line no null) → reattach_orphan_to_line,
      - model OCUPAT (WO ORDER OPEN lligat a una ALTRA comanda) → NO viatja; s'informa a
        'intent_conflicts'. La conversió NO es bloqueja MAI per conflictes: es completa i informa.
    Els intents es queden a la Quote com a registre (queda ACCEPTED i segellada).

    Retorna (SalesOrder creada, meta) on meta = {'intent_conflicts': [...], 'assigned': N,
    'reattached': N}.
    """
    from django.core.exceptions import ValidationError
    from .models import SalesOrder, SalesOrderLine, WorkOrder
    if quote.status != 'SENT':
        raise ValidationError("Només es pot convertir en comanda una oferta enviada (SENT).")
    lines = list(quote.lines.all())
    if not lines:
        raise ValidationError("L'oferta no té cap línia; no es pot convertir en comanda.")
    if SalesOrder.objects.filter(source_quote=quote).exists():
        raise ValidationError("Aquesta oferta ja s'ha convertit en comanda.")
    profile = getattr(user, 'profile', None) if user is not None else None
    conflicts, assigned, reattached = [], 0, 0
    with transaction.atomic():
        order = SalesOrder.objects.create(
            customer=quote.customer,
            payment_terms=effective_payment_terms(quote),
            issued_at=timezone.now().date(),
            source_quote=quote,
            created_by=profile,
        )
        # Clona cada línia guardant el parell (QuoteLine origen → SalesOrderLine clonada) per
        # poder projectar-hi després les intencions de model.
        clone_pairs = []
        for ln in lines:
            sol = SalesOrderLine.objects.create(
                order=order, product=ln.product, description=ln.description,
                quantity=ln.quantity, unit_price=ln.unit_price)
            clone_pairs.append((ln, sol))
        order.recalculate_totals()   # compute_document_totals + generate_due_dates sobre la comanda

        # Propagació de les intencions: cada model d'una línia d'oferta cap a la línia clonada.
        for ln, sol in clone_pairs:
            for intent in ln.model_intents.select_related('model').order_by('position', 'id'):
                model = intent.model
                open_order_wos = WorkOrder.objects.filter(model=model, kind='ORDER', status='OPEN')
                orphan = open_order_wos.filter(order_line__isnull=True).first()
                active = open_order_wos.filter(order_line__isnull=False).first()
                try:
                    if orphan is not None:
                        reattach_orphan_to_line(orphan, sol, user=profile)
                        reattached += 1
                    elif active is not None:
                        # Model ocupat per un encàrrec viu d'una ALTRA comanda: no viatja, s'informa.
                        conflicts.append({
                            'model': model.id, 'model_codi': model.codi_intern,
                            'reason': 'busy',
                            'work_order': active.number,
                            'order': getattr(active.order_line.order, 'document_number', None),
                        })
                    else:
                        assign_model_to_order_line(model, sol, user=profile)
                        assigned += 1
                except ValidationError as e:
                    # Un guard d'assign/reattach ha fallat (p.ex. línia sense quantitat disponible):
                    # la conversió NO es bloqueja; es registra com a conflicte i continua.
                    conflicts.append({
                        'model': model.id, 'model_codi': model.codi_intern,
                        'reason': 'guard', 'detail': '; '.join(e.messages),
                    })

        quote.status = 'ACCEPTED'
        quote.save(update_fields=['status', 'updated_at'])
    order.refresh_from_db()
    return order, {'intent_conflicts': conflicts, 'assigned': assigned, 'reattached': reattached}


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

    El gate d'extres sense resolució comercial és IMPLÍCIT a la safata (`_extres_albaranables`):
    un off_recipe sense Adjustment que el resolgui no hi surt, o sigui que no es pot albaranar
    fins que el comercial li fixi preu de venda. NO viu aquí.
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


def _assign_model_core(model, order_line, user=None):
    """NUCLI d'assignació d'UN model a una línia: guards durs + creació del WorkOrder ORDER
    (snapshots congelats) + imputació +1 a qty_allocated + migració de les tasques del col·lector.
    NO obre transacció: el CALLER n'és responsable (wrapper single o batch), perquè el batch pugui
    ser tot-o-res en UNA sola transacció sense niar-ne. Muta `order_line` en memòria (qty_allocated)
    perquè el batch acumuli correctament entre models. Retorna (work_order, meta).

    Llança ValidationError als guards durs. `meta.warnings` = avisos no bloquejants (p.ex. GTI).
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

    product = order_line.product
    recipe_codes = list(product.recipe_lines.values_list('task_code', flat=True))
    wo = WorkOrder.objects.create(
        customer_id=model.customer_id, model=model, order_line=order_line,
        kind='ORDER', origin='MANUAL', created_by=user,
        price_snapshot={'unit_price': str(order_line.unit_price or '0'),
                        'product_code': getattr(product, 'code', None),
                        # Congelem també el tipus d'IVA: si el WO es desassigna (order_line→None),
                        # la línia d'albarà perd el product viu i el seu tipus; el snapshot el
                        # conserva perquè compute_document_totals no caigui a 0% (D2).
                        'tax_rate': str(getattr(product, 'tax_rate', '0'))},
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


def assign_model_to_order_line(model, order_line, user=None):
    """Assigna UN model a una línia de comanda i crea el seu WorkOrder ORDER (B4b). Wrapper
    transaccional del nucli (`_assign_model_core`); manté el contracte públic existent. Retorna
    (work_order, meta). Llança ValidationError als guards durs.
    """
    with transaction.atomic():
        return _assign_model_core(model, order_line, user=user)


def assign_models_to_order_line_batch(order_line_id, model_ids, user=None):
    """Assigna N models a UNA línia de comanda en UNA sola transacció, TOT-O-RES (Sprint C · H1).

    - `select_for_update` sobre la SalesOrderLine → serialitza els batches concurrents i evita el
      lost-update de qty_allocated (read-modify-write per model).
    - Valida la capacitat CONJUNTA ABANS d'assignar res: len(model_ids) ≤ quantity − qty_allocated;
      si no, ValidationError amb el màxim disponible (el caller → 400).
    - Si QUALSEVOL model del lot viola un guard dur (client, dualitat WO obert, no trobat…), CAP
      s'assigna (rollback de tota la transacció) i l'error identifica el model conflictiu.

    Retorna (work_orders, warnings_agregats).
    """
    from django.core.exceptions import ValidationError
    from .models import SalesOrderLine
    from fhort.models_app.models import Model

    with transaction.atomic():
        line = (SalesOrderLine.objects
                .select_for_update()
                .select_related('order', 'product')
                .get(pk=order_line_id))
        available = Decimal(line.quantity or 0) - Decimal(line.qty_allocated or 0)
        if Decimal(len(model_ids)) > available:
            raise ValidationError(
                f"Capacitat insuficient: la línia admet {int(available)} model(s) més "
                f"(n'has demanat {len(model_ids)}).")

        work_orders, warnings = [], []
        for mid in model_ids:
            model = Model.objects.filter(pk=mid).first()
            if model is None:
                raise ValidationError(f"Model {mid} no trobat.")
            try:
                wo, meta = _assign_model_core(model, line, user=user)
            except ValidationError as e:
                # Tot-o-res: identifica el model conflictiu i deixa que el rollback ho desfaci tot.
                raise ValidationError(f"Model {model.codi_intern or mid}: {'; '.join(e.messages)}")
            work_orders.append(wo)
            warnings.extend(meta['warnings'])
        return work_orders, warnings


def create_quote_line_intents_bulk(quote_line, model_ids, user=None):
    """Crea intents model↔línia d'oferta en LOT (Sprint C · H1). Simètric al batch de comanda però
    barat (intenció pura: no toca WO ni cartera). IGNORA silenciosament els duplicats ja existents
    (unique_together quote_line+model). Guards mirall del serializer: oferta DRAFT/SENT + coherència
    de client. Retorna {created:[ids], skipped:[model_ids]}.
    """
    from django.core.exceptions import ValidationError
    from .models import QuoteLineModelIntent
    from fhort.models_app.models import Model

    quote = quote_line.quote
    if quote.status not in ('DRAFT', 'SENT'):
        raise ValidationError(
            "Només es poden editar intencions de models mentre l'oferta negocia (DRAFT o SENT).")

    existing = set(QuoteLineModelIntent.objects
                   .filter(quote_line=quote_line).values_list('model_id', flat=True))

    created, skipped = [], []
    with transaction.atomic():
        for mid in model_ids:
            mid = int(mid)
            if mid in existing:
                skipped.append(mid)
                continue
            model = Model.objects.filter(pk=mid).first()
            if model is None:
                raise ValidationError(f"Model {mid} no trobat.")
            if model.customer_id != quote.customer_id:
                raise ValidationError(
                    f"Model {model.codi_intern or mid}: el model i l'oferta han de ser del mateix client.")
            intent = QuoteLineModelIntent.objects.create(
                quote_line=quote_line, model=model, created_by=user)
            created.append(intent.id)
            existing.add(mid)
    return {'created': created, 'skipped': skipped}


def unassign_model_from_order_line(work_order, user=None):
    """Desassigna un model d'una línia de comanda: ORFANDA el WorkOrder ORDER (simètric a
    assign_model_to_order_line). Allibera una unitat de cartera de la línia, mou la referència
    d'order_line a orphaned_from_line (traça) i deixa order_line=None. Retorna el WorkOrder.

    Llança ValidationError als guards durs (abans de la transacció).
    """
    from django.core.exceptions import ValidationError
    from .models import DeliveryNoteLine

    if work_order.kind != 'ORDER':
        raise ValidationError("Només es pot desassignar un WorkOrder ORDER (el col·lector no té línia).")
    if work_order.status != 'OPEN':
        raise ValidationError("El WorkOrder ja està tancat (CLOSED): no es pot desassignar.")
    if work_order.order_line_id is None:
        raise ValidationError("Aquest WorkOrder no té cap línia de comanda assignada.")
    if DeliveryNoteLine.objects.filter(work_order=work_order).exists():
        raise ValidationError("Aquest WorkOrder ja està albaranat: no es pot desassignar per API.")

    with transaction.atomic():
        line = work_order.order_line
        # Allibera 1 unitat de cartera (clamp a 0, mai negatiu; mateix quantize que l'assignació).
        line.qty_allocated = max(
            Decimal('0'), Decimal(line.qty_allocated or 0) - Decimal('1')).quantize(_CENT)
        line.save(update_fields=['qty_allocated'])

        # Orfandat: mou la traça a orphaned_from_line i buida order_line (mateix acte).
        work_order.orphaned_from_line = line
        work_order.order_line = None
        # Les ModelTask migrades NO es toquen: es queden intactes al WO orfe. Decisió conscient
        # (D3) — la feina real ja executada no s'ha de revertir al col·lector; el WO orfe segueix
        # sent el seu contenidor d'execució fins que es reassigni o es tanqui. NO és un oblit.
        work_order.save(update_fields=['orphaned_from_line', 'order_line', 'updated_at'])

    return work_order


def reattach_orphan_to_line(work_order, new_line, user=None):
    """Re-adopta un WorkOrder ORFE enganxant-lo a una línia de comanda NOVA (camí invers de
    unassign_model_from_order_line, E4). Simetria estricta amb els 7 guards espill de la diagnosi
    (P4). Imputa +1 de cartera a la línia nova, neteja la traça d'orfandat i RE-CONGELA els
    snapshots contra el product de la línia NOVA (decisió Agus: opció 2). Retorna el WorkOrder.

    Llança ValidationError als guards durs (abans de la transacció).
    """
    from django.core.exceptions import ValidationError
    from .models import DeliveryNoteLine

    order = new_line.order
    # 7 guards espill (P4): mirall d'assign_model_to_order_line + unassign_model_from_order_line.
    if work_order.kind != 'ORDER':
        raise ValidationError("Només es pot re-adoptar un WorkOrder ORDER (el col·lector no té línia).")
    if work_order.status != 'OPEN':
        raise ValidationError("El WorkOrder ja està tancat (CLOSED): no es pot re-adoptar.")
    if work_order.order_line_id is not None:
        raise ValidationError("Aquest WorkOrder ja té una línia assignada: no és orfe.")
    if order.status != 'OPEN':
        raise ValidationError("La comanda de destí no està oberta (OPEN): no s'hi pot re-adoptar.")
    if work_order.customer_id != order.customer_id:
        raise ValidationError("El WorkOrder i la comanda de destí han de ser del mateix client.")
    if Decimal(new_line.qty_allocated or 0) >= Decimal(new_line.quantity or 0):
        raise ValidationError("La línia de destí ja té tota la quantitat imputada (qty_allocated = quantity).")
    if DeliveryNoteLine.objects.filter(work_order=work_order).exists():
        raise ValidationError("Aquest WorkOrder ja està albaranat: no es pot re-adoptar per API.")

    with transaction.atomic():
        product = new_line.product
        recipe_codes = list(product.recipe_lines.values_list('task_code', flat=True))

        # Imputació de cartera a la línia NOVA: +1 unitat (mirall exacte d'assign).
        new_line.qty_allocated = (Decimal(new_line.qty_allocated or 0) + Decimal('1')).quantize(_CENT)
        new_line.save(update_fields=['qty_allocated'])

        # Re-adopció: enganxa a la línia nova i NETEJA la traça d'orfandat (torna a null — l'orfandat
        # és transitòria, no història; decisió Agus 2026-07-20).
        work_order.order_line = new_line
        work_order.orphaned_from_line = None
        # RE-CONGELA els snapshots contra el product de la línia NOVA (opció 2, decisió Agus): el
        # preu contractat, el tipus d'IVA i la recepta queden alineats amb la comanda a què s'enganxa.
        # Idèntic a assign_model_to_order_line (cap FK viva; l'albarà llegirà aquests valors congelats).
        work_order.price_snapshot = {
            'unit_price': str(new_line.unit_price or '0'),
            'product_code': getattr(product, 'code', None),
            'tax_rate': str(getattr(product, 'tax_rate', '0')),
        }
        work_order.recipe_snapshot = {'task_codes': recipe_codes}
        # Els WorkOrderAdjustment ja registrats NO es re-valoren: són fets històrics contra el preu
        # del seu moment (decisió Agus 2026-07-20). El re-congelat només afecta les línies d'albarà
        # que es proposin d'ara endavant, no els ajustos ja resolts.
        work_order.save(update_fields=['order_line', 'orphaned_from_line',
                                       'price_snapshot', 'recipe_snapshot', 'updated_at'])

    return work_order


class ContradiccioDePacte(Exception):
    """L'albarà diu una cosa del pacte i el pacte n'ha passat a dir una altra. Porta la LLISTA
    de contradiccions (`.contradiccions`), no un text: qui la mostri ha de poder dir cada cas
    amb noms i números, i en l'idioma de qui mira.

    Excepció PRÒPIA i no un `ValidationError` més perquè no és el mateix tipus de refús: els
    altres guards d'emissió diuen «això encara no es pot fer» (400) i aquest diu «això que tens
    davant ja no és cert» (409) —un CONFLICTE amb un estat que ha canviat sota els peus— i
    demana un gest diferent, que és anar a la comanda o convertir la línia a mà.
    """

    def __init__(self, contradiccions):
        self.contradiccions = contradiccions
        super().__init__(f'{len(contradiccions)} contradicció/ons de pacte')


def contradiccions_de_pacte(delivery_note):
    """LES LÍNIES QUE JA NO DIUEN LA VERITAT sobre el pacte, comparades amb el numeral VIGENT.

    🚨 EL FORAT QUE TANCA. El numeral d'una línia de comanda és editable (FIT-5) i el veredicte
    d'una volta es resol EN OBRIR-LA. Entre l'una i l'altra hi cap que algú pugi
    `rounds_included` després que el comercial hagi afegit la volta a l'albarà com a
    `encarrec_directe` amb preu lliure: llavors el document diu «encàrrec directe sense
    pressupost» d'una volta que ARA hi entra, i el `consumit` del pacte se la compta com a
    gastada del numeral. El mateix a l'inrevés: una línia facturada sota el pacte la volta de la
    qual ara en surt.

    Es mira ABANS de congelar, i **només informa**: qui decideix és qui emet. Auto-convertir la
    línia seria canviar el preu d'un document que una persona ja ha compost —el preu d'una volta
    directa és LLIURE i no el fixa cap pacte, o sigui que «convertir-la» voldria dir triar-li un
    import nou sense preguntar.

    Retorna `[{model, model_id, ronda, ronda_id, numeral_vigent, linia, ara}]`, amb `ara`
    `'dins'` o `'fora'` segons on cau la volta AVUI. Llista buida = res a dir.
    """
    from fhort.tasks.services_r import numeral_efectiu

    fora_de_lloc, pactes = [], {}
    for linia in (delivery_note.lines
                  .prefetch_related('rondes__model')
                  .order_by('position', 'id')):
        for ronda in linia.rondes.all():
            if ronda.model_id not in pactes:
                pactes[ronda.model_id] = numeral_efectiu(ronda.model)
            pacte, numeral = pactes[ronda.model_id]
            # 🚨 SENSE PACTE VIU NO HI HA CONTRADICCIÓ POSSIBLE, i tractar-ho com si n'hi hagués
            # era un FALS POSITIU: `numeral_efectiu` torna `(None, None)` quan el model no té cap
            # comanda, i llavors `fora` surt False i tota línia DIRECTA quedava acusada de
            # contradir un pacte que no existeix —quan justament diu la veritat: «encàrrec directe
            # sense pressupost». Els dos `None` de `numeral_efectiu` volen dir coses diferents i
            # aquí la diferència mana: `(None, None)` = cap pacte · `(linia, None)` = pacte sense
            # límit, on una volta directa SÍ que contradiu (cap volta en pot sortir).
            #
            # I un model desassignat després de compondre tampoc no s'acusa: la línia conserva la
            # seva `linia_comanda` congelada i el document segueix dient de quina venda venia. El
            # que aquest guard vigila és que el NUMERAL s'hagi mogut, no que l'assignació canviï.
            if pacte is None:
                continue
            fora = numeral is not None and ronda.seq > numeral
            # La contradicció és que la MARCA de la línia i el veredicte d'ara no coincideixin.
            # Les dues direccions són el mateix defecte vist des de cada banda i totes dues
            # deixen un document que menteix, o sigui que totes dues aturen l'emissió.
            if bool(linia.encarrec_directe) == bool(fora):
                continue
            m = ronda.model
            fora_de_lloc.append({
                'linia': linia.id,
                'model_id': m.id if m else None,
                # La llei del nom: el nom mana i el codi va de secundari.
                'model': (m.nom_prenda or m.codi_intern) if m else None,
                'model_codi': m.codi_intern if m else None,
                'ronda_id': ronda.id,
                'ronda': ronda.seq,
                'numeral_vigent': numeral,
                'ara': 'fora' if fora else 'dins',
            })
    return fora_de_lloc


def issue_delivery_note(delivery_note, user=None):
    """Emet un albarà DRAFT→ISSUED (B4c). Guard: almenys 1 línia. Un cop ISSUED les línies queden
    congelades (guard DRAFT-only de DeliveryNoteLine, patró Quote). Llança ValidationError, i
    `ContradiccioDePacte` si el numeral ha canviat sota una línia ja composta."""
    from django.core.exceptions import ValidationError
    if delivery_note.status != 'DRAFT':
        raise ValidationError("Només es pot emetre un albarà en esborrany (DRAFT).")
    # v2 — el guard compta línies VISIBLES: un albarà només d'ítems amagats no té document a emetre.
    if not delivery_note.lines.filter(visible=True).exists():
        raise ValidationError("L'albarà no té cap línia visible; no es pot emetre.")
    # 🔒 ABANS DE CONGELAR, I FORA DE LA TRANSACCIÓ. Congelar és el que fa irreversible el
    # veredicte; si la comprovació anés a dins, el codi hauria de desfer el que acaba d'escriure
    # per poder-se negar. Aquí encara no s'ha tocat res.
    contradiccions = contradiccions_de_pacte(delivery_note)
    if contradiccions:
        raise ContradiccioDePacte(contradiccions)
    with transaction.atomic():
        # A4 · EMETRE ÉS CONGELAR. Fins aquí `fora_de_comanda` es tornava a pesar contra el
        # numeral viu a cada lectura de la safata; a partir d'aquí, el veredicte d'aquestes
        # voltes és el que el document diu i cap edició posterior del numeral el pot moure.
        # S'escriu ARA i no en obrir la volta perquè és ara quan deixa de ser una opinió: el
        # document ja ho ha dit al client.
        #
        # Es congela el valor EFECTIU (el que la safata acaba de calcular), no el que la fila
        # portava: si no, emetre no canviaria res i el congelat seria una foto d'un altre dia.
        from fhort.tasks.services_r import numeral_efectiu
        vistes = {}
        for linia in delivery_note.lines.prefetch_related('rondes__model'):
            for ronda in linia.rondes.all():
                if ronda.model_id not in vistes:
                    vistes[ronda.model_id] = numeral_efectiu(ronda.model)[1]
                numeral = vistes[ronda.model_id]
                fora = numeral is not None and ronda.seq > numeral
                if ronda.fora_de_comanda != fora:
                    ronda.fora_de_comanda = fora
                    ronda.save(update_fields=['fora_de_comanda'])
        delivery_note.status = 'ISSUED'
        delivery_note.issued_by = user
        if not delivery_note.issued_at:
            delivery_note.issued_at = timezone.now().date()
        delivery_note.save(update_fields=['status', 'issued_by', 'issued_at', 'updated_at'])
    return delivery_note


def mark_delivery_note_invoiced(delivery_note, user=None):
    """Marca un albarà ISSUED→INVOICED ("presentat al client, OK"; v2). NO és la factura (B5): és
    l'avançada d'estat. Guard: només des d'ISSUED (DRAFT no; un INVOICED ja marcat és idempotent).
    Llança ValidationError. Marcatge individual o massiu (el bucle massiu viu a la view)."""
    from django.core.exceptions import ValidationError
    if delivery_note.status == 'INVOICED':
        return delivery_note
    if delivery_note.status != 'ISSUED':
        raise ValidationError("Només es pot marcar com facturat un albarà emès (ISSUED).")
    delivery_note.status = 'INVOICED'
    delivery_note.invoiced_by = user
    if not delivery_note.invoiced_at:
        delivery_note.invoiced_at = timezone.now().date()
    delivery_note.save(update_fields=['status', 'invoiced_by', 'invoiced_at', 'updated_at'])
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


def _ronda_header(ronda):
    """M4 · FIT-12 — La VOLTA d'un ítem albaranable, tal com la safata l'ha de poder dir.

    Porta les DATES (`oberta_el`/`tancada_el`), que és el que FIT-12 demana explícitament: són
    la clau perquè el comercial informi QUAN es va fer cada volta. I porta el «perquè» en peces
    (`fora_de_comanda`, `numeral_vigent`, `comanda`) i no com a frase feta: la frase es compon a
    la cara, on hi ha l'idioma. Aquí no es tradueix res.

    `comanda` és el `document_number` de la comanda que fixava el numeral, resolt per la línia
    congelada a la volta (`Ronda.linia_comanda`) i no recalculat: si el model s'ha desassignat
    des de llavors, el «perquè» ha de seguir dient de quina venda parlava.
    """
    if ronda is None:
        return None
    linia = ronda.linia_comanda
    comanda = linia.order.document_number if linia is not None and linia.order_id else None
    return {
        'id': ronda.id, 'seq': ronda.seq, 'motiu': ronda.motiu,
        'fora_de_comanda': ronda.fora_de_comanda,
        'numeral_vigent': ronda.numeral_vigent,
        'comanda': comanda,
        'oberta_el': ronda.oberta_el.isoformat() if ronda.oberta_el else None,
        'tancada_el': ronda.tancada_el.isoformat() if ronda.tancada_el else None,
    }


def cost_hora_efectiu(model_task, rate_tenant):
    """A3 · QUINA TARIFA/HORA s'aplica a aquesta tasca. Punt únic.

    L'override de la tasca mana; sense override, la tarifa plana del tenant. `None` als dos vol
    dir que no se'n pot dir el cost, i llavors el cost és `None` —no zero: «no ho sabem» i «no
    costa res» són coses diferents i el zero les confondria a la cara.

    ⚠️ `0` a l'override SÍ que és una decisió («aquesta hora no la cobrem internament») i s'ha de
    respectar: per això la comprovació és `is not None` i no la veritat del valor.
    """
    if model_task is not None and getattr(model_task, 'hourly_rate_override', None) is not None:
        return model_task.hourly_rate_override
    return rate_tenant


def _ronda_albaranable(ronda, fora_efectiu):
    """La volta tal com la safata l'ha de dir. SENSE tasques (A1: la unitat és el MODEL).

    `entregada` i la data de lliurament surten de l'`Entrega`, que és el FET declarat; una volta
    en curs hi entra amb `entregada=False` i data `None` — la safata l'ha d'ENSENYAR (perquè el
    comercial vegi que existeix) i alhora no deixar-la marcar, i això només es pot fer si la
    porta la serveix i la diu.
    """
    e = getattr(ronda, 'entrega', None)
    return {
        'id': ronda.id, 'seq': ronda.seq,
        'entregada': e is not None,
        'data_lliurament': e.data.isoformat() if e is not None else None,
        'data_ok': e.data_ok.isoformat() if (e is not None and e.data_ok) else None,
        'fora_de_comanda': fora_efectiu,
        # El veredicte CONGELAT, al costat de l'efectiu. No serveix per decidir res: serveix
        # perquè es pugui veure que un albarà emès va congelar una altra cosa (A4).
        'fora_de_comanda_congelat': ronda.fora_de_comanda,
        'numeral_vigent': ronda.numeral_vigent,
    }


# Les tres menes d'albaranable que NO són una volta, i la seva forma de línia. El `line_kind`
# del document ja existia des de la v1: aquí només se'n diu quin correspon a cada origen.
_EXTRA_KINDS = {'EXTRA_BILL': 'EXTRA', 'DEDUCTION': 'DEDUCTION'}


def _extres_albaranables(customer):
    """ELS ALBARANABLES QUE NO SÓN UNA VOLTA: extres facturables, deduccions i despeses.

    🚨 **AIXÒ ÉS UNA REGRESSIÓ REPARADA.** La safata de tasques els servia (v2, `kind` EXTRA /
    DEDUCTION / EXPENSE) i la reescriptura del bloc A —que va canviar la unitat a MODEL+VOLTES—
    se'ls va endur sense substitut. Quedaven vius NOMÉS per `generate/` des de la fitxa
    d'encàrrec: un `EXTRA_BILL` ja revisat pel comercial no apareixia enlloc de
    `/comercial/albarans/<id>` i **es facturava de menys, en silenci**. Una volta no és l'única
    cosa que es cobra.

    Retorna `{model_id | None: [ítem, …]}`. La clau `None` NO és un descart: una deducció de
    concepte lliure sobre un col·lector no té model resoluble, i deixar-la fora seria repetir el
    defecte que aquesta funció ve a tancar.

    ── QUÈ ÉS CANDIDAT ────────────────────────────────────────────────────────────────────────
    El mateix criteri que les voltes: **cap línia d'albarà al darrere** (`delivery_note_lines`
    buit), DRAFT inclòs. Un ítem ja posat en un esborrany surt de la safata i hi torna sol si
    l'esborrany s'esborra (CASCADE de línies).

    `EXTRA_ABSORB` queda FORA i no és un oblit: absorbir és la decisió de no cobrar-ho, i
    ensenyar-lo a la safata seria oferir de facturar el que ja s'ha decidit que no es factura.

    🔑 **AQUÍ NO S'HI ESCRIU CAP FRASE.** La v1 congelava `'Extra'` / `'Deducció'` a la
    descripció de la línia quan l'origen no en tenia; una frase congelada en una columna no es
    tradueix mai més i el document surt en tres idiomes. La descripció viatja **buida** i qui
    renderitza la resol amb el `kind`, en l'idioma que toqui.
    """
    from .models import Expense, WorkOrderAdjustment

    fora = {}

    def _posa(model, item):
        fora.setdefault(model.id if model is not None else None, []).append(item)

    # EXTRA / DEDUCTION — el model surt de la tasca resolta i, si no n'hi ha, del WO.
    for adj in (WorkOrderAdjustment.objects
                .filter(work_order__customer=customer, kind__in=tuple(_EXTRA_KINDS),
                        delivery_note_lines__isnull=True)
                .select_related('work_order__model', 'work_order__order_line__product',
                                'model_task__model')
                .order_by('id')):
        model = (adj.model_task.model if adj.model_task_id else None) or adj.work_order.model
        preu = Decimal(adj.amount or 0).quantize(_CENT)
        # La deducció va en NEGATIU des de l'origen: `compute_document_totals` suma amb signe i
        # la resta surt sola, sense cap cas especial al motor de totals ni al document.
        if adj.kind == 'DEDUCTION':
            preu = -abs(preu)
        _posa(model, {
            'clau': f'ajust-{adj.id}',
            'kind': _EXTRA_KINDS[adj.kind],
            'descripcio': (adj.description or '').strip(),
            'preu_proposat': str(preu),
            # 🚨 EL PRODUCTE ÉS QUI PORTA EL TIPUS D'IVA, i per això viatja encara que la
            # targeta no en digui res. Un ajust no té article propi i hereta el de la venda del
            # seu encàrrec, que és el que la v1 ja feia: sense això, `compute_document_totals`
            # tracta la línia com a 0 % i l'extra es cobra sense IVA — un forat de diner que no
            # es veu enlloc de la pantalla, perquè el que falla és el que NO hi ha escrit.
            '_product_id': (adj.work_order.order_line.product_id
                            if adj.work_order.order_line_id else None),
            '_work_order_id': adj.work_order_id,
        })

    # EXPENSE — línia externa (servei extern o mercaderia). El preu és el de VENDA, mai el cost.
    for exp in (Expense.objects
                .filter(work_order__customer=customer, delivery_note_lines__isnull=True)
                .select_related('work_order__model', 'product')
                .order_by('id')):
        # A1 · LA LÍNIA NO TÉ COLUMNA DE QUANTITAT: l'import de la targeta és tot el que es
        # veu, a la pantalla i al document. Una despesa de 3×10 € entra com UN import de 30 €
        # —el diner és el mateix— i el desglossament segueix llegible per l'FK `expense`.
        # Servir `quantity=3` a una targeta que no la pinta faria que l'import de la cara i el
        # del total no quadressin.
        preu = (Decimal(exp.sale_price or 0) * Decimal(exp.quantity or 0)).quantize(
            _CENT, rounding=ROUND_HALF_UP)
        _posa(exp.work_order.model, {
            'clau': f'despesa-{exp.id}',
            'kind': 'EXPENSE',
            'descripcio': (exp.description or (exp.product.name if exp.product_id else '')).strip(),
            'preu_proposat': str(preu),
            # Una despesa SÍ que té article propi: el seu IVA és el d'aquell article.
            '_product_id': exp.product_id,
            '_work_order_id': exp.work_order_id,
        })

    return fora


def get_billable_items(customer):
    """SAFATA D'ALBARANABLES · BLOC A — la unitat és el MODEL i el que es cobra són RONDES.

    ⚠️ **AIXÒ SUBSTITUEIX LA SAFATA PER TASQUES.** Abans un ítem era una `ModelTask` Done (més
    extres, deduccions i despeses) i el bloc-model només agrupava. L'A1 diu que la unitat
    d'albarà és el MODEL —una targeta per model, import únic, sense quantitat— i l'A7 que el que
    el document ha de dir són les VOLTES. Una safata de tasques no ho pot compondre: el preu d'un
    model no és la suma dels preus de les seves tasques, és el que diu la línia de comanda.

    QUÈ SURT, per model del client amb voltes candidates:
      · la identitat (nom, ref nostra, ref del client, col·lecció, temporada) — llei del nom;
      · el PACTE viu, si n'hi ha: oferta, concepte, preu unitari, numeral i consum;
      · un BLOC per pacte amb les voltes que hi caben, i un bloc PROPI per cada volta que en
        surt (A7: targeta pròpia, preu lliure, «encàrrec directe»).

    Cada BLOC és el que es marca i el que després serà UNA línia d'albarà.

    ── QUÈ ÉS CANDIDAT ────────────────────────────────────────────────────────────────────────
    Voltes de models d'aquest client que **no estan cobertes per cap línia d'albarà**, ni DRAFT
    ni ISSUED.

    🚩 **DIVERGÈNCIA DECLARADA amb la lletra del brief**, que diu «no cobertes per cap línia
    d'albarà EMÈS». Si una volta ja posada en un esborrany seguís sortint a la safata, es podria
    afegir DOS COPS al mateix esborrany —i el guard d'`add_lines_to_draft` és per ORIGEN, no per
    volta. La llei anti-doble-comptatge que ja hi havia (`delivery_note_lines__isnull=True`) es
    manté, i esborrar l'esborrany les retorna soles (CASCADE de línies). L'«EMÈS» del brief
    governa una ALTRA pregunta —el congelat de l'A4— i allà sí que s'aplica al peu de la lletra.

    ── A4 · L'HÍBRID ──────────────────────────────────────────────────────────────────────────
    `fora_de_comanda` es RECALCULA amb el numeral VIGENT per a tota volta que no estigui coberta
    per una línia d'albarà EMÈS; les que sí que ho estan conserven el veredicte congelat. Això
    és el que fa que pujar el numeral d'una comanda torni a dins les voltes que encara no s'han
    facturat, i que no toqui ni una que ja ha sortit en un document. Els dos valors viatgen
    (`fora_de_comanda` efectiu · `fora_de_comanda_congelat`) perquè la diferència es pugui veure.

    Lectura pura: no persisteix res. En particular **NO reescriu `Ronda.fora_de_comanda`** —el
    camp segueix sent la foto de l'obertura, i qui la congela de debò és l'emissió (commit 5).
    """
    from fhort.models_app.models import Model
    from fhort.tasks.models import Ronda
    from fhort.tasks.services_r import numeral_efectiu

    # Voltes candidates: del client, sense cap línia d'albarà al darrere.
    voltes = (Ronda.objects
              .filter(model__customer=customer, delivery_note_lines__isnull=True)
              .select_related('model', 'entrega', 'linia_comanda__order', 'linia_comanda__product')
              .order_by('model__codi_intern', 'seq'))

    extres = _extres_albaranables(customer)

    grups = {}
    numerals = {}          # model_id -> (linia, numeral) — un sol pivot per model

    def _grup(m):
        """El grup d'un model, creant-lo si cal. `m` pot ser `None` (ítems sense model)."""
        clau = m.id if m is not None else None
        g = grups.get(clau)
        if g is None:
            if m is not None and clau not in numerals:
                numerals[clau] = numeral_efectiu(m)
            linia = numerals.get(clau, (None, None))[0]
            g = grups[clau] = {
                'model': _model_header(m),
                'pacte': _pacte_header(linia) if linia is not None else None,
                'blocs': [],
                # Els albaranables que no són voltes. Llista PRÒPIA i no un bloc més: un bloc de
                # voltes es marca sencer (una línia, un import) i un extra es marca sol. Barrejar
                # les dues formes en una sola llista obligaria cada lector a distingir-les pel
                # contingut, que és com es cola un ítem al calaix que no li toca.
                'extres': extres.get(clau, []),
                '_pacte_rondes': [],
            }
        return g

    for r in voltes:
        m = r.model
        if m.id not in numerals:
            numerals[m.id] = numeral_efectiu(m)
        linia, numeral = numerals[m.id]

        # A4 · HÍBRID. Tota volta que arriba aquí es torna a pesar contra el numeral d'ARA.
        # `numeral is None` = sense pacte o sense límit: mai desborda.
        #
        # 🚩 AQUÍ NO HI HA CAP BRANCA DE «CONSERVA EL CONGELAT», i tenir-n'hi una era codi mort:
        # `voltes` ja exclou tot el que té línia d'albarà, i «ja emesa» és un subconjunt d'això.
        # Els dos conjunts són DISJUNTS per construcció, o sigui que la comparació no s'avaluava
        # mai certa i la consulta que la sostenia es gastava per res. La meitat «congelada» de
        # l'híbrid la fa `issue_delivery_note`, i NOMÉS ell: aquesta funció només recalcula.
        fora = numeral is not None and r.seq > numeral

        g = _grup(m)
        if fora:
            # A7 — cada volta fora de pacte és un albaranable PROPI. Preu lliure: la comanda no
            # el fixa (per definició, aquesta volta no hi és) i qui el posa és el comercial.
            g['blocs'].append({
                'clau': f'directe-{r.id}',
                'encarrec_directe': True,
                'linia_comanda': None,
                'preu_proposat': '0.00',
                'rondes': [_ronda_albaranable(r, True)],
            })
        else:
            g['_pacte_rondes'].append(_ronda_albaranable(r, False))

    # Un extra pot ser l'ÚNIC que queda per cobrar d'un model —o pot no tenir model. Els seus
    # grups s'obren aquí, després de les voltes, perquè un model que ja hi és no se'n fabriqui
    # un segon. Una sola consulta per als models que encara no hi són.
    faltants = [k for k in extres if k is not None and k not in grups]
    if faltants:
        for m in Model.objects.filter(pk__in=faltants):
            _grup(m)
    if None in extres:
        _grup(None)

    # 🔑 UN MODEL ENTRA A LA SAFATA SI TÉ ALGUNA VOLTA ENTREGADA **O ALGUN EXTRA**. Un model amb
    # totes les voltes en curs i res més no té cap cosa per cobrar i seria soroll a la safata del
    # comercial; un model amb un extra pendent SÍ que en té, encara que cap volta seva hagi
    # arribat —i aquesta és exactament la porta per on el defecte anterior els feia desaparèixer.
    # Les voltes EN CURS del model que sí que hi entra s'hi queden i es diuen (`entregada: false`):
    # la safata ha d'ensenyar que existeixen —perquè es vegi que la feina no s'ha acabat— i alhora
    # la cara no les ha de deixar marcar. Amagar-les faria creure que el model ja està tancat.
    grups = {k: g for k, g in grups.items()
             if g['extres']
             or any(r['entregada'] for b in g['blocs'] for r in b['rondes'])
             or any(r['entregada'] for r in g['_pacte_rondes'])}

    # El bloc del PACTE va PRIMER (A7: la volta directa ve «immediatament després del mateix
    # model»), i només existeix si hi ha alguna volta que hi càpiga.
    for g in grups.values():
        rondes_pacte = g.pop('_pacte_rondes')
        if rondes_pacte:
            pacte = g['pacte'] or {}
            g['blocs'].insert(0, {
                'clau': 'pacte',
                'encarrec_directe': False,
                'linia_comanda': pacte.get('linia_id'),
                # El preu el proposa la línia de comanda; sense pacte, 0 i el posa el comercial.
                'preu_proposat': pacte.get('preu_unitari') or '0.00',
                'rondes': rondes_pacte,
            })

    return sorted(grups.values(), key=lambda g: g['model']['codi_intern'] or '')


def _pacte_header(linia):
    """EL PACTE que governa el model, tal com la safata i el document l'han de dir.

    `consumit` són les voltes DINS del pacte que ja han sortit en un albarà emès: el que queda
    per gastar del numeral. No compta les que hi ha a la safata sense marcar —encara no s'ha
    decidit res— ni les que van fora de pacte, que per definició no en gasten.
    """
    from fhort.tasks.models import Ronda
    consumit = (Ronda.objects
                .filter(linia_comanda=linia, fora_de_comanda=False,
                        delivery_note_lines__delivery_note__status__in=('ISSUED', 'INVOICED'))
                .distinct().count())
    return {
        'linia_id': linia.id,
        'oferta': linia.order.document_number if linia.order_id else None,
        'oferta_id': linia.order_id,
        'concepte': linia.description or (linia.product.name if linia.product_id else None),
        'preu_unitari': str(Decimal(linia.unit_price or 0).quantize(_CENT)),
        'rounds_included': linia.rounds_included,
        'consumit': consumit,
    }


def create_or_get_draft(customer, user=None):
    """Retorna el DRAFT obert del client o en crea un de nou. Un per client alhora: mentre n'hi ha
    un d'obert, tot 'afegir' hi apunta (add_lines_to_draft). NEIX BUIT: les línies s'hi afegeixen
    després, una a una, des de la safata. Retorna (draft, created)."""
    from .models import DeliveryNote
    existing = (DeliveryNote.objects.filter(customer=customer, status='DRAFT')
                .order_by('created_at').first())
    if existing is not None:
        return existing, False
    return DeliveryNote.objects.create(customer=customer, created_by=user), True


def add_lines_to_draft(draft, selected_items, user=None):
    """Crea UNA línia per BLOC seleccionat de la safata. A1: la unitat és el MODEL.

    `selected_items`: `[{'model_id': int|None, 'clau': …}]` — exactament les claus que
    `get_billable_items` emet, de qualsevol de les dues llistes del grup:

      · `'pacte'` / `'directe-<ronda_id>'`  → un BLOC de voltes (`blocs`) → línia `TASK`;
      · `'ajust-<id>'` / `'despesa-<id>'`   → un EXTRA (`extres`) → línia `EXTRA`/`DEDUCTION`/
        `EXPENSE`, sense cap volta lligada i mai `encarrec_directe` (un extra no és una volta
        fora de pacte: és una altra mena de cosa, i marcar-lo com a directa faria que el
        document li imprimís «encàrrec directe sense pressupost», que seria fals).

    No s'accepta cap altra forma: la safata és qui decideix què és un albaranable, i deixar que
    el client en compongui un altre seria tenir-ne dues.

    ⚠️ **AIXÒ JA NO CREA LÍNIES PER TASCA.** Abans hi havia una línia per `ModelTask`/ajust/despesa
    i el preu sortia del `price_snapshot` del WorkOrder. Ara la línia és el MODEL, el seu import és
    el PREU UNITARI DE LA LÍNIA DE COMANDA (editable després, en esborrany) i les voltes que cobreix
    hi queden lligades per la M2M — que és el que després deixa que el document digui «R1, R2» i
    baixi a les tasques de cadascuna.

    IDEMPOTENT PER VOLTA, no per origen: es recomprova contra la safata VIVA i, si una volta ja té
    línia, el bloc s'omet sencer. Aquest és el guard que evita el doble comptatge ara que l'origen
    ja no és una tasca —el guard vell (`delivery_note_lines__isnull=True` sobre la tasca) no diria
    res d'un bloc de tres voltes.

    Retorna les línies creades.
    """
    from django.core.exceptions import ValidationError
    from .models import DeliveryNoteLine, SalesOrderLine
    if draft.status != 'DRAFT':
        raise ValidationError("Només es poden afegir línies a un albarà en esborrany (DRAFT).")

    # La safata viva és l'ÚNICA autoritat sobre què es pot afegir i a quin preu.
    safata = {g['model']['id']: g for g in get_billable_items(draft.customer)}
    created = []
    # 🚨 LA FOTO DE LA SAFATA ES PREN UN COP, i per tant no veu el que aquesta mateixa crida
    # acaba d'afegir: `{"items":[{...,"clau":"pacte"},{...,"clau":"pacte"}]}` creava DUES línies
    # sobre les mateixes voltes, amb els dos imports als totals. El guard de la safata val entre
    # crides; dins d'una crida cal recordar què s'ha consumit. La cara no ho reprodueix (envia un
    # `Set`), però la porta HTTP sí.
    consumides = set()
    # El mateix guard per als extres: dos `ajust-7` al mateix cos creaven dues línies sobre el
    # mateix ajust, perquè la foto de la safata no veu el que aquesta crida acaba d'afegir.
    extres_consumits = set()
    with transaction.atomic():
        pos = draft.lines.count()
        for sel in (selected_items or []):
            grup = safata.get(sel.get('model_id'))
            if grup is None:
                continue
            clau = sel.get('clau')

            # ── EXTRA / DEDUCCIÓ / DESPESA — un ítem, una línia, sense voltes ──────────────
            extra = next((e for e in grup['extres'] if e['clau'] == clau), None)
            if extra is not None:
                if clau in extres_consumits:
                    continue
                extres_consumits.add(clau)
                origen, _, ident = clau.partition('-')
                line = DeliveryNoteLine(
                    delivery_note=draft, line_kind=extra['kind'],
                    model_id=grup['model']['id'],
                    # L'FK d'ORIGEN és el que treu l'ítem de la safata la propera vegada: sense
                    # ella, la línia no sabria de què ve i l'ítem seguiria sortint com a pendent.
                    adjustment_id=int(ident) if origen == 'ajust' else None,
                    expense_id=int(ident) if origen == 'despesa' else None,
                    # El producte porta el TIPUS D'IVA; el `work_order`, la traça de l'encàrrec
                    # —i amb ella el guard que impedeix desassignar un model ja albaranat
                    # (`unassign_model_from_order_line` mira les línies per `work_order`).
                    product_id=extra.get('_product_id'),
                    work_order_id=extra.get('_work_order_id'),
                    quantity=Decimal('1'),
                    unit_price=Decimal(extra['preu_proposat']).quantize(
                        _CENT, rounding=ROUND_HALF_UP),
                    description=extra['descripcio'][:300], position=pos + 1, visible=True)
                line.save()
                created.append(line)
                pos += 1
                continue

            bloc = next((b for b in grup['blocs'] if b['clau'] == clau), None)
            if bloc is None:
                continue
            # Una volta EN CURS no es factura: la safata la mostra, però marcar-la no val.
            rondes_ids = [r['id'] for r in bloc['rondes'] if r['entregada']]
            if not rondes_ids or consumides.intersection(rondes_ids):
                continue
            consumides.update(rondes_ids)

            linia_comanda = (SalesOrderLine.objects.filter(pk=bloc['linia_comanda']).first()
                             if bloc['linia_comanda'] else None)
            m = grup['model']
            # EL CONCEPTE de la línia. El del pacte NOMÉS quan la línia hi pertany: una volta
            # fora de pacte no té concepte pactat —per definició no és a cap pressupost— i
            # heretar-lo diria que sí. Allà el concepte és la identitat del model, i la frase
            # «encàrrec directe sense pressupost» la posa QUI RENDERITZA, en l'idioma que toqui,
            # a partir d'`encarrec_directe`. Aquí no s'hi escriu cap frase: una frase congelada
            # en una columna no es tradueix mai més.
            concepte = (None if bloc['encarrec_directe']
                        else (grup['pacte'] or {}).get('concepte'))
            concepte = concepte or m['nom_prenda'] or m['codi_intern']
            line = DeliveryNoteLine(
                delivery_note=draft, line_kind='TASK', model_id=m['id'],
                # El producte (i per tant l'IVA) surt de la línia de comanda quan n'hi ha.
                product=linia_comanda.product if linia_comanda else None,
                linia_comanda=linia_comanda,
                encarrec_directe=bloc['encarrec_directe'],
                # A1 · SENSE camp quantitat: sempre 1, i l'import és el de la targeta.
                quantity=Decimal('1'),
                unit_price=Decimal(bloc['preu_proposat']).quantize(_CENT, rounding=ROUND_HALF_UP),
                # `position` comença a `count()+1`, com fa la creació de línies MANUAL
                # (`views.py`): amb `count()` a seques, la primera línia afegida naixia amb la
                # posició de l'última existent i les dues empataven.
                description=str(concepte)[:300], position=pos + 1, visible=True)
            line.save()
            line.rondes.set(rondes_ids)
            created.append(line)
            pos += 1
        if created:
            draft.recalculate_totals()
    return created


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
