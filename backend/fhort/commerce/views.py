"""ViewSets del mestre d'articles (B1).

Gating: lectura = qualsevol autenticat; escriptura = capability CONFIGURE (semàntica de
configuració de catàleg, com CustomerViewSet). La capability pròpia del mòdul i el gate de
tier (feature_flags) arriben a B5.
"""
from django.db.models import ProtectedError
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.accounts.capabilities import HasCapability, CONFIGURE

from .models import Unit, Product, ProductRecipe, ProductSupplier, ProductComponent, ProductPriceGTI
from .serializers import (
    UnitSerializer, ProductSerializer, ProductRecipeSerializer, ProductSupplierSerializer,
    ProductComponentSerializer, ProductPriceGTISerializer,
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
