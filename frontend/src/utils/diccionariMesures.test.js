// LA COMPOSICIÓ DEL CODI I DEL SLUG D'UNA GERMANA (D-31.26).
//     cd frontend && node --test src/utils/diccionariMesures.test.js
//
// LA PROMESA QUE FIXA: el codi proposat és `base + sufix` CONCATENAT, sense cap separador
// —estil Brownie natiu: `B`+`T` → `BT`, mai `B-T`—, i el slug d'instància es compon SEMPRE en
// l'ordre dels eixos (posició abans que estat). L'ordre importa perquè la clau única de la BD
// és `(model, pom, capa, instancia)`: si el slug depengués de l'ordre de clic, la mateixa
// germana tindria dues claus i les dues files conviurien sense que res petés.
//
// I la promesa INVERSA, que és la que evita inventar codis: els ESTATS no porten sufix i la
// CAPA no toca mai el codi. Quan no hi ha sufix, la proposta és el codi base tal qual.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  EIX_POSICIO, EIX_ESTAT, COMPLEMENTARIA,
  eixDe, filaInstancia, tramsInstancia, composaInstancia, codiProposat, codiBase,
} from './diccionariMesures.js'

// Diccionari amb la forma EXACTA que emet `GET /api/v1/mesures/diccionari/` (verificat contra
// el tenant `fhort` el 05/08). Retallat a les files que els casos toquen.
const D = {
  capes: [{ slug: 'exterior' }, { slug: 'folre' }],
  instancies: {
    [EIX_POSICIO]: [
      { slug: 'left', sufix: 'L' }, { slug: 'right', sufix: 'R' },
      { slug: 'top', sufix: 'T' }, { slug: 'bottom', sufix: 'B' },
      { slug: 'cf', sufix: 'CF' }, { slug: 'cb', sufix: 'CB' },
      { slug: 'side', sufix: 'S' }, { slug: 'waistband_seam', sufix: '' },
    ],
    [EIX_ESTAT]: [{ slug: 'relaxed', sufix: '' }, { slug: 'extended', sufix: '' }],
  },
  regles: { sufix_separador: '', instancia_separador: '-', capa_al_codi: false, instancia_unica: '' },
}

test('el sufix s\'enganxa SENSE separador (estil Brownie natiu)', () => {
  assert.equal(codiProposat(D, 'B', ['top']), 'BT')
  assert.equal(codiProposat(D, 'FS', ['cf']), 'FSCF')
  assert.equal(codiProposat(D, 'AH', ['left']), 'AHL')
  // I mai amb guió: és exactament el format que les dades velles porten malament.
  assert.notEqual(codiProposat(D, 'AH', ['left']), 'AH-L')
})

test('els ESTATS no componen sufix: la proposta és el codi base', () => {
  assert.equal(codiProposat(D, 'B', ['relaxed']), 'B')
  assert.equal(codiProposat(D, 'B', ['extended']), 'B')
  // `waistband_seam` és un DATUM i tampoc no en porta (es diu a la descripció).
  assert.equal(codiProposat(D, 'W', ['waistband_seam']), 'W')
})

test('creuar els dos eixos enganxa NOMÉS el sufix de la posició', () => {
  assert.equal(codiProposat(D, 'B', ['left', 'relaxed']), 'BL')
  assert.equal(codiProposat(D, 'B', ['relaxed', 'left']), 'BL')
})

test('el slug compost va SEMPRE en l\'ordre dels eixos, no en el del clic', () => {
  assert.equal(composaInstancia(D, ['left', 'relaxed']), 'left-relaxed')
  assert.equal(composaInstancia(D, ['relaxed', 'left']), 'left-relaxed')
  // Idempotent i sense duplicats: dos clics a la mateixa opció no fabriquen `left-left`.
  assert.equal(composaInstancia(D, ['left', 'left']), 'left')
  assert.equal(composaInstancia(D, []), '')
})

test('el slug compost es desmunta pel separador del diccionari', () => {
  assert.deepEqual(tramsInstancia(D, 'left-relaxed'), ['left', 'relaxed'])
  assert.deepEqual(tramsInstancia(D, 'left'), ['left'])
  assert.deepEqual(tramsInstancia(D, ''), [])
  assert.deepEqual(tramsInstancia(D, null), [])
})

test('cada slug sap de quin eix és, i un de desconegut no menteix', () => {
  assert.equal(eixDe(D, 'left'), EIX_POSICIO)
  assert.equal(eixDe(D, 'cb'), EIX_POSICIO)
  assert.equal(eixDe(D, 'extended'), EIX_ESTAT)
  assert.equal(eixDe(D, 'sleeve-2'), null)
  assert.equal(eixDe(null, 'left'), null)
})

test('la fila del diccionari porta el sufix real', () => {
  assert.equal(filaInstancia(D, 'cf').sufix, 'CF')
  assert.equal(filaInstancia(D, 'relaxed').sufix, '')
  assert.equal(filaInstancia(D, 'inexistent'), null)
})

test('les complementàries són recíproques, i no totes les posicions en tenen', () => {
  for (const [a, b] of Object.entries(COMPLEMENTARIA)) {
    assert.equal(COMPLEMENTARIA[b], a, `${a}↔${b} no és recíproca`)
  }
  // `side` i `waistband_seam` NO es parteixen: no tenen germana geomètrica.
  assert.equal(COMPLEMENTARIA.side, undefined)
  assert.equal(COMPLEMENTARIA.waistband_seam, undefined)
})

test('el codi base es recupera per RE-partir sense acumular sufixos', () => {
  assert.equal(codiBase(D, 'AHL', ['left']), 'AH')
  assert.equal(codiBase(D, 'BT', ['top']), 'B')
  assert.equal(codiBase(D, 'FSCF', ['cf']), 'FS')
  // Creuament dels dos eixos: només la posició havia posat sufix.
  assert.equal(codiBase(D, 'BL', ['left', 'relaxed']), 'B')
  // Sense instància no hi ha res a treure.
  assert.equal(codiBase(D, 'CH', []), 'CH')
})

test('el codi base no endevina: només treu el sufix que la fila DECLARA', () => {
  // «TOTAL» acaba en «L» però la fila no diu `left` → no se'n toca res.
  assert.equal(codiBase(D, 'TOTAL', []), 'TOTAL')
  // I si la fila diu `right`, tampoc: el sufix que busca és «R», i «TOTAL» no hi acaba.
  assert.equal(codiBase(D, 'TOTAL', ['right']), 'TOTAL')
  // Amb `left` sí que hi acaba, i és el que la fila declara: es treu.
  assert.equal(codiBase(D, 'TOTAL', ['left']), 'TOTA')
})

test('sense diccionari no s\'inventa res', () => {
  assert.equal(codiProposat(null, 'B', ['top']), 'B')
  assert.equal(composaInstancia(null, ['left']), 'left')
})
