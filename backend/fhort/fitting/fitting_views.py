# Sprint 4 — Fitting wizard views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_fitting_view(request, sf_id):
    """
    POST /api/v1/size-fittings/{id}/crear-fitting/
    Body: {"tipus": "Proto"} | "Sample" | "PPS"
    Crea un nou fitting amb línies pre-poblades des de GradedSpec.
    """
    tipus = request.data.get('tipus', 'Proto')
    valid_tipus = ['Proto', 'Sample', 'PPS']
    if tipus not in valid_tipus:
        return Response(
            {'error': f'tipus ha de ser un de: {valid_tipus}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        from fhort.fitting.services import crear_fitting
        fitting, n_linies = crear_fitting(int(sf_id), tipus, request.user.id)

        return Response({
            'fitting_id': fitting.pk,
            'fitting_num': fitting.fitting_num,
            'tipus': fitting.tipus,
            'estat': fitting.estat,
            'linies_creades': n_linies,
            'missatge': f'Fitting #{fitting.fitting_num} creat amb {n_linies} línies',
        }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error creant fitting")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def tancar_fitting_view(request, fitting_id):
    """
    POST /api/v1/fittings/{id}/tancar/
    Tanca el fitting i actualitza els GradedSpec amb els valors nous.
    """
    try:
        from fhort.fitting.services import tancar_fitting
        result = tancar_fitting(int(fitting_id))
        return Response({
            **result,
            'missatge': (
                f"Fitting tancat. {result['modificades']} mesures modificades, "
                f"{result['ok']} sense canvis."
            ),
        })
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error tancant fitting")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def anullar_fitting_view(request, fitting_id):
    """POST /api/v1/fittings/{id}/anullar/"""
    motiu = request.data.get('motiu', '')
    try:
        from fhort.fitting.services import anullar_fitting
        anullar_fitting(int(fitting_id), motiu)
        return Response({'missatge': 'Fitting anul·lat correctament'})
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def llistat_fittings_view(request, sf_id):
    """
    GET /api/v1/size-fittings/{id}/fittings/
    Retorna tots els fittings d'un SF amb resum de línies.
    """
    try:
        from fhort.fitting.models import SFFitting
        fittings = SFFitting.objects.filter(
            size_fitting_id=sf_id
        ).select_related('responsable').order_by('fitting_num')

        data = []
        for f in fittings:
            n_linies = f.linies.count() if hasattr(f, 'linies') else 0
            n_modif = f.linies.filter(estat_cella='Modificat').count() if hasattr(f, 'linies') else 0
            data.append({
                'id': f.pk,
                'fitting_num': f.fitting_num,
                'tipus': f.tipus,
                'estat': f.estat,
                'data_inici': f.data_inici,
                'data_fi': getattr(f, 'data_fi', None),
                'responsable': str(f.responsable) if f.responsable else None,
                'n_linies': n_linies,
                'n_modificades': n_modif,
            })

        return Response({'sf_id': sf_id, 'fittings': data})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
