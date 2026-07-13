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
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from fhort.fitting.models import GradingVersion
from fhort.models_app.models import BaseMeasurement, Model
from fhort.models_app.services_fitxers import (DOWNLOAD_TTL, UploadRejected,
                                               serve_fitxer, validate_upload)
from fhort.tasks.models import GarmentTypeItem

from .adapters import DjangoGeometryStore
from .engine.aama_reader import AAMAReader
from .engine.errors import PatternParseError
from .engine.rul_reader import RULReader, coherencia_dxf_rul
from .export import PERFILS_DISPONIBLES, ExportBlocked, build_export
from .models import ExportAcknowledgement, PatternFile, PatternPOM
from .serializers import (PatternFileLlistaSerializer, PatternFileSerializer,
                          PatternGeometrySerializer)
from .services import delete_pattern_bytes, save_pattern_file
from .svg import render_document

logger = logging.getLogger(__name__)

#: Salts PROPIS, al costat dels de `models_app.services_fitxers`. El payload del token és
#: només l'id: amb un salt compartit, un token de ModelFitxer id=5 validaria aquí.
PATTERN_DOWNLOAD_SALT = 'pattern_file_download'
PATTERN_RUL_DOWNLOAD_SALT = 'pattern_file_rul_download'

#: L'últim recurs de la tolerància, quan ni la mesura ni el catàleg en diuen res. Mateixa
#: xifra que `pom.s10_views.TOL_FALLBACK`: una mesura no pot tenir una tolerància aquí i
#: una altra allà segons quina pantalla la miri.
TOL_FALLBACK = 0.6


def _tol(de_la_mesura, del_cataleg):
    """La tolerància de la MESURA mana; la del catàleg és el pla B; 0.6 és l'últim recurs."""
    for v in (de_la_mesura, del_cataleg):
        if v is not None:
            return float(v)
    return TOL_FALLBACK

#: ⚠️ TEXT PROVISIONAL — PENDENT D'ADVOCAT ABANS DE PRODUCCIÓ REAL.
#: Viu aquí i no al frontend perquè és el text que es DESA a `ExportAcknowledgement`: el
#: registre ha de guardar el que l'usuari va veure de debò, i si la font fos el bundle del
#: navegador, el que quedaria desat seria el que el navegador d'aquell dia deia. El
#: frontend el rep per l'API i el mostra; no en té una còpia.
GATE_TEXT_CA = (
    'Aquest fitxer ha estat generat automàticament. Cal obrir-lo al teu CAD i verificar '
    'geometria, costures i grading abans de tallar.'
)


def _preview_payload(resultat) -> dict:
    """El resultat del pipeline → el que el modal ensenya.

    Hi surt tot el que qui exporta ha de poder mirar abans de fer-se'n responsable, i
    especialment **el que NO ha entrat a la niada**: les omissions no es filtren ni es
    resumeixen en un número. Un modal que amaga que un POM no s'ha graduat convertiria el
    gate en un tràmit.
    """
    proj = resultat.projeccio
    return {
        'talles': [
            {
                'talla': sp.talla,
                'es_base': sp.es_base,
                'bbox_cm': [round(v / 10.0, 1) for v in sp.bbox],
                'ok': sp.ok,
                'poms': [
                    {
                        'pom_code': p.pom_code,
                        'peca': p.peca,
                        'valor_cm': (round(p.valor_cm, 2) if p.valor_cm is not None else None),
                        'delta_llegit_cm': (
                            round(p.delta_llegit_cm, 2)
                            if p.delta_llegit_cm is not None else None),
                        'delta_spec_cm': p.delta_spec_cm,
                        'desviament_cm': p.desviament_cm,
                        # El valor que la FITXA declara. No té per què coincidir amb el que
                        # el patró mesura: es mostra perquè es vegi, no perquè quadri.
                        'valor_spec_cm': p.valor_spec_cm,
                        'ok': p.ok,
                        'error': p.error,
                    }
                    for p in sp.poms
                ],
                'costures': [
                    {
                        'sew_id': s.sew_id,
                        'casa': bool(s.check and s.check.casa),
                        'missatge': (s.check.missatge if s.check else s.error),
                        'desviament_cm': (
                            round(s.check.desviament_cm, 2) if s.check else None),
                    }
                    for s in sp.costures
                ],
            }
            for sp in resultat.previews
        ],
        'omissions': [
            {'codi': o.codi, 'pom_code': o.pom_code, 'missatge': o.missatge}
            for o in proj.omissions
        ],
        'problemes_poms': list(resultat.problemes_poms),
        'regles': proj.regles_actives,
        'autovalidacio': {
            'ok': resultat.autovalidacio.ok,
            'resum': resultat.autovalidacio.resum(),
            'punts_comparats': resultat.autovalidacio.punts_comparats,
            'desviacio_maxima_um': resultat.autovalidacio.desviacio_maxima_um,
        },
        'text_gate': GATE_TEXT_CA,
    }


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
        .prefetch_related('pieces__points', 'pieces__segments', 'pieces__poms__pom_master')
        .all()
    )
    # MultiPart/Form per a l'upload (que porta els bytes del DXF); JSON per a l'exportació,
    # que és una crida amb un cos d'objectes. Sense el JSONParser, `POST …/export/` amb un
    # `application/json` respon 415 i el modal no arriba ni a demanar-ho.
    parser_classes = [MultiPartParser, FormParser, JSONParser]
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

    # ── La llista de treball del taller ──────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='model-poms')
    def model_poms(self, request, pk=None):
        """Les Mesures del model creuades amb l'estat d'ancoratge en AQUEST patró.

        La pregunta que el taller fa tota l'estona és una de sola: «d'això que la fitxa
        diu que s'ha de mesurar, què he col·locat ja, i el que he col·locat quadra?».
        Respondre-la des del client volia dir baixar-se dues llistes i creuar-les a mà; el
        creuament és de domini (la frontissa és el POMMaster) i viu aquí.

        Read-only. Cada fila porta el que la fitxa mana (codi de client, nomenclatura del
        croquis, nom canònic, valor a talla base, tolerància) i, si el POM ja és al patró,
        el que el patró mesura (peça, valor mesurat) i la DIFERÈNCIA — que és tot el que
        això persegueix. La tolerància només qualifica la diferència quan n'hi ha: sense
        tolerància es dona la xifra i no es jutja.
        """
        fp = self.get_object()
        if fp.model_id is None:
            # Un patró penjat d'un GarmentTypeItem (l'altra branca del XOR) no té fitxa de
            # model: no hi ha res per creuar, i dir-ho és millor que tornar una llista buida
            # que sembli «aquest model no té mesures».
            return Response(
                {'error': 'Aquest patró no penja de cap model: no té fitxa de mesures.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ancorats = {
            p.pom_master_id: p
            for p in PatternPOM.objects
            .filter(pattern_piece__pattern_file=fp)
            .select_related('pattern_piece', 'pom_master')
        }

        files = []
        base = (
            BaseMeasurement.objects
            .filter(model_id=fp.model_id, is_active=True)
            .select_related('pom', 'pom__pom_global')
            .order_by('ordre', 'pom__codi_client')
        )
        for bm in base:
            pom, glob = bm.pom, bm.pom.pom_global
            anc = ancorats.get(bm.pom_id)

            # La tolerància de la mesura mana sobre la del catàleg; el 0.6 de la casa és
            # l'últim recurs (mateixa escala que `s10_views._tolerance_map`).
            tol_minus = _tol(bm.tolerancia_minus, pom.tolerancia_default_minus)
            tol_plus = _tol(bm.tolerancia_plus, pom.tolerancia_default_plus)

            fila = {
                'base_measurement': bm.id,
                'pom_master': bm.pom_id,
                'codi_client': pom.codi_client,
                'nom_fitxa': bm.nom_fitxa,
                'nom_client': pom.nom_client,
                'nom_canonic': glob.nom_ca or glob.nom_en if glob else '',
                'codi_global': glob.codi if glob else '',
                'valor_fitxa_cm': bm.base_value_cm,
                'tolerancia_minus_cm': tol_minus,
                'tolerancia_plus_cm': tol_plus,
                'is_key': bm.is_key,
                'ancorat': anc is not None,
                'pattern_pom': None,
                'pattern_piece': None,
                'peca': None,
                'valor_mesurat_cm': None,
                'delta_cm': None,
                'dins_tolerancia': None,
            }

            if anc is not None:
                fila.update({
                    'pattern_pom': anc.id,
                    'pattern_piece': anc.pattern_piece_id,
                    'peca': anc.pattern_piece.nom_block,
                    'valor_mesurat_cm': anc.valor_mesurat_cm,
                })
                # La Δ només existeix si hi ha les DUES xifres. Un POM col·locat sobre una
                # mesura sense valor de fitxa (origen TEMPLATE) es pot mesurar igualment,
                # però no hi ha res amb què comparar-lo: la Δ es queda a None i no s'inventa.
                if anc.valor_mesurat_cm is not None and bm.base_value_cm is not None:
                    delta = round(anc.valor_mesurat_cm - bm.base_value_cm, 2)
                    fila['delta_cm'] = delta
                    fila['dins_tolerancia'] = -tol_minus <= delta <= tol_plus

            files.append(fila)

        return Response({
            'pattern_file': fp.id,
            'model': fp.model_id,
            'total': len(files),
            'ancorats': sum(1 for f in files if f['ancorat']),
            'results': files,
        })

    # ── L'escalat: previsualitzar i exportar ─────────────────────────────────
    @action(detail=True, methods=['get'], url_path='grading-versions')
    def grading_versions(self, request, pk=None):
        """Les versions de grading APROVADES del model d'aquest patró. Només aquestes.

        No s'ofereix la «versió activa» ni la «vigent»: `aprovada` i `is_active` són
        ortogonals (a staging, 3 de les 4 aprovades NO són l'activa), i qui exporta una
        niada tria una versió SIGNADA, no la que la UI serveix per defecte.
        """
        fp = self.get_object()
        if fp.model_id is None:
            return Response([])

        versions = (
            GradingVersion.objects
            .filter(size_fitting__model_id=fp.model_id, aprovada=True)
            .select_related('size_fitting')
            .order_by('-data', '-id')
        )
        return Response([
            {
                'id': gv.id,
                'nom': gv.nom,
                'data': gv.data,
                'version_number': gv.version_number,
                'is_active': gv.is_active,
                'specs': gv.graded_specs.filter(is_active=True).count(),
            }
            for gv in versions
        ])

    @action(detail=True, methods=['post'], url_path='export-preview')
    def export_preview(self, request, pk=None):
        """La taula que l'usuari ha de mirar ABANS de reconèixer res.

        Fa el pipeline sencer —projecció, previsualització i autovalidació— i NO torna
        bytes. Si l'exportació fallaria, ha de fallar aquí, amb el modal obert i el motiu a
        la vista, i no després que algú hagi clicat que se'n fa responsable.
        """
        try:
            resultat = build_export(
                self.get_object(),
                grading_version_id=int(request.data.get('grading_version_id') or 0),
                destination_profile=request.data.get('destination_profile') or 'polypattern',
            )
        except (TypeError, ValueError):
            return Response({'error': 'Cal un `grading_version_id` numèric.'}, status=400)
        except ExportBlocked as e:
            return Response(e.as_dict(), status=422)

        return Response(_preview_payload(resultat))

    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        """POST … /export/ → el DXF de la niada. **El gate és una precondició dura.**

        `{grading_version_id, destination_profile, acknowledged: true}`.

        Sense `acknowledged`, no es genera res: ni s'arriba a cridar el motor. L'ordre
        importa —primer el gate, després els bytes— perquè un 403 després d'haver fabricat
        el fitxer seria un gate de mentida.

        El RUL germà es descarrega a part (`export-rul`), amb els mateixos paràmetres: són
        dos artefactes, no un (esmena E3), i el navegador no pot baixar-ne dos d'una sola
        resposta.
        """
        fp = self.get_object()

        if request.data.get('acknowledged') is not True:
            return Response(
                {
                    'error': 'Aquesta exportació necessita un reconeixement explícit.',
                    'text_gate': GATE_TEXT_CA,
                },
                status=403,
            )

        try:
            grading_version_id = int(request.data.get('grading_version_id') or 0)
        except (TypeError, ValueError):
            return Response({'error': 'Cal un `grading_version_id` numèric.'}, status=400)

        perfil = request.data.get('destination_profile') or 'polypattern'

        try:
            resultat = build_export(fp, grading_version_id, perfil)
        except ExportBlocked as e:
            return Response(e.as_dict(), status=422)

        # El registre entra ABANS de servir els bytes: si la BD falla, el fitxer no surt.
        ExportAcknowledgement.objects.create(
            pattern_file=fp,
            versio_patro=fp.versio,
            grading_version_id=grading_version_id,
            destination_profile=perfil,
            usuari=getattr(request.user, 'profile', None),
            texts_shown=request.data.get('texts_shown') or GATE_TEXT_CA,
        )

        resposta = HttpResponse(resultat.dxf, content_type='application/dxf')
        resposta['Content-Disposition'] = f'attachment; filename="{resultat.nom_dxf}"'
        return resposta

    @action(detail=True, methods=['post'], url_path='export-rul')
    def export_rul(self, request, pk=None):
        """El RUL germà de la niada. Mateix gate: sense reconeixement, no hi ha bytes."""
        fp = self.get_object()

        if request.data.get('acknowledged') is not True:
            return Response(
                {'error': 'Aquesta exportació necessita un reconeixement explícit.',
                 'text_gate': GATE_TEXT_CA},
                status=403,
            )

        try:
            resultat = build_export(
                fp,
                int(request.data.get('grading_version_id') or 0),
                request.data.get('destination_profile') or 'polypattern',
            )
        except (TypeError, ValueError):
            return Response({'error': 'Cal un `grading_version_id` numèric.'}, status=400)
        except ExportBlocked as e:
            return Response(e.as_dict(), status=422)

        resposta = HttpResponse(resultat.rul, content_type='application/octet-stream')
        resposta['Content-Disposition'] = f'attachment; filename="{resultat.nom_rul}"'
        return resposta

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
