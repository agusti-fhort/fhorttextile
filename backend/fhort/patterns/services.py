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


# ═════════════════════════════════════════════════════════════════════════════
# I2a — identificació de peces (escriptura + acta)
# ═════════════════════════════════════════════════════════════════════════════

#: ⚠️ TEXT PROVISIONAL. Viu aquí i no al frontend pel mateix motiu que `GATE_TEXT_CA` de
#: l'exportació: és el text que es DESA a l'acta, i si la font fos el bundle del navegador,
#: el que quedaria registrat seria el que el navegador d'aquell dia deia.
CONFIRM_TEXT_CA = (
    'Confirmo que he revisat la identitat de cada peça d\'aquest patró: què és, de quin '
    'costat i en quin estat. El sistema no ho ha endevinat.'
)

#: Els camps que el client pot escriure. `rol_origen` NO hi és a posta: el decideix el
#: servidor comparant amb el que hi havia — si el client el pogués enviar, podria dir que
#: una cosa l'ha confirmada una persona quan no és cert, i el senyal deixaria de valer.
CAMPS_ESCRIVIBLES = ('piece_role_id', 'nom', 'lateralitat', 'ordinal', 'estat_peca')


class IdentificacioRebutjada(Exception):
    """La petició no es pot aplicar. Missatge per a qui l'ha feta, mai un 500."""


def _valida_fila(fila, peces_del_fitxer, rols_existents):
    from .models import PatternPiece

    piece_id = fila.get('piece_id')
    peca = peces_del_fitxer.get(piece_id)
    if peca is None:
        raise IdentificacioRebutjada(
            f'La peça {piece_id} no és d\'aquest patró. Una identificació no pot tocar '
            f'peces d\'un altre fitxer.')

    rol_id = fila.get('piece_role_id')
    if rol_id is not None and rol_id not in rols_existents:
        raise IdentificacioRebutjada(f'El rol de peça {rol_id} no existeix al catàleg.')

    lat = fila.get('lateralitat')
    if lat is not None and lat not in dict(PatternPiece.LAT_CHOICES):
        raise IdentificacioRebutjada(f'Lateralitat no vàlida: {lat!r}.')

    estat = fila.get('estat_peca')
    if estat is not None and estat not in dict(PatternPiece.ESTAT_CHOICES):
        raise IdentificacioRebutjada(f'Estat de peça no vàlid: {estat!r}.')

    return peca


@transaction.atomic
def identificar_peces(*, pattern_file, files, usuari=None, confirm=False,
                      texts_shown=''):
    """Escriu la identitat d'unes quantes peces. Amb `confirm`, hi deixa ACTA.

    Servei propi i no serializer escrivible, per la llei del mòdul (`views.py:5-7`): qui
    escriu ha de saber mantenir el que la fila implica, i aquí implica dues coses que un
    ModelSerializer no faria — decidir `rol_origen` comparant amb el que hi havia, i
    aixecar l'acta d'una sola peça amb la resta.

    **Es pot desar sense confirmar.** Canviar un rol i marxar és un estat legítim del
    treball: la Montse pot identificar un patró a trossos. El que NO passa sense `confirm`
    és l'acta — perquè no s'ha confirmat res.
    """
    from fhort.pom.models import PatternPieceRole

    from .models import PieceIdentityAcknowledgement

    peces_del_fitxer = {p.id: p for p in pattern_file.pieces.select_related('piece_role')}
    rols_existents = set(PatternPieceRole.objects.values_list('id', flat=True))

    tocades = []
    for fila in files:
        peca = _valida_fila(fila, peces_del_fitxer, rols_existents)

        canvis = []
        if 'piece_role_id' in fila:
            nou_rol = fila['piece_role_id']
            # Tres actes humans diferents, tres senyals diferents. Col·lapsar-los faria
            # que, el dia que el motor proposi rols (I2b), no es pogués saber de què es
            # fia el sistema: quantes vegades encerta i quantes el corregeixen.
            if nou_rol is None:
                # Treure el rol: no queda cap rol de què dir la procedència.
                peca.rol_origen = peca.ROL_ORIGEN_CAP
            elif peca.piece_role_id == nou_rol:
                # RATIFICAR no és corregir: la persona no l'ha canviat, l'ha donat per bo.
                peca.rol_origen = peca.ROL_ORIGEN_CONFIRMAT
            elif peca.piece_role_id is None:
                # ASSIGNAR no és corregir: no hi havia res a corregir.
                peca.rol_origen = peca.ROL_ORIGEN_ASSIGNAT
            else:
                peca.rol_origen = peca.ROL_ORIGEN_CORREGIT
            peca.piece_role_id = nou_rol
            canvis += ['piece_role', 'rol_origen']

        for camp in ('nom', 'lateralitat', 'ordinal', 'estat_peca'):
            if camp in fila:
                setattr(peca, camp, fila[camp])
                canvis.append(camp)

        if canvis:
            peca.save(update_fields=canvis)
            tocades.append(peca)

    acta = None
    if confirm:
        acta = PieceIdentityAcknowledgement.objects.create(
            pattern_file=pattern_file,
            versio_patro=pattern_file.versio,
            snapshot=_snapshot(pattern_file),
            usuari=usuari,
            texts_shown=(texts_shown or CONFIRM_TEXT_CA).strip(),
        )

    return tocades, acta


def _snapshot(pattern_file) -> list:
    """Què deia cada peça IDENTIFICADA al moment de confirmar, copiat.

    Només les que tenen rol: confirmar la identitat d'una peça que encara no en té no vol
    dir res, i inflar l'acta amb files buides faria que el recompte mentís.
    """
    return [
        {
            'piece_id': p.id,
            'nom_block': p.nom_block,
            'rol_slug': p.piece_role.slug if p.piece_role_id else '',
            'nom': p.nom,
            'lateralitat': p.lateralitat,
            'ordinal': p.ordinal,
            'estat_peca': p.estat_peca,
        }
        for p in pattern_file.pieces.select_related('piece_role').order_by('id')
        if p.piece_role_id is not None
    ]
