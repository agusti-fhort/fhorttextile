// EL BANC DEL MOTIU — S42/F2 · S45/B.
//
//     node --test frontend/src/utils/motiuPasPresa.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { motiuPasMesurarSet, motiuPasPresa } from './motiuPasPresa.js'

// ══ MESURAR PRENDA (pas ③) — NO exigeix propagat ══════════════════════════════════════

test('🚨 S45/B · un PROTO sense graduació ni propagació es pot MESURAR', () => {
  // La regla d'Agus (Patró C): un prototip pot arribar a la sala sense graduació definida.
  // El backend l'admet des de S45/B —versió buida + línies de la talla base— i el botó no
  // pot ser més estricte que la porta que obre.
  assert.equal(motiuPasPresa({
    te_mesures: true, te_regles: false, te_taula: false, te_propagacio: false,
  }), null)
})

test('🚨 1379 · amb els POM gravats i la graduació feta, la presa JA NO espera el propagat', () => {
  // L'ESTAT REAL del model 1379 (BRW-FW26-0002) llegit de `grading-status` el 16/08/2026.
  // Aquest estat era el cas que va obrir F2 i donava `pas_sense_propagacio`; amb S45/B el
  // pas ③ s'obre, perquè propagar és la feina de la porta ④ i no d'aquesta.
  const estatPas = {
    te_mesures: true, te_regles: true, te_taula: false, te_presa: false,
    te_propagacio: false, version_number: null,
  }
  assert.equal(motiuPasPresa(estatPas), null)
})

test('sense cap mesura no hi ha res a prendre, i és l\'ÚNIC motiu que queda', () => {
  assert.equal(motiuPasPresa({ te_mesures: false, te_regles: false, te_taula: false }),
    'model_sheet.pas_sense_mesures')
  // amb regles i tot: si no hi ha mesura base amb valor, la graella naixeria buida
  assert.equal(motiuPasPresa({ te_mesures: false, te_regles: true, te_taula: false }),
    'model_sheet.pas_sense_mesures')
})

test('sense resposta encara, el botó NO es bloqueja', () => {
  assert.equal(motiuPasPresa(null), null)
  assert.equal(motiuPasPresa(undefined), null)
})

test('CONTROL una-peça · un model acabat de propagar no canvia de comportament', () => {
  assert.equal(motiuPasPresa({
    te_mesures: true, te_regles: true, te_taula: true, te_presa: true,
  }), null)
})

// ══ MESURAR SET (tab Escalat) — SÍ que exigeix propagat ═══════════════════════════════

test('🚨 S45/B · el SET segueix exigint la taula: sense specs no hi ha full de set', () => {
  // `desa_presa_escalat` busca la línia de (POM, talla) i alça `PresaSenseLiniaError` si no
  // hi és. Sense `GradedSpec` només existeix la talla base: no hi ha set a mesurar.
  assert.equal(motiuPasMesurarSet({
    te_mesures: true, te_regles: true, te_taula: false,
  }), 'model_sheet.pas_sense_propagacio')
  assert.equal(motiuPasMesurarSet({
    te_mesures: true, te_regles: false, te_taula: false,
  }), 'model_sheet.pas_sense_regles')
})

test('el SET mana el PRIMER pas que falta, no l\'últim', () => {
  // Dir «cal propagar» a qui encara no ha gravat cap mesura seria el mateix error girat.
  assert.equal(motiuPasMesurarSet({ te_mesures: false, te_regles: false, te_taula: false }),
    'model_sheet.pas_sense_mesures')
})

test('amb taula el SET és accessible, i `te_taula` mana', () => {
  assert.equal(motiuPasMesurarSet({ te_mesures: true, te_regles: true, te_taula: true }), null)
  // encara que l'estat sigui incoherent: `te_taula` és el predicat que la presa d'escalat
  // necessita de debò, i el botó no pot ser més estricte que la porta que obre.
  assert.equal(motiuPasMesurarSet({ te_mesures: false, te_regles: false, te_taula: true }), null)
})

test('el SET tampoc no es bloqueja per una cosa que no sabem', () => {
  assert.equal(motiuPasMesurarSet(null), null)
  assert.equal(motiuPasMesurarSet(undefined), null)
})

// ══ I LES DUES PORTES NO SÓN LA MATEIXA ═══════════════════════════════════════════════

test('🔑 les dues portes DIVERGEIXEN exactament al cas del proto', () => {
  const proto = { te_mesures: true, te_regles: false, te_taula: false }
  assert.equal(motiuPasPresa(proto), null)                                  // es pot mesurar
  assert.equal(motiuPasMesurarSet(proto), 'model_sheet.pas_sense_regles')   // no es pot el set
})
