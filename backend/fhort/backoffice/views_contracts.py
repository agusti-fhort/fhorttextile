import logging

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import ServiceCatalog, TenantContract
from .serializers_contracts import (
    ServiceCatalogSerializer,
    TenantContractListSerializer, TenantContractDetailSerializer,
    TenantContractCreateSerializer,
)
from .views import HasBackofficeRole

logger = logging.getLogger(__name__)

ADMIN_ACTIONS = {'create', 'update', 'partial_update', 'destroy'}


class ServiceCatalogViewSet(viewsets.ModelViewSet):
    queryset = ServiceCatalog.objects.all()
    filterset_fields = ['tipus', 'actiu']
    serializer_class = ServiceCatalogSerializer

    def get_permissions(self):
        roles = ['ADMIN'] if self.action in ADMIN_ACTIONS else None
        return [IsAuthenticated(), HasBackofficeRole(roles=roles)()]


class TenantContractViewSet(viewsets.ModelViewSet):
    queryset = TenantContract.objects.select_related('client').prefetch_related('lines__service').all()
    filterset_fields = ['client', 'actiu']

    def get_permissions(self):
        roles = ['ADMIN'] if self.action in ADMIN_ACTIONS else None
        return [IsAuthenticated(), HasBackofficeRole(roles=roles)()]

    def get_serializer_class(self):
        if self.action == 'create':   return TenantContractCreateSerializer
        if self.action == 'retrieve': return TenantContractDetailSerializer
        return TenantContractListSerializer


from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status as drf_status
from .billing_service import generate_invoice


@api_view(['POST'])
@permission_classes([IsAuthenticated, HasBackofficeRole()])
def generate_invoice_view(request):
    """Sprint 6: genera la factura automàtica per a {codi_client, period}.
    Body: { codi_client: 'FTT', period: '2026-06', dry_run: false }"""
    codi_client = request.data.get('codi_client')
    period      = request.data.get('period')
    dry_run     = request.data.get('dry_run', False)

    if not codi_client or not period:
        return Response({'error': 'codi_client i period són obligatoris.'}, status=400)

    try:
        invoice, created, warnings = generate_invoice(codi_client, period, dry_run=dry_run)
        return Response({
            'dry_run': dry_run,
            'created': created,
            'warnings': warnings,
            'invoice_id': invoice.id if invoice else None,
            'total': str(invoice.total) if invoice else None,
            'estat': invoice.estat if invoice else None,
        })
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        logger.exception('generate_invoice_view error')
        return Response({'error': str(e)}, status=500)
