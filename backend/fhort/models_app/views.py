from django.db import connection
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import BaseMeasurement, Model, ModelFitxer
from .serializers import (
    BaseMeasurementSerializer,
    ModelDetailSerializer,
    ModelFitxerSerializer,
    ModelListSerializer,
)


class ModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estat', 'fase_actual', 'garment_type', 'responsable']
    search_fields = ['codi_intern', 'codi_client', 'nom_prenda']
    ordering_fields = ['prioritat', 'data_objectiu', 'data_entrada']
    ordering = ['-prioritat']
    queryset = Model.objects.all()

    def get_queryset(self):
        # django-tenants ja restringeix les queries a l'esquema actual del tenant
        # via la connection. Al schema 'public' no hi ha taules de models, però
        # retornem un queryset buit per evitar errors a vistes mal encaminades.
        if getattr(connection, 'schema_name', None) == 'public':
            return Model.objects.none()
        return (
            Model.objects
            .select_related('garment_type', 'garment_group',
                            'responsable', 'responsable__user',
                            'size_system', 'talla_base', 'grading_rule_set')
            .all()
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return ModelListSerializer
        return ModelDetailSerializer


class ModelFitxerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ModelFitxerSerializer
    queryset = ModelFitxer.objects.select_related('model', 'pujat_per').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'categoria', 'enviat_ia']
    ordering_fields = ['data_pujada']
    ordering = ['-data_pujada']


# Sprint S14B — BaseMeasurement CRUD
class BaseMeasurementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BaseMeasurementSerializer
    queryset = (
        BaseMeasurement.objects
        .select_related('pom', 'pom__pom_global')
        .all()
    )
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'pom', 'is_active', 'origen']
    ordering_fields = ['updated_at', 'id']
    ordering = ['model', 'id']

    def get_queryset(self):
        # Al schema 'public' no hi ha dades de tenant — retorna queryset buit.
        if getattr(connection, 'schema_name', None) == 'public':
            return BaseMeasurement.objects.none()
        return super().get_queryset()



# Sprint 1C — ModelServeiViewSet
from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend

class ModelServeiViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['model', 'servei', 'contractat', 'estat_autoritzacio']
    ordering = ['servei__ordre_popup']

    def get_queryset(self):
        from .models import ModelServei
        return ModelServei.objects.select_related('servei', 'model').all()

    def get_serializer_class(self):
        from .serializers import ModelServeiSerializer
        return ModelServeiSerializer
