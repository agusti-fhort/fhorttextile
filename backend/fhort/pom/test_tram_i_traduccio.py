"""
TRAM ⓘ — els guards del tram de traducció.

No es prova que DeepL tradueixi bé: es prova el que la casa promet i el que costa diners si es
trenca —que la cache s'usi, que una API caiguda no tregui un vermell a la pantalla, i que una
pantalla sencera de POMs sigui UNA crida i no tretze—. El proveïdor és un mock amb COMPTADOR:
un test que digui «la cache funciona» sense comptar crides no prova res.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.pom import translation_service as ts
from fhort.pom.models import POMMaster, TranslationCache


class MockProveidor:
    """Compta les crides i tradueix posant un prefix. Substitueix `_crida_proveidor`, que és
    l'única porta cap enfora del servei."""

    def __init__(self, resposta=True):
        self.crides = 0
        self.textos = []
        self.resposta = resposta

    def __call__(self, texts, lang):
        self.crides += 1
        self.textos.append(list(texts))
        if not self.resposta:
            return None
        return [f'{lang.upper()}:{t}' for t in texts]


class TramTraduccioTest(TenantTestCase):

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
        self.original = ts._crida_proveidor
        self.user = get_user_model().objects.create(username='qa_tram_i')
        self.api = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        self.api.force_authenticate(user=self.user)
        self.poms = [
            POMMaster.objects.create(codi_client=f'T{i}', nom_client=f'Chest width {i}')
            for i in range(3)
        ]

    def tearDown(self):
        ts._crida_proveidor = self.original

    def _mock(self, resposta=True):
        m = MockProveidor(resposta)
        ts._crida_proveidor = m
        return m

    def _get(self, ids, lang='es'):
        return self.api.get(
            '/api/v1/translate/pom/',
            {'pom_ids': ','.join(str(p.id) for p in ids), 'lang': lang},
        )

    # ── GUARD 1 · la cache ────────────────────────────────────────────────────────────────
    def test_segona_peticio_no_toca_lapi(self):
        m = self._mock()
        r1 = self._get(self.poms[:1])
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(m.crides, 1)
        self.assertEqual(r1.data['items'][0]['font'], 'api')
        self.assertEqual(r1.data['items'][0]['text'], 'ES:Chest width 0')

        r2 = self._get(self.poms[:1])
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(m.crides, 1, 'la 2a petició del mateix (pom, lang) ha tocat l\'API')
        self.assertEqual(r2.data['items'][0]['font'], 'cache')
        self.assertEqual(r2.data['items'][0]['text'], 'ES:Chest width 0')

    def test_idioma_diferent_es_una_entrada_diferent(self):
        m = self._mock()
        self._get(self.poms[:1], lang='es')
        self._get(self.poms[:1], lang='fr')
        self.assertEqual(m.crides, 2)
        self.assertEqual(
            TranslationCache.objects.filter(source_ref=ts.ref_de_pom(self.poms[0].id)).count(), 2)

    def test_reformular_el_nom_canonic_refresca_la_fila_sense_canviar_la_clau(self):
        self._mock()
        self._get(self.poms[:1])
        pom = self.poms[0]
        pom.nom_client = 'Chest girth'
        pom.save(update_fields=['nom_client'])

        r = self._get([pom])
        self.assertEqual(r.data['items'][0]['text'], 'ES:Chest girth')
        self.assertEqual(
            TranslationCache.objects.filter(source_ref=ts.ref_de_pom(pom.id), lang='es').count(), 1,
            'el mateix POM ha de seguir tenint UNA entrada per idioma',
        )

    # ── GUARD 2 · el fallback ─────────────────────────────────────────────────────────────
    def test_api_caiguda_torna_200_amb_langles(self):
        m = self._mock(resposta=False)
        r = self._get(self.poms[:1])
        self.assertEqual(r.status_code, 200, 'una traducció que falla no pot ser un 500')
        self.assertEqual(m.crides, 1)
        self.assertEqual(r.data['items'][0]['text'], 'Chest width 0')
        self.assertEqual(r.data['items'][0]['font'], 'fallback')

    def test_el_fallback_no_es_memoritza(self):
        self._mock(resposta=False)
        self._get(self.poms[:1])
        self.assertFalse(
            TranslationCache.objects.filter(lang='es').exists(),
            "l'anglès de fallback desat com a traducció deixaria la ⓘ muda per sempre",
        )
        # …i quan el proveïdor torna, la ⓘ parla sense que ningú hagi de buidar res.
        m = self._mock()
        r = self._get(self.poms[:1])
        self.assertEqual(r.data['items'][0]['font'], 'api')
        self.assertEqual(m.crides, 1)

    def test_sense_proveidor_configurat_tampoc_peta(self):
        # Sense mock: `TRANSLATE_PROVIDER=deepl` i `DEEPL_API_KEY` buida (el cas d'avui).
        r = self._get(self.poms[:1])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['items'][0]['text'], 'Chest width 0')
        self.assertEqual(r.data['items'][0]['font'], 'fallback')

    # ── GUARD 3 · el lot ──────────────────────────────────────────────────────────────────
    def test_n_poms_una_sola_crida(self):
        m = self._mock()
        r = self._get(self.poms)
        self.assertEqual(len(r.data['items']), 3)
        self.assertEqual(m.crides, 1, 'tres POMs no cachejats han de ser UNA crida')
        self.assertEqual(len(m.textos[0]), 3)

    def test_el_lot_nomes_porta_els_que_falten(self):
        m = self._mock()
        self._get(self.poms[:1])
        m.crides, m.textos = 0, []
        self._get(self.poms)
        self.assertEqual(m.crides, 1)
        self.assertEqual(m.textos[0], ['Chest width 1', 'Chest width 2'])

    def test_tot_cachejat_zero_crides(self):
        m = self._mock()
        self._get(self.poms)
        m.crides = 0
        r = self._get(self.poms)
        self.assertEqual(m.crides, 0)
        self.assertTrue(all(i['font'] == 'cache' for i in r.data['items']))

    # ── L'entrada ─────────────────────────────────────────────────────────────────────────
    def test_langles_no_es_una_traduccio(self):
        m = self._mock()
        r = self._get(self.poms[:1], lang='en')
        self.assertEqual(m.crides, 0, "demanar el text en el seu propi idioma no gasta quota")
        self.assertEqual(r.data['items'][0]['text'], 'Chest width 0')
        self.assertEqual(r.data['items'][0]['font'], 'origen')

    def test_lang_amb_regio_es_redueix_a_la_base(self):
        m = self._mock()
        self._get(self.poms[:1], lang='es-ES')
        self._get(self.poms[:1], lang='es')
        self.assertEqual(m.crides, 1, '`es-ES` i `es` són la mateixa entrada de cache')

    def test_pom_id_sol(self):
        self._mock()
        r = self.api.get('/api/v1/translate/pom/', {'pom_id': self.poms[0].id, 'lang': 'es'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['items']), 1)

    def test_ids_escombraries_i_inexistents_no_peten(self):
        self._mock()
        r = self.api.get('/api/v1/translate/pom/', {'pom_ids': 'x,,999999', 'lang': 'es'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['items'], [])

    def test_massa_ids_es_rebutja(self):
        r = self.api.get(
            '/api/v1/translate/pom/',
            {'pom_ids': ','.join(str(i) for i in range(ts.MAX_IDS + 1)), 'lang': 'es'},
        )
        self.assertEqual(r.status_code, 400)

    def test_cal_estar_autenticat(self):
        r = APIClient(SERVER_NAME=self.get_test_tenant_domain()).get(
            '/api/v1/translate/pom/', {'pom_ids': '1', 'lang': 'es'})
        self.assertIn(r.status_code, (401, 403))
