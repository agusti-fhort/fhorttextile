// L'edició en línia d'un àlies — el que s'envia i el que es diu quan peta.
//     cd frontend && node --test src/utils/edicioAlies.test.js

import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  CAMPS_EDITABLES, canvisDe, errorDeResposta, esborranyDe, hiHaCanvis, payloadDe,
} from './edicioAlies.js'

const alias = (extra) => ({
  id: 7, client_code: 'CH', description_en: 'Chest', description_local: 'Pit',
  language: 'ca', pom: 12, origen: 'IMPORT', ...extra,
})

test('🔒 el codi del client NO és editable: no és a la llista i no viatja mai', () => {
  assert.equal(CAMPS_EDITABLES.includes('client_code'), false)
  const p = payloadDe({ ...esborranyDe(alias()), client_code: 'ALTRE' }, alias())
  assert.equal('client_code' in p, false)
})

test("l'esborrany surt de la fila i només porta els quatre camps", () => {
  assert.deepEqual(esborranyDe(alias()), {
    description_en: 'Chest', description_local: 'Pit', language: 'ca', pom: 12,
  })
})

test('sense tocar res, no hi ha canvis ni payload', () => {
  const a = alias()
  assert.equal(hiHaCanvis(esborranyDe(a), a), false)
  assert.deepEqual(payloadDe(esborranyDe(a), a), {})
})

test('el PATCH és MÍNIM: només el camp tocat', () => {
  const a = alias()
  const e = { ...esborranyDe(a), description_local: 'Ample de pit' }
  assert.deepEqual(payloadDe(e, a), { description_local: 'Ample de pit' })
})

test('un àlies pendent de mapar té pom null, i triar-ne un és un canvi', () => {
  const a = alias({ pom: null })
  assert.equal(esborranyDe(a).pom, null)
  assert.deepEqual(payloadDe({ ...esborranyDe(a), pom: 33 }, a), { pom: 33 })
})

test('el pom arriba com a text del cercador i surt com a NÚMERO', () => {
  const a = alias({ pom: 12 })
  assert.deepEqual(payloadDe({ ...esborranyDe(a), pom: '33' }, a), { pom: 33 })
  assert.deepEqual(payloadDe({ ...esborranyDe(a), pom: '12' }, a), {})
})

test('buidar una descripció SÍ que és un canvi (no es confon amb «no tocat»)', () => {
  const a = alias()
  assert.deepEqual(canvisDe({ ...esborranyDe(a), description_en: '' }, a),
    { description_en: '' })
})

test("l'error de validació de DRF surt a la fila amb el seu missatge", () => {
  const err = { response: { data: { client_code: ['El codi del client és la identitat.'] } } }
  assert.equal(errorDeResposta(err, 'generic'), 'El codi del client és la identitat.')
})

test('el 403 de permisos també, i pel seu `detail`', () => {
  const err = { response: { data: { detail: 'No tens permís per configurar.' } } }
  assert.equal(errorDeResposta(err, 'generic'), 'No tens permís per configurar.')
})

test('una caiguda de xarxa sense cos cau al text genèric de la pantalla', () => {
  assert.equal(errorDeResposta(new Error('Network Error'), 'generic'), 'generic')
  assert.equal(errorDeResposta({ response: { data: {} } }, 'generic'), 'generic')
})
