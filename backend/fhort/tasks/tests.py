"""Tests de la cascada de resolució de temps (lookup_estimated_minutes, 4 graons).

Graó 1 — cel·la pròpia item×task (empíric si n>=llindar, sinó seed de la cel·la).
Graó 2 — empíric global del task_type (mitjana de les cel·les MADURES de qualsevol item).
Graó 3 — llavor de tenant TimeSeed (scope='task' per code, sinó scope='phase' per fase).
Graó 4 — None NOMÉS si tot buit (el graó "demanar" = captura conscient del PM).
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.pom.models import GarmentType
from fhort.tasks.models import GarmentTypeItem, TaskType, TaskTimeEstimate, TimeSeed
from fhort.tasks.services_g import lookup_estimated_minutes
from fhort.tasks.views_b import time_capture_seed_view


def _model_stub(item_id):
    """La cascada només llegeix model.garment_type_item_id → stub mínim."""
    return type('ModelStub', (), {'garment_type_item_id': item_id})()


class TimeCascadeTest(TenantTestCase):

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
        self.gt = GarmentType.objects.create(codi_client='GT1', nom_client='Garment 1', grup='tops')
        self.item = GarmentTypeItem.objects.create(garment_type=self.gt, code='item_a', name='Item A')
        self.other = GarmentTypeItem.objects.create(garment_type=self.gt, code='item_b', name='Item B')
        self.task = TaskType.objects.create(code='task_x', name='Task X', fase='Dev. tècnic')

    def _cell(self, item, n=0, mean='0', seed=None):
        return TaskTimeEstimate.objects.create(
            garment_type_item=item, task_type=self.task,
            n=n, mean_minutes=Decimal(mean), estimated_minutes=seed)

    # ── Graó 1 — cel·la pròpia ──────────────────────────────────────────────
    def test_grao1_empiric_madur(self):
        self._cell(self.item, n=5, mean='42.4')            # n>=llindar → round(mean)
        self.assertEqual(lookup_estimated_minutes(_model_stub(self.item.id), self.task), 42)

    def test_grao1_seed_si_immadur(self):
        self._cell(self.item, n=2, mean='99', seed=30)     # n<llindar → seed de la cel·la
        self.assertEqual(lookup_estimated_minutes(_model_stub(self.item.id), self.task), 30)

    # ── Graó 2 — empíric global del task_type ───────────────────────────────
    def test_grao2_empiric_global(self):
        # el model apunta a self.item (sense cel·la); una ALTRA cel·la madura resol pel task.
        self._cell(self.other, n=8, mean='60')
        self.assertEqual(lookup_estimated_minutes(_model_stub(self.item.id), self.task), 60)

    # ── Graó 3 — llavor TimeSeed (task, sinó fase) ──────────────────────────
    def test_grao3_llavor_task(self):
        TimeSeed.objects.create(scope='task', key='task_x', minuts=77, origen='MIGRACIO')
        self.assertEqual(lookup_estimated_minutes(_model_stub(None), self.task), 77)

    def test_grao3_fallback_fase(self):
        TimeSeed.objects.create(scope='phase', key='Dev. tècnic', minuts=88, origen='ONBOARDING')
        self.assertEqual(lookup_estimated_minutes(_model_stub(None), self.task), 88)

    def test_grao3_task_precedeix_fase(self):
        TimeSeed.objects.create(scope='task', key='task_x', minuts=77, origen='MIGRACIO')
        TimeSeed.objects.create(scope='phase', key='Dev. tècnic', minuts=88, origen='ONBOARDING')
        self.assertEqual(lookup_estimated_minutes(_model_stub(None), self.task), 77)

    # ── Graó 4 — None quan tot buit ─────────────────────────────────────────
    def test_grao4_none_tot_buit(self):
        self.assertIsNone(lookup_estimated_minutes(_model_stub(None), self.task))

    def test_grao4_none_cel_immadura_sense_seed(self):
        self._cell(self.item, n=3, mean='50', seed=None)   # n<llindar i sense seed → None
        self.assertIsNone(lookup_estimated_minutes(_model_stub(self.item.id), self.task))


class CaptureSeedTest(TenantTestCase):
    """Captura conscient del PM: l'endpoint desa una llavor origen=CAPTURA i desbloqueja
    la cascada al moment (graó 3 passa de None a un valor)."""

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
        self.task = TaskType.objects.create(code='task_y', name='Task Y', fase='Dev. tècnic')
        self.user = get_user_model().objects.create(username='pm')
        # get_or_create per si un signal ja ha sembrat el perfil; forcem rol admin + grant.
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.rol_nom = 'admin'
        self.profile.nom_complet = 'PM'
        self.profile.permisos = {'grant': ['define_tasks']}
        self.profile.save()
        # Re-fetch de l'usuari: neteja qualsevol cache negatiu de la relació inversa user.profile.
        self.user = get_user_model().objects.get(pk=self.user.pk)

    def test_capture_desa_llavor_i_desbloqueja(self):
        # Abans: la cascada no resol (cap cel·la, cap empíric, cap llavor) → None.
        self.assertIsNone(lookup_estimated_minutes(_model_stub(None), self.task))
        # Captura via endpoint (admin = bypass de la gate define_tasks).
        req = APIRequestFactory().post(
            '/api/v1/time-analysis/capture-seed/',
            {'task_code': 'task_y', 'minuts': 25}, format='json')
        force_authenticate(req, user=self.user)
        resp = time_capture_seed_view(req)
        self.assertEqual(resp.status_code, 200)
        seed = TimeSeed.objects.get(scope='task', key='task_y')
        self.assertEqual((seed.minuts, seed.origen, seed.updated_by_id),
                         (25, 'CAPTURA', self.profile.id))
        # Després: la mateixa cascada ja resol al moment.
        self.assertEqual(lookup_estimated_minutes(_model_stub(None), self.task), 25)

    def test_capture_rebutja_minuts_no_positius(self):
        req = APIRequestFactory().post(
            '/api/v1/time-analysis/capture-seed/',
            {'task_code': 'task_y', 'minuts': 0}, format='json')
        force_authenticate(req, user=self.user)
        resp = time_capture_seed_view(req)
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(TimeSeed.objects.filter(key='task_y').exists())
