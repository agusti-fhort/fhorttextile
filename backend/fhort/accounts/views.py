import django_filters
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, status as http_status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import UserProfile
from .capabilities import (HasCapability, MANAGE_USERS, ROLE_CAPABILITIES,
                           get_capabilities)
from .serializers import (MeSerializer, UserListSerializer, UserAdminSerializer,
                          UserCreateSerializer)


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
    """GET /api/v1/me/ — profile of the authenticated user in the current tenant.

    F4 P-LEGAL (única incursió al tenant): s'hi afegeix `legal_pending` — les versions
    legals vigents amb requereix_reacceptacio=True que el Client (empresa) encara no ha
    acceptat. El gate és PER-CLIENT (B2B): l'admin accepta en nom de l'empresa; la UI de
    tenant que consumeix aquesta dada és territori PLATAFORMA (handoff, no es construeix aquí).
    """
    data = dict(MeSerializer(request.user).data)
    # Import local: evita cicle accounts↔backoffice en càrrega.
    from fhort.backoffice.legal_service import pending_versions_for_client
    client = getattr(request, 'tenant', None)
    pend = pending_versions_for_client(client, nomes_reacceptacio=True)
    data['legal_pending'] = [
        {'id': v.id, 'tipus': v.document.tipus, 'nom': v.document.nom,
         'numero_versio': v.numero_versio, 'sha256': v.sha256, 'contingut': v.contingut}
        for v in pend
    ]
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def me_change_password(request):
    """POST /api/v1/me/change-password/  {new_password, new_password_confirm} — canvi autoservei.
    NO s'exigeix la contrasenya actual: la sessió JWT ja autentica. El JWT és stateless, així que
    la sessió actual segueix vàlida després del canvi (no es blacklisteja res)."""
    new_password = request.data.get('new_password') or ''
    confirm = request.data.get('new_password_confirm') or ''
    if new_password != confirm:
        return Response({'error': 'Les contrasenyes no coincideixen.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(new_password, request.user)
    except DjangoValidationError as e:
        return Response({'error': ' '.join(e.messages)}, status=http_status.HTTP_400_BAD_REQUEST)
    request.user.set_password(new_password)
    request.user.save(update_fields=['password'])
    return Response({'ok': True}, status=http_status.HTTP_200_OK)


class UserViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.CreateModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    """GET /api/v1/users/ — list/retrieve d'usuaris actius del tenant (selector + matriu).
    POST /api/v1/users/ — alta d'usuari (User + profile via signal), gated `manage_users`.
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
        # Alta = serializer de creació. Escriptura/PATCH = serializer admin. En lectura, els qui
        # poden gestionar usuaris reben la vista completa (matriu); la resta, el selector mínim.
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserAdminSerializer
        if MANAGE_USERS in get_capabilities(self.request.user):
            return UserAdminSerializer
        return UserListSerializer

    def create(self, request, *args, **kwargs):
        """POST /api/v1/users/ — alta gated manage_users. Els perfils del tenant no viuen a
        'public'; allà l'alta no té sentit → 400. Retorna la representació admin del nou usuari."""
        if getattr(connection, 'schema_name', None) == 'public':
            return Response({'error': "No es poden crear usuaris des de l'schema 'public'."},
                            status=http_status.HTTP_400_BAD_REQUEST)
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        # El signal deixa user.profile cachejat amb els valors per defecte; re-consultem fresc
        # perquè la representació reflecteixi rol_nom/permisos/capabilities reals del nou usuari.
        user = User.objects.select_related('profile').get(pk=user.pk)
        out = UserAdminSerializer(user, context=self.get_serializer_context())
        return Response(out.data, status=http_status.HTTP_201_CREATED)

    def get_queryset(self):
        if getattr(connection, 'schema_name', None) == 'public':
            return User.objects.none()
        active_user_ids = UserProfile.objects.filter(actiu=True).values_list('user_id', flat=True)
        return (
            User.objects
            .filter(id__in=active_user_ids, is_active=True)
            .select_related('profile')
        )

    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """POST /api/v1/users/bulk/ — accions massives (gated manage_users; patró gates/bulk/).
        Body: {"user_ids":[...], "action":"set_role|set_task|set_active", "value":...}
          - set_role:   value = "<rol_nom>"
          - set_active: value = true|false
          - set_task:   value = {"code":"<TaskType.code>", "on":true|false}  (afegeix/treu de permisos["tasks"])
        Read-modify-write per usuari. Resposta {"updated": N}. Només afecta perfils del tenant."""
        user_ids = request.data.get('user_ids') or []
        op = request.data.get('action')
        value = request.data.get('value')
        if not isinstance(user_ids, list) or not user_ids:
            return Response({'error': 'user_ids ha de ser una llista no buida.'},
                            status=http_status.HTTP_400_BAD_REQUEST)
        if op not in ('set_role', 'set_task', 'set_active'):
            return Response({'error': "action ha de ser 'set_role', 'set_task' o 'set_active'."},
                            status=http_status.HTTP_400_BAD_REQUEST)
        # Validació del value segons l'acció (abans de tocar res).
        if op == 'set_role' and value not in ROLE_CAPABILITIES:
            return Response({'error': f"Rol desconegut '{value}'. Vàlids: {sorted(ROLE_CAPABILITIES)}."},
                            status=http_status.HTTP_400_BAD_REQUEST)
        if op == 'set_active' and not isinstance(value, bool):
            return Response({'error': 'value ha de ser booleà per a set_active.'},
                            status=http_status.HTTP_400_BAD_REQUEST)
        if op == 'set_task' and (not isinstance(value, dict) or 'code' not in value
                                 or not isinstance(value.get('on'), bool)):
            return Response({'error': 'value ha de ser {"code":..., "on":true|false} per a set_task.'},
                            status=http_status.HTTP_400_BAD_REQUEST)
        # Aplicació (read-modify-write). El filtre per UserProfile manté l'abast dins del tenant.
        updated = 0
        for prof in UserProfile.objects.filter(user_id__in=user_ids):
            if op == 'set_role':
                prof.rol_nom = value
            elif op == 'set_active':
                prof.actiu = value
            elif op == 'set_task':
                permisos = dict(prof.permisos or {})
                tasks = list(permisos.get('tasks', []))
                code, on = value['code'], value['on']
                if on and code not in tasks:
                    tasks.append(code)
                elif not on and code in tasks:
                    tasks.remove(code)
                permisos['tasks'] = tasks
                prof.permisos = permisos
            prof.save()
            updated += 1
        return Response({'updated': updated}, status=http_status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reset-link')
    def reset_link(self, request, pk=None):
        """POST /api/v1/users/<pk>/reset-link/ — genera un enllaç de recuperació (gated manage_users).
        NO envia correu: retorna la URL perquè l'admin la passi a la persona pel canal que vulgui.
        L'enllaç porta el domini de la request (= schema del tenant, resolt per django-tenants) i
        caduca segons PASSWORD_RESET_TIMEOUT (24h). get_object() ja limita l'abast al tenant."""
        user = self.get_object()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        url = f"{request.scheme}://{request.get_host()}/reset-password/{uid}/{token}"
        return Response({'url': url}, status=http_status.HTTP_200_OK)


def _user_from_uid(uid):
    """Decodifica uid (urlsafe base64) → User dins l'schema actual. None si falla o no existeix.
    Schema resolt pel domini de la request (django-tenants); no cal tenant explícit."""
    if not uid:
        return None
    try:
        pk = urlsafe_base64_decode(uid).decode()
        return User.objects.get(pk=pk)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


@api_view(['GET'])
@permission_classes([AllowAny])
def password_reset_validate(request):
    """GET /api/v1/password-reset/validate/?uid=&token= — pre-check de la pàgina pública.
    No revela res més enllà del necessari: {'valid': bool}."""
    user = _user_from_uid(request.query_params.get('uid'))
    token = request.query_params.get('token') or ''
    valid = bool(user and default_token_generator.check_token(user, token))
    return Response({'valid': valid})


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """POST /api/v1/password-reset/confirm/  {uid, token, new_password} — fixa la nova contrasenya.
    Missatges genèrics (no exposa si l'usuari existeix). En desar el nou hash, el token queda
    invalidat sol (default_token_generator depèn del hash) → no es pot reutilitzar."""
    user = _user_from_uid(request.data.get('uid'))
    token = request.data.get('token') or ''
    new_password = request.data.get('new_password') or ''
    if user is None or not default_token_generator.check_token(user, token):
        return Response({'error': 'Enllaç de recuperació invàlid o caducat.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(new_password, user)
    except DjangoValidationError as e:
        return Response({'error': ' '.join(e.messages)}, status=http_status.HTTP_400_BAD_REQUEST)
    user.set_password(new_password)
    user.save(update_fields=['password'])
    return Response({'ok': True}, status=http_status.HTTP_200_OK)
