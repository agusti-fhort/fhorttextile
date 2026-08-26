// La política de números de la casa (26/08). `node --test src/utils/num.test.js`.
//
// Es prova amb el runner de Node i sense cap dependència a posta: `num.js` no importa res
// justament per poder-ho fer (v. la seva capçalera).
import test from 'node:test'
import assert from 'node:assert/strict'

import { esNumeroEnCurs, formatDeltaNum, formatNum, parseNum } from './num.js'

// ── R1 · ENTRADA TOLERANT ────────────────────────────────────────────────────────────────

test('parseNum · el punt i la coma diuen el MATEIX número', () => {
  assert.equal(parseNum('0.75'), 0.75)
  assert.equal(parseNum('0,75'), 0.75)
  assert.equal(parseNum('-1.5'), -1.5)
  assert.equal(parseNum('-1,5'), -1.5)
})

test('parseNum · els estats d\'edició vàlids no peten i no inventen decimals', () => {
  // 🚨 EL CAS DEL DEFECTE: «1.» ha de poder EXISTIR mentre s'escriu. Que `parseNum` en tregui
  // 1 és correcte —al blur, un «1.» és un 1—; el que era el bug és aplicar-ho a cada tecla.
  assert.equal(parseNum('1.'), 1)
  assert.equal(parseNum('1,'), 1)
})

test('parseNum · buit és NULL i no zero (una cel·la sense mesura no és una mesura de 0)', () => {
  assert.equal(parseNum(''), null)
  assert.equal(parseNum('   '), null)
  assert.equal(parseNum(null), null)
  assert.equal(parseNum(undefined), null)
  assert.equal(parseNum('-'), null)      // el guionet sol encara no és cap número
})

test('parseNum · la brossa torna null i no llança MAI', () => {
  assert.equal(parseNum('abc'), null)
  assert.equal(parseNum('1.2.3'), null)
  assert.equal(parseNum('12px'), null)
  assert.equal(parseNum({}), null)
  assert.equal(parseNum(NaN), null)
  assert.equal(parseNum(Infinity), null)
})

test('parseNum · amb DOS separadors, l\'últim és el decimal i l\'altre és de miler', () => {
  assert.equal(parseNum('1.234,5'), 1234.5)
  assert.equal(parseNum('1,234.5'), 1234.5)
  // …però amb UN de sol sempre és decimal: aquí els números són mesures, no imports.
  assert.equal(parseNum('1.5'), 1.5)
  assert.equal(parseNum('1,5'), 1.5)
})

test('parseNum · un número ja numèric passa tal qual (els payloads no sempre porten text)', () => {
  assert.equal(parseNum(3.5), 3.5)
  assert.equal(parseNum(0), 0)
})

test('esNumeroEnCurs · el que s\'està teclejant no es pinta de vermell', () => {
  for (const bo of ['', '-', '1.', '1,', '-0,', '1.5', '0', '+2,']) {
    assert.equal(esNumeroEnCurs(bo), true, `«${bo}» hauria de ser vàlid en curs`)
  }
  for (const mal of ['abc', '1.2.3', '1,2,3', '12px']) {
    assert.equal(esNumeroEnCurs(mal), false, `«${mal}» NO hauria de ser vàlid`)
  }
})

// ── R2 · PRESENTACIÓ PER IDIOMA ──────────────────────────────────────────────────────────

test('formatNum · ca i es escriuen COMA; en escriu PUNT', () => {
  assert.equal(formatNum(0.75, { lang: 'ca' }), '0,75')
  assert.equal(formatNum(0.75, { lang: 'es' }), '0,75')
  assert.equal(formatNum(0.75, { lang: 'en' }), '0.75')
})

test('formatNum · l\'idioma pot venir amb regió («ca-ES»): la política és de LLENGUA', () => {
  assert.equal(formatNum(1.5, { lang: 'ca-ES' }), '1,5')
  assert.equal(formatNum(1.5, { lang: 'en-GB' }), '1.5')
})

test('formatNum · sense `dec` no s\'inventen decimals; amb `dec` es fixen', () => {
  assert.equal(formatNum(0.5, { lang: 'ca' }), '0,5')          // mai «0,50»
  assert.equal(formatNum(2, { lang: 'ca' }), '2')              // mai «2,0»
  assert.equal(formatNum(0.5, { lang: 'ca', dec: 2 }), '0,50')
})

test('formatNum · el buit es diu com el cridador vulgui, i per defecte calla', () => {
  assert.equal(formatNum('', { lang: 'ca' }), '')
  assert.equal(formatNum(null, { lang: 'ca', buit: '—' }), '—')
  assert.equal(formatNum('abc', { lang: 'ca', buit: '—' }), '—')
})

test('formatNum · SENSE separador de miler (un delta amb un punt enmig es rellegiria malament)', () => {
  assert.equal(formatNum(1234.5, { lang: 'ca' }), '1234,5')
  assert.equal(formatNum(1234.5, { lang: 'en' }), '1234.5')
})

test('parseNum(formatNum(x)) === x — l\'anada i tornada no perd res en cap idioma', () => {
  for (const lang of ['ca', 'es', 'en']) {
    for (const v of [0, 0.5, -1.5, 2, 1234.5, 0.75]) {
      assert.equal(parseNum(formatNum(v, { lang })), v, `${v} en ${lang}`)
    }
  }
})

// ── El delta, que és el que pinten els breaks ────────────────────────────────────────────

test('formatDeltaNum · el signe hi és sempre, menys al zero', () => {
  assert.equal(formatDeltaNum(3, { lang: 'ca' }), '+3')
  assert.equal(formatDeltaNum(-1.5, { lang: 'ca' }), '−1,5')   // menys TIPOGRÀFIC
  assert.equal(formatDeltaNum(0, { lang: 'ca' }), '0')
  assert.equal(formatDeltaNum(-1.5, { lang: 'en' }), '−1.5')
})
