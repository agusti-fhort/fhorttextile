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
import { ampladaPerTextos, repartimentEnPagines, trossosDeTalles } from '../../frontend/src/utils/repartimentTaules.js'
import { filesFitting, filesGrading, filesNotes, filesSizeSet, filesSizeSetConsolidat, liniesBreakQ8 } from '../../frontend/src/utils/taulesQ8.js'

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

prova('T1 · la mesura INTACTA d\'una sessió tancada porta Actual: va arribar clavada', () => {
  const ss = filesSizeSet(grid)
  const hl = ss.files.find(f => f.codi === 'HL' && f.garment === '')
  assert.equal(hl.celles.XS.actual, hl.celles.XS.teorica, 'la columna no pot quedar mig buida')
  assert.equal(hl.celles.XS.dif, 0, 'i qui pinta deixarà el zero en blanc')
})

prova('T1 · cap fila de la talla base es queda sense Actual', () => {
  assert.ok(q8a.files.every(f => f.actual != null),
    `sense Actual: ${q8a.files.filter(f => f.actual == null).map(f => f.codi)}`)
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

// ── F4-QUATER · LA COLUMNA «BREAKS» DE LA FITXA, DE PUNTA A PUNTA ───────────────────────────
//
// 🚨 EL QUE AQUEST BLOC GUARDA ÉS LA JUNTURA, no la frase (que ja té banc a `taulesQ8.test.js`).
// `filesGrading` REBATEJA els camps de la regla —`logica`→`regla`, `increment_base`→`delta`,
// `increment_break`→`delta_break`, `talla_break_label`→`talla_break`— i `fraseBreakQ8` els ha de
// tornar a traduir. Si algú desfés aquella correspondència, la fitxa sortiria SENSE CAP RELLEU i
// tot seguiria verd: el build compila, el banc de motor no mira dibuixos i la taula s'imprimiria
// igual. Per això la cadena es prova SENCERA i sobre la sortida real del constructor, mai sobre
// una fila escrita a mà que ja tingués els noms bons.
const _cm = (v) => Number(v).toFixed(1)
const _q8bRelleu = (extra) => filesGrading(
  [{ ...rowsTM[0], ...extra }], talles, dades.model.base_size_label)[0]

prova('F4-QUATER · el break LLEGAT arriba a la columna de la fitxa (i en convenció de MOTOR)', () => {
  // ⚠️ EL RUN DEL BANC ÉS `XS·S·M` (tres talles), no el de cinc dels altres fums: el break
  // desat a `S` fa que el motor gradui `S..M`, i la frase ha de dir `S→M` — l'última talla del
  // run, sigui quina sigui. Escriure-hi `M→XL` de memòria hauria estat provar un altre banc.
  const f = _q8bRelleu({ increment_break: 3, talla_break_label: 'S' })
  assert.equal(f.delta_break, 3, 'el constructor el rebateja a `delta_break`')
  assert.equal(f.talla_break, 'S', '…i a `talla_break`, CRU')
  assert.deepEqual(liniesBreakQ8(f, talles, _cm), ['S→M +3.0'],
    'si això surt buit, la traducció de noms de camp de `liniesBreakQ8` s\'ha trencat')
})

prova('F4-QUATER · els INTERVALS explícits hi arriben TOTS, un per línia', () => {
  const f = _q8bRelleu({ breaks: [
    { inici: 'XS', final: 'XS', delta: 3 },
    { inici: 'S', final: 'M', delta: 4 }] })
  // 🚨 CAP COMPTADOR: dos trams, dues línies, i el d'una talla sola SENSE fletxa.
  assert.deepEqual(liniesBreakQ8(f, talles, _cm), ['XS +3.0', 'S→M +4.0'],
    'un `+N` de sobrant aquí és el defecte que va fer llegir una fitxa congelada com a incoherent')
})

prova('F4-QUATER · REGLA DEL SILENCI: la fitxa no imprimeix el que no mana', () => {
  assert.deepEqual(liniesBreakQ8(_q8bRelleu({}), talles, _cm), [], 'sense relleu, res')
  assert.deepEqual(
    liniesBreakQ8(_q8bRelleu({ logica: 'FIXED', increment_base: 0, increment_break: 0,
      talla_break_label: 'S' }), talles, _cm),
    [], 'un FIXED amb residu llegat no gradua i no diu res')
  assert.deepEqual(
    liniesBreakQ8(_q8bRelleu({ increment_break: 2, talla_break_label: 'S' }), talles, _cm),
    [], 'un llegat que repeteix el Δ general (2) no és un trencament')
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

prova('T3 · el constructor segueix sabent el veredicte, però la TAULA ja no el pinta', () => {
  // La dada no desapareix del model —la taula de fitting la necessita—; el que canvia és què
  // n'ensenya el size set, que és INFORMATIU. R2 segueix valent al constructor.
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
console.log('\nQ8-ter · T3 · sostre A4, partició per talles i sòl de 8pt')
const MARGE = 10
// T3 — el sostre és l'A4 APAÏSAT i l'A3 ha sortit de la tria automàtica: la fitxa s'imprimeix en
// A4 i un full que ningú no pot imprimir no és un document.
const FORMATS = { A4P: 210, A4L: 297 }
const AMPLE_UTIL_MAX = 270

const CHAR_MM = 3.175 * 0.6
const noms = q8a.files.map(f => f.nom_en)
const wPom = ampladaPerTextos(noms, { charMm: CHAR_MM, padMm: 4, minMm: 34, maxMm: 62 })
// H-bis/3 — LA COLUMNA DE NOMENCLATURA, que ara la porten LES CINC taules. Una sola línia (un
// codi partit deixa de servir per trobar la fila d'un cop d'ull) i sostre per als àlies llargs.
const wCodi = ampladaPerTextos(q8a.files.map(f => f.codi), {
  charMm: CHAR_MM, padMm: 4, minMm: 14, maxMm: 30, linies: 1,
})

// M1/M2 — la mateixa aritmètica que el builder: monoespaiada, cos de capçalera 8pt (el sòl),
// tracking inclòs. Serveix per saber si una capçalera parteix en dues línies, que és el que fa
// créixer TOTA la taula (l'alçada la mana el títol de columna més alt).
const MM_TO_PX_Q8 = 2.4
const HDR_PX = Math.round(8 * 0.3528 * MM_TO_PX_Q8)
const HDR_CHAR_MM = (HDR_PX * 0.6 + Math.max(0.4, HDR_PX * 0.06)) / MM_TO_PX_Q8
const liniesCapcalera = (etiqueta, wMm) => {
  const caben = Math.max(1, Math.floor((wMm - 4) / HDR_CHAR_MM))
  return Math.max(1, Math.ceil(etiqueta.length / caben))
}

prova('M1 · «REAL» cap a UNA línia a la columna de 13 mm del size set; «ACTUAL» no hi cabia', () => {
  assert.equal(liniesCapcalera('REAL', 13), 1)
  assert.equal(liniesCapcalera('ACTUAL', 13), 2,
    'si això fos 1, el canvi no hauria calgut i la prova no diria res')
  console.log(`      → capçalera 1,93 mm/car · REAL 1 línia · ACTUAL 2 (i les 14 columnes hi creixien)`)
})

prova('M1 · cap capçalera de les taules Q8 parteix en dues línies', () => {
  const cols = [
    ['LAYER', 16], ['POM', wCodi], ['NAME', wPom], ['REAL', 18], ['REAL', 13], ['DIFF', 16],
    ['VERDICT', 22], ['NOTES', 52], ['RULE', 18], ['Δ', 14], ['BREAK', 14], ['B. SIZE', 18],
  ]
  const parteixen = cols.filter(([et, w]) => liniesCapcalera(et, w) > 1)
  assert.deepEqual(parteixen, [], `parteixen: ${JSON.stringify(parteixen)}`)
})

prova('el nom més llarg cap en 2 línies a l\'amplada calculada', () => {
  const llarg = Math.max(...noms.map(s => s.length))
  const perLinia = Math.floor((wPom - 4) / CHAR_MM)
  assert.ok(Math.ceil(llarg / perLinia) <= 2,
    `«${noms.find(s => s.length === llarg)}» (${llarg} car.) no hi cap en 2 línies a ${wPom.toFixed(1)} mm`)
  console.log(`      → columna POM ${wPom.toFixed(1)} mm per a «${noms.find(s => s.length === llarg)}»`)
})

const ample = (cols) => cols.reduce((a, b) => a + b, 0)
const CINC = ['XXS', 'XS', 'S', 'M', 'L']
// T3 — el size set ha passat de TRES columnes per talla a DUES (teòrica · Actual), i han caigut
// la Dif i el Verdict. Aquesta és l'aritmètica que decideix si cal apaïsat.
// H-bis/3 — i totes tres porten ara LAYER · POM · NAME al davant, no LAYER · POM.
const casos = [
  ['Q8a fitting', ample([16, wCodi, wPom, 18, 18, 16, 22, 52])],
  // F4-QUATER — `Break`(14) + `B.Size`(18) han passat a una sola «Breaks»(26): −6 mm.
  ['Q8b grading (5 talles)', ample([16, wCodi, wPom, 18, 14, 26, ...CINC.map(() => 14)])],
  ['Q8c size set (5 talles)', ample([16, wCodi, wPom, ...CINC.flatMap(() => [13, 13])])],
]
for (const [nom, w] of casos) {
  const capA4P = w <= FORMATS.A4P - 2 * MARGE
  const fmtKey = capA4P ? 'A4P' : (w <= AMPLE_UTIL_MAX ? 'A4L' : null)
  const pt = 9 * Math.min(1, (fmtKey ? FORMATS[fmtKey] - 2 * MARGE : AMPLE_UTIL_MAX) / w)
  console.log(`      ${nom}: ${w.toFixed(0)} mm → ${fmtKey || 'PARTICIÓ'} · ${pt.toFixed(1)}pt`)
  prova(`${nom}: ≥ 8pt i sense pujar d'A4`, () => {
    assert.ok(pt >= 8, `${pt.toFixed(2)}pt`)
    assert.ok(fmtKey === 'A4P' || fmtKey === 'A4L', `ha triat ${fmtKey}`)
  })
}

prova('M2 · el rètol (data · nom · unitat) cap a l\'amplada de la taula més estreta', () => {
  // Cos normal 9pt per a data i nom; la unitat va a 0,8 del cos.
  const cosMm = (9 * 0.3528 * MM_TO_PX_Q8 * 0.6) / MM_TO_PX_Q8
  const subMm = cosMm * 0.8
  const rotul = '18/08/2026 · Fitting Notes'
  const unitat = 'Measurements in inches'
  const need = rotul.length * cosMm + unitat.length * subMm + 8
  const mesEstreta = Math.min(...casos.map(([, w]) => w))
  assert.ok(need <= mesEstreta, `el rètol demana ${need.toFixed(0)} mm i la taula més estreta en fa ${mesEstreta}`)
  console.log(`      → rètol més llarg ${need.toFixed(0)} mm · taula més estreta ${mesEstreta} mm`)
})

// 🚨 H-bis/3 — AQUESTA PROVA DEIA EL CONTRARI I S'HA HAGUT DE REESCRIURE, que és exactament el
// que ha de passar quan una decisió en substitueix una altra. T3 (18/08) va guanyar l'A4 VERTICAL
// per al run de cinc traient la Dif i el Verdict del size set; l'ordre del 21/08 hi torna a posar
// una columna —la NOMENCLATURA, que hi faltava a totes— i els mil·límetres se'n tornen.
//
// No és una regressió silenciosa: és el fallback SANCIONAT de T3 (apaïsat abans que encongir, i
// mai A3). El que la prova gasta és que segueixi dins del sostre i per damunt del sòl de 8pt.
// Si algun dia s'ha de recuperar el vertical, el mil·límetre és de la columna del NOM, no del codi.
prova('H-bis · el run de 5 amb nomenclatura baixa a l\'APAÏSAT, dins del sostre i sobre el sòl', () => {
  const w = casos[2][1]
  const sensCodi = w - wCodi
  assert.ok(sensCodi <= FORMATS.A4P - 2 * MARGE, 'sense la columna de codi hi cabia (era la T3)')
  assert.ok(w <= AMPLE_UTIL_MAX, `${w} mm se surt fins i tot de l'apaïsat`)
  assert.ok(9 * Math.min(1, (FORMATS.A4L - 2 * MARGE) / w) >= 8, 'per sota del sòl de 8pt')
  console.log(`      → size set de 5 talles: ${sensCodi.toFixed(0)} mm sense codi (A4P) · ${w.toFixed(0)} mm amb codi (A4L)`)
})

prova('T3 · el que no cap ni en A4 apaïsat es parteix per TALLES, no puja de paper', () => {
  // Un run de 20 talles: 16 + wCodi + wPom fixos, 26 mm per talla, sostre 270.
  const bandes = trossosDeTalles(20, 16 + wCodi + wPom, 26, AMPLE_UTIL_MAX)
  assert.ok(bandes.length > 1, 'hauria de partir')
  assert.equal(bandes[0][0], 0)
  assert.equal(bandes[bandes.length - 1][1], 20, 'cap talla es perd')
  bandes.slice(1).forEach((b, i) => assert.equal(b[0], bandes[i][1], 'ni se\'n repeteix cap'))
  const ampleBanda = 16 + wCodi + wPom + (bandes[0][1] - bandes[0][0]) * 26
  assert.ok(ampleBanda <= AMPLE_UTIL_MAX, `${ampleBanda} mm se surt del sostre`)
  console.log(`      → 20 talles = ${bandes.length} bandes de ${bandes[0][1]} · ${ampleBanda.toFixed(0)} mm cadascuna`)
})

console.log(`\n${ok} proves verdes${process.exitCode ? ' — I ALGUNA DE VERMELLA' : ''}\n`)
