"""Tests del format .ftt (pack/unpack). Funcions pures → SimpleTestCase, sense BD."""
import io
import json
import zipfile

from django.test import SimpleTestCase

from .services_ftt import (
    FTT_MAGIC,
    FTT_SCHEMA_VERSION,
    pack,
    unpack,
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
