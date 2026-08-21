"""
fhort/pom/s8_views.py — Sprint S8: CSV/PDF export
"""
import csv
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

CM_TO_INCH = 0.393701


def get_unit(request):
    try:
        from fhort.accounts.models import TenantConfig
        return TenantConfig.get_or_create_default().unitat_mesura
    except Exception:
        return 'CM'


def cv(val, unit):
    if val is None:
        return '—'
    v = float(val)
    if unit == 'INCH':
        return f'{v * CM_TO_INCH:.3f}"'
    return f'{v:.1f}'


def _pom_codi(p):
    if not p:
        return ''
    if getattr(p, 'pom_global_id', None):
        return p.pom_global.codi
    return p.codi_client or ''


def _pom_name_en(p):
    if not p:
        return ''
    if getattr(p, 'pom_global_id', None) and p.pom_global.nom_en:
        return p.pom_global.nom_en
    return p.nom_client or ''


def _delta_de(r, unit):
    """FIX-A/PAS-4 — LA COLUMNA «Increment/talla» DEIA EL CAMP LLEGAT.

    Els dos CSV d'aquest fitxer imprimien `r.increment`, que des del FIX-A/PAS-3 ja no el
    llegeix ningú (i abans tampoc manava: el motor gradua per `increment_base`). Un joc amb
    break s'exportava, a més, amb UNA sola columna, o sigui que el full que sortia d'aquí no
    es podia tornar a entrar: hi faltava la meitat de la llei.

    Ara surt el delta que MANA i, quan hi ha trencament, també el seu — cada cosa a la seva
    columna, que és com el document del client ja les escriu.
    """
    if r.logica == 'STEP':
        return '(STEP)'                     # els valors viuen a `valors_step`, no en un escalar
    if r.increment_base is None:
        # Regla incompleta: des del PAS 3 no gradua i no emet cap cel·la (llei D2). El CSV ho
        # ha de dir igual que ho diu la propagació, no imprimir-hi un 0 que sembli un delta.
        return '—'
    return cv(r.increment_base, unit)


def _delta_break_de(r, unit):
    if r.logica == 'STEP' or r.increment_break is None:
        return ''
    return cv(r.increment_break, unit)


def _category_name(p):
    if not p or not getattr(p, 'categoria_id', None):
        return ''
    return p.categoria.nom_ca or p.categoria.nom_en or ''


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_grading_csv_view(request, rule_set_id):
    """GET /api/v1/grading-rule-sets/{id}/export/csv/"""
    unit = get_unit(request)
    try:
        from fhort.pom.models import GradingRule, GradingRuleSet

        rs = GradingRuleSet.objects.get(pk=rule_set_id)
        rules = GradingRule.objects.filter(
            rule_set=rs, actiu=True
        ).select_related('pom', 'pom__categoria', 'pom__pom_global').order_by(
            'pom__categoria__display_order', 'pom__codi_client'
        )

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            f'attachment; filename="grading_{rs.codi_sistema or rs.id}.csv"'
        )
        response.write('﻿')

        writer = csv.writer(response)
        writer.writerow(['POM Code', 'POM Name EN', 'Categoria', 'Logica',
                         f'Increment ({unit.lower()})/talla',
                         f'Increment break ({unit.lower()})/talla', 'Talla break'])
        for r in rules:
            writer.writerow([
                _pom_codi(r.pom),
                _pom_name_en(r.pom),
                _category_name(r.pom),
                r.logica,
                _delta_de(r, unit),
                _delta_break_de(r, unit),
                # 🔒 EN CONVENCIÓ DE MOTOR, i és deliberat. La volta a convenció de DOCUMENT
                # (`utils/breakConvention`) viu al front i necessita el run per fer-la; un CSV
                # que se l'inventés mouria l'etiqueta una talla sencera. Qui exporti i torni a
                # importar troba la MATEIXA etiqueta que hi ha a la BD.
                r.talla_break_label or '',
            ])
        return response
    except GradingRuleSet.DoesNotExist:
        return Response({'error': 'RuleSet no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('export_grading_csv error')
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_size_set_csv_view(request, profile_id):
    """GET /api/v1/sizing-profiles/{id}/export/csv/"""
    unit = get_unit(request)
    try:
        from fhort.pom.models import SizingProfile, GradingRule, SizeDefinition

        profile = SizingProfile.objects.select_related(
            'target', 'construction', 'fit_type',
            'size_system', 'grading_rule_set'
        ).get(pk=profile_id)

        sizes = SizeDefinition.objects.filter(
            size_system=profile.size_system
        ).order_by('ordre') if profile.size_system_id else []

        rules = GradingRule.objects.filter(
            rule_set=profile.grading_rule_set, actiu=True
        ).select_related('pom', 'pom__categoria', 'pom__pom_global').order_by(
            'pom__categoria__display_order', 'pom__codi_client'
        ) if profile.grading_rule_set_id else []

        filename = f"sizeset_{profile.size_system.codi if profile.size_system_id else profile_id}.csv"
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('﻿')

        writer = csv.writer(response)
        writer.writerow(['FHORT Textile Tech — Size Set Export'])
        writer.writerow(['Sistema', profile.size_system.nom if profile.size_system_id else ''])
        writer.writerow(['Target', profile.target.nom_en if profile.target_id else ''])
        writer.writerow(['Construccio', profile.construction.nom_en if profile.construction_id else ''])
        writer.writerow(['Fit', profile.fit_type.nom_en if profile.fit_type_id else ''])
        writer.writerow(['Grading', profile.grading_rule_set.nom if profile.grading_rule_set_id else ''])
        writer.writerow(['Unitats', unit])
        writer.writerow([])

        sizes_list = list(sizes)
        size_labels = [s.etiqueta for s in sizes_list]
        writer.writerow(['Talles'] + size_labels)
        if any(s.body_bust_cm for s in sizes_list):
            writer.writerow(['Bust corporal (cm)'] + [s.body_bust_cm or '' for s in sizes_list])
        if any(s.body_height_cm for s in sizes_list):
            writer.writerow(['Alcada corporal (cm)'] + [s.body_height_cm or '' for s in sizes_list])
        writer.writerow([])

        writer.writerow(['POM', 'Nom', 'Categoria', 'Logica',
                         f'Increment ({unit.lower()})/talla',
                         f'Increment break ({unit.lower()})/talla', 'Talla break'])
        for r in rules:
            writer.writerow([
                _pom_codi(r.pom),
                _pom_name_en(r.pom),
                _category_name(r.pom),
                r.logica,
                _delta_de(r, unit),
                _delta_break_de(r, unit),
                r.talla_break_label or '',     # convenció de MOTOR (v. l'export germà)
            ])
        return response
    except SizingProfile.DoesNotExist:
        return Response({'error': 'Perfil no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('export_size_set_csv error')
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_fitting_csv_view(request, pf_id):
    """GET /api/v1/fittings/peca/{pf_id}/export/csv/

    Exports a PieceFitting: per line spec=valor_teoric, mesurat=valor_real, Δ=val-spec.
    Asymmetric tolerance from BaseMeasurement(model, pom) with 0.6 fallback;
    PASS iff -tol_minus <= Δ <= tol_plus.
    """
    unit = get_unit(request)
    TOL_FALLBACK = 0.6
    try:
        from fhort.fitting.models import PieceFitting, PieceFittingLine
        from fhort.models_app.models import BaseMeasurement

        pf = PieceFitting.objects.select_related('model').get(pk=pf_id)
        model = pf.model
        lines = PieceFittingLine.objects.filter(
            piece_fitting=pf
        ).select_related('pom', 'pom__pom_global').order_by('pom__codi_client', 'size_label')

        # C2/Onada 1 — clau (pom, capa), com el consumidor: cada `PieceFittingLine` es jutja
        # amb la tolerància de la SEVA capa. Per POM sol, l'última capa llegida manaria sobre
        # tota la família i el CSV donaria PASS/FAIL amb la vara equivocada.
        # FASE_2/C1-ins — la clau creix amb la INSTÀNCIA pel mateix motiu: la sisa dreta i
        # l'esquerra són dues mesures amb tolerància pròpia, i la línia consumidora sap dir
        # de quina parla. FORMA A: la clau completa, perquè aquí hi ha de qui copiar-la.
        tol_map = {}
        for bm in BaseMeasurement.objects.filter(model=model, is_active=True):
            tm = float(bm.tolerancia_minus) if bm.tolerancia_minus is not None else TOL_FALLBACK
            tp = float(bm.tolerancia_plus) if bm.tolerancia_plus is not None else TOL_FALLBACK
            # SET-2/T6a — la PEÇA, com al germà `s10_views`: si no, el CSV imprimeix la
            # tolerància i per tant el `Resultat` d'una altra prenda.
            tol_map[(bm.pom_id, bm.capa, bm.instancia, bm.garment)] = (tm, tp)

        nom_model = str(model) if model else f'piece_{pf_id}'
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="fitting_peca_{pf_id}.csv"'
        response.write('﻿')

        writer = csv.writer(response)
        writer.writerow(['FHORT Textile Tech — Fitting Report'])
        writer.writerow(['Model', nom_model])
        writer.writerow(['PieceFitting', pf_id])
        writer.writerow(['Unitats', unit])
        writer.writerow([])
        writer.writerow(['POM', 'Nom', 'Talla', f'Spec ({unit.lower()})',
                         f'Mesurat ({unit.lower()})', f'Δ ({unit.lower()})',
                         f'Tolerancia ({unit.lower()})', 'Resultat'])

        for line in lines:
            spec = float(line.valor_teoric) if line.valor_teoric is not None else None
            val = float(line.valor_real) if line.valor_real is not None else None
            desv = round(val - spec, 2) if (val is not None and spec is not None) else None
            tol_minus, tol_plus = tol_map.get(
                (line.pom_id, line.capa, line.instancia, line.garment),
                (TOL_FALLBACK, TOL_FALLBACK))
            passa = ((-tol_minus) <= desv <= tol_plus) if desv is not None else None

            writer.writerow([
                _pom_codi(line.pom),
                _pom_name_en(line.pom),
                line.size_label,
                cv(spec, unit) if spec is not None else '—',
                cv(val, unit) if val is not None else '—',
                (f'+{cv(desv, unit)}' if desv and desv > 0 else cv(desv, unit)) if desv is not None else '—',
                f'-{cv(tol_minus, unit)}/+{cv(tol_plus, unit)}',
                'PASS' if passa else 'FAIL' if passa is False else '—',
            ])
        return response
    except PieceFitting.DoesNotExist:
        return Response({'error': 'PieceFitting no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('export_fitting_csv error')
        return Response({'error': str(e)}, status=500)


