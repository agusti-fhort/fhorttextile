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
