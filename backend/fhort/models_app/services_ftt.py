"""Format .ftt — contenidor zip propietari per a documents de fitxa tècnica.

Un fitxer .ftt és un zip estàndard amb aquesta estructura:

    manifest.json   {magic:"FTT", schema_version:1, app_version, checksums:{path->sha256}}
    document.json   el document lògic (estructura v-ftt; opac per a aquest mòdul)
    assets/<nom>    binaris referenciats pel document (imatges, logos, ...)
    preview.png     (opcional) render PNG de previsualització

`pack`/`unpack` són funcions PURES: no toquen BD ni Django, només zipfile + json +
hashlib de la llibreria estàndard. Això les fa testables aïlladament i sense dependència
nova. El desempaquetat viu al backend; el client mai rep el zip (rep document.json + URLs).
"""
import base64
import hashlib
import io
import json
import re
import zipfile
from urllib.parse import unquote_to_bytes

FTT_MAGIC = "FTT"
FTT_SCHEMA_VERSION = 1
FTT_APP_VERSION = "0.1.0"

# Tipus de document dins el .ftt (manifest.kind). Retrocompat: absent → document.
FTT_KIND_DOCUMENT = "document"
FTT_KIND_TEMPLATE = "template"

MANIFEST_NAME = "manifest.json"
DOCUMENT_NAME = "document.json"
PREVIEW_NAME = "preview.png"
ASSETS_PREFIX = "assets/"

# Esquema del document lògic (document.json), distint del schema_version del contenidor.
FTT_DOCUMENT_SCHEMA = 1
DEFAULT_PAGE_FORMAT = "A4L"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def new_empty_document(metadata=None, page_format=DEFAULT_PAGE_FORMAT):
    """Document.json mínim vàlid: una pàgina buida, metadata buida.

    Estructura v-ftt:
        {ftt_schema, metadata{}, pageFormat, pages:[{id, objects:[]}]}
    """
    return {
        "ftt_schema": FTT_DOCUMENT_SCHEMA,
        "metadata": metadata or {},
        "pageFormat": page_format,
        "pages": [{"id": "p1", "objects": []}],
    }


def pack(document_json, assets=None, preview=None, app_version=FTT_APP_VERSION, kind=FTT_KIND_DOCUMENT):
    """Empaqueta un document lògic en un blob .ftt (bytes).

    - `document_json`: dict serialitzable a JSON.
    - `assets`: dict {nom -> bytes} de binaris; es desen sota `assets/<nom>`.
    - `preview`: bytes PNG opcionals; es desen com `preview.png`.
    - `kind`: "document" (per defecte) o "template"; discriminador al manifest.

    El manifest hi inclou un sha256 per cada peça per a auditoria/integritat futura.
    """
    assets = assets or {}
    document_bytes = json.dumps(
        document_json, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    checksums = {DOCUMENT_NAME: _sha256(document_bytes)}
    for name, data in assets.items():
        checksums[ASSETS_PREFIX + name] = _sha256(data)
    if preview is not None:
        checksums[PREVIEW_NAME] = _sha256(preview)

    manifest = {
        "magic": FTT_MAGIC,
        "schema_version": FTT_SCHEMA_VERSION,
        "app_version": app_version,
        "kind": kind,
        "checksums": checksums,
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            MANIFEST_NAME,
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2),
        )
        zf.writestr(DOCUMENT_NAME, document_bytes)
        for name, data in assets.items():
            zf.writestr(ASSETS_PREFIX + name, data)
        if preview is not None:
            zf.writestr(PREVIEW_NAME, preview)
    return buf.getvalue()


# ── Mapatge template_json v2 ↔ document.json v-ftt ───────────────────────────
# El template_json v2 de l'editor és {version:2, pages:[{id,objects}], pageFormat}. Els
# binaris inline (image.src com a dataURL) es treuen a assets/<hash>.<ext> deixant
# src='assets/<nom>' → document.json lleuger i binaris fora del JSON.

_DATAURL_RE = re.compile(r"^data:(?P<mime>[^;,]*);?(?P<b64>base64)?,(?P<data>.*)$", re.DOTALL)
_MIME_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/svg+xml": "svg",
}


def _decode_dataurl(src):
    """Retorna (bytes, mime) d'un dataURL, o None si no ho és."""
    m = _DATAURL_RE.match(src)
    if not m:
        return None
    raw = m.group("data")
    if m.group("b64"):
        data = base64.b64decode(raw)
    else:
        data = unquote_to_bytes(raw)
    return data, (m.group("mime") or "application/octet-stream")


def _map_object_tree(obj, mapper):
    """Aplica `mapper` a l'objecte i, recursivament, als seus `children`.

    Mirall exacte de mapObjectTree (TechSheetEditor.jsx:152-156): els objectes de l'editor
    són un ARBRE (grups amb fills), no una llista plana. Un recorregut pla es deixaria les
    imatges niades dins de grups.
    """
    obj = mapper(dict(obj))
    children = obj.get("children")
    if isinstance(children, list):
        obj["children"] = [_map_object_tree(c, mapper) for c in children]
    return obj


def _extract_inline_objects(objects, assets):
    """Treu els `src` dataURL dels objectes (i dels seus fills) a `assets`, in-place al dict."""
    def mapper(obj):
        src = obj.get("src")
        if isinstance(src, str) and src.startswith("data:"):
            decoded = _decode_dataurl(src)
            if decoded is not None:
                data, mime = decoded
                # sha16 del contingut: el mateix binari mai es duplica i re-desar és estable.
                name = "%s.%s" % (_sha256(data)[:16], _MIME_EXT.get(mime, "bin"))
                assets[name] = data
                obj["src"] = ASSETS_PREFIX + name
        return obj

    return [_map_object_tree(o, mapper) for o in objects or []]


def extract_document_assets(document_json):
    """document.json → (document.json sense dataURL, assets:{nom->bytes}).   [S03a · P3]

    Font ÚNICA de l'extracció inline→assets: hi criden el camí de PLANTILLES (v2_to_document)
    i el de DOCUMENTS (services_ftt_document.save_document). Preserva TOTA la resta del
    document: `guides` de pàgina, claus desconegudes i l'arbre de fills. Idempotent: un
    document sense dataURL torna igual i amb assets={}.
    """
    assets = {}
    doc = dict(document_json)
    pages_out = []
    for page in doc.get("pages") or []:
        page = dict(page)
        page["objects"] = _extract_inline_objects(page.get("objects"), assets)
        pages_out.append(page)
    doc["pages"] = pages_out
    return doc, assets


def v2_to_document(template_json, metadata=None):
    """template_json v2 → (document_json v-ftt, assets:{nom->bytes}).

    Extreu cada binari inline (objecte amb `src` dataURL) a assets/<sha16>.<ext> i hi
    deixa `src='assets/<nom>'`. La resta de l'objecte es conserva intacta.
    """
    assets = {}
    pages_out = []
    for page in template_json.get("pages") or []:
        pages_out.append({
            "id": page.get("id"),
            "objects": _extract_inline_objects(page.get("objects"), assets),
        })
    document = {
        "ftt_schema": FTT_DOCUMENT_SCHEMA,
        "metadata": metadata or {},
        "pageFormat": template_json.get("pageFormat") or DEFAULT_PAGE_FORMAT,
        "pages": pages_out,
    }
    return document, assets


def document_to_v2(document_json, asset_src=None):
    """document.json v-ftt → template_json v2 (per carregar a l'editor).

    `asset_src(nom) -> str` reescriu les refs `assets/<nom>` (p.ex. a URL absoluta servida
    pel backend). Per defecte les deixa com `assets/<nom>`.
    """
    def mapper(obj):
        src = obj.get("src")
        if isinstance(src, str) and src.startswith(ASSETS_PREFIX) and asset_src is not None:
            obj["src"] = asset_src(src[len(ASSETS_PREFIX):])
        return obj

    pages_out = []
    for page in document_json.get("pages") or []:
        pages_out.append({
            "id": page.get("id"),
            "objects": [_map_object_tree(o, mapper) for o in page.get("objects") or []],
        })
    return {
        "version": 2,
        "pageFormat": document_json.get("pageFormat") or DEFAULT_PAGE_FORMAT,
        "pages": pages_out,
    }


def unpack(blob):
    """Desempaqueta un blob .ftt i retorna un dict.

    Retorna {manifest, document_json, assets:{nom->bytes}, preview:bytes|None, kind}.
    `kind` és normalitzat: si el manifest no en té (fitxers antics), es fixa a
    FTT_KIND_DOCUMENT per retrocompatibilitat.
    Valida `magic == "FTT"` i `schema_version` suportat; si no, ValueError clar.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile as exc:
        raise ValueError(".ftt no és un zip vàlid: %s" % exc)

    with zf:
        names = set(zf.namelist())
        if MANIFEST_NAME not in names:
            raise ValueError(".ftt sense %s" % MANIFEST_NAME)

        try:
            manifest = json.loads(zf.read(MANIFEST_NAME))
        except json.JSONDecodeError as exc:
            raise ValueError(".ftt amb manifest il·legible: %s" % exc)

        magic = manifest.get("magic")
        if magic != FTT_MAGIC:
            raise ValueError(
                ".ftt amb magic invàlid: %r (esperat %r)" % (magic, FTT_MAGIC)
            )
        schema_version = manifest.get("schema_version")
        if schema_version != FTT_SCHEMA_VERSION:
            raise ValueError(
                ".ftt schema_version no suportat: %r (suportat %r)"
                % (schema_version, FTT_SCHEMA_VERSION)
            )

        if DOCUMENT_NAME not in names:
            raise ValueError(".ftt sense %s" % DOCUMENT_NAME)
        try:
            document_json = json.loads(zf.read(DOCUMENT_NAME))
        except json.JSONDecodeError as exc:
            raise ValueError(".ftt amb document.json il·legible: %s" % exc)

        assets = {}
        for name in names:
            if name.startswith(ASSETS_PREFIX) and not name.endswith("/"):
                assets[name[len(ASSETS_PREFIX):]] = zf.read(name)

        preview = zf.read(PREVIEW_NAME) if PREVIEW_NAME in names else None

    return {
        "manifest": manifest,
        "document_json": document_json,
        "assets": assets,
        "preview": preview,
        "kind": manifest.get("kind", FTT_KIND_DOCUMENT),
    }
