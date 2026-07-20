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


class RecomputeReresolutionTest(TenantTestCase):
    """Peça 5: en replanificar (recompute), NOMÉS les tasques Pending re-resolen l'estimació
    via cascada; InProgress/Paused conserven el snapshot (Done ja excloses de la cua)."""

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
        from fhort.models_app.models import Model
        self.user = get_user_model().objects.create(username='tec')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.prof.rol_nom = 'technician'
        self.prof.save()
        self.model = Model.objects.create(codi_intern='M1', codi_tenant='TST', any=2026,
                                          temporada='SS26', sequencial=1)

    def _task_amb_llavor(self, code):
        tt = TaskType.objects.create(code=code, name=code, fase='Dev. tècnic')
        TimeSeed.objects.create(scope='task', key=code, minuts=40, origen='MIGRACIO')  # cascada → 40
        return tt

    def _mt(self, tt, status, est):
        from fhort.tasks.models import ModelTask
        return ModelTask.objects.create(model=self.model, task_type=tt, order=0,
                                        status=status, assignee=self.prof, estimated_minutes=est)

    def test_pending_reresol_started_conserva(self):
        from fhort.planning.plan_service import recompute_for_technicians
        pending = self._mt(self._task_amb_llavor('task_p'), 'Pending', 10)     # 10 → 40
        inprog = self._mt(self._task_amb_llavor('task_i'), 'InProgress', 10)   # conserva 10
        paused = self._mt(self._task_amb_llavor('task_a'), 'Paused', 10)       # conserva 10
        recompute_for_technicians([self.prof.id])
        for t in (pending, inprog, paused):
            t.refresh_from_db()
        self.assertEqual(pending.estimated_minutes, 40)
        self.assertEqual(inprog.estimated_minutes, 10)
        self.assertEqual(paused.estimated_minutes, 10)


class DestroyPendingOnlyTest(TenantTestCase):
    """C3 — DELETE de ModelTask NOMÉS quan status='Pending'. Les altres → 409 (no es destrueix
    història). Una Pending assignada/planificada replica la cascada d'unassign en esborrar-se."""

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
        from fhort.models_app.models import Model
        self.user = get_user_model().objects.create(username='pm')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.prof.rol_nom = 'admin'
        self.prof.permisos = {'grant': ['define_tasks', 'view_team_tasks']}
        self.prof.save()
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.tt = TaskType.objects.create(code='task_del', name='Del', fase='Dev. tècnic')
        self.model = Model.objects.create(codi_intern='D1', codi_tenant='TST', any=2026,
                                          temporada='SS', sequencial=1)

    def _mt(self, status='Pending', assignee=None, planned_start=None, tt=None):
        from fhort.tasks.models import ModelTask
        return ModelTask.objects.create(model=self.model, task_type=tt or self.tt, order=0,
                                        status=status, assignee=assignee,
                                        planned_start=planned_start, estimated_minutes=20)

    def _delete(self, pk):
        from fhort.tasks.views_b import ModelTaskViewSet
        req = APIRequestFactory().delete(f'/api/v1/model-task-items/{pk}/')
        force_authenticate(req, user=self.user)
        return ModelTaskViewSet.as_view({'delete': 'destroy'})(req, pk=pk)

    def test_pending_pura_sesborra(self):
        from fhort.tasks.models import ModelTask
        mt = self._mt(status='Pending')
        resp = self._delete(mt.id)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(ModelTask.objects.filter(pk=mt.id).exists())

    def test_no_pending_retorna_409(self):
        from fhort.tasks.models import ModelTask
        for st in ('InProgress', 'Paused', 'Done'):
            tt = TaskType.objects.create(code=f'task_{st}', name=st, fase='Dev. tècnic')
            mt = self._mt(status=st, tt=tt)   # tt distint: la unicitat prevista és per (model,tasktype)
            resp = self._delete(mt.id)
            self.assertEqual(resp.status_code, 409, st)
            self.assertTrue(ModelTask.objects.filter(pk=mt.id).exists(), st)

    def test_pending_planificada_replica_cascada(self):
        from fhort.tasks.models import ModelTask
        from fhort.models_app.models import Model
        from fhort.planning.models import TechnicianQueueOrder
        import django.utils.timezone as tz
        mt = self._mt(status='Pending', assignee=self.prof, planned_start=tz.now())
        TechnicianQueueOrder.objects.create(profile=self.prof, model=self.model, position=0)
        Model.objects.filter(pk=self.model.id).update(
            predicted_start=datetime.date(2026, 7, 1), predicted_end=datetime.date(2026, 7, 2))
        resp = self._delete(mt.id)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(ModelTask.objects.filter(pk=mt.id).exists())
        # Cascada: l'ordre manual de cua del model s'ha netejat i predicted_* també (cap no-Done
        # assignada resta al model).
        self.assertFalse(TechnicianQueueOrder.objects.filter(profile=self.prof, model=self.model).exists())
        self.model.refresh_from_db()
        self.assertIsNone(self.model.predicted_start)
        self.assertIsNone(self.model.predicted_end)
