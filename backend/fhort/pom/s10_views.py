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
    if val is None:
        return None
    v = float(val)
    return round(v * CM_TO_INCH, 3) if unit == 'INCH' else round(v, 2)


def _pom_codi(p):
    if not p:
        return ''
    if getattr(p, 'pom_global_id', None):
        return p.pom_global.codi
    return p.codi_client or ''


def _pom_nom_en(p):
    if not p:
        return ''
    if getattr(p, 'pom_global_id', None) and p.pom_global.nom_en:
        return p.pom_global.nom_en
    return p.nom_client or ''


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fitting_vs_spec_view(request, sf_id, fitting_id):
    """
    GET /api/v1/size-fittings/{sf_id}/fittings/{fitting_id}/vs-spec/
    Compara fitting vs specs (GradedSpec o fallback BaseMeasurement).
    """
    unit = get_unit(request)
    try:
        from fhort.fitting.models import SFFitting, SFFittingLinia, GradedSpec, GradingVersion
        from fhort.models_app.models import BaseMeasurement

        fitting = SFFitting.objects.select_related(
            'size_fitting__model'
        ).get(pk=fitting_id, size_fitting_id=sf_id)

        sf = fitting.size_fitting
        model = sf.model if sf else None
        talla_fitting = None  # SFFitting no te size_label; usem talla de les linies

        gv = GradingVersion.objects.filter(
            size_fitting=sf
        ).order_by('-data', '-id').first()

        spec_map = {}
        if gv:
            # Si tenim grading, agafem un map (pom_id, size_label) → valor
            specs = GradedSpec.objects.filter(
                grading_version=gv, is_active=True
            ).select_related('pom')
            spec_map = {
                (s.pom_id, s.size_label): float(s.graded_value_cm) if s.graded_value_cm is not None else None
                for s in specs
            }

        # Fallback per quan no hi ha grading: BaseMeasurements (talla base)
        base_map = {}
        if model:
            for bm in BaseMeasurement.objects.filter(model=model, is_active=True):
                if bm.base_value_cm is not None:
                    base_map[bm.pom_id] = float(bm.base_value_cm)

        lines = SFFittingLinia.objects.filter(
            fitting=fitting
        ).select_related('pom', 'pom__pom_global').order_by('pom__codi_client', 'talla')

        TOL_DEFAULT = 0.6
        resultats = []
        n_pass = n_fail = n_pend = 0

        for line in lines:
            # Buscar spec segons (pom, talla); fallback a base
            spec_cm = spec_map.get((line.pom_id, line.talla))
            if spec_cm is None:
                spec_cm = base_map.get(line.pom_id)

            val_cm = float(line.valor_nou) if line.valor_nou is not None else None
            tol = TOL_DEFAULT

            desv = None
            passa = None
            if val_cm is not None and spec_cm is not None:
                desv = round(val_cm - spec_cm, 2)
                passa = abs(desv) <= tol

            if passa is True:
                n_pass += 1
            elif passa is False:
                n_fail += 1
            else:
                n_pend += 1

            resultats.append({
                'pom_id': line.pom_id,
                'codi_client': _pom_codi(line.pom),
                'nom_en': _pom_nom_en(line.pom),
                'talla': line.talla,
                'is_key': line.pom.is_key_measure if line.pom_id else False,
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

        # Generar POMAlerts (si el model existeix)
        try:
            from fhort.pom.models import POMAlert
            for r in resultats:
                if r['passa'] is False and model:
                    POMAlert.objects.update_or_create(
                        model=model,
                        pom_id=r['pom_id'],
                        size_fitting=sf,
                        defaults={
                            'desviacio_cm': r['desviacio_cm'],
                            'tolerancia_cm': r['tolerancia_cm'],
                            'missatge': (f"Fitting {fitting_id}: {r['codi_client']} "
                                         f"talla {r['talla']} desvia {r['desviacio_cm']:+.2f}cm "
                                         f"(tol ±{r['tolerancia_cm']}cm)"),
                            'estat': 'Obert',
                            'origen': 'FITTING',
                        }
                    )
        except Exception:
            pass

        return Response({
            'fitting_id': fitting_id,
            'talla': talla_fitting,
            'model_nom': model.nom_prenda if model else '',
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
        logging.getLogger(__name__).exception('fitting_vs_spec_view error')
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_fitting_history_view(request, model_id):
    """
    GET /api/v1/models/{id}/fitting-history/
    Historial de tots els fittings d'un model amb count POMs.
    """
    try:
        from fhort.fitting.models import SFFitting, SFFittingLinia, SizeFitting
        from fhort.models_app.models import Model

        model = Model.objects.get(pk=model_id)
        sfs = SizeFitting.objects.filter(model=model).order_by('-data_creacio')

        resultats = []
        for sf in sfs:
            fittings = SFFitting.objects.filter(size_fitting=sf).order_by('-data_creacio')
            for fitting in fittings:
                n_total = SFFittingLinia.objects.filter(fitting=fitting).count()
                resultats.append({
                    'sf_id': sf.id,
                    'sf_codi': sf.codi or '',
                    'sf_numero': sf.numero,
                    'sf_tipus': sf.tipus,
                    'sf_estat': sf.estat,
                    'fitting_id': fitting.id,
                    'fitting_num': fitting.fitting_num,
                    'fitting_estat': fitting.estat,
                    'fitting_tipus': fitting.tipus,
                    'data_creacio': fitting.data_creacio.isoformat() if fitting.data_creacio else None,
                    'data_tancament': fitting.data_tancament.isoformat() if fitting.data_tancament else None,
                    'n_poms': n_total,
                })

        return Response({
            'model_id': model_id,
            'count': len(resultats),
            'results': resultats,
        })
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('model_fitting_history_view error')
        return Response({'error': str(e)}, status=500)
