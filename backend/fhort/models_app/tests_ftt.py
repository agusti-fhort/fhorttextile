"""Tests del format .ftt (pack/unpack + mapatge v2). Funcions pures → SimpleTestCase, sense BD."""
import base64
import io
import json
import zipfile

from django.test import SimpleTestCase

from .services_ftt import (
    ASSETS_PREFIX,
    FTT_MAGIC,
    FTT_SCHEMA_VERSION,
    document_to_v2,
    pack,
    unpack,
    v2_to_document,
)


class FttPackUnpackTest(SimpleTestCase):
    def test_roundtrip_identical(self):
        doc = {
            "ftt": 1,
            "pageFormat": "A4L",
            "pages": [
                {"id": "p1", "objects": [{"type": "text", "text": "talla €/ñ", "x": 10}]},
                {"id": "p2", "objects": [{"type": "image", "src": "assets/logo.png"}]},
            ],
        }
        assets = {
            "logo.png": b"\x89PNG\r\n\x1a\n\x00\x01\x02binari\xff\xfe",
            "foto.jpg": bytes(range(256)),
        }
        preview = b"%PDF-fake-preview-bytes\x00\x01"

        blob = pack(doc, assets, preview)
        out = unpack(blob)

        self.assertEqual(out["document_json"], doc)
        self.assertEqual(out["assets"], assets)
        self.assertEqual(out["preview"], preview)
        self.assertEqual(out["manifest"]["magic"], FTT_MAGIC)
        self.assertEqual(out["manifest"]["schema_version"], FTT_SCHEMA_VERSION)
        # checksums presents per a cada peça
        self.assertIn("document.json", out["manifest"]["checksums"])
        self.assertIn("assets/logo.png", out["manifest"]["checksums"])

    def test_roundtrip_no_assets_no_preview(self):
        doc = {"ftt": 1, "pages": []}
        out = unpack(pack(doc))
        self.assertEqual(out["document_json"], doc)
        self.assertEqual(out["assets"], {})
        self.assertIsNone(out["preview"])

    def _zip_with_manifest(self, manifest):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("document.json", "{}")
        return buf.getvalue()

    def test_rejects_bad_magic(self):
        blob = self._zip_with_manifest({"magic": "XXX", "schema_version": 1})
        with self.assertRaises(ValueError):
            unpack(blob)

    def test_rejects_unknown_schema_version(self):
        blob = self._zip_with_manifest({"magic": "FTT", "schema_version": 999})
        with self.assertRaises(ValueError):
            unpack(blob)

    def test_rejects_non_zip(self):
        with self.assertRaises(ValueError):
            unpack(b"this is definitely not a zip file")

    def test_rejects_missing_document(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"magic": "FTT", "schema_version": 1}))
        with self.assertRaises(ValueError):
            unpack(buf.getvalue())


class FttV2MappingTest(SimpleTestCase):
    # 1x1 PNG transparent (base64) per simular un image.src inline.
    PNG_B64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9"
        "awAAAABJRU5ErkJggg=="
    )

    def _v2_sample(self):
        return {
            "version": 2,
            "pageFormat": "A4L",
            "pages": [
                {
                    "id": "p1",
                    "objects": [
                        {"type": "text", "text": "REF 123", "x": 10, "y": 5},
                        {"type": "image", "src": "data:image/png;base64," + self.PNG_B64,
                         "kind": "logo", "width": 40, "height": 40},
                    ],
                },
                {"id": "p2", "objects": [{"type": "line", "points": [0, 0, 10, 10]}]},
            ],
        }

    def test_v2_to_document_extracts_inline_binaries(self):
        v2 = self._v2_sample()
        doc, assets = v2_to_document(v2, metadata={"reference": "BRW-1"})
        # binari fora del JSON
        self.assertEqual(len(assets), 1)
        (asset_name,) = assets.keys()
        img = doc["pages"][0]["objects"][1]
        self.assertEqual(img["src"], ASSETS_PREFIX + asset_name)
        self.assertNotIn("data:", json.dumps(doc))
        # estructura preservada
        self.assertEqual(doc["ftt_schema"], 1)
        self.assertEqual(doc["metadata"], {"reference": "BRW-1"})
        self.assertEqual(doc["pageFormat"], "A4L")
        self.assertEqual([len(p["objects"]) for p in doc["pages"]], [2, 1])
        # camps no-src intactes
        self.assertEqual(img["kind"], "logo")
        self.assertEqual(doc["pages"][0]["objects"][0]["text"], "REF 123")

    def test_roundtrip_v2_to_ftt_to_v2_no_object_loss(self):
        v2 = self._v2_sample()
        doc, assets = v2_to_document(v2)
        out = unpack(pack(doc, assets))
        back = document_to_v2(out["document_json"])
        # mateix nombre de pàgines i d'objectes per pàgina
        self.assertEqual(len(back["pages"]), len(v2["pages"]))
        self.assertEqual(
            [len(p["objects"]) for p in back["pages"]],
            [len(p["objects"]) for p in v2["pages"]],
        )
        self.assertEqual(back["version"], 2)
        self.assertEqual(back["pageFormat"], "A4L")
        # el binari és recuperable des dels assets i és el PNG original
        recovered = out["assets"][list(out["assets"])[0]]
        self.assertEqual(recovered, base64.b64decode(self.PNG_B64))

    def test_document_to_v2_rewrites_asset_src(self):
        doc, assets = v2_to_document(self._v2_sample())
        back = document_to_v2(doc, asset_src=lambda n: "https://x/" + n)
        img = back["pages"][0]["objects"][1]
        self.assertTrue(img["src"].startswith("https://x/"))
