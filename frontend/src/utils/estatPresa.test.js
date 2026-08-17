// Banc d'`estatDeLaPresa` — E1/B3.
//     cd frontend && node --test src/utils/estatPresa.test.js

import test from 'node:test'
import assert from 'node:assert/strict'
import { BUIDA, DECIDIDA, MESURANT, SENSE_PRESA, estatDeLaPresa } from './estatPresa.js'

const payload = (resum, oberta = true) => ({
  presa_oberta: oberta,
  session: { id: 7, data: '2026-08-17', estat: 'Oberta' },
  resum: { n_preses: 0, n_linies: 10, talles_amb_presa: [],
           pendents_base: 2, decidides_base: 0, ...resum },
})

test('sense payload (la crida ha fallat) NO s\'inventa una presa oberta', () => {
  const e = estatDeLaPresa(null)
  assert.equal(e.estat, SENSE_PRESA)
  assert.equal(e.n_preses, 0)
  assert.equal(e.session, null)
})

test('presa_oberta false → SENSE_PRESA', () => {
  assert.equal(estatDeLaPresa(payload({}, false)).estat, SENSE_PRESA)
})

test('oberta i sense cap mesura → BUIDA', () => {
  const e = estatDeLaPresa(payload({}))
  assert.equal(e.estat, BUIDA)
  assert.equal(e.n_linies, 10)
  assert.equal(e.session.id, 7)
})

test('mesurant: hi ha preses i queda base per decidir', () => {
  const e = estatDeLaPresa(payload({ n_preses: 3, talles_amb_presa: ['S', 'L', 'XL'] }))
  assert.equal(e.estat, MESURANT)
  assert.deepEqual(e.talles, ['S', 'L', 'XL'])
  assert.equal(e.pendents_base, 2)
})

test('🔑 amb DUES prendes, una base decidida NO tanca la feina', () => {
  // El cas que un `decidides_base > 0` donaria per fet quan la meitat no ho està.
  const e = estatDeLaPresa(payload({ n_preses: 3, decidides_base: 1, pendents_base: 1 }))
  assert.equal(e.estat, MESURANT)
})

test('decidida: cap base pendent', () => {
  const e = estatDeLaPresa(payload({ n_preses: 3, decidides_base: 2, pendents_base: 0 }))
  assert.equal(e.estat, DECIDIDA)
})

test('mesurada però amb 0 bases al model no es queda a MESURANT per sempre', () => {
  // Un model sense línia de base (cas degenerat): sense pendents, la feina d'aquí està feta.
  const e = estatDeLaPresa(payload({ n_preses: 1, pendents_base: 0, decidides_base: 0 }))
  assert.equal(e.estat, DECIDIDA)
})

test('un resum absent no peta i no menteix', () => {
  const e = estatDeLaPresa({ presa_oberta: true })
  assert.equal(e.estat, BUIDA)
  assert.deepEqual(e.talles, [])
})
