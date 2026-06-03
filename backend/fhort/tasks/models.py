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
    model_task = models.ForeignKey('ModelTask', on_delete=models.CASCADE, related_name='timers')
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
        return f'{self.tecnic} · {self.model_task} · {self.inici:%Y-%m-%d %H:%M}'



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


class TaskType(models.Model):
    """Catàleg de tipus de tasca (per-tenant, editable). Pla i simple."""
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    default_order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['default_order', 'code']
        verbose_name = 'Task type'
        verbose_name_plural = 'Task types'

    def __str__(self):
        return self.code


class ModelTask(models.Model):
    """Instància de tasca d'un model. Estats nous (Sprint B); temps/log a Sprint C."""
    STATUS_CHOICES = [('Pending', 'Pending'), ('Paused', 'Paused'),
                      ('InProgress', 'InProgress'), ('Done', 'Done')]
    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='model_tasks')
    task_type = models.ForeignKey(TaskType, on_delete=models.PROTECT, related_name='instances')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    assignee = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='assigned_tasks')
    order = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True,
                          help_text="Snapshot del temps estimat en crear la tasca (minuts).")
    # Sprint B — planificació per tasca (motor d'scheduling determinista).
    planned_start = models.DateTimeField(null=True, blank=True,
                      help_text="Inici previst calculat pel motor (calendari laboral).")
    planned_end = models.DateTimeField(null=True, blank=True,
                    help_text="Fi prevista calculada pel motor.")
    planned_locked = models.BooleanField(default=False,
                       help_text="Posició manual fixa: el recàlcul es col·loca al voltant.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['model', 'order']
        verbose_name = 'Model task'
        verbose_name_plural = 'Model tasks'
        # Defensa de fons: una tasca de cada tipus per model (la view ja ho comprova;
        # això ho garanteix a BD contra curses i camins futurs sense check).
        unique_together = [('model', 'task_type')]

    def __str__(self):
        return f'{self.model_id} · {self.task_type.code} ({self.status})'


class TaskTransition(models.Model):
    """Log immutable de transicions d'estat d'una ModelTask. Base del comptador
    de rectificacions (Done→InProgress)."""
    model_task = models.ForeignKey('ModelTask', on_delete=models.CASCADE, related_name='transitions')
    from_status = models.CharField(max_length=20, null=True, blank=True)
    to_status = models.CharField(max_length=20)
    by = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL,
                           null=True, blank=True, related_name='task_transitions')
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['at']
        verbose_name = 'Task transition'
        verbose_name_plural = 'Task transitions'

    def __str__(self):
        return f'{self.model_task_id}: {self.from_status}→{self.to_status}'


class GateEvent(models.Model):
    """Log d'un gate: acceptació formal que avança la fase d'un Model.
    Captura qui accepta, quan, des de quina fase i cap a quina (memo §3.5)."""
    KIND_CHOICES = [('advance', 'advance'), ('regress', 'regress')]
    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='gate_events')
    from_phase = models.CharField(max_length=20, null=True, blank=True)
    to_phase = models.CharField(max_length=20)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default='advance')
    by = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL,
                           null=True, blank=True, related_name='gate_events')
    notes = models.TextField(null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['at']
        verbose_name = 'Gate event'
        verbose_name_plural = 'Gate events'

    def __str__(self):
        return f'{self.model_id}: {self.from_phase}→{self.to_phase}'


class Supplier(models.Model):
    """Destinatari d'una confecció (taller/fàbrica). Esquelètic ara; creix cap a fitxa
    de proveïdor en un sprint futur."""
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20,
                            choices=[('workshop', 'Taller'), ('factory', 'Fàbrica')], default='workshop')
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'

    def __str__(self):
        return self.name


class Production(models.Model):
    """Confecció: encàrrec extern de produir una peça per a una fase. Recurs extern amb
    cicle propi. Precondició: la fase ha d'haver passat el gate. La seva entrega (Delivered)
    habilita el fitting executable d'aquella fase."""
    STATUS_CHOICES = [('Requested', 'Requested'), ('InProgress', 'InProgress'),
                      ('Delivered', 'Delivered')]
    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='productions')
    phase = models.CharField(max_length=20)   # la fase que materialitza (Proto/Fit/...)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='productions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Requested')
    requested_at = models.DateTimeField(auto_now_add=True)
    expected_at = models.DateField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='requested_productions')
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Production'
        verbose_name_plural = 'Productions'

    def __str__(self):
        return f'{self.model_id} · {self.phase} · {self.status}'


class GarmentTypeItem(models.Model):
    """Variant d'un GarmentType per grau de complexitat (arbre família→variant).
    Ex: GarmentType 'Pantaló' → items xandall < chino < sastre. El node que tria un
    model per derivar estimacions de temps i (futur) matching de POMs."""
    garment_type = models.ForeignKey('pom.GarmentType', on_delete=models.CASCADE,
                                     related_name='items')
    code = models.SlugField(max_length=60)
    name = models.CharField(max_length=200)
    complexity_order = models.PositiveIntegerField(default=0,
                         help_text="Ordre de complexitat creixent dins la família")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['garment_type', 'complexity_order', 'code']
        unique_together = [('garment_type', 'code')]
        verbose_name = 'Garment type item'
        verbose_name_plural = 'Garment type items'

    def __str__(self):
        return f'{self.garment_type_id}/{self.code}'


class TaskTimeEstimate(models.Model):
    """Cel·la de la matriu d'estimació de temps: (garment_type_item × task_type) → minuts.
    estimated_minutes = SEED (estimació inicial). n/mean_minutes/m2 = estadística Welford de
    temps reals observats (Sprint I). El planificador usa mean_minutes si n>=llindar, si no seed."""
    garment_type_item = models.ForeignKey(GarmentTypeItem, on_delete=models.CASCADE,
                                          related_name='time_estimates')
    task_type = models.ForeignKey(TaskType, on_delete=models.CASCADE, related_name='time_estimates')
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    n = models.PositiveIntegerField(default=0)         # nombre de mostres reals
    mean_minutes = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # mitjana real
    m2 = models.DecimalField(max_digits=16, decimal_places=4, default=0)  # acum. variància (Welford)

    class Meta:
        unique_together = [('garment_type_item', 'task_type')]
        verbose_name = 'Task time estimate'
        verbose_name_plural = 'Task time estimates'

    def __str__(self):
        return f'{self.garment_type_item_id}×{self.task_type_id}={self.estimated_minutes}'


class PlanSnapshot(models.Model):
    """Fotografia immutable d'una previsió de campanya. Cada recàlcul en crea un de nou.
    Suport del previst-vs-real (§7): el previst es DESA, no es recalcula i s'oblida."""
    computed_at = models.DateTimeField(auto_now_add=True)
    computed_by = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='plan_snapshots')
    # Inputs desats (per reproduir/auditar el càlcul):
    start_date = models.DateField()
    technician_count = models.PositiveIntegerField(default=1)
    working_minutes_per_day = models.PositiveIntegerField(default=420)  # 7h; input, no constant
    blocked_dates = models.JSONField(default=list, blank=True)   # ["2026-06-02", ...]
    model_sequence = models.JSONField(default=list, blank=True)  # [110, 111, ...] ordenat
    # Metadada de filtre de campanya (no propietat; només context):
    campaign_filter = models.JSONField(default=dict, blank=True)  # {"temporada":"SS","any":26,"client":"..."}
    # Output desat:
    result = models.JSONField(default=dict, blank=True)
    # {"models": {"110": {"predicted_start":"...","predicted_end":"...","load_minutes":N}, ...},
    #  "campaign_end": "..."}

    class Meta:
        ordering = ['-computed_at']
        verbose_name = 'Plan snapshot'
        verbose_name_plural = 'Plan snapshots'

    def __str__(self):
        return f'Plan {self.id} @ {self.computed_at:%Y-%m-%d %H:%M}'
