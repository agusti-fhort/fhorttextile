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


#: TRAM E · LA PORTA DEL VALOR VERMELL (2026-08-21, decisió d'Agus). Codis de rebuig d'editar
#: una cel·la que ha sortit amb el valor de la talla base prestat. La porta escriu `valors_step`
#: de la regla RESIDENT —mai un override—: v. `valida_valor_step`.
CODI_STEP_NO_ES_STEP = 'STEP_NO_ES_STEP'
CODI_STEP_TALLA_BASE = 'STEP_TALLA_BASE'
CODI_STEP_TALLA_FORANA = 'STEP_TALLA_FORANA'
CODI_STEP_VALOR = 'STEP_VALOR'
CODI_STEP_CAMI_INCOMPLET = 'STEP_CAMI_INCOMPLET'


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


def valida_breaks(breaks, logica=None, run=None, increment_base=None):
    """Valida els intervals d'AUTORIA. Retorna `(normalitzats, error)`.

    `normalitzats`: la llista tal com s'ha de DESAR —ordenada, deltes a float i etiquetes amb
    l'ortografia del run— o `None` si la regla no en porta cap (i llavors el camp es desa NULL:
    una llista buida i «no en té» han de ser la mateixa cosa a la BD).
    `error`: `{'codi', 'detall'}` o `None`.

    Les regles, totes decidides al brief del tram F:
      · només sota LINEAR (sota FIXED/ZERO no hi ha relleu; sota STEP el relleu és `valors_step`)
      · com a molt `MAX_BREAKS`
      · cal delta GENERAL (`increment_base`): sense corba de fons un interval no és un
        trencament de res, i el motor no emetria cap cel·la (llei D2)
      · etiquetes del run del SISTEMA de la regla, `inici` ≤ `final` en ordre de sistema
      · sense solapament
      · **delta ≠ delta adjacent**: un interval que repeteix el delta del seu veí (el general, o
        l'interval enganxat) no trenca res — o és soroll o és el mateix tram dit en dos trossos.

    ⚠️ SENSE RUN NO ES VALIDEN LES ETIQUETES (i es diu, no es dissimula): hi ha jocs de catàleg
    sense `size_system`, i el motor mateix hi resol el break per etiqueta contra el run que
    tingui. La forma, el recompte i el règim SÍ que es validen igualment.
    """
    if breaks in (None, '', [], ()):
        return None, None
    if not isinstance(breaks, (list, tuple)):
        return None, {'codi': CODI_BREAKS_FORMA,
                      'detall': "Els intervals han de venir com a llista "
                                "[{inici, final, delta}]."}
    items = list(breaks)
    if not items:
        return None, None
    if (logica or '').strip().upper() != 'LINEAR':
        return None, {'codi': CODI_BREAKS_NOMES_LINEAR,
                      'detall': ("Els intervals de graduació només tenen sentit sota LINEAR. "
                                 "Sota STEP el creixement viu als valors per talla; sota "
                                 "FIXED/ZERO la mesura no creix.")}
    if len(items) > MAX_BREAKS:
        return None, {'codi': CODI_BREAKS_MAX,
                      'detall': f"Com a màxim {MAX_BREAKS} intervals per regla."}
    general = _f(increment_base)
    if general is None:
        return None, {'codi': CODI_BREAKS_SENSE_GENERAL,
                      'detall': ("Una regla amb intervals necessita el seu Δ base: és el delta "
                                 "que mana fora dels intervals.")}

    etiquetes = [str(x).strip() for x in (run or [])]
    pos = _posicions(etiquetes)
    nets = []
    for it in items:
        if not isinstance(it, dict) or 'inici' not in it or 'final' not in it:
            return None, {'codi': CODI_BREAKS_FORMA,
                          'detall': "Cada interval vol talla d'inici, talla final i Δ."}
        delta = _f(it.get('delta'))
        if delta is None:
            return None, {'codi': CODI_BREAKS_FORMA,
                          'detall': "El Δ d'un interval ha de ser un número."}
        ini_raw, fi_raw = it.get('inici'), it.get('final')
        if _norm_label(ini_raw) == '' or _norm_label(fi_raw) == '':
            return None, {'codi': CODI_BREAKS_FORMA,
                          'detall': "Cada interval vol talla d'inici i talla final."}
        if etiquetes:
            i_ini, i_fi = pos.get(_norm_label(ini_raw)), pos.get(_norm_label(fi_raw))
            if i_ini is None or i_fi is None:
                forana = ini_raw if i_ini is None else fi_raw
                return None, {'codi': CODI_BREAKS_TALLA_FORANA,
                              'detall': (f"La talla «{forana}» no és al sistema de talles "
                                         f"d'aquesta regla ({' · '.join(etiquetes)}).")}
            if i_fi < i_ini:
                return None, {'codi': CODI_BREAKS_ORDRE,
                              'detall': (f"L'interval «{ini_raw} → {fi_raw}» va del revés: la "
                                         "talla d'inici ha d'anar abans que la final.")}
            nets.append({'inici': etiquetes[i_ini], 'final': etiquetes[i_fi], 'delta': delta,
                         '_i': i_ini, '_f': i_fi})
        else:
            nets.append({'inici': str(ini_raw).strip(), 'final': str(fi_raw).strip(),
                         'delta': delta, '_i': None, '_f': None})

    if etiquetes:
        nets.sort(key=lambda d: d['_i'])
        for anterior, seguent in zip(nets, nets[1:]):
            if seguent['_i'] <= anterior['_f']:
                return None, {'codi': CODI_BREAKS_SOLAPAMENT,
                              'detall': (f"Els intervals «{anterior['inici']} → "
                                         f"{anterior['final']}» i «{seguent['inici']} → "
                                         f"{seguent['final']}» es trepitgen.")}
        # Coherència: un interval que diu el mateix que el seu veí no trenca res.
        idx = [(d['_i'], d['_f'], d['delta']) for d in nets]
        for d in nets:
            veins = [p for p in (d['_i'] - 1, d['_f'] + 1) if 0 <= p < len(etiquetes)]
            for p in veins:
                if abs(delta_de_posicio(p, idx, general) - d['delta']) < 0.0001:
                    return None, {
                        'codi': CODI_BREAKS_DELTA_REDUNDANT,
                        'detall': (f"L'interval «{d['inici']} → {d['final']}» té el mateix Δ "
                                   f"({d['delta']}) que el tram del costat: no trenca res. "
                                   "Canvia'n el Δ o esborra l'interval.")}

    return [{'inici': d['inici'], 'final': d['final'], 'delta': d['delta']} for d in nets], None


def valida_valor_step(logica, talla, valor, base_label, run):
    """Valida l'edició del valor d'UNA talla d'una regla STEP. Retorna `(valor, error)`.

    Punt únic de la porta, com `valida_breaks` ho és de la dels intervals. El que decideix:

      · **només sota STEP.** Sota LINEAR el valor d'una talla no s'escriu: es deriva del Δ, i
        voler-lo escriure vol dir canviar la regla o posar-hi un override (que és una altra
        porta i una altra semàntica).
      · **la talla BASE no.** El seu valor viu a `BaseMeasurement` i s'edita com a mesura base
        — la mateixa llei que ja tenia la porta d'override.
      · **la talla ha de ser del run** que el motor recorre.
      · **el valor ha de ser un número.** El 0 hi és legítim (una mesura pot no créixer en un
        tram); el que no hi és és el buit disfressat.

    ⚠️ NO valida el CAMÍ (que els deltes de les talles que hi ha entre la base i aquesta hi
    siguin): això és geometria del motor i el decideix `grading_utils.step_delta_acumulat`, que
    és qui sap dir quina etiqueta falta. La porta l'ha de consultar i rebutjar amb
    `CODI_STEP_CAMI_INCOMPLET` — v. l'acta de la vista.
    """
    if (logica or '').strip().upper() != 'STEP':
        return None, {'codi': CODI_STEP_NO_ES_STEP,
                      'detall': ("Aquest valor només s'edita quan la regla és STEP. Amb una "
                                 "regla LINEAR el valor d'una talla surt del Δ: canvia la "
                                 "regla des de Graduació.")}
    et = _norm_label(talla)
    if et == '':
        return None, {'codi': CODI_STEP_TALLA_FORANA, 'detall': "Falta la talla."}
    if et == _norm_label(base_label):
        return None, {'codi': CODI_STEP_TALLA_BASE,
                      'detall': ("La talla base s'edita com a mesura base, no com a valor de "
                                 "la regla.")}
    etiquetes = [str(x).strip() for x in (run or [])]
    if not etiquetes or et not in [_norm_label(x) for x in etiquetes]:
        return None, {'codi': CODI_STEP_TALLA_FORANA,
                      'detall': f"La talla «{talla}» no és al run d'aquest model."}
    v = _f(valor)
    if v is None:
        return None, {'codi': CODI_STEP_VALOR, 'detall': "El valor ha de ser un número."}
    return v, None


def es_linear_degenerada(logica, increment_base=None, increment=None,
                         increment_break=None, talla_break_label=None, breaks=None) -> bool:
    """True si la regla és LINEAR però matemàticament FIXED: CAP delta en joc és diferent de 0.

    ── LA LLEI, DITA SENCERA (Agus, 21/08, del passi visual del banc) ──────────────────────────

        DEGENERADA  ⟺  delta general == 0  I  cap interval amb delta ≠ 0

    Els tres casos que això cobreix, i cap d'ells és nou —la funció ja els feia des del tram F—,
    però convé que estiguin escrits perquè el dubte no torni a costar una diagnosi:

      · sense breaks i general 0 ................. degenerada (com sempre)
      · general 0 amb QUALSEVOL tram viu ......... **LEGAL** ← el cas canònic del disseny
        d'intervals: «XXS→XS no creix, a partir de S creix 2». És la F del 1383.
      · tot a zero amb breaks informats .......... degenerada, i el missatge d'aquí val
        («fes-la FIXED o esborra-la»)

    🔑 I LA FORMA VELLA HI COMPTA IGUALMENT, perquè les tres superfícies conviuen: una regla no
    migrada amb `ib=0` i `increment_break=2` segueix sent LINEAR de ple dret. El guard llegeix
    les DUES formes perquè cap regla es quedi fora de la llei per no haver passat encara per la
    pantalla nova.

    🚨 TRAM F — EL DEUTE «LINEAR+0 AMB BREAK» (defecte 4 de la diagnosi de PROD §A.5).
    Aquí hi havia `if te_break(...): return False` a seques: n'hi havia prou d'informar una talla
    de break perquè una regla amb els DOS deltes a zero passés la porta i es presentés com a
    LINEAR. Al model 1215 de PROD n'hi ha CINC així (`G1`, `SLT`, `EK2`, `E5`, `U`:
    `ib=0 · brk=0 · break M`) i produeixen exactament el que la llei A3 volia tancar: una taula
    PLANA que es diu graduada. El break no és una excepció a la llei, és una segona manera
    d'informar el relleu — i un relleu de zero no és relleu.

    El que NO canvia: amb break i un delta no-zero (el cas normal `ib=0 · brk=1.5`, un sostre a
    l'inrevés) la regla segueix sent LINEAR de ple dret. `te_break` es conserva perquè diu una
    altra cosa —«hi ha trencament informat»— i té lector propi a la UI.

    ⚠️ Aquesta funció NO toca cap fila existent: és una porta d'AUTORIA. Les 9 regles d'aquesta
    forma que viuen al banc 1383 es queden com són (dades vives, precedent del ruleset 115) i el
    banc les segueix graduant igual. El que canvia és que no se'n pot escriure cap de nova.
    """
    if (logica or '').strip().upper() != 'LINEAR':
        return False
    if delta_base_efectiu(increment_base, increment) != 0.0:
        return False
    brk = _f(increment_break)
    if brk not in (None, 0.0):
        return False
    for it in (breaks or []):
        if isinstance(it, dict) and (_f(it.get('delta')) or 0.0) != 0.0:
            return False
    return True


def normalitza_logica(logica, increment_base=None, increment=None,
                      increment_break=None, talla_break_label=None, breaks=None) -> str:
    """Règim que s'ha de DESAR. LINEAR degenerada → 'FIXED'; la resta, sense tocar."""
    if es_linear_degenerada(logica, increment_base, increment,
                            increment_break, talla_break_label, breaks):
        return 'FIXED'
    return logica
