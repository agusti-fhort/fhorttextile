# Sprint 1C — Serializers Tasca, PaquetServei, ModelServei
from rest_framework import serializers
from .models import Tasca, PaquetServei, PaquetServeiTasca


class TascaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tasca
        fields = [
            'id', 'nom_tasca', 'tipus_tasca', 'fase', 'ordre_base',
            'slots_base', 'facturable', 'bloqueja_model', 'gate',
            'resultat_gate', 'notes', 'is_active',
        ]


class PaquetServeiTascaSerializer(serializers.ModelSerializer):
    tasca_detail = TascaSerializer(source='tasca', read_only=True)

    class Meta:
        model = PaquetServeiTasca
        fields = ['id', 'tasca', 'tasca_detail', 'ordre', 'opcional', 'notes']


class PaquetServeiSerializer(serializers.ModelSerializer):
    tasques = PaquetServeiTascaSerializer(many=True, read_only=True)

    class Meta:
        model = PaquetServei
        fields = [
            'id', 'nom', 'actiu', 'grup', 'multiplicador', 'slots_base',
            'ordre_popup', 'descripcio', 'notes_comercials', 'tasques',
        ]


class PaquetServeiListSerializer(serializers.ModelSerializer):
    """Versió llista sense tasques nested (més ràpid)."""
    class Meta:
        model = PaquetServei
        fields = ['id', 'nom', 'actiu', 'grup', 'slots_base', 'ordre_popup']
