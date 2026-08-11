// EL GUARD DE LA IDENTITAT DE FILA — SET-2/T6b.
//
// Aquesta clau no viatja i no es desa: és interna d'un `Map` del client. Per això, quan
// s'equivoca, no hi ha cap error — hi ha una FILA MENYS a la pantalla, i ningú no ho anuncia.
// És exactament el tipus de defecte que només un banc veu.
//
//     node --test frontend/src/utils/identitatMesura.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { identitatMesura } from './identitatMesura.js'

test('dues files idèntiques en tot MENYS el garment no col·lapsen', () => {
  // EL CAS QUE OBRE SET-2: la mateixa mesura, la mateixa capa i la mateixa instància, a dues
  // prendes del mateix model. Amb tres trams, la segona queia a sobre de la primera al `Map`
  // i desapareixia de la graella sense dir res.
  const cos = { pom_id: 12, capa: 'exterior', instancia: '', garment: '' }
  const maniga = { pom_id: 12, capa: 'exterior', instancia: '', garment: '02' }

  assert.notEqual(identitatMesura(cos), identitatMesura(maniga))
  assert.equal(new Map([cos, maniga].map(f => [identitatMesura(f), f])).size, 2)
})

test('el garment va L\'ÚLTIM, com al backend (`pom/identitat.py`)', () => {
  // No és estètica: el front en fabrica un de paral·lel al del contracte, i tenir-los amb
  // l'ordre canviat convidaria a comparar-los algun dia i a creure que difereixen.
  assert.equal(
    identitatMesura({ pom_id: 12, capa: 'folre', instancia: 'esq', garment: '02' }),
    '12|folre|esq|02',
  )
})

test('la PEÇA MARE és el tram buit, mai absent', () => {
  // Els quatre trams sempre: `12|exterior||` i `12|exterior|` serien la mateixa mesura escrita
  // de dues maneres, i qualsevol comparació de claus diria que són distintes.
  assert.equal(identitatMesura({ pom_id: 12, capa: 'exterior', instancia: '' }), '12|exterior||')
  assert.equal(identitatMesura({ pom_id: 12, capa: 'exterior', instancia: '', garment: '' }),
    '12|exterior||')
  assert.equal(identitatMesura({ pom_id: 12, capa: 'exterior', instancia: '', garment: null }),
    '12|exterior||')
})

test('CONTROL — amb una sola peça, l\'agrupació és la d\'avui', () => {
  // El 100% del corpus: cap fila porta garment. Les germanes s'han de seguir separant per capa
  // i per instància exactament igual que abans, i les no-germanes seguir col·lapsant.
  const files = [
    { pom_id: 12, capa: 'exterior', instancia: '' },
    { pom_id: 12, capa: 'folre', instancia: '' },
    { pom_id: 12, capa: 'exterior', instancia: 'esq' },
    { pom_id: 12, capa: 'exterior', instancia: 'dre' },
    { pom_id: 13, capa: 'exterior', instancia: '' },
  ]
  const clau = new Map(files.map(f => [identitatMesura(f), f]))
  assert.equal(clau.size, 5)

  // I dues línies de la MATEIXA mesura (el cas que el `Map` ha de col·lapsar a posta: dues
  // talles de la mateixa fila) segueixen caient a la mateixa clau.
  assert.equal(
    identitatMesura({ pom_id: 12, capa: 'exterior', instancia: '', size_label: 'S' }),
    identitatMesura({ pom_id: 12, capa: 'exterior', instancia: '', size_label: 'M' }),
  )
})

test('un camp absent i un camp buit són la MATEIXA fila', () => {
  // Els payloads no són uniformes: uns emeten `instancia: ''` i altres no l'emeten. Si les dues
  // formes donessin claus distintes, la mateixa fila es duplicaria segons de quina vora vingui.
  assert.equal(identitatMesura({ pom_id: 7 }), identitatMesura({
    pom_id: 7, capa: '', instancia: '', garment: '',
  }))
})
