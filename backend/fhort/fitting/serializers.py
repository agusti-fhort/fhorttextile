from rest_framework import serializers

from .models import (
    FitComment,
    FitCommentFitxer,
    Fitting,
    FittingLine,
    GradedSpecLine,
    GradingVersion,
    POMAlert,
    SizeFitting,
)


class SizeFittingSerializer(serializers.ModelSerializer):
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    creat_per_nom = serializers.CharField(source='creat_per.nom_complet', read_only=True)

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


class GradedSpecLineSerializer(serializers.ModelSerializer):
    pom_codi = serializers.CharField(source='pom.codi_client', read_only=True)
    talla_etiqueta = serializers.CharField(source='talla.etiqueta', read_only=True)

    class Meta:
        model = GradedSpecLine
        fields = (
            'id',
            'grading_version',
            'pom',
            'pom_codi',
            'talla',
            'talla_etiqueta',
            'valor_target',
            'valor_pare',
            'delta',
            'motiu_delta',
            'estat',
            'avis_text',
        )


class FittingLineSerializer(serializers.ModelSerializer):
    pom_codi = serializers.CharField(source='pom.codi_client', read_only=True)
    talla_etiqueta = serializers.CharField(source='talla.etiqueta', read_only=True)

    class Meta:
        model = FittingLine
        fields = (
            'id',
            'fitting',
            'pom',
            'pom_codi',
            'talla',
            'talla_etiqueta',
            'valor_target',
            'valor_mesurat',
            'delta_real',
            'estat',
            'nota',
        )


class FitCommentFitxerSerializer(serializers.ModelSerializer):
    class Meta:
        model = FitCommentFitxer
        fields = '__all__'
        read_only_fields = ('data_pujada',)


class FitCommentSerializer(serializers.ModelSerializer):
    fitxers = FitCommentFitxerSerializer(many=True, read_only=True)

    class Meta:
        model = FitComment
        fields = '__all__'


class FittingSerializer(serializers.ModelSerializer):
    responsable_nom = serializers.CharField(source='responsable.nom_complet', read_only=True)
    linies = FittingLineSerializer(many=True, read_only=True)
    comentaris = FitCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Fitting
        fields = '__all__'


class POMAlertSerializer(serializers.ModelSerializer):
    pom_codi = serializers.CharField(source='pom.codi_client', read_only=True)
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    resolt_per_nom = serializers.CharField(source='resolt_per.nom_complet', read_only=True)

    class Meta:
        model = POMAlert
        fields = '__all__'
        read_only_fields = ('data_creacio',)



# Sprint 4 — Serializer SFFittingLinia
class SFFittingLiniaUpdateSerializer(serializers.ModelSerializer):
    """Per actualitzar valor_nou des del frontend."""

    class Meta:
        try:
            from fhort.fitting.models import SFFittingLinia
            model = SFFittingLinia
        except ImportError:
            model = None
        fields = ['id', 'pom', 'nom_pom', 'talla', 'valor_vigent', 'valor_nou', 'estat_cella']
        read_only_fields = ['pom', 'nom_pom', 'talla', 'valor_vigent', 'estat_cella']
