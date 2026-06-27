"""
fhort/models_app/extraction_service.py
Technical-sheet data extraction service via the Claude API.
"""
from __future__ import annotations
import json
import base64
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Ets un sistema especialitzat en extracció de dades de fitxes tècniques de moda.
Analitzes documents (PDF, imatge, Excel) i retornes un JSON estructurat.

Instruccions generals:
- Extreu TOTS els camps que puguis identificar amb seguretat.
- Per a cada camp indica la confiança: "high" | "medium" | "low".
- Si un camp no apareix al document, retorna null (no inventis valors).
- Els codis de POM (punts de mesura) sempre en format original del client (ex: B, E, L.3, D1, G1...).
- Les mesures sempre en CM amb 1 decimal.
- Si detectes un dibuix tècnic amb POMs etiquetats amb fletxes, extreu els codis visibles.
- Si el document és un sketch manuscrit, indica document_type = "sketch_manual".
- Si detectes un dibuix tècnic de la peça, descriu-lo breument a thumbnail_description (max 50 paraules, en anglès).

Retorna ÚNICAMENT el JSON següent sense cap text addicional ni markdown:

{
  "document_type": "plm_export|tech_pack_pdf|measurement_sheet|fit_comments|grading_table|sketch_manual|unknown",
  "brand": {"value": null, "confidence": "high"},
  "supplier": {"value": null, "confidence": "high"},
  "style_code": {"value": null, "confidence": "high"},
  "style_name": {"value": null, "confidence": "high"},
  "season": {"value": null, "confidence": "high"},
  "year": {"value": null, "confidence": "high"},
  "designer": {"value": null, "confidence": "high"},
  "patternmaker": {"value": null, "confidence": "high"},
  "garment_type": {"value": null, "confidence": "high"},
  "garment_description": {"value": null, "confidence": "high"},
  "main_fabric": {"value": null, "confidence": "high"},
  "fabric_composition": {"value": null, "confidence": "high"},
  "colorway": {"value": null, "confidence": "high"},
  "base_size": {"value": null, "confidence": "high"},
  "size_run": {"value": null, "confidence": "high"},
  "has_grading_table": false,
  "has_base_only": false,
  "poms": [
    {"code": "B", "description": "CHEST WIDTH (1/2)", "base_value_cm": 22.5, "tolerance_minus": 0.5, "tolerance_plus": 0.5, "confidence": "high"}
  ],
  "grading_table": [
    {"code": "B", "values_by_size": {"S": 22.5, "M": 23.5}, "tolerance_minus": 0.5, "tolerance_plus": 0.5}
  ],
  "fit_comments": [
    {"title": "Hip Width Adjustment", "description": "Increase hip width by +2cm", "pom_affected": "E", "delta_cm": 2.0, "confidence": "high"}
  ],
  "construction_notes": [],
  "has_technical_drawing": false,
  "pom_codes_on_drawing": [],
  "thumbnail_description": null,
  "anomalies_detected": [],
  "design_freeze_blockers": []
}

Regles de Design Freeze — afegeix a design_freeze_blockers si manca:
- style_name o style_code
- garment_type
- base_size
- main_fabric
- almenys 3 POMs amb base_value_cm (o has_grading_table=true)

Afegeix a anomalies_detected (no bloquejant):
- size_run buit quan has_grading_table=true
- toleràncies no definides
- fabric_composition sense percentatge
- POMs visibles al dibuix però sense valor a la taula"""


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-opus-4-5"


def _get_api_key() -> str:
    from django.conf import settings
    key = getattr(settings, 'ANTHROPIC_API_KEY', None)
    if not key:
        import os
        key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        raise ValueError("ANTHROPIC_API_KEY no configurat a settings o variables d\'entorn")
    return key


def _file_to_content_block(file_bytes: bytes, filename: str) -> dict:
    """Convert a file into a content block for the Claude API."""
    ext = Path(filename).suffix.lower()

    if ext == '.pdf':
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.b64encode(file_bytes).decode()
            }
        }
    elif ext in ('.png', '.jpg', '.jpeg', '.webp', '.gif'):
        media_map = {'.png': 'image/png', '.jpg': 'image/jpeg',
                     '.jpeg': 'image/jpeg', '.webp': 'image/webp',
                     '.gif': 'image/gif'}
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_map.get(ext, 'image/jpeg'),
                "data": base64.b64encode(file_bytes).decode()
            }
        }
    else:
        # Fallback: try as text
        try:
            text = file_bytes.decode('utf-8', errors='replace')
            return {"type": "text", "text": f"Contingut del fitxer {filename}:\n{text[:8000]}"}
        except Exception:
            raise ValueError(f"Format de fitxer no suportat: {ext}")


def extract_from_file(file_bytes: bytes, filename: str, wizard_context: dict | None = None) -> dict:
    """
    Send the file to the Claude API and return the extraction JSON.

    wizard_context: optional dict with target, garment_type, size_system,
    size_run, base_size, construction, fit_type — coming from the wizard
    before the file upload.
    """
    from fhort.models_app.extraction_prompt import build_extraction_prompt

    api_key = _get_api_key()

    content_block = _file_to_content_block(file_bytes, filename)
    prompt_text = build_extraction_prompt(wizard_context) + EXTRACTION_PROMPT

    payload = {
        "model": MODEL,
        "max_tokens": 8192,
        "messages": [
            {
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": prompt_text}
                ]
            }
        ]
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "anthropic-beta": "pdfs-2024-09-25"
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(f"Claude API HTTP error: {e.response.status_code} — {e.response.text[:300]}")
        raise ValueError(f"Error de la API de Claude: {e.response.status_code}")
    except httpx.TimeoutException:
        raise ValueError("Timeout en la crida a la API de Claude (>120s)")

    data = response.json()
    raw_text = data['content'][0]['text']

    # Parse tolerant (fences markdown, prosa al voltant, comes finals, el·lipsis).
    from fhort.models_app.extraction_utils import safe_json_parse
    try:
        result = safe_json_parse(raw_text)
    except ValueError as e:
        logger.error(f"JSON inválid de Claude: {raw_text[:300]}")
        raise ValueError(f"La resposta de Claude no és JSON vàlid: {e}")

    return result


def check_design_freeze(extracted: dict) -> dict:
    """
    Validate the required fields for the Design Freeze gate.
    Return {"pass": bool, "blockers": [...], "warnings": [...]}
    """
    blockers = list(extracted.get('design_freeze_blockers', []))
    warnings = list(extracted.get('anomalies_detected', []))

    # Additional local validations
    def val(field):
        v = extracted.get(field)
        if isinstance(v, dict):
            return v.get('value')
        return v

    if not val('style_name') and not val('style_code'):
        if 'Nom o codi de model no identificat' not in blockers:
            blockers.append('Nom o codi de model no identificat')

    if not val('garment_type'):
        if 'Tipus de prenda no identificat' not in blockers:
            blockers.append('Tipus de prenda no identificat')

    if not val('base_size'):
        if 'Talla base no identificada' not in blockers:
            blockers.append('Talla base no identificada')

    if not val('main_fabric'):
        if 'Material principal no identificat' not in blockers:
            blockers.append('Material principal no identificat')

    poms = extracted.get('poms', [])
    has_grading = extracted.get('has_grading_table', False)
    poms_with_value = [p for p in poms if p.get('base_value_cm') is not None]
    if len(poms_with_value) < 3 and not has_grading:
        if 'Mínim 3 POMs amb mesures de talla base requerits' not in blockers:
            blockers.append('Mínim 3 POMs amb mesures de talla base requerits')

    return {
        "pass": len(blockers) == 0,
        "blockers": blockers,
        "warnings": warnings,
    }
