from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class Plan(models.Model):
    NOM_SOLO = 'Solo'
    NOM_STUDIO = 'Studio'
    NOM_BRAND = 'Brand'
    NOM_ENTERPRISE = 'Enterprise'
    NOM_CHOICES = [
        (NOM_SOLO, 'Solo'),
        (NOM_STUDIO, 'Studio'),
        (NOM_BRAND, 'Brand'),
        (NOM_ENTERPRISE, 'Enterprise'),
    ]

    TIPOLOGIA_ESTUDI = 'estudi'
    TIPOLOGIA_MARCA = 'marca'
    TIPOLOGIA_ENTERPRISE = 'enterprise'
    TIPOLOGIA_CHOICES = [
        (TIPOLOGIA_ESTUDI, 'Estudi'),
        (TIPOLOGIA_MARCA, 'Marca'),
        (TIPOLOGIA_ENTERPRISE, 'Enterprise'),
    ]

    nom = models.CharField(max_length=20, choices=NOM_CHOICES, unique=True)
    tipologia = models.CharField(max_length=20, choices=TIPOLOGIA_CHOICES)
    preu_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    max_models_actius = models.IntegerField()
    max_usuaris = models.IntegerField()
    storage_gb = models.IntegerField()
    ia_credits_mes = models.IntegerField()
    feature_flags = models.JSONField(default=dict, blank=True)
    actiu = models.BooleanField(default=True)

    # Facturació per models iniciats/mes (Sprint 2 — Capa 2). Reconcilia la
    # qüestió oberta: preu_mensual = quota base; models_inclosos = inclosos en
    # aquesta quota; preu_model_extra = excés per model iniciat per sobre.
    models_inclosos = models.IntegerField(default=0)
    preu_model_extra = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    moneda_pla = models.CharField(max_length=3, default='EUR')

    class Meta:
        verbose_name = 'Pla'
        verbose_name_plural = 'Plans'

    def __str__(self):
        return self.nom


class Client(TenantMixin):
    TIPOLOGIA_ESTUDI = 'estudi'
    TIPOLOGIA_MARCA = 'marca'
    TIPOLOGIA_CHOICES = [
        (TIPOLOGIA_ESTUDI, 'Estudi'),
        (TIPOLOGIA_MARCA, 'Marca'),
    ]

    UNITAT_CM = 'cm'
    UNITAT_INCH = 'inch'
    UNITAT_CHOICES = [(UNITAT_CM, 'cm'), (UNITAT_INCH, 'inch')]

    # Estats del cicle de vida del tenant (Sprint 2 — Capa 1). El booleà `actiu`
    # existent es conserva (no trencar DB/codi); `estat` és la font de veritat
    # granular i `es_actiu` fa de pont de compatibilitat.
    ESTAT_ONBOARDING = 'onboarding'
    ESTAT_ACTIU = 'actiu'
    ESTAT_SUSPES = 'suspes'
    ESTAT_BAIXA = 'baixa'
    ESTAT_CHOICES = [
        (ESTAT_ONBOARDING, 'Onboarding'),
        (ESTAT_ACTIU, 'Actiu'),
        (ESTAT_SUSPES, 'Suspès'),
        (ESTAT_BAIXA, 'Baixa'),
    ]

    # Mètode de pagament (referència; les dades sensibles viuen a Stripe).
    METODE_STRIPE_CARD = 'stripe_card'
    METODE_SEPA = 'sepa'
    METODE_PAGAMENT_CHOICES = [
        (METODE_STRIPE_CARD, 'Targeta (Stripe)'),
        (METODE_SEPA, 'SEPA'),
    ]

    nom = models.CharField(max_length=200)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='clients', null=True, blank=True)
    tipologia = models.CharField(max_length=20, choices=TIPOLOGIA_CHOICES)
    feature_flags = models.JSONField(default=dict, blank=True)
    actiu = models.BooleanField(default=True)
    data_alta = models.DateField(auto_now_add=True)
    onboarding_complet = models.BooleanField(default=False)

    moneda = models.CharField(max_length=3, default='EUR')
    unitats = models.CharField(max_length=4, choices=UNITAT_CHOICES, default=UNITAT_CM)
    idioma = models.CharField(max_length=5, default='ca')

    codi_tenant = models.CharField(max_length=3, unique=True)

    # Cicle de vida granular (Sprint 2). `actiu` (bool) es manté intacte.
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default=ESTAT_ONBOARDING)

    # Dades fiscals (facturació internacional).
    rao_social = models.CharField(max_length=200, blank=True)
    nif = models.CharField(max_length=20, blank=True)
    adreca_fiscal = models.TextField(blank=True)
    pais = models.CharField(max_length=2, default='ES')  # ISO 3166-1 alpha-2
    email_facturacio = models.EmailField(blank=True)

    # Pagaments — NOMÉS referències Stripe, mai dades sensibles.
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    metode_pagament = models.CharField(max_length=20, choices=METODE_PAGAMENT_CHOICES, blank=True)
    stripe_payment_method_id = models.CharField(max_length=100, blank=True)

    # Dates del cicle de vida.
    data_suspensio = models.DateField(null=True, blank=True)
    data_baixa = models.DateField(null=True, blank=True)
    motiu_baixa = models.TextField(blank=True)

    auto_create_schema = True
    auto_drop_schema = False

    class Meta:
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'

    def __str__(self):
        return f'{self.nom} [{self.codi_tenant}]'

    @property
    def es_actiu(self):
        """Pont de compatibilitat: codi que abans llegia `actiu` (bool)."""
        return self.estat == self.ESTAT_ACTIU


class Domain(DomainMixin):
    pass
