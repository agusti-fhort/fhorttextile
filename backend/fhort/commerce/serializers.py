"""Serializers del mestre d'articles (B1). Read-only nested als satèl·lits a la fitxa;
escriptura dels satèl·lits via els seus ViewSets propis (filtrats per ?product=).
Els guards de domini de model.clean() es repliquen a validate() perquè apliquin via API.
"""
from decimal import Decimal

from rest_framework import serializers

from .models import (
    Unit, Product, ProductRecipe, ProductSupplier, ProductComponent, ProductPriceGTI,
    Quote, QuoteLine, PaymentTerms, PaymentTermLine, SalesOrder, SalesOrderLine,
    DocumentDueDate, WorkOrder, WorkOrderAdjustment, Expense, DeliveryNote, DeliveryNoteLine,
)


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'code', 'name', 'active']


class ProductRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRecipe
        fields = ['id', 'product', 'task_code', 'qty']

    def validate(self, data):
        product = data.get('product') or getattr(self.instance, 'product', None)
        if product and product.nature != 'INTERNAL_SERVICE':
            raise serializers.ValidationError(
                "La recepta només s'aplica a serveis interns (INTERNAL_SERVICE).")
        return data


class ProductSupplierSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = ProductSupplier
        fields = ['id', 'product', 'supplier', 'supplier_name', 'cost_price', 'is_default']


class ProductComponentSerializer(serializers.ModelSerializer):
    component_code = serializers.CharField(source='component.code', read_only=True)
    component_name = serializers.CharField(source='component.name', read_only=True)

    class Meta:
        model = ProductComponent
        fields = ['id', 'pack', 'component', 'component_code', 'component_name', 'qty']

    def validate(self, data):
        pack = data.get('pack') or getattr(self.instance, 'pack', None)
        component = data.get('component') or getattr(self.instance, 'component', None)
        if pack and pack.nature != 'PACK':
            raise serializers.ValidationError("El contenidor d'un component ha de ser un PACK.")
        if component and component.nature == 'PACK':
            raise serializers.ValidationError("Un PACK no pot contenir un altre PACK (un sol nivell).")
        if pack and component and pack.pk == component.pk:
            raise serializers.ValidationError("Un pack no pot contenir-se a si mateix.")
        return data


class ProductPriceGTISerializer(serializers.ModelSerializer):
    gti_code = serializers.CharField(source='garment_type_item.code', read_only=True)
    gti_name = serializers.CharField(source='garment_type_item.name', read_only=True)

    class Meta:
        model = ProductPriceGTI
        fields = ['id', 'product', 'garment_type_item', 'gti_code', 'gti_name', 'price']


class ProductSerializer(serializers.ModelSerializer):
    """Llista/creació/edició dels camps NUCLI de l'article. Els satèl·lits es llegeixen
    a la fitxa (camps *_detail) i s'editen pels seus endpoints propis."""
    unit_code = serializers.CharField(source='unit.code', read_only=True)
    recipe_lines = ProductRecipeSerializer(many=True, read_only=True)
    suppliers = ProductSupplierSerializer(many=True, read_only=True)
    components = ProductComponentSerializer(many=True, read_only=True)
    price_exceptions = ProductPriceGTISerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'code', 'name', 'nature', 'price_mode', 'base_price', 'sale_rate',
                  'markup_pct', 'tax_rate', 'unit', 'unit_code', 'active', 'created_at', 'updated_at',
                  'recipe_lines', 'suppliers', 'components', 'price_exceptions']
        read_only_fields = ['created_at', 'updated_at']


# ── Condicions de pagament (B3a) ───────────────────────────────────────────────────────

class PaymentTermLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTermLine
        fields = ['id', 'percentage', 'days_offset', 'position']


class PaymentTermsSerializer(serializers.ModelSerializer):
    """Condició de pagament amb fraccions nested WRITABLE (M4): les fraccions s'editen sempre
    com a conjunt i es desen amb la condició en una sola crida. Guard Σ%=100 aplicat aquí per a
    l'escriptura via API (mateix invariant que PaymentTermLine.clean); el frontend en mostra
    l'error de forma clara."""
    lines = PaymentTermLineSerializer(many=True, required=False)

    class Meta:
        model = PaymentTerms
        fields = ['id', 'code', 'name', 'active', 'lines']

    def validate(self, data):
        lines = data.get('lines')
        if lines:
            total = sum((ln['percentage'] for ln in lines), Decimal('0'))
            if total != Decimal('100.00'):
                raise serializers.ValidationError({'lines':
                    f"La suma de percentatges de les fraccions ha de ser 100.00 (actual: {total})."})
        return data

    def create(self, validated_data):
        lines = validated_data.pop('lines', [])
        terms = PaymentTerms.objects.create(**validated_data)
        self._sync_lines(terms, lines)
        return terms

    def update(self, instance, validated_data):
        lines = validated_data.pop('lines', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if lines is not None:
            instance.lines.all().delete()
            self._sync_lines(instance, lines)
        return instance

    @staticmethod
    def _sync_lines(terms, lines):
        for ln in lines:
            PaymentTermLine.objects.create(terms=terms, **{k: v for k, v in ln.items() if k != 'id'})


# ── Documents comercials — Quote (B2) ──────────────────────────────────────────────────

class QuoteLineSerializer(serializers.ModelSerializer):
    """Línia d'oferta. `line_total` és calculat (read-only); `unit_price` és editable mentre
    l'oferta és DRAFT (guard replicat del model, patró B1). Preu congelat: en crear la línia
    sense unit_price s'hi copia el base_price del Product."""
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = QuoteLine
        fields = ['id', 'quote', 'product', 'product_code', 'product_name', 'description',
                  'quantity', 'unit_price', 'line_total', 'position']
        read_only_fields = ['line_total']

    def validate(self, data):
        quote = data.get('quote') or getattr(self.instance, 'quote', None)
        if quote and quote.status != 'DRAFT':
            raise serializers.ValidationError(
                "No es poden modificar línies d'una oferta que no està en esborrany (DRAFT).")
        # Congelació del preu: si es crea sense unit_price, copia el base_price del Product.
        if self.instance is None and data.get('unit_price') is None:
            product = data.get('product')
            if product is not None and product.base_price is not None:
                data['unit_price'] = product.base_price
        return data


class QuoteSerializer(serializers.ModelSerializer):
    """Capçalera d'oferta amb línies nested (read-only, s'editen pel QuoteLineViewSet, ?quote=).
    Numeració, totals i estat són calculats/gestionats pel backend (read-only)."""
    customer_nom = serializers.CharField(source='customer.nom', read_only=True)
    lines = QuoteLineSerializer(many=True, read_only=True)
    # Display (B3a): nom de la condició override + condició per defecte del client (per al selector).
    payment_terms_name = serializers.CharField(source='payment_terms.name', read_only=True)
    customer_payment_terms = serializers.IntegerField(source='customer.payment_terms_id', read_only=True)

    class Meta:
        model = Quote
        fields = ['id', 'document_number', 'doc_type', 'customer', 'customer_nom', 'status',
                  'issued_at', 'valid_until', 'payment_terms', 'payment_terms_name',
                  'customer_payment_terms', 'subtotal', 'tax_amount', 'total',
                  'tax_breakdown', 'notes', 'created_at', 'updated_at', 'lines']
        # tax_amount deixa de ser editable manual (B2): ara sempre calculat (B3a). tax_breakdown
        # és el desglossament calculat, només lectura.
        read_only_fields = ['document_number', 'doc_type', 'status', 'subtotal', 'tax_amount',
                            'total', 'tax_breakdown', 'created_at', 'updated_at']


# ── Documents comercials — SalesOrder (comanda, B3b) ───────────────────────────────────

class SalesOrderLineSerializer(serializers.ModelSerializer):
    """Línia de comanda. IRREVERSIBILITAT (B3b): preu/quantitat CONGELATS un cop creada (neixen
    de la conversió); l'ÚNIC camp mutable per API és `qty_allocated` (imputació de cartera)."""
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SalesOrderLine
        fields = ['id', 'order', 'product', 'product_code', 'product_name', 'description',
                  'quantity', 'unit_price', 'line_total', 'position', 'qty_allocated']
        read_only_fields = ['order', 'product', 'description', 'quantity', 'unit_price',
                            'line_total', 'position']

    def validate_qty_allocated(self, value):
        if value is None:
            return value
        if value < 0:
            raise serializers.ValidationError("La quantitat imputada no pot ser negativa.")
        line = self.instance
        if line is not None and value > line.quantity:
            raise serializers.ValidationError(
                "La quantitat imputada no pot superar la quantitat comandada.")
        return value


class DocumentDueDateSerializer(serializers.ModelSerializer):
    """Venciment materialitzat (read-only) per a la fitxa de comanda/oferta."""
    class Meta:
        model = DocumentDueDate
        fields = ['id', 'due_date', 'amount', 'percentage', 'position']


class SalesOrderSerializer(serializers.ModelSerializer):
    """Capçalera de comanda amb línies i venciments nested (read-only). Tot calculat/congelat;
    l'ÚNIC camp editable per API és `status` (OPEN/COMPLETED/CANCELLED). Traçabilitat a l'oferta."""
    customer_nom = serializers.CharField(source='customer.nom', read_only=True)
    lines = SalesOrderLineSerializer(many=True, read_only=True)
    due_dates = DocumentDueDateSerializer(many=True, read_only=True)
    payment_terms_name = serializers.CharField(source='payment_terms.name', read_only=True)
    source_quote_number = serializers.CharField(source='source_quote.document_number', read_only=True)

    class Meta:
        model = SalesOrder
        fields = ['id', 'document_number', 'doc_type', 'customer', 'customer_nom', 'status',
                  'issued_at', 'valid_until', 'payment_terms', 'payment_terms_name',
                  'source_quote', 'source_quote_number', 'subtotal', 'tax_amount', 'total',
                  'tax_breakdown', 'notes', 'created_at', 'updated_at', 'lines', 'due_dates']
        read_only_fields = ['document_number', 'doc_type', 'customer', 'issued_at', 'valid_until',
                            'payment_terms', 'source_quote', 'subtotal', 'tax_amount', 'total',
                            'tax_breakdown', 'notes', 'created_at', 'updated_at']


class WorkOrderAdjustmentSerializer(serializers.ModelSerializer):
    """Ajust d'un encàrrec (B4a): extra facturat/absorbit o deducció. L'albarà (B4c) el llegirà."""
    class Meta:
        model = WorkOrderAdjustment
        fields = ['id', 'work_order', 'model_task', 'kind', 'description', 'amount',
                  'resolved_by', 'resolved_at']
        read_only_fields = ['resolved_at']


class WorkOrderSerializer(serializers.ModelSerializer):
    """Encàrrec / ordre de treball (B4a). Lectura amb detall de tasques (estat + minuts de timer
    agregats) i adjustments. El detall de tasques s'omet a la llista (evita N+1)."""
    customer_nom = serializers.CharField(source='customer.nom', read_only=True)
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True, default=None)
    n_tasks = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()
    adjustments = WorkOrderAdjustmentSerializer(many=True, read_only=True)

    class Meta:
        model = WorkOrder
        fields = ['id', 'number', 'kind', 'origin', 'status', 'customer', 'customer_nom',
                  'model', 'model_codi', 'order_line', 'period', 'delivery_note',
                  'price_snapshot', 'recipe_snapshot',
                  'closed_at', 'closed_by', 'created_at', 'n_tasks', 'tasks', 'adjustments']

    def get_n_tasks(self, obj):
        return obj.tasks.count()

    def get_tasks(self, obj):
        # A la llista no carreguem el detall (només el comptador n_tasks).
        view = self.context.get('view')
        if view is not None and getattr(view, 'action', None) == 'list':
            return None
        from django.db.models import Sum
        rows = []
        for t in obj.tasks.select_related('task_type').all():
            minutes = t.timers.aggregate(m=Sum('minuts'))['m'] or 0
            rows.append({
                'id': t.pk, 'task_type_code': t.task_type.code, 'task_type_name': t.task_type.name,
                'status': t.status, 'off_recipe': t.off_recipe, 'assignee': t.assignee_id,
                'minutes': minutes,
            })
        return rows


class ExpenseSerializer(serializers.ModelSerializer):
    """Despesa d'un encàrrec (B4b): línia externa amb cost real i preu de venda (marge propi)."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_nature = serializers.CharField(source='product.nature', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = Expense
        fields = ['id', 'work_order', 'product', 'product_name', 'product_nature',
                  'supplier', 'supplier_name', 'cost_price', 'sale_price', 'quantity',
                  'description', 'incurred_at', 'created_by', 'created_at']
        read_only_fields = ['created_by', 'created_at']

    def validate(self, attrs):
        # DRF no crida Model.clean(); l'invoquem perquè el guard de nature (EXTERNAL_SERVICE/
        # GOODS) apliqui via API. Fusiona attrs entrants amb la instància (PATCH parcial).
        from django.core.exceptions import ValidationError as DjangoValidationError
        product = attrs.get('product', getattr(self.instance, 'product', None))
        probe = Expense(product=product)
        try:
            probe.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError({'product': e.messages})
        return attrs


# ── Documents comercials — DeliveryNote (albarà, B4c) ──────────────────────────────────

class DeliveryNoteLineSerializer(serializers.ModelSerializer):
    """Línia d'albarà. En DRAFT el comercial edita NOMÉS `unit_price`/`description`/`notes`; els
    camps de traçabilitat (FK), `quantity`, `line_kind` i `line_total` són read-only. El guard
    DRAFT viu al model i es replica aquí per a un 400 net (patró QuoteLine)."""
    product_code = serializers.CharField(source='product.code', read_only=True, default=None)
    product_name = serializers.CharField(source='product.name', read_only=True, default=None)
    model_intern = serializers.CharField(source='model.codi_intern', read_only=True, default=None)

    class Meta:
        model = DeliveryNoteLine
        fields = ['id', 'delivery_note', 'line_kind', 'product', 'product_code', 'product_name',
                  'description', 'quantity', 'unit_price', 'line_total', 'position', 'visible',
                  'model', 'model_intern', 'internal_minutes',
                  'work_order', 'model_task', 'expense', 'adjustment']
        # v2 — editables en DRAFT: description, quantity, unit_price, visible. La resta (traçabilitat,
        # model, internal_minutes, line_total) read-only: es fixen en compondre la línia.
        read_only_fields = ['delivery_note', 'line_kind', 'product', 'line_total', 'position',
                            'model', 'model_intern', 'internal_minutes',
                            'work_order', 'model_task', 'expense', 'adjustment']

    def validate(self, data):
        dn = getattr(self.instance, 'delivery_note', None)
        if dn is not None and dn.status != 'DRAFT':
            raise serializers.ValidationError(
                "No es poden modificar línies d'un albarà que no està en esborrany (DRAFT).")
        return data


class DeliveryNoteSerializer(serializers.ModelSerializer):
    """Capçalera d'albarà amb línies nested (read-only, s'editen pel DeliveryNoteLineViewSet,
    ?delivery_note=). Numeració/totals/estat calculats o gestionats pel backend (read-only);
    `notes` editable en DRAFT. `work_orders_included` = els WO agregats (traçabilitat)."""
    customer_nom = serializers.CharField(source='customer.nom', read_only=True)
    lines = DeliveryNoteLineSerializer(many=True, read_only=True)
    issued_by_nom = serializers.CharField(source='issued_by.nom_complet', read_only=True, default=None)
    work_orders_included = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryNote
        fields = ['id', 'document_number', 'doc_type', 'customer', 'customer_nom', 'status',
                  'issued_at', 'issued_by', 'issued_by_nom', 'subtotal', 'tax_amount', 'total',
                  'tax_breakdown', 'notes', 'created_at', 'updated_at', 'lines',
                  'work_orders_included']
        read_only_fields = ['document_number', 'doc_type', 'customer', 'status', 'issued_at',
                            'issued_by', 'subtotal', 'tax_amount', 'total', 'tax_breakdown',
                            'created_at', 'updated_at']

    def get_work_orders_included(self, obj):
        return [{'id': w.id, 'number': w.number, 'kind': w.kind}
                for w in obj.delivery_notes_included.all()]
