"""Template FTT — plantilla mestra de capçalera de fitxa tècnica (S12).

`build_master_header_document()` retorna un document_json DETERMINISTA: una pàgina A4
apaïsat amb un únic `data_block kind:'header'` marcat `config.layout='masterFtt'`. La
GEOMETRIA i el mapatge de camps viuen al renderer frontend (buildMasterHeaderPrimitives);
aquí només es marca el bloc i es fixa la seva caixa (mm). El logo del customer NO es cou:
es resol al render des de `customer.logo`.

`seed_master_template()` la pack-eja i crea/actualitza el DocumentTemplate "Template FTT"
del tenant actual (origen sistema). Idempotent: re-executar regenera el fitxer. És el pas
especial de sembra de bootstrap_tenant (NO una peça de _spec: _spec copia files de BD i
aquesta plantilla és file-backed a media → cal generar-la, no copiar-la).
"""
import logging

from django.core.files.base import ContentFile

from . import services_ftt

logger = logging.getLogger(__name__)

MASTER_TEMPLATE_NAME = 'Template FTT'
MASTER_TEMPLATE_DESC = (
    'Plantilla mestra de capçalera de fitxa tècnica (3 caixes: document · identificació · '
    'definició tècnica). Etiquetes angleses fixes; valors del model + logo del client al '
    'render. Consciència de pàgina (PAGE i/n). Sembrada a cada tenant per bootstrap_tenant.'
)

# Caixa de la capçalera (mm), mapada des de la geometria del brief en pt (×0.3528 mm/pt):
# banda x=28.6 y=39 w=784.7 h=90.2 pt.
_HEADER_OBJ = {
    'id': 'hdr1', 'type': 'data_block', 'kind': 'header', 'layer': 'template',
    'x': 10.1, 'y': 13.8, 'width': 276.9, 'height': 31.8,
    'locked': True,                       # bloc ancorat: no draggable ni seleccionable per edició
    'config': {'layout': 'masterFtt'},
}


def build_master_header_document():
    """document_json determinista de la Template FTT (una pàgina, header mestre ancorat)."""
    return {
        'ftt_schema': services_ftt.FTT_DOCUMENT_SCHEMA,
        'metadata': {},
        'pageFormat': services_ftt.DEFAULT_PAGE_FORMAT,   # 'A4L'
        'pages': [{'id': 'p1', 'objects': [dict(_HEADER_OBJ)]}],
    }


def seed_master_template():
    """Crea/actualitza el DocumentTemplate "Template FTT" del tenant actual. Idempotent.

    Retorna (template, created). Regenera SEMPRE el fitxer .fttpt (esborrant l'anterior) perquè
    re-executar reflecteixi els canvis del document determinista.
    """
    from .ftt_models import DocumentTemplate

    blob = services_ftt.pack(build_master_header_document(), kind=services_ftt.FTT_KIND_TEMPLATE)
    tpl, created = DocumentTemplate.objects.get_or_create(
        nom=MASTER_TEMPLATE_NAME,
        defaults={'descripcio': MASTER_TEMPLATE_DESC, 'origen': 'sistema',
                  'is_sample': True, 'actiu': True},
    )
    old_name = tpl.fitxer_template.name if tpl.fitxer_template else None
    tpl.descripcio = MASTER_TEMPLATE_DESC
    tpl.origen = 'sistema'
    tpl.is_sample = True
    tpl.actiu = True
    tpl.fitxer_template.save('template_ftt.fttpt', ContentFile(blob), save=False)
    tpl.save()
    if old_name and old_name != tpl.fitxer_template.name:
        try:
            tpl.fitxer_template.storage.delete(old_name)
        except OSError:
            logger.warning('No s\'ha pogut esborrar el .fttpt antic: %s', old_name)
    return tpl, created
