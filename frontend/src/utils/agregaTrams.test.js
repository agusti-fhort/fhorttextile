import test from 'node:test'
import assert from 'node:assert/strict'

import {
  MAX_MINUTS_TRAM, darrersDies, diaDelTram, formataMinuts, horaLocal, minutsDelTram,
  tramObert, tramsDelDia,
} from './agregaTrams.js'

// Trams tal com el servidor els emet DE DEBÒ: inici/fi/minuts/actiu/origen.
const tram = (extra = {}) => ({
  id: 1, inici: '2026-08-05T09:00:00Z', fi: '2026-08-05T10:00:00Z',
  minuts: 60, actiu: false, origen: 'mesurat', ...extra,
})

// ── El bug de §S-3, com a test ───────────────────────────────────────────────
test('un tram amb els camps REALS no es perd', () => {
  // El codi vell llegia `data_inici`/`created_at`: `''` no és mai una data i la llista sortia
  // buida sempre. Si algú torna a llegir camps inexistents, aquest test cau.
  assert.notEqual(diaDelTram(tram()), null)
  assert.equal(minutsDelTram(tram()), 60)
})

test('els camps INVENTATS no serveixen de res', () => {
  assert.equal(diaDelTram({ data_inici: '2026-08-05T09:00:00Z' }), null)
  assert.equal(minutsDelTram({ data_inici: '2026-08-05T09:00:00Z', data_fi: null }), 0)
})

// ── minuts ───────────────────────────────────────────────────────────────────
test('`minuts` del servidor mana quan hi és', () => {
  // No es recalcula: el servidor l'ha fet amb floor(segons/60) i és el que va a l'albarà.
  assert.equal(minutsDelTram(tram({ minuts: 57 })), 57)
})

test('sense `minuts`, es calcula de la franja', () => {
  assert.equal(minutsDelTram(tram({ minuts: null })), 60)
})

test('un tram OBERT compta el que porta corregut', () => {
  const ara = new Date('2026-08-05T09:45:00Z').getTime()
  assert.equal(minutsDelTram(tram({ fi: null, minuts: null }), ara), 45)
})

test('els trams desbocats no es compten (mateix sostre que el backend)', () => {
  assert.equal(minutsDelTram(tram({ minuts: MAX_MINUTS_TRAM })), MAX_MINUTS_TRAM)
  assert.equal(minutsDelTram(tram({ minuts: MAX_MINUTS_TRAM + 1 })), 0)
})

test('un tram sense inici val zero i no peta', () => {
  assert.equal(minutsDelTram(null), 0)
  assert.equal(minutsDelTram({}), 0)
})

// ── el tram obert ────────────────────────────────────────────────────────────
test('el tram obert és el que no té fi', () => {
  const obert = tram({ id: 2, fi: null, minuts: null, actiu: true })
  assert.equal(tramObert([tram(), obert])?.id, 2)
})

test('sense cap obert retorna null', () => {
  assert.equal(tramObert([tram(), tram({ id: 3 })]), null)
  assert.equal(tramObert([]), null)
  assert.equal(tramObert(undefined), null)
})

// ── el dia ───────────────────────────────────────────────────────────────────
test('els trams del dia són els TANCATS, ordenats per hora', () => {
  const dia = diaDelTram(tram())
  const tard = tram({ id: 9, inici: '2026-08-05T16:00:00Z', fi: '2026-08-05T17:00:00Z' })
  const obert = tram({ id: 8, fi: null, minuts: null })
  const r = tramsDelDia([tard, obert, tram()], dia)
  assert.deepEqual(r.map(x => x.id), [1, 9])
})

// ── la setmana ───────────────────────────────────────────────────────────────
test('darrersDies retorna n dies del més antic al més recent', () => {
  const avui = new Date(2026, 7, 5)
  const d = darrersDies([], 7, avui)
  assert.equal(d.length, 7)
  assert.equal(d[6].clau, '2026-08-05')
  assert.equal(d[0].clau, '2026-07-30')
  assert.equal(d.every(x => x.minuts === 0), true)
})

test('els minuts s\'acumulen al dia del seu INICI', () => {
  const avui = new Date(2026, 7, 5)
  const t1 = { id: 1, inici: new Date(2026, 7, 5, 9).toISOString(), fi: new Date(2026, 7, 5, 10).toISOString(), minuts: 60 }
  const t2 = { id: 2, inici: new Date(2026, 7, 5, 11).toISOString(), fi: new Date(2026, 7, 5, 11, 30).toISOString(), minuts: 30 }
  const t3 = { id: 3, inici: new Date(2026, 7, 3, 9).toISOString(), fi: new Date(2026, 7, 3, 10).toISOString(), minuts: 45 }
  const d = darrersDies([t1, t2, t3], 7, avui)
  assert.equal(d.find(x => x.clau === '2026-08-05').minuts, 90)
  assert.equal(d.find(x => x.clau === '2026-08-03').minuts, 45)
})

// ── format ───────────────────────────────────────────────────────────────────
test('el format és hores i minuts, mai segons', () => {
  assert.equal(formataMinuts(0), '0m')
  assert.equal(formataMinuts(59), '59m')
  assert.equal(formataMinuts(60), '1h 00m')
  assert.equal(formataMinuts(725), '12h 05m')
  assert.equal(formataMinuts(null), '0m')
})

test('l\'hora es llegeix en local i el buit no ensenya NaN', () => {
  assert.match(horaLocal('2026-08-05T09:30:00Z'), /^\d{2}:\d{2}$/)
  assert.equal(horaLocal(null), '—')
  assert.equal(horaLocal('escombraries'), '—')
})
