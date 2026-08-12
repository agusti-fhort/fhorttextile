// El banc del payload de desar mesures — SET-2/T7-B6.
//
// La regla que aquí es guarda té dany mesurat: sense `garment` al payload, desar la taula de la
// MARE desactivava la fila de la peça 02 (provat contra el model 1320 el 12/08, amb rollback).
// El backend ja resol per una clau de quatre; el que faltava era que el client la digués.
//
//     node --test frontend/src/utils/payloadMesures.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { CAMPS_DE_MESURA, construeixPayload, garmentDeFila, payloadComparable } from './payloadMesures.js'

const fila = (extra = {}) => ({
  pom_id: 904, capa: 'exterior', instancia: '', base_value_cm: 50, notes: '', nom_fitxa: 'A', ...extra,
})

// ── L'EIX HI ÉS, A LES DUES BANDES DEL PAYLOAD ───────────────────────────────────────────

test('la mesura porta l\'eix de la prenda', () => {
  const p = construeixPayload([fila()], '02')

  assert.equal(p.measurements[0].garment, '02')
})

test('🛑 `keep_mesures` TAMBÉ el porta: és el que evita l\'esborrat silenciós', () => {
  // `_poda_mesures` conserva per `(pom_id, capa, instancia, garment)` i, quan el client no diu
  // l'eix, `_identitat_de_mesura` hi posa `''`. Sense aquest camp, desar la taula de la mare
  // deixava la fila de la 02 FORA del conjunt a conservar i la donava de baixa.
  const p = construeixPayload([fila()], '02')

  assert.deepEqual(p.keep_mesures, [{ pom_id: 904, capa: 'exterior', instancia: '', garment: '02' }])
})

test('la MARE envia l\'eix BUIT, i buit és un valor: mai absent', () => {
  // Una clau absent obliga el servidor a assumir-ne una, i assumir és el que fabrica la
  // col·lisió. `''` diu «la mare» de manera afirmativa.
  const p = construeixPayload([fila()], '')

  assert.equal(p.measurements[0].garment, '')
  assert.equal(p.keep_mesures[0].garment, '')
  assert.ok('garment' in p.measurements[0])
  assert.ok('garment' in p.keep_mesures[0])
})

test('mana l\'eix DE LA FILA quan el porta; el del contenidor és el pla B', () => {
  // La fila sap de qui és (dada factual). El contenidor només respon mentre els adaptadors de
  // lectura no propaguin l'eix.
  assert.equal(garmentDeFila({ garment: '03' }, '02'), '03')
  assert.equal(garmentDeFila({}, '02'), '02')
  assert.equal(garmentDeFila({ garment: '' }, '02'), '')   // '' de la fila NO cau al contenidor
  assert.equal(garmentDeFila(null), '')
})

test('dues germanes que només es distingeixen per la PRENDA no es col·lapsen', () => {
  // El cas real del 1320: pom 904, capa exterior, instància buida, a la mare i a la 02. Amb la
  // clau de tres eren la mateixa fila; amb la de quatre, no.
  const p = construeixPayload([fila({ garment: '' }), fila({ garment: '02', base_value_cm: 42.5 })])
  const claus = p.keep_mesures.map(k => `${k.pom_id}|${k.capa}|${k.instancia}|${k.garment}`)

  assert.equal(new Set(claus).size, 2)
})

// ── EL QUE JA REGIA I NO POT CAURE ───────────────────────────────────────────────────────

test('`keep_*` es fa sobre TOTES les files amb pom, no només les que tenen valor', () => {
  // Una fila buida que en quedés fora deixaria de ser «conservada» i el backend l'esborraria.
  const p = construeixPayload([fila(), fila({ pom_id: 7, base_value_cm: null })])

  assert.equal(p.measurements.length, 1)      // només la que té valor s'envia com a mesura
  assert.deepEqual(p.keep_pom_ids, [904, 7])  // però totes dues es conserven
  assert.equal(p.keep_mesures.length, 2)
})

test('les files sense pom no entren a `keep_*`', () => {
  const p = construeixPayload([fila(), { pom_id: null, capa: 'exterior', base_value_cm: null }])

  assert.deepEqual(p.keep_pom_ids, [904])
})

test('PIN · els camps que s\'envien són SET, amb l\'eix inclòs', () => {
  assert.deepEqual([...CAMPS_DE_MESURA].sort(),
    ['base_value_cm', 'capa', 'garment', 'instancia', 'nom_fitxa', 'notes', 'pom_id'].sort())
  assert.deepEqual(Object.keys(construeixPayload([fila()])[ 'measurements' ][0]).sort(),
    [...CAMPS_DE_MESURA].sort())
})

// ── LA COMPARACIÓ (el detector de brut) SURT DEL MATEIX LLOC ─────────────────────────────

test('canviar només la PRENDA d\'una fila ja és un canvi per desar', () => {
  const a = payloadComparable([fila()], '')
  const b = payloadComparable([fila()], '02')

  assert.notDeepEqual(a, b)
})

test('el comparable segueix normalitzant text i buits', () => {
  assert.deepEqual(payloadComparable([fila({ base_value_cm: '50' })]),
    payloadComparable([fila({ base_value_cm: 50 })]))
  assert.deepEqual(payloadComparable([fila({ base_value_cm: '' })]),
    payloadComparable([fila({ base_value_cm: null })]))
})
