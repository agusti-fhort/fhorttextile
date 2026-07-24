"""Serialització d'un RECURS (TenantLink vist des de la Marca que l'emet) — P7.

El que hi ha aquí és tan important com el que no hi és: `token` NO és camp del serializer.
La view l'afegeix a mà a la resposta de creació i enlloc més (views_recursos.py). Deixar-lo
fora per construcció vol dir que cap `list`, cap `retrieve` i cap acció futura el pot filtrar
per descuit.
"""
from rest_framework import serializers

from .models import Client, TenantLink


class RecursSerializer(serializers.ModelSerializer):
    #: Codi nu del Studio. És el nom que el domini fa servir (`studio_codi`), no el del camp
    #: de BD (`studio_codi_tenant`): l'API parla de recursos, no de la taula del pont.
    studio_codi = serializers.CharField(source='studio_codi_tenant', read_only=True)
    studio_nom = serializers.SerializerMethodField()

    class Meta:
        model = TenantLink
        fields = ('id', 'studio_codi', 'studio_nom', 'estat', 'created_at', 'aturat_at', 'nota')
        read_only_fields = fields

    def get_studio_nom(self, obj):
        """Nom del Client del destí, resolt per CODI NU (mai per FK — llei de la federació).

        Consulta a `public` sense `schema_context`: `tenants_client` només existeix allà i el
        `search_path` del tenant ja hi arriba (diagnosi P7 §A1). Un Studio esborrat del
        registre deixa el nom buit i el codi visible: el vincle no ha de desaparèixer de la
        vista del Brand perquè l'altre extrem s'hagi mogut.
        """
        client = Client.objects.filter(codi_tenant=obj.studio_codi_tenant).only('nom').first()
        return client.nom if client else ''
