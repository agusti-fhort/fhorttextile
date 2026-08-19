// E3/QA — EL GEST DE LA PRESA NO NAVEGA, i per tant no pot caure al SALT DE SUPERFÍCIE.
//
//   node ops/qa/e3_gest_no_navega.mjs
//
// ── PER QUÈ AIXÒ ÉS UNA PROVA DE TEXT I NO D'EXECUCIÓ ───────────────────────────────────────
// El defecte que vigila (§D2 de `docs/diagnosis/DIAGNOSI_QA_2054_REGRESSIO_O_FORAT.md`) NO viu
// dins de cap funció pura: viu a la JUNTURA entre React Router i un `useEffect`.
// `models/:id/escalat` i `models/:id` munten el MATEIX `ModelSheet`, o sigui que el router
// RECONCILIA en comptes de remuntar; `editing` sobreviu valent 'Escalat', i llavors el salt de
// superfície (`ModelSheet:664-675`) llegeix el canvi de tab com un canvi d'EINA, obre la tasca
// `pom` i aterra a Definició POM. Reproduir-ho de debò vol router + React + el cicle d'efectes,
// i en aquesta casa `node --test` no pot ni importar un `.jsx`.
//
// El que SÍ es pot fixar, i és el que va trencar, és la PRECONDICIÓ: perquè el salt es dispari
// cal que la superfície d'Escalat NAVEGUI cap al tab Mesures. Si no navega, no hi ha salt. La
// guarda és, doncs, exactament tan forta com el fet que vigila, i ni un pèl més.
//
// 🔴 VERMELL PRIMER, mesurat: contra `PropagatedEditor.jsx` a `1b417209^` aquest fitxer falla amb
//    «la superfície d'Escalat NAVEGA a ?tab=Mesures» — hi havia el botó `porta_obrir`.
//    Contra el disc actual, verd.

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'

const ARREL = new URL('../../', import.meta.url)
const llegeix = (rel) => readFileSync(new URL(rel, ARREL), 'utf8')

// Permet apuntar la guarda a una revisió anterior per comprovar que sap dir que NO:
//   node ops/qa/e3_gest_no_navega.mjs 1b417209^
const rev = process.argv[2]
const font = (rel) => (rev
  ? execFileSync('git', ['show', `${rev}:${rel}`], { cwd: new URL('.', ARREL).pathname })
      .toString()
  : llegeix(rel))

let ok = 0
const prova = (nom, fn) => {
  try { fn(); ok += 1; console.log(`  ✓ ${nom}`) } catch (e) {
    console.error(`  ✗ ${nom}\n    ${e.message}`); process.exitCode = 1
  }
}

console.log(`\nE3/QA · el gest de la presa no navega${rev ? ` (rev ${rev})` : ''}`)

const escalat = font('frontend/src/pages/PropagatedEditor.jsx')

prova('la superfície d\'Escalat NO navega a ?tab=Mesures (precondició del salt D2)', () => {
  const navegacions = [...escalat.matchAll(/navigate\s*\(\s*[`'"][^`'"]*/g)].map(m => m[0])
  assert.deepEqual(
    navegacions, [],
    `la superfície d'Escalat NAVEGA: ${navegacions.join(' · ')}. Amb ModelSheet reconciliat, `
    + 'un navigate cap a un altre tab dispara el salt de superfície i aterra a Definició POM.')
})

prova('ni tan sols hi queda el hook de navegació', () => {
  assert.ok(!/useNavigate/.test(escalat),
    'queda `useNavigate` a PropagatedEditor: la porta és a mig tancar i el pròxim que hi passi '
    + 'la trobarà oberta.')
})

prova('el racó NO té cap botó: en tots tres estats és una ETIQUETA', () => {
  // El racó és el `dreta` del SubTabs. Un `<button` allà dins és el defecte tornant.
  const m = escalat.match(/dreta=\{([\s\S]*?)\n\s{10}\}\s*\/>/)
  assert.ok(m, 'no s\'ha trobat el racó (`dreta={...}`) del SubTabs')
  assert.ok(!/<button/.test(m[1]),
    'el racó torna a tenir un botó: el gest de crear la presa és «Mesurar set», no el racó.')
})

prova('el gest viu a ModelSheet i obre la presa SENSE navegar', () => {
  const ms = font('frontend/src/pages/ModelSheet.jsx')
  assert.ok(/measure_set/.test(ms), 'no hi ha el botó «Mesurar set»')
  const crida = ms.match(/enterEdit\('Escalat', 'grading'[^)]*\)/)
  assert.ok(crida, 'el botó no crida enterEdit(\'Escalat\', \'grading\')')
  assert.ok(/obrePresa:\s*true/.test(crida[0]),
    'el botó no demana obrir la presa: sense `obrePresa` només entra en mode edició i la '
    + 'graella es queda de lectura.')
})

prova('🔑 obrir la presa NO penja del parell (tab, code): un ENLLAÇ no pot escriure al domini', () => {
  const ms = font('frontend/src/pages/ModelSheet.jsx')
  // `autoEdit` (ruta /models/:id/escalat, des del Kanban) crida el MATEIX parell sense opcions.
  const auto = ms.match(/enterEdit\(autoEdit,[^)]*\)/)
  assert.ok(auto, 'no s\'ha trobat la crida d\'autoEdit')
  assert.ok(!/obrePresa/.test(auto[0]),
    'la ruta /models/:id/escalat obriria una presa en muntar-se: sessió + peça + N línies '
    + 'nascudes d\'un enllaç. Crear és del GEST; entrar-hi, de la ruta.')
})

console.log(`\n${ok}/5 verd\n`)
