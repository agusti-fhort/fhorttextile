from django.db import models


class Tasca(models.Model):
    """Task catalog (tenant). Merges legacy TascaCataleg + process metadata."""
    # --- Legacy TascaCataleg ---
    tasca_global = models.ForeignKey(
        'pom.TascaGlobal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='catalegs_tenant',
    )
    nom_custom = models.CharField(max_length=200, null=True, blank=True)
    minuts_estandard = models.PositiveIntegerField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    # --- Sprint 1B: process metadata ---
    nom_tasca = models.CharField(max_length=200, null=True, blank=True)
    tipus_tasca = models.CharField(
        max_length=20,
        choices=[
            ('Interna', 'Interna'),
            ('Externa', 'Externa'),
            ('Validació', 'Validació'),
        ],
        default='Interna',
    )
    fase = models.CharField(
        max_length=20,
        choices=[
            ('Disseny', 'Disseny'),
            ('Tècnic', 'Tècnic'),
            ('Prototip', 'Prototip'),
            ('Mostres', 'Mostres'),
            ('Preproducció', 'Preproducció'),
            ('Producció', 'Producció'),
        ],
        default='Disseny',
    )
    ordre_base = models.IntegerField(default=0)
    slots_base = models.FloatField(
        default=0.0,
        help_text="Referència orientativa. Els slots reals vénen de la tipologia del model.",
    )
    facturable = models.BooleanField(
        default=True,
        help_text="Els gates i tasques de validació no son facturables.",
    )
    bloqueja_model = models.BooleanField(default=False)
    gate = models.BooleanField(default=False)
    resultat_gate = models.CharField(
        max_length=20,
        choices=[('OK', 'OK'), ('NO_OK', 'No OK'), ('EXCEPCIO', 'Excepció')],
        null=True, blank=True,
    )
    notes = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tasca (catàleg tenant)'
        verbose_name_plural = 'Tasques (catàleg tenant)'
        ordering = ['ordre_base', 'ordre']

    def __str__(self):
        if self.nom_tasca:
            return f"[{self.fase}] {self.nom_tasca}"
        if self.nom_custom:
            return self.nom_custom
        return self.tasca_global.codi if self.tasca_global_id else f'Tasca#{self.pk}'


class ModelTasca(models.Model):
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('EnCurs', 'En curs'),
        ('Feta', 'Feta'),
        ('Bloquejada', 'Bloquejada'),
    ]
    GATE_CHOICES = [
        ('OK', 'OK'),
        ('NO_OK', 'No OK'),
        ('EXCEPCIO', 'Excepció'),
    ]

    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='tasques')
    tasca = models.ForeignKey(Tasca, on_delete=models.PROTECT, related_name='instancies')
    ordre = models.PositiveIntegerField(default=0)
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='Pendent')
    responsable = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasques_assignades',
    )
    data_limit = models.DateField(null=True, blank=True)

    minuts_assignats = models.PositiveIntegerField()
    minuts_reals = models.PositiveIntegerField(default=0)

    cost_real = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    es_gate = models.BooleanField(default=False)
    resultat_gate = models.CharField(max_length=20, choices=GATE_CHOICES, null=True, blank=True)
    gate_revisat_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gates_revisades',
    )
    gate_data = models.DateTimeField(null=True, blank=True)
    gate_notes = models.TextField(null=True, blank=True)

    # --- Sprint 1A: new fields ---
    paquet_origen = models.CharField(max_length=200, null=True, blank=True)
    slots_base = models.FloatField(null=True, blank=True, default=0)
    slots_reals = models.FloatField(null=True, blank=True, default=0)
    hores_reals = models.FloatField(null=True, blank=True, default=0)
    tipus_encarrec = models.CharField(
        max_length=20,
        choices=[
            ('Proto', 'Proto'), ('Fit Sample', 'Fit Sample'),
            ('Size Set', 'Size Set'), ('PP Sample', 'PP Sample'),
            ('TOP Sample', 'TOP Sample'), ('Producció', 'Producció'),
        ],
        null=True, blank=True,
    )
    color_codi = models.CharField(max_length=20, null=True, blank=True)
    item_ref = models.CharField(max_length=100, null=True, blank=True)
    # --- End Sprint 1A ---

    class Meta:
        verbose_name = 'Tasca de model'
        verbose_name_plural = 'Tasques de model'
        ordering = ['model', 'ordre']

    def __str__(self):
        return f'{self.model.codi_intern} · {self.tasca} ({self.estat})'


class TipologiaModel(models.Model):
    """Model typology with load slots per production route.

    NOTE: the spec asked for IntegerField but the real master-data values
    contain decimals (3.5, 5.0, 6.5) — we use DecimalField to avoid losing
    precision. Likewise, patrons_aprox is a range ("10-14"), hence CharField.
    """

    codi = models.CharField(max_length=40, unique=True)
    nom = models.CharField(max_length=200, blank=True)
    familia = models.CharField(max_length=80, blank=True)
    familia_codi = models.CharField(max_length=20, blank=True)
    garment_type = models.ForeignKey(
        'pom.GarmentType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tipologies',
    )

    complexitat = models.CharField(max_length=40, null=True, blank=True)
    patrons_aprox = models.CharField(max_length=20, null=True, blank=True)

    slots_cad_client = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    slots_digitalitzacio = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    slots_des_de_zero = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    slots_conf_proto = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    slots_conf_proto_sample = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    slots_conf_proto_sample_size = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    actiu = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Tipologia de model'
        verbose_name_plural = 'Tipologies de model'
        ordering = ['familia_codi', 'codi']

    def __str__(self):
        return f'{self.codi} · {self.nom}'


class TimerEntrada(models.Model):
    model_tasca = models.ForeignKey(ModelTasca, on_delete=models.CASCADE, related_name='timers')
    tecnic = models.ForeignKey('accounts.UserProfile', on_delete=models.PROTECT, related_name='timers')
    inici = models.DateTimeField()
    fi = models.DateTimeField(null=True, blank=True)
    minuts = models.PositiveIntegerField(null=True, blank=True)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Entrada de timer'
        verbose_name_plural = 'Entrades de timer'
        ordering = ['-inici']

    def __str__(self):
        return f'{self.tecnic} · {self.model_tasca} · {self.inici:%Y-%m-%d %H:%M}'



class PaquetServei(models.Model):
    """Offered service package. Groups tasks that are applied together."""
    nom = models.CharField(max_length=200, unique=True)
    actiu = models.BooleanField(default=True)
    grup = models.CharField(
        max_length=50,
        choices=[
            ('Patronatge', 'Patronatge'),
            ('Tech Pack', 'Tech Pack'),
            ('Mostres', 'Mostres'),
            ('Producció', 'Producció'),
        ],
        null=True, blank=True,
    )
    multiplicador = models.FloatField(null=True, blank=True)
    slots_base = models.FloatField(null=True, blank=True)
    ordre_popup = models.IntegerField(null=True, blank=True)
    descripcio = models.TextField(null=True, blank=True)
    notes_comercials = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['ordre_popup', 'nom']
        verbose_name = 'Paquet de servei'
        verbose_name_plural = 'Paquets de servei'

    def __str__(self):
        return self.nom


class PaquetServeiTasca(models.Model):
    """Link between PaquetServei and Tasca. Defines the order and whether it is optional."""
    paquet = models.ForeignKey(
        PaquetServei, on_delete=models.CASCADE, related_name='tasques',
    )
    tasca = models.ForeignKey(
        Tasca, on_delete=models.CASCADE, related_name='paquets',
    )
    ordre = models.IntegerField()
    opcional = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['ordre']
        unique_together = [['paquet', 'tasca']]
        verbose_name = 'Tasca de paquet'
        verbose_name_plural = 'Tasques de paquet'

    def __str__(self):
        return f"{self.paquet.nom} — {self.tasca.nom_tasca} (#{self.ordre})"
