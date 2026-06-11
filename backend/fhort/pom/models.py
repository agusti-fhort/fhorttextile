from django.db import models


# ─────────────────────────────────────────────────────────────
# FHORT global catalog ('public' schema)
# ─────────────────────────────────────────────────────────────

class POMGlobal(models.Model):
    UNITAT_CHOICES = [('cm', 'cm'), ('inch', 'inch')]
    SCOPE_CHOICES = [
        ('HALF', 'Half'), ('FULL', 'Full'), ('CALCULATED', 'Calculated'),
    ]
    ORIENTATION_CHOICES = [
        ('HORIZONTAL', 'Horizontal'), ('VERTICAL', 'Vertical'),
        ('CIRCUMFERENCE', 'Circumference'), ('CURVED', 'Curved'),
        ('DIAGONAL', 'Diagonal'),
    ]
    STATE_CHOICES = [
        ('FLAT', 'Flat'), ('RELAXED', 'Relaxed'),
        ('STRETCHED', 'Stretched'), ('ON_BODY', 'On body'),
    ]
    LINE_CHOICES = [
        ('STRAIGHT', 'Straight'), ('CURVED', 'Curved'),
        ('ALONG CURVE', 'Along curve'), ('ANGLED', 'Angled'),
    ]
    BODY_SECTION_CHOICES = [
        ('FRONT', 'Front'), ('BACK', 'Back'), ('SIDE', 'Side'),
        ('SLEEVE', 'Sleeve'), ('BOTH', 'Both'), ('HEAD', 'Head'),
    ]

    codi = models.CharField(max_length=80, unique=True)
    nom_en = models.CharField(max_length=200)
    nom_ca = models.CharField(max_length=200)
    nom_es = models.CharField(max_length=200, blank=True)
    categoria = models.CharField(max_length=40)
    descripcio_en = models.TextField(blank=True)
    descripcio_ca = models.TextField(blank=True)
    unitat = models.CharField(max_length=4, choices=UNITAT_CHOICES, default='cm')
    actiu = models.BooleanField(default=True)

    # Sprint S12-A — extended catalog (detailed How To Measure)
    abbreviation    = models.CharField(max_length=40, blank=True)
    start_point     = models.CharField(max_length=120, blank=True)
    end_point       = models.CharField(max_length=120, blank=True)
    reference_point = models.CharField(max_length=200, blank=True)
    scope           = models.CharField(max_length=20, choices=SCOPE_CHOICES, blank=True)
    orientation     = models.CharField(max_length=20, choices=ORIENTATION_CHOICES, blank=True)
    state           = models.CharField(max_length=20, choices=STATE_CHOICES, blank=True)
    line            = models.CharField(max_length=20, choices=LINE_CHOICES, blank=True)
    body_section    = models.CharField(max_length=20, choices=BODY_SECTION_CHOICES, blank=True)
    is_key          = models.BooleanField(default=False)
    tol_prod_cm     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tol_samp_cm     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    applies_woven   = models.BooleanField(default=True)
    applies_knit    = models.BooleanField(default=True)
    applies_swim    = models.BooleanField(default=False)
    notes           = models.TextField(blank=True)
    iso_ref         = models.CharField(max_length=60, blank=True)
    # End Sprint S12-A

    # Sprint S1 — ISO 8559-1 linkage
    body_measure_iso = models.ForeignKey(
        'BodyMeasurementISO',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='poms_globals',
        help_text="Mesura corporal ISO 8559-1 equivalent"
    )
    # End Sprint S1

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
    # Sprint S13-A
    is_system = models.BooleanField(default=True,
        help_text="True = catàleg canònic, no esborrable")
    display_order = models.PositiveIntegerField(default=0)
    # Pas previ 5 — descripció de família (construcció)
    descripcio = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Tipus garment global'
        verbose_name_plural = 'Tipus garment globals'
        ordering = ['grup', 'display_order', 'codi']

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
# Per-tenant catalog (tenant schema)
# ─────────────────────────────────────────────────────────────

class POMCategory(models.Model):
    """POM categories (UPPER/LOWER/JK/CD/PL/...). Imported from master data."""

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

    # Sprint 5B.1: standard tolerance for this catalogue POM (asymmetric).
    # Copied onto BaseMeasurement.tolerancia_minus/plus when measurements are poured
    # into a model (copy-at-the-moment, like base_value_cm — not a live reference).
    tolerancia_default_minus = models.DecimalField(max_digits=5, decimal_places=2, default=0.6)
    tolerancia_default_plus = models.DecimalField(max_digits=5, decimal_places=2, default=0.6)
    pendent_revisio = models.BooleanField(
        default=False,
        verbose_name='Pendent de revisió',
        help_text="POM creat automàticament des d'importació. Requereix revisió de la patronista.",
    )
    origen_import = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Origen importació',
        help_text="Referència del model/fitxa des d'on s'ha creat aquest POM",
    )

    class Meta:
        verbose_name = 'POM (tenant)'
        verbose_name_plural = 'POMs (tenant)'

    def __str__(self):
        return f'{self.codi_client} · {self.nom_client}'

    # ── Alias properties for the sprint3/4 code ────────────────────────────
    # Resolve TECH_DEBT.md #2. Read-only — they do not work in the ORM (.filter/order_by).
    # For the ORM, use the natural FKs: pom__categoria__display_order, pom__pom_global__nom_ca.
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
        # We have no equivalent field in the current schema. If we needed to
        # distinguish "key measures", add an explicit BooleanField to the model (migration).
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

    # Sprint Size Map Setup — derivació per client
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='derived_systems',
        verbose_name='Sistema pare',
    )
    customer_codi = models.CharField(
        max_length=3, blank=True, default='',
        verbose_name='Codi client',
    )

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



    # Sprint S1 — reference body measurements
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
    """Garment families (SWIMWEAR, OUTERWEAR, BOTTOMS, ...). Imported from master data."""

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

    # Sprint S13-A — multilanguage + system flag
    nom_en = models.CharField(max_length=200, blank=True, default='')
    nom_ca = models.CharField(max_length=200, blank=True, default='')
    nom_es = models.CharField(max_length=200, blank=True, default='')
    is_system = models.BooleanField(default=False,
        help_text="True = ve del catàleg global canònic, no esborrable")

    # Sprint S1 — target and construction
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
    # Pas previ 5 — descripció de família (construcció)
    descripcio = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Tipus garment (tenant)'
        verbose_name_plural = 'Tipus garment (tenant)'

    def __str__(self):
        return f'{self.codi_client} · {self.nom_client}'


class GarmentPOMMap(models.Model):
    # Migration família → item (COMPLETADA, PAS 6): la pertinença POM viu únicament a
    # garment_type_item. El FK legacy garment_type i el seu unique_together s'han eliminat
    # (migració 0016) un cop migrats i esborrats els 95 mapes legacy.
    # db_constraint=False: 'pom' és app SHARED (taula també a 'public'), però 'tasks' és tenant-only
    # → un constraint de BD cap a tasks_garmenttypeitem petaria a 'public'. L'FK és lògic (ORM);
    # el CASCADE l'emula Django al collector. Patró estàndard per a FK que creuen shared↔tenant.
    garment_type_item = models.ForeignKey('tasks.GarmentTypeItem', on_delete=models.CASCADE,
                                          related_name='pom_maps', null=True, blank=True,
                                          db_constraint=False)
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT, related_name='garment_maps')
    obligatori = models.BooleanField(default=False)
    is_key = models.BooleanField(default=False)
    # Sprint Excel-Map · nivell de la cel·la de l'Excel (K/M/O/D). Metadada addicional,
    # independent d'is_key/obligatori; el loader (load_garment_pom_map) escriu tots tres coherents.
    nivell = models.CharField(
        max_length=1, blank=True, default='O',
        choices=[('K', 'Key'), ('M', 'Mandatory'), ('O', 'Optional'), ('D', 'Detail-dependent')],
    )
    ordre = models.PositiveIntegerField(default=0)
    # Migration família → item: clons de germà es marquen per revisió (Montse ajusta el delta).
    pendent_revisio = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Mapa garment ↔ POM'
        verbose_name_plural = 'Mapes garment ↔ POM'
        ordering = ['garment_type_item', 'ordre']
        unique_together = [('garment_type_item', 'pom')]

    def __str__(self):
        anchor = self.garment_type_item.code if self.garment_type_item_id else '?'
        return f'{anchor} · {self.pom.codi_client}'


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



    # Sprint S1 — target, construction, versioning
    # Sprint S16-A — `target` FK kept temporarily (related_name renamed
    # to *_legacy). The new `targets` M2M is the authoritative source; the FK will be
    # removed in a later sprint once the consuming code is updated.
    target = models.ForeignKey(
        'Target', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='grading_rule_sets_legacy',
    )
    targets = models.ManyToManyField(
        'Target',
        blank=True,
        related_name='grading_rule_sets',
        verbose_name='Targets aplicables',
        help_text='Un RuleSet pot aplicar a múltiples targets (ex: BABY_GIRL+BABY_BOY+BABY_UNISEX).',
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
    # Sprint S16-A — decimals 4 → 2 (real precision for garment measurements in cm)
    valor_base = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    increment = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    valors_step = models.JSONField(null=True, blank=True)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Regla grading'
        verbose_name_plural = 'Regles grading'
        unique_together = [('rule_set', 'pom')]

    def __str__(self):
        return f'{self.rule_set.nom} · {self.pom.codi_client} ({self.logica})'


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 3 — Grading engine (catalog data shared with tenants)
# BaseMeasurement lives in models_app (FK Model), GradedSpec lives in fitting (FK GradingVersion).
# ─────────────────────────────────────────────────────────────────────────────

class GradingException(models.Model):
    """Specific override per (POM, size) within a GradingRuleSet."""
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
    """Online Welford statistic per (codi_client, garment_type, POM, size).

    Accumulates mean/M2 without storing individual values. It is updated
    every time a fitting is closed and a line has been modified.

    Sprint 5B.3: keyed by `codi_client` (the end brand-client within the tenant,
    from Model.codi_client), not by the tenant-level `client` FK (which lumped all
    brands of a tenant together). `client` is kept nullable for legacy/optional use.
    """
    client = models.ForeignKey(
        'tenants.Client', on_delete=models.CASCADE, related_name='mesures_perfil',
        null=True, blank=True,
    )
    codi_client = models.CharField(max_length=80, blank=True, default='')
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
        unique_together = [('codi_client', 'garment_type', 'pom', 'talla')]
        ordering = ['codi_client', 'garment_type', 'pom', 'talla']

    def __str__(self):
        return f'{self.codi_client} · gt{self.garment_type_id} · {self.pom.codi_client} @ {self.talla} (n={self.n_mostres})'



# =============================================================================
# SPRINT S1 — New global models (public schema)
# Added to fhort/pom/models.py
# =============================================================================

class FitType(models.Model):
    """Fit type (Slim / Regular / Loose / Oversized). Public schema."""
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
    """Target population of a garment. Public schema."""
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
    """Fabric construction type. Determines grading and tolerances."""
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
    """Body measurements defined by ISO 8559-1:2017. Public schema."""
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
    Sizing profile: combination target+garment+construction+fit -> size_system+grading.
    It is the heart of the SizingProfileWizard.
    Public (global) schema — tenants can create their own versions via parent_profile.
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


class GradingRuleHistory(models.Model):
    """
    Change history for a GradingRule.
    Records who changed which POM, from which value to which, and when.
    """
    rule_set        = models.ForeignKey('GradingRuleSet', on_delete=models.CASCADE,
                        related_name='history')
    pom             = models.ForeignKey('POMGlobal', on_delete=models.SET_NULL,
                        null=True, related_name='rule_history')
    pom_codi        = models.CharField(max_length=20, blank=True,
                        help_text="Codi POM cached per si el POM s'elimina")
    valor_anterior  = models.DecimalField(max_digits=6, decimal_places=2)
    valor_nou       = models.DecimalField(max_digits=6, decimal_places=2)
    logica_anterior = models.CharField(max_length=20, blank=True)
    logica_nova     = models.CharField(max_length=20, blank=True)
    modificat_per_id = models.IntegerField(null=True, blank=True,
                        help_text="ID usuari cross-schema")
    modificat_per_nom = models.CharField(max_length=200, blank=True)
    modificat_at    = models.DateTimeField(auto_now_add=True)
    nota            = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-modificat_at']

    def __str__(self):
        return (f"{self.pom_codi}: {self.valor_anterior} → {self.valor_nou} "
                f"({self.modificat_at.strftime('%Y-%m-%d %H:%M')})")
