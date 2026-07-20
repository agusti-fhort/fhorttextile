"""Endpoint PÚBLIC de tenant-discovery (viu a fhort.urls_public → schema public).

Contracte: POST /api/discovery/ {email} → SEMPRE resposta UNIFORME (indistingible entre email
en 0, 1 o >1 tenants). Si l'email existeix a ≥1 tenant, s'envia (best-effort) un correu amb
el/s enllaç/os d'accés. L'única revelació és a la bústia del titular.

DEFAULT_PERMISSION_CLASSES del projecte = IsAuthenticated → aquí cal AllowAny explícit.
No hi ha throttling global (diagnosi P5) → s'adjunta un throttle propi a aquest endpoint sensible.
"""
import logging

from rest_framework import status, throttling
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .discovery_service import find_workspaces_for_email, send_discovery_email

logger = logging.getLogger(__name__)

# Missatge uniforme (fallback; el frontend en pinta la seva versió i18n). NO revela existència.
DISCOVERY_UNIFORM_DETAIL = "Si l'adreça està registrada, rebràs un correu amb els teus accessos."


class DiscoveryRateThrottle(throttling.SimpleRateThrottle):
    """Rate-limit propi de l'endpoint de discovery (per IP). Rate fix, sense dependre de
    DEFAULT_THROTTLE_RATES (que el projecte no defineix). Frena l'enumeració per volum."""
    scope = 'discovery'

    def get_rate(self):
        return '10/hour'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class TenantDiscoveryView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [DiscoveryRateThrottle]
    authentication_classes = []   # endpoint anònim; evita el cost/soroll de SessionAuth/JWT

    def post(self, request):
        email = (request.data.get('email') or '').strip()
        if not email:
            # Camp absent = error de client (no revela existència de cap email concret).
            return Response({'detail': 'Cal indicar una adreça de correu.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            workspaces = find_workspaces_for_email(email)
            if workspaces:
                send_discovery_email(email, workspaces)
        except Exception:   # noqa: BLE001 — cap error intern pot alterar la resposta uniforme
            logger.exception("discovery: fallada interna (empassada per uniformitat)")
        # SEMPRE la mateixa resposta, hi hagi 0, 1 o N workspaces.
        return Response({'detail': DISCOVERY_UNIFORM_DETAIL}, status=status.HTTP_200_OK)
