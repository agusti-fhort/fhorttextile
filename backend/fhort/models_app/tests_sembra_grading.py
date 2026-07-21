"""Tests de la CADENA DE SEMBRA (materialitzar-poms) i de la porta D1 d'update-step2.

Sprint FIX WIZARD EDICIÓ + SEMBRA FIABLE · F3.1. Convenció del repo: fitxer `test*.py` dins de
l'app, executat amb `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).

Fins avui aquesta cadena tenia ZERO cobertura (DIAGNOSI_GTI_PLANTILLA §B1.3: «NO EXISTEIX cap
test del model ni de l'endpoint»), i és la que copia el patrimoni de l'item al model i la que
decideix si un model es queda sense regles de graduació. El que defensen aquests tests:

  1. materialitzar-poms sembra amb valors (ITEM_STANDARD) i sense (TEMPLATE), és IDEMPOTENT i
     respecta la SOBIRANIA del model (mai trepitja MANUAL/IMPORTED/FITTED ni res amb valor).
  2. El subconjunt `pom_ids` (F2.2) sembra només el que se li demana, i els ids que no són del
     mapa de l'item es reporten en comptes d'ignorar-se en silenci.
  3. La porta D1 d'update-step2: ruleset buit → 400, size_system creuat → 400, customer creuat →
     409 fins que arriba `confirmar_altre_client`, i llavors 200 amb materialització REAL i
     provinença correcta (R8: CLIENT_RUN si la font ho és, no CANONICAL per defecte).

FIXTURES: cada classe crea les seves (codis propis, `_codi()` amb prefix per classe) per no
xocar amb el deute conegut de TenantTestCase entre classes germanes (col·lisió d'unicitat de
SizeFitting, que el signal de creació de Model dispara).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.models_app.views import materialize_poms_view, update_model_step2
from fhort.pom.models import (GarmentPOMMap, GarmentType, GradingRule, GradingRuleSet,
                              ItemBaseMeasurement, POMMaster, SizeDefinition, SizeSystem)
from fhort.tasks.models import Customer, GarmentTypeItem


class _BaseSembraTest(TenantTestCase):
    """Bastida comuna: tenant, usuari i helpers de fixtures. Cada subclasse posa el seu PREFIX."""

    PREFIX = 'XX'

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
        self.user = get_user_model().objects.create(username=f'tec{self.PREFIX}')
        UserProfile.objects.get_or_create(user=self.user)
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self._seq = 0

    # ── fixtures ──────────────────────────────────────────────────────────────
    def _codi(self, base):
        return f'{self.PREFIX}_{base}'

    def _pom(self, codi):
        return POMMaster.objects.create(codi_client=self._codi(codi), nom_client=f'POM {codi}')

    def _item(self, code='blouse'):
        gt = GarmentType.objects.create(
            codi_client=self._codi('GT'), nom_client='Família de prova', grup='TOPS')
        return GarmentTypeItem.objects.create(
            garment_type=gt, code=self._codi(code), name='Item de prova')

    def _model(self, **kw):
        self._seq += 1
        return Model.objects.create(
            codi_intern=f'{self.PREFIX}-M{self._seq}', codi_tenant='TST', any=2026,
            temporada='SS', sequencial=self._seq, created_by_id=self.user.profile.id, **kw)

    def _size_system(self, codi, talles=('S', 'M', 'L')):
        ss = SizeSystem.objects.create(codi=self._codi(codi), nom=f'Sistema {codi}')
        for i, et in enumerate(talles):
            SizeDefinition.objects.create(size_system=ss, etiqueta=et, ordre=i)
        return ss

    # ── crides ────────────────────────────────────────────────────────────────
    def _materialitzar(self, model, body=None):
        req = (APIRequestFactory().post(f'/api/v1/models/{model.id}/materialitzar-poms/', body,
                                        format='json')
               if body is not None
               else APIRequestFactory().post(f'/api/v1/models/{model.id}/materialitzar-poms/'))
        force_authenticate(req, user=self.user)
        return materialize_poms_view(req, model.id)

    def _step2(self, model, payload):
        req = APIRequestFactory().patch(f'/api/v1/models/{model.id}/update-step2/', payload,
                                        format='json')
        force_authenticate(req, user=self.user)
        return update_model_step2(req, model.id)


class MaterialitzarPomsTest(_BaseSembraTest):
    """La sembra item→model: què copia, què respecta i què no toca mai."""

    PREFIX = 'SEM'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.pom_amb_valor = self._pom('A')
        self.pom_sense_valor = self._pom('B')
        for i, pom in enumerate([self.pom_amb_valor, self.pom_sense_valor]):
            GarmentPOMMap.objects.create(garment_type_item=self.item, pom=pom,
                                         is_key=(i == 0), ordre=i)
        # Només un dels dos POMs té valor a la plantilla de l'item.
        ItemBaseMeasurement.objects.create(
            garment_type_item=self.item, pom=self.pom_amb_valor,
            base_value_cm='60.00', tol_minus='0.50', tol_plus='0.50', nom_fitxa='A')
        ItemBaseMeasurement.objects.create(
            garment_type_item=self.item, pom=self.pom_sense_valor, base_value_cm=None)
        self.model = self._model(garment_type_item=self.item,
                                 garment_type=self.item.garment_type)

    def test_sembra_valors_i_buits(self):
        resp = self._materialitzar(self.model)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['seeded'], 1)         # el que porta valor
        self.assertEqual(resp.data['materialized'], 1)   # el que no
        self.assertEqual(resp.data['total_template'], 2)

        amb = BaseMeasurement.objects.get(model=self.model, pom=self.pom_amb_valor)
        self.assertEqual(amb.origen, 'ITEM_STANDARD')
        self.assertEqual(amb.base_value_cm, 60.0)
        self.assertEqual(amb.nom_fitxa, 'A')
        self.assertEqual(str(amb.tolerancia_minus), '0.50')
        self.assertTrue(amb.is_key)          # is_key/ordre vénen del GarmentPOMMap, no de la plantilla

        sense = BaseMeasurement.objects.get(model=self.model, pom=self.pom_sense_valor)
        self.assertEqual(sense.origen, 'TEMPLATE')
        self.assertIsNone(sense.base_value_cm)

    def test_idempotent(self):
        self._materialitzar(self.model)
        resp = self._materialitzar(self.model)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['seeded'], 0)
        self.assertEqual(resp.data['materialized'], 0)
        self.assertEqual(resp.data['skipped'], 2)
        self.assertEqual(BaseMeasurement.objects.filter(model=self.model).count(), 2)

    def test_sobirania_no_trepitja_manual_ni_importat(self):
        """A partir del primer valor, el Model és sobirà: la sembra no el toca."""
        BaseMeasurement.objects.create(model=self.model, pom=self.pom_amb_valor,
                                       base_value_cm=99.0, origen='MANUAL')
        BaseMeasurement.objects.create(model=self.model, pom=self.pom_sense_valor,
                                       base_value_cm=42.0, origen='IMPORTED')
        resp = self._materialitzar(self.model)
        self.assertEqual(resp.data['skipped'], 2)
        self.assertEqual(resp.data['seeded'], 0)
        manual = BaseMeasurement.objects.get(model=self.model, pom=self.pom_amb_valor)
        self.assertEqual(manual.base_value_cm, 99.0)
        self.assertEqual(manual.origen, 'MANUAL')
        importat = BaseMeasurement.objects.get(model=self.model, pom=self.pom_sense_valor)
        self.assertEqual(importat.base_value_cm, 42.0)
        self.assertEqual(importat.origen, 'IMPORTED')

    def test_omple_template_buit_quan_l_item_porta_valor(self):
        """L'única fila existent que SÍ es reomple: TEMPLATE sense valor."""
        BaseMeasurement.objects.create(model=self.model, pom=self.pom_amb_valor,
                                       base_value_cm=None, origen='TEMPLATE')
        resp = self._materialitzar(self.model)
        self.assertEqual(resp.data['seeded'], 1)
        fila = BaseMeasurement.objects.get(model=self.model, pom=self.pom_amb_valor)
        self.assertEqual(fila.origen, 'ITEM_STANDARD')
        self.assertEqual(fila.base_value_cm, 60.0)

    # ── F2.2 · subconjunt ─────────────────────────────────────────────────────
    def test_subconjunt_pom_ids(self):
        resp = self._materialitzar(self.model, {'pom_ids': [self.pom_amb_valor.id]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['seeded'], 1)
        self.assertEqual(resp.data['requested'], 1)
        self.assertEqual(resp.data['total_template'], 2)   # el mapa sencer segueix sent 2
        self.assertEqual(BaseMeasurement.objects.filter(model=self.model).count(), 1)
        self.assertFalse(BaseMeasurement.objects
                         .filter(model=self.model, pom=self.pom_sense_valor).exists())

    def test_sense_pom_ids_sembra_tot(self):
        """Cap caller antic queda trencat: sense el paràmetre, es sembra tot el mapa."""
        resp = self._materialitzar(self.model, {})
        self.assertEqual(BaseMeasurement.objects.filter(model=self.model).count(), 2)
        self.assertNotIn('requested', resp.data)

    def test_pom_ids_buit_no_sembra_res(self):
        resp = self._materialitzar(self.model, {'pom_ids': []})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(BaseMeasurement.objects.filter(model=self.model).count(), 0)

    def test_pom_ids_desconegut_es_reporta(self):
        aliè = self._pom('Z')   # existeix, però no és al GarmentPOMMap de l'item
        resp = self._materialitzar(self.model, {'pom_ids': [self.pom_amb_valor.id, aliè.id]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['pom_ids_desconeguts'], [aliè.id])
        self.assertIn('warning', resp.data)
        self.assertEqual(BaseMeasurement.objects.filter(model=self.model).count(), 1)

    def test_pom_ids_mal_format(self):
        self.assertEqual(self._materialitzar(self.model, {'pom_ids': 'tot'}).status_code, 400)
        self.assertEqual(self._materialitzar(self.model, {'pom_ids': ['a']}).status_code, 400)

    def test_model_sense_item(self):
        orfe = self._model()
        resp = self._materialitzar(orfe)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['materialized'], 0)
        self.assertIn('warning', resp.data)


class UpdateStep2GradingTest(_BaseSembraTest):
    """La porta D1: cap ruleset s'assigna sense servir, i la provinença no menteix (R8)."""

    PREFIX = 'D1'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.pom = self._pom('A')
        GarmentPOMMap.objects.create(garment_type_item=self.item, pom=self.pom, ordre=0)
        self.ss_model = self._size_system('SS_MODEL')
        self.ss_altre = self._size_system('SS_ALTRE')
        self.client_a = Customer.objects.create(codi=f'{self.PREFIX[:2]}A', nom='Client A')
        self.client_b = Customer.objects.create(codi=f'{self.PREFIX[:2]}B', nom='Client B')
        self.model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                                 size_system=self.ss_model, size_run_model='S·M·L',
                                 base_size_label='M', customer=self.client_a)

    def _ruleset(self, nom, *, size_system, customer=None, origen=None, amb_regla=True):
        rs = GradingRuleSet.objects.create(nom=self._codi(nom), size_system=size_system,
                                           customer=customer, origen=origen)
        if amb_regla:
            GradingRule.objects.create(
                rule_set=rs, pom=self.pom,
                talla_base=size_system.talles.get(etiqueta='M'),
                logica=GradingRule.LOGICA_LINEAR, increment='1.00', actiu=True)
        return rs

    def test_ruleset_buit_bloqueja(self):
        rs = self._ruleset('BUIT', size_system=self.ss_model, amb_regla=False)
        resp = self._step2(self.model, {'grading_rule_set_id': rs.id})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'GRADING_RULESET_EMPTY')
        self.model.refresh_from_db()
        self.assertIsNone(self.model.grading_rule_set_id)

    def test_size_system_creuat_bloqueja(self):
        rs = self._ruleset('ALTRE_SS', size_system=self.ss_altre)
        resp = self._step2(self.model, {'grading_rule_set_id': rs.id})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'GRADING_SIZE_SYSTEM_MISMATCH')
        self.model.refresh_from_db()
        self.assertIsNone(self.model.grading_rule_set_id)

    def test_customer_creuat_avisa_i_despres_desa_amb_provinenca_real(self):
        """409 conscient → confirmació → 200 amb regles residents REALS i origen R8."""
        rs = self._ruleset('ALTRE_CLIENT', size_system=self.ss_model, customer=self.client_b,
                           origen=GradingRuleSet.ORIGEN_CLIENT_RUN)

        resp = self._step2(self.model, {'grading_rule_set_id': rs.id})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['tipus'], 'ruleset_altre_client')
        self.model.refresh_from_db()
        self.assertIsNone(self.model.grading_rule_set_id)

        resp = self._step2(self.model, {'grading_rule_set_id': rs.id,
                                        'confirmar_altre_client': True})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['regles_materialitzades'], 1)
        self.model.refresh_from_db()
        self.assertEqual(self.model.grading_rule_set_id, rs.id)
        # R8 — la provinença de les regles residents surt del ruleset font, no d'un literal.
        mgr = ModelGradingRule.objects.get(model=self.model, pom=self.pom)
        self.assertEqual(mgr.origen, 'CLIENT_RUN')

    def test_ruleset_canonic_materialitza_com_a_canonic(self):
        rs = self._ruleset('CANONIC', size_system=self.ss_model,
                           origen=GradingRuleSet.ORIGEN_CANONICAL)
        resp = self._step2(self.model, {'grading_rule_set_id': rs.id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ModelGradingRule.objects.get(model=self.model, pom=self.pom).origen,
                         'CANONICAL')

    def test_canvi_de_size_system_al_mateix_patch_es_valida_contra_el_nou(self):
        """D1 valida contra els valors POSTERIORS: el mateix PATCH pot moure el size_system."""
        rs = self._ruleset('DEL_NOU_SS', size_system=self.ss_altre)
        resp = self._step2(self.model, {'grading_rule_set_id': rs.id,
                                        'size_system_id': self.ss_altre.id})
        self.assertEqual(resp.status_code, 200)
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_system_id, self.ss_altre.id)
        self.assertEqual(self.model.grading_rule_set_id, rs.id)

    def test_desar_sense_tocar_la_graduacio_no_rebota(self):
        """Re-desar un model amb ruleset assignat, sense enviar-lo, no ha de validar res."""
        rs = self._ruleset('VIGENT', size_system=self.ss_model)
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': rs.id}).status_code, 200)
        resp = self._step2(self.model, {'size_run': 'S·M'})
        self.assertEqual(resp.status_code, 200)
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'S·M')
        self.assertEqual(self.model.grading_rule_set_id, rs.id)
