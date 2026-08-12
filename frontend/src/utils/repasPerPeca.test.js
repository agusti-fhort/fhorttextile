import test from 'node:test'
import assert from 'node:assert/strict'

import { columnesAmbContingut, recompteFittings, tallaDeLaCapcalera } from './repasPerPeca.js'

// BANC · el Repàs compta per prenda (SET-2/PRED-1).
//
// El contrapès que trenca la coincidència en aquest banc: la MARE i la 02 han de donar números
// DIFERENTS amb les MATEIXES sessions. Si el dia de demà algú torna a comptar sobre el model,
// aquests dos casos no poden passar tots dos.

const SESSIONS = [
  { id: 'entrada', origen: 'ENTRADA' },
  { id: 151, origen: 'SESSIO' },
  { id: 152, origen: 'SESSIO' },
  { id: 'etapa:manual@2026-08-12T10:00:00', origen: 'MANUAL' },
]

// La mare la toquen les tres columnes d'esdeveniment; la 02, només la 152.
const FILES_MARE = [
  { garment: '', valors: {
    entrada: { valor_real: 50 },
    151: { valor_real: 50.5 },
    152: { valor_real: 51 },
    'etapa:manual@2026-08-12T10:00:00': { valor_real: 51.5 },
  } },
]
const FILES_02 = [
  { garment: '02', valors: {
    entrada: { valor_real: 33 },
    152: { valor_real: 33.3 },
  } },
]

test('el recompte d una prenda són les columnes que TOQUEN les seves files', () => {
  assert.equal(recompteFittings(FILES_MARE, SESSIONS), 3)
  assert.equal(recompteFittings(FILES_02, SESSIONS), 1)
})

test('EL CONTRAPÈS · dues prendes amb les mateixes sessions donen números diferents', () => {
  // Aquesta és l'afirmació que un recompte fet sobre el MODEL no pot complir mai: allà les
  // dues dirien 3. Si algú torna a comptar `sessions.filter(...)`, aquest test cau.
  assert.notEqual(recompteFittings(FILES_MARE, SESSIONS),
                  recompteFittings(FILES_02, SESSIONS))
})

test('l ENTRADA DE POMs no és un fitting i no compta mai', () => {
  const nomesEntrada = [{ garment: '02', valors: { entrada: { valor_real: 33 } } }]
  assert.equal(recompteFittings(nomesEntrada, SESSIONS), 0)
  assert.ok(!columnesAmbContingut(FILES_MARE, SESSIONS).includes('entrada'))
})

test('una columna sense valor a AQUESTES files no compta', () => {
  // La columna 151 existeix i la 02 no hi té cel·la: per a aquesta prenda, aquell dia no va
  // passar res. Una cel·la amb `valor_real: null` és el mateix cas dit explícitament.
  const ambNul = [{ garment: '02', valors: { 151: { valor_real: null }, 152: { valor_real: 33.3 } } }]
  assert.deepEqual(columnesAmbContingut(ambNul, SESSIONS), ['152'])
})

test('una nota sense número NO és una presa', () => {
  // Comptar-la faria pujar el recompte d'una prenda que ningú ha mesurat: una columna que només
  // porta el motiu d'un gate parla de la sessió, no d'aquesta fila.
  const nomesNota = [{ garment: '02', valors: { 151: { valor_real: null, nota: 'la sisa balla' } } }]
  assert.equal(recompteFittings(nomesNota, SESSIONS), 0)
})

test('CONTROL D UNA PRENDA · el número és el de sempre', () => {
  // Un model d'una sola prenda ha de donar EXACTAMENT el que donava el recompte del model:
  // totes les columnes d'esdeveniment menys l'ENTRADA. És la contraprova que aquest canvi no
  // mou res al 100% del corpus d'avui.
  const sessionsModel = SESSIONS.filter(s => s.origen !== 'ENTRADA').length
  assert.equal(recompteFittings(FILES_MARE, SESSIONS), sessionsModel)
})

test('sense files ni sessions no peta i diu zero', () => {
  assert.equal(recompteFittings([], SESSIONS), 0)
  assert.equal(recompteFittings(FILES_MARE, []), 0)
  assert.equal(recompteFittings(undefined, undefined), 0)
})

// ── LA TALLA DE LA CAPÇALERA ────────────────────────────────────────────────────────────────

test('la talla no divergeix quan la prenda hereta la base del model', () => {
  const peca = { codi: '02', es_mare: false, base_size_label: { etiqueta: 'S', heretat: true } }
  assert.deepEqual(tallaDeLaCapcalera('S', peca), { talla: 'S', divergeix: false, propia: 'S' })
})

test('🚨 la talla DIVERGEIX quan la prenda declara la seva pròpia base', () => {
  // El cas que avui no és al corpus i que la pantalla ha de saber dir: la vista ensenya les
  // files de la talla del MODEL i el contenidor és d'una prenda que es mesura en una altra.
  const peca = { codi: '02', es_mare: false, base_size_label: { etiqueta: 'M', heretat: false } }
  assert.deepEqual(tallaDeLaCapcalera('S', peca), { talla: 'S', divergeix: true, propia: 'M' })
})

test('la MARE no divergeix mai: la talla de la vista és la seva', () => {
  const mare = { codi: '', es_mare: true, base_size_label: { etiqueta: 'S', heretat: false } }
  assert.equal(tallaDeLaCapcalera('S', mare).divergeix, false)
})

test('sense peça (o sense base resolta) no s acusa cap divergència', () => {
  assert.equal(tallaDeLaCapcalera('S', null).divergeix, false)
  assert.equal(tallaDeLaCapcalera('S', { codi: '02', es_mare: false }).divergeix, false)
  assert.equal(tallaDeLaCapcalera('', { codi: '02', es_mare: false,
                                        base_size_label: { etiqueta: 'M' } }).divergeix, false)
})
