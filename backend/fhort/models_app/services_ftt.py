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
import hashlib
import io
import json
import zipfile

FTT_MAGIC = "FTT"
FTT_SCHEMA_VERSION = 1
FTT_APP_VERSION = "0.1.0"

MANIFEST_NAME = "manifest.json"
DOCUMENT_NAME = "document.json"
PREVIEW_NAME = "preview.png"
ASSETS_PREFIX = "assets/"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def pack(document_json, assets=None, preview=None, app_version=FTT_APP_VERSION):
    """Empaqueta un document lògic en un blob .ftt (bytes).

    - `document_json`: dict serialitzable a JSON.
    - `assets`: dict {nom -> bytes} de binaris; es desen sota `assets/<nom>`.
    - `preview`: bytes PNG opcionals; es desen com `preview.png`.

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


def unpack(blob):
    """Desempaqueta un blob .ftt i retorna un dict.

    Retorna {manifest, document_json, assets:{nom->bytes}, preview:bytes|None}.
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
    }
