"""F3 · observabilitat dels 500 — el traceback ha d'arribar a un fitxer, no només a journald.

Motiu: el 500 real del 27/07/2026 (`MultipleObjectsReturned` a l'import de POMs) es va haver de
reproduir a mà per saber què era. `django.request` a ERROR és el logger que Django fa servir per
a tot 500 no capturat, amb `exc_info`; el que faltava era un handler de fitxer enganxat-hi.

Es prova amb una VISTA DE PROVA que peta de debò —no cridant el logger a mà—, perquè el que ha
de quedar fixat és la canonada sencera: excepció no capturada → handler d'excepcions de Django →
logger `django.request` → fitxer amb el traceback.
"""
import datetime
import logging
import logging.config
import os
import tempfile

from django.conf import settings
from django.http import HttpResponse
from django.test import SimpleTestCase
from django.urls import path
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient


# ── urlconf de prova (només per a aquest mòdul) ────────────────────────────────────
def _vista_que_peta(request):
    raise ValueError('petada de prova F3')


def _vista_sana(request):
    return HttpResponse('ok')


urlpatterns = [
    path('peta/', _vista_que_peta),
    path('sana/', _vista_sana),
]


class ConfiguracioDelLogDErrorsTest(SimpleTestCase):
    """El que settings.py declara. Barat, i evita que algú desenganxi el handler sense adonar-se'n."""

    def test_django_request_esta_declarat_a_ERROR(self):
        conf = settings.LOGGING['loggers']['django.request']
        self.assertEqual(conf['level'], 'ERROR')
        self.assertFalse(conf['propagate'], 'propagate=True duplicaria cada 500 al log')

    def test_el_path_surt_de_lentorn_i_no_esta_cuit(self):
        """El default és dins de BASE_DIR; /var/log/fhort el posa PROD via FHORT_ERROR_LOG."""
        self.assertTrue(settings.ERROR_LOG_PATH.endswith('.log'))
        self.assertEqual(
            settings.ERROR_LOG_PATH,
            os.environ.get('FHORT_ERROR_LOG',
                           str(settings.BASE_DIR / 'logs' / 'django-error.log')))

    def test_el_handler_de_fitxer_hi_es_quan_el_directori_es_escrivible(self):
        """I NO hi és quan no ho és: un log que no es pot escriure no ha de petar l'arrencada."""
        if settings.ERROR_LOG_ACTIU:
            self.assertIn('error_file', settings.LOGGING['handlers'])
            self.assertIn('error_file', settings.LOGGING['loggers']['django.request']['handlers'])
        else:
            self.assertNotIn('error_file', settings.LOGGING['handlers'])
            self.assertEqual(settings.LOGGING['loggers']['django.request']['handlers'],
                             ['console'])


class ElTracebackArribaAlFitxerTest(TenantTestCase):
    """La canonada de debò: una vista que peta ha de deixar el traceback al fitxer.

    `TenantTestCase` i no `SimpleTestCase`: el middleware de django-tenants resol el tenant amb
    una consulta a `Domain` abans d'arribar a cap vista, i sense BD la petició peta ALLÀ. El
    primer intent d'aquest test va donar un 500 de `DatabaseOperationForbidden` — que, de fet,
    ja demostrava que la canonada de log funciona, però provava el middleware i no la vista.

    L'urlconf s'injecta amb `self.settings(...)` DINS del test i no amb `@override_settings` de
    classe: sobre `TenantTestCase` el decorador de classe no arriba a aplicar-se (verificat —
    `settings.ROOT_URLCONF` seguia sent `fhort.urls` i totes les peticions donaven 404).
    """

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.fitxer = os.path.join(self.dir.name, 'django-error.log')

        # La MATEIXA forma que settings.LOGGING, amb el path desviat al temporal. Es restaura
        # la configuració real al final perquè cap altre test hereti aquesta.
        logging.config.dictConfig({
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {'standard': {'format': '%(levelname)s %(name)s: %(message)s'}},
            'handlers': {
                'error_file': {
                    'class': 'logging.handlers.WatchedFileHandler',
                    'filename': self.fitxer,
                    'level': 'ERROR',
                    'formatter': 'standard',
                    'delay': True,
                },
            },
            'loggers': {
                'django.request': {'handlers': ['error_file'], 'level': 'ERROR',
                                   'propagate': False},
            },
        })
        self.addCleanup(logging.config.dictConfig, settings.LOGGING)

        # El client de test re-llança l'excepció per defecte; aquí volem el 500 de veritat.
        self.client.raise_request_exception = False

    def _log(self):
        if not os.path.exists(self.fitxer):
            return ''
        with open(self.fitxer, encoding='utf-8') as fh:
            return fh.read()

    def test_un_500_escriu_el_traceback_al_fitxer(self):
        with self.settings(ROOT_URLCONF=__name__, DEBUG=False):
            resp = self.client.get('/peta/')
        self.assertEqual(resp.status_code, 500)

        contingut = self._log()
        self.assertIn('ERROR django.request', contingut)
        self.assertIn('/peta/', contingut, 'ha de dir QUINA petició ha petat')
        self.assertIn('ValueError: petada de prova F3', contingut,
                      "el traceback (exc_info) és tot el motiu d'existir d'aquest handler")
        self.assertIn('Traceback (most recent call last)', contingut)

    def test_una_peticio_sana_no_escriu_res(self):
        """`delay=True`: sense cap ERROR, el fitxer ni tan sols s'arriba a crear."""
        with self.settings(ROOT_URLCONF=__name__, DEBUG=False):
            resp = self.client.get('/sana/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._log(), '')
