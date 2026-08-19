// P2-bis · LES PÍNDOLES EMETEN EL SLUG BO — el guard.
//
//     cd frontend && node --test src/components/instancia/instanciaTria.test.js
//
// El que defensa, i és tot el que la peça promet a la porta de sortida:
//
//   1 · **ELS EIXOS ES CREUEN.** Prémer «Bottom» i després «Extended» ha de donar
//       `bottom-extended`, no substituir l'un per l'altre. Amb el `<select>` pla de P2 això era
//       impossible —una instància composta no es podia demanar— i és la vora que hi vam censar.
//   2 · **L'ORDRE EL MANA EL DICCIONARI, NO EL CLIC.** `extended` primer i `left` després dona
//       igualment `left-extended`: si no, la mateixa germana tindria dues claus i la clau única
//       de la BD és `(model, pom, capa, instancia)`.
//   3 · **UNA PÍNDOLA ENCESA S'APAGA** (tornar a la instància única és un gest, no una recàrrega).
//   4 · **CAP TRIA = INSTÀNCIA ÚNICA** (`''`), que és el 100% del comportament d'avui.
//
// El diccionari d'aquí sota és la forma REAL de `GET /api/v1/mesures/diccionari/` (dos eixos,
// `instancia_separador: '-'`), retallat a les files que fan falta.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { aplicaCombinacio, tramsPerEix, triaTram } from './instanciaTria.js'

const DICC = {
  eixos: [{ clau: 'POSICIO', nom_ca: 'Posició' }, { clau: 'ESTAT', nom_ca: 'Estat' }],
  instancies: {
    POSICIO: [{ slug: 'left', display_order: 1 }, { slug: 'right', display_order: 2 },
              { slug: 'top', display_order: 3 }, { slug: 'bottom', display_order: 4 }],
    ESTAT: [{ slug: 'relaxed', display_order: 1 }, { slug: 'extended', display_order: 2 }],
  },
  regles: { instancia_separador: '-' },
}

// ── 1 · ELS EIXOS ES CREUEN ───────────────────────────────────────────────────
test('una sola píndola dona el seu slug', () => {
  assert.equal(triaTram(DICC, '', 'bottom'), 'bottom')
})

test('una píndola d\'un ALTRE eix se suma, no substitueix', () => {
  assert.equal(triaTram(DICC, 'bottom', 'extended'), 'bottom-extended')
})

test('la vora censada a P2 es tanca: left-relaxed es pot demanar', () => {
  assert.equal(triaTram(DICC, 'left', 'relaxed'), 'left-relaxed')
})

test('una píndola del MATEIX eix rellevà la seva, i deixa l\'altre eix intacte', () => {
  assert.equal(triaTram(DICC, 'bottom-extended', 'top'), 'top-extended')
  assert.equal(triaTram(DICC, 'bottom-extended', 'relaxed'), 'bottom-relaxed')
})

// ── 2 · L'ORDRE EL MANA EL DICCIONARI ─────────────────────────────────────────
test('l\'ordre dels trams és el dels EIXOS, no el dels clics', () => {
  // Primer l'estat i després la posició: el slug ha de sortir igual que a l'inrevés.
  assert.equal(triaTram(DICC, 'extended', 'left'), 'left-extended')
  assert.equal(triaTram(DICC, 'left', 'extended'), 'left-extended')
})

// ── 3 · APAGAR ────────────────────────────────────────────────────────────────
test('prémer la píndola encesa l\'apaga', () => {
  assert.equal(triaTram(DICC, 'bottom', 'bottom'), '')
  assert.equal(triaTram(DICC, 'bottom-extended', 'extended'), 'bottom')
})

// ── 4 · EL CONTROL: cap tria = instància única ────────────────────────────────
test('un slug que el diccionari no coneix no toca res', () => {
  assert.equal(triaTram(DICC, 'bottom', 'zzz'), 'bottom')
})

test('el modal ＋ compon el que se li dona, per la mateixa porta', () => {
  assert.equal(aplicaCombinacio(DICC, { ESTAT: 'relaxed', POSICIO: 'left' }), 'left-relaxed')
  assert.equal(aplicaCombinacio(DICC, { POSICIO: 'left', ESTAT: '' }), 'left')
  assert.equal(aplicaCombinacio(DICC, {}), '', 'cap tria és la instància única')
})

test('tramsPerEix diu quina píndola va encesa a cada grup', () => {
  assert.deepEqual(tramsPerEix(DICC, 'left-relaxed'), { POSICIO: 'left', ESTAT: 'relaxed' })
  assert.deepEqual(tramsPerEix(DICC, 'bottom'), { POSICIO: 'bottom' })
  assert.deepEqual(tramsPerEix(DICC, ''), {})
})
