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

from fhort.accounts.capabilities import HasCapability, CONFIGURE, DEFINE_TASKS

from .models import (
    Unit, Product, ProductRecipe, ProductSupplier, ProductComponent, ProductPriceGTI,
    Quote, QuoteLine, PaymentTerms, SalesOrder, SalesOrderLine, WorkOrder, Expense,
    DeliveryNote, DeliveryNoteLine,
)
from .serializers import (
    UnitSerializer, ProductSerializer, ProductRecipeSerializer, ProductSupplierSerializer,
    ProductComponentSerializer, ProductPriceGTISerializer,
    QuoteSerializer, QuoteLineSerializer, PaymentTermsSerializer,
    SalesOrderSerializer, SalesOrderLineSerializer, WorkOrderSerializer, ExpenseSerializer,
    DeliveryNoteSerializer, DeliveryNoteLineSerializer,
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


class PaymentTermsViewSet(_ConfigureWriteMixin, viewsets.ModelViewSet):
    """Condicions de pagament (M4): CRUD amb fraccions nested writable. Lectura oberta (selector al
    Customer i als documents); escriptura gated CONFIGURE. El guard Σ%=100 viu al serializer."""
    queryset = PaymentTerms.objects.prefetch_related('lines').all()
    serializer_class = PaymentTermsSerializer
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

    @action(detail=True, methods=['post'], url_path='assign-model')
    def assign_model(self, request, pk=None):
        """POST commerce/order-lines/{id}/assign-model/ — assigna un model a la línia i crea el
        seu WorkOrder ORDER (snapshots congelats), imputa +1 a qty_allocated i migra les tasques
        del col·lector al nou encàrrec. Gate CONFIGURE. Body: {model_id}."""
        from fhort.models_app.models import Model
        line = self.get_object()
        model_id = request.data.get('model_id')
        model = Model.objects.filter(pk=model_id).first()
        if model is None:
            return Response({'detail': 'Model no trobat.'}, status=status.HTTP_404_NOT_FOUND)
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import assign_model_to_order_line
        try:
            wo, meta = assign_model_to_order_line(model, line, user=getattr(request.user, 'profile', None))
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'work_order': WorkOrderSerializer(wo).data, **meta},
                        status=status.HTTP_201_CREATED)


class WorkOrderViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Encàrrecs / ordres de treball (B4a). Lectura (autenticat) + acció `close` (gate
    DEFINE_TASKS). No es crea per POST: els ORDER neixen del wizard (B4b) i els COLLECTOR
    del hook lazy. Llista filtrable per kind/status/customer/period."""
    queryset = WorkOrder.objects.select_related('customer', 'model', 'closed_by', 'order_line') \
        .prefetch_related('adjustments', 'tasks__task_type').all()
    serializer_class = WorkOrderSerializer
    filterset_fields = ['kind', 'status', 'customer', 'period']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        # El tècnic tanca (DEFINE_TASKS); el comercial revisa el preu de venda (CONFIGURE).
        p = HasCapability()
        self.required_capability = CONFIGURE if self.action == 'review' else DEFINE_TASKS
        return [p]

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """POST work-orders/{id}/review/ — revisió COMERCIAL (preu de venda) d'un WO tancat.
        Gate CONFIGURE. Body: {items:[{model_task_id, kind, amount}]}. No toca cap cost."""
        wo = self.get_object()
        profile = getattr(request.user, 'profile', None)
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import apply_commercial_review
        try:
            apply_commercial_review(wo, request.data.get('items') or [], user=profile)
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(wo).data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """POST commerce/work-orders/{id}/close/ — el TÈCNIC tanca (feina feta). Bloqueja
        NOMÉS per tasques InProgress/Paused; els extres NO bloquegen (la revisió comercial
        en preu de venda és un acte posterior, /review/, B4b). Resposta estructurada
        { closed, blockers, pending_proposals }. 409 si no es pot tancar. Body opcional:
        {cancel_pending: bool}."""
        wo = self.get_object()
        profile = getattr(request.user, 'profile', None)
        from .services import close_work_order
        result = close_work_order(
            wo, user=profile,
            cancel_pending=bool(request.data.get('cancel_pending')))
        code = status.HTTP_200_OK if result['closed'] else status.HTTP_409_CONFLICT
        return Response(result, status=code)


class ExpenseViewSet(_ConfigureWriteMixin, viewsets.ModelViewSet):
    """Despeses d'un encàrrec (B4b): línies externes (servei extern / mercaderia) amb cost
    real i preu de venda. CRUD gated CONFIGURE; lectura oberta. Satèl·lit del WorkOrder,
    filtrat per ?work_order= (mateix patró que order-lines/quote-lines). NO és una tasca."""
    queryset = Expense.objects.select_related('product', 'supplier', 'created_by').all()
    serializer_class = ExpenseSerializer
    filterset_fields = ['work_order', 'product', 'supplier']

    def perform_create(self, serializer):
        serializer.save(created_by=getattr(self.request.user, 'profile', None))


# ── Documents comercials — DeliveryNote (albarà, B4c) ──────────────────────────────────

class DeliveryNoteViewSet(_ConfigureWriteMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                          mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    """Albarans (B4c). Lectura oberta; `generate`/`issue`/`destroy` gated CONFIGURE; `pdf`
    lectura. NO es crea per POST directe: neix de `generate/` (agrega 1..N WorkOrder CLOSED del
    mateix customer). `destroy` només en DRAFT (allibera els WO via SET_NULL). L'UPDATE del
    header serveix per editar `notes` en DRAFT (el status es mou només per `issue`)."""
    queryset = DeliveryNote.objects.select_related('customer', 'issued_by', 'created_by') \
        .prefetch_related('lines__product', 'delivery_notes_included').all()
    serializer_class = DeliveryNoteSerializer
    filterset_fields = ['status', 'customer']

    def get_permissions(self):
        if self.action == 'pdf':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """POST commerce/delivery-notes/generate/ — genera un albarà DRAFT amb línies proposades
        a partir de {work_order_ids}. Gate CONFIGURE. Retorna el DRAFT creat (201) o els errors
        del guard junts (400 amb `detail` i `errors`, p.ex. extres pendents de revisió)."""
        ids = request.data.get('work_order_ids') or []
        wos = list(WorkOrder.objects.select_related('order_line__product', 'customer')
                   .filter(pk__in=ids))
        missing = set(ids) - {w.pk for w in wos}
        if missing:
            return Response({'detail': f'Encàrrecs no trobats: {sorted(missing)}.'},
                            status=status.HTTP_404_NOT_FOUND)
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import generate_delivery_note
        try:
            dn = generate_delivery_note(wos, user=getattr(request.user, 'profile', None))
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages), 'errors': e.messages},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(dn).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        """POST commerce/delivery-notes/{id}/issue/ — emet el DRAFT (→ISSUED, congela línies).
        Gate CONFIGURE. Guard: almenys 1 línia."""
        dn = self.get_object()
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import issue_delivery_note
        try:
            issue_delivery_note(dn, user=getattr(request.user, 'profile', None))
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(dn).data)

    def destroy(self, request, *args, **kwargs):
        dn = self.get_object()
        if dn.status != 'DRAFT':
            return Response({'detail': "No es pot esborrar un albarà emès (ISSUED)."},
                            status=status.HTTP_409_CONFLICT)
        return super().destroy(request, *args, **kwargs)


class DeliveryNoteLineViewSet(_ConfigureWriteMixin, mixins.RetrieveModelMixin,
                              mixins.ListModelMixin, mixins.UpdateModelMixin,
                              viewsets.GenericViewSet):
    """Línies d'albarà (edició filtrada per ?delivery_note=). Només PATCH de preu/descripció en
    DRAFT (guard replicat al serializer per a un 400 net); FK de traçabilitat read-only. Sense
    create/destroy per API: les línies neixen de `generate/`."""
    queryset = DeliveryNoteLine.objects.select_related('delivery_note', 'product').all()
    serializer_class = DeliveryNoteLineSerializer
    filterset_fields = ['delivery_note', 'line_kind']
