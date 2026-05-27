# fhort/models_app/extraction_views.py
import datetime as _dt
import re as _re

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status


def normalize_size_run(raw):
    """Converteix qualsevol format de size_run a 'XXS·XS·S·M·L·XL'."""
    if not raw:
        return ''
    if isinstance(raw, list):
        sizes = [str(s).strip() for s in raw if str(s).strip()]
    elif isinstance(raw, str):
        # Pot ser "['XXS', 'XS', 'S']" o "XXS,XS,S" o "XXS XS S"
        sizes = _re.findall(r'[A-Z0-9]+', raw.upper())
        # Filtra tokens que no semblen talles
        sizes = [s for s in sizes if 1 <= len(s) <= 5]
    else:
        return ''
    return '·'.join(sizes)


def parse_any(raw):
    """Normalitza l'any a un enter de 4 dígits."""
    if not raw:
        return _dt.date.today().year
    try:
        y = int(str(raw).strip())
        if y < 100:
            y += 2000
        return y
    except (ValueError, TypeError):
        return _dt.date.today().year


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

    # Fix A — size_run normalitzat
    size_run_raw = overrides.get('size_run') or val('size_run')
    size_run = normalize_size_run(size_run_raw)

    # Fix D — any correcte (2 dígits → 4, fallback a l'any actual)
    any_value = parse_any(any_)

    # Fix C — codi_client obligatori per al signal pre_save (genera codi_intern)
    codi_client = (overrides.get('codi_client') or '').strip().upper()
    if not codi_client:
        ref = val('style_reference') or val('style_code') or ''
        codi_client = _re.sub(r'[^A-Z0-9]', '', str(ref).upper())[:6]
    if not codi_client:
        codi_client = _re.sub(r'[^A-Z]', '', str(style_name or 'IMP').upper())[:3]
    if not codi_client:
        codi_client = 'IMP'

    codi_tenant = (overrides.get('codi_tenant') or codi_client[:3]).upper()[:3]

    try:
        from django_tenants.utils import schema_context
        from fhort.models_app.models import Model, BaseMeasurement
        from fhort.pom.models import POMMaster, GarmentType

        tenant_schema = request.tenant.schema_name if hasattr(request, 'tenant') else 'fhort'

        with schema_context(tenant_schema):
            # garment_type és NOT NULL al Model. Provem a fer match per nom
            # aproximat amb el que ha extret la IA; si no, agafem el primer
            # GarmentType disponible com a fallback.
            gt_hint = overrides.get('garment_type') or val('garment_type') or ''
            gt = None
            if gt_hint:
                gt = (
                    GarmentType.objects.filter(nom_client__icontains=gt_hint).first()
                    or GarmentType.objects.filter(codi_client__icontains=gt_hint).first()
                )
            if gt is None:
                gt = GarmentType.objects.first()
            if gt is None:
                return Response(
                    {'error': 'No hi ha cap GarmentType configurat al tenant; cal sembrar-ne almenys un.'},
                    status=422,
                )

            # Crear el model
            model = Model.objects.create(
                nom_prenda=style_name,
                temporada=temporada[:2].upper() if temporada else 'SS',
                any=any_value,
                base_size_label=base_size,
                size_run_model=size_run,
                codi_client=codi_client,
                codi_tenant=codi_tenant,
                sequencial=overrides.get('sequencial', 1),
                responsable_id=request.user.id,
                garment_type=gt,
            )

            # Fix B — Match POMMaster amb prioritats: codi exacte, descripció,
            # nom_en del POMGlobal, abbreviation.
            def find_pom_master(code, description):
                pm = POMMaster.objects.filter(codi_client__iexact=code).first()
                if pm:
                    return pm, 'exact_code'

                if not description:
                    return None, 'no_match'

                desc_clean = description.lower().strip()
                desc_base = _re.sub(r'\s*[\(\[].*?[\)\]]', '', desc_clean).strip()

                for pm in POMMaster.objects.select_related('pom_global').filter(actiu=True):
                    nom = (pm.nom_client or '').lower()
                    if desc_base and (desc_base in nom or nom in desc_base):
                        return pm, 'description_match'

                for pm in POMMaster.objects.select_related('pom_global').filter(
                    pom_global__isnull=False, actiu=True
                ):
                    pg = pm.pom_global
                    nom_en = (pg.nom_en or '').lower()
                    abbrev = (pg.abbreviation or '').lower()
                    if desc_base and (desc_base in nom_en or nom_en in desc_base):
                        return pm, 'global_name_match'
                    if code and code.lower() == abbrev:
                        return pm, 'abbreviation_match'

                return None, 'no_match'

            poms_created = 0
            poms_skipped = []
            match_log = []

            for pom_data in extracted.get('poms', []):
                base_value = pom_data.get('base_value_cm')
                if not base_value:
                    continue

                code = pom_data.get('code', '') or ''
                description = pom_data.get('description', '') or ''

                pm, match_type = find_pom_master(code, description)

                if not pm:
                    poms_skipped.append({
                        'code': code,
                        'description': description,
                        'reason': 'Cap POM del catàleg coincideix — assigna manualment',
                    })
                    continue

                BaseMeasurement.objects.update_or_create(
                    model=model, pom=pm,
                    defaults={
                        'base_value_cm': base_value,
                        'nom_fitxa': code,
                        'origen': 'IMPORTED',
                        'is_active': True,
                        'notes': description,
                    },
                )
                match_log.append({
                    'code': code,
                    'pom': pm.codi_client,
                    'match_type': match_type,
                })
                poms_created += 1

            return Response({
                'model_id': model.id,
                'model_codi': model.codi_intern,
                'poms_created': poms_created,
                'poms_skipped': poms_skipped,
                'match_log': match_log,
                'size_run': model.size_run_model,
                'message': (
                    f'Model creat. {poms_created} POMs importats, '
                    f'{len(poms_skipped)} pendents de revisió manual.'
                ),
            }, status=201)

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error creant model des d'extracció")
        return Response({'error': str(e)}, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_model_view(request, model_id):
    """
    DELETE /api/v1/models/<id>/delete/
    Esborra el model i totes les dades associades en cascada:
    BaseMeasurements, SizeFittings, GradingVersions, GradedSpecs,
    ModelFitxers (fitxers físics inclosos), POMAlerts, ModelTasques.
    """
    from django.core.files.storage import default_storage
    from fhort.models_app.models import Model, ModelFitxer

    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    nom = model.nom_prenda
    codi = model.codi_intern

    # Esborrar fitxers físics associats (no bloquejar si falla)
    try:
        for fitxer in ModelFitxer.objects.filter(model=model):
            if fitxer.fitxer and default_storage.exists(fitxer.fitxer.name):
                default_storage.delete(fitxer.fitxer.name)
    except Exception:
        pass

    # Esborrar el model (cascada BD)
    model.delete()

    return Response({
        'deleted': True,
        'model_id': model_id,
        'nom': nom,
        'codi': codi,
        'message': f'Model "{nom}" ({codi}) esborrat correctament.',
    })
