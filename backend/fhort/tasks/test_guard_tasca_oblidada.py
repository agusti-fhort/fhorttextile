"""Guard de tasca oblidada — el batec i la marca d'automatisme (27/07).

Convenció del repo: fitxer `test*.py` dins de l'app, executat amb
`python manage.py test fhort.tasks` (el projecte NO fa servir pytest).

Dues peces del backend, provades pel forat pel qual es colarien:

  1. **El batec.** `TimerEntradaSerializer` fa `fields='__all__'`, de manera que un camp nou neix
     ESCRIVIBLE si ningú no ho impedeix — i un `last_heartbeat` escrivible pel PATCH deixa
     esquivar el guard des del navegador. L'única porta d'escriptura ha de ser `heartbeat`, i
     només sobre un tram viu del PROPI tècnic.
  2. **La marca.** `transition_task(..., auto=...)` no obre cap camí nou: passa per les mateixes
     regles i només tenyeix el log. I sense marca, el log ha de seguir dient «gest humà» (null),
     que és el que val per a tot l'històric.
"""
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, ModelTask, TaskTransition, TaskType, TimerEntrada
from fhort.tasks.services_c import transition_task
from fhort.tasks.views import TimerEntradaViewSet


class GuardTascaOblidadaTest(TenantTestCase):

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

        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create(username='tecguard')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.altre_user = get_user_model().objects.create(username='tecaltre')
        self.altre_prof, _ = UserProfile.objects.get_or_create(user=self.altre_user)

        self.customer = Customer.objects.create(codi='CLI', nom='Client de prova')
        GarmentType.objects.create(codi_client='GTG', nom_client='Família', grup='TOPS')
        self.tt = TaskType.objects.create(code='task_guard', name='Task Guard', fase='Dev. tècnic')
        self.model = Model.objects.create(
            codi_intern='TST-SS26-0100', codi_tenant='TST', any=2026, temporada='SS',
            sequencial=100, customer=self.customer, nom_prenda='Samarreta')
        self.task = ModelTask.objects.create(model=self.model, task_type=self.tt, order=0,
                                             status='Pending', assignee=self.prof)

    def _post(self, path, data, user, view, **kwargs):
        req = self.factory.post(path, data, format='json')
        force_authenticate(req, user=user)
        return view(req, **kwargs)

    def _heartbeat(self, user=None):
        return self._post('/api/v1/timers/heartbeat/', {}, user or self.user,
                          TimerEntradaViewSet.as_view({'post': 'heartbeat'}))

    def _timer_obert(self):
        return TimerEntrada.objects.get(model_task=self.task, fi__isnull=True, actiu=True)

    # ── El batec ────────────────────────────────────────────────────────────
    def test_timer_neix_sense_segell(self):
        """null = mai n'hi ha hagut cap. És el que fa que el llindar es mesuri des d'`inici`
        i que una tasca oberta i MAI confirmada venci igualment."""
        transition_task(self.task, 'InProgress', self.prof)
        self.assertIsNone(self._timer_obert().last_heartbeat)

    def test_heartbeat_segella_el_tram_obert(self):
        transition_task(self.task, 'InProgress', self.prof)
        res = self._heartbeat()
        self.assertEqual(res.status_code, 200)
        timer = self._timer_obert()
        self.assertEqual(res.data['timer_id'], timer.pk)
        self.assertEqual(res.data['model_task'], self.task.pk)
        self.assertIsNotNone(timer.last_heartbeat)

    def test_heartbeat_es_idempotent_i_avanca(self):
        """Trucar-hi dos cops no duplica res: només mou el segell endavant (rearmament)."""
        transition_task(self.task, 'InProgress', self.prof)
        self._heartbeat()
        primer = self._timer_obert().last_heartbeat
        self._heartbeat()
        self.assertEqual(TimerEntrada.objects.filter(model_task=self.task).count(), 1)
        self.assertGreaterEqual(self._timer_obert().last_heartbeat, primer)

    def test_heartbeat_404_si_la_tasca_ja_no_es_en_curs(self):
        """Pausada des d'una altra pestanya: el batec no ha de ressuscitar el tram."""
        transition_task(self.task, 'InProgress', self.prof)
        transition_task(self.task, 'Paused', self.prof)
        self.assertEqual(self._heartbeat().status_code, 404)

    def test_heartbeat_404_sense_cap_tasca_oberta(self):
        self.assertEqual(self._heartbeat().status_code, 404)

    def test_heartbeat_no_toca_el_tram_dun_altre_tecnic(self):
        """Sense `pk` a la ruta, el tram es busca pel propi perfil: per construcció, el batec
        d'un tècnic no pot segellar el d'un altre."""
        transition_task(self.task, 'InProgress', self.prof)
        self.assertEqual(self._heartbeat(user=self.altre_user).status_code, 404)
        self.assertIsNone(self._timer_obert().last_heartbeat)

    # ── El serializer (lliçó DRF: `fields='__all__'` fa néixer camps escrivibles) ──
    def test_last_heartbeat_no_es_pot_falsificar_pel_patch(self):
        transition_task(self.task, 'InProgress', self.prof)
        timer = self._timer_obert()
        fals = (timezone.now() + datetime.timedelta(hours=5)).isoformat()
        req = self.factory.patch(f'/api/v1/timers/{timer.pk}/', {'last_heartbeat': fals},
                                 format='json')
        force_authenticate(req, user=self.user)
        res = TimerEntradaViewSet.as_view({'patch': 'partial_update'})(req, pk=timer.pk)
        self.assertEqual(res.status_code, 200)
        timer.refresh_from_db()
        self.assertIsNone(timer.last_heartbeat)   # ignorat, no desat

    def test_serializer_exposa_last_heartbeat_en_lectura(self):
        """El frontend llegeix el segell d'aquí per saber des d'on comptar."""
        transition_task(self.task, 'InProgress', self.prof)
        self._heartbeat()
        req = self.factory.get('/api/v1/timers/', {'actiu': 'true'})
        force_authenticate(req, user=self.user)
        res = TimerEntradaViewSet.as_view({'get': 'list'})(req)
        self.assertEqual(res.status_code, 200)
        rows = res.data['results'] if isinstance(res.data, dict) else res.data
        obert = [r for r in rows if r['fi'] is None]
        self.assertEqual(len(obert), 1)
        self.assertIsNotNone(obert[0]['last_heartbeat'])
        self.assertIsNotNone(obert[0]['inici'])   # àncora del comptador del front

    # ── La marca al log ─────────────────────────────────────────────────────
    def test_gest_huma_deixa_la_marca_a_null(self):
        transition_task(self.task, 'InProgress', self.prof)
        transition_task(self.task, 'Paused', self.prof)
        tr = TaskTransition.objects.filter(model_task=self.task).order_by('at').last()
        self.assertEqual((tr.from_status, tr.to_status), ('InProgress', 'Paused'))
        self.assertIsNone(tr.auto)

    def test_auto_pausa_diu_quin_guard_ha_actuat(self):
        transition_task(self.task, 'InProgress', self.prof)
        transition_task(self.task, 'Paused', self.prof, auto='guard_30min')
        tr = TaskTransition.objects.filter(model_task=self.task).order_by('at').last()
        self.assertEqual(tr.auto, 'guard_30min')
        self.assertEqual(tr.by_id, self.prof.id)   # de qui era la tasca, sense mentir sobre el gest

    def test_lexclusio_una_sola_inprogress_tambe_es_marca(self):
        """Obrir una segona tasca en pausa la primera: el sistema, no el tècnic."""
        altra = ModelTask.objects.create(model=self.model, task_type=self.tt, order=1,
                                         status='Pending', assignee=self.prof, origen='ad_hoc')
        transition_task(self.task, 'InProgress', self.prof)
        res = transition_task(altra, 'InProgress', self.prof)
        self.assertEqual(res['paused_task_id'], self.task.pk)
        tr = TaskTransition.objects.filter(model_task=self.task).order_by('at').last()
        self.assertEqual((tr.from_status, tr.to_status), ('InProgress', 'Paused'))
        self.assertEqual(tr.auto, 'exclusio_inprogress')

    def test_lauto_pausa_no_es_mai_done(self):
        """El Stop és humà (llei intacta): el guard pausa, i la tasca queda represa-ble."""
        transition_task(self.task, 'InProgress', self.prof)
        transition_task(self.task, 'Paused', self.prof, auto='guard_30min')
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'Paused')
        self.assertIsNone(self.task.finished_at)

    def test_els_minuts_previs_a_lauto_pausa_compten(self):
        """Decisió v1: el temps treballat abans del venciment no es perd (deute anotat: pot
        incloure estona morta)."""
        transition_task(self.task, 'InProgress', self.prof)
        timer = self._timer_obert()
        TimerEntrada.objects.filter(pk=timer.pk).update(
            inici=timezone.now() - datetime.timedelta(minutes=30))
        transition_task(self.task, 'Paused', self.prof, auto='guard_30min')
        timer.refresh_from_db()
        self.assertEqual(timer.minuts, 30)
        self.assertFalse(timer.actiu)

    def test_la_tasca_auto_pausada_es_repren_net(self):
        """El guard i el kanban no es trepitgen: Paused→InProgress obre tram NOU i el segell
        del tram vell no arrossega res."""
        transition_task(self.task, 'InProgress', self.prof)
        self._heartbeat()
        transition_task(self.task, 'Paused', self.prof, auto='guard_30min')
        transition_task(self.task, 'InProgress', self.prof)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'InProgress')
        self.assertEqual(TimerEntrada.objects.filter(model_task=self.task).count(), 2)
        self.assertIsNone(self._timer_obert().last_heartbeat)
