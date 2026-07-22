"""
Robustesa d'extracció IA — parse tolerant de respostes LLM.

Principi: degradació amb gràcia, mai petar. Les respostes de la IA poden venir amb
fences markdown, prosa abans/després, comes finals o el·lipsis. safe_json_parse extreu
el JSON real i tolera aquests defectes; salvage_measurements recupera files POM una a una
quan el JSON global no parseja (perquè una cel·la de grading malformada no s'emporti els POMs).
"""
import json
import logging as _logging
import re


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith('```'):
        s = s.split('\n', 1)[1] if '\n' in s else s[3:]
    if s.endswith('```'):
        s = s.rsplit('```', 1)[0]
    return s.strip()


def _extract_balanced(s: str):
    """Retorna el primer valor JSON balancejat ({...} o [...]), respectant strings/escapes."""
    start = None
    opener = None
    for i, ch in enumerate(s):
        if ch in '{[':
            start, opener = i, ch
            break
    if start is None:
        return None
    closer = '}' if opener == '{' else ']'
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    return None  # sense tancament aparellat (truncat)


def _cleanup(s: str) -> str:
    # comes finals abans de } o ]
    s = re.sub(r',(\s*[}\]])', r'\1', s)
    # el·lipsis com a "valor" → null
    s = re.sub(r':\s*\.{3}', ': null', s)
    s = s.replace('…', '')
    # NaN/Infinity (no són JSON vàlid)
    s = re.sub(r'\bNaN\b', 'null', s)
    s = re.sub(r'\b-?Infinity\b', 'null', s)
    return s


def safe_json_parse(text):
    """
    Parse tolerant. Retorna l'objecte parsejat o llança ValueError amb missatge clar.
    Tolera: fences markdown, prosa al voltant, comes finals, el·lipsis, NaN/Infinity.
    """
    if not text or not text.strip():
        raise ValueError('resposta buida')
    s = _strip_fences(text)

    # 1) intent directe
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 2) primer valor JSON balancejat (descarta prosa abans/després)
    cand = _extract_balanced(s)
    if cand is not None:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            # 3) neteja (comes finals, el·lipsis, NaN) i reintent
            try:
                return json.loads(_cleanup(cand))
            except json.JSONDecodeError as e:
                raise ValueError(f'JSON invàlid després de sanejat: {e}')
    raise ValueError('no s\'ha trobat cap JSON vàlid a la resposta')


def _iter_top_objects(arr_text: str):
    """Itera els objectes {...} de primer nivell dins un text d'array."""
    depth = 0
    in_str = False
    esc = False
    start = None
    for i, ch in enumerate(arr_text):
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                yield arr_text[start:i + 1]
                start = None


def salvage_measurements(text):
    """
    Recupera files de `measurements` una a una quan el JSON global no parseja.
    Una cel·la malformada fa perdre NOMÉS la seva fila, no les altres. Retorna una
    llista (possiblement buida) d'objectes de mesura que sí parsegen.
    """
    if not text:
        return []
    s = _strip_fences(text)
    m = re.search(r'"measurements"\s*:\s*\[', s)
    if not m:
        return []
    arr = _extract_balanced(s[m.end() - 1:])  # comença al '['
    if not arr:
        # array truncat: agafa fins al final i recupera el que es pugui
        arr = s[m.end() - 1:]
    rows = []
    for obj_text in _iter_top_objects(arr):
        try:
            rows.append(json.loads(obj_text))
        except json.JSONDecodeError:
            try:
                rows.append(json.loads(_cleanup(obj_text)))
            except json.JSONDecodeError:
                continue  # fila irrecuperable → es descarta, la resta es conserva
    return rows


def registra_us_ia(*, cami, model_ia, usage=None, import_session=None, model=None,
                   created_by=None, ok=True, error=''):
    """Desa el cost d'UNA crida a l'API d'Anthropic. Mai peta el camí de negoci.

    Decisió Agus 2026-07-22: «tot usage es loggeja». `usage` és l'objecte `response.usage`
    del SDK o el dict `usage` del JSON cru (extraction_service va per httpx): s'accepten
    tots dos perquè el registre no depengui de com s'ha fet la crida.

    Envoltat d'un `except` ample a posta: un problema comptant tokens no pot tombar una
    extracció que ja s'ha pagat i que l'usuari està esperant. Si el registre falla, es
    queixa al log i el camí segueix.
    """
    def _t(nom):
        if usage is None:
            return 0
        v = usage.get(nom) if isinstance(usage, dict) else getattr(usage, nom, 0)
        return int(v or 0)

    try:
        from fhort.models_app.models import AIUsage
        return AIUsage.objects.create(
            cami=cami, model_ia=model_ia or '',
            import_session=import_session, model=model, created_by=created_by,
            input_tokens=_t('input_tokens'), output_tokens=_t('output_tokens'),
            cache_creation_tokens=_t('cache_creation_input_tokens'),
            cache_read_tokens=_t('cache_read_input_tokens'),
            ok=ok, error=(error or '')[:2000],
        )
    except Exception:
        _logging.getLogger(__name__).exception(
            f'No s\'ha pogut registrar l\'ús d\'IA ({cami}/{model_ia})')
        return None
