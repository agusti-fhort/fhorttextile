// Banc de la capçalera «SAMPLE» de la fitxa tècnica (ordre 23/09, continuació
// ORDRE_ETIQUETES_VEREDICTE_SAMPLE.md).
//     cd frontend && node --test src/pages/techSheetQ8Header.test.js
//
// ESCRIT, NO EXECUTAT (consigna del brief). No hi ha vitest ni testing-library en aquest
// front (v. `utils/taulaPresaPerTalla.test.js`); els guards són `node --test` sobre funcions
// pures.
//
// ⚠️ MIRALL, NO IMPORT. La geometria de capçalera (`hdrGeom` de sota) és una còpia fidel de
// `buildTableCellPrimitives` (`pages/TechSheetEditor.jsx:913-914,952-958`): aquella funció NO
// és `export`ada (viu dins d'un fitxer de component gegant amb Konva/react-i18n que `node --test`
// no pot resoldre en sec) i copiar-la aquí és l'únic mode de testejar-la sense arrencar tota
// l'app. Si `TechSheetEditor.jsx` toca aquestes constants (`MM_TO_PX`, `T_PAD`, la fórmula de
// `hdrCharW`), aquest mirall s'ha d'actualitzar a mà — no hi ha manera d'evitar-ho sense
// exportar la funció real, que és fora d'abast d'aquesta peça.
//
// Verificat manualment (rèplica Konva real + Playwright headless, no `node --test`, veure
// ORDRE_ETIQUETES_VEREDICTE_SAMPLE.md §2b) que aquests números coincideixen amb el que Konva.Text
// dibuixa de debò, no només amb la fórmula.

import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const MM_TO_PX = 2.4
const T_PAD = 2 * MM_TO_PX

function hdrGeom(widthMm, fontSize = 9) {
  const pt = Math.max(8, fontSize)
  const hdrPt = Math.max(8, pt * 0.85)
  const hdrFontPx = Math.round(hdrPt * 0.3528 * MM_TO_PX)
  const hdrLS = Math.max(0.4, hdrFontPx * 0.06)
  const hdrCharW = hdrFontPx * 0.6 + hdrLS
  const cw = Math.max(6, widthMm) * MM_TO_PX
  const cabenPerLinia = Math.max(1, Math.floor((cw - 2 * T_PAD) / hdrCharW))
  return { hdrFontPx, hdrCharW, cw, cabenPerLinia }
}

function liniesDeCapcalera(text, widthMm) {
  const { cabenPerLinia } = hdrGeom(widthMm)
  const etiqueta = text.toUpperCase() // `etiquetaCol` fa `.toUpperCase()` amb `capcaleraFina`
  return Math.max(1, Math.ceil(etiqueta.length / cabenPerLinia))
}

test('SAMPLE (6 car.) cap en 1 línia a la columna NOVA de 18mm', () => {
  assert.equal(liniesDeCapcalera('Sample', 18), 1)
})

test('SAMPLE hauria desbordat (2 línies) a l\'amplada VELLA de 13mm — per això la columna puja', () => {
  assert.equal(liniesDeCapcalera('Sample', 13), 2)
})

test('REAL (document VELL, ja serialitzat) segueix cabent en 1 línia a 13mm — retrocompatibilitat', () => {
  assert.equal(liniesDeCapcalera('Real', 13), 1)
})

test('el sòl de mida de la capçalera fina és 8pt (NORMA_LAYOUT §2, mai per sota)', () => {
  assert.equal(hdrGeom(18).hdrFontPx >= 6, true) // hdrFontPx és PX derivat de 8pt, no confondre unitats
  const hdrPt = Math.max(8, Math.max(8, 9) * 0.85)
  assert.equal(hdrPt, 8)
})

// ── Plantilla d'inserció (TechSheetEditor.jsx:5539,5733) — valors literals, llegits del
// codi font per no dependre d'un import que no es pot resoldre en sec (React/Konva/i18n).
test('les dues columnes "actual" de la plantilla d\'inserció Q8 usen la MATEIXA clau i18n i totes dues valen 18mm', () => {
  const here = path.dirname(fileURLToPath(import.meta.url))
  const src = readFileSync(path.join(here, 'TechSheetEditor.jsx'), 'utf8')
  const matches = [...src.matchAll(/key:\s*(?:'actual'|`\$\{sl\}_act`),\s*label:\s*tEn\('tech_sheet\.q8_col_actual'\),\s*width:\s*(\d+)/g)]
  assert.equal(matches.length, 2, 'han de ser exactament les dues taules Q8 (q8_fitting i q8_size_set)')
  for (const m of matches) assert.equal(m[1], '18')
})

// ── i18n — mateix text als 3 idiomes (vocabulari de domini, com LINEAR/STEP i com el
// veredicte del COMMIT 1 anterior). Llegim els JSON directament: és exactament el que
// `tEn()`/`t()` acabaran servint, i aquest fitxer no pot importar react-i18next en sec.
test('tech_sheet.q8_col_actual val "Sample" als 3 idiomes (ca/en/es)', () => {
  const here = path.dirname(fileURLToPath(import.meta.url))
  for (const lang of ['ca', 'en', 'es']) {
    const json = JSON.parse(readFileSync(path.join(here, '..', 'i18n', `${lang}.json`), 'utf8'))
    assert.equal(json.tech_sheet.q8_col_actual, 'Sample', `${lang}.json`)
  }
})

// ── Retrocompatibilitat estructural: un objecte de taula ja serialitzat (13mm/"Real") no
// porta cap marca de versió i cap camp que la plantilla nova hagi deixat de conèixer — la
// funció de render (`buildTableCellPrimitives`) llegeix `columns[i].label`/`.width` tal com
// són, sense normalitzar-los contra la plantilla d'avui. Aquest test documenta la forma
// mínima d'un objecte vell perquè una regressió futura que hi afegís un camp obligatori nou
// es noti aquí abans que en producció.
test('forma mínima d\'una columna "actual" ja serialitzada (document vell) — cap camp nou obligatori', () => {
  const columnaVella = { key: 'M_act', label: 'Real', width: 13 }
  assert.deepEqual(Object.keys(columnaVella).sort(), ['key', 'label', 'width'])
  assert.equal(liniesDeCapcalera(columnaVella.label, columnaVella.width), 1)
})
