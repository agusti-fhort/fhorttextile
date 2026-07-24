"""La superfície del Studio: safata, traspàs per API i aterratge del token (Federació v2, P8).

Les lleis que defensen:

  · EL STUDIO ÉS EL DEL REQUEST, MAI EL DEL PAYLOAD (mirall de P7).
  · L'ESTAT ÉS UNA COMPARACIÓ, NO UN CAMP: PENDENT/TRASPASSAT surt de mirar si el codi_intern
    ja existeix al meu schema. Esborrar el model local el torna a PENDENT tot sol.
  · PARITAT API↔COMMAND: les dues boques donen el MATEIX resultat perquè criden el mateix
    servei. El test ho comprova sobre el resultat, no sobre el codi.
  · NOMÉS VINCLES ACTIUS a la safata: un pont tancat no és feina pendent.
  · EL TOKEN IDENTIFICA, NO AUTORITZA: no crea vincle, no el reactiva, i el d'un altre Studio
    no serveix. Els tres errors tenen la MATEIXA cara.
  · UNA MARCA NO REP ENCÀRRECS: 403 a tota la superfície.

    cd backend && venv/bin/python manage.py test fhort.tenants.tests_encarrecs
"""
import io

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_model, schema_context
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.models import Model
from fhort.tasks.models import Customer
from fhort.tasks.views_b import CustomerViewSet
from fhort.tenants.models import Client, TenantLink
from fhort.tenants.views_encarrecs import EncarrecViewSet

BRAND = 'BRD'
ALTRE_BRAND = 'BR2'
ALTRE_STUDIO = 'ST2'


class EncarrecsBase(TenantTestCase):
    """El tenant del test és l'ESTUDI. Dos Brands reals a part (un vinculat, un altre no)."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Estudi'
        tenant.codi_tenant = 'STU'
        tenant.tipologia = Client.TIPOLOGIA_ESTUDI
        tenant.email_facturacio = 'e@x.com'
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connection.set_schema_to_public()
        TenantModel = get_tenant_model()
        cls.brand = TenantModel(schema_name='brd', nom='Marca U', codi_tenant=BRAND,
                                tipologia=Client.TIPOLOGIA_MARCA, email_facturacio='m@x.com')
        cls.brand.save(verbosity=0)
        cls.brand.domains.create(domain='brd.test.com', is_primary=True)
        cls.brand2 = TenantModel(schema_name='br2', nom='Marca Dos', codi_tenant=ALTRE_BRAND,
                                 tipologia=Client.TIPOLOGIA_MARCA, email_facturacio='m2@x.com')
        cls.brand2.save(verbosity=0)
        cls.brand2.domains.create(domain='br2.test.com', is_primary=True)
        cls.studio2 = TenantModel(schema_name='st2', nom='Estudi Dos', codi_tenant=ALTRE_STUDIO,
                                  tipologia=Client.TIPOLOGIA_ESTUDI, email_facturacio='e2@x.com')
        cls.studio2.save(verbosity=0)
        cls.studio2.domains.create(domain='st2.test.com', is_primary=True)
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        for t in (cls.brand, cls.brand2, cls.studio2):
            t.delete(force_drop=True)
        super().tearDownClass()

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user('admin@test.local', password='x')
        prof, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Admin', 'rol_nom': 'admin'})
        prof.rol_nom = 'admin'
        prof.save(update_fields=['rol_nom'])
        self.user = get_user_model().objects.get(pk=self.user.pk)

        with schema_context('public'):
            TenantLink.objects.all().delete()
            self.link = TenantLink.objects.create(
                brand_codi_tenant=BRAND, studio_codi_tenant='STU')

        # 5 models al Brand: 3 assignats a mi, 1 a un altre Studio, 1 sense assignar.
        with schema_context('brd'):
            Model.objects.all().delete()
            for i in range(1, 6):
                Model.objects.create(
                    codi_intern=f'BRD-SS27-{i:04d}', codi_tenant=BRAND, any=2027,
                    temporada='SS', sequencial=i, nom_prenda=f'M{i}',
                    studio_assignat=('STU' if i <= 3 else (ALTRE_STUDIO if i == 4 else '')))

        # Al meu schema: el Customer del Brand (condició del traspàs) i cap model.
        Model.objects.all().delete()
        Customer.objects.get_or_create(codi=BRAND, defaults={'nom': 'Marca U'})

    # ── helpers ────────────────────────────────────────────────────────────────
    def _req(self, method, path, data=None, tenant=None):
        req = getattr(self.factory, method)(path, data, format='json')
        force_authenticate(req, user=self.user)
        req.tenant = tenant or self.tenant
        return req

    def _safata(self):
        return EncarrecViewSet.as_view({'get': 'list'})(self._req('get', '/api/v1/encarrecs/'))

    def _traspassar(self, data):
        return EncarrecViewSet.as_view({'post': 'traspassar'})(
            self._req('post', '/api/v1/encarrecs/traspassar/', data))


# ── La safata ───────────────────────────────────────────────────────────────────
class SafataTest(EncarrecsBase):

    def test_agrupa_per_brand_i_nomes_el_que_m_han_assignat(self):
        d = self._safata().data
        self.assertEqual(len(d['grups']), 1)
        g = d['grups'][0]
        self.assertEqual(g['brand_codi'], BRAND)
        self.assertEqual(g['brand_nom'], 'Marca U')
        # 3 meus; el d'ALTRE_STUDIO i el no assignat no hi són.
        self.assertEqual([m['codi_intern'] for m in g['models']],
                         ['BRD-SS27-0001', 'BRD-SS27-0002', 'BRD-SS27-0003'])

    def test_estat_local_arrenca_tot_pendent(self):
        g = self._safata().data['grups'][0]
        self.assertTrue(all(m['estat_local'] == 'PENDENT' for m in g['models']))
        self.assertEqual((g['n_pendents'], g['n_traspassats']), (3, 0))

    def test_l_estat_es_una_comparacio_no_un_camp(self):
        self._traspassar({'brand_codi': BRAND, 'codis': ['BRD-SS27-0001']})
        g = self._safata().data['grups'][0]
        self.assertEqual((g['n_pendents'], g['n_traspassats']), (2, 1))
        # …i esborrar el model local el torna a PENDENT tot sol: cap booleà que mantenir.
        Model.objects.filter(codi_intern='BRD-SS27-0001').delete()
        g = self._safata().data['grups'][0]
        self.assertEqual((g['n_pendents'], g['n_traspassats']), (3, 0))

    def test_vincle_aturat_desapareix_de_la_safata(self):
        with schema_context('public'):
            self.link.aturar()
        self.assertEqual(self._safata().data['grups'], [])

    def test_no_veig_els_encarrecs_d_un_altre_studio(self):
        with schema_context('public'):
            TenantLink.objects.create(brand_codi_tenant=ALTRE_BRAND,
                                      studio_codi_tenant=ALTRE_STUDIO)
        self.assertEqual([g['brand_codi'] for g in self._safata().data['grups']], [BRAND])

    def test_una_marca_no_te_safata(self):
        self.tenant.tipologia = Client.TIPOLOGIA_MARCA
        self.assertEqual(self._safata().status_code, 403)
        self.tenant.tipologia = Client.TIPOLOGIA_ESTUDI


# ── El traspàs per API ──────────────────────────────────────────────────────────
class TraspasApiTest(EncarrecsBase):

    def test_traspassa_els_codis_triats(self):
        r = self._traspassar({'brand_codi': BRAND, 'codis': ['BRD-SS27-0001', 'BRD-SS27-0002']})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['n_creats'], 2)
        self.assertEqual(Model.objects.filter(origen=Model.ORIGEN_EXTERN).count(), 2)

    def test_tots_pendents(self):
        r = self._traspassar({'brand_codi': BRAND, 'codis': 'tots_pendents'})
        self.assertEqual(r.data['n_creats'], 3)
        self.assertEqual(Model.objects.count(), 3)

    def test_idempotent_segona_passada_salta(self):
        self._traspassar({'brand_codi': BRAND, 'codis': 'tots_pendents'})
        r = self._traspassar({'brand_codi': BRAND, 'codis': 'tots_pendents'})
        self.assertEqual(r.data['n_creats'], 0)
        self.assertEqual(r.data['n_saltats'], 3)
        self.assertEqual(Model.objects.count(), 3)   # cap duplicat

    def test_no_puc_demanar_un_model_que_no_m_han_assignat(self):
        # El 0004 és d'ALTRE_STUDIO: el filtre d'assignació mana sobre els codis demanats.
        r = self._traspassar({'brand_codi': BRAND, 'codis': ['BRD-SS27-0004']})
        self.assertEqual(r.data['n_creats'], 0)
        self.assertFalse(Model.objects.filter(codi_intern='BRD-SS27-0004').exists())

    def test_pont_aturat_es_409(self):
        with schema_context('public'):
            self.link.aturar()
        r = self._traspassar({'brand_codi': BRAND, 'codis': 'tots_pendents'})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['code'], 'link_not_active')
        self.assertEqual(Model.objects.count(), 0)

    def test_brand_sense_vincle_es_400(self):
        r = self._traspassar({'brand_codi': ALTRE_BRAND, 'codis': 'tots_pendents'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data['code'], 'link_missing')

    def test_sense_client_al_studio_es_409_amb_nom(self):
        Customer.objects.filter(codi=BRAND).delete()
        r = self._traspassar({'brand_codi': BRAND, 'codis': 'tots_pendents'})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['code'], 'customer_missing')

    def test_brand_codi_obligatori(self):
        self.assertEqual(self._traspassar({'codis': 'tots_pendents'}).status_code, 400)

    def test_una_marca_no_traspassa(self):
        self.tenant.tipologia = Client.TIPOLOGIA_MARCA
        self.assertEqual(
            self._traspassar({'brand_codi': BRAND, 'codis': 'tots_pendents'}).status_code, 403)
        self.tenant.tipologia = Client.TIPOLOGIA_ESTUDI

    # ── PARITAT: les dues boques, el mateix resultat ────────────────────────────
    def test_paritat_api_vs_command(self):
        """L'API crea exactament el que el command hauria creat, amb els mateixos camps."""
        self._traspassar({'brand_codi': BRAND, 'codis': 'tots_pendents'})
        per_api = {(m.codi_intern, m.origen, m.any, m.temporada, m.sequencial, m.nom_prenda)
                   for m in Model.objects.all()}
        self.assertEqual(len(per_api), 3)

        Model.objects.all().delete()
        out = io.StringIO()
        call_command('instantiate_external_models', '--brand', BRAND, '--studio', 'STU',
                     '--commit', stdout=out)
        per_command = {(m.codi_intern, m.origen, m.any, m.temporada, m.sequencial, m.nom_prenda)
                       for m in Model.objects.all()}

        self.assertEqual(per_api, per_command)
        self.assertIn('Fet: 3 models EXTERN creats', out.getvalue())

    def test_regressio_el_command_segueix_igual(self):
        """El refactor a servei no ha canviat ni els números ni els textos del command."""
        out = io.StringIO()
        call_command('instantiate_external_models', '--brand', BRAND, '--studio', 'STU', stdout=out)
        s = out.getvalue()
        self.assertIn('models al Brand   : 5 · assignats a STU: 3', s)
        self.assertIn('llegits (assignats): 3', s)
        self.assertIn('a crear          : 3', s)
        self.assertIn('saltats (ja hi són): 0', s)
        self.assertIn('DRY-RUN: no s\'ha escrit res', s)
        self.assertEqual(Model.objects.count(), 0)   # dry-run no escriu


# ── L'aterratge del token ───────────────────────────────────────────────────────
class VincularTokenTest(EncarrecsBase):

    def setUp(self):
        super().setUp()
        self.cust = Customer.objects.get(codi=BRAND)

    def _vincular(self, pk, data=None, method='post'):
        req = self._req(method, f'/api/v1/customers/{pk}/vincular-token/', data)
        return CustomerViewSet.as_view({method: 'vincular_token'})(req, pk=pk)

    def test_token_valid_escriu_codi_global(self):
        r = self._vincular(self.cust.pk, {'token': self.link.token})
        self.assertEqual(r.status_code, 200)
        self.cust.refresh_from_db()
        self.assertEqual(self.cust.codi_global, BRAND)
        self.assertEqual(r.data['vincle_estat'], TenantLink.ESTAT_ACTIU)

    def test_token_de_vincle_aturat_es_rebutja(self):
        with schema_context('public'):
            self.link.aturar()
        r = self._vincular(self.cust.pk, {'token': self.link.token})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data['code'], 'token_invalid')
        self.cust.refresh_from_db()
        self.assertIsNone(self.cust.codi_global)   # el pont tancat no es reobre per aquí

    def test_token_d_un_altre_studio_es_rebutja(self):
        with schema_context('public'):
            alie = TenantLink.objects.create(brand_codi_tenant=ALTRE_BRAND,
                                             studio_codi_tenant=ALTRE_STUDIO)
        r = self._vincular(self.cust.pk, {'token': alie.token})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data['code'], 'token_invalid')

    def test_token_inexistent_te_la_mateixa_cara(self):
        r = self._vincular(self.cust.pk, {'token': 'no-existeix'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data['code'], 'token_invalid')

    def test_token_buit_es_rebutja(self):
        self.assertEqual(self._vincular(self.cust.pk, {'token': ''}).status_code, 400)

    def test_dos_clients_no_poden_apuntar_al_mateix_brand(self):
        self._vincular(self.cust.pk, {'token': self.link.token})
        altre = Customer.objects.create(codi='ZZZ', nom='Un altre')
        r = self._vincular(altre.pk, {'token': self.link.token})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['code'], 'codi_global_pres')

    def test_desvincular_buida_pero_no_toca_el_vincle(self):
        self._vincular(self.cust.pk, {'token': self.link.token})
        r = self._vincular(self.cust.pk, method='delete')
        self.assertEqual(r.status_code, 200)
        self.cust.refresh_from_db()
        self.assertIsNone(self.cust.codi_global)
        with schema_context('public'):
            self.link.refresh_from_db()
            self.assertEqual(self.link.estat, TenantLink.ESTAT_ACTIU)   # el pont, intacte

    def test_codi_global_no_s_escriu_per_patch(self):
        req = self._req('patch', f'/api/v1/customers/{self.cust.pk}/', {'codi_global': BRAND})
        CustomerViewSet.as_view({'patch': 'partial_update'})(req, pk=self.cust.pk)
        self.cust.refresh_from_db()
        self.assertIsNone(self.cust.codi_global)   # l'única porta és vincular-token
