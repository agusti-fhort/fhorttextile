// H-bis · LES COLUMNES D'IDENTITAT DE LES CINC TAULES DE LA FITXA, SOBRE DADES REALES.
//
// Ordre d'Agus del 21/08 sobre les captures del 1383: la nomenclatura va ENTRE la capa i el nom
// a TOTES les taules (LAYER · POM · NOM), Grading i Size Set no en portaven cap, i el codi i el
// nom que s'imprimeixen han de ser els RESIDENTS al model —els que el tècnic veu a Mesures—,
// no els del catàleg que cada payload arrossega pel seu compte.
//
// Aquest banc corre els MÒDULS REALS (`taulesQ8` + `nomenclaturaPom` + `identitatMesura`) sobre
// payloads REALS de staging i diu, fila a fila, què hi ha a les dues columnes d'identitat —abans
// (cada taula resolent del SEU payload) i ara (del resident)—. No mesura la pàgina: d'això se
// n'ocupa `q8_taules_fitxa.mjs`. Mesura QUÈ HI DIU.
//
// Els payloads es bolquen amb (des de `backend/`, read-only):
//   HBIS_MODEL=1383 venv/bin/python manage.py tenant_command shell --schema=fhort \
//     -c "exec(open('scripts_tmp/hbis_dump_payloads.py').read())" | tail -1 > payloads_1383.json
//   HBIS_MODEL=1379 … hbis_dump_grid.py …                                  > grid_1379.json
//
//   node ops/qa/hbis_columnes_fitxa.mjs <payloads_1383.json> [grid_1379.json payloads_1379.json]
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { identitatMesura } from '../../frontend/src/utils/identitatMesura.js'
import { etiquetaInstancia } from '../../frontend/src/utils/capaInstancia.js'
import { nomenclaturaDePom, nomsDePom } from '../../frontend/src/utils/nomenclaturaPom.js'
import {
  filesBase, filesFitting, filesGrading, filesNotes, filesSizeSet,
} from '../../frontend/src/utils/taulesQ8.js'

const [fBase, fGrid, fBase2] = process.argv.slice(2)
const P = JSON.parse(readFileSync(fBase, 'utf8'))

let ok = 0
const prova = (nom, fn) => {
  try { fn(); ok += 1; console.log(`  ✓ ${nom}`) } catch (e) {
    console.error(`  ✗ ${nom}\n    ${e.message}`); process.exitCode = 1
  }
}

// ── EL RESOLUTOR DE LA PÀGINA, TAL COM `TechSheetEditor` el munta ────────────────────────────
// (`residentsQ8` / `residentQ8` / `codiPomQ8` / `nomPomQ8`, sense la instància traduïda, que
// demana el diccionari de la sessió i no canvia ni el codi ni el nom.)
const indexResidents = (pomRows) => {
  const m = new Map()
  for (const bm of pomRows || []) m.set(identitatMesura(bm), bm)
  return m
}
const RES = indexResidents(P.base_measurements.results)
const resident = (f) => RES.get(identitatMesura(f)) || f
const codiARA = (f) => nomenclaturaDePom(resident(f)) || nomenclaturaDePom(f)
// LA INSTÀNCIA VIU DINS DEL NOM, i és el que separa `relaxed` d'`extended` al 1320 —dues files
// del mateix POM, la mateixa capa i el MATEIX codi de client (J1), que sense ella s'imprimirien
// idèntiques i amb xifres diferents (7,0 i 18,0 cm). Sense diccionari de la sessió, `NOM_INSTANCIA`
// dona la mateixa paraula que l'editor pinta; el que el diccionari hi afegeix són sinònims.
const ambInstancia = (f, nom) => {
  const inst = etiquetaInstancia(f.instancia)
  return `${nom}${inst ? ` · ${inst}` : ''}`
}
const nomARA = (f) => ambInstancia(f, nomsDePom(resident(f)).canonic)
const codiABANS = (f) => nomenclaturaDePom(f)
const nomABANS = (f) => ambInstancia(f, nomsDePom(f).canonic)

const taula = (titol, files, teniaCodi) => {
  console.log(`\n── ${titol} · ${files.length} files`)
  console.log(`   ABANS: ${teniaCodi ? 'LAYER · NOM · codi (sense títol, al final)' : 'LAYER · NOM  → CAP NOMENCLATURA'}`)
  console.log('   ARA:   LAYER · POM · NOM')
  for (const f of files.slice(0, 6)) {
    const mv = codiABANS(f) === codiARA(f) && nomABANS(f) === nomARA(f) ? ' ' : '≠'
    console.log(`   ${mv} ${(f.capa || '—').padEnd(9)} | ${String(codiARA(f)).padEnd(6)} | ${nomARA(f)}`
      + (mv === '≠' ? `        (abans: ${codiABANS(f) || '∅'} | ${nomABANS(f) || '∅'})` : ''))
  }
  if (files.length > 6) console.log(`   … ${files.length - 6} files més`)
  // LES FILES ON EL RESIDENT I EL PAYLOAD NO DIUEN EL MATEIX: són la raó de ser d'H-bis/4, i
  // amb dades sense bateig ni àlies n'hi ha ZERO —cosa que també s'ha de poder llegir—.
  const divergents = files.filter(f => codiABANS(f) !== codiARA(f) || nomABANS(f) !== nomARA(f))
  console.log(`   ⇄ ${divergents.length}/${files.length} files on el RESIDENT corregeix el payload`)
  for (const f of divergents.slice(0, 8)) {
    console.log(`     · ${codiABANS(f) || '∅'} | ${nomABANS(f) || '∅'}`)
    console.log(`       →  ${codiARA(f) || '∅'} | ${nomARA(f) || '∅'}`)
  }
  prova(`${titol}: cap cel·la de POM muda i cap de NOM muda`, () => {
    const mutes = files.filter(f => !String(codiARA(f)).trim() || !String(nomARA(f)).trim())
    assert.deepEqual(mutes.map(f => f.identitat), [], 'files amb una columna d\'identitat buida')
  })
  // LES DUES COLUMNES D'IDENTITAT HAN DE DISTINGIR LES FILES, que és per a això que hi són. El
  // 1379 en té tres que es diuen totes «Waist width» i només el codi (B · BB · B1) les separa:
  // sense la columna de nomenclatura, la taula impresa deia tres vegades el mateix.
  prova(`${titol}: cap parell (POM, NOM) repetit dins d'una peça`, () => {
    const vistos = new Map()
    const xocs = []
    for (const f of files) {
      const k = `${f.garment || ''}‖${codiARA(f)}‖${nomARA(f)}`
      if (vistos.has(k)) xocs.push(k); else vistos.set(k, f)
    }
    assert.deepEqual(xocs, [], 'dues files s\'imprimirien exactament igual')
  })
  return files
}

console.log(`\n╔═ H-bis · model ${fBase.split('/').pop().match(/\d{3,}/)?.[0]} · ${P.base_measurements.count} mesures residents`)

// Q8e · BASE — i la tolerància, REVOCADA.
const base = taula('Q8e · MESURES DE TALLA BASE', filesBase(P.base_measurements.results), true)
prova('Q8e · la columna de tolerància ja no arriba ni com a dada', () => {
  assert.ok(base.every(f => !('tol_minus' in f) && !('tol_plus' in f)),
    'el constructor encara emet tol_minus/tol_plus i ningú no els pinta')
})

// Q8b · GRADING — la que no en portava cap.
const talles = P.taula_mesures.size_run || []
const baseLbl = base.length ? null : null
const grad = filesGrading(P.taula_mesures.rows, talles, P.taula_mesures.base_size_label || '')
taula('Q8b · ESCALAT (GRADING)', grad, false)
prova('Q8b · el codi surt del RESIDENT, no de `pom_code` del payload d\'escalat', () => {
  for (const f of grad) {
    const r = resident(f)
    assert.notEqual(r, f, `la fila ${f.identitat} no té resident al model`)
    assert.equal(codiARA(f), nomenclaturaDePom(r))
  }
})

// Q8a/Q8c/Q8c-bis · les que beuen del grid d'una sessió TANCADA.
if (fGrid) {
  const G = JSON.parse(readFileSync(fGrid, 'utf8'))
  const P2 = fBase2 ? JSON.parse(readFileSync(fBase2, 'utf8')) : null
  if (P2) { RES.clear(); for (const [k, v] of indexResidents(P2.base_measurements.results)) RES.set(k, v) }
  console.log(`\n╔═ H-bis · sessió TANCADA ${G.sessio?.id} (${G.sessio?.data}) · ${G.grids.length} peça/es`)
  for (const grid of G.grids) {
    taula(`Q8a · FITTING · peça ${grid.id}`, filesFitting(grid).files, false)
    taula(`Q8c · SIZE SET · peça ${grid.id}`, filesSizeSet(grid).files, false)
    const notes = filesNotes(grid).files
    if (notes.length) taula(`Q8c-bis · NOTES · peça ${grid.id}`, notes, false)
    else console.log(`\n── Q8c-bis · NOTES · peça ${grid.id}: cap línia amb nota (la taula no s'insereix)`)
  }
}

console.log(`\n${ok} proves verdes${process.exitCode ? ' — I ALGUNA DE VERMELLA' : ''}\n`)
