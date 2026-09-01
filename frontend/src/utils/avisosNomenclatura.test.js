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
import { avisDeLaFila, germanaDeLaFila, nomsAmbAvis } from './avisosNomenclatura.js'

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

// ─── LA SEGONA FAMÍLIA · GERMANES HOMÒNIMES ──────────────────────────────────────────────
// El que aquest bloc protegeix: que la funció de germanes **no miri el POM**. Al backend és
// indiferent, i mirar-lo aquí deixaria sense marca el cas CENTRAL (dues instàncies del mateix
// POM) — l'avís existiria a la resposta i cap fila s'encendria.
const GERM = { garment: '', capa: 'exterior', nom_fitxa: 'AH',
               instancies: ['left', 'right'], files: [10, 11] }
const g = (o) => ({ pom_id: 904, capa: 'exterior', instancia: 'left', garment: '',
                    nom_fitxa: 'AH', ...o })

test('les dues germanes que el grup enumera el troben', () => {
  assert.equal(germanaDeLaFila([GERM], g()), GERM)
  assert.equal(germanaDeLaFila([GERM], g({ instancia: 'right' })), GERM)
})

test('🚨 el POM NO hi entra: el cas central és el MATEIX POM a les dues germanes', () => {
  assert.equal(germanaDeLaFila([GERM], g({ pom_id: 907 })), GERM)
  assert.equal(germanaDeLaFila([GERM], g({ pom_id: undefined })), GERM)
})

test('una instància que el grup no enumera no el troba', () => {
  assert.equal(germanaDeLaFila([GERM], g({ instancia: 'top' })), null)
  assert.equal(germanaDeLaFila([GERM], g({ instancia: '' })), null)
})

test('la instància BUIDA hi compta quan el grup la porta', () => {
  const amb = { ...GERM, instancies: ['', 'left'] }
  assert.equal(germanaDeLaFila([amb], g({ instancia: '' })), amb)
  assert.equal(germanaDeLaFila([amb], g({ instancia: undefined })), amb)
})

test('peça i capa separen; la caixa del nom no', () => {
  assert.equal(germanaDeLaFila([GERM], g({ garment: '02' })), null)
  assert.equal(germanaDeLaFila([GERM], g({ capa: 'folre' })), null)
  assert.equal(germanaDeLaFila([GERM], g({ nom_fitxa: 'ah' })), GERM)
})

test('la capa buida de la fila és la «exterior» del grup, com a l\'altra família', () => {
  assert.equal(germanaDeLaFila([GERM], g({ capa: '' })), GERM)
})

test('sense grups, sense fila o amb brossa torna null', () => {
  assert.equal(germanaDeLaFila([], g()), null)
  assert.equal(germanaDeLaFila(null, g()), null)
  assert.equal(germanaDeLaFila([GERM], null), null)
  assert.equal(germanaDeLaFila([{ ...GERM, instancies: undefined }], g()), null)
})
