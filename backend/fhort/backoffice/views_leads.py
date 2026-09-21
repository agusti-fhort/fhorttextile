# P-LEADS — porta pública del formulari de leads (ftt-web).
from django.db import transaction
from rest_framework import status, throttling
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .leads_service import notifica_lead
from .legal_service import client_ip
from .serializers_leads import LeadPublicSerializer


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
