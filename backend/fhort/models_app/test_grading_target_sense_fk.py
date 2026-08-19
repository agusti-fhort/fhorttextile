"""N1 — EL NOM DEL TARGET SURT DE LA M2M, I UN RULESET SENSE TARGETS NO PETA.

El defecte que això fixa: `get_grading_target_nom` i `get_grading_noms` tenien un tercer graó
que llegia `GradingRuleSet.target`, el FK que la migració `pom/0043` (P7) va RETIRAR. Amb un
ruleset de `targets` buida el graó s'executava i el GET del model responia **500** amb
`AttributeError: 'GradingRuleSet' object has no attribute 'target_id'`. A staging hi queien
quatre models de debò (163, 164, 182, 188), tots apuntant al mateix ruleset.

Els tres tests fixen el contracte SENCER, no només que no peti: el camí de la M2M (que és el
que ha de manar), el camí del text lliure del Model (que és el que cobreix el ruleset sense
targets) i el cas sense ruleset.

Convenció del repo: `python manage.py test fhort.models_app.test_grading_target_sense_fk`.
"""
import datetime

from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import Model
from fhort.models_app.serializers import ModelDetailSerializer
from fhort.pom.models import GradingRuleSet, Target


class GradingTargetSenseFKTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TGT'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        self.rs = GradingRuleSet.objects.create(nom='QA ruleset N1')
        self._n = 0

    def _model(self, **extra):
        self._n += 1
        return Model.objects.create(
            codi_intern=f'QA-N1-{self._n}', codi_tenant='TGT', any=2027, sequencial=self._n,
            nom_prenda='QA N1', **extra)

    def test_ruleset_sense_targets_no_peta_i_cau_al_camp_del_model(self):
        """EL CAS DEL 500. `targets` buida ja no és una excepció: és el camí del text lliure."""
        m = self._model(target='WOMAN', grading_rule_set=self.rs)
        dades = ModelDetailSerializer(m).data
        self.assertEqual(dades['grading_target_nom'], 'WOMAN')
        self.assertEqual(dades['grading_noms']['target'],
                         {'ca': 'WOMAN', 'en': 'WOMAN', 'es': 'WOMAN'})

    def test_la_m2m_mana_sobre_el_camp_del_model(self):
        """Amb targets al ruleset, el nom surt del CATÀLEG i traduït — no del text lliure."""
        t = Target.objects.create(codi='QA_MAN', nom_en='Man', nom_cat='Home', nom_es='Hombre')
        self.rs.targets.add(t)
        m = self._model(target='NO VISIBLE', grading_rule_set=self.rs)
        dades = ModelDetailSerializer(m).data
        self.assertEqual(dades['grading_target_nom'], 'Man')
        self.assertEqual(dades['grading_noms']['target'],
                         {'ca': 'Home', 'en': 'Man', 'es': 'Hombre'})

    def test_sense_ruleset_ni_text_no_hi_ha_nom(self):
        """Ni ruleset ni camp: `None`, no una cadena buida ni una excepció."""
        m = self._model(target='')
        dades = ModelDetailSerializer(m).data
        self.assertIsNone(dades['grading_target_nom'])
        self.assertIsNone(dades['grading_noms']['target'])
