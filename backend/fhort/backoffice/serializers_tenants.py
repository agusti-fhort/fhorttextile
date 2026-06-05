# Sprint 2 — Capa 1/2: serializers de tenants (Client) i plans (Plan) per al
# backoffice. Separat de serializers.py (auth). Principi rector: el backoffice
# llegeix el REGISTRE de tenants al schema public, mai entra als seus schemas.
# Els identificadors Stripe MAI s'exposen com a valor: només es diu si existeixen.
from rest_framework import serializers

from fhort.tenants.models import Client, Plan


class ClientListSerializer(serializers.ModelSerializer):
    """Vista de llista de tenants al backoffice."""

    plan = serializers.SerializerMethodField()
    stripe_customer_id = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            'codi_tenant', 'nom', 'tipologia', 'estat', 'plan',
            'moneda', 'pais', 'data_alta', 'stripe_customer_id',
            'onboarding_complet',
        ]

    def get_plan(self, obj):
        return obj.plan.nom if obj.plan_id else None

    def get_stripe_customer_id(self, obj):
        # Mai el valor real: només si el tenant té client Stripe associat.
        return bool(obj.stripe_customer_id)


class ClientDetailSerializer(ClientListSerializer):
    """Detall d'un tenant: afegeix dades fiscals, pagament i cicle de vida."""

    stripe_payment_method_id = serializers.SerializerMethodField()

    class Meta(ClientListSerializer.Meta):
        fields = ClientListSerializer.Meta.fields + [
            'rao_social', 'nif', 'adreca_fiscal', 'email_facturacio',
            'metode_pagament', 'stripe_payment_method_id',
            'data_suspensio', 'data_baixa', 'motiu_baixa', 'feature_flags',
        ]

    def get_stripe_payment_method_id(self, obj):
        return bool(obj.stripe_payment_method_id)


class ClientUpdateSerializer(serializers.ModelSerializer):
    """Camps editables d'un tenant des del backoffice.

    `codi_tenant` és immutable (identitat del tenant) i no s'inclou.
    """

    class Meta:
        model = Client
        fields = [
            'nom', 'rao_social', 'nif', 'adreca_fiscal', 'pais',
            'email_facturacio', 'metode_pagament', 'estat', 'motiu_baixa',
        ]


class PlanSerializer(serializers.ModelSerializer):
    """Pla complet, inclosos els camps de facturació per models iniciats/mes."""

    class Meta:
        model = Plan
        fields = '__all__'
