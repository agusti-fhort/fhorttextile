# F4 P-LEGAL — serializers dels documents legals (backoffice).
from rest_framework import serializers

from .models import LegalDocument, LegalDocumentVersion, LegalAcceptance


class LegalDocumentVersionSerializer(serializers.ModelSerializer):
    document_tipus = serializers.CharField(source='document.tipus', read_only=True)
    document_nom = serializers.CharField(source='document.nom', read_only=True)

    class Meta:
        model = LegalDocumentVersion
        fields = [
            'id', 'document', 'document_tipus', 'document_nom', 'numero_versio',
            'contingut', 'sha256', 'estat', 'data_publicacio',
            'requereix_reacceptacio', 'created_at',
        ]
        # sha256/estat/data_publicacio només es fixen en publicar (endpoint dedicat),
        # mai per PATCH directe. numero_versio l'assigna el servidor (perform_create posa
        # el següent del document) → read_only, mai el fixa el client.
        read_only_fields = ['numero_versio', 'sha256', 'estat', 'data_publicacio', 'created_at']
        # Suprimim el UniqueTogetherValidator auto (derivat de unique_versio_per_document):
        # inclouria numero_versio (read_only) i el faria obligatori. La constraint de BD ja
        # garanteix la unicitat; perform_create assigna un número lliure sempre.
        validators = []

    def validate(self, attrs):
        # Una versió PUBLICADA no s'edita per l'API (el save-guard del model ho reforça,
        # però aquí donem un 400 net en lloc d'un 500).
        if self.instance and self.instance.estat == LegalDocumentVersion.ESTAT_PUBLICADA:
            if 'contingut' in attrs or 'numero_versio' in attrs:
                raise serializers.ValidationError(
                    'Aquesta versió està PUBLICADA i és immutable.')
        return attrs


class LegalDocumentSerializer(serializers.ModelSerializer):
    versions = LegalDocumentVersionSerializer(many=True, read_only=True)

    class Meta:
        model = LegalDocument
        fields = ['id', 'tipus', 'nom', 'actiu', 'created_at', 'versions']
        read_only_fields = ['created_at']


class LegalAcceptanceSerializer(serializers.ModelSerializer):
    codi_tenant = serializers.CharField(source='client.codi_tenant', read_only=True)
    document_tipus = serializers.CharField(source='versio.document.tipus', read_only=True)
    numero_versio = serializers.IntegerField(source='versio.numero_versio', read_only=True)
    sha256 = serializers.CharField(source='versio.sha256', read_only=True)

    class Meta:
        model = LegalAcceptance
        fields = [
            'id', 'client', 'codi_tenant', 'versio', 'document_tipus', 'numero_versio',
            'sha256', 'accepted_by', 'ip', 'user_agent', 'metode', 'timestamp',
        ]
