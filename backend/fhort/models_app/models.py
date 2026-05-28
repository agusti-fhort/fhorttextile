from django.db import models
from django.conf import settings


# Stubs mínims: l'enunciat exigeix les FKs Model.contracte/linia_contracte
# però no defineix aquests models. Ampliar quan es construeixi l'app de contractes.
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
        ('Proto', 'Proto'),
        ('Fit', 'Fit'),
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
    fit_type = models.CharField(max_length=20, choices=FIT_CHOICES, default='Regular')
    size_system = models.ForeignKey(
        'pom.SizeSystem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models',
    )
    talla_base = models.ForeignKey(
        'pom.SizeDefinition',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models_base',
    )
    grading_rule_set = models.ForeignKey(
        'pom.GradingRuleSet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models',
    )

    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default=ESTAT_NOU)
    fase_actual = models.CharField(max_length=20, choices=FASE_CHOICES, default='Proto')

    responsable = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='models_responsable',
    )
    prioritat = models.PositiveSmallIntegerField(default=3)
    data_entrada = models.DateField(auto_now_add=True)
    data_objectiu = models.DateField(null=True, blank=True)
    data_tancament = models.DateField(null=True, blank=True)

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

    # --- Sprint 1A: camps nous (fase_actual ja existeix amb FASE_CHOICES) ---
    familia = models.CharField(max_length=100, null=True, blank=True)
    slots_prev_tecnics = models.FloatField(null=True, blank=True, default=0)
    slots_prev_confeccio = models.FloatField(null=True, blank=True, default=0)
    slots_reals_tecnic = models.FloatField(null=True, blank=True, default=0)
    slots_reals_confeccio = models.FloatField(null=True, blank=True, default=0)
    # --- Fi Sprint 1A ---

    # --- Sprint 3/4: configuració de talles per al grading ---
    size_run_model = models.CharField(
        max_length=200, null=True, blank=True,
        help_text="Talles del model separades per · o ; (p.ex. 'XS·S·M·L·XL')",
    )
    base_size_label = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="Etiqueta de la talla base (ha de coincidir amb un valor de size_run_model)",
    )

    # Última activitat (s'actualitza a cada save via signal post_save)
    darrera_activitat = models.DateTimeField(null=True, blank=True)

    
    # --- Sprint 7A: Design Freeze ---
    design_freeze_at = models.DateTimeField(null=True, blank=True)
    design_freeze_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='design_freezes',
    )
    # --- Fi Sprint 7A ---
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
    """Serveis assignats a un Model. Child table del tab Servei."""
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
# Sprint 3 — Motor de grading
# ─────────────────────────────────────────────────────────────────────────────

class BaseMeasurement(models.Model):
    """Mesures de la talla base introduïdes per al Model abans de generar talles."""

    ORIGEN_CHOICES = [
        ('STANDARD',   'Estàndard (carregat del RuleSet)'),
        ('IMPORTED',   'Importat de fitxa externa'),
        ('MANUAL',     'Introduït manualment'),
        ('FITTED',     'Modificat en fitting'),
        ('CALCULATED', 'Calculat des de talla base + delta'),
    ]

    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name='base_measurements')
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='base_measurements')
    base_value_cm = models.FloatField()
    is_active = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Sprint S14-A
    nom_fitxa = models.CharField(
        max_length=20, blank=True, default='',
        help_text='Nomenclatura de la fletxa al croquis (ex: A, 1, CH). '
                  'Per defecte: abbreviation del POMGlobal.'
    )
    origen = models.CharField(
        max_length=20, choices=ORIGEN_CHOICES, default='STANDARD',
    )

    class Meta:
        verbose_name = 'Mesura base'
        verbose_name_plural = 'Mesures base'
        unique_together = [('model', 'pom')]
        ordering = ['model', 'pom']

    def __str__(self):
        return f'{self.model} · {self.pom.codi_client} = {self.base_value_cm}cm'
