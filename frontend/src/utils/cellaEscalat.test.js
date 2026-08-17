// Banc de `cellaEscalat` — E1/B3.
//     cd frontend && node --test src/utils/cellaEscalat.test.js

import test from 'node:test'
import assert from 'node:assert/strict'
import { cellaEscalat } from './cellaEscalat.js'

const PRESA = { teoric: 52, real: 53.4, desviacio: 1.4, estat: '' }

test('E2a · DUES columnes per talla: la Mesura (teòrica) i el Fit actual', () => {
  const c = cellaEscalat({ lineId: 'x:L', vigent: 52, presa: PRESA })
  assert.deepEqual(c.history, { teorica: 52 })   // una sola referència, no dues iguals
  assert.equal(c.active.value, 53.4)             // la peça arribada
})

test('E2a · després de propagar, la MESURA segueix sent la TEÒRICA de la presa', () => {
  // La presa es va fer contra 52; la base s'ha decidit i la corba ha pujat a 54. La columna
  // NO passa a 54: si ho fes, el vermell de R1 canviaria de significat a mitja feina.
  const c = cellaEscalat({ lineId: 'x:L', vigent: 54, presa: PRESA })
  assert.equal(c.history.teorica, 52)
  assert.equal(c.active.baseValue, 52)
  assert.equal(c.active.value, 53.4)
})

test('🔑 EL REFERENT DEL VERMELL ÉS LA TEÒRICA, no la corba vigent', () => {
  // Sense això, després d'una propagació TOTES les cel·les es tornarien vermelles soles.
  const c = cellaEscalat({ lineId: 'x:L', vigent: 54, presa: PRESA })
  assert.equal(c.active.baseValue, 52)
})

test('E2b · una cel·la sense mesurar surt PRE-OMPLERTA amb la teòrica, i és FANTASMA', () => {
  // ⚠️ CANVI DE LLEI (E2b, QA d'Agus 17/08). Abans aquest test deia «surt BUIDA»: la modista
  // havia de reteclejar la xifra que ja hi era per confirmar que la peça hi coincideix. Ara la
  // xifra hi surt, però marcada com a fantasma —es veu i no afirma res—, i només passa a ser
  // presa quan algú la toca o la confirma.
  const c = cellaEscalat({ lineId: 'x:L', vigent: 52, presa: { teoric: 52, real: null, desviacio: null, estat: '' } })
  assert.equal(c.active.value, 52, 'la cel·la no comença buida')
  assert.equal(c.active.fantasma, true, 'però NO és una presa')
  assert.equal(c.active.desviacio, null, 'i no hi ha desviació: ningú no ha mesurat')
})

test('E2b · una presa de debò NO és fantasma, encara que coincideixi amb la teòrica', () => {
  // El cas que `presa_at` fa possible al backend: confirmar la teòrica tal qual. Aquí es veu
  // el reflex a la cel·la — mateix número que el fantasma, i estat oposat.
  const c = cellaEscalat({ lineId: 'x:L', vigent: 52, presa: { teoric: 52, real: 52, desviacio: 0, estat: '' } })
  assert.equal(c.active.value, 52)
  assert.equal(c.active.fantasma, false, 'algú l\'ha confirmada: ja no és pre-omplert')
  assert.equal(c.active.desviacio, 0, 'desviació 0 NO és «no mesurat»')
})

test('sense presa oberta es cau a la corba vigent, i el pre-omplert també hi cau', () => {
  const c = cellaEscalat({ lineId: 'x:L', vigent: 52 })
  assert.equal(c.history.teorica, 52)
  assert.equal(c.active.value, 52, 'E2b: mai buida')
  assert.equal(c.active.fantasma, true, 'i sense presa oberta res pot ser una presa')
  assert.equal(c.active.baseValue, 52)
  assert.equal(c.active.estat, '')
})

test('el veredicte i la desviació viatgen resolts pel servidor, no recalculats', () => {
  const c = cellaEscalat({ lineId: 'x:M', vigent: 50, presa: { teoric: 50, real: 44, desviacio: -6, estat: 'REJECTED' } })
  assert.equal(c.active.estat, 'REJECTED')
  assert.equal(c.active.desviacio, -6)
})

test('una talla sense corba vigent no peta i no s\'inventa cap referent', () => {
  // Sense teòrica NO hi ha pre-omplert: el fantasma és la teòrica, i si no n'hi ha, la cel·la
  // segueix buida. Inventar-hi un `0` seria posar-hi una mesura que ningú no ha calculat.
  const c = cellaEscalat({ lineId: 'x:XXL' })
  assert.deepEqual(c.history, { teorica: null })
  assert.equal(c.active.value, '')
  assert.equal(c.active.fantasma, false)
  assert.equal(c.active.baseValue, null)
})

test('el `0` és un valor i no es confon amb el buit', () => {
  const c = cellaEscalat({ lineId: 'x:L', vigent: 0, presa: { teoric: 0, real: 0, desviacio: 0, estat: '' } })
  assert.equal(c.active.value, 0)
  assert.equal(c.active.baseValue, 0)
  assert.equal(c.history.teorica, 0)
})
