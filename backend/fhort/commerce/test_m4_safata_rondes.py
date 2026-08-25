"""M4 · FIT-12 — LES TASQUES D'UNA VOLTA DESBORDADA, AL CAMÍ D'ENCÀRRECS.

«Quan les rondes reals superen el numeral, LA RONDA R(n) AMB LES SEVES TASQUES passa a encàrrecs
(comercial) per ser albaranada i facturada A PART» (Agus, 24/08).

El camí ja existia sencer i no s'ha reescrit: `get_billable_items` parteix de `ModelTask`, i
`add_lines_to_draft` omple `DeliveryNoteLine.model_task`. El que M4 hi afegeix és que la safata
**sàpiga de quina volta parla**: la volta, les seves dates i el perquè viatgen amb cada ítem.

Convenció del repo: `python manage.py test fhort.commerce.test_m4_safata_rondes` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.commerce.services import add_lines_to_draft, create_or_get_draft, get_billable_items
from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, GarmentTypeItem, ModelTask, Ronda, TaskType
from fhort.tasks.services_r import obrir_ronda, ronda_del_gest, tancar_ronda


class SafataRondesTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant M4 safata'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TS4'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.commerce.models import Product, SalesOrder, SalesOrderLine, WorkOrder
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='comM4')
        UserProfile.objects.get_or_create(user=self.user)
        self.prof = self.user.profile
        self.customer = Customer.objects.create(codi='CS4', nom='Client safata M4')
        gt = GarmentType.objects.create(codi_client='GS4', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_s4', name='Item S4')
        self.tt_pom, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(
            codi_intern='TS4-SS26-0001', codi_tenant='TS4', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item, nom_prenda='Peça')

        # LA COMANDA: 2 voltes incloses. La R3 desbordarà.
        product = Product.objects.create(code='serv-s4', name='Servei S4',
                                         nature='INTERNAL_SERVICE')
        self.order = SalesOrder.objects.create(customer=self.customer, status='OPEN')
        self.linia = SalesOrderLine.objects.create(order=self.order, product=product, quantity=5,
                                                   unit_price=100, rounds_included=2)
        self.wo = WorkOrder.objects.create(customer=self.customer, model=self.model, kind='ORDER',
                                           status='OPEN', order_line=self.linia,
                                           price_snapshot={'unit_price': '100.00'})

        # Tres voltes: R1 i R2 dins del pacte, R3 fora.
        ronda_del_gest(self.model)
        tancar_ronda(Ronda.objects.get(model=self.model, seq=1), profile=self.prof)
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'], profile=self.prof)
        tancar_ronda(r2, profile=self.prof)
        self.r3 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'], profile=self.prof)
        self.assertTrue(self.r3.fora_de_comanda, 'precondició del banc: la R3 desborda')

        # La feina de la R3, acabada i encara sense albarà: això és el que ha d'arribar a la safata.
        self.tasca_r3 = ModelTask.objects.get(ronda=self.r3, task_type=self.tt_pom)
        self.tasca_r3.status = 'Done'
        self.tasca_r3.work_order = self.wo
        self.tasca_r3.save(update_fields=['status', 'work_order', 'updated_at'])

    # ── Lectura de la safata ───────────────────────────────────────────────────────────────
    def _bloc(self):
        grups = get_billable_items(self.customer)
        blocs = [g for g in grups if g['model']['id'] == self.model.id]
        self.assertEqual(len(blocs), 1, 'un sol bloc per model')
        return blocs[0]

    def test_la_tasca_de_la_volta_desbordada_arriba_a_la_safata(self):
        items = self._bloc()['items']
        ids = [it.get('model_task_id') for it in items]
        self.assertIn(self.tasca_r3.id, ids)

    def test_l_item_porta_la_seva_volta_amb_les_dates_i_el_perque(self):
        it = next(i for i in self._bloc()['items'] if i.get('model_task_id') == self.tasca_r3.id)
        r = it['ronda']
        self.assertIsNotNone(r, 'la volta viatja amb l\'ítem')
        self.assertEqual(r['seq'], 3)
        self.assertTrue(r['fora_de_comanda'])
        self.assertEqual(r['numeral_vigent'], 2, 'el perquè pot dir «n>2»')
        self.assertEqual(r['comanda'], self.order.document_number, 'i de quina comanda parla')
        self.assertIsNotNone(r['oberta_el'], 'la data d\'inici, que FIT-12 demana')
        self.assertIsNone(r['tancada_el'], 'encara oberta: no en té de tancament')

    def test_el_bloc_porta_l_index_de_voltes_ordenat(self):
        rondes = self._bloc()['rondes']
        self.assertEqual([r['seq'] for r in rondes], sorted(r['seq'] for r in rondes))
        self.assertIn(3, [r['seq'] for r in rondes])

    def test_la_feina_SENSE_volta_no_s_inventa_cap_ronda(self):
        """La feina llegada (`ronda` NULL) segueix al calaix «sense volta»: `ronda` = None."""
        llegada = ModelTask.objects.create(model=self.model, task_type=self.tt_pom, order=99,
                                           status='Done', origen='prevista', off_recipe=True)
        it = next(i for i in self._bloc()['items'] if i.get('model_task_id') == llegada.id)
        self.assertIsNone(it['ronda'])

    def test_cap_preu_de_volta_es_calcula(self):
        """El brief ho prohibeix: la tasca desbordada proposa el preu del seu WO, com sempre."""
        it = next(i for i in self._bloc()['items'] if i.get('model_task_id') == self.tasca_r3.id)
        self.assertEqual(it['proposed_price'], '100.00')

    def test_un_model_sense_comanda_no_desborda_i_la_safata_ho_diu(self):
        from fhort.models_app.models import Model
        lliure = Model.objects.create(
            codi_intern='TS4-SS26-0002', codi_tenant='TS4', any=2026, temporada='SS',
            sequencial=2, customer=self.customer, garment_type_item=self.item, nom_prenda='Lliure')
        ronda_del_gest(lliure)
        tancar_ronda(Ronda.objects.get(model=lliure, seq=1), profile=self.prof)
        r2 = obrir_ronda(lliure, Ronda.MOTIU_NOVA_MOSTRA, ['pom'], profile=self.prof)
        t = ModelTask.objects.get(ronda=r2, task_type=self.tt_pom)
        t.status = 'Done'
        t.save(update_fields=['status', 'updated_at'])

        bloc = next(g for g in get_billable_items(self.customer) if g['model']['id'] == lliure.id)
        it = next(i for i in bloc['items'] if i.get('model_task_id') == t.id)
        self.assertFalse(it['ronda']['fora_de_comanda'])
        self.assertIsNone(it['ronda']['numeral_vigent'])
        self.assertIsNone(it['ronda']['comanda'])

    # ── Escriptura: el camí d'encàrrecs sencer ─────────────────────────────────────────────
    def test_la_tasca_de_la_volta_entra_a_l_albara_amb_la_seva_traça(self):
        """`add_lines_to_draft` → `DeliveryNoteLine.model_task`, que és per on es reconstrueix
        la volta d'una línia sense cap FK nova (services.py:835)."""
        draft, _ = create_or_get_draft(self.customer, user=self.prof)
        creades = add_lines_to_draft(draft, [{'kind': 'TASK',
                                              'model_task_id': self.tasca_r3.id}], user=self.prof)
        self.assertEqual(len(creades), 1)
        linia = creades[0]
        self.assertEqual(linia.model_task_id, self.tasca_r3.id)
        self.assertEqual(linia.model_id, self.model.id)
        self.assertEqual(linia.line_kind, 'TASK')
        self.assertEqual(linia.model_task.ronda_id, self.r3.id,
                         'de la línia se n\'arriba a la volta')

    def test_un_cop_albaranada_la_tasca_surt_de_la_safata(self):
        draft, _ = create_or_get_draft(self.customer, user=self.prof)
        add_lines_to_draft(draft, [{'kind': 'TASK', 'model_task_id': self.tasca_r3.id}],
                           user=self.prof)
        ids = [it.get('model_task_id') for it in self._bloc()['items']]
        self.assertNotIn(self.tasca_r3.id, ids)

    def test_cap_albara_ni_factura_automatics(self):
        """La safata és lectura pura: llegir-la no crea cap document."""
        from fhort.commerce.models import DeliveryNote
        abans = DeliveryNote.objects.count()
        get_billable_items(self.customer)
        self.assertEqual(DeliveryNote.objects.count(), abans)
