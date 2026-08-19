// EL GUARD DE LA IDENTITAT DE FILA — SET-2/T6b.
//
// Aquesta clau no viatja i no es desa: és interna d'un `Map` del client. Per això, quan
// s'equivoca, no hi ha cap error — hi ha una FILA MENYS a la pantalla, i ningú no ho anuncia.
// És exactament el tipus de defecte que només un banc veu.
//
//     node --test frontend/src/utils/identitatMesura.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { clauDeFila, clauRegla, eixosDeLaFila, filesDeLaPeca, identitatMesura } from './identitatMesura.js'

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

test('la PK mana sobre els eixos quan el payload la dona', () => {
  // `BaseMeasurement` és únic per (model, pom, capa, instancia, garment): la seva PK és una
  // identitat MÉS FORTA que els quatre trams, i no cal recompondre res per fer-la servir.
  assert.equal(clauDeFila({ pom_id: 12, capa: 'exterior' }, 881), 881)
  assert.equal(clauDeFila({ pom_id: 12, capa: 'exterior' }, 0), 0)   // una PK 0 seguiria sent PK
})

test('sense PK, el pla B és la CLAU SENCERA i no el pom_id', () => {
  // EL DEFECTE D'AVUI, i no espera les peces per fer mal: amb `?? pom_id`, dues germanes
  // —la mateixa mesura a l'exterior i al folre— comparteixen clau de fila, i React reconcilia
  // una amb l'estat de l'altra (cel·la enfocada, ordre en arrossegar).
  const exterior = { pom_id: 12, capa: 'exterior', instancia: '' }
  const folre = { pom_id: 12, capa: 'folre', instancia: '' }

  assert.notEqual(clauDeFila(exterior, null), clauDeFila(folre, null))
  assert.notEqual(clauDeFila(exterior, undefined), 12)
  assert.equal(clauDeFila(exterior, null), '12|exterior||')
  // I la peça, quan arribi, hi és pel mateix camí.
  assert.notEqual(clauDeFila({ ...exterior, garment: '02' }, null), clauDeFila(exterior, null))
})

test('un camp absent i un camp buit són la MATEIXA fila', () => {
  // Els payloads no són uniformes: uns emeten `instancia: ''` i altres no l'emeten. Si les dues
  // formes donessin claus distintes, la mateixa fila es duplicaria segons de quina vora vingui.
  assert.equal(identitatMesura({ pom_id: 7 }), identitatMesura({
    pom_id: 7, capa: '', instancia: '', garment: '',
  }))
})

// ── SET-2/T7-B8 · el repartiment de files per contenidor ────────────────────────────────

test('cada contenidor es queda les seves files, i la mare és `\'\'`', () => {
  const files = [
    { pom_id: 1, garment: '' }, { pom_id: 2, garment: '02' }, { pom_id: 3 },
  ]

  assert.deepEqual(filesDeLaPeca(files, '').map(f => f.pom_id), [1, 3])   // sense eix = de la mare
  assert.deepEqual(filesDeLaPeca(files, '02').map(f => f.pom_id), [2])
  assert.deepEqual(filesDeLaPeca(files, '03').map(f => f.pom_id), [])     // buit, i és correcte
})

test('sense saber la peça hi són TOTES: mai es buida una taula pel dubte', () => {
  // `/peces/` no ha contestat o ha fallat. Filtrar per un eix desconegut deixaria el model
  // sencer sense taula — el pitjor error possible en una superfície de treball.
  const files = [{ pom_id: 1, garment: '' }, { pom_id: 2, garment: '02' }]

  assert.equal(filesDeLaPeca(files, null).length, 2)
  assert.equal(filesDeLaPeca(files, undefined).length, 2)
  assert.deepEqual(filesDeLaPeca(null, ''), [])
})

// ── S42 · EL 1379 REAL, I EL FORAT QUE NO CANTA ────────────────────────────────────────
//
// Les 18 files de `BRW-FW26-0002` (RUFFLES) tal com les serveixen `taula-mesures` i
// `base-stages` el 16/08/2026: 11 de la mare i 7 de la 02 (Short). No és un cas inventat —
// és el model amb què es va reportar que «les 7 del Short surten al contenidor de la mare».
const FILES_1379 = [
  { codi: 'B', garment: '' }, { codi: 'BB', garment: '' }, { codi: 'B1', garment: '' },
  { codi: 'BF', garment: '' }, { codi: 'D', garment: '' }, { codi: 'G1', garment: '' },
  { codi: 'FS', garment: '' }, { codi: 'FS2', garment: '' }, { codi: 'FS3', garment: '' },
  { codi: 'FS4', garment: '' }, { codi: 'FS5', garment: '' },
  { codi: 'FR', garment: '02' }, { codi: 'FE', garment: '02' }, { codi: 'CT', garment: '02' },
  { codi: 'M', garment: '02' }, { codi: 'M1', garment: '02' }, { codi: 'F1', garment: '02' },
  { codi: 'FT', garment: '02' },
]

test('1379 · els dos contenidors es reparteixen 11 / 7, i cap fila es queda pel camí', () => {
  const mare = filesDeLaPeca(FILES_1379, '')
  const short = filesDeLaPeca(FILES_1379, '02')

  assert.equal(mare.length, 11)
  assert.deepEqual(short.map(f => f.codi), ['FR', 'FE', 'CT', 'M', 'M1', 'F1', 'FT'])
  // Cap fila duplicada i cap perduda: els dos contenidors sumen el payload sencer.
  assert.equal(mare.length + short.length, FILES_1379.length)
})

test('🚨 una fila que ha PERDUT l\'eix cau a la MARE, i el forat és MUT', () => {
  // AIXÒ ÉS EL QUE S'HA DE VIGILAR, i per què cap pantalla en pot avisar: `f.garment || ''`
  // no distingeix «és de la mare» de «algú ha deixat caure el camp pel camí». Un adaptador
  // que no copiï `garment` (v. `buildEscalatRows`, `buildRepasRows`, `CheckMeasureEditor.
  // buildRows`, que el copien TOTS TRES a posta) no peta, no avisa i no deixa rastre: les
  // seves files se'n van senceres al primer contenidor i el de la peça surt buit.
  //
  // El símptoma és EXACTAMENT el que es va reportar el 16/08, i per això el cas viu aquí amb
  // nom i cognoms: si algun dia torna, que el banc digui de què es tracta abans que ningú
  // hagi de tornar a llegir sis fitxers.
  const ambFuita = FILES_1379.map(f => (f.garment === '02' ? { codi: f.codi } : f))

  assert.equal(filesDeLaPeca(ambFuita, '').length, 18)   // ← les 18 al contenidor de la mare
  assert.equal(filesDeLaPeca(ambFuita, '02').length, 0)  // ← i el del Short, buit
})

// ── S42/F5+ · LA PODA, I ON VA A PARAR ────────────────────────────────────────────────
//
// Aquest banc no es queda al payload: el RESOL, perquè el dany no era d'un costat ni de
// l'altre sinó de la JUNTA. Enviar dos eixos de tres no peta enlloc — simplement apunta a una
// altra fila, i aquella fila cau.

/** Les files de `BaseMeasurement` del 1379 que tenen germana a l'altra prenda, tal com són a
 *  BD: el POM 962 (G1) hi és dos cops amb la MATEIXA `(capa, instancia)`. Només l'eix de
 *  prenda els separa, i per això és el cas que aquest guard no pot passar per casualitat. */
const BD_1379 = [
  { id: 3344, pom_id: 962, capa: 'exterior', instancia: '', garment: '' },    // la MARE
  { id: 3354, pom_id: 962, capa: 'exterior', instancia: '', garment: '02' },  // el SHORT
  { id: 3350, pom_id: 954, capa: 'exterior', instancia: '', garment: '02' },  // només al Short
  { id: 3342, pom_id: 908, capa: 'exterior', instancia: '', garment: '' },    // només a la mare
]

/** MIRALL de `desactivar_pom_view` (`models_app/views.py:4964`): filtra per
 *  `(model, pom, capa, instancia, garment)`, i qui no diu un eix rep el literal de la MARE
 *  (`_identitat_de_mesura`, `:3636`). Retorna la PK que cauria, o `null` (el 404). */
const filaQueCau = (payload) => {
  const capa = payload.capa || 'exterior'
  const instancia = payload.instancia || ''
  const garment = payload.garment || ''
  const bm = BD_1379.find(r => r.pom_id === payload.pom_id && r.capa === capa
    && r.instancia === instancia && r.garment === garment)
  return bm ? bm.id : null
}

const podaDe = (fila) => filaQueCau({ pom_id: fila.pom_id, ...eixosDeLaFila(fila) })

test('🚨 1379 · podar la fila del SHORT no toca la de la mare', () => {
  // EL DANY QUE AIXÒ TANCA: amb el contenidor Short buit, aquest clic no existia. F5 el va
  // omplir i el mateix clic va passar a desactivar la fila de la MARE, amb entrada al
  // `MeasurementChangeLog`, que és append-only.
  const delShort = { pom_id: 962, capa: 'exterior', instancia: '', garment: '02' }
  const deLaMare = { pom_id: 962, capa: 'exterior', instancia: '', garment: '' }

  assert.equal(podaDe(delShort), 3354)   // la del Short, no la 3344
  assert.equal(podaDe(deLaMare), 3344)   // i la de la mare segueix sent la seva
})

test('els tres eixos viatgen, i la mare és `\'\'` i no absent', () => {
  assert.deepEqual(eixosDeLaFila({ capa: 'folre', instancia: 'esq', garment: '02' }),
    { capa: 'folre', instancia: 'esq', garment: '02' })
  // Una fila de la mare i una fila a qui ningú ha posat l'eix han de dir el MATEIX al
  // servidor: `''`. Enviar `undefined` seria deixar que el default decidís per nosaltres.
  assert.equal(eixosDeLaFila({ capa: 'exterior', instancia: '', garment: '' }).garment, '')
  assert.equal(eixosDeLaFila({ capa: 'exterior', instancia: '' }).garment, '')
})

test('CONTROL · una fila que viu a UNA sola prenda cau on toca', () => {
  assert.equal(podaDe({ pom_id: 954, capa: 'exterior', instancia: '', garment: '02' }), 3350)
  assert.equal(podaDe({ pom_id: 908, capa: 'exterior', instancia: '', garment: '' }), 3342)
})

test('CONTROL una-peça · sense `02` la poda va contra la mare, com sempre', () => {
  // El 100% del corpus d'una sola prenda: totes les files són `garment:''` i el
  // comportament ha de ser idèntic al d'abans d'aquest canvi.
  for (const fila of BD_1379.filter(r => r.garment === '')) {
    assert.equal(podaDe(fila), fila.id)
  }
})

test('la regla és del POM i de la PRENDA: dues capes la comparteixen, dues prendes no', () => {
  const mareExterior = { pom_id: 7, garment: '', capa: 'exterior' }
  const mareFolre = { pom_id: 7, garment: '', capa: 'folre' }
  const laDeLa02 = { pom_id: 7, garment: '02', capa: 'exterior' }

  assert.equal(clauRegla(mareExterior), clauRegla(mareFolre))   // mateixa llei d'increments
  assert.notEqual(clauRegla(mareExterior), clauRegla(laDeLa02)) // prendes distintes, regles distintes
  assert.equal(clauRegla({ pom_id: 7 }), '7|')                  // sense eix = la mare
})
