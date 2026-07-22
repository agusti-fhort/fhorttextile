"""Login únic — autenticació central cross-schema (F1) i bescanvi al tenant (F2).

Les lleis que defensen:

  · UNA PORTA, CAP ORACLE. Un email que no existeix i una contrasenya dolenta han de tornar
    exactament la mateixa resposta. La porta és pública: si distingeix, enumera comptes.
  · UN CODI, UN SOL ÚS. El consum és un UPDATE condicional; dues carreres pel mateix codi
    han de deixar exactament una sessió.
  · UN CODI, UN SOL TENANT. La lliçó de F0 un pis més amunt: un codi emès per a un schema
    presentat a un altre no val — si valgués, seria el mateix forat d'intercanviabilitat que
    F0 va tancar per al JWT.
  · LA CONTRASENYA VIATJA UN COP. Amb multi-workspace, la tria va amb un tiquet efímer.

Es munten DOS tenants reals amb el MATEIX email i la MATEIXA contrasenya: el cas
multi-workspace no és una hipòtesi de test, és la condició real que es reprodueix aquí.

    cd backend && venv/bin/python manage.py test fhort.tenants.tests_login_unic
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.urls import Resolver404, resolve
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import get_tenant_model, schema_context
from rest_framework_simplejwt.tokens import AccessToken

from fhort.auth_jwt import TENANT_CLAIM
from fhort.tenants.auth_central_service import (
    autentica_cross_schema,
    consumeix_codi,
    emet_codi,
    resol_host,
)
from fhort.tenants.models import CodiAuth

User = get_user_model()

EMAIL = 'compartit@exemple.com'
PASSWORD = 'una-contrasenya-prou-llarga-9'


class LoginUnicTest(TenantTestCase):
    """F1 + F2 sencers, amb dos schemas de tenant i un usuari a cadascun."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Espai A'
        tenant.codi_tenant = 'EA'
        tenant.email_facturacio = 'a@x.com'
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Segon tenant real amb domini propi: el multi-workspace i el creuament de schemas
        # necessiten un germà de debò, no un mock.
        connection.set_schema_to_public()
        Client = get_tenant_model()
        cls.tenant_b = Client(
            schema_name='tb', nom='Espai B', codi_tenant='EB', email_facturacio='b@x.com',
        )
        cls.tenant_b.save(verbosity=0)
        cls.tenant_b.domains.create(domain='tb.test.com', is_primary=True)
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.tenant_b.delete(force_drop=True)
        super().tearDownClass()

    def setUp(self):
        self.client = TenantClient(self.tenant)
        cache.clear()   # el throttle és de cache: sense això un test en condiciona un altre
        with schema_context('public'):
            CodiAuth.objects.all().delete()
        self.usuaris = {}
        for schema in (self.tenant.schema_name, 'tb'):
            with schema_context(schema):
                u, _ = User.objects.get_or_create(username=EMAIL, defaults={'email': EMAIL})
                u.is_active = True
                u.set_password(PASSWORD)
                u.save()
                self.usuaris[schema] = u.pk

    # ── utillatge ────────────────────────────────────────────────────────────
    def _nomes_a(self, schema):
        """Deixa l'email viu NOMÉS a `schema` (per als casos de match únic)."""
        for altre in (self.tenant.schema_name, 'tb'):
            if altre != schema:
                with schema_context(altre):
                    User.objects.filter(pk=self.usuaris[altre]).delete()

    def _central(self, email=EMAIL, password=PASSWORD):
        return self.client.post('/api/auth/central/',
                                {'email': email, 'password': password},
                                content_type='application/json')

    def _bescanvi(self, code):
        return self.client.post('/api/auth/bescanvi/', {'code': code},
                                content_type='application/json')

    def _codi_per(self, schema):
        return emet_codi(CodiAuth.MENA_BESCANVI,
                         tenant_schema=schema, user_id=self.usuaris[schema])

    def _envelleix(self, segons):
        with schema_context('public'):
            CodiAuth.objects.all().update(
                created_at=timezone.now() - timedelta(seconds=segons))

    # ══ F1 · autenticació central ════════════════════════════════════════════
    def test_match_unic_emet_codi_de_bescanvi(self):
        self._nomes_a(self.tenant.schema_name)
        r = self._central()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['mena'], 'codi')
        self.assertTrue(r.json()['code'])
        self.assertEqual(r.json()['workspace']['schema'], self.tenant.schema_name)
        self.assertEqual(r.json()['workspace']['nom'], 'Espai A')

    def test_multi_match_llista_workspaces_i_no_emet_cap_codi(self):
        """Amb dos espais, un sol login NO pot obrir-ne dos: primer es tria."""
        r = self._central()
        self.assertEqual(r.status_code, 200)
        dades = r.json()
        self.assertEqual(dades['mena'], 'seleccio')
        self.assertNotIn('code', dades)
        self.assertEqual({w['schema'] for w in dades['workspaces']},
                         {self.tenant.schema_name, 'tb'})
        self.assertTrue(dades['seleccio'])
        with schema_context('public'):
            self.assertFalse(CodiAuth.objects.filter(mena=CodiAuth.MENA_BESCANVI).exists())

    def test_email_inexistent_i_contrasenya_dolenta_son_INDISTINGIBLES(self):
        """El requisit dur de la porta: cap diferència entre els dos fracassos."""
        inexistent = self._central(email='ningu@exemple.com')
        dolenta = self._central(password='no-es-aquesta')
        self.assertEqual(inexistent.status_code, 401)
        self.assertEqual(dolenta.status_code, 401)
        self.assertEqual(inexistent.json(), dolenta.json())
        self.assertEqual(inexistent.content, dolenta.content)

    def test_usuari_desactivat_no_es_credencial_valida(self):
        self._nomes_a(self.tenant.schema_name)
        with schema_context(self.tenant.schema_name):
            User.objects.filter(pk=self.usuaris[self.tenant.schema_name]).update(is_active=False)
        self.assertEqual(self._central().status_code, 401)

    def test_falten_camps(self):
        self.assertEqual(self._central(password='').status_code, 400)
        self.assertEqual(self._central(email='').status_code, 400)

    def test_el_throttle_frena_la_porta(self):
        """És la superfície on es proven contrasenyes: sense fre és credential stuffing."""
        vistos = {self._central(password='dolenta').status_code for _ in range(21)}
        self.assertIn(429, vistos)

    def test_la_porta_central_es_a_TOTS_DOS_urlconfs(self):
        """Al public (host neutre de PROD) i al tenant (validació visual a staging, S19)."""
        for urlconf in ('fhort.urls_public', 'fhort.urls'):
            with self.subTest(urlconf=urlconf):
                self.assertEqual(resolve('/api/auth/central/', urlconf=urlconf).url_name,
                                 'auth-central')
                self.assertEqual(resolve('/api/auth/central/tria/', urlconf=urlconf).url_name,
                                 'auth-central-tria')

    def test_el_codi_no_es_desa_en_clar(self):
        self._nomes_a(self.tenant.schema_name)
        codi = self._central().json()['code']
        with schema_context('public'):
            self.assertFalse(CodiAuth.objects.filter(codi_hash=codi).exists())
            self.assertEqual(CodiAuth.objects.count(), 1)

    # ══ F1 · la tria (multi-workspace) ═══════════════════════════════════════
    def _tria(self, seleccio, schema):
        return self.client.post('/api/auth/central/tria/',
                                {'seleccio': seleccio, 'schema': schema},
                                content_type='application/json')

    def test_la_tria_dona_el_codi_del_workspace_triat(self):
        seleccio = self._central().json()['seleccio']
        r = self._tria(seleccio, 'tb')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['workspace']['schema'], 'tb')
        self.assertTrue(r.json()['code'])

    def test_la_tria_nomes_val_per_als_schemas_que_van_validar(self):
        """Un tiquet legítim no pot ser una clau mestra cap a qualsevol tenant."""
        seleccio = emet_codi(CodiAuth.MENA_SELECCIO,
                             candidats=[{'schema': self.tenant.schema_name,
                                         'user_id': self.usuaris[self.tenant.schema_name]}])
        self.assertEqual(self._tria(seleccio, 'tb').status_code, 401)

    def test_el_tiquet_de_seleccio_tambe_es_d_un_sol_us(self):
        seleccio = self._central().json()['seleccio']
        self.assertEqual(self._tria(seleccio, 'tb').status_code, 200)
        self.assertEqual(self._tria(seleccio, 'tb').status_code, 401)

    # ══ F2 · bescanvi al host del tenant ═════════════════════════════════════
    def test_bescanvi_valid_dona_el_parell_jwt_amb_el_claim_correcte(self):
        codi = self._codi_per(self.tenant.schema_name)
        r = self._bescanvi(codi)
        self.assertEqual(r.status_code, 200)
        dades = r.json()
        self.assertIn('access', dades)
        self.assertIn('refresh', dades)
        payload = AccessToken(dades['access']).payload
        self.assertEqual(payload[TENANT_CLAIM], self.tenant.schema_name)
        self.assertEqual(str(payload['user_id']), str(self.usuaris[self.tenant.schema_name]))

    def test_el_codi_usat_dos_cops_nomes_val_el_primer(self):
        codi = self._codi_per(self.tenant.schema_name)
        self.assertEqual(self._bescanvi(codi).status_code, 200)
        self.assertEqual(self._bescanvi(codi).status_code, 401)

    def test_codi_caducat(self):
        codi = self._codi_per(self.tenant.schema_name)
        self._envelleix(CodiAuth.TTL_BESCANVI.total_seconds() + 5)
        self.assertEqual(self._bescanvi(codi).status_code, 401)

    def test_codi_d_un_altre_schema_no_val_aqui(self):
        """La lliçó de F0: un codi de `tb` presentat al host d'`A` no obre res."""
        codi = self._codi_per('tb')
        self.assertEqual(self._bescanvi(codi).status_code, 401)

    def test_usuari_desactivat_entre_emissio_i_bescanvi(self):
        codi = self._codi_per(self.tenant.schema_name)
        with schema_context(self.tenant.schema_name):
            User.objects.filter(pk=self.usuaris[self.tenant.schema_name]).update(is_active=False)
        self.assertEqual(self._bescanvi(codi).status_code, 401)

    def test_codi_inexistent(self):
        self.assertEqual(self._bescanvi('no-existeixo').status_code, 401)
        self.assertEqual(self._bescanvi('').status_code, 401)

    def test_tots_els_fracassos_del_bescanvi_tenen_la_mateixa_cara(self):
        caducat = self._codi_per(self.tenant.schema_name)
        self._envelleix(CodiAuth.TTL_BESCANVI.total_seconds() + 5)
        respostes = [
            self._bescanvi(caducat),
            self._bescanvi(self._codi_per('tb')),
            self._bescanvi('inventat'),
        ]
        self.assertEqual({r.status_code for r in respostes}, {401})
        self.assertEqual(len({r.content for r in respostes}), 1)

    def test_el_bescanvi_NO_es_al_public(self):
        """Ha d'emetre'l el host del tenant: és el que fa que la sessió neixi same-origin."""
        with self.assertRaises(Resolver404):
            resolve('/api/auth/bescanvi/', urlconf='fhort.urls_public')
        self.assertEqual(resolve('/api/auth/bescanvi/', urlconf='fhort.urls').url_name,
                         'auth-bescanvi')

    # ══ La cursa del doble bescanvi ══════════════════════════════════════════
    def test_dos_consums_del_mateix_codi_deixen_exactament_un_exit(self):
        """Simulació de la cursa amb el WHERE condicional.

        Els dos «fils» llegeixen la fila i la veuen VIVA (és el moment en què un
        comprova-i-després-marca hauria deixat passar tots dos). Després tots dos consumeixen:
        el veredicte no és la lectura, és el nombre de files que l'UPDATE afecta.
        """
        codi = self._codi_per(self.tenant.schema_name)
        with schema_context('public'):
            fila = CodiAuth.objects.get(tenant_schema=self.tenant.schema_name)
            self.assertIsNone(fila.used_at)                                # fil 1 la veu viva
            self.assertIsNone(CodiAuth.objects.get(pk=fila.pk).used_at)    # fil 2 també

        resultats = [consumeix_codi(codi, CodiAuth.MENA_BESCANVI),
                     consumeix_codi(codi, CodiAuth.MENA_BESCANVI)]
        self.assertEqual(sum(1 for r in resultats if r is not None), 1)

    # ══ Servei: host de destí i lookup ═══════════════════════════════════════
    def test_el_host_de_desti_prefereix_aquell_des_del_qual_s_entra(self):
        """Regla que sosté la validació a staging: el primari de `fhort` és PROD."""
        with schema_context('public'):
            self.tenant.domains.create(domain='segon.test.com', is_primary=False)
        self.assertEqual(resol_host(self.tenant.schema_name, 'segon.test.com'),
                         'segon.test.com')
        self.assertEqual(resol_host(self.tenant.schema_name, 'un-altre.example'),
                         self.tenant.get_primary_domain().domain)

    def test_autentica_cross_schema_retorna_tots_els_espais_valids(self):
        valids = autentica_cross_schema(EMAIL, PASSWORD)
        self.assertEqual({v['schema'] for v in valids}, {self.tenant.schema_name, 'tb'})
        self.assertEqual(autentica_cross_schema(EMAIL, 'dolenta'), [])
        self.assertEqual(autentica_cross_schema('ningu@x.com', PASSWORD), [])
