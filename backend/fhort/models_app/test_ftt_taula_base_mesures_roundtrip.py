"""La taula T0 (Mesures talla base) al .ftt: roundtrip + no-regressió de les que ja hi eren.

La T0 s'insereix amb el MATEIX patró que la T1a/T1b/T3: un `type:'table'` amb les columnes i
els valors ja resolts com a strings. Aquests tests fixen les dues cares d'aquesta decisió:

  1. El kind nou (`base_measures`) desa i reobre intacte, sense cap canvi d'esquema.
  2. La T1a (`pom_fitting`), la T1b (`pom_grading`) i la T3 (`fitting_history`) no canvien de
     comportament — ni al roundtrip ni al descongelat de plantilla. Si algú toca la
     serialització de taules pensant en la T0, això ha de petar.

I una tercera cosa, que és la raó de ser d'aquesta taula: **no hi ha CAP dada de graduació**.
El test ho comprova sobre les columnes, no sobre la intenció — un Δ o un break que s'hi
colessin per una còpia distreta de la T1a caurien aquí.

El sòl de 8pt i l'ajust a la pàgina són de RENDER (buildTableCellPrimitives / fitTableObj) i
no viatgen al fitxer: aquí es prova el que el .ftt promet, que és conservar el document.
"""
import json

from django.test import SimpleTestCase

from fhort.models_app import services_ftt
from fhort.models_app.services_ftt_document import PENDING_MARK, unfreeze_document


def _taula_base(**extra):
    """La T0 amb la forma REAL que insereix `insertTableBaseMeasures`.

    TRES columnes —nomenclatura, POM bilingüe i mida de la talla base— i cap més. La talla
    viatja DINS l'etiqueta de la columna `base` (les taules de la casa no tenen títol) i
    també al snapshot.
    """
    obj = {
        'id': 'tb', 'type': 'table', 'layer': 'free', 'x': 10, 'y': 14,
        'kind': 'base_measures', 'scale': 0.92, 'width': 92.0, 'height': 48.0,
        'columns': [
            {'key': 'ref', 'label': 'Nomenclatura', 'width': 22},
            {'key': 'pom', 'label': 'POM', 'width': 46},
            {'key': 'base', 'label': 'Base · M (cm)', 'width': 24},
        ],
        'rows': [
            ['PIT', {'text': 'Chest width', 'sub': 'Amplada de pit'}, '47.0'],
            ['A', {'text': 'Waist', 'sub': 'Cintura'}, '38.0'],
            ['X-CUSTOM', {'text': 'Mesura del tenant', 'sub': ''}, ''],
        ],
        'style': {'fontSize': 9, 'headerFill': '#111827', 'zebra': True},
        'snapshot': {'model_id': 163, 'talla_base': 'M',
                     'snapshot_at': '2026-07-30T10:00:00.000Z'},
    }
    obj.update(extra)
    return obj


def _taula(kind, **extra):
    """Taula snapshot GENÈRICA de les que ja hi eren (T1a/T1b/T3), per a la no-regressió."""
    obj = {
        'id': 't1', 'type': 'table', 'layer': 'free', 'x': 10, 'y': 14,
        'kind': kind, 'scale': 0.87, 'width': 240.0, 'height': 60.0,
        'columns': [
            {'key': 'ref', 'label': 'REF', 'width': 22},
            {'key': 'nom', 'label': 'POM', 'width': 46},
            {'key': 'base', 'label': 'Base (cm)', 'width': 18},
            {'key': 'rule', 'label': 'Regla/Δ', 'width': 18},
            {'key': 'break', 'label': 'Break', 'width': 18},
        ],
        'rows': [
            ['CH', {'text': 'Chest width', 'sub': 'Amplada de pit'}, '47.0', '+2.0', 'L'],
            ['WA', {'text': 'Waist', 'sub': 'Cintura'}, '38.0', '—', ''],
        ],
        'style': {'fontSize': 9, 'zebra': True},
        'snapshot': {'model_id': 163, 'snapshot_at': '2026-07-28T10:00:00.000Z'},
    }
    obj.update(extra)
    return obj


def _doc(*objectes):
    return {'pageFormat': 'A4L', 'pages': [{'id': 'p1', 'objects': list(objectes)}]}


class TaulaBaseMesuresRoundtripTest(SimpleTestCase):

    def _roundtrip(self, doc):
        return services_ftt.unpack(services_ftt.pack(doc))['document_json']

    # ── El kind nou ──────────────────────────────────────────────────────────
    def test_la_T0_desa_i_reobre_intacta(self):
        taula = _taula_base()
        tornada = self._roundtrip(_doc(taula))['pages'][0]['objects'][0]
        self.assertEqual(tornada, taula)

    def test_la_T0_te_EXACTAMENT_TRES_columnes(self):
        """La correcció d'Agus (30/07), fixada. La primera versió va sortir amb Tol± i
        Comentaris per mimetisme amb la T1a i eren justament les dues que sobraven: aquesta
        taula és POM + nomenclatura + mida, i res més."""
        tornada = self._roundtrip(_doc(_taula_base()))['pages'][0]['objects'][0]
        claus = [c['key'] for c in tornada['columns']]
        self.assertEqual(claus, ['ref', 'pom', 'base'])
        self.assertEqual(len(tornada['rows'][0]), 3)

    def test_la_T0_no_porta_CAP_columna_de_graduacio_ni_danotacio(self):
        """Si algú hi encasta un Δ, un break o la Tol± copiant de la T1a, cau aquí i no a la
        impremta."""
        claus = [c['key'] for c in
                 self._roundtrip(_doc(_taula_base()))['pages'][0]['objects'][0]['columns']]
        for prohibida in ('rule', 'break', 'delta', 'tol', 'coment', 'nova'):
            self.assertNotIn(prohibida, claus)

    def test_la_capcalera_de_la_base_diu_QUINA_talla_es(self):
        """La talla base viatja DINS l'etiqueta de la columna, no en un títol de taula: les
        taules d'aquesta casa no en tenen (buildTableCellPrimitives pinta capçalera + files).
        És l'única cosa del document que declara de quina talla parlen les xifres, i per això
        es fixa aquí i no només al snapshot."""
        tornada = self._roundtrip(_doc(_taula_base()))['pages'][0]['objects'][0]
        base = next(c for c in tornada['columns'] if c['key'] == 'base')
        self.assertIn('M', base['label'])
        self.assertEqual(base['label'], 'Base · M (cm)')
        # I el snapshot en guarda la versió en cru, per a la traça.
        self.assertEqual(tornada['snapshot']['talla_base'], 'M')

    def test_els_valors_congelats_i_la_cel_la_bilingue_sobreviuen(self):
        files = self._roundtrip(_doc(_taula_base()))['pages'][0]['objects'][0]['rows']
        self.assertEqual(files[0][1], {'text': 'Chest width', 'sub': 'Amplada de pit'})
        self.assertEqual(files[0][2], '47.0')            # string, no número: congelat
        self.assertEqual(files[2][2], '')                # POM materialitzat sense valor

    def test_la_nomenclatura_arriba_sencera_i_mai_buida(self):
        """Les tres branques de `nomenclaturaDePom` viatgen com a text pla: el .ftt no les
        pot re-resoldre (el document és una fotografia, no un binding viu)."""
        files = self._roundtrip(_doc(_taula_base()))['pages'][0]['objects'][0]['rows']
        self.assertEqual([f[0] for f in files], ['PIT', 'A', 'X-CUSTOM'])
        for f in files:
            self.assertNotEqual(f[0], '')

    def test_la_T0_es_desvincula_com_qualsevol_taula_snapshot(self):
        """No cal cap regla nova al descongelat: `_unfreeze_table` és per TIPUS, no per kind.
        Una plantilla no es pot endur les mesures del model d'origen."""
        doc2, _, report = unfreeze_document(json.loads(json.dumps(_doc(_taula_base()))), {})
        neta = doc2['pages'][0]['objects'][0]
        self.assertIsNone(neta['snapshot']['model_id'])
        self.assertTrue(neta[PENDING_MARK])
        self.assertEqual(report['taules_desvinculades'], 1)
        # L'estructura que el tècnic va compondre es queda: columnes i nombre de files.
        self.assertEqual(len(neta['columns']), 3)
        self.assertEqual(len(neta['rows']), 3)
        self.assertEqual(neta['rows'][0][0], '')       # cel·les buidades
        # ⚠️ L'etiqueta de la columna NO es buida en descongelar: `_unfreeze_table` neteja
        # VALORS, no estructura. Una plantilla treta d'aquest document arrossega la talla del
        # model d'origen a la capçalera fins que algú re-insereix la taula. És el mateix
        # comportament que ja tenen les columnes de talla de la T1b — es fixa perquè es vegi,
        # no perquè estigui bé.
        base = next(c for c in neta['columns'] if c['key'] == 'base')
        self.assertEqual(base['label'], 'Base · M (cm)')

    # ── No-regressió de les taules que ja hi eren ────────────────────────────
    def test_T1a_T1b_i_T3_no_canvien_al_roundtrip(self):
        t1a = _taula('pom_fitting', id='a')
        t1b = _taula('pom_grading', id='b')
        t3 = _taula('fitting_history', id='c')
        tornades = self._roundtrip(_doc(t1a, t1b, t3))['pages'][0]['objects']
        self.assertEqual(tornades[0], t1a)
        self.assertEqual(tornades[1], t1b)
        self.assertEqual(tornades[2], t3)

    def test_T1a_T1b_i_T3_es_descongelen_com_sempre(self):
        doc = _doc(_taula('pom_fitting', id='a'), _taula('pom_grading', id='b'),
                   _taula('fitting_history', id='c'))
        doc2, _, report = unfreeze_document(json.loads(json.dumps(doc)), {})
        for neta in doc2['pages'][0]['objects']:
            self.assertIsNone(neta['snapshot']['model_id'])
            self.assertTrue(neta[PENDING_MARK])
            self.assertEqual(neta['rows'][0][0], '')
        self.assertEqual(report['taules_desvinculades'], 3)

    def test_un_document_sense_T0_no_guanya_res(self):
        """El corpus de .ftt VELLS: cap kind nou, cap clau nova. Intactes per construcció."""
        doc = _doc(_taula('pom_fitting', id='a'), _taula('pom_grading', id='b'))
        tornat = self._roundtrip(doc)
        self.assertEqual(tornat, doc)
        kinds = {o.get('kind') for o in tornat['pages'][0]['objects']}
        self.assertNotIn('base_measures', kinds)
