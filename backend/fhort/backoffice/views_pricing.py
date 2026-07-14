"""
Endpoint de pricing — F1 (P-PRICE) · P2.

Serveix el preu VIGENT (des de Stripe, amb cache 5 min). Mai inventa preus:
si Stripe cau i no hi ha cap cache, respon 503; si hi ha cache caducada, la serveix
amb la capçalera X-Pricing-Stale: true.

  · GET /api/backoffice/v1/pricing/         → autenticat backoffice.
  · GET /api/backoffice/v1/pricing/public/  → AllowAny (perquè la web el consumeixi).
  Mateixa resposta; el paràmetre ?country=ES resol variants de país amb fallback EUR.
"""
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .pricing_service import PricingUnavailable, resolve_pricing

logger = logging.getLogger('fhort.backoffice.pricing')


def _pricing_response(request):
    """Cos comú dels dos endpoints. La resposta és idèntica (cap dada interna)."""
    country = request.query_params.get('country') or None
    try:
        payload, stale = resolve_pricing(country)
    except PricingUnavailable as exc:
        logger.error('Pricing 503: %s', exc)
        return Response(
            {'detail': 'Preus temporalment indisponibles. Torna-ho a provar en uns minuts.'},
            status=503,
        )
    resp = Response({'country': country, 'pricing': payload})
    if stale:
        resp['X-Pricing-Stale'] = 'true'
    return resp


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pricing_view(request):
    return _pricing_response(request)


@api_view(['GET'])
@permission_classes([AllowAny])
def pricing_public_view(request):
    return _pricing_response(request)
