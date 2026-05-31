from rest_framework import serializers
from .models import TaskType, ModelTask
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
                  'rectifications']
        read_only_fields = ['created_at', 'updated_at']

    def get_rectifications(self, obj):
        return rectification_count(obj)
