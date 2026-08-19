// GUARD · LA FITXA TÈCNICA NO ES POT TORNAR A PINTAR AMB EL LAYOUT GENERAL.
//
// El 09/08 el commit 133496e2 va moure la `<Route>` de l'editor .ftt de FORA del `Shell` a
// DINS, i ningú se'n va adonar fins que Agus ho va veure a pantalla el 14/08: l'eina havia
// perdut la pantalla completa i li havien aparegut a sobre el sidebar, la top bar i les nou
// píndoles de seccions del model. Va passar EN SILENCI perquè no hi havia res que ho vigilés:
// el build passava, els tests passaven, i el símptoma només es veu obrint la pantalla.
//
// Aquest test fixa la INVARIANT, no la implementació. La fitxa pot arribar a la pantalla
// completa per dos camins legítims —tenint la ruta fora del `Shell`, com el Taller de patró, o
// tenint-la dins però declarada a `rutesPantallaCompleta`— i el guard accepta els dos. El que
// no accepta és el tercer cas: dins del Shell i sense declarar, que és exactament l'estat en
// què va quedar del 09/08 al 14/08.
//
// Es llegeix el SOURCE d'`App.jsx` a posta. Muntar el router sencer aquí voldria dir un DOM i
// mitja aplicació; el que cal comprovar és estructural i es veu al fitxer: ¿on cau la ruta
// respecte del `<Route path="/">` que munta el `Shell`?
//
// Córrer: `node --test src/components/layout/rutesPantallaCompleta.test.js` (des de `frontend/`).
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

import { esPantallaCompleta } from './rutesPantallaCompleta.js'

const AQUI = dirname(fileURLToPath(import.meta.url))
const APP = readFileSync(resolve(AQUI, '../../App.jsx'), 'utf8')

/** Línia (1-indexada) del primer match, o null. */
function linia(re) {
  const idx = APP.split('\n').findIndex(l => re.test(l))
  return idx === -1 ? null : idx + 1
}

test('el matcher reconeix la ruta de la fitxa tècnica', () => {
  assert.equal(esPantallaCompleta('/models/1320/ftt/762'), true)
  assert.equal(esPantallaCompleta('/models/1/ftt/1/'), true)
})

test('el matcher NO s\'endú les pàgines del model', () => {
  // Si aquestes hi entressin, el sidebar desapareixeria de mitja aplicació.
  for (const p of ['/models/1320', '/models/1320/escalat', '/models/1320/fitxa',
                   '/models', '/', '/models/1320/ftt']) {
    assert.equal(esPantallaCompleta(p), false, `${p} no és pantalla completa`)
  }
})

test('LA INVARIANT · la fitxa .ftt no es renderitza amb el layout general', () => {
  const ftt = linia(/path=["'][^"']*ftt\/:fitxerId/)
  const shell = linia(/<Route path="\/" element=/)
  assert.ok(ftt, 'no s\'ha trobat la ruta de la fitxa a App.jsx')
  assert.ok(shell, 'no s\'ha trobat el <Route path="/"> que munta el Shell')

  const dinsDelShell = ftt > shell
  if (!dinsDelShell) return   // fora del Shell, com el Taller de patró: correcte.

  // Dins del Shell → ha d'estar declarada com a pantalla completa, o l'eina perd la pantalla.
  assert.equal(
    esPantallaCompleta('/models/1320/ftt/762'), true,
    `La ruta de la fitxa (App.jsx:${ftt}) és DINS del Shell (App.jsx:${shell}) i no està `
    + 'declarada a rutesPantallaCompleta: es pintarà amb sidebar, top bar i tabs del model.')

  // …i el Shell ha de consumir la declaració de debò. Sense això, la llista seria decorativa.
  const shellSrc = readFileSync(resolve(AQUI, 'Shell.jsx'), 'utf8')
  assert.match(
    shellSrc, /esPantallaCompleta/,
    'Shell.jsx no consumeix esPantallaCompleta: la declaració no la mira ningú.')
})
