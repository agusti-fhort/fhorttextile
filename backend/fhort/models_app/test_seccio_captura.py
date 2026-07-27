"""F3 — la SECCIÓ d'origen, dels dos camins d'extracció fins a la BaseMeasurement.

Convenció del repo: fitxer `test*.py` dins de l'app, executat amb
`python manage.py test fhort.models_app` (el projecte NO fa servir pytest).

CONTEXT DE LA "CAPTURA DEGRADADA". El brief demanava reproduir un cas confirmat en què
només 2 de 35 files es van endur la secció, i arreglar el camí que la perdia. El que s'ha
trobat en mesurar-ho a staging és que **cap dels dos camins d'extracció la perd**:

  · Parser determinista: 10/10 files amb secció sobre `dalia_losan_3seccions.xlsx`
    (`test_parser_excel.py` ja ho fixava des del fix del layout LOSAN).
  · Camí IA: el text que se li dóna (`_excel_to_text`) conté les tres files de rètol, el
    prompt demana `section` per fila i el mapatge de `extraction_views.py` la trasllada.
  · Les 24 ImportSession de staging tenen `seccio` a 0 files — TOTES són anteriors a la
    captura, o sigui que la sessió del 2/35 no és aquí i no es pot reproduir.

El que SÍ es perdia, i és el que aquest sprint arregla, és el tram final: la secció arribava
viva a `session.poms_extrets` i el confirm la llençava perquè `BaseMeasurement` no tenia on
desar-la. Aquests tests fixen la cadena sencera pels DOS camins.

⚠️ LÍMIT ESTRUCTURAL FIXAT EXPLÍCITAMENT (l'últim test). `unique_together ('model','pom')`
segueix manant: dues seccions que comparteixin un POM col·lapsen a una sola fila i la que
sobreviu es queda amb la secció de l'última. No és un defecte d'aquest codi — és la clau, i
tocar-la travessa 5 taules més (DIAGNOSI_MULTIPECA_DALIA §Q2, taula final §9). El test hi és
perquè el dia que algú canviï la clau, aquest comportament li salti a la cara en vermell en
comptes de descobrir-lo a producció.
"""
import pathlib

from django.test import SimpleTestCase
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.extraction_views import _excel_to_text, _match_rows, _parse_excel_poms
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.models import POMMaster

_FIXTURES = pathlib.Path(__file__).resolve().parent / 'tests_fixtures'
_SECCIONS = ['01.- DRESS'] * 5 + ['02.- KNICKERS'] * 3 + ['03.- HEADBAND'] * 2


def _fixture(nom):
    return (_FIXTURES / nom).read_bytes()


class ParserPortaLaSeccioTest(SimpleTestCase):
    """Camí determinista: 10/10, cap fila sense secció."""

    def setUp(self):
        self.poms, _, self.meta = _parse_excel_poms(
            _fixture('dalia_losan_3seccions.xlsx'),
            base_hint='0M-1M',
            run_hint=['0M-1M', '1M-3M', '3M-6M', '6M-9M', '9M-12M'],
        )

    def test_no_abdica(self):
        self.assertIsNone(self.meta['motiu'])

    def test_totes_les_files_porten_seccio(self):
        """El 'N/N' d'aquesta fixture. Cap fila muda."""
        amb = [p for p in self.poms if p.get('seccio')]
        self.assertEqual(len(amb), len(self.poms))
        self.assertEqual(len(self.poms), 10)

    def test_i_es_la_seccio_correcta(self):
        self.assertEqual([p['seccio'] for p in self.poms], _SECCIONS)


class TextPerALaIATest(SimpleTestCase):
    """El camí IA no pot capturar el que no se li ensenya: es fixa que els rètols hi són."""

    def test_les_tres_files_de_seccio_arriben_al_prompt(self):
        text = _excel_to_text(_fixture('dalia_losan_3seccions.xlsx'))
        for retol in ('01.- DRESS', '02.- KNICKERS', '03.- HEADBAND'):
            self.assertIn(retol, text)

    def test_i_hi_arriben_com_a_fila_propia_sense_codi_al_costat(self):
        """El prompt diu que els rètols NO porten client_code i que no s'han d'emetre com a
        fila de mesura. Si el rètol vingués enganxat a una fila de dades, aquella instrucció
        no es podria complir."""
        linies = _excel_to_text(_fixture('dalia_losan_3seccions.xlsx')).splitlines()
        retol = next(l for l in linies if l.startswith('01.- DRESS'))
        self.assertEqual(retol.replace('\t', '').strip(), '01.- DRESS')


class MatchRowsTraslladaLaSeccioTest(TenantTestCase):
    """`_match_rows` és la font ÚNICA de matching dels dos camins: la secció hi ha de
    travessar tal qual, tant si ve del parser com si ve del JSON de la IA.

    Cal BD: `find_pom_master` consulta el catàleg de POMMaster per cada fila.
    """

    PREFIX = 'SEC'

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'

    def test_la_seccio_sobreviu_al_matching(self):
        files = [
            {'codi_fitxa': 'B', 'descripcio': 'CHEST WIDTH', 'values': {},
             'tol_minus': None, 'tol_plus': None, 'seccio': '01.- DRESS'},
            {'codi_fitxa': 'C.4', 'descripcio': 'WAIST RELAXED', 'values': {},
             'tol_minus': None, 'tol_plus': None, 'seccio': '02.- KNICKERS'},
        ]
        rows, _ = _match_rows(files, None)
        self.assertEqual([r['seccio'] for r in rows], ['01.- DRESS', '02.- KNICKERS'])

    def test_una_fila_sense_seccio_no_n_inventa_cap(self):
        """La majoria de fitxes són d'una sola peça i no tenen rètols: absència no és error."""
        rows, _ = _match_rows(
            [{'codi_fitxa': 'B', 'descripcio': 'CHEST', 'values': {},
              'tol_minus': None, 'tol_plus': None, 'seccio': None}],
            None,
        )
        self.assertIsNone(rows[0]['seccio'])


class SeccioALaBaseMeasurementTest(TenantTestCase):
    """El tram que aquest sprint arregla: la secció es DESA, i el límit que no arregla."""

    PREFIX = 'SECBM'

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'

    def setUp(self):
        self.model = Model.objects.create(
            codi_intern='SEC-0001', nom_prenda='DALIA', codi_tenant='SEC',
            any=2026, temporada='SS', sequencial=1,
        )
        self.pom = POMMaster.objects.create(
            pom_global=None, codi_client='C', nom_client='WAIST WIDTH', actiu=True)

    def _escriu(self, pom, seccio, valor):
        """Imita EXACTAMENT el gest del confirm (extraction_views.py)."""
        BaseMeasurement.objects.update_or_create(
            model=self.model, pom=pom,
            defaults={'base_value_cm': valor, 'origen': 'IMPORTED',
                      'is_active': True, 'ordre': 0, 'seccio': seccio or ''},
        )

    def test_la_seccio_es_desa_i_es_llegeix(self):
        self._escriu(self.pom, '01.- DRESS', 24.0)
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom)
        self.assertEqual(bm.seccio, '01.- DRESS')

    def test_sense_seccio_la_columna_es_buida_mai_NULL(self):
        """667 files existents la porten buida; el contracte és '' i no None."""
        self._escriu(self.pom, None, 24.0)
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom)
        self.assertEqual(bm.seccio, '')

    def test_DUES_SECCIONS_AMB_EL_MATEIX_POM_COL·LAPSEN(self):
        """⚠️ EL LÍMIT ESTRUCTURAL, fixat a propòsit.

        `unique_together ('model','pom')` no s'ha tocat en aquest sprint. Si el document té
        WAIST WIDTH a DRESS i a KNICKERS, el confirm fa `update_or_create` dues vegades sobre
        la MATEIXA fila: en queda una, amb la secció de l'última i el valor de l'última.

        Això NO és el comportament desitjat per a multi-peça — és el que hi ha, i el camp
        `seccio` tot sol no ho pot arreglar perquè el bloqueig és la clau
        (DIAGNOSI_MULTIPECA_DALIA §Q2, taula final §9). Aquest test hi és perquè el dia que
        algú toqui la clau, ho vegi caure aquí i sàpiga que era conegut.
        """
        self._escriu(self.pom, '01.- DRESS', 24.0)
        self._escriu(self.pom, '02.- KNICKERS', 17.0)

        files = BaseMeasurement.objects.filter(model=self.model, pom=self.pom)
        self.assertEqual(files.count(), 1, 'la clau encara col·lapsa: si això falla, la clau ha canviat')
        self.assertEqual(files.first().seccio, '02.- KNICKERS')
        self.assertEqual(files.first().base_value_cm, 17.0)
