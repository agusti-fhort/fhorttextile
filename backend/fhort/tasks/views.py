from django.db import connection
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import TimerEntrada
from .serializers import TimerEntradaSerializer


class TimerEntradaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TimerEntradaSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model_task', 'actiu']
    ordering_fields = ['inici', 'fi']
    ordering = ['-inici']

    def _get_profile(self):
        # UserProfile is linked via OneToOne with related_name='profile'.
        # The 'public' schema has no UserProfile, so we return None.
        if getattr(connection, 'schema_name', None) == 'public':
            return None
        return getattr(self.request.user, 'profile', None)

    def get_queryset(self):
        qs = (
            TimerEntrada.objects
            .select_related('tecnic', 'tecnic__user', 'model_task', 'model_task__model')
        )
        profile = self._get_profile()
        if profile is None:
            return qs.none()
        return qs.filter(tecnic=profile)

    def perform_create(self, serializer):
        profile = self._get_profile()
        if profile is None:
            raise PermissionDenied('Usuari sense UserProfile en aquest tenant.')
        serializer.save(tecnic=profile)

    @action(detail=False, methods=['post'], url_path='heartbeat')
    def heartbeat(self, request):
        """POST /api/v1/timers/heartbeat/ (sense body) — segella el tram obert del tècnic.

        Porta LLEUGERA: el frontend hi truca quan la persona confirma el modal del guard de tasca
        oblidada, i els 30 min es rearmen des del segell nou. Sense `pk` a posta — el timer es
        busca pel propi perfil (queryset ja scopat), de manera que per construcció no es pot
        segellar el tram d'un altre.

        Només compta el tram d'una tasca realment En curs: si la tasca ja s'ha pausat o tancat
        des d'una altra pestanya, el batec no ha de ressuscitar res → 404 i el front es
        resincronitza. Idempotent: trucar-hi dos cops només avança el segell."""
        timer = (self.get_queryset()
                 .filter(fi__isnull=True, actiu=True, model_task__status='InProgress')
                 .order_by('-inici').first())
        if timer is None:
            return Response({'error': 'Cap tasca En curs amb tram obert.'},
                            status=status.HTTP_404_NOT_FOUND)
        timer.last_heartbeat = timezone.now()
        # GANXO F-MÀ (no construït): quan la mà tingui TTL, `last_activity_at` s'escriu AQUÍ
        # mateix, en el mateix save. És el mateix senyal; dos batecs separats es desincronitzarien.
        timer.save(update_fields=['last_heartbeat'])
        return Response({'timer_id': timer.pk, 'model_task': timer.model_task_id,
                         'last_heartbeat': timer.last_heartbeat.isoformat()},
                        status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='tancar')
    def tancar(self, request, pk=None):
        timer = self.get_object()
        if timer.fi is not None:
            raise ValidationError('El timer ja està tancat.')
        now = timezone.now()
        delta = now - timer.inici
        minutes = max(0, int(delta.total_seconds() // 60))
        timer.fi = now
        timer.minuts = minutes
        timer.actiu = False
        timer.save(update_fields=['fi', 'minuts', 'actiu'])
        serializer = self.get_serializer(timer)
        return Response(serializer.data, status=status.HTTP_200_OK)
