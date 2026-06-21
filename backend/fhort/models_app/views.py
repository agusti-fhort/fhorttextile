import datetime

from django.db import connection, transaction
from rest_framework import viewsets
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import BaseMeasurement, ConsumptionRecord, GarmentSet, Model, ModelFitxer
from .serializers import (
    BaseMeasurementSerializer,
    ModelDetailSerializer,
    ModelFitxerSerializer,
    ModelListSerializer,
)


class ModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estat', 'fase_actual', 'garment_type', 'responsable', 'temporada', 'any']
    search_fields = ['codi_intern', 'codi_client', 'nom_prenda']
    ordering_fields = ['prioritat', 'data_objectiu', 'data_entrada']
    ordering = ['-prioritat']
    queryset = Model.objects.all()

    def get_queryset(self):
        # django-tenants already restricts queries to the current tenant schema
        # via the connection. The 'public' schema has no model tables, but we
        # return an empty queryset to avoid errors in misrouted views.
        if getattr(connection, 'schema_name', None) == 'public':
            return Model.objects.none()
        qs = (
            Model.objects
            .select_related('garment_type', 'garment_group',
                            'responsable', 'responsable__user',
                            'size_system', 'grading_rule_set')
            .all()
        )
        if self.action != 'list':
            return qs
        # Pas 5C — enriquiment de la LLISTA: 3 dates de cicle (Subquery correlat, sense N+1) +
        # prefetch dels assignees per al "principal + N" (tècnics).
        from django.db.models import OuterRef, Subquery, Prefetch
        from django.utils import timezone
        from fhort.tasks.models import Production, ModelTask
        from fhort.fitting.models import FittingSession
        today = timezone.localdate()
        return qs.annotate(
            entrada_prod=Subquery(Production.objects
                .filter(model=OuterRef('pk'), phase=OuterRef('fase_actual'))
                .order_by('-requested_at').values('requested_at')[:1]),
            arribada_proto=Subquery(Production.objects
                .filter(model=OuterRef('pk'), phase='Proto', delivered_at__isnull=False)
                .order_by('-delivered_at').values('delivered_at')[:1]),
            fitting_prev=Subquery(FittingSession.objects
                .filter(model=OuterRef('pk'), data__gte=today)
                .order_by('data').values('data')[:1]),
        ).prefetch_related(Prefetch(
            'model_tasks',
            queryset=ModelTask.objects.exclude(assignee__isnull=True).select_related('assignee'),
        ))

    def get_serializer_class(self):
        if self.action == 'list':
            return ModelListSerializer
        return ModelDetailSerializer


class ModelFitxerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ModelFitxerSerializer
    queryset = ModelFitxer.objects.select_related('model', 'pujat_per').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'categoria', 'tipus', 'enviat_ia']
    ordering_fields = ['data_pujada']
    ordering = ['-data_pujada']


# Sprint S14B — BaseMeasurement CRUD
class BaseMeasurementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BaseMeasurementSerializer
    queryset = (
        BaseMeasurement.objects
        .select_related('pom', 'pom__pom_global')
        .all()
    )
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'pom', 'is_active', 'origen']
    ordering_fields = ['updated_at', 'id']
    ordering = ['model', 'id']

    def get_queryset(self):
        # The 'public' schema has no tenant data — return an empty queryset.
        if getattr(connection, 'schema_name', None) == 'public':
            return BaseMeasurement.objects.none()
        return super().get_queryset()

    # Sprint 3 / F1: tag the request user so the change-log signal can fill created_by.
    def perform_create(self, serializer):
        # created_by is set on the instance before the signal fires.
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        # _changed_by takes priority over the original created_by for edits.
        serializer.instance._changed_by = self.request.user
        serializer.save()



# Sprint 1C — ModelServeiViewSet
from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend

class ModelServeiViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['model', 'servei', 'contractat', 'estat_autoritzacio']
    ordering = ['servei__ordre_popup']

    def get_queryset(self):
        from .models import ModelServei
        return ModelServei.objects.select_related('servei', 'model').all()

    def get_serializer_class(self):
        from .serializers import ModelServeiSerializer
        return ModelServeiSerializer


def _resolve_customer_code(customer_id):
    """Codi (3 chars) per a un customer_id donat, amb fallback al self-customer del tenant.
    Font única del prefix per als endpoints de codi-gen (preview i creació)."""
    from fhort.tasks.models import Customer
    from fhort.models_app.services import get_self_customer
    cust = None
    if customer_id:
        cust = Customer.objects.filter(pk=customer_id).first()
    if cust is None:
        cust = get_self_customer()
    return (cust.codi if cust else 'IMP'), cust


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def next_model_ref(request):
    year = request.GET.get('year', str(datetime.date.today().year))
    season = request.GET.get('season', 'SS')
    # El prefix surt del customer (la preview ha de portar ?customer_id); fallback self-customer.
    prefix, _ = _resolve_customer_code(request.GET.get('customer_id'))
    year_short = str(year)[-2:]
    base = f"{prefix}-{season}{year_short}-"
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT codi_intern FROM models_app_model "
            "WHERE codi_intern LIKE %s "
            "ORDER BY codi_intern DESC LIMIT 1",
            [base + '%']
        )
        row = cursor.fetchone()
    if row:
        last_num = int(row[0].split('-')[-1])
        next_num = last_num + 1
    else:
        next_num = 1
    codi = f"{base}{str(next_num).zfill(4)}"
    return Response({'codi_intern': codi, 'next_number': next_num})


def _resolve_garment_def(d):
    """Resol la definició de garment + talles d'un payload d'esquelet (Pas 5A).
    Cada camp és OPCIONAL (es posa només si ve al payload). Retorna (fields, error_msg).
    garment_type_item_id és la BAULA del motor de temps (matriu item×task_type)."""
    from fhort.pom.models import GarmentType, GarmentGroup, SizeSystem, GradingRuleSet
    from fhort.tasks.models import GarmentTypeItem
    fields = {}
    # Pont família↔item: si arriba l'item, la família (i el grup) es DERIVEN de l'item; el
    # garment_type_id del payload s'IGNORA → garanteix garment_type == garment_type_item.garment_type.
    if d.get('garment_type_item_id'):
        try:
            item = (GarmentTypeItem.objects.select_related('garment_type')
                    .get(id=d['garment_type_item_id']))
        except GarmentTypeItem.DoesNotExist:
            return None, 'GarmentTypeItem no trobat'
        fields['garment_type_item'] = item
        fields['garment_type'] = item.garment_type
        grp = GarmentGroup.objects.filter(codi=item.garment_type.grup).first()
        if grp is not None:
            fields['garment_group'] = grp
    elif d.get('garment_type_id'):
        # Legacy: sense item → es respecta el garment_type_id del payload (compatibilitat).
        try:
            fields['garment_type'] = GarmentType.objects.get(id=d['garment_type_id'])
        except GarmentType.DoesNotExist:
            return None, 'GarmentType no trobat'
    if d.get('size_system_id'):
        try:
            fields['size_system'] = SizeSystem.objects.get(id=d['size_system_id'])
        except SizeSystem.DoesNotExist:
            return None, 'SizeSystem no trobat'
    if d.get('grading_rule_set_id'):
        try:
            fields['grading_rule_set'] = GradingRuleSet.objects.get(id=d['grading_rule_set_id'])
        except GradingRuleSet.DoesNotExist:
            pass  # tolerant (com el flux original)
    if d.get('target'):
        fields['target'] = d['target']
    if d.get('construction'):
        fields['construction'] = d['construction']
    if d.get('size_run'):
        fields['size_run_model'] = d['size_run']
    if d.get('base_size'):
        fields['base_size_label'] = d['base_size']
    return fields, None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_model_wizard(request):
    """Pas 5A — creació UNIFICADA: l'esquelet COMPLET (identificació + garment def + talles)
    en un sol POST. Desa garment_type_item (baula del motor) i la traçabilitat created_by."""
    year = request.data.get('year')
    season = request.data.get('season')
    ref_client = request.data.get('ref_client', '')
    customer_id = request.data.get('customer_id')
    nom_prenda = request.data.get('nom_prenda', '')
    descripcio = request.data.get('descripcio', '')
    collection = request.data.get('collection', '')
    data_objectiu = request.data.get('data_objectiu') or None   # deadline (opcional)
    # Sprint A — multi-piece (immutable after creation)
    is_multipiece = bool(request.data.get('is_multipiece', False))
    num_pieces = request.data.get('num_pieces')

    # PG-3 Cas B: bloqueig a la CREACIÓ — talla base sense ruleset triat no té grading.
    # Només aquí (no al builder compartit ni a update_model_step2, on base i ruleset poden
    # venir per separat legítimament en edició).
    if request.data.get('base_size') and not request.data.get('grading_rule_set_id'):
        return Response(
            {'error': 'Selecciona un ruleset de graduació per a la talla base.'}, status=400)

    garment_fields, gerr = _resolve_garment_def(request.data)
    if gerr:
        return Response({'error': gerr}, status=400)
    creator = getattr(request.user, 'profile', None)

    if not year or not season:
        return Response({'error': 'year i season són obligatoris'}, status=400)

    if is_multipiece:
        try:
            num_pieces = int(num_pieces)
        except (TypeError, ValueError):
            return Response(
                {'error': 'num_pieces ha de ser un enter quan is_multipiece és cert'},
                status=400,
            )
        if num_pieces < 2:
            return Response(
                {'error': 'Un conjunt multi-peça necessita num_pieces >= 2'},
                status=400,
            )

    # Prefix unificat: codi del customer (fallback self-customer). Escopa la seqüència via
    # el codi_intern (regex sota), de manera que el next_num ja és per-customer (Pas 4).
    prefix, customer = _resolve_customer_code(customer_id)
    year_short = str(year)[-2:]
    base = f"{prefix}-{season}{year_short}-"

    # next_num must look ONLY at base codes (FTT-SS26-NNNN), NOT at piece codes
    # (FTT-SS26-NNNN-NN). A plain LIKE 'base%' would capture piece codes and
    # split('-')[-1] would return the piece suffix, breaking the sequence.
    # The regex anchors a 4-digit sequential at the end → piece codes excluded.
    # We scan BOTH Model.codi_intern base codes AND GarmentSet.codi_base, because
    # a set's base number is consumed (its pieces are NNNN-01/-02) and must not be
    # reused by a later single model.
    base_pattern = f"^{prefix}-{season}{year_short}-[0-9]{{4}}$"
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT codi_intern FROM models_app_model WHERE codi_intern ~ %s",
            [base_pattern]
        )
        candidates = [r[0] for r in cursor.fetchall()]
        cursor.execute(
            "SELECT codi_base FROM models_app_garmentset WHERE codi_base ~ %s",
            [base_pattern]
        )
        candidates += [r[0] for r in cursor.fetchall()]
    nums = [int(c.split('-')[-1]) for c in candidates]
    next_num = (max(nums) + 1) if nums else 1
    codi_base = f"{base}{str(next_num).zfill(4)}"

    # Single piece (~90%): unchanged flow, no GarmentSet.
    if not is_multipiece:
        model = Model.objects.create(
            codi_intern=codi_base,
            codi_client=ref_client,
            customer=customer,
            codi_tenant=prefix,
            any=int(year),
            temporada=season,
            sequencial=next_num,
            nom_prenda=nom_prenda or None,
            descripcio=descripcio or None,
            collection=collection or '',
            created_by=creator,
            estat='Nou',
            data_objectiu=data_objectiu,
            **garment_fields,
        )
        # PG-2 Cas B: si s'ha triat ruleset, materialitza'n les regles al model (origen=CANONICAL).
        # El model ja està desat (create fora de transacció); l'atomic embolcalla NOMÉS la
        # materialització → si peta, no queda cap MGR parcial i el model gradua igualment pel
        # fallback PG-1 (ruleset extern). Degradació gràcil INTENCIONAL, no descuit.
        if model.grading_rule_set_id:
            from django.db import transaction
            from fhort.models_app.services import materialize_model_grading_rules
            with transaction.atomic():
                materialize_model_grading_rules(
                    model, model.grading_rule_set.regles.all(), origen='CANONICAL')
        return Response({'id': model.id, 'codi_intern': model.codi_intern}, status=201)

    # Multi-piece: one GarmentSet + N piece Models, codi_intern = codi_base-NN.
    with transaction.atomic():
        garment_set = GarmentSet.objects.create(
            codi_base=codi_base,
            nom_comercial=nom_prenda or '',
            num_pieces=num_pieces,
        )
        pieces = []
        for i in range(1, num_pieces + 1):
            piece = Model.objects.create(
                codi_intern=f"{codi_base}-{str(i).zfill(2)}",
                codi_client=ref_client,
                customer=customer,
                codi_tenant=prefix,
                any=int(year),
                temporada=season,
                sequencial=next_num,
                nom_prenda=nom_prenda or None,
                descripcio=descripcio or None,
                collection=collection or '',
                created_by=creator,
                estat='Nou',
                data_objectiu=data_objectiu,
                garment_set=garment_set,
                piece_number=i,
                **garment_fields,
            )
            # PG-2 Cas B (multi-peça): cada peça hereta el ruleset via garment_fields →
            # materialitza les seves regles residents. Dins l'atomic del set: una fallada
            # avorta tot el conjunt (atòmic per disseny del multi-peça).
            if piece.grading_rule_set_id:
                from fhort.models_app.services import materialize_model_grading_rules
                materialize_model_grading_rules(
                    piece, piece.grading_rule_set.regles.all(), origen='CANONICAL')
            pieces.append({
                'id': piece.id,
                'codi_intern': piece.codi_intern,
                'piece_number': piece.piece_number,
            })

    return Response({
        'garment_set_id': garment_set.id,
        'codi_base': garment_set.codi_base,
        'num_pieces': garment_set.num_pieces,
        'pieces': pieces,
    }, status=201)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_model_step2(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    d = request.data
    # Pas 5A — reutilitza el mateix resolutor que la creació (inclou garment_type_item_id).
    garment_fields, gerr = _resolve_garment_def(d)
    if gerr:
        return Response({'error': gerr}, status=400)
    for k, v in garment_fields.items():
        setattr(model, k, v)
    if d.get('collection') is not None:
        model.collection = d['collection'] or ''

    model.save()
    # PG-2 Cas B: re-materialitza si hi ha ruleset (wipe-and-recreate cobreix canvi de profile).
    # L'atomic embolcalla només la materialització → si peta, el model queda sense MGR i gradua
    # pel fallback PG-1 (ruleset extern). Degradació gràcil INTENCIONAL, no descuit.
    if model.grading_rule_set_id:
        from django.db import transaction
        from fhort.models_app.services import materialize_model_grading_rules
        with transaction.atomic():
            materialize_model_grading_rules(
                model, model.grading_rule_set.regles.all(), origen='CANONICAL')
    return Response({'id': model.id, 'codi_intern': model.codi_intern})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def suggested_poms_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    # Migration família → item: els POMs suggerits surten de l'ITEM (garment_type_item),
    # no de la família. Si el model no té item definit, no hi ha suggeriment.
    if not model.garment_type_item_id:
        return Response({'poms': [], 'warning': 'Garment type item no definit'})

    from fhort.pom.models import GarmentPOMMap

    maps = GarmentPOMMap.objects.filter(
        garment_type_item=model.garment_type_item,
    ).select_related('pom', 'pom__pom_global').order_by('-is_key', 'ordre')

    result = []
    for m in maps:
        pom = m.pom
        pg = getattr(pom, 'pom_global', None)
        result.append({
            'pom_id': pom.id,
            'pom_code': pom.codi_client,
            'nom_en': pg.nom_en if pg else pom.nom_client,
            'nom_ca': pg.nom_ca if pg else pom.nom_client,
            'abbreviation': pg.abbreviation if pg else '',
            'categoria': pg.categoria if pg else '',
            'is_key': m.is_key,
            'ordre': m.ordre,
        })

    return Response({'poms': result, 'total': len(result)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def materialize_poms_view(request, model_id):
    """POST /api/v1/models/<id>/materialitzar-poms/ — instancia la pertinença de POMs de l'item
    com a BaseMeasurement BUIDES (base_value_cm=None, origen='TEMPLATE'), copiant is_key/ordre de
    la plantilla GarmentPOMMap. Idempotent (get_or_create per (model,pom)): no toca files existents
    (amb o sense valor). Les buides NO disparen log (guard al signal). Sense garment_type_item → avís."""
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    if not model.garment_type_item_id:
        return Response({'materialized': 0, 'skipped': 0,
                         'warning': 'Garment type item no definit'})

    from fhort.pom.models import GarmentPOMMap
    from fhort.models_app.models import BaseMeasurement

    maps = (GarmentPOMMap.objects
            .filter(garment_type_item=model.garment_type_item)
            .select_related('pom').order_by('ordre'))
    materialized = skipped = 0
    for m in maps:
        _, created = BaseMeasurement.objects.get_or_create(
            model=model, pom=m.pom,
            defaults={
                'base_value_cm': None,        # materialitzada sense valor
                'origen': 'TEMPLATE',
                'is_key': m.is_key,
                'ordre': m.ordre,
            },
        )
        if created:
            materialized += 1
        else:
            skipped += 1
    return Response({'materialized': materialized, 'skipped': skipped,
                     'total_template': maps.count()})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_table_view(request, model_id):
    """POST /api/v1/models/<id>/tancar-taula/ — Sprint B · tancar la taula de mides.

    Resol (o crea, get_or_create_size_fitting) el SizeFitting del model i executa
    close_base → estat final 'Tancat'. Avís clar si encara no hi ha mides entrades
    (BaseMeasurement amb valor): no es pot tancar una taula buida."""
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    from fhort.models_app.models import BaseMeasurement
    # Guarda UX: una taula sense cap mida entrada (només files TEMPLATE buides) no es tanca.
    if not BaseMeasurement.objects.filter(
        model=model, is_active=True, base_value_cm__isnull=False
    ).exists():
        return Response(
            {'error': 'Cal introduir mides abans de tancar la taula.'},
            status=400,
        )

    from fhort.pom.services import get_or_create_size_fitting, close_base
    profile = getattr(request.user, 'profile', None)
    try:
        # Atòmic (B4): si es tanca la taula, es tanca la tasca. Tot o res.
        with transaction.atomic():
            sf = get_or_create_size_fitting(model, request.user.id)
            result = close_base(sf.id, request.user.id)
            pom_task = _close_pom_task_for_model(model, profile)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error closing table")
        return Response({'error': str(e)}, status=500)

    return Response({'sf_id': sf.id, 'pom_task': pom_task, **result})


def _close_pom_task_for_model(model, profile):
    """B4 · en tancar la taula, la tasca POM del model passa a Done via transition_task
    (l'única porta: status=Done, finished_at, tanca timer, record_actual_time, log).
    Done només és vàlid des de InProgress → si està Pending/Paused, hi passem primer.
    Sense tasca pom → no fa res. Ja Done → idempotent."""
    from fhort.tasks.models import ModelTask
    from fhort.tasks.services_c import transition_task

    task = (ModelTask.objects
            .filter(model=model, task_type__code='pom')
            .order_by('id').first())
    if not task:
        return {'closed': False, 'reason': 'no_pom_task'}
    if task.status == 'Done':
        return {'closed': False, 'reason': 'already_done', 'task_id': task.id}

    # Done només es pot assolir des de InProgress (ALLOWED a services_c). Pending/Paused
    # hi passen primer perquè la transició no peti.
    if task.status in ('Pending', 'Paused'):
        transition_task(task, 'InProgress', profile)
        task.refresh_from_db()
    transition_task(task, 'Done', profile)
    return {'closed': True, 'task_id': task.id}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def measurements_table_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    from fhort.models_app.models import BaseMeasurement

    size_run = []
    if model.size_run_model:
        size_run = [s.strip() for s in model.size_run_model.split('·') if s.strip()]

    base_measurements = BaseMeasurement.objects.filter(
        model=model,
        is_active=True,
    ).select_related('pom', 'pom__pom_global').order_by('ordre', 'pom__codi_client')

    graded_by_pom = {}
    try:
        from fhort.fitting.models import SizeFitting, GradingVersion, GradedSpec
        sf = SizeFitting.objects.filter(model=model).first()
        if sf:
            gv = GradingVersion.objects.filter(
                size_fitting=sf
            ).order_by('-data').first()
            if gv:
                for spec in GradedSpec.objects.filter(grading_version=gv):
                    pom_id = spec.pom_id
                    if pom_id not in graded_by_pom:
                        graded_by_pom[pom_id] = {}
                    graded_by_pom[pom_id][spec.size_label] = (
                        float(spec.graded_value_cm) if spec.graded_value_cm is not None else None
                    )
    except Exception:
        pass

    rows = []
    for bm in base_measurements:
        pom = bm.pom
        pg = getattr(pom, 'pom_global', None)
        rows.append({
            'id': bm.id,
            'ordre': bm.ordre,
            'pom_id': pom.id,
            'pom_code': pom.codi_client,
            'nom_fitxa': bm.nom_fitxa or '',
            'nom_en': pg.nom_en if pg else pom.nom_client,
            'nom_ca': pg.nom_ca if pg else pom.nom_client,
            'abbreviation': pg.abbreviation if pg else '',
            'base_value_cm': float(bm.base_value_cm) if bm.base_value_cm is not None else None,
            'is_key': bm.is_key,
            'origen': bm.origen,
            'notes': bm.notes or '',
            'graded': graded_by_pom.get(pom.id, {}),
        })

    base_size = model.base_size_label

    def _size_value(row, size):
        # The base-size value lives in base_value_cm; the rest, in graded (GradedSpec).
        if size == base_size:
            return row['base_value_cm']
        return row['graded'].get(size)

    # Sizes with at least one real value (≠ null) in some row.
    sizes_with_data = [
        s for s in size_run
        if any(_size_value(r, s) is not None for r in rows)
    ]

    # Δ = mean of increments between consecutive sizes with data; None if <2 values.
    deltas = {}
    for r in rows:
        values = [_size_value(r, s) for s in sizes_with_data]
        values = [v for v in values if v is not None]
        if len(values) >= 2:
            increments = [values[i + 1] - values[i] for i in range(len(values) - 1)]
            deltas[str(r['pom_id'])] = round(sum(increments) / len(increments), 2)
        else:
            deltas[str(r['pom_id'])] = None

    # Taula tancada? (SizeFitting estat='Tancat' → vista de només lectura al frontend)
    tancat = False
    try:
        from fhort.fitting.models import SizeFitting
        tancat = SizeFitting.objects.filter(model=model, estat='Tancat').exists()
    except Exception:
        tancat = False

    return Response({
        'model_id': model.id,
        'codi_intern': model.codi_intern,
        'base_size': base_size,
        'size_run': size_run,               # kept so as not to break consumers
        'size_run_complet': size_run,
        'sizes_amb_dades': sizes_with_data,
        'deltes': deltas,
        'rows': rows,
        'total_poms': len(rows),
        'tancat': tancat,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_measurements_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    measurements = request.data.get('measurements', [])
    # keep_pom_ids: TOTS els pom_id que segueixen a la taula (amb valor O buits/TEMPLATE). Els
    # BaseMeasurement actius del model el pom dels quals NO hi és → soft-delete (is_active=False),
    # com fa el xat IA, per persistir la X d'eliminar fila. None = client antic, no desactivar.
    keep_pom_ids = request.data.get('keep_pom_ids', None)
    if not measurements and keep_pom_ids is None:
        return Response({'error': 'measurements és obligatori'}, status=400)

    from fhort.pom.models import POMMaster
    from fhort.models_app.models import BaseMeasurement

    created = updated = deactivated = 0
    errors = []

    with transaction.atomic():
        for m in measurements:
            pom_id = m.get('pom_id')
            value = m.get('base_value_cm')
            if not pom_id or value is None:
                errors.append(f'pom_id i base_value_cm obligatoris')
                continue
            try:
                pom = POMMaster.objects.get(id=pom_id)
                _, was_created = BaseMeasurement.objects.update_or_create(
                    model=model, pom=pom,
                    defaults={
                        'base_value_cm': float(value),
                        'notes': m.get('notes', ''),
                        'origen': 'MANUAL',
                        # Re-entrar un valor reactiva una fila prèviament eliminada.
                        'is_active': True,
                        # Sprint 5B.1: copy tolerance from the catalogue POM.
                        'tolerancia_minus': pom.tolerancia_default_minus,
                        'tolerancia_plus': pom.tolerancia_default_plus,
                    }
                )
                if was_created: created += 1
                else: updated += 1
            except POMMaster.DoesNotExist:
                errors.append(f'POMMaster {pom_id} no trobat')

        if keep_pom_ids is not None:
            keep = [int(x) for x in keep_pom_ids]
            deactivated = (BaseMeasurement.objects
                           .filter(model=model, is_active=True)
                           .exclude(pom_id__in=keep)
                           .update(is_active=False))

    # NOTE: set-measurements només fa upsert de BaseMeasurement (+ el log via signal). La generació
    # de GradedSpec viu EXCLUSIVAMENT a generar-grading → generate_graded_specs (l'únic camí que
    # respecta ModelGradingOverride). El grading inline d'aquí estava trencat (rule.increment_cm no
    # existeix → delta 0) i clobberava els overrides; eliminat.
    return Response({'created': created, 'updated': updated, 'deactivated': deactivated,
                     'errors': errors},
                    status=201 if not errors else 207)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reorder_measurements_view(request, model_id):
    """
    Update the order of a model's BaseMeasurements.
    Payload: { order: [bm_id_1, bm_id_2, ...] }
    """
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    order = request.data.get('order', [])
    if not order:
        return Response({'error': 'order és obligatori'}, status=400)

    from fhort.models_app.models import BaseMeasurement
    for i, bm_id in enumerate(order):
        BaseMeasurement.objects.filter(id=bm_id, model=model).update(ordre=i)

    return Response({'updated': len(order)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_file_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    uploaded_file = request.FILES.get('fitxer')
    if not uploaded_file:
        return Response({'error': 'fitxer és obligatori'}, status=400)

    tipus = request.data.get('tipus', 'ALTRES')
    name = request.data.get('nom') or uploaded_file.name

    # version: increment the latest of the same type
    latest = ModelFitxer.objects.filter(model=model, tipus=tipus).order_by('-id').first()
    try:
        prev_num = int(latest.versio) if latest and latest.versio else 0
    except (TypeError, ValueError):
        prev_num = 0
    version = str(prev_num + 1)

    # Map type → category (existing) for consistency with old filters
    categoria_map = {
        'PATRO': 'Patro', 'MARCADA': 'Patro', 'ESCALAT': 'Patro',
        'SKETCH_FLETXES': 'Disseny', 'SKETCH_NET': 'Disseny',
        'FITXA': 'Document',
    }
    categoria = categoria_map.get(tipus, 'Document')

    mf = ModelFitxer.objects.create(
        model=model,
        fitxer=uploaded_file,
        nom_fitxer=name,
        tipus=tipus,
        categoria=categoria,
        versio=version,
        mida_bytes=uploaded_file.size,
        path_servidor=uploaded_file.name,
        pujat_per=getattr(request.user, 'profile', None),
    )

    return Response({
        'id': mf.id,
        'nom_fitxer': mf.nom_fitxer,
        'tipus': mf.tipus,
        'categoria': mf.categoria,
        'versio': mf.versio,
        'url': request.build_absolute_uri(mf.fitxer.url) if mf.fitxer else None,
    }, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_analysis_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    import anthropic
    import base64
    import json
    from django.conf import settings

    base_measurements = BaseMeasurement.objects.filter(
        model=model, is_active=True
    ).select_related('pom').order_by('ordre')

    mesures_text = "\n".join([
        f"- {bm.pom.codi_client}: {bm.base_value_cm}cm ({bm.pom.nom_client or ''})"
        for bm in base_measurements
    ])

    fitxers_analisi = list(ModelFitxer.objects.filter(
        model=model,
        tipus__in=['PATRO', 'ESCALAT', 'SKETCH_FLETXES', 'SKETCH_NET']
    ).order_by('-id')[:5])

    content_blocks = []
    for mf in fitxers_analisi:
        if not mf.fitxer:
            continue
        try:
            with mf.fitxer.open('rb') as f:
                data = f.read()
            ext = mf.nom_fitxer.split('.')[-1].lower()
            if ext == 'pdf':
                content_blocks.append({
                    'type': 'document',
                    'source': {
                        'type': 'base64',
                        'media_type': 'application/pdf',
                        'data': base64.standard_b64encode(data).decode('utf-8'),
                    },
                    'title': mf.nom_fitxer,
                })
            elif ext in ('jpg', 'jpeg', 'png', 'svg'):
                media_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                             'png': 'image/png', 'svg': 'image/svg+xml'}
                content_blocks.append({
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': media_map.get(ext, 'image/png'),
                        'data': base64.standard_b64encode(data).decode('utf-8'),
                    },
                })
        except Exception:
            continue

    if not content_blocks:
        return Response({'error': 'No hi ha fitxers per analitzar'}, status=400)

    prompt = (
        f"Ets un expert tècnic en patronatge i especificació de peces de moda.\n\n"
        f"MODEL: {model.codi_intern} — {model.nom_prenda or ''}\n"
        f"TARGET: {model.target or ''} | CONSTRUCCIÓ: {model.construction or ''} | "
        f"FIT: {model.fit_type or ''}\n"
        f"TALLA BASE: {model.base_size_label or ''} | RUN: {model.size_run_model or ''}\n\n"
        f"MESURES DE LA TALLA BASE:\n{mesures_text or 'No hi ha mesures registrades.'}\n\n"
        "Analitza els fitxers adjunts i detecta discrepàncies. Retorna ÚNICAMENT aquest JSON:\n"
        "{\n"
        '  "alertes": [\n'
        "    {\n"
        '      "tipus": "DISCREPANCIA_TEIXIT|DISCREPANCIA_MESURA|DISCREPANCIA_ESCALAT|AVÍS_SKETCH|ALTRE",\n'
        '      "gravetat": "CRITICA|IMPORTANT|INFORMATIVA",\n'
        '      "descripcio": "descripció clara del problema",\n'
        '      "pom_afectat": "codi POM o null",\n'
        '      "valor_taula": "valor a la taula o null",\n'
        '      "valor_patro": "valor al patró o null",\n'
        '      "accio_suggerida": "què hauria de fer el tècnic"\n'
        "    }\n"
        "  ],\n"
        '  "resum": "resum breu de l\'anàlisi",\n'
        f'  "fitxers_analitzats": {len(fitxers_analisi)}\n'
        "}"
    )

    content_blocks.append({'type': 'text', 'text': prompt})

    try:
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-opus-4-5',
            max_tokens=4096,
            messages=[{'role': 'user', 'content': content_blocks}],
            extra_headers={'anthropic-beta': 'pdfs-2024-09-25'},
        )
        text = response.content[0].text
        text = text.replace('```json', '').replace('```', '').strip()
        result = json.loads(text)
        return Response({
            'model_id': model_id,
            'analisi': result,
            'fitxers_analitzats': len(fitxers_analisi),
        })
    except json.JSONDecodeError as e:
        return Response({'error': f'Resposta IA no parsejable: {e}'}, status=500)
    except Exception as e:
        return Response({'error': f'Error IA: {e}'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def measurements_chat_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    message = (request.data.get('missatge') or '').strip()
    history = request.data.get('historial', []) or []

    if not message:
        return Response({'error': 'missatge és obligatori'}, status=400)

    from fhort.pom.models import POMMaster

    base_measurements = BaseMeasurement.objects.filter(
        model=model, is_active=True
    ).select_related('pom').order_by('ordre')

    mesures_context = "\n".join([
        f"ID:{bm.id} | CODI:{bm.pom.codi_client} | "
        f"NOM:{bm.pom.nom_client or bm.pom.codi_client} | VALOR:{bm.base_value_cm}cm"
        for bm in base_measurements
    ])

    system_prompt = (
        f"Ets un assistent tècnic de patronatge per al model {model.codi_intern}.\n"
        "Pots fer canvis REALS a les mesures. Quan l'usuari demani un canvi, retorna un JSON d'acció.\n\n"
        f"MESURES ACTUALS:\n{mesures_context}\n\n"
        "Respon SEMPRE amb aquest format JSON:\n"
        "{\n"
        '  "resposta": "text de resposta a l\'usuari en català",\n'
        '  "accions": [\n'
        '    {\n'
        '      "tipus": "ACTUALITZAR|AFEGIR|ELIMINAR|CAP",\n'
        '      "bm_id": <id del BaseMeasurement o null si és nou>,\n'
        '      "pom_codi": "codi del POM",\n'
        '      "valor": <float o null>,\n'
        '      "nom_fitxa": "nomenclatura nova o null"\n'
        '    }\n'
        '  ]\n'
        "}\n\n"
        "Regles:\n"
        "- Si l'usuari corregeix un valor, usa tipus ACTUALITZAR amb el bm_id corresponent\n"
        "- Si demana afegir un POM nou, usa tipus AFEGIR (bm_id=null)\n"
        "- Si demana eliminar, usa tipus ELIMINAR\n"
        "- Si és una pregunta sense acció, usa tipus CAP i accions=[]\n"
        "- Sempre confirma l'acció a la resposta en català"
    )

    import anthropic
    import json
    from django.conf import settings

    messages = history + [{'role': 'user', 'content': message}]

    try:
        client = anthropic.Anthropic(api_key=getattr(settings, 'ANTHROPIC_API_KEY', None))
        response = client.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )
        text = response.content[0].text
        from fhort.models_app.extraction_utils import safe_json_parse
        result = safe_json_parse(text)   # tolerant: fences, prosa, comes finals…

        accions_executades = []
        for accio in result.get('accions', []):
            tipus = accio.get('tipus')
            try:
                if tipus == 'ACTUALITZAR' and accio.get('bm_id'):
                    bm = BaseMeasurement.objects.get(id=accio['bm_id'], model=model)
                    if accio.get('valor') is not None:
                        bm.base_value_cm = float(accio['valor'])
                    if accio.get('nom_fitxa') is not None:
                        bm.nom_fitxa = accio['nom_fitxa']
                    bm.save()
                    accions_executades.append(
                        f"Actualitzat {bm.pom.codi_client} = {bm.base_value_cm}cm"
                    )
                elif tipus == 'AFEGIR' and accio.get('pom_codi'):
                    pom = POMMaster.objects.filter(
                        codi_client__iexact=accio['pom_codi']
                    ).first()
                    if pom and accio.get('valor') is not None:
                        bm, created = BaseMeasurement.objects.update_or_create(
                            model=model, pom=pom,
                            defaults={
                                'base_value_cm': float(accio['valor']),
                                'origen': 'MANUAL',
                                'ordre': base_measurements.count(),
                                # Sprint 5B.1: copy tolerance from the catalogue POM.
                                'tolerancia_minus': pom.tolerancia_default_minus,
                                'tolerancia_plus': pom.tolerancia_default_plus,
                            },
                        )
                        accions_executades.append(
                            f"{'Afegit' if created else 'Actualitzat'} {pom.codi_client}"
                        )
                elif tipus == 'ELIMINAR' and accio.get('bm_id'):
                    bm = BaseMeasurement.objects.get(id=accio['bm_id'], model=model)
                    nom = bm.pom.codi_client
                    bm.is_active = False
                    bm.save()
                    accions_executades.append(f"Eliminat {nom}")
            except Exception as e:
                accions_executades.append(f"Error: {e}")

        mesures_actualitzades = list(
            BaseMeasurement.objects.filter(model=model, is_active=True)
            .select_related('pom').order_by('ordre')
            .values('id', 'pom__codi_client', 'base_value_cm', 'nom_fitxa', 'ordre')
        )

        return Response({
            'resposta': result.get('resposta', ''),
            'accions_executades': accions_executades,
            'mesures_actualitzades': mesures_actualitzades,
            'historial_nou': messages + [{'role': 'assistant', 'content': text}],
        })
    except (ValueError, json.JSONDecodeError) as e:
        return Response({'error': f'Error parsing IA: {e}'}, status=500)
    except Exception as e:
        return Response({'error': f'Error: {e}'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_grading_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    if not model.grading_rule_set_id:
        return Response({'error': 'El model no té GradingRuleSet configurat'}, status=400)
    if not model.size_run_model or not model.base_size_label:
        return Response({'error': 'Cal configurar talles i talla base'}, status=400)

    from fhort.fitting.models import SizeFitting, GradingVersion, GradedSpec
    from fhort.pom.services import generate_graded_specs

    base_measurements_qs = BaseMeasurement.objects.filter(model=model, is_active=True)
    if not base_measurements_qs.exists():
        return Response({'error': 'No hi ha mesures base'}, status=400)

    # Get or create SizeFitting with the real required fields
    sf = SizeFitting.objects.filter(model=model).first()
    if not sf:
        next_num = 1
        codi = f"{model.codi_intern}-SF-{next_num}"
        while SizeFitting.objects.filter(codi=codi).exists():
            next_num += 1
            codi = f"{model.codi_intern}-SF-{next_num}"
        profile = getattr(request.user, 'profile', None)
        try:
            sf = SizeFitting.objects.create(
                model=model,
                numero=next_num,
                codi=codi,
                tipus='SizeSet',
                creat_per=profile,
            )
        except Exception as e:
            return Response({'error': f'Error creant SizeFitting: {e}'}, status=500)

    # Call the existing engine
    try:
        graded_count = generate_graded_specs(sf.id)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        return Response({'error': f'Error generant grading: {e}'}, status=500)

    # Build a measurements-table-style response
    size_run = [s.strip() for s in model.size_run_model.split('·') if s.strip()]
    gv = GradingVersion.objects.filter(size_fitting=sf).order_by('-data').first()

    rows = []
    for bm in (
        BaseMeasurement.objects.filter(model=model, is_active=True)
        .select_related('pom', 'pom__pom_global').order_by('ordre')
    ):
        pom = bm.pom
        pg = getattr(pom, 'pom_global', None)
        graded = {}
        if gv:
            for spec in GradedSpec.objects.filter(grading_version=gv, pom=pom):
                graded[spec.size_label] = (
                    float(spec.graded_value_cm) if spec.graded_value_cm is not None else None
                )
        rows.append({
            'id': bm.id,
            'pom_id': pom.id,
            'pom_code': pom.codi_client,
            'nom_fitxa': bm.nom_fitxa or '',
            'nom_ca': pg.nom_ca if pg else pom.nom_client,
            'nom_en': pg.nom_en if pg else pom.nom_client,
            'base_value_cm': float(bm.base_value_cm) if bm.base_value_cm is not None else None,
            'graded': graded,
            'ordre': bm.ordre,
        })

    return Response({
        'model_id': model_id,
        'graded_count': graded_count,
        'size_run': size_run,
        'base_size': model.base_size_label,
        'rows': rows,
    })


ISO_SHRINKAGE_TABLE = [
    {'id': 'woven_cotton',    'nom': 'Woven Cotton',    'warp': 3.0, 'weft': 3.0},
    {'id': 'woven_linen',     'nom': 'Woven Linen',     'warp': 3.0, 'weft': 3.0},
    {'id': 'woven_viscose',   'nom': 'Woven Viscose',   'warp': 4.0, 'weft': 4.0},
    {'id': 'woven_silk',      'nom': 'Woven Silk',      'warp': 2.0, 'weft': 2.0},
    {'id': 'woven_polyester', 'nom': 'Woven Polyester', 'warp': 1.0, 'weft': 1.0},
    {'id': 'knit_cotton',     'nom': 'Knit Cotton',     'warp': 5.0, 'weft': 5.0},
    {'id': 'knit_jersey',     'nom': 'Knit Jersey',     'warp': 5.0, 'weft': 5.0},
    {'id': 'stretch_knit',    'nom': 'Stretch Knit',    'warp': 8.0, 'weft': 8.0},
    {'id': 'knit_wool',       'nom': 'Knit Wool',       'warp': 6.0, 'weft': 6.0},
    {'id': 'denim',           'nom': 'Denim',           'warp': 5.0, 'weft': 3.0},
    {'id': 'technical',       'nom': 'Technical',       'warp': 0.0, 'weft': 0.0},
]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def iso_shrinkage_view(request):
    return Response(ISO_SHRINKAGE_TABLE)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_fabric_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    fields = ['fabric_main', 'fabric_composition', 'shrinkage_type',
              'shrinkage_warp', 'shrinkage_weft', 'shrinkage_pct', 'fabric_notes',
              'shrinkage_iso_key']
    for f in fields:
        if f in request.data:
            setattr(model, f, request.data[f])
    model.save()
    return Response({'id': model.id, 'fabric_main': model.fabric_main})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consumption_delivery_view(request, model_id):
    """Sprint 4.3: albarà-repositori VIU d'un model.
    Capçalera immutable (ConsumptionRecord) + cos calculat sobre producció
    (ModelTask/TimerEntrada/TaskTransition). Tot intra-tenant. Agregació en
    Python sobre dades prefetchades → una sola consulta (sense N+1).
    Timers oberts (minuts NULL) NO es compten (B1-a: només temps consolidat)."""
    try:
        model = Model.objects.select_related('consumption_record').prefetch_related(
            'model_tasks__task_type',
            'model_tasks__timers__tecnic',
            'model_tasks__transitions__by',
        ).get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    rec = getattr(model, 'consumption_record', None)
    if rec is None:
        return Response({'merited': False, 'model_id': model.id})

    steps = []
    total_minutes = 0
    rectifications = 0
    per_tech = {}   # tecnic_id -> {'label':..., 'minutes':int}
    history = []

    tasks = sorted(model.model_tasks.all(), key=lambda t: (t.order, t.id))
    for mt in tasks:
        task_minutes = 0
        for tm in mt.timers.all():
            if tm.minuts is None:        # timer obert → no consolidat (B1-a)
                continue
            task_minutes += tm.minuts
            total_minutes += tm.minuts
            if tm.tecnic_id is not None:
                label = (tm.tecnic.nom_complet or tm.tecnic.user.get_username()) if tm.tecnic else str(tm.tecnic_id)
                slot = per_tech.setdefault(tm.tecnic_id, {'technician_id': tm.tecnic_id, 'label': label, 'minutes': 0})
                slot['minutes'] += tm.minuts
        steps.append({
            'task_type': mt.task_type.name if mt.task_type_id else None,
            'status': mt.status,
            'minutes': task_minutes,
            'started_at': mt.started_at,
            'finished_at': mt.finished_at,
        })
        for tr in mt.transitions.all():
            if tr.from_status == 'Done' and tr.to_status == 'InProgress':
                rectifications += 1
            by_label = None
            if tr.by_id is not None and tr.by:
                by_label = tr.by.nom_complet or tr.by.user.get_username()
            history.append({
                'task_type': mt.task_type.name if mt.task_type_id else None,
                'from': tr.from_status,
                'to': tr.to_status,
                'by': by_label,
                'at': tr.at,
            })

    history.sort(key=lambda h: (h['at'] is None, h['at']))

    return Response({
        'merited': True,
        'model_id': model.id,
        'header': {
            'code': rec.code_snapshot,
            'name': rec.name_snapshot,
            'period': rec.period,
            'merited_at': rec.merited_at,
            'opaque_ref': str(rec.opaque_ref),
        },
        'steps': steps,
        'totals': {'total_minutes': total_minutes, 'rectifications': rectifications},
        'per_technician': list(per_tech.values()),
        'history': history,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_dashboard_view(request, model_id):
    """Dashboard del model — PEÇA B1 (versió mínima: Q1 + Q4).

    Endpoint compositor read-only que agrega, per a UN model, l'estat de treball
    (Q1: on sóc / què bloqueja / artefactes vigents) i les tasques (Q4: què puc fer).
    NO inclou timeline (Q2), alertes/handoffs (Q3) ni esforç/cost (⑤ M, que ja serveix
    consumption_delivery_view → no es duplica). Tot intra-tenant, cap escriptura a BD.

    Degradació amb gràcia: un model nou (sense tasques/SF/fitxa/base) retorna 200 amb els
    sub-blocs en null/buit/0, MAI un 500. Reusa els resolutors canònics ja existents."""
    from django.shortcuts import get_object_or_404
    from fhort.tasks.services_d import model_ready_for_gate
    from fhort.fitting.services import _resolve_working_size_fitting, _active_grading_version

    model = get_object_or_404(
        Model.objects.prefetch_related('model_tasks__task_type'),
        id=model_id,
    )

    # --- Q1: on sóc / què bloqueja ---
    tasks = sorted(model.model_tasks.all(), key=lambda t: (t.order, t.id))
    tasks_open = sum(1 for t in tasks if t.status != 'Done')

    phases = [c[0] for c in Model.FASE_CHOICES]
    try:
        idx = phases.index(model.fase_actual)
        next_phase = phases[idx + 1] if idx + 1 < len(phases) else None
    except ValueError:
        next_phase = None

    on_soc = {
        'fase': model.fase_actual,
        'estat': model.estat,
        'ready_for_gate': model_ready_for_gate(model.id),
        'next_phase': next_phase,
        'blockers': {'tasks_open': tasks_open},
    }

    # --- Q1: artefactes vigents (cada accés a una relació opcional tolera absència) ---
    ts = getattr(model, 'tech_sheet', None)   # reverse O2O: None si no existeix (igual que consumption_record)
    fitxa = {'versio': ts.versio, 'estat': ts.estat} if ts is not None else None

    grading = None
    sf = _resolve_working_size_fitting(model)   # resolutor canònic: grading és per SizeFitting, no per Model
    if sf is not None:
        gv = _active_grading_version(sf)
        if gv is not None:
            grading = {
                'version_number': gv.version_number,
                'aprovada': gv.aprovada,
                'size_fitting_id': sf.id,
            }

    n_active = model.base_measurements.filter(
        is_active=True, base_value_cm__isnull=False,
    ).count()
    base = {'base_size_label': model.base_size_label, 'n_active': n_active}

    artefactes_vigents = {'fitxa': fitxa, 'grading': grading, 'base': base}

    # --- Q4: tasques (llista saltable) ---
    tasques = [{
        'id': t.id,
        'task_type': t.task_type.name if t.task_type_id else None,
        'task_type_code': t.task_type.code if t.task_type_id else None,
        'status': t.status,
        'assignee_id': t.assignee_id,
        'order': t.order,
    } for t in tasks]

    return Response({
        'model_id': model.id,
        'on_soc': on_soc,
        'artefactes_vigents': artefactes_vigents,
        'tasques': tasques,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def registre_activitat_view(request):
    """Sprint 4.5: llista global de ConsumptionRecord del tenant.
    Filtres: ?period=YYYY-MM &tecnic_id=<int> &page=<int> &page_size=<int>
    Retorna: { count, totals:{models,total_minutes,avg_per_model,avg_per_step}, results:[...] }"""
    from fhort.models_app.models import ConsumptionRecord

    period   = request.query_params.get('period')
    tecnic_id = request.query_params.get('tecnic_id')
    page     = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 25)), 100)

    qs = ConsumptionRecord.objects.select_related('model__customer').prefetch_related(
        'model__model_tasks__timers',
        'model__model_tasks',
    ).order_by('-merited_at')

    if period:
        qs = qs.filter(period=period)
    if tecnic_id:
        qs = qs.filter(
            model__model_tasks__timers__tecnic_id=tecnic_id,
            model__model_tasks__timers__minuts__isnull=False,
        ).distinct()
    task_type_id = request.query_params.get('task_type_id')
    if task_type_id:
        qs = qs.filter(
            model__model_tasks__task_type_id=task_type_id,
            model__model_tasks__timers__minuts__isnull=False,
        ).distinct()

    # Totalitzadors sobre el queryset filtrat (en Python, sobre slice petit)
    all_ids = list(qs.values_list('id', flat=True))
    total_models = len(all_ids)
    total_minutes = 0
    total_steps = 0
    for rec in qs.prefetch_related('model__model_tasks__timers'):
        for mt in rec.model.model_tasks.all():
            total_steps += 1
            for tm in mt.timers.all():
                if tm.minuts is not None:
                    total_minutes += tm.minuts

    avg_per_model = round(total_minutes / total_models, 1) if total_models else 0
    avg_per_step  = round(total_minutes / total_steps,  1) if total_steps  else 0

    # Paginació manual
    start = (page - 1) * page_size
    page_qs = qs[start:start + page_size]

    results = []
    for rec in page_qs:
        model = rec.model
        mins = sum(
            tm.minuts for mt in model.model_tasks.all()
            for tm in mt.timers.all() if tm.minuts is not None
        )
        steps = model.model_tasks.count()
        results.append({
            'id': model.id,
            'code': rec.code_snapshot,
            'name': rec.name_snapshot,
            'period': rec.period,
            'merited_at': rec.merited_at,
            'total_minutes': mins,
            'steps': steps,
            'opaque_ref': str(rec.opaque_ref),
        })

    return Response({
        'count': total_models,
        'totals': {
            'models': total_models,
            'total_minutes': total_minutes,
            'avg_per_model': avg_per_model,
            'avg_per_step': avg_per_step,
        },
        'results': results,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_pom_regim_view(request, model_id, pom_id):
    """PG-4b-3a — UPSERT del règim (logica) d'UNA ModelGradingRule resident per (model, pom).

    Body: {logica: 'LINEAR'|'STEP'}. Si la resident existeix → actualitza logica + origen='MANUAL'.
    Si no → la materialitza copiant els camps canònics del fallback GradingRule del rule_set
    (segur: amb logica='STEP' el motor ignora increment_base — es conserva latent). Sense fallback
    → 400 (no es crea cap resident buida). Innocu sobre el grading persistent (no toca
    measurements_version / GradedSpec / GradingVersion; només el proper generate_graded_specs).
    """
    from fhort.models_app.models import ModelGradingRule
    from fhort.pom.models import GradingRule

    logica = (request.data.get('logica') or '').strip().upper()
    if logica not in ('LINEAR', 'STEP'):
        return Response({'detail': "logica ha de ser 'LINEAR' o 'STEP'."}, status=400)

    model = Model.objects.filter(pk=model_id).first()
    if model is None:
        return Response({'detail': 'Model no trobat.'}, status=404)

    with transaction.atomic():
        rule = ModelGradingRule.objects.filter(model=model, pom_id=pom_id).first()
        if rule is not None:
            rule.logica = logica
            rule.origen = 'MANUAL'
            rule.save(update_fields=['logica', 'origen', 'updated_at'])
        else:
            src = (GradingRule.objects.filter(
                       rule_set_id=model.grading_rule_set_id, pom_id=pom_id).first()
                   if model.grading_rule_set_id else None)
            if src is None:
                return Response(
                    {'detail': "No hi ha regla de fallback per a aquest POM; cal definir-la "
                               "al catàleg abans de triar-ne el règim."}, status=400)
            rule = ModelGradingRule.objects.create(
                model=model, pom_id=pom_id, logica=logica, origen='MANUAL', actiu=True,
                increment=src.increment, valors_step=src.valors_step,
                increment_base=src.increment_base, increment_break=src.increment_break,
                talla_break_label=src.talla_break_label, talla_break_pos=src.talla_break_pos,
            )

    return Response({
        'model': model.id,
        'pom': rule.pom_id,
        'logica': rule.logica,
        'origen': rule.origen,
        'increment_base': float(rule.increment_base) if rule.increment_base is not None else None,
        'increment_break': float(rule.increment_break) if rule.increment_break is not None else None,
        'talla_break_label': rule.talla_break_label,
    })
