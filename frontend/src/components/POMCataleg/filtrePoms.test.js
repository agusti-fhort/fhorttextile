// LA TRIA DE LA LLISTA DE POMs — el guard.
//
//     cd frontend && node --test src/components/POMCataleg/filtrePoms.test.js
//
// El que fixa, que és tot el que la peça promet:
//   1 · el DEFECTE és «actius» i la llista de treball deixa de portar l'arxiu a sobre;
//   2 · els RECOMPTES són de la llista sencera i NO ballen amb la cerca;
//   3 · la CERCA actua dins del tab… i la CREUADA diu quantes n'hi ha a l'altre costat —la
//       guarda perquè ningú re-creï un POM que viu a l'arxiu;
//   4 · el filtre de PENDENTS es combina amb el tab i amb la cerca alhora;
//   5 · al tab «Tots», els inactius van DARRERE dins de cada família.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  TABS, TAB_ACTIUS, TAB_INACTIUS, TAB_TOTS,
  delTab, casa, recomptes, tria, inactiusDarrere,
} from './filtrePoms.js'

// Files amb la forma que serveix `/api/v1/poms/` (retallades als camps que la tria toca).
const P = (id, codi, nom, actiu, pendent = false) => ({
  id, codi_client: codi, nom_client: nom, pom_code: codi, name_en: nom, name_cat: nom,
  actiu, pendent_revisio: pendent,
})

const LLISTA = [
  P(1, 'CH', 'Chest width', true),
  P(2, 'WA', 'Waist width', true, true),          // actiu I pendent
  P(3, 'HI', 'Hip width', true),
  P(4, 'WA-OLD', 'Waist width (arxiu)', false),   // l'arxiu que la cerca ha de saber trobar
  P(5, 'ZZ', 'Zip length', false, true),          // inactiu I pendent
]

test('el defecte és ACTIUS, i és el primer tab', () => {
  assert.equal(TABS[0], TAB_ACTIUS)
  assert.deepEqual(tria(LLISTA).files.map(p => p.id), [1, 2, 3])
})

test('cada tab veu el que li toca', () => {
  assert.deepEqual(delTab(LLISTA, TAB_ACTIUS).map(p => p.id), [1, 2, 3])
  assert.deepEqual(delTab(LLISTA, TAB_INACTIUS).map(p => p.id), [4, 5])
  assert.deepEqual(delTab(LLISTA, TAB_TOTS).map(p => p.id), [1, 2, 3, 4, 5])
})

test('una fila sense `actiu` compta com a ACTIVA (mai desapareix per un camp absent)', () => {
  const sensecamp = [{ id: 9, codi_client: 'X', nom_client: 'X' }]
  assert.equal(delTab(sensecamp, TAB_ACTIUS).length, 1)
  assert.equal(delTab(sensecamp, TAB_INACTIUS).length, 0)
})

test('els recomptes són de la llista SENCERA i no ballen amb la cerca', () => {
  const r = recomptes(LLISTA)
  assert.deepEqual(r, { [TAB_ACTIUS]: 3, [TAB_INACTIUS]: 2, [TAB_TOTS]: 5 })
  // La cerca no els toca: el badge del tab diu què hi ha al catàleg, no què queda del filtre.
  assert.deepEqual(recomptes(LLISTA), r)
})

test('la cerca mira codi, els dos noms i la categoria — i el buit ho casa tot', () => {
  const p = { codi_client: 'WA', nom_client: 'Amplada de cintura', name_en: 'Waist width',
              name_cat: 'Amplada', categoria: 'Lower body', actiu: true }
  assert.equal(casa(p, ''), true, 'sense text, tot passa')
  assert.equal(casa(p, '   '), true, 'només espais, també')
  assert.equal(casa(p, 'wa'), true, 'pel codi')
  assert.equal(casa(p, 'WAIST'), true, 'pel nom anglès, sense mirar majúscules')
  assert.equal(casa(p, 'cintura'), true, 'pel nom del client')
  assert.equal(casa(p, 'lower'), true, 'per la categoria')
  assert.equal(casa(p, 'zzz'), false)
  assert.equal(casa({}, 'zzz'), false, 'una fila buida no peta')
})

test('la cerca actua DINS del tab actiu', () => {
  assert.deepEqual(tria(LLISTA, { tab: TAB_ACTIUS, q: 'waist' }).files.map(p => p.id), [2])
  assert.deepEqual(tria(LLISTA, { tab: TAB_INACTIUS, q: 'waist' }).files.map(p => p.id), [4])
  assert.deepEqual(tria(LLISTA, { tab: TAB_TOTS, q: 'waist' }).files.map(p => p.id), [2, 4])
})

test('🚨 LA CREUADA: la cerca diu quantes n\'hi ha a l\'ALTRE costat', () => {
  assert.deepEqual(tria(LLISTA, { tab: TAB_ACTIUS, q: 'waist' }).creuada,
    { tab: TAB_INACTIUS, n: 1 })
  assert.deepEqual(tria(LLISTA, { tab: TAB_INACTIUS, q: 'waist' }).creuada,
    { tab: TAB_ACTIUS, n: 1 })
})

test('la creuada calla quan no hi ha res a dir', () => {
  assert.equal(tria(LLISTA, { tab: TAB_ACTIUS }).creuada, null, 'sense text de cerca')
  assert.equal(tria(LLISTA, { tab: TAB_ACTIUS, q: 'chest' }).creuada, null, 'sense res a l\'arxiu')
  assert.equal(tria(LLISTA, { tab: TAB_TOTS, q: 'waist' }).creuada, null, '«Tots» ja les veu totes')
})

test('la creuada troba l\'arxiu encara que el tab actiu no doni CAP resultat', () => {
  // El cas de la Montse: busca al catàleg viu, no hi és, i el duplicat 522 comença aquí.
  const r = tria(LLISTA, { tab: TAB_ACTIUS, q: 'arxiu' })
  assert.equal(r.files.length, 0)
  assert.deepEqual(r.creuada, { tab: TAB_INACTIUS, n: 1 })
})

test('el filtre de PENDENTS es combina amb el tab i amb la cerca', () => {
  assert.deepEqual(tria(LLISTA, { tab: TAB_ACTIUS, nomesPendents: true }).files.map(p => p.id), [2])
  assert.deepEqual(tria(LLISTA, { tab: TAB_INACTIUS, nomesPendents: true }).files.map(p => p.id), [5])
  assert.deepEqual(tria(LLISTA, { tab: TAB_TOTS, nomesPendents: true }).files.map(p => p.id), [2, 5])
  assert.deepEqual(
    tria(LLISTA, { tab: TAB_TOTS, q: 'waist', nomesPendents: true }).files.map(p => p.id), [2])
})

test('el xip de pendents diu quants n\'hi ha DINS del tab i la cerca', () => {
  assert.equal(tria(LLISTA, { tab: TAB_ACTIUS }).pendents, 1)
  assert.equal(tria(LLISTA, { tab: TAB_TOTS }).pendents, 2)
  assert.equal(tria(LLISTA, { tab: TAB_TOTS, q: 'waist' }).pendents, 1)
  // …i el número NO canvia pel fet de tenir el filtre encès: si no, apagar-lo seria endevinar.
  assert.equal(tria(LLISTA, { tab: TAB_TOTS, nomesPendents: true }).pendents, 2)
})

test('la cerca sense resultats no menteix', () => {
  const r = tria(LLISTA, { tab: TAB_TOTS, q: 'zzzzz' })
  assert.deepEqual(r.files, [])
  assert.equal(r.pendents, 0)
  assert.equal(r.creuada, null)
})

test('dins d\'una família, els inactius van DARRERE i la resta conserva l\'ordre', () => {
  assert.deepEqual(inactiusDarrere(LLISTA).map(p => p.id), [1, 2, 3, 4, 5])
  assert.deepEqual(inactiusDarrere([LLISTA[3], LLISTA[0], LLISTA[4], LLISTA[1]]).map(p => p.id),
    [1, 2, 4, 5])
})

test('sense llista no peta res', () => {
  assert.deepEqual(recomptes(null), { [TAB_ACTIUS]: 0, [TAB_INACTIUS]: 0, [TAB_TOTS]: 0 })
  assert.deepEqual(tria(null).files, [])
  assert.deepEqual(inactiusDarrere(undefined), [])
})
