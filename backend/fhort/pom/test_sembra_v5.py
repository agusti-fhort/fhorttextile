"""OPS/SEMBRA_V5 · el banc de les set comandes (23/08/2026).

Substrat: el brief `OPS/SEMBRA_V5`, el `CENS_CATALEG_V5_STAGING.md` (22/08) i el tren de panys
del mateix dia. El que es mesura, i per què cada cas hi és:

  · `CorpusTest`        — el hash ABORTA, i els recomptes del full també. La sembra no llegeix
                          mai un arxiu que no sigui EL de la decisió.
  · `S1FamiliesTest`    — les 14 a `public`, idempotents, i el pany de nomenclatura.
  · `S2CatalegTest`     — els 165 globals, idempotents, i el pany camp a camp.
  · `S3LligamTest`      — el lligam pel mapa del r2; **un POM SEPARAT no es re-enganxa** (el
                          cas que el brief demana explícitament); un lligam divergent es
                          reporta i no es mou; i el codi HOMÒNIM no es lliga per coincidència.
  · `S4AliesTest`       — create-only: un àlies amb un altre destí no es mou.
  · `S5RemapTest`       — el remapatge per fila del r2, l'arxiu intacte i la supressió amb
                          guarda de les `CAT-*` (que amb `SET_NULL` no petaria mai sola).
  · `S6TancamentTest`   — el cas 462/463 del brief, resolt PEL CODI i no per pk.
  · `S7FinestraTest`    — el tall inert, l'abort quan deixaria de ser inert, i l'arxivat sense
                          cap `DELETE`.
  · `LleiGirthTest`     — ⚖️ cap comanda del tram crea cap `GradingRule`. Cap.

⚠️ Cap escriptura a cap BD viva: `TenantTestCase` corre sobre una BD de test pròpia.
"""
import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context

from fhort.pom.models import (CustomerPOMAlias, GradingRule, GradingRuleSet, POMCategory,
                              POMGlobal, POMMaster)
from fhort.pom.sembra_v5 import corpus
from fhort.tasks.models import Customer


#: Les guardes del brief porten xifres de PROD (12 `CAT-*`, 2 POMs de tancament, 25 models,
#: 27 jocs). Un banc és un entorn en miniatura i no les té: per això cada prova DECLARA la seva
#: amb `--espera`, que és exactament la porta que l'operador fa servir quan la realitat no
#: confirma el brief. Que el banc l'hagi de fer servir és part del que es mesura.
def crida(comanda, *args, **kw):
    """Corre una comanda del tram i retorna el que ha escrit a stdout."""
    out = StringIO()
    call_command(comanda, *args, stdout=out, stderr=out, **kw)
    return out.getvalue()


class BancV5(TenantTestCase):
    """El terreny mínim: el schema del tenant de test i el corpus real."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema = connection.schema_name
        _sha, cls.poms, cls.families, cls.alies = corpus.carrega()
        cls.mapa = corpus.mapa_brownie(cls.alies)

    def sembra_globals(self):
        crida('sembra_cataleg_sistema', '--schema', self.schema, '--no-dry-run')


# ── El corpus ─────────────────────────────────────────────────────────────────────────────
class CorpusTest(TenantTestCase):

    def test_el_r2_dona_els_recomptes_del_brief(self):
        _sha, poms, families, alies = corpus.carrega()
        self.assertEqual((len(poms), len(families), len(alies)), (165, 14, 105))
        self.assertEqual(sum(1 for p in poms if p['actiu']), 161)
        self.assertEqual(sum(1 for p in poms if not p['actiu']), 4)

    def test_un_arxiu_retocat_ABORTA(self):
        """El hash no és decoració: dos entorns han de llegir els MATEIXOS bytes."""
        with tempfile.TemporaryDirectory() as d:
            fals = Path(d) / corpus.NOM_XLSX
            shutil.copy(corpus.cami_del_corpus(), fals)
            with open(fals, 'ab') as fh:
                fh.write(b'\x00')
            with self.assertRaises(CommandError) as e:
                corpus.carrega(str(fals))
            self.assertIn('HASH NO COINCIDENT', str(e.exception))

    def test_les_columnes_sense_desti_estan_declarades(self):
        """El forat d'esquema no es pot oblidar en silenci: viu al codi, no a l'acta."""
        for col in ('Pos.', 'Règim', 'Ancoratge', 'Capa'):
            self.assertIn(col, corpus.COLUMNES_SENSE_DESTI)


# ── S1 ────────────────────────────────────────────────────────────────────────────────────
class S1FamiliesTest(BancV5):

    def test_crea_les_14_i_la_segona_passada_no_canvia_res(self):
        with schema_context('public'):
            POMCategory.objects.filter(codi__in=[f['codi'] for f in self.families]).delete()
        crida('sembra_families_sistema', '--no-dry-run')
        with schema_context('public'):
            self.assertEqual(
                POMCategory.objects.filter(
                    codi__in=[f['codi'] for f in self.families]).count(), 14)
        sortida = crida('sembra_families_sistema', '--no-dry-run')
        self.assertIn('famílies creades: 0', sortida)
        self.assertIn('famílies ja iguals (idempotència): 14', sortida)

    def test_una_familia_rebatejada_a_ma_NO_es_reescriu(self):
        crida('sembra_families_sistema', '--no-dry-run')
        with schema_context('public'):
            cat = POMCategory.objects.get(codi='E')
            cat.nom_ca = 'EL NOM QUE LA MONTSE HI VA POSAR'
            cat.save(update_fields=['nom_ca'])
        sortida = crida('sembra_families_sistema', '--no-dry-run')
        self.assertIn('🔒', sortida)
        with schema_context('public'):
            self.assertEqual(POMCategory.objects.get(codi='E').nom_ca,
                             'EL NOM QUE LA MONTSE HI VA POSAR')
        crida('sembra_families_sistema', '--no-dry-run', '--overwrite-from-xlsx')
        with schema_context('public'):
            self.assertNotEqual(POMCategory.objects.get(codi='E').nom_ca,
                                'EL NOM QUE LA MONTSE HI VA POSAR')

    def test_el_dry_run_no_escriu(self):
        with schema_context('public'):
            POMCategory.objects.filter(codi='H').delete()
        crida('sembra_families_sistema')
        with schema_context('public'):
            self.assertFalse(POMCategory.objects.filter(codi='H').exists())


# ── S2 ────────────────────────────────────────────────────────────────────────────────────
class S2CatalegTest(BancV5):

    def test_els_165_i_la_idempotencia(self):
        self.sembra_globals()
        self.assertEqual(POMGlobal.objects.count(), 165)
        self.assertEqual(POMGlobal.objects.filter(actiu=False).count(), 4)
        sortida = self.sembra_globals_sortida()
        self.assertIn('POMGlobal creats: 0', sortida)
        self.assertIn('POMGlobal ja iguals (idempotència): 165', sortida)

    def sembra_globals_sortida(self):
        return crida('sembra_cataleg_sistema', '--schema', self.schema, '--no-dry-run')

    def test_el_com_es_mesura_hi_entra_sencer(self):
        self.sembra_globals()
        fila = next(p for p in self.poms if p['codi'] == 'E')
        pg = POMGlobal.objects.get(codi='E')
        self.assertEqual(pg.start_point, fila['start_point'])
        self.assertEqual(pg.end_point, fila['end_point'])
        self.assertEqual(pg.reference_point, fila['reference_point'])
        self.assertEqual(pg.scope, fila['scope'])
        self.assertEqual(pg.body_section, fila['body_section'])
        self.assertEqual(pg.tol_prod_cm, fila['tol_prod_cm'])
        self.assertEqual(pg.tol_samp_cm, fila['tol_samp_cm'])

    def test_un_camp_editat_a_ma_NO_es_reescriu(self):
        self.sembra_globals()
        pg = POMGlobal.objects.get(codi='E')
        pg.nom_ca = 'REDACTAT PER UN HUMÀ'
        pg.save(update_fields=['nom_ca'])
        sortida = self.sembra_globals_sortida()
        self.assertIn('🔒', sortida)
        self.assertEqual(POMGlobal.objects.get(codi='E').nom_ca, 'REDACTAT PER UN HUMÀ')
        crida('sembra_cataleg_sistema', '--schema', self.schema, '--no-dry-run',
              '--overwrite-from-xlsx')
        self.assertNotEqual(POMGlobal.objects.get(codi='E').nom_ca, 'REDACTAT PER UN HUMÀ')

    def test_els_4_girth_entren_INACTIUS(self):
        self.sembra_globals()
        for codi in ('A1', 'A2', 'C2', 'D11'):
            self.assertFalse(POMGlobal.objects.get(codi=codi).actiu, codi)


# ── S3 ────────────────────────────────────────────────────────────────────────────────────
class S3LligamTest(BancV5):

    def setUp(self):
        super().setUp()
        self.sembra_globals()
        # Un POM de casa amb el codi de Brownie 'E' (que el r2 mapa al sistema 'E').
        self.pom = POMMaster.objects.create(codi_client='E', nom_client='Espatlla', actiu=True)

    def test_lliga_pel_mapa_del_r2(self):
        crida('lliga_fhort_al_sistema', '--schema', self.schema, '--no-dry-run')
        self.pom.refresh_from_db()
        self.assertEqual(self.pom.pom_global.codi, self.mapa['E'])

    def test_un_POM_SEPARAT_no_es_re_enganxa(self):
        """🔒 El cas que el brief demana: la sobirania mana i es mira PRIMER."""
        self.pom.separat_de_global = 'E'
        self.pom.save(update_fields=['separat_de_global'])
        sortida = crida('lliga_fhort_al_sistema', '--schema', self.schema, '--no-dry-run')
        self.pom.refresh_from_db()
        self.assertIsNone(self.pom.pom_global_id)
        self.assertIn('SOBIRÀ', sortida)
        self.assertIn('POMs sobirans respectats: 1', sortida)

    def test_un_lligam_cap_a_un_ALTRE_global_es_reporta_i_no_es_mou(self):
        altre = POMGlobal.objects.get(codi='B')
        self.pom.pom_global = altre
        self.pom.save(update_fields=['pom_global'])
        sortida = crida('lliga_fhort_al_sistema', '--schema', self.schema, '--no-dry-run')
        self.pom.refresh_from_db()
        self.assertEqual(self.pom.pom_global_id, altre.id)
        self.assertIn('NO es mou', sortida)

    def test_un_codi_HOMONIM_no_es_lliga_per_coincidencia(self):
        """🚨 El parany mesurat el 23/08: el `M` del tenant és «Leg opening» i el del v5,
        «Neck width». Mateixa lletra, mesura diferent."""
        homonim = POMMaster.objects.create(
            codi_client='M', nom_client='Leg opening', actiu=True)
        self.assertNotIn('M', self.mapa)
        sortida = crida('lliga_fhort_al_sistema', '--schema', self.schema, '--no-dry-run')
        homonim.refresh_from_db()
        self.assertIsNone(homonim.pom_global_id)
        self.assertIn('REUTILITZA aquest codi', sortida)

    def test_larxiu_no_es_lliga(self):
        self.pom.actiu = False
        self.pom.save(update_fields=['actiu'])
        crida('lliga_fhort_al_sistema', '--schema', self.schema, '--no-dry-run')
        self.pom.refresh_from_db()
        self.assertIsNone(self.pom.pom_global_id)

    def test_idempotent(self):
        crida('lliga_fhort_al_sistema', '--schema', self.schema, '--no-dry-run')
        sortida = crida('lliga_fhort_al_sistema', '--schema', self.schema, '--no-dry-run')
        self.assertIn('lligams NOUS: 0', sortida)
        self.assertIn('lligams ja fets (idempotència): 1', sortida)


# ── S4 ────────────────────────────────────────────────────────────────────────────────────
class S4AliesTest(BancV5):

    def setUp(self):
        super().setUp()
        self.sembra_globals()
        self.client_brw = Customer.objects.create(codi='BRW', nom='Brownie')
        self.pom = POMMaster.objects.create(codi_client='E', nom_client='Espatlla', actiu=True)
        crida('lliga_fhort_al_sistema', '--schema', self.schema, '--no-dry-run')

    def test_crea_lalies_del_full(self):
        crida('sembra_alies_brownie', '--schema', self.schema, '--no-dry-run')
        a = CustomerPOMAlias.objects.get(customer=self.client_brw, client_code='E')
        self.assertEqual(a.pom_id, self.pom.id)

    def test_un_alies_amb_un_altre_desti_es_reporta_i_NO_es_mou(self):
        altre = POMMaster.objects.create(codi_client='ZZ', nom_client='Un altre', actiu=True)
        CustomerPOMAlias.objects.create(customer=self.client_brw, pom=altre, client_code='E')
        sortida = crida('sembra_alies_brownie', '--schema', self.schema, '--no-dry-run')
        self.assertEqual(
            CustomerPOMAlias.objects.get(customer=self.client_brw, client_code='E').pom_id,
            altre.id)
        self.assertIn('NO es mou', sortida)

    def test_idempotent(self):
        crida('sembra_alies_brownie', '--schema', self.schema, '--no-dry-run')
        sortida = crida('sembra_alies_brownie', '--schema', self.schema, '--no-dry-run')
        self.assertIn('àlies creats: 0', sortida)
        self.assertIn('àlies ja correctes (idempotència): 1', sortida)


# ── S5 ────────────────────────────────────────────────────────────────────────────────────
class S5RemapTest(BancV5):

    def setUp(self):
        super().setUp()
        self.sembra_globals()
        self.vella = POMCategory.objects.create(codi='ZVELLA', nom_ca='La família vella')
        self.pom = POMMaster.objects.create(codi_client='E', nom_client='Espatlla',
                                            actiu=True, categoria=self.vella)
        crida('lliga_fhort_al_sistema', '--schema', self.schema, '--no-dry-run')

    def remapa(self, cat_esborrades=0):
        return crida('remap_families_fhort', '--schema', self.schema, '--no-dry-run',
                     '--espera', f'CAT-* buides esborrades={cat_esborrades}')

    def test_remapa_per_la_fila_del_r2(self):
        self.remapa()
        self.pom.refresh_from_db()
        fam = next(p['familia'] for p in self.poms if p['codi'] == self.mapa['E'])
        self.assertEqual(self.pom.categoria.codi, fam)

    def test_larxiu_no_es_reescriu(self):
        self.pom.actiu = False
        self.pom.save(update_fields=['actiu'])
        self.remapa()
        self.pom.refresh_from_db()
        self.assertEqual(self.pom.categoria_id, self.vella.id)

    def test_una_CAT_buida_es_esborra_i_una_AMB_POMs_no(self):
        POMCategory.objects.create(codi='CAT-BUIDA', nom_ca='buida')
        amb = POMCategory.objects.create(codi='CAT-UB', nom_ca='amb POMs')
        POMMaster.objects.create(codi_client='ZZ', nom_client='resident', actiu=False,
                                 categoria=amb)
        sortida = self.remapa(cat_esborrades=1)
        self.assertFalse(POMCategory.objects.filter(codi='CAT-BUIDA').exists())
        self.assertTrue(POMCategory.objects.filter(codi='CAT-UB').exists())
        self.assertIn('NO s\'esborra', sortida)

    def test_idempotent(self):
        self.remapa()
        sortida = self.remapa()
        self.assertIn('POMs remapats: 0', sortida)


# ── S6 ────────────────────────────────────────────────────────────────────────────────────
class S6TancamentTest(BancV5):

    def test_reactiva_per_CODI_i_no_per_pk(self):
        """El brief els cita com 462/463 (PROD); aquí les pks són unes altres i el cas passa
        igual, que és exactament el que la llei R-POM demana."""
        s = POMMaster.objects.create(codi_client='S', nom_client='Front armhole', actiu=False)
        s2 = POMMaster.objects.create(codi_client='S2', nom_client='Back armhole', actiu=False)
        self.assertNotIn(s.pk, (462, 463))
        sortida = crida('tancament_142', '--schema', self.schema, '--no-dry-run')
        s.refresh_from_db()
        s2.refresh_from_db()
        self.assertTrue(s.actiu)
        self.assertTrue(s2.actiu)
        self.assertIn('POMs reactivats: 2', sortida)

    def test_la_familia_no_sendevina(self):
        POMMaster.objects.create(codi_client='S2', nom_client='Back armhole', actiu=False)
        sortida = crida('tancament_142', '--schema', self.schema, '--no-dry-run',
                        '--espera', 'POMs del tancament trobats=1')
        self.assertIn('NO s\'endevina', sortida)

    def test_el_duplicat_SF_es_ANOTA_i_no_es_fusiona(self):
        a = POMMaster.objects.create(codi_client='SF', nom_client='Armhole depth', actiu=True)
        b = POMMaster.objects.create(codi_client='SFB', nom_client='AH DEP', actiu=True)
        sortida = crida('tancament_142', '--schema', self.schema, '--no-dry-run',
                        '--espera', 'POMs del tancament trobats=0')
        self.assertIn('FUSIÓ PENDENT', sortida)
        self.assertTrue(POMMaster.objects.filter(pk__in=(a.pk, b.pk)).count() == 2)


# ── S7 ────────────────────────────────────────────────────────────────────────────────────
class S7FinestraTest(BancV5):

    def _model_amb_fk(self, joc):
        from fhort.models_app.models import Model
        return Model.objects.create(codi_intern='QA-S7', any=2026, sequencial=1,
                                    grading_rule_set=joc)

    def _joc(self, nom):
        return GradingRuleSet.objects.create(nom=nom, actiu=True)

    def finestra(self, talls, arxivats, *extra):
        return crida('finestra_graduacio', '--schema', self.schema, '--no-dry-run',
                     '--espera', f'models amb FK de graduació tallada={talls}',
                     '--espera', f'jocs arxivats={arxivats}', *extra)

    def test_arxiva_els_condemnats_i_NO_esborra_res(self):
        supervivent = self._joc('GRADING BROWNIE 2026')
        condemnat = self._joc('UN JOC VELL')
        self.finestra(0, 1)
        supervivent.refresh_from_db()
        condemnat.refresh_from_db()
        self.assertTrue(supervivent.actiu)
        self.assertFalse(condemnat.actiu)
        self.assertEqual(GradingRuleSet.objects.count(), 2)

    def test_sense_supervivent_ATURA(self):
        self._joc('UN JOC QUE NINGÚ CONEIX')
        with self.assertRaises(CommandError) as e:
            self.finestra(0, 0)
        self.assertIn('els arxivaria TOTS', str(e.exception))

    def test_sense_condemnats_no_talla_cap_FK_sense_el_flag(self):
        joc = self._joc('GRADING BROWNIE 2026')
        m = self._model_amb_fk(joc)
        sortida = self.finestra(0, 0)
        m.refresh_from_db()
        self.assertIsNotNone(m.grading_rule_set_id)
        self.assertIn('no és el no-op', sortida)

    def test_una_FK_INERTA_es_talla(self):
        joc = self._joc('GRADING BROWNIE 2026')
        m = self._model_amb_fk(joc)
        self.finestra(1, 0, '--talla-fk-sense-condemna')
        m.refresh_from_db()
        self.assertIsNone(m.grading_rule_set_id)

    def test_una_FK_que_NO_es_inerta_ATURA_LA_FINESTRA_SENCERA(self):
        """🚨 El número del brief es RE-MESURA. Si el contenidor cobreix una cel·la que cap
        resident no cobreix, tallar-lo la perdria: no es talla res i no s'arxiva res."""
        from fhort.models_app.models import BaseMeasurement
        from fhort.pom.models import SizeDefinition, SizeSystem
        ss = SizeSystem.objects.create(codi='QA-S7-SS', nom='QA')
        base = SizeDefinition.objects.create(size_system=ss, etiqueta='M', ordre=1)
        joc = self._joc('GRADING BROWNIE 2026')
        condemnat = self._joc('UN JOC VELL')
        m = self._model_amb_fk(joc)
        self.sembra_globals()
        pom = POMMaster.objects.create(codi_client='E', nom_client='Espatlla', actiu=True)
        BaseMeasurement.objects.create(model=m, pom=pom, base_value_cm=40)
        GradingRule.objects.create(rule_set=joc, pom=pom, talla_base=base,
                                   logica='FIXED', actiu=True)
        with self.assertRaises(CommandError) as e:
            self.finestra(0, 1, '--talla-fk-sense-condemna')
        self.assertIn('RE-MESURA', str(e.exception))
        m.refresh_from_db()
        condemnat.refresh_from_db()
        self.assertIsNotNone(m.grading_rule_set_id)
        self.assertTrue(condemnat.actiu)


# ── La llei de motor ──────────────────────────────────────────────────────────────────────
class LleiGirthTest(BancV5):

    def test_cap_comanda_del_tram_crea_cap_regla_de_graduacio(self):
        """⚖️ «cap comanda crea NI CREARÀ regles de graduació sobre una instància @girth». El
        tram sencer no en crea CAP, ni de @girth ni de cap altra: la prova és el recompte."""
        Customer.objects.create(codi='BRW', nom='Brownie')
        POMMaster.objects.create(codi_client='E', nom_client='Espatlla', actiu=True)
        abans = GradingRule.objects.count()
        crida('sembra_families_sistema', '--no-dry-run')
        self.sembra_globals()
        crida('lliga_fhort_al_sistema', '--schema', self.schema, '--no-dry-run')
        crida('sembra_alies_brownie', '--schema', self.schema, '--no-dry-run')
        crida('remap_families_fhort', '--schema', self.schema, '--no-dry-run',
              '--espera', 'CAT-* buides esborrades=0')
        crida('tancament_142', '--schema', self.schema, '--no-dry-run',
              '--espera', 'POMs del tancament trobats=0')
        crida('finestra_graduacio', '--schema', self.schema, '--no-dry-run',
              '--espera', 'models amb FK de graduació tallada=0',
              '--espera', 'jocs arxivats=0')
        self.assertEqual(GradingRule.objects.count(), abans)
