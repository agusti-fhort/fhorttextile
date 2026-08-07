from django.conf import settings
from django.db import models


# ─────────────────────────────────────────────────────────────
# FHORT global catalog ('public' schema)
# ─────────────────────────────────────────────────────────────

class POMGlobal(models.Model):
    UNITAT_CHOICES = [('cm', 'cm'), ('inch', 'inch')]
    SCOPE_CHOICES = [
        ('HALF', 'Half'), ('FULL', 'Full'), ('CALCULATED', 'Calculated'),
    ]
    ORIENTATION_CHOICES = [
        ('HORIZONTAL', 'Horizontal'), ('VERTICAL', 'Vertical'),
        ('CIRCUMFERENCE', 'Circumference'), ('CURVED', 'Curved'),
        ('DIAGONAL', 'Diagonal'),
    ]
    STATE_CHOICES = [
        ('FLAT', 'Flat'), ('RELAXED', 'Relaxed'),
        ('STRETCHED', 'Stretched'), ('ON_BODY', 'On body'),
    ]
    LINE_CHOICES = [
        ('STRAIGHT', 'Straight'), ('CURVED', 'Curved'),
        ('ALONG CURVE', 'Along curve'), ('ANGLED', 'Angled'),
    ]
    BODY_SECTION_CHOICES = [
        ('FRONT', 'Front'), ('BACK', 'Back'), ('SIDE', 'Side'),
        ('SLEEVE', 'Sleeve'), ('BOTH', 'Both'), ('HEAD', 'Head'),
    ]

    codi = models.CharField(max_length=80, unique=True)
    nom_en = models.CharField(max_length=200)
    nom_ca = models.CharField(max_length=200)
    nom_es = models.CharField(max_length=200, blank=True)
    categoria = models.CharField(max_length=40)
    descripcio_en = models.TextField(blank=True)
    descripcio_ca = models.TextField(blank=True)
    unitat = models.CharField(max_length=4, choices=UNITAT_CHOICES, default='cm')
    actiu = models.BooleanField(default=True)

    # Sprint S12-A — extended catalog (detailed How To Measure)
    abbreviation    = models.CharField(max_length=40, blank=True)
    start_point     = models.CharField(max_length=120, blank=True)
    end_point       = models.CharField(max_length=120, blank=True)
    reference_point = models.CharField(max_length=200, blank=True)
    scope           = models.CharField(max_length=20, choices=SCOPE_CHOICES, blank=True)
    orientation     = models.CharField(max_length=20, choices=ORIENTATION_CHOICES, blank=True)
    state           = models.CharField(max_length=20, choices=STATE_CHOICES, blank=True)
    line            = models.CharField(max_length=20, choices=LINE_CHOICES, blank=True)
    body_section    = models.CharField(max_length=20, choices=BODY_SECTION_CHOICES, blank=True)
    is_key          = models.BooleanField(default=False)
    tol_prod_cm     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tol_samp_cm     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    applies_woven   = models.BooleanField(default=True)
    applies_knit    = models.BooleanField(default=True)
    applies_swim    = models.BooleanField(default=False)
    notes           = models.TextField(blank=True)
    iso_ref         = models.CharField(max_length=60, blank=True)
    # End Sprint S12-A

    # Sprint S1 — ISO 8559-1 linkage
    body_measure_iso = models.ForeignKey(
        'BodyMeasurementISO',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='poms_globals',
        help_text="Mesura corporal ISO 8559-1 equivalent"
    )
    # End Sprint S1

    class Meta:
        verbose_name = 'POM global'
        verbose_name_plural = 'POMs globals'

    def __str__(self):
        return f'{self.codi} · {self.nom_en}'


class GarmentTypeGlobal(models.Model):
    codi = models.CharField(max_length=80, unique=True)
    nom_en = models.CharField(max_length=200)
    nom_ca = models.CharField(max_length=200)
    nom_es = models.CharField(max_length=200)
    grup = models.CharField(max_length=40)
    actiu = models.BooleanField(default=True)
    # Sprint S13-A
    is_system = models.BooleanField(default=True,
        help_text="True = catàleg canònic, no esborrable")
    display_order = models.PositiveIntegerField(default=0)
    # Pas previ 5 — descripció de família (construcció)
    descripcio = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Tipus garment global'
        verbose_name_plural = 'Tipus garment globals'
        ordering = ['grup', 'display_order', 'codi']

    def __str__(self):
        return f'{self.codi} · {self.nom_en}'


class PatternPieceRole(models.Model):
    """Rol CANÒNIC d'una peça de patró: què és aquesta peça, no com se'n diu.

    Viu aquí i no a `patterns/` per una raó d'infraestructura, no de gust: `fhort.pom` és
    l'única app que és a SHARED **i** a TENANT alhora, o sigui l'única on una taula pot
    existir a `public` i replicar-se a cada tenant. `fhort.patterns` és tenant-only, i un
    catàleg de sistema declarat allà no podria arribar mai al schema públic.

    **CATÀLEG DE SISTEMA. El tenant PROPOSA; la promoció és un acte separat (D-1).**
    Un rol amb `is_system=True` és propietat de la casa i no s'esborra. Un tenant que es
    troba una peça que el catàleg no sap anomenar pot crear el seu rol —`is_system=False`,
    `pendent_revisio=True`, `origen=MANUAL` o `IMPORT`—, i aquell rol serveix per treballar
    des del primer dia; convertir-lo en canònic és una decisió humana, amb el seu gate, i
    mai un efecte secundari d'una importació. És la mateixa llei que ja governa
    `POMMaster.pom_global=None` i `CustomerPOMAlias.pendent_revisio`.

    **LA SEMBRA NO ESBORRA MAI.** `update_or_create` per `slug`, cap `delete`, i el revers
    de tota migració de dades és un noop: revertir un esquema no ha de destruir el catàleg
    (mateix criteri que `0025_seed_canonical_task_types`).

    El `slug` és la clau estable —el que viatja entre tenants i entre versions d'un patró—;
    els noms són per als ulls i van en tres idiomes des del primer dia, com `POMGlobal`,
    perquè afegir-los després vol dir repassar files a mà.

    Un rol NO és la identitat d'una peça: hi ha camises amb tres vistes i pantalons amb
    dues traves. La identitat es completa amb lateralitat i ordinal, que viuen a la peça.
    """

    CLASSE_COS = 'cos'
    CLASSE_MANIGA = 'maniga'
    CLASSE_BANDA = 'banda'
    CLASSE_TIRA = 'tira'
    CLASSE_PANELL = 'panell'
    CLASSE_COMPLEMENT = 'complement'
    CLASSE_CHOICES = [
        (CLASSE_COS, 'Cos'),
        (CLASSE_MANIGA, 'Màniga'),
        (CLASSE_BANDA, 'Banda'),
        (CLASSE_TIRA, 'Tira'),
        (CLASSE_PANELL, 'Panell'),
        (CLASSE_COMPLEMENT, 'Complement'),
    ]

    ORIGEN_SEED = 'SEED'
    ORIGEN_MANUAL = 'MANUAL'
    ORIGEN_IMPORT = 'IMPORT'
    ORIGEN_CHOICES = [
        (ORIGEN_SEED, 'Sembra'),
        (ORIGEN_MANUAL, 'Manual'),
        (ORIGEN_IMPORT, 'Importació'),
    ]

    slug = models.SlugField(max_length=60, unique=True)
    nom_en = models.CharField(max_length=120)
    nom_ca = models.CharField(max_length=120)
    nom_es = models.CharField(max_length=120)
    classe = models.CharField(max_length=12, choices=CLASSE_CHOICES)
    #: Propietat de la casa: no s'esborra (mateix guard que `GarmentTypeGlobal.is_system`).
    is_system = models.BooleanField(default=False)
    #: Rol nascut al tenant i encara no promogut a canònic.
    pendent_revisio = models.BooleanField(default=False)
    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default=ORIGEN_MANUAL)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Rol de peça de patró'
        verbose_name_plural = 'Rols de peça de patró'
        ordering = ['display_order', 'slug']

    def __str__(self):
        return f'{self.slug} · {self.nom_ca or self.nom_en}'


class MeasurementLayer(models.Model):
    """CAPA d'una mesura: de QUINA matèria de la peça parla aquesta mesura.

    Un mateix POM es mesura més d'un cop sobre la mateixa peça segons la capa: el pit de
    l'exterior i el pit del folre no són el mateix valor, i avui el sistema no els sap
    distingir perquè la clau de mesura és `(model, pom)` i prou. Aquest catàleg és el
    vocabulari amb què s'anomenaran; la clau ampliada arriba a T3 i el permís d'usar-la
    més enllà d'`exterior`, a C4 (fins llavors mana la comporta CHECK de T4).

    **Viu aquí i no a `models_app` per la mateixa raó d'infraestructura que
    `PatternPieceRole`**: `fhort.pom` és l'única app que és a SHARED **i** a TENANT alhora,
    o sigui l'única on una taula pot existir a `public` i replicar-se a cada tenant. Les
    taules que hi faran referència viuen escampades entre `models_app`, `fitting` i `pom`
    (totes tenant-only excepte les del propi `pom`); un catàleg declarat a qualsevol
    d'elles no podria arribar mai al schema públic.

    **CATÀLEG DE SISTEMA. El tenant PROPOSA; la promoció és un acte separat (D-1).**
    Una capa amb `is_system=True` és propietat de la casa i no s'esborra. Un tenant que es
    troba una matèria que el catàleg no sap anomenar pot crear la seva capa —`is_system=False`,
    `pendent_revisio=True`, `origen=MANUAL` o `IMPORT`—, i aquella capa serveix per treballar
    des del primer dia; convertir-la en canònica és una decisió humana, amb el seu gate, i
    mai un efecte secundari d'una importació. És la mateixa llei que ja governa
    `PatternPieceRole`, `POMMaster.pom_global=None` i `CustomerPOMAlias.pendent_revisio`.

    **LA SEMBRA NO ESBORRA MAI.** `update_or_create` per `slug`, cap `delete`, i el revers
    de tota migració de dades és un noop: revertir un esquema no ha de destruir el catàleg.

    El `slug` és la clau estable —el que viatja entre tenants i el que les taules de mesura
    referencien, mai la PK (llei G9)—; els noms són per als ulls i van en tres idiomes des
    del primer dia, com `POMGlobal` i `PatternPieceRole`, perquè afegir-los després vol dir
    repassar files a mà.

    ⚠️ Els noms sembrats a `seed_measurement_layers` són PROVISIONALS, pendents de la
    nomenclatura definitiva de la Montse. Els `slug` són el contracte i no es toquen; els
    tres noms es poden reescriure amb una passada més de la sembra sense migrar cap fila.
    """

    ORIGEN_SEED = 'SEED'
    ORIGEN_MANUAL = 'MANUAL'
    ORIGEN_IMPORT = 'IMPORT'
    ORIGEN_CHOICES = [
        (ORIGEN_SEED, 'Sembra'),
        (ORIGEN_MANUAL, 'Manual'),
        (ORIGEN_IMPORT, 'Importació'),
    ]

    #: La capa per defecte de tot el sistema: el que fins avui era «la mesura», sense adjectiu.
    SLUG_DEFECTE = 'exterior'

    slug = models.SlugField(max_length=20, unique=True)
    nom_en = models.CharField(max_length=120)
    nom_ca = models.CharField(max_length=120)
    nom_es = models.CharField(max_length=120)
    #: Propietat de la casa: no s'esborra (mateix guard que `PatternPieceRole.is_system`).
    is_system = models.BooleanField(default=False)
    #: Capa nascuda al tenant i encara no promoguda a canònica.
    pendent_revisio = models.BooleanField(default=False)
    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default=ORIGEN_MANUAL)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Capa de mesura'
        verbose_name_plural = 'Capes de mesura'
        ordering = ['display_order', 'slug']

    def __str__(self):
        return f'{self.slug} · {self.nom_ca or self.nom_en}'


class MeasurementInstance(models.Model):
    """INSTÀNCIA d'una mesura: QUINA de les repeticions del mateix POM és aquesta (D-31.26).

    Bessona de `MeasurementLayer` i pel mateix motiu d'infraestructura (`fhort.pom` és
    l'única app que és a SHARED **i** a TENANT alhora), amb el mateix contracte: el `slug`
    és el que desen les columnes `instancia` de les taules de mesura —mai la PK, llei G9—
    i els tres noms són per als ulls.

    **NO ÉS UN CATÀLEG DE POMS.** El catàleg té UN POM per mesura; el MODEL diu quantes
    cares en té (D-31.19). Aquesta taula és el vocabulari amb què s'anomenen aquelles cares,
    no una llista de mesures noves: `left`/`right` no són dos POMs de sisa, són la mateixa
    sisa dita dues vegades.

    **DOS EIXOS, NO UN.** Una germana es distingeix per ON es mesura (POSICIÓ: la sisa
    esquerra, la cintura per dalt) o per COM (ESTAT: la goma relaxada, la goma estirada).
    Són ortogonals i es componen amb guió al slug que es desa (`'left-relaxed'`), tal com
    ja el desmunta `frontend/src/utils/capaInstancia.js`. Separar-los aquí és el que permet
    que el gest de crear una germana ofereixi les vuit posicions i els dos estats sense
    barrejar-los en una sola llista de deu.

    **EL SUFIX ÉS DE LA POSICIÓ, MAI DE L'ESTAT.** La instància AMPLIA la nomenclatura: el
    sistema PROPOSA `codi base + sufix` en crear la germana (B→BT, FS→FSCF), estil Brownie
    —concatenació directa, sense guió— i el patronista el pot editar, perquè el `nom_fitxa`
    és lliure. Els estats no componen sufix: fan servir el codi oficial del client si en té
    (B1 = «stretched waist width») o la descripció. Per això `sufix` és buit als dos estats
    i no és un oblit.

    **LA PROPOSTA NO ÉS L'OBLIGACIÓ.** `instancia_exigeix_nom` (invariant viva de BD) demana
    que tota germana porti nom; qui el posa és el patronista. Aquesta taula li dona el
    vocabulari i una proposta de codi, no li tria el nom.

    Mateixa llei de catàleg que la capa: **la sembra no esborra mai** (`update_or_create` per
    `slug`), `is_system=True` és propietat de la casa, i un tenant pot crear-se la seva
    instància (`is_system=False`, `pendent_revisio=True`) sense que la sembra la toqui.
    """

    ORIGEN_SEED = 'SEED'
    ORIGEN_MANUAL = 'MANUAL'
    ORIGEN_IMPORT = 'IMPORT'
    ORIGEN_CHOICES = [
        (ORIGEN_SEED, 'Sembra'),
        (ORIGEN_MANUAL, 'Manual'),
        (ORIGEN_IMPORT, 'Importació'),
    ]

    #: ON es mesura (lateralitat, vora, costura de referència).
    EIX_POSICIO = 'POSICIO'
    #: COM es mesura (amb tensió o sense).
    EIX_ESTAT = 'ESTAT'
    EIX_CHOICES = [
        (EIX_POSICIO, 'Posició'),
        (EIX_ESTAT, 'Estat'),
    ]
    #: EL NOM DE L'EIX, trilingüe, per a qui n'ha de pintar una COLUMNA (D-31.18: la taula de
    #: mesures té un grup de columnes per eix). Viu aquí, al costat de `EIX_CHOICES`, perquè
    #: l'eix es DEFINEIX aquí i no té fila pròpia a cap taula: és el discriminant de les que hi
    #: ha. Que el front se'ls escrigui seria el segon lloc que sap quins eixos hi ha, i el dia
    #: que se n'afegís un tercer la columna nova sortiria sense nom.
    EIX_NOMS = {
        EIX_POSICIO: {'nom_en': 'Position', 'nom_ca': 'Posició', 'nom_es': 'Posición'},
        EIX_ESTAT: {'nom_en': 'State', 'nom_ca': 'Estat', 'nom_es': 'Estado'},
    }

    #: La instància ÚNICA: cadena buida, no una fila d'aquesta taula. Una mesura que només
    #: es fa un cop no té res a qualificar (v. `sufixIdentitat`, que hi torna `''`).
    SLUG_UNICA = ''

    slug = models.SlugField(max_length=30, unique=True)
    nom_en = models.CharField(max_length=120)
    nom_ca = models.CharField(max_length=120)
    nom_es = models.CharField(max_length=120)
    eix = models.CharField(max_length=8, choices=EIX_CHOICES, db_index=True)
    #: Sufix que s'enganxa al codi base per PROPOSAR el codi de la germana (B→BT). Buit a
    #: l'eix ESTAT per decisió, i buit també a `waistband_seam`, que és un DATUM: es diu a la
    #: descripció, no al codi (full INSTANCIES, decisió Agus 05/08).
    sufix = models.CharField(max_length=4, blank=True, default='')
    #: Propietat de la casa: no s'esborra (mateix guard que `MeasurementLayer.is_system`).
    is_system = models.BooleanField(default=False)
    #: Instància nascuda al tenant i encara no promoguda a canònica.
    pendent_revisio = models.BooleanField(default=False)
    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default=ORIGEN_MANUAL)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Instància de mesura'
        verbose_name_plural = 'Instàncies de mesura'
        ordering = ['eix', 'display_order', 'slug']

    def __str__(self):
        return f'{self.slug} · {self.nom_ca or self.nom_en}'


class POMEstadisticaGlobal(models.Model):
    pom_global = models.ForeignKey(POMGlobal, on_delete=models.CASCADE, related_name='estadistiques_globals')
    garment_type_global = models.ForeignKey(GarmentTypeGlobal, on_delete=models.CASCADE, related_name='estadistiques_globals')
    n = models.PositiveIntegerField(default=0)
    mitjana = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    m2 = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    segment = models.CharField(max_length=20)
    talla_label = models.CharField(max_length=30)

    class Meta:
        verbose_name = 'Estadística POM global'
        verbose_name_plural = 'Estadístiques POM globals'
        unique_together = [('pom_global', 'garment_type_global', 'segment', 'talla_label')]

    def __str__(self):
        return f'{self.pom_global.codi} · {self.garment_type_global.codi} · {self.segment}/{self.talla_label}'


# ─────────────────────────────────────────────────────────────
# Per-tenant catalog (tenant schema)
# ─────────────────────────────────────────────────────────────

class POMCategory(models.Model):
    """POM categories (UPPER/LOWER/JK/CD/PL/...). Imported from master data."""

    codi = models.CharField(max_length=20, unique=True)
    nom_en = models.CharField(max_length=120, blank=True)
    nom_ca = models.CharField(max_length=120, blank=True)
    descripcio = models.TextField(blank=True)
    body_area = models.CharField(max_length=20, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Categoria POM'
        verbose_name_plural = 'Categories POM'
        ordering = ['display_order', 'codi']

    def __str__(self):
        return f'{self.codi} · {self.nom_ca or self.nom_en}'


class POMMaster(models.Model):
    pom_global = models.ForeignKey(
        POMGlobal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='masters',
    )
    categoria = models.ForeignKey(
        POMCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='poms',
    )
    codi_client = models.CharField(max_length=30)
    nom_client = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    actiu = models.BooleanField(default=True)

    # Sprint 5B.1: standard tolerance for this catalogue POM (asymmetric).
    # Copied onto BaseMeasurement.tolerancia_minus/plus when measurements are poured
    # into a model (copy-at-the-moment, like base_value_cm — not a live reference).
    tolerancia_default_minus = models.DecimalField(max_digits=5, decimal_places=2, default=0.6)
    tolerancia_default_plus = models.DecimalField(max_digits=5, decimal_places=2, default=0.6)
    pendent_revisio = models.BooleanField(
        default=False,
        verbose_name='Pendent de revisió',
        help_text="POM creat automàticament des d'importació. Requereix revisió de la patronista.",
    )
    origen_import = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Origen importació',
        help_text="Referència del model/fitxa des d'on s'ha creat aquest POM",
    )

    class Meta:
        verbose_name = 'POM (tenant)'
        verbose_name_plural = 'POMs (tenant)'

    def __str__(self):
        return f'{self.codi_client} · {self.nom_client}'

    # ── Alias properties for the sprint3/4 code ────────────────────────────
    # Resolve TECH_DEBT.md #2. Read-only — they do not work in the ORM (.filter/order_by).
    # For the ORM, use the natural FKs: pom__categoria__display_order, pom__pom_global__nom_ca.
    @property
    def pom_code(self):
        return self.codi_client or (self.pom_global.codi if self.pom_global_id else '')

    @property
    def name_cat(self):
        if self.pom_global_id and self.pom_global.nom_ca:
            return self.pom_global.nom_ca
        return self.nom_client

    @property
    def name_en(self):
        if self.pom_global_id and self.pom_global.nom_en:
            return self.pom_global.nom_en
        return self.nom_client

    @property
    def display_order(self):
        return self.categoria.display_order if self.categoria_id else 999

    @property
    def is_key_measure(self):
        # We have no equivalent field in the current schema. If we needed to
        # distinguish "key measures", add an explicit BooleanField to the model (migration).
        return False


class POMEstadisticaTenant(models.Model):
    pom = models.ForeignKey(POMMaster, on_delete=models.CASCADE, related_name='estadistiques')
    garment_type = models.CharField(max_length=80)
    talla_label = models.CharField(max_length=30)
    n = models.PositiveIntegerField(default=0)
    mitjana = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    m2 = models.DecimalField(max_digits=16, decimal_places=4, default=0)

    class Meta:
        verbose_name = 'Estadística POM tenant'
        verbose_name_plural = 'Estadístiques POM tenant'
        unique_together = [('pom', 'garment_type', 'talla_label')]

    def __str__(self):
        return f'{self.pom.codi_client} · {self.garment_type}/{self.talla_label}'


class CustomerPOMAlias(models.Model):
    """Àlies de NOMENCLATURA per client (N1, DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08): separa
    "com anomena un client una mesura" (client_code/client_description) del catàleg canònic
    (POMMaster). Un client pot tenir DIVERSOS codis per al mateix POM (p.ex. Losan H.11 sleeve
    opening vs H.16 cuff opening) → unicitat (customer, client_code), NO (customer, pom).
    El matcher el consumeix com a estratègia (a) prioritària de find_pom_master (N3 fet,
    models_app/extraction_views.py:543)."""
    # `MODEL` (06/08) — l'àlies neix perquè un model necessitava una mesura que el catàleg del
    # client no tenia, i algú la va crear des del cercador de Definició POM («Crear POM propi del
    # model»). NO és un àlies de menys categoria: entra a l'espai de nomenclatura del client com
    # qualsevol altre, la validació de col·lisió el veu, i un altre model del mateix client el pot
    # reutilitzar pel cercador. Això és coneixement del client acumulant-se, que és el que ha de
    # passar (decisió d'Agus, 06/08).
    #
    # El que marca és la PROVINENÇA: d'on va sortir aquest codi. Serveix per saber què s'ha
    # d'ensenyar al diccionari com a pendent de consolidar i què ve d'un document oficial.
    ORIGEN_CHOICES = [
        ('IMPORT', 'Import'), ('MANUAL', 'Manual'), ('MIGRACIO', 'Migració'),
        ('DICCIONARI', 'Diccionari'), ('MODEL', 'Nascut d\'un model'),
    ]
    # db_constraint=False: `pom` és SHARED+TENANT però `tasks.Customer` és tenant-only → la FK
    # creua schemas (mateix patró que GarmentPOMMap). PROTECT a nivell ORM, sense constraint de BD.
    customer = models.ForeignKey(
        'tasks.Customer', on_delete=models.PROTECT, related_name='pom_aliases',
        db_constraint=False)
    # NULLABLE (QA-S8-R1): un àlies SENSE pom és vocabulari del client encara PENDENT DE MAPAR.
    # És un estat legítim del domini, no una dada incompleta: el client anomena una mesura i
    # encara no sabem a quin POM canònic correspon (o el mapatge que teníem era FALS i s'ha
    # desvinculat). El matcher no els mira (find_pom_master filtra `pom__isnull=False`): un
    # àlies sense destí no pot vincular res. (Migració 0037.)
    pom = models.ForeignKey(
        POMMaster, on_delete=models.CASCADE, related_name='client_aliases',
        null=True, blank=True)
    client_code = models.CharField(max_length=60)
    # OBSOLET (TODO): camp de descripció únic heretat. Substituït per description_en +
    # description_local. Es manté la columna (migració 0035 hi va bolcar el contingut propi
    # cap a description_en); no s'esborra per no perdre històric. No escriure-hi de nou.
    client_description = models.CharField(max_length=200, blank=True, default='')
    # Diccionari del client (carregat al setup): descripció canònica internacional (EN) +
    # descripció en l'idioma local de l'empresa. Ambdues alimenten find_pom_master com a
    # senyal de matching addicional. `language` = ISO 639-1 del camp local.
    description_en = models.CharField(max_length=200, blank=True, default='')
    description_local = models.CharField(max_length=200, blank=True, default='')
    language = models.CharField(max_length=2, blank=True, default='')
    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default='MANUAL')
    pendent_revisio = models.BooleanField(default=False)
    # F3/D-31.26 — ÀLIES D'INSTÀNCIA: aquest codi del client no és una mesura pròpia, és una
    # REPETICIÓ de la del `pom`. El doc oficial de Brownie declara A2/A3 variants de la mateixa
    # fila que A: no són tres amplades de pit, són l'amplada de pit dita tres vegades.
    #
    # Sense aquesta marca els dos casos són indistingibles per al matcher —un codi que resol a
    # un POM— i acabaria vinculant A2 al pit i donant la feina per feta. El que ha de passar és
    # l'altra cosa: resol el POM i DEIXA LA FILA A «assignar instància», perquè QUINA cara és
    # (la 2a? la de l'esquerra? l'estirada?) no ho diu el codi, ho diu qui mesura. Auto-triar-la
    # seria inventar-se una dada que el document no porta.
    #
    # ⚠️ AQUÍ NOMÉS HI HA LA DADA, NO LA REGLA. El comportament del matcher és el full MATCHER i
    # s'implementa al seu lloc; aquesta columna és el que llegirà quan hi sigui.
    #
    # Deliberadament NO desa QUINA instància és (ni l'ordinal «2a/3a» ni l'eix). Desar-ho seria
    # exactament l'auto-tria que la regla prohibeix, i el `nom_fitxa` del model ja és el lloc on
    # viu la resposta un cop una persona l'ha donada.
    es_instancia = models.BooleanField(
        default=False,
        help_text="Aquest codi és una REPETICIÓ del POM apuntat, no una mesura pròpia. "
                  "El matcher hi resol el POM però deixa la fila a «assignar instància».")
    creat_at = models.DateTimeField(auto_now_add=True)
    actualitzat_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Àlies POM de client'
        verbose_name_plural = 'Àlies POM de client'
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'client_code'], name='uniq_customer_client_code'),
        ]
        indexes = [
            models.Index(fields=['customer', 'client_code'], name='idx_customer_client_code'),
        ]

    def __str__(self):
        desti = self.pom.codi_client if self.pom_id else '(pendent de mapar)'
        return f'{self.customer.codi}:{self.client_code} → {desti}'


class SizeSystem(models.Model):
    codi = models.CharField(max_length=60, unique=True)
    nom = models.CharField(max_length=120)
    descripcio = models.TextField(blank=True)
    actiu = models.BooleanField(default=True)



    # Sprint S1 → 0a: target FK migrat a M2M (harmonitza amb GradingRuleSet.targets).
    targets = models.ManyToManyField(
        'Target', blank=True,
        related_name='size_systems',
    )
    base_unit = models.CharField(
        max_length=20, blank=True,
        choices=[
            ('ALPHA','Alpha (XS/S/M/L...)'),
            ('NUMERIC_EU','Numeric EU (34/36/38...)'),
            ('NUMERIC_US','Numeric US (0/2/4...)'),
            ('CM_HEIGHT','CM Height (50/56/62...)'),
            ('MONTHS','Months (0M/3M/6M...)'),
            ('AGE_YEARS','Age Years (6Y/8Y...)'),
        ],
        help_text="Tipus de designacio de talles"
    )
    norma_ref = models.CharField(max_length=50, blank=True,
        help_text="Ex: ISO 8559-2, ASTM D5585")
    # Fi Sprint S1

    # Sprint Size Map Setup — derivació per client
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='derived_systems',
        verbose_name='Sistema pare',
    )
    customer_codi = models.CharField(
        max_length=3, blank=True, default='',
        verbose_name='Codi client',
    )

    # ── N1 (2026-08-06 nit) · EL RUN ES DESCRIU A SI MATEIX ────────────────────────────
    # Fins ara el run era una escala muda: qui deia per a qui servia era el `SizingProfile`
    # (la combinació target×família×construcció×fit). Això obligava a inventar-se un perfil
    # —i amb ell una graduació— per declarar que un run existeix per a un àmbit. Aquestes
    # etiquetes són del RUN i NOMÉS descriuen a qui s'assembla: cap camp de graduació, cap
    # FK a POMs, res que lligui capes.
    TIPUS_ESCALA_CHOICES = [
        ('ALPHA', 'Alpha (XS/S/M/L…)'),
        ('NUM', 'Numèrica (34/36/38…)'),
        ('MESOS', 'Mesos i edat (0M/3M · 2/4/6 anys)'),
        ('ALTURA', 'Alçada en cm (50/56/62…)'),
    ]
    tipus_escala = models.CharField(
        max_length=10, blank=True, default='',
        choices=TIPUS_ESCALA_CHOICES,
        verbose_name='Tipus d\'escala',
        help_text="Deduït de les etiquetes de talla. Buit = no deduïble sol.",
    )
    # Les tres capes que faltaven, amb el patró que la casa ja fa servir per a `targets`:
    # M2M al vocabulari, exposat i escrit per CODI (SlugRelatedField). 0..n per capa, i
    # **buit NO vol dir universal** — mateixa llei que `targets` (v. serializers.py).
    construccions = models.ManyToManyField(
        'ConstructionType', blank=True, related_name='size_systems',
        verbose_name='Construccions',
    )
    fits = models.ManyToManyField(
        'FitType', blank=True, related_name='size_systems',
        verbose_name='Fits',
    )
    # GRUP: el vocabulari surt de GARMENT TYPES (`GarmentGroup`), no de POM System
    # (decisió d'Agus, 2026-08-06 nit). El vocabulari alternatiu —`POMCategory`— descriu
    # àrees de cos, no famílies de peça, i no és font d'àmbit.
    grups = models.ManyToManyField(
        'GarmentGroup', blank=True, related_name='size_systems',
        verbose_name='Grups de peça',
    )
    # Eix client com a FK (`customer_codi` és el codi curt heretat i es manté intacte).
    # db_constraint=False + SET_NULL: mateix patró que `SizingProfile.customer`
    # (models.py:1521) — `pom` és SHARED+TENANT i `tasks.Customer` és tenant-only.
    customer = models.ForeignKey(
        'tasks.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, db_constraint=False,
        related_name='size_systems', verbose_name='Client',
    )

    class Meta:
        verbose_name = 'Sistema de talles'
        verbose_name_plural = 'Sistemes de talles'

    def __str__(self):
        return self.codi

    # ── C4 (2026-08-07) · el deute §7.4.3, pagat en CODI ──────────────────────────────
    # N1 va posar l'algorisme (`size_labels`) i el va fer servir una vegada, a la data
    # migration. Faltava la porta: res no impedia tornar a escriure un `base_unit` que
    # contradiu les etiquetes, que és exactament com havia arribat `TODDLER_EU` a dir
    # `AGE_YEARS` amb unes talles en cm. Amb C1 aplicat, ara mateix no hi ha CAP run en
    # conflicte als tres schemes — o sigui que aquesta validació neix amb el terra net.
    def clean(self):
        from django.core.exceptions import ValidationError
        from fhort.pom.size_labels import _tipus_de_les_etiquetes, BASE_UNIT_A_TIPUS

        super().clean()
        if not self.pk:
            return                     # sense pk no hi ha talles: no hi ha res a contrastar
        etiquetes = list(self.talles.values_list('etiqueta', flat=True))
        segons_etiquetes = _tipus_de_les_etiquetes(etiquetes)
        if not segons_etiquetes:
            return                     # les etiquetes no donen veredicte: `base_unit` mana

        errors = {}
        segons_base = BASE_UNIT_A_TIPUS.get((self.base_unit or '').strip().upper())
        if segons_base and segons_base != segons_etiquetes:
            errors['base_unit'] = (
                f"«{self.base_unit}» contradiu les etiquetes del run, que són de tipus "
                f"{segons_etiquetes}. L'etiqueta mana: v. DIAGNOSI_VOCABULARIS §T3."
            )
        if self.tipus_escala and self.tipus_escala != segons_etiquetes:
            errors['tipus_escala'] = (
                f"«{self.tipus_escala}» contradiu les etiquetes, que són {segons_etiquetes}."
            )
        if errors:
            raise ValidationError(errors)


class SizeDefinition(models.Model):
    size_system = models.ForeignKey(SizeSystem, on_delete=models.CASCADE, related_name='talles')
    etiqueta = models.CharField(max_length=30)
    ordre = models.PositiveIntegerField(default=0)
    valor_numeric = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)



    # Sprint S1 — reference body measurements
    body_height_cm  = models.DecimalField(max_digits=5, decimal_places=1,
                        null=True, blank=True,
                        help_text="Alcada corporal de referencia (ISO 8559-1)")
    body_bust_cm    = models.DecimalField(max_digits=5, decimal_places=1,
                        null=True, blank=True,
                        help_text="Perimetre pit (bust/chest) corporal")
    body_waist_cm   = models.DecimalField(max_digits=5, decimal_places=1,
                        null=True, blank=True)
    body_hip_cm     = models.DecimalField(max_digits=5, decimal_places=1,
                        null=True, blank=True)
    age_months_min  = models.IntegerField(null=True, blank=True,
                        help_text="Mesos minim per a baby/kids sizes")
    age_months_max  = models.IntegerField(null=True, blank=True)
    # Fi Sprint S1

    class Meta:
        verbose_name = 'Talla'
        verbose_name_plural = 'Talles'
        ordering = ['size_system', 'ordre']
        # C4 (2026-08-07) · deute §7.4.4. `ordering` ordena per `ordre`, i si dos `ordre`
        # empaten l'ordre real el decideix Postgres — o sigui que el run es llegeix diferent
        # segons el dia. **Un run desordenat és un grading incorrecte**: el motor compta per
        # POSICIÓ. La unicitat és el que converteix `ordre` en una seqüència de debò, i de
        # passada DRF en fabrica sol un UniqueTogetherValidator per a l'API.
        unique_together = [('size_system', 'etiqueta'), ('size_system', 'ordre')]

    def __str__(self):
        return f'{self.size_system.codi} · {self.etiqueta}'


class GarmentGroup(models.Model):
    """Garment families (SWIMWEAR, OUTERWEAR, BOTTOMS, ...). Imported from master data."""

    codi = models.CharField(max_length=40, unique=True)
    nom = models.CharField(max_length=120)
    descripcio = models.TextField(blank=True)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Família de garment'
        verbose_name_plural = 'Famílies de garment'
        ordering = ['codi']

    def __str__(self):
        return f'{self.codi} · {self.nom}'


class GarmentType(models.Model):
    garment_type_global = models.ForeignKey(
        GarmentTypeGlobal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tenant_types',
    )
    codi_client = models.CharField(max_length=60)
    nom_client = models.CharField(max_length=120)
    grup = models.CharField(max_length=40)
    # ── C6 · PAS 1 (2026-08-07) · l'amo del vocabulari de grup és la BD ───────────────
    # Decisió 1 de DIAGNOSI_VOCABULARIS §2.6. La FK i el string CONVIUEN a posta: el pas 2
    # (retirar el string) està ATURAT, i no per prudència genèrica sinó per una dada
    # concreta — el tenant `los` té un `GarmentType` amb `grup='TOPS'` i la taula
    # `GarmentGroup` BUIDA, o sigui que allà el backfill no pot resoldre res i retirar el
    # string perdria l'única informació de grup que hi ha. V. REPORT_CATALEG_TALLES.md §C6.
    #
    # Mentre convisquin, la font de veritat segueix sent `grup` (tots els lectors del cens hi
    # continuen apuntant, i cap contracte d'API canvia). `save()` manté la FK alineada perquè
    # no neixi rància: una FK que ningú escriu és pitjor que no tenir-la.
    grup_ref = models.ForeignKey(
        GarmentGroup, on_delete=models.PROTECT,
        null=True, blank=True, related_name='garment_types',
        verbose_name='Grup (FK)',
        help_text='Pas 1 de C6: conviu amb `grup`. NULL = el codi no existeix a GarmentGroup.',
    )
    actiu = models.BooleanField(default=True)

    # Sprint S13-A — multilanguage + system flag
    nom_en = models.CharField(max_length=200, blank=True, default='')
    nom_ca = models.CharField(max_length=200, blank=True, default='')
    nom_es = models.CharField(max_length=200, blank=True, default='')
    is_system = models.BooleanField(default=False,
        help_text="True = ve del catàleg global canònic, no esborrable")

    # Sprint S1 — construction. (L'M2M `targets_recomanats` es va jubilar 2026-07-19: buit a tots els
    # entorns i sense lector; la compatibilitat target↔família viu a SizingProfile.)
    construccio_habitual = models.CharField(
        max_length=50, blank=True,
        help_text="Ex: WOVEN, KNIT, BOTH, STRETCH_KNIT"
    )
    # Fi Sprint S1
    # Pas previ 5 — descripció de família (construcció)
    descripcio = models.TextField(blank=True, default='')

    def save(self, *args, **kwargs):
        # C6 · pas 1 — la FK segueix el string, no al revés. Mentre `grup` sigui la font de
        # veritat (que ho és fins que el pas 2 es pugui fer), qualsevol escriptura del string
        # ha de reflectir-se aquí o la FK naixeria rància el primer dia. Si el codi no existeix
        # a `GarmentGroup` es deixa NULL: inventar-hi un grup seria exactament el que aquesta
        # migració vol acabar. `update_fields` es respecta perquè un save parcial que no toca
        # `grup` no ha de disparar cap query de més.
        camps = kwargs.get('update_fields')
        if camps is None or 'grup' in camps:
            codi = (self.grup or '').strip()
            actual = GarmentGroup.objects.filter(codi=codi).first() if codi else None
            if (actual.pk if actual else None) != self.grup_ref_id:
                self.grup_ref = actual
                if camps is not None:
                    kwargs['update_fields'] = list(camps) + ['grup_ref']
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Tipus garment (tenant)'
        verbose_name_plural = 'Tipus garment (tenant)'

    def __str__(self):
        return f'{self.codi_client} · {self.nom_client}'


class GarmentPOMMap(models.Model):
    # Migration família → item (COMPLETADA, PAS 6): la pertinença POM viu únicament a
    # garment_type_item. El FK legacy garment_type i el seu unique_together s'han eliminat
    # (migració 0016) un cop migrats i esborrats els 95 mapes legacy.
    # db_constraint=False: 'pom' és app SHARED (taula també a 'public'), però 'tasks' és tenant-only
    # → un constraint de BD cap a tasks_garmenttypeitem petaria a 'public'. L'FK és lògic (ORM);
    # el CASCADE l'emula Django al collector. Patró estàndard per a FK que creuen shared↔tenant.
    garment_type_item = models.ForeignKey('tasks.GarmentTypeItem', on_delete=models.CASCADE,
                                          related_name='pom_maps', null=True, blank=True,
                                          db_constraint=False)
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT, related_name='garment_maps')
    obligatori = models.BooleanField(default=False)
    is_key = models.BooleanField(default=False)
    # Sprint Excel-Map · nivell de la cel·la de l'Excel (K/M/O/D). Metadada addicional,
    # independent d'is_key/obligatori; el loader (load_garment_pom_map) escriu tots tres coherents.
    nivell = models.CharField(
        max_length=1, blank=True, default='O',
        choices=[('K', 'Key'), ('M', 'Mandatory'), ('O', 'Optional'), ('D', 'Detail-dependent')],
    )
    ordre = models.PositiveIntegerField(default=0)
    # Migration família → item: clons de germà es marquen per revisió (Montse ajusta el delta).
    pendent_revisio = models.BooleanField(default=False)
    # C1 (2026-07-30) — la capa (declaració canònica a `models_app.BaseMeasurement.capa`):
    # slug de `MeasurementLayer`, per SLUG i mai per PK (llei G9). Aquí la capa diu de quina
    # matèria de la peça és el POM que la plantilla de l'item reclama: un item pot demanar el
    # mateix POM a l'exterior i al folre i són DUES pertinences, no una. La validació contra
    # el catàleg arriba a C2/C4; fins llavors mana la comporta CHECK de C1/T4.
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
                  "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).",
    )
    # C1-ins — la instància (declaració canònica a `models_app.BaseMeasurement.instancia`).
    # Aquí la instància diu QUANTES VEGADES la plantilla de l'item reclama el mateix POM: una
    # americana demana la sisa dues vegades —dreta i esquerra— i són DUES pertinences, no una.
    # És l'origen de tot: el que aquesta taula declara és el que la sembra item→model copia.
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )

    class Meta:
        verbose_name = 'Mapa garment ↔ POM'
        verbose_name_plural = 'Mapes garment ↔ POM'
        ordering = ['garment_type_item', 'ordre']
        # C1/T3 — la clau incorpora la CAPA (v. `models_app.BaseMeasurement.Meta`): un item
        # pot reclamar el mateix POM a l'exterior i al folre, i són dues pertinences.
        # C1-ins/T3 — i la INSTÀNCIA: també en són dues si el reclama dos cops a la mateixa
        # capa (sisa dreta i esquerra).
        unique_together = [('garment_type_item', 'pom', 'capa', 'instancia')]
        constraints = [
            # C1/T4 — la comporta (v. `models_app.BaseMeasurement.Meta`, on hi ha
            # l'argument sencer). C4 la retira per migració.
            # ✅ C4/G4 (04/08) — retirada per la migració pom/0057. El CATÀLEG és l'últim grup
            # a posta: una germana declarada aquí es propaga a tots els models que en neixin
            # (C-31.h, la sembra item→model), o sigui que obrir-lo abans que les superfícies
            # del model sabessin llegir-les hauria escampat el problema en comptes de
            # contenir-lo. És l'única de les quatre taules d'aquest grup que viu també a
            # `public`: el catàleg és compartit.
            # C1-ins — la comporta d'instància (v. `models_app.BaseMeasurement.Meta`).
            # C4-ins la retira per migració.
            # ✅ C4/G4 (04/08) — retirada per la migració pom/0057. El CATÀLEG és l'últim grup
            # a posta: una germana declarada aquí es propaga a tots els models que en neixin
            # (C-31.h, la sembra item→model), o sigui que obrir-lo abans que les superfícies
            # del model sabessin llegir-les hauria escampat el problema en comptes de
            # contenir-lo. És l'única de les quatre taules d'aquest grup que viu també a
            # `public`: el catàleg és compartit.
        ]

    def __str__(self):
        anchor = self.garment_type_item.code if self.garment_type_item_id else '?'
        return f'{anchor} · {self.pom.codi_client}'


class ItemBaseSet(models.Model):
    """Sprint BaseSet condicionat (B1, 2026-07-25). Satèl·lit de mesures base de l'Item per MÓN.

    LLEI (Patró C, Agus 2026-07-25): «L'item MAI es parteix. Un sol GTI per peça, un sol superset
    de POMs. El món viu als satèl·lits: BaseSets condicionats per (item × size_system × fit).»
    Això substitueix el pointer únic GarmentTypeItem.base_size_definition (V1, llegat a jubilar):
    un item pot vestir-se en ALPHA_EU_M i en KIDS_CM alhora, i cada món té la seva talla base i
    els seus valors, sense partir l'item ni duplicar el superset de POMs (GarmentPOMMap).

    CAP scope-node, cap àmbit, cap cascada: el matching és un LOOKUP DIRECTE per la clau única
    (garment_type_item, size_system, fit_type). Vegeu `resolve_item_base_set()`.

    `fit_type` és NULLABLE per la llei, però la convenció de lookup és REGULAR: tant la creació
    com el resolver passen pel mateix `normalize_fit_type()`, que tradueix «cap fit» → el FitType
    REGULAR del schema. NULL només subsisteix en schemas que no tenen FitType sembrat (avui `los`).
    Sense aquesta normalització compartida un set creat sense fit i una cerca sense fit podrien
    caure en files diferents. Les DUES constraints d'unicitat (la normal i la parcial per a
    fit_type IS NULL) hi són perquè a Postgres NULL no participa en un UNIQUE: sense la parcial,
    dos sets «sense fit» del mateix món podrien conviure.

    db_constraint=False al FK cap a 'tasks' pel mateix motiu que GarmentPOMMap i
    ItemBaseMeasurement: 'pom' és app SHARED (taula també a 'public') i 'tasks' és tenant-only.
    """
    ORIGEN_PROMOCIO = 'PROMOCIO'  # nascut d'una promoció model→set (via canònica de naixement, B3)
    ORIGEN_MASTER = 'MASTER'      # entrat per paquet/màster de catàleg
    ORIGEN_MANUAL = 'MANUAL'      # creat a mà al catàleg (ItemAuthoring)
    ORIGEN_CHOICES = [
        (ORIGEN_PROMOCIO, 'Promogut des d\'un model'),
        (ORIGEN_MASTER, 'Màster de catàleg'),
        (ORIGEN_MANUAL, 'Creat manualment'),
    ]

    garment_type_item = models.ForeignKey('tasks.GarmentTypeItem', on_delete=models.CASCADE,
                                          related_name='base_sets', db_constraint=False)
    size_system = models.ForeignKey(SizeSystem, on_delete=models.PROTECT,
                                    related_name='item_base_sets')
    # PROTECT i no SET_NULL: el fit és part de la clau única. Un SET_NULL col·lapsaria el set
    # dins l'slot «sense fit» del mateix món i podria xocar amb un que ja hi visqués.
    # Referència per string: FitType es declara més avall en aquest mateix mòdul.
    fit_type = models.ForeignKey('pom.FitType', on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='item_base_sets',
                                 help_text="Buit = Regular (convenció de lookup).")
    # OBLIGATÒRIA per la llei 2: la talla base es declara EN CREAR el set, i totes les mesures
    # del set s'hi expressen. PROTECT: esborrar la talla base d'un set viu ha de BLOQUEJAR.
    base_size_definition = models.ForeignKey('pom.SizeDefinition', on_delete=models.PROTECT,
                                             related_name='base_set_for_items',
                                             help_text="Talla base del set (on s'expressen els valors).")

    # Provinença i autoria — mateix patró P9 que ItemBaseMeasurement (2026-07-22).
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default=ORIGEN_MANUAL)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='item_base_sets_updated',
    )

    class Meta:
        verbose_name = 'Set de mesures base d\'item'
        verbose_name_plural = 'Sets de mesures base d\'item'
        ordering = ['garment_type_item', 'size_system', 'fit_type']
        constraints = [
            models.UniqueConstraint(
                fields=['garment_type_item', 'size_system', 'fit_type'],
                name='uniq_itembaseset_item_system_fit',
            ),
            models.UniqueConstraint(
                fields=['garment_type_item', 'size_system'],
                condition=models.Q(fit_type__isnull=True),
                name='uniq_itembaseset_item_system_nofit',
            ),
        ]

    def clean(self):
        # La talla base ha de viure al sistema del set. Mateix esperit que GarmentTypeItem.clean()
        # (tasks/models.py:341): validació d'ORM, no constraint de BD (cross-table fràgil).
        super().clean()
        if self.base_size_definition_id and self.size_system_id:
            if self.base_size_definition.size_system_id != self.size_system_id:
                from django.core.exceptions import ValidationError
                raise ValidationError({
                    'base_size_definition': (
                        "La talla base ha de pertànyer al sistema de talles del set.")
                })

    def __str__(self):
        anchor = self.garment_type_item.code if self.garment_type_item_id else '?'
        fit = self.fit_type.codi if self.fit_type_id else 'REGULAR'
        return f'{anchor} · {self.size_system.codi} · {fit} @ {self.base_size_definition.etiqueta}'


class FitTypeDesconegut(ValueError):
    """El fit demanat no correspon a cap FitType del catàleg d'aquest schema.

    NO és el mateix que «cap fit»: un fit desconegut que es degradés a None cauria a l'slot
    REGULAR/NULL i el lookup retornaria el set d'un ALTRE món. Val més quedar-se sense set.
    """


# Pont de vocabularis. `Model.fit_type` (models_app/models.py:204) és un CharField amb valors
# propis en CamelCase i NO coincideix amb `FitType.codi`, que és el catàleg real en majúscules.
# Els tres primers els resol el match case-insensitive; aquests dos no, i sense el pont
# «Oversize» seria un fit desconegut. «Tailored» NO hi és a posta: no té equivalent al catàleg
# de FitType i inventar-l'hi seria decidir producte — vegeu la bandera CTO de l'informe.
FIT_ALIES_MODEL = {
    'OVERSIZE': 'OVERSIZED',
}


def normalize_fit_type(fit=None):
    """Convenció de lookup del BaseSet: «cap fit» → FitType REGULAR d'aquest schema.

    Font ÚNICA compartida per la creació i pel resolver (`resolve_item_base_set`): si les dues
    bandes no normalitzessin igual, un set creat sense fit i una cerca sense fit cauria en files
    diferents.

    Accepta una instància de FitType, un id, un codi ('REGULAR', o el vocabulari de Model
    'Regular'/'Oversize') o None. Retorna None NOMÉS quan no s'ha demanat cap fit i el schema no
    té FitType REGULAR sembrat (avui `los`); llavors el set viu amb fit_type NULL, cobert per la
    constraint parcial. Un fit demanat i no trobat aixeca FitTypeDesconegut.
    """
    if fit is None or fit == '':
        return FitType.objects.filter(codi='REGULAR').first()
    if isinstance(fit, FitType):
        return fit
    if isinstance(fit, int):
        obj = FitType.objects.filter(pk=fit).first()
        if obj is None:
            raise FitTypeDesconegut(f'FitType id={fit} inexistent')
        return obj
    codi = str(fit).strip().upper()
    codi = FIT_ALIES_MODEL.get(codi, codi)
    if codi == 'REGULAR':
        # REGULAR ≡ «cap fit»: és la mateixa branca que fit=None, no una de paral·lela. Sense
        # això, un schema sense FitType sembrat (avui `los`, i els schemas de test) crearia els
        # sets amb fit_type NULL i després no els trobaria mai, perquè Model.fit_type val
        # 'Regular' per defecte (models_app/models.py:204) i seria un fit «desconegut».
        return FitType.objects.filter(codi='REGULAR').first()
    obj = FitType.objects.filter(codi__iexact=codi).first()
    if obj is None:
        raise FitTypeDesconegut(f'FitType «{fit}» inexistent al catàleg')
    return obj


def resolve_item_base_set(item, size_system, fit=None):
    """Lookup DIRECTE del BaseSet d'un món. Cap heurística, cap fuzzy, cap cascada (llei 1).

    `item` i `size_system` accepten instància o id. `fit` passa per `normalize_fit_type()`.
    Retorna l'ItemBaseSet o None — i el None és senyal de «món sense set» (naixement mandrós
    pendent, llei 7), mai un error. Un fit fora de catàleg també és None: aquell món no té set
    perquè aquell món no existeix al catàleg.
    """
    item_id = getattr(item, 'pk', item)
    system_id = getattr(size_system, 'pk', size_system)
    if item_id is None or system_id is None:
        return None
    try:
        fit_obj = normalize_fit_type(fit)
    except FitTypeDesconegut:
        return None
    return ItemBaseSet.objects.filter(
        garment_type_item_id=item_id,
        size_system_id=system_id,
        fit_type=fit_obj,
    ).select_related('base_size_definition', 'size_system', 'fit_type').first()


# Convenció Montse (llei 2 del BaseSet): la talla base d'un set és la MÉS PETITA del sistema,
# excepte en adults, on el taller treballa en HOME M/42 i DONA S/38. És SUGGERIMENT de UI: qui
# crea el set decideix, i el codi no imposa res — per això `suggerir_talla_base` retorna una
# proposta i mai escriu.
CONVENCIO_TALLA_BASE = {
    'MAN': ('M', '42'),
    'UNISEX_ADULT': ('M', '42'),
    'WOMAN': ('S', '38'),
    'MATERNITY': ('S', '38'),
}


def suggerir_talla_base(size_system, target_codi=None):
    """Proposta de talla base per a un BaseSet nou. Retorna una SizeDefinition o None.

    Cau a la més petita del sistema sempre que el target no sigui d'adult o que l'etiqueta de
    convenció no existeixi en aquell sistema (p.ex. un sistema numèric on no hi ha cap «M»).
    """
    system_id = getattr(size_system, 'pk', size_system)
    talles = SizeDefinition.objects.filter(size_system_id=system_id).order_by('ordre', 'id')
    etiquetes = CONVENCIO_TALLA_BASE.get((target_codi or '').strip().upper())
    if etiquetes:
        for et in etiquetes:
            trobada = talles.filter(etiqueta__iexact=et).first()
            if trobada is not None:
                return trobada
    return talles.first()


class ItemBaseMeasurement(models.Model):
    """Sprint Mesures Base per Item (P2). Valors base TÍPICS de la plantilla de l'Item, per POM.

    Germà de GarmentPOMMap (pertinença pura) que aporta el VALOR: penja NET de l'Item per clau
    (garment_type_item, pom), SENSE passar pel Model ni per GarmentPOMMap. És plantilla/catàleg
    (capa Item), no instància: a la sembra (P5) aquests valors es COPIEN a BaseMeasurement del
    Model (copy-at-the-moment, origen='ITEM_STANDARD'); a partir d'aquí el Model és sobirà.

    La talla a la qual s'expressen aquests valors és GarmentTypeItem.base_size_definition (P1).
    db_constraint=False al FK cap a 'tasks' (tenant-only) pel mateix motiu que GarmentPOMMap:
    'pom' és SHARED (taula també a 'public') i un constraint cap a tasks_garmenttypeitem petaria a
    'public'. El FK és lògic (ORM); el CASCADE l'emula Django al collector."""
    garment_type_item = models.ForeignKey('tasks.GarmentTypeItem', on_delete=models.CASCADE,
                                          related_name='base_measurements', db_constraint=False)
    # B1 (2026-07-25) — el valor ja no penja de l'item pelat sinó del SET del seu món.
    # 0047 crea la columna nullable, 0048 hi repunta les files, 0049 la torna NOT NULL (0 òrfenes
    # verificades a fhort/los/public). `garment_type_item` es manté com a denormalització: és
    # redundant amb base_set.garment_type_item, però sosté l'unique_together històric i tots els
    # consumidors V1 mentre convisquin les dues vies.
    base_set = models.ForeignKey('pom.ItemBaseSet', on_delete=models.CASCADE,
                                 related_name='measurements')
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT, related_name='item_base_measurements')
    # Valor base a la talla base de l'Item (cm). NULL = POM de l'Item sense valor estàndard encara.
    base_value_cm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    # Toleràncies opcionals (mateixa precisió que BaseMeasurement.tolerancia_*); NULL → els
    # consumidors cauen al default del catàleg (POMMaster.tolerancia_default_*).
    tol_minus = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tol_plus = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Nomenclatura editable; còpia LITERAL de BaseMeasurement.nom_fitxa (models_app/models.py:515)
    # perquè la sembra item→model copiï camp-a-camp sense traducció. Se sembra de l'abreviatura del
    # POM, editable (sobirania de l'item).
    # DEUTE: renombrar nom_fitxa→anglès a les DUES taules a la sessió Size Check.
    nom_fitxa = models.CharField(max_length=20, blank=True, default='')

    # ── P9 (2026-07-22) — PROVINENÇA I AUTORIA. Condició dura de D-PROM: sense això una
    # promoció model→item és IRRECUPERABLE I ANÒNIMA (un valor de plantilla no deia ni qui
    # ni quan; risc 9 de la DIAGNOSI_GTI_PLANTILLA).
    #
    # `origen` NO copia els 8 valors de BaseMeasurement.ORIGEN_CHOICES: la capa Item només
    # en necessita tres. TEMPLATE/ITEM_STANDARD/FITTED/CALCULATED/CHECKED/STANDARD són estats
    # d'INSTÀNCIA (com ha arribat un valor a un model concret) i aquí no volen dir res.
    ORIGEN_MANUAL = 'MANUAL'        # escrit a mà a ItemAuthoring / ViewSet (l'únic camí fins avui)
    ORIGEN_PROMOTED = 'PROMOTED'    # promogut des d'un model real (acte CONFIGURE explícit)
    ORIGEN_IMPORTED = 'IMPORTED'    # entrat per paquet/loader (load_losan_package)
    ORIGEN_CHOICES = [
        (ORIGEN_MANUAL, 'Introduït manualment'),
        (ORIGEN_PROMOTED, 'Promogut des d\'un model'),
        (ORIGEN_IMPORTED, 'Importat de paquet'),
    ]
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default=ORIGEN_MANUAL)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    # SET_NULL: esborrar un usuari no ha d'endur-se el valor de plantilla del taller.
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='item_base_measurements_updated',
    )
    # C1 — la capa (declaració canònica a `models_app.BaseMeasurement.capa`). És el mirall de
    # la capa Item del mateix eix: el valor típic de plantilla també és el valor D'UNA capa.
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
                  "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).",
    )
    # C1-ins — la instància (declaració canònica a `models_app.BaseMeasurement.instancia`).
    # Mirall de la instància del `GarmentPOMMap` del mateix eix: si la plantilla reclama el
    # POM dues vegades, el valor típic també és doble.
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )

    class Meta:
        verbose_name = 'Mesura base d\'item'
        verbose_name_plural = 'Mesures base d\'item'
        ordering = ['garment_type_item', 'pom']
        # B1 (2026-07-25) — la clau passa de (item, pom) a (base_set, pom). Amb la clau V1, un
        # item amb DOS sets no podria tenir el mateix POM als dos, que és justament el que la
        # llei del BaseSet condicionat demana (la mateixa peça vestida en dos mons, cadascun amb
        # el seu valor per al mateix POM). El set ja porta l'item, així que no es perd unicitat.
        # C1/T3 (2026-07-30) — i ara hi entra la CAPA (v. `models_app.BaseMeasurement.Meta`):
        # el mateix POM del mateix set té un valor a l'exterior i un altre al folre.
        # C1-ins/T3 — i la INSTÀNCIA, pel mateix camí: dues repeticions del POM a la mateixa
        # capa són dos valors típics.
        unique_together = [('base_set', 'pom', 'capa', 'instancia')]
        constraints = [
            # C1/T4 — la comporta (v. `models_app.BaseMeasurement.Meta`). C4 la retira.
            # ✅ C4/G4 (04/08) — retirada per la migració pom/0057, al costat de
            # `GarmentPOMMap` (v. l'argument allà). La base de l'ITEM és la plantilla d'on
            # surten les mesures d'un model nou.
            # C1-ins — la comporta d'instància (v. `models_app.BaseMeasurement.Meta`).
            # C4-ins la retira per migració.
            # ✅ C4/G4 (04/08) — retirada per la migració pom/0057, al costat de
            # `GarmentPOMMap` (v. l'argument allà). La base de l'ITEM és la plantilla d'on
            # surten les mesures d'un model nou.
        ]

    def __str__(self):
        anchor = self.garment_type_item.code if self.garment_type_item_id else '?'
        return f'{anchor} · {self.pom.codi_client} = {self.base_value_cm}cm'


class GradingRuleSet(models.Model):
    # PROVINENÇA-LITE (llei PROVINENÇA, DECISIONS.md:348 — versió mínima; el document d'origen i
    # el snapshot dels values_by_size queden diferits amb nom). Sense aquest eix, res distingeix un
    # ruleset canònic d'un derivat d'un run de client, i una còpia cega a un tenant nou violaria
    # RUN-CLIENT (DECISIONS.md:304, la regla com a secret industrial).
    # NULL = "no classificat": l'estat de les files anteriors al camp. El tanca el backfill
    # (`manage.py set_grading_origen`), que és decisió humana, no automàtica.
    # SEMÀNTICA (decisió CTO 2026-07-10):
    #   CANONICAL  — catàleg propi de FHORT: viatja a un tenant nou.
    #   CLIENT_RUN — DERIVAT DE CLIENT, tant si ve d'un run/fitxa importat com si és autoria
    #                manual per a un client concret (p.ex. clonar un perfil estàndard en una
    #                versió de client). MAI viatja. El valor no es renomenarà: si algun dia
    #                la paraula "run" molesta, és un rename cosmètic del choice.
    #   IMPORT     — entrat des d'una font externa sense client darrere.
    ORIGEN_CANONICAL = 'CANONICAL'
    ORIGEN_CLIENT_RUN = 'CLIENT_RUN'
    ORIGEN_IMPORT = 'IMPORT'
    ORIGEN_CHOICES = [
        (ORIGEN_CANONICAL, 'Canònic FHORT'),
        (ORIGEN_CLIENT_RUN, 'Derivat de run de client'),
        (ORIGEN_IMPORT, 'Importat'),
    ]
    origen = models.CharField(
        max_length=12, choices=ORIGEN_CHOICES, null=True, blank=True,
        help_text="Procedència. NULL = no classificat (anterior a la llei PROVINENÇA).")

    nom = models.CharField(max_length=120)
    garment_group = models.ForeignKey(
        GarmentGroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='grading_rule_sets',
    )
    size_system = models.ForeignKey(SizeSystem, on_delete=models.PROTECT, null=True, blank=True, related_name='grading_rule_sets')
    # CONTENIDOR (llei 2026-07-16) — el node fi de la identitat d'un contenidor de client:
    # (customer + size_system + garment_type_item + fit_type). `garment_group` (sobre) és més bast i
    # queda com a eix opcional del picker; NO és identitat. FK cap a tasks.GarmentTypeItem (cross-app,
    # pom viu al mateix schema del tenant que tasks). Nullable i additiu: els canònics/seed el deixen
    # NULL (no són de client). El FK invers `GarmentTypeItem.grading_rule_set` (tasks/models.py:319)
    # apunta al MATEIX contenidor: es reconcilien al backfill. on_delete=SET_NULL: esborrar un item no
    # destrueix el contenidor, només neteja el pointer.
    garment_type_item = models.ForeignKey(
        'tasks.GarmentTypeItem', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='container_rule_sets', db_constraint=False,
        help_text="Node fi de la identitat del contenidor de client (llei CONTENIDOR). NULL = canònic/no-client.")
    actiu = models.BooleanField(default=True)
    # N1 — client propietari de la graduació (àlies de nomenclatura). FK REAL a Customer (decisió
    # CTO), nullable i additiu. Divergència ANOTADA i NO tocada: SizeSystem.customer_codi va per
    # codi de 3 chars; aquí anem per FK. Backfill via size_system.customer_codi (N2-3).
    customer = models.ForeignKey(
        'tasks.Customer', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='grading_rule_sets', db_constraint=False)
    # R2 — codis de document del run que NO es van poder vincular a cap POM (no es perden en
    # silenci: es desen aquí com a "pendents de vincular" per revisar-los més tard). Llista de str.
    pendents_vincular = models.JSONField(default=list, blank=True,
        help_text="Codis de document no vinculats a cap POM en crear el run (pendents de vincular).")



    # Sprint S1 — target, construction, versioning
    # P7 (2026-07-22, D-CONS "un rol, un vincle") — el FK legacy `target` s'ha RETIRAT
    # (migració 0043). `targets` és la font única del ventall de targets: és l'únic que
    # sap expressar el cas real (8 rulesets aplicaven a més d'un target i el FK no ho
    # podia representar). Vegeu docs/diagnosis/DIAGNOSI_ITEM_PLANTILLA_COMPLETA_2026-07-22.md §B2.6.
    targets = models.ManyToManyField(
        'Target',
        blank=True,
        related_name='grading_rule_sets',
        verbose_name='Targets aplicables',
        help_text='Un RuleSet pot aplicar a múltiples targets (ex: BABY_GIRL+BABY_BOY+BABY_UNISEX).',
    )
    construction = models.ForeignKey(
        'ConstructionType', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='grading_rule_sets',
    )
    fit_type = models.ForeignKey(
        'FitType', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='grading_rule_sets',
    )
    is_system_default = models.BooleanField(default=False,
        help_text="True = ve del seed data estandard ISO")
    parent_version = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='versions',
        help_text="NULL = original estandard. Apunta al pare si es versio client."
    )
    version_number = models.IntegerField(default=1)
    codi_sistema = models.CharField(max_length=50, blank=True,
        help_text="Codi de referencia — ex: EU_WOVEN_WOMAN_REGULAR")
    # Fi Sprint S1

    class Meta:
        verbose_name = 'Joc de regles grading'
        verbose_name_plural = 'Jocs de regles grading'
        constraints = [
            # CONTENIDOR ÚNIC (llei 2026-07-16): un sol contenidor de client per combinació
            # (customer + size_system + garment_type_item + fit_type). PARCIAL a `origen='CLIENT_RUN'`:
            # els canònics (customer NULL, origen CANONICAL/IMPORT/NULL) queden intactes. Postgres tracta
            # NULLS DISTINCT per defecte → mentre `garment_type_item` sigui NULL no bloqueja (els client
            # rulesets el porten un cop backfillats). Guarda dura de la unicitat, no només a l'aplicació.
            models.UniqueConstraint(
                fields=['customer', 'size_system', 'garment_type_item', 'fit_type'],
                condition=models.Q(origen='CLIENT_RUN'),
                name='uniq_client_container_identity',
            ),
        ]

    def __str__(self):
        return self.nom


class RuleSetScopeNode(models.Model):
    """ÀMBIT D'APLICABILITAT (disponibilitat) d'un GradingRuleSet de client — un node de l'arbre únic
    Grup→Família→Item al qual el contenidor «aplica» (= «està disponible per a»). MULTI-NODE: un
    contenidor en pot tenir diversos (p.ex. grup TOPS + item Blusa).

    Sprint ÀMBIT (2026-07-17, opció (c) del gate): la IDENTITAT/unicitat del contenidor SEGUEIX vivint a
    `GradingRuleSet.garment_type_item` + la constraint parcial `uniq_client_container_identity` (migració
    0039, INTACTES). Aquest model és NOMÉS DISPONIBILITAT per al matching (picker/cascada): additiu, cap
    canvi a la identitat ni a la reconciliació de sembra. Un node = EXACTAMENT un dels tres FKs (validat a
    clean() segons node_type)."""
    NODE_GROUP = 'GROUP'
    NODE_TYPE = 'TYPE'
    NODE_ITEM = 'ITEM'
    NODE_CHOICES = [(NODE_GROUP, 'Grup'), (NODE_TYPE, 'Família'), (NODE_ITEM, 'Item')]

    rule_set = models.ForeignKey(GradingRuleSet, on_delete=models.CASCADE, related_name='scope_nodes')
    node_type = models.CharField(max_length=6, choices=NODE_CHOICES)
    garment_group = models.ForeignKey(GarmentGroup, on_delete=models.CASCADE, null=True, blank=True,
                                      related_name='scope_nodes')
    garment_type = models.ForeignKey(GarmentType, on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='scope_nodes')
    # Cross-app cap a tasks (igual que GradingRuleSet.garment_type_item): FK lògic, db_constraint=False
    # (pom viu al schema del tenant; un constraint real cap a tasks petaria a 'public').
    garment_type_item = models.ForeignKey('tasks.GarmentTypeItem', on_delete=models.CASCADE, null=True,
                                          blank=True, db_constraint=False, related_name='scope_nodes')

    class Meta:
        verbose_name = "Node d'àmbit de grading"
        verbose_name_plural = "Nodes d'àmbit de grading"
        constraints = [
            # Un sol node de cada mena per contenidor (parcials per node_type; eviten duplicats que
            # una UniqueConstraint composta amb NULLs DISTINCT deixaria passar).
            models.UniqueConstraint(fields=['rule_set', 'garment_group'],
                                    condition=models.Q(node_type='GROUP'), name='uniq_scope_group'),
            models.UniqueConstraint(fields=['rule_set', 'garment_type'],
                                    condition=models.Q(node_type='TYPE'), name='uniq_scope_type'),
            models.UniqueConstraint(fields=['rule_set', 'garment_type_item'],
                                    condition=models.Q(node_type='ITEM'), name='uniq_scope_item'),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        fks = {'GROUP': self.garment_group_id, 'TYPE': self.garment_type_id, 'ITEM': self.garment_type_item_id}
        setats = [k for k, v in fks.items() if v is not None]
        if setats != [self.node_type]:
            raise ValidationError(
                f"Un node d'àmbit ha de tenir EXACTAMENT el FK del seu node_type ({self.node_type}); "
                f"trobat: {setats or 'cap'}.")

    def __str__(self):
        codi = (self.garment_group and self.garment_group.codi) or \
               (self.garment_type and self.garment_type.codi_client) or \
               (self.garment_type_item_id and f'item#{self.garment_type_item_id}') or '?'
        return f'{self.node_type}:{codi}'


class GradingRule(models.Model):
    LOGICA_LINEAR = 'LINEAR'
    LOGICA_STEP = 'STEP'
    LOGICA_FIXED = 'FIXED'
    LOGICA_ZERO = 'ZERO'
    LOGICA_EXCEPTION = 'EXCEPTION'
    LOGICA_CHOICES = [
        (LOGICA_LINEAR, 'Linear'),
        (LOGICA_STEP, 'Step'),
        (LOGICA_FIXED, 'Fixed'),
        (LOGICA_ZERO, 'Zero'),
        (LOGICA_EXCEPTION, 'Exception'),
    ]

    rule_set = models.ForeignKey(GradingRuleSet, on_delete=models.CASCADE, related_name='regles')
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT, related_name='regles_grading')
    talla_base = models.ForeignKey(SizeDefinition, on_delete=models.PROTECT, related_name='regles_base')
    # ── CAT2.1 · PAS (a) · LA BASE, PER ETIQUETA ─────────────────────────────────────
    # Decisió d'Agus (07/08): les regles referencien l'ETIQUETA de talla, no una FILA d'un run
    # concret. Mateix patró que el creuament de POMs (per codi, mai per id) — i, sobretot,
    # mateix patró que el seu propi germà `talla_break_label`, que la Peça A ja va passar a
    # etiqueta amb el comentari «break ancorat per ETIQUETA, resolt al run de graduació».
    #
    # 🔑 El motor NO canvia, i això no és un descuit: `_apply_rule` ja ancora a
    # `model.base_size_label` sobre el run del MODEL, i `grading_utils.py:72` ja deia en veu
    # alta que `rule.talla_base` és «mer metadata del seed». La FK no calculava res — però
    # PROTEGIA files d'un run, i això és el que va lligar 1.267 regles a runs que no són seus
    # i el que va fer impossible esborrar «Alpha EU — Grading Reference».
    #
    # Conviu amb la FK fins que el backfill doni 100% (v. `0069`); el pas (b) la retira.
    talla_base_label = models.CharField(
        max_length=30, blank=True, default='',
        verbose_name='Talla base (etiqueta)',
        help_text="L'etiqueta, resolta contra el run del model. Buit = encara no backfillat.",
    )
    logica = models.CharField(max_length=20, choices=LOGICA_CHOICES)
    # Sprint S16-A — decimals 4 → 2 (real precision for garment measurements in cm)
    # NOTA: el camp `valor_base` s'ha eliminat (Sprint Mesures Base per Item, P0). La talla base
    # del grading viu a `talla_base`; el VALOR base de cada POM viu a BaseMeasurement (del Model)
    # i, com a plantilla, a ItemBaseMeasurement (de l'Item). El grading no en depèn (mai es llegia
    # per a càlcul; només s'emmagatzemava com a fidelitat redundant, sempre 0 a la BD).
    increment = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    valors_step = models.JSONField(null=True, blank=True)
    # Peça A — forma canònica d'aplicació (break ancorat per ETIQUETA, resolt al run de
    # graduació). valors_step roman com a origen/auditoria. NULL = no backfillat → fallback.
    increment_base = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    increment_break = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    talla_break_label = models.CharField(max_length=30, null=True, blank=True)
    talla_break_pos = models.IntegerField(null=True, blank=True)  # cache opcional (run del ruleset)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Regla grading'
        verbose_name_plural = 'Regles grading'
        # ⚠️ SENSE `capa` i SENSE `instancia`, PER DECISIÓ DE DOMINI — igual que la seva
        # germana resident `models_app.ModelGradingRule`, on hi ha l'argument sencer.
        # Una regla és una llei d'INCREMENTS, no un valor: el folre d'un pit creix el mateix
        # que l'exterior d'aquell pit, i (decisió Montse, C1-ins) la sisa dreta i l'esquerra
        # GRADÚEN IGUAL. Els VALORS sí que porten els dos eixos (BaseMeasurement, GradedSpec,
        # ItemBaseMeasurement…): la regla és compartida, el resultat d'aplicar-la és per capa
        # i per instància. Donar-li cap dels dos eixos voldria dir demanar que es declari n
        # vegades el mateix delta i mantenir-les sincronitzades a mà.
        # Qui vulgui revisar-ho: és decisió d'arquitectura (Patró C), no una peça d'sprint.
        unique_together = [('rule_set', 'pom')]

    def __str__(self):
        return f'{self.rule_set.nom} · {self.pom.codi_client} ({self.logica})'


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 3 — Grading engine (catalog data shared with tenants)
# BaseMeasurement lives in models_app (FK Model), GradedSpec lives in fitting (FK GradingVersion).
# ─────────────────────────────────────────────────────────────────────────────

# G6/1a — `GradingException` JUBILADA (2026-07-13, DIAGNOSI_G6_DUAL_PATH §B2.1).
#
# Era una excepció per (POM, talla) penjada del GradingRuleSet — o sigui, d'una PLANTILLA
# COMPARTIDA: qualsevol model que fes servir aquell set l'heretava. El seu substitut viu és
# `models_app.ModelGradingOverride`, que neix acotat a UN model, i el docstring d'aquell ja
# declarava per escrit que existia per rellevar-la ("UNLIKE pom.GradingException, which lives
# on the shared GradingRuleSet (a template) and would leak to every model using that set").
#
# La substitució estava feta; el mort no s'havia enterrat. En jubilar-la: 0 files a la BD (als
# DOS schemes), cap escriptor a l'aplicació (cap viewset, cap serializer, cap URL, zero hits als
# dos frontends) — només seeds i l'importador legacy. El que es mata de debò és una BRANCA del
# fork de precedència del motor (`pom/services.py`), que tenia dues de les tres branques mortes.


class ClientMesuraPerfil(models.Model):
    """Online Welford statistic per (codi_client, garment_type, POM, size).

    Accumulates mean/M2 without storing individual values. It is updated
    every time a fitting is closed and a line has been modified.

    Sprint 5B.3: keyed by `codi_client` (the end brand-client within the tenant,
    from Model.codi_client), not by the tenant-level `client` FK (which lumped all
    brands of a tenant together). `client` is kept nullable for legacy/optional use.
    """
    client = models.ForeignKey(
        'tenants.Client', on_delete=models.CASCADE, related_name='mesures_perfil',
        null=True, blank=True,
    )
    codi_client = models.CharField(max_length=80, blank=True, default='')
    garment_type = models.ForeignKey(GarmentType, on_delete=models.CASCADE, related_name='mesures_perfil')
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT, related_name='mesures_perfil')
    talla = models.CharField(max_length=20)
    n_mostres = models.PositiveIntegerField(default=0)
    mitjana = models.FloatField(default=0.0)
    m2_acum = models.FloatField(default=0.0)   # Welford running M2
    desviacio = models.FloatField(default=0.0)
    darrera_actualitzacio = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil mesures client'
        verbose_name_plural = 'Perfils mesures client'
        unique_together = [('codi_client', 'garment_type', 'pom', 'talla')]
        ordering = ['codi_client', 'garment_type', 'pom', 'talla']

    def __str__(self):
        return f'{self.codi_client} · gt{self.garment_type_id} · {self.pom.codi_client} @ {self.talla} (n={self.n_mostres})'



# =============================================================================
# SPRINT S1 — New global models (public schema)
# Added to fhort/pom/models.py
# =============================================================================

class FitType(models.Model):
    """Fit type (Slim / Regular / Loose / Oversized). Public schema."""
    CODI_CHOICES = [
        ('SLIM','Slim'),
        ('REGULAR','Regular'),
        ('RELAXED','Relaxed'),
        ('LOOSE','Loose'),
        ('OVERSIZED','Oversized'),
    ]
    codi          = models.CharField(max_length=20, unique=True, choices=CODI_CHOICES)
    nom_en        = models.CharField(max_length=100)
    nom_cat       = models.CharField(max_length=100, blank=True)
    nom_es        = models.CharField(max_length=100, blank=True)
    descripcio_en = models.TextField(blank=True)
    display_order = models.IntegerField(default=0)

    # Sprint S1 — ease fields
    ease_bust_cm  = models.DecimalField(max_digits=5, decimal_places=1,
                       null=True, blank=True,
                       help_text="Ease estandar pit en cm")
    ease_waist_cm = models.DecimalField(max_digits=5, decimal_places=1,
                       null=True, blank=True)
    ease_hip_cm   = models.DecimalField(max_digits=5, decimal_places=1,
                       null=True, blank=True)
    ease_thigh_cm = models.DecimalField(max_digits=5, decimal_places=1,
                       null=True, blank=True)
    client_definible = models.BooleanField(default=False,
                       help_text="Si True, el client pot crear instancies propies")

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.nom_en


class Target(models.Model):
    """Target population of a garment. Public schema."""
    # P0b (2026-07-24) — vocabulari alineat amb el sector: la franja que LOSAN diu «BABY» és
    # la que aquí es deia TODDLER, i el que aquí es deia BABY és NEWBORN. Verificat contra la
    # columna `seccio_client` de sembra_models_losan_ss27.csv (1:1 amb comptes exactes).
    # Renames: BOY→KID_BOY · GIRL→KID_GIRL · TODDLER_*→BABY_* · BABY_*→NEWBORN_*.
    # El rename de dades el fa backend/scripts_tmp/rename_targets_p0b.py als 3 schemas
    # (els FK apunten a `id`, no a `codi` — cap referència es trenca).
    CODI_CHOICES = [
        ('WOMAN','Woman'),('MAN','Man'),('UNISEX_ADULT','Unisex Adult'),
        ('NEWBORN_GIRL','Newborn Girl'),('NEWBORN_BOY','Newborn Boy'),('NEWBORN_UNISEX','Newborn Unisex'),
        ('BABY_GIRL','Baby Girl'),('BABY_BOY','Baby Boy'),
        ('KID_GIRL','Kid Girl'),('KID_BOY','Kid Boy'),
        ('TEEN_GIRL','Teen Girl'),('TEEN_BOY','Teen Boy'),
        ('MATERNITY','Maternity'),
    ]
    PRIMARY_DIM_CHOICES = [
        ('BUST','Bust girth'),('CHEST','Chest girth'),
        ('HEIGHT_CM','Height (cm)'),('WAIST','Waist girth'),
    ]
    codi            = models.CharField(max_length=20, unique=True, choices=CODI_CHOICES)
    nom_en          = models.CharField(max_length=100)
    nom_cat         = models.CharField(max_length=100, blank=True)
    nom_es          = models.CharField(max_length=100, blank=True)
    age_min_months  = models.IntegerField(null=True, blank=True)
    age_max_months  = models.IntegerField(null=True, blank=True)
    primary_dimension = models.CharField(max_length=20, choices=PRIMARY_DIM_CHOICES, default='BUST')
    display_order   = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.nom_en

    @property
    def is_adult(self):
        return self.age_min_months is None

    @property
    def is_baby(self):
        return self.age_max_months is not None and self.age_max_months <= 36


class ConstructionType(models.Model):
    """Fabric construction type. Determines grading and tolerances."""
    CODI_CHOICES = [
        ('WOVEN','Woven (Pla)'),
        ('KNIT','Knit (Punt Jersey)'),
        ('STRETCH_KNIT','Stretch Knit (Punt Elastic)'),
        ('TECHNICAL','Technical'),
    ]
    codi                    = models.CharField(max_length=20, unique=True, choices=CODI_CHOICES)
    nom_en                  = models.CharField(max_length=100)
    nom_cat                 = models.CharField(max_length=100, blank=True)
    nom_es                  = models.CharField(max_length=100, blank=True)
    mesures_en_mitja        = models.BooleanField(default=False,
                                help_text="Knit specs typically use HALF measurements")
    tolerancia_critica_cm   = models.DecimalField(max_digits=4, decimal_places=2, default=0.6)
    tolerancia_secundaria_cm= models.DecimalField(max_digits=4, decimal_places=2, default=0.6)
    display_order           = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.nom_en


class BodyMeasurementISO(models.Model):
    """Body measurements defined by ISO 8559-1:2017. Public schema."""
    CATEGORIA_CHOICES = [
        ('VERTICAL','Vertical measurements (§5.1)'),
        ('WIDTH_DEPTH','Widths and depths (§5.2)'),
        ('GIRTH','Girth / circumference (§5.3)'),
        ('SURFACE','Surface measurements (§5.4)'),
        ('HAND_FOOT','Hand and foot (§5.5)'),
        ('OTHER','Other (§5.6)'),
        ('CALCULATED','Calculated (§5.7)'),
    ]
    codi_iso        = models.CharField(max_length=20, blank=True,
                        help_text="Referencia ISO 8559-1 — ex: 5.3.4")
    codi_intern     = models.CharField(max_length=50, unique=True,
                        help_text="Codi FHORT intern — ex: BUST_GIRTH")
    nom_en          = models.CharField(max_length=200,
                        help_text="Nom EN (idioma de treball)")
    nom_cat         = models.CharField(max_length=200, blank=True)
    nom_es          = models.CharField(max_length=200, blank=True)
    categoria       = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    htm_en          = models.TextField(blank=True,
                        help_text="How To Measure — instruccions completes EN")
    figura_iso      = models.CharField(max_length=20, blank=True,
                        help_text="Figura de la norma — ex: Fig. 62")
    es_primaria_iso = models.BooleanField(default=False,
                        help_text="Es dimensio primaria per designacio de talla (ISO 8559-2)")
    actiu           = models.BooleanField(default=True)

    class Meta:
        ordering = ['categoria', 'codi_iso']

    def __str__(self):
        return f"{self.codi_iso} — {self.nom_en}"


class SizingProfile(models.Model):
    """
    Sizing profile: combination target+garment+construction+fit -> size_system+grading.
    Public (global) schema — tenants can create their own versions via parent_profile.
    """
    target           = models.ForeignKey('Target', on_delete=models.PROTECT,
                         related_name='sizing_profiles')
    garment_type     = models.ForeignKey('GarmentType', on_delete=models.PROTECT,
                         related_name='sizing_profiles')
    construction     = models.ForeignKey('ConstructionType', on_delete=models.PROTECT,
                         related_name='sizing_profiles')
    fit_type         = models.ForeignKey('FitType', on_delete=models.PROTECT,
                         related_name='sizing_profiles')
    # L'àmbit SÍ que declara sistema de talles: un perfil diu en quina escala viu la combinació.
    size_system      = models.ForeignKey('SizeSystem', on_delete=models.PROTECT,
                         related_name='sizing_profiles')
    # C3 (2026-07-23) — NULLABLE. Un SizingProfile és, abans que res, una declaració d'ÀMBIT
    # (aquesta família aplica a aquest target amb aquesta construcció i aquest fit): és el que
    # consumeix el filtre de compatibilitat del wizard (`pom/views.py:121-132`). La graduació és
    # un SUGGERIMENT que el perfil pot portar, no la seva raó de ser. Obligar-la volia dir que
    # declarar àmbit de catàleg exigia inventar-se una graduació — contradicció amb la llei de
    # sobirania (el catàleg proposa, el model disposa). Mateix patró que el camp germà
    # `GarmentTypeItem.grading_rule_set` (tasks/models.py:329). on_delete=PROTECT es manté:
    # esborrar un ruleset referenciat segueix passant pel consentiment informat de
    # `GradingRuleSetViewSet.destroy` (pom/views.py:218-253).
    grading_rule_set = models.ForeignKey('GradingRuleSet', on_delete=models.PROTECT,
                         null=True, blank=True,
                         related_name='sizing_profiles')
    # Eix client (DIAGNOSI_BIBLIOTECA_CLIENT_2026-07-08): NULL = perfil genèric del tenant;
    # informat = perfil propi del client. db_constraint=False perquè `pom` és SHARED+TENANT i
    # `tasks.Customer` és tenant-only → la FK creua schemas (mateix patró que CustomerPOMAlias
    # i GradingRuleSet.customer). SET_NULL: esborrar un Customer no ha d'endur-se el perfil.
    customer         = models.ForeignKey('tasks.Customer', on_delete=models.SET_NULL,
                         null=True, blank=True, db_constraint=False,
                         related_name='sizing_profiles')
    is_default       = models.BooleanField(default=True,
                         help_text="El sistema suggereix aquest perfil per defecte")
    parent_profile   = models.ForeignKey('self', null=True, blank=True,
                         on_delete=models.SET_NULL, related_name='versions',
                         help_text="NULL = perfil estandard. Apunta al pare si es versio client.")
    version          = models.IntegerField(default=1)
    modified_by_id   = models.IntegerField(null=True, blank=True,
                         help_text="ID de l'usuari que ha modificat (cross-schema)")
    modified_at      = models.DateTimeField(null=True, blank=True)
    notes            = models.TextField(blank=True)

    class Meta:
        ordering = ['target__display_order', 'garment_type__nom_client']
        # CAT2.3 (2026-08-07) · el deute §7.4.2, tancat. Les 5 files que la violaven es van
        # esborrar a `0070` amb la decisió d'Agus (539 es queda del grup A; 288 del grup B).
        # ⚠️ Conseqüència assumida: una VERSIÓ (`parent_profile`) del mateix àmbit ja no és
        # possible sense canviar `customer` — el cas del 510 era exactament aquest.
        unique_together = [('target', 'garment_type', 'construction', 'fit_type',
                            'size_system', 'customer')]

    #: Els camps que fan que dos perfils siguin EL MATEIX àmbit.
    CLAU_NATURAL = ('target_id', 'garment_type_id', 'construction_id',
                    'fit_type_id', 'size_system_id', 'customer_id')

    def __str__(self):
        return (f"{self.target.nom_en} | {self.garment_type.nom_en} | "
                f"{self.construction.nom_en} | {self.fit_type.nom_en}")

    def clean(self):
        """Frena la proliferació sense tocar les 5 files que ja hi són.

        Un perfil és una declaració d'ÀMBIT. Dos perfils amb el mateix àmbit no diuen dues
        coses: diuen la mateixa dues vegades, i llavors «quin mana?» no té resposta. Això
        bloqueja els NOUS; els que ja existeixen es queden fins que l'Agus decideixi.
        """
        from django.core.exceptions import ValidationError

        super().clean()
        clau = {c: getattr(self, c) for c in self.CLAU_NATURAL}
        germans = SizingProfile.objects.filter(**clau)
        if self.pk:
            germans = germans.exclude(pk=self.pk)
        if germans.exists():
            raise ValidationError(
                'Ja hi ha un perfil per a aquest àmbit (mateix target, família, construcció, '
                f'fit, sistema de talles i client): id {germans.first().pk}. Edita aquell en '
                'comptes de duplicar-lo.'
            )


class GradingRuleHistory(models.Model):
    """
    Change history for a GradingRule.
    Records who changed which POM, from which value to which, and when.
    """
    rule_set        = models.ForeignKey('GradingRuleSet', on_delete=models.CASCADE,
                        related_name='history')
    pom             = models.ForeignKey('POMGlobal', on_delete=models.SET_NULL,
                        null=True, related_name='rule_history')
    pom_codi        = models.CharField(max_length=20, blank=True,
                        help_text="Codi POM cached per si el POM s'elimina")
    valor_anterior  = models.DecimalField(max_digits=6, decimal_places=2)
    valor_nou       = models.DecimalField(max_digits=6, decimal_places=2)
    logica_anterior = models.CharField(max_length=20, blank=True)
    logica_nova     = models.CharField(max_length=20, blank=True)
    modificat_per_id = models.IntegerField(null=True, blank=True,
                        help_text="ID usuari cross-schema")
    modificat_per_nom = models.CharField(max_length=200, blank=True)
    modificat_at    = models.DateTimeField(auto_now_add=True)
    nota            = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-modificat_at']

    def __str__(self):
        return (f"{self.pom_codi}: {self.valor_anterior} → {self.valor_nou} "
                f"({self.modificat_at.strftime('%Y-%m-%d %H:%M')})")
