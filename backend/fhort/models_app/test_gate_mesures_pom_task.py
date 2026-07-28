"""El gate de Mesures NO depèn dels permisos de tasques.

El full del model derivava «la feina de POM està feta» de `GET model-task-items`, que va
escopat per `view_team_tasks`. Un tècnic sense la capability, i que no fos l'assignat de la
tasca `pom`, no en veia la fila i el full concloïa que la feina no estava feta: «Mesures
encara no disponibles» amb la tasca Done i la taula plena.

`pom_task_done` és la resposta del servidor a aquella pregunta, calculada SENSE cap scope de
visibilitat. Aquests tests fixen les dues cares:

  · l'estat del model és el mateix per a tothom (el que arregla el bug),
  · la llista de tasques segueix escopada exactament com abans (el que NO havia de canviar).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.capabilities import VIEW_TEAM_TASKS, get_capabilities
from fhort.models_app.models import Model
from fhort.models_app.views import ModelViewSet
from fhort.tasks.models import ModelTask, TaskType
from fhort.tasks.views_b import ModelTaskViewSet


class GateMesuresPomTaskTest(TenantTestCase):

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
        self.factory = APIRequestFactory()

        # Tècnic: rol SENSE view_team_tasks (ROLE_CAPABILITIES['technician']).
        self.tecnic = get_user_model().objects.create(username='tecnic')
        self.perfil_tecnic, _ = UserProfile.objects.get_or_create(user=self.tecnic)
        self.perfil_tecnic.rol_nom = 'technician'
        self.perfil_tecnic.permisos = {}
        self.perfil_tecnic.save()
        self.tecnic = get_user_model().objects.get(pk=self.tecnic.pk)

        # Una ALTRA persona: és qui té assignada la tasca de POM.
        self.altre = get_user_model().objects.create(username='altre')
        self.perfil_altre, _ = UserProfile.objects.get_or_create(user=self.altre)
        self.perfil_altre.rol_nom = 'technician'
        self.perfil_altre.save()

        # Manager: SÍ que té view_team_tasks.
        self.manager = get_user_model().objects.create(username='manager')
        self.perfil_manager, _ = UserProfile.objects.get_or_create(user=self.manager)
        self.perfil_manager.rol_nom = 'manager'
        self.perfil_manager.save()
        self.manager = get_user_model().objects.get(pk=self.manager.pk)

        # El catàleg de TaskType el sembra una migració: `pom` ja hi és al tenant de test.
        self.tt_pom, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'POM', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(codi_intern='G1', codi_tenant='TST', any=2026,
                                          temporada='SS26', sequencial=1)

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _tasca_pom(self, status, assignee=None, origen='prevista'):
        return ModelTask.objects.create(model=self.model, task_type=self.tt_pom, order=0,
                                        status=status, assignee=assignee, origen=origen)

    def _get_model(self, user):
        req = self.factory.get(f'/api/v1/models/{self.model.pk}/')
        force_authenticate(req, user=user)
        return ModelViewSet.as_view({'get': 'retrieve'})(req, pk=self.model.pk)

    def _llista_tasques(self, user):
        req = self.factory.get('/api/v1/model-task-items/', {'model': self.model.pk})
        force_authenticate(req, user=user)
        resp = ModelTaskViewSet.as_view({'get': 'list'})(req)
        dades = resp.data
        return dades['results'] if isinstance(dades, dict) and 'results' in dades else dades

    # ── Premissa: el tècnic NO té la capability ─────────────────────────────
    def test_premissa_el_tecnic_no_te_view_team_tasks(self):
        self.assertNotIn(VIEW_TEAM_TASKS, get_capabilities(self.tecnic))
        self.assertIn(VIEW_TEAM_TASKS, get_capabilities(self.manager))

    # ── EL BUG: tasca Done d'ALTRI, usuari sense la capability ───────────────
    def test_sense_view_team_tasks_i_tasca_pom_Done_daltri_el_gate_sobre(self):
        self._tasca_pom('Done', assignee=self.perfil_altre)

        resp = self._get_model(self.tecnic)
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.data['pom_task_done'], True)

        # I la raó per la qual abans fallava segueix sent certa: la fila NO la veu.
        self.assertEqual(self._llista_tasques(self.tecnic), [])

    def test_el_manager_i_el_tecnic_veuen_el_MATEIX_estat_del_model(self):
        self._tasca_pom('Done', assignee=self.perfil_altre)
        self.assertEqual(self._get_model(self.tecnic).data['pom_task_done'],
                         self._get_model(self.manager).data['pom_task_done'])

    # ── El gate segueix tancat quan la feina no està feta ────────────────────
    def test_tasca_pom_no_feta_el_gate_es_tancat_per_a_tothom(self):
        self._tasca_pom('InProgress', assignee=self.perfil_altre)
        for user in (self.tecnic, self.manager):
            self.assertIs(self._get_model(user).data['pom_task_done'], False)

    def test_sense_cap_tasca_pom_el_gate_es_tancat(self):
        self.assertIs(self._get_model(self.tecnic).data['pom_task_done'], False)

    def test_una_tasca_daltre_tipus_Done_no_obre_el_gate(self):
        tt, _ = TaskType.objects.get_or_create(
            code='tech_sheet', defaults={'name': 'Fitxa', 'fase': 'Dev. tècnic'})
        ModelTask.objects.create(model=self.model, task_type=tt, order=0, status='Done')
        self.assertIs(self._get_model(self.tecnic).data['pom_task_done'], False)

    def test_amb_dues_tasques_pom_nhi_ha_prou_amb_una_de_Done(self):
        """La unicitat (model, task_type) només val per a `origen='prevista'`: un model pot
        tenir-ne més d'una. El criteri és determinista, no «la primera de la llista»."""
        self._tasca_pom('Pending', assignee=self.perfil_altre)
        self._tasca_pom('Done', assignee=self.perfil_altre, origen='extra')
        self.assertIs(self._get_model(self.tecnic).data['pom_task_done'], True)

    # ── NO-REGRESSIÓ: l'scope de la llista de tasques no s'ha tocat ──────────
    def test_la_llista_de_tasques_segueix_filtrada_per_capability(self):
        propia = self._tasca_pom('Done', assignee=self.perfil_tecnic)
        daltri = ModelTask.objects.create(model=self.model, task_type=self.tt_pom, order=1,
                                          status='Pending', assignee=self.perfil_altre,
                                          origen='extra')
        # El tècnic només veu la SEVA.
        ids_tecnic = {t['id'] for t in self._llista_tasques(self.tecnic)}
        self.assertEqual(ids_tecnic, {propia.id})
        # El manager les veu totes dues.
        ids_manager = {t['id'] for t in self._llista_tasques(self.manager)}
        self.assertEqual(ids_manager, {propia.id, daltri.id})

    def test_el_model_no_exposa_cap_dada_de_la_tasca(self):
        """`pom_task_done` respon la pregunta del gate i res més: ni qui hi treballa, ni
        quantes n'hi ha, ni quin estat concret tenen."""
        self._tasca_pom('Done', assignee=self.perfil_altre)
        dades = self._get_model(self.tecnic).data
        self.assertIn('pom_task_done', dades)
        for prohibit in ('pom_task', 'pom_task_id', 'pom_task_assignee', 'model_tasks', 'tasks'):
            self.assertNotIn(prohibit, dades)
