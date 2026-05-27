from rest_framework import serializers

from .models import (
    GarmentGroup,
    GarmentType,
    GarmentTypeGlobal,
    GradingRule,
    GradingRuleSet,
    POMCategory,
    POMGlobal,
    POMMaster,
    SizeDefinition,
    SizeSystem,
)


class GarmentGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarmentGroup
        fields = '__all__'


class POMCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = POMCategory
        fields = '__all__'


class POMMasterSerializer(serializers.ModelSerializer):
    pom_global_codi = serializers.CharField(source='pom_global.codi', read_only=True)
    pom_global_nom = serializers.CharField(source='pom_global.nom_en', read_only=True)

    class Meta:
        model = POMMaster
        fields = '__all__'


class SizeDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeDefinition
        fields = '__all__'


class SizeSystemSerializer(serializers.ModelSerializer):
    talles = SizeDefinitionSerializer(many=True, read_only=True)

    class Meta:
        model = SizeSystem
        fields = ('id', 'codi', 'nom', 'descripcio', 'actiu', 'talles')


class GarmentTypeSerializer(serializers.ModelSerializer):
    global_codi = serializers.CharField(source='garment_type_global.codi', read_only=True)
    global_nom = serializers.CharField(source='garment_type_global.nom_en', read_only=True)

    class Meta:
        model = GarmentType
        fields = '__all__'
        read_only_fields = ['is_system']


class GradingRuleSerializer(serializers.ModelSerializer):
    pom_codi = serializers.CharField(source='pom.codi_client', read_only=True)
    pom_nom = serializers.CharField(source='pom.nom_client', read_only=True)
    pom_abbreviation = serializers.SerializerMethodField()
    talla_base_etiqueta = serializers.CharField(source='talla_base.etiqueta', read_only=True)

    def get_pom_abbreviation(self, obj):
        if obj.pom and obj.pom.pom_global:
            return obj.pom.pom_global.abbreviation
        return obj.pom.codi_client if obj.pom else None

    class Meta:
        model = GradingRule
        fields = '__all__'


class GradingRuleSetSerializer(serializers.ModelSerializer):
    garment_group_nom = serializers.CharField(source='garment_group.nom', read_only=True)
    size_system_codi = serializers.CharField(source='size_system.codi', read_only=True)
    size_system_nom = serializers.CharField(source='size_system.nom', read_only=True)
    regles_count = serializers.IntegerField(source='regles.count', read_only=True)
    regles = GradingRuleSerializer(many=True, read_only=True)
    target_codi = serializers.SerializerMethodField()
    construction_codi = serializers.SerializerMethodField()
    fit_type_codi = serializers.SerializerMethodField()

    def get_target_codi(self, obj):
        return obj.target.codi if obj.target and hasattr(obj.target, 'codi') else str(obj.target) if obj.target else None

    def get_construction_codi(self, obj):
        return obj.construction.codi if obj.construction and hasattr(obj.construction, 'codi') else str(obj.construction) if obj.construction else None

    def get_fit_type_codi(self, obj):
        return obj.fit_type.codi if obj.fit_type and hasattr(obj.fit_type, 'codi') else str(obj.fit_type) if obj.fit_type else None

    class Meta:
        model = GradingRuleSet
        fields = (
            'id', 'nom', 'codi_sistema',
            'target', 'target_codi',
            'construction', 'construction_codi',
            'fit_type', 'fit_type_codi',
            'garment_group', 'garment_group_nom',
            'size_system', 'size_system_codi', 'size_system_nom',
            'is_system_default', 'actiu',
            'regles_count', 'regles',
        )
        read_only_fields = ['is_system_default']
