from collections import defaultdict

from rest_framework import serializers, status
from rest_framework.exceptions import APIException

from .size_labels import _tipus_de_les_etiquetes
from .nomenclatura import (CAMPS_QUE_SEPAREN, COM_ES_MESURA, abreviatura_de,
                           categoria_de, codi_de, com_es_mesura_de, noms_de,
                           separa_del_global)
from .grading_regime import valida_breaks

from .models import (
    ConstructionType,
    CustomerPOMAlias,
    FitType,
    GarmentGroup,
    GarmentGroupPOMMap,
    GarmentPOMMap,
    GarmentTypePOMMap,
    GarmentType,
    GarmentTypeGlobal,
    GradingRule,
    GradingRuleSet,
    ItemBaseMeasurement,
    ItemBaseSet,
    POMCategory,
    POMGlobal,
    POMMaster,
    SizeDefinition,
    SizeSystem,
    Target,
)


class GarmentGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarmentGroup
        fields = '__all__'


class POMCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = POMCategory
        fields = '__all__'


class POMMasterSerializer(serializers.ModelSerializer):
    # ── LA FORMA DE LA RESPOSTA NO POT VARIAR PER FILA (F2.1a) ────────────────────────────
    # Els 21 camps que pengen de `pom_global` s'emeten SEMPRE, amb `null` quan el POM no està
    # lligat al catàleg global. Abans DESAPAREIXIEN de la resposta: quan el `source` travessa un
    # `None`, `get_attribute()` de DRF llança AttributeError i, com que `read_only` implica
    # `required=False`, el camp cau per `SkipField` (rest_framework/fields.py:450-456). Amb
    # `allow_null=True` la mateixa branca retorna `None` i la clau es queda.
    #
    # Per què importa i no és cosmètica: `fhort` té 396 POMs, **122 sense `pom_global`**. Un
    # client no podia distingir «no lligat al catàleg» de «camp que no existeix» —les dues coses
    # es veien igual: la clau absent—, i és exactament l'error que va fer que el cens de la
    # Fase 1 conclogués que aquests camps no existien. Ara la resposta distingeix TRES estats:
    #     null           → no lligat al catàleg global   (122 POMs)
    #     cadena buida    → lligat, però sense informar   (149 POMs)
    #     valor           → dada de debò                  (125 POMs)
    # La UI els ha de dir amb paraules diferents; els guions muts els amagaven tots tres.
    #
    # Additiu i read-only: no es treu ni es renombra res, i no s'obre cap camí d'escriptura.
    pom_global_codi = serializers.CharField(source='pom_global.codi', read_only=True, allow_null=True)
    pom_global_nom = serializers.CharField(source='pom_global.nom_en', read_only=True, allow_null=True)

    # PAS B5 — bloc complet "com mesurar" per a la vista Catalogue (NOMÉS LECTURA). Mateix patró
    # que GarmentPOMMapSerializer però arrelat al propi POMMaster: pom_global flat amb fallback
    # tenant-only. Tots read_only → no afegeixen escriptura (el catàleg es conserva intacte).
    pom_code = serializers.SerializerMethodField()
    name_en = serializers.SerializerMethodField()
    name_cat = serializers.SerializerMethodField()
    abbreviation = serializers.SerializerMethodField()
    categoria_nom = serializers.SerializerMethodField()
    applies_woven = serializers.BooleanField(source='pom_global.applies_woven', read_only=True, allow_null=True)
    applies_knit = serializers.BooleanField(source='pom_global.applies_knit', read_only=True, allow_null=True)
    applies_swim = serializers.BooleanField(source='pom_global.applies_swim', read_only=True, allow_null=True)
    # 🚨 ELS NOU CAMPS DEL «COM ES MESURA» PASSEN PER LA CASCADA (22/08). Fins al tram 3 només
    # vivien a `POMGlobal` i aquí es llegien d'allà en directe; ara també viuen al tenant, i
    # el que ha de sortir és el que MANA: el del tenant si l'ha informat, el del global si no
    # (`nomenclatura.com_es_mesura_de`). Deixar-los apuntant al global hauria fet que la
    # pantalla d'edició del catàleg desés un valor i seguís ensenyant l'altre — el mateix
    # mode de fallada que aquest sprint tanca, per la porta de darrere.
    #
    # `unitat` és més avall, amb la resta de camps que segueixen sent del global.
    start_point = serializers.SerializerMethodField()
    end_point = serializers.SerializerMethodField()
    reference_point = serializers.SerializerMethodField()
    scope = serializers.SerializerMethodField()
    orientation = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    line = serializers.SerializerMethodField()
    body_section = serializers.SerializerMethodField()
    tol_prod_cm = serializers.DecimalField(source='pom_global.tol_prod_cm',
                                           max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    tol_samp_cm = serializers.DecimalField(source='pom_global.tol_samp_cm',
                                           max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    iso_ref = serializers.CharField(source='pom_global.iso_ref', read_only=True, allow_null=True)
    unitat = serializers.SerializerMethodField()
    descripcio_en = serializers.CharField(source='pom_global.descripcio_en', read_only=True, allow_null=True)
    descripcio_ca = serializers.CharField(source='pom_global.descripcio_ca', read_only=True, allow_null=True)
    body_measure_iso_codi = serializers.CharField(
        source='pom_global.body_measure_iso.codi_iso', read_only=True, allow_null=True)
    body_measure_iso_nom = serializers.CharField(
        source='pom_global.body_measure_iso.nom_en', read_only=True, allow_null=True)

    # 🚨 FONT ÚNICA (22/08) — aquests cinc mètodes feien guanyar el GLOBAL, i la propietat
    # `POMMaster.pom_code` feia guanyar el TENANT: dues implementacions de la mateixa veritat
    # dient coses contràries sobre la mateixa fila. Ara tots dos camins passen pel resolutor
    # de `pom/nomenclatura.py` (llei d'Agus: ÀLIES > TENANT > GLOBAL). El catàleg no té
    # context de client —és de la casa, no d'un client—, i per això no hi passa cap àlies:
    # la cadena hi comença al tenant. La FORMA de la resposta no canvia; el VALOR, sí.
    #: La cascada és pura i barata (nou `getattr` sobre objectes ja carregats amb
    #: `select_related`): es crida per camp i prou. Memoritzar-la per fila demanaria una clau
    #: d'identitat de l'objecte, i `id()` es reutilitza després d'un GC — un cau que pot
    #: servir els camps d'una ALTRA fila és molt pitjor que nou diccionaris petits.
    def _com(self, obj):
        return com_es_mesura_de(obj)

    def get_unitat(self, obj):
        return self._com(obj)['unitat']

    def get_start_point(self, obj):
        return self._com(obj)['start_point']

    def get_end_point(self, obj):
        return self._com(obj)['end_point']

    def get_reference_point(self, obj):
        return self._com(obj)['reference_point']

    def get_scope(self, obj):
        return self._com(obj)['scope']

    def get_orientation(self, obj):
        return self._com(obj)['orientation']

    def get_state(self, obj):
        return self._com(obj)['state']

    def get_line(self, obj):
        return self._com(obj)['line']

    def get_body_section(self, obj):
        return self._com(obj)['body_section']

    def get_pom_code(self, obj):
        return codi_de(obj)

    def get_name_en(self, obj):
        return noms_de(obj)['nom_en']

    def get_name_cat(self, obj):
        return noms_de(obj)['nom_ca']

    def get_abbreviation(self, obj):
        return abreviatura_de(obj)

    def get_categoria_nom(self, obj):
        return categoria_de(obj)

    def validate_codi_client(self, value):
        """El codi és ÚNIC AL CATÀLEG i les majúscules no el distingeixen — dit amb un 400.

        La constraint `uniq_pommaster_codi_client_ci` (migració `pom/0075`) ja ho impedeix a la
        BD, però una constraint d'EXPRESSIÓ no la tradueix ningú: DRF només genera validadors
        automàtics a partir d'`unique_together` i de `unique=True`, no de `UniqueConstraint` amb
        `Upper(...)`. Sense això, aquest `ModelViewSet` —que és obert a l'escriptura— tornaria un
        **500 amb un `IntegrityError`** en comptes de dir quin camp està malament.

        La comprovació és `iexact` perquè ha de mirar el mateix que mira l'índex; i exclou la
        pròpia fila perquè rebatejar un POM amb el codi que ja tenia no és cap col·lisió.
        """
        codi = (value or '').strip()
        qs = POMMaster.objects.filter(codi_client__iexact=codi)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        xoc = qs.values('pk', 'nom_client').first()
        if xoc:
            raise serializers.ValidationError(
                f"«{codi}» ja és al catàleg (POM {xoc['pk']} · {xoc['nom_client']}). "
                f"Les majúscules no distingeixen un codi d'un altre."
            )
        return codi

    class Meta:
        model = POMMaster
        fields = '__all__'


#: ELS CAMPS QUE L'API POT ESCRIURE AL CATÀLEG DE POMs. Viu a nivell de mòdul —i no dins
#: de la classe— perquè el `Meta` de sota l'ha de veure des d'una comprensió, i el cos d'una
#: classe no és un àmbit tancat per als seus fills.
_POM_ESCRIVIBLES = (
    'codi_client', 'nom_client', 'categoria', 'actiu', 'notes', 'pendent_revisio',
    'tolerancia_default_minus', 'tolerancia_default_plus',
) + COM_ES_MESURA


class POMMasterWriteSerializer(serializers.ModelSerializer):
    """🔴 L'ESCRIPTURA DEL CATÀLEG DE POMs, amb camps EXPLÍCITS i la separació al mig.

    `POMMasterViewSet` era un `ModelViewSet` PELAT: `IsAuthenticated`, `fields='__all__'` i
    **`pom_global` ESCRIVIBLE per API**. O sigui que qualsevol usuari autenticat podia, amb un
    PATCH, re-enganxar un POM del tenant a qualsevol fila del catàleg global —o desenganxar-l'hi—
    sense passar per cap decisió ni deixar cap traça. La separació és una LLEI del domini
    (copy-on-write), no un camp de formulari.

    Què s'hi pot escriure i per què només això:
      · `codi_client`, `nom_client`, `categoria` — la identitat al catàleg de la casa;
      · `unitat` i el bloc «com es mesura» — el que el tram 3 va fer informable al tenant, i
        que és exactament el que feia impossible «complementar la informació d'un POM propi»;
      · `actiu`, `notes` — administrar-lo (i per això NO separen: arxivar no és redefinir);
      · `tolerancia_default_*`, `pendent_revisio` — ja hi eren i segueixen.

    `Meta.fields` és la llista TANCADA: el que no hi és no és camp, i DRF l'ignora en silenci a
    l'entrada. `pom_global` no hi és, i per tant no hi ha manera de dir-lo.

    🚨 **NO HEREDA DE `POMMasterSerializer`, I ÉS UNA CORRECCIÓ.** El primer intent sí que en
    heretava «per no repetir la forma», i allà els nou camps del «com es mesura» estan declarats
    com a `SerializerMethodField` —perquè la LECTURA ha de passar per la cascada— i un
    `SerializerMethodField` **és read-only sempre**. Resultat: el formulari d'edició hauria
    enviat `start_point`, `scope` i companyia, DRF els hauria descartat sense piular, i la
    pantalla hauria desat amb **200 OK sense que passés res** — el mode de fallada exacte que
    aquesta casa ja ha pagat dues vegades (`increment` a `GradingRuleSerializer`, i el motiu del
    seu `validate`). Mesurat amb `serializer().fields`, no deduït.

    La LECTURA es delega a `POMMasterSerializer` (`to_representation`): la resposta d'un PATCH
    és, camp per camp, la d'un GET —amb el codi, els noms i el «com es mesura» resolts—, que és
    el que la pantalla recarrega.
    """

    class Meta:
        model = POMMaster
        fields = _POM_ESCRIVIBLES

    #: El mateix validador que la porta de lectura: el codi és ÚNIC AL CATÀLEG i les majúscules
    #: no el distingeixen, dit amb un 400 i no amb l'`IntegrityError` de la constraint
    #: d'expressió (que DRF no tradueix sol).
    validate_codi_client = POMMasterSerializer.validate_codi_client

    def update(self, instance, validated_data):
        """🚨 SEPARAR PRIMER, ESCRIURE DESPRÉS.

        Si el POM està lligat al global i el PATCH toca un camp de `CAMPS_QUE_SEPAREN`, la
        separació copia el que penjava del global ABANS que el valor nou entri. L'ordre invers
        deixaria el camp editat trepitjat per la còpia — i `separa_del_global` només omple els
        buits, o sigui que el símptoma seria un desat que es perd només de vegades.
        """
        if instance.pom_global_id and any(c in validated_data for c in CAMPS_QUE_SEPAREN):
            separa_del_global(instance)
            instance.save()
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return POMMasterSerializer(instance, context=self.context).data


class SizeDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeDefinition
        fields = '__all__'


class SizeSystemSerializer(serializers.ModelSerializer):
    talles = SizeDefinitionSerializer(many=True, read_only=True)
    # LLEI 5 CAPES: codis de target aplicables (M2M). Sprint TARGETS-EDITABLES (2026-07-26):
    # passa a ESCRIVIBLE per codi (abans read-only SerializerMethodField) — un sistema pot servir
    # múltiples targets sense clonar-lo (diagnosi DIAGNOSI_SIZE_SYSTEMS_CARDINALITAT). Zero contacte
    # amb el motor de grading, que no llegeix mai `targets`. La forma JSON de lectura no canvia
    # (llista de codis). Buit PERMÈS (M2M blank=True) però NO és "universal" per contracte: el
    # wizard mostra només escales amb el target de la peça assignat (comportament actual intacte).
    # SlugRelatedField ja valida que cada codi existeixi a Target.
    target_codis = serializers.SlugRelatedField(
        many=True, slug_field='codi', source='targets',
        queryset=Target.objects.all(), required=False,
    )
    # N1 (2026-08-06 nit) — les altres tres capes de restricció del RUN, amb el mateix patró
    # que `target_codis`: llista de CODIS a la lectura, llista de codis a l'escriptura, i el
    # SlugRelatedField ja valida que cada codi existeixi al seu vocabulari. Mateixa llei que
    # `targets`: **buit NO és "universal"**, és "no declarat" — qui filtra ha de decidir què
    # en fa, i el pas 3 del wizard ORDENA per proximitat sense amagar res (D-31.3).
    construccio_codis = serializers.SlugRelatedField(
        many=True, slug_field='codi', source='construccions',
        queryset=ConstructionType.objects.all(), required=False,
    )
    fit_codis = serializers.SlugRelatedField(
        many=True, slug_field='codi', source='fits',
        queryset=FitType.objects.all(), required=False,
    )
    # El vocabulari de GRUP és `GarmentGroup` (Garment Types), no POM System.
    grup_codis = serializers.SlugRelatedField(
        many=True, slug_field='codi', source='grups',
        queryset=GarmentGroup.objects.all(), required=False,
    )
    customer_alias = serializers.CharField(source='customer.nom', read_only=True, default=None)

    class Meta:
        model = SizeSystem
        fields = ('id', 'codi', 'nom', 'descripcio', 'actiu', 'talles', 'target_codis',
                  'customer_codi', 'tipus_escala', 'construccio_codis', 'fit_codis',
                  'grup_codis', 'customer', 'customer_alias')

    def validate_tipus_escala(self, value):
        """C4 · el tipus d'escala no pot contradir les etiquetes del run (deute §7.4.3).

        `base_unit` no és escrivible per aquí, però `tipus_escala` sí — i és la mateixa
        mentida per una altra porta. La llei de N1 és que **l'etiqueta mana**: si les talles
        diuen una cosa, el camp no en pot dir una altra. Buit sempre s'accepta (és «no
        deduït», que és honest), i un run sense talles tampoc té amb què contradir-se.
        """
        if not value or self.instance is None:
            return value
        etiquetes = list(self.instance.talles.values_list('etiqueta', flat=True))
        segons_etiquetes = _tipus_de_les_etiquetes(etiquetes)
        if segons_etiquetes and value != segons_etiquetes:
            raise serializers.ValidationError(
                f'Les talles d\'aquest run són de tipus {segons_etiquetes}; «{value}» les '
                'contradiu. Canvia les etiquetes o deixa el camp buit.'
            )
        return value


class GarmentTypeSerializer(serializers.ModelSerializer):
    global_codi = serializers.CharField(source='garment_type_global.codi', read_only=True)
    global_nom = serializers.CharField(source='garment_type_global.nom_en', read_only=True)
    # Annotat al queryset del ViewSet (Count('items')). `default=0` perquè la resposta d'un
    # POST/PUT serialitza la instància desada, que no ve del queryset i no porta l'anotació.
    items_count = serializers.IntegerField(read_only=True, default=0)
    # C5 — veredicte de compatibilitat amb la combinació demanada (`?compat_target=…`). NULL quan
    # no s'ha demanat: el consumidor que no en sap res no en veu res. `motiu` és el codi de l'eix
    # que la deixa fora (el PRIMER que falla, de fora cap a dins), mai text traduït.
    compat = serializers.SerializerMethodField()

    def get_compat(self, obj):
        if not hasattr(obj, 'compat_target'):
            return None
        if not obj.compat_target:
            return {'ok': False, 'motiu': 'target'}
        if hasattr(obj, 'compat_construction') and not obj.compat_construction:
            return {'ok': False, 'motiu': 'construction'}
        if hasattr(obj, 'compat_fit') and not obj.compat_fit:
            return {'ok': False, 'motiu': 'fit'}
        return {'ok': True, 'motiu': None}

    class Meta:
        model = GarmentType
        fields = '__all__'
        read_only_fields = ['is_system']


class ConflicteConfirmable(APIException):
    """Un 409 amb cos PROPI: un avís que es pot confirmar, no un error.

    ⚠️ `self.detail` s'assigna DIRECTAMENT i no es passa per `APIException.__init__`, que
    normalitza tot el payload amb `_get_error_details` i converteix els enters en cadenes
    (`'regles': 3` → `'3'`). El front hi compta plurals amb aquests nombres, i un «3» de text
    no és un 3. DRF ja retorna els `dict` tal qual (`exception_handler`), o sigui que no cal
    res més perquè el cos arribi sencer.
    """

    status_code = status.HTTP_409_CONFLICT

    def __init__(self, payload):
        self.detail = payload


class GradingRuleSerializer(serializers.ModelSerializer):
    pom_codi = serializers.CharField(source='pom.codi_client', read_only=True)
    pom_nom = serializers.CharField(source='pom.nom_client', read_only=True)
    pom_nom_en = serializers.SerializerMethodField()
    pom_nom_ca = serializers.SerializerMethodField()
    pom_abbreviation = serializers.SerializerMethodField()
    # S16-B fix: global code (POM-001) for the table's CODI column,
    # and global category (Upper body, Sleeve, ...) to filter rules by
    # garment group on the frontend.
    pom_code_global = serializers.SerializerMethodField()
    pom_categoria = serializers.SerializerMethodField()
    talla_base_etiqueta = serializers.CharField(source='talla_base.etiqueta', read_only=True)

    # FONT ÚNICA (22/08) — la cadena de precedència passa pel resolutor. `pom_code_global` i
    # `pom_categoria` (a sota) NO hi passen a posta: el seu nom diu «global» i el seu contracte
    # és servir el camp del catàleg canònic tal com és, no una cadena.
    def get_pom_nom_en(self, obj):
        return noms_de(obj.pom)['nom_en'] if obj.pom_id else None

    def get_pom_nom_ca(self, obj):
        return noms_de(obj.pom)['nom_ca'] if obj.pom_id else None

    def get_pom_abbreviation(self, obj):
        return abreviatura_de(obj.pom) if obj.pom_id else None

    def get_pom_code_global(self, obj):
        if obj.pom and obj.pom.pom_global:
            return obj.pom.pom_global.codi
        return None

    def get_pom_categoria(self, obj):
        if obj.pom and obj.pom.pom_global:
            return obj.pom.pom_global.categoria
        return None

    class Meta:
        model = GradingRule
        fields = (
            'id', 'rule_set', 'pom', 'pom_codi', 'pom_nom',
            'pom_nom_en', 'pom_nom_ca', 'pom_abbreviation',
            'pom_code_global', 'pom_categoria',
            'talla_base', 'talla_base_etiqueta',
            'logica', 'increment', 'valors_step', 'actiu',
            'increment_base', 'increment_break', 'talla_break_label', 'talla_break_pos',  # Peça A (vista)
            'breaks',   # TRAM F — els intervals. Camp de FILA: viatja sol, com `valors_step`.
        )
        # FIX-A/PAS-3 — `increment` és el camp LLEGAT i ja no el llegeix ningú del motor. Es
        # queda en LECTURA (hi ha eines i exports que encara el miren i treure'l seria trencar-los
        # sense avisar) però deixa de ser ESCRIVIBLE: aquesta era l'última porta per on es podia
        # desar un delta que semblava manar i no manava.
        read_only_fields = ('rule_set', 'increment')

    def validate(self, attrs):
        """Un PATCH amb `increment` no s'ignora en silenci: es diu on ha d'anar.

        DRF descarta els camps read-only sense piular, i aquí això seria el mateix defecte que
        el fix acaba de tancar —desar amb 200 OK i que no passi res—, només que un pis més
        amunt. Val més un 400 que digui el nom del camp bo.
        """
        if 'increment' in getattr(self, 'initial_data', {}):
            raise serializers.ValidationError({'increment': (
                "`increment` és el camp llegat i ja no gradua res. El delta d'una regla LINEAR "
                "és `increment_base` (i `increment_break` + `talla_break_label` si té "
                "trencament).")})
        attrs = super().validate(attrs)

        # TRAM F — LA QUARTA PORTA. Aquesta és l'única d'escriptura del catàleg que toca la
        # forma de la regla (les dues PATCH de `s2_views`/`s4_views` només mouen delta i règim),
        # i per tant és aquí que els intervals s'han de validar amb el MATEIX punt únic que les
        # residents. El run surt del `size_system` del joc; un joc sense sistema deixa la
        # validació d'etiquetes en suspens i es diu al docstring de `valida_breaks`, no aquí.
        # ⚠️ NOMÉS QUAN ALGÚ ELS ESCRIU, i això no és un detall: els intervals es conserven
        # LATENTS sota STEP, igual que `increment_base` i `valors_step` (PG-4b-3a, el pas
        # STEP↔LINEAR no-destructiu). Validar-los a cada PATCH voldria dir que canviar el règim
        # a STEP d'una regla que en porta es rebutjaria amb 400 i obligaria a esborrar el relleu
        # per tornar-hi — que és exactament el que la casa va decidir no fer amb els valors.
        if 'breaks' in getattr(self, 'initial_data', {}):
            from fhort.pom.grading_utils import run_sistema_de
            rs = attrs.get('rule_set') or getattr(self.instance, 'rule_set', None)
            run = run_sistema_de(getattr(rs, 'size_system', None)) if rs else []
            nets, err = valida_breaks(
                attrs.get('breaks'),
                logica=attrs.get('logica', getattr(self.instance, 'logica', None)),
                run=run,
                increment_base=attrs.get('increment_base',
                                         getattr(self.instance, 'increment_base', None)))
            if err:
                raise serializers.ValidationError({'breaks': err['detall'], 'codi': err['codi']})
            attrs['breaks'] = nets
        return attrs


class GradingRuleSetSerializer(serializers.ModelSerializer):
    garment_group_nom = serializers.CharField(source='garment_group.nom', read_only=True)
    # WIZARD-COMPLET C.2 — codi del grup (font única = model GarmentGroup). Fins ara el front havia de
    # construir el mapa id→codi a mà (garment-groups) perquè el serializer només exposava el _nom.
    garment_group_codi = serializers.CharField(source='garment_group.codi', read_only=True, default=None)
    size_system_codi = serializers.CharField(source='size_system.codi', read_only=True)
    size_system_nom = serializers.CharField(source='size_system.nom', read_only=True)
    customer_codi = serializers.CharField(source='customer.codi', read_only=True, default='')
    customer_nom = serializers.CharField(source='customer.nom', read_only=True, default='')
    regles_count = serializers.IntegerField(source='regles.count', read_only=True)
    regles = GradingRuleSerializer(many=True, read_only=True)
    # S16-A: array of target codes (M2M). target_codi kept for compatibility.
    targets_codis = serializers.SerializerMethodField()
    target_codi = serializers.SerializerMethodField()
    construction_codi = serializers.SerializerMethodField()
    fit_type_codi = serializers.SerializerMethodField()
    # Sprint ÀMBIT — àmbit d'aplicabilitat multi-node (disponibilitat). Llista de nodes (grup/família/
    # item) al qual el contenidor «aplica». El matching hi baixa fins a item; buit = fallback a garment_group.
    # ESCRIVIBLE (edició = reclassificació, paritat amb la creació size-map): write_only per no xocar amb
    # la lectura, que la posa `to_representation` des de scope_nodes. En escriure → apply_scope_nodes +
    # garment_group=None (D1: convergència per atrició, una sola font d'abast per ruleset).
    applies_to = serializers.ListField(
        child=serializers.DictField(), required=False, write_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['applies_to'] = [
            {'node_type': s.node_type,
             'group_codi': s.garment_group.codi if s.garment_group_id else None,
             'garment_type_id': s.garment_type_id,
             'garment_type_item_id': s.garment_type_item_id}
            for s in instance.scope_nodes.all()
        ]
        return data

    def _write_scope(self, inst, applies):
        # D1 — en tocar l'abast: reemplaça scope_nodes i BUIDA garment_group (una sola font).
        from fhort.pom.grading_utils import apply_scope_nodes
        apply_scope_nodes(inst, applies)
        if inst.garment_group_id is not None:
            inst.garment_group = None
            inst.save(update_fields=['garment_group'])

    def create(self, validated_data):
        applies = validated_data.pop('applies_to', None)
        inst = super().create(validated_data)
        if applies is not None:
            self._write_scope(inst, applies)
        return inst

    def update(self, instance, validated_data):
        applies = validated_data.pop('applies_to', None)
        inst = super().update(instance, validated_data)
        if applies is not None:
            self._write_scope(inst, applies)
        return inst

    # `.all()` i prou: `values_list()` i `.first()` construeixen un queryset NOU i per tant
    # ignoren la cache del prefetch_related del ViewSet — eren 2 queries per conjunt encara
    # amb el prefetch posat. `.all()` sobre un M2M prefetchat no toca la BD.
    def get_targets_codis(self, obj):
        return [tg.codi for tg in obj.targets.all()]

    def get_target_codi(self, obj):
        codis = self.get_targets_codis(obj)
        return codis[0] if codis else None

    def get_construction_codi(self, obj):
        return obj.construction.codi if obj.construction else None

    def get_fit_type_codi(self, obj):
        return obj.fit_type.codi if obj.fit_type else None

    # ── CANVIAR EL SISTEMA DE TALLES D'UN CONJUNT AMB REGLES ─────────────────────────────
    #
    # 🚨 AQUÍ HI HAVIA UN GUARD DUR (400) i el seu motiu era FALS (Agus, 2026-08-10). Deia:
    # «no es pot canviar: les talles base de les regles pertanyen al run actual». Però
    # `GradingRule.talla_base` és **mer metadata del seed** i el motor no la llegeix mai —ho
    # té escrit `grading_utils.grading_rules_match`: «_apply_rule ancora a
    # model.base_size_label, no a rule.talla_base»—, i el trencament es resol per ETIQUETA
    # (`_break_idx_de` compara `talla_break_label` amb les etiquetes del run). O sigui que un
    # conjunt NO pertany al seu run: hi apunta, i el pot canviar.
    #
    # El que sí que és real és una etiqueta que desapareix: si una regla trenca a `S` i el run
    # nou no té cap `S`, `_break_idx_de` torna `None` i **aquella regla es gradua sense
    # trencament**, en silenci. Això no és per bloquejar-ho —hi ha casos legítims— sinó per
    # PREGUNTAR-HO, amb els noms a la vista.
    #
    # 🔑 EL CRITERI DE COMPARACIÓ ÉS EL DEL MOTOR I NO UN ALTRE: `_norm` (upper+strip), mai
    # `canonical_size_label`. Afinar-lo aquí faria que la porta i el càlcul diguessin coses
    # diferents, que és pitjor que tenir-los tots dos estrictes.
    def _validar_canvi_de_run(self, inst, nou):
        from fhort.pom.grading_utils import _norm

        nou_id = getattr(nou, 'id', None)
        if nou_id == inst.size_system_id:
            return
        # Treure el run (`None`) no deixa cap etiqueta orfe: el conjunt passa a no apuntar
        # enlloc i el motor el resol contra el run del MODEL, que és cap on va CAT2.1.
        if nou is None:
            return

        etiquetes_noves = {_norm(e) for e in nou.talles.values_list('etiqueta', flat=True)}
        orfes = defaultdict(list)
        for r in inst.regles.select_related('pom').all():
            lbl = (r.talla_break_label or '').strip()
            if lbl and _norm(lbl) not in etiquetes_noves:
                orfes[lbl].append(r.pom.codi_client if r.pom_id else f'#{r.id}')
        if not orfes:
            return

        if str(self.initial_data.get('confirmar_etiquetes_fora_del_run', '')).lower() in (
                'true', '1', 'yes', 'on'):
            return

        n_regles = sum(len(v) for v in orfes.values())
        raise ConflicteConfirmable({
            'conflict': True,
            'tipus': 'etiquetes_fora_del_run',
            'codi': 'GRADING_BREAK_LABELS_OUTSIDE_RUN',
            'grading_rule_set_id': inst.id,
            'grading_rule_set_nom': inst.nom,
            'size_system_nou': nou.codi,
            # Els POMs, TALLATS a 8 per etiqueta: la llista és per reconèixer-les, no per
            # auditar-les, i 86 codis en un diàleg no es llegeixen — es tanquen.
            'etiquetes': [
                {'etiqueta': lbl, 'regles': len(poms), 'poms': sorted(poms)[:8]}
                for lbl, poms in sorted(orfes.items(), key=lambda kv: -len(kv[1]))
            ],
            'regles_afectades': n_regles,
            'message': (
                f"{n_regles} regles de «{inst.nom}» trenquen a talles que {nou.codi} no té "
                f"({', '.join(sorted(orfes))}). Si continues, aquestes regles graduaran SENSE "
                f"trencament fins que se'ls doni una talla del run nou."),
        })

    def validate(self, attrs):
        inst = self.instance
        if inst is not None and 'size_system' in attrs:
            self._validar_canvi_de_run(inst, attrs['size_system'])
        # F-5 — GUARD DUR: un seed ISO (is_system_default) NO pot canviar d'eixos. El `disabled`
        # del front és UX; la seguretat real viu aquí (protegeix contra PATCH directes a l'API).
        if inst is not None and inst.is_system_default:
            if 'applies_to' in attrs:
                raise serializers.ValidationError(
                    {'applies_to': "No es pot canviar l'abast d'un ruleset de sistema (is_system_default)."})
            for f in ('targets', 'construction', 'fit_type', 'garment_group'):
                if f not in attrs:
                    continue
                if f == 'targets':
                    changed = (set(t.id for t in attrs[f])
                               != set(inst.targets.values_list('id', flat=True)))
                else:
                    changed = getattr(attrs[f], 'id', None) != getattr(inst, f'{f}_id')
                if changed:
                    raise serializers.ValidationError(
                        {f: "No es poden canviar els eixos d'un ruleset de sistema (is_system_default)."})
        return attrs

    class Meta:
        model = GradingRuleSet
        fields = (
            'id', 'nom', 'codi_sistema',
            'targets', 'targets_codis', 'target_codi',
            'construction', 'construction_codi',
            'fit_type', 'fit_type_codi',
            'garment_group', 'garment_group_nom', 'garment_group_codi',
            'garment_type_item', 'applies_to',
            'size_system', 'size_system_codi', 'size_system_nom',
            'customer', 'customer_codi', 'customer_nom',
            'origen',
            'is_system_default', 'actiu',
            'regles_count', 'regles',
        )
        # `origen` és NOMÉS lectura: el fixa el camí de creació (import-fitxa / size-map →
        # CLIENT_RUN; seeds → CANONICAL via backfill). El CRUD no l'ha de poder canviar.
        read_only_fields = ['is_system_default', 'regles', 'regles_count', 'origen']


class GarmentPOMMapSerializer(serializers.ModelSerializer):
    # U2/R2 (07/08) — `capa` i `instancia` SURTEN PER L'API. Eren al model des de C1/C1-ins i són
    # part de la CLAU ÚNICA, però no eren a `Meta.fields`: existien a la BD i eren invisibles per
    # a qualsevol lector d'API. La pantalla del catàleg en fa quatre columnes (Capa + el bloc
    # Instància), i sense això els seus desplegables i píndoles no tindrien on escriure.
    #
    # ⚠️ EL `default` NO ÉS DECORATIU, ÉS EL QUE EVITA UNA REGRESSIÓ. En completar-se la tupla de
    # la `unique_together`, DRF hi afegeix sol un `UniqueTogetherValidator` — que és justament el
    # que volem (un 400 net en comptes de l'`IntegrityError`/500 d'abans). Però el seu
    # `enforce_required_fields` exigeix TOTS els camps de la clau al `create`, i un camp de model
    # amb `default` només arriba a DRF com a `required=False`, SENSE default de serializer. Sense
    # aquests dos `default` explícits, tota crida que ja existeix —`MeasurementBaseGrid` crea amb
    # `{garment_type_item, pom, ordre}`— passaria a rebre un 400 «This field is required».
    # En PATCH parcial DRF salta els defaults i el validador omple des de la instància: `update`
    # amb només `{ordre}` segueix sense tocar ni la capa ni la instància.
    capa = serializers.CharField(max_length=20, default='exterior')
    instancia = serializers.CharField(max_length=60, default='', allow_blank=True)
    # Display fields amb FALLBACK a POMMaster (tenant-only, pom_global=None → els 19 importats per IA
    # no han de sortir buits): si no hi ha pom_global, caure a codi_client / nom_client / categoria FK.
    pom_code = serializers.SerializerMethodField()
    name_en = serializers.SerializerMethodField()
    name_cat = serializers.SerializerMethodField()
    abbreviation = serializers.SerializerMethodField()
    categoria = serializers.SerializerMethodField()
    applies_woven = serializers.BooleanField(source='pom.pom_global.applies_woven', read_only=True)
    applies_knit = serializers.BooleanField(source='pom.pom_global.applies_knit', read_only=True)
    applies_swim = serializers.BooleanField(source='pom.pom_global.applies_swim', read_only=True)

    # PAS B3-ter — bloc complet "com mesurar" des de pom.pom_global. Quan pom_global és None
    # (tenant-only, importats per IA) DRF retorna None en travessar el FK nul: el front els pinta
    # com "—", que és precisament el senyal de camp pendent de definir.
    start_point = serializers.CharField(source='pom.pom_global.start_point', read_only=True)
    end_point = serializers.CharField(source='pom.pom_global.end_point', read_only=True)
    reference_point = serializers.CharField(source='pom.pom_global.reference_point', read_only=True)
    scope = serializers.CharField(source='pom.pom_global.scope', read_only=True)
    orientation = serializers.CharField(source='pom.pom_global.orientation', read_only=True)
    state = serializers.CharField(source='pom.pom_global.state', read_only=True)
    line = serializers.CharField(source='pom.pom_global.line', read_only=True)
    body_section = serializers.CharField(source='pom.pom_global.body_section', read_only=True)
    tol_prod_cm = serializers.DecimalField(source='pom.pom_global.tol_prod_cm',
                                           max_digits=5, decimal_places=2, read_only=True)
    tol_samp_cm = serializers.DecimalField(source='pom.pom_global.tol_samp_cm',
                                           max_digits=5, decimal_places=2, read_only=True)
    iso_ref = serializers.CharField(source='pom.pom_global.iso_ref', read_only=True)
    unitat = serializers.CharField(source='pom.pom_global.unitat', read_only=True)
    descripcio_en = serializers.CharField(source='pom.pom_global.descripcio_en', read_only=True)
    descripcio_ca = serializers.CharField(source='pom.pom_global.descripcio_ca', read_only=True)
    body_measure_iso_codi = serializers.CharField(
        source='pom.pom_global.body_measure_iso.codi_iso', read_only=True)
    body_measure_iso_nom = serializers.CharField(
        source='pom.pom_global.body_measure_iso.nom_en', read_only=True)

    # Migration família → item COMPLETADA (PAS 6): la pertinença viu només a garment_type_item;
    # el FK legacy garment_type s'ha eliminat (migració 0016).
    garment_type_item_codi = serializers.CharField(source='garment_type_item.code', read_only=True)
    garment_type_item_name = serializers.CharField(source='garment_type_item.name', read_only=True)

    # FONT ÚNICA (22/08) — mateixa llei i mateix resolutor que la resta (ÀLIES > TENANT >
    # GLOBAL). La pertinença és de CATÀLEG (quins POMs porta una peça), no d'un model d'un
    # client: no hi ha àlies a passar-hi.
    def get_pom_code(self, obj):
        return codi_de(obj.pom)

    def get_name_en(self, obj):
        return noms_de(obj.pom)['nom_en']

    def get_name_cat(self, obj):
        return noms_de(obj.pom)['nom_ca']

    def get_abbreviation(self, obj):
        return abreviatura_de(obj.pom)

    def get_categoria(self, obj):
        return categoria_de(obj.pom)

    class Meta:
        model = GarmentPOMMap
        fields = (
            'id',
            'garment_type_item', 'garment_type_item_codi', 'garment_type_item_name',
            'pom',
            'pom_code', 'name_en', 'name_cat', 'abbreviation', 'categoria',
            'applies_woven', 'applies_knit', 'applies_swim',
            # PAS B3-ter — bloc complet "com mesurar"
            'start_point', 'end_point', 'reference_point',
            'scope', 'orientation', 'state', 'line', 'body_section',
            'tol_prod_cm', 'tol_samp_cm', 'iso_ref', 'unitat',
            'descripcio_en', 'descripcio_ca',
            'body_measure_iso_codi', 'body_measure_iso_nom',
            'is_key', 'obligatori', 'ordre', 'pendent_revisio',
            # U2/R2 — la identitat de la pertinença, que ja era clau única a la BD.
            'capa', 'instancia',
        )

    def validate_instancia(self, valor):
        """🔒 ELS DOS EIXOS DE LA POSICIÓ (22-23/08): fins a UNA etiqueta per eix.

        La pertinença és l'ALTRA porta on s'escriu una instància (la pantalla del catàleg, amb
        les seves píndoles). Si la llei només visqués a la porta de les mesures, el mateix slug
        impossible entraria per aquí i la mesura que en naixés l'heretaria.
        """
        from fhort.pom.models import MeasurementInstance
        mal = MeasurementInstance.error_de_combinacio(valor)
        if mal:
            raise serializers.ValidationError(mal)
        return valor


class _POMDisplayMixin(serializers.Serializer):
    """Els camps de display d'un POM, amb el FALLBACK de sempre: `pom_global` si n'hi ha, i si
    no (tenant-only, els importats per IA) el que digui `POMMaster`.

    U2 — viu en un mixin perquè les DUES pertinences noves (família i grup) l'han de dir igual
    que la de l'item. `GarmentPOMMapSerializer` **no s'ha tocat**: convergir-lo aquí és una
    millora òbvia però toca un serializer viu amb 103 lectors, i aquest sprint no ho demanava.
    ANOTAT al report com a deute.
    """
    pom_code = serializers.SerializerMethodField()
    name_en = serializers.SerializerMethodField()
    name_cat = serializers.SerializerMethodField()
    abbreviation = serializers.SerializerMethodField()
    categoria = serializers.SerializerMethodField()
    unitat = serializers.CharField(source='pom.pom_global.unitat', read_only=True)

    #: Els camps que el mixin aporta, per no repetir-los a cada `Meta.fields`.
    CAMPS = ('pom_code', 'name_en', 'name_cat', 'abbreviation', 'categoria', 'unitat')

    # FONT ÚNICA (22/08) — mateixa llei i mateix resolutor que la resta (ÀLIES > TENANT >
    # GLOBAL). La pertinença és de CATÀLEG (quins POMs porta una peça), no d'un model d'un
    # client: no hi ha àlies a passar-hi.
    def get_pom_code(self, obj):
        return codi_de(obj.pom)

    def get_name_en(self, obj):
        return noms_de(obj.pom)['nom_en']

    def get_name_cat(self, obj):
        return noms_de(obj.pom)['nom_ca']

    def get_abbreviation(self, obj):
        return abreviatura_de(obj.pom)

    def get_categoria(self, obj):
        return categoria_de(obj.pom)


class GarmentTypePOMMapSerializer(_POMDisplayMixin, serializers.ModelSerializer):
    """U2 — els POMs que aporta una FAMÍLIA. Germà del de l'item, mateixa forma."""

    garment_type_codi = serializers.CharField(source='garment_type.codi_client', read_only=True)
    garment_type_nom = serializers.CharField(source='garment_type.nom_client', read_only=True)

    class Meta:
        model = GarmentTypePOMMap
        fields = (('id', 'garment_type', 'garment_type_codi', 'garment_type_nom', 'pom')
                  + _POMDisplayMixin.CAMPS
                  + ('is_key', 'obligatori', 'nivell', 'ordre', 'pendent_revisio',
                     'capa', 'instancia'))


class GarmentGroupPOMMapSerializer(_POMDisplayMixin, serializers.ModelSerializer):
    """U2 — els POMs que aporta un GRUP, el nivell més bast de l'acumulació."""

    garment_group_codi = serializers.CharField(source='garment_group.codi', read_only=True)
    garment_group_nom = serializers.CharField(source='garment_group.nom', read_only=True)

    class Meta:
        model = GarmentGroupPOMMap
        fields = (('id', 'garment_group', 'garment_group_codi', 'garment_group_nom', 'pom')
                  + _POMDisplayMixin.CAMPS
                  + ('is_key', 'obligatori', 'nivell', 'ordre', 'pendent_revisio',
                     'capa', 'instancia'))


class ItemBaseSetSerializer(serializers.ModelSerializer):
    """BaseSet condicionat d'un Item (B1). El món = size_system x fit; la talla base s'hi declara.

    Els camps de display eviten que el catàleg hagi de fer una crida per set només per pintar
    «ALPHA_EU_M · Regular · L · 37 mesures». `mesures_count` ve anotat del ViewSet, no per fila.
    """
    size_system_codi = serializers.CharField(source='size_system.codi', read_only=True)
    fit_type_codi = serializers.CharField(source='fit_type.codi', read_only=True, default=None)
    base_size_label = serializers.CharField(
        source='base_size_definition.etiqueta', read_only=True)
    mesures_count = serializers.IntegerField(read_only=True, default=0)
    # Quantes en tenen VALOR: un set de 37 files buides no és el mateix que un de 37 mesurades,
    # i la columna del cataleg ha de poder-ho dir sense obrir la graella.
    mesures_amb_valor = serializers.IntegerField(read_only=True, default=0)
    updated_by_nom = serializers.CharField(source='updated_by.username', read_only=True,
                                           default=None)

    class Meta:
        model = ItemBaseSet
        fields = (
            'id', 'garment_type_item', 'size_system', 'size_system_codi',
            'fit_type', 'fit_type_codi', 'base_size_definition', 'base_size_label',
            'mesures_count', 'mesures_amb_valor',
            # `origen` read_only: el determina el CAMI (promocio = PROMOCIO . cataleg = MANUAL .
            # paquet = MASTER), mai el body — mateixa regla que a ItemBaseMeasurement.
            'origen', 'created_at', 'updated_at', 'updated_by', 'updated_by_nom',
        )
        read_only_fields = ('origen', 'created_at', 'updated_at', 'updated_by')

    def validate(self, attrs):
        # La talla base ha de viure al sistema del set. clean() ho diu al model; aqui es fa
        # explicit perque el DRF retorni 400 amb el camp assenyalat i no un 500 d'IntegrityError.
        sistema = attrs.get('size_system') or getattr(self.instance, 'size_system', None)
        talla = attrs.get('base_size_definition') or getattr(
            self.instance, 'base_size_definition', None)
        if sistema is not None and talla is not None and talla.size_system_id != sistema.pk:
            raise serializers.ValidationError({
                'base_size_definition': 'La talla base ha de pertanyer al sistema de talles del set.'
            })
        return attrs


class ItemBaseMeasurementSerializer(serializers.ModelSerializer):
    """Valor base + toleràncies de la plantilla de l'Item, per (item, pom). Sprint Mesures Base
    per Item (P3). Inclou display del POM (codi/nom) per a la columna del POMBrowser ASSIGN (P4)."""
    pom_codi = serializers.CharField(source='pom.codi_client', read_only=True)
    pom_nom = serializers.CharField(source='pom.nom_client', read_only=True)
    # P9 — qui i quan. `updated_by_nom` és display; l'autoria mateixa no s'escriu per API.
    updated_by_nom = serializers.CharField(source='updated_by.username', read_only=True,
                                           default=None)

    class Meta:
        model = ItemBaseMeasurement
        fields = (
            'id', 'garment_type_item', 'base_set', 'pom', 'pom_codi', 'pom_nom',
            'base_value_cm', 'tol_minus', 'tol_plus', 'nom_fitxa',
            # P9 — PROVINENÇA: read_only sencera. `origen` el determina el CAMÍ d'escriptura
            # (ViewSet = MANUAL · promoció = PROMOTED · loader = IMPORTED), mai el body: si
            # fos escrivible, qualsevol client podria signar un valor com a promogut.
            'origen', 'created_at', 'updated_at', 'updated_by', 'updated_by_nom',
        )
        read_only_fields = ('origen', 'created_at', 'updated_at', 'updated_by')


class CustomerPOMAliasSerializer(serializers.ModelSerializer):
    """Biblioteca de nomenclatura del client: (client_code, client_description) → POM canònic.
    Font de sembra per-client del matcher (find_pom_master, estratègia (a))."""
    # SerializerMethodField (no `source='pom.codi_client'`): el pom és NULLABLE — un àlies pot
    # ser vocabulari del client pendent de mapar (QA-S8-R1) — i la travessia de `source` sobre
    # un FK nul no és de fiar. Aquí el None és explícit i el frontend hi pinta "pendent de mapar".
    pom_codi = serializers.SerializerMethodField()
    pom_nom = serializers.SerializerMethodField()
    customer_codi = serializers.CharField(source='customer.codi', read_only=True)
    # Identificació canònica del POM (mateix patró que GradingRuleSerializer): codi global
    # (POM-XXX) com a element principal + abreviatura + nom EN/CA per al display de la fitxa.
    pom_code_global = serializers.SerializerMethodField()
    pom_abbreviation = serializers.SerializerMethodField()
    pom_nom_en = serializers.SerializerMethodField()
    pom_nom_ca = serializers.SerializerMethodField()

    def get_pom_codi(self, obj):
        return obj.pom.codi_client if obj.pom_id else None

    def get_pom_nom(self, obj):
        return obj.pom.nom_client if obj.pom_id else None

    def get_pom_code_global(self, obj):
        if obj.pom and obj.pom.pom_global:
            return obj.pom.pom_global.codi
        return None

    # FONT ÚNICA (22/08). Aquí NO s'hi passa l'àlies encara que la fila EN SIGUI un: aquests
    # camps descriuen el POM de destí perquè qui llegeix la biblioteca pugui dir «U1 és
    # BUTTON SPACING al catàleg» — si hi caiguessin els camps de la pròpia fila, la columna
    # repetiria el `client_code` que ja hi ha al costat.
    def get_pom_abbreviation(self, obj):
        return abreviatura_de(obj.pom) if obj.pom_id else None

    def get_pom_nom_en(self, obj):
        return noms_de(obj.pom)['nom_en'] if obj.pom_id else None

    def get_pom_nom_ca(self, obj):
        return noms_de(obj.pom)['nom_ca'] if obj.pom_id else None

    class Meta:
        model = CustomerPOMAlias
        fields = (
            'id', 'customer', 'customer_codi', 'pom', 'pom_codi', 'pom_nom',
            'pom_code_global', 'pom_abbreviation', 'pom_nom_en', 'pom_nom_ca',
            # description_en/local + language són els camps VIUS de la descripció (models.py:262-264):
            # els escriu el diccionari (dictionary_views.py:167-168). Sense exposar-los, la
            # biblioteca no en podia pintar cap (QA-S8 · D4b). `client_description` es manté al
            # contracte només com a LLEGAT (camp obsolet, models.py:255-258).
            'client_code', 'client_description', 'description_en', 'description_local', 'language',
            'origen', 'pendent_revisio',
            'creat_at', 'actualitzat_at',
        )
        read_only_fields = ('creat_at', 'actualitzat_at')
