"""Cicle de persistència de documents .ftt sobre el Finder (ModelFitxer).

Un document .ftt es desa com a `ModelFitxer` tipus TECHSHEET, categoria 'Document',
versionat amb la invariant is_current/save_model_file ja existent. Aquest mòdul orquestra
crear/carregar/desar; l'empaquetat zip viu a `services_ftt` i el versionat a
`services_fitxers.save_model_file` (INTOCABLE: únic escriptor de is_current/versio).

El "Desa" de l'editor = una versió nova encadenada (nou cap de cadena is_current=True,
predecessor a is_current=False), no una sobreescriptura.
"""
import datetime
import logging
import os

from django.core.files.base import ContentFile
from django.utils import timezone

from . import services_ftt
from .models import FttDocumentLock, ModelFitxer
from .services_fitxers import save_model_file

logger = logging.getLogger(__name__)

# Caducitat del lock: passat aquest temps sense renovar, un altre usuari el pot forçar.
FTT_LOCK_TTL = datetime.timedelta(minutes=30)


def document_root(fitxer):
    """Arrel (v1) de la cadena versio_anterior: identitat estable del document lògic."""
    node = fitxer
    while node.versio_anterior_id is not None:
        node = node.versio_anterior
    return node


def acquire_lock(fitxer, user):
    """Adquireix el lock del document lògic. Retorna (lock, ok).

    ok=True si era lliure, ja era teu, o estava caducat (force-if-stale). ok=False si
    l'ocupa algú altre amb lock vigent.
    """
    root = document_root(fitxer)
    now = timezone.now()
    lock, _ = FttDocumentLock.objects.get_or_create(document_root=root)
    holder = lock.locked_by
    is_free = holder is None
    is_mine = holder == user
    is_stale = (
        holder is not None
        and lock.locked_at is not None
        and lock.locked_at < now - FTT_LOCK_TTL
    )
    if is_free or is_mine or is_stale:
        lock.locked_by = user
        lock.locked_at = now
        lock.save(update_fields=['locked_by', 'locked_at'])
        return lock, True
    return lock, False


def release_lock(fitxer, user, *, can_override=False):
    """Allibera el lock. Retorna False si l'ocupa algú altre i no hi ha override CONFIGURE."""
    root = document_root(fitxer)
    try:
        lock = FttDocumentLock.objects.get(document_root=root)
    except FttDocumentLock.DoesNotExist:
        return True
    if lock.locked_by is not None and lock.locked_by != user and not can_override:
        return False
    lock.locked_by = None
    lock.locked_at = None
    lock.save(update_fields=['locked_by', 'locked_at'])
    return True


def user_holds_lock(fitxer, user):
    root = document_root(fitxer)
    return FttDocumentLock.objects.filter(document_root=root, locked_by=user).exists()


def renew_lock(fitxer, user):
    """Renova locked_at si l'usuari té el lock (arreglo del timer-gap). True si renovat."""
    root = document_root(fitxer)
    updated = FttDocumentLock.objects.filter(
        document_root=root, locked_by=user
    ).update(locked_at=timezone.now())
    return bool(updated)


def _doc_filename(model):
    base = getattr(model, "codi_intern", None) or model.pk
    return "%s_fitxa%s" % (base, ModelFitxer.FTT_EXTENSION)


def _placeholder_values(model):
    """Construeix el mapa key→valor (str) per resoldre placeholders des del model."""
    from fhort.models_app.serializers import ModelDetailSerializer  # import local: evita cicles

    data = ModelDetailSerializer(model).data
    keys = [
        'nom_prenda', 'codi_intern', 'codi_client', 'customer_nom', 'collection',
        'color_referencia', 'descripcio', 'responsable_nom', 'data_entrada',
        'base_size_label', 'size_system_nom', 'fabric_main', 'fabric_composition',
    ]
    vals = {k: ('' if data.get(k) is None else str(data.get(k))) for k in keys}
    vals['temporada_any'] = (f"{data.get('temporada') or ''} {data.get('any') or ''}").strip()
    vals['data_avui'] = timezone.localdate().isoformat()
    return vals  # customer_logo intencionadament absent: es resol com a imatge a _resolve_obj


def _resolve_logo_obj(o, model):
    """Resol el placeholder customer_logo: 'image' amb el logo del client com a asset,
    o 'text' buit si el client no en té (mai bloquejant)."""
    cust = getattr(model, 'customer', None)
    logo = getattr(cust, 'logo', None) if cust else None
    if logo:
        try:
            logo.open('rb')
            try:
                data = logo.read()
            finally:
                logo.close()
            ext = os.path.splitext(logo.name)[1] or '.png'
            name = 'field_customer_logo' + ext
            return name, data, {
                'id': o.get('id'), 'type': 'image', 'layer': o.get('layer', 'free'),
                'x': o.get('x', 0), 'y': o.get('y', 0), 'width': 40, 'height': 16,
                'src': 'assets/' + name,
            }
        except (ValueError, OSError):
            logger.exception("Logo del client %s il·legible; es deixa buit", getattr(cust, 'pk', None))
    style = o.get('style') or {}
    return None, None, {
        'id': o.get('id'), 'type': 'text', 'layer': o.get('layer', 'free'),
        'x': o.get('x', 0), 'y': o.get('y', 0), 'text': '',
        'fontSize': style.get('fontSize', 11),
    }


def _resolve_obj(o, vals, model, assets_out):
    """Retorna l'objecte resolt: 'field' → 'text' congelat (customer_logo → 'image')."""
    if o.get('type') == 'field':
        if o.get('key') == 'customer_logo':
            name, data, resolved = _resolve_logo_obj(o, model)
            if name is not None:
                assets_out[name] = data
            return resolved
        text = vals.get(o.get('key'), '')
        style = o.get('style') or {}
        return {
            'id': o.get('id'), 'type': 'text', 'layer': o.get('layer', 'free'),
            'x': o.get('x', 0), 'y': o.get('y', 0), 'text': text,
            'fontSize': style.get('fontSize', 11),
        }
    if o.get('children'):
        return {**o, 'children': [_resolve_obj(c, vals, model, assets_out) for c in o['children']]}
    return o


def resolve_placeholders(document_json, model):
    """Instanciació des de plantilla: congela cada 'field' com a 'text' amb el valor real
    del model (snapshot; no binding en viu); customer_logo es resol com a 'image' amb el
    logo del client empaquetat com a asset. Retorna (document_json, assets)."""
    vals = _placeholder_values(model)
    assets = {}
    pages = [
        {**p, 'objects': [_resolve_obj(o, vals, model, assets) for o in (p.get('objects') or [])]}
        for p in (document_json.get('pages') or [])
    ]
    return {**document_json, 'pages': pages}, assets


def create_document(model, *, document_json=None, assets=None, preview=None, nom=None):
    """Crea la v1 d'un document .ftt per al model (cadena nova, is_current=True)."""
    if document_json is None:
        document_json = services_ftt.new_empty_document()
    blob = services_ftt.pack(document_json, assets=assets, preview=preview)
    filename = nom or _doc_filename(model)
    return save_model_file(
        model,
        ContentFile(blob, name=filename),
        tipus=ModelFitxer.TIPUS_TECHSHEET,
        nom=filename,
    )


def load_document(fitxer):
    """Desempaqueta el .ftt d'un ModelFitxer i retorna el contingut lògic (sense el zip)."""
    fitxer.fitxer.open("rb")
    try:
        blob = fitxer.fitxer.read()
    finally:
        fitxer.fitxer.close()
    return services_ftt.unpack(blob)


def save_document(head_fitxer, document_json, *, assets=None, preview=None):
    """Desa una versió nova encadenada del document.

    Els assets existents es conserven (es fusionen amb els nous) perquè el document.json
    pot referir-los sense reenviar-ne els bytes. `tipus` s'hereta del predecessor via
    save_model_file. Retorna el nou cap de cadena.
    """
    existing = load_document(head_fitxer).get("assets", {})
    if assets:
        existing.update(assets)
    blob = services_ftt.pack(document_json, assets=existing, preview=preview)
    return save_model_file(
        head_fitxer.model,
        ContentFile(blob, name=head_fitxer.nom_fitxer),
        versio_anterior=head_fitxer,  # tipus heretat
        nom=head_fitxer.nom_fitxer,
    )


def save_export(source_ftt, file, *, nom=None):
    """Desa un PDF d'export com a ModelFitxer EXPORT enllaçat a la versió .ftt origen.

    L'export és la SEVA pròpia cadena (versio_anterior=None): el document .ftt NO es toca
    (el seu is_current es manté). L'enllaç a la versió que el va generar es desa a
    `generat_des_de`. save_model_file segueix sent l'únic escriptor de is_current/versio;
    `generat_des_de` s'escriu a part (no és camp de cadena).
    """
    filename = nom or getattr(file, "name", None) or "export.pdf"
    export = save_model_file(
        source_ftt.model,
        file,
        tipus=ModelFitxer.TIPUS_EXPORT,
        nom=filename,
    )
    export.generat_des_de = source_ftt
    export.save(update_fields=["generat_des_de"])
    return export
