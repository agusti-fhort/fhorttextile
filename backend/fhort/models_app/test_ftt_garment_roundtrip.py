"""SET-2/T9 · `garmentId` sobreviu el round-trip del `.ftt` — ALS TIPUS QUE L'HAN DE PORTAR.

El precedent ja provat és `test_ftt_peca_grup_roundtrip.py:46-54`: el `.ftt` no filtra claus per
tipus d'objecte i un `group kind:'sketch'` torna byte a byte. Això, però, és una prova feta
sobre UN tipus. Aquest tram ancora la peça a tres famílies distintes —la TAULA (`type:'table'` i
el `data_block` legacy), el CROQUIS (`sketch_svg`/`image`/`path`/`group`) i la COTA de POM
(`group` amb `pomId`)—, i el `data_block` és precisament l'únic tipus del qual la serialització
del frontend SÍ que treu una clau (`TechSheetEditor.jsx:554`, `{src, ...rest}`).

Per això aquí es prova cada família per separat, i les dues direccions que fan que el tram sigui
barat:
  · el camp hi és i torna intacte (desar → empaquetar → rellegir);
  · una fitxa SENSE el camp segueix carregant EXACTAMENT igual, sense guanyar cap clau — que és
    el que permet no migrar ni un document (`services_ftt_document.py:511-513`).

⚠️ AFIRMACIÓ D'ESTAT DATADA — 2026-08-10: avui cap document viu porta `garmentId` (el tram
l'escriu només als objectes NOUS) i cap dada real té cap peça 02 (comportes CHECK de T2).
Re-verificar el primer amb: `grep -c garmentId` sobre un `document.json` desat abans d'avui.
"""
import json

from django.test import SimpleTestCase

from fhort.models_app import services_ftt

# La peça mare, la mateixa sentinella que la BD (`models_app/models.py:781`) i que
# `frontend/src/utils/garmentFitxa.js`. Mai None: '' vol dir «el Model mateix».
MARE = ''


def _taula(**extra):
    """`type:'table'` — el que insereixen T0/T1a/T1b/T2/T3 i la personalitzada."""
    return {
        'id': 't1', 'type': 'table', 'layer': 'free', 'x': 10, 'y': 14,
        'kind': 'pom_grading', 'garmentId': '02',
        'columns': [{'key': 'ref', 'label': '', 'width': 22}],
        'rows': [['A', 'Chest width', '52.0']],
        'style': {'fontSize': 9, 'zebra': True},
        'snapshot': {'model_id': 163, 'seccio': '02.- KNICKERS'},
        **extra,
    }


def _data_block(**extra):
    """`data_block` — l'ÚNIC tipus amb una clau retirada a la serialització (`src`)."""
    return {
        'id': 'd1', 'type': 'data_block', 'kind': 'graded_table', 'layer': 'data',
        'size_fitting_id': 9, 'garmentId': '03', 'x': 10, 'y': 14, 'scale': 0.8,
        **extra,
    }


def _croquis(**extra):
    """Croquis vectorial inserit des del patró: `garmentId` conviu amb `piece_name`."""
    return {
        'id': 's1', 'type': 'path', 'layer': 'free', 'd': 'M0 0 L10 0 L10 10 Z',
        'piece_name': 'DAVANTER', 'pattern_file_id': 77, 'garmentId': '02',
        **extra,
    }


def _cota(**extra):
    """Cota VIVA de POM: la identitat sencera (pom|capa|instància) + la peça."""
    return {
        'id': 'c1', 'type': 'group', 'layer': 'free', 'x': 20, 'y': 20, 'rotation': 0,
        'pomId': 273, 'bmId': 1319, 'capa': 'folre', 'instancia': 'left',
        'garmentId': '02', 'pomCanonical': 'POM-020', 'viewSlot': 'front',
        'precedentGermana': False,
        'children': [
            {'id': 'k1', 'type': 'path', 'layer': 'free', 'd': 'M0 0 L30 0'},
            {'id': 'k2', 'type': 'text', 'layer': 'free', 'text': 'A', 'fontSize': 9},
        ],
        **extra,
    }


def _doc(*objectes):
    return {'pageFormat': 'A4L', 'pages': [{'id': 'p1', 'objects': list(objectes)}]}


class GarmentIdRoundtripTest(SimpleTestCase):

    def _roundtrip(self, doc):
        return services_ftt.unpack(services_ftt.pack(doc))['document_json']

    def _tornat(self, obj):
        return self._roundtrip(_doc(obj))['pages'][0]['objects'][0]

    # ── El camp hi és i torna intacte, família per família ───────────────────

    def test_la_taula_torna_byte_a_byte_amb_la_seva_peca(self):
        taula = _taula()
        self.assertEqual(self._tornat(taula), taula)

    def test_el_data_block_conserva_la_peca(self):
        """El tipus del qual la serialització del front SÍ treu una clau: la treu SOLS a `src`."""
        bloc = _data_block(src='data:image/png;base64,AAA')
        tornat = self._tornat(bloc)
        self.assertEqual(tornat['garmentId'], '03')
        self.assertEqual(tornat['size_fitting_id'], 9)

    def test_el_croquis_porta_la_peca_al_costat_del_nom_de_la_peca_de_patro(self):
        """Dos eixos que no s'han de confondre: `piece_name` és del PATRÓ, `garmentId` del MODEL."""
        tornat = self._tornat(_croquis())
        self.assertEqual(tornat['garmentId'], '02')
        self.assertEqual(tornat['piece_name'], 'DAVANTER')

    def test_la_cota_de_pom_conserva_la_identitat_SENCERA_i_la_peca(self):
        tornat = self._tornat(_cota())
        self.assertEqual(
            (tornat['pomId'], tornat['capa'], tornat['instancia'], tornat['garmentId']),
            (273, 'folre', 'left', '02'),
        )
        self.assertEqual([k['type'] for k in tornat['children']], ['path', 'text'])

    def test_la_peca_MARE_es_desa_i_torna_com_a_cadena_buida_mai_com_a_null(self):
        """'' no és «no ho sé»: és el Model mateix. Un `null` al document trencaria la
        convenció que comparteixen la BD i el front."""
        tornat = self._tornat(_taula(garmentId=MARE))
        self.assertIn('garmentId', tornat)
        self.assertEqual(tornat['garmentId'], MARE)
        self.assertIsNotNone(tornat['garmentId'])

    def test_els_quatre_tipus_alhora_a_la_mateixa_pagina(self):
        doc = _doc(_taula(), _data_block(), _croquis(), _cota())
        tornats = self._roundtrip(doc)['pages'][0]['objects']
        self.assertEqual([o['garmentId'] for o in tornats], ['02', '03', '02', '02'])

    # ── CONTROL: la fitxa que NO en porta no canvia gens ─────────────────────

    def test_CONTROL_una_fitxa_sense_el_camp_torna_IDENTICA_i_no_en_guanya_cap(self):
        """La raó per la qual aquest tram no necessita cap migració de documents: el que no
        declara la peça segueix sense declarar-la, i qui el llegeix ja sap que és la mare."""
        vell = {
            'id': 't9', 'type': 'table', 'layer': 'free', 'kind': 'pom_fitting',
            'columns': [], 'rows': [],
        }
        tornat = self._tornat(json.loads(json.dumps(vell)))
        self.assertEqual(tornat, vell)
        self.assertNotIn('garmentId', tornat)

    def test_CONTROL_una_cota_antiga_sense_eixos_segueix_sense_eixos(self):
        """El format vell d'una cota (nomes `pomId`) no ha de créixer al passar pel `.ftt`."""
        vella = {'id': 'c9', 'type': 'group', 'pomId': 273, 'children': []}
        tornat = self._tornat(vella)
        self.assertEqual(tornat, vella)
        for clau in ('garmentId', 'capa', 'instancia'):
            self.assertNotIn(clau, tornat)
