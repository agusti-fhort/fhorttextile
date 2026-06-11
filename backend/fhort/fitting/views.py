import logging

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
from fhort.accounts.capabilities import HasCapability, SCHEDULE_FITTINGS

logger = logging.getLogger(__name__)


class _ScheduleFittingsPerm(HasCapability):
    required_capability = SCHEDULE_FITTINGS


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
    filterset_fields = ['model', 'garment_set', 'fase', 'estat', 'data', 'responsable']
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

    @action(detail=False, methods=['post'], url_path='schedule',
            permission_classes=[_ScheduleFittingsPerm])
    def schedule(self, request):
        """POST /api/v1/fitting-sessions/schedule/ — programa un fitting (estat Programada).
        Body: {"fase","data","responsable_id","model_id" XOR "garment_set_id","lloc",
               "start_time","end_time"}"""
        d = request.data
        import datetime as _dt
        start_time_raw = d.get('start_time')
        start_time = _dt.time.fromisoformat(start_time_raw) if start_time_raw else None
        duracio_minuts_raw = d.get('duracio_minuts')
        duracio_minuts = int(duracio_minuts_raw) if duracio_minuts_raw else None
        attendee_ids = d.get('attendee_ids', [])
        try:
            s = services.schedule_session(
                fase=d.get('fase'), data=d.get('data'),
                responsable_id=d.get('responsable_id'),
                model_id=d.get('model_id'), garment_set_id=d.get('garment_set_id'),
                lloc=d.get('lloc', ''),
                start_time=start_time, end_time=d.get('end_time'),
                duracio_minuts=duracio_minuts, attendee_ids=attendee_ids)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # Via adaptativa: si s'informa expected_at i no hi ha Delivered per a (model, fase),
        # actualitza/crea la Production perquè el calendari reflecteixi la recepció esperada.
        # Mai re-raise: el fitting ja existeix; un error aquí només es registra (warning).
        model_id = d.get('model_id')
        fase = d.get('fase')
        expected_at = d.get('expected_at')
        if model_id and expected_at:
            from fhort.tasks.models import Production
            try:
                prod = (Production.objects
                        .filter(model_id=model_id, phase=fase)
                        .exclude(status='Delivered').first())
                if prod:
                    prod.expected_at = expected_at
                    prod.save(update_fields=['expected_at'])
                elif not Production.objects.filter(
                        model_id=model_id, phase=fase, status='Delivered').exists():
                    # DEUTE: Production.supplier és obligatori (PROTECT, no nullable).
                    # Aquest create() fallarà si no es passa supplier → el try/except
                    # ho captura com a warning i el fitting es crea igualment.
                    # Cas cobert: actualitzar Productions existents (prod.expected_at).
                    # Cas no cobert: crear Production nova sense supplier previ.
                    # Solució futura: demanar supplier al modal o fer-lo nullable (migració).
                    Production.objects.create(
                        model_id=model_id, phase=fase, status='Requested',
                        expected_at=expected_at,
                        requested_by=getattr(request.user, 'profile', None))
            except Exception:
                logger.warning(
                    "schedule: via adaptativa Production fallida (model_id=%s, fase=%s)",
                    model_id, fase, exc_info=True)
        return Response(FittingSessionDetailSerializer(s, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='open',
            permission_classes=[_ScheduleFittingsPerm])
    def open(self, request, pk=None):
        """POST /api/v1/fitting-sessions/<pk>/open/ — Programada→Oberta (el dia del fitting)."""
        try:
            s = services.open_session(int(pk))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FittingSessionDetailSerializer(s, context={'request': request}).data,
                        status=status.HTTP_200_OK)


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

    @action(detail=True, methods=['post'])
    def discard(self, request, pk=None):
        """Revert valor_real := valor_teoric for all lines (pure measurement revert)."""
        result = services.discard_piece_fitting(int(pk))
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
