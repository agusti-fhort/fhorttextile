# P-LEADS — serializers del formulari públic i de l'API privada de leads (backoffice).
from rest_framework import serializers

from .models import Lead


class LeadPublicSerializer(serializers.ModelSerializer):
    """Entrada del formulari públic (ftt-web). `website` és el camp honeypot: mai es
    desa (no és un camp del model) — la view el mira ABANS de validar/instanciar
    aquest serializer i talla curt si ve ple, sense arribar aquí."""

    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Lead
        fields = [
            'nom', 'empresa', 'email', 'missatge', 'idioma', 'pagina_origen',
            'consentiment', 'privacy_version', 'website',
        ]

    def validate_consentiment(self, value):
        if not value:
            raise serializers.ValidationError('Cal acceptar la política de privacitat.')
        return value

    def validate_missatge(self, value):
        if len(value) > 4000:
            raise serializers.ValidationError('El missatge no pot superar els 4000 caràcters.')
        return value

    def create(self, validated_data):
        validated_data.pop('website', None)
        return Lead.objects.create(**validated_data)
