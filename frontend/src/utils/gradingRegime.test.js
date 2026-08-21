// EL MIRALL DEL RÈGIM — i el deute que el TRAM F hi tanca.
//
//     node --test frontend/src/utils/gradingRegime.test.js
//
// `gradingRegime.js` és el mirall de `pom/grading_regime.py`: si els dos deixen de dir el
// mateix, la pantalla dibuixa com a graduada una regla que la porta rebutja (o al revés). El
// cas nou és el defecte 4 de la diagnosi de PROD: `ib=0 · brk=0` amb talla de break informada
// **no gradua res** i es presentava com a LINEAR — una taula plana que sembla graduació.
import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  MAX_BREAKS, effectiveRegime, finalTriables, iniciTriables, intervalNou, intervalsDe,
  intervalsVisibles, isDegenerateLinear, ordenaIntervals, relleuLlegat, relleuResidual, teRelleu,
} from './gradingRegime.js'

test('el sostre és el mateix que el del backend', () => {
  assert.equal(MAX_BREAKS, 3)
})

test('LINEAR+0 sense break segueix sent FIXED (llei A3)', () => {
  assert.equal(effectiveRegime({ logica: 'LINEAR', increment_base: 0 }), 'FIXED')
  assert.equal(effectiveRegime({ logica: 'LINEAR', increment_base: 1.5 }), 'LINEAR')
  assert.equal(effectiveRegime({ logica: 'STEP', increment_base: 0 }), 'STEP')
})

test('🚨 LINEAR amb ib=0, brk=0 i talla de break ÉS FIXED (defecte 4)', () => {
  assert.equal(
    effectiveRegime({ logica: 'LINEAR', increment_base: 0, increment_break: 0, talla_break_label: 'M' }),
    'FIXED')
  assert.equal(
    isDegenerateLinear({ logica: 'LINEAR', increment_base: 0, increment_break: 0, talla_break_label: 'M' }),
    true)
})

test('un sostre a l\'inrevés (0 fins al break, 1.5 després) SÍ que gradua', () => {
  assert.equal(
    effectiveRegime({ logica: 'LINEAR', increment_base: 0, increment_break: 1.5, talla_break_label: 'M' }),
    'LINEAR')
})

test('els intervals compten com a relleu, i els de delta 0 no', () => {
  const ambDelta = { logica: 'LINEAR', increment_base: 0, breaks: [{ inici: 'M', final: 'L', delta: 2 }] }
  const totZero = { logica: 'LINEAR', increment_base: 0, breaks: [{ inici: 'M', final: 'L', delta: 0 }] }
  assert.equal(effectiveRegime(ambDelta), 'LINEAR')
  assert.equal(effectiveRegime(totZero), 'FIXED')
  assert.equal(teRelleu(ambDelta), true)
  assert.equal(teRelleu({ logica: 'LINEAR', increment_base: 2 }), false)
})

test('intervalsDe sempre torna llista (mai null): és camp de fila, com valors_step', () => {
  assert.deepEqual(intervalsDe({ breaks: null }), [])
  assert.deepEqual(intervalsDe(undefined), [])
  assert.deepEqual(intervalsDe({ breaks: [{ inici: 'M', final: 'L', delta: 3 }] }),
    [{ inici: 'M', final: 'L', delta: 3 }])
})

// ── F4-BIS · LA COLUMNA «BREAKS» ─────────────────────────────────────────────────────────────
//
// El banc d'aquesta part fixa DUES coses que, si s'esberlen, no canten a cap build:
//   ① que llegir un break d'1 tram com a interval doni EXACTAMENT el que en diu el motor
//      (`grading_utils.intervals_de`), etiqueta SENSE desplaçar;
//   ② que els selectors no puguin construir un solapament ni un interval del revés — que és
//      el que converteix dues validacions del servidor en impossibilitats de la pantalla.

const RUN = ['XS', 'S', 'M', 'L', 'XL']

test('🔑 un break d\'1 tram es LLEGEIX com l\'interval [label .. última del run]', () => {
  const r = { logica: 'LINEAR', increment_base: 2, increment_break: 3, talla_break_label: 'M' }
  assert.deepEqual(intervalsVisibles(r, RUN),
    [{ inici: 'M', final: 'XL', delta: 3, llegat: true }])
  // 🚨 L'ETIQUETA NO ES DESPLAÇA: la BD desa convenció de MOTOR i el xip la diu tal qual.
  // Amb el desplaçament de document diria «S → XL» i mouria la corba una talla sencera.
  assert.equal(intervalsVisibles(r, RUN)[0].inici, 'M')
  assert.equal(relleuLlegat(r, RUN), true)
})

test('amb les dues formes informades mana `breaks`, i llavors no hi ha llegat', () => {
  const r = {
    logica: 'LINEAR', increment_base: 2, increment_break: 3, talla_break_label: 'M',
    breaks: [{ inici: 'S', final: 'L', delta: 4 }],
  }
  assert.deepEqual(intervalsVisibles(r, RUN), [{ inici: 'S', final: 'L', delta: 4, llegat: false }])
  assert.equal(relleuLlegat(r, RUN), false)
})

// ⚠️ CONTRACTE RETIRAT EL 21/08, i es diu. Aquest test asseia que un `brk=0` amb etiqueta es
// PINTAVA com un interval de delta 0. La regla del silenci ho retira: un tram que repeteix el
// delta que ja mana no diu res i no s'ha de pintar. El que el test protegia de debò —que la
// DADA no es toca i que el MOTOR la segueix llegint igual— es conserva, i és el que fa que
// silenciar-la sigui una decisió de pantalla i no una pèrdua d'informació.
test('brk=0 amb etiqueta: el motor el llegeix, i la pantalla el CALLA', () => {
  const r = { logica: 'LINEAR', increment_base: 0, increment_break: 0, talla_break_label: 'M' }
  assert.deepEqual(intervalsVisibles(r, RUN), [])
  // La dada hi és i ningú l'ha tocada: `teRelleu` la segueix veient, i és el que el motor
  // llegirà (`intervals_de` emet el tram; amb delta 0 dona el mateix valor que el general).
  assert.equal(teRelleu(r), true)
  assert.equal(r.increment_break, 0)
  assert.equal(r.talla_break_label, 'M')
})

test('etiqueta forana o sense run: cap interval (com el motor, que no en troba cap)', () => {
  const r = { logica: 'LINEAR', increment_base: 2, increment_break: 3, talla_break_label: 'XXL' }
  assert.deepEqual(intervalsVisibles(r, RUN), [])
  assert.deepEqual(intervalsVisibles(r, []), [])
  assert.deepEqual(intervalsVisibles({ increment_break: null, talla_break_label: 'M' }, RUN), [])
})

test('🚨 l\'INICI només ofereix talles que cap ALTRE interval cobreix', () => {
  const ivs = [{ inici: 'S', final: 'M', delta: 3 }, { inici: 'XL', final: 'XL', delta: 4 }]
  // Editant el 0: el seu propi tram torna a ser triable, el de l'altre no.
  assert.deepEqual(iniciTriables(ivs, RUN, 0), ['XS', 'S', 'M', 'L'])
  // Un interval NOU (índex fora de la llista): només el que queda lliure de tots dos.
  assert.deepEqual(iniciTriables(ivs, RUN, -1), ['XS', 'L'])
})

test('🚨 el FINAL va des de l\'inici ENDAVANT i s\'atura al primer tram ocupat', () => {
  const ivs = [{ inici: 'S', final: 'M', delta: 3 }, { inici: 'XL', final: 'XL', delta: 4 }]
  // Un nou que comenci a L topa amb XL, ocupat: només s'ofereix L.
  assert.deepEqual(finalTriables(ivs, RUN, -1, 'L'), ['L'])
  // Editant el 0 des de XS: el seu propi tram és lliure i s'arriba fins a L (XL és de l'altre).
  assert.deepEqual(finalTriables(ivs, RUN, 0, 'XS'), ['XS', 'S', 'M', 'L'])
  // Mai cap a enrere: `final ≥ inici` per construcció → cap BREAKS_ORDRE possible.
  assert.equal(finalTriables([], RUN, -1, 'M').includes('S'), false)
  assert.deepEqual(finalTriables([], RUN, -1, 'M'), ['M', 'L', 'XL'])
  assert.deepEqual(finalTriables([], RUN, -1, 'ZZ'), [])
})

test('inici=final és legal i es tria com qualsevol altre (el xip el pinta «XL → XL»)', () => {
  assert.equal(finalTriables([], RUN, -1, 'XL')[0], 'XL')
  assert.deepEqual(finalTriables([], RUN, -1, 'XL'), ['XL'])
})

test('el [+] neix al PRIMER tram lliure i s\'estén fins on arriba; null si no en queda cap', () => {
  assert.deepEqual(intervalNou([], RUN), { inici: 'XS', final: 'XL', delta: null })
  assert.deepEqual(intervalNou([{ inici: 'XS', final: 'S', delta: 1 }], RUN),
    { inici: 'M', final: 'XL', delta: null })
  assert.deepEqual(
    intervalNou([{ inici: 'XS', final: 'S', delta: 1 }, { inici: 'L', final: 'XL', delta: 2 }], RUN),
    { inici: 'M', final: 'M', delta: null })
  assert.equal(intervalNou([{ inici: 'XS', final: 'XL', delta: 1 }], RUN), null)
  assert.equal(intervalNou([], []), null)
})

test('els intervals es pinten ORDENATS, com els desarà `valida_breaks`', () => {
  const desordre = [{ inici: 'XL', final: 'XL', delta: 4 }, { inici: 'XS', final: 'S', delta: 1 }]
  assert.deepEqual(ordenaIntervals(desordre, RUN).map(iv => iv.inici), ['XS', 'XL'])
  // Una etiqueta que no cau al run no es pot situar: va al final i no en desplaça cap.
  const ambForana = [{ inici: 'ZZ', final: 'ZZ', delta: 9 }, { inici: 'M', final: 'L', delta: 2 }]
  assert.deepEqual(ordenaIntervals(ambForana, RUN).map(iv => iv.inici), ['M', 'ZZ'])
})

// ── LA REGLA DEL SILENCI (21/08, del passi visual del banc 1383) ──────────────────────────────
//
// UN XIP NOMÉS ES PINTA SI DIU ALGUNA COSA. El que això fixa no és cosmètic: un xip mut porta
// un ✕ que convida a tocar una fila que no té res a dir, i tocar-la la fa entrar al lot del
// Gravar amb el guard de degenerada al darrere.

test('🚨 sota un règim que no gradua, cap xip (les 8 files FIXED del banc)', () => {
  const fixedAmbResidu = {
    logica: 'FIXED', increment_base: 0, increment_break: 0, talla_break_label: 'M' }
  assert.deepEqual(intervalsVisibles(fixedAmbResidu, RUN), [])
  // I amb intervals residuals de quan era LINEAR, igual: hi són a la BD i no surten a pantalla.
  assert.deepEqual(intervalsVisibles(
    { logica: 'FIXED', increment_base: 0, breaks: [{ inici: 'M', final: 'L', delta: 2 }] },
    RUN), [])
  // STEP també calla — però allà el relleu és LATENT i NO s'ha de netejar (PG-4b-3a).
  assert.deepEqual(intervalsVisibles(
    { logica: 'STEP', increment_base: 0, increment_break: 2, talla_break_label: 'M' }, RUN), [])
})

test('🚨 un break llegat que repeteix el delta general no es pinta', () => {
  // brk 0 sobre general 0: no trenca res.
  assert.deepEqual(intervalsVisibles(
    { logica: 'LINEAR', increment_base: 0, increment_break: 0, talla_break_label: 'M' }, RUN), [])
  // brk 2 sobre general 2: tampoc.
  assert.deepEqual(intervalsVisibles(
    { logica: 'LINEAR', increment_base: 2, increment_break: 2, talla_break_label: 'M' }, RUN), [])
  // brk 2 sobre general 0: SÍ que trenca — és la F del 1383.
  assert.deepEqual(intervalsVisibles(
    { logica: 'LINEAR', increment_base: 0, increment_break: 2, talla_break_label: 'M' }, RUN),
    [{ inici: 'M', final: 'XL', delta: 2, llegat: true }])
})

test('⚠️ el silenci és del LLEGAT: un interval explícit es pinta encara que sembli redundant', () => {
  // La porta el rebutja en néixer (BREAKS_DELTA_REDUNDANT); si malgrat això n'hi ha un a la BD,
  // amagar-lo el faria invisible i inesborrable. Una ⓘ muda no vol dir «no hi ha dada».
  assert.deepEqual(intervalsVisibles(
    { logica: 'LINEAR', increment_base: 0, breaks: [{ inici: 'M', final: 'L', delta: 0 }] }, RUN),
    [{ inici: 'M', final: 'L', delta: 0, llegat: false }])
})

test('🔑 EL CAS F DEL 1383: general 0 + intervals vius NO és degenerada', () => {
  const f = { logica: 'LINEAR', increment_base: 0, increment_break: null, talla_break_label: null,
    breaks: [{ inici: 'M', final: 'L', delta: 2 }, { inici: 'XL', final: 'XL', delta: 3 }] }
  assert.equal(isDegenerateLinear(f), false)
  assert.equal(effectiveRegime(f), 'LINEAR')
  assert.equal(intervalsVisibles(f, RUN).length, 2)
})

test('la llei de degenerada, dita sencera', () => {
  const L = (extra) => ({ logica: 'LINEAR', increment_base: 0, ...extra })
  // general 0 i cap tram viu → degenerada (com sempre)
  assert.equal(isDegenerateLinear(L({})), true)
  // general 0 + qualsevol tram viu → LEGAL
  assert.equal(isDegenerateLinear(L({ breaks: [{ inici: 'M', final: 'L', delta: 2 }] })), false)
  // tot a zero amb breaks informats → degenerada
  assert.equal(isDegenerateLinear(L({ breaks: [{ inici: 'M', final: 'L', delta: 0 }] })), true)
  // la forma VELLA hi compta: brk llegat ≠ 0 la salva (regles no migrades)
  assert.equal(isDegenerateLinear(L({ increment_break: 2, talla_break_label: 'M' })), false)
  assert.equal(isDegenerateLinear(L({ increment_break: 0, talla_break_label: 'M' })), true)
})

test('relleuResidual: què s\'ha de netejar en desar, i què no', () => {
  const relleu = { increment_break: 2, talla_break_label: 'M' }
  assert.equal(relleuResidual({ logica: 'FIXED', ...relleu }), true)
  assert.equal(relleuResidual({ logica: 'ZERO', breaks: [{ inici: 'M', final: 'L', delta: 2 }] }), true)
  // 🚨 MAI SOTA STEP: el relleu hi és LATENT per llei (PG-4b-3a).
  assert.equal(relleuResidual({ logica: 'STEP', ...relleu }), false)
  // Ni sota LINEAR, que és on el relleu MANA.
  assert.equal(relleuResidual({ logica: 'LINEAR', ...relleu }), false)
  // Un FIXED net no té res a netejar.
  assert.equal(relleuResidual({ logica: 'FIXED', increment_base: 0 }), false)
})
