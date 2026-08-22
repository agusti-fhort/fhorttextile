import test from 'node:test'
import assert from 'node:assert/strict'

import {
  CARA_ALBARANADA, CARA_CAP, CARA_CONFLICTE, CARA_FETA, CARA_LLIURADA,
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

// S-19 (05/08) — L'AFIRMACIÓ GIRADA. Abans aquest cas obria el diàleg; ara no. Assignada a un
// altre sense rellotge corrent és feina PREVISTA, i agafar-la ha de ser sense fricció.
//
// 🚨 J (21/08) — EL FIXTURE D'AQUEST TEST DEIA UNA COSA QUE EL SEU PROPI TÍTOL NO DEIA. Passava
// l'`status` per defecte, que és `InProgress`, i per tant no provava «feina prevista» sinó
// **feina COMENÇADA per un altre amb el tram tancat** —una fuita, o el guard de tasca oblidada—,
// que és un cas ben diferent: el backend hi cau a la branca de handoff i s'enduia la tasca en
// silenci (`traspassa_tram` + `assignee`). S-19 no va decidir això mai; el fixture ho tapava.
//
// El cas de S-19 es prova ara amb els estats que S-19 descrivia (`Pending`/`Paused`), i el que
// el fixture provava sense voler té test propi, just a sota, amb el veredicte de J.
test('assignada a un altre i NO COMENÇADA → CAP modal (S-19: és feina prevista)', () => {
  for (const status of ['Pending', 'Paused']) {
    const t = tasca({ obert_per: null, assignee: ALTRE, status })
    assert.equal(caraObrirTasca(t, JO), CARA_CAP, status)
    assert.equal(obreSenseFriccio(t, JO), true, status)
  }
})

// ── J · R3 — ENTRAR NO ENDÚ ─────────────────────────────────────────────────
test('EN CURS d\'un altre sense tram obert → conflicte (una mirada no s\'endú la tasca)', () => {
  // `obert_per` surt del TRAM i aquí no n'hi ha cap: el guard de tasca oblidada l'ha tancat, o
  // ha fuit. La tasca segueix `InProgress` i d'un altre, i el backend, sense preguntar, feia
  // `traspassa_tram` + `assignee = jo`. Això no és pausar-la: és PRENDRE-LA.
  assert.equal(
    caraObrirTasca(tasca({ obert_per: null, assignee: ALTRE, status: 'InProgress' }), JO),
    CARA_CONFLICTE)
})

test('...però si el rellotge corre, encara que l\'assignee sigui JO, hi ha conflicte', () => {
  assert.equal(caraObrirTasca(tasca({ obert_per: ALTRE, assignee: JO }), JO), CARA_CONFLICTE)
})

test('el TRAM mana sobre l\'assignee: si el rellotge és meu, no hi ha conflicte', () => {
  // Assignada a un altre però qui hi treballa sóc jo (el cas real dels timers 116/117).
  assert.equal(caraObrirTasca(tasca({ obert_per: JO, assignee: ALTRE }), JO), CARA_CAP)
})

// ── CARA B · LLIURADA (RONDA) ────────────────────────────────────────────────
test('Done + lliurable → cara de ronda', () => {
  assert.equal(caraObrirTasca(tasca({ status: 'Done', es_lliurable: true }), JO), CARA_LLIURADA)
})

// 🚨 J (21/08) — AQUEST TEST AFIRMAVA EL FORAT. Deia «es reobre i prou», i «i prou» volia dir
// que entrar-hi A MIRAR la reobria: tram nou, rellotge reiniciat i una fila al log atribuint a
// algú una decisió de rectificar que no havia pres. Segueix sense merèixer el diàleg de RONDA
// —no és lliurable, no hi ha volta que obrir— però ara té cara pròpia, i el defecte és consultar.
test('Done però NO lliurable → cara FETA, no reobertura silenciosa', () => {
  assert.equal(caraObrirTasca(tasca({ status: 'Done', es_lliurable: false }), JO), CARA_FETA)
  assert.equal(obreSenseFriccio(tasca({ status: 'Done', es_lliurable: false }), JO), false)
})

test('lliurada mana sobre feta: si hi ha volta a obrir, la cara és la de ronda', () => {
  assert.equal(caraObrirTasca(tasca({ status: 'Done', es_lliurable: true }), JO), CARA_LLIURADA)
})

test('albaranada mana sobre feta', () => {
  assert.equal(
    caraObrirTasca(tasca({ albaranada: true, status: 'Done', es_lliurable: false }), JO),
    CARA_ALBARANADA)
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

// J · R3 — els dos codis nous. Van DAVANT del 409 genèric: sense això, una tasca feta hauria
// obert la cara de conflicte i hauria dit que hi ha algú altre treballant-hi, que és fals.
test('el 409 de tasca FETA dona la cara de feta, no la de conflicte', () => {
  assert.equal(caraDeError({ response: { status: 409, data: { code: 'tasca_feta' } } }), CARA_FETA)
})

test('el 409 de tasca d\'un altre dona conflicte', () => {
  assert.equal(caraDeError({ response: { status: 409, data: { code: 'tasca_dun_altre' } } }),
    CARA_CONFLICTE)
})

test('un error qualsevol no obre cap cara', () => {
  assert.equal(caraDeError({ response: { status: 500, data: {} } }), null)
  assert.equal(caraDeError(undefined), null)
})
