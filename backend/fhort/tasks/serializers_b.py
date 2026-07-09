from rest_framework import serializers
from .models import (TaskType, ModelTask, Supplier, Production,
                     GarmentTypeItem, TaskTimeEstimate, Customer)
from .services_c import rectification_count


class TaskTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskType
        # B1: s'exposen fase/eina/mode (additiu, read-only) perquè l'arbre de tasques agrupi per
        # fase i pugui navegar a l'eina correcta en iniciar. Referència sempre per `code` (G9).
        fields = ['id', 'code', 'name', 'default_order', 'active', 'fase', 'eina', 'mode']


class ModelTaskSerializer(serializers.ModelSerializer):
    task_type_code = serializers.CharField(source='task_type.code', read_only=True)
    task_type_name = serializers.CharField(source='task_type.name', read_only=True)
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    rectifications = serializers.SerializerMethodField()

    class Meta:
        model = ModelTask
        fields = ['id', 'model', 'model_codi', 'task_type', 'task_type_code', 'task_type_name',
                  'status', 'origen', 'assignee', 'order', 'created_at', 'updated_at',
                  'started_at', 'finished_at', 'estimated_minutes', 'rectifications',
                  'planned_start', 'planned_end', 'planned_locked',
                  'work_order', 'off_recipe']
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
                            'work_order', 'off_recipe']

    def get_rectifications(self, obj):
        return rectification_count(obj)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'type', 'active',
                  # Comercial Studio (B1) — dades fiscals/compra/contacte (additives, blank).
                  'rao_social', 'nif', 'adreca_linia1', 'adreca_linia2', 'ciutat', 'codi_postal',
                  'pais', 'condicions_compra', 'persona_contacte', 'telefon_contacte', 'email_contacte']


class CustomerSerializer(serializers.ModelSerializer):
    # Comptadors agregats (annotate del CustomerViewSet). SerializerMethodField amb default 0 perquè
    # les respostes fora de list (create/update) — que no venen annotades — no petin.
    quotes_sent = serializers.SerializerMethodField()
    quotes_accepted = serializers.SerializerMethodField()
    orders_open = serializers.SerializerMethodField()
    delivery_notes_count = serializers.SerializerMethodField()

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
                  # Pàgina Clients (annotate): ofertes presentades/acceptades, comandes obertes, albarans.
                  'quotes_sent', 'quotes_accepted', 'orders_open', 'delivery_notes_count']
        read_only_fields = ['logo']

    def get_quotes_sent(self, o):
        return getattr(o, 'cnt_quotes_sent', 0) or 0

    def get_quotes_accepted(self, o):
        return getattr(o, 'cnt_quotes_accepted', 0) or 0

    def get_orders_open(self, o):
        return getattr(o, 'cnt_orders_open', 0) or 0

    def get_delivery_notes_count(self, o):
        return getattr(o, 'cnt_delivery_notes', 0) or 0


class ProductionSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = Production
        fields = ['id', 'model', 'phase', 'supplier', 'supplier_name', 'status',
                  'requested_at', 'expected_at', 'delivered_at', 'requested_by', 'notes']
        read_only_fields = ['requested_at', 'delivered_at', 'status', 'requested_by']


class GarmentTypeItemSerializer(serializers.ModelSerializer):
    # Sprint Llibreria d'Items (B3b): camps de completesa READ-ONLY per a la graella de cards de
    # Garment Types (nom del ruleset, etiqueta de la talla base, compte de POMs). Additius; no
    # afecten el write path (la pàgina d'autoria escriu via els FK grading_rule_set/base_size_definition).
    grading_rule_set_nom = serializers.SerializerMethodField()
    base_size_label = serializers.SerializerMethodField()
    poms_count = serializers.SerializerMethodField()

    class Meta:
        model = GarmentTypeItem
        # Sprint Llibreria d'Items (B3a): exposa el context de grading de l'Item (FK ruleset) i
        # la talla base, escrivibles per la pàgina d'autoria (Fase B). Tots dos nullable.
        fields = ['id', 'garment_type', 'code', 'name', 'complexity_order', 'active',
                  'grading_rule_set', 'base_size_definition',
                  'grading_rule_set_nom', 'base_size_label', 'poms_count']

    def get_grading_rule_set_nom(self, obj):
        return obj.grading_rule_set.nom if obj.grading_rule_set_id else None

    def get_base_size_label(self, obj):
        return obj.base_size_definition.etiqueta if obj.base_size_definition_id else None

    def get_poms_count(self, obj):
        # Pertinença POM de l'item (GarmentPOMMap.related_name='pom_maps').
        return obj.pom_maps.count()

    def validate(self, attrs):
        # B3a — DRF no crida Model.clean() sol; l'invoquem aquí perquè el constrenyiment d'A3
        # (base_size_definition.size_system == grading_rule_set.size_system) es validi al desar
        # via serializer. Fusiona els attrs entrants amb la instància existent (PATCH parcial) i
        # delega al clean() del model (font única; cas null = skip, sense error).
        from django.core.exceptions import ValidationError as DjangoValidationError
        grs = attrs.get('grading_rule_set', getattr(self.instance, 'grading_rule_set', None))
        bsd = attrs.get('base_size_definition', getattr(self.instance, 'base_size_definition', None))
        probe = GarmentTypeItem(grading_rule_set=grs, base_size_definition=bsd)
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
