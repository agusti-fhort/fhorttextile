# fhort/models_app/extraction_views.py
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def extract_from_file_view(request):
    """
    POST /api/v1/models/extract-from-file/
    Multipart: file (obligatori), generate_thumbnail (opcional, default=true)

    Retorna el JSON d'extracció + resultat del gate de Design Freeze.
    No crea cap Model — és una operació de preview/anàlisi.
    """
    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({'error': 'Cal adjuntar un fitxer (camp "file")'}, status=400)

    max_size_mb = 20
    if file_obj.size > max_size_mb * 1024 * 1024:
        return Response({'error': f'El fitxer supera el màxim de {max_size_mb}MB'}, status=400)

    allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.webp'}
    import os
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in allowed_extensions:
        return Response(
            {'error': f'Format no suportat: {ext}. Acceptats: {", ".join(allowed_extensions)}'},
            status=400
        )

    try:
        file_bytes = file_obj.read()
    except Exception as e:
        return Response({'error': f'Error llegint el fitxer: {e}'}, status=400)

    try:
        from fhort.models_app.extraction_service import extract_from_file, check_design_freeze
        extracted = extract_from_file(file_bytes, file_obj.name)
        design_freeze = check_design_freeze(extracted)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error en extracció de fitxa tècnica")
        return Response({'error': f'Error intern: {e}'}, status=500)

    return Response({
        'filename': file_obj.name,
        'file_size_kb': round(file_obj.size / 1024, 1),
        'extracted': extracted,
        'design_freeze': design_freeze,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_from_extraction_view(request):
    """
    POST /api/v1/models/create-from-extraction/
    Body: {extracted: {...}, overrides: {...}}

    Crea un Model + BaseMeasurements des del JSON d'extracció.
    Només funciona si design_freeze.pass == true.
    """
    extracted = request.data.get('extracted')
    overrides = request.data.get('overrides', {})

    if not extracted:
        return Response({'error': 'Cal proporcionar el camp "extracted"'}, status=400)

    from fhort.models_app.extraction_service import check_design_freeze
    df = check_design_freeze(extracted)
    if not df['pass']:
        return Response({
            'error': 'El document no passa el gate de Design Freeze',
            'blockers': df['blockers'],
        }, status=422)

    def val(field, fallback=None):
        v = extracted.get(field)
        if isinstance(v, dict):
            return v.get('value') or fallback
        return v or fallback

    # Aplicar overrides de l'usuari
    style_name = overrides.get('style_name') or val('style_name') or val('style_code')
    temporada = overrides.get('temporada') or val('season', 'SS')
    any_ = overrides.get('any') or val('year')
    base_size = overrides.get('base_size') or val('base_size')
    size_run = overrides.get('size_run') or val('size_run')

    try:
        from django_tenants.utils import schema_context
        from fhort.models_app.models import Model, BaseMeasurement
        from fhort.pom.models import POMMaster

        tenant_schema = request.tenant.schema_name if hasattr(request, 'tenant') else 'fhort'

        with schema_context(tenant_schema):
            # Crear el model
            model = Model.objects.create(
                nom_prenda=style_name,
                temporada=temporada[:2].upper() if temporada else 'SS',
                any=int(str(any_)[-2:]) if any_ else 27,
                base_size_label=base_size,
                size_run_model=size_run,
                codi_client=overrides.get('codi_client', ''),
                codi_tenant=overrides.get('codi_tenant', 'GEN'),
                sequencial=overrides.get('sequencial', 1),
                responsable_id=request.user.id,
            )

            # Crear BaseMeasurements
            poms_created = 0
            poms_skipped = 0
            for pom_data in extracted.get('poms', []):
                if not pom_data.get('base_value_cm'):
                    continue
                # Buscar POMMaster per codi_client
                pom_qs = POMMaster.objects.filter(codi_client=pom_data['code'])
                if not pom_qs.exists():
                    poms_skipped += 1
                    continue
                pom = pom_qs.first()
                BaseMeasurement.objects.update_or_create(
                    model=model,
                    pom=pom,
                    defaults={
                        'base_value_cm': pom_data['base_value_cm'],
                        'is_active': True,
                        'notes': pom_data.get('description', ''),
                    }
                )
                poms_created += 1

            return Response({
                'model_id': model.id,
                'codi_intern': model.codi_intern,
                'poms_created': poms_created,
                'poms_skipped': poms_skipped,
                'missatge': f'Model {model.codi_intern} creat amb {poms_created} POMs',
            }, status=201)

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error creant model des d'extracció")
        return Response({'error': str(e)}, status=500)
