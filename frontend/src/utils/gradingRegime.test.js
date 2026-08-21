// EL MIRALL DEL RÈGIM — i el deute que el TRAM F hi tanca.
//
//     node --test frontend/src/utils/gradingRegime.test.js
//
// `gradingRegime.js` és el mirall de `pom/grading_regime.py`: si els dos deixen de dir el
// mateix, la pantalla dibuixa com a graduada una regla que la porta rebutja (o al revés). El
// cas nou és el defecte 4 de la diagnosi de PROD: `ib=0 · brk=0` amb talla de break informada
// **no gradua res** i es presentava com a LINEAR — una taula plana que sembla graduació.
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { MAX_BREAKS, effectiveRegime, intervalsDe, isDegenerateLinear, teRelleu } from './gradingRegime.js'

test('el sostre és el mateix que el del backend', () => {
  assert.equal(MAX_BREAKS, 3)
})

test('LINEAR+0 sense break segueix sent FIXED (llei A3)', () => {
  assert.equal(effectiveRegime({ logica: 'LINEAR', increment_base: 0 }), 'FIXED')
  assert.equal(effectiveRegime({ logica: 'LINEAR', increment_base: 1.5 }), 'LINEAR')
  assert.equal(effectiveRegime({ logica: 'STEP', increment_base: 0 }), 'STEP')
})

test('🚨 LINEAR amb ib=0, brk=0 i talla de break ÉS FIXED (defecte 4)', () => {
  assert.equal(
    effectiveRegime({ logica: 'LINEAR', increment_base: 0, increment_break: 0, talla_break_label: 'M' }),
    'FIXED')
  assert.equal(
    isDegenerateLinear({ logica: 'LINEAR', increment_base: 0, increment_break: 0, talla_break_label: 'M' }),
    true)
})

test('un sostre a l\'inrevés (0 fins al break, 1.5 després) SÍ que gradua', () => {
  assert.equal(
    effectiveRegime({ logica: 'LINEAR', increment_base: 0, increment_break: 1.5, talla_break_label: 'M' }),
    'LINEAR')
})

test('els intervals compten com a relleu, i els de delta 0 no', () => {
  const ambDelta = { logica: 'LINEAR', increment_base: 0, breaks: [{ inici: 'M', final: 'L', delta: 2 }] }
  const totZero = { logica: 'LINEAR', increment_base: 0, breaks: [{ inici: 'M', final: 'L', delta: 0 }] }
  assert.equal(effectiveRegime(ambDelta), 'LINEAR')
  assert.equal(effectiveRegime(totZero), 'FIXED')
  assert.equal(teRelleu(ambDelta), true)
  assert.equal(teRelleu({ logica: 'LINEAR', increment_base: 2 }), false)
})

test('intervalsDe sempre torna llista (mai null): és camp de fila, com valors_step', () => {
  assert.deepEqual(intervalsDe({ breaks: null }), [])
  assert.deepEqual(intervalsDe(undefined), [])
  assert.deepEqual(intervalsDe({ breaks: [{ inici: 'M', final: 'L', delta: 3 }] }),
    [{ inici: 'M', final: 'L', delta: 3 }])
})
