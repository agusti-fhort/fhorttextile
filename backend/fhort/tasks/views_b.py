from rest_framework import viewsets, status
from rest_framework import status as http_status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, ProtectedError

from rest_framework.exceptions import ValidationError
from fhort.accounts.capabilities import (HasCapability, DEFINE_TASKS, EXECUTE_TASKS,
                                         CLOSE_GATES, SCHEDULE_FITTINGS, CONFIGURE,
                                         get_allowed_task_types, scope_model_task_queryset)
from fhort.models_app.models import Model
from .models import (TaskType, ModelTask, Supplier, Production,
                     GarmentTypeItem, TaskTimeEstimate, TaskTransition, Customer)
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

    def destroy(self, request, *args, **kwargs):
        # FK ModelTask.task_type = PROTECT → si el tipus té instàncies, l'esborrat falla.
        # Retornem 409 net (en lloc d'un 500 cru) perquè el front en mostri el missatge.
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': "No es pot esborrar: hi ha tasques que l'usen. Desactiva'l en lloc d'esborrar."},
                status=status.HTTP_409_CONFLICT)


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
    existing = set(ModelTask.objects.filter(model_id=model_id, task_type_id__in=ids)
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
                                      estimated_minutes=est)
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
        return Response({'error': 'Usuari sense perfil en aquest tenant.'}, status=http_status.HTTP_403_FORBIDDEN)
    # GUARD allow-list: només pots obrir un tipus que executes (admin = bypass) — igual que claim.
    if code not in get_allowed_task_types(request.user):
        return Response({'error': f"No pots obrir una tasca del tipus '{code}' (no és a la teva allow-list)."},
                        status=http_status.HTTP_403_FORBIDDEN)
    # 1. Crea-si-falta (mirall de define_model_tasks_view).
    task = ModelTask.objects.filter(model=model, task_type=tt).first()
    created = False
    if task is None:
        order = ModelTask.objects.filter(model=model).count()
        est = lookup_estimated_minutes(model, tt)
        task = ModelTask.objects.create(model=model, task_type=tt, order=order,
                                        status='Pending', estimated_minutes=est)
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
    return Response({'task_id': task.id, 'code': code, 'created': created, 'status': task.status},
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
    filterset_fields = ['active']

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
    queryset = GarmentTypeItem.objects.select_related(
        'garment_type', 'grading_rule_set', 'base_size_definition').all()
    serializer_class = GarmentTypeItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['garment_type', 'active']

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
