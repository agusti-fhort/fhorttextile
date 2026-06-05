# Sprint 2 — Capa 1/2: serializers de tenants (Client) i plans (Plan) per al
# backoffice. Separat de serializers.py (auth). Principi rector: el backoffice
# llegeix el REGISTRE de tenants al schema public, mai entra als seus schemas.
# Els identificadors Stripe MAI s'exposen com a valor: només es diu si existeixen.
from rest_framework import serializers

from fhort.tenants.models import Client, Plan, TenantContacte


class TenantContacteSerializer(serializers.ModelSerializer):
    """Contacte d'un tenant. `client` és write_only (s'injecta des de la ruta)."""

    class Meta:
        model = TenantContacte
        fields = [
            'id', 'client', 'nom', 'cognom', 'carrec',
            'email', 'telefon', 'principal',
        ]
        extra_kwargs = {'client': {'write_only': True, 'required': False}}


class ClientListSerializer(serializers.ModelSerializer):
    """Vista de llista de tenants al backoffice."""

    plan = serializers.SerializerMethodField()
    stripe_customer_id = serializers.SerializerMethodField()
    is_gratuit = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            'codi_tenant', 'nom', 'tipologia', 'estat', 'plan',
            'moneda', 'pais', 'data_alta', 'stripe_customer_id',
            'onboarding_complet', 'gratis_fins', 'nota_comercial', 'is_gratuit',
        ]

    def get_plan(self, obj):
        return obj.plan.nom if obj.plan_id else None

    def get_stripe_customer_id(self, obj):
        # Mai el valor real: només si el tenant té client Stripe associat.
        return bool(obj.stripe_customer_id)

    def get_is_gratuit(self, obj):
        # Conveniència per a la UI: el tenant no s'ha de facturar aquest mes.
        return obj.es_gratuit


class ClientDetailSerializer(ClientListSerializer):
    """Detall d'un tenant: dades fiscals, adreça estructurada, VAT, contactes."""

    stripe_payment_method_id = serializers.SerializerMethodField()
    contactes = TenantContacteSerializer(many=True, read_only=True)

    class Meta(ClientListSerializer.Meta):
        fields = ClientListSerializer.Meta.fields + [
            'rao_social', 'nif', 'adreca_fiscal', 'email_facturacio',
            'metode_pagament', 'stripe_payment_method_id',
            'data_suspensio', 'data_baixa', 'motiu_baixa', 'feature_flags',
            # Adreça estructurada + VAT internacional (Sprint 3).
            'adreca_linia1', 'adreca_linia2', 'ciutat', 'estat_provincia',
            'codi_postal', 'vat_number', 'vat_validat', 'vat_validat_data',
            'tipus_client', 'regim_vat', 'contactes',
        ]

    def get_stripe_payment_method_id(self, obj):
        return bool(obj.stripe_payment_method_id)


class ClientUpdateSerializer(serializers.ModelSerializer):
    """Camps editables d'un tenant des del backoffice.

    `codi_tenant` és immutable (read_only). `regim_vat` no s'edita: és calculat.
    """

    codi_tenant = serializers.CharField(read_only=True)

    class Meta:
        model = Client
        fields = [
            'codi_tenant', 'nom', 'rao_social', 'nif',
            'adreca_linia1', 'adreca_linia2', 'ciutat', 'estat_provincia',
            'codi_postal', 'pais', 'email_facturacio', 'metode_pagament',
            'estat', 'motiu_baixa', 'vat_number', 'tipus_client',
            # Gestió comercial (ADMIN/COMERCIAL via get_permissions).
            'gratis_fins', 'nota_comercial',
        ]


class ClientCreateSerializer(serializers.ModelSerializer):
    """Alta d'un tenant nou. schema_name es deriva de codi_tenant (minúscules)."""

    class Meta:
        model = Client
        fields = [
            'codi_tenant', 'nom', 'tipologia', 'schema_name', 'plan',
            'moneda', 'idioma',
            'rao_social', 'nif', 'adreca_linia1', 'ciutat', 'pais',
            'email_facturacio', 'tipus_client',
        ]
        read_only_fields = ['schema_name']
        extra_kwargs = {
            'nom': {'required': True},
            'tipologia': {'required': True},
            'plan': {'required': True},
            'moneda': {'required': True},
            'idioma': {'required': True},
            'rao_social': {'required': False},
            'nif': {'required': False},
            'adreca_linia1': {'required': False},
            'ciutat': {'required': False},
            'pais': {'required': False},
            'email_facturacio': {'required': False},
            'tipus_client': {'required': False},
        }

    def validate_codi_tenant(self, value):
        v = (value or '').strip()
        if len(v) != 3:
            raise serializers.ValidationError('Ha de tenir exactament 3 caràcters.')
        if not v.isalnum():
            raise serializers.ValidationError('Només alfanumèric (sense símbols ni espais).')
        if v != v.upper():
            raise serializers.ValidationError("Ha d'anar en majúscules.")
        if Client.objects.filter(codi_tenant=v).exists():
            raise serializers.ValidationError('Aquest codi_tenant ja existeix.')
        schema = v.lower()
        # schema_name ha de ser un identificador PostgreSQL vàlid: no començar per dígit.
        if not schema[0].isalpha():
            raise serializers.ValidationError(
                'El schema derivat ha de començar per lletra (el codi no pot començar per dígit).'
            )
        if Client.objects.filter(schema_name=schema).exists():
            raise serializers.ValidationError('El schema derivat ja existeix.')
        return v

    def create(self, validated_data):
        validated_data['schema_name'] = validated_data['codi_tenant'].lower()
        return super().create(validated_data)


class PlanSerializer(serializers.ModelSerializer):
    """Pla complet, inclosos els camps de facturació per models iniciats/mes."""

    class Meta:
        model = Plan
        fields = '__all__'
