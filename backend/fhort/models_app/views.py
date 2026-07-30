import datetime
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from django.db.models import Exists, OuterRef
from rest_framework import mixins, viewsets
from rest_framework.decorators import api_view, parser_classes, permission_classes, action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from fhort.accounts.capabilities import HasCapability, EXECUTE_TASKS, CONFIGURE
from fhort.pom.services import SealedGradingVersionError, _te_regles
from fhort.pom.grading_regime import (
    CODI_LINEAR_ZERO, MISSATGE_LINEAR_ZERO, es_linear_degenerada,
)
from .models import BaseMeasurement, ConsumptionRecord, GarmentSet, Model, ModelFitxer, Watchpoint
from .services_fitxers import DOWNLOAD_SALT, DOWNLOAD_TTL
from .serializers import (
    BaseMeasurementSerializer,
    ModelDetailSerializer,
    ModelFitxerSerializer,
    ModelListSerializer,
    WatchpointSerializer,
)


class ModelFilter(django_filters.FilterSet):
    """FONT ÚNICA DE FILTRES de model (C1). El consumeixen els TRES punts d'entrada que
    abans el reflectien per separat: el Model list (`ModelViewSet`), els comptadors per fase
    (`fase-counts`) i el board per-model (`by_model`, tasks/views_b.py, via subquery d'ids).
    Params:
      - ?fase_actual / ?garment_type / ?temporada / ?any / ?estat / ?prioritat   exactes
      - ?customer=<id>                  exacte (FK)
      - ?collection=<text>              icontains (CharField lliure)
      - ?data_objectiu_after=YYYY-MM-DD&data_objectiu_before=YYYY-MM-DD  rang inclusiu
      - ?responsable=<userprofile_id>   SEMPRE el DIRECTOR del model (Model.responsable, FK).
      - ?assignee=me | <userprofile_id> tècnic amb ≥1 ModelTask assignada (càrrega real).
        Desdoblament semàntic de C1: `assignee` és el param NOU que hereta el comportament
        que abans `responsable` tenia a by_model/fase-counts; `responsable` queda net com a
        director. Valors invàlids d'`assignee` s'ignoren (coherent amb la resta de filtres).
    """
    collection = django_filters.CharFilter(field_name='collection', lookup_expr='icontains')
    data_objectiu = django_filters.DateFromToRangeFilter(field_name='data_objectiu')
    assignee = django_filters.CharFilter(method='filter_assignee')

    # Capes del ruleset (S16: target = M2M `targets` autoritatiu; construction/fit_type = FK). Filtrem
    # per CODI travessant la relació — NO dupliquem l'eix al Model (els CharField target/fit_type/
    # construction del Model són legacy). Ref DIAGNOSI_UNIFICACIO_SELECTORS_CASCADE.
    # Peça (multi-node del CascadeSelector) → OR dins de cada nivell. Conviuen amb els filtres exactes
    # (garment_type/garment_type_item de Meta.fields, que usen fase-counts/garment-counts). GROUP node
    # filtra pel grup del garment_type del model (garment_type__grup, camí autoritatiu de l'arbre únic).
    garment_type__in = django_filters.BaseInFilter(field_name='garment_type', lookup_expr='in')
    garment_type_item__in = django_filters.BaseInFilter(field_name='garment_type_item', lookup_expr='in')
    garment_group_codi__in = django_filters.BaseInFilter(field_name='garment_type__grup', lookup_expr='in')

    target = django_filters.CharFilter(field_name='grading_rule_set__targets__codi', lookup_expr='exact')
    fit = django_filters.CharFilter(field_name='grading_rule_set__fit_type__codi', lookup_expr='exact')
    construction = django_filters.CharFilter(field_name='grading_rule_set__construction__codi', lookup_expr='exact')

    # Eixos operatius per Exists (sense N+1, sense duplicar files): watchpoints oberts, dins del pla
    # (scheduler S15 = planned_start no nul), i l'estat d'una tasca d'un tipus (task_type per CODE, llei G9).
    watchpoints_open = django_filters.BooleanFilter(method='filter_watchpoints_open')
    in_plan = django_filters.BooleanFilter(method='filter_in_plan')
    task_type = django_filters.CharFilter(method='filter_task_state')
    task_status = django_filters.CharFilter(method='_noop_task_status')

    class Meta:
        model = Model
        fields = ['fase_actual', 'garment_type', 'garment_type_item', 'garment_group',
                  'size_system', 'grading_rule_set',
                  'responsable', 'temporada', 'any',
                  'estat', 'prioritat', 'customer', 'collection', 'data_objectiu']

    def filter_assignee(self, queryset, name, value):
        """`me` → perfil de la request; `<id>` → aquell perfil. Filtra els models on el perfil
        és ASSIGNEE d'≥1 ModelTask (subquery per model_id, sense tocar la resta de filtres).
        Valor no resoluble → queryset intacte (s'ignora, com els altres filtres invàlids)."""
        from fhort.tasks.models import ModelTask
        if value == 'me':
            profile = getattr(getattr(self.request, 'user', None), 'profile', None)
            if profile is None:
                return queryset.none()
            model_ids = ModelTask.objects.filter(assignee=profile).values('model_id')
        elif str(value).isdigit():
            model_ids = ModelTask.objects.filter(assignee_id=int(value)).values('model_id')
        else:
            return queryset
        return queryset.filter(id__in=model_ids)

    def filter_watchpoints_open(self, queryset, name, value):
        """?watchpoints_open=true → models amb ≥1 Watchpoint estat='open'; =false → cap.
        Exists correlat (sense N+1, sense duplicar files)."""
        if value is None:
            return queryset
        has_open = Exists(Watchpoint.objects.filter(model=OuterRef('pk'), estat='open'))
        return queryset.filter(has_open) if value else queryset.exclude(has_open)

    def filter_in_plan(self, queryset, name, value):
        """?in_plan=true → models amb ≥1 ModelTask planificada (scheduler S15: planned_start no nul)."""
        if value is None:
            return queryset
        from fhort.tasks.models import ModelTask
        planned = Exists(ModelTask.objects.filter(model=OuterRef('pk'), planned_start__isnull=False))
        return queryset.filter(planned) if value else queryset.exclude(planned)

    def filter_task_state(self, queryset, name, value):
        """Parell (task_type, task_status): ?task_type=<code>[&task_status=<status>] → models amb ≥1
        ModelTask d'aquell tipus (per CODE slug, llei G9) i, si es dona, en aquell status. task_type és
        l'àncora; task_status refina (es llegeix del querystring, no filtra sol → veure _noop_task_status)."""
        if not value:
            return queryset
        from fhort.tasks.models import ModelTask
        crit = {'task_type__code': value}
        status = self.data.get('task_status')
        if status:
            crit['status'] = status
        return queryset.filter(Exists(ModelTask.objects.filter(model=OuterRef('pk'), **crit)))

    def _noop_task_status(self, queryset, name, value):
        """task_status es consumeix DINS filter_task_state (parell lligat); com a filtre propi és no-op
        perquè el param sigui vàlid al contracte de conjunt (C2) sense doblar el filtratge."""
        return queryset


class ModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ModelFilter
    search_fields = ['codi_intern', 'codi_client', 'nom_prenda']
    ordering_fields = ['prioritat', 'data_objectiu', 'data_entrada']
    ordering = ['-prioritat']
    queryset = Model.objects.all()

    def get_queryset(self):
        # django-tenants already restricts queries to the current tenant schema
        # via the connection. The 'public' schema has no model tables, but we
        # return an empty queryset to avoid errors in misrouted views.
        if getattr(connection, 'schema_name', None) == 'public':
            return Model.objects.none()
        qs = (
            Model.objects
            # `garment_type_item` i `customer`: el serializer els llegeix per fila
            # (serializers.py:90,92) i sense select_related eren 2 queries per model
            # — 407 amb page_size=200 (§B3.1).
            .select_related('garment_type', 'garment_group',
                            'responsable', 'responsable__user',
                            'size_system', 'grading_rule_set',
                            'garment_type_item', 'customer',
                            # SET-1: el serializer hi niua el conjunt (badge «SET n/N»).
                            'garment_set')
            # …i les germanes, per no fer una query per fila de conjunt.
            .prefetch_related('garment_set__peces')
            .all()
        )
        if self.action != 'list':
            return qs
        # Pas 5C — enriquiment de la LLISTA: 3 dates de cicle (Subquery correlat, sense N+1) +
        # prefetch dels assignees per al "principal + N" (tècnics).
        from django.db.models import OuterRef, Subquery, Prefetch, Exists
        from django.utils import timezone
        from fhort.tasks.models import Production, ModelTask
        from fhort.fitting.models import FittingSession
        from fhort.commerce.models import WorkOrder
        today = timezone.localdate()
        return qs.annotate(
            entrada_prod=Subquery(Production.objects
                .filter(model=OuterRef('pk'), phase=OuterRef('fase_actual'))
                .order_by('-requested_at').values('requested_at')[:1]),
            arribada_proto=Subquery(Production.objects
                .filter(model=OuterRef('pk'), phase='Proto', delivered_at__isnull=False)
                .order_by('-delivered_at').values('delivered_at')[:1]),
            fitting_prev=Subquery(FittingSession.objects
                .filter(model=OuterRef('pk'), data__gte=today)
                .order_by('data').values('data')[:1]),
            # v2 albarà — traçabilitat: el model té encàrrec real (WO ORDER) o va directe (col·lector).
            has_order=Exists(WorkOrder.objects.filter(model=OuterRef('pk'), kind='ORDER')),
        ).prefetch_related(Prefetch(
            'model_tasks',
            queryset=ModelTask.objects.exclude(assignee__isnull=True).select_related('assignee'),
        ))

    def get_permissions(self):
        # `assignar-recurs` no és edició de model: és un acte de govern del Brand sobre qui
        # pot treballar-lo. Va gatejat CONFIGURE, la mateixa capacitat que RecursViewSet i que
        # els mestres del tenant. La resta del ViewSet conserva el seu permís de sempre.
        if self.action == 'assignar_recurs':
            perm = HasCapability()
            self.required_capability = CONFIGURE
            return [IsAuthenticated(), perm]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'list':
            return ModelListSerializer
        return ModelDetailSerializer

    @action(detail=False, methods=['get'], url_path='fase-counts')
    def fase_counts(self, request):
        """GET /api/v1/models/fase-counts/ — comptadors de models per fase.

        Respecta EXACTAMENT els mateixos filtres que el board (filter_queryset → mateix
        FilterSet + search). Es calcula a la BD (values+annotate), sense carregar files,
        per escalar a 600+ models. Retorna {counts:{<fase>:n}, total}.

        ABAST "els meus" (board tècnic): ?assignee=me | <profile_id> filtra els models on
        l'usuari (o el perfil) és ASSIGNEE d'≥1 ModelTask — MATEIXA semàntica que by-model
        (C1: font única de filtres via ModelFilter). `responsable` és el DIRECTOR del model.

        L'acció no és 'list' → get_queryset() torna el queryset pla (sense les anotacions
        de cicle de la llista). order_by() buit abans de values() perquè un OrderingFilter
        actiu no trenqui el GROUP BY.
        """
        from django.db.models import Count
        # C1 — el filtrat (inclosos responsable=director i assignee=tècnic) el resol el
        # ModelFilter canònic via filter_queryset; aquí només s'agrupa.
        qs = self.filter_queryset(self.get_queryset()).order_by()
        rows = qs.values('fase_actual').annotate(n=Count('id'))
        counts = {r['fase_actual']: r['n'] for r in rows}
        return Response({'counts': counts, 'total': sum(counts.values())})

    @action(detail=False, methods=['get'], url_path='garment-counts')
    def garment_counts(self, request):
        """GET /api/v1/models/garment-counts/ — comptadors de models per garment_type i per
        garment_type_item del conjunt FILTRAT.

        Respecta EXACTAMENT els filtres actius (mateix ModelFilter C1 via filter_queryset),
        igual que fase-counts. Alimenta els comptadors per node del CascadeSelector en mode
        filtre (el consumidor demana aquest endpoint i injecta els counts; el component NO fa
        fetch propi, i el wizard/grading no paguen mai aquestes queries).

        DOS GROUP BY independents (un per eix): el GROUP BY del PARELL (garment_type,
        garment_type_item) NO equival als dos subtotals per nivell (veure
        docs/diagnosis/DIAGNOSI_UNIFICACIO_SELECTORS_CASCADE.md · P5). Cada eix agrupa sobre el
        mateix queryset ja filtrat i amb order_by() buit (com fase-counts) perquè un
        OrderingFilter actiu no injecti columnes al GROUP BY. Els nodes NULL (models sense
        garment_type / garment_type_item) s'exclouen dels mapes; `total` és el recompte honest
        del conjunt filtrat sencer (inclou els models sense node). Sense N+1: comptat a la BD.

        Retorna {by_type:{<id>:n}, by_item:{<id>:n}, total:n}.
        """
        from django.db.models import Count
        qs = self.filter_queryset(self.get_queryset()).order_by()
        by_type = {r['garment_type']: r['n']
                   for r in qs.values('garment_type').annotate(n=Count('id'))
                   if r['garment_type'] is not None}
        by_item = {r['garment_type_item']: r['n']
                   for r in qs.values('garment_type_item').annotate(n=Count('id'))
                   if r['garment_type_item'] is not None}
        return Response({'by_type': by_type, 'by_item': by_item, 'total': qs.count()})

    @action(detail=False, methods=['post'], url_path='assignar-recurs')
    def assignar_recurs(self, request):
        """POST /api/v1/models/assignar-recurs/ — la palanca de sobirania del Brand.

        Body: {model_ids:[...], studio_codi:'FTT'}  ·  studio_codi:'' = RETIRAR l'assignació.
        Resposta: {assignats, ja_hi_eren, no_trobats, studio_codi}.

        LA PORTA LEGÍTIMA. `Model.studio_assignat` és el camp que decideix què travessa el
        pont, i fins ara al backend només l'escrivia un management command. Aquest endpoint és
        el seu equivalent per a la persona que decideix, i afegeix el que el CRUD genèric no
        fa: comprovar que el pont cap a aquest Studio existeix i és ACTIU abans d'escriure res.

        DUES CLAUS INDEPENDENTS (llei de la federació): el TenantLink autoritza el PONT,
        `studio_assignat` autoritza CADA MODEL. Per això assignar amb el vincle ATURAT és 409
        i no un avís: assignar seria escriure una autorització que el pont tancat desmenteix.

        RETIRAR NO DEMANA PONT. `studio_codi=''` buida el camp sense validar cap vincle: treure
        una autorització sempre ha de ser possible, també — i sobretot — quan el pont ja no hi és.

        EL BRAND ÉS EL DEL REQUEST. El vincle es busca amb `request.tenant.codi_tenant`; el
        payload no diu mai en nom de qui s'assigna (mateixa llei que RecursViewSet).

        NO ES COMPROVA SI EL MODEL JA S'HA TRASPASSAT: no es pot. La instància EXTERN viu al
        schema del Studio i el Brand no hi ha de mirar mai. No cal: `instantiate_external_models`
        és idempotent per `codi_intern` (salta el que ja existeix), així que reassignar un model
        ja traspassat no en duplica cap. L'escriptura s'accepta sempre.
        """
        from fhort.tenants.models import TenantLink

        model_ids = request.data.get('model_ids')
        if not isinstance(model_ids, list) or not model_ids:
            return Response({'error': 'model_ids ha de ser una llista no buida.',
                             'code': 'model_ids_required'}, status=400)

        studio_codi = (request.data.get('studio_codi') or '').strip().upper()
        brand_codi = getattr(getattr(request, 'tenant', None), 'codi_tenant', None)

        if studio_codi:
            if brand_codi is None:
                return Response({'error': "Aquest schema no té tenant de producte.",
                                 'code': 'no_tenant'}, status=400)
            link = TenantLink.objects.filter(
                brand_codi_tenant=brand_codi, studio_codi_tenant=studio_codi).first()
            if link is None:
                return Response({'error': f"No hi ha cap vincle amb '{studio_codi}'.",
                                 'code': 'link_missing'}, status=400)
            if not link.es_viu():
                return Response({'error': f"El vincle amb '{studio_codi}' no és ACTIU (estat={link.estat}).",
                                 'code': 'link_not_active'}, status=409)

        qs = Model.objects.filter(id__in=model_ids)
        trobats = set(qs.values_list('id', flat=True))
        no_trobats = [i for i in model_ids if i not in trobats]
        # Compte honest: només és "assignat" el que CANVIA. Repetir l'acció no infla el número.
        ja_hi_eren = qs.filter(studio_assignat=studio_codi).count()
        assignats = qs.exclude(studio_assignat=studio_codi).update(studio_assignat=studio_codi)

        return Response({'assignats': assignats, 'ja_hi_eren': ja_hi_eren,
                         'no_trobats': no_trobats, 'studio_codi': studio_codi})


class ModelFitxerFilter(django_filters.FilterSet):
    """Eix únic `tipus` (S03a · P1). `?tipus__in=PATRO,ESCALAT` per als panells que
    agrupen més d'un rol. `categoria` ja no és filtrable: és un eix deprecat i buit."""
    tipus__in = django_filters.BaseInFilter(field_name='tipus', lookup_expr='in')

    class Meta:
        model = ModelFitxer
        fields = ['model', 'tipus', 'enviat_ia', 'is_current', 'mimetype']


class ModelFitxerViewSet(mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    """Lectura (list/retrieve/versions) + esborrat. NO exposa create/update: l'ÚNICA via
    d'escriptura és services_fitxers.save_model_file, que manté la invariant is_current
    de la cadena de versions. El ViewSet genèric la saltava (S03a · P0.1)."""
    permission_classes = [IsAuthenticated]
    serializer_class = ModelFitxerSerializer
    # S03c · C2.4 — `derivat_de_label` resol el codi de l'origen (model o item): sense els dos
    # select_related, cada fila derivada faria 2 queries extra.
    queryset = ModelFitxer.objects.select_related(
        'model', 'pujat_per',
        'derivat_de_model__model', 'derivat_de_item__garment_type_item').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ModelFitxerFilter
    ordering_fields = ['data_pujada']
    ordering = ['-data_pujada']

    def perform_destroy(self, instance):
        """Esborra els bytes abans de la fila: `instance.delete()` sol deixa orfes al disc."""
        from .services_fitxers import delete_fitxer_bytes
        delete_fitxer_bytes(instance)
        instance.delete()

    @action(detail=True, methods=['post'], url_path='usar-al-model')
    def usar_al_model(self, request, pk=None):
        """POST /api/v1/model-fitxers/<id>/usar-al-model/  Body: {model_id}   [S03c · C3.2]

        Cicle model→model: **importació, no edició in-place**. Crea un ModelFitxer NOU al model
        destí amb `derivat_de_model` apuntant a l'origen. L'origen NO es toca mai.

        Germà d'`item_fitxer_views.usar_al_model` (catàleg→model). Tots dos passen pel MATEIX
        camí de descongelat (`ftt_svc.font_per_al_model`): un `.ftt` mai es copia tal qual,
        vingui d'on vingui, perquè porta les dades del host on es va crear (text congelat,
        logo del client, taules snapshot amb les mesures, `graded_table` amb binding viu). La
        resta de tipus (PDF, DXF, SVG, imatges) són còpia directa de bytes.

        Gate: `IsAuthenticated` (permission_classes del ViewSet), el MATEIX que `upload_file_view`:
        l'escriptura va al model destí, i qui pot pujar-hi un fitxer pot importar-n'hi un.
        """
        from django.shortcuts import get_object_or_404

        from . import services_ftt_document as ftt_svc
        from .services_fitxers import marcar_procedencia, save_model_file

        origen = self.get_object()
        if not origen.fitxer:
            return Response({'error': "El fitxer d'origen no té bytes."}, status=400)

        model_id = request.data.get('model_id')
        if not model_id:
            return Response({'error': 'model_id és obligatori.'}, status=400)
        desti = get_object_or_404(Model, pk=model_id)

        if desti.pk == origen.model_id:
            return Response(
                {'error': 'El model destí és el mateix que el del fitxer origen.'}, status=400)

        origen.fitxer.open('rb')
        try:
            font, report = ftt_svc.font_per_al_model(origen, desti)
            nou = save_model_file(desti, font, tipus=origen.tipus,
                                  origen='upload', nom=origen.nom_fitxer)
        except ValueError as e:
            # unpack() llança ValueError amb missatge clar si el .ftt està corromput.
            return Response({'error': f'.ftt origen il·legible: {e}'}, status=400)
        finally:
            origen.fitxer.close()

        marcar_procedencia(nou, request.user, derivat_de_model=origen)

        dades = ModelFitxerSerializer(nou, context={'request': request}).data
        avis = ftt_svc.avis_de_copia(report)
        if avis:
            dades['avis'] = avis
        return Response(dades, status=201)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Cadena de versions completa (read-only) del fitxer, ordenada per versio."""
        from .services_fitxers import get_version_chain
        chain = get_version_chain(self.get_object())
        serializer = self.get_serializer(chain, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """GET /api/v1/model-fitxers/<id>/download/ — descàrrega GATED per Authorization.

        Els bytes de /media/ els serveix nginx per `alias`, sense que Django hi intervingui:
        no hi ha cap check d'autenticació ni de tenant. Aquest endpoint és la porta que sí
        el fa. El queryset ja està acotat al schema del tenant per django-tenants.

        Per a consumidors que NO poden posar capçaleres (<a href>, <img src>), vegeu
        `download_signed` (D13).
        """
        from .services_fitxers import serve_fitxer
        return serve_fitxer(self.get_object())

    @action(detail=True, methods=['get'], url_path='download-signed',
            permission_classes=[AllowAny], authentication_classes=[])
    def download_signed(self, request, pk=None):
        """GET /api/v1/model-fitxers/<id>/download-signed/?token=… — descàrrega SIGNADA (D13).

        `<a href>` i `<img src>` no poden portar capçalera Authorization (el JWT viu a
        localStorage). La porta és un token de curta vida (TTL_SIGNATURA) emès pel serializer
        NOMÉS a qui ja s'ha autenticat per a llegir la fila. AllowAny és deliberat: el permís
        el porta el token, no la sessió.

        El tenant l'aïlla el Host (django-tenants), com a la resta de l'API → el token no
        n'ha de portar cap. El payload és l'id: si el token d'un fitxer s'enganxa a la URL
        d'un altre, no valida.

        `?inline=1` → Content-Disposition: inline, per als previsualitzadors (<iframe> de PDF).
        """
        from django.core import signing
        from django.http import HttpResponseForbidden

        from .services_fitxers import serve_fitxer

        token = request.query_params.get('token') or ''
        try:
            signed_id = signing.loads(token, salt=DOWNLOAD_SALT, max_age=DOWNLOAD_TTL)
        except signing.SignatureExpired:
            return HttpResponseForbidden('Enllaç de descàrrega caducat.')
        except signing.BadSignature:
            return HttpResponseForbidden('Enllaç de descàrrega no vàlid.')

        if str(signed_id) != str(pk):
            return HttpResponseForbidden('El token no correspon a aquest fitxer.')

        inline = request.query_params.get('inline') == '1'
        return serve_fitxer(self.get_object(), as_attachment=not inline)


# D-12 — Watchpoints: advertències de text lliure que viatgen amb el model a través dels gates.
class WatchpointViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WatchpointSerializer
    queryset = Watchpoint.objects.select_related('created_by', 'resolved_by', 'task__task_type').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'estat', 'task']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=getattr(self.request.user, 'profile', None))

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        from django.utils import timezone
        wp = self.get_object()
        wp.estat = 'resolved'
        wp.resolved_by = getattr(request.user, 'profile', None)
        wp.resolved_at = timezone.now()
        wp.resolution_note = (request.data.get('resolution_note') or '').strip()
        wp.save(update_fields=['estat', 'resolved_by', 'resolved_at', 'resolution_note'])
        return Response(self.get_serializer(wp).data)

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        wp = self.get_object()
        wp.estat = 'open'
        wp.resolved_by = None
        wp.resolved_at = None
        wp.resolution_note = ''
        wp.save(update_fields=['estat', 'resolved_by', 'resolved_at', 'resolution_note'])
        return Response(self.get_serializer(wp).data)


# Sprint S14B — BaseMeasurement CRUD
class BaseMeasurementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BaseMeasurementSerializer
    queryset = (
        BaseMeasurement.objects
        .select_related('pom', 'pom__pom_global')
        .all()
    )
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'pom', 'is_active', 'origen']
    ordering_fields = ['updated_at', 'id']
    ordering = ['model', 'id']

    def get_queryset(self):
        # The 'public' schema has no tenant data — return an empty queryset.
        if getattr(connection, 'schema_name', None) == 'public':
            return BaseMeasurement.objects.none()
        return super().get_queryset()

    # Sprint 3 / F1: tag the request user so the change-log signal can fill created_by.
    def perform_create(self, serializer):
        # created_by is set on the instance before the signal fires.
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        # _changed_by takes priority over the original created_by for edits.
        serializer.instance._changed_by = self.request.user
        serializer.save()



def _resolve_customer_code(customer_id):
    """Codi (3 chars) per a un customer_id donat, amb fallback al self-customer del tenant.
    Font única del prefix per als endpoints de codi-gen (preview i creació)."""
    from fhort.tasks.models import Customer
    from fhort.models_app.services import get_self_customer
    cust = None
    if customer_id:
        cust = Customer.objects.filter(pk=customer_id).first()
    if cust is None:
        cust = get_self_customer()
    return (cust.codi if cust else 'IMP'), cust


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def next_model_ref(request):
    year = request.GET.get('year', str(datetime.date.today().year))
    season = request.GET.get('season', 'SS')
    # El prefix surt del customer (la preview ha de portar ?customer_id); fallback self-customer.
    prefix, _ = _resolve_customer_code(request.GET.get('customer_id'))
    year_short = str(year)[-2:]
    base = f"{prefix}-{season}{year_short}-"
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT codi_intern FROM models_app_model "
            "WHERE codi_intern LIKE %s "
            "ORDER BY codi_intern DESC LIMIT 1",
            [base + '%']
        )
        row = cursor.fetchone()
    if row:
        last_num = int(row[0].split('-')[-1])
        next_num = last_num + 1
    else:
        next_num = 1
    codi = f"{base}{str(next_num).zfill(4)}"
    return Response({'codi_intern': codi, 'next_number': next_num})


def _validar_ruleset_assignable(rs, *, size_system_id=None, customer_id=None, confirmat=False):
    """D1 — porta d'entrada de l'assignació d'un GradingRuleSet a un model.

    Assignar un ruleset dispara un wipe-and-recreate de les regles residents
    (`materialize_model_grading_rules`): si el ruleset no serveix, el model es queda
    sense regles i el motor ja no ho pot arreglar. Per això es valida ABANS d'assignar,
    no al consum. És el forat pel qual el model 163 va quedar buit
    (DIAGNOSI_REFACTOR_GRADING_2026-07-21, R5/R6).

    Retorna `(payload, status)` si cal aturar, o `None` si es pot assignar.
      - 0 regles actives          → BLOQUEIG DUR (400). Mai assignable.
      - size_system divergent     → BLOQUEIG DUR (400). Graduar amb un run que no és el
                                    del model no vol dir res.
      - customer divergent        → AVÍS CONSCIENT (409) fins que arribi `confirmat`.
                                    MAI bloqueig: aplicar la forma d'un altre client és
                                    un flux de taller legítim.
    """
    from fhort.pom.models import GradingRule

    n_regles = GradingRule.objects.filter(rule_set_id=rs.id, actiu=True).count()
    if n_regles == 0:
        return ({
            'error': 'ruleset_buit',
            'codi': 'GRADING_RULESET_EMPTY',
            'grading_rule_set_id': rs.id,
            'grading_rule_set_nom': rs.nom,
            'message': (f"El grading «{rs.nom}» no té cap regla: assignar-lo deixaria el "
                        f"model sense graduació. Tria'n un altre o omple'l primer."),
        }, 400)

    if rs.size_system_id and size_system_id and rs.size_system_id != size_system_id:
        return ({
            'error': 'size_system_divergent',
            'codi': 'GRADING_SIZE_SYSTEM_MISMATCH',
            'grading_rule_set_id': rs.id,
            'grading_rule_set_nom': rs.nom,
            'ruleset_size_system_id': rs.size_system_id,
            'model_size_system_id': size_system_id,
            'message': (f"El grading «{rs.nom}» és d'un altre sistema de talles que el del "
                        f"model. Les regles no es poden aplicar a aquest run."),
        }, 400)

    if rs.customer_id and customer_id and rs.customer_id != customer_id and not confirmat:
        return ({
            'conflict': True,
            'tipus': 'ruleset_altre_client',
            'codi': 'GRADING_CUSTOMER_MISMATCH',
            'grading_rule_set_id': rs.id,
            'grading_rule_set_nom': rs.nom,
            'ruleset_customer': str(getattr(rs.customer, 'nom', '') or rs.customer_id),
            'message': (f"El grading «{rs.nom}» és d'un altre client. Es pot fer servir "
                        f"igualment, però és una decisió conscient: confirma-ho per continuar."),
        }, 409)

    return None


def _resolve_garment_def(d, model=None):
    """Resol la definició de garment + talles d'un payload d'esquelet (Pas 5A).
    Cada camp és OPCIONAL (es posa només si ve al payload). Retorna (fields, error_payload).
    garment_type_item_id és la BAULA del motor de temps (matriu item×task_type).

    PORTA ÚNICA DEL RUN (llei S24b): `size_run` no es desa mai cru. Passa per
    `run_del_model`, que l'ordena per `SizeDefinition.ordre` del SizeSystem. Aquesta funció
    la comparteixen `create_model_wizard` i `update_model_step2`, i per tant tancar-la aquí
    cobreix la creació I l'edició d'un sol cop — que és per on va entrar el run apendat del
    model 166.

    `model` és el model existent en el camí d'EDICIÓ: cal per resoldre el sistema contra el
    qual ordenar quan el PATCH porta `size_run` però no `size_system_id`.

    El retorn d'error és un DICT (payload de resposta), no un string: la llista d'etiquetes
    desconegudes ha de viatjar al client, no quedar aixafada dins d'un missatge.
    """
    from fhort.pom.models import GarmentType, GarmentGroup, SizeSystem, GradingRuleSet
    from fhort.pom.grading_utils import run_del_model
    from fhort.tasks.models import GarmentTypeItem
    fields = {}
    # Pont família↔item: si arriba l'item, la família (i el grup) es DERIVEN de l'item; el
    # garment_type_id del payload s'IGNORA → garanteix garment_type == garment_type_item.garment_type.
    if d.get('garment_type_item_id'):
        try:
            item = (GarmentTypeItem.objects.select_related('garment_type')
                    .get(id=d['garment_type_item_id']))
        except GarmentTypeItem.DoesNotExist:
            return None, {'error': 'GarmentTypeItem no trobat'}
        fields['garment_type_item'] = item
        fields['garment_type'] = item.garment_type
        grp = GarmentGroup.objects.filter(codi=item.garment_type.grup).first()
        if grp is not None:
            fields['garment_group'] = grp
    elif d.get('garment_type_id'):
        # Legacy: sense item → es respecta el garment_type_id del payload (compatibilitat).
        try:
            fields['garment_type'] = GarmentType.objects.get(id=d['garment_type_id'])
        except GarmentType.DoesNotExist:
            return None, {'error': 'GarmentType no trobat'}
    if d.get('size_system_id'):
        try:
            fields['size_system'] = SizeSystem.objects.get(id=d['size_system_id'])
        except SizeSystem.DoesNotExist:
            return None, {'error': 'SizeSystem no trobat'}
    if d.get('grading_rule_set_id'):
        try:
            fields['grading_rule_set'] = GradingRuleSet.objects.get(id=d['grading_rule_set_id'])
        except GradingRuleSet.DoesNotExist:
            pass  # tolerant (com el flux original)
    if d.get('target'):
        fields['target'] = d['target']
    if d.get('construction'):
        fields['construction'] = d['construction']
    if d.get('size_run'):
        # PORTA ÚNICA (S24b). El sistema contra el qual s'ordena és el que assigna aquest
        # mateix payload; si no en porta, el que ja té el model (camí d'edició). Sense cap
        # dels dos, `run_del_model` degrada i conserva l'ordre d'entrada.
        _ss = fields.get('size_system') or (model.size_system if model is not None else None)
        _run, _desconegudes = run_del_model(
            str(d['size_run']).replace(';', '·').split('·'), _ss,
        )
        if _desconegudes:
            return None, {
                'error': (
                    "Aquestes talles no pertanyen al sistema de talles del model: "
                    + ', '.join(_desconegudes)
                ),
                'codi': 'talles_desconegudes',
                'etiquetes_desconegudes': _desconegudes,
            }
        fields['size_run_model'] = '·'.join(_run)
    if d.get('base_size'):
        fields['base_size_label'] = d['base_size']
    return fields, None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_model_wizard(request):
    """Pas 5A — creació UNIFICADA: l'esquelet COMPLET (identificació + garment def + talles)
    en un sol POST. Desa garment_type_item (baula del motor) i la traçabilitat created_by."""
    year = request.data.get('year')
    season = request.data.get('season')
    ref_client = request.data.get('ref_client', '')
    customer_id = request.data.get('customer_id')
    nom_prenda = request.data.get('nom_prenda', '')
    descripcio = request.data.get('descripcio', '')
    collection = request.data.get('collection', '')
    data_objectiu = request.data.get('data_objectiu') or None   # deadline (opcional)
    # Sprint A — multi-piece (immutable after creation)
    is_multipiece = bool(request.data.get('is_multipiece', False))
    num_pieces = request.data.get('num_pieces')

    # LLEI 5 CAPES (2026-07-16): la talla base és ESCALA PURA (capa 3) i s'ha de poder desar SENSE
    # graduació (capa 4). El pas «Talles» del wizard ja no arrossega ruleset; la graduació es tria
    # per separat després (RuleSetCard → update-step2, que re-materialitza). Es retira el guard
    # PG-3 Cas B que exigia ruleset a la creació (update_model_step2 ja no el tenia).

    garment_fields, gerr = _resolve_garment_def(request.data)
    if gerr:
        return Response(gerr, status=400)

    # D1 — mateixa porta que a update_model_step2: el wizard pot arrossegar graduació ja des de
    # la creació, i un ruleset buit o d'un altre run faria néixer el model sense regles útils.
    _rs = garment_fields.get('grading_rule_set')
    if _rs is not None:
        _ss = garment_fields.get('size_system')
        _err = _validar_ruleset_assignable(
            _rs,
            size_system_id=(_ss.id if _ss is not None else None),
            customer_id=request.data.get('customer_id') or None,
            confirmat=bool(request.data.get('confirmar_altre_client')),
        )
        if _err is not None:
            payload, status_code = _err
            return Response(payload, status=status_code)

    creator = getattr(request.user, 'profile', None)

    if not year or not season:
        return Response({'error': 'year i season són obligatoris'}, status=400)

    # B4b — garment_type_item obligatori al wizard: és la baula del motor de temps i de la
    # valoració de receptes (comercial). Guard de servei; la columna segueix nullable a BD
    # (additiu; 0 models amb GTI null al tenant → cap backfill). TODO: fer-la NOT NULL a BD
    # en una sessió futura si es vol la garantia dura.
    if not request.data.get('garment_type_item_id'):
        return Response({'error': 'garment_type_item és obligatori'}, status=400)

    # ── SET-1 · A4 — EL GTI MANA. Decisió 3 del sprint SET: és l'item qui declara PEÇA o
    #    CONJUNT, no el payload. `is_multipiece`/`num_pieces` (que cap superfície de frontend
    #    enviava) queden com a redundància: si contradiuen el GTI, 400 — mai s'endevina.
    item_triat = garment_fields.get('garment_type_item')
    parts_del_set = []
    if item_triat is not None and item_triat.is_set:
        parts_del_set = list(
            item_triat.parts.select_related(
                'part_item', 'part_item__garment_type',
                'part_item__grading_rule_set', 'part_item__base_size_definition',
            ).order_by('ordre', 'id'))
        if len(parts_del_set) < 2:
            return Response({
                'error': (f"L'item «{item_triat.code}» està declarat com a conjunt però la seva "
                          f'composició té {len(parts_del_set)} peça/es. Defineix-ne la '
                          'composició al catàleg abans de crear-hi models.'),
                'codi': 'set_sense_composicio',
            }, status=400)
        if 'is_multipiece' in request.data and not is_multipiece:
            return Response({
                'error': (f"L'item «{item_triat.code}» és un CONJUNT: no es pot crear com a peça "
                          'única. Retira `is_multipiece: false` del payload.'),
                'codi': 'contradiccio_gti_set',
            }, status=400)
        if num_pieces is not None and int(num_pieces) != len(parts_del_set):
            return Response({
                'error': (f'`num_pieces` ({num_pieces}) contradiu la composició de l\'item '
                          f'«{item_triat.code}» ({len(parts_del_set)} peces). El GTI mana.'),
                'codi': 'contradiccio_gti_num_pieces',
            }, status=400)
        is_multipiece = True
        num_pieces = len(parts_del_set)
    elif is_multipiece:
        # El camí llegat (N peces idèntiques d'un item que NO és conjunt) deixa d'existir: amb
        # la decisió 3, un conjunt és una declaració del catàleg. Es rebutja explícitament en
        # comptes de crear N models bessons que cap GTI no reconeixeria com a peces.
        return Response({
            'error': (f"L'item «{item_triat.code if item_triat else '—'}» no està declarat com a "
                      'conjunt al catàleg: no s\'hi poden crear peces. Marca\'l com a conjunt i '
                      'defineix-ne la composició.'),
            'codi': 'contradiccio_gti_no_set',
        }, status=400)

    # Prefix unificat: codi del customer (fallback self-customer). Escopa la seqüència via
    # el codi_intern (regex sota), de manera que el next_num ja és per-customer (Pas 4).
    prefix, customer = _resolve_customer_code(customer_id)
    year_short = str(year)[-2:]
    base = f"{prefix}-{season}{year_short}-"

    # next_num must look ONLY at base codes (FTT-SS26-NNNN), NOT at piece codes
    # (FTT-SS26-NNNN-NN). A plain LIKE 'base%' would capture piece codes and
    # split('-')[-1] would return the piece suffix, breaking the sequence.
    # The regex anchors a 4-digit sequential at the end → piece codes excluded.
    # We scan BOTH Model.codi_intern base codes AND GarmentSet.codi_base, because
    # a set's base number is consumed (its pieces are NNNN-01/-02) and must not be
    # reused by a later single model.
    base_pattern = f"^{prefix}-{season}{year_short}-[0-9]{{4}}$"
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT codi_intern FROM models_app_model WHERE codi_intern ~ %s",
            [base_pattern]
        )
        candidates = [r[0] for r in cursor.fetchall()]
        cursor.execute(
            "SELECT codi_base FROM models_app_garmentset WHERE codi_base ~ %s",
            [base_pattern]
        )
        candidates += [r[0] for r in cursor.fetchall()]
    nums = [int(c.split('-')[-1]) for c in candidates]
    next_num = (max(nums) + 1) if nums else 1
    codi_base = f"{base}{str(next_num).zfill(4)}"

    # Single piece (~90%): unchanged flow, no GarmentSet.
    if not is_multipiece:
        model = Model.objects.create(
            codi_intern=codi_base,
            codi_client=ref_client,
            customer=customer,
            codi_tenant=prefix,
            any=int(year),
            temporada=season,
            sequencial=next_num,
            nom_prenda=nom_prenda or None,
            descripcio=descripcio or None,
            collection=collection or '',
            created_by=creator,
            estat='Nou',
            data_objectiu=data_objectiu,
            **garment_fields,
        )
        # PG-2 Cas B: si s'ha triat ruleset, materialitza'n les regles al model (origen=CANONICAL).
        # El model ja està desat (create fora de transacció); l'atomic embolcalla NOMÉS la
        # materialització → si peta, no queda cap MGR parcial i el model gradua igualment pel
        # fallback PG-1 (ruleset extern). Degradació gràcil INTENCIONAL, no descuit.
        if model.grading_rule_set_id:
            # `transaction` ve del import de mòdul (:4). Un `from django.db import transaction`
            # AQUÍ el feia local a TOTA la funció i deixava la branca multi-peça amb un
            # UnboundLocalError al seu `with transaction.atomic()` — latent mentre cap
            # superfície no enviava `is_multipiece` (forat #4 del dimensionat).
            from fhort.models_app.services import (materialize_model_grading_rules,
                                               origen_mgr_des_de_ruleset)
            with transaction.atomic():
                materialize_model_grading_rules(
                    model, model.grading_rule_set.regles.all(),
                    origen=origen_mgr_des_de_ruleset(model.grading_rule_set))
        return Response({'id': model.id, 'codi_intern': model.codi_intern}, status=201)

    # SET-1 · A4 (forat #1 del dimensionat, :849) — les peces JA NO neixen idèntiques. Fins ara
    # el bucle clonava el MATEIX `**garment_fields` a totes: mateix item, mateix ruleset, mateix
    # nom. Amb la composició del GTI, cada peça resol el SEU món a través de la mateixa porta
    # única (`_resolve_garment_def`), i és això —i només això— el que fa que A6 (grading per
    # part) surti gratis: cada part-Model va al seu contenidor perquè porta el seu propi
    # `garment_type_item` i `grading_rule_set`.
    base_payload = {k: request.data.get(k) for k in (
        'garment_type_item_id', 'garment_type_id', 'size_system_id', 'grading_rule_set_id',
        'target', 'construction', 'size_run', 'base_size')}
    # Nom OPCIONAL per peça enviat pel wizard, per id de GarmentTypeItemPart. La composició del
    # catàleg mana sobre el defecte; això només permet batejar les peces d'AQUEST model (una
    # «Braga» pot ser «Culotte» en aquest bikini). Buit ⇒ el `nom_peca` de la composició.
    noms_peces = request.data.get('noms_peces') or {}
    if not isinstance(noms_peces, dict):
        return Response({'error': '`noms_peces` ha de ser un objecte {part_id: nom}.'}, status=400)

    camps_per_peca = []
    for part in parts_del_set:
        d_part = dict(base_payload)
        d_part['garment_type_item_id'] = part.part_item_id
        # El ruleset i la talla base de la PEÇA manen sobre els del payload; si la peça no en
        # declara, s'hereta el del conjunt (que és el que passava abans per a totes).
        if part.part_item.grading_rule_set_id:
            d_part['grading_rule_set_id'] = part.part_item.grading_rule_set_id
        if part.part_item.base_size_definition_id:
            d_part['base_size'] = part.part_item.base_size_definition.etiqueta
        fields_part, err_part = _resolve_garment_def(d_part)
        if err_part:
            err_part['peca'] = part.ordre
            return Response(err_part, status=400)
        nom_peca = (noms_peces.get(str(part.id)) or noms_peces.get(part.id) or '').strip()
        camps_per_peca.append((part, fields_part, nom_peca))

    # Multi-piece: one GarmentSet + N piece Models, codi_intern = codi_base-NN.
    with transaction.atomic():
        garment_set = GarmentSet.objects.create(
            codi_base=codi_base,
            nom_comercial=nom_prenda or '',
            num_pieces=num_pieces,
        )
        pieces = []
        for i, (part, fields_part, nom_peca) in enumerate(camps_per_peca, start=1):
            piece = Model.objects.create(
                codi_intern=f"{codi_base}-{str(i).zfill(2)}",
                codi_client=ref_client,
                customer=customer,
                codi_tenant=prefix,
                any=int(year),
                temporada=season,
                sequencial=next_num,
                # El nom de la PEÇA el dona la composició del catàleg («Top», «Bikini bottom»);
                # el nom comercial del conjunt viu a GarmentSet.nom_comercial.
                nom_prenda=(nom_peca or part.nom_peca or nom_prenda) or None,
                descripcio=descripcio or None,
                collection=collection or '',
                created_by=creator,
                estat='Nou',
                data_objectiu=data_objectiu,
                garment_set=garment_set,
                piece_number=i,
                **fields_part,
            )
            # PG-2 Cas B (multi-peça): cada peça hereta el ruleset via garment_fields →
            # materialitza les seves regles residents. Dins l'atomic del set: una fallada
            # avorta tot el conjunt (atòmic per disseny del multi-peça).
            if piece.grading_rule_set_id:
                from fhort.models_app.services import (materialize_model_grading_rules,
                                               origen_mgr_des_de_ruleset)
                materialize_model_grading_rules(
                    piece, piece.grading_rule_set.regles.all(),
                    origen=origen_mgr_des_de_ruleset(piece.grading_rule_set))
            pieces.append({
                'id': piece.id,
                'codi_intern': piece.codi_intern,
                'piece_number': piece.piece_number,
                'nom_prenda': piece.nom_prenda,
                'garment_type_item': piece.garment_type_item_id,
            })

    return Response({
        'garment_set_id': garment_set.id,
        'codi_base': garment_set.codi_base,
        'num_pieces': garment_set.num_pieces,
        'pieces': pieces,
    }, status=201)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_model_step2(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    d = request.data
    # Pas 5A — reutilitza el mateix resolutor que la creació (inclou garment_type_item_id).
    # S24b: se li passa el `model` perquè pugui ordenar el run contra el SizeSystem que ja té
    # quan el PATCH porta `size_run` sense `size_system_id`.
    garment_fields, gerr = _resolve_garment_def(d, model=model)
    if gerr:
        return Response(gerr, status=400)
    for k, v in garment_fields.items():
        setattr(model, k, v)
    if d.get('collection') is not None:
        model.collection = d['collection'] or ''

    # WIZARD pas 4 «Sense graduació» en EDICIÓ: buidatge EXPLÍCIT del ruleset. El resolutor només
    # ASSIGNA quan grading_rule_set_id és truthy (mai neteja); aquí, si la clau ve present i buida
    # (null), es desacobla la graduació i s'esborren les regles residents (queda estat "sense graduació",
    # vàlid). Idempotent i acotat a la intenció explícita del pas 4 — cap efecte si la clau no ve.
    if 'grading_rule_set_id' in d and not d.get('grading_rule_set_id') and model.grading_rule_set_id:
        model.grading_rule_set = None
        model.grading_rules.all().delete()

    # D1 — valida ABANS de desar i abans del wipe-and-recreate. Es valida contra els valors
    # POSTERIORS a l'assignació (el mateix PATCH pot canviar size_system), i només quan el
    # ruleset ve al payload: re-desar un model sense tocar la graduació no ha de rebotar.
    if d.get('grading_rule_set_id') and model.grading_rule_set_id:
        _err = _validar_ruleset_assignable(
            model.grading_rule_set,
            size_system_id=model.size_system_id,
            customer_id=model.customer_id,
            confirmat=bool(d.get('confirmar_altre_client')),
        )
        if _err is not None:
            payload, status_code = _err
            return Response(payload, status=status_code)

    model.save()
    # PG-2 Cas B: re-materialitza si hi ha ruleset (wipe-and-recreate cobreix canvi de profile).
    # L'atomic embolcalla només la materialització → si peta, el model queda sense MGR i gradua
    # pel fallback PG-1 (ruleset extern). Degradació gràcil INTENCIONAL, no descuit.
    n_regles = None
    if model.grading_rule_set_id:
        from django.db import transaction
        from fhort.models_app.services import (materialize_model_grading_rules,
                                               origen_mgr_des_de_ruleset)
        with transaction.atomic():
            n_regles = materialize_model_grading_rules(
                model, model.grading_rule_set.regles.all(),
                origen=origen_mgr_des_de_ruleset(model.grading_rule_set))
        # R1 — el retorn d'aquesta funció es DESCARTAVA. Materialitzar 0 regles (ruleset buit)
        # esborrava les residents i tornava un 200 mut: exactament el que va buidar el 163.
        # Amb la validació D1 això ja no hauria de poder passar per l'endpoint; si passa igual
        # (dades tocades per un altre camí), que quedi rastre i que la resposta ho digui.
        if n_regles == 0:
            import logging
            logging.getLogger(__name__).warning(
                f"update_model_step2: model {model.codi_intern} (id={model.id}) ha "
                f"materialitzat 0 regles des del GradingRuleSet {model.grading_rule_set_id} "
                f"— el model queda SENSE regles residents."
            )
    return Response({
        'id': model.id,
        'codi_intern': model.codi_intern,
        'regles_materialitzades': n_regles,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def suggested_poms_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    # Migration família → item: els POMs suggerits surten de l'ITEM (garment_type_item),
    # no de la família. Si el model no té item definit, no hi ha suggeriment.
    if not model.garment_type_item_id:
        return Response({'poms': [], 'warning': 'Garment type item no definit'})

    from fhort.pom.models import GarmentPOMMap
    from fhort.pom.nomenclatura import alies_per_pom, camps_de

    maps = GarmentPOMMap.objects.filter(
        garment_type_item=model.garment_type_item,
    ).select_related('pom', 'pom__pom_global').order_by('-is_key', 'ordre')

    # C3 — nomenclatura del CLIENT del model (CustomerPOMAlias). El wizard de definició de
    # POMs treballa un model d'un client concret: el codi i el nom que hi han de sortir són
    # els seus. Additiu — qui no els llegeixi veu exactament el mateix d'abans.
    alias_by_pom = alies_per_pom(model.customer_id)

    result = []
    for m in maps:
        pom = m.pom
        pg = getattr(pom, 'pom_global', None)
        result.append({
            'pom_id': pom.id,
            'pom_code': pom.codi_client,
            'nom_en': pg.nom_en if pg else pom.nom_client,
            'nom_ca': pg.nom_ca if pg else pom.nom_client,
            'abbreviation': pg.abbreviation if pg else '',
            'categoria': pg.categoria if pg else '',
            'is_key': m.is_key,
            'ordre': m.ordre,
            **camps_de(alias_by_pom, pom.id),
        })

    return Response({'poms': result, 'total': len(result)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def materialize_poms_view(request, model_id):
    """POST /api/v1/models/<id>/materialitzar-poms/ — instancia la pertinença de POMs de l'item
    com a BaseMeasurement, copiant is_key/ordre de la plantilla GarmentPOMMap.

    B4 — SEMBRA item→model (copy-at-the-moment): si l'item té valors base (ItemBaseMeasurement),
    copia valor + nom_fitxa + tolerància a la BaseMeasurement amb origen='ITEM_STANDARD'. Si no en
    té, materialitza BUIDA (origen='TEMPLATE', base_value_cm=None) com abans.

    SOBIRANIA DEL MODEL (idempotent): NOMÉS sembra on no hi ha res o on hi ha un TEMPLATE BUIT.
    Una fila amb origen més específic (MANUAL/IMPORTED/FITTED) o amb valor ja posat NO es trepitja:
    a partir del primer valor, el Model és sobirà. Re-executar no clobera res.

    F2.2 — `pom_ids` (llista opcional al body): sembra NOMÉS aquests POMs, sempre que pertanyin al
    GarmentPOMMap de l'item. Sense el paràmetre, es sembra tot el mapa (comportament de sempre, cap
    caller trencat). Un `pom_ids` present i buit és una petició sense feina, no "sembra-ho tot".

    P1 — GUARD DE TALLA (2026-07-22, DIAGNOSI_ITEM_PLANTILLA §B1.5). Un valor de plantilla està
    expressat EN UNA TALLA: la de `GarmentTypeItem.base_size_definition`. Fins ara aquesta vista
    copiava valors item→model sense comparar-la mai amb `Model.base_size_label` — els valors podien
    aterrar a `BaseMeasurement` expressats en una talla diferent de la del model, EN SILENCI. La
    coherència de les dades d'avui és casualitat, no invariant (cap FK, cap constraint, cap codi).
      · talles DIVERGENTS → NO es sembra cap valor; sí la PERTINENÇA (fila TEMPLATE buida), perquè
        la pertinença de POMs és certa encara que la talla no quadri. Avís explícit a la resposta.
      · `base_size_definition` NULL → se sembra com sempre, amb l'avís «talla de plantilla no
        verificada». NO bloqueja: 59 dels 62 items de `fhort` la tenen NULL avui, i bloquejar
        trencaria la sembra de tot el catàleg per una dada que ningú no ha omplert encara."""
    from django.db import transaction
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    if not model.garment_type_item_id:
        return Response({'materialized': 0, 'seeded': 0, 'skipped': 0,
                         'warning': 'Garment type item no definit'})

    from fhort.pom.models import (
        GarmentPOMMap, ItemBaseMeasurement, ItemBaseSet, resolve_item_base_set,
    )
    from fhort.models_app.models import BaseMeasurement

    subconjunt = None
    if 'pom_ids' in request.data:
        crus = request.data.get('pom_ids')
        if not isinstance(crus, list):
            return Response({'error': "pom_ids ha de ser una llista d'ids de POM"}, status=400)
        try:
            subconjunt = {int(x) for x in crus}
        except (TypeError, ValueError):
            return Response({'error': "pom_ids ha de contenir només ids numèrics"}, status=400)

    maps = (GarmentPOMMap.objects
            .filter(garment_type_item=model.garment_type_item)
            .select_related('pom').order_by('ordre'))
    total_template = maps.count()
    if subconjunt is not None:
        maps = maps.filter(pom_id__in=subconjunt)
        # Els ids que no són del mapa de l'item no es sembren en silenci: es reporten.
        desconeguts = sorted(subconjunt - {m.pom_id for m in maps})
    else:
        desconeguts = []
    item = model.garment_type_item

    # B2 (2026-07-25) — EL MÓN MANA. Els valors base ja no pengen de l'item pelat sinó del
    # BaseSet del món del model (item × size_system × fit). Lookup directe, cap heurística.
    base_set = resolve_item_base_set(item, model.size_system_id, model.fit_type)
    base_set_absent = base_set is None

    if base_set is not None:
        ibms = {i.pom_id: i for i in ItemBaseMeasurement.objects.filter(base_set=base_set)}
        talla_item = (getattr(base_set.base_size_definition, 'etiqueta', None) or '').strip()
    else:
        # CAMÍ LLEGAT (conviu mentre no tots els mons tinguin set). Només s'hi cau si el món del
        # model no en té cap, i NOMÉS si l'item és inequívoc: amb 0 o 1 set, les mesures de
        # l'item parlen d'un sol món i el guard V1 les sap jutjar. Amb 2+ sets NO endevinem quin
        # món val — se sembra la pertinença i cap valor, que és el que diu la llei 7.
        sets_item = ItemBaseSet.objects.filter(garment_type_item=item).count()
        if sets_item <= 1:
            ibms = {i.pom_id: i for i in ItemBaseMeasurement.objects.filter(
                garment_type_item=item)}
            talla_item = (getattr(item.base_size_definition, 'etiqueta', None) or '').strip()
        else:
            ibms = {}
            talla_item = ''

    # P1 — GUARD DE TALLA. Es resol UNA vegada, abans del bucle: la talla no depèn del POM.
    # Reorientat a B2: la talla de referència és la del SET del món, no la de l'item pelat
    # (l'item pot vestir-se en diversos sistemes i cadascun té la seva talla base).
    talla_model = (model.base_size_label or '').strip()
    talla_avis = None
    talla_divergent = False
    if not talla_item:
        talla_avis = ("Talla de plantilla NO VERIFICADA: aquest món no té BaseSet i l'item "
                      "tampoc no té `base_size_definition`. Els valors s'han sembrat assumint "
                      f"que ja parlen la talla base del model («{talla_model or '—'}»), però "
                      "ningú no ho ha declarat.")
    elif not talla_model:
        talla_divergent = True
        talla_avis = (f"El model no té talla base definida i la plantilla parla en «{talla_item}»: "
                      "no s'ha sembrat cap VALOR (sí la pertinença de POMs). Fixa la talla base "
                      "del model i torna a sembrar.")
    elif talla_item != talla_model:
        talla_divergent = True
        talla_avis = (f"TALLES DIVERGENTS: la plantilla de l'item està expressada en «{talla_item}» "
                      f"i la talla base del model és «{talla_model}». NO s'ha sembrat cap VALOR "
                      "(sí la pertinença de POMs, que és certa igualment). Un valor en una talla "
                      "que no és la del model és una mesura falsa.")

    materialized = seeded = skipped = 0
    with transaction.atomic():
        for m in maps:
            ibm = ibms.get(m.pom_id)
            # P1 — amb talles divergents un valor de plantilla és una mesura FALSA: la pertinença
            # sí es materialitza (fila TEMPLATE buida), el valor no viatja.
            has_value = (not talla_divergent) and ibm is not None and ibm.base_value_cm is not None
            existing = BaseMeasurement.objects.filter(model=model, pom=m.pom).first()

            if existing is None:
                if has_value:
                    BaseMeasurement.objects.create(
                        model=model, pom=m.pom,
                        base_value_cm=ibm.base_value_cm,
                        nom_fitxa=ibm.nom_fitxa or '',
                        tolerancia_minus=ibm.tol_minus,
                        tolerancia_plus=ibm.tol_plus,
                        origen='ITEM_STANDARD', is_key=m.is_key, ordre=m.ordre,
                    )
                    seeded += 1
                else:
                    BaseMeasurement.objects.create(
                        model=model, pom=m.pom,
                        base_value_cm=None, origen='TEMPLATE',
                        is_key=m.is_key, ordre=m.ordre,
                    )
                    materialized += 1
                continue

            # Ja existeix: sobirania. Només sembra si és un TEMPLATE BUIT i l'item porta valor.
            is_empty_template = existing.origen == 'TEMPLATE' and existing.base_value_cm is None
            if has_value and is_empty_template:
                existing.base_value_cm = ibm.base_value_cm
                existing.nom_fitxa = ibm.nom_fitxa or existing.nom_fitxa
                existing.tolerancia_minus = ibm.tol_minus
                existing.tolerancia_plus = ibm.tol_plus
                existing.origen = 'ITEM_STANDARD'
                existing.save(update_fields=[
                    'base_value_cm', 'nom_fitxa', 'tolerancia_minus',
                    'tolerancia_plus', 'origen', 'updated_at'])
                seeded += 1
            else:
                skipped += 1   # res a sembrar, o fila sobirana (MANUAL/IMPORTED/FITTED/amb valor)

    resposta = {'materialized': materialized, 'seeded': seeded, 'skipped': skipped,
                'total_template': total_template}
    # B2 — el món del model, sempre explícit. Quan hi ha set, el frontend en sap la talla base
    # sense tornar a preguntar; quan no n'hi ha, `code='base_set_absent'` porta el CONTEXT
    # necessari perquè la UI n'ofereixi el naixement (B4). El backend MAI crea el set sol.
    if base_set is not None:
        resposta['base_set'] = {
            'id': base_set.pk,
            'size_system_id': base_set.size_system_id,
            'size_system': base_set.size_system.codi,
            'fit_type': base_set.fit_type.codi if base_set.fit_type_id else None,
            'base_size_label': base_set.base_size_definition.etiqueta,
            'origen': base_set.origen,
        }
    else:
        resposta['base_set'] = None
        resposta['base_set_absent'] = {
            'code': 'base_set_absent',
            'garment_type_item_id': item.pk,
            'garment_type_item_code': item.code,
            'size_system_id': model.size_system_id,
            'size_system': model.size_system.codi if model.size_system_id else None,
            'fit_type': model.fit_type or None,
        }

    # P1 — el veredicte de la talla mai és silenciós, ni quan deixa passar la sembra.
    resposta['talla_item'] = talla_item or None
    resposta['talla_model'] = talla_model or None
    resposta['talla_verificada'] = bool(talla_item) and not talla_divergent
    resposta['valors_bloquejats_per_talla'] = talla_divergent
    if talla_avis:
        resposta['talla_avis'] = talla_avis
    if subconjunt is not None:
        resposta['requested'] = len(subconjunt)
        if desconeguts:
            resposta['pom_ids_desconeguts'] = desconeguts
            resposta['warning'] = ('Aquests POMs no pertanyen al GarmentPOMMap de '
                                   f"l'item i no s'han sembrat: {desconeguts}")
    return Response(resposta)


#: Sprint B — tipus de ModelFitxer que viatgen en una còpia model→model. SKETCH i PATRO
#: descriuen la PEÇA (dibuix i patronatge) i són el patrimoni que un model germà vol
#: heretar. DOCUMENT en queda FORA sempre: és el paper d'origen d'UNA importació concreta
#: (`extraction_views.py:2624`), la prova documental d'un fet que no ha passat al destí.
TIPUS_COPIABLES_MODEL_A_MODEL = ('SKETCH_FLETXES', 'SKETCH_NET', 'SKETCH_SVG', 'PATRO')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def copiar_de_model_view(request, model_id, src_id):
    """POST /api/v1/models/<dst>/copiar-de/<src>/ — copia el patrimoni d'un model a un altre.

    MIRALL de `materialize_poms_view` (:986): mateixa llei de SOBIRANIA, mateix guard de
    talla, mateixa atomicitat. La diferència és la font: allà l'ITEM (plantilla del catàleg),
    aquí un altre MODEL. El que es copia són quatre coses independents, cadascuna amb el seu
    flag al body (tots per defecte certs):

      · `copy_run`     — size_system + size_run_model + base_size_label. NOMÉS si el destí no
        té cap BaseMeasurement pròpia: un run és el marc en què estan expressats els valors
        que el destí JA té, i canviar-lo sota seu els convertiria en mesures falses. Si el
        destí en té, el flag s'IGNORA i la resposta ho diu (mai trepitjar en silenci).
      · `copy_values`  — GUARD P1 TRANSPOSAT (de :1071-1092). Un valor està expressat EN UNA
        TALLA. Si el run s'acaba de copiar, les bases coincideixen per construcció. Si no,
        es comparen `src.base_size_label` i `dst.base_size_label`: divergents → es copia
        NOMÉS la pertinença (fila TEMPLATE buida) i cap valor, amb avís explícit. Sense
        aquest guard es reintrodueix el bug que P1 va corregir.
      · `copy_grading` — assigna el `grading_rule_set` de l'origen i re-materialitza les
        regles residents, exactament com `update_model_step2` (:917-936). NO es copien ni
        `ModelGradingOverride` ni Watchpoints: són el judici d'un altre model sobre les
        SEVES dades, no un patrimoni transferible.
      · `copy_files`   — SKETCH* i PATRO (mai DOCUMENT). Bytes nous pel mateix camí que el
        germà per-fitxer (`ModelFitxerViewSet.usar_al_model`, :345), amb versió pròpia del
        destí i nom canònic `{codi}_{TIPUS}_{NNN}`.

    SOBIRANIA (idèntica a la sembra item→model): una fila del destí amb origen específic
    (MANUAL/IMPORTED/FITTED) o amb valor ja posat NO es trepitja mai; només s'omple un
    TEMPLATE BUIT. Les files intactes es compten a `skipped`, no desapareixen del report.

    `pom_ids` (llista opcional al body) acota la còpia a aquests POMs de l'origen; els que no
    hi pertanyen es reporten, no s'ignoren en silenci.
    """
    import logging
    import os

    from django.core.files.base import ContentFile

    from . import services_ftt_document as ftt_svc
    from .services_fitxers import marcar_procedencia, save_model_file

    try:
        dst = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model destí no trobat'}, status=404)
    try:
        src = Model.objects.select_related('grading_rule_set', 'size_system').get(id=src_id)
    except Model.DoesNotExist:
        return Response({'error': "Model d'origen no trobat"}, status=404)

    if src.pk == dst.pk:
        return Response({'error': "L'origen i el destí són el mateix model."}, status=400)

    # `_truthy` (:3241) és la font única de lectura de banderes del body en aquest mòdul: un
    # `false` JSON i un `"false"` de formulari han de dir el mateix. Absent = cert (per defecte
    # es copia tot); qualsevol valor no-truthy explícit apaga la peça.
    copy_values = _truthy(request.data.get('copy_values', True))
    copy_run = _truthy(request.data.get('copy_run', True))
    copy_grading = _truthy(request.data.get('copy_grading', True))
    copy_files = _truthy(request.data.get('copy_files', True))

    subconjunt = None
    if 'pom_ids' in request.data:
        crus = request.data.get('pom_ids')
        if not isinstance(crus, list):
            return Response({'error': "pom_ids ha de ser una llista d'ids de POM"}, status=400)
        try:
            subconjunt = {int(x) for x in crus}
        except (TypeError, ValueError):
            return Response({'error': "pom_ids ha de contenir només ids numèrics"}, status=400)

    # ── Inventari de l'origen. Un model buit del tot no és una font: 400 abans de tocar res.
    src_mesures = list(BaseMeasurement.objects.filter(model=src, is_active=True)
                       .select_related('pom').order_by('ordre', 'pom_id'))
    src_fitxers = list(ModelFitxer.objects.filter(
        model=src, tipus__in=TIPUS_COPIABLES_MODEL_A_MODEL, is_current=True,
    ).exclude(fitxer='').exclude(fitxer__isnull=True).order_by('tipus', 'id'))
    if not src_mesures and not src.grading_rule_set_id and not src_fitxers:
        return Response({
            'error': (f"El model d'origen «{src.codi_intern}» no té res a copiar: cap mesura "
                      'base activa, cap regla de graduació i cap croquis ni patró.'),
            'codi': 'origen_buit',
        }, status=400)

    if subconjunt is not None:
        poms_origen = {bm.pom_id for bm in src_mesures}
        desconeguts = sorted(subconjunt - poms_origen)
        src_mesures = [bm for bm in src_mesures if bm.pom_id in subconjunt]
    else:
        desconeguts = []

    warnings = []

    # ── copy_run. El destí amb mesures pròpies és sobirà del seu marc: el flag s'ignora.
    dst_te_mesures = BaseMeasurement.objects.filter(model=dst).exists()
    run_copied = False
    if copy_run and dst_te_mesures:
        warnings.append(
            f"S'ha demanat copiar el sistema de talles i el run, però el model destí "
            f"«{dst.codi_intern}» ja té mesures base pròpies: el seu run és el marc en què "
            'estan expressades. El flag s\'ha IGNORAT i no s\'ha tocat res del run.')
    elif copy_run:
        dst.size_system_id = src.size_system_id
        dst.size_run_model = src.size_run_model
        dst.base_size_label = src.base_size_label
        dst.save(update_fields=['size_system', 'size_run_model', 'base_size_label'])
        run_copied = True

    # ── GUARD P1 TRANSPOSAT. Amb el run copiat les bases coincideixen per construcció.
    talla_src = (src.base_size_label or '').strip()
    talla_dst = (dst.base_size_label or '').strip()
    talla_divergent = False
    if run_copied:
        pass
    elif not talla_src:
        warnings.append(
            f"Talla base de l'origen NO DECLARADA: el model «{src.codi_intern}» no té talla "
            f"base. Els valors s'han copiat assumint que ja parlen la talla base del destí "
            f"(«{talla_dst or '—'}»), però ningú no ho ha declarat.")
    elif not talla_dst:
        talla_divergent = True
        warnings.append(
            f"El model destí no té talla base definida i l'origen parla en «{talla_src}»: no "
            "s'ha copiat cap VALOR (sí la pertinença de POMs). Fixa la talla base del destí i "
            'torna a copiar.')
    elif talla_src != talla_dst:
        talla_divergent = True
        warnings.append(
            f"TALLES DIVERGENTS: l'origen està expressat en «{talla_src}» i la talla base del "
            f"destí és «{talla_dst}». NO s'ha copiat cap VALOR (sí la pertinença de POMs, que "
            'és certa igualment). Un valor en una talla que no és la del model és una mesura '
            'falsa.')

    seeded = values_copied = skipped = 0
    grading_set = None
    n_regles = None

    with transaction.atomic():
        # L'ordre és GLOBAL i únic dins el model (:2420). Si el destí ja en té de propis, la
        # còpia s'HI AFEGEIX AL FINAL conservant l'ordre relatiu de l'origen, en comptes de
        # barrejar dos ordres globals; si està verge, l'ordre de l'origen es copia tal qual.
        ordre_base = 0
        if dst_te_mesures:
            from django.db.models import Max
            ordre_base = (BaseMeasurement.objects.filter(model=dst)
                          .aggregate(m=Max('ordre'))['m'] or 0)

        for rang, bm in enumerate(src_mesures, start=1):
            te_valor = (copy_values and not talla_divergent and bm.base_value_cm is not None)
            existent = BaseMeasurement.objects.filter(model=dst, pom_id=bm.pom_id).first()

            if existent is None:
                nova = BaseMeasurement(
                    model=dst, pom_id=bm.pom_id,
                    base_value_cm=bm.base_value_cm if te_valor else None,
                    # `notes` NO viatja: és text lliure escrit SOBRE l'altre model (p.ex. «el
                    # proveïdor va confirmar 62 cm en aquesta peça») i copiat aquí seria una
                    # afirmació falsa amb aparença d'auditoria.
                    nom_fitxa=(bm.nom_fitxa or '') if te_valor else '',
                    tolerancia_minus=bm.tolerancia_minus if te_valor else None,
                    tolerancia_plus=bm.tolerancia_plus if te_valor else None,
                    origen='COPIED' if te_valor else 'TEMPLATE',
                    is_key=bm.is_key,
                    ordre=(ordre_base + rang) if dst_te_mesures else bm.ordre,
                )
                nova._changed_by = request.user
                nova.save()
                seeded += 1
                if te_valor:
                    values_copied += 1
                continue

            # Ja existeix: SOBIRANIA. Només s'omple un TEMPLATE BUIT.
            template_buit = existent.origen == 'TEMPLATE' and existent.base_value_cm is None
            if te_valor and template_buit:
                existent.base_value_cm = bm.base_value_cm
                existent.nom_fitxa = bm.nom_fitxa or existent.nom_fitxa
                existent.tolerancia_minus = bm.tolerancia_minus
                existent.tolerancia_plus = bm.tolerancia_plus
                existent.origen = 'COPIED'
                existent._changed_by = request.user
                existent.save(update_fields=[
                    'base_value_cm', 'nom_fitxa', 'tolerancia_minus',
                    'tolerancia_plus', 'origen', 'updated_at'])
                values_copied += 1
            else:
                skipped += 1

        # ── copy_grading. Mateix camí que `update_model_step2` (:917-936): assignar la FK i
        #    re-materialitzar. NO es copien overrides ni watchpoints.
        if copy_grading and src.grading_rule_set_id:
            from fhort.models_app.services import (materialize_model_grading_rules,
                                                   origen_mgr_des_de_ruleset)
            dst.grading_rule_set_id = src.grading_rule_set_id
            dst.save(update_fields=['grading_rule_set'])
            grading_set = src.grading_rule_set_id
            n_regles = materialize_model_grading_rules(
                dst, src.grading_rule_set.regles.all(),
                origen=origen_mgr_des_de_ruleset(src.grading_rule_set))
            if n_regles == 0:
                # R1 (el forat que va buidar el 163): un ruleset buit esborra les residents i
                # torna un 200 mut. Aquí no: queda al log i a la resposta.
                logging.getLogger(__name__).warning(
                    "copiar_de_model: model %s (id=%s) ha materialitzat 0 regles des del "
                    "GradingRuleSet %s — el model queda SENSE regles residents.",
                    dst.codi_intern, dst.id, src.grading_rule_set_id)
                warnings.append(
                    f"El GradingRuleSet «{src.grading_rule_set.nom}» de l'origen no té cap "
                    'regla: el destí queda SENSE regles residents de graduació.')
        elif copy_grading:
            warnings.append(f"El model d'origen «{src.codi_intern}» no té graduació assignada: "
                            "no s'ha copiat cap regla.")

    # ── copy_files. FORA de l'atomic de les mesures: escriu BYTES a disc, i un rollback de
    #    transacció no els desfaria (deixaria fitxers orfes). Cada fitxer és una unitat pròpia,
    #    com al germà per-fitxer (`usar_al_model`, :345).
    files_copied = 0
    if copy_files:
        for origen_f in src_fitxers:
            anterior = (ModelFitxer.objects.filter(model=dst, tipus=origen_f.tipus)
                        .order_by('-versio', '-id').first())
            num = (anterior.versio + 1) if anterior else 1
            ext = os.path.splitext(origen_f.nom_fitxer)[1] or ''
            nom = f'{dst.codi_intern}_{origen_f.tipus}_{num:03d}{ext}'
            origen_f.fitxer.open('rb')
            try:
                # Mateixa porta que els dos cicles d'importació: un `.ftt` mai es copia tal
                # qual. Cap dels tipus copiables ho és avui, però la porta és única. Per a la
                # resta de tipus `font` ÉS el FieldFile de l'origen: s'ha de mantenir obert
                # fins que `save_model_file` n'hagi llegit els bytes (mateixa forma que el
                # germà per-fitxer, :378-387).
                font, _report = ftt_svc.font_per_al_model(origen_f, dst)
                nou = save_model_file(dst, font, versio_anterior=anterior,
                                      tipus=origen_f.tipus, origen='upload', nom=nom)
            except (ValueError, OSError) as e:
                warnings.append(f"No s'ha pogut copiar «{origen_f.nom_fitxer}»: {e}")
                continue
            finally:
                origen_f.fitxer.close()
            # Procedència: model→model és `derivat_de_model`. `derivat_de_item` es CONSERVA si
            # l'origen el porta — la cadena de procedència del catàleg no s'ha de perdre pel
            # camí (aquest croquis segueix venint d'aquell ItemFitxer).
            camps = {'derivat_de_model': origen_f}
            if origen_f.derivat_de_item_id:
                camps['derivat_de_item'] = origen_f.derivat_de_item
            marcar_procedencia(nou, request.user, **camps)
            files_copied += 1

    resposta = {
        'seeded': seeded,
        'values_copied': values_copied,
        'skipped': skipped,
        'run_copied': run_copied,
        'grading_set': grading_set,
        'files_copied': files_copied,
        'warnings': warnings,
        # Context del veredicte de talla, sempre explícit (com a `materialitzar-poms`).
        'origen': {'id': src.id, 'codi_intern': src.codi_intern},
        'talla_origen': talla_src or None,
        'talla_desti': (dst.base_size_label or '').strip() or None,
        'valors_bloquejats_per_talla': talla_divergent,
        'regles_materialitzades': n_regles,
    }
    if subconjunt is not None:
        resposta['requested'] = len(subconjunt)
        if desconeguts:
            resposta['pom_ids_desconeguts'] = desconeguts
            warnings.append("Aquests POMs no són del model d'origen i no s'han copiat: "
                            f'{desconeguts}')
    return Response(resposta)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_table_view(request, model_id):
    """POST /api/v1/models/<id>/tancar-taula/ — Sprint B · tancar la taula de mides.

    Resol (o crea, get_or_create_size_fitting) el SizeFitting del model i executa
    close_base → estat final 'Tancat'. Avís clar si encara no hi ha mides entrades
    (BaseMeasurement amb valor): no es pot tancar una taula buida."""
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    from fhort.models_app.models import BaseMeasurement
    # Guarda UX: una taula sense cap mida entrada (només files TEMPLATE buides) no es tanca.
    if not BaseMeasurement.objects.filter(
        model=model, is_active=True, base_value_cm__isnull=False
    ).exists():
        return Response(
            {'error': 'Cal introduir mides abans de tancar la taula.'},
            status=400,
        )

    from fhort.pom.services import get_or_create_size_fitting, close_base
    profile = getattr(request.user, 'profile', None)
    try:
        # Atòmic (B4): si es tanca la taula, es tanca la tasca. Tot o res.
        with transaction.atomic():
            sf = get_or_create_size_fitting(model, request.user.id)
            result = close_base(sf.id, request.user.id)
            pom_task = _close_pom_task_for_model(model, profile)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error closing table")
        return Response({'error': str(e)}, status=500)

    return Response({'sf_id': sf.id, 'pom_task': pom_task, **result})


def _close_pom_task_for_model(model, profile):
    """B4 · en tancar la taula, la tasca POM del model passa a Done via transition_task
    (l'única porta: status=Done, finished_at, tanca timer, record_actual_time, log).
    Done només és vàlid des de InProgress → si està Pending/Paused, hi passem primer.
    Sense tasca pom → no fa res. Ja Done → idempotent."""
    from fhort.tasks.models import ModelTask
    from fhort.tasks.services_c import transition_task

    task = (ModelTask.objects
            .filter(model=model, task_type__code='pom')
            .order_by('id').first())
    if not task:
        return {'closed': False, 'reason': 'no_pom_task'}
    if task.status == 'Done':
        return {'closed': False, 'reason': 'already_done', 'task_id': task.id}

    # Done només es pot assolir des de InProgress (ALLOWED a services_c). Pending/Paused
    # hi passen primer perquè la transició no peti.
    if task.status in ('Pending', 'Paused'):
        transition_task(task, 'InProgress', profile)
        task.refresh_from_db()
    transition_task(task, 'Done', profile)
    return {'closed': True, 'task_id': task.id}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def measurements_table_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    from fhort.models_app.models import BaseMeasurement

    size_run = []
    if model.size_run_model:
        size_run = [s.strip() for s in model.size_run_model.split('·') if s.strip()]

    base_measurements = BaseMeasurement.objects.filter(
        model=model,
        is_active=True,
    ).select_related('pom', 'pom__pom_global').order_by('ordre', 'pom__codi_client')

    graded_by_pom = {}
    try:
        from fhort.fitting.models import GradedSpec
        from fhort.fitting.services import (
            _resolve_working_size_fitting, vigent_grading_version,
        )
        # Versió vigent: criteri ÚNIC compartit amb graded-table (SizeFitting de treball
        # + is_active prioritari, fallback a la més recent). Abans: first()/-data divergent.
        sf = _resolve_working_size_fitting(model)
        if sf:
            gv = vigent_grading_version(sf)
            if gv:
                for spec in GradedSpec.objects.filter(grading_version=gv):
                    pom_id = spec.pom_id
                    if pom_id not in graded_by_pom:
                        graded_by_pom[pom_id] = {}
                    graded_by_pom[pom_id][spec.size_label] = (
                        float(spec.graded_value_cm) if spec.graded_value_cm is not None else None
                    )
    except Exception:
        pass

    # Règim per POM (logica/increments/break) per a l'editor propagat: resolutor canònic
    # (ModelGradingRule resident → fallback GradingRule del rule_set), batched una sola vegada.
    rules_by_pom = {}
    try:
        from fhort.pom.services import _load_grading_rules
        rules_by_pom = _load_grading_rules(model)
    except Exception:
        rules_by_pom = {}

    # C4 — GRADING INFORMAT AL WIZARD. El resolutor canònic mira el model (regla resident) i
    # el seu `grading_rule_set`; el ruleset del client, però, sovint penja del GARMENT TYPE
    # ITEM (RS146-149 hi són assignats), i llavors el tècnic es trobava les columnes Règim /
    # Delta / Break buides tot i que la regla existeix. Aquí s'hi cau NOMÉS PER OMPLIR LA
    # PANTALLA: és lectura, i el motor de graduació no en sap res —si el tècnic desa, la regla
    # passa a ser resident del model, que és qui mana. Sense ruleset al GTI, res canvia.
    gti_rule_set_id = getattr(model.garment_type_item, 'grading_rule_set_id', None)
    if gti_rule_set_id:
        from fhort.pom.models import GradingRule
        for r in GradingRule.objects.filter(rule_set_id=gti_rule_set_id, actiu=True):
            rules_by_pom.setdefault(r.pom_id, r)

    def _flt(v):
        return float(v) if v is not None else None

    # C3 — nomenclatura del CLIENT del model, mateix resolutor que la resta de superfícies.
    from fhort.pom.nomenclatura import alies_per_pom, camps_de
    alias_by_pom = alies_per_pom(model.customer_id)

    rows = []
    for bm in base_measurements:
        pom = bm.pom
        pg = getattr(pom, 'pom_global', None)
        rule = rules_by_pom.get(pom.id)
        rows.append({
            'id': bm.id,
            'ordre': bm.ordre,
            'pom_id': pom.id,
            'pom_code': pom.codi_client,
            **camps_de(alias_by_pom, pom.id),
            'nom_fitxa': bm.nom_fitxa or '',
            'nom_en': pg.nom_en if pg else pom.nom_client,
            'nom_ca': pg.nom_ca if pg else pom.nom_client,
            'abbreviation': pg.abbreviation if pg else '',
            'base_value_cm': float(bm.base_value_cm) if bm.base_value_cm is not None else None,
            'is_key': bm.is_key,
            'origen': bm.origen,
            'notes': bm.notes or '',
            'graded': graded_by_pom.get(pom.id, {}),
            # Règim (additiu; consumidors antics ignoren camps desconeguts).
            'logica': getattr(rule, 'logica', None) if rule else None,
            'increment_base': _flt(getattr(rule, 'increment_base', None)) if rule else None,
            'increment_break': _flt(getattr(rule, 'increment_break', None)) if rule else None,
            'talla_break_label': getattr(rule, 'talla_break_label', None) if rule else None,
        })

    base_size = model.base_size_label

    def _size_value(row, size):
        # The base-size value lives in base_value_cm; the rest, in graded (GradedSpec).
        if size == base_size:
            return row['base_value_cm']
        return row['graded'].get(size)

    # Sizes with at least one real value (≠ null) in some row.
    sizes_with_data = [
        s for s in size_run
        if any(_size_value(r, s) is not None for r in rows)
    ]

    # Δ = mean of increments between consecutive sizes with data; None if <2 values.
    deltas = {}
    for r in rows:
        values = [_size_value(r, s) for s in sizes_with_data]
        values = [v for v in values if v is not None]
        if len(values) >= 2:
            increments = [values[i + 1] - values[i] for i in range(len(values) - 1)]
            deltas[str(r['pom_id'])] = round(sum(increments) / len(increments), 2)
        else:
            deltas[str(r['pom_id'])] = None

    # Taula tancada? (SizeFitting estat='Tancat' → vista de només lectura al frontend)
    tancat = False
    try:
        from fhort.fitting.models import SizeFitting
        tancat = SizeFitting.objects.filter(model=model, estat='Tancat').exists()
    except Exception:
        tancat = False

    return Response({
        'model_id': model.id,
        'codi_intern': model.codi_intern,
        'base_size': base_size,
        'size_run': size_run,               # kept so as not to break consumers
        'size_run_complet': size_run,
        'sizes_amb_dades': sizes_with_data,
        'deltes': deltas,
        'rows': rows,
        'total_poms': len(rows),
        'tancat': tancat,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_measurements_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    measurements = request.data.get('measurements', [])
    # keep_pom_ids: TOTS els pom_id que segueixen a la taula (amb valor O buits/TEMPLATE). Els
    # BaseMeasurement actius del model el pom dels quals NO hi és → soft-delete (is_active=False),
    # com fa el xat IA, per persistir la X d'eliminar fila. None = client antic, no desactivar.
    keep_pom_ids = request.data.get('keep_pom_ids', None)
    if not measurements and keep_pom_ids is None:
        return Response({'error': 'measurements és obligatori'}, status=400)

    from fhort.pom.models import POMMaster
    from fhort.models_app.models import BaseMeasurement

    created = updated = deactivated = 0
    errors = []

    with transaction.atomic():
        for m in measurements:
            pom_id = m.get('pom_id')
            value = m.get('base_value_cm')
            if not pom_id or value is None:
                errors.append(f'pom_id i base_value_cm obligatoris')
                continue
            try:
                pom = POMMaster.objects.get(id=pom_id)
                _, was_created = BaseMeasurement.objects.update_or_create(
                    model=model, pom=pom,
                    defaults={
                        'base_value_cm': float(value),
                        'notes': m.get('notes', ''),
                        'nom_fitxa': m.get('nom_fitxa', '') or '',
                        'origen': 'MANUAL',
                        # Re-entrar un valor reactiva una fila prèviament eliminada.
                        'is_active': True,
                        # Sprint 5B.1: copy tolerance from the catalogue POM.
                        'tolerancia_minus': pom.tolerancia_default_minus,
                        'tolerancia_plus': pom.tolerancia_default_plus,
                    }
                )
                if was_created: created += 1
                else: updated += 1
            except POMMaster.DoesNotExist:
                errors.append(f'POMMaster {pom_id} no trobat')

        if keep_pom_ids is not None:
            keep = [int(x) for x in keep_pom_ids]
            deactivated = (BaseMeasurement.objects
                           .filter(model=model, is_active=True)
                           .exclude(pom_id__in=keep)
                           .update(is_active=False))

    # NOTE: set-measurements només fa upsert de BaseMeasurement (+ el log via signal). La generació
    # de GradedSpec viu EXCLUSIVAMENT a generar-grading → generate_graded_specs (l'únic camí que
    # respecta ModelGradingOverride). El grading inline d'aquí estava trencat (rule.increment_cm no
    # existeix → delta 0) i clobberava els overrides; eliminat.
    return Response({'created': created, 'updated': updated, 'deactivated': deactivated,
                     'errors': errors},
                    status=201 if not errors else 207)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def gravar_pom_view(request, model_id):
    """POST /api/v1/models/<id>/gravar-pom/

    Acte lleuger de genesi POM: persisteix base + nomenclatura + regles residents i tanca
    la ModelTask `pom` a Done. No tanca SizeFitting, no genera GradedSpec i no propaga.
    """
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return Response({'error': 'Usuari sense perfil en aquest tenant.'}, status=403)

    measurements = request.data.get('measurements', [])
    rules = request.data.get('rules', [])
    keep_pom_ids = request.data.get('keep_pom_ids', None)
    if not measurements and keep_pom_ids is None:
        return Response({'error': 'measurements és obligatori'}, status=400)

    from fhort.pom.models import GradingRule, POMMaster
    from fhort.models_app.models import BaseMeasurement, ModelGradingRule

    def _to_float(value, field_name, errors):
        if value in (None, ''):
            return None
        try:
            return float(str(value).replace(',', '.'))
        except (TypeError, ValueError):
            errors.append(f'{field_name} ha de ser numèric')
            return None

    def _to_decimal(value, field_name, errors):
        if value in (None, ''):
            return None
        try:
            return Decimal(str(value).replace(',', '.'))
        except (InvalidOperation, TypeError, ValueError):
            errors.append(f'{field_name} ha de ser numèric')
            return None

    def _break_pos(label):
        if not label or not model.size_run_model:
            return None
        run = [s.strip() for s in model.size_run_model.replace(';', '·').split('·') if s.strip()]
        return run.index(label) if label in run else None

    errors = []
    prepared = []
    for m in measurements:
        pom_id = m.get('pom_id')
        value = _to_float(m.get('base_value_cm'), 'base_value_cm', errors)
        if not pom_id or value is None:
            errors.append('pom_id i base_value_cm obligatoris')
            continue
        # D2 — una talla base a 0 és físicament impossible. O el POM no aplica a aquest model
        # (i llavors no s'entra, no s'entra a zero), o és un error de teclat. El motor tracta
        # el 0 com a "el POM no existeix" i no en gradua cap cel·la: si es deixés entrar, la
        # mesura desapareixeria de la taula sense dir-ho a ningú.
        if value == 0:
            errors.append(
                f"POM {pom_id}: la mesura base no pot ser 0 cm. Si aquesta mesura no aplica "
                f"a aquest model, deixa-la buida o desactiva-la; no la posis a zero."
            )
            continue
        prepared.append((m, value))

    if not prepared:
        errors.append('Cal introduir almenys una mida base abans de gravar POM')
    if errors:
        return Response({'errors': errors}, status=400)

    created = updated = deactivated = rules_saved = 0
    try:
        with transaction.atomic():
            had_base_before = BaseMeasurement.objects.filter(
                model=model, is_active=True, base_value_cm__isnull=False,
            ).exists()

            for m, value in prepared:
                try:
                    pom = POMMaster.objects.get(id=m.get('pom_id'))
                except POMMaster.DoesNotExist:
                    errors.append(f"POMMaster {m.get('pom_id')} no trobat")
                    continue

                bm = BaseMeasurement.objects.filter(model=model, pom=pom).first()
                if bm is None:
                    bm = BaseMeasurement(model=model, pom=pom, created_by=request.user)
                    created += 1
                else:
                    updated += 1
                bm.base_value_cm = value
                bm.notes = m.get('notes', '') or ''
                bm.nom_fitxa = m.get('nom_fitxa', '') or ''
                bm.origen = 'MANUAL'
                bm.is_active = True
                bm.tolerancia_minus = pom.tolerancia_default_minus
                bm.tolerancia_plus = pom.tolerancia_default_plus
                bm._changed_by = request.user
                bm._motiu = 'gravar_pom'
                bm.save()

            if errors:
                raise ValueError('; '.join(errors))

            if keep_pom_ids is not None:
                keep = [int(x) for x in keep_pom_ids]
                deactivated = (BaseMeasurement.objects
                               .filter(model=model, is_active=True)
                               .exclude(pom_id__in=keep)
                               .update(is_active=False))

            valid_logiques = {code for code, _ in GradingRule.LOGICA_CHOICES}
            for r in rules:
                pom_id = r.get('pom_id')
                if not pom_id:
                    continue
                logica = (r.get('logica') or '').strip().upper() or None
                if logica is not None and logica not in valid_logiques:
                    errors.append(f"logica ha de ser un de: {', '.join(sorted(valid_logiques))}")
                    continue
                src = (GradingRule.objects.filter(
                           rule_set_id=model.grading_rule_set_id, pom_id=pom_id).first()
                       if model.grading_rule_set_id else None)
                rule = ModelGradingRule.objects.filter(model=model, pom_id=pom_id).first()
                if rule is None:
                    rule = ModelGradingRule(
                        model=model, pom_id=pom_id, actiu=True,
                        logica=(src.logica if src else 'LINEAR'),
                        increment=(src.increment if src else 0),
                        valors_step=(src.valors_step if src else None),
                        increment_base=(src.increment_base if src else None),
                        increment_break=(src.increment_break if src else None),
                        talla_break_label=(src.talla_break_label if src else None),
                        talla_break_pos=(src.talla_break_pos if src else None),
                    )
                if logica is not None:
                    rule.logica = logica
                if 'increment_base' in r:
                    rule.increment_base = _to_decimal(r.get('increment_base'), 'increment_base', errors)
                if 'increment_break' in r:
                    rule.increment_break = _to_decimal(r.get('increment_break'), 'increment_break', errors)
                if 'talla_break_label' in r:
                    label = (r.get('talla_break_label') or '').strip() or None
                    rule.talla_break_label = label
                    rule.talla_break_pos = _break_pos(label)
                # A3 (2026-07-22) — MATEIX guard que set_pom_regim_view. Aquest camí
                # (gravar_pom, la taula de gènesi) escrivia LINEAR+0 sense cap comprovació:
                # era el forat per on la llei encara es podia trencar.
                if es_linear_degenerada(rule.logica, rule.increment_base, rule.increment,
                                        rule.increment_break, rule.talla_break_label):
                    errors.append(f'POM {pom_id}: {MISSATGE_LINEAR_ZERO}')
                    continue
                rule.origen = 'MANUAL'
                rule.actiu = True
                rule.save()
                rules_saved += 1

            if errors:
                raise ValueError('; '.join(errors))

            if not BaseMeasurement.objects.filter(
                model=model, is_active=True, base_value_cm__isnull=False,
            ).exists():
                raise ValueError('Cal introduir mides abans de gravar POM')

            pom_task = _close_pom_task_for_model(model, profile)
            if pom_task.get('reason') == 'no_pom_task':
                raise ValueError('Cal obrir la tasca POM abans de gravar-la')
    except ValueError as e:
        return Response({'error': str(e)}, status=400)

    return Response({
        'created': created,
        'updated': updated,
        'deactivated': deactivated,
        'rules_saved': rules_saved,
        'reseed': had_base_before,
        'pom_task': pom_task,
    }, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reorder_measurements_view(request, model_id):
    """
    Update the order of a model's BaseMeasurements.
    Payload: { order: [bm_id_1, bm_id_2, ...] }
    """
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    order = request.data.get('order', [])
    if not order:
        return Response({'error': 'order és obligatori'}, status=400)

    from fhort.models_app.models import BaseMeasurement
    for i, bm_id in enumerate(order):
        BaseMeasurement.objects.filter(id=bm_id, model=model).update(ordre=i)

    return Response({'updated': len(order)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_file_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    uploaded_file = request.FILES.get('fitxer')
    if not uploaded_file:
        return Response({'error': 'fitxer és obligatori'}, status=400)

    from .services_fitxers import (ConversioFallida, UploadRejected, converteix_heic_a_jpeg,
                                   es_heic, save_model_file, validate_upload)

    # Contracte Finder: `tipus` opcional (neutre si no es dona). Sense autoincrement per
    # tipus — la versió la governa el servei via la cadena. `categoria` ja no s'accepta
    # (eix deprecat, S03a · P1.2): el Finder no l'ha enviada mai.
    tipus = request.data.get('tipus') or None
    nom = request.data.get('nom') or uploaded_file.name

    # D12/D18 — mateix guard i mateixa resposta 400 que ItemFitxerViewSet.create: aquest era
    # l'únic camí d'upload que no validava ni extensió ni mida.
    try:
        validate_upload(uploaded_file, nom)
    except UploadRejected as e:
        return Response({'error': str(e)}, status=400)

    # Les fotos de fitting es fan amb el mòbil i un iPhone les desa en HEIC, que cap navegador
    # d'escriptori no pinta. S'accepten a la pujada i es converteixen AQUÍ: el que entra a la
    # cadena de versions és sempre un JPEG. No es desa mai l'original — la decisió és desar
    # NOMÉS el JPEG, i guardar les dues coses duplicaria l'emmagatzematge sense que ningú
    # arribés a obrir la HEIC.
    if es_heic(nom, getattr(uploaded_file, 'content_type', '')):
        try:
            uploaded_file, nom = converteix_heic_a_jpeg(uploaded_file, nom)
        except ConversioFallida as e:
            return Response({'error': str(e)}, status=422)

    # versio_anterior_id opcional → encadena una nova versió d'un fitxer existent.
    versio_anterior = None
    versio_anterior_id = request.data.get('versio_anterior_id')
    if versio_anterior_id:
        try:
            versio_anterior = ModelFitxer.objects.get(id=versio_anterior_id, model=model)
        except ModelFitxer.DoesNotExist:
            return Response(
                {'error': 'versio_anterior_id no vàlid per a aquest model'}, status=400)

    mf = save_model_file(
        model, uploaded_file,
        versio_anterior=versio_anterior,
        tipus=tipus,
        origen='upload',
        nom=nom,
    )
    perfil = getattr(request.user, 'profile', None)
    if perfil is not None:
        mf.pujat_per = perfil
        mf.save(update_fields=['pujat_per'])

    return Response({
        'id': mf.id,
        'nom_fitxer': mf.nom_fitxer,
        'tipus': mf.tipus,
        'versio': mf.versio,
        'is_current': mf.is_current,
        'versio_anterior': mf.versio_anterior_id,
        'url': request.build_absolute_uri(mf.fitxer.url) if mf.fitxer else None,
    }, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_analysis_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    import anthropic
    import base64
    import json
    from django.conf import settings

    base_measurements = BaseMeasurement.objects.filter(
        model=model, is_active=True
    ).select_related('pom').order_by('ordre')

    mesures_text = "\n".join([
        f"- {bm.pom.codi_client}: {bm.base_value_cm}cm ({bm.pom.nom_client or ''})"
        for bm in base_measurements
    ])

    fitxers_analisi = list(ModelFitxer.objects.filter(
        model=model,
        tipus__in=['PATRO', 'ESCALAT', 'SKETCH_FLETXES', 'SKETCH_NET']
    ).order_by('-id')[:5])

    content_blocks = []
    for mf in fitxers_analisi:
        if not mf.fitxer:
            continue
        try:
            with mf.fitxer.open('rb') as f:
                data = f.read()
            ext = mf.nom_fitxer.split('.')[-1].lower()
            if ext == 'pdf':
                content_blocks.append({
                    'type': 'document',
                    'source': {
                        'type': 'base64',
                        'media_type': 'application/pdf',
                        'data': base64.standard_b64encode(data).decode('utf-8'),
                    },
                    'title': mf.nom_fitxer,
                })
            elif ext in ('jpg', 'jpeg', 'png', 'svg'):
                media_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                             'png': 'image/png', 'svg': 'image/svg+xml'}
                content_blocks.append({
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': media_map.get(ext, 'image/png'),
                        'data': base64.standard_b64encode(data).decode('utf-8'),
                    },
                })
        except Exception:
            continue

    if not content_blocks:
        return Response({'error': 'No hi ha fitxers per analitzar'}, status=400)

    prompt = (
        f"Ets un expert tècnic en patronatge i especificació de peces de moda.\n\n"
        f"MODEL: {model.codi_intern} — {model.nom_prenda or ''}\n"
        f"TARGET: {model.target or ''} | CONSTRUCCIÓ: {model.construction or ''} | "
        f"FIT: {model.fit_type or ''}\n"
        f"TALLA BASE: {model.base_size_label or ''} | RUN: {model.size_run_model or ''}\n\n"
        f"MESURES DE LA TALLA BASE:\n{mesures_text or 'No hi ha mesures registrades.'}\n\n"
        "Analitza els fitxers adjunts i detecta discrepàncies. Retorna ÚNICAMENT aquest JSON:\n"
        "{\n"
        '  "alertes": [\n'
        "    {\n"
        '      "tipus": "DISCREPANCIA_TEIXIT|DISCREPANCIA_MESURA|DISCREPANCIA_ESCALAT|AVÍS_SKETCH|ALTRE",\n'
        '      "gravetat": "CRITICA|IMPORTANT|INFORMATIVA",\n'
        '      "descripcio": "descripció clara del problema",\n'
        '      "pom_afectat": "codi POM o null",\n'
        '      "valor_taula": "valor a la taula o null",\n'
        '      "valor_patro": "valor al patró o null",\n'
        '      "accio_suggerida": "què hauria de fer el tècnic"\n'
        "    }\n"
        "  ],\n"
        '  "resum": "resum breu de l\'anàlisi",\n'
        f'  "fitxers_analitzats": {len(fitxers_analisi)}\n'
        "}"
    )

    content_blocks.append({'type': 'text', 'text': prompt})

    try:
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-opus-4-5',
            max_tokens=4096,
            messages=[{'role': 'user', 'content': content_blocks}],
            extra_headers={'anthropic-beta': 'pdfs-2024-09-25'},
        )
        text = response.content[0].text
        text = text.replace('```json', '').replace('```', '').strip()
        result = json.loads(text)
        return Response({
            'model_id': model_id,
            'analisi': result,
            'fitxers_analitzats': len(fitxers_analisi),
        })
    except json.JSONDecodeError as e:
        return Response({'error': f'Resposta IA no parsejable: {e}'}, status=500)
    except Exception as e:
        return Response({'error': f'Error IA: {e}'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def measurements_chat_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    message = (request.data.get('missatge') or '').strip()
    history = request.data.get('historial', []) or []

    if not message:
        return Response({'error': 'missatge és obligatori'}, status=400)

    from fhort.pom.models import POMMaster

    base_measurements = BaseMeasurement.objects.filter(
        model=model, is_active=True
    ).select_related('pom').order_by('ordre')

    mesures_context = "\n".join([
        f"ID:{bm.id} | CODI:{bm.pom.codi_client} | "
        f"NOM:{bm.pom.nom_client or bm.pom.codi_client} | VALOR:{bm.base_value_cm}cm"
        for bm in base_measurements
    ])

    system_prompt = (
        f"Ets un assistent tècnic de patronatge per al model {model.codi_intern}.\n"
        "Pots fer canvis REALS a les mesures. Quan l'usuari demani un canvi, retorna un JSON d'acció.\n\n"
        f"MESURES ACTUALS:\n{mesures_context}\n\n"
        "Respon SEMPRE amb aquest format JSON:\n"
        "{\n"
        '  "resposta": "text de resposta a l\'usuari en català",\n'
        '  "accions": [\n'
        '    {\n'
        '      "tipus": "ACTUALITZAR|AFEGIR|ELIMINAR|CAP",\n'
        '      "bm_id": <id del BaseMeasurement o null si és nou>,\n'
        '      "pom_codi": "codi del POM",\n'
        '      "valor": <float o null>,\n'
        '      "nom_fitxa": "nomenclatura nova o null"\n'
        '    }\n'
        '  ]\n'
        "}\n\n"
        "Regles:\n"
        "- Si l'usuari corregeix un valor, usa tipus ACTUALITZAR amb el bm_id corresponent\n"
        "- Si demana afegir un POM nou, usa tipus AFEGIR (bm_id=null)\n"
        "- Si demana eliminar, usa tipus ELIMINAR\n"
        "- Si és una pregunta sense acció, usa tipus CAP i accions=[]\n"
        "- Sempre confirma l'acció a la resposta en català"
    )

    import anthropic
    import json
    from django.conf import settings

    messages = history + [{'role': 'user', 'content': message}]

    try:
        client = anthropic.Anthropic(api_key=getattr(settings, 'ANTHROPIC_API_KEY', None))
        response = client.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )
        text = response.content[0].text
        from fhort.models_app.extraction_utils import safe_json_parse
        result = safe_json_parse(text)   # tolerant: fences, prosa, comes finals…

        accions_executades = []
        for accio in result.get('accions', []):
            tipus = accio.get('tipus')
            try:
                if tipus == 'ACTUALITZAR' and accio.get('bm_id'):
                    bm = BaseMeasurement.objects.get(id=accio['bm_id'], model=model)
                    if accio.get('valor') is not None:
                        bm.base_value_cm = float(accio['valor'])
                    if accio.get('nom_fitxa') is not None:
                        bm.nom_fitxa = accio['nom_fitxa']
                    bm.save()
                    accions_executades.append(
                        f"Actualitzat {bm.pom.codi_client} = {bm.base_value_cm}cm"
                    )
                elif tipus == 'AFEGIR' and accio.get('pom_codi'):
                    pom = POMMaster.objects.filter(
                        codi_client__iexact=accio['pom_codi']
                    ).first()
                    if pom and accio.get('valor') is not None:
                        bm, created = BaseMeasurement.objects.update_or_create(
                            model=model, pom=pom,
                            defaults={
                                'base_value_cm': float(accio['valor']),
                                'origen': 'MANUAL',
                                'ordre': base_measurements.count(),
                                # Sprint 5B.1: copy tolerance from the catalogue POM.
                                'tolerancia_minus': pom.tolerancia_default_minus,
                                'tolerancia_plus': pom.tolerancia_default_plus,
                            },
                        )
                        accions_executades.append(
                            f"{'Afegit' if created else 'Actualitzat'} {pom.codi_client}"
                        )
                elif tipus == 'ELIMINAR' and accio.get('bm_id'):
                    bm = BaseMeasurement.objects.get(id=accio['bm_id'], model=model)
                    nom = bm.pom.codi_client
                    bm.is_active = False
                    bm.save()
                    accions_executades.append(f"Eliminat {nom}")
            except Exception as e:
                accions_executades.append(f"Error: {e}")

        mesures_actualitzades = list(
            BaseMeasurement.objects.filter(model=model, is_active=True)
            .select_related('pom').order_by('ordre')
            .values('id', 'pom__codi_client', 'base_value_cm', 'nom_fitxa', 'ordre')
        )

        return Response({
            'resposta': result.get('resposta', ''),
            'accions_executades': accions_executades,
            'mesures_actualitzades': mesures_actualitzades,
            'historial_nou': messages + [{'role': 'assistant', 'content': text}],
        })
    except (ValueError, json.JSONDecodeError) as e:
        return Response({'error': f'Error parsing IA: {e}'}, status=500)
    except Exception as e:
        return Response({'error': f'Error: {e}'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_grading_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    # G6-A/T2 (forat que va quedar obert): el gate del MOTOR ja pregunta "té regles?" —residents o
    # de set—, però aquest CALLER encara preguntava pel PUNTER pel seu compte. Efecte: el model 163
    # (25 regles residents, `grading_rule_set` NULL) graduava si cridaves el servei, i rebia un 400
    # si ho demanaves per l'endpoint. El predicat és un i és `_te_regles`.
    if not _te_regles(model):
        return Response({'error': 'El model no té regles de grading (ni residents ni de rule set)'},
                        status=400)
    if not model.size_run_model or not model.base_size_label:
        return Response({'error': 'Cal configurar talles i talla base'}, status=400)

    from fhort.fitting.models import SizeFitting, GradedSpec
    from fhort.pom.services import generate_graded_specs

    base_measurements_qs = BaseMeasurement.objects.filter(model=model, is_active=True)
    if not base_measurements_qs.exists():
        return Response({'error': 'No hi ha mesures base'}, status=400)

    # Get or create SizeFitting with the real required fields
    sf = SizeFitting.objects.filter(model=model).first()
    if not sf:
        next_num = 1
        codi = f"{model.codi_intern}-SF-{next_num}"
        while SizeFitting.objects.filter(codi=codi).exists():
            next_num += 1
            codi = f"{model.codi_intern}-SF-{next_num}"
        profile = getattr(request.user, 'profile', None)
        try:
            sf = SizeFitting.objects.create(
                model=model,
                numero=next_num,
                codi=codi,
                tipus='SizeSet',
                creat_per=profile,
            )
        except Exception as e:
            return Response({'error': f'Error creant SizeFitting: {e}'}, status=500)

    new_version = bool(request.data.get('new_version', False))
    allow_reopen_sealed = bool(request.data.get('allow_reopen_sealed', False))
    n_consolidat = 0  # B3: POMs de talla base consolidats des de fittings oberts abans de propagar

    # Crida el motor. new_version=True → acte conscient de PROPAGAR (Peça 2): crea v+1 via el
    # helper bump_grading_version_and_generate (base_changed=False: propagar NO toca la base, no
    # incrementa measurements_version). Sobre una versió SEGELLADA (aprovada) sense autorització
    # → 409 conscient perquè el frontend demani la doble confirmació. new_version=False →
    # comportament clàssic (reutilitza la versió vigent): NO es toca per als usos vells.
    if new_version:
        from fhort.fitting.models import GradingVersion
        from fhort.pom.services import bump_grading_version_and_generate
        sealed_active = (GradingVersion.objects
                         .filter(size_fitting=sf, is_active=True, aprovada=True)
                         .order_by('-version_number').first())
        if sealed_active is not None and not allow_reopen_sealed:
            return Response({
                'error': 'sealed',
                'version_number': sealed_active.version_number,
                'message': (f'La versió vigent v{sealed_active.version_number} està segellada '
                            f'(aprovada a producció); cal confirmació explícita per superar-la.'),
            }, status=409)
        profile = getattr(request.user, 'profile', None)
        # LLENÇ NET (LLEI): propagar inicia una FASE NOVA des de base+regla, esborrant els ajustos per
        # cel·la (ModelGradingOverride) de la propagació anterior; el motor (helper) regenera de zero.
        # NO és un eix de versions per comparar: el botó ja ha advertit (2 passos) abans d'arribar aquí.
        from fhort.models_app.models import ModelGradingOverride
        ModelGradingOverride.objects.filter(model=model).delete()
        # B3 (decisió b1): abans que el motor llegeixi la base, consolida la realitat mesurada
        # que viu en fittings OBERTS (línies de talla base amb valor_real rectificat) a
        # BaseMeasurement.base_value_cm → es propaga sobre l'última mesura vàlida, no sobre la
        # base original. NO toca el motor (pom/services.py); només actualitza la base abans.
        from fhort.fitting.models import PieceFitting
        from fhort.fitting.services import consolidate_base_from_fitting
        _open_pfs = (PieceFitting.objects
                     .filter(model=model, session__estat='Oberta')
                     .select_related('model', 'grading_version', 'grading_version__size_fitting'))
        for _pf in _open_pfs:
            n_consolidat += len(consolidate_base_from_fitting(_pf, auth_user=request.user))
        try:
            new_v = bump_grading_version_and_generate(
                sf.id,
                base_changed=False,
                profile_id=(profile.id if profile else None),
                allow_reopen_sealed=allow_reopen_sealed,
                nom='Propagació conscient',
                reopen_context='Propagació conscient',
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': f'Error generant grading: {e}'}, status=500)
        graded_count = GradedSpec.objects.filter(grading_version=new_v).count()
        # Watchpoint informatiu de traça quan s'ha superat una versió segellada (NO bloca).
        if sealed_active is not None and allow_reopen_sealed:
            from fhort.tasks.models import ModelTask
            grading_task = (ModelTask.objects
                            .filter(model=model, task_type__code='grading')
                            .order_by('-id').first())
            Watchpoint.objects.create(
                model=model,
                task=grading_task,
                text=(f'Versió segellada v{sealed_active.version_number} superada per '
                      f'{str(profile) if profile else "usuari desconegut"} '
                      f'propagant a v{new_v.version_number}.'),
                estat='open',
                created_by=profile,
            )
    else:
        try:
            graded_count = generate_graded_specs(sf.id)
        except SealedGradingVersionError as e:
            # G6-B/T1 · camí 1/6. Regenerar in-place sobre una versió segellada: refusat. La
            # sortida és el `new_version=True` d'aquest mateix endpoint (el bump), no forçar.
            return Response(e.payload, status=409)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': f'Error generant grading: {e}'}, status=500)

    # Build a measurements-table-style response
    size_run = [s.strip() for s in model.size_run_model.split('·') if s.strip()]
    # Versió vigent: mateix criteri únic que els lectors graded-table/taula-mesures.
    from fhort.fitting.services import vigent_grading_version
    gv = vigent_grading_version(sf)

    rows = []
    for bm in (
        BaseMeasurement.objects.filter(model=model, is_active=True)
        .select_related('pom', 'pom__pom_global').order_by('ordre')
    ):
        pom = bm.pom
        pg = getattr(pom, 'pom_global', None)
        graded = {}
        if gv:
            for spec in GradedSpec.objects.filter(grading_version=gv, pom=pom):
                graded[spec.size_label] = (
                    float(spec.graded_value_cm) if spec.graded_value_cm is not None else None
                )
        rows.append({
            'id': bm.id,
            'pom_id': pom.id,
            'pom_code': pom.codi_client,
            'nom_fitxa': bm.nom_fitxa or '',
            'nom_ca': pg.nom_ca if pg else pom.nom_client,
            'nom_en': pg.nom_en if pg else pom.nom_client,
            'base_value_cm': float(bm.base_value_cm) if bm.base_value_cm is not None else None,
            'graded': graded,
            'ordre': bm.ordre,
        })

    return Response({
        'model_id': model_id,
        'graded_count': graded_count,
        'size_run': size_run,
        'base_size': model.base_size_label,
        'base_consolidada_des_de_fitting': n_consolidat,  # B3: POMs base consolidats (0 si cap)
        'rows': rows,
    })


class _ExecuteTasksCap(HasCapability):
    required_capability = EXECUTE_TASKS


@api_view(['POST'])
@permission_classes([_ExecuteTasksCap])
def set_size_override_view(request, model_id):
    """POST /api/v1/models/<model_id>/set-size-override/  Body: {pom_id, size_label, valor}

    Edita el valor d'UNA talla NO-base com a ModelGradingOverride (per-model,
    traçable) i RE-PROPAGA el grading (generate_graded_specs) sobre la
    GradingVersion vigent (criteri de PEÇA 0). L'override té precedència màxima
    al motor (override→exception→regla→FIXED), per tant editar una 2a talla
    manté la 1a. NO toca GradedSpec directament (és sortida del motor) ni
    PieceFittingLine. Idempotent per (model, pom, size_label).
    """
    from fhort.models_app.models import ModelGradingOverride, MeasurementChangeLog
    from fhort.pom.models import POMMaster
    from fhort.pom.services import generate_graded_specs
    from fhort.fitting.services import _resolve_working_size_fitting, vigent_grading_version
    from fhort.fitting.models import GradedSpec

    # 1. Model
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    # 2. Payload
    data = request.data or {}
    pom_id = data.get('pom_id')
    size_label = (data.get('size_label') or '').strip()
    valor = data.get('valor')
    if pom_id is None or not size_label or valor is None:
        return Response({'error': 'Calen pom_id, size_label i valor.'}, status=400)
    try:
        valor = round(float(valor), 2)
    except (TypeError, ValueError):
        return Response({'error': 'valor ha de ser numèric.'}, status=400)

    # 3. La talla base s'edita com a mesura base (BaseMeasurement), no com a override.
    base_size = (model.base_size_label or '').strip()
    if not base_size:
        return Response({'error': 'El model no té talla base definida.'}, status=400)
    if size_label == base_size:
        return Response(
            {'error': "La talla base s'edita com a mesura base, no com a override de talla."},
            status=400,
        )

    # 4. La talla ha de ser al size run del model.
    size_run = [s.strip() for s in (model.size_run_model or '').replace(';', '·').split('·') if s.strip()]
    if size_label not in size_run:
        return Response({'error': f"La talla '{size_label}' no és al size run del model."}, status=400)

    # 5. POM
    try:
        pom = POMMaster.objects.get(id=pom_id)
    except POMMaster.DoesNotExist:
        return Response({'error': 'POM no trobat.'}, status=404)

    profile = getattr(request.user, 'profile', None)

    with transaction.atomic():
        # 6. Override upsert idempotent (origen MODEL, no sessió → fitting_ref=None). Aquest és
        #    l'ÚNIC camí que escriu ModelGradingOverride per talla des de PEÇA 4 (la sessió de
        #    fitting ja no n'escriu; vegeu close_piece_fitting).
        prev = (ModelGradingOverride.objects
                .filter(model=model, pom=pom, size_label=size_label)
                .values_list('value_cm', flat=True).first())
        ModelGradingOverride.objects.update_or_create(
            model=model, pom=pom, size_label=size_label,
            defaults={
                'value_cm': valor,
                'motiu': 'Edició manual de talla (taula propagada)',
                'fitting_ref': None,
                'created_by': profile,
            },
        )

        # 7. Rastre F1: talla editada = esdeveniment. El signal post_save NOMÉS cobreix
        #    BaseMeasurement; per a una talla no-base el registrem explícitament aquí.
        if prev is None or abs(float(prev) - valor) > 1e-9:
            MeasurementChangeLog.objects.create(
                model=model, pom=pom, base_measurement=None,
                valor_anterior=(float(prev) if prev is not None else None),
                valor_nou=valor,
                context='manual',
                motiu=f'Override talla {size_label}',
                created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
            )

        # 8. Re-propaga sobre la GradingVersion vigent (l'override mana al motor).
        sf = _resolve_working_size_fitting(model)
        if sf is None:
            return Response(
                {'error': 'El model no té SizeFitting; genera el grading abans d\'editar talles.'},
                status=400,
            )
        try:
            generate_graded_specs(sf.id)
        except SealedGradingVersionError as e:
            # G6-B/T1 · camí 2/6. `set_rollback` NO és decoratiu: som DINS del `transaction.atomic`
            # que acaba d'escriure el ModelGradingOverride, i un `return` des de dins d'un bloc
            # atòmic **fa commit** (no propaga cap excepció). Sense això, el 409 deixaria l'override
            # desat alimentant una versió segellada — exactament el que aquest guard ha d'impedir.
            transaction.set_rollback(True)
            return Response(e.payload, status=409)
        except ValueError as e:
            transaction.set_rollback(True)
            return Response({'error': str(e)}, status=400)

    # 9. Retorna el GradedSpec resultant de la talla editada (reflecteix l'override).
    gv = vigent_grading_version(sf)
    graded = (GradedSpec.objects
              .filter(grading_version=gv, pom=pom, size_label=size_label)
              .values_list('graded_value_cm', flat=True).first()) if gv else None
    return Response({
        'ok': True,
        'model_id': model.id,
        'pom_id': pom.id,
        'size_label': size_label,
        'override_value_cm': valor,
        'grading_version_id': gv.id if gv else None,
        'graded_value_cm': float(graded) if graded is not None else None,
    }, status=200)


@api_view(['POST'])
@permission_classes([_ExecuteTasksCap])
def escalat_ajustar_talla_view(request, model_id):
    """POST /api/v1/models/<model_id>/escalat/ajustar-talla/  Body: {pom_id, talla, valor}

    Convergència amb el fitting (piece-fitting-lines/propagar): ancora la talla editada i PROPAGA
    EL DELTA per regla a les germanes, com fa el fitting amb propaga_ancoratges. A nivell de MODEL
    no hi ha PieceFittingLine; el magatzem que sobreviu la re-derivació amb la regla intacta és la
    BASE (BaseMeasurement): propaga_ancoratges desplaça tota la corba mantenint els deltes de la
    regla, per tant n'hi ha prou d'escriure la nova base i re-derivar (generate_graded_specs).

      · LINEAR/canònic, talla no-base → propaga_ancoratges → nova base → BaseMeasurement → re-deriva.
      · talla BASE (editable, el fitting no la bloqueja) → escriu BaseMeasurement directament.
      · STEP/FIXED/ZERO o sense regla → NO propaga (com el fitting): override puntual de la cel·la.

    Re-deriva amb el motor PUR existent (generate_graded_specs); NO duplica lògica de grading ni
    crea versió nova (l'acte conscient de versionar és Propagar, generate_grading_view). Retorna
    'linies' [{id, valor_real}] per refrescar la fila sencera (mirall de /propagar).
    """
    from fhort.models_app.models import ModelGradingOverride, MeasurementChangeLog
    from fhort.pom.models import POMMaster
    from fhort.pom.services import generate_graded_specs, _load_grading_rules, escala_del_model
    from fhort.pom.grading_utils import propaga_ancoratges
    from fhort.fitting.services import _resolve_working_size_fitting, vigent_grading_version
    from fhort.fitting.models import GradedSpec

    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    data = request.data or {}
    pom_id = data.get('pom_id')
    talla = (data.get('talla') or '').strip()
    valor = data.get('valor')
    if pom_id is None or not talla:
        return Response({'error': 'Calen pom_id i talla.'}, status=400)

    base_size = (model.base_size_label or '').strip()
    if not base_size:
        return Response({'error': 'El model no té talla base definida.'}, status=400)
    size_run = [s.strip() for s in (model.size_run_model or '').replace(';', '·').split('·') if s.strip()]
    if talla not in size_run:
        return Response({'error': f"La talla '{talla}' no és al size run del model."}, status=400)
    try:
        pom = POMMaster.objects.get(id=pom_id)
    except POMMaster.DoesNotExist:
        return Response({'error': 'POM no trobat.'}, status=404)

    sf = _resolve_working_size_fitting(model)
    if sf is None:
        return Response(
            {'error': "El model no té SizeFitting; genera el grading abans d'escalar."}, status=400)

    profile = getattr(request.user, 'profile', None)
    auth_user = request.user if getattr(request.user, 'is_authenticated', False) else None

    # Valor buit → cap escriptura (mirall del fitting: ancoratge None no propaga). Retorna l'estat actual.
    if valor in (None, ''):
        propagat, motiu = False, 'sense_ancoratge'
    else:
        try:
            valor = round(float(valor), 2)
        except (TypeError, ValueError):
            return Response({'error': 'valor ha de ser numèric.'}, status=400)

        rule = _load_grading_rules(model).get(pom.id)
        logica = getattr(rule, 'logica', None) if rule else None
        canonic = getattr(rule, 'increment_base', None) is not None if rule else False
        # LINEAR/canònic → propaga per regla (com el fitting, que sobreescriu TOTES les germanes);
        # STEP/FIXED/ZERO o sense regla → NO propaga (només la cel·la editada).
        propaga = rule is not None and (logica != 'STEP') and (canonic or logica == 'LINEAR')

        with transaction.atomic():
            if propaga:
                # Nova base de la corba ancorada a l'edició (per a la base, l'ancoratge ÉS la base).
                # Geometria del MOTOR (`escala_del_model`): el relleu el manen el run del
                # SISTEMA i la talla BASE (llei S24b + FIX-1). Amb el run del model, un forat
                # col·lapsava el pas i el break queia on no toca — d'aquí que reescriure el
                # valor vigent d'una cel·la moqués la base (DIAGNOSI_MESURES_TEA_205, B1).
                nova_base = valor
                if talla != base_size:
                    try:
                        _run_model, run_sistema, _pos, _bidx = escala_del_model(model)
                    except ValueError as e:
                        return Response({'error': str(e)}, status=400)
                    nova_base = propaga_ancoratges(
                        rule, talla, valor, size_run,
                        run_sistema=run_sistema, base_label=base_size).get(base_size)
                if nova_base is None:
                    return Response({'error': "No s'ha pogut derivar la base des de la talla ancorada."}, status=400)
                _write_base(model, pom, round(float(nova_base), 2), auth_user,
                            f'Escalat · ajust talla {talla} (propaga per regla)')
                # La corba de la regla mana: neteja els pins per cel·la del POM (el fitting sobreescriu
                # els valor_real de les germanes; aquí l'equivalent és treure els overrides residuals).
                ModelGradingOverride.objects.filter(model=model, pom=pom).delete()
                propagat, motiu = True, (logica or 'CANONIC')
            elif talla == base_size:
                # Base sense règim LINEAR: desa la base; germanes intactes (mirall del fitting STEP).
                _write_base(model, pom, valor, auth_user, f'Escalat · base {talla}')
                propagat, motiu = False, (logica or 'BASE')
            else:
                # STEP/FIXED/ZERO o sense regla → override puntual (germanes intactes, com el fitting).
                prev = (ModelGradingOverride.objects
                        .filter(model=model, pom=pom, size_label=talla)
                        .values_list('value_cm', flat=True).first())
                ModelGradingOverride.objects.update_or_create(
                    model=model, pom=pom, size_label=talla,
                    defaults={'value_cm': valor, 'motiu': 'Escalat · ajust talla (sense propagació)',
                              'fitting_ref': None, 'created_by': profile},
                )
                if prev is None or abs(float(prev) - valor) > 1e-9:
                    MeasurementChangeLog.objects.create(
                        model=model, pom=pom, base_measurement=None,
                        valor_anterior=(float(prev) if prev is not None else None), valor_nou=valor,
                        context='manual', motiu=f'Escalat talla {talla}', created_by=auth_user)
                propagat, motiu = False, (logica or 'sense_regla')

            try:
                generate_graded_specs(sf.id)
            except SealedGradingVersionError as e:
                # G6-B/T1 · camí 3/6. Igual que el 2: dins de l'atòmic que ha escrit l'override
                # (i el MeasurementChangeLog). Rollback explícit o el 409 mentiria.
                transaction.set_rollback(True)
                return Response(e.payload, status=409)
            except ValueError as e:
                transaction.set_rollback(True)
                return Response({'error': str(e)}, status=400)

    # Files actualitzades del POM (mirall de 'linies' de /propagar): {id, valor_real} per talla.
    gv = vigent_grading_version(sf)
    graded = {}
    if gv:
        for spec in GradedSpec.objects.filter(grading_version=gv, pom=pom):
            graded[spec.size_label] = (
                float(spec.graded_value_cm) if spec.graded_value_cm is not None else None)
    linies = [{'id': f'{pom.id}:{s}', 'valor_real': graded.get(s)} for s in size_run]
    return Response({'ok': True, 'propagat': propagat, 'motiu': motiu,
                     'grading_version_id': gv.id if gv else None, 'linies': linies}, status=200)


def _write_base(model, pom, valor, auth_user, motiu):
    """Escriu BaseMeasurement(model, pom).base_value_cm i deixa que el signal F1 registri el canvi."""
    from fhort.models_app.models import BaseMeasurement
    bm, _created = BaseMeasurement.objects.get_or_create(
        model=model, pom=pom, defaults={'base_value_cm': valor, 'origen': 'STANDARD'})
    bm.base_value_cm = valor
    bm._changed_by = auth_user
    bm._motiu = motiu
    bm.save()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grading_status_view(request, model_id):
    """GET /api/v1/models/<model_id>/grading-status/  (read-only)

    Perquè el botó "Propagar a grading" MIRI ABANS d'executar (avís de 2 passos): retorna si ja hi
    ha una propagació vigent (que es SUBSTITUIRÀ sobre llenç net) i si està segellada (producció).
    """
    from fhort.fitting.models import GradedSpec
    from fhort.fitting.services import _resolve_working_size_fitting, vigent_grading_version

    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    sf = _resolve_working_size_fitting(model)
    gv = vigent_grading_version(sf) if sf else None
    te_dades = bool(gv and GradedSpec.objects.filter(grading_version=gv).exists())
    # G6-B2: si la versió vigent està SEGELLADA, aquí es diu també si encara diu la veritat. És la
    # superfície on es decideix propagar, i propagar sobre un segell que ja ha quedat enrere no és
    # el mateix acte que propagar sobre un de fresc — qui ho decideix ho ha de saber abans, no
    # després.
    from fhort.fitting.staleness import com_a_dict, estalitud
    return Response({
        'te_dades_propagades': te_dades,
        'segellada': bool(gv and gv.aprovada),
        'version_number': gv.version_number if gv else None,
        'estalitud': com_a_dict(estalitud(gv)) if gv else None,
    })


@api_view(['POST'])
@permission_classes([_ExecuteTasksCap])
def base_measurements_reorder_view(request, model_id):
    """POST /api/v1/models/<model_id>/base-measurements/reorder/  Body: {ids: [bm_id, ...] ordenats}

    Desa BaseMeasurement.ordre = posició a la llista (ordre ÚNIC i global del model). Totes les taules
    llegeixen order_by('ordre') → reordenar a Mesures es materialitza a Grading EN PROPAGAR (la fase
    nova sobre llenç net hereta l'ordre vigent). Reescriptura en bloc, atòmica, sense col·lisions.
    """
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)
    ids = request.data.get('ids')
    if not isinstance(ids, list) or not ids:
        return Response({'error': 'Cal una llista ids ordenada.'}, status=400)
    bms = {bm.id: bm for bm in BaseMeasurement.objects.filter(model=model, id__in=ids)}
    with transaction.atomic():
        for pos, bid in enumerate(ids):
            bm = bms.get(bid)
            if bm is not None and bm.ordre != pos:
                bm.ordre = pos
                bm.save(update_fields=['ordre'])
    return Response({'ok': True, 'n': len(bms)})


# Sprint NOMS-POM (2026-07-30) — límit dur dels dos textos, el mateix que declara el model
# (`BaseMeasurement.nom_canonic_model` / `nom_traduit_model`, CharField(160)). Es valida aquí
# perquè un text massa llarg ha de tornar un 400 explicat, no una excepció de BD.
NOMS_POM_MAX = 160
NOMS_POM_CAMPS = ('nom_canonic_model', 'nom_traduit_model')


@api_view(['PATCH'])
@permission_classes([_ExecuteTasksCap])
def base_measurement_noms_view(request, bm_id):
    """PATCH /api/v1/base-measurements/<bm_id>/noms/  Body: {nom_canonic_model?, nom_traduit_model?}

    EL BATEIG DEL MODEL: els dos textos amb què aquest model anomena la mesura (nom canònic EN
    + traducció del client). Buit ('') NO és un valor: és tornar la fila al catàleg.

    Endpoint PROPI i petit, no el serializer genèric de `BaseMeasurementViewSet`: aquell obre
    tota la fila (valor base, origen, is_active, toleràncies…) i aquí només s'hi ha de poder
    tocar la PRESENTACIÓ. Un camp qualsevol que hi entri de passada seria una mesura canviada
    sense que ningú ho hagi demanat. Els camps que no arriben al body no es toquen.

    Permís: `EXECUTE_TASKS` (`_ExecuteTasksCap`) — la MATEIXA capability que ja governa l'edició
    de les mesures del model en aquesta superfície (`set_size_override_view` i
    `base_measurements_reorder_view`, just aquí a sobre). Qui pot escriure el valor d'una mesura
    del model pot anomenar-la; no s'inventa cap porta nova per a un camp de text.

    REGISTRE: NO passa pel `MeasurementChangeLog` (F1), i és deliberat. Aquell log és la memòria
    de les MESURES —el que va valer cada POM i quan—, i el llegeixen com a tal la taula
    d'estadis (`base_stages_view`) i el Repàs: hi entra una fila i el model diria que algú ha
    tornat a prendre la mesura. Rebatejar no és mesurar. `updated_at` (auto_now) ja diu quan
    s'ha tocat, i el catàleg segueix sent recuperable en un sol gest (esborrar el text).
    El signal de F1 tampoc no s'hi dispara sol: només registra canvis de `base_value_cm`.

    El CATÀLEG no es toca mai des d'aquí (ni `POMGlobal` ni `POMMaster`): el bateig és d'aquest
    model i no pot reescriure com anomenen la mesura els altres models de la casa.
    """
    try:
        bm = BaseMeasurement.objects.get(id=bm_id)
    except BaseMeasurement.DoesNotExist:
        return Response({'error': 'Mesura no trobada'}, status=404)

    canvis = {}
    for camp in NOMS_POM_CAMPS:
        if camp not in request.data:
            continue
        valor = request.data.get(camp)
        # `null` i `''` volen dir el mateix: treure el bateig i tornar al catàleg.
        valor = '' if valor is None else str(valor).strip()
        if len(valor) > NOMS_POM_MAX:
            return Response(
                {'error': f'«{camp}» no pot passar de {NOMS_POM_MAX} caràcters.'}, status=400)
        canvis[camp] = valor

    if not canvis:
        return Response(
            {'error': 'Cal com a mínim un de: ' + ', '.join(NOMS_POM_CAMPS) + '.'}, status=400)

    for camp, valor in canvis.items():
        setattr(bm, camp, valor)
    bm.save(update_fields=[*canvis.keys(), 'updated_at'])

    return Response({
        'id': bm.id,
        'nom_canonic_model': bm.nom_canonic_model,
        'nom_traduit_model': bm.nom_traduit_model,
        'updated_at': bm.updated_at.isoformat(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def base_stages_view(request, model_id):
    """Taula base amb ESTADIS (talla base): columnes teòriques que CREIXEN, una per presa
    que ha escrit base (de l'històric MeasurementChangeLog), + tolerància + base vigent.

    Read-only i NOMÉS de la talla base — no toca la taula propagada (grading). Cada estadi
    és un snapshot per carry-forward dels valors base fins aquell moment; l'últim estadi
    coincideix amb la base vigent (BaseMeasurement).
    """
    from fhort.models_app.models import MeasurementChangeLog
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    bms = list(BaseMeasurement.objects.filter(model=model, is_active=True)
               .select_related('pom', 'pom__pom_global').order_by('ordre', 'pom__codi_client'))

    def _tol(bm):
        pom = bm.pom
        tm = bm.tolerancia_minus if bm.tolerancia_minus is not None else getattr(pom, 'tolerancia_default_minus', None)
        tp = bm.tolerancia_plus if bm.tolerancia_plus is not None else getattr(pom, 'tolerancia_default_plus', None)
        return (float(tm) if tm is not None else 0.6, float(tp) if tp is not None else 0.6)

    # Estadis = events de MeasurementChangeLog agrupats per (context, segon), en ordre d'aparició.
    #
    # NOMÉS PRESES DE LA TALLA BASE (FIX-2, DIAGNOSI_MESURES_TEA_205 · fila B del 205).
    # `MeasurementChangeLog` també registra els OVERRIDES de talla no-base (l'edició d'una
    # cel·la d'Escalat i el `set_size_override`), i aquests s'escriuen amb `base_measurement`
    # a NULL — és el senyal que distingeix «he tocat la base» de «he pinçat una talla».
    # Sense el filtre entraven a la taula com si fossin preses de base i, com que els estadis
    # són SNAPSHOTS per carry-forward, un override arrossegava el seu valor cap endavant per
    # tota la fila: al 205, el POM B (base 46) es veia caure a 1 perquè algú havia escrit 1
    # a les cel·les XXS i XS. La taula deia una base que la fitxa no ha tingut mai.
    #
    # Els logs NO es toquen (són auditoria): el que canvia és qui té dret a pintar-hi columna.
    logs = (MeasurementChangeLog.objects
            .filter(model=model, base_measurement__isnull=False)
            .select_related('pom').order_by('created_at', 'id'))
    events, ev_index, changes_by_ev = [], {}, {}
    for c in logs:
        if c.valor_nou is None:
            continue
        bucket = c.created_at.replace(microsecond=0).isoformat()
        key = f'{c.context}@{bucket}'
        if key not in ev_index:
            ev_index[key] = len(events)
            events.append({'key': key, 'context': c.context, 'at': c.created_at.isoformat()})
            changes_by_ev[key] = {}
        changes_by_ev[key][c.pom_id] = float(c.valor_nou)

    # Snapshots acumulats (carry-forward) per estadi.
    snapshot, stages, stage_snaps = {}, [], []
    for ev in events:
        snapshot.update(changes_by_ev[ev['key']])
        stages.append(ev)
        stage_snaps.append(dict(snapshot))

    # FaseD — descarta els estadis (columnes de presa) sense CAP valor displayable per a les files
    # mostrades (p.ex. events de POMs després desactivats): no es pinten columnes buides.
    displayed = {bm.pom_id for bm in bms}
    keep = [i for i in range(len(stages))
            if any(stage_snaps[i].get(pid) is not None for pid in displayed)]
    stages = [stages[i] for i in keep]
    stage_snaps = [stage_snaps[i] for i in keep]

    rows = []
    for bm in bms:
        pom = bm.pom
        pg = getattr(pom, 'pom_global', None)
        tm, tp = _tol(bm)
        takes = {}
        for i, st in enumerate(stages):
            v = stage_snaps[i].get(pom.id)
            if v is not None:
                takes[st['key']] = v
        rows.append({
            'pom_id': pom.id,
            'pom_code': pom.codi_client,
            'nom_fitxa': bm.nom_fitxa or '',
            'nom_ca': pg.nom_ca if pg else pom.nom_client,
            'nom_en': pg.nom_en if pg else pom.nom_client,
            # Sprint NOMS-POM (30/07) — el BATEIG d'aquest model, CRU i al costat del catàleg
            # (`nom_ca`/`nom_en`, que no es toquen): '' vol dir «no batejat, mana el catàleg».
            # La cascada la resol qui pinta, que és qui sap si mostra un input amb placeholder
            # o un text pla. Camps NOUS: cap camp existent canvia de valor ni de nom.
            'nom_canonic_model': bm.nom_canonic_model or '',
            'nom_traduit_model': bm.nom_traduit_model or '',
            'is_key': bm.is_key,
            'tol_minus': tm,
            'tol_plus': tp,
            'base_value_cm': float(bm.base_value_cm) if bm.base_value_cm is not None else None,
            'base_measurement_id': bm.id,
            'takes': takes,
        })

    return Response({
        'base_size': model.base_size_label,
        'stages': stages,
        'rows': rows,
    })


ISO_SHRINKAGE_TABLE = [
    {'id': 'woven_cotton',    'nom': 'Woven Cotton',    'warp': 3.0, 'weft': 3.0},
    {'id': 'woven_linen',     'nom': 'Woven Linen',     'warp': 3.0, 'weft': 3.0},
    {'id': 'woven_viscose',   'nom': 'Woven Viscose',   'warp': 4.0, 'weft': 4.0},
    {'id': 'woven_silk',      'nom': 'Woven Silk',      'warp': 2.0, 'weft': 2.0},
    {'id': 'woven_polyester', 'nom': 'Woven Polyester', 'warp': 1.0, 'weft': 1.0},
    {'id': 'knit_cotton',     'nom': 'Knit Cotton',     'warp': 5.0, 'weft': 5.0},
    {'id': 'knit_jersey',     'nom': 'Knit Jersey',     'warp': 5.0, 'weft': 5.0},
    {'id': 'stretch_knit',    'nom': 'Stretch Knit',    'warp': 8.0, 'weft': 8.0},
    {'id': 'knit_wool',       'nom': 'Knit Wool',       'warp': 6.0, 'weft': 6.0},
    {'id': 'denim',           'nom': 'Denim',           'warp': 5.0, 'weft': 3.0},
    {'id': 'technical',       'nom': 'Technical',       'warp': 0.0, 'weft': 0.0},
]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def iso_shrinkage_view(request):
    return Response(ISO_SHRINKAGE_TABLE)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_fabric_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    fields = ['fabric_main', 'fabric_composition', 'shrinkage_type',
              'shrinkage_warp', 'shrinkage_weft', 'shrinkage_pct', 'fabric_notes',
              'shrinkage_iso_key']
    for f in fields:
        if f in request.data:
            setattr(model, f, request.data[f])
    model.save()
    return Response({'id': model.id, 'fabric_main': model.fabric_main})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consumption_delivery_view(request, model_id):
    """Sprint 4.3: albarà-repositori VIU d'un model.
    Capçalera immutable (ConsumptionRecord) + cos calculat sobre producció
    (ModelTask/TimerEntrada/TaskTransition). Tot intra-tenant. Agregació en
    Python sobre dades prefetchades → una sola consulta (sense N+1).
    Timers oberts NO es compten (B1-a: només temps consolidat), i els trams desbocats tampoc
    (`tram_compta`: mateixa llei que el Welford i la resta d'agregadors)."""
    from fhort.tasks.services_i import tram_compta
    try:
        model = Model.objects.select_related('consumption_record').prefetch_related(
            'model_tasks__task_type',
            'model_tasks__timers__tecnic',
            'model_tasks__transitions__by',
        ).get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    rec = getattr(model, 'consumption_record', None)
    if rec is None:
        return Response({'merited': False, 'model_id': model.id})

    steps = []
    total_minutes = 0
    rectifications = 0
    per_tech = {}   # tecnic_id -> {'label':..., 'minutes':int}
    history = []

    tasks = sorted(model.model_tasks.all(), key=lambda t: (t.order, t.id))
    for mt in tasks:
        task_minutes = 0
        for tm in mt.timers.all():
            if not tram_compta(tm):      # timer obert (B1-a) o tram desbocat → fora
                continue
            task_minutes += tm.minuts
            total_minutes += tm.minuts
            if tm.tecnic_id is not None:
                label = (tm.tecnic.nom_complet or tm.tecnic.user.get_username()) if tm.tecnic else str(tm.tecnic_id)
                slot = per_tech.setdefault(tm.tecnic_id, {'technician_id': tm.tecnic_id, 'label': label, 'minutes': 0})
                slot['minutes'] += tm.minuts
        steps.append({
            'task_type': mt.task_type.name if mt.task_type_id else None,
            'status': mt.status,
            'minutes': task_minutes,
            'started_at': mt.started_at,
            'finished_at': mt.finished_at,
        })
        for tr in mt.transitions.all():
            if tr.from_status == 'Done' and tr.to_status == 'InProgress':
                rectifications += 1
            by_label = None
            if tr.by_id is not None and tr.by:
                by_label = tr.by.nom_complet or tr.by.user.get_username()
            history.append({
                'task_type': mt.task_type.name if mt.task_type_id else None,
                'from': tr.from_status,
                'to': tr.to_status,
                'by': by_label,
                'at': tr.at,
            })

    history.sort(key=lambda h: (h['at'] is None, h['at']))

    return Response({
        'merited': True,
        'model_id': model.id,
        'header': {
            'code': rec.code_snapshot,
            'name': rec.name_snapshot,
            'period': rec.period,
            'merited_at': rec.merited_at,
            'opaque_ref': str(rec.opaque_ref),
        },
        'steps': steps,
        'totals': {'total_minutes': total_minutes, 'rectifications': rectifications},
        'per_technician': list(per_tech.values()),
        'history': history,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_dashboard_view(request, model_id):
    """Dashboard del model — PEÇA B1 (versió mínima: Q1 + Q4).

    Endpoint compositor read-only que agrega, per a UN model, l'estat de treball
    (Q1: on sóc / què bloqueja / artefactes vigents) i les tasques (Q4: què puc fer).
    NO inclou timeline (Q2), alertes/handoffs (Q3) ni esforç/cost (⑤ M, que ja serveix
    consumption_delivery_view → no es duplica). Tot intra-tenant, cap escriptura a BD.

    Degradació amb gràcia: un model nou (sense tasques/SF/fitxa/base) retorna 200 amb els
    sub-blocs en null/buit/0, MAI un 500. Reusa els resolutors canònics ja existents."""
    from django.shortcuts import get_object_or_404
    from fhort.tasks.services_d import model_ready_for_gate
    from fhort.fitting.services import _resolve_working_size_fitting, _active_grading_version
    from fhort.fitting.models import POMAlert

    model = get_object_or_404(
        Model.objects.prefetch_related('model_tasks__task_type'),
        id=model_id,
    )

    # --- Q1: on sóc / què bloqueja ---
    tasks = sorted(model.model_tasks.all(), key=lambda t: (t.order, t.id))
    tasks_open = sum(1 for t in tasks if t.status != 'Done')

    phases = [c[0] for c in Model.FASE_CHOICES]
    try:
        idx = phases.index(model.fase_actual)
        next_phase = phases[idx + 1] if idx + 1 < len(phases) else None
    except ValueError:
        next_phase = None

    on_soc = {
        'fase': model.fase_actual,
        'estat': model.estat,
        'ready_for_gate': model_ready_for_gate(model.id),
        'next_phase': next_phase,
        'blockers': {'tasks_open': tasks_open},
    }

    # --- Q1: artefactes vigents (cada accés a una relació opcional tolera absència) ---
    ts = getattr(model, 'tech_sheet', None)   # reverse O2O: None si no existeix (igual que consumption_record)
    fitxa = {'versio': ts.versio, 'estat': ts.estat} if ts is not None else None

    grading = None
    sf = _resolve_working_size_fitting(model)   # resolutor canònic: grading és per SizeFitting, no per Model
    if sf is not None:
        gv = _active_grading_version(sf)
        if gv is not None:
            grading = {
                'version_number': gv.version_number,
                'aprovada': gv.aprovada,
                'size_fitting_id': sf.id,
            }

    n_active = model.base_measurements.filter(
        is_active=True, base_value_cm__isnull=False,
    ).count()
    base = {'base_size_label': model.base_size_label, 'n_active': n_active}

    artefactes_vigents = {'fitxa': fitxa, 'grading': grading, 'base': base}

    # --- Q4: tasques (Pla de treball) — ordre CANÒNIC + temps consumit + obertures + assignee ---
    # Additiu: es mantenen TOTS els camps antics (id, task_type, task_type_code, status,
    # assignee_id, order). Ordre per task_type.default_order/code (clau canònica de l'scheduler,
    # P0), NO per ModelTask.order. Temps i obertures es deriven sense camp nou (P0.1) amb consultes
    # SEPARADES per evitar el join cartesià Timer×Transition (RISC confirmat a P0.1).
    from django.db.models import Count
    from fhort.tasks.models import ModelTask as _ModelTask, TimerEntrada, TaskTransition

    pla_tasks = (_ModelTask.objects
                 .filter(model_id=model.id)
                 .select_related('task_type', 'assignee')
                 .order_by('task_type__default_order', 'task_type__code'))
    # Temps consumit per tasca amb la regla d'higiene (== helper canònic _real_minutes). 1 query.
    from fhort.tasks.services_i import minuts_per_model_task
    temps_per_task = minuts_per_model_task(
        TimerEntrada.objects.filter(model_task__model_id=model.id))
    # Obertures: count de transicions a InProgress per tasca (cada Play hi deixa una fila). 1 query.
    obertures_per_task = {r['model_task_id']: r['c'] for r in (
        TaskTransition.objects.filter(model_task__model_id=model.id, to_status='InProgress')
        .values('model_task_id').annotate(c=Count('id')))}

    tasques = [{
        'id': t.id,
        'task_type': t.task_type.name if t.task_type_id else None,
        'task_type_code': t.task_type.code if t.task_type_id else None,
        'task_type_name': t.task_type.name if t.task_type_id else None,
        'default_order': t.task_type.default_order if t.task_type_id else None,
        'status': t.status,
        'assignee_id': t.assignee_id,
        'assignee_nom': (t.assignee.nom_complet if t.assignee_id else None),
        'temps_consumit_min': int(temps_per_task.get(t.id, 0)),
        'obertures': int(obertures_per_task.get(t.id, 0)),
        'order': t.order,
        # B4a — origen/off_recipe per pintar el filet grana (extra fora de recepta) al board.
        'origen': t.origen,
        'off_recipe': t.off_recipe,
    } for t in pla_tasks]

    # --- Q3: atenció tècnica — alertes POM PENDENTS de resoldre ---
    # Anomalia de dades coneguda (ANOTAR): els ESTAT_CHOICES del model són
    # Pendent/Acceptat/Corregit, però els disparadors vius escriuen valors fora-de-choice
    # ('Obert' a FITTING pom/s10_views.py:144 i MANUAL pom/s11_views.py:191; 'Resolt' al
    # resoldre pom/s11_views.py:96). Per NO amagar alertes reals, "pendent" = NO resolt:
    # excloem el conjunt de resolts → surten 'Pendent', 'Obert' i qualsevol valor inesperat
    # (en un panell d'atenció és més segur surar que amagar). select_related(pom) evita N+1.
    RESOLVED_ALERT_STATES = ('Acceptat', 'Corregit', 'Resolt')
    alertes = [{
        'id': a.id,
        'tipus': a.tipus,
        'pom_codi': a.pom.codi_client if a.pom_id else None,
        'valor_detectat': str(a.valor_detectat) if a.valor_detectat is not None else None,
        'valor_esperat': str(a.valor_esperat) if a.valor_esperat is not None else None,
        'desviacio_cm': str(a.desviacio_cm) if a.desviacio_cm is not None else None,
        'tolerancia_cm': str(a.tolerancia_cm) if a.tolerancia_cm is not None else None,
        'missatge': a.missatge or '',
        'data_creacio': a.data_creacio,
    } for a in (POMAlert.objects
                .filter(model_id=model.id)
                .exclude(estat__in=RESOLVED_ALERT_STATES)
                .select_related('pom')
                .order_by('-data_creacio'))]
    atencio = {'alertes': alertes, 'n_pendents': len(alertes)}

    return Response({
        'model_id': model.id,
        'on_soc': on_soc,
        'artefactes_vigents': artefactes_vigents,
        'tasques': tasques,
        'atencio': atencio,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_timeline_view(request, model_id):
    """Timeline del model — PEÇA B2 (Q2 "què ha canviat").

    Merge ordenat per temps (desc) de les TRES fonts append-only `a` del model:
    canvis de mesura (MeasurementChangeLog), moviments de gate (GateEvent) i
    transicions de tasca (TaskTransition). Es projecten a UNA forma comuna
    {at, kind, actor, payload} discriminable per `kind`, i es retornen en UNA
    sola llista. NO inclou fonts `b` (pujades d'artefacte) ni `c` (arribades/
    handoffs) — v1 = només les 3 `a`. NO last-seen per-usuari (v1 = "últims canvis").
    Tot intra-tenant, read-only, cap escriptura a BD.

    Degradació amb gràcia: model nou sense events → 200 amb events:[]; cada
    projecció tolera FK null (actor null si SET_NULL; pom/task_type → null al payload)."""
    from django.shortcuts import get_object_or_404
    from .models import MeasurementChangeLog
    from fhort.tasks.models import GateEvent, TaskTransition

    model = get_object_or_404(Model, id=model_id)

    try:
        limit = int(request.query_params.get('limit', 50))
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 200))   # sostre de seguretat: "últims canvis", no historial sencer

    # actor unificat. measure_change → created_by és auth.User; gate/task → by és UserProfile.
    def actor_user(u):
        if u is None:
            return None
        return {'id': u.id, 'label': u.get_full_name() or u.get_username()}

    def actor_profile(p):
        if p is None:
            return None
        label = p.nom_complet or (p.user.get_username() if p.user_id else str(p.id))
        return {'id': p.id, 'label': label}

    events = []

    # Font 1 — MeasurementChangeLog (FK directa `model`). select_related evita N+1 sobre pom/created_by.
    for c in (MeasurementChangeLog.objects
              .filter(model_id=model.id)
              .select_related('pom', 'created_by')
              .order_by('-created_at')[:limit]):
        events.append({
            'at': c.created_at,
            'kind': 'measure_change',
            'actor': actor_user(c.created_by),
            'payload': {
                'pom_id': c.pom_id,
                'pom_codi': c.pom.codi_client if c.pom_id else None,
                'valor_anterior': c.valor_anterior,
                'valor_nou': c.valor_nou,
                'context': c.context,
                'fora_de_tolerancia': c.fora_de_tolerancia,
                'motiu': c.motiu,
            },
        })

    # Font 2 — GateEvent (FK directa `model`). kind discrimina gate_advance / gate_regress.
    for g in (GateEvent.objects
              .filter(model_id=model.id)
              .select_related('by', 'by__user')
              .order_by('-at')[:limit]):
        events.append({
            'at': g.at,
            'kind': 'gate_advance' if g.kind == 'advance' else 'gate_regress',
            'actor': actor_profile(g.by),
            'payload': {
                'from_phase': g.from_phase,
                'to_phase': g.to_phase,
                'notes': g.notes,
            },
        })

    # Font 3 — TaskTransition (FK INDIRECTA: filtrar per model_task__model). select_related al type.
    for tr in (TaskTransition.objects
               .filter(model_task__model_id=model.id)
               .select_related('by', 'by__user', 'model_task__task_type')
               .order_by('-at')[:limit]):
        tt = tr.model_task.task_type if tr.model_task.task_type_id else None
        events.append({
            'at': tr.at,
            'kind': 'task_transition',
            'actor': actor_profile(tr.by),
            'payload': {
                'task_type_code': tt.code if tt else None,
                'task_type_name': tt.name if tt else None,
                'from_status': tr.from_status,
                'to_status': tr.to_status,
            },
        })

    # Merge: cada font ja acotada a `limit` → ordenar per temps desc i retallar a `limit` global.
    # Correcte: els `limit` events més recents en total no poden venir més de `limit` d'una font.
    events.sort(key=lambda e: e['at'], reverse=True)
    events = events[:limit]

    return Response({'model_id': model.id, 'events': events})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def registre_activitat_view(request):
    """Sprint 4.5: llista global de ConsumptionRecord del tenant.
    Filtres: ?period=YYYY-MM &tecnic_id=<int> &page=<int> &page_size=<int>
    Retorna: { count, totals:{models,total_minutes,avg_per_model,avg_per_step}, results:[...] }
    Els minuts són els dels trams SANS (`tram_compta`), com la resta de superfícies de temps."""
    from fhort.models_app.models import ConsumptionRecord
    from fhort.tasks.services_i import tram_compta

    period   = request.query_params.get('period')
    tecnic_id = request.query_params.get('tecnic_id')
    page     = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 25)), 100)

    qs = ConsumptionRecord.objects.select_related('model__customer').prefetch_related(
        'model__model_tasks__timers',
        'model__model_tasks',
    ).order_by('-merited_at')

    if period:
        qs = qs.filter(period=period)
    if tecnic_id:
        qs = qs.filter(
            model__model_tasks__timers__tecnic_id=tecnic_id,
            model__model_tasks__timers__minuts__isnull=False,
        ).distinct()
    task_type_id = request.query_params.get('task_type_id')
    if task_type_id:
        qs = qs.filter(
            model__model_tasks__task_type_id=task_type_id,
            model__model_tasks__timers__minuts__isnull=False,
        ).distinct()

    # Totalitzadors sobre el queryset filtrat (en Python, sobre slice petit)
    all_ids = list(qs.values_list('id', flat=True))
    total_models = len(all_ids)
    total_minutes = 0
    total_steps = 0
    for rec in qs.prefetch_related('model__model_tasks__timers'):
        for mt in rec.model.model_tasks.all():
            total_steps += 1
            for tm in mt.timers.all():
                if tram_compta(tm):
                    total_minutes += tm.minuts

    avg_per_model = round(total_minutes / total_models, 1) if total_models else 0
    avg_per_step  = round(total_minutes / total_steps,  1) if total_steps  else 0

    # Paginació manual
    start = (page - 1) * page_size
    page_qs = qs[start:start + page_size]

    results = []
    for rec in page_qs:
        model = rec.model
        mins = sum(
            tm.minuts for mt in model.model_tasks.all()
            for tm in mt.timers.all() if tram_compta(tm)
        )
        steps = model.model_tasks.count()
        results.append({
            'id': model.id,
            'code': rec.code_snapshot,
            'name': rec.name_snapshot,
            'period': rec.period,
            'merited_at': rec.merited_at,
            'total_minutes': mins,
            'steps': steps,
            'opaque_ref': str(rec.opaque_ref),
        })

    return Response({
        'count': total_models,
        'totals': {
            'models': total_models,
            'total_minutes': total_minutes,
            'avg_per_model': avg_per_model,
            'avg_per_step': avg_per_step,
        },
        'results': results,
    })


def _truthy(v):
    """Un `confirm` que arriba com a string ('true'/'1') val igual que un booleà JSON."""
    return v is True or str(v).strip().lower() in ('true', '1', 'yes', 'si', 'sí')


class _Configure(HasCapability):
    """Gate CONFIGURE PROPI (D-PROM). La capa Item exigeix CONFIGURE a tot arreu
    (`pom/views.py:get_permissions`), i els endpoints de la capa Model estan gated només a
    `IsAuthenticated`. Un endpoint que ESCRIU a la capa Item des de la capa Model no pot
    heretar el gate fluix de l'amfitrió: se'l posa propi."""
    required_capability = CONFIGURE


@api_view(['POST'])
@permission_classes([_Configure])
def promoure_a_item_view(request, model_id):
    """POST /api/v1/models/<id>/promoure-a-item/ — P0+P2+P3, l'ACTE DE PROMOCIÓ model→item.

    LLEI (Agus, 2026-07-22): *"La sobirania del model és sobre els SEUS valors. L'estàndard del
    taller és un acte separat, explícit i CONFIGURE — mai un efecte secundari d'un import."*

    Aquest endpoint és el bessó INVERS de `materialize_poms_view`: allà la plantilla sembra el
    model, aquí un model real fixa la plantilla. Per això NO es penja de `confirmar/` de l'import
    (la norma inamovible 1 queda intacta) i per això té gate CONFIGURE propi.

    D-PROM — SOBREESCRIURE AMB CONFIRMACIÓ, en dues fases (mateix patró que el 409 del
    contenidor i que el principi del soroll):
      · **dry-run** (default) — retorna el diff sencer i NO escriu RES.
      · **`confirm=true`** — aplica, dins d'una sola transacció.

    El diff, per POM: `forat` (el set no el té) · `divergent` (el set el té amb un altre valor)
    · `igual` (res a fer) · `sobraria` (al set i no al model) · `ampliaria_item` (al model i fora
    del superset de POMs de l'item).

    B3 (2026-07-25) — REORIENTAT AL BASESET, amb tres canvis de fons que venen de la LLEI:

    LLEI 4 — les mesures base viatgen en UNA direcció, item→model. La promoció inversa
    **OMPLE FORATS EXCLUSIVAMENT**: afegeix al set els POMs que no hi són, i MAI modifica un
    valor que ja hi viu. Abans aquest mateix endpoint sobreescrivia amb `update_or_create`, i
    això convertia qualsevol model en autoritat sobre l'estàndard del taller. Modificar un valor
    existent és un acte canònic SEPARAT (`acte_canonic_base_set_view`, sota).

    LLEI 5 — la divergència model↔estàndard és VIDA NORMAL. Els divergents es llisten al diff
    perquè el tècnic els vegi, i prou: cap watchpoint, cap alarma, cap escriptura.

    LLEI 7 — un món sense set no és un error sec sinó un naixement pendent. Si el model viu en
    un món que no té BaseSet, el dry-run el PROPOSA (amb la talla base suggerida per la convenció
    Montse) i el confirm el crea amb `origen=PROMOCIO`. Aquesta és la via canònica de naixement
    d'un set. El backend no el crea mai sol: cal `confirm`.

    LLEI 6 — l'ampliació del superset (POMs del model que no són al `GarmentPOMMap` de l'item)
    va en secció pròpia del diff i només entra AMB CONFIRMACIÓ, mai en silenci.

    Els «sobraria» **NO s'esborren mai**, ni amb confirm. `ItemBaseMeasurement` no té
    `is_active`, o sigui que l'única poda possible seria un DELETE dur, i el principi del soroll
    diu proposar, no executar. Es LLISTEN perquè el tècnic els podi a mà des d'ItemAuthoring.

    V1 — aquest acte JA NO escriu `GarmentTypeItem.base_size_definition`: la talla base viu ara
    al set (llei 2, es declara en crear-lo). El camp queda com a llegat a jubilar.
    """
    from django.db import transaction
    from fhort.pom.models import (
        GarmentPOMMap, ItemBaseMeasurement, ItemBaseSet, SizeDefinition,
        normalize_fit_type, resolve_item_base_set, suggerir_talla_base, FitTypeDesconegut,
    )
    from fhort.models_app.models import BaseMeasurement

    model = (Model.objects.select_related('garment_type_item', 'size_system')
             .filter(id=model_id).first())
    if model is None:
        return Response({'error': 'Model no trobat'}, status=404)

    item = model.garment_type_item
    if item is None:
        return Response({'error': "Aquest model no té cap item de tipologia assignat: no hi ha "
                                  "cap plantilla a promoure."}, status=400)

    talla_model = (model.base_size_label or '').strip()
    if not talla_model:
        return Response({
            'error': "El model no té talla base definida. Un valor de plantilla ha de dir en "
                     "quina talla està expressat; sense això la promoció seria una mesura muda.",
            'tipus': 'model_sense_talla_base',
        }, status=422)

    if model.size_system_id is None:
        return Response({
            'error': "El model no té sistema de talles: sense món no hi ha BaseSet on promoure.",
            'tipus': 'model_sense_size_system',
        }, status=422)

    # ── El material: mesures VIVES i AMB VALOR del model. Les files buides o podades no són
    # patrimoni promocionable (principi del soroll: no s'ascendeix el que no és realitat).
    fonts = (BaseMeasurement.objects
             .filter(model=model, is_active=True, base_value_cm__isnull=False)
             .select_related('pom').order_by('ordre', 'id'))
    if not fonts:
        return Response({
            'error': "El model no té cap mesura viva amb valor: no hi ha res a promoure.",
            'tipus': 'model_sense_mesures',
        }, status=422)

    # ── EL MÓN. Lookup directe; si no hi ha set, el naixement es proposa (llei 7).
    base_set = resolve_item_base_set(item, model.size_system_id, model.fit_type)
    naixement = None
    talla_nova = None
    if base_set is None:
        # La talla base del set nou: la que digui el body, o la que suggereix la convenció.
        # Es valida SEMPRE contra el sistema del model — una talla d'un altre sistema faria
        # néixer el set mentint sobre en què parla.
        demanada = request.data.get('base_size_definition')
        if demanada:
            talla_nova = SizeDefinition.objects.filter(
                pk=demanada, size_system_id=model.size_system_id).first()
            if talla_nova is None:
                return Response({
                    'error': "La talla base demanada no existeix al sistema de talles del model.",
                    'tipus': 'talla_base_fora_del_sistema',
                }, status=422)
        else:
            talla_nova = suggerir_talla_base(model.size_system_id, model.target)
        if talla_nova is None:
            return Response({
                'error': ("El sistema de talles del model no té cap talla definida: no es pot "
                          "fer néixer el BaseSet."),
                'tipus': 'sistema_sense_talles',
            }, status=422)
        try:
            fit_obj = normalize_fit_type(model.fit_type)
        except FitTypeDesconegut:
            return Response({
                'error': (f"El fit «{model.fit_type}» del model no existeix al catàleg de "
                          "FitType: no es pot fer néixer el BaseSet d'aquest món."),
                'tipus': 'fit_desconegut',
            }, status=422)
        naixement = {
            'code': 'base_set_absent',
            'size_system_id': model.size_system_id,
            'size_system': model.size_system.codi,
            'fit_type': fit_obj.codi if fit_obj else None,
            'talla_base_proposada_id': talla_nova.pk,
            'talla_base_proposada': talla_nova.etiqueta,
            'talles_disponibles': [
                {'id': t.pk, 'etiqueta': t.etiqueta}
                for t in SizeDefinition.objects.filter(size_system_id=model.size_system_id)
                                               .order_by('ordre', 'id')],
            'origen': ItemBaseSet.ORIGEN_PROMOCIO,
        }

    # ── Coherència de talla: el valor del model només és promocionable si parla la MATEIXA
    # talla que el set. Amb un set nou això és cert per construcció si la talla proposada és la
    # del model; si no ho és, el tècnic està declarant que aquest model NO és el que fixa la base.
    talla_set = (base_set.base_size_definition.etiqueta if base_set is not None
                 else talla_nova.etiqueta)
    talla_divergent = (talla_set or '').strip() != talla_model
    talla_avis = None
    if talla_divergent:
        talla_avis = (f"El model parla en «{talla_model}» i el set del seu món parla en "
                      f"«{talla_set}». Promoure aquests valors hi escriuria mesures d'una altra "
                      "talla. No s'escriurà cap valor.")

    actuals = ({i.pom_id: i for i in ItemBaseMeasurement.objects.filter(base_set=base_set)}
               if base_set is not None else {})
    # LLEI 6 — el superset de POMs de l'item. El que en surti s'ha d'AMPLIAR amb confirmació.
    poms_item = set(GarmentPOMMap.objects.filter(garment_type_item=item)
                    .values_list('pom_id', flat=True))

    # ── El DIFF (pur, sense escriure).
    forats, divergents, iguals, ampliaria_item = [], [], [], []
    for bm in fonts:
        actual = actuals.get(bm.pom_id)
        fila = {
            'pom_id': bm.pom_id,
            'codi': bm.nom_fitxa or bm.pom.codi_client or '',
            'nom': bm.pom.nom_client or '',
            'valor_model': float(bm.base_value_cm),
        }
        if bm.pom_id not in poms_item:
            ampliaria_item.append(dict(fila))
        if actual is None:
            forats.append(fila)
        elif actual.base_value_cm is None:
            # Fila de pertinença sense valor: també és un forat, i omplir-lo no modifica res.
            fila['valor_item'] = None
            fila['origen_item'] = actual.origen
            forats.append(fila)
        elif float(actual.base_value_cm) != float(bm.base_value_cm):
            fila['valor_item'] = float(actual.base_value_cm)
            fila['origen_item'] = actual.origen
            # LLEI 5 — vida normal. Informatiu i prou: ni s'escriu ni s'aixeca cap watchpoint.
            divergents.append(fila)
        else:
            iguals.append(fila)

    poms_model = {bm.pom_id for bm in fonts}
    sobrarien = ([{
        'pom_id': i.pom_id,
        'codi': i.nom_fitxa or i.pom.codi_client or '',
        'nom': i.pom.nom_client or '',
        'valor_item': float(i.base_value_cm) if i.base_value_cm is not None else None,
        'origen_item': i.origen,
    } for i in ItemBaseMeasurement.objects
        .filter(base_set=base_set).exclude(pom_id__in=poms_model)
        .select_related('pom').order_by('pom__codi_client')] if base_set is not None else [])

    diff = {
        'model': model.id,
        'model_codi': model.codi_intern,
        'garment_type_item': item.id,
        'item_code': item.code,
        'talla_model': talla_model,
        'talla_set': talla_set,
        'talla_divergent': talla_divergent,
        'talla_avis': talla_avis,
        'base_set': ({'id': base_set.pk,
                      'size_system': base_set.size_system.codi,
                      'fit_type': base_set.fit_type.codi if base_set.fit_type_id else None,
                      'base_size_label': base_set.base_size_definition.etiqueta,
                      'origen': base_set.origen} if base_set is not None else None),
        'naixement': naixement,
        'forats': forats,
        # LLEI 5 — es mostren els dos valors i NO es toquen. Modificar-los és l'acte canònic.
        'divergents': divergents,
        'iguals': iguals,
        # LLEI 6 — mai en silenci.
        'ampliaria_item': ampliaria_item,
        # NO s'esborren mai: es llisten perquè el tècnic decideixi a ItemAuthoring.
        'sobrarien': sobrarien,
        'resum': {'forats': len(forats), 'divergents': len(divergents),
                  'iguals': len(iguals), 'sobrarien': len(sobrarien),
                  'ampliaria_item': len(ampliaria_item)},
    }

    if not _truthy(request.data.get('confirm')):
        diff['dry_run'] = True
        diff['message'] = (
            (f"El món «{diff['naixement']['size_system']}» encara no té mesures estàndard: es "
             f"crearia el set amb talla base «{naixement['talla_base_proposada']}». "
             if naixement else '')
            + (f"{len(forats)} forat(s) s'omplirien, {len(divergents)} divergent(s) es "
               f"CONSERVEN sense tocar, {len(iguals)} iguals. " if not talla_divergent
               else "Cap valor s'escriuria: les talles no coincideixen. ")
            + (f"{len(ampliaria_item)} POM(s) ampliarien el superset de l'item. "
               if ampliaria_item else '')
            + "Cap escriptura feta.")
        return Response(diff, status=200)

    # ── APLICAR. Tot dins d'una transacció: o s'escriu el món sencer, o no s'escriu res.
    with transaction.atomic():
        if base_set is None:
            base_set = ItemBaseSet.objects.create(
                garment_type_item=item,
                size_system_id=model.size_system_id,
                fit_type=normalize_fit_type(model.fit_type),
                base_size_definition=talla_nova,
                origen=ItemBaseSet.ORIGEN_PROMOCIO,
                updated_by=request.user,
            )

        # LLEI 6 — l'ampliació del superset entra AQUÍ, dins del confirm, mai abans.
        ordre_seguent = (GarmentPOMMap.objects.filter(garment_type_item=item)
                         .order_by('-ordre').values_list('ordre', flat=True).first() or 0)
        for fila in ampliaria_item:
            ordre_seguent += 1
            GarmentPOMMap.objects.get_or_create(
                garment_type_item=item, pom_id=fila['pom_id'],
                # pendent_revisio=False: els confirma un tècnic amb gate CONFIGURE, no un clon
                # automàtic de germà (que és el cas que va inventar la marca).
                defaults={'ordre': ordre_seguent, 'pendent_revisio': False},
            )

        escrits = 0
        if not talla_divergent:
            for fila in forats:
                bm = next(b for b in fonts if b.pom_id == fila['pom_id'])
                # LLEI 4 — NOMÉS forats. `update_or_create` sobre una fila amb valor seria
                # exactament l'acte que aquesta llei prohibeix; per això la clau del create és
                # el forat i els divergents ni entren al bucle.
                obj, creat = ItemBaseMeasurement.objects.get_or_create(
                    base_set=base_set, pom_id=bm.pom_id,
                    defaults={
                        'garment_type_item': item,
                        'base_value_cm': bm.base_value_cm,
                        'tol_minus': bm.tolerancia_minus,
                        'tol_plus': bm.tolerancia_plus,
                        'nom_fitxa': bm.nom_fitxa or '',
                        'origen': ItemBaseMeasurement.ORIGEN_PROMOTED,
                        'updated_by': request.user,
                    })
                if creat:
                    escrits += 1
                elif obj.base_value_cm is None:
                    # Pertinença sense valor: omplir el forat NO és modificar res.
                    obj.base_value_cm = bm.base_value_cm
                    obj.tol_minus = bm.tolerancia_minus
                    obj.tol_plus = bm.tolerancia_plus
                    obj.nom_fitxa = bm.nom_fitxa or obj.nom_fitxa
                    obj.origen = ItemBaseMeasurement.ORIGEN_PROMOTED
                    obj.updated_by = request.user
                    obj.save(update_fields=['base_value_cm', 'tol_minus', 'tol_plus',
                                            'nom_fitxa', 'origen', 'updated_by', 'updated_at'])
                    escrits += 1

    diff['dry_run'] = False
    diff['base_set'] = {'id': base_set.pk,
                        'size_system': base_set.size_system.codi,
                        'fit_type': base_set.fit_type.codi if base_set.fit_type_id else None,
                        'base_size_label': base_set.base_size_definition.etiqueta,
                        'origen': base_set.origen}
    diff['base_set_creat'] = naixement is not None
    diff['promoguts'] = escrits
    diff['ampliats'] = len(ampliaria_item)
    diff['message'] = (
        (f"BaseSet creat per al món «{base_set.size_system.codi}» amb talla base "
         f"«{base_set.base_size_definition.etiqueta}» (origen PROMOCIO). " if naixement else '')
        + (f"{escrits} forat(s) omplerts a la plantilla de l'item «{item.code}» amb origen "
           f"PROMOTED. " if escrits else "Cap valor escrit. ")
        + (f"{len(divergents)} valor(s) divergeixen del model i s'han CONSERVAT intactes: "
           "canviar-los és l'acte canònic, no la promoció. " if divergents else '')
        + (f"{len(ampliaria_item)} POM(s) afegits al superset de l'item. "
           if ampliaria_item else '')
        + (f"{len(sobrarien)} valor(s) del set no són al model i s'han CONSERVAT: "
           f"podi'ls a mà des de l'autoria d'item si vols." if sobrarien else ''))
    return Response(diff, status=200)


@api_view(['POST'])
@permission_classes([_Configure])
def acte_canonic_base_set_view(request, base_set_id):
    """POST /api/v1/item-base-sets/<id>/acte-canonic/ — MODIFICAR un valor que el set ja té.

    B3 (2026-07-25). La llei 4 treu aquesta capacitat de la promoció a posta: si un model
    qualsevol pogués reescriure un valor de l'estàndard, l'estàndard no seria de ningú. Marcar
    un valor NOU com a canònic de la marca és un acte propi, deliberat i signat.

    Body: {pom, base_value_cm, tol_minus?, tol_plus?, confirm}. Sense `confirm` és dry-run i
    torna el valor anterior i el nou sense escriure. Gate CONFIGURE (com la promoció).

    El registre de qui/quan/valor-anterior viu a `MeasurementChangeLog`, que és on ja viu la
    resta de l'auditoria de mesures — no s'inventa una segona taula de log per a això.
    """
    from decimal import Decimal, InvalidOperation
    from fhort.pom.models import ItemBaseMeasurement, ItemBaseSet

    base_set = (ItemBaseSet.objects
                .select_related('size_system', 'fit_type', 'base_size_definition',
                                'garment_type_item')
                .filter(pk=base_set_id).first())
    if base_set is None:
        return Response({'error': 'BaseSet no trobat'}, status=404)

    pom_id = request.data.get('pom')
    if not pom_id:
        return Response({'error': 'pom requerit.'}, status=400)

    actual = (ItemBaseMeasurement.objects.select_related('pom')
              .filter(base_set=base_set, pom_id=pom_id).first())
    if actual is None or actual.base_value_cm is None:
        return Response({
            'error': ("Aquest POM no té cap valor al set: omplir un forat NO és un acte canònic, "
                      "és una promoció. Fes-la des del model."),
            'tipus': 'no_hi_ha_valor_a_substituir',
        }, status=422)

    cru = request.data.get('base_value_cm')
    try:
        nou_valor = Decimal(str(cru))
    except (InvalidOperation, TypeError, ValueError):
        return Response({'error': 'base_value_cm ha de ser un número.'}, status=400)

    anterior = float(actual.base_value_cm)
    resposta = {
        'base_set': base_set.pk,
        'pom_id': actual.pom_id,
        'codi': actual.nom_fitxa or actual.pom.codi_client or '',
        'talla_base': base_set.base_size_definition.etiqueta,
        'valor_anterior': anterior,
        'valor_nou': float(nou_valor),
        'canvia': float(nou_valor) != anterior,
    }

    if not _truthy(request.data.get('confirm')):
        resposta['dry_run'] = True
        resposta['message'] = (
            f"Simulació: «{resposta['codi']}» passaria de {anterior} a {float(nou_valor)} cm a la "
            f"talla base «{resposta['talla_base']}». Cap escriptura feta."
            if resposta['canvia'] else
            f"«{resposta['codi']}» ja val {anterior} cm: no hi ha res a canviar.")
        return Response(resposta, status=200)

    if not resposta['canvia']:
        resposta['dry_run'] = False
        resposta['message'] = f"«{resposta['codi']}» ja val {anterior} cm: no s'ha escrit res."
        return Response(resposta, status=200)

    camps = {'base_value_cm': nou_valor}
    for camp in ('tol_minus', 'tol_plus'):
        if camp in request.data:
            camps[camp] = request.data.get(camp)
    for camp, valor in camps.items():
        setattr(actual, camp, valor)
    # L'acte canònic és mà humana signada: la provinença ho ha de dir, no quedar-se a PROMOTED.
    actual.origen = ItemBaseMeasurement.ORIGEN_MANUAL
    actual.updated_by = request.user
    actual.save(update_fields=list(camps) + ['origen', 'updated_by', 'updated_at'])

    resposta['dry_run'] = False
    resposta['message'] = (
        f"«{resposta['codi']}» marcat com a canònic de la marca: {anterior} → "
        f"{float(nou_valor)} cm a la talla base «{resposta['talla_base']}».")
    return Response(resposta, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def desactivar_pom_view(request, model_id, pom_id):
    """C1 (PRINCIPI DEL SOROLL, 2026-07-22) — PODA d'un POM del model. SOFT, mai DELETE.

    La superfície de treball real (MeasureGrid) no tenia cap manera de treure un POM del
    model: la poda només existia com a efecte col·lateral del desat complet de la taula de
    GÈNESI (`keep_pom_ids`), i l'endpoint REST de DELETE dur era orfe de client
    (DIAGNOSI_GTI_PLANTILLA §B3.4). Això n'és la porta, i és la SOFT: `is_active=False` +
    entrada al `MeasurementChangeLog` (via la marca `_desactivat`, vegeu signals.py).

    Deliberadament NO es cabla el DELETE dur: la mesura va existir i el model n'ha de
    guardar memòria. La UI pot dir «eliminar»; la BD diu «inactiva».

    Body opcional: {motiu: str}.
    """
    from fhort.models_app.models import BaseMeasurement

    bm = (BaseMeasurement.objects
          .filter(model_id=model_id, pom_id=pom_id, is_active=True)
          .select_related('pom').first())
    if bm is None:
        return Response({'detail': 'Mesura no trobada (o ja inactiva) per a aquest model.'},
                        status=404)

    bm.is_active = False
    bm._desactivat = True
    bm._changed_by = request.user
    bm._motiu = (request.data.get('motiu') or '').strip() or 'poda manual des de la graella'
    bm.save(update_fields=['is_active'])

    return Response({
        'model': int(model_id),
        'pom': int(pom_id),
        'base_measurement': bm.id,
        'is_active': False,
        'codi': bm.nom_fitxa or bm.pom.codi_client or '',
    })


def _sembra_step_des_dels_specs(model, pom_id):
    """`valors_step` d'un POM derivat dels seus GradedSpec VIGENTS. {} si no es pot.

    La part d'I/O de la sembra: tria d'on es llegeixen els números (la versió de grading
    vigent del SizeFitting de treball, criteri únic de `vigent_grading_version`) i la
    geometria del motor (`escala_del_model` → run del SISTEMA, llei S24b). L'aritmètica és
    de `grading_utils.sembra_valors_step`, pura i testejable a part.

    Retorna {} —i el cridador deixa la regla com estava— quan el model encara no té
    grading: un model sense specs ha de poder passar a STEP i néixer buit, no petar.
    """
    from fhort.fitting.models import GradedSpec
    from fhort.fitting.services import _resolve_working_size_fitting, vigent_grading_version
    from fhort.pom.grading_utils import sembra_valors_step
    from fhort.pom.services import escala_del_model

    sf = _resolve_working_size_fitting(model)
    gv = vigent_grading_version(sf) if sf is not None else None
    if gv is None:
        return {}

    valors = dict(GradedSpec.objects
                  .filter(grading_version=gv, pom_id=pom_id, is_active=True)
                  .values_list('size_label', 'graded_value_cm'))
    if not valors:
        return {}

    try:
        _size_run, run_sistema, _pos, _base_idx = escala_del_model(model)
    except ValueError:
        return {}       # geometria incompleta: no es sembra a mitges (v. docstring)
    return sembra_valors_step(valors, run_sistema, model.base_size_label)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_pom_regim_view(request, model_id, pom_id):
    """PG-4b-3a / P3 — UPSERT de la REGLA resident (ModelGradingRule) per (model, pom).

    La regla (règim + deltes + break) és patrimoni VIU del MODEL (origen='MANUAL'); el motor la
    llegeix via _load_grading_rules→_apply_rule (NO es toca el CÀLCUL). Body (tots opcionals;
    s'actualitza només el que ve):
      - logica: 'LINEAR' | 'STEP'
      - increment_base: float|null   (delta base, p.ex. 4)
      - increment_break: float|null  (delta a partir del trencament, p.ex. 2.5)
      - talla_break_label: str|null  (talla d'inici del break; del run del model)
    Si la resident no existeix: es materialitza des del fallback del catàleg; si tampoc n'hi ha,
    es crea de nou (autoria manual de la regla des de zero). Innocu sobre el grading persistent
    (no toca GradedSpec/GradingVersion; només el proper generate_graded_specs).

    Passar a STEP amb `valors_step` buit els SEMBRA des dels GradedSpec vigents del model per a
    aquell POM (`_sembra_step_des_dels_specs`): la fila STEP neix amb els números que ja es
    veien, editables. Els specs només es LLEGEIXEN.
    """
    from fhort.models_app.models import ModelGradingRule
    from fhort.pom.models import GradingRule

    data = request.data
    has = lambda k: k in data   # noqa: E731 — actualització selectiva per presència de camp

    valid_logiques = {code for code, _ in GradingRule.LOGICA_CHOICES}
    logica = (data.get('logica') or '').strip().upper() if has('logica') else None
    if logica is not None and logica not in valid_logiques:
        return Response({'detail': f"logica ha de ser un de: {', '.join(sorted(valid_logiques))}"}, status=400)

    def _num(k):
        v = data.get(k)
        if v in (None, ''):
            return None
        try:
            return float(str(v).replace(',', '.'))
        except (TypeError, ValueError):
            return 'ERR'

    model = Model.objects.filter(pk=model_id).first()
    if model is None:
        return Response({'detail': 'Model no trobat.'}, status=404)

    with transaction.atomic():
        rule = ModelGradingRule.objects.filter(model=model, pom_id=pom_id).first()
        if rule is None:
            # Sembra des del fallback del catàleg si n'hi ha; si no, regla nova (autoria de zero).
            src = (GradingRule.objects.filter(
                       rule_set_id=model.grading_rule_set_id, pom_id=pom_id).first()
                   if model.grading_rule_set_id else None)
            rule = ModelGradingRule(
                model=model, pom_id=pom_id, actiu=True,
                logica=(src.logica if src else 'LINEAR'),
                increment=(src.increment if src else 0),
                valors_step=(src.valors_step if src else None),
                increment_base=(src.increment_base if src else None),
                increment_break=(src.increment_break if src else None),
                talla_break_label=(src.talla_break_label if src else None),
                talla_break_pos=(src.talla_break_pos if src else None),
            )

        if logica is not None:
            rule.logica = logica
        for k in ('increment_base', 'increment_break'):
            if has(k):
                val = _num(k)
                if val == 'ERR':
                    return Response({'detail': f"{k} ha de ser numèric."}, status=400)
                setattr(rule, k, val)
        if has('talla_break_label'):
            tbl = (data.get('talla_break_label') or '').strip() or None
            rule.talla_break_label = tbl
            rule.talla_break_pos = None
            if tbl and model.size_run_model:
                run = [s.strip() for s in model.size_run_model.replace(';', '·').split('·') if s.strip()]
                if tbl in run:
                    rule.talla_break_pos = run.index(tbl)
        # El pas a STEP CONSERVA els valors vigents (DIAGNOSI_GRADING_POP, 30/07). Una regla
        # STEP viu dels seus `valors_step`; passar-hi amb el calaix buit deixava `_apply_rule`
        # retornant None per a cada cel·la i el `continue` de services.py:277 no reescrivia res
        # — els GradedSpec vells es quedaven a la taula i la fila es CONGELAVA amb números que
        # ja no venien de cap regla. Aquí se sembren els deltes des dels valors que ja es veien,
        # i la fila neix amb els mateixos números, ara editables i re-emesos.
        if rule.logica == 'STEP' and not rule.valors_step:
            rule.valors_step = _sembra_step_des_dels_specs(model, rule.pom_id) or None

        # D2 — una regla LINEAR amb delta 0 és INVÀLIDA: no gradua res, i el que expressa
        # («aquesta mesura no canvia entre talles») ja té forma pròpia i honesta, que és
        # FIXED. Deixar-la passar torna a fabricar una taula plana que sembla graduada.
        # A3 (2026-07-22): la condició viu ara a pom.grading_regime (punt únic del backend),
        # perquè aquest camí i el de `gravar_pom` no divergeixin.
        if es_linear_degenerada(rule.logica, rule.increment_base, rule.increment,
                                rule.increment_break, rule.talla_break_label):
            return Response({
                'detail': MISSATGE_LINEAR_ZERO,
                'codi': CODI_LINEAR_ZERO,
            }, status=400)

        rule.origen = 'MANUAL'
        rule.save()

    return Response({
        'model': model.id,
        'pom': rule.pom_id,
        'logica': rule.logica,
        'origen': rule.origen,
        'increment_base': float(rule.increment_base) if rule.increment_base is not None else None,
        'increment_break': float(rule.increment_break) if rule.increment_break is not None else None,
        'talla_break_label': rule.talla_break_label,
    })
