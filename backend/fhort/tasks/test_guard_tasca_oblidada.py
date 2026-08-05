"""Guard de tasca oblidada — el batec i la marca d'automatisme (27/07).

Convenció del repo: fitxer `test*.py` dins de l'app, executat amb
`python manage.py test fhort.tasks` (el projecte NO fa servir pytest).

Dues peces del backend, provades pel forat pel qual es colarien:

  1. **El batec.** `TimerEntradaSerializer` fa `fields='__all__'`, de manera que un camp nou neix
     ESCRIVIBLE si ningú no ho impedeix — i un `last_heartbeat` escrivible pel PATCH deixa
     esquivar el guard des del navegador. L'única porta d'escriptura ha de ser `heartbeat`, i
     només sobre un tram viu del PROPI tècnic.
     04/08 — la llei ja no es defensa camp a camp sinó al nivell correcte: el viewset és
     `ReadOnlyModelViewSet` i el CRUD de trams (create/update/destroy) **no existeix**. El tram
     neix i mor dins de `transition_task`; el client només llegeix i truca les dues accions.
  2. **La marca.** `transition_task(..., auto=...)` no obre cap camí nou: passa per les mateixes
     regles i només tenyeix el log. I sense marca, el log ha de seguir dient «gest humà» (null),
     que és el que val per a tot l'històric.
"""
import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
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

    # ── El CRUD de trams: la porta que no hi ha de ser ──────────────────────
    #
    # Es prova per la RUTA REAL (`APIClient` + domini del tenant, patró de
    # `pom/test_regla_inactiva_no_editable.py`) i no amb `as_view({...})`, perquè el que es
    # defensa és exactament el que el ROUTER publica: `SimpleRouter.get_method_map` només
    # enruta els verbs l'acció dels quals existeix al viewset, i sense `create`/`update`/
    # `destroy` la resposta és un 405 de debò. Cridar `as_view({'post': 'create'})` provaria
    # una altra cosa (no hi ha handler) i no diria res del que veu un navegador.
    def _api(self):
        from rest_framework.test import APIClient
        c = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        c.force_authenticate(user=self.user)
        return c

    def test_last_heartbeat_no_es_pot_falsificar_pel_patch(self):
        """La defensa ja no és camp a camp: **el PATCH no existeix**.

        Abans això comprovava que el PATCH tornava 200 i ignorava el camp — una porta oberta amb
        el forat tapat. Ara la porta és tancada, i el camp segueix intacte (que és la invariant
        que aquest test defensa des del primer dia)."""
        transition_task(self.task, 'InProgress', self.prof)
        timer = self._timer_obert()
        fals = (timezone.now() + datetime.timedelta(hours=5)).isoformat()
        res = self._api().patch(f'/api/v1/timers/{timer.pk}/', {'last_heartbeat': fals},
                                format='json')
        self.assertEqual(res.status_code, 405)
        timer.refresh_from_db()
        self.assertIsNone(timer.last_heartbeat)   # ni desat ni tocat

    def test_el_tram_no_es_pot_inventar_ni_esborrar_des_del_client(self):
        """El temps facturable no és un recurs que el navegador redacti.

        `POST /timers/` deixava crear un tram amb l'`inici` i el `model_task` que es volgués, i
        `DELETE /timers/<id>/` en deixava esborrar un — tots dos amb només `IsAuthenticated` i
        sense passar per cap transició ni deixar cap `TaskTransition` al log. El tram neix i mor
        dins de `transition_task`; per aquí només es llegeix."""
        transition_task(self.task, 'InProgress', self.prof)
        timer = self._timer_obert()
        api = self._api()

        inventat = api.post('/api/v1/timers/', {
            'model_task': self.task.pk,
            'inici': (timezone.now() - datetime.timedelta(hours=9)).isoformat(),
        }, format='json')
        self.assertEqual(inventat.status_code, 405)
        self.assertEqual(api.delete(f'/api/v1/timers/{timer.pk}/').status_code, 405)
        self.assertEqual(api.put(f'/api/v1/timers/{timer.pk}/', {}, format='json').status_code, 405)

        # Cap tram nou, i el que hi havia segueix viu: el cens no s'ha mogut.
        self.assertEqual(TimerEntrada.objects.filter(model_task=self.task).count(), 1)
        self.assertTrue(TimerEntrada.objects.filter(pk=timer.pk).exists())

    def test_les_portes_vives_sobreviuen_al_read_only(self):
        """Tancar el CRUD no pot tancar el que sí que es fa servir: `list`, `retrieve` i
        `heartbeat` (guard)."""
        transition_task(self.task, 'InProgress', self.prof)
        api = self._api()
        self.assertEqual(api.get('/api/v1/timers/', {'actiu': 'true'}).status_code, 200)
        self.assertEqual(api.post('/api/v1/timers/heartbeat/').status_code, 200)
        timer = self._timer_obert()
        self.assertEqual(api.get(f'/api/v1/timers/{timer.pk}/').status_code, 200)

    def test_l_accio_tancar_esta_JUBILADA(self):
        """F1.7 — `tancar` tancava un tram sense passar per `transition_task`: cap
        `TaskTransition`, cap `record_actual_time`, i la tasca quedava «En curs» sense tram obert
        (l'anomalia «òrfena»). Era, a més, l'última escriptura pública d'aquest viewset: el pas a
        `ReadOnlyModelViewSet` va tancar el router, però les `@action` no en depenen.

        Qui vulgui tancar feina té el Stop, que passa per la màquina d'estats."""
        transition_task(self.task, 'InProgress', self.prof)
        timer = self._timer_obert()
        resposta = self._api().post(f'/api/v1/timers/{timer.pk}/tancar/')
        self.assertIn(resposta.status_code, (404, 405))
        timer.refresh_from_db()
        self.assertIsNone(timer.fi, 'el tram s\'ha tancat per una porta que ja no hi hauria de ser')

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

    # ── La xarxa de seguretat (pestanya tancada) ────────────────────────────
    def _envelleix(self, minuts, camp='inici'):
        timer = self._timer_obert()
        TimerEntrada.objects.filter(pk=timer.pk).update(
            **{camp: timezone.now() - datetime.timedelta(minutes=minuts)})

    def _cron(self, **kwargs):
        from django.db import connection
        out = StringIO()
        call_command('pausa_tasques_oblidades', tenant=connection.schema_name,
                     stdout=out, **kwargs)
        return out.getvalue()

    def test_cron_pausa_el_tram_sense_cap_senyal(self):
        transition_task(self.task, 'InProgress', self.prof)
        self._envelleix(45)
        self._cron()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'Paused')
        tr = TaskTransition.objects.filter(model_task=self.task).order_by('at').last()
        self.assertEqual(tr.auto, 'cron_40min')
        self.assertEqual(tr.to_status, 'Paused')

    def test_cron_respecta_el_batec(self):
        """Tram vell però amb senyal recent: el tècnic hi és, no s'hi toca."""
        transition_task(self.task, 'InProgress', self.prof)
        self._envelleix(120)
        self._heartbeat()
        self._cron()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'InProgress')

    def test_cron_no_toca_els_trams_joves(self):
        transition_task(self.task, 'InProgress', self.prof)
        self._envelleix(10)
        self._cron()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'InProgress')

    def test_cron_dry_run_no_escriu(self):
        transition_task(self.task, 'InProgress', self.prof)
        self._envelleix(45)
        sortida = self._cron(dry_run=True)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'InProgress')
        self.assertIn('dry-run', sortida)

    def test_cron_es_idempotent(self):
        transition_task(self.task, 'InProgress', self.prof)
        self._envelleix(45)
        self._cron()
        abans = TaskTransition.objects.filter(model_task=self.task).count()
        self._cron()
        self.assertEqual(TaskTransition.objects.filter(model_task=self.task).count(), abans)

    def test_cron_amb_llindar_curt_es_la_via_de_qa(self):
        transition_task(self.task, 'InProgress', self.prof)
        self._envelleix(3)
        self._cron(minuts=2)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'Paused')

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
