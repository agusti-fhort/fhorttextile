"""Fitxers del CATÀLEG (ItemFitxer) — S03b · P4.

Mirall del `ModelFitxerViewSet` retallat a S03a · P0.1: lectura ampla (IsAuthenticated),
escriptura gated per `CONFIGURE` (el catàleg és configuració, no feina de model). L'única via
d'escriptura és `services_fitxers.save_item_file`, que manté la invariant de cadena.
"""
from django.core import signing
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from fhort.accounts.capabilities import CONFIGURE, HasCapability
from fhort.tasks.models import GarmentTypeItem

from .models import ItemFitxer, Model
from .serializers import ItemFitxerSerializer
from .services_fitxers import (DOWNLOAD_TTL, ITEM_DOWNLOAD_SALT, UploadRejected,
                               delete_fitxer_bytes, get_version_chain, marcar_procedencia,
                               save_item_file, serve_fitxer, validate_upload)


class ItemFitxerViewSet(mixins.CreateModelMixin,
                        mixins.DestroyModelMixin,
                        viewsets.ReadOnlyModelViewSet):
    """list/retrieve/create/destroy + versions + download + download-signed."""
    serializer_class = ItemFitxerSerializer
    queryset = ItemFitxer.objects.select_related('garment_type_item', 'pujat_per').all()
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['garment_type_item', 'tipus', 'is_current']
    ordering_fields = ['data_pujada']
    ordering = ['-data_pujada']

    def get_permissions(self):
        # Lectura i descàrrega: qualsevol autenticat. `download_signed` porta el permís al
        # token (D13) i s'exclou de tot gate. Escriptura: CONFIGURE (com GarmentTypeItemViewSet).
        if self.action == 'download_signed':
            return [AllowAny()]
        # `usar_al_model` escriu al MODEL, no al catàleg → mateix gate que upload_file_view.
        if self.action in ('list', 'retrieve', 'versions', 'download', 'usar_al_model'):
            return [IsAuthenticated()]
        p = HasCapability()
        self.required_capability = CONFIGURE
        return [p]

    def perform_destroy(self, instance):
        """Esborra els bytes abans de la fila: `instance.delete()` sol deixa orfes al disc."""
        delete_fitxer_bytes(instance)
        instance.delete()

    def create(self, request, *args, **kwargs):
        """POST /api/v1/item-fitxers/  (multipart: garment_type_item, fitxer, [tipus], [nom],
        [versio_anterior_id]). NO passa pel serializer: l'escriptura la governa save_item_file."""
        item_id = request.data.get('garment_type_item')
        uploaded = request.FILES.get('fitxer')
        if not item_id or not uploaded:
            return Response({'error': 'garment_type_item i fitxer són obligatoris.'}, status=400)

        item = get_object_or_404(GarmentTypeItem, pk=item_id)
        nom = request.data.get('nom') or uploaded.name

        try:
            validate_upload(uploaded, nom)   # D12
        except UploadRejected as e:
            return Response({'error': str(e)}, status=400)

        versio_anterior = None
        va_id = request.data.get('versio_anterior_id')
        if va_id:
            versio_anterior = ItemFitxer.objects.filter(
                pk=va_id, garment_type_item=item).first()
            if versio_anterior is None:
                return Response(
                    {'error': 'versio_anterior_id no vàlid per a aquest item.'}, status=400)

        fitxer = save_item_file(item, uploaded, versio_anterior=versio_anterior,
                                tipus=request.data.get('tipus') or None, nom=nom)
        perfil = getattr(request.user, 'profile', None)
        if perfil is not None:
            fitxer.pujat_per = perfil
            fitxer.save(update_fields=['pujat_per'])

        return Response(self.get_serializer(fitxer).data, status=201)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Cadena de versions completa (read-only), ordenada per versio."""
        chain = get_version_chain(self.get_object())
        return Response(self.get_serializer(chain, many=True).data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Descàrrega gated per capçalera Authorization."""
        return serve_fitxer(self.get_object())

    # NOTA: aquí NO es posa `permission_classes=[AllowAny]` a l'@action (com sí fa
    # ModelFitxerViewSet): aquest ViewSet sobreescriu get_permissions(), que decideix per
    # `self.action` i mai llegeix self.permission_classes → seria codi mort i una trampa de
    # manteniment. `authentication_classes=[]` sí que hi va: get_authenticators() no està
    # sobreescrit i llegeix l'atribut en temps real.
    @action(detail=True, methods=['get'], url_path='download-signed',
            authentication_classes=[])
    def download_signed(self, request, pk=None):
        """Descàrrega signada (D13). Vegeu ModelFitxerViewSet.download_signed."""
        token = request.query_params.get('token') or ''
        try:
            signed_id = signing.loads(token, salt=ITEM_DOWNLOAD_SALT, max_age=DOWNLOAD_TTL)
        except signing.SignatureExpired:
            return HttpResponseForbidden('Enllaç de descàrrega caducat.')
        except signing.BadSignature:
            return HttpResponseForbidden('Enllaç de descàrrega no vàlid.')

        if str(signed_id) != str(pk):
            return HttpResponseForbidden('El token no correspon a aquest fitxer.')

        inline = request.query_params.get('inline') == '1'
        return serve_fitxer(self.get_object(), as_attachment=not inline)

    @action(detail=True, methods=['post'], url_path='usar-al-model')
    def usar_al_model(self, request, pk=None):
        """POST /api/v1/item-fitxers/<id>/usar-al-model/  Body: {model_id}   [S03b · P5]

        Cicle ① catàleg→model: **importació, no edició in-place**. Crea un ModelFitxer NOU al
        model amb els MATEIXOS bytes i el mateix `tipus`, amb `derivat_de_item` apuntant a
        l'origen. L'ItemFitxer NO es toca mai: no és una edició compartida, és una còpia amb
        procedència.

        Un `.ftt` es copia tal qual: el ZIP és auto-contingut des de S03a · P3 (els `src` són
        noms interns `assets/<sha16>.<ext>`), per tant no cal reescriure cap referència. La
        resta de tipus (DXF, SVG, PDF, imatges) són còpia directa de bytes.

        NO existeix la promoció inversa (② model→catàleg): forat amb nom, diferit.

        Gate: `IsAuthenticated` (via get_permissions), el MATEIX que `upload_file_view`.
        L'escriptura va al MODEL, no al catàleg: qui pot pujar un fitxer al model pot
        importar-n'hi un. Exigir CONFIGURE aquí impediria al tècnic fer la seva feina.
        """
        from .serializers import ModelFitxerSerializer
        from .services_fitxers import save_model_file

        origen = self.get_object()
        if not origen.fitxer:
            return Response({'error': "El fitxer d'origen no té bytes."}, status=400)

        model_id = request.data.get('model_id')
        if not model_id:
            return Response({'error': 'model_id és obligatori.'}, status=400)
        model = get_object_or_404(Model, pk=model_id)

        # Còpia de bytes: es reobre l'origen i es passa a save_model_file, que recalcula
        # checksum/mida/mimetype sobre el contingut real (no els copia a cegues) i manté la
        # invariant de cadena del ModelFitxer nou (cadena pròpia: versio=1, is_current=True).
        origen.fitxer.open('rb')
        try:
            nou = save_model_file(model, origen.fitxer, tipus=origen.tipus,
                                  origen='upload', nom=origen.nom_fitxer)
        finally:
            origen.fitxer.close()

        # Mateix helper que el germà model→model (views.ModelFitxerViewSet.usar_al_model).
        marcar_procedencia(nou, request.user, derivat_de_item=origen)

        return Response(ModelFitxerSerializer(nou, context={'request': request}).data,
                        status=201)
