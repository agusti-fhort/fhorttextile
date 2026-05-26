from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import viewsets, mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import UserProfile
from .serializers import MeSerializer, UserListSerializer


User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """GET /api/v1/me/ — perfil de l'usuari autenticat al tenant actual."""
    return Response(MeSerializer(request.user).data)


class UserViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    """GET /api/v1/users/ — llistat d'usuaris actius del tenant.

    Filtra per UserProfile.actiu=True. Al schema 'public' retorna buit
    perquè els perfils tenant no hi viuen.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserListSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'first_name', 'last_name']
    ordering = ['username']

    def get_queryset(self):
        if getattr(connection, 'schema_name', None) == 'public':
            return User.objects.none()
        active_user_ids = UserProfile.objects.filter(actiu=True).values_list('user_id', flat=True)
        return (
            User.objects
            .filter(id__in=active_user_ids, is_active=True)
            .select_related('profile')
        )
