// El banc de la lectura del contracte de peces. La regla que aquí es guarda no és estètica:
// «hereta S·M·L» i «declara S·M·L» pinten el mateix text i han de sortir DIFERENTS a la
// pantalla, perquè si el model canvia, un dels dos canviarà i l'altre no.
//
//     node --test frontend/src/utils/pecaDefinicio.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { anclaDeLaPeca, nomDeLaPeca, presentacioCamp } from './pecaDefinicio.js'

test('el mateix text amb herències distintes NO és el mateix estat', () => {
  const declarat = presentacioCamp({ valor: 'S·M·L', etiqueta: 'S·M·L', heretat: false })
  const heretat = presentacioCamp({ valor: 'S·M·L', etiqueta: 'S·M·L', heretat: true })

  assert.equal(declarat.text, heretat.text)
  assert.notEqual(declarat.heretat, heretat.heretat)
})

test('el buit és un ESTAT, no l\'absència de la fila', () => {
  // Un model sense joc de graduació: el contracte emet `valor: null` a posta (una clau absent
  // obligaria el client a distingir «no ho sé» de «no n'hi ha»). La fila s'ha de seguir pintant.
  const cap = presentacioCamp({ valor: null, etiqueta: '', heretat: true })

  assert.equal(cap.buit, true)
  assert.equal(cap.text, '')
  assert.equal(cap.heretat, true)   // heretar el no-res segueix sent heretar
})

test('un FK sense etiqueta útil segueix tenint contingut', () => {
  // `buit` mira el VALOR, no el text: un FK pot arribar amb PK i amb `etiqueta: ''`, i llavors
  // la fila té valor encara que no tingui res a escriure.
  assert.equal(presentacioCamp({ valor: 12, etiqueta: '', heretat: false }).buit, false)
})

test('un camp que no ha arribat no peta i es llegeix com a buit', () => {
  for (const entrada of [undefined, null]) {
    const p = presentacioCamp(entrada)
    assert.equal(p.buit, true)
    assert.equal(p.heretat, false)
    assert.equal(p.text, '')
  }
})

test('la MARE no és una peça sense nom: és el model', () => {
  assert.equal(nomDeLaPeca({ es_mare: true, codi: '', nom: 'Blusa KAYCE' }, 'Model base'),
    'Model base')
  assert.equal(nomDeLaPeca({ es_mare: false, codi: '02', nom: 'Pantaló' }, 'Model base'),
    'Pantaló')
  // Una peça batejada encara no: el codi és el que la identifica, i no queda muda.
  assert.equal(nomDeLaPeca({ es_mare: false, codi: '02', nom: '' }, 'Model base'), '02')
})

test('l\'ancla de la mare no és `#peca-`', () => {
  assert.equal(anclaDeLaPeca({ es_mare: true, codi: '' }), 'peca-base')
  assert.equal(anclaDeLaPeca({ es_mare: false, codi: '02' }), 'peca-02')
})
