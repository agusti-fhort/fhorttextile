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


#: TRAM F — SOSTRE D'INTERVALS PER REGLA. **Constant ÚNICA de tota la casa**: el motor, les
#: quatre portes d'autoria i el mirall del front (`frontend/src/utils/gradingRegime.js`,
#: `MAX_BREAKS`) no en poden tenir cap de pròpia. Tres és decisió d'Agus, no una llei de domini:
#: canviar-la aquí ha de bastar.
MAX_BREAKS = 3

#: Codis de rebuig dels intervals. El `detall` és text de domini en català (com la resta
#: d'aquest fitxer i de `models_app/views.py`); el `codi` és el que el front pot traduir.
CODI_BREAKS_MAX = 'BREAKS_MAX'
CODI_BREAKS_FORMA = 'BREAKS_FORMA'
CODI_BREAKS_NOMES_LINEAR = 'BREAKS_NOMES_LINEAR'
CODI_BREAKS_TALLA_FORANA = 'BREAKS_TALLA_FORANA'
CODI_BREAKS_ORDRE = 'BREAKS_ORDRE'
CODI_BREAKS_SOLAPAMENT = 'BREAKS_SOLAPAMENT'
CODI_BREAKS_DELTA_REDUNDANT = 'BREAKS_DELTA_REDUNDANT'
CODI_BREAKS_SENSE_GENERAL = 'BREAKS_SENSE_GENERAL'


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
    """Delta base que aplicarà el motor. Des del FIX-A/PAS-3: NOMÉS `increment_base`.

    🚨 AQUÍ HI HAVIA EL FALLBACK AL LLEGAT, i era el MIRALL del que `_apply_rule` feia. Quan el
    motor va deixar de llegir `increment` (PAS 3), aquesta funció va quedar dient una cosa que
    ja no és certa —el seu propi docstring citava «el fallback legacy que llegeix `_apply_rule`»—
    i el guard d'autoria que en penja hauria donat per bona una regla que el motor no gradua.

    Un mirall que menteix és pitjor que no tenir-ne: la pantalla hauria dit «aquesta regla té
    delta 2.0 i és correcta» d'una fila que després no emet cap cel·la.

    `increment` es conserva al perfil de la funció perquè els quatre cridadors el passen i
    treure'l seria tocar-los tots per res; simplement ja no compta. El mirall del front
    (`frontend/src/utils/gradingRegime.js`, `deltaBase`) ha canviat amb aquesta.

    CONSEQÜÈNCIA VOLGUDA: una LINEAR **sense** `increment_base` i **sense** break ara és
    DEGENERADA i les portes d'autoria la rebutgen amb 400. Abans es desava i graduava amb el
    delta fossilitzat del joc — que és el bug sencer d'aquest sprint, tancat també a l'entrada.
    Amb break, `te_break` continua fent curtcircuit i la regla es desa: allà el rebuig el dona la
    propagació, amb el seu missatge propi (llei D2, `_apply_rule`).
    """
    return _f(increment_base) or 0.0


# ─────────────────────────────────────────────────────────────────────────────────────────────
# TRAM F · ELS INTERVALS (multi-break) — lectura, i validació d'autoria
#
# 🔑 UNA SOLA FORMA, DOS LECTORS AMB CRITERIS DIFERENTS, I ÉS A POSTA:
#
#   · `intervals_en_index` — el que llegeix el MOTOR. **Tolerant**: un interval que no es pot
#     resoldre contra el run s'ignora, exactament com avui `_break_idx_de` retorna None quan
#     l'etiqueta del break no és al run. El motor no té canal per dir «aquesta dada és dolenta»
#     (és una funció pura que retorna un float) i inventar-s'hi un valor seria pitjor.
#   · `valida_breaks` — el que guarda les QUATRE PORTES d'autoria. **Estricte**: aquí sí que hi
#     ha algú a qui dir-li que la regla que acaba d'escriure no vol dir res, i es diu amb 400.
#
# La distància entre els dos és la mateixa que ja hi ha entre `normalitza_logica` (sembra) i
# `es_linear_degenerada` (autoria), i per la mateixa raó.
# ─────────────────────────────────────────────────────────────────────────────────────────────

def _norm_label(v) -> str:
    """upper+strip — el criteri EXACTE del run i de `grading_utils._norm`. Afinar-lo aquí
    mouria GradedSpec ja emesos."""
    return str(v if v is not None else '').strip().upper()


def _posicions(run):
    return {_norm_label(x): i for i, x in enumerate(run or [])}


def intervals_en_index(breaks, run):
    """`breaks` (forma de BD) → `[(i_ini, i_fi, delta)]` en índexs del `run`, ordenats.

    LECTURA DEL MOTOR (tolerant, v. la nota de dalt):
      · forma invàlida, delta no numèric o `inici` que no és al run → l'interval s'IGNORA;
      · `final` que no és al run → es CLAVA a l'última talla del run. És el cas normal d'una
        regla d'1 break llegida com a interval quan el model no fabrica l'última talla del
        sistema, i clavar-lo hi diu exactament el mateix que deia el break: «d'aquí cap amunt».
    """
    if not breaks or not isinstance(breaks, (list, tuple)) or not run:
        return []
    pos = _posicions(run)
    out = []
    for it in breaks:
        if not isinstance(it, dict):
            continue
        delta = _f(it.get('delta'))
        if delta is None:
            continue
        i_ini = pos.get(_norm_label(it.get('inici')))
        if i_ini is None:
            continue
        i_fi = pos.get(_norm_label(it.get('final')))
        if i_fi is None:
            i_fi = len(run) - 1
        if i_fi < i_ini:
            continue
        out.append((i_ini, i_fi, delta))
    return sorted(out, key=lambda t: t[0])


def delta_de_posicio(idx, intervals, general):
    """El delta que mana a una posició del run: el del primer interval que la conté, o el
    GENERAL. Punt únic de la regla de lectura — la comparteixen el motor (per l'extrem exterior
    de cada aresta) i la validació de coherència (per als veïns d'un interval)."""
    for (ini, fi, delta) in intervals:
        if ini <= idx <= fi:
            return delta
    return general


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
