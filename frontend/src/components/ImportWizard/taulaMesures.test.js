// P1 · LA GRAELLA DE L'IMPORT PARLA PER FILA — el guard.
//
//     cd frontend && node --test src/components/ImportWizard/taulaMesures.test.js
//
// Dos blocs, i l'ordre importa:
//
//   1 · NO-REGRESSIÓ (el PRIMER guard, no l'últim). Un POM per fila —el 100% dels imports
//       d'avui— ha de produir EXACTAMENT el mateix payload que abans de la peça: mateix
//       `pom_master_id`, mateixa `talla_label` (la del DOCUMENT), mateix `valor` i les
//       mateixes cel·les omeses. L'`ordre` que la peça hi afegeix és ADDITIU: qui llegia
//       `pom_master_id` segueix veient-hi el mateix número.
//
//   2 · LA BRUMÀ (30 · 31 · 40). Tres files del MATEIX POM B en tres instàncies. Amb la clau
//       d'avui —`pom_master_id`— la graella les fon en una sola entrada i les tres cel·les
//       ensenyen i envien el mateix número: el dany silenciós que el backend ja no té
//       (Onada 3, `0804fa3e`) però que la pantalla encara fabrica. Aquests tests s'han vist
//       VERMELLS sobre la versió 1 del mòdul, que era la graella de producció literal.
//
// La clau de fila és l'`ordre`, i el motiu de triar-lo és el mateix que a
// `cataleg/TaulaPOMsCataleg.jsx:66`: la identitat d'una fila no és el seu POM. Aquí, a més,
// l'`ordre` ja el fixa el backend a l'extracció i sobreviu a tot el pipeline, o sigui que és
// ESTABLE entre renders — condició dura per fer-lo servir de `key` de React sense que els
// `<input>` es desmuntin i es mengin el que s'està teclejant.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  aplicaGrading, clauDeFila, columnesBuides, comptaValors, construeixBaseValues,
  construeixMesures, construeixTaula, teValorABase,
} from './taulaMesures.js'

const TALLES = ['S', 'M', 'L']

/** Una fila de `poms_extrets` com la deixa el pas 2. */
const fila = (ordre, pom_master_id, extra = {}) => ({
  ordre, pom_master_id, actiu: true, codi_fitxa: `F${ordre}`, values: {}, ...extra,
})

// ══════════════════ 1 · NO-REGRESSIÓ — un POM per fila, com el 100% d'avui ══════════════════

const CH = fila(0, 11, { values: { S: 98, M: 100, L: 102 } })
const WA = fila(1, 22, { values: { S: 78, M: 80, L: 82 } })

test('construeixTaula porta els valors del document a la graella', () => {
  const t = construeixTaula([CH, WA], TALLES)
  assert.deepEqual(t[clauDeFila(CH)], { S: '98', M: '100', L: '102' })
  assert.deepEqual(t[clauDeFila(WA)], { S: '78', M: '80', L: '82' })
})

test('les files INACTIVES no entren a la graella', () => {
  const t = construeixTaula([CH, { ...WA, actiu: false }], TALLES)
  assert.equal(Object.keys(t).length, 1)
})

test('una cel·la absent del document neix buida, mai `undefined`', () => {
  const t = construeixTaula([fila(0, 11, { values: { M: 100 } })], TALLES)
  assert.deepEqual(t[0], { S: '', M: '100', L: '' })
})

test('el payload d\'un-POM-per-fila és el d\'avui, amb l\'`ordre` afegit', () => {
  const poms = [CH, WA]
  const t = construeixTaula(poms, TALLES)
  const mesures = construeixMesures(poms, TALLES, t)

  assert.equal(mesures.length, 6)
  // Byte a byte el contracte d'avui: POM, etiqueta del DOCUMENT i valor numèric.
  assert.deepEqual(
    mesures.map(({ pom_master_id, talla_label, valor }) => ({ pom_master_id, talla_label, valor })),
    [
      { pom_master_id: 11, talla_label: 'S', valor: 98 },
      { pom_master_id: 11, talla_label: 'M', valor: 100 },
      { pom_master_id: 11, talla_label: 'L', valor: 102 },
      { pom_master_id: 22, talla_label: 'S', valor: 78 },
      { pom_master_id: 22, talla_label: 'M', valor: 80 },
      { pom_master_id: 22, talla_label: 'L', valor: 82 },
    ],
  )
  // …i l'única cosa nova és additiva.
  assert.deepEqual(mesures.map(m => m.ordre), [0, 0, 0, 1, 1, 1])
})

test('les cel·les buides NO viatgen (mai `null`)', () => {
  const poms = [CH]
  const t = { ...construeixTaula(poms, TALLES), 0: { S: '', M: '100', L: '   ' } }
  const mesures = construeixMesures(poms, TALLES, t)
  assert.deepEqual(mesures.map(m => m.talla_label), ['M', 'L'])
  assert.equal(mesures.find(m => m.talla_label === 'S'), undefined)
})

test('columnesBuides · teValorABase · comptaValors llegeixen la mateixa graella', () => {
  const poms = [CH, WA]
  const t = construeixTaula(poms, TALLES)
  assert.deepEqual(columnesBuides(poms, TALLES, t), [])
  assert.equal(teValorABase(poms, t, 'M'), true)
  assert.equal(comptaValors(poms, TALLES, t), 6)

  const buida = construeixTaula([fila(0, 11), fila(1, 22)], TALLES)
  assert.deepEqual(columnesBuides([fila(0, 11), fila(1, 22)], TALLES, buida), TALLES)
  assert.equal(teValorABase([fila(0, 11)], buida, 'M'), false)
})

// ══════════════════ 2 · LA BRUMÀ — tres files, un POM, tres valors ══════════════════
//
// B «at the top» 30 · BB «at the bottom» 31 · B1 «stretched out» 40. El mateix POM B (id 7).

const BRUMA = [
  fila(0, 7, { codi_fitxa: 'B', instancia: '', values: { S: 28, M: 30, L: 32 } }),
  fila(1, 7, { codi_fitxa: 'BB', instancia: 'bottom', values: { S: 29, M: 31, L: 33 } }),
  fila(2, 7, { codi_fitxa: 'B1', instancia: 'extended', values: { S: 38, M: 40, L: 42 } }),
]

test('la graella té TRES entrades independents, no una', () => {
  const t = construeixTaula(BRUMA, TALLES)
  assert.equal(Object.keys(t).length, 3, 'tres files són tres entrades')
  assert.equal(t[0].M, '30')
  assert.equal(t[1].M, '31')
  assert.equal(t[2].M, '40')
})

test('les claus de fila són ÚNIQUES — és el `key` de React', () => {
  const claus = BRUMA.map(clauDeFila)
  assert.equal(new Set(claus).size, BRUMA.length,
    'dues files amb la mateixa clau desmunten i remunten els <input>')
})

test('teclejar a una germana no toca les altres dues', () => {
  const t = construeixTaula(BRUMA, TALLES)
  const seguent = { ...t, [clauDeFila(BRUMA[1])]: { ...t[clauDeFila(BRUMA[1])], M: '31.5' } }
  assert.equal(seguent[0].M, '30')
  assert.equal(seguent[1].M, '31.5')
  assert.equal(seguent[2].M, '40')
})

test('el payload porta els TRES valors, cadascun amb la seva fila', () => {
  const t = construeixTaula(BRUMA, TALLES)
  const base = construeixMesures(BRUMA, TALLES, t).filter(m => m.talla_label === 'M')
  assert.deepEqual(base.map(m => [m.ordre, m.pom_master_id, m.valor]),
                   [[0, 7, 30], [1, 7, 31], [2, 7, 40]])
})

test('el preview de graduació pregunta per FILA (llista), no per POM', () => {
  const t = construeixTaula(BRUMA, TALLES)
  assert.deepEqual(construeixBaseValues(BRUMA, t, 'M'),
                   [{ ordre: 0, valor: '30' }, { ordre: 1, valor: '31' }, { ordre: 2, valor: '40' }])
})

test('el grading tornat per fila omple només les cel·les buides de la SEVA fila', () => {
  const buides = BRUMA.map(p => ({ ...p, values: { M: p.values.M } }))
  const t = construeixTaula(buides, TALLES)
  const seguent = aplicaGrading(t, buides, TALLES, {
    0: { S: 28, L: 32 }, 1: { S: 29, L: 33 }, 2: { S: 38, L: 42 },
  })
  assert.deepEqual(seguent[0], { S: '28', M: '30', L: '32' })
  assert.deepEqual(seguent[1], { S: '29', M: '31', L: '33' })
  assert.deepEqual(seguent[2], { S: '38', M: '40', L: '42' })
})

test('el grading no trepitja mai un valor que ve del document', () => {
  const t = construeixTaula(BRUMA, TALLES)
  const seguent = aplicaGrading(t, BRUMA, TALLES, { 0: { M: 999 }, 1: { M: 999 }, 2: { M: 999 } })
  assert.deepEqual([seguent[0].M, seguent[1].M, seguent[2].M], ['30', '31', '40'])
})
