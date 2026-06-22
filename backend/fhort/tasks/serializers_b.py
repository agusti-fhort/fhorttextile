from rest_framework import serializers
from .models import (TaskType, ModelTask, Supplier, Production,
                     GarmentTypeItem, TaskTimeEstimate, Customer)
from .services_c import rectification_count


class TaskTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskType
        fields = ['id', 'code', 'name', 'default_order', 'active']


class ModelTaskSerializer(serializers.ModelSerializer):
    task_type_code = serializers.CharField(source='task_type.code', read_only=True)
    task_type_name = serializers.CharField(source='task_type.name', read_only=True)
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    rectifications = serializers.SerializerMethodField()

    class Meta:
        model = ModelTask
        fields = ['id', 'model', 'model_codi', 'task_type', 'task_type_code', 'task_type_name',
                  'status', 'assignee', 'order', 'created_at', 'updated_at',
                  'started_at', 'finished_at', 'estimated_minutes', 'rectifications',
                  'planned_start', 'planned_end', 'planned_locked']
        # started_at/finished_at els gestiona la transició; estimated_minutes és snapshot → read-only.
        # planned_* els escriu el MOTOR (planning), no el client → read-only.
        # ⚠️ Fus horari: aquí planned_start/end surten en UTC (USE_TZ=True). El front de
        # planificació NO ha de barrejar aquesta font amb les respostes del motor
        # (plan/compute|preview|apply, que van en ISO LOCAL). Aquests camps són per a
        # referència/llista; el Gantt pinta des de plan/compute (local).
        read_only_fields = ['created_at', 'updated_at',
                            'started_at', 'finished_at', 'estimated_minutes',
                            'planned_start', 'planned_end', 'planned_locked']

    def get_rectifications(self, obj):
        return rectification_count(obj)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'type', 'active']


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        # logo: ImageField → URL (absoluta si el ViewSet passa `request` al context, que és
        # el cas per defecte de ModelViewSet). read_only: s'escriu via l'acció upload-logo.
        fields = ['id', 'codi', 'nom', 'active', 'is_self', 'logo']
        read_only_fields = ['logo']


class ProductionSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = Production
        fields = ['id', 'model', 'phase', 'supplier', 'supplier_name', 'status',
                  'requested_at', 'expected_at', 'delivered_at', 'requested_by', 'notes']
        read_only_fields = ['requested_at', 'delivered_at', 'status', 'requested_by']


class GarmentTypeItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarmentTypeItem
        # Sprint Llibreria d'Items (B3a): exposa el context de grading de l'Item (FK ruleset) i
        # la talla base, escrivibles per la pàgina d'autoria (Fase B). Tots dos nullable.
        fields = ['id', 'garment_type', 'code', 'name', 'complexity_order', 'active',
                  'grading_rule_set', 'base_size_definition']

    def validate(self, attrs):
        # B3a — DRF no crida Model.clean() sol; l'invoquem aquí perquè el constrenyiment d'A3
        # (base_size_definition.size_system == grading_rule_set.size_system) es validi al desar
        # via serializer. Fusiona els attrs entrants amb la instància existent (PATCH parcial) i
        # delega al clean() del model (font única; cas null = skip, sense error).
        from django.core.exceptions import ValidationError as DjangoValidationError
        grs = attrs.get('grading_rule_set', getattr(self.instance, 'grading_rule_set', None))
        bsd = attrs.get('base_size_definition', getattr(self.instance, 'base_size_definition', None))
        probe = GarmentTypeItem(grading_rule_set=grs, base_size_definition=bsd)
        try:
            probe.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                getattr(e, 'message_dict', None) or {'base_size_definition': e.messages})
        return attrs


class TaskTimeEstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskTimeEstimate
        fields = ['id', 'garment_type_item', 'task_type', 'estimated_minutes']
