// P6 — el suggerit de l'item (V1) al RuleSetPicker.
//
// El projecte no té harness de test de frontend (ni vitest ni jest): aquests van amb el
// runner natiu de Node, que ja llegeix ESM perquè el package és "type": "module".
//     cd frontend && node --test src/components/grading/gradingAxes.test.js
//
// La llei que defensen: SUGGERIR ≠ ARROSSEGAR. El suggerit canvia l'ORDRE de presentació i
// res més — mai el conjunt de candidats (això el decideix el matching d'eixos) i mai
// l'assignació (això la decideix el clic del tècnic).

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { orderWithSuggestedFirst } from './gradingAxes.js'

const A = { id: 75, nom: 'EU Woven Woman Regular' }
const B = { id: 115, nom: 'BRW · Blusa · ALPHA_EU_W' }
const C = { id: 124, nom: 'Prova BRW ALPHA UE' }

test('present als candidats → puja primer', () => {
  assert.deepEqual(
    orderWithSuggestedFirst([A, B, C], 115).map(r => r.id),
    [115, 75, 124],
  )
})

test('present però ja primer → llista intacta (mateixa referència)', () => {
  const m = [B, A, C]
  assert.equal(orderWithSuggestedFirst(m, 115), m)
})

test('absent dels candidats → cap efecte', () => {
  // El cas real: l'item porta un ruleset que els eixos del model no seleccionen. No
  // s'injecta — el ventall no creix mai per la porta del suggeriment.
  const m = [A, C]
  assert.equal(orderWithSuggestedFirst(m, 115), m)
  assert.deepEqual(orderWithSuggestedFirst(m, 115).map(r => r.id), [75, 124])
})

test("l'item sense estàndard (null) → cap efecte", () => {
  const m = [A, B, C]
  assert.equal(orderWithSuggestedFirst(m, null), m)
})

test('no altera mai el conjunt, només l’ordre', () => {
  const m = [A, B, C]
  const out = orderWithSuggestedFirst(m, 115)
  assert.deepEqual(new Set(out.map(r => r.id)), new Set(m.map(r => r.id)))
  assert.equal(out.length, m.length)
})

test('llista buida → buida', () => {
  assert.deepEqual(orderWithSuggestedFirst([], 115), [])
})
