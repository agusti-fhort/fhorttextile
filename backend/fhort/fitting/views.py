from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated

from .models import (
    FitComment,
    Fitting,
    FittingLine,
    GradedSpecLine,
    GradingVersion,
    POMAlert,
    SizeFitting,
)
from .serializers import (
    FitCommentSerializer,
    FittingLineSerializer,
    FittingSerializer,
    GradedSpecLineSerializer,
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


class GradedSpecLineViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GradedSpecLineSerializer
    queryset = GradedSpecLine.objects.select_related('grading_version', 'pom', 'talla').all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['grading_version', 'pom', 'estat']


class FittingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FittingSerializer
    queryset = (
        Fitting.objects
        .select_related('size_fitting', 'responsable')
        .prefetch_related('linies', 'comentaris')
        .all()
    )
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['size_fitting', 'tipus', 'estat']
    ordering_fields = ['data_fitting', 'numero']
    ordering = ['size_fitting', 'numero']


class FittingLineViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FittingLineSerializer
    queryset = FittingLine.objects.select_related('fitting', 'pom', 'talla').all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['fitting', 'pom', 'estat']


class FitCommentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FitCommentSerializer
    queryset = FitComment.objects.select_related('fitting', 'resolt_en').all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['fitting', 'estat', 'tipus']


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
