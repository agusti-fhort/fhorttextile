// EL BANC DE LES FILES DE PRESA — S42/G8.
//
//     node --test frontend/src/utils/filesDePresa.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { construeixFilesDePresa } from './filesDePresa.js'

// Dues files de `base-stages` amb TOTS els camps que l'adaptador ha de saber traslladar.
const BASE = [
  {
    base_measurement_id: 3344, pom_id: 962, pom_code: 'G1', capa: 'exterior', instancia: '',
    garment: '', nom_fitxa: 'G1', nom_en: 'Gusset', nom_ca: 'Escaire',
    nom_canonic_model: 'GUSSET', nom_traduit_model: 'Escaire', is_key: true, base_value_cm: 0.5,
  },
  {
    base_measurement_id: 3350, pom_id: 954, pom_code: 'FD', capa: 'exterior', instancia: '',
    garment: '02', nom_fitxa: 'FR', nom_en: 'Front rise', nom_ca: 'Tir davanter',
    nom_canonic_model: '', nom_traduit_model: '', is_key: false, base_value_cm: 18.5,
  },
]
const LINIES = [{ id: 771, base_measurement_id: 3344, valor_real: 0.7, valor_teoric: 0.5 }]
const REGLES = new Map([[962, { logica: 'FIXED', increment_base: 0 }]])

const fes = (extra = {}) => construeixFilesDePresa({
  baseRows: BASE, linies: LINIES, reglaPerPom: REGLES, readOnly: true, ...extra,
})

test('la identitat i la nomenclatura viatgen senceres', () => {
  const [g1] = fes()

  assert.equal(g1.id, 3344)              // la PK de la mesura: la taula hi penja el bateig
  assert.equal(g1.pom_id, 962)
  assert.equal(g1.pom_code, 'G1')
  assert.equal(g1.capa, 'exterior')
  assert.equal(g1.instancia, '')
  assert.equal(g1.nom_fitxa, 'G1')
  assert.equal(g1.nom_canonic_model, 'GUSSET')
  assert.equal(g1.is_key, true)
})

test('la línia del check es creua per la PK, i sense línia la fila viu igual', () => {
  const [g1, fr] = fes()

  assert.equal(g1.lineId, 771)   // té línia oberta
  assert.equal(fr.lineId, null)  // no en té, i no és cap error: la fila ve de `base-stages`
})

test('CONSULTA · les dues columnes són la BASE VIGENT, no la presa', () => {
  // El defecte del MILEY: llegint `valor_real`/`valor_teoric` també en consulta, un model amb
  // valors gravats i cap SizeCheck ensenyava les files i les columnes a «—».
  const [g1, fr] = fes({ readOnly: true })

  assert.equal(g1.base_value_cm, 0.5)   // de `base-stages`, no el 0.7 de la línia
  assert.equal(g1.base_vigent, 0.5)
  assert.equal(fr.base_value_cm, 18.5)  // sense línia, i tanmateix amb xifra
})

test('PRESA · el carril porta el que la modista escriu avui', () => {
  const [g1, fr] = fes({ readOnly: false })

  assert.equal(g1.base_value_cm, 0.7)   // `valor_real` de la línia
  assert.equal(g1.base_vigent, 0.5)     // el teòric que el check va congelar
  assert.equal(fr.base_value_cm, null)  // sense línia no hi ha presa
})

test('la regla s\'hi fusiona per pom_id, i qui no en té no inventa camps', () => {
  const [g1, fr] = fes()

  assert.equal(g1.logica, 'FIXED')
  assert.equal(g1.increment_base, 0)
  assert.equal('logica' in fr, false)
})

test('entrades buides no peten: cap fila, i prou', () => {
  assert.deepEqual(construeixFilesDePresa({ baseRows: [], linies: [], reglaPerPom: new Map(), readOnly: true }), [])
  assert.deepEqual(construeixFilesDePresa({ readOnly: true }), [])
})
