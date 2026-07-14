"""Tests del format .ftt (pack/unpack + mapatge v2). Funcions pures → SimpleTestCase, sense BD."""
import base64
import io
import json
import os
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
from .services_ftt_document import PENDING_MARK, avis_de_copia, unfreeze_document


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


# ── El descongelat (BIB S0) ───────────────────────────────────────────────────────────────
# Contra .ftt REALS del disc: els dos que porten les dues bèsties que la funció es deixava.
#   · ftt_model_188_pom_fitting.ftt — taula `pom_fitting` amb 10 files de mesures del model 188
#     congelades a dins (POMs, valors base) i snapshot {model_id: 188, size_fitting_id: 78}.
#   · ftt_model_162_graded_table.ftt — `data_block kind:'graded_table'` amb size_fitting_id 52,
#     que NO és un valor congelat sinó un binding VIU: l'editor el re-llegeix en obrir.
# Són fitxers de producció de staging, copiats tal com estaven. El test val precisament perquè
# no els ha fabricat ningú per passar-lo.
FIXTURE_188 = 'ftt_model_188_pom_fitting.ftt'
FIXTURE_162 = 'ftt_model_162_graded_table.ftt'


def _carrega_fixture(nom):
    ruta = os.path.join(os.path.dirname(__file__), 'tests_fixtures', nom)
    with open(ruta, 'rb') as f:
        return unpack(f.read())


def _tots_els_objectes(document_json):
    """Recorregut recursiu de l'arbre (grups inclosos): el mateix que fa el descongelat."""
    def baixa(o):
        yield o
        for c in (o.get('children') or []):
            yield from baixa(c)
    for pagina in document_json.get('pages') or []:
        for arrel in pagina.get('objects') or []:
            yield from baixa(arrel)


def _claus_amb_valor(node, sufix):
    """Totes les claus acabades en `sufix` amb valor NO nul, a qualsevol fondària del JSON."""
    trobades = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k.endswith(sufix) and v is not None:
                trobades.append((k, v))
            trobades.extend(_claus_amb_valor(v, sufix))
    elif isinstance(node, list):
        for item in node:
            trobades.extend(_claus_amb_valor(item, sufix))
    return trobades


class FttUnfreezeTest(SimpleTestCase):
    """El descongelat ha de deixar el document sense res del host, i amb tot el que és seu."""

    # ── El blindatge: cap referència, cap valor ───────────────────────────────────────────
    def test_cap_referencia_de_host_sobreviu(self):
        """Escaneig recursiu: cap clau `*_id` amb valor, en cap dels dos .ftt reals.

        Aquest és el test que blinda T1c. No comprova una llista de tipus coneguts: escombra
        el JSON SENCER. El dia que algú afegeixi un tipus de canvas amb una referència nova al
        host i no la posi a HOST_REF_KEYS, aquest test peta — que és exactament el que ha de
        passar, perquè el forat d'aquesta sessió va néixer així (les taules snapshot es van
        afegir després de `unfreeze_document` i ningú va tornar a passar per aquí).
        """
        for nom in (FIXTURE_188, FIXTURE_162):
            with self.subTest(fixture=nom):
                paquet = _carrega_fixture(nom)
                net, _, _ = unfreeze_document(paquet['document_json'], paquet.get('assets') or {})
                vius = _claus_amb_valor(net, '_id')
                self.assertEqual(vius, [], f'referències de host vives a {nom}: {vius}')

    def test_cap_valor_del_model_origen_sobreviu(self):
        """Les mesures del model 188 no poden viatjar a cap altre model."""
        paquet = _carrega_fixture(FIXTURE_188)
        net, _, _ = unfreeze_document(paquet['document_json'], paquet.get('assets') or {})
        cru = json.dumps(net, ensure_ascii=False)
        for valor_del_188 in ('Chest width', 'Ample de pit', '1/2 bottom width relaxed'):
            self.assertNotIn(valor_del_188, cru)
        # El '37' (ample de pit base) tampoc, i es comprova a la cel·la, no a tot el JSON:
        # un '37' solt podria ser una coordenada legítima.
        taula = next(o for o in _tots_els_objectes(net) if o.get('type') == 'table')
        cel_les = [c for fila in taula['rows'] for c in fila]
        for c in cel_les:
            self.assertIn(c, ('', {'text': '', 'sub': ''}), f'cel·la amb valor de l\'origen: {c!r}')

    # ── L'altra meitat: l'estructura es conserva ──────────────────────────────────────────
    def test_la_graella_es_conserva_sencera(self):
        """Es buiden els VALORS, no la taula: la graella és del tècnic, no del model."""
        paquet = _carrega_fixture(FIXTURE_188)
        original = next(o for o in _tots_els_objectes(paquet['document_json'])
                        if o.get('type') == 'table')
        net, _, report = unfreeze_document(paquet['document_json'], paquet.get('assets') or {})
        taula = next(o for o in _tots_els_objectes(net) if o.get('type') == 'table')

        self.assertEqual(taula['columns'], original['columns'])          # capçaleres i amples
        self.assertEqual(len(taula['rows']), len(original['rows']))      # 10 files
        self.assertEqual(len(taula['rows'][0]), len(original['rows'][0]))  # 8 columnes
        for clau in ('x', 'y', 'width', 'height', 'kind'):               # geometria i mena
            self.assertEqual(taula.get(clau), original.get(clau))
        self.assertTrue(taula[PENDING_MARK])
        self.assertIsNone(taula['snapshot']['model_id'])
        self.assertIsNone(taula['snapshot']['size_fitting_id'])
        self.assertEqual(report['taules_desvinculades'], 1)

    def test_la_forma_de_la_cel_la_es_respecta(self):
        """Una cel·la bilingüe {text, sub} es buida SENSE tornar-se plana."""
        paquet = _carrega_fixture(FIXTURE_188)
        net, _, _ = unfreeze_document(paquet['document_json'], paquet.get('assets') or {})
        taula = next(o for o in _tots_els_objectes(net) if o.get('type') == 'table')
        # La columna POM del .ftt real porta cel·les {text, sub}: han de seguir sent dict.
        self.assertEqual(taula['rows'][0][1], {'text': '', 'sub': ''})
        self.assertEqual(taula['rows'][0][0], '')          # i les planes, planes

    def test_graded_table_perd_el_binding_viu(self):
        """L'únic objecte que RE-LLEGEIX del host en obrir: amb l'id vell serviria la niada
        d'un altre model sense dir-ho."""
        paquet = _carrega_fixture(FIXTURE_162)
        net, _, report = unfreeze_document(paquet['document_json'], paquet.get('assets') or {})
        bloc = next(o for o in _tots_els_objectes(net)
                    if o.get('type') == 'data_block' and o.get('kind') == 'graded_table')
        self.assertIsNone(bloc['size_fitting_id'])
        self.assertTrue(bloc[PENDING_MARK])
        self.assertEqual(report['taules_desvinculades'], 1)

    def test_estructura_pura_intacta(self):
        """El que NO és del host viatja sencer: dibuix, text, geometria — i els grups."""
        doc = {
            'ftt_schema': 1, 'metadata': {}, 'pageFormat': 'A4L',
            'pages': [{'id': 'p1', 'objects': [
                {'id': 'g1', 'type': 'group', 'x': 5, 'y': 5, 'children': [
                    {'id': 's1', 'type': 'sketch_svg', 'svg': '<svg><path d="M0,0 L9,9"/></svg>',
                     'x': 1, 'y': 2, 'width': 30, 'height': 40},
                    {'id': 't1', 'type': 'text', 'text': 'Nota del tècnic', 'x': 3, 'y': 4},
                ]},
                {'id': 'p2', 'type': 'path', 'paths': [{'d': 'M1,1 L2,2'}], 'x': 0, 'y': 0},
            ]}],
        }
        net, _, report = unfreeze_document(doc, {})
        objectes = {o['id']: o for o in _tots_els_objectes(net)}
        self.assertEqual(objectes['s1']['svg'], '<svg><path d="M0,0 L9,9"/></svg>')
        self.assertEqual(objectes['t1']['text'], 'Nota del tècnic')
        self.assertEqual(objectes['p2']['paths'], [{'d': 'M1,1 L2,2'}])
        self.assertEqual(objectes['g1']['x'], 5)
        self.assertEqual(report['taules_desvinculades'], 0)

    def test_pattern_piece_perd_l_id_pero_conserva_el_dibuix(self):
        """F1 (576fd88): el tipus més nou del canvas, i el primer que va néixer amb una
        referència de host. El dibuix ÉS el sketch que la biblioteca vol; l'id, no."""
        doc = {
            'ftt_schema': 1, 'metadata': {}, 'pageFormat': 'A4L',
            'pages': [{'id': 'p1', 'objects': [
                {'id': 'pp1', 'type': 'pattern_piece', 'src': 'assets/abc123.svg',
                 'piece_name': 'TATE_FRONT', 'pattern_file_id': 8, 'x': 10, 'y': 10,
                 'width': 110, 'height': 78, 'caption': True},
            ]}],
        }
        net, _, report = unfreeze_document(doc, {})
        peca = next(_tots_els_objectes(net))
        self.assertIsNone(peca['pattern_file_id'])
        self.assertEqual(peca['src'], 'assets/abc123.svg')   # el dibuix es queda
        self.assertEqual(peca['piece_name'], 'TATE_FRONT')
        self.assertNotIn(PENDING_MARK, peca)                 # no falta res: no hi ha feina pendent
        self.assertEqual(report['peces_despenjades'], 1)

    # ── L'invariant del PDF (T3), tan lluny com Python el pot mirar ───────────────────────
    def test_pendent_vincle_nomes_en_tipus_que_el_pdf_sap_pintar(self):
        """La marca només pot caure on el renderer la sap pintar.

        Els dos switches del canvas (ObjectNode i addObjectToLayer) pinten el rètol «per
        vincular» per a `table` i `data_block`. Si el descongelat marqués un tipus que no
        surt en aquesta llista, el PDF no en pintaria res —el forat mut que T3 acaba de
        tapar— i ningú se n'assabentaria fins a la impressora.
        """
        SAP_PINTAR_HO = {'table', 'data_block'}
        for nom in (FIXTURE_188, FIXTURE_162):
            with self.subTest(fixture=nom):
                paquet = _carrega_fixture(nom)
                net, _, _ = unfreeze_document(paquet['document_json'], paquet.get('assets') or {})
                marcats = {o['type'] for o in _tots_els_objectes(net) if o.get(PENDING_MARK)}
                self.assertTrue(marcats <= SAP_PINTAR_HO, f'tipus marcat sense render: {marcats}')

    def test_el_sistema_no_re_vincula_mai_sol(self):
        """La taula queda buida i marcada, no re-omplerta amb dades del host nou. Re-vincular
        és un clic del tècnic (decisió Agus: res en silenci)."""
        paquet = _carrega_fixture(FIXTURE_188)
        net, _, _ = unfreeze_document(paquet['document_json'], paquet.get('assets') or {})
        taula = next(o for o in _tots_els_objectes(net) if o.get('type') == 'table')
        self.assertTrue(taula[PENDING_MARK])
        self.assertTrue(all(c in ('', {'text': '', 'sub': ''}) for fila in taula['rows'] for c in fila))

    def test_l_avis_ho_diu_a_la_persona(self):
        """Res en silenci: la resposta de la còpia ha de dir que hi ha taules per vincular."""
        paquet = _carrega_fixture(FIXTURE_188)
        _, _, report = unfreeze_document(paquet['document_json'], paquet.get('assets') or {})
        avis = avis_de_copia(report)
        self.assertIn('PER VINCULAR', avis)
        self.assertIsNone(avis_de_copia(None))   # no és un .ftt: res a dir
