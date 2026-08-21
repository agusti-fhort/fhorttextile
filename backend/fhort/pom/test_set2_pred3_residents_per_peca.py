"""SET-2/PRED-3 — «té residents?» deixa de ser una pregunta del MODEL (2026-08-12).

Tercer membre de la família censada el 12/08: **cada cop que una pantalla —o un motor— entra
al patró de peces, hi ha un predicat de MODEL que s'hi cola i no canta en vermell.** Aquest és
el del motor, i el que decideix és si el **contenidor del client** es llegeix o no.

EL DANY, i la direcció importa perquè és la contrària de la que sembla:

  · mare amb residents + 02 SENSE → la 02 **hereta** la de la mare. Ja era correcte (D5-bis)
    i aquest tram no ho toca. Aquí es vigila que segueixi sent-ho.
  · **02 amb residents + mare SENSE** → `rules.exists()` sobre tot el model deia que sí, el
    contenidor no es llegia MAI, i la mare queia a `rule is None` → **llei de cel·la absent:
    cap cel·la**. La graduació de la mare desapareixia sencera i només en quedava un avís de
    «cobertura parcial». És l'estat que fabrica l'import per prenda (SET-2/T8) quan la mare
    gradua pel catàleg del client.

⚠️ **EL SUBJECTE DEL PREDICAT NO ÉS LA PEÇA, ÉS LA MARE**, i la diferència no és estètica: el
contenidor no pot portar garment i quan entra ho fa SEMPRE com a llei de la peça mare.
Preguntar «en té AQUESTA peça?» confondria els dos estats que D5-bis separa —«no en té»
(hereta) i «ningú no en té» (contenidor)— i faria baixar el catàleg per a una filla que el que
ha de fer és heretar de la seva mare.

El control d'una sola prenda és tan important com el vermell: amb els residents tots a `''`
—el 100% del corpus d'avui— el predicat ha de valer exactament el que valia.
"""
# FIX-A/PAS-1c (21/08) — les fixtures d'aquest fitxer construïen la regla LINEAR amb el
# camp LLEGAT `increment`. Funcionava perquè el motor hi queia per fallback; des que el
# fallback no hi és (`_apply_rule`, llei D2), una regla sense `increment_base` NO gradua i
# no emet cap cel·la. El SUBJECTE d'aquestes proves no és el camp sinó el que hi ha a
# sobre (germanes, peces, transacció), o sigui que la fixture passa al camp que mana i
# CAP asserció es toca: si alguna hagués canviat de valor, el canvi no seria de fixture.
import contextlib
import datetime

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.accounts.models import UserProfile
from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.pom.models import (GradingRule, GradingRuleSet, POMMaster, SizeDefinition,
                              SizeSystem)

MARE = ''
SEGONA = '02'
TAULES = ('models_app_basemeasurement', 'models_app_modelgradingrule', 'fitting_gradedspec',
          'models_app_measurementchangelog')


@contextlib.contextmanager
def comportes_garment_alcades(*taules):
    """Alça les comportes `*_garment_gate_set2` dins d'un savepoint que SEMPRE es desfà.

    Des del #12 (12/08) les comportes ja no hi són i això és un no-op; es conserva perquè el
    banc segueixi corrent igual si una comporta tornés, i perquè és el patró d'aquest fitxer
    germà (`test_set2_t4_motor_per_garment`).
    """
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            for taula in taules:
                cur.execute(
                    f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                    f'DROP CONSTRAINT IF EXISTS "{taula}_garment_gate_set2"'
                )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class _BasePred3Test(TenantTestCase):
    """Un model amb sistema S·M·L, base M, i un contenidor de client a punt d'entrar."""

    CODI = 'TST-PRED3'

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
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.ss = SizeSystem.objects.create(codi=f'SS_{self.CODI}', nom='SS PRED3',
                                            base_unit='ALPHA')
        self.talles = {}
        for i, et in enumerate(['S', 'M', 'L']):
            self.talles[et] = SizeDefinition.objects.create(
                size_system=self.ss, etiqueta=et, ordre=i)
        self.model = Model.objects.create(
            codi_intern=self.CODI, codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_system=self.ss, size_run_model='S·M·L',
            base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username=f'qa_{self.CODI}', defaults={'email': 'qa@pred3.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA PRED3', 'rol_nom': 'QA'})
        from fhort.fitting.models import SizeFitting
        self.sf, _ = SizeFitting.objects.get_or_create(
            model=self.model, numero=1,
            defaults={'codi': f'SF-{self.CODI}', 'tipus': 'SizeSet', 'estat': 'Pendent',
                      'creat_per': self.perfil},
        )

    # ── bastida ───────────────────────────────────────────────────────────────
    def _contenidor(self, increment=5.0):
        """El catàleg del client: NO porta garment i no en pot portar."""
        grs = GradingRuleSet.objects.create(nom='Catàleg PRED3', size_system=self.ss,
                                            actiu=True)
        GradingRule.objects.create(rule_set=grs, pom=self.pom, talla_base=self.talles['M'],
                                   logica='LINEAR', increment_base=increment, actiu=True)
        self.model.grading_rule_set = grs
        self.model.save(update_fields=['grading_rule_set'])
        return grs

    def _base(self, garment, valor):
        return BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=valor, ordre=1,
            nom_fitxa=f'A-{garment or "MARE"}', garment=garment)

    def _resident(self, garment, increment):
        return ModelGradingRule.objects.create(
            model=self.model, pom=self.pom, logica='LINEAR', increment_base=increment,
            actiu=True, garment=garment)

    def _specs(self):
        from fhort.fitting.models import GradedSpec
        from fhort.fitting.services import vigent_grading_version
        gv = vigent_grading_version(self.sf.pk)
        return {(s.garment, s.size_label): s.graded_value_cm
                for s in GradedSpec.objects.filter(grading_version=gv, pom=self.pom,
                                                   is_active=True)}


class ElVermellTest(_BasePred3Test):
    """02 amb residents + mare SENSE: la mare ha de seguir graduant pel contenidor."""

    CODI = 'TST-PRED3A'

    def test_els_residents_d_una_filla_no_apaguen_el_contenidor_de_la_mare(self):
        """EL VERMELL DEL TRAM.

        Increments ben distints (contenidor +5, resident de la 02 +10) perquè si les lleis es
        col·lapsessin la fila no fallaria per un decimal. El que abans passava no era una
        xifra dolenta: era **cap fila** per a la mare.
        """
        from fhort.pom.services import generate_graded_specs

        with comportes_garment_alcades(*TAULES):
            self._contenidor(increment=5.0)
            self._base(MARE, 100.0)
            self._base(SEGONA, 50.0)
            self._resident(SEGONA, 10.0)      # NOMÉS la filla en té

            generate_graded_specs(self.sf.pk)

            self.assertEqual(self._specs(), {
                # La mare, pel CATÀLEG (+5). Abans d'aquest tram: cap d'aquestes tres files.
                (MARE, 'S'): 95.0, (MARE, 'M'): 100.0, (MARE, 'L'): 105.0,
                # La filla, per la SEVA regla (+10).
                (SEGONA, 'S'): 40.0, (SEGONA, 'M'): 50.0, (SEGONA, 'L'): 60.0,
            })

    def test_la_font_serveix_les_dues_lleis_alhora(self):
        """El predicat, mirat de prop: el `return` excloent s'ha convertit en `update`.

        Abans les dues branques s'excloïen per força —o residents o catàleg— i és aquella
        exclusió la que deixava la mare muda. Ara conviuen, cadascuna a la seva clau.
        """
        from fhort.pom.services import _load_grading_rules_per_garment, _regla_de

        with comportes_garment_alcades(*TAULES):
            self._contenidor(increment=5.0)
            self._resident(SEGONA, 10.0)

            rules = _load_grading_rules_per_garment(self.model)

            # FIX-A/PAS-1c — el DISCRIMINADOR passa a `increment_base`. Aquest test no mesura
            # cap camp: mesura QUINA regla torna `_regla_de` per a cada peça, i el delta només
            # hi és per distingir-les. Amb la fixture al camp canònic, el llegat val el default
            # del model (0.00) i deixaria de distingir res.
            self.assertEqual(float(_regla_de(rules, self.pom.id, MARE).increment_base), 5.0)
            self.assertEqual(float(_regla_de(rules, self.pom.id, SEGONA).increment_base), 10.0)


class LHerenciaNoCanviaTest(_BasePred3Test):
    """L'altra direcció —la benigna— ha de seguir exactament com estava."""

    CODI = 'TST-PRED3B'

    def test_una_peca_sense_llei_propia_HERETA_la_de_la_mare(self):
        """D5-bis: «no en té» vol dir HERETA, no «baixa el catàleg per mi».

        Amb la mare amb residents, el contenidor NO ha d'entrar per a ningú —ni per a la
        filla—: la llei de la mare mana i la filla l'hereta. Si el predicat hagués passat a
        preguntar «en té aquesta peça?», la 02 hauria graduat a +5 (catàleg) en comptes de
        +1 (la llei de la seva mare), i això seria una segona veritat dins del mateix model.
        """
        from fhort.pom.services import generate_graded_specs

        with comportes_garment_alcades(*TAULES):
            self._contenidor(increment=5.0)
            self._base(MARE, 100.0)
            self._base(SEGONA, 50.0)
            self._resident(MARE, 1.0)         # NOMÉS la mare en té

            generate_graded_specs(self.sf.pk)

            self.assertEqual(self._specs(), {
                (MARE, 'S'): 99.0, (MARE, 'M'): 100.0, (MARE, 'L'): 101.0,
                # HERETADA de la mare (+1), NO del catàleg (+5).
                (SEGONA, 'S'): 49.0, (SEGONA, 'M'): 50.0, (SEGONA, 'L'): 51.0,
            })


class ControlUnaSolaPrendaTest(_BasePred3Test):
    """EL CONTROL. Amb una sola prenda el predicat ha de valer el que valia."""

    CODI = 'TST-PRED3C'

    def test_els_residents_de_la_mare_manen_i_el_contenidor_no_entra(self):
        """El comportament de sempre, byte a byte: amb residents al model, el catàleg calla."""
        from fhort.pom.services import generate_graded_specs

        self._contenidor(increment=5.0)
        self._base(MARE, 100.0)
        self._resident(MARE, 1.0)

        generate_graded_specs(self.sf.pk)

        self.assertEqual(self._specs(), {
            (MARE, 'S'): 99.0, (MARE, 'M'): 100.0, (MARE, 'L'): 101.0,
        })

    def test_sense_cap_resident_gradua_el_contenidor(self):
        """L'altra meitat del control: sense residents, el catàleg segueix entrant."""
        from fhort.pom.services import generate_graded_specs

        self._contenidor(increment=5.0)
        self._base(MARE, 100.0)

        generate_graded_specs(self.sf.pk)

        self.assertEqual(self._specs(), {
            (MARE, 'S'): 95.0, (MARE, 'M'): 100.0, (MARE, 'L'): 105.0,
        })
