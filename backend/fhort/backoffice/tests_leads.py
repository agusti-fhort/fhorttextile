"""Leads (P-LEADS) — formulari públic de la web de marketing.

L1: model + porta pública (throttle, honeypot, guarda de muntatge a `public`).
L2: avís per correu (adormit fins que hi hagi SMTP real).
L3: API privada (ADMIN) — llista/detall/PATCH(estat+notes)/DELETE/counts.

    cd backend && venv/bin/python manage.py test fhort.backoffice.tests_leads
"""
import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.backoffice.models import BackofficeUser, Lead
from fhort.backoffice.views_leads import LeadViewSet, lead_counts_view, lead_public_view

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


class LeadAdminApiTest(TenantTestCase):
    """L3: API privada (ADMIN) — llista (filtre ?estat=)/detall/PATCH(estat+notes,
    la resta read-only)/DELETE. BackofficeUser és SHARED/public-only (com Lead):
    creat sota schema_context('public'), autenticat amb force_authenticate (evita
    dependre de JWT/sessió per exercir només el permís)."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Tenant Leads Admin'
        tenant.tipologia = 'marca'
        tenant.codi_tenant = 'TL4'
        tenant.vat_number = 'X0000005X'
        tenant.tipus_client = 'b2b'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        Lead.objects.all().delete()
        User = get_user_model()
        with schema_context('public'):
            self.admin_user = User.objects.create_user(
                username='admin@fhort.test', email='admin@fhort.test', password='pw123456')
            BackofficeUser.objects.create(
                usuari=self.admin_user, rol=BackofficeUser.Rol.ADMIN, actiu=True)
            self.comercial_user = User.objects.create_user(
                username='comercial@fhort.test', email='comercial@fhort.test', password='pw123456')
            BackofficeUser.objects.create(
                usuari=self.comercial_user, rol=BackofficeUser.Rol.COMERCIAL, actiu=True)
        self.lead = Lead.objects.create(
            nom='Joan Vidal', email='joan@example.com', missatge='Hola',
            idioma='ca', consentiment=True, privacy_version='v1')

    # ── anònim / rol equivocat ───────────────────────────────────────────────
    def test_llista_anonim_dona_401_o_403(self):
        req = APIRequestFactory().get('/api/backoffice/v1/leads/')
        resp = LeadViewSet.as_view({'get': 'list'})(req)
        self.assertIn(resp.status_code, (401, 403))

    def test_llista_rol_no_admin_dona_403(self):
        req = APIRequestFactory().get('/api/backoffice/v1/leads/')
        force_authenticate(req, user=self.comercial_user)
        resp = LeadViewSet.as_view({'get': 'list'})(req)
        self.assertEqual(resp.status_code, 403)

    # ── llista + filtre ──────────────────────────────────────────────────────
    def test_llista_admin_ok_ordenada_per_created_at_desc(self):
        req = APIRequestFactory().get('/api/backoffice/v1/leads/')
        force_authenticate(req, user=self.admin_user)
        resp = LeadViewSet.as_view({'get': 'list'})(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['id'], self.lead.pk)

    def test_filtre_per_estat(self):
        Lead.objects.create(nom='Altre', email='altre@example.com', missatge='Hi',
                            idioma='es', consentiment=True, privacy_version='v1',
                            estat=Lead.ESTAT_TANCAT)
        req = APIRequestFactory().get('/api/backoffice/v1/leads/', {'estat': 'tancat'})
        force_authenticate(req, user=self.admin_user)
        resp = LeadViewSet.as_view({'get': 'list'})(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['estat'], 'tancat')

    # ── PATCH: només estat i notes ───────────────────────────────────────────
    def test_patch_estat_i_notes_ok_altres_camps_ignorats(self):
        req = APIRequestFactory().patch(
            f'/api/backoffice/v1/leads/{self.lead.pk}/',
            {'estat': 'contactat', 'notes': 'Trucat el 21/09', 'email': 'hacked@x.com'},
            format='json')
        force_authenticate(req, user=self.admin_user)
        resp = LeadViewSet.as_view({'patch': 'partial_update'})(req, pk=self.lead.pk)
        self.assertEqual(resp.status_code, 200)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.estat, 'contactat')
        self.assertEqual(self.lead.notes, 'Trucat el 21/09')
        self.assertEqual(self.lead.email, 'joan@example.com')   # ignorat, no canvia

    # ── DELETE ───────────────────────────────────────────────────────────────
    def test_delete_esborra(self):
        req = APIRequestFactory().delete(f'/api/backoffice/v1/leads/{self.lead.pk}/')
        force_authenticate(req, user=self.admin_user)
        resp = LeadViewSet.as_view({'delete': 'destroy'})(req, pk=self.lead.pk)
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Lead.objects.count(), 0)


class LeadCountsApiTest(TenantTestCase):
    """GET leads/counts/ — recompte per estat + tots, ADMIN, una sola consulta
    agregada. Ruta estàtica: mai xoca amb leads/<pk>/ (vegeu resolve() a
    LeadPublicMuntatgeTest per l'equivalent de leads/public/)."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Tenant Leads Counts'
        tenant.tipologia = 'marca'
        tenant.codi_tenant = 'TL5'
        tenant.vat_number = 'X0000006X'
        tenant.tipus_client = 'b2b'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        Lead.objects.all().delete()
        User = get_user_model()
        with schema_context('public'):
            self.admin_user = User.objects.create_user(
                username='admin-counts@fhort.test', email='admin-counts@fhort.test',
                password='pw123456')
            BackofficeUser.objects.create(
                usuari=self.admin_user, rol=BackofficeUser.Rol.ADMIN, actiu=True)
            self.comercial_user = User.objects.create_user(
                username='comercial-counts@fhort.test', email='comercial-counts@fhort.test',
                password='pw123456')
            BackofficeUser.objects.create(
                usuari=self.comercial_user, rol=BackofficeUser.Rol.COMERCIAL, actiu=True)

    def _get(self, user=None):
        req = APIRequestFactory().get('/api/backoffice/v1/leads/counts/')
        if user is not None:
            force_authenticate(req, user=user)
        return lead_counts_view(req)

    def test_anonim_dona_401_o_403(self):
        resp = self._get()
        self.assertIn(resp.status_code, (401, 403))

    def test_rol_no_admin_dona_403(self):
        resp = self._get(user=self.comercial_user)
        self.assertEqual(resp.status_code, 403)

    def test_buit_dona_zeros(self):
        resp = self._get(user=self.admin_user)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {'nou': 0, 'contactat': 0, 'tancat': 0, 'tots': 0})

    def test_recomptes_correctes_amb_estats_diferents(self):
        for estat, n in (('nou', 3), ('contactat', 2), ('tancat', 1)):
            for i in range(n):
                Lead.objects.create(
                    nom=f'{estat}-{i}', email=f'{estat}{i}@example.com', missatge='Hi',
                    idioma='ca', consentiment=True, privacy_version='v1', estat=estat)
        resp = self._get(user=self.admin_user)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {'nou': 3, 'contactat': 2, 'tancat': 1, 'tots': 6})
