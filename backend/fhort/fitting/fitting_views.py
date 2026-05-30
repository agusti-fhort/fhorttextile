# Sprint 4 — Fitting wizard views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_fitting_view(request, sf_id):
    """
    POST /api/v1/size-fittings/{id}/crear-fitting/
    Body: {"tipus": "Proto"} | "Sample" | "PPS"
    Create a new fitting with lines pre-populated from GradedSpec.
    """
    fitting_type = request.data.get('tipus', 'Proto')
    valid_types = ['Proto', 'Sample', 'PPS']
    if fitting_type not in valid_types:
        return Response(
            {'error': f'tipus ha de ser un de: {valid_types}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        from fhort.fitting.services import create_fitting
        fitting, n_lines = create_fitting(int(sf_id), fitting_type, request.user.id)

        return Response({
            'fitting_id': fitting.pk,
            'fitting_num': fitting.fitting_num,
            'tipus': fitting.tipus,
            'estat': fitting.estat,
            'linies_creades': n_lines,
            'missatge': f'Fitting #{fitting.fitting_num} creat amb {n_lines} línies',
        }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error creating fitting")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_fitting_view(request, fitting_id):
    """
    POST /api/v1/fittings/{id}/tancar/
    Close the fitting and update the GradedSpec with the new values.
    """
    try:
        from fhort.fitting.services import close_fitting
        result = close_fitting(int(fitting_id))
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
        logging.getLogger(__name__).exception("Error closing fitting")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_fitting_view(request, fitting_id):
    """POST /api/v1/fittings/{id}/anullar/"""
    reason = request.data.get('motiu', '')
    try:
        from fhort.fitting.services import cancel_fitting
        cancel_fitting(int(fitting_id), reason)
        return Response({'missatge': 'Fitting anul·lat correctament'})
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_fittings_view(request, sf_id):
    """
    GET /api/v1/size-fittings/{id}/fittings/
    Return all fittings of an SF with a line summary.
    """
    try:
        from fhort.fitting.models import SFFitting
        fittings = SFFitting.objects.filter(
            size_fitting_id=sf_id
        ).select_related('responsable').order_by('fitting_num')

        data = []
        for f in fittings:
            n_lines = f.linies.count() if hasattr(f, 'linies') else 0
            n_modified = f.linies.filter(estat_cella='Modificat').count() if hasattr(f, 'linies') else 0
            data.append({
                'id': f.pk,
                'fitting_num': f.fitting_num,
                'tipus': f.tipus,
                'estat': f.estat,
                'data_inici': f.data_inici,
                'data_fi': getattr(f, 'data_fi', None),
                'responsable': str(f.responsable) if f.responsable else None,
                'n_linies': n_lines,
                'n_modificades': n_modified,
            })

        return Response({'sf_id': sf_id, 'fittings': data})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
