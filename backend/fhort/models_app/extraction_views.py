# fhort/models_app/extraction_views.py
import datetime as _dt
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def extract_from_file_view(request):
    """
    POST /api/v1/models/extract-from-file/
    Multipart: file (required), generate_thumbnail (optional, default=true)

    Return the extraction JSON + the Design Freeze gate result.
    Does not create any Model — it is a preview/analysis operation.
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

    wizard_context = {
        'target_codi':        request.data.get('target_codi', ''),
        'garment_type_codi':  request.data.get('garment_type_codi', ''),
        'garment_type_nom':   request.data.get('garment_type_nom', ''),
        'size_system_codi':   request.data.get('size_system_codi', ''),
        'size_system_id':     request.data.get('size_system_id', ''),
        'size_run':           request.data.get('size_run', ''),
        'base_size':          request.data.get('base_size', ''),
        'construction_codi':  request.data.get('construction_codi', ''),
        'fit_type_codi':      request.data.get('fit_type_codi', ''),
    }

    try:
        from fhort.models_app.extraction_service import extract_from_file, check_design_freeze
        extracted = extract_from_file(file_bytes, file_obj.name, wizard_context)
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
        'wizard_context': wizard_context,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_from_extraction_view(request):
    """
    POST /api/v1/models/create-from-extraction/
    Body: {extracted: {...}, overrides: {...}}

    Create a Model + BaseMeasurements from the extraction JSON.
    Only works if design_freeze.pass == true.
    """
    extracted = request.data.get('extracted')
    overrides = request.data.get('overrides', {})
    wizard_context = request.data.get('wizard_context', {}) or {}

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

    # Apply user overrides, with fallback to wizard_context
    style_name = overrides.get('style_name') or val('style_name') or val('style_code')
    temporada = overrides.get('temporada') or val('season', 'SS')
    any_ = overrides.get('any') or val('year')
    base_size = overrides.get('base_size') or val('base_size') or wizard_context.get('base_size')

    # Fix A — normalized size_run (wizard as the last safety net)
    size_run_raw = (
        overrides.get('size_run')
        or val('size_run')
        or wizard_context.get('size_run')
    )
    size_run = normalize_size_run(size_run_raw)

    # Fix D — correct year (2 digits → 4, fallback to the current year)
    any_value = parse_any(any_)

    # Fix C — codi_client required for the pre_save signal (generates codi_intern)
    codi_client = (overrides.get('codi_client') or '').strip().upper()
    if not codi_client:
        ref = val('style_reference') or val('style_code') or ''
        codi_client = _re.sub(r'[^A-Z0-9]', '', str(ref).upper())[:6]
    if not codi_client:
        codi_client = _re.sub(r'[^A-Z]', '', str(style_name or 'IMP').upper())[:3]
    if not codi_client:
        codi_client = 'IMP'

    # codi_tenant: priority override > logged-in tenant > first chars of codi_client
    tenant_schema_for_codi = (
        request.tenant.schema_name if hasattr(request, 'tenant') and request.tenant else ''
    )
    codi_tenant = (
        overrides.get('codi_tenant')
        or tenant_schema_for_codi
        or codi_client
    )
    codi_tenant = (codi_tenant or 'IMP').upper()[:3]

    try:
        from django_tenants.utils import schema_context
        from fhort.models_app.models import Model, BaseMeasurement, ModelFitxer
        from fhort.pom.models import POMMaster, GarmentType

        tenant_schema = request.tenant.schema_name if hasattr(request, 'tenant') else 'fhort'

        with schema_context(tenant_schema):
            # garment_type is NOT NULL on the Model. Priorities:
            # 1) wizard_context.garment_type_codi → exact match by codi_client
            # 2) overrides.garment_type → match by name/code (heuristic)
            # 3) val('garment_type_code') / val('garment_type') → heuristic match
            # 4) first available GarmentType as fallback
            gt = None
            wiz_gt_codi = (wizard_context.get('garment_type_codi') or '').strip()
            if wiz_gt_codi:
                gt = GarmentType.objects.filter(codi_client__iexact=wiz_gt_codi).first()

            if gt is None:
                gt_hint = (
                    overrides.get('garment_type')
                    or val('garment_type_code')
                    or val('garment_type')
                    or ''
                )
                if gt_hint:
                    gt = (
                        GarmentType.objects.filter(codi_client__iexact=gt_hint).first()
                        or GarmentType.objects.filter(nom_client__icontains=gt_hint).first()
                        or GarmentType.objects.filter(codi_client__icontains=gt_hint).first()
                    )
            if gt is None:
                gt = GarmentType.objects.first()
            if gt is None:
                return Response(
                    {'error': 'No hi ha cap GarmentType configurat al tenant; cal sembrar-ne almenys un.'},
                    status=422,
                )

            # Create the model — or use the existing one if overrides.model_id
            model_id_override = overrides.get('model_id')
            if model_id_override:
                try:
                    model = Model.objects.get(id=int(model_id_override))
                    if base_size:
                        model.base_size_label = base_size
                    if size_run:
                        model.size_run_model = size_run
                    model.save()
                except Model.DoesNotExist:
                    return Response(
                        {'error': f'Model {model_id_override} no trobat'},
                        status=404,
                    )
            else:
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

            # === SIZE SYSTEM ===
            # Priority:
            #   1) explicit override (size_system = id)
            #   2) wizard_context.size_system_id (id) or size_system_codi (codi)
            #   3) heuristic (alpha + garment group).
            from fhort.pom.models import SizeSystem
            size_system_assigned = None
            size_system_id = overrides.get('size_system') or wizard_context.get('size_system_id')
            wiz_ss_codi = (wizard_context.get('size_system_codi') or '').strip()
            ss = None
            if size_system_id:
                try:
                    ss = SizeSystem.objects.get(id=size_system_id)
                except Exception:
                    ss = None
            if ss is None and wiz_ss_codi:
                ss = SizeSystem.objects.filter(codi__iexact=wiz_ss_codi).first()
            if ss is not None:
                model.size_system = ss
                model.save(update_fields=['size_system'])
                size_system_assigned = ss.codi
            else:
                sizes_list = [s for s in (size_run or '').split('·') if s]
                has_alpha = any(
                    s.upper() in ('XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL')
                    for s in sizes_list
                )
                garment_group_code = (extracted.get('garment_group_code') or '').upper()
                if has_alpha and garment_group_code in (
                    'DRESSES', 'TOPS', 'BOTTOMS', 'OUTERWEAR'
                ):
                    ss = SizeSystem.objects.filter(codi='ALPHA_EU_W').first()
                    if ss:
                        model.size_system = ss
                        model.save(update_fields=['size_system'])
                        size_system_assigned = ss.codi

            # Fix B — Match POMMaster with priorities: exact code, root-code
            # (positional codes like D1/G2s/Y5 → root D/G/Y), description,
            # explicit synonyms, POMGlobal nom_en, abbreviation.
            SYNONYMS = {
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
                # NEW — Brownie positional POMs (override the previous ones on
                # collision, per spec S19; duplicate keys in the session
                # file make the last one win).
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
                # Strategy 0 — positional letter+digit codes (D1, G2s...).
                # Only if the code has digits/suffix after the initial letters.
                if code:
                    m = _re.match(r'^([A-Za-z]+)', code)
                    if m and m.group(1) != code:
                        root = m.group(1)
                        pm = POMMaster.objects.filter(
                            codi_client__iexact=root, actiu=True,
                        ).first()
                        if pm:
                            return pm, 'root_code_match', 'MEDIUM'

                # Strategy 1 — exact match by codi_client.
                pm = POMMaster.objects.filter(
                    codi_client__iexact=code, actiu=True,
                ).first()
                if pm:
                    return pm, 'exact_code', 'HIGH'

                if not description:
                    return None, 'no_match', 'NO_MATCH'

                desc_clean = description.lower().strip()
                desc_base = _re.sub(r'\s*[\(\[].*?[\)\]]', '', desc_clean).strip()

                # Strategy 2 — explicit synonym (curated table).
                syn = SYNONYMS.get(desc_clean) or SYNONYMS.get(desc_base)
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

            poms_created = 0
            poms_skipped = []
            match_log = []

            for i, pom_data in enumerate(extracted.get('poms', [])):
                base_value = pom_data.get('base_value_cm')
                if not base_value:
                    continue

                code = pom_data.get('code', '') or ''
                description = pom_data.get('description', '') or ''

                pm, match_type, confidence = find_pom_master(code, description)

                if not pm:
                    # No match — create a new POMMaster marked as pending review.
                    nou_codi = f"{code}-M{model.id}"
                    if POMMaster.objects.filter(codi_client=nou_codi).exists():
                        nou_codi = f"{code}-M{model.id}-{_dt.datetime.now().strftime('%H%M%S')}"
                    pm = POMMaster.objects.create(
                        pom_global=None,
                        codi_client=nou_codi,
                        nom_client=description or code,
                        notes=(
                            f"Creat automàticament des d'importació. "
                            f"Codi original: {code}. Requereix revisió."
                        ),
                        actiu=True,
                        pendent_revisio=True,
                        origen_import=f"{model.nom_prenda} ({model.codi_intern})",
                    )
                    match_type = 'auto_created'
                    confidence = 'LOW'
                    match_log.append({
                        'code': code,
                        'pom': nou_codi,
                        'match_type': match_type,
                        'confidence': confidence,
                        'action': 'NOU POM creat — pendent de revisió',
                    })
                else:
                    match_log.append({
                        'code': code,
                        'pom': pm.codi_client,
                        'match_type': match_type,
                        'confidence': confidence,
                    })

                # Sprint 5B.1: tolerance from the AI extraction if present, else the catalogue POM.
                tol_minus = pom_data.get('tolerance_minus')
                tol_plus = pom_data.get('tolerance_plus')
                if tol_minus is None:
                    tol_minus = pm.tolerancia_default_minus
                if tol_plus is None:
                    tol_plus = pm.tolerancia_default_plus
                BaseMeasurement.objects.update_or_create(
                    model=model, pom=pm,
                    defaults={
                        'base_value_cm': base_value,
                        'nom_fitxa': code,
                        'origen': 'IMPORTED',
                        'is_active': True,
                        'notes': description,
                        'ordre': i,
                        'tolerancia_minus': tol_minus,
                        'tolerancia_plus': tol_plus,
                    },
                )
                poms_created += 1

                # Create an alert for uncertain matches or new POMs.
                if confidence in ('MEDIUM', 'LOW'):
                    _create_pom_alert(
                        model, pm, code, description, confidence, match_type,
                    )

                # Notify superadmin for new POMs (auto_created).
                if match_type == 'auto_created':
                    try:
                        from fhort.accounts.models import UserProfile
                        from django.core.mail import send_mail
                        from django.conf import settings

                        admin_emails = list(
                            UserProfile.objects
                            .filter(rol_nom__iexact='admin', actiu=True)
                            .values_list('user__email', flat=True)
                        )
                        admin_emails = [e for e in admin_emails if e]

                        if admin_emails and getattr(settings, 'EMAIL_HOST', None):
                            send_mail(
                                subject=f'[FHORT] Nou POM pendent de revisió: {code}',
                                message=(
                                    f"S'ha creat un nou POM durant la importació:\n\n"
                                    f"Codi client: {code}\n"
                                    f"Descripció: {description}\n"
                                    f"Model: {model.nom_prenda} ({model.codi_intern})\n\n"
                                    f"Accedeix al sistema per revisar i incorporar al catàleg global."
                                ),
                                from_email=getattr(
                                    settings, 'DEFAULT_FROM_EMAIL',
                                    'noreply@fhorttextile.tech',
                                ),
                                recipient_list=admin_emails,
                                fail_silently=True,
                            )
                    except Exception:
                        pass  # No bloquejar si falla l'email

            # Extract and save images from the PDF if it arrives in the request
            try:
                from fhort.models_app.extraction_service import extract_images_from_pdf
                from django.core.files.base import ContentFile

                pdf_file = request.FILES.get('file')
                if pdf_file and pdf_file.name.endswith('.pdf'):
                    pdf_bytes = pdf_file.read()
                    imatges = extract_images_from_pdf(pdf_bytes, model.codi_intern)

                    for img_data in imatges:
                        ultima = ModelFitxer.objects.filter(
                            model=model, tipus=img_data['tipus']
                        ).order_by('-id').first()
                        num = 1
                        if ultima and ultima.nom_fitxer:
                            try:
                                num = int(ultima.nom_fitxer.split('_')[-1].split('.')[0]) + 1
                            except Exception:
                                num = 2

                        nom = f'{model.codi_intern}_{img_data["tipus"]}_{num:03d}.{img_data["ext"]}'
                        content = ContentFile(img_data['bytes'], name=nom)
                        mf = ModelFitxer(
                            model=model,
                            nom_fitxer=nom,
                            categoria=img_data['categoria'],
                            tipus=img_data['tipus'],
                            versio=f'{num:03d}',
                            mida_bytes=len(img_data['bytes']),
                            path_servidor=nom,
                        )
                        mf.fitxer.save(nom, content, save=True)
            except Exception:
                pass

            # === GRADING: create SizeFitting → GradingVersion → GradedSpecs ===
            from fhort.fitting.models import SizeFitting, GradingVersion, GradedSpec

            grading_table = extracted.get('grading_table', []) or []
            graded_created = 0
            graded_skipped = []

            if grading_table and poms_created > 0:
                try:
                    from fhort.accounts.models import UserProfile
                    user_profile = UserProfile.objects.filter(user=request.user).first()
                except Exception:
                    user_profile = None

                if user_profile is None:
                    # SizeFitting.creat_per is NOT NULL — we cannot create the chain.
                    graded_skipped.append({
                        'reason': "No s'ha trobat UserProfile per a l'usuari; "
                                  'cal crear SizeFitting i grading manualment.',
                    })
                else:
                    try:
                        sf_codi = f"IMP-{model.id}-{_dt.date.today().strftime('%y%m%d')}"

                        size_fitting, _ = SizeFitting.objects.get_or_create(
                            model=model,
                            codi=sf_codi,
                            defaults={
                                'numero': 1,
                                'tipus': 'Proto',
                                'estat': 'BaseOberta',
                                'creat_per': user_profile,
                                'notes': 'Creat automàticament durant importació de fitxa tècnica',
                            },
                        )

                        grading_version, _ = GradingVersion.objects.get_or_create(
                            size_fitting=size_fitting,
                            version_number=1,
                            defaults={
                                'nom': 'Importació automàtica',
                                'aprovada': False,
                                'creat_per': user_profile,
                                'notes': 'Generat des de fitxa tècnica. Revisar i aprovar.',
                                'is_active': True,
                            },
                        )

                        # Map nom_fitxa → POMMaster from the already-created BaseMeasurements.
                        bm_map = {
                            bm.nom_fitxa: bm.pom
                            for bm in BaseMeasurement.objects.filter(model=model)
                            if bm.nom_fitxa
                        }

                        # B1 — If the wizard defined size_run, we limit grading
                        # to those sizes (filters out extra columns from the document).
                        # If size_run is empty, we keep the current behavior:
                        # we import every size that appears in the document.
                        wiz_size_run_str = wizard_context.get('size_run', '') or ''
                        wiz_size_labels = {
                            s.strip().upper()
                            for s in wiz_size_run_str.split('·')
                            if s.strip()
                        }

                        for row in grading_table:
                            code = row.get('code', '') or ''
                            values_by_size = row.get('values_by_size', {}) or {}

                            if not values_by_size:
                                continue

                            pom_master = bm_map.get(code)
                            if not pom_master:
                                graded_skipped.append({
                                    'code': code,
                                    'reason': 'No BaseMeasurement per aquest codi — POM no importat',
                                })
                                continue

                            bm = BaseMeasurement.objects.filter(
                                model=model, pom=pom_master,
                            ).first()
                            base_val = float(bm.base_value_cm) if bm else None

                            for size_label, value in values_by_size.items():
                                if value is None:
                                    continue
                                if (
                                    wiz_size_labels
                                    and str(size_label).strip().upper() not in wiz_size_labels
                                ):
                                    continue
                                try:
                                    v = float(value)
                                    grading_type = (
                                        'FIXED'
                                        if base_val is not None and abs(v - base_val) < 0.01
                                        else 'LINEAR'
                                    )
                                    GradedSpec.objects.update_or_create(
                                        grading_version=grading_version,
                                        pom=pom_master,
                                        size_label=str(size_label).strip(),
                                        defaults={
                                            'graded_value_cm': v,
                                            'grading_type_applied': grading_type,
                                            'increment_applied_cm': 0,
                                            'is_active': True,
                                        },
                                    )
                                    graded_created += 1
                                except Exception as e:
                                    graded_skipped.append({
                                        'code': code,
                                        'size': size_label,
                                        'reason': str(e),
                                    })

                    except Exception as e:
                        graded_skipped.append({
                            'reason': f'Error creant SizeFitting/GradingVersion: {e}',
                        })

            poms_pendents = [
                m['code'] for m in match_log
                if m.get('match_type') == 'auto_created'
            ]
            return Response({
                'model_id': model.id,
                'model_codi': model.codi_intern,
                'poms_created': poms_created,
                'poms_skipped': poms_skipped,
                'match_log': match_log,
                'graded_created': graded_created,
                'graded_skipped': graded_skipped,
                'size_run': model.size_run_model,
                'size_system': size_system_assigned,
                'size_discrepancy': extracted.get('size_discrepancy'),
                'poms_pendents': poms_pendents,
                'message': (
                    f'Model creat. {poms_created} POMs importats, '
                    f'{graded_created} valors de grading, '
                    f'{len(poms_skipped)} POMs pendents de revisió.'
                    + (
                        f' {len(poms_pendents)} POMs nous pendents de revisió.'
                        if poms_pendents else ''
                    )
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
