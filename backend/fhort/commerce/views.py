"""ViewSets del mestre d'articles (B1).

Gating: lectura = qualsevol autenticat; escriptura = capability CONFIGURE (semàntica de
configuració de catàleg, com CustomerViewSet). La capability pròpia del mòdul i el gate de
tier (feature_flags) arriben a B5.
"""
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.accounts.capabilities import HasCapability, CONFIGURE

from .models import (
    Unit, Product, ProductRecipe, ProductSupplier, ProductComponent, ProductPriceGTI,
    Quote, QuoteLine, PaymentTerms, SalesOrder, SalesOrderLine,
)
from .serializers import (
    UnitSerializer, ProductSerializer, ProductRecipeSerializer, ProductSupplierSerializer,
    ProductComponentSerializer, ProductPriceGTISerializer,
    QuoteSerializer, QuoteLineSerializer, PaymentTermsSerializer,
    SalesOrderSerializer, SalesOrderLineSerializer,
)


class _ConfigureWriteMixin:
    """Lectura oberta a autenticats; escriptura gated CONFIGURE (patró CustomerViewSet)."""
    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        p = HasCapability(); self.required_capability = CONFIGURE
        return [p]


class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    """Catàleg d'unitats (sembrat; consulta per al selector d'unitat de l'article)."""
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['active']


class PaymentTermsViewSet(viewsets.ReadOnlyModelViewSet):
    """Catàleg de condicions de pagament (sembrat; selector al Customer i als documents)."""
    queryset = PaymentTerms.objects.prefetch_related('lines').all()
    serializer_class = PaymentTermsSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['active']


class ProductViewSet(_ConfigureWriteMixin, viewsets.ModelViewSet):
    queryset = Product.objects.select_related('unit').prefetch_related(
        'recipe_lines', 'suppliers__supplier', 'components__component', 'price_exceptions__garment_type_item'
    ).all()
    serializer_class = ProductSerializer
    filterset_fields = ['nature', 'price_mode', 'active']

    def destroy(self, request, *args, **kwargs):
        # PROTECT a components/futurs documents → 409 net (no 500).
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': "No es pot esborrar: l'article està referenciat. Desactiva'l."},
                status=status.HTTP_409_CONFLICT)


class ProductRecipeViewSet(_ConfigureWriteMixin, viewsets.ModelViewSet):
    queryset = ProductRecipe.objects.select_related('product').all()
    serializer_class = ProductRecipeSerializer
    filterset_fields = ['product', 'task_code']


class ProductSupplierViewSet(_ConfigureWriteMixin, viewsets.ModelViewSet):
    queryset = ProductSupplier.objects.select_related('product', 'supplier').all()
    serializer_class = ProductSupplierSerializer
    filterset_fields = ['product', 'supplier', 'is_default']


class ProductComponentViewSet(_ConfigureWriteMixin, viewsets.ModelViewSet):
    queryset = ProductComponent.objects.select_related('pack', 'component').all()
    serializer_class = ProductComponentSerializer
    filterset_fields = ['pack', 'component']


class ProductPriceGTIViewSet(_ConfigureWriteMixin, viewsets.ModelViewSet):
    queryset = ProductPriceGTI.objects.select_related('product', 'garment_type_item').all()
    serializer_class = ProductPriceGTISerializer
    filterset_fields = ['product', 'garment_type_item']


# ── Documents comercials — Quote (B2) ──────────────────────────────────────────────────

class QuoteViewSet(_ConfigureWriteMixin, viewsets.ModelViewSet):
    """CRUD d'ofertes + accions `send` (DRAFT→SENT) i `pdf` (descàrrega). Escriptura gated
    CONFIGURE (com el mestre B1); el `pdf` és lectura (autenticat). Rol comercial propi = B5."""
    queryset = Quote.objects.select_related('customer', 'created_by').prefetch_related(
        'lines__product').all()
    serializer_class = QuoteSerializer
    filterset_fields = ['status', 'customer']

    def get_permissions(self):
        # El PDF és una lectura: obert a autenticats (no gated CONFIGURE).
        if self.action == 'pdf':
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(created_by=getattr(self.request.user, 'profile', None))

    def perform_update(self, serializer):
        # Un canvi de payment_terms/issued_at (o notes) ha de regenerar els venciments.
        quote = serializer.save()
        from .services import generate_due_dates
        generate_due_dates(quote)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Transiciona DRAFT→SENT. Guard: l'oferta ha de tenir almenys una línia."""
        quote = self.get_object()
        if quote.status != 'DRAFT':
            return Response({'detail': "Només es pot enviar una oferta en esborrany (DRAFT)."},
                            status=status.HTTP_409_CONFLICT)
        if not quote.lines.exists():
            return Response({'detail': "L'oferta no té cap línia; afegeix-ne almenys una."},
                            status=status.HTTP_400_BAD_REQUEST)
        quote.status = 'SENT'
        if not quote.issued_at:
            quote.issued_at = timezone.now().date()
        quote.save(update_fields=['status', 'issued_at', 'updated_at'])
        from .services import generate_due_dates
        generate_due_dates(quote)   # materialitza els venciments amb la data d'emissió
        return Response(self.get_serializer(quote).data)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Genera i retorna el PDF de l'oferta (reportlab, P5). Import mandrós per no acoblar."""
        quote = self.get_object()
        from .pdf_service import generate_quote_pdf
        pdf_bytes = generate_quote_pdf(quote)
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{quote.document_number or "quote"}.pdf"'
        return resp

    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        """Converteix l'oferta en comanda (IRREVERSIBLE, B3b). Retorna la SalesOrder creada (201)
        o l'error del guard (400 amb missatge clar). Escriptura gated CONFIGURE."""
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import convert_quote_to_order
        quote = self.get_object()
        try:
            order = convert_quote_to_order(quote, user=request.user)
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SalesOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class QuoteLineViewSet(_ConfigureWriteMixin, viewsets.ModelViewSet):
    """Línies d'oferta (edició filtrada per ?quote=, patró satèl·lit B1). El guard DRAFT viu al
    model i es replica al serializer per a un 400 net."""
    queryset = QuoteLine.objects.select_related('quote', 'product').all()
    serializer_class = QuoteLineSerializer
    filterset_fields = ['quote', 'product']


# ── Documents comercials — SalesOrder (comanda, B3b) ───────────────────────────────────

class SalesOrderViewSet(_ConfigureWriteMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                        mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Comandes de venda (B3b). NOMÉS lectura + update restringit a `status` (les comandes neixen
    de la conversió d'una oferta, mai per POST; irreversibilitat de línies via serializer). El
    `pdf` és lectura (autenticat)."""
    queryset = SalesOrder.objects.select_related('customer', 'source_quote', 'created_by').prefetch_related(
        'lines__product', 'due_dates').all()
    serializer_class = SalesOrderSerializer
    filterset_fields = ['status', 'customer']

    def get_permissions(self):
        if self.action == 'pdf':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """PDF de la comanda: reutilitza el generador de l'oferta amb títol 'Comanda'."""
        order = self.get_object()
        from .pdf_service import generate_document_pdf
        pdf_bytes = generate_document_pdf(order, doc_title='Comanda')
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{order.document_number or "order"}.pdf"'
        return resp


class SalesOrderLineViewSet(_ConfigureWriteMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                            mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Línies de comanda (lectura + PATCH restringit a `qty_allocated`, filtrat per ?order=). Sense
    create/destroy: les línies neixen de la conversió (irreversibilitat, B3b)."""
    queryset = SalesOrderLine.objects.select_related('order', 'product').all()
    serializer_class = SalesOrderLineSerializer
    filterset_fields = ['order', 'product']
