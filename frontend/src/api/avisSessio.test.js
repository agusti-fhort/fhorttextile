// K5 — la lògica de temporització de l'avís de sessió, i la lectura de l'`exp` del JWT.
//     cd frontend && node --test src/api/avisSessio.test.js
//
// El que NO es prova aquí (va a QA manual, anotat al report): el modal com a component, el
// sondeig sobre un `document.visibilityState` real i el refresh contra el servidor.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  calAvisar, ESTAT_AVIS, ESTAT_CADUCADA, ESTAT_VIVA, estatSessio, MARGE_AVIS_MS,
} from './avisSessio.js'
import { llegeixExpMs, llegeixPayload } from './jwt.js'

const ARA = 1_800_000_000_000   // instant fix: cap test depèn del rellotge real
const MIN = 60 * 1000

// ── Estat de la sessió ──────────────────────────────────────────────────────────────────

test('amb temps de sobres, la sessió és viva i no es diu res', () => {
  assert.equal(estatSessio(ARA + 3 * 24 * 60 * MIN, ARA), ESTAT_VIVA)
  assert.equal(estatSessio(ARA + 6 * MIN, ARA), ESTAT_VIVA, 'a 6 min encara no toca')
})

test('dins dels últims 5 minuts, toca avisar', () => {
  assert.equal(estatSessio(ARA + 5 * MIN, ARA), ESTAT_AVIS, 'el llindar és inclusiu')
  assert.equal(estatSessio(ARA + 1 * MIN, ARA), ESTAT_AVIS)
  assert.equal(estatSessio(ARA + 1, ARA), ESTAT_AVIS)
})

test('passat l\'instant, és caducada (i el modal ja no hi pinta res: mana K1)', () => {
  assert.equal(estatSessio(ARA, ARA), ESTAT_CADUCADA)
  assert.equal(estatSessio(ARA - MIN, ARA), ESTAT_CADUCADA)
})

test('sense exp llegible no s\'inventa cap avís', () => {
  for (const dolent of [null, undefined, NaN, Infinity, 'demà', {}]) {
    assert.equal(estatSessio(dolent, ARA), ESTAT_VIVA)
  }
})

// ── Un modal per cicle ──────────────────────────────────────────────────────────────────

test('el modal no es repeteix en bucle per al mateix cicle', () => {
  const exp = ARA + 2 * MIN
  assert.equal(calAvisar(exp, ARA, null), true, 'el primer cop, sí')
  assert.equal(calAvisar(exp, ARA, exp), false, 'ja preguntat: mai més per a aquest exp')
  // Encara que passin els ticks següents dins de la mateixa finestra.
  assert.equal(calAvisar(exp, ARA + 30 * 1000, exp), false)
  assert.equal(calAvisar(exp, ARA + 60 * 1000, exp), false)
})

test('«Continua treballant» arma el cicle SEGÜENT, no el silencia per sempre', () => {
  const expVell = ARA + 2 * MIN
  // El refresh rota el token: exp nou 7 dies més enllà (ROTATE_REFRESH_TOKENS + set_exp()).
  const expNou = ARA + 7 * 24 * 60 * MIN
  assert.equal(calAvisar(expNou, ARA, expVell), false, 'de moment queda molt temps')
  // I quan aquell cicle arribi al seu final, torna a avisar.
  const araTard = expNou - 2 * MIN
  assert.equal(calAvisar(expNou, araTard, expVell), true)
})

test('fora de la finestra no s\'avisa encara que no s\'hagi vist mai', () => {
  assert.equal(calAvisar(ARA + 60 * MIN, ARA, null), false)
  assert.equal(calAvisar(ARA - MIN, ARA, null), false, 'ja caducada: no és feina del modal')
})

test('el marge és de 5 minuts', () => {
  assert.equal(MARGE_AVIS_MS, 5 * 60 * 1000)
})

// ── Lectura de l'exp del JWT ────────────────────────────────────────────────────────────

/** Un JWT de mentida amb el payload demanat (la signatura no es mira: no la validem). */
function fesJwt(payload) {
  const b64 = obj => Buffer.from(JSON.stringify(obj)).toString('base64')
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  return `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64(payload)}.signatura-falsa`
}

test('llegeix l\'exp del refresh token en mil·lisegons', () => {
  const exp = Math.floor(ARA / 1000) + 7 * 24 * 3600
  assert.equal(llegeixExpMs(fesJwt({ exp, token_type: 'refresh' })), exp * 1000)
})

test('un payload amb accents es llegeix bé (UTF-8, no latin-1)', () => {
  const p = llegeixPayload(fesJwt({ exp: 1, nom: 'Àngel Muñoz · Escalatge' }))
  assert.equal(p.nom, 'Àngel Muñoz · Escalatge')
})

test('un token il·legible no llança mai: retorna null', () => {
  for (const dolent of [null, undefined, 42, '', 'no-és-un-jwt', 'a.b', 'a.b.c.d', 'a.@@@.c']) {
    assert.equal(llegeixExpMs(dolent), null)
  }
})

test('un JWT sense exp retorna null (i llavors no s\'avisa)', () => {
  assert.equal(llegeixExpMs(fesJwt({ token_type: 'refresh' })), null)
  assert.equal(estatSessio(llegeixExpMs(fesJwt({})), ARA), ESTAT_VIVA)
})
