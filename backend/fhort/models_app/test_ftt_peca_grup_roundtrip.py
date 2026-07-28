"""La peça de patró inserida com a GRUP sobreviu al roundtrip del .ftt.

Des de `b4cb0b7` una peça amb els rols separats s'insereix com a `group kind:'sketch'` amb
un fill per rol, en lloc d'un `path` únic. El requisit obert era si `piece_name` a l'ARREL
del grup és el lloc que els lectors del .ftt esperen — i això no es podia assumir: calia
desar i reobrir de debò.

Aquests tests fixen la resposta: el .ftt no filtra claus per tipus d'objecte, així que
`piece_name`/`pattern_file_id` viatgen igual en un grup que en un path, i el descongelat de
plantilla recorre l'arbre sencer (fills inclosos).

NO es prova aquí el despenjat de `pattern_file_id` d'un GRUP: avui no passa (vegeu el test
final, que documenta el forat amb el comportament REAL, no amb el desitjat).
"""
import json

from django.test import SimpleTestCase

from fhort.models_app import services_ftt
from fhort.models_app.services_ftt_document import unfreeze_document


def _peca_grup(**extra):
    """Peça amb dos rols: el que insereix la fitxa quan el croquis en porta més d'un."""
    return {
        'id': 'g1', 'type': 'group', 'kind': 'sketch', 'layer': 'free',
        'x': 20, 'y': 20, 'width': 110, 'height': 78,
        'piece_name': 'DAVANTER', 'pattern_file_id': 77,
        'children': [
            {'id': 'c1', 'type': 'path', 'd': 'M0 0 L10 0 L10 10 Z', 'stroke': '#000', 'layer': 'free'},
            {'id': 'c2', 'type': 'path', 'd': 'M2 2 L8 2', 'stroke': '#f00', 'layer': 'free'},
        ],
    }


def _doc(*objectes):
    return {'pageFormat': 'A4L', 'pages': [{'id': 'p1', 'objects': list(objectes)}]}


class PecaGrupRoundtripTest(SimpleTestCase):

    def _roundtrip(self, doc):
        return services_ftt.unpack(services_ftt.pack(doc))['document_json']

    def test_el_grup_sobreviu_identic_a_desar_i_reobrir(self):
        grup = _peca_grup()
        tornat = self._roundtrip(_doc(grup))['pages'][0]['objects'][0]
        # Byte a byte: el .ftt és JSON sense whitelist de claus per tipus.
        self.assertEqual(tornat, grup)

    def test_piece_name_a_larrel_del_grup_es_llegible_despres_del_roundtrip(self):
        tornat = self._roundtrip(_doc(_peca_grup()))['pages'][0]['objects'][0]
        self.assertEqual(tornat['piece_name'], 'DAVANTER')
        self.assertEqual(tornat['pattern_file_id'], 77)
        self.assertEqual(tornat['kind'], 'sketch')

    def test_els_rols_no_es_perden(self):
        fills = self._roundtrip(_doc(_peca_grup()))['pages'][0]['objects'][0]['children']
        self.assertEqual([c['stroke'] for c in fills], ['#000', '#f00'])

    def test_el_path_dun_sol_rol_segueix_igual(self):
        """La forma antiga no es toca: una peça d'un sol rol viatja com sempre."""
        path = {'id': 'p1', 'type': 'path', 'layer': 'free', 'd': 'M0 0 L1 1',
                'piece_name': 'ESQUENA', 'pattern_file_id': 77}
        tornat = self._roundtrip(_doc(path))['pages'][0]['objects'][0]
        self.assertEqual(tornat, path)

    def test_el_descongelat_recorre_els_fills_del_grup(self):
        """`_map_object_tree` entra als fills: un `path` amb pattern_file_id DINS el grup
        sí que es despenja. Serveix per afirmar que el recorregut no és pla."""
        grup = _peca_grup()
        grup['children'][0]['pattern_file_id'] = 77
        doc2, _, report = unfreeze_document(json.loads(json.dumps(_doc(grup))), {})
        fill = doc2['pages'][0]['objects'][0]['children'][0]
        self.assertIsNone(fill['pattern_file_id'])
        self.assertEqual(report['peces_despenjades'], 1)

    def test_FORAT_el_pattern_file_id_de_larrel_del_grup_NO_es_despenja(self):
        """Comportament REAL d'avui, no el desitjat.

        `_unfreeze_mapper` (services_ftt_document.py) casa `pattern_piece` o `path` amb
        `pattern_file_id`; un `group` no hi casa. Una fitxa amb una peça de rols separats
        convertida en PLANTILLA se'n va amb el punter al PatternFile del model d'origen.

        El fix és d'una condició a la serialització general, que aquest sprint tenia
        prohibit tocar. Si algú l'arregla, aquest test ha de PETAR: és la seva alarma.
        """
        doc2, _, report = unfreeze_document(json.loads(json.dumps(_doc(_peca_grup()))), {})
        arrel = doc2['pages'][0]['objects'][0]
        self.assertEqual(arrel['pattern_file_id'], 77)   # ← hauria de ser None
        self.assertEqual(report['peces_despenjades'], 0)
        # El que sí que es conserva (i és el que X3 preguntava):
        self.assertEqual(arrel['piece_name'], 'DAVANTER')
