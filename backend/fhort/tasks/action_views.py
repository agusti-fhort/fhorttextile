# Sprint 2 — Action endpoints for business logic
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


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
