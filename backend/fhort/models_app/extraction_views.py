# fhort/models_app/extraction_views.py
import base64 as _base64
import datetime as _dt
import io as _io
import logging as _logging
import re as _re

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from fhort.pom.size_labels import canonical_size_label


def normalize_size_run(raw):
    """Convert any size_run format to 'XXS·XS·S·M·L·XL'."""
    if not raw:
        return ''
    if isinstance(raw, list):
        sizes = [str(s).strip() for s in raw if str(s).strip()]
    elif isinstance(raw, str):
        # Can be "['XXS', 'XS', 'S']" or "XXS,XS,S" or "XXS XS S"
        sizes = _re.findall(r'[A-Z0-9]+', raw.upper())
        # Filter out tokens that do not look like sizes
        sizes = [s for s in sizes if 1 <= len(s) <= 5]
    else:
        return ''
    return '·'.join(sizes)


def parse_any(raw):
    """Normalize the year to a 4-digit integer."""
    if not raw:
        return _dt.date.today().year
    try:
        y = int(str(raw).strip())
        if y < 100:
            y += 2000
        return y
    except (ValueError, TypeError):
        return _dt.date.today().year


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_model_view(request, model_id):
    """
    DELETE /api/v1/models/<id>/delete/
    Delete the model and all associated data in cascade:
    BaseMeasurements, SizeFittings, GradingVersions, GradedSpecs,
    ModelFitxers (physical files included), POMAlerts, ModelTasques.
    """
    from django.core.files.storage import default_storage
    from fhort.models_app.models import Model, ModelFitxer

    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    nom = model.nom_prenda
    codi = model.codi_intern

    # Delete associated physical files (do not block if it fails)
    try:
        for fitxer in ModelFitxer.objects.filter(model=model):
            if fitxer.fitxer and default_storage.exists(fitxer.fitxer.name):
                default_storage.delete(fitxer.fitxer.name)
    except Exception:
        pass

    # Delete the model (DB cascade)
    model.delete()

    return Response({
        'deleted': True,
        'model_id': model_id,
        'nom': nom,
        'codi': codi,
        'message': f'Model "{nom}" ({codi}) esborrat correctament.',
    })


# =====================================================================
# F2.2/F2.3 — Importació guiada per sessió (ImportSession)
# Crida 1: cribratge barat (tipologia, nº models, run de talles).
# =====================================================================

CRIBRATGE_MODEL = 'claude-opus-4-7'

# RETURN ONLY VALID JSON — cap prosa, cap markdown. Visió barata, sense thinking.
CRIBRATGE_PROMPT = """You are a fast triage system for fashion tech-sheet documents.
Look at the document and return ONLY a single valid JSON object. No prose, no markdown fences.

Detect, at a glance (do NOT extract measurements):
- How many INDEPENDENT garment models/styles the document contains (distinct style names or codes).
- The garment typology, in English (dress, trousers, shirt, skirt, jacket, pyjama...).
- The target gender/age segment.
- The size-run labels exactly as printed, in order.
- Which size system those labels belong to.

Return EXACTLY this shape:
{
  "num_models": <int>,
  "models_detectats": [{"nom": "<style name or code>", "pagina": <int>, "descripcio": "<short>"}],
  "tipologia_detectada": "<dress|trousers|shirt|skirt|...>",
  "genere_detectat": "<woman|man|unisex|baby|kids>",
  "run_talles_document": ["<label1>", "<label2>", "..."],
  "sistema_talles": "<letters|age_months|age_years|numeric|height_cm|unknown>"
}

Rules:
- num_models counts distinct styles/patterns. Two patterns on the same page = 2.
- Use the EXACT size labels printed in the document, preserving their order.
- letters = XS/S/M/L..., numeric = 34/36/38..., age_months = 0M/3M/6M..., age_years = 6Y/8Y...,
  height_cm = 50/56/62... (cm body height for baby/kids). If unsure, "unknown".
- Output ONLY the JSON object, nothing else."""


def _excel_to_text(file_bytes: bytes) -> str:
    """Converteix un .xlsx/.xls a text tabulat perquè la IA en llegeixi el contingut."""
    import openpyxl
    wb = openpyxl.load_workbook(_io.BytesIO(file_bytes), data_only=True, read_only=True)
    lines = []
    for ws in wb.worksheets:
        lines.append(f'### Full: {ws.title}')
        for row in ws.iter_rows(values_only=True):
            cells = ['' if c is None else str(c) for c in row]
            if any(cells):
                lines.append('\t'.join(cells))
    wb.close()
    return '\n'.join(lines)


# ═══════════════ Parser determinista d'Excel — perfil "spec sheet" ═══════════════
# QA-S8 · FIX C (DIAGNOSI_QA_S8_IMPORT §D1c). El parser anterior cercava el codi a la
# COLUMNA A i abdicava sempre que la taula no hi comencés — que és el cas de totes les
# fitxes reals que tenim (la taula Brownie viu de la B a la H i la columna A és buida de
# dalt a baix). Aquest perfil ancora la taula pel CONTINGUT de la capçalera i mapa les
# columnes per ETIQUETA, no per índex.

#: Etiquetes que ANCOREN la capçalera. La columna on viuen no importa: és el contingut
#: qui mana (D1c·1). Calen totes dues famílies a la mateixa fila per considerar-la capçalera.
_ETIQ_CODI = {'CODE', 'CODI', 'POM', 'POM CODE'}
_ETIQ_DESC = {'DESCRIPTION', 'DESCRIPCIO', 'DESCRIPCIÓ', 'DESC', 'ENGLISH'}

#: Columnes de SERVEI: tenen etiqueta però NO són talles (D1c·6). Sense aquesta llista,
#: 'SAMPLE', 'ADJUSTMENTS' i 'COMMENTS' entrarien com si fossin tres talles més.
_ETIQ_SERVEI = _ETIQ_CODI | _ETIQ_DESC | {
    'GRADING', 'DIM', 'SAMPLE', 'SAMPLE SIZE', 'ADJUSTMENTS', 'ADJUSTMENT',
    'COMMENTS', 'COMMENT', 'NOTES', 'NOTE', 'REMARKS', 'MEASUREMENT', 'MEASUREMENTS',
}

#: Una etiqueta de TALLA: lletres (S/M/L/XL/XXL/2XL), numèrica (34/36), edat (6M/8Y) o T2.
_RE_TALLA = _re.compile(r'^(?:X*[SL]|M|\d+X[SL]|\d{1,3}(?:[.,]\d{1,2})?|\d{1,2}\s*[MYA]|T\d{1,2})$',
                        _re.I)

#: Un CODI de POM: curt i sense espais interns (A, D, G1, EK2, U2, LZ1, SF). El que no hi
#: encaixa i seu a la columna del codi és un BANNER ('SKETCH WITH CODES'), no un POM (D1c·5).
_RE_CODI = _re.compile(r'^[A-Za-z0-9][A-Za-z0-9.\-/]{0,7}$')

#: Metadades del bloc superior (B2:B7 a la fitxa Brownie) → claus del `header`, les MATEIXES
#: que retorna la via Opus (extraction_prompt.py), perquè els dos camins parlin igual.
_META_HEADER = {
    'BRAND': 'brand',
    'NAME STYLE': 'style_name',
    'STYLE NAME': 'style_name',
    'STYLE': 'style_name',
    'COLOR': 'color',
    'COLOUR': 'color',
    'SEASON': 'season',
    'DATE': 'date',
    'STYLE NO': 'style_reference',
    'REF': 'style_reference',
    'REFERENCE': 'style_reference',
}

#: Files amb codi I valor a la talla base que calen per donar la taula per ENTESA. Per sota
#: d'això el parser abdica: tres files coherents són la prova mínima que hem trobat una taula
#: de mesures de debò i no un bloc qualsevol amb text a sobre.
_MIN_FILES_ENTESA = 3


def _num(v):
    """float si v és numèric (accepta coma decimal); None altrament."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().replace(',', '.'))
    except (ValueError, TypeError):
        return None


def _etiqueta(v):
    """Text d'una cel·la de capçalera, normalitzat per COMPARAR (majúscules, espais collapsats)."""
    if v is None:
        return ''
    return ' '.join(str(v).split()).upper()


def _valor_meta(v):
    """Valor d'una cel·la del bloc de metadades, com a text net."""
    if v is None:
        return ''
    if isinstance(v, _dt.datetime):
        return v.date().isoformat()
    if isinstance(v, _dt.date):
        return v.isoformat()
    return str(v).strip()


def _files_banner(ws, ci_codi):
    """Files (1-indexades) tapades per un bloc FUSIONAT ample — sketch, comentaris, peus.

    D1c·5 i bandera 4: la fitxa Brownie té `B39:H39` (el rètol 'SKETCH WITH CODES') i tres
    blocs grans (`B40:H67`, `B70:H97`, `B100:H127`). Un parser que no els talli recorre fins
    a la fila 127 i s'empassa el sketch com si fossin POMs. Un merge d'UNA columna (les
    capçaleres verticals `B9:B10`) NO és un banner: només compten els que travessen la taula.
    """
    banner = set()
    for rang in ws.merged_cells.ranges:
        ample = rang.max_col - rang.min_col + 1
        if ample >= 3 and rang.min_col <= ci_codi + 1 <= rang.max_col:
            banner.update(range(rang.min_row, rang.max_row + 1))
    return banner


def _parse_excel_poms(file_bytes: bytes, base_hint=None, run_hint=None):
    """Parse determinista d'una fitxa Excel de POMs (via ràpida del wizard).

    Retorna `(poms, talles, meta)`:
      poms  = [{'codi_fitxa', 'descripcio', 'dim', 'values': {talla: float}, 'tol_*'}]
      talles = [etiquetes de talla, en ordre de columna]
      meta  = {'header', 'base_size', 'full', 'n_files_amb_codi', 'motiu'}

    ⚠️ **PORTA D'ABDICACIÓ — la llei d'aquest parser** (DIAGNOSI_QA_S8_IMPORT, risc de D1c).
    El contracte del wizard és "si el parser no en treu res, cau a la IA". Un parser més
    llest però EQUIVOCAT ja no cau: substitueix la IA **en silenci** i escriu dades dolentes.
    Això és pitjor que el defecte que arregla. Per tant aquesta funció només retorna files
    quan pot DEMOSTRAR que ha entès la taula:

      1. capçalera ancorada per CONTINGUT — una fila amb una etiqueta de CODI *i* una de
         DESCRIPCIÓ (a la columna que sigui);
      2. columna de TALLA BASE identificada — el `SAMPLE SIZE` de les metadades (o el
         `base_hint` del model) ha de correspondre a una columna de talla REAL; i
      3. almenys `_MIN_FILES_ENTESA` files amb codi *i* valor numèric a aquella talla base.

    Si qualsevol de les tres falla, retorna `([], [], meta)` amb el motiu, i el caller cau
    a la IA **com fins ara**. La prova es fa full per full: en un llibre de diverses pestanyes
    guanya la primera que la passa (a la fitxa Rosalia això descarta 'PROTO COMMENTS' —que té
    la columna de la talla base BUIDA— i tria 'RECTI 1 COMMENTS', que és on hi ha les mesures).

    `meta['n_files_amb_codi']` és el nombre de files de POM que el document conté de debò.
    Serveix per al Fix D encara que s'abdiqui: si la IA en retorna menys, algú ho ha de dir
    (la fitxa del Tate té 26 POMs i la IA en va perdre un, 'JJ', sense cap avís).
    """
    import openpyxl

    meta = {'header': {}, 'base_size': None, 'full': None,
            'n_files_amb_codi': 0, 'motiu': 'cap full amb capçalera de POMs reconeixible'}
    run_canonic = {canonical_size_label(t) for t in (run_hint or []) if str(t).strip()}

    # read_only=False: els merges (D1c·3 i ·5) NO es poblen en mode read_only, i sense ells
    # no es poden ni compondre les capçaleres dobles ni tallar els blocs del sketch.
    wb = openpyxl.load_workbook(_io.BytesIO(file_bytes), data_only=True)
    try:
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))

            # ── 1. Ancorar la capçalera pel CONTINGUT (D1c·1): la fila que porta alhora una
            # etiqueta de codi i una de descripció. La columna on caiguin és la que sigui.
            header_idx = ci_codi = ci_desc = None
            for idx, row in enumerate(rows):
                codi_ci = desc_ci = None
                for ci, cell in enumerate(row):
                    et = _etiqueta(cell)
                    if codi_ci is None and et in _ETIQ_CODI:
                        codi_ci = ci
                    elif desc_ci is None and et in _ETIQ_DESC:
                        desc_ci = ci
                if codi_ci is not None and desc_ci is not None:
                    header_idx, ci_codi, ci_desc = idx, codi_ci, desc_ci
                    break
            if header_idx is None:
                continue

            # ── 2. Capçalera DOBLE amb merges (D1c·3). Els merges verticals (B9:B10) només
            # porten valor a la cel·la de dalt; les etiquetes NO fusionades de la segona fila
            # (C10='ENGLISH', F10='RECTI 1') són pròpies. Regla: mana la primera fila, la
            # segona només omple els buits.
            etiquetes = {ci: _etiqueta(c) for ci, c in enumerate(rows[header_idx])}
            if header_idx + 1 < len(rows):
                seguent = rows[header_idx + 1]
                if not _etiqueta(seguent[ci_codi] if ci_codi < len(seguent) else None):
                    for ci, cell in enumerate(seguent):
                        if not etiquetes.get(ci):
                            etiquetes[ci] = _etiqueta(cell)

            # ── 3. Mapa de columnes per ETIQUETA (D1c·2 i ·6). Una columna és de TALLA si té
            # etiqueta, no és de servei, no és de tolerància, i sembla una talla (o és al run
            # del model). Així 'SAMPLE', 'ADJUSTMENTS' i 'COMMENTS' es queden fora.
            size_cols, dim_ci = [], None
            tol_minus_ci = tol_plus_ci = tol_single_ci = None
            for ci, et in sorted(etiquetes.items()):
                if not et or ci in (ci_codi, ci_desc):
                    continue
                if 'TOL' in et:
                    # B2: les columnes de tolerància es capturen (tol_minus/tol_plus). Una sola
                    # columna 'Tol' sense signe → mateix valor als dos costats (simètrica).
                    if '-' in et or 'MIN' in et:
                        tol_minus_ci = ci
                    elif '+' in et or 'PLUS' in et or 'MAX' in et:
                        tol_plus_ci = ci
                    else:
                        tol_single_ci = ci
                    continue
                if et == 'DIM':
                    dim_ci = ci
                    continue
                if et in _ETIQ_SERVEI:
                    continue
                if _RE_TALLA.match(et) or canonical_size_label(et) in run_canonic:
                    # L'etiqueta que es desa és la del document tal com hi surt (l'etiqueta
                    # del tenant la posa el reconcile de W5); `et` és només per comparar.
                    crua = rows[header_idx][ci] if ci < len(rows[header_idx]) else None
                    size_cols.append((ci, str(crua).strip() if crua is not None else et))
            if not size_cols:
                meta['motiu'] = f"full '{ws.title}': cap columna de talla reconeguda"
                continue

            # ── 4. Bloc de metadades (B2:B7) — el bonus barat de D1c. Etiqueta a la columna del
            # codi, valor a la de la descripció. D'aquí surt el SAMPLE SIZE, que és qui diu quina
            # és la TALLA BASE del document (D1c·6): mai "la primera columna".
            header_meta = {}
            sample_size = None
            for row in rows[:header_idx]:
                clau = _etiqueta(row[ci_codi] if ci_codi < len(row) else None)
                valor = _valor_meta(row[ci_desc] if ci_desc < len(row) else None)
                if not clau or not valor:
                    continue
                if clau == 'SAMPLE SIZE':
                    sample_size = valor
                elif clau in _META_HEADER:
                    header_meta[_META_HEADER[clau]] = valor

            # ── 5. La TALLA BASE. Si el document (o el model) la declara, ha de correspondre a
            # una columna de talla real: si no hi és, hem entès malament la taula → abdicar.
            # Si ningú no la declara, la base és la primera talla (contracte del parser antic).
            base_label = (sample_size or base_hint or '').strip()
            base_ci = None
            if base_label:
                canon = canonical_size_label(base_label)
                base_ci = next((ci for ci, lbl in size_cols
                                if canonical_size_label(lbl) == canon), None)
                if base_ci is None:
                    meta['motiu'] = (f"full '{ws.title}': la talla base '{base_label}' no té "
                                     f"columna a la taula")
                    continue
            else:
                base_ci, base_label = size_cols[0][0], size_cols[0][1]

            # ── 6. Files de dades. Tres menes de fila que NO són POMs:
            #   · SECCIÓ ('Bodice:', 'Cord:') → codi buit + descripció plena. SALTAR, mai `break`
            #     (D1c·4: el parser antic hi feia `break` i es quedava amb zero files).
            #   · BANNER ('SKETCH WITH CODES') i blocs fusionats → FI DE TAULA (D1c·5).
            #   · fila buida → saltar.
            banner = _files_banner(ws, ci_codi)

            def _cell(row, ci):
                return _num(row[ci]) if (ci is not None and ci < len(row)) else None

            poms = []
            for idx in range(header_idx + 1, len(rows)):
                row = rows[idx]
                if (idx + 1) in banner:
                    break
                codi = str(row[ci_codi]).strip() if (ci_codi < len(row)
                                                     and row[ci_codi] is not None) else ''
                if not codi:
                    continue                      # secció, capçalera-2, o fila buida
                if not _RE_CODI.match(codi):
                    break                         # rètol ('SKETCH WITH CODES') → fi de taula
                desc = (str(row[ci_desc]).strip()
                        if (ci_desc < len(row) and row[ci_desc] is not None) else '')
                values = {}
                for ci, lbl in size_cols:
                    nv = _cell(row, ci)
                    if nv is not None:
                        values[lbl] = nv
                if not desc and not values:
                    continue                      # codi solt sense res: soroll, no un POM
                tm, tp = _cell(row, tol_minus_ci), _cell(row, tol_plus_ci)
                ts = _cell(row, tol_single_ci)
                if ts is not None:
                    tm = ts if tm is None else tm
                    tp = ts if tp is None else tp
                poms.append({
                    'codi_fitxa': codi,           # D1c·7: 'D ' → 'D' (strip)
                    'descripcio': desc,
                    'dim': _cell(row, dim_ci),
                    'values': values,
                    'tol_minus': tm,
                    'tol_plus': tp,
                })

            # ── 7. LA PORTA. ¿Podem demostrar que hem entès la taula? Files amb codi I valor a
            # la talla base. Si no arriben a _MIN_FILES_ENTESA, aquest full no és una taula de
            # mesures que sapiguem llegir: abdiquem i que la IA hi digui la seva.
            # El recompte de files sobreviu a l'abdicació a PROPÒSIT: si aquest full s'ha
            # entès prou per comptar-ne les files però no per fiar-se'n, la IA se n'ocuparà
            # — i el Fix D encara ha de poder dir "el document en tenia N i n'has tret menys".
            meta['n_files_amb_codi'] = max(meta['n_files_amb_codi'], len(poms))

            amb_base = sum(1 for p in poms if base_label in p['values'])
            if amb_base < _MIN_FILES_ENTESA:
                meta['motiu'] = (f"full '{ws.title}': només {amb_base} fila(es) amb valor a la "
                                 f"talla base '{base_label}' (en calen {_MIN_FILES_ENTESA})")
                continue

            meta.update({
                'header': header_meta,
                'base_size': base_label,
                'full': ws.title,
                # Files de POM que el document conté DE DEBÒ (Fix D). Aquí és igual a len(poms):
                # el parser no en deixa caure cap — una fila sense valor a la talla base ('JJ')
                # és un POM legítim (BaseMeasurement.base_value_cm és null=True), no un descart.
                'n_files_amb_codi': len(poms),
                'motiu': None,
            })
            return poms, [lbl for _, lbl in size_cols], meta
    finally:
        wb.close()
    return [], [], meta


def _cribratge_content_block(file_bytes: bytes, filename: str, content_type: str) -> dict:
    """Bloc de contingut per a la API segons el tipus de fitxa origen (PDF/imatge/Excel)."""
    name = (filename or '').lower()
    ct = (content_type or '').lower()

    if ct == 'application/pdf' or name.endswith('.pdf'):
        return {
            'type': 'document',
            'source': {
                'type': 'base64',
                'media_type': 'application/pdf',
                'data': _base64.standard_b64encode(file_bytes).decode(),
            },
        }
    if name.endswith(('.xlsx', '.xls')) or 'spreadsheet' in ct or 'excel' in ct:
        text = _excel_to_text(file_bytes)
        return {'type': 'text', 'text': f'Contingut del full de càlcul (fitxa Excel):\n{text[:12000]}'}

    # Imatge (jpg/png/webp)
    if ct in ('image/jpeg', 'image/png', 'image/webp'):
        media = ct
    elif name.endswith('.png'):
        media = 'image/png'
    elif name.endswith('.webp'):
        media = 'image/webp'
    else:
        media = 'image/jpeg'
    return {
        'type': 'image',
        'source': {
            'type': 'base64',
            'media_type': media,
            'data': _base64.standard_b64encode(file_bytes).decode(),
        },
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def import_session_cribratge_view(request):
    """
    POST /api/v1/import-sessions/cribratge/
    multipart: document (fitxer), model_id, garment_type_item_code

    Crida 1 — cribratge barat (visió, Opus, tokens baixos, sense thinking): detecta nº de
    models al document, tipologia, gènere i el run de talles. SEMPRE retorna resultats; el
    gating (bloqueig de talles, confirmació multi-model) és el pas F2.3.
    """
    import anthropic
    from django.conf import settings
    from django.core.files.base import ContentFile

    from fhort.accounts.models import UserProfile
    from fhort.models_app.models import ImportSession, Model
    from fhort.models_app.extraction_utils import safe_json_parse
    from fhort.tasks.models import GarmentTypeItem

    file_obj = request.FILES.get('document')
    if not file_obj:
        return Response({'error': 'Cal adjuntar un fitxer (camp "document")'}, status=400)

    model_id = request.data.get('model_id')
    if not model_id:
        return Response({'error': 'Cal indicar model_id'}, status=400)
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': f'Model {model_id} no trobat'}, status=404)

    item_code = (request.data.get('garment_type_item_code') or '').strip()
    item = None
    if item_code:
        # Prefer the item already on the model if its code matches; else look up by code.
        if model.garment_type_item_id and model.garment_type_item.code == item_code:
            item = model.garment_type_item
        else:
            item = GarmentTypeItem.objects.filter(code=item_code).first()

    profile = UserProfile.objects.filter(user=request.user).first()

    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        return Response({'error': 'ANTHROPIC_API_KEY no configurada al backend'}, status=500)

    # Crea la sessió i desa el document origen.
    session = ImportSession.objects.create(
        estat='CRIBRATGE', creat_per=profile, model=model, tipologia_confirmada=item,
    )
    file_bytes = file_obj.read()
    session.document.save(file_obj.name, ContentFile(file_bytes), save=True)

    content_block = _cribratge_content_block(file_bytes, file_obj.name, file_obj.content_type)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=CRIBRATGE_MODEL,
            max_tokens=900,
            system=CRIBRATGE_PROMPT,
            messages=[{'role': 'user', 'content': [content_block]}],
        )
        raw = ''.join(
            b.text for b in response.content if getattr(b, 'type', None) == 'text'
        ).strip()
    except Exception as e:
        _logging.getLogger(__name__).exception('Cribratge: error a la crida Claude')
        return Response({'error': f'Error a la crida de cribratge: {e}', 'token': str(session.token)},
                        status=502)

    # Parse tolerant (Fase 1).
    try:
        resultat = safe_json_parse(raw)
    except ValueError as e:
        session.avisos = (session.avisos or []) + [f'Cribratge: JSON invàlid ({e})']
        session.save(update_fields=['avisos', 'actualitzat_at'])
        return Response({'error': f'Cribratge: resposta no parsejable ({e})',
                         'token': str(session.token), 'raw': raw[:500]}, status=422)

    num_models = resultat.get('num_models') or len(resultat.get('models_detectats') or []) or 0
    models_detectats = resultat.get('models_detectats') or []
    tipologia = resultat.get('tipologia_detectada') or ''
    genere = resultat.get('genere_detectat') or ''
    run_document = resultat.get('run_talles_document') or []
    sistema = resultat.get('sistema_talles') or 'unknown'

    run_configurat = [
        s.strip() for s in (model.size_run_model or '').replace(';', '·').split('·') if s.strip()
    ]

    # Desa a la sessió (no fa gating; només cribratge).
    session.model_detectat = models_detectats
    session.run_conciliat = {
        'document': run_document,
        'sistema': sistema,
        'configurat': run_configurat,
        'estat': 'PENDENT',
    }
    # Persisteix el cribratge cru per a F2.3 (gènere/tipologia) sense tocar `resultat` definitiu.
    session.resultat = {**(session.resultat or {}), 'cribratge': resultat}
    session.estat = 'CRIBRATGE'
    session.save()

    plausible_genere = genere in ('woman', 'man', 'unisex', 'baby', 'kids')
    pot_continuar = bool(num_models == 1 and tipologia and tipologia != 'unknown' and plausible_genere)

    return Response({
        'token': str(session.token),
        'estat': session.estat,
        'num_models': num_models,
        'model_detectat': models_detectats,
        'tipologia_detectada': tipologia,
        'genere_detectat': genere,
        'run_talles_document': run_document,
        'sistema_talles': sistema,
        'run_configurat': run_configurat,
        'pot_continuar': pot_continuar,
    }, status=200)


def _norm_label(s):
    return (s or '').strip().upper()


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def import_session_talles_view(request, token):
    """
    PATCH /api/v1/import-sessions/<token>/talles/  (Pas W1 — APARELLAMENT de talles)

    Rep:
      - talles_seleccionades: labels del DOCUMENT que el tècnic manté com a columnes.
      - talla_mapping: [{document, model}] editat per l'humà (opcional). Si NO ve, el backend
        auto-proposa l'aparellament per forma canònica (dialecte mesos inclòs).

    Retorna la proposta/validació (talla_mapping + no_aparellades + errors), les etiquetes REALS
    del model (system_labels, del SizeSystem) i base_size_label. El resultat és LA LLEI de la
    sessió: es desa a run_conciliat.talla_mapping i el confirm el consumeix en exclusiva (la clau
    `mapeig` antiga es retira). Validació: aparellament UNÍVOC (1↔1), model del system, sense dups.
    `alinear` RETIRAT: el run del model parla SEMPRE en etiquetes tenant.
    """
    from fhort.models_app.models import ImportSession

    session = ImportSession.objects.filter(token=token).select_related(
        'model', 'model__size_system',
    ).first()
    if not session:
        return Response({'error': 'Sessió no trobada'}, status=404)
    model = session.model
    if not model:
        return Response({'error': 'La sessió no té model associat'}, status=400)

    talles_sel = [str(t).strip() for t in (request.data.get('talles_seleccionades') or []) if str(t).strip()]
    mapping_in = request.data.get('talla_mapping')   # [{document, model}] editat per l'humà (opcional)
    base_in = request.data.get('base_size_label')    # B5: canvi de talla base (etiqueta model)

    # Run configurat actual del model (etiquetes tenant; només informatiu).
    configurat = [
        s.strip() for s in (model.size_run_model or '').replace(';', '·').split('·') if s.strip()
    ]

    # Etiquetes REALS del model (SizeDefinition del system, ordenades) — LA veritat del panell dret.
    system_labels = []
    if model.size_system_id:
        system_labels = list(model.size_system.talles.order_by('ordre').values_list('etiqueta', flat=True))
    canon_to_tenant = {}
    for _e in system_labels:
        canon_to_tenant.setdefault(canonical_size_label(_e), _e)

    def _propose(doc_labels):
        """Auto-proposta document→model per forma canònica (dialecte mesos inclòs). 1↔1."""
        pairs, no_ap, used = [], [], set()
        for d in doc_labels:
            tgt = canon_to_tenant.get(canonical_size_label(d))
            if tgt and tgt not in used:
                pairs.append({'document': d, 'model': tgt})
                used.add(tgt)
            else:
                no_ap.append(d)
        return pairs, no_ap

    errors = []
    if mapping_in is not None:
        # Validació de l'aparellament editat per l'humà: UNÍVOC (1↔1), model del system, sense dups.
        talla_mapping, no_aparellades, seen_doc, seen_model = [], [], set(), set()
        sys_set = set(system_labels)
        for pair in mapping_in:
            d = str((pair or {}).get('document') or '').strip()
            mdl = str((pair or {}).get('model') or '').strip()
            if not d:
                continue
            if not mdl:
                no_aparellades.append(d)
                continue
            if mdl not in sys_set:
                errors.append(f"La talla model «{mdl}» no és del sistema de talles del model.")
            if d in seen_doc:
                errors.append(f"La talla del document «{d}» surt aparellada més d'un cop.")
            if mdl in seen_model:
                errors.append(f"La talla del model «{mdl}» s'aparella dues vegades (ha de ser 1↔1).")
            seen_doc.add(d)
            seen_model.add(mdl)
            talla_mapping.append({'document': d, 'model': mdl})
    else:
        talla_mapping, no_aparellades = _propose(talles_sel)

    # ── B5 · TALLA BASE. Canvi opcional (limitat a les SizeDefinition del system) → escriu al model.
    if base_in is not None:
        base_in = str(base_in).strip()
        if base_in and base_in in set(system_labels) and base_in != (model.base_size_label or ''):
            model.base_size_label = base_in
            model.save(update_fields=['base_size_label'])
        elif base_in and base_in not in set(system_labels):
            errors.append(f"La talla base «{base_in}» no és del sistema de talles del model.")
    base_label = (model.base_size_label or '').strip()

    # Guard BLOQUEJANT: la talla base ha de tenir una columna del document aparellada (si no, l'import
    # no pot escriure el valor base → seria el 422 del confirm). Es bloqueja ja al pas 1.
    base_paired = any(p.get('model') == base_label for p in talla_mapping)
    base_avisos = []
    if base_label and not base_paired:
        errors.append(f"La talla base «{base_label}» no té cap columna del document aparellada.")

    # Avís NO bloquejant: base divergent de la convenció (mínima del run · S/38 dona · M/42 home)
    # o de l'àncora del ruleset del model.
    def _conventional_base():
        tgt = (model.target or '').upper()
        if any(k in tgt for k in ('WOMAN', 'WOMEN')):
            for c in ('S', '38'):
                if c in system_labels:
                    return c
        if 'MAN' in tgt or 'MEN' in tgt:
            for c in ('M', '42'):
                if c in system_labels:
                    return c
        return system_labels[0] if system_labels else None   # mínima del run
    conv = _conventional_base()
    if base_label and conv and base_label != conv:
        base_avisos.append(f"La talla base «{base_label}» divergeix de la convenció del segment (esperada «{conv}»).")
    if base_label and model.grading_rule_set_id:
        anchor = (model.grading_rule_set.regles.values_list('talla_base__etiqueta', flat=True).first())
        if anchor and anchor != base_label:
            base_avisos.append(f"La talla base «{base_label}» divergeix de l'àncora del ruleset «{anchor}».")

    ready = bool(talla_mapping) and not errors

    rc = dict(session.run_conciliat or {})
    rc.update({
        'configurat': configurat,
        'seleccionades': talles_sel,
        'talla_mapping': talla_mapping,       # B1: LA LLEI de la sessió (document→model tenant).
        'no_aparellades': no_aparellades,
        'sense_desti': no_aparellades,        # compat: lectors antics.
        'estat': 'RESOLT' if ready else 'PENDENT',
    })
    rc.pop('mapeig', None)                     # la clau `mapeig` MOR: una sola font de veritat.
    session.run_conciliat = rc
    if ready:
        session.estat = 'TALLES'
    session.save(update_fields=['run_conciliat', 'estat', 'actualitzat_at'])

    # Columnes del document sense parella → oferim pre-omplir el Size Map Setup (run de client nou).
    size_map_prefill = None
    if not ready and no_aparellades:
        target_codi = model.target or ''
        if not target_codi and model.size_system_id:
            _ss_target = model.size_system.targets.first()
            if _ss_target:
                target_codi = _ss_target.codi
        size_map_prefill = {
            'target_codi': target_codi or None,
            'labels': no_aparellades,
            'base_size': model.base_size_label or None,
            'import_session_token': str(session.token),
            'model_id': model.id,
        }

    return Response({
        'ready': ready,
        'estat': session.estat,
        'run_conciliat': rc,
        'talla_mapping': talla_mapping,
        'no_aparellades': no_aparellades,
        'system_labels': system_labels,       # etiquetes REALS del model (selectors + panell dret).
        'base_size_label': base_label,
        'base_paired': base_paired,
        'base_avisos': base_avisos,           # B5: divergències no bloquejants de la talla base.
        'conventional_base': conv,
        'size_run_model': model.size_run_model,
        'errors': errors,
        'size_map_prefill': size_map_prefill,
    }, status=200)


# ─────────────────────── Matching POMMaster (compartit) ───────────────────────
# Extret de create_from_extraction_view perquè l'extracció per sessió (W2) i la creació
# directa des d'extracció comparteixin EXACTAMENT la mateixa lògica de matching.
_POM_SYNONYMS = {
    # Existing
    'waist position':                  'waist position',
    'hip position':                    'hip position',
    'front body length':               'body length',
    'straight back body length':       'body length cb',
    'side length':                     'side seam',
    'front armhole curve':             'armhole curve',
    'neckline width':                  'neck width',
    'collar height':                   'collar height',
    'collar width':                    'collar width',
    'bottom width':                    'skirt sweep',
    'body zip length':                 'zip length',
    'lining length at center front':   'lining length',
    'lining length at center back':    'lining length',
    'lining bottom width along hem':   'lining hem width',
    # El bloc "Brownie positional POMs" (nomenclatura del customer BRW disfressada de sinònim
    # canònic) s'ha MIGRAT a CustomerPOMAlias (origen=MIGRACIO), migració pom 0031 (N2-4a,
    # DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08). Els sinònims genèrics d'aquest diccionari es
    # conserven; el matcher llegeix els àlies com a estratègia (a) prioritària (N3 fet, veure
    # find_pom_master més avall).
}


def find_pom_master(code, description, customer=None):
    """
    Find the most suitable POMMaster.
    Return (pom_master, match_type, confidence)
    confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'NO_MATCH'

    ORDRE (DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08, N3):
      (a) ÀLIES exacte del `customer` (CustomerPOMAlias) → HIGH. Requereix `customer`; si és None
          (context sense client) se salta. El `client_code` d'un àlies pot ser un codi posicional
          (LOS 'H.6') O el text de la descripció del client (BRW 'front armhole curve') → es prova
          contra `code` I contra `description`.
          ⚠️ Un àlies amb `pendent_revisio=True` **NO auto-vincula** (v. sota, QA-S8-R1).
      (b) descripció + sinònims canònics → HIGH/MEDIUM (nom_client, POMGlobal.nom_en).
      (c) codi numèric + 'lining' → MEDIUM.
      (c-bis) l'àlies PENDENT DE REVISIÓ, com a darrer suggeriment → LOW (mai auto-vincle).
      (d) FALLBACK TRANSITORI (deprecació — objectiu de la diagnosi: treure `codi_client` del
          matcher): `codi_client` exacte i root-prefix → LOW. Amb el llindar d'auto-vinculació
          (c2b19bd) un LOW NO auto-vincula: cau a pendents amb el suggeriment visible. Abans
          anaven PRIMER amb HIGH; ara són l'últim recurs, per sota de l'àlies i la descripció.
    """
    from fhort.pom.models import POMMaster, CustomerPOMAlias

    desc_clean = (description or '').lower().strip()
    desc_base = _re.sub(r'\s*[\(\[].*?[\)\]]', '', desc_clean).strip()

    # (a) Àlies de nomenclatura del client. Va PRIMER: un codi/descripció reclamat explícitament
    # per un àlies d'AQUEST customer mana sobre qualsevol heurística de descripció.
    #
    # ⚠️ QA-S8-R1 · LA PORTA DEL MATCHER. Un àlies marcat `pendent_revisio` és un àlies del qual
    # el sistema DESCONFIA: el guard d'aprenentatge (pom/services.py) el marca així quan el POM
    # que reclama ja el reclamava un ALTRE codi del mateix client — o sigui, quan o bé sobra, o
    # bé una de les dues mesures acabarà sobre el POM equivocat. Un àlies del qual desconfiem no
    # pot ser alhora la font de màxima confiança del matcher: seria marcar-lo per revisar i
    # continuar creient-l'hi. Aquí es DEGRADA a suggeriment (c-bis), mai a auto-vincle.
    #
    # I no s'atura la cerca: es prova la resta d'estratègies, que poden trobar-hi un vincle bo
    # de debò. L'àlies pendent només parla si no parla ningú altre.
    #
    # `pom__isnull=False` (QA-S8-R1): un àlies SENSE POM no és matchable — és vocabulari del
    # client pendent de mapar (CustomerPOMAlias.pom és nullable, migració 0037). No té destí,
    # així que no pot vincular res, i sense el filtre `alias.pom.actiu` petaria amb AttributeError.
    alias_pendent = None
    if customer is not None:
        for key in (k for k in (code, desc_clean) if k):
            alias = (CustomerPOMAlias.objects
                     .filter(customer=customer, client_code__iexact=key, pom__isnull=False)
                     .select_related('pom').first())
            if alias and alias.pom.actiu:
                if alias.pendent_revisio:
                    if alias_pendent is None:
                        alias_pendent = alias.pom
                    continue
                return alias.pom, 'alias_match', 'HIGH'

    if desc_clean:
        # Strategy 2 — explicit synonym (curated table).
        syn = _POM_SYNONYMS.get(desc_clean) or _POM_SYNONYMS.get(desc_base)
        if syn:
            for pm in POMMaster.objects.select_related('pom_global').filter(actiu=True):
                nom = (pm.nom_client or '').lower()
                if syn in nom or nom in syn:
                    return pm, 'synonym_match', 'HIGH'
            for pm in POMMaster.objects.select_related('pom_global').filter(
                pom_global__isnull=False, actiu=True,
            ):
                nom_en = (pm.pom_global.nom_en or '').lower()
                if syn in nom_en or nom_en in syn:
                    return pm, 'synonym_global_match', 'HIGH'

        # Strategy 3 — match by nom_client (exact=HIGH, contains=MEDIUM).
        for pm in POMMaster.objects.select_related('pom_global').filter(actiu=True):
            nom = (pm.nom_client or '').lower()
            if desc_base and len(desc_base) > 3:
                if desc_base == nom:
                    return pm, 'exact_description', 'HIGH'
                if desc_base in nom or nom in desc_base:
                    return pm, 'description_match', 'MEDIUM'

        # Strategy 4 — match by POMGlobal nom_en / abbreviation.
        for pm in POMMaster.objects.select_related('pom_global').filter(
            pom_global__isnull=False, actiu=True,
        ):
            pg = pm.pom_global
            nom_en = (pg.nom_en or '').lower()
            abbrev = (pg.abbreviation or '').lower()
            if desc_base and len(desc_base) > 3:
                if desc_base == nom_en:
                    return pm, 'global_exact', 'HIGH'
                if desc_base in nom_en or nom_en in desc_base:
                    return pm, 'global_name_match', 'MEDIUM'
            if code and code.lower() == abbrev:
                return pm, 'abbreviation_match', 'HIGH'

    # (c) Strategy — pure numeric codes → lining.
    if code and code.isdigit():
        desc_lower = (description or '').lower()
        if 'lining' in desc_lower:
            for pm in POMMaster.objects.select_related('pom_global').filter(actiu=True):
                nom = (pm.nom_client or '').lower()
                if 'lining' in nom:
                    return pm, 'numeric_lining_match', 'MEDIUM'

    # (c-bis) L'ÀLIES PENDENT DE REVISIÓ (QA-S8-R1). Cap altra estratègia no ha trobat res ferm,
    # així que ara sí que val la pena dir què reclamava aquell àlies del qual desconfiem — però
    # com el que és: un SUGGERIMENT (LOW). El llindar (`_apply_match_threshold`) el deixarà a
    # pendents amb el nom visible, i una persona decidirà. Va per damunt dels fallbacks de codi
    # (d) perquè un àlies el va declarar algú d'aquest client; un root-prefix no l'ha declarat ningú.
    if alias_pendent is not None:
        return alias_pendent, 'alias_pendent_revisio', 'LOW'

    # (d) FALLBACK TRANSITORI — `codi_client` exacte. Abans era la 1a estratègia amb HIGH; ara és
    # penúltim recurs amb LOW (deprecació): l'àlies i la descripció manen. Un exacte que arriba
    # aquí no ha resolt per àlies ni per descripció → suggeriment feble, no auto-vinculació.
    if code:
        pm = POMMaster.objects.filter(codi_client__iexact=code, actiu=True).first()
        if pm:
            return pm, 'legacy_code_match', 'LOW'

    # (d) FALLBACK TRANSITORI (ÚLTIM RECURS) — root de lletres inicials per a codis posicionals
    # (D1, G2s → D, G). NO es rooteja la nomenclatura d'AGRUPACIÓ 'LLETRA.NÚMERO' (H.6, G.3, J.2):
    # la lletra és un grup del document, no un codi de mesura, i col·lapsaria a un POM d'una sola
    # lletra aliè. Confiança LOW: darrer recurs, no una vinculació segura.
    if code and not _re.match(r'^[A-Za-z]+\.\d', code):
        m = _re.match(r'^([A-Za-z]+)', code)
        if m and m.group(1) != code:
            root = m.group(1)
            pm = POMMaster.objects.filter(codi_client__iexact=root, actiu=True).first()
            if pm:
                return pm, 'root_code_match', 'LOW'

    return None, 'no_match', 'NO_MATCH'


# ─────────────────────────────────────────────────────────────────────────────
# PORTES DE VINCULACIÓ (QA-S8, DIAGNOSI_QA_S8_IMPORT)
#
# Bessones de les de `pom/size_map_views.py:29,53` (importador de la Size Library), que
# ja les tenia i que l'importador de MODELS no. La diagnosi va trobar el forat: el mateix
# mode de fallada estava protegit en un importador i despullat a l'altre. No s'extreu un
# helper compartit entre les dues apps (seria refactor fora d'abast); s'adapten aquí a les
# claus de `poms_extrets` (`pom_master_id`/`pom_codi`/`pom_nom`) i el docstring diu d'on
# vénen, perquè el dia que una de les dues canviï se sàpiga que hi ha una germana.
# ─────────────────────────────────────────────────────────────────────────────

#: Un match per sota d'això NO auto-vincula. Un LOW (codi legacy, arrel del codi) és el
#: darrer recurs del matcher, no una certesa: la fila cau a pendents amb el suggeriment
#: visible i la persona decideix. Vincular en silenci amb confiança baixa és el que va
#: fer que 'U2' i 'U3' (First/Last button) acabessin tots dos sobre el POM 'U'
#: (Width sequins piece) — un disbarat que ningú no va veure perquè no es va dir.
_POM_AUTOLINK_CONF = ('HIGH', 'MEDIUM')


def _apply_match_threshold(pom, conf):
    """El llindar: (pom, conf) → (pom_efectiu, weak_suggestion).

    Per sota del llindar es desvincula i es torna el nom suggerit, perquè la UI el mostri
    com a pendent. Mai una vinculació dubtosa en silenci.
    """
    if pom is not None and conf not in _POM_AUTOLINK_CONF:
        return None, pom
    return pom, None


def _apply_many_to_one_guard(rows):
    """Si DUES files del document resolen al MATEIX POM, **cap de les dues auto-vincula**.

    `BaseMeasurement` és únic per `(model, pom)`: dues files que hi cauen col·lapsen, i la
    segona sobreescriu la primera **en silenci** (W5, `update_or_create`). El símptoma que
    va veure QA —una mesura del document que desapareix— surt exactament d'aquí.

    ⚠️ **AQUÍ L'ÀLIES NO QUEDA EXEMPT, i la germana de `size_map_views.py:53` SÍ.** La
    divergència és deliberada i és el moll de l'os:

      · A `size_map` el destí és `GradingRule`, i que dos codis del client comparteixin un
        POM hi és tolerable (Losan H.11 sleeve opening / H.16 cuff opening).
      · Aquí el destí és `BaseMeasurement`, **únic per (model, pom)**. Dues files NO hi
        caben. Per legítim que sigui l'àlies, la segona esborra la primera. L'exempció
        importaria una premissa que en aquest destí no es compleix.

    I no és teòric: al catàleg viu, el client BRW té els àlies `F` i `FF` (Centre FRONT
    length i Centre BACK length — dues mesures distintes) tots dos cap al POM 389
    'TOTAL LENGTH', i `U2`/`U3` (First/Last button) tots dos cap al 439 'Width sequins
    piece'. Amb l'exempció posada, aquestes quatre files travessaven les dues portes amb
    confiança HIGH i dues mesures del document s'esborraven a W5 sense dir res.

    Un àlies dolent és un problema del catàleg i es resol al catàleg; el que aquesta porta
    ha de garantir és que **no acabi sent una pèrdua de dades silenciosa**.

    Muta `rows` in situ.
    """
    counts = {}
    for r in rows:
        if r.get('pom_master_id'):
            counts[r['pom_master_id']] = counts.get(r['pom_master_id'], 0) + 1
    dup_ids = {pid for pid, n in counts.items() if n >= 2}
    if not dup_ids:
        return rows

    for r in rows:
        if r.get('pom_master_id') in dup_ids:
            # El suggeriment queda VISIBLE: la persona ha de poder veure a què s'assemblava.
            r['weak_suggestion'] = r.get('pom_nom')
            r['weak_suggestion_codi'] = r.get('pom_codi')
            r['pom_master_id'] = None
            r['pom_codi'] = None
            r['pom_nom'] = None
            r['many_to_one'] = True
            r['actiu'] = False
    return rows


def _match_rows(files, customer):
    """Files llegides del document → `poms_extrets`, amb les portes aplicades.

    **Font ÚNICA de matching per als DOS camins d'extracció** (parser ràpid d'Excel i visió
    Opus). Abans cadascun es muntava la seva llista i divergien: la via ràpida marcava
    `actiu=True` per a tothom i la via Opus `actiu=bool(pm)`. Ara el criteri és un i és
    aquest:

        **actiu ⇔ vincle FERM** (match per sobre del llindar i no compartit amb cap altra fila).

    `files`: [{codi_fitxa, descripcio, values, tol_minus, tol_plus}].
    Retorna (poms_extrets, stats) amb stats = {n_nomatch, n_low, n_many_to_one}.
    """
    rows = []
    n_nomatch = n_low = 0

    for i, f in enumerate(files):
        codi = (f.get('codi_fitxa') or '').strip()
        descripcio = (f.get('descripcio') or '').strip()
        pm, match_type, confidence = find_pom_master(codi, descripcio, customer=customer)

        # Els comptadors es prenen del match CRU (abans del llindar): així l'avís continua
        # distingint "no s'ha trobat res" de "s'ha trobat però no és de fiar".
        if pm is None:
            n_nomatch += 1
        elif confidence == 'LOW':
            n_low += 1

        pm_efectiu, suggeriment = _apply_match_threshold(pm, confidence)

        rows.append({
            'codi_fitxa': codi,
            'descripcio': descripcio,
            'pom_master_id': pm_efectiu.id if pm_efectiu else None,
            'pom_codi': pm_efectiu.codi_client if pm_efectiu else None,
            'pom_nom': pm_efectiu.nom_client if pm_efectiu else None,
            'match_type': match_type,
            'confidence': confidence,
            'values': f.get('values') or {},
            'tol_minus': f.get('tol_minus'),
            'tol_plus': f.get('tol_plus'),
            'actiu': bool(pm_efectiu),
            'ordre': i,
            'weak_suggestion': suggeriment.nom_client if suggeriment else None,
            'weak_suggestion_codi': suggeriment.codi_client if suggeriment else None,
            'many_to_one': False,
        })

    _apply_many_to_one_guard(rows)
    n_many = sum(1 for r in rows if r.get('many_to_one'))

    return rows, {'n_nomatch': n_nomatch, 'n_low': n_low, 'n_many_to_one': n_many}


def _avisos_de_matching(stats):
    """Els avisos del matching. Un per motiu, i cadascun diu QUÈ ha de fer la persona."""
    avisos = []
    if stats['n_nomatch']:
        avisos.append(
            f"{stats['n_nomatch']} POM(s) sense match al catàleg — cal revisar o "
            f"afegir manualment."
        )
    if stats['n_low']:
        avisos.append(
            f"{stats['n_low']} POM(s) amb confiança baixa: NO s'han vinculat "
            f"automàticament. Revisa'ls al pas de POMs — hi tens el suggeriment."
        )
    if stats['n_many_to_one']:
        avisos.append(
            f"{stats['n_many_to_one']} POM(s) de la fitxa apuntaven al MATEIX POM del "
            f"catàleg: cap no s'ha vinculat automàticament (dues mesures no poden compartir "
            f"un POM: la segona esborraria la primera). Resol-los un per un."
        )
    return avisos


# ═══════════════════════════ W2 — Extracció POMs ═══════════════════════════
EXTRACCIO_MODEL = 'claude-opus-4-7'
EXTRACCIO_MAX_TOKENS = 16000

EXCEL_REVISION_MODEL = 'claude-sonnet-4-6'
EXCEL_REVISION_MAX_TOKENS = 2000


def _revise_excel_poms_with_sonnet(poms_text: str, api_key: str) -> dict:
    """Revisió lleugera (Sonnet) dels POMs extrets d'un Excel. No-fatal:
    retorna SEMPRE un dict {'corrections': [...], 'warnings': [...]}."""
    import anthropic
    from fhort.models_app.extraction_utils import safe_json_parse

    default = {'corrections': [], 'warnings': []}
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=EXCEL_REVISION_MODEL,
            max_tokens=EXCEL_REVISION_MAX_TOKENS,
            system="""Ets un validador de fitxes tècniques tèxtils.
Reps una llista de POMs (punts de mesura) extrets d'un Excel.
Retorna NOMÉS un JSON amb aquest format exacte:
{"corrections": [{"codi": "X", "camp": "descripcio|dim", "valor_suggerit": "..."}], "warnings": ["..."]}
Si no cal cap correcció, retorna {"corrections": [], "warnings": []}
No afegeixis cap text fora del JSON.""",
            messages=[{'role': 'user', 'content': poms_text}],
        )
        raw = ''.join(
            b.text for b in response.content if getattr(b, 'type', None) == 'text'
        ).strip()
        parsed = safe_json_parse(raw)
        if not isinstance(parsed, dict):
            return default
        return {
            'corrections': parsed.get('corrections') or [],
            'warnings': parsed.get('warnings') or [],
        }
    except Exception:
        _logging.getLogger(__name__).exception('Revisió Excel (Sonnet): error no-fatal')
        return default


def _avis_files_perdudes(n_document, n_extretes):
    """FIX D (DIAGNOSI_QA_S8_IMPORT §D1e): el document té més files de POM que les extretes.

    La fitxa del Tate té 26 POMs i la IA en va retornar 25. La que va deixar caure —`JJ`,
    '1/2 Elbow width'— era l'única fila SENSE valor a la talla base, i **cap avís ho va dir**:
    una fila del document desapareixia en silenci. Un POM sense mesura base és legítim
    (`BaseMeasurement.base_value_cm` és `null=True`), així que la fila no s'havia de perdre;
    i si es perd, s'ha de dir.

    El recompte del document el dona el parser determinista (`meta['n_files_amb_codi']`), que
    sap comptar les files encara que abdiqui de llegir-ne els valors. Només s'avisa en el sentit
    que fa mal —el document en té MÉS que les extretes—, mai al revés.
    """
    if n_document and n_extretes < n_document:
        perdudes = n_document - n_extretes
        return [f"El document té {n_document} files amb codi de POM i se n'han extret "
                f"{n_extretes}: {perdudes} fila(es) no s'han llegit. Revisa-les a mà (sovint "
                f"són files sense valor a la talla base, que són POMs igualment vàlids)."]
    return []


def _extraccio_via_excel(session, api_key):
    """Via ràpida d'extracció per a fitxes Excel: parse determinista + revisió Sonnet,
    SENSE la crida Opus.

    Retorna `(resposta, meta)`:
      · `resposta` = Response amb la MATEIXA forma que la via PDF/imatge, o **None** si el
        parser abdica (el caller fa fallback IA via Opus, com sempre).
      · `meta` = el que el parser ha pogut saber del document **encara que abdiqui** — hi ha
        el recompte de files, que el camí IA necessita per al Fix D.
    """
    # 1. Bytes del document desat al Pas 1.
    try:
        session.document.open('rb')
        file_bytes = session.document.read()
    finally:
        session.document.close()

    # 2. Parse determinista. Les pistes del model (talla base i run) ajuden a reconèixer les
    # columnes de talla quan el document no declara `SAMPLE SIZE`; si el document sí que ho
    # diu, mana el document.
    model = session.model
    raw_poms, talles_detectades, meta = _parse_excel_poms(
        file_bytes,
        base_hint=(model.base_size_label if model else None),
        run_hint=[s.strip() for s in ((model.size_run_model if model else '') or '')
                  .replace(';', '·').split('·') if s.strip()],
    )

    # 3. Sense POMs llegibles → senyal (None) perquè el caller faci fallback IA (Opus).
    if not raw_poms:
        return None, meta

    # 4. Text pla per a la revisió Sonnet.
    linies = [
        f"{p['codi_fitxa']} | {p['descripcio']} | DIM:{p.get('dim', '')} | {p['values']}"
        for p in raw_poms
    ]
    poms_text = '\n'.join(linies)

    # 5. Revisió lleugera (no-fatal).
    revision = _revise_excel_poms_with_sonnet(poms_text, api_key)

    # 6. Aplica correccions (només camp descripcio/dim, codis existents).
    by_codi = {}
    for p in raw_poms:
        by_codi.setdefault(p['codi_fitxa'], p)
    for corr in (revision.get('corrections') or []):
        if not isinstance(corr, dict):
            continue
        target = by_codi.get(str(corr.get('codi') or '').strip())
        camp = corr.get('camp')
        if not target or camp not in ('descripcio', 'dim'):
            continue
        if camp == 'descripcio':
            target['descripcio'] = str(corr.get('valor_suggerit') or '').strip()
        else:  # dim
            try:
                target['dim'] = float(str(corr.get('valor_suggerit')).replace(',', '.'))
            except (ValueError, TypeError):
                pass

    # 7-8. Matching POM + format IDÈNTIC al de la via Opus: la MATEIXA funció (`_match_rows`),
    # amb les mateixes portes. Abans aquesta via marcava `actiu=True` per a totes les files,
    # inclosos els sense match; ara el criteri és únic (actiu ⇔ vincle ferm) perquè el
    # matching és literalment el mateix codi.
    # N3: customer del model per resoldre els àlies de nomenclatura del client.
    import_customer = session.model.customer if session.model_id else None
    poms_extrets, stats = _match_rows(raw_poms, import_customer)

    avisos_extraccio = list(revision.get('warnings', []))
    avisos_extraccio += _avisos_de_matching(stats)

    # 9. Talles, capçalera i talla BASE — els tres, llegits del document.
    #
    # PARITAT AMB LA VIA OPUS (bandera 3 de la diagnosi). Aquesta via retornava `header: {}`
    # i `base_size = sizes[0]` **encara quan funcionava**. Cap de les dues coses era innocent:
    #   · el `header` buit deixava el wizard sense marca/temporada/nom d'estil, que la via Opus
    #     sí que omplia → dues respostes amb la mateixa forma i contingut diferent;
    #   · i `sizes[0]` NO és la talla base: a la fitxa Rosalia el run és XXS·XS·S·M·L i la base
    #     és 'S', no 'XXS'. A més, sense `base_size` a `resultat['extraccio']`, la reconciliació
    #     de talles de W5 (:1426) queda desactivada del tot per aquest camí ("manca base").
    # Ara les dues surten del bloc de metadades del document (`SAMPLE SIZE`), i el camí ràpid
    # deixa de ser un ciutadà de segona.
    sizes = [str(t) for t in talles_detectades]
    header = meta.get('header') or {}
    base_size = meta.get('base_size') or (sizes[0] if sizes else None)
    extraccio = {'via': 'excel', 'header': header, 'sizes': sizes, 'base_size': base_size}

    # 10. Persisteix. NOTA: `session.poms_extrets` és la font de veritat per als passos
    # W2-confirmació (:1216) i W3-mesures (:1415); cal desar-la (paritat amb la via Opus).
    session.resultat = {**(session.resultat or {}),
                        'extraccio': extraccio,
                        'grading_status': 'ok'}
    session.poms_extrets = poms_extrets
    session.avisos = list(session.avisos or []) + avisos_extraccio
    session.estat = 'POMS'
    session.save(update_fields=['resultat', 'poms_extrets', 'avisos', 'estat',
                                'actualitzat_at'])

    # 11. Resposta amb EXACTAMENT el mateix format que la via PDF/imatge (:1180-1188),
    # `suggested_valors_mode` inclòs: el toggle absoluts/deltes del wizard el llegeix, i sense
    # ell aquesta via el deixava sense default. Cosmètic → mai pot petar l'extracció.
    try:
        from fhort.pom.grading_utils import suggest_valors_mode
        suggested_valors_mode = suggest_valors_mode(
            {p['pom_master_id']: p['values'] for p in poms_extrets
             if p.get('pom_master_id') and p.get('values')},
            base_size, sizes)
    except Exception:
        suggested_valors_mode = 'absoluts'

    return Response({
        'estat': 'POMS',
        'poms_extrets': poms_extrets,
        'header': header,
        'base_size': base_size,
        'sizes': sizes,
        'grading_status': {'status': 'ok', 'detail': ''},
        'avisos': avisos_extraccio,
        'suggested_valors_mode': suggested_valors_mode,
    }, status=200), meta


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_session_extraccio_view(request, token):
    """
    POST /api/v1/import-sessions/<token>/extraccio/  (Pas W2 — Crida 2: extracció completa)

    Re-llegeix el document desat a la sessió i fa l'extracció completa (POMs + valors +
    grading) amb visió Opus 16k. Per cada POM crida find_pom_master i desa el matching a
    session.poms_extrets. Desa l'extracció completa a session.resultat. estat→'POMS'.
    SEMPRE retorna (mai bloqueja: salvage de Fase 1 si el JSON global falla).
    """
    import anthropic
    from django.conf import settings

    from fhort.models_app.models import ImportSession
    from fhort.models_app.extraction_prompt import TECH_SHEET_EXTRACTION_PROMPT
    from fhort.models_app.extraction_utils import safe_json_parse, salvage_measurements

    session = ImportSession.objects.filter(token=token).select_related('model').first()
    if not session:
        return Response({'error': 'Sessió no trobada'}, status=404)
    if not session.document:
        return Response({'error': 'La sessió no té document desat'}, status=400)

    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        return Response({'error': 'ANTHROPIC_API_KEY no configurada al backend'}, status=500)

    # Via ràpida Excel: parse determinista + revisió Sonnet, saltant Opus.
    # Si el parser ràpid no reconeix el format (None), es continua pel camí comú
    # Opus amb el full de càlcul convertit a text. PDF/imatge no canvien.
    doc_name = session.document.name or ''
    es_excel = doc_name.lower().endswith(('.xlsx', '.xls'))
    excel_meta = {}
    if es_excel:
        resposta_rapida, excel_meta = _extraccio_via_excel(session, api_key)
        if resposta_rapida is not None:
            return resposta_rapida

    # Llegeix el document desat al Pas 1.
    try:
        session.document.open('rb')
        file_bytes = session.document.read()
    finally:
        session.document.close()

    avisos = list(session.avisos or [])
    detectats = session.model_detectat or []
    if len(detectats) > 1:
        avisos.append(
            f'Document multi-model ({len(detectats)} detectats); extracció del model principal.'
        )

    if es_excel:
        content_block = {'type': 'text',
                         'text': f'Contingut del full de càlcul (fitxa Excel):\n{_excel_to_text(file_bytes)}'}
        # L'avís diu ara PER QUÈ el parser ha abdicat. Abans deia només que ho havia fet, i la
        # diagnosi va haver d'executar el parser sobre els bytes reals per esbrinar el motiu.
        motiu = (excel_meta.get('motiu') or '').strip()
        avisos.append('Format Excel no reconegut pel parser ràpid; extracció via IA.'
                      + (f' Motiu: {motiu}.' if motiu else ''))
    else:
        content_block = _cribratge_content_block(file_bytes, session.document.name, '')

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=EXTRACCIO_MODEL,
            max_tokens=EXTRACCIO_MAX_TOKENS,
            thinking={'type': 'adaptive'},
            output_config={'effort': 'high'},
            system=[{'type': 'text', 'text': TECH_SHEET_EXTRACTION_PROMPT,
                     'cache_control': {'type': 'ephemeral'}}],
            messages=[{'role': 'user', 'content': [content_block]}],
        )
        raw = ''.join(
            b.text for b in response.content if getattr(b, 'type', None) == 'text'
        ).strip()
    except Exception as e:
        _logging.getLogger(__name__).exception('Extracció W2: error a la crida Claude')
        return Response({'error': f'Error a la crida d\'extracció: {e}'}, status=502)

    # Guarda de truncament: si Opus talla per límit de tokens, degradem amb gràcia
    # (no bloqueja; el JSON pot quedar incomplet i el gestiona el salvage de sota).
    if getattr(response, 'stop_reason', None) == 'max_tokens':
        avisos.append("Resposta d'extracció truncada pel límit de tokens; "
                      'resultat possiblement incomplet.')

    # Parse tolerant (Fase 1) amb salvage per fila.
    grading_status = {'status': 'ok', 'detail': ''}
    try:
        extracted = safe_json_parse(raw)
    except ValueError as e:
        salvaged = salvage_measurements(raw)
        if not salvaged:
            session.avisos = avisos + [f'Extracció: JSON il·legible ({e})']
            session.save(update_fields=['avisos', 'actualitzat_at'])
            return Response({'error': 'La IA no ha retornat dades llegibles',
                             'detail': str(e)}, status=422)
        extracted = {'measurements': salvaged}
        grading_status = {'status': 'error',
                          'detail': f'JSON global malformat; recuperats {len(salvaged)} POMs per fila. ({e})'}
        avisos.append(grading_status['detail'])

    measurements = extracted.get('measurements', []) or []

    # FIX D — la fila que la IA deixa caure en silenci. Si el document és un Excel, el parser
    # determinista n'ha comptat les files de POM encara que hagi abdicat de llegir-lo; si la IA
    # en torna menys, es diu. (Amb el Tate: 26 al document, 25 d'Opus, `JJ` perduda i cap avís.)
    avisos += _avis_files_perdudes(excel_meta.get('n_files_amb_codi') or 0, len(measurements))

    # Matching POM per fila.
    # N3 (DIAGNOSI_NOMENCLATURA_ALIES): customer del model → el matcher resol els àlies de
    # nomenclatura d'AQUEST client abans que per descripció. Si el model no en té, customer=None
    # (comportament previ: resol per descripció).
    import_customer = session.model.customer if session.model_id else None
    poms_extrets, stats = _match_rows(
        [
            {
                'codi_fitxa': msr.get('client_code') or msr.get('code') or '',
                'descripcio': msr.get('description') or '',
                'values': msr.get('values') or {},
                # B2: tolerància del document (None si absent).
                'tol_minus': msr.get('tol_minus'),
                'tol_plus': msr.get('tol_plus'),
            }
            for msr in measurements
        ],
        import_customer,
    )
    avisos += _avisos_de_matching(stats)

    session.resultat = {**(session.resultat or {}), 'extraccio': extracted,
                        'grading_status': grading_status}
    session.poms_extrets = poms_extrets
    session.avisos = avisos
    session.estat = 'POMS'
    session.save(update_fields=['resultat', 'poms_extrets', 'avisos', 'estat', 'actualitzat_at'])

    # 1C-2b: suggeriment del mode dels valors (default del toggle al front). Es calcula sobre
    # els POMs amb match (identitat canònica) i sobre el run/base del DOCUMENT (extracted) —
    # mateix origen que les claus de `values`. Cosmètic → mai pot petar W2; default 'absoluts'.
    try:
        from fhort.pom.grading_utils import suggest_valors_mode
        vals_per_pom = {
            p['pom_master_id']: p['values']
            for p in poms_extrets
            if p.get('pom_master_id') and p.get('values')
        }
        suggested_valors_mode = suggest_valors_mode(
            vals_per_pom, extracted.get('base_size'), extracted.get('sizes') or [])
    except Exception:
        suggested_valors_mode = 'absoluts'

    return Response({
        'estat': session.estat,
        'poms_extrets': poms_extrets,
        'header': extracted.get('header') or {},
        'base_size': extracted.get('base_size'),
        'sizes': extracted.get('sizes') or [],
        'grading_status': grading_status,
        'avisos': avisos,
        'suggested_valors_mode': suggested_valors_mode,
    }, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def import_session_poms_view(request, token):
    """
    PATCH /api/v1/import-sessions/<token>/poms/  (Pas W2 — confirmació de POMs)

    Rep poms_confirmats (llista de pom_master_id actius). Marca actiu per cada POM extret;
    els pom_master_id confirmats que no hi siguin (afegits manualment del catàleg) s'incorporen.
    Rep també poms_tenant_only (llista d'ordres de files NO_MATCH que el tècnic vol crear com
    a POMMaster tenant-only: pom_global=None, codi_client=codi_fitxa). estat→'MESURES'.
    """
    from fhort.models_app.models import ImportSession
    from fhort.pom.models import POMMaster, POMCategory

    session = ImportSession.objects.filter(token=token).first()
    if not session:
        return Response({'error': 'Sessió no trobada'}, status=404)

    confirmats = [int(x) for x in (request.data.get('poms_confirmats') or []) if str(x).isdigit()]
    confirmats_set = set(confirmats)
    tenant_only_ordres = {
        int(x) for x in (request.data.get('poms_tenant_only') or [])
        if str(x).lstrip('-').isdigit()
    }

    poms = list(session.poms_extrets or [])
    existents = {p.get('pom_master_id') for p in poms if p.get('pom_master_id')}
    for p in poms:
        if p.get('pom_master_id'):
            p['actiu'] = p['pom_master_id'] in confirmats_set

    # POMs sense match triats pel tècnic → crear (o reutilitzar) POMMaster tenant-only.
    if tenant_only_ordres:
        categoria_default = (POMCategory.objects.filter(actiu=True)
                             .order_by('display_order', 'codi').first())
        for p in poms:
            if p.get('pom_master_id') or p.get('ordre') not in tenant_only_ordres:
                continue
            codi = (p.get('codi_fitxa') or '').strip()
            if not codi:
                continue
            descripcio = (p.get('descripcio') or '').strip()
            pm, _created = POMMaster.objects.get_or_create(
                pom_global=None,
                codi_client=codi,
                defaults={
                    'nom_client': descripcio or codi,
                    'actiu': True,
                    'categoria': categoria_default,
                    'pendent_revisio': True,
                    'origen_import': str(session.token),
                    'notes': f'Creat automàticament per import, fitxa {session.token}',
                },
            )
            p['pom_master_id'] = pm.id
            p['pom_codi'] = pm.codi_client
            p['pom_nom'] = pm.nom_client
            p['match_type'] = 'tenant_only'
            p['confidence'] = 'TENANT_ONLY'
            p['actiu'] = True
            existents.add(pm.id)

    # Afegir POMs confirmats que no eren a l'extracció (afegits manualment).
    for pid in confirmats_set - existents:
        pm = POMMaster.objects.filter(id=pid, actiu=True).first()
        if not pm:
            continue
        poms.append({
            'codi_fitxa': '',
            'descripcio': pm.nom_client or '',
            'pom_master_id': pm.id,
            'pom_codi': pm.codi_client,
            'pom_nom': pm.nom_client,
            'match_type': 'manual',
            'confidence': 'HIGH',
            'values': {},
            'actiu': True,
            'ordre': len(poms),
        })

    session.poms_extrets = poms
    session.estat = 'MESURES'
    session.save(update_fields=['poms_extrets', 'estat', 'actualitzat_at'])

    actius = [p for p in poms if p.get('actiu')]
    return Response({'ok': True, 'estat': session.estat,
                     'poms_actius': len(actius), 'poms_extrets': poms}, status=200)


# ═══════════════════════════ W3 — Mesures ═══════════════════════════
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_session_grading_preview_view(request, token):
    """
    POST /api/v1/import-sessions/<token>/grading-preview/  (Pas W3 — preview de grading)

    Calcula el grading SENSE persistir (reutilitza el motor via preview_graded_specs) per
    omplir talles buides a la taula del wizard. NO crea SizeFitting/GradedSpec — això és
    feina del desament definitiu (W5). Rep base_values {pom_master_id: valor}.
    """
    from fhort.models_app.models import ImportSession
    from fhort.pom.services import preview_graded_specs

    session = ImportSession.objects.filter(token=token).select_related('model').first()
    if not session:
        return Response({'error': 'Sessió no trobada'}, status=404)
    model = session.model
    if not model:
        return Response({'error': 'La sessió no té model associat'}, status=400)
    if not model.grading_rule_set_id:
        return Response({'error': 'El model no té GradingRuleSet configurat', 'grading': {}}, status=400)

    raw = request.data.get('base_values') or {}
    base_values = {}
    for k, v in raw.items():
        if not str(k).isdigit() or v in (None, ''):
            continue
        try:
            base_values[int(k)] = float(v)
        except (TypeError, ValueError):
            continue

    grading_avisos: list[str] = []
    grading = preview_graded_specs(model, base_values, warnings=grading_avisos)
    # Claus a string per a JSON consistent al frontend.
    grading = {str(pid): row for pid, row in grading.items()}
    return Response({'grading': grading, 'base_size': model.base_size_label,
                     'size_run': (model.size_run_model or '').split('·'),
                     'avisos': grading_avisos}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def import_session_mesures_view(request, token):
    """
    PATCH /api/v1/import-sessions/<token>/mesures/  (Pas W3 — desa valors de la taula)

    Rep mesures [{pom_master_id, talla_label, valor}]. Desa a session.resultat['mesures'].
    estat→'MESURES_OK'.
    """
    from fhort.models_app.models import ImportSession

    session = ImportSession.objects.filter(token=token).first()
    if not session:
        return Response({'error': 'Sessió no trobada'}, status=404)

    mesures = request.data.get('mesures') or []
    # Normalitza a llista neta de {pom_master_id, talla_label, valor}.
    net = []
    for m in mesures:
        pid = m.get('pom_master_id')
        talla = m.get('talla_label')
        valor = m.get('valor')
        if pid is None or talla in (None, ''):
            continue
        net.append({'pom_master_id': pid, 'talla_label': talla, 'valor': valor})

    session.resultat = {**(session.resultat or {}), 'mesures': net}
    # 1C-2a: si el wizard declara el mode dels valors (absoluts/deltes), desar-lo per al W5.
    valors_mode = request.data.get('valors_mode')
    if valors_mode in ('absoluts', 'deltes'):
        session.resultat = {**session.resultat, 'valors_mode': valors_mode}
    session.estat = 'MESURES_OK'
    session.save(update_fields=['resultat', 'estat', 'actualitzat_at'])

    return Response({'ok': True, 'estat': session.estat, 'n_valors': len(net)}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_session_library_prefill_view(request, token):
    """
    POST /api/v1/import-sessions/<token>/library-prefill/  (1C-3 — pont fitxa → Size Library)

    Construeix el prefill ENRIQUIT per a la Size Library des de l'extracció ja feta: run + base
    + target + POMs amb els seus valors per talla, en ABSOLUTS. Si la fitxa era en mode 'deltes',
    converteix amb deltes_a_absoluts (1C-2a) abans d'enviar (el camí Library deriva amb
    detect_grading, que espera absoluts). NO crea res: només llegeix la sessió. Robust: degrada.
    """
    from fhort.models_app.models import ImportSession

    session = ImportSession.objects.filter(token=token).select_related('model').first()
    if not session:
        return Response({'error': 'Sessió no trobada'}, status=404)
    model = session.model

    # valors {pid:{talla:valor}} des de les mesures desades (els valors EDITATS al W3).
    valors = {}
    for m in (session.resultat or {}).get('mesures', []):
        try:
            pid = int(m['pom_master_id'])
        except (KeyError, TypeError, ValueError):
            continue
        if m.get('talla_label') in (None, ''):
            continue
        valors.setdefault(pid, {})[m['talla_label']] = m.get('valor')

    base_size = ((model.base_size_label if model else '') or '').strip()
    run = [s.strip() for s in ((model.size_run_model if model else '') or '')
           .replace(';', '·').split('·') if s.strip()]

    # Mode deltes → absoluts ABANS d'enviar (reusa 1C-2a; una sola font de conversió).
    if ((session.resultat or {}).get('valors_mode') or 'absoluts') == 'deltes' and run and base_size:
        from fhort.pom.grading_utils import deltes_a_absoluts
        valors = deltes_a_absoluts(valors, base_size, run)

    # codi_client per pom des del CATÀLEG (font autoritativa per pid), no de la còpia
    # serialitzada a poms_extrets. find_pom_master al camí Library matcheja codi_client__iexact
    # (Strategy 1, exact_code HIGH) → round-trip garantit al MATEIX POMMaster.
    from fhort.pom.models import POMMaster
    codi_by_pid = {
        pm.id: (pm.codi_client or '')
        for pm in POMMaster.objects.filter(id__in=list(valors.keys()))
    }

    poms = []
    for pid, vals in valors.items():
        net = {k: v for k, v in (vals or {}).items() if v not in (None, '')}
        if net:
            poms.append({'pom_codi': codi_by_pid.get(pid) or '', 'valors': net})

    target_codi = (model.target if model else '') or ''
    if not target_codi and model and model.size_system_id:
        _t = model.size_system.targets.first()
        if _t:
            target_codi = _t.codi

    # Classificació del model resolta a IDs (com 1B, codi__iexact) perquè el drawer pugui crear
    # el SizingProfile (target+construction+fit+garment_type). garment_type ja és FK al model.
    from fhort.pom.models import ConstructionType, FitType
    rs_constr = (ConstructionType.objects.filter(codi__iexact=model.construction).first()
                 if (model and model.construction) else None)
    rs_fit = (FitType.objects.filter(codi__iexact=model.fit_type).first()
              if (model and model.fit_type) else None)

    return Response({
        'target_codi': target_codi or None,
        'labels': run,
        'base_size': base_size or None,
        'poms': poms,
        'construction_id': rs_constr.id if rs_constr else None,
        'fit_type_id': rs_fit.id if rs_fit else None,
        'garment_type_id': (model.garment_type_id if model else None),
        'import_session_token': str(session.token),
        'model_id': model.id if model else None,
    }, status=200)


# ═══════════════════════════ W4 — Teixit ═══════════════════════════
_TEIXIT_FIELDS = ['fabric_main', 'fabric_composition', 'shrinkage_type', 'shrinkage_warp',
                  'shrinkage_weft', 'shrinkage_pct', 'shrinkage_iso_key', 'fabric_notes']


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def import_session_teixit_view(request, token):
    """
    PATCH /api/v1/import-sessions/<token>/teixit/  (Pas W4 — desa el teixit a la sessió)

    Desa els camps de teixit a session.resultat['teixit'] (no toca el model fins a W5).
    Opcional (es pot ometre amb skip).
    """
    from fhort.models_app.models import ImportSession

    session = ImportSession.objects.filter(token=token).first()
    if not session:
        return Response({'error': 'Sessió no trobada'}, status=404)

    teixit = {f: request.data.get(f) for f in _TEIXIT_FIELDS if f in request.data}
    session.resultat = {**(session.resultat or {}), 'teixit': teixit}
    session.save(update_fields=['resultat', 'actualitzat_at'])
    return Response({'ok': True, 'teixit': teixit}, status=200)


# ═══════════════════════════ W5 — Confirmar i guardar ═══════════════════════════
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_session_confirmar_view(request, token):
    """
    POST /api/v1/import-sessions/<token>/confirmar/  (Pas W5 — desament definitiu)

    NORMES INAMOVIBLES:
      1. Mana el document: crea NOMÉS BaseMeasurement dels POMs confirmats (Pas 2). NO
         materialitza la plantilla de l'item (no crida materialize_poms_view) i elimina les
         files buides de plantilla preexistents (base_value_cm=None).
      2. SizeFitting contenidor (sense GradingVersion/GradedSpec): el grading PROPAGAT no es
         reté; es projecta conscientment des de la regla del model (deltes+breaks), D-10.
      3. NO sessions de fitting (cap FittingSession).
      4. PDF → ModelFitxer(tipus='DOCUMENT', versio NNN, naming {codi}_DOCUMENT_{NNN});
         re-import → versio_anterior apunta a l'anterior.
      5. session.estat='CONFIRMAT'.
    """
    import os
    from django.db import transaction
    from django.core.files.base import ContentFile

    from fhort.models_app.models import ImportSession, BaseMeasurement, ModelFitxer
    from fhort.accounts.models import UserProfile
    from fhort.pom.models import POMMaster
    from fhort.fitting.models import SizeFitting
    from fhort.models_app.matching import match_size_system

    session = ImportSession.objects.filter(token=token).select_related('model').first()
    if not session:
        return Response({'error': 'Sessió no trobada'}, status=404)
    model = session.model
    if not model:
        return Response({'error': 'La sessió no té model associat'}, status=400)

    user_profile = UserProfile.objects.filter(user=request.user).first()

    poms = [p for p in (session.poms_extrets or []) if p.get('actiu') and p.get('pom_master_id')]
    if not poms:
        return Response({'error': 'No hi ha POMs confirmats per importar'}, status=400)

    # mesures (Pas 3) → {pom_id: {talla: valor}}
    valors = {}
    for m in (session.resultat or {}).get('mesures', []):
        try:
            pid = int(m['pom_master_id'])
        except (KeyError, TypeError, ValueError):
            continue
        valors.setdefault(pid, {})[m['talla_label']] = m['valor']

    with transaction.atomic():
        # ── B1 · APARELLAMENT = LLEI DE LA SESSIÓ. Si el pas 1 va fixar `talla_mapping`, el confirm
        # el consumeix EN EXCLUSIVA (document→model tenant) i NO re-deriva res. Si no hi és (sessions
        # anteriors al canvi), fallback al remap canònic C1b + avís. El save de model es difereix.
        meta_update_fields = []
        _to_tenant = None
        doc_to_model = {}
        extraccio = (session.resultat or {}).get('extraccio') or {}
        run_detectat = extraccio.get('sizes') or []
        base_detectada = extraccio.get('base_size')
        talla_mapping = (session.run_conciliat or {}).get('talla_mapping')

        if talla_mapping:
            for _p in talla_mapping:
                _d, _m = (_p or {}).get('document'), (_p or {}).get('model')
                if _d and _m:
                    doc_to_model[_d] = _m
            valors = {pid: {doc_to_model.get(k, k): v for k, v in d.items()}
                      for pid, d in valors.items()}
            # El run i la base del model ja parlen tenant (el pas 1 no els toca); res a re-derivar.
        else:
            session.avisos = (session.avisos or []) + [
                "Sessió sense taula d'aparellament de talles (anterior al canvi): s'aplica el remap "
                "canònic automàtic. Reobre el pas 1 per fixar l'aparellament si cal."]
            target_codi = model.target or ''
            if not target_codi and model.size_system_id:
                _ss_target = model.size_system.targets.first()
                if _ss_target:
                    target_codi = _ss_target.codi
            if run_detectat and base_detectada and target_codi:
                mr = match_size_system(target_codi, run_detectat, base_detectada)
                if mr.ok and mr.score == 1.0 and mr.base_ok:
                    model.size_system = mr.size_system
                    meta_update_fields = ['size_system', 'base_size_label', 'size_run_model']
                else:
                    session.avisos = (session.avisos or []) + [
                        f"Size system no reconciliat automàticament (match {mr.score:.0%} per target "
                        f"'{target_codi}'): es manté la classificació manual."]
            if model.size_system_id:
                from fhort.pom.models import SizeDefinition
                _tenant_labels = list(SizeDefinition.objects.filter(size_system=model.size_system)
                                      .values_list('etiqueta', flat=True))
                _canon_to_tenant, _canon_ambig = {}, set()
                for _e in _tenant_labels:
                    _c = canonical_size_label(_e)
                    if _c in _canon_to_tenant and _canon_to_tenant[_c] != _e:
                        _canon_ambig.add(_c)
                    _canon_to_tenant[_c] = _e
                _no_resol = set()

                def _to_tenant(lbl):
                    _c = canonical_size_label(lbl)
                    if _c in _canon_ambig:
                        _no_resol.add(lbl)
                        return lbl
                    _t = _canon_to_tenant.get(_c)
                    if _t is None:
                        _no_resol.add(lbl)
                        return lbl
                    return _t

                valors = {pid: {_to_tenant(k): v for k, v in d.items()} for pid, d in valors.items()}
                if base_detectada:
                    base_detectada = _to_tenant(base_detectada)
                if meta_update_fields:
                    model.base_size_label = base_detectada or model.base_size_label
                    model.size_run_model = '·'.join(_to_tenant(l) for l in run_detectat)
                if _no_resol:
                    session.avisos = (session.avisos or []) + [
                        "Etiquetes del document sense equivalència única al sistema "
                        f"'{model.size_system.codi}': {', '.join(sorted(_no_resol))} (no traduïdes)."]

        # base_size = etiqueta tenant del model (mai document).
        base_size = (model.base_size_label or '').strip()
        if _to_tenant is not None and base_size:
            base_size = _to_tenant(base_size)

        # ── 1C-2a. Si la fitxa portava INCREMENTS (deltes) en comptes de mesures absolutes,
        # convertir-los a absoluts AQUÍ — abans dels TRES consumidors de `valors`
        # (BaseMeasurement a 1693, chain de GradedSpec a 1733, derive_grading_rule_set) —
        # perquè tots tres rebin absoluts i detect_grading/derive quedin INTACTES. Default
        # 'absoluts' = camí d'avui sense canvi (la conversió només s'activa si s'ha declarat).
        valors_mode = (session.resultat or {}).get('valors_mode') or 'absoluts'
        if valors_mode == 'deltes':
            from fhort.pom.grading_utils import deltes_a_absoluts
            run_ordenat_conv = [
                s.strip() for s in (model.size_run_model or '').replace(';', '·').split('·')
                if s.strip()
            ]
            valors = deltes_a_absoluts(valors, base_size, run_ordenat_conv)

        # ── C1c (D2, guard DUR). La talla base del model ha de tenir valor a la fitxa (després del
        # remap). Si no hi és entre les etiquetes dels valors → 422 ABANS de cap escriptura: mai més
        # base_value_cm=None silenciós. set_rollback per desfer el save de metadata diferit (si n'hi
        # hagués). Els valors ja parlen la llengua-tenant per C1b.
        _val_labels = set()
        for _d in valors.values():
            _val_labels |= {k for k, v in _d.items() if v is not None}
        if base_size and base_size not in _val_labels:
            transaction.set_rollback(True)
            return Response({
                'error': ("La talla base «%s» no té valor a la fitxa (etiquetes disponibles: %s)."
                          % (base_size, ', '.join(sorted(_val_labels)) or '—')),
                'tipus': 'base_size_absent',
                'base_size': base_size,
                'etiquetes': sorted(_val_labels),
            }, status=422)

        # ── POMs confirmats resolts (pur, sense escriure): necessari per a la detecció de grading.
        resolved = []
        confirmed_pom_ids = []
        for i, p in enumerate(poms):
            pm = POMMaster.objects.filter(id=int(p['pom_master_id'])).first()
            if not pm:
                continue
            resolved.append((i, p, pm))
            confirmed_pom_ids.append(int(p['pom_master_id']))

        # ══ PRE-FLIGHT SOROLL (B1, LLEI DEL SOROLL 2026-07-22) ═══════════════════════════
        # «El model s'alimenta de realitat: tot element sense contingut real és soroll i ES
        # PROPOSA eliminar, amb confirmació.»
        #
        # La norma 1 («mana el document») ja existia, però NOMÉS de cara al que el document
        # SÍ porta. La contrapartida faltava: els POMs vius del model que el document NO
        # menciona sobrevivien actius EN SILENCI, i la fitxa importada quedava contaminada
        # amb mesures que el client no demanava (§B3.3 de la DIAGNOSI_GTI_PLANTILLA).
        #
        # Ara es PROPOSEN, mai s'esborren sols: 409 amb la llista → el tècnic tria
        # `poda_choice`. Mateix mecanisme que `container_choice` (no cal pantalla nova).
        # Sempre soft (is_active=False), mai DELETE dur.
        poda_choice = (request.data.get('poda_choice') or '').strip().lower()  # 'desactivar'|'conservar'
        orfes = list(
            BaseMeasurement.objects
            .filter(model=model, is_active=True, base_value_cm__isnull=False)
            .exclude(pom_id__in=confirmed_pom_ids)
            .select_related('pom')
        )
        if orfes and poda_choice not in ('desactivar', 'conservar'):
            return Response({
                'conflict': True,
                'tipus': 'poms_no_mencionats',
                'poms': [{
                    'pom_id': bm.pom_id,
                    'codi': bm.pom.codi_client or '',
                    'nom': bm.nom_fitxa or getattr(bm.pom, 'nom_ca', '') or '',
                    'base_value_cm': bm.base_value_cm,
                    'origen': bm.origen,
                } for bm in orfes],
                'n': len(orfes),
                'message': ("Aquest model té mesures vives que el document no menciona. "
                            "Vols desactivar-les (el model s'alimenta de la realitat del "
                            "document) o conservar-les?"),
            }, status=409)

        # ══ PRE-FLIGHT PRECEDÈNCIA MANUAL (B2) ══════════════════════════════════════════
        # Precedència d'orígens MÍNIMA — només la que aquesta llei necessita, no el mapa
        # complet (§B3.3: `ORIGEN_CHOICES` segueix sent una llista plana i això NO ho canvia).
        #
        # Una fila origen='MANUAL' amb valor és patrimoni escrit a mà per un tècnic. Fins ara
        # l'`update_or_create` de sota la trepitjava sense mirar-se l'origen previ — l'única
        # comparació d'origen de tot el repo vivia a `models_app/views.py:827`. El patró de
        # guard que se segueix és `pom/dictionary_service.py:158` (`preserve_manual`).
        #
        # No es decideix per ell en cap direcció: es PROPOSA, com el soroll.
        manual_choice = (request.data.get('manual_choice') or '').strip().lower()  # 'sobreescriure'|'respectar'
        _doc_pom_ids = {int(p['pom_master_id']) for _i, p, _pm in resolved
                        if valors.get(int(p['pom_master_id']), {}).get(base_size) is not None}
        manuals = list(
            BaseMeasurement.objects
            .filter(model=model, is_active=True, origen='MANUAL',
                    base_value_cm__isnull=False, pom_id__in=_doc_pom_ids)
            .select_related('pom')
        ) if _doc_pom_ids else []
        if manuals and manual_choice not in ('sobreescriure', 'respectar'):
            return Response({
                'conflict': True,
                'tipus': 'manual_trepitjat',
                'poms': [{
                    'pom_id': bm.pom_id,
                    'codi': bm.pom.codi_client or '',
                    'nom': bm.nom_fitxa or getattr(bm.pom, 'nom_ca', '') or '',
                    'valor_manual': bm.base_value_cm,
                    'valor_document': valors.get(bm.pom_id, {}).get(base_size),
                } for bm in manuals],
                'n': len(manuals),
                'message': ("El document porta valor per a mesures introduïdes MANUALMENT. "
                            "Vols que mani el document o que es respecti el valor manual?"),
            }, status=409)
        # POMs on el valor manual guanya: l'escriptura de sota els salta.
        respectats_pom_ids = ({bm.pom_id for bm in manuals}
                              if manual_choice == 'respectar' else set())

        # ══ PRE-FLIGHT GRADING (D1) — detecció (pura) + matcher + GATES 409, TOT abans d'escriure.
        # El contenidor de client (GradingRuleSet origen=CLIENT_RUN) és ÚNIC per (customer +
        # size_system + garment_type_item + fit). Les decisions que exigeixen tria del tècnic surten
        # amb 409 SENSE haver tocat cap fila → les mesures (sobirania del model) ja no es fan
        # rollback per una decisió de grading. derive_rules_from_fitxa és pur (no persisteix).
        from fhort.pom.grading_utils import (
            derive_rules_from_fitxa, resolve_grading_container, classifica_fitxa_vs_contenidor)
        from fhort.pom.models import FitType, Target, ConstructionType, GradingRuleSet
        from fhort.models_app.services import (
            materialize_model_grading_rules_from_specs, afegeix_regles_al_contenidor)
        from fhort.pom.services import maybe_learn_customer_alias

        grading_avisos = []
        grading_bloqueigs = []
        # REFERENT (llei S24): el run del DOCUMENT en llengua-tenant. Es passa pel MATEIX
        # aparellament que ja s'ha aplicat a `valors` més amunt (taula de la sessió si n'hi ha,
        # remap canònic si no) perquè referent i valors parlin la mateixa llengua. Abans aquí
        # s'hi passava `model.size_run_model`: amb un run de model més ESTRET que el document,
        # els deltes es calculaven entre veïns falsos i el break sortia fabricat (bug 166).
        run_document = list(run_detectat or [])
        if talla_mapping:
            run_document = [doc_to_model.get(l, l) for l in run_document]
        elif _to_tenant is not None:
            run_document = [_to_tenant(l) for l in run_document]
        # (a) DETECCIÓ de les regles de la fitxa (pur, sense persistència; reusa detect_grading).
        fitxa_specs = derive_rules_from_fitxa(
            run_document=run_document, base_size=base_size, valors=valors,
            confirmed_pom_ids=confirmed_pom_ids, size_system=model.size_system,
            avisos=grading_avisos, bloqueigs=grading_bloqueigs)
        # BLOQUEIG d'integritat (llei 2026-07-08): cap regla d'una taula incompleta. Abans
        # aquest camí només avisava i persistia igualment — el forat del bug 166. 422 ABANS de
        # cap escriptura de grading; `set_rollback` perquè som dins de l'atomic i les mesures
        # ja escrites més amunt no poden quedar confirmades amb un error a la mà.
        if grading_bloqueigs:
            incompletes = [b for b in grading_bloqueigs if b['tipus'] == 'fila_incompleta']
            desconegudes = [e for b in grading_bloqueigs
                            if b['tipus'] == 'talles_desconegudes' for e in b['etiquetes']]
            if desconegudes:
                msg = ("El document porta talles que el sistema de talles del model no coneix: "
                       f"{', '.join(desconegudes)}.")
            else:
                msg = (f"{len(incompletes)} mesura/es no tenen valor per a totes les talles del "
                       "document; no se'n pot derivar cap regla sense inventar-ne el trencament. "
                       "Completa-les al pas de mesures o desmarca-les.")
            transaction.set_rollback(True)
            return Response({
                'error': msg + ' (cap regla desada)',
                'tipus': 'grading_taula_incompleta',
                'bloqueigs': grading_bloqueigs,
                'run_document': run_document,
                'avisos': grading_avisos,
            }, status=422)
        base_def_id = fitxa_specs[0]['talla_base_id'] if fitxa_specs else None

        # (b) MATCHER ÚNIC (M1): resol fit (codi→FK) i EL contenidor per la llei del contenidor
        # (N1 identitat exacta · N2 ampli item-NULL del mateix client · N3 cap).
        rs_fit = FitType.objects.filter(codi__iexact=model.fit_type).first() if model.fit_type else None
        gti = model.garment_type_item
        grp_codi = model.garment_group.codi if model.garment_group_id else None
        res_cont = resolve_grading_container(
            model.customer, model.size_system, model.target, model.construction,
            rs_fit, grp_codi, garment_type_item=gti)
        container = res_cont['container']
        container_choice = (request.data.get('container_choice') or '').strip().lower()  # 'create'|'no_container'

        cls = None
        if fitxa_specs:
            # (c) DECISIONS que exigeixen tria conscient → 409 SENSE cap escriptura (cap set_rollback:
            # res s'ha tocat encara; la metadata reconciliada tampoc, es desa al bloc d'escriptura).
            if res_cont['motiu'] == 'ambiguous':
                return Response({
                    'conflict': True,
                    'tipus': 'container_ambigu',
                    'candidats': [{'id': c.id, 'nom': c.nom} for c in res_cont['candidats']],
                    'message': ("Hi ha més d'un contenidor de graduació possible per a aquesta "
                                "combinació. Cal triar-ne un abans de continuar."),
                }, status=409)
            if container is None and container_choice not in ('create', 'no_container'):
                return Response({
                    'conflict': True,
                    'tipus': 'container_absent',
                    'customer_nom': str(getattr(model.customer, 'nom', '') or model.customer or ''),
                    'garment_type_item': (getattr(gti, 'name', '') if gti else ''),
                    'size_system': str(getattr(model.size_system, 'nom', '') or model.size_system or ''),
                    'fit': (rs_fit.codi if rs_fit else (model.fit_type or '')),
                    'n_regles': len(fitxa_specs),
                    'message': ("Aquest client no té graduació per a aquesta combinació "
                                "(peça + sistema de talles + fit). Vols crear-ne el contenidor?"),
                }, status=409)
            if container is not None:
                # M3 — llei del contenidor INTOCABLE (classificació pura; s'aplica a l'escriptura).
                cls = classifica_fitxa_vs_contenidor(fitxa_specs, container)

        # ════════════════════════════════ ESCRIPTURA ════════════════════════════════
        # Totes les decisions que podien retornar 409/422 ja s'han pres. Persistim la metadata
        # reconciliada del model (diferida del pre-flight) i escrivim les mesures (sobirania).
        if meta_update_fields:
            model.save(update_fields=meta_update_fields)

        # ── 1. Mana el document: neteja files buides i crea NOMÉS els confirmats.
        #
        # B1 (LLEI DEL SOROLL) — CRITERI TRIAT per a les files sense valor:
        #   · origen TEMPLATE/ITEM_STANDARD → **DELETE dur**. Són bastida de plantilla que
        #     mai va ser realitat: ningú les va mesurar, no hi ha res a auditar i deixar-les
        #     com a inactives només acumularia runa que un segon import tornaria a trobar.
        #   · qualsevol altre origen (MANUAL, IMPORTED, FITTED…) → **SOFT** (is_active=False)
        #     + entrada al MeasurementChangeLog. Algú les va crear conscientment encara que
        #     ara no portin valor; la seva desaparició ha de deixar rastre.
        _TEMPLATE_ORIGENS = ('TEMPLATE', 'ITEM_STANDARD')
        _buides = BaseMeasurement.objects.filter(model=model, base_value_cm__isnull=True)
        _buides.filter(origen__in=_TEMPLATE_ORIGENS).delete()
        n_buides_soft = 0
        for bm in _buides.exclude(origen__in=_TEMPLATE_ORIGENS).exclude(is_active=False):
            bm.is_active = False
            bm._desactivat = True
            bm._changed_by = request.user
            bm._motiu = 'import: fila sense valor (soroll)'
            bm.save(update_fields=['is_active'])
            n_buides_soft += 1

        n_bm = 0
        n_bm_valors = 0
        n_manual_respectats = 0
        for i, p, pm in resolved:
            base_val = valors.get(int(p['pom_master_id']), {}).get(base_size)
            # B2 — el tècnic ha decidit que el valor manual mana: el document no el trepitja.
            # La fila queda tal com està (valor, origen MANUAL i tot); només és patrimoni que
            # sobreviu a l'import, no una fila nova.
            if pm.id in respectats_pom_ids:
                n_manual_respectats += 1
                n_bm += 1
                n_bm_valors += 1
                # El vincle codi↔POM SÍ s'aprèn: la tria és sobre el VALOR, no sobre el
                # vocabulari. El document ha anomenat aquest POM i això és realitat.
                maybe_learn_customer_alias(
                    model.customer, p.get('codi_fitxa'), p.get('descripcio'), pm,
                    origen='IMPORT', nomes_si_manual=False)
                continue
            _defaults = {
                'base_value_cm': base_val,
                'nom_fitxa': p.get('codi_fitxa') or '',
                'origen': 'IMPORTED',
                'is_active': True,
                'ordre': i,
                'notes': p.get('descripcio') or '',
            }
            # B2: només escrivim tolerància si el document en porta (asimètrica, contracte Size Check).
            if p.get('tol_minus') is not None:
                _defaults['tolerancia_minus'] = p['tol_minus']
            if p.get('tol_plus') is not None:
                _defaults['tolerancia_plus'] = p['tol_plus']
            BaseMeasurement.objects.update_or_create(model=model, pom=pm, defaults=_defaults)
            n_bm += 1
            if base_val is not None:
                n_bm_valors += 1
            # Biblioteca del client (QA-S8-R1): aprèn de tot vincle ferm confirmat (idempotent). El
            # guard de pom/services.py aplica: si un ALTRE codi ja reclama el POM, l'àlies neix
            # pendent_revisio=True i find_pom_master no l'auto-vincula.
            maybe_learn_customer_alias(
                model.customer, p.get('codi_fitxa'), p.get('descripcio'), pm,
                origen='IMPORT', nomes_si_manual=False)

        # ── 1b. PODA CONFIRMADA (B1). Els POMs vius que el document no menciona: el tècnic
        # ja ha triat al pre-flight. SOFT sempre (is_active=False) + MeasurementChangeLog;
        # cap DELETE dur — la mesura va existir i el model n'ha de guardar memòria.
        n_podats = 0
        if orfes and poda_choice == 'desactivar':
            for bm in orfes:
                bm.is_active = False
                bm._desactivat = True
                bm._changed_by = request.user
                bm._motiu = 'import: POM no mencionat pel document (poda confirmada)'
                bm.save(update_fields=['is_active'])
                n_podats += 1
            grading_avisos.append(
                f"Poda confirmada: {n_podats} POM(s) que el document no menciona s'han "
                f"desactivat (soft, amb registre al log de mesures).")
        elif orfes and poda_choice == 'conservar':
            grading_avisos.append(
                f"{len(orfes)} POM(s) vius que el document NO menciona s'han CONSERVAT per "
                f"decisió del tècnic: la fitxa del model els segueix incloent.")
        if n_manual_respectats:
            grading_avisos.append(
                f"{n_manual_respectats} mesura/es d'origen MANUAL s'han RESPECTAT per decisió "
                f"del tècnic: el valor del document no les ha trepitjat.")
        elif manuals and manual_choice == 'sobreescriure':
            grading_avisos.append(
                f"{len(manuals)} mesura/es d'origen MANUAL s'han sobreescrit amb el valor del "
                f"document per decisió del tècnic.")
        if n_buides_soft:
            grading_avisos.append(
                f"{n_buides_soft} fila/es sense valor i d'origen no-plantilla s'han "
                f"desactivat (soft) en lloc d'esborrar-se.")

        # ── 2. Identificador del contenidor SF.
        next_num = 1
        while SizeFitting.objects.filter(model=model, numero=next_num).exists():
            next_num += 1
        sf_codi = f"IMP-{model.id}-{next_num}"
        while SizeFitting.objects.filter(codi=sf_codi).exists():
            next_num += 1
            sf_codi = f"IMP-{model.id}-{next_num}"

        # (d) APLICAR (escriptures) — savepoint intern amb degradació amb gràcia.
        new_rule_set = model.grading_rule_set
        resident_specs = None
        prev_grs_id = model.grading_rule_set_id
        if fitxa_specs:
            try:
                with transaction.atomic():
                    if container is None:
                        if container_choice == 'no_container':
                            # SOBIRANIA: el model queda amb regles residents pròpies, sense contenidor.
                            model.grading_rule_set = None
                            model.save(update_fields=['grading_rule_set'])
                            new_rule_set = None
                            resident_specs = fitxa_specs
                            grading_avisos.append(
                                "Contenidor no creat (decisió del tècnic): el model queda amb "
                                "regles residents pròpies (sobirania de dades).")
                        else:  # 'create' — M3: CREAR contenidor AMPLI (item=NULL) per defecte.
                            rs_target = (Target.objects.filter(codi__iexact=model.target).first()
                                         if model.target else None)
                            rs_constr = (ConstructionType.objects.filter(codi__iexact=model.construction).first()
                                         if model.construction else None)
                            nom_cont = " · ".join(p for p in [
                                str(getattr(model.customer, 'nom', '') or model.customer or ''),
                                str(getattr(model.garment_group, 'nom', '') or model.garment_group or ''),
                                str(getattr(model.size_system, 'nom', '') or model.size_system or ''),
                            ] if p)[:120] or f"Contenidor client · {model.codi_intern}"
                            # AMPLI: garment_type_item=NULL (abast per garment_group FK → el troba M1
                            # nivell 2 la propera vegada). NO és la identitat fina (item), és de món.
                            container = GradingRuleSet.objects.create(
                                nom=nom_cont, size_system=model.size_system,
                                garment_group=model.garment_group, garment_type_item=None,
                                construction=rs_constr, fit_type=rs_fit,
                                is_system_default=False, actiu=True,
                                origen=GradingRuleSet.ORIGEN_CLIENT_RUN, customer=model.customer)
                            if rs_target:
                                container.targets.add(rs_target)
                            afegeix_regles_al_contenidor(container, fitxa_specs, base_def_id)
                            model.grading_rule_set = container
                            model.save(update_fields=['grading_rule_set'])
                            new_rule_set = container
                            resident_specs = fitxa_specs
                            grading_avisos.append(
                                f"Contenidor de client AMPLI NOU creat #{container.id} '{container.nom}' "
                                f"(el client estrenava aquesta combinació) amb {len(fitxa_specs)} regla(es).")
                    elif not container.regles.exists():
                        # CONTENIDOR ESQUELET (0 regles) → sembrar-lo des de la fitxa és LEGÍTIM (M3).
                        # Amb 0 regles, cls['amplia'] == totes les specs (res per coincidir/divergir).
                        if cls['amplia']:
                            afegeix_regles_al_contenidor(container, cls['amplia'], base_def_id)
                        model.grading_rule_set = container
                        model.save(update_fields=['grading_rule_set'])
                        new_rule_set = container
                        resident_specs = fitxa_specs
                        grading_avisos.append(
                            f"Contenidor esquelet #{container.id} '{container.nom}' sembrat des de la "
                            f"fitxa ({len(fitxa_specs)} regla(es)).")
                    else:
                        # CONTENIDOR AMB REGLES → INTOCABLE (llei M3): el catàleg del client NO es toca.
                        #   coincideix (sembra) → res: el model hereta la regla del contenidor.
                        #   divergeix (conflicte) + POM nou (amplia) → ModelGradingOverride per-talla
                        #     (valors de la fitxa a les talles no-base) + WATCHPOINT. El motor llegeix
                        #     l'override amb prioritat sobre la projecció del contenidor
                        #     (services._load_model_overrides); base i talla-base van a BaseMeasurement.
                        from fhort.pom.grading_utils import _norm as _norm_label
                        from fhort.models_app.models import ModelGradingOverride
                        model.grading_rule_set = container
                        model.save(update_fields=['grading_rule_set'])
                        new_rule_set = container
                        # SENSE residents: el contenidor mana (all-or-nothing de _load_grading_rules).
                        # Neteja residents ranços perquè l'herència del contenidor no quedi tapada.
                        model.grading_rules.all().delete()
                        resident_specs = None
                        base_norm = _norm_label(base_size)
                        pom_divergents = ([c['pom_id'] for c in cls['conflicte']]
                                          + [s['pom_id'] for s in cls['amplia']])
                        n_ovr = 0
                        for pom_id in pom_divergents:
                            for label, val in (valors.get(pom_id) or {}).items():
                                if val is None or _norm_label(label) == base_norm:
                                    continue
                                ModelGradingOverride.objects.update_or_create(
                                    model=model, pom_id=pom_id, size_label=label,
                                    defaults={'value_cm': float(val), 'created_by': user_profile,
                                              'motiu': ("Import W5 — divergència vs catàleg del "
                                                        "contenidor (INTOCABLE)")})
                                n_ovr += 1
                        if cls['conflicte']:
                            grading_avisos.append(
                                f"⚠️ Watchpoint: {len(cls['conflicte'])} POM(s) divergeixen del catàleg "
                                f"del contenidor #{container.id} (INTOCABLE); desats com a override "
                                f"per-talla al model (el catàleg del client NO s'ha tocat).")
                        if cls['amplia']:
                            grading_avisos.append(
                                f"⚠️ Watchpoint: {len(cls['amplia'])} POM(s) de la fitxa no són al "
                                f"contenidor #{container.id}; desats com a override per-talla al model "
                                f"(contenidor intocable).")
                        if cls['sembra']:
                            grading_avisos.append(
                                f"{len(cls['sembra'])} POM(s) coincideixen amb el catàleg: el model "
                                f"els hereta del contenidor #{container.id} (sense override).")
                    # SEMBRA SELECTIVA de residents (origen=IMPORTED); el motor les llegeix amb prioritat.
                    if resident_specs is not None:
                        materialize_model_grading_rules_from_specs(
                            model, resident_specs, origen='IMPORTED')
            except Exception as e:
                model.grading_rule_set_id = prev_grs_id
                new_rule_set = model.grading_rule_set
                grading_avisos.append(
                    f"Grading no aplicat (error en desar: {e}); es manté el ruleset previ del model.")
        n_rules = model.grading_rules.count()

        # ── 3. SizeFitting CONTENIDOR per a la projecció CONSCIENT (D-10) — només quan no hi ha
        # conflicte pendent. L'import reté base + deltes + breaks (ModelGradingRule); el grading
        # PROPAGAT no es reté: el projecta el motor després, des de la regla vigent del model
        # (generate_grading_view crea/omple la versió sobre AQUEST SF). Estat/segellat (D-1) NO aquí.
        size_fitting = SizeFitting.objects.create(
            model=model, numero=next_num, codi=sf_codi, tipus='SizeSet',
            estat='Tancat', base_tancada=True, creat_per=user_profile,
            notes="Importació guiada (wizard). Contenidor; grading propagat NO retingut "
                  "(es projecta conscientment des de la regla del model, D-10).",
        )
        n_specs = 0   # cap valor propagat persistit a l'import

        # ── C3 (D3, defensa en profunditat). Amb el guard C1c això no hauria de passar; si tot i
        # així cap POM ha rebut valor de talla base, avís destacat (mai un "OK" enganyós amb 0 valors).
        if n_bm and not n_bm_valors:
            grading_avisos.append(
                f"⚠️ S'han desat {n_bm} POM(s) SENSE cap valor de talla base "
                f"(base '{base_size}'): revisa l'alineació d'etiquetes de la fitxa.")

        if grading_avisos:
            session.avisos = (session.avisos or []) + grading_avisos

        # ── 4. PDF/document → ModelFitxer(tipus='DOCUMENT') amb versionat (re-import = v2).
        #     Delega la invariant a save_model_file (B2): re-import encadena (versio_anterior)
        #     i deixa is_current correcte. El naming {codi}_DOCUMENT_{NNN} es passa explícit.
        doc_fitxer = None
        if session.document:
            from .services_fitxers import save_model_file
            anterior = ModelFitxer.objects.filter(
                model=model, tipus='DOCUMENT',
            ).order_by('-id').first()
            num = (anterior.versio + 1) if anterior else 1
            ext = os.path.splitext(session.document.name)[1] or '.pdf'
            nom = f"{model.codi_intern}_DOCUMENT_{num:03d}{ext}"
            try:
                session.document.open('rb')
                doc_bytes = session.document.read()
            finally:
                session.document.close()
            doc_fitxer = save_model_file(
                model, ContentFile(doc_bytes),
                versio_anterior=anterior, tipus='DOCUMENT',
                origen='upload', nom=nom,
            )
            doc_fitxer.pujat_per = user_profile
            doc_fitxer.descripcio = 'Document origen de la importació guiada.'
            doc_fitxer.save(update_fields=['pujat_per', 'descripcio'])

        # ── 5. Teixit (si informat al Pas 4) → camps del model.
        teixit = (session.resultat or {}).get('teixit') or {}
        teixit_aplicat = False
        for f in _TEIXIT_FIELDS:
            if f in teixit and teixit[f] not in (None, ''):
                setattr(model, f, teixit[f])
                teixit_aplicat = True
        if teixit_aplicat:
            model.save()

        # ── 6. Tanca la sessió.
        session.estat = 'CONFIRMAT'
        session.save(update_fields=['estat', 'avisos', 'actualitzat_at'])

    return Response({
        'ok': True,
        'estat': session.estat,
        'model_id': model.id,
        'model_codi': model.codi_intern,
        'base_measurements': n_bm,
        'base_measurements_amb_valor': n_bm_valors,
        # B1 — el resultat de la poda mai és silenciós.
        'poms_podats': n_podats,
        'poms_conservats': (len(orfes) if poda_choice == 'conservar' else 0),
        'files_buides_desactivades': n_buides_soft,
        'manual_respectats': n_manual_respectats,
        'graded_specs': n_specs,
        'size_fitting': size_fitting.codi,
        'document_fitxer': (doc_fitxer.nom_fitxer if doc_fitxer else None),
        'teixit_aplicat': teixit_aplicat,
        'grading_rule_set': (new_rule_set.nom if new_rule_set else None),
        'grading_rules': n_rules,
        'grading_avisos': grading_avisos,
        'message': f'Importació confirmada: {n_bm} POMs ({n_bm_valors} amb valor de base), regla '
                   f'(deltes+breaks) retinguda al model; grading propagat pendent de projecció conscient.',
    }, status=201)
