// SET-2/T9 — l'eix de la peça a la fitxa: la mare per defecte, i l'arbre NOMÉS amb més d'una.
//     cd frontend && node --test src/utils/garmentFitxa.test.js
//
// EL QUE ES VIGILA AQUÍ és la DEGRADACIÓ, no la funcionalitat nova: mentre tot el corpus sigui
// d'una sola peça (avui, 2026-08-10: 13 comportes CHECK congelen `garment` a ''), aquestes
// funcions han de tornar exactament una branca i cap rètol. El cas de >1 peça hi és per provar
// que el cablatge existeix i que el guard NO TALLA DE MÉS quan algun dia arribi la 02.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  GARMENT_MARE, agrupaPerGarment, calArbrePerGarment, garmentDeFila, garmentIdDe,
} from './garmentFitxa.js'

// ── Lectura de l'eix: absent = la mare, mai undefined ────────────────────────

test('un objecte SENSE garmentId es llegeix com la mare (retrocompat de les fitxes vives)', () => {
  assert.equal(garmentIdDe({ id: 'o1', type: 'table' }), GARMENT_MARE)
  assert.equal(garmentIdDe(undefined), GARMENT_MARE)
  assert.equal(garmentIdDe(null), GARMENT_MARE)
})

test('un garmentId declarat es respecta, i un no-string cau a la mare', () => {
  assert.equal(garmentIdDe({ garmentId: '02' }), '02')
  assert.equal(garmentIdDe({ garmentId: '' }), GARMENT_MARE)
  // `null`/número no són l'eix: la convenció és string, i «no ho sé» aquí no existeix.
  assert.equal(garmentIdDe({ garmentId: null }), GARMENT_MARE)
  assert.equal(garmentIdDe({ garmentId: 2 }), GARMENT_MARE)
})

test('a les FILES de dades la clau es diu `garment`, com la columna', () => {
  assert.equal(garmentDeFila({ pom_id: 1, garment: '03' }), '03')
  assert.equal(garmentDeFila({ pom_id: 1 }), GARMENT_MARE)   // payload que encara no la serveix
})

// ── Agrupació: EL CAS DE CONTROL (avui) i el cas viu (algun dia) ─────────────

test("CONTROL — amb tot d'una sola peça hi ha UNA branca i l'arbre no surt", () => {
  const files = [{ id: 1, garment: '' }, { id: 2, garment: '' }, { id: 3 }]
  const grups = agrupaPerGarment(files)
  assert.equal(grups.length, 1)
  assert.equal(grups[0].garment, GARMENT_MARE)
  assert.deepEqual(grups[0].items, files)        // ni una fila es mou ni es perd
  assert.equal(calArbrePerGarment(grups), false) // ← cap rètol, cap clic de més
})

test('sense cap fila no hi ha ni grups ni arbre', () => {
  assert.deepEqual(agrupaPerGarment([]), [])
  assert.equal(calArbrePerGarment([]), false)
  assert.equal(calArbrePerGarment(agrupaPerGarment(undefined)), false)
})

test('amb dues peces surten dues branques i l\'arbre s\'encén', () => {
  const grups = agrupaPerGarment([
    { id: 1, garment: '' }, { id: 2, garment: '02' }, { id: 3, garment: '' },
  ])
  assert.deepEqual(grups.map(g => g.garment), ['', '02'])
  assert.deepEqual(grups.map(g => g.items.map(i => i.id)), [[1, 3], [2]])
  assert.equal(calArbrePerGarment(grups), true)
})

test("l'ordre és el D'APARICIÓ, mai alfabètic: agrupar no és reordenar", () => {
  // L'usuari ha ordenat les mesures amb el drag&drop del carril i `base_measurements_view`
  // les serveix per `ordre`. Un `sort()` aquí li desfaria la feina en silenci.
  const grups = agrupaPerGarment([{ garment: '03' }, { garment: '' }, { garment: '02' }])
  assert.deepEqual(grups.map(g => g.garment), ['03', '', '02'])
})

test('agrupa igual els OBJECTES del .ftt quan se li passa el lector d\'objecte', () => {
  const objs = [{ id: 'a', type: 'table' }, { id: 'b', type: 'table', garmentId: '02' }]
  const grups = agrupaPerGarment(objs, garmentIdDe)
  assert.deepEqual(grups.map(g => g.garment), ['', '02'])
})
