// S42/C3 — la fila-títol de prenda al full de fitting.
//     cd frontend && node --test src/utils/grupsDelFull.test.js
//
// EL VERMELL D'AQUEST BANC és el 1379: 18 files de la talla base repartides 11 (mare) + 7
// (Short), que abans queien totes a una taula plana i sense rètol. El VERD que ha de seguir
// intacte és el model d'una sola prenda: cap fila-títol, la mateixa llista i el mateix ordre
// que abans del tram. Un rètol que no distingeix res és soroll.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { grupsDelFull } from './grupsDelFull.js'

const MARE = 'Base model'

// Les 18 files reals del `PieceFitting 40` (model 1379, talla base S), en l'ordre que les
// serveix el serializer: `BaseMeasurement.ordre`, que és global al model.
const FILES_1379 = [
  ...['B', 'BB', 'B1', 'BF', 'D', 'G1', 'FS', 'FS2', 'FS3', 'FS4', 'FS5']
    .map((codi, i) => ({ id: i + 1, codi, garment: '' })),
  ...['FR', 'FE', 'CT', 'M', 'M1', 'F1', 'FT']
    .map((codi, i) => ({ id: 100 + i, codi, garment: '02' })),
]

const PECES_1379 = [
  { id: null, codi: '', nom: 'RUFFLES', ordre: 0, es_mare: true },
  { id: 4, codi: '02', nom: 'Short', ordre: 1, es_mare: false },
]

// ── VERMELL amb el 1379 ──────────────────────────────────────────────────────

test('1379 · dos grups amb fila-títol: «Base model» amb 11 files i «Short» amb 7', () => {
  const grups = grupsDelFull(FILES_1379, PECES_1379, MARE)
  assert.equal(grups.length, 2)
  assert.deepEqual(grups.map(g => [g.garment, g.titol, g.files.length]),
    [['', 'Base model', 11], ['02', 'Short', 7]])
})

test('la mare NO es diu com el model: el nom de la prenda ja el diu la banda', () => {
  const [mare] = grupsDelFull(FILES_1379, PECES_1379, MARE)
  assert.equal(mare.titol, 'Base model')
  assert.notEqual(mare.titol, 'RUFFLES')
})

test('cap fila es perd ni es repeteix pel camí', () => {
  const grups = grupsDelFull(FILES_1379, PECES_1379, MARE)
  const codis = grups.flatMap(g => g.files.map(f => f.codi))
  assert.equal(codis.length, FILES_1379.length)
  assert.equal(new Set(codis).size, FILES_1379.length)
})

// ── L'ORDRE EL MANA EL CONTRACTE, NO LA PRIMERA FILA QUE ARRIBI ──────────────

test('la mare va primera encara que el payload comenci per una fila del Short', () => {
  const capgirat = [...FILES_1379].reverse()
  const grups = grupsDelFull(capgirat, PECES_1379, MARE)
  assert.deepEqual(grups.map(g => g.garment), ['', '02'])
})

test('🚨 amb les prendes INTERCALADES surt UN títol per prenda, no un per canvi de fila', () => {
  // El payload ordena per `BaseMeasurement.ordre`, que és global al model: res no impedeix
  // que una mesura de la mare caigui entre dues del Short. Qui emetés un títol cada cop que
  // el `garment` canvia respecte de l'anterior en trauria QUATRE.
  const intercalat = [
    { id: 1, codi: 'B', garment: '' },
    { id: 2, codi: 'FR', garment: '02' },
    { id: 3, codi: 'BB', garment: '' },
    { id: 4, codi: 'FE', garment: '02' },
  ]
  const grups = grupsDelFull(intercalat, PECES_1379, MARE)
  assert.equal(grups.length, 2)
  assert.deepEqual(grups.map(g => [g.titol, g.files.map(f => f.codi)]),
    [['Base model', ['B', 'BB']], ['Short', ['FR', 'FE']]])
})

// ── VERD que ha de quedar intacte: el model d'UNA sola prenda ────────────────

test('model sense 02 · CAP fila-títol i la llista sencera, com abans del tram', () => {
  const files = FILES_1379.filter(f => f.garment === '')
  const grups = grupsDelFull(files, [PECES_1379[0]], MARE)
  assert.equal(grups.length, 1)
  assert.equal(grups[0].titol, null)
  assert.deepEqual(grups[0].files, files)
})

test('files sense la clau `garment` (payload vell) · cap rètol, cap fila perduda', () => {
  const files = [{ id: 1, codi: 'B' }, { id: 2, codi: 'BB' }]
  const grups = grupsDelFull(files, [PECES_1379[0]], MARE)
  assert.deepEqual(grups, [{ garment: '', titol: null, files }])
})

// ── DEGRADACIÓ: sense el contracte de peces, la taula surt SENCERA i plana ───

test('🚨 si `/peces/` no contesta, cap rètol — però mai una taula buida', () => {
  for (const sensePeces of [null, undefined, []]) {
    const grups = grupsDelFull(FILES_1379, sensePeces, MARE)
    assert.equal(grups.length, 1)
    assert.equal(grups[0].titol, null)
    assert.equal(grups[0].files.length, 18)
  }
})

test('una prenda amb files que el contracte no coneix va al final, no desapareix', () => {
  const ambIntrusa = [...FILES_1379, { id: 900, codi: 'XX', garment: '99' }]
  const grups = grupsDelFull(ambIntrusa, PECES_1379, MARE)
  assert.deepEqual(grups.map(g => g.garment), ['', '02', '99'])
  assert.equal(grups.at(-1).files.length, 1)
})

test('sense files, cap grup', () => {
  assert.deepEqual(grupsDelFull([], PECES_1379, MARE), [])
})
