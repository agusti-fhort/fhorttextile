"""ESMENA · BLOC A — contractes escrits contra el que els curls C1-C3 de
`docs/ordres/ORDRE_BLOC_A_ALBARA.md` (§ESMENA) han MESURAT: extres a la safata, la contradicció
de pacte a l'emissió i el gate COMERCIAL a la cara. Fins ara cap dels tres tenia test escrit —la
suite de `fhort.commerce` passava igual amb ells trencats.

🚨 AQUEST FITXER NO S'HA EXECUTAT. Escrit contra la lectura del codi real (`services.py`,
`views.py`, `serializers.py`, `pdf_service.py`) i els curls de l'acta; verificat només amb
`python -m py_compile`, no amb `manage.py test`. Convenció del repo un cop es corrin:
`python manage.py test fhort.commerce.test_esmena_bloc_a` (no pytest).

Sis grups, un per contracte de l'ordre de tancament:
  · SafataExtresTest       — extres/despeses/deduccions per model; EXTRA_ABSORB absent;
                              un cop albaranat, l'ítem desapareix (bloc de voltes I extra).
  · AddLinesTest            — 1 línia per model (+1 directa); import = preu de la línia de
                              comanda; IVA del producte; idempotent entre crides I dins d'una.
  · HibridRecalculTest      — abans d'emetre, `contradiccions_de_pacte` ho diu i la BD no es
                              mou; `issue_delivery_note` és qui congela.
  · EmetreContradiccioTest  — 409 als dos sentits (directa que cauria dins / pacte que cauria
                              fora); 200 després de corregir; mai auto-converteix; els dos
                              `None` de `numeral_efectiu` es distingeixen.
  · GatesComercialTest      — sense COMERCIAL: PATCH unit_price 403, POST cost-hora 403, GET
                              podat; un model d'un altre client → 400 (mai 200).
  · PdfBlocsTest            — bloc per model, rondes en una línia, la directa hi diu les
                              tasques fetes, els extres van SOTA les rondes, notes UNA vegada.
"""
import datetime
import subprocess
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.commerce.models import (
    DeliveryNote, DeliveryNoteLine, Expense, Product, SalesOrder, SalesOrderLine,
    WorkOrder, WorkOrderAdjustment,
)
from fhort.commerce.services import (
    ContradiccioDePacte, add_lines_to_draft, contradiccions_de_pacte, create_or_get_draft,
    get_billable_items, issue_delivery_note,
)
from fhort.commerce.views import DeliveryNoteLineViewSet, SalesOrderLineViewSet
from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, Entrega, GarmentTypeItem, ModelTask, Ronda, Supplier, TaskType
from fhort.tasks.services_r import numeral_efectiu, resol_desbordament
from fhort.tasks.views_b import ModelTaskViewSet


def _pdf_text(pdf_bytes):
    """Extreu el text del PDF real amb `pdftotext -layout` (poppler-utils), mateixa eina que
    l'acta va usar per a la «extracció de text del PDF real» del commit 8. No hi ha cap
    llibreria Python d'extracció instal·lada al venv (només `reportlab`, que EMET; i
    `pikepdf`, que no en dona text pla), i el binari sí que hi és."""
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(pdf_bytes)
        f.flush()
        out = subprocess.run(['pdftotext', '-layout', f.name, '-'],
                             capture_output=True, check=True)
    return out.stdout.decode('utf-8')


class _BaseEsmena(TenantTestCase):
    """Un client, un model amb pacte (numeral 2, preu 120,00, IVA 21 %) i tres voltes:
    R1/R2 dins, R3 fora. Cadascuna té una tasca Done (necessària per als «tasques fetes» del
    PDF a la volta directa) i està ENTREGADA (necessària per ser albaranable, A1)."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant esmena A'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TEA'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.models_app.models import Model

        self.factory = APIRequestFactory()
        self.author = get_user_model().objects.create(username='autorEA')
        UserProfile.objects.get_or_create(user=self.author)

        self.customer = Customer.objects.create(codi='CEA', nom='Client esmena A')
        self.altre_client = Customer.objects.create(codi='ALT', nom='Un altre client')
        gt = GarmentType.objects.create(codi_client='GEA', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_ea', name='Item EA')
        self.tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})

        self.model = Model.objects.create(
            codi_intern='TEA-SS26-0001', codi_tenant='TEA', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item,
            nom_prenda='Top BEYONCÉ', collection='COL·LECCIÓ BANC')

        self.product = Product.objects.create(
            code='serv-ea', name='Servei EA', nature='INTERNAL_SERVICE', tax_rate=Decimal('21.00'))
        self.order = SalesOrder.objects.create(customer=self.customer, status='OPEN')
        self.linia = SalesOrderLine.objects.create(
            order=self.order, product=self.product, quantity=5, unit_price=Decimal('120.00'),
            rounds_included=2, description='Disseny patró')
        self.wo = WorkOrder.objects.create(
            customer=self.customer, model=self.model, kind='ORDER', status='CLOSED',
            order_line=self.linia, price_snapshot={'unit_price': '120.00', 'tax_rate': '21.00'})

        ara = timezone.now()
        self.rondes = {}
        for seq in (1, 2, 3):
            r = Ronda.objects.create(model=self.model, seq=seq, motiu='nova_mostra')
            resol_desbordament(r)
            ModelTask.objects.create(model=self.model, task_type=self.tt, ronda=r,
                                     work_order=self.wo, status='Done', origen='prevista')
            Entrega.objects.create(ronda=r, data=ara - datetime.timedelta(days=10 - seq),
                                   destinatari='Client', qui_informa=self.author.profile)
            self.rondes[seq] = r

        # Gates: la Montse de l'acta — manager amb CONFIGURE concedit individualment, SENSE
        # COMERCIAL (cas real d'staging). L'admin hi té totes dues.
        self.admin = self._usuari('admin@tea.local', 'admin')
        self.montse = self._usuari('montse@tea.local', 'manager', grant=['configure'])

    def _usuari(self, username, rol, grant=None):
        user = get_user_model().objects.create_user(username, password='x')
        prof, _ = UserProfile.objects.get_or_create(
            user=user, defaults={'nom_complet': username, 'rol_nom': rol})
        prof.rol_nom = rol
        prof.permisos = {'grant': list(grant or [])}
        prof.save(update_fields=['rol_nom', 'permisos'])
        # Rellegir: `user.profile` queda cachejat amb el perfil vell (mateix parany que
        # test_gate_comercial.py:63-64).
        return get_user_model().objects.get(pk=user.pk)

    def _grup(self, customer=None):
        grups = [g for g in get_billable_items(customer or self.customer)
                 if g['model']['id'] == self.model.id]
        self.assertEqual(len(grups), 1, 'un sol grup per model')
        return grups[0]

    def _bloc(self, clau_prefix, customer=None):
        return [b for b in self._grup(customer)['blocs'] if b['clau'].startswith(clau_prefix)]

    def _draft(self):
        dn, _ = create_or_get_draft(self.customer, user=self.author.profile)
        return dn


# ── SAFATA · extres, despeses i deduccions per model ────────────────────────────────────────
class SafataExtresTest(_BaseEsmena):

    def _amb_extres(self):
        WorkOrderAdjustment.objects.create(
            work_order=self.wo, kind='EXTRA_BILL', amount=Decimal('85.00'),
            description='Retoc de màniga fora de recepta')
        WorkOrderAdjustment.objects.create(
            work_order=self.wo, kind='DEDUCTION', amount=Decimal('30.00'),
            description='Recepta no executada: escalat')
        WorkOrderAdjustment.objects.create(
            work_order=self.wo, kind='EXTRA_ABSORB', amount=Decimal('40.00'),
            description='Absorbit, no es factura')
        supplier = Supplier.objects.create(name='Estampats SL')
        extern = Product.objects.create(code='ext-ea', name='Estampació externa',
                                        nature='EXTERNAL_SERVICE', tax_rate=Decimal('21.00'))
        Expense.objects.create(work_order=self.wo, product=extern, supplier=supplier,
                               cost_price=Decimal('10.00'), sale_price=Decimal('20.00'),
                               quantity=Decimal('3'), description='Estampació externa')

    def test_els_tres_tipus_arriben_i_amb_el_seu_import(self):
        self._amb_extres()
        extres = {e['kind']: e for e in self._grup()['extres']}
        self.assertEqual(set(extres), {'EXTRA', 'DEDUCTION', 'EXPENSE'})
        self.assertEqual(extres['EXTRA']['preu_proposat'], '85.00')
        self.assertEqual(extres['DEDUCTION']['preu_proposat'], '-30.00', 'la deducció és negativa')
        self.assertEqual(extres['EXPENSE']['preu_proposat'], '60.00', '3 × 20,00')

    def test_extra_absorb_no_hi_surt_mai(self):
        self._amb_extres()
        kinds = {e['kind'] for e in self._grup()['extres']}
        self.assertNotIn('EXTRA_ABSORB', kinds)
        # I no hi és per cap altre nom: només n'hi ha d'EXTRA/DEDUCTION/EXPENSE.
        self.assertEqual(len(self._grup()['extres']), 3)

    def test_un_model_nomes_amb_extres_i_cap_volta_entregada_no_desapareix(self):
        Entrega.objects.filter(ronda__model=self.model).delete()
        self._amb_extres()
        grups = [g for g in get_billable_items(self.customer) if g['model']['id'] == self.model.id]
        self.assertEqual(len(grups), 1, 'té extres: no és el cas buit de bloc A')
        self.assertEqual(grups[0]['blocs'], [], 'cap volta entregada: cap bloc')
        self.assertEqual(len(grups[0]['extres']), 3, 'EXTRA_BILL + DEDUCTION + EXPENSE')

    def test_un_extra_ja_albaranat_desapareix_de_la_safata(self):
        self._amb_extres()
        adj = WorkOrderAdjustment.objects.get(kind='EXTRA_BILL')
        dn = self._draft()
        add_lines_to_draft(dn, [{'model_id': self.model.id, 'clau': f'ajust-{adj.id}'}],
                           user=self.author.profile)
        claus = {e['clau'] for e in self._grup()['extres']}
        self.assertNotIn(f'ajust-{adj.id}', claus)
        # Els altres dos (deducció + despesa) segueixen pendents.
        self.assertEqual(len(self._grup()['extres']), 2)

    def test_una_volta_ja_albaranada_desapareix_de_la_safata(self):
        dn = self._draft()
        add_lines_to_draft(dn, [{'model_id': self.model.id, 'clau': 'pacte'}],
                           user=self.author.profile)
        totes = {r['seq'] for b in self._grup()['blocs'] for r in b['rondes']}
        self.assertEqual(totes, {3}, 'R1 i R2 (pacte) ja tenen línia; només queda R3 (directa)')


# ── ADD-LINES · 1 línia per model, import de la comanda, IVA i idempotència ─────────────────
class AddLinesTest(_BaseEsmena):

    def test_una_linia_per_bloc_pacte_mes_una_directa(self):
        dn = self._draft()
        created = add_lines_to_draft(dn, [
            {'model_id': self.model.id, 'clau': 'pacte'},
            {'model_id': self.model.id, 'clau': f'directe-{self.rondes[3].id}'},
        ], user=self.author.profile)
        self.assertEqual(len(created), 2, '1 línia pel bloc pacte + 1 per la directa')
        pacte_line = next(l for l in created if not l.encarrec_directe)
        directa_line = next(l for l in created if l.encarrec_directe)
        self.assertEqual({r.seq for r in pacte_line.rondes.all()}, {1, 2})
        self.assertEqual({r.seq for r in directa_line.rondes.all()}, {3})

    def test_import_es_el_preu_de_la_linia_de_comanda(self):
        dn = self._draft()
        created = add_lines_to_draft(dn, [{'model_id': self.model.id, 'clau': 'pacte'}],
                                     user=self.author.profile)
        self.assertEqual(created[0].unit_price, Decimal('120.00'))

    def test_iva_es_el_del_producte_de_la_linia_de_comanda(self):
        dn = self._draft()
        add_lines_to_draft(dn, [{'model_id': self.model.id, 'clau': 'pacte'}],
                           user=self.author.profile)
        dn.refresh_from_db()
        # subtotal 120,00 × 21 % = 25,20 (B3a, quantize 0.01).
        self.assertEqual(dn.subtotal, Decimal('120.00'))
        self.assertEqual(dn.tax_amount, Decimal('25.20'))

    def test_idempotent_entre_crides(self):
        dn = self._draft()
        add_lines_to_draft(dn, [{'model_id': self.model.id, 'clau': 'pacte'}],
                           user=self.author.profile)
        segona = add_lines_to_draft(dn, [{'model_id': self.model.id, 'clau': 'pacte'}],
                                    user=self.author.profile)
        self.assertEqual(segona, [], 'les voltes ja tenen línia: la safata viva no les torna a oferir')
        self.assertEqual(dn.lines.count(), 1)

    def test_idempotent_dins_de_la_mateixa_crida(self):
        dn = self._draft()
        created = add_lines_to_draft(dn, [
            {'model_id': self.model.id, 'clau': 'pacte'},
            {'model_id': self.model.id, 'clau': 'pacte'},
        ], user=self.author.profile)
        self.assertEqual(len(created), 1,
                         'dos "pacte" al mateix cos: la foto de la safata no veu el que la '
                         'crida acaba d\'afegir, i el guard "consumides" és qui talla la segona')
        self.assertEqual(dn.lines.count(), 1)

    def test_volta_en_curs_no_es_pot_afegir(self):
        r4 = Ronda.objects.create(model=self.model, seq=4, motiu='nova_mostra')
        resol_desbordament(r4)
        # NO entregada: en curs.
        dn = self._draft()
        created = add_lines_to_draft(dn, [
            {'model_id': self.model.id, 'clau': f'directe-{r4.id}'},
        ], user=self.author.profile)
        self.assertEqual(created, [], 'una volta EN CURS surt a la safata però no es pot marcar')


# ── L'HÍBRID A4 · recàlcul en esborrany, congelat NOMÉS a l'emissió ─────────────────────────
class HibridRecalculTest(_BaseEsmena):

    def test_abans_de_composar_res_no_hi_ha_contradiccio(self):
        dn = self._draft()
        add_lines_to_draft(dn, [{'model_id': self.model.id, 'clau': 'pacte'}],
                           user=self.author.profile)
        self.assertEqual(contradiccions_de_pacte(dn), [])

    def test_pujar_el_numeral_es_veu_a_contradiccions_de_pacte_i_no_toca_la_bd(self):
        dn = self._draft()
        add_lines_to_draft(dn, [
            {'model_id': self.model.id, 'clau': f'directe-{self.rondes[3].id}'},
        ], user=self.author.profile)
        self.linia.rounds_included = 3   # ara R3 hi cabria "dins"
        self.linia.save(update_fields=['rounds_included'])

        contr = contradiccions_de_pacte(dn)
        self.assertEqual(len(contr), 1)
        self.assertEqual(contr[0]['ronda'], 3)
        self.assertEqual(contr[0]['ara'], 'dins')

        # 🔑 Encara NO s'ha emès: el veredicte a la BD segueix congelat al de quan es va obrir.
        self.rondes[3].refresh_from_db()
        self.assertTrue(self.rondes[3].fora_de_comanda)

    def test_nomes_issue_delivery_note_escriu_el_veredicte_efectiu(self):
        dn = self._draft()
        add_lines_to_draft(dn, [{'model_id': self.model.id, 'clau': 'pacte'}],
                           user=self.author.profile)
        # Numeral encara a 2: cap contradicció. Emetre ha d'escriure el veredicte EFECTIU
        # (ja era 'dins' per a R1/R2, cap canvi visible, però és el mateix camí de codi).
        issue_delivery_note(dn, user=self.author.profile)
        dn.refresh_from_db()
        self.assertEqual(dn.status, 'ISSUED')
        self.rondes[1].refresh_from_db(); self.rondes[2].refresh_from_db()
        self.assertFalse(self.rondes[1].fora_de_comanda)
        self.assertFalse(self.rondes[2].fora_de_comanda)


# ── EMETRE · 409 als dos sentits, 200 en corregir, mai auto-converteix ──────────────────────
class EmetreContradiccioTest(_BaseEsmena):

    def test_409_directa_que_ara_cauria_dins(self):
        dn = self._draft()
        add_lines_to_draft(dn, [
            {'model_id': self.model.id, 'clau': f'directe-{self.rondes[3].id}'},
        ], user=self.author.profile)
        self.linia.rounds_included = 3
        self.linia.save(update_fields=['rounds_included'])

        with self.assertRaises(ContradiccioDePacte) as ctx:
            issue_delivery_note(dn, user=self.author.profile)
        self.assertEqual(ctx.exception.contradiccions[0]['ara'], 'dins')
        dn.refresh_from_db()
        self.assertEqual(dn.status, 'DRAFT', 'la 409 no emet res')

    def test_409_pacte_que_ara_cauria_fora(self):
        dn = self._draft()
        add_lines_to_draft(dn, [{'model_id': self.model.id, 'clau': 'pacte'}],
                           user=self.author.profile)
        self.linia.rounds_included = 1   # R2 (dins la línia pacte) ara en surt
        self.linia.save(update_fields=['rounds_included'])

        with self.assertRaises(ContradiccioDePacte) as ctx:
            issue_delivery_note(dn, user=self.author.profile)
        self.assertEqual(ctx.exception.contradiccions[0]['ronda'], 2)
        self.assertEqual(ctx.exception.contradiccions[0]['ara'], 'fora')

    def test_200_despres_de_corregir_el_numeral(self):
        dn = self._draft()
        add_lines_to_draft(dn, [
            {'model_id': self.model.id, 'clau': f'directe-{self.rondes[3].id}'},
        ], user=self.author.profile)
        self.linia.rounds_included = 3
        self.linia.save(update_fields=['rounds_included'])
        with self.assertRaises(ContradiccioDePacte):
            issue_delivery_note(dn, user=self.author.profile)

        self.linia.rounds_included = 2   # corregit
        self.linia.save(update_fields=['rounds_included'])
        issue_delivery_note(dn, user=self.author.profile)   # ja no llança
        dn.refresh_from_db()
        self.assertEqual(dn.status, 'ISSUED')

    def test_mai_auto_converteix(self):
        """Una 409 no toca ni la línia ni el preu: el preu d'una volta directa és LLIURE."""
        dn = self._draft()
        created = add_lines_to_draft(dn, [
            {'model_id': self.model.id, 'clau': f'directe-{self.rondes[3].id}'},
        ], user=self.author.profile)
        linia_directa = created[0]
        linia_directa.unit_price = Decimal('99.00')
        linia_directa.save(update_fields=['unit_price'])
        self.linia.rounds_included = 3
        self.linia.save(update_fields=['rounds_included'])
        with self.assertRaises(ContradiccioDePacte):
            issue_delivery_note(dn, user=self.author.profile)

        linia_directa.refresh_from_db()
        self.assertTrue(linia_directa.encarrec_directe, 'segueix sent directa: no s\'ha convertit')
        self.assertIsNone(linia_directa.linia_comanda_id, 'no se li ha enganxat cap pacte')
        self.assertEqual(linia_directa.unit_price, Decimal('99.00'), 'el preu lliure no es toca')

    def test_els_dos_none_de_numeral_efectiu_es_distingeixen(self):
        from fhort.models_app.models import Model
        sense_comanda = Model.objects.create(
            codi_intern='TEA-SS26-0099', codi_tenant='TEA', any=2026, sequencial=99,
            temporada='SS', customer=self.customer, garment_type_item=self.item,
            nom_prenda='Model sense comanda')
        self.assertEqual(numeral_efectiu(sense_comanda), (None, None),
                         'sense pacte, mai desborda: no és el mateix "None" que un límit')

        self.linia.rounds_included = None
        self.linia.save(update_fields=['rounds_included'])
        linia, numeral = numeral_efectiu(self.model)
        self.assertIsNotNone(linia)
        self.assertIsNone(numeral, 'pacte SENSE límit: (linia, None), no (None, None)')


# ── GATES · sense COMERCIAL, el diner no viatja ni s'escriu ─────────────────────────────────
class GatesComercialTest(_BaseEsmena):

    def setUp(self):
        super().setUp()
        self.dn = self._draft()
        self.linia_dn = add_lines_to_draft(
            self.dn, [{'model_id': self.model.id, 'clau': 'pacte'}], user=self.author.profile)[0]

    def _patch(self, viewset, user, pk, data, accio='partial_update'):
        req = self.factory.patch('/x/', data, format='json')
        force_authenticate(req, user=user)
        req.tenant = self.tenant
        return viewset.as_view({'patch': accio})(req, pk=pk)

    def _get(self, viewset, user, accio='retrieve', ruta='/x/', **kwargs):
        req = self.factory.get(ruta)
        force_authenticate(req, user=user)
        req.tenant = self.tenant
        return viewset.as_view({'get': accio})(req, **kwargs)

    def test_patch_unit_price_sense_comercial_403(self):
        resp = self._patch(DeliveryNoteLineViewSet, self.montse, self.linia_dn.pk,
                           {'unit_price': '999.00'})
        self.assertEqual(resp.status_code, 403)
        self.linia_dn.refresh_from_db()
        self.assertEqual(self.linia_dn.unit_price, Decimal('120.00'), 'la BD no s\'ha mogut')

    def test_patch_unit_price_amb_comercial_200(self):
        resp = self._patch(DeliveryNoteLineViewSet, self.admin, self.linia_dn.pk,
                           {'unit_price': '250.00'})
        self.assertEqual(resp.status_code, 200)

    def test_get_sense_comercial_no_porta_unit_price_ni_internal_rate(self):
        resp = self._get(DeliveryNoteLineViewSet, self.montse, pk=self.linia_dn.pk)
        self.assertEqual(resp.status_code, 200, 'la lectura NO es talla: es poda')
        self.assertNotIn('unit_price', resp.data)
        self.assertNotIn('internal_rate', resp.data)
        self.assertNotIn('line_total', resp.data)
        self.assertNotIn('internal_cost', resp.data)
        # El que SÍ que ha de seguir arribant (traçabilitat, no diner).
        self.assertIn('dn_number', resp.data)
        self.assertIn('model', resp.data)

    def test_get_amb_comercial_veu_unit_price(self):
        resp = self._get(DeliveryNoteLineViewSet, self.admin, pk=self.linia_dn.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['unit_price'], '120.00')

    def test_cost_hora_sense_comercial_403(self):
        tasca = self.rondes[1].tasques.first()
        req = self.factory.post('/x/', {'hourly_rate_override': '45.00'}, format='json')
        force_authenticate(req, user=self.montse)
        req.tenant = self.tenant
        resp = ModelTaskViewSet.as_view({'post': 'cost_hora'})(req, pk=tasca.pk)
        self.assertEqual(resp.status_code, 403)
        tasca.refresh_from_db()
        self.assertIsNone(tasca.hourly_rate_override)

    def test_cost_hora_amb_comercial_200(self):
        tasca = self.rondes[1].tasques.first()
        req = self.factory.post('/x/', {'hourly_rate_override': '45.00'}, format='json')
        force_authenticate(req, user=self.admin)
        req.tenant = self.tenant
        resp = ModelTaskViewSet.as_view({'post': 'cost_hora'})(req, pk=tasca.pk)
        self.assertEqual(resp.status_code, 200)
        tasca.refresh_from_db()
        self.assertEqual(tasca.hourly_rate_override, Decimal('45.00'))

    def test_assign_model_d_un_altre_client_400_mai_200(self):
        from fhort.models_app.models import Model
        model_altre = Model.objects.create(
            codi_intern='ALT-SS26-0001', codi_tenant='TEA', any=2026, sequencial=1,
            temporada='SS', customer=self.altre_client, garment_type_item=self.item,
            nom_prenda='Model d\'un altre client')
        req = self.factory.post('/x/', {'model_id': model_altre.pk}, format='json')
        force_authenticate(req, user=self.admin)
        req.tenant = self.tenant
        resp = SalesOrderLineViewSet.as_view({'post': 'assign_model'})(req, pk=self.linia.pk)
        self.assertEqual(resp.status_code, 400, 'el model i la comanda han de ser del mateix client')
        self.assertFalse(WorkOrder.objects.filter(model=model_altre).exists())


# ── PDF · bloc per model, rondes en una línia, extres sota, notes una vegada ────────────────
class PdfBlocsTest(_BaseEsmena):

    def _pdf(self, dn, lang='ca'):
        from fhort.commerce.pdf_service import generate_delivery_note_pdf
        return _pdf_text(generate_delivery_note_pdf(dn, lang=lang))

    def test_bloc_per_model_amb_rondes_en_una_linia_i_directa_amb_tasques(self):
        dn = self._draft()
        add_lines_to_draft(dn, [
            {'model_id': self.model.id, 'clau': 'pacte'},
            {'model_id': self.model.id, 'clau': f'directe-{self.rondes[3].id}'},
        ], user=self.author.profile)
        dn.refresh_from_db()
        text = self._pdf(dn)

        self.assertIn('Top BEYONCÉ', text, 'la identitat del model surt un sol cop')
        self.assertEqual(text.count('Top BEYONCÉ'), 1,
                         'un extra o una segona volta no obren una segona capçalera de model')
        self.assertIn('Ronda 1', text)
        self.assertIn('Ronda 2', text)
        self.assertIn('Ronda 3', text)
        self.assertIn('Encàrrec directe sense pressupost', text,
                      'la volta fora de pacte ho diu explícitament, en negreta a la maqueta')
        # La volta directa arrossega el nom de la tasca feta, perquè justifiqui el preu lliure.
        self.assertIn('Definició POM', text)

    def test_extres_van_sota_les_rondes_del_seu_model(self):
        WorkOrderAdjustment.objects.create(
            work_order=self.wo, kind='EXTRA_BILL', amount=Decimal('85.00'),
            description='Retoc de màniga fora de recepta')
        dn = self._draft()
        adj = WorkOrderAdjustment.objects.get(kind='EXTRA_BILL')
        add_lines_to_draft(dn, [
            {'model_id': self.model.id, 'clau': 'pacte'},
            {'model_id': self.model.id, 'clau': f'ajust-{adj.id}'},
        ], user=self.author.profile)
        dn.refresh_from_db()
        text = self._pdf(dn)

        pos_ronda = text.index('Ronda 1')
        pos_extra = text.index('Retoc de màniga fora de recepta')
        self.assertGreater(pos_extra, pos_ronda, 'l\'extra surt DESPRÉS de les voltes, no abans')

    def test_notes_surten_una_sola_vegada(self):
        dn = self._draft()
        add_lines_to_draft(dn, [{'model_id': self.model.id, 'clau': 'pacte'}],
                           user=self.author.profile)
        dn.notes = 'Text de comentari únic i identificable'
        dn.save(update_fields=['notes'])
        dn.refresh_from_db()
        text = self._pdf(dn)
        self.assertEqual(text.count('Text de comentari únic i identificable'), 1,
                         'abans hi havia "Comentaris" i "Observacions": el mateix text dues '
                         'vegades. Ara només el bloc "Comentaris".')
        self.assertIn('Comentaris', text)
