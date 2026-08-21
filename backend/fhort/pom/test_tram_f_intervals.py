"""TRAM F · MULTI-BREAK PER INTERVALS — el motor, la porta i l'equivalència (2026-08-21).

Tres coses, i la primera mana sobre les altres dues:

  ① **EQUIVALÈNCIA.** Tota regla d'1 break llegida com a interval `[talla_break_label ..
     última talla]` ha de donar EXACTAMENT la mateixa taula que abans. El banc 1383 ho mesura
     sobre dades vives (A=105 · B=525); aquí es fixa sobre la geometria, que és el que un banc
     de dades no pot fer: runs amb forat, break a la primera talla, break fora del run, break
     sense delta. Si això es trenca, el que s'ha mogut és la LLEI, no un número.
  ② **LA SEMÀNTICA NOVA** — el cas de la Montse: general 2 · `S→L` 3 vol dir S→M 3 **i** M→L 3,
     i XL torna a 2. El delta és entre talles CONSECUTIVES, i l'aresta pren el delta de
     l'interval que conté el seu EXTREM EXTERIOR.
  ③ **LES PORTES.** `valida_breaks` és el punt únic de les quatre, i el deute LINEAR+0 amb
     break (defecte 4 de la diagnosi de PROD) es tanca amb ell.

🔑 ELS DOS NODES, SEMPRE JUNTS. Cada cas de graduació es mesura pels DOS camins —`_apply_rule`
(Escalat/GradedSpec) i `propaga_ancoratges` (la presa)— perquè la lliçó del fix A és que un
node canviat sol fa divergir les dues pantalles EN SILENCI. És el mateix contracte que el bloc
C del banc, aquí sobre geometria sintètica.
"""
import datetime
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.pom.grading_regime import (
    MAX_BREAKS, es_linear_degenerada, intervals_en_index, valida_breaks,
)
from fhort.pom.grading_utils import intervals_de, propaga_ancoratges
from fhort.pom.services import _apply_rule

SISTEMA = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']   # ALPHA_EU_W
BASE_VAL = 100.0


def _rule(**kw):
    base = dict(logica='LINEAR', increment=None, increment_base=None, increment_break=None,
                talla_break_label=None, talla_break_pos=None, valors_step=None, breaks=None,
                pom=None, pom_id=1)
    base.update(kw)
    return SimpleNamespace(**base)


def _taula_escalat(rule, run_model, base='S', sistema=SISTEMA):
    """La corba pel camí ① (el que emet `GradedSpec`)."""
    pos = {e: i for i, e in enumerate(sistema)}
    base_idx = pos[base]
    out = {}
    for label in sorted(run_model, key=lambda l: pos[l]):
        i = pos[label]
        val, _ = _apply_rule(rule, BASE_VAL, i - base_idx, i, base_idx,
                             size_run=sistema, warnings=[])
        out[label] = None if val is None else round(val, 2)
    return out


def _taula_presa(rule, run_model, base='S', sistema=SISTEMA):
    """La MATEIXA corba pel camí ② (el que serveix la presa), ancorada a la BASE."""
    vals = propaga_ancoratges(rule, base, BASE_VAL, run_model,
                              run_sistema=sistema, base_label=base)
    return {k: (None if v is None else round(v, 2)) for k, v in vals.items()}


class EquivalenciaUnBreakIntervalTest(SimpleTestCase):
    """① La migració que NO s'ha fet: llegir el break d'1 tram com un interval."""

    RUN = ['XS', 'S', 'M', 'L', 'XL']

    def _dos_costats(self, vell, nou, run=None, base='S'):
        run = run or self.RUN
        for camí, taula in (('escalat', _taula_escalat), ('presa', _taula_presa)):
            self.assertEqual(
                taula(vell, run, base), taula(nou, run, base),
                f"[{camí}] la forma d'intervals NO reprodueix el break d'1 tram")

    def test_break_al_mig_els_dos_camins(self):
        """El cas A/C del banc: ib=2 · brk=3 · break M ≡ general 2 · [M..3XL] 3."""
        vell = _rule(increment_base=2.0, increment_break=3.0, talla_break_label='M')
        nou = _rule(increment_base=2.0, breaks=[{'inici': 'M', 'final': '3XL', 'delta': 3.0}])
        self._dos_costats(vell, nou)
        # I la taula és la que el banc va mesurar: −2.0 avall, +3.0 amunt des de la base.
        self.assertEqual(_taula_escalat(nou, self.RUN),
                         {'XS': 98.0, 'S': 100.0, 'M': 103.0, 'L': 106.0, 'XL': 109.0})

    def test_sostre_brk_zero(self):
        """`brk=0` (el sostre) no és cap cas a part: és un interval amb delta 0."""
        vell = _rule(increment_base=0.5, increment_break=0.0, talla_break_label='L')
        nou = _rule(increment_base=0.5, breaks=[{'inici': 'L', 'final': '3XL', 'delta': 0.0}])
        self._dos_costats(vell, nou)
        self.assertEqual(_taula_escalat(nou, self.RUN),
                         {'XS': 99.5, 'S': 100.0, 'M': 100.5, 'L': 100.5, 'XL': 100.5})

    def test_break_PER_SOTA_de_la_base(self):
        """L'extrem exterior baixant és l'etiqueta INFERIOR (llei RS146/E2, model 205)."""
        vell = _rule(increment_base=1.0, increment_break=1.5, talla_break_label='XS')
        nou = _rule(increment_base=1.0, breaks=[{'inici': 'XS', 'final': '3XL', 'delta': 1.5}])
        self._dos_costats(vell, nou, run=['XXS', 'XS', 'S', 'M'])
        self.assertEqual(_taula_escalat(nou, ['XXS', 'XS', 'S', 'M']),
                         {'XXS': 97.5, 'XS': 98.5, 'S': 100.0, 'M': 101.5})

    def test_run_amb_FORAT(self):
        """S24b: el camí es recorre sobre el SISTEMA, i l'equivalència també."""
        vell = _rule(increment_base=2.0, increment_break=3.0, talla_break_label='M')
        nou = _rule(increment_base=2.0, breaks=[{'inici': 'M', 'final': '3XL', 'delta': 3.0}])
        self._dos_costats(vell, nou, run=['XS', 'S', 'L'])
        self.assertEqual(_taula_escalat(nou, ['XS', 'S', 'L']),
                         {'XS': 98.0, 'S': 100.0, 'L': 106.0})

    def test_etiqueta_forana_no_trenca_res(self):
        """Un interval que comença a una talla que el sistema no té s'IGNORA, com el break."""
        vell = _rule(increment_base=2.0, increment_break=3.0, talla_break_label='42')
        nou = _rule(increment_base=2.0, breaks=[{'inici': '42', 'final': '3XL', 'delta': 3.0}])
        self._dos_costats(vell, nou)
        # XL és a TRES arestes de la base (S→M→L→XL) en espai de sistema: 100 + 3×2.
        self.assertEqual(_taula_escalat(nou, self.RUN)['XL'], 106.0, 'ha de graduar uniforme')

    def test_L_OFF_BY_ONE_QUE_NO_S_HA_FET(self):
        """🚨 L'esmena del 21/08: la BD desa la convenció de MOTOR i l'etiqueta NO es desplaça.

        Si algú «tradueix» l'etiqueta en migrar, la corba es mou una talla sencera. Aquest test
        fixa la diferència perquè el dia que algú ho torni a proposar, la vegi.
        """
        vell = _rule(increment_base=2.0, increment_break=3.0, talla_break_label='M')
        bo = _rule(increment_base=2.0, breaks=[{'inici': 'M', 'final': '3XL', 'delta': 3.0}])
        desplaçat = _rule(increment_base=2.0, breaks=[{'inici': 'L', 'final': '3XL', 'delta': 3.0}])
        self.assertEqual(_taula_escalat(vell, self.RUN), _taula_escalat(bo, self.RUN))
        self.assertNotEqual(_taula_escalat(vell, self.RUN), _taula_escalat(desplaçat, self.RUN))
        self.assertEqual(_taula_escalat(desplaçat, self.RUN)['M'], 102.0,
                         'amb el desplaçament, la M creixeria 2 en comptes de 3')


class SemanticaDelsIntervalsTest(SimpleTestCase):
    """② El cas de la Montse i la mecànica de l'extrem exterior."""

    RUN = ['XS', 'S', 'M', 'L', 'XL']

    def test_EL_CAS_MONTSE(self):
        """general 2 · S→L 3 → S→M 3, M→L 3, i XL TORNA A 2."""
        r = _rule(increment_base=2.0, breaks=[{'inici': 'S', 'final': 'L', 'delta': 3.0}])
        esperat = {'XS': 98.0, 'S': 100.0, 'M': 103.0, 'L': 106.0, 'XL': 108.0}
        self.assertEqual(_taula_escalat(r, self.RUN), esperat)
        self.assertEqual(_taula_presa(r, self.RUN), esperat,
                         'ESCALAT I PRESA HAN DE DIR EL MATEIX (lliçó del fix A)')

    def test_tres_intervals(self):
        """El sostre de la casa és 3, i tres han de conviure sense trepitjar-se."""
        r = _rule(increment_base=1.0, breaks=[
            {'inici': 'XS', 'final': 'XS', 'delta': 2.0},
            {'inici': 'M', 'final': 'L', 'delta': 3.0},
            {'inici': 'XXL', 'final': '3XL', 'delta': 4.0},
        ])
        run = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']
        self.assertEqual(_taula_escalat(r, run), {
            'XXS': 97.0,    # XXS↔XS exterior XXS → general 1 ; XS↔S exterior XS → 2 → 100−2−1
            'XS': 98.0,
            'S': 100.0,
            'M': 103.0,     # S↔M exterior M → 3
            'L': 106.0,     # M↔L exterior L → 3
            'XL': 107.0,    # L↔XL exterior XL → general 1
            'XXL': 111.0,   # XL↔XXL exterior XXL → 4
            '3XL': 115.0,
        })
        self.assertEqual(_taula_presa(r, run), _taula_escalat(r, run))

    def test_propagar_des_de_QUALSEVOL_talla_dona_la_mateixa_corba(self):
        """La llei FIX-1, amb intervals: el relleu és de (regla + run + base), no de l'entrada."""
        r = _rule(increment_base=2.0, breaks=[{'inici': 'S', 'final': 'L', 'delta': 3.0}])
        canonica = _taula_escalat(r, self.RUN)
        for ancora, valor in canonica.items():
            vals = propaga_ancoratges(r, ancora, valor, self.RUN,
                                      run_sistema=SISTEMA, base_label='S')
            self.assertEqual({k: round(v, 2) for k, v in vals.items()}, canonica,
                             f"ancorant a {ancora} la corba canvia")

    def test_els_intervals_manen_sobre_el_break_dun_tram(self):
        """Amb les dues formes informades mana la nova: és la que algú ha escrit expressament."""
        r = _rule(increment_base=2.0, increment_break=9.0, talla_break_label='M',
                  breaks=[{'inici': 'S', 'final': 'L', 'delta': 3.0}])
        self.assertEqual(_taula_escalat(r, self.RUN)['XL'], 108.0)

    def test_intervals_de_es_el_punt_unic(self):
        """La lectura de les dues formes viu en UNA funció, i és la que el motor crida."""
        vell = _rule(increment_base=2.0, increment_break=3.0, talla_break_label='M')
        self.assertEqual(intervals_de(vell, SISTEMA), [(3, 7, 3.0)])
        nou = _rule(increment_base=2.0, breaks=[{'inici': 'M', 'final': 'L', 'delta': 3.0}])
        self.assertEqual(intervals_de(nou, SISTEMA), [(3, 4, 3.0)])
        self.assertEqual(intervals_de(_rule(increment_base=2.0), SISTEMA), [])


class LecturaToleranteDelMotorTest(SimpleTestCase):
    """El motor no té canal per dir «aquesta dada és dolenta»: ignora el que no pot resoldre."""

    def test_final_fora_del_run_es_clava_a_lultima(self):
        self.assertEqual(
            intervals_en_index([{'inici': 'M', 'final': 'XXXL', 'delta': 3}], SISTEMA),
            [(3, 7, 3.0)])

    def test_ordena_i_descarta_el_que_no_sap_llegir(self):
        self.assertEqual(
            intervals_en_index([
                {'inici': 'XXL', 'final': '3XL', 'delta': 4},
                {'inici': 'M', 'final': 'L', 'delta': 3},
                {'inici': 'M', 'final': 'L'},            # sense delta → fora
                {'inici': 'ZZ', 'final': 'L', 'delta': 1},   # inici forà → fora
                'no soc un dict',
            ], SISTEMA),
            [(3, 4, 3.0), (6, 7, 4.0)])


class PortaDAutoriaTest(SimpleTestCase):
    """③ `valida_breaks` — el punt únic de les quatre portes."""

    def _err(self, breaks, **kw):
        kw.setdefault('logica', 'LINEAR')
        kw.setdefault('run', SISTEMA)
        kw.setdefault('increment_base', 2)
        nets, err = valida_breaks(breaks, **kw)
        self.assertIsNotNone(err, f"hauria d'haver estat rebutjat: {breaks}")
        return err['codi']

    def test_el_cas_bo_es_normalitza_i_passa(self):
        nets, err = valida_breaks([{'inici': 'm', 'final': '3xl', 'delta': '3,5'}],
                                  logica='LINEAR', run=SISTEMA, increment_base=2)
        self.assertIsNone(err)
        self.assertEqual(nets, [{'inici': 'M', 'final': '3XL', 'delta': 3.5}],
                         "l'etiqueta es desa amb l'ortografia del run i el delta com a número")

    def test_buit_i_None_son_el_mateix_estat(self):
        for valor in (None, [], ''):
            nets, err = valida_breaks(valor, logica='LINEAR', run=SISTEMA, increment_base=2)
            self.assertIsNone(err)
            self.assertIsNone(nets, 'una llista buida es desa com a NULL')

    def test_maxim(self):
        u = {'inici': 'M', 'final': 'L', 'delta': 3}
        self.assertEqual(self._err([u] * (MAX_BREAKS + 1)), 'BREAKS_MAX')

    def test_ordre_invertit(self):
        self.assertEqual(self._err([{'inici': 'L', 'final': 'M', 'delta': 3}]), 'BREAKS_ORDRE')

    def test_solapament(self):
        self.assertEqual(self._err([{'inici': 'S', 'final': 'L', 'delta': 3},
                                    {'inici': 'L', 'final': 'XXL', 'delta': 4}]),
                         'BREAKS_SOLAPAMENT')

    def test_talla_forana(self):
        self.assertEqual(self._err([{'inici': '46', 'final': '3XL', 'delta': 3}]),
                         'BREAKS_TALLA_FORANA')

    def test_nomes_linear(self):
        self.assertEqual(self._err([{'inici': 'M', 'final': 'L', 'delta': 3}], logica='STEP'),
                         'BREAKS_NOMES_LINEAR')

    def test_sense_delta_general(self):
        self.assertEqual(self._err([{'inici': 'M', 'final': 'L', 'delta': 3}],
                                   increment_base=None), 'BREAKS_SENSE_GENERAL')

    def test_delta_igual_al_general_no_trenca_res(self):
        self.assertEqual(self._err([{'inici': 'M', 'final': 'L', 'delta': 2}]),
                         'BREAKS_DELTA_REDUNDANT')

    def test_dos_intervals_ENGANXATS_amb_el_mateix_delta(self):
        """«M→L 3» i «XL→3XL 3» és UN tram dit en dos trossos."""
        self.assertEqual(self._err([{'inici': 'M', 'final': 'L', 'delta': 3},
                                    {'inici': 'XL', 'final': '3XL', 'delta': 3}]),
                         'BREAKS_DELTA_REDUNDANT')

    def test_dos_intervals_SEPARATS_amb_el_mateix_delta_SI_valen(self):
        """Amb un tram general pel mig, els dos diuen coses diferents i són legítims."""
        nets, err = valida_breaks([{'inici': 'XXS', 'final': 'XS', 'delta': 3},
                                   {'inici': 'L', 'final': '3XL', 'delta': 3}],
                                  logica='LINEAR', run=SISTEMA, increment_base=2)
        self.assertIsNone(err, err)
        self.assertEqual(len(nets), 2)

    def test_sense_run_es_valida_la_forma_pero_no_les_etiquetes(self):
        nets, err = valida_breaks([{'inici': 'QUALSEVOL', 'final': 'COSA', 'delta': 3}],
                                  logica='LINEAR', run=[], increment_base=2)
        self.assertIsNone(err, 'un joc sense sistema de talles no es pot validar per etiqueta')
        self.assertEqual(len(nets), 1)


class DeuteLinearZeroAmbBreakTest(SimpleTestCase):
    """El defecte 4 de la diagnosi de PROD: `ib=0 · brk=0` + break informat NO gradua res."""

    def test_ib0_brk0_amb_break_ES_degenerada(self):
        self.assertTrue(es_linear_degenerada('LINEAR', 0, 2, 0, 'M'))

    def test_ib0_amb_break_de_debo_NO_es_degenerada(self):
        self.assertFalse(es_linear_degenerada('LINEAR', 0, 2, 1.5, 'M'),
                         'un sostre a l’inrevés (0 fins al break, 1.5 després) SÍ que gradua')

    def test_ib0_amb_interval_de_debo_NO_es_degenerada(self):
        self.assertFalse(es_linear_degenerada(
            'LINEAR', 0, 0, 0, None, [{'inici': 'M', 'final': 'L', 'delta': 1.0}]))

    def test_ib0_amb_intervals_TOTS_a_zero_ES_degenerada(self):
        self.assertTrue(es_linear_degenerada(
            'LINEAR', 0, 0, 0, None, [{'inici': 'M', 'final': 'L', 'delta': 0}]))

    def test_el_cas_de_sempre_no_canvia(self):
        self.assertTrue(es_linear_degenerada('LINEAR', 0, 2, None, None))
        self.assertFalse(es_linear_degenerada('LINEAR', 1.5, 0, None, None))
        self.assertFalse(es_linear_degenerada('FIXED', 0, 0, None, None))


class IntervalsPerLaPortaHTTPTest(TenantTestCase):
    """La porta de la regla RESIDENT, de punta a punta: es desa, es gradua i es rebutja."""

    RUN = ['XS', 'S', 'M', 'L', 'XL']
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
        from fhort.fitting.models import SizeFitting
        from fhort.models_app.models import BaseMeasurement, Model
        from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem

        self.user = get_user_model().objects.create(username='tramf')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'TRAM F', 'rol_nom': 'admin'})

        self.ss = SizeSystem.objects.create(codi='SS_TF', nom='SS TF', base_unit='ALPHA')
        for i, et in enumerate(SISTEMA):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)

        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Chest')
        # 🚩 MODEL DE PROVA, MAI EL BANC: el 1383 és dada viva i el gate el mesura.
        self.model = Model.objects.create(
            codi_intern='TST-TRAMF', codi_tenant='TST', any=2026, sequencial=1,
            nom_prenda='Test tram F', size_system=self.ss,
            size_run_model='·'.join(self.RUN), base_size_label=self.BASE,
        )
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, is_active=True, ordre=0)
        self.sf = SizeFitting.objects.filter(model=self.model).order_by('numero').first()

    def _regim(self, body):
        from fhort.models_app.views import set_pom_regim_view
        r = APIRequestFactory().post('/x/', body, format='json')
        force_authenticate(r, user=self.user)
        return set_pom_regim_view(r, self.model.id, self.pom.id)

    def _taula(self):
        from fhort.fitting.models import GradedSpec, GradingVersion
        from fhort.pom.services import generate_graded_specs
        generate_graded_specs(self.sf.id)
        gv = GradingVersion.objects.filter(
            size_fitting=self.sf, is_active=True).order_by('-version_number').first()
        return {s.size_label: float(s.graded_value_cm)
                for s in GradedSpec.objects.filter(grading_version=gv, pom=self.pom)}

    def test_EL_CAS_MONTSE_de_punta_a_punta(self):
        """S'escriu per la porta i es gradua: general 2 · S→L 3 · XL torna a 2."""
        resp = self._regim({'logica': 'LINEAR', 'increment_base': 2,
                            'breaks': [{'inici': 'S', 'final': 'L', 'delta': 3}]})
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertEqual(resp.data['breaks'], [{'inici': 'S', 'final': 'L', 'delta': 3.0}],
                         'la resposta ha de dir el relleu que ha quedat desat')
        self.assertEqual(self._taula(),
                         {'XS': 98.0, 'S': 100.0, 'M': 103.0, 'L': 106.0, 'XL': 108.0})

    def test_la_porta_rebutja_el_solapament(self):
        resp = self._regim({'logica': 'LINEAR', 'increment_base': 2, 'breaks': [
            {'inici': 'S', 'final': 'L', 'delta': 3}, {'inici': 'L', 'final': 'XL', 'delta': 4}]})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get('codi'), 'BREAKS_SOLAPAMENT')

    def test_es_pot_ESBORRAR_el_relleu_amb_una_llista_buida(self):
        self._regim({'logica': 'LINEAR', 'increment_base': 2,
                     'breaks': [{'inici': 'S', 'final': 'L', 'delta': 3}]})
        resp = self._regim({'breaks': []})
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertEqual(resp.data['breaks'], [])
        self.assertEqual(self._taula()['XL'], 106.0,
                         'sense relleu, tot creix amb el Δ general (3 passos × 2)')

    def test_un_interval_a_una_talla_del_SISTEMA_que_el_model_no_fabrica(self):
        """La frontera de §4.4: el motor resol contra el sistema, i la porta també."""
        resp = self._regim({'logica': 'LINEAR', 'increment_base': 2,
                            'breaks': [{'inici': 'M', 'final': '3XL', 'delta': 3}]})
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertEqual(self._taula()['XL'], 109.0)

    def test_LINEAR_zero_amb_break_informat_ja_no_entra(self):
        """El deute LINEAR+0, a la porta que el deixava passar."""
        resp = self._regim({'logica': 'LINEAR', 'increment_base': 0, 'increment_break': 0,
                            'talla_break_label': 'M'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get('codi'), 'LINEAR_INCREMENT_ZERO')

    def test_el_payload_de_la_taula_serveix_els_intervals_i_el_run_del_sistema(self):
        from fhort.models_app.views import measurements_table_view
        self._regim({'logica': 'LINEAR', 'increment_base': 2,
                     'breaks': [{'inici': 'S', 'final': 'L', 'delta': 3}]})
        r = APIRequestFactory().get('/x/')
        force_authenticate(r, user=self.user)
        resp = measurements_table_view(r, self.model.id)
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        fila = resp.data['rows'][0]
        self.assertEqual(fila['breaks'], [{'inici': 'S', 'final': 'L', 'delta': 3.0}])
        self.assertEqual(resp.data['run_sistema'], SISTEMA)


class ElsIntervalsViatgenTest(TenantTestCase):
    """F5 — un camp de FORMA que no viatja és mitja regla: el clon, la materialització i la
    comparació. És el mode de fallada que el fix A va trobar al clon de perfil."""

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
        from fhort.pom.models import (ConstructionType, FitType, GarmentType, GradingRule,
                                      GradingRuleSet, POMMaster, SizeDefinition, SizeSystem,
                                      Target)
        self.ss = SizeSystem.objects.create(codi='SS_TFV', nom='SS TFV', base_unit='ALPHA')
        self.talles = {et: SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
                       for i, et in enumerate(SISTEMA)}
        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Chest')
        self.rs = GradingRuleSet.objects.create(nom='Joc TF', codi_sistema='TF', size_system=self.ss)
        # `talla_base` és FK NOT NULL i el motor no la llegeix mai («mer metadata del seed»),
        # però la fila no neix sense ella.
        self.regla = GradingRule.objects.create(
            rule_set=self.rs, pom=self.pom, talla_base=self.talles['S'], talla_base_label='S',
            logica='LINEAR', increment=0,
            increment_base=2.0, breaks=[{'inici': 'M', 'final': '3XL', 'delta': 3.0}])
        self.target = Target.objects.create(codi='WOMAN', nom_en='Woman', display_order=1)
        self.gt = GarmentType.objects.create(nom_client='Dresses', actiu=True)
        self.constr = ConstructionType.objects.create(codi='WOVEN', nom_en='Woven',
                                                      display_order=1)
        self.fit = FitType.objects.create(codi='REGULAR', nom_en='Regular', display_order=1)

    def test_el_clon_de_perfil_conserva_els_intervals(self):
        from fhort.pom.models import GradingRule, SizingProfile
        from fhort.pom.s2_views import clone_sizing_profile_view
        perfil = SizingProfile.objects.create(
            target=self.target, garment_type=self.gt, construction=self.constr,
            fit_type=self.fit, size_system=self.ss, grading_rule_set=self.rs,
            is_default=True, version=1)
        r = APIRequestFactory().post('/x/', {'nom_client': 'Clon TF'}, format='json')
        force_authenticate(r, user=get_user_model().objects.create(username='clonf'))
        resp = clone_sizing_profile_view(r, perfil.pk)
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        clonada = GradingRule.objects.get(rule_set_id=resp.data['grading_rule_set_id'])
        self.assertEqual(clonada.breaks, self.regla.breaks,
                         'EL CLON HA PERDUT EL RELLEU (el bug del fix A, una altra vegada)')

    def test_materialitzar_al_model_els_porta(self):
        from fhort.models_app.models import Model, ModelGradingRule
        from fhort.models_app.services import materialize_model_grading_rules
        model = Model.objects.create(
            codi_intern='TST-TFV', codi_tenant='TST', any=2026, sequencial=2,
            size_system=self.ss, size_run_model='S·M·L', base_size_label='M')
        materialize_model_grading_rules(model, [self.regla], origen='CANONICAL')
        resident = ModelGradingRule.objects.get(model=model, pom=self.pom)
        self.assertEqual(resident.breaks, self.regla.breaks)

    def test_la_comparacio_de_formes_els_mira(self):
        from fhort.pom.grading_utils import grading_rules_match, rule_to_spec, spec_forms_match
        # `talla_base_id` hi és perquè `rule_to_spec` el llegeix: el motor no l'usa mai («mer
        # metadata del seed») però l'spec el transporta, i un doble que no el porti menteix.
        altra = SimpleNamespace(pom_id=self.pom.id, pom=self.pom, logica='LINEAR',
                                increment=0, increment_base=2.0, increment_break=None,
                                talla_break_label=None, valors_step=None, talla_break_pos=None,
                                talla_base_id=self.talles['S'].id, rule_set_id=None,
                                breaks=[{'inici': 'M', 'final': '3XL', 'delta': 4.0}])
        ok, divs = grading_rules_match([altra], [self.regla])
        self.assertFalse(ok, 'dues regles amb relleus diferents NO són la mateixa forma')
        self.assertIn('interval', divs[0]['detall'])
        self.assertFalse(spec_forms_match(rule_to_spec(altra), rule_to_spec(self.regla)))
        self.assertTrue(spec_forms_match(rule_to_spec(self.regla), rule_to_spec(self.regla)))


class PortaDelValorVermellTest(TenantTestCase):
    """TRAM E · LA PORTA DEL VALOR VERMELL — escriu la REGLA, mai un override.

    El cens d'E+F va contrastar les dues formes i el fet que decideix és aquest: **propagar amb
    `new_version=True` esborra tots els `ModelGradingOverride` del model** (el «llenç net», que
    és llei). Amb un override, el tècnic hauria escrit vint xifres a mà i el primer «Propagar»
    conscient se les hauria endut sense dir res. Escrivint `valors_step`, el valor **és** la
    regla i sobreviu a totes les re-propagacions.

    El que aquestes proves fixen, i que és el difícil del règim STEP: `valors_step` no desa
    valors sinó **passos entre veïns**. Per això la porta no pot escriure una talla si el camí
    fins a ella té forats — i quan no pot, ho DIU nomenant la talla que falta, en comptes
    d'omplir-la amb un zero (que seria la corba plana fabricada que la llei D2 prohibeix).
    """

    RUN = ['XS', 'S', 'M', 'L', 'XL']
    BASE = 'S'
    BASE_VAL = 100.0

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
        from fhort.fitting.models import SizeFitting
        from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
        from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem

        self.user = get_user_model().objects.create(username='porta_step')
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Porta STEP', 'rol_nom': 'admin'})
        self.ss = SizeSystem.objects.create(codi='SS_PS', nom='SS PS', base_unit='ALPHA')
        for i, et in enumerate(SISTEMA):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Chest')
        self.model = Model.objects.create(
            codi_intern='TST-PORTA-STEP', codi_tenant='TST', any=2026, sequencial=7,
            size_system=self.ss, size_run_model='·'.join(self.RUN), base_size_label=self.BASE)
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=self.BASE_VAL, is_active=True, ordre=0)
        self.regla = ModelGradingRule.objects.create(
            model=self.model, pom=self.pom, logica='STEP', valors_step=None, actiu=True,
            increment=0, origen='CANONICAL')
        self.sf = SizeFitting.objects.filter(model=self.model).order_by('numero').first()

    def _posa(self, talla, valor):
        from fhort.models_app.views import set_step_valor_view
        r = APIRequestFactory().post('/x/', {'talla': talla, 'valor': valor}, format='json')
        force_authenticate(r, user=self.user)
        return set_step_valor_view(r, self.model.id, self.pom.id)

    def _taula(self):
        from fhort.fitting.models import GradedSpec
        from fhort.fitting.services import vigent_grading_version
        gv = vigent_grading_version(self.sf)
        return {s.size_label: float(s.graded_value_cm)
                for s in GradedSpec.objects.filter(grading_version=gv, pom=self.pom)}

    def _vermells(self):
        from fhort.models_app.views import measurements_table_view
        r = APIRequestFactory().get('/x/')
        force_authenticate(r, user=self.user)
        fila = next(f for f in measurements_table_view(r, self.model.id).data['rows']
                    if f['pom_id'] == self.pom.id)
        return fila['step_base_copiada']

    def test_EL_CICLE_SENCER_posar_valor_treu_el_vermell_i_RESISTEIX_la_re_propagacio(self):
        from fhort.pom.services import generate_graded_specs
        generate_graded_specs(self.sf.id)
        self.assertEqual(self._taula(), {s: self.BASE_VAL for s in self.RUN},
                         'de sortida, totes prestades')
        self.assertEqual(sorted(self._vermells()), ['L', 'M', 'XL', 'XS'])

        resp = self._posa('M', 103)
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertEqual(resp.data['delta'], 3.0)
        self.assertEqual(self._taula()['M'], 103.0, 'la porta re-propaga in place')
        self.assertNotIn('M', self._vermells(), 'i la M surt del vermell')

        # 🔑 EL QUE L'OVERRIDE NO HAURIA SOBREVISCUT: una propagació conscient (llenç net).
        from fhort.pom.services import bump_grading_version_and_generate
        from fhort.models_app.models import ModelGradingOverride
        ModelGradingOverride.objects.filter(model=self.model).delete()
        bump_grading_version_and_generate(self.sf.id, base_changed=False)
        self.assertEqual(self._taula()['M'], 103.0,
                         'EL VALOR HA DE SOBREVIURE: és la regla, no un ajust per cel·la')
        self.assertNotIn('M', self._vermells())

    def test_el_cami_incomplet_es_REBUTJA_dient_quina_talla_falta(self):
        """Escriure la L sense la M no es pot expressar: un delta és un pas entre veïns."""
        from fhort.pom.services import generate_graded_specs
        generate_graded_specs(self.sf.id)
        resp = self._posa('L', 106)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'STEP_CAMI_INCOMPLET')
        self.assertEqual(resp.data['talla_que_falta'], 'M')
        self.assertIsNone(self.regla.__class__.objects.get(pk=self.regla.pk).valors_step,
                          'un rebuig no escriu res')

    def test_la_cadena_es_completa_de_la_base_cap_enfora_amunt_i_avall(self):
        from fhort.pom.services import generate_graded_specs
        generate_graded_specs(self.sf.id)
        self.assertEqual(self._posa('M', 103).status_code, 200)
        self.assertEqual(self._posa('L', 106).status_code, 200)
        self.assertEqual(self._posa('XS', 98).status_code, 200)
        self.assertEqual(self._taula(),
                         {'XS': 98.0, 'S': 100.0, 'M': 103.0, 'L': 106.0, 'XL': 100.0})
        self.assertEqual(self._vermells(), ['XL'], 'només queda la que ningú ha dit')
        # Avall el delta és el PAS cap enfora, no la resta amb signe.
        self.regla.refresh_from_db()
        self.assertEqual(self.regla.valors_step['XS'], 2.0)

    def test_la_talla_BASE_no_entra_per_aquesta_porta(self):
        resp = self._posa(self.BASE, 99)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'STEP_TALLA_BASE')

    def test_sota_LINEAR_la_porta_es_tanca(self):
        self.regla.logica = 'LINEAR'
        self.regla.increment_base = 2
        self.regla.save(update_fields=['logica', 'increment_base'])
        resp = self._posa('M', 103)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'STEP_NO_ES_STEP')

    def test_una_talla_que_no_es_del_run(self):
        resp = self._posa('42', 103)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'STEP_TALLA_FORANA')

    def test_el_valor_ha_de_ser_un_numero(self):
        resp = self._posa('M', 'gairebé 103')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'STEP_VALOR')
