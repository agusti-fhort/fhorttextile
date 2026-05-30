from rest_framework import serializers

from .models import (
    GradingVersion,
    POMAlert,
    SizeFitting,
)


class SizeFittingSerializer(serializers.ModelSerializer):
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    creat_per_nom = serializers.CharField(source='creat_per.nom_complet', read_only=True)
    estat_display = serializers.CharField(source='get_estat_display', read_only=True)

    class Meta:
        model = SizeFitting
        fields = '__all__'
        read_only_fields = ('data_creacio',)


class GradingVersionSerializer(serializers.ModelSerializer):
    creat_per_nom = serializers.CharField(source='creat_per.nom_complet', read_only=True)

    class Meta:
        model = GradingVersion
        fields = '__all__'
        read_only_fields = ('data',)


class POMAlertSerializer(serializers.ModelSerializer):
    pom_codi = serializers.CharField(source='pom.codi_client', read_only=True)
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    resolt_per_nom = serializers.CharField(source='resolt_per.nom_complet', read_only=True)

    class Meta:
        model = POMAlert
        fields = '__all__'
        read_only_fields = ('data_creacio',)



# Sprint 4 — SFFittingLinia serializer
class SFFittingLiniaUpdateSerializer(serializers.ModelSerializer):
    """To update valor_nou from the frontend."""

    class Meta:
        try:
            from fhort.fitting.models import SFFittingLinia
            model = SFFittingLinia
        except ImportError:
            model = None
        fields = ['id', 'pom', 'nom_pom', 'talla', 'valor_vigent', 'valor_nou', 'estat_cella']
        read_only_fields = ['pom', 'nom_pom', 'talla', 'valor_vigent', 'estat_cella']
