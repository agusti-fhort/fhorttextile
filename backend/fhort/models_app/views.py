import datetime

from django.db import connection
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import BaseMeasurement, Model, ModelFitxer
from .serializers import (
    BaseMeasurementSerializer,
    ModelDetailSerializer,
    ModelFitxerSerializer,
    ModelListSerializer,
)


class ModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estat', 'fase_actual', 'garment_type', 'responsable']
    search_fields = ['codi_intern', 'codi_client', 'nom_prenda']
    ordering_fields = ['prioritat', 'data_objectiu', 'data_entrada']
    ordering = ['-prioritat']
    queryset = Model.objects.all()

    def get_queryset(self):
        # django-tenants ja restringeix les queries a l'esquema actual del tenant
        # via la connection. Al schema 'public' no hi ha taules de models, però
        # retornem un queryset buit per evitar errors a vistes mal encaminades.
        if getattr(connection, 'schema_name', None) == 'public':
            return Model.objects.none()
        return (
            Model.objects
            .select_related('garment_type', 'garment_group',
                            'responsable', 'responsable__user',
                            'size_system', 'talla_base', 'grading_rule_set')
            .all()
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return ModelListSerializer
        return ModelDetailSerializer


class ModelFitxerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ModelFitxerSerializer
    queryset = ModelFitxer.objects.select_related('model', 'pujat_per').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'categoria', 'enviat_ia']
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
        # Al schema 'public' no hi ha dades de tenant — retorna queryset buit.
        if getattr(connection, 'schema_name', None) == 'public':
            return BaseMeasurement.objects.none()
        return super().get_queryset()



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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_model_wizard(request):
    year = request.data.get('year')
    season = request.data.get('season')
    ref_client = request.data.get('ref_client', '')
    nom_prenda = request.data.get('nom_prenda', '')
    descripcio = request.data.get('descripcio', '')

    if not year or not season:
        return Response({'error': 'year i season són obligatoris'}, status=400)

    prefix = 'FTT'
    year_short = str(year)[-2:]
    base = f"{prefix}-{season}{year_short}-"

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT codi_intern FROM models_app_model "
            "WHERE codi_intern LIKE %s "
            "ORDER BY codi_intern DESC LIMIT 1",
            [base + '%']
        )
        row = cursor.fetchone()
    next_num = (int(row[0].split('-')[-1]) + 1) if row else 1
    codi_intern = f"{base}{str(next_num).zfill(4)}"

    model = Model.objects.create(
        codi_intern=codi_intern,
        codi_client=ref_client,
        codi_tenant=prefix,
        any=int(year),
        temporada=season,
        sequencial=next_num,
        nom_prenda=nom_prenda or None,
        descripcio=descripcio or None,
        estat='Nou',
    )
    return Response({'id': model.id, 'codi_intern': model.codi_intern}, status=201)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_model_step2(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    d = request.data
    if d.get('garment_type_id'):
        from fhort.pom.models import GarmentType
        try:
            model.garment_type = GarmentType.objects.get(id=d['garment_type_id'])
        except GarmentType.DoesNotExist:
            return Response({'error': 'GarmentType no trobat'}, status=400)
    if d.get('size_system_id'):
        from fhort.pom.models import SizeSystem
        try:
            model.size_system = SizeSystem.objects.get(id=d['size_system_id'])
        except SizeSystem.DoesNotExist:
            return Response({'error': 'SizeSystem no trobat'}, status=400)
    if d.get('grading_rule_set_id'):
        from fhort.pom.models import GradingRuleSet
        try:
            model.grading_rule_set = GradingRuleSet.objects.get(id=d['grading_rule_set_id'])
        except GradingRuleSet.DoesNotExist:
            pass
    if d.get('target'):
        model.target = d['target']
    if d.get('construction'):
        model.construction = d['construction']
    if d.get('size_run'):
        model.size_run_model = d['size_run']
    if d.get('base_size'):
        model.base_size_label = d['base_size']

    model.save()
    return Response({'id': model.id, 'codi_intern': model.codi_intern})
