"""fhort/pom/size_map_views.py — Size Map Setup wizard (backend).

Wizard per, a partir d'una taula de mides de client, identificar si un SizeSystem
existent encaixa (REUTILITZAR), si cal derivar-ne un (CLONAR) o crear-ne un de nou
(CREAR), generar-ne el GradingRuleSet/GradingRule (detectant LINEAR/STEP/FIXED a
partir dels valors) i els SizingProfiles.

Tots els endpoints requereixen la capacitat CONFIGURE.
"""
import logging
import re

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from fhort.accounts.capabilities import HasCapability, CONFIGURE
from fhort.pom.grading_utils import _norm, detect_grading, derive_break_fields

logger = logging.getLogger(__name__)

# Llindar d'auto-vinculació del matcher (DIAGNOSI_POM_RESOLUCIO_RUN_2026-07-08): només els
# matches HIGH/MEDIUM auto-vinculen la fila. Un match dèbil (LOW — p.ex. el root-prefix, que és
# l'últim recurs) NO es vincula en silenci: la fila cau a pendents amb un suggeriment visible.
_POM_AUTOLINK_CONF = ('HIGH', 'MEDIUM')


def _apply_match_threshold(pom, conf):
    """Aplica el llindar: retorna (pom_efectiu, weak_suggestion).
    Si el match és per sota del llindar, desvincula (pom→None) i torna el nom suggerit perquè
    la UI el mostri com a pendent; mai una vinculació dubtosa en silenci."""
    if pom is not None and conf not in _POM_AUTOLINK_CONF:
        return None, pom.nom_client
    return pom, None


def _resolve_run_customer(data, ssid):
    """Customer d'AQUEST run per al matcher per àlies (N3, DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08).
    Prefereix el `customer_codi` explícit del wizard; si no, el del SizeSystem triat. Retorna un
    Customer o None (si None, find_pom_master salta l'estratègia d'àlies i resol per descripció)."""
    from fhort.tasks.models import Customer
    from fhort.pom.models import SizeSystem
    codi = ((data or {}).get('customer_codi') or '').strip()
    if not codi and ssid:
        codi = (SizeSystem.objects.filter(pk=ssid)
                .values_list('customer_codi', flat=True).first() or '').strip()
    if not codi:
        return None
    return Customer.objects.filter(codi=codi).first()


def _apply_many_to_one_guard(results):
    """GUARD anti-many-to-one (N3-P2): si DUES files del mateix document resolen al MATEIX POM per
    DESCRIPCIÓ/fuzzy, cap de les dues auto-vincula → totes a pendents amb avís explícit (marca
    `many_to_one`). Motiu: `GradingRule` és únic per (rule_set, pom); dues files que hi cauen
    col·lapsarien i la segona sobreescriuria la primera (l'origen de "ja vinculat per un altre
    codi"). L'ÀLIES exacte queda EXEMPT: un client pot etiquetar legítimament el mateix POM amb
    dos codis (Losan H.11 sleeve opening / H.16 cuff opening) → `match_type == 'alias_match'` no
    dispara el guard. Muta `results` in situ."""
    counts = {}
    for r in results:
        if r.get('pom_id') and r.get('match_type') != 'alias_match':
            counts[r['pom_id']] = counts.get(r['pom_id'], 0) + 1
    dup_ids = {pid for pid, n in counts.items() if n >= 2}
    if not dup_ids:
        return results
    for r in results:
        if r.get('pom_id') in dup_ids and r.get('match_type') != 'alias_match':
            r['weak_suggestion'] = r.get('pom_nom')  # suggeriment visible per a la vinculació manual
            r['pom_id'] = None
            r['pom_nom'] = None
            r['many_to_one'] = True
    return results


class _Configure(HasCapability):
    required_capability = CONFIGURE


def _unique_size_system_code(base: str):
    """Retorna (codi, NN) amb el primer NN que fa el codi únic dins el schema."""
    from fhort.pom.models import SizeSystem
    base = re.sub(r'[^A-Z0-9_]', '', (base or '').upper()).strip('_') or 'SYS'
    n = 1
    while True:
        codi = f"{base}_{n:02d}"
        if not SizeSystem.objects.filter(codi=codi).exists():
            return codi, n
        n += 1


def _target_nom(t) -> str:
    """Nom mostrable d'un Target (no té camp `nom`): prefereix català, cau a l'anglès."""
    if not t:
        return ''
    return t.nom_cat or t.nom_en or t.codi


def _customer_label(customer_codi: str) -> str:
    """Nom llegible del client (best-effort); cau al codi si no es resol."""
    if not customer_codi:
        return ''
    try:
        from fhort.tasks.models import Customer
        c = Customer.objects.filter(codi=customer_codi).first()
        if c and c.nom:
            return c.nom
    except Exception:
        pass
    return customer_codi


# ─────────────────────────────────────────────────────────────────────────────
# LOOKUPS — selectors del wizard (no hi ha endpoint de fit-types enlloc)
# ─────────────────────────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([_Configure])
def size_map_lookups_view(request):
    """GET size-map/lookups/ — targets, constructions, fit_types, garment_types actius."""
    try:
        from fhort.pom.models import Target, ConstructionType, FitType, GarmentType

        def _nom(o):
            return getattr(o, 'nom_cat', '') or getattr(o, 'nom_en', '') or o.codi

        targets = [{'codi': t.codi, 'nom': _nom(t)} for t in Target.objects.all().order_by('display_order')]
        constructions = [{'id': c.id, 'codi': c.codi, 'nom': _nom(c)}
                         for c in ConstructionType.objects.all().order_by('display_order')]
        fit_types = [{'id': f.id, 'codi': f.codi, 'nom': _nom(f)}
                     for f in FitType.objects.all().order_by('display_order')]
        garment_types = [{'id': g.id, 'codi': g.codi_client, 'nom': g.nom_client}
                         for g in GarmentType.objects.filter(actiu=True).order_by('nom_client')]
        return Response({
            'targets': targets,
            'constructions': constructions,
            'fit_types': fit_types,
            'garment_types': garment_types,
            'base_units': [
                {'codi': 'ALPHA', 'nom': 'Alpha (XS/S/M/L...)'},
                {'codi': 'NUMERIC_EU', 'nom': 'Numeric EU (34/36/38...)'},
                {'codi': 'NUMERIC_US', 'nom': 'Numeric US (0/2/4...)'},
                {'codi': 'CM_HEIGHT', 'nom': 'CM Height (50/56/62...)'},
                {'codi': 'MONTHS', 'nom': 'Months (0M/3M/6M...)'},
                {'codi': 'AGE_YEARS', 'nom': 'Age Years (6Y/8Y...)'},
            ],
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("size_map_lookups_view error")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# 3A — MATCH
# ─────────────────────────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([_Configure])
def size_map_match_view(request):
    """POST size-map/match/ — {target_codi, labels:[...], base_size}.

    Reutilitza match_size_system i recomana REUTILITZAR / CLONAR / CREAR.
    """
    try:
        from fhort.models_app.matching import match_size_system

        data = request.data or {}
        target_codi = data.get('target_codi')
        labels = data.get('labels') or []
        base_size = data.get('base_size') or ''

        mr = match_size_system(target_codi, labels, base_size)

        candidates = []
        if mr.size_system is not None:
            if mr.score >= 1.0 and mr.base_ok:
                rec = 'REUTILITZAR'
            elif mr.score >= 0.5:
                rec = 'CLONAR'
            else:
                rec = 'CREAR'
            candidates.append({
                'size_system_id': mr.size_system.id,
                'nom': mr.size_system.nom,
                'codi': mr.size_system.codi,
                'score': round(mr.score, 3),
                'unmatched_labels': mr.unmatched_labels,
                'base_ok': mr.base_ok,
                'warning': mr.warning or mr.error,
                'recomanacio': rec,
            })
            recomanacio = rec
        else:
            recomanacio = 'CREAR'

        return Response({'candidates': candidates, 'recomanacio': recomanacio})
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("size_map_match_view error")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# 3B — PREVIEW (SizeDefinitions previstes)
# ─────────────────────────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([_Configure])
def size_map_preview_view(request):
    """POST size-map/preview/ — llista de SizeDefinitions previstes (no persisteix).

    REUTILITZAR → talles del sistema existent.
    CLONAR      → talles existents + les de l'input (merge per etiqueta).
    CREAR       → només les de l'input.
    """
    try:
        from fhort.pom.models import SizeDefinition

        data = request.data or {}
        accio = data.get('accio') or 'CREAR'
        ssid = data.get('size_system_id')
        labels = data.get('labels') or []

        def _from_input(l, idx):
            return {
                'etiqueta': l.get('etiqueta'),
                'ordre': l.get('ordre', idx + 1),
                'valor_numeric': l.get('valor_numeric'),
                'age_months_min': l.get('age_months_min'),
                'age_months_max': l.get('age_months_max'),
                'body_height_cm': l.get('body_height_cm'),
                'origen': 'input',
            }

        merged = {}
        if accio in ('REUTILITZAR', 'CLONAR') and ssid:
            for d in SizeDefinition.objects.filter(size_system_id=ssid).order_by('ordre'):
                merged[_norm(d.etiqueta)] = {
                    'etiqueta': d.etiqueta,
                    'ordre': d.ordre,
                    'valor_numeric': float(d.valor_numeric) if d.valor_numeric is not None else None,
                    'age_months_min': d.age_months_min,
                    'age_months_max': d.age_months_max,
                    'body_height_cm': float(d.body_height_cm) if d.body_height_cm is not None else None,
                    'origen': 'existent',
                }

        if accio in ('CLONAR', 'CREAR'):
            for idx, l in enumerate(labels):
                merged[_norm(l.get('etiqueta'))] = _from_input(l, idx)

        out = sorted(merged.values(), key=lambda x: (x['ordre'] if x['ordre'] is not None else 9999))
        return Response({'size_definitions': out, 'count': len(out)})
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("size_map_preview_view error")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# 3C — GRADING PREVIEW (detecció LINEAR / STEP / FIXED)
# ─────────────────────────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([_Configure])
def size_map_grading_preview_view(request):
    """POST size-map/grading-preview/ — detecta la lògica de grading per POM.

    Input: {size_system_id (opt), base_size, taula:[{pom_codi_client, valors:{etiqueta:valor}}]}.
    Per cada POM: resol find_pom_master, calcula deltes per salt (format C: delta = increment
    respecte el veí cap a la base) i detecta LINEAR / STEP / FIXED. Cap persistència.
    """
    try:
        from fhort.pom.models import SizeDefinition
        from fhort.models_app.extraction_views import find_pom_master

        data = request.data or {}
        ssid = data.get('size_system_id')
        base_size = data.get('base_size') or ''
        taula = data.get('taula') or []
        customer = _resolve_run_customer(data, ssid)  # N3: matcher per àlies del client

        # Run ordenat: unió d'etiquetes presents, ordenades pel size_system si es dóna.
        all_labels = []
        for row in taula:
            for k in (row.get('valors') or {}).keys():
                if k not in all_labels:
                    all_labels.append(k)
        order_map = {}
        if ssid:
            for et, ordre in SizeDefinition.objects.filter(
                size_system_id=ssid).order_by('ordre').values_list('etiqueta', 'ordre'):
                order_map[_norm(et)] = ordre
        if order_map:
            run = sorted(all_labels, key=lambda l: order_map.get(_norm(l), 9999))
        else:
            run = list(all_labels)

        results = []
        for row in taula:
            codi = row.get('pom_codi_client')
            valors_raw = row.get('valors') or {}

            # descripció si el paste la porta (avui no); el fitxer SÍ → match per nom.
            pom, mtype, conf = find_pom_master(codi, row.get('descripcio') or '', customer=customer)
            pom, weak_suggestion = _apply_match_threshold(pom, conf)
            warning = ''
            if pom is None and not weak_suggestion:
                warning = f"POM '{codi}' no resolt al catàleg."

            # BLOQUEIG (integritat): taula incompleta → no derivar amb deltes parcials.
            missing = [s for s in run if valors_raw.get(s) is None] if run else []
            if missing:
                results.append({
                    'pom_codi_client': codi,
                    'pom_id': pom.id if pom else None,
                    'pom_nom': pom.nom_client if pom else None,
                    'match_type': mtype, 'confidence': conf,
                    'logica_detectada': None, 'increment': None, 'valors_step': None,
                    'increment_base': None, 'increment_break': None,
                    'talla_break_label': None, 'talla_break_pos': None,
                    'valors_calculats': {k: valors_raw.get(k) for k in valors_raw},
                    'weak_suggestion': weak_suggestion,
                    'incompleta': True, 'missing_sizes': missing,
                    'warning': warning,
                })
                continue

            det = detect_grading(valors_raw, run, base_size)
            if det['warning']:
                warning = (warning + ' ' if warning else '') + det['warning']

            ib, ibrk, tlabel, tpos = derive_break_fields(
                det['logica'], det['increment'], det['valors_step'], run)

            results.append({
                'pom_codi_client': codi,
                'pom_id': pom.id if pom else None,
                'pom_nom': pom.nom_client if pom else None,
                'match_type': mtype,
                'confidence': conf,
                'logica_detectada': det['logica'],
                'increment': det['increment'],
                'valors_step': det['valors_step'],
                'increment_base': ib,
                'increment_break': ibrk,
                'talla_break_label': tlabel,
                'talla_break_pos': tpos,
                'valors_calculats': {k: valors_raw.get(k) for k in valors_raw},
                'weak_suggestion': weak_suggestion,
                'incompleta': False, 'missing_sizes': [],
                'warning': warning,
            })

        _apply_many_to_one_guard(results)  # N3-P2: dues files → mateix POM per descripció → pendents
        return Response({'results': results, 'run': run, 'base_size': base_size})
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("size_map_grading_preview_view error")
        return Response({'error': str(e)}, status=500)


def _parse_grading_excel(file_bytes):
    """Parser Excel propi de la Size Library (format simple de graduació):
    capçalera a la fila 1, A=codi, B=descripció, C endavant=talles. Retorna
    (poms, talles): poms=[{'codi_fitxa','descripcio','values':{talla:float}}].
    Distint de _parse_excel_poms (fitxa de model, models_app/extraction_views.py), que des del
    FIX C de QA-S8 ancora la capçalera pel CONTINGUT i mapa les columnes per ETIQUETA, i que
    abdica —cau a la IA— si no pot demostrar que ha entès la taula. Aquest d'aquí és el format
    simple i tancat de la Library: si canvia, no arrossega l'altre."""
    import openpyxl, io
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []
    header = rows[0]
    size_cols = [(i, str(h).strip()) for i, h in enumerate(header)
                 if i >= 2 and h is not None and str(h).strip()]
    talles = [lbl for _, lbl in size_cols]
    poms = []
    for row in rows[1:]:
        if not row or row[0] is None or str(row[0]).strip() == '':
            continue
        codi = str(row[0]).strip()
        desc = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ''
        values = {}
        for ci, lbl in size_cols:
            if ci < len(row) and row[ci] is not None:
                try:
                    values[lbl] = float(str(row[ci]).replace(',', '.'))
                except (ValueError, TypeError):
                    pass
        if values:
            poms.append({'codi_fitxa': codi, 'descripcio': desc, 'values': values})
    return poms, talles


def _pdf_extracted_to_poms(extracted, base_size):
    """Normalitza l'esquema REAL del servei G3 (`extract_from_file`: claus `poms` + `grading_table`,
    NO `measurements`) a la llista comuna [{codi_fitxa, descripcio, values}].
    - `codi_fitxa` = `poms[*].code`; `descripcio` = `poms[*].description`.
    - `values` = graduació per talla: `grading_table[*].values_by_size` casat per `code`; si el POM
      no té fila de graduació (o `has_base_only`), es munta {base_size: base_value_cm}.
    base_size: talla base triada al wizard (FormData); si buida, s'usa la detectada al document.
    """
    grading_by_code = {(g.get('code') or '').strip(): (g.get('values_by_size') or {})
                       for g in (extracted.get('grading_table') or [])}
    # Toleràncies extretes per code (grading_table primer, fallback al POM). NOMÉS display
    # (paritat R7): NO es persisteixen — el sprint POM-review les farà aterrar al POM/model.
    tol_by_code = {}
    for g in (extracted.get('grading_table') or []):
        c = (g.get('code') or '').strip()
        if c and (g.get('tolerance_minus') is not None or g.get('tolerance_plus') is not None):
            tol_by_code[c] = (g.get('tolerance_minus'), g.get('tolerance_plus'))
    xb = (extracted.get('base_size') or {}).get('value')
    eff_base = base_size or (str(xb).strip() if xb is not None else '')
    out = []
    for p in (extracted.get('poms') or []):
        code = (p.get('code') or '').strip()
        values = dict(grading_by_code.get(code) or {})
        if not values:
            bv = p.get('base_value_cm')
            if eff_base and bv is not None:
                values = {eff_base: bv}
        tmin, tplus = tol_by_code.get(code, (p.get('tolerance_minus'), p.get('tolerance_plus')))
        out.append({
            'codi_fitxa': code,
            'descripcio': (p.get('description') or '').strip(),
            'values': values,
            'tolerance_minus': tmin,
            'tolerance_plus': tplus,
        })
    return out


@api_view(['POST'])
@permission_classes([_Configure])
def size_map_grading_preview_file_view(request):
    """POST size-map/grading-preview-file/ — preview de grading des d'un FITXER.

    Multipart: {file, size_system_id (opt), base_size}. Excel → _parse_grading_excel (parser
    propi de la Library: A=codi, B=descripció, C+=talles); PDF/imatge → extract_from_file (Opus,
    funció PURA del motor del model). Normalitza a [{codi_fitxa, descripcio, values}], resol
    find_pom_master AMB descripció (match per nom) i deriva el grading amb la MATEIXA lògica que
    el preview de paste (detect_grading + derive_break_fields). Cap persistència.
    Robust per fila: un POM que falla a la derivació s'omet amb avís, no aborta tot.
    """
    try:
        from fhort.pom.models import SizeDefinition, SizeSystem
        from fhort.models_app.extraction_views import find_pom_master
        from fhort.models_app.extraction_service import extract_from_file
        from fhort.pom.size_labels import canonical_size_label

        f = request.FILES.get('file')
        if f is None:
            return Response({'error': 'Cal adjuntar un fitxer (camp "file").'}, status=400)
        ssid = request.data.get('size_system_id')
        base_size = (request.data.get('base_size') or '').strip()
        customer = _resolve_run_customer(request.data, ssid)  # N3: matcher per àlies del client

        name = (f.name or '').lower()
        file_bytes = f.read()
        avisos = []

        # Run del tenant (etiquetes canòniques del SizeSystem) — es coneix ABANS d'extreure. És la
        # MATEIXA font que el run ordenat de sota; es puja aquí per passar-lo a l'extractor (Capa 1).
        tenant_run = []
        if ssid:
            tenant_run = list(SizeDefinition.objects.filter(size_system_id=ssid)
                              .order_by('ordre').values_list('etiqueta', flat=True))

        # 1-2. Extracció → llista comuna [{codi_fitxa, descripcio, values}].
        poms_in = []
        if name.endswith(('.xlsx', '.xls')):
            raw_poms, _talles = _parse_grading_excel(file_bytes)
            for p in raw_poms:
                poms_in.append({
                    'codi_fitxa': (p.get('codi_fitxa') or '').strip(),
                    'descripcio': (p.get('descripcio') or '').strip(),
                    'values': p.get('values') or {},
                })
        elif name.endswith(('.pdf', '.png', '.jpg', '.jpeg', '.webp')):
            # Capa 1 (DIAGNOSI_ETIQUETES_TALLA): diem a l'extractor el run del tenant perquè mapi la
            # graduació a AQUESTES talles (2XL, no XXL) i marqui size_discrepancy. El wizard ja el sap.
            wiz_ctx = {
                'size_run': ', '.join(tenant_run),
                'base_size': base_size,
                'size_system_codi': (SizeSystem.objects.filter(pk=ssid).values_list('codi', flat=True).first() or '') if ssid else '',
            }
            extracted = extract_from_file(file_bytes, f.name, wiz_ctx)
            # Instrumentació K.1 (R4): registra els valors CRUS per talla tal com surten de
            # l'extracció, ABANS de detect_grading (que fa l'alineació run↔talles). Permet
            # re-executar un cas (p.ex. BERG) i discriminar si una regla FIXED espúria ve de
            # l'extracció (valors ja constants a l'origen) o de l'alineació. Sense persistència.
            for _row in (extracted.get('grading_table') or []):
                logger.info(
                    "size_map extract [K.1]: file=%s code=%r values_by_size=%r tol=(%r,%r)",
                    f.name, (_row.get('code') or '').strip(),
                    _row.get('values_by_size') or {},
                    _row.get('tolerance_minus'), _row.get('tolerance_plus'))
            # Capa 1: recull la discrepància de talles que el model marqui (document vs run configurat).
            discrep = extracted.get('size_discrepancy')
            if discrep:
                avisos.append(f"Discrepància de talles document↔run: {discrep}")
            poms_in = _pdf_extracted_to_poms(extracted, base_size)
            if not poms_in:
                avisos.append("La IA no ha retornat cap mesura llegible del document.")
        else:
            return Response({'error': (
                f"Format no suportat: {name}. "
                "Accepta .xlsx/.xls/.pdf/.png/.jpg/.jpeg/.webp.")}, status=400)

        if not poms_in:
            return Response({'results': [], 'run': [], 'base_size': base_size,
                             'avisos': avisos or ["No s'han trobat POMs al fitxer."]}, status=200)

        # 3. run ordenat — MATEIXA font que el preview de paste i el create (tenant_run, ja calculat).
        run = list(tenant_run)
        if not run:
            for p in poms_in:
                for k in (p['values'] or {}).keys():
                    if k not in run:
                        run.append(k)

        # Capa 2 (DIAGNOSI_ETIQUETES_TALLA): mapa forma-canònica → etiqueta del tenant, per re-clavar
        # les claus de values_by_size a les talles del run ABANS de detect_grading. Reusa
        # canonical_size_label (mateix helper que el camí d'import, extraction_views.py:1250); NO és
        # un normalitzador nou. Salva XXL↔2XL, que _norm (upper+strip) no cobreix.
        canon_to_tenant = {canonical_size_label(e): e for e in run}

        # 4-5. matching (amb descripció) + derivació de grading, robust per fila.
        results = []
        for p in poms_in:
            codi = p['codi_fitxa']
            descripcio = p['descripcio']
            values = p['values'] or {}
            # Capa 2 — re-clau a etiquetes del tenant. R4: valors DESPRÉS del re-clau (el log
            # d'extracció d'abans, a l'entrada, dona els valors CRUS → es pot comparar el pont).
            values = {canon_to_tenant.get(canonical_size_label(k), k): v for k, v in values.items()}
            logger.info("size_map reclau [K.1]: file=%s code=%r values_by_size=%r",
                        f.name, codi, values)
            try:
                pom, mtype, conf = find_pom_master(codi, descripcio, customer=customer)
            except Exception:
                pom, mtype, conf = None, 'no_match', 'NO_MATCH'
            pom, weak_suggestion = _apply_match_threshold(pom, conf)
            warning = '' if (pom or weak_suggestion) else f"POM '{codi}' no resolt al catàleg."
            # BLOQUEIG (integritat): si falta valor per a alguna talla del run (després del re-clau),
            # la fila és INCOMPLETA → NO es deriva la regla amb deltes parcials (un break a la talla
            # perduda es perdria en silenci). Es marca i el create la bloquejarà.
            missing = [s for s in run if values.get(s) is None] if run else []
            if missing:
                results.append({
                    'pom_codi_client': codi, 'pom_descripcio': descripcio,
                    'pom_id': pom.id if pom else None,
                    'pom_nom': pom.nom_client if pom else None,
                    'match_type': mtype, 'confidence': conf,
                    'logica_detectada': None, 'increment': None, 'valors_step': None,
                    'increment_base': None, 'increment_break': None,
                    'talla_break_label': None, 'talla_break_pos': None,
                    'valors_calculats': {k: values.get(k) for k in values},
                    'tolerance_minus': p.get('tolerance_minus'),
                    'tolerance_plus': p.get('tolerance_plus'),
                    'weak_suggestion': weak_suggestion,
                    'incompleta': True, 'missing_sizes': missing,
                    'warning': warning,
                })
                continue
            try:
                det = detect_grading(values, run, base_size)
            except Exception as e:
                avisos.append(f"POM '{codi}': grading no derivat ({e}); omès.")
                continue
            if det['warning']:
                warning = (warning + ' ' if warning else '') + det['warning']
            ib, ibrk, tlabel, tpos = derive_break_fields(
                det['logica'], det['increment'], det['valors_step'], run)
            results.append({
                'pom_codi_client': codi,
                'pom_descripcio': descripcio,
                'pom_id': pom.id if pom else None,
                'pom_nom': pom.nom_client if pom else None,
                'match_type': mtype,
                'confidence': conf,
                'logica_detectada': det['logica'],
                'increment': det['increment'],
                'valors_step': det['valors_step'],
                'increment_base': ib,
                'increment_break': ibrk,
                'talla_break_label': tlabel,
                'talla_break_pos': tpos,
                'valors_calculats': {k: values.get(k) for k in values},
                # Paritat R7 (NOMÉS display): toleràncies extretes al costat de la regla derivada.
                'tolerance_minus': p.get('tolerance_minus'),
                'tolerance_plus': p.get('tolerance_plus'),
                'weak_suggestion': weak_suggestion,
                'incompleta': False, 'missing_sizes': [],
                'warning': warning,
            })

        _apply_many_to_one_guard(results)  # N3-P2: dues files → mateix POM per descripció → pendents
        return Response({'results': results, 'run': run, 'base_size': base_size,
                         'avisos': avisos})
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("size_map_grading_preview_file_view error")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# 3D — CREATE (persisteix SizeSystem + GradingRuleSet + GradingRule + SizingProfile)
# ─────────────────────────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([_Configure])
def size_map_create_view(request):
    """POST size-map/create/ — materialitza el run de client dins transaction.atomic.

    accio: REUTILITZAR (no crea SizeSystem) | CLONAR (deriva amb parent) | CREAR.
    Sempre crea/actualitza GradingRuleSet + GradingRule + SizingProfile.
    """
    try:
        from fhort.pom.models import (
            SizeSystem, SizeDefinition, GradingRuleSet, GradingRule,
            SizingProfile, POMMaster, Target, ConstructionType, FitType,
            GarmentType,
        )
        from fhort.pom.grading_utils import derive_break_fields

        data = request.data or {}
        accio = data.get('accio') or 'CREAR'
        customer_codi = (data.get('customer_codi') or '').strip()
        nom_custom = (data.get('nom_custom') or '').strip()
        target_codi = data.get('target_codi')
        base_unit = data.get('base_unit') or ''
        talles = data.get('talles') or []
        grading = data.get('grading') or []
        perfils = data.get('perfils') or []
        base_size = (data.get('base_size') or '').strip()
        src_ssid = data.get('size_system_id')
        # R2 — codis de document que el frontend NO va poder vincular a cap POM. NO es perden en
        # silenci: es desen al ruleset com a "pendents de vincular" i s'eco-retornen al resultat.
        discarded_codes = [str(c).strip() for c in (data.get('discarded_codes') or []) if str(c).strip()]
        # 1C-4b-be — resolució de conflictes de graduació (N graduacions per combinació,
        # distingides pel nom). on_conflict: None | 'new' | 'update'.
        on_conflict = data.get('on_conflict')
        nom_variant = (data.get('nom_variant') or '').strip() or None

        warnings = []

        # ── Guard d'INTEGRITAT (talla absent = BLOQUEIG): cap regla es deriva d'una taula
        # incompleta. Les files marcades incompletes al preview (falta valor per a alguna talla del
        # run) arriben amb logica_detectada=None però logica='LINEAR' per defecte → derivarien una
        # regla falsa. Es BLOQUEGEN aquí, abans d'escriure res → 400 amb la llista de files.
        incompletes = [
            {'codi': (g.get('codi') or '').strip(), 'missing_sizes': g.get('missing_sizes') or []}
            for g in grading if g.get('incompleta')
        ]
        if incompletes:
            return Response({
                'error': ('Hi ha files amb talles absents (taula incompleta); completa-les o '
                          'treu-les abans de crear (cap regla desada).'),
                'incompletes': incompletes,
            }, status=status.HTTP_400_BAD_REQUEST)

        # ── Guard de col·lisió (R1): dos codis de document vinculats al MATEIX POM col·lapsarien
        # a una sola regla (update_or_create(rule_set, pom), l'última guanya) → pèrdua SILENCIOSA.
        # Decisió CTO: BLOQUEJAR abans d'escriure res → 400 amb la llista {codi_document → pom}.
        by_pom = {}
        for g in grading:
            pid = g.get('pom_id')
            if pid is None:
                continue
            by_pom.setdefault(pid, []).append((g.get('codi') or '').strip())
        collisions = []
        for pid, codes in by_pom.items():
            if len(codes) > 1:
                pom = POMMaster.objects.filter(pk=pid).first()
                collisions.append({
                    'pom_id': pid,
                    'pom_codi': (getattr(pom, 'codi_client', '') or '') if pom else '',
                    'pom_nom': (getattr(pom, 'nom_client', '') or '') if pom else '',
                    'codis_document': [c for c in codes if c],
                })
        if collisions:
            return Response({
                'error': ('Dos o més codis de document es vinculen al mateix POM; '
                          'resol els duplicats abans de crear (cap regla desada).'),
                'collisions': collisions,
            }, status=status.HTTP_400_BAD_REQUEST)

        target = Target.objects.filter(codi=target_codi).first() if target_codi else None

        # ── Pre-check d'avís-i-confirma (NOMÉS REUTILITZAR: el sistema ja existeix i la
        # combinació és coneguda d'entrada). CREAR/CLONAR creen sistema nou → combinació
        # nova → mai conflicte. Es fa ABANS d'escriure res; MAI sobreescriure en silenci.
        if accio == 'REUTILITZAR' and on_conflict is None:
            ss_check = SizeSystem.objects.filter(pk=src_ssid).first()
            if ss_check is not None:
                existing = []
                for p in perfils:
                    p_target = Target.objects.filter(codi=p.get('target_codi')).first()
                    construction = ConstructionType.objects.filter(pk=p.get('construction_id')).first()
                    fit_type = FitType.objects.filter(pk=p.get('fit_type_id')).first()
                    if not (p_target and construction and fit_type):
                        continue
                    qs = SizingProfile.objects.filter(
                        size_system=ss_check, target=p_target,
                        construction=construction, fit_type=fit_type,
                    ).select_related('grading_rule_set', 'target', 'construction', 'fit_type')
                    for prof in qs:
                        existing.append({
                            'nom': prof.grading_rule_set.nom if prof.grading_rule_set_id else '',
                            'id': prof.id,
                            'combinacio': f"{p_target.codi}/{construction.codi}/{fit_type.codi}",
                        })
                if existing:
                    return Response({
                        'conflict': True,
                        'existing': existing,
                        'message': ('Ja existeix/en graduació/ns per a aquesta/es combinació/ns. '
                                    'Tria actualitzar-ne una o crear-ne una de nova amb un nom.'),
                    }, status=status.HTTP_409_CONFLICT)

        with transaction.atomic():
            # ---- 1. Resoldre / crear el SizeSystem ----
            if accio == 'REUTILITZAR':
                ss = SizeSystem.objects.get(pk=src_ssid)
            elif accio == 'CLONAR':
                parent = SizeSystem.objects.get(pk=src_ssid)
                cust = _customer_label(customer_codi)
                codi, nn = _unique_size_system_code(f"{parent.codi}_{customer_codi}")
                nom = f"{parent.nom} — {cust} Run {nn:02d}"
                ss = SizeSystem.objects.create(
                    codi=codi, nom=nom, base_unit=base_unit or parent.base_unit,
                    actiu=True, parent=parent, customer_codi=customer_codi,
                )
                if target:
                    ss.targets.add(target)
                else:
                    ss.targets.set(parent.targets.all())
                # Copiar les talles del pare, després merge amb les de l'input.
                for d in SizeDefinition.objects.filter(size_system=parent).order_by('ordre'):
                    SizeDefinition.objects.create(
                        size_system=ss, etiqueta=d.etiqueta, ordre=d.ordre,
                        valor_numeric=d.valor_numeric, age_months_min=d.age_months_min,
                        age_months_max=d.age_months_max, body_height_cm=d.body_height_cm,
                    )
            else:  # CREAR
                cust = _customer_label(customer_codi)
                base_code = f"{target_codi or 'SYS'}_{customer_codi}" if customer_codi else (target_codi or 'SYS')
                codi, nn = _unique_size_system_code(base_code)
                nom = nom_custom or f"{(_target_nom(target) if target else target_codi) or 'Sistema'} {base_unit} — {cust} Run {nn:02d}".strip()
                ss = SizeSystem.objects.create(
                    codi=codi, nom=nom, base_unit=base_unit,
                    actiu=True, customer_codi=customer_codi,
                )
                if target:
                    ss.targets.add(target)

            # ---- 2. Talles de l'input (merge per (size_system, etiqueta)) ----
            if accio in ('CLONAR', 'CREAR'):
                for idx, t in enumerate(talles):
                    et = (t.get('etiqueta') or '').strip()
                    if not et:
                        continue
                    SizeDefinition.objects.update_or_create(
                        size_system=ss, etiqueta=et,
                        defaults={
                            'ordre': t.get('ordre', idx + 1),
                            'valor_numeric': t.get('valor_numeric'),
                            'age_months_min': t.get('age_months_min'),
                            'age_months_max': t.get('age_months_max'),
                            'body_height_cm': t.get('body_height_cm'),
                        },
                    )

            # ---- 3. Resoldre la talla base (talla_base és NOT NULL a GradingRule) ----
            base_def = None
            if base_size:
                base_def = SizeDefinition.objects.filter(
                    size_system=ss, etiqueta__iexact=base_size).first()
            if base_def is None:
                base_def = SizeDefinition.objects.filter(size_system=ss).order_by('ordre').first()

            # Customer del run: resolt AQUÍ (abans del ruleset) perquè la procedència del
            # GradingRuleSet el necessita. El fan servir també les GradingRules i els perfils.
            from fhort.pom.services import maybe_learn_customer_alias
            alias_customer = _resolve_run_customer(data, src_ssid)

            # ---- 4. GradingRuleSet (graduació; el nom és el discriminador de variant) ----
            # nom explícit del payload, o fallback derivat. filter().first() en lloc de
            # get_or_create: GradingRuleSet no té unique (size_system, nom) → evita
            # MultipleObjectsReturned davant dades brutes.
            rs_nom = nom_variant or f"{ss.nom} — Grading"
            if on_conflict == 'update':
                rule_set = GradingRuleSet.objects.filter(size_system=ss, nom=rs_nom).first()
                if rule_set is None:
                    return Response(
                        {'error': f"Graduació a actualitzar no trobada (nom='{rs_nom}')."},
                        status=status.HTTP_400_BAD_REQUEST)
                rule_set.actiu = True
                if target:
                    rule_set.target = target
                rule_set.save(update_fields=['actiu', 'target'])
            else:
                # on_conflict=='new' o cas sense conflicte: reusa la graduació d'aquest
                # nom si ja existeix, si no en crea una de nova.
                rule_set = GradingRuleSet.objects.filter(size_system=ss, nom=rs_nom).first()
                if rule_set is None:
                    # PROVINENÇA: el wizard de size-map és camí d'importació d'un run → CLIENT_RUN
                    # encara que el customer no sigui resoluble (run genèric); l'origen ja tanca
                    # la fuita i el warning en deixa traça.
                    if alias_customer is None:
                        logger.warning(
                            "GradingRuleSet CLIENT_RUN sense customer resoluble (nom=%r): "
                            "run genèric; procedència tancada per origen.", rs_nom)
                    rule_set = GradingRuleSet.objects.create(
                        nom=rs_nom, size_system=ss, actiu=True, target=target,
                        origen=GradingRuleSet.ORIGEN_CLIENT_RUN, customer=alias_customer,
                    )
            if target:
                rule_set.targets.add(target)

            # R2 — desa els codis no vinculats al ruleset (pendents de vincular).
            rule_set.pendents_vincular = discarded_codes
            rule_set.save(update_fields=['pendents_vincular'])

            # ---- 5. GradingRules ----
            if base_def is None and grading:
                warnings.append("No s'ha pogut resoldre cap talla base; regles de grading omeses.")
            else:
                # run ordenat del size system: MATEIXA font que el preview 3C (l.232-233) i que
                # el run_of() del backfill — SizeDefinition de `ss` ordenades per `ordre`. Ja
                # materialitzades al pas 2. Alimenta la forma canònica PEÇA A (increment_base...).
                run_ordenat = list(
                    SizeDefinition.objects.filter(size_system=ss)
                    .order_by('ordre').values_list('etiqueta', flat=True))
                for g in grading:
                    pom_id = g.get('pom_id')
                    pom = POMMaster.objects.filter(pk=pom_id).first()
                    if pom is None:
                        warnings.append(f"POM id={pom_id} no trobat; regla omesa.")
                        continue
                    logica_eff = g.get('logica') or 'LINEAR'
                    ib, ibrk, tlabel, tpos = derive_break_fields(
                        logica_eff, g.get('increment'), g.get('valors_step'), run_ordenat)
                    GradingRule.objects.update_or_create(
                        rule_set=rule_set, pom=pom,
                        defaults={
                            'talla_base': base_def,
                            'logica': logica_eff,
                            'increment': g.get('increment') or 0,
                            'valors_step': g.get('valors_step'),
                            'increment_base': ib,
                            'increment_break': ibrk,
                            'talla_break_label': tlabel,
                            'talla_break_pos': tpos,
                            'actiu': True,
                        },
                    )
                    # Biblioteca del client: si el codi de document → POM l'ha resolt un
                    # humà (el matcher no l'encerta sol), sembra un CustomerPOMAlias
                    # reutilitzable. NO toca cap model existent (sembra futures imports).
                    maybe_learn_customer_alias(
                        alias_customer, g.get('codi'), g.get('descripcio'), pom,
                        origen='IMPORT')

            # ---- 6. SizingProfiles ----
            sizing_profile_ids = []
            for p in perfils:
                p_target = Target.objects.filter(codi=p.get('target_codi')).first()
                construction = ConstructionType.objects.filter(pk=p.get('construction_id')).first()
                fit_type = FitType.objects.filter(pk=p.get('fit_type_id')).first()
                garment_type = GarmentType.objects.filter(pk=p.get('garment_type_id')).first()
                if not (p_target and construction and fit_type and garment_type):
                    warnings.append(
                        f"Perfil incomplet (target={p.get('target_codi')}, "
                        f"construction={p.get('construction_id')}, fit={p.get('fit_type_id')}, "
                        f"garment={p.get('garment_type_id')}); omès.")
                    continue
                # fit_type i grading_rule_set formen part de la IDENTITAT (filter, no
                # defaults) → s'acaba la reassignació silenciosa de fit i la col·lisió
                # intra-crida. La regla N-perfils permet coexistir variants pel rule_set.
                profile = SizingProfile.objects.filter(
                    size_system=ss, target=p_target, construction=construction,
                    fit_type=fit_type, grading_rule_set=rule_set,
                ).first()
                if profile is not None:
                    profile.garment_type = garment_type
                    profile.is_default = True
                    profile.customer = alias_customer  # eix client (NULL si run genèric)
                    profile.save(update_fields=['garment_type', 'is_default', 'customer'])
                else:
                    profile = SizingProfile.objects.create(
                        target=p_target, construction=construction, size_system=ss,
                        fit_type=fit_type, garment_type=garment_type,
                        grading_rule_set=rule_set, is_default=True,
                        customer=alias_customer,  # eix client (NULL si run genèric)
                    )
                sizing_profile_ids.append(profile.id)

        return Response({
            'size_system_id': ss.id,
            'codi': ss.codi,
            'nom': ss.nom,
            'grading_rule_set_id': rule_set.id,
            'sizing_profile_ids': sizing_profile_ids,
            # R5 — comptador de font única: regles REALS persistides al ruleset (no files de
            # document). Coincideix amb regles_count del serializer i amb la fitxa del run.
            'rules_count': rule_set.regles.count(),
            'discarded_codes': discarded_codes,
            'warnings': warnings,
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("size_map_create_view error")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# 3E — SYSTEMS (llista per al wizard)
# ─────────────────────────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([_Configure])
def size_map_systems_view(request):
    """GET size-map/systems/ — SizeSystems actius: primer els de client, després canònics."""
    try:
        from django.db.models import Count
        from fhort.pom.models import SizeSystem

        qs = SizeSystem.objects.filter(actiu=True).select_related(
            'target', 'parent').annotate(
            num_talles=Count('talles', distinct=True),
            num_rule_sets=Count('grading_rule_sets', distinct=True),
        )
        # Ordre: client (codi no buit) abans que canònics; dins cada grup per nom.
        systems = sorted(
            qs,
            key=lambda s: (s.customer_codi == '', s.customer_codi, s.nom),
        )
        results = [{
            'id': s.id,
            'codi': s.codi,
            'nom': s.nom,
            'base_unit': s.base_unit,
            'target_nom': _target_nom(s.target) if s.target else None,
            'customer_codi': s.customer_codi,
            'parent_codi': s.parent.codi if s.parent else None,
            'parent_nom': s.parent.nom if s.parent else None,
            'num_talles': s.num_talles,
            'num_rule_sets': s.num_rule_sets,
        } for s in systems]
        return Response({'count': len(results), 'results': results})
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("size_map_systems_view error")
        return Response({'error': str(e)}, status=500)
