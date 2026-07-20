from rest_framework import viewsets, status
from rest_framework import status as http_status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, ProtectedError

from rest_framework.exceptions import ValidationError
from fhort.accounts.capabilities import (HasCapability, DEFINE_TASKS, EXECUTE_TASKS,
                                         CLOSE_GATES, SCHEDULE_FITTINGS, CONFIGURE, VIEW_TEAM_TASKS,
                                         get_allowed_task_types, scope_model_task_queryset)
from fhort.models_app.models import Model
from .models import (TaskType, ModelTask, Supplier, Production,
                     GarmentTypeItem, TaskTimeEstimate, TaskTransition, Customer, TimeSeed)
from .serializers_b import (TaskTypeSerializer, ModelTaskSerializer,
                            SupplierSerializer, ProductionSerializer,
                            GarmentTypeItemSerializer, TaskTimeEstimateSerializer,
                            CustomerSerializer)
from .services_c import transition_task, TransitionError, rectification_count
from .services_d import (advance_phase_gate, advance_phases_chain, regress_phase,
                         model_ready_for_gate, GateError)
from .services_e import (request_production, set_production_status,
                         ProductionError, has_delivered_production)
from .services_g import lookup_estimated_minutes


class TaskTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Catàleg CANÒNIC de tipus de tasca (propietat del sistema). READ-ONLY via API:
    el tenant no l'edita (només list/retrieve, autenticat). L'alta/enriquiment del catàleg
    viu a migracions de seed (patró POMGlobal), no a un CRUD del tenant. Escriure-hi
    (POST/PUT/PATCH/DELETE) retorna 405 per a tothom, inclòs admin."""
    queryset = TaskType.objects.all()
    serializer_class = TaskTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['active']


class ModelTaskViewSet(viewsets.ModelViewSet):
    """Instàncies de tasca d'un model. Escriptura requereix define_tasks."""
    queryset = ModelTask.objects.select_related('task_type', 'assignee', 'model').all()
    serializer_class = ModelTaskSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['model', 'status', 'task_type', 'assignee']

    def get_queryset(self):
        """Row-level scope (Opció A): sense VIEW_TEAM_TASKS, l'usuari només veu les seves
        tasques; si a més té DEFINE_TASKS, també les NO assignades (per poder assignar-les).
        Mai veu les tasques ja assignades d'altri. Els filterset_fields s'apliquen damunt
        d'aquest abast, de manera que ?assignee=<altre> NO pot tornar tasques alienes.

        Aquest queryset el comparteixen update/partial_update/destroy (gate DEFINE_TASKS):
        un product_manager pot assignar/editar les NO assignades, mai les d'altri."""
        return scope_model_task_queryset(super().get_queryset(), self.request.user)

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'by_model'):
            return [IsAuthenticated()]
        perm = HasCapability(); self.required_capability = DEFINE_TASKS
        return [perm]

    # Whitelist d'ordenació pública → camp real del queryset agrupat. Qualsevol valor fora
    # d'aquí s'ignora (mai es passa el valor cru a .order_by() → cap injecció d'ordering).
    # Tots els camps de Model referenciats han d'estar a values() perquè order_by no alteri el GROUP BY.
    _ORDERING = {
        'nom_prenda': 'model__nom_prenda', 'codi_intern': 'model__codi_intern',
        'any': 'model__any', 'temporada': 'model__temporada', 'prioritat': 'model__prioritat',
        'data_entrada': 'model__data_entrada', 'data_objectiu': 'model__data_objectiu',
        'data_tancament': 'model__data_tancament', 'fase_actual': 'model__fase_actual',
        'estat': 'model__estat',
        # comptadors annotats (ordenació opcional):
        'in_progress': 'in_progress', 'pending': 'pending', 'paused': 'paused', 'done': 'done',
    }
    _DEFAULT_ORDER = ('-in_progress', '-pending', '-paused', 'model__codi_intern')

    @action(detail=False, methods=['get'], url_path='by-model')
    def by_model(self, request):
        """GET /api/v1/model-task-items/by-model/  — agregador per a la columna 1 del Kanban.

        Agrupa per model les ModelTask VISIBLES per a l'usuari (reusa el row-level scope de
        get_queryset(): sense view_team_tasks → només les pròpies). Els comptadors per estat es
        calculen a la BD (Count + filter=Q), de manera que escala a 600+ models sense carregar files.

        Query params:
          ?all=true        inclou també els models amb totes les tasques Done (per defecte s'oculten).
          ?search=         icontains sobre codi_intern OR nom_prenda (OR).
          ?ordering=       camp de la whitelist _ORDERING (prefix '-' = desc; coma = multi).
                           Valors fora de la whitelist s'ignoren → es manté l'ordre per defecte.
          Filtres exactes (additius, AND; valors invàlids ignorats silenciosament):
            ?temporada= (SS/FW/CO/SP)  ?estat= (Nou/EnCurs/EnRevisio/Tancat)
            ?fase_actual= (Proto/Fit/SizeSet/PP/TOP)  ?garment_type=<id>  ?any=<int>
            ?prioritat=<int>  ?responsable=<userprofile_id> | me (perfil de request.user)
            ?customer=<id>  ?collection=<text icontains>  (campanya del board, Sprint 5)
            ?data_objectiu_after=YYYY-MM-DD  ?data_objectiu_before=YYYY-MM-DD (rang inclusiu)

        Resposta (paginada, mateixa paginació del projecte):
          [{ model_id, model_codi, model_nom, fase, counts:{pending,paused,in_progress,done},
             prioritat, temporada, estat, data_objectiu, responsable_id }]

        Ordenació per defecte (sense ?ordering): feina activa/pendent a dalt
          (-in_progress,-pending,-paused), desempat per codi_intern (unique → estable per paginar).
        """
        qs = self.get_queryset()   # ← MATEIX scope que model-task-items/ (no duplicat)
        qp = request.query_params

        search = (qp.get('search') or '').strip()
        if search:
            # Punt d'extensió: quan calgui, afegir aquí col·lecció i garment_type SENSE tocar
            # el contracte de resposta (p. ex. q |= Q(model__garment_group__nom__icontains=search)).
            q = Q(model__codi_intern__icontains=search) | Q(model__nom_prenda__icontains=search)
            qs = qs.filter(q)

        # --- Filtres exactes opcionals (sobre el queryset abans d'agrupar) ---
        def _choice_set(choices):
            return {c[0] for c in choices}

        temporada = qp.get('temporada')
        if temporada in _choice_set(Model.TEMPORADA_CHOICES):
            qs = qs.filter(model__temporada=temporada)
        estat = qp.get('estat')
        if estat in _choice_set(Model.ESTAT_CHOICES):
            qs = qs.filter(model__estat=estat)
        fase = qp.get('fase_actual')
        if fase in _choice_set(Model.FASE_CHOICES):
            qs = qs.filter(model__fase_actual=fase)

        responsable = qp.get('responsable')
        if responsable == 'me':
            # FIX 2 — "jo" = models on sóc ASSIGNEE d'alguna tasca (no Model.responsable, sovint null).
            # qs és un queryset de ModelTask → subquery per model_id (manté els comptadors complets).
            profile = getattr(request.user, 'profile', None)
            qs = (qs.filter(model_id__in=ModelTask.objects.filter(assignee=profile).values('model_id'))
                  if profile is not None else qs.none())
        elif responsable and responsable.isdigit():
            # Coherent amb 'me': filtra per models on aquest PERFIL és assignee d'alguna tasca
            # (la seva càrrega real), no per model__responsable_id (director del model).
            qs = qs.filter(model_id__in=ModelTask.objects.filter(
                assignee_id=int(responsable)).values('model_id'))

        garment_type = qp.get('garment_type')
        if garment_type and garment_type.isdigit():
            qs = qs.filter(model__garment_type_id=int(garment_type))
        any_ = qp.get('any')
        if any_ and any_.isdigit():
            qs = qs.filter(model__any=int(any_))
        prioritat = qp.get('prioritat')
        if prioritat and prioritat.isdigit():
            qs = qs.filter(model__prioritat=int(prioritat))

        # --- Filtres de campanya del board (Sprint 5): mirall additiu del filterset del Model
        # list, perquè el board del Dashboard pugui acotar per client/col·lecció/data-objectiu
        # igual que els comptadors per fase. Valors invàlids ignorats silenciosament. ---
        customer = qp.get('customer')
        if customer and customer.isdigit():
            qs = qs.filter(model__customer_id=int(customer))
        collection = (qp.get('collection') or '').strip()
        if collection:
            qs = qs.filter(model__collection__icontains=collection)
        from datetime import date as _date
        for param, lookup in (('data_objectiu_after', 'gte'), ('data_objectiu_before', 'lte')):
            raw = qp.get(param)
            if raw:
                try:
                    qs = qs.filter(**{f'model__data_objectiu__{lookup}': _date.fromisoformat(raw)})
                except ValueError:
                    pass   # data mal formada → s'ignora (no trenca la consulta)

        agg = (qs.values(
                   'model_id', 'model__codi_intern', 'model__nom_prenda', 'model__fase_actual',
                   'model__estat', 'model__temporada', 'model__prioritat', 'model__data_objectiu',
                   'model__responsable_id', 'model__any', 'model__data_entrada', 'model__data_tancament',
               )
               .annotate(
                   pending=Count('id', filter=Q(status='Pending')),
                   paused=Count('id', filter=Q(status='Paused')),
                   in_progress=Count('id', filter=Q(status='InProgress')),
                   done=Count('id', filter=Q(status='Done')),
               ))

        # --- Ordenació: whitelist estricta; default si res vàlid ---
        order_fields = []
        for raw in (qp.get('ordering') or '').split(','):
            raw = raw.strip()
            if not raw:
                continue
            desc = raw.startswith('-')
            mapped = self._ORDERING.get(raw[1:] if desc else raw)
            if mapped:
                order_fields.append(('-' + mapped) if desc else mapped)
        agg = agg.order_by(*(order_fields or self._DEFAULT_ORDER))

        if qp.get('all') != 'true':
            # Per defecte només models amb alguna tasca no-Done (HAVING sobre els comptadors).
            agg = agg.filter(Q(pending__gt=0) | Q(paused__gt=0) | Q(in_progress__gt=0))

        def kanban_state(pending, paused, in_progress, done):
            """Estat-kanban derivat del model (única font de veritat al backend, Sprint 5 1c).
            ∈ {pending, open, paused, done}. Ordre: feina viva mana sobre l'estàtica.
              open    si in_progress>0
              paused  si paused>0 i in_progress=0
              pending si queda pendent (i res actiu/pausat)
              done    si tot Done (cap pending/paused/in_progress)
            Així el frontend no recalcula la classificació."""
            if in_progress > 0:
                return 'open'
            if paused > 0:
                return 'paused'
            if pending > 0:
                return 'pending'
            return 'done'

        def shape(row):
            return {
                'model_id': row['model_id'],
                'model_codi': row['model__codi_intern'],
                'model_nom': row['model__nom_prenda'],
                'fase': row['model__fase_actual'],
                'counts': {
                    'pending': row['pending'],
                    'paused': row['paused'],
                    'in_progress': row['in_progress'],
                    'done': row['done'],
                },
                'kanban_state': kanban_state(
                    row['pending'], row['paused'], row['in_progress'], row['done']),
                # Extres additius (la UI els pot etiquetar sense una segona crida):
                'prioritat': row['model__prioritat'],
                'temporada': row['model__temporada'],
                'estat': row['model__estat'],
                'data_objectiu': row['model__data_objectiu'],
                'responsable_id': row['model__responsable_id'],
            }

        page = self.paginate_queryset(agg)
        if page is not None:
            return self.get_paginated_response([shape(r) for r in page])
        return Response([shape(r) for r in agg])

    def _validate_assignee(self, serializer):
        """Enforcement Opció A: no es pot assignar una tasca a algú que no la pot fer.
        Quan un PATCH/POST estableix assignee no-null, exigeix que el task_type.code
        sigui a l'allow-list de l'assignee (get_allowed_task_types). Admin = bypass."""
        if 'assignee' not in serializer.validated_data:
            return
        assignee = serializer.validated_data.get('assignee')
        if assignee is None:
            return   # desassignar sempre permès
        task_type = serializer.validated_data.get('task_type') or \
            getattr(serializer.instance, 'task_type', None)
        if task_type is None:
            return
        if task_type.code not in get_allowed_task_types(assignee.user):
            raise ValidationError(
                {'assignee': f"L'usuari assignat no té permès el tipus de tasca "
                             f"'{task_type.code}' (allow-list de tasques)."})

    @action(detail=False, methods=['post'], url_path='extra')
    def extra(self, request):
        """POST /api/v1/model-task-items/extra/ — crea una tasca EXTRA off_recipe (B4a).

        Body: {work_order, model, task_type}. Neix origen='ad_hoc', off_recipe=True,
        status='Pending', lligada al WorkOrder. Gate DEFINE_TASKS (get_permissions).
        Guards: WO ha d'estar OPEN; per un WO ORDER el model ha de coincidir amb el del WO;
        per un COLLECTOR el model ha de ser del mateix customer."""
        from fhort.commerce.models import WorkOrder
        wo_id = request.data.get('work_order')
        model_id = request.data.get('model')
        tt_id = request.data.get('task_type')
        if not (wo_id and model_id and tt_id):
            return Response({'error': 'Calen work_order, model i task_type.'},
                            status=status.HTTP_400_BAD_REQUEST)
        wo = WorkOrder.objects.filter(pk=wo_id).first()
        if wo is None:
            return Response({'error': 'WorkOrder no trobat.'}, status=status.HTTP_404_NOT_FOUND)
        if wo.status != 'OPEN':
            return Response({'error': "L'encàrrec està tancat: no accepta més tasques."},
                            status=status.HTTP_409_CONFLICT)
        model = Model.objects.filter(pk=model_id).first()
        if model is None:
            return Response({'error': 'Model no trobat.'}, status=status.HTTP_404_NOT_FOUND)
        if wo.kind == 'ORDER' and wo.model_id != model.pk:
            return Response({'error': "El model no correspon a l'encàrrec (WO ORDER)."},
                            status=status.HTTP_400_BAD_REQUEST)
        if wo.kind == 'COLLECTOR' and model.customer_id != wo.customer_id:
            return Response({'error': "El model no és del client del col·lector."},
                            status=status.HTTP_400_BAD_REQUEST)
        tt = TaskType.objects.filter(pk=tt_id, active=True).first()
        if tt is None:
            return Response({'error': 'TaskType no trobat o inactiu.'},
                            status=status.HTTP_404_NOT_FOUND)
        order = ModelTask.objects.filter(model=model).count()
        task = ModelTask.objects.create(
            model=model, task_type=tt, order=order, status='Pending',
            origen='ad_hoc', off_recipe=True, work_order=wo)
        return Response(ModelTaskSerializer(task).data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        self._validate_assignee(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validate_assignee(serializer)
        old_assignee_id = serializer.instance.assignee_id
        serializer.save()
        new_assignee_id = serializer.instance.assignee_id
        # Reassignar una tasca (canvi de tècnic) → recalcular la cua SENCERA dels DOS tècnics.
        if old_assignee_id != new_assignee_id:
            inst = serializer.instance
            # Si s'ha desassignat (nou=None), buidar planned_* d'aquesta tasca (read-only al
            # serializer, així que ho fem aquí) abans de recalcular.
            if new_assignee_id is None and inst.status != 'Done':
                ModelTask.objects.filter(pk=inst.pk).update(
                    planned_start=None, planned_end=None, planned_locked=False)
            from fhort.planning.plan_service import recompute_for_technicians, cleanup_queue_order
            # Si el model ha sortit de la cua del tècnic vell (o nou=None), esborra l'ordre manual.
            cleanup_queue_order([old_assignee_id, new_assignee_id], [inst.model_id])
            recompute_for_technicians([old_assignee_id, new_assignee_id])


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
    existing = set(ModelTask.objects.filter(model_id=model_id, task_type_id__in=ids,
                                             origen='prevista')
                   .values_list('task_type_id', flat=True))
    if not Model.objects.filter(pk=model_id).exists():
        return Response({'error': 'Model no trobat.'}, status=status.HTTP_404_NOT_FOUND)
    model = Model.objects.get(pk=model_id)  # instància per al lookup d'estimació (Sprint G)
    created = []
    base_order = (ModelTask.objects.filter(model_id=model_id)
                  .count())  # afegeix al final de l'ordre existent
    for i, t in enumerate(types):
        if t.id in existing:
            continue
        est = lookup_estimated_minutes(model, t)   # snapshot del temps estimat (None si no n'hi ha)
        mt = ModelTask.objects.create(model_id=model_id, task_type=t,
                                      order=base_order + i, status='Pending',
                                      origen='prevista', estimated_minutes=est)
        created.append(mt.id)
    return Response({'created_ids': created, 'skipped_existing': sorted(existing)},
                    status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_task_log_view(request, model_id):
    """GET /api/v1/models/<model_id>/task-log/ — log informatiu (read-only) de les transicions
    de les ModelTask del model, ordenat per data/hora desc. Font: TaskTransition."""
    qs = (TaskTransition.objects
          .filter(model_task__model_id=model_id)
          .select_related('model_task__task_type', 'by')
          .order_by('-at'))
    log = [{
        'id': tr.id,
        'task_type': tr.model_task.task_type.code,
        'from_status': tr.from_status,
        'to_status': tr.to_status,
        'by': (tr.by.nom_complet if tr.by_id else None),
        'at': tr.at.isoformat(),
    } for tr in qs[:300]]
    return Response({'log': log}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_DefineTasks])
def assign_model_view(request, model_id):
    """POST /api/v1/models/<model_id>/assign/
    Body: {"assignee_id": <UserProfile id>, "task_ids": [..]?}.
    Assigna el tècnic a les tasques no-Done del model (totes, o només task_ids) i recalcula la
    cua SENCERA de cada tècnic afectat (no només aquest model → sense solapaments). Done intactes."""
    from fhort.planning.plan_service import assign_model
    if not Model.objects.filter(pk=model_id).exists():
        return Response({'error': 'Model no trobat.'}, status=status.HTTP_404_NOT_FOUND)
    assignee_id = request.data.get('assignee_id')
    if not assignee_id:
        return Response({'error': 'assignee_id requerit.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        out = assign_model(model_id=model_id, assignee_id=assignee_id,
                           task_ids=request.data.get('task_ids'))
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(out, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_DefineTasks])
def unassign_model_view(request, model_id):
    """POST /api/v1/models/<model_id>/unassign/
    Treu el tècnic i buida planned_* de les tasques no-Done del model → torna a Pendents i
    recalcula la cua dels tècnics afectats. Done intactes."""
    from fhort.planning.plan_service import unassign_model
    if not Model.objects.filter(pk=model_id).exists():
        return Response({'error': 'Model no trobat.'}, status=status.HTTP_404_NOT_FOUND)
    try:
        out = unassign_model(model_id=model_id)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(out, status=status.HTTP_200_OK)


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
    # Enforcement Opció A: arrencar una tasca (→InProgress) exigeix execute_tasks (ja garantit per
    # _ExecuteTasks) I que el task_type sigui a l'allow-list de qui executa. Admin = bypass.
    if to_status == 'InProgress' and \
            task.task_type.code not in get_allowed_task_types(request.user):
        return Response(
            {'error': f"No tens permès executar el tipus de tasca '{task.task_type.code}'."},
            status=http_status.HTTP_403_FORBIDDEN)
    try:
        result = transition_task(task, to_status, profile)
    except TransitionError as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    return Response(result, status=http_status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_ExecuteTasks])
def claim_task_view(request, pk):
    """POST /api/v1/model-task-items/<pk>/claim/   (sense body rellevant)

    Self-claim entre tècnics (handoff §6): qui pot EXECUTAR una tasca pot fer-se-la SEVA, encara
    que avui sigui d'un altre tècnic. És una porta NOVA i acotada — NO afluixa el PATCH genèric
    (segueix gated define_tasks per a la planificació massiva) ni l'scope de llista (les cues
    personals segueixen scopades). Mirall de transition_task_view (mateix estil de la casa:
    view de funció + _ExecuteTasks + profile de request.user).

    - Obté la tasca per pk DIRECTAMENT (NO via get_queryset() scopat): el dashboard del model és
      transparent (decisió Agus) i el claim opera sobre el model sencer; el scope de llista
      amagaria la tasca d'altri i tornaria un 404 fals.
    - GUARD allow-list: el task_type ha de ser executable per qui reclama (admin = bypass dins
      get_allowed_task_types). Mateix patró que la validació InProgress de transition_task_view.
    - SELF-ONLY: assignee = el profile de request.user SEMPRE; MAI llegeix cap assignee del body
      (a diferència del PATCH genèric, no es pot assignar a un tercer).
    - Idempotent: si ja és teva, no-op (retorna-la tal qual, sense recompute).
    - NO toca status (claim = fer-la meva; el Play/transition el dispara el front DESPRÉS, P3).
    - Reassignació real (old != new) → dispara la MATEIXA cascada que perform_update
      (cleanup_queue_order + recompute_for_technicians dels dos tècnics); no es duplica lògica.
    """
    from .models import ModelTask
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil en aquest tenant.'},
                        status=http_status.HTTP_403_FORBIDDEN)
    try:
        task = ModelTask.objects.select_related('task_type').get(pk=pk)
    except ModelTask.DoesNotExist:
        return Response({'error': 'ModelTask no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)
    # GUARD allow-list: no pots agafar una tasca d'un tipus que no executes (admin = bypass).
    if task.task_type.code not in get_allowed_task_types(request.user):
        return Response(
            {'error': f"No pots agafar una tasca del tipus '{task.task_type.code}' "
                      f"(no és a la teva allow-list d'execució)."},
            status=http_status.HTTP_403_FORBIDDEN)
    old_assignee_id = task.assignee_id
    # Idempotent: ja és teva → no-op (cap reassignació, cap recompute).
    if old_assignee_id == profile.id:
        return Response(ModelTaskSerializer(task).data, status=http_status.HTTP_200_OK)
    # Self-claim: SEMPRE a mi mateix. Mai un tercer.
    task.assignee = profile
    task.save(update_fields=['assignee', 'updated_at'])
    # Mateixa cascada que ModelTaskViewSet.perform_update: old != new → neteja l'ordre manual i
    # recalcula la cua SENCERA dels DOS tècnics. Reusem el servei de planificació (no dupliquem).
    from fhort.planning.plan_service import recompute_for_technicians, cleanup_queue_order
    cleanup_queue_order([old_assignee_id, profile.id], [task.model_id])
    recompute_for_technicians([old_assignee_id, profile.id])
    return Response(ModelTaskSerializer(task).data, status=http_status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_ExecuteTasks])
def open_model_task_view(request, model_id):
    """POST /api/v1/models/<model_id>/open-task/  Body: {"code": "pom"}

    PORTA-MENÚ (zoom-in): obre una tasca CONCRETA del model des del menú, encara que NO estigui
    assignada al tècnic actual. Orquestra (sense lògica nova) els camins ja vius:
      1. CREA-si-falta la ModelTask del tipus `code` (idempotent per (model, task_type), igual que
         define-tasks: order al final + snapshot d'estimació).
      2. La posa En curs reusant `transition_task` (auto-assign + timer + exclusió un-InProgress).
         Si ja és En curs d'un altre tècnic → la fa SEVA (claim, sense re-transicionar). Si ja és
         meva i En curs → no-op.
    Retorna {task_id, code, created, status} perquè el front navegui a l'eina amb el task_id.
    """
    code = (request.data or {}).get('code')
    if not code:
        return Response({'error': 'Cal el code del tipus de tasca.'}, status=http_status.HTTP_400_BAD_REQUEST)
    try:
        model = Model.objects.get(pk=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)
    try:
        tt = TaskType.objects.get(code=code, active=True)
    except TaskType.DoesNotExist:
        return Response({'error': f"Tipus de tasca '{code}' no trobat o inactiu."}, status=http_status.HTTP_404_NOT_FOUND)
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil en aquest tenant.', 'code': 'no_profile'},
                        status=http_status.HTTP_403_FORBIDDEN)
    # GUARD allow-list: només pots obrir un tipus que executes (admin = bypass) — igual que claim.
    # `code` discriminant (S03b · P6, D10): el menú de fitxa ha de distingir "no tens aquest
    # tipus a l'allow-list" (→ ofereix obrir en consulta) de qualsevol altre 403 (bloqueig dur).
    # Sense això, el frontend hauria de fer match sobre el text del missatge. Additiu: cap
    # consumidor existent llegeix aquesta clau.
    if code not in get_allowed_task_types(request.user):
        return Response({'error': f"No pots obrir una tasca del tipus '{code}' (no és a la teva allow-list).",
                         'code': 'task_type_not_allowed'},
                        status=http_status.HTTP_403_FORBIDDEN)
    # 1. Crea-si-falta (mirall de define_model_tasks_view). La canònica és la prevista.
    task = ModelTask.objects.filter(model=model, task_type=tt, origen='prevista').first()
    created = False
    if task is None:
        order = ModelTask.objects.filter(model=model).count()
        est = lookup_estimated_minutes(model, tt)
        task = ModelTask.objects.create(model=model, task_type=tt, order=order,
                                        status='Pending', origen='prevista',
                                        estimated_minutes=est)
        created = True
    # 2. En curs (reusa transition_task) o claim si ja és En curs d'un altre.
    if task.status != 'InProgress':
        try:
            transition_task(task, 'InProgress', profile)
        except TransitionError as e:
            return Response({'error': str(e)}, status=http_status.HTTP_409_CONFLICT)
    elif task.assignee_id != profile.id:
        old_assignee_id = task.assignee_id
        task.assignee = profile
        task.save(update_fields=['assignee', 'updated_at'])
        from fhort.planning.plan_service import recompute_for_technicians, cleanup_queue_order
        cleanup_queue_order([old_assignee_id, profile.id], [task.model_id])
        recompute_for_technicians([old_assignee_id, profile.id])
    task.refresh_from_db()

    # LLEI "l'inici desplaça": iniciar una tasca reancora el model al present i desplaça la cua
    # del tècnic. El recompute va DESPRÉS del refresh (transition_task pot auto-assignar l'assignee)
    # i FORA del try/except de la transició. L'assignee es llegeix post-refresh. La branca claim
    # (elif) ja ha recomputat per als dos tècnics; aquí es cobreix el cas Pending→InProgress.
    if task.assignee_id:
        from fhort.planning.plan_service import recompute_for_technicians
        recompute_for_technicians([task.assignee_id])
        task.refresh_from_db()

    # Sprint Y — context de sessió de fitting: la convocatòria (contenidor) llança aquesta tasca de
    # presa de mesures. Opcional i additiu: sense `fitting_session_id`, el camí del check esporàdic
    # queda idèntic. Amb ell: valida pertinença al model, escriu el FK (punter MUTABLE: reapunta si ja
    # en tenia un altre, decisió 4) i, si la sessió és Programada, l'obre (Programada→Oberta).
    fitting_session_id = (request.data or {}).get('fitting_session_id')
    if fitting_session_id:
        from fhort.fitting.models import FittingSession
        from fhort.fitting.services import open_session
        try:
            fs = FittingSession.objects.get(pk=fitting_session_id)
        except FittingSession.DoesNotExist:
            return Response({'error': 'Sessió de fitting no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)
        if fs.model_id != model.id:
            return Response({'error': 'La sessió de fitting no és del mateix model que la tasca.',
                             'code': 'session_model_mismatch'}, status=http_status.HTTP_400_BAD_REQUEST)
        if task.fitting_session_id != fs.id:
            task.fitting_session = fs
            task.save(update_fields=['fitting_session', 'updated_at'])
        if fs.estat == 'Programada':
            open_session(fs.id)

    # F4 — gate SUPER SUAU: informem de quins camps de config falten (font única F1), però NO bloquegem
    # l'obertura de la tasca. El Watchpoint persistent (F2/F3) ja mostra l'avís accionable; el tècnic decideix.
    from fhort.models_app.services import model_config_missing
    return Response({'task_id': task.id, 'code': code, 'created': created, 'status': task.status,
                     'missing_config': model_config_missing(model)},
                    status=http_status.HTTP_200_OK)


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
def regress_model_view(request, model_id):
    """POST /api/v1/models/<model_id>/regress/  Body: {"to_phase":"Proto","notes":"..."}
    Retrocedeix la fase (reobrir feina anterior). NOMÉS canvia fase_actual + GateEvent kind=regress."""
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil.'}, status=http_status.HTTP_403_FORBIDDEN)
    try:
        model = Model.objects.get(pk=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)
    to_phase = request.data.get('to_phase')
    if not to_phase:
        return Response({'error': 'to_phase requerit.'}, status=http_status.HTTP_400_BAD_REQUEST)
    try:
        res = regress_phase(model, to_phase, profile, request.data.get('notes'))
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


class _ScheduleFittings(HasCapability):
    required_capability = SCHEDULE_FITTINGS


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filterset_fields = ['active', 'type']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        p = HasCapability(); self.required_capability = SCHEDULE_FITTINGS
        return [p]

    def destroy(self, request, *args, **kwargs):
        # FK Production.supplier = PROTECT → si té confeccions, l'esborrat falla. 409 net (no 500).
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': "No es pot esborrar: té confeccions associades. Desactiva'l."},
                status=status.HTTP_409_CONFLICT)


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['active']
    search_fields = ['codi', 'nom']   # cercador de la pàgina Clients (codi, nom)

    def get_queryset(self):
        """Comptadors agregats en UNA sola consulta (annotate, cap N+1): ofertes presentades
        (SENT) / acceptades (ACCEPTED), comandes obertes (OPEN) i albarans. `?exclude_self=1`
        amaga el customer propi (is_self) — només la pàgina Clients l'envia; la resta de consumidors
        (selectors de client) segueixen veient-lo."""
        qs = Customer.objects.annotate(
            cnt_quotes_sent=Count('quotes', filter=Q(quotes__status='SENT'), distinct=True),
            cnt_quotes_accepted=Count('quotes', filter=Q(quotes__status='ACCEPTED'), distinct=True),
            cnt_orders_open=Count('salesorders', filter=Q(salesorders__status='OPEN'), distinct=True),
            cnt_delivery_notes=Count('deliverynotes', distinct=True),
        )
        p = self.request.query_params.get('exclude_self')
        if p and p.lower() not in ('0', 'false', ''):
            qs = qs.exclude(is_self=True)
        return qs

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        p = HasCapability(); self.required_capability = CONFIGURE
        return [p]

    def destroy(self, request, *args, **kwargs):
        # FK Model.customer = PROTECT → si té models, l'esborrat falla. 409 net (no 500).
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': "No es pot esborrar: té models associats. Desactiva'l."},
                status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=['post'], url_path='upload-logo',
            parser_classes=[MultiPartParser, FormParser])
    def upload_logo(self, request, pk=None):
        """Puja/substitueix el logo del client (TS-4c). Gated CONFIGURE via get_permissions
        (l'acció no és list/retrieve). Patró d'upload com models_app.upload_file_view."""
        customer = self.get_object()
        logo_file = request.FILES.get('logo')
        if not logo_file:
            return Response({'detail': 'logo requerit.'}, status=status.HTTP_400_BAD_REQUEST)
        if customer.logo:
            customer.logo.delete(save=False)   # neteja el fitxer anterior
        customer.logo = logo_file
        customer.save(update_fields=['logo'])
        return Response(self.get_serializer(customer, context={'request': request}).data)


class ProductionViewSet(viewsets.ReadOnlyModelViewSet):
    """Llistat/detall de confeccions. Creació i transicions via endpoints dedicats."""
    queryset = Production.objects.select_related('supplier', 'model', 'requested_by').all()
    serializer_class = ProductionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['model', 'phase', 'status', 'supplier']


@api_view(['POST'])
@permission_classes([_ScheduleFittings])
def request_production_view(request, model_id):
    """POST /api/v1/models/<model_id>/request-production/
    Body: {"phase":"Proto","supplier_id":1,"expected_at":"2026-06-15","notes":"..."}"""
    profile = getattr(request.user, 'profile', None)
    try:
        model = Model.objects.get(pk=model_id)
        supplier = Supplier.objects.get(pk=request.data['supplier_id'])
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)
    except Supplier.DoesNotExist:
        return Response({'error': 'Supplier no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)
    except KeyError:
        return Response({'error': 'supplier_id requerit.'}, status=http_status.HTTP_400_BAD_REQUEST)
    phase = request.data.get('phase')
    if not phase:
        return Response({'error': 'phase requerit.'}, status=http_status.HTTP_400_BAD_REQUEST)
    # Gap C (5B): guard TOU — múltiples Productions per (model,fase) permeses (cicle de mostres),
    # però avisem si ja n'hi ha una ACTIVA (Requested/InProgress) al mateix supplier+fase.
    dup_actiu = Production.objects.filter(
        model=model, phase=phase, supplier=supplier,
        status__in=['Requested', 'InProgress']).exists()
    try:
        p = request_production(model, phase, supplier, profile,
                               expected_at=request.data.get('expected_at'),
                               notes=request.data.get('notes'))
    except ProductionError as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    data = ProductionSerializer(p).data
    data['warning'] = ('Ja hi havia un enviament actiu per a aquesta fase i proveïdor.'
                       if dup_actiu else None)
    return Response(data, status=http_status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([_ScheduleFittings])
def production_status_view(request, pk):
    """POST /api/v1/productions/<pk>/status/  Body: {"status":"Delivered"}"""
    try:
        prod = Production.objects.get(pk=pk)
    except Production.DoesNotExist:
        return Response({'error': 'Production no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)
    new_status = request.data.get('status')
    if not new_status:
        return Response({'error': 'status requerit.'}, status=http_status.HTTP_400_BAD_REQUEST)
    try:
        prod = set_production_status(prod, new_status)
    except ProductionError as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    return Response(ProductionSerializer(prod).data, status=http_status.HTTP_200_OK)


class _Configure(HasCapability):
    required_capability = CONFIGURE


class GarmentTypeItemViewSet(viewsets.ModelViewSet):
    # B3b: select_related dels FK de completesa (ruleset/talla base) per evitar N+1 a la graella.
    # S03c · C2.1: `poms_count` feia un `.count()` per fila (N+1: 57 items = 57 queries) i
    # `fitxers_count` no existia. Els dos passen a ser anotacions.
    #
    # `distinct=True` NO és cosmètic: `pom_maps` i `fitxers` són dues relacions multivaluades
    # i els seus LEFT JOIN es multipliquen entre si (un item amb 3 POMs i 2 fitxers donaria
    # poms_count=6 i fitxers_count=6). Amb `distinct` cada Count compta files úniques.
    #
    # `fitxers_count` compta NOMÉS `is_current=True`: en un Finder, "fitxers" és el que
    # l'usuari veu a la carpeta, no la suma de totes les versions històriques de cada cadena.
    #
    # `order_by` explícit i idèntic al Meta.ordering: `annotate()` afegeix GROUP BY i Django
    # descarta l'ordenació per defecte a les queries agregades (el SQL en perdia l'ORDER BY).
    # Sense això, la paginació d'aquest endpoint deixava de ser determinista.
    queryset = (GarmentTypeItem.objects
                .select_related('garment_type', 'grading_rule_set', 'base_size_definition')
                .annotate(
                    poms_count=Count('pom_maps', distinct=True),
                    fitxers_count=Count('fitxers', filter=Q(fitxers__is_current=True),
                                        distinct=True),
                )
                .order_by('garment_type', 'complexity_order', 'code'))
    serializer_class = GarmentTypeItemSerializer
    # S03c · C2.2 — cerca de text per al Finder: abans no n'hi havia cap (taula #5).
    # `code` i `name` són els únics camps presentables del model: no en té cap altre de nom
    # (les etiquetes i18n viuen a GarmentType, no a l'item).
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['garment_type', 'active']
    search_fields = ['code', 'name']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        p = HasCapability(); self.required_capability = CONFIGURE
        return [p]


class TaskTimeEstimateViewSet(viewsets.ModelViewSet):
    queryset = TaskTimeEstimate.objects.select_related('garment_type_item', 'task_type').all()
    serializer_class = TaskTimeEstimateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['garment_type_item', 'task_type']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        p = HasCapability(); self.required_capability = CONFIGURE
        return [p]

# Sprint B (motor): plan/compute + preview + apply + snapshots s'han mogut a
# fhort/planning/views.py (motor determinista sobre el calendari laboral).
# El plan/compute per-model-en-sèrie (Sprint H, services_h.py) queda jubilat.


# ── Sprint M2 — Anàlisi de temps (rollup task_type→fase + arbre drill-down) ──────────────────
# El motor de temps (Welford) viu a nivell de cel·la (garment_type_item × task_type). Aquí
# s'AGREGA cap amunt per fase (TaskType.fase), de manera consultiva. Cap escriptura del motor.

class _ViewTeamTasks(HasCapability):
    required_capability = VIEW_TEAM_TASKS


def _cell_effective_and_maturity(cell):
    """(minuts|None, maduresa) d'una cel·la TaskTimeEstimate. maduresa ∈ empiric|seed|none.
    Mirall de services_i.effective_minutes però retornant també l'origen (per a la cobertura)."""
    from .services_i import WELFORD_MIN_SAMPLES
    if cell.n >= WELFORD_MIN_SAMPLES and cell.mean_minutes > 0:
        emp = int(round(cell.mean_minutes))
        if emp > 0:
            return emp, 'empiric'
    seed = cell.estimated_minutes
    if seed and seed > 0:
        return int(seed), 'seed'
    return None, 'none'


# Acumulador genèric d'un node (fase, task_type, …): mitjana ponderada per n + cobertura.
def _acc_factory():
    return {'cells_total': 0, 'cells_empiric': 0, 'cells_seed': 0, 'cells_none': 0,
            'n_total': 0, '_wsum': 0.0, '_w': 0, '_vsum': 0, '_vcount': 0}


def _acc_add(a, cell):
    """Acumula una cel·la TaskTimeEstimate al node. Pes = n (empíric) | 1 (seed)."""
    a['cells_total'] += 1
    a['n_total'] += cell.n
    val, mat = _cell_effective_and_maturity(cell)
    a['cells_' + mat] += 1
    if val is not None:
        w = cell.n if mat == 'empiric' else 1
        a['_wsum'] += val * w
        a['_w'] += w
        a['_vsum'] += val
        a['_vcount'] += 1


def _acc_metrics(a):
    """Projecta un acumulador a minuts ponderats + mitjana simple + maduresa + cobertura."""
    return {
        'minutes': int(round(a['_wsum'] / a['_w'])) if a['_w'] > 0 else None,
        'avg_minutes': int(round(a['_vsum'] / a['_vcount'])) if a['_vcount'] else None,
        'maturity': 'empiric' if a['cells_empiric'] > 0 else ('seed' if a['cells_seed'] > 0 else 'empty'),
        'cells_total': a['cells_total'], 'cells_empiric': a['cells_empiric'],
        'cells_seed': a['cells_seed'], 'cells_none': a['cells_none'], 'n_total': a['n_total'],
    }


def _phase_rollup(cells):
    """Rollup task_type→fase sobre un iterable de TaskTimeEstimate (amb task_type carregat).
    Retorna {fase: acumulador}."""
    from collections import defaultdict
    acc = defaultdict(_acc_factory)
    for c in cells:
        _acc_add(acc[c.task_type.fase], c)
    return acc


def _phase_summary(fase, a):
    """Projecta l'acumulador d'una fase a la forma servible (None-safe)."""
    return {'fase': fase, **_acc_metrics(a if a else _acc_factory())}


@api_view(['GET'])
@permission_classes([_ViewTeamTasks])
def time_by_phase_view(request):
    """GET /api/v1/time-analysis/by-phase/ — temps estadístic agregat per fase (rollup
    task_type→fase). Inclou TOTES les fases del catàleg; les buides surten amb maturity='empty'.
    Gated view_team_tasks (manager/admin)."""
    from .services_i import WELFORD_MIN_SAMPLES
    cells = TaskTimeEstimate.objects.select_related('task_type').all()
    acc = _phase_rollup(cells)
    phases = [_phase_summary(fase, acc.get(fase)) for fase, _label in TaskType.FASE_CHOICES]
    return Response({'phases': phases, 'welford_min_samples': WELFORD_MIN_SAMPLES})


def _cell_item_payload(c):
    """Projecta una cel·la a la fulla de l'arbre: estimat (seed) vs real (mean) vs n vs desviació."""
    val, mat = _cell_effective_and_maturity(c)
    seed = int(c.estimated_minutes) if (c.estimated_minutes and c.estimated_minutes > 0) else None
    mean = int(round(c.mean_minutes)) if (c.n > 0 and c.mean_minutes > 0) else None
    item = c.garment_type_item
    gt = getattr(item, 'garment_type', None) if item else None
    gt_nom = ''
    if gt:
        gt_nom = (gt.nom_client or gt.nom_ca or gt.nom_es or gt.nom_en or gt.codi_client
                  or f'#{gt.id}')
    return {
        'garment_type_item_id': c.garment_type_item_id,
        'item_nom': getattr(item, 'name', '') if item else '',
        'garment_type_id': getattr(gt, 'id', None),
        'garment_type_nom': gt_nom,
        'task_type_code': c.task_type.code,
        'estimated_minutes': seed,
        'mean_minutes': mean,
        'effective_minutes': val,
        'n': c.n,
        'desviacio_min': (mean - seed) if (mean is not None and seed is not None) else None,
        'desviacio_pct': int(round((mean - seed) / seed * 100)) if (mean is not None and seed) else None,
        'maturity': mat,
    }


@api_view(['GET'])
@permission_classes([_ViewTeamTasks])
def time_tree_view(request):
    """GET /api/v1/time-analysis/tree/ — arbre consultiu fase→task_type→item amb temps estimat
    (seed) vs real (mean) vs n vs desviació vs maduresa per cel·la. Reusa el rollup ponderat del
    commit 1 a cada node. Filtres opcionals: ?fase= ?task_type=(code) ?garment_type=
    ?garment_type_item=. Gated view_team_tasks."""
    from .services_i import WELFORD_MIN_SAMPLES
    qs = TaskTimeEstimate.objects.select_related(
        'task_type', 'garment_type_item', 'garment_type_item__garment_type').all()
    fase = request.query_params.get('fase')
    if fase:
        qs = qs.filter(task_type__fase=fase)
    tt = request.query_params.get('task_type')
    if tt:
        qs = qs.filter(task_type__code=tt)
    gt = request.query_params.get('garment_type')
    if gt:
        qs = qs.filter(garment_type_item__garment_type_id=gt)
    gti = request.query_params.get('garment_type_item')
    if gti:
        qs = qs.filter(garment_type_item_id=gti)

    phases = {}   # fase → {'acc', 'tts': {tt_id: {'code','name','fase','acc','items'}}}
    for c in qs:
        ph = phases.setdefault(c.task_type.fase, {'acc': _acc_factory(), 'tts': {}})
        _acc_add(ph['acc'], c)
        node = ph['tts'].setdefault(c.task_type_id, {
            'code': c.task_type.code, 'name': c.task_type.name, 'fase': c.task_type.fase,
            'acc': _acc_factory(), 'items': []})
        _acc_add(node['acc'], c)
        node['items'].append(_cell_item_payload(c))

    out = []
    for fase, _label in TaskType.FASE_CHOICES:
        ph = phases.get(fase)
        if not ph:
            continue   # fase sense cel·les (després de filtrar) → fora de l'arbre
        tts = []
        for node in ph['tts'].values():
            node['items'].sort(key=lambda x: (x['item_nom'] or ''))
            tts.append({'code': node['code'], 'name': node['name'], 'fase': node['fase'],
                        **_acc_metrics(node['acc']), 'items': node['items']})
        tts.sort(key=lambda x: x['code'])
        out.append({'fase': fase, **_acc_metrics(ph['acc']), 'task_types': tts})
    return Response({'phases': out, 'welford_min_samples': WELFORD_MIN_SAMPLES})


@api_view(['POST'])
@permission_classes([_DefineTasks])
def time_set_estimate_view(request):
    """POST /api/v1/time-analysis/set-estimate/ — captura-PM (graó 4 de la cascada de temps):
    fixa el seed (estimated_minutes) d'una cel·la (garment_type_item × task_type), creant-la si no
    existeix. NO toca mai l'empíric (n/mean/m2). Body: {garment_type_item, task_type(code), minutes}.
    Gated define_tasks. Retorna la fulla actualitzada (mateixa forma que l'arbre)."""
    gti = request.data.get('garment_type_item')
    code = request.data.get('task_type')
    minutes = request.data.get('minutes')
    if not gti or not code:
        return Response({'error': 'garment_type_item i task_type requerits.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return Response({'error': 'minutes ha de ser un enter.'}, status=http_status.HTTP_400_BAD_REQUEST)
    if minutes <= 0:
        return Response({'error': 'minutes ha de ser > 0.'}, status=http_status.HTTP_400_BAD_REQUEST)
    try:
        tt = TaskType.objects.get(code=code)
    except TaskType.DoesNotExist:
        return Response({'error': 'task_type no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)
    if not GarmentTypeItem.objects.filter(pk=gti).exists():
        return Response({'error': 'garment_type_item no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)
    cell, _created = TaskTimeEstimate.objects.get_or_create(garment_type_item_id=gti, task_type=tt)
    cell.estimated_minutes = minutes
    cell.save(update_fields=['estimated_minutes'])   # NOMÉS el seed; mai n/mean/m2
    cell = TaskTimeEstimate.objects.select_related(
        'task_type', 'garment_type_item', 'garment_type_item__garment_type').get(pk=cell.pk)
    return Response(_cell_item_payload(cell), status=http_status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_DefineTasks])
def time_capture_seed_view(request):
    """POST /api/v1/time-analysis/capture-seed/ — captura conscient del PM (graó 3 de la cascada):
    fixa una LLAVOR de tenant per task (TimeSeed scope='task', origen='CAPTURA') quan la
    planificació no ha pogut estimar una tasca (needs_estimate). Desbloqueja TOTES les tasques
    d'aquell task sense cel·la ni empíric. Body: {task_code, minuts}. Gated define_tasks."""
    code = request.data.get('task_code')
    minuts = request.data.get('minuts')
    if not code:
        return Response({'error': 'task_code requerit.'}, status=http_status.HTTP_400_BAD_REQUEST)
    try:
        minuts = int(minuts)
    except (TypeError, ValueError):
        return Response({'error': 'minuts ha de ser un enter.'}, status=http_status.HTTP_400_BAD_REQUEST)
    if minuts <= 0:
        return Response({'error': 'minuts ha de ser > 0.'}, status=http_status.HTTP_400_BAD_REQUEST)
    if not TaskType.objects.filter(code=code).exists():
        return Response({'error': 'task_type no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)
    profile = getattr(request.user, 'profile', None)
    seed, _ = TimeSeed.objects.update_or_create(
        scope='task', key=code,
        defaults={'minuts': minuts, 'origen': 'CAPTURA', 'updated_by': profile})
    return Response({'ok': True, 'task_code': code, 'minuts': seed.minuts, 'origen': seed.origen},
                    status=http_status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([_ViewTeamTasks])
def time_by_model_view(request):
    """GET /api/v1/time-analysis/by-model/ — anàlisi de temps amb el MODEL com a eix.

    L'eix tècnic (TaskTimeEstimate, `garment_type_item × task_type`) NO té dimensió model
    (`unique_together=[('garment_type_item','task_type')]`); per tant el "per model" NO es pot
    derivar de l'arbre `tree`/`by-phase`. La dimensió model viu a `ModelTask.model` (snapshot
    `estimated_minutes` per tasca) + `TimerEntrada.minuts` (real consolidat). Aquesta vista
    reusa la MATEIXA mètrica est/real/n/desviació/maduresa de l'arbre, agrupant
    model → fase → task_type (cada model té com a molt una ModelTask per task_type:
    `unique_together=[('model','task_type')]`, doncs el task_type és la fulla).

    Filtres opcionals: ?model=id ?fase=. Gated view_team_tasks (com la resta d'anàlisi de temps)."""
    from django.db.models import Sum
    from .models import TimerEntrada
    qs = ModelTask.objects.select_related('task_type', 'model').all()
    model_id = request.query_params.get('model')
    if model_id:
        qs = qs.filter(model_id=model_id)
    fase = request.query_params.get('fase')
    if fase:
        qs = qs.filter(task_type__fase=fase)
    # Real consolidat per ModelTask = Sum(timers.minuts); timers oberts (minuts NULL) fora (B1-a).
    # Mateixa regla que l'albarà (models_app/views.py) i el helper canònic _real_minutes. 1 query.
    real_per_task = {r['model_task_id']: (r['s'] or 0) for r in (
        TimerEntrada.objects.filter(model_task__in=qs)
        .values('model_task_id').annotate(s=Sum('minuts')))}

    fase_order = {f: i for i, (f, _l) in enumerate(TaskType.FASE_CHOICES)}
    models = {}   # model_id → {label, nom, est, real, n, fases: {fase: {...}}}
    for tk in qs:
        m = models.setdefault(tk.model_id, {
            'model_id': tk.model_id, 'label': tk.model.codi_intern,
            'nom': tk.model.nom_prenda or '', 'est': 0, 'real': 0, 'n': 0, 'fases': {}})
        ph = m['fases'].setdefault(tk.task_type.fase, {
            'fase': tk.task_type.fase, 'est': 0, 'real': 0, 'n': 0, 'tasks': []})
        est = int(tk.estimated_minutes or 0)
        real = int(real_per_task.get(tk.id, 0))
        ph['tasks'].append({
            'task_type_code': tk.task_type.code, 'task_type_name': tk.task_type.name,
            'status': tk.status,
            'estimated_minutes': est or None, 'real_minutes': real or None,
            'desviacio_min': (real - est) if (est and real) else None,
            'desviacio_pct': int(round((real - est) / est * 100)) if (est and real) else None,
            'maturity': 'empiric' if real else ('seed' if est else 'none'),
        })
        for node in (m, ph):
            node['est'] += est
            node['real'] += real
            node['n'] += 1

    out = []
    for m in sorted(models.values(), key=lambda x: x['label']):
        fases = sorted(m['fases'].values(), key=lambda x: fase_order.get(x['fase'], 99))
        for ph in fases:
            ph['tasks'].sort(key=lambda x: x['task_type_code'])
        out.append({'model_id': m['model_id'], 'label': m['label'], 'nom': m['nom'],
                    'est': m['est'], 'real': m['real'], 'n': m['n'], 'fases': fases})
    return Response({'models': out})
