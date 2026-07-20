"""Tests del contracte de CONJUNT de plan/assign-batch (C2).

Cobreix:
  - XOR dur de la font de models: model_ids i filters no poden venir alhora ni cap dels dos.
  - Límit dur d'ids explícits (ASSIGN_BATCH_MAX_EXPLICIT_IDS).
  - Camí `filters`: el backend RE-AVALUA el queryset server-side amb el ModelFilter canònic
    (C1) al moment d'executar, i respecta exclude_ids.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.models import Model
from fhort.tasks.models import TaskType, TimeSeed, ModelTask
from fhort.planning.views import plan_assign_batch_view, ASSIGN_BATCH_MAX_EXPLICIT_IDS


class AssignBatchContractTest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='pm')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.prof.rol_nom = 'admin'                              # admin → bypass gate + allow-list
        self.prof.permisos = {'grant': ['define_tasks']}
        self.prof.save()
        self.user = get_user_model().objects.get(pk=self.user.pk)  # neteja cache user.profile

        self.tt = TaskType.objects.create(code='task_z', name='Task Z', fase='Dev. tècnic')
        TimeSeed.objects.create(scope='task', key='task_z', minuts=30, origen='MIGRACIO')  # cascada → 30

        # Dos models de temporades diferents (base de la re-avaluació per filtre).
        self.m_ss = Model.objects.create(codi_intern='SS1', codi_tenant='TST', any=2026,
                                         temporada='SS', sequencial=1)
        self.m_fw = Model.objects.create(codi_intern='FW1', codi_tenant='TST', any=2026,
                                         temporada='FW', sequencial=2)

    def _post(self, body):
        req = APIRequestFactory().post('/api/v1/plan/assign-batch/', body, format='json')
        force_authenticate(req, user=self.user)
        return plan_assign_batch_view(req)

    def _assignacio(self):
        return [{'task_type_code': 'task_z', 'assignee_profile_id': self.prof.id}]

    # ── XOR de la font de models ────────────────────────────────────────────
    def test_xor_both_sources_400(self):
        resp = self._post({'model_ids': [self.m_ss.id], 'filters': {'temporada': 'SS'},
                           'assignacions': self._assignacio()})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('EXACTAMENT una font', resp.data['error'])

    def test_xor_no_source_400(self):
        resp = self._post({'assignacions': self._assignacio()})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('EXACTAMENT una font', resp.data['error'])

    # ── Límit dur d'ids explícits ───────────────────────────────────────────
    def test_explicit_ids_over_limit_400(self):
        too_many = list(range(1, ASSIGN_BATCH_MAX_EXPLICIT_IDS + 2))   # límit + 1
        resp = self._post({'model_ids': too_many, 'assignacions': self._assignacio()})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Massa models', resp.data['error'])

    # ── Camí filters: re-avaluació server-side + exclude_ids ─────────────────
    def test_filters_path_reevaluates_queryset(self):
        resp = self._post({'filters': {'temporada': 'SS'}, 'assignacions': self._assignacio()})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['fets'], 1)
        # NOMÉS el model SS ha rebut la tasca; el FW (fora del filtre) no.
        self.assertTrue(ModelTask.objects.filter(model=self.m_ss, task_type=self.tt).exists())
        self.assertFalse(ModelTask.objects.filter(model=self.m_fw).exists())

    def test_filters_path_respects_exclude_ids(self):
        resp = self._post({'filters': {'temporada': 'SS'}, 'exclude_ids': [self.m_ss.id],
                           'assignacions': self._assignacio()})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['fets'], 0)
        self.assertFalse(ModelTask.objects.filter(task_type=self.tt).exists())

    def test_explicit_ids_path_still_works(self):
        resp = self._post({'model_ids': [self.m_fw.id], 'assignacions': self._assignacio()})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['fets'], 1)
        self.assertTrue(ModelTask.objects.filter(model=self.m_fw, task_type=self.tt).exists())
