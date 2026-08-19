"""FASE 2 (2026-08-19) — el banc dels DOS GUARDS DIRIGITS PER DADES.

Executat amb `python manage.py test fhort.pom` (el projecte NO fa servir pytest).

CONTEXT. `pom/0066` i `pom/0070` van néixer amb el cens de STAGING cablejat a dins (ids
literals, noms de ruleset, i fins i tot l'afirmació «a `los` no hi ha cap SizingProfile»).
Contra PROD les dues avortaven, i l'avortament tapava el que de debò importava: que allà els
mateixos codis designen objectes VIUS. La FASE 2 les va reescriure perquè decideixin per
dades. Aquest banc fixa el comportament que aquella reescriptura ha de garantir per sempre:

  · **0066** — un run només cau si les dades diuen que és mort. Si és viu, es LOGA i se salta;
    mai avorta, mai esborra a mitges.
  · **0070** — només cauen els duplicats d'àmbit que són bessons BYTE A BYTE. Els que porten
    graduació distinta es conserven, que és el cas de LOSAN (NEWBORN × 3 menes de peça).

Les funcions de migració es criden amb el registre d'apps REAL: només fan servir
`apps.get_model` / `apps.get_models` i `schema_editor.connection.schema_name`, o sigui que un
`schema_editor` de fusta n'hi ha prou i el que s'exercita és el guard de debò, no una còpia.
"""
from importlib import import_module

from django.apps import apps as apps_reals
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import Model
from fhort.pom.models import (ConstructionType, FitType, GarmentType, GradingRule,
                              GradingRuleSet, POMMaster, SizeDefinition, SizeSystem,
                              SizingProfile, Target)
from fhort.tasks.models import Customer

M0066 = import_module('fhort.pom.migrations.0066_c3_depuracio_runs_autoritzada')
M0070 = import_module('fhort.pom.migrations.0070_cat23_sizingprofile_unicitat')


class _EditorDeFusta:
    """El mínim que les dues funcions demanen: `connection.schema_name`."""

    class connection:
        schema_name = 'test'


class Guard0066Test(TenantTestCase):
    """Un run autoritzat cau NOMÉS si les dades diuen que és mort."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        return tenant

    def _run(self, codi):
        return SizeSystem.objects.create(codi=codi, nom=f'Run {codi}')

    def _depura(self):
        M0066.depura(apps_reals, _EditorDeFusta())

    def test_run_mort_i_autoritzat_cau(self):
        """Cap ruleset, cap model, cap FK entrant → s'esborra, i amb ell les seves talles."""
        ss = self._run('MEN-SHIRT-NUM')
        SizeDefinition.objects.create(size_system=ss, etiqueta='38', ordre=1)
        self._depura()
        self.assertFalse(SizeSystem.objects.filter(pk=ss.pk).exists())
        self.assertFalse(SizeDefinition.objects.filter(size_system_id=ss.pk).exists())

    def test_run_amb_model_viu_NO_cau(self):
        """El cas de PROD: `WOMAN_BRW_01` amb 10 models. Se salta, no avorta."""
        ss = self._run('WOMAN_BRW_01')
        client = Customer.objects.create(codi='TST', nom='Test')
        Model.objects.create(codi_intern='TST-SS26-0001', codi_tenant='TST', any=2026,
                             temporada='SS', sequencial=1, customer=client, size_system=ss)
        self._depura()                                   # no ha de llançar res
        self.assertTrue(SizeSystem.objects.filter(pk=ss.pk).exists(),
                        'un run amb models vius no es pot esborrar')

    def test_run_amb_ruleset_no_autoritzat_NO_cau(self):
        """L'altra meitat del cas de PROD: rulesets que el cens no va autoritzar."""
        ss = self._run('WOMAN_BRW_01')
        GradingRuleSet.objects.create(nom='BRW WOMEN WOVEN REGULAR BLUSA', size_system=ss)
        self._depura()
        self.assertTrue(SizeSystem.objects.filter(pk=ss.pk).exists())
        self.assertTrue(GradingRuleSet.objects.filter(size_system=ss).exists(),
                        'el ruleset no autoritzat tampoc no es toca')

    def test_run_no_autoritzat_NO_es_mira(self):
        """Un run mort però fora de la llista segueix viu: la llista mana sobre l'estat."""
        ss = self._run('UN_RUN_QUALSEVOL')
        self._depura()
        self.assertTrue(SizeSystem.objects.filter(pk=ss.pk).exists())

    def test_el_cens_de_fk_veu_les_related_name_plus(self):
        """La troballa de la FASE 2: `related_name='+'` no surt per introspecció inversa.

        Si `_fks_cap_a` tornés a fer-se amb `get_fields()`, aquestes dues desapareixerien del
        cens i un delete quedaria «segur» sense ser-ho.
        """
        parelles = {(m._meta.label, c)
                    for m, c in M0066._fks_cap_a(apps_reals, POMMaster)}
        self.assertIn(('models_app.SizeCheckLine', 'pom'), parelles)
        self.assertIn(('fitting.PieceFittingLine', 'pom'), parelles)


class Guard0070Test(TenantTestCase):
    """Només cauen els duplicats d'àmbit que són bessons byte a byte."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        return tenant

    def setUp(self):
        self.target = Target.objects.create(codi='NEWBORN_GIRL', nom_en='Newborn Girl')
        self.gt = GarmentType.objects.create(codi_client='NEWBORN', nom_client='Newborn',
                                             grup='NEWBORN')
        self.constr = ConstructionType.objects.create(codi='KNIT', nom_en='Knit')
        self.fit = FitType.objects.create(codi='REG', nom_en='Regular')
        self.ss = SizeSystem.objects.create(codi='NEWBORN_LOS_01', nom='LOS New Born')
        self.talla = SizeDefinition.objects.create(size_system=self.ss, etiqueta='3M', ordre=1)
        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Front width')

    def _ruleset(self, nom, increment):
        rs = GradingRuleSet.objects.create(nom=nom, size_system=self.ss)
        GradingRule.objects.create(rule_set=rs, pom=self.pom, talla_base=self.talla,
                                   logica='LINEAR', increment_base=increment)
        return rs

    def _perfil(self, rs):
        return SizingProfile.objects.create(
            target=self.target, garment_type=self.gt, construction=self.constr,
            fit_type=self.fit, size_system=self.ss, grading_rule_set=rs)

    def _neteja(self):
        M0070.neteja(apps_reals, _EditorDeFusta())

    def test_duplicats_amb_graduacio_DISTINTA_es_conserven(self):
        """El cas de LOSAN: NEWBORN × Tops/Onepieces/Bottoms. Cap dels tres pot caure."""
        a = self._perfil(self._ruleset('LOS New Born Knit — Tops', 1))
        b = self._perfil(self._ruleset('LOS New Born Knit — Onepieces', 2))
        c = self._perfil(self._ruleset('LOS New Born Knit — Bottoms', 3))
        self._neteja()
        for p in (a, b, c):
            self.assertTrue(SizingProfile.objects.filter(pk=p.pk).exists(),
                            f'el perfil {p.pk} porta graduació pròpia i no pot caure')

    def test_bessons_byte_a_byte_cau_el_mes_nou(self):
        """Mateix àmbit i MATEIX joc de regles: allò sí que és un duplicat."""
        vell = self._perfil(self._ruleset('Canonic', 1))
        nou = self._perfil(self._ruleset('Copia byte a byte', 1))
        self._neteja()
        self.assertTrue(SizingProfile.objects.filter(pk=vell.pk).exists(),
                        'es queda el més antic')
        self.assertFalse(SizingProfile.objects.filter(pk=nou.pk).exists())

    def test_la_clau_unica_ja_no_hi_es(self):
        """D4: la BD ha de deixar conviure el que el domini justifica."""
        self.assertEqual(SizingProfile._meta.unique_together, (),
                         'unique_together ha de ser buit — v. DEUTE G6')

    def test_perfil_sense_ruleset_no_es_toca(self):
        """Sense graduació no hi ha empremta comparable: no es pot afirmar que siguin bessons."""
        a = self._perfil(None)
        b = self._perfil(None)
        self._neteja()
        self.assertEqual(SizingProfile.objects.filter(pk__in=[a.pk, b.pk]).count(), 2)
