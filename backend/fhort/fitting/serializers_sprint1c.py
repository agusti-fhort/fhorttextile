# Sprint 1C — SessioFitting
from rest_framework import serializers
try:
    from .models import SessioFitting
except ImportError:
    SessioFitting = None


if SessioFitting:
    class SessioFittingSerializer(serializers.ModelSerializer):
        client_nom = serializers.CharField(source='client.__str__', read_only=True)

        class Meta:
            model = SessioFitting
            fields = [
                'id', 'client', 'client_nom', 'data_sessio', 'hora_inici',
                'hora_fi', 'durada_hores', 'lloc', 'tipus', 'temporada',
                'any', 'responsable', 'estat', 'notes',
            ]


# SFFittingLiniaUpdateSerializer lives in fhort/fitting/serializers.py (canonical)
