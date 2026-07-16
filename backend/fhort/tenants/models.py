from django.db import models
from django_tenants.models import DomainMixin, TenantMixin

# Estats membres de la UE (ISO 3166-1 alpha-2). Pivot per al règim de VAT.
PAISOS_UE = frozenset({
    'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR',
    'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK',
    'SI', 'ES', 'SE',
})


class Plan(models.Model):
    NOM_FREE = 'Free'
    NOM_SOLO = 'Solo'
    NOM_STUDIO = 'Studio'
    NOM_BRAND = 'Brand'
    NOM_ENTERPRISE = 'Enterprise'
    NOM_CHOICES = [
        # F3-B1: 'Free' absorbit des de F1 (preu 0, sense lookup_keys a Stripe;
        # la fila Plan Free la sembra F3). Enterprise queda fora del catàleg públic.
        (NOM_FREE, 'Free'),
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

    # F1 (P-PRICE) — ganxo amb el catàleg de Stripe. NO és preu: és el punter al
    # lookup_key de Stripe (font de veritat del preu). La BD FHORT no guarda imports.
    # Sense seed encara (això és fase posterior amb la fitxa de client): només el ganxo.
    stripe_lookup_platform = models.CharField(max_length=100, null=True, blank=True)
    stripe_lookup_model = models.CharField(max_length=100, null=True, blank=True)

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

    # Fiscalitat internacional (Sprint 3).
    TIPUS_B2B = 'b2b'
    TIPUS_B2C = 'b2c'
    TIPUS_CLIENT_CHOICES = [(TIPUS_B2B, 'B2B'), (TIPUS_B2C, 'B2C')]

    REGIM_ESPANYOL = 'espanyol'
    REGIM_REVERSE_CHARGE_UE = 'reverse_charge_ue'
    REGIM_OSS_UE = 'oss_ue'
    REGIM_FORA_UE = 'fora_ue'
    REGIM_VAT_CHOICES = [
        (REGIM_ESPANYOL, 'IVA Espanyol'),
        (REGIM_REVERSE_CHARGE_UE, 'Reverse Charge UE'),
        (REGIM_OSS_UE, 'OSS UE'),
        (REGIM_FORA_UE, 'Fora UE'),
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
    adreca_fiscal = models.TextField(blank=True)  # LEGACY: substituït per l'adreça estructurada; es buidarà via migració de dades.
    pais = models.CharField(max_length=2, default='ES')  # ISO 3166-1 alpha-2 — pivot fiscal
    email_facturacio = models.EmailField(blank=True)

    # Adreça estructurada internacional (Sprint 3).
    adreca_linia1 = models.CharField(max_length=200, blank=True)
    adreca_linia2 = models.CharField(max_length=200, blank=True)
    ciutat = models.CharField(max_length=100, blank=True)
    estat_provincia = models.CharField(max_length=100, blank=True)
    codi_postal = models.CharField(max_length=20, blank=True)

    # VAT internacional (Sprint 3). regim_vat es deriva via recalcular_regim_vat().
    vat_number = models.CharField(
        max_length=50, blank=True,
        help_text='NIF fiscal internacional (VAT/EIN/etc.)',
    )
    vat_validat = models.BooleanField(default=False)
    vat_validat_data = models.DateTimeField(null=True, blank=True)
    tipus_client = models.CharField(
        max_length=10, blank=True, choices=TIPUS_CLIENT_CHOICES, default=TIPUS_B2B,
    )
    regim_vat = models.CharField(max_length=30, blank=True, choices=REGIM_VAT_CHOICES)

    # Pagaments — NOMÉS referències Stripe, mai dades sensibles.
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    metode_pagament = models.CharField(max_length=20, choices=METODE_PAGAMENT_CHOICES, blank=True)
    stripe_payment_method_id = models.CharField(max_length=100, blank=True)

    # Dates del cicle de vida.
    data_suspensio = models.DateField(null=True, blank=True)
    data_baixa = models.DateField(null=True, blank=True)
    motiu_baixa = models.TextField(blank=True)

    # Gratuïtat / context comercial (Sprint 3).
    gratis_fins = models.DateField(
        null=True, blank=True,
        help_text='Null=gratuïtat perpètua. Data=prova/promoció fins aquella data.',
    )
    nota_comercial = models.TextField(
        blank=True,
        help_text='Context comercial intern: motiu prova, acord especial, etc.',
    )

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

    @property
    def es_gratuit(self):
        """True si el tenant NO s'ha de facturar aquest mes: gratuïtat perpètua
        (gratis_fins=None) o prova/promoció encara vigent (gratis_fins>=avui)."""
        from django.utils import timezone
        return self.gratis_fins is None or self.gratis_fins >= timezone.now().date()

    def recalcular_regim_vat(self):
        """Deriva regim_vat de pais + tipus_client + vat_number."""
        if self.pais == 'ES':
            self.regim_vat = self.REGIM_ESPANYOL
        elif self.pais in PAISOS_UE:
            if self.tipus_client == self.TIPUS_B2B and self.vat_number:
                self.regim_vat = self.REGIM_REVERSE_CHARGE_UE
            else:
                self.regim_vat = self.REGIM_OSS_UE
        else:
            self.regim_vat = self.REGIM_FORA_UE
        return self.regim_vat

    def save(self, *args, **kwargs):
        # Manté regim_vat sempre coherent. super() (TenantMixin) gestiona la
        # creació del schema quan auto_create_schema=True.
        self.recalcular_regim_vat()
        super().save(*args, **kwargs)


class Domain(DomainMixin):
    pass


class TenantContacte(models.Model):
    """Contactes d'un tenant (registre al public; mai dins del seu schema)."""

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contactes')
    nom = models.CharField(max_length=100)
    cognom = models.CharField(max_length=100, blank=True)
    carrec = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    telefon = models.CharField(max_length=30, blank=True)
    principal = models.BooleanField(default=False)

    class Meta:
        ordering = ['-principal', 'nom']
        constraints = [
            models.UniqueConstraint(
                fields=['client'],
                condition=models.Q(principal=True),
                name='unic_contacte_principal_per_client',
            ),
        ]

    def __str__(self):
        return f'{self.nom} {self.cognom}'.strip()
