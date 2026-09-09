import test from 'node:test'
import assert from 'node:assert/strict'

import { agrupaPerRonda, estatDeRonda, RONDA_ENTREGADA, RONDA_OBERTA } from './rondes.js'

// Les dues fonts d'aquesta pantalla arriben per portes diferents (`/dashboard/` les tasques,
// `/rondes/` les voltes) i poden anar desacompassades. El que aquests tests fixen és que
// `agrupaPerRonda` mai perdi una fila, passi el que passi amb la segona font.
// (v. DIAGNOSI_REACTIVITAT_FRONT.md §Q2.2)

const tasca = (id, ronda_seq, extra = {}) => ({
  id, ronda_seq, status: 'Pending', temps_consumit_min: 0, task_type_code: 'pom', ...extra,
})
const volta = (seq, extra = {}) => ({ id: seq * 10, seq, oberta_el: '2026-09-01T08:00:00Z', ...extra })

const totesLesFiles = (blocs) => blocs.flatMap(b => b.tasques.map(t => t.id)).sort((a, b) => a - b)

// ── agrupaPerRonda · cap fila es perd ──
  test('el cas normal: cada tasca al seu contenidor', () => {
    const blocs = agrupaPerRonda([tasca(1, 1), tasca(2, 2)], [volta(1), volta(2)])
    assert.deepEqual(blocs.map(b => b.clau), ['r1', 'r2'])
    assert.deepEqual(totesLesFiles(blocs), [1, 2])
  })

  test('ronda_seq null → bloc orfe (contracte de sempre, M1-bis · FIT-4)', () => {
    const blocs = agrupaPerRonda([tasca(1, 1), tasca(2, null)], [volta(1)])
    assert.deepEqual(blocs.map(b => b.clau), ['r1', 'orfe'])
    assert.deepEqual(blocs[1].tasques.map(t => t.id), [2])
  })

  // 🚨 EL DEFECTE D'EN SALVA · cas B — hi ha voltes, però la llista no porta la NOVA.
  // Abans d'aquest tram la tasca 2 no queia a `orfes` (el seu `ronda_seq` no és null) ni tenia
  // bloc (no hi ha volta amb seq 2): DESAPAREIXIA, amb 200 OK i sense cap senyal.
  test("volta desconeguda → orfe, MAI empassada", () => {
    const blocs = agrupaPerRonda([tasca(1, 1), tasca(2, 2)], [volta(1)])
    assert.deepEqual(totesLesFiles(blocs), [1, 2])
    assert.deepEqual(blocs.map(b => b.clau), ['r1', 'orfe'])
    assert.deepEqual(blocs[1].tasques.map(t => t.id), [2])
  })

  // 🚨 EL DEFECTE D'EN SALVA · cas A — la PRIMERA volta del model (`open-task` la fa néixer)
  // i la llista de voltes encara és buida.
  test('cap volta carregada → totes les files al bloc orfe', () => {
    const blocs = agrupaPerRonda([tasca(1, 1), tasca(2, 1)], [])
    assert.equal(blocs.length, 1)
    assert.equal(blocs[0].clau, 'orfe')
    assert.deepEqual(totesLesFiles(blocs), [1, 2])
  })

  test('voltes desconegudes MÚLTIPLES: ordre estable per seq, i cap duplicat', () => {
    const blocs = agrupaPerRonda([tasca(5, 3), tasca(4, 2), tasca(1, 1)], [volta(1)])
    assert.deepEqual(totesLesFiles(blocs), [1, 4, 5])
    // R2 abans que R3 dins del bloc orfe: l'ordre no pot ballar entre renders.
    assert.deepEqual(blocs[1].tasques.map(t => t.id), [4, 5])
  })

  test('orfes de debò i orfes per volta desconeguda comparteixen bloc, sense perdre'
     + " cap de les dues menes", () => {
    const blocs = agrupaPerRonda([tasca(1, null), tasca(2, 9)], [volta(1)])
    assert.deepEqual(blocs.map(b => b.clau), ['r1', 'orfe'])
    assert.deepEqual(totesLesFiles(blocs), [1, 2])
  })

  test('una volta sense tasques conserva el seu contenidor buit', () => {
    const blocs = agrupaPerRonda([], [volta(1)])
    assert.equal(blocs.length, 1)
    assert.equal(blocs[0].total, 0)
  })

  test('els agregats del bloc orfe es calculen sobre les seves files, no sobre zero', () => {
    const blocs = agrupaPerRonda(
      [tasca(1, 7, { status: 'Done', temps_consumit_min: 30 }), tasca(2, 7)], [])
    assert.equal(blocs[0].total, 2)
    assert.equal(blocs[0].fets, 1)
    assert.equal(blocs[0].pct, 50)
    assert.equal(blocs[0].minuts, 30)
  })

// ── estatDeRonda · no ha canviat ──
  test('entregada mana sobre tancada', () => {
    assert.equal(estatDeRonda({ entregada: true, tancada_el: 'x' }), RONDA_ENTREGADA)
  })
  test('sense tancar → oberta', () => {
    assert.equal(estatDeRonda({ entregada: false, tancada_el: null }), RONDA_OBERTA)
  })
