# Sprint 1 — Capa 9: views d'autenticació, perfil i RBAC del backoffice.
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import BackofficeTokenObtainSerializer, BackofficeUserMeSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def health_view(request):
    """Health check del routing public del backoffice (Sprint 0a). Sense auth."""
    return Response({'status': 'ok', 'scope': 'backoffice'})


class BackofficeTokenObtainView(TokenObtainPairView):
    """Login JWT del backoffice. Després d'emetre el token, segella ultim_acces.

    Replica la lògica del pare (TokenObtainPairView.post) per poder accedir a
    serializer.user i actualitzar el perfil sense una segona consulta.
    """

    serializer_class = BackofficeTokenObtainSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        perfil = getattr(serializer.user, 'backoffice_profile', None)
        if perfil is not None:
            perfil.ultim_acces = timezone.now()
            perfil.save(update_fields=['ultim_acces'])

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class BackofficeMeView(APIView):
    """Perfil de l'usuari de backoffice autenticat. Reforça actiu=True."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        perfil = getattr(request.user, 'backoffice_profile', None)
        if perfil is None or not perfil.actiu:
            raise PermissionDenied('Accés no autoritzat')
        return Response(BackofficeUserMeSerializer(perfil).data)


def HasBackofficeRole(roles=None):
    """Fàbrica de permisos DRF per restringir una view a rols concrets.

    Ús (a partir del Sprint 2)::

        permission_classes = [HasBackofficeRole(roles=['ADMIN', 'FACTURACIO'])]

    Sense `roles` només exigeix un BackofficeUser actiu. Combina amb
    IsAuthenticated per cobrir també el cas d'usuari anònim.
    """
    allowed = list(roles or [])

    class _HasBackofficeRole(BasePermission):
        message = 'Accés no autoritzat'

        def has_permission(self, request, view):
            perfil = getattr(request.user, 'backoffice_profile', None)
            if perfil is None or not perfil.actiu:
                return False
            if not allowed:
                return True
            return perfil.rol in allowed

    return _HasBackofficeRole
