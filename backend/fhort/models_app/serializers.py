from rest_framework import serializers

from .models import (BaseMeasurement, Contracte, ItemFitxer, LiniaContracte, Model,
                     ModelFitxer, Watchpoint)


def _signed_download_url(obj, request, *, salt, ruta):
    """URL absoluta i signada (D13). Compartida per ModelFitxer i ItemFitxer.

    `<a href>` i `<img src>` no poden portar Authorization; el permís viatja al token, que
    només rep qui ja s'ha autenticat per llegir aquesta fila. Sense `request` al context no
    es pot construir una URL absoluta → None (mateix patró que _asset_urls,
    ftt_document_views.py:40-46). Cada model té el SEU salt: si en compartissin un, un token
    emès per a ModelFitxer id=5 validaria a ItemFitxer id=5.
    """
    from django.core import signing

    if request is None or not obj.fitxer:
        return None
    token = signing.dumps(obj.id, salt=salt)
    return request.build_absolute_uri(f'/api/v1/{ruta}/{obj.id}/download-signed/?token={token}')


class ModelFitxerSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    # S03c · C2.3 — el Finder mostra qui va pujar el fitxer, no el seu id (taula #8). ADDITIU:
    # `pujat_per` (PK) es manté per als consumidors actuals. Sense N+1: els dos ViewSets ja fan
    # select_related('pujat_per'). `default=None` cobreix pujat_per NULL (FK nullable).
    pujat_per_nom = serializers.CharField(source='pujat_per.nom_complet', read_only=True,
                                          default=None)
    # S03c · C2.4 (D17) — procedència llegible. `derivat_de_model` i `derivat_de_item` ja
    # surten com a id per `fields='__all__'`; aquí es fixen com a NOMÉS LECTURA i s'hi afegeix
    # una etiqueta curta. Són els PRIMERS lectors d'aquests camps, que fins ara eren write-only.
    derivat_de_label = serializers.SerializerMethodField()

    class Meta:
        model = ModelFitxer
        fields = '__all__'
        # La procedència l'escriuen els serveis d'importació (usar_al_model i, a C3, el germà
        # model→model), mai el serializer.
        read_only_fields = ('data_pujada', 'derivat_de_model', 'derivat_de_item')

    def get_download_url(self, obj):
        from .services_fitxers import DOWNLOAD_SALT
        return _signed_download_url(obj, self.context.get('request'),
                                    salt=DOWNLOAD_SALT, ruta='model-fitxers')

    def get_derivat_de_label(self, obj):
        """Codi de l'origen: el del MODEL si ve d'un altre model, el de l'ITEM si ve del catàleg.

        Els dos camps són excloents a la pràctica (una còpia té un sol origen), però si mai en
        coexistissin, model→model mana: és la procedència més específica. Sense N+1: el
        ViewSet fa select_related dels dos camins.
        """
        if obj.derivat_de_model_id:
            origen = obj.derivat_de_model
            return origen.model.codi_intern if origen and origen.model_id else None
        if obj.derivat_de_item_id:
            origen = obj.derivat_de_item
            return origen.garment_type_item.code if origen and origen.garment_type_item_id else None
        return None


class ItemFitxerSerializer(serializers.ModelSerializer):
    """Mirall d'ModelFitxerSerializer per al catàleg (S03b · P4)."""
    download_url = serializers.SerializerMethodField()
    # S03c · C2.3 — mirall de ModelFitxerSerializer.pujat_per_nom.
    pujat_per_nom = serializers.CharField(source='pujat_per.nom_complet', read_only=True,
                                          default=None)

    class Meta:
        model = ItemFitxer
        fields = '__all__'
        # TOT read-only: l'escriptura la governa save_item_file (via ViewSet.create), mai el
        # serializer. Amb `garment_type_item`/`versio_anterior` escrivibles, un futur PATCH
        # podria reencadenar un fitxer a un ALTRE item saltant-se el guard cross-item de create().
        read_only_fields = ('data_pujada', 'versio', 'is_current', 'checksum', 'mimetype',
                            'mida_bytes', 'pujat_per', 'garment_type_item', 'versio_anterior',
                            'fitxer', 'nom_fitxer', 'tipus')

    def get_download_url(self, obj):
        from .services_fitxers import ITEM_DOWNLOAD_SALT
        return _signed_download_url(obj, self.context.get('request'),
                                    salt=ITEM_DOWNLOAD_SALT, ruta='item-fitxers')


class ModelListSerializer(serializers.ModelSerializer):
    garment_type = serializers.SerializerMethodField()
    responsable = serializers.SerializerMethodField()
    garment_type_item_nom = serializers.CharField(source='garment_type_item.name', read_only=True)
    # v2 albarà — client del model (per a l'acció massiva "Assignar a comanda": mateix client).
    customer_nom = serializers.CharField(source='customer.nom', read_only=True, default=None)
    # v2 albarà — traçabilitat: True si el model té un encàrrec (WO ORDER); False = va directe.
    has_order = serializers.BooleanField(read_only=True, default=False)
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
            'has_order',
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
