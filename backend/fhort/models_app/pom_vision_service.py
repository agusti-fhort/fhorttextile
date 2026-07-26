"""F3 · PROPOSTA de col·locació de cotes POM amb IA de visió (D5: SYNC amb guards).

Règim INFORMATIU de la fitxa: la IA POT proposar ON va una cota (extrems + etiqueta sobre
la bbox de l'objecte sketch), MAI QUANT — el valor viu a la taula, la cota només diu on. Tota
proposta passa per revisió humana (cap autoescriptura). Ometre és CORRECTE: una cota dubtosa
va a `skip`, mai s'inventa.

Reutilitza el client existent (httpx cru a l'API de Missatges, com `extraction_service`), el
parser tolerant (`safe_json_parse`) i el ledger d'ús (`registra_us_ia` → AIUsage, camí
`proposta_cotes`). NO introdueix cap SDK ni cap segona taula d'usage.
"""
import base64
import io
import logging

import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
# PROVISIONAL — pendent benchmark F0. Swap d'una sola línia quan es decideixi el model definitiu.
MODEL_VISIO_COTES = "claude-sonnet-4-6"

# Guards de la crida (D5): límits amb nom, afinables.
TIMEOUT_S = 90.0            # timeout explícit al transport (visió pot trigar segons, no ms)
MAX_COSTAT_LLARG_PX = 1600  # downscale si el costat llarg supera això (menys tokens d'imatge)
MAX_TOKENS = 4096           # sostre de sortida raonable per a un JSON de propostes


def _get_api_key() -> str:
    from django.conf import settings
    key = getattr(settings, 'ANTHROPIC_API_KEY', None)
    if not key:
        import os
        key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        raise ValueError("ANTHROPIC_API_KEY no configurat")
    return key


def _dataurl_to_png_block(page_image: str) -> dict:
    """dataURL PNG → content block d'imatge base64, fent downscale si el costat llarg és gran.

    Accepta `data:image/png;base64,...` o base64 nu. Retorna sempre PNG (el llenç l'exporta així).
    """
    raw = page_image.split(',', 1)[1] if page_image.startswith('data:') else page_image
    img_bytes = base64.b64decode(raw)
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(img_bytes))
        w, h = im.size
        llarg = max(w, h)
        if llarg > MAX_COSTAT_LLARG_PX:
            f = MAX_COSTAT_LLARG_PX / llarg
            im = im.resize((max(1, round(w * f)), max(1, round(h * f))))
            buf = io.BytesIO()
            im.save(buf, format='PNG')
            img_bytes = buf.getvalue()
    except Exception:
        # Si PIL falla, s'envia la imatge tal com ha arribat: mai bloquejar per un downscale.
        logger.warning("pom_vision: downscale fallit; s'envia la imatge original", exc_info=True)
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png",
                   "data": base64.b64encode(img_bytes).decode()},
    }


def _build_prompt(sketches: list, poms: list) -> str:
    import json
    sk = json.dumps(sketches, ensure_ascii=False)
    pm = json.dumps(poms, ensure_ascii=False)
    return f"""Ets un assistent de patronatge tècnic. A la imatge hi ha una pàgina d'una fitxa amb
un o més CROQUIS (sketches) de la peça. Has de PROPOSAR on col·locar les cotes de mesura (POM)
sobre els croquis: cada cota és una fletxa de doble punta entre dos extrems (A→B) amb una
etiqueta. NOMÉS dius ON va la cota, MAI quant mesura.

OBJECTES SKETCH de la pàgina (amb la seva bounding box normalitzada 0..1 respecte de la IMATGE,
i la vista si es coneix):
{sk}

POMs a col·locar (pendents; codi i nom per identificar-los al croquis):
{pm}

REGLES DURES:
- Proposa NOMÉS les cotes que vegis CLARES al croquis. Les dubtoses van a "skip" (ometre és
  correcte i preferible a inventar). No forcis una col·locació que no veus.
- Les coordenades x1,y1,x2,y2 i label_x,label_y són 0..1 RELATIVES A LA BOUNDING BOX DE
  L'OBJECTE `object_id` on ancores la cota (NO respecte de la pàgina ni de la imatge).
- Cada proposta ha de referir un `pom_id` de la llista i un `object_id` dels sketches.
- `confidence`: "alta" si l'extrem és inequívoc, "mitjana" si és una lectura raonable però no
  segura.

Respon NOMÉS amb JSON, sense text ni fences:
{{"placements": [{{"pom_id": <int>, "object_id": "<str>", "x1": <0..1>, "y1": <0..1>,
"x2": <0..1>, "y2": <0..1>, "label_x": <0..1>, "label_y": <0..1>, "view": "<str|null>",
"confidence": "alta"|"mitjana"}}], "skip": [<pom_id>, ...]}}"""


def proposar_cotes(*, page_image: str, sketches: list, poms: list,
                   model=None, created_by=None) -> dict:
    """Crida de visió SYNC. Retorna {placements, skip, usage}. Llança ValueError en error net
    (el view el tradueix a 502). L'ús es registra sempre (ok o error) al ledger d'AIUsage.
    """
    api_key = _get_api_key()
    payload = {
        "model": MODEL_VISIO_COTES,
        "max_tokens": MAX_TOKENS,
        "messages": [{
            "role": "user",
            "content": [
                _dataurl_to_png_block(page_image),
                {"type": "text", "text": _build_prompt(sketches, poms)},
            ],
        }],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    from fhort.models_app.extraction_utils import registra_us_ia, safe_json_parse
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            response = client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(f"pom_vision HTTP {e.response.status_code}: {e.response.text[:300]}")
        registra_us_ia(cami='proposta_cotes', model_ia=MODEL_VISIO_COTES, model=model,
                       created_by=created_by, ok=False, error=f'HTTP {e.response.status_code}')
        raise ValueError(f"Error de la IA de visió: {e.response.status_code}")
    except httpx.TimeoutException:
        registra_us_ia(cami='proposta_cotes', model_ia=MODEL_VISIO_COTES, model=model,
                       created_by=created_by, ok=False, error=f'timeout >{TIMEOUT_S}s')
        raise ValueError(f"Timeout en la crida de visió (>{TIMEOUT_S:.0f}s)")

    data = response.json()
    try:
        raw = data['content'][0]['text']
        result = safe_json_parse(raw)
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"pom_vision: resposta no és JSON vàlid: {str(data)[:300]}")
        registra_us_ia(cami='proposta_cotes', model_ia=MODEL_VISIO_COTES, model=model,
                       created_by=created_by, usage=data.get('usage'), ok=False,
                       error=f'parse: {e}')
        raise ValueError("La resposta de la IA no és JSON vàlid")

    placements = result.get('placements') or []
    skip = result.get('skip') or []
    registra_us_ia(cami='proposta_cotes', model_ia=MODEL_VISIO_COTES, model=model,
                   created_by=created_by, usage=data.get('usage'),
                   n_proposades=len(placements), n_skip=len(skip))
    return {'placements': placements, 'skip': skip,
            'usage': data.get('usage'), 'model': MODEL_VISIO_COTES}
