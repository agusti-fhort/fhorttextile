"""Servei de versionat de fitxers de Model i de Catàleg (item).

FONT ÚNICA DE LA INVARIANT: cada fitxer lògic és una cadena `versio_anterior`. En tota
cadena hi ha EXACTAMENT UN registre amb `is_current=True` (el cap). `save_model_file` i
`save_item_file` són els únics llocs que toquen aquesta invariant — qualsevol escriptor
(upload manual, import, eines IA) hi delega.
"""

import hashlib
import logging
import mimetypes
import os

from django.db import transaction

from .models import ItemFitxer, ModelFitxer

logger = logging.getLogger(__name__)

# D13 — descàrrega signada. Font única dels salts i del TTL: hi beuen els serializers (qui
# signen) i els ViewSets (qui verifiquen). Canviar un salt invalida tots els enllaços vius.
# Els dos salts han de ser DIFERENTS: amb un de sol, un token emès per a ModelFitxer id=5
# validaria a ItemFitxer id=5 (el payload és només l'id).
DOWNLOAD_SALT = 'model_fitxer_download'
ITEM_DOWNLOAD_SALT = 'item_fitxer_download'
DOWNLOAD_TTL = 900   # segons (15 min): prou per obrir/descarregar, poc per compartir.

# D12 — validació d'upload. NO es copia el forat de Customer.upload_logo (que no valida res).
# 20 MB, no 25: és el sostre que ja regia a tech_sheet_views.py:45, i és més estricte que el
# `client_max_body_size 25M` d'nginx. S'adopta el més estricte dels dos ja existents.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# Whitelist per EXTENSIÓ, no per mimetype: els formats de domini (.dxf, .rul, .ftt) arriben
# del navegador com a application/octet-stream o amb mimetypes inconsistents entre sistemes,
# de manera que filtrar per content_type els rebutjaria falsament. Coherent amb TIPUS_CHOICES.
ALLOWED_UPLOAD_EXTENSIONS = frozenset({
    '.ftt',                                  # TECHSHEET
    '.pdf',                                  # DOCUMENT / EXPORT
    '.dxf',                                  # PATRO / ESCALAT / MARCADA (CAD)
    '.svg',                                  # SKETCH_SVG
    '.rul', '.txt',                          # RUL
    '.png', '.jpg', '.jpeg', '.webp', '.gif',   # sketches i imatges
    # D18 — `upload_file_view` no validava res i hi ha 1 `.xlsx` real a la BD (218 files).
    # Endollar-hi `validate_upload` sense afegir-los rebutjaria dades que el sistema ja accepta.
    # `.xls` acompanya `.xlsx` pel mateix motiu que `.jpg` acompanya `.jpeg`.
    '.xlsx', '.xls',                         # fulls de càlcul (mesures, BOM)
    # Les fotos de fitting es fan amb el mòbil, i un iPhone les desa en HEIC. S'accepten a la
    # PUJADA, però no es desen mai en HEIC: es converteixen a JPEG aquí al servidor
    # (`converteix_heic_a_jpeg`) i el que arriba a la BD és sempre un .jpg. Cap navegador
    # d'escriptori no pinta HEIC, i el visor de fitxers del model ha de poder ensenyar la foto.
    '.heic', '.heif',                        # fotos de mòbil → es desen convertides a .jpg
})

# Extensions que NO es desen tal com arriben: entren, es converteixen i desen com una altra cosa.
HEIC_EXTENSIONS = frozenset({'.heic', '.heif'})
HEIC_MIMETYPES = frozenset({
    'image/heic', 'image/heif', 'image/heic-sequence', 'image/heif-sequence',
})
JPEG_QUALITY = 90


class UploadRejected(ValueError):
    """L'upload no passa la validació (mida o extensió). El caller la tradueix a 400."""


class ConversioFallida(ValueError):
    """El fitxer diu que és HEIC però no s'ha pogut convertir. El caller la tradueix a 422.

    422 i no 500: el fitxer ha arribat bé i la petició és correcta; el que no serveix és el
    CONTINGUT. Un 500 diria que el servidor s'ha trencat, i el que ha passat és que la foto
    no es pot llegir — que és una cosa que l'usuari pot entendre i resoldre.
    """


def es_heic(nom, content_type=''):
    """L'upload és HEIC/HEIF? Per EXTENSIÓ (la llei de la casa, vegeu ALLOWED_UPLOAD_EXTENSIONS)
    i, si l'extensió no ho diu, pel MIME: Safari de vegades puja la foto amb nom `.jpg` i el
    content_type correcte, i aleshores el que mana és el contingut."""
    ext = os.path.splitext(nom or '')[1].lower()
    if ext in HEIC_EXTENSIONS:
        return True
    return (content_type or '').split(';')[0].strip().lower() in HEIC_MIMETYPES


def converteix_heic_a_jpeg(file, nom):
    """HEIC/HEIF → JPEG q=90. Retorna `(fitxer_nou, nom_nou)` amb el nom original i `.jpg`.

    ORIENTACIÓ: les fotos de mòbil vénen girades i amb un tag EXIF que diu com desgirar-les.
    `pillow_heif` JA aplica l'orientació en descodificar (torna la imatge dreta i el tag
    normalitzat a 1), o sigui que `exif_transpose` és aquí un no-op en el camí d'avui. S'hi
    deixa a posta: és la crida que ho garanteix si un dia el descodificador canvia de criteri,
    i no costa res quan el tag ja val 1.

    NO es conserva la resta d'EXIF (data, càmera, GPS). Reinjectar-lo obligaria a netejar-ne
    l'orientació —si no, un visor que l'honrés giraria una imatge que ja ve dreta— i el que la
    decisió demanava és la foto, no les seves metadades.
    """
    import io

    from django.core.files.base import ContentFile

    try:
        import pillow_heif
        from PIL import Image, ImageOps
    except ImportError as exc:   # dep nova al lock: si el desplegament no ha fet pip install
        raise ConversioFallida(
            "El servidor no pot convertir fotos HEIC (falta pillow-heif). "
            "Puja la foto en JPEG o avisa l'administrador."
        ) from exc

    pillow_heif.register_heif_opener()
    try:
        try:
            file.seek(0)
        except (AttributeError, ValueError):
            pass
        imatge = Image.open(file)
        imatge = ImageOps.exif_transpose(imatge) or imatge
        if imatge.mode != 'RGB':
            # JPEG no té canal alfa ni paleta; una HEIC amb transparència peta en desar-se.
            imatge = imatge.convert('RGB')
        sortida = io.BytesIO()
        imatge.save(sortida, format='JPEG', quality=JPEG_QUALITY)
    except ConversioFallida:
        raise
    except Exception as exc:
        logger.warning('HEIC il·legible (%s): %s', nom, exc)
        raise ConversioFallida(
            "No s'ha pogut llegir la foto HEIC: pot estar corrupta o incompleta."
        ) from exc

    bytes_jpeg = sortida.getvalue()
    # El sostre de mida es torna a mirar SOBRE EL RESULTAT: un JPEG pesa més que la HEIC
    # d'origen, i acceptar per la porta de la conversió un fitxer que la llei del sistema
    # rebutja per la porta del davant seria obrir-hi un forat.
    if len(bytes_jpeg) > MAX_UPLOAD_BYTES:
        raise ConversioFallida(
            f'La foto convertida a JPEG ocupa {len(bytes_jpeg) / (1024 * 1024):.1f} MB, '
            f'per sobre del màxim de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.')

    nom_jpg = os.path.splitext(nom or 'foto')[0] + '.jpg'
    return ContentFile(bytes_jpeg, name=nom_jpg), nom_jpg


def validate_upload(file, nom=None):
    """Guard únic d'upload (D12). Llança UploadRejected amb un missatge per a l'usuari."""
    nom_fitxer = nom or getattr(file, 'name', '') or ''
    ext = os.path.splitext(nom_fitxer)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        permeses = ', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        raise UploadRejected(
            f"Extensió no permesa: '{ext or '(cap)'}'. Permeses: {permeses}.")
    mida = getattr(file, 'size', None) or 0
    if mida > MAX_UPLOAD_BYTES:
        # Un decimal: amb divisió entera, 20 MB + 1 byte es llegia "20 MB. Màxim 20 MB."
        raise UploadRejected(
            f'Fitxer massa gran ({mida / (1024 * 1024):.1f} MB). '
            f'Màxim {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.')


def _compute_checksum(file):
    """sha256 del contingut, deixant el punter a l'inici per a la desada posterior."""
    h = hashlib.sha256()
    for chunk in file.chunks():
        h.update(chunk)
    try:
        file.seek(0)
    except (AttributeError, ValueError):
        pass
    return h.hexdigest()


def _guess_mimetype(file, nom):
    ct = getattr(file, 'content_type', None)
    if ct:
        return ct
    return mimetypes.guess_type(nom)[0] or ''


@transaction.atomic
def save_model_file(model, file, *, versio_anterior=None,
                    tipus=None, origen='upload', nom=None):
    """Desa un fitxer de model respectant la invariant de cadena.

    - Sense `versio_anterior`: cadena nova → versio=1, is_current=True, versio_anterior=NULL.
    - Amb `versio_anterior`: encadena → versio=pred.versio+1, is_current=True al nou i
      is_current=False al predecessor. `tipus` s'hereta del predecessor si no s'especifica.

    Retorna el `ModelFitxer` creat. És l'ÚNIC punt que escriu `is_current`/`versio` en una
    pujada; cap autoincrement per `tipus`. `categoria` (eix deprecat, S03a · P1.2) es deixa
    buida: ningú l'escriu amb valor semàntic ni la llegeix.
    """
    nom_fitxer = nom or getattr(file, 'name', None) or 'fitxer'
    checksum = _compute_checksum(file)
    mida = getattr(file, 'size', None) or 0
    mimetype = _guess_mimetype(file, nom_fitxer)

    if versio_anterior is not None:
        versio = (versio_anterior.versio or 0) + 1
        if tipus is None:
            tipus = versio_anterior.tipus
    else:
        versio = 1

    fitxer = ModelFitxer(
        model=model,
        nom_fitxer=nom_fitxer,
        categoria='',
        tipus=tipus or 'ALTRES',
        versio=versio,
        is_current=True,
        versio_anterior=versio_anterior,
        mida_bytes=mida,
        checksum=checksum,
        mimetype=mimetype,
        origen=origen,
    )
    # save=False: el FileField escriu els bytes i fixa .name; el INSERT ve després.
    fitxer.fitxer.save(nom_fitxer, file, save=False)
    fitxer.save()

    if versio_anterior is not None and versio_anterior.is_current:
        versio_anterior.is_current = False
        versio_anterior.save(update_fields=['is_current'])

    return fitxer


@transaction.atomic
def save_item_file(item, file, *, versio_anterior=None, tipus=None, nom=None):
    """Mirall de `save_model_file` per al catàleg (S03b · P4). Mateixa invariant de cadena.

    NO s'ha extret un helper genèric compartit amb `save_model_file`: els dos models tenen
    conjunts de camps diferents (ModelFitxer porta categoria/origen/url_extern/generat_des_de;
    ItemFitxer no en porta cap). Un helper parametritzat per model + mapa de camps sortiria
    més llarg i més opac que aquestes 20 línies. El que SÍ es comparteix és el que és
    realment comú: `_compute_checksum`, `_guess_mimetype` i `validate_upload`.
    """
    nom_fitxer = nom or getattr(file, 'name', None) or 'fitxer'
    checksum = _compute_checksum(file)
    mida = getattr(file, 'size', None) or 0
    mimetype = _guess_mimetype(file, nom_fitxer)

    if versio_anterior is not None:
        versio = (versio_anterior.versio or 0) + 1
        if tipus is None:
            tipus = versio_anterior.tipus
    else:
        versio = 1

    fitxer = ItemFitxer(
        garment_type_item=item,
        nom_fitxer=nom_fitxer,
        tipus=tipus or 'ALTRES',
        versio=versio,
        is_current=True,
        versio_anterior=versio_anterior,
        mida_bytes=mida,
        checksum=checksum,
        mimetype=mimetype,
    )
    fitxer.fitxer.save(nom_fitxer, file, save=False)
    fitxer.save()

    if versio_anterior is not None and versio_anterior.is_current:
        versio_anterior.is_current = False
        versio_anterior.save(update_fields=['is_current'])

    return fitxer


def marcar_procedencia(nou, user, **camps):
    """Escriu la procedència i l'autor d'una còpia importada, en un sol UPDATE.

    Comú als dos cicles d'importació: catàleg→model (`derivat_de_item`) i model→model
    (`derivat_de_model`). És l'únic tros que comparteixen de veritat — la còpia de bytes
    difereix (el `.ftt` model→model es reescriu, vegeu D16) i la font també. Mateix criteri
    que `save_model_file` vs `save_item_file`: es comparteix el que és realment comú, no
    s'inventa un helper parametritzat que surti més llarg i més opac.

    NO toca `is_current`/`versio`: d'aquells n'és únic escriptor `save_model_file`.
    """
    for camp, valor in camps.items():
        setattr(nou, camp, valor)
    noms = list(camps)
    perfil = getattr(user, 'profile', None)
    if perfil is not None:
        nou.pujat_per = perfil
        noms.append('pujat_per')
    nou.save(update_fields=noms)
    return nou


def delete_fitxer_bytes(fitxer):
    """Esborra els bytes d'un ModelFitxer O d'un ItemFitxer. Font única, com `serve_fitxer`.

    `mixins.DestroyModelMixin` fa `instance.delete()`, i des de Django 1.3 el `FileField` no
    s'engancha a `post_delete` → esborrar la fila deixa els bytes orfes al disc. Els dos
    ViewSets de fitxers hi criden des de `perform_destroy`.

    Segueix el precedent d'`extraction_views.py:66-75`: guard `exists()` i `try/except` que
    **mai bloqueja l'esborrat de la fila**. Un fitxer ja absent del disc (fila fantasma) no
    ha d'impedir netejar la BD — és exactament el cas que volem poder resoldre.
    """
    from django.core.files.storage import default_storage

    name = fitxer.fitxer.name if fitxer.fitxer else ''
    if not name:
        return
    try:
        if default_storage.exists(name):
            default_storage.delete(name)
    except Exception:
        # No es propaga: la fila s'ha de poder esborrar encara que el disc falli.
        logger.warning("Bytes no esborrats per a '%s'", name, exc_info=True)


def serve_fitxer(fitxer, *, as_attachment=True):
    """Serveix els bytes d'un ModelFitxer O d'un ItemFitxer delegant-los a nginx (S03a · P2b).

    Font ÚNICA del servei de bytes: hi criden els endpoints autenticats (`download`) i els
    signats (`download_signed`) dels dos models. Django no serveix mai els bytes en producció:
    envia la capçalera `X-Accel-Redirect` cap a `location /protected-media/` (internal) i nginx
    els escup. Vegeu docs/OPS_S03_NGINX.md.

    `as_attachment=False` → `Content-Disposition: inline`, necessari per als previsualitzadors
    (`<iframe>` de PDF): amb `attachment` el navegador descarregaria en lloc de renderitzar.

    - `url_extern` → 302 (el fitxer no viu aquí). ItemFitxer no té aquest camp: `getattr`.
    - sense nom, o amb nom però sense bytes al disc (fila fantasma) → 404 JSON.
    - DEBUG → FileResponse (no hi ha nginx al davant).
    """
    from urllib.parse import quote

    from django.conf import settings
    from django.core.files.storage import default_storage
    from django.http import (FileResponse, HttpResponse, HttpResponseRedirect,
                             JsonResponse)

    def _sense_bytes():
        # JSON, no HTML: manté el contracte del 404 que servia DRF abans de l'extracció.
        return JsonResponse({'error': 'El fitxer no té bytes associats.'}, status=404)

    url_extern = getattr(fitxer, 'url_extern', None)
    if url_extern:
        return HttpResponseRedirect(url_extern)
    if not fitxer.fitxer:
        return _sense_bytes()
    # Un FieldFile és falsy només si no té `name`: el guard de sobre comprova existència de
    # NOM, no de BYTES. Una fila fantasma (nom desat, bytes absents del disc) el passava i
    # petava més avall — 500 en DEBUG (`FileResponse.open`), i en producció un 404 d'nginx
    # sense el JSON del contracte, perquè la branca X-Accel no toca mai el disc. Amb aquest
    # guard el contracte és el MATEIX en tots dos entorns.
    if not default_storage.exists(fitxer.fitxer.name):
        return _sense_bytes()

    nom = fitxer.nom_fitxer or os.path.basename(fitxer.fitxer.name)

    if settings.DEBUG:
        return FileResponse(fitxer.fitxer.open('rb'), as_attachment=as_attachment, filename=nom)

    # El path relatiu JA porta el prefix del schema: TenantFileSystemStorage el resol a
    # `location`, no al `name` (P2a).
    rel = os.path.relpath(fitxer.fitxer.path, str(settings.MEDIA_ROOT))
    response = HttpResponse(status=200)
    response['X-Accel-Redirect'] = '/protected-media/' + quote(rel)
    # RFC 5987: els noms pujats per l'usuari no tenen per què ser ASCII.
    tipus_disp = 'attachment' if as_attachment else 'inline'
    response['Content-Disposition'] = f"{tipus_disp}; filename*=UTF-8''{quote(nom)}"
    response['Content-Type'] = fitxer.mimetype or 'application/octet-stream'
    return response


def get_version_chain(fitxer):
    """Retorna la cadena completa (read-only) ordenada per versio ascendent.

    Recorre amunt per `versio_anterior` i avall per `versions_posteriors` a partir de
    qualsevol node de la cadena. No escriu res.
    """
    seen = {}
    # Amunt: predecessors.
    node = fitxer
    while node is not None and node.id not in seen:
        seen[node.id] = node
        node = node.versio_anterior
    # Avall: successors a partir del node donat.
    node = fitxer
    while node is not None:
        nxt = node.versions_posteriors.first()
        if nxt is None or nxt.id in seen:
            break
        seen[nxt.id] = nxt
        node = nxt
    return sorted(seen.values(), key=lambda f: (f.versio, f.id))
