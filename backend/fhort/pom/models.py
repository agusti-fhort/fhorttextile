from django.db import models


# ─────────────────────────────────────────────────────────────
# Catàleg global FHORT (esquema 'public')
# ─────────────────────────────────────────────────────────────

class POMGlobal(models.Model):
    UNITAT_CHOICES = [('cm', 'cm'), ('inch', 'inch')]

    codi = models.CharField(max_length=80, unique=True)
    nom_en = models.CharField(max_length=200)
    nom_ca = models.CharField(max_length=200)
    nom_es = models.CharField(max_length=200)
    categoria = models.CharField(max_length=40)
    descripcio_en = models.TextField(blank=True)
    unitat = models.CharField(max_length=4, choices=UNITAT_CHOICES, default='cm')
    actiu = models.BooleanField(default=True)



    # Sprint S1 — ISO 8559-1 linkage
    body_measure_iso = models.ForeignKey(
        'BodyMeasurementISO',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='poms_globals',
        help_text="Mesura corporal ISO 8559-1 equivalent"
    )
    # Fi Sprint S1

    class Meta:
        verbose_name = 'POM global'
        verbose_name_plural = 'POMs globals'

    def __str__(self):
        return f'{self.codi} · {self.nom_en}'


class GarmentTypeGlobal(models.Model):
    codi = models.CharField(max_length=80, unique=True)
    nom_en = models.CharField(max_length=200)
    nom_ca = models.CharField(max_length=200)
    nom_es = models.CharField(max_length=200)
    grup = models.CharField(max_length=40)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tipus garment global'
        verbose_name_plural = 'Tipus garment globals'

    def __str__(self):
        return f'{self.codi} · {self.nom_en}'


class TascaGlobal(models.Model):
    FASE_CHOICES = [
        ('Proto', 'Proto'),
        ('Fit', 'Fit'),
        ('SizeSet', 'SizeSet'),
        ('PP', 'PP'),
        ('TOP', 'TOP'),
    ]
    TIPUS_CHOICES = [
        ('Interna', 'Interna'),
        ('Externa', 'Externa'),
        ('Validacio', 'Validació'),
    ]

    codi = models.CharField(max_length=80, unique=True)
    nom_en = models.CharField(max_length=200)
    nom_ca = models.CharField(max_length=200)
    nom_es = models.CharField(max_length=200)
    fase = models.CharField(max_length=20, choices=FASE_CHOICES)
    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES)
    minuts_estandard = models.PositiveIntegerField()
    es_gate = models.BooleanField(default=False)
    resultat_gate_opcions = models.JSONField(default=list, blank=True)
    facturable = models.BooleanField(default=False)
    ordre_base = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tasca global'
        verbose_name_plural = 'Tasques globals'
        ordering = ['ordre_base', 'codi']

    def __str__(self):
        return f'{self.codi} · {self.nom_ca}'


class POMEstadisticaGlobal(models.Model):
    pom_global = models.ForeignKey(POMGlobal, on_delete=models.CASCADE, related_name='estadistiques_globals')
    garment_type_global = models.ForeignKey(GarmentTypeGlobal, on_delete=models.CASCADE, related_name='estadistiques_globals')
    n = models.PositiveIntegerField(default=0)
    mitjana = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    m2 = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    segment = models.CharField(max_length=20)
    talla_label = models.CharField(max_length=30)

    class Meta:
        verbose_name = 'Estadística POM global'
        verbose_name_plural = 'Estadístiques POM globals'
        unique_together = [('pom_global', 'garment_type_global', 'segment', 'talla_label')]

    def __str__(self):
        return f'{self.pom_global.codi} · {self.garment_type_global.codi} · {self.segment}/{self.talla_label}'


# ─────────────────────────────────────────────────────────────
# Catàleg per-tenant (esquema del tenant)
# ─────────────────────────────────────────────────────────────

class POMCategory(models.Model):
    """Categories de POMs (UPPER/LOWER/JK/CD/PL/...). Importat del master data."""

    codi = models.CharField(max_length=20, unique=True)
    nom_en = models.CharField(max_length=120, blank=True)
    nom_ca = models.CharField(max_length=120, blank=True)
    descripcio = models.TextField(blank=True)
    body_area = models.CharField(max_length=20, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Categoria POM'
        verbose_name_plural = 'Categories POM'
        ordering = ['display_order', 'codi']

    def __str__(self):
        return f'{self.codi} · {self.nom_ca or self.nom_en}'


class POMMaster(models.Model):
    pom_global = models.ForeignKey(
        POMGlobal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='masters',
    )
    categoria = models.ForeignKey(
        POMCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='poms',
    )
    codi_client = models.CharField(max_length=30)
    nom_client = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'POM (tenant)'
        verbose_name_plural = 'POMs (tenant)'

    def __str__(self):
        return f'{self.codi_client} · {self.nom_client}'

    # ── Properties d'alias per al codi sprint3/4 ────────────────────────────
    # Resolen TECH_DEBT.md #2. Read-only — no funcionen en ORM (.filter/order_by).
    # Per ORM, usar les FKs naturals: pom__categoria__display_order, pom__pom_global__nom_ca.
    @property
    def pom_code(self):
        return self.codi_client or (self.pom_global.codi if self.pom_global_id else '')

    @property
    def name_cat(self):
        if self.pom_global_id and self.pom_global.nom_ca:
            return self.pom_global.nom_ca
        return self.nom_client

    @property
    def name_en(self):
        if self.pom_global_id and self.pom_global.nom_en:
            return self.pom_global.nom_en
        return self.nom_client

    @property
    def display_order(self):
        return self.categoria.display_order if self.categoria_id else 999

    @property
    def is_key_measure(self):
        # No tenim camp equivalent al schema actual. Si calgués distingir
        # "key measures", afegir un BooleanField explícit al model (migració).
        return False


class POMEstadisticaTenant(models.Model):
    pom = models.ForeignKey(POMMaster, on_delete=models.CASCADE, related_name='estadistiques')
    garment_type = models.CharField(max_length=80)
    talla_label = models.CharField(max_length=30)
    n = models.PositiveIntegerField(default=0)
    mitjana = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    m2 = models.DecimalField(max_digits=16, decimal_places=4, default=0)

    class Meta:
        verbose_name = 'Estadística POM tenant'
        verbose_name_plural = 'Estadístiques POM tenant'
        unique_together = [('pom', 'garment_type', 'talla_label')]

    def __str__(self):
        return f'{self.pom.codi_client} · {self.garment_type}/{self.talla_label}'


class SizeSystem(models.Model):
    codi = models.CharField(max_length=60, unique=True)
    nom = models.CharField(max_length=120)
    descripcio = models.TextField(blank=True)
    actiu = models.BooleanField(default=True)



    # Sprint S1
    target = models.ForeignKey(
        'Target', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='size_systems',
    )
    base_unit = models.CharField(
        max_length=20, blank=True,
        choices=[
            ('ALPHA','Alpha (XS/S/M/L...)'),
            ('NUMERIC_EU','Numeric EU (34/36/38...)'),
            ('NUMERIC_US','Numeric US (0/2/4...)'),
            ('CM_HEIGHT','CM Height (50/56/62...)'),
            ('MONTHS','Months (0M/3M/6M...)'),
            ('AGE_YEARS','Age Years (6Y/8Y...)'),
        ],
        help_text="Tipus de designacio de talles"
    )
    norma_ref = models.CharField(max_length=50, blank=True,
        help_text="Ex: ISO 8559-2, ASTM D5585")
    # Fi Sprint S1

    class Meta:
        verbose_name = 'Sistema de talles'
        verbose_name_plural = 'Sistemes de talles'

    def __str__(self):
        return self.codi


class SizeDefinition(models.Model):
    size_system = models.ForeignKey(SizeSystem, on_delete=models.CASCADE, related_name='talles')
    etiqueta = models.CharField(max_length=30)
    ordre = models.PositiveIntegerField(default=0)
    valor_numeric = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)



    # Sprint S1 — mesures corporals de referencia
    body_height_cm  = models.DecimalField(max_digits=5, decimal_places=1,
                        null=True, blank=True,
                        help_text="Alcada corporal de referencia (ISO 8559-1)")
    body_bust_cm    = models.DecimalField(max_digits=5, decimal_places=1,
                        null=True, blank=True,
                        help_text="Perimetre pit (bust/chest) corporal")
    body_waist_cm   = models.DecimalField(max_digits=5, decimal_places=1,
                        null=True, blank=True)
    body_hip_cm     = models.DecimalField(max_digits=5, decimal_places=1,
                        null=True, blank=True)
    age_months_min  = models.IntegerField(null=True, blank=True,
                        help_text="Mesos minim per a baby/kids sizes")
    age_months_max  = models.IntegerField(null=True, blank=True)
    # Fi Sprint S1

    class Meta:
        verbose_name = 'Talla'
        verbose_name_plural = 'Talles'
        ordering = ['size_system', 'ordre']
        unique_together = [('size_system', 'etiqueta')]

    def __str__(self):
        return f'{self.size_system.codi} · {self.etiqueta}'


class GarmentGroup(models.Model):
    """Famílies de prendes (SWIMWEAR, OUTERWEAR, BOTTOMS, ...). Importat del master data."""

    codi = models.CharField(max_length=40, unique=True)
    nom = models.CharField(max_length=120)
    descripcio = models.TextField(blank=True)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Família de garment'
        verbose_name_plural = 'Famílies de garment'
        ordering = ['codi']

    def __str__(self):
        return f'{self.codi} · {self.nom}'


class GarmentType(models.Model):
    garment_type_global = models.ForeignKey(
        GarmentTypeGlobal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tenant_types',
    )
    codi_client = models.CharField(max_length=60)
    nom_client = models.CharField(max_length=120)
    grup = models.CharField(max_length=40)
    actiu = models.BooleanField(default=True)



    # Sprint S1 — target i construccio
    targets_recomanats = models.ManyToManyField(
        'Target',
        blank=True,
        related_name='garment_types',
    )
    construccio_habitual = models.CharField(
        max_length=50, blank=True,
        help_text="Ex: WOVEN, KNIT, BOTH, STRETCH_KNIT"
    )
    # Fi Sprint S1

    class Meta:
        verbose_name = 'Tipus garment (tenant)'
        verbose_name_plural = 'Tipus garment (tenant)'

    def __str__(self):
        return f'{self.codi_client} · {self.nom_client}'


class GarmentPOMMap(models.Model):
    garment_type = models.ForeignKey(GarmentType, on_delete=models.CASCADE, related_name='pom_maps')
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT, related_name='garment_maps')
    obligatori = models.BooleanField(default=False)
    is_key = models.BooleanField(default=False)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Mapa garment ↔ POM'
        verbose_name_plural = 'Mapes garment ↔ POM'
        ordering = ['garment_type', 'ordre']
        unique_together = [('garment_type', 'pom')]

    def __str__(self):
        return f'{self.garment_type.codi_client} · {self.pom.codi_client}'


class GradingRuleSet(models.Model):
    nom = models.CharField(max_length=120)
    garment_group = models.ForeignKey(
        GarmentGroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='grading_rule_sets',
    )
    size_system = models.ForeignKey(SizeSystem, on_delete=models.PROTECT, null=True, blank=True, related_name='grading_rule_sets')
    actiu = models.BooleanField(default=True)



    # Sprint S1 — target, construccio, versioning
    target = models.ForeignKey(
        'Target', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='grading_rule_sets',
    )
    construction = models.ForeignKey(
        'ConstructionType', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='grading_rule_sets',
    )
    fit_type = models.ForeignKey(
        'FitType', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='grading_rule_sets',
    )
    is_system_default = models.BooleanField(default=False,
        help_text="True = ve del seed data estandard ISO")
    parent_version = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='versions',
        help_text="NULL = original estandard. Apunta al pare si es versio client."
    )
    version_number = models.IntegerField(default=1)
    codi_sistema = models.CharField(max_length=50, blank=True,
        help_text="Codi de referencia — ex: EU_WOVEN_WOMAN_REGULAR")
    # Fi Sprint S1

    class Meta:
        verbose_name = 'Joc de regles grading'
        verbose_name_plural = 'Jocs de regles grading'

    def __str__(self):
        return self.nom


class GradingRule(models.Model):
    LOGICA_LINEAR = 'LINEAR'
    LOGICA_STEP = 'STEP'
    LOGICA_FIXED = 'FIXED'
    LOGICA_ZERO = 'ZERO'
    LOGICA_EXCEPTION = 'EXCEPTION'
    LOGICA_CHOICES = [
        (LOGICA_LINEAR, 'Linear'),
        (LOGICA_STEP, 'Step'),
        (LOGICA_FIXED, 'Fixed'),
        (LOGICA_ZERO, 'Zero'),
        (LOGICA_EXCEPTION, 'Exception'),
    ]

    rule_set = models.ForeignKey(GradingRuleSet, on_delete=models.CASCADE, related_name='regles')
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT, related_name='regles_grading')
    talla_base = models.ForeignKey(SizeDefinition, on_delete=models.PROTECT, related_name='regles_base')
    logica = models.CharField(max_length=20, choices=LOGICA_CHOICES)
    valor_base = models.DecimalField(max_digits=10, decimal_places=4)
    increment = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    valors_step = models.JSONField(null=True, blank=True)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Regla grading'
        verbose_name_plural = 'Regles grading'
        unique_together = [('rule_set', 'pom')]

    def __str__(self):
        return f'{self.rule_set.nom} · {self.pom.codi_client} ({self.logica})'


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 3 — Motor de grading (dades de catàleg compartides amb tenants)
# BaseMeasurement viu a models_app (FK Model), GradedSpec viu a fitting (FK GradingVersion).
# ─────────────────────────────────────────────────────────────────────────────

class GradingException(models.Model):
    """Override puntual per (POM, talla) dins d'un GradingRuleSet."""
    rule_set = models.ForeignKey(GradingRuleSet, on_delete=models.CASCADE, related_name='exceptions')
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT, related_name='grading_exceptions')
    size_label = models.CharField(max_length=20)
    value_cm = models.FloatField()
    is_active = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Excepció de grading'
        verbose_name_plural = 'Excepcions de grading'
        unique_together = [('rule_set', 'pom', 'size_label')]

    def __str__(self):
        return f'{self.rule_set.nom} · {self.pom.codi_client} @ {self.size_label}'


class ClientMesuraPerfil(models.Model):
    """Estadística Welford online per (client, garment_type, POM, talla).

    Acumula mean/M2 sense guardar valors individuals. Es va actualitzant
    cada vegada que un fitting es tanca i una línia ha estat modificada.
    """
    client = models.ForeignKey('tenants.Client', on_delete=models.CASCADE, related_name='mesures_perfil')
    garment_type = models.ForeignKey(GarmentType, on_delete=models.CASCADE, related_name='mesures_perfil')
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT, related_name='mesures_perfil')
    talla = models.CharField(max_length=20)
    n_mostres = models.PositiveIntegerField(default=0)
    mitjana = models.FloatField(default=0.0)
    m2_acum = models.FloatField(default=0.0)   # Welford running M2
    desviacio = models.FloatField(default=0.0)
    darrera_actualitzacio = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil mesures client'
        verbose_name_plural = 'Perfils mesures client'
        unique_together = [('client', 'garment_type', 'pom', 'talla')]
        ordering = ['client', 'garment_type', 'pom', 'talla']

    def __str__(self):
        return f'{self.client_id} · gt{self.garment_type_id} · {self.pom.codi_client} @ {self.talla} (n={self.n_mostres})'



# =============================================================================
# SPRINT S1 — Nous models globals (schema public)
# Afegit a fhort/pom/models.py
# =============================================================================

class FitType(models.Model):
    """Tipus de fit (Slim / Regular / Loose / Oversized). Schema public."""
    CODI_CHOICES = [
        ('SLIM','Slim'),
        ('REGULAR','Regular'),
        ('RELAXED','Relaxed'),
        ('LOOSE','Loose'),
        ('OVERSIZED','Oversized'),
    ]
    codi          = models.CharField(max_length=20, unique=True, choices=CODI_CHOICES)
    nom_en        = models.CharField(max_length=100)
    nom_cat       = models.CharField(max_length=100, blank=True)
    nom_es        = models.CharField(max_length=100, blank=True)
    descripcio_en = models.TextField(blank=True)
    display_order = models.IntegerField(default=0)

    # Sprint S1 — ease fields
    ease_bust_cm  = models.DecimalField(max_digits=5, decimal_places=1,
                       null=True, blank=True,
                       help_text="Ease estandar pit en cm")
    ease_waist_cm = models.DecimalField(max_digits=5, decimal_places=1,
                       null=True, blank=True)
    ease_hip_cm   = models.DecimalField(max_digits=5, decimal_places=1,
                       null=True, blank=True)
    ease_thigh_cm = models.DecimalField(max_digits=5, decimal_places=1,
                       null=True, blank=True)
    client_definible = models.BooleanField(default=False,
                       help_text="Si True, el client pot crear instancies propies")

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.nom_en


class Target(models.Model):
    """Poblacio objectiu d'una peca de vestir. Schema public."""
    CODI_CHOICES = [
        ('WOMAN','Woman'),('MAN','Man'),('UNISEX_ADULT','Unisex Adult'),
        ('BABY_GIRL','Baby Girl'),('BABY_BOY','Baby Boy'),('BABY_UNISEX','Baby Unisex'),
        ('TODDLER_GIRL','Toddler Girl'),('TODDLER_BOY','Toddler Boy'),
        ('GIRL','Girl'),('BOY','Boy'),
        ('TEEN_GIRL','Teen Girl'),('TEEN_BOY','Teen Boy'),
        ('MATERNITY','Maternity'),
    ]
    PRIMARY_DIM_CHOICES = [
        ('BUST','Bust girth'),('CHEST','Chest girth'),
        ('HEIGHT_CM','Height (cm)'),('WAIST','Waist girth'),
    ]
    codi            = models.CharField(max_length=20, unique=True, choices=CODI_CHOICES)
    nom_en          = models.CharField(max_length=100)
    nom_cat         = models.CharField(max_length=100, blank=True)
    nom_es          = models.CharField(max_length=100, blank=True)
    age_min_months  = models.IntegerField(null=True, blank=True)
    age_max_months  = models.IntegerField(null=True, blank=True)
    primary_dimension = models.CharField(max_length=20, choices=PRIMARY_DIM_CHOICES, default='BUST')
    display_order   = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.nom_en

    @property
    def is_adult(self):
        return self.age_min_months is None

    @property
    def is_baby(self):
        return self.age_max_months is not None and self.age_max_months <= 36


class ConstructionType(models.Model):
    """Tipus de construccio de teixit. Determina grading i tolerancies."""
    CODI_CHOICES = [
        ('WOVEN','Woven (Pla)'),
        ('KNIT','Knit (Punt Jersey)'),
        ('STRETCH_KNIT','Stretch Knit (Punt Elastic)'),
        ('TECHNICAL','Technical'),
    ]
    codi                    = models.CharField(max_length=20, unique=True, choices=CODI_CHOICES)
    nom_en                  = models.CharField(max_length=100)
    nom_cat                 = models.CharField(max_length=100, blank=True)
    nom_es                  = models.CharField(max_length=100, blank=True)
    mesures_en_mitja        = models.BooleanField(default=False,
                                help_text="Knit specs typically use HALF measurements")
    tolerancia_critica_cm   = models.DecimalField(max_digits=4, decimal_places=2, default=0.6)
    tolerancia_secundaria_cm= models.DecimalField(max_digits=4, decimal_places=2, default=0.6)
    display_order           = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.nom_en


class BodyMeasurementISO(models.Model):
    """Mesures corporals definides per ISO 8559-1:2017. Schema public."""
    CATEGORIA_CHOICES = [
        ('VERTICAL','Vertical measurements (§5.1)'),
        ('WIDTH_DEPTH','Widths and depths (§5.2)'),
        ('GIRTH','Girth / circumference (§5.3)'),
        ('SURFACE','Surface measurements (§5.4)'),
        ('HAND_FOOT','Hand and foot (§5.5)'),
        ('OTHER','Other (§5.6)'),
        ('CALCULATED','Calculated (§5.7)'),
    ]
    codi_iso        = models.CharField(max_length=20, blank=True,
                        help_text="Referencia ISO 8559-1 — ex: 5.3.4")
    codi_intern     = models.CharField(max_length=50, unique=True,
                        help_text="Codi FHORT intern — ex: BUST_GIRTH")
    nom_en          = models.CharField(max_length=200,
                        help_text="Nom EN (idioma de treball)")
    nom_cat         = models.CharField(max_length=200, blank=True)
    nom_es          = models.CharField(max_length=200, blank=True)
    categoria       = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    htm_en          = models.TextField(blank=True,
                        help_text="How To Measure — instruccions completes EN")
    figura_iso      = models.CharField(max_length=20, blank=True,
                        help_text="Figura de la norma — ex: Fig. 62")
    es_primaria_iso = models.BooleanField(default=False,
                        help_text="Es dimensio primaria per designacio de talla (ISO 8559-2)")
    actiu           = models.BooleanField(default=True)

    class Meta:
        ordering = ['categoria', 'codi_iso']

    def __str__(self):
        return f"{self.codi_iso} — {self.nom_en}"


class SizingProfile(models.Model):
    """
    Perfil de sizing: combinacio target+garment+construction+fit -> size_system+grading.
    Es el cor del SizingProfileWizard.
    Schema public (global) — els tenants poden crear versions propies via parent_profile.
    """
    target           = models.ForeignKey('Target', on_delete=models.PROTECT,
                         related_name='sizing_profiles')
    garment_type     = models.ForeignKey('GarmentType', on_delete=models.PROTECT,
                         related_name='sizing_profiles')
    construction     = models.ForeignKey('ConstructionType', on_delete=models.PROTECT,
                         related_name='sizing_profiles')
    fit_type         = models.ForeignKey('FitType', on_delete=models.PROTECT,
                         related_name='sizing_profiles')
    size_system      = models.ForeignKey('SizeSystem', on_delete=models.PROTECT,
                         related_name='sizing_profiles')
    grading_rule_set = models.ForeignKey('GradingRuleSet', on_delete=models.PROTECT,
                         related_name='sizing_profiles')
    is_default       = models.BooleanField(default=True,
                         help_text="El sistema suggereix aquest perfil per defecte")
    parent_profile   = models.ForeignKey('self', null=True, blank=True,
                         on_delete=models.SET_NULL, related_name='versions',
                         help_text="NULL = perfil estandard. Apunta al pare si es versio client.")
    version          = models.IntegerField(default=1)
    modified_by_id   = models.IntegerField(null=True, blank=True,
                         help_text="ID de l'usuari que ha modificat (cross-schema)")
    modified_at      = models.DateTimeField(null=True, blank=True)
    notes            = models.TextField(blank=True)

    class Meta:
        ordering = ['target__display_order', 'garment_type__nom_client']

    def __str__(self):
        return (f"{self.target.nom_en} | {self.garment_type.nom_en} | "
                f"{self.construction.nom_en} | {self.fit_type.nom_en}")
