"""models_app/bulk_import_views.py — endpoints REST de l'import massiu de models.

  GET  /api/v1/bulk-import/template/?customer_id=X   → descarrega la plantilla xlsx
  POST /api/v1/bulk-import/upload/                    → puja fitxer, valida, preview
  POST /api/v1/bulk-import/<id>/commit/              → commit parcial (crea Models + SF)
  GET  /api/v1/bulk-import/<id>/errors-report/       → informe d'errors xlsx
"""
import datetime
import io

from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

XLSX_CT = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _get_customer(customer_id):
    from fhort.tasks.models import Customer
    try:
        return Customer.objects.get(pk=customer_id)
    except (Customer.DoesNotExist, ValueError, TypeError):
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def template_view(request):
    from fhort.models_app.bulk_import_service import generate_template_bytes
    customer = _get_customer(request.GET.get('customer_id'))
    if customer is None:
        return Response({'error': 'Client no trobat.'}, status=400)
    data = generate_template_bytes(customer)
    today = datetime.date.today().strftime('%Y%m%d')
    resp = HttpResponse(data, content_type=XLSX_CT)
    resp['Content-Disposition'] = f'attachment; filename="plantilla_colleccio_{customer.codi}_{today}.xlsx"'
    return resp


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_view(request):
    from django.core.files.base import ContentFile
    from fhort.models_app.models import BulkCollectionImport, BulkCollectionRow
    from fhort.models_app.bulk_import_service import parse_upload, validate_rows

    customer = _get_customer(request.data.get('customer_id'))
    if customer is None:
        return Response({'error': 'Client no trobat.'}, status=400)
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'El teu usuari no té perfil; no pots importar.'}, status=400)

    file = request.FILES.get('file')
    if file is None:
        return Response({'error': 'Cal adjuntar un fitxer (camp "file").'}, status=400)
    name = (file.name or '').lower()
    if not (name.endswith('.xlsx') or name.endswith('.xls')):
        return Response({'error': 'Format no suportat. Adjunta un fitxer Excel (.xlsx).'}, status=400)

    file_bytes = file.read()
    try:
        detected, raw_rows = parse_upload(file_bytes)
    except Exception as e:
        return Response({'error': f'No s\'ha pogut llegir el fitxer: {e}'}, status=400)

    # 5.1 — Mismatch de Customer: BLOQUEJA abans de processar cap fila (error global).
    if detected and detected.strip().upper() != customer.codi.upper():
        return Response({'error': (
            f"El fitxer pertany al client {detected} però has seleccionat {customer.codi}. "
            f"Selecciona el client correcte o descarrega una nova plantilla.")}, status=400)

    if not raw_rows:
        return Response({'error': 'El fitxer no conté cap fila de dades.'}, status=400)

    results, resum = validate_rows(customer, raw_rows)

    imp = BulkCollectionImport.objects.create(
        customer=customer, creat_per=profile, estat='PREVISAT', resum=resum,
        resultat=[{'row_num': r['row_num'], 'estat': r['estat'], 'errors': r['errors']} for r in results],
    )
    imp.document.save(file.name, ContentFile(file_bytes), save=True)

    BulkCollectionRow.objects.bulk_create([
        BulkCollectionRow(importacio=imp, row_num=r['row_num'], raw_data=r['raw_data'],
                          estat=r['estat'], errors=r['errors'])
        for r in results
    ])

    return Response({
        'import_id': imp.id, 'resum': resum,
        'rows': [{'row_num': r['row_num'], 'estat': r['estat'],
                  'errors': r['errors'], 'raw_data': r['raw_data']} for r in results],
    }, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def commit_view(request, import_id):
    from fhort.models_app.models import BulkCollectionImport
    from fhort.models_app.bulk_import_service import commit_import

    try:
        imp = BulkCollectionImport.objects.get(pk=import_id)
    except BulkCollectionImport.DoesNotExist:
        return Response({'error': 'Importació no trobada.'}, status=404)
    if imp.estat == 'IMPORTAT':
        return Response({'error': 'Aquesta importació ja s\'ha confirmat.'}, status=400)
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'El teu usuari no té perfil; no pots importar.'}, status=400)

    stats = commit_import(imp, profile)
    return Response({'import_id': imp.id, 'estat': imp.estat, **stats}, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def errors_report_view(request, import_id):
    from fhort.models_app.models import BulkCollectionImport
    from fhort.models_app.bulk_import_service import errors_report_bytes

    try:
        imp = BulkCollectionImport.objects.get(pk=import_id)
    except BulkCollectionImport.DoesNotExist:
        return Response({'error': 'Importació no trobada.'}, status=404)

    data = errors_report_bytes(imp)
    today = datetime.date.today().strftime('%Y%m%d')
    resp = HttpResponse(data, content_type=XLSX_CT)
    resp['Content-Disposition'] = f'attachment; filename="errors_import_{imp.customer.codi}_{today}.xlsx"'
    return resp
