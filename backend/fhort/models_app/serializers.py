from rest_framework import serializers

from .models import Contracte, LiniaContracte, Model, ModelFitxer, ModelServei


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
    responsable_nom = serializers.CharField(source='responsable.nom_complet', read_only=True)
    size_system_codi = serializers.CharField(source='size_system.codi', read_only=True)
    talla_base_etiqueta = serializers.CharField(source='talla_base.etiqueta', read_only=True)

    class Meta:
        model = Model
        fields = '__all__'
        read_only_fields = ('codi_intern', 'data_entrada')



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
