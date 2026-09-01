// M1194 · L'AVÍS TROBA LA SEVA FILA — banc pur, sense React ni BD.
//
//     node --test frontend/src/utils/avisosNomenclatura.test.js
//
// El que aquest banc protegeix és **el retrobament**: el backend agrupa amb els eixos ja
// normalitzats i la pantalla té les files tal com les ha escrit el tècnic. Si les dues bandes
// no normalitzen igual, `avisDeLaFila` no troba res, la taula es desa amb l'ambigüitat i no la
// canta ningú — un avís mut és pitjor que cap avís, perquè fa creure que s'ha mirat.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { avisDeLaFila, nomsAmbAvis } from './avisosNomenclatura.js'

const AVIS = { garment: '', capa: 'exterior', instancia: '', nom_fitxa: 'B',
               poms: [904, 907], files: [0, 1] }
const fila = (o) => ({ pom_id: 904, capa: 'exterior', instancia: '', garment: '',
                       nom_fitxa: 'B', ...o })

test('la fila que l\'avís enumera el troba', () => {
  assert.equal(avisDeLaFila([AVIS], fila()), AVIS)
  assert.equal(avisDeLaFila([AVIS], fila({ pom_id: 907 })), AVIS)
})

test('un POM que l\'avís NO enumera no el troba', () => {
  // Tercera fila del mateix àmbit amb un nom diferent: no és ambigua amb ningú.
  assert.equal(avisDeLaFila([AVIS], fila({ pom_id: 1015 })), null)
})

test('🚨 LA CAPA BUIDA DE LA FILA ÉS LA «exterior» DE L\'AVÍS', () => {
  // El defecte que aquest mòdul existeix per matar: el backend normalitza i la pantalla no.
  assert.equal(avisDeLaFila([AVIS], fila({ capa: '' })), AVIS)
  assert.equal(avisDeLaFila([AVIS], fila({ capa: undefined })), AVIS)
  assert.equal(avisDeLaFila([AVIS], fila({ capa: null })), AVIS)
})

test('el nom es compara sense distingir caixa ni vora', () => {
  assert.equal(avisDeLaFila([AVIS], fila({ nom_fitxa: 'b' })), AVIS)
  assert.equal(avisDeLaFila([AVIS], fila({ nom_fitxa: ' B ' })), AVIS)
})

test('cada eix de l\'àmbit separa per separat', () => {
  for (const [eix, valor] of [['garment', '02'], ['instancia', 'left'], ['capa', 'folre']]) {
    assert.equal(avisDeLaFila([AVIS], fila({ [eix]: valor })), null, `l'eix «${eix}» no separa`)
  }
})

test('el pom_id es compara com a text: un id de JSON pot arribar en cadena', () => {
  assert.equal(avisDeLaFila([AVIS], fila({ pom_id: '904' })), AVIS)
})

test('sense avisos, sense fila o amb brossa no peta i torna null', () => {
  assert.equal(avisDeLaFila([], fila()), null)
  assert.equal(avisDeLaFila(null, fila()), null)
  assert.equal(avisDeLaFila(undefined, fila()), null)
  assert.equal(avisDeLaFila([AVIS], null), null)
  assert.equal(avisDeLaFila([AVIS], fila({ nom_fitxa: '' })), null)
})

test('els noms per a la capçalera van sense repetir i en ordre', () => {
  assert.deepEqual(nomsAmbAvis([AVIS, { ...AVIS, nom_fitxa: 'X1' }, { ...AVIS, nom_fitxa: 'B' }]),
                   ['B', 'X1'])
  assert.deepEqual(nomsAmbAvis([]), [])
  assert.deepEqual(nomsAmbAvis(null), [])
})
