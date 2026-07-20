"""Tests dels filtres nous del ModelFilter canònic (C1) — Sprint FILTRES AVANÇATS · G1.

Convenció del repo: fitxer `test*.py`, executat amb `python manage.py test fhort.models_app`.

Cada filtre nou amb cas POSITIU i NEGATIU. watchpoints_open / in_plan / task_state comproven
l'Exists correlat (el model hi entra només si existeix la fila relacionada amb el criteri exacte).
Capes del ruleset (target/fit/construction) filtrades travessant grading_rule_set, NO l'eix legacy
del Model.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import Model, Watchpoint
from fhort.models_app.views import ModelViewSet
from fhort.pom.models import (
    GradingRuleSet, SizeSystem, Target, FitType, ConstructionType,
)
from fhort.tasks.models import TaskType, ModelTask, GarmentTypeItem
from fhort.pom.models import GarmentType


class ModelFiltersTest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='pm')
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.user = get_user_model().objects.get(pk=self.user.pk)

        # Eixos i sistema de talles. ss2/rs2 = vàlids però sense cap model (casos negatius).
        self.ss = SizeSystem.objects.create(codi='ALPHA_EU_W', nom='Alpha', base_unit='ALPHA')
        self.ss2 = SizeSystem.objects.create(codi='ALPHA_EU_M', nom='Alpha M', base_unit='ALPHA')
        self.t_woman = Target.objects.create(codi='WOMAN', nom_en='Woman', display_order=1)
        self.t_man = Target.objects.create(codi='MAN', nom_en='Man', display_order=2)
        self.fit_slim = FitType.objects.create(codi='SLIM', nom_en='Slim', display_order=1)
        self.constr_knit = ConstructionType.objects.create(codi='KNIT', nom_en='Knit', display_order=1)

        # Ruleset amb capes: target WOMAN (M2M), fit SLIM, construction KNIT.
        self.rs = GradingRuleSet.objects.create(nom='RS Woman Slim Knit')
        self.rs.fit_type = self.fit_slim
        self.rs.construction = self.constr_knit
        self.rs.size_system = self.ss
        self.rs.save()
        self.rs.targets.add(self.t_woman)
        self.rs2 = GradingRuleSet.objects.create(nom='RS buit')   # vàlid, cap model l'usa

        # Peça: garment_type (grup TOPS) + item, assignats a m1.
        self.gt = GarmentType.objects.create(codi_client='GTA', nom_client='Família A', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=self.gt, code='a1', name='Item A1')

        # m1: ruleset + size_system + peça + watchpoint obert + tasca planificada InProgress.
        self.m1 = self._mk(garment=None)
        self.m1.grading_rule_set = self.rs
        self.m1.size_system = self.ss
        self.m1.garment_type = self.gt
        self.m1.garment_type_item = self.item
        self.m1.save()
        Watchpoint.objects.create(model=self.m1, text='wp obert', estat='open')
        self.tt = TaskType.objects.create(code='sew', name='Sew', fase='Dev. tècnic')
        ModelTask.objects.create(model=self.m1, task_type=self.tt, order=0,
                                 status='InProgress', planned_start=datetime.datetime(2026, 6, 1, 9, 0))

        # m2: net (sense ruleset, sense size_system, sense watchpoint obert, tasca no planificada Pending).
        self.m2 = self._mk(garment=None)
        Watchpoint.objects.create(model=self.m2, text='wp resolt', estat='resolved')
        ModelTask.objects.create(model=self.m2, task_type=self.tt, order=0, status='Pending')

    def _mk(self, garment=None):
        n = Model.objects.count() + 1
        return Model.objects.create(codi_intern=f'M{n}', codi_tenant='TST', any=2026,
                                    temporada='SS', sequencial=n)

    def _ids(self, **params):
        req = APIRequestFactory().get('/api/v1/models/', params)
        force_authenticate(req, user=self.user)
        resp = ModelViewSet.as_view({'get': 'list'})(req)
        self.assertEqual(resp.status_code, 200)
        rows = resp.data['results'] if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        return {r['id'] for r in rows}

    # ── Filtres directes (FK) ────────────────────────────────────────────────
    def test_size_system(self):
        self.assertEqual(self._ids(size_system=self.ss.id), {self.m1.id})
        self.assertEqual(self._ids(size_system=self.ss2.id), set())

    def test_grading_rule_set(self):
        self.assertEqual(self._ids(grading_rule_set=self.rs.id), {self.m1.id})
        self.assertEqual(self._ids(grading_rule_set=self.rs2.id), set())

    # ── Capes del ruleset (per codi, travessant la relació) ──────────────────
    def test_target(self):
        self.assertEqual(self._ids(target='WOMAN'), {self.m1.id})
        self.assertEqual(self._ids(target='MAN'), set())

    def test_fit(self):
        self.assertEqual(self._ids(fit='SLIM'), {self.m1.id})
        self.assertEqual(self._ids(fit='LOOSE'), set())

    def test_construction(self):
        self.assertEqual(self._ids(construction='KNIT'), {self.m1.id})
        self.assertEqual(self._ids(construction='WOVEN'), set())

    # ── Peça multi-node (__in, OR dins de cada nivell) ───────────────────────
    def test_garment_multi_in(self):
        self.assertEqual(self._ids(garment_type_item__in=f'{self.item.id},99999'), {self.m1.id})
        self.assertEqual(self._ids(garment_type__in=f'{self.gt.id}'), {self.m1.id})
        self.assertEqual(self._ids(garment_group_codi__in='TOPS'), {self.m1.id})
        self.assertEqual(self._ids(garment_group_codi__in='BOTTOMS'), set())

    # ── Eixos operatius (Exists) ─────────────────────────────────────────────
    def test_watchpoints_open(self):
        self.assertEqual(self._ids(watchpoints_open='true'), {self.m1.id})
        self.assertEqual(self._ids(watchpoints_open='false'), {self.m2.id})

    def test_in_plan(self):
        self.assertEqual(self._ids(in_plan='true'), {self.m1.id})
        self.assertEqual(self._ids(in_plan='false'), {self.m2.id})

    def test_task_state_parell(self):
        # task_type + status exactes → m1 (té sew InProgress).
        self.assertEqual(self._ids(task_type='sew', task_status='InProgress'), {self.m1.id})
        # mateix tipus, status que ningú té InProgress excepte m1 → Pending el té m2.
        self.assertEqual(self._ids(task_type='sew', task_status='Pending'), {self.m2.id})
        # status inexistent → cap.
        self.assertEqual(self._ids(task_type='sew', task_status='Done'), set())
        # task_type sol (àncora) → tots dos tenen una tasca 'sew'.
        self.assertEqual(self._ids(task_type='sew'), {self.m1.id, self.m2.id})
