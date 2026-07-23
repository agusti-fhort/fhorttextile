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

import { classifyRuleSets, orderWithSuggestedFirst } from './gradingAxes.js'

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

// ── C5 · LLEI DELS WIZARDS ELIMINATIUS (2026-07-23) ────────────────────────────
// La llei que defensen: seleccionar ATENUA I REORDENA, mai amaga. El conjunt de sortida ha de
// tenir SEMPRE la mida del d'entrada; el que canvia és el veredicte i l'ordre.

const RS = (id, extra = {}) => ({ id, nom: `RS${id}`, targets_codis: [], ...extra })

test('cap eix triat → tot compatible, ordre intacte', () => {
  const rss = [RS(1, { targets_codis: ['WOMAN'] }), RS(2, { construction_codi: 'KNIT' })]
  const out = classifyRuleSets(rss, {}, {})
  assert.deepEqual(out.map(x => x.rs.id), [1, 2])
  assert.ok(out.every(x => x.compatible && x.motius.length === 0))
})

test('un eix que no casa → incompatible AMB MOTIU, mai fora de la llista', () => {
  const rss = [RS(1, { targets_codis: ['MAN'] }), RS(2, { targets_codis: ['WOMAN'] })]
  const out = classifyRuleSets(rss, { target: 'WOMAN' }, {})
  assert.equal(out.length, 2)                       // res amagat
  assert.deepEqual(out.map(x => x.rs.id), [2, 1])   // compatible amunt
  assert.deepEqual(out[1].motius, ['target'])
})

test('acumula tots els motius, no només el primer', () => {
  const rss = [RS(1, { targets_codis: ['MAN'], construction_codi: 'WOVEN', fit_type_codi: 'SLIM' })]
  const out = classifyRuleSets(rss, { target: 'WOMAN', construction: 'KNIT', fit: 'REGULAR' }, {})
  assert.deepEqual(out[0].motius, ['target', 'construction', 'fit'])
})

test('eix NULL al ruleset = comodí (lenient), com a matchingRuleSets', () => {
  const rss = [RS(1, { construction_codi: null, fit_type_codi: null })]
  const out = classifyRuleSets(rss, { target: 'WOMAN', construction: 'KNIT', fit: 'REGULAR' }, {})
  assert.ok(out[0].compatible)
})

test('ordre estable dins de cada grup', () => {
  const rss = [RS(1, { targets_codis: ['MAN'] }), RS(2, { targets_codis: ['WOMAN'] }),
               RS(3, { targets_codis: ['MAN'] }), RS(4, { targets_codis: ['WOMAN'] })]
  const out = classifyRuleSets(rss, { target: 'WOMAN' }, {})
  assert.deepEqual(out.map(x => x.rs.id), [2, 4, 1, 3])
})
