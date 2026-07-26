"""F3 · endpoint de PROPOSTA de cotes amb IA de visió (D5: SYNC amb guards).

POST /api/v1/models/<model_id>/proposar-cotes/
Body: { page_image (dataURL PNG), sketches: [{object_id, bbox_norm{x,y,w,h}, view_slot|null}],
        poms: [{pom_id, code, canonical_name, client_alias|null, definition|null}] }
Resposta: { placements: [...], skip: [...], usage, model }  ·  error net → 502 (mai 500 críptic).

Règim INFORMATIU + revisió humana: aquí NO s'escriu cap cota ni cap valor. El view només
retorna la proposta; el tècnic l'accepta al frontend (i l'acceptació és qui escriu precedent).
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Model

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def proposar_cotes_view(request, model_id):
    model = get_object_or_404(Model, pk=model_id)
    data = request.data or {}
    page_image = data.get('page_image')
    sketches = data.get('sketches') or []
    poms = data.get('poms') or []
    if not page_image:
        return Response({'error': 'page_image (dataURL PNG) és obligatori.'}, status=400)
    if not poms:
        return Response({'error': 'Cap POM pendent a proposar.'}, status=400)

    from .pom_vision_service import proposar_cotes
    perfil = getattr(request.user, 'profile', None)
    try:
        result = proposar_cotes(page_image=page_image, sketches=sketches, poms=poms,
                                model=model, created_by=perfil)
    except ValueError as e:
        # Error NET (config, HTTP, timeout, JSON invàlid) → 502, mai un 500 críptic.
        return Response({'error': str(e)}, status=502)
    except Exception:
        logger.exception("proposar_cotes_view: error inesperat")
        return Response({'error': 'Error inesperat en la proposta de cotes.'}, status=502)
    return Response(result)
