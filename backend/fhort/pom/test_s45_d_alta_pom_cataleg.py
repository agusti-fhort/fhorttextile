"""S45/D · ALTA DE POM AL CATÀLEG DEL TENANT — el POM neix SOL.

Substrat: `docs/ordres/DIAGNOSI_BUGS_PROD_837_2026-08-21.md` §D.

── QUÈ CANVIA I PER QUÈ ─────────────────────────────────────────────────────────────────
`POST /api/v1/poms/crear-tenant/` existia des de sempre i **no la cridava ningú**: el
POMBrowser (645 POMs, cercador, assignar, treure, KEY, reordenar) no tenia cap botó de crear,
i l'única alta de POM del producte era la del MODEL (`create_model_pom_view`), que exigeix
`modelId` i neix amb `CustomerPOMAlias`. El tram li posa la UI al davant.

🚨 **EL DEFECTE QUE S'HI VA TROBAR EN OBRIR-LA**: el guard de duplicats mirava
`filter(codi_client=code)` —exacte— i la constraint de la BD és CASE-INSENSITIVE
(`uniq_pommaster_codi_client_ci`). Amb «CF» al catàleg, crear «cf» passava el guard, petava
contra la constraint i sortia per l'`except Exception` com un **500 amb el text del driver**.
El banc el fixa amb `test_el_duplicat_amb_ALTRA_CAIXA_es_400_i_no_un_500`, que abans del canvi
donava 500.

── EL QUE AQUEST BANC PROTEGEIX MÉS ENLLÀ DEL 400 ──────────────────────────────────────
Que el POM neix **SOL**: sense `CustomerPOMAlias`, sense `GarmentPOMMap`, sense `pom_global`.
Són les tres coses que §D.4 marca com a efectes col·laterals i que el brief prohibeix tocar —
vincular-lo a una peça és el flux ASSIGN, i promoure'l a canònic és feina de backoffice. Si
algun dia algú «millora» aquesta porta afegint-hi l'àlies per comoditat, aquí es posa vermell.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.pom.models import CustomerPOMAlias, POMCategory, POMMaster
from fhort.pom.wizard_views import create_tenant_pom_view


class AltaPomCatalegTest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='tester_s45d')
        self.cat = POMCategory.objects.create(codi='CAT_S45D', nom_en='Cat S45D')
        self.factory = APIRequestFactory()

    def _crear(self, **body):
        req = self.factory.post('/api/v1/poms/crear-tenant/', body, format='json')
        force_authenticate(req, user=self.user)
        return create_tenant_pom_view(req)

    # ── el camí bo ────────────────────────────────────────────────────────────────────
    def test_crea_el_POM_i_el_torna(self):
        resp = self._crear(codi_client='ZZ1', nom_client='Mesura de prova')
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        self.assertEqual(resp.data['codi_client'], 'ZZ1')
        self.assertTrue(POMMaster.objects.filter(codi_client='ZZ1').exists())

    def test_neix_ACTIU_i_sense_pom_global(self):
        self._crear(codi_client='ZZ2', nom_client='Mesura 2')
        pom = POMMaster.objects.get(codi_client='ZZ2')
        self.assertTrue(pom.actiu)
        self.assertIsNone(pom.pom_global_id)      # catàleg de TENANT, no canònic
        self.assertEqual(pom.origen_import, 'cataleg')
        # No neix pendent de revisió: qui l'ha creat ÉS a la pantalla del catàleg.
        self.assertFalse(pom.pendent_revisio)

    def test_la_categoria_es_OPCIONAL_i_sassigna_si_ve(self):
        self._crear(codi_client='ZZ3', nom_client='Mesura 3')
        self.assertIsNone(POMMaster.objects.get(codi_client='ZZ3').categoria_id)
        self._crear(codi_client='ZZ4', nom_client='Mesura 4', categoria_id=self.cat.pk)
        self.assertEqual(POMMaster.objects.get(codi_client='ZZ4').categoria_id, self.cat.pk)

    # ── 🔑 el POM neix SOL: cap efecte col·lateral ────────────────────────────────────
    def test_NO_crea_alies_de_client(self):
        """§D.4 — vincular-lo a un client és una altra decisió, i té la seva porta."""
        self._crear(codi_client='ZZ5', nom_client='Mesura 5')
        pom = POMMaster.objects.get(codi_client='ZZ5')
        self.assertFalse(CustomerPOMAlias.objects.filter(pom=pom).exists())

    def test_NO_entra_a_cap_GTI_ni_a_cap_sembra(self):
        """§D.4 — posar-lo en una peça és el flux ASSIGN del POMBrowser."""
        from fhort.pom.models import GarmentPOMMap
        self._crear(codi_client='ZZ6', nom_client='Mesura 6')
        pom = POMMaster.objects.get(codi_client='ZZ6')
        self.assertFalse(GarmentPOMMap.objects.filter(pom=pom).exists())

    # ── els guards ───────────────────────────────────────────────────────────────────
    def test_sense_codi_o_sense_nom_es_400(self):
        self.assertEqual(self._crear(codi_client='', nom_client='X').status_code, 400)
        self.assertEqual(self._crear(codi_client='ZZ7', nom_client='').status_code, 400)
        self.assertFalse(POMMaster.objects.filter(codi_client='ZZ7').exists())

    def test_el_duplicat_EXACTE_es_400(self):
        self._crear(codi_client='ZZ8', nom_client='Mesura 8')
        resp = self._crear(codi_client='ZZ8', nom_client='Una altra')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('ZZ8', resp.data['error'])
        self.assertEqual(POMMaster.objects.filter(codi_client__iexact='ZZ8').count(), 1)

    def test_el_duplicat_amb_ALTRA_CAIXA_es_400_i_no_un_500(self):
        """🔴→🟢 La constraint és case-insensitive; el guard mirava en exacte i queia al 500."""
        self._crear(codi_client='ZZ9', nom_client='Mesura 9')
        resp = self._crear(codi_client='zz9', nom_client='Una altra')
        self.assertEqual(resp.status_code, 400, getattr(resp, 'data', None))
        self.assertEqual(POMMaster.objects.filter(codi_client__iexact='ZZ9').count(), 1)
