"""S2 · STOP UNIVERSAL COM A GEST — el que el backend ha de garantir (28/07).

DECISIÓ Patró C (Agus): la màquina d'estats NO es toca. `Paused → Done` segueix PROHIBIDA
(`services_c.ALLOWED`). El que canvia és el GEST: el Stop sobre una tasca pausada és
play+stop encadenat — dues transicions legals en un sol acte d'usuari, i el front les
encadena. Aquest fitxer no prova el front: prova que el camí que el front encadenarà fa el
que ha de fer al backend, perquè el sprint no ho podia ASSUMIR.

Tres coses que s'hi fixen:
  1. `Paused → Done` directe segueix rebent TransitionError (la porta no s'ha obert).
  2. L'encadenat passa per la branca `frm == 'InProgress'` de `transition_task:224-227`:
     escriu `finished_at` i tanca el timer que ell mateix acaba d'obrir. Cap tram penjat.
  3. El tram nou es tanca amb els SEGONS REALS. Un encadenat instantani val 0 min i això
     és la veritat, no un zero artificial: `_close_open_timer` fa `//60` sobre la durada.
  4. Dependència amb S1: si la tasca arrossega un tram desbocat, el gest NO injecta hores
     falses al Welford — la mostra que hi arriba és la FILTRADA.

Convenció del repo: `python manage.py test fhort.tasks` (el projecte NO fa servir pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import (Customer, GarmentTypeItem, ModelTask, TaskTimeEstimate,
                                TaskType, TimerEntrada)
from fhort.tasks.services_c import ALLOWED, TransitionError, transition_task
from fhort.tasks.services_i import MAX_MINUTS_TRAM

TRAM_DESBOCAT = 3710


class StopEncadenatTest(TenantTestCase):

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

        self.user = get_user_model().objects.create(username='tecstop')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.customer = Customer.objects.create(codi='CLI', nom='Client de prova')
        gt = GarmentType.objects.create(codi_client='GTS', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_s', name='Item S')
        self.tt = TaskType.objects.create(code='task_s', name='Task S', fase='Dev. tècnic')
        self.Model = Model
        self._seq = 0

    def _model(self):
        self._seq += 1
        return self.Model.objects.create(
            codi_intern=f'TST-SS26-{self._seq:04d}', codi_tenant='TST', any=2026,
            temporada='SS', sequencial=self._seq, customer=self.customer,
            garment_type_item=self.item, nom_prenda='Peça')

    def _tasca_pausada(self, minuts_treballats):
        """Una tasca treballada `minuts_treballats` i PAUSADA — l'estat de partida del gest."""
        task = ModelTask.objects.create(model=self._model(), task_type=self.tt, order=0,
                                        status='Pending', assignee=self.prof)
        transition_task(task, 'InProgress', self.prof)
        timer = TimerEntrada.objects.get(model_task=task, fi__isnull=True, actiu=True)
        TimerEntrada.objects.filter(pk=timer.pk).update(
            inici=timezone.now() - datetime.timedelta(minutes=minuts_treballats))
        transition_task(task, 'Paused', self.prof)
        task.refresh_from_db()
        self.assertEqual(task.status, 'Paused')
        return task

    def _gest_stop(self, task):
        """El gest: play+stop encadenat. El segon pas NOMÉS si el primer ha anat bé — mateixa
        seqüència que farà el front (i mateixa raó: cap estat intermedi silenciós)."""
        transition_task(task, 'InProgress', self.prof)
        task.refresh_from_db()
        transition_task(task, 'Done', self.prof)
        task.refresh_from_db()
        return task

    # ── La màquina d'estats NO s'ha tocat ────────────────────────────────────
    def test_paused_a_done_directe_segueix_prohibida(self):
        task = self._tasca_pausada(40)
        with self.assertRaises(TransitionError):
            transition_task(task, 'Done', self.prof)
        self.assertNotIn('Done', ALLOWED['Paused'])

    # ── El gest fa el que ha de fer ──────────────────────────────────────────
    def test_el_gest_tanca_la_tasca_i_el_timer(self):
        """CONFIRMACIÓ (no assumpció) que l'encadenat passa per la branca frm=='InProgress'
        de transition_task:224-227."""
        task = self._gest_stop(self._tasca_pausada(40))

        self.assertEqual(task.status, 'Done')
        self.assertIsNotNone(task.finished_at, 'finished_at ha de quedar escrit')
        self.assertFalse(
            TimerEntrada.objects.filter(model_task=task, fi__isnull=True).exists(),
            'el gest no pot deixar cap tram obert')
        self.assertFalse(
            TimerEntrada.objects.filter(model_task=task, actiu=True).exists(),
            'cap tram viu després del Stop')

    def test_el_tram_del_gest_es_tanca_amb_els_segons_reals(self):
        """El tram que obre l'encadenat dura el que dura: un gest instantani són 0 min, i és
        la veritat (`//60` de pocs segons). El que NO pot passar és que quedi obert o amb
        `minuts` a NULL — això sí seria un residu."""
        task = self._tasca_pausada(40)
        abans = set(TimerEntrada.objects.filter(model_task=task).values_list('pk', flat=True))
        self._gest_stop(task)

        nou = TimerEntrada.objects.filter(model_task=task).exclude(pk__in=abans).get()
        self.assertIsNotNone(nou.fi)
        self.assertIsNotNone(nou.minuts, 'minuts NULL = tram no consolidat (residu)')
        self.assertEqual(nou.minuts, 0)
        self.assertEqual(nou.minuts, max(0, int((nou.fi - nou.inici).total_seconds() // 60)))

    def test_el_gest_no_infla_el_temps_de_la_tasca(self):
        """El play del gest no és feina nova: el temps consolidat després del Stop ha de ser
        el mateix que abans (el tram nou val 0)."""
        from fhort.tasks.services_i import _real_minutes
        task = self._tasca_pausada(40)
        abans = _real_minutes(task)
        self._gest_stop(task)
        self.assertEqual(_real_minutes(task), abans)
        self.assertEqual(abans, 40)

    # ── Dependència amb S1: el gest no pot injectar hores falses ─────────────
    def test_el_gest_sobre_un_tram_desbocat_no_injecta_hores_falses(self):
        """Una tasca oblidada (tram de 61 h) que es tanca amb el gest. El Welford ha de rebre
        la mostra FILTRADA. Sense S1, aquesta cel·la naixeria amb una mitjana de 61 h i el
        planificador la faria servir com si fos real."""
        task = self._tasca_pausada(TRAM_DESBOCAT)
        self._gest_stop(task)

        cella = TaskTimeEstimate.objects.filter(
            garment_type_item=self.item, task_type=self.tt).first()
        # `_real_minutes` filtrat = 0 → `record_actual_time` descarta x<=0 → cap cel·la.
        self.assertIsNone(cella, 'cap mostra: del tram desbocat no en tenim dada')

    def test_el_gest_aporta_nomes_el_temps_sa(self):
        """Variant amb barreja: 45 min sans + un tram desbocat. La mostra ha de ser 45, no
        45+3710. El gest tanca la tasca; la mentida no hi entra."""
        task = self._tasca_pausada(45)
        TimerEntrada.objects.create(
            model_task=task, tecnic=self.prof,
            inici=timezone.now() - datetime.timedelta(minutes=TRAM_DESBOCAT),
            fi=timezone.now(), minuts=TRAM_DESBOCAT, actiu=False)
        self._gest_stop(task)

        cella = TaskTimeEstimate.objects.get(garment_type_item=self.item, task_type=self.tt)
        self.assertEqual(cella.n, 1)
        self.assertEqual(int(cella.mean_minutes), 45)
        self.assertLess(cella.mean_minutes, MAX_MINUTS_TRAM)
