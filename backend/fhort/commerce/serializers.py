"""Serializers del mestre d'articles (B1). Read-only nested als satèl·lits a la fitxa;
escriptura dels satèl·lits via els seus ViewSets propis (filtrats per ?product=).
Els guards de domini de model.clean() es repliquen a validate() perquè apliquin via API.
"""
from rest_framework import serializers

from .models import (
    Unit, Product, ProductRecipe, ProductSupplier, ProductComponent, ProductPriceGTI,
    Quote, QuoteLine,
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

    class Meta:
        model = Quote
        fields = ['id', 'document_number', 'doc_type', 'customer', 'customer_nom', 'status',
                  'issued_at', 'valid_until', 'payment_terms', 'subtotal', 'tax_amount', 'total',
                  'tax_breakdown', 'notes', 'created_at', 'updated_at', 'lines']
        # tax_amount deixa de ser editable manual (B2): ara sempre calculat (B3a). tax_breakdown
        # és el desglossament calculat, només lectura.
        read_only_fields = ['document_number', 'doc_type', 'status', 'subtotal', 'tax_amount',
                            'total', 'tax_breakdown', 'created_at', 'updated_at']
