// FASE A — el filtre de seccions per desplegament (`seccionsVisibles`).
// Banc pur: `node --test src/utils/modelSeccions.test.js`.
import test from 'node:test'
import assert from 'node:assert/strict'

import { SECCIONS_MODEL, seccionsVisibles, pindolesDeModel } from './modelSeccions.js'

test('encès: la llista és la canònica, element per element', () => {
  assert.deepEqual(seccionsVisibles(true), SECCIONS_MODEL)
})

test('apagat: cau «Patró» i NOMÉS «Patró»', () => {
  const vistes = seccionsVisibles(false)
  assert.ok(!vistes.includes('Patró'))
  assert.deepEqual(vistes, SECCIONS_MODEL.filter((s) => s !== 'Patró'))
  assert.equal(vistes.length, SECCIONS_MODEL.length - 1)
})

test("apagat: l'ORDRE de la resta no es mou", () => {
  // L'ordre és dada (és el recorregut del model). Filtrar no pot reordenar res.
  const vistes = seccionsVisibles(false)
  const esperat = ['Dashboard', 'Resum', 'Mesures', 'Escalat', 'Fitxa tècnica',
    'Fitxers', "Registre d'activitat", 'Tasques']
  assert.deepEqual(vistes, esperat)
})

test('cap dels dos casos muta la llista canònica', () => {
  const copia = [...SECCIONS_MODEL]
  seccionsVisibles(true)
  seccionsVisibles(false)
  assert.deepEqual(SECCIONS_MODEL, copia)
})

test('les píndoles hereten el filtre quan se les hi passa', () => {
  const t = (clau) => clau
  const apagades = pindolesDeModel({
    activa: 'Dashboard', onTria: () => {}, t, seccions: seccionsVisibles(false),
  })
  assert.ok(!apagades.some((p) => p.key === 'Patró'))
  // …i sense passar-n'hi cap, el default segueix sent la llista sencera: la signatura vella
  // (`{activa, onTria, t}`) no ha canviat de comportament per a ningú.
  const totes = pindolesDeModel({ activa: 'Dashboard', onTria: () => {}, t })
  assert.equal(totes.length, SECCIONS_MODEL.length)
  assert.ok(totes.some((p) => p.key === 'Patró'))
})
