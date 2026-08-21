// LLEI (Agus, 2026-07-22) — LINEAR amb increment 0 i SENSE break ÉS FIXED.
//
// Una regla LINEAR amb delta 0 no gradua res: matemàticament és idèntica a FIXED
// («aquesta mesura no canvia entre talles»), però es presenta com si gradués i
// fabrica taules planes que semblen graduades. El backend ja BLOQUEJA l'autoria de
// regles noves així (models_app/views.py, codi LINEAR_INCREMENT_ZERO) i una migració
// de dades ha convertit les preexistents; aquest helper és el punt ÚNIC de
// classificació per a la capa de presentació, perquè cap superfície torni a
// dibuixar LINEAR+0 encara que li arribi de dades velles, d'un import o d'un seed.
//
// Punt únic deliberat: les 4 superfícies (Escalat/PropagatedEditor, editor de regles
// del check, taula de GradingRuleSets, EditableTable) s'alimenten d'endpoints i
// serializers DIFERENTS; el denominador comú on convergeixen és el frontend.
//
// NO s'aplica a `EditableTable` (gènesi): allà el desplegable de règim és un control
// d'AUTORIA en curs — reinterpretar el valor mentre el tècnic encara no ha escrit el
// delta li canviaria la tria sota els dits. Les files ja desades hi arriben ja
// convertides per la migració de dades, així que el forat és teòric.

/**
 * Delta base efectiu d'una regla. Des del FIX-A/PAS-3: NOMÉS `increment_base`.
 *
 * 🚨 Aquí hi havia el fallback a `increment`, i era el MIRALL del que feia `_apply_rule`. El dia
 * que el motor va deixar de llegir el camp llegat, aquest mirall va quedar dient una cosa que ja
 * no és certa: hauria pintat «LINEAR amb delta 2.0, correcta» sobre una fila que el motor ja no
 * gradua. Va amb el seu bessó de backend (`pom/grading_regime.py`, `delta_base_efectiu`) i no
 * es poden separar — és literalment el que aquest fitxer declara ser.
 */
function deltaBase(rule) {
  const ib = rule?.increment_base
  if (ib !== null && ib !== undefined && ib !== '') return Number(ib)
  return 0
}

/** true si la regla porta un trencament informat (talla + valor). NO vol dir «gradua». */
function hasBreak(rule) {
  const lbl = rule?.talla_break_label
  const brk = rule?.increment_break
  if (lbl !== null && lbl !== undefined && String(lbl).trim() !== '') return true
  return brk !== null && brk !== undefined && brk !== '' && Number(brk) !== 0
}

// ── TRAM F · ELS INTERVALS ───────────────────────────────────────────────────────────────────
//
// MIRALL EXACTE de `pom/grading_regime.py`: allà hi ha la constant ÚNICA del backend i la
// validació que guarda les quatre portes; aquí hi ha el que la pantalla necessita saber per no
// oferir el que el servidor rebutjarà. Els dos no es poden separar — canviar el sostre en un
// dels dos costats faria que la pantalla i la porta diguessin coses diferents del mateix gest.
export const MAX_BREAKS = 3

/** Els intervals d'una regla, sempre com a llista (mai null). Camp de fila, com `valors_step`. */
export function intervalsDe(rule) {
  const b = rule?.breaks
  return Array.isArray(b) ? b : []
}

/** El delta d'un interval en número (o null): els inputs escriuen text i la coma decimal. */
function deltaInterval(iv) {
  const v = iv?.delta
  if (v === null || v === undefined || v === '') return null
  const n = Number(String(v).replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

/**
 * Règim EFECTIU d'una regla per a presentació.
 * LINEAR sense CAP delta diferent de 0 → 'FIXED'. Qualsevol altre cas → la lògica tal qual.
 * Valors de DADA (LINEAR/STEP/FIXED) — no es tradueixen.
 *
 * 🚨 TRAM F — abans n'hi havia prou amb `hasBreak` per declarar-la LINEAR, i era el mateix
 * forat que el defecte 4 de la diagnosi de PROD: una regla amb `ib=0 · brk=0` i talla de break
 * informada es presentava com a graduada i pintava una taula PLANA. El backend l'ha deixat de
 * deixar escriure (`es_linear_degenerada`) i aquest mirall va amb ell.
 */
export function effectiveRegime(rule) {
  const logica = rule?.logica
  if (logica !== 'LINEAR') return logica
  if (deltaBase(rule) !== 0) return 'LINEAR'
  const brk = rule?.increment_break
  if (brk !== null && brk !== undefined && brk !== '' && Number(brk) !== 0) return 'LINEAR'
  if (intervalsDe(rule).some(iv => (deltaInterval(iv) ?? 0) !== 0)) return 'LINEAR'
  return 'FIXED'
}

/** true si la regla porta relleu: un break d'1 tram o intervals. Per apagar controls, no per
 *  classificar el règim (això és `effectiveRegime`). */
export function teRelleu(rule) {
  return hasBreak(rule) || intervalsDe(rule).length > 0
}

/**
 * true si algun interval està a MITGES (li falta una talla o el Δ).
 *
 * Un interval neix buit de Δ —el gest és «afegeix-me'n un», no «tinc-ho tot decidit»— i el
 * backend el rebutjaria amb 400 `BREAKS_FORMA`. Val més que la pantalla ho digui A LA FILA que
 * no pas que la persona ho descobreixi en un toast després de prémer Gravar: és el mateix
 * criteri que ja regeix per a la LINEAR degenerada.
 */
export function intervalsIncomplets(rule) {
  return intervalsDe(rule).some(iv => !iv || !String(iv.inici || '').trim()
    || !String(iv.final || '').trim() || deltaInterval(iv) === null)
}

/** true si la regla es presenta com a FIXED tot i estar desada com a LINEAR. */
export function isDegenerateLinear(rule) {
  return rule?.logica === 'LINEAR' && effectiveRegime(rule) === 'FIXED'
}
