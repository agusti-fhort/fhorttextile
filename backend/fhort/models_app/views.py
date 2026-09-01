import datetime
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from django.db.models import Exists, OuterRef
from rest_framework import mixins, viewsets
from rest_framework import status as http_status
from rest_framework.decorators import api_view, parser_classes, permission_classes, action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from fhort.accounts.capabilities import HasCapability, EXECUTE_TASKS, CONFIGURE, CLOSE_GATES
from fhort.pom.services import SealedGradingVersionError, _te_regles
from fhort.pom.grading_regime import (
    CODI_LINEAR_ZERO, MISSATGE_LINEAR_ZERO, es_linear_degenerada, valida_breaks,
)
# F1.3 — el batec d'escriptura: escriure sobre un model és el senyal de «hi estic
# treballant» (D-2). El decorador bat NOMÉS en 2xx i mai llança.
from fhort.tasks.services_batec import (SUP_ESCALAT, SUP_FITXA, SUP_MESURES, SUP_PRESA,
                                        bat_escriptura, batec_de_request)
from fhort.pom.models import MeasurementInstance, MeasurementLayer
from fhort.pom.plausibilitat import CODI_MESURA_FORA_RANG, mesura_fora_de_rang
from .models import (BaseMeasurement, ConsumptionRecord, GarmentSet, Model, ModelFitxer,
                     ModelGarment, Watchpoint)
from .services_fitxers import DOWNLOAD_SALT, DOWNLOAD_TTL
from fhort.pom.nomenclatura import (abreviatura_de, alies_per_pom, camps_de,
                                    categoria_de, codi_de, noms_de)
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
    # A5 · llista canònica (NORMA_LAYOUT §8e): «capçaleres th ORDENABLES amb icona d'ordenació».
    # Una capçalera que ofereix ordenar i el backend rebutja (DRF ignora en silenci el camp que
    # no és a la llista) és pitjor que no oferir-ho. S'hi afegeixen NOMÉS els camps que la
    # graella pinta —tots columnes reals de `Model`, cap anotació ni cap camp calculat—; la
    # columna «Estat» no hi entra perquè avui no té dada (Kanban comercial pendent).
    ordering_fields = [
        'prioritat', 'data_objectiu', 'data_entrada',
        'codi_intern', 'codi_client', 'nom_prenda', 'collection', 'temporada', 'any',
        'fase_actual',
    ]
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
    # SET-2/T5 — `garment` entra al filtre perquè el client pugui demanar les mesures d'UNA
    # peça. Sense ell, l'única manera de separar-les seria filtrar a mà a la vora del payload.
    filterset_fields = ['model', 'pom', 'is_active', 'origen', 'garment']
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
        # F1.3 — editar una cel·la de la graella de mides ÉS treballar. El `model_id` no ve del
        # camí sinó de la fila (`BaseMeasurement.model`), i és per això que aquesta superfície
        # —la que més s'escriu— no tenia rellotge fins avui.
        batec_de_request(self.request, serializer.instance.model_id, SUP_MESURES)



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


def comptar_regles_residents(model):
    """D-31.4 — quantes regles residents cauran si s'assigna un ruleset, i de quin origen.

    → `(total, {origen: n})`. Un dict buit vol dir que no hi ha res a perdre.

    L'origen no és decoratiu: una `IMPORTED` ve del document del client i es pot tornar a
    importar; una `MANUAL` només existeix al cap de qui la va escriure. Qui confirma
    l'esborrat ha de poder distingir-les abans de dir que sí, no després.
    """
    from django.db.models import Count
    files = (model.grading_rules.values('origen')
             .annotate(n=Count('id')).order_by('origen'))
    per_origen = {f['origen']: f['n'] for f in files}
    return sum(per_origen.values()), per_origen


def comptar_regles_residents_per_garment(model):
    """SET-2/R11 — les mateixes regles residents, comptades per PEÇA.

    → `{garment: n}`, amb `''` per a la peça mare. Germà de `comptar_regles_residents`,
    que les compta per ORIGEN: són dos talls del mateix conjunt i cadascun respon una
    pregunta distinta del diàleg de confirmació —«què perdré» (origen) i «de quina prenda»
    (peça)—. Es deixen separats a posta: fer que un sol comptador tornés els dos talls
    hauria canviat l'aritat de retorn de `comptar_regles_residents`, que té QUATRE
    cridadors i dos en desempaqueten el parell (censat el 2026-08-11:
    `views.py:679`, `:1110`, `:1142` i `migra_brownie_ruleset.py:142`).

    Per què el diàleg ho necessita: amb dues peces vives, «aquest model té 15 regles
    pròpies i les perdràs» no diu prou. Perdre-les totes i perdre les d'una sola prenda
    són dos gestos molt diferents, i qui confirma ha de poder distingir-los ABANS de dir
    que sí, no després — el mateix argument que va fer néixer `per_origen`.
    """
    from django.db.models import Count
    files = (model.grading_rules.values('garment')
             .annotate(n=Count('id')).order_by('garment'))
    return {f['garment']: f['n'] for f in files}


def _validar_ruleset_assignable(rs, *, size_system_id=None, customer_id=None, confirmat=False,
                                model=None, confirmat_residents=False, preservades=0):
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
      - regles residents          → AVÍS CONSCIENT (409) fins que arribi `confirmat_residents`
                                    (D-31.4). Tampoc bloqueig: migrar un model al catàleg és
                                    legítim; el que no és legítim és fer-ho sense saber-ho.

    ⚠️ `model` és opcional PERQUÈ EL CAMÍ DE CREACIÓ NO EN TÉ: un model que encara no existeix
    no pot tenir regles residents, i el cas D-31.4 no s'hi ha d'activar mai.

    ⚠️ ELS DOS FLAGS SÓN SEPARATS I NO ES REUTILITZEN L'UN PER L'ALTRE. Acceptar el grading
    d'un altre client no és acceptar que s'esborrin 88 regles pròpies. Amb un sol flag, un
    consentiment n'arrossegaria l'altre en silenci — i el silenci és exactament el defecte que
    D-31.4 tanca. Si els dos casos concorren, es retornen d'un en un: el client confirma, torna
    a demanar, i troba el segon. Cap consentiment implícit.
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

    # D-31.4 — LES REGLES RESIDENTS QUE CAURAN. Va l'ÚLTIM dels quatre a posta: si el ruleset
    # no és assignable (buit, run divergent) no té sentit avisar del que s'hi perdria, perquè
    # no s'arribarà a assignar mai.
    #
    # 6.1 — `preservades` són les `MANUAL` d'autoria que sobreviuran al wipe. Es resten del que
    # es demana permís per destruir, i si no queda res a destruir NO ES DEMANA RES: el permís i
    # la destrucció han de mirar el mateix (F1-bis), i això val en els dos sentits.
    if model is not None and not confirmat_residents:
        total_abans, per_origen = comptar_regles_residents(model)
        total = total_abans - preservades
        if total > 0:
            per_origen = dict(per_origen)
            if preservades:
                restant = per_origen.get('MANUAL', 0) - preservades
                if restant > 0:
                    per_origen['MANUAL'] = restant
                else:
                    per_origen.pop('MANUAL', None)
            n_imported = per_origen.get('IMPORTED', 0)
            detall = ' · '.join(f'{n} {o}' for o, n in sorted(per_origen.items()))
            frase_imported = (
                f" {n_imported} d'elles vénen del document del client (IMPORTED)."
                if n_imported else '')
            return ({
                'conflict': True,
                'tipus': 'esborrat_residents',
                'codi': 'GRADING_RESIDENTS_WIPE',
                'grading_rule_set_id': rs.id,
                'grading_rule_set_nom': rs.nom,
                'model_id': model.id,
                'residents': total,
                'per_origen': per_origen,
                # SET-2/R11 — DE QUINA PEÇA parla cadascuna. Clau NOVA i additiva, com
                # `preservades`: el front que no la conegui segueix llegint `residents`
                # i `per_origen` com sempre.
                'per_garment': comptar_regles_residents_per_garment(model),
                # 6.1 — les que es queden. Clau NOVA i additiva: el front que no la conegui
                # segueix llegint `residents` i `per_origen` com sempre.
                'preservades': preservades,
                # Redundant amb `per_origen` I A POSTA: la llei diu que IMPORTED s'ha de poder
                # distingir, i una clau de primer nivell no es pot passar per alt llegint el
                # payload de pressa. Perdre una regla escrita a mà no és el mateix que perdre'n
                # una que es pot tornar a importar.
                'imported': n_imported,
                'message': (
                    f"Aquest model té {total} regles de graduació pròpies ({detall}). "
                    f"Assignar-li «{rs.nom}» les esborrarà i el model passarà a graduar "
                    f"amb les del joc.{frase_imported}"
                    + (f" Les {preservades} escrites a mà (MANUAL) es conserven."
                       if preservades else '')
                    + " Confirma-ho per continuar."),
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
            # M3 · FIT-9 — el vocabulari d'estat viu a `Model.ESTAT_CHOICES` i no s'escriu a mà:
            # aquest literal deia `'Nou'` i el dia del repropòsit hauria escrit un valor mort.
            estat=Model.ESTAT_NOU,
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
    # ── F1-bis (Agus, 06/08 vespre) · EL PERMÍS I LA DESTRUCCIÓ MIREN EL MATEIX ──────────────
    # EL JOC QUE EL MODEL TENIA ABANS que el resolutor toqui res. Sense aquesta foto, «ha
    # canviat el joc?» no es pot respondre —a partir del `setattr` de sota el model ja porta el
    # valor nou— i era exactament aquí que s'obria el forat: el permís (409 de D-31.4) mirava el
    # PAYLOAD (`d.get('grading_rule_set_id')`) i la destrucció mirava l'ESTAT DEL MODEL
    # (`model.grading_rule_set_id`). El predicat destructiu era el més ample, o sigui que
    # QUALSEVOL `update-step2` sobre un model amb joc —un canvi de talla base, un canvi de
    # construcció, res a veure amb la graduació— reescrivia les residents i es menjava les
    # `origen='MANUAL'` sense 409, sense Watchpoint i sense que ningú hagués parlat de graduar.
    grs_abans = model.grading_rule_set_id
    # 6.1 — l'OBJECTE, no només l'id: per decidir si les `MANUAL` són autoria cal llegir-ne
    # l'`origen`, i s'ha de capturar ABANS del `setattr` (a partir d'aquí l'atribut ja resol el
    # joc NOU). `None` si el model no en tenia cap, i és informació, no absència.
    grs_abans_obj = model.grading_rule_set
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

    # ── LES DUES PORTES QUE DESTRUEIXEN REGLES, i el que les separa de les que no en toquen cap.
    # `canvia_joc` és el predicat ÚNIC: el joc entra al payload **i** el valor és un altre. Un
    # PATCH que no parla de graduació —o que reenvia el joc que el model ja té— no toca cap regla.
    joc_demanat = d.get('grading_rule_set_id') or None
    desacobla_joc = 'grading_rule_set_id' in d and not joc_demanat and bool(grs_abans)
    canvia_joc = bool(joc_demanat) and model.grading_rule_set_id != grs_abans
    confirmat_residents = bool(d.get('confirmar_esborrat_residents'))
    residents_perdudes = (0, {})
    motiu_watchpoint = None
    # 6.1 — els POMs de les `MANUAL` que sobreviuran. Buit per defecte: la porta de desacoblar
    # («Sense graduació») segueix esborrant-ho tot, com abans. El gest hi diu explícitament que
    # el model es queda SENSE graduació, i deixar-hi residents òrfenes el faria graduar igual
    # (`_load_grading_rules` és all-or-nothing) — que és el contrari del que l'usuari ha demanat.
    poms_preservats = set()

    # WIZARD pas 4 «Sense graduació» en EDICIÓ: buidatge EXPLÍCIT del ruleset. El resolutor només
    # ASSIGNA quan grading_rule_set_id és truthy (mai neteja); aquí, si la clau ve present i buida
    # (null), es desacobla la graduació i s'esborren les regles residents (queda estat "sense graduació",
    # vàlid). Idempotent i acotat a la intenció explícita del pas 4 — cap efecte si la clau no ve.
    #
    # D-31.4 · LA SEGONA PORTA (Agus, 06/08 vespre). «Sense graduació» diu que desacobla el JOC;
    # no diu que s'endugui les regles que el tècnic ha escrit A MÀ, i qui prem el botó espera
    # quedar-se-les. Com que el gest les mata, ha de demanar permís amb el recompte al davant —i
    # no pot sortir més barat que canviar de joc, que ja el demanava.
    # El `tipus` és el MATEIX ('esborrat_residents') A POSTA: el fet és idèntic —les residents
    # cauen— i el front ja el sap gestionar (`useConfirmacioRuleset.FLAG_PER_TIPUS`, mateix flag,
    # mateix resum per origen). El que canvia és la CAUSA, i la causa viu al `message`, que el
    # redacta el backend perquè és qui sap el recompte.
    if desacobla_joc:
        _total, _per_origen = comptar_regles_residents(model)
        if _total and not confirmat_residents:
            _detall = ' · '.join(f'{n} {o}' for o, n in sorted(_per_origen.items()))
            _n_imported = _per_origen.get('IMPORTED', 0)
            return Response({
                'conflict': True,
                'tipus': 'esborrat_residents',
                'codi': 'GRADING_RESIDENTS_WIPE',
                'model_id': model.id,
                'residents': _total,
                'per_origen': _per_origen,
                # SET-2/R11 — el MATEIX camp que l'altre 409 d'aquest `tipus`. Les dues
                # portes alimenten el MATEIX diàleg (`useConfirmacioRuleset`, mateix
                # `tipus` a posta), o sigui que servir-lo en una i no en l'altra deixaria
                # el diàleg mut segons per on s'hi hagi arribat.
                'per_garment': comptar_regles_residents_per_garment(model),
                'imported': _n_imported,
                'message': (
                    f"Aquest model té {_total} regles de graduació pròpies ({_detall}). "
                    f"Deixar-lo sense graduació les esborrarà totes."
                    + (f" {_n_imported} d'elles vénen del document del client (IMPORTED)."
                       if _n_imported else '')
                    + " Confirma-ho per continuar."),
            }, status=409)
        model.grading_rule_set = None
        model.grading_rules.all().delete()
        residents_perdudes = (_total, _per_origen)
        motiu_watchpoint = 'desacoblat_graduacio'

    # D1 — valida ABANS de desar i abans del wipe-and-recreate. Es valida contra els valors
    # POSTERIORS a l'assignació (el mateix PATCH pot canviar size_system), i només quan el
    # ruleset CANVIA de debò: re-desar un model sense tocar la graduació —o reenviant el joc
    # que ja hi és— no ha de rebotar ni ha de destruir res.
    if canvia_joc:
        # D-31.4 — el recompte es pren AQUÍ, abans de validar i abans de desar: a partir de
        # `model.save()` el wipe-and-recreate de :1001 ja les haurà esborrades i el rastre no
        # podria dir quantes n'hi havia.
        residents_perdudes = comptar_regles_residents(model)
        motiu_watchpoint = 'esborrat_residents'
        # 6.1 — quines sobreviuran. Es passa al validador perquè EL PERMÍS I LA DESTRUCCIÓ
        # MIRIN EL MATEIX (la llei de F1-bis): demanar permís per esborrar 4 regles que no
        # s'esborraran és la mateixa mentida, amb el signe canviat.
        from fhort.models_app.services import poms_manual_a_preservar
        poms_preservats = poms_manual_a_preservar(model, grs_abans_obj)
        _err = _validar_ruleset_assignable(
            model.grading_rule_set,
            size_system_id=model.size_system_id,
            customer_id=model.customer_id,
            confirmat=bool(d.get('confirmar_altre_client')),
            model=model,
            confirmat_residents=confirmat_residents,
            preservades=len(poms_preservats),
        )
        if _err is not None:
            payload, status_code = _err
            return Response(payload, status=status_code)

    model.save()
    # PG-2 Cas B: re-materialitza NOMÉS quan el joc canvia (F1-bis). El wipe-and-recreate cobreix
    # el canvi de profile; el que no pot cobrir és un PATCH que no parla de graduació.
    # L'atomic embolcalla només la materialització → si peta, el model queda sense MGR i gradua
    # pel fallback PG-1 (ruleset extern). Degradació gràcil INTENCIONAL, no descuit.
    n_regles = None
    if canvia_joc:
        from django.db import transaction
        from fhort.models_app.services import (materialize_model_grading_rules,
                                               origen_mgr_des_de_ruleset)
        with transaction.atomic():
            n_regles = materialize_model_grading_rules(
                model, model.grading_rule_set.regles.all(),
                origen=origen_mgr_des_de_ruleset(model.grading_rule_set),
                joc_anterior=grs_abans_obj)
        # R1 — el retorn d'aquesta funció es DESCARTAVA. Materialitzar 0 regles (ruleset buit)
        # esborrava les residents i tornava un 200 mut: exactament el que va buidar el 163.
        # Amb la validació D1 això ja no hauria de poder passar per l'endpoint; si passa igual
        # (dades tocades per un altre camí), que quedi rastre i que la resposta ho digui.
        # 6.1 — «0 materialitzades» ja NO vol dir «sense residents»: pot voler dir que totes les
        # del joc queien sobre POMs que el tècnic havia escrit a mà, i que per tant hi manen. Un
        # rastre que menteix és pitjor que cap rastre, i aquí el matís canvia el diagnòstic.
        if n_regles == 0:
            import logging
            _cua = (f"— totes les del joc cauen sobre POMs amb regla MANUAL preservada "
                    f"({len(poms_preservats)}), que és qui gradua."
                    if poms_preservats else
                    "— el model queda SENSE regles residents.")
            logging.getLogger(__name__).warning(
                f"update_model_step2: model {model.codi_intern} (id={model.id}) ha "
                f"materialitzat 0 regles des del GradingRuleSet {model.grading_rule_set_id} "
                + _cua
            )
    # D-31.4 · EL RASTRE. La confirmació és una decisió, i una decisió que destrueix feina ha de
    # deixar constància que sobrevisqui a la sessió del navegador. Watchpoint i no un log: el log
    # el llegeix qui el va a buscar, i el Watchpoint viatja AMB EL MODEL a través dels gates, que
    # és on el trobarà el tècnic que d'aquí a un mes es pregunti on han anat les seves regles.
    # Neix `open` (default del model) i el tanca qui hagi comprovat que la graduació nova és bona.
    n_residents, per_origen = residents_perdudes
    # 6.1 — el rastre ha de dir el que ha passat, no el que hauria passat abans. `n_residents`
    # és el recompte PREVI (i es queda: és el que hi havia); el que s'ha destruït de debò és
    # aquest, i el que s'ha salvat surt a part. Sense aquesta resta, el Watchpoint hauria
    # començat a dir «esborrades 2» d'un gest que n'ha esborrat 1.
    n_preservades = len(poms_preservats)
    n_esborrades = n_residents - n_preservades
    # …i la condició mira les ESBORRADES, no les que hi havia: un Watchpoint existeix per
    # respondre «on han anat les meves regles», i si no n'ha anat cap enlloc no hi ha res a
    # respondre. Abans de 6.1 les dues xifres eren sempre la mateixa i la distinció no existia.
    if n_esborrades:
        from fhort.models_app.models import Watchpoint
        _perfil = getattr(request.user, 'profile', None)
        _detall = ' · '.join(f'{n} {o}' for o, n in sorted(per_origen.items()))
        if motiu_watchpoint == 'desacoblat_graduacio':
            # La segona porta deixa el MATEIX rastre que la primera: el tècnic que d'aquí a un
            # mes es pregunti on han anat les seves regles ha de trobar la resposta al model,
            # tant si les va matar un canvi de joc com si les va matar un «Sense graduació».
            _text = (f"Desacoblada la graduació del model (joc #{grs_abans}), esborrant "
                     f"{n_residents} regles pròpies ({_detall}). El model queda SENSE "
                     f"graduació. Verifica-ho abans d'entregar.")
            _dades = {
                'tipus': 'desacoblat_graduacio',
                'grading_rule_set_id': grs_abans,
                'residents': n_residents,
                'per_origen': per_origen,
                'imported': per_origen.get('IMPORTED', 0),
            }
        else:
            _text = (f"Assignat el joc de regles «{model.grading_rule_set.nom}» "
                     f"(#{model.grading_rule_set_id}) esborrant {n_esborrades} regles pròpies "
                     f"del model ({_detall})."
                     + (f" {n_preservades} escrites a mà (MANUAL) s'han conservat."
                        if n_preservades else '')
                     + " Verifica la graduació abans d'entregar.")
            _dades = {
                'tipus': 'esborrat_residents',
                'grading_rule_set_id': model.grading_rule_set_id,
                'grading_rule_set_nom': model.grading_rule_set.nom,
                # `residents` = les que hi HAVIA (l'acta d'abans, com sempre).
                # `esborrades`/`preservades` = què n'ha passat (6.1).
                'residents': n_residents,
                'esborrades': n_esborrades,
                'preservades': n_preservades,
                'per_origen': per_origen,
                'imported': per_origen.get('IMPORTED', 0),
                'regles_materialitzades': n_regles,
            }
        Watchpoint.objects.create(model=model, task=None, created_by=_perfil,
                                  text=_text, dades=_dades)

    return Response({
        'id': model.id,
        'codi_intern': model.codi_intern,
        'regles_materialitzades': n_regles,
        # Que la resposta ho digui: qui ha confirmat ha de veure què ha passat de debò, no
        # només que la crida ha anat bé. 6.1: `residents_esborrades` passa a ser el que s'ha
        # esborrat DE DEBÒ, i les salvades van a la clau nova.
        'residents_esborrades': n_esborrades,
        'residents_preservades': n_preservades,
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
        # FONT ÚNICA (22/08) — el codi i els noms del CATÀLEG surten del resolutor
        # (`pom/nomenclatura.py`: ÀLIES > TENANT > GLOBAL). L'àlies del client viatja a part
        # (`camps_de`, tres línies més avall) perquè la pantalla el pugui distingir.
        _noms = noms_de(pom)
        result.append({
            'pom_id': pom.id,
            'pom_code': codi_de(pom),
            'nom_en': _noms['nom_en'],
            'nom_ca': _noms['nom_ca'],
            'abbreviation': abreviatura_de(pom),
            'categoria': categoria_de(pom),
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

    # FASE_3/C1-ins — la clau del mapa de valors de l'item és COMPLETA. Aquí neix la capa i
    # la instància del model (decisió D6: neixen a l'ITEM), i per `pom_id` sol dues
    # pertinences germanes del mateix POM es fonien en una i l'última llegida donava el valor
    # a totes dues. El `GarmentPOMMap` diu QUÈ es reclama i quantes vegades; l'`ItemBaseMeasurement`
    # diu amb quin valor. Els dos parlen la mateixa clau o la sembra menteix.
    if base_set is not None:
        ibms = {(i.pom_id, i.capa, i.instancia): i
                for i in ItemBaseMeasurement.objects.filter(base_set=base_set)}
        talla_item = (getattr(base_set.base_size_definition, 'etiqueta', None) or '').strip()
    else:
        # CAMÍ LLEGAT (conviu mentre no tots els mons tinguin set). Només s'hi cau si el món del
        # model no en té cap, i NOMÉS si l'item és inequívoc: amb 0 o 1 set, les mesures de
        # l'item parlen d'un sol món i el guard V1 les sap jutjar. Amb 2+ sets NO endevinem quin
        # món val — se sembra la pertinença i cap valor, que és el que diu la llei 7.
        sets_item = ItemBaseSet.objects.filter(garment_type_item=item).count()
        if sets_item <= 1:
            ibms = {(i.pom_id, i.capa, i.instancia): i
                    for i in ItemBaseMeasurement.objects.filter(garment_type_item=item)}
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
            # La clau completa surt del `GarmentPOMMap`, que és el portador de la pertinença.
            ibm = ibms.get((m.pom_id, m.capa, m.instancia))
            # P1 — amb talles divergents un valor de plantilla és una mesura FALSA: la pertinença
            # sí es materialitza (fila TEMPLATE buida), el valor no viatja.
            has_value = (not talla_divergent) and ibm is not None and ibm.base_value_cm is not None
            existing = BaseMeasurement.objects.filter(
                model=model, pom=m.pom, capa=m.capa, instancia=m.instancia).first()

            if existing is None:
                if has_value:
                    BaseMeasurement.objects.create(
                        model=model, pom=m.pom,
                        capa=m.capa, instancia=m.instancia,
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
                        capa=m.capa, instancia=m.instancia,
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

    # ── SET-2/T10 · LES PECES VIATGEN PRIMER, i abans que res que les anomeni.
    #
    # `BaseMeasurement.garment` ja viatja des de T5 («la còpia COPIA»), però el codi que
    # hi ha a dins no volia dir res al destí: `ModelGarment` no es copiava, o sigui que
    # el model copiat es quedava amb mesures de la peça '02' i CAP peça '02' — codis
    # orfes, i amb ells els overrides de run/ruleset/talla base de la peça, que
    # silenciosament queien als del model.
    #
    # VIATGEN AMB QUALSEVOL DELS TRES FLAGS que les poden anomenar (run, valors,
    # graduació) i no amb un de sol: són l'ESQUELET del model —quines prendes té—, i
    # copiar-ne les mesures o la configuració sense elles és el que fabrica l'orfe.
    # `copy_files` no hi entra: un croquis no parla de peces.
    #
    # Idempotent per `(model, codi)`, com la unicitat: una segona còpia ACTUALITZA la
    # peça existent al destí en comptes de petar. No s'esborra cap peça que el destí
    # tingui i l'origen no: esborrar-la deixaria òrfenes les SEVES mesures, i aquesta
    # porta és MUDA (no demana permís) — el que no sap desfer, no ho desfà.
    if copy_run or copy_values or copy_grading:
        for peca in src.garments.all():
            ModelGarment.objects.update_or_create(
                model=dst, codi=peca.codi,
                defaults={
                    'nom': peca.nom,
                    'ordre': peca.ordre,
                    # Els overrides van SENCERS, NULL inclòs: un NULL no és «no ho sé»,
                    # és «hereta del model», i és una declaració tan copiable com
                    # qualsevol altra. Copiar-ne només els informats convertiria una
                    # herència en una declaració.
                    'size_system_id': peca.size_system_id,
                    'grading_rule_set_id': peca.grading_rule_set_id,
                    'size_run_model': peca.size_run_model,
                    'base_size_label': peca.base_size_label,
                },
            )

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
            # FASE_3/C1-ins — la còpia COPIA: els eixos surten de la fila d'origen, no de cap
            # literal. Un model copiat d'un altre ha de tenir les mateixes mesures, i «les
            # mateixes» inclou de quina matèria i de quina repetició parla cadascuna.
            existent = BaseMeasurement.objects.filter(
                model=dst, pom_id=bm.pom_id, capa=bm.capa, instancia=bm.instancia,
                garment=bm.garment).first()

            if existent is None:
                nova = BaseMeasurement(
                    model=dst, pom_id=bm.pom_id,
                    # SET-2/T5 — el tercer eix segueix el mateix rastre: la còpia COPIA, i
                    # «les mateixes mesures» inclou de quina PRENDA parla cadascuna.
                    capa=bm.capa, instancia=bm.instancia, garment=bm.garment,
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
                                                   origen_mgr_des_de_ruleset,
                                                   poms_manual_a_preservar)
            from fhort.models_app.services_garment import valor_efectiu
            # 6.1 — el joc que el DESTÍ tenia, capturat abans del `save()` (a partir d'aquí ja
            # porta el de l'origen). Aquesta porta és MUDA —no compta residents, no demana
            # permís, no deixa Watchpoint—, i per això la preservació hi val doble: és l'única
            # protecció que hi arriba.
            grs_dst_abans = dst.grading_rule_set
            n_preservades_dst = len(poms_manual_a_preservar(dst, grs_dst_abans))
            dst.grading_rule_set_id = src.grading_rule_set_id
            dst.save(update_fields=['grading_rule_set'])
            grading_set = src.grading_rule_set_id
            # SET-2/T10 — UNA MATERIALITZACIÓ PER PEÇA. `materialize_model_grading_rules`
            # ja fa el wipe per `(model, garment)` des de T3, però aquí se li deia una
            # sola vegada amb el `garment` per defecte: només la MARE quedava sembrada, i
            # les peces del model copiat es quedaven sense cap regla resident —mudes— o,
            # pitjor, amb les que el destí ja tingués d'una còpia anterior.
            #
            # Cada peça se sembra des del SEU joc EFECTIU (`valor_efectiu`, el punt únic
            # de D5): si la peça no en declara cap, hereta el del model —que és el que
            # acabem de copiar de l'origen— i queda sembrada igual que la mare.
            n_regles = materialize_model_grading_rules(
                dst, src.grading_rule_set.regles.all(),
                origen=origen_mgr_des_de_ruleset(src.grading_rule_set),
                joc_anterior=grs_dst_abans)
            for peca in dst.garments.all():
                joc_peca = valor_efectiu(dst, peca, 'grading_rule_set')
                if joc_peca is None:
                    continue
                n_regles += materialize_model_grading_rules(
                    dst, joc_peca.regles.all(),
                    origen=origen_mgr_des_de_ruleset(joc_peca),
                    joc_anterior=grs_dst_abans, garment=peca.codi)
            if n_preservades_dst:
                warnings.append(
                    f"{n_preservades_dst} regles de graduació escrites a mà (MANUAL) al model "
                    f"de destí s'han conservat i manen sobre les del joc copiat.")
            if n_regles == 0 and not n_preservades_dst:
                # R1 (el forat que va buidar el 163): un ruleset buit esborra les residents i
                # torna un 200 mut. Aquí no: queda al log i a la resposta.
                # 6.1 — amb MANUAL preservades, «0 materialitzades» no vol dir «sense
                # graduació»: vol dir que mana el tècnic. El warning d'això ja l'ha posat la
                # preservació més amunt, i repetir-hi «SENSE regles residents» seria mentir.
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
@bat_escriptura(SUP_MESURES)
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
        # Atòmic (B4). F1.2 — «tancar taula» tanca la TAULA (close_base), no la tasca: el Stop
        # humà és l'únic que tanca (D-2). Aquí la tasca només s'assegura oberta.
        with transaction.atomic():
            sf = get_or_create_size_fitting(model, request.user.id)
            result = close_base(sf.id, request.user.id)
            pom_task = _assegura_pom_task_oberta(model, profile)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error closing table")
        return Response({'error': str(e)}, status=500)

    return Response({'sf_id': sf.id, 'pom_task': pom_task, **result})


def _assegura_pom_task_oberta(model, profile):
    """F1.2 · DESAR NO TANCA MAI (D-2). Desar assegura que la tasca està OBERTA.

    Fins avui aquesta funció tancava la tasca `pom` a `Done` a cada desat, i el resultat mesurat
    era el ping-pong: 28 de 49 transicions `→Done` eren repeticions sobre una tasca ja tancada, i
    tot el que el tècnic feia entre «Gravar» i el gest següent no tenia rellotge (la feina seguia,
    la tasca no). El Stop humà és ara l'ÚNIC que tanca.

    Obrir-si-cal no és un efecte secundari: **és el batec fort**. Qui desa està treballant, i una
    tasca `Pending`/`Paused` que rep un desat ha d'estar `InProgress`.

    Retorna `{'oberta': bool, 'reason': str|None, 'task_id': int|None}`. Cap consumidor de
    frontend llegeix aquest dict (verificat); qui el llegeix és `gravar_pom_view`, per al seu
    gate `no_pom_task`.
    """
    from fhort.tasks.services_c import TransitionError, transition_task
    from fhort.tasks.services_r import tasca_vigent

    # F1.0 — abans: `.order_by('id').first()`, o sigui LA MÉS ANTIGA. Amb una ronda oberta això
    # tancava la tasca de la ronda 1 mentre el tècnic treballava la 2 (§S-4 de la diagnosi).
    task = tasca_vigent(model, 'pom')
    if not task:
        return {'oberta': False, 'reason': 'no_pom_task', 'task_id': None}
    if task.status == 'InProgress':
        return {'oberta': True, 'reason': 'ja_oberta', 'task_id': task.id}

    # Pending/Paused → oberta. Done → reobertura (rectificació): és una decisió del tècnic que
    # ha tornat a desar sobre feina tancada, i el log l'ha de veure com el que és.
    try:
        transition_task(task, 'InProgress', profile)
    except TransitionError as e:
        # L'única paret real aquí és l'albarà emès (D-5): no es reobre, s'obre una RONDA. Es
        # retorna el `code` perquè la porta HTTP pugui dir-ho i el front oferir la sortida.
        return {'oberta': False, 'reason': getattr(e, 'code', None) or 'transicio_refusada',
                'task_id': task.id, 'error': str(e)}
    return {'oberta': True, 'reason': 'oberta', 'task_id': task.id}


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
    ).select_related('pom', 'pom__pom_global').order_by(
        'ordre', 'pom__codi_client', 'capa', 'instancia')

    # C4 — EL MAPA DE GRADUATS CREIX A LA IDENTITAT SENCERA.
    #
    # Aquesta vista MAI no va tenir àncora al queryset: les files sempre han sortit totes
    # (una per `BaseMeasurement`). El seu defecte era l'altre —i pitjor de veure—: `graded_by_pom`
    # i `deltas` són diccionaris per `pom_id` pelat, o sigui que amb dues germanes la pantalla
    # ensenyava LES DUES FILES i totes dues llegien la mateixa entrada. Una de les dues sortia
    # amb el graduat i el delta de la seva germana com si fossin seus.
    #
    # Absència vs. valor equivocat: les cinc superfícies ancorades AMAGAVEN; aquesta COL·LAPSAVA.
    # És pitjor perquè no hi ha res a la pantalla que suggereixi que falta o sobra res.
    graded_by_pom = {}
    # T4 — declarades FORA del `try`: si la resolució de la versió peta, la resposta ha de sortir
    # igualment amb la data a `None`, no amb un `NameError` (mateixa acta que `_regla_de`).
    grading_version_data = None
    grading_version_number = None
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
                # Q8-ter/T4 — LA DATA DE LA CORBA VIGENT. La fitxa ha de dir de QUIN DIA és cada
                # taula, i la de graduació no en té cap altra: la seva font és aquesta versió, i
                # `data` és quan es va crear (l'última propagació la torna a crear —
                # `bump_grading_version_and_generate`—, o sigui que és la marca de l'últim canvi).
                # Camp ADDITIU: `gv` ja es resolia aquí mateix per omplir `graded_by_pom`, o sigui
                # que no hi ha ni una consulta nova.
                grading_version_data = gv.data.isoformat() if gv.data else None
                grading_version_number = gv.version_number
                for spec in GradedSpec.objects.filter(grading_version=gv):
                    # SET-2/T6a — l'eix de la peça entra al mapa alhora que a la `clau` de la
                    # fila (just a sota): si un cresqués i l'altre no, la fila de la 02
                    # buscaria amb quatre trams en un mapa de tres i es quedaria sense corba
                    # graduada, o —pitjor— dues peces es disputarien la mateixa entrada i una
                    # ensenyaria la corba de l'altra com si fos seva.
                    ident = (spec.pom_id, spec.capa, spec.instancia, spec.garment)
                    if ident not in graded_by_pom:
                        graded_by_pom[ident] = {}
                    graded_by_pom[ident][spec.size_label] = (
                        float(spec.graded_value_cm) if spec.graded_value_cm is not None else None
                    )
    except Exception:
        pass

    # Règim per PEÇA I POM (logica/increments/break) per a l'editor propagat: resolutor canònic
    # (ModelGradingRule resident → fallback GradingRule del rule_set), batched una sola vegada.
    #
    # ✅ SET-2/F1 · Q1-bis — LA CINQUENA BOCA, censada i tancada. L'acta de
    # `_load_grading_rules` (`pom/services.py:774-806`) n'enumerava els consumidors i deia que
    # la línia que separa els adaptats dels que es queden NO és l'app on viuen sinó **si
    # escriuen**. Aquesta es va classificar com a presentació, i no ho és del tot: aquesta
    # taula és la FONT de l'Escalat, i el que la pantalla pinta és el que el tècnic edita
    # després. Amb la llei de la mare a la fila de la 02, la pantalla i el motor
    # (`generate_graded_specs`, que ja reparteix per peça des de T4) deien coses diferents
    # sobre la mateixa fila.
    # ⚠️ `_regla_de` s'importa FORA del `try`: és una funció pura i, si quedés a dins, un
    # error de càrrega de les regles la deixaria sense definir i la construcció de files
    # petaria amb un `NameError` — canviar un règim buit per un 500.
    from fhort.pom.services import _regla_de
    rules_by_garment = {}
    try:
        from fhort.pom.services import _load_grading_rules_per_garment
        rules_by_garment = _load_grading_rules_per_garment(model)
    except Exception:
        rules_by_garment = {}
    # P0.5d — per poder dir si la regla que serveix cada fila viu al MODEL o al JOC. El
    # resolutor torna l'una o l'altra classe i aquí és l'únic lloc on encara se sap.
    from fhort.models_app.models import ModelGradingRule

    # LES REGLES QUE AQUESTA TAULA DIU SÓN LES DEL MODEL, I NOMÉS LES SEVES (31/07).
    #
    # `_load_grading_rules` ja respon exactament això: ModelGradingRule resident amb prioritat i
    # fallback al `grading_rule_set` que el MODEL té assignat. Res més s'hi fusiona.
    #
    # Aquí hi va haver, i ja no hi és, un fallback que omplia els forats amb el ruleset del
    # catàleg (l'item primer, després també el SizingProfile). El QA del model 1302 va ensenyar
    # el preu: un model creat expressament SENSE graduació ensenyava «CH · LINEAR +2,0/+3,0 @XS»
    # —la regla d'un altre— i, com que la taula reenviava el que pintava, desar les mesures
    # l'hauria materialitzada sense que ningú l'acceptés. LLEI: BD neta = taula neta.
    #
    # La proposta del catàleg NO s'ha perdut: viu al pas de Graduació (`GraduacioPanel`), que és
    # on hi ha un «Usar aquest joc» al davant i on triar és un acte, no un efecte secundari.

    def _flt(v):
        return float(v) if v is not None else None

    # ── TRAM E · LES TALLES SENSE VALOR STEP, DERIVADES AQUÍ I NO EMMAGATZEMADES ─────────────
    # `GradedSpec` és sortida pura i no té camp d'origen (llei). La marca de «aquí hi ha el
    # valor de la talla base copiat» no és una dada de l'spec: és una propietat de la REGLA
    # (STEP + `valors_step` que no cobreix el camí fins a aquella talla), i per tant es deriva
    # al LECTOR — l'alternativa de menys radi de les quatre censades.
    #
    # Es deriva AQUÍ i no al front perquè el predicat ha de ser EL MATEIX que el del motor, i el
    # del motor és `step_delta_acumulat`. Amb un mirall a JavaScript, la cel·la vermella i la
    # cel·la copiada podrien deixar de ser la mateixa el dia que una de les dues canviés — i
    # justament aquest és el cas on el model pot no fabricar la talla que falta al camí.
    from fhort.pom.grading_utils import step_delta_acumulat
    try:
        from fhort.pom.services import escala_del_model as _escala
        _run_model_e, _run_sist_e, _pos_e, _base_idx_e = _escala(model)
    except (ValueError, AttributeError):
        _run_model_e, _run_sist_e, _pos_e, _base_idx_e = [], [], None, None

    def _talles_step_sense_valor(rule):
        """Les talles del run del MODEL que sortiran amb el valor de la base copiat."""
        if rule is None or getattr(rule, 'logica', None) != 'STEP' or _pos_e is None:
            return []
        fora = []
        for etiqueta in _run_model_e:
            try:
                idx = _pos_e(etiqueta)
            except (ValueError, KeyError):
                continue
            _total, falta = step_delta_acumulat(rule, _run_sist_e, _base_idx_e, idx)
            if falta is not None:
                fora.append(etiqueta)
        return fora

    # C3 — nomenclatura del CLIENT del model, mateix resolutor que la resta de superfícies.
    from fhort.pom.identitat import clau_mesura
    alias_by_pom = alies_per_pom(model.customer_id)

    rows = []
    for bm in base_measurements:
        pom = bm.pom
        # ✅ SET-2/F1 · Q1-bis — LA REGLA DE LA SEVA PEÇA. Era `rules_by_pom.get(pom.id)`:
        # amb la mare i la 02 compartint POM, les dues files rebien la MATEIXA llei i el
        # contenidor de la 02 ensenyava el règim, la Δ i el break de la mare. Aquesta taula
        # alimenta l'Escalat i la CONSULTA de Mesures, o sigui que era la boca que feia que
        # la pantalla i el motor no diguessin el mateix.
        rule = _regla_de(rules_by_garment, pom.id, bm.garment)
        rows.append({
            'id': bm.id,
            'ordre': bm.ordre,
            'pom_id': pom.id,
            # C4 — els dos eixos al contracte. Aquesta taula sempre ha pintat una fila per
            # germana; el que li faltava era dir QUINA és cada fila, i és el que fan aquests
            # dos camps més la `clau` de sota (la que enllaça amb `deltes`).
            'capa': bm.capa,
            'instancia': bm.instancia,
            'clau': clau_mesura(pom.id, bm.capa, bm.instancia, bm.garment),
            # SET-2/T6a — l'eix de la fila al contracte, al costat dels dos de germanor.
            'garment': bm.garment,
            # FONT ÚNICA (22/08) — el codi del CATÀLEG resolt (tenant > global); l'àlies
            # del client segueix viatjant a part, a `camps_de`, que és el que permet al front
            # dir-los amb paraules diferents.
            'pom_code': codi_de(pom),
            **camps_de(alias_by_pom, pom.id),
            'nom_fitxa': bm.nom_fitxa or '',
            # Sprint NOMS-POM — el BATEIG d'aquest model, CRU i al costat del catàleg
            # (`nom_en`/`nom_ca`, que no es toquen): '' vol dir «no batejat, mana el catàleg».
            # La cascada la resol qui pinta, que és qui sap si mostra un input amb placeholder o
            # un text pla. Camps NOUS: cap camp existent canvia de valor ni de nom.
            #
            # 31/07 — hi arriben ARA. El paquet del bateig els va posar a `base_stages_view` i a
            # `wizard_views.base_measurements_view`, però NO aquí, i aquesta és justament la
            # taula que alimenta la pantalla d'entrada de Mesures: la cel·la del nom hi sortia
            # sense res a editar perquè el payload no li portava el bateig.
            'nom_canonic_model': bm.nom_canonic_model or '',
            'nom_traduit_model': bm.nom_traduit_model or '',
            'nom_en': noms_de(pom)['nom_en'],
            'nom_ca': noms_de(pom)['nom_ca'],
            'abbreviation': abreviatura_de(pom),   # FONT ÚNICA (22/08)
            'base_value_cm': float(bm.base_value_cm) if bm.base_value_cm is not None else None,
            'is_key': bm.is_key,
            'origen': bm.origen,
            'notes': bm.notes or '',
            'graded': graded_by_pom.get((pom.id, bm.capa, bm.instancia, bm.garment), {}),
            # Règim (additiu; consumidors antics ignoren camps desconeguts).
            'logica': getattr(rule, 'logica', None) if rule else None,
            'increment_base': _flt(getattr(rule, 'increment_base', None)) if rule else None,
            'increment_break': _flt(getattr(rule, 'increment_break', None)) if rule else None,
            'talla_break_label': getattr(rule, 'talla_break_label', None) if rule else None,
            # TRAM F — els intervals. Aquest payload és el punt d'entrada de 5 de les 7
            # superfícies visuals de la regla: si el relleu no hi surt, la pantalla que l'edita
            # no el pot ni ensenyar ni tornar a desar sencer.
            'breaks': (getattr(rule, 'breaks', None) or []) if rule else [],
            # TRAM E — les talles d'aquesta fila que porten el valor de la base COPIAT (regla
            # STEP sense valor). Derivat, mai desat: v. `_talles_step_sense_valor`.
            'step_base_copiada': _talles_step_sense_valor(rule),
            # P0.5d — D'ON VE LA REGLA, perquè la superfície de Graduació ho ha de poder dir.
            #
            # CALEN ELS DOS CAMPS, i el primer cop només en vaig posar un. `origen` sol MENTIA
            # al cas de fallback: `pom.GradingRule` —la regla del JOC— **no té camp `origen`**
            # (verificat a `pom/models.py:1230`), o sigui que quan el model gradua de debò pel
            # joc, `getattr` retorna `None`, i el front llegia «no és MANUAL... doncs del model».
            # Just al revés. Provocat en transacció sobre el model 169: 13 files resoltes pel
            # joc, totes retornant `regla_origen=None` i pintant «del model».
            #
            # El senyal fiable és DE QUINA TAULA ha sortit la regla, que és una cosa que aquest
            # codi sap del cert perquè `_load_grading_rules` retorna l'una o l'altra:
            #   · `regla_es_resident=False` → ve del JOC en directe (fallback, cap resident)
            #   · `regla_es_resident=True`  → viu al MODEL, i llavors `regla_origen` diu si
            #                                 l'ha escrita algú (MANUAL) o si és una còpia
            #                                 materialitzada del joc (CLIENT_RUN/CANONICAL/…)
            #   · `None` a tots dos          → fila sense regla (les «—»)
            #
            # Camps additius: cap consumidor existent els llegeix i cap camp canvia de valor.
            'regla_origen': getattr(rule, 'origen', None) if rule else None,
            'regla_es_resident': isinstance(rule, ModelGradingRule) if rule else None,
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
    #
    # C4 — LA CLAU DEL DICT ÉS LA IDENTITAT DE LA MESURA, NO EL POM. Amb `str(pom_id)`, dues
    # germanes escrivien a la mateixa entrada i la segona esborrava el delta de la primera:
    # `deltes` tenia dues entrades per a quatre files, i dues files de la pantalla ensenyaven
    # un delta que no era el seu. La clau ve de `pom.identitat.clau_mesura`, la mateixa forma
    # que fa servir `pom/grading_views.cells` — l'altre lector que publica la mesura com a
    # clau d'objecte JSON.
    deltas = {}
    for r in rows:
        values = [_size_value(r, s) for s in sizes_with_data]
        values = [v for v in values if v is not None]
        if len(values) >= 2:
            increments = [values[i + 1] - values[i] for i in range(len(values) - 1)]
            deltas[r['clau']] = round(sum(increments) / len(increments), 2)
        else:
            deltas[r['clau']] = None

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
        # TRAM F — EL RUN DEL SISTEMA, i tanca una frontera que amb un sol break ja coixejava.
        # El motor resol el relleu contra el run del SISTEMA (llei S24b) però la pantalla només
        # sabia oferir el run del MODEL: un interval que acabi a una talla que el sistema té i
        # el model no fabrica —que és la forma canònica de tota regla d'1 break llegida com a
        # interval— no era ni triable ni re-desable sense perdre'l. Amb el run del sistema al
        # payload, el picker pot oferir exactament el que el motor sap llegir.
        'run_sistema': _run_sist_e,
        'sizes_amb_dades': sizes_with_data,
        'deltes': deltas,
        'rows': rows,
        'total_poms': len(rows),
        'tancat': tancat,
        # T4 — additius: cap consumidor existent els llegeix i cap camp canvia de valor.
        'grading_version_data': grading_version_data,
        'grading_version_number': grading_version_number,
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
    # C4/BLOC 1-TER — `keep_mesures` és la mateixa llista amb la IDENTITAT de cada fila
    # (`{pom_id, capa, instancia}`) en comptes del `pom_id` pelat. Els dos conviuen: v.
    # `_poda_mesures` per què el vell no es pot reinterpretar.
    keep_mesures = request.data.get('keep_mesures', None)
    if not measurements and keep_pom_ids is None and keep_mesures is None:
        return Response({'error': 'measurements és obligatori'}, status=400)

    from fhort.pom.models import POMMaster
    from fhort.models_app.models import BaseMeasurement

    created = updated = deactivated = 0
    errors = []

    # C4/BLOC 1-BIS — mateix guard que a `gravar_pom_view`: dues entrades del MATEIX request
    # que escriuen a la mateixa fila són un error de petició, no una escriptura. Executar-ho
    # seria «l'última guanya» dins del bucle.
    identitats = set()
    for m in measurements:
        pom_id = m.get('pom_id')
        if not pom_id:
            continue
        ident = (int(pom_id),) + _identitat_de_mesura(m)
        if ident in identitats:
            capa, instancia = ident[1], ident[2]
            return Response({'errors': [
                f'POM {pom_id} (capa={capa or "exterior"}, instància={instancia or "única"}): '
                'la petició porta dues mesures per a la mateixa fila i no es pot decidir '
                'quina val'
            ]}, status=400)
        identitats.add(ident)

    with transaction.atomic():
        for m in measurements:
            pom_id = m.get('pom_id')
            value = m.get('base_value_cm')
            if not pom_id or value is None:
                errors.append(f'pom_id i base_value_cm obligatoris')
                continue
            try:
                pom = POMMaster.objects.get(id=pom_id)
                # C4/BLOC 1-BIS — la fila es resol per la IDENTITAT SENCERA (els eixos vénen
                # del payload; qui no els digui rep el literal de sempre). Amb el literal fix
                # que hi havia, dues germanes queien sobre la mateixa fila.
                capa, instancia, garment = _identitat_de_mesura(m)
                # 🔒 La mateixa llei que a `gravar_pom_view`: fins a una etiqueta per eix.
                mal = MeasurementInstance.error_de_combinacio(instancia)
                if mal:
                    errors.append(f'POM {pom_id}: {mal}')
                    continue
                # L'ORIGEN I LES TOLERÀNCIES NO SÓN EFECTE SECUNDARI D'AQUESTA ESCRIPTURA
                # (v. `_procedencia_de_mesura`): abans anaven als `defaults` de l'upsert i
                # això les reescrivia a CADA fila del payload, canviés el valor o no.
                bm = BaseMeasurement.objects.filter(
                    model=model, pom=pom, capa=capa, instancia=instancia,
                    garment=garment).first()
                es_nova = bm is None
                if es_nova:
                    bm = BaseMeasurement(model=model, pom=pom, capa=capa,
                                         instancia=instancia, garment=garment)
                valor_nou = float(value)
                _procedencia_de_mesura(bm, m, pom, valor_nou, es_nova)
                bm.base_value_cm = valor_nou
                bm.notes = m.get('notes', '')
                bm.nom_fitxa = m.get('nom_fitxa', '') or ''
                # Re-entrar un valor reactiva una fila prèviament eliminada.
                bm.is_active = True
                bm.save()
                if es_nova: created += 1
                else: updated += 1
            except POMMaster.DoesNotExist:
                errors.append(f'POMMaster {pom_id} no trobat')

        if keep_mesures is not None or keep_pom_ids is not None:
            # C4/BLOC 1-TER — la poda resol per FILA quan el client diu els eixos, i conserva
            # el comportament d'abans quan no els diu. L'argument sencer viu a `_poda_mesures`,
            # que és també el que fa servir `gravar_pom_view`: dues portes, una sola llei.
            # SET-2/#12b — `garments` (opcional): l'abast EXPLÍCIT de la poda, per al
            # contenidor que es desa buit i no pot anomenar cap fila. V. `_poda_mesures`.
            deactivated = _poda_mesures(model, keep_mesures, keep_pom_ids,
                                        _abast_de_poda(request.data))

    # NOTE: set-measurements només fa upsert de BaseMeasurement (+ el log via signal). La generació
    # de GradedSpec viu EXCLUSIVAMENT a generar-grading → generate_graded_specs (l'únic camí que
    # respecta ModelGradingOverride). El grading inline d'aquí estava trencat (rule.increment_cm no
    # existeix → delta 0) i clobberava els overrides; eliminat.
    return Response({'created': created, 'updated': updated, 'deactivated': deactivated,
                     'errors': errors},
                    status=201 if not errors else 207)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@bat_escriptura(SUP_MESURES)
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
    # C4/BLOC 1-TER — v. `_poda_mesures`: la llista amb els eixos poda per FILA; la de
    # `pom_id` pelats conserva el comportament d'abans.
    keep_mesures = request.data.get('keep_mesures', None)
    if not measurements and keep_pom_ids is None and keep_mesures is None:
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

    from fhort.pom.nomenclatura import avisos_de_nomenclatura

    errors = []
    # DECISIÓ 8 · L'HOMONÍMIA ES DIU, NO ES BARRA. Les files que arriben es recullen amb el seu
    # àmbit ja normalitzat i, quan tot el payload s'ha llegit, `avisos_de_nomenclatura` en treu
    # els grups ambigus. La llista és d'AVISOS i no d'errors a posta: no talla el bucle, no
    # canvia el codi de resposta i no decideix res — viatja al 200 al costat del que s'ha desat.
    nomenclatures = []
    fora_rang = []
    prepared = []
    identitats = set()
    # L'ÍNDEX DEL PAYLOAD, no el de `prepared`: la referència que viatja a l'avís ha d'apuntar a
    # la fila TAL COM EL CLIENT LA VA ENVIAR, i `prepared` en descarta (rang, duplicats). Que en
    # un 200 les dues llistes coincideixin —qualsevol descart torna 400 o 422 abans d'arribar-hi—
    # és una casualitat d'avui, no un contracte.
    for _ref, m in enumerate(measurements):
        pom_id = m.get('pom_id')
        value = _to_float(m.get('base_value_cm'), 'base_value_cm', errors)
        if not pom_id or value is None:
            errors.append('pom_id i base_value_cm obligatoris')
            continue
        # GUARDA DE RANG FÍSIC (30/07) — punt únic compartit amb `escalat_ajustar_talla_view`,
        # les DUES portes per on entra una mesura al backend. Cobreix el 0 que aquí ja es
        # rebutjava (D2: el motor el tracta com a «el POM no existeix» i la mesura desapareix
        # de la taula sense dir-ho a ningú) i, ara, també el negatiu i el 22224,7 del POP.
        fora = mesura_fora_de_rang(value)
        if fora:
            fora_rang.append(f'POM {pom_id}: {fora}')
            continue

        # C4/BLOC 1-BIS — LA IDENTITAT DE LA FILA SURT DEL PAYLOAD (v. `_identitat_de_mesura`).
        capa, instancia, garment = _identitat_de_mesura(m)
        # 🔒 ELS DOS EIXOS DE LA POSICIÓ (22-23/08): fins a UNA etiqueta per eix. `left`+`back`
        # és una germana legítima; `left`+`right` i `front`+`back` no ho són. Es valida AQUÍ i
        # no només a la UI: aquesta és la porta, i una pantalla no és una barana.
        _mal = MeasurementInstance.error_de_combinacio(instancia)
        if _mal:
            errors.append(f'POM {pom_id}: {_mal}')
            continue
        ident = (int(pom_id), capa, instancia, garment)
        if ident in identitats:
            # 🔴 DUES ENTRADES DEL MATEIX REQUEST QUE ESCRIUEN A LA MATEIXA FILA. Executar-ho
            # seria «l'última guanya» dins del propi bucle —el valor de la primera no arribaria
            # mai a la BD i ningú no ho sabria—, i és exactament el mode de fallada que aquest
            # tram existeix per matar. No es tria: es rebutja la petició sencera.
            errors.append(
                f'POM {pom_id} (capa={capa or "exterior"}, instància={instancia or "única"}): '
                'la petició porta dues mesures per a la mateixa fila i no es pot decidir '
                'quina val'
            )
            continue
        identitats.add(ident)

        # 🚨 AQUÍ HI HAVIA UN GUARDA D'ABAST **CUSTOMER**, I ERA LA PREGUNTA EQUIVOCADA.
        #
        # Cridava `colisio_de_codi(model.customer_id, nomen)` i refusava la petició sencera amb
        # un 400 si el nom de fitxa ja era un `CustomerPOMAlias` d'un ALTRE POM del client. Però
        # desar la taula de mesures d'un model **no escriu cap àlies de client**: la unicitat que
        # aquell guarda protegeix —`UNIQUE (customer, client_code)`— no la pot trencar aquesta
        # porta. Qui la pot trencar és `create_model_pom_view` (l'alta de POM propi), i allà el
        # guarda es queda tal com era.
        #
        # El dany era real i mesurat (M1194): un model VERGE de BRW no es podia gravar perquè
        # «B» i «SF» ja eren al diccionari del client per uns altres POMs. Un nom de fitxa és
        # BATEIG DEL MODEL —sobirania: entre models, lliure—, i la pantalla no oferia cap manera
        # de reanomenar la fila, o sigui que el refús no tenia sortida.
        #
        # ⚖️ LA LLEI QUE HI QUEDA (Agus, Decisió 8) ÉS **PER MODEL I ADVISORY**: dues files
        # del mateix àmbit amb POMs diferents que es diguin igual es DESEN i es diuen. La
        # recollida és aquí perquè els eixos ja estan resolts (v. `_identitat_de_mesura`, unes
        # línies amunt) i han de ser EXACTAMENT els mateixos amb què s'escriurà: agrupar per una
        # normalització i escriure per una altra és fabricar avisos que no es corresponen amb cap
        # fila. El veredicte es demana un cop llegit tot el payload, no per fila.
        nomen = (m.get('nom_fitxa') or '').strip()
        if nomen:
            nomenclatures.append({
                # La REFERÈNCIA DE FILA és la posició dins de `measurements`, i no `ordre`: el
                # client no l'envia (l'ordre el fabrica el servidor amb l'`enumerate` de
                # l'escriptura) i un `None` no identifica cap fila a la pantalla.
                'ref': _ref,
                'pom_id': int(pom_id),
                'garment': garment,
                'capa': capa,
                'instancia': instancia,
                'nom_fitxa': nomen,
            })
        # SET-2/#12c — l'eix viatja fins a l'escriptura. Fins aquí el `garment` es llegia
        # (v. el guard de duplicats, unes línies més amunt) i es llençava: la tupla el
        # deixava fora i l'upsert de sota resolia sense ell.
        prepared.append((m, value, capa, instancia, garment))

    # El rang físic té resposta pròpia (422) i mai es barreja amb els errors de forma (400):
    # un número impossible no és una petició mal escrita, és una dada que no pot existir.
    if fora_rang:
        return Response({'errors': fora_rang, 'codi': CODI_MESURA_FORA_RANG}, status=422)

    # DECISIÓ 8 — el veredicte d'homonímia es demana AQUÍ, amb tot el payload llegit, i **no
    # torna cap resposta**: es guarda per acompanyar el 200. Les files que hi surten ja són a
    # `prepared` i s'escriuran com qualsevol altra.
    avisos_nomenclatura = avisos_de_nomenclatura(nomenclatures)

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

            # ⚠️ **L'ORDRE DE LES FILES ÉS DADA DE L'USUARI, I AQUESTA PORTA EL LLENÇAVA**
            # (QA Agus 09/08). El carril té drag&drop i la tècnica ordena les cotes per
            # conveniència de mesura —l'ordre en què les prendrà amb la peça a la mà—, però
            # `gravar-pom` no escrivia `ordre` enlloc: totes les files del 1320 tenien `ordre=0`,
            # el default del camp. L'endpoint de reordenar (`base-measurements/reorder/`) sí que
            # el desa, però només el crida la superfície de PRESA; el carril de gènesi desa per
            # aquí, i per aquí l'ordre no existia.
            #
            # `measurements` ja arriba en l'ordre de la taula (és el que el client pinta), o sigui
            # que la posició a la llista ÉS l'ordre: no cal cap camp nou al payload ni cap gest
            # més. `enumerate` sobre `prepared`, que conserva l'ordre d'entrada.
            for pos, (m, value, capa, instancia, garment) in enumerate(prepared):
                try:
                    pom = POMMaster.objects.get(id=m.get('pom_id'))
                except POMMaster.DoesNotExist:
                    errors.append(f"POMMaster {m.get('pom_id')} no trobat")
                    continue

                # C4/BLOC 1-BIS — la fila es resol per la IDENTITAT SENCERA. Amb el literal
                # `(exterior, '')` que hi havia, dues germanes de la taula queien sobre la
                # mateixa fila i la segona escrivia damunt la primera. Els eixos vénen del
                # payload (v. `_identitat_de_mesura`); qui no els digui rep el literal de
                # sempre, i el `.first()` deixa de poder triar perquè la clau ja és única.
                # SET-2/#12c — LA PRENDA ENTRA A LA RESOLUCIÓ, com a l'upsert germà de
                # `set_measurements_view`. El `garment` ja arribava per aquesta funció —el
                # guard de duplicats del mateix request l'usa des de T2— però es perdia abans
                # d'escriure: el filtre no el deia i el constructor tampoc. Amb la mare i la
                # 02 al MATEIX POM (el cas normal: el pit del top i el pit de la calceta són
                # el mateix POM) el `.first()` podia caure sobre la fila de l'altra prenda i
                # sobreescriure-la, i tota fila nova naixia a la mare pel default del camp.
                # És la porta de la DEFINICIÓ de POM: la primera vegada que una taula de
                # mesures es desa passa per aquí.
                bm = BaseMeasurement.objects.filter(
                    model=model, pom=pom,
                    capa=capa, instancia=instancia, garment=garment).first()
                es_nova = bm is None
                if es_nova:
                    bm = BaseMeasurement(
                        model=model, pom=pom,
                        capa=capa, instancia=instancia, garment=garment,
                        created_by=request.user)
                    created += 1
                else:
                    updated += 1
                # Mateixa llei que l'altra porta (v. `_procedencia_de_mesura`): l'origen i les
                # toleràncies NO són efecte secundari de desar la taula. Es calcula ABANS
                # d'escriure el valor nou, perquè la regla compara amb el que hi havia.
                _procedencia_de_mesura(bm, m, pom, value, es_nova)
                bm.base_value_cm = value
                bm.notes = m.get('notes', '') or ''
                bm.nom_fitxa = m.get('nom_fitxa', '') or ''
                bm.ordre = pos                      # v. la nota del `for`: la posició ÉS l'ordre
                bm.is_active = True
                bm._changed_by = request.user
                bm._motiu = 'gravar_pom'
                bm.save()

            if errors:
                raise ValueError('; '.join(errors))

            if keep_mesures is not None or keep_pom_ids is not None:
                # C4/BLOC 1-TER — mateixa llei que l'altra porta (v. `_poda_mesures`). El
                # contracte ja porta els eixos i la baixa és per FILA; el client que només
                # sap dir `pom_id` conserva el comportament d'abans, que és no matar-ne cap.
                # SET-2/#12b — mateixa vora d'abast explícit que a `set_measurements_view`.
                deactivated = _poda_mesures(model, keep_mesures, keep_pom_ids,
                                            _abast_de_poda(request.data))

            valid_logiques = {code for code, _ in GradingRule.LOGICA_CHOICES}
            from fhort.pom.services import escala_del_model
            # TRAM F — el run del SISTEMA es llegeix UN cop per a totes les files: és el referent
            # dels intervals (llei S24b) i demanar-lo per fila serien N consultes per res. Un
            # model sense geometria completa el deixa buit, i llavors la validació d'intervals
            # comprova forma i recompte però no pot comprovar etiquetes (v. `valida_breaks`).
            try:
                _sr_g, run_sistema_gravar, _p_g, _bi_g = escala_del_model(model)
            except (ValueError, AttributeError):
                run_sistema_gravar = []
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
                        breaks=(src.breaks if src else None),      # TRAM F — el relleu sencer
                        # M3 — mateix criteri que `set_pom_regim_view` (vegeu-hi la nota): la
                        # fila que neix del fallback del catàleg ve d'aquell joc; la que neix
                        # de zero, de ningú. Una fila que ja existia no es re-etiqueta.
                        derivat_de_rule_set_id=(src.rule_set_id if src else None),
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
                # TRAM F — els intervals, amb la MATEIXA validació que la porta germana i contra
                # el mateix run (el del SISTEMA). Un error aquí s'acumula com la resta: aquesta
                # porta desa moltes files i ha de dir totes les que no van.
                if 'breaks' in r:
                    nets, err_breaks = valida_breaks(
                        r.get('breaks'), logica=rule.logica, run=run_sistema_gravar,
                        increment_base=rule.increment_base)
                    if err_breaks:
                        errors.append(f"POM {pom_id}: {err_breaks['detall']}")
                        continue
                    rule.breaks = nets
                # A3 (2026-07-22) — MATEIX guard que set_pom_regim_view. Aquest camí
                # (gravar_pom, la taula de gènesi) escrivia LINEAR+0 sense cap comprovació:
                # era el forat per on la llei encara es podia trencar.
                if es_linear_degenerada(rule.logica, rule.increment_base, rule.increment,
                                        rule.increment_break, rule.talla_break_label,
                                        rule.breaks):
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

            pom_task = _assegura_pom_task_oberta(model, profile)
            if pom_task.get('reason') == 'no_pom_task':
                raise ValueError('Cal obrir la tasca POM abans de gravar-la')
    except ValueError as e:
        return Response({'error': str(e)}, status=400)

    # ⚠️ **LA TAULA DE TALLES NO LA GENERAVA NINGÚ DEL FLUX** (QA Agus 09/08, bloquejant).
    #
    # «Mesurar prenda» refusa amb «el model no té cap GradingVersion activa» un model que té run,
    # talla base, mesures i graduació: tot el que cal per graduar-lo. Qui la generava era
    # `generar-grading`, i al front l'ÚNIC que el crida és el botó **Propagar** — o sigui que la
    # taula existia només si algú premia un botó que no diu que serveixi per a això. Al wizard
    # vell el recorregut hi passava per damunt; el Resum partit no hi passa, i el pas va quedar
    # orfe. No és que el gate estigui mal posat: és que ningú no complia la seva condició.
    #
    # El moment que toca és AQUEST i no el de desar talles ni el de desar graduació: graduar
    # necessita les TRES coses alhora —regles, run i mesures base—, i les mesures base neixen
    # aquí. Als altres dos moments el model encara no en té cap i generar seria generar el buit.
    # És idempotent (`generate_graded_specs` reutilitza la versió vigent, no fa bump: propagar
    # segueix sent l'acte conscient que crea la v+1) i **no pot tombar el desat**: la gènesi POM
    # ja ha quedat persistida i commitada més amunt; si graduar peta, es diu al payload i s'entra
    # a Mesures pel camí de sempre, no es perd la feina de la tècnica.
    taula = None
    try:
        if _te_regles(model) and model.size_run_model and model.base_size_label:
            from fhort.pom.services import generate_graded_specs, get_or_create_size_fitting
            sf = get_or_create_size_fitting(model, actor_profile_id=getattr(profile, 'id', None))
            taula = {'size_fitting': sf.id, 'specs': generate_graded_specs(sf.id)}
    except Exception as e:                       # noqa: BLE001 — mai ha de tombar el desat
        import logging
        logging.getLogger(__name__).warning(
            'gravar_pom: no s\'ha pogut generar la taula de talles del model %s: %s',
            model.codi_intern, e)
        taula = {'error': str(e)}

    return Response({
        'created': created,
        'updated': updated,
        'deactivated': deactivated,
        'rules_saved': rules_saved,
        'reseed': had_base_before,
        'pom_task': pom_task,
        #: La taula de talles generada en el mateix acte (o el motiu pel qual no s'ha pogut).
        'taula_talles': taula,
        #: DECISIÓ 8 — els grups de files que comparteixen àmbit i nom de fitxa amb POMs
        #: diferents. **Sempre present** (llista buida quan no n'hi ha cap), pel mateix
        #: argument que `camps_de`: el consumidor no ha de distingir entre «no n'hi ha» i
        #: «aquest backend encara no ho serveix». Tot el que hi surt JA ESTÀ DESAT.
        'avisos_nomenclatura': avisos_nomenclatura,
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
    """F1.3 · AQUESTA PORTA NO BAT, I ÉS UNA DECISIÓ, NO UN OBLIT.

    Pujar un fitxer a un model no diu a QUINA feina pertany: no hi ha cap `TaskType` amb l'eina
    de «fitxers» (el catàleg mapeja `mesures`/`escalat`/`fitxa`/`patro`, i cap d'ells és això).
    Un adjunt pot ser d'una fitxa, d'un patró, d'un fitting o de res. Batre-hi obligaria a triar
    una superfície a l'atzar i imputar temps a la tasca equivocada — pitjor que no imputar-ne.
    Si algun dia un `TaskType` reclama els adjunts, el batec entra aquí amb el seu `code`.
    """
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    uploaded_file = request.FILES.get('fitxer')
    if not uploaded_file:
        return Response({'error': 'fitxer és obligatori'}, status=400)

    from .services_fitxers import (MAX_ADJUNT_DIM, ConversioFallida, UploadRejected,
                                   redueix_imatge, save_model_file, validate_upload)

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

    # EMBUT D'IMATGE (una sola porta per a HEIC i mida): les fotos es fan amb el mòbil, arriben
    # en HEIC —que cap navegador d'escriptori no pinta— i amb 4000+ px que ningú mira. El que
    # entra a la cadena de versions és sempre pintable i de mida raonable. Els no-ràsters
    # (.pdf, .dxf, .ftt, …) hi passen de llarg intactes.
    #
    # `save_model_file` també hi passa la imatge (l'embut viu al COLL, no només aquí), i el
    # sostre ha de ser EL MATEIX als dos llocs: amb sostres diferents la foto es re-encodaria
    # dues vegades —3000→2000 aquí, 2000→1500 al coll— i cada re-encodat de JPEG hi deixa
    # pèrdua. Igualats, la segona passada la reconeix com a conforme i la torna byte a byte.
    # Aquesta crida es queda perquè és qui sap traduir `ConversioFallida` en un 422: al coll,
    # que serveix camins sense request, l'excepció puja com a ValueError.
    try:
        uploaded_file, nom = redueix_imatge(
            uploaded_file, nom, getattr(uploaded_file, 'content_type', ''),
            max_dim=MAX_ADJUNT_DIM)
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
                        # L'ORIGEN I LES TOLERÀNCIES NO SÓN EFECTE SECUNDARI D'AQUESTA
                        # ESCRIPTURA — la mateixa llei que ja tenen les altres dues portes
                        # (`set_measurements_view` i `gravar_pom_view`), aquí pendent des del
                        # 05/08. Amb l'`update_or_create` d'abans, els `defaults` s'apliquen
                        # TAMBÉ quan la fila ja hi és: un AFEGIR sobre una mesura que ja
                        # existia la reescrivia a `MANUAL` —encara que vingués d'una presa de
                        # size check i el valor fos el mateix— i li tornava les toleràncies
                        # del catàleg, esborrant les que algú hagués afinat. I aquest camí és
                        # el pitjor lloc per fabricar un `MANUAL` fals: qui ho ha teclejat és
                        # una IA, i `origen` no és append-only (el registre que salva els
                        # mobles és `MeasurementChangeLog`).
                        #
                        # FASE_3/C1-ins — literals dels eixos (v. `_write_base`).
                        bm = BaseMeasurement.objects.filter(
                            model=model, pom=pom,
                            capa=MeasurementLayer.SLUG_DEFECTE, instancia='').first()
                        created = bm is None
                        if created:
                            bm = BaseMeasurement(
                                model=model, pom=pom,
                                capa=MeasurementLayer.SLUG_DEFECTE, instancia='',
                                # L'ordre és de naixement: reasignar-lo a cada AFEGIR movia
                                # al final una fila que ja tenia el seu lloc a la taula.
                                ordre=base_measurements.count())
                        valor_nou = float(accio['valor'])
                        # El payload del xat no parla d'origen (no és al contracte d'acció de
                        # la IA), o sigui que mana la regla de defecte: neix → MANUAL; ja hi
                        # era i el valor canvia → MANUAL; ja hi era i el valor és el mateix →
                        # no es toca res.
                        _procedencia_de_mesura(bm, {}, pom, valor_nou, created)
                        bm.base_value_cm = valor_nou
                        bm.save()
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
@bat_escriptura(SUP_ESCALAT)
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
    # TRAM E — el canal de la llista de treball manual (v. `generate_graded_specs`).
    informe: dict = {}
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
        # C3-A2 — LA PROPAGACIÓ ÉS UN ACTE, NO TRES. `ATOMIC_REQUESTS` no existeix
        # (settings.py:118-127) i aquesta vista no obria cap atòmic: el llenç net d'overrides
        # de sota es commitava tot sol, i si el motor petava després, la vista retornava 400 o
        # 500 amb els ajustos per cel·la JA ESBORRATS i sense manera de recuperar-los. Pitjor:
        # `bump_grading_version_and_generate` desactiva les versions actives i crea la v+1
        # abans de propagar-hi (pom/services.py:876-880), o sigui que una petada del motor
        # podia deixar la v+1 viva i BUIDA amb l'anterior ja desactivada — el model sense cap
        # graduació llegible i sense cap error que ho expliqués.
        # Mateixa atomicitat que les germanes del fitxer (:1583 tancar-taula, :2773 escalat).
        # NO es toca res de la lògica de grading: només l'embolcall.
        with transaction.atomic():
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
                    informe=informe,
                )
            except ValueError as e:
                # Rollback explícit: es retorna des de DINS de l'atòmic, i sense això Django
                # el donaria per bo i commitaria el llenç net (mateix motiu que a :2840).
                transaction.set_rollback(True)
                return Response({'error': str(e)}, status=400)
            except Exception as e:
                transaction.set_rollback(True)
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
        # C3-A2 — el camí in-place també. Aquí el motor és l'únic escriptor, però escriu cel·la
        # a cel·la (`_upsert_graded_spec` per (POM, talla)) i posa l'estat de l'SF al final:
        # una petada a mitja graella deixava files noves i files velles barrejades a la versió
        # vigent, amb l'estat sense actualitzar i un 500 que no deia què havia quedat escrit.
        with transaction.atomic():
            try:
                graded_count = generate_graded_specs(sf.id, informe=informe)
            except SealedGradingVersionError as e:
                # G6-B/T1 · camí 1/6. Regenerar in-place sobre una versió segellada: refusat. La
                # sortida és el `new_version=True` d'aquest mateix endpoint (el bump), no forçar.
                transaction.set_rollback(True)
                return Response(e.payload, status=409)
            except ValueError as e:
                transaction.set_rollback(True)
                return Response({'error': str(e)}, status=400)
            except Exception as e:
                transaction.set_rollback(True)
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
        graded = {}
        if gv:
            # C4/BLOC 2 — LA CORBA ÉS DE LA MESURA, NO DEL POM. Aquesta consulta filtrava per
            # `(grading_version, pom)` i les germanes hi queien totes al mateix
            # `graded[size_label]`: guanyava l'última llegida, i la fila d'exterior ensenyava
            # la corba del folre.
            #
            # MESURAT A ROSALIA (model 188), amb les germanes vives i G1 retirat:
            #     A     base 37.0 → graded S 35.5   ← la corba d'A-FOL
            #     AH-L  base 23.2 → graded S 23.0   ← la corba d'AH-R
            # La BD era correcta i `taula-mesures` també: només mentia aquest payload. És
            # l'onzena superfície, i el cens de C4 en tenia deu.
            for spec in GradedSpec.objects.filter(grading_version=gv, pom=pom,
                                                  capa=bm.capa, instancia=bm.instancia):
                graded[spec.size_label] = (
                    float(spec.graded_value_cm) if spec.graded_value_cm is not None else None
                )
        rows.append({
            'id': bm.id,
            'pom_id': pom.id,
            # Els dos eixos al contracte: `pom_id` no és únic dins de `rows`, i `id` (la PK de
            # la mesura) és l'àncora forta de cada element.
            'capa': bm.capa,
            'instancia': bm.instancia,
            # FONT ÚNICA (22/08) — codi i noms del catàleg pel resolutor de
            # `pom/nomenclatura.py` (ÀLIES > TENANT > GLOBAL).
            'pom_code': codi_de(pom),
            'nom_fitxa': bm.nom_fitxa or '',
            'nom_ca': noms_de(pom)['nom_ca'],
            'nom_en': noms_de(pom)['nom_en'],
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
        # TRAM E — LA LLISTA DE TREBALL MANUAL, no un avís genèric: quins POMs i quines talles
        # han sortit amb el valor de la talla base copiat perquè la regla STEP no en té valor.
        # Buida quan no n'hi ha cap (una clau que hi és sempre és més fàcil de llegir que una
        # que apareix i desapareix).
        'step_base_copiada': informe.get('step_base_copiada', []),
        'rows': rows,
    })


class _ExecuteTasksCap(HasCapability):
    required_capability = EXECUTE_TASKS


@api_view(['POST'])
@permission_classes([_ExecuteTasksCap])
def set_size_override_view(request, model_id):
    """POST /api/v1/models/<model_id>/set-size-override/  Body: {pom_id, size_label, valor, garment?}

    Edita el valor d'UNA talla NO-base com a ModelGradingOverride (per-model,
    traçable) i RE-PROPAGA el grading (generate_graded_specs) sobre la
    GradingVersion vigent (criteri de PEÇA 0). L'override té precedència màxima
    al motor (override→exception→regla→FIXED), per tant editar una 2a talla
    manté la 1a. NO toca GradedSpec directament (és sortida del motor) ni
    PieceFittingLine.

    ── F2 (2026-08-25) · **IDEMPOTENT PER `(model, pom, size_label, garment)`** ─────────
    Ho era per `(model, pom, size_label)`, i era la frase d'abans que el model tingués peces.
    La `unique` real de `ModelGradingOverride` són SIS columnes
    —`(model, pom, size_label, capa, instancia, garment)`— i aquest camí en deia CINC: el
    `garment` no hi era ni al lookup ni al payload, o sigui que no es podia ni dir ni
    distingir. Amb dues peces vives que comparteixin un POM, el `filter` de cinc columnes
    casa DUES files i l'`update_or_create` peta amb `MultipleObjectsReturned` (500); i abans
    d'arribar-hi, el `prev` ja ha pogut llegir el valor de l'ALTRA peça i deixar un
    `MeasurementChangeLog` que diu que s'ha canviat una mesura que ningú no ha tocat.
    El defecte NO era latent: `fhort` ja té tres parells `(model, pom)` amb mesura a dues
    peces (1320/904, 1379/962, 1380/962) — v. `docs/ordres/CENS_INSTANCIES_POM_2026-08-25.md`,
    fila 9 del veredicte.

    És el MIRALL del germà `escalat_ajustar_talla_view`, que ja el diu i ja el passa des de
    SET-2/T8. El `garment` surt del punt únic `_identitat_de_mesura`: **qui no el diu rep
    `''`, la peça MARE**, que és el comportament d'avui byte a byte per a tot model d'una
    sola peça (i per a tot client antic, que no el sabrà enviar mai).

    ⚠️ `capa` i `instancia` segueixen sent LITERALS aquí, i no és un oblit: aquest fix obre
    UN eix, el que tenia el defecte. Amb el `garment` al lookup la clau ja és la `unique`
    sencera i cap `update_or_create` d'aquest camí pot tornar a casar dues files. Que aquesta
    porta no sàpiga adreçar una GERMANA d'instància és una limitació coneguda i separada
    (mateix cens, fila 12-13); obrir-la és una altra decisió i un altre tram.
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
    # F2 — EL GARMENT, PEL PUNT ÚNIC. `_identitat_de_mesura` és qui decideix què rep qui no
    # el diu (v. la seva acta): `''` = peça MARE, i un `None` explícit al cos val el mateix
    # que no dir-ho, perquè la columna és NOT NULL amb default. Se'n pren NOMÉS el tercer
    # eix: els altres dos segueixen literals en aquesta porta (v. el docstring).
    garment = _identitat_de_mesura(data)[2]
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
        # FASE_3/C1-ins — literals als TRES punts d'aquest bloc (la lectura de `prev`,
        # l'upsert i el log): han de parlar de la MATEIXA fila o el rastre diria que s'ha
        # canviat una mesura que no s'ha tocat. V. `_write_base`.
        # F2 — i el `garment` va als TRES pel mateix motiu, que aquí és el més urgent dels
        # tres: al lookup perquè la clau ha d'anar SEMPRE alineada amb la unicitat real de la
        # taula (sis columnes, no cinc) i sense ell l'`update_or_create` casa dues files; a
        # `prev` perquè el valor d'abans ha de ser el D'AQUESTA peça; i al log perquè
        # `MeasurementChangeLog` és APPEND-ONLY i no té unicitat — una fila mal atribuïda no
        # es pot corregir després.
        prev = (ModelGradingOverride.objects
                .filter(model=model, pom=pom, size_label=size_label,
                        capa=MeasurementLayer.SLUG_DEFECTE, instancia='',
                        garment=garment)
                .values_list('value_cm', flat=True).first())
        ModelGradingOverride.objects.update_or_create(
            model=model, pom=pom, size_label=size_label,
            capa=MeasurementLayer.SLUG_DEFECTE, instancia='',
            garment=garment,
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
                capa=MeasurementLayer.SLUG_DEFECTE, instancia='',
                garment=garment,
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
    # F2 — LA LECTURA DE RETORN TAMBÉ VOL LA IDENTITAT, i era el segon forat d'aquest camí.
    # La `unique` de `GradedSpec` són sis columnes i aquest filtre en deia TRES: amb una
    # germana viva —d'instància o de peça— el `.first()` sense `order_by` retorna la fila que
    # el planner de Postgres vulgui, o sigui que la resposta podia dir el `graded_value_cm`
    # d'una ALTRA mesura amb un 200 OK. S'hi posen els tres eixos, i els dos literals són
    # exactament els que aquest camí acaba d'escriure: la resposta descriu la fila escrita.
    # Mirall del germà (`escalat_ajustar_talla_view`), que ja hi filtra per identitat sencera.
    gv = vigent_grading_version(sf)
    graded = (GradedSpec.objects
              .filter(grading_version=gv, pom=pom, size_label=size_label,
                      capa=MeasurementLayer.SLUG_DEFECTE, instancia='', garment=garment)
              .values_list('graded_value_cm', flat=True).first()) if gv else None
    return Response({
        'ok': True,
        'model_id': model.id,
        'pom_id': pom.id,
        'size_label': size_label,
        # F2 — QUINA PEÇA s'ha escrit. Additiu: un client que no el llegeixi no en nota res,
        # i el que l'envia pot comprovar que ha aterrat on volia (l'`''` és la mare).
        'garment': garment,
        'override_value_cm': valor,
        'grading_version_id': gv.id if gv else None,
        'graded_value_cm': float(graded) if graded is not None else None,
    }, status=200)


@api_view(['POST'])
@permission_classes([_ExecuteTasksCap])
@bat_escriptura(SUP_ESCALAT)
def escalat_ajustar_talla_view(request, model_id):
    """POST /api/v1/models/<model_id>/escalat/ajustar-talla/

    Body: `{pom_id, talla, valor, capa?, instancia?, garment?}` — els tres eixos identifiquen
    LA MESURA (v. `_identitat_de_mesura`); qui no els diu rep el literal de sempre, que és
    l'exterior de la instància única de la peça MARE.

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
    from fhort.pom.services import (generate_graded_specs, _load_grading_rules_per_garment,
                                    _regla_de, escala_del_model)
    from fhort.pom.grading_utils import propaga_ancoratges
    from fhort.fitting.services import _resolve_working_size_fitting, vigent_grading_version
    from fhort.fitting.models import GradedSpec

    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    data = request.data or {}
    pom_id = data.get('pom_id')
    # C4/BLOC 2 — QUINA GERMANA S'AJUSTA. Aquesta vista escriu a QUATRE taules
    # (`BaseMeasurement` via `_write_base`, `ModelGradingOverride` dues vegades i
    # `MeasurementChangeLog`) i les quatre anaven amb el literal `(exterior, '')`: ajustar la
    # talla de la sisa dreta movia la base de l'esquerra, li esborrava els overrides i deixava
    # l'apunt del canvi atribuït a l'altra al registre append-only.
    # Punt únic compartit amb els dos upserts, les dues podes i `desactivar_pom`.
    capa, instancia, garment = _identitat_de_mesura(data)
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

        # GUARDA DE RANG FÍSIC (30/07) — la porta per on va entrar el 22224,7 del POP. És
        # una de les DUES portes de mesura del backend (l'altra és `gravar_pom`) i totes
        # dues passen pel mateix punt únic. Dins del rang no restringeix res: v. la llei a
        # `pom/plausibilitat.py`.
        fora = mesura_fora_de_rang(valor)
        if fora:
            return Response({'error': fora, 'codi': CODI_MESURA_FORA_RANG}, status=422)

        # ✅ SET-2/F1 · Q1-bis — LA LLEI DE LA PEÇA, NO LA DE LA MARE.
        # Això era `_load_grading_rules(model).get(pom.id)`, la 4a de les cinc boques que
        # serveixen la regla de la peça mare (acta a `pom/services.py:774-806`). Aquella
        # acta ja deia que la línia que separa els consumidors adaptats dels que es queden
        # NO és l'app on viuen sinó **si escriuen** — i aquest DECIDEIX UNA ESCRIPTURA:
        # `propaga_ancoratges` deriva la nova base a partir del delta de la regla. Amb la
        # llei de la mare, ajustar una talla de la 02 li aplicava un increment que no és
        # seu (D4 diu que poden divergir) i escrivia el resultat a la seva base.
        #
        # 🚨 PER QUÈ VA AL MATEIX COMMIT QUE EL LOOKUP: mentre `_write_base` petava amb
        # `MultipleObjectsReturned`, el 500 TAPAVA aquest defecte. Arreglar el lookup sol
        # hauria convertit un error sorollós en un valor mal calculat i MUT. És la llei
        # S42 girada: tancar una escriptura ARMA el seu lector.
        rule = _regla_de(_load_grading_rules_per_garment(model), pom.id, garment)
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
                avisos_regla = []
                if talla != base_size:
                    try:
                        _run_model, run_sistema, _pos, _bidx = escala_del_model(model)
                    except ValueError as e:
                        return Response({'error': str(e)}, status=400)
                    nova_base = propaga_ancoratges(
                        rule, talla, valor, size_run, warnings=avisos_regla,
                        run_sistema=run_sistema, base_label=base_size).get(base_size)
                if nova_base is None:
                    # FIX-A/PAS-3 — EL MOTIU VIATJA. Des que la regla incompleta deixa de caure
                    # al camp llegat, `propaga_ancoratges` pot tornar tot None, i el missatge
                    # genèric d'aquí feia buscar el defecte a la talla ancorada quan el que
                    # falla és la REGLA. `warnings` en porta la frase exacta.
                    return Response(
                        {'error': (avisos_regla[0] if avisos_regla
                                   else "No s'ha pogut derivar la base des de la talla ancorada."),
                         'code': 'regla_sense_delta' if avisos_regla else 'base_no_derivable'},
                        status=400)
                _write_base(model, pom, round(float(nova_base), 2), auth_user,
                            f'Escalat · ajust talla {talla} (propaga per regla)',
                            capa=capa, instancia=instancia, garment=garment)
                # La corba de la regla mana: neteja els pins per cel·la del POM (el fitting sobreescriu
                # els valor_real de les germanes; aquí l'equivalent és treure els overrides residuals).
                # L'esborrat tampoc no és per POM: neteja els overrides de LA MESURA que es
                # torna a propagar. C4/BLOC 2 — els eixos vénen del cos; sense ells s'enduria
                # els de les germanes, que ningú no ha tocat.
                # SET-2/F1 — i la PEÇA: `unique_together` d'aquesta taula ja la porta
                # (`models.py:1089`), o sigui que sense l'eix aquest `.delete()` s'enduia
                # els pins de l'ALTRA peça, que ningú no ha tocat tampoc.
                ModelGradingOverride.objects.filter(
                    model=model, pom=pom,
                    capa=capa, instancia=instancia, garment=garment).delete()
                propagat, motiu = True, (logica or 'CANONIC')
            elif talla == base_size:
                # Base sense règim LINEAR: desa la base; germanes intactes (mirall del fitting STEP).
                _write_base(model, pom, valor, auth_user, f'Escalat · base {talla}',
                            capa=capa, instancia=instancia, garment=garment)
                propagat, motiu = False, (logica or 'BASE')
            else:
                # STEP/FIXED/ZERO o sense regla → override puntual (germanes intactes, com el fitting).
                # C4/BLOC 2 — els tres punts van per la identitat de la mesura, no pel POM.
                # SET-2/F1 — els TRES eixos als tres punts. Sense la peça, l'`update_or_create`
                # naixia sempre a la mare (la clau única de la taula la porta) i el
                # `MeasurementChangeLog` —que és APPEND-ONLY— quedava amb l'apunt atribuït a
                # una peça que no era: un error que no es pot corregir mai.
                prev = (ModelGradingOverride.objects
                        .filter(model=model, pom=pom, size_label=talla,
                                capa=capa, instancia=instancia, garment=garment)
                        .values_list('value_cm', flat=True).first())
                ModelGradingOverride.objects.update_or_create(
                    model=model, pom=pom, size_label=talla,
                    capa=capa, instancia=instancia, garment=garment,
                    defaults={'value_cm': valor, 'motiu': 'Escalat · ajust talla (sense propagació)',
                              'fitting_ref': None, 'created_by': profile},
                )
                if prev is None or abs(float(prev) - valor) > 1e-9:
                    MeasurementChangeLog.objects.create(
                        model=model, pom=pom, base_measurement=None,
                        capa=capa, instancia=instancia, garment=garment,
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

    # Files actualitzades de LA MESURA (mirall de 'linies' de /propagar): {id, valor_real} per
    # talla. C4/BLOC 2 — dues coses aquí, i totes dues es veien a la pantalla:
    #
    # ① la consulta filtra per la germana. Per `(grading_version, pom)` sol, els specs de les
    #    dues germanes queien al mateix `graded[size_label]` i la resposta tornava la corba de
    #    l'última llegida — o sigui que després d'ajustar la sisa dreta, la fila ensenyava les
    #    xifres de l'esquerra.
    #
    # ② l'`id` és la CLAU DE LA MESURA, no `{pom_id}:{talla}`. `MeasureGrid` fa servir aquest
    #    `id` per indexar el seu buffer de cel·les, que va per `lineId`, i el `lineId` de
    #    l'Escalat va passar a `{clau}:{talla}` al bloc 3 (`a0f588f9`). Des d'aleshores els dos
    #    formats no casaven i el refresc de les talles propagades NO ARRIBAVA A LA PANTALLA:
    #    l'escriptura es feia, la corba es re-derivava, i les cel·les germanes es quedaven amb
    #    el valor vell fins a recarregar. Sense error i sense avís.
    #    La forma la decideix `pom/identitat.clau_mesura`, l'únic lloc que sap com s'aplana.
    #
    # ③ ✅ SET-2/F1 — LA PEÇA, I EL TRAM PROPI ÉS AQUEST. El que hi havia deia: «obrir el
    #    contracte d'ESCRIPTURA al garment és un tram propi; això NO ho és», i el filtre
    #    anava amb el literal `''`. El contracte ja està obert (la pantalla el sap dir i
    #    `_identitat_de_mesura` el resol), o sigui que el literal se'n va.
    #
    #    Aquesta és la SUPERFÍCIE DE RESPONSE LITERAL de la vista: `linies` es construeix
    #    aquí mateix, sense serializer, i `MeasureGrid` indexa el seu buffer de cel·les per
    #    aquest `id`. Amb l'eix cuit a `''`, el refresc d'una fila de la 02 no arribava mai
    #    a la seva cel·la —l'escriptura es feia, la corba es re-derivava, i la pantalla es
    #    quedava amb el valor vell fins a recarregar—: el mode de fallada mut que ② descriu
    #    per al `lineId`, un eix més tard.
    from fhort.pom.identitat import clau_mesura
    gv = vigent_grading_version(sf)
    graded = {}
    if gv:
        for spec in GradedSpec.objects.filter(grading_version=gv, pom=pom,
                                              capa=capa, instancia=instancia,
                                              garment=garment):
            graded[spec.size_label] = (
                float(spec.graded_value_cm) if spec.graded_value_cm is not None else None)
    clau = clau_mesura(pom.id, capa, instancia, garment)
    linies = [{'id': f'{clau}:{s}', 'valor_real': graded.get(s)} for s in size_run]
    return Response({'ok': True, 'propagat': propagat, 'motiu': motiu,
                     'grading_version_id': gv.id if gv else None, 'linies': linies}, status=200)


def _abast_de_poda(data):
    """Les prendes que un desat declara que està podant, o `None` si no ho declara. Punt únic.

    SET-2/#12b — la vora d'ABAST EXPLÍCIT. Normalment l'abast es dedueix de les files que el
    payload anomena (v. `_poda_mesures`), i no cal dir res: un contenidor que envia files ja
    diu de quina prenda parla. L'únic gest que la derivació no pot resoldre és el contenidor
    que es desa BUIT —cap fila, cap eix, i tanmateix una ordre de buidar-lo—, i per a aquell
    el client ha de poder dir qui és.

    És deliberadament un camp del COS i no un paràmetre d'URL: viatja amb el desat, dins de la
    mateixa transacció que el provoca. I és opcional per la mateixa raó que `keep_mesures` ho
    va ser al seu dia: un client que no el digui ha de seguir fent exactament el que feia.
    """
    g = (data or {}).get('garments')
    if not isinstance(g, (list, tuple)):
        return None
    return [str(x or '') for x in g]


def _poda_mesures(model, keep_mesures, keep_pom_ids, garments=None):
    """Desactiva les mesures actives del model que el client NO ha dit que conserva.

    ── C4/BLOC 1-TER · LA PODA RESOL PER FILA, I EL CLIENT VELL NO EN MATA CAP ─────────
    Les dues portes que podaven (`set_measurements_view` i `gravar_pom_view`) ho feien amb
    `keep_pom_ids`, una llista d'ENTERS, i ancorades a `(exterior, '')`. L'àncora no era un
    defecte de lectura: era el gest d'esborrar que no arribava. Amb dues germanes a la taula,
    treure la fila del folre i desar no feia res —la consulta no la mirava— i l'usuari no
    tenia manera de saber-ho.

    Desancorar-la sense tocar el contracte no ho arregla, l'empitjora. Un `pom_id` pelat no
    pot dir «conserva el folre i treu l'exterior»: només diu de quins POMs es parla. Amb la
    llista d'enters només hi ha dues lectures possibles, i totes dues són dolentes —o cap
    germana es pot esborrar mai, o esborrar-ne una les mata totes.

    LA SORTIDA ÉS QUE EL CONTRACTE PORTI LA IDENTITAT, igual que a l'upsert:

      · `keep_mesures` — llista de `{pom_id, capa, instancia}`. La poda hi resol per la fila
        sencera: sobreviu qui hi és, cau qui no. És el camí del client d'avui.
      · `keep_pom_ids` sol — el client ANTIC. Es conserva EXACTAMENT el comportament d'abans:
        poda limitada a l'exterior de la instància única.

    ⚠️ I la segona no és una mancança que algú hagi d'«arreglar» després. **Una llista de POMs
    no diu que cap germana s'hagi de treure.** Interpretar-ne el silenci com una ordre
    d'esborrar seria decidir per un client que no ha dit res —exactament el que aquest tram ha
    prohibit a l'upsert—, i el preu de l'error no és una cel·la mal pintada: és una mesura
    donada de baixa que ningú no ha demanat.

    ── SET-2/#12b · I L'ABAST DE LA PODA ÉS EL DE LES PECES QUE EL PAYLOAD NOMENA ──────
    La branca de `keep_mesures` resolia per fila però mirava TOTES les files vives del model,
    i això només era correcte mentre la taula fos una de sola. Amb la taula partida per peça
    (S2, pas 3) un desat porta les files del SEU contenidor i prou: desar el de la mare
    hauria donat de baixa les files del Pantaló —amb l'eix al payload i tot—, perquè no
    sortien a la llista. Mesurat contra dades vives per S2, amb rollback: 1 baixa, la fila
    de la 02 morta.

    És la MATEIXA llei que T5 va aplicar a la branca de la clau curta, un contracte més
    amunt: **una llista de files no és una ordre d'esborrar la feina d'una altra prenda**. Qui
    no surt a la llista cau NOMÉS si la seva peça és una de les que la llista anomena; les
    files de les altres prendes no són ni candidates.

    ⚠️ Això REVISA una decisió de T5 (`test_set2_t5_escriptors`, 10/08), que llegia
    `keep_mesures` com «tot el que queda al MODEL». Ara es llegeix com «tot el que queda al
    CONTENIDOR», que és el que el client realment sap dir. El test d'aquell dia s'ha adaptat
    amb el motiu datat.

    `garments` — l'abast EXPLÍCIT, per al cas que la derivació no pot resoldre: un contenidor
    que es desa BUIT no anomena cap peça i el payload no diu de qui és. Sense ell no es poda
    res (no s'endevina mai de qui és el silenci); amb ell, el contenidor diu qui és i pot
    buidar-se sencer. Cap client l'envia encara: és la vora que S2 necessitarà al pas 3.

    Torna el nombre de files desactivades.
    """
    from fhort.models_app.models import BaseMeasurement
    from fhort.pom.models import MeasurementLayer

    vives = BaseMeasurement.objects.filter(model=model, is_active=True)

    if keep_mesures is not None:
        conserva = {(int(k['pom_id']),) + _identitat_de_mesura(k)
                    for k in keep_mesures if k.get('pom_id')}
        # L'ABAST: el que diu el client si el diu, i si no el que les files NOMENEN. Un
        # conjunt buit —cap fila i cap abast explícit— no és «totes»: és «no ho sé», i
        # d'un «no ho sé» no en surt cap baixa.
        if garments is not None:
            abast = {str(g or '') for g in garments}
        else:
            abast = {ident[3] for ident in conserva}
        # `.exclude()` no pot expressar una clau composta: es resol en Python sobre les files
        # vives del model, que són poques i ja s'han de llegir igualment.
        baixes = [bm.id for bm in vives
                  if bm.garment in abast
                  and (bm.pom_id, bm.capa, bm.instancia, bm.garment) not in conserva]
        return BaseMeasurement.objects.filter(id__in=baixes).update(is_active=False) if baixes else 0

    # ── SET-2/T5 · LA BRANCA DE LA CLAU CURTA, I PER QUÈ HI ENTRA `garment=''` ─────────
    # Aquesta branca DESACTIVA tot el que no sigui a `keep_pom_ids`, i el cridador que hi
    # arriba només sap dir POMs: no sap de capes, ni d'instàncies, ni de peces. Per això ja
    # s'acotava a l'exterior de la instància única — desactivar la germana d'un eix que el
    # client no ha nomenat seria decidir per ell.
    # El `garment=''` és la MATEIXA llei amb l'eix nou, i sense ell el dany era el més gros
    # del tram: una crida amb clau curta —les que fa avui el 100% del corpus— hauria donat
    # de baixa les files de TOTES les peces del model, no només les de la mare. Esborra
    # feina i no crida: ningú peta, les mesures simplement deixen de comptar.
    # Una llista de POMs no diu que cap peça s'hagi de treure.
    keep = [int(x) for x in keep_pom_ids]
    return (vives
            .filter(capa=MeasurementLayer.SLUG_DEFECTE, instancia='', garment='')
            .exclude(pom_id__in=keep)
            .update(is_active=False))


def _identitat_de_mesura(m):
    """Els dos eixos d'una mesura tal com arriben pel cos d'una petició. Punt únic.

    ── C4/BLOC 1-BIS · EL CONTRACTE D'ESCRIPTURA S'OBRE ────────────────────────────────
    Fins ara els escriptors que reben el POM per HTTP declaraven els eixos amb el literal
    del cas (`_write_base` en té l'acta), perquè el cos era `{'pom_id': …}` i prou. Amb dues
    germanes vives això deixa de ser una declaració i passa a ser una col·lisió: dues files
    de la taula hi cauen a sobre i la segona escriu el seu valor damunt de la primera.

    Ara el client els pot dir, i els diu com a DOS CAMPS —no com la cadena aplanada
    `{pom}|{capa}|{inst}`—, que és el que mana `pom/identitat.py`: la cadena serveix la vora
    del payload on la mesura ha de ser clau d'un objecte JSON, i escriure no és aquest cas.

    QUI NO ELS DIU REP EL LITERAL DE SEMPRE, i això és deliberat: un client antic (o una
    fila que encara no s'ha desat mai, que no té eixos perquè no té mesura) segueix escrivint
    a l'exterior de la instància única, exactament com abans. El que NO es fa mai és mirar
    quines files hi ha i triar-ne una: això seria el desempat a l'atzar que tot aquest tram
    persegueix. El default és explícit i no depèn de les dades.

    ⚠️ Un `None` explícit al cos es tracta com el valor buit, no com el text «None»: les
    columnes són NOT NULL amb default i un client que enviï `null` vol dir «la de sempre».
    """
    from fhort.pom.models import MeasurementLayer
    return (m.get('capa') or MeasurementLayer.SLUG_DEFECTE,
            m.get('instancia') or '',
            m.get('garment') or '')


#: Sentinella per distingir «el payload no en diu res» de «el payload diu None».
_NO_DIT = object()


def _procedencia_de_mesura(bm, m, pom, valor_nou, es_nova):
    """L'ORIGEN I LES TOLERÀNCIES D'UNA FILA: què s'hi toca i, sobretot, què NO (Agus, 05/08).

    ── EL DEFECTE ─────────────────────────────────────────────────────────────────────
    Les dues portes d'escriptura massiva d'aquest fitxer (`set_measurements_view` i
    `gravar_pom_view`) forçaven `origen='MANUAL'` i reescrivien les dues toleràncies des del
    catàleg a **cada fila del payload**, hi hagués canviat el valor o no. Efecte: qualsevol
    escriptura que passés per allà —encara que només vingués a moure una fila de capa o a
    reenviar la taula sencera sense tocar cap xifra— convertia en `MANUAL` una base que una
    sessió de size check havia deixat `CHECKED`, i li tornava les toleràncies del catàleg
    esborrant les que algú hagués afinat.

    ── PER QUÈ IMPORTA ────────────────────────────────────────────────────────────────
    Trenca la PRECEDÈNCIA TEMPORAL: l'última mesura escrita és la veritat i el seu origen ha
    de ser el que li correspon. Un `MANUAL` fals diu «això ho va teclejar algú» sobre una
    xifra que va sortir d'una presa de proto, i qui després auditi «qui va mesurar això» rep
    una resposta falsa que ja no es pot desfer —`origen` el sobreescriu el canvi següent i
    no és append-only (`MeasurementChangeLog` sí, i és qui salva els mobles).

    ── LA REGLA ───────────────────────────────────────────────────────────────────────
    · Si el payload ho diu EXPLÍCITAMENT, mana el payload. Sempre.
    · Si no ho diu i la fila NEIX, `MANUAL` i les toleràncies del catàleg: és el naixement,
      no hi ha res a trepitjar.
    · Si no ho diu i la fila JA HI ÉS:
        - amb el valor CANVIAT → `MANUAL` (algú l'acaba de teclejar: l'origen li correspon);
        - amb el valor IGUAL   → **no es toca res**. Aquesta escriptura no ha mesurat res.
    Les toleràncies, un cop la fila existeix, no es reescriuen mai des del catàleg: són
    patrimoni de la fila i el catàleg només les sembra.
    """
    origen = m.get('origen', _NO_DIT)
    if origen is not _NO_DIT and origen:
        bm.origen = origen
    elif es_nova or bm.base_value_cm != valor_nou:
        bm.origen = 'MANUAL'

    for camp, defecte in (('tolerancia_minus', pom.tolerancia_default_minus),
                          ('tolerancia_plus', pom.tolerancia_default_plus)):
        dit = m.get(camp, _NO_DIT)
        if dit is not _NO_DIT:
            setattr(bm, camp, dit)
        elif es_nova:
            setattr(bm, camp, defecte)


def _write_base(model, pom, valor, auth_user, motiu, capa=None, instancia='', garment=''):
    """Escriu el BaseMeasurement de LA MESURA indicada i deixa que F1 registri.

    ── FASE_3/C1-ins · L'EXPLICACIÓ CANÒNICA DELS LITERALS D'AQUEST FITXER ──────────────
    Els escriptors de `models_app/views.py` que reben el POM per HTTP (`{'pom_id': …}`) no
    poden COPIAR els eixos de cap fila d'origen: el contracte d'entrada no els porta, i no
    els portarà fins a C4-ins. La llei de la fase és que **cap escriptor de les 9 taules
    deixi els eixos al default implícit**: o els copia d'una fila que els sap dir, o els
    declara amb el literal del cas. Aquí toca el segon.

    La diferència amb el que hi havia no és cosmètica. Amb el lookup curt, un
    `get_or_create(model, pom)` sobre una família de dues germanes o bé n'agafa una a l'atzar
    o bé peta amb `MultipleObjectsReturned`; amb el lookup complet, sap exactament sobre
    quina escriu. I quan C4-ins obri el contracte, el lloc on posar el valor real ja hi és:
    només canvia d'on ve.

    ✅ C4/BLOC 2 — ELS EIXOS SÓN PARÀMETRE. El contracte d'entrada ja els porta, o sigui que
    la crida pot dir de quina germana parla en comptes de declarar-la. Qui no els passi rep el
    literal de sempre —l'exterior de la instància única—, que és el que feien tots els punts
    d'aquest fitxer fins ara i el que han de seguir fent mentre la seva porta no els sàpiga dir.

    Els altres punts d'aquest fitxer porten una nota d'una línia que apunta aquí.

    ✅ SET-2/F1 — I EL TERCER EIX, QUE ERA EL QUE PETAVA. El docstring de sobre descrivia
    el mode de fallada del lookup curt («o bé n'agafa una a l'atzar o bé peta amb
    `MultipleObjectsReturned`») per a `capa`/`instancia`, i era paraula per paraula el que
    passava amb `garment`: dues files vives que només difereixen per la peça hi cauen totes
    dues a sobre i el `get_or_create` fa `.get()` sobre un queryset de 2. Mesurat a
    staging: POM 962 del model 1379 i POM 904 del 1320 → **500 determinista**, no una cursa.

    🚨 **`is_active` NO ENTRA AL LOOKUP.** La lectura temptadora de la diagnosi («una poda
    no cura el 500») porta a afegir-hi `is_active=True`, i seria canviar un 500 per un
    altre: la clau única és `(model, pom, capa, instancia, garment)` i NO inclou
    `is_active`, o sigui que amb la fila de la peça PODADA el lookup no la trobaria i
    intentaria crear-ne una segona amb la mateixa clau → `IntegrityError`. La clau sencera
    ja garanteix com a màxim UNA fila; l'eix sol cura el 500. I reviure la fila podada en
    escriure-hi és el comportament correcte: qui n'ajusta la talla la vol viva.
    """
    from fhort.models_app.models import BaseMeasurement
    from fhort.pom.models import MeasurementLayer
    bm, _created = BaseMeasurement.objects.get_or_create(
        model=model, pom=pom,
        capa=capa or MeasurementLayer.SLUG_DEFECTE, instancia=instancia or '',
        garment=garment or '',
        defaults={'base_value_cm': valor, 'origen': 'STANDARD'})
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
    # G2 (2026-07-31) — «té regles?» viatja amb l'estat perquè Propagar pugui MIRAR ABANS també
    # això, no només si hi ha propagació prèvia. Sense regla NO es propaga mai (condició dura de
    # P2), i el front ha de poder portar el tècnic a informar-la en lloc d'ensenyar-li el toast
    # mut del 400. És EL MATEIX predicat que el gate dur de `generate_grading_view` (:2354) i que
    # el del motor: un sol `_te_regles`, com mana G6/0b — dos predicats serien dues veritats.
    from fhort.pom.services import _te_regles
    # STEPPER DE MESURES (§6 · Agus 09/08). Les quatre portes de Mesures es pinten pel seu ESTAT
    # —fet · disponible · bloquejat amb motiu— i l'estat el sap el backend, no la pantalla. Es
    # diuen aquí i no en un endpoint nou perquè aquesta ja és LA vista d'estat d'aquest circuit:
    # dos endpoints per a la mateixa pregunta acabarien donant dues respostes.
    #   · te_mesures — hi ha alguna mesura base amb valor (el pas «Editar POM» està fet);
    #   · te_taula   — hi ha versió activa amb specs, que és el que «Mesurar prenda» exigeix i el
    #                  que el model 1320 no tenia (el gate deia la veritat: no hi era).
    #
    # B4 (10/08) — I ELS DOS FETS QUE FALTAVEN, que és el que feia que el stepper i el Dashboard
    # es contradiguessin. El Dashboard deia «Mesurar prenda: Feta» i «Escalat: Feta» i el stepper
    # pintava les dues portes com si res: no és que discrepessin, és que el stepper **no tenia
    # cap fet per a aquests dos passos** i per tant no podia dir-ne res. Cap dels dos mentia.
    #
    # QUINA MANA, ara que totes dues poden parlar: **el FET del model**. Una `ModelTask` és el
    # testimoni de la FEINA —algú la pot marcar Feta sense que hi hagi res al model, i el seu
    # llistat va escopat per `view_team_tasks`, o sigui que depèn de qui mira—; el stepper diu
    # ON ÉS EL MODEL, i això no pot dependre ni d'un gest ni d'un permís. És la mateixa llei que
    # ja mana al gate d'entrada del tab Mesures (`pom_task_done` del MODEL, no de la llista) i
    # la que diu `CLAUDE.md`: la conformitat es mesura.
    #   · te_presa      — hi ha algun fitting amb contingut (algú ha mesurat una peça de debò,
    #                     no una graella oberta i no tocada). MATEIX predicat que el Repàs i la
    #                     Comprovació: `fitting.esdeveniments`.
    #   · te_propagacio — àlies de `te_dades_propagades` per al stepper, perquè el pas ④ es
    #                     pinti amb el mateix vocabulari que els altres tres i no calgui que la
    #                     pantalla sàpiga que dos noms són la mateixa cosa.
    from fhort.fitting.esdeveniments import peces_amb_contingut
    te_mesures = BaseMeasurement.objects.filter(
        model=model, is_active=True, base_value_cm__isnull=False).exists()
    te_taula = bool(gv and gv.is_active and GradedSpec.objects.filter(
        grading_version=gv, is_active=True).exists())
    return Response({
        'te_mesures': te_mesures,
        'te_taula': te_taula,
        'te_presa': bool(peces_amb_contingut(model.id)),
        'te_propagacio': te_dades,
        'te_dades_propagades': te_dades,
        'segellada': bool(gv and gv.aprovada),
        'version_number': gv.version_number if gv else None,
        'estalitud': com_a_dict(estalitud(gv)) if gv else None,
        'te_regles': _te_regles(model),
    })


@api_view(['POST'])
@permission_classes([_ExecuteTasksCap])
@bat_escriptura(SUP_MESURES)
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


# Sprint NOMS-POM (2026-07-30) — límit dur dels textos, el mateix que declara el model. Es
# valida aquí perquè un text massa llarg ha de tornar un 400 explicat, no una excepció de BD.
#
# DECISIÓ 7 (2026-08-28) — i ara `nom_fitxa` hi entra, que és el motiu del canvi. Els tres
# camps són EL BATEIG DE LA FILA: els dos noms llargs i la nomenclatura curta. Fins avui la
# nomenclatura s'escrivia pel PATCH genèric del viewset —el que obre tota la fila (valor base,
# `origen`, `is_active`, toleràncies…)— i és exactament el risc que el docstring d'aquesta
# vista ja argumentava per als noms. Una porta, auditada, per a les tres coses.
#
# ⚠️ EL LÍMIT NO ÉS UN, SÓN DOS, i per això això és un diccionari i no una tupla amb un màxim
# al costat: `nom_canonic_model`/`nom_traduit_model` són `CharField(160)` i `nom_fitxa` és
# `CharField(20)` (`models_app/models.py:748`). Amb un sol màxim de 160, un `nom_fitxa` de 30
# caràcters hauria passat la validació i hauria petat a la BD amb un 500 mut — que és
# precisament el que aquesta constant existeix per evitar.
NOMS_POM_MAX = 160
NOMS_POM_LIMITS = {
    'nom_canonic_model': 160,
    'nom_traduit_model': 160,
    'nom_fitxa': 20,
}
NOMS_POM_CAMPS = tuple(NOMS_POM_LIMITS)


@api_view(['PATCH'])
@permission_classes([_ExecuteTasksCap])
def base_measurement_noms_view(request, bm_id):
    """PATCH …/base-measurements/<bm_id>/noms/  Body: {nom_canonic_model?, nom_traduit_model?, nom_fitxa?}

    EL BATEIG DEL MODEL: els TRES textos amb què aquest model anomena la mesura — el nom
    canònic EN, la traducció del client i la NOMENCLATURA CURTA del croquis. Buit ('') NO és un
    valor a cap dels tres: és tornar la fila al catàleg.

    DECISIÓ 7 (2026-08-28) — `nom_fitxa` hi entra i SURT del PATCH genèric del viewset (allà
    queda `read_only`). Fins avui la nomenclatura s'escrivia per la porta ampla, que és el que
    el paràgraf de sota desaconsella per als noms; no hi havia cap raó perquè el codi curt
    tingués una llei diferent de la dels dos noms que l'acompanyen a la mateixa cel·la.
    És també l'única porta on es comprova la UNICITAT dins de l'àmbit de la fila (F2).

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
        limit = NOMS_POM_LIMITS[camp]
        if len(valor) > limit:
            return Response(
                {'error': f'«{camp}» no pot passar de {limit} caràcters.'}, status=400)
        canvis[camp] = valor

    if not canvis:
        return Response(
            {'error': 'Cal com a mínim un de: ' + ', '.join(NOMS_POM_CAMPS) + '.'}, status=400)

    # DECISIÓ 7 · F2 — LA UNICITAT DINS DE L'ÀMBIT DE LA FILA (model + garment + capa).
    #
    # Es comprova AQUÍ, a la porta, i no amb un `unique_together`: la constraint hauria de
    # cobrir també les files que hi ha, i el cens del 28/08 les ha de trobar netes abans que
    # ningú la pugui posar (v. l'acta). Mentrestant aquesta és la porta per on passa tota
    # edició humana de nomenclatura, que és on la col·lisió es pot explicar en comptes de
    # petar.
    #
    # La consulta i la frase viuen a `pom/nomenclatura.py` i no aquí, pel mateix argument que
    # `frase_de_colisio`: el refús ha de sonar igual vingui d'on vingui.
    #
    # ⚠️ NOMÉS si el valor CANVIA. Re-desar una fila amb la nomenclatura que ja tenia no és
    # cap col·lisió —és el mateix argument que `excloent_pom_id` a `colisio_de_codi`— i sense
    # aquesta condició el cens del 28/08 es tornaria una trampa: hi ha 4 parelles vives a
    # `fhort` (bm 3389/3390 'SR', 2288/2289 i 2230/2231 'J1', 3386/3387 'B') que són el MATEIX
    # POM en dues INSTÀNCIES compartint codi. Són anteriors a aquesta llei i precisament el que
    # ve a evitar; fins que es netegin, qui obri el llapis en una d'elles i deixi el codi tal
    # com estava ha de poder desar el NOM sense que se li refusi res.
    if 'nom_fitxa' in canvis and canvis['nom_fitxa'] != bm.nom_fitxa:
        from fhort.pom.nomenclatura import (
            colisio_de_nomenclatura, frase_de_colisio_nomenclatura,
        )
        germana, _etiqueta, context = colisio_de_nomenclatura(bm, canvis['nom_fitxa'])
        if germana is not None:
            return Response({
                'error': frase_de_colisio_nomenclatura(canvis['nom_fitxa'], context),
                'codi': 'NOMENCLATURA_DUPLICADA',
                'conflicte': context,
            }, status=409)

    for camp, valor in canvis.items():
        setattr(bm, camp, valor)
    bm.save(update_fields=[*canvis.keys(), 'updated_at'])
    batec_de_request(request, bm.model_id, SUP_MESURES)   # F1.3 — batejar una fila és treballar

    return Response({
        'id': bm.id,
        'nom_canonic_model': bm.nom_canonic_model,
        'nom_traduit_model': bm.nom_traduit_model,
        'nom_fitxa': bm.nom_fitxa,
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
        # C2/Onada 1 — CLAU COMPOSTA (pom, capa) a tota la cadena d'estadis. `changes_by_ev`,
        # `snapshot`, `displayed` i el lookup de `takes` són el MATEIX espai de claus i han de
        # créixer junts. El perill aquí no és perdre una fila: és que el carry-forward
        # arrossegui el valor d'una capa cap endavant per la fila d'una altra —una base que
        # aquella capa no ha tingut mai—, que és exactament el símptoma del 205 que FIX-2 va
        # tancar per l'altra porta (els overrides de talla no-base).
        # El payload NO canvia: les files segueixen sortint amb `pom_id` sol; la capa només
        # viu a la clau interna, i `bm.capa` la porta a cada fila.
        # FASE_2/C1-ins — i la INSTÀNCIA entra al mateix espai de claus, amb el mateix perill
        # exacte i un de propi: aquí el carry-forward arrossegaria la presa de la sisa dreta
        # per la fila de l'esquerra. La comporta encara ho fa impossible, però aquest lector
        # és el node del PIN —13 tests el vigilen— i és el que ha d'arribar-hi ja correcte.
        # El payload segueix sense canviar: `pom_id` sol a la fila, els dos eixos a la clau.
        changes_by_ev[key][(c.pom_id, c.capa, c.instancia)] = float(c.valor_nou)

    # Snapshots acumulats (carry-forward) per estadi.
    snapshot, stages, stage_snaps = {}, [], []
    for ev in events:
        snapshot.update(changes_by_ev[ev['key']])
        stages.append(ev)
        stage_snaps.append(dict(snapshot))

    # FaseD — descarta els estadis (columnes de presa) sense CAP valor displayable per a les files
    # mostrades (p.ex. events de POMs després desactivats): no es pinten columnes buides.
    displayed = {(bm.pom_id, bm.capa, bm.instancia) for bm in bms}
    keep = [i for i in range(len(stages))
            if any(stage_snaps[i].get(clau) is not None for clau in displayed)]
    stages = [stages[i] for i in keep]
    stage_snaps = [stage_snaps[i] for i in keep]

    rows = []
    for bm in bms:
        pom = bm.pom
        tm, tp = _tol(bm)
        takes = {}
        # C2/Onada 1 + C1-ins — la fila demana ELS SEUS estadis, no els del POM.
        clau_bm = (pom.id, bm.capa, bm.instancia)
        for i, st in enumerate(stages):
            v = stage_snaps[i].get(clau_bm)
            if v is not None:
                takes[st['key']] = v
        rows.append({
            'pom_id': pom.id,
            # FONT ÚNICA (22/08) — codi i noms del catàleg pel resolutor de
            # `pom/nomenclatura.py` (ÀLIES > TENANT > GLOBAL).
            'pom_code': codi_de(pom),
            'nom_fitxa': bm.nom_fitxa or '',
            'nom_ca': noms_de(pom)['nom_ca'],
            'nom_en': noms_de(pom)['nom_en'],
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
            # C4/BLOC 2 — ELS DOS EIXOS AL CONTRACTE. El quart lector de la mateixa espècie que
            # A1/A2/A3: resol la identitat sencera aquí dins (`clau_bm`, i `displayed` per
            # `(pom, capa, instancia)`) i després no la deia.
            #
            # Aquí no és només llegir. Aquesta vista alimenta la graella de MESURES, que és
            # l'única superfície amb poda (`measureSources.supportsPoda`): sense els eixos, el
            # front no pot dir QUINA germana treu, i `desactivar_pom` no té com saber-ho.
            'capa': bm.capa,
            'instancia': bm.instancia,
            # SET-2/R11 — I EL TERCER EIX, pel mateix argument literal, un eix més tard:
            # aquesta vista alimenta Comprovació i la graella de Mesures, i sense ell la
            # pantalla no pot distingir dues prendes. És l'eix d'una FILA —dada factual,
            # de quina peça és aquesta mesura— i per tant entra per l'acta de T6a
            # («servir l'eix d'una fila és sempre legítim»), no per la de la resolució.
            'garment': bm.garment,
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
            'model_tasks__ronda',
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
        minuts_per_tecnic = {}   # M2 · etiqueta -> minuts SANS d'aquest pas (per al `qui`)
        for tm in mt.timers.all():
            if not tram_compta(tm):      # timer obert (B1-a) o tram desbocat → fora
                continue
            task_minutes += tm.minuts
            total_minutes += tm.minuts
            if tm.tecnic_id is not None:
                label = (tm.tecnic.nom_complet or tm.tecnic.user.get_username()) if tm.tecnic else str(tm.tecnic_id)
                slot = per_tech.setdefault(tm.tecnic_id, {'technician_id': tm.tecnic_id, 'label': label, 'minutes': 0})
                slot['minutes'] += tm.minuts
                minuts_per_tecnic[label] = minuts_per_tecnic.get(label, 0) + tm.minuts
        # M2 — DUES ADDICIONS READ-ONLY, i cap camp nou a cap taula.
        #
        # `ronda_seq`: el registre d'activitat s'agrupa per VOLTA (mockup B v3) i el pas no deia
        # de quina era. Creuar-ho pel `task_type` seria ambigu precisament al cas que importa:
        # amb rondes, el MATEIX code apareix un cop per volta i les files no es podrien
        # distingir. `null` = feina d'abans del canvi de llei o nascuda al buit entre voltes
        # (mateix contracte que `ModelTaskSerializer.ronda_seq`).
        #
        # `qui`: el tècnic que hi ha posat MÉS MINUTS SANS, no l'`assignee`. La lliçó és la de
        # F1.5 i la repeteix `ModelTaskSerializer.obert_per`: `assignee` és PLANIFICACIÓ i el
        # rellotge és REALITAT, i un registre d'ACTIVITAT ha de dir qui la va fer. Sense cap
        # tram sa, `null` — «ningú no hi ha treballat» és una dada, no un forat a omplir amb
        # el nom de qui la tenia assignada.
        qui = None
        if minuts_per_tecnic:
            qui = max(minuts_per_tecnic.items(), key=lambda kv: (kv[1], kv[0]))[0]
        steps.append({
            'task_type': mt.task_type.name if mt.task_type_id else None,
            'status': mt.status,
            'minutes': task_minutes,
            'started_at': mt.started_at,
            'finished_at': mt.finished_at,
            'ronda_seq': mt.ronda.seq if mt.ronda_id else None,
            'qui': qui,
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
        # M3 · FIT-9/10 — el banner de la fitxa ha de poder dir PER QUÈ està acabat i des de
        # quan. Sense el motiu, «Acabat» i «Tret de catàleg» —que són fets ben diferents— es
        # pintarien igual, i el segon és el que explica per què no hi haurà més voltes.
        'motiu_tancament': model.motiu_tancament,
        'data_tancament': model.data_tancament.isoformat() if model.data_tancament else None,
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
                 .select_related('task_type', 'assignee', 'ronda')
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
        # M2 — ADDICIÓ READ-ONLY: de quina VOLTA és la tasca. El Pla de treball s'agrupa per
        # ronda (mockup A v2) i aquest compositor era l'únic lloc que no ho deia. NO es fa
        # llegint `/model-task-items/`, que ja porta `ronda`/`ronda_seq`: aquell endpoint té
        # ABAST PER FILA (`scope_model_task_queryset`) i a un tècnic sense VIEW_TEAM_TASKS li
        # amagaria les tasques d'altri — el Pla passaria a ensenyar-ne menys de les que ensenya
        # avui, i en silenci. El compositor no scopa, i per això la volta ha de sortir d'aquí.
        # `ronda_seq` null = feina d'abans del canvi de llei (M1-bis · FIT-4) o nascuda al buit
        # entre voltes: mateix contracte que `ModelTaskSerializer.ronda_seq`.
        'ronda': t.ronda_id,
        'ronda_seq': t.ronda.seq if t.ronda_id else None,
    } for t in pla_tasks]

    # --- Q3: atenció tècnica — alertes POM PENDENTS de resoldre ---
    # Anomalia de dades PARCIALMENT tancada (03/08): els ESTAT_CHOICES del model són
    # Pendent/Acceptat/Corregit. L''Obert' que escrivien els dos disparadors de creació
    # (FITTING pom/s10_views.py i MANUAL pom/s11_views.py) ja NO s'escriu: era sinònim de
    # 'Pendent' —el `default` del camp— i s'ha substituït pel valor declarat.
    # 🚩 QUEDA OBERT el 'Resolt' de pom/s11_views.py:96, que NO té sinònim declarat exacte:
    # 'Acceptat' (la desviació s'accepta) i 'Corregit' (la mesura s'ha corregit) són
    # resolucions DIFERENTS, i triar-ne una és decisió de domini, no de neteja.
    # Per això aquest lector es queda com és. Per NO amagar alertes reals, "pendent" = NO resolt:
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

    # FASE_3/C1-ins — el DIFF de promoció es fa amb la CLAU COMPLETA a les tres bandes
    # (`actuals`, `poms_item`, `poms_model`). Aquest endpoint compara el patrimoni d'un model
    # amb el d'un item i decideix què s'hi escriu: per `pom_id` sol, dues germanes del model
    # es comparaven totes dues contra la mateixa fila de l'item, i el veredicte
    # forat/divergent/igual sortia de l'última llegida. La promoció escriuria l'estàndard del
    # taller a partir d'un diff que no sap de què parla.
    actuals = ({(i.pom_id, i.capa, i.instancia): i
                for i in ItemBaseMeasurement.objects.filter(base_set=base_set)}
               if base_set is not None else {})
    # LLEI 6 — el superset de POMs de l'item. El que en surti s'ha d'AMPLIAR amb confirmació.
    poms_item = set(GarmentPOMMap.objects.filter(garment_type_item=item)
                    .values_list('pom_id', 'capa', 'instancia'))

    # ── El DIFF (pur, sense escriure).
    forats, divergents, iguals, ampliaria_item = [], [], [], []
    for bm in fonts:
        clau_bm = (bm.pom_id, bm.capa, bm.instancia)
        actual = actuals.get(clau_bm)
        fila = {
            'pom_id': bm.pom_id,
            'codi': bm.nom_fitxa or bm.pom.codi_client or '',
            'nom': bm.pom.nom_client or '',
            'valor_model': float(bm.base_value_cm),
            # Camps INTERNS (no de contracte): el bucle d'aplicació els necessita per
            # retrobar la fila exacta, i el `next(...)` de sota no els pot deduir del
            # `pom_id`. El payload els ignora fins a C4-ins.
            '_capa': bm.capa,
            '_instancia': bm.instancia,
        }
        if clau_bm not in poms_item:
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

    # «Sobrarien» és el complement del diff, i s'ha de calcular amb la MATEIXA clau. L'ORM no
    # sap fer `exclude` per tupla, o sigui que el complement es fa en Python sobre el conjunt
    # de claus completes — que és el que `exclude(pom_id__in=…)` volia dir i no deia.
    poms_model = {(bm.pom_id, bm.capa, bm.instancia) for bm in fonts}
    sobrarien = ([{
        'pom_id': i.pom_id,
        'codi': i.nom_fitxa or i.pom.codi_client or '',
        'nom': i.pom.nom_client or '',
        'valor_item': float(i.base_value_cm) if i.base_value_cm is not None else None,
        'origen_item': i.origen,
    } for i in ItemBaseMeasurement.objects
        .filter(base_set=base_set)
        .select_related('pom').order_by('pom__codi_client')
        if (i.pom_id, i.capa, i.instancia) not in poms_model] if base_set is not None else [])

    # FASE_3/C1-ins — el PAYLOAD no canvia. Les files de treball porten `_capa`/`_instancia`
    # perquè el bucle d'aplicació ha de retrobar la fila EXACTA, però són estat intern: el
    # contracte d'aquest endpoint no porta eixos fins a C4-ins, i afegir-hi camps ara seria
    # el primer canvi visible del tram. Es netegen aquí, en un sol lloc.
    def _sense_intern(files):
        return [{k: v for k, v in f.items() if not k.startswith('_')} for f in files]

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
        'forats': _sense_intern(forats),
        # LLEI 5 — es mostren els dos valors i NO es toquen. Modificar-los és l'acte canònic.
        'divergents': _sense_intern(divergents),
        'iguals': _sense_intern(iguals),
        # LLEI 6 — mai en silenci.
        'ampliaria_item': _sense_intern(ampliaria_item),
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
            # FASE_3/C1-ins — la pertinença nova neix amb els eixos de la mesura que la
            # justifica, no amb literals: si el model mesura la sisa esquerra, la plantilla
            # ha de reclamar la sisa esquerra.
            GarmentPOMMap.objects.get_or_create(
                garment_type_item=item, pom_id=fila['pom_id'],
                capa=fila['_capa'], instancia=fila['_instancia'],
                # pendent_revisio=False: els confirma un tècnic amb gate CONFIGURE, no un clon
                # automàtic de germà (que és el cas que va inventar la marca).
                defaults={'ordre': ordre_seguent, 'pendent_revisio': False},
            )

        escrits = 0
        if not talla_divergent:
            for fila in forats:
                # Per la clau COMPLETA: amb `pom_id` sol, el `next(...)` es quedava amb la
                # primera germana i el valor promogut podia ser el de l'altra.
                bm = next(b for b in fonts
                          if (b.pom_id, b.capa, b.instancia)
                          == (fila['pom_id'], fila['_capa'], fila['_instancia']))
                # LLEI 4 — NOMÉS forats. `update_or_create` sobre una fila amb valor seria
                # exactament l'acte que aquesta llei prohibeix; per això la clau del create és
                # el forat i els divergents ni entren al bucle.
                obj, creat = ItemBaseMeasurement.objects.get_or_create(
                    base_set=base_set, pom_id=bm.pom_id,
                    capa=bm.capa, instancia=bm.instancia,
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

    # FASE_3/C1-ins — literals: el body és `{'pom': …}` i no porta eixos. El `.first()` per
    # `pom_id` sol escrivia l'ACTE CANÒNIC de la marca sobre una germana a l'atzar, i aquest
    # endpoint és precisament el que existeix perquè el valor de l'estàndard no el decideixi
    # ningú de passada. V. `_write_base` per a l'argument sencer dels literals.
    actual = (ItemBaseMeasurement.objects.select_related('pom')
              .filter(base_set=base_set, pom_id=pom_id,
                      capa=MeasurementLayer.SLUG_DEFECTE, instancia='').first())
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
@bat_escriptura(SUP_MESURES)
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

    ✅ C4/BLOC 2 — EL DEUTE PAGAT: LA RUTA JA DIU DE QUINA GERMANA PARLA.
    El que hi havia deia: «quan la ruta sàpiga dir la capa i la instància, aquest ancoratge
    se'n va». Ara ho sap, i se n'ha anat.

    Els eixos entren pel COS, no pel camí. El camí segueix sent
    `/models/<model_id>/pom/<pom_id>/desactivar/` perquè aquesta petició ja és un POST amb cos
    (`{motiu}`) i perquè una `instancia` buida —el cas normal— no té representació honesta dins
    d'una URL: `.../pom/12//desactivar/` i `.../pom/12/-/desactivar/` són dues maneres
    d'escriure el mateix i totes dues conviden a equivocar-se. La resolució passa per
    `_identitat_de_mesura`, el mateix punt únic que fan servir els dos upserts i les dues podes.

    QUI NO ELS DIU rep el literal de sempre —l'exterior de la instància única—, exactament com
    abans d'aquest canvi. No es mira mai quines files hi ha per triar-ne una: aquell desempat
    a l'atzar (el `Meta.ordering` de `BaseMeasurement` no inclou `instancia`, models.py:759) és
    el que aquest tram existeix per matar, i aquí el preu era especialment alt perquè
    l'escriptura deixa entrada al `MeasurementChangeLog` via `_desactivat`: una fila MAL
    ATRIBUÏDA en una taula append-only, que no es podrà corregir mai.

    Body: `{motiu?: str, capa?: str, instancia?: str}`.
    """
    from fhort.models_app.models import BaseMeasurement

    capa, instancia, garment = _identitat_de_mesura(request.data)
    bm = (BaseMeasurement.objects
          .filter(model_id=model_id, pom_id=pom_id, is_active=True,
                  capa=capa, instancia=instancia, garment=garment)
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
        # C4/BLOC 2 — la resposta diu QUINA fila ha caigut. Amb germanes vives, «s'ha podat el
        # POM 12» no és una resposta: n'hi ha dues i el client ha de poder confirmar que la que
        # ha marxat és la que ell mirava.
        # S42/F1 — i la PRENDA amb elles. El filtre d'aquesta vista ja resol els QUATRE eixos
        # des de F5+, però la resposta n'emetia dos: amb dues peces vives, «s'ha podat la
        # capa exterior de la instància única» segueix sense dir QUINA fila ha caigut, que és
        # justament el que el comentari de sobre diu que aquesta resposta serveix per fer.
        'capa': bm.capa,
        'instancia': bm.instancia,
        'garment': bm.garment,
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

    # C2/Onada 1 — ÀNCORA DE SEMBRA: regla compartida (3c.1). La regla de graduació és una
    # llei d'INCREMENTS i no té capa per decisió de domini —el folre d'un pit creix el mateix
    # que el seu exterior, perquè la peça és la mateixa peça—, o sigui que sembrar-ne els
    # `valors_step` demana UNA font i no la barreja de totes les capes del POM. L'exterior és
    # l'àncora. Sense el filtre, `dict()` es quedaria amb l'últim `size_label` llegit i la
    # regla naixeria amb valors de capes diferents barrejats, sense cap rastre.
    # FASE_2/C1-ins — el segon eix va al mateix filtre i tapa el mateix forat: la clau del
    # `dict()` és la TALLA, o sigui que dues instàncies del mateix POM es disputarien cada
    # cel·la i la regla naixeria mig d'una i mig de l'altra. Una regla és compartida entre
    # instàncies (decisió Montse), però la SEMBRA de la qual neix ha de sortir d'una de sola.
    from fhort.pom.models import MeasurementLayer
    valors = dict(GradedSpec.objects
                  .filter(grading_version=gv, pom_id=pom_id, is_active=True,
                          capa=MeasurementLayer.SLUG_DEFECTE, instancia='')
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
@bat_escriptura(SUP_ESCALAT)
def set_step_valor_view(request, model_id, pom_id):
    """TRAM E · LA PORTA DEL VALOR VERMELL (decisió d'Agus, 2026-08-21).

    `POST /api/v1/models/<model_id>/pom/<pom_id>/step-valor/`
    Body: `{talla, valor, capa?, instancia?, garment?}`

    Una cel·la que ha sortit amb el valor de la talla base PRESTAT (regla STEP sense valor per a
    aquella talla) s'edita AQUÍ, i el que s'escriu és **`valors_step` de la `ModelGradingRule`**.

    ── PER QUÈ LA REGLA I NO UN OVERRIDE ──────────────────────────────────────────────────────
    Les dues formes existien i el cens les va contrastar (acta d'E+F §2). La que decideix:
    **propagar amb `new_version=True` esborra TOTS els `ModelGradingOverride` del model** —el
    «llenç net», que és llei— o sigui que el tècnic hauria escrit vint xifres a mà i el primer
    «Propagar» conscient se les hauria endut sense dir res. Escrivint la REGLA, el valor
    sobreviu a totes les re-propagacions perquè **és** la regla: la cel·la surt del vermell per
    la raó correcta, no perquè algú l'hagi tapada.

    L'override no es jubila: es queda per al seu ús propi —la decisió puntual per talla que el
    llenç net ha d'esborrar per disseny—. Són dues intencions diferents i ara tenen dues portes.

    ── LA CADENA DE DELTES, QUE ÉS EL QUE FA AQUESTA PORTA DELICADA ───────────────────────────
    `valors_step` no desa valors: desa **deltes entre veïns**, acumulats cap enfora des de la
    base. Per tant escriure «la M mesura 101.5» vol dir escriure `delta[M] = 101.5 − valor(veí
    cap a la base)`, i el veí ha de tenir valor CALCULABLE. Si el camí fins aquí té forats, el
    valor demanat no es pot expressar i la porta **rebutja dient quina talla s'ha d'omplir
    primer** (`STEP_CAMI_INCOMPLET`): omplir-los amb un 0 seria fabricar la corba plana que la
    llei D2 prohibeix, i fer-ho en silenci seria pitjor.

    Efecte lateral volgut i inherent al règim STEP: com que els deltes són relatius, corregir
    una talla desplaça les de MÉS ENFORA que ja tinguin delta. És el que vol dir STEP.

    Re-propaga IN PLACE sobre la versió vigent (com feia la porta d'override): sense això la
    marca cauria —es deriva de la REGLA— però la xifra seguiria sent la prestada fins a la
    propagació següent, i la pantalla diria dues coses alhora.
    """
    from fhort.models_app.models import ModelGradingRule
    from fhort.pom.grading_regime import (CODI_STEP_CAMI_INCOMPLET, valida_valor_step)
    from fhort.pom.grading_utils import step_delta_acumulat
    from fhort.pom.services import escala_del_model, generate_graded_specs
    from fhort.fitting.services import _resolve_working_size_fitting

    data = request.data or {}
    model = Model.objects.filter(pk=model_id).first()
    if model is None:
        return Response({'detail': 'Model no trobat.'}, status=404)

    # Els eixos, pel punt únic de la casa: la regla només travessa `garment` (D4), però la
    # MESURA BASE d'on surt la corba sí que és de (capa, instància, garment).
    capa, instancia, garment = _identitat_de_mesura(data)

    rule = ModelGradingRule.objects.filter(
        model=model, pom_id=pom_id, garment=garment).first()
    if rule is None:
        return Response({'detail': "Aquest POM no té regla al model: informa-la des de Graduació.",
                         'codi': 'STEP_SENSE_REGLA'}, status=400)

    try:
        size_run, run_sistema, _pos, base_idx = escala_del_model(model)
    except (ValueError, AttributeError) as e:
        return Response({'detail': f'Geometria de talles incompleta: {e}'}, status=400)

    talla = (data.get('talla') or '').strip()
    valor, err = valida_valor_step(rule.logica, talla, data.get('valor'),
                                   model.base_size_label, size_run)
    if err:
        return Response({'detail': err['detall'], 'codi': err['codi']}, status=400)

    base_bm = BaseMeasurement.objects.filter(
        model=model, pom_id=pom_id, capa=capa, instancia=instancia, garment=garment,
        is_active=True, base_value_cm__isnull=False).first()
    if base_bm is None:
        return Response({'detail': "Aquesta mesura no té valor de talla base: la corba no té d'on sortir.",
                         'codi': 'STEP_SENSE_BASE'}, status=400)
    base_val = float(base_bm.base_value_cm)

    # Posició EN ESPAI DE SISTEMA (llei S24b) i el veí cap a la base.
    #
    # 🚨 AQUÍ HI HAVIA UN SEGON JUDICI DE «ÉS LA TALLA BASE?» (21/08). Deia el mateix fet que
    # `valida_valor_step` acaba de dir quatre línies més amunt —i amb el mateix codi de
    # rebuig, `STEP_TALLA_BASE`, escrit a mà—, però el MESURAVA D'UNA ALTRA MANERA: el punt
    # únic compara ETIQUETES contra `model.base_size_label`; això comparava ÍNDEXS contra el
    # `base_idx` d'`escala_del_model`. Mentre els dos coincideixin, aquesta branca no s'assoleix
    # mai; i el dia que divergissin, la que mana és la primera —o sigui que el segon judici no
    # protegeix de res i només fabrica la il·lusió que sí. És l'espècie del fix A i la del
    # 400 d'avui: dues mesures del mateix fet.
    # El que es queda és la FEINA (la posició, que fa falta per trobar el veí); el que marxa
    # és el JUDICI. Si algun dia la porta ha de dir alguna cosa nova sobre la talla base, ho
    # dirà `valida_valor_step`, que és qui en sap.
    idx = _pos(talla)
    idx_vei = idx - 1 if idx > base_idx else idx + 1
    total_vei, falta = step_delta_acumulat(rule, run_sistema, base_idx, idx_vei)
    if falta is not None:
        return Response({
            'detail': (f"Abans d'aquesta talla cal el valor de la {falta}: els valors d'una "
                       "regla STEP són passos entre talles veïnes i es completen des de la "
                       "talla base cap enfora."),
            'codi': CODI_STEP_CAMI_INCOMPLET,
            'talla_que_falta': falta,
        }, status=400)
    valor_vei = base_val + (total_vei or 0.0)

    # El delta és el PAS entre el veí i aquesta talla, sempre comptat cap enfora (és la
    # convenció de `valors_step`, i la que `step_delta_acumulat` desfà: pujant se suma, baixant
    # es resta).
    delta = round(valor - valor_vei if idx > base_idx else valor_vei - valor, 2)

    with transaction.atomic():
        # L'etiqueta es desa amb l'ORTOGRAFIA DEL RUN, com fa `valida_breaks`: el motor compara
        # normalitzat, però la dada que es desa ha de ser llegible i estable.
        etiqueta = next((x for x in run_sistema if x.strip().upper() == talla.upper()), talla)
        vs = dict(rule.valors_step or {})
        vs[etiqueta] = delta
        rule.valors_step = vs
        rule.origen = 'MANUAL'
        rule.save(update_fields=['valors_step', 'origen', 'updated_at'])

        sf = _resolve_working_size_fitting(model)
        if sf is not None:
            try:
                generate_graded_specs(sf.id)
            except SealedGradingVersionError as e:
                transaction.set_rollback(True)
                return Response(e.payload, status=409)
            except ValueError as e:
                transaction.set_rollback(True)
                return Response({'detail': str(e)}, status=400)

    # Les talles que ENCARA porten el valor prestat, amb el mateix predicat del motor: la
    # pantalla ha de poder treure el vermell d'aquesta i deixar-lo a les que segueixen.
    pendents = []
    for etiqueta_run in size_run:
        try:
            i_run = _pos(etiqueta_run)
        except (ValueError, KeyError):
            continue
        if step_delta_acumulat(rule, run_sistema, base_idx, i_run)[1] is not None:
            pendents.append(etiqueta_run)

    return Response({
        'model': model.id, 'pom': int(pom_id), 'garment': garment,
        'talla': etiqueta, 'delta': delta, 'valor': round(valor, 2),
        'valors_step': rule.valors_step,
        'step_base_copiada': pendents,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@bat_escriptura(SUP_ESCALAT)
def set_pom_regim_view(request, model_id, pom_id):
    """PG-4b-3a / P3 — UPSERT de la REGLA resident (ModelGradingRule) per (model, pom).

    La regla (règim + deltes + break) és patrimoni VIU del MODEL (origen='MANUAL'); el motor la
    llegeix via _load_grading_rules→_apply_rule (NO es toca el CÀLCUL). Body (tots opcionals;
    s'actualitza només el que ve):
      - logica: 'LINEAR' | 'STEP'
      - increment_base: float|null   (delta base, p.ex. 4)
      - increment_break: float|null  (delta a partir del trencament, p.ex. 2.5)
      - talla_break_label: str|null  (talla d'inici del break; del run del model)
      - breaks: [{inici, final, delta}]|null  (TRAM F — intervals; etiquetes del run del
        SISTEMA en convenció de MOTOR, extrems inclusius, màx. `MAX_BREAKS`. Llista buida o
        null = la regla no en porta, i el camp es desa NULL.)
    Si la resident no existeix: es materialitza des del fallback del catàleg; si tampoc n'hi ha,
    es crea de nou (autoria manual de la regla des de zero). Innocu sobre el grading persistent
    (no toca GradedSpec/GradingVersion; només el proper generate_graded_specs).

    Passar a STEP amb `valors_step` buit els SEMBRA des dels GradedSpec vigents del model per a
    aquell POM (`_sembra_step_des_dels_specs`): la fila STEP neix amb els números que ja es
    veien, editables. Els specs només es LLEGEIXEN.
    """
    from fhort.models_app.models import ModelGradingRule
    from fhort.pom.models import GradingRule
    from fhort.pom.services import escala_del_model

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

    # SET-2/#12d — DE QUINA PRENDA ÉS LA REGLA. La clau de `ModelGradingRule` és
    # `(model, pom, garment)` des de T3 i la comporta que la congelava va caure al #12, però
    # aquest contracte encara identificava la regla amb el `pom_id` pelat: editar-la des del
    # contenidor de la 02 escrivia sobre la de la mare. L'eix surt del punt únic de la casa
    # (`_identitat_de_mesura`), i qui no el diu —el 100% dels clients d'avui— rep la mare,
    # exactament com abans.
    garment = _identitat_de_mesura(data)[2]

    with transaction.atomic():
        rule = ModelGradingRule.objects.filter(
            model=model, pom_id=pom_id, garment=garment).first()
        if rule is None:
            # Sembra des del fallback del catàleg si n'hi ha; si no, regla nova (autoria de zero).
            # ⚠️ El joc del CATÀLEG no porta `garment` i no en pot portar: és una llei
            # reutilitzable, mai propietat d'un model ni d'una prenda (v. `pom.GradingRule`).
            # La sembra, doncs, es busca igual per a totes dues prendes; el que neix amb l'eix
            # és la resident.
            src = (GradingRule.objects.filter(
                       rule_set_id=model.grading_rule_set_id, pom_id=pom_id).first()
                   if model.grading_rule_set_id else None)
            rule = ModelGradingRule(
                model=model, pom_id=pom_id, garment=garment, actiu=True,
                logica=(src.logica if src else 'LINEAR'),
                increment=(src.increment if src else 0),
                valors_step=(src.valors_step if src else None),
                increment_base=(src.increment_base if src else None),
                increment_break=(src.increment_break if src else None),
                talla_break_label=(src.talla_break_label if src else None),
                talla_break_pos=(src.talla_break_pos if src else None),
                # TRAM F — els intervals viatgen amb la resta de la forma: una resident que neix
                # del joc ha de néixer amb el relleu SENCER del joc, no amb la meitat. És el
                # mateix defecte que el clon de perfil arrossegava fins al fix A.
                breaks=(src.breaks if src else None),
                # M3 — el criteri d'aquest upsert, i el sap ell mateix: si la fila NEIX del
                # fallback del catàleg (`src`), ve d'aquell joc, per molt que el `MANUAL` de
                # sota li digui el contrari —és exactament la mentida que M3 desfà. Si neix
                # sense `src`, és autoria de zero i el camp es queda NULL.
                derivat_de_rule_set_id=(src.rule_set_id if src else None),
            )
        # Si la fila JA EXISTIA no es toca `derivat_de_rule_set`: editar-la no canvia d'on va
        # néixer. El camp diu la PROCEDÈNCIA, no qui l'ha tocada l'últim (això és `origen`).

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
        # TRAM F — ELS INTERVALS. Es validen contra el run del SISTEMA (no el del model): és
        # l'espai on el motor resol el relleu (llei S24b), i un interval que acabi a una talla
        # que el sistema té i el model no fabrica segueix sent llegible — que és exactament la
        # forma de tota regla d'1 break llegida com a interval.
        #
        # Només quan el client els ENVIA (`has`), com la resta de camps: sota STEP el relleu es
        # conserva LATENT, igual que `increment_base` i `valors_step` (PG-4b-3a). El motor no
        # el llegeix mentre el règim sigui STEP, i torna a manar si algú refà la regla LINEAR.
        if has('breaks'):
            try:
                _sr, run_sistema, _p, _bi = escala_del_model(model)
            except (ValueError, AttributeError):
                run_sistema = []
            nets, err_breaks = valida_breaks(
                data.get('breaks'), logica=rule.logica, run=run_sistema,
                increment_base=rule.increment_base)
            if err_breaks:
                return Response({'detail': err_breaks['detall'], 'codi': err_breaks['codi']},
                                status=400)
            rule.breaks = nets

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
                                rule.increment_break, rule.talla_break_label, rule.breaks):
            return Response({
                'detail': MISSATGE_LINEAR_ZERO,
                'codi': CODI_LINEAR_ZERO,
            }, status=400)

        rule.origen = 'MANUAL'
        rule.save()

    return Response({
        'model': model.id,
        'pom': rule.pom_id,
        # SET-2/#12d — la resposta diu QUINA regla ha canviat. Amb dues prendes, «s'ha desat
        # la regla del POM 12» no és una resposta: n'hi pot haver dues i el client ha de poder
        # confirmar que la que ha canviat és la que ell mirava. Mateixa llei que la resposta
        # de `desactivar_pom` a C4/BLOC 2.
        'garment': rule.garment,
        'logica': rule.logica,
        'origen': rule.origen,
        'increment_base': float(rule.increment_base) if rule.increment_base is not None else None,
        'increment_break': float(rule.increment_break) if rule.increment_break is not None else None,
        'talla_break_label': rule.talla_break_label,
        # TRAM F — la resposta diu el relleu SENCER: la pantalla desa per presència de clau i ha
        # de poder confirmar què ha quedat desat sense tornar a demanar la taula.
        'breaks': rule.breaks or [],
    })


# ── M3 · EL CICLE DE VIDA DEL MODEL — les tres portes (FIT-9 · FIT-10 · FIT-11) ──────────────
#
# ✅ CAPABILITY: **`CLOSE_GATES`**, i no és una tria per analogia. És la capacitat de GOVERN de
# la casa: és la que gateja els actes que mouen un MODEL sense executar-ne cap tasca —
# `gate_model_view`, `regress_model_view` i `gate_bulk_view` («accions de govern post-reunió»,
# `tasks/views_b.py:827-897`)— i la que segella una versió de graduació (`fitting/views.py:75`:
# «aprovar és un gate, i els gates són decisió humana i gated»). Acabar, jubilar i reobrir un
# model són exactament això: decisions de responsable sobre el model sencer. Per rol la tenen
# `manager` i `admin`, no el `technician` ni el `product_manager` (`accounts/capabilities.py`).
#
# Per què NO `_ExecuteTasks` (la d'M1 per a l'entrega): entregar una volta és feina de qui
# treballa —«qui pot treballar pot entregar»—, i tancar el model és tancar-ho tot, inclosa la
# feina viva d'altri. Aquí NO cal el TODO que M1 va haver de declarar: la capability existia.

class _CloseGates(HasCapability):
    """Gate de GOVERN (CLOSE_GATES) per als actes del cicle de vida del model."""
    required_capability = CLOSE_GATES


def _model_i_perfil(request, model_id):
    """(model, profile, resposta_d_error). La resposta és None quan tot va bé."""
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return None, None, Response({'error': 'Usuari sense perfil en aquest tenant.',
                                     'code': 'no_profile'}, status=http_status.HTTP_403_FORBIDDEN)
    try:
        model = Model.objects.get(pk=model_id)
    except Model.DoesNotExist:
        return None, None, Response({'error': 'Model no trobat.'},
                                    status=http_status.HTTP_404_NOT_FOUND)
    return model, profile, None


def _estat_del_model(model, entrega=None):
    """La forma que tornen les tres portes: l'estat VIU + l'últim rastre. Una sola forma per a
    les tres, perquè la cara no hagi d'aprendre'n tres."""
    ultim = model.esdeveniments_estat.select_related('per').first()   # ordering: -quan
    return {
        'model_id': model.pk,
        'estat': model.estat,
        'motiu_tancament': model.motiu_tancament,
        'data_tancament': model.data_tancament.isoformat() if model.data_tancament else None,
        'rastre': None if ultim is None else {
            'de': ultim.de_estat, 'a': ultim.a_estat, 'motiu': ultim.motiu,
            'per': ultim.per.nom_complet if ultim.per_id else None,
            'quan': ultim.quan.isoformat(),
        },
        'entrega': None if entrega is None else {
            'id': entrega.pk, 'ronda_seq': entrega.ronda.seq,
            'destinatari': entrega.destinatari, 'data': entrega.data.isoformat(),
        },
    }


@api_view(['POST'])
@permission_classes([_CloseGates])
def tancar_model_view(request, model_id):
    """POST /api/v1/models/<model_id>/tancar/ · {motiu, confirmar_entrega?, destinatari?, descripcio?}

    FIT-10 — l'acte humà que acaba un model. `motiu` ∈ {`acabat`, `tret_de_cataleg`}.

    🚨 **AMB RONDA OBERTA CONTESTA 409, I EL 409 ÉS LA PREGUNTA.** Porta `code='ronda_oberta'`,
    les dades de la volta i **`requereix_entrega`**, perquè la cara sàpiga quina pregunta ha de
    fer. Amb `confirmar=true` la segona crida ho fa tot en una transacció, i el que fa amb la
    volta depèn del motiu (CODA d'M3):

      · `acabat`           → entrega (porta d'M1) → tancament de la volta i de la feina viva
                             (FIT-13 + FIT-6) → `estat='acabat'`. Demana `destinatari`.
      · `tret_de_cataleg`  → **cap entrega** (FIT-1: l'Entrega registra fets que han passat) →
                             `tancar_ronda` → `estat='acabat'`.

    `confirmar_entrega` s'accepta com a àlies de `confirmar`: és el nom que la porta va publicar
    a M3 i el que els fums escrits abans de la CODA segueixen enviant.
    """
    from .services_cicle import CicleVidaError, tancar_model

    model, profile, err = _model_i_perfil(request, model_id)
    if err is not None:
        return err
    dades = request.data or {}
    try:
        entrega = tancar_model(
            model, motiu=dades.get('motiu'), profile=profile,
            confirmar=_truthy(dades.get('confirmar')) or _truthy(dades.get('confirmar_entrega')),
            destinatari=(dades.get('destinatari') or '').strip(),
            descripcio=(dades.get('descripcio') or '').strip())
    except CicleVidaError as e:
        codi = (http_status.HTTP_409_CONFLICT if e.code == 'ronda_oberta'
                else http_status.HTTP_400_BAD_REQUEST)
        return Response({'error': str(e), 'code': e.code, **e.dades}, status=codi)
    model.refresh_from_db()
    return Response(_estat_del_model(model, entrega), status=http_status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_CloseGates])
def reobrir_model_view(request, model_id):
    """POST /api/v1/models/<model_id>/reobrir/ · {motiu?}

    FIT-11 — el model torna a OBERT. Què es fa a dins (rectificar la darrera volta o obrir-ne
    una de nova) és una decisió posterior i separada, i el guard d'FIT-11 viu a
    `transition_task`, no aquí.
    """
    from .services_cicle import CicleVidaError, reobrir_model

    model, profile, err = _model_i_perfil(request, model_id)
    if err is not None:
        return err
    try:
        reobrir_model(model, profile=profile,
                      motiu=((request.data or {}).get('motiu') or '').strip())
    except CicleVidaError as e:
        return Response({'error': str(e), 'code': e.code}, status=http_status.HTTP_400_BAD_REQUEST)
    model.refresh_from_db()
    return Response(_estat_del_model(model), status=http_status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_CloseGates])
def jubilar_model_view(request, model_id):
    """POST /api/v1/models/<model_id>/jubilar/ · {motiu?}  — FIT-9, l'arxiu. Només des d'`acabat`."""
    from .services_cicle import CicleVidaError, jubilar_model

    model, profile, err = _model_i_perfil(request, model_id)
    if err is not None:
        return err
    try:
        jubilar_model(model, profile=profile,
                      motiu=((request.data or {}).get('motiu') or '').strip())
    except CicleVidaError as e:
        return Response({'error': str(e), 'code': e.code}, status=http_status.HTTP_400_BAD_REQUEST)
    model.refresh_from_db()
    return Response(_estat_del_model(model), status=http_status.HTTP_200_OK)
