import datetime

from django.db import connection, transaction
from rest_framework import viewsets
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import BaseMeasurement, GarmentSet, Model, ModelFitxer
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def next_model_ref(request):
    year = request.GET.get('year', str(datetime.date.today().year))
    season = request.GET.get('season', 'SS')
    prefix = 'FTT'
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
    from fhort.pom.models import GarmentType, SizeSystem, GradingRuleSet
    from fhort.tasks.models import GarmentTypeItem
    fields = {}
    if d.get('garment_type_id'):
        try:
            fields['garment_type'] = GarmentType.objects.get(id=d['garment_type_id'])
        except GarmentType.DoesNotExist:
            return None, 'GarmentType no trobat'
    if d.get('garment_type_item_id'):
        try:
            fields['garment_type_item'] = GarmentTypeItem.objects.get(id=d['garment_type_item_id'])
        except GarmentTypeItem.DoesNotExist:
            return None, 'GarmentTypeItem no trobat'
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
    nom_prenda = request.data.get('nom_prenda', '')
    descripcio = request.data.get('descripcio', '')
    collection = request.data.get('collection', '')
    # Sprint A — multi-piece (immutable after creation)
    is_multipiece = bool(request.data.get('is_multipiece', False))
    num_pieces = request.data.get('num_pieces')

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

    prefix = 'FTT'
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
            codi_tenant=prefix,
            any=int(year),
            temporada=season,
            sequencial=next_num,
            nom_prenda=nom_prenda or None,
            descripcio=descripcio or None,
            collection=collection or '',
            created_by=creator,
            estat='Nou',
            **garment_fields,
        )
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
                codi_tenant=prefix,
                any=int(year),
                temporada=season,
                sequencial=next_num,
                nom_prenda=nom_prenda or None,
                descripcio=descripcio or None,
                collection=collection or '',
                created_by=creator,
                estat='Nou',
                garment_set=garment_set,
                piece_number=i,
                **garment_fields,
            )
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
    return Response({'id': model.id, 'codi_intern': model.codi_intern})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def suggested_poms_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    if not model.garment_type:
        return Response({'poms': [], 'warning': 'Garment type no definit'})

    from fhort.pom.models import GarmentPOMMap

    maps = GarmentPOMMap.objects.filter(
        garment_type=model.garment_type,
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
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_measurements_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    measurements = request.data.get('measurements', [])
    if not measurements:
        return Response({'error': 'measurements és obligatori'}, status=400)

    from fhort.pom.models import POMMaster
    from fhort.models_app.models import BaseMeasurement

    created = updated = 0
    errors = []

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
                    # Sprint 5B.1: copy tolerance from the catalogue POM.
                    'tolerancia_minus': pom.tolerancia_default_minus,
                    'tolerancia_plus': pom.tolerancia_default_plus,
                }
            )
            if was_created: created += 1
            else: updated += 1
        except POMMaster.DoesNotExist:
            errors.append(f'POMMaster {pom_id} no trobat')

    try:
        from fhort.fitting.models import SizeFitting, GradingVersion, GradedSpec
        from fhort.pom.models import GradingRule, GradingRuleSet

        sf, _ = SizeFitting.objects.get_or_create(
            model=model,
            defaults={'size_system': model.size_system}
        )

        gv = GradingVersion.objects.create(size_fitting=sf)

        size_run = []
        if model.size_run_model:
            size_run = [s.strip() for s in model.size_run_model.split('·') if s.strip()]

        base_size = model.base_size_label

        all_bm = BaseMeasurement.objects.filter(model=model, is_active=True)
        grading_rule_set = model.grading_rule_set

        for bm in all_bm:
            base_val = float(bm.base_value_cm) if bm.base_value_cm else 0

            for size_label in size_run:
                if size_label == base_size:
                    graded_val = base_val
                else:
                    delta = 0
                    if grading_rule_set:
                        rule = GradingRule.objects.filter(
                            rule_set=grading_rule_set,
                            pom=bm.pom,
                            size_label=size_label,
                        ).first()
                        if rule:
                            delta = float(rule.increment_cm or 0)
                    graded_val = base_val + delta

                GradedSpec.objects.update_or_create(
                    grading_version=gv,
                    pom=bm.pom,
                    size_label=size_label,
                    defaults={'graded_value_cm': graded_val}
                )
    except Exception:
        pass

    return Response({'created': created, 'updated': updated, 'errors': errors},
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
        text = response.content[0].text.replace('```json', '').replace('```', '').strip()
        result = json.loads(text)

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
    except json.JSONDecodeError as e:
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
              'shrinkage_warp', 'shrinkage_weft', 'shrinkage_pct', 'fabric_notes']
    for f in fields:
        if f in request.data:
            setattr(model, f, request.data[f])
    model.save()
    return Response({'id': model.id, 'fabric_main': model.fabric_main})
