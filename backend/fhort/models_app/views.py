from django.db import connection
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Model, ModelFitxer
from .serializers import (
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
            .select_related('garment_type', 'responsable', 'responsable__user',
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
