"""Tests del tenant-discovery (porta única).

Cobreix el requisit dur: email en 1 tenant, en 0 tenants, en >1 tenant → la resposta HTTP
pública ha de ser INDISTINGIBLE en els tres casos. A més: el correu només s'envia si l'email
existeix (best-effort, via mail.outbox), i el throttle frena l'enumeració per volum.

Es crea un SEGON schema real (a més del 'test' de TenantTestCase) per al cas ">1".
"""
import datetime

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context
from rest_framework.test import APIRequestFactory

from fhort.tenants.models import Client, Domain
from fhort.tenants.discovery_service import find_workspaces_for_email
from fhort.tenants.views_discovery import TenantDiscoveryView, DISCOVERY_UNIFORM_DETAIL


class TenantDiscoveryTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Tenant U'
        tenant.tipologia = 'marca'
        tenant.codi_tenant = 'TU1'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'b2b'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Segon tenant amb schema real (per al cas ">1 tenant"). Es crea des de PUBLIC.
        connection.set_schema_to_public()
        cls.tenant2 = Client(schema_name='ws2', nom='Tenant Dos', tipologia='marca',
                             codi_tenant='TU2', vat_number='X0000001X', tipus_client='b2b',
                             gratis_fins=datetime.date(2030, 1, 1))
        cls.tenant2.save(verbosity=0)
        cls.domain2 = Domain(tenant=cls.tenant2, domain='ws2.test.com', is_primary=True)
        cls.domain2.save()
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.domain2.delete()
        cls.tenant2.delete(force_drop=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()   # reinicia el comptador del throttle entre tests (LocMemCache persistent)
        User = get_user_model()
        # single@ → només al tenant 'test'; multi@ → als DOS; none@ → enlloc.
        with schema_context(self.tenant.schema_name):
            User.objects.create_user(username='single@x.com', email='single@x.com', password='pw123456')
            User.objects.create_user(username='multi@x.com', email='multi@x.com', password='pw123456')
        with schema_context(self.tenant2.schema_name):
            User.objects.create_user(username='multi@x.com', email='multi@x.com', password='pw123456')

    def _post(self, email):
        req = APIRequestFactory().post('/api/discovery/', {'email': email}, format='json')
        return TenantDiscoveryView.as_view()(req)

    # ── Servei cross-schema: 1 / 0 / >1 ──────────────────────────────────────
    def test_service_single_tenant(self):
        ws = find_workspaces_for_email('single@x.com')
        self.assertEqual([w['schema'] for w in ws], [self.tenant.schema_name])

    def test_service_no_tenant(self):
        self.assertEqual(find_workspaces_for_email('none@x.com'), [])

    def test_service_multi_tenant(self):
        ws = find_workspaces_for_email('multi@x.com')
        self.assertCountEqual([w['schema'] for w in ws],
                              [self.tenant.schema_name, self.tenant2.schema_name])

    def test_service_email_iexact(self):
        # Coherent amb EmailOrUsernameBackend: la cerca és case-insensitive.
        self.assertEqual(len(find_workspaces_for_email('SINGLE@X.COM')), 1)

    # ── Resposta HTTP INDISTINGIBLE en els 3 casos ───────────────────────────
    def test_response_uniform_across_cases(self):
        r1 = self._post('single@x.com')
        r0 = self._post('none@x.com')
        rN = self._post('multi@x.com')
        for r in (r1, r0, rN):
            self.assertEqual(r.status_code, 200)
        self.assertEqual(r1.data, r0.data)
        self.assertEqual(r0.data, rN.data)
        self.assertEqual(r1.data['detail'], DISCOVERY_UNIFORM_DETAIL)

    def test_missing_email_400(self):
        r = self._post('')
        self.assertEqual(r.status_code, 400)

    # ── Correu best-effort: només si existeix, i selector si >1 ──────────────
    def test_email_only_when_exists(self):
        mail.outbox = []
        self._post('none@x.com')
        self.assertEqual(len(mail.outbox), 0)
        self._post('single@x.com')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['single@x.com'])

    def test_email_multi_te_selector(self):
        mail.outbox = []
        self._post('multi@x.com')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].body.count('/login'), 2)   # un enllaç per workspace

    # ── Throttle: frena l'enumeració per volum ───────────────────────────────
    def test_throttle_kicks_in(self):
        # 10/hour → la 11a petició des de la mateixa IP és 429.
        codes = [self._post('none@x.com').status_code for _ in range(11)]
        self.assertTrue(all(c == 200 for c in codes[:10]), codes)
        self.assertEqual(codes[10], 429)
