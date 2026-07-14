"""
Connector pricing ↔ fitxa de client — F2-B P2 (deute concret de F1/D2).

F1 va deixar el pricing CEC al client: l'endpoint de pricing resol per `?country=`
(views_pricing.py) però ningú alimentava aquest país des de la fitxa. Aquí es tanca el
forat SENSE tocar cap fitxer de F1: només es REUTILITZA `resolve_pricing` i s'hi passa
`Client.pais`. El fallback EUR viu dins `resolve_pricing` (si el país no té Price pròpia).

Superfície:
  · resolve_pricing_for_client(client) — servei intern reutilitzable (simulacions de
    contracte / futures pantalles) que NO acobla res a HTTP.
  · GET /api/backoffice/v1/pricing/for-client/<codi_tenant>/ — endpoint autenticat que
    exposa el mateix, per verificar-ho i per a la UI.
"""
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.tenants.models import Client

from .pricing_service import PricingUnavailable, resolve_pricing

logger = logging.getLogger('fhort.backoffice.pricing')


def resolve_pricing_for_client(client):
    """Preu vigent per a un client concret: alimenta el país de la fitxa al pricing de F1.

    Retorna (country, payload, stale). El fallback EUR és intern a resolve_pricing (si el
    `Client.pais` no té Price pròpia a Stripe). Propaga PricingUnavailable si Stripe cau i
    no hi ha cache — MAI inventa un preu.
    """
    country = client.pais or None
    payload, stale = resolve_pricing(country)
    return country, payload, stale


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pricing_for_client_view(request, codi_tenant):
    """Pricing vigent resolt amb el país de la fitxa del client. Autenticat backoffice."""
    try:
        client = Client.objects.get(codi_tenant=codi_tenant)
    except Client.DoesNotExist:
        return Response({'detail': 'Client no trobat.'}, status=404)

    try:
        country, payload, stale = resolve_pricing_for_client(client)
    except PricingUnavailable as exc:
        logger.error('Pricing 503 (client %s): %s', codi_tenant, exc)
        return Response(
            {'detail': 'Preus temporalment indisponibles. Torna-ho a provar en uns minuts.'},
            status=503,
        )

    resp = Response({'codi_tenant': codi_tenant, 'country': country, 'pricing': payload})
    if stale:
        resp['X-Pricing-Stale'] = 'true'
    return resp
