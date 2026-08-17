// Q8/B4 — les files de les tres taules de la fitxa.
//     cd frontend && node --test src/utils/taulesQ8.test.js
//
// EL VERMELL QUE AQUEST BANC GUARDA és el de sempre en aquest territori: una `PieceFittingLine`
// neix amb `valor_real = valor_teoric`, i qualsevol constructor que llegeixi el real a pèl omple
// la fitxa de preses que ningú no ha fet. Aquí es prova que `actual` és `null` mentre ningú no
// hagi tocat la línia, i que la Dif no s'inventa un 0 quan hi falta una banda.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { diferencia, filesFitting, filesGrading, filesNotes, filesSizeSet, filesSizeSetConsolidat } from './taulesQ8.js'

const MODEL = { base_size_label: 'S', size_run_model: 'XS·S·M' }

// Una línia del `grid`, amb els tres eixos. Per defecte NEIX com neixen de debò: real = teòric,
// sense decisió i sense nota — o sigui, ningú no l'ha mesurada.
const linia = (pom, talla, extra = {}) => ({
  id: `${pom}-${talla}`, pom_id: pom, capa: '', instancia: '', garment: '',
  codi: `P${pom}`, nom_en: `POM ${pom}`, nom_local: `Mesura ${pom}`, nom_fitxa: null,
  size_label: talla, valor_teoric: 50, valor_real: 50, decisio: '', nota: '', ...extra,
})

const grid = (lines) => ({ model: MODEL, lines })

test('EXISTIR NO ÉS HAVER MESURAT: sense gest, `actual` és null i la Dif no s\'inventa un 0', () => {
  const { base, files } = filesFitting(grid([linia(1, 'S')]))
  assert.equal(base, 'S')
  assert.equal(files[0].aprovada, 50)
  assert.equal(files[0].actual, null)
  assert.equal(files[0].dif, null)
  assert.equal(files[0].veredicte, '')
})

test('amb presa i veredicte, la fila diu l\'aprovada, l\'actual i la desviació', () => {
  const { files } = filesFitting(grid([
    linia(1, 'S', { valor_real: 51.5, decisio: 'ADJUSTED', nota: 'obrir 1,5 al pit' }),
  ]))
  assert.equal(files[0].aprovada, 50)
  assert.equal(files[0].actual, 51.5)
  assert.equal(files[0].dif, 1.5)
  assert.equal(files[0].veredicte, 'ADJUSTED')
  assert.equal(files[0].nota, 'obrir 1,5 al pit')
})

test('la NOTA sola ja és contingut: la cel·la té actual encara que el número no s\'aparti', () => {
  const { files } = filesFitting(grid([linia(1, 'S', { nota: 'queda bé' })]))
  assert.equal(files[0].actual, 50)
  assert.equal(files[0].dif, 0)
})

test('només la TALLA BASE: les línies de les altres talles no fan fila a Q8a', () => {
  const { files } = filesFitting(grid([linia(1, 'XS'), linia(1, 'S'), linia(1, 'M')]))
  assert.equal(files.length, 1)
  assert.equal(files[0].aprovada, 50)
})

test('DUES GERMANES són DUES files, no una: la identitat porta els quatre eixos', () => {
  const { files } = filesFitting(grid([
    linia(1, 'S', { capa: 'exterior' }),
    linia(1, 'S', { capa: 'lining', valor_real: 49, decisio: 'ACCEPTED' }),
  ]))
  assert.equal(files.length, 2)
  assert.deepEqual(files.map(f => f.capa), ['exterior', 'lining'])
  assert.deepEqual(files.map(f => f.actual), [null, 49])
})

test('l\'eix de la PRENDA viatja amb la fila, que és el que la deixa repartir per peça', () => {
  const { files } = filesFitting(grid([linia(1, 'S'), linia(2, 'S', { garment: '02' })]))
  assert.deepEqual(files.map(f => f.garment), ['', '02'])
})

// ── Q8c · size set ──────────────────────────────────────────────────────────────────────────

test('SIZE SET: una cel·la per talla del run declarat, i el forat es veu', () => {
  const { talles, files } = filesSizeSet(grid([
    linia(1, 'XS', { valor_teoric: 48 }),
    linia(1, 'S', { valor_real: 51, decisio: 'ACCEPTED' }),
    // la M no té línia: la cel·la ha d'existir buida, no desaparèixer
  ]))
  assert.deepEqual(talles, ['XS', 'S', 'M'])
  assert.deepEqual(Object.keys(files[0].celles), ['XS', 'S', 'M'])
  assert.equal(files[0].celles.M.teorica, null)
  assert.equal(files[0].celles.XS.teorica, 48)
  assert.equal(files[0].celles.S.dif, 1)
})

test('R2 · EL VEREDICTE NOMÉS A LA BASE: una talla no-base no arriba mai a BaseMeasurement', () => {
  const { files } = filesSizeSet(grid([
    linia(1, 'XS', { decisio: 'REJECTED' }),
    linia(1, 'S', { decisio: 'ACCEPTED' }),
    linia(1, 'M', { decisio: 'ADJUSTED' }),
  ]))
  assert.equal(files[0].celles.S.veredicte, 'ACCEPTED')
  assert.equal(files[0].celles.XS.veredicte, '')
  assert.equal(files[0].celles.M.veredicte, '')
})

// ── Notes, en taula pròpia ──────────────────────────────────────────────────────────────────

test('LES NOTES VAN A PART i només hi entren les files que en tenen', () => {
  const { files } = filesNotes(grid([
    linia(1, 'S', { nota: '  massa ample  ' }),
    linia(2, 'S'),
    linia(3, 'S', { nota: 'puja el coll' }),
  ]))
  assert.deepEqual(files.map(f => f.pom_id), [1, 3])
  assert.equal(files[0].nota, 'massa ample')
})

// ── Q8b · grading ───────────────────────────────────────────────────────────────────────────

const filaTM = (extra = {}) => ({
  pom_id: 7, capa: '', instancia: '', garment: '', pom_code: 'CH', nom_en: 'Chest',
  nom_ca: 'Pit', base_value_cm: 50, graded: { XS: 48, M: 52 },
  logica: 'LINEAR', increment_base: 2, increment_break: null, talla_break_label: null, ...extra,
})

test('GRADING: la BASE surt de `base_value_cm` i la resta de `graded` (criteri de l\'Escalat)', () => {
  const [f] = filesGrading([filaTM()], ['XS', 'S', 'M'], 'S')
  assert.deepEqual(f.valors, { XS: 48, S: 50, M: 52 })
  assert.equal(f.regla, 'LINEAR')
  assert.equal(f.delta, 2)
})

test('una fila SENSE regla no s\'inventa règim: tot a null i la corba igualment', () => {
  const [f] = filesGrading([filaTM({ logica: null, increment_base: null })], ['XS', 'S', 'M'], 'S')
  assert.equal(f.regla, '')
  assert.equal(f.delta, null)
  assert.deepEqual(f.valors, { XS: 48, S: 50, M: 52 })
})

test('el BREAK surt CRU: desplaçar-lo a convenció de document és feina de qui pinta', () => {
  const [f] = filesGrading(
    [filaTM({ logica: 'STEP', increment_break: 3, talla_break_label: 'M' })], ['XS', 'S', 'M'], 'S')
  assert.equal(f.talla_break, 'M')       // el que hi ha a la BD, sense tocar
  assert.equal(f.delta_break, 3)
})

test('una talla sense valor graduat surt null, no 0: un 0 seria una mesura', () => {
  const [f] = filesGrading([filaTM({ graded: {} })], ['XS', 'S', 'M'], 'S')
  assert.deepEqual(f.valors, { XS: null, S: 50, M: null })
})

test('la prenda viatja també a la fila de grading', () => {
  const fs = filesGrading([filaTM(), filaTM({ garment: '02' })], ['S'], 'S')
  assert.deepEqual(fs.map(f => f.garment), ['', '02'])
})

// ── La resta ────────────────────────────────────────────────────────────────────────────────

test('diferencia: null quan falta una banda, i amb la precisió del domini', () => {
  assert.equal(diferencia(null, 50), null)
  assert.equal(diferencia(50, null), null)
  assert.equal(diferencia(50.1, 50), 0.1)      // i no 0.09999999999999432
  assert.equal(diferencia(49, 50), -1)
  assert.equal(diferencia(50, 50), 0)
})

test('un grid buit no peta ni inventa talles', () => {
  assert.deepEqual(filesFitting(null), { base: '', files: [] })
  assert.deepEqual(filesGrading(null, ['S'], 'S'), [])
  assert.deepEqual(filesNotes(grid([])).files, [])
})

// ── B0 · el size set sense cap presa: la corba del model ja és size set ──────────────────────

test('B0 · SIZE SET CONSOLIDAT: la corba hi és i les preses surten BUIDES, no absents', () => {
  const { base, talles, files } = filesSizeSetConsolidat([filaTM()], ['XS', 'S', 'M'], 'S')
  assert.equal(base, 'S')
  assert.deepEqual(talles, ['XS', 'S', 'M'])
  // Les tres cel·les existeixen: un forat s'ha de poder veure, i el que hi falta és la PRESA.
  assert.deepEqual(Object.keys(files[0].celles), ['XS', 'S', 'M'])
  assert.deepEqual(files[0].celles.S, { teorica: 50, actual: null, dif: null, veredicte: '' })
  assert.equal(files[0].celles.XS.teorica, 48, 'la corba surt de `graded`')
})

test('B0 · la forma de sortida és la MATEIXA que amb sessió: qui pinta no ha de saber d\'on ve', () => {
  const amb = filesSizeSet(grid([linia(1, 'S')]))
  const sense = filesSizeSetConsolidat([filaTM()], ['XS', 'S', 'M'], 'S')
  assert.deepEqual(Object.keys(amb).sort(), Object.keys(sense).sort())
  assert.deepEqual(Object.keys(amb.files[0].celles.S).sort(),
                   Object.keys(sense.files[0].celles.S).sort())
})

test('B0 · el consolidat també porta l\'eix de la prenda, o no es podria repartir', () => {
  const { files } = filesSizeSetConsolidat(
    [filaTM(), filaTM({ garment: '02' })], ['S'], 'S')
  assert.deepEqual(files.map(f => f.garment), ['', '02'])
})
