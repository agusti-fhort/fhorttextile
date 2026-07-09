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

from .models import ItemFitxer
from .serializers import ItemFitxerSerializer
from .services_fitxers import (DOWNLOAD_TTL, ITEM_DOWNLOAD_SALT, UploadRejected,
                               get_version_chain, save_item_file, serve_fitxer,
                               validate_upload)


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
        if self.action in ('list', 'retrieve', 'versions', 'download'):
            return [IsAuthenticated()]
        p = HasCapability()
        self.required_capability = CONFIGURE
        return [p]

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

    @action(detail=True, methods=['get'], url_path='download-signed',
            permission_classes=[AllowAny], authentication_classes=[])
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
