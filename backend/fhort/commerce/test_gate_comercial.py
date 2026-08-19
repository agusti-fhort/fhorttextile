"""La capacitat COMERCIAL: qui veu el diner, i qui segueix treballant sense veure'l.

Dues meitats que s'han de provar juntes, perquè cadascuna és el guard de l'altra:

1. EL TALL. Un tècnic no llegeix el bloc comercial. Fins al 14/08 la lectura era oberta a
   qualsevol autenticat (`_ConfigureWriteMixin`) i n'hi havia prou amb estar dins per
   baixar-se preus, marges i el PDF sencer d'una oferta.

2. LA PODA. El tall NO pot ser un 403 a tot arreu: hi ha pantalles TÈCNIQUES que viuen
   d'aquests endpoints i no pinten cap import — la traçabilitat de la fitxa del model
   (`ProductionTab.jsx:75-76`) i el selector d'assignació (`ActionsMenu.jsx:86`). Allà la
   crida ha de seguir tornant 200 i el que ha de desaparèixer són els CAMPS. Els asserts
   d'aquesta meitat miren els NOMS DE CAMP al JSON: que no hi siguin, no que valguin zero.

I la tercera pota, que és la que fa que la decisió d'Agus sigui viable: el manager no té
COMERCIAL per rol, però la concessió individual de la matriu (`permisos.grant`) l'hi dona.
Si aquest override no funcionés, «es concedeix per usuari» seria una promesa buida.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.commerce.models import (
    Product, Quote, QuoteLine, SalesOrder, SalesOrderLine, WorkOrder,
    DeliveryNote, DeliveryNoteLine,
)
from fhort.commerce.views import (
    QuoteViewSet, ProductViewSet, SalesOrderViewSet, SalesOrderLineViewSet,
    WorkOrderViewSet, DeliveryNoteLineViewSet,
)
from fhort.tasks.models import Customer


class BaseComercial(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'estudi'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        self.factory = APIRequestFactory()
        self.tecnic = self._usuari('tecnic@test.local', 'technician')
        self.manager = self._usuari('manager@test.local', 'manager')
        self.admin = self._usuari('admin@test.local', 'admin')
        self._sembra()

    def _usuari(self, username, rol, grant=None):
        user = get_user_model().objects.create_user(username, password='x')
        prof, _ = UserProfile.objects.get_or_create(
            user=user, defaults={'nom_complet': username, 'rol_nom': rol})
        prof.rol_nom = rol
        prof.permisos = {'grant': list(grant or [])}
        prof.save(update_fields=['rol_nom', 'permisos'])
        # Rellegir: el signal ha deixat el perfil VELL cachejat a `user.profile`, que és d'on
        # llegeix get_capabilities(). Sense això el rol nou no compta.
        return get_user_model().objects.get(pk=user.pk)

    def _sembra(self):
        self.customer = Customer.objects.create(codi='CLI', nom='Client de prova')
        self.product = Product.objects.create(
            code='SRV', name='Servei', nature='INTERNAL_SERVICE', price_mode='FIXED',
            base_price=50, tax_rate=21)
        self.quote = Quote.objects.create(customer=self.customer, status='DRAFT')
        QuoteLine.objects.create(quote=self.quote, product=self.product, description='línia',
                                 quantity=1, unit_price=50, position=1)
        self.order = SalesOrder.objects.create(customer=self.customer, status='OPEN')
        self.line = SalesOrderLine.objects.create(
            order=self.order, product=self.product, description='línia', quantity=2,
            unit_price=120, position=1)
        self.wo = WorkOrder.objects.create(
            customer=self.customer, kind='ORDER', status='OPEN', order_line=self.line,
            price_snapshot={'unit_price': '120', 'tax_rate': '21.00'}, recipe_snapshot={})
        self.dn = DeliveryNote.objects.create(customer=self.customer, status='DRAFT')
        self.dn_line = DeliveryNoteLine.objects.create(
            delivery_note=self.dn, line_kind='TASK', description='feina',
            quantity=1, unit_price=30, position=1, internal_minutes=120)

    def _get(self, viewset, user, accio='list', ruta='/x/', **kwargs):
        req = self.factory.get(ruta, kwargs.pop('params', None))
        force_authenticate(req, user=user)
        req.tenant = self.tenant
        vista = viewset.as_view({'get': accio})
        return vista(req, **kwargs)

    def _files(self, resp):
        dades = resp.data
        return dades['results'] if isinstance(dades, dict) and 'results' in dades else dades


# ── 1. EL TALL: el tècnic no llegeix el bloc comercial ──────────────────────────
class TallComercialTest(BaseComercial):

    def test_tecnic_no_llegeix_ofertes(self):
        self.assertEqual(self._get(QuoteViewSet, self.tecnic).status_code, 403)

    def test_tecnic_no_llegeix_articles(self):
        self.assertEqual(self._get(ProductViewSet, self.tecnic).status_code, 403)

    def test_tecnic_no_es_baixa_el_pdf_de_l_oferta(self):
        """La lectura més sensible del mòdul: l'oferta sencera amb tots els imports impresos."""
        resp = self._get(QuoteViewSet, self.tecnic, accio='pdf', pk=self.quote.pk)
        self.assertEqual(resp.status_code, 403)

    def test_admin_segueix_llegint_les_ofertes_amb_els_imports(self):
        resp = self._get(QuoteViewSet, self.admin)
        self.assertEqual(resp.status_code, 200)
        fila = self._files(resp)[0]
        self.assertIn('total', fila)
        self.assertIn('unit_price', fila['lines'][0])


# ── 2. LA PODA: les pantalles tècniques segueixen vives, sense diner ────────────
class PodaSuperficiesTecniquesTest(BaseComercial):
    """Els asserts miren NOMS DE CAMP. Un camp a 0 o a null seguiria sent una fuita."""

    ECONOMICS_WO = ('price_snapshot',)
    ECONOMICS_DN_LINE = ('unit_price', 'line_total', 'internal_cost')
    ECONOMICS_ORDER = ('subtotal', 'tax_amount', 'total', 'tax_breakdown')

    def test_tecnic_llegeix_els_encarrecs_del_model(self):
        """ProductionTab.jsx:75 — la cadena comanda→encàrrec→albarà de la fitxa del model."""
        resp = self._get(WorkOrderViewSet, self.tecnic, params={'model': ''})
        self.assertEqual(resp.status_code, 200)

    def test_els_encarrecs_del_tecnic_no_porten_price_snapshot(self):
        fila = self._files(self._get(WorkOrderViewSet, self.tecnic))[0]
        for camp in self.ECONOMICS_WO:
            self.assertNotIn(camp, fila, f"{camp} ha viatjat a un tècnic")
        # …i el que la pantalla SÍ que pinta segueix arribant.
        for camp in ('number', 'kind', 'status', 'delivery_note_number'):
            self.assertIn(camp, fila)

    def test_les_linies_d_albara_del_tecnic_no_porten_ni_preu_ni_cost_intern(self):
        """El cas que va obrir la peça: internal_cost = minuts × tarifa/hora."""
        fila = self._files(self._get(DeliveryNoteLineViewSet, self.tecnic))[0]
        for camp in self.ECONOMICS_DN_LINE:
            self.assertNotIn(camp, fila, f"{camp} ha viatjat a un tècnic")
        self.assertIn('dn_number', fila)
        self.assertIn('dn_status', fila)
        # Els minuts NO són diner: són la feina del tècnic i es queden.
        self.assertIn('internal_minutes', fila)

    def test_el_selector_d_assignacio_segueix_servint_sense_imports(self):
        """ActionsMenu.jsx:86 + :392 — el selector vol document_number i quantity/qty_allocated."""
        resp = self._get(SalesOrderViewSet, self.manager)
        self.assertEqual(resp.status_code, 200)
        comanda = self._files(resp)[0]
        for camp in self.ECONOMICS_ORDER:
            self.assertNotIn(camp, comanda, f"{camp} ha viatjat a qui no té COMERCIAL")
        self.assertIn('document_number', comanda)
        linia = comanda['lines'][0]
        for camp in ('unit_price', 'line_total'):
            self.assertNotIn(camp, linia, f"{camp} ha viatjat a qui no té COMERCIAL")
        for camp in ('quantity', 'qty_allocated'):
            self.assertIn(camp, linia, f"{camp} és cartera, no diner: ha d'arribar")

    def test_l_admin_veu_els_imports_de_la_comanda(self):
        comanda = self._files(self._get(SalesOrderViewSet, self.admin))[0]
        for camp in self.ECONOMICS_ORDER:
            self.assertIn(camp, comanda)
        self.assertIn('unit_price', comanda['lines'][0])

    def test_l_informe_d_orfes_no_es_per_a_tecnics(self):
        """`orphaned` es construeix el payload a mà (amb order.total) i no passa per la poda."""
        resp = self._get(WorkOrderViewSet, self.tecnic, accio='orphaned')
        self.assertEqual(resp.status_code, 403)


# ── 3. L'OVERRIDE DE LA MATRIU: sense ell, la decisió d'Agus no se sosté ────────
class ConcessioIndividualTest(BaseComercial):

    def test_manager_sense_concessio_no_veu_el_bloc_comercial(self):
        self.assertEqual(self._get(QuoteViewSet, self.manager).status_code, 403)

    def test_manager_amb_concessio_individual_hi_veu_com_un_admin(self):
        comercial = self._usuari('cap.vendes@test.local', 'manager', grant=['comercial'])
        resp = self._get(QuoteViewSet, comercial)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('total', self._files(resp)[0])

    def test_l_escriptura_comercial_vol_les_dues_capacitats(self):
        """COMERCIAL sol no basta per escriure: el manager amb la concessió té CONFIGURE?
        No — el rol manager no porta CONFIGURE, així que la creació d'articles li ha de
        tallar igualment. És el que fa que «veure» i «tocar» segueixin sent coses diferents."""
        comercial = self._usuari('cap.vendes2@test.local', 'manager', grant=['comercial'])
        req = self.factory.post('/x/', {}, format='json')
        force_authenticate(req, user=comercial)
        req.tenant = self.tenant
        resp = ProductViewSet.as_view({'post': 'create'})(req)
        self.assertEqual(resp.status_code, 403)


# ── 4. L'acció operativa segueix fora de COMERCIAL ─────────────────────────────
class AssignacioOperativaTest(BaseComercial):

    def _model(self, codi, seq):
        """Mateixa forma que `test_batch_assign.py:48-51`: `any` i `sequencial` són NOT NULL
        i sense default, i el run/base els vol el servei d'assignació."""
        from fhort.models_app.models import Model
        return Model.objects.create(
            codi_intern=codi, codi_tenant='TST', any=2026, sequencial=seq,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
            customer=self.customer)

    def test_qui_assigna_no_necessita_veure_el_diner(self):
        """L'assignació model↔comanda és cartera, no comerç (decisió d'Agus). El gate segueix
        sent CONFIGURE: un admin (que el té) passa el permís encara sense tocar COMERCIAL."""
        req = self.factory.post('/x/', {'model_id': 999999}, format='json')
        force_authenticate(req, user=self.admin)
        req.tenant = self.tenant
        resp = SalesOrderLineViewSet.as_view({'post': 'assign_model'})(req, pk=self.line.pk)
        # 404 = model inexistent: el PERMÍS ha passat, que és el que es prova aquí.
        self.assertEqual(resp.status_code, 404)

    def test_el_tecnic_no_assigna(self):
        req = self.factory.post('/x/', {'model_id': 1}, format='json')
        force_authenticate(req, user=self.tecnic)
        req.tenant = self.tenant
        resp = SalesOrderLineViewSet.as_view({'post': 'assign_model'})(req, pk=self.line.pk)
        self.assertEqual(resp.status_code, 403)

    def test_qui_assigna_sense_comercial_assigna_de_debo_i_sense_veure_imports(self):
        """El cas real de la peça: un cap de producció amb CONFIGURE però SENSE COMERCIAL.
        Assigna (vincle fet, 201) i el que li torna no porta ni un import."""
        assignador = self._usuari('cap.prod@test.local', 'manager', grant=['configure'])
        model = self._model('M-001', 1)
        req = self.factory.post('/x/', {'model_id': model.pk}, format='json')
        force_authenticate(req, user=assignador)
        req.tenant = self.tenant
        resp = SalesOrderLineViewSet.as_view({'post': 'assign_model'})(req, pk=self.line.pk)
        self.assertEqual(resp.status_code, 201)
        # El vincle existeix de debò: un WorkOrder nou penjat de la línia amb aquest model.
        self.assertTrue(WorkOrder.objects.filter(order_line=self.line, model=model).exists())
        self.assertNotIn('price_snapshot', resp.data['work_order'],
                         "price_snapshot ha viatjat a qui no té COMERCIAL")

    def test_per_aquest_cami_no_s_edita_res_mes_de_la_comanda(self):
        """L'endpoint és acotat: només llegeix `model_id`. Qualsevol altre camp que s'hi
        colés (preu, estat, quantitat) s'IGNORA en silenci — no hi ha cap camí d'escriptura
        cap al document. Es prova amb els noms que temptarien: si algun dia algú els
        connectés, aquest test cau."""
        assignador = self._usuari('cap.prod2@test.local', 'manager', grant=['configure'])
        model = self._model('M-002', 2)
        req = self.factory.post('/x/', {
            'model_id': model.pk,
            'unit_price': '1.00', 'quantity': '999', 'status': 'CANCELLED', 'total': '0',
        }, format='json')
        force_authenticate(req, user=assignador)
        req.tenant = self.tenant
        self.assertEqual(
            SalesOrderLineViewSet.as_view({'post': 'assign_model'})(req, pk=self.line.pk).status_code,
            201)
        self.line.refresh_from_db(); self.order.refresh_from_db()
        self.assertEqual(str(self.line.unit_price), '120.00')
        self.assertEqual(str(self.line.quantity), '2.00')
        self.assertEqual(self.order.status, 'OPEN')
