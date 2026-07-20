"""D3 — unassign_model_from_order_line: orfanda un WorkOrder ORDER, allibera cartera i
respecta els guards durs (ORDER, OPEN, no albaranat)."""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django_tenants.test.cases import TenantTestCase

from fhort.tasks.models import Customer, ModelTask, TaskType
from fhort.commerce.models import (Product, SalesOrder, SalesOrderLine, WorkOrder,
                                   DeliveryNote, DeliveryNoteLine)
from fhort.commerce.services import (assign_model_to_order_line,
                                    unassign_model_from_order_line)
from fhort.models_app.models import Model


class UnassignModelTest(TenantTestCase):

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
        get_user_model().objects.create(username='tester')
        self.customer = Customer.objects.create(codi='CLI', nom='Client Test')
        self.product = Product.objects.create(
            code='SRV-1', name='Servei', nature='INTERNAL_SERVICE', tax_rate=Decimal('21.00'))

    def _assign(self):
        order = SalesOrder.objects.create(customer=self.customer)
        line = SalesOrderLine.objects.create(
            order=order, product=self.product, quantity=Decimal('2'),
            unit_price=Decimal('50'), line_total=Decimal('100'), position=1)
        model = Model.objects.create(
            codi_intern='TST-1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M', customer=self.customer)
        wo, _ = assign_model_to_order_line(model, line)
        return wo, line, model

    def test_unassign_orfanda_i_allibera_cartera(self):
        wo, line, _ = self._assign()
        line.refresh_from_db()
        self.assertEqual(line.qty_allocated, Decimal('1.00'))

        wo2 = unassign_model_from_order_line(wo)
        wo2.refresh_from_db(); line.refresh_from_db()
        self.assertIsNone(wo2.order_line_id, "order_line ha de quedar buida")
        self.assertEqual(wo2.orphaned_from_line_id, line.id, "orphaned_from_line ha de guardar la traça")
        self.assertEqual(line.qty_allocated, Decimal('0.00'), "s'allibera 1 unitat de cartera")
        self.assertEqual(wo2.status, 'OPEN')

    def test_modeltask_no_es_toquen(self):
        """Les ModelTask migrades es queden intactes al WO orfe (decisió conscient D3)."""
        wo, _, model = self._assign()
        # Crea una tasca penjada del WO (com faria la migració del col·lector).
        tt = TaskType.objects.filter(active=True).first() or TaskType.objects.create(
            code='x', name='X', tool='mesures', mode='presa')
        task = ModelTask.objects.create(model=model, task_type=tt, work_order=wo, status='Pending')
        unassign_model_from_order_line(wo)
        task.refresh_from_db()
        self.assertEqual(task.work_order_id, wo.id, "la ModelTask segueix al WO orfe, no es reverteix")

    def test_guard_ja_albaranat(self):
        wo, _, _ = self._assign()
        dn = DeliveryNote.objects.create(customer=self.customer)
        DeliveryNoteLine.objects.create(
            delivery_note=dn, product=None, work_order=wo, line_kind='TASK',
            quantity=Decimal('1'), unit_price=Decimal('10'), line_total=Decimal('10'), position=1)
        with self.assertRaises(ValidationError):
            unassign_model_from_order_line(wo)

    def test_guard_closed(self):
        wo, _, _ = self._assign()
        wo.status = 'CLOSED'; wo.save(update_fields=['status'])
        with self.assertRaises(ValidationError):
            unassign_model_from_order_line(wo)

    def test_guard_collector(self):
        wo = WorkOrder.objects.create(customer=self.customer, kind='COLLECTOR', period='2026-07')
        with self.assertRaises(ValidationError):
            unassign_model_from_order_line(wo)

    def test_guard_sense_linia(self):
        wo = WorkOrder.objects.create(customer=self.customer, kind='ORDER', order_line=None)
        with self.assertRaises(ValidationError):
            unassign_model_from_order_line(wo)
