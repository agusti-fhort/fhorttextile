from rest_framework import serializers

from .models import (
    GarmentGroup,
    GarmentPOMMap,
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
    pom_nom_en = serializers.SerializerMethodField()
    pom_nom_ca = serializers.SerializerMethodField()
    pom_abbreviation = serializers.SerializerMethodField()
    # S16-B fix: codi global (POM-001) per a la columna CODI de la taula,
    # i categoria global (Upper body, Sleeve, ...) per filtrar regles per
    # grup de peça al frontend.
    pom_code_global = serializers.SerializerMethodField()
    pom_categoria = serializers.SerializerMethodField()
    talla_base_etiqueta = serializers.CharField(source='talla_base.etiqueta', read_only=True)

    def get_pom_nom_en(self, obj):
        if obj.pom and obj.pom.pom_global:
            return obj.pom.pom_global.nom_en
        return obj.pom.nom_client if obj.pom else None

    def get_pom_nom_ca(self, obj):
        if obj.pom and obj.pom.pom_global:
            return obj.pom.pom_global.nom_ca
        return None

    def get_pom_abbreviation(self, obj):
        if obj.pom and obj.pom.pom_global:
            return obj.pom.pom_global.abbreviation
        return obj.pom.codi_client if obj.pom else None

    def get_pom_code_global(self, obj):
        if obj.pom and obj.pom.pom_global:
            return obj.pom.pom_global.codi
        return None

    def get_pom_categoria(self, obj):
        if obj.pom and obj.pom.pom_global:
            return obj.pom.pom_global.categoria
        return None

    class Meta:
        model = GradingRule
        fields = (
            'id', 'rule_set', 'pom', 'pom_codi', 'pom_nom',
            'pom_nom_en', 'pom_nom_ca', 'pom_abbreviation',
            'pom_code_global', 'pom_categoria',
            'talla_base', 'talla_base_etiqueta',
            'logica', 'valor_base', 'increment', 'valors_step', 'actiu',
        )
        read_only_fields = ('rule_set',)


class GradingRuleSetSerializer(serializers.ModelSerializer):
    garment_group_nom = serializers.CharField(source='garment_group.nom', read_only=True)
    size_system_codi = serializers.CharField(source='size_system.codi', read_only=True)
    size_system_nom = serializers.CharField(source='size_system.nom', read_only=True)
    regles_count = serializers.IntegerField(source='regles.count', read_only=True)
    regles = GradingRuleSerializer(many=True, read_only=True)
    # S16-A: array de target codis (M2M). target_codi conservat per compat.
    targets_codis = serializers.SerializerMethodField()
    target_codi = serializers.SerializerMethodField()
    construction_codi = serializers.SerializerMethodField()
    fit_type_codi = serializers.SerializerMethodField()

    def get_targets_codis(self, obj):
        return list(obj.targets.values_list('codi', flat=True))

    def get_target_codi(self, obj):
        first = obj.targets.first()
        return first.codi if first else None

    def get_construction_codi(self, obj):
        return obj.construction.codi if obj.construction else None

    def get_fit_type_codi(self, obj):
        return obj.fit_type.codi if obj.fit_type else None

    class Meta:
        model = GradingRuleSet
        fields = (
            'id', 'nom', 'codi_sistema',
            'targets', 'targets_codis', 'target_codi',
            'construction', 'construction_codi',
            'fit_type', 'fit_type_codi',
            'garment_group', 'garment_group_nom',
            'size_system', 'size_system_codi', 'size_system_nom',
            'is_system_default', 'actiu',
            'regles_count', 'regles',
        )
        read_only_fields = ['is_system_default', 'regles', 'regles_count']


class GarmentPOMMapSerializer(serializers.ModelSerializer):
    # Exposem els camps del POMMaster → POMGlobal per a la UI.
    pom_code = serializers.CharField(source='pom.pom_global.codi', read_only=True)
    name_en = serializers.CharField(source='pom.pom_global.nom_en', read_only=True)
    name_cat = serializers.CharField(source='pom.pom_global.nom_ca', read_only=True)
    abbreviation = serializers.CharField(source='pom.pom_global.abbreviation', read_only=True)
    categoria = serializers.CharField(source='pom.pom_global.categoria', read_only=True)
    applies_woven = serializers.BooleanField(source='pom.pom_global.applies_woven', read_only=True)
    applies_knit = serializers.BooleanField(source='pom.pom_global.applies_knit', read_only=True)
    applies_swim = serializers.BooleanField(source='pom.pom_global.applies_swim', read_only=True)
    garment_type_codi = serializers.CharField(source='garment_type.codi_client', read_only=True)

    class Meta:
        model = GarmentPOMMap
        fields = (
            'id',
            'garment_type', 'garment_type_codi',
            'pom',
            'pom_code', 'name_en', 'name_cat', 'abbreviation', 'categoria',
            'applies_woven', 'applies_knit', 'applies_swim',
            'is_key', 'obligatori', 'ordre',
        )
