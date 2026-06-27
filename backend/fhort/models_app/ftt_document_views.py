"""Endpoints del document .ftt (crear / carregar / desar / servir assets).

El client mai rep el zip: load retorna document.json + URLs d'assets (servits per
FttDocumentAssetView, que desempaqueta el .ftt al backend). Desar genera una versió
nova encadenada via save_model_file (invariant is_current intacta).

NOTA (B3): encara NO hi ha enforcement de lock; arriba a B7 (lock sobre el document
lògic + timer-gap). De moment només IsAuthenticated.
"""
import mimetypes

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services_ftt_document as svc
from .models import Model, ModelFitxer
from .serializers import ModelFitxerSerializer


def _asset_urls(request, fitxer, asset_names):
    return {
        name: request.build_absolute_uri(
            "/api/v1/ftt-documents/%s/asset/%s/" % (fitxer.id, name)
        )
        for name in asset_names
    }


class FttDocumentCreateView(APIView):
    """POST models/<model_id>/ftt-document/ → crea la v1 (buit o des de plantilla)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, model_id):
        model = get_object_or_404(Model, pk=model_id)
        # template_id: reservat per a B5 (magatzem de plantilles). B3 crea buit.
        document_json = None
        fitxer = svc.create_document(model, document_json=document_json)
        return Response(ModelFitxerSerializer(fitxer).data, status=status.HTTP_201_CREATED)


class FttDocumentDetailView(APIView):
    """GET/PATCH ftt-documents/<fitxer_id>/ → carrega / desa (versió nova)."""

    permission_classes = [IsAuthenticated]

    def _get_techsheet(self, fitxer_id):
        return get_object_or_404(
            ModelFitxer, pk=fitxer_id, tipus=ModelFitxer.TIPUS_TECHSHEET
        )

    def get(self, request, fitxer_id):
        fitxer = self._get_techsheet(fitxer_id)
        data = svc.load_document(fitxer)
        return Response(
            {
                "fitxer": ModelFitxerSerializer(fitxer).data,
                "document_json": data["document_json"],
                "manifest": data["manifest"],
                "assets": _asset_urls(request, fitxer, data["assets"].keys()),
            }
        )

    def patch(self, request, fitxer_id):
        head = self._get_techsheet(fitxer_id)
        if not head.is_current:
            return Response(
                {"detail": "Només es pot desar des del cap de cadena vigent."},
                status=status.HTTP_409_CONFLICT,
            )
        document_json = request.data.get("document_json")
        if document_json is None:
            return Response(
                {"detail": "Falta document_json."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_head = svc.save_document(head, document_json)
        return Response(ModelFitxerSerializer(new_head).data, status=status.HTTP_200_OK)


class FttDocumentExportView(APIView):
    """POST ftt-documents/<fitxer_id>/export/ → desa un PDF d'export enllaçat al .ftt.

    Rep el PDF (multipart, camp `file`) generat al client des d'aquesta versió del .ftt i
    el desa al Finder com a ModelFitxer EXPORT (cadena pròpia). El .ftt no es toca.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, fitxer_id):
        source = get_object_or_404(
            ModelFitxer, pk=fitxer_id, tipus=ModelFitxer.TIPUS_TECHSHEET
        )
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "Falta el fitxer PDF (camp `file`)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        nom = request.data.get("nom") or upload.name
        export = svc.save_export(source, upload, nom=nom)
        return Response(
            ModelFitxerSerializer(export).data, status=status.HTTP_201_CREATED
        )


class FttDocumentAssetView(APIView):
    """GET ftt-documents/<fitxer_id>/asset/<name>/ → bytes d'un asset del .ftt."""

    permission_classes = [IsAuthenticated]

    def get(self, request, fitxer_id, asset_name):
        fitxer = get_object_or_404(
            ModelFitxer, pk=fitxer_id, tipus=ModelFitxer.TIPUS_TECHSHEET
        )
        data = svc.load_document(fitxer)
        blob = data["assets"].get(asset_name)
        if blob is None:
            return Response(
                {"detail": "Asset no trobat."}, status=status.HTTP_404_NOT_FOUND
            )
        ctype = mimetypes.guess_type(asset_name)[0] or "application/octet-stream"
        return HttpResponse(blob, content_type=ctype)
