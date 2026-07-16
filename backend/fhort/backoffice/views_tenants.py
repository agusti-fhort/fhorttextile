# Sprint 2 — Capa 1/2 · Sprint 3 — alta/edició de tenants i plans (backoffice).
# El backoffice administra el REGISTRE de tenants (taules Client/Domain/
# TenantContacte al schema public). En crear un tenant, django-tenants
# PROVISIONA un schema nou (auto_create_schema); MAI s'entra al schema d'un
# tenant existent per llegir-ne dades.
import subprocess
import sys

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.tenants.models import Client, Domain, Plan, TenantContacte

from .models import BackofficeActionLog
from .serializers_tenants import (
    ClientCreateSerializer,
    ClientDetailSerializer,
    ClientListSerializer,
    ClientUpdateSerializer,
    PlanSerializer,
    TenantContacteSerializer,
)
from .views import HasBackofficeRole

# Accions que muten el registre → només ADMIN.
ADMIN_ACTIONS = {'create', 'partial_update', 'update_estat', 'contactes', 'contacte_detail'}


def _llanca_sembra_free(client):
    """F3 P-FREE-SEED (B3): dispara la sembra automàtica d'un tenant Free.

    Es crida NOMÉS quan `client.plan` és el tier Free, DESPRÉS de crear el Domain
    (el schema ja existeix i el host resol). Llança `provision_free_tenant` en un
    subprocés DETACHED (start_new_session) i torna a l'instant: el create() HTTP
    respon 201 sense esperar la sembra; el frontend fa polling de `Client.estat`
    (onboarding→actiu, que tanca el bootstrap). L'orquestrador escriu cada pas al
    Registre d'activitat i és re-executable si falla.
    """
    manage_py = str(settings.BASE_DIR / 'manage.py')
    subprocess.Popen(
        [sys.executable, manage_py, 'provision_free_tenant', client.schema_name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,  # desacobla del cicle de vida del worker/petició
    )


class ClientViewSet(viewsets.ReadOnlyModelViewSet):
    """Llista/detall de tenants + alta, edició, canvi d'estat i contactes.

    Base ReadOnly ampliada amb mètodes/accions explícits: NO s'exposa PUT (full
    update) ni DELETE de tenant (esborrar un Client deixaria el schema orfe).
    """

    queryset = Client.objects.select_related('plan').all()
    lookup_field = 'codi_tenant'
    filterset_fields = ['estat', 'tipologia', 'plan']
    permission_classes = [IsAuthenticated, HasBackofficeRole()]

    def get_permissions(self):
        roles = ['ADMIN'] if self.action in ADMIN_ACTIONS else None
        return [IsAuthenticated(), HasBackofficeRole(roles=roles)()]

    def get_serializer_class(self):
        if self.action == 'create':
            return ClientCreateSerializer
        if self.action == 'partial_update':
            return ClientUpdateSerializer
        if self.action == 'retrieve':
            return ClientDetailSerializer
        return ClientListSerializer

    # ---- Alta d'un tenant (provisiona schema + domini) --------------------
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # IMPORTANT: la creació del tenant NO va dins transaction.atomic. El
        # serializer.save() dispara auto_create_schema (django-tenants), que
        # executa DDL/migracions sobre el schema nou. Embolcallar-ho en una
        # transacció amb l'INSERT del Client provoca a PostgreSQL l'error
        # "cannot ALTER TABLE ... because it has pending trigger events".
        # Patró django-tenants: provisionar el tenant FORA de transaccions.
        # Compromís acceptat: si falla la creació del Domain, queda un Client +
        # schema orfe (cleanup manual / comanda futura).
        client = serializer.save()
        domini = f'{client.codi_tenant.lower()}.fhorttextile.tech'
        Domain.objects.create(domain=domini, tenant=client, is_primary=True)
        BackofficeActionLog.objects.create(
            usuari=getattr(request.user, 'backoffice_profile', None),
            accio='client.create',
            objecte_tipus='Client',
            objecte_id=client.codi_tenant,
            detall={'nom': client.nom, 'schema': client.schema_name, 'domini': domini},
        )
        # F3 P-FREE-SEED: només un tenant Free sembra sol. La resta de plans (i plan
        # NULL) queden en onboarding, buits, fins a provisió manual. `plan.nom` és la
        # font (F1 hi ha afegit NOM_FREE); si plan és NULL, no és Free.
        if client.plan_id and client.plan.nom == Plan.NOM_FREE:
            _llanca_sembra_free(client)
        return Response(
            ClientDetailSerializer(client).data, status=status.HTTP_201_CREATED,
        )

    # ---- Edició parcial (PATCH) -------------------------------------------
    def partial_update(self, request, *args, **kwargs):
        client = self.get_object()
        serializer = self.get_serializer(client, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        regim_abans = client.regim_vat
        with transaction.atomic():
            # Client.save() recalcula regim_vat automàticament a partir del pivot.
            client = serializer.save()
            BackofficeActionLog.objects.create(
                usuari=getattr(request.user, 'backoffice_profile', None),
                accio='client.update',
                objecte_tipus='Client',
                objecte_id=client.codi_tenant,
                detall={
                    'camps': list(serializer.validated_data.keys()),
                    'regim_vat': (
                        {'abans': regim_abans, 'despres': client.regim_vat}
                        if regim_abans != client.regim_vat else None
                    ),
                },
            )
        return Response(ClientDetailSerializer(client).data)

    # ---- Canvi d'estat del cicle de vida ----------------------------------
    @action(detail=True, methods=['post'])
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

    # ---- Gestió de contactes ----------------------------------------------
    @action(detail=True, methods=['get', 'post'])
    def contactes(self, request, codi_tenant=None):
        """GET llista · POST crea contactes del tenant. POST auditat."""
        client = self.get_object()

        if request.method == 'GET':
            return Response(
                TenantContacteSerializer(client.contactes.all(), many=True).data
            )

        # POST
        serializer = TenantContacteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            # Un sol principal per client: en marcar-ne un, es degrada l'anterior.
            if serializer.validated_data.get('principal'):
                client.contactes.filter(principal=True).update(principal=False)
            contacte = serializer.save(client=client)
            BackofficeActionLog.objects.create(
                usuari=getattr(request.user, 'backoffice_profile', None),
                accio='client.contacte_create',
                objecte_tipus='TenantContacte',
                objecte_id=str(contacte.pk),
                detall={
                    'codi_tenant': client.codi_tenant,
                    'nom': f'{contacte.nom} {contacte.cognom}'.strip(),
                    'principal': contacte.principal,
                },
            )
        return Response(
            TenantContacteSerializer(contacte).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=['delete'],
        url_path=r'contactes/(?P<contacte_id>[^/.]+)',
    )
    def contacte_detail(self, request, codi_tenant=None, contacte_id=None):
        """DELETE d'un contacte concret per id: /contactes/{id}/. Auditat."""
        client = self.get_object()
        contacte = client.contactes.filter(pk=contacte_id).first()
        if contacte is None:
            return Response(
                {'detail': 'Contacte no trobat per a aquest tenant.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        detall = {
            'codi_tenant': client.codi_tenant,
            'nom': f'{contacte.nom} {contacte.cognom}'.strip(),
        }
        with transaction.atomic():
            contacte.delete()
            BackofficeActionLog.objects.create(
                usuari=getattr(request.user, 'backoffice_profile', None),
                accio='client.contacte_delete',
                objecte_tipus='TenantContacte',
                objecte_id=str(contacte_id),
                detall=detall,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlanViewSet(viewsets.ModelViewSet):
    """CRUD complet de plans comercials. Només ADMIN."""

    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated, HasBackofficeRole(roles=['ADMIN'])]
