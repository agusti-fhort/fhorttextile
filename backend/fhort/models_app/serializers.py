from rest_framework import serializers

from .models import BaseMeasurement, Contracte, LiniaContracte, Model, ModelFitxer, Watchpoint


class ModelFitxerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelFitxer
        fields = '__all__'
        read_only_fields = ('data_pujada',)


class ModelListSerializer(serializers.ModelSerializer):
    garment_type = serializers.SerializerMethodField()
    responsable = serializers.SerializerMethodField()
    garment_type_item_nom = serializers.CharField(source='garment_type_item.name', read_only=True)
    # v2 albarà — client del model (per a l'acció massiva "Assignar a comanda": mateix client).
    customer_nom = serializers.CharField(source='customer.nom', read_only=True, default=None)
    # Pas 5C — dates del cicle (annotacions Subquery al queryset del ViewSet).
    entrada_prod = serializers.DateTimeField(read_only=True)
    arribada_proto = serializers.DateTimeField(read_only=True)
    fitting_prev = serializers.DateField(read_only=True)
    # Pas 5C — tècnics = assignees distints de les ModelTask (prefetch, sense N+1).
    tecnics = serializers.SerializerMethodField()

    class Meta:
        model = Model
        fields = (
            'id',
            'codi_intern',
            'codi_client',
            'nom_prenda',
            'collection',
            'temporada',
            'any',
            'customer',
            'customer_nom',
            'created_at',
            'garment_type',
            'garment_type_item_nom',
            'fase_actual',
            'responsable',
            'prioritat',
            'data_objectiu',
            # M1 — predicció del planificador (min start / max end de les tasques; §17). Read-only.
            'predicted_start',
            'predicted_end',
            # Pas 5C — cicle
            'entrada_prod',
            'arribada_proto',
            'fitting_prev',
            'tecnics',
            # Sprint 1A
            'slots_prev_tecnics',
            'slots_prev_confeccio',
            'slots_reals_tecnic',
            'slots_reals_confeccio',
        )

    def get_garment_type(self, obj):
        return obj.garment_type.nom_client if obj.garment_type_id else None

    def get_responsable(self, obj):
        return obj.responsable.nom_complet if obj.responsable_id else None

    def get_tecnics(self, obj):
        # model_tasks ve prefetchat (només tasques amb assignee) → 0 queries aquí.
        counter = {}
        for tk in obj.model_tasks.all():
            a = tk.assignee
            if not a:
                continue
            c = counter.setdefault(a.id, {'id': a.id, 'nom': a.nom_complet,
                                          'color': getattr(a, 'color_avatar', None), 'n': 0})
            c['n'] += 1
        ordenats = sorted(counter.values(), key=lambda x: (-x['n'], x['nom'] or ''))
        return [{'id': c['id'], 'nom': c['nom'], 'color': c['color']} for c in ordenats]


class ContracteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contracte
        fields = '__all__'


class LiniaContracteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiniaContracte
        fields = '__all__'


class ModelDetailSerializer(serializers.ModelSerializer):
    fitxers = ModelFitxerSerializer(many=True, read_only=True)
    garment_type_nom = serializers.CharField(source='garment_type.nom_client', read_only=True)
    garment_group_nom = serializers.CharField(source='garment_group.nom', read_only=True)
    responsable_nom = serializers.CharField(source='responsable.nom_complet', read_only=True)
    created_by_nom = serializers.CharField(source='created_by.nom_complet', read_only=True)
    customer_nom = serializers.CharField(source='customer.nom', read_only=True)
    garment_type_item_nom = serializers.CharField(source='garment_type_item.name', read_only=True)
    garment_type_item_code = serializers.CharField(source='garment_type_item.code', read_only=True)
    size_system_codi = serializers.CharField(source='size_system.codi', read_only=True)
    size_system_nom = serializers.CharField(source='size_system.nom', read_only=True)
    grading_rule_set_nom = serializers.CharField(source='grading_rule_set.nom', read_only=True)  # P8: ruleset vigent (lectura)
    customer_logo = serializers.SerializerMethodField()   # TS-4c: logo del client (URL)

    def get_customer_logo(self, obj):
        if obj.customer_id and obj.customer.logo:
            request = self.context.get('request')
            url = obj.customer.logo.url
            return request.build_absolute_uri(url) if request else url
        return None

    class Meta:
        model = Model
        # 'fields = __all__' already includes the new fields origen_patro, versio,
        # garment_group. The *_nom variants are only exposed read-only.
        fields = '__all__'
        read_only_fields = ('codi_intern', 'data_entrada', 'created_at', 'created_by')



# Sprint S14B — BaseMeasurement CRUD
class BaseMeasurementSerializer(serializers.ModelSerializer):
    # Expose POM fields via `pom.pom_global` for the UI.
    pom_code = serializers.CharField(source='pom.pom_global.codi', read_only=True)
    pom_name_en = serializers.CharField(source='pom.pom_global.nom_en', read_only=True)
    pom_name_cat = serializers.CharField(source='pom.pom_global.nom_ca', read_only=True)
    pom_abbreviation = serializers.CharField(source='pom.pom_global.abbreviation', read_only=True)
    pom_is_key = serializers.BooleanField(source='pom.pom_global.is_key', read_only=True)
    pom_category = serializers.CharField(source='pom.pom_global.categoria', read_only=True)
    # Legacy POMMaster fields (fallback when there is no associated pom_global).
    pom_codi_client = serializers.CharField(source='pom.codi_client', read_only=True)
    pom_nom_client = serializers.CharField(source='pom.nom_client', read_only=True)

    class Meta:
        model = BaseMeasurement
        fields = (
            'id', 'model', 'pom',
            'pom_code', 'pom_name_en', 'pom_name_cat',
            'pom_abbreviation', 'pom_is_key', 'pom_category',
            'pom_codi_client', 'pom_nom_client',
            'base_value_cm', 'is_active', 'notes',
            'nom_fitxa', 'origen',
            'updated_at',
        )
        read_only_fields = ('updated_at',)


class WatchpointSerializer(serializers.ModelSerializer):
    created_by_nom = serializers.CharField(source='created_by.nom_complet', read_only=True)
    resolved_by_nom = serializers.CharField(source='resolved_by.nom_complet', read_only=True)
    task_type_code = serializers.CharField(source='task.task_type.code', read_only=True)

    class Meta:
        model = Watchpoint
        fields = [
            'id', 'model', 'task', 'task_type_code', 'text', 'estat', 'dades',
            'created_by', 'created_by_nom', 'created_at',
            'resolved_by', 'resolved_by_nom', 'resolved_at', 'resolution_note',
        ]
        # L'estat i l'autoria es gestionen pel servidor (create / accions resolve/reopen).
        # 'dades' és de sistema (l'omple l'import/recàlcul, F2/F3) → read-only per al client.
        read_only_fields = ['estat', 'dades', 'created_by', 'created_at', 'resolved_by', 'resolved_at', 'resolution_note']
