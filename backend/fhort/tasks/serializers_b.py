from rest_framework import serializers
from .models import (TaskType, ModelTask, Supplier, Production,
                     GarmentTypeItem, TaskTimeEstimate)
from .services_c import rectification_count


class TaskTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskType
        fields = ['id', 'code', 'name', 'default_order', 'active']


class ModelTaskSerializer(serializers.ModelSerializer):
    task_type_code = serializers.CharField(source='task_type.code', read_only=True)
    task_type_name = serializers.CharField(source='task_type.name', read_only=True)
    rectifications = serializers.SerializerMethodField()

    class Meta:
        model = ModelTask
        fields = ['id', 'model', 'task_type', 'task_type_code', 'task_type_name',
                  'status', 'assignee', 'order', 'created_at', 'updated_at',
                  'started_at', 'finished_at', 'estimated_minutes', 'rectifications']
        # started_at/finished_at els gestiona la transició; estimated_minutes és snapshot → read-only.
        read_only_fields = ['created_at', 'updated_at',
                            'started_at', 'finished_at', 'estimated_minutes']

    def get_rectifications(self, obj):
        return rectification_count(obj)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'type', 'active']


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
        fields = ['id', 'garment_type', 'code', 'name', 'complexity_order', 'active']


class TaskTimeEstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskTimeEstimate
        fields = ['id', 'garment_type_item', 'task_type', 'estimated_minutes']
