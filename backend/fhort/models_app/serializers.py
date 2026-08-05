from rest_framework import serializers

from .models import (BaseMeasurement, Contracte, GarmentSet, ItemFitxer, LiniaContracte,
                     Model, ModelFitxer, Watchpoint)


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


class GarmentSetMiniSerializer(serializers.ModelSerializer):
    """SET-1 · A4 — el CONJUNT vist des d'una peça. Read-only i mínim: el que cal per pintar el
    badge «SET n/N» i per navegar a les germanes, res més. La font del codi COMERCIAL és
    `codi_base` (decisió 1: un codi comercial; les peces són parts internes -01/-02)."""
    peces = serializers.SerializerMethodField()

    class Meta:
        model = GarmentSet
        fields = ('id', 'codi_base', 'nom_comercial', 'num_pieces', 'peces')

    def get_peces(self, obj):
        """Les germanes, per poder navegar-hi des de la capçalera sense un segon fetch.
        Va aquí i no a un endpoint nou perquè és una llista de 2-3 files que ja s'ha de
        travessar per pintar el badge: un endpoint per a això seria una crida de més."""
        return [
            {'id': p.id, 'codi_intern': p.codi_intern, 'piece_number': p.piece_number,
             'nom_prenda': p.nom_prenda}
            for p in obj.peces.all().order_by('piece_number', 'id')
        ]


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
    # SET-1 · A4 — la pertinença a un conjunt, visible a la llista. Fins ara `ModelListSerializer`
    # no exposava ni `garment_set` ni `piece_number`, i un tècnic no podia saber que una fila era
    # la peça d'un producte. Read-only: l'única escriptura de `garment_set` és a la creació.
    garment_set = GarmentSetMiniSerializer(read_only=True)
    # F2.7 — l'avís de LLIURABLE va a la LLISTA, no només al detall: el PM ha de veure quins
    # models ja han donat el que havien de donar sense entrar-hi un per un. Llista de `seq` de
    # rondes lliurades; buida = res a ensenyar (el consumidor no ha de distingir «cap ronda» de
    # «cap acabada»).
    lliurable_ronda_n = serializers.SerializerMethodField()

    def get_lliurable_ronda_n(self, obj):
        from fhort.tasks.services_r import rondes_lliurables   # local: cicle models_app↔tasks
        return rondes_lliurables(obj)

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
            # P7 — el RECURS assignat (codi nu del Studio, '' = cap). La llista del Brand
            # n'ha de poder pintar una columna sense demanar el detall model a model.
            'studio_assignat',
            # RETORN-2 — la MADURESA que l'altra casa publica sobre aquesta peça. Va a la
            # LLISTA i no només al detall: qui mira 200 files vol veure d'un cop quines
            # avancen i quines no, i entrar model a model per saber-ho no és una llista.
            # Read-only per naturalesa (l'únic escriptor és `federation_service.sync_estat`);
            # aquest serializer no desa res.
            'federacio_estat',
            # RETORN-1 — la provinença, a la llista: sense ella la UI de l'estudi no pot saber
            # quines files es poden enviar a una marca i quines han nascut a casa.
            'origen',
            'created_at',
            'garment_type',
            'garment_type_item_nom',
            'lliurable_ronda_n',
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
            # SET-1
            'garment_set',
            'piece_number',
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


# B7 — idioma del document → columna del catàleg. Els catàlegs de graduació (Target, FitType,
# ConstructionType) porten el nom als tres idiomes; el codi de l'idioma és el de la UI ('ca'),
# el de la columna és el del model de dades ('nom_cat'), i no són el mateix nom.
_CATALEG_NOM_ATTR = {'ca': 'nom_cat', 'en': 'nom_en', 'es': 'nom_es'}


class ModelDetailSerializer(serializers.ModelSerializer):
    fitxers = ModelFitxerSerializer(many=True, read_only=True)
    garment_type_nom = serializers.CharField(source='garment_type.nom_client', read_only=True)
    garment_group_nom = serializers.CharField(source='garment_group.nom', read_only=True)
    # Codi de grup CANÒNIC de la peça (arbre únic Grup→Família→Item). Font: garment_type.grup, que
    # SEMPRE és present (a diferència de garment_group FK, buit als models importats). El wizard (pas 4)
    # el fa servir per pre-sembrar l'eix de grup del matching estricte fins i tot en edició/models buits.
    garment_type_grup = serializers.CharField(source='garment_type.grup', read_only=True)
    responsable_nom = serializers.CharField(source='responsable.nom_complet', read_only=True)
    created_by_nom = serializers.CharField(source='created_by.nom_complet', read_only=True)
    customer_nom = serializers.CharField(source='customer.nom', read_only=True)
    garment_type_item_nom = serializers.CharField(source='garment_type_item.name', read_only=True)
    garment_type_item_code = serializers.CharField(source='garment_type_item.code', read_only=True)
    size_system_codi = serializers.CharField(source='size_system.codi', read_only=True)
    size_system_nom = serializers.CharField(source='size_system.nom', read_only=True)
    grading_rule_set_nom = serializers.CharField(source='grading_rule_set.nom', read_only=True)  # P8: ruleset vigent (lectura)
    # S12 · realineació 5 capes: target/fit/construction de la capçalera vénen del GradingRuleSet
    # triat (la capa de graduació), NO del run ni dels camps legacy del Model. En anglès (nom_en)
    # per coherència amb les etiquetes fixes angleses de la Template FTT. Model sense ruleset → None.
    grading_target_nom = serializers.SerializerMethodField()
    grading_fit_nom = serializers.SerializerMethodField()
    grading_construction_nom = serializers.SerializerMethodField()
    # B7 — els mateixos tres, en els TRES idiomes, per a la fitxa amb idioma propi.
    grading_noms = serializers.SerializerMethodField()
    customer_logo = serializers.SerializerMethodField()   # TS-4c: logo del client (URL)
    # L'ESTAT DE LA FEINA DE POM ÉS UN FET DEL MODEL, no una fila de la llista de tasques.
    #
    # El full del model derivava el gate de Mesures de `GET model-task-items`, que va escopat
    # per `view_team_tasks` (accounts/capabilities.scope_model_task_queryset): un tècnic que no
    # té la capability i no és l'assignat de la tasca `pom` no en veia la fila, i el full
    # concloïa que la feina no estava feta. Resultat: «Mesures encara no disponibles» amb la
    # tasca Done i la taula plena. El permís decidia si el model tenia mesures, que no és el
    # que aquell permís vol dir — regula QUINES TASQUES VEUS, no quin estat té el model.
    #
    # Per això aquest booleà es calcula al servidor i SENSE cap scope de visibilitat. La llista
    # de tasques segueix escopada exactament com fins ara: aquí no s'exposa cap tasca, ni qui hi
    # treballa, ni quantes n'hi ha — només si la feina de POM del model està tancada.
    pom_task_done = serializers.SerializerMethodField()
    # F1.6 — les voltes que ja han lliurat, per al PM. NOMÉS EL FET consultable: quines rondes
    # han donat tot el que havien de donar (`task_type.es_lliurable` totes Done). L'avís visual
    # —qui el veu, quan i com— és F2; aquí no es notifica ningú. Llista buida = cap ronda, o cap
    # ronda acabada: el consumidor no ha de distingir-ho per decidir si ensenya res.
    lliurable_ronda_n = serializers.SerializerMethodField()
    # F2.0 — la volta VIGENT del model: {seq, motiu, oberta_el} o null (la 1a és implícita).
    # El modal de F2.1 l'ha de saber per titular la cara B («obrir ronda N+1»).
    ronda_oberta = serializers.SerializerMethodField()
    # SET-1 · A4 — el conjunt, niuat, amb les germanes per navegar-hi des de la capçalera.
    # DESVIACIÓ ANOTADA: `fields='__all__'` exposava `garment_set` com a pk ESCRIVIBLE; aquesta
    # declaració el fa read-only. Cap caller el feia servir (0 hits al frontend; els dos únics
    # escriptors —`create_model_wizard` i `bulk_import_service`— són per ORM), i A5 diu que la
    # conversió mandrosa d'un model a peça no té camí: obrir-la per un PATCH genèric seria
    # precisament el camí que ningú no ha dissenyat.
    garment_set = GarmentSetMiniSerializer(read_only=True)

    # F1 — FALLBACK als camps PROPIS del model. Aquests tres `_nom` alimenten la línia
    # "TARGET | FIT TYPE | CONSTRUCTION" de la capçalera de la fitxa
    # (TechSheetEditor.buildMasterHeaderPrimitives, caixa 3). Fins ara sortien de la cascada
    # del GradingRuleSet i prou: un model amb graduació RESIDENT (ModelGradingRule) i
    # `grading_rule_set=NULL` —el cas normal després d'un import— imprimia la capçalera BUIDA
    # tot i tenir `target`/`fit_type`/`construction` poblats a la seva pròpia fila.
    #
    # Precedència: mana el ruleset quan n'hi ha (porta els noms CANÒNICS del catàleg, en
    # anglès i possiblement multi-target); si no, el camp propi TAL QUAL. No s'inventa res:
    # si el model tampoc no en té, segueix sent None i la capçalera calla.
    def get_ronda_oberta(self, obj):
        from fhort.tasks.services_r import _ronda_oberta   # import local: cicle models_app↔tasks
        r = _ronda_oberta(obj)
        return None if r is None else {'id': r.pk, 'seq': r.seq, 'motiu': r.motiu,
                                       'oberta_el': r.oberta_el.isoformat()}

    def get_lliurable_ronda_n(self, obj):
        from fhort.tasks.services_r import rondes_lliurables   # import local: cicle models_app↔tasks
        return rondes_lliurables(obj)

    def get_pom_task_done(self, obj):
        # La unicitat (model, task_type) només val per a `origen='prevista'` (tasks/models.py),
        # o sigui que un model pot tenir més d'una tasca `pom`. «Feta» = n'hi ha ALGUNA de Done:
        # és determinista, a diferència del que feia el front (agafar la primera de la llista,
        # que depenia de l'ordre i de què l'scope li havia deixat veure).
        from fhort.tasks.models import ModelTask   # import local: evita cicle models_app↔tasks
        return ModelTask.objects.filter(
            model_id=obj.pk, task_type__code='pom', status='Done').exists()

    def get_grading_target_nom(self, obj):
        # N1 — aquí hi havia un tercer graó: si la M2M `targets` era buida, es llegia el FK
        # legacy `GradingRuleSet.target`. Aquell FK el va RETIRAR la migració `pom/0043` (P7,
        # «un rol, un vincle»), i des de llavors la branca no era un fallback sinó un
        # AttributeError: qualsevol model amb ruleset de targets buits feia 500 el seu propi GET.
        #
        # S'esborra en comptes de reescriure's sobre `targets` perquè seria codi mort per
        # construcció: la 0043 reconcilia FK→M2M ABANS de l'esborrat («tot `target` no NULL ha
        # de constar a `targets`»), o sigui que no existeix cap estat on `targets` sigui buida i
        # el FK tingués res a dir. El que el graó cobria de debò —ruleset sense cap target— ja
        # el cobreix l'última línia, que cau al camp lliure del Model.
        rs = obj.grading_rule_set if obj.grading_rule_set_id else None
        if rs:
            noms = [t.nom_en for t in rs.targets.all()]
            if noms:
                return ' / '.join(noms)
        return (obj.target or '').strip() or None

    def get_grading_fit_nom(self, obj):
        rs = obj.grading_rule_set if obj.grading_rule_set_id else None
        if rs and rs.fit_type_id:
            return rs.fit_type.nom_en
        return (obj.fit_type or '').strip() or None

    def get_grading_construction_nom(self, obj):
        rs = obj.grading_rule_set if obj.grading_rule_set_id else None
        if rs and rs.construction_id:
            return rs.construction.nom_en
        return (obj.construction or '').strip() or None

    def get_grading_noms(self, obj):
        """Target/fit/construction en ELS TRES IDIOMES: {target: {ca,en,es}, fit: …, …}.

        B7 — la fitxa tècnica té idioma PROPI (propietat del document, no de qui l'obre), i
        aquests tres són valors de CATÀLEG: tenen nom a cada idioma i s'han de dir en el del
        document. Es donen els tres alhora, no un de resolt per petició, perquè commutar
        l'idioma de la fitxa ha de re-renderitzar el document sense tornar a demanar el model.

        `grading_*_nom` (anglès) es conserven intactes: hi ha consumidors que no són la fitxa.
        Un idioma sense traducció al catàleg cau a l'anglès — una capçalera no es queda en
        blanc mai. Els camps legacy de text lliure del Model no es tradueixen (són dades
        escrites a mà, no tokens de catàleg): el mateix valor als tres idiomes.
        """
        rs = obj.grading_rule_set if obj.grading_rule_set_id else None

        def per_idiomes(items, legacy):
            if items:
                return {
                    idioma: ' / '.join((getattr(it, attr, '') or '').strip() or it.nom_en for it in items)
                    for idioma, attr in _CATALEG_NOM_ATTR.items()
                }
            val = (legacy or '').strip()
            return {idioma: val for idioma in _CATALEG_NOM_ATTR} if val else None

        # Mateix graó mort que a `get_grading_target_nom`, i mateix motiu per esborrar-lo: el FK
        # `target` no existeix des de `pom/0043`, i la M2M ja conté tot el que ell tenia.
        targets = list(rs.targets.all()) if rs else []
        return {
            'target': per_idiomes(targets, obj.target),
            'fit': per_idiomes([rs.fit_type] if rs and rs.fit_type_id else [], obj.fit_type),
            'construction': per_idiomes([rs.construction] if rs and rs.construction_id else [], obj.construction),
        }

    def get_customer_logo(self, obj):
        if obj.customer_id and obj.customer.logo:
            request = self.context.get('request')
            url = obj.customer.logo.url
            return request.build_absolute_uri(url) if request else url
        return None

    def validate(self, attrs):
        """PORTA ÚNICA DEL RUN (llei S24b) — la via oberta del CRUD genèric.

        `fields = '__all__'` fa escrivible `size_run_model`, i aquest `ModelViewSet`
        (`POST/PUT/PATCH /api/v1/models/[<pk>/]`) no passa per `_resolve_garment_def`: era
        l'única via del cens que acceptava un run arbitrari sense cap guard. Es valida aquí i
        no amb `read_only`, perquè un client legítim que vulgui desar el run per aquest camí
        ha de poder fer-ho — el que no pot és desar-lo desordenat.

        Va a `validate()` (nivell objecte) i no a `validate_size_run_model()` perquè cal el
        `size_system`, que pot venir al MATEIX payload o ja viure a la instància.
        """
        attrs = super().validate(attrs)
        if 'size_run_model' not in attrs or not attrs['size_run_model']:
            return attrs

        from fhort.pom.grading_utils import run_del_model

        size_system = attrs.get('size_system') or getattr(self.instance, 'size_system', None)
        run, desconegudes = run_del_model(
            str(attrs['size_run_model']).replace(';', '·').split('·'), size_system,
        )
        if desconegudes:
            raise serializers.ValidationError({
                'size_run_model': (
                    "Aquestes talles no pertanyen al sistema de talles del model: "
                    + ', '.join(desconegudes)
                ),
            })
        attrs['size_run_model'] = '·'.join(run)
        return attrs

    class Meta:
        model = Model
        # 'fields = __all__' already includes the new fields origen_patro, versio,
        # garment_group. The *_nom variants are only exposed read-only.
        fields = '__all__'
        # RETORN-2 — `federacio_estat` és una FINESTRA a l'altra casa, no un camp d'aquesta:
        # `fields='__all__'` l'hauria fet escrivible pel PATCH genèric i qualsevol client
        # hauria pogut escriure-hi una maduresa inventada que la UI pinta com si vingués de
        # l'estudi. L'únic escriptor legítim és `federation_service.sync_estat`.
        read_only_fields = ('codi_intern', 'data_entrada', 'created_at', 'created_by',
                            'federacio_estat')



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
            # C4 — ELS DOS EIXOS D'IDENTITAT (D-31.22 · D-31.26). Hi entren com a ESCRIVIBLES
            # perquè la pantalla de PRESA els ha de poder tocar per fila (moure una mesura de
            # capa, partir-la per instància) i l'únic camí que ho feia fins ara era
            # `set-measurements`, que reescriu `origen` a 'MANUAL' i les toleràncies de TOTES
            # les files del payload. Fer passar una presa per allà convertiria una base
            # 'CHECKED' en 'MANUAL' sense que ningú ho hagués demanat: dany d'auditoria dins
            # d'un canvi de nom de columna.
            'capa', 'instancia',
            'base_value_cm', 'is_active', 'notes',
            'nom_fitxa', 'origen',
            'updated_at',
        )
        read_only_fields = ('updated_at',)

    def validate(self, attrs):
        """La CLAU ÚNICA `(model, pom, capa, instancia)` i la invariant del nom, dites a temps.

        Totes dues viuen a la BD i, sense això, arriben com un IntegrityError —un 500 mut— quan
        el que ha passat és que l'usuari ha triat una cara que aquesta mesura ja té.
        """
        inst = self.instance
        camps = {
            'model': attrs.get('model', getattr(inst, 'model', None)),
            'pom': attrs.get('pom', getattr(inst, 'pom', None)),
            'capa': attrs.get('capa', getattr(inst, 'capa', '') or ''),
            'instancia': attrs.get('instancia', getattr(inst, 'instancia', '') or ''),
        }
        if camps['model'] and camps['pom']:
            germanes = BaseMeasurement.objects.filter(**camps)
            if inst is not None:
                germanes = germanes.exclude(pk=inst.pk)
            if germanes.exists():
                raise serializers.ValidationError({'instancia': (
                    'Aquesta mesura ja té una fila en aquesta capa i instància.'
                )})
        # `models_app_basemeasurement_instancia_exigeix_nom`: amb instància, el nom és obligatori.
        nom = attrs.get('nom_fitxa', getattr(inst, 'nom_fitxa', '') or '')
        if camps['instancia'] and not (nom or '').strip():
            raise serializers.ValidationError({'nom_fitxa': (
                'Una mesura amb instància ha de portar nomenclatura.'
            )})
        return attrs


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
