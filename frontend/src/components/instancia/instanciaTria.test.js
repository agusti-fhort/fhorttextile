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

import { aplicaCombinacio, tramsPerEix, triaAlModal, triaTram } from './instanciaTria.js'

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

// ── 5 · ELS DOS EIXOS DE LA POSICIÓ (Agus, 22-23/08) ──────────────────────────
// CARA (front · back) i LATERAL (left · right): dins d'un, excloents; entre ells, combinables.
// El diccionari de dalt NO porta `subeix` a posta —és el que emet un backend anterior a aquest
// tram— i per això els nou tests de sobre segueixen valent: sense sub-eixos, tot es comporta
// com sempre. Aquest d'aquí sota és el diccionari d'ARA.
const DICC2 = {
  ...DICC,
  subeixos: ['CARA', 'LATERAL'],
  instancies: {
    POSICIO: [
      { slug: 'left', subeix: 'LATERAL', display_order: 1 },
      { slug: 'right', subeix: 'LATERAL', display_order: 2 },
      { slug: 'top', subeix: '', display_order: 3 },
      { slug: 'bottom', subeix: '', display_order: 4 },
      { slug: 'front', subeix: 'CARA', display_order: 9 },
      { slug: 'back', subeix: 'CARA', display_order: 10 },
    ],
    ESTAT: DICC.instancies.ESTAT,
  },
}

test('seleccionar Left desmarca Right, i Front desmarca Back', () => {
  assert.equal(triaTram(DICC2, 'left', 'right'), 'right')
  assert.equal(triaTram(DICC2, 'front', 'back'), 'back')
})

test('🚨 LES CREUADES CONVIUEN: Left + Back és una germana legítima', () => {
  assert.equal(triaTram(DICC2, 'left', 'back'), 'back-left')
  assert.equal(triaTram(DICC2, 'back', 'left'), 'back-left')
  assert.equal(triaTram(DICC2, 'front', 'right'), 'front-right')
})

test('dins d\'una combinada, cada eix es canvia sol', () => {
  assert.equal(triaTram(DICC2, 'back-left', 'right'), 'back-right')   // canvia la banda
  assert.equal(triaTram(DICC2, 'back-left', 'front'), 'front-left')   // canvia la cara
})

test('prémer la píndola encesa d\'una combinada només l\'apaga a ella', () => {
  assert.equal(triaTram(DICC2, 'back-left', 'left'), 'back')
  assert.equal(triaTram(DICC2, 'back-left', 'back'), 'left')
})

test('una posició SENSE sub-eix segueix sent excloent amb tot el seu eix', () => {
  assert.equal(triaTram(DICC2, 'back-left', 'top'), 'top')      // `top` se les endú totes dues
  assert.equal(triaTram(DICC2, 'top', 'left'), 'left')          // i marxa quan n'entra una
})

test('l\'estat segueix creuant-se amb la posició sencera', () => {
  assert.equal(triaTram(DICC2, 'back-left', 'relaxed'), 'back-left-relaxed')
  assert.equal(triaTram(DICC2, 'back-left-relaxed', 'right'), 'back-right-relaxed')
})

test('tramsPerEix indexa per la FAMÍLIA, i cau a l\'eix quan no n\'hi ha', () => {
  // La clau d'exclusió és la FAMÍLIA sola des del 26/08 (era `EIX/subeix`).
  assert.deepEqual(tramsPerEix(DICC2, 'back-left'), { CARA: 'back', LATERAL: 'left' })
  // `top` no en té a DICC2 (payload d'un backend anterior): cau a l'eix, com abans.
  assert.deepEqual(tramsPerEix(DICC2, 'top'), { POSICIO: 'top' })
})

test('el modal ＋ segueix la mateixa llei que la fila', () => {
  assert.deepEqual(triaAlModal(DICC2, { LATERAL: 'left' }, 'back'),
    { LATERAL: 'left', CARA: 'back' })
  assert.deepEqual(triaAlModal(DICC2, { LATERAL: 'left' }, 'right'), { LATERAL: 'right' })
  // `top` sense família (payload vell) segueix rellevant tot el seu eix.
  assert.deepEqual(triaAlModal(DICC2, { CARA: 'back', LATERAL: 'left' }, 'top'),
    { POSICIO: 'top' })
  assert.deepEqual(triaAlModal(DICC2, { CARA: 'back' }, 'back'), {})
  assert.equal(aplicaCombinacio(DICC2, { CARA: 'back', LATERAL: 'left' }), 'back-left')
})

// ── 6 · LES SIS FAMÍLIES (llei d'Agus, 26/08) ─────────────────────────────────
// DICC2 és el payload de QUAN les famílies eren dues i sis slugs eren orfes; es queda perquè
// prova la compatibilitat amb un backend endarrerit. Aquest és el d'ARA.
const DICC3 = {
  eixos: DICC.eixos,
  subeixos: ['PECA', 'BANDA', 'VERTICALITAT', 'COSTURA', 'LINIA', 'ESTAT'],
  instancies: {
    POSICIO: [
      { slug: 'front', subeix: 'PECA', display_order: 9 },
      { slug: 'back', subeix: 'PECA', display_order: 10 },
      { slug: 'left', subeix: 'BANDA', display_order: 1 },
      { slug: 'right', subeix: 'BANDA', display_order: 2 },
      { slug: 'top', subeix: 'VERTICALITAT', display_order: 3 },
      { slug: 'bottom', subeix: 'VERTICALITAT', display_order: 4 },
      { slug: 'side', subeix: 'COSTURA', display_order: 7 },
      { slug: 'waistband_seam', subeix: 'COSTURA', display_order: 8 },
      { slug: 'cf', subeix: 'LINIA', display_order: 5 },
      { slug: 'cb', subeix: 'LINIA', display_order: 6 },
    ],
    ESTAT: [
      { slug: 'relaxed', subeix: 'ESTAT', display_order: 1 },
      { slug: 'extended', subeix: 'ESTAT', display_order: 2 },
    ],
  },
  regles: { instancia_separador: '-' },
}

test('🚨 les SIS famílies es creuen: cap n\'apaga una altra', () => {
  // El símptoma de la formació, dit en gestos: prémer «Top» apagava «Left».
  let v = ''
  for (const s of ['front', 'left', 'top', 'side', 'cf', 'relaxed']) v = triaTram(DICC3, v, s)
  assert.equal(v, 'front-left-top-side-cf-relaxed')
})

test('dins de CADA família, la segona píndola rellevà la primera', () => {
  for (const [a, b] of [['front', 'back'], ['left', 'right'], ['top', 'bottom'],
                        ['side', 'waistband_seam'], ['cf', 'cb'], ['relaxed', 'extended']]) {
    assert.equal(triaTram(DICC3, a, b), b, `${a} → ${b}`)
  }
})

test('l\'ordre canònic no depèn del clic, amb les sis famílies', () => {
  let v = ''
  for (const s of ['relaxed', 'cf', 'side', 'top', 'left', 'front']) v = triaTram(DICC3, v, s)
  assert.equal(v, 'front-left-top-side-cf-relaxed')
})

test('la redundància és LEGAL: front + cf conviuen', () => {
  assert.equal(triaTram(DICC3, 'front', 'cf'), 'front-cf')
})
