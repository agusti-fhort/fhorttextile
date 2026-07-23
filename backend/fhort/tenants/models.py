import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError
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


class CodiAuth(models.Model):
    """Codi opac d'UN SOL ÚS del login únic (F1/F2). Viu SEMPRE al schema `public`.

    PER QUÈ AL PUBLIC: el bescanvi creua orígens. Qui EMET el codi és l'autenticació
    central (que pot atendre's des de qualsevol host) i qui el CONSUMEIX és el host del
    tenant de destí. Una taula per-schema no la veurien tots dos. `fhort.tenants` és a
    SHARED_APPS i no a TENANT_APPS (`settings.py:37,63`) → les seves taules només
    existeixen a `public`, que és exactament el que aquesta peça necessita.

    PER QUÈ UNA SOLA TAULA PER A DUES MENES: el flux té dos tiquets efímers de la mateixa
    naturalesa (opac, server-side, un sol ús, TTL curt): la SELECCIÓ (multi-workspace: el
    client ha de poder triar sense re-enviar mai la contrasenya) i el BESCANVI (el codi que
    viatja a la URL i es canvia per un parell JWT). Mateixa mecànica de consum atòmic,
    mateixa neteja, mateix risc → mateixa taula amb `mena`, no dues bessones.

    PER QUÈ ES DESA EL HASH I NO EL CODI: el codi és el permís. Desar-lo en clar convertiria
    qualsevol lectura de la BD del public (dump, backup, còpia a staging) en un joc de
    credencials vives. El SHA-256 és suficient perquè el codi no és endevinable (32 bytes
    d'entropia de `secrets`): no cal cap KDF lent, i la cerca segueix sent per índex únic.

    L'ÚS ÉS ATÒMIC, no comprovat-i-després-marcat: el consum és un UPDATE condicional
    (`WHERE used_at IS NULL`) i el que compta és el nombre de files afectades. Dos bescanvis
    simultanis del mateix codi entren els dos a la comprovació però només un fa 1 fila.
    """

    MENA_SELECCIO = 'seleccio'
    MENA_BESCANVI = 'bescanvi'
    MENA_CHOICES = [
        (MENA_SELECCIO, 'Selecció de workspace'),
        (MENA_BESCANVI, 'Bescanvi per sessió'),
    ]

    #: TTL del codi de bescanvi: el temps d'una redirecció, no el d'una persona.
    TTL_BESCANVI = timedelta(seconds=60)
    #: TTL de la selecció: aquí SÍ que hi ha una persona llegint i triant.
    TTL_SELECCIO = timedelta(seconds=180)
    #: Llindar de la neteja oportunista (sense cron nou): prou per sobre del TTL màxim.
    TTL_RETENCIO = timedelta(minutes=5)

    codi_hash = models.CharField(max_length=64, unique=True)
    mena = models.CharField(max_length=10, choices=MENA_CHOICES)

    # Destí del bescanvi. Buit a les files de mena=seleccio (encara no s'ha triat).
    tenant_schema = models.CharField(max_length=63, blank=True)
    user_id = models.IntegerField(null=True, blank=True)

    # Només mena=seleccio: els workspaces on les credencials han estat VÀLIDES,
    # [{'schema': …, 'user_id': …}]. La contrasenya ja no torna a viatjar mai més.
    candidats = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)   # NULL = viu

    class Meta:
        verbose_name = "Codi d'autenticació"
        verbose_name_plural = "Codis d'autenticació"

    def __str__(self):
        return f'{self.mena} → {self.tenant_schema or "?"}'

    @property
    def ttl(self):
        return self.TTL_SELECCIO if self.mena == self.MENA_SELECCIO else self.TTL_BESCANVI


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


class TenantLink(models.Model):
    """Pont de federació entre una Marca (Brand) i un Estudi (Studio).

    LA LLEI: el token governa el PONT, mai la capacitat de treballar. El vincle
    l'emet el Brand; mentre és viu (estat=ACTIU) el pont deixa passar; aturar-lo
    o revocar-lo NO destrueix cap dada ni impedeix a l'Studio seguir treballant amb
    el seu Customer intern. Són els 3 estats legítims de la relació (llei C1 de la
    diagnosi): sense vincle / vincle viu / vincle aturat. El treball no depèn del pont.

    PER QUÈ VIU A `tenants` I NO A `backoffice`: com `CodiAuth`, el vincle creua
    orígens i ha de ser visible des dels dos costats. `fhort.tenants` és a SHARED_APPS
    → les seves taules només existeixen a `public`, que és on un vincle cross-tenant
    ha de viure. A més, `backoffice` depèn de `tenants` (no a la inversa): posar el
    vincle a `backoffice` invertiria l'única frontera neta que queda (diagnosi §5.5).

    PER QUÈ REFERÈNCIA PER CODI NU I NO PER FK: el vincle ha de sobreviure a la lectura
    des de DINS d'un tenant, on `Client` no és consultable sense `schema_context`. El
    precedent directe és `CodiAuth.tenant_schema` (un CharField, no una FK). Els
    `codi_tenant` són identitat estable de 3 chars (`Client.codi_tenant`, unique).
    """

    ESTAT_ACTIU = 'ACTIU'
    ESTAT_ATURAT = 'ATURAT'
    ESTAT_REVOCAT = 'REVOCAT'
    ESTAT_CHOICES = [
        (ESTAT_ACTIU, 'Actiu'),
        (ESTAT_ATURAT, 'Aturat'),
        (ESTAT_REVOCAT, 'Revocat'),
    ]

    #: El Brand (tipologia='marca') que EMET el vincle i és la casa canònica.
    brand_codi_tenant = models.CharField(max_length=3)
    #: L'Studio (tipologia='estudi') que treballa el catàleg del Brand a través del pont.
    studio_codi_tenant = models.CharField(max_length=3)

    #: Secret opac del pont. 32 bytes d'entropia de `secrets`, generat en crear.
    token = models.CharField(max_length=64, unique=True)
    estat = models.CharField(max_length=10, choices=ESTAT_CHOICES, default=ESTAT_ACTIU)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    #: Moment de l'última aturada/revocació (NULL mentre no s'ha aturat mai).
    aturat_at = models.DateTimeField(null=True, blank=True)
    nota = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'Vincle de federació'
        verbose_name_plural = 'Vincles de federació'
        unique_together = [('brand_codi_tenant', 'studio_codi_tenant')]

    def __str__(self):
        return f'{self.brand_codi_tenant} ↔ {self.studio_codi_tenant} ({self.estat})'

    @staticmethod
    def genera_token():
        return secrets.token_urlsafe(32)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.genera_token()
        super().save(*args, **kwargs)

    def clean(self):
        """Els dos extrems han d'existir i tenir la tipologia correcta.

        `tipologia` és aquí el primer consumidor de domini del camp (fins ara inert):
        el Brand ha de ser 'marca' i l'Studio 'estudi'. Lectura de `Client` a public
        (mateix schema: `tenants` és SHARED i `Client` és consultable sense context).
        """
        brand = Client.objects.filter(codi_tenant=self.brand_codi_tenant).first()
        if brand is None:
            raise ValidationError({'brand_codi_tenant': f"No existeix cap tenant '{self.brand_codi_tenant}'."})
        if brand.tipologia != Client.TIPOLOGIA_MARCA:
            raise ValidationError({'brand_codi_tenant': f"El tenant '{self.brand_codi_tenant}' no és una Marca (tipologia='{brand.tipologia}')."})

        studio = Client.objects.filter(codi_tenant=self.studio_codi_tenant).first()
        if studio is None:
            raise ValidationError({'studio_codi_tenant': f"No existeix cap tenant '{self.studio_codi_tenant}'."})
        if studio.tipologia != Client.TIPOLOGIA_ESTUDI:
            raise ValidationError({'studio_codi_tenant': f"El tenant '{self.studio_codi_tenant}' no és un Estudi (tipologia='{studio.tipologia}')."})

    def es_viu(self):
        """El pont deixa passar (només ACTIU)."""
        return self.estat == self.ESTAT_ACTIU

    def aturar(self):
        """Atura el pont sense destruir res. Només des d'ACTIU."""
        if self.estat != self.ESTAT_ACTIU:
            raise ValidationError(f"Només es pot aturar un vincle ACTIU (estat actual: {self.estat}).")
        from django.utils import timezone
        self.estat = self.ESTAT_ATURAT
        self.aturat_at = timezone.now()
        self.save(update_fields=['estat', 'aturat_at', 'updated_at'])

    def reactivar(self):
        """Reactiva un pont aturat. REVOCAT és terminal: no es pot reactivar."""
        if self.estat != self.ESTAT_ATURAT:
            raise ValidationError(f"Només es pot reactivar un vincle ATURAT (estat actual: {self.estat}).")
        self.estat = self.ESTAT_ACTIU
        self.aturat_at = None
        self.save(update_fields=['estat', 'aturat_at', 'updated_at'])

    def revocar(self):
        """Talla el pont de manera definitiva (estat terminal). No destrueix cap dada."""
        if self.estat == self.ESTAT_REVOCAT:
            return
        from django.utils import timezone
        self.estat = self.ESTAT_REVOCAT
        if self.aturat_at is None:
            self.aturat_at = timezone.now()
        self.save(update_fields=['estat', 'aturat_at', 'updated_at'])
