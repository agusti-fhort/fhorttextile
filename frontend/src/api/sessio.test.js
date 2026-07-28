// K4 — la lògica que es pot provar sense navegador: el MUTEX del refresh i el helper de
// missatges. La resta (interceptor axios, authFetch sobre un fetch real, el modal) va a
// QA manual, anotat al report.
//
// El projecte no té harness de test de frontend (ni vitest ni jest): aquests van amb el
// runner natiu de Node, que ja llegeix ESM perquè el package és "type": "module".
//     cd frontend && node --test src/api/sessio.test.js
//
// LA LLEI QUE DEFENSEN: un sol refresh per a tota l'app. Amb ROTATE_REFRESH_TOKENS=True
// (settings.py:228) dos refreshos concurrents roten el token i el segon es queda amb un
// refresh que el primer acaba de substituir → expulsió amb la sessió encara vàlida.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { creaGestorSessio } from './sessioCore.js'
import { esTokenCaducat, missatgeError } from './errorsAuth.js'

// Un gestor de joguina amb comptadors, per veure QUANTES vegades s'ha demanat el refresh.
function fesGestor({ refresh = 'r0', falla = false } = {}) {
  const n = { demanats: 0, desats: 0, tancaments: 0 }
  let resol, rebutja
  const gestor = creaGestorSessio({
    llegeixRefresh: () => refresh,
    desaTokens: () => { n.desats += 1 },
    demanaRefresh: () => {
      n.demanats += 1
      return new Promise((res, rej) => {
        resol = () => res({ access: 'access-nou', refresh: 'refresh-nou' })
        rebutja = () => rej(new Error('refresh mort'))
        if (falla) rej(new Error('refresh mort'))
      })
    },
    tancaSessio: () => { n.tancaments += 1 },
  })
  return { gestor, n, resol: () => resol(), rebutja: () => rebutja() }
}

test('N crides concurrents comparteixen UN sol refresh', async () => {
  const { gestor, n, resol } = fesGestor()

  // 11 XHR que fallen alhora (la ràfega real mesurada a §B2.4 de la diagnosi).
  const totes = Array.from({ length: 11 }, () => gestor.refresca())
  assert.equal(n.demanats, 1, 'onze 401 no poden fer onze refreshos')

  resol()
  const tokens = await Promise.all(totes)
  assert.deepEqual(new Set(tokens), new Set(['access-nou']), 'totes reben el MATEIX token nou')
  assert.equal(n.desats, 1, 'el token es desa un sol cop')
})

test('el mutex s\'allibera: un refresh posterior sí que en dispara un de nou', async () => {
  const { gestor, n, resol } = fesGestor()
  const primera = gestor.refresca()
  assert.equal(gestor.enMarxa, true)
  resol()
  await primera
  assert.equal(gestor.enMarxa, false, 'el mutex no pot quedar-se encallat')

  gestor.refresca()
  assert.equal(n.demanats, 2, 'passat el primer, un 401 nou ha de poder refrescar')
})

test('refresh mort → tanca sessió UN cop, encara que hi hagi N esperant', async () => {
  const { gestor, n } = fesGestor({ falla: true })

  const totes = Array.from({ length: 5 }, () => gestor.refresca())
  await Promise.allSettled(totes)

  assert.equal(n.demanats, 1)
  assert.equal(n.tancaments, 1, 'cinc peticions no poden provocar cinc redireccions a login')
  for (const p of totes) await assert.rejects(p, /refresh mort/)
})

test('sense refresh token no s\'inventa cap crida: tanca i prou', async () => {
  const { gestor, n } = fesGestor({ refresh: null })
  await assert.rejects(gestor.refresca(), /no hi ha refresh token/)
  assert.equal(n.demanats, 0)
  assert.equal(n.tancaments, 1)
})

test('un refresh fallit no deixa el mutex encallat', async () => {
  const { gestor, n, rebutja } = fesGestor()
  const primera = gestor.refresca()
  rebutja()
  await assert.rejects(primera)
  assert.equal(gestor.enMarxa, false)

  gestor.refresca()
  assert.equal(n.demanats, 2, 'després d\'un fracàs, la sessió següent ha de poder tornar a provar')
})

// ── El helper de missatges (K3) ─────────────────────────────────────────────────────────

// El cos EXACTE de la captura de PROD del 28/07 07:53.
const COS_DE_LA_CAPTURA = {
  detail: 'Given token not valid for any token type',
  code: 'token_not_valid',
  messages: [{ token_class: 'AccessToken', token_type: 'access', message: 'Token is expired' }],
}

const t = clau => (clau === 'auth.session_expired' ? 'La sessió ha caducat. Torna a entrar.' : clau)

test('el cos de la captura es reconeix com a token caducat', () => {
  assert.equal(esTokenCaducat(COS_DE_LA_CAPTURA), true)
})

test('un 401 de permisos NO és token caducat (no s\'ha de refrescar ni expulsar)', () => {
  assert.equal(esTokenCaducat({ detail: 'No tens permís per fer això.' }), false)
  assert.equal(esTokenCaducat(null), false)
  assert.equal(esTokenCaducat('text pla'), false)
  assert.equal(esTokenCaducat(undefined), false)
})

test('el banner no pinta mai el JSON cru per al cas conegut', () => {
  const msg = missatgeError(COS_DE_LA_CAPTURA, t)
  assert.equal(msg, 'La sessió ha caducat. Torna a entrar.')
  assert.ok(!msg.includes('token_not_valid'), 'ni rastre del codi intern')
  assert.ok(!msg.includes('{'), 'ni rastre del JSON')
})

test('els errors NO reconeguts es deixen exactament com estaven', () => {
  const altre = { camp: ['Aquest camp és obligatori.'] }
  assert.equal(missatgeError(altre, t), JSON.stringify(altre))
})
