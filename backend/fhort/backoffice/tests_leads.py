"""Leads (P-LEADS) — formulari públic de la web de marketing.

L1: model + porta pública (throttle, honeypot, guarda de muntatge a `public`).
L2: avís per correu (adormit fins que hi hagi SMTP real).
L3 amplia aquest fitxer quan arriba la seva peça (API privada).

    cd backend && venv/bin/python manage.py test fhort.backoffice.tests_leads
"""
import datetime
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from rest_framework.test import APIRequestFactory

from fhort.backoffice.models import Lead
from fhort.backoffice.views_leads import lead_public_view

URL = '/api/backoffice/v1/leads/public/'

VALID_PAYLOAD = {
    'nom': 'Maria Puig',
    'empresa': 'Puig Confecció SL',
    'email': 'maria@puigconfeccio.example',
    'missatge': 'Voldria una demo del motor de patrons.',
    'idioma': 'ca',
    'pagina_origen': '/ca/plataforma/motor-de-patrons/',
    'consentiment': True,
    'privacy_version': 'v1',
}


class LeadPublicViewTest(TenantTestCase):
    """Crida la view DIRECTAMENT (APIRequestFactory), mateix patró que
    tenants/tests_discovery.py: el Lead viu a 'public' (SHARED_APP) i el search_path
    de django-tenants el fa visible des de qualsevol schema actiu, així que no cal
    canviar de schema per exercir la lògica. La guarda de MUNTATGE (404 a tenant) es
    prova a part, amb una petició real via TenantClient."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Tenant Leads'
        tenant.tipologia = 'marca'
        tenant.codi_tenant = 'TL1'
        tenant.vat_number = 'X0000002X'
        tenant.tipus_client = 'b2b'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        cache.clear()   # el throttle és de cache: sense això un test en condiciona un altre
        Lead.objects.all().delete()

    def _post(self, data, ip='198.51.100.7'):
        req = APIRequestFactory().post(URL, data, format='json',
                                       REMOTE_ADDR=ip, HTTP_X_FORWARDED_FOR=ip)
        return lead_public_view(req)

    # ── alta correcta ─────────────────────────────────────────────────────────
    def test_alta_correcta(self):
        resp = self._post(VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data, {'ok': True})
        self.assertEqual(Lead.objects.count(), 1)
        lead = Lead.objects.get()
        self.assertEqual(lead.nom, VALID_PAYLOAD['nom'])
        self.assertEqual(lead.email, VALID_PAYLOAD['email'])
        self.assertEqual(lead.idioma, 'ca')
        self.assertEqual(lead.estat, Lead.ESTAT_NOU)
        self.assertEqual(lead.ip, '198.51.100.7')
        self.assertFalse(lead.notificat)

    # ── consentiment fals ────────────────────────────────────────────────────
    def test_consentiment_false_dona_400(self):
        payload = {**VALID_PAYLOAD, 'consentiment': False}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('consentiment', resp.data)
        self.assertEqual(Lead.objects.count(), 0)

    # ── honeypot ─────────────────────────────────────────────────────────────
    def test_honeypot_dona_201_i_no_desa(self):
        payload = {**VALID_PAYLOAD, 'website': 'https://spam.example'}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data, {'ok': True})
        self.assertEqual(Lead.objects.count(), 0)

    def test_honeypot_amb_payload_invalid_igualment_201(self):
        # Un bot no ha de poder distingir cap resposta: també amb la resta invàlida.
        payload = {'website': 'spam', 'consentiment': False}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Lead.objects.count(), 0)

    # ── límits ───────────────────────────────────────────────────────────────
    def test_missatge_massa_llarg_dona_400(self):
        payload = {**VALID_PAYLOAD, 'missatge': 'x' * 4001}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('missatge', resp.data)
        self.assertEqual(Lead.objects.count(), 0)

    def test_nom_massa_llarg_dona_400(self):
        payload = {**VALID_PAYLOAD, 'nom': 'x' * 121}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('nom', resp.data)

    def test_email_invalid_dona_400(self):
        payload = {**VALID_PAYLOAD, 'email': 'no-es-un-email'}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('email', resp.data)

    def test_idioma_fora_de_choices_dona_400(self):
        payload = {**VALID_PAYLOAD, 'idioma': 'fr'}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('idioma', resp.data)

    # ── throttle ─────────────────────────────────────────────────────────────
    def test_throttle_dona_429(self):
        # 5/hour → la 6a petició des de la mateixa IP és 429.
        codis = [self._post(VALID_PAYLOAD, ip='203.0.113.9').status_code for _ in range(6)]
        self.assertEqual(codis, [201, 201, 201, 201, 201, 429])
        self.assertEqual(Lead.objects.count(), 5)

    def test_throttle_es_per_ip(self):
        # Una IP diferent no consumeix la quota de l'altra.
        for _ in range(5):
            self._post(VALID_PAYLOAD, ip='203.0.113.10')
        resp = self._post(VALID_PAYLOAD, ip='203.0.113.11')
        self.assertEqual(resp.status_code, 201)


class LeadPublicMuntatgeTest(TenantTestCase):
    """GUARDA DE LLEI: leads/public/ NOMÉS existeix a `public`. Un host de TENANT
    (ROOT_URLCONF='fhort.urls', que no munta backoffice) l'ha de donar 404 — no és
    un forat de permisos, és un forat de resolució de tenant."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Tenant Leads Muntatge'
        tenant.tipologia = 'marca'
        tenant.codi_tenant = 'TL2'
        tenant.vat_number = 'X0000003X'
        tenant.tipus_client = 'b2b'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def test_post_a_host_de_tenant_dona_404(self):
        client = TenantClient(self.tenant)
        resp = client.post(URL, VALID_PAYLOAD, content_type='application/json')
        self.assertEqual(resp.status_code, 404)

    def test_leads_public_resol_a_public_urlconf(self):
        from django.urls import resolve
        self.assertEqual(
            resolve('/api/backoffice/v1/leads/public/', urlconf='fhort.urls_public').url_name,
            'backoffice-leads-public',
        )

    def test_leads_public_no_resol_a_tenant_urlconf(self):
        from django.urls import Resolver404, resolve
        with self.assertRaises(Resolver404):
            resolve('/api/backoffice/v1/leads/public/', urlconf='fhort.urls')


class LeadNotificationTest(TenantTestCase):
    """L2: avís per correu best-effort, adormit fins que hi hagi SMTP real.

    La view crida notifica_lead() via transaction.on_commit; TestCase envolta cada
    test en una transacció que es desfà (mai es commiteja de veritat), així que cal
    captureOnCommitCallbacks(execute=True) perquè el callback arribi a executar-se —
    sense això, cap d'aquests tests veuria mai el correu (fals verd silenciós)."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Tenant Leads Notify'
        tenant.tipologia = 'marca'
        tenant.codi_tenant = 'TL3'
        tenant.vat_number = 'X0000004X'
        tenant.tipus_client = 'b2b'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        cache.clear()
        Lead.objects.all().delete()
        mail.outbox = []

    def _post(self, data, ip='198.51.100.20'):
        req = APIRequestFactory().post(URL, data, format='json',
                                       REMOTE_ADDR=ip, HTTP_X_FORWARDED_FOR=ip)
        with self.captureOnCommitCallbacks(execute=True):
            return lead_public_view(req)

    @override_settings(EMAIL_HOST='', LEADS_NOTIFY_EMAIL='')
    def test_sense_config_lead_desat_notificat_false_0_correus(self):
        resp = self._post(VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 201)
        lead = Lead.objects.get()
        self.assertFalse(lead.notificat)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        EMAIL_HOST='localhost', LEADS_NOTIFY_EMAIL='ops@fhort.test',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_amb_locmem_backend_1_correu_notificat_true(self):
        resp = self._post(VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 201)
        lead = Lead.objects.get()
        self.assertTrue(lead.notificat)
        self.assertEqual(len(mail.outbox), 1)
        enviat = mail.outbox[0]
        self.assertEqual(enviat.to, ['ops@fhort.test'])
        self.assertEqual(enviat.reply_to, [VALID_PAYLOAD['email']])
        self.assertIn(VALID_PAYLOAD['nom'], enviat.body)
        self.assertIn(f'/leads/{lead.pk}', enviat.body)

    @override_settings(
        EMAIL_HOST='localhost', LEADS_NOTIFY_EMAIL='ops@fhort.test',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_smtp_que_peta_lead_desat_201_notificat_false(self):
        with mock.patch('django.core.mail.EmailMessage.send', side_effect=Exception('boom')):
            resp = self._post(VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 201)
        lead = Lead.objects.get()
        self.assertFalse(lead.notificat)
        self.assertEqual(len(mail.outbox), 0)
