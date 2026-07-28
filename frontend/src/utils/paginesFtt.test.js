// F4 — el format per pàgina ha de sobreviure a desar i reobrir.
//     cd frontend && node --test src/utils/paginesFtt.test.js
//
// EL BUG (QA real): posar la pàgina 2 en vertical funcionava mentre el document era obert,
// però en reobrir tornava a horitzontal. El .ftt SÍ portava la clau `format` (l'escriptura
// era correcta a totes tres funcions, i el backend té els seus propis tests): qui la perdia
// era la HIDRATACIÓ, que reconstruïa cada pàgina amb {id, objects, guides} i prou.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { ambFormat, hidratarPagines } from './paginesFtt.js'

let n = 0
const uid = () => `gen-${++n}`

// El que fan serializePages / v2ToDocument / documentToV2 amb cada pàgina.
const serialitza = (pagines) => pagines.map(p => ambFormat(p, { id: p.id, objects: p.objects || [], guides: p.guides || [] }))

test('roundtrip: la pàgina 2 en A4P reobre en A4P i la 1 hereta el document', () => {
  const estat = [
    { id: 'p1', objects: [], guides: [] },
    { id: 'p2', objects: [], guides: [], format: 'A4P' },   // posada en vertical a la UI
  ]
  const alFitxer = serialitza(estat)
  assert.equal(alFitxer[1].format, 'A4P', 'el .ftt ha de portar la clau')

  const reobert = hidratarPagines(alFitxer, uid)
  assert.equal(reobert[1].format, 'A4P')          // ← això fallava: sortia undefined
  assert.equal('format' in reobert[0], false)     // la 1 no en declara cap → hereta A4L del document
})

test('un document sense formats mixtos no en guanya cap (retrocompat byte a byte)', () => {
  const vell = [{ id: 'p1', objects: [{ id: 'o1', type: 'rect' }] }]
  const reobert = hidratarPagines(vell, uid)
  assert.equal('format' in reobert[0], false)
  assert.deepEqual(serialitza(reobert), [{ id: 'p1', objects: [{ id: 'o1', type: 'rect' }], guides: [] }])
})

test('la hidratació no perd res més de la pàgina: objects i guides tornen', () => {
  const reobert = hidratarPagines([{ id: 'p1', objects: [{ id: 'o1' }], guides: [{ pos: 5 }], format: 'A3L' }], uid)
  assert.deepEqual(reobert[0], { id: 'p1', objects: [{ id: 'o1' }], guides: [{ pos: 5 }], format: 'A3L' })
})

test('documents antics sense id: se n\'hi genera un, i el format es manté igual', () => {
  const reobert = hidratarPagines([{ objects: [{ type: 'text' }], format: 'A4P' }], uid)
  assert.match(reobert[0].id, /^gen-/)
  assert.match(reobert[0].objects[0].id, /^gen-/)
  assert.equal(reobert[0].format, 'A4P')
})

// SEMÀNTICA TROBADA (F4, TechSheetEditor: setPageFormatDePagina i aplicarFormatATotElDocument):
// el `format` de pàgina és una EXCEPCIÓ a l'herència, no un valor absolut. Triar per a una
// pàgina el mateix valor que el document ESBORRA la clau (torna a heretar), i "Aplicar a tot el
// document" mou el valor al document i neteja totes les excepcions. Canviar el format del
// document per aquesta via, doncs, sí que esborra els formats de pàgina — és el gest que ho
// demana explícitament. El que no els ha de tocar mai és desar i reobrir.
test('el format de pàgina és una excepció a l\'herència, no un valor absolut', () => {
  const pagina = { id: 'p1', objects: [], format: 'A4P' }
  const { format: _fora, ...senseExcepcio } = pagina        // el que fa la UI quan tries l'herència
  assert.equal('format' in serialitza([senseExcepcio])[0], false)
  assert.equal(serialitza([pagina])[0].format, 'A4P')
})
