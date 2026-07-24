"""La superfície del Brand sobre els seus recursos (Federació v2, P7).

Les lleis que defensen:

  · EL BRAND ÉS EL DEL REQUEST, MAI EL DEL PAYLOAD. Ni en llegir, ni en crear, ni en
    assignar. Si el brand pogués viatjar al body, un tenant emetria vincles en nom d'un
    altre i el unique_together no ho aturaria (seria una parella nova, perfectament vàlida).
  · EL TOKEN SURT UN SOL COP. A la resposta de creació i enlloc més: ni a la llista, ni a
    cap acció. Una credencial rellegible a voluntat acaba a tots els logs i caches del camí.
  · DUES CLAUS INDEPENDENTS. El vincle autoritza el PONT; studio_assignat autoritza CADA
    MODEL. Assignar amb el pont ATURAT és 409 — seria escriure una autorització desmentida.
  · RETIRAR NO DEMANA PONT. Treure una autorització ha de ser possible sempre, també quan
    el pont ja no hi és.
  · UN ESTUDI NO EMET VINCLES, ELS REP. 403 a tota la superfície.

Es munten DOS tenants reals (una Marca que és el tenant del test i un Estudi a part) perquè
la validació de tipologies llegeix `Client` de debò.

    cd backend && venv/bin/python manage.py test fhort.tenants.tests_recursos
"""
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_model
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.accounts.views import me_view
from fhort.models_app.models import Model
from fhort.models_app.views import ModelViewSet
from fhort.tenants.models import Client, TenantLink
from fhort.tenants.views_recursos import RecursViewSet

BRAND = 'BRD'
STUDIO = 'STU'
ALIEN = 'ALI'   # una altra Marca: els seus vincles no s'han de veure mai des de BRD


class RecursosBase(TenantTestCase):
    """El tenant del test és la MARCA. Un segon tenant real fa d'Estudi."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Marca'
        tenant.codi_tenant = BRAND
        tenant.tipologia = Client.TIPOLOGIA_MARCA
        tenant.email_facturacio = 'm@x.com'
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connection.set_schema_to_public()
        TenantModel = get_tenant_model()
        cls.studio = TenantModel(
            schema_name='stu', nom='Estudi Vinculat', codi_tenant=STUDIO,
            tipologia=Client.TIPOLOGIA_ESTUDI, email_facturacio='e@x.com',
        )
        cls.studio.save(verbosity=0)
        cls.studio.domains.create(domain='stu.test.com', is_primary=True)
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.studio.delete(force_drop=True)
        super().tearDownClass()

    def setUp(self):
        self.factory = APIRequestFactory()
        # admin → té CONFIGURE, que és el gate de tota l'escriptura d'aquesta superfície.
        self.user = get_user_model().objects.create_user('admin@test.local', password='x')
        # El signal post_save(User) ja ha creat el perfil amb el rol per defecte: cal
        # promocionar-lo i RELLEGIR l'usuari (get_capabilities llegeix user.profile cachejat).
        prof, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Admin', 'rol_nom': 'admin'})
        prof.rol_nom = 'admin'
        prof.save(update_fields=['rol_nom'])
        self.user = get_user_model().objects.get(pk=self.user.pk)
        TenantLink.objects.all().delete()

    # ── helpers de crida (patró tests_self_customer: view directa, sense routing) ──
    def _req(self, method, path, data=None, tenant=None):
        req = getattr(self.factory, method)(path, data, format='json')
        force_authenticate(req, user=self.user)
        req.tenant = tenant or self.tenant
        return req

    def _list(self, tenant=None):
        return RecursViewSet.as_view({'get': 'list'})(self._req('get', '/api/v1/recursos/', tenant=tenant))

    def _create(self, data, tenant=None):
        return RecursViewSet.as_view({'post': 'create'})(
            self._req('post', '/api/v1/recursos/', data, tenant=tenant))

    def _acte(self, pk, nom):
        return RecursViewSet.as_view({'post': nom})(
            self._req('post', f'/api/v1/recursos/{pk}/{nom}/'), pk=pk)

    def _assignar(self, data, tenant=None):
        return ModelViewSet.as_view({'post': 'assignar_recurs'})(
            self._req('post', '/api/v1/models/assignar-recurs/', data, tenant=tenant))


# ── /me diu qui és la CASA, no només qui és l'usuari ────────────────────────────
class MeTenantTest(RecursosBase):

    def _me(self):
        return me_view(self._req('get', '/api/v1/me/'))

    def test_me_exposa_el_tenant(self):
        t = self._me().data['tenant']
        self.assertEqual(t['codi_tenant'], BRAND)
        self.assertEqual(t['tipologia'], Client.TIPOLOGIA_MARCA)
        self.assertEqual(t['nom'], 'Marca')

    def test_me_sense_tenant_dona_none_no_diccionari_a_mitges(self):
        req = self._req('get', '/api/v1/me/')
        req.tenant = None
        self.assertIsNone(me_view(req).data['tenant'])


# ── Llista: només els meus vincles, i mai el token ──────────────────────────────
class LlistaRecursosTest(RecursosBase):

    def setUp(self):
        super().setUp()
        self.meu = TenantLink.objects.create(
            brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)
        self.alie = TenantLink.objects.create(
            brand_codi_tenant=ALIEN, studio_codi_tenant=STUDIO)

    def test_nomes_els_vincles_del_brand_del_request(self):
        data = self._list().data
        self.assertEqual([r['studio_codi'] for r in data], [STUDIO])
        self.assertEqual(len(data), 1)   # el vincle d'ALI existeix però no es veu

    def test_la_llista_no_porta_mai_el_token(self):
        for r in self._list().data:
            self.assertNotIn('token', r)

    def test_la_llista_resol_el_nom_del_studio_per_codi_nu(self):
        self.assertEqual(self._list().data[0]['studio_nom'], 'Estudi Vinculat')

    def test_un_estudi_no_pot_mirar_recursos(self):
        self.tenant.tipologia = Client.TIPOLOGIA_ESTUDI   # només a l'objecte del request
        self.assertEqual(self._list().status_code, 403)
        self.tenant.tipologia = Client.TIPOLOGIA_MARCA


# ── Alta: el token un sol cop, el brand del request, i les validacions del destí ─
class AltaRecursTest(RecursosBase):

    def test_alta_retorna_el_token_un_sol_cop(self):
        res = self._create({'studio_codi': STUDIO})
        self.assertEqual(res.status_code, 201)
        token = res.data['token']
        self.assertTrue(token)
        # …i no torna a sortir mai més per la llista.
        self.assertNotIn('token', self._list().data[0])

    def test_el_brand_surt_del_request_mai_del_payload(self):
        self._create({'studio_codi': STUDIO, 'brand_codi_tenant': ALIEN})
        link = TenantLink.objects.get(studio_codi_tenant=STUDIO)
        self.assertEqual(link.brand_codi_tenant, BRAND)   # NO ALI

    def test_desti_inexistent_es_400(self):
        res = self._create({'studio_codi': 'ZZZ'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['code'], 'invalid_studio')

    def test_desti_que_no_es_estudi_es_400(self):
        res = self._create({'studio_codi': BRAND})   # el propi Brand: existeix, però és marca
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['code'], 'self_link')

    def test_vincle_duplicat_es_409(self):
        self._create({'studio_codi': STUDIO})
        res = self._create({'studio_codi': STUDIO})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data['code'], 'link_exists')

    def test_codi_buit_es_400(self):
        self.assertEqual(self._create({'studio_codi': ''}).status_code, 400)

    def test_un_estudi_no_pot_emetre_vincles(self):
        self.tenant.tipologia = Client.TIPOLOGIA_ESTUDI
        self.assertEqual(self._create({'studio_codi': STUDIO}).status_code, 403)
        self.tenant.tipologia = Client.TIPOLOGIA_MARCA


# ── Els tres actes: el model mana les transicions, la view només les trasllada ──
class ActesRecursTest(RecursosBase):

    def setUp(self):
        super().setUp()
        self.link = TenantLink.objects.create(
            brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)

    def test_aturar_i_reactivar(self):
        self.assertEqual(self._acte(self.link.pk, 'aturar').data['estat'], TenantLink.ESTAT_ATURAT)
        self.assertEqual(self._acte(self.link.pk, 'reactivar').data['estat'], TenantLink.ESTAT_ACTIU)

    def test_reactivar_un_actiu_es_409(self):
        self.assertEqual(self._acte(self.link.pk, 'reactivar').status_code, 409)

    def test_revocat_es_terminal(self):
        self.assertEqual(self._acte(self.link.pk, 'revocar').data['estat'], TenantLink.ESTAT_REVOCAT)
        res = self._acte(self.link.pk, 'reactivar')
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data['code'], 'transicio_invalida')

    def test_no_es_pot_tocar_el_vincle_d_una_altra_marca(self):
        alie = TenantLink.objects.create(brand_codi_tenant=ALIEN, studio_codi_tenant=STUDIO)
        self.assertEqual(self._acte(alie.pk, 'aturar').status_code, 404)
        alie.refresh_from_db()
        self.assertEqual(alie.estat, TenantLink.ESTAT_ACTIU)   # intacte


# ── L'assignació: la segona clau, i el pont que la desmenteix ───────────────────
class AssignarRecursTest(RecursosBase):

    def setUp(self):
        super().setUp()
        self.link = TenantLink.objects.create(
            brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)
        Model.objects.all().delete()
        self.models = [
            Model.objects.create(codi_intern=f'BRD-SS27-{i:04d}', codi_tenant=BRAND,
                                 any=2027, temporada='SS', sequencial=i, nom_prenda=f'M{i}')
            for i in range(1, 6)
        ]

    def _ids(self, n):
        return [m.id for m in self.models[:n]]

    def test_assigna_en_bloc(self):
        res = self._assignar({'model_ids': self._ids(3), 'studio_codi': STUDIO})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['assignats'], 3)
        self.assertEqual(Model.objects.filter(studio_assignat=STUDIO).count(), 3)

    def test_repetir_no_infla_el_compte(self):
        self._assignar({'model_ids': self._ids(3), 'studio_codi': STUDIO})
        res = self._assignar({'model_ids': self._ids(3), 'studio_codi': STUDIO})
        self.assertEqual(res.data['assignats'], 0)     # cap CANVI
        self.assertEqual(res.data['ja_hi_eren'], 3)

    def test_retirar_amb_codi_buit(self):
        self._assignar({'model_ids': self._ids(3), 'studio_codi': STUDIO})
        self._assignar({'model_ids': self._ids(3), 'studio_codi': ''})
        self.assertEqual(Model.objects.filter(studio_assignat=STUDIO).count(), 0)

    def test_assignar_amb_vincle_aturat_es_409(self):
        self.link.aturar()
        res = self._assignar({'model_ids': self._ids(3), 'studio_codi': STUDIO})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data['code'], 'link_not_active')
        self.assertEqual(Model.objects.filter(studio_assignat=STUDIO).count(), 0)   # res escrit

    def test_retirar_funciona_encara_que_el_pont_estigui_tancat(self):
        self._assignar({'model_ids': self._ids(3), 'studio_codi': STUDIO})
        self.link.revocar()
        res = self._assignar({'model_ids': self._ids(3), 'studio_codi': ''})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Model.objects.filter(studio_assignat=STUDIO).count(), 0)

    def test_studio_sense_vincle_es_400(self):
        res = self._assignar({'model_ids': self._ids(1), 'studio_codi': 'ZZZ'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['code'], 'link_missing')

    def test_model_ids_buit_es_400(self):
        self.assertEqual(self._assignar({'model_ids': [], 'studio_codi': STUDIO}).status_code, 400)

    def test_ids_inexistents_es_reporten_no_es_silencien(self):
        res = self._assignar({'model_ids': self._ids(1) + [999999], 'studio_codi': STUDIO})
        self.assertEqual(res.data['assignats'], 1)
        self.assertEqual(res.data['no_trobats'], [999999])
