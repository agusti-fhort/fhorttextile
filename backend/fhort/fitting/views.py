from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    GradingVersion,
    POMAlert,
    SizeFitting,
    FittingSession,
    PieceFitting,
    PieceFittingLine,
    FittingPhoto,
)
from .serializers import (
    GradingVersionSerializer,
    POMAlertSerializer,
    SizeFittingSerializer,
    FittingSessionListSerializer,
    FittingSessionDetailSerializer,
    FittingSessionCreateSerializer,
    FittingSessionUpdateSerializer,
    PieceFittingSummarySerializer,
    PieceFittingGridSerializer,
    PieceFittingLineSerializer,
    FittingPhotoSerializer,
)
from . import services


def _profile_id(request):
    """Resolve the current user's accounts.UserProfile id (or None)."""
    profile = getattr(request.user, 'profile', None)
    return profile.id if profile else None


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


# ═════════════════════════════════════════════════════════════════════════════
# Sprint 5B.6 — Fitting REST API. CRUD via ViewSets; operations via @action.
# The business logic lives in fitting/services.py (5B.3/5B.4); these only expose it.
# ═════════════════════════════════════════════════════════════════════════════

class FittingSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'garment_set', 'fase', 'estat']
    ordering_fields = ['data', 'created_at']
    ordering = ['-data', '-created_at']

    def get_queryset(self):
        return (
            FittingSession.objects
            .select_related('model', 'garment_set', 'responsable', 'created_by')
            .annotate(n_peces=Count('piece_fittings'))
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return FittingSessionListSerializer
        if self.action == 'create':
            return FittingSessionCreateSerializer
        if self.action in ('update', 'partial_update'):
            return FittingSessionUpdateSerializer
        return FittingSessionDetailSerializer

    def create(self, request, *args, **kwargs):
        ser = FittingSessionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            session = services.create_session(
                fase=d['fase'],
                data=d['data'],
                model_id=d.get('model'),
                garment_set_id=d.get('garment_set'),
                responsable_id=d.get('responsable'),
                model_persona=d.get('model_persona', ''),
                assistents=d.get('assistents', ''),
                lloc=d.get('lloc', ''),
                notes=d.get('notes', ''),
                created_by_id=_profile_id(request),
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        out = FittingSessionDetailSerializer(session, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='can-advance')
    def can_advance(self, request, pk=None):
        return Response({'can_advance': services.session_can_advance(int(pk))})

    @action(detail=True, methods=['post'], url_path='create-piece')
    def create_piece(self, request, pk=None):
        model_id = request.data.get('model_id')
        if not model_id:
            return Response({'error': 'model_id requerit'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pf, n = services.create_piece_fitting(
                int(pk), int(model_id), created_by_id=_profile_id(request),
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        out = PieceFittingGridSerializer(pf, context={'request': request})
        return Response({'n_linies': n, **out.data}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='advance-phase')
    def advance_phase(self, request, pk=None):
        nova_fase = request.data.get('nova_fase')
        if not nova_fase:
            return Response({'error': 'nova_fase requerit'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = services.advance_phase(
                int(pk), nova_fase, user_profile_id=_profile_id(request),
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class PieceFittingViewSet(mixins.RetrieveModelMixin,
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['session', 'model', 'gate']
    ordering = ['session', 'model']
    queryset = (
        PieceFitting.objects
        .select_related('model', 'grading_version', 'grading_version__size_fitting', 'gate_per')
    )

    def get_serializer_class(self):
        if self.action == 'list':
            return PieceFittingSummarySerializer
        return PieceFittingGridSerializer

    @action(detail=True, methods=['post'], url_path='set-gate')
    def set_gate(self, request, pk=None):
        resultat = request.data.get('resultat')
        motiu = request.data.get('motiu', '')
        try:
            pf = services.set_piece_gate(
                int(pk), resultat, motiu, user_profile_id=_profile_id(request),
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'id': pf.pk, 'gate': pf.gate, 'gate_motiu': pf.gate_motiu, 'gate_at': pf.gate_at,
        })

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        try:
            result = services.close_piece_fitting(int(pk), user_profile_id=_profile_id(request))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class PieceFittingLineViewSet(mixins.UpdateModelMixin,
                              mixins.RetrieveModelMixin,
                              viewsets.GenericViewSet):
    """Autosave only: PATCH a cell's valor_real / nota. No list/create/destroy/PUT."""
    permission_classes = [IsAuthenticated]
    serializer_class = PieceFittingLineSerializer
    queryset = PieceFittingLine.objects.select_related('pom').all()
    http_method_names = ['get', 'patch', 'head', 'options']


class FittingPhotoViewSet(mixins.ListModelMixin,
                          mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FittingPhotoSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['session', 'piece_fitting']
    ordering = ['session', 'id']
    queryset = FittingPhoto.objects.select_related('session', 'piece_fitting').all()
