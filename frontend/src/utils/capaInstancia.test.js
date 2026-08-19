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

// El diccionari, tal com el serveix `GET /api/v1/mesures/diccionari/`. Les capes ja no són cap
// constant del client (F2.2): els seus literals vénen d'aquí, i per això les proves n'han de
// portar un. Només les dues capes que els casos toquen.
const dicc = { capes: [
  { slug: 'exterior', nom_en: 'Shell', nom_ca: 'Exterior', nom_es: 'Exterior' },
  { slug: 'folre', nom_en: 'Lining', nom_ca: 'Folre', nom_es: 'Forro' },
] }

test('la mesura única d\'exterior no porta sufix: la fila no canvia de forma', () => {
  assert.equal(sufixIdentitat({ capa: 'exterior', instancia: '' }, dicc), '')
  // Sense eixos declarats és el mateix cas (C4: una mesura sense eixos és l'exterior únic).
  assert.equal(sufixIdentitat({}, dicc), '')
  assert.equal(sufixIdentitat({ capa: '', instancia: '' }, dicc), '')
})

test('la germana de CAPA porta la seva capa', () => {
  assert.equal(sufixIdentitat({ capa: 'folre', instancia: '' }, dicc), ' · Folre')
})

test('la germana d\'INSTÀNCIA porta la seva instància, EN ANGLÈS CANÒNIC', () => {
  // No passa per `t()`: la paraula d'instància és la que allarga el nom del POM i de la qual
  // surt el sufix del codi (`AHL`). Traduir-la deixaria dues llengües a la mateixa línia.
  assert.equal(sufixIdentitat({ capa: 'exterior', instancia: 'left' }, dicc), ' · Left')
  assert.equal(sufixIdentitat({ capa: 'exterior', instancia: 'right' }, dicc), ' · Right')
})

test('amb els dos eixos: INSTÀNCIA primer, capa després', () => {
  // Es llegeix com es diu: la instància qualifica la mesura («la sisa esquerra») i la capa diu
  // de quina matèria parla («…al folre»). L'ordre invers no es llegeix.
  assert.equal(sufixIdentitat({ capa: 'folre', instancia: 'left' }, dicc),
    ' · Left · Folre')
})

test('una instància composta es desmunta pels guions, sense perdre cap tram', () => {
  assert.equal(sufixIdentitat({ capa: 'exterior', instancia: 'left-relaxed' }, t),
    ' · Left · Relaxed')
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
  assert.equal(sufixIdentitat(undefined, dicc), '')
})

test('etiquetaCapa: el buit és l\'exterior, no «sense capa»', () => {
  // La columna és NOT NULL amb default; el buit vol dir «l'exterior de sempre».
  assert.equal(etiquetaCapa('', dicc), 'Exterior')
  assert.equal(etiquetaCapa(null, dicc), 'Exterior')
})

test('etiquetaInstancia: la instància única torna buit, no un guió penjat', () => {
  assert.equal(etiquetaInstancia(''), '')
  assert.equal(etiquetaInstancia(null), '')
})

test('LA PARAULA D\'INSTÀNCIA NO ES TRADUEIX: anglès canònic sempre', () => {
  // La promesa de fons: la mateixa fila es llegeix igual a la pantalla catalana, a l'anglesa i
  // a la fitxa que va al fabricant, perquè el sufix del codi (`L`) surt d'aquesta paraula.
  assert.equal(etiquetaInstancia('left'), 'Left')
  assert.equal(etiquetaInstancia('waistband_seam'), 'Waistband seam')
  // NET, sense sinònim: `extended` i `stretched`/`stretched out` són el mateix estat i el nom
  // canònic és un de sol (Agus, 06/08). Aquest camí és el del MIRALL —sense diccionari— i no
  // passa per `curta()`, o sigui que el que hi hagi escrit a `NOM_INSTANCIA` és el que es veurà.
  assert.equal(etiquetaInstancia('extended'), 'Extended')
  // CF/CB són acrònims del sector i no es desmunten ni es capitalitzen.
  assert.equal(etiquetaInstancia('cf'), 'CF')
})

test('amb diccionari MANA LA BD: un tenant pot tenir una instància que el front no coneix', () => {
  const dicc = { instancies: { POSICIO: [{ slug: 'sleeve_head', nom_en: 'Sleeve head' }] } }
  assert.equal(etiquetaInstancia('sleeve_head', dicc), 'Sleeve head')
  // I si la BD reanomena una de canòniques, mana ella i no el mirall d'aquest fitxer.
  const renom = { instancies: { POSICIO: [{ slug: 'left', nom_en: 'Left side' }] } }
  assert.equal(etiquetaInstancia('left', renom), 'Left side')
})
