"""El PATCH de `/api/v1/tenant-config/` és una ESCRIPTURA, i fins ara no ho semblava.

La diagnosi del 14/08 (`docs/diagnosis/DIAGNOSI_CAPA_ACCES_COMERCIAL_2026-08-14.md` §4.3) el
va trobar com a única escriptura sense gate de tot el cens: `@api_view(['GET','PATCH'])` amb
un sol `@permission_classes([IsAuthenticated])`, i una llista blanca de camps que porta
`hourly_rate`, `iban`, `tax_id`, `legal_name` i `legal_footer`. Un tècnic podia escriure-hi
la tarifa de cost per hora — la mateixa que després alimenta `internal_cost` a les línies
d'albarà (`commerce/serializers.py:449-457`).

El GET es queda obert: tota la SPA el consulta per saber `unitat_mesura`, i tancar-lo
trencaria qualsevol pantalla de mesures. El tall va per MÈTODE, dins la funció, que és el
patró de la casa per a una vista de funció amb capability (`backoffice/views_legal_tenant.py:23`).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.pom.s2_views import tenant_config_view


class GateTenantConfigTest(TenantTestCase):

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
        self.tecnic = self._usuari('tecnic@test.local', 'technician')
        self.admin = self._usuari('admin@test.local', 'admin')

    def _usuari(self, username, rol):
        """Usuari amb rol. El signal post_save(User) ja crea el perfil amb el rol per defecte,
        així que cal promocionar-lo i RELLEGIR l'usuari: `get_capabilities` llegeix de
        `user.profile`, que el signal ha deixat cachejat amb els valors vells."""
        user = get_user_model().objects.create_user(username, password='x')
        prof, _ = UserProfile.objects.get_or_create(
            user=user, defaults={'nom_complet': username, 'rol_nom': rol})
        prof.rol_nom = rol
        prof.save(update_fields=['rol_nom'])
        return get_user_model().objects.get(pk=user.pk)

    def _crida(self, metode, user, dades=None):
        req = (self.factory.get('/api/v1/tenant-config/') if metode == 'get'
               else self.factory.patch('/api/v1/tenant-config/', dades or {}, format='json'))
        force_authenticate(req, user=user)
        req.tenant = self.tenant
        return tenant_config_view(req)

    # ── El guard ────────────────────────────────────────────────────────────────
    def test_patch_de_tecnic_es_403(self):
        """EL VERMELL DE LA PEÇA: abans del gate, això tornava 200 i desava la tarifa."""
        resp = self._crida('patch', self.tecnic, {'hourly_rate': '999.00'})
        self.assertEqual(resp.status_code, 403)

    def test_patch_de_tecnic_no_escriu_res(self):
        """Un 403 que hagués desat abans de tallar no seria un gate. La tarifa no es mou."""
        from fhort.accounts.models import TenantConfig
        cfg = TenantConfig.get_or_create_default()
        cfg.hourly_rate = None
        cfg.save(update_fields=['hourly_rate'])
        self._crida('patch', self.tecnic, {'hourly_rate': '999.00'})
        cfg.refresh_from_db()
        self.assertIsNone(cfg.hourly_rate)

    # ── Els controls: el que NO ha de canviar ───────────────────────────────────
    def test_get_de_tecnic_segueix_200(self):
        """Tota la SPA llegeix aquí `unitat_mesura`. Tancar el GET trencaria les mesures."""
        resp = self._crida('get', self.tecnic)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['unitat_mesura'], 'CM')

    def test_patch_d_admin_segueix_funcionant(self):
        resp = self._crida('patch', self.admin, {'nom_empresa': 'Casa Nova'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['nom_empresa'], 'Casa Nova')
