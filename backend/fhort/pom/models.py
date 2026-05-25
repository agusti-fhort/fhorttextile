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
    size_system = models.ForeignKey(SizeSystem, on_delete=models.PROTECT, related_name='grading_rule_sets')
    actiu = models.BooleanField(default=True)

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
