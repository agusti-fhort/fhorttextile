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

    # PAS B5 — bloc complet "com mesurar" per a la vista Catalogue (NOMÉS LECTURA). Mateix patró
    # que GarmentPOMMapSerializer però arrelat al propi POMMaster: pom_global flat amb fallback
    # tenant-only. Tots read_only → no afegeixen escriptura (el catàleg es conserva intacte).
    pom_code = serializers.SerializerMethodField()
    name_en = serializers.SerializerMethodField()
    name_cat = serializers.SerializerMethodField()
    abbreviation = serializers.SerializerMethodField()
    categoria_nom = serializers.SerializerMethodField()
    applies_woven = serializers.BooleanField(source='pom_global.applies_woven', read_only=True)
    applies_knit = serializers.BooleanField(source='pom_global.applies_knit', read_only=True)
    applies_swim = serializers.BooleanField(source='pom_global.applies_swim', read_only=True)
    start_point = serializers.CharField(source='pom_global.start_point', read_only=True)
    end_point = serializers.CharField(source='pom_global.end_point', read_only=True)
    reference_point = serializers.CharField(source='pom_global.reference_point', read_only=True)
    scope = serializers.CharField(source='pom_global.scope', read_only=True)
    orientation = serializers.CharField(source='pom_global.orientation', read_only=True)
    state = serializers.CharField(source='pom_global.state', read_only=True)
    line = serializers.CharField(source='pom_global.line', read_only=True)
    body_section = serializers.CharField(source='pom_global.body_section', read_only=True)
    tol_prod_cm = serializers.DecimalField(source='pom_global.tol_prod_cm',
                                           max_digits=5, decimal_places=2, read_only=True)
    tol_samp_cm = serializers.DecimalField(source='pom_global.tol_samp_cm',
                                           max_digits=5, decimal_places=2, read_only=True)
    iso_ref = serializers.CharField(source='pom_global.iso_ref', read_only=True)
    unitat = serializers.CharField(source='pom_global.unitat', read_only=True)
    descripcio_en = serializers.CharField(source='pom_global.descripcio_en', read_only=True)
    descripcio_ca = serializers.CharField(source='pom_global.descripcio_ca', read_only=True)
    body_measure_iso_codi = serializers.CharField(
        source='pom_global.body_measure_iso.codi_iso', read_only=True)
    body_measure_iso_nom = serializers.CharField(
        source='pom_global.body_measure_iso.nom_en', read_only=True)

    def get_pom_code(self, obj):
        pg = obj.pom_global
        return (pg.codi if pg else None) or obj.codi_client

    def get_name_en(self, obj):
        pg = obj.pom_global
        return (pg.nom_en if pg else None) or obj.nom_client

    def get_name_cat(self, obj):
        pg = obj.pom_global
        return (pg.nom_ca if pg else None) or obj.nom_client

    def get_abbreviation(self, obj):
        pg = obj.pom_global
        return (pg.abbreviation if pg else None) or obj.codi_client

    def get_categoria_nom(self, obj):
        pg = obj.pom_global
        if pg and pg.categoria:
            return pg.categoria
        cat = obj.categoria
        return (cat.nom_ca or cat.nom_en) if cat else ''

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
    # S16-B fix: global code (POM-001) for the table's CODI column,
    # and global category (Upper body, Sleeve, ...) to filter rules by
    # garment group on the frontend.
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
            'increment_base', 'increment_break', 'talla_break_label', 'talla_break_pos',  # Peça A (vista)
        )
        read_only_fields = ('rule_set',)


class GradingRuleSetSerializer(serializers.ModelSerializer):
    garment_group_nom = serializers.CharField(source='garment_group.nom', read_only=True)
    size_system_codi = serializers.CharField(source='size_system.codi', read_only=True)
    size_system_nom = serializers.CharField(source='size_system.nom', read_only=True)
    regles_count = serializers.IntegerField(source='regles.count', read_only=True)
    regles = GradingRuleSerializer(many=True, read_only=True)
    # S16-A: array of target codes (M2M). target_codi kept for compatibility.
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
    # Display fields amb FALLBACK a POMMaster (tenant-only, pom_global=None → els 19 importats per IA
    # no han de sortir buits): si no hi ha pom_global, caure a codi_client / nom_client / categoria FK.
    pom_code = serializers.SerializerMethodField()
    name_en = serializers.SerializerMethodField()
    name_cat = serializers.SerializerMethodField()
    abbreviation = serializers.SerializerMethodField()
    categoria = serializers.SerializerMethodField()
    applies_woven = serializers.BooleanField(source='pom.pom_global.applies_woven', read_only=True)
    applies_knit = serializers.BooleanField(source='pom.pom_global.applies_knit', read_only=True)
    applies_swim = serializers.BooleanField(source='pom.pom_global.applies_swim', read_only=True)

    # PAS B3-ter — bloc complet "com mesurar" des de pom.pom_global. Quan pom_global és None
    # (tenant-only, importats per IA) DRF retorna None en travessar el FK nul: el front els pinta
    # com "—", que és precisament el senyal de camp pendent de definir.
    start_point = serializers.CharField(source='pom.pom_global.start_point', read_only=True)
    end_point = serializers.CharField(source='pom.pom_global.end_point', read_only=True)
    reference_point = serializers.CharField(source='pom.pom_global.reference_point', read_only=True)
    scope = serializers.CharField(source='pom.pom_global.scope', read_only=True)
    orientation = serializers.CharField(source='pom.pom_global.orientation', read_only=True)
    state = serializers.CharField(source='pom.pom_global.state', read_only=True)
    line = serializers.CharField(source='pom.pom_global.line', read_only=True)
    body_section = serializers.CharField(source='pom.pom_global.body_section', read_only=True)
    tol_prod_cm = serializers.DecimalField(source='pom.pom_global.tol_prod_cm',
                                           max_digits=5, decimal_places=2, read_only=True)
    tol_samp_cm = serializers.DecimalField(source='pom.pom_global.tol_samp_cm',
                                           max_digits=5, decimal_places=2, read_only=True)
    iso_ref = serializers.CharField(source='pom.pom_global.iso_ref', read_only=True)
    unitat = serializers.CharField(source='pom.pom_global.unitat', read_only=True)
    descripcio_en = serializers.CharField(source='pom.pom_global.descripcio_en', read_only=True)
    descripcio_ca = serializers.CharField(source='pom.pom_global.descripcio_ca', read_only=True)
    body_measure_iso_codi = serializers.CharField(
        source='pom.pom_global.body_measure_iso.codi_iso', read_only=True)
    body_measure_iso_nom = serializers.CharField(
        source='pom.pom_global.body_measure_iso.nom_en', read_only=True)

    # Migration família → item COMPLETADA (PAS 6): la pertinença viu només a garment_type_item;
    # el FK legacy garment_type s'ha eliminat (migració 0016).
    garment_type_item_codi = serializers.CharField(source='garment_type_item.code', read_only=True)
    garment_type_item_name = serializers.CharField(source='garment_type_item.name', read_only=True)

    def get_pom_code(self, obj):
        pg = obj.pom.pom_global
        return (pg.codi if pg else None) or obj.pom.codi_client

    def get_name_en(self, obj):
        pg = obj.pom.pom_global
        return (pg.nom_en if pg else None) or obj.pom.nom_client

    def get_name_cat(self, obj):
        pg = obj.pom.pom_global
        return (pg.nom_ca if pg else None) or obj.pom.nom_client

    def get_abbreviation(self, obj):
        pg = obj.pom.pom_global
        return (pg.abbreviation if pg else None) or obj.pom.codi_client

    def get_categoria(self, obj):
        pg = obj.pom.pom_global
        if pg and pg.categoria:
            return pg.categoria
        cat = obj.pom.categoria
        return (cat.nom_ca or cat.nom_en) if cat else ''

    class Meta:
        model = GarmentPOMMap
        fields = (
            'id',
            'garment_type_item', 'garment_type_item_codi', 'garment_type_item_name',
            'pom',
            'pom_code', 'name_en', 'name_cat', 'abbreviation', 'categoria',
            'applies_woven', 'applies_knit', 'applies_swim',
            # PAS B3-ter — bloc complet "com mesurar"
            'start_point', 'end_point', 'reference_point',
            'scope', 'orientation', 'state', 'line', 'body_section',
            'tol_prod_cm', 'tol_samp_cm', 'iso_ref', 'unitat',
            'descripcio_en', 'descripcio_ca',
            'body_measure_iso_codi', 'body_measure_iso_nom',
            'is_key', 'obligatori', 'ordre', 'pendent_revisio',
        )
