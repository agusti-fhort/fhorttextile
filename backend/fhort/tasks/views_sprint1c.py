# Sprint 1C — ViewSets Tasca, PaquetServei
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Tasca, PaquetServei, PaquetServeiTasca
from .serializers_sprint1c import (
    TascaSerializer, PaquetServeiSerializer, PaquetServeiListSerializer,
)


class TascaViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TascaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fase', 'tipus_tasca', 'gate', 'facturable', 'is_active']
    search_fields = ['nom_tasca']
    ordering_fields = ['ordre_base', 'fase']
    ordering = ['ordre_base']

    def get_queryset(self):
        return Tasca.objects.filter(is_active=True)


class PaquetServeiViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['grup', 'actiu']
    search_fields = ['nom']
    ordering = ['ordre_popup', 'nom']

    def get_serializer_class(self):
        if self.action == 'list':
            return PaquetServeiListSerializer
        return PaquetServeiSerializer

    def get_queryset(self):
        return PaquetServei.objects.prefetch_related(
            'tasques', 'tasques__tasca'
        ).filter(actiu=True)
