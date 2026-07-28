// Inserció de peça de patró: quines formes s'accepten i com es compten.
//     cd frontend && node --test src/utils/pecaInsercio.test.js
//
// LA REGRESSIÓ: `b4cb0b7` va fer que el conversor tornés un `group kind:'sketch'` quan el
// croquis té més d'un rol, però la inserció de peça només acceptava `path` i només comptava
// `path` per a la cascada. Resultat: la peça amb rols separats no s'inseria, i si s'hi
// hagués inserit, totes haurien caigut apilades a la mateixa cantonada.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { comptaPecesInserides, esGrupSketch, esPecaInserible } from './pecaInsercio.js'

const path = extra => ({ id: 'p', type: 'path', d: 'M0 0 L1 1', ...extra })
const grup = extra => ({ id: 'g', type: 'group', kind: 'sketch', children: [], ...extra })

test('un sol rol → path: s\'accepta, com abans de la regressió', () => {
  assert.equal(esPecaInserible(path()), true)
})

test('dos rols → grup sketch: s\'accepta', () => {
  assert.equal(esPecaInserible(grup()), true)
  assert.equal(esGrupSketch(grup()), true)
})

test('un grup que NO és sketch no és una peça', () => {
  // La condició és la del precedent: no n'hi ha prou amb ser un grup.
  assert.equal(esGrupSketch({ type: 'group' }), false)
  assert.equal(esPecaInserible({ type: 'group', kind: 'zona' }), false)
})

test('el que el conversor torna quan falla NO s\'accepta', () => {
  // `convertLegacySketchSvgObject` torna l'objecte d'entrada intacte si no sap convertir-lo:
  // aquest és el cas que ha de seguir ensenyant l'error d'inserció.
  assert.equal(esPecaInserible({ type: 'sketch_svg', svg: '<svg/>' }), false)
  assert.equal(esPecaInserible(null), false)
  assert.equal(esPecaInserible(undefined), false)
})

test('la cascada compta les DUES formes', () => {
  const pagina = [
    path({ piece_name: 'DAVANTER' }),
    grup({ piece_name: 'ESQUENA' }),
    grup({ piece_name: 'MÀNIGA' }),
  ]
  assert.equal(comptaPecesInserides(pagina), 3)
})

test('la cascada no compta el que no és una peça', () => {
  const pagina = [
    path({ piece_name: 'DAVANTER' }),   // peça
    path(),                             // vector dibuixat a mà: no és peça
    grup({ kind: 'zona', piece_name: 'X' }),  // grup d'una altra família
    { type: 'text', text: 'nota' },
    grup({ piece_name: 'ESQUENA' }),    // peça
  ]
  assert.equal(comptaPecesInserides(pagina), 2)
})

test('pàgina buida o sense objectes → 0, no una excepció', () => {
  assert.equal(comptaPecesInserides([]), 0)
  assert.equal(comptaPecesInserides(null), 0)
  assert.equal(comptaPecesInserides(undefined), 0)
})

test('escalonat: amb N peces la següent no cau on la primera', () => {
  // Mateixa aritmètica que el punt d'inserció (20 + (n % 5) * 10).
  const posicio = n => ({ x: 20 + (n % 5) * 10, y: 20 + (n % 5) * 10 })
  const pagina = [path({ piece_name: 'A' }), grup({ piece_name: 'B' })]
  const n = comptaPecesInserides(pagina)
  assert.equal(n, 2)
  assert.notDeepEqual(posicio(n), posicio(0))
  // Abans del fix, el grup no comptava: n hauria estat 1 i la 3a peça hauria caigut
  // sobre la 2a. Amb les dues formes comptades, cada peça té el seu esglaó.
  assert.notDeepEqual(posicio(n), posicio(1))
})
