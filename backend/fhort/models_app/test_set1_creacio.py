"""SET-1 · A4+A6 — creació d'un conjunt des d'un GTI declarat `is_set`.

Convenció del repo: `python manage.py test fhort.models_app` (no pytest).

Fins ara la branca multi-peça de `create_model_wizard` existia sencera però **totes les peces
naixien idèntiques**: `**garment_fields` era el MATEIX dict per a cadascuna (forat #1 del
dimensionat, `views.py:849`). Aquesta única línia decidia si A6 (grading per part) era gratis o
no. El que defensen aquests tests:

  1. Un GTI compost de 2 parts genera 2 Models amb `garment_type_item` DISTINT i amb el nom de
     peça de la composició.
  2. Cada peça hereta el `grading_rule_set` del SEU part_item, i per tant materialitza les
     regles del seu contenidor — que és **A6 verificat sense codi nou** (QA A6 del brief C-5).
  3. El GTI mana: un payload que el contradiu (peça única sobre un conjunt, `num_pieces`
     diferent, o multi-peça sobre un item que no és conjunt) rebota amb 400.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import GarmentSet, Model, ModelGradingRule
from fhort.models_app.views import create_model_wizard
from fhort.pom.models import (GarmentType, GradingRule, GradingRuleSet, POMMaster,
                              SizeDefinition, SizeSystem)
from fhort.tasks.models import Customer, GarmentTypeItem, GarmentTypeItemPart


class CreacioSetTest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='tecwiz')
        UserProfile.objects.get_or_create(user=self.user)
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.customer = Customer.objects.create(codi='SET', nom='Client SET')

        self.ss = SizeSystem.objects.create(codi='SET_SS', nom='Sistema SET')
        for i, et in enumerate(('S', 'M', 'L')):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.talla_m = SizeDefinition.objects.get(size_system=self.ss, etiqueta='M')

        self.gt = GarmentType.objects.create(codi_client='SETGT', nom_client='Família SET',
                                             grup='SWIMWEAR')
        # Dos contenidors de grading DISTINTS, un per peça: és el que A6 vol veure separat.
        self.rs_top = self._ruleset('SET_RS_TOP', 'POM_TOP')
        self.rs_bot = self._ruleset('SET_RS_BOT', 'POM_BOT')

        self.item_top = GarmentTypeItem.objects.create(
            garment_type=self.gt, code='set_top', name='Top',
            grading_rule_set=self.rs_top, base_size_definition=self.talla_m)
        self.item_bot = GarmentTypeItem.objects.create(
            garment_type=self.gt, code='set_bot', name='Bottom',
            grading_rule_set=self.rs_bot, base_size_definition=self.talla_m)
        self.item_set = GarmentTypeItem.objects.create(
            garment_type=self.gt, code='set_bikini', name='Bikini', is_set=True)
        GarmentTypeItemPart.objects.create(set_item=self.item_set, part_item=self.item_top,
                                           ordre=1, nom_peca='Top')
        GarmentTypeItemPart.objects.create(set_item=self.item_set, part_item=self.item_bot,
                                           ordre=2, nom_peca='Braga')

    def _ruleset(self, nom, pom_codi):
        rs = GradingRuleSet.objects.create(nom=nom, size_system=self.ss)
        pom = POMMaster.objects.create(codi_client=pom_codi, nom_client=pom_codi)
        GradingRule.objects.create(rule_set=rs, pom=pom, logica='LINEAR', increment=1.0,
                                   talla_base=SizeDefinition.objects.get(
                                       size_system=self.ss, etiqueta='M'))
        return rs

    def _crear(self, **extra):
        payload = {
            'year': 2026, 'season': 'SS', 'customer_id': self.customer.id,
            'nom_prenda': 'Bikini Palma', 'garment_type_item_id': self.item_set.id,
            'size_system_id': self.ss.id, 'size_run': 'S·M·L', 'base_size': 'M',
        }
        payload.update(extra)
        req = APIRequestFactory().post('/api/v1/models/create-wizard/', payload, format='json')
        force_authenticate(req, user=self.user)
        return create_model_wizard(req)

    # ── A4 ────────────────────────────────────────────────────────────────────
    def test_gti_compost_genera_dues_peces_amb_item_distint(self):
        resp = self._crear()
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['num_pieces'], 2)
        self.assertEqual(len(resp.data['pieces']), 2)

        gs = GarmentSet.objects.get(pk=resp.data['garment_set_id'])
        peces = list(Model.objects.filter(garment_set=gs).order_by('piece_number'))
        self.assertEqual([p.piece_number for p in peces], [1, 2])
        # El forat #1: cada peça porta el SEU item, no el del conjunt clonat.
        self.assertEqual([p.garment_type_item_id for p in peces],
                         [self.item_top.id, self.item_bot.id])
        self.assertEqual([p.nom_prenda for p in peces], ['Top', 'Braga'])
        # El codi comercial és un i viu al conjunt; les peces són -01/-02.
        self.assertTrue(peces[0].codi_intern.endswith('-01'))
        self.assertTrue(peces[1].codi_intern.endswith('-02'))
        self.assertEqual(gs.nom_comercial, 'Bikini Palma')

    def test_is_multipiece_no_cal_al_payload(self):
        """El GTI mana: `is_multipiece` és redundant i la creació funciona sense enviar-lo."""
        resp = self._crear()
        self.assertEqual(resp.status_code, 201)
        self.assertIn('garment_set_id', resp.data)

    # ── A6 (QA sense codi nou) ────────────────────────────────────────────────
    def test_cada_peca_gradua_pel_seu_contenidor(self):
        """A6: dues parts amb GTI distint materialitzen les regles dels SEUS rulesets."""
        resp = self._crear()
        peces = list(Model.objects.filter(garment_set_id=resp.data['garment_set_id'])
                     .order_by('piece_number'))
        self.assertEqual([p.grading_rule_set_id for p in peces],
                         [self.rs_top.id, self.rs_bot.id])
        poms_top = set(ModelGradingRule.objects.filter(model=peces[0])
                       .values_list('pom__codi_client', flat=True))
        poms_bot = set(ModelGradingRule.objects.filter(model=peces[1])
                       .values_list('pom__codi_client', flat=True))
        self.assertEqual(poms_top, {'POM_TOP'})
        self.assertEqual(poms_bot, {'POM_BOT'})
        self.assertNotEqual(poms_top, poms_bot)   # cap peça no ha heretat el contenidor de l'altra

    # ── El GTI mana: contradiccions ───────────────────────────────────────────
    def test_payload_peca_unica_sobre_un_set_400(self):
        resp = self._crear(is_multipiece=False)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'contradiccio_gti_set')

    def test_num_pieces_que_contradiu_la_composicio_400(self):
        resp = self._crear(num_pieces=3)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'contradiccio_gti_num_pieces')

    def test_multipeca_sobre_un_item_que_no_es_set_400(self):
        resp = self._crear(garment_type_item_id=self.item_top.id,
                           is_multipiece=True, num_pieces=2)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'contradiccio_gti_no_set')

    def test_set_sense_composicio_400(self):
        buit = GarmentTypeItem.objects.create(garment_type=self.gt, code='set_buit',
                                              name='Conjunt sense parts', is_set=True)
        resp = self._crear(garment_type_item_id=buit.id)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'set_sense_composicio')

    def test_peca_unica_normal_intacta(self):
        """El ~90% de la creació no canvia."""
        resp = self._crear(garment_type_item_id=self.item_top.id)
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertIn('id', resp.data)
        m = Model.objects.get(pk=resp.data['id'])
        self.assertIsNone(m.garment_set_id)
