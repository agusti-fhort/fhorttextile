from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated

from .models import (
    GradingVersion,
    POMAlert,
    SizeFitting,
)
from .serializers import (
    GradingVersionSerializer,
    POMAlertSerializer,
    SizeFittingSerializer,
)


class SizeFittingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SizeFittingSerializer
    queryset = (
        SizeFitting.objects
        .select_related('model', 'sf_pare', 'creat_per')
        .all()
    )
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'tipus', 'estat']
    ordering_fields = ['data_creacio', 'numero']
    ordering = ['model', 'numero']


class GradingVersionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GradingVersionSerializer
    queryset = GradingVersion.objects.select_related('size_fitting', 'creat_per').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['size_fitting', 'aprovada']
    ordering = ['-data']


class POMAlertViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = POMAlertSerializer
    queryset = (
        POMAlert.objects
        .select_related('model', 'size_fitting', 'pom', 'resolt_per')
        .all()
    )
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['estat', 'tipus', 'model', 'pom']
    ordering_fields = ['data_creacio', 'data_resolucio']
    ordering = ['-data_creacio']
