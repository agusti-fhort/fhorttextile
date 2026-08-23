"""L'EDICIÓ D'UN ÀLIES DE LA BIBLIOTECA DE NOMENCLATURA (23/08/2026).

Substrat: `PATCH /api/v1/customer-pom-aliases/<id>/` ja existia —`CustomerPOMAliasViewSet` és un
`ModelViewSet` sencer i `partial_update` ja demanava CONFIGURE, igual que l'alta—, o sigui que
aquest tram **no obre cap porta nova**: el que hi afegeix són les dues lleis que l'edició ha de
complir i que fins avui ningú feia complir.

  · `EdicioAliesTest`        — el camí bo: es desa, `editat_at` s'estampa i l'`origen` es queda.
  · `CodiImmutableTest`      — 🔒 el `client_code` és la IDENTITAT i el servidor el defensa.
  · `PermisEdicioTest`       — la mateixa permission que l'alta: sense CONFIGURE, 403.

🚨 Les dues trampes conegudes de la casa hi valen: el perfil ja el crea un signal (s'ADOPTA amb
`get_or_create`) i `user.profile` CACHEJA (cal rellegir l'usuari); i el client ha d'apuntar al
DOMINI DEL TENANT o l'urlconf de `public` torna un 404.

⚠️ Cap escriptura a cap BD viva: `TenantTestCase` corre sobre una BD de test pròpia.
"""
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.accounts.models import UserProfile
from fhort.pom.models import CustomerPOMAlias, POMMaster
from fhort.tasks.models import Customer


class _BancAlies(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test edició àlies'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TEA'
        return tenant

    def setUp(self):
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')
        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Chest width',
                                            actiu=True)
        self.altre = POMMaster.objects.create(codi_client='B', nom_client='Waist width',
                                              actiu=True)
        self.alias = CustomerPOMAlias.objects.create(
            customer=self.customer, pom=self.pom, client_code='CH',
            description_en='Chest', description_local='Pit', language='ca',
            origen='IMPORT')
        self.admin = self._usuari('admin_tea', 'admin')
        self.tecnic = self._usuari('tecnic_tea', 'technician')

    def _usuari(self, username, rol):
        user = get_user_model().objects.create_user(username, password='x')
        perfil, _ = UserProfile.objects.get_or_create(
            user=user, defaults={'nom_complet': username, 'rol_nom': rol})
        perfil.rol_nom = rol
        perfil.save(update_fields=['rol_nom'])
        return get_user_model().objects.get(pk=user.pk)   # el cau de `user.profile` mataria el test

    def _client(self, user):
        c = APIClient(HTTP_HOST=self.get_test_tenant_domain())
        c.force_authenticate(user=user)
        return c

    @property
    def url(self):
        return f'/api/v1/customer-pom-aliases/{self.alias.id}/'


class EdicioAliesTest(_BancAlies):

    def test_desa_les_tres_descripcions_i_el_POM(self):
        r = self._client(self.admin).patch(self.url, {
            'description_en': 'Chest width', 'description_local': 'Ample de pit',
            'language': 'ca', 'pom': self.altre.id}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.description_en, 'Chest width')
        self.assertEqual(self.alias.description_local, 'Ample de pit')
        self.assertEqual(self.alias.pom_id, self.altre.id)

    def test_estampa_la_marca_dedicio(self):
        self.assertIsNone(self.alias.editat_at)
        r = self._client(self.admin).patch(self.url, {'description_en': 'X'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.alias.refresh_from_db()
        self.assertIsNotNone(self.alias.editat_at)
        self.assertIsNotNone(r.data.get('editat_at'))

    def test_LORIGEN_ES_CONSERVA__i_no_es_pot_reescriure(self):
        """🔑 L'origen diu D'ON VE l'àlies, no qui l'ha tocat l'últim. Un àlies d'IMPORT
        corregit a mà segueix sent d'IMPORT — també si el client envia un altre origen."""
        r = self._client(self.admin).patch(
            self.url, {'description_en': 'X', 'origen': 'MANUAL'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.origen, 'IMPORT')

    def test_no_editat_no_porta_marca(self):
        """La marca ha de distingir de debò: un àlies que ningú ha tocat la té a `NULL`."""
        altre = CustomerPOMAlias.objects.create(
            customer=self.customer, pom=self.pom, client_code='ZZ', origen='DICCIONARI')
        self.assertIsNone(altre.editat_at)


class CodiImmutableTest(_BancAlies):

    def test_canviar_el_codi_es_rebutja_amb_el_motiu(self):
        """🔒 Una pantalla no és una barana: el camp entra per HTTP i el servidor el defensa."""
        r = self._client(self.admin).patch(self.url, {'client_code': 'CH2'}, format='json')
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn('client_code', r.data)
        self.assertIn('identitat', str(r.data['client_code']).lower())
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.client_code, 'CH')

    def test_reenviar_el_MATEIX_codi_no_molesta(self):
        """Un client que reenvia la fila sencera no ha de petar: el que es barra és el CANVI."""
        r = self._client(self.admin).patch(
            self.url, {'client_code': 'CH', 'description_en': 'X'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.alias.refresh_from_db()
        self.assertEqual((self.alias.client_code, self.alias.description_en), ('CH', 'X'))


class PermisEdicioTest(_BancAlies):

    def test_sense_CONFIGURE_no_edita(self):
        r = self._client(self.tecnic).patch(self.url, {'description_en': 'X'}, format='json')
        self.assertEqual(r.status_code, 403, r.data)
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.description_en, 'Chest')

    def test_la_LECTURA_segueix_oberta(self):
        r = self._client(self.tecnic).get('/api/v1/customer-pom-aliases/',
                                          {'customer': self.customer.id})
        self.assertEqual(r.status_code, 200, r.data)
