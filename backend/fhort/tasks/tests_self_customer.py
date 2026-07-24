"""El customer propi (is_self) en tenants Marca vs Estudi.

Dues coses hi conviuen i es proven aquí:

1. `tipologia` arriba al frontend (TenantConfig) — és el discriminador que fa servir la pàgina
   Clients per decidir si envia `exclude_self`. Un ESTUDI amaga el client propi (allà és
   fontaneria del sistema); una MARCA l'ha de veure (és casa del seu propi patrimoni), que si no
   una Marca que només té el seu self veu la pàgina Clients BUIDA.

2. El blindatge del client propi: ni s'esborra ni es desactiva, i el blindatge és del BACKEND
   (amagar botons és cortesia). Error amb `code` discriminant (patró DA-30) perquè el frontend
   no hagi de fer match sobre el text del missatge.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.tasks.models import Customer
from fhort.tasks.views_b import CustomerViewSet, SELF_CUSTOMER_PROTEGIT
from fhort.pom.s2_views import tenant_config_view


class SelfCustomerBase(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'estudi'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        self.factory = APIRequestFactory()
        # admin → té CONFIGURE, que és el que gateja l'escriptura del CustomerViewSet. Sense
        # perfil el permís talla amb 403 i no s'arribaria mai a provar el blindatge.
        self.user = get_user_model().objects.create_user('admin@test.local', password='x')
        # El signal post_save(User) ja crea el perfil amb el rol per defecte ('technician'), de
        # manera que els `defaults` d'un get_or_create no hi entrarien: cal promocionar-lo a mà.
        prof, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Admin', 'rol_nom': 'admin'})
        prof.rol_nom = 'admin'
        prof.save(update_fields=['rol_nom'])
        # …i rellegir l'usuari: el signal va deixar el perfil VELL cachejat a `user.profile`, que
        # és d'on llegeix get_capabilities() → sense això el gate CONFIGURE respon 403.
        self.user = get_user_model().objects.get(pk=self.user.pk)
        # La migració 0020 ja sembra el customer propi; agafar-lo evita dependre'n de l'ordre.
        self.self_cu = Customer.objects.filter(is_self=True).first() \
            or Customer.objects.create(codi='TST', nom='Tenant propi', is_self=True)
        self.altre = Customer.objects.create(codi='CLI', nom='Client normal')

    def _crida(self, req, **kwargs):
        force_authenticate(req, user=self.user)
        req.tenant = self.tenant
        return req, kwargs


# ── 1. tipologia al frontend ────────────────────────────────────────────────────
class TipologiaExposadaTest(SelfCustomerBase):

    def _get_config(self):
        req = self.factory.get('/api/v1/tenant-config/')
        force_authenticate(req, user=self.user)
        req.tenant = self.tenant
        return tenant_config_view(req)

    def test_tipologia_surt_al_tenant_config(self):
        self.tenant.tipologia = 'estudi'
        self.assertEqual(self._get_config().data['tipologia'], 'estudi')

    def test_tipologia_marca_surt_al_tenant_config(self):
        self.tenant.tipologia = 'marca'
        self.assertEqual(self._get_config().data['tipologia'], 'marca')

    def test_tipologia_no_es_editable_des_del_tenant(self):
        """La governa el backoffice (schema públic); el PATCH del tenant l'ha d'ignorar."""
        self.tenant.tipologia = 'estudi'
        req = self.factory.patch('/api/v1/tenant-config/', {'tipologia': 'marca'}, format='json')
        force_authenticate(req, user=self.user)
        req.tenant = self.tenant
        self.assertEqual(tenant_config_view(req).data['tipologia'], 'estudi')
        self.assertEqual(self.tenant.tipologia, 'estudi')


# ── 2. exclude_self: els dos camins del llistat ─────────────────────────────────
class ExcludeSelfTest(SelfCustomerBase):

    def _list(self, params=None):
        req = self.factory.get('/api/v1/customers/', params or {})
        force_authenticate(req, user=self.user)
        req.tenant = self.tenant
        res = CustomerViewSet.as_view({'get': 'list'})(req)
        rows = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        return {r['codi'] for r in rows}

    def test_estudi_amaga_el_self(self):
        """Camí ESTUDI — la pàgina envia el filtre: el self no hi surt."""
        codis = self._list({'exclude_self': 'true'})
        self.assertNotIn(self.self_cu.codi, codis)
        self.assertIn(self.altre.codi, codis)

    def test_marca_veu_el_self(self):
        """Camí MARCA — la pàgina NO envia el filtre: el self hi surt amb els altres."""
        codis = self._list()
        self.assertIn(self.self_cu.codi, codis)
        self.assertIn(self.altre.codi, codis)

    def test_marca_amb_nomes_el_self_no_veu_la_llista_buida(self):
        """El bug original: una Marca que només té el seu self veia la pàgina Clients buida."""
        self.altre.delete()
        self.assertEqual(self._list(), {self.self_cu.codi})
        self.assertEqual(self._list({'exclude_self': 'true'}), set())   # el que passava abans


# ── 3. blindatge del client propi ───────────────────────────────────────────────
class BlindatgeSelfTest(SelfCustomerBase):

    def _delete(self, cu):
        req = self.factory.delete(f'/api/v1/customers/{cu.pk}/')
        force_authenticate(req, user=self.user)
        req.tenant = self.tenant
        return CustomerViewSet.as_view({'delete': 'destroy'})(req, pk=cu.pk)

    def _patch(self, cu, payload):
        req = self.factory.patch(f'/api/v1/customers/{cu.pk}/', payload, format='json')
        force_authenticate(req, user=self.user)
        req.tenant = self.tenant
        return CustomerViewSet.as_view({'patch': 'partial_update'})(req, pk=cu.pk)

    def test_no_es_pot_esborrar_el_self(self):
        res = self._delete(self.self_cu)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data['code'], SELF_CUSTOMER_PROTEGIT)
        self.assertTrue(Customer.objects.filter(pk=self.self_cu.pk).exists())

    def test_no_es_pot_desactivar_el_self(self):
        res = self._patch(self.self_cu, {'active': False})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data['code'], SELF_CUSTOMER_PROTEGIT)
        self.self_cu.refresh_from_db()
        self.assertTrue(self.self_cu.active)

    def test_el_self_segueix_essent_editable(self):
        """El blindatge és quirúrgic: bloqueja esborrat i desactivació, no l'edició."""
        res = self._patch(self.self_cu, {'nom': 'Nom nou'})
        self.assertEqual(res.status_code, 200)
        self.self_cu.refresh_from_db()
        self.assertEqual(self.self_cu.nom, 'Nom nou')

    def test_is_self_no_es_pot_desarmar_amb_un_patch(self):
        """Si `is_self` fos escrivible, n'hi hauria prou amb desarmar-lo per saltar el blindatge."""
        res = self._patch(self.self_cu, {'is_self': False})
        self.assertEqual(res.status_code, 200)
        self.self_cu.refresh_from_db()
        self.assertTrue(self.self_cu.is_self)
        self.assertEqual(self._delete(self.self_cu).status_code, 409)

    def test_un_client_normal_segueix_essent_esborrable_i_desactivable(self):
        """Cap regressió: el blindatge només toca el self."""
        self.assertEqual(self._patch(self.altre, {'active': False}).status_code, 200)
        self.assertEqual(self._delete(self.altre).status_code, 204)
        self.assertFalse(Customer.objects.filter(pk=self.altre.pk).exists())
