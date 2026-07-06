"""Endpoints del document .ftt (crear / carregar / desar / servir assets).

El client mai rep el zip: load retorna document.json + URLs d'assets (servits per
FttDocumentAssetView, que desempaqueta el .ftt al backend). Desar genera una versió
nova encadenada via save_model_file (invariant is_current intacta).

NOTA (B3): encara NO hi ha enforcement de lock; arriba a B7 (lock sobre el document
lògic + timer-gap). De moment només IsAuthenticated.
"""
import logging
import mimetypes

from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fhort.accounts.capabilities import CONFIGURE, get_capabilities

from . import services_ftt, services_ftt_document as svc
from .ftt_template_views import DocumentTemplateSerializer
from .models import DocumentTemplate, Model, ModelFitxer
from .serializers import ModelFitxerSerializer

logger = logging.getLogger(__name__)


def _lock_data(lock):
    return {
        'locked_by_id': lock.locked_by_id,
        'locked_by_username': getattr(lock.locked_by, 'username', None),
        'locked_at': lock.locked_at,
        'document_root_id': lock.document_root_id,
    }


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
        template_id = request.data.get('template_id')
        document_json = None
        assets = None
        if template_id:
            tpl = get_object_or_404(DocumentTemplate, pk=template_id)
            if tpl.fitxer_template:
                try:
                    tpl.fitxer_template.open('rb')
                    try:
                        blob = tpl.fitxer_template.read()
                    finally:
                        tpl.fitxer_template.close()
                    unpacked = services_ftt.unpack(blob)
                    document_json, extra_assets = svc.resolve_placeholders(
                        unpacked['document_json'], model
                    )
                    assets = {**(unpacked.get('assets') or {}), **extra_assets}
                except (ValueError, OSError):
                    # Plantilla corrupta o il·legible: degradem a document buit (mai 500).
                    logger.exception("Plantilla %s il·legible; es crea document buit", template_id)
                    document_json = None
                    assets = None
        fitxer = svc.create_document(model, document_json=document_json, assets=assets)
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
        if not svc.user_holds_lock(head, request.user):
            return Response(
                {"detail": "Cal tenir el lock del document per desar."},
                status=status.HTTP_403_FORBIDDEN,
            )
        document_json = request.data.get("document_json")
        if document_json is None:
            return Response(
                {"detail": "Falta document_json."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_head = svc.save_document(head, document_json)
        # Arreglo del timer-gap: desar renova locked_at → editar >TTL no perd el lock.
        svc.renew_lock(new_head, request.user)
        return Response(ModelFitxerSerializer(new_head).data, status=status.HTTP_200_OK)


class FttDocumentLockView(APIView):
    """POST ftt-documents/<fitxer_id>/lock/ → adquireix el lock del document lògic."""

    permission_classes = [IsAuthenticated]

    def post(self, request, fitxer_id):
        fitxer = get_object_or_404(
            ModelFitxer, pk=fitxer_id, tipus=ModelFitxer.TIPUS_TECHSHEET
        )
        lock, ok = svc.acquire_lock(fitxer, request.user)
        if ok:
            return Response(_lock_data(lock))
        return Response(_lock_data(lock), status=status.HTTP_409_CONFLICT)


class FttDocumentUnlockView(APIView):
    """POST ftt-documents/<fitxer_id>/unlock/ → allibera (propietari o CONFIGURE)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, fitxer_id):
        fitxer = get_object_or_404(
            ModelFitxer, pk=fitxer_id, tipus=ModelFitxer.TIPUS_TECHSHEET
        )
        can_override = CONFIGURE in get_capabilities(request.user)
        ok = svc.release_lock(fitxer, request.user, can_override=can_override)
        if not ok:
            return Response(
                {"detail": "El document està bloquejat per un altre usuari."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({"status": "unlocked"})


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


class FttSaveAsTemplateView(APIView):
    """POST ftt-documents/<fitxer_id>/save-as-template/ → desa el cap com a DocumentTemplate."""

    permission_classes = [IsAuthenticated]

    def post(self, request, fitxer_id):
        nom = (request.data.get('nom') or '').strip()
        if not nom:
            return Response({'detail': 'nom requerit'}, status=status.HTTP_400_BAD_REQUEST)
        descripcio = request.data.get('descripcio') or ''
        # Cap de cadena actual (l'autosave del client el manté al dia).
        fitxer = get_object_or_404(ModelFitxer, pk=fitxer_id)
        data = svc.load_document(fitxer)
        blob = services_ftt.pack(
            data['document_json'], assets=data.get('assets'), kind=services_ftt.FTT_KIND_TEMPLATE
        )
        tpl = DocumentTemplate(nom=nom, descripcio=descripcio, created_by=request.user, origen='tenant')
        safe_nom = nom[:60].replace('/', '_').replace('\\', '_').replace(' ', '_')
        tpl.fitxer_template.save(f"{safe_nom}.fttpt", ContentFile(blob), save=False)
        tpl.save()
        return Response(DocumentTemplateSerializer(tpl).data, status=status.HTTP_201_CREATED)


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
