from rest_framework import serializers

from .models import TimerEntrada


class TimerEntradaSerializer(serializers.ModelSerializer):
    tecnic_nom = serializers.CharField(source='tecnic.nom_complet', read_only=True)
    model_task_codi = serializers.CharField(source='model_task.model.codi_intern', read_only=True)

    class Meta:
        model = TimerEntrada
        fields = '__all__'
        # tecnic is assigned automatically in ViewSet.perform_create
        read_only_fields = ('tecnic', 'minuts', 'fi')
