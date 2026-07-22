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
