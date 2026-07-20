"""D2 — un WorkOrder ORFE (order_line=None) ha d'albarar amb l'IVA CONGELAT del snapshot,
no a 0%. Abans, compute_document_totals derivava el tipus de line.product (None a l'orfe → 0%).
Ara el price_snapshot congela `tax_rate` a l'assignació i compute_document_totals el llegeix via
line.work_order quan la línia no té product.
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.tasks.models import Customer
from fhort.commerce.models import Product, WorkOrder, DeliveryNote, DeliveryNoteLine


class OrphanWorkOrderIvaTest(TenantTestCase):

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
        self.customer = Customer.objects.create(codi='CLI', nom='Client Test')  # tax_regime=DOMESTIC
        self.product = Product.objects.create(
            code='SRV-1', name='Servei intern', nature='INTERNAL_SERVICE', tax_rate=Decimal('21.00'))

    def _delivery_with_orphan_line(self, snapshot):
        """Un albarà DRAFT amb UNA línia sense product que ve d'un WO orfe amb el snapshot donat."""
        wo = WorkOrder.objects.create(
            customer=self.customer, kind='ORDER', status='OPEN',
            order_line=None, price_snapshot=snapshot, recipe_snapshot={})
        dn = DeliveryNote.objects.create(customer=self.customer)   # status DRAFT per defecte
        DeliveryNoteLine.objects.create(
            delivery_note=dn, product=None, work_order=wo, line_kind='TASK',
            quantity=Decimal('1'), unit_price=Decimal('100'), line_total=Decimal('100'),
            position=1, visible=True)
        return dn

    def test_orfe_albara_amb_iva_congelat(self):
        """order_line=None + snapshot tax_rate=21 → IVA 21%, no 0%."""
        dn = self._delivery_with_orphan_line(
            {'unit_price': '100', 'product_code': 'SRV-1', 'tax_rate': '21.00'})
        dn.recalculate_totals()
        self.assertEqual(dn.subtotal, Decimal('100.00'))
        self.assertEqual(dn.tax_amount, Decimal('21.00'),
                         "El WO orfe ha d'albarar amb l'IVA congelat del snapshot, no a 0%")
        self.assertEqual(dn.total, Decimal('121.00'))

    def test_snapshot_sense_tax_rate_cau_a_zero(self):
        """Control: sense tax_rate al snapshot (dades antigues), es manté el 0% d'abans."""
        dn = self._delivery_with_orphan_line({'unit_price': '100', 'product_code': 'SRV-1'})
        dn.recalculate_totals()
        self.assertEqual(dn.tax_amount, Decimal('0.00'))

    def test_assign_congela_tax_rate_al_snapshot(self):
        """El camí d'assignació escriu tax_rate al price_snapshot (prerequisit del fix)."""
        from fhort.commerce.services import assign_model_to_order_line
        from fhort.commerce.models import SalesOrder, SalesOrderLine
        from fhort.models_app.models import Model
        order = SalesOrder.objects.create(customer=self.customer)
        line = SalesOrderLine.objects.create(
            order=order, product=self.product, quantity=Decimal('2'),
            unit_price=Decimal('50'), line_total=Decimal('100'), position=1)
        model = Model.objects.create(
            codi_intern='TST-1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
            customer=self.customer)
        wo, meta = assign_model_to_order_line(model, line)
        self.assertEqual(wo.price_snapshot.get('tax_rate'), '21.00',
                         "assign ha de congelar tax_rate del product al snapshot")
