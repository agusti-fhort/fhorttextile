# Sprint 2 — Capa 1/2: views de tenants i plans per al backoffice.
# El backoffice consulta i administra el REGISTRE de tenants (taula Client al
# schema public). MAI commuta cap al schema d'un tenant.
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.tenants.models import Client, Plan

from .models import BackofficeActionLog
from .serializers_tenants import (
    ClientDetailSerializer,
    ClientListSerializer,
    PlanSerializer,
)
from .views import HasBackofficeRole


class ClientViewSet(viewsets.ReadOnlyModelViewSet):
    """Llista i detall de tenants + acció de canvi d'estat (ADMIN).

    Base de només lectura: el backoffice no crea ni esborra tenants des d'aquí
    (l'alta d'un tenant crea schema; queda fora d'abast d'aquest sprint). Els
    canvis permesos passen per accions explícites i auditades.
    """

    queryset = Client.objects.select_related('plan').all()
    lookup_field = 'codi_tenant'
    filterset_fields = ['estat', 'tipologia', 'plan']
    permission_classes = [IsAuthenticated, HasBackofficeRole()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ClientDetailSerializer
        return ClientListSerializer

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated, HasBackofficeRole(roles=['ADMIN'])],
    )
    def update_estat(self, request, codi_tenant=None):
        """Canvia l'estat del cicle de vida d'un tenant. Només ADMIN. Auditat.

        Body: {"estat": "<onboarding|actiu|suspes|baixa>", "motiu_baixa"?: str}.
        Segella data_suspensio/data_baixa en la transició corresponent.
        """
        client = self.get_object()
        nou_estat = request.data.get('estat')
        valids = dict(Client.ESTAT_CHOICES)
        if nou_estat not in valids:
            return Response(
                {'estat': f'Estat invàlid. Opcions: {list(valids)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        anterior = client.estat
        update_fields = ['estat']
        client.estat = nou_estat

        avui = timezone.now().date()
        if nou_estat == Client.ESTAT_SUSPES and not client.data_suspensio:
            client.data_suspensio = avui
            update_fields.append('data_suspensio')
        if nou_estat == Client.ESTAT_BAIXA and not client.data_baixa:
            client.data_baixa = avui
            update_fields.append('data_baixa')

        motiu = request.data.get('motiu_baixa')
        if motiu is not None:
            client.motiu_baixa = motiu
            update_fields.append('motiu_baixa')

        client.save(update_fields=update_fields)

        BackofficeActionLog.objects.create(
            usuari=getattr(request.user, 'backoffice_profile', None),
            accio='client.update_estat',
            objecte_tipus='Client',
            objecte_id=client.codi_tenant,
            detall={'de': anterior, 'a': nou_estat, 'motiu': motiu or ''},
        )

        return Response(ClientDetailSerializer(client).data)


class PlanViewSet(viewsets.ModelViewSet):
    """CRUD complet de plans comercials. Només ADMIN."""

    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated, HasBackofficeRole(roles=['ADMIN'])]
