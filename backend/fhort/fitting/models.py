from django.db import models
from django.conf import settings

from fhort.models_app.models import Model


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

    # Sprint 5B.4 — production seal (set by advance_phase when a gate is passed).
    # `aprovada` = sealed as production; who/when for the manual decision.
    aprovada_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        related_name='grading_versions_aprovades',
        null=True, blank=True,
    )
    data_aprovacio = models.DateTimeField(null=True, blank=True)

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
# Sprint 4 — Fitting wizard (SFFitting/SFFittingLinia): removed in Sprint 5B.5,
# replaced by FittingSession / PieceFitting / PieceFittingLine (below).
# ─────────────────────────────────────────────────────────────────────────────


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


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 5B.2 — Fitting cycle layer (structure only; services come in 5B.3)
# ─────────────────────────────────────────────────────────────────────────────

class FittingSession(models.Model):
    """The event: the fit model tries on the product (a set or a single piece).

    N=1 (single piece) is the common case, modelled as a session with one
    PieceFitting. The target is EITHER a GarmentSet (multi-piece) OR a Model
    (single piece), never both and never neither (XOR, enforced by CheckConstraint).
    """
    ESTAT_CHOICES = [
        ('Oberta', 'Oberta'),
        ('Tancada', 'Tancada'),
        ('Anullada', 'Anul·lada'),
    ]

    garment_set = models.ForeignKey(
        'models_app.GarmentSet',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='fitting_sessions',
    )
    model = models.ForeignKey(
        'models_app.Model',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='fitting_sessions',
    )
    # Phase lives on the Model/set (Proto/Fit/SizeSet/PP/TOP); reuse its choices.
    fase = models.CharField(max_length=20, choices=Model.FASE_CHOICES)
    data = models.DateField()
    model_persona = models.CharField(max_length=200, blank=True, default='')
    assistents = models.CharField(max_length=300, blank=True, default='')
    lloc = models.CharField(max_length=200, blank=True, default='')
    responsable = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fitting_sessions_responsable',
    )
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='Oberta')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fitting_sessions_creades',
    )

    class Meta:
        verbose_name = 'Sessió de fitting'
        verbose_name_plural = 'Sessions de fitting'
        ordering = ['-data', '-created_at']
        constraints = [
            models.CheckConstraint(
                name='fittingsession_set_xor_model',
                condition=(
                    models.Q(garment_set__isnull=False, model__isnull=True) |
                    models.Q(garment_set__isnull=True, model__isnull=False)
                ),
            ),
        ]

    def __str__(self):
        target = self.garment_set_id and self.garment_set or self.model
        return f'FittingSession {self.data} · {target} ({self.fase})'


class PieceFitting(models.Model):
    """One per piece evaluated in the session. Owns an independent gate."""
    GATE_CHOICES = [
        ('Pendent', 'Pendent'),
        ('OK', 'OK'),
        ('NO_OK', 'No OK'),
        ('EXCEPCIO', 'Excepció'),
    ]

    session = models.ForeignKey(
        FittingSession, on_delete=models.CASCADE, related_name='piece_fittings',
    )
    model = models.ForeignKey(
        'models_app.Model', on_delete=models.PROTECT, related_name='piece_fittings',
    )
    grading_version = models.ForeignKey(
        GradingVersion, on_delete=models.PROTECT, related_name='piece_fittings',
    )
    gate = models.CharField(max_length=10, choices=GATE_CHOICES, default='Pendent')
    gate_motiu = models.TextField(blank=True, default='')
    # Sprint 5B.4 — who/when set the gate (manual-decision traceability).
    gate_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        related_name='piece_fittings_gated',
        null=True, blank=True,
    )
    gate_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='piece_fittings_creats',
    )

    class Meta:
        verbose_name = 'Fitting de peça'
        verbose_name_plural = 'Fittings de peça'
        ordering = ['session', 'model']
        unique_together = [('session', 'model')]

    def __str__(self):
        return f'{self.session_id} · {self.model} [{self.gate}]'


class PieceFittingLine(models.Model):
    """A (POM, size) row: theoretical (grading) vs real (measured) — SEPARATE.

    Only the two current values are stored. The evolution across versions is read
    dynamically from the GradingVersion history, NOT materialised here.
    """
    piece_fitting = models.ForeignKey(
        PieceFitting, on_delete=models.CASCADE, related_name='linies',
    )
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='+')
    size_label = models.CharField(max_length=20)
    valor_teoric = models.FloatField()
    valor_real = models.FloatField(null=True, blank=True)
    nota = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        verbose_name = 'Línia de fitting de peça'
        verbose_name_plural = 'Línies de fitting de peça'
        ordering = ['piece_fitting', 'pom', 'size_label']
        unique_together = [('piece_fitting', 'pom', 'size_label')]

    def __str__(self):
        return f'{self.piece_fitting_id} · {self.pom.codi_client} @ {self.size_label}'


class FittingPhoto(models.Model):
    """Autonomous photo (FileField pattern like ModelFitxer, not FitxerVersio).

    Belongs to a session; optionally pinned to a specific PieceFitting.
    """
    session = models.ForeignKey(
        FittingSession, on_delete=models.CASCADE, related_name='photos',
    )
    piece_fitting = models.ForeignKey(
        PieceFitting, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='photos',
    )
    fitxer = models.ImageField(upload_to='fitting_photos/%Y/%m/')
    caption = models.CharField(max_length=300, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foto de fitting'
        verbose_name_plural = 'Fotos de fitting'
        ordering = ['session', 'id']

    def __str__(self):
        return f'{self.session_id} · {self.caption or self.fitxer.name}'
