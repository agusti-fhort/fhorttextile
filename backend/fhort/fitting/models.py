from django.db import models
from django.conf import settings


class SizeFitting(models.Model):
    TIPUS_CHOICES = [
        ('Proto', 'Proto'),
        ('Fit', 'Fit'),
        ('SizeSet', 'SizeSet'),
        ('PP', 'PP'),
        ('TOP', 'TOP'),
    ]
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('BaseOberta', 'Base oberta'),
        ('BaseTancada', 'Base tancada'),
        ('TallesGenerades', 'Talles generades'),
        ('Tancat', 'Tancat'),
    ]

    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='size_fittings')
    numero = models.PositiveIntegerField()
    codi = models.CharField(max_length=60, unique=True)
    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES)
    sf_pare = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fills',
    )

    estat = models.CharField(max_length=30, choices=ESTAT_CHOICES, default='Pendent')

    data_creacio = models.DateTimeField(auto_now_add=True)
    data_tancament = models.DateTimeField(null=True, blank=True)
    creat_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.PROTECT,
        related_name='size_fittings_creats',
    )

    notes = models.TextField(null=True, blank=True)

    # --- Sprint 1A: new fields ---
    base_tancada = models.BooleanField(default=False)
    data_tancament_base = models.DateTimeField(null=True, blank=True)
    # --- End Sprint 1A ---

    class Meta:
        verbose_name = 'Size & Fitting'
        verbose_name_plural = 'Size & Fittings'
        ordering = ['model', 'numero']
        unique_together = [('model', 'numero')]

    def __str__(self):
        return self.codi


class GradingVersion(models.Model):
    size_fitting = models.ForeignKey(SizeFitting, on_delete=models.CASCADE, related_name='grading_versions')
    nom = models.CharField(max_length=100, blank=True, default='')
    aprovada = models.BooleanField(default=False)
    data = models.DateTimeField(auto_now_add=True)
    creat_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.PROTECT,
        related_name='grading_versions_creades',
        null=True, blank=True,
    )
    notes = models.TextField(null=True, blank=True)

    # Sprint 3 — grading engine
    version_number = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Versió de grading'
        verbose_name_plural = 'Versions de grading'
        ordering = ['size_fitting', '-data']

    def __str__(self):
        return f'{self.size_fitting.codi} · {self.nom}'


class POMAlert(models.Model):
    TIPUS_CHOICES = [
        ('desviacio', 'Desviació'),
        ('fora_rang', 'Fora de rang'),
        ('manca', 'Manca'),
        ('conflicte', 'Conflicte'),
    ]
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('Acceptat', 'Acceptat'),
        ('Corregit', 'Corregit'),
    ]

    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='pom_alerts', null=True, blank=True)
    size_fitting = models.ForeignKey(
        SizeFitting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pom_alerts',
    )
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='alerts', null=True, blank=True)
    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES, blank=True, default='desviacio')
    valor_detectat = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    valor_esperat = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    z_score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='Pendent')
    creat_per = models.CharField(max_length=100, default='sistema')
    data_creacio = models.DateTimeField(auto_now_add=True)
    resolt_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pom_alerts_resoltes',
    )
    data_resolucio = models.DateTimeField(null=True, blank=True)

    # Sprint S11 — extra fields for vs-spec + check-tolerances
    desviacio_cm   = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    tolerancia_cm  = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    missatge       = models.TextField(blank=True)
    origen         = models.CharField(max_length=20, default='FITTING')
    nota_resolucio = models.TextField(blank=True)
    resolt_per_user_id = models.IntegerField(null=True, blank=True,
                       help_text='ID usuari cross-schema (Sprint S11)')

    class Meta:
        verbose_name = 'Alerta POM'
        verbose_name_plural = 'Alertes POM'

    def __str__(self):
        return f'{self.model.codi_intern} · {self.pom.codi_client} ({self.tipus})'


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 4 — Fitting wizard (to be replaced by FittingSession/PieceFitting in Sprint 5B)
# ─────────────────────────────────────────────────────────────────────────────

class SFFitting(models.Model):
    """Fitting wizard session: tracking of modifications vs GradedSpec."""
    TIPUS_CHOICES = [
        ('Proto', 'Proto'),
        ('Sample', 'Sample'),
        ('PPS', 'PPS'),
    ]
    ESTAT_CHOICES = [
        ('Obert', 'Obert'),
        ('Tancat', 'Tancat'),
        ('Anullat', 'Anul·lat'),
    ]

    size_fitting = models.ForeignKey(SizeFitting, on_delete=models.CASCADE, related_name='sf_fittings')
    fitting_num = models.PositiveIntegerField()
    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES)
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='Obert')
    responsable = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sf_fittings_responsable',
    )
    data_creacio = models.DateTimeField(auto_now_add=True)
    data_tancament = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'SF Fitting (wizard)'
        verbose_name_plural = 'SF Fittings (wizard)'
        unique_together = [('size_fitting', 'fitting_num')]
        ordering = ['size_fitting', 'fitting_num']

    def __str__(self):
        return f'{self.size_fitting.codi} · SF#{self.fitting_num} ({self.tipus})'


class SFFittingLinia(models.Model):
    """Line of an SFFitting: (POM, talla) with valor_vigent (GradedSpec) and valor_nou (entered)."""
    ESTAT_CELLA_CHOICES = [
        ('Pendent', 'Pendent'),
        ('OK', 'OK'),
        ('Modificat', 'Modificat'),
    ]

    fitting = models.ForeignKey(SFFitting, on_delete=models.CASCADE, related_name='linies')
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='sf_fitting_linies')
    nom_pom = models.CharField(max_length=200)
    talla = models.CharField(max_length=20)
    valor_vigent = models.FloatField()
    valor_nou = models.FloatField(null=True, blank=True)
    estat_cella = models.CharField(max_length=20, choices=ESTAT_CELLA_CHOICES, default='Pendent')
    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Línia SF Fitting'
        verbose_name_plural = 'Línies SF Fitting'
        ordering = ['fitting', 'pom', 'talla']

    def __str__(self):
        return f'{self.fitting} · {self.nom_pom} @ {self.talla}'


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 3 — Grading engine output (per GradingVersion)
# ─────────────────────────────────────────────────────────────────────────────

class GradedSpec(models.Model):
    """Measurement generated per (GradingVersion, POM, talla) — grading engine output."""
    GRADING_TYPE_CHOICES = [
        ('LINEAR', 'Linear'),
        ('STEP', 'Step'),
        ('FIXED', 'Fixed'),
        ('ZERO', 'Zero'),
        ('EXCEPTION', 'Exception'),
    ]
    grading_version = models.ForeignKey(
        GradingVersion, on_delete=models.CASCADE, related_name='graded_specs',
    )
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='graded_specs')
    size_label = models.CharField(max_length=20)
    graded_value_cm = models.FloatField()
    grading_type_applied = models.CharField(max_length=20, choices=GRADING_TYPE_CHOICES)
    increment_applied_cm = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)

    # Sprint 4 / F2: measurement version this spec was generated from.
    # Null for the 84 pre-existing specs (unknown origin). The brain (dependency
    # graph) will later compare generated_from_version < model.measurements_version
    # to detect stale specs — NOT implemented here, only the link is stored.
    generated_from_version = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = 'Spec generat'
        verbose_name_plural = 'Specs generats'
        unique_together = [('grading_version', 'pom', 'size_label')]
        ordering = ['grading_version', 'pom', 'size_label']

    def __str__(self):
        return f'v{self.grading_version_id} · {self.pom.codi_client} @ {self.size_label} = {self.graded_value_cm}cm'
