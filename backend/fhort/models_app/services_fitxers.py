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
    # PUJADA, però no es desen mai en HEIC: passen per l'embut (`redueix_imatge`) i el que
    # arriba a la BD és sempre un .jpg. Cap navegador d'escriptori no pinta HEIC, i el visor
    # de fitxers del model ha de poder ensenyar la foto.
    '.heic', '.heif',                        # fotos de mòbil → es desen convertides a .jpg
})

# Extensions que NO es desen tal com arriben: entren, es converteixen i desen com una altra cosa.
HEIC_EXTENSIONS = frozenset({'.heic', '.heif'})
HEIC_MIMETYPES = frozenset({
    'image/heic', 'image/heif', 'image/heic-sequence', 'image/heif-sequence',
})
JPEG_QUALITY = 90            # transcodificació pura (HEIC petita: només canvia de contenidor)
JPEG_QUALITY_REDUIDA = 80    # q0.8 — la imatge ja ha perdut píxels, no cal guardar-ne el gra

# Sostre del costat llarg. Una foto de mòbil fa 4000+ px i a la fitxa s'hi veu a 15 cm: els
# píxels de més no els mira ningú, però viatgen a cada desat i ocupen RAM al navegador.
MAX_COSTAT_LLARG_PX = 2000

# Ràsters que passen per l'embut. `.gif` en queda FORA a posta: Pillow en llegiria només el
# primer fotograma i desar-lo mataria l'animació en silenci — reduir no pot destruir dades.
# `.svg` tampoc hi és: és vectorial, no té píxels que reduir.
RASTER_EXTENSIONS = frozenset({'.png', '.jpg', '.jpeg', '.webp'}) | HEIC_EXTENSIONS

_EXT_PER_FORMAT = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}


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


def _registra_heif():
    """Ensenya a Pillow a obrir HEIC/HEIF. False si la dep no hi és (lock desalineat)."""
    try:
        import pillow_heif
    except ImportError:
        return False
    pillow_heif.register_heif_opener()
    return True


def redueix_imatge(file, nom, content_type=''):
    """EMBUT ÚNIC d'imatge del servidor. Retorna `(fitxer, nom)` — el mateix o un de nou.

    Fa dues coses en UNA descodificació, perquè són la mateixa decisió sobre els mateixos
    píxels i separar-les significaria obrir la imatge dues vegades a la mateixa porta:

    1. **HEIC/HEIF → JPEG.** Cap navegador d'escriptori pinta HEIC. No es desa mai l'original:
       guardar les dues coses duplicaria l'emmagatzematge sense que ningú obrís la HEIC.
    2. **Costat llarg > MAX_COSTAT_LLARG_PX → es redimensiona.** Una foto de mòbil entra amb
       4000+ px i a la fitxa es veu a 15 cm. Els píxels de més viatgen a cada desat del `.ftt`
       i s'acumulen en RAM al navegador; aquí és on es paren.

    FORMAT DE SORTIDA: JPEG, tret que la imatge porti transparència (llavors PNG, o WEBP si ja
    ho era) — aplanar l'alfa contra negre destruiria el retall d'un sketch. Les HEIC sempre
    surten JPEG: són fotos, i el canal alfa no hi juga.

    NO ES TOCA RES que no calgui: una imatge que ja compleix (≤2000 px i no-HEIC) torna
    BYTE A BYTE com ha entrat. Re-encodar-la només hi afegiria pèrdua. `.gif` i `.svg` queden
    fora de l'embut (vegeu RASTER_EXTENSIONS), i els no-ràsters (.pdf, .dxf, …) hi passen de llarg.

    ORIENTACIÓ: les fotos de mòbil vénen girades amb un tag EXIF que diu com desgirar-les.
    S'aplica sempre (`exif_transpose`) perquè la sortida NO conserva EXIF: si es desés el gir
    sense el tag, la foto quedaria tombada per sempre. La resta d'EXIF (data, càmera, GPS) es
    perd a posta — el que la decisió demanava és la foto, no les seves metadades.

    ERRORS, dues lleis distintes segons qui promet què:
    - HEIC il·legible → `ConversioFallida` (el caller: 422). Hem promès convertir-la i no podem;
      desar els bytes crus seria desar un fitxer que ningú podrà obrir.
    - Qualsevol altra imatge que Pillow no sàpiga llegir → es desa l'ORIGINAL i es reporta al
      log. És la llei de `pom_vision_service`: un downscale mai no bloqueja una pujada vàlida.
    """
    import io

    from django.core.files.base import ContentFile
    from PIL import Image, ImageOps

    def _intacte():
        # El punter torna SEMPRE a l'inici: qui rep el fitxer (un serializer d'imatge, el
        # checksum, el storage) el llegeix des de zero, i llegir-lo aquí per decidir si calia
        # tocar-lo el deixava a EOF. Un `ImageField` de DRF hi veia zero bytes i responia
        # "imatge no vàlida" per una foto perfectament sana.
        try:
            file.seek(0)
        except (AttributeError, ValueError):
            pass
        return file, nom

    heic = es_heic(nom, content_type)
    ext = os.path.splitext(nom or '')[1].lower()
    if not heic and ext not in RASTER_EXTENSIONS:
        return _intacte()
    if not _registra_heif() and heic:
        # dep nova al lock: si el desplegament no ha fet pip install
        raise ConversioFallida(
            "El servidor no pot convertir fotos HEIC (falta pillow-heif). "
            "Puja la foto en JPEG o avisa l'administrador.")

    try:
        try:
            file.seek(0)
        except (AttributeError, ValueError):
            pass
        imatge = Image.open(file)
        format_origen = (imatge.format or '').upper()
        imatge = ImageOps.exif_transpose(imatge) or imatge
        imatge.load()
    except Exception as exc:
        if heic:
            logger.warning('HEIC il·legible (%s): %s', nom, exc)
            raise ConversioFallida(
                "No s'ha pogut llegir la foto HEIC: pot estar corrupta o incompleta."
            ) from exc
        logger.warning("Imatge no reduïda, es desa l'original (%s): %s", nom, exc)
        return _intacte()

    amplada, alcada = imatge.size
    cal_reduir = max(amplada, alcada) > MAX_COSTAT_LLARG_PX
    if not cal_reduir and not heic:
        return _intacte()         # ja compleix: torna byte a byte, sense re-encodar

    try:
        if cal_reduir:
            factor = MAX_COSTAT_LLARG_PX / max(amplada, alcada)
            imatge = imatge.resize(
                (max(1, round(amplada * factor)), max(1, round(alcada * factor))),
                Image.LANCZOS)
        te_alfa = imatge.mode in ('RGBA', 'LA', 'PA') or 'transparency' in imatge.info
        if heic or not te_alfa:
            format_sortida = 'JPEG'
        else:
            format_sortida = 'WEBP' if format_origen == 'WEBP' else 'PNG'
        if format_sortida == 'JPEG' and imatge.mode != 'RGB':
            # JPEG no té canal alfa ni paleta; desar-hi una RGBA peta.
            imatge = imatge.convert('RGB')
        sortida = io.BytesIO()
        if format_sortida == 'JPEG':
            imatge.save(sortida, format='JPEG',
                        quality=JPEG_QUALITY_REDUIDA if cal_reduir else JPEG_QUALITY,
                        optimize=True)
        else:
            imatge.save(sortida, format=format_sortida, optimize=True)
    except Exception as exc:
        if heic:
            logger.warning('HEIC no convertible (%s): %s', nom, exc)
            raise ConversioFallida(
                "No s'ha pogut convertir la foto HEIC a JPEG.") from exc
        logger.warning("Imatge no reduïda, es desa l'original (%s): %s", nom, exc)
        return _intacte()

    bytes_nous = sortida.getvalue()
    # El sostre de mida es torna a mirar SOBRE EL RESULTAT: un JPEG pesa més que la HEIC
    # d'origen, i acceptar per la porta de la conversió un fitxer que la llei del sistema
    # rebutja per la porta del davant seria obrir-hi un forat.
    if len(bytes_nous) > MAX_UPLOAD_BYTES:
        if heic:
            raise ConversioFallida(
                f'La foto convertida a JPEG ocupa {len(bytes_nous) / (1024 * 1024):.1f} MB, '
                f'per sobre del màxim de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.')
        logger.warning("Imatge reduïda més gran que el màxim, es desa l'original (%s)", nom)
        return _intacte()
    # NO hi ha guard de "si el resultat pesa més, torna l'original": el que aquí es persegueix
    # són els PÍXELS, no només els bytes. Una imatge de 4000 px que comprimeix bé segueix
    # ocupant 4000×3000×4 bytes de RAM quan el navegador la descodifica, que és exactament el
    # que fa anar espès l'editor. La mida en disc és la conseqüència, no el criteri.

    nom_nou = os.path.splitext(nom or 'imatge')[0] + _EXT_PER_FORMAT[format_sortida]
    return ContentFile(bytes_nous, name=nom_nou), nom_nou


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
