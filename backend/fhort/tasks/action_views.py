# Sprint 2 — Action endpoints for business logic
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_tasks_view(request, model_id):
    """
    POST /api/v1/models/{id}/generar-tasques/
    Generate the ModelTasca rows from the service packages assigned to the model.
    """
    try:
        from fhort.tasks.services import generate_model_tasks
        n = generate_model_tasks(int(model_id))
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
def process_gate_view(request, tasca_id):
    """
    POST /api/v1/model-tasques/{id}/processar-gate/
    Mark the gate as OK and unblock the tasks of the next phase.
    """
    from fhort.tasks.services import process_gate, _get_model_task
    ModelTasca = _get_model_task()

    try:
        mt = ModelTasca.objects.get(pk=tasca_id)
    except ModelTasca.DoesNotExist:
        return Response({'error': 'Tasca no trobada'}, status=404)

    if not mt.es_gate:
        return Response({'error': 'Aquesta tasca no és un gate'}, status=400)

    mt.estat = 'Feta'
    mt.resultat_gate = request.data.get('resultat', 'OK')
    mt.save(update_fields=['estat', 'resultat_gate'])

    n = process_gate(mt.pk)
    return Response({
        'desblocades': n,
        'fase_actual': mt.model.fase_actual,
        'missatge': f'Gate passat. {n} tasques desblocades.',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tasks_summary_view(request, model_id):
    """
    GET /api/v1/models/{id}/resum-tasques/
    Return a summary by state and phase of the model's tasks.
    """
    ModelTasca = _get_model_task_local()
    from fhort.tasks.services import _get_model_task
    ModelTasca = _get_model_task()

    tasks = ModelTasca.objects.filter(model_id=model_id).values(
        'estat', 'tasca__fase', 'tasca__gate'
    )

    summary = {}
    for t in tasks:
        estat = t['estat']
        summary[estat] = summary.get(estat, 0) + 1

    return Response({
        'model_id': model_id,
        'per_estat': summary,
        'total': sum(summary.values()),
    })


def _get_model_task_local():
    try:
        from fhort.tasks.models import ModelTasca
        return ModelTasca
    except ImportError:
        from fhort.models_app.models import ModelTasca
        return ModelTasca
