// Q8/B3 — el salt de pàgina de les taules de la fitxa.
//     cd frontend && node --test src/utils/repartimentTaules.test.js
//
// EL VERMELL QUE AQUEST BANC GUARDA és el que hi havia abans del tram: una taula llarga no es
// partia, s'ESCALAVA sencera per cabre a la pàgina, i el cos de lletra queia per sota del sòl de
// 8pt sense que res ho digués. Aquí la prova és que les files es reparteixen SENCERES i que cada
// tros torna a pagar títol + capçalera — que és el que fa que la capçalera es repeteixi.
//
// Números en mm, com la fitxa col·loca els objectes. A4 vertical: 297 d'alt, cos útil 14→283.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { paginesDelRepartiment, repartimentEnPagines } from './repartimentTaules.js'

const PAGINA = { yInici: 14, yFinal: 283, separacio: 6 }
// Geometria d'una taula Q8 típica: banda de títol 6, capçalera 8, fila 5.
const geo = (nFiles, extra = {}) => ({ hTitol: 6, hCapcalera: 8, hFila: 5, nFiles, ...extra })

test('una taula que hi cap surt d\'una peça, i no toca cap pàgina nova', () => {
  const r = repartimentEnPagines([geo(20)], PAGINA)
  assert.deepEqual(r, [{ taula: 0, ini: 0, fi: 20, pagina: 0, y: 14 }])
  assert.equal(paginesDelRepartiment(r), 1)
})

test('CAP FILA PARTIDA: la suma dels trossos torna les files exactes i sense forats', () => {
  // 200 files no caben de cap manera a una pàgina: (283−14−14)/5 = 51 files per pàgina.
  const r = repartimentEnPagines([geo(200)], PAGINA)
  assert.ok(r.length > 1, 'ha de partir')
  assert.equal(r[0].ini, 0)
  assert.equal(r[r.length - 1].fi, 200)
  // Contigus i sense solapament: el final d'un tros és el principi del següent.
  r.slice(1).forEach((t, i) => assert.equal(t.ini, r[i].fi))
  // I cap tros buit: un tros de 0 files seria una capçalera sola enmig del document.
  r.forEach(t => assert.ok(t.fi > t.ini))
})

test('CADA TROS PAGA TÍTOL I CAPÇALERA: és el que fa que es repeteixin', () => {
  const r = repartimentEnPagines([geo(200)], PAGINA)
  const capacitat = Math.floor((283 - 14 - 6 - 8) / 5)   // 51
  assert.equal(r[0].fi - r[0].ini, capacitat)
  // El segon tros arrenca al capdamunt d'una pàgina NOVA, no on s'ha quedat el primer.
  assert.equal(r[1].pagina, 1)
  assert.equal(r[1].y, 14)
})

test('DUES PECES APILADES a la mateixa pàgina: la segona cau sota la primera', () => {
  const r = repartimentEnPagines([geo(10), geo(8)], PAGINA)
  assert.equal(r.length, 2)
  assert.equal(r[0].pagina, 0)
  assert.equal(r[1].pagina, 0)
  // y de la segona = 14 + (6+8) + 10·5 + 6 de separació
  assert.equal(r[1].y, 14 + 14 + 50 + 6)
})

test('quan la segona peça ja no hi cap, salta de pàgina SENCERA si li toca', () => {
  const r = repartimentEnPagines([geo(48), geo(30)], PAGINA)
  assert.equal(r[0].pagina, 0)
  assert.equal(r[0].fi, 48)
  // Després de la primera: 14 + 14 + 240 + 6 = 274. Queden 9 mm i en calen 14 només de fixa.
  assert.equal(r[1].pagina, 1)
  assert.equal(r[1].y, 14)
  assert.equal(r[1].fi - r[1].ini, 30)
})

test('la peça que continua a la pàgina següent hi arrenca de dalt, no on s\'havia quedat', () => {
  const r = repartimentEnPagines([geo(60)], PAGINA)
  assert.equal(r.length, 2)
  assert.deepEqual(r.map(t => [t.pagina, t.y]), [[0, 14], [1, 14]])
})

test('BLOC MÍNIM D\'UNA FILA: una fila més alta que la pàgina no penja l\'editor', () => {
  // hFila 400 sobre un cos útil de 269: la capacitat calculada és negativa a totes les pàgines.
  const r = repartimentEnPagines([geo(3, { hFila: 400 })], PAGINA)
  assert.equal(r.length, 3)
  r.forEach(t => assert.equal(t.fi - t.ini, 1))
  assert.deepEqual(r.map(t => t.pagina), [0, 1, 2])
})

test('una taula SENSE files surt igualment: filtrar-la és decisió del domini, no d\'aquí', () => {
  const r = repartimentEnPagines([geo(0)], PAGINA)
  assert.deepEqual(r, [{ taula: 0, ini: 0, fi: 0, pagina: 0, y: 14 }])
})

test('sense taules no hi ha ni trossos ni pàgines', () => {
  assert.deepEqual(repartimentEnPagines([], PAGINA), [])
  assert.equal(paginesDelRepartiment([]), 0)
  assert.equal(paginesDelRepartiment(repartimentEnPagines(null, PAGINA)), 0)
})

test('sense banda de títol el repartiment és el mateix menys la seva alçada', () => {
  const r = repartimentEnPagines([geo(200, { hTitol: 0 })], PAGINA)
  assert.equal(r[0].fi, Math.floor((283 - 14 - 8) / 5))
})
