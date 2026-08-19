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
  GARMENT_MARE, agrupaPerGarment, calArbrePerGarment, garmentComu, garmentDeFila, garmentIdDe,
  partirTaules,
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

// ── Partir una taula en diverses: la llei dels dos eixos ─────────────────────
//
// El criteri de secció és el de la casa (`seccionsDeFiles` a TechSheetEditor): les seccions
// no buides, en ordre d'aparició. Aquí se'n passa una còpia perquè la llei no depengui de
// l'editor.
const seccionsDe = (files) => {
  const vistes = []
  for (const f of files) {
    const s = (f?.seccio || '').trim()
    if (s && !vistes.includes(s)) vistes.push(s)
  }
  return vistes
}
const FILES = [
  { id: 1, garment: '', seccio: '01.- DRESS' },
  { id: 2, garment: '', seccio: '01.- DRESS' },
  { id: 3, garment: '', seccio: '' },
]

test('CONTROL — un model d\'una sola peça i sense partició: UNA taula amb totes les files', () => {
  const grups = partirTaules(FILES, { seccionsDe })
  assert.equal(grups.length, 1)
  assert.deepEqual(grups[0], { garment: GARMENT_MARE, seccio: null, files: FILES })
})

test('CONTROL — demanar la partició per peça a un model d\'una peça NO parteix res', () => {
  // El guard no ha de tallar de més: la casella ni tan sols es pinta en aquest cas, però si
  // hi arribés marcada el resultat ha de seguir sent una taula i prou.
  const grups = partirTaules(FILES, { perPeca: true, seccionsDe })
  assert.equal(grups.length, 1)
  assert.deepEqual(grups[0].files, FILES)
})

test('la partició per SECCIÓ segueix funcionant igual que abans (dues seccions)', () => {
  const files = [...FILES, { id: 4, garment: '', seccio: '02.- KNICKERS' }]
  const grups = partirTaules(files, { perSeccio: true, seccionsDe })
  assert.deepEqual(grups.map(g => g.seccio), ['01.- DRESS', '02.- KNICKERS'])
  assert.deepEqual(grups.map(g => g.garment), ['', ''])
  // La fila sense secció (id 3) no entra enlloc: és el comportament que ja hi havia.
  assert.deepEqual(grups.map(g => g.files.map(f => f.id)), [[1, 2], [4]])
})

test('amb dues peces, la PRENDA parteix i la secció queda a dins', () => {
  const files = [
    { id: 1, garment: '', seccio: 'cos' },
    { id: 2, garment: '', seccio: 'caputxa' },
    { id: 3, garment: '02', seccio: 'cos' },
  ]
  const nomesPeca = partirTaules(files, { perPeca: true, seccionsDe })
  assert.deepEqual(nomesPeca.map(g => [g.garment, g.seccio, g.files.length]),
    [['', null, 2], ['02', null, 1]])

  // Els dos eixos alhora: prenda a fora, secció a dins. La 02 té una sola secció → no es
  // parteix (el criteri de secció exigeix més d'una, i s'aplica DINS de cada prenda).
  const tots = partirTaules(files, { perPeca: true, perSeccio: true, seccionsDe })
  assert.deepEqual(tots.map(g => [g.garment, g.seccio]),
    [['', 'cos'], ['', 'caputxa'], ['02', null]])
})

test('una taula NO partida que abraça dues prendes s\'ancora a la mare, mai a una de sola', () => {
  // La 02 va PRIMERA a propòsit: amb la mare al davant, «ancora-la a la primera peça» i «a
  // la mare» donarien el mateix i el test no distingiria res.
  const files = [{ id: 1, garment: '02' }, { id: 2, garment: '' }]
  const grups = partirTaules(files, { seccionsDe })
  assert.equal(grups.length, 1)
  assert.equal(grups[0].garment, GARMENT_MARE)
  assert.equal(garmentComu(files), GARMENT_MARE)
  assert.equal(garmentComu([{ garment: '02' }, { garment: '02' }]), '02')
})

test('sense cap fila hi ha UN grup buit, no cap grup (el que feia el codi d\'abans)', () => {
  // Les portes de T1a/T1b ja tallen la llista buida abans d'arribar aquí; això pin·la que
  // partir no és filtrar: el nombre de taules no depèn de si hi ha files.
  assert.deepEqual(partirTaules([], { seccionsDe }),
    [{ garment: GARMENT_MARE, seccio: null, files: [] }])
  assert.deepEqual(partirTaules([], { perPeca: true, perSeccio: true, seccionsDe }),
    [{ garment: GARMENT_MARE, seccio: null, files: [] }])
})
