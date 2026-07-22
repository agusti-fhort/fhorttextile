"""P4 (2026-07-22) — l'eina de propostes d'àmbit `seed_scope_nodes_proposals`.

Executat amb `python manage.py test fhort.pom` (el projecte NO fa servir pytest).

L'eina és material per a una sessió de treball humana: proposa nodes ITEM derivats dels
models reals que usen cada contenidor, i la decisió node a node és de la Montse. Per això
el que aquests tests defensen no és el criteri (que és de domini) sinó les GUARDES:

  · el dry-run —que és el DEFAULT— no escriu ni una fila;
  · els contenidors que JA tenen àmbit no es toquen, ni per completar-los;
  · un contenidor sense regles no entra (no és assignable: `amb_regles=1` al picker);
  · la proposta és MULTI-NODE — el cas real que va fer impossible el backfill literal de la
    identitat (13 dels 20 contenidors LOSAN serveixen un CONJUNT d'items, no un item);
  · `--apply` és idempotent i mai toca la IDENTITAT (`garment_type_item`).
"""
import datetime
from io import StringIO

from django.core.management import call_command
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import Model
from fhort.pom.models import (GarmentType, GradingRule, GradingRuleSet, POMMaster,
                              RuleSetScopeNode, SizeDefinition, SizeSystem)
from fhort.tasks.models import GarmentTypeItem


class P4ScopeProposalsTest(TenantTestCase):

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
        self.ss = SizeSystem.objects.create(nom='P4 ALPHA', codi='P4_ALPHA')
        self.sd = SizeDefinition.objects.create(size_system=self.ss, etiqueta='M', ordre=1)
        self.pom = POMMaster.objects.create(codi_client='P4-01', nom_client='Pit')
        self.gt = GarmentType.objects.create(
            codi_client='P4_TOPS', nom_client='Tops P4', grup='TOPS')
        self.item_a = GarmentTypeItem.objects.create(
            garment_type=self.gt, code='p4_tee', name='Tee')
        self.item_b = GarmentTypeItem.objects.create(
            garment_type=self.gt, code='p4_polo', name='Polo')
        self._seq = 0

    # ── helpers ────────────────────────────────────────────────────────────────

    def _rs(self, nom, amb_regles=True):
        rs = GradingRuleSet.objects.create(nom=nom, size_system=self.ss)
        if amb_regles:
            GradingRule.objects.create(rule_set=rs, pom=self.pom, talla_base=self.sd,
                                       logica='LINEAR', increment=1)
        return rs

    def _model(self, rs, item):
        self._seq += 1
        return Model.objects.create(
            codi_intern=f'P4-M{self._seq}', codi_tenant='TST', any=2026, temporada='SS',
            sequencial=self._seq, garment_type=self.gt,
            garment_type_item=item, grading_rule_set=rs)

    def _run(self, **kw):
        out = StringIO()
        call_command('seed_scope_nodes_proposals', schema=self.tenant.schema_name,
                     stdout=out, **kw)
        return out.getvalue()

    # ── la guarda principal ────────────────────────────────────────────────────

    def test_dry_run_es_el_default_i_no_escriu_res(self):
        rs = self._rs('P4 candidat')
        self._model(rs, self.item_a)

        sortida = self._run()

        self.assertEqual(RuleSetScopeNode.objects.count(), 0)
        self.assertIn('DRY-RUN', sortida)
        self.assertIn('no s’ha escrit res', sortida)
        # I la proposta SÍ que es veu: dry-run vol dir "no escriu", no "no diu res".
        self.assertIn(f'ITEM {self.item_a.id}', sortida)

    # ── qui queda fora ─────────────────────────────────────────────────────────

    def test_un_contenidor_amb_ambit_no_es_toca(self):
        """Qui ja té nodes els té per decisió humana: completar-la seria inventar-se-la."""
        rs = self._rs('P4 ja amb àmbit')
        RuleSetScopeNode.objects.create(rule_set=rs, node_type=RuleSetScopeNode.NODE_ITEM,
                                        garment_type_item=self.item_a)
        self._model(rs, self.item_b)   # un item NOU que no és al seu àmbit

        self._run(apply=True)

        self.assertEqual(
            list(rs.scope_nodes.values_list('garment_type_item_id', flat=True)),
            [self.item_a.id])

    def test_un_contenidor_sense_regles_no_entra(self):
        rs = self._rs('P4 buit', amb_regles=False)
        self._model(rs, self.item_a)

        self._run(apply=True)

        self.assertEqual(rs.scope_nodes.count(), 0)

    def test_sense_models_no_sinventa_res(self):
        rs = self._rs('P4 orfe')

        sortida = self._run(apply=True)

        self.assertEqual(rs.scope_nodes.count(), 0)
        self.assertIn('SENSE EVIDÈNCIA', sortida)

    # ── el cas real: multi-node ────────────────────────────────────────────────

    def test_proposa_MULTI_node_quan_el_contenidor_serveix_un_conjunt(self):
        """El cas que va fer impossible el backfill literal de la identitat.

        Dos items diferents avalats per models diferents: una FK singular no ho pot dir,
        l'àmbit sí. I l'ordre és per aval descendent (el més usat, primer).
        """
        rs = self._rs('P4 conjunt')
        self._model(rs, self.item_a)
        self._model(rs, self.item_a)
        self._model(rs, self.item_b)

        sortida = self._run()
        self.assertLess(sortida.index(f'ITEM {self.item_a.id}'),
                        sortida.index(f'ITEM {self.item_b.id}'))
        self.assertIn('avalat per 2 model(s)', sortida)

        self._run(apply=True)
        self.assertEqual(
            set(rs.scope_nodes.values_list('garment_type_item_id', flat=True)),
            {self.item_a.id, self.item_b.id})

    def test_min_models_filtra_el_soroll(self):
        rs = self._rs('P4 llindar')
        self._model(rs, self.item_a)
        self._model(rs, self.item_a)
        self._model(rs, self.item_b)      # 1 sol model → sota el llindar

        self._run(apply=True, min_models=2)

        self.assertEqual(
            list(rs.scope_nodes.values_list('garment_type_item_id', flat=True)),
            [self.item_a.id])

    # ── apply: idempotent i sense tocar la identitat ───────────────────────────

    def test_apply_es_idempotent_i_no_toca_la_identitat(self):
        rs = self._rs('P4 idempotent')
        self._model(rs, self.item_a)

        self._run(apply=True)
        self._run(apply=True)

        self.assertEqual(rs.scope_nodes.count(), 1)
        rs.refresh_from_db()
        self.assertIsNone(rs.garment_type_item_id)   # la IDENTITAT, intacta
