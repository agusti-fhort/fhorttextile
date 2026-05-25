from django.db import connection
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ModelTasca, TascaCataleg, TimerEntrada
from .serializers import (
    ModelTascaSerializer,
    TascaCatalegSerializer,
    TimerEntradaSerializer,
)


class TascaCatalegViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TascaCatalegSerializer
    queryset = TascaCataleg.objects.select_related('tasca_global').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['activa', 'tasca_global']
    ordering_fields = ['ordre']
    ordering = ['ordre']


class ModelTascaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ModelTascaSerializer
    queryset = (
        ModelTasca.objects
        .select_related(
            'model',
            'tasca',
            'tasca__tasca_global',
            'responsable',
            'responsable__user',
            'gate_revisat_per',
        )
        .all()
    )
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'estat', 'responsable']
    ordering_fields = ['ordre', 'data_limit']
    ordering = ['model', 'ordre']


class TimerEntradaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TimerEntradaSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model_tasca', 'actiu']
    ordering_fields = ['inici', 'fi']
    ordering = ['-inici']

    def _get_profile(self):
        # El UserProfile s'enllaça via OneToOne amb related_name='profile'.
        # Al schema 'public' no hi ha UserProfile, així que retornem None.
        if getattr(connection, 'schema_name', None) == 'public':
            return None
        return getattr(self.request.user, 'profile', None)

    def get_queryset(self):
        qs = (
            TimerEntrada.objects
            .select_related('tecnic', 'tecnic__user', 'model_tasca', 'model_tasca__model')
        )
        profile = self._get_profile()
        if profile is None:
            return qs.none()
        return qs.filter(tecnic=profile)

    def perform_create(self, serializer):
        profile = self._get_profile()
        if profile is None:
            raise PermissionDenied('Usuari sense UserProfile en aquest tenant.')
        serializer.save(tecnic=profile)

    @action(detail=True, methods=['post'], url_path='tancar')
    def tancar(self, request, pk=None):
        timer = self.get_object()
        if timer.fi is not None:
            raise ValidationError('El timer ja està tancat.')
        ara = timezone.now()
        delta = ara - timer.inici
        minuts = max(0, int(delta.total_seconds() // 60))
        timer.fi = ara
        timer.minuts = minuts
        timer.actiu = False
        timer.save(update_fields=['fi', 'minuts', 'actiu'])
        serializer = self.get_serializer(timer)
        return Response(serializer.data, status=status.HTTP_200_OK)
