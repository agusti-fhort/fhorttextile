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
    talla_base_etiqueta = serializers.CharField(source='talla_base.etiqueta', read_only=True)

    class Meta:
        model = GradingRule
        fields = '__all__'


class GradingRuleSetSerializer(serializers.ModelSerializer):
    garment_group_nom = serializers.CharField(source='garment_group.nom', read_only=True)
    size_system_codi = serializers.CharField(source='size_system.codi', read_only=True)
    regles = GradingRuleSerializer(many=True, read_only=True)

    class Meta:
        model = GradingRuleSet
        fields = ('id', 'nom', 'garment_group', 'garment_group_nom',
                  'size_system', 'size_system_codi', 'actiu', 'regles')
