import uuid

from django.db import models
from django.conf import settings

# Single source of truth per a les opcions de lògica de grading. ModelGradingRule
# (resident al model) en reusa les choices: si demà canvien a pom.GradingRule, no
# divergeixen. pom.models no importa models_app → cap import circular a load time.
from fhort.pom.models import GradingRule


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

    # Provinença del model (Federació v2). INTERN = nascut en aquesta casa (el cas de sempre).
    # EXTERN = instanciat des d'un altre tenant via el pont de federació: conserva el sequencial
    # del Brand (dada real, útil per ordenar) però QUEDA EXCLÒS del càlcul de terra de seqüència,
    # perquè el seu número viu en un altre espai de numeració i enverinaria el comptador local.
    # NO és `origen_patro` (provinença del PATRÓ, no del model): eixos diferents, camps diferents.
    ORIGEN_INTERN = 'INTERN'
    ORIGEN_EXTERN = 'EXTERN'
    ORIGEN_CHOICES = [
        (ORIGEN_INTERN, 'Intern'),
        (ORIGEN_EXTERN, 'Extern'),
    ]

    codi_intern = models.CharField(max_length=40, unique=True)
    # SKU/referència pròpia del client per a aquest model (traçabilitat seva). Text lliure;
    # NO és prefix ni clau tècnica de codi-gen (això ho mana ara `customer`).
    codi_client = models.CharField(max_length=80, blank=True, default='')

    # Client final servit. Font del prefix del codi_intern i de l'abast de la seqüència
    # (via helper customer_code_for). PROTECT: esborrar un Customer amb models dona 409.
    # Nullable a BD per a la transició; el wizard l'exigeix.
    customer = models.ForeignKey(
        'tasks.Customer',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='models',
    )

    # DEPRECAT: còpia denormalitzada de customer.codi (la mantenim viva per als índexs/lectures
    # existents). El codi-gen ja no llegeix d'aquí; s'omple = customer.codi en crear.
    codi_tenant = models.CharField(max_length=3)
    any = models.PositiveSmallIntegerField()
    temporada = models.CharField(max_length=4, choices=TEMPORADA_CHOICES)
    sequencial = models.PositiveIntegerField()
    origen = models.CharField(
        max_length=20, choices=ORIGEN_CHOICES, default=ORIGEN_INTERN, db_index=True,
    )

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

    consumption_started_at = models.DateTimeField(null=True, blank=True)
    # Sprint 4: data en què el model va iniciar la primera tasca (meritació).
    # NULL = encara no ha consumit màquina. L'omple el servei a Sprint 4.2.

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
    # C4d — marcador "+": el model ha entrat/pujat al pla per INICI REAL d'una tasca (no per
    # reorder del planificador). Efímer: s'activa a l'auto-start (open_model_task_view) i es
    # neteja al següent reorder manual (plan/reorder). Perquè el planificador entengui per què
    # la llista de Planificació/Board/Gantt s'ha reordenat sola.
    reanchored_by_start = models.BooleanField(default=False)

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
    # DEPRECAT (S03a · P1.2) — eix mort. `tipus` és l'ÚNIC eix de classificació viu.
    # Ningú l'escriu amb valor semàntic ni el llegeix; el camp es conserva (patró G2:
    # deixar de llegir abans de deixar d'existir) i es farà drop en un sprint posterior.
    CATEGORIA_CHOICES = [
        ('Patro', 'Patró'),
        ('Disseny', 'Disseny'),
        ('Fitting', 'Fitting'),
        ('Document', 'Document'),
    ]

    # Origen del fitxer dins la cadena de versions (manual vs eines IA).
    ORIGEN_CHOICES = [
        ('upload', 'Pujada manual'),
        ('ia_escalat', "IA d'escalat"),
        ('ia_marcada', 'IA de marcada'),
        ('ia_ocr', 'IA OCR'),
    ]

    # EIX ÚNIC (S03a · P1.1). Els 9 primers valors són els que ja circulaven de facto com a
    # convenció de codi (byte-idèntics, cap migració de dades); RUL i SKETCH_SVG són nous.
    # La invariant is_current/versio (save_model_file) segueix sent agnòstica al tipus.
    TIPUS_CHOICES = [
        ('ALTRES', 'Altres'),
        ('DOCUMENT', 'Document'),
        ('TECHSHEET', 'Fitxa tècnica (.ftt)'),
        ('EXPORT', "PDF d'export"),
        ('PATRO', 'Patró'),
        ('ESCALAT', 'Escalat'),
        ('SKETCH_FLETXES', 'Sketch amb fletxes'),
        ('SKETCH_NET', 'Sketch net'),
        ('SKETCH_SVG', 'Sketch SVG'),
        ('MARCADA', 'Marcada'),
        ('RUL', 'RUL'),
    ]

    TIPUS_TECHSHEET = 'TECHSHEET'   # document editable .ftt (fitxa tècnica)
    TIPUS_EXPORT = 'EXPORT'         # PDF d'export generat des d'un document .ftt
    FTT_EXTENSION = '.ftt'

    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name='fitxers')
    nom_fitxer = models.CharField(max_length=255)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, blank=True)
    tipus = models.CharField(max_length=30, choices=TIPUS_CHOICES, default='ALTRES', blank=True)
    versio = models.PositiveIntegerField(default=1)
    # Invariant: exactament un is_current=True per cadena versio_anterior (el cap).
    is_current = models.BooleanField(default=True, db_index=True)
    versio_anterior = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions_posteriors',
    )
    # Enllaç (no cadena): per a artefactes generats des d'un altre fitxer, p.ex. un PDF
    # EXPORT generat des d'una versió concreta del document .ftt. NO és versio_anterior:
    # l'export és la seva pròpia cadena i el .ftt origen no es toca (is_current intacte).
    generat_des_de = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exports_generats',
    )
    # Procedència del catàleg (S03b · P5): aquest fitxer és una CÒPIA importada d'un
    # ItemFitxer. No és una edició compartida — l'origen no es toca mai i pot desaparèixer
    # (SET_NULL) sense afectar la còpia del model.
    derivat_de_item = models.ForeignKey(
        'models_app.ItemFitxer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usos_a_models',
    )
    # Procedència model→model (D17): aquest fitxer és una CÒPIA importada del fitxer d'un
    # ALTRE model. Germà de `derivat_de_item`, no de `generat_des_de`: els dos primers
    # codifiquen "còpia amb procedència" i el tercer "artefacte generat des d'un altre
    # fitxer" (p.ex. un PDF EXPORT d'un .ftt). Barrejar-los amagaria dues semàntiques sota
    # un sol camp. SET_NULL: l'origen pot desaparèixer sense afectar la còpia.
    #
    # ATENCIÓ (Q4.4 de DIAGNOSI_S03C_NAVEGACIO): a diferència de catàleg→model, un `.ftt`
    # model→model NO es pot copiar tal qual — porta text congelat, l'asset del logo, un
    # objecte image amb la URL i metadata del model origen. L'endpoint que escriurà aquest
    # camp (C3) haurà de reescriure'ls. Aquí només s'hi crea el camp.
    derivat_de_model = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derivats',
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

    enviat_ia = models.BooleanField(default=False)
    resultat_ia_path = models.CharField(max_length=500, null=True, blank=True)

    # Metadades de la cadena de versions (font: services_fitxers.save_model_file).
    checksum = models.CharField(max_length=64, blank=True)
    mimetype = models.CharField(max_length=100, blank=True)
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default='upload')

    class Meta:
        verbose_name = 'Fitxer de model'
        verbose_name_plural = 'Fitxers de model'

    def __str__(self):
        return f'{self.model.codi_intern} · {self.nom_fitxer} ({self.versio})'


def item_fitxer_upload_to(instance, filename):
    """`{schema}/items/<gti_id>/<filename>` — el prefix del schema el posa el storage
    (TenantFileSystemStorage, S03a · P2a); aquí només la part relativa al tenant."""
    return f'items/{instance.garment_type_item_id}/{filename}'


class ItemFitxer(models.Model):
    """Fitxer del CATÀLEG, ancorat a un GarmentTypeItem (S03b · P4).

    Mirall d'`ModelFitxer` a nivell d'item: mateixa invariant de cadena (`versio_anterior`
    + exactament un `is_current` per cadena, mantinguda per `save_item_file`) i el MATEIX
    conjunt `ModelFitxer.TIPUS_CHOICES` — no se n'inventa un de nou.

    Diferències deliberades respecte de ModelFitxer:
    - **Sense `categoria`**: aquell eix va morir a S03a · P1; no es reprodueix en un model nou.
    - Sense `url_extern`/`origen`/`generat_des_de`/`accessible_portal`: cap consumidor al
      catàleg. S'afegiran si algun dia hi ha un cas, no per simetria.
    """
    garment_type_item = models.ForeignKey(
        'tasks.GarmentTypeItem', on_delete=models.CASCADE, related_name='fitxers')
    nom_fitxer = models.CharField(max_length=255)
    tipus = models.CharField(max_length=30, choices=ModelFitxer.TIPUS_CHOICES,
                             default='ALTRES', blank=True)
    versio = models.PositiveIntegerField(default=1)
    # Invariant: exactament un is_current=True per cadena versio_anterior (el cap).
    is_current = models.BooleanField(default=True, db_index=True)
    versio_anterior = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='versions_posteriors')
    pujat_per = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL, null=True,
        related_name='item_fitxers_pujats')
    data_pujada = models.DateTimeField(auto_now_add=True)
    mida_bytes = models.BigIntegerField()
    fitxer = models.FileField(upload_to=item_fitxer_upload_to, null=True, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    mimetype = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Fitxer de catàleg (item)'
        verbose_name_plural = 'Fitxers de catàleg (item)'

    def __str__(self):
        return f'{self.garment_type_item_id} · {self.nom_fitxer} ({self.versio})'


class ImportSession(models.Model):
    ESTAT_CHOICES = [
        ('INICI','Inici'), ('CRIBRATGE','Cribratge'), ('TALLES','Talles'),
        ('EXTRACCIO','Extracció'), ('POMS','POMs'),
        ('MESURES','Mesures'), ('MESURES_OK','Mesures OK'),
        ('IMPORT','Import'),
        ('CONFIRMAT','Confirmat'), ('DESCARTAT','Descartat'),
    ]
    # Identificació
    token           = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    creat_per       = models.ForeignKey('accounts.UserProfile', null=True, blank=True,
                        on_delete=models.SET_NULL, related_name='import_sessions')
    data_creacio    = models.DateTimeField(auto_now_add=True)
    actualitzat_at  = models.DateTimeField(auto_now=True)
    # Estat del flux
    estat           = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='INICI')
    # Document origen (PDF, Excel o imatge)
    document        = models.FileField(upload_to='import_sessions/%Y/%m/',
                        null=True, blank=True)
    # Model destí (es crea en confirmar)
    model           = models.ForeignKey('models_app.Model', null=True, blank=True,
                        on_delete=models.SET_NULL, related_name='import_sessions')
    # Resultats per fase
    model_detectat          = models.JSONField(default=dict, blank=True)
    tipologia_confirmada    = models.ForeignKey('tasks.GarmentTypeItem', null=True, blank=True,
                                on_delete=models.SET_NULL)
    run_conciliat           = models.JSONField(default=dict, blank=True)
    poms_extrets            = models.JSONField(default=list, blank=True)
    resultat                = models.JSONField(default=dict, blank=True)
    historia_xat            = models.JSONField(default=list, blank=True)
    avisos                  = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-data_creacio']

    def __str__(self):
        return f'ImportSession {self.token} [{self.estat}]'


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
        ('CHECKED',    'Validat en size check (proto a talla base)'),
        ('ITEM_STANDARD', 'Sembrat de l\'estàndard de l\'item (copy-at-the-moment)'),
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
    scoped to ONE model — unlike the old `pom.GradingException`, which lived on the
    shared GradingRuleSet (a template) and would leak to every model using that set.

    G6/1a (2026-07-13): that argument won. `pom.GradingException` is now RETIRED, and this
    class is the only per-(POM, size) override in the engine. The docstring keeps naming it
    because the reason it was replaced is the reason this one is scoped to a single model —
    lose the reason and someone re-adds a template-level exception.

    The grading engine (generate_graded_specs) reads these with PRIORITY over the rules. The
    base-size case does NOT come here: it promotes to BaseMeasurement (the root) instead.
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


class ModelGradingRule(models.Model):
    """PG-0 — Graduació canònica RESIDENT al model (una regla per (model, POM)).

    Materialitza dins el tenant la mateixa forma canònica que pom.GradingRule, però
    penjant del Model en lloc d'un GradingRuleSet compartit extern. NO duplica la base
    (viu a BaseMeasurement) ni la config de run (model.size_run_model /
    model.base_size_label ja la porten): el break es resol per ETIQUETA contra el run
    del model, igual que fa _apply_rule avui.

    PG-0 només crea l'entitat — RES la consumeix encara. Cap canvi de comportament.
    """
    # R8 (2026-07-21) — 'CLIENT_RUN' hi faltava. El vocabulari de GradingRuleSet.origen
    # (CANONICAL/CLIENT_RUN/IMPORT) i el d'aquí no s'alineaven, i el wizard resolia la
    # diferència escrivint sempre 'CANONICAL': 104 regles residents de 4 models deien que
    # eren canòniques quan venien d'un run de client (DIAGNOSI_REFACTOR_GRADING_2026-07-21,
    # R8). Sense aquest valor, la provinença real no era ni expressable.
    ORIGEN_CHOICES = [
        ('IMPORTED', 'Importat de fitxa externa'),
        ('CANONICAL', 'Derivat canònicament'),
        ('CLIENT_RUN', 'Derivat de run de client'),
        ('MANUAL', 'Introduït manualment'),
    ]

    model = models.ForeignKey(
        'models_app.Model', on_delete=models.CASCADE, related_name='grading_rules',
    )
    # db_constraint=False: 'pom' és app SHARED (taula també a 'public'), però aquest model
    # és tenant-only → un constraint de BD cap a pom_pommaster petaria a 'public'. L'FK és
    # lògic (ORM). Mateix patró cross-schema que pom.GarmentPOMMap.garment_type_item.
    pom = models.ForeignKey(
        'pom.POMMaster', on_delete=models.PROTECT, related_name='model_grading_rules',
        db_constraint=False,
    )

    logica = models.CharField(max_length=20, choices=GradingRule.LOGICA_CHOICES)

    # Legacy LINEAR/FIXED: _apply_rule té una branca de fallback que llegeix `increment`
    # quan increment_base és NULL. Sense aquest camp, una regla no-canònica no graduaria.
    increment = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    valors_step = models.JSONField(null=True, blank=True)  # STEP origen/auditoria

    # Forma canònica d'aplicació (break ancorat per ETIQUETA, resolt al run del model).
    # valors_step roman com a origen/auditoria. NULL = no canònic → fallback a `increment`.
    increment_base = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    increment_break = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    talla_break_label = models.CharField(max_length=30, null=True, blank=True)
    talla_break_pos = models.IntegerField(null=True, blank=True)  # cache opcional (run del model)

    origen = models.CharField(max_length=20, default='CANONICAL', choices=ORIGEN_CHOICES)
    actiu = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Regla grading (model)'
        verbose_name_plural = 'Regles grading (model)'
        unique_together = [('model', 'pom')]

    def __str__(self):
        return f'{self.model} · {self.pom.codi_client} ({self.logica})'


# ───────────────────────── Import massiu de models (bulk) ─────────────────────────

class ModelSequence(models.Model):
    """Comptador atòmic de seqüencial per (customer, year, season), per a la creació en bulk.
    El camí manual (1 model) segueix usant el scan MAX(sequencial) del signal generate_model_code;
    el bulk reserva un rang en una sola operació via reserve_sequence_range() (services.py),
    amb select_for_update (mateix patró que tasks/services_i.py). El rang cobreix models simples
    i GarmentSet (el codi_base del set consumeix 1 número, igual que un model simple)."""
    customer = models.ForeignKey('tasks.Customer', on_delete=models.PROTECT,
                                 related_name='model_sequences')
    year = models.PositiveSmallIntegerField()
    season = models.CharField(max_length=4, choices=Model.TEMPORADA_CHOICES)
    last_seq = models.PositiveIntegerField(default=0, help_text="Últim seqüencial reservat")

    class Meta:
        unique_together = [('customer', 'year', 'season')]
        verbose_name = 'Seqüència de model'
        verbose_name_plural = 'Seqüències de model'

    def __str__(self):
        return f'{self.customer.codi} {self.season}{self.year} → {self.last_seq}'


class BulkCollectionImport(models.Model):
    """Staging d'una importació massiva de models des d'Excel (col·lecció): N esquelets en una
    sola pujada. Conceptualment diferent d'ImportSession (single-model). El Customer és el context
    de la importació (no una columna). Flux: PUJAT → VALIDANT → PREVISAT → IMPORTAT / DESCARTAT."""
    ESTAT_CHOICES = [
        ('PUJAT', 'Pujat'),
        ('VALIDANT', 'Validant'),
        ('PREVISAT', 'Previsat'),
        ('IMPORTAT', 'Importat'),
        ('DESCARTAT', 'Descartat'),
    ]
    customer = models.ForeignKey('tasks.Customer', on_delete=models.PROTECT,
                                 related_name='bulk_imports')
    document = models.FileField(upload_to='bulk_imports/%Y/%m/', null=True, blank=True)
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='PUJAT')
    # El tècnic que importa (= request.user.profile). PROTECT, mateixa convenció que SizeFitting.
    creat_per = models.ForeignKey('accounts.UserProfile', on_delete=models.PROTECT,
                                  related_name='bulk_imports')
    creat_at = models.DateTimeField(auto_now_add=True)
    resum = models.JSONField(default=dict, blank=True)       # {total, ok, errors, avisos, conjunts}
    resultat = models.JSONField(default=list, blank=True)    # resultats per fila (cache de preview)

    class Meta:
        ordering = ['-creat_at']
        verbose_name = 'Importació massiva'
        verbose_name_plural = 'Importacions massives'

    def __str__(self):
        return f'BulkImport #{self.pk} {self.customer_id} [{self.estat}]'


class BulkCollectionRow(models.Model):
    """Una fila del staging d'import massiu (resultat de la validació/preview). El Model real
    es crea al commit parcial (Pas 6) i s'enllaça a model_creat."""
    ESTAT_CHOICES = [
        ('OK', 'OK'),
        ('ERROR', 'Error'),
        ('AVIS', 'Avís'),
        ('DUPLICAT', 'Duplicat'),
    ]
    importacio = models.ForeignKey(BulkCollectionImport, on_delete=models.CASCADE,
                                   related_name='rows')
    row_num = models.PositiveIntegerField(help_text="Número de fila al fitxer Excel")
    raw_data = models.JSONField(default=dict, blank=True)    # contingut original de la fila
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES)
    errors = models.JSONField(default=list, blank=True)      # [{camp, missatge_client}] llegibles pel client
    model_creat = models.ForeignKey('models_app.Model', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='bulk_rows')

    class Meta:
        ordering = ['importacio', 'row_num']
        verbose_name = 'Fila d\'importació massiva'
        verbose_name_plural = 'Files d\'importació massiva'

    def __str__(self):
        return f'Row {self.row_num} [{self.estat}]'


class ConsumptionRecord(models.Model):
    """Sprint 4: albarà de consum. Viu al TENANT, el veu el client.
    Àncora immutable del fet 'aquest model va meritar'. El detall viu/creixent
    (tasques, temps, usuaris) es calcula sobre TaskTransition, NO es duplica aquí."""
    model = models.OneToOneField(
        'models_app.Model', on_delete=models.CASCADE, related_name='consumption_record'
    )
    code_snapshot = models.CharField(max_length=40)            # snapshot de codi_intern
    name_snapshot = models.CharField(max_length=200, blank=True, default='')  # snapshot de nom_prenda
    period = models.CharField(max_length=7)                    # 'YYYY-MM'
    opaque_ref = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    merited_at = models.DateTimeField()                        # set explícit pel servei (4.2)

    class Meta:
        ordering = ['-merited_at']

    def __str__(self):
        return f'{self.code_snapshot} · {self.period}'


# ───────────────────────── Size Check (SC-0) ─────────────────────────
# Validació del proto a talla base, ABANS del fitting. Entitat NETA (no reusa
# PieceFitting). Germana estructural de PieceFitting/PieceFittingLine però viu a
# models_app perquè toca Model + BaseMeasurement (tots dos aquí) i és pre-fitting.
# En acceptar-se, escriu BaseMeasurement amb origen='CHECKED' (rastre via el signal
# F1, mateix patró que el bloc FITTED de fitting/services.py).

class SizeCheck(models.Model):
    """Un check de talla base per a un model (proto vs esperat). Historial repetible:
    SENSE unique_together — un model pot acumular N checks al llarg del temps."""
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('Acceptat', 'Acceptat'),      # gravat amb totes acceptades → propaga al grading
        ('Rebutjat', 'Rebutjat'),      # gravat però amb mesures descartades → NO propaga (proto a refer)
        ('Descartat', 'Descartat'),    # decisió de no mesurar ara → NO propaga; tasca reagendada
    ]

    model = models.ForeignKey(
        'models_app.Model', on_delete=models.PROTECT, related_name='size_checks',
    )
    estat = models.CharField(max_length=10, choices=ESTAT_CHOICES, default='Pendent')
    talla_base_label = models.CharField(max_length=20)
    missatge_fabricant = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='size_checks_creats',
    )
    resolt_per = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='size_checks_resolts',
    )
    resolt_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Validació de talla'
        verbose_name_plural = 'Validacions de talla'
        ordering = ['model', '-created_at']

    def __str__(self):
        return f'SizeCheck #{self.pk} · {self.model} [{self.estat}]'


class SizeCheckLine(models.Model):
    """Una fila (POM) del check, només a talla base. valor_teoric = snapshot del
    BaseMeasurement.base_value_cm vigent en crear la línia; valor_real = mesura del tècnic."""
    size_check = models.ForeignKey(
        SizeCheck, on_delete=models.CASCADE, related_name='linies',
    )
    # db_constraint=False: 'pom' és app SHARED (taula també a 'public') però aquest model
    # és tenant-only → mateix patró cross-schema que ModelGradingRule.pom.
    pom = models.ForeignKey(
        'pom.POMMaster', on_delete=models.PROTECT, related_name='+',
        db_constraint=False,
    )
    valor_teoric = models.FloatField()
    valor_real = models.FloatField(null=True, blank=True)
    # SC-3: decisió per línia (substitueix el bool acceptat). null = sense decidir encara.
    #   tolerancia_acceptada → el valor_real es propaga a la base (CHECKED) en resoldre.
    #   valor_descartat      → es manté la base original; nota preescrita.
    DECISIO_CHOICES = [
        ('tolerancia_acceptada', 'Tolerància acceptada'),
        ('valor_descartat', 'Valor descartat'),
    ]
    decisio = models.CharField(max_length=24, choices=DECISIO_CHOICES, null=True, blank=True)
    nota = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        verbose_name = 'Línia de validació de talla'
        verbose_name_plural = 'Línies de validació de talla'
        ordering = ['size_check', 'pom']
        unique_together = [('size_check', 'pom')]

    def __str__(self):
        return f'{self.size_check_id} · {self.pom.codi_client}'


class Watchpoint(models.Model):
    """D-12 — advertència de TEXT LLIURE que viatja amb el MODEL a través dels gates. Ancorada al
    model i, com a ORIGEN, a la tasca/ronda on es va crear (referència; travessa gates igualment).
    Cicle open→resolved (qui/quan/per què). NO va a la fitxa tècnica; viu a l'historial perquè un
    altre tècnic entengui l'advertència."""
    ESTAT_CHOICES = [('open', 'Oberta'), ('resolved', 'Resolta')]
    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='watchpoints')
    # Origen: la tasca/ronda on es va crear (la referència es conserva encara que la tasca es tanqui).
    task = models.ForeignKey('tasks.ModelTask', on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='watchpoints')
    text = models.TextField()
    # F2 — Watchpoint estructurat: si 'dades' és no-null, és un Watchpoint de SISTEMA (no human-authored;
    # p.ex. l'import viu) i conté dades per renderitzar per clau en l'idioma del lector (llista de claus de
    # config que falten, de model_config_missing). Combinat amb task IS NULL identifica l'origen import.
    dades = models.JSONField(null=True, blank=True)
    estat = models.CharField(max_length=10, choices=ESTAT_CHOICES, default='open')
    created_by = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='watchpoints_creats')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_by = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='watchpoints_resolts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Watchpoint'
        verbose_name_plural = 'Watchpoints'
        ordering = ['-created_at']

    def __str__(self):
        return f'Watchpoint #{self.pk} ({self.estat}) · model {self.model_id}'


# Plantilla de fitxa per Customer. Definida a tech_sheet_models.py i importada aquí perquè
# Django la descobreixi dins l'app `models_app`. (El model TechSheet per-model s'ha jubilat
# a la Fase 2 .ftt; el document editable viu com a ModelFitxer tipus TECHSHEET.)
from .tech_sheet_models import TechSheetTemplate  # noqa: E402,F401

# Sistema de documents .ftt: magatzem de plantilles + lock del document lògic.
from .ftt_models import DocumentTemplate, FttDocumentLock  # noqa: E402,F401


class AIUsage(models.Model):
    """Cost d'una crida a l'API d'Anthropic feta pel pipeline d'import/extracció.

    Decisió Agus 2026-07-22: «tot usage es loggeja». L'objectiu és que la pregunta "què ens
    ha costat aquest import?" tingui resposta amb una consulta, i que el cribratge que ara
    NO es fa (xlsx determinista) es vegi com el que és: una fila que no hi és.

    Append-only per naturalesa: una crida feta no es desfà. No hi ha `update` enlloc del
    codi; si una crida falla, es registra igual amb `ok=False` — una crida que peta també
    s'ha pagat, i no registrar-la faria que el cost real quedés per sota del comptat.

    Els tokens es desen crus (input/output/cache) i NO es converteixen a euros aquí: la
    tarifa canvia amb el temps i per model, i una xifra en euros congelada al moment de la
    inserció seria mentida sis mesos després. El preu es multiplica quan es consulta.
    """
    CAMI_CHOICES = [
        ('cribratge', 'Cribratge'),
        ('revisio', 'Revisió'),
        ('extraccio', 'Extracció'),
        ('fallback', 'Fallback'),
    ]
    cami = models.CharField(max_length=20, choices=CAMI_CHOICES, db_index=True)
    model_ia = models.CharField(max_length=80, help_text="Model d'Anthropic (p.ex. claude-opus-4-7)")
    import_session = models.ForeignKey('models_app.ImportSession', on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='ai_usages')
    model = models.ForeignKey('models_app.Model', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='ai_usages')
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    # El caching de prompt és el gruix de l'estalvi de la via Opus: separat perquè es vegi.
    cache_creation_tokens = models.IntegerField(default=0)
    cache_read_tokens = models.IntegerField(default=0)
    ok = models.BooleanField(default=True)
    error = models.TextField(blank=True, default='')
    created_by = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='ai_usages')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Ús d\'IA'
        verbose_name_plural = "Usos d'IA"
        ordering = ['-created_at']

    def __str__(self):
        return (f'{self.cami} · {self.model_ia} · '
                f'{self.input_tokens}in/{self.output_tokens}out')
