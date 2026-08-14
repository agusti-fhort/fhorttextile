from rest_framework import serializers

from fhort.accounts.capabilities import PodaEconomicaMixin

from .models import (TaskType, ModelTask, Supplier, Production,
                     GarmentTypeItem, GarmentTypeItemPart, TaskTimeEstimate, Customer)
from .services_c import rectification_count


class TaskTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskType
        # B1: s'exposen fase/eina/mode (additiu, read-only) perquè l'arbre de tasques agrupi per
        # fase i pugui navegar a l'eina correcta en iniciar. Referència sempre per `code` (G9).
        # F2.0 — `tipus` i `es_lliurable` s'hi afegeixen perquè la UI sàpiga QUÈ té davant sense
        # inventar-s'ho: `tipus` decideix si la tasca admet temps declarat (F2.5, Externa-lliure)
        # i `es_lliurable` si compta per a l'avís de ronda lliurada (F2.7).
        # T1 — `visible` s'hi afegeix perquè la UI sàpiga QUÈ ha d'oferir sense mantenir cap
        # llista pròpia de codis: qui decideix si una targeta es pinta és el catàleg.
        fields = ['id', 'code', 'name', 'default_order', 'active', 'fase', 'eina', 'mode',
                  'tipus', 'es_lliurable', 'visible']


class ModelTaskSerializer(serializers.ModelSerializer):
    """F2.0 — EL CONTRACTE QUE LA UI DE F2 NECESSITA.

    F1 va construir la genealogia (`ronda`, `mare`, `motiu`) i les regles noves (albarà, batec,
    exclusió per trams) però **no en va exposar res**: el serializer seguia sent el de Sprint B.
    La UI de F2 ha de decidir quina cara del modal ensenya, i no pot deduir-ho de l'`status`.

    Els sis camps derivats responen sis preguntes concretes, totes read-only:

      · `es_vigent`      — és AQUESTA la tasca que `tasca_vigent` resol per al seu code?
      · `ronda_seq`      — de quina volta és (null = la 1a, implícita)
      · `albaranada`     — té línia en albarà EMÈS? (la paret de D-5; cara C del modal)
      · `obert_per`/`_nom` — QUI la té oberta ara, segons el TRAM (no segons `assignee`)
      · `es_lliurable`   — el seu tipus produeix lliurable (F2.7)
      · `tipus_extern`   — admet temps declarat (F2.5)

    ⚠️ `obert_per` mira `TimerEntrada`, no `assignee`. És la lliçó de F1.5: `assignee` és
    planificació i el rellotge és realitat, i confondre-les és el que va trencar l'exclusió.
    """

    task_type_code = serializers.CharField(source='task_type.code', read_only=True)
    task_type_name = serializers.CharField(source='task_type.name', read_only=True)
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    rectifications = serializers.SerializerMethodField()
    assignee_nom = serializers.CharField(source='assignee.nom_complet', read_only=True,
                                         default=None)
    es_lliurable = serializers.BooleanField(source='task_type.es_lliurable', read_only=True)
    tipus_extern = serializers.SerializerMethodField()
    ronda_seq = serializers.IntegerField(source='ronda.seq', read_only=True, default=None)
    es_vigent = serializers.SerializerMethodField()
    albaranada = serializers.SerializerMethodField()
    obert_per = serializers.SerializerMethodField()
    obert_per_nom = serializers.SerializerMethodField()
    # T4 — el modal d'acabar diu en veu alta quant temps s'està tancant: la sessió que s'acaba i
    # el total de la tasca. Sense això la decisió es pren a cegues, i és la que porta a albarà.
    temps_consumit_min = serializers.SerializerMethodField()
    sessio_inici = serializers.SerializerMethodField()

    class Meta:
        model = ModelTask
        fields = ['id', 'model', 'model_codi', 'task_type', 'task_type_code', 'task_type_name',
                  'status', 'origen', 'assignee', 'order', 'created_at', 'updated_at',
                  'started_at', 'finished_at', 'estimated_minutes', 'rectifications',
                  'planned_start', 'planned_end', 'planned_locked',
                  'work_order', 'off_recipe', 'fitting_session',
                  # F2.0 — genealogia (F1.1) + estat derivat per al modal de F2.1.
                  'ronda', 'ronda_seq', 'mare', 'motiu',
                  'assignee_nom', 'es_lliurable', 'tipus_extern',
                  'es_vigent', 'albaranada', 'obert_per', 'obert_per_nom',
                  'temps_consumit_min', 'sessio_inici']
        # started_at/finished_at els gestiona la transició; estimated_minutes és snapshot → read-only.
        # origen el fixa el backend en crear (prevista per defecte; ad_hoc des de l'arbre global,
        # Sprint 4) → read-only per al client.
        # planned_* els escriu el MOTOR (planning), no el client → read-only.
        # ⚠️ Fus horari: aquí planned_start/end surten en UTC (USE_TZ=True). El front de
        # planificació NO ha de barrejar aquesta font amb les respostes del motor
        # (plan/compute|preview|apply, que van en ISO LOCAL). Aquests camps són per a
        # referència/llista; el Gantt pinta des de plan/compute (local).
        read_only_fields = ['created_at', 'updated_at', 'origen',
                            'started_at', 'finished_at', 'estimated_minutes',
                            'planned_start', 'planned_end', 'planned_locked',
                            'work_order', 'off_recipe', 'fitting_session',
                            # La genealogia l'escriu `obrir_ronda`, mai el client.
                            'ronda', 'mare', 'motiu']

    def get_rectifications(self, obj):
        return rectification_count(obj)

    def get_tipus_extern(self, obj):
        return obj.task_type.tipus == 'Externa-lliure'

    def get_es_vigent(self, obj):
        """La resolució la fa `tasca_vigent`, mai el client: si la UI se la reimplementés,
        tornaríem a tenir dos criteris (§S-4)."""
        from .services_r import tasca_vigent
        vigent = tasca_vigent(obj.model_id, obj.task_type.code)
        return bool(vigent and vigent.pk == obj.pk)

    def get_albaranada(self, obj):
        """La paret de D-5, precalculada. El modal de F2.1 no pot dependre NOMÉS del 409:
        ha de poder ensenyar la cara C abans que l'usuari piqui contra la porta."""
        return obj.delivery_note_lines.filter(
            delivery_note__status__in=['ISSUED', 'INVOICED']).exists()

    def _tram_obert(self, obj):
        return (obj.timers.filter(fi__isnull=True, actiu=True)
                .select_related('tecnic').order_by('-inici').first())

    def get_temps_consumit_min(self, obj):
        """Minuts SANS acumulats. Mateixa higiene que el recompute i que l'albarà: els trams
        desbocats no són temps treballat, i aquí no poden dir una xifra diferent."""
        from .services_i import _real_minutes
        return _real_minutes(obj)

    def get_sessio_inici(self, obj):
        """Quan va començar el tram OBERT (null si no n'hi ha cap). El modal en calcula la
        sessió; el serializer no li dóna una durada perquè el rellotge corre mentre es llegeix."""
        tram = obj.timers.filter(fi__isnull=True, actiu=True).first()
        return tram.inici.isoformat() if tram else None

    def get_obert_per(self, obj):
        tram = self._tram_obert(obj)
        return tram.tecnic_id if tram else None

    def get_obert_per_nom(self, obj):
        tram = self._tram_obert(obj)
        return tram.tecnic.nom_complet if tram else None


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'type', 'active',
                  # Comercial Studio (B1) — dades fiscals/compra/contacte (additives, blank).
                  'rao_social', 'nif', 'adreca_linia1', 'adreca_linia2', 'ciutat', 'codi_postal',
                  'pais', 'condicions_compra', 'persona_contacte', 'telefon_contacte', 'email_contacte']


class CustomerSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
    #: `descompte_pct` és condició comercial. El Dashboard (la home de TOTHOM) carrega
    #: `customers.list({page_size:200})` (`frontend/src/pages/Dashboard.jsx:233`) i el
    #: CustomerSelector el fa servir des del wizard de models: el descompte de tots els
    #: clients arribava a qualsevol tècnic (diagnosi 2026-08-14 §3.1).
    CAMPS_ECONOMICS = ('descompte_pct',)

    # Comptadors agregats (annotate del CustomerViewSet). SerializerMethodField amb default 0 perquè
    # les respostes fora de list (create/update) — que no venen annotades — no petin.
    quotes_sent = serializers.SerializerMethodField()
    quotes_accepted = serializers.SerializerMethodField()
    orders_open = serializers.SerializerMethodField()
    delivery_notes_count = serializers.SerializerMethodField()
    # P8 — l'estat del PONT amb el tenant connectat. Read-only i derivat: el vincle és
    # patrimoni del Brand i el Studio només el consulta. None quan el client no està connectat.
    vincle_estat = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        # logo: ImageField → URL (absoluta si el ViewSet passa `request` al context, que és
        # el cas per defecte de ModelViewSet). read_only: s'escriu via l'acció upload-logo.
        fields = ['id', 'codi', 'nom', 'active', 'is_self', 'logo',
                  # Comercial Studio (B1) — dades fiscals/comercials (additives, blank).
                  'rao_social', 'nif', 'adreca_linia1', 'adreca_linia2', 'ciutat', 'codi_postal',
                  'pais', 'email_facturacio', 'condicions_pagament', 'descompte_pct',
                  'persona_contacte', 'telefon_contacte',
                  # Comercial Studio (B3a) — règim fiscal + condicions de pagament per defecte.
                  'tax_regime', 'vat_number', 'payment_method', 'payment_terms',
                  # Idioma per defecte dels PDF comercials (default del selector d'emissió).
                  'language',
                  # Pàgina Clients (annotate): ofertes presentades/acceptades, comandes obertes, albarans.
                  'quotes_sent', 'quotes_accepted', 'orders_open', 'delivery_notes_count',
                  # P8 (Federació v2) — connexió amb un tenant Brand. `codi_global` és el ganxo
                  # (codi nu del Brand) i `vincle_estat` l'estat del pont, tots dos de lectura:
                  # s'escriuen NOMÉS per l'acció `vincular-token`, que és qui valida el token.
                  'codi_global', 'vincle_estat']
        # is_self: la sembra el fixa (migració 0020 / bootstrap_tenant / load_losan_package, tots
        # per ORM, cap via aquest serializer). Read-only perquè, si no, un PATCH `is_self:false`
        # desarmaria el blindatge d'esborrat/desactivació del client propi (views_b.py).
        # codi_global: escriure'l per PATCH permetria declarar-se connectat a un Brand sense
        # presentar-ne mai el token — precisament el que l'acció `vincular-token` existeix per
        # impedir. Read-only aquí, i l'única porta és aquella.
        read_only_fields = ['logo', 'is_self', 'codi_global']

    def get_vincle_estat(self, o):
        """Estat del TenantLink entre el Brand connectat i AQUEST tenant. Sense connexió, None.

        Es consulta a `public` sense schema_context: `tenants_tenantlink` només existeix allà i
        el search_path del tenant ja hi arriba (diagnosi P7 §A1). Cap query per als clients no
        connectats, que són la immensa majoria de la llista.
        """
        if not o.codi_global:
            return None
        from fhort.tenants.models import TenantLink
        req = self.context.get('request')
        meu = getattr(getattr(req, 'tenant', None), 'codi_tenant', None)
        if meu is None:
            return None
        link = TenantLink.objects.filter(
            brand_codi_tenant=o.codi_global, studio_codi_tenant=meu).only('estat').first()
        return link.estat if link else None

    def get_quotes_sent(self, o):
        return getattr(o, 'quotes_sent', 0) or 0

    def get_quotes_accepted(self, o):
        return getattr(o, 'quotes_accepted', 0) or 0

    def get_orders_open(self, o):
        return getattr(o, 'orders_open', 0) or 0

    def get_delivery_notes_count(self, o):
        return getattr(o, 'delivery_notes_count', 0) or 0


class ProductionSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = Production
        fields = ['id', 'model', 'phase', 'supplier', 'supplier_name', 'status',
                  'requested_at', 'expected_at', 'delivered_at', 'requested_by', 'notes']
        read_only_fields = ['requested_at', 'delivered_at', 'status', 'requested_by']


class GarmentTypeItemPartSerializer(serializers.ModelSerializer):
    """Composició d'un item-conjunt (SET-1). READ-ONLY dins de GarmentTypeItemSerializer: el
    PATCH genèric del ModelViewSet no escriu relacions inverses, i escriure-les per aquí
    obligaria a inventar-se una semàntica de merge parcial. L'escriptura té acció pròpia
    (`PUT /garment-type-items/<id>/parts/`), que és REEMPLAÇAMENT declarat de la llista."""
    part_item_code = serializers.CharField(source='part_item.code', read_only=True)
    part_item_name = serializers.CharField(source='part_item.name', read_only=True)

    class Meta:
        model = GarmentTypeItemPart
        fields = ['id', 'part_item', 'part_item_code', 'part_item_name', 'ordre', 'nom_peca']


class GarmentTypeItemSerializer(serializers.ModelSerializer):
    # Sprint Llibreria d'Items (B3b): camps de completesa READ-ONLY per a la graella de cards de
    # Garment Types (nom del ruleset, etiqueta de la talla base, compte de POMs). Additius; no
    # afecten el write path (la pàgina d'autoria escriu via els FK grading_rule_set/base_size_definition).
    grading_rule_set_nom = serializers.SerializerMethodField()
    base_size_label = serializers.SerializerMethodField()
    # S03c · C2.1 — anotats al queryset del ViewSet, no calculats per fila. `poms_count` feia
    # `obj.pom_maps.count()` (N+1). `default=0`: la resposta d'un POST/PUT serialitza la
    # instància desada, que no ve del queryset i no porta les anotacions.
    poms_count = serializers.IntegerField(read_only=True, default=0)
    fitxers_count = serializers.IntegerField(read_only=True, default=0)
    # SET-1 — la composició, niuada en LECTURA. L'escriptura va per l'acció `parts/` (vegeu
    # GarmentTypeItemPartSerializer). `is_set` sí és escrivible pel PATCH genèric: és un camp
    # concret de la taula, i és la declaració que la decisió 3 posa a mans de l'autoria.
    parts = GarmentTypeItemPartSerializer(many=True, read_only=True)
    # U2/R3 — el nom del run PROPOSAT, per a la columna «Run de talles» de la llista del catàleg.
    # Read-only i amb el mateix patró que `grading_rule_set_nom`: el que s'escriu és el FK.
    proposed_size_system_nom = serializers.SerializerMethodField()

    class Meta:
        model = GarmentTypeItem
        # Sprint Llibreria d'Items (B3a): exposa el context de grading de l'Item (FK ruleset) i
        # la talla base, escrivibles per la pàgina d'autoria (Fase B). Tots dos nullable.
        fields = ['id', 'garment_type', 'code', 'name', 'complexity_order', 'active',
                  'is_set', 'parts',
                  'grading_rule_set', 'base_size_definition',
                  'grading_rule_set_nom', 'base_size_label', 'poms_count', 'fitxers_count',
                  # U2/R3 — la PROPOSTA de l'item: run i talla base. Escrivibles per la pantalla
                  # del catàleg; no manen sobre el joc de regles ni sobre cap ItemBaseSet.
                  'proposed_size_system', 'proposed_base_size_label', 'proposed_size_system_nom']

    def get_grading_rule_set_nom(self, obj):
        return obj.grading_rule_set.nom if obj.grading_rule_set_id else None

    def get_proposed_size_system_nom(self, obj):
        return obj.proposed_size_system.nom if obj.proposed_size_system_id else None

    def get_base_size_label(self, obj):
        return obj.base_size_definition.etiqueta if obj.base_size_definition_id else None

    def validate(self, attrs):
        # B3a — DRF no crida Model.clean() sol; l'invoquem aquí perquè el constrenyiment d'A3
        # (base_size_definition.size_system == grading_rule_set.size_system) es validi al desar
        # via serializer. Fusiona els attrs entrants amb la instància existent (PATCH parcial) i
        # delega al clean() del model (font única; cas null = skip, sense error).
        from django.core.exceptions import ValidationError as DjangoValidationError
        grs = attrs.get('grading_rule_set', getattr(self.instance, 'grading_rule_set', None))
        bsd = attrs.get('base_size_definition', getattr(self.instance, 'base_size_definition', None))
        # U2/R3 — el probe ha de portar TAMBÉ la proposta: si no, la seva branca del clean()
        # veuria sempre els camps buits i la validació no s'executaria mai per API. Mateixa
        # fusió (attrs sobre instància) perquè el PATCH parcial es validi contra el que ja hi ha.
        pss = attrs.get('proposed_size_system',
                        getattr(self.instance, 'proposed_size_system', None))
        pbl = attrs.get('proposed_base_size_label',
                        getattr(self.instance, 'proposed_base_size_label', '') or '')
        probe = GarmentTypeItem(grading_rule_set=grs, base_size_definition=bsd,
                                proposed_size_system=pss, proposed_base_size_label=pbl)
        try:
            probe.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                getattr(e, 'message_dict', None) or {'base_size_definition': e.messages})
        return attrs


class TaskTimeEstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskTimeEstimate
        fields = ['id', 'garment_type_item', 'task_type', 'estimated_minutes']
