import test from 'node:test'
import assert from 'node:assert/strict'

import { durada, estatSessio, segonsDeSessio } from './sessioActiva.js'

const T0 = new Date('2026-08-05T10:00:00Z').getTime()
const tram = (extra = {}) => ({
  id: 5, inici: '2026-08-05T10:00:00Z', fi: null, origen: 'mesurat', ...extra,
})
const tasca = (extra = {}) => ({
  id: 42, status: 'InProgress', task_type_name: 'Definició POM', task_type_code: 'pom',
  model: 188, model_codi: 'BRW-SS27-0001', ...extra,
})

// ── El rellotge ──────────────────────────────────────────────────────────────
test('els segons es compten des de l\'inici del tram', () => {
  assert.equal(segonsDeSessio(tram(), T0 + 90_000), 90)
})

test('un tram sense inici val zero i no peta', () => {
  assert.equal(segonsDeSessio(null), 0)
  assert.equal(segonsDeSessio({}), 0)
})

test('mai negatiu encara que el rellotge del client vagi endarrerit', () => {
  assert.equal(segonsDeSessio(tram(), T0 - 60_000), 0)
})

test('la durada s\'expressa en minuts i hores, mai en segons', () => {
  assert.equal(durada(0), '0m')
  assert.equal(durada(59), '0m')
  assert.equal(durada(60), '1m')
  assert.equal(durada(725 * 60), '12h 05m')
  assert.equal(durada(3600), '1h 00m')
})

// ── Quan s'ensenya i quan NO ─────────────────────────────────────────────────
test('amb tram obert i tasca En curs, l\'indicador surt', () => {
  const e = estatSessio(tram(), tasca())
  assert.equal(e.taskId, 42)
  assert.equal(e.nom, 'Definició POM')
  assert.equal(e.model, 'BRW-SS27-0001')
  assert.equal(e.declarat, false)
})

test('sense tram no hi ha indicador', () => {
  assert.equal(estatSessio(null, tasca()), null)
})

test('un tram ja tancat no és una sessió', () => {
  assert.equal(estatSessio(tram({ fi: '2026-08-05T11:00:00Z' }), tasca()), null)
})

test('UN TRAM ZOMBI NO ENSENYA RES: mana l\'estat de la TASCA', () => {
  // La lliçó que GuardTascaOblidada va aprendre a base de 282 POSTs en minuts.
  assert.equal(estatSessio(tram(), tasca({ status: 'Paused' })), null)
  assert.equal(estatSessio(tram(), tasca({ status: 'Done' })), null)
  assert.equal(estatSessio(tram(), null), null)
})

test('un tram declarat es marca com a tal', () => {
  assert.equal(estatSessio(tram({ origen: 'declarat' }), tasca()).declarat, true)
})

test('sense nom de tipus cau al code, mai a undefined', () => {
  assert.equal(estatSessio(tram(), tasca({ task_type_name: null })).nom, 'pom')
})

// ── F2.4 · el salt entre superfícies ────────────────────────────────────────
import { CODE_PER_TAB, saltDeSuperficie } from './sessioActiva.js'

const viva = (extra = {}) => ({ id: 1, status: 'Paused', ...extra })

test('el mapa de pestanyes NO inclou la fitxa tècnica', () => {
  // Aquell tab és una llista; entrar-hi és navegar. La sessió de la fitxa l'obre «Modificar».
  assert.equal(CODE_PER_TAB['Fitxa tècnica'], undefined)
  assert.equal(CODE_PER_TAB.Mesures, 'pom')
  assert.equal(CODE_PER_TAB.Escalat, 'grading')
})

test('saltar a una superfície de treball amb la tasca lliure', () => {
  assert.deepEqual(saltDeSuperficie('Escalat', viva(), 7, 'cap'), { tab: 'Escalat', code: 'grading' })
})

test('un tab que no és superfície no fa saltar res', () => {
  assert.equal(saltDeSuperficie('Fitxers', viva(), 7, 'cap'), null)
  assert.equal(saltDeSuperficie('Fitxa tècnica', viva(), 7, 'cap'), null)
})

test('sense tasca no se n\'inventa cap: que la creï un gest explícit', () => {
  assert.equal(saltDeSuperficie('Mesures', null, 7, 'cap'), null)
})

test('SILENCI: si caldria preguntar, no se salta i no es pregunta', () => {
  assert.equal(saltDeSuperficie('Mesures', viva(), 7, 'conflicte'), null)
  assert.equal(saltDeSuperficie('Mesures', viva(), 7, 'albaranada'), null)
  assert.equal(saltDeSuperficie('Mesures', viva(), 7, 'lliurada'), null)
})

test('una tasca ja acabada no reobre sola en canviar de pestanya', () => {
  assert.equal(saltDeSuperficie('Mesures', viva({ status: 'Done' }), 7, 'cap'), null)
})
