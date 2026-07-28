// Traçat de la ploma / fletxa curva: el node fantasma del doble clic.
//     cd frontend && node --test src/utils/tracatPloma.test.js
//
// EL CAS REAL: al corpus .ftt local hi ha fletxes curves desades amb els dos últims nodes a les
// MATEIXES coordenades (p. ex. 202.771/129.808 repetit) — el rastre del doble clic amb què
// s'intentava tancar el traçat. Aquell tram de llargada 0 és el que desorienta la punta.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { potTancar, treuAncoratgeFantasma } from './tracatPloma.js'

const n = (x, y, extra = {}) => ({ x, y, inX: 0, inY: 0, outX: 0, outY: 0, ...extra })

test('doble clic al final: el node repetit cau, el traçat queda de 2 nodes', () => {
  const pts = [n(10, 10), n(80, 40), n(80, 40)]
  assert.deepEqual(treuAncoratgeFantasma(pts), [n(10, 10), n(80, 40)])
})

test('el fantasma no cal que sigui exacte: dins dels 3 px també cau', () => {
  const pts = [n(10, 10), n(80, 40), n(81, 41)]
  assert.equal(treuAncoratgeFantasma(pts).length, 2)
})

test('mai baixa de 2 nodes: amb 2 clics idèntics no es toca res', () => {
  const pts = [n(10, 10), n(10, 10)]
  assert.deepEqual(treuAncoratgeFantasma(pts), pts)
})

test('nodes de debò separats: el traçat multi-node no es retalla', () => {
  const pts = [n(10, 10), n(80, 40), n(140, 90)]
  assert.deepEqual(treuAncoratgeFantasma(pts), pts)
})

test('si l\'últim node porta nanses és una corba volguda, encara que caigui a sobre', () => {
  const pts = [n(10, 10), n(80, 40), n(80, 40, { outX: 12, outY: -5, inX: -12, inY: 5 })]
  assert.deepEqual(treuAncoratgeFantasma(pts), pts)
})

test('entrades degenerades no peten', () => {
  assert.deepEqual(treuAncoratgeFantasma([]), [])
  assert.deepEqual(treuAncoratgeFantasma(null), null)
})

test('tancar demana dos ancoratges', () => {
  assert.equal(potTancar([n(0, 0)]), false)
  assert.equal(potTancar([n(0, 0), n(5, 5)]), true)
  assert.equal(potTancar(null), false)
})
