import test from 'node:test'
import assert from 'node:assert/strict'

import {
  CARA_ALBARANADA, CARA_CAP, CARA_CONFLICTE, CARA_LLIURADA,
  caraDeError, caraObrirTasca, obreSenseFriccio,
} from './caraObrirTasca.js'

// Fila de `ModelTaskSerializer` amb el cas normal per defecte: meva, viva, neta.
const tasca = (extra = {}) => ({
  id: 1, status: 'InProgress', assignee: 7, obert_per: 7,
  albaranada: false, es_lliurable: false, ...extra,
})
const JO = 7
const ALTRE = 9

// ── LA REGLA D'OR ────────────────────────────────────────────────────────────
test('el cas normal no obre cap modal', () => {
  assert.equal(caraObrirTasca(tasca(), JO), CARA_CAP)
  assert.equal(obreSenseFriccio(tasca(), JO), true)
})

test('una tasca de ningú i sense rellotge tampoc obre modal', () => {
  assert.equal(caraObrirTasca(tasca({ assignee: null, obert_per: null, status: 'Pending' }), JO),
    CARA_CAP)
})

test('la meva tasca pausada tampoc obre modal', () => {
  assert.equal(caraObrirTasca(tasca({ status: 'Paused', obert_per: null }), JO), CARA_CAP)
})

test('sense tasca no hi ha modal (open-task la crearà)', () => {
  assert.equal(caraObrirTasca(null, JO), CARA_CAP)
})

// ── CARA A · CONFLICTE (D-7) ─────────────────────────────────────────────────
test('algú altre hi té el rellotge corrent → conflicte', () => {
  assert.equal(caraObrirTasca(tasca({ obert_per: ALTRE, assignee: ALTRE }), JO), CARA_CONFLICTE)
})

test('assignada a un altre encara que ningú hi treballi → conflicte', () => {
  assert.equal(caraObrirTasca(tasca({ obert_per: null, assignee: ALTRE }), JO), CARA_CONFLICTE)
})

test('el TRAM mana sobre l\'assignee: si el rellotge és meu, no hi ha conflicte', () => {
  // Assignada a un altre però qui hi treballa sóc jo (el cas real dels timers 116/117).
  assert.equal(caraObrirTasca(tasca({ obert_per: JO, assignee: ALTRE }), JO), CARA_CAP)
})

// ── CARA B · LLIURADA (RONDA) ────────────────────────────────────────────────
test('Done + lliurable → cara de ronda', () => {
  assert.equal(caraObrirTasca(tasca({ status: 'Done', es_lliurable: true }), JO), CARA_LLIURADA)
})

test('Done però NO lliurable no mereix el diàleg de ronda', () => {
  // És una rectificació de sempre: es reobre i prou.
  assert.equal(caraObrirTasca(tasca({ status: 'Done', es_lliurable: false }), JO), CARA_CAP)
})

// ── CARA C · ALBARANADA (D-5) ────────────────────────────────────────────────
test('albaranada → cara d\'albarà', () => {
  assert.equal(caraObrirTasca(tasca({ albaranada: true }), JO), CARA_ALBARANADA)
})

test('albaranada mana sobre lliurada', () => {
  assert.equal(
    caraObrirTasca(tasca({ albaranada: true, status: 'Done', es_lliurable: true }), JO),
    CARA_ALBARANADA)
})

test('albaranada mana sobre conflicte', () => {
  // Oferir «treballar-hi jo» seria oferir una porta que el backend tancarà amb un 409.
  assert.equal(caraObrirTasca(tasca({ albaranada: true, obert_per: ALTRE }), JO), CARA_ALBARANADA)
})

// ── El fallback per error (estat precalculat ranci) ──────────────────────────
test('el 409 amb codi d\'albarà dona la cara d\'albarà', () => {
  assert.equal(caraDeError({ response: { status: 409, data: { code: 'tasca_albaranada' } } }),
    CARA_ALBARANADA)
})

test('un 409 sense codi és conflicte', () => {
  assert.equal(caraDeError({ response: { status: 409, data: {} } }), CARA_CONFLICTE)
})

test('un error qualsevol no obre cap cara', () => {
  assert.equal(caraDeError({ response: { status: 500, data: {} } }), null)
  assert.equal(caraDeError(undefined), null)
})
