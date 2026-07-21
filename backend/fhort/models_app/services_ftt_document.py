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


# D16 — marca de procedència del congelat. `resolve_placeholders` congela 'field' → 'text' i
# perdia tot rastre de quin camp era: la descongelació cega és impossible. La marca és additiva
# i de cost zero, i sobreviu el round-trip de l'editor (mapObjectTree, TechSheetEditor.jsx:153,
# no fa whitelist de props). Els .ftt anteriors a aquest commit NO en tenen: vegeu
# `unfreeze_document`.
FIELD_MARK = 'field_key'

# Nom de l'asset del logo del client, empaquetat per `_resolve_logo_obj`. L'extensió varia.
LOGO_ASSET_STEM = 'field_customer_logo'

# D16-bis — les claus que lliguen un objecte del canvas al seu HOST (el model on es va crear).
# `unfreeze_document` les posa TOTES a None: un document que canvia de host no pot arrossegar
# els ids del host vell (apuntarien a dades d'un altre model, i el `graded_table` fins i tot les
# re-llegiria en viu). Qualsevol tipus NOU del canvas que porti una referència de host ha
# d'afegir la seva clau aquí: el test `test_cap_referencia_de_host_sobreviu` escaneja el JSON
# sencer recursivament i peta si n'apareix una que no passi per aquí.
HOST_REF_KEYS = ('model_id', 'size_fitting_id', 'pattern_file_id')

# Estat d'un objecte que portava dades del host i n'ha quedat òrfe. NO és un error: és una
# feina pendent, i té representació explícita al canvas i al PDF («Taula per vincular al
# model»). Re-vincular és un clic del TÈCNIC — el sistema no ho fa mai sol (decisió Agus:
# res en silenci, i re-vincular sol seria endevinar quin fitting del host nou toca).
PENDING_MARK = 'pendent_vincle'


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
            name = LOGO_ASSET_STEM + ext
            return name, data, {
                'id': o.get('id'), 'type': 'image', 'layer': o.get('layer', 'free'),
                'x': o.get('x', 0), 'y': o.get('y', 0), 'width': 40, 'height': 16,
                'src': 'assets/' + name,
                FIELD_MARK: 'customer_logo',
            }
        except (ValueError, OSError):
            logger.exception("Logo del client %s il·legible; es deixa buit", getattr(cust, 'pk', None))
    style = o.get('style') or {}
    return None, None, {
        'id': o.get('id'), 'type': 'text', 'layer': o.get('layer', 'free'),
        'x': o.get('x', 0), 'y': o.get('y', 0), 'text': '',
        'fontSize': style.get('fontSize', 11),
        FIELD_MARK: 'customer_logo',
    }


def _resolve_obj(o, vals, model, assets_out):
    """Retorna l'objecte resolt: 'field' → 'text' congelat (customer_logo → 'image')."""
    if o.get('type') == 'field':
        if o.get('key') == 'customer_logo':
            name, data, resolved = _resolve_logo_obj(o, model)
            if name is not None:
                assets_out[name] = data
            return resolved
        key = o.get('key')
        text = vals.get(key, '')
        style = o.get('style') or {}
        return {
            'id': o.get('id'), 'type': 'text', 'layer': o.get('layer', 'free'),
            'x': o.get('x', 0), 'y': o.get('y', 0), 'text': text,
            'fontSize': style.get('fontSize', 11),
            FIELD_MARK: key,   # D16 — sense això, el congelat és irreversible
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


def _is_logo_image_obj(o):
    """Objecte `image kind:'logo'` inserit a mà per l'usuari (TechSheetEditor.jsx:2645).

    El seu `src` és una URL http(s) absoluta cap al logo del model ORIGEN, i
    `_extract_inline_objects` no la reescriu mai (només toca els dataURL). No és el mateix
    que l'asset `field_customer_logo` del placeholder: aquell porta marca i es descongela.
    """
    if o.get('type') != 'image' or o.get('kind') != 'logo':
        return False
    src = o.get('src') or ''
    return src.startswith('http://') or src.startswith('https://')


def _buida_cel_la(c):
    """Buida el VALOR conservant la FORMA de la cel·la (string | {text, sub, bold}).

    La forma és estructura (la sap el renderer: `buildTableCellPrimitives`); el valor és del
    model origen. Buidar-la a `''` sec convertiria una cel·la bilingüe en una de plana.
    """
    if isinstance(c, dict):
        return {k: ('' if k in ('text', 'sub') else v) for k, v in c.items()}
    return ''


def _unfreeze_table(o, report):
    """Taula snapshot S3 (`pom_fitting`/`bom`/`custom`): valors del host → buits.

    Els valors (POMs, mesures base, materials) es van CONGELAR del model origen a la inserció
    (llei S3: cap binding viu). L'estructura —columnes, nombre de files, geometria, estil— NO és
    del host: és el que el tècnic va compondre. Per això la graella es conserva sencera i
    només se'n buiden les cel·les, amb els ids del host a None i la marca «per vincular».
    """
    snapshot = {
        k: (None if k in HOST_REF_KEYS else v)
        for k, v in (o.get('snapshot') or {}).items()
    }
    net = {**o, 'snapshot': snapshot, PENDING_MARK: True}
    if o.get('rows'):
        net['rows'] = [[_buida_cel_la(c) for c in fila] for fila in o['rows']]
    report['taules_desvinculades'] += 1
    return net


def _unfreeze_data_block(o, report):
    """`graded_table` → desvinculada. `header` → intacte (no desa cap valor: es reconstrueix
    a cada render des del `modelData` del host, per això D16 en pren la simetria).

    El `graded_table` és l'únic objecte amb un binding VIU: l'editor re-llegeix
    `/api/v1/fitting/<size_fitting_id>/graded-table/` en obrir. Amb l'id del host vell, al host
    nou serviria la niada d'un ALTRE model sense dir-ho. A None, i que es vegi.
    """
    if o.get('kind') != 'graded_table' or o.get('size_fitting_id') is None:
        return o
    report['taules_desvinculades'] += 1
    return {**o, 'size_fitting_id': None, PENDING_MARK: True}


def _unfreeze_pattern_piece(o, report):
    """Peça de patró (F1): cau l'ID del `PatternFile` del host; el DIBUIX es queda.

    El `src` és un dataURL (o `assets/<sha16>.svg`) que viatja dins el ZIP: el render de la
    peça és estructura auto-continguda —exactament el que una biblioteca de sketches vol
    conservar—. L'únic que era del host és el punter de traçabilitat, i marxa. No queda
    «per vincular»: no falta res a la vista, i inventar-hi una feina pendent seria soroll.
    """
    if o.get('pattern_file_id') is None:
        return o
    report['peces_despenjades'] += 1
    return {**o, 'pattern_file_id': None}


def _unfreeze_mapper(o, report):
    """'text'/'image' amb marca → 'field' (geometria intacta). Sense marca, per tipus."""
    key = o.get(FIELD_MARK)
    if not key:
        tipus = o.get('type')
        if tipus == 'table':
            return _unfreeze_table(o, report)
        if tipus == 'data_block':
            return _unfreeze_data_block(o, report)
        # R6 — la peça de patró s'insereix ara com a `path` vectorial, no com a imatge; el que
        # la identifica és el punter de traçabilitat, no el tipus. Es mira el camp perquè la
        # regla valgui per als dos: els documents antics (pattern_piece) i els nous (path).
        if tipus == 'pattern_piece' or (tipus == 'path' and o.get('pattern_file_id') is not None):
            return _unfreeze_pattern_piece(o, report)
        return o
    report['camps_descongelats'] += 1
    style = dict(o.get('style') or {})
    # El congelat desa fontSize a l'arrel; el 'field' l'espera dins style (buildFieldChipPrims).
    if 'fontSize' in o and 'fontSize' not in style:
        style['fontSize'] = o['fontSize']
    camp = {
        'id': o.get('id'), 'type': 'field', 'key': key,
        'layer': o.get('layer', 'free'), 'x': o.get('x', 0), 'y': o.get('y', 0),
    }
    if style:
        camp['style'] = style
    return camp


def _unfreeze_objects(objects, report):
    """Elimina les imatges de logo de l'origen i descongela la resta, recursivament."""
    out = []
    for o in objects or []:
        if _is_logo_image_obj(o):
            report['imatges_logo_eliminades'] += 1
            continue
        # _map_object_tree recorre l'arbre (fills inclosos); no pot ELIMINAR nodes, per això
        # el filtre de logos va a part, en aquest mateix bucle.
        out.append(services_ftt._map_object_tree(o, lambda x: _unfreeze_mapper(x, report)))
    return out


def unfreeze_document(document_json, assets):
    """Invers de `resolve_placeholders` (D16). Retorna (document_json, assets, report).

    Un `.ftt` d'un model A porta coses materialitzades de A; aquesta funció les desfà TOTES:

      1. Text congelat dels `field` de plantilla → torna a `type:'field'` per la marca
         `field_key`. Geometria (id/layer/x/y) i estil intactes.
      2. Asset `assets/field_customer_logo.<ext>` (bytes del logo del client de A) → purgat.
      3. Objecte `image kind:'logo'` amb URL absoluta al logo de A → eliminat.
      4. `metadata{}` → buidada.
      5. Taules snapshot S3 (`type:'table'`) → cel·les buidades conservant la graella, ids del
         host a None, marca «per vincular» (`_unfreeze_table`).
      6. `data_block kind:'graded_table'` → `size_fitting_id` a None + «per vincular»
         (`_unfreeze_data_block`). És l'únic binding VIU del document.
      7. `pattern_piece` (F1) → cau `pattern_file_id`; el dibuix es queda
         (`_unfreeze_pattern_piece`).

    Els punts 5-7 són D16-bis: 1-4 es van escriure quan el document encara no tenia ni taules
    snapshot ni peces de patró, i la funció s'havia quedat enrere —deia que descongelava i
    deixava passar les mesures del model origen—. La capçalera `data_block kind:'header'` NO es
    toca: no desa cap valor, es reconstrueix a cada render des de `modelData` del host.

    El que NO fa, i és deliberat: **re-vincular**. Les taules queden buides i marcades, i és el
    tècnic qui les torna a lligar amb un clic. Endevinar quin fitting del host nou correspon a
    la taula del host vell seria escriure dades que ningú ha demanat (decisió Agus).

    DEGRADACIÓ CONEGUDA I ACCEPTADA: els `.ftt` creats abans que `resolve_placeholders` posés
    la marca no en tenen cap. Per a aquests, els texts congelats es deixen TAL QUAL (mostraran
    dades de A) i `report['te_marques']` és False perquè el caller ho pugui advertir. NO s'hi
    fa cap heurística de matching per contingut: seria fràgil (dos camps amb el mateix valor,
    text editat a mà) i podria corrompre documents. L'usuari els edita a mà.
    """
    report = {'camps_descongelats': 0, 'imatges_logo_eliminades': 0,
              'assets_logo_purgats': 0, 'te_marques': False,
              'taules_desvinculades': 0, 'peces_despenjades': 0}

    pages = [
        {**p, 'objects': _unfreeze_objects(p.get('objects'), report)}
        for p in (document_json.get('pages') or [])
    ]
    report['te_marques'] = report['camps_descongelats'] > 0

    nets = {}
    for name, data in (assets or {}).items():
        if os.path.splitext(name)[0] == LOGO_ASSET_STEM:
            report['assets_logo_purgats'] += 1
            continue
        nets[name] = data

    # metadata buida: `ftt_schema` i `pageFormat` són germans de metadata, no fills — es mantenen.
    return {**document_json, 'metadata': {}, 'pages': pages}, nets, report


def reescriure_ftt_per_model(blob, model_desti):
    """Bytes d'un `.ftt` del model A → bytes del mateix `.ftt` per al model B (D16).

    unfreeze (treu tot el que és de A) → resolve_placeholders (congela amb les dades de B).
    El resultat és indistingible d'instanciar la plantilla directament sobre B: el document
    importat torna a ser "jove". Retorna (blob_nou, report).

    El `preview.png` NO es propaga: és un render dels valors de A i quedaria com una 5a cosa
    materialitzada de l'origen. Es regenera sol al primer desat des de l'editor.
    """
    paquet = services_ftt.unpack(blob)
    document_json, assets, report = unfreeze_document(
        paquet['document_json'], paquet.get('assets') or {})
    document_json, assets_desti = resolve_placeholders(document_json, model_desti)
    assets.update(assets_desti)
    return services_ftt.pack(document_json, assets=assets), report


def font_per_al_model(origen, model_desti):
    """L'origen (ModelFitxer **o** ItemFitxer), llest per copiar-lo al model destí.

    UN SOL CAMÍ de descongelat per a tots els orígens. Abans n'hi havia dos i no feien el
    mateix: el de model→model descongelava (D16) i el de catàleg→model copiava els bytes tal
    qual, emparat en una docstring que deia que «un `.ftt` es copia tal qual: el ZIP és
    auto-contingut». Això només és cert si el `.ftt` de l'item no ve d'un model — i l'única
    manera d'entrar-ne un al catàleg, avui, és pujar-hi el que algú s'ha baixat d'un model.
    Un ItemFitxer no és una font neta per definició: ho és pel que porta a dins.

    Retorna `(font, report|None)`; `report` és None si l'origen no és un `.ftt` (PDF, DXF,
    SVG, imatges: còpia directa de bytes). Cal cridar-la amb els bytes de l'origen oberts.
    """
    if not es_ftt(origen):
        return origen.fitxer, None
    blob, report = reescriure_ftt_per_model(origen.fitxer.read(), model_desti)
    return ContentFile(blob, name=origen.nom_fitxer), report


def avis_de_copia(report):
    """El que el tècnic ha de saber d'una còpia, o None si no hi ha res a dir.

    Res en silenci: si el document ha perdut el seu vincle amb el model origen, la resposta
    ho diu. Qui ho ha de llegir és una persona, no un log.
    """
    if report is None:
        return None
    avisos = []
    if report.get('taules_desvinculades'):
        n = report['taules_desvinculades']
        avisos.append(
            f"{n} {'taula' if n == 1 else 'taules'} {'ha' if n == 1 else 'han'} quedat "
            "PER VINCULAR: la graella es conserva, però els valors eren del model origen i "
            "s'han buidat. Cal tornar-les a vincular al model."
        )
    if report.get('camps_descongelats') == 0:
        # Degradació anunciada (D16): .ftt anterior a la marca `field_key`. Els camps de
        # plantilla congelats segueixen mostrant dades del model origen.
        avisos.append(
            "El document és anterior al marcatge de camps: els camps de plantilla mantenen "
            "les dades del model origen i cal editar-los a mà."
        )
    return ' '.join(avisos) if avisos else None


def es_ftt(fitxer):
    """True si el ModelFitxer és un document .ftt (per tipus o per extensió)."""
    if fitxer.tipus == ModelFitxer.TIPUS_TECHSHEET:
        return True
    nom = fitxer.nom_fitxer or ''
    return nom.lower().endswith(ModelFitxer.FTT_EXTENSION)


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


def save_document(head_fitxer, document_json, *, assets=None, preview=None, kind=None):
    """Desa una versió nova encadenada del document.

    Els assets existents es conserven (es fusionen amb els nous) perquè el document.json
    pot referir-los sense reenviar-ne els bytes. `tipus` s'hereta del predecessor via
    save_model_file. Retorna el nou cap de cadena.

    S03a · P3 — abans d'empaquetar, els binaris inline (imatges noves de l'editor, que hi
    arriben com a dataURL) s'extreuen a assets/<sha16>.<ext>. Cap dataURL nou es persisteix
    dins document.json. Les fitxes velles amb inline es sanegen soles en re-desar-se: no cal
    cap migració de dades. Idempotent (sha del contingut → re-desar no fa créixer res).
    """
    document_json, inline_assets = services_ftt.extract_document_assets(document_json)
    anterior = load_document(head_fitxer)
    existing = anterior.get("assets", {})
    if assets:
        existing.update(assets)
    existing.update(inline_assets)
    # `kind` del manifest: fins ara cada desat el tornava al valor per defecte ("document"),
    # de manera que un document marcat com a plantilla ho perdia al primer autosave. Ara
    # s'HERETA del predecessor si el caller no en diu res, i el caller el pot canviar
    # explícitament (és el que fa l'interruptor de mode plantilla de l'editor).
    kind_final = kind or anterior.get("kind") or services_ftt.FTT_KIND_DOCUMENT
    blob = services_ftt.pack(document_json, assets=existing, preview=preview, kind=kind_final)
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
