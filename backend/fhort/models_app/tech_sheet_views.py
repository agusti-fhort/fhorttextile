"""
Sprint S17 — Importació de fitxes tècniques via API Anthropic.

Dues views:
- TechSheetExtractView: rep PDF/imatge → crida l'API Anthropic → retorna JSON estructurat.
  No crea cap Model — és una passa de previsualització perquè l'usuari revisi/corregeixi
  abans de confirmar la creació.
- TechSheetCreateModelView: rep les dades extretes (ja confirmades) + overrides
  manuals → crea el Model i les BaseMeasurements al tenant actual.

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

    Retorna JSON estructurat (camp `_meta` afegit per al frontend).
    No crea cap Model.
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
                # Prompt estable al `system` amb cache_control. A Opus 4.7 el
                # mínim per a caching és 4096 tokens; el nostre prompt n'és ~750.
                # La marca no fa cap mal i s'activa automàticament si creix.
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

            # Neteja markdown fences defensivament.
            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1] if '\n' in response_text else response_text[3:]
                response_text = response_text.rsplit('```', 1)[0].strip()

            try:
                extracted = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.exception('Anthropic returned non-JSON response')
                return Response(
                    {'error': 'La IA no ha retornat JSON vàlid', 'detail': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Errors estructurats que el model emet (OUT_OF_SCOPE, NOT_A_TECH_SHEET).
            if isinstance(extracted, dict) and 'error' in extracted and len(extracted) <= 2:
                return Response(extracted, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            measurements = extracted.get('measurements', []) or []
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
                # Telemetria de tokens — útil per monitoring de costos i validació
                # de cache hits a futur (cache_read_input_tokens > 0 ⇒ cache va).
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                    'cache_creation_input_tokens': getattr(response.usage, 'cache_creation_input_tokens', 0),
                    'cache_read_input_tokens': getattr(response.usage, 'cache_read_input_tokens', 0),
                },
            }
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

    Crea el Model i les BaseMeasurements al tenant actual. Salta mesures amb
    confiança baixa que l'usuari no ha sobreescrit.
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

        # django-tenants ja ens posa al schema correcte via connection — no cal schema_context.
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

        # Fix 1 (S17): la IA pot retornar `sizes` com a string (ex: "['XXS','XS','S']")
        # o com a array net. Normalitzem a llista d'strings nets abans de join.
        raw_sizes = extracted.get('sizes') or []
        if isinstance(raw_sizes, str):
            raw_sizes = re.findall(r'[A-Za-z0-9]+', raw_sizes)
        size_run = '·'.join(
            str(s).strip() for s in raw_sizes if str(s).strip()
        )

        # Camps NOT NULL del Model que el view ha d'omplir explícitament:
        # - any: extret del header (`year`) o, defectivament, l'any actual.
        # - sequencial=1: el signal pre_save del Model recalcula el correlatiu
        #   real per tenant+any+temporada; cal un valor inicial vàlid per
        #   satisfer el constraint NOT NULL abans del signal.
        try:
            year_value = int(header.get('year') or datetime.date.today().year)
        except (TypeError, ValueError):
            year_value = datetime.date.today().year

        model = Model.objects.create(
            nom_prenda=header.get('style_name') or 'Model importat',
            codi_client=header.get('style_reference') or '',
            codi_tenant=(header.get('style_reference') or 'IMP')[:3].upper(),
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

            # Salta confiances baixes que l'usuari no ha confirmat.
            if not pom_code or (confidence in ('LOW', 'CUSTOM') and client_code not in user_mappings):
                skipped.append({
                    'client_code': client_code,
                    'description': m.get('description'),
                    'reason': 'Confiança baixa — requereix revisió manual',
                })
                continue

            # Fix 2 (S17): pom_global no és unique a POMMaster (un tenant pot
            # tenir variants personalitzades del mateix POMGlobal). Usem
            # .filter().first() per evitar MultipleObjectsReturned i loguem
            # qualsevol miss al `skipped`.
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
