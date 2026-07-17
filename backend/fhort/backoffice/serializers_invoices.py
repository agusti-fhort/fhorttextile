"""Serializers de la facturació fiscal (F-FACT B1): sèries, tipus d'IVA i factures."""
from rest_framework import serializers

from fhort.tenants.models import Client

from .models import Invoice, InvoiceLine, InvoiceSerie, VATRate


class InvoiceSerieSerializer(serializers.ModelSerializer):
    # Com quedaria el pròxim número, sense reservar-lo: la UI ha de poder ensenyar la
    # conseqüència del format ABANS de desar-lo.
    exemple = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceSerie
        fields = ['id', 'codi', 'nom', 'format', 'reinici_anual',
                  'any_actual', 'comptador', 'activa', 'exemple', 'created_at']
        # El correlatiu és estat viu del motor: no s'edita per API. Qui el mou és
        # reserve_invoice_number(), dins la transacció de l'emissió.
        read_only_fields = ['any_actual', 'comptador', 'created_at']

    def get_exemple(self, obj):
        return obj.exemple()

    def validate_format(self, value):
        """Rebutja una plantilla que no sabria renderitzar. Val més fallar aquí que en
        emetre, quan ja hi ha un client esperant la factura."""
        try:
            value.format(codi='XX', any=2026, any2=26, num=1)
        except (KeyError, IndexError, ValueError) as e:
            raise serializers.ValidationError(
                f'Format invàlid: {e}. Claus permeses: {{codi}} {{any}} {{any2}} {{num}}.')
        return value


class VATRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VATRate
        fields = ['id', 'codi', 'nom', 'percentatge', 'regim_default',
                  'mencio_legal', 'actiu', 'created_at']
        read_only_fields = ['created_at']


class InvoiceLineSerializer(serializers.ModelSerializer):
    service_code = serializers.CharField(source='service.code', read_only=True)

    class Meta:
        model = InvoiceLine
        fields = ['id', 'service', 'service_code', 'descripcio', 'quantitat',
                  'preu_unit', 'total', 'moneda', 'vat_rate', 'pct_iva', 'quota_iva']
        # total/pct/quota els calcula el motor, mai el client de l'API.
        read_only_fields = ['total', 'pct_iva', 'quota_iva']


class InvoiceListSerializer(serializers.ModelSerializer):
    client_codi = serializers.CharField(source='client.codi_tenant', read_only=True)
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    serie_codi = serializers.CharField(source='serie.codi', read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'client', 'client_codi', 'client_nom', 'period', 'tipus',
                  'estat', 'serie', 'serie_codi', 'numero', 'base_imposable',
                  'quota_iva', 'total', 'moneda', 'created_at', 'emesa_at']


class InvoiceDetailSerializer(InvoiceListSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)
    rectifica_numero = serializers.CharField(source='rectifica.numero', read_only=True)

    class Meta(InvoiceListSerializer.Meta):
        fields = InvoiceListSerializer.Meta.fields + ['lines', 'nota', 'rectifica',
                                                      'rectifica_numero', 'num_seq']


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """Alta d'una factura MANUAL en esborrany. La numeració i l'IVA no s'hi toquen:
    arriben en emetre.

    El client s'identifica per `codi_tenant`, no per pk: és la clau natural que fa
    servir tota l'API del backoffice (ClientViewSet.lookup_field) i l'única que la SPA
    arriba a veure — la llista de tenants no exposa cap id.
    """
    client = serializers.SlugRelatedField(
        slug_field='codi_tenant', queryset=Client.objects.all())

    class Meta:
        model = Invoice
        fields = ['id', 'client', 'period', 'moneda', 'nota']

    def create(self, validated_data):
        validated_data['tipus'] = Invoice.TIPUS_MANUAL
        validated_data['estat'] = Invoice.ESTAT_ESBORRANY
        return super().create(validated_data)
