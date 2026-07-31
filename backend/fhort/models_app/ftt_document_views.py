"""Endpoints del document .ftt (crear / carregar / desar / servir assets).

El client mai rep el zip: load retorna document.json + URLs d'assets (servits per
FttDocumentAssetView, que desempaqueta el .ftt al backend). Desar genera una versió
nova encadenada via save_model_file (invariant is_current intacta).

NOTA (B3): encara NO hi ha enforcement de lock; arriba a B7 (lock sobre el document
lògic + timer-gap). De moment només IsAuthenticated.
"""
import base64
import binascii
import io
import logging
import mimetypes
import os
import re

from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fhort.accounts.capabilities import CONFIGURE, get_capabilities

from . import services_ftt, services_ftt_document as svc
from .ftt_template_views import DocumentTemplateSerializer
from .models import DocumentTemplate, Model, ModelFitxer
from .serializers import ModelFitxerSerializer
from .services_fitxers import (MAX_UPLOAD_BYTES, ConversioFallida, UploadRejected,
                               redueix_imatge, validate_upload)

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


_NOM_ASSET_RE = re.compile(r"^[0-9a-f]{16}\.[a-z0-9]{1,5}$")


def _assets_del_payload(assets, document_json):
    """`{nom: base64}` del client → `{nom: bytes}` per a `save_document`. {} si no en ve cap.

    L'editor puja la imatge en COL·LOCAR-LA (FttAssetPrepareView) i n'obté el nom; els bytes
    viatgen amb el PRIMER desat que la referencia, i cap més: a partir d'aquí el document
    només en porta `assets/<nom>`. Abans, la imatge anava inline dins document.json a CADA
    autosave, i cada autosave n'escriu una versió nova del `.ftt`.

    Dos guards, tots dos durs:
    - **el nom l'ha fet el servidor** (sha16 + extensió). Els noms viatgen a rutes dins del zip
      i un nom lliure hi escriuria on volgués.
    - **només s'accepta el que el document REFERENCIA.** Un asset sense referència seria un
      orfe per sempre (`save_document` fusiona i no poda mai). Col·locar una foto i desfer-ho
      abans de desar no ha de deixar-ne rastre: s'ignora en silenci, no és cap error.
    """
    if not assets:
        return {}
    if not isinstance(assets, dict):
        raise ValueError("assets ha de ser un objecte {nom: base64}.")
    referenciats = services_ftt.noms_assets_referenciats(document_json)
    sortida = {}
    for nom, b64 in assets.items():
        if not isinstance(nom, str) or not _NOM_ASSET_RE.match(nom):
            raise ValueError("Nom d'asset no vàlid: '%s'." % nom)
        if nom not in referenciats:
            logger.info("Asset '%s' rebut sense referència al document: ignorat.", nom)
            continue
        try:
            data = base64.b64decode(b64 or "", validate=True)
        except (binascii.Error, TypeError, ValueError) as e:
            raise ValueError("Asset '%s' amb base64 no vàlid." % nom) from e
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("Asset '%s' massa gran." % nom)
        sortida[nom] = data
    return sortida


class FttAssetPrepareView(APIView):
    """POST ftt-documents/<fitxer_id>/prepare-asset/ → passa una imatge per l'EMBUT.

    És la porta de l'editor, i no desa RES: rep el fitxer tal com surt del mòbil, li aplica
    el mateix embut que Arxius i fitting (`redueix_imatge`: HEIC→JPEG, costat llarg a
    2000 px) i torna els bytes ja reduïts amb el NOM canònic que tindran dins del `.ftt`.

    Per què no desa: els assets viuen dins del zip de la versió vigent. Escriure-hi ara
    voldria dir encadenar una versió nova per cada foto col·locada —justament el churn que
    patim— o inventar un magatzem paral·lel. Amb aquesta forma, els bytes creuen la xarxa
    EXACTAMENT UN COP (amb el primer desat que els referencia) i el document mai no torna a
    portar-los. El que aquí es guanya és que el navegador deixa de carregar 4000 px a la RAM
    i que l'usuari veu l'error de pujada quan puja, no en silenci a l'autosave.

    El `fitxer_id` no s'hi fa servir per a res més que per acotar la porta al document que
    s'està editant: la conversió és pura.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, fitxer_id):
        get_object_or_404(ModelFitxer, pk=fitxer_id, tipus=ModelFitxer.TIPUS_TECHSHEET)
        pujat = request.FILES.get("fitxer")
        if pujat is None:
            return Response({"detail": "Falta fitxer."}, status=status.HTTP_400_BAD_REQUEST)

        nom = getattr(pujat, "name", "") or "imatge"
        try:
            validate_upload(pujat, nom)
        except UploadRejected as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pujat, nom = redueix_imatge(pujat, nom, getattr(pujat, "content_type", ""))
        except ConversioFallida as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        data = pujat.read()
        ext = os.path.splitext(nom)[1]
        mime = mimetypes.guess_type(nom)[0] or "application/octet-stream"
        amplada = alcada = None
        try:
            from PIL import Image
            amplada, alcada = Image.open(io.BytesIO(data)).size
        except Exception:   # noqa: BLE001 — un SVG no té mida en píxels i no és cap error
            pass
        return Response({
            "nom": services_ftt.nom_asset(data, ext),
            "dataurl": "data:%s;base64,%s" % (mime, base64.b64encode(data).decode()),
            "mida_bytes": len(data),
            "amplada": amplada,
            "alcada": alcada,
        })


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
        # F2 — nom i descripció opcionals: el que distingeix N fitxes del MATEIX model a la
        # llista d'Arxius. Absents → nom derivat del model, exactament com fins ara.
        fitxer = svc.create_document(
            model, document_json=document_json, assets=assets,
            nom=request.data.get('nom'), descripcio=request.data.get('descripcio'),
        )
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
        # `kind` opcional: l'interruptor de mode plantilla de l'editor l'envia per marcar el
        # document com a plantilla en construcció. Si no ve, save_document l'hereta.
        kind = request.data.get("kind")
        if kind is not None and kind not in (services_ftt.FTT_KIND_DOCUMENT, services_ftt.FTT_KIND_TEMPLATE):
            return Response(
                {"detail": "kind ha de ser 'document' o 'template'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            assets = _assets_del_payload(request.data.get("assets"), document_json)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        new_head = svc.save_document(head, document_json, assets=assets or None, kind=kind)
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
        # DESCONGELAR ABANS D'EMPAQUETAR. El document del qual sortim és una INSTÀNCIA: els seus
        # `field` ja estan congelats a text amb els valors del model host (codi, client, logo,
        # taules de mesures). Empaquetar-lo tal qual —el que es feia fins ara— fabricava
        # plantilles que arrossegaven les dades d'aquell model com a text literal a tots els
        # documents que en naixessin. `unfreeze_document` és l'invers exacte i ja existia.
        document_json, assets, report = svc.unfreeze_document(
            data['document_json'], data.get('assets') or {}
        )
        blob = services_ftt.pack(
            document_json, assets=assets, kind=services_ftt.FTT_KIND_TEMPLATE
        )
        tpl = DocumentTemplate(nom=nom, descripcio=descripcio, created_by=request.user, origen='tenant')
        safe_nom = nom[:60].replace('/', '_').replace('\\', '_').replace(' ', '_')
        tpl.fitxer_template.save(f"{safe_nom}.fttpt", ContentFile(blob), save=False)
        tpl.save()
        # El report viatja perquè l'editor pugui dir QUÈ s'ha desmaterialitzat: sense això
        # l'usuari no sap que les taules li han quedat buides i a punt de re-vincular.
        return Response(
            {**DocumentTemplateSerializer(tpl).data, 'unfreeze_report': report},
            status=status.HTTP_201_CREATED,
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
