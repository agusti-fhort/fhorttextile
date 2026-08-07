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
from decimal import Decimal

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.models_app.views import materialize_poms_view, update_model_step2
from fhort.pom.models import (GarmentPOMMap, GarmentType, GradingRule, GradingRuleSet,
                              ItemBaseMeasurement, ItemBaseSet, POMMaster, SizeDefinition,
                              SizeSystem)
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

    def _base_set(self, item, size_system=None, base_size='M', fit=None):
        """BaseSet del món (item x size_system x fit). B1: tota mesura base viu dins un set.

        `fit=None` passa per normalize_fit_type, que en un schema sense FitType sembrat (el cas
        d'aquests tests) deixa fit_type a NULL — el mateix slot on cau Model.fit_type='Regular'.
        """
        from fhort.pom.models import normalize_fit_type
        if size_system is None:
            size_system = self._size_system('BS')
        return ItemBaseSet.objects.create(
            garment_type_item=item, size_system=size_system,
            fit_type=normalize_fit_type(fit),
            base_size_definition=SizeDefinition.objects.get(
                size_system=size_system, etiqueta=base_size),
        )

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
        # B1 — tota mesura base viu dins un BaseSet. Aquests models no porten size_system, així
        # que la sembra cau al camí LLEGAT (item inequívoc, 1 sol set) i el que defensen aquests
        # tests — què copia, què respecta — no canvia.
        self.base_set = self._base_set(self.item)
        # Només un dels dos POMs té valor a la plantilla de l'item.
        ItemBaseMeasurement.objects.create(
            base_set=self.base_set,
            garment_type_item=self.item, pom=self.pom_amb_valor,
            base_value_cm='60.00', tol_minus='0.50', tol_plus='0.50', nom_fitxa='A')
        ItemBaseMeasurement.objects.create(
            base_set=self.base_set,
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


# ═════════════════════════════════════════════════════════════════════════════════════════
# MELÓ 2026-07-22 — LINEAR+0=FIXED (fase A) · PRINCIPI DEL SOROLL (fase B) · PODA (fase C)
# ═════════════════════════════════════════════════════════════════════════════════════════

class LinearZeroEsFixedTest(_BaseSembraTest):
    """A2/A3 — la llei «LINEAR amb delta 0 i sense break ÉS FIXED», als dos costats:
    el filtre de la migració de dades i el helper únic que guarda els camins d'escriptura."""

    PREFIX = 'LZF'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.ss = self._size_system('SS')
        self.rs = GradingRuleSet.objects.create(nom=self._codi('RS'), size_system=self.ss)
        self.talla_base = SizeDefinition.objects.filter(size_system=self.ss).first()

    def _regla(self, codi, **kw):
        return GradingRule.objects.create(
            rule_set=self.rs, pom=self._pom(codi), talla_base=self.talla_base, **kw)

    # ── el filtre de la migració 0042 (la conversió de dades, A2) ─────────────────────
    def test_migracio_selecciona_LINEAR_zero_sense_break(self):
        """El filtre de la migració agafa la degenerada i NO les seves veïnes legítimes."""
        from importlib import import_module
        mig = import_module('fhort.pom.migrations.0042_linear_zero_to_fixed')
        degenerada = self._regla('DEG', logica='LINEAR', increment='0.00', increment_base='0.00')
        # increment_base NULL + increment 0 → també degenerada (fallback legacy d'_apply_rule).
        legacy = self._regla('LEG', logica='LINEAR', increment='0.00', increment_base=None)
        # Delta real → gradua: intocable.
        amb_delta = self._regla('DELTA', logica='LINEAR', increment='2.00', increment_base='2.00')
        # EL BREAK ÉS SAGRAT: delta base 0 però trencament informat → segueix LINEAR.
        amb_break = self._regla('BRK', logica='LINEAR', increment='0.00', increment_base='0.00',
                                increment_break='1.50', talla_break_label='L')
        # Break sense etiqueta però amb valor → també sagrat.
        brk_valor = self._regla('BRKV', logica='LINEAR', increment='0.00', increment_base='0.00',
                                increment_break='0.75')
        # Altres règims no es toquen mai.
        step = self._regla('STP', logica='STEP', increment='0.00', increment_base='0.00')

        ids = set(mig._zero_delta_no_break(GradingRule.objects.all())
                  .values_list('id', flat=True))
        self.assertEqual(ids, {degenerada.id, legacy.id})
        for r in (amb_delta, amb_break, brk_valor, step):
            self.assertNotIn(r.id, ids)

    def test_migracio_converteix_i_deixa_el_break_intacte(self):
        """Aplicar la conversió: la degenerada passa a FIXED; la del break NO es mou."""
        from importlib import import_module
        mig = import_module('fhort.pom.migrations.0042_linear_zero_to_fixed')
        degenerada = self._regla('C_DEG', logica='LINEAR', increment='0.00', increment_base='0.00')
        amb_break = self._regla('C_BRK', logica='LINEAR', increment='0.00', increment_base='0.00',
                                increment_break='1.50', talla_break_label='L')

        mig._zero_delta_no_break(GradingRule.objects.all()).update(logica='FIXED')

        degenerada.refresh_from_db(); amb_break.refresh_from_db()
        self.assertEqual(degenerada.logica, 'FIXED')
        self.assertEqual(amb_break.logica, 'LINEAR')
        # La conversió NO toca cap valor: només l'etiqueta.
        self.assertEqual(float(degenerada.increment_base), 0.0)

    # ── el helper únic del backend (A3) ───────────────────────────────────────────────
    def test_helper_classifica_igual_que_la_migracio(self):
        from fhort.pom.grading_regime import es_linear_degenerada, normalitza_logica
        self.assertTrue(es_linear_degenerada('LINEAR', increment_base=0, increment=0))
        self.assertTrue(es_linear_degenerada('LINEAR', increment_base=None, increment=0))
        self.assertTrue(es_linear_degenerada('LINEAR', increment_base=None, increment=None))
        self.assertFalse(es_linear_degenerada('LINEAR', increment_base=2))
        self.assertFalse(es_linear_degenerada('FIXED', increment_base=0))
        self.assertFalse(es_linear_degenerada('STEP', increment_base=0))
        # El break, per etiqueta o per valor, protegeix la regla.
        self.assertFalse(es_linear_degenerada('LINEAR', increment_base=0, talla_break_label='L'))
        self.assertFalse(es_linear_degenerada('LINEAR', increment_base=0, increment_break=1.5))
        # increment_base poblat MANA sobre el fallback legacy.
        self.assertTrue(es_linear_degenerada('LINEAR', increment_base=0, increment=5))
        self.assertEqual(normalitza_logica('LINEAR', increment_base=0), 'FIXED')
        self.assertEqual(normalitza_logica('LINEAR', increment_base=3), 'LINEAR')
        self.assertEqual(normalitza_logica('STEP', increment_base=0), 'STEP')

    def test_sembra_normalitza_no_rebutja(self):
        """El camí de SEMBRA/IMPORT etiqueta FIXED en lloc de petar (no hi ha ningú a preguntar)."""
        from fhort.models_app.services import materialize_model_grading_rules
        self._regla('S_DEG', logica='LINEAR', increment='0.00', increment_base='0.00')
        self._regla('S_BRK', logica='LINEAR', increment='0.00', increment_base='0.00',
                    increment_break='1.50', talla_break_label='L')
        model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type)

        n = materialize_model_grading_rules(model, self.rs.regles.all(), 'CANONICAL')

        self.assertEqual(n, 2)
        logiques = dict(model.grading_rules.values_list('pom__codi_client', 'logica'))
        self.assertEqual(logiques[self._codi('S_DEG')], 'FIXED')
        self.assertEqual(logiques[self._codi('S_BRK')], 'LINEAR')   # el break és sagrat


class PodaSoftTest(_BaseSembraTest):
    """C1 + B1 — treure un POM del model és SOFT i deixa rastre. Mai un DELETE dur."""

    PREFIX = 'PODA'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.model = self._model(garment_type_item=self.item,
                                 garment_type=self.item.garment_type)
        self.pom = self._pom('P1')
        self.bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=60.0, origen='MANUAL', is_active=True)

    def _desactivar(self, pom_id):
        from fhort.models_app.views import desactivar_pom_view
        req = APIRequestFactory().post(
            f'/api/v1/models/{self.model.id}/pom/{pom_id}/desactivar/', {}, format='json')
        force_authenticate(req, user=self.user)
        return desactivar_pom_view(req, self.model.id, pom_id)

    def test_poda_es_soft_i_la_fila_sobreviu(self):
        resp = self._desactivar(self.pom.id)
        self.assertEqual(resp.status_code, 200)
        self.bm.refresh_from_db()
        self.assertFalse(self.bm.is_active)
        # SOFT: la fila NO s'ha esborrat i el valor es conserva (memòria del model).
        self.assertTrue(BaseMeasurement.objects.filter(pk=self.bm.pk).exists())
        self.assertEqual(self.bm.base_value_cm, 60.0)

    def test_poda_registra_al_measurement_change_log(self):
        """El forat cobert: fins ara una desactivació no deixava cap rastre enlloc."""
        from fhort.models_app.models import MeasurementChangeLog
        abans = MeasurementChangeLog.objects.filter(model=self.model, pom=self.pom).count()
        self._desactivar(self.pom.id)
        entrades = MeasurementChangeLog.objects.filter(model=self.model, pom=self.pom)
        self.assertEqual(entrades.count(), abans + 1)
        log = entrades.order_by('-id').first()
        self.assertEqual(log.valor_anterior, 60.0)
        self.assertIn('poda', log.motiu)

    def test_poda_dun_pom_inexistent_es_404_no_un_ok_enganyos(self):
        altre = self._pom('P2')
        self.assertEqual(self._desactivar(altre.id).status_code, 404)

    def test_poda_repetida_no_torna_a_registrar(self):
        """Ja inactiva → 404: idempotent i sense inflar el log amb sorollositat."""
        self.assertEqual(self._desactivar(self.pom.id).status_code, 200)
        self.assertEqual(self._desactivar(self.pom.id).status_code, 404)

    def test_altres_toggles_dis_active_no_generen_log(self):
        """La promesa del signal es manté: només registra qui posa la marca `_desactivat`."""
        from fhort.models_app.models import MeasurementChangeLog
        abans = MeasurementChangeLog.objects.filter(model=self.model, pom=self.pom).count()
        self.bm.is_active = False
        self.bm.save(update_fields=['is_active'])
        self.assertEqual(
            MeasurementChangeLog.objects.filter(model=self.model, pom=self.pom).count(), abans)


class ImportSorollTest(_BaseSembraTest):
    """B1 + B2 — el PRINCIPI DEL SOROLL a l'import: res s'esborra sol, res sobreviu en silenci.

    Cobreix el pre-flight de `confirmar/`: POMs vius que el document no menciona (proposta →
    confirmació → soft) i files MANUAL amb valor que el document trepitjaria (precedència mínima).
    """

    PREFIX = 'IMPS'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.ss = self._size_system('SS', talles=('S', 'M', 'L'))
        self.model = self._model(
            garment_type_item=self.item, garment_type=self.item.garment_type,
            size_system=self.ss, size_run_model='S·M·L', base_size_label='M')
        # POM que SÍ ve al document.
        self.pom_doc = self._pom('DOC')
        # POM viu al model que el document NO menciona (el soroll).
        self.pom_orfe = self._pom('ORFE')
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_orfe, base_value_cm=42.0,
            origen='ITEM_STANDARD', is_active=True)

    def _sessio(self):
        from fhort.models_app.models import ImportSession
        return ImportSession.objects.create(
            model=self.model, estat='MESURES_OK',
            poms_extrets=[{'actiu': True, 'pom_master_id': self.pom_doc.id,
                           'codi_fitxa': 'DOC', 'descripcio': 'POM del document'}],
            run_conciliat={'talla_mapping': [{'document': 'M', 'model': 'M'}]},
            resultat={'mesures': [{'pom_master_id': self.pom_doc.id,
                                   'talla_label': 'M', 'valor': 60.0}]},
        )

    def _confirmar(self, sessio, body=None):
        from fhort.models_app.extraction_views import import_session_confirmar_view
        req = APIRequestFactory().post(
            f'/api/v1/import-sessions/{sessio.token}/confirmar/', body or {}, format='json')
        force_authenticate(req, user=self.user)
        return import_session_confirmar_view(req, sessio.token)

    # ── B1 · POMs que el document no menciona ────────────────────────────────────────
    def test_poms_no_mencionats_es_PROPOSEN_no_s_apliquen_sols(self):
        resp = self._confirmar(self._sessio())
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['tipus'], 'poms_no_mencionats')
        self.assertEqual(resp.data['n'], 1)
        self.assertEqual(resp.data['poms'][0]['pom_id'], self.pom_orfe.id)
        # RES s'ha tocat: el 409 és un pre-flight, no un fet consumat.
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom_orfe)
        self.assertTrue(bm.is_active)

    def test_poda_confirmada_desactiva_pero_NO_esborra(self):
        resp = self._confirmar(self._sessio(), {'poda_choice': 'desactivar'})
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        self.assertEqual(resp.data['poms_podats'], 1)
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom_orfe)
        self.assertFalse(bm.is_active)
        self.assertEqual(bm.base_value_cm, 42.0)   # el valor es conserva: memòria del model

    def test_poda_confirmada_deixa_rastre_al_log(self):
        from fhort.models_app.models import MeasurementChangeLog
        self._confirmar(self._sessio(), {'poda_choice': 'desactivar'})
        self.assertTrue(MeasurementChangeLog.objects
                        .filter(model=self.model, pom=self.pom_orfe).exists())

    def test_conservar_deixa_la_fila_viva_i_ho_diu(self):
        sessio = self._sessio()
        resp = self._confirmar(sessio, {'poda_choice': 'conservar'})
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        self.assertEqual(resp.data['poms_podats'], 0)
        self.assertEqual(resp.data['poms_conservats'], 1)
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom_orfe)
        self.assertTrue(bm.is_active)
        # La decisió CONSTA: conservar tampoc és silenciós.
        self.assertTrue(any('CONSERVAT' in a for a in resp.data['grading_avisos']))

    def test_sense_orfes_no_hi_ha_gat(self):
        """Un model net no ha de veure mai el modal: el gat només salta si hi ha soroll."""
        BaseMeasurement.objects.filter(model=self.model, pom=self.pom_orfe).delete()
        resp = self._confirmar(self._sessio())
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))

    # ── B2 · precedència mínima: MANUAL protegit ─────────────────────────────────────
    def test_manual_amb_valor_no_es_trepitja_sense_proposar_ho(self):
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_doc, base_value_cm=55.0,
            origen='MANUAL', is_active=True)
        resp = self._confirmar(self._sessio(), {'poda_choice': 'conservar'})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['tipus'], 'manual_trepitjat')
        # La proposta és INFORMADA: mostra els dos valors.
        self.assertEqual(resp.data['poms'][0]['valor_manual'], 55.0)
        self.assertEqual(resp.data['poms'][0]['valor_document'], 60.0)
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom_doc)
        self.assertEqual(bm.base_value_cm, 55.0)   # intacte

    def test_respectar_manual_conserva_el_valor_a_ma(self):
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_doc, base_value_cm=55.0,
            origen='MANUAL', is_active=True)
        resp = self._confirmar(self._sessio(),
                               {'poda_choice': 'conservar', 'manual_choice': 'respectar'})
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        self.assertEqual(resp.data['manual_respectats'], 1)
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom_doc)
        self.assertEqual(bm.base_value_cm, 55.0)
        self.assertEqual(bm.origen, 'MANUAL')

    def test_sobreescriure_deixa_manar_el_document(self):
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_doc, base_value_cm=55.0,
            origen='MANUAL', is_active=True)
        resp = self._confirmar(self._sessio(),
                               {'poda_choice': 'conservar', 'manual_choice': 'sobreescriure'})
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom_doc)
        self.assertEqual(bm.base_value_cm, 60.0)
        self.assertEqual(bm.origen, 'IMPORTED')

    def test_importat_previ_NO_dispara_el_gat_de_manual(self):
        """La protecció és per a MANUAL, no per a tot: un IMPORTED previ es refresca sol."""
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_doc, base_value_cm=55.0,
            origen='IMPORTED', is_active=True)
        resp = self._confirmar(self._sessio(), {'poda_choice': 'conservar'})
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom_doc)
        self.assertEqual(bm.base_value_cm, 60.0)

    # ── B1 · criteri de les files buides ─────────────────────────────────────────────
    def test_fila_buida_de_plantilla_s_esborra_i_la_daltre_origen_es_soft(self):
        pom_tpl = self._pom('TPL')
        pom_man = self._pom('MANBUIT')
        BaseMeasurement.objects.create(model=self.model, pom=pom_tpl,
                                       base_value_cm=None, origen='TEMPLATE', is_active=True)
        BaseMeasurement.objects.create(model=self.model, pom=pom_man,
                                       base_value_cm=None, origen='MANUAL', is_active=True)

        resp = self._confirmar(self._sessio(), {'poda_choice': 'conservar'})
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))

        # Bastida que mai va ser realitat → fora de la BD.
        self.assertFalse(BaseMeasurement.objects.filter(model=self.model, pom=pom_tpl).exists())
        # Creada conscientment → sobreviu inactiva.
        bm_man = BaseMeasurement.objects.get(model=self.model, pom=pom_man)
        self.assertFalse(bm_man.is_active)
        self.assertEqual(resp.data['files_buides_desactivades'], 1)


class GuardDeTallaSembraTest(_BaseSembraTest):
    """P1 — la sembra item→model compara la talla de la PLANTILLA amb la del MODEL.

    Un `ItemBaseMeasurement` està expressat en una talla base. Copiar-lo a un model amb una altra
    talla base produeix una mesura FALSA, i abans de P1 passava en silenci.

    B2 (2026-07-25) — el guard queda REORIENTAT AL SET: la talla de referència és la del BaseSet
    del món del model (item × size_system × fit), no la de l'item pelat. Un item pot vestir-se en
    diversos sistemes i cadascun té la SEVA talla base; llegir-la de l'item era llegir-ne una de
    sola per a tots els mons.
    """

    PREFIX = 'GTAL'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.ss = self._size_system('SS', talles=('S', 'M', 'L'))
        self.pom = self._pom('A')
        GarmentPOMMap.objects.create(garment_type_item=self.item, pom=self.pom, ordre=0)
        self.base_set = self._base_set(self.item, size_system=self.ss, base_size='M')
        ItemBaseMeasurement.objects.create(
            base_set=self.base_set, garment_type_item=self.item, pom=self.pom,
            base_value_cm='60.00', nom_fitxa='A')

    def _talla(self, etiqueta):
        return SizeDefinition.objects.get(size_system=self.ss, etiqueta=etiqueta)

    def _talla_base_del_set(self, etiqueta):
        self.base_set.base_size_definition = self._talla(etiqueta)
        self.base_set.save(update_fields=['base_size_definition'])

    def _model_amb_base(self, etiqueta):
        return self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                           size_system=self.ss, size_run_model='S·M·L', base_size_label=etiqueta)

    def test_talles_divergents_no_sembren_valors_pero_si_pertinenca(self):
        self._talla_base_del_set('M')
        model = self._model_amb_base('L')          # el model parla en L, el set en M

        resp = self._materialitzar(model)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['seeded'], 0)
        self.assertEqual(resp.data['materialized'], 1)      # la PERTINENÇA sí viatja
        self.assertTrue(resp.data['valors_bloquejats_per_talla'])
        self.assertFalse(resp.data['talla_verificada'])
        self.assertIn('DIVERGENTS', resp.data['talla_avis'])
        self.assertEqual(resp.data['talla_item'], 'M')
        self.assertEqual(resp.data['talla_model'], 'L')

        bm = BaseMeasurement.objects.get(model=model, pom=self.pom)
        self.assertEqual(bm.origen, 'TEMPLATE')
        self.assertIsNone(bm.base_value_cm)                 # el VALOR no ha aterrat

    def test_talles_coincidents_sembren_i_ho_declaren(self):
        self._talla_base_del_set('M')
        model = self._model_amb_base('M')

        resp = self._materialitzar(model)

        self.assertEqual(resp.data['seeded'], 1)
        self.assertTrue(resp.data['talla_verificada'])
        self.assertFalse(resp.data['valors_bloquejats_per_talla'])
        self.assertNotIn('talla_avis', resp.data)
        bm = BaseMeasurement.objects.get(model=model, pom=self.pom)
        self.assertEqual(bm.origen, 'ITEM_STANDARD')
        self.assertEqual(bm.base_value_cm, 60.0)

    def test_mon_sense_set_i_item_sense_talla_sembra_pero_avisa(self):
        """CAMÍ LLEGAT: 59/62 items tenen base_size_definition NULL. Bloquejar trencaria el
        catàleg sencer, i per això el guard avisa i deixa passar en comptes d'aturar.

        El model viu en un sistema de talles ALTRE, on l'item no té BaseSet: el resolver no
        troba res, la sembra cau al camí llegat (item inequívoc) i l'item no diu talla base."""
        altre = self._size_system('ALT', talles=('S', 'M', 'L'))
        model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                            size_system=altre, size_run_model='S·M·L', base_size_label='M')

        resp = self._materialitzar(model)

        self.assertEqual(resp.data['seeded'], 1)
        self.assertFalse(resp.data['talla_verificada'])
        self.assertFalse(resp.data['valors_bloquejats_per_talla'])
        self.assertIn('NO VERIFICADA', resp.data['talla_avis'])
        # B2 — el «món sense set» mai és silenciós: porta el context que B4 necessita.
        self.assertEqual(resp.data['base_set_absent']['code'], 'base_set_absent')
        self.assertEqual(resp.data['base_set_absent']['size_system_id'], altre.id)
        self.assertIsNone(resp.data['base_set'])

    def test_el_set_resolt_viatja_a_la_resposta(self):
        """Quan el món SÍ té set, el frontend n'ha de saber la identitat sense tornar a preguntar."""
        self._talla_base_del_set('M')
        model = self._model_amb_base('M')

        resp = self._materialitzar(model)

        self.assertNotIn('base_set_absent', resp.data)
        self.assertEqual(resp.data['base_set']['id'], self.base_set.id)
        self.assertEqual(resp.data['base_set']['size_system'], self.ss.codi)
        self.assertEqual(resp.data['base_set']['base_size_label'], 'M')

    def test_un_altre_system_no_agafa_el_set_del_primer(self):
        """El nucli de la llei: els sets són per MÓN. Dos sets al mateix item no es barregen."""
        altre = self._size_system('ALT2', talles=('S', 'M', 'L'))
        set_altre = self._base_set(self.item, size_system=altre, base_size='S')
        ItemBaseMeasurement.objects.create(
            base_set=set_altre, garment_type_item=self.item, pom=self.pom,
            base_value_cm='42.00', nom_fitxa='A')
        model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                            size_system=altre, size_run_model='S·M·L', base_size_label='S')

        resp = self._materialitzar(model)

        self.assertEqual(resp.data['base_set']['id'], set_altre.id)
        self.assertEqual(resp.data['talla_item'], 'S')
        bm = BaseMeasurement.objects.get(model=model, pom=self.pom)
        self.assertEqual(bm.base_value_cm, 42.0)   # el valor de l'ALTRE món, no el de 60

    def test_model_sense_talla_base_no_rep_valors(self):
        """Si el model no diu en quina talla parla, no es pot afirmar que la plantilla hi encaixi."""
        self._talla_base_del_set('M')
        model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                            size_system=self.ss)

        resp = self._materialitzar(model)

        self.assertEqual(resp.data['seeded'], 0)
        self.assertEqual(resp.data['materialized'], 1)
        self.assertTrue(resp.data['valors_bloquejats_per_talla'])

    def test_la_divergencia_no_trepitja_una_fila_ja_sembrada(self):
        """La sobirania segueix manant: el guard no reobre files que el model ja posseeix."""
        self._talla_base_del_set('M')
        model = self._model_amb_base('M')
        self._materialitzar(model)                       # sembra legítima en M

        self._talla_base_del_set('L')                    # algú canvia la talla base del set
        resp = self._materialitzar(model)

        self.assertEqual(resp.data['seeded'], 0)
        self.assertEqual(resp.data['skipped'], 1)
        bm = BaseMeasurement.objects.get(model=model, pom=self.pom)
        self.assertEqual(bm.base_value_cm, 60.0)          # intacte, no revertit


class PromocioModelItemTest(_BaseSembraTest):
    """B3 — l'acte de promoció model→BaseSet: gate, dry-run, forats, naixement i ampliació.

    LLEI: la sobirania del model és sobre els SEUS valors; l'estàndard del taller és un acte
    separat, explícit i CONFIGURE. B3 hi afegeix el que la llei del BaseSet exigeix:

      · llei 4 — la promoció OMPLE FORATS i prou. Mai modifica un valor que el set ja té.
      · llei 5 — la divergència és vida normal: es llista, no s'escriu, no alerta.
      · llei 6 — ampliar el superset de POMs de l'item només AMB CONFIRMACIÓ.
      · llei 7 — un món sense set és un naixement pendent, no un error sec.
    """

    PREFIX = 'PROM'

    def setUp(self):
        super().setUp()
        from fhort.accounts.models import UserProfile
        # L'usuari base del bastidor no té CONFIGURE (rol per defecte = technician).
        self.user_sense = self.user
        # Usuari amb CONFIGURE per la via d'overrides (no cal inventar un rol).
        self.user_amb = get_user_model().objects.create(username=f'cfg{self.PREFIX}')
        UserProfile.objects.update_or_create(
            user=self.user_amb,
            defaults={'rol_nom': 'technician', 'permisos': {'grant': ['configure']}})
        self.user_amb = get_user_model().objects.get(pk=self.user_amb.pk)

        self.item = self._item()
        self.ss = self._size_system('SS', talles=('S', 'M', 'L'))
        self.rs = GradingRuleSet.objects.create(nom=self._codi('RS'), size_system=self.ss)
        self.item.grading_rule_set = self.rs
        self.item.save(update_fields=['grading_rule_set'])

        self.pom_forat = self._pom('FOR')      # al superset i al model, sense valor al set
        self.pom_divergent = self._pom('DIV')  # als dos, amb valors diferents
        self.pom_igual = self._pom('IGU')      # als dos, amb el mateix valor
        self.pom_sobra = self._pom('SOB')      # al set, no al model
        self.pom_fora = self._pom('FRA')       # al model i FORA del superset de l'item
        for i, pom in enumerate((self.pom_forat, self.pom_divergent, self.pom_igual,
                                 self.pom_sobra)):
            GarmentPOMMap.objects.create(garment_type_item=self.item, pom=pom, ordre=i)

        self.base_set = self._base_set(self.item, size_system=self.ss, base_size='M')
        self.model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                                 size_system=self.ss, size_run_model='S·M·L', base_size_label='M')
        for pom, val in ((self.pom_forat, 30.0), (self.pom_divergent, 40.0),
                         (self.pom_igual, 50.0), (self.pom_fora, 70.0)):
            BaseMeasurement.objects.create(model=self.model, pom=pom, base_value_cm=val,
                                           origen='MANUAL', is_active=True)
        ItemBaseMeasurement.objects.create(base_set=self.base_set, garment_type_item=self.item,
                                           pom=self.pom_divergent, base_value_cm='45.00')
        ItemBaseMeasurement.objects.create(base_set=self.base_set, garment_type_item=self.item,
                                           pom=self.pom_igual, base_value_cm='50.00')
        ItemBaseMeasurement.objects.create(base_set=self.base_set, garment_type_item=self.item,
                                           pom=self.pom_sobra, base_value_cm='99.00')

    def _promoure(self, body=None, user=None, model=None):
        from fhort.models_app.views import promoure_a_item_view
        model = model or self.model
        req = APIRequestFactory().post(f'/api/v1/models/{model.id}/promoure-a-item/',
                                       body or {}, format='json')
        force_authenticate(req, user=user or self.user_amb)
        return promoure_a_item_view(req, model.id)

    def _talla(self, etiqueta):
        return SizeDefinition.objects.get(size_system=self.ss, etiqueta=etiqueta)

    # ── El gate ──────────────────────────────────────────────────────────────────────
    def test_sense_capability_configure_es_403(self):
        """La capa Item exigeix CONFIGURE: aquest endpoint no hereta el gate fluix del model."""
        resp = self._promoure(user=self.user_sense)
        self.assertEqual(resp.status_code, 403)
        # I no ha escrit res de passada.
        self.assertEqual(ItemBaseMeasurement.objects
                         .get(base_set=self.base_set, pom=self.pom_divergent).base_value_cm,
                         Decimal('45.00'))

    # ── Dry-run ──────────────────────────────────────────────────────────────────────
    def test_dry_run_classifica_be_i_NO_escriu(self):
        resp = self._promoure()

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['dry_run'])
        self.assertEqual(resp.data['resum'],
                         {'forats': 2, 'divergents': 1, 'iguals': 1, 'sobrarien': 1,
                          'ampliaria_item': 1})
        self.assertEqual({f['pom_id'] for f in resp.data['forats']},
                         {self.pom_forat.id, self.pom_fora.id})
        divergent = resp.data['divergents'][0]
        # El diff ensenya els DOS valors: sense això la confirmació seria cega.
        self.assertEqual(divergent['valor_item'], 45.0)
        self.assertEqual(divergent['valor_model'], 40.0)
        self.assertEqual(resp.data['sobrarien'][0]['pom_id'], self.pom_sobra.id)
        self.assertEqual(resp.data['base_set']['id'], self.base_set.id)
        self.assertIsNone(resp.data['naixement'])

        # CAP escriptura: ni valors nous, ni ampliació del superset.
        self.assertEqual(ItemBaseMeasurement.objects.filter(base_set=self.base_set).count(), 3)
        self.assertFalse(GarmentPOMMap.objects
                         .filter(garment_type_item=self.item, pom=self.pom_fora).exists())

    # ── Llei 4: NOMÉS forats ─────────────────────────────────────────────────────────
    def test_confirm_omple_forats_i_NO_toca_els_divergents(self):
        """El cor de la llei 4. Abans d'B3 això mateix sobreescrivia amb update_or_create."""
        resp = self._promoure({'confirm': True})

        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertFalse(resp.data['dry_run'])
        self.assertEqual(resp.data['promoguts'], 2)          # els dos forats

        omplert = ItemBaseMeasurement.objects.get(base_set=self.base_set, pom=self.pom_forat)
        self.assertEqual(omplert.base_value_cm, Decimal('30.00'))
        self.assertEqual(omplert.origen, ItemBaseMeasurement.ORIGEN_PROMOTED)
        self.assertEqual(omplert.updated_by_id, self.user_amb.id)     # P9: ja no és anònim

        # EL VALOR DIVERGENT SEGUEIX INTACTE: el model no és autoritat sobre l'estàndard.
        divergent = ItemBaseMeasurement.objects.get(base_set=self.base_set,
                                                    pom=self.pom_divergent)
        self.assertEqual(divergent.base_value_cm, Decimal('45.00'))
        self.assertEqual(divergent.origen, ItemBaseMeasurement.ORIGEN_MANUAL)   # ni re-signat

    def test_una_fila_de_pertinenca_sense_valor_ES_un_forat(self):
        """Omplir una fila buida no modifica res: la llei 4 hi deixa entrar."""
        buida = ItemBaseMeasurement.objects.create(
            base_set=self.base_set, garment_type_item=self.item, pom=self.pom_forat,
            base_value_cm=None)
        resp = self._promoure({'confirm': True})

        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        buida.refresh_from_db()
        self.assertEqual(buida.base_value_cm, Decimal('30.00'))
        self.assertEqual(buida.origen, ItemBaseMeasurement.ORIGEN_PROMOTED)

    def test_els_sobrants_es_llisten_pero_NO_s_esborren(self):
        resp = self._promoure({'confirm': True})
        self.assertEqual(len(resp.data['sobrarien']), 1)
        # Segueix viu: ItemBaseMeasurement no té is_active i un DELETE dur no és una proposta.
        sobrant = ItemBaseMeasurement.objects.get(base_set=self.base_set, pom=self.pom_sobra)
        self.assertEqual(sobrant.base_value_cm, Decimal('99.00'))
        self.assertEqual(sobrant.origen, ItemBaseMeasurement.ORIGEN_MANUAL)   # ni re-signat

    # ── Llei 6: l'ampliació del superset ─────────────────────────────────────────────
    def test_l_ampliacio_del_superset_va_en_seccio_propia_i_només_amb_confirm(self):
        dry = self._promoure()
        self.assertEqual([f['pom_id'] for f in dry.data['ampliaria_item']], [self.pom_fora.id])
        self.assertFalse(GarmentPOMMap.objects
                         .filter(garment_type_item=self.item, pom=self.pom_fora).exists())

        resp = self._promoure({'confirm': True})

        self.assertEqual(resp.data['ampliats'], 1)
        mapa = GarmentPOMMap.objects.get(garment_type_item=self.item, pom=self.pom_fora)
        # pendent_revisio=False: els confirma un tècnic amb gate CONFIGURE, no un clon automàtic.
        self.assertFalse(mapa.pendent_revisio)

    # ── Llei 7: el naixement mandrós ─────────────────────────────────────────────────
    def test_mon_sense_set_proposa_el_naixement_i_NO_el_crea_sol(self):
        altre = self._size_system('NOU', talles=('S', 'M', 'L'))
        model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                            size_system=altre, size_run_model='S·M·L', base_size_label='S')
        BaseMeasurement.objects.create(model=model, pom=self.pom_forat, base_value_cm=31.0,
                                       origen='MANUAL', is_active=True)

        dry = self._promoure(model=model)

        self.assertEqual(dry.status_code, 200, getattr(dry, 'data', None))
        self.assertIsNone(dry.data['base_set'])
        self.assertEqual(dry.data['naixement']['code'], 'base_set_absent')
        self.assertEqual(dry.data['naixement']['size_system_id'], altre.id)
        self.assertEqual(dry.data['naixement']['origen'], ItemBaseSet.ORIGEN_PROMOCIO)
        # El backend MAI crea el set sol.
        self.assertFalse(ItemBaseSet.objects.filter(size_system=altre).exists())

    def test_el_confirm_fa_neixer_el_set_amb_origen_promocio(self):
        altre = self._size_system('NOU2', talles=('S', 'M', 'L'))
        model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                            size_system=altre, size_run_model='S·M·L', base_size_label='S')
        BaseMeasurement.objects.create(model=model, pom=self.pom_forat, base_value_cm=31.0,
                                       origen='MANUAL', is_active=True)

        resp = self._promoure({'confirm': True}, model=model)

        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertTrue(resp.data['base_set_creat'])
        nou_set = ItemBaseSet.objects.get(garment_type_item=self.item, size_system=altre)
        self.assertEqual(nou_set.origen, ItemBaseSet.ORIGEN_PROMOCIO)
        self.assertEqual(nou_set.base_size_definition.etiqueta, 'S')   # convenció: la més petita
        self.assertEqual(nou_set.updated_by_id, self.user_amb.id)
        # I el set del PRIMER món no s'ha tocat gens.
        self.assertEqual(ItemBaseMeasurement.objects.filter(base_set=self.base_set).count(), 3)

    def test_la_convencio_montse_suggereix_M_en_home_i_S_en_dona(self):
        """Llei 2: la més petita, EXCEPTE adults (HOME M/42, DONA S/38)."""
        from fhort.pom.models import suggerir_talla_base
        ss = self._size_system('CONV', talles=('XS', 'S', 'M', 'L'))
        self.assertEqual(suggerir_talla_base(ss, 'MAN').etiqueta, 'M')
        self.assertEqual(suggerir_talla_base(ss, 'WOMAN').etiqueta, 'S')
        self.assertEqual(suggerir_talla_base(ss, 'KID_BOY').etiqueta, 'XS')   # la més petita
        self.assertEqual(suggerir_talla_base(ss, None).etiqueta, 'XS')

    def test_la_talla_base_del_naixement_es_pot_triar_pero_ha_de_ser_del_sistema(self):
        altre = self._size_system('NOU3', talles=('S', 'M', 'L'))
        model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                            size_system=altre, size_run_model='S·M·L', base_size_label='L')
        BaseMeasurement.objects.create(model=model, pom=self.pom_forat, base_value_cm=31.0,
                                       origen='MANUAL', is_active=True)
        forastera = self._talla('M')          # del sistema self.ss, no del d'aquest model

        rebutjat = self._promoure({'confirm': True, 'base_size_definition': forastera.id},
                                  model=model)
        self.assertEqual(rebutjat.status_code, 422)
        self.assertEqual(rebutjat.data['tipus'], 'talla_base_fora_del_sistema')

        bona = SizeDefinition.objects.get(size_system=altre, etiqueta='L')
        ok = self._promoure({'confirm': True, 'base_size_definition': bona.id}, model=model)
        self.assertEqual(ok.status_code, 200, getattr(ok, 'data', None))
        self.assertEqual(ItemBaseSet.objects.get(garment_type_item=self.item, size_system=altre)
                         .base_size_definition_id, bona.id)

    def test_talles_divergents_no_escriuen_cap_valor(self):
        """Un valor del model en una talla que no és la del set és una mesura falsa."""
        self.model.base_size_label = 'L'
        self.model.save(update_fields=['base_size_label'])

        resp = self._promoure({'confirm': True})

        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertTrue(resp.data['talla_divergent'])
        self.assertEqual(resp.data['promoguts'], 0)
        self.assertFalse(ItemBaseMeasurement.objects
                         .filter(base_set=self.base_set, pom=self.pom_forat).exists())

    # ── Les portes d'entrada ─────────────────────────────────────────────────────────
    def test_model_sense_talla_base_no_promou(self):
        self.model.base_size_label = ''
        self.model.save(update_fields=['base_size_label'])
        resp = self._promoure({'confirm': True})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.data['tipus'], 'model_sense_talla_base')

    def test_model_sense_size_system_no_promou(self):
        """Sense món no hi ha BaseSet on promoure."""
        self.model.size_system = None
        self.model.save(update_fields=['size_system'])
        resp = self._promoure({'confirm': True})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.data['tipus'], 'model_sense_size_system')

    def test_nomes_promou_mesures_vives_i_amb_valor(self):
        """No s'ascendeix el que no és realitat: files podades o buides no són patrimoni."""
        BaseMeasurement.objects.filter(model=self.model, pom=self.pom_forat).update(is_active=False)
        BaseMeasurement.objects.create(model=self.model, pom=self.pom_sobra,
                                       base_value_cm=None, origen='TEMPLATE', is_active=True)
        resp = self._promoure()
        ids = {f['pom_id'] for f in
               resp.data['forats'] + resp.data['divergents'] + resp.data['iguals']}
        self.assertNotIn(self.pom_forat.id, ids)    # desactivada
        self.assertNotIn(self.pom_sobra.id, ids)    # sense valor

    def test_model_sense_item_no_te_plantilla_on_promoure(self):
        model = self._model(base_size_label='M')
        from fhort.models_app.views import promoure_a_item_view
        req = APIRequestFactory().post(f'/api/v1/models/{model.id}/promoure-a-item/', {},
                                       format='json')
        force_authenticate(req, user=self.user_amb)
        self.assertEqual(promoure_a_item_view(req, model.id).status_code, 400)


class ActeCanonicBaseSetTest(_BaseSembraTest):
    """B3 — l'acte canònic: modificar un valor que el set JA té.

    La llei 4 el treu de la promoció a posta. Aquests tests defensen que és una porta pròpia,
    signada i amb confirmació — i que NO serveix per omplir forats (per això hi ha la promoció).
    """

    PREFIX = 'CANO'

    def setUp(self):
        super().setUp()
        from fhort.accounts.models import UserProfile
        self.user_sense = self.user
        self.user_amb = get_user_model().objects.create(username=f'cfg{self.PREFIX}')
        UserProfile.objects.update_or_create(
            user=self.user_amb,
            defaults={'rol_nom': 'technician', 'permisos': {'grant': ['configure']}})
        self.user_amb = get_user_model().objects.get(pk=self.user_amb.pk)

        self.item = self._item()
        self.ss = self._size_system('SS', talles=('S', 'M', 'L'))
        self.base_set = self._base_set(self.item, size_system=self.ss, base_size='M')
        self.pom_amb = self._pom('AMB')
        self.pom_buit = self._pom('BUI')
        self.ibm = ItemBaseMeasurement.objects.create(
            base_set=self.base_set, garment_type_item=self.item, pom=self.pom_amb,
            base_value_cm='45.00', origen=ItemBaseMeasurement.ORIGEN_PROMOTED)
        ItemBaseMeasurement.objects.create(
            base_set=self.base_set, garment_type_item=self.item, pom=self.pom_buit,
            base_value_cm=None)

    def _acte(self, body, user=None, base_set_id=None):
        from fhort.models_app.views import acte_canonic_base_set_view
        bs = base_set_id or self.base_set.id
        req = APIRequestFactory().post(f'/api/v1/item-base-sets/{bs}/acte-canonic/',
                                       body, format='json')
        force_authenticate(req, user=user or self.user_amb)
        return acte_canonic_base_set_view(req, bs)

    def test_sense_capability_configure_es_403(self):
        resp = self._acte({'pom': self.pom_amb.id, 'base_value_cm': '50.00', 'confirm': True},
                          user=self.user_sense)
        self.assertEqual(resp.status_code, 403)
        self.ibm.refresh_from_db()
        self.assertEqual(self.ibm.base_value_cm, Decimal('45.00'))

    def test_dry_run_ensenya_l_anterior_i_el_nou_i_NO_escriu(self):
        resp = self._acte({'pom': self.pom_amb.id, 'base_value_cm': '50.00'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['dry_run'])
        self.assertEqual(resp.data['valor_anterior'], 45.0)
        self.assertEqual(resp.data['valor_nou'], 50.0)
        self.assertEqual(resp.data['talla_base'], 'M')
        self.ibm.refresh_from_db()
        self.assertEqual(self.ibm.base_value_cm, Decimal('45.00'))

    def test_confirm_escriu_i_signa(self):
        resp = self._acte({'pom': self.pom_amb.id, 'base_value_cm': '50.00', 'confirm': True})
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.ibm.refresh_from_db()
        self.assertEqual(self.ibm.base_value_cm, Decimal('50.00'))
        # L'acte canònic és mà humana: la provinença ho diu, no es queda a PROMOTED.
        self.assertEqual(self.ibm.origen, ItemBaseMeasurement.ORIGEN_MANUAL)
        self.assertEqual(self.ibm.updated_by_id, self.user_amb.id)

    def test_un_forat_NO_es_acte_canonic(self):
        """Omplir un buit és promoció, no acte canònic. Si compartissin porta, la llei 4 seria
        una recomanació en comptes d'una invariant."""
        resp = self._acte({'pom': self.pom_buit.id, 'base_value_cm': '50.00', 'confirm': True})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.data['tipus'], 'no_hi_ha_valor_a_substituir')

    def test_valor_no_numeric_es_400(self):
        resp = self._acte({'pom': self.pom_amb.id, 'base_value_cm': 'ample', 'confirm': True})
        self.assertEqual(resp.status_code, 400)


class ItemBaseMeasurementBasicsTest(_BaseSembraTest):
    """P9/P10 — la taula de plantilla no tenia CAP test. Unicitat i provinença per camí."""

    PREFIX = 'IBMB'

    def setUp(self):
        super().setUp()
        from fhort.accounts.models import UserProfile
        self.item = self._item()
        self.pom = self._pom('P1')
        # B1 — un valor base no pot existir fora d'un món. L'item en té UN, així que l'upsert
        # el dedueix sol i els callers d'avui (columna ASSIGN del POMBrowser) no canvien.
        self.base_set = self._base_set(self.item)
        self.user_amb = get_user_model().objects.create(username=f'cfg{self.PREFIX}')
        UserProfile.objects.update_or_create(
            user=self.user_amb,
            defaults={'rol_nom': 'technician', 'permisos': {'grant': ['configure']}})
        self.user_amb = get_user_model().objects.get(pk=self.user_amb.pk)

    def _upsert(self, body, user=None):
        from fhort.pom.views import ItemBaseMeasurementViewSet
        req = APIRequestFactory().post('/api/v1/item-base-measurements/upsert/', body,
                                       format='json')
        force_authenticate(req, user=user or self.user_amb)
        return ItemBaseMeasurementViewSet.as_view({'post': 'upsert'})(req)

    def test_upsert_crea_amb_origen_manual_i_autoria(self):
        resp = self._upsert({'garment_type_item': self.item.id, 'pom': self.pom.id,
                             'base_value_cm': '60.00'})
        self.assertEqual(resp.status_code, 201)
        ibm = ItemBaseMeasurement.objects.get(garment_type_item=self.item, pom=self.pom)
        self.assertEqual(ibm.origen, ItemBaseMeasurement.ORIGEN_MANUAL)
        self.assertEqual(ibm.updated_by_id, self.user_amb.id)
        self.assertIsNotNone(ibm.created_at)

    def test_upsert_es_idempotent_per_base_set_pom(self):
        """La clau és (base_set, pom): el segon upsert actualitza, no duplica."""
        self._upsert({'garment_type_item': self.item.id, 'pom': self.pom.id,
                      'base_value_cm': '60.00'})
        resp = self._upsert({'garment_type_item': self.item.id, 'pom': self.pom.id,
                             'base_value_cm': '61.00'})
        self.assertEqual(resp.status_code, 200)          # update, no create
        self.assertEqual(ItemBaseMeasurement.objects
                         .filter(garment_type_item=self.item, pom=self.pom).count(), 1)
        self.assertEqual(ItemBaseMeasurement.objects
                         .get(garment_type_item=self.item, pom=self.pom).base_value_cm,
                         Decimal('61.00'))

    def test_origen_NO_s_accepta_del_body(self):
        """Si `origen` fos escrivible, qualsevol client podria signar un valor com a promogut."""
        self._upsert({'garment_type_item': self.item.id, 'pom': self.pom.id,
                      'base_value_cm': '60.00', 'origen': 'PROMOTED'})
        self.assertEqual(ItemBaseMeasurement.objects
                         .get(garment_type_item=self.item, pom=self.pom).origen,
                         ItemBaseMeasurement.ORIGEN_MANUAL)

    def test_upsert_sense_cap_set_es_400_amb_codi(self):
        """Un valor base fora d'un món no existeix: es refusa amb senyal, no amb error sec."""
        altre = self._item(code='altre')
        resp = self._upsert({'garment_type_item': altre.id, 'pom': self.pom.id,
                             'base_value_cm': '60.00'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'base_set_absent')

    def test_upsert_amb_dos_sets_exigeix_dir_quin(self):
        """Amb 2+ mons, endevinar-ne un seria escriure el valor a la peça equivocada."""
        segon = self._base_set(self.item, size_system=self._size_system('BS2'))
        resp = self._upsert({'garment_type_item': self.item.id, 'pom': self.pom.id,
                             'base_value_cm': '60.00'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'base_set_ambigu')
        self.assertEqual(len(resp.data['base_sets']), 2)

        ok = self._upsert({'garment_type_item': self.item.id, 'pom': self.pom.id,
                           'base_set': segon.id, 'base_value_cm': '60.00'})
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ItemBaseMeasurement.objects.get(base_set=segon, pom=self.pom)
                         .base_value_cm, Decimal('60.00'))

    def test_el_mateix_pom_pot_viure_a_dos_mons_amb_valors_diferents(self):
        """El nucli de la llei: l'item no es parteix, i cada món té el seu valor del mateix POM."""
        segon = self._base_set(self.item, size_system=self._size_system('BS3'))
        self._upsert({'garment_type_item': self.item.id, 'pom': self.pom.id,
                      'base_set': self.base_set.id, 'base_value_cm': '60.00'})
        self._upsert({'garment_type_item': self.item.id, 'pom': self.pom.id,
                      'base_set': segon.id, 'base_value_cm': '42.00'})
        self.assertEqual(ItemBaseMeasurement.objects.filter(pom=self.pom).count(), 2)
        self.assertEqual(ItemBaseMeasurement.objects.get(base_set=self.base_set, pom=self.pom)
                         .base_value_cm, Decimal('60.00'))
        self.assertEqual(ItemBaseMeasurement.objects.get(base_set=segon, pom=self.pom)
                         .base_value_cm, Decimal('42.00'))

    def test_upsert_sense_capability_es_403(self):
        resp = self._upsert({'garment_type_item': self.item.id, 'pom': self.pom.id,
                             'base_value_cm': '60.00'}, user=self.user)
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(ItemBaseMeasurement.objects.filter(garment_type_item=self.item).exists())

    def test_reescriure_manual_sobre_un_promogut_el_torna_a_signar(self):
        """La provinença diu com hi ha arribat el valor VIGENT, no com hi va arribar el primer."""
        ItemBaseMeasurement.objects.create(
            base_set=self.base_set, garment_type_item=self.item, pom=self.pom,
            base_value_cm='60.00', origen=ItemBaseMeasurement.ORIGEN_PROMOTED)
        self._upsert({'garment_type_item': self.item.id, 'pom': self.pom.id,
                      'base_value_cm': '62.00'})
        ibm = ItemBaseMeasurement.objects.get(garment_type_item=self.item, pom=self.pom)
        self.assertEqual(ibm.origen, ItemBaseMeasurement.ORIGEN_MANUAL)
        self.assertEqual(ibm.updated_by_id, self.user_amb.id)


class EsborratResidentsD314Test(_BaseSembraTest):
    """D-31.4 — assignar un ruleset esborra les regles residents del model, i fins avui ho feia
    SENSE MIRAR L'ORIGEN I SENSE AVISAR.

    El radi no és teòric: mesurat contra el dump de PROD del 04/08 hi ha **35 models amb 1.444
    regles residents** (660 MANUAL en 25 models · 523 CLIENT_RUN · 241 CANONICAL · 20 IMPORTED).
    El camí és `update_model_step2` → `materialize_model_grading_rules`, que fa
    wipe-and-recreate (`services.py:266`).

    Per què AVÍS i no bloqueig: migrar un model al catàleg del client és un flux legítim i
    volgut (és el que farà la migració a BRW-CATALEG-v2). El que no és legítim és fer-ho sense
    saber què es perd.
    """

    PREFIX = 'RES'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.pom = self._pom('A')
        GarmentPOMMap.objects.create(garment_type_item=self.item, pom=self.pom, ordre=0)
        self.ss = self._size_system('SS_RES')
        self.client_a = Customer.objects.create(codi=f'{self.PREFIX[:2]}A', nom='Client A')
        self.model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                                 size_system=self.ss, size_run_model='S·M·L',
                                 base_size_label='M', customer=self.client_a)
        self.rs = GradingRuleSet.objects.create(nom=self._codi('CATALEG'), size_system=self.ss,
                                                customer=self.client_a)
        GradingRule.objects.create(
            rule_set=self.rs, pom=self.pom, talla_base=self.ss.talles.get(etiqueta='M'),
            logica=GradingRule.LOGICA_LINEAR, increment='1.00', actiu=True)

    def _resident(self, origen, pom=None):
        return ModelGradingRule.objects.create(
            model=self.model, pom=(pom or self._pom(f'R{origen[:3]}')),
            logica=GradingRule.LOGICA_LINEAR, increment='2.00', origen=origen, actiu=True)

    def _watchpoints(self):
        from fhort.models_app.models import Watchpoint
        return Watchpoint.objects.filter(model=self.model)

    # ── B1 · l'avís ───────────────────────────────────────────────────────────

    def test_amb_residents_i_sense_flag_avisa_i_no_esborra_res(self):
        # M1 (07/08) — aquest model no té cap joc, o sigui que la seva MANUAL és autoria i es
        # PRESERVA. El permís, doncs, ja no la pot comptar: es demana pel que cau de debò (la
        # IMPORTED), que és la llei F1-bis. Abans de M1 aquí s'esperaven 2 i {MANUAL:1, IMPORTED:1}.
        self._resident('MANUAL')
        self._resident('IMPORTED')

        resp = self._step2(self.model, {'grading_rule_set_id': self.rs.id})

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['tipus'], 'esborrat_residents')
        self.assertEqual(resp.data['codi'], 'GRADING_RESIDENTS_WIPE')
        self.assertEqual(resp.data['residents'], 1)
        self.assertEqual(resp.data['per_origen'], {'IMPORTED': 1})
        self.assertEqual(resp.data['preservades'], 1)
        # RES ESBORRAT, i el ruleset TAMPOC assignat: un avís que ja hagués desat a mitges
        # seria pitjor que no avisar.
        self.assertEqual(ModelGradingRule.objects.filter(model=self.model).count(), 2)
        self.model.refresh_from_db()
        self.assertIsNone(self.model.grading_rule_set_id)
        self.assertFalse(self._watchpoints().exists())

    def test_l_avis_distingeix_les_IMPORTED_a_primer_nivell(self):
        """🔴 La llei del brief: perdre una regla escrita a mà no és el mateix que perdre'n una
        que ve del document del client i es pot tornar a importar. Va a una clau pròpia i no
        només dins de `per_origen` perquè no es pugui passar per alt llegint de pressa."""
        self._resident('MANUAL')
        self._resident('IMPORTED')
        self._resident('IMPORTED', pom=self._pom('RIMP2'))

        resp = self._step2(self.model, {'grading_rule_set_id': self.rs.id})

        self.assertEqual(resp.data['imported'], 2)
        self.assertIn('IMPORTED', resp.data['message'])
        # M1 — de les 3 residents només en cauen 2: la MANUAL d'un model sense joc és autoria i
        # es conserva. El que s'ensenya és el que cau (abans: 3), i que la salvada es diu.
        self.assertEqual(resp.data['residents'], 2)
        self.assertEqual(resp.data['preservades'], 1)
        self.assertIn('es conserven', resp.data['message'])

    def test_els_dos_flags_no_es_presten_el_consentiment(self):
        """El motiu de tenir-ne dos i no un: confirmar que fas servir el grading d'un altre
        client no pot autoritzar que se t'esborrin les regles pròpies. Amb un sol flag, un
        consentiment n'arrossegaria l'altre EN SILENCI — el defecte que D-31.4 tanca."""
        # M1 — la resident ha de ser una que CAIGUI de debò, si no el que es prova aquí
        # desapareix: la MANUAL d'un model sense joc ara es preserva, no hi hauria res a
        # destruir i per tant tampoc cap segon consentiment a demanar (F1-bis). El subjecte del
        # test és la SEPARACIÓ DELS DOS FLAGS, i amb una IMPORTED es prova igual de bé.
        self._resident('IMPORTED')

        resp = self._step2(self.model, {'grading_rule_set_id': self.rs.id,
                                        'confirmar_altre_client': True})

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['tipus'], 'esborrat_residents')
        self.assertEqual(ModelGradingRule.objects.filter(model=self.model).count(), 1)

    # ── B2 · el rastre ────────────────────────────────────────────────────────

    def test_amb_flag_esborra_i_deixa_watchpoint_obert(self):
        manual = self._resident('MANUAL')
        self._resident('IMPORTED')

        resp = self._step2(self.model, {'grading_rule_set_id': self.rs.id,
                                        'confirmar_esborrat_residents': True})

        self.assertEqual(resp.status_code, 200)
        # M1 — cau la IMPORTED; la MANUAL d'un model sense joc és autoria i es queda.
        self.assertEqual(resp.data['residents_esborrades'], 1)
        self.assertEqual(resp.data['residents_preservades'], 1)
        self.model.refresh_from_db()
        self.assertEqual(self.model.grading_rule_set_id, self.rs.id)
        # Wipe-and-recreate: hi ha la del ruleset i la MANUAL salvada; la IMPORTED ha caigut.
        residents = ModelGradingRule.objects.filter(model=self.model)
        self.assertEqual(sorted(r.pom_id for r in residents),
                         sorted([self.pom.id, manual.pom_id]))

        wp = self._watchpoints().get()
        self.assertEqual(wp.estat, 'open')
        self.assertEqual(wp.created_by_id, self.user.profile.id)
        # `residents` segueix essent l'acta d'ABANS (les que hi havia); el que n'ha passat va a
        # `esborrades`/`preservades`. Aquesta distinció és de 6.1 i M1 no la toca.
        self.assertEqual(wp.dades['residents'], 2)
        self.assertEqual(wp.dades['esborrades'], 1)
        self.assertEqual(wp.dades['preservades'], 1)
        self.assertEqual(wp.dades['imported'], 1)
        self.assertEqual(wp.dades['per_origen'], {'MANUAL': 1, 'IMPORTED': 1})
        self.assertEqual(wp.dades['grading_rule_set_id'], self.rs.id)
        # El text diu el que s'ha ESBORRAT (1), i que la MANUAL s'ha conservat.
        self.assertIn('esborrant 1 regles pròpies', wp.text)
        self.assertIn("1 escrites a mà (MANUAL) s'han conservat", wp.text)
        # 🚩 NO s'afirma res sobre el desglossament entre parèntesis: avui hi surt el recompte
        # d'ABANS («1 IMPORTED · 1 MANUAL») al costat d'un «esborrant 1», o sigui que hi llista
        # una regla que NO ha caigut. És un llegat de 6.1 (el 409 sí que la resta, `views.py`
        # :671-676; el Watchpoint no) que M1 fa molt més visible perquè ara la preservació és el
        # cas normal. ANOTAT al report M-FI §M1; no es toca aquí perquè l'abast és tancat.

    def test_el_rastre_conta_les_d_ABANS_no_les_de_despres(self):
        """El recompte es pren abans del `save()`: si es prengués després, el wipe ja hauria
        passat i el watchpoint diria «0 regles esborrades» — un rastre que menteix és pitjor
        que cap rastre."""
        for o in ('MANUAL', 'MANUAL', 'CANONICAL'):
            self._resident(o, pom=self._pom(f'RX{o}{self._seq}'))

        self._step2(self.model, {'grading_rule_set_id': self.rs.id,
                                 'confirmar_esborrat_residents': True})

        self.assertEqual(self._watchpoints().get().dades['residents'], 3)

    # ── B3 · cap fricció on no toca ───────────────────────────────────────────

    def test_sense_residents_no_hi_ha_cap_friccio(self):
        """Un model que no perd res no ha de veure cap diàleg: l'avís ha d'aparèixer quan hi
        ha alguna cosa a perdre, o s'acabarà clicant sense llegir."""
        resp = self._step2(self.model, {'grading_rule_set_id': self.rs.id})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['residents_esborrades'], 0)
        self.assertFalse(self._watchpoints().exists())

    def test_el_cami_de_creacio_no_activa_mai_l_avis(self):
        """`create_model_wizard` crida el mateix validador sense `model`: un model que encara
        no existeix no pot tenir regles residents, i el cas no s'hi ha d'activar mai."""
        from fhort.models_app.views import _validar_ruleset_assignable
        self._resident('MANUAL')   # residents d'UN ALTRE model, que no hi pinten res

        self.assertIsNone(_validar_ruleset_assignable(
            self.rs, size_system_id=self.ss.id, customer_id=self.client_a.id))


class PermisIDestruccioMirenElMateixTest(_BaseSembraTest):
    """F1-bis (06/08) — D-31.4 demanava permís mirant una cosa i el codi en destruïa una altra.

    ── EL DEFECTE ─────────────────────────────────────────────────────────────────────────
    Dos predicats per al mateix acte:
      · el 409 que demana permís mirava el PAYLOAD          → `d.get('grading_rule_set_id')`
      · el wipe-and-recreate que destrueix mirava el MODEL  → `model.grading_rule_set_id`
    El destructiu era el més AMPLE. Conseqüència viva: QUALSEVOL `update-step2` sobre un model
    amb joc assignat —canviar la talla base, la construcció, el run: coses que no parlen de
    graduació— reescrivia totes les residents i es menjava les `origen='MANUAL'` sense 409,
    sense Watchpoint i sense que la resposta ho digués. El camí mut més fàcil d'encertar:
    editar el model al wizard fins que el joc hidratat deixi de casar (`ModelWizard.jsx:405`
    posa `gradingRuleSetId=null` → `skeletonPayload` ja no envia la clau) i desar.

    ── LA LLEI ────────────────────────────────────────────────────────────────────────────
    PERMÍS I DESTRUCCIÓ MIREN EL MATEIX. Un sol predicat, `canvia_joc`: la clau entra al
    payload **i** el valor és un altre. Si no canvia, no es toca cap regla. I les DUES portes
    destructives —canviar de joc i desacoblar-lo («Sense graduació»)— demanen el mateix permís
    i deixen el mateix rastre: desacoblar no pot sortir més barat que canviar.

    El motor de materialització NO es toca; només QUAN es crida.
    """

    PREFIX = 'F1B'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.pom = self._pom('A')
        GarmentPOMMap.objects.create(garment_type_item=self.item, pom=self.pom, ordre=0)
        self.ss = self._size_system('SS_F1B')
        self.cli = Customer.objects.create(codi='F1A', nom='Client F1-bis')
        self.model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                                 size_system=self.ss, size_run_model='S·M·L',
                                 base_size_label='M', customer=self.cli)
        self.joc_a = self._joc('JOC_A')
        self.joc_b = self._joc('JOC_B')
        # ESTAT DE PARTIDA: el model ja té el joc A (i, per tant, les seves residents).
        self.assertEqual(
            self._step2(self.model, {'grading_rule_set_id': self.joc_a.id}).status_code, 200)
        self.model.refresh_from_db()

    def _joc(self, nom):
        # `origen=CLIENT_RUN` EXPLÍCIT i no per defecte: un ruleset sense origen classificat
        # materialitza les seves residents com a 'MANUAL' (`origen_mgr_des_de_ruleset`), i
        # llavors «el que ve del joc» i «el que ha escrit el tècnic» es dirien igual —
        # justament la distinció que aquests tests han de poder fer.
        rs = GradingRuleSet.objects.create(nom=self._codi(nom), size_system=self.ss,
                                           customer=self.cli,
                                           origen=GradingRuleSet.ORIGEN_CLIENT_RUN)
        GradingRule.objects.create(
            rule_set=rs, pom=self.pom, talla_base=self.ss.talles.get(etiqueta='M'),
            logica=GradingRule.LOGICA_LINEAR, increment='1.00', actiu=True)
        return rs

    def _manual(self, codi):
        """Una regla escrita A MÀ pel tècnic — el que la pantalla nova de Graduació crea."""
        return ModelGradingRule.objects.create(
            model=self.model, pom=self._pom(codi),
            logica=GradingRule.LOGICA_LINEAR, increment='2.00', origen='MANUAL', actiu=True)

    def _regles(self):
        return ModelGradingRule.objects.filter(model=self.model)

    def _watchpoints(self):
        from fhort.models_app.models import Watchpoint
        return Watchpoint.objects.filter(model=self.model)

    # ── (a) el cas que mossegava ──────────────────────────────────────────────

    def test_un_patch_que_no_parla_de_graduacio_no_toca_cap_regla(self):
        """🔴 EL CAS. Un PATCH sense `grading_rule_set_id` sobre un model amb joc."""
        self._manual('MAN1')
        self._manual('MAN2')
        ids_abans = sorted(r.id for r in self._regles())

        resp = self._step2(self.model, {'size_run': 'S·M', 'base_size': 'M'})

        self.assertEqual(resp.status_code, 200)
        # Ni una regla tocada: els MATEIXOS ids, no només el mateix recompte —un
        # wipe-and-recreate deixaria el mateix nombre de files amb ids nous.
        self.assertEqual(sorted(r.id for r in self._regles()), ids_abans)
        self.assertEqual(self._regles().filter(origen='MANUAL').count(), 2)
        self.assertIsNone(resp.data['regles_materialitzades'])
        self.assertFalse(self._watchpoints().exists())
        # I el PATCH sí que ha fet la seva feina.
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'S·M')
        self.assertEqual(self.model.grading_rule_set_id, self.joc_a.id)

    # ── (b) i (c) · canviar de joc segueix demanant permís i deixant rastre ───

    def test_canviar_de_joc_amb_MANUAL_vives_avisa_amb_recompte(self):
        """⚠️ ACTUALITZAT PER 6.1 (06/08 nit). El joc A està CLASSIFICAT (`CLIENT_RUN`), i per
        tant la `MAN1` és autoria de debò: sobreviurà al canvi. El 409 segueix existint —cau la
        resident que ve del joc A— però ja NO diu que s'endurà la MANUAL, perquè no se l'endú.
        El permís i la destrucció miren el mateix, i això val en els dos sentits."""
        self._manual('MAN1')

        resp = self._step2(self.model, {'grading_rule_set_id': self.joc_b.id})

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['tipus'], 'esborrat_residents')
        self.assertEqual(resp.data['residents'], 1)          # NOMÉS la del joc A
        self.assertEqual(resp.data['preservades'], 1)        # la MANUAL es queda
        self.assertIsNone(resp.data['per_origen'].get('MANUAL'))
        self.assertIn('MANUAL', resp.data['message'])
        self.assertEqual(self._regles().filter(origen='MANUAL').count(), 1)
        self.model.refresh_from_db()
        self.assertEqual(self.model.grading_rule_set_id, self.joc_a.id)

    def test_canvi_de_joc_confirmat_esborra_i_deixa_watchpoint(self):
        """⚠️ ACTUALITZAT PER 6.1: la `MANUAL` d'autoria SOBREVIU al canvi de joc, i el rastre
        diu el que ha passat de debò (1 esborrada, 1 preservada), no el que hauria passat abans."""
        self._manual('MAN1')
        manual_pom_id = self._regles().get(origen='MANUAL').pom_id

        resp = self._step2(self.model, {'grading_rule_set_id': self.joc_b.id,
                                        'confirmar_esborrat_residents': True})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['residents_esborrades'], 1)
        self.assertEqual(resp.data['residents_preservades'], 1)
        self.model.refresh_from_db()
        self.assertEqual(self.model.grading_rule_set_id, self.joc_b.id)
        # La del joc A ha caigut i la del joc B ocupa el seu POM; la MANUAL segueix viva.
        self.assertEqual(sorted(r.pom_id for r in self._regles()),
                         sorted([self.pom.id, manual_pom_id]))
        self.assertEqual(self._regles().get(pom_id=manual_pom_id).origen, 'MANUAL')
        wp = self._watchpoints().get()
        self.assertEqual(wp.dades['tipus'], 'esborrat_residents')
        self.assertEqual(wp.dades['residents'], 2)      # les que HI HAVIA
        self.assertEqual(wp.dades['esborrades'], 1)     # les que han caigut
        self.assertEqual(wp.dades['preservades'], 1)    # les que s'han salvat

    # ── (d) reenviar el mateix joc és un NO-OP ────────────────────────────────

    def test_reenviar_el_mateix_joc_no_toca_res_ni_rebota(self):
        """Desar dues vegades seguides la mateixa pantalla no és canviar de joc. Abans
        d'aquest fix rebotava amb 409 o —confirmat— destruïa les MANUAL sense motiu."""
        self._manual('MAN1')
        ids_abans = sorted(r.id for r in self._regles())

        resp = self._step2(self.model, {'grading_rule_set_id': self.joc_a.id})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(sorted(r.id for r in self._regles()), ids_abans)
        self.assertIsNone(resp.data['regles_materialitzades'])
        self.assertEqual(resp.data['residents_esborrades'], 0)
        self.assertFalse(self._watchpoints().exists())

    # ── la SEGONA porta · «Sense graduació» (Agus, 06/08 vespre) ──────────────

    def test_desacoblar_amb_residents_demana_permis(self):
        """«Sense graduació» diu que desacobla el JOC; no diu que s'endugui les regles escrites
        a mà. Com que les mata, ha de demanar permís amb el recompte davant."""
        self._manual('MAN1')

        resp = self._step2(self.model, {'grading_rule_set_id': None})

        self.assertEqual(resp.status_code, 409)
        # MATEIX `tipus` que l'altra porta a posta: el fet és el mateix i el front ja el sap
        # gestionar (`useConfirmacioRuleset.FLAG_PER_TIPUS`). La causa viu al `message`.
        self.assertEqual(resp.data['tipus'], 'esborrat_residents')
        self.assertEqual(resp.data['residents'], 2)
        self.assertIn('sense graduació', resp.data['message'].lower())
        self.assertEqual(self._regles().count(), 2)
        self.model.refresh_from_db()
        self.assertEqual(self.model.grading_rule_set_id, self.joc_a.id)

    def test_desacoblar_confirmat_esborra_i_deixa_el_seu_rastre(self):
        self._manual('MAN1')

        resp = self._step2(self.model, {'grading_rule_set_id': None,
                                        'confirmar_esborrat_residents': True})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['residents_esborrades'], 2)
        self.model.refresh_from_db()
        self.assertIsNone(self.model.grading_rule_set_id)
        self.assertEqual(self._regles().count(), 0)
        wp = self._watchpoints().get()
        self.assertEqual(wp.dades['tipus'], 'desacoblat_graduacio')
        self.assertEqual(wp.dades['grading_rule_set_id'], self.joc_a.id)
        self.assertEqual(wp.dades['residents'], 2)
        self.assertEqual(wp.estat, 'open')

    def test_desacoblar_un_model_sense_residents_no_frega(self):
        self._regles().delete()

        resp = self._step2(self.model, {'grading_rule_set_id': None})

        self.assertEqual(resp.status_code, 200)
        self.model.refresh_from_db()
        self.assertIsNone(self.model.grading_rule_set_id)
        self.assertFalse(self._watchpoints().exists())


class Decisio61PreservaManualTest(_BaseSembraTest):
    """DECISIÓ 6.1 (Agus, 2026-08-06 nit) — el wipe deixa de matar l'autoria del tècnic.

    ── EL DEFECTE ─────────────────────────────────────────────────────────────────────────
    `materialize_model_grading_rules` feia `model.grading_rules.all().delete()` SENSE FILTRE
    (`services.py`). Qualsevol de les portes que hi passa —canvi de joc, copiar-de-model,
    reimport W5, el command de migració— s'enduia les regles `origen='MANUAL'`, que és el que
    la pantalla de Graduació escriu quan un tècnic afina una mesura a mà. Al dump de PROD del
    04/08 hi havia **660 MANUAL en 25 models**.

    ── LA LLEI, I EL PARANY QUE LA LIMITA ─────────────────────────────────────────────────
    `origen='MANUAL'` NO sempre vol dir autoria: `origen_mgr_des_de_ruleset` estampa MANUAL a
    les residents que surten d'un `GradingRuleSet` amb `origen` NULL, i `ModelGradingRule` no
    guarda de quin joc ve cada fila. Amb la informació disponible al moment del wipe, la
    distinció només es pot fer per l'estat del JOC ANTERIOR — i per això la versió mínima és
    ESTRICTA: es preserva NOMÉS si aquell joc estava classificat. La resta manté el
    comportament d'abans i **s'anota** (`motiu_no_preserva`), perquè la política fina és una
    decisió humana i s'ha de poder prendre amb el cens al davant.

    ── EL RISC QUE LA PRESERVACIÓ OBRE, I QUE AQUÍ ES FIXA ─────────────────────────────────
    `ModelGradingRule` té `unique_together('model','pom')` i la materialització fa `bulk_create`
    sense conflict-handling. Una MANUAL preservada sobre un POM que el joc nou també porta seria
    un `IntegrityError` — i és el cas NORMAL, no el rar (el tècnic retoca el pit del model, i
    després li canvien el joc de catàleg). La regla: la MANUAL preservada MANA sobre la del joc.
    """

    PREFIX = 'D61'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.pom = self._pom('A')
        GarmentPOMMap.objects.create(garment_type_item=self.item, pom=self.pom, ordre=0)
        self.ss = self._size_system('SS_D61')
        self.cli = Customer.objects.create(codi='D6A', nom='Client 6.1')
        self.model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                                 size_system=self.ss, size_run_model='S·M·L',
                                 base_size_label='M', customer=self.cli)

    # ── fixtures ──────────────────────────────────────────────────────────────

    def _joc(self, nom, origen=GradingRuleSet.ORIGEN_CLIENT_RUN, pom=None):
        rs = GradingRuleSet.objects.create(nom=self._codi(nom), size_system=self.ss,
                                           customer=self.cli, origen=origen)
        GradingRule.objects.create(
            rule_set=rs, pom=(pom or self.pom), talla_base=self.ss.talles.get(etiqueta='M'),
            logica=GradingRule.LOGICA_LINEAR, increment='1.00', actiu=True)
        return rs

    def _manual(self, codi, pom=None):
        return ModelGradingRule.objects.create(
            model=self.model, pom=(pom or self._pom(codi)),
            logica=GradingRule.LOGICA_LINEAR, increment='2.00', origen='MANUAL', actiu=True)

    def _regles(self, model=None):
        return ModelGradingRule.objects.filter(model=(model or self.model))

    # ── el predicat, aïllat ───────────────────────────────────────────────────

    def test_el_motiu_de_no_preservar_es_explicit_i_distingeix_els_casos(self):
        from fhort.models_app.services import (JOC_ANTERIOR_NO_INFORMAT, motiu_no_preserva)
        self.assertEqual(motiu_no_preserva(JOC_ANTERIOR_NO_INFORMAT), 'no_informat')
        # M1 (07/08) — «el model no tenia cap joc» JA NO és un motiu de no preservar.
        self.assertIsNone(motiu_no_preserva(None))
        self.assertEqual(motiu_no_preserva(self._joc('SENSE_ORIG', origen='')),
                         'joc_sense_classificar')
        self.assertIsNone(motiu_no_preserva(self._joc('CLASSIFICAT')))

    def test_els_tres_origens_classificats_preserven(self):
        from fhort.models_app.services import motiu_no_preserva
        for origen in (GradingRuleSet.ORIGEN_CANONICAL, GradingRuleSet.ORIGEN_CLIENT_RUN,
                       GradingRuleSet.ORIGEN_IMPORT):
            self.assertIsNone(motiu_no_preserva(self._joc(f'J_{origen}', origen=origen)), origen)

    def test_sense_joc_anterior_informat_el_motor_es_comporta_com_sempre(self):
        """La compatibilitat cap enrere: un camí que encara no ha adoptat 6.1 esborra tot."""
        from fhort.models_app.services import materialize_model_grading_rules
        joc = self._joc('J')
        self._manual('MAN1')
        materialize_model_grading_rules(self.model, joc.regles.all(), origen='CLIENT_RUN')
        self.assertEqual(self._regles().filter(origen='MANUAL').count(), 0)

    # ── PORTA 1 · canvi de joc confirmat (`update-step2`) ─────────────────────

    def test_porta1_canvi_de_joc_amb_MANUAL_autentica_la_MANUAL_sobreviu(self):
        joc_a, joc_b = self._joc('A'), self._joc('B')
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': joc_a.id}).status_code, 200)
        pom_manual = self._pom('MAN')
        self._manual('MAN', pom=pom_manual)

        resp = self._step2(self.model, {'grading_rule_set_id': joc_b.id,
                                        'confirmar_esborrat_residents': True})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['residents_preservades'], 1)
        viva = self._regles().get(pom_id=pom_manual.id)
        self.assertEqual(viva.origen, 'MANUAL')
        self.assertEqual(str(viva.increment), '2.00')   # el VALOR del tècnic, no el del joc

    def test_porta1_amb_MANUAL_de_joc_SENSE_CLASSIFICAR_es_comporta_com_abans(self):
        """🚩 EL PARANY. El joc A no declara origen → les seves residents surten MANUAL i són
        indistingibles de l'autoria. Aquí NO es preserva res, i és a posta: la política fina
        d'aquest cas és una decisió de l'Agus, no una que es pugui deduir de les dades."""
        joc_a = self._joc('A_MUT', origen='')
        joc_b = self._joc('B_OK')
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': joc_a.id}).status_code, 200)
        # El joc A materialitza les seves com a MANUAL: aquesta és la prova del parany.
        self.assertEqual(self._regles().filter(origen='MANUAL').count(), 1)
        self._manual('MAN')                                  # i una d'autoria de debò

        resp = self._step2(self.model, {'grading_rule_set_id': joc_b.id,
                                        'confirmar_esborrat_residents': True})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['residents_preservades'], 0)
        self.assertEqual(resp.data['residents_esborrades'], 2)
        self.assertEqual(self._regles().filter(origen='MANUAL').count(), 0)

    def test_porta1_una_MANUAL_sobre_el_MATEIX_POM_que_el_joc_nou_no_peta_i_mana(self):
        """🔴 El cas que hauria estat un IntegrityError: `unique_together('model','pom')`.
        La MANUAL preservada ocupa el POM i la regla del joc nou NO s'hi escriu a sobre."""
        joc_a, joc_b = self._joc('A'), self._joc('B')        # tots dos porten regla per `self.pom`
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': joc_a.id}).status_code, 200)
        # El tècnic edita EL MATEIX POM que el joc porta (el que fa `set_pom_regim_view`).
        regla = self._regles().get(pom_id=self.pom.id)
        regla.origen = 'MANUAL'
        regla.increment = '9.00'
        regla.save(update_fields=['origen', 'increment'])

        resp = self._step2(self.model, {'grading_rule_set_id': joc_b.id,
                                        'confirmar_esborrat_residents': True})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._regles().count(), 1)
        viva = self._regles().get()
        self.assertEqual(viva.pom_id, self.pom.id)
        self.assertEqual(viva.origen, 'MANUAL')
        self.assertEqual(str(viva.increment), '9.00')        # mana el tècnic, no el joc

    def test_porta1_si_no_es_destrueix_res_no_es_demana_permis(self):
        """La llei de F1-bis en l'altre sentit: demanar permís per esborrar el que NO s'esborra
        és la mateixa mentida amb el signe canviat."""
        joc_a, joc_b = self._joc('A'), self._joc('B', pom=self._pom('ALTRE'))
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': joc_a.id}).status_code, 200)
        # Totes les residents passen a ser autoria del tècnic.
        self._regles().update(origen='MANUAL')

        resp = self._step2(self.model, {'grading_rule_set_id': joc_b.id})   # SENSE confirmar

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['residents_esborrades'], 0)
        self.assertEqual(resp.data['residents_preservades'], 1)
        # I tampoc hi ha Watchpoint: existeix per respondre «on han anat les meves regles», i
        # aquí no n'ha anat cap enlloc.
        from fhort.models_app.models import Watchpoint
        self.assertFalse(Watchpoint.objects.filter(model=self.model).exists())

    # ── M1 (Agus, 07/08) · el model SENSE CAP JOC també preserva ──────────────

    def test_M1_model_sense_joc_conserva_les_MANUAL_en_rebre_el_PRIMER_joc(self):
        """El cas que 6.1 deixava obert i que l'Agus ha tancat el 07/08.

        Un model sense cap joc amb regles `MANUAL`: aquelles NOMÉS poden ser autoria. No hi ha
        joc del qual hagin pogut sortir com a còpia, i «Sense graduació» —l'únic gest que deixa
        un model sense joc havent-ne tingut— ja esborra totes les residents abans. Assignar-li
        el primer joc no se les pot endur.
        """
        pom_manual = self._pom('M1MAN')
        self._manual('M1MAN', pom=pom_manual)
        self.assertIsNone(self.model.grading_rule_set_id)     # sense cap joc: la premissa
        joc = self._joc('M1_PRIMER')

        resp = self._step2(self.model, {'grading_rule_set_id': joc.id,
                                        'confirmar_esborrat_residents': True})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['residents_preservades'], 1)
        viva = self._regles().get(pom_id=pom_manual.id)
        self.assertEqual(viva.origen, 'MANUAL')
        self.assertEqual(str(viva.increment), '2.00')
        # I la del joc també hi és: cauen sobre POMs diferents, no competeixen.
        self.assertEqual(self._regles().count(), 2)

    def test_M1_la_MANUAL_del_model_sense_joc_MANA_sobre_la_del_joc_al_mateix_POM(self):
        """La segona meitat de la mateixa llei: al POM compartit, qui mana és el tècnic."""
        self._manual('M1SAME', pom=self.pom)      # el MATEIX POM que portarà el joc
        joc = self._joc('M1_XOC')

        resp = self._step2(self.model, {'grading_rule_set_id': joc.id,
                                        'confirmar_esborrat_residents': True})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._regles().count(), 1)
        viva = self._regles().get()
        self.assertEqual(viva.pom_id, self.pom.id)
        self.assertEqual(viva.origen, 'MANUAL')
        self.assertEqual(str(viva.increment), '2.00')         # el valor del tècnic, no l'1.00 del joc

    # ── PORTA 2 · copiar d'un altre model ─────────────────────────────────────

    def test_porta2_copiar_de_model_conserva_les_MANUAL_del_desti_i_ho_avisa(self):
        from fhort.models_app.views import copiar_de_model_view
        joc_src = self._joc('SRC')
        joc_dst = self._joc('DST', pom=self._pom('PDST'))
        src = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                          size_system=self.ss, size_run_model='S·M·L', base_size_label='M',
                          customer=self.cli, grading_rule_set=joc_src)
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': joc_dst.id}).status_code, 200)
        pom_manual = self._pom('MANDST')
        self._manual('MANDST', pom=pom_manual)

        req = APIRequestFactory().post(
            f'/api/v1/models/{self.model.id}/copiar-de/{src.id}/',
            # Només la graduació: els altres flags per defecte són certs i aquí només es prova
            # la porta 2 del wipe.
            {'copy_grading': True, 'copy_values': False, 'copy_run': False, 'copy_files': False},
            format='json')
        force_authenticate(req, user=self.user)
        resp = copiar_de_model_view(req, self.model.id, src.id)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._regles().get(pom_id=pom_manual.id).origen, 'MANUAL')
        self.assertTrue(any('MANUAL' in w for w in resp.data.get('warnings', [])))

    # ── PORTA 4 · el command de migració ──────────────────────────────────────

    def test_porta4_cal_materialitzar_segueix_essent_idempotent_amb_MANUAL_vives(self):
        """`migra_brownie_ruleset` promet ser idempotent. Amb la igualtat estricta de conjunts,
        una MANUAL preservada que el joc no porta hauria fet que la comanda trobés feina a
        cada passada, per sempre. La pregunta correcta és «FALTA cap POM del joc?»."""
        from fhort.models_app.management.commands.migra_brownie_ruleset import cal_materialitzar
        joc = self._joc('IDEM')
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': joc.id}).status_code, 200)
        self.assertFalse(cal_materialitzar(self.model, joc))

        self._manual('EXTRA')          # una MANUAL amb un POM que el joc NO porta
        self.assertFalse(cal_materialitzar(self.model, joc))

        self._regles().filter(pom_id=self.pom.id).delete()   # ara SÍ que en falta una del joc
        self.assertTrue(cal_materialitzar(self.model, joc))

    # ── el que 6.1 NO tanca, fixat perquè no se'ns oblidi ─────────────────────

    def test_desacoblar_segueix_esborrant_TOT_i_es_a_posta(self):
        """«Sense graduació» diu que el model es queda SENSE graduar. Deixar-hi residents
        vives el faria graduar igual (`_load_grading_rules` és all-or-nothing) — el contrari
        del que l'usuari ha demanat. Aquesta porta NO entra a 6.1."""
        joc = self._joc('A')
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': joc.id}).status_code, 200)
        self._manual('MAN')

        resp = self._step2(self.model, {'grading_rule_set_id': None,
                                        'confirmar_esborrat_residents': True})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._regles().count(), 0)
        self.assertEqual(resp.data['residents_preservades'], 0)


class M3DerivatDeRuleSetTest(_BaseSembraTest):
    """M3 (2026-08-07) — `ModelGradingRule.derivat_de_rule_set`: de quin joc ve cada fila.

    ── PER QUÈ EXISTEIX ───────────────────────────────────────────────────────────────────
    És l'arrel del parany que la decisió 6.1 no podia tancar. `origen` diu «algú hi ha tocat»,
    no «aquest valor és seu»: els escriptors de pantalla estampen `MANUAL` encara que la regla
    sigui una còpia literal de la del joc, i `origen_mgr_des_de_ruleset` també estampa `MANUAL`
    a tot el que surt d'un joc sense classificar. Amb aquesta sola informació, el wipe només
    podia INFERIR l'autoria mirant l'estat del joc anterior del model sencer.

    ── QUÈ ÉS I QUÈ NO ÉS ─────────────────────────────────────────────────────────────────
    És SENYAL, no llei: M3 no canvia cap política de preservació (l'últim test d'aquesta classe
    ho fixa). D'ara endavant s'omple a la font; les files velles es queden NULL i **no hi ha
    backfill** perquè d'on venien no es pot saber.
    """

    PREFIX = 'M3'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.pom = self._pom('A')
        GarmentPOMMap.objects.create(garment_type_item=self.item, pom=self.pom, ordre=0)
        self.ss = self._size_system('SS_M3')
        self.cli = Customer.objects.create(codi='M3A', nom='Client M3')
        self.model = self._model(garment_type_item=self.item, garment_type=self.item.garment_type,
                                 size_system=self.ss, size_run_model='S·M·L',
                                 base_size_label='M', customer=self.cli)

    # ── fixtures ──────────────────────────────────────────────────────────────

    def _joc(self, nom, origen=GradingRuleSet.ORIGEN_CLIENT_RUN, pom=None):
        rs = GradingRuleSet.objects.create(nom=self._codi(nom), size_system=self.ss,
                                           customer=self.cli, origen=origen)
        GradingRule.objects.create(
            rule_set=rs, pom=(pom or self.pom), talla_base=self.ss.talles.get(etiqueta='M'),
            logica=GradingRule.LOGICA_LINEAR, increment='1.00', increment_base='1.00', actiu=True)
        return rs

    def _regles(self):
        return ModelGradingRule.objects.filter(model=self.model)

    def _set_regim(self, pom_id, payload):
        from fhort.models_app.views import set_pom_regim_view
        req = APIRequestFactory().post(
            f'/api/v1/models/{self.model.id}/poms/{pom_id}/regim/', payload, format='json')
        force_authenticate(req, user=self.user)
        return set_pom_regim_view(req, self.model.id, pom_id)

    # ── materialitzar OMPLE la FK ─────────────────────────────────────────────

    def test_materialitzar_des_del_joc_omple_la_traçabilitat(self):
        joc = self._joc('OMPLE')
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': joc.id}).status_code, 200)

        regla = self._regles().get(pom_id=self.pom.id)
        self.assertEqual(regla.derivat_de_rule_set_id, joc.id)

    def test_canviar_de_joc_reescriu_la_traçabilitat_al_joc_NOU(self):
        """El camp segueix la fila, i la fila es torna a materialitzar: ha de dir el joc VIU."""
        joc_a, joc_b = self._joc('A'), self._joc('B')
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': joc_a.id}).status_code, 200)
        self.assertEqual(self._regles().get(pom_id=self.pom.id).derivat_de_rule_set_id, joc_a.id)

        resp = self._step2(self.model, {'grading_rule_set_id': joc_b.id,
                                        'confirmar_esborrat_residents': True})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._regles().get(pom_id=self.pom.id).derivat_de_rule_set_id, joc_b.id)

    def test_el_cami_dels_SPECS_distingeix_el_contenidor_del_document(self):
        """El camí de W5 és MIXT a posta: el que ve del contenidor porta el joc, el que ve del
        document del client no en porta cap —perquè no en ve de cap."""
        from fhort.models_app.services import materialize_model_grading_rules_from_specs
        from fhort.pom.grading_utils import rule_to_spec
        joc = self._joc('SPECS')
        pom_doc = self._pom('DOC')
        spec_contenidor = rule_to_spec(joc.regles.get())
        spec_document = {'pom_id': pom_doc.id, 'logica': 'LINEAR', 'increment': '3.00',
                         'increment_base': '3.00'}

        materialize_model_grading_rules_from_specs(
            self.model, [spec_contenidor, spec_document], origen='IMPORTED')

        self.assertEqual(self._regles().get(pom_id=self.pom.id).derivat_de_rule_set_id, joc.id)
        self.assertIsNone(self._regles().get(pom_id=pom_doc.id).derivat_de_rule_set_id)

    # ── les MANUAL de pantalla ────────────────────────────────────────────────

    def test_pantalla_regla_nova_SENSE_joc_al_model_deixa_la_FK_NULL(self):
        """Autoria de zero: no hi ha cap joc darrere d'aquesta fila, i el camp ho ha de dir."""
        self.assertIsNone(self.model.grading_rule_set_id)

        resp = self._set_regim(self.pom.id, {'logica': 'LINEAR', 'increment_base': 4})

        self.assertEqual(resp.status_code, 200)
        regla = self._regles().get(pom_id=self.pom.id)
        self.assertEqual(regla.origen, 'MANUAL')
        self.assertIsNone(regla.derivat_de_rule_set_id)

    def test_pantalla_regla_nova_SEMBRADA_del_fallback_del_cataleg_HERETA_el_joc(self):
        """🔴 La mentida que M3 desfà. La fila neix copiant la regla del joc i se li estampa
        `MANUAL` igualment: `origen` diu «algú hi ha tocat», i la FK diu d'on ve de debò."""
        joc = self._joc('FALLBACK')
        self.model.grading_rule_set = joc
        self.model.save(update_fields=['grading_rule_set'])
        pom_nou = self._pom('NOU')
        GradingRule.objects.create(
            rule_set=joc, pom=pom_nou, talla_base=self.ss.talles.get(etiqueta='M'),
            logica=GradingRule.LOGICA_LINEAR, increment='1.00', increment_base='1.00', actiu=True)

        resp = self._set_regim(pom_nou.id, {'logica': 'LINEAR', 'increment_base': 4})

        self.assertEqual(resp.status_code, 200)
        regla = self._regles().get(pom_id=pom_nou.id)
        self.assertEqual(regla.origen, 'MANUAL')
        self.assertEqual(regla.derivat_de_rule_set_id, joc.id)

    def test_pantalla_editar_una_fila_existent_NO_li_canvia_la_procedencia(self):
        """El camp diu d'on va NÉIXER la fila, no qui l'ha tocada l'últim (això és `origen`)."""
        joc = self._joc('EDIT')
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': joc.id}).status_code, 200)
        self.assertEqual(self._regles().get(pom_id=self.pom.id).derivat_de_rule_set_id, joc.id)

        resp = self._set_regim(self.pom.id, {'logica': 'LINEAR', 'increment_base': 7})

        self.assertEqual(resp.status_code, 200)
        regla = self._regles().get(pom_id=self.pom.id)
        self.assertEqual(regla.origen, 'MANUAL')            # ara sí que hi ha tocat algú
        self.assertEqual(str(regla.increment_base), '7.00')
        self.assertEqual(regla.derivat_de_rule_set_id, joc.id)   # però d'on ve no ha canviat

    # ── NO-REGRESSIÓ: el senyal existeix, però encara no mana ─────────────────

    def test_el_wipe_amb_la_FK_informada_es_comporta_EXACTAMENT_com_ahir(self):
        """M3 afegeix senyal, no política. Qui decideix la preservació segueix essent l'estat
        del JOC ANTERIOR (6.1 + M1), no aquest camp — encara que ara el camp digui la veritat.

        Les dues meitats, al mateix test perquè el contrast és el que fixa la llei:
          · joc anterior CLASSIFICAT     → la MANUAL sobreviu (com ahir).
          · joc anterior SENSE classificar → la MANUAL cau, tot i que la FK ja diu que ve
            d'aquell joc. Si algun dia això canvia, serà una decisió, i aquest test la veurà.
        """
        from fhort.models_app.services import poms_manual_a_preservar
        joc_mut = self._joc('MUT', origen='')
        joc_ok = self._joc('OK')
        self.assertEqual(self._step2(self.model, {'grading_rule_set_id': joc_mut.id}).status_code, 200)
        regla = self._regles().get(pom_id=self.pom.id)
        self.assertEqual(regla.origen, 'MANUAL')                  # el parany, materialitzat
        self.assertEqual(regla.derivat_de_rule_set_id, joc_mut.id)  # i ara SABEM que és còpia
        # ...i tot i saber-ho, la política no el mira: joc anterior sense classificar → no preserva.
        self.assertEqual(poms_manual_a_preservar(self.model, joc_mut), set())

        resp = self._step2(self.model, {'grading_rule_set_id': joc_ok.id,
                                        'confirmar_esborrat_residents': True})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['residents_preservades'], 0)

        # L'ALTRA MEITAT. Ara el model penja d'un joc CLASSIFICAT i el tècnic li toca la regla
        # (la fila es queda amb la seva FK: ve de `joc_ok`, i editar-la no ho canvia). El
        # predicat, amb el mateix camp informat que abans, ara SÍ que preserva — perquè el que
        # mira és el joc anterior, no la FK.
        self.assertEqual(self._set_regim(self.pom.id, {'logica': 'LINEAR',
                                                       'increment_base': 5}).status_code, 200)
        tocada = self._regles().get(pom_id=self.pom.id)
        self.assertEqual(tocada.origen, 'MANUAL')
        self.assertEqual(tocada.derivat_de_rule_set_id, joc_ok.id)
        self.assertEqual(poms_manual_a_preservar(self.model, joc_ok), {self.pom.id})
