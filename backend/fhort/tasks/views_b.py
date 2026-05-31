from rest_framework import viewsets, status
from rest_framework import status as http_status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from fhort.accounts.capabilities import HasCapability, DEFINE_TASKS, EXECUTE_TASKS, CLOSE_GATES
from fhort.models_app.models import Model
from .models import TaskType, ModelTask
from .serializers_b import TaskTypeSerializer, ModelTaskSerializer
from .services_c import transition_task, TransitionError, rectification_count
from .services_d import (advance_phase_gate, advance_phases_chain,
                         model_ready_for_gate, GateError)


class TaskTypeViewSet(viewsets.ModelViewSet):
    """Catàleg de tipus de tasca (editable). Lectura: autenticat. Escriptura: define_tasks."""
    queryset = TaskType.objects.all()
    serializer_class = TaskTypeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['active']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        perm = HasCapability(); self.required_capability = DEFINE_TASKS
        return [perm]


class ModelTaskViewSet(viewsets.ModelViewSet):
    """Instàncies de tasca d'un model. Escriptura requereix define_tasks."""
    queryset = ModelTask.objects.select_related('task_type', 'assignee', 'model').all()
    serializer_class = ModelTaskSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['model', 'status', 'task_type', 'assignee']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        perm = HasCapability(); self.required_capability = DEFINE_TASKS
        return [perm]


class _DefineTasks(HasCapability):
    required_capability = DEFINE_TASKS


@api_view(['POST'])
@permission_classes([_DefineTasks])
def define_model_tasks_view(request, model_id):
    """POST /api/v1/models/<model_id>/define-tasks/
    Body: {"task_type_ids": [1,2,3]}  (bulk) o {"task_type_ids": [1]} (individual).
    Crea ModelTask per a cada TaskType indicat, en l'ordre default_order del tipus.
    Idempotència suau: no duplica un (model, task_type) ja existent."""
    ids = request.data.get('task_type_ids') or []
    if not isinstance(ids, list) or not ids:
        return Response({'error': 'task_type_ids ha de ser una llista no buida.'},
                        status=status.HTTP_400_BAD_REQUEST)
    types = list(TaskType.objects.filter(id__in=ids, active=True).order_by('default_order'))
    if not types:
        return Response({'error': 'Cap TaskType actiu trobat per als ids donats.'},
                        status=status.HTTP_400_BAD_REQUEST)
    existing = set(ModelTask.objects.filter(model_id=model_id, task_type_id__in=ids)
                   .values_list('task_type_id', flat=True))
    created = []
    base_order = (ModelTask.objects.filter(model_id=model_id)
                  .count())  # afegeix al final de l'ordre existent
    for i, t in enumerate(types):
        if t.id in existing:
            continue
        mt = ModelTask.objects.create(model_id=model_id, task_type=t,
                                      order=base_order + i, status='Pending')
        created.append(mt.id)
    return Response({'created_ids': created, 'skipped_existing': sorted(existing)},
                    status=status.HTTP_201_CREATED)


class _ExecuteTasks(HasCapability):
    required_capability = EXECUTE_TASKS


@api_view(['POST'])
@permission_classes([_ExecuteTasks])
def transition_task_view(request, pk):
    """POST /api/v1/model-task-items/<pk>/transition/  Body: {"to_status": "InProgress"}
    Aplica la transició. Retorna la tasca i, si escau, paused_task_id (per l'avís del front)."""
    from .models import ModelTask
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil en aquest tenant.'},
                        status=http_status.HTTP_403_FORBIDDEN)
    try:
        task = ModelTask.objects.get(pk=pk)
    except ModelTask.DoesNotExist:
        return Response({'error': 'ModelTask no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)
    to_status = request.data.get('to_status')
    if not to_status:
        return Response({'error': 'to_status requerit.'}, status=http_status.HTTP_400_BAD_REQUEST)
    try:
        result = transition_task(task, to_status, profile)
    except TransitionError as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    return Response(result, status=http_status.HTTP_200_OK)


class _CloseGates(HasCapability):
    required_capability = CLOSE_GATES


@api_view(['POST'])
@permission_classes([_CloseGates])
def gate_model_view(request, model_id):
    """POST /api/v1/models/<model_id>/gate/
    Body: {"to_phase":"Fit","notes":"..."}  o  {"to_phases":["Fit","SizeSet"],"notes":"..."}"""
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil.'}, status=http_status.HTTP_403_FORBIDDEN)
    try:
        model = Model.objects.get(pk=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)
    notes = request.data.get('notes')
    try:
        if request.data.get('to_phases'):
            res = advance_phases_chain(model, request.data['to_phases'], profile, notes)
            return Response({'chain': res}, status=http_status.HTTP_200_OK)
        to_phase = request.data.get('to_phase')
        if not to_phase:
            return Response({'error': 'to_phase o to_phases requerit.'}, status=http_status.HTTP_400_BAD_REQUEST)
        res = advance_phase_gate(model, to_phase, profile, notes)
        return Response(res, status=http_status.HTTP_200_OK)
    except GateError as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([_CloseGates])
def gate_bulk_view(request):
    """POST /api/v1/gates/bulk/  Body: {"items":[{"model_id":1,"to_phase":"Fit"}, ...], "notes":"..."}
    Accions de govern post-reunió. NO exigeix model_ready (decisió de govern, no automatisme)."""
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil.'}, status=http_status.HTTP_403_FORBIDDEN)
    items = request.data.get('items') or []
    if not isinstance(items, list) or not items:
        return Response({'error': 'items ha de ser llista no buida.'}, status=http_status.HTTP_400_BAD_REQUEST)
    notes = request.data.get('notes')
    done, errors = [], []
    for it in items:
        try:
            m = Model.objects.get(pk=it['model_id'])
            done.append(advance_phase_gate(m, it['to_phase'], profile, notes))
        except (Model.DoesNotExist, GateError, KeyError) as e:
            errors.append({'item': it, 'error': str(e)})
    return Response({'done': done, 'errors': errors}, status=http_status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([_CloseGates])
def gate_ready_models_view(request):
    """GET /api/v1/gates/ready/  Kanban del responsable: models llestos per gate
    (totes les ModelTask Done) amb fase actual i comptador de tasques."""
    out = []
    for m in Model.objects.all():
        if model_ready_for_gate(m.id):
            out.append({'model_id': m.id,
                        'codi_intern': getattr(m, 'codi_intern', ''),
                        'fase_actual': m.fase_actual,
                        'task_count': ModelTask.objects.filter(model_id=m.id).count()})
    return Response({'ready': out}, status=http_status.HTTP_200_OK)
