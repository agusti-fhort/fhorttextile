"""M4 · FIT-5 + FIT-12 — EL NUMERAL DE VOLTES I EL DESBORDAMENT.

FIT-5 (Agus + Salva, 24/08): el numeral de rondes previstes viu **a la comanda**, no al producte.
FIT-12 (Agus, 24/08): quan les voltes reals el superen, la volta R(n) amb les seves tasques passa
a encàrrecs per ser albaranada i facturada A PART — i **la cara del tècnic no canvia gens**.

Aquest fitxer guarda les quatre coses que el gate d'M4 demana del costat de `tasks`:
  1. el numeral EFECTIU d'un model (i els tres «sense límit» que no són el mateix),
  2. la marca `fora_de_comanda` que s'escriu EN OBRIR,
  3. un model SENSE COMANDA no té límit i no és cap error,
  4. i que el veredicte és una FOTO: editar el numeral després no reescriu la història.

Convenció del repo: `python manage.py test fhort.tasks.test_m4_desbordament` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, GarmentTypeItem, ModelTask, Ronda, TaskType
from fhort.tasks.services_r import (linia_de_comanda, numeral_efectiu, obrir_ronda,
                                    ronda_del_gest, tancar_ronda)


class BaseM4(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant M4'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TM4'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='tecM4')
        UserProfile.objects.get_or_create(user=self.user)
        self.prof = self.user.profile
        self.customer = Customer.objects.create(codi='CM4', nom='Client M4')
        gt = GarmentType.objects.create(codi_client='GM4', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_m4', name='Item M4')
        self.tt_pom, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(
            codi_intern='TM4-SS26-0001', codi_tenant='TM4', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item, nom_prenda='Peça')

    # ── Utillatge comercial ────────────────────────────────────────────────────────────────
    def _linia(self, *, rounds_included=None, order_status='OPEN'):
        """Una comanda amb una línia, i el numeral que se li demani."""
        from fhort.commerce.models import Product, SalesOrder, SalesOrderLine
        product, _ = Product.objects.get_or_create(
            code='serv-m4', defaults={'name': 'Servei M4', 'nature': 'INTERNAL_SERVICE'})
        order = SalesOrder.objects.create(customer=self.customer, status=order_status)
        return SalesOrderLine.objects.create(order=order, product=product, quantity=5,
                                             unit_price=100, rounds_included=rounds_included)

    def _assigna(self, linia, *, wo_status='OPEN', orfe=False):
        """El PIVOT model↔comanda: un WorkOrder ORDER. `orfe` = desassignat (order_line NULL)."""
        from fhort.commerce.models import WorkOrder
        return WorkOrder.objects.create(
            customer=self.customer, model=self.model, kind='ORDER', status=wo_status,
            order_line=None if orfe else linia,
            orphaned_from_line=linia if orfe else None)

    def _volta(self, codes=('pom',)):
        return obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, list(codes), profile=self.prof)


class NumeralEfectiuTest(BaseM4):
    """§1 — QUANTES VOLTES ADMET EL PACTE. Tres «sense límit» que no volen dir el mateix."""

    def test_model_SENSE_comanda_no_te_limit_i_no_es_un_error(self):
        """FIT-12, cas explícit del brief: sense numeral no hi ha límit. `(None, None)`."""
        self.assertIsNone(linia_de_comanda(self.model))
        self.assertEqual(numeral_efectiu(self.model), (None, None))

    def test_comanda_amb_numeral_el_retorna(self):
        linia = self._linia(rounds_included=2)
        self._assigna(linia)
        resolt_linia, numeral = numeral_efectiu(self.model)
        self.assertEqual(resolt_linia.pk, linia.pk)
        self.assertEqual(numeral, 2)

    def test_comanda_SENSE_numeral_dona_linia_i_None(self):
        """`(linia, None)`: hi ha pacte, però no en fixa cap. Distingible de «no hi ha comanda»."""
        linia = self._linia(rounds_included=None)
        self._assigna(linia)
        resolt_linia, numeral = numeral_efectiu(self.model)
        self.assertEqual(resolt_linia.pk, linia.pk)
        self.assertIsNone(numeral)

    def test_numeral_ZERO_no_es_sense_limit(self):
        """`(linia, 0)`: el pacte no inclou CAP volta. És el cas que un default de 0 amagaria."""
        linia = self._linia(rounds_included=0)
        self._assigna(linia)
        self.assertEqual(numeral_efectiu(self.model), (linia, 0))

    def test_un_WO_ORFE_no_governa(self):
        """Desassignar és treure el model de la venda: aquella comanda ja no li fixa cap límit."""
        linia = self._linia(rounds_included=1)
        self._assigna(linia, orfe=True)
        self.assertIsNone(linia_de_comanda(self.model))

    def test_una_comanda_CANCELLED_no_governa(self):
        linia = self._linia(rounds_included=1, order_status='CANCELLED')
        self._assigna(linia)
        self.assertIsNone(linia_de_comanda(self.model))

    def test_un_COLLECTOR_no_governa(self):
        """El col·lector és el contenidor de la feina SENSE comanda: per definició no en té."""
        from fhort.commerce.models import WorkOrder
        WorkOrder.objects.create(customer=self.customer, kind='COLLECTOR', period='2026-08')
        self.assertIsNone(linia_de_comanda(self.model))

    def test_mana_el_WO_OBERT_quan_n_hi_ha_un_de_tancat(self):
        vella = self._linia(rounds_included=1)
        nova = self._linia(rounds_included=9)
        self._assigna(vella, wo_status='CLOSED')
        self._assigna(nova, wo_status='OPEN')
        self.assertEqual(numeral_efectiu(self.model), (nova, 9))


class MarcaEnObrirTest(BaseM4):
    """§2 — LA MARCA S'ESCRIU EN OBRIR, i diu el perquè sencer."""

    def test_dins_del_numeral_la_volta_NO_es_fora_de_comanda(self):
        linia = self._linia(rounds_included=2)
        self._assigna(linia)
        ronda_del_gest(self.model)                      # R1
        tancar_ronda(Ronda.objects.get(model=self.model, seq=1), profile=self.prof)
        r2 = self._volta()
        self.assertEqual(r2.seq, 2)
        self.assertFalse(r2.fora_de_comanda)
        self.assertEqual(r2.numeral_vigent, 2)
        self.assertEqual(r2.linia_comanda_id, linia.pk)

    def test_passar_el_numeral_marca_la_volta_FORA_DE_COMANDA(self):
        """FIT-12: la R3 d'una comanda de 2 voltes es factura a part. I SEGUEIX SENT la R3."""
        linia = self._linia(rounds_included=2)
        self._assigna(linia)
        ronda_del_gest(self.model)
        for seq in (1, 2):
            if seq == 2:
                self._volta()
            tancar_ronda(Ronda.objects.get(model=self.model, seq=seq), profile=self.prof)
        r3 = self._volta()
        self.assertEqual(r3.seq, 3, 'la numeració del model NO es toca')
        self.assertTrue(r3.fora_de_comanda)
        self.assertEqual(r3.numeral_vigent, 2)
        self.assertEqual(r3.linia_comanda_id, linia.pk)

    def test_numeral_zero_desborda_ja_la_R1(self):
        """La R1 neix del primer gest (`ronda_del_gest`) i també es pesa contra el numeral."""
        linia = self._linia(rounds_included=0)
        self._assigna(linia)
        r1 = ronda_del_gest(self.model)
        self.assertEqual(r1.seq, 1)
        self.assertTrue(r1.fora_de_comanda)
        self.assertEqual(r1.numeral_vigent, 0)

    def test_model_sense_comanda_cap_volta_desborda_mai(self):
        ronda_del_gest(self.model)
        tancar_ronda(Ronda.objects.get(model=self.model, seq=1), profile=self.prof)
        r2 = self._volta()
        tancar_ronda(r2, profile=self.prof)
        r3 = self._volta()
        for r in (Ronda.objects.get(model=self.model, seq=1), r2, r3):
            self.assertFalse(r.fora_de_comanda)
            self.assertIsNone(r.numeral_vigent)
            self.assertIsNone(r.linia_comanda_id)

    def test_el_veredicte_es_una_FOTO_i_no_es_recalcula(self):
        """Pujar el numeral després NO torna la volta a dins: seria reescriure la història."""
        linia = self._linia(rounds_included=1)
        self._assigna(linia)
        ronda_del_gest(self.model)
        tancar_ronda(Ronda.objects.get(model=self.model, seq=1), profile=self.prof)
        r2 = self._volta()
        self.assertTrue(r2.fora_de_comanda)

        linia.rounds_included = 5
        linia.save(update_fields=['rounds_included'])
        r2.refresh_from_db()
        self.assertTrue(r2.fora_de_comanda, 'la foto de l\'obertura no es toca')
        self.assertEqual(r2.numeral_vigent, 1, 'el perquè segueix dient n>1')

    def test_la_R1_que_ja_existia_no_es_re_resol_a_cada_gest(self):
        """`ronda_del_gest` retorna la R1 existent sense tornar-hi a escriure el veredicte."""
        linia = self._linia(rounds_included=0)
        self._assigna(linia)
        r1 = ronda_del_gest(self.model)
        self.assertTrue(r1.fora_de_comanda)
        linia.rounds_included = 9
        linia.save(update_fields=['rounds_included'])
        un_altre_gest = ronda_del_gest(self.model)
        self.assertEqual(un_altre_gest.pk, r1.pk)
        un_altre_gest.refresh_from_db()
        self.assertTrue(un_altre_gest.fora_de_comanda)


class LaCaraDelTecnicNoCanviaTest(BaseM4):
    """§3 — FIT-12: «el tècnic NO VEU RES del desbordament». El payload de la volta ho prova."""

    def test_el_serializer_de_ronda_no_serveix_cap_camp_del_desbordament(self):
        from fhort.tasks.serializers_b import RondaSerializer
        linia = self._linia(rounds_included=0)
        self._assigna(linia)
        r1 = ronda_del_gest(self.model)
        self.assertTrue(r1.fora_de_comanda, 'la marca hi és a BD…')
        dades = RondaSerializer(r1).data
        for camp in ('fora_de_comanda', 'linia_comanda', 'numeral_vigent'):
            self.assertNotIn(camp, dades, '…i NO viatja a la cara del tècnic')

    def test_obrir_una_volta_desbordada_no_canvia_res_de_les_seves_tasques(self):
        linia = self._linia(rounds_included=1)
        self._assigna(linia)
        ronda_del_gest(self.model)
        tancar_ronda(Ronda.objects.get(model=self.model, seq=1), profile=self.prof)
        r2 = self._volta()
        self.assertTrue(r2.fora_de_comanda)
        tasca = ModelTask.objects.get(ronda=r2, task_type=self.tt_pom)
        self.assertEqual(tasca.status, 'Pending')
        self.assertEqual(tasca.origen, 'ad_hoc')
        self.assertEqual(tasca.motiu, Ronda.MOTIU_NOVA_MOSTRA)
