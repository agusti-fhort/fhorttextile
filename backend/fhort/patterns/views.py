"""API del motor de patrons.

Convencions calcades de `commerce/` (S0-B9) i del pipeline de fitxers (S0-B1):

  · **L'escriptura NO passa pel serializer.** La governa `services.save_pattern_file`,
    que és qui sap mantenir la invariant de cadena. Mateixa decisió que
    `ModelFitxerViewSet`, que va haver de treure el create genèric perquè se la saltava.
  · **Un error de parse és un 422 amb detall, mai un 500.** Un DXF que el motor no entén
    no és una avaria del servidor: és una cosa que li passa al fitxer de l'usuari, i
    l'usuari ha de poder llegir què li passa.
  · **Els bytes surten per una porta de Django**, mai per l'`alias` d'nginx: `download`
    (gate per capçalera) i `download-signed` (gate al token, TTL 900 s). Amb **salts
    propis**: si en compartíssim un amb `ModelFitxer`, un token emès per al fitxer id=5
    d'allà obriria el patró id=5 d'aquí.
"""
import logging
from dataclasses import replace
from types import SimpleNamespace

from django.core import signing
from django.http import HttpResponse, HttpResponseForbidden
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from fhort.models_app.models import Model
from fhort.models_app.services_fitxers import (DOWNLOAD_TTL, UploadRejected,
                                               serve_fitxer, validate_upload)
from fhort.tasks.models import GarmentTypeItem

from .adapters import DjangoGeometryStore
from .engine.aama_reader import AAMAReader
from .engine.errors import PatternParseError
from .engine.rul_reader import RULReader, coherencia_dxf_rul
from .models import PatternFile
from .serializers import (PatternFileLlistaSerializer, PatternFileSerializer,
                          PatternGeometrySerializer)
from .services import delete_pattern_bytes, save_pattern_file
from .svg import render_document

logger = logging.getLogger(__name__)

#: Salts PROPIS, al costat dels de `models_app.services_fitxers`. El payload del token és
#: només l'id: amb un salt compartit, un token de ModelFitxer id=5 validaria aquí.
PATTERN_DOWNLOAD_SALT = 'pattern_file_download'
PATTERN_RUL_DOWNLOAD_SALT = 'pattern_file_rul_download'


def _rul_servable(fp: PatternFile):
    """Proxy que compleix el duck-type de `serve_fitxer` (fitxer / nom_fitxer / mimetype).

    `serve_fitxer` és la font única de bytes del projecte i espera un objecte amb un sol
    fitxer. Un `PatternFile` en porta dos, així que el RUL hi entra amb aquest embolcall
    en comptes d'obrir una segona via de servir bytes.
    """
    return SimpleNamespace(
        fitxer=fp.fitxer_rul,
        nom_fitxer=fp.nom_rul or 'patro.rul',
        mimetype='application/octet-stream',
    )


class PatternFileViewSet(mixins.CreateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.ReadOnlyModelViewSet):
    """list / retrieve / create / destroy + render.svg + descàrregues."""

    queryset = (
        PatternFile.objects
        .select_related('model', 'garment_type_item', 'pujat_per', 'versio_anterior')
        .prefetch_related('pieces__points')
        .all()
    )
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'garment_type_item', 'is_current', 'font_cad']
    ordering_fields = ['data_pujada', 'versio']
    ordering = ['-data_pujada']

    def get_serializer_class(self):
        if self.action == 'list':
            return PatternFileLlistaSerializer
        return PatternFileSerializer

    def get_permissions(self):
        # Les descàrregues signades porten el permís al token (D13) i no passen per cap
        # gate. La resta: autenticat. L'escriptura va al MODEL, no a un catàleg, així que
        # és la mateixa política que `upload_file_view` i `usar_al_model` (S0-B1).
        if self.action in ('download_signed', 'download_rul_signed'):
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_destroy(self, instance):
        """Els bytes dels DOS artefactes, abans de la fila: `delete()` sol els deixa orfes."""
        delete_pattern_bytes(instance)
        instance.delete()

    # ── POST: pujar i entendre un patró ──────────────────────────────────────
    def create(self, request, *args, **kwargs):
        """POST /api/v1/patterns/pattern-files/

        multipart: `fitxer_dxf` (obligatori) · `fitxer_rul` (opcional) ·
        `model` O `garment_type_item` · `versio_anterior_id` (opcional).
        """
        dxf = request.FILES.get('fitxer_dxf')
        if not dxf:
            return Response({'error': 'Falta el fitxer DXF (camp `fitxer_dxf`).'}, status=400)
        rul = request.FILES.get('fitxer_rul')

        propietari, error = self._resoldre_propietari(request)
        if error:
            return error

        versio_anterior, error = self._resoldre_versio_anterior(request, propietari)
        if error:
            return error

        for fitxer in (dxf, rul):
            if fitxer is None:
                continue
            try:
                validate_upload(fitxer)
            except UploadRejected as e:
                return Response({'error': str(e)}, status=400)

        # ── El motor. Un fitxer que no entenem és un 422 amb detall, mai un 500.
        try:
            document = AAMAReader().read(dxf.read())
        except PatternParseError as e:
            return Response(e.as_dict(), status=422)
        finally:
            dxf.seek(0)

        grade_table = None
        avisos = []
        if rul is not None:
            try:
                grade_table = RULReader().read(rul.read())
            except PatternParseError as e:
                return Response(e.as_dict(), status=422)
            finally:
                rul.seek(0)
            # El DXF i el RUL viatgen junts, però ningú no garanteix que siguin germans.
            avisos = [
                {'codi': i.codi, 'missatge': i.missatge, 'detall': i.detall}
                for i in coherencia_dxf_rul(document, grade_table)
            ]
            # UN sol document, amb el seu grading a dins: el store desa el document
            # sencer, i així no hi ha dues escriptures que puguin quedar desaparellades.
            document = replace(document, grade_table=grade_table)

        fp = save_pattern_file(
            model=propietari if isinstance(propietari, Model) else None,
            garment_type_item=propietari if isinstance(propietari, GarmentTypeItem) else None,
            dxf=dxf, rul=rul,
            document=document,
            versio_anterior=versio_anterior,
            nom=dxf.name,
            nom_rul=rul.name if rul else None,
        )

        profile = getattr(request.user, 'profile', None)
        if profile is not None:
            fp.pujat_per = profile
            fp.save(update_fields=['pujat_per'])

        # El document sencer: geometria, empremta i taula de grading.
        DjangoGeometryStore().save(document, pattern_file=fp)

        fp.refresh_from_db()
        dades = self.get_serializer(fp).data
        if avisos:
            # No bloquegen: el fitxer s'ha desat. Però el desajust s'ha de veure.
            dades['avisos_coherencia'] = avisos
        return Response(dades, status=201)

    def _resoldre_propietari(self, request):
        model_id = request.data.get('model')
        item_id = request.data.get('garment_type_item')

        if bool(model_id) == bool(item_id):
            return None, Response(
                {'error': 'Cal indicar exactament un propietari: `model` O '
                          '`garment_type_item` (mai tots dos, mai cap).'},
                status=400,
            )
        if model_id:
            obj = Model.objects.filter(pk=model_id).first()
            if obj is None:
                return None, Response({'error': f'El model {model_id} no existeix.'}, status=404)
            return obj, None

        obj = GarmentTypeItem.objects.filter(pk=item_id).first()
        if obj is None:
            return None, Response({'error': f"L'ítem {item_id} no existeix."}, status=404)
        return obj, None

    def _resoldre_versio_anterior(self, request, propietari):
        pk = request.data.get('versio_anterior_id')
        if not pk:
            return None, None

        anterior = PatternFile.objects.filter(pk=pk).first()
        if anterior is None:
            return None, Response(
                {'error': f'La versió anterior {pk} no existeix.'}, status=400)

        # Encadenar cap a un altre amo trencaria la sobirania del Model.
        mateix_amo = (
            anterior.model_id == getattr(propietari, 'id', None)
            or anterior.garment_type_item_id == getattr(propietari, 'id', None)
        )
        if not mateix_amo:
            return None, Response(
                {'error': 'La versió anterior pertany a un altre propietari.'}, status=400)

        if anterior.versions_posteriors.exists():
            # El constraint de BD també ho aturaria, però amb un 500. Aquí es diu per què.
            return None, Response(
                {'error': f'La versió {anterior.versio} ja té un successor: una cadena de '
                          f'versions no pot bifurcar.'},
                status=409,
            )
        return anterior, None

    # ── El visor ─────────────────────────────────────────────────────────────
    @action(detail=True, methods=['get'])
    def geometry(self, request, pk=None):
        """La geometria sencera, amb coordenades: el que el visor Konva dibuixa.

        El visor NO dibuixa des de l'SVG del servidor: dibuixa des d'AQUÍ. L'SVG és un
        render de DOCUMENT (paleta fixa, per imprimir i arxivar); el visor és una eina
        interactiva que necessita saber què és cada punt per poder-hi reaccionar. Un
        <img> no et pot dir que el cursor és a sobre d'un punt de gir.
        """
        return Response(PatternGeometrySerializer(self.get_object()).data)

    @action(detail=True, methods=['get'], url_path='render.svg')
    def render_svg(self, request, pk=None):
        """SVG del conjunt, o d'una peça (`?piece=BACK`). Render propi, no matplotlib."""
        fp = self.get_object()
        doc = DjangoGeometryStore().load_from(fp)
        svg = render_document(doc, piece_name=request.query_params.get('piece', ''))
        return HttpResponse(svg, content_type='image/svg+xml')

    # ── Els bytes ────────────────────────────────────────────────────────────
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """DXF, gated per capçalera Authorization."""
        return serve_fitxer(self.get_object())

    @action(detail=True, methods=['get'], url_path='download-rul')
    def download_rul(self, request, pk=None):
        fp = self.get_object()
        if not fp.fitxer_rul:
            return Response({'error': 'Aquest patró no porta RUL.'}, status=404)
        return serve_fitxer(_rul_servable(fp))

    @action(detail=True, methods=['get'], url_path='download-signed',
            authentication_classes=[])
    def download_signed(self, request, pk=None):
        fp, error = self._verificar_token(request, pk, PATTERN_DOWNLOAD_SALT)
        if error:
            return error
        inline = request.query_params.get('inline') == '1'
        return serve_fitxer(fp, as_attachment=not inline)

    @action(detail=True, methods=['get'], url_path='download-rul-signed',
            authentication_classes=[])
    def download_rul_signed(self, request, pk=None):
        fp, error = self._verificar_token(request, pk, PATTERN_RUL_DOWNLOAD_SALT)
        if error:
            return error
        if not fp.fitxer_rul:
            return Response({'error': 'Aquest patró no porta RUL.'}, status=404)
        return serve_fitxer(_rul_servable(fp))

    def _verificar_token(self, request, pk, salt):
        token = request.query_params.get('token') or ''
        try:
            signed_id = signing.loads(token, salt=salt, max_age=DOWNLOAD_TTL)
        except signing.SignatureExpired:
            return None, HttpResponseForbidden('Enllaç de descàrrega caducat.')
        except signing.BadSignature:
            # Aquí hi cau també el token d'un ALTRE model signat amb un altre salt: és
            # exactament per això que els salts són separats.
            return None, HttpResponseForbidden('Enllaç de descàrrega no vàlid.')

        if str(signed_id) != str(pk):
            return None, HttpResponseForbidden('El token no correspon a aquest fitxer.')
        return self.get_object(), None
