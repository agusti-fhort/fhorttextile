// FIX-4 (DIAGNOSI_MESURES_TEA_205) — la guarda de plausibilitat pregunta on toca i calla on toca.
//     cd frontend && node --test src/utils/plausibilitatMesura.test.js
//
// EL CAS REAL: model 205 «TEA», POM B amb base 46 cm i un `1` escrit a les cel·les XXS i XS
// (era l'increment de la regla, no una llargada). El brief cita també la forma 1.0 sobre base
// 32: totes dues han de preguntar. I el cas normal —46 sobre base 46, ±3— no ha de dir res.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  LLINDAR_DELTA, LLINDAR_MESURA, deltaSemblaMesura, mesuraSemblaIncrement,
} from './plausibilitatMesura.js'

test('el cas TEA: un 1 escrit a una cel·la de talla pregunta', () => {
  assert.equal(mesuraSemblaIncrement(1.0, 32), true)   // la forma citada al brief
  assert.equal(mesuraSemblaIncrement(1.0, 46), true)   // la fila B real del 205
  assert.equal(mesuraSemblaIncrement('1', '46'), true) // el valor arriba com a text de l'input
})

test('els valors normals no diuen res', () => {
  for (const v of [46, 43, 49, 45.5, '46,5']) {
    assert.equal(mesuraSemblaIncrement(v, 46), false, `${v} sobre base 46 no hauria de preguntar`)
  }
})

test('la frontera del 40% és exacta i NO pregunta quan hi cau just', () => {
  // base 50 → banda [30, 70]. 30 i 70 hi són a dins; 29.9 i 70.1 no.
  assert.equal(mesuraSemblaIncrement(30, 50), false)
  assert.equal(mesuraSemblaIncrement(70, 50), false)
  assert.equal(mesuraSemblaIncrement(29.9, 50), true)
  assert.equal(mesuraSemblaIncrement(70.1, 50), true)
  assert.equal(LLINDAR_MESURA, 0.40)
})

test('les peces petites legítimes no queden bloquejades: només se les pregunta', () => {
  // Una trabeta de 2 cm amb base 2: cap pregunta. La guarda no inventa sospites.
  assert.equal(mesuraSemblaIncrement(2, 2), false)
  // I quan sí que pregunta, és una pregunta — el «sí» el resol la capa d'UI, no aquesta funció.
  assert.equal(mesuraSemblaIncrement(1, 2), true)
})

test('el camp Δ pregunta quan sembla una mesura', () => {
  assert.equal(deltaSemblaMesura(46, 46), true)     // hi ha escrit la mesura sencera
  assert.equal(deltaSemblaMesura(10, 46), true)     // 10 > 9.2
  assert.equal(deltaSemblaMesura(1, 46), false)     // el delta real del POM B
  assert.equal(deltaSemblaMesura(1.5, 46), false)
  assert.equal(LLINDAR_DELTA, 0.20)
})

test('un delta negatiu es jutja per magnitud', () => {
  assert.equal(deltaSemblaMesura(-1, 46), false)
  assert.equal(deltaSemblaMesura(-20, 46), true)
})

test('sense base no es pregunta res (millor callar que acusar a cegues)', () => {
  for (const b of [null, undefined, '', 0, 'ampla']) {
    assert.equal(mesuraSemblaIncrement(1, b), false, `base ${b}`)
    assert.equal(deltaSemblaMesura(99, b), false, `base ${b}`)
  }
})

test('sense valor tampoc: esborrar una cel·la no és sospitós', () => {
  for (const v of [null, undefined, '', 'x']) {
    assert.equal(mesuraSemblaIncrement(v, 46), false, `valor ${v}`)
    assert.equal(deltaSemblaMesura(v, 46), false, `valor ${v}`)
  }
})
