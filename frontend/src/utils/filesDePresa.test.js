// EL BANC DE LES FILES DE PRESA — S42/G8.
//
//     node --test frontend/src/utils/filesDePresa.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { filesDeLaPeca } from './identitatMesura.js'
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

// ── S42/G8 · EL REPARTIMENT ENTRE CONTENIDORS ──────────────────────────────────────────
//
// Aquestes files no es pinten totes juntes: `CheckMeasureEditor` les reparteix per prenda amb
// `filesDeLaPeca`, un contenidor per peça. El banc arriba fins aquí a posta — el defecte de
// F5 no era ni de l'adaptador sol ni del filtre sol, sinó de la JUNTA, i una junta només es
// prova provant-la sencera.

/** Les 18 files de `base-stages` del model 1379 (BRW-FW26-0002 «RUFFLES», tenant `fhort`),
 *  llegides el 16/08/2026: 11 de la peça mare i 7 de la '02' (Short). Cas real, no inventat. */
const BASE_1379 = [
  { base_measurement_id: 3339, pom_id: 906, pom_code: 'B', capa: 'exterior', instancia: 'top', garment: '', nom_fitxa: 'B', base_value_cm: 35.0 },
  { base_measurement_id: 3340, pom_id: 906, pom_code: 'B', capa: 'exterior', instancia: 'bottom', garment: '', nom_fitxa: 'BB', base_value_cm: 36.0 },
  { base_measurement_id: 3341, pom_id: 906, pom_code: 'B', capa: 'exterior', instancia: 'extended', garment: '', nom_fitxa: 'B1', base_value_cm: 45.0 },
  { base_measurement_id: 3342, pom_id: 908, pom_code: 'BF', capa: 'exterior', instancia: '', garment: '', nom_fitxa: 'BF', base_value_cm: 7.2 },
  { base_measurement_id: 3343, pom_id: 920, pom_code: 'D', capa: 'exterior', instancia: '', garment: '', nom_fitxa: 'D', base_value_cm: 78.0 },
  { base_measurement_id: 3344, pom_id: 962, pom_code: 'G1', capa: 'exterior', instancia: '', garment: '', nom_fitxa: 'G1', base_value_cm: 0.5 },
  { base_measurement_id: 3345, pom_id: 958, pom_code: 'FS', capa: 'exterior', instancia: 'cf', garment: '', nom_fitxa: 'FS', base_value_cm: 33.0 },
  { base_measurement_id: 3346, pom_id: 958, pom_code: 'FS', capa: 'exterior', instancia: 'cb', garment: '', nom_fitxa: 'FS2', base_value_cm: 35.5 },
  { base_measurement_id: 3347, pom_id: 958, pom_code: 'FS', capa: 'exterior', instancia: 'waistband_seam', garment: '', nom_fitxa: 'FS3', base_value_cm: 33.5 },
  { base_measurement_id: 3348, pom_id: 1050, pom_code: 'FS4', capa: 'exterior', instancia: '', garment: '', nom_fitxa: 'FS4', base_value_cm: 22.0 },
  { base_measurement_id: 3349, pom_id: 960, pom_code: 'FS5', capa: 'folre', instancia: '', garment: '', nom_fitxa: 'FS5', base_value_cm: 1.0 },
  { base_measurement_id: 3350, pom_id: 954, pom_code: 'FD', capa: 'exterior', instancia: '', garment: '02', nom_fitxa: 'FR', base_value_cm: 18.5 },
  { base_measurement_id: 3351, pom_id: 955, pom_code: 'FE', capa: 'exterior', instancia: '', garment: '02', nom_fitxa: 'FE', base_value_cm: 30.0 },
  { base_measurement_id: 3352, pom_id: 914, pom_code: 'CT', capa: 'exterior', instancia: '', garment: '02', nom_fitxa: 'CT', base_value_cm: 33.0 },
  { base_measurement_id: 3353, pom_id: 993, pom_code: 'M', capa: 'exterior', instancia: '', garment: '02', nom_fitxa: 'M', base_value_cm: 33.0 },
  { base_measurement_id: 3354, pom_id: 962, pom_code: 'G1', capa: 'exterior', instancia: '', garment: '02', nom_fitxa: 'M1', base_value_cm: 0.5 },
  { base_measurement_id: 3355, pom_id: 956, pom_code: 'FI', capa: 'exterior', instancia: '', garment: '02', nom_fitxa: 'F1', base_value_cm: 5.0 },
  { base_measurement_id: 3356, pom_id: 949, pom_code: 'F2', capa: 'exterior', instancia: 'waistband_seam', garment: '02', nom_fitxa: 'FT', base_value_cm: 22.0 },
]

const repartides = (baseRows) => {
  const files = construeixFilesDePresa({ baseRows, linies: [], reglaPerPom: new Map(), readOnly: true })
  // El mateix que fa `CheckMeasureEditor` per a cada contenidor de `PecesDelModel`.
  return { mare: filesDeLaPeca(files, ''), short: filesDeLaPeca(files, '02') }
}

test('🚨 1379 · «Model base» es queda 11 files i «Short» les seves 7', () => {
  const { mare, short } = repartides(BASE_1379)

  assert.equal(mare.length, 11)
  assert.deepEqual(short.map(f => f.nom_fitxa), ['FR', 'FE', 'CT', 'M', 'M1', 'F1', 'FT'])
  // Ni una fila duplicada ni una de perduda: els dos contenidors sumen el payload sencer.
  assert.equal(mare.length + short.length, BASE_1379.length)
})

test('🚨 el POM que viu a LES DUES prendes no es confon de contenidor', () => {
  // El 962 (G1) hi és dos cops amb la MATEIXA `(capa, instancia)`: només l'eix de prenda els
  // separa. És el cas que fa que aquest guard no es pugui passar per casualitat.
  const { mare, short } = repartides(BASE_1379)

  assert.deepEqual(mare.filter(f => f.pom_id === 962).map(f => f.id), [3344])
  assert.deepEqual(short.filter(f => f.pom_id === 962).map(f => f.id), [3354])
})

test('CONTROL una-peça · un model sense \'02\' no canvia de comportament', () => {
  // El 100% del corpus d'una sola prenda: totes les files són de la mare i el contenidor únic
  // se les queda. Aquest cas ha de ser idèntic abans i després de F5.
  const nomesMare = BASE_1379.filter(r => r.garment === '')
  const { mare, short } = repartides(nomesMare)

  assert.equal(mare.length, 11)
  assert.equal(short.length, 0)
  // I sense saber encara quina peça és (`/peces/` no ha contestat), hi són TOTES: mai es
  // buida una taula pel dubte.
  const files = construeixFilesDePresa({ baseRows: nomesMare, readOnly: true })
  assert.equal(filesDeLaPeca(files, null).length, 11)
})
