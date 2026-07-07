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


class FitTypeSerializer(serializers.Serializer):
    codi = serializers.CharField()
    nom_en = serializers.CharField()
    display_order = serializers.IntegerField()


class SizeSystemLightSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    codi = serializers.CharField()
    nom = serializers.CharField()
    base_unit = serializers.CharField()
    norma_ref = serializers.CharField()


class SizeDefinitionLightSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    size_label = serializers.CharField(source='etiqueta')
    display_order = serializers.IntegerField(source='ordre')
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
    # R2 — codis de document pendents de vincular, persistits al crear el run.
    pendents_vincular = serializers.JSONField(read_only=True)

    def get_has_custom_version(self, obj):
        return hasattr(obj, 'versions') and obj.versions.exists()


class GradingRuleLightSerializer(serializers.Serializer):
    pom_codi = serializers.SerializerMethodField()
    pom_nom_en = serializers.SerializerMethodField()
    logica = serializers.CharField()
    increment = serializers.FloatField()

    def get_pom_codi(self, obj):
        if not obj.pom_id:
            return ''
        if getattr(obj.pom, 'pom_global_id', None):
            return obj.pom.pom_global.codi
        return getattr(obj.pom, 'codi_client', '') or ''

    def get_pom_nom_en(self, obj):
        if not obj.pom_id:
            return ''
        if getattr(obj.pom, 'pom_global_id', None):
            return obj.pom.pom_global.nom_en
        return getattr(obj.pom, 'nom_client', '') or ''


class SizingProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    target = TargetSerializer()
    construction = ConstructionTypeSerializer()
    fit_type_nom = serializers.SerializerMethodField()
    fit_type_codi = serializers.SerializerMethodField()
    size_system = SizeSystemLightSerializer()
    grading_rule_set = GradingRuleSetLightSerializer()
    is_default = serializers.BooleanField()
    is_custom = serializers.SerializerMethodField()
    version = serializers.IntegerField()

    # Size Map Setup — distingir runs de client vs sistemes canònics al ModelWizard.
    size_system_customer_codi = serializers.SerializerMethodField()
    size_system_parent_nom = serializers.SerializerMethodField()

    size_definitions = serializers.SerializerMethodField()
    grading_rules_preview = serializers.SerializerMethodField()

    def get_fit_type_nom(self, obj):
        return obj.fit_type.nom_en if obj.fit_type_id else ''

    def get_fit_type_codi(self, obj):
        return obj.fit_type.codi if obj.fit_type_id else None

    def get_size_system_customer_codi(self, obj):
        return (obj.size_system.customer_codi or '') if obj.size_system_id else ''

    def get_size_system_parent_nom(self, obj):
        if obj.size_system_id and obj.size_system.parent_id:
            return obj.size_system.parent.nom
        return ''

    def get_is_custom(self, obj):
        return obj.parent_profile_id is not None

    def get_size_definitions(self, obj):
        if not obj.size_system_id:
            return []
        try:
            from fhort.pom.models import SizeDefinition
            defs = SizeDefinition.objects.filter(
                size_system=obj.size_system
            ).order_by('ordre')
            return SizeDefinitionLightSerializer(defs, many=True).data
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
            ).select_related('pom', 'pom__pom_global').order_by('pom__codi_client')[:5]
            return GradingRuleLightSerializer(rules, many=True).data
        except Exception:
            return []


class TenantConfigSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    unitat_mesura = serializers.ChoiceField(choices=['CM', 'INCH'])
    norma_referencia = serializers.ChoiceField(choices=['ISO_8559', 'ASTM_D13'])
    nom_empresa = serializers.CharField(allow_blank=True)
    logo_url = serializers.URLField(allow_blank=True)
    # Comercial Studio (B1) — tarifa interna de cost per hora (plana). ≠ Product.sale_rate.
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2,
                                           required=False, allow_null=True)


class POMGlobalLightSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    codi = serializers.CharField()
    nom_en = serializers.CharField()
    nom_ca = serializers.CharField()
    nom_es = serializers.CharField()
    categoria = serializers.CharField()
    descripcio_en = serializers.CharField()
    actiu = serializers.BooleanField()
