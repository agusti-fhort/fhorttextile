"""Tests unitaris de propaga_ancoratges (PG-4b-1) — propagació LINEAR/canònica des d'UN ancoratge.

Funció PURA, SENSE DB (SimpleTestCase). La regla es simula amb SimpleNamespace (mateixos
atributs que ModelGradingRule / pom.GradingRule). Règim STEP/FIXED/ZERO no entra a la funció.
"""
from types import SimpleNamespace

from django.test import SimpleTestCase

from fhort.pom.grading_utils import propaga_ancoratges
from fhort.pom.services import _apply_rule


def _rule(**kw):
    """Regla falsa amb tots els atributs que llegeixen propaga_ancoratges i _apply_rule."""
    base = dict(logica=None, increment=None, increment_base=None,
                increment_break=None, talla_break_label=None, valors_step=None,
                pom=None, pom_id=1)
    base.update(kw)
    return SimpleNamespace(**base)


class PropagaAncoratgesTest(SimpleTestCase):

    RUN = ['S', 'M', 'L', 'XL']

    # ── T1: CANÒNIC uniforme, ancora a la base (M) → caminar increment_base. Retrocompat.
    def test_t1_canonic_uniforme_ancora_base(self):
        rule = _rule(logica='LINEAR', increment_base=2)
        out = propaga_ancoratges(rule, 'M', 50, self.RUN)
        self.assertEqual(out, {'S': 48, 'M': 50, 'L': 52, 'XL': 54})

    # ── T2: CANÒNIC amb break (ib=2, break a L, brk=3), ancora a la base (M).
    def test_t2_canonic_amb_break_ancora_base(self):
        rule = _rule(logica='LINEAR', increment_base=2,
                     talla_break_label='L', increment_break=3)
        out = propaga_ancoratges(rule, 'M', 50, self.RUN)
        # S=48 (sota break, ib), L=53 (al break, brk), XL=56 (M→XL: 2 passos brk).
        self.assertEqual(out, {'S': 48, 'M': 50, 'L': 53, 'XL': 56})

    # ── T_ancora_no_base: canònic uniforme ib=2, ancora a L=50 (no-base).
    # Propaga amunt I avall des de L: S=46, M=48, L=50, XL=52.
    def test_ancora_no_base(self):
        rule = _rule(logica='LINEAR', increment_base=2)
        out = propaga_ancoratges(rule, 'L', 50, self.RUN)
        self.assertEqual(out, {'S': 46, 'M': 48, 'L': 50, 'XL': 52})

    # ── T_regla_incompleta: regla sense cap delta (increment_base=None, increment=None)
    # → propagació PLANA (totes = anchor_val) + un únic warning (degradació gràcil).
    def test_regla_incompleta_warning_i_columna_plana(self):
        rule = _rule(logica='LINEAR')           # sense increment_base ni increment
        warnings = []
        out = propaga_ancoratges(rule, 'M', 50, self.RUN, warnings=warnings)
        self.assertEqual(out, {'S': 50, 'M': 50, 'L': 50, 'XL': 50})
        self.assertEqual(len(warnings), 1)

    # ── T_retrocompat: ancorant a la BASE, propaga_ancoratges ha de coincidir EXACTAMENT
    # amb _apply_rule talla a talla (regla canònica uniforme i regla amb break).
    def test_retrocompat_vs_apply_rule(self):
        base_idx = 1            # 'M'
        base_val = 50.0
        rules = [
            _rule(logica='LINEAR', increment_base=2),                              # uniforme
            _rule(logica='LINEAR', increment_base=2,
                  talla_break_label='L', increment_break=3),                       # amb break
        ]
        for rule in rules:
            out = propaga_ancoratges(rule, 'M', base_val, self.RUN)
            for i, label in enumerate(self.RUN):
                expected, _ = _apply_rule(
                    rule, base_val, i - base_idx, i, base_idx, size_run=self.RUN,
                )
                self.assertEqual(
                    out[label], expected,
                    msg=f"divergència a {label} (ib={rule.increment_base}, "
                        f"break={rule.talla_break_label})",
                )


class ApplyRuleStepGuardTest(SimpleTestCase):
    """PG-4b-3a — `logica` és la veritat del règim a _apply_rule: STEP guanya sobre increment_base."""

    RUN = ['S', 'M', 'L', 'XL']
    BASE_IDX = 1            # 'M'
    BASE_VAL = 50.0

    def _grade(self, rule, warnings=None):
        """Grada tot el run amb _apply_rule (ancora a base). Retorna {label: (val, gt)}."""
        out = {}
        for i, label in enumerate(self.RUN):
            out[label] = _apply_rule(
                rule, self.BASE_VAL, i - self.BASE_IDX, i, self.BASE_IDX,
                size_run=self.RUN, warnings=warnings,
            )
        return out

    # ── R1: NO-REGRESSIÓ LINEAR — increment_base=2, logica='LINEAR' grada igual que sempre.
    def test_r1_linear_no_regressio(self):
        rule = _rule(logica='LINEAR', increment_base=2)
        out = self._grade(rule)
        self.assertEqual(out, {
            'S': (48, 'LINEAR'), 'M': (50, 'LINEAR'),
            'L': (52, 'LINEAR'), 'XL': (54, 'LINEAR'),
        })

    # ── R2: STEP guanya — MATEIX increment_base=2 poblat, però logica='STEP' + valors_step.
    # _apply_rule usa valors_step (NO el canònic): L=55 (≠ 52 canònic) ho demostra.
    def test_r2_step_guanya_sobre_increment_base(self):
        rule = _rule(logica='STEP', increment_base=2,
                     valors_step={'S': 1, 'L': 5, 'XL': 6})
        out = self._grade(rule)
        # STEP: S=50-1=49, L=50+5=55, XL=50+5+6=61 (canònic donaria 48/52/54).
        self.assertEqual(out['L'], (55, 'STEP'))
        self.assertEqual(out['S'], (49, 'STEP'))
        self.assertEqual(out['XL'], (61, 'STEP'))
        self.assertNotEqual(out['L'][0], 52)   # NO ha gradat canònic

    # ── R3: STEP sense valors_step — increment_base poblat però logica='STEP', vs buit →
    # comportament STEP definit (cel·la None + warning); NO inventa delta canònic.
    def test_r3_step_sense_valors_step(self):
        rule = _rule(logica='STEP', increment_base=2, valors_step=None)
        warnings = []
        out = self._grade(rule, warnings=warnings)
        self.assertEqual(out['L'], (None, 'STEP'))   # no calcula (no 52 canònic)
        self.assertTrue(warnings)
