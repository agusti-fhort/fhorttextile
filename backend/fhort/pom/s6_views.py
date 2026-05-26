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
    """Converteix cm a la unitat del tenant."""
    if val is None: return None
    v = float(val)
    if unit == 'INCH': return round(v * CM_TO_INCH, 3)
    return round(v, 2)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pom_htm_view(request, pom_id):
    """
    GET /api/v1/poms/{id}/htm/
    Retorna les instruccions de mesura (HTM) d'un POM.
    Primer busca al POMMaster del tenant (htm_override),
    si no existeix usa POMGlobal.
    """
    unit = get_unit(request)
    try:
        from fhort.pom.models import POMMaster

        pom = POMMaster.objects.select_related('pom_global').get(pk=pom_id)

        # HTM: tenant override > global > buit
        htm_en = (pom.htm_override or
                  (pom.pom_global.htm_metode_en if pom.pom_global_id else '') or '')
        htm_cat = pom.pom_global.htm_cat if pom.pom_global_id else ''
        htm_es  = pom.pom_global.htm_es  if pom.pom_global_id else ''

        start   = pom.pom_global.htm_punt_inici_en if pom.pom_global_id else ''
        end_pt  = pom.pom_global.htm_punt_fi_en    if pom.pom_global_id else ''
        ref     = pom.pom_global.htm_referencia    if pom.pom_global_id else ''
        posicio = pom.pom_global.htm_posicio        if pom.pom_global_id else ''

        tol_prod = cv(pom.pom_global.tolerancia_woven_cm if pom.pom_global_id else 0.6, unit)
        tol_samp = cv(pom.pom_global.tolerancia_knit_cm  if pom.pom_global_id else 1.3, unit)

        return Response({
            'pom_id': pom.id,
            'codi_client': pom.codi_client,
            'nom_client': pom.nom_client,
            'htm_en': htm_en,
            'htm_cat': htm_cat,
            'htm_es': htm_es,
            'punt_inici': start,
            'punt_final': end_pt,
            'referencia': ref,
            'posicio': posicio,
            'tolerancia_prod': tol_prod,
            'tolerancia_samp': tol_samp,
            'unitat': unit,
            'is_key': pom.pom_global.is_key_measure if pom.pom_global_id else False,
            'diagram_svg': pom.pom_global.diagram_svg if pom.pom_global_id else '',
        })
    except POMMaster.DoesNotExist:
        return Response({'error': 'POM no trobat'}, status=404)
    except Exception as e:
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
        ).select_related('pom', 'pom__pom_global', 'pom__pom_global__categoria')
        bms = bms.order_by(
            'pom__pom_global__categoria__display_order',
            'pom__codi_client'
        )

        data = [{
            'id': bm.id,
            'pom_id': bm.pom_id,
            'codi_client': bm.pom.codi_client,
            'nom_client': bm.pom.nom_client,
            'nom_en': bm.pom.pom_global.nom_en if bm.pom.pom_global_id else '',
            'categoria_nom': (bm.pom.pom_global.categoria.nom_en
                               if bm.pom.pom_global_id and bm.pom.pom_global.categoria_id
                               else ''),
            'base_value_cm': float(bm.base_value_cm),
            'base_value_display': cv(bm.base_value_cm, unit),
            'unitat': unit,
            'is_key': bm.pom.pom_global.is_key_measure if bm.pom.pom_global_id else False,
            'notes': bm.notes or '',
        } for bm in bms]

        return Response({
            'count': len(data),
            'unitat': unit,
            'results': data,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def graded_specs_with_units_view(request, sf_id):
    """
    GET /api/v1/size-fittings/{id}/graded-specs-units/
    Retorna les GradedSpec (taula de talles) amb valors convertits.
    Agrupa per POM i mostra totes les talles.
    """
    unit = get_unit(request)
    try:
        from fhort.fitting.models import GradedSpec, GradingVersion
        from fhort.fitting.models import SizeFitting

        sf = SizeFitting.objects.select_related('model').get(pk=sf_id)

        # Última versió de grading
        gv = GradingVersion.objects.filter(
            size_fitting=sf
        ).order_by('-creat_at').first()

        if not gv:
            return Response({'count': 0, 'results': [], 'unitat': unit})

        specs = GradedSpec.objects.filter(
            grading_version=gv
        ).select_related(
            'pom', 'pom__pom_global', 'pom__pom_global__categoria'
        ).order_by(
            'pom__pom_global__categoria__display_order',
            'pom__codi_client',
            'size_label'
        )

        # Agrupar per POM
        pom_dict = {}
        talles = []
        for spec in specs:
            pid = spec.pom_id
            if pid not in pom_dict:
                pom_dict[pid] = {
                    'pom_id': pid,
                    'codi_client': spec.pom.codi_client,
                    'nom_client': spec.pom.nom_client,
                    'nom_en': spec.pom.pom_global.nom_en if spec.pom.pom_global_id else '',
                    'categoria_nom': (spec.pom.pom_global.categoria.nom_en
                                       if spec.pom.pom_global_id and spec.pom.pom_global.categoria_id
                                       else ''),
                    'is_key': spec.pom.pom_global.is_key_measure if spec.pom.pom_global_id else False,
                    'values': {},
                }
            pom_dict[pid]['values'][spec.size_label] = {
                'cm': float(spec.value_cm),
                'display': cv(spec.value_cm, unit),
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
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fitting_lines_with_units_view(request, fitting_id):
    """
    GET /api/v1/fittings/{id}/lines-units/
    Retorna les línies d'un fitting amb valors i toleràncies convertits.
    Inclou si cada mesura PASSA o FALLA la tolerància.
    """
    unit = get_unit(request)
    try:
        from fhort.fitting.models import SFFitting, SFFittingLinia

        fitting = SFFitting.objects.get(pk=fitting_id)
        lines = SFFittingLinia.objects.filter(
            fitting=fitting
        ).select_related(
            'pom', 'pom__pom_global', 'pom__pom_global__categoria'
        ).order_by(
            'pom__pom_global__categoria__display_order',
            'pom__codi_client'
        )

        data = []
        for line in lines:
            tol = (float(line.pom.pom_global.tolerancia_woven_cm)
                   if line.pom.pom_global_id else 0.6)

            val_cm = float(line.value_cm) if line.value_cm else None
            spec_cm = float(line.spec_value_cm) if line.spec_value_cm else None

            # Calcular desviació
            desviacio = None
            passa = None
            if val_cm is not None and spec_cm is not None:
                desviacio = round(val_cm - spec_cm, 2)
                passa = abs(desviacio) <= tol

            data.append({
                'id': line.id,
                'pom_id': line.pom_id,
                'codi_client': line.pom.codi_client,
                'nom_client': line.pom.nom_client,
                'nom_en': line.pom.pom_global.nom_en if line.pom.pom_global_id else '',
                'is_key': line.pom.pom_global.is_key_measure if line.pom.pom_global_id else False,
                'spec_cm': spec_cm,
                'spec_display': cv(spec_cm, unit),
                'value_cm': val_cm,
                'value_display': cv(val_cm, unit),
                'desviacio_cm': desviacio,
                'desviacio_display': cv(desviacio, unit) if desviacio is not None else None,
                'tolerancia_cm': tol,
                'tolerancia_display': cv(tol, unit),
                'passa': passa,
                'unitat': unit,
                'notes': line.notes or '',
            })

        n_fail = sum(1 for d in data if d['passa'] is False)
        n_pass = sum(1 for d in data if d['passa'] is True)

        return Response({
            'fitting_id': fitting_id,
            'unitat': unit,
            'resum': {'pass': n_pass, 'fail': n_fail, 'pendent': len(data)-n_pass-n_fail},
            'count': len(data),
            'results': data,
        })
    except SFFitting.DoesNotExist:
        return Response({'error': 'Fitting no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
