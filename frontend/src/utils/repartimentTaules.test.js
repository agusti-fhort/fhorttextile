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

import { ampladaPerTextos, paginesDelRepartiment, repartimentEnPagines } from './repartimentTaules.js'

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

// ── L'amplada que fa que el nom més llarg no es talli ───────────────────────────────────────

test('AMPLADA PER TEXTOS: el nom més llarg hi cap en dues línies, i el límit no es negocia', () => {
  // 40 caràcters a 2 línies = 20 per línia · 1.5 mm/caràcter = 30 mm, més 2 de padding.
  const w = ampladaPerTextos(['x'.repeat(40), 'curt'], { charMm: 1.5, padMm: 2 })
  assert.equal(w, 32)
})

test('el mínim mana quan els noms són curts (una columna raquítica no es llegeix)', () => {
  assert.equal(ampladaPerTextos(['AB'], { charMm: 1.5, minMm: 30 }), 30)
})

test('el màxim mana quan els noms són desmesurats: la pàgina no és negociable', () => {
  assert.equal(ampladaPerTextos(['x'.repeat(400)], { charMm: 1.5, maxMm: 60 }), 60)
})

test('sense textos, sense amplada de caràcter o amb la llista buida, cau al mínim', () => {
  assert.equal(ampladaPerTextos([], { charMm: 1.5, minMm: 44 }), 44)
  assert.equal(ampladaPerTextos(null, { charMm: 1.5, minMm: 44 }), 44)
  assert.equal(ampladaPerTextos(['Chest'], { charMm: 0, minMm: 44 }), 44)
})

test('a UNA línia demana el doble d\'amplada que a dues', () => {
  const opts = { charMm: 1, padMm: 0 }
  assert.equal(ampladaPerTextos(['x'.repeat(30)], { ...opts, linies: 1 }), 30)
  assert.equal(ampladaPerTextos(['x'.repeat(30)], { ...opts, linies: 2 }), 15)
})

// ── C2 · alçades reals per fila ──────────────────────────────────────────────────────────────

test('C2 · amb `hFiles` cada fila val el que val, i no totes el màxim', () => {
  // 10 files compactes (4) i una de doble (8): amb el màxim antic serien 11×8 = 88;
  // amb l'alçada real són 10×4 + 8 = 48, i el que hi cap a la pàgina canvia de debò.
  const hFiles = [...Array(10).fill(4), 8]
  const r = repartimentEnPagines([{ hTitol: 6, hCapcalera: 8, hFiles, nFiles: 11 }],
    { yInici: 14, yFinal: 14 + 14 + 48, separacio: 6 })
  assert.equal(r.length, 1, 'hi caben totes just')
  assert.equal(r[0].fi, 11)
})

test('C2 · el tall cau on la SUMA se surt, no on ho diria una alçada mitjana', () => {
  const hFiles = [10, 10, 10, 2, 2, 2]
  // Espai per a 30 de cos: les tres primeres hi caben i la quarta ja no… sí que hi cap (32>30 no).
  const r = repartimentEnPagines([{ hTitol: 0, hCapcalera: 0, hFiles, nFiles: 6 }],
    { yInici: 0, yFinal: 30, separacio: 0 })
  assert.equal(r[0].fi, 3, 'tres files de 10 omplen els 30 exactes')
  assert.equal(r[1].ini, 3)
  assert.equal(r[1].fi, 6, 'les tres petites caben totes a la següent')
})

test('C2 · `hFila` (número únic) segueix valent: les taules sense wrap no fan cap llista', () => {
  const ambLlista = repartimentEnPagines([{ hTitol: 6, hCapcalera: 8, hFiles: Array(20).fill(5), nFiles: 20 }], PAGINA)
  const ambNumero = repartimentEnPagines([{ hTitol: 6, hCapcalera: 8, hFila: 5, nFiles: 20 }], PAGINA)
  assert.deepEqual(ambNumero, ambLlista)
})

test('C2 · una fila més alta que la pàgina segueix sortint sola, sense penjar-se', () => {
  const r = repartimentEnPagines([{ hTitol: 0, hCapcalera: 0, hFiles: [500, 500], nFiles: 2 }],
    { yInici: 14, yFinal: 287, separacio: 6 })
  assert.equal(r.length, 2)
  r.forEach(t => assert.equal(t.fi - t.ini, 1))
})
