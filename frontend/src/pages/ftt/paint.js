// ════════════════════════════════════════════════════════════════════════════
// X2 — EL CONTRACTE DE PINTURA D'UN `path`
//
// Un objecte `path` té DOS nivells i cadascun és font de veritat del seu:
//
//   · l'OBJECTE SENCER  →  obj.stroke / obj.fill / obj.strokeWidth
//   · un SUBPATH concret →  paths[i].stroke / .fill / .strokeWidth
//
// LLEI DE LECTURA: el subpath mana sobre l'objecte. Absent (`undefined`/`null`)
// vol dir «no en tinc, hereta»; qualsevol altre valor —inclòs `'transparent'`—
// és una decisió de l'usuari i NO hereta.
//
// LLEI D'ESCRIPTURA: pintar l'OBJECTE SENCER esborra els sobreescrits dels seus
// subpaths (`sensePintura`). Sense això la llei de lectura deixaria l'ordre de
// l'usuari amagada per sempre sota un valor de subpath que ell no recorda haver
// posat — que és exactament el que passava.
//
// Aquestes funcions són l'ÚNICA porta: hi entren el llenç Konva viu, l'export a
// PDF i el sub-editor de Paper. Abans cadascú tenia la seva cascada i les seves
// invencions (el sub-editor, a més, amb la precedència al revés), i per això un
// mateix objecte es veia d'una manera dins del mode d'edició i d'una altra fora.
// ════════════════════════════════════════════════════════════════════════════

// Un color que no pinta res és `null`: ni cadena buida, ni 'none', ni degradats
// (que aquest editor no desa i que Konva no sabria pintar des d'aquí).
export function normalizePaint(value) {
  if (value == null || value === '' || value === 'none' || value === 'transparent') return null
  if (typeof value === 'string' && value.startsWith('url(')) return null
  return value
}

export function normalizeFillRule(value) {
  return value === 'evenodd' ? 'evenodd' : 'nonzero'
}

// L'ÚNIC valor inventat de tot el contracte, i només s'arriba a fer servir quan hi
// ha color de traç i ningú —ni el subpath ni l'objecte— n'ha dit el gruix. Cap
// altra cascada pot inventar-se un color: sense color no es pinta traç, i prou.
export const TRAC_PER_DEFECTE = 1.2

const hereta = (sub, obj) => (sub === undefined || sub === null ? obj : sub)

export function resolStroke(obj, path) {
  return normalizePaint(hereta(path?.stroke, obj?.stroke))
}

export function resolFill(obj, path) {
  return normalizePaint(hereta(path?.fill, obj?.fill))
}

export function resolStrokeWidth(obj, path) {
  const w = Number(hereta(path?.strokeWidth, obj?.strokeWidth))
  return Number.isFinite(w) && w >= 0 ? w : TRAC_PER_DEFECTE
}

// Treu d'un subpath els sobreescrits de les claus indicades, perquè torni a heretar
// de l'objecte. Retorna el mateix subpath si no en tenia cap (no fabrica objectes
// nous per no res: aquests arrays es comparen per referència a la història).
export function sensePintura(path, claus) {
  if (!path || !claus.some(k => k in path)) return path
  const net = { ...path }
  claus.forEach(k => delete net[k])
  return net
}
