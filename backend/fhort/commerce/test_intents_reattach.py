"""Tests del vincle preparatori (QuoteLineModelIntent) i de la re-adopció d'un WO orfe:
- E1: unique_together (quote_line, model) + CASCADE en esborrar el model.
- E3: propagació en convertir oferta→comanda pels TRES camins (lliure/conflicte/orfe).
- E4: reattach_orphan_to_line — els 7 guards + re-congelació del snapshot + orphaned null.
"""
import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.tasks.models import Customer
from fhort.commerce.models import (Product, Quote, QuoteLine, QuoteLineModelIntent,
                                    SalesOrder, SalesOrderLine, WorkOrder, DeliveryNote,
                                    DeliveryNoteLine)
from fhort.commerce.services import (assign_model_to_order_line, unassign_model_from_order_line,
                                     reattach_orphan_to_line, convert_quote_to_order)
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
        self.customer = Customer.objects.create(codi='CLI', nom='Client Test')
        self.other = Customer.objects.create(codi='CL2', nom='Altre Client')
        self.product = Product.objects.create(
            code='SRV-1', name='Servei', nature='INTERNAL_SERVICE',
            base_price=Decimal('50.00'), tax_rate=Decimal('21.00'))
        self._seq = 0

    def _model(self, customer=None):
        self._seq += 1
        return Model.objects.create(
            codi_intern=f'TST-{self._seq}', codi_tenant='TST', any=2026, sequencial=self._seq,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
            customer=customer or self.customer)

    def _line(self, order, product=None, qty='2', price='50'):
        return SalesOrderLine.objects.create(
            order=order, product=product or self.product, quantity=Decimal(qty),
            unit_price=Decimal(price), line_total=Decimal(qty) * Decimal(price), position=1)


# ── E1 ────────────────────────────────────────────────────────────────────────────────
class IntentModelTest(_Base):
    def _quote_line(self):
        quote = Quote.objects.create(customer=self.customer)
        return QuoteLine.objects.create(
            quote=quote, product=self.product, quantity=Decimal('3'),
            unit_price=Decimal('50'), line_total=Decimal('150'), position=1)

    def test_unique_together_quote_line_model(self):
        line, model = self._quote_line(), self._model()
        QuoteLineModelIntent.objects.create(quote_line=line, model=model)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                QuoteLineModelIntent.objects.create(quote_line=line, model=model)

    def test_cascade_en_esborrar_model(self):
        """CASCADE: esborrar el model esborra la intenció (model fora → intenció fora)."""
        line, model = self._quote_line(), self._model()
        intent = QuoteLineModelIntent.objects.create(quote_line=line, model=model)
        model.delete()
        self.assertFalse(QuoteLineModelIntent.objects.filter(pk=intent.pk).exists())

    def test_cascade_en_esborrar_quote_line(self):
        line, model = self._quote_line(), self._model()
        intent = QuoteLineModelIntent.objects.create(quote_line=line, model=model)
        line.delete()
        self.assertFalse(QuoteLineModelIntent.objects.filter(pk=intent.pk).exists())


# ── E3 ────────────────────────────────────────────────────────────────────────────────
class ConvertPropagationTest(_Base):
    def test_tres_camins_en_una_conversio(self):
        """Una conversió amb tres intencions: model lliure→assign · orfe→reattach · ocupat→conflicte."""
        free_model = self._model()
        orphan_model = self._model()
        busy_model = self._model()

        # Camí ORFE: assigna orphan_model a una comanda i desassigna'l → WO orfe.
        o_orphan = SalesOrder.objects.create(customer=self.customer)
        l_orphan = self._line(o_orphan)
        wo_orphan, _ = assign_model_to_order_line(orphan_model, l_orphan)
        unassign_model_from_order_line(wo_orphan)
        wo_orphan.refresh_from_db()
        self.assertIsNone(wo_orphan.order_line_id)

        # Camí CONFLICTE: busy_model té un WO ORDER OPEN viu en una ALTRA comanda.
        o_busy = SalesOrder.objects.create(customer=self.customer)
        l_busy = self._line(o_busy)
        wo_busy, _ = assign_model_to_order_line(busy_model, l_busy)

        # Oferta amb tres línies, una intenció per línia (línies creades en DRAFT, després SENT).
        quote = Quote.objects.create(customer=self.customer)
        for m in (free_model, orphan_model, busy_model):
            ql = QuoteLine.objects.create(
                quote=quote, product=self.product, quantity=Decimal('2'),
                unit_price=Decimal('50'), line_total=Decimal('100'), position=1)
            QuoteLineModelIntent.objects.create(quote_line=ql, model=m)
        quote.status = 'SENT'; quote.save(update_fields=['status'])

        order, meta = convert_quote_to_order(quote)

        # Comptadors.
        self.assertEqual(meta['assigned'], 1, "el model lliure s'assigna")
        self.assertEqual(meta['reattached'], 1, "el model orfe es reattacha")
        self.assertEqual(len(meta['intent_conflicts']), 1, "el model ocupat és conflicte")
        self.assertEqual(meta['intent_conflicts'][0]['model'], busy_model.id)
        self.assertEqual(meta['intent_conflicts'][0]['reason'], 'busy')

        # El model lliure té ara un WO ORDER OPEN lligat a una línia de la comanda nova.
        wo_free = WorkOrder.objects.get(model=free_model, kind='ORDER', status='OPEN')
        self.assertIsNotNone(wo_free.order_line_id)
        self.assertEqual(wo_free.order_line.order_id, order.id)

        # L'orfe s'ha re-adoptat a la comanda nova (traça netejada).
        wo_orphan.refresh_from_db()
        self.assertIsNotNone(wo_orphan.order_line_id)
        self.assertEqual(wo_orphan.order_line.order_id, order.id)
        self.assertIsNone(wo_orphan.orphaned_from_line_id)

        # El model ocupat NO ha viatjat: el seu WO segueix a la comanda original.
        wo_busy.refresh_from_db()
        self.assertEqual(wo_busy.order_line_id, l_busy.id)

        # La conversió s'ha completat: comanda creada + oferta segellada.
        quote.refresh_from_db()
        self.assertEqual(quote.status, 'ACCEPTED')

    def test_conversio_sense_intencions_no_afecta(self):
        quote = Quote.objects.create(customer=self.customer)
        QuoteLine.objects.create(quote=quote, product=self.product, quantity=Decimal('1'),
                                 unit_price=Decimal('50'), line_total=Decimal('50'), position=1)
        quote.status = 'SENT'; quote.save(update_fields=['status'])
        order, meta = convert_quote_to_order(quote)
        self.assertEqual(meta, {'intent_conflicts': [], 'assigned': 0, 'reattached': 0})


# ── E4 ────────────────────────────────────────────────────────────────────────────────
class ReattachServiceTest(_Base):
    def _make_orphan(self):
        """Crea un WO orfe (assign + unassign) sobre el product base. Retorna (wo, model)."""
        order = SalesOrder.objects.create(customer=self.customer)
        line = self._line(order)
        model = self._model()
        wo, _ = assign_model_to_order_line(model, line)
        unassign_model_from_order_line(wo)
        wo.refresh_from_db()
        return wo, model

    def test_recongela_snapshot_i_neteja_orfandat(self):
        wo, _ = self._make_orphan()
        old_snapshot = dict(wo.price_snapshot)   # congelat contra el product base (50 / 21%)

        # Línia NOVA amb un product diferent (preu i IVA diferents).
        product_b = Product.objects.create(
            code='SRV-2', name='Servei 2', nature='INTERNAL_SERVICE',
            base_price=Decimal('99.00'), tax_rate=Decimal('10.00'))
        order_b = SalesOrder.objects.create(customer=self.customer)
        line_b = self._line(order_b, product=product_b, qty='2', price='99')

        wo2 = reattach_orphan_to_line(wo, line_b)
        wo2.refresh_from_db(); line_b.refresh_from_db()

        self.assertEqual(wo2.order_line_id, line_b.id)
        self.assertIsNone(wo2.orphaned_from_line_id, "l'orfandat es neteja (torna a null)")
        self.assertEqual(line_b.qty_allocated, Decimal('1.00'), "imputa +1 a la línia nova")
        # Re-congelació: el snapshot nou reflecteix el product de la línia NOVA i és != al vell.
        self.assertEqual(wo2.price_snapshot['unit_price'], '99')
        self.assertEqual(wo2.price_snapshot['product_code'], 'SRV-2')
        self.assertEqual(wo2.price_snapshot['tax_rate'], '10.00')
        self.assertNotEqual(wo2.price_snapshot, old_snapshot)

    # --- Els 7 guards ---
    def test_guard_kind_no_order(self):
        wo = WorkOrder.objects.create(customer=self.customer, kind='COLLECTOR', period='2026-07')
        order = SalesOrder.objects.create(customer=self.customer)
        with self.assertRaises(ValidationError):
            reattach_orphan_to_line(wo, self._line(order))

    def test_guard_wo_closed(self):
        wo, _ = self._make_orphan()
        wo.status = 'CLOSED'; wo.save(update_fields=['status'])
        order = SalesOrder.objects.create(customer=self.customer)
        with self.assertRaises(ValidationError):
            reattach_orphan_to_line(wo, self._line(order))

    def test_guard_no_orfe(self):
        """Un WO amb order_line assignada NO és orfe: no es pot re-adoptar."""
        order = SalesOrder.objects.create(customer=self.customer)
        line = self._line(order)
        wo, _ = assign_model_to_order_line(self._model(), line)   # order_line viva
        order_b = SalesOrder.objects.create(customer=self.customer)
        with self.assertRaises(ValidationError):
            reattach_orphan_to_line(wo, self._line(order_b))

    def test_guard_comanda_desti_no_oberta(self):
        wo, _ = self._make_orphan()
        order = SalesOrder.objects.create(customer=self.customer, status='CANCELLED')
        with self.assertRaises(ValidationError):
            reattach_orphan_to_line(wo, self._line(order))

    def test_guard_customer_incoherent(self):
        wo, _ = self._make_orphan()   # customer = self.customer
        order = SalesOrder.objects.create(customer=self.other)
        with self.assertRaises(ValidationError):
            reattach_orphan_to_line(wo, self._line(order))

    def test_guard_qty_no_disponible(self):
        wo, _ = self._make_orphan()
        order = SalesOrder.objects.create(customer=self.customer)
        line = self._line(order, qty='1')
        line.qty_allocated = Decimal('1.00'); line.save(update_fields=['qty_allocated'])
        with self.assertRaises(ValidationError):
            reattach_orphan_to_line(wo, line)

    def test_guard_ja_albaranat(self):
        wo, _ = self._make_orphan()
        dn = DeliveryNote.objects.create(customer=self.customer)
        DeliveryNoteLine.objects.create(
            delivery_note=dn, product=None, work_order=wo, line_kind='TASK',
            quantity=Decimal('1'), unit_price=Decimal('10'), line_total=Decimal('10'), position=1)
        order = SalesOrder.objects.create(customer=self.customer)
        with self.assertRaises(ValidationError):
            reattach_orphan_to_line(wo, self._line(order))
