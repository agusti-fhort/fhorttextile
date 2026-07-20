import logging

from django.db import IntegrityError
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.accounts.capabilities import HasCapability, CLOSE_GATES

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

# Guard d'escriptura sobre fitting segellat (Tancada/Anullada). Missatge i codi IDÈNTICS
# als dos punts (propagar + partial_update) perquè el front els distingeixi amb una sola
# comprovació. Vegeu services.fitting_line_is_locked.
SEALED_SESSION_DETAIL = 'Sessió de fitting tancada; no es pot modificar.'


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


class _CloseGates(HasCapability):
    required_capability = CLOSE_GATES


class GradingVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """Versions de grading: NOMÉS LECTURA + l'acció d'aprovar (G6-B/T2).

    Era un `ModelViewSet` complet amb `fields = '__all__'` i `IsAuthenticated`: **qualsevol
    usuari autenticat podia fer `PATCH {"aprovada": false}` sobre una versió segellada, o
    `DELETE`-la sencera.** Sense capability, sense guard, sense rastre. El segell era una casella
    editable per REST — i alhora la cosa en què confia el motor de patrons per projectar.

    Ara: `PATCH`/`PUT`/`DELETE`/`POST` → **405**. L'única escriptura és `POST .../approve/`, que
    demana `CLOSE_GATES` (aprovar és un gate, i els gates són decisió humana i gated) i passa pel
    servei de segell únic, que escriu els tres camps junts.

    **Des-aprovar NO existeix per API.** Una versió aprovada se supera creant-ne una de nova (el
    bump de `generar-grading`), que deixa rastre; no desdient-se del segell en silenci.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = GradingVersionSerializer
    queryset = GradingVersion.objects.select_related('size_fitting', 'creat_per').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['size_fitting', 'aprovada']
    ordering = ['-data']

    @action(detail=True, methods=['post'], permission_classes=[_CloseGates])
    def approve(self, request, pk=None):
        """POST /api/v1/grading-versions/<pk>/approve/ — segella la versió (capability CLOSE_GATES)."""
        from fhort.fitting.services import seal_grading_version

        version = self.get_object()

        # Només la versió VIGENT es pot segellar: aprovar una versió ja superada seria aprovar
        # unes talles que ningú no serveix (i deixaria dues aprovades al mateix SizeFitting, que
        # cap constraint no impedeix — v. R7 de la diagnosi).
        if not version.is_active:
            return Response({
                'error': 'not_active',
                'message': (f'La versió v{version.version_number} no és la vigent: només es pot '
                            f'aprovar la versió activa del SizeFitting.'),
            }, status=status.HTTP_409_CONFLICT)

        ja_estava = version.aprovada
        profile = getattr(request.user, 'profile', None)
        seal_grading_version(version, user_profile_id=(profile.id if profile else None))
        version.refresh_from_db()

        return Response({
            'ok': True,
            'ja_estava_aprovada': ja_estava,   # idempotent: no es reescriu qui la va aprovar
            **GradingVersionSerializer(version).data,
        }, status=status.HTTP_200_OK)


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
    # P4 — `convocatoria` (UUID, db_index) permet demanar les sessions d'una fulla amb
    # ?convocatoria=<uuid>. Fins ara el client baixava la llista sencera i la particionava.
    filterset_fields = ['model', 'garment_set', 'fase', 'estat', 'data', 'responsable',
                        'convocatoria']
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
        # C4 — alta lliure de fitting (POST /fitting-sessions/) JUBILADA amb create_session.
        # L'alta va per schedule/ (programat) o schedule-now/ ("aquí i ara"). Cap consumidor.
        from rest_framework.exceptions import MethodNotAllowed
        raise MethodNotAllowed(
            'POST', detail="Alta de fitting retirada: usa /schedule/ o /schedule-now/.")

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
        except IntegrityError:
            # XD — la peça (session, model) ja existeix: unique_together de PieceFitting.
            # No es fa get_or_create (la semàntica del servei —materialitzar línies— queda
            # intacta): es torna 409 llegible perquè el cridador programàtic del Sprint Y
            # sigui idempotent. Substitueix el 500 cru que deixava el `create` nu.
            return Response(
                {'error': 'Aquesta peça ja existeix a la sessió.', 'code': 'piece_exists'},
                status=status.HTTP_409_CONFLICT,
            )
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

    @action(detail=False, methods=['post'], url_path='schedule-now',
            permission_classes=[_ScheduleFittingsPerm])
    def schedule_now(self, request):
        """POST /api/v1/fitting-sessions/schedule-now/ — "Fitting AQUÍ I ARA" (C4, deute S15).
        UN CLIC, cap formulari: programa un fitting del model ARA mateix amb tot el camí normal
        de schedule_session (estat Programada, guard solapament, recompute, calendari).
        Defaults server-side: data=avui, start_time=ara, responsable=attendee=actor de la
        request, durada 10×N. Body: {model_id, fase?(→ fase_actual del model), force?}."""
        from django.utils import timezone
        from fhort.models_app.models import Model
        model_id = request.data.get('model_id')
        if not model_id:
            return Response({'error': 'model_id requerit.'}, status=status.HTTP_400_BAD_REQUEST)
        model = Model.objects.filter(pk=model_id).first()
        if model is None:
            return Response({'error': 'Model no trobat.'}, status=status.HTTP_404_NOT_FOUND)
        actor_id = _profile_id(request)
        now = timezone.localtime()
        try:
            s = services.schedule_session(
                fase=request.data.get('fase') or model.fase_actual,
                data=now.date(), responsable_id=actor_id, model_id=int(model_id),
                start_time=now.time().replace(microsecond=0),
                attendee_ids=[actor_id] if actor_id else [],
                created_by_id=actor_id, force=bool(request.data.get('force')))
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


@api_view(['DELETE'])
@permission_classes([_ScheduleFittingsPerm])
def group_remove(request, conv_uuid):
    """(Ajust 1) DELETE /fitting-sessions/group/<uuid>/ — elimina la convocatòria en bloc.
    409 (atòmic, no esborra res) si hi ha sessions Obertes o amb peces."""
    try:
        res = services.delete_group(conv_uuid)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    if not res['ok']:
        return Response({
            'detail': "No es pot eliminar: hi ha sessions ja obertes o amb peces.",
            'conflicts': res['conflicts'],
        }, status=status.HTTP_409_CONFLICT)
    return Response(status=status.HTTP_204_NO_CONTENT)


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
        # XB: reobertura explícita d'un grading segellat (aprovada). Default False →
        # comportament actual intacte. La UI que activa el flag pertany al Sprint Y
        # (ancorada a la tasca); aquí només s'exposa el contracte.
        allow_reopen = bool(request.data.get('allow_reopen_sealed', False))
        try:
            result = services.close_piece_fitting(
                int(pk), user_profile_id=_profile_id(request),
                allow_reopen_sealed=allow_reopen,
            )
        except ValueError as e:
            # El guard D-1 (motor, intocable) llança ValueError nu quan la GradingVersion
            # activa està aprovada. El codi de client s'afegeix AQUÍ, a la view, no al motor:
            # 'grading_sealed' permet al client oferir la reobertura sense parsejar el text.
            body = {'error': str(e)}
            if 'segellada a producció' in str(e):
                body['code'] = 'grading_sealed'
            return Response(body, status=status.HTTP_400_BAD_REQUEST)
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
    # select_related fins a la sessió i al model: els dos guards (estat i eix) els consulten
    # sense queries extra a partial_update/propagar.
    queryset = PieceFittingLine.objects.select_related(
        'pom', 'piece_fitting__session', 'piece_fitting__model').all()
    http_method_names = ['get', 'patch', 'post', 'head', 'options']

    def _rebuig_escriptura(self, line):
        """Guards d'escriptura, compartits per `partial_update` i `propagar`. Retorna una
        Response de rebuig, o None si la línia és editable.

        Ordre deliberat: primer l'estat de la sessió (una sessió segellada no s'edita ni tan
        sols a la base), després l'eix (P1).
        """
        if services.fitting_line_is_locked(line):
            return Response({'detail': SEALED_SESSION_DETAIL}, status=status.HTTP_409_CONFLICT)
        if services.fitting_line_is_non_base(line):
            # 400, no 409: no és conflicte d'estat sinó escriptura fora de l'eix del fitting.
            return Response({'detail': services.NON_BASE_LINE_DETAIL},
                            status=status.HTTP_400_BAD_REQUEST)
        return None

    def partial_update(self, request, *args, **kwargs):
        # Guards ABANS de desar; delega només si la línia és editable.
        rebuig = self._rebuig_escriptura(self.get_object())
        if rebuig is not None:
            return rebuig
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='propagar')
    def propagar(self, request, pk=None):
        """Ancoratge en temps d'edició. Desa el valor_real de la cel·la editada i, si el
        règim és LINEAR/canònic, propaga el delta a les germanes del mateix POM (escrivint
        el seu valor_real). `valor_teoric` NO es toca mai. Retorna les línies del POM.

        STEP/FIXED/ZERO/EXCEPTION o sense regla → només desa la cel·la (germanes intactes).
        Permís = el del viewset (IsAuthenticated), igual que l'autosave."""
        from django.db import transaction
        from fhort.pom.services import _load_grading_rules
        from fhort.pom.grading_utils import propaga_ancoratges

        line = self.get_object()
        pf = line.piece_fitting

        # Guards (sessió segellada · eix no-base) abans de qualsevol save. L'ancoratge només
        # es pot fer des de la talla BASE; la propagació a les germanes, en canvi, es manté:
        # els seus valor_real són DERIVATS del motor, no feina del tècnic (P1).
        rebuig = self._rebuig_escriptura(line)
        if rebuig is not None:
            return rebuig

        def _resp(propagat, motiu, warnings=None):
            linies = (PieceFittingLine.objects
                      .filter(piece_fitting=pf, pom=line.pom)
                      .select_related('pom').order_by('size_label'))
            return Response({
                'propagat': propagat,
                'motiu': motiu,
                'warnings': warnings or [],
                'linies': PieceFittingLineSerializer(linies, many=True).data,
            })

        # 1-2. Desa SEMPRE la cel·la ancorada (valor_real | null).
        raw = request.data.get('valor_real', None)
        anchor_val = None if raw in (None, '') else float(raw)
        line.valor_real = anchor_val
        line.save(update_fields=['valor_real'])
        if anchor_val is None:                       # treure ancoratge → no propaga
            return _resp(False, 'sense_ancoratge')

        # 3. Regla resident → fallback (cadena de _load_grading_rules).
        rule = _load_grading_rules(pf.model).get(line.pom_id)
        if rule is None:
            return _resp(False, 'sense_regla')

        # 4. Propaga NOMÉS si LINEAR o canònic. PG-4b-3a: STEP MAI propaga, encara que
        # increment_base estigui poblat (logica és la veritat del règim).
        logica = getattr(rule, 'logica', None)
        canonic = getattr(rule, 'increment_base', None) is not None
        propaga = (logica != 'STEP') and (canonic or logica == 'LINEAR')
        if not propaga:
            return _resp(False, logica or 'desconegut')

        # 5. Propaga el delta des de l'ancoratge → valor_real de les germanes (valor_teoric intacte).
        size_run = [s.strip() for s in (pf.model.size_run_model or '')
                    .replace(';', '·').split('·') if s.strip()]
        warnings = []
        teorics = propaga_ancoratges(rule, line.size_label, anchor_val, size_run, warnings=warnings)
        with transaction.atomic():
            for sl, val in teorics.items():
                if val is None:
                    continue
                (PieceFittingLine.objects
                 .filter(piece_fitting=pf, pom=line.pom, size_label=sl)
                 .update(valor_real=val))
        return _resp(True, logica or 'CANONIC', warnings)


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
