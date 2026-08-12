// El banc del detector de «brut» — SET-2/T7-B5c.
//
// La pregunta que aquest fitxer contesta: **edició → revert deixa l'estat NET?** Si no, el
// guarda de sortida salta sempre i la gent aprèn a ignorar-lo.
//
//     node --test frontend/src/utils/taulaBruta.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { CAMPS_DE_MESURA, esBruta, projeccioDesable } from './taulaBruta.js'

const fila = (extra = {}) => ({
  pom_id: 7, capa: 'exterior', instancia: '', base_value_cm: 50, notes: '', nom_fitxa: 'A', ...extra,
})

// ── LA PREGUNTA DE TANCAMENT ─────────────────────────────────────────────────────────────

test('EDITAR I TORNAR AL VALOR ORIGINAL deixa la taula NETA', () => {
  const desades = [fila()]
  const editada = [fila({ base_value_cm: 61 })]
  const revertida = [fila({ base_value_cm: 50 })]

  assert.equal(esBruta(desades, editada), true)      // mentre és diferent, brut
  assert.equal(esBruta(desades, revertida), false)   // ← el fals positiu que es tanca
})

test('el revert per TECLAT tampoc embruta: l\'input torna text, no números', () => {
  // Aquest és el cas de debò. Ningú «reverteix» amb un número: reescriu la mateixa xifra, i
  // llavors el 50 desat i el '50' teclejat són el mateix valor amb dos tipus.
  assert.equal(esBruta([fila({ base_value_cm: 50 })], [fila({ base_value_cm: '50' })]), false)
  assert.equal(esBruta([fila({ base_value_cm: 50 })], [fila({ base_value_cm: '50.0' })]), false)
  // I un canvi de debò escrit com a text SÍ que embruta.
  assert.equal(esBruta([fila({ base_value_cm: 50 })], [fila({ base_value_cm: '51' })]), true)
})

test('buidar un valor i tornar-lo a posar: `\'\'` i `null` són el mateix estat', () => {
  assert.equal(esBruta([fila({ base_value_cm: null })], [fila({ base_value_cm: '' })]), false)
  // Buidar de debò una fila que tenia valor SÍ que és un canvi.
  assert.equal(esBruta([fila({ base_value_cm: 50 })], [fila({ base_value_cm: '' })]), true)
})

// ── EL FALS POSITIU QUE NOMÉS ES VEU PROJECTANT EL PAYLOAD ───────────────────────────────

test('treure una fila SUGGERIDA i buida no és cap canvi: no entra al payload', () => {
  // Les files de `poms-suggerits` no tenen `pom_id` ni valor: no van ni a `measurements` ni a
  // `keep_*`. Comparant camps de fila, esborrar-ne una diria «brut» i el guarda saltaria per
  // no res. Comparant el que s'ENVIA, no.
  const suggerida = { pom_id: null, capa: 'exterior', instancia: '', base_value_cm: null }
  const desades = [fila(), suggerida]
  const senseSuggerida = [fila()]

  assert.equal(esBruta(desades, senseSuggerida), false)
})

test('treure una fila DESADA sí que és un canvi', () => {
  assert.equal(esBruta([fila(), fila({ pom_id: 9 })], [fila()]), true)
})

// ── EL QUE HA D'EMBRUTAR ─────────────────────────────────────────────────────────────────

test('reordenar embruta: `keep_pom_ids` és una llista i l\'ordre hi compta', () => {
  const a = [fila(), fila({ pom_id: 9 })]
  const b = [fila({ pom_id: 9 }), fila()]

  assert.equal(esBruta(a, b), true)
})

test('els eixos de la fila són identitat: moure de capa embruta', () => {
  assert.equal(esBruta([fila()], [fila({ capa: 'folre' })]), true)
  assert.equal(esBruta([fila()], [fila({ instancia: 'relaxed' })]), true)
})

test('la nomenclatura i la nota també es desen, o sigui que també embruten', () => {
  assert.equal(esBruta([fila()], [fila({ nom_fitxa: 'A1' })]), true)
  assert.equal(esBruta([fila()], [fila({ notes: 'revisar' })]), true)
})

test('afegir una fila amb valor embruta', () => {
  assert.equal(esBruta([fila()], [fila(), fila({ pom_id: 9, base_value_cm: 12 })]), true)
})

// ── EL PIN DE L'ACOBLAMENT ───────────────────────────────────────────────────────────────

test('PIN · els camps que es desen són SIS, i si en creix un aquí ha de petar', () => {
  // Aquest mòdul reprodueix `EditableTable.buildPayload`. Si el payload guanya un camp i aquí
  // no, el detector dirà «net» amb canvis pendents — el fals NEGATIU, que perd feina en
  // silenci. Aquest test és el que fa sorollós aquell oblit.
  assert.deepEqual(CAMPS_DE_MESURA,
    ['pom_id', 'capa', 'instancia', 'base_value_cm', 'notes', 'nom_fitxa'])
  const p = projeccioDesable([fila()])
  assert.deepEqual(Object.keys(p.mesures[0]).sort(), [...CAMPS_DE_MESURA].sort())
})

test('sense files, res a desar', () => {
  assert.equal(esBruta([], []), false)
  assert.equal(esBruta(null, undefined), false)
})
