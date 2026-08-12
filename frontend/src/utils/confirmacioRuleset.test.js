// El banc de la clau de confirmació — SET-2/T7-B4.
//
// La regla que es guarda aquí: **dos 409 del mateix tipus no són el mateix avís si parlen de
// prendes diferents**. Amb un model d'una sola peça la distinció no es notava; amb dues, la
// clau vella convertia la segona pregunta en un error vermell.
//
//     node --test frontend/src/utils/confirmacioRuleset.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { FLAG_PER_TIPUS, clauDeConfirmacio, garmentDeLavis } from './confirmacioRuleset.js'

test('dues peces, dos 409 del MATEIX tipus, dues confirmacions independents', () => {
  const deLa02 = { tipus: 'esborrat_residents', garment: '02', residents: 5 }
  const deLaMare = { tipus: 'esborrat_residents', garment: '', residents: 10 }

  assert.notEqual(clauDeConfirmacio(deLa02), clauDeConfirmacio(deLaMare))
  // I el flag que autoritza segueix sent el MATEIX: qui decideix quantes vegades es pregunta és
  // la clau; què autoritza cada resposta ho diu el contracte del servidor.
  assert.equal(FLAG_PER_TIPUS[deLa02.tipus], FLAG_PER_TIPUS[deLaMare.tipus])
})

test('el mateix avís repetit dona la MATEIXA clau: el bucle s\'ha de plantar', () => {
  // Un 409 idèntic després d'enviar el flag vol dir que el backend no l'ha acceptat. Tornar-hi
  // seria un bucle infinit amb cara de pantalla penjada.
  const avis = { tipus: 'ruleset_altre_client', garment: '02' }

  assert.equal(clauDeConfirmacio(avis), clauDeConfirmacio({ ...avis }))
})

test('un 409 que no és confirmable no té clau', () => {
  // `garment_duplicat` i `garment_amb_dades` també són 409, i NO es confirmen: es mostren. Si
  // tinguessin clau, el bucle els preguntaria i els reintentaria eternament.
  assert.equal(clauDeConfirmacio({ tipus: 'garment_duplicat', garment: '02' }), null)
  assert.equal(clauDeConfirmacio({}), null)
  assert.equal(clauDeConfirmacio(null), null)
})

test('mana el payload; el context del gest només és el pla B', () => {
  assert.equal(garmentDeLavis({ garment: '02' }, '03'), '02')
  assert.equal(garmentDeLavis({}, '03'), '03')
})

test('la mare és `\'\'` i és un valor, no un «no ho sé»', () => {
  // Un eix buit i un eix absent no es poden confondre (llei del vocabulari, F22): el payload
  // que diu `garment: ''` afirma que parla de la mare, i no ha de caure al context.
  assert.equal(garmentDeLavis({ garment: '' }, '02'), '')
  assert.equal(clauDeConfirmacio({ tipus: 'esborrat_residents', garment: '' }, '02'),
    'esborrat_residents|')
})
