# Sprint 3 — Endpoints grading
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def tancar_base_view(request, sf_id):
    """
    POST /api/v1/size-fittings/{id}/tancar-base/
    Tanca la talla base i genera les talles automàticament.
    """
    try:
        from fhort.pom.services import tancar_base
        n = tancar_base(int(sf_id), request.user.id)
        return Response({
            'graded_specs_creats': n,
            'missatge': f'{n} especificacions generades correctament',
        })
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error tancant base")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerar_talles_view(request, sf_id):
    """
    POST /api/v1/size-fittings/{id}/regenerar-talles/
    Regenera les talles (per si s'han canviat regles de grading).
    """
    try:
        from fhort.pom.services import generar_graded_specs
        n = generar_graded_specs(int(sf_id))
        return Response({
            'graded_specs_actualitzats': n,
            'missatge': f'{n} especificacions actualitzades',
        })
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def taula_mesures_view(request, sf_id):
    """
    GET /api/v1/size-fittings/{id}/taula-mesures/
    Retorna la taula POM × talla per mostrar al frontend.
    Format: { poms: [...], talles: [...], cells: {pom_id: {talla: value}} }
    """
    try:
        from fhort.fitting.models import SizeFitting, GradedSpec

        sf = SizeFitting.objects.select_related('model').get(pk=sf_id)
        model = sf.model

        # Size run
        size_run = []
        if model.size_run_model:
            size_run = [s.strip() for s in model.size_run_model.replace(';', '·').split('·') if s.strip()]

        # GradedSpecs actius
        grading_version = None
        try:
            from fhort.fitting.models import GradingVersion
            grading_version = GradingVersion.objects.filter(
                size_fitting=sf, is_active=True
            ).last()
        except Exception:
            pass

        cells = {}
        poms_info = []
        poms_seen = set()

        if grading_version:
            specs = GradedSpec.objects.filter(
                grading_version=grading_version, is_active=True
            ).select_related('pom').order_by('pom__display_order', 'size_label')

            for spec in specs:
                pom_id = spec.pom_id
                if pom_id not in poms_seen:
                    poms_seen.add(pom_id)
                    poms_info.append({
                        'id': pom_id,
                        'codi': spec.pom.pom_code,
                        'nom_cat': spec.pom.name_cat,
                        'nom_en': spec.pom.name_en,
                        'display_order': spec.pom.display_order,
                        'is_key_measure': spec.pom.is_key_measure,
                    })
                if pom_id not in cells:
                    cells[pom_id] = {}
                cells[pom_id][spec.size_label] = {
                    'value': spec.graded_value_cm,
                    'type': spec.grading_type_applied,
                    'increment': spec.increment_applied_cm,
                }

        # BaseMeasurements si no hi ha grading
        if not grading_version:
            try:
                from fhort.models_app.models import BaseMeasurement
                base_ms = BaseMeasurement.objects.filter(
                    model=model, is_active=True
                ).select_related('pom')
                for bm in base_ms:
                    pom_id = bm.pom_id
                    if pom_id not in poms_seen:
                        poms_seen.add(pom_id)
                        poms_info.append({
                            'id': pom_id,
                            'codi': bm.pom.pom_code,
                            'nom_cat': bm.pom.name_cat,
                            'nom_en': bm.pom.name_en,
                            'display_order': bm.pom.display_order,
                            'is_key_measure': bm.pom.is_key_measure,
                        })
                    if pom_id not in cells:
                        cells[pom_id] = {}
                    cells[pom_id][model.base_size_label] = {
                        'value': bm.base_value_cm,
                        'type': 'BASE',
                        'increment': 0,
                    }
            except Exception:
                pass

        poms_info.sort(key=lambda x: x.get('display_order', 999))

        return Response({
            'sf_id': sf_id,
            'codi_model': model.codi_intern,
            'estat': sf.estat,
            'estat_display': sf.get_estat_display(),
            'base_tancada': sf.base_tancada,
            'base_size': model.base_size_label,
            'size_run': size_run,
            'poms': poms_info,
            'cells': {str(k): v for k, v in cells.items()},
        })

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error generant taula mesures")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
