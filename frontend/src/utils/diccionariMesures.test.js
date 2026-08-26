// LA COMPOSICIÓ DEL CODI I DEL SLUG D'UNA GERMANA (D-31.26).
//     cd frontend && node --test src/utils/diccionariMesures.test.js
//
// LA PROMESA QUE FIXA: el codi proposat és `base + sufix` CONCATENAT, sense cap separador
// —estil Brownie natiu: `B`+`T` → `BT`, mai `B-T`—, i el slug d'instància es compon SEMPRE en
// l'ordre dels eixos (posició abans que estat). L'ordre importa perquè la clau única de la BD
// és `(model, pom, capa, instancia)`: si el slug depengués de l'ordre de clic, la mateixa
// germana tindria dues claus i les dues files conviurien sense que res petés.
//
// I la promesa INVERSA, que és la que evita inventar codis: els ESTATS no porten sufix i la
// CAPA no toca mai el codi. Quan no hi ha sufix, la proposta és el codi base tal qual.

import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  COMPLEMENTARIA, dimensionsDe, eixPrincipal, nomEnIdioma,
  eixDe, filaInstancia, tramsInstancia, composaInstancia, codiProposat, codiBase,
  subeixDe, clauExclusio, xoquen,
} from './diccionariMesures.js'

// Els eixos NO són constants del front: són el que el diccionari declara. Aquí es fixen amb el
// literal que la BD emet perquè el test parli del contracte, no de cap import.
const EIX_POSICIO = 'POSICIO'
const EIX_ESTAT = 'ESTAT'

// Diccionari amb la forma EXACTA que emet `GET /api/v1/mesures/diccionari/` (verificat contra
// el tenant `fhort` el 05/08). Retallat a les files que els casos toquen.
const D = {
  capes: [{ slug: 'exterior' }, { slug: 'folre' }],
  eixos: [
    { clau: EIX_POSICIO, nom_en: 'Position', nom_ca: 'Posició', nom_es: 'Posición' },
    { clau: EIX_ESTAT, nom_en: 'State', nom_ca: 'Estat', nom_es: 'Estado' },
  ],
  // LES FAMÍLIES, EN ORDRE CANÒNIC (llei d'Agus, 26/08): peça → banda → verticalitat →
  // costura → línia → estat. No és el `display_order` —aquell diu en quin ordre s'OFEREIXEN
  // els xips— i no s'hi ha de fer coincidir.
  subeixos: ['PECA', 'BANDA', 'VERTICALITAT', 'COSTURA', 'LINIA', 'ESTAT'],
  // 🚨 LES CLAUS D'AQUEST OBJECTE VAN A POSTA EN L'ORDRE «DOLENT» (ESTAT primer).
  //
  // Aquest fixture les tenia amb POSICIO davant, i **el servidor no les emetia així**: les
  // posava `order_by('eix')`, que és ALFABÈTIC (`'ESTAT' < 'POSICIO'`). `pesCanonic` en prenia
  // l'ordre de composició amb `Object.keys`, o sigui que el test passava en VERD contra un
  // payload que la porta real no envia mai — i la BD, mentrestant, acumulava `extended-right`.
  //
  // Ara el fixture reprodueix l'ordre que el servidor DEIA (el pitjor cas) i l'ordre canònic
  // n'ha de sortir igualment bé: si algú torna a fer dependre la composició de les claus
  // d'aquest objecte, aquestes assercions cauen.
  instancies: {
    [EIX_ESTAT]: [
      { slug: 'relaxed', sufix: '', subeix: 'ESTAT', display_order: 1 },
      { slug: 'extended', sufix: '', subeix: 'ESTAT', display_order: 2 },
    ],
    [EIX_POSICIO]: [
      { slug: 'left', sufix: 'L', subeix: 'BANDA', display_order: 1 },
      { slug: 'right', sufix: 'R', subeix: 'BANDA', display_order: 2 },
      { slug: 'top', sufix: 'T', subeix: 'VERTICALITAT', display_order: 3 },
      // `BM`, no `B`: `B` és de `back` des del 22-23/08 (`pom/0079_bottom_sufix_bm`).
      { slug: 'bottom', sufix: 'BM', subeix: 'VERTICALITAT', display_order: 4 },
      { slug: 'cf', sufix: 'CF', subeix: 'LINIA', display_order: 5 },
      { slug: 'cb', sufix: 'CB', subeix: 'LINIA', display_order: 6 },
      { slug: 'side', sufix: 'S', subeix: 'COSTURA', display_order: 7 },
      { slug: 'waistband_seam', sufix: '', subeix: 'COSTURA', display_order: 8 },
      { slug: 'front', sufix: 'F', subeix: 'PECA', display_order: 9 },
      { slug: 'back', sufix: 'B', subeix: 'PECA', display_order: 10 },
    ],
  },
  regles: { sufix_separador: '', instancia_separador: '-', capa_al_codi: false, instancia_unica: '' },
}

test('el sufix s\'enganxa SENSE separador (estil Brownie natiu)', () => {
  assert.equal(codiProposat(D, 'B', ['top']), 'BT')
  assert.equal(codiProposat(D, 'FS', ['cf']), 'FSCF')
  assert.equal(codiProposat(D, 'AH', ['left']), 'AHL')
  // I mai amb guió: és exactament el format que les dades velles porten malament.
  assert.notEqual(codiProposat(D, 'AH', ['left']), 'AH-L')
})

test('els ESTATS no componen sufix: la proposta és el codi base', () => {
  assert.equal(codiProposat(D, 'B', ['relaxed']), 'B')
  assert.equal(codiProposat(D, 'B', ['extended']), 'B')
  // `waistband_seam` és un DATUM i tampoc no en porta (es diu a la descripció).
  assert.equal(codiProposat(D, 'W', ['waistband_seam']), 'W')
})

test('creuar els dos eixos enganxa NOMÉS el sufix de la posició', () => {
  assert.equal(codiProposat(D, 'B', ['left', 'relaxed']), 'BL')
  assert.equal(codiProposat(D, 'B', ['relaxed', 'left']), 'BL')
})

test('el slug compost va SEMPRE en l\'ordre CANÒNIC, no en el del clic', () => {
  assert.equal(composaInstancia(D, ['left', 'relaxed']), 'left-relaxed')
  assert.equal(composaInstancia(D, ['relaxed', 'left']), 'left-relaxed')
  // 🚨 EL CAS QUE LA BD PORTAVA MAL ESCRIT. Amb l'ordre pres de `Object.keys(instancies)` —i
  // el servidor emetent ESTAT primer— d'aquí en sortia `extended-right`, que és el que hi ha
  // desat a `fhort` (pk 3389/3390). La llei diu banda abans que estat.
  assert.equal(composaInstancia(D, ['extended', 'right']), 'right-extended')
  assert.equal(composaInstancia(D, ['right', 'extended']), 'right-extended')
  assert.equal(composaInstancia(D, ['relaxed', 'right']), 'right-relaxed')
  // Idempotent i sense duplicats: dos clics a la mateixa opció no fabriquen `left-left`.
  assert.equal(composaInstancia(D, ['left', 'left']), 'left')
  assert.equal(composaInstancia(D, []), '')
})

test('el slug compost es desmunta pel separador del diccionari', () => {
  assert.deepEqual(tramsInstancia(D, 'left-relaxed'), ['left', 'relaxed'])
  assert.deepEqual(tramsInstancia(D, 'left'), ['left'])
  assert.deepEqual(tramsInstancia(D, ''), [])
  assert.deepEqual(tramsInstancia(D, null), [])
})

test('cada slug sap de quin eix és, i un de desconegut no menteix', () => {
  assert.equal(eixDe(D, 'left'), EIX_POSICIO)
  assert.equal(eixDe(D, 'cb'), EIX_POSICIO)
  assert.equal(eixDe(D, 'extended'), EIX_ESTAT)
  assert.equal(eixDe(D, 'sleeve-2'), null)
  assert.equal(eixDe(null, 'left'), null)
})

test('la fila del diccionari porta el sufix real', () => {
  assert.equal(filaInstancia(D, 'cf').sufix, 'CF')
  assert.equal(filaInstancia(D, 'relaxed').sufix, '')
  assert.equal(filaInstancia(D, 'inexistent'), null)
})

test('les complementàries són recíproques, i no totes les posicions en tenen', () => {
  for (const [a, b] of Object.entries(COMPLEMENTARIA)) {
    assert.equal(COMPLEMENTARIA[b], a, `${a}↔${b} no és recíproca`)
  }
  // `side` i `waistband_seam` NO es parteixen: no tenen germana geomètrica.
  assert.equal(COMPLEMENTARIA.side, undefined)
  assert.equal(COMPLEMENTARIA.waistband_seam, undefined)
})

test('el codi base es recupera per RE-partir sense acumular sufixos', () => {
  assert.equal(codiBase(D, 'AHL', ['left']), 'AH')
  assert.equal(codiBase(D, 'BT', ['top']), 'B')
  assert.equal(codiBase(D, 'FSCF', ['cf']), 'FS')
  // Creuament dels dos eixos: només la posició havia posat sufix.
  assert.equal(codiBase(D, 'BL', ['left', 'relaxed']), 'B')
  // Sense instància no hi ha res a treure.
  assert.equal(codiBase(D, 'CH', []), 'CH')
})

test('el codi base no endevina: només treu el sufix que la fila DECLARA', () => {
  // «TOTAL» acaba en «L» però la fila no diu `left` → no se'n toca res.
  assert.equal(codiBase(D, 'TOTAL', []), 'TOTAL')
  // I si la fila diu `right`, tampoc: el sufix que busca és «R», i «TOTAL» no hi acaba.
  assert.equal(codiBase(D, 'TOTAL', ['right']), 'TOTAL')
  // Amb `left` sí que hi acaba, i és el que la fila declara: es treu.
  assert.equal(codiBase(D, 'TOTAL', ['left']), 'TOTA')
})

test('sense diccionari no s\'inventa res', () => {
  assert.equal(codiProposat(null, 'B', ['top']), 'B')
  assert.equal(composaInstancia(null, ['left']), 'left')
})

// ── LES DIMENSIONS DE LA TAULA SURTEN DE LA BD ──────────────────────────────────────────────
// La prova que res no està codificat al front: canviant el diccionari canvien els grups de
// columnes, les seves opcions i el seu ordre, sense tocar cap fitxer de codi.

test('un grup de columnes per EIX, amb TOTES les opcions de l\'eix i en el seu ordre', () => {
  const dims = dimensionsDe(D)
  assert.deepEqual(dims.map(d => d.clau), [EIX_POSICIO, EIX_ESTAT])
  // DEU posicions —les vuit de sempre i les dues CARES (22-23/08)—, no les dues de la
  // demostració de la maqueta.
  assert.deepEqual(dims[0].opcions.map(o => o.slug),
    ['left', 'right', 'top', 'bottom', 'cf', 'cb', 'side', 'waistband_seam', 'front', 'back'])
  assert.deepEqual(dims[1].opcions.map(o => o.slug), ['relaxed', 'extended'])
})

test('un diccionari amb un eix MÉS dona una columna més, sense tocar el codi', () => {
  const D3 = {
    ...D,
    eixos: [...D.eixos, { clau: 'CAPA_TECNICA', nom_en: 'Technique', nom_ca: 'Tècnica', nom_es: 'Técnica' }],
    instancies: { ...D.instancies, CAPA_TECNICA: [{ slug: 'knit', sufix: 'K', display_order: 1 }] },
  }
  const dims = dimensionsDe(D3)
  assert.equal(dims.length, 3)
  assert.equal(dims[2].clau, 'CAPA_TECNICA')
  assert.deepEqual(dims[2].opcions.map(o => o.slug), ['knit'])
  // I el seu sufix entra a la composició del codi com qualsevol altre.
  assert.equal(codiProposat(D3, 'X', ['knit']), 'XK')
})

test('un eix declarat SENSE files no fabrica cap columna buida', () => {
  const D0 = { ...D, eixos: [...D.eixos, { clau: 'BUIT', nom_en: 'Empty' }] }
  assert.deepEqual(dimensionsDe(D0).map(d => d.clau), [EIX_POSICIO, EIX_ESTAT])
})

test('l\'eix que es gira en partir un POM és el PRIMER del diccionari, no un literal', () => {
  assert.equal(eixPrincipal(D), EIX_POSICIO)
  const invertit = { ...D, eixos: [D.eixos[1], D.eixos[0]] }
  assert.equal(eixPrincipal(invertit), EIX_ESTAT)
  assert.equal(eixPrincipal(null), null)
})

test('sense diccionari no hi ha cap columna: la taula es pinta igual', () => {
  assert.deepEqual(dimensionsDe(null), [])
  assert.deepEqual(dimensionsDe({}), [])
})

test('el nom de la columna el posa el diccionari, en l\'idioma de qui llegeix', () => {
  const [posicio] = dimensionsDe(D)
  assert.equal(nomEnIdioma(posicio, 'ca'), 'Posició')
  assert.equal(nomEnIdioma(posicio, 'es'), 'Posición')
  assert.equal(nomEnIdioma(posicio, 'en'), 'Position')
  // i18next dona codis com «ca-ES»: es mira el prefix, no la cadena sencera.
  assert.equal(nomEnIdioma(posicio, 'ca-ES'), 'Posició')
  // Un idioma que la fila no porta cau a l'anglès abans que a res buit.
  assert.equal(nomEnIdioma({ nom_en: 'Position' }, 'de'), 'Position')
})

// ── ELS DOS EIXOS DE LA POSICIÓ (Agus, 22-23/08) ────────────────────────────────────────────
// CARA (front · back) i LATERAL (left · right). Dins d'un, excloents; entre ells, combinables.
// Les posicions que no en declaren cap segueixen sent excloents amb tot el seu eix.

test('la FAMÍLIA la diu el diccionari, no aquest fitxer', () => {
  assert.equal(subeixDe(D, 'back'), 'PECA')
  assert.equal(subeixDe(D, 'left'), 'BANDA')
  // 🚨 JA NO HI HA CAP SLUG ORFE. Aquests tres tornaven `''` i per això s'excloïen amb tot:
  // és el que la formació va veure com «els xips són un grup exclusiu».
  assert.equal(subeixDe(D, 'top'), 'VERTICALITAT')
  assert.equal(subeixDe(D, 'cf'), 'LINIA')
  assert.equal(subeixDe(D, 'side'), 'COSTURA')
  assert.equal(subeixDe(D, 'relaxed'), 'ESTAT')
  assert.equal(subeixDe(D, 'sleeve'), '')      // desconegut: no s'inventa
  assert.equal(subeixDe(null, 'back'), '')     // sense diccionari, tampoc
})

test('la clau d\'exclusió és LA FAMÍLIA, i prou', () => {
  assert.equal(clauExclusio(D, 'left'), 'BANDA')
  assert.equal(clauExclusio(D, 'back'), 'PECA')
  assert.equal(clauExclusio(D, 'top'), 'VERTICALITAT')
  assert.equal(clauExclusio(D, 'side'), 'COSTURA')
  assert.equal(clauExclusio(D, 'cf'), 'LINIA')
  assert.equal(clauExclusio(D, 'relaxed'), 'ESTAT')
  assert.equal(clauExclusio(D, 'sleeve'), null)   // desconegut: no es pot dir què rellevaria
})

test('quines etiquetes xoquen: MATEIXA FAMÍLIA, i res més', () => {
  // Dins de família → xoquen. Les SIS famílies, una per una.
  assert.equal(xoquen(D, 'front', 'back'), true)                 // PECA
  assert.equal(xoquen(D, 'left', 'right'), true)                 // BANDA
  assert.equal(xoquen(D, 'top', 'bottom'), true)                 // VERTICALITAT
  assert.equal(xoquen(D, 'side', 'waistband_seam'), true)        // COSTURA
  assert.equal(xoquen(D, 'cf', 'cb'), true)                      // LINIA
  assert.equal(xoquen(D, 'relaxed', 'extended'), true)           // ESTAT
  // Entre famílies → conviuen SEMPRE.
  assert.equal(xoquen(D, 'back', 'left'), false)
  assert.equal(xoquen(D, 'front', 'right'), false)
  assert.equal(xoquen(D, 'left', 'relaxed'), false)
  // 🚨 ELS QUATRE QUE ABANS XOCAVEN I ARA NO: és el símptoma de la formació, dit en assercions.
  assert.equal(xoquen(D, 'top', 'left'), false)
  assert.equal(xoquen(D, 'cf', 'back'), false)     // la LÍNIA no és la PEÇA
  assert.equal(xoquen(D, 'side', 'top'), false)
  assert.equal(xoquen(D, 'waistband_seam', 'left'), false)
  // La redundància és LEGAL: el sistema no fa de policia semàntic.
  assert.equal(xoquen(D, 'front', 'cf'), false)
  // desconegut → no es jutja
  assert.equal(xoquen(D, 'sleeve', 'left'), false)
})

test('l\'ORDRE CANÒNIC SENCER: peça → banda → verticalitat → costura → línia → estat', () => {
  // L'exemple canònic de la llei.
  assert.equal(composaInstancia(D, ['left', 'back']), 'back-left')
  assert.equal(composaInstancia(D, ['back', 'left']), 'back-left')
  // L'estat va SEMPRE l'últim, vingui com vingui.
  assert.equal(composaInstancia(D, ['relaxed', 'left', 'back']), 'back-left-relaxed')
  assert.equal(composaInstancia(D, ['extended', 'top']), 'top-extended')
  // Les sis famílies alhora, en desordre d'entrada: una sola resposta possible.
  assert.equal(
    composaInstancia(D, ['relaxed', 'left', 'back', 'top', 'side', 'cf']),
    'back-left-top-side-cf-relaxed')
  // …i entrades en QUALSEVOL permutació donen el mateix slug: és el que la clau única exigeix.
  assert.equal(
    composaInstancia(D, ['cf', 'side', 'top', 'back', 'left', 'relaxed']),
    'back-left-top-side-cf-relaxed')
})

test('el sufix compost és CARA + LATERAL (FL · FR · BL · BR), no l\'ordre del clic', () => {
  assert.equal(codiProposat(D, 'CH', ['front']), 'CHF')
  assert.equal(codiProposat(D, 'CH', ['back']), 'CHB')
  assert.equal(codiProposat(D, 'CH', ['left']), 'CHL')
  assert.equal(codiProposat(D, 'CH', ['right']), 'CHR')
  assert.equal(codiProposat(D, 'CH', ['front', 'left']), 'CHFL')
  assert.equal(codiProposat(D, 'CH', ['left', 'front']), 'CHFL')   // ← el clic no mana
  assert.equal(codiProposat(D, 'CH', ['front', 'right']), 'CHFR')
  assert.equal(codiProposat(D, 'CH', ['back', 'left']), 'CHBL')
  assert.equal(codiProposat(D, 'CH', ['left', 'back']), 'CHBL')
  assert.equal(codiProposat(D, 'CH', ['back', 'right']), 'CHBR')
})

test('el codi base es recupera d\'un sufix compost, en qualsevol ordre de trams', () => {
  assert.equal(codiBase(D, 'CHBL', ['back', 'left']), 'CH')
  assert.equal(codiBase(D, 'CHBL', ['left', 'back']), 'CH')
  // i amb un estat pel mig, que no compon sufix
  assert.equal(codiBase(D, 'CHBL', ['back', 'left', 'relaxed']), 'CH')
})

test('`bottom` proposa BM: `B` ja només vol dir `back`', () => {
  assert.equal(codiProposat(D, 'CH', ['bottom']), 'CHBM')
  assert.equal(codiProposat(D, 'CH', ['back']), 'CHB')
})
