// Q8/B4 — les files de les tres taules de la fitxa.
//     cd frontend && node --test src/utils/taulesQ8.test.js
//
// EL VERMELL QUE AQUEST BANC GUARDA és el de sempre en aquest territori: una `PieceFittingLine`
// neix amb `valor_real = valor_teoric`, i qualsevol constructor que llegeixi el real a pèl omple
// la fitxa de preses que ningú no ha fet. Aquí es prova que `actual` és `null` mentre ningú no
// hagi tocat la línia, i que la Dif no s'inventa un 0 quan hi falta una banda.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { diferencia, filesFitting, filesGrading, filesNotes, filesSizeSet, filesSizeSetConsolidat, fraseBreakQ8 } from './taulesQ8.js'

const MODEL = { base_size_label: 'S', size_run_model: 'XS·S·M' }

// Una línia del `grid`, amb els tres eixos. Per defecte NEIX com neixen de debò: real = teòric,
// sense decisió i sense nota — o sigui, ningú no l'ha mesurada.
const linia = (pom, talla, extra = {}) => ({
  id: `${pom}-${talla}`, pom_id: pom, capa: '', instancia: '', garment: '',
  codi: `P${pom}`, nom_en: `POM ${pom}`, nom_local: `Mesura ${pom}`, nom_fitxa: null,
  size_label: talla, valor_teoric: 50, valor_real: 50, decisio: '', nota: '', ...extra,
})

const grid = (lines) => ({ model: MODEL, lines })

// ⚠️ AQUÍ HI HAVIA «EXISTIR NO ÉS HAVER MESURAT: sense gest, `actual` és null», i T1 (18/08) el
// deroga PER A AQUESTA TAULA. La llei no cau: segueix manant a `taulaPresaPerTalla`, que
// documenta una presa VIVA i té el seu propi banc. El que Q8a documenta és una sessió TANCADA, on
// una línia amb el real igual al teòric vol dir «va arribar clavada», no «ningú no l'ha mirada».
test('a la sessió TANCADA, una línia sense gest porta Actual i la Dif és zero', () => {
  const { base, files } = filesFitting(grid([linia(1, 'S')]))
  assert.equal(base, 'S')
  assert.equal(files[0].aprovada, 50)
  assert.equal(files[0].actual, 50)
  assert.equal(files[0].dif, 0)
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
  // T1 — totes dues porten Actual; el que les distingeix és que una s'aparta i l'altra no.
  assert.deepEqual(files.map(f => f.actual), [50, 49])
  assert.deepEqual(files.map(f => f.dif), [0, -1])
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

// ── F4-QUATER · LA FRASE DEL RELLEU A LA FITXA ───────────────────────────────────────────────
//
// Aquest test substitueix el de `resumBreakQ8` («1 break parla en DOCUMENT, els intervals en
// MOTOR»), i el canvi que fixa és PRECISAMENT el de l'sprint: **ja no hi ha dues gramàtiques.**
// El break llegat es llegeix com l'interval que el motor ja calcula i es diu en convenció de
// MOTOR, igual que els explícits. La volta ±1 ha mort d'aquesta superfície.
//
// 🚨 I FIXA LA TRADUCCIÓ DE NOMS DE CAMP, que és el mode de fallada silenciós d'aquesta peça:
// les files de `filesGrading` porten `regla`/`delta`/`delta_break`/`talla_break`, no els noms de
// la fila de regla. Si algú desfés el mapatge de `fraseBreakQ8`, la fitxa sortiria sense cap
// relleu i el build seguiria verd — aquestes asserts es posarien vermelles primer.
test('Q8b · la frase del relleu: llegat i intervals, TOTS en convenció de MOTOR', () => {
  const RUN = ['XS', 'S', 'M', 'L', 'XL']
  const cm = (v) => Number(v).toFixed(1)
  // El cas del banc 1383: ib=2 · brk=3 · break M desat. El motor gradua `M..XL` amb +3 i la
  // frase ho diu tal qual — abans aquí s'hi pintava `S` (l'última del tram petit).
  assert.equal(
    fraseBreakQ8({ regla: 'LINEAR', delta: 2, delta_break: 3, talla_break: 'M', breaks: [] }, RUN, cm),
    'M→XL +3.0')
  // El cas del 1384 (TRAM F): un interval explícit, igual de literal.
  assert.equal(
    fraseBreakQ8({ regla: 'LINEAR', delta: 2, breaks: [{ inici: 'S', final: 'L', delta: 3 }] }, RUN, cm),
    'S→L +3.0')
  // Amb les dues formes manen els intervals, com al motor.
  assert.equal(
    fraseBreakQ8({ regla: 'LINEAR', delta: 2, delta_break: 9, talla_break: 'M',
      breaks: [{ inici: 'S', final: 'L', delta: 3 }] }, RUN, cm),
    'S→L +3.0')
  // Tres trams: es lletreja el primer i es compten els altres (l'A4 no dona per a més).
  assert.equal(
    fraseBreakQ8({ regla: 'LINEAR', delta: 1, breaks: [
      { inici: 'XS', final: 'XS', delta: 2 },
      { inici: 'M', final: 'L', delta: 3 },
      { inici: 'XL', final: 'XL', delta: 4 },
    ] }, RUN, cm),
    'XS→XS +2.0 +2')
  // El Δ negatiu porta el menys TIPOGRÀFIC, com la resta de la fitxa.
  assert.equal(
    fraseBreakQ8({ regla: 'LINEAR', delta: 2, breaks: [{ inici: 'S', final: 'L', delta: -1.5 }] }, RUN, cm),
    'S→L −1.5')
})

test('Q8b · REGLA DEL SILENCI a la fitxa: el que no mana no s\'imprimeix', () => {
  const RUN = ['XS', 'S', 'M', 'L', 'XL']
  const cm = (v) => Number(v).toFixed(1)
  // Sense relleu, res.
  assert.equal(fraseBreakQ8({ regla: 'LINEAR', delta: 2, breaks: [] }, RUN, cm), '')
  // Un FIXED amb break residual (les VUIT files del banc 1383) no diu res: no gradua.
  assert.equal(
    fraseBreakQ8({ regla: 'FIXED', delta: 0, delta_break: 0, talla_break: 'M', breaks: [] }, RUN, cm),
    '')
  // Un llegat que repeteix el Δ general no és un trencament.
  assert.equal(
    fraseBreakQ8({ regla: 'LINEAR', delta: 2, delta_break: 2, talla_break: 'M', breaks: [] }, RUN, cm),
    '')
})

test('TRAM F: els INTERVALS surten crus i sempre com a llista (mai null)', () => {
  const breaks = [{ inici: 'S', final: 'L', delta: 3 }]
  const [amb] = filesGrading([filaTM({ breaks })], ['XS', 'S', 'M'], 'S')
  assert.deepEqual(amb.breaks, breaks, 'crus: la volta de convenció no és d\'aquest constructor')
  const [sense] = filesGrading([filaTM()], ['XS', 'S', 'M'], 'S')
  assert.deepEqual(sense.breaks, [], 'una fila sense intervals en porta una llista buida')
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

// ── T1 · l'Actual de TOTES les mesures d'una sessió tancada ──────────────────────────────────

test('T1 · una línia INTACTA d\'una sessió tancada SÍ que porta Actual: va arribar clavada', () => {
  const { files } = filesFitting(grid([linia(1, 'S')]))     // real == teòric, sense decisió ni nota
  assert.equal(files[0].actual, 50, 'la columna Actual no pot quedar mig buida al document')
  assert.equal(files[0].dif, 0, 'i la Dif és zero, que qui pinta deixarà en blanc')
})

test('T1 · la que s\'aparta segueix dient-ho, i la Dif porta el signe', () => {
  const { files } = filesFitting(grid([linia(1, 'S', { valor_real: 48.5 })]))
  assert.equal(files[0].actual, 48.5)
  assert.equal(files[0].dif, -1.5)
})

test('T1 · al SIZE SET, totes les talles porten Actual, no només les corregides', () => {
  const { files } = filesSizeSet(grid([
    linia(1, 'XS', { valor_teoric: 48, valor_real: 48 }),    // intacta: va arribar clavada
    linia(1, 'S', { valor_real: 51 }),                       // moguda
  ]))
  assert.equal(files[0].celles.XS.actual, 48, 'la intacta també va arribar i es diu')
  assert.equal(files[0].celles.XS.dif, 0)
  assert.equal(files[0].celles.S.actual, 51)
  assert.equal(files[0].celles.M.actual, null, 'la que no té línia segueix sent un forat')
})
