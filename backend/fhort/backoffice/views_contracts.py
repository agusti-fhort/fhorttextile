from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import ServiceCatalog, TenantContract
from .serializers_contracts import (
    ServiceCatalogSerializer,
    TenantContractListSerializer, TenantContractDetailSerializer,
    TenantContractCreateSerializer,
)
from .views import HasBackofficeRole

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
