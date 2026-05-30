from rest_framework import serializers

from .models import BaseMeasurement, Contracte, LiniaContracte, Model, ModelFitxer, ModelServei


class ModelFitxerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelFitxer
        fields = '__all__'
        read_only_fields = ('data_pujada',)


class ModelListSerializer(serializers.ModelSerializer):
    garment_type = serializers.SerializerMethodField()
    responsable = serializers.SerializerMethodField()

    class Meta:
        model = Model
        fields = (
            'id',
            'codi_intern',
            'codi_client',
            'nom_prenda',
            'garment_type',
            'estat',
            'fase_actual',
            'responsable',
            'prioritat',
            'data_objectiu',
            # Sprint 1A
            'familia',
            'slots_prev_tecnics',
            'slots_prev_confeccio',
            'slots_reals_tecnic',
            'slots_reals_confeccio',
        )

    def get_garment_type(self, obj):
        return obj.garment_type.nom_client if obj.garment_type_id else None

    def get_responsable(self, obj):
        return obj.responsable.nom_complet if obj.responsable_id else None


class ContracteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contracte
        fields = '__all__'


class LiniaContracteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiniaContracte
        fields = '__all__'


class ModelDetailSerializer(serializers.ModelSerializer):
    fitxers = ModelFitxerSerializer(many=True, read_only=True)
    garment_type_nom = serializers.CharField(source='garment_type.nom_client', read_only=True)
    garment_group_nom = serializers.CharField(source='garment_group.nom', read_only=True)
    responsable_nom = serializers.CharField(source='responsable.nom_complet', read_only=True)
    size_system_codi = serializers.CharField(source='size_system.codi', read_only=True)
    size_system_nom = serializers.CharField(source='size_system.nom', read_only=True)

    class Meta:
        model = Model
        # 'fields = __all__' already includes the new fields origen_patro, versio,
        # garment_group. The *_nom variants are only exposed read-only.
        fields = '__all__'
        read_only_fields = ('codi_intern', 'data_entrada')



# Sprint S14B — BaseMeasurement CRUD
class BaseMeasurementSerializer(serializers.ModelSerializer):
    # Expose POM fields via `pom.pom_global` for the UI.
    pom_code = serializers.CharField(source='pom.pom_global.codi', read_only=True)
    pom_name_en = serializers.CharField(source='pom.pom_global.nom_en', read_only=True)
    pom_name_cat = serializers.CharField(source='pom.pom_global.nom_ca', read_only=True)
    pom_abbreviation = serializers.CharField(source='pom.pom_global.abbreviation', read_only=True)
    pom_is_key = serializers.BooleanField(source='pom.pom_global.is_key', read_only=True)
    pom_category = serializers.CharField(source='pom.pom_global.categoria', read_only=True)
    # Legacy POMMaster fields (fallback when there is no associated pom_global).
    pom_codi_client = serializers.CharField(source='pom.codi_client', read_only=True)
    pom_nom_client = serializers.CharField(source='pom.nom_client', read_only=True)

    class Meta:
        model = BaseMeasurement
        fields = (
            'id', 'model', 'pom',
            'pom_code', 'pom_name_en', 'pom_name_cat',
            'pom_abbreviation', 'pom_is_key', 'pom_category',
            'pom_codi_client', 'pom_nom_client',
            'base_value_cm', 'is_active', 'notes',
            'nom_fitxa', 'origen',
            'updated_at',
        )
        read_only_fields = ('updated_at',)


# Sprint 1C — ModelServei
class ModelServeiSerializer(serializers.ModelSerializer):
    servei_nom = serializers.CharField(source='servei.nom', read_only=True)
    servei_grup = serializers.CharField(source='servei.grup', read_only=True)

    class Meta:
        model = ModelServei
        fields = [
            'id', 'model', 'servei', 'servei_nom', 'servei_grup',
            'nom_servei', 'grup', 'slots_base', 'contractat', 'ampliat',
            'estat_autoritzacio', 'autoritzat_per', 'data_autoritzacio',
            'linia_addicional',
        ]
        read_only_fields = ['nom_servei', 'grup', 'slots_base']
