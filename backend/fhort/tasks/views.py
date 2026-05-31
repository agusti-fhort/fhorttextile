from django.db import connection
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Tasca, TimerEntrada
from .serializers import (
    TascaSerializer,
    TimerEntradaSerializer,
)


class TascaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TascaSerializer
    queryset = Tasca.objects.select_related('tasca_global').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['activa', 'is_active', 'tasca_global', 'fase', 'gate']
    ordering_fields = ['ordre', 'ordre_base']
    ordering = ['ordre_base', 'ordre']


class TimerEntradaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TimerEntradaSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model_task', 'actiu']
    ordering_fields = ['inici', 'fi']
    ordering = ['-inici']

    def _get_profile(self):
        # UserProfile is linked via OneToOne with related_name='profile'.
        # The 'public' schema has no UserProfile, so we return None.
        if getattr(connection, 'schema_name', None) == 'public':
            return None
        return getattr(self.request.user, 'profile', None)

    def get_queryset(self):
        qs = (
            TimerEntrada.objects
            .select_related('tecnic', 'tecnic__user', 'model_task', 'model_task__model')
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
        now = timezone.now()
        delta = now - timer.inici
        minutes = max(0, int(delta.total_seconds() // 60))
        timer.fi = now
        timer.minuts = minutes
        timer.actiu = False
        timer.save(update_fields=['fi', 'minuts', 'actiu'])
        serializer = self.get_serializer(timer)
        return Response(serializer.data, status=status.HTTP_200_OK)
