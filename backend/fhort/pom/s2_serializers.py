"""
fhort/pom/s2_serializers.py — Sprint S2 serializers
"""
from rest_framework import serializers


class TargetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    codi = serializers.CharField()
    nom_en = serializers.CharField()
    nom_cat = serializers.CharField()
    nom_es = serializers.CharField()
    age_min_months = serializers.IntegerField(allow_null=True)
    age_max_months = serializers.IntegerField(allow_null=True)
    primary_dimension = serializers.CharField()
    display_order = serializers.IntegerField()
    is_adult = serializers.BooleanField()
    is_baby = serializers.BooleanField()


class ConstructionTypeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    codi = serializers.CharField()
    nom_en = serializers.CharField()
    nom_cat = serializers.CharField()
    mesures_en_mitja = serializers.BooleanField()
    tolerancia_critica_cm = serializers.DecimalField(max_digits=4, decimal_places=2)
    display_order = serializers.IntegerField()


class SizeSystemLightSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    codi = serializers.CharField()
    nom = serializers.CharField()
    base_unit = serializers.CharField()
    norma_ref = serializers.CharField()


class SizeDefinitionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    size_label = serializers.CharField()
    display_order = serializers.IntegerField()
    body_height_cm = serializers.FloatField(allow_null=True)
    body_bust_cm = serializers.FloatField(allow_null=True)
    age_months_min = serializers.IntegerField(allow_null=True)
    age_months_max = serializers.IntegerField(allow_null=True)


class GradingRuleSetLightSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nom = serializers.CharField()
    codi_sistema = serializers.CharField()
    is_system_default = serializers.BooleanField()
    version_number = serializers.IntegerField()
    has_custom_version = serializers.SerializerMethodField()

    def get_has_custom_version(self, obj):
        return hasattr(obj, 'versions') and obj.versions.exists()


class GradingRuleLightSerializer(serializers.Serializer):
    pom_codi = serializers.SerializerMethodField()
    pom_nom_en = serializers.SerializerMethodField()
    logica = serializers.CharField()
    increment = serializers.FloatField()

    def get_pom_codi(self, obj):
        return getattr(obj.pom, 'codi_intern', '') if obj.pom_id else ''

    def get_pom_nom_en(self, obj):
        return getattr(obj.pom, 'nom_en', '') if obj.pom_id else ''


class SizingProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    target = TargetSerializer()
    construction = ConstructionTypeSerializer()
    fit_type_nom = serializers.SerializerMethodField()
    size_system = SizeSystemLightSerializer()
    grading_rule_set = GradingRuleSetLightSerializer()
    is_default = serializers.BooleanField()
    is_custom = serializers.SerializerMethodField()
    version = serializers.IntegerField()

    size_definitions = serializers.SerializerMethodField()
    grading_rules_preview = serializers.SerializerMethodField()

    def get_fit_type_nom(self, obj):
        return obj.fit_type.nom_en if obj.fit_type_id else ''

    def get_is_custom(self, obj):
        return obj.parent_profile_id is not None

    def get_size_definitions(self, obj):
        if not obj.size_system_id:
            return []
        try:
            from fhort.pom.models import SizeDefinition
            defs = SizeDefinition.objects.filter(
                size_system=obj.size_system
            ).order_by('display_order')
            return SizeDefinitionSerializer(defs, many=True).data
        except Exception:
            return []

    def get_grading_rules_preview(self, obj):
        if not obj.grading_rule_set_id:
            return []
        try:
            from fhort.pom.models import GradingRule
            rules = GradingRule.objects.filter(
                rule_set=obj.grading_rule_set,
                actiu=True,
                pom__is_key_measure=True,
            ).select_related('pom')[:5]
            return GradingRuleLightSerializer(rules, many=True).data
        except Exception:
            return []


class TenantConfigSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    unitat_mesura = serializers.ChoiceField(choices=['CM', 'INCH'])
    norma_referencia = serializers.ChoiceField(choices=['ISO_8559', 'ASTM_D13'])
    nom_empresa = serializers.CharField(allow_blank=True)
    logo_url = serializers.URLField(allow_blank=True)


class POMGlobalLightSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    codi_intern = serializers.CharField()
    nom_en = serializers.CharField()
    nom_cat = serializers.CharField()
    categoria_nom = serializers.SerializerMethodField()
    is_key_measure = serializers.BooleanField()
    htm_metode_en = serializers.CharField()

    def get_categoria_nom(self, obj):
        return obj.categoria.nom_en if obj.categoria_id else ''
