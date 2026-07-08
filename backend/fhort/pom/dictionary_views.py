"""pom/dictionary_views.py — endpoints del diccionari de nomenclatura del client.

  GET  /api/v1/pom/customers/<id>/dictionary/template/  → plantilla xlsx
  POST /api/v1/pom/customers/<id>/dictionary/preview/   → parse + proposta (SENSE desar)
  POST /api/v1/pom/customers/<id>/dictionary/commit/    → desa la taula CONFIRMADA per l'humà

Escriptura gated CONFIGURE. Stateless (no taula de staging). El commit NO re-resol res: desa
el que la persona ha validat. Idempotent: update_or_create per (customer, client_code).
"""
import datetime

from django.db import transaction
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


@api_view(['POST'])
@permission_classes([_Configure])
def dictionary_commit_view(request, customer_id):
    """Desa la taula CONFIRMADA. NO re-resol: usa el pom_master_id que l'humà ha validat.
    action per fila: 'link' (vincula al POM triat) · 'create' (crea POM tenant-only nou i
    hi vincula) · 'skip' (no crea àlies). Guard: no sobreescriu un àlies origen=MANUAL sense
    reconeixement explícit (acknowledge_manual per fila)."""
    from fhort.pom.models import POMMaster, CustomerPOMAlias

    customer = _get_customer(customer_id)
    if customer is None:
        return Response({'error': 'Client no trobat.'}, status=400)

    rows = request.data.get('rows') or []
    existing = {
        (a.client_code or '').strip().lower(): a
        for a in CustomerPOMAlias.objects.filter(customer=customer).select_related('pom')
    }

    # 1) Guard anti-sobreescriptura de feina humana: detecta col·lisions amb àlies MANUAL
    #    abans d'escriure res. Si n'hi ha de no reconegudes → 409, cap escriptura.
    conflicts = []
    for row in rows:
        if (row.get('action') or 'link') != 'link':
            continue
        code = (row.get('codi_client') or '').strip()
        ex = existing.get(code.lower())
        if ex is None or ex.origen != 'MANUAL':
            continue
        new_pom = row.get('pom_master_id')
        if new_pom and ex.pom_id != int(new_pom) and not row.get('acknowledge_manual'):
            conflicts.append({
                'row_num': row.get('row_num'), 'codi_client': code,
                'existing_pom_id': ex.pom_id, 'new_pom_id': int(new_pom),
            })
    if conflicts:
        return Response({
            'error': 'Algunes files sobreescriurien un àlies MANUAL (correcció humana). '
                     'Confirma-les explícitament abans de desar.',
            'manual_conflicts': conflicts,
        }, status=409)

    # 2) Escriptura (transacció). El commit no re-resol: desa el que l'humà ha validat.
    today = datetime.date.today().strftime('%Y-%m-%d')
    stats = {'linked': 0, 'created_pom': 0, 'skipped': 0}
    with transaction.atomic():
        for row in rows:
            action = row.get('action') or 'link'
            code = (row.get('codi_client') or '').strip()
            if not code or action == 'skip':
                stats['skipped'] += 1
                continue
            desc_en = (row.get('descripcio_en') or '').strip()
            desc_local = (row.get('descripcio_local') or '').strip()
            idioma = (row.get('idioma') or '').strip().lower()[:2]

            if action == 'create':
                # Re-import idempotent: si ja hi ha un àlies per (customer, client_code) que
                # apunta a un POM tenant-only (creat per un diccionari previ), el REUTILITZEM
                # en comptes de crear-ne un de nou → cap POM orfe acumulat en re-imports.
                ex = existing.get(code.lower())
                if ex is not None and ex.pom is not None and ex.pom.pom_global_id is None:
                    pom = ex.pom
                else:
                    # POM tenant-only nou (sense gate — fase beta). Procedència: customer+diccionari+data.
                    pom = POMMaster.objects.create(
                        pom_global=None,
                        codi_client=code,
                        nom_client=(desc_en or desc_local or code),
                        actiu=True, pendent_revisio=True,
                        origen_import=f"diccionari:{customer.codi}:{today}",
                        notes=f"Creat des del diccionari del client {customer.codi} ({today}).",
                    )
                    stats['created_pom'] += 1
            else:  # link
                pom = POMMaster.objects.filter(pk=row.get('pom_master_id')).first()
                if pom is None:
                    stats['skipped'] += 1
                    continue

            # Idempotent: (customer, client_code). origen=DICCIONARI. 'quan' = actualitzat_at
            # (auto). TODO: CustomerPOMAlias no té camp autor ('qui'); afegir-lo si cal traça.
            CustomerPOMAlias.objects.update_or_create(
                customer=customer, client_code=code,
                defaults={
                    'pom': pom,
                    'description_en': desc_en,
                    'description_local': desc_local,
                    'language': idioma,
                    'origen': 'DICCIONARI',
                },
            )
            stats['linked'] += 1

    return Response({'customer': customer.codi, **stats}, status=200)
