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

import { agrupaPerPeca, capaEfectiva, estatDeLaPeca, filaAmbIdentitat, identitatEfectiva, instanciaEfectiva, pecaEfectiva, pecaVisible } from './filaPas2.js'

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

// ── SET-2/T8-ter · LA PEÇA A LA FILA ───────────────────────────────────────────────────
// Tres estats i una regla per cadascun. El que aquests guards defensen:
//   1 · «ningú no ho ha mirat» i «algú ha dit que és de la mare» NO són el mateix estat.
//   2 · la PROPOSTA del document no és una decisió, i no pot arribar al confirm com si ho fos.
//   3 · el control: sense res pendent ni proposat, la fila diu la peça de la SESSIÓ — que és
//       el comportament d'abans d'aquesta peça, byte a byte.

test('T8-ter · sense res dit, la fila és de la peça de la sessió (el control)', () => {
  assert.equal(pecaEfectiva({ ordre: 1 }, {}, '02'), '02')
  assert.equal(pecaEfectiva({ ordre: 1 }, {}, ''), '')
  assert.equal(estatDeLaPeca({ ordre: 1 }, {}), 'defecte')
})

test('T8-ter · la proposta del document es veu, però NO és una decisió', () => {
  const fila = { ordre: 1, garment_proposat: '02' }
  assert.equal(estatDeLaPeca(fila, {}), 'proposat')
  assert.equal(pecaVisible(fila, {}, ''), '02', 'la proposta s\'ha de veure col·locada')
  assert.equal(pecaEfectiva(fila, {}, ''), '', 'la proposta no pot arribar al confirm')
})

test('T8-ter · confirmar el proposat amb un clic el fa DECIDIT', () => {
  const fila = { ordre: 1, garment_proposat: '02' }
  const pendents = { 1: { garment: '02' } }
  assert.equal(estatDeLaPeca(fila, pendents), 'decidit')
  assert.equal(pecaEfectiva(fila, pendents, ''), '02')
})

test('T8-ter · triar LA MARE és una decisió, no una absència', () => {
  // El vermell d'`||`: amb `||` una tria de mare es llegiria com «no s'ha triat res» i la
  // columna tornaria a àmbar just després que algú l'hagi decidida.
  const fila = { ordre: 1, garment_proposat: '02' }
  const pendents = { 1: { garment: '' } }
  assert.equal(estatDeLaPeca(fila, pendents), 'decidit')
  assert.equal(pecaEfectiva(fila, pendents, '02'), '')
  assert.equal(pecaVisible(fila, pendents, '02'), '')
})

test('T8-ter · la pendent mana sobre la desada', () => {
  const fila = { ordre: 1, garment: '02' }
  assert.equal(pecaEfectiva(fila, { 1: { garment: '03' } }, ''), '03')
  assert.equal(estatDeLaPeca(fila, {}), 'decidit', 'una fila ja desada amb peça és decidida')
})

test('T8-ter · la peça viu al MATEIX mapa que capa i instància, sense trepitjar-les', () => {
  const fila = { ordre: 1, capa: 'exterior', instancia: 'bottom' }
  const pendents = { 1: { garment: '02' } }
  assert.deepEqual(identitatEfectiva(fila, pendents), { capa: 'exterior', instancia: 'bottom' })
  assert.equal(pecaEfectiva(fila, pendents, ''), '02')
})

test('T8-ter · el pas 3 parteix per PEÇA: files alternades donen DOS contenidors', () => {
  // Un document que alterni faldilla · short · faldilla ha de donar dos contenidors, no tres:
  // amb tres, el tècnic veuria la mateixa peça dues vegades i no sabria quina taula és quina.
  const items = [{ g: '' }, { g: '02' }, { g: '' }]
  const grups = agrupaPerPeca(items, x => x.g, ['', '02'])
  assert.equal(grups.length, 2)
  assert.deepEqual(grups.map(g => g.codi), ['', '02'])
  assert.equal(grups[0].items.length, 2)
  assert.equal(grups[1].items.length, 1)
})

test('T8-ter · l\'ordre és el del MODEL, no el d\'aparició al document', () => {
  const items = [{ g: '02' }, { g: '' }]
  assert.deepEqual(agrupaPerPeca(items, x => x.g, ['', '02']).map(g => g.codi), ['', '02'])
})

test('T8-ter · una peça que ja no és del model es pinta igual, al final', () => {
  // Amagar-la seria perdre files en silenci.
  const items = [{ g: '' }, { g: '99' }]
  const grups = agrupaPerPeca(items, x => x.g, ['', '02'])
  assert.deepEqual(grups.map(g => g.codi), ['', '99'])
})
