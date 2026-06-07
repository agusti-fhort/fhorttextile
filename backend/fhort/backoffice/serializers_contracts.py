from rest_framework import serializers
from .models import ServiceCatalog, TenantContract, ContractLine


class ServiceCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ServiceCatalog
        fields = '__all__'


class ContractLineSerializer(serializers.ModelSerializer):
    service_nom  = serializers.CharField(source='service.nom', read_only=True)
    service_code = serializers.CharField(source='service.code', read_only=True)

    class Meta:
        model  = ContractLine
        fields = ['id', 'service', 'service_code', 'service_nom',
                  'preu', 'moneda', 'inclosos', 'actiu']


class TenantContractListSerializer(serializers.ModelSerializer):
    client_codi = serializers.CharField(source='client.codi_tenant', read_only=True)
    lines_count = serializers.IntegerField(source='lines.count', read_only=True)

    class Meta:
        model  = TenantContract
        fields = ['id', 'client', 'client_codi', 'data_inici', 'data_fi',
                  'actiu', 'lines_count', 'created_at']


class TenantContractDetailSerializer(TenantContractListSerializer):
    lines = ContractLineSerializer(many=True, read_only=True)

    class Meta(TenantContractListSerializer.Meta):
        fields = TenantContractListSerializer.Meta.fields + ['lines', 'nota']


class TenantContractCreateSerializer(serializers.ModelSerializer):
    lines = ContractLineSerializer(many=True, required=False)

    class Meta:
        model  = TenantContract
        fields = ['client', 'data_inici', 'data_fi', 'actiu', 'nota', 'lines']

    def create(self, validated_data):
        lines_data = validated_data.pop('lines', [])
        contract = TenantContract.objects.create(**validated_data)
        for line in lines_data:
            ContractLine.objects.create(contract=contract, **line)
        return contract
