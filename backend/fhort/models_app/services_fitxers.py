"""Servei de versionat de fitxers de Model i de Catàleg (item).

FONT ÚNICA DE LA INVARIANT: cada fitxer lògic és una cadena `versio_anterior`. En tota
cadena hi ha EXACTAMENT UN registre amb `is_current=True` (el cap). `save_model_file` i
`save_item_file` són els únics llocs que toquen aquesta invariant — qualsevol escriptor
(upload manual, import, eines IA) hi delega.
"""

import hashlib
import mimetypes
import os

from django.db import transaction

from .models import ItemFitxer, ModelFitxer

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
})


class UploadRejected(ValueError):
    """L'upload no passa la validació (mida o extensió). El caller la tradueix a 400."""


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


def serve_fitxer(fitxer, *, as_attachment=True):
    """Serveix els bytes d'un ModelFitxer O d'un ItemFitxer delegant-los a nginx (S03a · P2b).

    Font ÚNICA del servei de bytes: hi criden els endpoints autenticats (`download`) i els
    signats (`download_signed`) dels dos models. Django no serveix mai els bytes en producció:
    envia la capçalera `X-Accel-Redirect` cap a `location /protected-media/` (internal) i nginx
    els escup. Vegeu docs/OPS_S03_NGINX.md.

    `as_attachment=False` → `Content-Disposition: inline`, necessari per als previsualitzadors
    (`<iframe>` de PDF): amb `attachment` el navegador descarregaria en lloc de renderitzar.

    - `url_extern` → 302 (el fitxer no viu aquí). ItemFitxer no té aquest camp: `getattr`.
    - sense bytes → 404.
    - DEBUG → FileResponse (no hi ha nginx al davant).
    """
    from urllib.parse import quote

    from django.conf import settings
    from django.http import (FileResponse, HttpResponse, HttpResponseRedirect,
                             JsonResponse)

    url_extern = getattr(fitxer, 'url_extern', None)
    if url_extern:
        return HttpResponseRedirect(url_extern)
    if not fitxer.fitxer:
        # JSON, no HTML: manté el contracte del 404 que servia DRF abans de l'extracció.
        return JsonResponse({'error': 'El fitxer no té bytes associats.'}, status=404)

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
