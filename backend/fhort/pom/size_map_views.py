"""fhort/pom/size_map_views.py — Size Map Setup wizard (backend).

Wizard per, a partir d'una taula de mides de client, identificar si un SizeSystem
existent encaixa (REUTILITZAR), si cal derivar-ne un (CLONAR) o crear-ne un de nou
(CREAR), generar-ne el GradingRuleSet/GradingRule (detectant LINEAR/STEP/FIXED a
partir dels valors) i els SizingProfiles.

Tots els endpoints requereixen la capacitat CONFIGURE.
"""
import re

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from fhort.accounts.capabilities import HasCapability, CONFIGURE


class _Configure(HasCapability):
    required_capability = CONFIGURE


def _norm(label) -> str:
    """Normalitza una etiqueta per comparar (upper + strip), com fa el run."""
    return str(label or '').strip().upper()


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
        base_norm = _norm(base_size)
        taula = data.get('taula') or []

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
        run_norm = [_norm(x) for x in run]
        base_idx = run_norm.index(base_norm) if base_norm in run_norm else None

        results = []
        for row in taula:
            codi = row.get('pom_codi_client')
            valors_raw = row.get('valors') or {}
            valors = {_norm(k): v for k, v in valors_raw.items()}

            pom, _mtype, _conf = find_pom_master(codi, '')
            warning = ''
            if pom is None:
                warning = f"POM '{codi}' no resolt al catàleg."

            logica = None
            increment = None
            valors_step = None

            if base_idx is None:
                warning = (warning + ' ' if warning else '') + \
                    f"Talla base '{base_size}' no és al run de talles."
            else:
                deltas = {}
                for j, lab in enumerate(run_norm):
                    if j == base_idx:
                        continue
                    if j > base_idx:
                        inner = run_norm[j - 1]
                        v_out, v_in = valors.get(lab), valors.get(inner)
                        sign = 1.0
                    else:
                        inner = run_norm[j + 1]
                        v_out, v_in = valors.get(lab), valors.get(inner)
                        sign = -1.0
                    if v_out is None or v_in is None:
                        warning = (warning + ' ' if warning else '') + \
                            f"Falta valor per calcular el delta de la talla {run[j]}."
                        continue
                    # format C: delta positiu en sentit de creixement cap enfora.
                    deltas[run[j]] = round(sign * (float(v_out) - float(v_in)), 2)

                if deltas:
                    vals = list(deltas.values())
                    if all(d == 0 for d in vals):
                        logica, increment = 'FIXED', 0.0
                    elif all(d == vals[0] for d in vals):
                        logica, increment = 'LINEAR', vals[0]
                    else:
                        logica, valors_step = 'STEP', deltas

            results.append({
                'pom_codi_client': codi,
                'pom_id': pom.id if pom else None,
                'pom_nom': pom.nom_client if pom else None,
                'logica_detectada': logica,
                'increment': increment,
                'valors_step': valors_step,
                'valors_calculats': {k: valors_raw.get(k) for k in valors_raw},
                'warning': warning,
            })

        return Response({'results': results, 'run': run, 'base_size': base_size})
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("size_map_grading_preview_view error")
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

        warnings = []

        target = Target.objects.filter(codi=target_codi).first() if target_codi else None

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
                    target=target or parent.target, actiu=True,
                    parent=parent, customer_codi=customer_codi,
                )
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
                    target=target, actiu=True, customer_codi=customer_codi,
                )

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

            # ---- 4. GradingRuleSet ----
            rs_nom = f"{ss.nom} — Grading"
            rule_set, _ = GradingRuleSet.objects.update_or_create(
                nom=rs_nom, size_system=ss,
                defaults={'actiu': True, 'target': target},
            )
            if target:
                rule_set.targets.add(target)

            # ---- 5. GradingRules ----
            if base_def is None and grading:
                warnings.append("No s'ha pogut resoldre cap talla base; regles de grading omeses.")
            else:
                for g in grading:
                    pom_id = g.get('pom_id')
                    pom = POMMaster.objects.filter(pk=pom_id).first()
                    if pom is None:
                        warnings.append(f"POM id={pom_id} no trobat; regla omesa.")
                        continue
                    GradingRule.objects.update_or_create(
                        rule_set=rule_set, pom=pom,
                        defaults={
                            'talla_base': base_def,
                            'logica': g.get('logica') or 'LINEAR',
                            'increment': g.get('increment') or 0,
                            'valors_step': g.get('valors_step'),
                            'actiu': True,
                        },
                    )

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
                profile, _ = SizingProfile.objects.update_or_create(
                    target=p_target, construction=construction, size_system=ss,
                    defaults={
                        'fit_type': fit_type,
                        'garment_type': garment_type,
                        'grading_rule_set': rule_set,
                        'is_default': True,
                    },
                )
                sizing_profile_ids.append(profile.id)

        return Response({
            'size_system_id': ss.id,
            'codi': ss.codi,
            'nom': ss.nom,
            'grading_rule_set_id': rule_set.id,
            'sizing_profile_ids': sizing_profile_ids,
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
