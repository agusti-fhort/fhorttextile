"""`recompute_welford` — la propietat que el fa fiable (27/07).

Convenció del repo: fitxer `test*.py` dins de l'app, executat amb
`python manage.py test fhort.tasks` (el projecte NO fa servir pytest).

El recompute només és de fiar si reprodueix EXACTAMENT el que el camí viu hauria escrit. És
una propietat d'identitat, i és el que aquests tests fixen — perquè la primera versió NO la
complia: arrodonia la mitjana abans de fer-la servir per a `m2` (la BD quantitza en DESAR, no
dins de la crida) i marcava com a «corregides» cel·les perfectament sanes. A `fhort` eren 3 de
455; en un tenant amb història llarga, la diferència entre netejar i trepitjar.

I fixen també les dues decisions de Patró C que el separen d'un recompute ingenu:
  · trams de més de 24 h fora de la mostra (regla d'higiene compartida amb la data-op),
  · una cel·la sense cap tasca supervivent NO es toca (és l'últim rastre d'aquella feina).
"""
import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import (Customer, GarmentTypeItem, ModelTask, TaskTimeEstimate,
                                TaskType, TimerEntrada)
from fhort.tasks.services_c import transition_task
from fhort.tasks.services_i import MAX_MINUTS_TRAM


class RecomputeWelfordTest(TenantTestCase):

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

        self.user = get_user_model().objects.create(username='tecwelford')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.customer = Customer.objects.create(codi='CLI', nom='Client de prova')
        gt = GarmentType.objects.create(codi_client='GTW', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_w', name='Item W')
        self.tt = TaskType.objects.create(code='task_w', name='Task W', fase='Dev. tècnic')
        self.Model = Model
        self._seq = 0

    def _model(self):
        self._seq += 1
        return self.Model.objects.create(
            codi_intern=f'TST-SS26-{self._seq:04d}', codi_tenant='TST', any=2026,
            temporada='SS', sequencial=self._seq, customer=self.customer,
            garment_type_item=self.item, nom_prenda='Peça')

    def _tasca_treballada(self, minuts):
        """Una tasca oberta, treballada `minuts` i tancada — pel camí VIU (alimenta el Welford)."""
        task = ModelTask.objects.create(model=self._model(), task_type=self.tt, order=0,
                                        status='Pending', assignee=self.prof)
        transition_task(task, 'InProgress', self.prof)
        timer = TimerEntrada.objects.get(model_task=task, fi__isnull=True, actiu=True)
        TimerEntrada.objects.filter(pk=timer.pk).update(
            inici=timezone.now() - datetime.timedelta(minutes=minuts))
        transition_task(task, 'Done', self.prof)
        return task

    def _cella(self):
        return TaskTimeEstimate.objects.get(garment_type_item=self.item, task_type=self.tt)

    def _recompute(self, **kwargs):
        out = StringIO()
        call_command('recompute_welford', tenant=connection.schema_name, stdout=out, **kwargs)
        return out.getvalue()

    # ── La propietat: recomputar el que el camí viu ha escrit no ha de moure res ──
    def test_reprodueix_exactament_una_cella_sana(self):
        for m in (12, 47, 30, 65, 41, 53, 28):
            self._tasca_treballada(m)
        c = self._cella()
        abans = (c.n, c.mean_minutes, c.m2)
        self.assertEqual(c.n, 7)

        sortida = self._recompute()
        c.refresh_from_db()
        self.assertEqual((c.n, c.mean_minutes, c.m2), abans)
        self.assertIn('0 cel·la/es a corregir', sortida)

    def test_una_tasca_reoberta_compta_com_a_mostra_NOVA(self):
        """`record_actual_time` es crida a CADA →Done: re-tancar aporta una altra mostra, amb el
        total acumulat. Si el recompute no ho reproduís, n baixaria i la mitjana es mouria."""
        task = self._tasca_treballada(20)
        transition_task(task, 'InProgress', self.prof)   # rectificació
        transition_task(task, 'Done', self.prof)
        c = self._cella()
        self.assertEqual(c.n, 2)
        abans = (c.n, c.mean_minutes, c.m2)

        self._recompute()
        c.refresh_from_db()
        self.assertEqual((c.n, c.mean_minutes, c.m2), abans)

    # ── Regla d'higiene ─────────────────────────────────────────────────────
    def test_un_tram_impossible_surt_de_la_mostra(self):
        self._tasca_treballada(30)
        zombi = self._tasca_treballada(MAX_MINUTS_TRAM + 500)
        c = self._cella()
        self.assertEqual(c.n, 2)
        self.assertGreater(c.mean_minutes, MAX_MINUTS_TRAM / 2)   # la mitjana ja menteix

        self._recompute(apply=True)
        c.refresh_from_db()
        self.assertEqual(c.n, 1, 'la mostra del tram impossible ha de caure')
        self.assertEqual(int(c.mean_minutes), 30)
        # La FILA del tram es conserva: la higiene és de la mostra, no de la traça.
        self.assertTrue(TimerEntrada.objects.filter(model_task=zombi).exists())

    def test_el_llindar_es_estricte_no_toca_el_que_hi_arriba_just(self):
        self._tasca_treballada(MAX_MINUTS_TRAM)
        c = self._cella()
        abans = (c.n, c.mean_minutes)
        self._recompute(apply=True)
        c.refresh_from_db()
        self.assertEqual((c.n, c.mean_minutes), abans)

    # ── Cel·les sense proves vives ──────────────────────────────────────────
    def test_una_cella_sense_tasques_supervivents_no_es_toca(self):
        """Esborrar una ModelTask s'emporta timers i transicions en CASCADE. La cel·la queda com
        a únic rastre: posar-la a zero seria deduir absència de l'absència de proves."""
        task = self._tasca_treballada(35)
        c = self._cella()
        abans = (c.n, c.mean_minutes, c.m2)
        ModelTask.objects.filter(pk=task.pk).delete()

        sortida = self._recompute(apply=True)
        c.refresh_from_db()
        self.assertEqual((c.n, c.mean_minutes, c.m2), abans)
        self.assertIn('sense cap tasca supervivent', sortida)

    def test_dry_run_no_escriu(self):
        self._tasca_treballada(30)
        self._tasca_treballada(MAX_MINUTS_TRAM + 500)
        c = self._cella()
        abans = (c.n, c.mean_minutes, c.m2)
        sortida = self._recompute()
        c.refresh_from_db()
        self.assertEqual((c.n, c.mean_minutes, c.m2), abans)
        self.assertIn('dry-run', sortida)

    def test_es_idempotent(self):
        self._tasca_treballada(30)
        self._tasca_treballada(MAX_MINUTS_TRAM + 500)
        self._recompute(apply=True)
        c = self._cella()
        despres = (c.n, c.mean_minutes, c.m2)
        sortida = self._recompute(apply=True)
        c.refresh_from_db()
        self.assertEqual((c.n, c.mean_minutes, c.m2), despres)
        self.assertIn('0 cel·la/es a corregir', sortida)
