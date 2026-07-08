"""pom/dictionary_views.py — endpoints del diccionari de nomenclatura del client.

  GET  /api/v1/pom/customers/<id>/dictionary/template/  → plantilla xlsx
  POST /api/v1/pom/customers/<id>/dictionary/preview/   → parse + proposta (SENSE desar)
  POST /api/v1/pom/customers/<id>/dictionary/commit/    → desa la taula CONFIRMADA per l'humà

Escriptura gated CONFIGURE. Stateless (no taula de staging). El commit NO re-resol res: desa
el que la persona ha validat. Idempotent: update_or_create per (customer, client_code).
"""
import datetime

from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from fhort.accounts.capabilities import HasCapability, CONFIGURE
from .dictionary_service import generate_template_bytes, parse_upload, build_preview

XLSX_CT = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class _Configure(HasCapability):
    required_capability = CONFIGURE


def _get_customer(customer_id):
    from fhort.tasks.models import Customer
    try:
        return Customer.objects.get(pk=customer_id)
    except (Customer.DoesNotExist, ValueError, TypeError):
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dictionary_template_view(request, customer_id):
    customer = _get_customer(customer_id)
    if customer is None:
        return Response({'error': 'Client no trobat.'}, status=400)
    data = generate_template_bytes(customer)
    today = datetime.date.today().strftime('%Y%m%d')
    resp = HttpResponse(data, content_type=XLSX_CT)
    resp['Content-Disposition'] = f'attachment; filename="diccionari_{customer.codi}_{today}.xlsx"'
    return resp


@api_view(['POST'])
@permission_classes([_Configure])
@parser_classes([MultiPartParser, FormParser])
def dictionary_preview_view(request, customer_id):
    customer = _get_customer(customer_id)
    if customer is None:
        return Response({'error': 'Client no trobat.'}, status=400)

    file = request.FILES.get('file')
    if file is None:
        return Response({'error': 'Cal adjuntar un fitxer (camp "file").'}, status=400)
    name = (file.name or '').lower()
    if not (name.endswith('.xlsx') or name.endswith('.xls')):
        return Response({'error': 'Format no suportat. Adjunta un fitxer Excel (.xlsx).'}, status=400)

    try:
        detected, raw_rows = parse_upload(file.read())
    except Exception as e:
        return Response({'error': f"No s'ha pogut llegir el fitxer: {e}"}, status=400)

    if detected and detected.strip().upper() != customer.codi.upper():
        return Response({'error': (
            f"El fitxer pertany al client {detected} però has seleccionat {customer.codi}. "
            f"Descarrega la plantilla del client correcte.")}, status=400)
    if not raw_rows:
        return Response({'error': 'El fitxer no conté cap fila de dades.'}, status=400)

    rows, resum = build_preview(customer, raw_rows)
    return Response({'customer': customer.codi, 'rows': rows, 'resum': resum}, status=200)
