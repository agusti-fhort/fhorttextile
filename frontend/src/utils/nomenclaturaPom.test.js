// Nomenclatura visible d'un POM — la cadena i, sobretot, la PROMESA.
//     cd frontend && node --test src/utils/nomenclaturaPom.test.js
//
// LA PROMESA QUE FIXA: la columna «Nomenclatura» no surt MAI buida. Una fila de mesures sense
// nom no es pot llegir ni anotar en un fitting presencial, i és exactament el que passava quan
// cada superfície es reescrivia la cadena pel seu compte i s'aturava al codi canònic — que un
// POM tenant-only no té.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { nomenclaturaDePom, nomsDePom } from './nomenclaturaPom.js'

// Una fila tal com la serveix `GET /models/<id>/base-measurements/`.
const bm = (extra) => ({
  nom_fitxa: '', client_alias: null, pom_code_global: '', codi_client: '', ...extra,
})

test('nom_fitxa mana per damunt de tot: és el que el tècnic ha escrit per a AQUEST model', () => {
  assert.equal(nomenclaturaDePom(bm({
    nom_fitxa: 'PIT', client_alias: 'A', pom_code_global: 'POM-020', codi_client: 'CH',
  })), 'PIT')
})

test('sense nom_fitxa mana l\'àlies del CLIENT: és el que diu el seu document', () => {
  assert.equal(nomenclaturaDePom(bm({
    client_alias: 'A', pom_code_global: 'POM-020', codi_client: 'CH',
  })), 'A')
})

test('🚨 sense nom_fitxa ni àlies mana el codi de la CASA, no el canònic (llei 22/08)', () => {
  // EL DEFECTE D'AGUS: aquí sortia `POM-020` (o `LOSPOM-548` a la fitxa que ell mirava) i el
  // catàleg del client en diu `CH`. La nomenclatura penja del client: ÀLIES > TENANT > GLOBAL.
  assert.equal(nomenclaturaDePom(bm({ pom_code_global: 'POM-020', codi_client: 'CH' })), 'CH')
})

test('el codi CANÒNIC és l\'ÚLTIM recurs, no el segon', () => {
  // Un POM que ningú no ha batejat: el global és cert i estable, i per això segueix a la
  // cadena. La promesa és que la columna no surt mai buida.
  assert.equal(nomenclaturaDePom(bm({ pom_code_global: 'POM-020' })), 'POM-020')
})

test('POM tenant-only (sense pom_global): cau al codi de la casa, MAI buida', () => {
  // El cas que trencava la promesa: sense `pom_global` el codi canònic és '', i una cadena
  // que s'hi aturés deixaria la cel·la muda.
  assert.equal(nomenclaturaDePom(bm({ codi_client: 'X-CUSTOM' })), 'X-CUSTOM')
})

test('una fila sense cap dels quatre camps torna string buida, no undefined', () => {
  // No es pot inventar un nom, però sí garantir el TIPUS: la cel·la de la taula fa
  // String(cell.text) i un undefined hi sortiria escrit literalment.
  assert.equal(nomenclaturaDePom(bm()), '')
  assert.equal(nomenclaturaDePom(null), '')
  assert.equal(nomenclaturaDePom(undefined), '')
})

test('els camps absents no compten com a valor (fila d\'un endpoint més pobre)', () => {
  assert.equal(nomenclaturaDePom({ codi_client: 'CH' }), 'CH')
})

// ── ELS DOS NOMS LLARGS, mateixa llei ──────────────────────────────────────────────────────
test('nomsDePom · el bateig del model mana per damunt del catàleg', () => {
  const r = nomsDePom({ nom_canonic_model: 'CHEST', nom_en: 'Chest width', nom_client: 'Pit' })
  assert.equal(r.canonic, 'CHEST')
})

test('nomsDePom · un POM tenant-only diu el nom de la casa, no una cadena buida', () => {
  // El banc 1383: 21 files sense `pom_global`, i per tant sense `nom_en` ni `nom_ca`.
  const r = nomsDePom({ nom_client: 'Sisa davantera' })
  assert.equal(r.canonic, 'Sisa davantera')
  assert.equal(r.local, '')   // una segona línia que repeteix la primera és soroll
})

test('nomsDePom · el local només surt quan diu una cosa diferent', () => {
  const r = nomsDePom({ nom_en: 'Chest width', nom_ca: 'Ample de pit' })
  assert.deepEqual(r, { canonic: 'Chest width', local: 'Ample de pit' })
})
