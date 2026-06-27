from django.db import models


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


class TaskType(models.Model):
    """Catàleg CANÒNIC de tipus de tasca (propietat del sistema; el tenant no l'edita).
    PLA per disseny: l'arbre de 2 nivells (pare→subtasca) és UX del frontend, no jerarquia de BD.
    `default_order` és l'ordre canònic global. Gate i espera NO són tasca → no hi ha és_gate ni
    bloqueja_model aquí. Camps de procés (fase/tipus/eina/mode/facturable) sembrats per code."""
    FASE_CHOICES = [
        ('Disseny', 'Disseny'),
        ('Dev. tècnic', 'Dev. tècnic'),
        ('Prototip', 'Prototip'),
        ('Mostres', 'Mostres'),
        ('Preproducció', 'Preproducció'),
        ('Producció', 'Producció'),
    ]
    TIPUS_CHOICES = [
        ('Interna', 'Interna'),
        ('Externa-lliure', 'Externa-lliure'),
    ]
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    default_order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    # --- Catàleg canònic (Sprint catàleg de tasques) ---
    fase = models.CharField(max_length=20, choices=FASE_CHOICES, default='Dev. tècnic')
    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES, default='Interna')
    eina = models.CharField(max_length=30, null=True, blank=True,
                            help_text="Slug de l'eina que transporta la tasca. null = transport "
                                      "manual / eina futura.")
    mode = models.CharField(max_length=40, null=True, blank=True,
                            help_text="Context d'obertura de l'eina (sub-mode). null si sense eina.")
    facturable = models.BooleanField(default=True)

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
    # Origen de la tasca: 'prevista' = creada pel flux normal del PM (define-tasks /
    # assign-batch / open-task des d'una eina); 'ad_hoc' = iniciada fora de l'encàrrec
    # (arbre global / tasca externa lliure). El rending "fora d'encàrrec" (filet grana)
    # i la tasca ad-hoc en depenen. Default 'prevista' perquè tot el flux actual és d'encàrrec.
    ORIGEN_CHOICES = [('prevista', 'Prevista'), ('ad_hoc', 'Ad-hoc')]
    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='model_tasks')
    task_type = models.ForeignKey(TaskType, on_delete=models.PROTECT, related_name='instances')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default='prevista')
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


class Customer(models.Model):
    """Client final servit pel tenant (marca/empresa per a qui es treballa un model).
    Mirall esquelètic de Supplier. El `codi` (3 chars) és la font del prefix del codi_intern
    dels models i de l'abast de la seqüència. El tenant és client d'ell mateix via is_self=True
    (self-customer sembrat amb codi = Client.codi_tenant), de manera que el codi-gen mai depèn
    de cap hardcode."""
    codi = models.CharField(max_length=3, unique=True)
    nom = models.CharField(max_length=200)
    active = models.BooleanField(default=True)
    is_self = models.BooleanField(default=False,
                                  help_text="El tenant com a client d'ell mateix (self-customer).")
    # Ganxo per al registre global de codis del backoffice futur (permeabilitat cross-tenant).
    # Placeholder sense lògica en aquest sprint.
    codi_global = models.CharField(max_length=3, null=True, blank=True)
    # Logo del client (TS-4c): per a la capçalera de la fitxa tècnica.
    logo = models.ImageField(upload_to='customer_logos/%Y/%m/', null=True, blank=True)

    class Meta:
        ordering = ['codi']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'

    def __str__(self):
        return f'{self.codi} · {self.nom}'


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

    # Sprint Mesures Base per Item (P1) — talla base de la plantilla de l'Item: la talla a la qual
    # s'expressen els valors base d'ItemBaseMeasurement (P2). FK NORMAL (constraint real) cap a
    # pom.SizeDefinition, igual que `garment_type` → pom.GarmentType (pom viu al schema del tenant).
    # on_delete=SET_NULL: pointer OPCIONAL i tou — esborrar una talla del catàleg NO bloqueja (PROTECT)
    # ni destrueix l'Item (CASCADE); només neteja el pointer (el camp ja és nullable).
    # Sprint Llibreria d'Items (A3) — porta TANCADA: el lligam Item→GradingRuleSet JA existeix
    # (grading_rule_set, sota). base_size_definition es CONSTRENY al size_system d'aquell ruleset
    # via clean() (no constraint de BD, cross-table fràgil). Validació amb skip si algun és NULL.
    base_size_definition = models.ForeignKey(
        'pom.SizeDefinition', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='base_for_items',
        help_text="Talla base de la plantilla de l'Item (on s'expressen els valors base). Es "
                  "constreny al size_system del grading_rule_set (validat a clean()).")

    # Sprint Llibreria d'Items (A3) — context de grading de l'Item: UN sol ruleset.
    # FK MUTABLE (es pot canviar; les regles no s'apliquen fins desplegar-les al model) i de
    # moment NULLABLE: els items-llavor existents queden a NULL fins que la pàgina (Fase B) els
    # assigni ruleset; una 2a migració (post-Fase B) la farà NOT NULL quan tots en tinguin.
    # on_delete=PROTECT: esborrar un ruleset referenciat per items ha de BLOQUEJAR (no esborrar
    # items ni deixar-los orfes). Cross-app tasks→pom amb constraint REAL (pom viu al schema del
    # tenant), igual que base_size_definition (P1).
    grading_rule_set = models.ForeignKey(
        'pom.GradingRuleSet', on_delete=models.PROTECT,
        null=True, blank=True, related_name='garment_type_items',
        help_text="Context de grading de l'Item (un sol ruleset). Mutable; obligatori a la pàgina "
                  "(Fase B). Constreny base_size_definition al seu size_system.")

    class Meta:
        ordering = ['garment_type', 'complexity_order', 'code']
        unique_together = [('garment_type', 'code')]
        verbose_name = 'Garment type item'
        verbose_name_plural = 'Garment type items'

    def clean(self):
        # A3 — coherència talla base ↔ sistema de talles del ruleset. SKIP si algun dels dos és
        # NULL (els items-llavor amb tots dos a NULL han de poder desar-se). Es revalida sempre que
        # es desa (p.ex. en canviar el ruleset mutable). No és constraint de BD (cross-table fràgil).
        super().clean()
        if self.base_size_definition_id and self.grading_rule_set_id:
            if self.base_size_definition.size_system_id != self.grading_rule_set.size_system_id:
                from django.core.exceptions import ValidationError
                raise ValidationError({
                    'base_size_definition': (
                        "La talla base ha de pertànyer al mateix sistema de talles que el "
                        "grading rule set de l'Item.")
                })

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


class TimeSeed(models.Model):
    """Llavor de temps del tenant (cascada graó 3): minuts per defecte quan no hi ha cap
    cel·la (item×task) ni empíric global. HETEROGÈNIA (model híbrid c): uns nodes definits a
    nivell de task_type, altres a nivell de fase. Dada de tenant EVOLUTIVA, separada del
    catàleg canònic TaskType (que es manté read-only)."""
    SCOPE_CHOICES = [('task', 'task'), ('phase', 'phase')]
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    key = models.CharField(max_length=50,
            help_text="TaskType.code si scope='task'; TaskType.fase (nom de fase) si scope='phase'.")
    minuts = models.PositiveIntegerField()

    class Meta:
        unique_together = [('scope', 'key')]
        verbose_name = 'Time seed'
        verbose_name_plural = 'Time seeds'

    def __str__(self):
        return f'{self.scope}:{self.key}={self.minuts}'
