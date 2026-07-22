"""D3 · NORMALITZACIÓ A 0,1 mm (decisió Agus 2026-07-22).

Tot valor extret es normalitza a la precisió del domini (2 decimals en cm) a la PORTA
d'entrada del pipeline —abans de derivar—, i els deltes surten dels valors ja nets.

El perill que fixen aquests tests té dues cares oposades i s'han de sostenir alhora:

  · el SOROLL ha de morir  — `openpyxl` torna 16.749999999999999 per un 16,75 escrit, i
    aquest valor arribava viu fins a `detect_grading`, on dues restes de sorolls diferents
    donaven passos que no casaven i convertien una regla LINEAR neta en STEP;
  · el PAS de 0,25 ha de viure — arrodonir a 1 decimal «per netejar» destruiria mig
    domini: 0,25 cm és un pas real i freqüent en confecció.

Per això la regla és 2 decimals, mai 1, i s'aplica als VALORS, no als deltes a part.
"""
from django.test import SimpleTestCase

from fhort.pom.grading_utils import PRECISIO_CM, detect_grading, normalitza_cm


class NormalitzaCmTest(SimpleTestCase):

    def test_precisio_del_domini_es_2_decimals(self):
        self.assertEqual(PRECISIO_CM, 2)

    def test_soroll_de_float_desapareix(self):
        self.assertEqual(normalitza_cm(16.749999999999999), 16.75)
        self.assertEqual(normalitza_cm(12.600000000000001), 12.6)
        self.assertEqual(normalitza_cm(0.30000000000000004), 0.3)

    def test_coma_decimal_i_espais(self):
        """L'enganxat d'un Excel europeu i el JSON de l'IA donen cadenes."""
        self.assertEqual(normalitza_cm('16,75'), 16.75)
        self.assertEqual(normalitza_cm('  3,5 '), 3.5)
        self.assertEqual(normalitza_cm('58.5'), 58.5)

    def test_pas_de_025_es_preserva(self):
        """MAI 1 decimal: 0,25 cm és un pas real del domini, no soroll."""
        for v in (0.25, 12.35, 12.6, 0.75, 61.25):
            self.assertEqual(normalitza_cm(v), v)

    def test_no_numerics_i_booleans(self):
        for v in (None, '', '   ', 'n/a', '-', [], {}):
            self.assertIsNone(normalitza_cm(v))
        # Una casella marcada no és una mesura, encara que True sigui numèric en Python.
        self.assertIsNone(normalitza_cm(True))
        self.assertIsNone(normalitza_cm(False))

    def test_zero_es_un_valor_no_un_absent(self):
        self.assertEqual(normalitza_cm(0), 0.0)
        self.assertIsNotNone(normalitza_cm(0.0))


class DeltesNetsTest(SimpleTestCase):
    """Els deltes surten dels valors nets; no s'arrodoneixen «a part»."""

    RUN = ['XS', 'S', 'M', 'L']

    def test_delta_exacte_sense_cua_de_float(self):
        d = detect_grading({'XS': 12.10, 'S': 12.35, 'M': 12.60, 'L': 12.85},
                           self.RUN, 'S')
        self.assertEqual(d['logica'], 'LINEAR')
        self.assertEqual(d['increment'], 0.25)      # ni 0.25000000000000044 ni 0.3

    def test_soroll_dxlsx_no_converteix_un_LINEAR_en_STEP(self):
        """El cas que inflava el bucket `conflicte`: mateixa taula, escrita amb soroll."""
        net = detect_grading({'XS': 12.10, 'S': 12.35, 'M': 12.60, 'L': 12.85},
                             self.RUN, 'S')
        brut = detect_grading({'XS': 12.099999999999998, 'S': 12.350000000000001,
                               'M': 12.599999999999998, 'L': 12.850000000000001},
                              self.RUN, 'S')
        self.assertEqual(brut['logica'], net['logica'])
        self.assertEqual(brut['increment'], net['increment'])
        self.assertEqual(brut['valors_step'], net['valors_step'])

    def test_valors_com_a_cadena_amb_coma(self):
        d = detect_grading({'XS': '12,10', 'S': '12,35', 'M': '12,60', 'L': '12,85'},
                           self.RUN, 'S')
        self.assertEqual(d['logica'], 'LINEAR')
        self.assertEqual(d['increment'], 0.25)

    def test_un_STEP_de_debo_segueix_sent_STEP(self):
        """La normalització no aplana res: passos realment diferents es conserven."""
        d = detect_grading({'XS': 11.85, 'S': 12.35, 'M': 12.60, 'L': 13.60},
                           self.RUN, 'S')
        self.assertEqual(d['logica'], 'STEP')
        self.assertEqual(d['valors_step'],
                         {'XS': 0.5, 'M': 0.25, 'L': 1.0})


class PortaXlsxTest(SimpleTestCase):
    """`_num` (parse d'xlsx) ha de normalitzar, no només convertir."""

    def test_num_delega_a_normalitza_cm(self):
        from fhort.models_app.extraction_views import _num
        self.assertEqual(_num(16.749999999999999), 16.75)
        self.assertEqual(_num('16,75'), 16.75)
        self.assertEqual(_num(0.25), 0.25)
        self.assertIsNone(_num(True))
        self.assertIsNone(_num('x'))
