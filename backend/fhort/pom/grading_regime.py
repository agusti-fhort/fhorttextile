"""Classificació del RÈGIM d'una regla de graduació — punt únic del backend.

LLEI (Agus, 2026-07-22) — **LINEAR amb delta 0 i SENSE break ÉS FIXED.**

Una regla així no gradua res: `_apply_rule` retorna `base_val` per a totes les talles,
exactament el mateix que `FIXED`. Presentar-la com a LINEAR fabrica una taula plana que
sembla graduada. Mirall exacte de `frontend/src/utils/gradingRegime.js`.

Dues sortides, per als dos tipus de camí d'escriptura:

  · `es_linear_degenerada(...)` — per als camins d'**AUTORIA** (el tècnic escriu la
    regla): es rebutja amb 400 i se li suggereix FIXED. No es converteix per ell.
  · `normalitza_logica(...)` — per als camins de **SEMBRA/IMPORT** (la regla es
    materialitza des d'una font: un ruleset, una fitxa parsejada). Aquí no hi ha ningú
    a qui preguntar i rebutjar trencaria l'import: s'etiqueta FIXED directament. La
    conversió és neutra (cap valor canvia), només deixa de mentir.

El break és SAGRAT en tots dos casos: amb `talla_break_label` informat o
`increment_break` no-zero, la regla és LINEAR encara que el delta base sigui 0.
"""

#: Missatge i codi del rebuig d'autoria. Text de domini (no i18n: el sufix el consumeix
#: el frontend pel `codi` si algun dia el vol traduir).
MISSATGE_LINEAR_ZERO = (
    "Una regla LINEAR amb increment 0 no gradua res. Si aquesta mesura no ha de canviar "
    "entre talles, fes-la FIXED; si no aplica a aquest model, esborra-la."
)
CODI_LINEAR_ZERO = 'LINEAR_INCREMENT_ZERO'


def _f(v):
    """Decimal/str/None → float (None i '' compten com a absents)."""
    if v is None or v == '':
        return None
    try:
        return float(str(v).replace(',', '.'))
    except (TypeError, ValueError):
        return None


def te_break(increment_break=None, talla_break_label=None) -> bool:
    """True si la regla porta un trencament informat. Amb break, MAI és FIXED."""
    if talla_break_label is not None and str(talla_break_label).strip() != '':
        return True
    brk = _f(increment_break)
    return brk is not None and brk != 0.0


def delta_base_efectiu(increment_base=None, increment=None) -> float:
    """Delta base que aplicarà el motor: la forma canònica (`increment_base`) si està
    poblada, si no el fallback legacy (`increment`) que llegeix `_apply_rule`."""
    ib = _f(increment_base)
    if ib is not None:
        return ib
    return _f(increment) or 0.0


def es_linear_degenerada(logica, increment_base=None, increment=None,
                         increment_break=None, talla_break_label=None) -> bool:
    """True si la regla és LINEAR però matemàticament FIXED (delta 0, cap break)."""
    if (logica or '').strip().upper() != 'LINEAR':
        return False
    if te_break(increment_break, talla_break_label):
        return False
    return delta_base_efectiu(increment_base, increment) == 0.0


def normalitza_logica(logica, increment_base=None, increment=None,
                      increment_break=None, talla_break_label=None) -> str:
    """Règim que s'ha de DESAR. LINEAR degenerada → 'FIXED'; la resta, sense tocar."""
    if es_linear_degenerada(logica, increment_base, increment,
                            increment_break, talla_break_label):
        return 'FIXED'
    return logica
