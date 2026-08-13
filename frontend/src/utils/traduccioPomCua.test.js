// TRAM ⓘ — el banc de la cua de traducció.
//
// El que es prova aquí és el que costa diners o deixa la pantalla muda: que N noms siguin UNA
// petició, que el segon cop no en surti cap, i que un tall de xarxa no congeli el silenci.
//
//     node --test frontend/src/utils/traduccioPomCua.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { baseLang, creaCua } from './traduccioPomCua.js'

/** Programador manual: el lot no surt fins que el test ho diu. Res de rellotges als tests. */
function banc(respon) {
  const crides = []
  let pendent = null
  const cua = creaCua(
    async (ids, lang) => { crides.push({ ids: [...ids], lang }); return respon(ids, lang) },
    (fn) => { pendent = fn },
  )
  return {
    cua,
    crides,
    async tic() { const f = pendent; pendent = null; if (f) await f() },
  }
}

const tradueix = (ids, lang) => ids.map(id => ({ pom_id: Number(id), text: `${lang}:${id}` }))

test('N POMs demanats per separat surten en UNA sola petició', async () => {
  const b = banc(tradueix)
  b.cua.demana([1], 'es')
  b.cua.demana([2, 3], 'es')
  b.cua.demana([4], 'es')
  assert.equal(b.crides.length, 0, 'res no ha de sortir abans del tic')
  await b.tic()
  assert.equal(b.crides.length, 1)
  assert.deepEqual(b.crides[0].ids, ['1', '2', '3', '4'].map(Number))
})

test('el segon cop no es torna a demanar', async () => {
  const b = banc(tradueix)
  b.cua.demana([1, 2], 'es')
  await b.tic()
  b.cua.demana([1, 2], 'es')
  await b.tic()
  assert.equal(b.crides.length, 1)
  assert.equal(b.cua.memoritzada(1, 'es'), 'es:1')
})

test('només es demanen els que falten', async () => {
  const b = banc(tradueix)
  b.cua.demana([1], 'es')
  await b.tic()
  b.cua.demana([1, 2, 3], 'es')
  await b.tic()
  assert.deepEqual(b.crides[1].ids, [2, 3])
})

test('cada idioma és una entrada pròpia', async () => {
  const b = banc(tradueix)
  b.cua.demana([1], 'es')
  b.cua.demana([1], 'fr')
  await b.tic()
  assert.equal(b.crides.length, 2, 'dos idiomes són dos lots: la petició en porta un de sol')
  assert.equal(b.cua.memoritzada(1, 'es'), 'es:1')
  assert.equal(b.cua.memoritzada(1, 'fr'), 'fr:1')
})

test('`es-ES` i `es` són la mateixa entrada', async () => {
  const b = banc(tradueix)
  b.cua.demana([1], 'es-ES')
  await b.tic()
  b.cua.demana([1], 'es')
  await b.tic()
  assert.equal(b.crides.length, 1)
  assert.equal(b.cua.memoritzada(1, 'es-ES'), 'es:1')
})

test('sense traducció, silenci: torna cadena buida i no peta', async () => {
  const b = banc(() => [{ pom_id: 1, text: '' }])
  b.cua.demana([1], 'es')
  await b.tic()
  assert.equal(b.cua.memoritzada(1, 'es'), '')
  assert.equal(b.cua.memoritzada(999, 'es'), '', 'un POM que no s\'ha demanat mai tampoc peta')
})

test('una petició fallada NO congela el silenci: al proper muntatge es torna a provar', async () => {
  let peta = true
  const b = banc((ids, lang) => {
    if (peta) throw new Error('xarxa')
    return tradueix(ids, lang)
  })
  b.cua.demana([1], 'es')
  await b.tic()
  assert.equal(b.cua.memoritzada(1, 'es'), '')

  peta = false
  b.cua.demana([1], 'es')
  await b.tic()
  assert.equal(b.crides.length, 2, "l'id fallat s'ha de poder tornar a demanar")
  assert.equal(b.cua.memoritzada(1, 'es'), 'es:1')
})

test('els oients s\'avisen quan arriba text nou, i no quan no n\'arriba', async () => {
  const b = banc(tradueix)
  let avisos = 0
  const baixa = b.cua.subscriu(() => { avisos += 1 })
  b.cua.demana([1], 'es')
  await b.tic()
  assert.equal(avisos, 1)
  b.cua.demana([1], 'es')      // ja memoritzat: no hi ha ni petició
  await b.tic()
  assert.equal(avisos, 1)
  baixa()
  b.cua.demana([2], 'es')
  await b.tic()
  assert.equal(avisos, 1, 'qui s\'ha donat de baixa no rep res')
})

test('sense idioma no es demana res (evita un lot amb la clau buida)', async () => {
  const b = banc(tradueix)
  b.cua.demana([1], '')
  await b.tic()
  assert.equal(b.crides.length, 0)
})

test('ids buits o nuls no entren a la cua', async () => {
  const b = banc(tradueix)
  b.cua.demana([null, undefined, '', 5], 'es')
  await b.tic()
  assert.deepEqual(b.crides[0].ids, [5])
})

test('`oblida` deixa la memòria com el primer dia', async () => {
  const b = banc(tradueix)
  b.cua.demana([1], 'es')
  await b.tic()
  b.cua.oblida()
  assert.equal(b.cua.memoritzada(1, 'es'), '')
  b.cua.demana([1], 'es')
  await b.tic()
  assert.equal(b.crides.length, 2)
})

test('baseLang redueix la regió i tolera el buit', () => {
  assert.equal(baseLang('ca-ES'), 'ca')
  assert.equal(baseLang('es_MX'), 'es')
  assert.equal(baseLang('EN'), 'en')
  assert.equal(baseLang(''), '')
  assert.equal(baseLang(null), '')
})
