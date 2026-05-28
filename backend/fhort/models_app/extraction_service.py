"""
fhort/models_app/extraction_service.py
Servei d\'extracció de dades de fitxes tècniques via Claude API.
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
    """Converteix un fitxer en un bloc de contingut per a la Claude API."""
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
        # Fallback: intenta com a text
        try:
            text = file_bytes.decode('utf-8', errors='replace')
            return {"type": "text", "text": f"Contingut del fitxer {filename}:\n{text[:8000]}"}
        except Exception:
            raise ValueError(f"Format de fitxer no suportat: {ext}")


def extract_from_file(file_bytes: bytes, filename: str, wizard_context: dict | None = None) -> dict:
    """
    Envia el fitxer a la Claude API i retorna el JSON d\'extracció.

    wizard_context: dict opcional amb target, garment_type, size_system,
    size_run, base_size, construction, fit_type — provinents del wizard
    abans de la pujada de fitxer.
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

    # Netejar possibles backticks de markdown
    raw_text = raw_text.strip()
    if raw_text.startswith('```'):
        raw_text = raw_text.split('\n', 1)[1] if '\n' in raw_text else raw_text[3:]
    if raw_text.endswith('```'):
        raw_text = raw_text.rsplit('```', 1)[0]

    try:
        result = json.loads(raw_text.strip())
    except json.JSONDecodeError as e:
        logger.error(f"JSON inválid de Claude: {raw_text[:300]}")
        raise ValueError(f"La resposta de Claude no és JSON vàlid: {e}")

    return result


def check_design_freeze(extracted: dict) -> dict:
    """
    Valida els camps obligatoris per al gate de Design Freeze.
    Retorna {"pass": bool, "blockers": [...], "warnings": [...]}
    """
    blockers = list(extracted.get('design_freeze_blockers', []))
    warnings = list(extracted.get('anomalies_detected', []))

    # Validacions addicionals locals
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


def extract_images_from_pdf(pdf_bytes: bytes, codi_intern: str) -> list:
    """
    Extreu imatges d'un PDF usant pymupdf.
    Retorna llista de dicts amb metadades i bytes.
    No guarda res — el caller decideix què fer.
    """
    try:
        import fitz
    except ImportError:
        return []

    results = []
    counters = {}

    def next_num(tipus):
        counters[tipus] = counters.get(tipus, 0) + 1
        return f'{counters[tipus]:03d}'

    try:
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    except Exception:
        return []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # MÈTODE 1: Imatges incrustades (fotos, logos)
        try:
            images = page.get_images(full=True)
            for img in images:
                try:
                    xref = img[0]
                    base_img = doc.extract_image(xref)
                    w = base_img.get('width', 0)
                    h = base_img.get('height', 0)
                    if w < 150 or h < 150:
                        continue
                    ext = base_img['ext']
                    tipus = 'sketch'
                    nom = f'{codi_intern}_{tipus}_{next_num(tipus)}.{ext}'
                    results.append({
                        'nom': nom,
                        'tipus': tipus,
                        'categoria': 'Disseny',
                        'pagina': page_num + 1,
                        'origen': 'INCRUSTADA',
                        'amplada': w,
                        'alcada': h,
                        'ext': ext,
                        'bytes': base_img['image'],
                    })
                except Exception:
                    continue
        except Exception:
            pass

        # MÈTODE 2: Rasteritzar pàgines amb sketches vectorials
        try:
            paths = page.get_drawings()
            text = page.get_text()
            pom_patterns = ['B ', 'M ', 'E.', 'D.', 'L.', 'K ', 'A.', 'S.', 'T.']
            has_pom = sum(1 for p in pom_patterns if p in text) >= 3
            has_vectors = len(paths) > 15

            if has_vectors and has_pom:
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                tipus = 'sketch'
                nom = f'{codi_intern}_{tipus}_{next_num(tipus)}.png'
                results.append({
                    'nom': nom,
                    'tipus': tipus,
                    'categoria': 'Disseny',
                    'pagina': page_num + 1,
                    'origen': 'RASTERITZADA',
                    'amplada': pix.width,
                    'alcada': pix.height,
                    'ext': 'png',
                    'bytes': pix.tobytes('png'),
                })
        except Exception:
            pass

    doc.close()
    return results
