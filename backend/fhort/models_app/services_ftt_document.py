"""Cicle de persistència de documents .ftt sobre el Finder (ModelFitxer).

Un document .ftt es desa com a `ModelFitxer` tipus TECHSHEET, categoria 'Document',
versionat amb la invariant is_current/save_model_file ja existent. Aquest mòdul orquestra
crear/carregar/desar; l'empaquetat zip viu a `services_ftt` i el versionat a
`services_fitxers.save_model_file` (INTOCABLE: únic escriptor de is_current/versio).

El "Desa" de l'editor = una versió nova encadenada (nou cap de cadena is_current=True,
predecessor a is_current=False), no una sobreescriptura.
"""
from django.core.files.base import ContentFile

from . import services_ftt
from .models import ModelFitxer
from .services_fitxers import save_model_file


def _doc_filename(model):
    base = getattr(model, "codi_intern", None) or model.pk
    return "%s_fitxa%s" % (base, ModelFitxer.FTT_EXTENSION)


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
        categoria="Document",
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
    pot referir-los sense reenviar-ne els bytes. tipus/categoria s'hereten del predecessor
    via save_model_file. Retorna el nou cap de cadena.
    """
    existing = load_document(head_fitxer).get("assets", {})
    if assets:
        existing.update(assets)
    blob = services_ftt.pack(document_json, assets=existing, preview=preview)
    return save_model_file(
        head_fitxer.model,
        ContentFile(blob, name=head_fitxer.nom_fitxer),
        versio_anterior=head_fitxer,  # tipus/categoria heretats
        nom=head_fitxer.nom_fitxer,
    )
