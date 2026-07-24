"""Els RECURSOS d'una Marca — la superfície del Brand sobre els seus vincles (P7).

    GET  /api/v1/recursos/                 → els Studios vinculats a AQUESTA Marca
    POST /api/v1/recursos/  {studio_codi}  → alta del vincle; el token surt UN SOL COP
    POST /api/v1/recursos/<pk>/aturar/     → tanca el pont sense destruir res
    POST /api/v1/recursos/<pk>/reactivar/  → el reobre (només des d'ATURAT)
    POST /api/v1/recursos/<pk>/revocar/    → el talla definitivament (terminal)

EL QUE EL BRAND VEU ÉS UN RECURS, NO UNA CASA DE GENT. Aquesta és la llei de la federació
duta a l'API: la resposta porta el codi i el nom del Studio i l'estat del pont, i res més.
Ni usuaris, ni tècnics, ni temps, ni feina. No és una omissió provisional: és el contracte.

EL BRAND SEMPRE ÉS EL DEL REQUEST, MAI EL DEL PAYLOAD. `request.tenant` és l'objecte que
django-tenants ha resolt pel domini, i és l'única font del `brand_codi_tenant` — tant en
llegir com en crear. Si el brand pogués viatjar al body, qualsevol tenant podria emetre's
vincles en nom d'un altre; el `unique_together` no ho aturaria (seria una parella nova).

PER QUÈ VIU A `tenants/` I ES SERVEIX DES DE L'URLCONF DE TENANT: la taula és a `public`
(fhort.tenants és SHARED), però qui la consulta és una petició de tenant. Verificat a la
diagnosi de P7 (A1): django-tenants deixa `search_path='<tenant>, public'` i
`tenants_tenantlink` NOMÉS existeix a `public` — cap taula del tenant la pot ombrejar. Per
tant es consulta directament, sense `schema_context` ni cap lectura delegada.

EL TOKEN NO ÉS UN CAMP, ÉS UNA CREDENCIAL. Surt exclusivament a la resposta 201 de la
creació — l'únic moment en què hi ha algú mirant que acaba de decidir emetre'l. No apareix
mai a la llista ni al detall, ni tan sols per a qui podria tornar a demanar-lo: una
credencial que es pot rellegir a voluntat és una credencial que viu a tots els logs, caches
i pestanyes obertes del camí. Si es perd, es revoca el vincle i se n'emet un de nou.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.accounts.capabilities import CONFIGURE, HasCapability

from .models import Client, TenantLink
from .serializers_recursos import RecursSerializer


class EsMarca(IsAuthenticated):
    """El tenant del request ha de ser una Marca. Un Estudi no emet vincles: els rep.

    403 i no 404: el recurs existeix conceptualment i l'usuari està autenticat; el que no
    té és la naturalesa per operar-hi. Amagar-ho seria mentir sobre la forma del sistema.
    """

    message = 'Només una Marca pot gestionar recursos.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        tenant = getattr(request, 'tenant', None)
        return tenant is not None and tenant.tipologia == Client.TIPOLOGIA_MARCA


class RecursViewSet(viewsets.ViewSet):
    """Els vincles de federació vistos des de la Marca que els emet.

    ViewSet pla (no ModelViewSet): el queryset no és "totes les files del model" sinó
    "les files d'AQUESTA marca", i les mutacions no són PATCH de camps sinó els tres actes
    de domini que el model ja sap fer (aturar/reactivar/revocar), amb les seves regles de
    transició. Un ModelViewSet obriria PUT/PATCH sobre `estat` i `token` i deixaria passar
    transicions que `TenantLink` prohibeix a posta (REVOCAT és terminal).
    """

    def get_permissions(self):
        # Llegir: qualsevol autenticat de la Marca. Escriure (alta i els 3 actes): CONFIGURE,
        # la capacitat que ja governa els mestres del tenant a tota la casa.
        if self.action == 'list':
            return [EsMarca()]
        perm = HasCapability()
        self.required_capability = CONFIGURE
        return [EsMarca(), perm]

    @property
    def _brand_codi(self):
        return self.request.tenant.codi_tenant

    def _qs(self):
        return TenantLink.objects.filter(brand_codi_tenant=self._brand_codi)

    def list(self, request):
        """Els recursos de la Marca, del més nou al més vell. Mai el token."""
        links = self._qs().order_by('-created_at')
        return Response(RecursSerializer(links, many=True).data)

    def create(self, request):
        """Alta d'un recurs. 201 amb el token; és l'únic cop que el token viatja."""
        studio_codi = (request.data.get('studio_codi') or '').strip().upper()
        if not studio_codi:
            return Response({'error': "Cal el codi del Studio.", 'code': 'studio_codi_required'},
                            status=status.HTTP_400_BAD_REQUEST)
        if studio_codi == self._brand_codi:
            return Response({'error': "Una Marca no es pot vincular a si mateixa.",
                             'code': 'self_link'}, status=status.HTTP_400_BAD_REQUEST)

        # 409 i no 400: el conflicte és amb un estat del món (el vincle ja existeix), no amb
        # la forma de la petició. Inclou el cas REVOCAT — reobrir-lo és una decisió que ha de
        # passar per revocar/reactivar, no per una alta que semblaria que no ha fet res.
        if self._qs().filter(studio_codi_tenant=studio_codi).exists():
            return Response({'error': f"Ja existeix un vincle amb '{studio_codi}'.",
                             'code': 'link_exists'}, status=status.HTTP_409_CONFLICT)

        link = TenantLink(brand_codi_tenant=self._brand_codi, studio_codi_tenant=studio_codi)
        try:
            # full_clean() és qui exigeix que el destí existeixi i sigui un Estudi (TenantLink.clean).
            # La validació de domini viu al model, no aquí: el command d'assignació i l'admin
            # han de rebre exactament el mateix veredicte que l'API.
            link.full_clean(exclude=['token'])
        except DjangoValidationError as e:
            return Response({'error': ' '.join(sum(e.message_dict.values(), [])),
                             'code': 'invalid_studio'}, status=status.HTTP_400_BAD_REQUEST)
        link.save()

        data = dict(RecursSerializer(link).data)
        data['token'] = link.token     # UN SOL COP, aquí i enlloc més
        return Response(data, status=status.HTTP_201_CREATED)

    def _transicio(self, pk, metode):
        """Els tres actes comparteixen forma: buscar dins l'abast de la Marca, provar la
        transició, i deixar que el model digui que no quan no toca (409, no 500)."""
        link = self._qs().filter(pk=pk).first()
        if link is None:
            return Response({'error': 'Recurs no trobat.', 'code': 'not_found'},
                            status=status.HTTP_404_NOT_FOUND)
        try:
            getattr(link, metode)()
        except DjangoValidationError as e:
            return Response({'error': ' '.join(e.messages), 'code': 'transicio_invalida'},
                            status=status.HTTP_409_CONFLICT)
        return Response(RecursSerializer(link).data)

    @action(detail=True, methods=['post'])
    def aturar(self, request, pk=None):
        return self._transicio(pk, 'aturar')

    @action(detail=True, methods=['post'])
    def reactivar(self, request, pk=None):
        return self._transicio(pk, 'reactivar')

    @action(detail=True, methods=['post'])
    def revocar(self, request, pk=None):
        return self._transicio(pk, 'revocar')
