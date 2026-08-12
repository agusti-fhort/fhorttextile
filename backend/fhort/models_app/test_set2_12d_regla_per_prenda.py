"""SET-2/#12d — la REGLA de graduació sap de quina prenda parla (2026-08-12).

Tercer cop del mateix patró, i el darrer dels tres costats del contracte de la peça:
`#12b` va acotar la PODA de mesures, `#12c` va donar l'eix a l'ESCRIPTURA de mesures, i
aquí el guanya la taula de REGLES.

LA CLAU DE `ModelGradingRule` ÉS `(model, pom, garment)` DES DE T3 —reobertura conscient de
l'acta, autoritzada (D4)— i la comporta que la congelava va caure al #12. Però el contracte
que l'edita es va quedar enrere: `set_pom_regim_view` identificava la regla amb el `pom_id`
pelat, o sigui que editar-la des del contenidor de la 02 escrivia sobre la de la mare.

I EL LECTOR ERA PITJOR QUE L'ESCRIPTOR. `base_measurements_view` indexava
`{r.pom_id: {...}}`: amb la mare i la 02 amb regla pròpia sobre el mateix POM, el diccionari
en perdia una —guanyava l'última llegida— i les DUES files ensenyaven la mateixa llei. El
mode de fallada exacte que `_load_grading_rules` tenia abans de T4 i que la comporta de T3
existia per fer impossible; amb la comporta fora, tornava a ser assolible.

HERÈNCIA (D5-bis): una peça sense regla pròpia SEGUEIX la de la mare. El lector la hi
serveix i ho diu (`heretat`), perquè «no en té» i «té la mateixa» no són el mateix estat i
la pantalla ha de poder distingir-los.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.models_app.views import set_pom_regim_view
from fhort.pom.models import POMMaster
from fhort.pom.wizard_views import base_measurements_view

MARE = ''
SEGONA = '02'


class LaReglaSapDeQuinaPrendaParlaTest(TenantTestCase):

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
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='TST-12D', codi_tenant='TST', any=2026, sequencial=5,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_12d', defaults={'email': 'qa@12d.test'})
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA 12d', 'rol_nom': 'QA'})

    def _post(self, body):
        r = APIRequestFactory().post('/x/', body, format='json')
        force_authenticate(r, user=self.user)
        return set_pom_regim_view(r, self.model.id, self.pom.id)

    def _get_files(self):
        r = APIRequestFactory().get('/x/')
        force_authenticate(r, user=self.user)
        resp = base_measurements_view(r, self.model.id)
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        return resp.data['results']

    def _regla(self, garment, increment_base):
        return ModelGradingRule.objects.create(
            model=self.model, pom=self.pom, garment=garment, actiu=True,
            logica='LINEAR', increment=0, increment_base=increment_base, origen='MANUAL')

    def _mesura(self, garment, valor, nom):
        return BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=valor, ordre=1,
            nom_fitxa=nom, garment=garment)

    # ── ESCRIPTURA ──────────────────────────────────────────────────────────────────

    def test_editar_la_regla_de_la_02_NO_toca_la_de_la_mare(self):
        """EL VERMELL. Les dues prendes tenen regla pròpia sobre el mateix POM."""
        mare = self._regla(MARE, 4.0)
        segona = self._regla(SEGONA, 2.0)

        resp = self._post({'increment_base': 9.0, 'garment': SEGONA})

        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        mare.refresh_from_db()
        segona.refresh_from_db()
        self.assertEqual(float(mare.increment_base), 4.0,
                         'EDITAR LA REGLA DE LA 02 HA MOGUT LA DE LA MARE')
        self.assertEqual(float(segona.increment_base), 9.0)
        self.assertEqual(resp.data.get('garment'), SEGONA,
                         'la resposta ha de dir de quina prenda parla')

    def test_una_peca_SENSE_regla_propia_estrena_la_seva_i_la_mare_queda_intacta(self):
        """L'override de llei (D5-bis): escriure des de la 02 fa NÉIXER la seva regla."""
        mare = self._regla(MARE, 4.0)
        self.assertEqual(ModelGradingRule.objects.filter(model=self.model).count(), 1)

        resp = self._post({'increment_base': 9.0, 'garment': SEGONA})

        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        mare.refresh_from_db()
        self.assertEqual(float(mare.increment_base), 4.0,
                         "la regla de la mare no es toca quan la peça estrena la seva")
        nova = ModelGradingRule.objects.get(model=self.model, pom=self.pom, garment=SEGONA)
        self.assertEqual(float(nova.increment_base), 9.0)
        self.assertEqual(nova.origen, 'MANUAL')

    def test_EL_CAS_DE_CONTROL_un_client_sense_garment_fa_el_de_sempre(self):
        """El 100% dels clients d'avui no envia l'eix: ha d'escriure a la mare, com sempre."""
        mare = self._regla(MARE, 4.0)
        segona = self._regla(SEGONA, 2.0)

        resp = self._post({'increment_base': 7.0})

        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        mare.refresh_from_db()
        segona.refresh_from_db()
        self.assertEqual(float(mare.increment_base), 7.0)
        self.assertEqual(float(segona.increment_base), 2.0,
                         "un client que no diu la prenda no pot tocar la de la 02")

    # ── LECTURA ─────────────────────────────────────────────────────────────────────

    def test_el_lector_serveix_a_cada_fila_LA_SEVA_llei(self):
        """EL VERMELL DEL LECTOR: `{r.pom_id: ...}` en perdia una i servia la mateixa a totes
        dues."""
        self._regla(MARE, 4.0)
        self._regla(SEGONA, 2.0)
        self._mesura(MARE, 100.0, 'A-MARE')
        self._mesura(SEGONA, 60.0, 'A-02')

        per_garment = {f['garment']: f.get('regla_model') for f in self._get_files()}

        self.assertEqual(float(per_garment[MARE]['increment_base']), 4.0)
        self.assertEqual(float(per_garment[SEGONA]['increment_base']), 2.0,
                         'LA FILA DE LA 02 ENSENYA LA LLEI DE LA MARE')
        self.assertFalse(per_garment[SEGONA]['heretat'])

    def test_una_peca_sense_regla_propia_HERETA_la_de_la_mare_i_es_diu(self):
        """D5-bis: «no en té» i «té la mateixa» no són el mateix estat."""
        self._regla(MARE, 4.0)
        self._mesura(MARE, 100.0, 'A-MARE')
        self._mesura(SEGONA, 60.0, 'A-02')

        per_garment = {f['garment']: f.get('regla_model') for f in self._get_files()}

        self.assertEqual(float(per_garment[SEGONA]['increment_base']), 4.0,
                         'la peça sense regla pròpia ha de seguir la de la mare')
        self.assertTrue(per_garment[SEGONA]['heretat'],
                        'i la pantalla ha de poder saber que és heretada')
        self.assertFalse(per_garment[MARE]['heretat'])
