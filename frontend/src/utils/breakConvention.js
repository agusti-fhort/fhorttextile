// LA CONVENCIÓ DE LA TALLA DE BREAK — un sol lloc per a tota la casa (Agus, 2026-08-10).
//
// 🔑 DUES CONVENCIONS PER AL MATEIX PUNT, I CAP DE LES DUES ÉS «LA CORRECTA»:
//
//     DOCUMENT   l'ÚLTIMA talla del tram petit    ← com ho escriu el full del client
//     MOTOR      la PRIMERA talla del tram gran   ← com ho desa la BD i com ho llegeix
//                                                   `grading_utils._break_idx_de`
//
// Són el mateix punt dit de dues bandes i es tradueixen amb un desplaçament d'UNA POSICIÓ dins
// el run: amb `[XXS, XS, S, M, L, …]`, el document diu `XS` on la BD desa `S`.
//
// 🚨 **LA DADA NO ES TOCA.** Contrastat el 10/08 amb `ops/qa/qa_contrast_sembra3.py`:
// `SEMBRA_3_grading_brownie.csv` ↔ ruleset 219 = **142/142 casen, 0 divergències**. El que
// canvia és NOMÉS com es PRESENTA: la BD segueix guardant la convenció del motor, perquè moure
// la dada desplaçaria la graduació una talla sencera per a 98 regles.
//
// Per això les dues funcions van SEMPRE aparellades a cada superfície: `aDocument` just abans
// de pintar, `aMotor` just abans de desar. Una superfície que en faci servir només una menteix.
//
// ⚠️ SENSE RUN NO HI HA TRADUCCIÓ POSSIBLE, i inventar-se-la seria pitjor que no fer-la: una
// etiqueta desplaçada per error és indistingible d'una de correcta. Quan el run no hi és o
// l'etiqueta no hi cau, les funcions tornen `null` i el que crida ha de pintar «—». Cap
// superfície no ha de passar per aquí sense el run del joc o del model.

/** Normalitza el run: accepta `['XXS','XS',…]` o `[{etiqueta}]`, i sempre torna etiquetes. */
export function etiquetesDelRun(run) {
  if (!Array.isArray(run)) return []
  return run
    .map(s => (typeof s === 'string' ? s : s?.etiqueta ?? s?.label ?? ''))
    .map(s => String(s).trim())
    .filter(Boolean)
}

const norm = (v) => String(v ?? '').trim().toUpperCase()

/** Posició d'una etiqueta dins el run, comparant com ho fa el motor (`_norm`: upper+strip). */
function posicio(etiqueta, run) {
  if (etiqueta === null || etiqueta === undefined || String(etiqueta).trim() === '') return -1
  const n = etiquetesDelRun(run).map(norm)
  return n.indexOf(norm(etiqueta))
}

/**
 * MOTOR → DOCUMENT. El que hi ha desat, tal com s'ha de PINTAR.
 * `null` si no es pot traduir (sense run, etiqueta forana, o cau a la primera talla del run,
 * que no té anterior i per tant no té nom en convenció de document).
 */
export function aDocument(etiquetaMotor, run) {
  const i = posicio(etiquetaMotor, run)
  return i > 0 ? etiquetesDelRun(run)[i - 1] : null
}

/**
 * DOCUMENT → MOTOR. El que s'ha triat a pantalla, tal com s'ha de DESAR.
 * `null` si no es pot traduir (inclosa l'última talla del run, que no té següent).
 */
export function aMotor(etiquetaDocument, run) {
  const i = posicio(etiquetaDocument, run)
  const et = etiquetesDelRun(run)
  return i >= 0 && i + 1 < et.length ? et[i + 1] : null
}

/**
 * Les talles que es poden OFERIR en convenció de document: totes menys l'última, perquè un
 * break a l'última no té talla següent on començar el tram gran i no és representable.
 */
export function opcionsDocument(run) {
  const et = etiquetesDelRun(run)
  return et.slice(0, Math.max(0, et.length - 1))
}

/**
 * L'etiqueta compacta d'una regla per a mesures i repàs: `+1 · trencament XS +3`.
 * Torna `''` quan no hi ha res a dir. `tBreak` és el rètol ja traduït («trencament»).
 * Sense run traduïble el break s'OMET i queda el delta base: val més dir menys que dir-ho mal.
 */
export function etiquetaRegla({ increment_base, increment_break, talla_break_label }, run, tBreak) {
  if (increment_base === null || increment_base === undefined) return ''
  const doc = increment_break !== null && increment_break !== undefined && talla_break_label
    ? aDocument(talla_break_label, run) : null
  return doc
    ? `+${increment_base} · ${tBreak} ${doc} +${increment_break}`
    : `+${increment_base}`
}
