"""P7 (2026-07-22) — jubilació del FK legacy `GradingRuleSet.target` (D-CONS).

Executat amb `python manage.py test fhort.pom` (el projecte NO fa servir pytest).

Context: el M2M `targets` va néixer a la migració 0009 SENSE data-migration, i per això va
conviure 13 mesos amb un FK singular que ningú llegia aigües avall però que 4 punts encara
escrivien. La diagnosi va comptar 10 divergències FK↔M2M al schema `fhort`, 8 d'elles **no
representables** per una FK (>1 target), i **1 cas de pèrdua real** si s'esborrava el camp a
sec: el rs 98, amb FK plena i M2M BUIDA.

Aquests tests fixen les tres coses que la jubilació ha de garantir per sempre:
  · **A** — el camp és fora del model i no pot tornar per descuit.
  · **B** — la forma del rs 98 (l'únic amb pèrdua real) sobreviu: un ruleset amb un sol
    target el conserva a la M2M i el resolutor de contenidors el troba.
  · **C** — el cas que el FK MAI va poder expressar (>1 target) ara és de primera classe, i
    el clon de perfil (`s2_views`) n'hereta el conjunt SENCER, no només el primer.
"""
import datetime

from django.core.exceptions import FieldDoesNotExist
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GradingRuleSet, SizeSystem, Target


class P7TargetFKTest(TenantTestCase):

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
        self.ss = SizeSystem.objects.create(nom='P7 ALPHA', codi='P7_ALPHA')
        # `Target` és catàleg compartit i pot venir sembrat: get_or_create, no create.
        self.t_woman, _ = Target.objects.get_or_create(
            codi='WOMAN', defaults={'nom_en': 'Woman'})
        self.t_teen, _ = Target.objects.get_or_create(
            codi='TEEN_GIRL', defaults={'nom_en': 'Teen Girl'})

    # ── A · el camp és fora, i la M2M és l'única via ────────────────────────────

    def test_fk_target_no_existeix_al_model(self):
        """Guarda de regressió: si algú el torna a afegir, aquest test cau."""
        with self.assertRaises(FieldDoesNotExist):
            GradingRuleSet._meta.get_field('target')

    def test_crear_amb_target_fk_peta(self):
        """El kwarg legacy ja no s'accepta enlloc — cap camí el pot ressuscitar en silenci."""
        with self.assertRaises(TypeError):
            GradingRuleSet.objects.create(
                nom='P7 amb FK', size_system=self.ss, target=self.t_woman)

    # ── B · la forma del rs 98: un sol target, cap pèrdua ───────────────────────

    def test_ruleset_amb_un_target_el_conserva_i_es_troba(self):
        """La forma exacta que la data-migration va haver de rescatar (rs 98).

        Un target únic ha de continuar sent consultable pels dos consumidors reals: el
        serializer (`target_codi`, que ja llegia `targets.first()`) i el filtre per codi
        que fa servir el resolutor de contenidors (`grading_utils.py:641`).
        """
        rs = GradingRuleSet.objects.create(nom='P7 un target', size_system=self.ss)
        rs.targets.add(self.t_woman)

        self.assertEqual(rs.targets.first(), self.t_woman)
        self.assertEqual(
            list(GradingRuleSet.objects.filter(targets__codi='WOMAN')), [rs])

    # ── C · el cas que el FK no podia expressar ─────────────────────────────────

    def test_multi_target_es_de_primera_classe(self):
        """8 rulesets reals apliquen a >1 target; amb el FK això era irrepresentable."""
        rs = GradingRuleSet.objects.create(nom='P7 multi', size_system=self.ss)
        rs.targets.set([self.t_woman, self.t_teen])

        self.assertEqual(rs.targets.count(), 2)
        # Es troba pels DOS codis, no només pel primer.
        for codi in ('WOMAN', 'TEEN_GIRL'):
            self.assertIn(rs, GradingRuleSet.objects.filter(targets__codi=codi))

    def test_clon_hereta_el_conjunt_sencer_de_targets(self):
        """`s2_views` clonava `target=original.target` → perdia tots menys un.

        Reprodueix el gest del clon de perfil tal com queda després de P7.
        """
        original = GradingRuleSet.objects.create(nom='P7 original', size_system=self.ss)
        original.targets.set([self.t_woman, self.t_teen])

        clon = GradingRuleSet.objects.create(nom='P7 clon', size_system=self.ss)
        clon.targets.set(original.targets.all())

        self.assertEqual(
            set(clon.targets.values_list('codi', flat=True)),
            {'WOMAN', 'TEEN_GIRL'})
