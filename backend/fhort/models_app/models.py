from django.db import models
from django.conf import settings


# Minimal stubs: the spec requires the Model.contracte/linia_contracte FKs
# but does not define these models. Extend when the contracts app is built.
class Contracte(models.Model):
    nom = models.CharField(max_length=200)
    referencia = models.CharField(max_length=80, blank=True)
    data_inici = models.DateField(null=True, blank=True)
    data_fi = models.DateField(null=True, blank=True)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Contracte'
        verbose_name_plural = 'Contractes'

    def __str__(self):
        return self.nom


class LiniaContracte(models.Model):
    contracte = models.ForeignKey(Contracte, on_delete=models.CASCADE, related_name='linies')
    descripcio = models.CharField(max_length=200)
    quantitat = models.PositiveIntegerField(default=0)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Línia de contracte'
        verbose_name_plural = 'Línies de contracte'

    def __str__(self):
        return f'{self.contracte.nom} · {self.descripcio}'


class GarmentSet(models.Model):
    """
    Commercial multi-piece product (twin set, dress + belt, top + bottom of the
    same fabric) that is sold and fitted as a single unit but is technically made
    of N independent pieces.

    Distinction vs GarmentGroup (pom.GarmentGroup):
      - GarmentGroup is a TAXONOMY/category (SWIMWEAR, OUTERWEAR, BOTTOMS...).
        Many unrelated Models share a group. It classifies.
      - GarmentSet is a CONCRETE product instance. Its pieces are specific Models
        bound to it. It groups the physical pieces of one product.

    Membership is explicit (Model.garment_set FK + Model.piece_number), never
    parsed from a code string. The base code lives here; each piece Model carries
    the full stored code (codi_base + '-NN') in its own codi_intern.
    """
    codi_base = models.CharField(max_length=40, unique=True)
    nom_comercial = models.CharField(max_length=200, blank=True, default='')
    num_pieces = models.PositiveSmallIntegerField(
        help_text='Nombre de peces del conjunt. Immutable després de la creació.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Garment Set (conjunt)'
        verbose_name_plural = 'Garment Sets (conjunts)'
        ordering = ['codi_base']

    def __str__(self):
        return f'{self.codi_base} ({self.num_pieces} peces)'


class Model(models.Model):
    TEMPORADA_CHOICES = [
        ('SS', 'Spring/Summer'),
        ('FW', 'Fall/Winter'),
        ('CO', 'Cruise'),
        ('SP', 'Special'),
    ]

    ESTAT_NOU = 'Nou'
    ESTAT_EN_CURS = 'EnCurs'
    ESTAT_EN_REVISIO = 'EnRevisio'
    ESTAT_TANCAT = 'Tancat'
    ESTAT_CHOICES = [
        (ESTAT_NOU, 'Nou'),
        (ESTAT_EN_CURS, 'En curs'),
        (ESTAT_EN_REVISIO, 'En revisió'),
        (ESTAT_TANCAT, 'Tancat'),
    ]

    FASE_CHOICES = [
        ('Pending', 'Pending'),
        ('Dev', 'Dev'),
        ('Proto', 'Proto'),
        ('SizeSet', 'SizeSet'),
        ('PP', 'PP'),
        ('TOP', 'TOP'),
    ]

    FIT_CHOICES = [
        ('Regular', 'Regular'),
        ('Slim', 'Slim'),
        ('Relaxed', 'Relaxed'),
        ('Oversize', 'Oversize'),
        ('Tailored', 'Tailored'),
    ]

    ORIGEN_PATRO_CHOICES = [
        ('CAD Client', 'CAD Client'),
        ('Digitalització', 'Digitalització'),
        ('Des de zero', 'Des de zero'),
    ]

    codi_intern = models.CharField(max_length=40, unique=True)
    codi_client = models.CharField(max_length=80, blank=True, default='')

    codi_tenant = models.CharField(max_length=3)
    any = models.PositiveSmallIntegerField()
    temporada = models.CharField(max_length=4, choices=TEMPORADA_CHOICES)
    sequencial = models.PositiveIntegerField()

    nom_prenda = models.CharField(max_length=200, blank=True, null=True)
    descripcio = models.TextField(null=True, blank=True)
    color_referencia = models.CharField(max_length=100, null=True, blank=True)
    # Pas 5A — col·lecció/línia comercial (text lliure, capa identificació)
    collection = models.CharField(max_length=120, blank=True, default='')

    garment_type = models.ForeignKey(
        'pom.GarmentType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models',
    )
    garment_group = models.ForeignKey(
        'pom.GarmentGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models',
    )
    # --- Sprint G: garment type variant (complexity node) for time estimation ---
    garment_type_item = models.ForeignKey(
        'tasks.GarmentTypeItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models',
    )

    # --- Sprint A: multi-piece (GarmentSet) ---
    # Membership in a commercial set is explicit (FK + piece_number), not parsed
    # from codi_intern. For a single-piece model (~90%) both are null and the
    # creation flow is unchanged.
    garment_set = models.ForeignKey(
        'models_app.GarmentSet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='peces',
    )
    piece_number = models.PositiveSmallIntegerField(null=True, blank=True)
    # --- End Sprint A ---

    fit_type = models.CharField(max_length=20, choices=FIT_CHOICES, default='Regular')
    target = models.CharField(max_length=30, null=True, blank=True)
    construction = models.CharField(max_length=20, null=True, blank=True)
    size_system = models.ForeignKey(
        'pom.SizeSystem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models',
    )
    grading_rule_set = models.ForeignKey(
        'pom.GradingRuleSet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models',
    )

    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default=ESTAT_NOU)
    fase_actual = models.CharField(max_length=20, choices=FASE_CHOICES, default='Pending')

    responsable = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models_responsable',
    )
    prioritat = models.PositiveSmallIntegerField(default=3)
    data_entrada = models.DateField(auto_now_add=True)
    # Pas 5A — traçabilitat de creació (creador + timestamp). responsable = assignat, no creador.
    created_by = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    data_objectiu = models.DateField(null=True, blank=True)
    data_tancament = models.DateField(null=True, blank=True)
    predicted_start = models.DateField(null=True, blank=True)
    predicted_end = models.DateField(null=True, blank=True)

    contracte = models.ForeignKey(
        Contracte,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models',
    )
    linia_contracte = models.ForeignKey(
        LiniaContracte,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models',
    )

    observacions = models.TextField(null=True, blank=True)

    origen_patro = models.CharField(
        max_length=50,
        choices=ORIGEN_PATRO_CHOICES,
        null=True,
        blank=True,
    )
    versio = models.CharField(max_length=20, null=True, blank=True)

    # --- Sprint 1A: new fields (fase_actual already exists with FASE_CHOICES) ---
    slots_prev_tecnics = models.FloatField(null=True, blank=True, default=0)
    slots_prev_confeccio = models.FloatField(null=True, blank=True, default=0)
    slots_reals_tecnic = models.FloatField(null=True, blank=True, default=0)
    slots_reals_confeccio = models.FloatField(null=True, blank=True, default=0)
    # --- End Sprint 1A ---

    # --- Sprint 3/4: size configuration for grading ---
    size_run_model = models.CharField(
        max_length=200, null=True, blank=True,
        help_text="Talles del model separades per · o ; (p.ex. 'XS·S·M·L·XL')",
    )
    base_size_label = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="Etiqueta de la talla base (ha de coincidir amb un valor de size_run_model)",
    )

    # Last activity (updated on every save via post_save signal)
    darrera_activitat = models.DateTimeField(null=True, blank=True)

    # --- Sprint 3 / F1: root versioning ---
    # Counter for the measurement table (the root). Incremented when grading is
    # regenerated (the increment itself is wired in a later sprint; here only the field).
    measurements_version = models.IntegerField(default=1)

    
    # --- Sprint 7A: Design Freeze ---
    design_freeze_at = models.DateTimeField(null=True, blank=True)
    design_freeze_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='design_freezes',
    )
    # --- End Sprint 7A ---

    # Fabric and shrinkage
    SHRINKAGE_TYPE_CHOICES = [
        ('NONE',     'No definit'),
        ('ISO',      'Estàndard ISO'),
        ('SUPPLIER', 'Fabricant'),
        ('CUSTOM',   'Personalitzat'),
    ]
    fabric_main        = models.CharField(max_length=200, blank=True, default='')
    fabric_composition = models.CharField(max_length=200, blank=True, default='')
    shrinkage_type     = models.CharField(max_length=10, choices=SHRINKAGE_TYPE_CHOICES,
                                           default='NONE')
    shrinkage_warp     = models.FloatField(null=True, blank=True,
                                            help_text='Encongiment ordit/warp (%)')
    shrinkage_weft     = models.FloatField(null=True, blank=True,
                                            help_text='Encongiment trama/weft (%)')
    shrinkage_pct      = models.FloatField(null=True, blank=True,
                                            help_text='Encongiment únic (%) si no és biaxial')
    # Clau del teixit ISO triat (id de la taula ISO_SHRINKAGE_TABLE). Conserva QUIN teixit es va
    # seleccionar (no només els %), necessari per al shrinkage-com-a-càlcul futur i per desambiguar
    # teixits amb warp/weft idèntics (Woven Cotton vs Linen).
    shrinkage_iso_key  = models.CharField(max_length=40, blank=True, default='',
                                           help_text='Teixit ISO triat (id de la taula ISO)')
    fabric_notes       = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Model'
        verbose_name_plural = 'Models'
        indexes = [
            models.Index(fields=['codi_tenant', 'any', 'temporada']),
            models.Index(fields=['estat', 'fase_actual']),
        ]

    def __str__(self):
        return f'{self.codi_intern} · {self.nom_prenda}'


class ModelFitxer(models.Model):
    CATEGORIA_CHOICES = [
        ('Patro', 'Patró'),
        ('Disseny', 'Disseny'),
        ('Fitting', 'Fitting'),
        ('Document', 'Document'),
    ]

    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name='fitxers')
    nom_fitxer = models.CharField(max_length=255)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    tipus = models.CharField(max_length=30, default='ALTRES', blank=True)
    versio = models.CharField(max_length=10)
    path_servidor = models.CharField(max_length=500)
    versio_anterior = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions_posteriors',
    )
    accessible_portal = models.BooleanField(default=False)
    pujat_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='fitxers_pujats',
    )
    data_pujada = models.DateTimeField(auto_now_add=True)
    mida_bytes = models.BigIntegerField()

    # Sprint 1B
    fitxer = models.FileField(upload_to='model_fitxers/%Y/%m/', null=True, blank=True)
    url_extern = models.URLField(
        null=True, blank=True,
        help_text="URL externa si el fitxer no s'emmagatzema aquí",
    )
    descripcio = models.TextField(null=True, blank=True)

    def get_url(self):
        if self.url_extern:
            return self.url_extern
        if self.fitxer:
            return self.fitxer.url
        return None

    enviat_ia = models.BooleanField(default=False)
    resultat_ia_path = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        verbose_name = 'Fitxer de model'
        verbose_name_plural = 'Fitxers de model'

    def __str__(self):
        return f'{self.model.codi_intern} · {self.nom_fitxer} ({self.versio})'



class ModelServei(models.Model):
    """Services assigned to a Model. Child table of the Servei tab."""
    model = models.ForeignKey(
        'Model', on_delete=models.CASCADE, related_name='serveis_model',
    )
    servei = models.ForeignKey(
        'tasks.PaquetServei', on_delete=models.PROTECT, related_name='models_servei',
    )
    nom_servei = models.CharField(max_length=200, null=True, blank=True)
    grup = models.CharField(max_length=50, null=True, blank=True)
    slots_base = models.FloatField(null=True, blank=True)
    contractat = models.BooleanField(default=True)
    ampliat = models.BooleanField(default=False)
    estat_autoritzacio = models.CharField(
        max_length=20,
        choices=[
            ('Pendent', 'Pendent'),
            ('Autoritzat', 'Autoritzat'),
            ('Rebutjat', 'Rebutjat'),
        ],
        null=True, blank=True,
    )
    autoritzat_per = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='autorizacions_servei',
    )
    data_autoritzacio = models.DateTimeField(null=True, blank=True)
    linia_addicional = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        ordering = ['servei__ordre_popup', 'id']
        verbose_name = 'Servei del model'
        verbose_name_plural = 'Serveis del model'

    def save(self, *args, **kwargs):
        if self.servei_id:
            if not self.nom_servei:
                self.nom_servei = self.servei.nom
            if not self.grup:
                self.grup = self.servei.grup
            if self.slots_base is None:
                self.slots_base = self.servei.slots_base
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.model.codi} — {self.nom_servei or self.servei.nom}"


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 3 — Grading engine
# ─────────────────────────────────────────────────────────────────────────────

class BaseMeasurement(models.Model):
    """Base-size measurements entered for the Model before generating sizes."""

    ORIGEN_CHOICES = [
        ('STANDARD',   'Estàndard (carregat del RuleSet)'),
        ('IMPORTED',   'Importat de fitxa externa'),
        ('MANUAL',     'Introduït manualment'),
        ('FITTED',     'Modificat en fitting'),
        ('CALCULATED', 'Calculat des de talla base + delta'),
        ('TEMPLATE',   'Materialitzat de plantilla (sense valor encara)'),
    ]

    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name='base_measurements')
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='base_measurements')
    # NULL = POM materialitzat de la plantilla de l'item sense valor encara (origen='TEMPLATE').
    # El signal del log i el motor de grading IGNOREN les files amb base_value_cm=None.
    base_value_cm = models.FloatField(null=True, blank=True)
    # Còpia de la plantilla GarmentPOMMap de l'item (snapshot per-model).
    is_key = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Sprint 3 / F1: root versioning ---
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='base_measurements_created',
    )

    # --- Sprint 5B.1: tolerance copied from the catalogue POM at pour time ---
    # NULL for the pre-existing measurements; consumers fall back to 0.6 (wired in 5B.4).
    tolerancia_minus = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tolerancia_plus = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Sprint S14-A
    nom_fitxa = models.CharField(
        max_length=20, blank=True, default='',
        help_text='Nomenclatura de la fletxa al croquis (ex: A, 1, CH). '
                  'Per defecte: abbreviation del POMGlobal.'
    )
    origen = models.CharField(
        max_length=20, choices=ORIGEN_CHOICES, default='STANDARD',
    )
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Mesura base'
        verbose_name_plural = 'Mesures base'
        unique_together = [('model', 'pom')]
        ordering = ['model', 'ordre', 'pom']

    def __str__(self):
        return f'{self.model} · {self.pom.codi_client} = {self.base_value_cm}cm'


class MeasurementChangeLog(models.Model):
    """
    Sprint 3 / F1 — Append-only log of base-measurement value changes.

    BaseMeasurement holds the *current* value (the root state); this log records
    *every* value change so the differential process table, the re-opening
    propagation (fora_de_tolerancia) and the z-score evolution can be built later.

    Append-only at application level: rows can only be inserted, never updated or
    deleted (see save()/delete() overrides).
    """
    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name='measurement_changes')
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='measurement_changes')
    base_measurement = models.ForeignKey(
        BaseMeasurement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='change_log',
    )
    valor_anterior = models.FloatField(null=True, blank=True)  # null when it is a creation
    valor_nou = models.FloatField()
    motiu = models.CharField(max_length=255, blank=True, default='')
    context = models.CharField(max_length=50)  # 'import' / 'manual' / 'fitting' / ...
    # Set when the change originates from a fitting (stays null until Sprint 5).
    fitting_ref = models.ForeignKey(
        'fitting.SizeFitting', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='measurement_changes',
    )
    fora_de_tolerancia = models.BooleanField(default=False)  # drives re-opening propagation (later)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='measurement_changes',
    )

    class Meta:
        verbose_name = 'Canvi de mesura'
        verbose_name_plural = 'Canvis de mesura'
        ordering = ['model', 'pom', 'created_at']

    def __str__(self):
        return f'{self.model} · {self.pom.codi_client}: {self.valor_anterior}→{self.valor_nou}cm'

    def save(self, *args, **kwargs):
        # Append-only: allow INSERT only, never UPDATE.
        if self.pk is not None:
            raise ValueError('MeasurementChangeLog is append-only: updates are not allowed.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('MeasurementChangeLog is append-only: deletes are not allowed.')


class ModelGradingOverride(models.Model):
    """Sprint 5B.3 — Per-model, per-size grading override from a validated fitting.

    When a fitting validates a real value at a NON-base size, it is stored here,
    scoped to ONE model — UNLIKE pom.GradingException, which lives on the shared
    GradingRuleSet (a template) and would leak to every model using that set.

    The grading engine (generate_graded_specs) reads these with PRIORITY over the
    rule_set exceptions and the rules. The base-size case does NOT come here: it
    promotes to BaseMeasurement (the root) instead.
    """
    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name='grading_overrides')
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='model_grading_overrides')
    size_label = models.CharField(max_length=20)
    value_cm = models.FloatField()
    motiu = models.TextField(blank=True, default='')
    fitting_ref = models.ForeignKey(
        'fitting.PieceFitting', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='grading_overrides',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='grading_overrides_created',
    )

    class Meta:
        verbose_name = 'Override de grading (model)'
        verbose_name_plural = 'Overrides de grading (model)'
        unique_together = [('model', 'pom', 'size_label')]
        ordering = ['model', 'pom', 'size_label']

    def __str__(self):
        return f'{self.model} · {self.pom.codi_client} @ {self.size_label} = {self.value_cm}cm'
