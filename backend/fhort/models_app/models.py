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
    # SET-1 · A3 (2026-07-27) — MERITACIÓ DE CONJUNT. Decisió 2: **SET = 1 mèrit**. La marca
    # d'arrencada viu AQUÍ, no repartida entre les peces, perquè és el conjunt el que merita.
    # Les germanes reben igualment el seu `consumption_started_at` (perquè el criteri de forat
    # de `reconcile_consumption` no les torni a meritar), però l'albarà n'és un i penja d'aquí.
    consumption_started_at = models.DateTimeField(null=True, blank=True)

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
    # Federació v2 (P6) — assignació Brand→Studio: codi del tenant Studio autoritzat a
    # instanciar aquest model. Buit = cap Studio. L'escriu el Brand; és la seva palanca de
    # sobirania sobre cada model. Referència per codi nu (patró de la casa, mai FK): viu al
    # schema del Brand i el Studio es resol per codi_tenant. Dues claus independents: el
    # TenantLink autoritza el PONT, aquest camp autoritza CADA MODEL — sense assignació, res viatja.
    studio_assignat = models.CharField(max_length=3, blank=True, default='', db_index=True)

    # Federació v2 · RETORN-2 (2026-07-27) — el CANAL D'ESTAT. Materialització del que passa a
    # l'ALTRA casa sobre aquesta mateixa peça: al bessó de la MARCA hi arriba la maduresa que
    # publica l'estudi (fase + recompte de tasques); és la finestra, no la font.
    #
    # PER QUÈ UN JSON I NO COLUMNES: el que viatja aquí és un RESUM d'estat aliè, no dades de
    # domini d'aquesta casa. Res del sistema hi consulta per decidir (ni el planificador, ni
    # els gates, ni el motor): només es pinta. Fer-ne columnes convidaria a filtrar-hi i a
    # tractar-lo com a veritat local, que és exactament el que la doctrina prohibeix. Les
    # dades que SÍ manen (prioritat, data_objectiu) viatgen a camps reals, no aquí.
    #
    # CAP HORA, CAP TÈCNIC, CAP COST hi entra mai (doctrina views_encarrecs.py:6-8). El
    # servei que l'escriu (tenants/federation_service.sync_estat) és l'únic escriptor i té un
    # test negatiu que ho defensa.
    federacio_estat = models.JSONField(null=True, blank=True)

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
    # ── SET-2/T8 · L'EIX DE LA PEÇA, A LA SESSIÓ ─────────────────────────────────────
    # Decisió Agus (Patró C): **un import = una prenda**, i s'inicia DES DE LA PEÇA. El
    # garment de destí, doncs, no és una pregunta del wizard ni una decisió que viatgi per
    # fila: és CONTEXT, i el context d'una sessió viu a la sessió. Es fixa a la iniciació
    # (`import_session_cribratge_view`) i el confirm hi escriu TOTES les files.
    #
    # `''` és la peça mare —el 100% del corpus del 12/08— i per això el default no canvia
    # el comportament de cap sessió existent: una sessió d'abans d'aquesta columna té ''
    # i escriu on ha escrit sempre.
    #
    # I ÉS TAMBÉ EL REGISTRE import→peça que el brief demana: cada `ImportSession` queda
    # amb el seu document, el seu model i la seva prenda. Els exemples etiquetats que una
    # detecció futura haurà de VALIDAR surten d'aquí (no és entrenament ni s'hi anota com
    # a tal: és el que aquest import va fer, dit en clar).
    garment         = models.CharField(
                        max_length=20, blank=True, default='',
                        help_text="Peça de destí de l'import: codi de ModelGarment ('02', "
                                  "'03'…). '' és la peça mare, que és el Model mateix.")
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
        # Sprint B (2026-07-27) — còpia model→model. Cap dels valors anteriors serveix: copiar
        # `src.origen` verbatim faria que un MANUAL del model A afirmés que algú va mesurar el
        # model B, que és una mentida d'auditoria. `COPIED` diu la veritat: el valor és cert
        # però la seva autoritat viu en un altre model.
        ('COPIED', 'Copiat d\'un altre model'),
        # RETORN-1 (2026-07-27) — arribat per la FEDERACIÓ, de l'altra casa. No és 'COPIED'
        # (que parla d'un altre MODEL d'aquesta mateixa casa) ni 'IMPORTED' (que parla d'una
        # fitxa externa que algú ha llegit): és el mateix model, mesurat per l'altra banda del
        # pont. La distinció importa el dia que algú pregunti «qui va mesurar això»: la
        # resposta és «l'estudi», i cap dels altres valors ho diu.
        ('FEDERAT', "Arribat de l'altra casa (federació)"),
        # C3/C (2026-08-02) — DERIVAT D'UNA GERMANA. El valor no l'ha mesurat ningú: el sistema
        # l'ha mogut perquè s'ha corregit una altra fila del MATEIX POM dins del mateix model
        # (l'exterior puja de 54 a 56 → el folre puja de 52 a 54). Es mou el VALOR, mai el
        # grading; la folgança es conserva sola perquè ningú no la toca.
        #
        # Cap dels valors anteriors ho pot dir: 'CALCULATED' parla de talla base + delta dins
        # d'una mateixa fila, i 'COPIED'/'FEDERAT' parlen de valors que vénen de fora del model.
        # Aquest ve de la fila del costat.
        #
        # La distinció no és decorativa: sense ella una auditoria exterior↔folre es compara amb
        # ella mateixa i sempre dona verd, perquè no pot saber si el folre el va mesurar algú o
        # el va moure el sistema. I el que ho ha de dir sobretot és L'ENTRADA DEL REGISTRE, no
        # aquesta columna: l'origen d'una fila el sobreescriu el canvi següent, mentre que el
        # `MeasurementChangeLog` és append-only i conserva la seqüència.
        ('DERIVAT', 'Derivat d\'una germana (mateix POM, altra capa o instància)'),
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

    # F3 — SECCIÓ d'origen de la mesura al document importat ('01.- DRESS', 'Bodice:'…).
    # És el rètol que agrupava les files a la fitxa del client, i fins ara es perdia al
    # confirm tot i que els DOS camins d'extracció ja el capturaven (parser i IA).
    # És DADA DESCRIPTIVA, no estructura: ningú no hi decideix res. Serveix perquè la fitxa
    # tècnica pugui partir la taula de mesures en una taula per peça, que és el que l'humà
    # composa a mà avui.
    #
    # ⚠️ LÍMIT CONEGUT, no resolt aquí (DIAGNOSI_MULTIPECA_DALIA §Q2 i taula final §9): la
    # clau segueix sent `unique_together = [('model','pom')]`. Si DUES seccions del mateix
    # document comparteixen un POM, el confirm en col·lapsa les files i la que sobreviu es
    # queda amb la secció de l'ÚLTIMA — aquest camp no ho pot arreglar, perquè el bloqueig
    # no és el camp que faltava sinó la clau. Separar-les de debò vol tocar la clau, que
    # travessa 5 taules més, i és decisió d'arquitectura (Patró C), no d'aquest sprint.
    seccio = models.CharField(max_length=60, blank=True, default='')

    # Sprint NOMS-POM (2026-07-30) — EL BATEIG DEL MODEL.
    #
    # LLEI: bateig del model; buit = catàleg mana. Els dos textos amb què aquest MODEL anomena
    # la mesura — el nom canònic (EN, el del sector) i la traducció que en fa servir el client —
    # viuen a la LÍNIA de mesura, no al catàleg. Buits (''), qui llegeix cau al catàleg
    # (`POMGlobal.nom_en` / `nom_ca`, o `POMMaster.nom_client`), que és el comportament d'abans
    # d'aquest sprint: cap fila neix rebatejada.
    #
    # És la TERCERA aplicació del mateix patró canònic+bateig que ja governa el projecte:
    #   1. les peces (D-3): rol canònic del catàleg + nom que el patronista hi posa;
    #   2. `nom_fitxa` (S14-A, just aquí a sobre): codi canònic del POM + nomenclatura curta
    #      que el model escriu al croquis;
    #   3. aquests dos camps: nom del catàleg + nom que el model (i el seu client) fa servir.
    # El catàleg NO es toca mai des d'aquí: rebatejar una mesura d'un model no pot reescriure
    # com l'anomenen els altres 900 models de la casa.
    #
    # Són DADA DE PRESENTACIÓ, no estructura: ningú hi decideix res (ni el motor de grading, ni
    # el matcher, ni la clau (model, pom)). Per això no passen pel `MeasurementChangeLog` —
    # veg. l'argument sencer a `base_measurement_noms_view` (models_app/views.py).
    nom_canonic_model = models.CharField(
        max_length=160, blank=True, default='',
        help_text="Nom canònic (EN) amb què AQUEST model anomena la mesura. "
                  "Buit: mana el catàleg (POMGlobal.nom_en).",
    )
    nom_traduit_model = models.CharField(
        max_length=160, blank=True, default='',
        help_text="Traducció del nom que fa servir el client d'aquest model. "
                  "Buit: mana el catàleg (POMGlobal.nom_ca / POMMaster.nom_client).",
    )

    # ── C1 (2026-07-30) — LA CAPA. Declaració canònica del camp; les altres set taules
    # de mesura el porten igual i apunten aquí.
    #
    # De quina MATÈRIA de la peça parla aquesta mesura: l'exterior, el folre, l'entretela…
    # El pit de l'exterior i el pit del folre no són el mateix valor, i fins avui el sistema
    # no els sabia distingir perquè la clau era `(model, pom)` i prou. Aquest camp és l'eix
    # que hi faltava; la clau ampliada arriba a C1/T3.
    #
    # REFERÈNCIA PER SLUG, MAI PER PK (llei G9). No és un FK a `pom.MeasurementLayer` a
    # posta: el catàleg viu a `fhort.pom` (SHARED **i** TENANT) i aquestes taules són
    # tenant-only o creuen schemas — un FK real petaria a `public` pel mateix motiu que ja
    # obliga `db_constraint=False` a mig arxiu. El slug, a més, és el que viatja entre
    # tenants i entre versions; una PK no viatja.
    #
    # La VALIDACIÓ contra el catàleg NO és aquí: arriba a C2/C4. Fins llavors mana la
    # COMPORTA de C1/T4 — un CHECK a BD que només deixa passar 'exterior'. Cap escriptor pot
    # crear una segona capa per accident abans que la cadena de consumidors hi estigui
    # adaptada; C4 el retirarà per migració.
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
                  "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).",
    )
    # ── C1-ins — LA INSTÀNCIA. Declaració canònica del camp; les altres vuit taules de la
    # cadena en porten una d'igual i apunten aquí.
    #
    # SEGON EIX, ORTOGONAL A LA CAPA. La capa diu de quina MATÈRIA parla la mesura
    # (exterior, folre, entretela…); la instància diu de QUINA DE LES REPETICIONS d'aquest
    # mateix POM sobre la mateixa matèria parla: la sisa dreta i l'esquerra, el pit RELAXED i
    # l'EXTENDED. Fins avui la segona d'aquestes files no podia existir: xocava amb la
    # primera, i el sistema es defensava BLOQUEJANT-LA (els set nodes de §II.13 del dossier).
    #
    # SLUG COMPOST CANÒNIC, mai FK i mai `choices` — exactament com `capa`, i pel mateix
    # motiu (llei G9: per slug, mai per PK; el slug viatja entre tenants i entre versions).
    # L'ORDRE DE COMPOSICIÓ ('left-relaxed' i no 'relaxed-left') el decidirà la UI a C4-ins:
    # la BD només en guarda l'string ja compost, i no el sap desmuntar.
    #
    # `''` (cadena buida, MAI NULL) és la instància ÚNICA: el que fins avui era «la mesura»,
    # sense qualificar. NULL voldria dir «no se sap», i aquí sempre se sap.
    #
    # La VALIDACIÓ contra un diccionari d'instàncies NO és aquí: arriba amb C4-ins i la
    # Montse. Fins llavors mana la COMPORTA — un CHECK a BD que només deixa passar ''.
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )
    # ── SET-2/T2 — EL GARMENT (la peça dins del model). Declaració canònica del camp; les
    # altres cinc taules de la família en porten una d'igual i apunten aquí.
    #
    # TERCER EIX, ORTOGONAL ALS DOS ANTERIORS. La capa diu de quina MATÈRIA parla la mesura;
    # la instància, de quina de les REPETICIONS del mateix POM sobre la mateixa matèria; el
    # garment diu de quina PRENDA del model parla — el top i la calceta d'un bikini, la
    # jaqueta i el pantaló d'un pijama. Fins avui un model era una sola prenda: la segona
    # mesura de «pit» no podia existir perquè xocava amb la primera.
    #
    # ⚠️ «GARMENT», NO «PEÇA» (D2): «peça» ja vol dir un Model sencer a `PieceFitting`, a
    # `Model.piece_number` i a `GarmentTypeItemPart.nom_peca`. La col·lisió és de codi; a la
    # UI en català se'n segueix dient «peça».
    #
    # CODI, MAI FK — i pel mateix motiu que `capa` i `instancia` (llei G9: per slug/codi, mai
    # per PK). El codi és el de `ModelGarment.codi` ('02', '03'…), que viatja entre tenants i
    # entre versions; una PK no viatja. La FK real petaria a `public` com la de la capa.
    #
    # `''` (cadena buida, MAI NULL) és la PEÇA MARE: el que fins avui era «el model», sense
    # qualificar. NULL voldria dir «no se sap», i aquí sempre se sap. (D1, i és la mateixa
    # llei que ja governa `instancia` just aquí a sobre.)
    #
    # CONVENCIÓ MANDROSA (D3): la mare NO té mai fila pròpia a `ModelGarment` — els seus
    # valors ja viuen als camps de `Model`, i materialitzar-la seria duplicar la font de
    # veritat. Només es materialitza a partir de la 02.
    #
    # La VALIDACIÓ contra `ModelGarment` NO és aquí: arriba amb el tram T2-bis. Fins llavors
    # mana la COMPORTA — un CHECK a BD que només deixa passar ''.
    garment = models.CharField(
        max_length=20, default='', db_index=True,
        help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). "
                  "'' és la peça mare, que és el Model mateix. Fins a la retirada de la "
                  "comporta només s'admet '' (comporta CHECK a BD).",
    )

    class Meta:
        verbose_name = 'Mesura base'
        verbose_name_plural = 'Mesures base'
        # C1/T3 — la clau incorpora la CAPA. Fins avui un model no podia tenir el pit de
        # l'exterior i el pit del folre alhora: la segona fila xocava amb la primera. Amb tot
        # a 'exterior' la clau nova és estrictament més permissiva que la vella (mateixes
        # columnes + una), o sigui que no pot rebutjar res que abans passés ni deixar entrar
        # cap duplicat que abans es barrés. Qui de debò impedeix una segona capa avui és la
        # comporta CHECK de T4, no aquesta clau.
        #
        # C1-ins/T3 — i ara també la INSTÀNCIA, pel mateix argument literal: mateixes
        # columnes + una, amb `instancia` constant ('') a totes les files → estrictament més
        # permissiva, 0 duplicats latents possibles. Qui impedeix la segona instància avui és
        # la comporta `_instancia_gate_cins`, no aquesta clau.
        #
        # SET-2/T2 — i ara també el GARMENT, pel mateix argument literal per tercera vegada:
        # mateixes columnes + una, amb `garment` constant ('') a totes les files →
        # estrictament més permissiva, 0 duplicats latents possibles. Qui impedeix la segona
        # peça avui és la comporta `_garment_gate_set2`, no aquesta clau.
        unique_together = [('model', 'pom', 'capa', 'instancia', 'garment')]
        # `capa` entra a l'ordre entre el model i l'ordre de fitxa: quan hi hagi més d'una
        # capa, la fitxa les vol AGRUPADES, no barrejades per `ordre`. Avui és un no-op
        # observable —amb una sola capa el valor és constant i l'ordre relatiu no es mou—,
        # i el fumeig de base-stages ho verifica byte a byte.
        ordering = ['model', 'capa', 'ordre', 'pom']
        constraints = [
            # ── C1/T4 — LA COMPORTA. Declaració canònica; les altres set taules de mesura
            # en porten una d'igual i apunten aquí.
            #
            # El tancament de seguretat del pla de capes. C1 ensenya l'IDIOMA de la capa al
            # sistema (catàleg + columna + claus) però NO el deixa parlar-lo encara: la
            # cadena de consumidors —serializers, motor, UI, import, fitxa— continua
            # assumint una mesura per (model, POM) i no s'adapta fins a C2/C3. Entre C1 i
            # C3, doncs, hi ha una finestra en què l'esquema ja admetria una segona capa i
            # el codi encara no la sabria llegir: una fila 'folre' escrita per accident en
            # aquesta finestra no petaria enlloc, es fondria dins les llistes com si fos de
            # l'exterior i corrompria en silenci mesures que són el producte.
            #
            # Aquest CHECK tanca la finestra a la BD, que és l'únic lloc on cap camí
            # d'escriptura no la pot esquivar: ni un `bulk_create`, ni un `update()`, ni un
            # loader, ni un `psql` a mà. No hi ha guard d'aplicació que ho iguali, i per
            # això no n'hi escrivim cap.
            #
            # **C4 EL RETIRA PER MIGRACIÓ.** És bastida, no arquitectura: el dia que la
            # cadena sap llegir capes, aquest constraint és justament el que ho impedeix.
            # Si el trobes vigent i C4 ja ha passat, és un deute, no una llei.
            # ✅ C4/G1 (04/08) — LA COMPORTA DE CAPA S'HA RETIRAT (migració 0076). Era
            # bastida i no arquitectura, i el seu propi comentari ho deia: «el dia que la
            # cadena sap llegir capes, aquest constraint és justament el que ho impedeix».
            # La cadena ja les sap llegir i escriure: v. `test_c4_germanes_a_les_superficies`
            # (les 10 superfícies) i `test_c4_escriptura_germanes` (els sis escriptors).
            # ── C1-ins — LA SEGONA COMPORTA. Declaració canònica; les altres vuit taules de
            # la cadena en porten una d'igual i apunten aquí.
            #
            # Mateixa bastida, mateix motiu, eix diferent. L'esquema ja sap dir «sisa
            # esquerra» i «sisa dreta», però la cadena de lectors encara indexa per
            # `pom_id` (o, com a molt, per `(pom_id, capa)`): una segona instància escrita
            # per accident abans de FASE_2/FASE_3 no petaria enlloc —es fondria dins les
            # llistes com la primera— i corrompria en silenci mesures que són el producte.
            #
            # Va a la BD i no a l'aplicació pel mateix motiu que la de capa: és l'únic lloc
            # que un `bulk_create`, un `update()`, un loader de paquet o un `psql` a mà no
            # poden esquivar.
            #
            # **C4-ins LA RETIRA PER MIGRACIÓ**, al costat de la seva germana de capa.
            # ✅ C4/G1 (04/08) — LA COMPORTA D'INSTÀNCIA S'HA RETIRAT (migració 0076), al
            # costat de la seva germana de capa, tal com el seu comentari deia.
            # ── C1-ins · DECISIÓ D1 — UNA INSTÀNCIA SENSE NOM DE FITXA ÉS IL·LEGAL.
            #
            # Aquesta no és bastida: és una llei de domini, i sobreviu a C4-ins. Si una
            # mesura es desdobla, l'única cosa que fa que les dues files siguin
            # distingibles per a un humà —al croquis, a la taula, al paper— és el
            # `nom_fitxa`. Dues files «pit» sense res que les separi visualment no són dues
            # mesures: són un duplicat amb aparença de dada bona, que és exactament el mode
            # de fallada que tot aquest tram existeix per evitar.
            #
            # Amb la comporta tancada (`instancia` sempre '') la condició és trivialment
            # certa a totes les files, present i futures: no rebutja res que avui passi.
            models.CheckConstraint(
                condition=~models.Q(instancia__gt='', nom_fitxa=''),
                name='models_app_basemeasurement_instancia_exigeix_nom',
            ),
            # ── SET-2/T2 — LA TERCERA COMPORTA. Declaració canònica; les altres cinc taules
            # de la família en porten una d'igual i apunten aquí.
            #
            # Mateixa bastida, mateix motiu, eix nou. L'esquema ja sap dir «el pit del top» i
            # «el pit de la calceta», però la cadena de consumidors —motor, escriptors,
            # import, graella, Resum, federació— encara assumeix una mesura per
            # `(model, POM, capa, instancia)` i no s'adapta fins a T4/T5. Entre T2 i T5 hi ha
            # una finestra en què l'esquema ja admetria una segona peça i el codi encara no
            # la sabria llegir: una fila '02' escrita per accident en aquesta finestra no
            # petaria enlloc —es fondria dins les llistes com si fos de la mare— i corrompria
            # en silenci mesures que són el producte.
            #
            # Va a la BD i no a l'aplicació pel mateix motiu que les seves dues germanes: és
            # l'únic lloc que un `bulk_create`, un `update()`, un loader de paquet o un
            # `psql` a mà no poden esquivar.
            #
            # **QUI LA RETIRA, I QUÈ HA D'ESTAR VERD ABANS.** La retirada NO es fa sense el
            # test de R3 verd: `germanes_de` (`services_derivacio.py`) filtra per
            # `(model, pom)` + «un eix diferent» i ESCRIU a les germanes (`aplica()`). Amb
            # dues peces i el filtre curt, corregir el pit del top mouria el de la calceta
            # —el mateix valor, en silenci, i creuant peces—: un bug de creuament
            # indetectable. Mentre aquesta comporta visqui, cap '02' pot existir i el filtre
            # de R3 és un no-op; per això la comporta és el gate i no la data.
            # ✅ SET-2/#12 (12/08) — RETIRADA per la migració `0084`, amb les condicions que
            # la mateixa comporta exigia verdes i mesurades: T4 ensenya el motor a distingir
            # peces, T5 els escriptors, i el filtre de R3 ja mira l'eix sencer
            # (`services_derivacio.EIXOS_DE_GERMANOR`) —o sigui que corregir el pit del top
            # ja no pot moure el de la calceta. Gate obert amb la suite sencera verda
            # (1841/1841, 12/08) i autorització de l'Agus. A partir d'aquí un '02' és legal
            # a tota la família i `garment` deixa de ser una columna congelada.
        ]

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
    # C1 — la capa (declaració canònica a `BaseMeasurement.capa`).
    #
    # AFEGIR AQUESTA COLUMNA NO VIOLA L'APPEND-ONLY. L'append-only d'aquesta taula prohibeix
    # que una fila ja escrita CANVIÏ de sentit: un `UPDATE` que reescrigui valor_anterior,
    # valor_nou o el context seria reescriure la història. Un `AddField` amb default de
    # columna és DDL, no DML: cap fila queda reescrita semànticament. Les 100% de files
    # històriques parlen, de fet i sense excepció, de la capa exterior —era l'única que el
    # sistema sabia mesurar—, o sigui que el default no els atribueix res que no diguessin
    # ja. Les overrides de talla no-base segueixen entrant amb `base_measurement=NULL`; això
    # no canvia.
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
                  "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).",
    )
    # C1-ins — la instància (declaració canònica a `BaseMeasurement.instancia`).
    #
    # MATEIX ARGUMENT QUE `capa`: afegir-la NO viola l'append-only. Un `AddField` és DDL, no
    # DML — cap fila queda reescrita semànticament —, i el 100% de la història d'aquesta
    # taula parla, de fet, de la instància única: era l'única que el sistema sabia escriure.
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )
    # SET-2/T2 — el garment (declaració canònica a `BaseMeasurement.garment`).
    # Aquesta taula és APPEND-ONLY i no té cap unicitat: si l'eix no neix aquí, el lector
    # no podrà dir mai de quina peça parlava un canvi ja registrat, i la pèrdua és
    # IRREVERSIBLE. Per això hi entra al mateix grup que la mesura, com capa i instància.
    garment = models.CharField(
        max_length=20, default='', db_index=True,
        help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). "
                  "'' és la peça mare, que és el Model mateix. Fins a la retirada de la "
                  "comporta només s'admet '' (comporta CHECK a BD).",
    )

    class Meta:
        verbose_name = 'Canvi de mesura'
        verbose_name_plural = 'Canvis de mesura'
        ordering = ['model', 'pom', 'created_at']
        constraints = [
            # C1/T4 — la comporta (v. `BaseMeasurement.Meta`). C4 la retira per migració.
            # ✅ C4/G1 (04/08) — retirada per la migració 0076 (v. la declaració canònica
            # a `BaseMeasurement`). Aquesta taula va al MATEIX grup que la mesura perquè el
            # signal F1 hi escriu dins de la mateixa transacció: separar-les deixaria una
            # alta de germana escrivint un apunt que la comporta del log rebutjaria.
            # C1-ins — la comporta d'instància (v. `BaseMeasurement.Meta`). C4-ins la retira.
            # ✅ C4/G1 (04/08) — retirada per la migració 0076 (v. la declaració canònica
            # a `BaseMeasurement`). Aquesta taula va al MATEIX grup que la mesura perquè el
            # signal F1 hi escriu dins de la mateixa transacció: separar-les deixaria una
            # alta de germana escrivint un apunt que la comporta del log rebutjaria.
            # SET-2/T2 — la comporta del garment (v. `BaseMeasurement.Meta`). Aquesta taula
            # va al MATEIX grup que la mesura, i pel mateix motiu de sempre: el signal F1 hi
            # escriu dins de la mateixa transacció, o sigui que separar-les deixaria una alta
            # de peça escrivint un apunt que la comporta del log rebutjaria.
            # ✅ SET-2/#12 (12/08) — RETIRADA per la migració `0084` (v. `BaseMeasurement`).
            # Va amb la mesura, com sempre: el signal F1 escriu l'apunt dins de la MATEIXA
            # transacció que la fila, o sigui que retirar-les per separat hauria deixat una
            # alta de peça legal escrivint un log il·legal.
        ]

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
    # C1 — la capa (declaració canònica a `BaseMeasurement.capa`). L'override sí que en porta,
    # a diferència de `ModelGradingRule`: un override és un VALOR mesurat en una talla concreta,
    # i el valor és de la capa que s'ha mesurat. La REGLA, en canvi, es comparteix entre capes
    # (§3c: «mateixos deltes») i per això no en té.
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
                  "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).",
    )
    # C1-ins — la instància (declaració canònica a `BaseMeasurement.instancia`). Mateix
    # argument que la capa: l'override és un VALOR mesurat, i la sisa dreta i l'esquerra es
    # poden corregir per separat en una talla. La REGLA segueix sense cap dels dos eixos.
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )
    # SET-2/T2 — el garment (declaració canònica a `BaseMeasurement.garment`).
    garment = models.CharField(
        max_length=20, default='', db_index=True,
        help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). "
                  "'' és la peça mare, que és el Model mateix. Fins a la retirada de la "
                  "comporta només s'admet '' (comporta CHECK a BD).",
    )

    class Meta:
        verbose_name = 'Override de grading (model)'
        verbose_name_plural = 'Overrides de grading (model)'
        # C1/T3 + C1-ins/T3 — la clau incorpora la CAPA i la INSTÀNCIA (v. `BaseMeasurement.Meta`).
        # SET-2/T2 — i el GARMENT (v. `BaseMeasurement.Meta`): mateixes columnes + una.
        unique_together = [('model', 'pom', 'size_label', 'capa', 'instancia', 'garment')]
        ordering = ['model', 'pom', 'size_label']
        constraints = [
            # SET-2/T2 — la comporta del garment (v. `BaseMeasurement.Meta`).
            # ✅ SET-2/#12 (12/08) — retirada per la migració `0084`. L'override és l'ajust
            # MANUAL d'una cel·la i la seva clau ja porta `garment`: pinar la M de la sisa
            # del top no pot moure la de la calceta.
            # C1/T4 — la comporta (v. `BaseMeasurement.Meta`). C4 la retira per migració.
            # ✅ C4/G3 (04/08) — retirada per la migració 0078. L'override és l'ajust MANUAL
            # d'una cel·la: pinar la talla M de la sisa dreta no pot moure l'esquerra, i
            # `escalat/ajustar-talla` ja hi escriu per la identitat sencera des de `959147a5`.
            # C1-ins — la comporta d'instància (v. `BaseMeasurement.Meta`). C4-ins la retira.
            # ✅ C4/G3 (04/08) — retirada per la migració 0078. L'override és l'ajust MANUAL
            # d'una cel·la: pinar la talla M de la sisa dreta no pot moure l'esquerra, i
            # `escalat/ajustar-talla` ja hi escriu per la identitat sencera des de `959147a5`.
        ]

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

    ⚠️ **SENSE `capa`, PER DECISIÓ DE DOMINI (C1 · §3c).** Aquesta és l'ÚNICA taula del cicle
    de mesura que la capa de C1 no travessa, i no és un oblit. Una regla de graduació és una
    llei d'INCREMENTS, no un valor: el folre d'un pit creix el mateix que l'exterior d'aquell
    pit —«mateixos deltes»— perquè la peça és la mateixa peça. Donar-li capa voldria dir
    demanar a algú que declari sis vegades el mateix delta i mantenir-les sincronitzades a mà.
    Els VALORS sí que en porten (`BaseMeasurement`, `GradedSpec`, `ModelGradingOverride`…):
    la regla és compartida, el resultat d'aplicar-la és per capa. Qui vulgui revisar-ho: és
    decisió d'arquitectura (Patró C), no una peça d'sprint.

    ⚠️ **I TAMPOC SENSE `instancia` (C1-ins), pel mateix motiu i amb la mateixa acta.**
    Decisió Montse: la sisa dreta i l'esquerra **gradúen igual**. Són dues mesures diferents
    —dos valors, dues fletxes al croquis, dues caselles a la fitxa— però una sola llei
    d'increments, com ho són l'exterior i el folre. Aquesta taula és, doncs, l'única del
    cicle que **no** travessa CAP dels dos eixos, i és a posta a les dues bandes. El pin que
    ho vigila: `test_instancia_comporta_cins.py` (columna absent a `information_schema`),
    germà del que ja hi ha per a `capa`. El mateix val per a `pom.GradingRule`.

    ── SET-2/T3 (2026-08-10) · **REOBERTURA CONSCIENT DE L'ACTA: LA CLAU CREIX AMB `garment`.**

    Això NO desmenteix res del que hi ha escrit a sobre; n'acota l'abast. L'acta de la Montse
    parla de **germanes DINS d'una mateixa peça** i segueix sent certa paraula per paraula: la
    sisa dreta i l'esquerra d'una mateixa prenda gradúen igual, i el folre d'un pit creix el
    mateix que el seu exterior. El que l'acta no diu —perquè quan es va escriure un model era
    una sola prenda— és que **un top i una calceta hagin de graduar igual**.

    I no ho fan. Una peça pot tenir el seu propi `grading_rule_set` (D5): un top per talla
    alfa i una calceta per mesos són dues lleis d'increments que ni tan sols parlen el mateix
    idioma de talles. Amb la clau `('model','pom')`, dues peces que compartissin un POM no
    podien tenir regles distintes — i, abans d'arribar-hi, **la sembra petava**: el wipe era
    per MODEL i el `bulk_create` indexava per `pom_id` sol.

    LA DISTINCIÓ, EN UNA LÍNIA: `capa` i `instancia` són **eixos de germanor** (dues cares de
    la mateixa mesura → una sola llei); `garment` és una **frontera** (dues mesures de dues
    prendes → dues lleis possibles). Per això aquesta clau creix amb el tercer i no amb els
    dos primers. La col·lecció canònica dels eixos de germanor viu a
    `services_derivacio.EIXOS_DE_GERMANOR`, i és la que llegeix el pin.

    EL PIN, ARA, VIGILA EL PRINCIPI. Els dos que hi havia comprovaven `column_name = 'capa'` i
    `= 'instancia'` literalment: una columna nova hi passava sense fer-los vermells, i la
    diagnosi SET-2 ho va demostrar. Ara iteren `EIXOS_DE_GERMANOR`, o sigui que el dia que el
    sistema aprengui un tercer eix de germanor el pin el vigilarà sol.
    ⚠️ **`pom.GradingRule` NO es reobre i el seu pin es REFORÇA**: un ruleset és una llei
    REUTILITZABLE del catàleg, mai propietat d'un model, i per tant no pot portar cap eix de
    model —`garment` inclòs—. És la línia que separa el catàleg del model.
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
        # RETORN-1 — mateixa raó que a BaseMeasurement: la regla resident ve de l'altra casa,
        # i cap dels quatre valors anteriors ho sabia dir.
        ('FEDERAT', "Arribat de l'altra casa (federació)"),
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
    # TRAM F — MULTI-BREAK PER INTERVALS. Forma i llei IDÈNTIQUES a la germana del catàleg
    # (`pom.GradingRule.breaks`, on viu l'acta sencera): llista ordenada
    # `[{"inici","final","delta"}]`, etiquetes en convenció de MOTOR, extrems inclusius, màxim
    # `grading_regime.MAX_BREAKS`. Buit = la regla d'1 break dels camps de sobre.
    breaks = models.JSONField(null=True, blank=True)

    origen = models.CharField(max_length=20, default='CANONICAL', choices=ORIGEN_CHOICES)
    # ── M3 (2026-08-07) · LA TRAÇABILITAT: DE QUIN JOC VE AQUESTA FILA ────────────────────────
    # L'arrel del parany de la decisió 6.1. `origen` diu «algú hi ha tocat», NO «aquest valor és
    # seu»: els dos escriptors de pantalla estampen `MANUAL` encara que la regla sigui una còpia
    # literal de la del joc, i `origen_mgr_des_de_ruleset` també estampa `MANUAL` a tot el que
    # surt d'un `GradingRuleSet` sense classificar. Amb això, «autoria» i «còpia» es deien igual
    # i el wipe només podia INFERIR-HO mirant l'estat del joc ANTERIOR del model sencer.
    # Aquest camp ho deixa dit per FILA, i a la font: qui la materialitza sap d'on la treu.
    #
    #   informat  → la fila VE d'aquest joc (encara que després l'hagin editada a mà).
    #   NULL      → no ve de cap joc, o no se sap. Autoria de pantalla des de zero, federació
    #               (el joc d'origen viu a l'altra casa i el seu id aquí no vol dir res) i
    #               TOTES les files anteriors a M3: **no hi ha backfill, i és a posta** —
    #               d'on venien no es pot saber, i inventar-ho seria tornar a mentir.
    #
    # NO canvia cap política: 6.1 i M1 segueixen decidint com ahir. És senyal, no llei; la
    # política que el llegeixi vindrà quan hi hagi dades (v. `poms_manual_a_preservar`).
    #
    # db_constraint=False i SET_NULL pel mateix motiu que `pom` (sobre): 'pom' és app SHARED
    # (taula també a 'public') i aquest model és tenant-only. Esborrar un joc del catàleg no ha
    # d'endur-se la regla resident del model —el patrimoni és del model—, només el rastre d'on
    # va néixer.
    derivat_de_rule_set = models.ForeignKey(
        'pom.GradingRuleSet', on_delete=models.SET_NULL, null=True, blank=True,
        db_constraint=False, related_name='regles_residents_derivades',
        help_text="Joc del qual es va materialitzar aquesta fila. NULL = autoria de pantalla, "
                  "federació, o fila anterior a M3 (sense backfill: no es pot saber).",
    )
    actiu = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # ── SET-2/T3 — EL GARMENT, i és l'ÚNIC eix que aquesta taula travessa (D4).
    # L'argument sencer viu a l'acta de la classe: `capa` i `instancia` són eixos de GERMANOR
    # (dues cares de la mateixa mesura → una sola llei d'increments) i per això no hi entren;
    # `garment` és una FRONTERA (dues prendes → dues lleis possibles) i per això hi entra.
    garment = models.CharField(
        max_length=20, default='', db_index=True,
        help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). "
                  "'' és la peça mare, que és el Model mateix. Fins a la retirada de la "
                  "comporta només s'admet '' (comporta CHECK a BD).",
    )

    class Meta:
        verbose_name = 'Regla grading (model)'
        verbose_name_plural = 'Regles grading (model)'
        # SET-2/T3 — la clau creix amb el garment (D4). Mateixes columnes + una →
        # estrictament més permissiva, amb `garment` constant ('') a totes les files.
        unique_together = [('model', 'pom', 'garment')]
        constraints = [
            # SET-2/T3 — la comporta, amb el mateix argument que les sis de T2 (v.
            # `BaseMeasurement.Meta`) i tancant una finestra que aquí és MÉS estreta i més
            # perillosa: `_load_grading_rules` indexa `{r.pom_id: r}` (`pom/services.py:749`),
            # un escalar SENSE cap eix. Amb dues peces que comparteixin un POM, la segona
            # regla no petaria: **sobreescriuria la primera en memòria** i el motor graduaria
            # tota una peça amb la llei de l'altra, sense un sol log. T4 és qui ensenya al
            # motor a distingir-les; fins llavors, aquí no hi pot haver cap '02'.
            # ✅ SET-2/#12 (12/08) — RETIRADA per la migració `0084`. La condició que la
            # comporta posava per escrit ja es compleix: `_load_grading_rules_per_garment`
            # (`pom/services.py:820`) indexa per `(pom_id, garment)` des de T4 —verificat, no
            # assumit—, o sigui que dues peces que comparteixin un POM
            # ja no s'aixafen en memòria. Aquesta és la comporta de T3 —la més estreta i la
            # més perillosa de les set— i cau amb les altres sis, no abans.
        ]

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
    # SET-1 · A3 — l'albarà ancora a UN Model **o** a UN GarmentSet, mai a tots dos ni a cap
    # (XOR sota, mateix patró que `FittingSession` a fitting/models.py:293-301). `model` passa a
    # nullable NOMÉS per fer-hi lloc: un albarà de conjunt no té model. La unicitat es conserva a
    # les dues bandes — `garment_set` és OneToOne com ho és `model` — perquè la decisió 2 diu
    # SET = 1 mèrit, i una FK plana deixaria escriure'n tres.
    model = models.OneToOneField(
        'models_app.Model', on_delete=models.CASCADE, related_name='consumption_record',
        null=True, blank=True,
    )
    garment_set = models.OneToOneField(
        'models_app.GarmentSet', on_delete=models.CASCADE, related_name='consumption_record',
        null=True, blank=True,
    )
    code_snapshot = models.CharField(max_length=40)            # snapshot de codi_intern
    name_snapshot = models.CharField(max_length=200, blank=True, default='')  # snapshot de nom_prenda
    period = models.CharField(max_length=7)                    # 'YYYY-MM'
    opaque_ref = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    merited_at = models.DateTimeField()                        # set explícit pel servei (4.2)

    class Meta:
        ordering = ['-merited_at']
        constraints = [
            models.CheckConstraint(
                name='consumptionrecord_model_xor_set',
                condition=(
                    models.Q(model__isnull=False, garment_set__isnull=True) |
                    models.Q(model__isnull=True, garment_set__isnull=False)
                ),
            ),
        ]

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
    # C1 — la capa (declaració canònica a `models_app.BaseMeasurement.capa`).
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
                  "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).",
    )
    # C1-ins — la instància (declaració canònica a `models_app.BaseMeasurement.instancia`).
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )
    # SET-2/T2 — el garment (declaració canònica a `BaseMeasurement.garment`).
    garment = models.CharField(
        max_length=20, default='', db_index=True,
        help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). "
                  "'' és la peça mare, que és el Model mateix. Fins a la retirada de la "
                  "comporta només s'admet '' (comporta CHECK a BD).",
    )

    class Meta:
        verbose_name = 'Línia de validació de talla'
        verbose_name_plural = 'Línies de validació de talla'
        ordering = ['size_check', 'pom']
        # C1/T3 + C1-ins/T3 — la clau incorpora la CAPA i la INSTÀNCIA (v. `BaseMeasurement.Meta`).
        # SET-2/T2 — i el GARMENT (v. `BaseMeasurement.Meta`): mateixes columnes + una.
        unique_together = [('size_check', 'pom', 'capa', 'instancia', 'garment')]
        constraints = [
            # SET-2/T2 — la comporta del garment (v. `BaseMeasurement.Meta`). El SizeCheck
            # segueix penjant del MODEL i sense eix (D6): mesurar una prenda és mesurar tot
            # el model, i el veredicte es compta per FILA sobre el model sencer. L'eix és de
            # la LÍNIA, que és la presa, no del check.
            # ✅ SET-2/#12 (12/08) — retirada per la migració `0084`. El SizeCheck segueix
            # penjant del MODEL i sense eix (D6): el que s'obre és la LÍNIA, que és la presa,
            # i pot dir de quina prenda parla.
            # C1/T4 — la comporta (v. `BaseMeasurement.Meta`). C4 la retira per migració.
            # ✅ C4/G2 (04/08) — retirada per la migració 0077. La línia de check és una
            # PRESA: la modista mesura la sisa dreta i l'esquerra per separat, i el veredicte
            # de tolerància de cadascuna es jutja amb la SEVA. Amb la comporta viva i les
            # germanes ja creades, obrir un Size Check petava amb `IntegrityError` —
            # `_materialize_lines` sembra una línia per mesura amb els seus eixos.
            # C1-ins — la comporta d'instància (v. `BaseMeasurement.Meta`). C4-ins la retira.
            # ✅ C4/G2 (04/08) — retirada per la migració 0077. La línia de check és una
            # PRESA: la modista mesura la sisa dreta i l'esquerra per separat, i el veredicte
            # de tolerància de cadascuna es jutja amb la SEVA. Amb la comporta viva i les
            # germanes ja creades, obrir un Size Check petava amb `IntegrityError` —
            # `_materialize_lines` sembra una línia per mesura amb els seus eixos.
        ]

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
        ('proposta_cotes', 'Proposta de cotes (IA visió · F3)'),
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
    # Vision F3 (proposta de cotes): recompte de la proposta perquè el mesurament d'ús no sigui
    # només tokens. Null als camins que no proposen (extracció/cribratge): no és una fila que hi
    # falti, és una dimensió que no aplica. Unifiquem al ledger d'AIUsage en comptes d'una taula
    # nova (llei "tot usage es loggeja" en UN sol lloc).
    n_proposades = models.IntegerField(null=True, blank=True, help_text="F3: cotes proposades en aquesta crida")
    n_skip = models.IntegerField(null=True, blank=True, help_text="F3: POMs omesos (la IA no ho ha vist clar)")
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


class POMPlacement(models.Model):
    """Precedent de COL·LOCACIÓ d'una cota POM sobre un sketch de CATÀLEG (F2).

    La col·locació viu al CATÀLEG (ItemFitxer), no al model: una sola veritat que els
    documents nascuts de l'item hereten via `ModelFitxer.derivat_de_item` (D1). Els extrems
    estan NORMALITZATS 0..1 respecte de la BOUNDING BOX DE L'OBJECTE SKETCH que la cota
    anota — NO de la pàgina ni de la silueta.

    ⚠️ bbox-d'objecte ≠ silueta: els marges buits dins una imatge (ràster sobretot) poden
    desviar la col·locació respecte del contorn real de la peça. Acceptat a v1 i traçat per
    `source_kind` (mai jerarquia; només qualitat de l'origen).

    NOMÉS és un precedent geomètric: MAI escriu cap valor de mesura (frontera G1). El vincle
    al POM és de LECTURA (PROTECT, com BaseMeasurement/PatternPOM); esborrar un POM
    referenciat dona 409, no arrossega la col·locació.
    """
    SOURCE_VECTOR = 'vector'
    SOURCE_RASTER = 'raster'
    SOURCE_KIND_CHOICES = [(SOURCE_VECTOR, 'Vector'), (SOURCE_RASTER, 'Ràster')]

    # CASCADE: el precedent és del fitxer de catàleg; si el sketch d'origen desapareix, els
    # seus precedents no tenen sentit. (D1: la casa del precedent és l'ItemFitxer.)
    item_fitxer = models.ForeignKey(
        ItemFitxer, on_delete=models.CASCADE, related_name='pom_placements')
    pom = models.ForeignKey(
        'pom.POMMaster', on_delete=models.PROTECT, related_name='placements')
    # Slug de vista dins la pàgina: canònics 'front'/'back'/'detail', sufix lliure
    # ('detail-coll'). NO és un enum tancat (D4): el vocabulari de vistes el fixa el producte.
    view_slot = models.SlugField(max_length=40)
    # Extrems A→B de la cota, normalitzats 0..1 sobre la bbox de l'objecte sketch.
    x1 = models.FloatField()
    y1 = models.FloatField()
    x2 = models.FloatField()
    y2 = models.FloatField()
    # Offset del centre de l'etiqueta respecte del punt mig del segment, normalitzat sobre les
    # dimensions de la bbox (captura un arrossegament manual del contenidor vermell; 0,0 = default).
    label_dx = models.FloatField(default=0)
    label_dy = models.FloatField(default=0)
    # Traça de qualitat de l'origen (mai jerarquia): 'vector' és exacte; 'raster' depèn de la
    # bbox de la imatge (v. avís bbox≠silueta).
    source_kind = models.CharField(
        max_length=8, choices=SOURCE_KIND_CHOICES, default=SOURCE_VECTOR)
    creat_per = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pom_placements_creats')
    creat_el = models.DateTimeField(auto_now_add=True)
    actualitzat_el = models.DateTimeField(auto_now=True)
    # C1 — la capa (declaració canònica a `models_app.BaseMeasurement.capa`). Una cota del
    # folre i una cota de l'exterior poden voler dos traços diferents sobre el mateix sketch.
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
                  "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).",
    )
    # C1-ins — la instància (declaració canònica a `models_app.BaseMeasurement.instancia`).
    # És l'eix que la cota necessita més literalment de tots: la sisa dreta i l'esquerra
    # s'assenyalen amb DUES fletxes en llocs diferents del mateix croquis.
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )

    class Meta:
        verbose_name = 'Col·locació de cota POM (precedent)'
        verbose_name_plural = 'Col·locacions de cota POM (precedent)'
        constraints = [
            # C1/T3 — la clau incorpora la CAPA (v. `BaseMeasurement.Meta`). El nom canvia
            # amb els camps a posta: un constraint que digui `_item_pom_view` i en guardi
            # quatre menteix a qui llegeixi l'esquema. Cap consumidor el referencia pel nom.
            # C1-ins/T3 hi afegeix la INSTÀNCIA, i el nom torna a créixer amb els camps pel
            # mateix motiu: dues cotes del mateix POM al mateix slot són justament el cas
            # que aquesta taula ha de saber guardar (la sisa dreta i l'esquerra
            # s'assenyalen amb dues fletxes al mateix croquis).
            models.UniqueConstraint(
                fields=['item_fitxer', 'pom', 'view_slot', 'capa', 'instancia'],
                name='uniq_pomplacement_item_pom_view_capa_instancia'),
            # C1/T4 — la comporta (v. `BaseMeasurement.Meta`). C4 la retira per migració.
            # ✅ C4/G3 (04/08) — retirada per la migració 0078. La col·locació és on la mesura
            # es lliga al CROQUIS, i és el punt on «dues cares, dues línies» es veurà de debò:
            # la sisa dreta i l'esquerra són dues cotes al dibuix, no una.
            # 🚩 La decisió de producte sobre la col·locació automàtica (una cota o dues per a
            # un POM amb germanes) segueix OBERTA — v. el commit `b56b2dfb`. Retirar la
            # comporta no la pren: la deixa possible.
            # C1-ins — la comporta d'instància (v. `BaseMeasurement.Meta`). C4-ins la retira.
            # ✅ C4/G3 (04/08) — retirada per la migració 0078. La col·locació és on la mesura
            # es lliga al CROQUIS, i és el punt on «dues cares, dues línies» es veurà de debò:
            # la sisa dreta i l'esquerra són dues cotes al dibuix, no una.
            # 🚩 La decisió de producte sobre la col·locació automàtica (una cota o dues per a
            # un POM amb germanes) segueix OBERTA — v. el commit `b56b2dfb`. Retirar la
            # comporta no la pren: la deixa possible.
        ]
        indexes = [
            models.Index(fields=['item_fitxer', 'view_slot'],
                         name='idx_pomplacement_item_view'),
        ]

    def __str__(self):
        return f'{self.item_fitxer_id} · POM {self.pom_id} @ {self.view_slot}'


class ModelGarment(models.Model):
    """UNA PEÇA DINS D'UN MODEL — l'entitat que D5 pressuposava i que SET-2/T2 no va crear.

    ── QUÈ ÉS, I QUÈ NO ÉS ────────────────────────────────────────────────────────────
    Un model pot ser més d'una prenda: un pijama té jaqueta i pantaló, i cadascuna té les
    seves mesures, la seva graduació i potser fins i tot la seva escala de talles (un top
    per talla alfa i una calceta per mesos són dues lleis d'increments que ni parlen el
    mateix idioma). El `garment` que les sis taules de mesura porten des de T2 és el CODI
    d'una d'aquestes peces; aquesta taula és on aquell codi finalment existeix.

    ⚠️ NO CONFONDRE AMB `GarmentSet`, i el paranys és que en llenguatge de domini totes dues
    són «peces». Són dues ALÇADES distintes:
      · `GarmentSet.peces` → els MODELS d'un producte comercial (un twin set = 2 models
        independents, cadascun amb la seva fitxa).
      · `ModelGarment` → les prendes DINS d'un sol model (un pijama = 1 model, 2 peces, 1
        fitxa).
    Per això el `related_name` d'aquí és `garments` i no `peces`: dos atributs amb el mateix
    nom a dues alçades diferents és la mena de coincidència que fabrica el bug que ningú no
    veu. El rètol de pantalla sí que dirà «peces»; l'atribut, no.

    ── D3 · LA MARE NO TÉ FILA, I ÉS DELIBERAT ────────────────────────────────────────
    El `garment=''` de les taules de mesura és la PEÇA MARE, i la peça mare **és el model
    mateix**: el seu run, la seva talla base i el seu joc de graduació ja viuen als camps de
    `Model`. Materialitzar-li una fila aquí duplicaria la font de veritat i obriria la
    pregunta «quin dels dos mana» a cada lectura. Per això hi ha una comporta CHECK que
    prohibeix `codi=''`: no és una validació de formulari, és la llei D3 escrita a Postgres.

    ── D5 · ELS OVERRIDES SÓN NULLABLES, I NULL VOL DIR «HERETA» ──────────────────────
    Els quatre camps heretables neixen `NULL`. NULL **no és** «buit» ni «cap»: és «pregunta-ho
    al model». Una peça acabada de crear no ha de re-declarar res per començar a funcionar, i
    canviar el run del model el canvia a totes les peces que no l'hagin sobreescrit.

    🔑 La resolució viu en UN SOL PUNT —`services_garment.valor_efectiu`— i enlloc més. És la
    raó per la qual es va revertir `7cc133b5`: una vora que serveixi el valor CRU al costat
    d'una altra que serveixi el RESOLT són dos orígens per al mateix camp, i acaben divergint.
    Qui necessiti el valor efectiu, que passi per allà.

    ── EL QUE AQUESTA TAULA NO PORTA, I PER QUÈ ───────────────────────────────────────
    `garment_type_item` NO hi és. El brief el demanava «nullable i sense cap lector», i un
    camp sense lector és exactament la bastida que aquest sprint ha après a no construir: la
    clau `garment` de `base-measurements/` es va revertir el 10/08 amb aquest argument literal
    («bastida sense funció; barata de treure ara i cara de treure després»). A més, la decisió
    de domini és que **el GTI no baixa a la peça**, o sigui que la columna codificaria una
    capacitat que el domini nega. Censat: cap dels lectors actuals de `garment_type_item`
    (`patterns/views.py`, `patterns/services.py`, `patterns/serializers.py`) pregunta per una
    peça — tots resolen la propietat d'un `PatternFile`, que penja d'un model O d'un item.
    Si algun dia el GTI ha de baixar, és una migració d'una línia i una decisió humana.
    """

    #: Els camps que una peça pot sobreescriure. Font única: el resolutor, el serializer i
    #: les proves en surten tots d'aquí, de manera que afegir-ne un és un sol canvi.
    CAMPS_HERETABLES = ('size_system', 'grading_rule_set', 'size_run_model', 'base_size_label')

    model = models.ForeignKey(
        'models_app.Model',
        on_delete=models.CASCADE,
        related_name='garments',
        help_text='El model del qual aquesta peça forma part.',
    )
    codi = models.CharField(
        max_length=20,
        help_text="Codi de la peça dins del model ('02', '03'…). Mai '': la peça mare és el "
                  "model mateix i no té fila (D3).",
    )
    nom = models.CharField(
        max_length=200, blank=True, default='',
        help_text='Bateig del tècnic («Pantaló», «Caputxa»). Buit = encara sense batejar.',
    )
    ordre = models.PositiveSmallIntegerField(
        default=0, help_text='Ordre de presentació dins del model.')

    # ── Overrides (D5). NULL = hereta del model. ──────────────────────────────────────
    size_system = models.ForeignKey(
        'pom.SizeSystem', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='garments_override',
    )
    grading_rule_set = models.ForeignKey(
        'pom.GradingRuleSet', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='garments_override',
    )
    size_run_model = models.CharField(max_length=200, null=True, blank=True)
    base_size_label = models.CharField(max_length=20, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Peça de model'
        verbose_name_plural = 'Peces de model'
        ordering = ['model_id', 'ordre', 'codi']
        unique_together = [('model', 'codi')]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(codi=''),
                name='models_app_modelgarment_codi_no_buit',
            ),
        ]

    def __str__(self):
        return f'{self.model_id} · peça {self.codi}{f" ({self.nom})" if self.nom else ""}'
