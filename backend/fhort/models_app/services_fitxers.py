"""Servei de versionat de fitxers de Model.

FONT ÚNICA DE LA INVARIANT: cada fitxer lògic és una cadena `versio_anterior`. En tota
cadena hi ha EXACTAMENT UN registre amb `is_current=True` (el cap). `save_model_file` és
l'únic lloc que toca aquesta invariant — qualsevol escriptor (upload manual, import,
eines IA) hi delega.
"""

import hashlib
import mimetypes

from django.db import transaction

from .models import ModelFitxer

# D13 — descàrrega signada. Font única del salt i del TTL: hi beuen el serializer (qui
# signa) i el ViewSet (qui verifica). Canviar el salt invalida tots els enllaços vius.
DOWNLOAD_SALT = 'model_fitxer_download'
DOWNLOAD_TTL = 900   # segons (15 min): prou per obrir/descarregar, poc per compartir.


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


def serve_model_file(fitxer, *, as_attachment=True):
    """Serveix els bytes d'un ModelFitxer delegant-los a nginx (S03a · P2b).

    Font ÚNICA del servei de bytes: hi criden tant l'endpoint autenticat (`download`) com el
    signat (`download_signed`). Django no serveix mai els bytes en producció: envia la
    capçalera `X-Accel-Redirect` cap a `location /protected-media/` (internal) i nginx els
    escup. Vegeu docs/OPS_S03_NGINX.md.

    `as_attachment=False` → `Content-Disposition: inline`, necessari per als previsualitzadors
    (`<iframe>` de PDF): amb `attachment` el navegador descarregaria en lloc de renderitzar.

    - `url_extern` → 302 (el fitxer no viu aquí).
    - sense bytes → 404.
    - DEBUG → FileResponse (no hi ha nginx al davant).
    """
    import os
    from urllib.parse import quote

    from django.conf import settings
    from django.http import (FileResponse, HttpResponse, HttpResponseRedirect,
                             JsonResponse)

    if fitxer.url_extern:
        return HttpResponseRedirect(fitxer.url_extern)
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
