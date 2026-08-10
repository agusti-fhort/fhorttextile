from django.db import models
from django.conf import settings

from fhort.models_app.models import Model


class SizeFitting(models.Model):
    TIPUS_CHOICES = [
        ('Proto', 'Proto'),
        ('Fit', 'Fit'),
        ('SizeSet', 'SizeSet'),
        ('PP', 'PP'),
        ('TOP', 'TOP'),
    ]
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('BaseOberta', 'Base oberta'),
        ('BaseTancada', 'Base tancada'),
        ('TallesGenerades', 'Talles generades'),
        ('Tancat', 'Tancat'),
    ]

    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='size_fittings')
    numero = models.PositiveIntegerField()
    codi = models.CharField(max_length=60, unique=True)
    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES)
    sf_pare = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fills',
    )

    estat = models.CharField(max_length=30, choices=ESTAT_CHOICES, default='Pendent')

    data_creacio = models.DateTimeField(auto_now_add=True)
    data_tancament = models.DateTimeField(null=True, blank=True)
    creat_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.PROTECT,
        related_name='size_fittings_creats',
    )

    notes = models.TextField(null=True, blank=True)

    # --- Sprint 1A: new fields ---
    base_tancada = models.BooleanField(default=False)
    data_tancament_base = models.DateTimeField(null=True, blank=True)
    # --- End Sprint 1A ---

    class Meta:
        verbose_name = 'Size & Fitting'
        verbose_name_plural = 'Size & Fittings'
        ordering = ['model', 'numero']
        unique_together = [('model', 'numero')]

    def __str__(self):
        return self.codi


class GradingVersion(models.Model):
    size_fitting = models.ForeignKey(SizeFitting, on_delete=models.CASCADE, related_name='grading_versions')
    nom = models.CharField(max_length=100, blank=True, default='')
    aprovada = models.BooleanField(default=False)
    data = models.DateTimeField(auto_now_add=True)
    creat_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.PROTECT,
        related_name='grading_versions_creades',
        null=True, blank=True,
    )
    notes = models.TextField(null=True, blank=True)

    # Sprint 3 — grading engine
    version_number = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    # Sprint 5B.4 — production seal (set by advance_phase when a gate is passed).
    # `aprovada` = sealed as production; who/when for the manual decision.
    aprovada_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        related_name='grading_versions_aprovades',
        null=True, blank=True,
    )
    data_aprovacio = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Versió de grading'
        verbose_name_plural = 'Versions de grading'
        ordering = ['size_fitting', '-data']
        constraints = [
            # R7 (G6-B2). UNA sola versió VIGENT per SizeFitting, i que ho digui la BD.
            #
            # El codi ja ho respectava (`bump_grading_version_and_generate` desactiva totes les
            # actives abans de crear la nova), però era una invariant de cortesia: viva només
            # mentre tothom hi passés. El motor de patrons en depèn per saber quina versió mana, i
            # una segona activa faria que dues superfícies llegissin talles diferents del mateix
            # model — el bug que G6/T1 acaba de tancar.
            #
            # CAP constraint sobre `aprovada`: l'historial d'aprovades és LEGÍTIM. Un segell vell
            # ha de poder continuar dient què es va signar aquell dia. `aprovada` i `is_active` són
            # ortogonals, i només la segona és una invariant d'unicitat.
            models.UniqueConstraint(
                fields=['size_fitting'],
                condition=models.Q(is_active=True),
                name='gradingversion_una_sola_activa_per_sf',
            ),
        ]

    def __str__(self):
        return f'{self.size_fitting.codi} · {self.nom}'


class POMAlert(models.Model):
    TIPUS_CHOICES = [
        ('desviacio', 'Desviació'),
        ('fora_rang', 'Fora de rang'),
        ('manca', 'Manca'),
        ('conflicte', 'Conflicte'),
    ]
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('Acceptat', 'Acceptat'),
        ('Corregit', 'Corregit'),
    ]

    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='pom_alerts', null=True, blank=True)
    size_fitting = models.ForeignKey(
        SizeFitting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pom_alerts',
    )
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='alerts', null=True, blank=True)
    # C4/BLOC 2 — ELS DOS EIXOS. Una alerta és el veredicte sobre UNA mesura, no sobre un POM:
    # la sisa dreta pot desviar 2 cm i l'esquerra estar dins de tolerància, i són dues coses
    # diferents que un tècnic ha de poder veure per separat. Amb la clau curta
    # (`update_or_create` per `(model, pom, size_fitting)`) les dues germanes escrivien la
    # MATEIXA alerta: l'última guanyava, i el missatge —que porta la talla i la desviació—
    # acabava descrivint una fila i titulant-ne una altra.
    #
    # NO porten comporta CHECK, i és deliberat. Les 40 comportes de C1/C1-ins són el dic que
    # aquest tram està a punt de retirar; afegir-ne dues de noves per treure-les tot seguit
    # seria fer soroll. I aquesta taula no és font de res: una alerta es DERIVA d'una mesura
    # que sí que està gatejada.
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de la mesura alertada: slug de pom.MeasurementLayer (per SLUG, mai per PK).",
    )
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic. '' és la instància única.",
    )
    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES, blank=True, default='desviacio')
    valor_detectat = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    valor_esperat = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    z_score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='Pendent')
    creat_per = models.CharField(max_length=100, default='sistema')
    data_creacio = models.DateTimeField(auto_now_add=True)
    resolt_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pom_alerts_resoltes',
    )
    data_resolucio = models.DateTimeField(null=True, blank=True)

    # Sprint S11 — extra fields for vs-spec + check-tolerances
    desviacio_cm   = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    tolerancia_cm  = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    missatge       = models.TextField(blank=True)
    origen         = models.CharField(max_length=20, default='FITTING')
    nota_resolucio = models.TextField(blank=True)
    resolt_per_user_id = models.IntegerField(null=True, blank=True,
                       help_text='ID usuari cross-schema (Sprint S11)')

    class Meta:
        verbose_name = 'Alerta POM'
        verbose_name_plural = 'Alertes POM'

    def __str__(self):
        return f'{self.model.codi_intern} · {self.pom.codi_client} ({self.tipus})'


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 4 — Fitting wizard (SFFitting/SFFittingLinia): removed in Sprint 5B.5,
# replaced by FittingSession / PieceFitting / PieceFittingLine (below).
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 3 — Grading engine output (per GradingVersion)
# ─────────────────────────────────────────────────────────────────────────────

class GradedSpec(models.Model):
    """Measurement generated per (GradingVersion, POM, talla) — grading engine output."""
    GRADING_TYPE_CHOICES = [
        ('LINEAR', 'Linear'),
        ('STEP', 'Step'),
        ('FIXED', 'Fixed'),
        ('ZERO', 'Zero'),
        ('EXCEPTION', 'Exception'),
    ]
    grading_version = models.ForeignKey(
        GradingVersion, on_delete=models.CASCADE, related_name='graded_specs',
    )
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='graded_specs')
    size_label = models.CharField(max_length=20)
    graded_value_cm = models.FloatField()
    grading_type_applied = models.CharField(max_length=20, choices=GRADING_TYPE_CHOICES)
    increment_applied_cm = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)

    # Sprint 4 / F2: measurement version this spec was generated from.
    # Null for the 84 pre-existing specs (unknown origin). The brain (dependency
    # graph) will later compare generated_from_version < model.measurements_version
    # to detect stale specs — NOT implemented here, only the link is stored.
    generated_from_version = models.IntegerField(null=True, blank=True)

    # C1 (2026-07-30) — la capa (declaració canònica a `models_app.BaseMeasurement.capa`):
    # slug de `pom.MeasurementLayer`, per SLUG i mai per PK (llei G9). La validació contra el
    # catàleg arriba a C2/C4; fins llavors mana la comporta CHECK de C1/T4, que només deixa
    # passar 'exterior'. El motor de grading NO es toca a C1: escriu el default i prou.
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
                  "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).",
    )
    # C1-ins — la instància (declaració canònica a `models_app.BaseMeasurement.instancia`).
    # L'spec és el RESULTAT d'aplicar la regla a un valor base, i el valor base ja té els dos
    # eixos: si el pit RELAXED i l'EXTENDED són dues bases, en surten dos specs. La regla, en
    # canvi, segueix sent una de sola (decisió Montse, «gradúen igual»).
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )
    # SET-2/T2 — el garment (declaració canònica a `models_app.BaseMeasurement.garment`).
    # L'spec és el RESULTAT d'aplicar la regla a un valor base, i el valor base ja porta els
    # tres eixos: si el pit del top i el de la calceta són dues bases, en surten dos specs.
    # ⚠️ La VERSIÓ, en canvi, NO travessa l'eix (D6): el fitting és del model sencer, i una
    # sola `GradingVersion` conté els specs de TOTES les peces. Un segell per peça no
    # existeix, i que no existeixi és decisió de domini, no limitació tècnica.
    garment = models.CharField(
        max_length=20, default='', db_index=True,
        help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). "
                  "'' és la peça mare, que és el Model mateix. Fins a la retirada de la "
                  "comporta només s'admet '' (comporta CHECK a BD).",
    )

    class Meta:
        verbose_name = 'Spec generat'
        verbose_name_plural = 'Specs generats'
        # C1/T3 + C1-ins/T3 — la clau incorpora la CAPA i la INSTÀNCIA
        # (v. `models_app.BaseMeasurement.Meta`).
        # SET-2/T2 — i el GARMENT (v. `models_app.BaseMeasurement.Meta`): mateixes columnes
        # + una. La VERSIÓ no hi entra (D6): una sola `GradingVersion` conté els specs de
        # totes les peces, i el segell és del model per decisió de domini.
        unique_together = [('grading_version', 'pom', 'size_label', 'capa', 'instancia',
                            'garment')]
        ordering = ['grading_version', 'pom', 'size_label']
        # ✅ C4/G1 (04/08) — LES DUES COMPORTES S'HAN RETIRAT (migració fitting/0022).
        # Aquesta taula va al MATEIX grup que `BaseMeasurement` i no a un de posterior, i el
        # motiu es va MESURAR: escriure una base de germana encadena cap al motor
        # (`generate_graded_specs`), que hi escriu els specs dins de la mateixa crida. Amb la
        # comporta d'aquí viva i la de la mesura retirada, `escalat/ajustar-talla` petava amb
        # `CheckViolation` — v. el commit `959147a5`, on va sortir de cara.
        constraints = [
            # SET-2/T2 — la comporta del garment (v. `models_app.BaseMeasurement.Meta`).
            # Aquesta taula torna a anar al MATEIX grup que la mesura, i pel motiu que ja es
            # va MESURAR amb capa i instància: escriure una base de peça encadena cap al
            # motor, que hi escriu els specs dins de la mateixa crida.
            models.CheckConstraint(
                condition=models.Q(garment=''),
                name='fitting_gradedspec_garment_gate_set2',
            ),
        ]

    def __str__(self):
        return f'v{self.grading_version_id} · {self.pom.codi_client} @ {self.size_label} = {self.graded_value_cm}cm'


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 5B.2 — Fitting cycle layer (structure only; services come in 5B.3)
# ─────────────────────────────────────────────────────────────────────────────

class FittingSession(models.Model):
    """The event: the fit model tries on the product (a set or a single piece).

    N=1 (single piece) is the common case, modelled as a session with one
    PieceFitting. The target is EITHER a GarmentSet (multi-piece) OR a Model
    (single piece), never both and never neither (XOR, enforced by CheckConstraint).
    """
    ESTAT_CHOICES = [
        ('Programada', 'Programada'),
        ('Oberta', 'Oberta'),
        ('Tancada', 'Tancada'),
        ('Anullada', 'Anul·lada'),
    ]

    garment_set = models.ForeignKey(
        'models_app.GarmentSet',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='fitting_sessions',
    )
    model = models.ForeignKey(
        'models_app.Model',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='fitting_sessions',
    )
    # Phase lives on the Model/set (Proto/Fit/SizeSet/PP/TOP); reuse its choices.
    fase = models.CharField(max_length=20, choices=Model.FASE_CHOICES)
    data = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    model_persona = models.CharField(max_length=200, blank=True, default='')
    assistents = models.CharField(max_length=300, blank=True, default='')
    lloc = models.CharField(max_length=200, blank=True, default='')
    responsable = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fitting_sessions_responsable',
    )
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='Oberta')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fitting_sessions_creades',
    )
    duracio_minuts = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Durada de la franja. Default en programar: 10 min × models.')
    attendees = models.ManyToManyField(
        'accounts.UserProfile', blank=True,
        related_name='fitting_sessions',
        help_text='Assistents interns: ocupen franja a la seva cua de planificació.')
    convocatoria = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text='UUID compartit per sessions creades juntes (bulk). Null = individual.')
    # Peça 1 — temps real del cicle (no és la franja prevista, que viu a data/start_time).
    started_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Marca real d'obertura (Programada→Oberta).")
    finished_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Marca real de tancament (→Tancada).')
    motiu_anullacio = models.TextField(
        blank=True, default='',
        help_text="Motiu d'anul·lació (estat Anullada).")

    class Meta:
        verbose_name = 'Sessió de fitting'
        verbose_name_plural = 'Sessions de fitting'
        ordering = ['-data', '-created_at']
        constraints = [
            models.CheckConstraint(
                name='fittingsession_set_xor_model',
                condition=(
                    models.Q(garment_set__isnull=False, model__isnull=True) |
                    models.Q(garment_set__isnull=True, model__isnull=False)
                ),
            ),
        ]

    def __str__(self):
        target = self.garment_set_id and self.garment_set or self.model
        return f'FittingSession {self.data} · {target} ({self.fase})'


class PieceFitting(models.Model):
    """One per piece evaluated in the session. Owns an independent gate."""
    GATE_CHOICES = [
        ('Pendent', 'Pendent'),
        ('OK', 'OK'),
        ('NO_OK', 'No OK'),
        ('EXCEPCIO', 'Excepció'),
    ]

    session = models.ForeignKey(
        FittingSession, on_delete=models.CASCADE, related_name='piece_fittings',
    )
    model = models.ForeignKey(
        'models_app.Model', on_delete=models.PROTECT, related_name='piece_fittings',
    )
    grading_version = models.ForeignKey(
        GradingVersion, on_delete=models.PROTECT, related_name='piece_fittings',
    )
    gate = models.CharField(max_length=10, choices=GATE_CHOICES, default='Pendent')
    gate_motiu = models.TextField(blank=True, default='')
    # Sprint 5B.4 — who/when set the gate (manual-decision traceability).
    gate_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        related_name='piece_fittings_gated',
        null=True, blank=True,
    )
    gate_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='piece_fittings_creats',
    )

    class Meta:
        verbose_name = 'Fitting de peça'
        verbose_name_plural = 'Fittings de peça'
        ordering = ['session', 'model']
        unique_together = [('session', 'model')]

    def __str__(self):
        return f'{self.session_id} · {self.model} [{self.gate}]'


class PieceFittingLine(models.Model):
    """A (POM, size) row: theoretical (grading) vs real (measured) — SEPARATE.

    Only the two current values are stored. The evolution across versions is read
    dynamically from the GradingVersion history, NOT materialised here.
    """
    piece_fitting = models.ForeignKey(
        PieceFitting, on_delete=models.CASCADE, related_name='linies',
    )
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='+')
    size_label = models.CharField(max_length=20)
    valor_teoric = models.FloatField()
    valor_real = models.FloatField(null=True, blank=True)
    nota = models.CharField(max_length=200, blank=True, default='')
    # D-31.21 — EL VEREDICTE DE LA MODISTA sobre aquesta cel·la.
    #
    # Els tres valors són DADA DE DOMINI i no es tradueixen, com LINEAR/STEP: són el que el
    # full imprès porta cap al fabricant (AC/AD/RJ, `FittingPrintSheet.jsx:30`) i el que es
    # diu en veu alta a la sala. Traduir-los a pantalla i no al paper faria que les dues
    # superfícies parlessin diferent.
    #
    # ⚠️ EL BUIT NO ÉS 'ACCEPTED'. Una cel·la sense decidir és una cel·la que ningú no ha
    # mirat; una acceptada és una que algú ha mirat i ha donat per bona. Per això el default
    # és '' i no el primer choice: si no es distingissin, obrir un fitting i tancar-lo sense
    # tocar res deixaria tota la graella «acceptada» sense que ningú hi hagués dit res.
    DECISIO_ACCEPTED = 'ACCEPTED'
    DECISIO_ADJUSTED = 'ADJUSTED'
    DECISIO_REJECTED = 'REJECTED'
    DECISIO_CHOICES = [
        (DECISIO_ACCEPTED, 'Acceptada — la mesura real es dona per bona'),
        (DECISIO_ADJUSTED, "Ajustada — s'ha rectificat i el valor rectificat val"),
        (DECISIO_REJECTED, 'Rebutjada — la presa no val; NO sembra res'),
    ]
    decisio = models.CharField(
        max_length=10, choices=DECISIO_CHOICES, blank=True, default='', db_index=True,
        help_text="Veredicte de la cel·la (D-31.21). '' = sense decidir, que NO és ACCEPTED. "
                  "Una línia REJECTED es desa i es veu, però cap camí de sembra la llegeix.",
    )
    # C1 — la capa (declaració canònica a `models_app.BaseMeasurement.capa`).
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
                  "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).",
    )
    # C1-ins — la instància (declaració canònica a `models_app.BaseMeasurement.instancia`).
    # La línia de fitting és on es MESURA la peça real: si la fitxa demana la sisa dreta i
    # l'esquerra, la modista pren dues xifres i aquí hi ha d'haver dues línies.
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )
    # SET-2/T2 — el garment (declaració canònica a `models_app.BaseMeasurement.garment`).
    # La línia de fitting és on es MESURA la prenda real: si el model és un pijama, la
    # modista pren les xifres de la jaqueta i les del pantaló, i aquí hi ha d'haver dues
    # línies. ⚠️ La SESSIÓ i el veredicte segueixen sent del MODEL SENCER (D6): mesurar una
    # prenda és mesurar tot el model, i no existeix «tancar el fitting del dalt».
    garment = models.CharField(
        max_length=20, default='', db_index=True,
        help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). "
                  "'' és la peça mare, que és el Model mateix. Fins a la retirada de la "
                  "comporta només s'admet '' (comporta CHECK a BD).",
    )

    class Meta:
        verbose_name = 'Línia de fitting de peça'
        verbose_name_plural = 'Línies de fitting de peça'
        ordering = ['piece_fitting', 'pom', 'size_label']
        # C1/T3 + C1-ins/T3 — la clau incorpora la CAPA i la INSTÀNCIA
        # (v. `models_app.BaseMeasurement.Meta`).
        # SET-2/T2 — i el GARMENT (v. `models_app.BaseMeasurement.Meta`): mateixes columnes
        # + una. La `PieceFitting` i la `FittingSession` es queden SENSE eix (D6).
        unique_together = [('piece_fitting', 'pom', 'size_label', 'capa', 'instancia',
                            'garment')]
        # ✅ C4/G2 (04/08) — les dues comportes retirades (migració fitting/0023). La línia
        # de fitting és on es MESURA la peça real: si la fitxa demana la sisa dreta i
        # l'esquerra, la modista pren dues xifres i aquí hi ha d'haver dues línies. El sembrat
        # les clona de l'spec amb els seus eixos (`fitting/services.py:339`), o sigui que amb
        # germanes vives crear una PieceFitting hauria petat aquí.
        constraints = [
            # SET-2/T2 — la comporta del garment (v. `models_app.BaseMeasurement.Meta`).
            models.CheckConstraint(
                condition=models.Q(garment=''),
                name='fitting_piecefittingline_garment_gate_set2',
            ),
        ]

    def __str__(self):
        return f'{self.piece_fitting_id} · {self.pom.codi_client} @ {self.size_label}'


class FittingPhoto(models.Model):
    """Autonomous photo (FileField pattern like ModelFitxer, not FitxerVersio).

    Belongs to a session; optionally pinned to a specific PieceFitting.
    """
    session = models.ForeignKey(
        FittingSession, on_delete=models.CASCADE, related_name='photos',
    )
    piece_fitting = models.ForeignKey(
        PieceFitting, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='photos',
    )
    fitxer = models.ImageField(upload_to='fitting_photos/%Y/%m/')
    caption = models.CharField(max_length=300, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foto de fitting'
        verbose_name_plural = 'Fotos de fitting'
        ordering = ['session', 'id']

    def __str__(self):
        return f'{self.session_id} · {self.caption or self.fitxer.name}'


class FittingDurationStat(models.Model):
    """Welford incremental de durada real per model de sessió (minuts). Agregat GLOBAL del
    tenant: singleton (el servei farà get_or_create(pk=1)). Mateix patró que
    pom.ClientMesuraPerfil (n_mostres / mitjana / m2_acum / desviacio)."""
    n_mostres = models.PositiveIntegerField(default=0)
    mitjana = models.FloatField(default=0.0)
    m2_acum = models.FloatField(default=0.0)   # Welford running M2
    desviacio = models.FloatField(default=0.0)
    darrera_actualitzacio = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Estadística de durada de fitting'
        verbose_name_plural = 'Estadístiques de durada de fitting'

    def __str__(self):
        return f'FittingDurationStat n={self.n_mostres} mitjana={self.mitjana:.1f}min'
