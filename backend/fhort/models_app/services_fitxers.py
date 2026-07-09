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
