from rest_framework import viewsets, status
from rest_framework import status as http_status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Count, Q, ProtectedError, Min, OuterRef, Subquery
from django.db.models.functions import Coalesce

from rest_framework.exceptions import ValidationError
from fhort.accounts.capabilities import (HasCapability, DEFINE_TASKS, EXECUTE_TASKS,
                                         CLOSE_GATES, SCHEDULE_FITTINGS, CONFIGURE, VIEW_TEAM_TASKS,
                                         get_allowed_task_types, scope_model_task_queryset)
from fhort.models_app.models import Model
from .models import (TaskType, ModelTask, Supplier, Production,
                     GarmentTypeItem, GarmentTypeItemPart, TaskTimeEstimate,
                     TaskTransition, Customer, TimeSeed, Ronda)
from .serializers_b import (TaskTypeSerializer, ModelTaskSerializer,
                            SupplierSerializer, ProductionSerializer,
                            GarmentTypeItemSerializer, TaskTimeEstimateSerializer,
                            CustomerSerializer)
from .services_c import (transition_task, traspassa_tram, TransitionError,
                         rectification_count, te_paret_albara, AUTO_CONSULTA)
from .services_d import (advance_phase_gate, advance_phases_chain, regress_phase,
                         model_ready_for_gate, GateError)
from .services_e import (request_production, set_production_status,
                         ProductionError, has_delivered_production)
from .services_g import lookup_estimated_minutes
from .services_r import ronda_del_gest, tasca_vigent


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

    def destroy(self, request, *args, **kwargs):
        """C3 — esborrat NOMÉS de tasques Pending (les altres → 409, per no destruir història:
        timers/transicions pengen en CASCADE d'una tasca ja treballada). Gate DEFINE_TASKS i
        row-level scope ja aplicats (get_permissions/get_queryset). Si la Pending estava
        assignada/planificada, es replica la cascada d'unassign (recompute + cleanup_queue_order
        + neteja predicted_*) reutilitzant plan_service, perquè la cua no quedi incoherent."""
        instance = self.get_object()
        if instance.status != 'Pending':
            return Response(
                {'error': 'Només es poden esborrar tasques pendents (Pending). Una tasca '
                          'iniciada, pausada o feta conserva la seva història i no s\'esborra.'},
                status=status.HTTP_409_CONFLICT)
        model_id, assignee_id = instance.model_id, instance.assignee_id
        instance.delete()
        if assignee_id is not None:
            from fhort.planning.plan_service import cleanup_after_pending_delete
            cleanup_after_pending_delete(model_id=model_id, assignee_id=assignee_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

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
    # C4 — FONT ÚNICA D'ORDRE: el pla materialitzat (min planned_start de tasques vives, fallback
    # a qualsevol tasca). Ja NO s'ordena per activitat: l'activitat (InProgress/Paused) és un eix
    # ORTOGONAL (kanban_state) per ressaltar/enfocar, no per reordenar. Desempat estable per codi.
    _DEFAULT_ORDER = (Coalesce('plan_start', 'plan_start_all').asc(nulls_last=True), 'model__codi_intern')

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
          Filtres de model (font única = ModelFilter canònic, C1; additius AND, invàlids
          ignorats silenciosament):
            ?temporada= (SS/FW/CO/SP)  ?estat= (Nou/EnCurs/EnRevisio/Tancat)
            ?fase_actual= (Proto/Fit/SizeSet/PP/TOP)  ?garment_type=<id>  ?any=<int>
            ?prioritat=<int>  ?responsable=<userprofile_id> (DIRECTOR del model)
            ?assignee=me | <userprofile_id> (tècnic amb ≥1 tasca assignada — abans era `responsable`)
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

        # --- C1: FONT ÚNICA DE FILTRES DE MODEL ---
        # Deixa de reflectir el filterset del Model list a mà: aplica el MATEIX ModelFilter
        # canònic (fase_actual/estat/garment_type/any/prioritat/customer/collection/
        # data_objectiu + responsable=DIRECTOR + assignee=tècnic) sobre Model i acota el
        # queryset de tasques als seus ids. `search`, `all` i `ordering` són propis del board
        # (no formen part del contracte de filtres de model) i es resolen a part.
        # NB: `.qs` d'un ModelFilter instanciat directament és lenient (valors invàlids
        # s'ignoren, no peta) — es preserva el comportament històric de by_model.
        from fhort.models_app.views import ModelFilter
        models_qs = ModelFilter(qp, queryset=Model.objects.all(), request=request).qs
        # ── M3 · FASE 4 · FIT-9 — EL BOARD ÉS EL TAULER DELS MODELS VIUS ────────────────────
        # Un model `acabat` o `jubilat` SURT del board: és exactament el que volen dir aquells
        # dos estats («fora del tauler actiu, consultable» i «històric»). No s'amaga cap dada —
        # la fitxa del model segueix sencera i les llistes els ensenyen amb filtre explícit—,
        # el que es treu és el SOROLL d'una columna de feina acabada que no torna.
        #
        # ⚠️ I ES POT DEMANAR EXPLÍCITAMENT: `?estat=acabat` (o `jubilat`) els torna a ensenyar.
        # L'exclusió és el DEFAULT, no una paret: qui pregunta per ells, els vol. Mateix criteri
        # que `?inclou=` del catàleg («el que està EN ÚS no s'amaga mai»).
        # Un `?estat=` que NO és cap de les choices s'ignora com l'ignora el filtre (regla
        # lenient de C1), i llavors l'exclusió **torna a manar**: si no, un valor mal escrit
        # obriria el board als acabats sense que ningú ho hagués demanat.
        if (qp.get('estat') or '').strip() not in dict(Model.ESTAT_CHOICES):
            models_qs = models_qs.exclude(estat__in=[Model.ESTAT_ACABAT, Model.ESTAT_JUBILAT])
        qs = qs.filter(model_id__in=models_qs.values('id'))

        # M3 · FASE 4 + CODA — LA VOLTA VIGENT DEL MODEL, per files i sense N+1. Ja no és
        # només informativa: **`kanban_state` en depèn**. La 4a columna és ara un FET D'ENTREGA
        # (darrera volta tancada AMB entrega i cap d'oberta), i això no es pot derivar dels
        # comptadors de tasques — cal saber si aquella volta es va ENVIAR. La fila segueix
        # portant-ho també cap a fora (`ronda: {seq, estat}`), que és el que deixa que la
        # targeta digui «R3 entregada» i no una paraula que valgui per a tres casos diferents.
        ultima_ronda = Ronda.objects.filter(model_id=OuterRef('model_id')).order_by('-seq')

        agg = (qs.values(
                   'model_id', 'model__codi_intern', 'model__nom_prenda', 'model__fase_actual',
                   'model__estat', 'model__temporada', 'model__prioritat', 'model__data_objectiu',
                   'model__responsable_id', 'model__any', 'model__data_entrada', 'model__data_tancament',
                   'model__reanchored_by_start',
               )
               .annotate(
                   pending=Count('id', filter=Q(status='Pending')),
                   paused=Count('id', filter=Q(status='Paused')),
                   in_progress=Count('id', filter=Q(status='InProgress')),
                   done=Count('id', filter=Q(status='Done')),
                   # C4 — posició al PLA MATERIALITZAT: min(planned_start) de les tasques vives
                   # del model (fallback a qualsevol tasca, per als models tot-Done amb all=true).
                   plan_start=Min('planned_start', filter=~Q(status='Done')),
                   plan_start_all=Min('planned_start'),
                   # M3 · la darrera volta del model (seq, si és tancada i si té entrega). Tres
                   # subqueries d'una fila cadascuna: el board segueix sent una sola consulta.
                   ronda_seq=Subquery(ultima_ronda.values('seq')[:1]),
                   ronda_tancada_el=Subquery(ultima_ronda.values('tancada_el')[:1]),
                   ronda_entrega_id=Subquery(ultima_ronda.values('entrega__id')[:1]),
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

        # C4a — NOMÉS ELS PLANIFICATS EXISTEIXEN al Board: un model sense cap ModelTask amb
        # planned_start encara no ha entrat al pla → fora (entra quan se li assigna/inicia tasca).
        agg = agg.filter(plan_start_all__isnull=False)

        if qp.get('all') != 'true':
            # Per defecte només models amb alguna tasca no-Done (HAVING sobre els comptadors)…
            #
            # M3 · CODA — …**i els que tenen una VOLTA OBERTA**, encara que no els quedi cap
            # tasca viva. És la conseqüència directa de la llei nova: aquell model ja no cau a
            # la 4a columna sinó a les d'estat de feina, i un model classificat «pendent» que la
            # consulta per defecte amaga seria una fila que existeix a la columna i no a la
            # llista. El que el filtre vol treure és la feina ACABADA, i una volta oberta no ho és.
            agg = agg.filter(Q(pending__gt=0) | Q(paused__gt=0) | Q(in_progress__gt=0)
                             | Q(ronda_seq__isnull=False, ronda_tancada_el__isnull=True))

        def kanban_state(row):
            """Estat-kanban derivat del model (única font de veritat al backend, Sprint 5 1c).
            ∈ {pending, open, paused, done}. Ordre: **la feina viva mana sobre tota la resta**.

              open    si in_progress > 0
              paused  si paused > 0 i cap en curs
              pending si en queda alguna de pendent (i res actiu ni pausat)

            …i quan no queda cap feina viva, mana **LA VOLTA** (M3 · CODA · decisió d'Agus):

              done    la darrera volta és TANCADA i té ENTREGA (i per tant cap d'oberta)
              pending qualsevol altre cas: la volta és OBERTA, o es va tancar sense declarar
                      cap entrega

            🔒 **LA 4a COLUMNA ÉS UN FET D'ENTREGA, NO UN RECOMPTE DE TASQUES.** Fins ara hi
            queia tot el que no tenia feina viva, i això barrejava dues coses ben diferents:
            una volta ENTREGADA (feina que ja és a fora, esperant el retorn del client) i una
            volta ACABADA DE TREBALLAR PERÒ NO ENVIADA, que és feina nostra i encara ho és. La
            segona torna a les columnes d'estat de feina —el gest que falta és humà, no una
            tasca— i el senyal de que ja es pot enviar el porta el badge LLIURABLE, que existeix
            des d'F2.7 i diu exactament això.

            ✅ **L'EXCEPCIÓ PRE-LLEI JA NO HI ÉS (M5, 25/08).** Mentre la prohibició de backfill
            va durar, un model sense cap `Ronda` conservava la lectura vella (tot Done → 4a
            columna): la seva feina no podia tenir volta, i per tant tampoc entrega, i aplicar-hi
            la llei nova l'hauria empès a «pendent» per sempre per una cosa que no era seva. Era
            **autoextingible a posta**, i el retroactiu de M5 li ha donat la seva R1 a tot model
            amb feina —**població pre-llei = 0**, verificat per SQL—, o sigui que la branca ja no
            trobava ningú. S'ha retirat, i amb ella el test que la mesurava.
            """
            if row['in_progress'] > 0:
                return 'open'
            if row['paused'] > 0:
                return 'paused'
            if row['pending'] > 0:
                return 'pending'
            # ── cap feina viva: mana la volta ────────────────────────────────────────────────
            # `ronda_*` és la volta de `seq` més ALT, i per la llei «una ronda oberta per model»
            # (ratificada 24/08, `services_r.obrir_ronda`) una volta oberta només pot ser
            # aquesta: si aquesta és tancada, no n'hi ha cap d'oberta. Per això no cal una quarta
            # subconsulta per preguntar-ho.
            if row['ronda_tancada_el'] is not None and row['ronda_entrega_id'] is not None:
                return 'done'
            return 'pending'

        def ronda_estat(row):
            """L'estat de la DARRERA volta del model — les tres que la BD pot donar, i cap més.
            Són les mateixes tres que M2 ja pinta a la fitxa (§9.3 de la seva acta): una volta
            pot estar tancada SENSE entrega, i pintar-la «entregada» seria mentir a seques."""
            if row['ronda_seq'] is None:
                return None
            if row['ronda_tancada_el'] is None:
                return 'oberta'
            return 'entregada' if row['ronda_entrega_id'] is not None else 'tancada'

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
                'kanban_state': kanban_state(row),
                # Extres additius (la UI els pot etiquetar sense una segona crida):
                'prioritat': row['model__prioritat'],
                'temporada': row['model__temporada'],
                'estat': row['model__estat'],
                'data_objectiu': row['model__data_objectiu'],
                'responsable_id': row['model__responsable_id'],
                # C4d — marcador "+": el model s'ha mogut sol al pla per un inici real.
                'reanchored_by_start': row['model__reanchored_by_start'],
                # M3 · FASE 4 — la darrera volta, perquè la 4a columna pugui dir QUÈ espera.
                # `null` = aquest model no té cap volta (feina llegada): no és una omissió.
                'ronda': (None if row['ronda_seq'] is None
                          else {'seq': row['ronda_seq'], 'estat': ronda_estat(row)}),
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
        # M1-bis · FIT-4 — un extra també és un GEST DE TREBALL: si el model encara no té cap
        # volta, aquesta la fa néixer (R1). Atòmic: no pot quedar la tasca sense la seva ronda.
        with transaction.atomic():
            task = ModelTask.objects.create(
                model=model, task_type=tt, order=order, status='Pending',
                origen='ad_hoc', off_recipe=True, work_order=wo,
                ronda=ronda_del_gest(model))
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
    # M1-bis · FIT-4 — definir la feina d'un model ÉS el gest de programació, i és el primer que
    # rep un model nou. La ronda es resol UN COP per a tot el lot: totes les tasques d'aquesta
    # crida són del mateix gest i han d'anar a la mateixa volta.
    with transaction.atomic():
        ronda = ronda_del_gest(model)
        for i, t in enumerate(types):
            if t.id in existing:
                continue
            est = lookup_estimated_minutes(model, t)   # snapshot del temps estimat (None si no n'hi ha)
            mt = ModelTask.objects.create(model_id=model_id, task_type=t,
                                          order=base_order + i, status='Pending',
                                          origen='prevista', estimated_minutes=est,
                                          ronda=ronda)
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
          .select_related('model_task__task_type', 'model_task__ronda', 'by')
          .order_by('-at'))
    log = [{
        'id': tr.id,
        'task_type': tr.model_task.task_type.code,
        'from_status': tr.from_status,
        'to_status': tr.to_status,
        'by': (tr.by.nom_complet if tr.by_id else None),
        # null = gest del tècnic; slug = el guard que ha actuat. Sense això el log diria que la
        # pausa la va fer `by`, que en una auto-pausa és fals.
        'auto': tr.auto,
        # M2 · LA CARA DE FIT-8 — el rastre de la reobertura post-entrega ja s'escrivia (M1 · §6)
        # i **no sortia per cap porta**: la dada existia i no es podia llegir. `nota` no és null
        # NOMÉS quan la tasca pertany a una volta amb entrega informada
        # (`_nota_reobertura_post_entrega`), o sigui que la seva PRESÈNCIA ja és el marcador: el
        # comptador de rectificacions es compta, no es dedueix parsejant la frase.
        # `ronda_seq` l'hi acompanya per agrupar-lo per volta sense haver de llegir el text.
        'nota': tr.nota,
        'ronda_seq': tr.model_task.ronda.seq if tr.model_task.ronda_id else None,
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


# Marques d'automatisme que el CLIENT pot demanar (i només sobre →Paused). 'cron_40min' no hi és:
# el naixement d'aquella marca és el command de cron, i un navegador no l'ha de poder falsificar.
_AUTO_DEL_CLIENT = {'guard_30min'}


@api_view(['POST'])
@permission_classes([_ExecuteTasks])
def transition_task_view(request, pk):
    """POST /api/v1/model-task-items/<pk>/transition/  Body: {"to_status": "InProgress"}
    Aplica la transició. Retorna la tasca i, si escau, paused_task_id (per l'avís del front).

    Body opcional `auto`: marca del guard que provoca la transició, perquè el log no signi amb
    el nom del tècnic una cosa que ell no ha fet. NO és un camp lliure — el client només pot
    demanar els valors de `_AUTO_DEL_CLIENT`, i només per a la pausa. Qualsevol altra cosa
    s'ignora en silenci i la transició es registra com el que sembla: un gest humà."""
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
    auto = request.data.get('auto')
    if to_status != 'Paused' or auto not in _AUTO_DEL_CLIENT:
        auto = None
    try:
        result = transition_task(task, to_status, profile, auto=auto)
    except TransitionError as e:
        cos = {'error': str(e)}
        codi = getattr(e, 'code', None)
        if codi:
            cos['code'] = codi
        # F1.7 · §S-2 — la MATEIXA paret sortia amb dos codis HTTP segons la porta: 409 per
        # `open-task` i 400 per aquí. Un client que discrimini per status (i n'hi ha: ModelSheet
        # i WorkPlan miren `err.response.status`) veia dues coses diferents pel mateix motiu, i
        # D-5 penja d'aquest disparador. El conflicte d'estat és 409 a les dues portes; la resta
        # de rebuigs —transició il·legal— segueixen sent 400, que és el que són.
        return Response(cos, status=(http_status.HTTP_409_CONFLICT if codi
                                     else http_status.HTTP_400_BAD_REQUEST))
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
    # F1.5 · D-7 — el relleu tanca el tram de qui la tenia i n'obre un per a mi, amb la seva fila
    # al log (`auto='handoff'`). Aquesta porta i la branca de claim d'`open-task` fan el MATEIX:
    # dues portes, un sol relleu.
    traspassa_tram(task, profile)
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
    # 1. Crea-si-falta (mirall de define_model_tasks_view). QUINA és «la tasca del model» ho
    # decideix `tasca_vigent` i ningú més (F1.0): amb una ronda oberta, la porta ha d'obrir la
    # tasca de la RONDA, no la prevista de sota. Si no en troba cap, el que es crea segueix sent
    # una `prevista` — la ronda no es crea per aquí, es crea amb `obrir_ronda`.
    task = tasca_vigent(model, code)
    created = False
    if task is None:
        order = ModelTask.objects.filter(model=model).count()
        est = lookup_estimated_minutes(model, tt)
        # M1-bis · FIT-4 — entrar-hi i executar és el gest de treball més directe de tots.
        # ⚠️ NOMÉS quan la tasca es CREA. Si `tasca_vigent` n'ha trobat una, aquella tasca ja té
        # la ronda que li toca i moure-la seria migrar feina entre voltes: FIT-6 ho prohibeix.
        with transaction.atomic():
            task = ModelTask.objects.create(model=model, task_type=tt, order=order,
                                            status='Pending', origen='prevista',
                                            estimated_minutes=est,
                                            ronda=ronda_del_gest(model))
        created = True
    # ── J · R3 · ENTRAR NO ENDÚ NI REOBRE ────────────────────────────────────────────────────
    #
    # Aquesta porta feia DUES coses per la mera entrada, totes dues en silenci i totes dues
    # irreversibles al log:
    #   · una tasca `Done` es REOBRIA (`ALLOWED` permet `Done → InProgress` perquè la
    #     rectificació existeix com a acte), amb tram nou i rellotge reiniciat;
    #   · una tasca `InProgress` d'un ALTRE tècnic es feia SEVA (`traspassa_tram` + `assignee`).
    #     Això no és pausar-la: és PRENDRE-LA. «Pausada conserva la mà» parla de l'estat, i aquí
    #     el que canviava de mans era la feina.
    #
    # Cap de les dues és dolenta: totes dues són gestos LEGÍTIMS i es conserven senceres. El que
    # no poden ser és **l'efecte secundari de mirar**. Ara cada una exigeix que qui entra ho digui
    # (`reobrir` / `handoff`), que és el que `PLA_DE_TREBALL §6` ja demanava per al relleu —*el
    # sistema em pregunta si la reassigno, i la reassignació és condició obligada per entrar-hi*—
    # i el que la capçalera de `services_batec` ja aplicava a l'escriptura: *reobrir és un acte
    # humà, no l'efecte d'un PATCH*. Aquí és: **ni l'efecte d'una mirada**.
    #
    # 🔑 LA MÀQUINA D'ESTATS NO ES TOCA. `transition_task` i `traspassa_tram` fan exactament el
    # mateix que ahir; J governa QUAN es criden, no què fan. Sense el gest, la resposta és un 409
    # amb codi —no un 403— perquè no és una manca de permís: és una decisió que ningú no ha pres
    # encara, i el client ha de poder oferir-la (consultar o fer el gest).
    #
    # L'ORDRE DE PRECEDÈNCIA és el mateix que `caraObrirTasca` ja aplica al front i que
    # `batec_escriptura` ja aplica a l'escriptura: **l'albarà mana sobre tota la resta**. Una
    # tasca albaranada ha de dir que ho està, i no «ja està feta»: són dues converses diferents
    # i la segona amaga la primera.
    gestos = request.data or {}
    if task.status == 'Done' and not gestos.get('reobrir'):
        if te_paret_albara(task):
            return Response({'error': 'No es pot reobrir una tasca ja albaranada (albarà emès).',
                             'code': 'tasca_albaranada'}, status=http_status.HTTP_409_CONFLICT)
        return Response({'error': 'Aquesta tasca ja està feta: reobrir-la és un gest conscient.',
                         'code': 'tasca_feta', 'task_id': task.id, 'status': task.status},
                        status=http_status.HTTP_409_CONFLICT)

    # 2. En curs (reusa transition_task) o claim si ja és En curs d'un altre.
    started = False   # C4d — True només si aquesta crida fa l'INICI real (Pending→InProgress)
    if task.status != 'InProgress':
        try:
            transition_task(task, 'InProgress', profile)
            started = True
        except TransitionError as e:
            # El `code` viatja quan n'hi ha: és l'única manera que el client pugui dir el motiu
            # en comptes del toast genèric. Sense codi, la resposta és exactament la d'abans.
            cos = {'error': str(e)}
            if getattr(e, 'code', None):
                cos['code'] = e.code
            return Response(cos, status=http_status.HTTP_409_CONFLICT)
    elif task.assignee_id != profile.id and not gestos.get('handoff'):
        # J · R3 — EL RELLEU EXIGEIX EL GEST, i el 409 porta QUI la té perquè el client pugui
        # preguntar-ho amb nom i cognoms en comptes d'un «algú altre hi treballa».
        obert = (task.timers.filter(fi__isnull=True, actiu=True)
                 .select_related('tecnic').order_by('-inici').first())
        return Response({'error': "Aquesta tasca la té un altre tècnic: endur-se-la és un gest conscient.",
                         'code': 'tasca_dun_altre', 'task_id': task.id, 'status': task.status,
                         'obert_per': obert.tecnic_id if obert else task.assignee_id,
                         'obert_per_nom': (obert.tecnic.nom_complet if obert
                                           else getattr(task.assignee, 'nom_complet', None))},
                        status=http_status.HTTP_409_CONFLICT)
    elif task.assignee_id != profile.id:
        # F1.5 · D-7 — HANDOFF CONSCIENT. Abans això reassignava i prou: el tram de l'anterior
        # quedava OBERT i seguia imputant-li temps a ell mentre el nou hi treballava sense
        # rellotge propi, i no en quedava cap fila al log. Ara el relleu és un acte visible.
        old_assignee_id = task.assignee_id
        handoff_de = traspassa_tram(task, profile)
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
        # C4d — marca "+": el model ha entrat/pujat al pla per INICI real (no per reorder).
        if started and not model.reanchored_by_start:
            model.reanchored_by_start = True
            model.save(update_fields=['reanchored_by_start'])
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
@permission_classes([_ExecuteTasks])
def sortir_sense_escriptura_view(request, pk):
    """POST /api/v1/model-tasks/<pk>/sortir-sense-escriptura/

    J · R1 — **SENSE ESCRIPTURA, CAP MODAL.** En sortir d'una superfície de treball sense haver
    escrit res, la tasca torna en silenci: no s'ha fet feina, i no hi ha res a decidir.

    Fins ara sortir sempre preguntava «Has acabat?» —una decisió que porta a albarà— encara que
    la sessió hagués estat mirar i marxar. La decisió d'Agus escrita a `ModelSheet.jsx` prohibia
    resoldre-ho per DURADA («no hi ha hagut sessió» no vol dir «ha durat poc»), i tenia raó: el
    predicat no és quant, és **si s'hi ha escrit**. Aquesta vista és aquell predicat, i la resposta
    la dona `TimerEntrada.escriptura_at`, que estampa `batec_escriptura` i només ell.

    🔑 LA MÀQUINA D'ESTATS NO ES TOCA. La tornada és **una sola transició LEGAL**
    (`InProgress → Paused`), la mateixa que el modal ja fa, per la mateixa porta i amb les
    mateixes regles. L'única diferència és que va MARCADA `auto='consulta_sense_escriptura'`:
    la llei del log diu que `auto` null és un gest del tècnic i un slug és el sistema, i aquí el
    tècnic no ha decidit pausar res — ha sortit d'una pantalla on no havia tocat res.

    I el tram que es tanca queda marcat `consulta=True` per `_close_open_timer` (R2), o sigui que
    aquests minuts no entren ni al temps del model ni al Welford. Les dues meitats de J es tanquen
    amb el mateix gest, i per força: són la mateixa sessió.

    ✅ J-bis — «TORNA EXACTAMENT ON ERA» JA ES COMPLEIX TAMBÉ PER A `Pending` (decisió d'Agus).
    `ALLOWED` té ara `InProgress → Pending` com a **única entrada guardada**: existeix per a
    aquest camí i el guard de `transition_task` exigeix marca `auto=AUTO_CONSULTA` **i** tram
    sense escriptura, o sigui que cap gest humà hi pot passar. L'estat d'entrada surt del LOG
    (`TaskTransition`), no d'una memòria del client, i per tant val per a totes les portes.

    Retorna `{revertit, status, motiu}`. `revertit=False` vol dir «hi ha hagut escriptura (o no hi
    ha tram meu obert)»: qui crida ha de seguir amb el modal de sempre.

    ── J-bis · `pausa_si_cal` — LA SORTIDA QUE NO POT ENCADENAR DUES CRIDES ──────────────────
    Amb `{'pausa_si_cal': true}`, una sessió AMB escriptura es pausa aquí mateix en comptes de
    tornar `revertit:false` i esperar que el client decideixi.

    Existeix per al DESMUNTATGE (tancar la pestanya, navegar fora): allà el client no pot
    encadenar res —`keepalive` garanteix que surti la petició que ja ha llançat, no la que
    vindria després de resoldre-la— i el que hi havia era una **pausa cega**, que pausava
    igualment una sessió on no s'havia tocat res. Amb el flag, la MATEIXA petició que abans
    pausava sempre ara pausa només si toca, i si no, torna la tasca on era.

    ⚠️ NOMÉS per a sortides que ja pausaven soles. La sortida DELIBERADA no l'ha de passar: allà
    la persona ha de poder triar `Done`, i decidir-ho per ella seria treure-li la decisió que el
    modal existeix per fer.
    """
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil.', 'code': 'no_profile'},
                        status=http_status.HTTP_403_FORBIDDEN)
    try:
        task = ModelTask.objects.get(pk=pk)
    except ModelTask.DoesNotExist:
        return Response({'error': 'Tasca no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)

    if task.status != 'InProgress':
        # Ja no hi ha res obert: sortir és sortir. Mateixa llei que la sortida del front.
        return Response({'revertit': False, 'status': task.status, 'motiu': 'no_en_curs'})

    # EL MEU TRAM I NOMÉS EL MEU. Si el tram obert és d'un altre (relleu a mitges), el seu
    # rellotge és seu i aquesta sortida no hi pot decidir res — la mateixa llei que el batec.
    tram = task.timers.filter(tecnic=profile, fi__isnull=True, actiu=True).first()
    if tram is None:
        return Response({'revertit': False, 'status': task.status, 'motiu': 'sense_tram_meu'})
    if tram.escriptura_at is not None:
        # J-bis — el desmuntatge no pot encadenar: si demana la pausa, es fa aquí. `auto` null:
        # això sí que és la pausa de sempre d'una sessió amb feina, i no un moviment del sistema.
        if (request.data or {}).get('pausa_si_cal'):
            transition_task(task, 'Paused', profile)
            task.refresh_from_db()
            return Response({'revertit': False, 'pausada': True, 'status': task.status,
                             'motiu': 'amb_escriptura'})
        return Response({'revertit': False, 'status': task.status, 'motiu': 'amb_escriptura'})

    # ── J-bis · A QUIN ESTAT ES TORNA, i d'on se sap ─────────────────────────────────────────
    #
    # A L'ESTAT D'ENTRADA, i el sap **el LOG**: l'última transició cap a `InProgress` d'aquesta
    # tasca porta el `from_status` amb què hi vam entrar. No cal cap camp nou ni cap memòria al
    # client, i funciona per a TOTES les portes d'entrada —el menú, la URL amb `?task_id=`, el
    # Pla de treball—, que és justament el que un estat recordat al front no aconseguiria.
    #
    # `TaskTransition` és append-only i aquesta lectura és la seva: el registre ja és la font de
    # veritat de per on ha passat una tasca, i preguntar-li-ho és més barat i més cert que
    # desar-ho una segona vegada.
    #
    # Sense cap transició registrada (dades velles, o una tasca posada `InProgress` per una via
    # que no hi va escriure) es cau a `Paused`, que és el comportament d'abans d'aquesta peça:
    # no saber d'on venies no pot impedir que surtis.
    entrada = (task.transitions.filter(to_status='InProgress')
               .order_by('-id').values_list('from_status', flat=True).first())
    desti = 'Pending' if entrada == 'Pending' else 'Paused'

    transition_task(task, desti, profile, auto=AUTO_CONSULTA)
    task.refresh_from_db()
    return Response({'revertit': True, 'status': task.status, 'motiu': 'sense_escriptura',
                     'estat_entrada': entrada})


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
    # ⚠️ NO HI HAVIA `search_fields`, I ÉS EL GERMÀ EXACTE DEL DEFECTE DE `CustomerViewSet`, AL
    # REVÉS: aquí el `SearchFilter` sí que hi és (els backends no se sobreescriuen) i el que
    # faltava era la llista de camps. Sense `search_fields`, el `SearchFilter` de DRF **deixa
    # passar el queryset sencer**: mesurat pel lot comercial, `?search=zzzz` retornava
    # exactament el mateix `count` que sense filtrar. `/proveïdors` va quedar sense cercador
    # amb el motiu escrit a la pantalla, perquè un camp de cerca que no filtra és pitjor que
    # no tenir-ne. Els tres camps són els presentables de la fitxa.
    search_fields = ['name', 'nif', 'ciutat']
    # ORDENACIÓ EXPLÍCITA. Avui ja ordenava —hereta l'`OrderingFilter` del defecte i DRF
    # accepta els camps del serializer com a implícits—, però l'implícit és justament el
    # contracte que es trenca en silenci el dia que algú toca el serializer. Escrit, no.
    ordering_fields = ['name', 'type', 'active']
    ordering = ['name']

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


# Codi discriminant de l'error de blindatge del customer propi (patró DA-30): el frontend
# decideix per `code`, mai fent match sobre el text del `detail` (que és català monolingüe).
SELF_CUSTOMER_PROTEGIT = 'self_customer_protected'


def _vol_desactivar(data):
    """El payload demana passar `active` a fals? Tolera el bool de JSON i el text de form-data."""
    if 'active' not in data:
        return False
    v = data['active']
    return v is False or v == 0 or str(v).strip().lower() in ('false', '0')


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    # ⚠️ AQUÍ HI HAVIA `[DjangoFilterBackend, SearchFilter]` I ES MENJAVA L'ORDENACIÓ EN SILENCI.
    # `DEFAULT_FILTER_BACKENDS` (settings.py:222-225) porta els TRES —DjangoFilterBackend,
    # SearchFilter i OrderingFilter—, i declarar-ne dos aquí no n'afegeix: els SUBSTITUEIX tots.
    # Conseqüència viva: `pages/Customers.jsx` envia `ordering=codi` a cada crida i DRF el
    # descarta sense error ni avís. La pàgina demanava un ordre que ningú aplicava, i no fallava
    # mai: la llista sortia en l'ordre del `Meta.ordering` del model i semblava que funcionés.
    # (Trobat pel lot comercial de la part B en anar a posar capçaleres ordenables a `/clients`,
    # que és el que la §8e mana a tota llista del producte.)
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['active']
    search_fields = ['codi', 'nom']   # cercador de la pàgina Clients (codi, nom)
    # Els camps de dada de la llista + els QUATRE COMPTADORS. Els comptadors són `annotate` del
    # `get_queryset` (una sola consulta, cap N+1) i per tant ordenables sense cost afegit: si la
    # §8e diu que tota capçalera de llista és ordenable, una columna de comptador que no ordena
    # és una capçalera que menteix. `ordering` explícit encara que `Customer.Meta.ordering` ja
    # digui el mateix: qui llegeix el ViewSet ha de poder saber en quin ordre surt la llista
    # sense anar a buscar el `Meta` del model.
    #
    # ⚠️ **EL NOM AMB QUÈ S'ORDENA HA DE SER EL NOM AMB QUÈ ES LLEGEIX.** Les anotacions es deien
    # `cnt_quotes_sent`… i el que el client rep es diu `quotes_sent`… — o sigui que ordenar per
    # una columna hauria demanat un nom que la resposta no conté enlloc. Això no és un detall
    # d'estil: `?ordering=quotes_sent` amb el nom d'anotació vell hauria estat DESCARTAT EN
    # SILENCI per DRF (exactament el defecte que aquest commit arregla, un nivell més avall).
    # Les anotacions passen a dir-se com els camps de la resposta i els quatre `getattr` del
    # serializer (`serializers_b.py:195-205`) els segueixen. Cap altre consumidor: censat.
    ordering_fields = ['codi', 'nom', 'active',
                       'quotes_sent', 'quotes_accepted',
                       'orders_open', 'delivery_notes_count']
    ordering = ['codi']

    def get_queryset(self):
        """Comptadors agregats en UNA sola consulta (annotate, cap N+1): ofertes presentades
        (SENT) / acceptades (ACCEPTED), comandes obertes (OPEN) i albarans. `?exclude_self=1`
        amaga el customer propi (is_self) — només la pàgina Clients l'envia; la resta de consumidors
        (selectors de client) segueixen veient-lo."""
        qs = Customer.objects.annotate(
            quotes_sent=Count('quotes', filter=Q(quotes__status='SENT'), distinct=True),
            quotes_accepted=Count('quotes', filter=Q(quotes__status='ACCEPTED'), distinct=True),
            orders_open=Count('salesorders', filter=Q(salesorders__status='OPEN'), distinct=True),
            delivery_notes_count=Count('deliverynotes', distinct=True),
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
        # El customer propi (is_self) és fontaneria del tenant, no un client qualsevol: fa de
        # default de la TechSheet (models_app/services.py:13) i és la casa dels models propis.
        # Esborrar-lo o desactivar-lo deixaria el tenant sense casa, així que el blindatge viu
        # AQUÍ i no només amagant botons — la UI és cortesia, l'API és la porta de debò.
        if self.get_object().is_self:
            return Response(
                {'detail': "No es pot esborrar el client propi del tenant.",
                 'code': SELF_CUSTOMER_PROTEGIT},
                status=status.HTTP_409_CONFLICT)
        # FK Model.customer = PROTECT → si té models, l'esborrat falla. 409 net (no 500).
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': "No es pot esborrar: té models associats. Desactiva'l."},
                status=status.HTTP_409_CONFLICT)

    def update(self, request, *args, **kwargs):
        # Cobreix PUT i PATCH: `partial_update` de DRF delega aquí amb partial=True.
        if _vol_desactivar(request.data) and self.get_object().is_self:
            return Response(
                {'detail': "No es pot desactivar el client propi del tenant.",
                 'code': SELF_CUSTOMER_PROTEGIT},
                status=status.HTTP_409_CONFLICT)
        return super().update(request, *args, **kwargs)

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

    @action(detail=True, methods=['post', 'delete'], url_path='vincular-token')
    def vincular_token(self, request, pk=None):
        """POST {token} — connecta aquest client amb el tenant Brand que l'ha emès. DELETE — desconnecta.

        L'ATERRATGE DEL TOKEN. Fins ara el token del `TenantLink` només el podia consumir un
        humà passant-lo a un command; aquí és on el Studio l'enganxa i el sistema resol tot sol
        de QUIN Brand parla. `Customer.codi_global` era el ganxo previst per a això des de la
        migració 0019 i fins avui no tenia cap consumidor real: aquest n'és el primer.

        EL TOKEN IDENTIFICA, NO AUTORITZA A MÉS DEL QUE JA HI HA. Enganxar-lo no crea cap
        vincle ni el reactiva: només diu "aquest client meu és aquell tenant". Qui emet,
        atura i revoca el pont és el Brand (P7), i això no es toca des d'aquí.

        TRES VALIDACIONS, TOTES NECESSÀRIES:
          · el token existeix — si no, no hi ha res a connectar;
          · el vincle és ACTIU — un pont aturat o revocat no s'ha de poder "reconnectar" per
            la porta del darrere, que és exactament el que seria acceptar-ne el token;
          · el vincle és MEU (`studio_codi_tenant` == el meu tenant) — un token filtrat no ha
            de servir a un tercer per declarar-se destinatari d'un encàrrec que no és seu.
        La resposta d'error és la MATEIXA per als tres casos (400 `token_invalid`): distingir-los
        diria a qui prova un token robat QUÈ ha fallat, i "aquest token és d'un altre studio" ja
        és una pista d'existència. Mateixa llei que el 401 mut del bescanvi (views_bescanvi.py).

        DELETE NO TOCA EL VINCLE, només buida el meu `codi_global`. El pont és patrimoni del
        Brand; el Studio decideix si l'ha mapat a un client seu, no si existeix.
        """
        from fhort.tenants.models import TenantLink

        customer = self.get_object()

        if request.method == 'DELETE':
            customer.codi_global = None
            customer.save(update_fields=['codi_global'])
            return Response(self.get_serializer(customer, context={'request': request}).data)

        token = (request.data.get('token') or '').strip()
        meu_codi = getattr(getattr(request, 'tenant', None), 'codi_tenant', None)
        link = TenantLink.objects.filter(token=token).first() if token else None
        if (link is None
                or not link.es_viu()
                or meu_codi is None
                or link.studio_codi_tenant != meu_codi):
            return Response({'detail': 'Token invàlid, caducat o no destinat a aquest tenant.',
                             'code': 'token_invalid'}, status=status.HTTP_400_BAD_REQUEST)

        # `codi_global` és únic quan no és NULL (constraint `unic_codi_global_no_null`): dos
        # clients del mateix Studio no poden apuntar al mateix Brand. Es comprova abans per
        # donar un 409 amb nom en comptes d'un IntegrityError.
        ja = (Customer.objects
              .filter(codi_global=link.brand_codi_tenant)
              .exclude(pk=customer.pk).first())
        if ja is not None:
            return Response({'detail': f"El client '{ja.codi}' ja està connectat amb aquest tenant.",
                             'code': 'codi_global_pres'}, status=status.HTTP_409_CONFLICT)

        customer.codi_global = link.brand_codi_tenant
        customer.save(update_fields=['codi_global'])
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
    # SET-1: `parts` es niua en lectura al serializer → prefetch, o cada item-conjunt de la
    # graella tornaria a la BD per la seva composició (i cada part per al seu `part_item`).
    queryset = (GarmentTypeItem.objects
                .select_related('garment_type', 'grading_rule_set', 'base_size_definition')
                .prefetch_related('parts__part_item')
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
    # SET-1: `?is_set=true` — la cascada i el wizard han de poder demanar només peces o només
    # conjunts sense filtrar al client.
    filterset_fields = ['garment_type', 'active', 'is_set']
    search_fields = ['code', 'name']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        p = HasCapability(); self.required_capability = CONFIGURE
        return [p]

    @action(detail=True, methods=['put'], url_path='parts')
    def parts(self, request, pk=None):
        """PUT /api/v1/garment-type-items/<id>/parts/ — Body: `[{part_item, ordre, nom_peca}]`

        SET-1 · escriptura de la composició d'un item-conjunt. És un REEMPLAÇAMENT declarat de
        la llista sencera, no un merge: el PATCH genèric del ModelViewSet no escriu relacions
        inverses, i inventar-hi una semàntica parcial (què vol dir «falta una part al payload»?)
        seria pitjor que dir clarament que el que s'envia ÉS la composició.

        Cada fila passa per `GarmentTypeItemPart.clean()` (anti-cicle i anti-set-de-sets) abans
        d'escriure res, exactament com `GarmentTypeItemSerializer.validate()` invoca el clean()
        del seu model: DRF no crida `Model.clean()` sol.

        Gate CONFIGURE (via `get_permissions`: no és list ni retrieve).
        """
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.db import transaction

        item = self.get_object()
        files = request.data
        if not isinstance(files, list):
            return Response({'error': 'El cos ha de ser una llista de parts.'},
                            status=http_status.HTTP_400_BAD_REQUEST)

        nous = []
        vistos = set()
        for i, f in enumerate(files):
            if not isinstance(f, dict) or not f.get('part_item'):
                return Response({'error': f'Fila {i}: `part_item` és obligatori.'},
                                status=http_status.HTTP_400_BAD_REQUEST)
            part_id = f['part_item']
            if part_id in vistos:
                return Response({'error': f'Fila {i}: `part_item` {part_id} repetit.'},
                                status=http_status.HTTP_400_BAD_REQUEST)
            vistos.add(part_id)
            part = GarmentTypeItem.objects.filter(pk=part_id).first()
            if part is None:
                return Response({'error': f'Fila {i}: item {part_id} no trobat.'},
                                status=http_status.HTTP_400_BAD_REQUEST)
            fila = GarmentTypeItemPart(
                set_item=item, part_item=part,
                ordre=f.get('ordre', i + 1) or (i + 1),
                nom_peca=(f.get('nom_peca') or '').strip(),
            )
            try:
                fila.clean()
            except DjangoValidationError as e:
                return Response(getattr(e, 'message_dict', None) or {'error': e.messages},
                                status=http_status.HTTP_400_BAD_REQUEST)
            nous.append(fila)

        with transaction.atomic():
            # PROTECT és de `part_item`, no de `set_item`: esborrar les files de composició
            # d'AQUEST conjunt no toca cap item.
            item.parts.all().delete()
            GarmentTypeItemPart.objects.bulk_create(nous)

        item.refresh_from_db()
        return Response(GarmentTypeItemSerializer(item).data)


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
    from .models import TimerEntrada
    from .services_i import minuts_per_model_task
    qs = ModelTask.objects.select_related('task_type', 'model').all()
    model_id = request.query_params.get('model')
    if model_id:
        qs = qs.filter(model_id=model_id)
    fase = request.query_params.get('fase')
    if fase:
        qs = qs.filter(task_type__fase=fase)
    # Real consolidat per ModelTask: trams tancats i sans (`TRAMS_SANS`). Mateixa font que
    # l'albarà, el compositor del dashboard i el helper canònic _real_minutes. 1 query.
    real_per_task = minuts_per_model_task(TimerEntrada.objects.filter(model_task__in=qs))

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


@api_view(['POST'])
@permission_classes([_ExecuteTasks])
def temps_declarat_view(request, pk):
    """POST /api/v1/model-tasks/<pk>/temps-declarat/  ·  {minuts} XOR {inici, fi}

    F1.7 · D-2, tercera pota: «externes = temps declarat». Una tasca `Externa-lliure` es fa fora
    de l'eina —patró a mà, revisió de disseny— i no hi ha cap escriptura que batre: el rellotge
    no hi arriba mai i, fins avui, aquell temps no existia enlloc.

    Crea un `TimerEntrada` ja TANCAT amb `origen='declarat'`, que el Welford aprèn igual que un
    de mesurat (una tasca, una mostra — D-3). Guard dur a `declara_temps`: sobre una tasca
    Interna es rebutja, perquè allà el temps SÍ que es mesura sol i declarar-lo a mà seria poder
    inventar hores facturables.
    """
    from django.utils.dateparse import parse_datetime

    from .models import ModelTask
    from .services_r import TempsDeclaratError, declara_temps

    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil en aquest tenant.'},
                        status=http_status.HTTP_403_FORBIDDEN)
    try:
        task = ModelTask.objects.select_related('task_type').get(pk=pk)
    except ModelTask.DoesNotExist:
        return Response({'error': 'ModelTask no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)

    dades = request.data or {}
    inici, fi = dades.get('inici'), dades.get('fi')
    try:
        tram = declara_temps(
            task, profile,
            minuts=dades.get('minuts'),
            inici=parse_datetime(inici) if inici else None,
            fi=parse_datetime(fi) if fi else None)
    except TempsDeclaratError as e:
        return Response({'error': str(e), 'code': 'temps_declarat_invalid'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    return Response({'timer_id': tram.pk, 'model_task': task.pk, 'minuts': tram.minuts,
                     'inici': tram.inici.isoformat(), 'fi': tram.fi.isoformat(),
                     'origen': tram.origen},
                    status=http_status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([_ExecuteTasks])
def crono_declarat_view(request, model_id):
    """POST /api/v1/models/<model_id>/crono/  ·  {code, accio: engegar|aturar|descartar|corregir}

    T3 · LA PORTA DEL CRONO DECLARAT. La maqueta aprovada mana una cosa per sobre de tota la
    resta: «viu al servidor; sobreviu a recarregar, canviar de pestanya i tancar el navegador».
    Per això aquí no hi ha cap cronòmetre de navegador que després desa: `engegar` obre un
    `TimerEntrada` REAL amb `origen='declarat'`, i el que el navegador fa és pintar-lo.

    Les quatre accions són les quatre de la maqueta, i cap d'elles tanca la tasca: acabar-la és
    un gest propi (T4). `corregir` accepta {minuts} XOR {inici, fi}, la mateixa regla de D-2.
    """
    from django.utils.dateparse import parse_datetime

    from .models import ModelTask, TaskType, TimerEntrada
    from .services_g import lookup_estimated_minutes
    from .services_r import (TempsDeclaratError, atura_crono_declarat, corregeix_tram_declarat,
                             descarta_tram_declarat, engega_crono_declarat, tasca_vigent)

    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil en aquest tenant.'},
                        status=http_status.HTTP_403_FORBIDDEN)

    dades = request.data or {}
    code, accio = dades.get('code'), dades.get('accio')
    try:
        model = Model.objects.get(pk=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)
    try:
        tt = TaskType.objects.get(code=code, active=True)
    except TaskType.DoesNotExist:
        return Response({'error': f"Tipus de tasca '{code}' no trobat o inactiu."},
                        status=http_status.HTTP_404_NOT_FOUND)
    # La porta és per (model, code) i no per id de tasca, igual que `open-task` i per la mateixa
    # raó (G9): el panell treballa amb el CATÀLEG, i la tasca d'una externa sovint encara no
    # existeix quan el tècnic prem el botó. Qui és «la tasca» ho diu `tasca_vigent` i ningú més.
    task = tasca_vigent(model, code)
    if task is None:
        if accio != 'engegar':
            return Response({'error': 'Aquesta tasca no té cap crono.'},
                            status=http_status.HTTP_404_NOT_FOUND)
        # M1-bis · FIT-4 — engegar el crono d'una externa és treballar-hi: mateix gest, mateixa llei.
        with transaction.atomic():
            task = ModelTask.objects.create(
                model=model, task_type=tt, order=ModelTask.objects.filter(model=model).count(),
                status='Pending', origen='prevista',
                estimated_minutes=lookup_estimated_minutes(model, tt),
                ronda=ronda_del_gest(model))

    def _tram_per_id():
        """El tram sobre el qual s'actua. Sempre d'AQUESTA tasca: un id de fora no val."""
        tram = TimerEntrada.objects.filter(pk=dades.get('timer_id'), model_task=task).first()
        if tram is None:
            raise TempsDeclaratError('Tram no trobat en aquesta tasca.')
        return tram

    try:
        if accio == 'engegar':
            tram = engega_crono_declarat(task, profile)
        elif accio == 'aturar':
            tram = atura_crono_declarat(task, profile)
        elif accio == 'descartar':
            descarta_tram_declarat(_tram_per_id())
            return Response({'descartat': True, 'model_task': task.pk},
                            status=http_status.HTTP_200_OK)
        elif accio == 'corregir':
            inici, fi = dades.get('inici'), dades.get('fi')
            tram = corregeix_tram_declarat(
                _tram_per_id(),
                minuts=dades.get('minuts'),
                inici=parse_datetime(inici) if inici else None,
                fi=parse_datetime(fi) if fi else None)
        else:
            return Response({'error': "`accio` ha de ser engegar|aturar|descartar|corregir.",
                             'code': 'accio_desconeguda'},
                            status=http_status.HTTP_400_BAD_REQUEST)
    except TempsDeclaratError as e:
        return Response({'error': str(e), 'code': 'crono_invalid'},
                        status=http_status.HTTP_400_BAD_REQUEST)

    task.refresh_from_db()
    return Response({'timer_id': tram.pk, 'model_task': task.pk, 'status': task.status,
                     'inici': tram.inici.isoformat(),
                     'fi': tram.fi.isoformat() if tram.fi else None,
                     'minuts': tram.minuts, 'origen': tram.origen},
                    status=http_status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_ExecuteTasks])
def obrir_ronda_view(request, model_id):
    """POST /api/v1/models/<model_id>/obrir-ronda/  ·  {motiu, codes: [...]}

    F2.1 — LA PORTA que a F1 no es va construir. El servei `obrir_ronda` hi era des de F1.1 i no
    tenia manera d'invocar-se des de la UI, de manera que la sortida de D-5 existia només al
    backend: el model 188 seguia tapiat a la pràctica.

    `motiu`: `nova_mostra` (el client demana una altra volta) | `correccio` (ho refem nosaltres).
    `codes`: slugs de `TaskType` que entren a la volta (G9: mai ids).
    """
    from .models import Ronda
    from .services_r import RondaError, obrir_correccio, obrir_ronda

    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil en aquest tenant.'},
                        status=http_status.HTTP_403_FORBIDDEN)
    try:
        model = Model.objects.get(pk=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)

    dades = request.data or {}
    codes = dades.get('codes') or []
    # Els codes han de ser executables per qui obre la ronda: la mateixa allow-list que
    # `open-task`. Obrir una volta és crear feina, i no es crea feina que un mateix no pot fer.
    #
    # M1-bis · FIT-4 — I EL GUARD ES QUEDA NOMÉS AMB EL QUE ES DEMANA. El joc REPLICAT de la volta
    # anterior no passa per aquí a posta: no és una tria de qui obre, és el que el model ja
    # arrossega. Amb el guard aplicat també a la rèplica, un PM que no executi (posem) `pattern_cad`
    # no podria obrir cap volta d'un model que en va fer —o sigui que la porta de +Ronda quedaria
    # tancada precisament per a qui l'ha de fer servir.
    permesos = get_allowed_task_types(request.user)
    fora = [c for c in codes if c not in permesos]
    if fora:
        return Response({'error': f"No pots obrir tasques del tipus: {', '.join(fora)}.",
                         'code': 'task_type_not_allowed'},
                        status=http_status.HTTP_403_FORBIDDEN)
    # S-20 — les dues sortides d'aquesta porta ja no fan el mateix. Una nova MOSTRA obre volta i
    # puja el comptador; una CORRECCIÓ no, perquè `seq` compta mostres i no esmenes nostres. El
    # client segueix demanant-ho igual (`motiu`): qui sap la diferència és el servei.
    motiu = dades.get('motiu')
    try:
        if motiu == Ronda.MOTIU_CORRECCIO:
            ronda, tasques = obrir_correccio(model, codes, profile=profile)
        else:
            ronda = obrir_ronda(model, motiu, codes, profile=profile)
            tasques = list(ronda.tasques.all())
    except RondaError as e:
        return Response({'error': str(e), 'code': 'ronda_invalida'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    # `ronda_id`/`seq` poden ser NULL en una correcció: la de la mare quan n'hi havia, i res quan
    # la mare és la prevista (la volta 1, implícita). El client no els llegeix; el contracte ho diu.
    return Response({'ronda_id': ronda.pk if ronda else None,
                     'seq': ronda.seq if ronda else None,
                     'motiu': motiu,
                     # M1-bis — què ha entrat per rèplica i què s'ha quedat pel camí perquè el
                     # catàleg l'ha desactivat. La UI de M2 ho ha de poder dir en veu alta.
                     'codes_replicats': getattr(ronda, '_codes_replicats', []),
                     'codes_omesos': getattr(ronda, '_codes_omesos', []),
                     # …i què s'ha ADOPTAT del buit entre voltes (feina que ja existia i que
                     # aquesta volta recull). No són tasques noves: la UI no les pot pintar igual.
                     'codes_adoptats': getattr(ronda, '_codes_adoptats', []),
                     'tasques': [t.id for t in tasques]},
                    status=http_status.HTTP_201_CREATED)


# ── M1 · FIT-1 + FIT-13 · LES PORTES DE L'ENTREGA ───────────────────────────────────────────
#
# ✅ PERMISOS — RESOLT (decisió d'Agus, M1-bis 24/08): **`_ExecuteTasks`, la mateixa que obre**.
# «Qui pot treballar pot entregar.» El TODO d'M1 queda retirat: hi vaig deixar `IsAuthenticated`
# perquè `tancar_ronda` no havia tingut mai porta HTTP i per tant cap capability que heretar, i
# la conseqüència era que la porta que TANCA la ronda era més oberta que la que l'obre. Ara les
# dues van amb `EXECUTE_TASKS` i aquella asimetria desapareix.

@api_view(['POST'])
@permission_classes([_ExecuteTasks])
def entrega_ronda_view(request, ronda_id):
    """POST /api/v1/rondes/<ronda_id>/entrega/  ·  {destinatari, descripcio?, data?}

    Informa l'entrega d'una ronda. **I amb això la tanca** (FIT-13), i el tancament tanca la
    feina viva de la volta (FIT-6) — tot dins la mateixa transacció.
    """
    from .models import Ronda
    from .serializers_b import EntregaSerializer
    from .services_r import EntregaError, RondaError, informar_entrega

    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil en aquest tenant.', 'code': 'no_profile'},
                        status=http_status.HTTP_403_FORBIDDEN)
    try:
        ronda = Ronda.objects.get(pk=ronda_id)
    except Ronda.DoesNotExist:
        return Response({'error': 'Ronda no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)

    # La FORMA la valida el serializer i el FET el decideix el servei. `data` arriba com a text
    # per HTTP: passar-la crua al model la desaria sense parsejar (o petaria en cru, segons el
    # backend). Aquí ja arriba `datetime` o ja s'ha rebutjat amb el 400 de sempre de DRF.
    forma = EntregaSerializer(data=request.data or {})
    if not forma.is_valid():
        return Response(forma.errors, status=http_status.HTTP_400_BAD_REQUEST)
    dades = forma.validated_data
    try:
        entrega = informar_entrega(ronda, destinatari=dades.get('destinatari'),
                                   descripcio=dades.get('descripcio') or '',
                                   data=dades.get('data') or None, profile=profile)
    except EntregaError as e:
        return Response({'error': str(e), 'code': 'entrega_invalida'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    except RondaError as e:
        # El tancament forçat (FIT-6) ha topat amb una paret: l'entrega NO s'ha escrit (la
        # transacció d'`informar_entrega` és una sola) i el client ha de saber que el motiu és
        # la feina de la volta, no la forma de l'entrega.
        return Response({'error': str(e), 'code': 'ronda_no_tancable'},
                        status=http_status.HTTP_409_CONFLICT)
    return Response(EntregaSerializer(entrega).data, status=http_status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([_ExecuteTasks])
def entrega_ok_client_view(request, entrega_id):
    """PATCH /api/v1/entregues/<entrega_id>/ok-client/  ·  {data_ok?}

    El senyal MANUAL i posterior: el client diu que li ha arribat bé. No toca la ronda.
    """
    from rest_framework import serializers

    from .models import Entrega
    from .serializers_b import EntregaSerializer
    from .services_r import EntregaError, informar_ok_client

    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil en aquest tenant.', 'code': 'no_profile'},
                        status=http_status.HTTP_403_FORBIDDEN)
    try:
        entrega = Entrega.objects.get(pk=entrega_id)
    except Entrega.DoesNotExist:
        return Response({'error': 'Entrega no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)

    data_ok = (request.data or {}).get('data_ok') or None
    if data_ok is not None:
        try:
            data_ok = serializers.DateTimeField().to_internal_value(data_ok)
        except ValidationError as e:
            return Response({'data_ok': e.detail}, status=http_status.HTTP_400_BAD_REQUEST)
    try:
        entrega = informar_ok_client(entrega, profile=profile, data_ok=data_ok)
    except EntregaError as e:
        return Response({'error': str(e), 'code': 'ok_client_invalid'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    return Response(EntregaSerializer(entrega).data, status=http_status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rondes_del_model_view(request, model_id):
    """GET /api/v1/models/<model_id>/rondes/ — les voltes del model, amb la seva entrega.

    Sense aquesta porta l'Entrega seria una dada que no es pot llegir: `ronda_oberta` (a
    `models_app`) no la pot ensenyar mai, perquè una ronda entregada és una ronda TANCADA.
    """
    from .models import Ronda
    from .serializers_b import RondaSerializer

    if not Model.objects.filter(pk=model_id).exists():
        return Response({'error': 'Model no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)
    qs = (Ronda.objects.filter(model_id=model_id)
          .select_related('entrega__qui_informa', 'entrega__qui_informa_ok').order_by('seq'))
    return Response(RondaSerializer(qs, many=True).data, status=http_status.HTTP_200_OK)
