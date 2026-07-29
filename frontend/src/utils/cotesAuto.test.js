// Col·locació automàtica de cotes sense precedent.
//     cd frontend && node --test src/utils/cotesAuto.test.js
//
// LA REGRESSIÓ QUE FIXA: el botó d'assignació automàtica només sabia col·locar des del
// precedent del catàleg. Un document amb una foto i cap croquis de catàleg (DALIA) no en tenia
// mai, i el botó no arribava a sortir. Ara hi ha una segona via que només necessita una
// superfície.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { reparteixCotes, superficieDeCotes } from './cotesAuto.js'

const bbox = { minX: 0, minY: 0, maxX: 100, maxY: 200 }

test('cada cota neix dins la superfície', () => {
  for (const c of reparteixCotes(bbox, 6)) {
    assert.ok(c.ax >= bbox.minX && c.ax + c.dx <= bbox.maxX, 'x dins')
    assert.ok(c.ay >= bbox.minY && c.ay <= bbox.maxY, 'y dins')
  }
})

test('cap cota no cau damunt d\'una altra', () => {
  const ys = reparteixCotes(bbox, 8).map(c => c.ay)
  assert.equal(new Set(ys).size, ys.length)
})

test('són horitzontals i totes de la mateixa llargada', () => {
  const cs = reparteixCotes(bbox, 4)
  assert.ok(cs.every(c => c.dy === 0))
  assert.equal(new Set(cs.map(c => c.dx)).size, 1)
  assert.ok(cs[0].dx > 0)
})

test('l\'ordre demanat és l\'ordre de dalt a baix', () => {
  const ys = reparteixCotes(bbox, 5).map(c => c.ay)
  assert.deepEqual(ys, [...ys].sort((a, b) => a - b))
})

test('moltes cotes en poc espai: se separen igual, mai al mateix punt', () => {
  const ys = reparteixCotes({ minX: 0, minY: 0, maxX: 10, maxY: 10 }, 40).map(c => c.ay)
  assert.equal(new Set(ys).size, 40)
})

test('demanar-ne cap o sense superfície no peta', () => {
  assert.deepEqual(reparteixCotes(bbox, 0), [])
  assert.deepEqual(reparteixCotes(null, 3), [])
})

test('la superfície és la MÉS GRAN de les candidates', () => {
  const objs = [
    { id: 'petit', bb: { minX: 0, minY: 0, maxX: 10, maxY: 10 } },
    { id: 'gran', bb: { minX: 20, minY: 20, maxX: 120, maxY: 220 } },
  ]
  assert.deepEqual(superficieDeCotes(objs, o => o.bb), objs[1].bb)
})

test('sense candidates (o totes degenerades) no hi ha superfície', () => {
  assert.equal(superficieDeCotes([], () => null), null)
  assert.equal(superficieDeCotes([{}], () => ({ minX: 5, minY: 5, maxX: 5, maxY: 5 })), null)
})
