// El banc de la lectura del contracte de peces. La regla que aquí es guarda no és estètica:
// «hereta S·M·L» i «declara S·M·L» pinten el mateix text i han de sortir DIFERENTS a la
// pantalla, perquè si el model canvia, un dels dos canviarà i l'altre no.
//
//     node --test frontend/src/utils/pecaDefinicio.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { ORIGEN, anclaDeLaPeca, nomDeLaPeca, origenDeLaFila, presentacioCamp,
  seguentCodiDePeca } from './pecaDefinicio.js'

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

test('«del model» NO és «hereta», ni tan sols quan el camp diu heretat', () => {
  // La distinció que l'Agus va demanar explícitament (11/08). «Hereta» parla d'un override que
  // existeix i que ara és NULL; «del model» parla d'un camp que la peça NO té i no tindrà. Si
  // es pintessin igual, la fila de «Peça» prometria una porta d'edició que no ha d'arribar mai.
  const heretat = { valor: 'S·M·L', etiqueta: 'S·M·L', heretat: true }

  assert.equal(origenDeLaFila(heretat), ORIGEN.HERETAT)
  assert.equal(origenDeLaFila(heretat, { delModel: true }), ORIGEN.DEL_MODEL)
  assert.notEqual(ORIGEN.DEL_MODEL, ORIGEN.HERETAT)
})

test('els tres origens són tres, i el propi és el que no diu res', () => {
  assert.equal(origenDeLaFila({ valor: '3M·6M', etiqueta: '3M·6M', heretat: false }), ORIGEN.PROPI)
  assert.equal(origenDeLaFila(null), ORIGEN.PROPI)              // sense camp, no s'afirma herència
  assert.equal(new Set(Object.values(ORIGEN)).size, 3)
})

// ── SET-2/T7-B3 · el codi que es proposa ─────────────────────────────────────────────────

test('la primera peça de debò és la 02: la mare ocupa l\'1 encara que no tingui fila', () => {
  assert.equal(seguentCodiDePeca([{ es_mare: true, codi: '' }]), '02')
  assert.equal(seguentCodiDePeca([]), '02')
  assert.equal(seguentCodiDePeca(null), '02')
})

test('es proposa el següent del MÀXIM, no el següent del recompte', () => {
  // El cas que trencaria comptar: la '02' s'ha esborrat i la '03' viu. Amb el recompte es
  // proposaria '03' i el desat xocaria amb un 409 `garment_duplicat` que ningú ha buscat.
  const ambForat = [{ es_mare: true, codi: '' }, { es_mare: false, codi: '03' }]

  assert.equal(seguentCodiDePeca(ambForat), '04')
})

test('un codi no numèric no participa del càlcul però tampoc el trenca', () => {
  const barreja = [{ es_mare: true, codi: '' }, { es_mare: false, codi: '02' },
    { es_mare: false, codi: 'CAPUTXA' }]

  assert.equal(seguentCodiDePeca(barreja), '03')
  // I si NOMÉS n'hi ha de no numèrics, es torna a la primera lliure.
  assert.equal(seguentCodiDePeca([{ es_mare: false, codi: 'CAPUTXA' }]), '02')
})
