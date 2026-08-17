// Banc d'`estatDeLaPresa` — E1/B3.
//     cd frontend && node --test src/utils/estatPresa.test.js

import test from 'node:test'
import assert from 'node:assert/strict'
import { BUIDA, DECIDIDA, MESURANT, SENSE_PRESA, TANCADA, estatDeLaPresa } from './estatPresa.js'

const payload = (resum, oberta = true) => ({
  presa_oberta: oberta,
  presa_tancada: false,
  session: { id: 7, data: '2026-08-17', estat: 'Oberta' },
  resum: { n_preses: 0, n_linies: 10, talles_amb_presa: [],
           pendents_base: 2, decidides_base: 0, ...resum },
})

// E3a — l'acta: `presa_oberta:false` PERÒ amb sessió i dades. És el payload que abans no existia.
const acta = (resum) => ({
  presa_oberta: false,
  presa_tancada: true,
  session: { id: 7, data: '2026-08-16', estat: 'Tancada' },
  resum: { n_preses: 4, n_linies: 90, talles_amb_presa: ['S', 'M'],
           pendents_base: 1, decidides_base: 1, ...resum },
})

test('sense payload (la crida ha fallat) NO s\'inventa una presa oberta', () => {
  const e = estatDeLaPresa(null)
  assert.equal(e.estat, SENSE_PRESA)
  assert.equal(e.n_preses, 0)
  assert.equal(e.session, null)
})

test('presa_oberta false → SENSE_PRESA', () => {
  assert.equal(estatDeLaPresa(payload({}, false)).estat, SENSE_PRESA)
})

test('oberta i sense cap mesura → BUIDA', () => {
  const e = estatDeLaPresa(payload({}))
  assert.equal(e.estat, BUIDA)
  assert.equal(e.n_linies, 10)
  assert.equal(e.session.id, 7)
})

test('mesurant: hi ha preses i queda base per decidir', () => {
  const e = estatDeLaPresa(payload({ n_preses: 3, talles_amb_presa: ['S', 'L', 'XL'] }))
  assert.equal(e.estat, MESURANT)
  assert.deepEqual(e.talles, ['S', 'L', 'XL'])
  assert.equal(e.pendents_base, 2)
})

test('🔑 amb DUES prendes, una base decidida NO tanca la feina', () => {
  // El cas que un `decidides_base > 0` donaria per fet quan la meitat no ho està.
  const e = estatDeLaPresa(payload({ n_preses: 3, decidides_base: 1, pendents_base: 1 }))
  assert.equal(e.estat, MESURANT)
})

test('decidida: cap base pendent', () => {
  const e = estatDeLaPresa(payload({ n_preses: 3, decidides_base: 2, pendents_base: 0 }))
  assert.equal(e.estat, DECIDIDA)
})

test('mesurada però amb 0 bases al model no es queda a MESURANT per sempre', () => {
  // Un model sense línia de base (cas degenerat): sense pendents, la feina d'aquí està feta.
  const e = estatDeLaPresa(payload({ n_preses: 1, pendents_base: 0, decidides_base: 0 }))
  assert.equal(e.estat, DECIDIDA)
})

test('un resum absent no peta i no menteix', () => {
  const e = estatDeLaPresa({ presa_oberta: true })
  assert.equal(e.estat, BUIDA)
  assert.deepEqual(e.talles, [])
})

// ── E3a · EL CINQUÈ ESTAT ───────────────────────────────────────────────────────────────────
// 🚨 El cor és `l'acta i el no-res NO poden donar el mateix estat`. La resta és contorn: aquell
// empat era l'arrel única dels tres símptomes de la QA de les 20:54.

test('🚨 l\'acta i el no-res NO poden donar el mateix estat', () => {
  assert.equal(estatDeLaPresa(acta({})).estat, TANCADA)
  assert.equal(estatDeLaPresa({ presa_oberta: false, presa_tancada: false }).estat, SENSE_PRESA)
})

test('TANCADA porta les dades de l\'acta: no és un buit amb un nom nou', () => {
  const e = estatDeLaPresa(acta({}))
  assert.equal(e.n_preses, 4)
  assert.equal(e.n_linies, 90)
  assert.deepEqual(e.talles, ['S', 'M'])
  assert.equal(e.session.id, 7)
  assert.equal(e.session.data, '2026-08-16')
  assert.equal(e.session.estat, 'Tancada')
})

test('🔑 CAP dels dos estats sense presa és escrivible — és d\'aquí que no en pot néixer un 409', () => {
  assert.equal(estatDeLaPresa(acta({})).escrivible, false)
  assert.equal(estatDeLaPresa(payload({}, false)).escrivible, false)
  assert.equal(estatDeLaPresa(null).escrivible, false)
})

test('els tres estats VIUS sí que són escrivibles', () => {
  assert.equal(estatDeLaPresa(payload({})).escrivible, true)                       // BUIDA
  assert.equal(estatDeLaPresa(payload({ n_preses: 3 })).escrivible, true)          // MESURANT
  assert.equal(estatDeLaPresa(payload({ n_preses: 3, pendents_base: 0 })).escrivible, true)
})

test('TANCADA es mira ABANS que el buit: totes dues tenen presa_oberta false', () => {
  // Si l'ordre s'invertís, el cinquè estat no sortiria mai i tornaria l'empat d'origen.
  const e = estatDeLaPresa({ presa_oberta: false, presa_tancada: true })
  assert.equal(e.estat, TANCADA)
})

test('un payload vell (sense presa_tancada) segueix llegint-se com sempre', () => {
  // El camp és additiu: cap consumidor ni cap resposta en caché canvia de veredicte.
  assert.equal(estatDeLaPresa({ presa_oberta: false }).estat, SENSE_PRESA)
  assert.equal(
    estatDeLaPresa({ presa_oberta: true, resum: { n_preses: 2, pendents_base: 1 } }).estat,
    MESURANT)
})
