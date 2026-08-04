from rest_framework import serializers

from fhort.models_app.models import Model
from fhort.accounts.models import UserProfile

from .models import (
    GradingVersion,
    POMAlert,
    SizeFitting,
    FittingSession,
    PieceFitting,
    PieceFittingLine,
    FittingPhoto,
    GradedSpec,
)


class SizeFittingSerializer(serializers.ModelSerializer):
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    creat_per_nom = serializers.CharField(source='creat_per.nom_complet', read_only=True)
    estat_display = serializers.CharField(source='get_estat_display', read_only=True)
    #: F1 — quantes specs graduades té aquest fitting. La T1b de la fitxa es construeix des de
    #: `fitting/<id>/graded-table/`, i un fitting SENSE GradingVersion la torna buida: el modal
    #: de tria l'oferia igual i el tècnic hi topava després de triar. Amb això el modal el pot
    #: atenuar i dir per què. 0 = no hi ha graduació encara (no és un error: és un fitting que
    #: encara no s'ha graduat). Es compta sobre la versió ACTIVA, que és la que llegeix
    #: graded-table.
    n_graded_specs = serializers.SerializerMethodField()

    def get_n_graded_specs(self, obj):
        gv = obj.grading_versions.filter(is_active=True).order_by('-data').first()
        return gv.graded_specs.count() if gv else 0

    class Meta:
        model = SizeFitting
        fields = '__all__'
        read_only_fields = ('data_creacio',)


class GradingVersionSerializer(serializers.ModelSerializer):
    creat_per_nom = serializers.CharField(source='creat_per.nom_complet', read_only=True)
    #: G6-B2 — L'ESTALITUD. Una versió aprovada pot haver quedat enrere (la base ha canviat sota el
    #: segell), i el sistema ho ha de DIR: la mesura és sobirana i el segell és honest, i el preu de
    #: no mentir per cap dels dos costats és que algú s'ha d'assabentar. Es CALCULA a cada lectura
    #: sobre el registre append-only de canvis de base — no es desa, perquè un flag desat tornaria a
    #: ser una cosa més que es pot quedar estala.
    estalitud = serializers.SerializerMethodField()

    def get_estalitud(self, obj):
        from fhort.fitting.staleness import com_a_dict, estalitud
        return com_a_dict(estalitud(obj))

    class Meta:
        model = GradingVersion
        fields = '__all__'
        # G6-B/T2 — el segell NO és un camp editable. El viewset ja és ReadOnly, però el pany de
        # dalt és el que es descuida: el dia que algú hi torni a posar un ModelViewSet (era el que
        # hi havia), aquests camps han de seguir sense poder-se flipar per REST. `aprovada` només
        # l'escriu `seal_grading_version`, via l'acció `approve` (capability CLOSE_GATES).
        read_only_fields = ('data', 'aprovada', 'aprovada_per', 'data_aprovacio', 'is_active')


class POMAlertSerializer(serializers.ModelSerializer):
    pom_codi = serializers.CharField(source='pom.codi_client', read_only=True)
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    resolt_per_nom = serializers.CharField(source='resolt_per.nom_complet', read_only=True)

    class Meta:
        model = POMAlert
        fields = '__all__'
        read_only_fields = ('data_creacio',)


# ═════════════════════════════════════════════════════════════════════════════
# Sprint 5B.6 — Fitting REST API (FittingSession / PieceFitting / lines / photos)
# Read/write serializers; the service (5B.3/5B.4) holds the business logic.
# ═════════════════════════════════════════════════════════════════════════════

def _session_target(obj):
    """Derived {type, id, label} for a session's target (GarmentSet XOR Model)."""
    if obj.garment_set_id:
        return {'type': 'garment_set', 'id': obj.garment_set_id, 'label': str(obj.garment_set)}
    if obj.model_id:
        return {'type': 'model', 'id': obj.model_id, 'label': str(obj.model)}
    return None


class FittingPhotoSerializer(serializers.ModelSerializer):
    """fitxer is serialised as an (absolute, if request in context) URL by DRF."""

    class Meta:
        model = FittingPhoto
        fields = ['id', 'session', 'piece_fitting', 'fitxer', 'caption', 'created_at']
        read_only_fields = ['id', 'created_at']


class PieceFittingSummarySerializer(serializers.ModelSerializer):
    """Per-piece summary embedded in the session detail (with gate state)."""
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    model_nom = serializers.CharField(source='model.nom_prenda', read_only=True)
    gate_per_nom = serializers.CharField(source='gate_per.nom_complet', read_only=True)
    n_linies = serializers.SerializerMethodField()

    class Meta:
        model = PieceFitting
        fields = [
            'id', 'model', 'model_codi', 'model_nom', 'grading_version',
            'gate', 'gate_motiu', 'gate_per_nom', 'gate_at', 'n_linies', 'created_at',
        ]

    def get_n_linies(self, obj):
        return obj.linies.count()


class FittingSessionListSerializer(serializers.ModelSerializer):
    responsable_nom = serializers.CharField(source='responsable.nom_complet', read_only=True)
    fase_display = serializers.CharField(source='get_fase_display', read_only=True)
    estat_display = serializers.CharField(source='get_estat_display', read_only=True)
    target = serializers.SerializerMethodField()
    n_peces = serializers.IntegerField(read_only=True)  # annotated in the viewset queryset
    # Convocatòria: agrupació de sessions creades en bulk (encadenades). Null = individual.
    attendees_info = serializers.SerializerMethodField()

    class Meta:
        model = FittingSession
        fields = [
            'id', 'data', 'fase', 'fase_display', 'estat', 'estat_display',
            'model', 'garment_set', 'target', 'responsable', 'responsable_nom',
            'n_peces', 'created_at',
            'convocatoria', 'start_time', 'duracio_minuts', 'attendees_info',
        ]
        read_only_fields = ['convocatoria', 'start_time', 'duracio_minuts']

    def get_target(self, obj):
        return _session_target(obj)

    def get_attendees_info(self, obj):
        return [{'id': a.id,
                 'nom': a.user.get_full_name() or a.user.username,
                 'color_avatar': a.color_avatar or '#888888'}
                for a in obj.attendees.all()]


class FittingSessionDetailSerializer(serializers.ModelSerializer):
    responsable_nom = serializers.CharField(source='responsable.nom_complet', read_only=True)
    created_by_nom = serializers.CharField(source='created_by.nom_complet', read_only=True)
    fase_display = serializers.CharField(source='get_fase_display', read_only=True)
    estat_display = serializers.CharField(source='get_estat_display', read_only=True)
    target = serializers.SerializerMethodField()
    # Identificació rica derivada del model (read-only; default=None pel cas garment_set).
    model_codi_client = serializers.CharField(source='model.codi_client', read_only=True, default=None)
    model_temporada = serializers.CharField(source='model.temporada', read_only=True, default=None)
    model_any = serializers.IntegerField(source='model.any', read_only=True, default=None)
    piece_fittings = PieceFittingSummarySerializer(many=True, read_only=True)
    photos = FittingPhotoSerializer(many=True, read_only=True)
    can_advance = serializers.SerializerMethodField()

    class Meta:
        model = FittingSession
        fields = [
            'id', 'data', 'start_time', 'end_time', 'fase', 'fase_display', 'estat', 'estat_display',
            'model', 'garment_set', 'target',
            'model_codi_client', 'model_temporada', 'model_any',
            'model_persona', 'assistents', 'lloc',
            'responsable', 'responsable_nom', 'notes', 'created_at',
            # P4 — la sessió ha de saber de quina convocatòria ve, per tornar-hi en gravar.
            # El serializer de LLISTA ja l'exposava; el de detall no.
            'convocatoria',
            'created_by', 'created_by_nom', 'piece_fittings', 'photos', 'can_advance',
        ]

    def get_target(self, obj):
        return _session_target(obj)

    def get_can_advance(self, obj):
        from .services import session_can_advance
        return session_can_advance(obj.pk)


class FittingSessionCreateSerializer(serializers.Serializer):
    """Input for create() — the view delegates to create_session() (XOR enforced)."""
    fase = serializers.ChoiceField(choices=[c[0] for c in Model.FASE_CHOICES])
    data = serializers.DateField()
    model = serializers.IntegerField(required=False, allow_null=True)
    garment_set = serializers.IntegerField(required=False, allow_null=True)
    responsable = serializers.IntegerField(required=False, allow_null=True)
    model_persona = serializers.CharField(required=False, allow_blank=True, default='')
    assistents = serializers.CharField(required=False, allow_blank=True, default='')
    lloc = serializers.CharField(required=False, allow_blank=True, default='')
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class FittingSessionUpdateSerializer(serializers.ModelSerializer):
    """Autosave: only the event-context fields are writable. attendees (M2M, interns) i
    duracio_minuts editables; DRF gestiona el .set() de la M2M a update()."""
    attendees = serializers.PrimaryKeyRelatedField(
        many=True, queryset=UserProfile.objects.all(), required=False)
    duracio_minuts = serializers.IntegerField(
        required=False, allow_null=True, min_value=1)

    class Meta:
        model = FittingSession
        fields = ['notes', 'model_persona', 'assistents', 'lloc', 'responsable',
                  'attendees', 'duracio_minuts']


class PieceFittingLineSerializer(serializers.ModelSerializer):
    """Autosave for a grid cell: valor_real, nota i decisio editables; rest frozen."""

    class Meta:
        model = PieceFittingLine
        # D-31.21 — `decisio` va pel MATEIX camí que la nota (PATCH per línia, autosave), i no
        # per un endpoint propi: el veredicte i el comentari són el mateix gest de la modista
        # sobre la mateixa cel·la, i separar-los voldria dir dos desats per a una sola decisió.
        fields = ['id', 'piece_fitting', 'pom', 'size_label', 'valor_teoric', 'valor_real',
                  'nota', 'decisio']
        read_only_fields = ['id', 'piece_fitting', 'pom', 'size_label', 'valor_teoric']


class PieceFittingGridSerializer(serializers.ModelSerializer):
    """Retrieve: the working grid + theoretical evolution across GradingVersions."""
    model = serializers.SerializerMethodField()
    grading_version_num = serializers.IntegerField(
        source='grading_version.version_number', read_only=True)
    gate_per_nom = serializers.CharField(source='gate_per.nom_complet', read_only=True)
    lines = serializers.SerializerMethodField()

    class Meta:
        model = PieceFitting
        fields = [
            'id', 'session', 'gate', 'gate_motiu', 'gate_per_nom', 'gate_at',
            'grading_version', 'grading_version_num', 'model', 'lines', 'created_at',
        ]

    def get_model(self, obj):
        m = obj.model
        return {
            'id': m.id, 'codi': m.codi_intern, 'nom': m.nom_prenda,
            'base_size_label': m.base_size_label, 'size_run_model': m.size_run_model,
        }

    def get_lines(self, obj):
        sf = obj.grading_version.size_fitting
        # All conserved versions of this size_fitting, oldest → newest.
        versions = list(
            GradingVersion.objects.filter(size_fitting=sf).order_by('version_number')
        )
        # Single query for ALL graded specs of those versions → no N+1.
        # FASE_2/C1-ins — la clau del `spec_map` creix amb els DOS eixos. La fila que hi
        # consulta és una `PieceFittingLine`, que els porta tots dos: FORMA A, sense àncora,
        # perquè aquí hi ha de qui copiar-los. Per `(gv, pom, talla)` l'evolució de la sisa
        # dreta ensenyaria les xifres de l'esquerra a cada versió conservada — i és
        # precisament la columna que serveix per veure si una mesura s'ha mogut.
        spec_map = {}
        for s in GradedSpec.objects.filter(grading_version__size_fitting=sf).values(
            'grading_version_id', 'pom_id', 'capa', 'instancia', 'size_label',
            'graded_value_cm',
        ):
            spec_map[(s['grading_version_id'], s['pom_id'], s['capa'], s['instancia'],
                      s['size_label'])] = s['graded_value_cm']

        # PG-4b-3a — règim per POM (resident→fallback) per al desplegable + etiqueta de regla.
        from fhort.pom.services import _load_grading_rules
        rules = _load_grading_rules(obj.model)

        # BaseMeasurement del model (unique per (model, pom, capa, instancia)): aporta
        # nom_fitxa (nomenclatura client, autoritativa) i l'ordre de fitxa. Una sola query,
        # reutilitzada per al 'nom' de cada línia i per a l'ordenació final.
        #
        # C2/Onada 1 — CLAU COMPOSTA (pom, capa): `PieceFittingLine` porta capa des de C1, o
        # sigui que cada línia pot demanar la SEVA. Per POM sol, el folre i l'exterior d'un
        # mateix pit es disputarien el `nom_fitxa` i —pitjor— el `bm_id`, que és per on
        # aquesta superfície desa el bateig: s'escriuria el nom a la mesura de l'altra capa.
        # FASE_2/C1-ins — i la INSTÀNCIA hi entra amb el mateix argument, agreujat: el
        # `nom_fitxa` és justament el que distingeix la sisa dreta de l'esquerra al croquis.
        # Amb la clau curta, batejar una escriuria el nom sobre l'altra i les dues quedarien
        # amb el mateix rètol — el duplicat amb aparença de dada bona que la comporta i el
        # CHECK «instància ⇒ nom» existeixen per evitar. Els TRES mapes creixen alhora: si un
        # s'ancorés i un altre no, una fila portaria l'ordre d'una instància i el nom d'una
        # altra.
        from fhort.models_app.models import BaseMeasurement
        # F2 — `origen` entra a la MATEIXA query que ja hi era (cap consulta nova): és el que
        # C3 va construir per dir que un valor no l'ha mesurat ningú (`origen='DERIVAT'`,
        # `services_derivacio.ORIGEN_DERIVAT`), i sense ell la pantalla no pot distingir la
        # germana que el sistema ha mogut de la que ningú no ha tocat. No s'hi afegeix cap
        # camp nou: la derivació ja té identificador i és aquest.
        bm_data = list(BaseMeasurement.objects.filter(model_id=obj.model_id)
                       .values_list('pom_id', 'capa', 'instancia', 'ordre', 'nom_fitxa', 'id',
                                    'origen'))
        ordre_map = {(p, c, i): o for p, c, i, o, _, _, _ in bm_data}
        nom_fitxa_map = {(p, c, i): nf for p, c, i, _, nf, _, _ in bm_data}
        bm_id_map = {(p, c, i): bid for p, c, i, _, _, bid, _ in bm_data}  # P4 — autoria de nom a nivell MODEL
        origen_map = {(p, c, i): og for p, c, i, _, _, _, og in bm_data}

        out = []
        # Ordre de fitxa, paral·lel a `out`. C4/BLOC 1-BIS: la fila del payload SÍ que porta
        # ara els eixos, o sigui que el motiu original d'aquesta llista paral·lela ha caigut.
        # El mecanisme es queda: substituir-lo per una ordenació sobre `out` és un canvi de
        # forma que no arregla res i que aquest commit no ha de portar.
        ordres = []
        for line in obj.linies.select_related('pom', 'pom__pom_global').all():
            clau_bm = (line.pom_id, line.capa, line.instancia)
            evolucio = []
            for v in versions:
                val = spec_map.get((v.id, line.pom_id, line.capa, line.instancia,
                                    line.size_label))
                if val is None:
                    continue
                evolucio.append({
                    'version_number': v.version_number,
                    'data': v.data.isoformat() if v.data else None,
                    'aprovada': v.aprovada,
                    'is_active': v.is_active,
                    'valor_cm': val,
                })
            pom = line.pom
            r = rules.get(line.pom_id)
            ordres.append(ordre_map.get(clau_bm, 10 ** 9))
            out.append({
                'id': line.id,
                'pom_id': line.pom_id,
                # C4/BLOC 1-BIS — ELS DOS EIXOS AL CONTRACTE. Aquest serializer resolia la
                # identitat sencera de la mesura (`clau_bm`, aquí sobre) per anar a buscar el
                # nom, l'ordre i el `bm_id`… i després NO la deia. El comentari de sota, ara
                # esmenat, ho declarava: «la fila del payload no porta capa».
                #
                # El preu el pagava el frontend, i no s'hi podia fer res des d'allà: el
                # consumidor rep una llista de línies i les agrupa per POM per fer-ne files
                # (`measureSources.deriveFitting`, `FittingDetail`, `SessionPanel`). Amb dues
                # germanes vives, dues línies portaven el mateix `pom_id` i el `Map` en
                # descartava una en silenci — el mode de fallada que C4 existeix per matar,
                # però a la banda del client, on cap test de backend el podia veure.
                #
                # No s'hi afegeix cap identificador de fila: `bm_id` (unes línies més avall)
                # ja hi és i ja es resol per `clau_bm`. Un segon camp amb el mateix valor i un
                # altre nom seria fabricar la divergència que aquest fitxer combat.
                'capa': line.capa,
                'instancia': line.instancia,
                'codi': pom.pom_code if pom else '',
                'nom': (nom_fitxa_map.get(clau_bm) or (pom.pom_code if pom else '')),  # nom_fitxa (croquis)
                'nom_en': pom.name_en if pom else '',        # nom canònic EN (línia superior, nomenclatura 2 línies)
                'nom_local': pom.name_cat if pom else '',    # nom en idioma usuari (línia inferior, canònic = sembra)
                'nom_fitxa': nom_fitxa_map.get(clau_bm),      # P4 — override d'autoria a nivell MODEL (precedència)
                'bm_id': bm_id_map.get(clau_bm),              # P4 — id de BaseMeasurement per editar el nom del model
                'is_key': pom.is_key_measure if pom else False,
                'size_label': line.size_label,
                'valor_teoric': line.valor_teoric,
                'valor_real': line.valor_real,
                'nota': line.nota,
                # D-31.21 — el veredicte, que la graella ha de poder tornar a pintar en obrir.
                'decisio': line.decisio,
                # F2 — l'origen de la mesura base d'AQUESTA germana (`clau_bm` ja porta els dos
                # eixos). 'DERIVAT' = el sistema l'ha moguda perquè s'ha corregit la seva
                # germana; qualsevol altre valor amb una germana FITTED al costat vol dir que
                # aquesta NO s'ha actualitzat. La pantalla ja té tot el que cal per etiquetar-ho
                # sense demanar res més: origen + capa + instancia + decisio, línia per línia.
                'origen': origen_map.get(clau_bm),
                'evolucio': evolucio,
                # Règim per POM (mateix valor a cada talla; el front el llegeix per pom_id).
                'logica': getattr(r, 'logica', None) if r else None,
                'increment_base': float(r.increment_base) if r and r.increment_base is not None else None,
                'increment_break': float(r.increment_break) if r and r.increment_break is not None else None,
                'talla_break_label': getattr(r, 'talla_break_label', None) if r else None,
            })
        # FIX 4B — ordena les files per l'ordre de la fitxa (BaseMeasurement.ordre del model;
        # POMMaster no té 'ordre'). ordre_map ja s'ha construït a dalt amb la mateixa query.
        # C2/Onada 1 — l'ordre viatja a `ordres`, paral·lel a `out`, perquè la clau porta capa
        # i la fila del payload no en tenia. `sorted` és estable i la clau és només el número:
        # els empats conserven l'ordre d'inserció, igual que el `list.sort` d'abans.
        # C4/BLOC 1-BIS: la fila ja porta els eixos i això es podria fer sobre `out`; no es
        # canvia aquí perquè seria una refosa sense defecte que la justifiqui.
        out = [fila for _ordre, fila in sorted(zip(ordres, out), key=lambda t: t[0])]
        return out
