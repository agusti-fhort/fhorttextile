"""F1.3 · EL BATEC D'ESCRIPTURA — `tasks/services_batec`.

El rellotge corria NOMÉS entre `enterEdit` i `exitEdit` de dues superfícies. D'una hora de
treball real en sortien registrats entre 0 i 60 minuts, i el que ho decidia no era quant s'havia
treballat sinó si la porta havia quedat oberta. A partir d'ara, **escriure és el senyal**.

Els tres casos que el brief demana —renova, reobre, no-op sense tasca— i els guards que fan que
el batec sigui observació i no una segona màquina d'estats.

Convenció del repo: `python manage.py test fhort.tasks.test_batec_escriptura` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import (Customer, GarmentTypeItem, ModelTask, TaskTransition, TaskType,
                                TimerEntrada)
from fhort.tasks.services_batec import SUP_MESURES, batec_escriptura
from fhort.tasks.services_c import transition_task


class BatecEscripturaTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TBA'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='tecbatec')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.altre_user = get_user_model().objects.create(username='tecaltre')
        self.altre, _ = UserProfile.objects.get_or_create(user=self.altre_user)
        self.customer = Customer.objects.create(codi='CBA', nom='Client de prova')
        gt = GarmentType.objects.create(codi_client='GTB', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_b', name='Item B')
        self.tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(
            codi_intern='TBA-SS26-0001', codi_tenant='TBA', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item, nom_prenda='Peça')

    def _tasca(self, status='Pending'):
        return ModelTask.objects.create(model=self.model, task_type=self.tt, order=0,
                                        status=status, origen='prevista')

    # ── Cas 1 · REOBRE (el batec fort) ───────────────────────────────────────
    def test_pending_passa_a_inprogress_i_obre_tram(self):
        task = self._tasca('Pending')
        res = batec_escriptura(self.model, SUP_MESURES, self.prof)
        task.refresh_from_db()
        self.assertEqual(res['accio'], 'oberta')
        self.assertEqual(task.status, 'InProgress')
        self.assertEqual(
            TimerEntrada.objects.filter(model_task=task, fi__isnull=True).count(), 1)

    def test_paused_passa_a_inprogress(self):
        task = self._tasca('Pending')
        transition_task(task, 'InProgress', self.prof)
        transition_task(task, 'Paused', self.prof)
        batec_escriptura(self.model, SUP_MESURES, self.prof)
        task.refresh_from_db()
        self.assertEqual(task.status, 'InProgress')

    # ── Cas 2 · RENOVA ───────────────────────────────────────────────────────
    def test_inprogress_renova_el_segell_i_no_transiciona(self):
        """El batec normal no ha d'escriure cap transició: si ho fes, tornaríem al ping-pong
        per l'altra banda (una fila de log per cada `PATCH` d'una cel·la)."""
        task = self._tasca('Pending')
        transition_task(task, 'InProgress', self.prof)
        n_trans = TaskTransition.objects.filter(model_task=task).count()
        tram = TimerEntrada.objects.get(model_task=task, fi__isnull=True)
        self.assertIsNone(tram.last_heartbeat)

        res = batec_escriptura(self.model, SUP_MESURES, self.prof)

        tram.refresh_from_db()
        self.assertEqual(res['accio'], 'renovat')
        self.assertIsNotNone(tram.last_heartbeat)
        self.assertEqual(TaskTransition.objects.filter(model_task=task).count(), n_trans)

    def test_el_batec_no_toca_el_tram_d_un_altre_tecnic(self):
        """Handoff a mitges: el rellotge de l'altre és seu i no es renova des d'aquí."""
        task = self._tasca('Pending')
        transition_task(task, 'InProgress', self.altre)
        res = batec_escriptura(self.model, SUP_MESURES, self.prof)
        tram_altre = TimerEntrada.objects.get(model_task=task, tecnic=self.altre)
        self.assertEqual(res['accio'], 'sense_tram')
        self.assertIsNone(tram_altre.last_heartbeat)

    # ── Cas 3 · NO-OP ────────────────────────────────────────────────────────
    def test_sense_tasca_no_fa_res_i_NO_en_crea_cap(self):
        """El batec no és una porta de gènesi: un PATCH sobre una mesura no pot fer néixer una
        tasca de POM que el PM no ha planificat."""
        res = batec_escriptura(self.model, SUP_MESURES, self.prof)
        self.assertEqual(res['accio'], 'sense_tasca')
        self.assertFalse(res['batec'])
        self.assertEqual(ModelTask.objects.filter(model=self.model).count(), 0)

    def test_sense_perfil_no_peta(self):
        self._tasca('Pending')
        res = batec_escriptura(self.model, SUP_MESURES, None)
        self.assertEqual(res['accio'], 'sense_perfil')

    def test_code_inexistent_no_peta(self):
        self._tasca('Pending')
        res = batec_escriptura(self.model, 'no_existeix_aquest_code', self.prof)
        self.assertEqual(res['accio'], 'sense_tasca')

    # ── El batec és observació: mai llança ───────────────────────────────────
    def test_la_paret_d_albara_es_refusa_sense_llancar(self):
        """Una tasca Done amb línia en albarà EMÈS no es reobre (D-5): el batec ho ACCEPTA i
        retorna `refusada` amb el codi, perquè qui vulgui treballar-hi obri una RONDA. El que no
        pot fer és propagar l'excepció i tombar el PATCH que l'ha disparat."""
        from fhort.commerce.models import DeliveryNote, DeliveryNoteLine

        task = self._tasca('Pending')
        transition_task(task, 'InProgress', self.prof)
        transition_task(task, 'Done', self.prof)
        # Les línies només s'escriuen en DRAFT (`DeliveryNoteLine._assert_editable`): l'albarà
        # s'emet DESPRÉS, que és també l'ordre real del flux comercial.
        dn = DeliveryNote.objects.create(customer=self.customer, status='DRAFT')
        DeliveryNoteLine.objects.create(delivery_note=dn, model_task=task, line_kind='TASK',
                                        quantity=1, unit_price=0, position=1)
        DeliveryNote.objects.filter(pk=dn.pk).update(status='ISSUED')

        res = batec_escriptura(self.model, SUP_MESURES, self.prof)

        task.refresh_from_db()
        self.assertEqual(res['accio'], 'refusada')
        self.assertEqual(res.get('code'), 'tasca_albaranada')
        self.assertEqual(task.status, 'Done')
