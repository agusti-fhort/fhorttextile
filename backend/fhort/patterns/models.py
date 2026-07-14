"""Models del motor de patrons — la projecció persistida del model geomètric.

Aquests models NO són el motor: el motor són les dataclasses d'`engine/geometry.py`,
que no saben què és Django. Això és on el resultat de llegir un fitxer es queda a viure,
i l'`adapters.DjangoGeometryStore` és l'únic que tradueix entre les dues bandes.

Dues lleis heretades de la diagnosi S0, que es calquen a consciència:

  · **La cadena de versions.** `versio` / `is_current` / `versio_anterior`, exactament com
    `ModelFitxer` (S0-B1). L'escriu un sol lloc (`services.save_pattern_file`), mai el
    serializer.
  · **La sobirania del Model.** Un patró pertany a un Model o a un ítem de catàleg, mai
    a tots dos ni a cap: el `CheckConstraint` XOR ho fa complir a la base de dades, no
    a la bona voluntat de qui escrigui.

I una llei nova, que S0 va identificar com a risc heretat i aquí NO es calca:
`ModelFitxer` deixa que una cadena **bifurqui** (dos fitxers amb el mateix
`versio_anterior`), i `get_version_chain` només en veu una branca. Aquí un
`UniqueConstraint` sobre `versio_anterior` ho impedeix a la BD. Els NULL no hi
compten —Postgres els considera tots distints—, així que hi pot haver tantes cadenes
com calgui, però cap amb dos futurs.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


def pattern_file_upload_to(instance, filename):
    """Relatiu al TENANT: el prefix del schema el posa TenantFileSystemStorage (S0-B1.3)."""
    return f'pattern_files/{filename}'


class PatternFile(models.Model):
    """Un patró CAD pujat: el DXF, el seu RUL germà si n'hi ha, i què n'hem entès.

    El DXF i el RUL són **germans però no el mateix artefacte** (esmena E3): el primer
    porta la geometria i el segon la taula de grading. Van en dos FileField perquè es
    poden pujar per separat i es descarreguen per separat.
    """

    # ── A qui pertany (XOR: exactament un dels dos) ──────────────────────────
    model = models.ForeignKey(
        'models_app.Model', on_delete=models.CASCADE,
        null=True, blank=True, related_name='pattern_files',
    )
    garment_type_item = models.ForeignKey(
        'tasks.GarmentTypeItem', on_delete=models.CASCADE,
        null=True, blank=True, related_name='pattern_files',
        help_text='Patró de biblioteca (base de catàleg). La seva autoria és post-traçadora.',
    )
    #: D'on ve aquesta còpia, si es va sembrar des del catàleg. `GarmentTypeItemAsset` NO
    #: existeix (S0-B2): qui fa de biblioteca d'actius d'ítem és `ItemFitxer`.
    source_asset = models.ForeignKey(
        'models_app.ItemFitxer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pattern_files_sembrats',
    )

    # ── Cadena de versions (calcada de ModelFitxer, S0-B1) ───────────────────
    versio = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True, db_index=True)
    versio_anterior = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='versions_posteriors',
    )

    # ── Els bytes ────────────────────────────────────────────────────────────
    nom_fitxer = models.CharField(max_length=255)
    fitxer_dxf = models.FileField(upload_to=pattern_file_upload_to, null=True, blank=True)
    mida_bytes = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True)
    mimetype = models.CharField(max_length=100, blank=True)

    nom_rul = models.CharField(max_length=255, blank=True)
    fitxer_rul = models.FileField(upload_to=pattern_file_upload_to, null=True, blank=True)
    mida_rul_bytes = models.BigIntegerField(default=0)
    checksum_rul = models.CharField(max_length=64, blank=True)

    # ── Què n'hem entès (l'empremta de S1) ───────────────────────────────────
    font_cad = models.CharField(max_length=40, blank=True, help_text="'polypattern', 'tuka'…")
    escala_mm = models.FloatField(
        default=1.0,
        help_text='Factor de les unitats natives del fitxer a mm.',
    )
    unitats_metode = models.CharField(
        max_length=20, blank=True,
        help_text="Com s'han sabut les unitats: header / document_text / geometry / assumed.",
    )
    unitats_confianca = models.CharField(max_length=10, blank=True)
    #: L'empremta sencera, serialitzada. És el que permet REPRODUIR el fitxer d'origen
    #: (S2): sense això, l'exportació seria un DXF qualsevol, no el DXF d'aquest client.
    empremta = models.JSONField(default=dict, blank=True)
    #: La taula de grading llegida del RUL del client, tal com venia. NO és un GradeRule
    #: projectat des del grading de l'FTT (això és S7 i és efímer): és el contingut del
    #: fitxer que ens van donar.
    grade_table = models.JSONField(null=True, blank=True)

    pujat_per = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL,
        null=True, related_name='pattern_files_pujats',
    )
    data_pujada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fitxer de patró'
        verbose_name_plural = 'Fitxers de patró'
        ordering = ['-data_pujada']
        constraints = [
            # Sobirania: o penja d'un Model, o d'un ítem de catàleg. Mai tots dos, mai cap.
            models.CheckConstraint(
                condition=(
                    Q(model__isnull=False, garment_type_item__isnull=True)
                    | Q(model__isnull=True, garment_type_item__isnull=False)
                ),
                name='patternfile_xor_model_item',
            ),
            # Anti-bifurcació: un fitxer no pot tenir dos successors. Els NULL no hi
            # compten (Postgres els tracta com a distints), o sigui que hi pot haver
            # tantes cadenes noves com calgui.
            models.UniqueConstraint(
                fields=['versio_anterior'],
                name='patternfile_un_sol_successor',
            ),
        ]

    def __str__(self):
        propietari = self.model or self.garment_type_item
        return f'{self.nom_fitxer} v{self.versio} ({propietari})'

    def clean(self):
        te_model = self.model_id is not None
        te_item = self.garment_type_item_id is not None
        if te_model == te_item:
            raise ValidationError(
                'Un patró ha de penjar exactament d\'un Model O d\'un ítem de catàleg.'
            )

    # ── Duck-type de `serve_fitxer` (S0-B1.4) ────────────────────────────────
    # La font única de bytes del projecte demana `.fitxer`, `.nom_fitxer` i `.mimetype`.
    # El DXF és l'artefacte principal, així que el compleix directament; el RUL se serveix
    # amb un proxy (views._rul_servable).
    @property
    def fitxer(self):
        return self.fitxer_dxf

    @property
    def te_rul(self) -> bool:
        return bool(self.fitxer_rul)


class PatternPiece(models.Model):
    """Una peça = un BLOCK del DXF."""

    pattern_file = models.ForeignKey(
        PatternFile, on_delete=models.CASCADE, related_name='pieces',
    )
    nom_block = models.CharField(max_length=120)
    rol = models.CharField(max_length=120, blank=True)

    #: METADADES de les vores, no les seves coordenades: [{index, role, layer, closed}].
    #: Els punts viuen a `PatternPoint` (una fila cadascun) perquè S7 els ha de poder moure
    #: d'un en un. Si les coordenades també fossin aquí, hi hauria dues veritats i una de
    #: les dues quedaria vella al primer escalat.
    contorns = models.JSONField(default=list, blank=True)

    #: Fil de la roba: {'x1','y1','x2','y2'} o null.
    grain = models.JSONField(null=True, blank=True)
    #: Metadades del CAD: piece_name, size, quantity, material, anchor…
    metadata = models.JSONField(default=dict, blank=True)
    #: Entitats de capes que no entenem, literals, per poder-les tornar a escriure.
    raw_entities = models.JSONField(default=list, blank=True)
    #: Eix de doblec, si la peça venia a mitges: {'eix_x1',…,'materialitzat','costat'}.
    doblec_original = models.JSONField(null=True, blank=True)
    insert_at = models.JSONField(default=list, blank=True)

    #: Flags de CAPACITAT. Es constaten en llegir; no s'assumeixen mai.
    has_sew = models.BooleanField(default=False)
    has_fold = models.BooleanField(default=False)
    unknown_layers = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = 'Peça de patró'
        verbose_name_plural = 'Peces de patró'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['pattern_file', 'nom_block'],
                name='patternpiece_block_unic_per_fitxer',
            ),
        ]

    def __str__(self):
        return f'{self.nom_block} ({self.pattern_file_id})'


class PatternPoint(models.Model):
    """Un punt de la geometria, en mil·límetres.

    Els vèrtexs pertanyen a una vora (`boundary_index` + `ordre`); els piquets no
    pertanyen a cap i tenen `boundary_index` a null.
    """

    MENA_VERTEX = 'vertex'
    MENA_NOTCH = 'notch'
    MENA_CHOICES = [(MENA_VERTEX, 'Vèrtex'), (MENA_NOTCH, 'Piquet')]

    TIPUS_TURN = 'turn'
    TIPUS_CURVE = 'curve'
    TIPUS_UNCLASSIFIED = 'unclassified'
    TIPUS_CHOICES = [
        (TIPUS_TURN, 'Gir'),
        (TIPUS_CURVE, 'Corba'),
        (TIPUS_UNCLASSIFIED, 'Sense classificar'),
    ]

    piece = models.ForeignKey(PatternPiece, on_delete=models.CASCADE, related_name='points')
    mena = models.CharField(max_length=10, choices=MENA_CHOICES, default=MENA_VERTEX)
    boundary_index = models.IntegerField(null=True, blank=True)
    ordre = models.PositiveIntegerField(default=0)

    x = models.FloatField()
    y = models.FloatField()
    tipus = models.CharField(max_length=15, choices=TIPUS_CHOICES, default=TIPUS_UNCLASSIFIED)

    #: Regla de grading que el CAD ha assignat al punt (el TEXT '# 1' assegut al damunt).
    #: Al material real només en porten els punts de GIR i els piquets: els de corba no es
    #: graden, flueixen entre els que sí. Per això és nullable i no és un error que ho sigui.
    grade_rule_num = models.IntegerField(null=True, blank=True)
    rastre = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = 'Punt de patró'
        verbose_name_plural = 'Punts de patró'
        ordering = ['piece', 'mena', 'boundary_index', 'ordre', 'id']
        indexes = [
            models.Index(fields=['piece', 'boundary_index', 'ordre']),
        ]

    def __str__(self):
        return f'({self.x:.1f}, {self.y:.1f}) {self.tipus}'


class PatternSegment(models.Model):
    """Un tram d'una vora, en coordenades paramètriques.

    És la manera d'ancorar coses (costures, POMs) a una vora sense clavar-les a un índex
    de vèrtex: si la geometria es mou, el tram continua sent el mateix tram.

    Els segments AUTO es deriven **de gir a gir** sobre el contorn de tall (S6): els punts
    de gir són les cantonades que el patronista reconeix com a fronteres —sisa, costat,
    escot—, i entre dos girs hi ha una vora amb sentit. Els punts de corba no en són
    frontera: flueixen per dins del tram.

    **Però la segmentació gir→gir és una PROPOSTA, no la veritat de la costura** (Taller de
    patró, W1). El CAD marca les cantonades que li convenen, no les que el patronista cus:
    una costura lateral pot acabar a mig tram auto, i dos trams auto poden ser una sola
    costura. Per això un segment pot ser DECLARAT: el patronista tria dos punts qualssevol
    de la mateixa vora i diu "això és la costura lateral".

    Un segment declarat és una REFERÈNCIA a la vora que ja hi és, mai geometria nova: no
    dibuixa res, delimita. Els seus extrems són punts existents i la seva longitud és el
    recorregut de la vora entre ells.
    """

    ORIGEN_AUTO = 'auto'
    ORIGEN_DECLARAT = 'declarat'
    ORIGEN_CHOICES = [
        (ORIGEN_AUTO, 'Derivat (gir a gir)'),
        (ORIGEN_DECLARAT, 'Declarat pel patronista'),
    ]

    piece = models.ForeignKey(PatternPiece, on_delete=models.CASCADE, related_name='segments')
    vora = models.IntegerField(help_text='Índex de la vora dins la peça (boundary_index).')
    #: 0.0–1.0 sobre la longitud de la vora. **`t_fi` < `t_inici` vol dir que el tram passa
    #: per l'origen de la vora** (només possible en una vora tancada): és el cas d'un tram
    #: declarat que travessa el punt on la polilínia tanca. Qui en calculi la longitud ha de
    #: fer servir `engine.segments.fraccio_tram`, no una resta.
    t_inici = models.FloatField(help_text='0.0–1.0 sobre la longitud de la vora.')
    t_fi = models.FloatField()
    tipus_vora = models.CharField(max_length=15, blank=True)

    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default=ORIGEN_AUTO)
    #: Nom lliure del patronista ("costura lateral", "sisa davant"). Només té sentit als
    #: declarats: un tram derivat no l'ha batejat ningú.
    nom = models.CharField(max_length=120, null=True, blank=True)

    class Meta:
        verbose_name = 'Segment de patró'
        verbose_name_plural = 'Segments de patró'
        ordering = ['piece', 'vora', 't_inici']

    def __str__(self):
        etiqueta = self.nom or f'vora {self.vora}'
        return f'{etiqueta} [{self.t_inici:.2f}–{self.t_fi:.2f}] ({self.origen})'


class PatternPOM(models.Model):
    """Un POM ancorat a la geometria: la capa que val.

    Això és el que converteix un DXF mort en un patró que sap què mesura. La geometria
    sola diu on són els punts; el POM ancorat diu que la distància entre AQUESTS dos
    punts **és** l'amplada de pit, i que quan el grading digui que l'amplada de pit
    creix 2 cm, són aquests punts els que s'han de moure.

    És una RELACIÓ sobre geometria existent, mai geometria nova (frontera §3.3 del pla):
    marcar un POM no dibuixa res, assenyala.
    """

    #: Mesura entre dos punts ancorats.
    MODE_POINTS = 'points'
    #: Mesura des d'un punt derivat ("1 cm sota el punt de sisa"). Es persisteix i es
    #: resol des de S6, però la UI v1 només ofereix el mode de punts: el mode landmark
    #: entra amb l'editor de receptes, no abans.
    MODE_LANDMARK = 'landmark'

    pattern_piece = models.ForeignKey(
        PatternPiece, on_delete=models.CASCADE, related_name='poms',
    )
    #: PROTECT: un POM del catàleg que algú ha ancorat a un patró no es pot esborrar
    #: sense adonar-se'n. La geometria en depèn.
    pom_master = models.ForeignKey(
        'pom.POMMaster', on_delete=models.PROTECT, related_name='pattern_poms',
    )

    #: La recepta. Dues formes, v1:
    #:   {"mode": "points",   "a": <PatternPoint.id>, "b": <PatternPoint.id>}
    #:   {"mode": "landmark", "landmark": <PatternPoint.id>, "offset_cm": 1.0,
    #:    "direccio": "down", "b": <PatternPoint.id>}
    definicio_mesura = models.JSONField(default=dict)

    #: LLEGIT de la geometria, mai teclejat. Si algú el pogués editar, deixaria de ser
    #: una mesura del patró per ser una opinió sobre el patró.
    valor_mesurat_cm = models.FloatField(null=True, blank=True)

    #: Com s'ha mesurat: recta entre punts, o longitud resseguint la vora.
    METODE_RECTA = 'recta'
    METODE_VORA = 'vora'
    METODE_CHOICES = [(METODE_RECTA, 'Distància recta'), (METODE_VORA, 'Longitud per vora')]
    metode = models.CharField(max_length=10, choices=METODE_CHOICES, default=METODE_RECTA)

    creat_per = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pattern_poms_creats',
    )
    data_creacio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'POM ancorat'
        verbose_name_plural = 'POMs ancorats'
        ordering = ['pattern_piece', 'pom_master']
        constraints = [
            # Un POM es mesura UNA vegada per peça. Dos ancoratges del mateix POM a la
            # mateixa peça serien dues veritats sobre la mateixa mesura.
            models.UniqueConstraint(
                fields=['pattern_piece', 'pom_master'],
                name='patternpom_un_ancoratge_per_peca',
            ),
        ]

    def __str__(self):
        return f'{self.pom_master_id} @ {self.pattern_piece_id} = {self.valor_mesurat_cm} cm'


class ExportAcknowledgement(models.Model):
    """El gate humà: algú ha llegit l'avís i s'ha fet responsable d'aquesta exportació.

    **És una PRECONDICIÓ DURA, no un registre a posteriori.** Sense una fila d'aquestes no
    surt ni un byte de niada. La raó no és burocràtica: el que exportem és un fitxer que
    una màquina de tallar pot convertir en tela tallada, i entre el nostre motor i la taula
    de tall hi ha d'haver una persona que hagi dit «sí, jo ho he mirat».

    El que es desa és el que caldria per reconstruir la decisió mesos després: **qui** va
    exportar, **quan**, de **quina versió** del patró, amb **quin grading** (la versió
    exacta, que és tota la gràcia del pinçament), cap a quin CAD, i —això és el que fa que
    l'acte sigui un acte i no un clic— **el text literal que se li va ensenyar**. Si el
    text canvia (i canviarà: avui és PROVISIONAL, pendent d'advocat), els reconeixements
    vells continuen dient què va acceptar cadascú de debò, i no el que avui diríem que va
    acceptar.
    """

    pattern_file = models.ForeignKey(
        PatternFile, on_delete=models.CASCADE, related_name='export_acknowledgements',
    )
    #: La versió del patró, COPIADA (no derivada per FK). Si el `PatternFile` s'esborra o
    #: la cadena es reescriu, aquesta fila ha de continuar sabent de què parlava.
    versio_patro = models.PositiveIntegerField()

    #: PROTECT: la versió de grading amb què es va exportar no es pot esborrar mentre hi
    #: hagi un fitxer al món que se'n va derivar. És l'única manera de tornar a generar
    #: exactament aquell fitxer.
    grading_version = models.ForeignKey(
        'fitting.GradingVersion', on_delete=models.PROTECT,
        related_name='pattern_export_acknowledgements',
    )
    destination_profile = models.CharField(max_length=40)

    usuari = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL, null=True,
        related_name='pattern_exports_reconeguts',
    )
    data = models.DateTimeField(auto_now_add=True, db_index=True)

    #: El text EXACTE que l'usuari va veure i acceptar, literal. No una clau i18n: el text.
    texts_shown = models.TextField()

    class Meta:
        verbose_name = 'Reconeixement d\'exportació'
        verbose_name_plural = 'Reconeixements d\'exportació'
        ordering = ['-data']
        indexes = [
            models.Index(fields=['pattern_file', '-data']),
        ]

    def __str__(self):
        return (
            f'{self.pattern_file_id} v{self.versio_patro} · grading '
            f'{self.grading_version_id} · {self.data:%Y-%m-%d %H:%M}'
        )


class SewRelation(models.Model):
    """Una costura: quins trams d'una peça es cusen amb quins d'una altra.

    **Penja del MODEL, no de la peça**, perquè cosir és una operació de MUNTATGE: hi
    intervenen dues peces i cap de les dues n'és propietària. Una costura que pengés
    d'una peça seria mitja costura.

    N-a-N a cada costat perquè el món és així: una màniga es cus contra una sisa que és
    la suma de dos trams (davanter i esquena).
    """

    TIPUS_CASAT = 'casat'
    TIPUS_FRUNZIT = 'frunzit'
    TIPUS_PINCA = 'pinca'
    TIPUS_CHOICES = [
        (TIPUS_CASAT, 'Casat'),
        (TIPUS_FRUNZIT, 'Frunzit'),
        (TIPUS_PINCA, 'Pinça'),
    ]

    model = models.ForeignKey(
        'models_app.Model', on_delete=models.CASCADE, related_name='sew_relations',
    )
    segments_a = models.ManyToManyField(
        PatternSegment, related_name='sew_relations_a',
    )
    segments_b = models.ManyToManyField(
        PatternSegment, related_name='sew_relations_b',
    )
    tipus = models.CharField(max_length=10, choices=TIPUS_CHOICES, default=TIPUS_CASAT)

    #: El BATEIG. Buit vol dir «el nom te'l generes tu», i es genera dels dos trams que uneix
    #: («Lateral davanter ⛓ Costura lateral darrera»). Per això aquí NO s'hi desa mai el nom
    #: generat: si s'hi desés, seria un string congelat, i el dia que algú reanomenés un tram
    #: la costura continuaria dient el nom vell. Els noms es REFERENCIEN (via els M2M), no es
    #: copien.
    #:
    #: I quan algú la bateja a mà, el bateig mana i es conserva: un nom que una persona ha
    #: triat no el pot trepitjar un generador.
    nom = models.CharField(
        max_length=160, blank=True,
        help_text='Nom triat a mà. Buit: es genera dels trams que uneix.',
    )

    #: Diferència de longitud ESPERADA entre els dos costats.
    #: En un CASAT ha de ser 0: si els dos costats no fan el mateix, és un error del
    #: patró. En un FRUNZIT o una PINÇA, el diferencial és la instrucció de muntatge
    #: (aquesta és la tela que s'ha d'arronsar), no un defecte. La mateixa xifra vol dir
    #: coses oposades segons el tipus, i el motor ho ha de saber (V1 §5.3.3).
    diferencial_cm = models.FloatField(default=0.0)

    notes = models.TextField(blank=True)
    creat_per = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sew_relations_creades',
    )
    data_creacio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Costura'
        verbose_name_plural = 'Costures'
        ordering = ['model', 'id']

    def __str__(self):
        return f'{self.get_tipus_display()} (model {self.model_id})'


class SewProposalRejection(models.Model):
    """Una costura que el motor va proposar i una persona va dir que NO.

    **El rebuig és l'altra meitat de la proposta.** Un motor que proposa i no escolta el «no»
    torna a proposar el mateix a cada recàrrega, i el patronista aprèn a no mirar la llista —que
    és la manera més segura de matar una eina d'assistència. Per això el rebuig es DESA.

    Es desa la PARELLA DE TRAMS, no la proposta: una proposta no és una fila de cap taula, és el
    resultat d'un càlcul que es refà cada cop que la geometria canvia. El que persisteix és el
    judici humà sobre dos trams concrets («aquests dos no es cusen»), i això sí que és un fet
    estable. La clau és canònica (el segment d'id més petit sempre a `segment_a`): una costura no
    té un costat A i un costat B de veritat, i desar-la en l'ordre en què va arribar faria que la
    mateixa parella, mirada de l'altra banda, tornés a sortir com si ningú no l'hagués rebutjada.

    **Un rebuig no bloqueja els trams.** Dir que no a «màniga ⛓ màniga» ha de deixar la màniga
    lliure per a la proposta bona: el que es rebutja és la PARELLA, no els seus trams.

    Els trams són `PatternSegment` derivats (origen `auto`), que es refan en pujar una versió
    nova del patró: un rebuig, doncs, val per a la geometria sobre la qual es va emetre, i una
    versió nova torna a preguntar. És el que ha de passar —la geometria nova pot fer certa la
    parella que a l'anterior era absurda—, i el CASCADE de les FK ho executa tot sol.
    """

    model = models.ForeignKey(
        'models_app.Model', on_delete=models.CASCADE, related_name='sew_proposal_rejections',
    )
    segment_a = models.ForeignKey(
        PatternSegment, on_delete=models.CASCADE, related_name='rebuigs_com_a',
    )
    segment_b = models.ForeignKey(
        PatternSegment, on_delete=models.CASCADE, related_name='rebuigs_com_b',
    )

    #: Per què no. Opcional: obligar a justificar un rebuig faria que la gent no rebutgés, i el
    #: silenci d'una llista plena de propostes mortes és pitjor que un rebuig sense motiu.
    motiu = models.TextField(blank=True)
    rebutjat_per = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sew_proposals_rebutjades',
    )
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Proposta de costura rebutjada'
        verbose_name_plural = 'Propostes de costura rebutjades'
        ordering = ['-data']
        constraints = [
            models.UniqueConstraint(
                fields=['segment_a', 'segment_b'],
                name='sewproposalrejection_una_per_parella',
            ),
        ]

    def __str__(self):
        return f'{self.segment_a_id} ⛓ {self.segment_b_id}: NO (model {self.model_id})'


class DartProposalRejection(models.Model):
    """Una pinça que el motor va proposar i una persona va dir que NO.

    Germà de `SewProposalRejection`, i deliberadament un GERMÀ i no una fila més d'aquella taula:
    el que identifica una pinça rebutjada són TRES punts (la boca i el vèrtex), i el que
    identifica una costura rebutjada són DOS trams. Encabir-ho tot en una taula obligaria a deixar
    columnes buides segons la mena, i a preguntar-se sempre quina mena de rebuig s'està llegint.

    La resta de la llei és idèntica, perquè el problema és idèntic: un motor que proposa i no
    escolta el «no» torna a proposar el mateix a cada recàrrega, i el patronista aprèn a no mirar
    la llista. La clau és CANÒNICA (els dos extrems de la boca ordenats: una V llegida a l'inrevés
    és la mateixa V), i el rebuig val per a la geometria sobre la qual es va emetre — una versió
    nova del patró refà els punts i torna a preguntar, que és el que ha de passar.
    """

    model = models.ForeignKey(
        'models_app.Model', on_delete=models.CASCADE, related_name='dart_proposal_rejections',
    )
    #: Els TRES punts del gest de W4b: inici de la boca, vèrtex, final de la boca.
    punt_a = models.ForeignKey(
        PatternPoint, on_delete=models.CASCADE, related_name='rebuigs_pinca_com_a',
    )
    punt_vertex = models.ForeignKey(
        PatternPoint, on_delete=models.CASCADE, related_name='rebuigs_pinca_com_vertex',
    )
    punt_b = models.ForeignKey(
        PatternPoint, on_delete=models.CASCADE, related_name='rebuigs_pinca_com_b',
    )

    motiu = models.TextField(blank=True)
    rebutjat_per = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dart_proposals_rebutjades',
    )
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Proposta de pinça rebutjada'
        verbose_name_plural = 'Propostes de pinça rebutjades'
        ordering = ['-data']
        constraints = [
            models.UniqueConstraint(
                fields=['punt_a', 'punt_vertex', 'punt_b'],
                name='dartproposalrejection_una_per_pinca',
            ),
        ]

    def __str__(self):
        return (f'{self.punt_a_id}→{self.punt_vertex_id}→{self.punt_b_id}: NO '
                f'(model {self.model_id})')
