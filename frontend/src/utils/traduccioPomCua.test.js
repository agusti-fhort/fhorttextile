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

// ── F4 · EL TROSSEJAT (26/08) ────────────────────────────────────────────────────────────
//
// `/poms` carrega el catàleg SENCER i el passava tot en UNA petició; la porta en refusa més de
// 300 amb un 400 i el `catch` era mut, o sigui que la ⓘ no sortia mai i ningú veia cap error.
// Aquí es compta el nombre de CRIDES, que és el que el defecte tenia malament — no el resultat,
// que ja sortia bé quan la petició cabia.

const idsSintetics = (n) => Array.from({ length: n }, (_, i) => i + 1)

test('F4 · 450 ids surten en LOTS, i cap lot passa del sostre', async () => {
  const b = banc(tradueix)
  b.cua.demana(idsSintetics(450), 'es')
  await b.tic()
  assert.ok(b.crides.length > 1, 'hauria d\'haver trossejat')
  for (const c of b.crides) {
    assert.ok(c.ids.length <= 300, `un lot de ${c.ids.length} passa del sostre de la porta`)
  }
  // Cap id perdut ni repetit pel camí: el trossejat reparteix, no filtra.
  const tots = b.crides.flatMap(c => c.ids).map(Number).sort((x, y) => x - y)
  assert.deepEqual(tots, idsSintetics(450))
})

test('F4 · trossejat o no, la memòria acaba tenint TOTS els noms', async () => {
  const b = banc(tradueix)
  b.cua.demana(idsSintetics(450), 'es')
  await b.tic()
  assert.equal(b.cua.memoritzada(1, 'es'), 'es:1')
  assert.equal(b.cua.memoritzada(250, 'es'), 'es:250')
  assert.equal(b.cua.memoritzada(450, 'es'), 'es:450')
})

test('F4 · un lot que cap segueix sent UNA sola petició (no es trosseja per gust)', async () => {
  const b = banc(tradueix)
  b.cua.demana(idsSintetics(150), 'es')
  await b.tic()
  assert.equal(b.crides.length, 1)
})

test('F4 · un 4xx NO es reintenta; un tall de xarxa SÍ', async () => {
  // El refús de la porta és determinista: tornar-hi dona el mateix i deixa la pantalla igual
  // de muda, però amb una petició per muntatge per sempre.
  const err4xx = Object.assign(new Error('400'), { response: { status: 400 } })
  const b = banc(() => { throw err4xx })
  b.cua.demana([1, 2], 'es')
  await b.tic()
  assert.equal(b.crides.length, 1)
  b.cua.demana([1, 2], 'es')          // el proper muntatge de la pantalla
  await b.tic()
  assert.equal(b.crides.length, 1, 'un 400 no s\'ha de tornar a demanar')

  // Un tall de xarxa (sense `response`) sí que ha de poder tornar: la ⓘ no pot quedar muda per
  // sempre per un segon dolent. És el comportament que ja hi havia i que es conserva.
  const b2 = banc(() => { throw new Error('network') })
  b2.cua.demana([1, 2], 'es')
  await b2.tic()
  b2.cua.demana([1, 2], 'es')
  await b2.tic()
  assert.equal(b2.crides.length, 2, 'un tall de xarxa sí que s\'ha de reintentar')
})
