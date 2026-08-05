"""F1.7 · D-2 — EL TEMPS DECLARAT (`services_r.declara_temps`).

Tercera pota de D-2: «externes = temps declarat». Una tasca `Externa-lliure` —patró a mà, revisió
de disseny, aclariments— es fa **fora de l'eina**. No hi ha cap escriptura que batre i el rellotge
no hi arriba mai, de manera que fins avui aquell temps no existia enlloc.

El que es fixa:
  · El XOR de les dues formes (`minuts` o bé `inici`+`fi`).
  · El guard dur: sobre una tasca INTERNA es rebutja. Allà el temps es mesura sol, i declarar-lo
    a mà seria poder inventar hores facturables sobre feina observable.
  · El tram neix TANCAT i el Welford l'aprèn com qualsevol altre (una tasca, una mostra — D-3).

Convenció del repo: `python manage.py test fhort.tasks.test_temps_declarat` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, GarmentTypeItem, ModelTask, TaskType, TimerEntrada
from fhort.tasks.services_i import MAX_MINUTS_TRAM, _real_minutes
from fhort.tasks.services_r import TempsDeclaratError, declara_temps


class TempsDeclaratTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TTD'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='tecdecl')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.customer = Customer.objects.create(codi='CTD', nom='Client de prova')
        gt = GarmentType.objects.create(codi_client='GTD', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_d', name='Item D')
        self.tt_externa = TaskType.objects.create(code='tt_ext', name='Externa',
                                                  fase='Dev. tècnic', tipus='Externa-lliure')
        self.tt_interna = TaskType.objects.create(code='tt_int', name='Interna',
                                                  fase='Dev. tècnic', tipus='Interna')
        self.model = Model.objects.create(
            codi_intern='TTD-SS26-0001', codi_tenant='TTD', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item, nom_prenda='Peça')

    def _tasca(self, tt):
        return ModelTask.objects.create(model=self.model, task_type=tt, order=0,
                                        status='Pending', assignee=self.prof)

    # ── El guard dur ─────────────────────────────────────────────────────────
    def test_una_tasca_interna_no_admet_temps_declarat(self):
        """El temps de les internes es mesura sol: declarar-lo a mà seria inventar hores
        facturables sobre feina que l'eina SÍ observa."""
        with self.assertRaises(TempsDeclaratError):
            declara_temps(self._tasca(self.tt_interna), self.prof, minuts=90)

    def test_sense_perfil_es_rebutja(self):
        with self.assertRaises(TempsDeclaratError):
            declara_temps(self._tasca(self.tt_externa), None, minuts=90)

    # ── El XOR ───────────────────────────────────────────────────────────────
    def test_minuts_i_franja_alhora_es_rebutgen(self):
        ara = timezone.now()
        with self.assertRaises(TempsDeclaratError):
            declara_temps(self._tasca(self.tt_externa), self.prof, minuts=90,
                          inici=ara - datetime.timedelta(hours=1), fi=ara)

    def test_ni_minuts_ni_franja_es_rebutja(self):
        with self.assertRaises(TempsDeclaratError):
            declara_temps(self._tasca(self.tt_externa), self.prof)

    def test_franja_incompleta_es_rebutja(self):
        with self.assertRaises(TempsDeclaratError):
            declara_temps(self._tasca(self.tt_externa), self.prof, inici=timezone.now())

    def test_franja_invertida_es_rebutja(self):
        ara = timezone.now()
        with self.assertRaises(TempsDeclaratError):
            declara_temps(self._tasca(self.tt_externa), self.prof,
                          inici=ara, fi=ara - datetime.timedelta(hours=1))

    # ── Els límits ───────────────────────────────────────────────────────────
    def test_zero_minuts_es_rebutja(self):
        with self.assertRaises(TempsDeclaratError):
            declara_temps(self._tasca(self.tt_externa), self.prof, minuts=0)

    def test_per_sobre_del_sostre_es_rebutja_en_comptes_d_excloure_s_despres(self):
        """`MAX_MINUTS_TRAM` exclou els trams desbocats de les lectures. Un tram declarat que el
        superi s'ha de rebutjar a la cara, no acceptar-lo i ignorar-lo després en silenci."""
        with self.assertRaises(TempsDeclaratError):
            declara_temps(self._tasca(self.tt_externa), self.prof, minuts=MAX_MINUTS_TRAM + 1)

    # ── El camí feliç ────────────────────────────────────────────────────────
    def test_minuts_crea_un_tram_tancat_i_declarat(self):
        task = self._tasca(self.tt_externa)
        tram = declara_temps(task, self.prof, minuts=90)
        self.assertEqual(tram.minuts, 90)
        self.assertEqual(tram.origen, TimerEntrada.ORIGEN_DECLARAT)
        self.assertIsNotNone(tram.fi)
        self.assertFalse(tram.actiu)
        self.assertEqual(tram.tecnic, self.prof)
        self.assertEqual(int((tram.fi - tram.inici).total_seconds() // 60), 90)

    def test_franja_calcula_els_minuts(self):
        task = self._tasca(self.tt_externa)
        fi = timezone.now()
        tram = declara_temps(task, self.prof, inici=fi - datetime.timedelta(minutes=45), fi=fi)
        self.assertEqual(tram.minuts, 45)
        self.assertEqual(tram.origen, TimerEntrada.ORIGEN_DECLARAT)

    def test_el_tram_declarat_compta_com_a_temps_real(self):
        """D-3: una tasca és una mostra, tant si el temps s'ha comptat sol com si l'ha dit algú."""
        task = self._tasca(self.tt_externa)
        declara_temps(task, self.prof, minuts=90)
        self.assertEqual(_real_minutes(task), 90)

    def test_dues_declaracions_sumen(self):
        task = self._tasca(self.tt_externa)
        declara_temps(task, self.prof, minuts=30)
        declara_temps(task, self.prof, minuts=45)
        self.assertEqual(_real_minutes(task), 75)

    def test_els_trams_mesurats_no_es_confonen_amb_els_declarats(self):
        from fhort.tasks.services_c import transition_task
        task = self._tasca(self.tt_externa)
        transition_task(task, 'InProgress', self.prof)
        declara_temps(task, self.prof, minuts=30)
        self.assertEqual(
            TimerEntrada.objects.filter(model_task=task,
                                        origen=TimerEntrada.ORIGEN_MESURAT).count(), 1)
        self.assertEqual(
            TimerEntrada.objects.filter(model_task=task,
                                        origen=TimerEntrada.ORIGEN_DECLARAT).count(), 1)
