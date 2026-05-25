from django.db import models


class TascaCataleg(models.Model):
    tasca_global = models.ForeignKey(
        'pom.TascaGlobal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='catalegs_tenant',
    )
    nom_custom = models.CharField(max_length=200, null=True, blank=True)
    minuts_estandard = models.PositiveIntegerField()
    activa = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Catàleg de tasca (tenant)'
        verbose_name_plural = 'Catàlegs de tasca (tenant)'
        ordering = ['ordre']

    def __str__(self):
        if self.nom_custom:
            return self.nom_custom
        return self.tasca_global.codi if self.tasca_global_id else f'TascaCataleg#{self.pk}'


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
    tasca = models.ForeignKey(TascaCataleg, on_delete=models.PROTECT, related_name='instancies')
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

    # --- Sprint 1A: camps nous ---
    paquet_origen = models.CharField(max_length=200, null=True, blank=True)
    slots_base = models.FloatField(null=True, blank=True, default=0)
    slots_reals = models.FloatField(null=True, blank=True, default=0)
    hores_reals = models.FloatField(null=True, blank=True, default=0)
    cost_real = models.FloatField(null=True, blank=True, default=0)
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
    # --- Fi Sprint 1A ---

    class Meta:
        verbose_name = 'Tasca de model'
        verbose_name_plural = 'Tasques de model'
        ordering = ['model', 'ordre']

    def __str__(self):
        return f'{self.model.codi_intern} · {self.tasca} ({self.estat})'


class TipologiaModel(models.Model):
    """Tipologia de model amb slots de càrrega per via de producció.

    NOTA: l'spec demanava IntegerField però els valors reals del master data
    contenen decimals (3.5, 5.0, 6.5) — usem DecimalField per no perdre precisió.
    Igualment, patrons_aprox és un range ("10-14"), per això CharField.
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
