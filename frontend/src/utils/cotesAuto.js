// Col·locació AUTOMÀTICA de cotes quan no hi ha precedent del catàleg.
//
// El camí bo és el precedent: una cota que ja es va col·locar sobre aquest croquis (o sobre la
// peça germana) sap on va. Però un document pot no tenir-ne cap —una foto, un croquis dibuixat
// aquí mateix— i llavors el botó automàtic no tenia res a fer i desapareixia. Aquesta és la
// segona via: repartir les cotes sobre la superfície que hi ha, en horitzontal i escalonades,
// perquè neixin totes visibles i separades. No pretén encertar la mesura: pretén que el tècnic
// les trobi dibuixades i només les hagi d'arrossegar al seu lloc.
//
// Tot en mm de document, i pur: cap dependència de Konva ni de l'estat de l'editor.

// Fracció de l'amplada de la superfície que ocupa cada fletxa, i marge interior.
const AMPLE = 0.6
const MARGE = 0.08

// Reparteix `n` cotes dins la bbox {minX,minY,maxX,maxY}. Retorna [{ax, ay, dx, dy}] amb
// l'origen de la fletxa i el seu vector, en l'ordre en què s'han demanat.
//
// Les files s'escalonen verticalment dins el marge; si n'hi ha més que files còmodes, es
// continuen repartint igual (mai s'apilen exactament al mateix punt: el pas mai és 0).
export function reparteixCotes(bbox, n) {
  if (!bbox || !(n > 0)) return []
  const w = (bbox.maxX - bbox.minX) || 1
  const h = (bbox.maxY - bbox.minY) || 1
  const ample = w * AMPLE
  const x0 = bbox.minX + (w - ample) / 2
  const dalt = bbox.minY + h * MARGE
  const util = h * (1 - 2 * MARGE)
  // n+1 intervals → cap cota no toca la vora de dalt ni la de baix.
  const pas = util / (n + 1)
  return Array.from({ length: n }, (_, i) => ({
    ax: x0,
    ay: dalt + pas * (i + 1),
    dx: ample,
    dy: 0,
  }))
}

// La superfície on col·locar: la MÉS GRAN de les candidates (el croquis mana sobre una icona
// perduda en una cantonada). `bboxDe` extreu la bbox de cada objecte. null si no n'hi ha cap
// —i llavors qui crida ha de dir per què no pot col·locar, no amagar el botó.
export function superficieDeCotes(objectes, bboxDe) {
  let millor = null
  let area = 0
  for (const o of objectes || []) {
    const bb = bboxDe(o)
    if (!bb) continue
    const a = Math.max(0, bb.maxX - bb.minX) * Math.max(0, bb.maxY - bb.minY)
    if (a > area) { area = a; millor = bb }
  }
  return area > 0 ? millor : null
}
