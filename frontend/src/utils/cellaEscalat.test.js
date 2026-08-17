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

test('una cel·la sense mesurar surt BUIDA, no a zero', () => {
  const c = cellaEscalat({ lineId: 'x:L', vigent: 52, presa: { teoric: 52, real: null, desviacio: null, estat: '' } })
  assert.equal(c.active.value, '')
  assert.equal(c.active.desviacio, null)
})

test('sense presa oberta es cau a la corba vigent i no hi ha arribada', () => {
  const c = cellaEscalat({ lineId: 'x:L', vigent: 52 })
  assert.equal(c.history.teorica, 52)
  assert.equal(c.active.value, '')
  assert.equal(c.active.baseValue, 52)
  assert.equal(c.active.estat, '')
})

test('el veredicte i la desviació viatgen resolts pel servidor, no recalculats', () => {
  const c = cellaEscalat({ lineId: 'x:M', vigent: 50, presa: { teoric: 50, real: 44, desviacio: -6, estat: 'REJECTED' } })
  assert.equal(c.active.estat, 'REJECTED')
  assert.equal(c.active.desviacio, -6)
})

test('una talla sense corba vigent no peta i no s\'inventa cap referent', () => {
  const c = cellaEscalat({ lineId: 'x:XXL' })
  assert.deepEqual(c.history, { teorica: null })
  assert.equal(c.active.value, '')
  assert.equal(c.active.baseValue, null)
})

test('el `0` és un valor i no es confon amb el buit', () => {
  const c = cellaEscalat({ lineId: 'x:L', vigent: 0, presa: { teoric: 0, real: 0, desviacio: 0, estat: '' } })
  assert.equal(c.active.value, 0)
  assert.equal(c.active.baseValue, 0)
  assert.equal(c.history.teorica, 0)
})
