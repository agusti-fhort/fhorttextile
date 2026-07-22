"""F0 — el JWT està lligat a l'schema que l'ha emès.

La llei que defensen: UN TOKEN NOMÉS VAL A CASA SEVA. Abans d'aquest canvi, un token
emès al tenant `fhort` per l'usuari id=1 era acceptat al schema `public` com un usuari
DIFERENT — el superusuari (prova empírica de DIAGNOSI_LOGIN_UNIC_2026-07-22 §B3.1). La
causa: `auth_user` és per-schema amb PKs independents que comencen a l'1, i el token només
duia `user_id`; l'schema el fixava el Host.

Els tests munten TRES schemas reals amb un usuari id=1 a cadascun — la col·lisió de PK no
és hipotètica, és la condició que es reprodueix aquí.

    cd backend && venv/bin/python manage.py test fhort.tests_auth_jwt
"""
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_model, schema_context
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from fhort.auth_jwt import (
    TENANT_CLAIM,
    TenantJWTAuthentication,
    TenantTokenObtainPairSerializer,
)

User = get_user_model()


class ClaimDeTenantTest(TenantTestCase):
    """Emissió, validació i invalidació neta del claim `tenant_schema`."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Tenant A'
        tenant.codi_tenant = 'TA'
        tenant.email_facturacio = 'a@x.com'
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Segon tenant real: cal un schema germà per provar el creuament tenant↔tenant.
        # Es crea des de PUBLIC (django-tenants no permet crear tenants des d'un tenant).
        connection.set_schema_to_public()
        Client = get_tenant_model()
        cls.tenant_b = Client(
            schema_name='tb', nom='Tenant B', codi_tenant='TB', email_facturacio='b@x.com',
        )
        cls.tenant_b.save(verbosity=0)
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.tenant_b.delete(force_drop=True)
        super().tearDownClass()

    def setUp(self):
        # Un usuari a CADA schema. Els tres agafen pk=1 al seu schema: la col·lisió de PK
        # que feia possible la suplantació queda reproduïda a posta.
        self.usuaris = {}
        for schema in (self.tenant.schema_name, 'tb', 'public'):
            with schema_context(schema):
                u, _ = User.objects.get_or_create(
                    username=f'usuari@{schema}.com',
                    defaults={'email': f'usuari@{schema}.com'},
                )
                self.usuaris[schema] = u.pk

    # ── utillatge ────────────────────────────────────────────────────────────
    def _emet(self, schema):
        """Token emès DES DE `schema`, pel camí real d'emissió (el serializer)."""
        with schema_context(schema):
            user = User.objects.get(pk=self.usuaris[schema])
            return str(TenantTokenObtainPairSerializer.get_token(user).access_token)

    def _valida(self, token, schema):
        """Valida `token` com si la petició hagués entrat pel Host de `schema`."""
        with schema_context(schema):
            return TenantJWTAuthentication().get_validated_token(token)

    def _assert_rebutjat(self, token, schema, missatge):
        with self.assertRaises(InvalidToken, msg=missatge):
            self._valida(token, schema)

    # ── C1 · emissió ─────────────────────────────────────────────────────────
    def test_el_token_porta_el_schema_que_l_ha_emes(self):
        for schema in (self.tenant.schema_name, 'tb', 'public'):
            with self.subTest(schema=schema):
                payload = AccessToken(self._emet(schema)).payload
                self.assertEqual(payload[TENANT_CLAIM], schema)

    def test_el_refresh_tambe_porta_el_claim(self):
        with schema_context('tb'):
            user = User.objects.get(pk=self.usuaris['tb'])
            refresh = TenantTokenObtainPairSerializer.get_token(user)
        self.assertEqual(refresh.payload[TENANT_CLAIM], 'tb')

    # ── C4 · creuament: cada schema contra els altres dos ────────────────────
    def test_token_de_tenant_rebutjat_als_altres_schemas(self):
        token = self._emet(self.tenant.schema_name)
        self._assert_rebutjat(token, 'tb', 'un token de tenant no pot entrar a un altre tenant')
        self._assert_rebutjat(token, 'public', 'un token de tenant no pot entrar al public')

    def test_token_de_public_rebutjat_als_tenants(self):
        token = self._emet('public')
        self._assert_rebutjat(token, self.tenant.schema_name, 'el backoffice no és excepció')
        self._assert_rebutjat(token, 'tb', 'el backoffice no és excepció')

    def test_token_del_segon_tenant_rebutjat_arreu(self):
        token = self._emet('tb')
        self._assert_rebutjat(token, self.tenant.schema_name, 'creuament tenant→tenant')
        self._assert_rebutjat(token, 'public', 'creuament tenant→public')

    # ── C4 · el cas legítim segueix funcionant ───────────────────────────────
    def test_cada_schema_accepta_el_seu_propi_token(self):
        for schema in (self.tenant.schema_name, 'tb', 'public'):
            with self.subTest(schema=schema):
                validat = self._valida(self._emet(schema), schema)
                self.assertEqual(validat[TENANT_CLAIM], schema)

    def test_l_usuari_autenticat_es_el_del_seu_schema(self):
        """El camí sencer: token → usuari. Ha de resoldre DINS del seu schema."""
        for schema in (self.tenant.schema_name, 'tb', 'public'):
            with self.subTest(schema=schema):
                with schema_context(schema):
                    auth = TenantJWTAuthentication()
                    user = auth.get_user(auth.get_validated_token(self._emet(schema)))
                    self.assertEqual(user.username, f'usuari@{schema}.com')

    # ── C3 · invalidació neta: els tokens vells cauen sols ───────────────────
    def test_token_sense_claim_rebutjat_a_tot_arreu(self):
        """Un token PRE-DEPLOY: emès pel camí antic, sense `tenant_schema`.

        No cal cap codi de migració — `payload.get(TENANT_CLAIM)` torna None i mai
        coincideix amb cap schema. La invalidació és automàtica.
        """
        with schema_context(self.tenant.schema_name):
            vell = AccessToken.for_user(User.objects.get(pk=self.usuaris[self.tenant.schema_name]))
        self.assertNotIn(TENANT_CLAIM, vell.payload)   # és de debò un token de l'era antiga
        for schema in (self.tenant.schema_name, 'tb', 'public'):
            with self.subTest(schema=schema):
                self._assert_rebutjat(str(vell), schema, 'cap token sense claim sobreviu')

    def test_claim_manipulat_no_cola(self):
        """Un token amb el claim canviat a mà: la signatura ja no lliga."""
        with schema_context(self.tenant.schema_name):
            t = TenantTokenObtainPairSerializer.get_token(
                User.objects.get(pk=self.usuaris[self.tenant.schema_name])).access_token
        t.payload[TENANT_CLAIM] = 'public'   # reescriu el claim i re-signa amb la MATEIXA clau
        self._assert_rebutjat(str(t), self.tenant.schema_name, 'el claim reescrit no val al seu origen')
        # I al schema que pretén ser, tampoc: el token diu 'public' i s'hi validaria… però
        # l'usuari 1 de public NO és el de fhort. Aquesta és la fuga original; ara el claim
        # és part de la signatura, així que reescriure'l només és possible amb la SECRET_KEY.
        with schema_context('public'):
            user = TenantJWTAuthentication().get_user(
                TenantJWTAuthentication().get_validated_token(str(t)))
            self.assertEqual(user.username, 'usuari@public.com')

    # ── C1 · el refresh PRESERVA, no recalcula ───────────────────────────────
    def test_el_refresh_conserva_el_schema_original(self):
        """Un refresh que arriba per un Host equivocat no es re-deriva.

        El claim viatja amb el token. Si es recalculés amb `connection.schema_name`, un
        refresh presentat a l'schema equivocat en sortiria legitimat — exactament el forat
        que aquest sprint tanca.
        """
        with schema_context(self.tenant.schema_name):
            refresh = TenantTokenObtainPairSerializer.get_token(
                User.objects.get(pk=self.usuaris[self.tenant.schema_name]))
        # El refresh es presenta DES D'UN ALTRE schema (Host equivocat):
        with schema_context('public'):
            nou = RefreshToken(str(refresh)).access_token
        self.assertEqual(nou[TENANT_CLAIM], self.tenant.schema_name)
        self._assert_rebutjat(str(nou), 'public', 'el refresh no legitima un canvi de schema')
        self.assertIsNotNone(self._valida(str(nou), self.tenant.schema_name))

    # ── La prova empírica de la diagnosi, reproduïda ─────────────────────────
    def test_reproduccio_de_la_fuga_de_la_diagnosi(self):
        """§B3.1: token de `fhort` id=1 → acceptat a `public` com el SUPERUSUARI.

        Es recrea la condició exacta: mateix pk als dos schemas, i al public aquest pk és
        un superusuari. Abans, `JWTAuthentication` l'hauria retornat. Ara ha de rebotar.
        """
        with schema_context('public'):
            root = User.objects.get(pk=self.usuaris['public'])
            root.is_superuser = root.is_staff = True
            root.save(update_fields=['is_superuser', 'is_staff'])

        token = self._emet(self.tenant.schema_name)
        pk_origen = AccessToken(token).payload['user_id']
        self.assertEqual(str(pk_origen), str(self.usuaris['public']),
                         'sense col·lisió de PK la prova no demostraria res')

        # El camí antic (la llibreria nua) encara entregaria el superusuari:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        with schema_context('public'):
            suplantat = JWTAuthentication().get_user(JWTAuthentication().get_validated_token(token))
            self.assertTrue(suplantat.is_superuser, 'la fuga original era real')

        # El camí actual el rebutja abans de tocar la BD:
        self._assert_rebutjat(token, 'public', 'LA FUGA DE LA DIAGNOSI HA DE SER MORTA')

    def test_l_schema_actiu_no_es_filtra_a_l_error(self):
        """L'error no pot dir per què ha fallat: seria un oracle d'enumeració d'schemas."""
        with self.assertRaises(InvalidToken) as ctx:
            self._valida(self._emet('tb'), 'public')
        text = str(ctx.exception.detail).lower()
        for pista in ('tb', 'public', 'schema', 'tenant'):
            self.assertNotIn(pista, text, f"l'error filtra «{pista}»")
