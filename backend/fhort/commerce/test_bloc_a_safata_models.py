"""BLOC A · LA SAFATA D'ALBARANABLES ÉS DE MODELS I RONDES, NO DE TASQUES.

Substitueix el contracte que provava `test_m4_safata_rondes` (safata per `ModelTask`). L'A1 diu
que la unitat d'albarà és el MODEL i l'A7 que el que el document diu són les VOLTES; una safata
de tasques no ho pot compondre, perquè el preu d'un model no és la suma dels preus de les seves
tasques sinó el que diu la línia de comanda.

El que aquí es fixa és el que no es pot trencar sense que algú se n'adoni:
  · una volta EN CURS surt però no és marcable (`entregada: false`);
  · una volta FORA DE PACTE és un bloc PROPI, no una fila del bloc del pacte (A7);
  · l'HÍBRID de l'A4: pujar el numeral torna a dins una volta desbordada **sense tocar la BD**,
    i una volta ja EMESA conserva el seu veredicte congelat;
  · un model sense cap volta entregada no embruta la safata.

Convenció del repo: `python manage.py test fhort.commerce.test_bloc_a_safata_models` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from fhort.commerce.services import get_billable_items
from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, Entrega, GarmentTypeItem, ModelTask, Ronda, TaskType
from fhort.tasks.services_r import resol_desbordament


class SafataModelsTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant bloc A'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TBA'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.commerce.models import Product, SalesOrder, SalesOrderLine, WorkOrder
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='comBlocA')
        UserProfile.objects.get_or_create(user=self.user)
        self.prof = self.user.profile
        self.customer = Customer.objects.create(codi='CBA', nom='Client bloc A')
        gt = GarmentType.objects.create(codi_client='GBA', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_ba', name='Item BA')
        self.tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(
            codi_intern='TBA-SS26-0001', codi_tenant='TBA', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item,
            nom_prenda='Top BEYONCÉ', collection='COL·LECCIÓ BANC')

        product = Product.objects.create(code='serv-ba', name='Servei BA',
                                         nature='INTERNAL_SERVICE')
        self.order = SalesOrder.objects.create(customer=self.customer, status='OPEN')
        self.linia = SalesOrderLine.objects.create(order=self.order, product=product, quantity=5,
                                                   unit_price=120, rounds_included=2,
                                                   description='Disseny patró')
        self.wo = WorkOrder.objects.create(customer=self.customer, model=self.model, kind='ORDER',
                                           status='OPEN', order_line=self.linia,
                                           price_snapshot={'unit_price': '120.00'})
        ara = timezone.now()
        # R1 i R2 dins del pacte i ENTREGADES; R3 fora i entregada; R4 fora i EN CURS.
        self.rondes = {}
        for seq in (1, 2, 3, 4):
            r = Ronda.objects.create(model=self.model, seq=seq, motiu='nova_mostra')
            resol_desbordament(r)
            ModelTask.objects.create(model=self.model, task_type=self.tt, ronda=r,
                                     work_order=self.wo, status='Done',
                                     origen='prevista' if seq == 1 else 'ad_hoc')
            if seq != 4:
                Entrega.objects.create(ronda=r, data=ara - datetime.timedelta(days=10 - seq),
                                       destinatari='Client', qui_informa=self.prof)
            self.rondes[seq] = r

    def _grup(self):
        grups = [g for g in get_billable_items(self.customer)
                 if g['model']['id'] == self.model.id]
        self.assertEqual(len(grups), 1, 'un sol grup per model')
        return grups[0]

    def _bloc(self, clau_prefix):
        return [b for b in self._grup()['blocs'] if b['clau'].startswith(clau_prefix)]

    # ── Identitat i pacte ──────────────────────────────────────────────────────────────────
    def test_el_grup_porta_la_identitat_del_model(self):
        m = self._grup()['model']
        self.assertEqual(m['nom_prenda'], 'Top BEYONCÉ')
        self.assertEqual(m['collection'], 'COL·LECCIÓ BANC')
        self.assertEqual(m['codi_intern'], 'TBA-SS26-0001')

    def test_el_pacte_diu_oferta_concepte_preu_i_numeral(self):
        p = self._grup()['pacte']
        self.assertEqual(p['linia_id'], self.linia.id)
        self.assertEqual(p['concepte'], 'Disseny patró')
        self.assertEqual(p['preu_unitari'], '120.00')
        self.assertEqual(p['rounds_included'], 2)
        self.assertEqual(p['consumit'], 0, 'res emès encara')

    # ── A7 · la volta fora de pacte és un bloc PROPI ───────────────────────────────────────
    def test_les_voltes_del_pacte_van_juntes_en_un_sol_bloc(self):
        pacte = self._bloc('pacte')
        self.assertEqual(len(pacte), 1)
        self.assertEqual([r['seq'] for r in pacte[0]['rondes']], [1, 2])
        self.assertEqual(pacte[0]['preu_proposat'], '120.00',
                         'el preu el proposa la línia de comanda')
        self.assertFalse(pacte[0]['encarrec_directe'])

    def test_cada_volta_fora_de_pacte_es_un_bloc_propi_i_a_preu_lliure(self):
        directes = self._bloc('directe')
        self.assertEqual(len(directes), 2, 'la R3 i la R4, cadascuna la seva targeta')
        for b in directes:
            self.assertEqual(len(b['rondes']), 1, 'una targeta = UNA volta')
            self.assertTrue(b['encarrec_directe'])
            self.assertEqual(b['preu_proposat'], '0.00', 'sense pacte, el preu el posa el comercial')
            self.assertIsNone(b['linia_comanda'])

    def test_el_bloc_del_pacte_va_primer(self):
        # A7: la volta directa ve «immediatament després del mateix model».
        self.assertEqual(self._grup()['blocs'][0]['clau'], 'pacte')

    # ── La volta en curs surt, però no es pot marcar ───────────────────────────────────────
    def test_la_volta_en_curs_surt_pero_no_es_marcable(self):
        totes = {r['seq']: r for b in self._grup()['blocs'] for r in b['rondes']}
        self.assertIn(4, totes, 'la volta en curs ha de sortir: existeix i la feina no s\'ha acabat')
        self.assertFalse(totes[4]['entregada'])
        self.assertIsNone(totes[4]['data_lliurament'])
        self.assertTrue(totes[1]['entregada'])

    def test_un_model_sense_cap_volta_entregada_no_embruta_la_safata(self):
        Entrega.objects.filter(ronda__model=self.model).delete()
        self.assertEqual([g for g in get_billable_items(self.customer)
                          if g['model']['id'] == self.model.id], [])

    # ── A4 · L'HÍBRID ──────────────────────────────────────────────────────────────────────
    def test_pujar_el_numeral_torna_la_volta_a_dins_sense_tocar_la_bd(self):
        self.assertEqual([r['seq'] for r in self._bloc('pacte')[0]['rondes']], [1, 2])
        self.linia.rounds_included = 3
        self.linia.save(update_fields=['rounds_included'])
        self.assertEqual([r['seq'] for r in self._bloc('pacte')[0]['rondes']], [1, 2, 3])
        # 🔑 la safata és LECTURA: el veredicte congelat de la BD no s'ha mogut.
        self.rondes[3].refresh_from_db()
        self.assertTrue(self.rondes[3].fora_de_comanda)

    def test_els_dos_veredictes_viatgen_i_es_poden_distingir(self):
        self.linia.rounds_included = 3
        self.linia.save(update_fields=['rounds_included'])
        r3 = next(r for r in self._bloc('pacte')[0]['rondes'] if r['seq'] == 3)
        self.assertFalse(r3['fora_de_comanda'], 'efectiu, amb el numeral d\'ara')
        self.assertTrue(r3['fora_de_comanda_congelat'], 'la foto de quan es va obrir')

    def test_una_volta_ja_albaranada_surt_de_la_safata(self):
        # 🚨 EL NOM D'ABANS MENTIA. Es deia «conserva el veredicte congelat» i el que assertava
        # —correctament— és que la volta ja NO hi és. No podia ser cap altra cosa: la safata
        # exclou tot el que té línia d'albarà, o sigui que una volta emesa no hi arriba mai i no
        # hi ha cap veredicte seu per conservar. Qui congela és `issue_delivery_note`, i el test
        # que ho prova és el curl de l'acta (BD True → False en emetre).
        # Un test amb un nom que promet més del que mira és pitjor que no tenir-lo: fa creure
        # que hi ha cobertura on no n'hi ha.
        from fhort.commerce.models import DeliveryNote, DeliveryNoteLine
        dn = DeliveryNote.objects.create(customer=self.customer)
        linia_dn = DeliveryNoteLine.objects.create(delivery_note=dn, model=self.model,
                                                   quantity=1, unit_price=120,
                                                   encarrec_directe=True)
        linia_dn.rondes.set([self.rondes[3]])
        DeliveryNote.objects.filter(pk=dn.pk).update(status='ISSUED')
        # Baixar el numeral no pot moure una volta que ja ha sortit en un document.
        self.linia.rounds_included = 99
        self.linia.save(update_fields=['rounds_included'])
        totes = {r['seq']: r for b in self._grup()['blocs'] for r in b['rondes']}
        self.assertNotIn(3, totes, 'una volta ja albaranada surt de la safata')

    # ── Anti-doble-comptatge ───────────────────────────────────────────────────────────────
    def test_una_volta_amb_linia_en_esborrany_surt_de_la_safata(self):
        from fhort.commerce.models import DeliveryNote, DeliveryNoteLine
        dn = DeliveryNote.objects.create(customer=self.customer)
        linia_dn = DeliveryNoteLine.objects.create(delivery_note=dn, model=self.model,
                                                   quantity=1, unit_price=120)
        linia_dn.rondes.set([self.rondes[1], self.rondes[2]])
        totes = {r['seq'] for b in self._grup()['blocs'] for r in b['rondes']}
        self.assertEqual(totes, {3, 4}, 'les que ja són a l\'esborrany no es poden tornar a afegir')
