"""
fhort/pom/s10_views.py — Sprint S10: Fitting vs Size Library
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
    if val is None: return None
    v = float(val)
    return round(v * CM_TO_INCH, 3) if unit == 'INCH' else round(v, 2)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fitting_vs_spec_view(request, sf_id, fitting_id):
    """
    GET /api/v1/size-fittings/{sf_id}/fittings/{fitting_id}/vs-spec/
    Compara les mesures del fitting amb les especificacions del model.
    Retorna per POM: spec, mesurat, desviació, tolerància, pass/fail.
    """
    unit = get_unit(request)
    try:
        from fhort.fitting.models import SFFitting, SFFittingLinia, GradedSpec, GradingVersion
        from fhort.models_app.models import BaseMeasurement

        fitting = SFFitting.objects.select_related(
            'size_fitting__model'
        ).get(pk=fitting_id, size_fitting_id=sf_id)

        model = fitting.size_fitting.model
        talla_fitting = fitting.size_label or model.base_size_label

        # Specs de la talla del fitting
        gv = GradingVersion.objects.filter(
            size_fitting=fitting.size_fitting
        ).order_by('-creat_at').first()

        spec_map = {}
        if gv and talla_fitting:
            specs = GradedSpec.objects.filter(
                grading_version=gv, size_label=talla_fitting
            ).select_related('pom')
            spec_map = {s.pom_id: float(s.value_cm) for s in specs}
        else:
            # Fallback: BaseMeasurements (talla base)
            bms = BaseMeasurement.objects.filter(model=model, is_active=True)
            spec_map = {bm.pom_id: float(bm.base_value_cm) for bm in bms}

        # Línies del fitting
        lines = SFFittingLinia.objects.filter(
            fitting=fitting
        ).select_related('pom', 'pom__pom_global')

        resultats = []
        n_pass = n_fail = n_pend = 0

        for line in lines:
            spec_cm = spec_map.get(line.pom_id)
            val_cm = float(line.value_cm) if line.value_cm else None
            tol = float(line.pom.pom_global.tolerancia_woven_cm
                        if line.pom.pom_global_id else 0.6)

            desv = round(val_cm - spec_cm, 2) if (val_cm and spec_cm) else None
            passa = abs(desv) <= tol if desv is not None else None

            if passa is True: n_pass += 1
            elif passa is False: n_fail += 1
            else: n_pend += 1

            resultats.append({
                'pom_id': line.pom_id,
                'codi_client': line.pom.codi_client,
                'nom_en': line.pom.pom_global.nom_en if line.pom.pom_global_id else line.pom.nom_client,
                'is_key': line.pom.pom_global.is_key_measure if line.pom.pom_global_id else False,
                'spec_cm': spec_cm,
                'spec_display': cv(spec_cm, unit),
                'value_cm': val_cm,
                'value_display': cv(val_cm, unit),
                'desviacio_cm': desv,
                'desviacio_display': cv(desv, unit),
                'tolerancia_cm': tol,
                'tolerancia_display': cv(tol, unit),
                'passa': passa,
                'unitat': unit,
            })

        # Generar POMAlerts per les desviacions
        from fhort.pom.models import POMMaster
        try:
            from fhort.pom.models import POMAlert
            for r in resultats:
                if r['passa'] is False:
                    POMAlert.objects.update_or_create(
                        model=model,
                        pom_id=r['pom_id'],
                        size_fitting=fitting.size_fitting,
                        defaults={
                            'desviacio_cm': r['desviacio_cm'],
                            'tolerancia_cm': r['tolerancia_cm'],
                            'missatge': (f"Fitting {fitting_id}: {r['codi_client']} "
                                          f"desvia {r['desviacio_cm']:+.2f}cm "
                                          f"(tol ±{r['tolerancia_cm']}cm)"),
                            'estat': 'Obert',
                            'origen': 'FITTING',
                        }
                    )
        except Exception:
            pass  # POMAlert pot no existir encara

        return Response({
            'fitting_id': fitting_id,
            'talla': talla_fitting,
            'model_nom': model.nom_prenda,
            'unitat': unit,
            'resum': {'pass': n_pass, 'fail': n_fail, 'pendent': n_pend,
                       'total': n_pass + n_fail + n_pend},
            'count': len(resultats),
            'results': resultats,
        })

    except SFFitting.DoesNotExist:
        return Response({'error': 'Fitting no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("fitting_vs_spec_view error")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_fitting_history_view(request, model_id):
    """
    GET /api/v1/models/{id}/fitting-history/
    Historial de tots els fittings d'un model amb resum pass/fail.
    """
    unit = get_unit(request)
    try:
        from fhort.fitting.models import SFFitting, SFFittingLinia
        from fhort.models_app.models import Model

        model = Model.objects.get(pk=model_id)
        sfs = model.size_fittings.all()

        resultats = []
        for sf in sfs:
            fittings = sf.fittings.all().order_by('-creat_at') if hasattr(sf, 'fittings') else []
            for fitting in fittings:
                lines = SFFittingLinia.objects.filter(fitting=fitting)
                n_total = lines.count()
                resultats.append({
                    'sf_id': sf.id,
                    'sf_codi': sf.codi,
                    'fitting_id': fitting.id,
                    'talla': fitting.size_label or model.base_size_label,
                    'data': fitting.creat_at.isoformat() if hasattr(fitting, 'creat_at') else '',
                    'n_poms': n_total,
                    'estat': sf.estat,
                })

        return Response({
            'model_id': model_id,
            'count': len(resultats),
            'results': resultats,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)
