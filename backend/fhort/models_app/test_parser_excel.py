"""Tests del parser determinista d'Excel — perfil "spec sheet" (QA-S8 · FIX C).

Convenció del repo: executat amb `python manage.py test fhort.models_app` (no hi ha pytest).

Aquests tests defensen DUES coses, i la segona importa més que la primera:

  1. Que el parser llegeixi bé les fitxes reals de Brownie (les DUES: el Tate de la sessió 33
     i la Rosalia de la 32, com a fixtures de debò, no com a sintètics).

  2. **Que abdiqui.** El contracte del wizard és "si el parser no en treu res, cau a la IA".
     Un parser més llest però equivocat ja no cau: substitueix la IA **en silenci** i escriu
     dades dolentes — pitjor que el defecte que arregla. Per això la meitat d'aquest fitxer
     són Excels deformats que han de fer ([], [], meta), i un test que ho comprova al caller:
     el camí IA continua sent el fallback.

Les fixtures:
  · `brownie_tate_spec_sheet.xlsx`    — els BYTES REALS del document de la ImportSession#33.
  · `brownie_rosalia_spec_sheet.xlsx` — el document real de la sessió 32, re-desat sense els
    sketches incrustats (8,6 MB → 14 KB). Cel·les, fulls i els 17 merges es conserven, i el
    parser en treu EXACTAMENT el mateix que de l'original (verificat abans de commitar).
"""
import io
import os
from unittest import mock

import openpyxl
from django.test import SimpleTestCase

from fhort.models_app.extraction_views import (
    _MIN_FILES_ENTESA,
    _avis_files_perdudes,
    _avis_fulls_multiples,
    _extraccio_via_excel,
    _parse_excel_poms,
)

FIXTURES = os.path.join(os.path.dirname(__file__), 'tests_fixtures')


def _fixture(nom):
    with open(os.path.join(FIXTURES, nom), 'rb') as fh:
        return fh.read()


def _xlsx(files, titol='FULL'):
    """Excel sintètic a partir d'una llista de files (tuples). Per als casos deformats."""
    return _xlsx_multi([(titol, files)])


def _xlsx_multi(fulls):
    """Llibre sintètic de diverses pestanyes. `fulls` = [(titol, [files])], en ordre."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for titol, files in fulls:
        ws = wb.create_sheet(title=titol)
        for fila in files:
            ws.append(list(fila))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


#: Una taula sana, en el format que el parser ha d'entendre. Les variants deformades de sota
#: la trenquen per un sol lloc cadascuna, per aïllar QUÈ fa abdicar el parser.
_SANA = [
    (None, 'SAMPLE SIZE', 'S'),
    (None, None, None),
    (None, 'CODE', 'DESCRIPTION', 'GRADING', 'S', 'SAMPLE', 'COMMENTS'),
    (None, None, 'ENGLISH', None, None, 'RECTI 1', None),
    (None, 'A', '1/2 chest width', None, 45, None, None),
    (None, 'D', '1/2 bottom width', None, 48, None, None),
    (None, 'E', 'Shoulder to shoulder', None, 36.5, None, None),
]


class ParserFitxaTateTest(SimpleTestCase):
    """La fitxa del Tate — els bytes reals de la sessió que QA va importar.

    Abans del FIX C el parser hi treia 0 POMs i 0 talles (cercava el codi a la columna A, que
    en aquest document és buida de dalt a baix) i la fitxa queia sencera a Opus.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.poms, cls.talles, cls.meta = _parse_excel_poms(_fixture('brownie_tate_spec_sheet.xlsx'))
        cls.codis = [p['codi_fitxa'] for p in cls.poms]

    def test_llegeix_les_26_files_del_document(self):
        self.assertEqual(len(self.poms), 26)

    def test_recupera_JJ_la_fila_que_la_IA_perdia_en_silenci(self):
        """`JJ` (1/2 Elbow width) és l'única fila SENSE valor a la talla base, i és exactament
        l'única que la IA va deixar caure (25 de 26), sense cap avís. Un POM sense mesura base
        és legítim: `BaseMeasurement.base_value_cm` és `null=True`."""
        self.assertIn('JJ', self.codis)
        jj = next(p for p in self.poms if p['codi_fitxa'] == 'JJ')
        self.assertEqual(jj['descripcio'], '1/2 Elbow width')
        self.assertEqual(jj['values'], {}, 'JJ no té valor a la talla base — i hi ha de ser igualment')

    def test_la_talla_es_la_del_SAMPLE_SIZE_no_tot_de_la_columna_E_endavant(self):
        """D1c·6. 'SAMPLE', 'ADJUSTMENTS' i 'COMMENTS' són columnes de servei: si s'agafés
        "de la columna E endavant", entrarien com tres talles fantasma."""
        self.assertEqual(self.talles, ['S'])
        self.assertEqual(self.meta['base_size'], 'S')

    def test_salta_les_files_de_seccio_i_no_hi_fa_break(self):
        """D1c·4. 'Bodice:' té el codi BUIT i text a la descripció. El parser antic hi feia
        `break` i es quedava amb zero files: la secció és la PRIMERA fila sota la capçalera."""
        self.assertNotIn('Bodice:', self.codis)
        self.assertEqual(self.codis[0], 'A', 'la primera fila de dades ve DESPRÉS de la secció')

    def test_talla_la_taula_al_banner_del_sketch(self):
        """D1c·5 i bandera 4. 'SKETCH WITH CODES' (dins el merge B39:H39) té "codi" però cap
        valor, i sota seu hi ha tres blocs fusionats fins a la fila 127."""
        self.assertNotIn('SKETCH WITH CODES', self.codis)
        self.assertEqual(self.codis[-1], 'I3', 'la darrera fila de dades és la I3 (f37)')

    def test_strip_de_codis_i_decimals(self):
        """D1c·7. Al document hi ha 'D ' (amb espai) i 17.75 (decimal)."""
        self.assertIn('D', self.codis)
        j = next(p for p in self.poms if p['codi_fitxa'] == 'J')
        self.assertEqual(j['values']['S'], 17.75)

    def test_llegeix_el_bloc_de_metadades(self):
        """El bonus barat de D1c: B2:B7. La via ràpida retornava `header: {}` fins i tot quan
        funcionava; la via Opus sí que l'omplia. Ara les dues parlen igual (bandera 3)."""
        self.assertEqual(self.meta['header'], {
            'brand': 'BROWNIE',
            'style_name': 'BLUSA: TATE',
            'color': 'CRUDO',
            'season': 'WINTER 2027',
        })

    def test_compta_les_files_del_document_per_al_fix_D(self):
        self.assertEqual(self.meta['n_files_amb_codi'], 26)
        self.assertIsNone(self.meta['motiu'])

    def test_els_valors_reals_de_la_fitxa(self):
        vals = {p['codi_fitxa']: p['values'].get('S') for p in self.poms}
        self.assertEqual(vals['A'], 45)
        self.assertEqual(vals['U2'], 5.5)    # la mesura que el guard many-to-one va salvar
        self.assertEqual(vals['U3'], 5)
        self.assertEqual(vals['I3'], 7.5)


class ParserFitxaRosaliaTest(SimpleTestCase):
    """La fitxa de la Rosalia (sessió 32) — DOS fulls, i el run sencer XXS·XS·S·M·L.

    És el cas que demostra que la porta d'abdicació no és només una xarxa de seguretat: també
    tria el full. 'PROTO COMMENTS' va PRIMER al llibre, però té la columna de la talla base
    (S) BUIDA de dalt a baix → no passa la porta → el parser continua i es queda amb
    'RECTI 1 COMMENTS', que és on hi ha les mesures de debò.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.poms, cls.talles, cls.meta = _parse_excel_poms(
            _fixture('brownie_rosalia_spec_sheet.xlsx'))
        cls.codis = [p['codi_fitxa'] for p in cls.poms]

    def test_tria_el_full_que_passa_la_porta_no_el_primer(self):
        self.assertEqual(self.meta['full'], 'RECTI 1 COMMENTS')

    def test_llegeix_el_run_sencer_i_la_base_es_la_S(self):
        """`base_size` NO és `sizes[0]`: el run comença a XXS però la talla base és la S (el
        `SAMPLE SIZE` del document). La via ràpida retornava XXS abans del FIX C."""
        self.assertEqual(self.talles, ['XXS', 'XS', 'S', 'M', 'L'])
        self.assertEqual(self.meta['base_size'], 'S')
        self.assertNotEqual(self.meta['base_size'], self.talles[0])

    def test_llegeix_les_11_files(self):
        self.assertEqual(len(self.poms), 11)
        self.assertEqual(self.codis[0], 'A')
        self.assertEqual(self.codis[-1], 'LZ1')

    def test_cada_pom_sap_de_quina_seccio_ve(self):
        """F4 · el text de la secció es LLEGIA i es llençava; ara viatja amb cada POM.

        Les quatre seccions reals d'aquest document, en ordre: 'Bodice:' (A, D, G1, F, FF),
        'CF Sequins piece:' (U, U1), 'Chest piece:' (P, P1) i 'Cord:' (LZ, LZ1).
        """
        per_seccio = {}
        for p in self.poms:
            per_seccio.setdefault(p['seccio'], []).append(p['codi_fitxa'])
        self.assertEqual(per_seccio, {
            'Bodice:': ['A', 'D', 'G1', 'F', 'FF'],
            'CF Sequins piece:': ['U', 'U1'],
            'Chest piece:': ['P', 'P1'],
            'Cord:': ['LZ', 'LZ1'],
        })

    def test_una_seccio_amb_valors_tambe_compta_com_a_seccio(self):
        """'Chest piece:' (f23) porta zeros a les columnes de talla. El discriminant és la
        DESCRIPCIÓ amb el codi buit, no l'absència de valors — si fos l'absència, P i P1
        s'haurien quedat penjats de la secció anterior."""
        p = next(p for p in self.poms if p['codi_fitxa'] == 'P')
        self.assertEqual(p['seccio'], 'Chest piece:')

    def test_la_fila_de_soroll_sense_text_no_canvia_la_seccio(self):
        """f22 té valors i CAP text: no és una secció i no ha de trencar la vigent."""
        u1 = next(p for p in self.poms if p['codi_fitxa'] == 'U1')
        self.assertEqual(u1['seccio'], 'CF Sequins piece:')

    def test_salta_les_tres_seccions_i_la_fila_de_zeros_sense_codi(self):
        """Aquesta fitxa té TRES seccions ('Bodice:', 'CF Sequins piece:', 'Cord:') i, a més,
        una fila sense codi PERÒ AMB VALORS (f22) — que tampoc no és un POM."""
        for soroll in ('Bodice:', 'CF Sequins piece:', 'Chest piece:', 'Cord:'):
            self.assertNotIn(soroll, self.codis)

    def test_el_header_hi_es(self):
        self.assertEqual(self.meta['header']['brand'], 'BROWNIE')
        self.assertEqual(self.meta['header']['style_name'], 'ROSALIA')


class PortaDAbdicacioTest(SimpleTestCase):
    """LA LLEI. El parser només retorna files quan pot DEMOSTRAR que ha entès la taula.

    En qualsevol altre cas retorna buit i el document cau a la IA, **com fins ara**. Cada test
    d'aquí trenca la taula sana per UN sol lloc.
    """

    def test_la_taula_sana_passa(self):
        """Control: si aquest test peta, els de sota no proven res."""
        poms, talles, meta = _parse_excel_poms(_xlsx(_SANA))
        self.assertEqual(len(poms), 3)
        self.assertEqual(talles, ['S'])
        self.assertIsNone(meta['motiu'])

    def test_abdica_sense_capcalera_ancorable(self):
        """Sense etiquetes de CODI i DESCRIPCIÓ no hi ha res a ancorar: podria ser qualsevol
        cosa. Un Excel de comandes, una factura, un full de mostres."""
        poms, talles, meta = _parse_excel_poms(_xlsx([
            (None, 'Article', 'Preu', 'Quantitat'),
            (None, 'A', 45, 3),
            (None, 'D', 48, 2),
            (None, 'E', 36.5, 1),
        ]))
        self.assertEqual((poms, talles), ([], []))
        self.assertIn('capçalera', meta['motiu'])

    def test_abdica_si_no_hi_ha_cap_columna_de_talla(self):
        deformat = [f for f in _SANA]
        deformat[2] = (None, 'CODE', 'DESCRIPTION', 'GRADING', 'SAMPLE', 'COMMENTS')
        poms, _, meta = _parse_excel_poms(_xlsx(deformat))
        self.assertEqual(poms, [])
        self.assertIn('cap columna de talla', meta['motiu'])

    def test_abdica_si_la_talla_base_declarada_no_te_columna(self):
        """El document diu que la mostra és una 'M' i a la taula no hi ha cap columna 'M'.
        Vol dir que hem entès malament la taula — i llavors val més no dir res."""
        deformat = [f for f in _SANA]
        deformat[0] = (None, 'SAMPLE SIZE', 'M')
        poms, _, meta = _parse_excel_poms(_xlsx(deformat))
        self.assertEqual(poms, [])
        self.assertIn("talla base 'M' no té columna", meta['motiu'])

    def test_abdica_amb_menys_de_tres_files_amb_valor_a_la_base(self):
        """La prova de comprensió: tres files coherents. Amb dues, el que hem trobat podria ser
        qualsevol bloc de text amb números al costat."""
        deformat = _SANA[:-1]   # queden 2 files de dades
        poms, _, meta = _parse_excel_poms(_xlsx(deformat))
        self.assertEqual(poms, [])
        self.assertIn(f'en calen {_MIN_FILES_ENTESA}', meta['motiu'])

    def test_abdica_amb_la_columna_de_la_base_buida(self):
        """El cas del full 'PROTO COMMENTS' de la Rosalia, aïllat: capçalera bona, columna de
        talla bona, i cap valor a sota."""
        deformat = [f for f in _SANA]
        for i in (4, 5, 6):
            fila = list(deformat[i])
            fila[4] = None
            deformat[i] = tuple(fila)
        poms, _, meta = _parse_excel_poms(_xlsx(deformat))
        self.assertEqual(poms, [])
        self.assertIn('0 fila(es) amb valor', meta['motiu'])

    def test_abdica_amb_un_excel_buit(self):
        poms, talles, meta = _parse_excel_poms(_xlsx([]))
        self.assertEqual((poms, talles), ([], []))
        self.assertIsNotNone(meta['motiu'])


class TallaBaseDelModelAmbEtiquetaDiferentTest(SimpleTestCase):
    """El cas LOS-SS27-0834 (DIAGNOSI_MULTIPECA_DALIA · Q5): el MODEL diu '00/01' i el
    DOCUMENT diu '0M-1M'. És la mateixa talla —`canonical_size_label` dona '0/1' per a totes
    dues— i el parser trobava la columna correctament.

    El que fallava era el que passava DESPRÉS: `base_label` es quedava amb l'etiqueta del
    model ('00/01') mentre que `values` s'indexa per l'etiqueta crua del document ('0M-1M').
    La porta de comprensió compara per igualtat literal de cadena, així que comptava 0 files
    amb valor a la base i el parser abdicava sobre un xlsx que havia entès sencer — i el
    document se n'anava a la IA, amb el cost i la pèrdua de fidelitat que això té.

    El document NO porta `SAMPLE SIZE`: és el cas en què mana el `base_hint` del model, que és
    exactament on neix l'asimetria.
    """

    #: Run NEWBORN escrit com l'escriu el document del client (mesos), sense SAMPLE SIZE.
    _MESOS = [
        (None, 'CODE', 'DESCRIPTION', '0M-1M', '1M-3M', '3M-6M', '6M-9M', '9M-12M'),
        (None, 'A', '1/2 chest width', 20.0, 21.0, 22.0, 23.0, 24.0),
        (None, 'D', '1/2 bottom width', 21.5, 22.5, 23.5, 24.5, 25.5),
        (None, 'E', 'Shoulder to shoulder', 18.0, 18.5, 19.0, 19.5, 20.0),
    ]

    def setUp(self):
        self.poms, self.talles, self.meta = _parse_excel_poms(
            _xlsx(self._MESOS),
            base_hint='00/01',
            run_hint=['00/01', '01/03', '03/06', '06/09', '09/12'],
        )

    def test_no_abdica(self):
        """El símptoma reportat: queia a la IA amb un xlsx perfectament llegible."""
        self.assertIsNone(self.meta['motiu'])
        self.assertEqual(len(self.poms), 3)

    def test_la_base_es_letiqueta_del_DOCUMENT_no_la_del_model(self):
        """`values` viu indexat per l'etiqueta del document; `base_size` ha de parlar el
        mateix idioma o el consumidor no hi pot indexar."""
        self.assertEqual(self.meta['base_size'], '0M-1M')

    def test_la_base_indexa_de_debo_els_valors_extrets(self):
        """La prova que tanca el cercle: amb l'etiqueta que retorna el parser es pot llegir
        el valor base de cada fila. Amb '00/01' no es podia llegir cap."""
        base = self.meta['base_size']
        self.assertEqual([p['values'][base] for p in self.poms], [20.0, 21.5, 18.0])

    def test_les_talles_del_document_es_conserven_crues(self):
        self.assertEqual(self.talles, ['0M-1M', '1M-3M', '3M-6M', '6M-9M', '9M-12M'])

    def test_no_inventa_seccio_quan_el_document_no_en_te(self):
        """F4 · una fitxa sense capçaleres de secció ha de donar `seccio=None`, no ''."""
        self.assertEqual([p['seccio'] for p in self.poms], [None, None, None])

    def test_el_document_segueix_manant_sobre_el_model(self):
        """Si el document declara `SAMPLE SIZE`, mana ell (contracte de D1c·6) — però
        l'etiqueta que en surt continua sent la de la COLUMNA, no la del bloc de metadades."""
        amb_sample = [(None, 'SAMPLE SIZE', '3M-6M'), (None, None, None)] + self._MESOS
        _, _, meta = _parse_excel_poms(
            _xlsx(amb_sample), base_hint='00/01',
            run_hint=['00/01', '01/03', '03/06', '06/09', '09/12'])
        self.assertEqual(meta['base_size'], '3M-6M')


def _peca(nom_seccio, codis, base='S'):
    """Un full amb capçalera, una secció i tres POMs — una 'peça' del llibre multi-full."""
    return ([(None, 'SAMPLE SIZE', base), (None, None, None),
             (None, 'CODE', 'DESCRIPTION', 'GRADING', base),
             (None, None, nom_seccio)]
            + [(None, c, f'mesura {c}', None, 30.0 + i) for i, c in enumerate(codis)])


class MultiFullInformeITriaTest(SimpleTestCase):
    """F5 · un llibre amb una peça per pestanya.

    Fins ara el parser retornava DINS del bucle al primer full que passava la porta i els
    següents no es miraven mai: els fulls 2..N es perdien sencers i sense cap avís de contingut
    (DIAGNOSI_MULTIPECA_DALIA, taula final §15). Ara s'avaluen tots i es pot triar.
    """

    LLIBRE = [
        ('DRESS', _peca('Bodice:', ['A', 'D', 'E'])),
        ('NOTES', [(None, 'Comentaris de fitting'), (None, 'res a veure')]),
        ('KNICKERS', _peca('Front:', ['K1', 'K2', 'K3'])),
    ]

    def setUp(self):
        self.bytes = _xlsx_multi(self.LLIBRE)

    def test_linforme_diu_QUE_hi_ha_a_cada_full(self):
        _, _, meta = _parse_excel_poms(self.bytes)
        self.assertEqual(meta['fulls'], [
            {'nom': 'DRESS', 'n_files_amb_codi': 3, 'passa_porta': True},
            {'nom': 'NOTES', 'n_files_amb_codi': 0, 'passa_porta': False},
            {'nom': 'KNICKERS', 'n_files_amb_codi': 3, 'passa_porta': True},
        ])

    def test_per_defecte_guanya_el_primer_que_passa(self):
        """El comportament de sempre: sense tria explícita, res no canvia."""
        poms, _, meta = _parse_excel_poms(self.bytes)
        self.assertEqual(meta['full'], 'DRESS')
        self.assertEqual([p['codi_fitxa'] for p in poms], ['A', 'D', 'E'])
        self.assertIsNone(meta['full_seleccionat_ignorat'])

    def test_el_full_triat_mana(self):
        poms, _, meta = _parse_excel_poms(self.bytes, full_seleccionat='KNICKERS')
        self.assertEqual(meta['full'], 'KNICKERS')
        self.assertEqual([p['codi_fitxa'] for p in poms], ['K1', 'K2', 'K3'])
        self.assertEqual([p['seccio'] for p in poms], ['Front:'] * 3)

    def test_un_full_triat_que_no_passa_la_porta_no_fa_abdicar_en_silenci(self):
        """Cau al default i ho DIU. Abdicar deixaria l'usuari sense import i sense saber per què."""
        poms, _, meta = _parse_excel_poms(self.bytes, full_seleccionat='NOTES')
        self.assertEqual(meta['full'], 'DRESS')
        self.assertEqual(meta['full_seleccionat_ignorat'], 'NOTES')
        self.assertEqual(len(poms), 3)

    def test_un_full_triat_inexistent_tampoc(self):
        _, _, meta = _parse_excel_poms(self.bytes, full_seleccionat='NO HI SOC')
        self.assertEqual(meta['full'], 'DRESS')
        self.assertEqual(meta['full_seleccionat_ignorat'], 'NO HI SOC')

    def test_lavis_diu_quants_fulls_amb_POMs_hi_ha_i_quin_sha_llegit(self):
        _, _, meta = _parse_excel_poms(self.bytes)
        avisos = _avis_fulls_multiples(meta['fulls'], meta['full'])
        self.assertEqual(len(avisos), 1)
        self.assertIn('2 fulls', avisos[0])
        self.assertIn("'DRESS' (3 POMs)", avisos[0])
        self.assertIn("'KNICKERS' (3 POMs)", avisos[0])
        self.assertIn("S'ha llegit 'DRESS'", avisos[0])

    def test_lavis_calla_amb_un_sol_full_amb_POMs(self):
        """La immensa majoria de fitxes. Un avís que surt sempre no el llegeix ningú."""
        _, _, meta = _parse_excel_poms(_xlsx(_SANA))
        self.assertEqual(_avis_fulls_multiples(meta['fulls'], meta['full']), [])


class MultiFullSobreLaFitxaRealTest(SimpleTestCase):
    """La Rosalia, que té dos fulls de debò: 'PROTO COMMENTS' (columna de la base BUIDA, no
    passa) i 'RECTI 1 COMMENTS' (les mesures). L'informe ha de dir exactament això."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bytes = _fixture('brownie_rosalia_spec_sheet.xlsx')

    def test_linforme_marca_el_full_que_no_passa(self):
        _, _, meta = _parse_excel_poms(self.bytes)
        self.assertEqual([(f['nom'], f['passa_porta']) for f in meta['fulls']],
                         [('PROTO COMMENTS', False), ('RECTI 1 COMMENTS', True)])

    def test_no_savisa_de_multi_full_perque_nomes_un_te_taula(self):
        _, _, meta = _parse_excel_poms(self.bytes)
        self.assertEqual(_avis_fulls_multiples(meta['fulls'], meta['full']), [])

    def test_triar_el_full_que_no_passa_cau_al_bo_i_ho_diu(self):
        poms, _, meta = _parse_excel_poms(self.bytes, full_seleccionat='PROTO COMMENTS')
        self.assertEqual(meta['full'], 'RECTI 1 COMMENTS')
        self.assertEqual(meta['full_seleccionat_ignorat'], 'PROTO COMMENTS')
        self.assertEqual(len(poms), 11)


class ElCamiIAContinuaSentElFallbackTest(SimpleTestCase):
    """El contracte del caller, no del parser: un Excel que el parser no entén ha d'anar a la IA.

    `_extraccio_via_excel` retorna `None` com a resposta → `import_session_extraccio_view`
    continua pel camí comú (Opus). Si això es trenqués, un document estrany no cauria a la IA:
    entraria mig llegit, o buit, i ningú no ho sabria.
    """

    class _Doc:
        """FieldFile mínim: el que `_extraccio_via_excel` en fa servir (open/read/close)."""

        def __init__(self, contingut):
            self._contingut = contingut
            self.name = 'estrany.xlsx'

        def open(self, mode='rb'):
            return self

        def read(self):
            return self._contingut

        def close(self):
            pass

    class _Sessio:
        """ImportSession mínima: prou per decidir via ràpida vs IA, sense BD."""

        model = None
        model_id = None

        def __init__(self, contingut, full_seleccionat=None):
            self.document = ElCamiIAContinuaSentElFallbackTest._Doc(contingut)
            self.resultat = {}
            self.poms_extrets = []
            self.avisos = []
            self.estat = 'TALLES'
            self.desada = False
            # F5 · el punter al full triat viu aquí (no hi ha camp nou a ImportSession).
            self.run_conciliat = ({'full_seleccionat': full_seleccionat}
                                  if full_seleccionat else {})

        def save(self, **kwargs):
            self.desada = True

    def test_un_excel_estrany_no_el_serveix_la_via_rapida(self):
        sessio = self._Sessio(_xlsx([
            (None, 'Article', 'Preu'),
            (None, 'A', 45),
        ]))

        resposta, meta = _extraccio_via_excel(sessio, api_key='no-cal')

        self.assertIsNone(resposta, 'el caller ha de caure a la IA, no rebre una resposta buida')
        self.assertIsNotNone(meta['motiu'])
        self.assertFalse(sessio.desada, 'abdicar no pot deixar rastre a la sessió')

    @mock.patch('fhort.models_app.extraction_views._match_rows')
    @mock.patch('fhort.models_app.extraction_views._revise_excel_poms_with_sonnet')
    def test_una_fitxa_bona_si_que_la_serveix_i_amb_header(self, revisio, match_rows):
        """El contrapunt: si el parser SÍ que l'entén, la via ràpida respon i Opus NO es crida.

        I la resposta ve completa — `header` i `base_size` inclosos (bandera 3). Abans del FIX C
        aquesta via retornava `header: {}` i `base_size = sizes[0]` fins i tot quan funcionava.
        """
        revisio.return_value = {'corrections': [], 'warnings': []}
        match_rows.side_effect = lambda files, customer: (
            [{'codi_fitxa': f['codi_fitxa'], 'values': f['values'], 'pom_master_id': None}
             for f in files],
            {'n_nomatch': 0, 'n_low': 0, 'n_many_to_one': 0},
        )
        sessio = self._Sessio(_fixture('brownie_tate_spec_sheet.xlsx'))

        resposta, meta = _extraccio_via_excel(sessio, api_key='no-cal')

        self.assertIsNotNone(resposta, 'la fitxa del Tate ja no ha de caure a la IA')
        self.assertEqual(len(resposta.data['poms_extrets']), 26)
        self.assertEqual(resposta.data['sizes'], ['S'])
        self.assertEqual(resposta.data['base_size'], 'S')
        self.assertEqual(resposta.data['header']['brand'], 'BROWNIE')
        self.assertEqual(resposta.data['header']['style_name'], 'BLUSA: TATE')
        # …i la sessió en desa la base, que és el que W5 necessita per reconciliar les talles.
        self.assertEqual(sessio.resultat['extraccio']['base_size'], 'S')
        self.assertEqual(sessio.estat, 'POMS')

    @mock.patch('fhort.models_app.extraction_views._match_rows')
    @mock.patch('fhort.models_app.extraction_views._revise_excel_poms_with_sonnet')
    def test_la_resposta_porta_linforme_de_fulls_i_respecta_la_tria(self, revisio, match_rows):
        """F5 · el cablejat sencer: `run_conciliat['full_seleccionat']` → parser → resposta.

        I l'avís de multi-full hi ha de ser: sense ell, els fulls no llegits desapareixen en
        silenci, que és exactament el forat que F5 tanca.
        """
        revisio.return_value = {'corrections': [], 'warnings': []}
        match_rows.side_effect = lambda files, customer: (
            [{'codi_fitxa': f['codi_fitxa'], 'values': f['values'], 'pom_master_id': None}
             for f in files],
            {'n_nomatch': 0, 'n_low': 0, 'n_many_to_one': 0},
        )
        llibre = _xlsx_multi(MultiFullInformeITriaTest.LLIBRE)

        sessio = self._Sessio(llibre, full_seleccionat='KNICKERS')
        resposta, _ = _extraccio_via_excel(sessio, api_key='no-cal')

        self.assertEqual(resposta.data['full'], 'KNICKERS')
        self.assertEqual([p['codi_fitxa'] for p in resposta.data['poms_extrets']],
                         ['K1', 'K2', 'K3'])
        self.assertEqual([f['nom'] for f in resposta.data['fulls']],
                         ['DRESS', 'NOTES', 'KNICKERS'])
        self.assertTrue(any('2 fulls' in a for a in resposta.data['avisos']),
                        "l'avís de multi-full ha d'arribar a la persona")
        # I la sessió també en desa l'informe (el wizard el pot rellegir sense re-extreure).
        self.assertEqual(sessio.resultat['extraccio']['full'], 'KNICKERS')


class SmokeMultipecaTest(SimpleTestCase):
    """SMOKE del sprint: F2 + F4 + F5 alhora sobre UNA fitxa.

    Fixture SINTÈTICA (`smoke_multipeca_2fulls_3seccions.xlsx`), generada per a aquest test i
    no un document de client: 2 fulls (DRESS/KNICKERS), 3 seccions al primer i el run NEWBORN
    escrit en mesos sense `SAMPLE SIZE`, que és la combinació del cas real LOS-SS27-0834.
    """

    BASE_HINT = '00/01'
    RUN_HINT = ['00/01', '01/03', '03/06']

    def _parse(self, **kw):
        return _parse_excel_poms(
            _fixture('smoke_multipeca_2fulls_3seccions.xlsx'),
            base_hint=self.BASE_HINT, run_hint=self.RUN_HINT, **kw)

    def test_F2_no_abdica_i_la_base_es_la_del_document(self):
        poms, talles, meta = self._parse()
        self.assertIsNone(meta['motiu'])
        self.assertEqual(meta['base_size'], '0M-1M')
        self.assertEqual(talles, ['0M-1M', '1M-3M', '3M-6M'])
        self.assertEqual([p['values'][meta['base_size']] for p in poms],
                         [20.0, 21.5, 18.0, 12.0, 6.0, 0.5, 75.0])

    def test_F4_les_tres_seccions_hi_son_i_en_ordre(self):
        poms, _, _ = self._parse()
        self.assertEqual(
            [(p['codi_fitxa'], p['seccio']) for p in poms],
            [('A', 'Bodice:'), ('D', 'Bodice:'), ('E', 'Bodice:'),
             ('S1', 'Sleeve:'), ('S2', 'Sleeve:'),
             ('LZ', 'Cord:'), ('LZ1', 'Cord:')])

    def test_F5_linforme_veu_els_dos_fulls_i_es_pot_triar_el_segon(self):
        _, _, meta = self._parse()
        self.assertEqual(meta['fulls'], [
            {'nom': 'DRESS', 'n_files_amb_codi': 7, 'passa_porta': True},
            {'nom': 'KNICKERS', 'n_files_amb_codi': 3, 'passa_porta': True},
        ])
        self.assertEqual(meta['full'], 'DRESS')          # default: el primer que passa

        poms2, _, meta2 = self._parse(full_seleccionat='KNICKERS')
        self.assertEqual(meta2['full'], 'KNICKERS')
        self.assertEqual([(p['codi_fitxa'], p['seccio']) for p in poms2],
                         [('K1', 'Front:'), ('K2', 'Front:'), ('K3', 'Front:')])

    def test_F5_lavis_de_multi_full_ho_diu_amb_noms_i_recomptes(self):
        _, _, meta = self._parse()
        avis = _avis_fulls_multiples(meta['fulls'], meta['full'])[0]
        self.assertIn('2 fulls', avis)
        self.assertIn("'DRESS' (7 POMs)", avis)
        self.assertIn("'KNICKERS' (3 POMs)", avis)

    def test_la_seccio_amb_valors_no_entra_com_a_POM(self):
        """'Cord:' porta zeros a les tres columnes i segueix sent una capçalera, no una fila."""
        poms, _, meta = self._parse()
        self.assertNotIn('Cord:', [p['codi_fitxa'] for p in poms])
        self.assertEqual(meta['n_files_amb_codi'], 7)


class AvisFilesPerdudesTest(SimpleTestCase):
    """FIX D — la pèrdua silenciosa. El document té 26 files i la IA en torna 25: s'ha de dir."""

    def test_avisa_quan_la_IA_en_perd_una(self):
        avisos = _avis_files_perdudes(26, 25)
        self.assertEqual(len(avisos), 1)
        self.assertIn('26', avisos[0])
        self.assertIn('25', avisos[0])
        self.assertIn('1 fila(es)', avisos[0])

    def test_calla_quan_no_se_nha_perdut_cap(self):
        self.assertEqual(_avis_files_perdudes(26, 26), [])

    def test_calla_quan_la_IA_en_troba_MES(self):
        """Només s'avisa en el sentit que fa mal. Que la IA en trobi més que el parser no és
        una pèrdua de dades: pot ser que hagi llegit un bloc que el parser talla."""
        self.assertEqual(_avis_files_perdudes(25, 26), [])

    def test_calla_quan_no_es_pot_comptar(self):
        """PDF, imatge, o un Excel del qual el parser no ha pogut ni ancorar la capçalera: no
        hi ha recompte de document, i un avís inventat seria pitjor que cap avís."""
        self.assertEqual(_avis_files_perdudes(0, 25), [])
