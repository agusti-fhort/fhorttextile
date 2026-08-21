"""S45/C · EL CATÀLEG DE JOCS S'OFEREIX ACOTAT — i els jubilats NO desapareixen.

Substrat: `docs/ordres/DIAGNOSI_BUGS_PROD_837_2026-08-21.md` §C.

── QUÈ CANVIA I PER QUÈ ─────────────────────────────────────────────────────────────────
A PROD (`fhort`) hi ha 52 `GradingRuleSet`: 34 actius i **18 JUBILATS**, i 51 amb regles. Els
quatre pickers de graduació demanaven `?page_size=200&amb_regles=1` i pintaven els 51 en un
`<div>` sense sostre. Dels 51, **24 són jocs LOS** que a un model de TRV o BRW no li serveixen
de res. Els filtres HI ERAN al `filterset_fields` des de sempre i cap dels quatre pickers els
feia servir.

**JUBILAR ≠ AMAGAR.** El que canvia és el DEFECTE, no la visibilitat: qui no diu res no vol
els jubilats; qui els ha de gestionar (la pantalla de Gestió de jocs, la fitxa de client) els
demana amb `?include_inactive=1`. I `?actiu=<x>` explícit segueix manant sobre tot plegat —
un defecte que es superposés a un filtre explícit tornaria SEMPRE buit amb `?actiu=false`.

**EL NULL ÉS COMODÍ, NO ABSÈNCIA.** Per això `per_client` i `per_size_system` no són el
`?customer=`/`?size_system=` exactes del filterset: un joc sense client és el catàleg de la
casa —el fons comú del qual tothom tria— i un joc sense sistema de talles val per a tots.
Filtrar per igualtat exacta buidaria la llista precisament dels jocs genèrics.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.pom.models import GradingRule, GradingRuleSet, POMMaster, SizeDefinition, SizeSystem
from fhort.pom.views import GradingRuleSetViewSet


class SedasJocsTest(TenantTestCase):
    """Un catàleg petit amb la MATEIXA forma que el de PROD: actius, jubilats, i d'altri."""

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
        from fhort.tasks.models import Customer
        self.user = get_user_model().objects.create(username='tester_s45c')

        self.ss_eu = SizeSystem.objects.create(codi='SS_EU', nom='EU', base_unit='ALPHA')
        self.ss_us = SizeSystem.objects.create(codi='SS_US', nom='US', base_unit='ALPHA')
        self.talla = SizeDefinition.objects.create(size_system=self.ss_eu, etiqueta='M', ordre=1)
        self.pom = POMMaster.objects.create(codi_client='PS45C', nom_client='POM S45C')

        self.brw = Customer.objects.create(codi='BRW', nom='Brownie')
        self.los = Customer.objects.create(codi='LOS', nom='Losan')

        def joc(nom, *, actiu=True, customer=None, size_system=None, amb_regla=True):
            rs = GradingRuleSet.objects.create(
                nom=nom, actiu=actiu, customer=customer, size_system=size_system)
            if amb_regla:
                GradingRule.objects.create(
                    rule_set=rs, pom=self.pom, talla_base=self.talla,
                    logica='LINEAR', increment_base=2)
            return rs

        self.casa_eu = joc('Casa EU', size_system=self.ss_eu)
        self.casa_cap_ss = joc('Casa sense sistema')            # comodí de sistema
        self.casa_us = joc('Casa US', size_system=self.ss_us)
        self.del_brw = joc('BRW propi', customer=self.brw)
        self.del_los = joc('LOS propi', customer=self.los)
        self.jubilat = joc('Casa JUBILAT', actiu=False)
        self.jubilat_brw = joc('BRW JUBILAT', actiu=False, customer=self.brw)
        self.esquelet = joc('Casa esquelet', amb_regla=False)

        self.factory = APIRequestFactory()
        self.view = GradingRuleSetViewSet.as_view({'get': 'list'})

    def _noms(self, **params):
        req = self.factory.get('/', {'page_size': 200, **params})
        force_authenticate(req, user=self.user)
        resp = self.view(req)
        self.assertEqual(resp.status_code, 200)
        dades = resp.data.get('results', resp.data)
        return sorted(d['nom'] for d in dades)


class DefecteNetTest(SedasJocsTest):
    """El DEFECTE: els jubilats no s'ofereixen."""

    def test_sense_cap_param_els_JUBILATS_no_hi_son(self):
        noms = self._noms()
        self.assertNotIn('Casa JUBILAT', noms)
        self.assertNotIn('BRW JUBILAT', noms)
        self.assertIn('Casa EU', noms)

    def test_include_inactive_els_TORNA(self):
        """🔑 Jubilar ≠ amagar: la pantalla que els gestiona els demana i els té."""
        noms = self._noms(include_inactive=1)
        self.assertIn('Casa JUBILAT', noms)
        self.assertIn('BRW JUBILAT', noms)
        self.assertIn('Casa EU', noms)

    def test_actiu_false_EXPLICIT_segueix_manant(self):
        """🚨 Si el defecte s'hi superposés, això tornaria SEMPRE buit."""
        noms = self._noms(actiu='false')
        self.assertEqual(noms, ['BRW JUBILAT', 'Casa JUBILAT'])

    def test_actiu_true_EXPLICIT_no_canvia_res(self):
        self.assertNotIn('Casa JUBILAT', self._noms(actiu='true'))

    def test_amb_regles_segueix_amagant_els_ESQUELETS(self):
        """No-regressió de B3: el filtre vell i el nou es componen, no es trepitgen."""
        noms = self._noms(amb_regles=1)
        self.assertNotIn('Casa esquelet', noms)
        self.assertNotIn('Casa JUBILAT', noms)
        self.assertIn('Casa EU', noms)


class PerClientTest(SedasJocsTest):
    """`per_client` — els del client MÉS els de catàleg. Mai els d'un altre client."""

    def test_els_del_client_i_els_de_CASA_hi_son_i_els_DALTRI_no(self):
        noms = self._noms(per_client=self.brw.pk)
        self.assertIn('BRW propi', noms)
        self.assertIn('Casa EU', noms)          # el catàleg de la casa és el fons comú
        self.assertNotIn('LOS propi', noms)     # ← els 24 jocs LOS de PROD, fora

    def test_per_client_NO_ressuscita_els_jubilats_del_client(self):
        self.assertNotIn('BRW JUBILAT', self._noms(per_client=self.brw.pk))

    def test_per_client_cap_deixa_NOMES_el_cataleg(self):
        noms = self._noms(per_client='cap')
        self.assertNotIn('BRW propi', noms)
        self.assertNotIn('LOS propi', noms)
        self.assertIn('Casa EU', noms)

    def test_un_per_client_ESCOMBRARIA_no_tomba_la_llista(self):
        """Un param brossa no pot ser un 500 ni un filtre fantasma: s'ignora."""
        self.assertIn('Casa EU', self._noms(per_client='patata'))

    def test_customer_EXACTE_del_filterset_segueix_sent_exacte(self):
        """No-regressió: `per_client` no és `?customer=`, i la fitxa de client usa aquell."""
        noms = self._noms(customer=self.brw.pk, include_inactive=1)
        self.assertEqual(noms, ['BRW JUBILAT', 'BRW propi'])


class PerSizeSystemTest(SedasJocsTest):
    """`per_size_system` — el sistema del model MÉS els que no en declaren cap."""

    def test_el_NULL_es_COMODI_i_no_absencia(self):
        noms = self._noms(per_size_system=self.ss_eu.pk)
        self.assertIn('Casa EU', noms)
        self.assertIn('Casa sense sistema', noms)   # ← comodí: hi ha de ser
        self.assertNotIn('Casa US', noms)

    def test_es_compon_amb_per_client(self):
        noms = self._noms(per_client=self.brw.pk, per_size_system=self.ss_eu.pk)
        self.assertIn('Casa EU', noms)
        self.assertIn('BRW propi', noms)            # sense sistema declarat → comodí
        self.assertNotIn('Casa US', noms)
        self.assertNotIn('LOS propi', noms)


class InclouTest(SedasJocsTest):
    """`?inclou=` — el que està EN ÚS travessa el sedàs. Mesurat al 1383 d'staging."""

    def test_el_joc_DALTRE_CLIENT_hi_torna_si_es_el_que_el_model_porta(self):
        """🚨 EL CAS REAL: model del client A amb un joc del client B assignat."""
        sense = self._noms(per_client=self.brw.pk)
        self.assertNotIn('LOS propi', sense)
        amb = self._noms(per_client=self.brw.pk, inclou=self.del_los.pk)
        self.assertIn('LOS propi', amb)
        self.assertIn('Casa EU', amb)          # i el sedàs segueix valent per a la resta
        self.assertNotIn('Casa JUBILAT', amb)

    def test_un_joc_JUBILAT_en_us_tambe_hi_torna(self):
        """Un model amb un joc jubilat posat l'ha de poder veure: si no, no el pot canviar."""
        self.assertIn('Casa JUBILAT', self._noms(inclou=self.jubilat.pk))

    def test_un_ESQUELET_en_us_tambe_hi_torna(self):
        self.assertIn('Casa esquelet', self._noms(amb_regles=1, inclou=self.esquelet.pk))

    def test_accepta_una_llista(self):
        noms = self._noms(per_client='cap', inclou=f'{self.del_los.pk},{self.del_brw.pk}')
        self.assertIn('LOS propi', noms)
        self.assertIn('BRW propi', noms)

    def test_un_inclou_ESCOMBRARIA_no_tomba_la_llista(self):
        self.assertIn('Casa EU', self._noms(inclou='patata'))

    def test_sense_inclou_res_no_canvia(self):
        self.assertEqual(self._noms(), self._noms(inclou=''))
