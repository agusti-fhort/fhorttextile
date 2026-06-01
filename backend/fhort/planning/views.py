"""Endpoints de configuració del calendari (Sprint A, Peça 3).
- company-calendar/ (singleton tenant) — gated `configure`.
- users/<id>/jornada/ (override per tècnic) — gated `configure` o `manage_users`.
- absencies/ (CRUD, filtrable per ?user_profile=) — gated `configure` o `manage_users`.
"""
from rest_framework import viewsets, mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status as http_status
from django_filters.rest_framework import DjangoFilterBackend

from fhort.accounts.models import UserProfile
from fhort.accounts.capabilities import (HasCapability, CONFIGURE, MANAGE_USERS,
                                         get_capabilities)
from .models import CompanyCalendar, Absencia
from .serializers import (CompanyCalendarSerializer, JornadaSerializer,
                          AbsenciaSerializer)
from . import plan_service
from fhort.tasks.models import ModelTask, PlanSnapshot


class _Configure(HasCapability):
    required_capability = CONFIGURE


class _ConfigureOrManageUsers(BasePermission):
    """Permet si l'usuari té `configure` O `manage_users`."""
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        caps = get_capabilities(user)
        return CONFIGURE in caps or MANAGE_USERS in caps


@api_view(['GET', 'PUT'])
@permission_classes([_Configure])
def company_calendar_view(request):
    """GET/PUT /api/v1/company-calendar/ — calendari d'empresa (singleton del tenant)."""
    cal = CompanyCalendar.load()   # get_or_create del singleton
    if request.method == 'GET':
        return Response(CompanyCalendarSerializer(cal).data)
    ser = CompanyCalendarSerializer(cal, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)


@api_view(['GET', 'PUT'])
@permission_classes([_ConfigureOrManageUsers])
def user_jornada_view(request, user_id):
    """GET/PUT /api/v1/users/<id>/jornada/ — override de jornada del tècnic (<id> = User id).
    PUT amb null/buit → torna a heretar la jornada de l'empresa."""
    try:
        profile = UserProfile.objects.get(user_id=user_id)
    except UserProfile.DoesNotExist:
        return Response({'error': 'Perfil no trobat en aquest tenant.'},
                        status=http_status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response({'user_id': user_id, 'jornada_override': profile.jornada_override})
    ser = JornadaSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    profile.jornada_override = ser.validated_data['jornada_override']
    profile.save(update_fields=['jornada_override'])
    return Response({'user_id': user_id, 'jornada_override': profile.jornada_override})


class AbsenciaViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                      viewsets.GenericViewSet):
    """CRUD d'absències per tècnic. Filtrable per ?user_profile=<id>."""
    queryset = Absencia.objects.select_related('user_profile').all()
    serializer_class = AbsenciaSerializer
    permission_classes = [_ConfigureOrManageUsers]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user_profile']


# ── Sprint B — motor de planificació (gated configure) ───────────────────────
@api_view(['POST'])
@permission_classes([_Configure])
def plan_compute_view(request):
    """POST /api/v1/plan/compute/ — planifica un conjunt amb el motor determinista,
    escriu planned_*/predicted_* i desa un PlanSnapshot.
    Body (tots opcionals; sense filtre = tot el pendent):
      {"model_ids":[110,111], "campaign_filter":{"temporada":"SS","any":26}}"""
    profile = getattr(request.user, 'profile', None)
    d = request.data
    try:
        out = plan_service.compute_and_save(
            model_ids=d.get('model_ids'), campaign_filter=d.get('campaign_filter'),
            computed_by=profile)
    except (ValueError, KeyError) as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    return Response(out, status=http_status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_Configure])
def plan_preview_view(request):
    """POST /api/v1/plan/preview/ — simula reposicionar una tasca SENSE desar.
    Body: {"task_id":123, "new_start":"2026-06-09T08:00:00"}.
    Retorna {moved_task_id, placements, warnings, impact}."""
    d = request.data
    if not d.get('task_id') or not d.get('new_start'):
        return Response({'error': 'task_id i new_start requerits.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    try:
        out = plan_service.preview(task_id=d['task_id'], new_start=d['new_start'])
    except ModelTask.DoesNotExist:
        return Response({'error': 'Tasca no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)
    except (ValueError, KeyError) as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    return Response(out, status=http_status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_Configure])
def plan_apply_view(request):
    """POST /api/v1/plan/apply/ — aplica una reposició acceptada: fixa la tasca
    (planned_locked=True a new_start) i desa el recàlcul de la cua (+ PlanSnapshot).
    Body: {"task_id":123, "new_start":"2026-06-09T08:00:00"}."""
    profile = getattr(request.user, 'profile', None)
    d = request.data
    if not d.get('task_id') or not d.get('new_start'):
        return Response({'error': 'task_id i new_start requerits.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    try:
        out = plan_service.apply(task_id=d['task_id'], new_start=d['new_start'],
                                 computed_by=profile)
    except ModelTask.DoesNotExist:
        return Response({'error': 'Tasca no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)
    except (ValueError, KeyError) as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    return Response(out, status=http_status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([_Configure])
def plan_snapshots_view(request):
    """GET /api/v1/plan/snapshots/ — historial de previsions (últimes 50)."""
    out = [{'id': s.id, 'computed_at': s.computed_at, 'start_date': s.start_date,
            'technician_count': s.technician_count,
            'campaign_filter': s.campaign_filter,
            'model_count': len(s.model_sequence)}
           for s in PlanSnapshot.objects.all()[:50]]
    return Response({'snapshots': out}, status=http_status.HTTP_200_OK)
