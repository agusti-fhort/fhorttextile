from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    GarmentGroup,
    GarmentType,
    GradingRule,
    GradingRuleSet,
    POMCategory,
    POMMaster,
    SizeDefinition,
    SizeSystem,
)
from .serializers import (
    GarmentGroupSerializer,
    GarmentTypeSerializer,
    GradingRuleSerializer,
    GradingRuleSetSerializer,
    POMCategorySerializer,
    POMMasterSerializer,
    SizeDefinitionSerializer,
    SizeSystemSerializer,
)


class POMMasterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = POMMasterSerializer
    queryset = POMMaster.objects.select_related('pom_global').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['actiu', 'pom_global']
    search_fields = ['codi_client', 'nom_client']
    ordering_fields = ['codi_client', 'nom_client']
    ordering = ['codi_client']


class SizeSystemViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SizeSystemSerializer
    queryset = SizeSystem.objects.prefetch_related('talles').all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['actiu']
    search_fields = ['codi', 'nom']
    ordering = ['codi']


class SizeDefinitionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SizeDefinitionSerializer
    queryset = SizeDefinition.objects.select_related('size_system').all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['size_system']
    ordering = ['size_system', 'ordre']


class GarmentTypeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GarmentTypeSerializer
    queryset = GarmentType.objects.select_related('garment_type_global').all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['actiu', 'grup']
    search_fields = ['codi_client', 'nom_client']
    ordering = ['codi_client']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system:
            return Response(
                {'error': 'No es pot esborrar un tipus de sistema.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class GarmentGroupViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GarmentGroupSerializer
    queryset = GarmentGroup.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['actiu']
    search_fields = ['codi', 'nom']
    ordering = ['codi']


class POMCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = POMCategorySerializer
    queryset = POMCategory.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['actiu', 'body_area']
    search_fields = ['codi', 'nom_en', 'nom_ca']
    ordering = ['display_order', 'codi']


class GradingRuleSetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GradingRuleSetSerializer
    queryset = (
        GradingRuleSet.objects
        .select_related('garment_group', 'size_system')
        .prefetch_related('regles')
        .all()
    )
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['actiu', 'garment_group', 'size_system']
    search_fields = ['nom']
    ordering = ['nom']


class GradingRuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GradingRuleSerializer
    queryset = GradingRule.objects.select_related('rule_set', 'pom', 'talla_base').all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['rule_set', 'pom', 'logica', 'actiu']
