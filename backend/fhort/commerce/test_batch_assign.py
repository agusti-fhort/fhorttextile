"""Sprint C · H1 — batch d'assignació de models a comanda + bulk d'intents a oferta.

Convenció del repo: `python manage.py test fhort.commerce`. Defensa:
  - capacitat conjunta (N cap, N+1 rebutjat amb el màxim al missatge)
  - TOT-O-RES (si un model del lot viola un guard, CAP s'assigna)
  - select_for_update present (serialització de batches concurrents)
  - bulk d'intents: duplicats existents skipped, sense petar
"""
import datetime
import inspect
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django_tenants.test.cases import TenantTestCase

from fhort.tasks.models import Customer
from fhort.commerce.models import (Product, SalesOrder, SalesOrderLine, WorkOrder,
                                    Quote, QuoteLine, QuoteLineModelIntent)
from fhort.commerce import services
from fhort.commerce.services import (assign_models_to_order_line_batch,
                                     create_quote_line_intents_bulk)
from fhort.models_app.models import Model


class _Base(TenantTestCase):

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
        self.other = Customer.objects.create(codi='CL2', nom='Altre Client')
        self.product = Product.objects.create(
            code='SRV-1', name='Servei', nature='INTERNAL_SERVICE', tax_rate=Decimal('21.00'))
        self._seq = 0

    def _model(self, customer=None):
        self._seq += 1
        return Model.objects.create(
            codi_intern=f'TST-{self._seq}', codi_tenant='TST', any=2026, sequencial=self._seq,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
            customer=customer or self.customer)

    def _line(self, qty='3'):
        order = SalesOrder.objects.create(customer=self.customer)
        return SalesOrderLine.objects.create(
            order=order, product=self.product, quantity=Decimal(qty),
            unit_price=Decimal('50'), line_total=Decimal(qty) * Decimal('50'), position=1)


class BatchAssignTest(_Base):

    def test_assigns_all_within_capacity(self):
        line = self._line(qty='3')
        models = [self._model(), self._model(), self._model()]
        wos, warnings = assign_models_to_order_line_batch(line.id, [m.id for m in models])
        self.assertEqual(len(wos), 3)
        line.refresh_from_db()
        self.assertEqual(line.qty_allocated, Decimal('3.00'))
        self.assertEqual(WorkOrder.objects.filter(order_line=line, kind='ORDER').count(), 3)

    def test_over_capacity_rejected_with_max(self):
        line = self._line(qty='2')
        models = [self._model(), self._model(), self._model()]   # 3 > 2
        with self.assertRaises(ValidationError) as cm:
            assign_models_to_order_line_batch(line.id, [m.id for m in models])
        self.assertIn('2', '; '.join(cm.exception.messages))   # màxim disponible al missatge
        # CAP assignat: cartera intacta i cap WO.
        line.refresh_from_db()
        self.assertEqual(line.qty_allocated, Decimal('0'))
        self.assertEqual(WorkOrder.objects.filter(order_line=line).count(), 0)

    def test_all_or_nothing_on_conflict(self):
        """El segon model del lot ja té un WO ORDER obert → CAP s'assigna (ni el primer, sà)."""
        line = self._line(qty='3')
        m_ok = self._model()
        m_conflict = self._model()
        # m_conflict ja té un encàrrec actiu (dualitat) en una ALTRA comanda.
        other_line = self._line(qty='1')
        assign_models_to_order_line_batch(other_line.id, [m_conflict.id])

        with self.assertRaises(ValidationError) as cm:
            assign_models_to_order_line_batch(line.id, [m_ok.id, m_conflict.id])
        self.assertIn(m_conflict.codi_intern, '; '.join(cm.exception.messages))
        # Rollback total: la línia objectiu queda intacta, ni tan sols el m_ok sà.
        line.refresh_from_db()
        self.assertEqual(line.qty_allocated, Decimal('0'))
        self.assertEqual(WorkOrder.objects.filter(order_line=line).count(), 0)
        self.assertFalse(WorkOrder.objects.filter(model=m_ok).exists())

    def test_select_for_update_present(self):
        """El batch bloqueja la fila de la línia (serialitza batches concurrents, evita lost-update)."""
        src = inspect.getsource(services.assign_models_to_order_line_batch)
        self.assertIn('select_for_update', src)


class BulkIntentsTest(_Base):

    def _quote_line(self):
        quote = Quote.objects.create(customer=self.customer)   # DRAFT per defecte
        return QuoteLine.objects.create(
            quote=quote, product=self.product, quantity=Decimal('3'),
            unit_price=Decimal('50'), line_total=Decimal('150'), position=1)

    def test_bulk_creates_and_skips_duplicates(self):
        line = self._quote_line()
        m_a, m_b = self._model(), self._model()
        QuoteLineModelIntent.objects.create(quote_line=line, model=m_a)   # ja existent
        res = create_quote_line_intents_bulk(line, [m_a.id, m_b.id])
        self.assertEqual(res['skipped'], [m_a.id])
        self.assertEqual(len(res['created']), 1)
        self.assertEqual(QuoteLineModelIntent.objects.filter(quote_line=line).count(), 2)

    def test_bulk_guard_customer(self):
        line = self._quote_line()
        m_other = self._model(customer=self.other)
        with self.assertRaises(ValidationError):
            create_quote_line_intents_bulk(line, [m_other.id])
        self.assertEqual(QuoteLineModelIntent.objects.filter(quote_line=line).count(), 0)

    def test_bulk_guard_quote_status(self):
        line = self._quote_line()   # línia creada en DRAFT…
        line.quote.status = 'ACCEPTED'   # …i l'oferta passa a ACCEPTED (ja convertida)
        line.quote.save(update_fields=['status'])
        m = self._model()
        with self.assertRaises(ValidationError):
            create_quote_line_intents_bulk(line, [m.id])
