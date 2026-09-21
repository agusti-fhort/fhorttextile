# P-LEADS — porta pública del formulari de leads (ftt-web) + API privada (ADMIN).
from django.db import transaction
from django.db.models import Count, Q
from rest_framework import status, throttling, viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .leads_service import notifica_lead
from .legal_service import client_ip
from .models import Lead
from .serializers_leads import LeadDetailSerializer, LeadListSerializer, LeadPublicSerializer
from .views import HasBackofficeRole

ADMIN = [IsAuthenticated, HasBackofficeRole(roles=['ADMIN'])]


class LeadRateThrottle(throttling.SimpleRateThrottle):
    """Rate-limit propi de l'endpoint públic de leads (per IP). Rate fix, sense
    dependre de DEFAULT_THROTTLE_RATES (que el projecte no defineix). Mateix patró
    que DiscoveryRateThrottle (tenants/views_discovery.py)."""
    scope = 'leads'

    def get_rate(self):
        return '5/hour'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
@throttle_classes([LeadRateThrottle])
def lead_public_view(request):
    """POST /api/backoffice/v1/leads/public/ — únicament muntat a `public`
    (backoffice/urls.py → fhort/urls_public.py); un host de tenant no el troba
    (ROOT_URLCONF de tenant no inclou backoffice) → 404, no és un forat de permisos.

    Honeypot: si `website` ve ple, es respon 201 IDÈNTIC sense desar res ni validar
    la resta — un bot no ha de poder distingir aquesta resposta d'un alta real.
    """
    if (request.data.get('website') or '').strip():
        return Response({'ok': True}, status=status.HTTP_201_CREATED)

    serializer = LeadPublicSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    lead = serializer.save(ip=client_ip(request))
    transaction.on_commit(lambda: notifica_lead(lead))
    return Response({'ok': True}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes(ADMIN)
def lead_counts_view(request):
    """GET /api/backoffice/v1/leads/counts/ — recompte per estat + total, UNA sola
    consulta agregada (Count condicional): les 4 pestanyes de LeadsPage el llegeixen
    en lloc de refer-se al `count` de la paginació de cada pestanya per separat."""
    agg = Lead.objects.aggregate(
        nou=Count('pk', filter=Q(estat=Lead.ESTAT_NOU)),
        contactat=Count('pk', filter=Q(estat=Lead.ESTAT_CONTACTAT)),
        tancat=Count('pk', filter=Q(estat=Lead.ESTAT_TANCAT)),
    )
    agg['tots'] = agg['nou'] + agg['contactat'] + agg['tancat']
    return Response(agg)


class LeadViewSet(viewsets.ModelViewSet):
    """Llista/detall/PATCH(estat+notes)/DELETE de leads. Només ADMIN. Sense POST
    (l'alta és la porta pública, leads/public/) ni PUT complet (només PATCH parcial,
    vegeu LeadDetailSerializer: la resta de camps hi és read-only)."""
    queryset = Lead.objects.all()
    permission_classes = ADMIN
    filterset_fields = ['estat']
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'list':
            return LeadListSerializer
        return LeadDetailSerializer
