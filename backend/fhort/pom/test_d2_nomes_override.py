"""D2 · POM NOMÉS-OVERRIDE — la sobirania del model (decisió Agus 2026-07-22).

Un import sobre un contenidor de client que JA té regles no toca el contenidor (llei M3,
INTOCABLE): els POMs que el contenidor no cobreix (`amplia`) o que hi divergeixen
(`conflicte`) es desen com a `BaseMeasurement` + `ModelGradingOverride` per-talla
(`models_app/extraction_views.py`, bloc del contenidor amb regles).

Aquests POMs NO tenen regla —ni resident ni de set—, i el motor els travessava per
`elif rule is None: continue`. Resultat: emetien les talles amb override però **no la
talla BASE**, l'única que mai és override (l'import l'exclou explícitament perquè el seu
valor viu a `BaseMeasurement`). La fila sortia coixa: graduada a tot arreu menys al
centre.

LLEI D2: els overrides per-talla SÓN la regla efectiva del POM. A la talla base la font
és el valor base del model. Una talla del run sense override segueix sent **cel·la
absent** (mai un valor fabricat).

⚠️ PARITAT: el canvi només AFEGEIX cel·les a POMs sense regla I amb almenys un override.
Un model sense cap `ModelGradingOverride` es gradua exactament igual que abans —
`ParitatSenseOverridesTest` ho fixa.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
from fhort.models_app.models import (
    BaseMeasurement, Model, ModelGradingOverride, ModelGradingRule,
)
from fhort.pom.models import MeasurementLayer, POMMaster, SizeDefinition, SizeSystem
from fhort.pom.services import generate_graded_specs, preview_graded_specs


class _D2Base(TenantTestCase):
    """Un model amb run XXS·XS·S·M·L, base S, i dos POMs:

      · `pom_regla`   — regla resident LINEAR +1 (el cas «heretat del contenidor»)
      · `pom_ovr`     — CAP regla, només overrides per-talla (el cas `amplia`/`conflicte`)
    """

    RUN = ['XXS', 'XS', 'S', 'M', 'L']
    BASE = 'S'

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
        self.user = get_user_model().objects.create(username='d2')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'D2', 'rol_nom': 'admin'})

        self.ss = SizeSystem.objects.create(codi='SS_D2', nom='SS D2', base_unit='ALPHA')
        for i, et in enumerate(self.RUN):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)

        self.pom_regla = POMMaster.objects.create(codi_client='A', nom_client='Chest')
        self.pom_ovr = POMMaster.objects.create(codi_client='D1', nom_client='Sleeve')

        self.model = Model.objects.create(
            codi_intern='TST-D2', codi_tenant='TST', any=2026, sequencial=1,
            nom_prenda='Test', size_system=self.ss,
            size_run_model='·'.join(self.RUN), base_size_label=self.BASE,
        )
        # Un signal de `Model` ja sembra el SizeFitting numero=1: reutilitzar-lo, no duplicar.
        self.sf = SizeFitting.objects.filter(model=self.model).order_by('numero').first()
        if self.sf is None:
            self.sf = SizeFitting.objects.create(
                model=self.model, numero=1, codi='SF-D2', tipus='SizeSet',
                estat='Pendent', creat_per=self.profile,
            )

        # POM amb regla: base 100, LINEAR +1 per talla.
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_regla, base_value_cm=100.0, is_active=True, ordre=0)
        ModelGradingRule.objects.create(
            model=self.model, pom=self.pom_regla, logica='LINEAR', increment_base=1.0, actiu=True)

        # POM només-override: base 58.5 + overrides a les 4 talles NO base (com escriu
        # l'import: la talla base mai és override).
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_ovr, base_value_cm=58.5, is_active=True, ordre=1)
        for label, val in (('XXS', 53.5), ('XS', 55.5), ('M', 61.5), ('L', 64.5)):
            ModelGradingOverride.objects.create(
                model=self.model, pom=self.pom_ovr, size_label=label, value_cm=val,
                created_by=self.profile, motiu='Import W5 — test D2')

    def _taula(self, pom):
        gv = GradingVersion.objects.filter(
            size_fitting=self.sf, is_active=True).order_by('-version_number').first()
        return {s.size_label: s.graded_value_cm
                for s in GradedSpec.objects.filter(grading_version=gv, pom=pom)}


class PomNomesOverrideGraduaTest(_D2Base):

    def test_el_pom_nomes_override_gradua_el_run_sencer(self):
        """El cas Meredith D1: 53.5/55.5/58.5/61.5/64.5 — la base inclosa."""
        generate_graded_specs(self.sf.id)
        self.assertEqual(
            self._taula(self.pom_ovr),
            {'XXS': 53.5, 'XS': 55.5, 'S': 58.5, 'M': 61.5, 'L': 64.5},
        )

    def test_la_talla_base_surt_del_valor_base_del_model(self):
        """La cel·la que faltava. Increment 0: la base no es desplaça d'ella mateixa."""
        generate_graded_specs(self.sf.id)
        gv = GradingVersion.objects.filter(size_fitting=self.sf, is_active=True).first()
        spec = GradedSpec.objects.get(grading_version=gv, pom=self.pom_ovr, size_label='S')
        self.assertEqual(spec.graded_value_cm, 58.5)
        self.assertEqual(spec.increment_applied_cm, 0.0)
        # Provinença honesta: la font és el model (override/excepció), no una regla.
        self.assertEqual(spec.grading_type_applied, 'EXCEPTION')

    def test_el_pom_amb_regla_no_es_veu_afectat(self):
        generate_graded_specs(self.sf.id)
        self.assertEqual(
            self._taula(self.pom_regla),
            {'XXS': 98.0, 'XS': 99.0, 'S': 100.0, 'M': 101.0, 'L': 102.0},
        )

    def test_preview_diu_el_mateix_que_el_generador(self):
        """El wizard no pot ensenyar una taula que el generador després no reprodueix.

        C3/B (2026-08-02) — la clau del preview ha crescut de `pom_id` a la identitat sencera
        `(pom_id, capa, instancia)`, alhora que la del generador, perquè si només en creixés una
        aquest assert deixaria de tenir sentit. L'ENTRADA segueix acceptant claus escalars (és
        el que li arriba del wizard d'importació, en JSON, que no pot expressar tuples) i es
        normalitza a la mesura única del POM; el que canvia és com s'indexa la SORTIDA.
        El que el test defensa —que preview i generador diuen el mateix— no s'ha tocat.
        """
        generate_graded_specs(self.sf.id)
        prev = preview_graded_specs(
            self.model, {self.pom_regla.id: 100.0, self.pom_ovr.id: 58.5})
        unica = (MeasurementLayer.SLUG_DEFECTE, '')
        self.assertEqual(prev[(self.pom_ovr.id, *unica)], self._taula(self.pom_ovr))
        self.assertEqual(prev[(self.pom_regla.id, *unica)], self._taula(self.pom_regla))


class CelLaAbsentTest(_D2Base):
    """La llei de cel·la absent no s'afluixa: només la BASE es rescata."""

    def test_talla_sense_override_segueix_absent(self):
        ModelGradingOverride.objects.filter(model=self.model, size_label='M').delete()
        generate_graded_specs(self.sf.id)
        taula = self._taula(self.pom_ovr)
        self.assertNotIn('M', taula)            # cap valor fabricat
        self.assertEqual(taula['S'], 58.5)      # la base sí

    def test_pom_sense_regla_i_sense_override_no_emet_res(self):
        pom_orfe = POMMaster.objects.create(codi_client='Z', nom_client='Orfe')
        BaseMeasurement.objects.create(
            model=self.model, pom=pom_orfe, base_value_cm=42.0, is_active=True, ordre=2)
        generate_graded_specs(self.sf.id)
        self.assertEqual(self._taula(pom_orfe), {})


class LaTracaDeCoberturaParcialNoMenteixTest(_D2Base):
    """SET-2/T6a (2026-08-11) — un POM només-override NO és «sense regla», i la traça ho ha de dir.

    `sense_regla` no mou cap cel·la: les dues branques del `rule is None` acaben igual amb un
    `continue`. El que decideix és l'avís de COBERTURA PARCIAL (`pom/services.py`, «N POM(s)
    amb mesura base i sense regla»), que és el rastre que la llei D2 va posar precisament
    perquè el silenci era el bug. Un avís que compta POMs ben coberts és el mateix silenci amb
    una altra disfressa: qui el llegeixi anirà a buscar una regla que no falta.

    Va quedar trencat perquè `_poms_amb_override` va passar a claus de quatre trams a
    SET-2/T4 i aquesta comparació es va quedar amb tres — la SEGONA PORTA del dany que
    `31e05db7` va tancar a `_load_grading_rules` i a `_identitat`. Cap assert de valors el
    podia veure, i per això el pin mira els LOGS i no la taula.
    """

    LOGGER = 'fhort.pom.services'

    def _pom_nomes_override_PARCIAL(self):
        """Un POM sense regla amb override a UNA talla, no a totes. És el cas que cal.

        ⚠️ El `pom_ovr` del fixture compartit NO serveix per a aquest pin, i la primera versió
        d'aquest test el feia servir: té override a TOTES les talles no-base i la base la
        cobreix el rescat de D2, o sigui que les seves cel·les surten totes per les branques
        de l'override i **no arriba mai** a la branca `rule is None` on viu el predicat. El
        mutant (tornar la comparació a tres trams) hi va SOBREVIURE, i el defecte era del
        test: no exercia la línia que deia vigilar.

        Amb override només a XXS, les talles XS/M/L sí que hi cauen — que és exactament el
        cas que el comentari de `services.py` descriu: «segueix valent per a les talles del
        run que el POM només-override no cobreix».
        """
        pom = POMMaster.objects.create(codi_client='P1', nom_client='Parcial')
        BaseMeasurement.objects.create(
            model=self.model, pom=pom, base_value_cm=30.0, is_active=True, ordre=3)
        ModelGradingOverride.objects.create(
            model=self.model, pom=pom, size_label='XXS', value_cm=28.0,
            created_by=self.profile, motiu='Import W5 — cobertura parcial')
        return pom

    def test_un_pom_nomes_override_no_compta_com_a_sense_regla(self):
        # Cobert per override a XXS i per la base: les altres tres talles són cel·la absent
        # LEGÍTIMA, no manca de regla. No ha de sortir a la traça de cobertura parcial.
        self._pom_nomes_override_PARCIAL()
        with self.assertNoLogs(self.LOGGER, level='WARNING'):
            generate_graded_specs(self.sf.id)

    def test_el_cas_de_control_SI_que_hi_entra(self):
        """El control ha de TRENCAR la coincidència: sense ell el test de dalt passaria igual
        amb l'avís desactivat del tot. Un POM amb base i sense CAP override ni regla sí que és
        cobertura parcial, i ha de sortir a la traça amb el seu id."""
        pom_mut = POMMaster.objects.create(codi_client='Z9', nom_client='Mut')
        BaseMeasurement.objects.create(
            model=self.model, pom=pom_mut, base_value_cm=42.0, is_active=True, ordre=2)

        with self.assertLogs(self.LOGGER, level='WARNING') as capturat:
            generate_graded_specs(self.sf.id)

        traca = '\n'.join(capturat.output)
        self.assertIn('sense regla', traca)
        # ⚠️ La LLISTA sencera, no `assertIn(id)` ni `assertNotIn(id)` sobre el text pelat: la
        # primera versió d'aquest assert feia `assertNotIn(str(self.pom_ovr.id), traca)` amb
        # l'id 2 i queia contra el «D2» de «llei D2 de cel·la absent». Un id d'una xifra dins
        # d'una frase que parla de la llei D2 casa amb qualsevol cosa; el que s'ha de fixar és
        # el conjunt que l'avís publica.
        self.assertIn(f'POMs: [{pom_mut.id}]', traca)   # només ell: ni dos ids, ni el només-override
        self.assertIn('1 POM(s)', traca)


class ParitatSenseOverridesTest(_D2Base):
    """⚠️ CONDICIÓ DURA del sprint: sense overrides, el motor no ha canviat gens."""

    def test_model_sense_overrides_gradua_exactament_igual(self):
        ModelGradingOverride.objects.filter(model=self.model).delete()
        n = generate_graded_specs(self.sf.id)
        # Només el POM amb regla emet: 5 cel·les. El només-override, ara sense overrides,
        # torna a ser un POM sense regla → cap cel·la (comportament de sempre).
        self.assertEqual(n, 5)
        self.assertEqual(self._taula(self.pom_ovr), {})
        self.assertEqual(
            self._taula(self.pom_regla),
            {'XXS': 98.0, 'XS': 99.0, 'S': 100.0, 'M': 101.0, 'L': 102.0},
        )
