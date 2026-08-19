"""U2/R3 · LA PROPOSTA DE RUN I DE TALLA BASE D'UN ITEM.

**Per què aquests dos camps existeixen.** «El GTI proposa, el model disposa.» El catàleg de
peces ensenya UN run i UNA talla base per item, i no hi havia on desar-los. El que ja existia
diu una altra cosa i aquest tram **no ho toca**:

  · `grading_rule_set.size_system` — n'hi ha UN per item, però la llei C1 diu que el joc de
    regles s'assigna **al MODEL** i el de l'item és només un suggeriment.
  · `ItemBaseSet` — n'hi ha **N** per item (un per món), i la seva talla base es declara en
    NÉIXER el set i després no es re-tria.

La proposta és una tercera cosa, tova i independent: no mana sobre cap de les dues.

**Per què l'etiqueta i no un FK.** És la llei del motor: les regles ancoren per
`base_size_label` i la fila de `SizeDefinition` és mer metadata del seed (CAT2.1). Un FK
tornaria a lligar la proposta a una fila d'un catàleg que es reordena.
"""
import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.pom.models import GarmentGroup, GarmentType, SizeDefinition, SizeSystem
from fhort.tasks.models import GarmentTypeItem


class PropostaRunTallaBaseTest(TenantTestCase):

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
        from fhort.accounts.models import UserProfile
        self.user = get_user_model().objects.create(username='r3_configurador')
        prof, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'R3'})
        prof.rol_nom = 'admin'
        prof.save(update_fields=['rol_nom'])
        self.user = get_user_model().objects.get(pk=self.user.pk)

        self.alpha = SizeSystem.objects.create(codi='R3_ALPHA', nom='Alpha EU', base_unit='ALPHA')
        for i, et in enumerate(['XS', 'S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.alpha, etiqueta=et, ordre=i)
        self.numeric = SizeSystem.objects.create(
            codi='R3_NUM', nom='Numeric EU', base_unit='NUMERIC_EU')
        for i, et in enumerate(['36', '38', '40']):
            SizeDefinition.objects.create(size_system=self.numeric, etiqueta=et, ordre=i)

        self.grup = GarmentGroup.objects.create(codi='R3_TOPS', nom='Tops')
        self.familia = GarmentType.objects.create(
            codi_client='R3_WOVEN', nom_client='Teixit pla', grup='R3_TOPS', grup_ref=self.grup)
        self.item = GarmentTypeItem.objects.create(
            garment_type=self.familia, code='r3_blouse', name='Blusa')

        self.api = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        self.api.force_authenticate(user=self.user)
        self.url = f'/api/v1/garment-type-items/{self.item.pk}/'

    # ── L'ESTAT NORMAL: sense proposta ────────────────────────────────────────

    def test_un_item_SENSE_proposta_es_valid_i_ho_diu(self):
        """No hi ha cap valor per defecte inventat: buit vol dir buit, i la pantalla ho dirà."""
        self.item.full_clean()
        self.assertIsNone(self.item.proposed_size_system_id)
        self.assertEqual(self.item.proposed_base_size_label, '')

        resp = self.api.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data['proposed_size_system'])
        self.assertEqual(resp.data['proposed_base_size_label'], '')
        self.assertIsNone(resp.data['proposed_size_system_nom'])

    # ── L'ESCRIPTURA ──────────────────────────────────────────────────────────

    def test_la_pantalla_desa_run_i_talla_base_junts(self):
        resp = self.api.patch(self.url, {
            'proposed_size_system': self.alpha.pk, 'proposed_base_size_label': 'M',
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)

        self.item.refresh_from_db()
        self.assertEqual(self.item.proposed_size_system_id, self.alpha.pk)
        self.assertEqual(self.item.proposed_base_size_label, 'M')
        self.assertEqual(resp.data['proposed_size_system_nom'], 'Alpha EU')

    # ── LA COHERÈNCIA: cap etiqueta inventada ─────────────────────────────────

    def test_una_etiqueta_que_el_run_NO_conte_es_rebutja(self):
        """'38' és del run numèric: proposar-la amb el run alpha seria un valor inventat."""
        resp = self.api.patch(self.url, {
            'proposed_size_system': self.alpha.pk, 'proposed_base_size_label': '38',
        }, format='json')
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn('proposed_base_size_label', resp.data)

    def test_canviar_de_run_SENSE_re_triar_la_talla_cau(self):
        """Triar un altre run és tornar a triar la talla base (ho fa la mateixa maqueta).
        Deixar-hi l'etiqueta vella deixaria una proposta incoherent desada en silenci."""
        self.item.proposed_size_system = self.alpha
        self.item.proposed_base_size_label = 'M'
        self.item.save()

        resp = self.api.patch(self.url, {'proposed_size_system': self.numeric.pk}, format='json')
        self.assertEqual(resp.status_code, 400, resp.data)

        self.item.refresh_from_db()
        self.assertEqual(self.item.proposed_size_system_id, self.alpha.pk,
                         'un PATCH rebutjat no pot haver mogut res')

    def test_canviar_de_run_AMB_la_talla_nova_passa(self):
        self.item.proposed_size_system = self.alpha
        self.item.proposed_base_size_label = 'M'
        self.item.save()

        resp = self.api.patch(self.url, {
            'proposed_size_system': self.numeric.pk, 'proposed_base_size_label': '38',
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)

        self.item.refresh_from_db()
        self.assertEqual(self.item.proposed_size_system_id, self.numeric.pk)
        self.assertEqual(self.item.proposed_base_size_label, '38')

    def test_un_run_SENSE_talla_base_es_una_proposta_a_mitges_valida(self):
        """El skip és la mateixa llei que A3: mentre en falti un dels dos, no es valida res."""
        resp = self.api.patch(self.url, {'proposed_size_system': self.alpha.pk}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_esborrar_la_proposta_es_un_gest_valid(self):
        self.item.proposed_size_system = self.alpha
        self.item.proposed_base_size_label = 'M'
        self.item.save()

        resp = self.api.patch(self.url, {
            'proposed_size_system': None, 'proposed_base_size_label': '',
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)

        self.item.refresh_from_db()
        self.assertIsNone(self.item.proposed_size_system_id)
        self.assertEqual(self.item.proposed_base_size_label, '')

    # ── LA INDEPENDÈNCIA: no mana sobre res del que ja existia ────────────────

    def test_la_proposta_NO_toca_el_joc_de_regles_ni_la_talla_base_real(self):
        self.api.patch(self.url, {
            'proposed_size_system': self.alpha.pk, 'proposed_base_size_label': 'M',
        }, format='json')

        self.item.refresh_from_db()
        self.assertIsNone(self.item.grading_rule_set_id,
                          'la proposta ha assignat un joc de regles: no és seva la decisió (C1)')
        self.assertIsNone(self.item.base_size_definition_id,
                          'la proposta ha tocat la talla base real de la plantilla')

    def test_esborrar_el_run_proposat_NO_bloqueja_ni_s_endu_l_item(self):
        """SET_NULL i no PROTECT: que un item «proposés» un run no pot impedir retirar-lo
        del catàleg, ni fer desaparèixer l'item amb ell."""
        self.item.proposed_size_system = self.alpha
        self.item.save()

        self.alpha.delete()

        self.item.refresh_from_db()
        self.assertIsNone(self.item.proposed_size_system_id)
        self.assertTrue(GarmentTypeItem.objects.filter(pk=self.item.pk).exists())

    # ── LA NO-REGRESSIÓ d'A3 ──────────────────────────────────────────────────

    def test_la_validacio_d_A3_segueix_viva(self):
        """El probe del serializer ara porta quatre camps; el constrenyiment vell no pot
        haver-se perdut pel camí."""
        from fhort.pom.models import GradingRuleSet
        rs = GradingRuleSet.objects.create(nom='RS R3', size_system=self.alpha)
        talla_altra = SizeDefinition.objects.get(size_system=self.numeric, etiqueta='38')

        with self.assertRaises(ValidationError):
            GarmentTypeItem(garment_type=self.familia, code='x', name='X',
                            grading_rule_set=rs, base_size_definition=talla_altra).clean()
