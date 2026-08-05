import test from 'node:test'
import assert from 'node:assert/strict'

import {
  MAX_MINUTS, MODE_DURADA, MODE_FRANJA, admetTempsDeclarat, validaTempsDeclarat,
} from './tempsDeclarat.js'

const ARA = new Date('2026-08-05T18:00:00Z').getTime()

// ── El XOR de modalitats ─────────────────────────────────────────────────────
test('mode desconegut es rebutja', () => {
  assert.deepEqual(validaTempsDeclarat({ mode: 'altre' }, ARA),
    { ok: false, error: 'temps_declarat.err_mode' })
})

// ── DURADA ───────────────────────────────────────────────────────────────────
test('una durada vàlida construeix {minuts}', () => {
  assert.deepEqual(validaTempsDeclarat({ mode: MODE_DURADA, minuts: '90' }, ARA),
    { ok: true, cos: { minuts: 90 } })
})

test('durada buida o no numèrica', () => {
  assert.equal(validaTempsDeclarat({ mode: MODE_DURADA, minuts: '' }, ARA).error,
    'temps_declarat.err_minuts')
  assert.equal(validaTempsDeclarat({ mode: MODE_DURADA, minuts: 'nou' }, ARA).error,
    'temps_declarat.err_minuts')
})

test('els minuts són enters: 90,5 no és una durada', () => {
  assert.equal(validaTempsDeclarat({ mode: MODE_DURADA, minuts: '90.5' }, ARA).error,
    'temps_declarat.err_enter')
})

test('zero i negatius es rebutgen', () => {
  assert.equal(validaTempsDeclarat({ mode: MODE_DURADA, minuts: '0' }, ARA).error,
    'temps_declarat.err_zero')
  assert.equal(validaTempsDeclarat({ mode: MODE_DURADA, minuts: '-30' }, ARA).error,
    'temps_declarat.err_zero')
})

test('el sostre és el mateix que el del backend (24 h)', () => {
  assert.equal(validaTempsDeclarat({ mode: MODE_DURADA, minuts: String(MAX_MINUTS) }, ARA).ok, true)
  assert.equal(validaTempsDeclarat({ mode: MODE_DURADA, minuts: String(MAX_MINUTS + 1) }, ARA).error,
    'temps_declarat.err_sostre')
})

// ── FRANJA ───────────────────────────────────────────────────────────────────
test('una franja vàlida construeix {inici, fi} en ISO', () => {
  const r = validaTempsDeclarat({
    mode: MODE_FRANJA, inici: '2026-08-05T09:00:00Z', fi: '2026-08-05T10:30:00Z',
  }, ARA)
  assert.equal(r.ok, true)
  assert.equal(r.cos.inici, '2026-08-05T09:00:00.000Z')
  assert.equal(r.cos.fi, '2026-08-05T10:30:00.000Z')
  assert.equal(r.cos.minuts, undefined, 'la franja no envia minuts: el XOR és del backend també')
})

test('franja incompleta', () => {
  assert.equal(validaTempsDeclarat({ mode: MODE_FRANJA, inici: '2026-08-05T09:00:00Z' }, ARA).error,
    'temps_declarat.err_franja_incompleta')
})

test('franja invertida', () => {
  assert.equal(validaTempsDeclarat({
    mode: MODE_FRANJA, inici: '2026-08-05T10:00:00Z', fi: '2026-08-05T09:00:00Z',
  }, ARA).error, 'temps_declarat.err_invertida')
})

test('franja de durada nul·la', () => {
  assert.equal(validaTempsDeclarat({
    mode: MODE_FRANJA, inici: '2026-08-05T09:00:00Z', fi: '2026-08-05T09:00:00Z',
  }, ARA).error, 'temps_declarat.err_invertida')
})

test('franja per sobre del sostre', () => {
  assert.equal(validaTempsDeclarat({
    mode: MODE_FRANJA, inici: '2026-08-01T09:00:00Z', fi: '2026-08-03T09:00:00Z',
  }, ARA).error, 'temps_declarat.err_sostre')
})

test('declarar feina del FUTUR no és declarar', () => {
  assert.equal(validaTempsDeclarat({
    mode: MODE_FRANJA, inici: '2026-08-05T19:00:00Z', fi: '2026-08-05T20:00:00Z',
  }, ARA).error, 'temps_declarat.err_futur')
})

test('dates escombraries', () => {
  assert.equal(validaTempsDeclarat({ mode: MODE_FRANJA, inici: 'ahir', fi: 'avui' }, ARA).error,
    'temps_declarat.err_data')
})

// ── Qui admet el formulari ───────────────────────────────────────────────────
test('només les tasques externes admeten temps declarat', () => {
  assert.equal(admetTempsDeclarat({ tipus_extern: true }), true)
  assert.equal(admetTempsDeclarat({ tipus_extern: false }), false)
  assert.equal(admetTempsDeclarat(null), false)
})
