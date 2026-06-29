"""Plantilles de fitxa per Customer (TechSheetTemplate).

NOTA (Fase 2 .ftt): la fitxa per-model (TechSheet O2O) s'ha jubilat — l'editor treballa ara
sobre documents .ftt (ModelFitxer tipus TECHSHEET) via els endpoints ftt-documents/. Aquí
només queden les vistes de PLANTILLA per Customer, que segueixen vives fins al seu cutover propi
a DocumentTemplate.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.accounts.capabilities import CONFIGURE, get_capabilities

from .tech_sheet_models import TechSheetTemplate
from .tech_sheet_serializers import TechSheetTemplateSerializer


# ── TechSheetTemplate views (plantilla per Customer) ─────────────────────────

def _get_template(customer_id):
    """Retorna (o crea) la plantilla del customer. 404 si el customer no existeix."""
    from fhort.tasks.models import Customer
    customer = get_object_or_404(Customer, pk=customer_id)
    template, _ = TechSheetTemplate.objects.get_or_create(customer=customer)
    return template


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_or_create_template(request, customer_id):
    template = _get_template(customer_id)
    return Response(TechSheetTemplateSerializer(template).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_template(request, customer_id):
    # Escriptura de plantilla gated `configure` (mateix patró que la resta del subsistema).
    if CONFIGURE not in get_capabilities(request.user):
        return Response({'detail': "Cal la capacitat 'configure'."},
                        status=status.HTTP_403_FORBIDDEN)
    tj = request.data.get('template_json')
    if tj is None:
        return Response({'detail': 'Falta template_json.'},
                        status=status.HTTP_400_BAD_REQUEST)
    template = _get_template(customer_id)
    template.template_json = tj
    nom = request.data.get('nom')
    if nom is not None:
        template.nom = nom
    template.save()
    return Response(TechSheetTemplateSerializer(template).data)
