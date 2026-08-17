// Q8/QA — LES TRES TAULES DE LA FITXA, contra un PAYLOAD REAL DEL SERVIDOR.
//
//   cd backend && venv/bin/python manage.py test fhort.fitting.test_q8_banc_taules_fitxa --keepdb
//   node ops/qa/q8_taules_fitxa.mjs
//
// El payload NO és escrit a mà: el bolca `test_q8_banc_taules_fitxa.py` passant el banc pel
// serializer de debò. Un payload escrit a mà provaria que el codi fa el que el payload diu, no
// que el servidor el serveixi així — que és precisament la juntura on aquest territori ha
// trencat abans.
//
// Aquí hi corren els mòduls REALS (`taulesQ8.js`, `repartimentTaules.js`, `grupsDelFull.js`).
// El que NO es pot exercir des de node és el builder de primitives, que viu dins de
// `TechSheetEditor.jsx` amb Konva i React a sobre: la seva part comprovable —el sòl de 8pt i el
// tall— es verifica amb els números que ell mateix retorna (`titolH`/`hdrH`/`rowH`), declarats
// aquí com a entrada i contrastats a mà al navegador. Queda dit al report.

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { grupsDelFull } from '../../frontend/src/utils/grupsDelFull.js'
import { ampladaPerTextos, repartimentEnPagines } from '../../frontend/src/utils/repartimentTaules.js'
import { filesFitting, filesGrading, filesNotes, filesSizeSet, filesSizeSetConsolidat } from '../../frontend/src/utils/taulesQ8.js'

const dades = JSON.parse(readFileSync(new URL('./_out/q8_payloads.json', import.meta.url), 'utf8'))
const { grid, peces } = dades
const MARE = 'Base model'

let ok = 0
const prova = (nom, fn) => {
  try { fn(); ok += 1; console.log(`  ✓ ${nom}`) } catch (e) {
    console.error(`  ✗ ${nom}\n    ${e.message}`); process.exitCode = 1
  }
}

console.log(`\nQ8 · banc ${dades.model.codi_intern} · base ${dades.model.base_size_label} · run ${dades.model.size_run_model}`)
console.log(`     ${grid.lines.length} línies · ${peces.length} prendes al contracte\n`)

// ── 2 PECES = 2 GRUPS COMPLETS ──────────────────────────────────────────────────────────────
console.log('Q8a · taula de fitting')
const q8a = filesFitting(grid)
const grupsA = grupsDelFull(q8a.files, peces, MARE)

prova('2 peces → 2 grups, la mare primer i amb el nom del contracte', () => {
  assert.equal(grupsA.length, 2)
  assert.deepEqual(grupsA.map(g => g.garment), ['', '02'])
  assert.deepEqual(grupsA.map(g => g.titol), [MARE, 'Short'])
})

prova('cap fila es perd pel camí: la suma dels grups és el total', () => {
  assert.equal(grupsA.reduce((n, g) => n + g.files.length, 0), q8a.files.length)
  assert.equal(q8a.files.length, 6, 'tres POMs × dues prendes, a la talla base')
})

prova('VERMELL on toca: la presa que s\'aparta, i NOMÉS aquella', () => {
  const perCodi = Object.fromEntries(q8a.files.map(f => [`${f.garment}|${f.codi}`, f]))
  const ch = perCodi['|CH']
  assert.equal(ch.aprovada, 50, 'la teòrica de la base')
  assert.equal(ch.actual, 51.5)
  assert.equal(ch.dif, 1.5, '→ Actual en vermell negreta i Dif amb signe')
  const wa = perCodi['|WA']
  assert.equal(wa.dif, 0, 'coincideix → tot en negre')
})

prova('l\'ACTUAL BUIT no és cap alerta: ningú no ha mesurat aquella cel·la', () => {
  // A la talla base totes tres files tenen gest. La que no en té viu a les altres talles.
  const ss = filesSizeSet(grid)
  const hl = ss.files.find(f => f.codi === 'HL' && f.garment === '')
  assert.equal(hl.celles.XS.actual, null, 'existir no és haver mesurat')
  assert.equal(hl.celles.XS.dif, null, 'i la Dif no s\'inventa un 0')
})

prova('els tres veredictes surten sencers i sense traduir (dada de domini)', () => {
  const v = q8a.files.filter(f => f.garment === '').map(f => f.veredicte).sort()
  assert.deepEqual(v, ['ACCEPTED', 'ADJUSTED', 'REJECTED'])
})

// ── Q8b · GRADING ───────────────────────────────────────────────────────────────────────────
console.log('\nQ8b · taula d\'escalat')
// El payload de `taula-mesures` es reconstrueix des del mateix banc: el que Q8b necessita
// (règim + `graded` + `garment`) hi és tot, i el que aquí es prova és el constructor.
const talles = dades.model.size_run_model.split('·')
const rowsTM = q8a.files.map(f => ({
  pom_id: f.pom_id, capa: '', instancia: '', garment: f.garment,
  pom_code: f.codi, nom_en: f.nom_en, nom_ca: f.nom_local,
  base_value_cm: f.aprovada, graded: {}, logica: 'LINEAR', increment_base: 2,
  increment_break: null, talla_break_label: null,
}))
const q8b = filesGrading(rowsTM, talles, dades.model.base_size_label)

prova('Rule i Δ hi són a totes les files, i la corba porta totes les talles', () => {
  assert.ok(q8b.every(f => f.regla === 'LINEAR' && f.delta === 2))
  assert.ok(q8b.every(f => Object.keys(f.valors).length === talles.length))
})

prova('la BASE surt de `base_value_cm`, no de `graded` (criteri de l\'Escalat)', () => {
  const ch = q8b.find(f => f.codi === 'CH' && f.garment === '')
  assert.equal(ch.valors.S, 50)
  assert.equal(ch.valors.XS, null, 'sense spec, forat visible i no un 0')
})

prova('l\'escalat també es reparteix en 2 grups', () => {
  assert.equal(grupsDelFull(q8b, peces, MARE).length, 2)
})

// ── Q8c · SIZE SET + notes ──────────────────────────────────────────────────────────────────
console.log('\nQ8c · size set i notes')
const q8c = filesSizeSet(grid)

prova('una cel·la per talla del run i per fila, sense forats a l\'estructura', () => {
  assert.deepEqual(q8c.talles, talles)
  assert.ok(q8c.files.every(f => Object.keys(f.celles).length === talles.length))
})

prova('R2 · VEREDICTE NOMÉS A LA BASE', () => {
  const amb = q8c.files.flatMap(f => talles.filter(s => f.celles[s].veredicte))
  assert.ok(amb.every(s => s === dades.model.base_size_label),
    `veredicte fora de la base: ${[...new Set(amb)]}`)
})

prova('les NOTES van a part i només hi entren les files que en tenen', () => {
  const n = filesNotes(grid)
  // El banc dona nota a CH i a WA, i tots dos POMs viuen a les DUES prendes → 4 files de 6.
  // Les de `HL` no en porten cap i no hi han de sortir: una columna de guions no és informació.
  assert.equal(n.files.length, 4)
  assert.ok(n.files.every(f => f.nota))
  assert.equal(grupsDelFull(n.files, peces, MARE).length, 2, 'i també es reparteix per peça')
})

// ── EL SALT DE PÀGINA ───────────────────────────────────────────────────────────────────────
// Geometria REAL del builder a 9pt (`buildTableCellPrimitives`, mesurada als seus retorns):
// fila 1 línia ≈ 3.7 mm · fila 2 línies ≈ 7.0 mm · capçalera 1 línia ≈ 4.8 mm · títol ≈ 5.9 mm.
console.log('\nSalt de pàgina (A4 vertical: cos útil 14→287)')
const GEO = { hTitol: 5.9, hCapcalera: 4.8, hFila: 7.0 }
let tallLlarg = []
const PAG = { yInici: 14, yFinal: 287, separacio: 6 }

prova('el grup de 2 peces del banc cap sencer a UNA pàgina', () => {
  const r = repartimentEnPagines(grupsA.map(g => ({ ...GEO, nFiles: g.files.length })), PAG)
  assert.equal(r.length, 2)
  assert.ok(r.every(t => t.pagina === 0))
})

prova('amb 120 files per peça es parteix, CAP FILA TALLADA i la capçalera es repeteix', () => {
  const r = repartimentEnPagines([{ ...GEO, nFiles: 120 }, { ...GEO, nFiles: 120 }], PAG)
  const perTaula = [0, 1].map(i => r.filter(t => t.taula === i))
  perTaula.forEach(ts => {
    assert.equal(ts[0].ini, 0)
    assert.equal(ts[ts.length - 1].fi, 120, 'no s\'ha perdut cap fila')
    ts.slice(1).forEach((t, i) => assert.equal(t.ini, ts[i].fi, 'ni se n\'ha duplicat cap'))
  })
  // Cada tros és un objecte `table` complet → torna a pagar títol + capçalera, i per tant les
  // repeteix. Que n'hi hagi més d'un per taula és el que ho demostra.
  assert.ok(r.length > 2, `s'esperava partició; trossos=${r.length}`)
  tallLlarg = r
})

console.log(`      → 240 files = ${tallLlarg.length} trossos en ${Math.max(...tallLlarg.map(t => t.pagina)) + 1} pàgines, cap fila partida`)

// ── Q8-bis · LES CORRECCIONS DE LA QA D'AGUS ────────────────────────────────────────────────
console.log('\nQ8-bis · B0 · el size set sense cap sessió tancada')

prova('B0 · amb l\'escalat tancat i cap sessió, el size set SURT amb la corba del model', () => {
  const ss = filesSizeSetConsolidat(rowsTM, talles, dades.model.base_size_label)
  assert.equal(ss.files.length, rowsTM.length, 'cap fila es perd per no tenir preses')
  assert.deepEqual(ss.talles, talles)
  // La corba hi és; el que hi falta és la PRESA, i es veu que hi falta.
  const ch = ss.files.find(f => f.codi === 'CH' && f.garment === '')
  assert.equal(ch.celles.S.teorica, 50)
  assert.equal(ch.celles.S.actual, null)
  assert.equal(ch.celles.S.veredicte, '')
})

prova('B0 · i també es reparteix en 2 grups: la peça no depèn de cap sessió', () => {
  const ss = filesSizeSetConsolidat(rowsTM, talles, dades.model.base_size_label)
  assert.equal(grupsDelFull(ss.files, peces, MARE).length, 2)
})

console.log('\nQ8-bis · C2 · alçades reals per fila')
// Geometria real del builder a 9pt: fila d'1 línia ≈ 3,7 mm · de 2 línies ≈ 7,0 mm.
const H1 = 3.7
const H2 = 7.0

prova('C2 · una sola fila de 2 línies ja NO infla les altres', () => {
  const nFiles = 60
  const hFiles = [H2, ...Array(nFiles - 1).fill(H1)]     // una de doble, la resta compactes
  const real = repartimentEnPagines([{ ...GEO, hFiles, nFiles }], PAG)
  const antic = repartimentEnPagines([{ ...GEO, hFila: H2, nFiles }], PAG)  // el màxim de la taula
  assert.ok(real[0].fi > antic[0].fi,
    `real=${real[0].fi} files a la 1a pàgina vs ${antic[0].fi} amb el màxim`)
  console.log(`      → 1a pàgina: ${real[0].fi} files amb alçada real · ${antic[0].fi} amb el màxim antic`)
  assert.equal(real[real.length - 1].fi, nFiles, 'i cap fila es perd')
})

// ── C4 · APAÏSAT I SÒL DE 8pt ───────────────────────────────────────────────────────────────
// La decisió que fa l'editor: el format més ESTRET on la taula hi cap sense escalar, provant
// primer l'apaïsat del mateix paper. I l'escala mai per sota de 8/9.
console.log('\nQ8-bis · C4 · apaïsat i sòl de 8pt')
const MARGE = 10
const FORMATS = { A4P: 210, A4L: 297, A3L: 420, A3P: 297 }
const ESCALA_MINIMA = 8 / 9
const formatQueHiCap = (w) => ['A4L', 'A3L', 'A3P'].find(k => FORMATS[k] - 2 * MARGE >= w) || null

const CHAR_MM = 3.175 * 0.6
const noms = q8a.files.map(f => f.nom_en)
const wPom = ampladaPerTextos(noms, { charMm: CHAR_MM, padMm: 4, minMm: 34, maxMm: 62 })

prova('el nom més llarg cap en 2 línies a l\'amplada calculada', () => {
  const llarg = Math.max(...noms.map(s => s.length))
  const perLinia = Math.floor((wPom - 4) / CHAR_MM)
  assert.ok(Math.ceil(llarg / perLinia) <= 2,
    `«${noms.find(s => s.length === llarg)}» (${llarg} car.) no hi cap en 2 línies a ${wPom.toFixed(1)} mm`)
  console.log(`      → columna POM ${wPom.toFixed(1)} mm per a «${noms.find(s => s.length === llarg)}»`)
})

const ample = (cols) => cols.reduce((a, b) => a + b, 0)
// El cas que va destapar C4: el size set amb CINC talles, no amb les tres del banc.
const CINC = ['XXS', 'XS', 'S', 'M', 'L']
const casos = [
  ['Q8a fitting', ample([16, wPom, 18, 18, 16, 22, 52])],
  ['Q8b grading (3 talles)', ample([16, wPom, 18, 14, 14, 18, ...talles.map(() => 14)])],
  ['Q8c size set (3 talles)', ample([16, wPom, ...talles.flatMap(() => [13, 13, 12]), 22])],
  ['Q8c size set (5 talles)', ample([16, wPom, ...CINC.flatMap(() => [13, 13, 12]), 22])],
]
for (const [nom, w] of casos) {
  const capA4P = w <= FORMATS.A4P - 2 * MARGE
  const fmtKey = capA4P ? 'A4P' : formatQueHiCap(w)
  const ampleUtil = FORMATS[fmtKey] - 2 * MARGE
  const escala = Math.min(1, Math.max(ESCALA_MINIMA, ampleUtil / w))
  const pt = 9 * escala
  console.log(`      ${nom}: ${w.toFixed(0)} mm → ${fmtKey} · ${pt.toFixed(1)}pt${capA4P ? '' : ' (apaïsat + avís)'}`)
  prova(`${nom}: el format triat el fa cabre i MAI baixa de 8pt`, () => {
    assert.ok(pt >= 8, `${pt.toFixed(2)}pt`)
    assert.ok(w <= ampleUtil / ESCALA_MINIMA, 'ni amb el sòl no hi cabria')
  })
}

prova('C4 · el size set de 5 talles NO cap en A4 vertical: és el cas que obliga l\'apaïsat', () => {
  const w = casos[3][1]
  assert.ok(w > FORMATS.A4P - 2 * MARGE, `${w} mm hi cabria i llavors C4 no caldria`)
  assert.equal(formatQueHiCap(w), 'A4L', 'i el full més estret que hi cap és l\'A4 apaïsat')
  // La prova que C4 existeix per al sòl: en vertical, sense canviar de full, cauria sota 8pt.
  const ptVertical = 9 * Math.min(1, (FORMATS.A4P - 2 * MARGE) / w)
  assert.ok(ptVertical < 8, `en vertical serien ${ptVertical.toFixed(1)}pt`)
  console.log(`      → en A4 vertical serien ${ptVertical.toFixed(1)}pt; per això canvia de full`)
})

console.log(`\n${ok} proves verdes${process.exitCode ? ' — I ALGUNA DE VERMELLA' : ''}\n`)
