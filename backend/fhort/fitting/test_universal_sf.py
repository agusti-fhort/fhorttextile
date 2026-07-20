"""Forat universal B2 — el SizeFitting es materialitza SEMPRE, també per a models verges.

Un model sembrat/creat sense `responsable` (cas normal d'onboarding de qualsevol client
nou) ha de tenir igualment el seu SizeFitting: sense SF no hi ha GradingVersion i la
superfície de mesures / create-piece quedava muda (400 silenciós). Aquí es verifica:

  1. El signal `sync_size_fitting` crea l'SF encara que `responsable` sigui None,
     resolent l'actor per: responsable → created_by → primer UserProfile.
  2. `get_or_create_size_fitting` és idempotent i honora `actor_profile_id`.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.fitting.models import SizeFitting
from fhort.models_app.models import Model
from fhort.pom.services import get_or_create_size_fitting


class UniversalSizeFittingTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        self.user = get_user_model().objects.create(username='tester')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Tester', 'rol_nom': 'admin'})

    def _make_model(self, codi, **extra):
        return Model.objects.create(
            codi_intern=codi, codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M', **extra,
        )

    def test_signal_crea_sf_sense_responsable(self):
        """Model verge (responsable=None, created_by=None) → SF creat, actor = primer perfil."""
        m = self._make_model('TST-VERGE-1')  # cap responsable ni created_by
        sfs = SizeFitting.objects.filter(model=m)
        self.assertEqual(sfs.count(), 1, "El signal ha de crear l'SF encara sense responsable")
        self.assertEqual(sfs.first().creat_per_id, self.profile.id,
                         "Sense responsable/created_by, l'actor cau al primer UserProfile")

    def test_signal_usa_created_by_quan_no_hi_ha_responsable(self):
        """Amb created_by però sense responsable → l'SF s'atribueix a created_by."""
        m = self._make_model('TST-VERGE-2', created_by=self.profile)
        self.assertTrue(m.responsable_id is None)
        sf = SizeFitting.objects.filter(model=m).first()
        self.assertIsNotNone(sf)
        self.assertEqual(sf.creat_per_id, self.profile.id)

    def test_get_or_create_idempotent_i_actor_profile_id(self):
        """get_or_create retorna l'SF existent (idempotència) i no en crea un de segon."""
        m = self._make_model('TST-VERGE-3')
        existent = SizeFitting.objects.get(model=m)  # el del signal
        tornat = get_or_create_size_fitting(m, actor_profile_id=self.profile.id)
        self.assertEqual(tornat.id, existent.id, "No ha de materialitzar un SF duplicat")
        self.assertEqual(SizeFitting.objects.filter(model=m).count(), 1)
