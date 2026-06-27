"""Serializer de la fitxa tècnica (estat + lock). Mínim: prou per pintar la capçalera
de l'editor i el badge de lock."""
from rest_framework import serializers

from .tech_sheet_models import TechSheet, TechSheetTemplate


class TechSheetSerializer(serializers.ModelSerializer):
    model_id = serializers.IntegerField(source='model.id', read_only=True)
    locked_by_id = serializers.IntegerField(source='locked_by.id', read_only=True, default=None)
    locked_by_username = serializers.SerializerMethodField()
    has_content = serializers.SerializerMethodField()
    num_pages = serializers.SerializerMethodField()

    class Meta:
        model = TechSheet
        fields = ['id', 'model_id', 'versio', 'template_json',
                  'locked_by_id', 'locked_by_username', 'updated_at',
                  'num_pages', 'has_content']

    def get_locked_by_username(self, obj):
        return obj.locked_by.get_username() if obj.locked_by_id else None

    def get_has_content(self, obj):
        tj = obj.template_json or {}
        pages = tj.get('pages') or []
        return len(pages) > 0 or bool(tj)

    def get_num_pages(self, obj):
        tj = obj.template_json or {}
        pages = tj.get('pages') or []
        return len(pages)


class TechSheetTemplateSerializer(serializers.ModelSerializer):
    customer_nom = serializers.CharField(source='customer.nom', read_only=True)
    has_content = serializers.SerializerMethodField()
    num_pages = serializers.SerializerMethodField()

    class Meta:
        model = TechSheetTemplate
        fields = ['id', 'customer', 'customer_nom', 'nom',
                  'template_json', 'has_content', 'num_pages',
                  'actiu', 'updated_at']

    def get_has_content(self, obj):
        tj = obj.template_json or {}
        pages = tj.get('pages')
        return bool(pages)

    def get_num_pages(self, obj):
        tj = obj.template_json or {}
        pages = tj.get('pages')
        return len(pages) if pages else 0
