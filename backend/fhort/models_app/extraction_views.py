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


def _create_pom_alert(model, pom_master, client_code, description, confidence, match_type):
    """Create a POMAlert for uncertain matches (MEDIUM/LOW) or newly created POMs."""
    try:
        from fhort.fitting.models import POMAlert
        # Real POMAlert.tipus choices: 'desviacio', 'fora_rang', 'manca', 'conflicte'.
        # New POMs → 'manca' (not in the catalog); medium matches → 'conflicte'.
        tipus = 'manca' if match_type == 'auto_created' else 'conflicte'
        if match_type == 'auto_created':
            missatge = (
                f'POM nou creat automàticament: "{client_code}" ({description}). '
                f'Cal completar la descripció, creixements i vincular al catàleg global.'
            )
        else:
            missatge = (
                f'POM "{client_code}" ({description}) importat amb confiança {confidence} '
                f'via {match_type}. Assignat a: {pom_master.codi_client} ({pom_master.nom_client}). '
                f"Verificar que l'assignació és correcta."
            )
        POMAlert.objects.create(
            model=model,
            pom=pom_master,
            tipus=tipus,
            missatge=missatge,
            origen='IMPORTACIO',
            estat='Pendent',
            creat_per='sistema',
        )
    except Exception:
        # Do not block the import if creating the alert fails.
        pass


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


def _parse_excel_poms(file_bytes: bytes):
    """Parse determinista d'una fitxa Excel de POMs (via ràpida del wizard).

    Cerca la fila capçalera (cel·la A == 'POM') i en llegeix: A=codi, C=descripció,
    D=DIM, i de la col E endavant les columnes de talla (excloent les que la capçalera
    marca com a tolerància, 'tol'). Retorna (poms, talles):
      poms  = [{'codi_fitxa', 'descripcio', 'dim', 'values': {talla: float}}]
      talles = [etiquetes de talla, en ordre]
    Si no troba cap capçalera 'POM', retorna ([], [])."""
    import openpyxl

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

    wb = openpyxl.load_workbook(_io.BytesIO(file_bytes), data_only=True, read_only=True)
    try:
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            header_idx = None
            for idx, row in enumerate(rows):
                a = row[0] if row else None
                if a is not None and str(a).strip().upper() == 'POM':
                    header_idx = idx
                    break
            if header_idx is None:
                continue

            header = rows[header_idx]
            # Columnes de talla: col E (índex 4) endavant, excloent toleràncies.
            size_cols = []  # [(col_index, label)]
            for ci in range(4, len(header)):
                label = header[ci]
                if label is None or str(label).strip() == '':
                    continue
                if 'tol' in str(label).strip().lower():
                    continue
                size_cols.append((ci, str(label).strip()))
            talles = [lbl for _, lbl in size_cols]

            poms = []
            for row in rows[header_idx + 1:]:
                a = row[0] if row else None
                if a is None or str(a).strip() == '':
                    break  # fi del bloc de dades
                values = {}
                for ci, lbl in size_cols:
                    if ci < len(row):
                        nv = _num(row[ci])
                        if nv is not None:
                            values[lbl] = nv
                desc = row[2] if len(row) > 2 and row[2] is not None else ''
                poms.append({
                    'codi_fitxa': str(a).strip(),
                    'descripcio': str(desc).strip(),
                    'dim': _num(row[3]) if len(row) > 3 else None,
                    'values': values,
                })
            return poms, talles
    finally:
        wb.close()
    return [], []


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
    PATCH /api/v1/import-sessions/<token>/talles/  (Pas W1 — reconciliació de talles)

    Rep:
      - talles_seleccionades: llista de labels (del document) que el tècnic confirma com a
        columnes finals de la taula.
      - accio: 'alinear' | 'mapejar' | 'res'.
      - mapeig_talles: dict opcional {label_doc: label_model} per a 'mapejar'.

    Gating per labels: una talla seleccionada té "destí" si coincideix amb el run configurat,
    amb una talla del SizeSystem, o amb una entrada del mapeig. Si 'alinear' → adopta el run
    seleccionat com a run del model (totes passen a tenir destí). ready=True quan TOTES en tenen.
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
    accio = (request.data.get('accio') or 'res').strip()
    mapeig = request.data.get('mapeig_talles') or {}

    # Run configurat actual del model.
    configurat = [
        s.strip() for s in (model.size_run_model or '').replace(';', '·').split('·') if s.strip()
    ]

    # 'alinear' → adopta el run seleccionat (del document) com a run del model.
    if accio == 'alinear' and talles_sel:
        model.size_run_model = '·'.join(talles_sel)
        model.save(update_fields=['size_run_model'])
        configurat = list(talles_sel)

    # Labels disponibles com a destí: run configurat + talles del SizeSystem + mapeig.
    system_labels = []
    if model.size_system_id:
        system_labels = list(model.size_system.talles.values_list('etiqueta', flat=True))
    destins = {_norm_label(x) for x in configurat} | {_norm_label(x) for x in system_labels}
    destins |= {_norm_label(v) for v in mapeig.values()}
    mapeig_norm = {_norm_label(k) for k in mapeig.keys()}

    sense_desti = [t for t in talles_sel
                   if _norm_label(t) not in destins and _norm_label(t) not in mapeig_norm]
    ready = bool(talles_sel) and not sense_desti

    rc = dict(session.run_conciliat or {})
    rc.update({
        'configurat': configurat,
        'seleccionades': talles_sel,
        'mapeig': mapeig,
        'sense_desti': sense_desti,
        'estat': 'RESOLT' if ready else 'PENDENT',
    })
    session.run_conciliat = rc
    if ready:
        session.estat = 'TALLES'
    session.save(update_fields=['run_conciliat', 'estat', 'actualitzat_at'])

    # Quan el gating bloqueja (PENDENT), oferim les dades per pre-omplir el Size Map Setup
    # (wizard de runs de client) sense canviar cap model: el tècnic pot configurar un run nou.
    size_map_prefill = None
    if not ready:
        target_codi = model.target or ''
        if not target_codi and model.size_system_id:
            _ss_target = model.size_system.targets.first()
            if _ss_target:
                target_codi = _ss_target.codi
        size_map_prefill = {
            'target_codi': target_codi or None,
            'labels': talles_sel or sense_desti,
            'base_size': model.base_size_label or None,
            'import_session_token': str(session.token),
            'model_id': model.id,
        }

    return Response({
        'ready': ready,
        'estat': session.estat,
        'run_conciliat': rc,
        'size_run_model': model.size_run_model,
        'sense_desti': sense_desti,
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
    # NEW — Brownie positional POMs (override the previous ones on collision, per spec
    # S19; duplicate keys make the last one win).
    'waist position':                  'waist position distance',
    'hip position':                    'hip position distance',
    'straight back body length':       'body length back',
    'front armhole curve':             'armhole',
    'collar width':                    'neck tie length',
    'body zip length':                 'zip',
    'lining length at center front':   'lining',
    'lining length at center back':    'lining',
    'lining bottom width along hem':   'lining bottom',
}


def find_pom_master(code, description):
    """
    Find the most suitable POMMaster.
    Return (pom_master, match_type, confidence)
    confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'NO_MATCH'
    """
    from fhort.pom.models import POMMaster

    # Strategy 1 — exact match by codi_client. Va PRIMER: un codi_client EXACTE sempre ha de
    # guanyar un match per prefix (p.ex. 'SH DR' → 'SH DR', no 'SH'). Abans anava DESPRÉS del
    # root-prefix i 'SH DR' es resolia erròniament a 'SH' (col·lisió que perdia 'SH DR').
    if code:
        pm = POMMaster.objects.filter(codi_client__iexact=code, actiu=True).first()
        if pm:
            return pm, 'exact_code', 'HIGH'

    # Strategy 0 — codis posicionals lletra+dígit (D1, G2s...): sense exacte, prova el root de
    # lletres inicials. DESPRÉS de l'exacte perquè no segresti codis amb sufix com 'SH DR'.
    if code:
        m = _re.match(r'^([A-Za-z]+)', code)
        if m and m.group(1) != code:
            root = m.group(1)
            pm = POMMaster.objects.filter(codi_client__iexact=root, actiu=True).first()
            if pm:
                return pm, 'root_code_match', 'MEDIUM'

    if not description:
        return None, 'no_match', 'NO_MATCH'

    desc_clean = description.lower().strip()
    desc_base = _re.sub(r'\s*[\(\[].*?[\)\]]', '', desc_clean).strip()

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

    # Strategy 5 — pure numeric codes → lining.
    if code and code.isdigit():
        desc_lower = (description or '').lower()
        if 'lining' in desc_lower:
            for pm in POMMaster.objects.select_related('pom_global').filter(actiu=True):
                nom = (pm.nom_client or '').lower()
                if 'lining' in nom:
                    return pm, 'numeric_lining_match', 'MEDIUM'

    return None, 'no_match', 'NO_MATCH'


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


def _extraccio_via_excel(session, api_key):
    """Via ràpida d'extracció per a fitxes Excel: parse determinista + revisió Sonnet,
    SENSE la crida Opus. Retorna la MATEIXA forma de resposta que la via PDF/imatge."""
    # 1. Bytes del document desat al Pas 1.
    try:
        session.document.open('rb')
        file_bytes = session.document.read()
    finally:
        session.document.close()

    # 2. Parse determinista.
    raw_poms, talles_detectades = _parse_excel_poms(file_bytes)

    # 3. Sense POMs llegibles → error clar.
    if not raw_poms:
        return Response({'error': 'No s\'ha pogut llegir l\'Excel'}, status=400)

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

    # 7-8. Matching POM + format IDÈNTIC al de la via Opus.
    poms_extrets = []
    for i, p in enumerate(raw_poms):
        pm, match_type, confidence = find_pom_master(p['codi_fitxa'], p['descripcio'])
        poms_extrets.append({
            'codi_fitxa': p['codi_fitxa'],
            'descripcio': p['descripcio'],
            'pom_master_id': pm.id if pm else None,
            'pom_codi': pm.codi_client if pm else None,
            'pom_nom': (pm.nom_client if pm else None),
            'match_type': match_type,
            'confidence': confidence,
            'values': p['values'],
            'actiu': True,
            'ordre': i,
        })

    # 9. Talles.
    sizes = [str(t) for t in talles_detectades]

    # 10. Persisteix. NOTA: `session.poms_extrets` és la font de veritat per als passos
    # W2-confirmació (:1216) i W3-mesures (:1415); cal desar-la (paritat amb la via Opus).
    session.resultat = {**(session.resultat or {}),
                        'extraccio': {'via': 'excel', 'header': {}, 'sizes': sizes},
                        'grading_status': 'ok'}
    session.poms_extrets = poms_extrets
    session.estat = 'POMS'
    session.save(update_fields=['resultat', 'poms_extrets', 'estat', 'actualitzat_at'])

    # 11. Resposta amb EXACTAMENT el mateix format que la via PDF/imatge (:1180-1188).
    return Response({
        'estat': 'POMS',
        'poms_extrets': poms_extrets,
        'header': {},
        'base_size': sizes[0] if sizes else None,
        'sizes': sizes,
        'grading_status': {'status': 'ok', 'detail': ''},
        'avisos': revision.get('warnings', []),
    }, status=200)


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
    # PDF/imatge segueixen el camí actual sense cap canvi.
    doc_name = session.document.name or ''
    if doc_name.lower().endswith(('.xlsx', '.xls')):
        return _extraccio_via_excel(session, api_key)

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

    # Matching POM per fila.
    poms_extrets = []
    n_low, n_nomatch = 0, 0
    for i, msr in enumerate(measurements):
        codi_fitxa = (msr.get('client_code') or msr.get('code') or '').strip()
        descripcio = (msr.get('description') or '').strip()
        pm, match_type, confidence = find_pom_master(codi_fitxa, descripcio)
        if confidence == 'LOW':
            n_low += 1
        if pm is None:
            n_nomatch += 1
        poms_extrets.append({
            'codi_fitxa': codi_fitxa,
            'descripcio': descripcio,
            'pom_master_id': pm.id if pm else None,
            'pom_codi': pm.codi_client if pm else None,
            'pom_nom': (pm.nom_client if pm else None),
            'match_type': match_type,
            'confidence': confidence,
            'values': msr.get('values') or {},
            'actiu': bool(pm),  # per defecte només actius els que tenen match
            'ordre': i,
        })

    if n_nomatch:
        avisos.append(f'{n_nomatch} POM(s) sense match al catàleg — cal revisar o afegir manualment.')
    if n_low:
        avisos.append(f'{n_low} POM(s) amb confiança baixa — recomanada revisió.')

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
      4. PDF → ModelFitxer(categoria='Document', versio NNN, naming {codi}_DOCUMENT_{NNN});
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
        # ── 0c. Reconciliació size_system/base/run des de l'extracció (tanca Capa 0).
        # Deriva el sistema NET del run detectat de la fitxa via match_size_system, en
        # comptes de confiar en la classificació del wizard (que pot haver triat un sistema
        # incorrecte). Estricte: només re-apunta amb match perfecte (afecta grading i DXF).
        extraccio = (session.resultat or {}).get('extraccio') or {}
        run_detectat = extraccio.get('sizes') or []
        base_detectada = extraccio.get('base_size')
        target_codi = model.target or ''
        if not target_codi and model.size_system_id:
            _ss_target = model.size_system.targets.first()
            if _ss_target:
                target_codi = _ss_target.codi
        if run_detectat and base_detectada and target_codi:
            mr = match_size_system(target_codi, run_detectat, base_detectada)
            if mr.ok and mr.score == 1.0 and mr.base_ok:
                model.size_system = mr.size_system
                model.base_size_label = base_detectada
                model.size_run_model = '·'.join(run_detectat)
                model.save(update_fields=['size_system', 'base_size_label', 'size_run_model'])
            else:
                session.avisos = (session.avisos or []) + [
                    f"Size system no reconciliat automàticament (match {mr.score:.0%} per target "
                    f"'{target_codi}'): es manté la classificació manual. Revisa que el sistema "
                    f"de talles assignat sigui correcte per a aquest run."]
        else:
            session.avisos = (session.avisos or []) + [
                "Reconciliació de talles omesa: manca run detectat, base o target a la sessió."]

        # base_size reflecteix el valor (possiblement) reconciliat.
        base_size = (model.base_size_label or '').strip()

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

        # ── 1. Mana el document: neteja files buides de plantilla i crea NOMÉS els confirmats.
        BaseMeasurement.objects.filter(model=model, base_value_cm__isnull=True).delete()

        n_bm = 0
        confirmed_pom_ids = []
        for i, p in enumerate(poms):
            pid = int(p['pom_master_id'])
            pm = POMMaster.objects.filter(id=pid).first()
            if not pm:
                continue
            base_val = valors.get(pid, {}).get(base_size)
            BaseMeasurement.objects.update_or_create(
                model=model, pom=pm,
                defaults={
                    'base_value_cm': base_val,
                    'nom_fitxa': p.get('codi_fitxa') or '',
                    'origen': 'IMPORTED',
                    'is_active': True,
                    'ordre': i,
                    'notes': p.get('descripcio') or '',
                },
            )
            confirmed_pom_ids.append(pid)
            n_bm += 1

        # ── 2. SizeFitting CONTENIDOR per a la projecció CONSCIENT (D-10).
        # PRINCIPI (sobirania): l'import CALCULA tot el grid (per derivar deltes+breaks) però RETÉ
        # NOMÉS base + deltes + breaks (ModelGradingRule, derivats a 3b). NO reté el grading PROPAGAT
        # (GradingVersion + GradedSpec) com a veritat del model: retenir-lo col·lisiona amb el sembrat
        # del motor i fa dubtar el tècnic. El propagat el PROJECTA el motor després, conscientment,
        # des de la regla vigent del model (generate_grading_view crea/omple la versió sobre AQUEST SF).
        # El SF es manté com a contenidor; el seu estat/segellat (D-1) NO es decideix aquí.
        next_num = 1
        while SizeFitting.objects.filter(model=model, numero=next_num).exists():
            next_num += 1
        sf_codi = f"IMP-{model.id}-{next_num}"
        while SizeFitting.objects.filter(codi=sf_codi).exists():
            next_num += 1
            sf_codi = f"IMP-{model.id}-{next_num}"
        size_fitting = SizeFitting.objects.create(
            model=model, numero=next_num, codi=sf_codi, tipus='SizeSet',
            estat='Tancat', base_tancada=True, creat_per=user_profile,
            notes="Importació guiada (wizard). Contenidor; grading propagat NO retingut "
                  "(es projecta conscientment des de la regla del model, D-10).",
        )
        # NO es crea GradingVersion ni GradedSpec a l'import: el grading propagat no és veritat del
        # model fins a la projecció conscient. n_specs=0 (cap valor propagat persistit).
        n_specs = 0

        # ── 3b. Derivar la regla de grading des dels valors i re-apuntar-hi el model.
        # La derivació (detect_grading per POM + dedup + anti-proliferació 1D + crear/
        # reutilitzar el ruleset) viu a pom.grading_utils.derive_grading_rule_set (pura de
        # model: 1C-1) perquè la Size Library la pugui cridar amb dades del fitxer. Aquí el
        # W5 la crida amb dades del model i fa el re-apuntat A FORA. Chain de GradedSpec no
        # tocat. Degradació amb gràcia: un error de desament no atura l'import.
        from fhort.pom.grading_utils import derive_grading_rule_set

        new_rule_set = None
        n_rules = 0
        grading_avisos = []
        prev_grs_id = model.grading_rule_set_id  # per restaurar la FK si el desament peta
        try:
            with transaction.atomic():
                new_rule_set = derive_grading_rule_set(
                    size_run_model=model.size_run_model,
                    base_size=base_size,
                    valors=valors,
                    confirmed_pom_ids=confirmed_pom_ids,
                    size_system=model.size_system,
                    garment_group=model.garment_group,
                    target_codi=model.target,
                    construction_codi=model.construction,
                    fit_type_codi=model.fit_type,
                    nom=f"Importació fitxa · {model.codi_intern}",
                    nom_sufix_unic=size_fitting.codi,
                    avisos=grading_avisos,
                )
                if new_rule_set is not None:
                    model.grading_rule_set = new_rule_set
                    model.save(update_fields=['grading_rule_set'])
                    # PG-2 Cas A: materialitza les regles residents (origen=IMPORTED). El motor
                    # (PG-1) les llegeix amb prioritat; el ruleset extern queda com a punter/rastre.
                    from fhort.models_app.services import materialize_model_grading_rules
                    materialize_model_grading_rules(
                        model, new_rule_set.regles.all(), origen='IMPORTED')
                    # PG-3 Cas A: compara el grading materialitzat (del document) amb el canònic
                    # de la Library que encaixaria i emet advertència. NOMÉS informa: embolcallat
                    # en try propi perquè un error de comparació NO faci rollback del grading ja
                    # materialitzat (degradació gràcil — no bloqueja, no muta grading).
                    try:
                        from fhort.pom.grading_utils import (
                            cerca_canonic_equivalent, grading_rules_match)
                        canonic = cerca_canonic_equivalent(model)
                        if canonic is None:
                            grading_avisos.append(
                                "Grading específic per aquest model: cap graduació canònica de "
                                "la Library hi encaixa.")
                        else:
                            ok, divs = grading_rules_match(
                                model.grading_rules.all(), canonic.regles.all())
                            if not ok:
                                detall = "; ".join(
                                    f"{d['pom_codi']}: {d['detall']}" for d in divs[:5])
                                grading_avisos.append(
                                    f"El grading del document difereix del canònic "
                                    f"'{canonic.nom}': {detall}")
                            # encaixa → cap append (silenci)
                    except Exception as _cmp_e:
                        grading_avisos.append(
                            f"Comparació amb el grading canònic omesa (error: {_cmp_e}).")
        except Exception as e:
            # Rollback del savepoint (creació + re-apuntat junts): la fila del ruleset ja no
            # existeix. Restaurem la FK en memòria AQUÍ, abans de qualsevol model.save()
            # posterior de l'import (p.ex. teixit), perquè no escrigui un id mort.
            model.grading_rule_set_id = prev_grs_id
            new_rule_set = None
            grading_avisos.append(
                f"Grading no derivat (error en desar regles: {e}); es manté el ruleset previ.")
        n_rules = new_rule_set.regles.count() if new_rule_set else 0

        if grading_avisos:
            session.avisos = (session.avisos or []) + grading_avisos

        # ── 4. PDF/document → ModelFitxer(categoria='Document') amb versionat (re-import = v2).
        doc_fitxer = None
        if session.document:
            anterior = ModelFitxer.objects.filter(
                model=model, categoria='Document',
            ).order_by('-id').first()
            num = 1
            if anterior:
                try:
                    num = int(str(anterior.versio).strip()) + 1
                except (TypeError, ValueError):
                    num = 2
            ext = os.path.splitext(session.document.name)[1] or '.pdf'
            nom = f"{model.codi_intern}_DOCUMENT_{num:03d}{ext}"
            try:
                session.document.open('rb')
                doc_bytes = session.document.read()
            finally:
                session.document.close()
            doc_fitxer = ModelFitxer(
                model=model, nom_fitxer=nom, categoria='Document', tipus='DOCUMENT',
                versio=f'{num:03d}', versio_anterior=anterior, path_servidor=nom,
                mida_bytes=len(doc_bytes), pujat_per=user_profile,
                descripcio='Document origen de la importació guiada.',
            )
            doc_fitxer.fitxer.save(nom, ContentFile(doc_bytes), save=True)

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
        'graded_specs': n_specs,
        'size_fitting': size_fitting.codi,
        'document_fitxer': (doc_fitxer.nom_fitxer if doc_fitxer else None),
        'teixit_aplicat': teixit_aplicat,
        'grading_rule_set': (new_rule_set.nom if new_rule_set else None),
        'grading_rules': n_rules,
        'grading_avisos': grading_avisos,
        'message': f'Importació confirmada: {n_bm} POMs, regla (deltes+breaks) retinguda al model; '
                   f'grading propagat pendent de projecció conscient.',
    }, status=201)
