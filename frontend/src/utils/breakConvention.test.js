// La traducció ±1 és l'única peça que, si s'equivoca, produeix un error INVISIBLE: una talla
// desplaçada es llegeix igual de bé que la correcta. Per això va amb banc propi.
//
//     node --test frontend/src/utils/breakConvention.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { aDocument, aMotor, etiquetaRegla, etiquetesDelRun, opcionsDocument } from './breakConvention.js'

const RUN = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']

test('els 3 parells reals de Brownie (142/142 del contrast del 10/08)', () => {
  assert.equal(aDocument('S', RUN), 'XS')      // 86 regles
  assert.equal(aDocument('M', RUN), 'S')       // 12 regles
  assert.equal(aDocument(null, RUN), null)     // 44 regles sense break
  assert.equal(aMotor('XS', RUN), 'S')
  assert.equal(aMotor('S', RUN), 'M')
})

test('anada i tornada: traduir i desfer torna al mateix punt', () => {
  for (const et of RUN.slice(1)) assert.equal(aMotor(aDocument(et, RUN), RUN), et)
  for (const et of RUN.slice(0, -1)) assert.equal(aDocument(aMotor(et, RUN), RUN), et)
})

test('els extrems no són representables i tornen null, no una talla inventada', () => {
  assert.equal(aDocument('XXS', RUN), null)    // la primera no té anterior
  assert.equal(aMotor('3XL', RUN), null)       // l'última no té següent
})

test('sense run, o amb etiqueta forana, MAI s\'endevina', () => {
  assert.equal(aDocument('S', []), null)
  assert.equal(aDocument('S', null), null)
  assert.equal(aDocument('42', RUN), null)
  assert.equal(aMotor('42', RUN), null)
})

test('compara com el motor: upper + strip', () => {
  assert.equal(aDocument(' s ', RUN), 'XS')
  assert.equal(aDocument('m', RUN), 'S')
})

test('el run accepta les dues formes (etiquetes o objectes)', () => {
  assert.deepEqual(etiquetesDelRun([{ etiqueta: 'XS' }, { etiqueta: 'S' }]), ['XS', 'S'])
  assert.equal(aDocument('S', [{ etiqueta: 'XS' }, { etiqueta: 'S' }]), 'XS')
})

test('les opcions ofertes exclouen l\'última talla (no és representable)', () => {
  assert.deepEqual(opcionsDocument(RUN), RUN.slice(0, -1))
  assert.deepEqual(opcionsDocument([]), [])
})

test('l\'etiqueta compacta parla en convenció de document', () => {
  assert.equal(
    etiquetaRegla({ increment_base: 2, increment_break: 3, talla_break_label: 'S' }, RUN, 'trencament'),
    '+2 · trencament XS +3')
  assert.equal(
    etiquetaRegla({ increment_base: 1, increment_break: null, talla_break_label: null }, RUN, 'trencament'),
    '+1')
})

test('sense run traduïble, l\'etiqueta OMET el break en comptes de dir-lo malament', () => {
  assert.equal(
    etiquetaRegla({ increment_base: 2, increment_break: 3, talla_break_label: 'S' }, [], 'trencament'),
    '+2')
  assert.equal(
    etiquetaRegla({ increment_base: null, increment_break: 3, talla_break_label: 'S' }, RUN, 'trencament'),
    '')
})

// ── TRAM F · L'ETIQUETA COMPACTA DELS INTERVALS ──────────────────────────────────────────────
// Els intervals es diuen en convenció de MOTOR i SENSE volta (esmena del 21/08): les etiquetes
// són les que la BD desa i les que el picker ofereix. Aquest test fixa la diferència amb la
// línia de sobre —break d'1 tram, convenció de document— perquè les dues conviuen a la mateixa
// taula i confondre-les seria desplaçar una talla sencera.
test('amb intervals, el compacte els diu en convenció de MOTOR', () => {
  assert.equal(
    etiquetaRegla({ increment_base: 2, breaks: [{ inici: 'S', final: 'L', delta: 3 }] },
      RUN, 'trencament'),
    '+2 · S→L +3')
  assert.equal(
    etiquetaRegla({
      increment_base: 1,
      breaks: [{ inici: 'XS', final: 'S', delta: 2 }, { inici: 'L', final: '3XL', delta: -1 }],
    }, RUN, 'trencament'),
    '+1 · XS→S +2 · L→3XL -1')
})

test('els intervals manen sobre el break d\'1 tram, com al motor', () => {
  assert.equal(
    etiquetaRegla({
      increment_base: 2, increment_break: 9, talla_break_label: 'M',
      breaks: [{ inici: 'S', final: 'L', delta: 3 }],
    }, RUN, 'trencament'),
    '+2 · S→L +3')
})

test('un interval sense Δ encara no diu res i no es pinta', () => {
  assert.equal(
    etiquetaRegla({ increment_base: 2, breaks: [{ inici: 'S', final: 'L', delta: null }] },
      RUN, 'trencament'),
    '+2')
})
