from django.db import connection
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import TimerEntrada
from .serializers import TimerEntradaSerializer


class TimerEntradaViewSet(viewsets.ReadOnlyModelViewSet):
    """Trams de temps del PROPI tècnic. **Lectura + les dues accions**, mai CRUD.

    Un `TimerEntrada` no és un recurs que el client redacti: neix i mor dins de `transition_task`
    (`services_c.py:_open_timer` / `_close_open_timer`), que és qui sap tancar-lo amb la seva
    durada i alimentar-ne el Welford. Com a `ModelViewSet`, però, el router publicava també
    `POST /timers/`, `PUT|PATCH /timers/<id>/` i `DELETE /timers/<id>/` amb només `IsAuthenticated`
    — i `inici` i `model_task` són escrivibles al serializer (`read_only_fields` només cobreix
    `tecnic`, `minuts`, `fi` i `last_heartbeat`). Amb això, el temps facturable era **inventable i
    esborrable des del navegador**, per `id`, sense passar per cap transició ni deixar cap
    `TaskTransition` al log.

    El fitxer de test d'aquesta zona ja declarava la llei —«l'única porta d'escriptura ha de ser
    `heartbeat`» (`test_guard_tasca_oblidada.py:11`)—; el que faltava era aplicar-la al nivell
    correcte. Defensar `last_heartbeat` camp a camp tapava un forat i deixava la porta oberta.

    Cap consumidor perd res: `timers.create` està declarat a `endpoints.js` però **no el crida
    ningú** (verificat), i no hi ha ni `update` ni `remove`. El que segueix viu és el que es fa
    servir: `list` (guard + pàgina de temps), `retrieve`, i les accions `tancar` i `heartbeat`.
    """
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

    # F1.7 — JUBILADA l'acció `tancar` (`POST /api/v1/timers/<pk>/tancar/`).
    #
    # Tancava un tram SENSE passar per `transition_task`: cap `TaskTransition`, cap
    # `record_actual_time`, i la tasca quedava «En curs» sense tram obert — l'anomalia «òrfena»
    # que el cron compta i no toca. Era, a més, l'última escriptura pública que quedava en aquest
    # viewset: el pas a `ReadOnlyModelViewSet` (89009858) va tancar el router, però les `@action`
    # no en depenen.
    #
    # El seu únic consumidor era el botó de `/temps` (`TimeTracking.jsx`), que a la pràctica no
    # funcionava: la pàgina llegeix `data_inici`/`data_fi`/`created_at` i el serializer emet
    # `inici`/`fi` (i `created_at` no existeix a la taula), de manera que el botó disparava sobre
    # el primer tram de la llista —normalment ja tancat— i rebia un 400 (§S-3).
    #
    # Qui vulgui tancar feina té el Stop, que passa per la màquina d'estats. La refeta de la
    # pàgina de temps és F2.
