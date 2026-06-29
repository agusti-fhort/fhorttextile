"""Serializer de plantilla de fitxa per Customer (TechSheetTemplate).

NOTA (Fase 2 .ftt): el serializer de la fitxa per-model (TechSheet) s'ha jubilat amb el model;
l'editor treballa sobre documents .ftt (ModelFitxerSerializer). Queda només la plantilla."""
from rest_framework import serializers

from .tech_sheet_models import TechSheetTemplate


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
