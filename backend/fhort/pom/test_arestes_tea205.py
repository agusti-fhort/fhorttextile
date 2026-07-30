"""FIX-1 (DIAGNOSI_MESURES_TEA_205) — el motor i la propagació caminen el MATEIX relleu.

Tests PURS (SimpleTestCase, cap DB): tota la mecànica d'arestes és `grading_utils`, i el
motor (`_apply_rule`) i `propaga_ancoratges` ara la consumeixen tots dos.

Fixture real: RS146 «Textiles y Confecciones Brownie SL · Tops · Alpha EU — Women»
(CLIENT_RUN) aplicat al model 205 «TEA» — base S, run de model XXS·XS·S·M·L, sistema
Alpha EU — Women (XXS·XS·S·M·L·XL·XXL·3XL). Els 80 rules són els de producció el
2026-07-30; la norma acceptada que fixa la semàntica és E2: XXS = base − 2.5.
"""
from types import SimpleNamespace

from django.test import SimpleTestCase

from fhort.pom.grading_utils import (
    desnivell_entre_talles, increment_de_l_aresta, propaga_ancoratges,
)
from fhort.pom.services import _apply_rule, _norm_label


# ── Geometria del model 205 ──────────────────────────────────────────────────────────
RUN_SISTEMA = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']
RUN_MODEL = ['XXS', 'XS', 'S', 'M', 'L']
BASE = 'S'
BASE_IDX = RUN_SISTEMA.index(BASE)               # 2

# ── RS146 sencer: (pom, logica, increment, increment_base, increment_break, talla_break) ──
RS146 = [
    ('0', 'FIXED', 0.00, 0.00, None, None),
    ('1/2_ELBOW_WIDTH', 'LINEAR', 0.60, 0.60, None, None),
    ('A.2', 'LINEAR', 1.20, 1.20, None, None),
    ('AC BK', 'LINEAR', 1.00, 1.00, 1.50, 'XS'),
    ('AC FR', 'LINEAR', 0.50, 0.50, None, None),
    ('AC SH', 'LINEAR', 0.50, 0.50, None, None),
    ('AG', 'LINEAR', 0.30, 0.30, 0.50, 'XS'),
    ('AH CIRC', 'LINEAR', 1.40, 1.40, 2.00, 'XS'),
    ('AH DEP', 'LINEAR', 0.70, 0.70, 1.00, 'XS'),
    ('BIC', 'LINEAR', 0.60, 0.60, 0.80, 'XS'),
    ('BL CB', 'LINEAR', 1.00, 1.00, 1.50, 'S'),
    ('BL HPS', 'LINEAR', 1.00, 1.00, None, None),
    ('CG', 'LINEAR', 0.50, 0.50, 0.75, 'XS'),
    ('CH', 'LINEAR', 2.00, 2.00, 3.00, 'XS'),
    ('COL L', 'LINEAR', 0.50, 0.50, 0.75, 'XS'),
    ('CUF H', 'FIXED', 0.00, 0.00, None, None),
    ('D', 'LINEAR', 2.00, 2.00, 3.00, 'XS'),
    ('D1', 'LINEAR', 1.50, 1.50, 2.00, 'XS'),
    ('DR L HPS', 'LINEAR', 1.00, 1.00, 1.50, 'S'),
    ('E', 'LINEAR', 1.00, 1.00, 1.50, 'XS'),
    ('E2', 'LINEAR', 1.00, 1.00, 1.50, 'XS'),
    ('E4', 'FIXED', 0.00, 0.00, None, None),
    ('EG', 'LINEAR', 0.80, 0.80, 1.20, 'XS'),
    ('EK1', 'LINEAR', 0.25, 0.25, 0.40, 'XS'),
    ('EK2', 'FIXED', 0.00, 0.00, None, None),
    ('ELB', 'LINEAR', 0.40, 0.40, 0.60, 'XS'),
    ('EP', 'FIXED', 0.00, 0.00, None, None),
    ('F', 'LINEAR', 1.00, 1.00, 1.50, 'S'),
    ('G1', 'FIXED', 0.00, 0.00, None, None),
    ('H11L', 'LINEAR', 0.30, 0.30, 0.50, 'XS'),
    ('HEM W', 'LINEAR', 1.50, 1.50, 2.00, 'XS'),
    ('HI', 'LINEAR', 1.50, 1.50, 2.00, 'XS'),
    ('HI PA', 'LINEAR', 1.50, 1.50, 2.00, 'XS'),
    ('I', 'LINEAR', 0.70, 0.70, None, None),
    ('I3', 'FIXED', 0.00, 0.00, None, None),
    ('I4', 'LINEAR', 0.50, 0.50, None, None),
    ('INS', 'LINEAR', 0.75, 0.75, 1.00, 'S'),
    ('J2', 'LINEAR', 0.60, 0.60, 0.80, 'XS'),
    ('KG', 'LINEAR', 0.70, 0.70, 1.00, 'XS'),
    ('KNE', 'LINEAR', 0.30, 0.30, 0.50, 'XS'),
    ('L', 'LINEAR', 0.30, 0.30, 0.50, 'XS'),
    ('LEG OP', 'LINEAR', 0.30, 0.30, 0.50, 'XS'),
    ('LOGO HPS', 'LINEAR', 0.30, 0.30, 0.50, 'XS'),
    ('LZ1', 'FIXED', 0.00, 0.00, None, None),
    ('M-M79', 'LINEAR', 1.00, 1.00, 1.50, 'S'),
    ('NC', 'LINEAR', 0.50, 0.50, 0.75, 'XS'),
    ('NK CIRC RLX', 'LINEAR', 1.00, 1.00, 1.50, 'XS'),
    ('NK DR BK', 'LINEAR', 0.10, 0.10, None, None),
    ('NK DR FR', 'LINEAR', 0.20, 0.20, None, None),
    ('NK W', 'LINEAR', 0.50, 0.50, 0.75, 'XS'),
    ('OUTS', 'LINEAR', 1.00, 1.00, 1.50, 'S'),
    ('P1', 'LINEAR', 0.30, 0.30, 0.50, 'XS'),
    ('P3', 'LINEAR', 0.30, 0.30, 0.50, 'XS'),
    ('P4', 'LINEAR', 0.30, 0.30, 0.50, 'XS'),
    ('PKT WB', 'LINEAR', 0.30, 0.30, 0.50, 'XS'),
    ('RI BK', 'LINEAR', 0.50, 0.50, 0.75, 'XS'),
    ('RI FR', 'LINEAR', 0.35, 0.35, 0.50, 'XS'),
    ('RI TOT', 'LINEAR', 0.85, 0.85, 1.25, 'XS'),
    ('S', 'LINEAR', 0.70, 0.70, 1.00, 'XS'),
    ('S2', 'LINEAR', 0.70, 0.70, 1.00, 'XS'),
    ('SH', 'LINEAR', 0.25, 0.25, 0.40, 'XS'),
    ('SH DR', 'FIXED', 0.00, 0.00, None, None),
    ('SK L', 'LINEAR', 1.00, 1.00, 1.50, 'S'),
    ('SK SW', 'LINEAR', 1.50, 1.50, 2.00, 'XS'),
    ('SL', 'LINEAR', 0.30, 0.30, None, None),
    ('SL CB', 'LINEAR', 0.75, 0.75, None, None),
    ('SL UA', 'LINEAR', 0.50, 0.50, None, None),
    ('SS', 'LINEAR', 0.75, 0.75, 1.00, 'S'),
    ('TH', 'LINEAR', 1.50, 1.50, 2.00, 'XS'),
    ('THI', 'LINEAR', 0.70, 0.70, 1.00, 'XS'),
    ('U2', 'LINEAR', 0.15, 0.15, 0.20, 'XS'),
    ('U3', 'FIXED', 0.00, 0.00, None, None),
    ('UA', 'LINEAR', 1.20, 1.20, 1.60, 'XS'),
    ('UB', 'LINEAR', 1.00, 1.00, 1.50, 'XS'),
    ('V', 'FIXED', 0.00, 0.00, None, None),
    ('VL', 'FIXED', 0.00, 0.00, None, None),
    ('WA', 'LINEAR', 1.00, 1.00, 1.50, 'XS'),
    ('WB RLX', 'LINEAR', 1.00, 1.00, 1.50, 'XS'),
    ('WB STR', 'LINEAR', 1.50, 1.50, 2.00, 'XS'),
    ('WG', 'LINEAR', 0.50, 0.50, None, None),
]


def _rule(logica=None, increment=None, increment_base=None, increment_break=None,
          talla_break_label=None, valors_step=None, pom_id=1):
    """Regla falsa amb tots els atributs que llegeixen el motor i la propagació."""
    return SimpleNamespace(
        logica=logica, increment=increment, increment_base=increment_base,
        increment_break=increment_break, talla_break_label=talla_break_label,
        valors_step=valors_step, pom=None, pom_id=pom_id)


def _regla_de(codi):
    """La regla de RS146 amb aquest codi de POM."""
    for pom, logica, inc, ib, brk, tbl in RS146:
        if pom == codi:
            return _rule(logica=logica, increment=inc, increment_base=ib,
                         increment_break=brk, talla_break_label=tbl)
    raise AssertionError(f'RS146 no té cap regla per al POM {codi}')


# Regla E2 de producció: LINEAR, ib=1.0, brk=1.5, break a XS.
E2 = _regla_de('E2')


def _grada_amb_motor(rule, base_val, run=RUN_MODEL):
    """Tota la fila tal com l'emetria `generate_graded_specs` (espai de SISTEMA, llei S24b)."""
    out = {}
    for label in run:
        i = RUN_SISTEMA.index(label)
        val, _gt = _apply_rule(rule, base_val, i - BASE_IDX, i, BASE_IDX,
                               size_run=RUN_SISTEMA)
        out[label] = val
    return out


def _propaga(rule, anchor_label, anchor_val, run=RUN_MODEL, **kw):
    return propaga_ancoratges(rule, anchor_label, anchor_val, run,
                              run_sistema=RUN_SISTEMA, base_label=BASE, **kw)


class NormaBrownieE2Test(SimpleTestCase):
    """La norma ACCEPTADA: E2 XXS = base − 2.5. Ha de sortir pels DOS camins.

    La fila esperada NO és inventada: és la que PRODUCCIÓ té emesa a `GradedSpec` per al
    model 205 / POM E2 (base 3.0 → XXS 0.5 · XS 1.5 · S 3.0 · M 4.5 · L 6.0, deltes
    −2.5 / −1.5 / 0 / +1.5 / +3.0), llegida del backup del 2026-07-30.
    """

    BASE_VAL = 3.0
    FILA_PROD = {'XXS': 0.5, 'XS': 1.5, 'S': 3.0, 'M': 4.5, 'L': 6.0}

    def test_e2_xxs_pel_motor(self):
        self.assertEqual(_grada_amb_motor(E2, self.BASE_VAL)['XXS'],
                         self.BASE_VAL - 2.5)

    def test_e2_xxs_per_propagacio(self):
        self.assertEqual(_propaga(E2, BASE, self.BASE_VAL)['XXS'],
                         self.BASE_VAL - 2.5)

    def test_e2_fila_sencera_identica_pels_dos_camins(self):
        motor = _grada_amb_motor(E2, self.BASE_VAL)
        self.assertEqual(motor, self.FILA_PROD)
        self.assertEqual(_propaga(E2, BASE, self.BASE_VAL), motor)

    def test_e2_aresta_a_aresta(self):
        """La llei: l'aresta pren el seu extrem EXTERIOR (el més lluny de la base)."""
        i = RUN_SISTEMA.index
        # Sota la base: XS↔S té l'exterior a XS, que ÉS el break → increment_break.
        self.assertEqual(increment_de_l_aresta(E2, RUN_SISTEMA, BASE_IDX,
                                               i('XS'), i('S')), 1.5)
        # XXS↔XS té l'exterior a XXS, per sota del break → increment_base.
        self.assertEqual(increment_de_l_aresta(E2, RUN_SISTEMA, BASE_IDX,
                                               i('XXS'), i('XS')), 1.0)
        # Per damunt de la base l'exterior és el SUPERIOR, i amb el break a XS tot el que
        # puja hi queda per damunt → increment_break. És el que PROD té emès (+1.5 a M).
        self.assertEqual(increment_de_l_aresta(E2, RUN_SISTEMA, BASE_IDX,
                                               i('S'), i('M')), 1.5)


class IdempotenciaEscalatTest(SimpleTestCase):
    """B1 — reescriure a una cel·la d'Escalat el valor que JA hi té no ha de moure res.

    És el símptoma exacte del 205: la vista d'Escalat ancora la cel·la editada, en deriva
    la nova BASE amb `propaga_ancoratges` i re-deriva la fila. Si la propagació no camina
    el mateix relleu que el motor, la base «derivada» no és la de partida i tota la fila
    llisca a cada desat.
    """

    BASE_VAL = 3.0

    def _base_derivada(self, rule, talla, valor):
        """El que fa `escalat_ajustar_talla_view`: ancorar i llegir-ne la base."""
        return _propaga(rule, talla, valor)[BASE]

    def test_reescriure_el_valor_vigent_no_mou_la_base(self):
        for pom, logica, inc, ib, brk, tbl in RS146:
            if logica == 'STEP' or ib is None:
                continue                      # Escalat no propaga aquests règims
            rule = _rule(logica=logica, increment=inc, increment_base=ib,
                         increment_break=brk, talla_break_label=tbl)
            fila = _grada_amb_motor(rule, self.BASE_VAL)
            for talla, vigent in fila.items():
                if vigent is None:
                    continue
                self.assertAlmostEqual(
                    self._base_derivada(rule, talla, vigent), self.BASE_VAL, places=9,
                    msg=f'POM {pom}: ancorar {talla}={vigent} mou la base')

    def test_reescriure_el_valor_vigent_no_mou_cap_cel_la(self):
        """I un cop re-derivada la base, la fila sencera ha de tornar idèntica."""
        fila = _grada_amb_motor(E2, self.BASE_VAL)
        for talla, vigent in fila.items():
            nova_base = self._base_derivada(E2, talla, vigent)
            self.assertEqual(_grada_amb_motor(E2, round(nova_base, 2)), fila,
                             msg=f'ancorar {talla}={vigent} mou la fila')

    def test_ancorar_a_una_talla_qualsevol_reprodueix_la_fila(self):
        """Propagar des de QUALSEVOL talla dóna la mateixa corba que el motor."""
        fila = _grada_amb_motor(E2, self.BASE_VAL)
        for talla, vigent in fila.items():
            self.assertEqual(_propaga(E2, talla, vigent), fila,
                             msg=f'propagar des de {talla} no reprodueix la fila')


class BreakALaBaseIALaXSTest(SimpleTestCase):
    """Els dos casos que el 205 exercita: break A LA BASE i break a XS."""

    BASE_VAL = 50.0

    def test_break_a_la_base(self):
        """Break = la talla base (S). L'aresta de sota (XS↔S) té l'exterior a XS < break
        → increment_base; la de sobre (S↔M) té l'exterior a M ≥ break → increment_break."""
        rule = _rule(logica='LINEAR', increment=1.0, increment_base=1.0,
                     increment_break=1.5, talla_break_label='S')
        motor = _grada_amb_motor(rule, self.BASE_VAL)
        self.assertEqual(motor, {'XXS': 48.0, 'XS': 49.0, 'S': 50.0,
                                 'M': 51.5, 'L': 53.0})
        for talla, vigent in motor.items():
            self.assertEqual(_propaga(rule, talla, vigent), motor,
                             msg=f'break a la base: propagar des de {talla} divergeix')

    def test_break_a_xs(self):
        rule = _rule(logica='LINEAR', increment=1.0, increment_base=1.0,
                     increment_break=1.5, talla_break_label='XS')
        motor = _grada_amb_motor(rule, self.BASE_VAL)
        self.assertEqual(motor, {'XXS': 47.5, 'XS': 48.5, 'S': 50.0,
                                 'M': 51.5, 'L': 53.0})
        for talla, vigent in motor.items():
            self.assertEqual(_propaga(rule, talla, vigent), motor,
                             msg=f'break a XS: propagar des de {talla} divergeix')


class RunNoContiguTest(SimpleTestCase):
    """Llei S24b — la DISTÀNCIA la mana el sistema, també a la propagació.

    Un model que no fabrica la M ha de comptar S→L com DOS passos. Abans, la propagació
    llegia el run del MODEL i el col·lapsava a un de sol.
    """

    def test_forat_al_run_del_model(self):
        rule = _rule(logica='LINEAR', increment=2.0, increment_base=2.0)
        run = ['XS', 'S', 'L']                 # sense M
        motor = _grada_amb_motor(rule, 50.0, run=run)
        self.assertEqual(motor, {'XS': 48.0, 'S': 50.0, 'L': 54.0})   # S→L = 2 passos
        self.assertEqual(
            propaga_ancoratges(rule, 'S', 50.0, run,
                               run_sistema=RUN_SISTEMA, base_label=BASE),
            motor)

    def test_talla_fora_del_sistema_no_inventa_distancia(self):
        rule = _rule(logica='LINEAR', increment=2.0, increment_base=2.0)
        out = propaga_ancoratges(rule, 'S', 50.0, ['XS', 'S', 'ZZZ'],
                                 run_sistema=RUN_SISTEMA, base_label=BASE)
        self.assertIsNone(out['ZZZ'])
        self.assertEqual(out['XS'], 48.0)


class NoRegressioMotorTest(SimpleTestCase):
    """El motor NO es mou: `_apply_rule` ha de donar EXACTAMENT el que donava abans.

    L'oracle és la implementació PRE-FIX-1 del branc canònic, transcrita aquí tal qual.
    Es compara sobre RS146 SENCER × totes les talles del sistema × totes les posicions de
    base: si el refactor mogués cap GradedSpec, aquest test cau.
    """

    def _oracle(self, rule, base_val, size_idx, base_idx, size_run):
        """Còpia literal del codi que hi havia a `_apply_rule` abans del refactor."""
        ib = float(rule.increment_base)
        brk = float(rule.increment_break) if rule.increment_break is not None else ib
        if size_idx == base_idx:
            return base_val
        break_idx = None
        if rule.talla_break_label and size_run:
            norm = [_norm_label(x) for x in size_run]
            tl = _norm_label(rule.talla_break_label)
            if tl in norm:
                break_idx = norm.index(tl)
        if size_idx > base_idx:
            path, sign = range(base_idx + 1, size_idx + 1), 1.0
        else:
            path, sign = range(size_idx, base_idx), -1.0
        total = 0.0
        for j in path:
            total += brk if (break_idx is not None and j >= break_idx) else ib
        return base_val + sign * total

    def test_rs146_sencer_no_es_mou(self):
        comprovats = 0
        for pom, logica, inc, ib, brk, tbl in RS146:
            if ib is None or logica == 'STEP':
                continue
            rule = _rule(logica=logica, increment=inc, increment_base=ib,
                         increment_break=brk, talla_break_label=tbl)
            for base_idx in range(len(RUN_SISTEMA)):
                for size_idx in range(len(RUN_SISTEMA)):
                    nou, _gt = _apply_rule(rule, 50.0, size_idx - base_idx,
                                           size_idx, base_idx, size_run=RUN_SISTEMA)
                    vell = self._oracle(rule, 50.0, size_idx, base_idx, RUN_SISTEMA)
                    self.assertEqual(
                        nou, vell,
                        msg=(f'POM {pom} (ib={ib}, brk={brk}, break={tbl}): '
                             f'base={RUN_SISTEMA[base_idx]} talla={RUN_SISTEMA[size_idx]}'))
                    comprovats += 1
        # Les 80 regles de RS146 són totes canòniques (les FIXED hi són amb ib=0.00).
        self.assertEqual(comprovats, 80 * 64)      # 80 regles × 8 bases × 8 talles

    def test_desnivell_es_la_mateixa_suma(self):
        """`desnivell_entre_talles` i el motor sumen les MATEIXES arestes."""
        for base_idx in range(len(RUN_SISTEMA)):
            for size_idx in range(len(RUN_SISTEMA)):
                nou, _ = _apply_rule(E2, 50.0, size_idx - base_idx, size_idx,
                                     base_idx, size_run=RUN_SISTEMA)
                self.assertEqual(
                    nou,
                    50.0 + desnivell_entre_talles(E2, RUN_SISTEMA, base_idx,
                                                  base_idx, size_idx))
