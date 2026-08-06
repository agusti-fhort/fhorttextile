import test from 'node:test'
import assert from 'node:assert/strict'

import { ordenaPerProximitat, proximitatCapa, PROP } from './proximitatRun.js'

// Runs REALS de `fhort` (SELECT del 06/08, després de la classificació de N1). Els 4 canònics
// que la casa fa servir de debò + el «BRW Run 01», que és el run de client de Brownie.
// Les 3 capes noves (construccio/fit/grup) van BUIDES perquè avui cap run les té informades:
// aquest és l'estat de sortida i el test l'ha de fixar, no dissimular-lo.
const ALPHA_EU_W = { id: 29, codi: 'ALPHA_EU_W', nom: 'Alpha EU — Women', tipus_escala: 'ALPHA', target_codis: ['WOMAN'], customer_codi: '', construccio_codis: [], fit_codis: [], grup_codis: [] }
const ALPHA_EU_M = { id: 30, codi: 'ALPHA_EU_M', nom: 'Alpha EU — Men', tipus_escala: 'ALPHA', target_codis: ['MAN'], customer_codi: '', construccio_codis: [], fit_codis: [], grup_codis: [] }
const NUMERIC_EU_W = { id: 32, codi: 'NUMERIC_EU_W', nom: 'Numeric EU — Women', tipus_escala: 'NUM', target_codis: ['WOMAN'], customer_codi: '', construccio_codis: [], fit_codis: [], grup_codis: [] }
const BABY_EU_CM = { id: 35, codi: 'BABY_EU_CM', nom: 'Baby EU — cm height', tipus_escala: 'ALTURA', target_codis: ['NEWBORN_GIRL'], customer_codi: '', construccio_codis: [], fit_codis: [], grup_codis: [] }
const BRW_RUN_01 = { id: 53, codi: 'WOMAN_BRW_01', nom: 'Dona ALPHA — Textiles y Confecciones Brownie SL Run 01', tipus_escala: 'ALPHA', target_codis: ['WOMAN'], customer_codi: 'BRW', construccio_codis: [], fit_codis: [], grup_codis: [] }
const WOMAN_LOS_01 = { id: 67, codi: 'WOMAN_LOS_01', nom: 'LOS Woman Alpha XS-3XL', tipus_escala: 'ALPHA', target_codis: ['WOMAN'], customer_codi: 'LOS', construccio_codis: [], fit_codis: [], grup_codis: [] }

const ELS_CINC = [ALPHA_EU_W, ALPHA_EU_M, NUMERIC_EU_W, BABY_EU_CM, BRW_RUN_01]
const codis = (rows) => rows.map(r => r.codi)

// ── LA REGLA: ORDENA, MAI AMAGA ──────────────────────────────────────────────────────────

test('cap run cau de la llista, encara que no encaixi amb res', () => {
  const out = ordenaPerProximitat(ELS_CINC, { target: 'NEWBORN_BOY', construction: 'TECHNICAL', fit: 'BODYCON', grup: 'SWIMWEAR' }, 'XXX')
  assert.equal(out.length, 5)
  assert.deepEqual(new Set(codis(out)), new Set(codis(ELS_CINC)))
})

test('ordenar no muta la llista d’entrada', () => {
  const abans = codis(ELS_CINC)
  ordenaPerProximitat(ELS_CINC, { target: 'MAN' }, 'BRW')
  assert.deepEqual(codis(ELS_CINC), abans)
})

// ── 1a CLAU: EL TARGET ───────────────────────────────────────────────────────────────────

test('el target de la peça mana per damunt de tot', () => {
  const out = codis(ordenaPerProximitat(ELS_CINC, { target: 'MAN' }, null))
  assert.equal(out[0], 'ALPHA_EU_M')
  // Els de WOMAN i NEWBORN_GIRL declaren un ALTRE target: van al final, però hi són.
  assert.ok(out.includes('BABY_EU_CM'))
})

test('un run sense cap target declarat queda AL MIG, no primer ni últim', () => {
  const senseTarget = { codi: 'SENSE', nom: 'Sense target', target_codis: [], customer_codi: '' }
  const out = codis(ordenaPerProximitat([ALPHA_EU_M, senseTarget, ALPHA_EU_W], { target: 'MAN' }, null))
  assert.deepEqual(out, ['ALPHA_EU_M', 'SENSE', 'ALPHA_EU_W'])
})

// ── 2a CLAU: DE QUI ÉS — el run del client del model, primer ──────────────────────────────

test('BRW Run 01 va DAVANT dels canònics quan el model és de Brownie', () => {
  const out = codis(ordenaPerProximitat(ELS_CINC, { target: 'WOMAN' }, 'BRW'))
  assert.equal(out[0], 'WOMAN_BRW_01')
  assert.deepEqual(out.slice(1, 3), ['ALPHA_EU_W', 'NUMERIC_EU_W'])
})

test('el run d’un ALTRE client no s’amaga, però va l’últim dels del seu target', () => {
  const rows = [WOMAN_LOS_01, ALPHA_EU_W, BRW_RUN_01]
  const out = codis(ordenaPerProximitat(rows, { target: 'WOMAN' }, 'BRW'))
  assert.deepEqual(out, ['WOMAN_BRW_01', 'ALPHA_EU_W', 'WOMAN_LOS_01'])
})

test('sense client, els canònics manen i els de client van al final', () => {
  const out = codis(ordenaPerProximitat(ELS_CINC, { target: 'WOMAN' }, null))
  assert.deepEqual(out.slice(0, 2), ['ALPHA_EU_W', 'NUMERIC_EU_W'])
  assert.equal(out[2], 'WOMAN_BRW_01')
})

// ── 3a-5a CLAU: LES CAPES NOVES ──────────────────────────────────────────────────────────

test('amb totes les capes buides (l’estat d’avui) l’ordre no es mou', () => {
  // La garantia de no-regressió: N3 posa el mecanisme, no canvia el que la tècnica veu fins
  // que algú etiqueti un run.
  const ambEixos = codis(ordenaPerProximitat(ELS_CINC, { target: 'WOMAN', construction: 'KNIT', fit: 'SLIM', grup: 'TOPS' }, 'BRW'))
  const nomesTarget = codis(ordenaPerProximitat(ELS_CINC, { target: 'WOMAN' }, 'BRW'))
  assert.deepEqual(ambEixos, nomesTarget)
})

test('la construcció desempata entre dos runs igual de propers', () => {
  const teixit = { ...ALPHA_EU_W, codi: 'A_WOVEN', nom: 'A', construccio_codis: ['WOVEN'] }
  const punt = { ...ALPHA_EU_W, codi: 'B_KNIT', nom: 'B', construccio_codis: ['KNIT'] }
  assert.deepEqual(codis(ordenaPerProximitat([teixit, punt], { target: 'WOMAN', construction: 'KNIT' }, null)),
                   ['B_KNIT', 'A_WOVEN'])
  assert.deepEqual(codis(ordenaPerProximitat([punt, teixit], { target: 'WOMAN', construction: 'WOVEN' }, null)),
                   ['A_WOVEN', 'B_KNIT'])
})

test('el fit i el grup desempaten en aquest ordre, després de la construcció', () => {
  const capaFit = { ...ALPHA_EU_W, codi: 'FIT_OK', nom: 'F', fit_codis: ['SLIM'], grup_codis: ['BOTTOMS'] }
  const capaGrup = { ...ALPHA_EU_W, codi: 'GRUP_OK', nom: 'G', fit_codis: ['OVERSIZED'], grup_codis: ['TOPS'] }
  // El fit va abans que el grup: el que encaixa de fit guanya encara que falli de grup.
  assert.deepEqual(codis(ordenaPerProximitat([capaGrup, capaFit], { target: 'WOMAN', fit: 'SLIM', grup: 'TOPS' }, null)),
                   ['FIT_OK', 'GRUP_OK'])
})

test('l’origen mana per damunt de les 3 capes noves: el run del client no baixa mai', () => {
  // El parany del model 174: un canònic que encaixa amb les 3 capes NO ha de passar davant del
  // run del client. Per això l'origen és la 2a clau i les capes noves són desempats.
  const canonicPerfecte = { ...ALPHA_EU_W, codi: 'CANONIC_PERFECTE', construccio_codis: ['KNIT'], fit_codis: ['SLIM'], grup_codis: ['TOPS'] }
  const out = codis(ordenaPerProximitat([canonicPerfecte, BRW_RUN_01],
                                        { target: 'WOMAN', construction: 'KNIT', fit: 'SLIM', grup: 'TOPS' }, 'BRW'))
  assert.deepEqual(out, ['WOMAN_BRW_01', 'CANONIC_PERFECTE'])
})

// ── LA SEMÀNTICA D'UNA CAPA ──────────────────────────────────────────────────────────────

test('una capa buida és NO DECLARADA, ni universal ni incompatible', () => {
  assert.equal(proximitatCapa([], 'KNIT'), PROP.SENSE)
  assert.equal(proximitatCapa(undefined, 'KNIT'), PROP.SENSE)
  assert.equal(proximitatCapa(['KNIT'], 'KNIT'), PROP.SI)
  assert.equal(proximitatCapa(['WOVEN'], 'KNIT'), PROP.ALTRE)
})

test('un eix que el model no ha triat és NEUTRE per a tothom', () => {
  assert.equal(proximitatCapa([], null), PROP.SI)
  assert.equal(proximitatCapa(['WOVEN'], null), PROP.SI)
  assert.equal(proximitatCapa(['WOVEN'], ''), PROP.SI)
})

// ── ESTABILITAT ──────────────────────────────────────────────────────────────────────────

test('dos runs igual de propers no ballen de posició entre càrregues', () => {
  const a = { codi: 'Z', nom: 'Alpha', target_codis: ['WOMAN'], customer_codi: '' }
  const b = { codi: 'A', nom: 'Beta', target_codis: ['WOMAN'], customer_codi: '' }
  assert.deepEqual(codis(ordenaPerProximitat([a, b], { target: 'WOMAN' }, null)), ['Z', 'A'])
  assert.deepEqual(codis(ordenaPerProximitat([b, a], { target: 'WOMAN' }, null)), ['Z', 'A'])
})
