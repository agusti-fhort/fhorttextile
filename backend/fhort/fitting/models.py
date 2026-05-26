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

    # --- Sprint 1A: camps nous ---
    base_tancada = models.BooleanField(default=False)
    data_tancament_base = models.DateTimeField(null=True, blank=True)
    # --- Fi Sprint 1A ---

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

    # Sprint 3 — motor de grading
    version_number = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Versió de grading'
        verbose_name_plural = 'Versions de grading'
        ordering = ['size_fitting', '-data']

    def __str__(self):
        return f'{self.size_fitting.codi} · {self.nom}'


class GradedSpecLine(models.Model):
    ESTAT_CHOICES = [('ok', 'OK'), ('avis', 'Avís'), ('error', 'Error')]

    grading_version = models.ForeignKey(GradingVersion, on_delete=models.CASCADE, related_name='linies')
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='+')
    talla = models.ForeignKey('pom.SizeDefinition', on_delete=models.PROTECT, related_name='+')

    valor_target = models.DecimalField(max_digits=10, decimal_places=4)
    valor_pare = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    delta = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    motiu_delta = models.CharField(max_length=200, null=True, blank=True)

    estat = models.CharField(max_length=10, choices=ESTAT_CHOICES, default='ok')
    avis_text = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        verbose_name = 'Línia spec gradada'
        verbose_name_plural = 'Línies spec gradades'
        unique_together = [('grading_version', 'pom', 'talla')]

    def __str__(self):
        return f'{self.grading_version} · {self.pom.codi_client} · {self.talla.etiqueta}'


class Fitting(models.Model):
    TIPUS_CHOICES = [
        ('Proto', 'Proto'),
        ('Sample', 'Sample'),
        ('PPS', 'PPS'),
    ]
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('Aprovat', 'Aprovat'),
        ('AmbCorreccions', 'Amb correccions'),
        ('Rebutjat', 'Rebutjat'),
    ]

    size_fitting = models.ForeignKey(SizeFitting, on_delete=models.CASCADE, related_name='fittings')
    numero = models.PositiveIntegerField()
    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES)
    data_fitting = models.DateField()
    lloc = models.CharField(max_length=200, null=True, blank=True)
    responsable = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.PROTECT,
        related_name='fittings_responsable',
    )
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='Pendent')
    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Fitting'
        verbose_name_plural = 'Fittings'
        ordering = ['size_fitting', 'numero']
        unique_together = [('size_fitting', 'numero')]

    def __str__(self):
        return f'{self.size_fitting.codi} · #{self.numero} ({self.tipus})'


class FittingLine(models.Model):
    ESTAT_CHOICES = [('ok', 'OK'), ('avis', 'Avís'), ('error', 'Error')]

    fitting = models.ForeignKey(Fitting, on_delete=models.CASCADE, related_name='linies')
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='+')
    talla = models.ForeignKey('pom.SizeDefinition', on_delete=models.PROTECT, related_name='+')

    valor_target = models.DecimalField(max_digits=10, decimal_places=4)
    valor_mesurat = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    delta_real = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    estat = models.CharField(max_length=10, choices=ESTAT_CHOICES, default='ok')
    nota = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        verbose_name = 'Línia de fitting'
        verbose_name_plural = 'Línies de fitting'
        unique_together = [('fitting', 'pom', 'talla')]

    def __str__(self):
        return f'{self.fitting} · {self.pom.codi_client} · {self.talla.etiqueta}'


class FitComment(models.Model):
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('Aplicat', 'Aplicat'),
        ('Rebutjat', 'Rebutjat'),
    ]

    fitting = models.ForeignKey(Fitting, on_delete=models.CASCADE, related_name='comentaris')
    tipus = models.CharField(max_length=40)
    descripcio = models.TextField()
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='Pendent')
    resolt_en = models.ForeignKey(
        GradingVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comentaris_resolts',
    )

    class Meta:
        verbose_name = 'Comentari de fitting'
        verbose_name_plural = 'Comentaris de fitting'

    def __str__(self):
        return f'{self.fitting} · {self.tipus}'


class FitCommentFitxer(models.Model):
    fit_comment = models.ForeignKey(FitComment, on_delete=models.CASCADE, related_name='fitxers')
    path_servidor = models.CharField(max_length=500)
    nom_fitxer = models.CharField(max_length=255)
    data_pujada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fitxer de comentari'
        verbose_name_plural = 'Fitxers de comentari'

    def __str__(self):
        return self.nom_fitxer


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

    # Sprint S11 — camps addicionals per a vs-spec + check-tolerances
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



class SessioFitting(models.Model):
    """
    Sessió de fitting cross-model. Un dia amb un client on es revisen
    múltiples models en la mateixa sessió presencial.
    """
    client = models.ForeignKey(
        'tenants.Client',
        on_delete=models.PROTECT,
        related_name='sessions_fitting',
        null=True, blank=True,
    )
    data_sessio = models.DateField()
    hora_inici = models.TimeField(null=True, blank=True)
    hora_fi = models.TimeField(null=True, blank=True)
    durada_hores = models.FloatField(null=True, blank=True)
    lloc = models.CharField(max_length=200, null=True, blank=True)
    tipus = models.CharField(
        max_length=20,
        choices=[
            ('Proto', 'Proto'),
            ('Fit Sample', 'Fit Sample'),
            ('Size Set', 'Size Set'),
            ('PP Sample', 'PP Sample'),
            ('Mixt', 'Mixt'),
        ],
    )
    temporada = models.CharField(max_length=10, null=True, blank=True)
    any = models.IntegerField(null=True, blank=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='sessions_responsable',
    )
    estat = models.CharField(
        max_length=20,
        choices=[
            ('Planificada', 'Planificada'),
            ('Confirmada', 'Confirmada'),
            ('Realitzada', 'Realitzada'),
            ('Anul·lada', 'Anul·lada'),
        ],
        default='Planificada',
    )
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_sessio']
        verbose_name = 'Sessió de fitting'
        verbose_name_plural = 'Sessions de fitting'

    def __str__(self):
        client_str = str(self.client) if self.client else 'sense client'
        return f"SF-{client_str}-{self.any}-{self.temporada}"


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 4 — Fitting wizard (paral·lel a Fitting/FittingLine simples)
# ─────────────────────────────────────────────────────────────────────────────

class SFFitting(models.Model):
    """Sessió de wizard de fitting: tracking de modificacions vs GradedSpec."""
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
    """Línia d'un SFFitting: (POM, talla) amb valor_vigent (GradedSpec) i valor_nou (introduït)."""
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
# Sprint 3 — Output del motor de grading (per GradingVersion)
# ─────────────────────────────────────────────────────────────────────────────

class GradedSpec(models.Model):
    """Mesura generada per (GradingVersion, POM, talla) — output del motor de grading."""
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

    class Meta:
        verbose_name = 'Spec generat'
        verbose_name_plural = 'Specs generats'
        unique_together = [('grading_version', 'pom', 'size_label')]
        ordering = ['grading_version', 'pom', 'size_label']

    def __str__(self):
        return f'v{self.grading_version_id} · {self.pom.codi_client} @ {self.size_label} = {self.graded_value_cm}cm'
