"""IA a l'import: cribratge NOMÉS quan cal (6) + log de cost de tota crida (7).

Decisió Agus 2026-07-22: «IA només quan el determinista no pot; un xlsx parsejable no ha de
costar ni un cèntim de token; tot usage es loggeja.»

El cribratge existeix per saber quants models porta el document i quin run de talles té.
Per a un .xlsx que el parser determinista entén, això ja ho sabem sense preguntar res: el
parser només retorna files quan pot DEMOSTRAR que ha entès la taula. Fins ara el fitxer
s'enviava a Opus SEMPRE, també quan el parser el resoldria sol al pas 2.

Cap test d'aquest fitxer fa cap crida de xarxa: el que es verifica és precisament QUANTES
se'n farien, i el client d'Anthropic es substitueix per un que peta si algú el crida.
"""
import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.extraction_utils import registra_us_ia
from fhort.models_app.models import AIUsage


class RegistraUsIaTest(TenantTestCase):
    """Commit 7 — tota crida deixa fila, també la que peta."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def test_llegeix_el_usage_del_SDK(self):
        usage = mock.Mock(input_tokens=1200, output_tokens=340,
                          cache_creation_input_tokens=0, cache_read_input_tokens=900)
        u = registra_us_ia(cami='extraccio', model_ia='claude-opus-4-7', usage=usage)
        self.assertEqual((u.input_tokens, u.output_tokens, u.cache_read_tokens),
                         (1200, 340, 900))
        self.assertTrue(u.ok)

    def test_llegeix_el_usage_com_a_dict(self):
        """`extraction_service` va per httpx cru: el usage arriba dins del JSON."""
        u = registra_us_ia(cami='extraccio', model_ia='claude-opus-4-5',
                           usage={'input_tokens': 50, 'output_tokens': 7})
        self.assertEqual((u.input_tokens, u.output_tokens), (50, 7))

    def test_una_crida_que_peta_tambe_es_registra(self):
        """També s'ha pagat: no registrar-la deixaria el cost real per sota del comptat."""
        u = registra_us_ia(cami='cribratge', model_ia='claude-opus-4-7',
                           ok=False, error='HTTP 529')
        self.assertFalse(u.ok)
        self.assertEqual(u.error, 'HTTP 529')

    def test_un_problema_comptant_tokens_no_tomba_res(self):
        """El registre és observabilitat: mai pot fer caure una extracció ja pagada."""
        with mock.patch.object(AIUsage.objects, 'create', side_effect=RuntimeError('BD morta')):
            self.assertIsNone(registra_us_ia(cami='revisio', model_ia='x'))

    def test_la_consulta_de_cost_es_una_sola_query(self):
        """L'objectiu del commit: «què ens ha costat aquest import?» amb una consulta."""
        from django.db.models import Sum
        for i in range(3):
            registra_us_ia(cami='extraccio', model_ia='claude-opus-4-7',
                           usage={'input_tokens': 100, 'output_tokens': 10})
        tot = AIUsage.objects.aggregate(i=Sum('input_tokens'), o=Sum('output_tokens'))
        self.assertEqual((tot['i'], tot['o']), (300, 30))


class RevisioSonnetOptInTest(SimpleTestCase):
    """Commit 6 — la revisió Sonnet passa a OPT-IN (per defecte apagada)."""

    def test_per_defecte_esta_apagada(self):
        from django.conf import settings
        self.assertFalse(getattr(settings, 'IMPORT_REVISIO_SONNET', False))

    def test_la_crida_esta_darrere_del_setting_al_lloc_on_es_fa(self):
        """El gate ha de ser AL punt de la crida, no en un `if` decoratiu més amunt.

        Es llegeix la font de `_extraccio_via_excel` perquè muntar-hi una sessió d'import
        sencera per veure una crida que NO es fa costaria molt més que el que assegura.
        """
        import inspect
        from fhort.models_app import extraction_views as ev
        src = inspect.getsource(ev._extraccio_via_excel)
        i_set = src.index('IMPORT_REVISIO_SONNET')
        i_call = src.index('_revise_excel_poms_with_sonnet(')
        self.assertLess(i_set, i_call, 'la crida a Sonnet no està darrere del setting')


class CribratgeDeterministaTest(SimpleTestCase):
    """Commit 6 — el routing de debò: `_cribratge_determinista` sobre un xlsx REAL.

    Res de mocks del parser aquí: es construeix un full de càlcul amb openpyxl i es comprova
    què decideix el routing. Un test que es mocqueja el parser i després l'invoca només
    provaria el mock.
    """

    RUN = ['XS', 'S', 'M', 'L']

    def _xlsx(self, files=4):
        import io
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(['SAMPLE SIZE', 'S'])
        ws.append([])
        ws.append(['CODE', 'DESCRIPTION'] + self.RUN)
        for i in range(files):
            base = 50 + i
            ws.append([f'D{i + 1}', f'Punt de mesura {i + 1}',
                       base - 1, base, base + 1, base + 2])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def _model(self):
        from types import SimpleNamespace
        return SimpleNamespace(size_run_model='XS·S·M·L', base_size_label='S')

    def test_un_xlsx_llegible_no_crida_la_IA(self):
        from fhort.models_app.extraction_views import _cribratge_determinista
        r = _cribratge_determinista('fitxa.xlsx', self._xlsx(), self._model())
        self.assertIsNotNone(r, 'un xlsx llegible NO hauria de caure a Opus')
        self.assertEqual(r['origen'], 'parser_determinista')
        self.assertEqual(r['num_models'], 1)
        self.assertEqual(r['run_talles_document'], self.RUN)
        self.assertGreaterEqual(r['n_files_amb_codi'], 3)

    def test_un_xlsx_que_el_parser_no_enten_cau_a_la_IA(self):
        """Porta d'abdicació: poques files coherents → val més pagar Opus que endevinar."""
        from fhort.models_app.extraction_views import _cribratge_determinista
        self.assertIsNone(
            _cribratge_determinista('fitxa.xlsx', self._xlsx(files=1), self._model()))

    def test_un_pdf_segueix_anant_a_la_IA(self):
        from fhort.models_app.extraction_views import _cribratge_determinista
        self.assertIsNone(
            _cribratge_determinista('fitxa.pdf', b'%PDF-1.4 ...', self._model()))

    def test_uns_bytes_corruptes_cauen_a_la_IA_sense_petar(self):
        """Que el parser peti compta com abdicar: davant del dubte, IA."""
        from fhort.models_app.extraction_views import _cribratge_determinista
        self.assertIsNone(
            _cribratge_determinista('fitxa.xlsx', b'aixo no es un xlsx', self._model()))
