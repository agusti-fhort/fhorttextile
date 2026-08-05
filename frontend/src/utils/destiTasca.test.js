import test from 'node:test'
import assert from 'node:assert/strict'

import {
  GEST_DECLARAT, GEST_EINA, GEST_SENSE_EINA, GEST_SENSE_PANTALLA,
  clauSuperficie, destiDeTasca, esOferible, gestDeTasca, superficiesVives,
} from './destiTasca.js'

// Files reals del catàleg (dump de T0.1, idèntic als dos tenants).
const CATALEG = {
  design_review: { code: 'design_review', tipus: 'Externa-lliure', eina: null, mode: null },
  design_clarify: { code: 'design_clarify', tipus: 'Externa-lliure', eina: null, mode: null },
  pattern_digit: { code: 'pattern_digit', tipus: 'Interna', eina: 'patro', mode: 'digitalitzar' },
  pattern_cad: { code: 'pattern_cad', tipus: 'Interna', eina: 'patro', mode: 'disseny_base' },
  pattern_hand: { code: 'pattern_hand', tipus: 'Externa-lliure', eina: null, mode: null },
  pom: { code: 'pom', tipus: 'Interna', eina: 'mesures', mode: 'autoria_base' },
  size_check: { code: 'size_check', tipus: 'Interna', eina: 'mesures', mode: 'presa' },
  grading: { code: 'grading', tipus: 'Interna', eina: 'escalat', mode: 'propagacio' },
  sample_check: { code: 'sample_check', tipus: 'Interna', eina: 'escalat', mode: 'presa' },
  tech_sheet: { code: 'tech_sheet', tipus: 'Interna', eina: 'fitxa', mode: 'document' },
  pattern_review: { code: 'pattern_review', tipus: 'Interna', eina: 'patro', mode: 'revisio' },
  bom: { code: 'bom', tipus: 'Interna', eina: 'fitxa', mode: 'bom', visible: false },
  scaling: { code: 'scaling', tipus: 'Interna', eina: 'patro', mode: 'escalat' },
  marking: { code: 'marking', tipus: 'Interna', eina: 'patro', mode: 'marcada' },
  audit: { code: 'audit', tipus: 'Externa-lliure', eina: null, mode: null, visible: false },
}

const CTX = { modelId: 188, taskId: 4321 }

// ── LES SIS QUE TENEN PANTALLA ───────────────────────────────────────────────
test('les sis internes amb pantalla hi porten, i amb el task_id a sobre', () => {
  const esperat = {
    pom: '/models/188?tab=Mesures&mode=entry',
    size_check: '/models/188?tab=Mesures&task_id=4321',
    grading: '/models/188/escalat?task_id=4321',
    tech_sheet: '/models/188/fitxa?task_id=4321',
    pattern_digit: '/models/188/patro/taller?task_id=4321',
    pattern_cad: '/models/188/patro/taller?task_id=4321',
  }
  for (const [code, route] of Object.entries(esperat)) {
    assert.equal(gestDeTasca(CATALEG[code]), GEST_EINA, code)
    assert.equal(destiDeTasca(CATALEG[code], CTX).route, route, code)
  }
})

test('només Mesures commuta de tab: la resta són rutes pròpies', () => {
  assert.equal(destiDeTasca(CATALEG.pom, CTX).tab, 'Mesures')
  assert.equal(destiDeTasca(CATALEG.size_check, CTX).tab, 'Mesures')
  assert.equal(destiDeTasca(CATALEG.grading, CTX).tab, undefined)
})

test('la definició de POM no arrossega task_id: la gènesi no en porta', () => {
  assert.ok(!destiDeTasca(CATALEG.pom, CTX).route.includes('task_id'))
})

// ── LES QUE NO EN TENEN: HO DIUEN, NO S'HO INVENTEN ──────────────────────────
test('interna amb eina i mode sense pantalla no navega enlloc', () => {
  for (const code of ['pattern_review', 'scaling', 'marking', 'sample_check', 'bom']) {
    assert.equal(gestDeTasca(CATALEG[code]), GEST_SENSE_PANTALLA, code)
    assert.equal(destiDeTasca(CATALEG[code], CTX), null, code)
  }
})

test('«patro» no és un salconduit: el mode mana sobre l\'eina', () => {
  // Tres tipus amb la MATEIXA eina que pattern_cad, i cap no va al Taller.
  assert.equal(gestDeTasca(CATALEG.pattern_cad), GEST_EINA)
  assert.equal(gestDeTasca(CATALEG.pattern_review), GEST_SENSE_PANTALLA)
  assert.equal(gestDeTasca(CATALEG.scaling), GEST_SENSE_PANTALLA)
  assert.equal(gestDeTasca(CATALEG.marking), GEST_SENSE_PANTALLA)
})

test('interna sense eina: transport manual, mai un destí arbitrari', () => {
  const tt = { code: 'qa', tipus: 'Interna', eina: null, mode: null }
  assert.equal(gestDeTasca(tt), GEST_SENSE_EINA)
  assert.equal(destiDeTasca(tt, CTX), null)
})

// ── LES EXTERNES ─────────────────────────────────────────────────────────────
test('les quatre externes són temps declarat i no naveguen', () => {
  for (const code of ['design_review', 'design_clarify', 'pattern_hand', 'audit']) {
    assert.equal(gestDeTasca(CATALEG[code]), GEST_DECLARAT, code)
    assert.equal(destiDeTasca(CATALEG[code], CTX), null, code)
  }
})

test('una externa amb eina seguiria sent temps declarat: `tipus` mana', () => {
  assert.equal(gestDeTasca({ tipus: 'Externa-lliure', eina: 'mesures', mode: 'presa' }),
    GEST_DECLARAT)
})

// ── QUÈ S'OFEREIX ────────────────────────────────────────────────────────────
test('invisible no s\'ofereix; inactiu tampoc; i la resta sí', () => {
  assert.equal(esOferible(CATALEG.bom), false)
  assert.equal(esOferible(CATALEG.audit), false)
  assert.equal(esOferible({ code: 'x', active: false }), false)
  assert.equal(esOferible(CATALEG.pom), true)
})

test('un catàleg que no porti `visible` es llegeix com a oferible', () => {
  assert.equal(esOferible({ code: 'antic', tipus: 'Interna' }), true)
})

test('les 13 targetes oferibles del catàleg real', () => {
  const oferibles = Object.values(CATALEG).filter(esOferible).map(tt => tt.code)
  assert.equal(oferibles.length, 13)
  assert.ok(!oferibles.includes('bom'))
  assert.ok(!oferibles.includes('audit'))
})

// ── HIGIENE ──────────────────────────────────────────────────────────────────
test('la clau és eina/mode, i sense mode no hi ha clau', () => {
  assert.equal(clauSuperficie(CATALEG.grading), 'escalat/propagacio')
  assert.equal(clauSuperficie({ eina: 'patro', mode: null }), null)
  assert.equal(clauSuperficie(null), null)
})

test('cap superfície viva sense el seu parell complet', () => {
  for (const clau of superficiesVives()) {
    const [eina, mode] = clau.split('/')
    assert.ok(eina && mode, clau)
  }
})
