import django_filters
from django.contrib.auth import get_user_model
from django.db import connection
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import UserProfile
from .capabilities import HasCapability, MANAGE_USERS, get_capabilities
from .serializers import MeSerializer, UserListSerializer, UserAdminSerializer


User = get_user_model()


class UserFilter(django_filters.FilterSet):
    """Filtres de la matriu d'usuaris: ?role=<rol_nom> i ?can_task=<TaskType.code>."""
    role = django_filters.CharFilter(field_name='profile__rol_nom')
    can_task = django_filters.CharFilter(method='filter_can_task')

    class Meta:
        model = User
        fields = []

    def filter_can_task(self, queryset, name, value):
        # Containment Postgres: usuaris amb `value` dins permisos["tasks"].
        return queryset.filter(profile__permisos__tasks__contains=[value])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """GET /api/v1/me/ — profile of the authenticated user in the current tenant."""
    return Response(MeSerializer(request.user).data)


class UserViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    """GET /api/v1/users/ — list/retrieve d'usuaris actius del tenant (selector + matriu).
    PATCH /api/v1/users/<id>/ — gestió admin (rol/actiu/permisos), gated `manage_users`.

    Filtra per UserProfile.actiu=True. A l'schema 'public' torna buit (els perfils del
    tenant no hi viuen). El serializer s'escull per capacitat: la matriu (manage_users) rep
    el serializer admin amb permisos/capabilities; el selector rep el mínim.
    """

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'first_name', 'last_name']
    ordering = ['username']

    def get_permissions(self):
        # Lectura: qualsevol autenticat (selector de responsable). Escriptura: manage_users.
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        perm = HasCapability(); self.required_capability = MANAGE_USERS
        return [perm]

    def get_serializer_class(self):
        # Escriptura sempre amb el serializer admin. En lectura, els qui poden gestionar
        # usuaris reben la vista completa (matriu); la resta, el selector mínim.
        if self.action in ('update', 'partial_update'):
            return UserAdminSerializer
        if MANAGE_USERS in get_capabilities(self.request.user):
            return UserAdminSerializer
        return UserListSerializer

    def get_queryset(self):
        if getattr(connection, 'schema_name', None) == 'public':
            return User.objects.none()
        active_user_ids = UserProfile.objects.filter(actiu=True).values_list('user_id', flat=True)
        return (
            User.objects
            .filter(id__in=active_user_ids, is_active=True)
            .select_related('profile')
        )
