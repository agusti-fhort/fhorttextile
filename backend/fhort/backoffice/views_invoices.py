"""
views_invoices.py — API de la facturació fiscal (F-FACT B1).

Tres superfícies:
  · /series/     CRUD de sèries de numeració (l'operador les crea; el codi no en sembra cap)
  · /tipus-iva/  CRUD de tipus d'IVA (percentatge i menció legal són dada)
  · /factures/   camí manual complet: esborrany → línies → previsualitzar → emetre → PDF

Permisos: lectura per a qualsevol perfil de backoffice; escriptura i EMISSIÓ, només
ADMIN (mateix patró que ServiceCatalog/TenantContract).
"""
import logging

from django.http import HttpResponse
from rest_framework import views, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .invoice_pdf import generate_invoice_pdf
from .invoice_service import compute_totals, create_rectificativa, emit_invoice
from .models import Invoice, InvoiceLine, InvoiceSerie, VATRate
from .recurring_service import generate_invoices
from .serializers_invoices import (
    InvoiceCreateSerializer, InvoiceDetailSerializer, InvoiceLineSerializer,
    InvoiceListSerializer, InvoiceSerieSerializer, VATRateSerializer,
)
from .views import HasBackofficeRole

logger = logging.getLogger(__name__)

ADMIN_ACTIONS = {'create', 'update', 'partial_update', 'destroy',
                 'linia', 'emetre', 'rectificar'}


class InvoiceSerieViewSet(viewsets.ModelViewSet):
    queryset = InvoiceSerie.objects.all()
    serializer_class = InvoiceSerieSerializer
    filterset_fields = ['activa']

    def get_permissions(self):
        roles = ['ADMIN'] if self.action in ADMIN_ACTIONS else None
        return [IsAuthenticated(), HasBackofficeRole(roles=roles)()]

    def perform_destroy(self, instance):
        # Una sèrie que ja ha numerat factures és part del seu rastre fiscal: es
        # desactiva, no s'esborra (si no, el número de la factura apuntaria al no-res).
        if instance.invoices.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {'error': f'La sèrie {instance.codi} ja ha numerat factures: '
                          f'desactiva-la en comptes d\'esborrar-la.'})
        instance.delete()


class VATRateViewSet(viewsets.ModelViewSet):
    queryset = VATRate.objects.all()
    serializer_class = VATRateSerializer
    filterset_fields = ['actiu', 'regim_default']

    def get_permissions(self):
        roles = ['ADMIN'] if self.action in ADMIN_ACTIONS else None
        return [IsAuthenticated(), HasBackofficeRole(roles=roles)()]

    def perform_destroy(self, instance):
        if instance.invoice_lines.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {'error': f'El tipus {instance.codi} ja s\'ha aplicat a factures: '
                          f'desactiva\'l en comptes d\'esborrar-lo.'})
        instance.delete()


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = (Invoice.objects
                .select_related('client', 'serie', 'rectifica')
                .prefetch_related('lines__service', 'lines__vat_rate')
                .all())
    # Es filtra per la clau natural del client (codi_tenant), com la resta de l'API:
    # la SPA no veu mai la pk d'un Client.
    filterset_fields = ['client__codi_tenant', 'estat', 'tipus', 'serie', 'period']

    def get_permissions(self):
        roles = ['ADMIN'] if self.action in ADMIN_ACTIONS else None
        return [IsAuthenticated(), HasBackofficeRole(roles=roles)()]

    def get_serializer_class(self):
        if self.action == 'create':
            return InvoiceCreateSerializer
        if self.action in ('retrieve', 'preview'):
            return InvoiceDetailSerializer
        return InvoiceListSerializer

    def _guard(self, fn, *a, **kw):
        """Els guards del domini parlen amb ValueError; l'API respon 400 amb el motiu."""
        from rest_framework.exceptions import ValidationError
        try:
            return fn(*a, **kw)
        except ValueError as e:
            raise ValidationError({'error': str(e)})

    def _fresh(self, invoice):
        """La factura rellegida de zero.

        get_object() ve amb prefetch_related('lines'): després d'afegir o esborrar una
        línia, aquell cache està RANCI i la resposta ensenyaria l'estat d'abans. Es
        rellegeix pel queryset, que és qui sap com carregar-la sencera.
        """
        return self.get_queryset().get(pk=invoice.pk)

    def perform_destroy(self, instance):
        # El model ja barra l'esborrat d'una emesa; aquí es tradueix a 400 llegible.
        self._guard(instance.delete)

    @action(detail=True, methods=['post', 'patch', 'delete'], url_path='linia')
    def linia(self, request, pk=None):
        """Alta/edició/baixa d'una línia de l'esborrany. El total de la línia el calcula
        el servidor (quantitat × preu_unit): un import que no quadri amb els seus factors
        no és una factura, és un error de captura."""
        from decimal import Decimal
        from rest_framework.exceptions import ValidationError
        invoice = self.get_object()
        if invoice.estat != Invoice.ESTAT_ESBORRANY:
            raise ValidationError(
                {'error': f'La factura està {invoice.estat} i és immutable. '
                          f'La correcció d\'una emesa és una rectificativa.'})

        if request.method == 'DELETE':
            line = InvoiceLine.objects.filter(pk=request.data.get('id'), invoice=invoice).first()
            if not line:
                raise ValidationError({'error': 'Línia no trobada en aquesta factura.'})
            self._guard(line.delete)
            return Response(InvoiceDetailSerializer(self._fresh(invoice)).data)

        data = dict(request.data)
        line = None
        if request.method == 'PATCH':
            line = InvoiceLine.objects.filter(pk=data.get('id'), invoice=invoice).first()
            if not line:
                raise ValidationError({'error': 'Línia no trobada en aquesta factura.'})
        ser = InvoiceLineSerializer(line, data=data, partial=(request.method == 'PATCH'))
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        qt = v.get('quantitat', line.quantitat if line else Decimal('1'))
        pu = v.get('preu_unit', line.preu_unit if line else Decimal('0'))
        obj = self._guard(ser.save, invoice=invoice, total=(Decimal(qt) * Decimal(pu)))
        logger.info('Factura %s: línia %s desada', invoice.pk, obj.pk)
        return Response(InvoiceDetailSerializer(self._fresh(invoice)).data)

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Totals calculats SENSE persistir res ni reservar número: el que es veurà."""
        invoice = self.get_object()
        base, quota, total, grups = self._guard(compute_totals, invoice)
        data = InvoiceDetailSerializer(invoice).data
        data['calcul'] = {
            'base_imposable': str(base), 'quota_iva': str(quota), 'total': str(total),
            'per_tipus': [{'codi': g['codi'], 'nom': g['nom'], 'pct': str(g['pct']),
                           'base': str(g['base']), 'quota': str(g['quota']),
                           'mencio_legal': g['mencio_legal']} for g in grups],
        }
        return Response(data)

    @action(detail=True, methods=['post'])
    def emetre(self, request, pk=None):
        """Emet: congela l'IVA, reserva el número de la sèrie i passa a EMESA."""
        from rest_framework.exceptions import ValidationError
        invoice = self.get_object()
        serie_id = request.data.get('serie')
        if not serie_id:
            raise ValidationError({'error': 'Cal indicar la sèrie amb què s\'emet.'})
        serie = InvoiceSerie.objects.filter(pk=serie_id).first()
        if serie is None:
            raise ValidationError({'error': f'Sèrie {serie_id} no trobada.'})
        invoice = self._guard(emit_invoice, invoice, serie)
        return Response(InvoiceDetailSerializer(invoice).data)

    @action(detail=True, methods=['post'])
    def rectificar(self, request, pk=None):
        """Crea l'ESBORRANY de la rectificativa (línies en negatiu). No emet res."""
        rect = self._guard(create_rectificativa, self.get_object(),
                           motiu=request.data.get('motiu', ''))
        return Response(InvoiceDetailSerializer(rect).data, status=201)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        invoice = self.get_object()
        pdf = self._guard(generate_invoice_pdf, invoice)
        nom = invoice.numero or f'esborrany-{invoice.pk}'
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="factura-{nom}.pdf"'
        return resp


class TancamentPeriodeView(views.APIView):
    """Tancament de període (F-RECUR): preview i generació de DRAFTs recurrents.

    GET  ?period=YYYY-MM[&client=COD]  → informe per client (dry-run, no persisteix).
    POST {period, client?}             → genera els DRAFTs (idempotent).
    Només ADMIN pot generar; el preview el pot veure qualsevol perfil de backoffice.
    """
    def get_permissions(self):
        roles = ['ADMIN'] if self.request.method == 'POST' else None
        return [IsAuthenticated(), HasBackofficeRole(roles=roles)()]

    def _run(self, request, dry_run):
        from rest_framework.exceptions import ValidationError
        period = request.query_params.get('period') or request.data.get('period')
        if not period or len(period) != 7 or period[4] != '-':
            raise ValidationError({'error': "Cal un període 'YYYY-MM'."})
        codi = request.query_params.get('client') or request.data.get('client')
        reports = generate_invoices(period, codi_client=codi or None, dry_run=dry_run)
        # Els Decimal no són JSON-serialitzables directament: a text, com la resta de l'API.
        for r in reports:
            if 'total_sense_iva' in r:
                r['total_sense_iva'] = str(r['total_sense_iva'])
        return Response({'period': period, 'dry_run': dry_run, 'clients': reports})

    def get(self, request):
        return self._run(request, dry_run=True)

    def post(self, request):
        return self._run(request, dry_run=False)
