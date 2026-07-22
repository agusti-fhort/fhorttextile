"""
Sprint S17 — Technical-sheet import via the Anthropic API.

Two views:
- TechSheetExtractView: receives PDF/image → calls the Anthropic API → returns structured JSON.
  Does not create any Model — it is a preview step so the user can review/correct
  before confirming creation.
- TechSheetCreateModelView: receives the extracted data (already confirmed) + manual
  overrides → creates the Model and the BaseMeasurements in the current tenant.

Notes d'integració amb l'SDK Anthropic (per skill `claude-api`):
- Model: `claude-opus-4-7` (recomanat per al perfil del cas d'ús — extracció de
  documents complexos amb taules, gradings i layouts variats).
- Adaptive thinking (`thinking: {type: "adaptive"}`) + `effort: "high"` → millor
  detecció de gradings irregulars, versions superseded i ambigüitats.
- Prompt caching: l'instrucció llarga viatja al camp `system` amb `cache_control`.
  El llindar de caching a Opus 4.7 és 4096 tokens; el nostre prompt n'és uns 750
  (~3 KB), per sota → el cache no s'activa, però la marca queda preparada per quan
  el prompt creixi. El PDF/imatge va al `user` message (variable per request).
- max_tokens=16000 → suficient per a la resposta + tokens d'adaptive thinking
  (Opus 4.7 inclou thinking dins del límit de max_tokens).
"""

import base64
import datetime
import json
import logging
import re

import anthropic
from django.conf import settings
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .extraction_prompt import TECH_SHEET_EXTRACTION_PROMPT
from .extraction_utils import safe_json_parse, salvage_measurements

logger = logging.getLogger(__name__)

EXTRACT_MODEL = 'claude-opus-4-7'
MAX_TOKENS = 16000
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_CONTENT_TYPES = {
    'application/pdf', 'image/jpeg', 'image/png', 'image/webp',
}


class TechSheetExtractView(APIView):
    """
    POST /api/v1/models/extract-sheet/
    multipart/form-data: file=<PDF|JPG|PNG|WEBP>

    Return structured JSON (`_meta` field added for the frontend).
    Does not create any Model.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        if file.content_type not in ALLOWED_CONTENT_TYPES:
            return Response(
                {'error': f'Tipus de fitxer no suportat: {file.content_type}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file.size > MAX_FILE_SIZE_BYTES:
            return Response(
                {'error': 'Fitxer massa gran (màxim 20MB)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
        if not api_key:
            return Response(
                {'error': 'ANTHROPIC_API_KEY no configurada al backend'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        file_b64 = base64.standard_b64encode(file.read()).decode('utf-8')
        if file.content_type == 'application/pdf':
            source_block = {
                'type': 'document',
                'source': {
                    'type': 'base64',
                    'media_type': 'application/pdf',
                    'data': file_b64,
                },
            }
        else:
            source_block = {
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': file.content_type,
                    'data': file_b64,
                },
            }

        try:
            client = anthropic.Anthropic(api_key=api_key)

            response = client.messages.create(
                model=EXTRACT_MODEL,
                max_tokens=MAX_TOKENS,
                thinking={'type': 'adaptive'},
                output_config={'effort': 'high'},
                # Stable prompt in `system` with cache_control. On Opus 4.7 the
                # minimum for caching is 4096 tokens; our prompt is ~750.
                # The marker does no harm and activates automatically if it grows.
                system=[
                    {
                        'type': 'text',
                        'text': TECH_SHEET_EXTRACTION_PROMPT,
                        'cache_control': {'type': 'ephemeral'},
                    },
                ],
                messages=[{
                    'role': 'user',
                    'content': [source_block],
                }],
            )

            response_text = ''.join(
                block.text for block in response.content
                if getattr(block, 'type', None) == 'text'
            ).strip()

            # FASE 1 · Robustesa: parse tolerant. Un grading malformat MAI ha de tombar els POMs.
            # Si el JSON global no parseja, recuperem les files de mesures una a una (salvage):
            # els POMs i la base es conserven encara que el grading vingui brut.
            grading_status = {'status': 'ok', 'detail': ''}
            try:
                extracted = safe_json_parse(response_text)
            except ValueError as e:
                logger.warning(f'extract-sheet: JSON global invàlid, intentant salvage. {e}')
                salvaged = salvage_measurements(response_text)
                if not salvaged:
                    # Ni amb salvage no hi ha POMs → això sí és un error dur (no hi ha res a mostrar).
                    return Response(
                        {'error': 'La IA no ha retornat dades llegibles', 'detail': str(e)},
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    )
                extracted = {'measurements': salvaged}
                grading_status = {
                    'status': 'error',
                    'detail': f'JSON global malformat; recuperats {len(salvaged)} POMs per fila. '
                              f'Grading no fiable, entra\'l després. ({e})',
                }

            # Structured errors the model emits (OUT_OF_SCOPE, NOT_A_TECH_SHEET).
            if isinstance(extracted, dict) and 'error' in extracted and len(extracted) <= 2:
                return Response(extracted, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            measurements = extracted.get('measurements', []) or []

            # grading_status quan el parse ha anat bé: hi ha grading multi-talla al document?
            if grading_status['status'] == 'ok':
                multi = [m for m in measurements
                         if len([v for v in (m.get('values') or {}).values() if v is not None]) >= 2]
                if not multi:
                    grading_status = {'status': 'skipped',
                                      'detail': 'Sense graella de grading multi-talla al document.'}
            valid_measurements = [
                m for m in measurements
                if any(v is not None for v in (m.get('values') or {}).values())
            ]

            blocking_reasons = []
            if not extracted.get('garment_type_code'):
                blocking_reasons.append('Tipus de prenda no identificat')
            if len(valid_measurements) < 3:
                blocking_reasons.append(f'Mesures insuficients ({len(valid_measurements)}/3 mínimes)')
            if not extracted.get('base_size'):
                blocking_reasons.append('Talla base no identificada')

            extracted['_meta'] = {
                'can_create_model': len(blocking_reasons) == 0,
                'valid_measurements_count': len(valid_measurements),
                'total_measurements_count': len(measurements),
                'high_confidence_count': sum(
                    1 for m in measurements if m.get('pom_confidence') == 'HIGH'
                ),
                'needs_review_count': sum(
                    1 for m in measurements
                    if m.get('pom_confidence') in ('LOW', 'CUSTOM')
                ),
                'blocking_reasons': blocking_reasons,
                # FASE 1 — estat del grading (no bloquejant): ok | skipped | error.
                'grading_status': grading_status,
                # Token telemetry — useful for cost monitoring and future cache-hit
                # validation (cache_read_input_tokens > 0 ⇒ cache works).
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                    'cache_creation_input_tokens': getattr(response.usage, 'cache_creation_input_tokens', 0),
                    'cache_read_input_tokens': getattr(response.usage, 'cache_read_input_tokens', 0),
                },
            }
            # També top-level perquè el front el llegeixi fàcil.
            extracted['grading_status'] = grading_status
            return Response(extracted)

        except anthropic.RateLimitError as e:
            return Response(
                {'error': 'API Anthropic — límit de ràtio. Reintenta més tard.', 'detail': str(e)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except anthropic.APIStatusError as e:
            logger.exception('Anthropic API status error')
            return Response(
                {'error': f'API Anthropic error {e.status_code}', 'detail': str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except anthropic.APIError as e:
            logger.exception('Anthropic APIError')
            return Response(
                {'error': 'Error API Anthropic', 'detail': str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.exception('Unexpected error in TechSheetExtractView')
            return Response(
                {'error': 'Error inesperat', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TechSheetCreateModelView(APIView):
    """
    POST /api/v1/models/create-from-sheet/
    body: { extracted: {...}, overrides: {garment_type_code?, pom_mappings?{}} }

    Create the Model and the BaseMeasurements in the current tenant. Skips
    low-confidence measurements that the user has not overridden.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        extracted = data.get('extracted')
        overrides = data.get('overrides') or {}

        if not extracted:
            return Response({'error': 'No extracted data provided'}, status=status.HTTP_400_BAD_REQUEST)

        meta = extracted.get('_meta') or {}
        if not meta.get('can_create_model'):
            return Response(
                {'error': 'No es pot crear el model', 'reasons': meta.get('blocking_reasons', [])},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # django-tenants already puts us in the correct schema via connection — no schema_context needed.
        from fhort.pom.models import GarmentType, POMMaster
        from fhort.models_app.models import BaseMeasurement, Model

        gt_code = overrides.get('garment_type_code') or extracted.get('garment_type_code')
        try:
            garment_type = GarmentType.objects.get(codi_client=gt_code)
        except GarmentType.DoesNotExist:
            return Response(
                {'error': f'GarmentType no trobat al tenant: {gt_code}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        header = extracted.get('header') or {}

        # Fix 1 (S17): the AI may return `sizes` as a string (e.g. "['XXS','XS','S']")
        # or as a clean array. We normalize to a clean list of strings before join.
        raw_sizes = extracted.get('sizes') or []
        if isinstance(raw_sizes, str):
            raw_sizes = re.findall(r'[A-Za-z0-9]+', raw_sizes)
        # PORTA ÚNICA DEL RUN (llei S24b). ⚠️ Aquest flux crea el Model SENSE `size_system`
        # assignat (vegeu el `Model.objects.create` de sota: no hi ha camp size_system), i per
        # tant no hi ha res contra què ordenar: `run_del_model` degrada amb gràcia i conserva
        # l'ordre del document, només deduplicant. És deliberat — un import legacy no s'ha de
        # petar per una llei que aquí no es pot aplicar. Queda ANOTAT: el dia que aquest camí
        # assigni SizeSystem, el run s'ordenarà sol sense tocar aquesta línia.
        from fhort.pom.grading_utils import run_del_model
        _run, _ = run_del_model([str(s).strip() for s in raw_sizes], None)
        size_run = '·'.join(_run)

        # NOT NULL Model fields the view must fill explicitly:
        # - any: taken from the header (`year`) or, by default, the current year.
        # - sequencial=1: the Model's pre_save signal recomputes the real
        #   sequential per tenant+any+temporada; a valid initial value is needed
        #   to satisfy the NOT NULL constraint before the signal.
        try:
            year_value = int(header.get('year') or datetime.date.today().year)
        except (TypeError, ValueError):
            year_value = datetime.date.today().year

        from fhort.models_app.services import get_self_customer
        model = Model.objects.create(
            nom_prenda=header.get('style_name') or 'Model importat',
            codi_client=header.get('style_reference') or '',
            # customer → self-customer (sense selector en aquest flux); el signal genera
            # codi_intern i codi_tenant a partir del seu codi.
            customer=get_self_customer(),
            temporada=header.get('season') or 'SS',
            any=year_value,
            sequencial=1,
            garment_type=garment_type,
            estat='Nou',
            fase_actual='Proto',
            base_size_label=extracted.get('base_size') or '',
            size_run_model=size_run,
            observacions=(
                f"Importat de fitxa: {header.get('style_reference', '')} | "
                f"Proveïdor: {header.get('supplier', '')} | "
                f"Data: {header.get('date', '')}"
            ),
        )

        user_mappings = overrides.get('pom_mappings') or {}
        measurements = extracted.get('measurements') or []
        created_bm = 0
        skipped = []
        base_size = extracted.get('base_size') or ''

        for m in measurements:
            client_code = m.get('client_code')
            pom_code = user_mappings.get(client_code) or m.get('pom_code')
            confidence = m.get('pom_confidence', 'LOW')

            # Skip low confidences the user has not confirmed.
            if not pom_code or (confidence in ('LOW', 'CUSTOM') and client_code not in user_mappings):
                skipped.append({
                    'client_code': client_code,
                    'description': m.get('description'),
                    'reason': 'Confiança baixa — requereix revisió manual',
                })
                continue

            # Fix 2 (S17): pom_global is not unique on POMMaster (a tenant may
            # have custom variants of the same POMGlobal). We use
            # .filter().first() to avoid MultipleObjectsReturned and log
            # any miss in `skipped`.
            pom_master = (
                POMMaster.objects
                .select_related('pom_global')
                .filter(pom_global__codi=pom_code)
                .first()
            )
            if pom_master is None:
                skipped.append({
                    'client_code': client_code,
                    'reason': f'POM {pom_code} no trobat al catàleg del tenant',
                })
                continue

            values = m.get('values') or {}
            base_value = values.get(base_size)
            if base_value is None and values:
                base_value = next(iter(values.values()))

            BaseMeasurement.objects.get_or_create(
                model=model,
                pom=pom_master,
                defaults={
                    'base_value_cm': float(base_value or 0),
                    'nom_fitxa': client_code or '',
                    'origen': 'IMPORTED',
                    'notes': m.get('description', ''),
                    'is_active': True,
                    # Sprint 5B.1: copy tolerance from the catalogue POM.
                    'tolerancia_minus': pom_master.tolerancia_default_minus,
                    'tolerancia_plus': pom_master.tolerancia_default_plus,
                },
            )
            created_bm += 1

        return Response(
            {
                'model_id': model.id,
                'model_codi': model.codi_intern,
                'base_measurements_created': created_bm,
                'skipped': skipped,
                'message': (
                    f'Model creat. {created_bm} mesures importades, '
                    f'{len(skipped)} pendents de revisió.'
                ),
            },
            status=status.HTTP_201_CREATED,
        )
