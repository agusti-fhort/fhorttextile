"""Serializers del mestre d'articles (B1). Read-only nested als satèl·lits a la fitxa;
escriptura dels satèl·lits via els seus ViewSets propis (filtrats per ?product=).
Els guards de domini de model.clean() es repliquen a validate() perquè apliquin via API.

PODA ECONÒMICA (2026-08-14): els camps de diner d'aquest mòdul viatgen NOMÉS a qui té la
capacitat COMERCIAL. Cada serializer declara els seus a `CAMPS_ECONOMICS`; la mecànica és
única i viu a `accounts/capabilities.py` (`PodaEconomicaMixin`), perquè la comparteixen
serializers de fora d'aquest fitxer (TenantConfig, Customer). El motiu de podar en comptes
de tallar amb 403: hi ha pantalles TÈCNIQUES que depenen d'aquests endpoints i no pinten
cap import — vegeu el docstring del mixin.
"""
from decimal import Decimal

from rest_framework import serializers

from fhort.accounts.capabilities import PodaEconomicaMixin
from fhort.i18n_content.serializers import TranslationsSerializerMixin

from .models import (
    Unit, Product, ProductRecipe, ProductSupplier, ProductComponent, ProductPriceGTI,
    Quote, QuoteLine, QuoteLineModelIntent, PaymentTerms, PaymentTermLine, SalesOrder,
    SalesOrderLine, DocumentDueDate, WorkOrder, WorkOrderAdjustment, Expense, DeliveryNote,
    DeliveryNoteLine,
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


class ProductSupplierSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    CAMPS_ECONOMICS = ('cost_price',)

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


class ProductPriceGTISerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    CAMPS_ECONOMICS = ('price',)

    gti_code = serializers.CharField(source='garment_type_item.code', read_only=True)
    gti_name = serializers.CharField(source='garment_type_item.name', read_only=True)

    class Meta:
        model = ProductPriceGTI
        fields = ['id', 'product', 'garment_type_item', 'gti_code', 'gti_name', 'price']


class ProductSerializer(PodaEconomicaMixin, TranslationsSerializerMixin, serializers.ModelSerializer):
    """Llista/creació/edició dels camps NUCLI de l'article. Els satèl·lits es llegeixen
    a la fitxa (camps *_detail) i s'editen pels seus endpoints propis. `name`/`description`
    guarden l'EN canònic; els idiomes addicionals viuen a `translations` (patró híbrid)."""
    CAMPS_ECONOMICS = ('base_price', 'sale_rate', 'markup_pct', 'tax_rate')
    unit_code = serializers.CharField(source='unit.code', read_only=True)
    recipe_lines = ProductRecipeSerializer(many=True, read_only=True)
    suppliers = ProductSupplierSerializer(many=True, read_only=True)
    components = ProductComponentSerializer(many=True, read_only=True)
    price_exceptions = ProductPriceGTISerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'code', 'name', 'description', 'translations', 'nature', 'price_mode',
                  'base_price', 'sale_rate', 'markup_pct', 'tax_rate', 'unit', 'unit_code',
                  'active', 'created_at', 'updated_at',
                  'recipe_lines', 'suppliers', 'components', 'price_exceptions']
        read_only_fields = ['created_at', 'updated_at']


# ── Condicions de pagament (B3a) ───────────────────────────────────────────────────────

class PaymentTermLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTermLine
        fields = ['id', 'percentage', 'days_offset', 'position']


class PaymentTermsSerializer(TranslationsSerializerMixin, serializers.ModelSerializer):
    """Condició de pagament amb fraccions nested WRITABLE (M4): les fraccions s'editen sempre
    com a conjunt i es desen amb la condició en una sola crida. Guard Σ%=100 aplicat aquí per a
    l'escriptura via API (mateix invariant que PaymentTermLine.clean); el frontend en mostra
    l'error de forma clara. `name` és traduïble (`translations`); l'EN viu a la columna."""
    lines = PaymentTermLineSerializer(many=True, required=False)

    class Meta:
        model = PaymentTerms
        fields = ['id', 'code', 'name', 'translations', 'active', 'lines']

    def validate(self, data):
        lines = data.get('lines')
        if lines:
            total = sum((ln['percentage'] for ln in lines), Decimal('0'))
            if total != Decimal('100.00'):
                raise serializers.ValidationError({'lines':
                    f"La suma de percentatges de les fraccions ha de ser 100.00 (actual: {total})."})
        return data

    def create(self, validated_data):
        # create/update propis (fraccions nested) → cal integrar-hi les traduccions a mà,
        # perquè no passen pel create/update del TranslationsSerializerMixin.
        translations = validated_data.pop('translations', None)
        lines = validated_data.pop('lines', [])
        terms = PaymentTerms.objects.create(**validated_data)
        self._sync_lines(terms, lines)
        if translations:
            self._write_translations(terms, translations)
        return terms

    def update(self, instance, validated_data):
        translations = validated_data.pop('translations', None)
        lines = validated_data.pop('lines', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if lines is not None:
            instance.lines.all().delete()
            self._sync_lines(instance, lines)
        if translations is not None:
            self._write_translations(instance, translations)
        return instance

    @staticmethod
    def _sync_lines(terms, lines):
        for ln in lines:
            PaymentTermLine.objects.create(terms=terms, **{k: v for k, v in ln.items() if k != 'id'})


# ── Data d'emissió: guard d'estat (2026-07-27) ─────────────────────────────────────────
# `issued_at` (models_base.py:45) ja existia i ja sortia al PDF; el que faltava era poder-la
# CORREGIR. És editable mentre el document encara es pot corregir i queda congelada quan el
# document ja està tancat — mateix principi de segellat que les línies i les intencions.
# El cens d'estats viu de cada tipus (STATUS_CHOICES) dona la frontera:
#   Quote        DRAFT·SENT    → mateixa frontera que les intencions de model ("mentre l'oferta
#                                negocia"); ACCEPTED està convertida i segellada, i REJECTED/
#                                EXPIRED són documents morts.
#   SalesOrder   OPEN          → COMPLETED i CANCELLED són terminals.
#   DeliveryNote DRAFT·ISSUED  → l'emissió és seva i encara s'ha de poder corregir; INVOICED ja
#                                s'ha presentat al client i acceptat.
def guard_issued_at_editable(serializer, value, live_statuses):
    """Bloqueja el canvi de data d'emissió si el document ja no és en un estat viu.
    En creació (instance=None) no aplica: encara no hi ha estat."""
    doc = serializer.instance
    if doc is not None and doc.status not in live_statuses:
        raise serializers.ValidationError(
            f"La data d'emissió no es pot canviar en un document en estat '{doc.status}' "
            f"(només {' o '.join(live_statuses)}).")
    return value


# ── Documents comercials — Quote (B2) ──────────────────────────────────────────────────

class QuoteLineSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    """Línia d'oferta. `line_total` és calculat (read-only); `unit_price` és editable mentre
    l'oferta és DRAFT (guard replicat del model, patró B1). Preu congelat: en crear la línia
    sense unit_price s'hi copia el base_price del Product."""
    CAMPS_ECONOMICS = ('unit_price', 'line_total')
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    # Vincle preparatori (E6): intencions de model d'aquesta línia, read-only nested (s'editen pel
    # QuoteLineModelIntentViewSet, ?quote_line=). Alimenta el picker de models de la fitxa d'oferta.
    model_intents = serializers.SerializerMethodField()

    class Meta:
        model = QuoteLine
        fields = ['id', 'quote', 'product', 'product_code', 'product_name', 'description',
                  'quantity', 'unit_price', 'line_total', 'position', 'model_intents']
        read_only_fields = ['line_total']

    def get_model_intents(self, obj):
        return [{'id': mi.id, 'model': mi.model_id, 'model_codi': mi.model.codi_intern,
                 'model_nom': mi.model.nom_prenda, 'qty': str(mi.qty), 'position': mi.position}
                for mi in obj.model_intents.all()]

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


class QuoteSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    """Capçalera d'oferta amb línies nested (read-only, s'editen pel QuoteLineViewSet, ?quote=).
    Numeració, totals i estat són calculats/gestionats pel backend (read-only)."""
    CAMPS_ECONOMICS = ('subtotal', 'tax_amount', 'total', 'tax_breakdown')
    customer_nom = serializers.CharField(source='customer.nom', read_only=True)
    # Default del selector d'idioma del PDF (Customer.language). '' = sense preselecció.
    customer_language = serializers.CharField(source='customer.language', read_only=True, default='')
    lines = QuoteLineSerializer(many=True, read_only=True)
    # Display (B3a): nom de la condició override + condició per defecte del client (per al selector).
    payment_terms_name = serializers.CharField(source='payment_terms.name', read_only=True)
    customer_payment_terms = serializers.IntegerField(source='customer.payment_terms_id', read_only=True)

    class Meta:
        model = Quote
        fields = ['id', 'document_number', 'doc_type', 'customer', 'customer_nom',
                  'customer_language', 'status',
                  'issued_at', 'valid_until', 'payment_terms', 'payment_terms_name',
                  'customer_payment_terms', 'subtotal', 'tax_amount', 'total',
                  'tax_breakdown', 'notes', 'created_at', 'updated_at', 'lines']
        # tax_amount deixa de ser editable manual (B2): ara sempre calculat (B3a). tax_breakdown
        # és el desglossament calculat, només lectura.
        read_only_fields = ['document_number', 'doc_type', 'status', 'subtotal', 'tax_amount',
                            'total', 'tax_breakdown', 'created_at', 'updated_at']

    def validate_issued_at(self, value):
        return guard_issued_at_editable(self, value, ('DRAFT', 'SENT'))


class QuoteLineModelIntentSerializer(serializers.ModelSerializer):
    """Vincle preparatori model↔línia d'oferta (E2). Intenció informativa: editable mentre
    l'oferta encara negocia models (DRAFT o SENT), bloquejada en ACCEPTED (ja convertida).
    Guard de coherència: el model ha de ser del mateix client que l'oferta (mirall de
    l'assignació real, assign_model_to_order_line)."""
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    model_nom = serializers.CharField(source='model.nom_prenda', read_only=True, default=None)

    class Meta:
        model = QuoteLineModelIntent
        fields = ['id', 'quote_line', 'model', 'model_codi', 'model_nom', 'qty', 'position',
                  'created_at']
        read_only_fields = ['created_at']

    def validate(self, data):
        line = data.get('quote_line') or getattr(self.instance, 'quote_line', None)
        model = data.get('model') or getattr(self.instance, 'model', None)
        if line is not None:
            # La intenció es negocia en DRAFT i SENT; un cop l'oferta és ACCEPTED (convertida i
            # segellada) ja no s'hi toca (mirall del guard DRAFT-only de les línies, però més laxe).
            if line.quote.status not in ('DRAFT', 'SENT'):
                raise serializers.ValidationError(
                    "Només es poden editar intencions de models mentre l'oferta negocia (DRAFT o SENT).")
            # Coherència de client (mirall d'assign_model_to_order_line).
            if model is not None and model.customer_id != line.quote.customer_id:
                raise serializers.ValidationError(
                    "El model i l'oferta han de ser del mateix client.")
        return data


# ── Documents comercials — SalesOrder (comanda, B3b) ───────────────────────────────────

class SalesOrderLineSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    """Línia de comanda. IRREVERSIBILITAT (B3b): preu/quantitat CONGELATS un cop creada (neixen
    de la conversió); l'ÚNIC camp mutable per API és `qty_allocated` (imputació de cartera).

    ⚠️ `quantity` i `qty_allocated` NO es poden podar: són la cartera, i el selector
    d'assignació de la fitxa del model els fa servir per saber quantes unitats queden lliures
    (`ActionsMenu.jsx:392-395`). No són diner."""
    CAMPS_ECONOMICS = ('unit_price', 'line_total')
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


class DocumentDueDateSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    """Venciment materialitzat (read-only) per a la fitxa de comanda/oferta."""
    CAMPS_ECONOMICS = ('amount',)

    class Meta:
        model = DocumentDueDate
        fields = ['id', 'due_date', 'amount', 'percentage', 'position']


class SalesOrderSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    """Capçalera de comanda amb línies i venciments nested (read-only). Tot calculat/congelat;
    els únics camps editables per API són `status` (OPEN/COMPLETED/CANCELLED) i la data
    d'emissió, corregible mentre la comanda és OPEN. La irreversibilitat de B3b es manté
    sencera: preus, quantitats i línies segueixen intocables."""
    CAMPS_ECONOMICS = ('subtotal', 'tax_amount', 'total', 'tax_breakdown')
    customer_nom = serializers.CharField(source='customer.nom', read_only=True)
    # Default del selector d'idioma del PDF (Customer.language). '' = sense preselecció.
    customer_language = serializers.CharField(source='customer.language', read_only=True, default='')
    lines = SalesOrderLineSerializer(many=True, read_only=True)
    due_dates = DocumentDueDateSerializer(many=True, read_only=True)
    payment_terms_name = serializers.CharField(source='payment_terms.name', read_only=True)
    source_quote_number = serializers.CharField(source='source_quote.document_number', read_only=True)

    class Meta:
        model = SalesOrder
        fields = ['id', 'document_number', 'doc_type', 'customer', 'customer_nom',
                  'customer_language', 'status',
                  'issued_at', 'valid_until', 'payment_terms', 'payment_terms_name',
                  'source_quote', 'source_quote_number', 'subtotal', 'tax_amount', 'total',
                  'tax_breakdown', 'notes', 'created_at', 'updated_at', 'lines', 'due_dates']
        read_only_fields = ['document_number', 'doc_type', 'customer', 'valid_until',
                            'payment_terms', 'source_quote', 'subtotal', 'tax_amount', 'total',
                            'tax_breakdown', 'notes', 'created_at', 'updated_at']

    def validate_issued_at(self, value):
        return guard_issued_at_editable(self, value, ('OPEN',))


class WorkOrderAdjustmentSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    """Ajust d'un encàrrec (B4a): extra facturat/absorbit o deducció. L'albarà (B4c) el llegirà."""
    CAMPS_ECONOMICS = ('amount',)

    class Meta:
        model = WorkOrderAdjustment
        fields = ['id', 'work_order', 'model_task', 'kind', 'description', 'amount',
                  'resolved_by', 'resolved_at']
        read_only_fields = ['resolved_at']


class WorkOrderSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    """Encàrrec / ordre de treball (B4a). Lectura amb detall de tasques (estat + minuts de timer
    agregats) i adjustments. El detall de tasques s'omet a la llista (evita N+1).

    ⚠️ Aquest serializer VIATJA A LA FITXA DEL MODEL: `ProductionTab.jsx:75` el demana per
    `?model=` per pintar la cadena comanda→encàrrec→albarà. `price_snapshot` és el preu de
    venda contractat congelat, i allà no hi pinta res: es poda. Els `adjustments` niats es
    poden sols pel seu propi serializer."""
    CAMPS_ECONOMICS = ('price_snapshot',)
    customer_nom = serializers.CharField(source='customer.nom', read_only=True)
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True, default=None)
    # v2 albarà — traçabilitat de la cadena comanda→WO→albarà (números de document, read-only).
    order_number = serializers.CharField(source='order_line.order.document_number', read_only=True, default=None)
    delivery_note_number = serializers.CharField(source='delivery_note.document_number', read_only=True, default=None)
    n_tasks = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()
    adjustments = WorkOrderAdjustmentSerializer(many=True, read_only=True)

    class Meta:
        model = WorkOrder
        fields = ['id', 'number', 'kind', 'origin', 'status', 'customer', 'customer_nom',
                  'model', 'model_codi', 'order_line', 'order_number', 'period', 'delivery_note',
                  'delivery_note_number', 'price_snapshot', 'recipe_snapshot',
                  'closed_at', 'closed_by', 'created_at', 'n_tasks', 'tasks', 'adjustments']

    def get_n_tasks(self, obj):
        return obj.tasks.count()

    def get_tasks(self, obj):
        # A la llista no carreguem el detall (només el comptador n_tasks).
        view = self.context.get('view')
        if view is not None and getattr(view, 'action', None) == 'list':
            return None
        from django.db.models import Sum
        from fhort.tasks.services_i import TRAMS_SANS
        rows = []
        for t in obj.tasks.select_related('task_type').all():
            minutes = t.timers.filter(TRAMS_SANS).aggregate(m=Sum('minuts'))['m'] or 0
            rows.append({
                'id': t.pk, 'task_type_code': t.task_type.code, 'task_type_name': t.task_type.name,
                'status': t.status, 'off_recipe': t.off_recipe, 'assignee': t.assignee_id,
                'minutes': minutes,
            })
        return rows


class ExpenseSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    """Despesa d'un encàrrec (B4b): línia externa amb cost real i preu de venda (marge propi)."""
    CAMPS_ECONOMICS = ('cost_price', 'sale_price')
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

class DeliveryNoteLineSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    """Línia d'albarà. En DRAFT el comercial edita NOMÉS `unit_price`/`description`/`notes`; els
    camps de traçabilitat (FK), `quantity`, `line_kind` i `line_total` són read-only. El guard
    DRAFT viu al model i es replica aquí per a un 400 net (patró QuoteLine).

    ⚠️ AQUEST ÉS EL CAS QUE VA OBRIR LA PEÇA. `ProductionTab.jsx:76` demana aquestes línies
    per `?model=` des de la fitxa del model i només en pinta `dn_number`/`dn_status`, però
    rebia `unit_price`, `line_total` i sobretot `internal_cost` — el COST INTERN, minuts ×
    tarifa/hora. Es podava sola quan `hourly_rate` era `null`; el dia que s'omplís a PROD,
    hauria començat a viatjar de debò (diagnosi 2026-08-14 §3.2). `internal_minutes` NO es
    poda: són minuts de feina, no diner, i són patrimoni del tècnic que els ha fet."""
    CAMPS_ECONOMICS = ('unit_price', 'line_total', 'internal_cost')
    product_code = serializers.CharField(source='product.code', read_only=True, default=None)
    product_name = serializers.CharField(source='product.name', read_only=True, default=None)
    # v2 — capçalera de bloc-model (agrupació al detall/PDF); read-only, per compondre els blocs.
    model_intern = serializers.CharField(source='model.codi_intern', read_only=True, default=None)
    model_codi_client = serializers.CharField(source='model.codi_client', read_only=True, default=None)
    model_nom = serializers.CharField(source='model.nom_prenda', read_only=True, default=None)
    model_collection = serializers.CharField(source='model.collection', read_only=True, default=None)
    model_temporada = serializers.CharField(source='model.temporada', read_only=True, default=None)
    model_any = serializers.IntegerField(source='model.any', read_only=True, default=None)
    # v2 — data de fi de la tasca inclosa (la data de lliurament del model = la darrera d'aquestes).
    task_finished_at = serializers.DateTimeField(source='model_task.finished_at', read_only=True, default=None)
    # v2 — número/estat de l'albarà (traçabilitat: albarans que inclouen un model, filtre ?model=).
    dn_number = serializers.CharField(source='delivery_note.document_number', read_only=True, default=None)
    dn_status = serializers.CharField(source='delivery_note.status', read_only=True, default=None)
    # Reskin (columna interna de cost, NOMÉS pantalla, mai al PDF): tècnic que va registrar el temps
    # de la tasca i cost = minuts interns × tarifa/hora (TenantConfig). Derivats; null sense minuts.
    internal_tecnic = serializers.SerializerMethodField()
    internal_cost = serializers.SerializerMethodField()

    def _hourly_rate(self):
        # Memoitzat al serializer fill (compartit per totes les línies del many=True): 1 sola lectura.
        if not hasattr(self, '_hr_cache'):
            from fhort.accounts.models import TenantConfig
            cfg = TenantConfig.objects.first()
            self._hr_cache = cfg.hourly_rate if (cfg and cfg.hourly_rate is not None) else None
        return self._hr_cache

    def get_internal_tecnic(self, obj):
        if not obj.model_task_id or not obj.internal_minutes:
            return None
        from django.db.models import Sum
        from fhort.tasks.services_i import TRAMS_SANS
        # Qui hi ha posat més hores. Amb els trams desbocats dins, un timer oblidat coronava
        # el tècnic que se l'havia deixat obert: la mateixa llei que la resta de lectures.
        row = (obj.model_task.timers.filter(TRAMS_SANS).values('tecnic__nom_complet')
               .annotate(m=Sum('minuts')).order_by('-m').first())
        return (row or {}).get('tecnic__nom_complet')

    def get_internal_cost(self, obj):
        rate = self._hourly_rate()
        if rate is None or obj.internal_minutes is None:
            return None
        from decimal import Decimal, ROUND_HALF_UP
        cost = (Decimal(obj.internal_minutes) / Decimal(60) * Decimal(rate)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        return str(cost)

    class Meta:
        model = DeliveryNoteLine
        fields = ['id', 'delivery_note', 'dn_number', 'dn_status', 'line_kind', 'product',
                  'product_code', 'product_name',
                  'description', 'quantity', 'unit_price', 'line_total', 'position', 'visible',
                  'model', 'model_intern', 'model_codi_client', 'model_nom', 'model_collection',
                  'model_temporada', 'model_any', 'internal_minutes', 'internal_tecnic',
                  'internal_cost', 'task_finished_at',
                  'work_order', 'model_task', 'expense', 'adjustment']
        # v2 — editables en DRAFT: description, quantity, unit_price, visible. La resta (traçabilitat,
        # model, internal_minutes, line_total) read-only: es fixen en compondre la línia.
        read_only_fields = ['delivery_note', 'line_kind', 'product', 'line_total', 'position',
                            'model', 'internal_minutes',
                            'work_order', 'model_task', 'expense', 'adjustment']

    def validate(self, data):
        dn = getattr(self.instance, 'delivery_note', None)
        if dn is not None and dn.status != 'DRAFT':
            raise serializers.ValidationError(
                "No es poden modificar línies d'un albarà que no està en esborrany (DRAFT).")
        return data


class DeliveryNoteSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    """Capçalera d'albarà amb línies nested (read-only, s'editen pel DeliveryNoteLineViewSet,
    ?delivery_note=). Numeració/totals/estat calculats o gestionats pel backend (read-only);
    `notes` editable en DRAFT. `work_orders_included` = els WO agregats (traçabilitat)."""
    CAMPS_ECONOMICS = ('subtotal', 'tax_amount', 'total', 'tax_breakdown')
    customer_nom = serializers.CharField(source='customer.nom', read_only=True)
    # Default del selector d'idioma del PDF (Customer.language). '' = sense preselecció.
    customer_language = serializers.CharField(source='customer.language', read_only=True, default='')
    lines = DeliveryNoteLineSerializer(many=True, read_only=True)
    issued_by_nom = serializers.CharField(source='issued_by.nom_complet', read_only=True, default=None)
    invoiced_by_nom = serializers.CharField(source='invoiced_by.nom_complet', read_only=True, default=None)
    work_orders_included = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryNote
        fields = ['id', 'document_number', 'doc_type', 'customer', 'customer_nom',
                  'customer_language', 'status',
                  'issued_at', 'issued_by', 'issued_by_nom', 'invoiced_at', 'invoiced_by',
                  'invoiced_by_nom', 'subtotal', 'tax_amount', 'total',
                  'tax_breakdown', 'notes', 'created_at', 'updated_at', 'lines',
                  'work_orders_included']
        read_only_fields = ['document_number', 'doc_type', 'customer', 'status',
                            'issued_by', 'invoiced_at', 'invoiced_by', 'subtotal', 'tax_amount',
                            'total', 'tax_breakdown', 'created_at', 'updated_at']

    def validate_issued_at(self, value):
        return guard_issued_at_editable(self, value, ('DRAFT', 'ISSUED'))

    def get_work_orders_included(self, obj):
        return [{'id': w.id, 'number': w.number, 'kind': w.kind}
                for w in obj.delivery_notes_included.all()]
