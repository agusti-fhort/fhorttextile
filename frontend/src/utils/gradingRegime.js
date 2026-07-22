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

/** Delta base efectiu d'una regla: forma canònica (increment_base) o fallback legacy (increment). */
function deltaBase(rule) {
  const ib = rule?.increment_base
  if (ib !== null && ib !== undefined && ib !== '') return Number(ib)
  const inc = rule?.increment
  if (inc !== null && inc !== undefined && inc !== '') return Number(inc)
  return 0
}

/** true si la regla porta un trencament informat (talla + valor). Amb break MAI és FIXED. */
function hasBreak(rule) {
  const lbl = rule?.talla_break_label
  const brk = rule?.increment_break
  if (lbl !== null && lbl !== undefined && String(lbl).trim() !== '') return true
  return brk !== null && brk !== undefined && brk !== '' && Number(brk) !== 0
}

/**
 * Règim EFECTIU d'una regla per a presentació.
 * LINEAR + delta 0 + sense break → 'FIXED'. Qualsevol altre cas → la lògica tal qual.
 * Valors de DADA (LINEAR/STEP/FIXED) — no es tradueixen.
 */
export function effectiveRegime(rule) {
  const logica = rule?.logica
  if (logica !== 'LINEAR') return logica
  if (hasBreak(rule)) return 'LINEAR'
  return deltaBase(rule) === 0 ? 'FIXED' : 'LINEAR'
}

/** true si la regla es presenta com a FIXED tot i estar desada com a LINEAR. */
export function isDegenerateLinear(rule) {
  return rule?.logica === 'LINEAR' && effectiveRegime(rule) === 'FIXED'
}
