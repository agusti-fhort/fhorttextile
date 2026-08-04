// El SUFIX que fa únic el nom d'una mesura a una superfície d'una sola línia.
//     cd frontend && node --test src/utils/capaInstancia.test.js
//
// LA PROMESA QUE FIXA: a una taula de PAPER —on no hi ha columna de capa, només la cel·la del
// nom— dues germanes no es poden llegir igual. Abans d'això, la fitxa de ROSALIA imprimia
// «Chest width» i «Chest width» amb xifres diferents, i el document se n'anava al fabricant.
//
// I la promesa INVERSA, que és la que protegeix les 600 files que no són germanes: una mesura
// única d'exterior no canvia de forma. El sufix és buit i la cel·la diu exactament el que deia.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { sufixIdentitat, etiquetaCapa, etiquetaInstancia } from './capaInstancia.js'

// Traductor de mentida amb la forma del real: torna la clau, que és el que fa `t()` quan no
// troba literal. Prou per fixar QUINA clau es demana i en quin ordre — que és el contracte.
const t = (clau) => clau

test('la mesura única d\'exterior no porta sufix: la fila no canvia de forma', () => {
  assert.equal(sufixIdentitat({ capa: 'exterior', instancia: '' }, t), '')
  // Sense eixos declarats és el mateix cas (C4: una mesura sense eixos és l'exterior únic).
  assert.equal(sufixIdentitat({}, t), '')
  assert.equal(sufixIdentitat({ capa: '', instancia: '' }, t), '')
})

test('la germana de CAPA porta la seva capa', () => {
  assert.equal(sufixIdentitat({ capa: 'folre', instancia: '' }, t), ' · capa.folre')
})

test('la germana d\'INSTÀNCIA porta la seva instància', () => {
  assert.equal(sufixIdentitat({ capa: 'exterior', instancia: 'left' }, t), ' · instancia.left')
  assert.equal(sufixIdentitat({ capa: 'exterior', instancia: 'right' }, t), ' · instancia.right')
})

test('amb els dos eixos: INSTÀNCIA primer, capa després', () => {
  // Es llegeix com es diu: la instància qualifica la mesura («la sisa esquerra») i la capa diu
  // de quina matèria parla («…al folre»). L'ordre invers no es llegeix.
  assert.equal(sufixIdentitat({ capa: 'folre', instancia: 'left' }, t),
    ' · instancia.left · capa.folre')
})

test('una instància composta es desmunta pels guions, sense perdre cap tram', () => {
  assert.equal(sufixIdentitat({ capa: 'exterior', instancia: 'left-relaxed' }, t),
    ' · instancia.left · instancia.relaxed')
})

test('un slug desconegut es mostra CRU, mai desapareix', () => {
  // Val més veure «Sleeve · 2» que no veure res: el diccionari d'instàncies encara no existeix.
  // El compost es desmunta pels guions SEMPRE, també quan cap tram té literal — per això el
  // separador surt entremig i no es recompon el slug original.
  assert.equal(sufixIdentitat({ capa: 'exterior', instancia: 'sleeve-2' }, t), ' · Sleeve · 2')
  assert.equal(sufixIdentitat({ capa: 'malla', instancia: '' }, t), ' · Malla')
})

test('res no peta amb una fila absent', () => {
  assert.equal(sufixIdentitat(null, t), '')
  assert.equal(sufixIdentitat(undefined, t), '')
})

test('etiquetaCapa: el buit és l\'exterior, no «sense capa»', () => {
  // La columna és NOT NULL amb default; el buit vol dir «l'exterior de sempre».
  assert.equal(etiquetaCapa('', t), 'capa.exterior')
  assert.equal(etiquetaCapa(null, t), 'capa.exterior')
})

test('etiquetaInstancia: la instància única torna buit, no un guió penjat', () => {
  assert.equal(etiquetaInstancia('', t), '')
  assert.equal(etiquetaInstancia(null, t), '')
})
