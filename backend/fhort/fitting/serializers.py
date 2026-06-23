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

    class Meta:
        model = SizeFitting
        fields = '__all__'
        read_only_fields = ('data_creacio',)


class GradingVersionSerializer(serializers.ModelSerializer):
    creat_per_nom = serializers.CharField(source='creat_per.nom_complet', read_only=True)

    class Meta:
        model = GradingVersion
        fields = '__all__'
        read_only_fields = ('data',)


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
    """Autosave for a grid cell: valor_real and nota editable; rest frozen."""

    class Meta:
        model = PieceFittingLine
        fields = ['id', 'piece_fitting', 'pom', 'size_label', 'valor_teoric', 'valor_real', 'nota']
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
        spec_map = {}
        for s in GradedSpec.objects.filter(grading_version__size_fitting=sf).values(
            'grading_version_id', 'pom_id', 'size_label', 'graded_value_cm',
        ):
            spec_map[(s['grading_version_id'], s['pom_id'], s['size_label'])] = s['graded_value_cm']

        # PG-4b-3a — règim per POM (resident→fallback) per al desplegable + etiqueta de regla.
        from fhort.pom.services import _load_grading_rules
        rules = _load_grading_rules(obj.model)

        # BaseMeasurement del model (unique per (model, pom)): aporta nom_fitxa (nomenclatura
        # client, autoritativa) i l'ordre de fitxa. Una sola query, reutilitzada per al 'nom' de
        # cada línia i per a l'ordenació final.
        from fhort.models_app.models import BaseMeasurement
        bm_data = list(BaseMeasurement.objects.filter(model_id=obj.model_id)
                       .values_list('pom_id', 'ordre', 'nom_fitxa'))
        ordre_map = {p: o for p, o, _ in bm_data}
        nom_fitxa_map = {p: nf for p, _, nf in bm_data}

        out = []
        for line in obj.linies.select_related('pom', 'pom__pom_global').all():
            evolucio = []
            for v in versions:
                val = spec_map.get((v.id, line.pom_id, line.size_label))
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
            out.append({
                'id': line.id,
                'pom_id': line.pom_id,
                'codi': pom.pom_code if pom else '',
                'nom': (nom_fitxa_map.get(line.pom_id) or (pom.pom_code if pom else '')),  # nom_fitxa (croquis)
                'nom_en': pom.name_en if pom else '',        # nom canònic EN (línia superior, nomenclatura 2 línies)
                'nom_local': pom.name_cat if pom else '',    # nom en idioma usuari (línia inferior)
                'is_key': pom.is_key_measure if pom else False,
                'size_label': line.size_label,
                'valor_teoric': line.valor_teoric,
                'valor_real': line.valor_real,
                'nota': line.nota,
                'evolucio': evolucio,
                # Règim per POM (mateix valor a cada talla; el front el llegeix per pom_id).
                'logica': getattr(r, 'logica', None) if r else None,
                'increment_base': float(r.increment_base) if r and r.increment_base is not None else None,
                'increment_break': float(r.increment_break) if r and r.increment_break is not None else None,
                'talla_break_label': getattr(r, 'talla_break_label', None) if r else None,
            })
        # FIX 4B — ordena les files per l'ordre de la fitxa (BaseMeasurement.ordre del model;
        # POMMaster no té 'ordre'). ordre_map ja s'ha construït a dalt amb la mateixa query.
        out.sort(key=lambda r: ordre_map.get(r['pom_id'], 10 ** 9))
        return out
