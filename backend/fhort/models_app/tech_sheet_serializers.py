"""Serializer de la fitxa tècnica (estat + lock). Mínim: prou per pintar la capçalera
de l'editor i el badge de lock."""
from rest_framework import serializers

from .tech_sheet_models import TechSheet


class TechSheetSerializer(serializers.ModelSerializer):
    model_id = serializers.IntegerField(source='model.id', read_only=True)
    locked_by_id = serializers.IntegerField(source='locked_by.id', read_only=True, default=None)
    locked_by_username = serializers.SerializerMethodField()

    class Meta:
        model = TechSheet
        fields = ['id', 'model_id', 'estat', 'locked_by_id', 'locked_by_username', 'updated_at']

    def get_locked_by_username(self, obj):
        return obj.locked_by.get_username() if obj.locked_by_id else None
