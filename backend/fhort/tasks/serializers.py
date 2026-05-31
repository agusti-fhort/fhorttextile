from rest_framework import serializers

from .models import Tasca, TimerEntrada


class TascaSerializer(serializers.ModelSerializer):
    tasca_global_codi = serializers.CharField(source='tasca_global.codi', read_only=True)
    tasca_global_nom = serializers.CharField(source='tasca_global.nom_ca', read_only=True)
    es_gate = serializers.BooleanField(source='tasca_global.es_gate', read_only=True)

    class Meta:
        model = Tasca
        fields = '__all__'


class TimerEntradaSerializer(serializers.ModelSerializer):
    tecnic_nom = serializers.CharField(source='tecnic.nom_complet', read_only=True)
    model_task_codi = serializers.CharField(source='model_task.model.codi_intern', read_only=True)

    class Meta:
        model = TimerEntrada
        fields = '__all__'
        # tecnic is assigned automatically in ViewSet.perform_create
        read_only_fields = ('tecnic', 'minuts', 'fi')
