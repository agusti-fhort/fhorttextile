from rest_framework import serializers

from .models import ModelTasca, Tasca, TimerEntrada


class TascaSerializer(serializers.ModelSerializer):
    tasca_global_codi = serializers.CharField(source='tasca_global.codi', read_only=True)
    tasca_global_nom = serializers.CharField(source='tasca_global.nom_ca', read_only=True)
    es_gate = serializers.BooleanField(source='tasca_global.es_gate', read_only=True)

    class Meta:
        model = Tasca
        fields = '__all__'


class ModelTascaSerializer(serializers.ModelSerializer):
    tasca_nom = serializers.SerializerMethodField()
    responsable_nom = serializers.CharField(source='responsable.nom_complet', read_only=True)
    gate_revisat_per_nom = serializers.CharField(source='gate_revisat_per.nom_complet', read_only=True)
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)

    class Meta:
        model = ModelTasca
        fields = '__all__'

    def get_tasca_nom(self, obj):
        if not obj.tasca_id:
            return None
        if obj.tasca.nom_tasca:
            return obj.tasca.nom_tasca
        if obj.tasca.nom_custom:
            return obj.tasca.nom_custom
        if obj.tasca.tasca_global_id:
            return obj.tasca.tasca_global.nom_ca
        return None


class TimerEntradaSerializer(serializers.ModelSerializer):
    tecnic_nom = serializers.CharField(source='tecnic.nom_complet', read_only=True)
    model_tasca_codi = serializers.CharField(source='model_tasca.model.codi_intern', read_only=True)

    class Meta:
        model = TimerEntrada
        fields = '__all__'
        # tecnic is assigned automatically in ViewSet.perform_create
        read_only_fields = ('tecnic', 'minuts', 'fi')
