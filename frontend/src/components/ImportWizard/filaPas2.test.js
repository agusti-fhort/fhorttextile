// P2-ter/1 · LA FILA DEL PAS 2 INFORMA — el guard.
//
//     cd frontend && node --test src/components/ImportWizard/filaPas2.test.js
//
// Les píndoles se'n van de la fila i la instància passa al NOM. El que això ha de complir, i és
// tot el que aquest fitxer defensa:
//
//   1 · **EL RÈTOL DIU LA DECISIÓ, NO L'ÚLTIM DESAT.** Entre triar «Bottom» al panell i desar el
//       pas 2, la decisió viu només a l'estat local. Si el nom llegís la fila del servidor diria
//       «única» just després d'haver triat, i el gest següent seria reobrir la fila per
//       comprovar-ho — que és exactament el que la peça treu.
//   2 · **UNA TRIA BUIDA ÉS UNA DECISIÓ**: treure la instància («torna a la única») no pot
//       llegir-se com «no s'ha triat res» i ressuscitar la desada.
//   3 · **EL CONTROL**: sense res pendent, el rètol és el d'avui, byte a byte.
//
// La composició de l'etiqueta NO es prova aquí: la fa `sufixIdentitat`, que té els seus onze
// tests. Aquí es prova QUINA identitat se li dona.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { capaEfectiva, filaAmbIdentitat, instanciaEfectiva } from './filaPas2.js'

const FILA = { ordre: 1, codi_fitxa: 'BB', pom_master_id: 7, capa: '', instancia: '' }

// ── 1 · LA DECISIÓ PENDENT MANA ───────────────────────────────────────────────
test('la instància triada i encara no desada és la que el rètol diu', () => {
  assert.equal(instanciaEfectiva(FILA, { 1: { instancia: 'bottom' } }), 'bottom')
})

test('la pendent mana sobre la desada quan discrepen', () => {
  const desada = { ...FILA, instancia: 'top' }
  assert.equal(instanciaEfectiva(desada, { 1: { instancia: 'bottom' } }), 'bottom')
})

test('la fila sencera viatja a `sufixIdentitat` amb la identitat efectiva', () => {
  const vista = filaAmbIdentitat(FILA, { 1: { instancia: 'left-relaxed' } })
  assert.equal(vista.instancia, 'left-relaxed')
  assert.equal(vista.codi_fitxa, 'BB', 'la resta de la fila no es toca')
  assert.equal(vista.pom_master_id, 7)
})

// ── 2 · TREURE-LA ÉS UNA DECISIÓ ──────────────────────────────────────────────
test('treure la instància («torna a la única») no ressuscita la desada', () => {
  const desada = { ...FILA, instancia: 'bottom' }
  assert.equal(instanciaEfectiva(desada, { 1: { instancia: '' } }), '')
})

// ── 3 · EL CONTROL: sense pendents, el d'avui ─────────────────────────────────
test('sense res pendent mana la fila desada', () => {
  assert.equal(instanciaEfectiva({ ...FILA, instancia: 'extended' }, {}), 'extended')
  assert.equal(instanciaEfectiva({ ...FILA, instancia: 'extended' }, undefined), 'extended')
  assert.equal(instanciaEfectiva(FILA, {}), '')
})

test('una altra fila pendent no contamina aquesta', () => {
  assert.equal(instanciaEfectiva(FILA, { 2: { instancia: 'bottom' } }), '')
})

// ── 4 · LA CAPA, EL PRIMER EIX DE LA IDENTITAT ────────────────────────────────
// Cas real (Agus, 16/08): una fila «lining» de la Brumà. Si el panell no pregunta la capa, la
// fila se'n va a l'exterior i es planta damunt de la germana que ja hi és.

test('la capa triada i encara no desada és la que el rètol diu', () => {
  assert.equal(capaEfectiva(FILA, { 1: { capa: 'folre' } }), 'folre')
})

test('capa i instància viatgen JUNTES a la fila que es llegeix', () => {
  const vista = filaAmbIdentitat(FILA, { 1: { capa: 'folre', instancia: 'bottom' } })
  assert.equal(vista.capa, 'folre')
  assert.equal(vista.instancia, 'bottom')
  assert.equal(vista.codi_fitxa, 'BB', 'la resta de la fila no es toca')
})

test('triar la instància no esborra la capa desada, ni al revés', () => {
  const desada = { ...FILA, capa: 'folre', instancia: 'bottom' }
  assert.deepEqual(
    { c: capaEfectiva(desada, { 1: { instancia: 'top' } }),
      i: instanciaEfectiva(desada, { 1: { instancia: 'top' } }) },
    { c: 'folre', i: 'top' })
})

test("tornar a l'exterior és una decisió, no un «res»", () => {
  assert.equal(capaEfectiva({ ...FILA, capa: 'folre' }, { 1: { capa: '' } }), '')
})

test('sense res pendent, la capa desada (i el control: cap = exterior)', () => {
  assert.equal(capaEfectiva({ ...FILA, capa: 'entretela' }, {}), 'entretela')
  assert.equal(capaEfectiva(FILA, {}), '')
})
