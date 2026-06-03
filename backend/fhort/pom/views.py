from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from fhort.accounts.capabilities import HasCapability, CONFIGURE

from .models import (
    GarmentGroup,
    GarmentPOMMap,
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
    GarmentPOMMapSerializer,
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
    queryset = POMMaster.objects.select_related(
        'pom_global', 'pom_global__body_measure_iso', 'categoria').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['actiu', 'pom_global']
    search_fields = ['codi_client', 'nom_client']
    ordering_fields = ['codi_client', 'nom_client']
    ordering = ['codi_client']


class SizeSystemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SizeSystemSerializer
    queryset = SizeSystem.objects.prefetch_related('talles').all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['actiu']
    search_fields = ['codi', 'nom']
    ordering = ['codi']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.talles.exists():
            return Response(
                {'error': 'Elimina primer les talles associades'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class SizeDefinitionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SizeDefinitionSerializer
    queryset = SizeDefinition.objects.select_related('size_system').all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['size_system']
    ordering = ['size_system', 'ordre']


class GarmentTypeViewSet(viewsets.ModelViewSet):
    serializer_class = GarmentTypeSerializer
    queryset = GarmentType.objects.select_related('garment_type_global').all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['actiu', 'grup']
    search_fields = ['codi_client', 'nom_client']
    ordering = ['codi_client']

    def get_permissions(self):
        # Lectura: autenticat. Escriptura: configure (alineat amb GarmentTypeItem/TaskTimeEstimate).
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        perm = HasCapability(); self.required_capability = CONFIGURE
        return [perm]

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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system_default:
            return Response(
                {'error': 'No es pot esborrar un RuleSet de sistema.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class GradingRuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GradingRuleSerializer
    queryset = GradingRule.objects.select_related(
        'pom__pom_global', 'talla_base', 'rule_set'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['rule_set', 'actiu', 'logica']
    search_fields = ['pom__codi_client', 'pom__nom_client']
    ordering = ['rule_set', 'pom__codi_client']

    def destroy(self, request, *args, **kwargs):
        """We do not delete physically — we mark as inactive."""
        instance = self.get_object()
        instance.actiu = False
        instance.save(update_fields=['actiu'])
        return Response(
            {'status': 'inactiu', 'id': instance.id},
            status=status.HTTP_200_OK
        )

    def perform_update(self, serializer):
        # Protect rules of system RuleSets: clone before modifying.
        instance = serializer.instance
        if instance.rule_set.is_system_default:
            raise PermissionDenied(
                'Les regles de RuleSets de sistema no es poden modificar. '
                'Clona el RuleSet primer.'
            )
        serializer.save()


class GarmentPOMMapViewSet(viewsets.ModelViewSet):
    serializer_class = GarmentPOMMapSerializer
    queryset = (
        GarmentPOMMap.objects
        .select_related('garment_type_item', 'garment_type_item__garment_type',
                        'pom', 'pom__pom_global', 'pom__pom_global__body_measure_iso',
                        'pom__categoria')
        .all()
    )

    def get_permissions(self):
        # Lectura: autenticat. Escriptura: configure (alineat amb GarmentType/GarmentTypeItem).
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        perm = HasCapability(); self.required_capability = CONFIGURE
        return [perm]

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    # Migration família → item COMPLETADA (PAS 6): la pertinença viu només a garment_type_item.
    # El filtre legacy `?garment_type=` s'ha retirat amb el drop del camp (migració 0016).
    filterset_fields = {
        'garment_type_item': ['exact'],
        'pom': ['exact'],
        'is_key': ['exact'],
        'obligatori': ['exact'],
        'pendent_revisio': ['exact'],
    }
    ordering_fields = ['ordre', 'id', 'garment_type_item']
    ordering = ['garment_type_item', 'ordre']
