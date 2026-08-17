// Banc de `taulaPresaPerTalla` — E1/B2.
//     cd frontend && node --test src/utils/taulaPresaPerTalla.test.js
//
// No hi ha vitest ni testing-library en aquest front: els guards són `node --test` sobre
// funcions pures. Per això el constructor viu a `utils/` i no dins d'un `.jsx`.
//
// ⚠️ PRESES SINTÈTIQUES, i està dit a posta. Amb E1/B3 congelat, cap dada viva té encara una
// presa a una talla no-base: el fixture les fabrica sobre la forma del banc QA
// **[QA-SC] BRW-26-SS-0002** (run XS·S·M·L·XL, base M) perquè el constructor s'exerciti amb el
// cas que li toca servir. La forma del payload és la de `PieceFittingGridSerializer.get_lines`.

import test from 'node:test'
import assert from 'node:assert/strict'
import {
  ACCEPTED, REJECTED,
  construeixTaulaPresaPerTalla, liniaTeContingut, tallesDelGrid, valorFinalDeLaCella,
} from './taulaPresaPerTalla.js'
import { agrupaPerGarment } from './garmentFitxa.js'

const RUN = 'XS·S·M·L·XL'
const BASE = 'M'

/** Una línia amb la forma del serializer. Per defecte, SEMBRA: real == teòric, sense gestos. */
const linia = (o) => ({
  id: o.id, pom_id: o.pom_id, capa: o.capa ?? 'exterior', instancia: o.instancia ?? '',
  garment: o.garment ?? '', codi: o.codi ?? 'CH', nom_en: o.nom_en ?? 'Chest width',
  nom_local: o.nom_local ?? 'Ample de pit', nom_fitxa: o.nom_fitxa ?? null,
  bm_id: o.bm_id ?? null, is_key: o.is_key ?? false,
  size_label: o.size_label, valor_teoric: o.valor_teoric,
  valor_real: 'valor_real' in o ? o.valor_real : o.valor_teoric,
  nota: o.nota ?? '', decisio: o.decisio ?? '',
  // E2/B1 — la MARCA del gest. `null` per defecte: la sembra no en posa cap, i és el que
  // fa que una línia acabada de néixer no compti com a mesurada.
  presa_at: o.presa_at ?? null,
})

const grid = (lines, opts = {}) => ({
  model: {
    id: 9002, codi_intern: 'BRW-26-SS-0002',
    size_run_model: opts.run ?? RUN, base_size_label: opts.base ?? BASE,
  },
  lines,
})

/** Corba teòrica del POM 962 al banc QA: +2 per talla des de la base. */
const TEORIC_962 = { XS: 46, S: 48, M: 50, L: 52, XL: 54 }
const linies962 = (extra = {}) =>
  Object.entries(TEORIC_962).map(([sl, v], i) => linia({
    id: 100 + i, pom_id: 962, codi: 'CH', size_label: sl, valor_teoric: v, ...(extra[sl] || {}),
  }))

// ── L'EIX DE TALLA ──────────────────────────────────────────────────────────────────────────

test('les talles surten del run DECLARAT, no de l\'ordre de les línies', () => {
  // Línies desordenades a posta: si manés l'ordre d'aparició, sortiria L·XS·M…
  const g = grid([
    linia({ id: 1, pom_id: 962, size_label: 'L', valor_teoric: 52 }),
    linia({ id: 2, pom_id: 962, size_label: 'XS', valor_teoric: 46 }),
    linia({ id: 3, pom_id: 962, size_label: 'M', valor_teoric: 50 }),
  ])
  assert.deepEqual(tallesDelGrid(g), ['XS', 'S', 'M', 'L', 'XL'])
  assert.deepEqual(construeixTaulaPresaPerTalla(g).talles, ['XS', 'S', 'M', 'L', 'XL'])
})

test('sense run declarat es cau a l\'ordre d\'aparició, mai a l\'alfabètic', () => {
  const g = grid([
    linia({ id: 1, pom_id: 962, size_label: 'L', valor_teoric: 52 }),
    linia({ id: 2, pom_id: 962, size_label: 'XS', valor_teoric: 46 }),
  ], { run: '' })
  assert.deepEqual(tallesDelGrid(g), ['L', 'XS'])
})

test('una talla que el run declarat no conté NO obre columna', () => {
  const g = grid([...linies962(), linia({ id: 9, pom_id: 962, size_label: 'XXL', valor_teoric: 56 })])
  const t = construeixTaulaPresaPerTalla(g)
  assert.equal(t.talles.includes('XXL'), false)
  assert.equal('XXL' in t.files[0].valors, false)
})

// ── LA LLEI QUE EVITA QUE EL FULL MENTEIXI ──────────────────────────────────────────────────

test('LA SEMBRA NO ÉS UNA ARRIBADA: real == teòric i cap gest → arribada null', () => {
  const t = construeixTaulaPresaPerTalla(grid(linies962()))
  for (const sl of t.talles) {
    assert.equal(t.files[0].valors[sl].arribada, null, `talla ${sl}`)
    assert.equal(t.files[0].valors[sl].teorica, TEORIC_962[sl])
  }
})

test('liniaTeContingut: el número que s\'aparta, la nota i el veredicte; res més', () => {
  assert.equal(liniaTeContingut(linia({ id: 1, pom_id: 962, size_label: 'M', valor_teoric: 50 })), false)
  assert.equal(liniaTeContingut(linia({ id: 1, pom_id: 962, size_label: 'M', valor_teoric: 50, valor_real: 50.5 })), true)
  assert.equal(liniaTeContingut(linia({ id: 1, pom_id: 962, size_label: 'M', valor_teoric: 50, nota: 'vora' })), true)
  assert.equal(liniaTeContingut(linia({ id: 1, pom_id: 962, size_label: 'M', valor_teoric: 50, decisio: ACCEPTED })), true)
  // Un real absent no és una presa (i no peta).
  assert.equal(liniaTeContingut(linia({ id: 1, pom_id: 962, size_label: 'M', valor_teoric: 50, valor_real: null })), false)
  assert.equal(liniaTeContingut(null), false)
})

test('E2/B1 · liniaTeContingut: la MARCA de presa mana sobre els números', () => {
  // 🔴 EL CAS QUE ELS NÚMEROS NO PODEN VEURE. Una presa CONFIRMADA tal qual deixa
  // `valor_real === valor_teoric`, que és exactament l'estat del naixement de la línia. Sense
  // `presa_at` el predicat diria false i la fitxa, el Repàs i la Comprovació no comptarien
  // aquesta presa. Bessona de `fitting/esdeveniments.py::linia_te_contingut`.
  const confirmada = linia({
    id: 1, pom_id: 962, size_label: 'M', valor_teoric: 50, valor_real: 50,
    presa_at: '2026-08-17T17:20:00Z',
  })
  assert.equal(liniaTeContingut(confirmada), true,
    'una presa confirmada amb el valor teòric ÉS una presa')

  // El contrapunt, i és la llei d'E1: sense marca i sense res més, la MATEIXA fila no ho és.
  assert.equal(liniaTeContingut(
    linia({ id: 1, pom_id: 962, size_label: 'M', valor_teoric: 50, valor_real: 50 })), false,
    'sense marca, valor_real == valor_teoric segueix sent la sembra')

  // Les files d'abans del camp (`presa_at` absent) es llegeixen com sempre.
  assert.equal(liniaTeContingut(
    linia({ id: 1, pom_id: 962, size_label: 'M', valor_teoric: 50, valor_real: 51 })), true)
})

test('una presa de debò a una talla NO base surt a `arribada`', () => {
  const t = construeixTaulaPresaPerTalla(grid(linies962({ L: { valor_real: 53.4 } })))
  assert.equal(t.files[0].valors.L.arribada, 53.4)
  assert.equal(t.files[0].valors.L.teorica, 52)
})

// ── EL VALOR FINAL — la llei de `consolidate_base_from_fitting`, dita al client ─────────────

test('base amb presa i SENSE veredicte: consolida (el close només exclou el rebuig)', () => {
  const t = construeixTaulaPresaPerTalla(grid(linies962({ M: { valor_real: 51.2 } })))
  assert.equal(t.files[0].valors.M.arribada, 51.2)
  assert.equal(t.files[0].valors.M.final, 51.2)
  assert.equal(t.files[0].valors.M.estat, '')
})

test('REJECTED a la base: l\'arribada es VEU però el final torna a la teòrica', () => {
  const t = construeixTaulaPresaPerTalla(
    grid(linies962({ M: { valor_real: 44, decisio: REJECTED } })))
  assert.equal(t.files[0].valors.M.arribada, 44)
  assert.equal(t.files[0].valors.M.final, 50)
  assert.equal(t.files[0].valors.M.estat, REJECTED)
})

test('presa a talla NO base: es veu, però el final NO l\'adopta (no consolida mai)', () => {
  const t = construeixTaulaPresaPerTalla(
    grid(linies962({ XL: { valor_real: 55.5, decisio: ACCEPTED } })))
  assert.equal(t.files[0].valors.XL.arribada, 55.5)
  assert.equal(t.files[0].valors.XL.final, 54)      // la teòrica: el close descarta la no-base
  assert.equal(t.files[0].valors.XL.estat, ACCEPTED)
})

test('valorFinalDeLaCella és la llei sencera, aïllada', () => {
  const c = (o) => valorFinalDeLaCella({ teorica: 50, arribada: 44, esBase: true, estat: '', ...o })
  assert.equal(c({}), 44)                                  // base + presa → presa
  assert.equal(c({ estat: REJECTED }), 50)                 // rebuig → teòrica
  assert.equal(c({ esBase: false }), 50)                   // no-base → teòrica
  assert.equal(c({ arribada: null }), 50)                  // sense presa → teòrica
})

// ── IDENTITAT: el cas POM 962, viu a la mare i a la 02 ─────────────────────────────────────

test('el MATEIX pom a dues prendes són DUES files, no una', () => {
  const g = grid([
    linia({ id: 1, pom_id: 962, garment: '', size_label: 'M', valor_teoric: 50, valor_real: 51 }),
    linia({ id: 2, pom_id: 962, garment: '02', size_label: 'M', valor_teoric: 30, valor_real: 31 }),
  ])
  const t = construeixTaulaPresaPerTalla(g)
  assert.equal(t.files.length, 2)
  assert.deepEqual(t.files.map(f => f.garment), ['', '02'])
  assert.equal(t.files[0].valors.M.arribada, 51)
  assert.equal(t.files[1].valors.M.arribada, 31)
})

test('capa i instància també separen germanes', () => {
  const g = grid([
    linia({ id: 1, pom_id: 962, capa: 'exterior', size_label: 'M', valor_teoric: 50 }),
    linia({ id: 2, pom_id: 962, capa: 'folre', size_label: 'M', valor_teoric: 48 }),
    linia({ id: 3, pom_id: 962, instancia: 'left', size_label: 'M', valor_teoric: 25 }),
  ])
  assert.equal(construeixTaulaPresaPerTalla(g).files.length, 3)
})

test('les files es parteixen per prenda amb la llei de garmentFitxa, sense adaptador', () => {
  const g = grid([
    linia({ id: 1, pom_id: 962, garment: '', size_label: 'M', valor_teoric: 50 }),
    linia({ id: 2, pom_id: 904, garment: '02', size_label: 'M', valor_teoric: 30 }),
  ])
  const grups = agrupaPerGarment(construeixTaulaPresaPerTalla(g).files)
  assert.deepEqual(grups.map(x => x.garment), ['', '02'])
  assert.equal(grups[0].items.length, 1)
})

// ── FORMA DE LA TAULA ──────────────────────────────────────────────────────────────────────

test('una mesura sense línia en una talla té la cel·la BUIDA, no absent', () => {
  const g = grid([linia({ id: 1, pom_id: 962, size_label: 'M', valor_teoric: 50 })])
  const cel = construeixTaulaPresaPerTalla(g).files[0].valors
  assert.deepEqual(Object.keys(cel), ['XS', 'S', 'M', 'L', 'XL'])
  assert.deepEqual(cel.XS, { teorica: null, arribada: null, final: null, estat: '' })
})

test('AGRUPAR NO ÉS REORDENAR: les files surten en ordre d\'aparició', () => {
  const g = grid([
    linia({ id: 1, pom_id: 904, codi: 'WA', size_label: 'M', valor_teoric: 40 }),
    linia({ id: 2, pom_id: 962, codi: 'CH', size_label: 'M', valor_teoric: 50 }),
    linia({ id: 3, pom_id: 904, codi: 'WA', size_label: 'L', valor_teoric: 42 }),
  ])
  assert.deepEqual(construeixTaulaPresaPerTalla(g).files.map(f => f.codi), ['WA', 'CH'])
})

test('un grid buit no peta i torna una taula buida', () => {
  const t = construeixTaulaPresaPerTalla({})
  assert.deepEqual(t, { base: '', talles: [], files: [] })
})

test('la fila porta la nomenclatura i la PK que el full necessita', () => {
  const g = grid([linia({
    id: 1, pom_id: 962, size_label: 'M', valor_teoric: 50,
    nom_fitxa: 'A', bm_id: 3344, is_key: true,
  })])
  const f = construeixTaulaPresaPerTalla(g).files[0]
  assert.equal(f.nom_fitxa, 'A')
  assert.equal(f.bm_id, 3344)
  assert.equal(f.is_key, true)
  assert.equal(f.codi, 'CH')
  assert.equal(f.nom_en, 'Chest width')
})
