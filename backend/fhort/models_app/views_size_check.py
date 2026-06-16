"""SC-1 — Size Check viewsets (mirall de PieceFittingViewSet).

SizeCheckViewSet: retrieve (graella) + list (històric) + open + resolve.
SizeCheckLineViewSet: PATCH autosave d'una cel·la (valor_real / acceptat / nota).
"""
from django.db import connection
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from . import services_size_check as sc_services
from .models import SizeCheck, SizeCheckLine
from .serializers_size_check import (
    SizeCheckGridSerializer,
    SizeCheckLineSerializer,
    SizeCheckSummarySerializer,
)


def _profile_id(request):
    """Resol l'id de l'accounts.UserProfile de l'usuari actual (o None)."""
    profile = getattr(request.user, 'profile', None)
    return profile.id if profile else None


class SizeCheckViewSet(mixins.RetrieveModelMixin,
                       mixins.ListModelMixin,
                       viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'estat']
    ordering = ['model', '-created_at']
    queryset = SizeCheck.objects.select_related('model', 'resolt_per')

    def get_queryset(self):
        if getattr(connection, 'schema_name', None) == 'public':
            return SizeCheck.objects.none()
        return self.queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return SizeCheckSummarySerializer
        return SizeCheckGridSerializer

    @action(detail=False, methods=['post'])
    def open(self, request):
        """POST /size-checks/open/ {model_id} — obre o reutilitza el check Pendent del model."""
        model_id = request.data.get('model_id')
        if not model_id:
            return Response({'error': 'model_id és obligatori'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            sc, _n = sc_services.open_size_check(
                int(model_id), created_by_id=_profile_id(request),
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SizeCheckGridSerializer(sc).data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """POST /size-checks/<pk>/resolve/ {estat, missatge_fabricant} — resol el check."""
        estat = request.data.get('estat')
        missatge = request.data.get('missatge_fabricant', '')
        try:
            result = sc_services.resolve_size_check(
                int(pk), estat, missatge, user_profile_id=_profile_id(request),
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class SizeCheckLineViewSet(mixins.UpdateModelMixin,
                           viewsets.GenericViewSet):
    """PATCH /size-check-lines/<pk>/ — autosave d'una cel·la."""
    permission_classes = [IsAuthenticated]
    serializer_class = SizeCheckLineSerializer
    queryset = SizeCheckLine.objects.all()

    def get_queryset(self):
        if getattr(connection, 'schema_name', None) == 'public':
            return SizeCheckLine.objects.none()
        return self.queryset
