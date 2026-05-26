"""
fhort/pom/s6_views.py — Sprint S6: HTM tooltips + unitats als fittings
"""
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
        return None
    v = float(val)
    if unit == 'INCH':
        return round(v * CM_TO_INCH, 3)
    return round(v, 2)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pom_htm_view(request, pom_id):
    """
    GET /api/v1/poms/{id}/htm/
    Retorna les instruccions de mesura disponibles per un POMMaster.
    El model actual no te camps htm dedicats; usem descripcio_en del global i
    notes del master. Tolerancies fixes (0.6/1.3) si no hi ha info especifica.
    """
    unit = get_unit(request)
    try:
        from fhort.pom.models import POMMaster

        pom = POMMaster.objects.select_related('pom_global', 'categoria').get(pk=pom_id)

        htm_en = ''
        htm_cat = ''
        if pom.pom_global_id:
            htm_en = pom.pom_global.descripcio_en or ''
            htm_cat = pom.pom_global.nom_ca or ''
        if pom.notes:
            htm_en = (htm_en + ('\n\n' if htm_en else '') + pom.notes).strip()

        return Response({
            'pom_id': pom.id,
            'codi_client': pom.codi_client,
            'nom_client': pom.nom_client,
            'htm_en': htm_en,
            'htm_cat': htm_cat,
            'htm_es': pom.pom_global.nom_es if pom.pom_global_id else '',
            'punt_inici': '',
            'punt_final': '',
            'referencia': '',
            'posicio': '',
            'tolerancia_prod': cv(0.6, unit),
            'tolerancia_samp': cv(1.3, unit),
            'unitat': unit,
            'is_key': pom.is_key_measure,
            'diagram_svg': '',
            'categoria': pom.pom_global.categoria if pom.pom_global_id else '',
        })
    except POMMaster.DoesNotExist:
        return Response({'error': 'POM no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('pom_htm_view error')
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def base_measurements_with_units_view(request, model_id):
    """
    GET /api/v1/models/{id}/base-measurements-units/
    Retorna les BaseMeasurements amb valors convertits a la unitat del tenant.
    """
    unit = get_unit(request)
    try:
        from fhort.models_app.models import BaseMeasurement

        bms = BaseMeasurement.objects.filter(
            model_id=model_id, is_active=True
        ).select_related('pom', 'pom__pom_global', 'pom__categoria').order_by(
            'pom__categoria__display_order', 'pom__codi_client'
        )

        data = []
        for bm in bms:
            pom = bm.pom
            categoria_nom = ''
            if pom and pom.categoria_id:
                categoria_nom = pom.categoria.nom_ca or pom.categoria.nom_en or ''
            data.append({
                'id': bm.id,
                'pom_id': bm.pom_id,
                'codi_client': pom.codi_client if pom else '',
                'nom_client': pom.nom_client if pom else '',
                'nom_en': pom.pom_global.nom_en if (pom and pom.pom_global_id) else '',
                'categoria_nom': categoria_nom,
                'base_value_cm': float(bm.base_value_cm) if bm.base_value_cm is not None else None,
                'base_value_display': cv(bm.base_value_cm, unit),
                'unitat': unit,
                'is_key': pom.is_key_measure if pom else False,
                'notes': bm.notes or '',
            })

        return Response({
            'count': len(data),
            'unitat': unit,
            'results': data,
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('base_measurements_with_units_view error')
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def graded_specs_with_units_view(request, sf_id):
    """
    GET /api/v1/size-fittings/{id}/graded-specs-units/
    Retorna les GradedSpec agrupades per POM amb conversio CM/INCH.
    """
    unit = get_unit(request)
    try:
        from fhort.fitting.models import SizeFitting
        from fhort.fitting.models import GradedSpec, GradingVersion

        sf = SizeFitting.objects.get(pk=sf_id)

        gv = GradingVersion.objects.filter(
            size_fitting=sf
        ).order_by('-data', '-id').first()

        if not gv:
            return Response({
                'sf_id': sf_id,
                'grading_version_id': None,
                'unitat': unit,
                'talles': [],
                'count': 0,
                'results': [],
            })

        specs = GradedSpec.objects.filter(
            grading_version=gv, is_active=True
        ).select_related(
            'pom', 'pom__pom_global', 'pom__categoria'
        ).order_by(
            'pom__categoria__display_order', 'pom__codi_client', 'size_label'
        )

        pom_dict = {}
        talles = []
        for spec in specs:
            pid = spec.pom_id
            pom = spec.pom
            if pid not in pom_dict:
                categoria_nom = ''
                if pom and pom.categoria_id:
                    categoria_nom = pom.categoria.nom_ca or pom.categoria.nom_en or ''
                pom_dict[pid] = {
                    'pom_id': pid,
                    'codi_client': pom.codi_client if pom else '',
                    'nom_client': pom.nom_client if pom else '',
                    'nom_en': pom.pom_global.nom_en if (pom and pom.pom_global_id) else '',
                    'categoria_nom': categoria_nom,
                    'is_key': pom.is_key_measure if pom else False,
                    'values': {},
                }
            pom_dict[pid]['values'][spec.size_label] = {
                'cm': float(spec.graded_value_cm) if spec.graded_value_cm is not None else None,
                'display': cv(spec.graded_value_cm, unit),
            }
            if spec.size_label not in talles:
                talles.append(spec.size_label)

        return Response({
            'sf_id': sf_id,
            'grading_version_id': gv.id,
            'unitat': unit,
            'talles': talles,
            'count': len(pom_dict),
            'results': list(pom_dict.values()),
        })
    except SizeFitting.DoesNotExist:
        return Response({'error': 'SizeFitting no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('graded_specs_with_units_view error')
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fitting_lines_with_units_view(request, fitting_id):
    """
    GET /api/v1/fittings/{id}/lines-units/
    SFFittingLinia: pom (POMMaster), nom_pom, talla, valor_vigent (spec), valor_nou (mesurat).
    Tolerancia fixa 0.6 cm.
    """
    unit = get_unit(request)
    try:
        from fhort.fitting.models import SFFitting, SFFittingLinia

        fitting = SFFitting.objects.get(pk=fitting_id)
        lines = SFFittingLinia.objects.filter(
            fitting=fitting
        ).select_related(
            'pom', 'pom__pom_global', 'pom__categoria'
        ).order_by(
            'pom__categoria__display_order', 'pom__codi_client', 'talla'
        )

        TOL_DEFAULT_CM = 0.6
        data = []
        for line in lines:
            pom = line.pom
            tol = TOL_DEFAULT_CM
            spec_cm = float(line.valor_vigent) if line.valor_vigent is not None else None
            val_cm = float(line.valor_nou) if line.valor_nou is not None else None

            desviacio = None
            passa = None
            if val_cm is not None and spec_cm is not None:
                desviacio = round(val_cm - spec_cm, 2)
                passa = abs(desviacio) <= tol

            data.append({
                'id': line.id,
                'pom_id': line.pom_id,
                'codi_client': pom.codi_client if pom else '',
                'nom_client': pom.nom_client if pom else (line.nom_pom or ''),
                'nom_en': pom.pom_global.nom_en if (pom and pom.pom_global_id) else '',
                'nom_pom': line.nom_pom or '',
                'talla': line.talla,
                'is_key': pom.is_key_measure if pom else False,
                'spec_cm': spec_cm,
                'spec_display': cv(spec_cm, unit),
                'value_cm': val_cm,
                'value_display': cv(val_cm, unit),
                'desviacio_cm': desviacio,
                'desviacio_display': cv(desviacio, unit) if desviacio is not None else None,
                'tolerancia_cm': tol,
                'tolerancia_display': cv(tol, unit),
                'passa': passa,
                'estat_cella': line.estat_cella,
                'unitat': unit,
                'notes': line.notes or '',
            })

        n_fail = sum(1 for d in data if d['passa'] is False)
        n_pass = sum(1 for d in data if d['passa'] is True)

        return Response({
            'fitting_id': fitting_id,
            'unitat': unit,
            'resum': {'pass': n_pass, 'fail': n_fail, 'pendent': len(data) - n_pass - n_fail},
            'count': len(data),
            'results': data,
        })
    except SFFitting.DoesNotExist:
        return Response({'error': 'Fitting no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('fitting_lines_with_units_view error')
        return Response({'error': str(e)}, status=500)
