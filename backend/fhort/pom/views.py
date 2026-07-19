from django.db import transaction
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from fhort.accounts.capabilities import HasCapability, CONFIGURE

from .models import (
    CustomerPOMAlias,
    GarmentGroup,
    GarmentPOMMap,
    GarmentType,
    GradingRule,
    GradingRuleSet,
    ItemBaseMeasurement,
    POMCategory,
    POMMaster,
    SizeDefinition,
    SizeSystem,
    SizingProfile,
)
from .serializers import (
    CustomerPOMAliasSerializer,
    GarmentGroupSerializer,
    GarmentPOMMapSerializer,
    GarmentTypeSerializer,
    GradingRuleSerializer,
    GradingRuleSetSerializer,
    ItemBaseMeasurementSerializer,
    POMCategorySerializer,
    POMMasterSerializer,
    SizeDefinitionSerializer,
    SizeSystemSerializer,
)


class _ConfigureWrite(HasCapability):
    """Escriptura del domini de talles gated CONFIGURE (lectura intacta).
    Reutilitza HasCapability d'accounts.capabilities."""
    required_capability = CONFIGURE


class POMMasterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = POMMasterSerializer
    queryset = POMMaster.objects.select_related(
        'pom_global', 'pom_global__body_measure_iso', 'categoria').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['actiu', 'pom_global']
    search_fields = ['codi_client', 'nom_client']
    ordering_fields = ['codi_client', 'nom_client']
    ordering = ['codi_client']


class SizeSystemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SizeSystemSerializer
    queryset = SizeSystem.objects.prefetch_related('talles').all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    # LLEI 5 CAPES: el pas «Talles» del wizard llista SizeSystems PURS (escala, capa 3) filtrats
    # pel target de la peça. `targets` (M2M) additiu al filterset → GET size-systems/?targets=<id>.
    filterset_fields = ['actiu', 'targets']
    search_fields = ['codi', 'nom']
    ordering = ['codi']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [_ConfigureWrite()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.talles.exists():
            return Response(
                {'error': 'Elimina primer les talles associades'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class SizeDefinitionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SizeDefinitionSerializer
    queryset = SizeDefinition.objects.select_related('size_system').all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['size_system']
    ordering = ['size_system', 'ordre']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [_ConfigureWrite()]
        return [IsAuthenticated()]


class GarmentTypeViewSet(viewsets.ModelViewSet):
    serializer_class = GarmentTypeSerializer
    # `items_count` a la BD, no per fila: l'arbre del Finder mostra el compte d'items de cada
    # garment type i un SerializerMethodField hi faria un N+1 de 19 queries (taula #4).
    #
    # `order_by` explícit: `annotate()` afegeix GROUP BY i Django descarta l'ordenació per
    # defecte a les queries agregades. Aquí no n'hi havia cap de real (Meta.ordering és buit i
    # l'atribut `ordering` de sota és inert sense OrderingFilter al filter_backends), i la
    # paginació sense ORDER BY pot repetir o saltar files entre pàgines.
    queryset = (GarmentType.objects
                .select_related('garment_type_global')
                .annotate(items_count=Count('items'))
                .order_by('codi_client'))
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['actiu', 'grup']
    search_fields = ['codi_client', 'nom_client']
    ordering = ['codi_client']

    def get_queryset(self):
        # `?target=<codi>` — cascada del wizard: només les famílies COMPATIBLES amb el target.
        # La compatibilitat target↔família viu a SizingProfile (target + garment_type poblats; vegeu
        # docs/diagnosis/DIAGNOSI_WIZARD_CASCADA_TARGET.md). Sense `target` → catàleg complet.
        qs = super().get_queryset()
        target = self.request.query_params.get('target')
        if target:
            from fhort.pom.models import SizingProfile
            qs = qs.filter(id__in=SizingProfile.objects
                           .filter(target__codi=target)
                           .values('garment_type'))
        return qs

    def get_permissions(self):
        # Lectura: autenticat. Escriptura: configure (alineat amb GarmentTypeItem/TaskTimeEstimate).
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        perm = HasCapability(); self.required_capability = CONFIGURE
        return [perm]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system:
            return Response(
                {'error': 'No es pot esborrar un tipus de sistema.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class GarmentGroupViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GarmentGroupSerializer
    queryset = GarmentGroup.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['actiu']
    search_fields = ['codi', 'nom']
    ordering = ['codi']


class POMCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = POMCategorySerializer
    queryset = POMCategory.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['actiu', 'body_area']
    search_fields = ['codi', 'nom_en', 'nom_ca']
    ordering = ['display_order', 'codi']


class GradingRuleSetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GradingRuleSetSerializer
    queryset = (
        GradingRuleSet.objects
        .select_related('garment_group', 'size_system')
        .prefetch_related('regles')
        .all()
    )
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['actiu', 'garment_group', 'size_system', 'customer']
    search_fields = ['nom']
    ordering = ['nom']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [_ConfigureWrite()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system_default:
            return Response(
                {'error': 'No es pot esborrar un RuleSet de sistema.'},
                status=status.HTTP_403_FORBIDDEN
            )
        # SizingProfile.grading_rule_set és PROTECT → un delete directe peta amb 500. A més,
        # Model.grading_rule_set és SET_NULL → esborrar deixa els models dependents sense grading
        # derivat (silenciosament). Per consentiment informat: si hi ha perfils O models, retorna
        # 409 amb els recomptes i un missatge clar. Amb ?force=1: cascada controlada (esborra
        # perfils + ruleset; les regles cauen per CASCADE; els models es buiden per SET_NULL — NO
        # s'esborren). is_system_default segueix 403.
        from fhort.models_app.models import Model
        n_prof = SizingProfile.objects.filter(grading_rule_set=instance).count()
        n_models = Model.objects.filter(grading_rule_set=instance).count()
        force = str(request.query_params.get('force', '')).lower() in ('1', 'true', 'yes')
        if (n_prof or n_models) and not force:
            parts = []
            if n_prof:
                parts.append(f'{n_prof} perfil(s) de talles')
            if n_models:
                parts.append(f'{n_models} model(s)')
            efectes = []
            if n_prof:
                efectes.append("n'eliminarà els perfils i les regles")
            if n_models:
                efectes.append('deixarà els models sense grading derivat')
            return Response(
                {'error': 'protected', 'profiles': n_prof, 'models_afectats': n_models,
                 'message': (f"Aquest RuleSet té {' i '.join(parts)} que en depenen. "
                             f"Esborrar-lo {' i '.join(efectes)}. Continuar?")},
                status=status.HTTP_409_CONFLICT,
            )
        with transaction.atomic():
            if n_prof:
                SizingProfile.objects.filter(grading_rule_set=instance).delete()
            instance.delete()  # CASCADE: GradingRule; Model → SET_NULL
        return Response(status=status.HTTP_204_NO_CONTENT)


class GradingRuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GradingRuleSerializer
    queryset = GradingRule.objects.select_related(
        'pom__pom_global', 'talla_base', 'rule_set'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['rule_set', 'actiu', 'logica']
    search_fields = ['pom__codi_client', 'pom__nom_client']
    ordering = ['rule_set', 'pom__codi_client']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [_ConfigureWrite()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        """We do not delete physically — we mark as inactive."""
        instance = self.get_object()
        instance.actiu = False
        instance.save(update_fields=['actiu'])
        return Response(
            {'status': 'inactiu', 'id': instance.id},
            status=status.HTTP_200_OK
        )

    def perform_update(self, serializer):
        # Protect rules of system RuleSets: clone before modifying.
        instance = serializer.instance
        if instance.rule_set.is_system_default:
            raise PermissionDenied(
                'Les regles de RuleSets de sistema no es poden modificar. '
                'Clona el RuleSet primer.'
            )
        serializer.save()


class GarmentPOMMapViewSet(viewsets.ModelViewSet):
    serializer_class = GarmentPOMMapSerializer
    queryset = (
        GarmentPOMMap.objects
        .select_related('garment_type_item', 'garment_type_item__garment_type',
                        'pom', 'pom__pom_global', 'pom__pom_global__body_measure_iso',
                        'pom__categoria')
        .all()
    )

    def get_permissions(self):
        # Lectura: autenticat. Escriptura: configure (alineat amb GarmentType/GarmentTypeItem).
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        perm = HasCapability(); self.required_capability = CONFIGURE
        return [perm]

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    # Migration família → item COMPLETADA (PAS 6): la pertinença viu només a garment_type_item.
    # El filtre legacy `?garment_type=` s'ha retirat amb el drop del camp (migració 0016).
    filterset_fields = {
        'garment_type_item': ['exact'],
        'pom': ['exact'],
        'is_key': ['exact'],
        'obligatori': ['exact'],
        'pendent_revisio': ['exact'],
    }
    ordering_fields = ['ordre', 'id', 'garment_type_item']
    ordering = ['garment_type_item', 'ordre']


class ItemBaseMeasurementViewSet(viewsets.ModelViewSet):
    """Valors base de plantilla per Item (Sprint Mesures Base per Item, P3). Motlle EXACTE de
    GarmentPOMMapViewSet: lectura autenticada, escriptura gated CONFIGURE (mateixa capability que
    garment-pom-maps, pom/views.py:get_permissions). Lectura per item via ?garment_type_item=<id>.
    UPSERT keyed (item, pom) via l'acció dedicada `upsert` (update_or_create, respecta la
    unique_together) — la columna del POMBrowser ASSIGN (P4) no ha de conèixer l'id de fila."""
    serializer_class = ItemBaseMeasurementSerializer
    queryset = (
        ItemBaseMeasurement.objects
        .select_related('garment_type_item', 'pom', 'pom__pom_global')
        .all()
    )

    def get_permissions(self):
        # Idèntic a GarmentPOMMapViewSet: lectura autenticada, escriptura CONFIGURE.
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        perm = HasCapability(); self.required_capability = CONFIGURE
        return [perm]

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        'garment_type_item': ['exact'],
        'pom': ['exact'],
    }
    ordering_fields = ['id', 'garment_type_item', 'pom']
    ordering = ['garment_type_item', 'pom']

    @action(detail=False, methods=['post'], url_path='upsert')
    def upsert(self, request):
        """POST /api/v1/item-base-measurements/upsert/  Body: {garment_type_item, pom,
        base_value_cm?, tol_minus?, tol_plus?, nom_fitxa?}. update_or_create per (item, pom). Gated
        CONFIGURE (l'acció no és list/retrieve → get_permissions retorna CONFIGURE)."""
        from fhort.tasks.models import GarmentTypeItem
        item_id = request.data.get('garment_type_item')
        pom_id = request.data.get('pom')
        if not item_id or not pom_id:
            return Response({'error': 'garment_type_item i pom requerits.'},
                            status=status.HTTP_400_BAD_REQUEST)
        # garment_type_item té db_constraint=False (cross-schema) → validem l'existència nosaltres
        # (la BD no ho faria); pom té constraint real però validem igual per retornar 400 net.
        if not GarmentTypeItem.objects.filter(pk=item_id).exists():
            return Response({'error': 'garment_type_item inexistent.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not POMMaster.objects.filter(pk=pom_id).exists():
            return Response({'error': 'pom inexistent.'},
                            status=status.HTTP_400_BAD_REQUEST)
        defaults = {f: request.data.get(f)
                    for f in ('base_value_cm', 'tol_minus', 'tol_plus', 'nom_fitxa')
                    if f in request.data}
        obj, created = ItemBaseMeasurement.objects.update_or_create(
            garment_type_item_id=item_id, pom_id=pom_id, defaults=defaults)
        return Response(self.get_serializer(obj).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CustomerPOMAliasViewSet(viewsets.ModelViewSet):
    """CRUD de la biblioteca de nomenclatura del client (CustomerPOMAlias).
    Lectura oberta (IsAuthenticated); escriptura gated CONFIGURE (mateix patró que grading).
    Filtra per ?customer=<id> per servir la fitxa del client."""
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerPOMAliasSerializer
    queryset = (
        CustomerPOMAlias.objects
        .select_related('customer', 'pom', 'pom__pom_global')
        .all()
    )
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['customer', 'pom', 'pendent_revisio', 'origen']
    # La cerca ha de trobar també les descripcions del diccionari (QA-S8 · D4b): sense els camps
    # nous, buscar "neckline" no retornava cap dels 90 àlies carregats pel wizard.
    search_fields = ['client_code', 'client_description', 'description_en', 'description_local']
    ordering = ['client_code']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [_ConfigureWrite()]
        return [IsAuthenticated()]
