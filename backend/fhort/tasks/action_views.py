# Sprint 2 — Endpoints d'acció per a lògica de negoci
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_tasques_view(request, model_id):
    """
    POST /api/v1/models/{id}/generar-tasques/
    Genera les ModelTasca des dels paquets de servei assignats al model.
    """
    try:
        from fhort.tasks.services import generar_tasques_model
        n = generar_tasques_model(int(model_id))
        return Response({
            'tasques_creades': n,
            'missatge': f'{n} tasques generades correctament',
        })
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error generant tasques")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def processar_gate_view(request, tasca_id):
    """
    POST /api/v1/model-tasques/{id}/processar-gate/
    Marca el gate com a OK i desbloqueja les tasques de la fase següent.
    """
    from fhort.tasks.services import processar_gate, _get_model_tasca
    ModelTasca = _get_model_tasca()

    try:
        mt = ModelTasca.objects.get(pk=tasca_id)
    except ModelTasca.DoesNotExist:
        return Response({'error': 'Tasca no trobada'}, status=404)

    if not mt.es_gate:
        return Response({'error': 'Aquesta tasca no és un gate'}, status=400)

    mt.estat = 'Feta'
    mt.resultat_gate = request.data.get('resultat', 'OK')
    mt.save(update_fields=['estat', 'resultat_gate'])

    n = processar_gate(mt.pk)
    return Response({
        'desblocades': n,
        'fase_actual': mt.model.fase_actual,
        'missatge': f'Gate passat. {n} tasques desblocades.',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resum_tasques_view(request, model_id):
    """
    GET /api/v1/models/{id}/resum-tasques/
    Retorna resum per estat i fase de les tasques del model.
    """
    ModelTasca = _get_model_tasca_local()
    from fhort.tasks.services import _get_model_tasca
    ModelTasca = _get_model_tasca()

    tasques = ModelTasca.objects.filter(model_id=model_id).values(
        'estat', 'tasca__fase', 'tasca__gate'
    )

    resum = {}
    for t in tasques:
        estat = t['estat']
        resum[estat] = resum.get(estat, 0) + 1

    return Response({
        'model_id': model_id,
        'per_estat': resum,
        'total': sum(resum.values()),
    })


def _get_model_tasca_local():
    try:
        from fhort.tasks.models import ModelTasca
        return ModelTasca
    except ImportError:
        from fhort.models_app.models import ModelTasca
        return ModelTasca
