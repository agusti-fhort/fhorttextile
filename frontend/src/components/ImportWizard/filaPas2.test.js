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

import { filaAmbIdentitat, instanciaEfectiva } from './filaPas2.js'

const FILA = { ordre: 1, codi_fitxa: 'BB', pom_master_id: 7, instancia: '' }

// ── 1 · LA DECISIÓ PENDENT MANA ───────────────────────────────────────────────
test('la instància triada i encara no desada és la que el rètol diu', () => {
  assert.equal(instanciaEfectiva(FILA, { 1: 'bottom' }), 'bottom')
})

test('la pendent mana sobre la desada quan discrepen', () => {
  const desada = { ...FILA, instancia: 'top' }
  assert.equal(instanciaEfectiva(desada, { 1: 'bottom' }), 'bottom')
})

test('la fila sencera viatja a `sufixIdentitat` amb la identitat efectiva', () => {
  const vista = filaAmbIdentitat(FILA, { 1: 'left-relaxed' })
  assert.equal(vista.instancia, 'left-relaxed')
  assert.equal(vista.codi_fitxa, 'BB', 'la resta de la fila no es toca')
  assert.equal(vista.pom_master_id, 7)
})

// ── 2 · TREURE-LA ÉS UNA DECISIÓ ──────────────────────────────────────────────
test('treure la instància («torna a la única») no ressuscita la desada', () => {
  const desada = { ...FILA, instancia: 'bottom' }
  assert.equal(instanciaEfectiva(desada, { 1: '' }), '')
})

// ── 3 · EL CONTROL: sense pendents, el d'avui ─────────────────────────────────
test('sense res pendent mana la fila desada', () => {
  assert.equal(instanciaEfectiva({ ...FILA, instancia: 'extended' }, {}), 'extended')
  assert.equal(instanciaEfectiva({ ...FILA, instancia: 'extended' }, undefined), 'extended')
  assert.equal(instanciaEfectiva(FILA, {}), '')
})

test('una altra fila pendent no contamina aquesta', () => {
  assert.equal(instanciaEfectiva(FILA, { 2: 'bottom' }), '')
})
