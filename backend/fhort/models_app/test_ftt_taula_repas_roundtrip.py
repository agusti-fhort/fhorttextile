"""La taula T3 (Repàs de fittings) al .ftt: roundtrip + no-regressió de T1a/T1b.

La T3 s'insereix amb el MATEIX patró que la T1b: un `type:'table'` amb les columnes i els
valors ja resolts com a strings. Aquests tests fixen les dues cares d'aquesta decisió:

  1. El kind nou (`fitting_history`) desa i reobre intacte, sense cap canvi d'esquema.
  2. La T1a (`pom_fitting`) i la T1b (`pom_grading`) no canvien de comportament — ni al
     roundtrip ni al descongelat de plantilla. Si algú toca la serialització de taules
     pensant en la T3, això ha de petar.

El sòl de 8pt i l'ajust a la pàgina són de RENDER (buildTableCellPrimitives / fitTableObj) i
no viatgen al fitxer: aquí es prova el que el .ftt promet, que és conservar el document.
"""
import json

from django.test import SimpleTestCase

from fhort.models_app import services_ftt
from fhort.models_app.services_ftt_document import PENDING_MARK, unfreeze_document


def _taula(kind, **extra):
    """Taula snapshot amb la forma real: cel·les string i una cel·la bilingüe {text, sub}."""
    obj = {
        'id': 't1', 'type': 'table', 'layer': 'free', 'x': 10, 'y': 14,
        'kind': kind, 'scale': 0.87, 'width': 240.0, 'height': 60.0,
        'columns': [
            {'key': 'ref', 'label': 'REF', 'width': 22},
            {'key': 'nom', 'label': 'POM', 'width': 46},
            {'key': '12', 'label': 'Fit @03/06', 'width': 20},
            {'key': 'etapa:checked@2026-06-10T09:00:00', 'label': 'Size check @10/06', 'width': 20},
            {'key': 'coment', 'label': 'Comentaris', 'width': 52},
        ],
        'rows': [
            ['CH', {'text': 'Chest width', 'sub': 'Amplada de pit'}, '47.0', '47.5', 'massa ample'],
            ['WA', {'text': 'Waist', 'sub': 'Cintura'}, '38.0', '–', ''],
        ],
        'style': {'fontSize': 9, 'zebra': True},
        'snapshot': {'model_id': 163, 'talla': 'S', 'n_esdeveniments': 2,
                     'snapshot_at': '2026-07-28T10:00:00.000Z'},
    }
    obj.update(extra)
    return obj


def _doc(*objectes):
    return {'pageFormat': 'A4L', 'pages': [{'id': 'p1', 'objects': list(objectes)}]}


class TaulaRepasRoundtripTest(SimpleTestCase):

    def _roundtrip(self, doc):
        return services_ftt.unpack(services_ftt.pack(doc))['document_json']

    # ── El kind nou ──────────────────────────────────────────────────────────
    def test_la_T3_desa_i_reobre_intacta(self):
        taula = _taula('fitting_history')
        tornada = self._roundtrip(_doc(taula))['pages'][0]['objects'][0]
        self.assertEqual(tornada, taula)

    def test_les_columnes_desdeveniment_conserven_la_clau_i_letiqueta(self):
        """Les claus d'etapa són strings amb ':' i '@' (les fabrica el backend del Repàs).
        Si el format del .ftt les toqués, la taula perdria l'aparellament columna↔valor."""
        tornada = self._roundtrip(_doc(_taula('fitting_history')))['pages'][0]['objects'][0]
        claus = [c['key'] for c in tornada['columns']]
        self.assertIn('etapa:checked@2026-06-10T09:00:00', claus)
        self.assertEqual([c['label'] for c in tornada['columns']][2:4],
                         ['Fit @03/06', 'Size check @10/06'])

    def test_la_cel_la_bilingue_i_els_valors_congelats_sobreviuen(self):
        files = self._roundtrip(_doc(_taula('fitting_history')))['pages'][0]['objects'][0]['rows']
        self.assertEqual(files[0][1], {'text': 'Chest width', 'sub': 'Amplada de pit'})
        self.assertEqual(files[0][2], '47.0')          # string, no número: congelat
        self.assertEqual(files[0][4], 'massa ample')   # últim comentari del POM
        self.assertEqual(files[1][3], '–')             # esdeveniment sense presa

    def test_la_T3_es_desvincula_com_qualsevol_taula_snapshot(self):
        """No cal cap regla nova al descongelat: `_unfreeze_table` és per TIPUS, no per kind.
        Una plantilla no es pot endur el repàs de fittings del model d'origen."""
        doc2, _, report = unfreeze_document(json.loads(json.dumps(_doc(_taula('fitting_history')))), {})
        neta = doc2['pages'][0]['objects'][0]
        self.assertIsNone(neta['snapshot']['model_id'])
        self.assertTrue(neta[PENDING_MARK])
        self.assertEqual(report['taules_desvinculades'], 1)
        # L'estructura que el tècnic va compondre es queda: columnes i nombre de files.
        self.assertEqual(len(neta['columns']), 5)
        self.assertEqual(len(neta['rows']), 2)
        self.assertEqual(neta['rows'][0][0], '')       # cel·les buidades

    # ── No-regressió de les taules que ja hi eren ────────────────────────────
    def test_T1a_i_T1b_no_canvien_al_roundtrip(self):
        t1a, t1b = _taula('pom_fitting', id='a'), _taula('pom_grading', id='b')
        tornades = self._roundtrip(_doc(t1a, t1b))['pages'][0]['objects']
        self.assertEqual(tornades[0], t1a)
        self.assertEqual(tornades[1], t1b)

    def test_T1a_i_T1b_es_descongelen_com_sempre(self):
        doc = _doc(_taula('pom_fitting', id='a'), _taula('pom_grading', id='b'))
        doc2, _, report = unfreeze_document(json.loads(json.dumps(doc)), {})
        for neta in doc2['pages'][0]['objects']:
            self.assertIsNone(neta['snapshot']['model_id'])
            self.assertTrue(neta[PENDING_MARK])
            self.assertEqual(neta['rows'][0][0], '')
        self.assertEqual(report['taules_desvinculades'], 2)

    def test_un_document_sense_T3_no_guanya_res(self):
        """Els .ftt vells: cap kind nou, cap clau nova. Intactes per construcció."""
        doc = _doc(_taula('pom_grading'))
        tornat = self._roundtrip(doc)
        self.assertEqual(tornat, doc)
        kinds = {o.get('kind') for o in tornat['pages'][0]['objects']}
        self.assertNotIn('fitting_history', kinds)
