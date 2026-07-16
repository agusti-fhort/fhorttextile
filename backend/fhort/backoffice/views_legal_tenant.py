# F4 P-LEGAL P3 — incursió al TENANT: acceptació legal en nom de l'empresa (B2B).
# La vista viu al backoffice (concentra la lògica legal) però es munta al urlconf de
# TENANT (accounts/urls.py) → /api/v1/legal/accept/. Reusa legal_service.record_acceptance,
# no duplica la vista del backoffice. Permís: capability d'admin de tenant (MANAGE_USERS):
# és l'admin qui accepta pel Client, no cada usuari.
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.accounts.capabilities import MANAGE_USERS, get_capabilities

from .legal_service import record_acceptance
from .models import LegalAcceptance, LegalDocumentVersion
from .serializers_legal import LegalAcceptanceSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def legal_accept_tenant_view(request):
    """POST /api/v1/legal/accept/ {versio} — l'admin del tenant accepta una versió legal
    en nom de l'empresa. Idempotent (get_or_create per client+versio). IP real + user_agent."""
    if MANAGE_USERS not in get_capabilities(request.user):
        return Response({'detail': "Només l'administrador pot acceptar documents legals "
                                   "en nom de l'empresa."}, status=403)
    client = getattr(request, 'tenant', None) or getattr(connection, 'tenant', None)
    if client is None:
        return Response({'detail': 'Sense tenant al context.'}, status=400)
    versio_id = request.data.get('versio')
    versio = LegalDocumentVersion.objects.filter(pk=versio_id).first()
    if versio is None:
        return Response({'detail': 'Versió no trobada.'}, status=404)
    try:
        acc, created = record_acceptance(
            client, versio, getattr(request.user, 'email', ''), request,
            LegalAcceptance.METODE_CHECKBOX)
    except ValueError as e:
        return Response({'detail': str(e)}, status=400)
    return Response(LegalAcceptanceSerializer(acc).data, status=201 if created else 200)
