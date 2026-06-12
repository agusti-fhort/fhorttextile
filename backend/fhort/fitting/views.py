import logging

from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action, api_view, permission_classes
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
            .prefetch_related('attendees__user')   # attendees_info (list) — evita N+1
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
        force = bool(d.get('force'))
        try:
            s = services.schedule_session(
                fase=d.get('fase'), data=d.get('data'),
                responsable_id=d.get('responsable_id'),
                model_id=d.get('model_id'), garment_set_id=d.get('garment_set_id'),
                lloc=d.get('lloc', ''),
                start_time=start_time, end_time=d.get('end_time'),
                duracio_minuts=duracio_minuts, attendee_ids=attendee_ids,
                created_by_id=_profile_id(request), force=force)
        except services.SessionOverlapError as e:
            # Conflicte DUR: franja encavalcada amb sessió viva → 409, no es crea.
            return Response({'error': str(e), 'conflicts': e.conflicts},
                            status=status.HTTP_409_CONFLICT)
        except services.SessionSoftConflict as e:
            # Conflicte SUAU: mateixa fase, franja diferent → 200, requereix confirmació.
            return Response({'warning': str(e), 'requires_confirmation': True,
                             'sessions': e.sessions}, status=status.HTTP_200_OK)
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

    @action(detail=False, methods=['post'], url_path='schedule-bulk',
            permission_classes=[_ScheduleFittingsPerm])
    def schedule_bulk_action(self, request):
        """POST /api/v1/fitting-sessions/schedule-bulk/ — programa N fittings ENCADENATS
        amb un `convocatoria` UUID compartit (sessió i+1 comença on acaba la i, calendari
        d'empresa pur). Body: {fase, data, start_time?, model_ids:[...], duracio_minuts?,
        attendee_ids?, responsable_id?, lloc?}."""
        import datetime as _dt
        d = request.data
        model_ids = d.get('model_ids', [])
        if not model_ids:
            return Response({'error': 'model_ids requerit'}, status=status.HTTP_400_BAD_REQUEST)
        fase = d.get('fase')
        data_str = d.get('data')
        if not fase or not data_str:
            return Response({'error': 'fase i data requerits'}, status=status.HTTP_400_BAD_REQUEST)
        data = _dt.date.fromisoformat(data_str)
        start_time_str = d.get('start_time')
        start_time = _dt.time.fromisoformat(start_time_str) if start_time_str else None
        duracio_minuts = int(d['duracio_minuts']) if d.get('duracio_minuts') else None
        attendee_ids = d.get('attendee_ids', [])
        responsable_id = d.get('responsable_id')
        lloc = d.get('lloc', '')
        try:
            sessions, convocatoria, skipped, warnings = services.schedule_bulk(
                fase=fase, data=data, start_time=start_time,
                model_ids=model_ids, duracio_minuts=duracio_minuts,
                attendee_ids=attendee_ids, responsable_id=responsable_id,
                lloc=lloc, created_by_id=_profile_id(request),
            )
        except Exception as e:
            logger.exception('schedule_bulk error')
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'convocatoria': str(convocatoria) if convocatoria else None,
            'n_sessions': len(sessions),
            'created': [{'id': s.id, 'model_id': s.model_id,
                         'start_time': str(s.start_time),
                         'data': str(s.data),
                         'duracio_minuts': s.duracio_minuts}
                        for s in sessions],
            'skipped': skipped,
            'warnings': warnings,
        }, status=status.HTTP_201_CREATED)

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

    def get_permissions(self):
        # Mutacions de cicle de vida → requereixen capability schedule_fittings.
        if self.action in ('destroy', 'discard', 'seal'):
            return [_ScheduleFittingsPerm()]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        """(Peça 2 · Op 2) DELETE /fitting-sessions/<id>/ — esborra físicament si
        Programada i sense peces; 409 si Oberta/amb peces (cal /discard/); 400 si
        Tancada/Anullada."""
        session = self.get_object()
        try:
            services._delete_session_if_allowed(session)
        except services.SessionActionConflict as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='discard')
    def discard(self, request, pk=None):
        """(Peça 2 · Op 3) Anul·la la sessió (Programada/Oberta → Anullada + motiu)."""
        try:
            s = services.discard_session(int(pk), motiu=request.data.get('motiu', ''))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'id': s.id, 'estat': s.estat,
                         'motiu_anullacio': s.motiu_anullacio,
                         'finished_at': s.finished_at})

    @action(detail=True, methods=['post'], url_path='seal')
    def seal(self, request, pk=None):
        """(Peça 2 · Op 7) Segellat independent → Tancada + finished_at. No toca fase."""
        try:
            s = services.seal_session(int(pk))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'id': s.id, 'estat': s.estat, 'finished_at': s.finished_at})


# ── Peça 2 — endpoints de GRUP (per convocatoria UUID) ───────────────────────
@api_view(['PATCH'])
@permission_classes([_ScheduleFittingsPerm])
def group_reschedule(request, conv_uuid):
    """(Op 1) PATCH /fitting-sessions/group/<uuid>/reschedule/ — Body {data, start_time?}."""
    import datetime as _dt
    data_str = request.data.get('data')
    if not data_str:
        return Response({'error': 'data requerit'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        data = _dt.date.fromisoformat(data_str)
        st_raw = request.data.get('start_time')
        start_time = _dt.time.fromisoformat(st_raw) if st_raw else None
    except ValueError as e:
        return Response({'error': f'format invàlid: {e}'}, status=status.HTTP_400_BAD_REQUEST)
    updated = services.reschedule_group(conv_uuid, data, start_time)
    return Response({'updated': updated})


@api_view(['POST'])
@permission_classes([_ScheduleFittingsPerm])
def group_add_model(request, conv_uuid):
    """(Op 4) POST /fitting-sessions/group/<uuid>/add-model/ — Body {model_id, fase?, force?}."""
    model_id = request.data.get('model_id')
    if not model_id:
        return Response({'error': 'model_id requerit'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        s = services.add_model_to_group(
            conv_uuid, int(model_id), fase=request.data.get('fase'),
            created_by_id=_profile_id(request), force=bool(request.data.get('force')))
    except services.SessionActionConflict as e:
        return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
    except services.SessionOverlapError as e:
        return Response({'error': str(e), 'conflicts': e.conflicts},
                        status=status.HTTP_409_CONFLICT)
    except services.SessionSoftConflict as e:
        return Response({'warning': str(e), 'requires_confirmation': True,
                         'sessions': e.sessions}, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(FittingSessionDetailSerializer(s, context={'request': request}).data,
                    status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([_ScheduleFittingsPerm])
def group_remove_model(request, conv_uuid, model_id):
    """(Op 5) DELETE /fitting-sessions/group/<uuid>/remove-model/<int:model_id>/."""
    try:
        removed = services.remove_model_from_group(conv_uuid, int(model_id))
    except services.SessionActionConflict as e:
        return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'removed': removed})


@api_view(['PATCH'])
@permission_classes([_ScheduleFittingsPerm])
def group_attendees(request, conv_uuid):
    """(Op 6) PATCH /fitting-sessions/group/<uuid>/attendees/ — Body {attendee_ids:[...]}."""
    updated = services.set_group_attendees(conv_uuid, request.data.get('attendee_ids', []))
    return Response({'updated': updated})


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
