"""ViewSets del mestre d'articles (B1).

Gating (2026-08-14): lectura I escriptura exigeixen COMERCIAL — la capability de VEURE EL
DINER; l'escriptura, a més, CONFIGURE. Fins aquí la lectura era oberta a qualsevol autenticat
i era la porta per on un tècnic es baixava preus, marges i el PDF sencer d'una oferta.

Quatre vistes en queden FORA a posta —SalesOrder, SalesOrderLine, WorkOrder i
DeliveryNoteLine— perquè sostenen dues superfícies TÈCNIQUES que no pinten cap import: el
selector d'assignació model↔comanda i la cadena de traçabilitat de la fitxa del model. Allà
la lectura segueix oberta i el que hi viatja es PODA (`PodaEconomicaMixin`). Cadascuna ho
raona al seu docstring. El gate de tier del mòdul (feature_flags) segueix pendent per a B5.
"""
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.accounts.capabilities import HasCapability, COMERCIAL, CONFIGURE, DEFINE_TASKS

from .models import (
    Unit, Product, ProductRecipe, ProductSupplier, ProductComponent, ProductPriceGTI,
    Quote, QuoteLine, QuoteLineModelIntent, PaymentTerms, SalesOrder, SalesOrderLine,
    WorkOrder, Expense, DeliveryNote, DeliveryNoteLine,
)
from .serializers import (
    UnitSerializer, ProductSerializer, ProductRecipeSerializer, ProductSupplierSerializer,
    ProductComponentSerializer, ProductPriceGTISerializer,
    QuoteSerializer, QuoteLineSerializer, QuoteLineModelIntentSerializer, PaymentTermsSerializer,
    SalesOrderSerializer, SalesOrderLineSerializer, WorkOrderSerializer, ExpenseSerializer,
    DeliveryNoteSerializer, DeliveryNoteLineSerializer,
)


class _Comercial(HasCapability):
    """Veure el DINER. Subclasse amb l'atribut de classe (patró `_DefineTasks`,
    `tasks/views_b.py:319`) i NO `self.required_capability = …` sobre la view: `HasCapability`
    mira primer la view i després la pròpia classe, o sigui que amb l'idioma vell dos permisos
    a la mateixa view acabarien exigint tots dos la MATEIXA capacitat."""
    required_capability = COMERCIAL


class _Configure(HasCapability):
    required_capability = CONFIGURE


class _DefineTasks(HasCapability):
    required_capability = DEFINE_TASKS


class _ComercialMixin:
    """Lectura I escriptura exigeixen COMERCIAL; l'escriptura, A MÉS, CONFIGURE.

    Abans (fins 2026-08-14) això era `_ConfigureWriteMixin`: lectura oberta a qualsevol
    autenticat i escriptura gated CONFIGURE. La lectura oberta era la porta per on un tècnic
    es baixava preus, marges i el PDF sencer d'una oferta (diagnosi §2.3). Ara qui escriu
    comerç necessita LES DUES: veure el diner i poder configurar.

    ⚠️ Aquest mixin NO el porten les vistes que sostenen l'assignació model↔comanda
    (SalesOrder, SalesOrderLine, WorkOrder, DeliveryNoteLine): allà la lectura queda oberta i
    el que hi viatja es poda. Cadascuna diu per què al seu docstring.
    """
    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [_Comercial()]
        return [_Comercial(), _Configure()]


class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    """Catàleg d'unitats (sembrat; consulta per al selector d'unitat de l'article).

    Sense cap import a dins, però els seus dos únics cridadors són la fitxa i la llista
    d'articles (`pages/Products.jsx:115`, `pages/ProductDetail.jsx:62`), que ara demanen
    COMERCIAL: deixar-lo obert seria l'únic forat d'un menú tancat."""
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [_Comercial]
    filterset_fields = ['active']


class PaymentTermsViewSet(_ComercialMixin, viewsets.ModelViewSet):
    """Condicions de pagament (M4): CRUD amb fraccions nested writable. El guard Σ%=100 viu al
    serializer. Els cridadors (fitxa d'oferta i fitxa de client) són tots comercials."""
    queryset = PaymentTerms.objects.prefetch_related('lines').all()
    serializer_class = PaymentTermsSerializer
    filterset_fields = ['active']


class ProductViewSet(_ComercialMixin, viewsets.ModelViewSet):
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


class ProductRecipeViewSet(_ComercialMixin, viewsets.ModelViewSet):
    queryset = ProductRecipe.objects.select_related('product').all()
    serializer_class = ProductRecipeSerializer
    filterset_fields = ['product', 'task_code']


class ProductSupplierViewSet(_ComercialMixin, viewsets.ModelViewSet):
    queryset = ProductSupplier.objects.select_related('product', 'supplier').all()
    serializer_class = ProductSupplierSerializer
    filterset_fields = ['product', 'supplier', 'is_default']


class ProductComponentViewSet(_ComercialMixin, viewsets.ModelViewSet):
    queryset = ProductComponent.objects.select_related('pack', 'component').all()
    serializer_class = ProductComponentSerializer
    filterset_fields = ['pack', 'component']


class ProductPriceGTIViewSet(_ComercialMixin, viewsets.ModelViewSet):
    queryset = ProductPriceGTI.objects.select_related('product', 'garment_type_item').all()
    serializer_class = ProductPriceGTISerializer
    filterset_fields = ['product', 'garment_type_item']


# ── Documents comercials — Quote (B2) ──────────────────────────────────────────────────

class QuoteViewSet(_ComercialMixin, viewsets.ModelViewSet):
    """CRUD d'ofertes + accions `send` (DRAFT→SENT) i `pdf` (descàrrega)."""
    queryset = Quote.objects.select_related('customer', 'created_by').prefetch_related(
        'lines__product', 'lines__model_intents__model').all()
    serializer_class = QuoteSerializer
    filterset_fields = ['status', 'customer']

    def get_permissions(self):
        # El PDF és una LECTURA, i per això no demana CONFIGURE — però és l'oferta sencera
        # amb tots els imports impresos, o sigui la lectura més sensible del mòdul. Demana
        # COMERCIAL com qualsevol altra lectura d'aquí (abans n'hi havia prou amb estar
        # autenticat: un tècnic se'l baixava, verificat a la diagnosi §2.3).
        if self.action == 'pdf':
            return [_Comercial()]
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
        """Genera i retorna el PDF de l'oferta (reportlab, P5). Import mandrós per no acoblar.

        `?lang=` és l'idioma triat per l'operador en emetre; si no ve o no és vàlid, mana el
        del client destinatari i, en últim terme, el fallback (resolve_pdf_lang)."""
        quote = self.get_object()
        from .pdf_service import generate_quote_pdf, resolve_pdf_lang
        lang = resolve_pdf_lang(request.query_params.get('lang'), quote.customer)
        pdf_bytes = generate_quote_pdf(quote, lang=lang)
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
            order, meta = convert_quote_to_order(quote, user=request.user)
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        # meta.intent_conflicts: models d'intenció que no han pogut viatjar (ocupats en una altra
        # comanda o sense quantitat) — el frontend els mostra al comercial. Mai bloqueja la conversió.
        # `context=` no és decoratiu: sense request al context la poda econòmica talla per
        # defecte i fins un admin rebria la comanda acabada de crear sense totals.
        return Response({**SalesOrderSerializer(order, context=self.get_serializer_context()).data,
                         **meta}, status=status.HTTP_201_CREATED)


class QuoteLineViewSet(_ComercialMixin, viewsets.ModelViewSet):
    """Línies d'oferta (edició filtrada per ?quote=, patró satèl·lit B1). El guard DRAFT viu al
    model i es replica al serializer per a un 400 net."""
    queryset = QuoteLine.objects.select_related('quote', 'product').all()
    serializer_class = QuoteLineSerializer
    filterset_fields = ['quote', 'product']


class QuoteLineModelIntentViewSet(_ComercialMixin, viewsets.ModelViewSet):
    """Vincle preparatori model↔línia d'oferta (E2, patró satèl·lit ?quote_line=). Escriptura
    gated CONFIGURE; els guards (estat DRAFT/SENT + coherència de client) viuen al serializer.
    Intenció informativa: no toca WO ni cartera."""
    queryset = QuoteLineModelIntent.objects.select_related(
        'quote_line__quote', 'model').all()
    serializer_class = QuoteLineModelIntentSerializer
    filterset_fields = ['quote_line', 'model']

    def perform_create(self, serializer):
        serializer.save(created_by=getattr(self.request.user, 'profile', None))

    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk(self, request):
        """POST commerce/quote-line-intents/bulk/ — crea intents en LOT per a una línia d'oferta.
        Ignora silenciosament els duplicats ja existents (unique_together). Gate CONFIGURE.
        Body: {quote_line, model_ids:[...]}. Resposta: {created:[ids], skipped:[model_ids]}."""
        from .models import QuoteLine
        quote_line_id = request.data.get('quote_line')
        model_ids = request.data.get('model_ids')
        if not quote_line_id or not isinstance(model_ids, list) or not model_ids:
            return Response({'detail': 'quote_line i model_ids (llista no buida) requerits.'},
                            status=status.HTTP_400_BAD_REQUEST)
        line = QuoteLine.objects.filter(pk=quote_line_id).select_related('quote').first()
        if line is None:
            return Response({'detail': "Línia d'oferta no trobada."}, status=status.HTTP_404_NOT_FOUND)
        try:
            model_ids = [int(x) for x in model_ids]
        except (TypeError, ValueError):
            return Response({'detail': "model_ids ha de ser una llista d'enters."},
                            status=status.HTTP_400_BAD_REQUEST)
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import create_quote_line_intents_bulk
        try:
            res = create_quote_line_intents_bulk(
                line, model_ids, user=getattr(request.user, 'profile', None))
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(res, status=status.HTTP_201_CREATED)


# ── Documents comercials — SalesOrder (comanda, B3b) ───────────────────────────────────

class SalesOrderViewSet(_ComercialMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                        mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Comandes de venda (B3b). NOMÉS lectura + update restringit a `status` (les comandes neixen
    de la conversió d'una oferta, mai per POST; irreversibilitat de línies via serializer).

    ⚠️ LECTURA OBERTA A POSTA (decisió d'Agus, 2026-08-14): l'assignació model↔comanda és una
    ACCIÓ OPERATIVA, no un acte comercial, i el seu selector viu a la fitxa del model
    (`ActionsMenu.jsx:86` demana les comandes OPEN del client). Qui assigna ha de poder triar
    la comanda encara que no vegi el diner. El selector només fa servir `document_number` i,
    de les línies, `quantity`/`qty_allocated` — cap import: la poda del serializer el deixa
    intacte. L'escriptura (status, data d'emissió) sí que és comercial i va gated."""
    queryset = SalesOrder.objects.select_related('customer', 'source_quote', 'created_by').prefetch_related(
        'lines__product', 'due_dates').all()
    serializer_class = SalesOrderSerializer
    filterset_fields = ['status', 'customer']

    def get_permissions(self):
        # El PDF imprimeix tots els imports: és lectura, però lectura COMERCIAL.
        if self.action == 'pdf':
            return [_Comercial()]
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_update(self, serializer):
        # Els venciments estan ancorats a la data d'emissió (due_date = issued_at + days_offset,
        # services.py:127): si es corregeix la data, s'han de tornar a materialitzar. Només quan
        # ha canviat de debò — un PATCH de `status` no ha de reescriure la taula de venciments.
        before = serializer.instance.issued_at
        order = serializer.save()
        if order.issued_at != before:
            from .services import generate_due_dates
            generate_due_dates(order)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """PDF de la comanda: reutilitza el generador de l'oferta amb la clau de títol
        'doc_order' (la CLAU, no el text: qui tradueix és el generador). `?lang=` com a Quote."""
        order = self.get_object()
        from .pdf_service import generate_document_pdf, resolve_pdf_lang
        lang = resolve_pdf_lang(request.query_params.get('lang'), order.customer)
        pdf_bytes = generate_document_pdf(order, doc_key='doc_order', lang=lang)
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{order.document_number or "order"}.pdf"'
        return resp


class SalesOrderLineViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin,
                            mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Línies de comanda (lectura + PATCH restringit a `qty_allocated`, filtrat per ?order=). Sense
    create/destroy: les línies neixen de la conversió (irreversibilitat, B3b).

    ⚠️ AQUESTA VISTA ÉS LA CASA DE L'ACCIÓ OPERATIVA i per això no porta `_ComercialMixin`.
    `assign-model`/`assign-models` són l'assignació model↔comanda, que Agus va decidir
    (2026-08-14) que queda FORA de COMERCIAL: qui assigna fa cartera, no comerç. També hi
    entra el PATCH de `qty_allocated`, que és la imputació d'aquella mateixa cartera. Tot
    plegat segueix demanant CONFIGURE, que és el que el manager ja té.

    Els imports de les línies els poda el serializer, igual que a la comanda."""
    queryset = SalesOrderLine.objects.select_related('order', 'product').all()
    serializer_class = SalesOrderLineSerializer
    filterset_fields = ['order', 'product']

    def get_permissions(self):
        # `allocation` és una expansió read-only (models assignats + tasques + % imputat) i
        # no porta cap import: alimenta el desplegable de la fitxa de comanda.
        if self.action in ('list', 'retrieve', 'allocation'):
            return [IsAuthenticated()]
        return [_Configure()]

    @action(detail=True, methods=['get'])
    def allocation(self, request, pk=None):
        """GET commerce/order-lines/{id}/allocation/ — expansió READ-ONLY de la línia (P4): els
        models assignats (via WorkOrder), les seves tasques de recepta amb estat, i el % imputat.
        Alimenta el desplegable de la fitxa de comanda. No escriu res."""
        from decimal import Decimal
        line = self.get_object()
        q, alloc = Decimal(line.quantity or 0), Decimal(line.qty_allocated or 0)
        pct = float((alloc / q * 100).quantize(Decimal('0.1'))) if q > 0 else 0.0
        wos = line.work_orders.select_related('model').prefetch_related('tasks__task_type').order_by('id')
        # Mirall del guard de unassign_model_from_order_line: un WO ORDER OPEN i NO albaranat es pot
        # desassignar. Precalculem els albaranats en 1 query per no fer N+1 (el frontend amaga el botó).
        from .models import DeliveryNoteLine
        billed_ids = set(DeliveryNoteLine.objects.filter(work_order__in=wos)
                         .values_list('work_order_id', flat=True))
        work_orders = [{
            'id': wo.id, 'number': wo.number, 'status': wo.status, 'kind': wo.kind,
            'can_unassign': (wo.kind == 'ORDER' and wo.status == 'OPEN' and wo.id not in billed_ids),
            'model': ({'id': wo.model.id, 'codi_intern': wo.model.codi_intern,
                       'nom_prenda': wo.model.nom_prenda} if wo.model_id else None),
            'tasks': [{
                'id': tk.id, 'code': tk.task_type.code, 'name': tk.task_type.name,
                'status': tk.status, 'off_recipe': tk.off_recipe,
            } for tk in sorted(wo.tasks.all(), key=lambda x: (x.off_recipe, x.order, x.id))],
        } for wo in wos]
        return Response({
            'line_id': line.id, 'quantity': str(q), 'qty_allocated': str(alloc),
            'pct_allocated': pct, 'work_orders': work_orders,
        })

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
        return Response({'work_order': WorkOrderSerializer(
                            wo, context=self.get_serializer_context()).data, **meta},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='assign-models')
    def assign_models(self, request, pk=None):
        """POST commerce/order-lines/{id}/assign-models/ — assigna N models a la línia en UNA
        transacció TOT-O-RES (select_for_update + validació de capacitat conjunta abans d'assignar
        res). Gate CONFIGURE. Body: {model_ids:[...]}. Resposta: {work_orders, warnings}."""
        line = self.get_object()
        model_ids = request.data.get('model_ids')
        if not isinstance(model_ids, list) or not model_ids:
            return Response({'detail': 'model_ids (llista no buida) requerit.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            model_ids = [int(x) for x in model_ids]
        except (TypeError, ValueError):
            return Response({'detail': "model_ids ha de ser una llista d'enters."},
                            status=status.HTTP_400_BAD_REQUEST)
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import assign_models_to_order_line_batch
        try:
            wos, warnings = assign_models_to_order_line_batch(
                line.id, model_ids, user=getattr(request.user, 'profile', None))
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'work_orders': WorkOrderSerializer(
                            wos, many=True, context=self.get_serializer_context()).data,
                         'warnings': warnings},
                        status=status.HTTP_201_CREATED)


class WorkOrderViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Encàrrecs / ordres de treball (B4a). No es crea per POST: els ORDER neixen del wizard
    (B4b) i els COLLECTOR del hook lazy. Llista filtrable per kind/status/customer/period.

    ⚠️ LECTURA OBERTA A POSTA: la pestanya Producció de la fitxa del model demana els WO per
    `?model=` (`ProductionTab.jsx:75`) per pintar la cadena comanda→encàrrec→albarà, i només
    en fa servir `number/kind/status/order_number/delivery_note_number`. El `price_snapshot`
    el poda el serializer. Tancar-ho amb 403 buidaria la traçabilitat a tot el taller."""
    queryset = WorkOrder.objects.select_related('customer', 'model', 'closed_by', 'order_line') \
        .prefetch_related('adjustments', 'tasks__task_type').all()
    serializer_class = WorkOrderSerializer
    filterset_fields = ['kind', 'status', 'customer', 'period', 'model']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        # `orphaned` NO pot anar amb els altres dos: es construeix el payload A MÀ
        # (`'total': str(order.total)`, sota) i per tant NO passa pel serializer ni per la
        # poda. A més és l'informe de la pantalla Comercial › Orfes. Lectura, però COMERCIAL.
        if self.action == 'orphaned':
            return [_Comercial()]
        # `review` és literalment la revisió del PREU DE VENDA d'un encàrrec tancat: qui la
        # fa ha de veure el diner (COMERCIAL) i poder configurar (CONFIGURE).
        if self.action == 'review':
            return [_Comercial(), _Configure()]
        # `unassign`/`reattach` mouen CARTERA, no preu: mateix estatut operatiu que
        # assign-model, i per tant fora de COMERCIAL (decisió d'Agus, 2026-08-14).
        if self.action in ('unassign', 'reattach'):
            return [_Configure()]
        # `close` és del TÈCNIC (feina feta). `reattach-candidates` cau aquí i queda com
        # estava: és una lectura sense imports servida amb DEFINE_TASKS — incoherència
        # anterior a aquesta peça, ANOTADA al report i no tocada (fora de scope).
        return [_DefineTasks()]

    @action(detail=False, methods=['get'])
    def orphaned(self, request):
        """GET commerce/work-orders/orphaned/ — informe (read-only) dels WO desassignats
        (orphaned_from_line no null): pendents de reassignar. Data, comanda i línia origen, total
        de la comanda, estat del WO. Llistat simple, sense filtres avançats (D6)."""
        qs = (WorkOrder.objects
              .filter(orphaned_from_line__isnull=False)
              .select_related('orphaned_from_line__order', 'orphaned_from_line__product',
                              'model', 'customer')
              .order_by('-created_at'))
        out = []
        for wo in qs:
            line = wo.orphaned_from_line
            order = line.order if line else None
            out.append({
                'id': wo.id, 'number': wo.number, 'status': wo.status, 'created_at': wo.created_at,
                'customer': wo.customer.nom if wo.customer_id else None,
                'model': ({'id': wo.model.id, 'codi_intern': wo.model.codi_intern,
                           'nom_prenda': wo.model.nom_prenda} if wo.model_id else None),
                'order': ({'id': order.id, 'document_number': order.document_number,
                           'total': str(order.total), 'status': order.status} if order else None),
                'line': ({'id': line.id, 'description': line.description or getattr(line.product, 'name', None),
                          'quantity': str(line.quantity)} if line else None),
            })
        return Response({'orphaned': out})

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

    @action(detail=True, methods=['post'])
    def unassign(self, request, pk=None):
        """POST commerce/work-orders/{id}/unassign/ — desassigna el model de la línia: ORFANDA el
        WO (order_line→None, orphaned_from_line→línia origen) i allibera 1 unitat de qty_allocated.
        Gate CONFIGURE (com assign-model). Guards durs: kind=ORDER, status=OPEN, no albaranat.
        200 amb el WO actualitzat, o 400 amb el missatge del guard que ha fallat."""
        wo = self.get_object()
        profile = getattr(request.user, 'profile', None)
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import unassign_model_from_order_line
        try:
            wo = unassign_model_from_order_line(wo, user=profile)
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(wo).data)

    @action(detail=True, methods=['get'], url_path='reattach-candidates')
    def reattach_candidates(self, request, pk=None):
        """GET commerce/work-orders/{id}/reattach-candidates/ — línies de comanda candidates per
        re-adoptar aquest WO orfe: comandes OPEN del MATEIX client amb quantitat disponible
        (qty_allocated < quantity). READ-ONLY, alimenta el picker de reassignació (E5)."""
        from decimal import Decimal
        wo = self.get_object()
        lines = (SalesOrderLine.objects
                 .filter(order__customer_id=wo.customer_id, order__status='OPEN')
                 .select_related('order', 'product').order_by('-order__created_at', 'position', 'id'))
        out = []
        for ln in lines:
            q, alloc = Decimal(ln.quantity or 0), Decimal(ln.qty_allocated or 0)
            if alloc >= q:
                continue
            out.append({
                'id': ln.id, 'order': ln.order_id, 'order_number': ln.order.document_number,
                'product_code': getattr(ln.product, 'code', None),
                'description': ln.description or getattr(ln.product, 'name', ''),
                'quantity': str(q), 'qty_allocated': str(alloc),
            })
        return Response({'candidates': out})

    @action(detail=True, methods=['post'])
    def reattach(self, request, pk=None):
        """POST commerce/work-orders/{id}/reattach/ — re-adopta el WO orfe a una línia de comanda
        nova (order_line→línia, orphaned_from_line→null, snapshots re-congelats). Gate CONFIGURE.
        Body: {order_line_id}. 200 amb el WO actualitzat, o 400/404 amb el missatge del guard."""
        wo = self.get_object()
        profile = getattr(request.user, 'profile', None)
        line = SalesOrderLine.objects.filter(pk=request.data.get('order_line_id')).first()
        if line is None:
            return Response({'detail': 'Línia de comanda no trobada.'}, status=status.HTTP_404_NOT_FOUND)
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import reattach_orphan_to_line
        try:
            wo = reattach_orphan_to_line(wo, line, user=profile)
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(wo).data)


class ExpenseViewSet(_ComercialMixin, viewsets.ModelViewSet):
    """Despeses d'un encàrrec (B4b): línies externes (servei extern / mercaderia) amb cost
    real i preu de venda. Satèl·lit del WorkOrder, filtrat per ?work_order= (mateix patró que
    order-lines/quote-lines). NO és una tasca. Una despesa és cost i marge de dalt a baix:
    aquí la lectura també demana COMERCIAL, cap pantalla tècnica no la consulta."""
    queryset = Expense.objects.select_related('product', 'supplier', 'created_by').all()
    serializer_class = ExpenseSerializer
    filterset_fields = ['work_order', 'product', 'supplier']

    def perform_create(self, serializer):
        serializer.save(created_by=getattr(self.request.user, 'profile', None))


# ── Documents comercials — DeliveryNote (albarà, B4c) ──────────────────────────────────

class DeliveryNoteViewSet(_ComercialMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
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
        # El PDF de l'albarà és el document amb els imports impresos: lectura COMERCIAL.
        if self.action == 'pdf':
            return [_Comercial()]
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def billable(self, request):
        """GET commerce/delivery-notes/billable/?customer=<id> — safata d'albaranables (v2)
        agrupada per model (tasques Done + extres + deduccions + despeses sense línia d'albarà).
        Gate CONFIGURE. Parteix de ModelTask: veu també la feina amb work_order=NULL (R2)."""
        from fhort.tasks.models import Customer
        customer_id = request.query_params.get('customer')
        customer = Customer.objects.filter(pk=customer_id).first()
        if customer is None:
            return Response({'detail': 'Client no trobat.'}, status=status.HTTP_404_NOT_FOUND)
        from .services import get_billable_items
        return Response({'customer': customer.id, 'groups': get_billable_items(customer)})

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

    @action(detail=False, methods=['post'])
    def draft(self, request):
        """POST commerce/delivery-notes/draft/ — retorna el DRAFT obert del client o en crea un de
        nou (un per client alhora). Gate CONFIGURE. Body: {customer}."""
        from fhort.tasks.models import Customer
        customer = Customer.objects.filter(pk=request.data.get('customer')).first()
        if customer is None:
            return Response({'detail': 'Client no trobat.'}, status=status.HTTP_404_NOT_FOUND)
        from .services import create_or_get_draft
        dn, created = create_or_get_draft(customer, user=getattr(request.user, 'profile', None))
        return Response(self.get_serializer(dn).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='add-lines')
    def add_lines(self, request, pk=None):
        """POST commerce/delivery-notes/{id}/add-lines/ — afegeix línies al DRAFT a partir dels
        ítems seleccionats de la safata. Gate CONFIGURE. Body: {items:[{kind, model_task_id|
        adjustment_id|expense_id}]}. Els ítems ja albaranats s'ometen (idempotent)."""
        dn = self.get_object()
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import add_lines_to_draft
        try:
            created = add_lines_to_draft(dn, request.data.get('items') or [],
                                         user=getattr(request.user, 'profile', None))
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        dn.refresh_from_db()
        return Response({'added': len(created), **self.get_serializer(dn).data})

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

    @action(detail=True, methods=['post'], url_path='mark-invoiced')
    def mark_invoiced(self, request, pk=None):
        """POST commerce/delivery-notes/{id}/mark-invoiced/ — ISSUED→INVOICED. Gate CONFIGURE."""
        dn = self.get_object()
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import mark_delivery_note_invoiced
        try:
            mark_delivery_note_invoiced(dn, user=getattr(request.user, 'profile', None))
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(dn).data)

    @action(detail=False, methods=['post'], url_path='mark-invoiced-bulk')
    def mark_invoiced_bulk(self, request):
        """POST commerce/delivery-notes/mark-invoiced-bulk/ — marcatge massiu ISSUED→INVOICED.
        Gate CONFIGURE. Body: {ids:[...]}. Retorna {marked, skipped} (els no-ISSUED s'ometen)."""
        from .services import mark_delivery_note_invoiced
        from django.core.exceptions import ValidationError as DjangoValidationError
        ids = request.data.get('ids') or []
        profile = getattr(request.user, 'profile', None)
        marked, skipped = [], []
        for dn in DeliveryNote.objects.filter(pk__in=ids):
            try:
                mark_delivery_note_invoiced(dn, user=profile)
                marked.append(dn.id)
            except DjangoValidationError:
                skipped.append(dn.id)
        return Response({'marked': marked, 'skipped': skipped})

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """PDF de l'albarà v2 (compost per model), SENSE bloc de venciments/condicions de
        pagament. `?lang=` com a Quote/SalesOrder."""
        dn = self.get_object()
        from .pdf_service import generate_delivery_note_pdf, resolve_pdf_lang
        lang = resolve_pdf_lang(request.query_params.get('lang'), dn.customer)
        pdf_bytes = generate_delivery_note_pdf(dn, lang=lang)
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{dn.document_number or "albara"}.pdf"'
        return resp

    def destroy(self, request, *args, **kwargs):
        dn = self.get_object()
        if dn.status != 'DRAFT':
            return Response({'detail': "No es pot esborrar un albarà emès (ISSUED)."},
                            status=status.HTTP_409_CONFLICT)
        return super().destroy(request, *args, **kwargs)


class DeliveryNoteLineViewSet(_ComercialMixin, mixins.RetrieveModelMixin,
                              mixins.ListModelMixin, mixins.CreateModelMixin,
                              mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                              viewsets.GenericViewSet):
    """Línies d'albarà (edició filtrada per ?delivery_note=). PATCH de preu/descripció/qty/visible
    en DRAFT (guard replicat al serializer per a un 400 net); FK de traçabilitat read-only. `create`
    crea una línia MANUAL (comentari lliure) en un DRAFT; `destroy` treu una línia del DRAFT. Les
    línies proposades neixen de `add-lines/` (v2) o `generate/` (v1).

    ⚠️ LECTURA OBERTA A POSTA: `ProductionTab.jsx:76` demana aquestes línies per `?model=` des
    de la fitxa del model i només en pinta `dn_number`/`dn_status`. És el cas que va obrir la
    peça — hi viatjaven `unit_price`, `line_total` i `internal_cost` (diagnosi §3.2) — i el
    serializer els poda. L'escriptura (preu de la línia en DRAFT) sí que és comercial."""
    queryset = DeliveryNoteLine.objects.select_related('delivery_note', 'product', 'model').all()
    serializer_class = DeliveryNoteLineSerializer
    filterset_fields = ['delivery_note', 'line_kind', 'model']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """POST commerce/delivery-note-lines/ — crea una línia MANUAL (comentari/lliure) en un DRAFT.
        Body: {delivery_note, description, quantity?, unit_price?, visible?}. line_kind forçat MANUAL."""
        from decimal import Decimal
        dn = DeliveryNote.objects.filter(pk=request.data.get('delivery_note')).first()
        if dn is None:
            return Response({'detail': 'Albarà no trobat.'}, status=status.HTTP_404_NOT_FOUND)
        if dn.status != 'DRAFT':
            return Response({'detail': "No es poden afegir línies a un albarà que no és DRAFT."},
                            status=status.HTTP_400_BAD_REQUEST)
        line = DeliveryNoteLine(
            delivery_note=dn, line_kind='MANUAL',
            description=str(request.data.get('description') or '')[:300],
            quantity=Decimal(str(request.data.get('quantity') or '0')),
            unit_price=Decimal(str(request.data.get('unit_price') or '0')),
            visible=bool(request.data.get('visible', True)),
            position=dn.lines.count() + 1)
        line.save()
        return Response(self.get_serializer(line).data, status=status.HTTP_201_CREATED)
