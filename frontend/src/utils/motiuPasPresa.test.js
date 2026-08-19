// EL BANC DEL MOTIU — S42/F2.
//
//     node --test frontend/src/utils/motiuPasPresa.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { motiuPasPresa } from './motiuPasPresa.js'

test('🚨 1379 · amb els POM gravats i la graduació feta, el que falta és PROPAGAR', () => {
  // L'ESTAT REAL del model 1379 (BRW-FW26-0002) llegit de `grading-status` el 16/08/2026.
  // Aquest és el cas que va obrir F2: el rètol deia «Cal gravar el POM» amb el pas ① en ✓.
  const estatPas = {
    te_mesures: true, te_regles: true, te_taula: false, te_presa: false,
    te_propagacio: false, version_number: null,
  }

  assert.equal(motiuPasPresa(estatPas), 'model_sheet.pas_sense_propagacio')
  assert.notEqual(motiuPasPresa(estatPas), 'model_sheet.pas_sense_mesures')
})

test('mana el PRIMER pas que falta, no l\'últim', () => {
  // Sense mesures no es pot ni graduar ni propagar: dir-li «cal propagar» seria el mateix
  // error d'ara, girat. Es diu el pas que la persona pot fer ARA.
  assert.equal(motiuPasPresa({ te_mesures: false, te_regles: false, te_taula: false }),
    'model_sheet.pas_sense_mesures')
  assert.equal(motiuPasPresa({ te_mesures: true, te_regles: false, te_taula: false }),
    'model_sheet.pas_sense_regles')
})

test('amb taula no hi ha motiu: el pas és accessible', () => {
  assert.equal(motiuPasPresa({ te_mesures: true, te_regles: true, te_taula: true }), null)
  // I encara que l'estat sigui incoherent, `te_taula` mana: és el predicat que el backend
  // exigeix a `create-piece`, i el botó no pot ser més estricte que la porta que obre.
  assert.equal(motiuPasPresa({ te_mesures: false, te_regles: false, te_taula: true }), null)
})

test('sense resposta encara, el botó NO es bloqueja', () => {
  // Equivalència exacta amb el predicat que substitueix (`estatPas != null && !te_taula`):
  // no es tanca una porta per una cosa que no sabem.
  assert.equal(motiuPasPresa(null), null)
  assert.equal(motiuPasPresa(undefined), null)
})

test('CONTROL una-peça · un model acabat de propagar no canvia de comportament', () => {
  // El 100% del corpus d'una sola prenda passa per aquí igual que abans: hi ha taula → cap
  // motiu → el botó s'encén. F2 no toca cap predicat, només el que la pantalla EN DIU.
  assert.equal(motiuPasPresa({ te_mesures: true, te_regles: true, te_taula: true, te_presa: true }), null)
})
