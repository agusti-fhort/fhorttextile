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
                increment_break=None, talla_break_label=None, valors_step=None)
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
