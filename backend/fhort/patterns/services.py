"""Servei d'escriptura de fitxers de patró.

Calca `models_app.services_fitxers.save_model_file` (S0-B1): mateixa invariant de cadena,
mateix ordre d'operacions, mateix `@transaction.atomic`.

I la calca **a mà, sense extreure'n un helper genèric**, per la mateixa raó que allà es
va decidir no fer-ho (`services_fitxers.py:142-146`): els dos serveis s'assemblen avui,
però tenen amos diferents i divergiran. Un helper compartit els encadenaria, i el dia que
un dels dos hagi de canviar la invariant, l'altre se n'assabentaria per un test vermell.

Aquí, a més, ja divergeixen: un `PatternFile` porta DOS artefactes (el DXF i el RUL
germà) i una empremta que ve del motor.
"""
import hashlib
import mimetypes

from django.db import transaction

from .models import PatternFile

#: Mides i extensions les valida `models_app.services_fitxers.validate_upload`, que ja
#: admet .dxf i .rul (S0-B1.2). No se'n fa una còpia: la whitelist ha de ser una sola.


def _compute_checksum(file) -> str:
    """sha256 per chunks, i el punter torna a l'inici (com fa el pipeline existent)."""
    h = hashlib.sha256()
    for chunk in file.chunks():
        h.update(chunk)
    file.seek(0)
    return h.hexdigest()


def _guess_mimetype(file, nom: str) -> str:
    return getattr(file, 'content_type', None) or mimetypes.guess_type(nom)[0] or ''


@transaction.atomic
def save_pattern_file(*, model=None, garment_type_item=None, dxf, rul=None,
                      document=None, versio_anterior=None, source_asset=None,
                      nom=None, nom_rul=None):
    """Desa un patró respectant la invariant de cadena.

    - Sense `versio_anterior`: cadena nova → versio=1, is_current=True.
    - Amb `versio_anterior`: encadena → versio=pred.versio+1, i el predecessor deixa de
      ser el cap de la cadena.

    És l'ÚNIC punt que escriu `versio`/`is_current`. El serializer no hi toca mai.

    `document` és el `PatternDocument` que el motor ha llegit del DXF: d'aquí surten
    l'empremta, la font CAD i l'escala. Si no ve, es desa el fitxer sense interpretar
    (cas que avui no fa servir ningú, però el servei no ha de decidir per la view).
    """
    nom_fitxer = nom or getattr(dxf, 'name', None) or 'patro.dxf'
    checksum = _compute_checksum(dxf)
    mida = getattr(dxf, 'size', None) or 0
    mimetype = _guess_mimetype(dxf, nom_fitxer)

    if versio_anterior is not None:
        versio = (versio_anterior.versio or 0) + 1
        if model is None and garment_type_item is None:
            # La versió nova hereta l'amo: una cadena no canvia de propietari a mitges.
            model = versio_anterior.model
            garment_type_item = versio_anterior.garment_type_item
    else:
        versio = 1

    fp = PatternFile(
        model=model,
        garment_type_item=garment_type_item,
        source_asset=source_asset,
        versio=versio,
        is_current=True,
        versio_anterior=versio_anterior,
        nom_fitxer=nom_fitxer,
        mida_bytes=mida,
        checksum=checksum,
        mimetype=mimetype,
    )

    if document is not None:
        _aplicar_empremta(fp, document)

    # save=False: el FileField escriu els bytes i fixa .name; el INSERT ve després.
    fp.fitxer_dxf.save(nom_fitxer, dxf, save=False)

    if rul is not None:
        nom_rul_fitxer = nom_rul or getattr(rul, 'name', None) or 'patro.rul'
        fp.nom_rul = nom_rul_fitxer
        fp.mida_rul_bytes = getattr(rul, 'size', None) or 0
        fp.checksum_rul = _compute_checksum(rul)
        fp.fitxer_rul.save(nom_rul_fitxer, rul, save=False)

    fp.save()

    if versio_anterior is not None and versio_anterior.is_current:
        versio_anterior.is_current = False
        versio_anterior.save(update_fields=['is_current'])

    return fp


def _aplicar_empremta(fp: PatternFile, document) -> None:
    """Aplana als camps de consulta el que la UI ensenya i el que es filtra.

    L'empremta SENCERA (el JSON) no s'escriu aquí: n'és amo el `DjangoGeometryStore`,
    que desa el document complet. Aquests camps en són una còpia plana perquè un llistat
    de patrons no hagi d'obrir un JSON per fila.
    """
    fp_data = document.fingerprint
    fp.font_cad = fp_data.font_cad or ''
    if fp_data.unitats:
        fp.escala_mm = fp_data.unitats.factor_to_mm
        fp.unitats_metode = fp_data.unitats.metode.value
        fp.unitats_confianca = fp_data.unitats.confianca.value


def delete_pattern_bytes(fp: PatternFile) -> None:
    """Esborra els bytes dels DOS artefactes abans d'esborrar la fila.

    Mateix precedent que `delete_fitxer_bytes` (S0-B1.4): un disc que falla no ha
    d'impedir mai netejar la BD — que és exactament el cas que es vol poder resoldre.
    """
    import logging

    from django.core.files.storage import default_storage

    logger = logging.getLogger(__name__)
    for camp in (fp.fitxer_dxf, fp.fitxer_rul):
        name = camp.name if camp else ''
        if not name:
            continue
        try:
            if default_storage.exists(name):
                default_storage.delete(name)
        except Exception:
            logger.warning("Bytes de patró no esborrats per a '%s'", name, exc_info=True)
