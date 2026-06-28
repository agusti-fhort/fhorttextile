import { useState, useEffect, useCallback, useRef, useMemo, lazy, Suspense } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Stage, Layer, Rect, Text, Line, Arrow, Ellipse, Image as KonvaImage, Transformer, Group, Path } from 'react-konva'
import Konva from 'konva'
import { PDFDocument } from 'pdf-lib'

const PaperFlatEditor = lazy(() => import('./PaperFlatEditor'))

// ════════════════════════════════════════════════════════════════════════════
// TechSheetEditor — TS-1 (motor Konva). Substitueix l'antic editor de maquetació.
//   · Canvas multipàgina A4-horitzontal, format template_json v2 (clau `pages`).
//   · Eines: seleccionar, text (edició inline), imatge (upload/drop/model),
//     rectangle, línia, dibuix lliure, bloc de dades (taula graduada).
//   · Autosave (debounce 2s, només amb lock), lock col·laboratiu, export PDF (pdf-lib).
// El backend (model/serializer/views/urls) NO canvia: template_json és opac i el
// serializer deriva has_content/num_pages de la clau `pages`.
// ════════════════════════════════════════════════════════════════════════════

const API = import.meta.env.VITE_API_URL || ''

// Geometria: A4 horitzontal 297×210mm. Visualització 1mm = 2.4px → 713×504px.
// Constants i helpers compartits amb TechSheetTemplateEditor (TS-3): s'exporten perquè
// el motor de canvas (render de blocs natius) no es dupliqui ni faci drift.
export const MM_TO_PX = 2.4
const A4_W_MM = 297
const A4_H_MM = 210
export const CANVAS_W = Math.round(A4_W_MM * MM_TO_PX)   // 713
export const CANVAS_H = Math.round(A4_H_MM * MM_TO_PX)   // 504
// A4 horitzontal en punts PostScript (pdf-lib). (CANVAS_W/H i PDF_W/H_PT = default A4L.)
export const PDF_W_PT = 841.89
export const PDF_H_PT = 595.28

// Formats de pàgina (TS-4b). Mides en mm + punts PostScript (A4=595.28×841.89, A3=841.89×1190.55).
export const PAGE_FORMATS = {
  A4L: { w: 297, h: 210, pdf: [841.89, 595.28], label: 'A4 ↔' },
  A4P: { w: 210, h: 297, pdf: [595.28, 841.89], label: 'A4 ↕' },
  A3L: { w: 420, h: 297, pdf: [1190.55, 841.89], label: 'A3 ↔' },
  A3P: { w: 297, h: 420, pdf: [841.89, 1190.55], label: 'A3 ↕' },
}

export const FONT = 'IBM Plex Mono, monospace'
// Re-tema DARK (C1). Editor-local: COL només l'usen els editors de fitxa (aquest +
// TechSheetTemplateEditor); cap altra pantalla. Per això NO toquem els tokens globals de
// :root (--border/--text-main/--text-muted) i la resta de l'app queda intacta. Decisió Agus
// (invertida): fons de TREBALL charcoal MÉS CLAR (`work`), CLOSCA charcoal MÉS FOSC
// (`sidebar`/`bg`); controls amb interior fosc (`field`) i text clar; gold = accent.
export const COL = {
  sidebar: '#1b1f24',   // closca fosca: topbar
  gold: 'var(--gold)',  // accent (es manté)
  goldPale: '#3a3322',  // fons d'estat actiu (tint daurat fosc)
  border: '#3a424c',    // vora subtil sobre fosc
  textMain: '#e8e5df',  // text clar
  textMuted: '#9aa1aa', // text clar atenuat
  bg: '#20262d',        // closca: asides, columnes, panells
  work: '#2d343c',      // fons de treball (viewport, darrere el paper) — MÉS CLAR
  field: '#13171b',     // interior de controls (inputs, dropdowns, botons neutres)
}
// Paleta LITERAL del canvas: Konva pinta sobre <canvas> via ctx.fillStyle i NO resol
// CSS custom properties → var(--token) cau a #000 (negre). Els primitius Konva (ObjectNode,
// build*Primitives, Rects de fons/selecció, text_box, previews) DEUEN usar aquests literals,
// no COL (que és per al DOM, on var() sí resol). Valors = mateixos hex que els tokens de :root.
const KONVA_COL = { white: '#ffffff', gold: '#c27a2a', border: '#e0d5c5', textMain: '#1d1d1b', textMuted: '#868685' }

const LAYER_ORDER = { template: 0, data: 1, free: 2 }
const ZOOM_MIN = 0.25
const ZOOM_MAX = 4
const ZOOM_STEP = 0.1
// TS-4c — eines per "família" de creació (mateixa mecànica de drag).
const RECT_TOOLS = ['rect', 'rect_round', 'ellipse']   // drag = bounding box
const LINE_TOOLS = ['line', 'line_dot', 'arrow', 'arrow2']   // drag = 2 punts
const PRESET_TOOLS = ['preset_callout', 'preset_detail_circle', 'preset_legend']
export const uid = () => (crypto.randomUUID ? crypto.randomUUID() : `id-${Math.round(performance.now())}-${Math.floor(Math.random() * 1e9)}`)
export const toPx = (mm) => mm * MM_TO_PX
export const toMm = (px) => px / MM_TO_PX

const EMPTY_FLAT_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 120"><path d="M34 94 C42 32 72 18 91 28 C114 16 145 33 150 94 C119 103 67 103 34 94 Z" fill="none" stroke="#1d1d1b" stroke-width="3" stroke-linejoin="round"/></svg>'

function svgDataUrl(svg) {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg || '')}`
}

function clampZoom(value) {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, value))
}

function svgAspectRatio(svgText) {
  const parsed = new DOMParser().parseFromString(svgText, 'image/svg+xml')
  if (parsed.querySelector('parsererror') || parsed.documentElement.nodeName !== 'svg') return null
  const svg = parsed.documentElement
  const viewBox = svg.getAttribute('viewBox')
  if (viewBox) {
    const nums = viewBox.trim().split(/[\s,]+/).map(Number)
    if (nums.length === 4 && nums[2] > 0 && nums[3] > 0) return nums[2] / nums[3]
  }
  const width = parseFloat(svg.getAttribute('width'))
  const height = parseFloat(svg.getAttribute('height'))
  return width > 0 && height > 0 ? width / height : null
}

function mapObjectTree(obj, mapper) {
  const mapped = mapper(obj)
  if (!Array.isArray(mapped.children)) return mapped
  return { ...mapped, children: mapped.children.map(child => mapObjectTree(child, mapper)) }
}

function flattenObjects(objects = []) {
  return objects.flatMap(o => [o, ...flattenObjects(o.children || [])])
}

function serializeObject(obj) {
  const base = obj.type === 'data_block' ? (({ src, ...rest }) => rest)(obj) : obj
  return mapObjectTree(base, o => (o.type === 'data_block' ? (({ src, ...rest }) => rest)(o) : o))
}

function localizeObject(obj, origin) {
  if (obj.type === 'line') {
    return { ...obj, points: (obj.points || []).map((v, i) => v - (i % 2 === 0 ? origin.x : origin.y)) }
  }
  if (obj.type === 'arrow') {
    return { ...obj, x: obj.x - origin.x, y: obj.y - origin.y, x2: obj.x2 - origin.x, y2: obj.y2 - origin.y }
  }
  return { ...obj, x: (obj.x || 0) - origin.x, y: (obj.y || 0) - origin.y }
}

function translateObject(obj, dx, dy) {
  if (obj.type === 'line') {
    return { ...obj, points: (obj.points || []).map((v, i) => v + (i % 2 === 0 ? dx : dy)) }
  }
  if (obj.type === 'arrow') {
    return { ...obj, x: obj.x + dx, y: obj.y + dy, x2: obj.x2 + dx, y2: obj.y2 + dy }
  }
  return { ...obj, x: (obj.x || 0) + dx, y: (obj.y || 0) + dy }
}

function groupPointToGlobal(group, x, y) {
  const sx = group.scaleX || 1
  const sy = group.scaleY || 1
  const r = ((group.rotation || 0) * Math.PI) / 180
  const px = x * sx
  const py = y * sy
  return {
    x: (group.x || 0) + px * Math.cos(r) - py * Math.sin(r),
    y: (group.y || 0) + px * Math.sin(r) + py * Math.cos(r),
  }
}

function globalizeObject(obj, group) {
  const scaleX = (obj.scaleX || 1) * (group.scaleX || 1)
  const scaleY = (obj.scaleY || 1) * (group.scaleY || 1)
  const rotation = (obj.rotation || 0) + (group.rotation || 0)
  const scaledSize = {
    ...(obj.width != null ? { width: obj.width * Math.abs(group.scaleX || 1) } : {}),
    ...(obj.height != null ? { height: obj.height * Math.abs(group.scaleY || 1) } : {}),
    ...(obj.rx != null ? { rx: obj.rx * Math.abs(group.scaleX || 1) } : {}),
    ...(obj.ry != null ? { ry: obj.ry * Math.abs(group.scaleY || 1) } : {}),
    ...(obj.scale != null ? { scale: obj.scale * Math.max(Math.abs(group.scaleX || 1), Math.abs(group.scaleY || 1)) } : {}),
  }
  if (obj.type === 'line') {
    return {
      ...obj, ...scaledSize, rotation, scaleX, scaleY,
      points: (obj.points || []).reduce((pts, _v, i, arr) => {
        if (i % 2 !== 0) return pts
        const p = groupPointToGlobal(group, arr[i], arr[i + 1])
        return [...pts, p.x, p.y]
      }, []),
    }
  }
  if (obj.type === 'arrow') {
    const a = groupPointToGlobal(group, obj.x || 0, obj.y || 0)
    const b = groupPointToGlobal(group, obj.x2 || 0, obj.y2 || 0)
    return { ...obj, ...scaledSize, x: a.x, y: a.y, x2: b.x, y2: b.y, rotation, scaleX, scaleY }
  }
  const p = groupPointToGlobal(group, obj.x || 0, obj.y || 0)
  return { ...obj, ...scaledSize, x: p.x, y: p.y, rotation, scaleX, scaleY }
}

function objectBounds(obj) {
  if (obj.type === 'line') {
    const xs = (obj.points || []).filter((_v, i) => i % 2 === 0)
    const ys = (obj.points || []).filter((_v, i) => i % 2 === 1)
    return { minX: Math.min(...xs), minY: Math.min(...ys), maxX: Math.max(...xs), maxY: Math.max(...ys) }
  }
  if (obj.type === 'arrow') {
    return { minX: Math.min(obj.x, obj.x2), minY: Math.min(obj.y, obj.y2), maxX: Math.max(obj.x, obj.x2), maxY: Math.max(obj.y, obj.y2) }
  }
  if (obj.type === 'path') {
    const pts = (obj.paths || []).flatMap(path => (path.segments || []).flatMap(seg => {
      const p = { x: seg.x || 0, y: seg.y || 0 }
      const hin = { x: p.x + (seg.inX || 0), y: p.y + (seg.inY || 0) }
      const hout = { x: p.x + (seg.outX || 0), y: p.y + (seg.outY || 0) }
      return [p, hin, hout]
    }))
    if (!pts.length) return { minX: obj.x || 0, minY: obj.y || 0, maxX: obj.x || 0, maxY: obj.y || 0 }
    const sx = Math.abs(obj.scaleX || 1)
    const sy = Math.abs(obj.scaleY || 1)
    return {
      minX: (obj.x || 0) + Math.min(...pts.map(p => p.x)) * sx,
      minY: (obj.y || 0) + Math.min(...pts.map(p => p.y)) * sy,
      maxX: (obj.x || 0) + Math.max(...pts.map(p => p.x)) * sx,
      maxY: (obj.y || 0) + Math.max(...pts.map(p => p.y)) * sy,
    }
  }
  if (obj.type === 'ellipse') {
    return { minX: obj.x - obj.rx, minY: obj.y - obj.ry, maxX: obj.x + obj.rx, maxY: obj.y + obj.ry }
  }
  if (obj.type === 'group') {
    const childBounds = (obj.children || []).map(child => objectBounds(globalizeObject(child, obj))).filter(Boolean)
    if (!childBounds.length) return { minX: obj.x || 0, minY: obj.y || 0, maxX: obj.x || 0, maxY: obj.y || 0 }
    return {
      minX: Math.min(...childBounds.map(b => b.minX)),
      minY: Math.min(...childBounds.map(b => b.minY)),
      maxX: Math.max(...childBounds.map(b => b.maxX)),
      maxY: Math.max(...childBounds.map(b => b.maxY)),
    }
  }
  const w = (obj.width || 10) * Math.abs(obj.scaleX || 1) * (obj.scale || 1)
  const h = (obj.height || 10) * Math.abs(obj.scaleY || 1) * (obj.scale || 1)
  return { minX: obj.x || 0, minY: obj.y || 0, maxX: (obj.x || 0) + w, maxY: (obj.y || 0) + h }
}

// ── .ftt ↔ v2 (cutover F2) ───────────────────────────────────────────────────
// El backend (ftt-documents/) serveix document.json (v-ftt) + un mapa d'assets {nom→URL}.
// L'editor pinta el format v2 (clau `pages`), on image.src ha de ser una URL carregable;
// per desar es torna a 'assets/<nom>'. Anàleg JS de services_ftt.document_to_v2/v2_to_document.
export function documentToV2(documentJson, assets = {}) {
  const urlOf = (name) => assets[name] || ('assets/' + name)
  return {
    version: 2,
    pageFormat: documentJson?.pageFormat || 'A4L',
    pages: (documentJson?.pages || []).map(p => ({
      id: p.id,
      objects: (p.objects || []).map(o => mapObjectTree(o, obj => (
        typeof obj.src === 'string' && obj.src.startsWith('assets/')
          ? { ...obj, src: urlOf(obj.src.slice(7)) }
          : obj
      ))),
    })),
  }
}

// Inversa per desar: pages v2 (ja serialitzades) → document.json. `urlToName` retorna les URLs
// d'assets carregats a 'assets/<nom>'; les imatges noves (dataURL) es desen inline (extracció
// a assets diferida — vegeu nota Fase 1).
export function v2ToDocument(v2Pages, pageFormat, metadata = {}, urlToName = {}) {
  return {
    ftt_schema: 1,
    metadata: metadata || {},
    pageFormat: pageFormat || 'A4L',
    pages: (v2Pages || []).map(p => ({
      id: p.id,
      objects: (p.objects || []).map(o => mapObjectTree(o, obj => (
        typeof obj.src === 'string' && urlToName[obj.src]
          ? { ...obj, src: 'assets/' + urlToName[obj.src] }
          : obj
      ))),
    })),
  }
}

// ─── (TS-2) El pipeline SVG→PNG de taules s'ha retirat: les taules ara són blocs
// Konva natius (vegeu buildTablePrimitives / GradedTableNode). Es mantenen només els
// helpers d'imatge (loadImageEl/useImage) per a croquis i fitxers del model. ───

// Carrega un HTMLImageElement (promesa) — per a l'export offscreen.
function loadImageEl(src) {
  return new Promise((res, rej) => {
    const i = new window.Image()
    i.crossOrigin = 'anonymous'
    i.onload = () => res(i)
    i.onerror = () => rej(new Error('img load'))
    i.src = src
  })
}

// Hook mínim: dataURL/URL → HTMLImageElement (sense dependència use-image).
function useImage(src) {
  const [img, setImg] = useState(null)
  useEffect(() => {
    if (!src) { setImg(null); return }
    let alive = true
    const image = new window.Image()
    image.crossOrigin = 'anonymous'
    image.onload = () => { if (alive) setImg(image) }
    image.onerror = () => { if (alive) setImg(null) }
    image.src = src
    return () => { alive = false }
  }, [src])
  return img
}

// ════════════════════ Blocs de dades vius (TS-2): geometria ═════════════════
// Geometria en px (escala MM_TO_PX). Una única font de veritat: tant els components
// React (live) com el render offscreen (export/miniatures) consumeixen les mateixes
// "primitives" {t:'r'|'t'|'l', ...}. Així no hi ha drift entre canvas i PDF.
// Cos de text coherent amb el document: 9pt (= 3.175mm a 72dpi) ≈ 8px.
const T_FONT = Math.round(3.175 * MM_TO_PX)   // ~8px (9pt)
const T_FONT_CA = Math.round(2.8222 * MM_TO_PX)  // ~7px (8pt) — subtítol nom_ca (terra de domini 8pt)
// TS-4c: alçada de fila derivada del contingut (2 línies + padding), no fixa.
const T_ROW_PAD = 3   // px de padding vertical per línia
const T_ROW_H = T_FONT + T_FONT_CA + T_ROW_PAD * 3   // dalt nom_en + entre + baix nom_ca
const T_HDR_H = T_FONT + T_ROW_PAD * 2               // capçalera d'una línia
const T_REF_W = 22 * MM_TO_PX     // nomenclatura del croquis (nom_fitxa)
const T_NOM_W = 58 * MM_TO_PX     // Nom EN + CA en dues línies a la mateixa cel·la
const T_VAL_W = 18 * MM_TO_PX     // valor per talla
const T_DELTA_W = 16 * MM_TO_PX   // delta (Δ) — UNA sola columna (valor de GradingRule)
const T_PAD = 2 * MM_TO_PX
const TBL = {
  HDR_BG: '#111827', HDR_TEXT: KONVA_COL.white, ROW_EVEN: KONVA_COL.white, ROW_ODD: '#f7f7f7',
  ROW_BORDER: KONVA_COL.border, OUTER: KONVA_COL.gold, REF: '#dc2626', NOM: '#6b7280', VAL: KONVA_COL.textMain,
  BASE_BG: '#fdf6ee', DELTA: '#185fa5',
}

// Delta de fila = increment de la GradingRule: primer increment no-zero de talla no-base.
// Tots 0 (grading FIXED) → '—'. Signe explícit (+1 / −0.5).
function rowDelta(row, baseSize, sizes) {
  for (const sl of sizes) {
    if (sl === baseSize) continue
    const d = row.deltas?.[sl]
    if (d && d !== 0) return d > 0 ? `+${d}` : `${String(d).replace('-', '−')}`
  }
  return '—'
}

// graded-table JSON (enriquit TS-4a) → {prims, totalW, totalH}. Camps: base_size,
// size_labels, rows[{ref, nom_en, nom_ca, valors, deltas}].
// Columnes: REF · Mesura(EN/CA) · [talles] · Δ (única). Talla base destacada.
function buildTablePrimitives(d) {
  const sizes = d?.size_labels || []
  const rows = d?.rows || []
  const baseSize = d?.base_size || null
  const sizesX0 = T_REF_W + T_NOM_W
  const deltaX0 = sizesX0 + sizes.length * T_VAL_W   // columna Δ única al final
  const totalW = deltaX0 + T_DELTA_W
  const totalH = T_HDR_H + rows.length * T_ROW_H
  const baseIdx = sizes.indexOf(baseSize)
  const prims = []

  // Capçalera
  prims.push({ t: 'r', x: 0, y: 0, w: totalW, h: T_HDR_H, fill: TBL.HDR_BG })
  prims.push({ t: 't', x: 0, y: 0, w: T_REF_W, h: T_HDR_H, text: 'REF', fill: TBL.HDR_TEXT, size: T_FONT, align: 'center', mid: true })
  prims.push({ t: 't', x: T_REF_W + T_PAD, y: 0, w: T_NOM_W - T_PAD, h: T_HDR_H, text: 'Mesura', fill: TBL.HDR_TEXT, size: T_FONT, mid: true })
  sizes.forEach((sl, si) => {
    const isBase = sl === baseSize
    // Cel·la de capçalera de la talla base: fons gold + text blanc.
    if (isBase) prims.push({ t: 'r', x: sizesX0 + si * T_VAL_W, y: 0, w: T_VAL_W, h: T_HDR_H, fill: TBL.OUTER })
    prims.push({ t: 't', x: sizesX0 + si * T_VAL_W, y: 0, w: T_VAL_W, h: T_HDR_H, text: isBase ? `${sl}*` : sl, fill: isBase ? KONVA_COL.white : TBL.HDR_TEXT, size: T_FONT, align: 'center', mid: true })
  })
  prims.push({ t: 't', x: deltaX0, y: 0, w: T_DELTA_W, h: T_HDR_H, text: 'Δ', fill: TBL.HDR_TEXT, size: T_FONT, align: 'center', mid: true })

  // Fons alternat de files
  rows.forEach((row, ri) => {
    const y = T_HDR_H + ri * T_ROW_H
    prims.push({ t: 'r', x: 0, y, w: totalW, h: T_ROW_H, fill: ri % 2 === 0 ? TBL.ROW_EVEN : TBL.ROW_ODD })
  })
  // Realçat de la columna talla base a les dades (sobre els fons, sota el text)
  if (baseIdx >= 0) {
    prims.push({ t: 'r', x: sizesX0 + baseIdx * T_VAL_W, y: T_HDR_H, w: T_VAL_W, h: rows.length * T_ROW_H, fill: TBL.BASE_BG })
  }

  // Contingut
  rows.forEach((row, ri) => {
    const y = T_HDR_H + ri * T_ROW_H
    const ref = row.ref || row.abbreviation || row.codi || ''
    prims.push({ t: 't', x: 0, y, w: T_REF_W, h: T_ROW_H, text: ref, fill: TBL.REF, size: T_FONT, bold: true, align: 'center', mid: true })
    // Nom: dues línies (EN a dalt, CA a baix més petit i cursiva) dins la mateixa cel·la.
    prims.push({ t: 't', x: T_REF_W + T_PAD, y: y + T_ROW_PAD, w: T_NOM_W - 2 * T_PAD, h: T_FONT + 2, text: row.nom_en || '', fill: TBL.VAL, size: T_FONT, mid: false })
    if (row.nom_ca) prims.push({ t: 't', x: T_REF_W + T_PAD, y: y + T_ROW_PAD * 2 + T_FONT, w: T_NOM_W - 2 * T_PAD, h: T_FONT_CA + 2, text: row.nom_ca, fill: TBL.NOM, size: T_FONT_CA, italic: true, mid: false })
    sizes.forEach((sl, si) => {
      const v = row.valors?.[sl]
      prims.push({ t: 't', x: sizesX0 + si * T_VAL_W, y, w: T_VAL_W, h: T_ROW_H, text: v != null ? String(v) : '–', fill: TBL.VAL, size: T_FONT, align: 'center', mid: true })
    })
    prims.push({ t: 't', x: deltaX0, y, w: T_DELTA_W, h: T_ROW_H, text: rowDelta(row, baseSize, sizes), fill: TBL.DELTA, size: T_FONT, align: 'center', mid: true })
    prims.push({ t: 'l', points: [0, y + T_ROW_H, totalW, y + T_ROW_H], stroke: TBL.ROW_BORDER, sw: 0.5 })
  })

  // Separadors verticals + vora exterior
  let cx = T_REF_W
  ;[T_NOM_W, ...sizes.map(() => T_VAL_W), T_DELTA_W].forEach(w => {
    prims.push({ t: 'l', points: [cx, 0, cx, totalH], stroke: TBL.ROW_BORDER, sw: 0.5 }); cx += w
  })
  prims.push({ t: 'r', x: 0, y: 0, w: totalW, h: totalH, stroke: TBL.OUTER, sw: 1.5 })
  return { prims, totalW, totalH }
}

// Capçalera del model → {prims, totalW, totalH}. Dues bandes (20mm + 12mm), 277mm d'ample.
// placeholderMode=true (editor de plantilla): mostra `{model.codi}` etc. en lloc de valors
// reals (no hi ha model), excepte customer_nom que SÍ és real (la plantilla és per client).
export function buildHeaderPrimitives(m, versio, placeholderMode = false, hasLogo = false) {
  const W = 277 * MM_TO_PX
  const B1 = 20 * MM_TO_PX, B2 = 12 * MM_TO_PX
  const totalH = B1 + B2
  const PAD = 2 * MM_TO_PX
  const PH = KONVA_COL.textMuted   // color dels placeholders (literal: Konva no fa CSS)
  // En mode plantilla cada camp és un placeholder en cursiva i gris.
  const f = {
    codi: placeholderMode ? '{model.codi}' : (m?.codi_intern || ''),
    nom: placeholderMode ? '{model.nom}' : (m?.nom_prenda || ''),
    temporada: placeholderMode ? '{temporada}' : (m?.temporada || ''),
    collection: placeholderMode ? '{col·lecció}' : (m?.collection || ''),
    tipus: placeholderMode ? '{tipus de peça}' : (m?.garment_type_item_nom || ''),
    sizesys: placeholderMode ? '{sistema talles}' : (m?.size_system_nom || ''),
    resp: placeholderMode ? '{responsable}' : (m?.responsable_nom || ''),
    versio: placeholderMode ? '{versió}' : `v${versio ?? 1}`,
  }
  const main = KONVA_COL.textMain
  const prims = []
  prims.push({ t: 'r', x: 0, y: 0, w: W, h: B1, fill: '#f5e6d0', stroke: KONVA_COL.gold, sw: 1 })
  prims.push({ t: 't', x: PAD, y: 0, w: W * 0.4 - PAD, h: B1, text: [f.codi, f.nom].filter(Boolean).join(' · '), fill: placeholderMode ? PH : main, size: Math.round(9 * MM_TO_PX), bold: !placeholderMode, italic: placeholderMode, mid: true })
  prims.push({ t: 't', x: W * 0.4, y: 0, w: W * 0.42, h: B1, text: [m?.customer_nom, f.temporada, f.collection].filter(Boolean).join(' · '), fill: placeholderMode ? PH : KONVA_COL.textMain, italic: placeholderMode, size: Math.round(7 * MM_TO_PX), align: 'center', mid: true })
  // Placeholder "(logo)" només si NO hi ha logo real (es pinta a sobre com a imatge).
  if (!hasLogo) prims.push({ t: 't', x: W * 0.82, y: 0, w: W * 0.18 - PAD, h: B1, text: '(logo)', fill: KONVA_COL.textMuted, size: Math.round(7 * MM_TO_PX), align: 'right', mid: true })
  prims.push({ t: 'r', x: 0, y: B1, w: W, h: B2, fill: '#fafafa', stroke: KONVA_COL.border, sw: 1 })
  const line2 = [f.tipus, f.sizesys, f.resp, f.versio].filter(Boolean).join(' · ')
  prims.push({ t: 't', x: PAD, y: B1, w: W - 2 * PAD, h: B2, text: line2, fill: placeholderMode ? PH : '#6b7280', italic: placeholderMode, size: Math.round(6.5 * MM_TO_PX), mid: true })
  return { prims, totalW: W, totalH }
}

// Primitiva → node React Konva. Els rectangles amb fill capturen el clic (hit area del
// Group); text/línies/vores no escolten (no bloquegen drag ni selecció).
function PrimNode({ p }) {
  if (p.t === 'r') {
    return <Rect x={p.x} y={p.y} width={p.w} height={p.h} fill={p.fill}
      stroke={p.stroke} strokeWidth={p.sw} listening={!!p.fill} />
  }
  if (p.t === 'l') {
    return <Line points={p.points} stroke={p.stroke} strokeWidth={p.sw} listening={false} />
  }
  return <Text x={p.x} y={p.y} width={p.w} height={p.h} text={p.text} fill={p.fill}
    fontSize={p.size} fontFamily={FONT} fontStyle={p.bold ? 'bold' : p.italic ? 'italic' : 'normal'}
    align={p.align || 'left'} verticalAlign={p.mid ? 'middle' : 'top'}
    ellipsis wrap="none" listening={false} />
}

// Primitiva → node Konva imperatiu (render offscreen per a export/miniatures).
function addPrimsToGroup(group, prims) {
  for (const p of prims) {
    if (p.t === 'r') group.add(new Konva.Rect({ x: p.x, y: p.y, width: p.w, height: p.h, fill: p.fill, stroke: p.stroke, strokeWidth: p.sw }))
    else if (p.t === 'l') group.add(new Konva.Line({ points: p.points, stroke: p.stroke, strokeWidth: p.sw }))
    else group.add(new Konva.Text({ x: p.x, y: p.y, width: p.w, height: p.h, text: p.text, fill: p.fill, fontSize: p.size, fontFamily: FONT, fontStyle: p.bold ? 'bold' : p.italic ? 'italic' : 'normal', align: p.align || 'left', verticalAlign: p.mid ? 'middle' : 'top', ellipsis: true, wrap: 'none' }))
  }
}

// Bloc de taula graduada — Konva natiu (no imatge). NO fa fetch: rep tableData del pare.
function GradedTableNode({ tableData, groupProps, isSelected }) {
  const { prims, totalW, totalH } = useMemo(() => buildTablePrimitives(tableData), [tableData])
  return (
    <Group {...groupProps}>
      {prims.map((p, i) => <PrimNode key={i} p={p} />)}
      {isSelected && <Rect x={0} y={0} width={totalW} height={totalH} stroke={TBL.OUTER} strokeWidth={2} dash={[4, 3]} fill="transparent" listening={false} />}
    </Group>
  )
}

// Capçalera del model — Konva natiu. Resol els camps en render. Si hi ha logoUrl,
// es pinta el logo real (cantonada superior dreta) en lloc del placeholder "(logo)".
function HeaderBlock({ modelData, versio, placeholderMode, logoUrl, groupProps, isSelected }) {
  const logoImg = useImage(logoUrl || '')
  const hasLogo = !!logoImg
  const { prims, totalW, totalH } = useMemo(
    () => buildHeaderPrimitives(modelData, versio, placeholderMode, hasLogo),
    [modelData, versio, placeholderMode, hasLogo])
  return (
    <Group {...groupProps}>
      {prims.map((p, i) => <PrimNode key={i} p={p} />)}
      {hasLogo && <KonvaImage image={logoImg} x={totalW - 45 * MM_TO_PX} y={2 * MM_TO_PX} width={40 * MM_TO_PX} height={16 * MM_TO_PX} listening={false} />}
      {isSelected && <Rect x={0} y={0} width={totalW} height={totalH} stroke={KONVA_COL.gold} strokeWidth={2} dash={[4, 3]} fill="transparent" listening={false} />}
    </Group>
  )
}

// ─── Descriptor compartit objecte → Konva ───────────────────────────────────
// Live i offscreen consumeixen aquests helpers perquè pantalla i PDF no derivin.
function textBoxParts(obj) {
  const pad = obj.bgPadding || 4
  const fs = obj.fontSize || 11
  const w = toPx(obj.width || 120)
  return {
    group: { x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1 },
    bg: { x: -pad, y: -pad, width: w + pad * 2, height: fs * 1.6 + pad * 2, fill: obj.bgFill, cornerRadius: 3 },
    text: {
      text: obj.text || '', width: w, fontSize: fs, fontFamily: obj.fontFamily || FONT,
      fontStyle: obj.fontStyle || 'normal', fill: obj.fill || KONVA_COL.textMain,
    },
  }
}

function textProps(obj) {
  return {
    x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1, width: obj.width ? toPx(obj.width) : undefined,
    text: obj.text || '', fontSize: obj.fontSize || 11, fontFamily: obj.fontFamily || FONT,
    fontStyle: obj.fontStyle || 'normal', fill: obj.fill || KONVA_COL.textMain,
  }
}

function rectProps(obj) {
  return {
    x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1, width: toPx(obj.width), height: toPx(obj.height),
    fill: obj.fill && obj.fill !== 'transparent' ? obj.fill : undefined,
    stroke: obj.stroke || KONVA_COL.gold, strokeWidth: obj.strokeWidth || 1,
    cornerRadius: obj.cornerRadius || 0,
  }
}

function ellipseProps(obj) {
  return {
    x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1, radiusX: toPx(obj.rx), radiusY: toPx(obj.ry),
    fill: obj.fill && obj.fill !== 'transparent' ? obj.fill : undefined,
    stroke: obj.stroke || KONVA_COL.textMain, strokeWidth: obj.strokeWidth || 1.5,
  }
}

function lineProps(obj) {
  return {
    x: 0, y: 0, rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1, points: (obj.points || []).map(toPx),
    stroke: obj.stroke || KONVA_COL.textMain, strokeWidth: obj.strokeWidth || 1,
    dash: obj.dash || undefined, lineCap: 'round', lineJoin: 'round',
  }
}

function arrowProps(obj) {
  return {
    x: 0, y: 0, rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1, points: [toPx(obj.x), toPx(obj.y), toPx(obj.x2), toPx(obj.y2)],
    stroke: obj.stroke || KONVA_COL.textMain, fill: obj.fill || obj.stroke || KONVA_COL.textMain,
    strokeWidth: obj.strokeWidth || 1.5, pointerLength: 8, pointerWidth: 6,
    pointerAtBeginning: !!obj.arrow2,
  }
}

function pathToData(path) {
  const segments = path.segments || []
  if (!segments.length) return ''
  const fmt = (n) => Math.round(toPx(n || 0) * 1000) / 1000
  const parts = [`M ${fmt(segments[0].x)} ${fmt(segments[0].y)}`]
  for (let i = 1; i < segments.length; i += 1) {
    const prev = segments[i - 1]
    const seg = segments[i]
    const hasCurve = prev.outX || prev.outY || seg.inX || seg.inY
    if (hasCurve) {
      parts.push(`C ${fmt((prev.x || 0) + (prev.outX || 0))} ${fmt((prev.y || 0) + (prev.outY || 0))} ${fmt((seg.x || 0) + (seg.inX || 0))} ${fmt((seg.y || 0) + (seg.inY || 0))} ${fmt(seg.x)} ${fmt(seg.y)}`)
    } else {
      parts.push(`L ${fmt(seg.x)} ${fmt(seg.y)}`)
    }
  }
  if (path.closed && segments.length > 1) {
    const last = segments[segments.length - 1]
    const first = segments[0]
    const hasClosingCurve = last.outX || last.outY || first.inX || first.inY
    if (hasClosingCurve) {
      parts.push(`C ${fmt((last.x || 0) + (last.outX || 0))} ${fmt((last.y || 0) + (last.outY || 0))} ${fmt((first.x || 0) + (first.inX || 0))} ${fmt((first.y || 0) + (first.inY || 0))} ${fmt(first.x)} ${fmt(first.y)}`)
    }
    parts.push('Z')
  }
  return parts.join(' ')
}

function pathChildProps(obj, path) {
  const fill = normalizePaint(path.fill ?? obj.fill)
  const stroke = normalizePaint(path.stroke ?? obj.stroke)
  return {
    data: pathToData(path),
    fill: fill || undefined,
    stroke: stroke || undefined,
    strokeWidth: path.strokeWidth ?? obj.strokeWidth ?? 1.2,
    fillRule: normalizeFillRule(path.fillRule),
    lineCap: 'round',
    lineJoin: 'round',
  }
}

function imageProps(obj) {
  return {
    x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1,
    width: toPx(obj.width), height: toPx(obj.height || obj.width),
  }
}

function dataBlockGroupProps(obj) {
  const scale = obj.scale || 1
  return { x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: scale * (obj.scaleX || 1), scaleY: scale * (obj.scaleY || 1) }
}

function dataBlockPlaceholderProps(obj) {
  return { width: toPx(obj.width || 120), height: toPx(obj.height || 40), fill: COL.goldPale, stroke: KONVA_COL.border, dash: [4, 4] }
}

function blocksTransform(obj) {
  return obj && (obj.type === 'line' || obj.type === 'arrow' || (obj.type === 'text' && obj.bgFill))
}

function commonValue(objects, key) {
  if (!objects.length) return ''
  const first = objects[0]?.[key] ?? ''
  return objects.every(o => (o?.[key] ?? '') === first) ? first : ''
}

async function addObjectToLayer(layer, obj, ctx) {
  if (obj.type === 'group') {
    const g = new Konva.Group({
      x: toPx(obj.x || 0), y: toPx(obj.y || 0), rotation: obj.rotation || 0,
      scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1,
    })
    const orderedChildren = [...(obj.children || [])].sort(
      (a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
    for (const child of orderedChildren) await addObjectToLayer(g, child, ctx)
    layer.add(g)
    return
  }
  if (obj.type === 'text') {
    if (obj.bgFill) {
      const p = textBoxParts(obj)
      const g = new Konva.Group(p.group)
      g.add(new Konva.Rect(p.bg))
      g.add(new Konva.Text({ ...p.text, listening: false }))
      layer.add(g)
      return
    }
    layer.add(new Konva.Text(textProps(obj)))
    return
  }
  if (obj.type === 'rect') {
    layer.add(new Konva.Rect(rectProps(obj)))
    return
  }
  if (obj.type === 'ellipse') {
    layer.add(new Konva.Ellipse(ellipseProps(obj)))
    return
  }
  if (obj.type === 'line') {
    layer.add(new Konva.Line(lineProps(obj)))
    return
  }
  if (obj.type === 'arrow') {
    layer.add(new Konva.Arrow(arrowProps(obj)))
    return
  }
  if (obj.type === 'path') {
    const g = new Konva.Group({
      x: toPx(obj.x || 0), y: toPx(obj.y || 0), rotation: obj.rotation || 0,
      scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1,
    })
    for (const path of obj.paths || []) {
      const props = pathChildProps(obj, path)
      if (props.data) g.add(new Konva.Path(props))
    }
    layer.add(g)
    return
  }
  if (obj.type === 'data_block') {
    let built = null
    let logoEl = null
    if (obj.kind === 'header') {
      if (ctx?.customerLogoUrl) { try { logoEl = await loadImageEl(ctx.customerLogoUrl) } catch { logoEl = null } }
      built = buildHeaderPrimitives(ctx?.modelData, ctx?.versio, ctx?.placeholderMode, !!logoEl)
    } else if (obj.kind === 'graded_table') {
      const data = ctx?.tableData?.[obj.id]
      if (data) built = buildTablePrimitives(data)
    }
    if (built) {
      const g = new Konva.Group(dataBlockGroupProps(obj))
      addPrimsToGroup(g, built.prims)
      if (logoEl) g.add(new Konva.Image({ image: logoEl, x: built.totalW - 45 * MM_TO_PX, y: 2 * MM_TO_PX, width: 40 * MM_TO_PX, height: 16 * MM_TO_PX }))
      layer.add(g)
    }
    return
  }
  if (obj.type === 'image') {
    const src = obj.src
    if (!src) return
    try {
      const el = await loadImageEl(src)
      layer.add(new Konva.Image({ ...imageProps(obj), image: el }))
    } catch { /* imatge no carregada → s'omet */ }
  }
  if (obj.type === 'sketch_svg') {
    try {
      const el = await loadImageEl(svgDataUrl(obj.svg))
      layer.add(new Konva.Image({ ...imageProps(obj), image: el }))
    } catch { /* flat no carregat → s'omet */ }
  }
}

// ─── Render offscreen d'una pàgina a dataURL (export PDF + miniatures) ───
// ctx = { tableData:{objId:json}, modelData, versio }. Dibuixa els blocs de dades
// natius amb les mateixes primitives que el canvas viu (cap PNG congelat).
export async function renderPageToDataURL(page, pixelRatio, ctx) {
  const pageW = ctx?.pageW || CANVAS_W   // TS-4b: dimensions segons format (fallback A4L)
  const pageH = ctx?.pageH || CANVAS_H
  const container = document.createElement('div')
  const stage = new Konva.Stage({ container, width: pageW, height: pageH })
  const layer = new Konva.Layer()
  stage.add(layer)
  layer.add(new Konva.Rect({ x: 0, y: 0, width: pageW, height: pageH, fill: KONVA_COL.white }))
  const ordered = [...(page.objects || [])].sort(
    (a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
  for (const o of ordered) {
    await addObjectToLayer(layer, o, ctx)
  }
  layer.draw()
  const url = stage.toDataURL({ pixelRatio, mimeType: 'image/png' })
  stage.destroy()
  return url
}

// Serialitza pages per a desar: els data_block graded_table NO desen el dataURL
// (es re-genera des de size_fitting_id en obrir); la resta es desa tal qual.
export function serializePages(pages) {
  return pages.map(p => ({
    id: p.id,
    objects: (p.objects || []).map(serializeObject),
  }))
}

// ════════════════════════ Nodes Konva interactius (live) ════════════════════
function ImageObj({ obj, src, common }) {
  const img = useImage(src)
  const props = imageProps(obj)
  if (!img) {
    // Placeholder mentre carrega / si falla.
    return <Rect {...common} width={props.width} height={props.height}
      scaleX={props.scaleX} scaleY={props.scaleY}
      fill={COL.goldPale} stroke={KONVA_COL.border} dash={[4, 4]} />
  }
  return <KonvaImage {...common} image={img} width={props.width} height={props.height}
    scaleX={props.scaleX} scaleY={props.scaleY} />
}

function SketchSvgObj({ obj, common }) {
  const img = useImage(svgDataUrl(obj.svg))
  const props = imageProps(obj)
  if (!img) {
    return <Rect {...common} width={props.width} height={props.height}
      scaleX={props.scaleX} scaleY={props.scaleY}
      fill="transparent" stroke={KONVA_COL.border} dash={[4, 4]} />
  }
  return <KonvaImage {...common} image={img} width={props.width} height={props.height}
    scaleX={props.scaleX} scaleY={props.scaleY} />
}

function PathObj({ obj, common, onDblVector }) {
  const paths = obj.paths || []
  return (
    <Group {...common} onDblClick={onDblVector} onDblTap={onDblVector}>
      {paths.map((path, i) => {
        const props = pathChildProps(obj, path)
        return props.data ? <Path key={i} {...props} hitStrokeWidth={10} /> : null
      })}
    </Group>
  )
}

export function ObjectNode({ obj, src, tableData, modelData, versio, placeholderMode, customerLogoUrl, selected, selectable, draggable, onSelect, onDragEnd, onTransformEnd, onDblText, onDblVector }) {
  const common = {
    id: obj.id,
    x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1,
    draggable,
    onClick: selectable ? onSelect : undefined,
    onTap: selectable ? onSelect : undefined,
    onDragEnd,
    onTransformEnd,
  }
  if (obj.type === 'data_block') {
    const dataCommon = { ...common, ...dataBlockGroupProps(obj) }
    if (obj.kind === 'header') {
      return <HeaderBlock modelData={modelData} versio={versio} placeholderMode={placeholderMode} logoUrl={customerLogoUrl} groupProps={dataCommon} isSelected={selected} />
    }
    const data = tableData?.[obj.id]
    if (!data) {
      return (
        <Group {...dataCommon}>
          <Rect {...dataBlockPlaceholderProps(obj)} />
          <Text x={6} y={6} text={data === null ? 'Sense grading actiu' : 'Carregant taula…'} fontSize={12} fontFamily={FONT} fill={KONVA_COL.textMuted} listening={false} />
        </Group>
      )
    }
    return <GradedTableNode tableData={data} groupProps={dataCommon} isSelected={selected} />
  }
  if (obj.type === 'text') {
    // Text amb fons (text_box): Group amb un Rect darrere; no redimensionable per Transformer.
    if (obj.bgFill) {
      const p = textBoxParts(obj)
      return (
        <Group {...common} onDblClick={onDblText} onDblTap={onDblText}>
          <Rect {...p.bg} />
          <Text {...p.text} listening={false} />
        </Group>
      )
    }
    return <Text {...common} {...textProps(obj)}
      onDblClick={onDblText} onDblTap={onDblText} />
  }
  if (obj.type === 'rect') {
    return <Rect {...common} {...rectProps(obj)} />
  }
  if (obj.type === 'ellipse') {
    return <Ellipse {...common} {...ellipseProps(obj)} />
  }
  if (obj.type === 'line') {
    return <Line {...common} {...lineProps(obj)} hitStrokeWidth={10} />
  }
  if (obj.type === 'arrow') {
    return <Arrow {...common} {...arrowProps(obj)} hitStrokeWidth={10} />
  }
  if (obj.type === 'path') {
    return <PathObj obj={obj} common={common} onDblVector={onDblVector} />
  }
  if (obj.type === 'image') {
    return <ImageObj obj={obj} src={src} common={common} />
  }
  if (obj.type === 'sketch_svg') {
    return <SketchSvgObj obj={obj} common={common} />
  }
  if (obj.type === 'group') {
    const orderedChildren = [...(obj.children || [])].sort(
      (a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
    return (
      <Group {...common}>
        {orderedChildren.map(child => (
          <ObjectNode key={child.id} obj={child} src={child.src}
            tableData={tableData} modelData={modelData} versio={versio}
            placeholderMode={placeholderMode} customerLogoUrl={customerLogoUrl}
            selected={false} selectable={false} draggable={false}
            onSelect={undefined} onDragEnd={undefined} onTransformEnd={undefined}
            onDblText={undefined} onDblVector={undefined} />
        ))}
      </Group>
    )
  }
  return null
}

function hasLegacySketchSvg(objects = []) {
  return objects.some(obj => obj.type === 'sketch_svg' || hasLegacySketchSvg(obj.children || []))
}

function paperColorToCss(color, fallback) {
  try {
    return color?.toCSS ? color.toCSS(true) : fallback
  } catch {
    return fallback
  }
}

function normalizePaint(value) {
  if (value == null || value === '' || value === 'none' || value === 'transparent') return null
  if (typeof value === 'string' && value.startsWith('url(')) return null
  return value
}

function normalizeFillRule(value) {
  return value === 'evenodd' ? 'evenodd' : 'nonzero'
}

function parseStyleDeclarations(body) {
  return Object.fromEntries(
    body.split(';')
      .map(part => part.trim())
      .filter(Boolean)
      .map(part => {
        const sep = part.indexOf(':')
        if (sep === -1) return null
        return [part.slice(0, sep).trim(), part.slice(sep + 1).trim()]
      })
      .filter(Boolean)
  )
}

function inlineSvgClassStyles(svgText) {
  if (typeof DOMParser === 'undefined') return svgText
  let doc
  try {
    doc = new DOMParser().parseFromString(svgText, 'image/svg+xml')
  } catch {
    return svgText
  }
  if (doc.querySelector('parsererror')) return svgText
  const classStyles = {}
  doc.querySelectorAll('style').forEach(styleEl => {
    const css = styleEl.textContent || ''
    css.replace(/([^{}]+)\{([^{}]+)\}/g, (_match, selectorText, body) => {
      const declarations = parseStyleDeclarations(body)
      selectorText.split(',').map(s => s.trim()).forEach(selector => {
        const className = selector.match(/^\.([\w-]+)$/)?.[1]
        if (!className) return
        classStyles[className] = { ...(classStyles[className] || {}), ...declarations }
      })
      return ''
    })
  })
  const paintAttrs = ['fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'fill-rule', 'clip-rule']
  doc.querySelectorAll('path, polygon, polyline, line, rect').forEach(el => {
    const merged = {}
    ;(el.getAttribute('class') || '').split(/\s+/).filter(Boolean).forEach(className => {
      Object.assign(merged, classStyles[className] || {})
    })
    paintAttrs.forEach(attr => {
      if (merged[attr] != null && !el.hasAttribute(attr)) el.setAttribute(attr, merged[attr])
    })
  })
  try {
    return new XMLSerializer().serializeToString(doc)
  } catch {
    return svgText
  }
}

async function legacySketchSvgToPath(obj, scope) {
  if (obj.type !== 'sketch_svg' || !obj.svg) return obj
  scope.project.clear()
  let imported
  try {
    imported = scope.project.importSVG(inlineSvgClassStyles(obj.svg), { insert: true, expandShapes: true })
  } catch {
    return obj
  }
  const bounds = imported.bounds
  if (!bounds?.width || !bounds?.height) return obj
  const width = Math.max(2, obj.width || 80)
  const height = Math.max(2, obj.height || 60)
  const scaleX = width / bounds.width
  const scaleY = height / bounds.height
  const strokeScale = (Math.abs(scaleX) + Math.abs(scaleY)) / 2
  const paths = imported.getItems({ class: scope.Path }).filter(path => path.segments?.length).map(path => ({
    closed: !!path.closed,
    stroke: normalizePaint(path.strokeColor ? paperColorToCss(path.strokeColor, null) : null),
    fill: normalizePaint(path.fillColor ? paperColorToCss(path.fillColor, null) : null),
    fillRule: normalizeFillRule(path.fillRule),
    strokeWidth: Math.max(0.2, (path.strokeWidth || 1) * strokeScale),
    segments: path.segments.map(seg => ({
      x: (seg.point.x - bounds.x) * scaleX,
      y: (seg.point.y - bounds.y) * scaleY,
      inX: seg.handleIn.x * scaleX,
      inY: seg.handleIn.y * scaleY,
      outX: seg.handleOut.x * scaleX,
      outY: seg.handleOut.y * scaleY,
    })),
  }))
  if (!paths.length) return obj
  return {
    ...obj,
    type: 'path',
    paths,
    stroke: undefined,
    fill: undefined,
    strokeWidth: undefined,
    svg: undefined,
    width: undefined,
    height: undefined,
  }
}

async function convertLegacySketchSvgs(pages) {
  if (!pages.some(page => hasLegacySketchSvg(page.objects || []))) return pages
  const mod = await import('paper')
  const paper = mod.default || mod
  const scope = new paper.PaperScope()
  const canvas = document.createElement('canvas')
  scope.setup(canvas)
  const convertObject = async (obj) => {
    const converted = await legacySketchSvgToPath(obj, scope)
    if (!Array.isArray(converted.children)) return converted
    const children = []
    for (const child of converted.children) children.push(await convertObject(child))
    return { ...converted, children }
  }
  const nextPages = []
  for (const page of pages) {
    const objects = []
    for (const obj of page.objects || []) objects.push(await convertObject(obj))
    nextPages.push({ ...page, objects })
  }
  scope.remove()
  return nextPages
}

async function convertLegacySketchSvgObject(obj) {
  const mod = await import('paper')
  const paper = mod.default || mod
  const scope = new paper.PaperScope()
  const canvas = document.createElement('canvas')
  scope.setup(canvas)
  const converted = await legacySketchSvgToPath(obj, scope)
  scope.remove()
  return converted
}

// ════════════════════════════════ Component ═════════════════════════════════
export default function TechSheetEditor() {
  const { t } = useTranslation()
  const { id, fitxerId } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const taskId = searchParams.get('task_id')
  // Mode .ftt: l'editor llegeix/desa el document .ftt (ModelFitxer) en comptes del TechSheet (O2O).
  const fttMode = !!fitxerId
  const isEditMode = !!taskId
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
  const uploadHeaders = { Authorization: `Bearer ${token}` }

  const [model, setModel] = useState(null)
  const [sheet, setSheet] = useState(null)
  const [pages, setPages] = useState([{ id: uid(), objects: [] }])
  const [currentPage, setCurrentPage] = useState(0)
  const [selectedIds, setSelectedIds] = useState([])
  const [tool, setTool] = useState('select')
  // 'loading' | 'owned' | 'conflict' | 'error' | 'readonly'
  const [lockState, setLockState] = useState((isEditMode || fttMode) ? 'loading' : 'readonly')
  const [conflict, setConflict] = useState(null)
  const [saveState, setSaveState] = useState(null)  // null|'saving'|'saved'|'error'
  const [fitxers, setFitxers] = useState([])
  const [sizeFittings, setSizeFittings] = useState([])
  const [tableData, setTableData] = useState({})    // {objId: jsonData|null} fora del JSON
  const [notice, setNotice] = useState(null)        // toast efímer (p.ex. "ja hi ha capçalera")
  const [thumbnails, setThumbnails] = useState([])
  const [exporting, setExporting] = useState(false)
  const [addingTable, setAddingTable] = useState(false)
  const [pickFitting, setPickFitting] = useState(false)
  const [editingText, setEditingText] = useState(null)  // {id, value, x, y, w}
  const [editingFlatId, setEditingFlatId] = useState(null)
  const [zoom, setZoom] = useState(1)
  const [pageFormat, setPageFormat] = useState('A4L')   // TS-4b: format del document sencer
  // PAL-1: paleta amb flyouts (estil Adobe). flyoutOpen = id del flyout desplegat; flyoutSel =
  // última eina triada per flyout (la que queda visible al botó col·lapsat).
  const [flyoutOpen, setFlyoutOpen] = useState(null)
  const [flyoutSel, setFlyoutSel] = useState({})
  const [flyoutRect, setFlyoutRect] = useState(null)   // rect del botó (popover en position:fixed)

  const locked = lockState === 'owned'
  const fmt = PAGE_FORMATS[pageFormat] || PAGE_FORMATS.A4L
  const pageW = Math.round(fmt.w * MM_TO_PX)
  const pageH = Math.round(fmt.h * MM_TO_PX)
  const customerLogoUrl = model?.customer_logo || null   // TS-4c
  const stageRef = useRef(null)
  const trRef = useRef(null)
  const viewportRef = useRef(null)
  const wrapRef = useRef(null)
  const fileRef = useRef(null)
  const holdTimer = useRef(null)        // PAL-1: timer del press-and-hold per obrir flyout
  const suppressClick = useRef(false)   // PAL-1: evita activar l'eina si el hold ja ha obert el flyout
  // PAL-1: tancar el flyout obert en clicar fora del seu contenidor.
  useEffect(() => {
    if (!flyoutOpen) return
    const onDown = (e) => {
      if (!(e.target.closest && e.target.closest(`[data-flyout="${flyoutOpen}"]`))) setFlyoutOpen(null)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [flyoutOpen])
  const flatFileRef = useRef(null)
  const saveTimer = useRef(null)
  const skipSave = useRef(true)        // salta l'autosave del primer load
  // Mode .ftt: estat del document (assets carregats + metadata + cap de cadena actual).
  const fttAssets = useRef({})         // {nom: URL} dels assets servits pel backend
  const fttUrlToName = useRef({})      // {URL: nom} per desar (URL → 'assets/<nom>')
  const fttMeta = useRef({})           // metadata del document.json (es conserva en desar)
  const fttHeadId = useRef(fitxerId || null)  // cap de cadena vigent (canvia en desar: nova versió)
  const drawing = useRef(null)         // {type, points, id} mentre es dibuixa
  const [drawTemp, setDrawTemp] = useState(null)

  // ── Helpers de mutació de pàgines ──────────────────────────────────────────
  const objectsOf = (pi) => pages[pi]?.objects || []
  const updatePageObjects = useCallback((pi, updater) => {
    setPages(ps => ps.map((p, i) => (i === pi ? { ...p, objects: updater(p.objects || []) } : p)))
  }, [])
  const addObject = useCallback((obj) => {
    updatePageObjects(currentPage, objs => [...objs, obj])
    setSelectedIds([obj.id])
  }, [currentPage, updatePageObjects])
  const updateObject = useCallback((objId, patch) => {
    updatePageObjects(currentPage, objs => objs.map(o => (o.id === objId ? { ...o, ...patch } : o)))
  }, [currentPage, updatePageObjects])
  const updateObjects = useCallback((objIds, patch) => {
    const ids = new Set(objIds)
    updatePageObjects(currentPage, objs => objs.map(o => (
      ids.has(o.id) ? { ...o, ...(typeof patch === 'function' ? patch(o) : patch) } : o
    )))
  }, [currentPage, updatePageObjects])
  const deleteObject = useCallback((objId) => {
    updatePageObjects(currentPage, objs => objs.filter(o => o.id !== objId))
    if (editingFlatId === objId) setEditingFlatId(null)
    setSelectedIds([])
  }, [currentPage, editingFlatId, updatePageObjects])
  const deleteObjects = useCallback((objIds) => {
    const ids = new Set(objIds)
    updatePageObjects(currentPage, objs => objs.filter(o => !ids.has(o.id)))
    setSelectedIds([])
  }, [currentPage, updatePageObjects])
  const clearSelection = useCallback(() => setSelectedIds([]), [])
  const setZoomClamped = useCallback((next) => {
    setZoom(current => clampZoom(typeof next === 'function' ? next(current) : next))
  }, [])
  const fitZoomToViewport = useCallback(() => {
    const viewport = viewportRef.current
    if (!viewport) return
    const pad = 48
    setZoomClamped(Math.min((viewport.clientWidth - pad) / pageW, (viewport.clientHeight - pad) / pageH))
  }, [pageH, pageW, setZoomClamped])
  const selectOnly = useCallback((objId) => setSelectedIds([objId]), [])
  const toggleSelection = useCallback((objId) => {
    setSelectedIds(ids => (ids.includes(objId) ? ids.filter(id => id !== objId) : [...ids, objId]))
  }, [])
  const handleSelectObject = useCallback((e, objId) => {
    if (e?.evt?.shiftKey) toggleSelection(objId)
    else selectOnly(objId)
  }, [selectOnly, toggleSelection])
  const mirrorObjects = useCallback((objIds, axis) => {
    updateObjects(objIds, o => ({ [axis]: -1 * (o[axis] || 1) }))
  }, [updateObjects])
  const createPreset = useCallback((preset, x, y) => {
    const base = { id: uid(), type: 'group', layer: 'free', x, y, rotation: 0 }
    if (preset === 'preset_callout') {
      return {
        ...base,
        children: [
          { id: uid(), type: 'text', layer: 'free', x: 0, y: 0, width: 54, height: 18, text: t('tech_sheet.preset_callout_text'), fontSize: 11, fontFamily: FONT, fill: KONVA_COL.textMain, bgFill: KONVA_COL.white, bgPadding: 4 },
          { id: uid(), type: 'arrow', layer: 'free', x: 58, y: 7, x2: 92, y2: 7, stroke: KONVA_COL.textMain, fill: KONVA_COL.textMain, strokeWidth: 1.5 },
        ],
      }
    }
    if (preset === 'preset_detail_circle') {
      return {
        ...base,
        children: [
          { id: uid(), type: 'ellipse', layer: 'free', x: 18, y: 18, rx: 16, ry: 16, stroke: KONVA_COL.gold, strokeWidth: 2, fill: 'transparent' },
          { id: uid(), type: 'line', layer: 'free', x: 0, y: 0, points: [34, 18, 72, 18], stroke: KONVA_COL.gold, strokeWidth: 1 },
        ],
      }
    }
    return {
      ...base,
      children: [
        { id: uid(), type: 'rect', layer: 'free', x: 0, y: 0, width: 78, height: 36, fill: KONVA_COL.white, stroke: KONVA_COL.border, strokeWidth: 1 },
        { id: uid(), type: 'text', layer: 'free', x: 4, y: 4, width: 68, height: 8, text: t('tech_sheet.preset_legend_title'), fontSize: 9, fontFamily: FONT, fontStyle: 'bold', fill: KONVA_COL.textMain },
        { id: uid(), type: 'text', layer: 'free', x: 4, y: 15, width: 68, height: 8, text: t('tech_sheet.preset_legend_row_1'), fontSize: 8, fontFamily: FONT, fill: KONVA_COL.textMain },
        { id: uid(), type: 'text', layer: 'free', x: 4, y: 25, width: 68, height: 8, text: t('tech_sheet.preset_legend_row_2'), fontSize: 8, fontFamily: FONT, fill: KONVA_COL.textMain },
      ],
    }
  }, [t])
  const moveSelectionInFreeLayer = useCallback((direction) => {
    const ids = new Set(selectedIds)
    updatePageObjects(currentPage, objs => {
      const next = [...objs]
      if (direction === 'forward') {
        for (let i = next.length - 2; i >= 0; i -= 1) {
          if (!ids.has(next[i].id) || next[i].layer !== 'free') continue
          const j = next.findIndex((o, idx) => idx > i && o.layer === 'free')
          if (j !== -1 && !ids.has(next[j].id)) [next[i], next[j]] = [next[j], next[i]]
        }
      } else {
        for (let i = 1; i < next.length; i += 1) {
          if (!ids.has(next[i].id) || next[i].layer !== 'free') continue
          let j = -1
          for (let p = i - 1; p >= 0; p -= 1) {
            if (next[p].layer === 'free') { j = p; break }
          }
          if (j !== -1 && !ids.has(next[j].id)) [next[i], next[j]] = [next[j], next[i]]
        }
      }
      return next
    })
  }, [currentPage, selectedIds, updatePageObjects])
  const groupSelection = useCallback(() => {
    const ids = new Set(selectedIds)
    const selected = objectsOf(currentPage).filter(o => ids.has(o.id) && o.layer !== 'template')
    if (selected.length < 2) return
    const bounds = selected.map(objectBounds).filter(Boolean)
    const origin = { x: Math.min(...bounds.map(b => b.minX)), y: Math.min(...bounds.map(b => b.minY)) }
    const groupId = uid()
    const group = {
      id: groupId, type: 'group', layer: 'free', x: origin.x, y: origin.y, rotation: 0,
      children: selected.map(o => localizeObject(o, origin)),
    }
    updatePageObjects(currentPage, objs => {
      const firstIndex = objs.findIndex(o => ids.has(o.id))
      const rest = objs.filter(o => !ids.has(o.id))
      const next = [...rest]
      next.splice(Math.max(0, firstIndex), 0, group)
      return next
    })
    setSelectedIds([groupId])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, pages, selectedIds, updatePageObjects])
  const ungroupObject = useCallback((groupId) => {
    const group = objectsOf(currentPage).find(o => o.id === groupId && o.type === 'group')
    if (!group) return
    const children = (group.children || []).map(child => globalizeObject(child, group))
    updatePageObjects(currentPage, objs => {
      return objs.flatMap(o => (o.id === groupId ? children : [o]))
    })
    setSelectedIds(children.map(child => child.id))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, pages, updatePageObjects])
  const alignSelection = useCallback((mode) => {
    const ids = new Set(selectedIds)
    const selected = objectsOf(currentPage).filter(o => ids.has(o.id))
    if (selected.length < 2) return
    const byId = Object.fromEntries(selected.map(o => [o.id, objectBounds(o)]))
    const all = Object.values(byId)
    const minX = Math.min(...all.map(b => b.minX))
    const maxX = Math.max(...all.map(b => b.maxX))
    const minY = Math.min(...all.map(b => b.minY))
    const maxY = Math.max(...all.map(b => b.maxY))
    updatePageObjects(currentPage, objs => objs.map(o => {
      if (!ids.has(o.id)) return o
      const b = byId[o.id]
      let dx = 0, dy = 0
      if (mode === 'left') dx = minX - b.minX
      if (mode === 'center') dx = (minX + maxX) / 2 - (b.minX + b.maxX) / 2
      if (mode === 'right') dx = maxX - b.maxX
      if (mode === 'top') dy = minY - b.minY
      if (mode === 'middle') dy = (minY + maxY) / 2 - (b.minY + b.maxY) / 2
      if (mode === 'bottom') dy = maxY - b.maxY
      return translateObject(o, dx, dy)
    }))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, pages, selectedIds, updatePageObjects])
  const distributeSelection = useCallback((axis) => {
    const ids = new Set(selectedIds)
    const selected = objectsOf(currentPage).filter(o => ids.has(o.id))
    if (selected.length < 3) return
    const entries = selected.map(o => ({ obj: o, bounds: objectBounds(o) }))
      .sort((a, b) => axis === 'h' ? a.bounds.minX - b.bounds.minX : a.bounds.minY - b.bounds.minY)
    const first = entries[0]
    const last = entries[entries.length - 1]
    const start = axis === 'h' ? first.bounds.minX : first.bounds.minY
    const end = axis === 'h' ? last.bounds.maxX : last.bounds.maxY
    const totalSize = entries.reduce((sum, e) => sum + (axis === 'h' ? e.bounds.maxX - e.bounds.minX : e.bounds.maxY - e.bounds.minY), 0)
    const gap = (end - start - totalSize) / (entries.length - 1)
    let cursor = start
    const deltaById = {}
    for (const e of entries) {
      const currentStart = axis === 'h' ? e.bounds.minX : e.bounds.minY
      deltaById[e.obj.id] = cursor - currentStart
      cursor += (axis === 'h' ? e.bounds.maxX - e.bounds.minX : e.bounds.maxY - e.bounds.minY) + gap
    }
    updatePageObjects(currentPage, objs => objs.map(o => {
      if (!ids.has(o.id)) return o
      return axis === 'h' ? translateObject(o, deltaById[o.id], 0) : translateObject(o, 0, deltaById[o.id])
    }))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, pages, selectedIds, updatePageObjects])

  // ── Càrrega inicial: model, sheet, fitxers, size fittings, lock ────────────
  useEffect(() => {
    if (!id) return
    let cancelled = false

    fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (!cancelled && d) setModel(d) }).catch(() => {})

    fetch(`${API}/api/v1/model-fitxers/?model=${id}&is_current=true&ordering=-data_pujada`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (!cancelled && d) setFitxers(d.results || d || []) }).catch(() => {})

    fetch(`${API}/api/v1/size-fittings/?model=${id}`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (!cancelled && d) setSizeFittings(d.results || d || []) }).catch(() => {})

    if (fttMode) {
      // Mode .ftt (F1): carrega el document des de ftt-documents/<fitxerId>/ i el porta a v2.
      // El lock i el desat els afegeix F2; F1 obre en consulta.
      fetch(`${API}/api/v1/ftt-documents/${fitxerId}/`, { headers: authHeaders })
        .then(r => (r.ok ? r.json() : null))
        .then(data => {
          if (cancelled || !data) return
          const assets = data.assets || {}
          fttAssets.current = assets
          fttUrlToName.current = Object.fromEntries(Object.entries(assets).map(([n, u]) => [u, n]))
          fttMeta.current = data.document_json?.metadata || {}
          fttHeadId.current = data.fitxer?.id || fitxerId
          setSheet(data.fitxer)   // versio ve de ModelFitxer.versio
          hydrate({ template_json: documentToV2(data.document_json, assets) })
        }).catch(() => {})

      // F2: adquireix el lock del document lògic (TTL+force-if-stale al backend; el timer-gap
      // ja està resolt: desar renova locked_at).
      fetch(`${API}/api/v1/ftt-documents/${fitxerId}/lock/`, { method: 'POST', headers: authHeaders })
        .then(async r => {
          if (cancelled) return
          if (r.ok) { await r.json(); setLockState('owned') }
          else if (r.status === 409) { setConflict(await r.json()); setLockState('conflict') }
          else setLockState('error')
        })
        .catch(() => { if (!cancelled) setLockState('error') })
    }

    return () => {
      cancelled = true
      // Si venia d'una tasca (Kanban), deixa-la en Pausa; allibera sempre el lock del .ftt.
      if (taskId) {
        fetch(`${API}/api/v1/model-task-items/${taskId}/transition/`, {
          method: 'POST', headers: authHeaders,
          body: JSON.stringify({ to_status: 'Paused' }), keepalive: true,
        }).catch(() => {})
      }
      fetch(`${API}/api/v1/ftt-documents/${fttHeadId.current}/unlock/`, {
        method: 'POST', headers: authHeaders, keepalive: true,
      }).catch(() => {})
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, fitxerId])

  // Carrega el template_json v2 a l'estat. tj buit/absent → 1 pàgina buida.
  function hydrate(sheetData) {
    const tj = sheetData?.template_json
    skipSave.current = true
    let rawPages = null
    if (tj && tj.version === 2 && Array.isArray(tj.pages) && tj.pages.length) {
      rawPages = tj.pages.map(p => ({ id: p.id || uid(), objects: (p.objects || []).map(o => ({ ...o, id: o.id || uid() })) }))
    } else {
      rawPages = [{ id: uid(), objects: [] }]
    }
    setPages(rawPages)
    convertLegacySketchSvgs(rawPages).then(converted => {
      if (converted !== rawPages) setPages(converted)
    }).catch(() => {})
    setPageFormat((tj && tj.pageFormat) || 'A4L')
    setCurrentPage(0)
  }

  // ── Re-fetch dels data_block (taula graduada) en carregar → cache JSON viu ──
  useEffect(() => {
    const pending = pages.flatMap(p => flattenObjects(p.objects || []))
      .filter(o => o.type === 'data_block' && o.kind === 'graded_table' && o.size_fitting_id && !(o.id in tableData))
    if (!pending.length) return
    let cancelled = false
    ;(async () => {
      for (const o of pending) {
        try {
          const r = await fetch(`${API}/api/v1/fitting/${o.size_fitting_id}/graded-table/`, { headers: authHeaders })
          // 404 (sf sense GradingVersion activa) → null = placeholder "Sense grading actiu".
          const data = r.ok ? await r.json() : null
          if (!cancelled) setTableData(m => ({ ...m, [o.id]: data }))
        } catch { if (!cancelled) setTableData(m => ({ ...m, [o.id]: null })) }
      }
    })()
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pages])

  // ── Autosave (debounce 2s; només amb lock; salta el primer load) ───────────
  useEffect(() => {
    if (skipSave.current) { skipSave.current = false; return }
    if (!locked) return
    setSaveState('saving')
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(async () => {
      try {
        const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        // Desa una versió NOVA del .ftt (save_model_file encadena; renova el lock). La resposta
        // és el nou cap de cadena → s'hi reapunta per als propers desats i per a la versió mostrada.
        const documentJson = v2ToDocument(serializePages(pages), pageFormat, fttMeta.current, fttUrlToName.current)
        const r = await fetch(`${API}/api/v1/ftt-documents/${fttHeadId.current}/`, {
          method: 'PATCH', headers, body: JSON.stringify({ document_json: documentJson }),
        })
        if (r.ok) { const nh = await r.json(); fttHeadId.current = nh.id; setSheet(nh); setSaveState('saved') }
        else setSaveState('error')
      } catch { setSaveState('error') }
    }, 2000)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pages, locked, pageFormat])

  // ── Miniatures: re-render offscreen de totes les pàgines (debounce) ────────
  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const ctx = { tableData, modelData: model, versio: sheet?.versio, pageW, pageH, customerLogoUrl }
        const thumbs = []
        for (const p of pages) thumbs.push(await renderPageToDataURL(p, 0.18, ctx))
        setThumbnails(thumbs)
      } catch { /* noop */ }
    }, 300)
    return () => clearTimeout(t)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pages, tableData, model, sheet?.versio, pageFormat])

  // ── Transformer: lliga el node seleccionat ─────────────────────────────────
  useEffect(() => {
    const tr = trRef.current
    const stage = stageRef.current
    if (!tr || !stage) return
    if (editingFlatId) {
      tr.nodes([])
      tr.getLayer()?.batchDraw()
      return
    }
    // Transformable: text, rect, ellipse, image, data_block (keepRatio). NO: línies, fletxes
    // (resize de punts), text amb fons (Group), plantilla.
    const selectedSet = new Set(selectedIds)
    const nodes = objectsOf(currentPage)
      .filter(o => selectedSet.has(o.id) && o.layer !== 'template' && !blocksTransform(o))
      .map(o => stage.findOne('#' + o.id))
      .filter(Boolean)
    tr.nodes(nodes)
    tr.getLayer()?.batchDraw()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIds, currentPage, pages, editingFlatId])

  // ── Teclat: Delete/Backspace esborra l'objecte free seleccionat ────────────
  useEffect(() => {
    const onKey = (e) => {
      if (editingFlatId) return
      if (editingText) return
      // No esborrar mentre s'escriu en un camp del panell (X/Y, escala, format…).
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (e.key !== 'Delete' && e.key !== 'Backspace') return
      if (!selectedIds.length || !locked) return
      const deletable = objectsOf(currentPage).filter(o => selectedIds.includes(o.id) && o.layer === 'free').map(o => o.id)
      if (deletable.length) { e.preventDefault(); deleteObjects(deletable) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIds, currentPage, pages, locked, editingText, editingFlatId])

  // ── Handlers de node (drag / transform) ────────────────────────────────────
  const handleDragEnd = (obj) => (e) => {
    const node = e.target
    if (obj.type === 'line') {
      const dx = toMm(node.x()), dy = toMm(node.y())
      const pts = (obj.points || []).map((v, i) => (i % 2 === 0 ? v + dx : v + dy))
      node.position({ x: 0, y: 0 })
      updateObject(obj.id, { points: pts })
    } else if (obj.type === 'arrow') {
      const dx = toMm(node.x()), dy = toMm(node.y())
      node.position({ x: 0, y: 0 })
      updateObject(obj.id, { x: obj.x + dx, y: obj.y + dy, x2: obj.x2 + dx, y2: obj.y2 + dy })
    } else {
      updateObject(obj.id, { x: toMm(node.x()), y: toMm(node.y()) })
    }
  }
  const handleTransformEnd = (obj) => (e) => {
    const node = e.target
    const sx = node.scaleX(), sy = node.scaleY()
    const absSx = Math.abs(sx), absSy = Math.abs(sy)
    const scaleX = sx < 0 ? -1 : 1
    const scaleY = sy < 0 ? -1 : 1
    const rotation = node.rotation()
    node.scaleX(1); node.scaleY(1)
    if (obj.type === 'group') {
      updateObject(obj.id, { x: toMm(node.x()), y: toMm(node.y()), rotation, scaleX: sx, scaleY: sy })
      return
    }
    if (obj.type === 'path') {
      updateObject(obj.id, { x: toMm(node.x()), y: toMm(node.y()), rotation, scaleX: sx, scaleY: sy })
      return
    }
    // Blocs de dades: el resize baka l'escala a obj.scale (coherent amb l'auto-fit),
    // no a width/height. node.scaleX() ja és l'escala absoluta nova (Konva multiplica
    // sobre l'escala base del Group), per tant s'hi assigna directament.
    if (obj.type === 'data_block') {
      updateObject(obj.id, { x: toMm(node.x()), y: toMm(node.y()), rotation, scaleX, scaleY, scale: Math.max(0.1, Math.max(absSx, absSy)) })
      return
    }
    if (obj.type === 'ellipse') {
      updateObject(obj.id, { x: toMm(node.x()), y: toMm(node.y()), rotation, scaleX, scaleY, rx: Math.max(1, toMm(node.radiusX() * absSx)), ry: Math.max(1, toMm(node.radiusY() * absSy)) })
      return
    }
    const patch = {
      x: toMm(node.x()), y: toMm(node.y()), rotation, scaleX, scaleY,
      width: Math.max(2, toMm(node.width() * absSx)),
    }
    if (obj.type !== 'text') patch.height = Math.max(2, toMm(node.height() * absSy))
    updateObject(obj.id, patch)
  }

  // ── Stage: dibuix de rect/línia/draw + crear text + deselecció ─────────────
  const stagePoint = () => {
    const stage = stageRef.current
    if (!stage) return null
    const p = stage.getPointerPosition()
    // R1: el Stage s'escala per `zoom` (Konva re-pinta nítid). getPointerPosition retorna
    // l'espai escalat → dividim per zoom per obtenir coords de CONTINGUT (px base), que és el
    // que esperen toMm i el dibuix de formes.
    return p ? { x: p.x / zoom, y: p.y / zoom } : null
  }
  const onStageMouseDown = (e) => {
    if (editingFlatId) return
    if (!locked) { if (e.target === e.target.getStage()) clearSelection(); return }
    const pos = stagePoint()
    if (!pos) return
    if (tool === 'select') {
      if (e.target === e.target.getStage()) clearSelection()
      return
    }
    if (tool === 'text' || tool === 'text_box') {
      const obj = {
        id: uid(), type: 'text', layer: 'free', x: toMm(pos.x), y: toMm(pos.y),
        width: 120, height: 30, text: 'Doble clic per editar', fontSize: 11,
        fontFamily: FONT, fill: KONVA_COL.textMain,
        ...(tool === 'text_box' ? { bgFill: KONVA_COL.white, bgPadding: 4 } : {}),
      }
      addObject(obj); setTool('select'); return
    }
    if (PRESET_TOOLS.includes(tool)) {
      addObject(createPreset(tool, toMm(pos.x), toMm(pos.y)))
      setTool('select')
      return
    }
    if (RECT_TOOLS.includes(tool) || LINE_TOOLS.includes(tool) || tool === 'draw') {
      drawing.current = { type: tool, startX: pos.x, startY: pos.y, points: [pos.x, pos.y] }
      setDrawTemp({ type: tool, x: pos.x, y: pos.y, w: 0, h: 0, points: [pos.x, pos.y] })
    }
  }
  const onStageMouseMove = () => {
    if (editingFlatId) return
    if (!drawing.current) return
    const pos = stagePoint()
    if (!pos) return
    const d = drawing.current
    if (RECT_TOOLS.includes(d.type)) {
      setDrawTemp({ type: d.type, x: Math.min(d.startX, pos.x), y: Math.min(d.startY, pos.y), w: Math.abs(pos.x - d.startX), h: Math.abs(pos.y - d.startY) })
    } else if (LINE_TOOLS.includes(d.type)) {
      setDrawTemp({ type: d.type, points: [d.startX, d.startY, pos.x, pos.y] })
    } else if (d.type === 'draw') {
      d.points = [...d.points, pos.x, pos.y]
      setDrawTemp({ type: 'draw', points: d.points })
    }
  }
  const onStageMouseUp = () => {
    if (editingFlatId) return
    const d = drawing.current
    if (!d) return
    drawing.current = null
    const pos = stagePoint() || { x: d.startX, y: d.startY }
    const base = { id: uid(), layer: 'free' }
    let obj = null
    if (d.type === 'rect' || d.type === 'rect_round') {
      const x = Math.min(d.startX, pos.x), y = Math.min(d.startY, pos.y)
      const w = Math.abs(pos.x - d.startX), h = Math.abs(pos.y - d.startY)
      // R2: un clic o drag massa petit creava un rect "invisible" (cap objecte). Ara sempre
      // es crea: amb la mida arrossegada o, si és menyspreable, una de per defecte al punt
      // clicat. Traç una mica més gruixut perquè es vegi clar.
      const small = w <= 3 || h <= 3
      obj = {
        ...base, type: 'rect',
        x: toMm(small ? d.startX : x), y: toMm(small ? d.startY : y),
        width: small ? 40 : toMm(w), height: small ? 28 : toMm(h),
        fill: 'transparent', stroke: KONVA_COL.gold, strokeWidth: 1.5,
        ...(d.type === 'rect_round' ? { cornerRadius: 8 } : {}),
      }
    } else if (d.type === 'ellipse') {
      const w = Math.abs(pos.x - d.startX), h = Math.abs(pos.y - d.startY)
      if (w > 3 && h > 3) obj = { ...base, type: 'ellipse', x: toMm((d.startX + pos.x) / 2), y: toMm((d.startY + pos.y) / 2), rx: toMm(w / 2), ry: toMm(h / 2), stroke: KONVA_COL.textMain, strokeWidth: 1.5, fill: 'transparent' }
    } else if (d.type === 'line' || d.type === 'line_dot') {
      obj = { ...base, type: 'line', x: 0, y: 0, points: [toMm(d.startX), toMm(d.startY), toMm(pos.x), toMm(pos.y)], stroke: KONVA_COL.textMain, strokeWidth: 1, ...(d.type === 'line_dot' ? { dash: [4, 4] } : {}) }
    } else if (d.type === 'arrow' || d.type === 'arrow2') {
      const dist = Math.hypot(pos.x - d.startX, pos.y - d.startY)
      if (dist > 5) obj = { ...base, type: 'arrow', x: toMm(d.startX), y: toMm(d.startY), x2: toMm(pos.x), y2: toMm(pos.y), stroke: KONVA_COL.textMain, fill: KONVA_COL.textMain, strokeWidth: 1.5, ...(d.type === 'arrow2' ? { arrow2: true } : {}) }
    } else if (d.type === 'draw') {
      if (d.points.length >= 4) obj = { ...base, type: 'line', x: 0, y: 0, points: d.points.map(toMm), stroke: KONVA_COL.textMain, strokeWidth: 1 }
    }
    setDrawTemp(null)
    if (obj) { addObject(obj); setTool('select') }
  }

  // ── Edició inline de text (textarea overlay) ───────────────────────────────
  const startTextEdit = (obj) => {
    if (!locked) return
    selectOnly(obj.id)
    setEditingText({ id: obj.id, value: obj.text || '', x: toPx(obj.x), y: toPx(obj.y), w: toPx(obj.width || 120) })
  }
  const commitTextEdit = () => {
    if (!editingText) return
    updateObject(editingText.id, { text: editingText.value })
    setEditingText(null)
  }
  const onViewportWheel = (e) => {
    if (!e.ctrlKey && !e.metaKey) return
    e.preventDefault()
    const direction = e.deltaY > 0 ? -1 : 1
    setZoomClamped(z => z + direction * ZOOM_STEP)
  }

  // ── Imatge: fitxer local (botó/drop) i fitxers del model ───────────────────
  const addImageFromDataURL = (dataURL) => {
    const obj = { id: uid(), type: 'image', layer: 'free', x: 50, y: 50, width: 120, height: 80, src: dataURL }
    addObject(obj)
  }
  const handleFile = (file) => {
    if (!file || !locked) return
    const fr = new FileReader()
    fr.onload = () => addImageFromDataURL(fr.result)
    fr.readAsDataURL(file)
  }
  const onDrop = (e) => {
    e.preventDefault()
    if (!locked) return
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('image/')) handleFile(file)
  }
  // Insereix el logo del client com a imatge lliure (redimensionable). TS-4c.
  const insertLogo = () => {
    if (!locked) return
    if (!customerLogoUrl) { flash(t('tech_sheet.flash_no_logo')); return }
    addObject({ id: uid(), type: 'image', kind: 'logo', layer: 'free', x: 10, y: 8, width: 40, height: 20, src: customerLogoUrl })
  }
  const insertFlatSketch = () => {
    if (!locked) return
    const obj = {
      id: uid(), type: 'path', layer: 'free',
      x: 54, y: 44,
      stroke: KONVA_COL.textMain,
      strokeWidth: 1.2,
      fill: 'transparent',
      paths: [{
        closed: true,
        stroke: KONVA_COL.textMain,
        strokeWidth: 1.2,
        fill: 'transparent',
        segments: [
          { x: 12, y: 10, inX: 0, inY: 0, outX: 10, outY: -4 },
          { x: 46, y: 8, inX: -10, inY: -3, outX: 12, outY: 3 },
          { x: 74, y: 18, inX: -6, inY: -5, outX: 5, outY: 14 },
          { x: 80, y: 54, inX: 3, inY: -12, outX: -9, outY: 6 },
          { x: 50, y: 64, inX: 12, inY: 5, outX: -13, outY: 3 },
          { x: 16, y: 56, inX: 12, inY: 6, outX: -6, outY: -14 },
        ],
      }],
    }
    addObject(obj)
    setEditingFlatId(obj.id)
  }
  const importFlatSvgText = async (svgText) => {
    if (!locked) return
    const ratio = svgAspectRatio(svgText)
    if (!ratio) {
      flash(t('tech_sheet.flat_import_invalid'))
      return
    }
    const maxW = 110
    const maxH = 78
    const width = ratio >= maxW / maxH ? maxW : maxH * ratio
    const height = width / ratio
    if (['sketch_svg', 'path'].includes(selObj?.type)) {
      const source = {
        id: selObj.id, type: 'sketch_svg', layer: selObj.layer || 'free',
        x: selObj.x || 54, y: selObj.y || 44,
        width: selObj.width || width, height: selObj.height || height,
        svg: svgText,
      }
      const converted = await convertLegacySketchSvgObject(source)
      updateObject(selObj.id, converted)
      setEditingText(null)
      setTool('select')
      setEditingFlatId(selObj.id)
      return
    }
    const source = {
      id: uid(), type: 'sketch_svg', layer: 'free',
      x: 54, y: 44, width, height,
      svg: svgText,
    }
    const obj = await convertLegacySketchSvgObject(source)
    addObject(obj)
    setEditingFlatId(obj.id)
  }
  const handleFlatSvgFile = (file) => {
    if (!file || !locked) return
    const fr = new FileReader()
    fr.onload = () => {
      importFlatSvgText(String(fr.result || '')).catch(() => flash(t('tech_sheet.flat_import_error')))
    }
    fr.onerror = () => flash(t('tech_sheet.flat_import_error'))
    fr.readAsText(file)
  }
  const editSelectedFlat = () => {
    if (!locked || !['sketch_svg', 'path'].includes(selObj?.type)) return
    setEditingText(null)
    setTool('select')
    setEditingFlatId(selObj.id)
  }
  const startVectorEdit = (obj) => {
    if (!locked || !['sketch_svg', 'path'].includes(obj?.type)) return
    setEditingText(null)
    setTool('select')
    selectOnly(obj.id)
    setEditingFlatId(obj.id)
  }
  const commitFlatEdit = (payload) => {
    if (!editingFlatId) return
    if (payload && typeof payload === 'object' && Array.isArray(payload.paths)) {
      updateObject(editingFlatId, { paths: payload.paths })
      setEditingFlatId(null)
      return
    }
    const svg = payload
    const current = objectsOf(currentPage).find(o => o.id === editingFlatId)
    const ratio = svgAspectRatio(svg)
    const patch = { svg }
    if (current && ratio) {
      const currentW = Math.max(2, current.width || 90)
      const currentH = Math.max(2, current.height || 60)
      if (ratio >= currentW / currentH) {
        patch.width = currentW
        patch.height = Math.max(2, currentW / ratio)
      } else {
        patch.height = currentH
        patch.width = Math.max(2, currentH * ratio)
      }
    }
    updateObject(editingFlatId, patch)
    setEditingFlatId(null)
  }
  const addModelFitxer = async (f) => {
    if (!locked) return
    let url = f.url_extern
    if (!url && f.fitxer) url = f.fitxer.startsWith('http') ? f.fitxer : `${API}${f.fitxer}`
    if (!url) return
    try {
      const blob = await fetch(url).then(r => { if (!r.ok) throw new Error('fetch'); return r.blob() })
      const dataURL = await new Promise((res, rej) => {
        const fr = new FileReader()
        fr.onload = () => res(fr.result); fr.onerror = () => rej(new Error('fr'))
        fr.readAsDataURL(blob)
      })
      addImageFromDataURL(dataURL)
    } catch { /* silenci */ }
  }

  const flash = (text) => { setNotice(text); setTimeout(() => setNotice(null), 2500) }

  // ── Bloc de dades: taula graduada (Konva natiu — sense PNG congelat) ────────
  const insertGradedTable = async (sfId) => {
    if (!locked) return
    setAddingTable(true)
    try {
      const r = await fetch(`${API}/api/v1/fitting/${sfId}/graded-table/`, { headers: authHeaders })
      if (!r.ok) { flash(t('tech_sheet.flash_no_grading')); return }
      const data = await r.json()
      if (!data.rows || !data.rows.length) { flash(t('tech_sheet.flash_empty_table')); return }
      const { totalW, totalH } = buildTablePrimitives(data)
      // Auto-fit a l'àrea útil del format actual (marge 10mm per costat); el factor es
      // persisteix com a obj.scale (i és reajustable manualment via el panell).
      const wMm = totalW / MM_TO_PX, hMm = totalH / MM_TO_PX
      const scale = Math.min(1, (fmt.w - 20) / wMm, (fmt.h - 20) / hMm)
      const objId = uid()
      const obj = {
        id: objId, type: 'data_block', kind: 'graded_table', size_fitting_id: sfId,
        layer: 'data', x: 10, y: 14, scale,
        width: wMm * scale, height: hMm * scale,
      }
      setTableData(m => ({ ...m, [objId]: data }))
      addObject(obj)
    } catch { /* silenci */ }
    finally { setAddingTable(false) }
  }
  const onAddTableClick = () => {
    if (!sizeFittings.length) return
    if (sizeFittings.length === 1) insertGradedTable(sizeFittings[0].id)
    else setPickFitting(true)
  }

  // ── Bloc de dades: capçalera del model (màxim 1 per pàgina) ─────────────────
  const insertHeader = () => {
    if (!locked) return
    if (objectsOf(currentPage).some(o => o.type === 'data_block' && o.kind === 'header')) {
      flash(t('tech_sheet.flash_header_exists')); return
    }
    const { totalW, totalH } = buildHeaderPrimitives(model, sheet?.versio)
    addObject({
      id: uid(), type: 'data_block', kind: 'header', layer: 'data',
      x: 10, y: 8, width: totalW / MM_TO_PX, height: totalH / MM_TO_PX,
    })
  }

  // ── Pàgines ────────────────────────────────────────────────────────────────
  const addPage = () => {
    if (!locked) return
    setPages(ps => [...ps, { id: uid(), objects: [] }])
    setCurrentPage(pages.length)
  }
  const removePage = (index) => {
    if (!locked || pages.length <= 1) return
    if (!window.confirm(t('tech_sheet.confirm_delete_page'))) return
    setPages(ps => ps.filter((_, i) => i !== index))
    setCurrentPage(ci => Math.min(ci, pages.length - 2))
    clearSelection()
  }

  // ── Export PDF (pdf-lib) ───────────────────────────────────────────────────
  const onExport = async () => {
    setExporting(true)
    try {
      const pdf = await PDFDocument.create()
      const ctx = { tableData, modelData: model, versio: sheet?.versio, pageW, pageH, customerLogoUrl }
      const [pdfW, pdfH] = fmt.pdf
      for (const p of pages) {
        const dataUrl = await renderPageToDataURL(p, 3.5, ctx)
        const png = await pdf.embedPng(dataUrl)
        const page = pdf.addPage([pdfW, pdfH])
        page.drawImage(png, { x: 0, y: 0, width: pdfW, height: pdfH })
      }
      const bytes = await pdf.save()
      const blob = new Blob([bytes], { type: 'application/pdf' })
      const filename = `${model?.codi_intern || id}_fitxa_v${sheet?.versio ?? 1}.pdf`
      // Mode .ftt (F4): puja el PDF al Finder com a EXPORT enllaçat a la versió .ftt actual
      // (cadena pròpia + generat_des_de; el .ftt no es toca). El backend el desa via B6.
      if (fttMode) {
        try {
          const fd = new FormData()
          fd.append('file', blob, filename)
          fd.append('nom', filename)
          await fetch(`${API}/api/v1/ftt-documents/${fttHeadId.current}/export/`, {
            method: 'POST', headers: uploadHeaders, body: fd,
          })
          flash(t('tech_sheet.export_saved_finder'))
        } catch { /* silenci */ }
      }
      // Descàrrega local (sempre, també en mode .ftt: l'usuari rep el fitxer a l'instant).
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch { /* silenci */ }
    finally { setExporting(false) }
  }

  // ── UI ───────────────────────────────────────────────────────────────────
  const badge = (() => {
    if (lockState === 'loading') return { text: t('model_sheet.loading'), bg: COL.bg, fg: COL.textMuted }
    if (lockState === 'readonly') return { text: t('tech_sheet.badge_readonly'), bg: COL.bg, fg: COL.textMuted }
    if (lockState === 'owned') return { text: t('tech_sheet.badge_editing'), bg: COL.gold, fg: 'var(--white)' }
    if (lockState === 'conflict') return { text: t('tech_sheet.badge_locked_by', { user: conflict?.locked_by || t('tech_sheet.another_user') }), bg: COL.bg, fg: COL.textMuted }
    return { text: t('tech_sheet.badge_lock_error'), bg: COL.bg, fg: COL.textMuted }
  })()
  const saveLabel = saveState === 'saving' ? t('tech_sheet.saving') : saveState === 'saved' ? t('tech_sheet.saved') : saveState === 'error' ? t('tech_sheet.save_error') : null
  const zoomLabel = `${Math.round(zoom * 100)}%`

  const headerBtn = {
    display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', padding: '5px 10px',
    borderRadius: 6, border: `1px solid ${COL.border}`, background: 'transparent',
    cursor: 'pointer', color: COL.textMain, fontFamily: FONT,
  }
  // Botó de la paleta d'eines vertical (C2): icona quadrada; eina activa ressaltada amb accent gold.
  const paletteBtn = {
    display: 'flex', alignItems: 'center', justifyContent: 'center', width: 32, height: 32,
    borderRadius: 6, border: `1px solid transparent`, background: 'transparent',
    cursor: 'pointer', color: COL.textMain, fontFamily: FONT,
  }
  const paletteBtnOn = { borderColor: COL.gold, background: COL.goldPale, color: COL.gold }
  // PAL-1: eina futura sense handler — placeholder visible però deshabilitat.
  const paletteBtnSoon = { color: COL.textMuted, opacity: 0.4, cursor: 'default' }
  // Barra contextual (C4): FOSCA com la resta de la closca (PAL-A), discreta, separada de la topbar
  // i del viewport per un filet molt fi (1px COL.border subtil) — com la barra d'estat inferior.
  const CTX_BG = COL.sidebar, CTX_BORDER = COL.border, CTX_TEXT = COL.textMain
  const ctxBtn = { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', minWidth: 26, height: 24, padding: '0 6px', border: `1px solid ${CTX_BORDER}`, borderRadius: 5, background: COL.bg, color: CTX_TEXT, cursor: 'pointer', fontFamily: FONT, fontSize: 'var(--fs-body)' }
  const curObjs = objectsOf(currentPage)
  const ordered = [...curObjs].sort((a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
  const selectedSet = new Set(selectedIds)
  const selectedObjects = curObjs.filter(o => selectedSet.has(o.id))
  const selObj = selectedObjects.length === 1 ? selectedObjects[0] : null
  const multiSelected = selectedObjects.length > 1
  const multiStroke = selectedObjects.filter(o => ['rect', 'ellipse', 'line', 'arrow', 'path'].includes(o.type))
  const multiFill = selectedObjects.filter(o => ['text', 'rect', 'ellipse', 'path'].includes(o.type))
  const multiPosition = selectedObjects.filter(o => o.type !== 'line' && o.type !== 'arrow')
  const mirrorableIds = selectedObjects.filter(o => !blocksTransform(o)).map(o => o.id)
  const freeSelectedIds = selectedObjects.filter(o => o.layer === 'free').map(o => o.id)
  const multiStrokeValue = commonValue(multiStroke, 'stroke')
  const multiFillValue = commonValue(multiFill, 'fill')
  const multiX = commonValue(multiPosition, 'x')
  const multiY = commonValue(multiPosition, 'y')
  const editingFlat = editingFlatId ? curObjs.find(o => o.id === editingFlatId && ['sketch_svg', 'path'].includes(o.type)) : null
  const paperFlatLabels = {
    loading: t('tech_sheet.flat_loading'),
    pathSelected: t('tech_sheet.flat_path_selected'),
    noPath: t('tech_sheet.flat_no_path'),
    changed: t('tech_sheet.flat_changed'),
    importError: t('tech_sheet.flat_import_error'),
    done: t('tech_sheet.flat_done'),
    cancel: t('tech_sheet.flat_cancel'),
  }

  // PAL-1: PALETA D'EINES (estil Adobe) — 6 categories amb separadors; els grups amb múltiples
  // eines són FLYOUTS (icona + ▸; clic al triangle o press-and-hold desplega; l'última usada queda
  // visible). Es conserven els tool keys i TOTS els handlers (RECT_TOOLS/LINE_TOOLS/PRESET_TOOLS,
  // onStageMouseDown…): això és només presentació + agrupació. Les eines sense handler avui es
  // marquen `soon` (placeholder deshabilitat) i NO s'hi cabla cap comportament (són tandes futures).
  const PALETTE = [
    { cat: 'select', items: [
      { kind: 'tool', k: 'select', icon: 'ti-pointer-2', label: t('tech_sheet.tool_select') },
      { kind: 'tool', k: 'node', icon: 'ti-vector', label: t('tech_sheet.tool_node'), soon: true },
      { kind: 'tool', k: 'subpath', icon: 'ti-vector-spline', label: t('tech_sheet.tool_subpath'), soon: true },
    ] },
    { cat: 'draw', items: [
      { kind: 'tool', k: 'draw', icon: 'ti-pencil', label: t('tech_sheet.tool_draw') },
      { kind: 'tool', k: 'pen', icon: 'ti-vector-bezier', label: t('tech_sheet.tool_pen'), soon: true },
      { kind: 'flyout', id: 'shapes', label: t('tech_sheet.tool_group_shapes'), tools: [
        { k: 'rect', icon: 'ti-square', label: t('tech_sheet.tool_rect') },
        { k: 'rect_round', icon: 'ti-square-rounded', label: t('tech_sheet.tool_rect_round') },
        { k: 'ellipse', icon: 'ti-circle', label: t('tech_sheet.tool_ellipse') },
      ] },
      { kind: 'flyout', id: 'lines', label: t('tech_sheet.tool_group_lines'), tools: [
        { k: 'line', icon: 'ti-line', label: t('tech_sheet.tool_line') },
        { k: 'line_dot', icon: 'ti-line-dashed', label: t('tech_sheet.tool_line_dot') },
      ] },
      { kind: 'flyout', id: 'arrows', label: t('tech_sheet.tool_group_arrows'), tools: [
        { k: 'arrow', icon: 'ti-arrow-right', label: t('tech_sheet.tool_arrow') },
        { k: 'arrow2', icon: 'ti-arrows-horizontal', label: t('tech_sheet.tool_arrow2') },
      ] },
    ] },
    { cat: 'text', items: [
      { kind: 'flyout', id: 'text', label: t('tech_sheet.tool_group_text'), tools: [
        { k: 'text', icon: 'ti-text-recognition', label: t('tech_sheet.tool_text') },
        { k: 'text_box', icon: 'ti-text-scan-2', label: t('tech_sheet.tool_text_box') },
      ] },
    ] },
    { cat: 'annot', items: [
      { kind: 'tool', k: 'cota_pom', icon: 'ti-ruler-measure', label: t('tech_sheet.tool_cota_pom'), soon: true },
      { kind: 'tool', k: 'note', icon: 'ti-arrow-guide', label: t('tech_sheet.tool_note'), soon: true },
      { kind: 'flyout', id: 'presets', label: t('tech_sheet.tool_group_presets'), tools: [
        { k: 'preset_callout', icon: 'ti-message-2-share', label: t('tech_sheet.preset_callout') },
        { k: 'preset_detail_circle', icon: 'ti-circle-dashed', label: t('tech_sheet.preset_detail_circle') },
        { k: 'preset_legend', icon: 'ti-list-details', label: t('tech_sheet.preset_legend') },
      ] },
    ] },
    { cat: 'modify', items: [
      { kind: 'flyout', id: 'pathfinder', label: t('tech_sheet.tool_group_pathfinder'), soon: true, tools: [
        { k: 'path_union', icon: 'ti-layers-union', label: t('tech_sheet.tool_path_union') },
        { k: 'path_subtract', icon: 'ti-layers-subtract', label: t('tech_sheet.tool_path_subtract') },
        { k: 'path_intersect', icon: 'ti-layers-intersect', label: t('tech_sheet.tool_path_intersect') },
        { k: 'path_difference', icon: 'ti-layers-difference', label: t('tech_sheet.tool_path_difference') },
      ] },
      { kind: 'tool', k: 'rotate', icon: 'ti-rotate', label: t('tech_sheet.tool_rotate'), soon: true },
      { kind: 'tool', k: 'resize', icon: 'ti-resize', label: t('tech_sheet.tool_resize'), soon: true },
      { kind: 'action', action: 'mirror_h', icon: 'ti-flip-horizontal', label: t('tech_sheet.mirror_h') },
      { kind: 'action', action: 'mirror_v', icon: 'ti-flip-vertical', label: t('tech_sheet.mirror_v') },
      { kind: 'tool', k: 'crop', icon: 'ti-crop', label: t('tech_sheet.tool_crop'), soon: true },
    ] },
    { cat: 'nav', items: [
      { kind: 'tool', k: 'pan', icon: 'ti-hand-stop', label: t('tech_sheet.tool_pan'), soon: true },
      { kind: 'action', action: 'zoom_fit', icon: 'ti-zoom', label: t('tech_sheet.tool_zoom') },
      { kind: 'tool', k: 'cursor_precise', icon: 'ti-crosshair', label: t('tech_sheet.tool_cursor_precise'), soon: true },
    ] },
  ]
  // PEU de la paleta — swatches (sense estat de color global avui → placeholders marcats `soon`).
  const PALETTE_SWATCHES = [
    { id: 'fill', icon: 'ti-square-filled', label: t('tech_sheet.swatch_fill') },
    { id: 'stroke', icon: 'ti-border-style', label: t('tech_sheet.swatch_stroke') },
    { id: 'swap', icon: 'ti-arrows-exchange', label: t('tech_sheet.swatch_swap') },
  ]
  // Eines funcionals planes (per resoldre icona/etiqueta de l'eina activa a la barra contextual).
  const flatTools = PALETTE.flatMap(c => c.items.flatMap(it => it.kind === 'flyout' ? it.tools : (it.kind === 'tool' ? [it] : [])))
  const activeToolDef = flatTools.find(tl => tl.k === tool) || { icon: 'ti-pointer-2', label: t('tech_sheet.tool_select') }
  // Accions de paleta (no són modes d'eina): operen sobre la selecció / viewport amb handlers existents.
  const runPaletteAction = (action) => {
    if (action === 'mirror_h') mirrorObjects(mirrorableIds, 'scaleX')
    else if (action === 'mirror_v') mirrorObjects(mirrorableIds, 'scaleY')
    else if (action === 'zoom_fit') fitZoomToViewport()
  }
  const paletteActionDisabled = (action) =>
    (action === 'mirror_h' || action === 'mirror_v') ? mirrorableIds.length === 0 : false
  // Flyout: eina visible (col·lapsada) = l'activa si pertany al grup, si no l'última triada, si no la 1a.
  const flyoutVisible = (fl) => fl.tools.find(tl => tl.k === tool) || fl.tools.find(tl => tl.k === flyoutSel[fl.id]) || fl.tools[0]
  const cancelHold = () => { if (holdTimer.current) { clearTimeout(holdTimer.current); holdTimer.current = null } }
  const openFlyout = (id, rect) => { setFlyoutRect(rect); setFlyoutOpen(id) }
  const startHold = (id, rect) => { cancelHold(); holdTimer.current = setTimeout(() => { suppressClick.current = true; openFlyout(id, rect) }, 300) }
  const pickFlyoutTool = (fl, k) => { setFlyoutSel(s => ({ ...s, [fl.id]: k })); setTool(k); setFlyoutOpen(null); cancelHold() }

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', background: COL.bg, fontFamily: FONT }}>
      {/* ── Topbar ── */}
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '0.7rem 1.2rem', borderBottom: `1px solid ${COL.border}`, background: COL.sidebar, color: COL.textMain }}>
        <button onClick={() => navigate(`/models/${id}`)} style={headerBtn}>
          <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> {t('tech_sheet.back_to_model')}
        </button>
        <button onClick={onExport} disabled={exporting}
          style={{ ...headerBtn, background: COL.gold, border: 'none', color: 'var(--white)', opacity: exporting ? 0.5 : 1 }}>
          <i className="ti ti-file-download" style={{ fontSize: 14 }} /> {exporting ? t('tech_sheet.exporting') : t('tech_sheet.export_pdf')}
        </button>
        <span style={{ fontSize: 'var(--fs-h3)', fontWeight: 600 }}>
          {model?.codi_intern || `#${id}`}{model?.nom_prenda ? ` · ${model.nom_prenda}` : ''}
        </span>
        <span style={{ fontSize: 'var(--fs-body)', color: COL.textMuted }}>{t('tech_sheet.page_of', { n: currentPage + 1, total: pages.length })}</span>

        {/* Eines → paleta esquerra (C2). Zoom/estat/notice → barra d'estat (C3).
            Format de pàgina + opcions contextuals → barra contextual (C4). */}
      </header>

      {/* ── Barra contextual (C4) — gris clar; opcions de l'eina/objecte actiu ── */}
      <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 8, padding: '4px 12px', minHeight: 32, background: CTX_BG, borderBottom: `1px solid ${CTX_BORDER}`, color: CTX_TEXT, fontSize: 'var(--fs-body)' }}>
        {!locked ? (
          <span style={{ color: COL.textMuted }}><i className="ti ti-eye" style={{ marginRight: 5 }} />{t('tech_sheet.readonly_overlay')}</span>
        ) : multiSelected ? (
          <>
            <span style={{ fontWeight: 600 }}>{t('tech_sheet.selected_objects', { n: selectedObjects.length })}</span>
            <span style={{ width: 1, height: 16, background: CTX_BORDER }} />
            <button onClick={() => alignSelection('left')} title={t('tech_sheet.align_left')} style={ctxBtn}><i className="ti ti-align-left" /></button>
            <button onClick={() => alignSelection('center')} title={t('tech_sheet.align_center')} style={ctxBtn}><i className="ti ti-align-center" /></button>
            <button onClick={() => alignSelection('right')} title={t('tech_sheet.align_right')} style={ctxBtn}><i className="ti ti-align-right" /></button>
            <button onClick={() => alignSelection('top')} title={t('tech_sheet.align_top')} style={ctxBtn}><i className="ti ti-align-top" /></button>
            <button onClick={() => alignSelection('middle')} title={t('tech_sheet.align_middle')} style={ctxBtn}><i className="ti ti-align-middle" /></button>
            <button onClick={() => alignSelection('bottom')} title={t('tech_sheet.align_bottom')} style={ctxBtn}><i className="ti ti-align-bottom" /></button>
          </>
        ) : selObj ? (
          <>
            <span style={{ fontWeight: 600 }}>{t('tech_sheet.element')} · {selObj.type}</span>
            {['rect', 'ellipse', 'line', 'arrow', 'path'].includes(selObj.type) && (
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>{t('tech_sheet.stroke_color')}
                <input type="color" value={selObj.stroke && selObj.stroke !== 'transparent' ? selObj.stroke : '#1d1d1b'}
                  onChange={e => updateObject(selObj.id, selObj.type === 'arrow' ? { stroke: e.target.value, fill: e.target.value } : { stroke: e.target.value })}
                  style={{ width: 26, height: 22, border: 'none', borderRadius: 4, cursor: 'pointer', padding: 0, background: 'none' }} /></label>
            )}
            {['rect', 'ellipse', 'path', 'text'].includes(selObj.type) && (
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>{t('tech_sheet.fill')}
                <input type="color" value={selObj.fill && selObj.fill !== 'transparent' ? selObj.fill : '#ffffff'}
                  onChange={e => updateObject(selObj.id, { fill: e.target.value })}
                  style={{ width: 26, height: 22, border: 'none', borderRadius: 4, cursor: 'pointer', padding: 0, background: 'none' }} /></label>
            )}
          </>
        ) : tool !== 'select' ? (
          <span><i className={`ti ${activeToolDef.icon}`} style={{ marginRight: 5 }} />{t('tech_sheet.ctx_tool', { tool: activeToolDef.label })}</span>
        ) : (
          <span style={{ color: COL.textMuted }}>{t('tech_sheet.ctx_idle')}</span>
        )}
        <select value={pageFormat} onChange={e => setPageFormat(e.target.value)} disabled={!locked}
          title={t('tech_sheet.page_format')}
          style={{ marginLeft: 'auto', height: 24, padding: '0 6px', border: `1px solid ${CTX_BORDER}`, borderRadius: 5, background: COL.bg, color: CTX_TEXT, fontFamily: FONT, fontSize: 'var(--fs-body)', cursor: locked ? 'pointer' : 'default' }}>
          {Object.entries(PAGE_FORMATS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
      </div>

      <main style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* ── Paleta d'eines vertical (C2) — 6 categories + flyouts estil Adobe (PAL-1) ── */}
        {locked && (
          <div style={{ width: 46, flexShrink: 0, background: COL.bg, borderRight: `1px solid ${COL.border}`, overflowY: 'auto', overflowX: 'visible', padding: '8px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
            {PALETTE.flatMap((cat, ci) => [
              ci > 0 ? <div key={`sep-${cat.cat}`} style={{ width: 26, height: 1, background: COL.border, margin: '3px 0' }} /> : null,
              ...cat.items.map((it, ii) => {
                const key = `${cat.cat}-${ii}`
                if (it.kind === 'tool') {
                  return (
                    <button key={key} disabled={it.soon} onClick={() => !it.soon && setTool(it.k)}
                      title={it.soon ? `${it.label} · ${t('tech_sheet.coming_soon')}` : it.label}
                      style={{ ...paletteBtn, ...(tool === it.k ? paletteBtnOn : {}), ...(it.soon ? paletteBtnSoon : {}) }}>
                      <i className={`ti ${it.icon}`} style={{ fontSize: 17 }} />
                    </button>
                  )
                }
                if (it.kind === 'action') {
                  const dis = paletteActionDisabled(it.action)
                  return (
                    <button key={key} disabled={dis} onClick={() => !dis && runPaletteAction(it.action)}
                      title={it.label}
                      style={{ ...paletteBtn, ...(dis ? paletteBtnSoon : {}) }}>
                      <i className={`ti ${it.icon}`} style={{ fontSize: 17 }} />
                    </button>
                  )
                }
                // flyout
                const vis = flyoutVisible(it)
                const groupActive = it.tools.some(tl => tl.k === tool)
                return (
                  <div key={key} data-flyout={it.id} style={{ position: 'relative' }}>
                    <button disabled={it.soon}
                      onMouseDown={e => !it.soon && startHold(it.id, e.currentTarget.getBoundingClientRect())}
                      onMouseUp={cancelHold} onMouseLeave={cancelHold}
                      onClick={() => { if (suppressClick.current) { suppressClick.current = false; return } if (it.soon) return; pickFlyoutTool(it, vis.k) }}
                      title={it.soon ? `${it.label} · ${t('tech_sheet.coming_soon')}` : `${it.label} — ${vis.label}`}
                      style={{ ...paletteBtn, ...(groupActive ? paletteBtnOn : {}), ...(it.soon ? paletteBtnSoon : {}) }}>
                      <i className={`ti ${vis.icon}`} style={{ fontSize: 17 }} />
                      {/* triangle ▸ indicador de flyout */}
                      <i className="ti ti-caret-right-filled"
                        onClick={e => { e.stopPropagation(); cancelHold(); suppressClick.current = false; if (!it.soon) openFlyout(it.id, e.currentTarget.parentElement.getBoundingClientRect()) }}
                        style={{ position: 'absolute', right: 1, bottom: 0, fontSize: 8, lineHeight: 1, opacity: it.soon ? 0.4 : 0.7 }} />
                    </button>
                    {flyoutOpen === it.id && flyoutRect && (
                      <div data-flyout={it.id} style={{ position: 'fixed', left: flyoutRect.right + 4, top: flyoutRect.top, zIndex: 60, display: 'flex', gap: 2, padding: 4, background: COL.sidebar, border: `1px solid ${COL.border}`, borderRadius: 6, boxShadow: '0 4px 16px rgba(0,0,0,0.35)' }}>
                        {it.tools.map(tl => (
                          <button key={tl.k} disabled={it.soon} onClick={() => !it.soon && pickFlyoutTool(it, tl.k)}
                            title={it.soon ? `${tl.label} · ${t('tech_sheet.coming_soon')}` : tl.label}
                            style={{ ...paletteBtn, ...(tool === tl.k ? paletteBtnOn : {}), ...(it.soon ? paletteBtnSoon : {}) }}>
                            <i className={`ti ${tl.icon}`} style={{ fontSize: 17 }} />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )
              }),
            ])}
            <div style={{ width: 26, height: 1, background: COL.border, margin: '3px 0' }} />
            <button onClick={() => fileRef.current?.click()} title={t('tech_sheet.tool_image')} style={paletteBtn}>
              <i className="ti ti-photo" style={{ fontSize: 17 }} />
            </button>
            <input ref={fileRef} type="file" accept="image/*" hidden
              onChange={e => { const f = e.target.files[0]; e.target.value = ''; handleFile(f) }} />
            {/* PEU: swatches (placeholders sense estat de color global — PAL-1) */}
            <div style={{ width: 26, height: 1, background: COL.border, margin: '3px 0' }} />
            {PALETTE_SWATCHES.map(sw => (
              <button key={sw.id} disabled title={`${sw.label} · ${t('tech_sheet.coming_soon')}`}
                style={{ ...paletteBtn, ...paletteBtnSoon }}>
                <i className={`ti ${sw.icon}`} style={{ fontSize: 17 }} />
              </button>
            ))}
          </div>
        )}

        {/* ── Centre: Stage Konva ── */}
        <div ref={viewportRef} onWheel={onViewportWheel} style={{ flex: 1, background: COL.work, minWidth: 0, overflow: 'auto', position: 'relative', padding: 24, boxSizing: 'border-box' }}>
          {lockState === 'readonly' && (
            <div style={{ position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)', zIndex: 5, background: COL.sidebar, border: `1px solid ${COL.border}`, borderRadius: 6, padding: '4px 12px', fontSize: 'var(--fs-body)', color: COL.textMuted }}>
              <i className="ti ti-eye" style={{ marginRight: 6 }} />{t('tech_sheet.readonly_overlay')}
            </div>
          )}
          <div style={{ width: pageW * zoom, height: pageH * zoom, position: 'relative', margin: '0 auto' }}>
          <div ref={wrapRef} onDrop={onDrop} onDragOver={e => e.preventDefault()}
            style={{ position: 'relative', width: pageW * zoom, height: pageH * zoom, boxShadow: '0 4px 24px rgba(0,0,0,0.12)', background: 'var(--white)', cursor: (locked && tool !== 'select') ? 'crosshair' : 'default' }}>
            {/* R1: el zoom el fa Konva (scaleX/scaleY) re-pintant els vectors a la mida real ×
                devicePixelRatio → NÍTID a qualsevol zoom. Ja no s'escala el bitmap per CSS. */}
            <Stage ref={stageRef} width={pageW * zoom} height={pageH * zoom} scaleX={zoom} scaleY={zoom}
              onMouseDown={onStageMouseDown} onMouseMove={onStageMouseMove} onMouseUp={onStageMouseUp}>
              {/* Fons blanc + 3 capes en ordre z. Konva no agrupa per `layer`:
                  ordenem els objectes i pintem en una sola Layer (z per ordre d'array). */}
              <Layer>
                <Rect x={0} y={0} width={pageW} height={pageH} fill={KONVA_COL.white} listening={false} />
                {ordered.filter(o => o.id !== editingFlatId).map(o => (
                  <ObjectNode key={o.id} obj={o} src={o.src}
                    tableData={tableData} modelData={model} versio={sheet?.versio} customerLogoUrl={customerLogoUrl}
                    selected={selectedIds.includes(o.id)}
                    selectable={locked && o.layer !== 'template'}
                    draggable={locked && tool === 'select' && o.layer !== 'template'}
                    onSelect={(e) => handleSelectObject(e, o.id)}
                    onDragEnd={handleDragEnd(o)}
                    onTransformEnd={handleTransformEnd(o)}
                    onDblText={() => startTextEdit(o)}
                    onDblVector={() => startVectorEdit(o)} />
                ))}
                {/* Forma temporal mentre es dibuixa */}
                {(drawTemp?.type === 'rect' || drawTemp?.type === 'rect_round') && <Rect x={drawTemp.x} y={drawTemp.y} width={drawTemp.w} height={drawTemp.h} stroke={KONVA_COL.gold} strokeWidth={1} dash={[4, 4]} cornerRadius={drawTemp.type === 'rect_round' ? 8 : 0} listening={false} />}
                {drawTemp?.type === 'ellipse' && <Ellipse x={drawTemp.x + drawTemp.w / 2} y={drawTemp.y + drawTemp.h / 2} radiusX={drawTemp.w / 2} radiusY={drawTemp.h / 2} stroke={KONVA_COL.textMain} strokeWidth={1} dash={[4, 4]} listening={false} />}
                {(drawTemp?.type === 'line' || drawTemp?.type === 'line_dot' || drawTemp?.type === 'draw') && <Line points={drawTemp.points} stroke={KONVA_COL.textMain} strokeWidth={1} dash={[4, 4]} listening={false} />}
                {(drawTemp?.type === 'arrow' || drawTemp?.type === 'arrow2') && <Arrow points={drawTemp.points} stroke={KONVA_COL.textMain} fill={KONVA_COL.textMain} strokeWidth={1.5} pointerLength={8} pointerWidth={6} pointerAtBeginning={drawTemp.type === 'arrow2'} listening={false} />}
                <Transformer ref={trRef} rotateEnabled ignoreStroke keepRatio={selectedObjects.length === 1 && selObj?.type === 'data_block'}
                  boundBoxFunc={(oldB, newB) => (newB.width < 10 || newB.height < 10 ? oldB : newB)} />
              </Layer>
            </Stage>

            {/* Textarea overlay per a l'edició inline de text */}
            {editingText && (
              <textarea
                autoFocus value={editingText.value}
                onChange={e => setEditingText(s => ({ ...s, value: e.target.value }))}
                onBlur={commitTextEdit}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commitTextEdit() } if (e.key === 'Escape') setEditingText(null) }}
                style={{ position: 'absolute', left: editingText.x * zoom, top: editingText.y * zoom, width: Math.max(80, editingText.w) * zoom, fontFamily: FONT, fontSize: `${12 * zoom}px`, color: COL.textMain, border: `1px solid ${COL.gold}`, padding: 2, resize: 'none', outline: 'none', background: 'var(--white)', zIndex: 10 }}
              />
            )}
          </div>
          {editingFlat && (
            <Suspense fallback={<div style={{ position: 'absolute', inset: 0, zIndex: 20, background: 'rgba(255,255,255,.65)', display: 'grid', placeItems: 'center', color: COL.textMuted, fontSize: 'var(--fs-body)' }}>{t('tech_sheet.flat_loading')}</div>}>
              <PaperFlatEditor
                flat={editingFlat}
                pageW={pageW}
                pageH={pageH}
                zoom={zoom}
                toPx={toPx}
                labels={paperFlatLabels}
                onCommit={commitFlatEdit}
                onCancel={() => setEditingFlatId(null)}
              />
            </Suspense>
          )}
          </div>
        </div>

        {/* ── Dreta: capes / inserir / propietats ── */}
        <aside style={{ width: 180, flexShrink: 0, borderLeft: `1px solid ${COL.border}`, background: COL.bg, display: 'flex', flexDirection: 'column', minHeight: 0, fontFamily: FONT }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 10px' }}>
            {/* Capes (C4): llista d'objectes de la pàgina (front a dalt) + z-order. */}
            <SectionTitle>{t('tech_sheet.layers')}</SectionTitle>
            {ordered.length === 0 ? (
              <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, margin: '0 0 8px' }}>{t('tech_sheet.layers_empty')}</p>
            ) : (
              <div style={{ marginBottom: 8, border: `1px solid ${COL.border}`, borderRadius: 5, overflow: 'hidden' }}>
                {[...ordered].reverse().map(o => {
                  const on = selectedIds.includes(o.id)
                  const icon = { text: 'ti-cursor-text', rect: 'ti-square', ellipse: 'ti-circle', line: 'ti-minus', arrow: 'ti-arrow-right', image: 'ti-photo', path: 'ti-vector', sketch_svg: 'ti-vector', data_block: 'ti-table', group: 'ti-box-multiple' }[o.type] || 'ti-shape'
                  const label = o.type === 'text' ? (o.text || t('tech_sheet.tool_text')) : o.type
                  return (
                    <div key={o.id} onClick={() => selectOnly(o.id)}
                      style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 6px', cursor: 'pointer', background: on ? COL.goldPale : 'transparent', color: on ? COL.gold : COL.textMain, borderBottom: `1px solid ${COL.border}` }}>
                      <i className={`ti ${icon}`} style={{ fontSize: 13, flexShrink: 0 }} />
                      <span style={{ flex: 1, fontSize: 'var(--fs-label)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</span>
                      {locked && o.layer === 'free' && (
                        <>
                          <button onClick={(e) => { e.stopPropagation(); selectOnly(o.id); moveSelectionInFreeLayer('forward') }} title={t('tech_sheet.bring_forward')}
                            style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', padding: 0, lineHeight: 1 }}><i className="ti ti-arrow-up" style={{ fontSize: 13 }} /></button>
                          <button onClick={(e) => { e.stopPropagation(); selectOnly(o.id); moveSelectionInFreeLayer('backward') }} title={t('tech_sheet.send_backward')}
                            style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', padding: 0, lineHeight: 1 }}><i className="ti ti-arrow-down" style={{ fontSize: 13 }} /></button>
                        </>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {/* Inserir blocs de dades */}
            <SectionTitle>{t('tech_sheet.insert_data_block')}</SectionTitle>
            <button onClick={insertHeader} disabled={!locked}
              style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', padding: '6px 8px', marginBottom: 6, border: 'none', borderRadius: 5, background: COL.gold, color: 'var(--white)', fontFamily: FONT, cursor: !locked ? 'default' : 'pointer', opacity: !locked ? 0.45 : 1 }}>
              <i className="ti ti-layout-navbar" style={{ fontSize: 13 }} /> {t('tech_sheet.model_header')}
            </button>
            <button onClick={insertLogo} disabled={!locked}
              title={customerLogoUrl ? t('tech_sheet.insert_logo_title') : t('tech_sheet.no_logo_title')}
              style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', padding: '6px 8px', marginBottom: 6, border: `1px solid ${COL.gold}`, borderRadius: 5, background: 'transparent', color: COL.gold, fontFamily: FONT, cursor: !locked ? 'default' : 'pointer', opacity: !locked ? 0.45 : 1 }}>
              <i className="ti ti-photo" style={{ fontSize: 13 }} /> {t('tech_sheet.client_logo')}
            </button>
            <button onClick={onAddTableClick} disabled={!locked || addingTable || !sizeFittings.length}
              style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', padding: '6px 8px', marginBottom: 6, border: 'none', borderRadius: 5, background: COL.gold, color: 'var(--white)', fontFamily: FONT, cursor: (!locked || !sizeFittings.length) ? 'default' : 'pointer', opacity: (!locked || addingTable || !sizeFittings.length) ? 0.45 : 1 }}>
              <i className="ti ti-table" style={{ fontSize: 13 }} /> {addingTable ? t('tech_sheet.adding') : t('tech_sheet.graded_table')}
            </button>
            <button onClick={insertFlatSketch} disabled={!locked}
              style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', padding: '6px 8px', marginBottom: 6, border: `1px solid ${COL.gold}`, borderRadius: 5, background: 'transparent', color: COL.gold, fontFamily: FONT, cursor: !locked ? 'default' : 'pointer', opacity: !locked ? 0.45 : 1 }}>
              <i className="ti ti-vector" style={{ fontSize: 13 }} /> {t('tech_sheet.flat_insert')}
            </button>
            <button onClick={() => flatFileRef.current?.click()} disabled={!locked}
              style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', padding: '6px 8px', marginBottom: 6, border: `1px solid ${COL.gold}`, borderRadius: 5, background: 'transparent', color: COL.gold, fontFamily: FONT, cursor: !locked ? 'default' : 'pointer', opacity: !locked ? 0.45 : 1 }}>
              <i className="ti ti-file-import" style={{ fontSize: 13 }} /> {t('tech_sheet.flat_import')}
            </button>
            <input ref={flatFileRef} type="file" accept=".svg,image/svg+xml" hidden
              onChange={e => { const f = e.target.files[0]; e.target.value = ''; handleFlatSvgFile(f) }} />
            {!sizeFittings.length && <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, margin: '0 0 8px' }}>{t('tech_sheet.no_size_fitting')}</p>}

            {/* Fitxers del model */}
            <SectionTitle>{t('tech_sheet.model_files', { n: fitxers.length })}</SectionTitle>
            {fitxers.length === 0 ? (
              <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted }}>{t('tech_sheet.no_files')}</p>
            ) : fitxers.map(f => {
              const hasUrl = !!(f.url_extern || f.fitxer)
              return (
                <button key={f.id} onClick={() => addModelFitxer(f)} disabled={!hasUrl || !locked}
                  title={f.nom_fitxer}
                  style={{ width: '100%', textAlign: 'left', fontSize: 'var(--fs-label)', padding: '5px 6px', marginBottom: 3, border: `1px solid ${COL.border}`, borderRadius: 4, background: COL.field, color: COL.textMain, fontFamily: FONT, cursor: (!hasUrl || !locked) ? 'default' : 'pointer', opacity: (!hasUrl || !locked) ? 0.5 : 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  <i className="ti ti-photo-plus" style={{ fontSize: 11, marginRight: 5 }} />{f.nom_fitxer}
                </button>
              )
            })}

            {/* Propietats de l'objecte seleccionat (TS-4b) */}
            {multiSelected && locked && (
              <>
                <SectionTitle>{t('tech_sheet.selected_objects', { n: selectedObjects.length })}</SectionTitle>
                <button type="button" onClick={groupSelection}
                  style={{ ...propInput, cursor: 'pointer', marginTop: 0, marginBottom: 8 }}>
                  <i className="ti ti-box-multiple" aria-hidden="true" /> {t('tech_sheet.group')}
                </button>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, marginBottom: 8 }}>
                  <button type="button" onClick={() => alignSelection('left')} title={t('tech_sheet.align_left')} style={{ ...propInput, cursor: 'pointer', marginTop: 0 }}>
                    <i className="ti ti-align-left" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => alignSelection('center')} title={t('tech_sheet.align_center')} style={{ ...propInput, cursor: 'pointer', marginTop: 0 }}>
                    <i className="ti ti-align-center" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => alignSelection('right')} title={t('tech_sheet.align_right')} style={{ ...propInput, cursor: 'pointer', marginTop: 0 }}>
                    <i className="ti ti-align-right" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => distributeSelection('h')} title={t('tech_sheet.distribute_h')} disabled={selectedObjects.length < 3} style={{ ...propInput, cursor: selectedObjects.length < 3 ? 'default' : 'pointer', marginTop: 0, opacity: selectedObjects.length < 3 ? 0.45 : 1 }}>
                    <i className="ti ti-distribute-horizontal" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => alignSelection('top')} title={t('tech_sheet.align_top')} style={{ ...propInput, cursor: 'pointer', marginTop: 0 }}>
                    <i className="ti ti-align-top" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => alignSelection('middle')} title={t('tech_sheet.align_middle')} style={{ ...propInput, cursor: 'pointer', marginTop: 0 }}>
                    <i className="ti ti-align-middle" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => alignSelection('bottom')} title={t('tech_sheet.align_bottom')} style={{ ...propInput, cursor: 'pointer', marginTop: 0 }}>
                    <i className="ti ti-align-bottom" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => distributeSelection('v')} title={t('tech_sheet.distribute_v')} disabled={selectedObjects.length < 3} style={{ ...propInput, cursor: selectedObjects.length < 3 ? 'default' : 'pointer', marginTop: 0, opacity: selectedObjects.length < 3 ? 0.45 : 1 }}>
                    <i className="ti ti-distribute-vertical" aria-hidden="true" />
                  </button>
                </div>
                {mirrorableIds.length === selectedObjects.length && (
                  <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                    <button type="button" onClick={() => mirrorObjects(mirrorableIds, 'scaleX')}
                      style={{ ...propInput, flex: 1, cursor: 'pointer', marginTop: 0 }}>
                      <i className="ti ti-flip-horizontal" aria-hidden="true" /> {t('tech_sheet.mirror_h')}
                    </button>
                    <button type="button" onClick={() => mirrorObjects(mirrorableIds, 'scaleY')}
                      style={{ ...propInput, flex: 1, cursor: 'pointer', marginTop: 0 }}>
                      <i className="ti ti-flip-vertical" aria-hidden="true" /> {t('tech_sheet.mirror_v')}
                    </button>
                  </div>
                )}
                {freeSelectedIds.length > 0 && (
                  <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                    <button type="button" onClick={() => moveSelectionInFreeLayer('backward')}
                      style={{ ...propInput, flex: 1, cursor: 'pointer', marginTop: 0 }}>
                      <i className="ti ti-arrow-down" aria-hidden="true" /> {t('tech_sheet.send_backward')}
                    </button>
                    <button type="button" onClick={() => moveSelectionInFreeLayer('forward')}
                      style={{ ...propInput, flex: 1, cursor: 'pointer', marginTop: 0 }}>
                      <i className="ti ti-arrow-up" aria-hidden="true" /> {t('tech_sheet.bring_forward')}
                    </button>
                  </div>
                )}
                {multiStroke.length > 0 && (
                  <div style={propLabel}>{t('tech_sheet.stroke_color')}
                    {!multiStrokeValue && <span style={{ display: 'block', color: COL.textMuted, marginTop: 2 }}>{t('tech_sheet.mixed_values')}</span>}
                    <ColorPicker value={multiStrokeValue || KONVA_COL.textMain}
                      onChange={c => updateObjects(multiStroke.map(o => o.id), o => ({ stroke: c, ...(o.type === 'arrow' ? { fill: c } : {}) }))} />
                  </div>
                )}
                {multiFill.length > 0 && (
                  <div style={propLabel}>{t('tech_sheet.fill')}
                    {!multiFillValue && <span style={{ display: 'block', color: COL.textMuted, marginTop: 2 }}>{t('tech_sheet.mixed_values')}</span>}
                    <ColorPicker value={multiFillValue || KONVA_COL.white}
                      onChange={c => updateObjects(multiFill.map(o => o.id), { fill: c })} />
                  </div>
                )}
                {multiPosition.length === selectedObjects.length && (
                  <div style={{ display: 'flex', gap: 6 }}>
                    <label style={{ ...propLabel, flex: 1 }}>{t('tech_sheet.pos_x')}
                      <input type="number" step={1} value={multiX === '' ? '' : Math.round(Number(multiX) * 10) / 10}
                        placeholder={t('tech_sheet.mixed_values')}
                        onChange={e => { if (e.target.value !== '') updateObjects(selectedIds, { x: Number(e.target.value) || 0 }) }} style={propInput} />
                    </label>
                    <label style={{ ...propLabel, flex: 1 }}>{t('tech_sheet.pos_y')}
                      <input type="number" step={1} value={multiY === '' ? '' : Math.round(Number(multiY) * 10) / 10}
                        placeholder={t('tech_sheet.mixed_values')}
                        onChange={e => { if (e.target.value !== '') updateObjects(selectedIds, { y: Number(e.target.value) || 0 }) }} style={propInput} />
                    </label>
                  </div>
                )}
              </>
            )}
            {selObj && locked && (
              <>
                <SectionTitle>{t('tech_sheet.element')} · {selObj.type}</SectionTitle>
                {selObj.type === 'text' && (
                  <>
                    <label style={propLabel}>{t('tech_sheet.font_size')}
                      <input type="number" min={6} max={48} value={selObj.fontSize || 11}
                        onChange={e => updateObject(selObj.id, { fontSize: Number(e.target.value) || 11 })} style={propInput} />
                    </label>
                    <label style={{ ...propLabel, display: 'flex', alignItems: 'center', gap: 6 }}>
                      <input type="checkbox" checked={selObj.fontStyle === 'bold'}
                        onChange={e => updateObject(selObj.id, { fontStyle: e.target.checked ? 'bold' : 'normal' })} />
                      {t('tech_sheet.bold')}
                    </label>
                    <div style={propLabel}>{t('tech_sheet.text_color')}
                      <ColorPicker value={selObj.fill || KONVA_COL.textMain} onChange={c => updateObject(selObj.id, { fill: c })} />
                    </div>
                  </>
                )}
                {(selObj.type === 'rect' || selObj.type === 'ellipse' || selObj.type === 'line' || selObj.type === 'arrow' || selObj.type === 'path') && (
                  <>
                    <div style={propLabel}>{t('tech_sheet.stroke_color')}
                      <ColorPicker value={selObj.stroke || KONVA_COL.textMain} onChange={c => updateObject(selObj.id, { stroke: c, ...(selObj.type === 'arrow' ? { fill: c } : {}) })} />
                    </div>
                    <label style={propLabel}>{t('tech_sheet.stroke_width')}
                      <input type="number" min={0.5} max={5} step={0.5} value={selObj.strokeWidth || (selObj.type === 'arrow' ? 1.5 : 1)}
                        onChange={e => updateObject(selObj.id, { strokeWidth: Number(e.target.value) || 1 })} style={propInput} />
                    </label>
                  </>
                )}
                {(selObj.type === 'rect' || selObj.type === 'ellipse' || selObj.type === 'path') && (
                  <div style={propLabel}>{t('tech_sheet.fill')}
                    <ColorPicker value={selObj.fill && selObj.fill !== 'transparent' ? selObj.fill : KONVA_COL.white} onChange={c => updateObject(selObj.id, { fill: c })} />
                  </div>
                )}
                {selObj.type === 'data_block' && (
                  <label style={propLabel}>{t('tech_sheet.scale_pct')}
                    <input type="number" min={10} max={200} step={5} value={Math.round((selObj.scale || 1) * 100)}
                      onChange={e => updateObject(selObj.id, { scale: Math.max(0.1, (Number(e.target.value) || 100) / 100) })} style={propInput} />
                  </label>
                )}
                {(selObj.type === 'sketch_svg' || selObj.type === 'path') && (
                  <>
                    <button type="button" onClick={editSelectedFlat}
                      style={{ ...propInput, cursor: 'pointer', marginTop: 0, marginBottom: 8 }}>
                      <i className="ti ti-vector-bezier" aria-hidden="true" /> {t('tech_sheet.flat_edit_nodes')}
                    </button>
                    {selObj.type === 'sketch_svg' && (
                      <button type="button" onClick={() => flatFileRef.current?.click()}
                        style={{ ...propInput, cursor: 'pointer', marginTop: 0, marginBottom: 8 }}>
                        <i className="ti ti-file-import" aria-hidden="true" /> {t('tech_sheet.flat_replace_svg')}
                      </button>
                    )}
                  </>
                )}
                {/* Posició X/Y (mm) per a objectes posicionats (no línia/fletxa). */}
                {selObj.type !== 'line' && selObj.type !== 'arrow' && (
                  <div style={{ display: 'flex', gap: 6 }}>
                    <label style={{ ...propLabel, flex: 1 }}>{t('tech_sheet.pos_x')}
                      <input type="number" step={1} value={Math.round((selObj.x || 0) * 10) / 10}
                        onChange={e => updateObject(selObj.id, { x: Number(e.target.value) || 0 })} style={propInput} />
                    </label>
                    <label style={{ ...propLabel, flex: 1 }}>{t('tech_sheet.pos_y')}
                      <input type="number" step={1} value={Math.round((selObj.y || 0) * 10) / 10}
                        onChange={e => updateObject(selObj.id, { y: Number(e.target.value) || 0 })} style={propInput} />
                    </label>
                  </div>
                )}
                {!blocksTransform(selObj) && (
                  <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                    <button type="button" onClick={() => mirrorObjects([selObj.id], 'scaleX')}
                      style={{ ...propInput, flex: 1, cursor: 'pointer', marginTop: 0 }}>
                      <i className="ti ti-flip-horizontal" aria-hidden="true" /> {t('tech_sheet.mirror_h')}
                    </button>
                    <button type="button" onClick={() => mirrorObjects([selObj.id], 'scaleY')}
                      style={{ ...propInput, flex: 1, cursor: 'pointer', marginTop: 0 }}>
                      <i className="ti ti-flip-vertical" aria-hidden="true" /> {t('tech_sheet.mirror_v')}
                    </button>
                  </div>
                )}
                {selObj.layer === 'free' && (
                  <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                    <button type="button" onClick={() => moveSelectionInFreeLayer('backward')}
                      style={{ ...propInput, flex: 1, cursor: 'pointer', marginTop: 0 }}>
                      <i className="ti ti-arrow-down" aria-hidden="true" /> {t('tech_sheet.send_backward')}
                    </button>
                    <button type="button" onClick={() => moveSelectionInFreeLayer('forward')}
                      style={{ ...propInput, flex: 1, cursor: 'pointer', marginTop: 0 }}>
                      <i className="ti ti-arrow-up" aria-hidden="true" /> {t('tech_sheet.bring_forward')}
                    </button>
                  </div>
                )}
                {!blocksTransform(selObj) && (
                  <label style={propLabel}>{t('tech_sheet.rotation_deg')}
                    <input type="number" min={0} max={360} step={1} value={Math.round(selObj.rotation || 0)}
                      onChange={e => updateObject(selObj.id, { rotation: ((Number(e.target.value) || 0) % 360 + 360) % 360 })} style={propInput} />
                  </label>
                )}
                {selObj.type === 'group' && (
                  <button type="button" onClick={() => ungroupObject(selObj.id)}
                    style={{ ...propInput, cursor: 'pointer', marginTop: 0, marginBottom: 8 }}>
                    <i className="ti ti-unlink" aria-hidden="true" /> {t('tech_sheet.ungroup')}
                  </button>
                )}
                {(selObj.layer === 'free' || selObj.type === 'data_block') && (
                  <button onClick={() => deleteObject(selObj.id)}
                    style={{ width: '100%', fontSize: 'var(--fs-body)', padding: '5px 8px', marginTop: 6, border: `1px solid #e74c3c`, borderRadius: 5, background: 'transparent', color: '#e74c3c', fontFamily: FONT, cursor: 'pointer' }}>
                    <i className="ti ti-trash" style={{ fontSize: 12, marginRight: 5 }} />{t('app.delete')}
                  </button>
                )}
              </>
            )}
          </div>
        </aside>
      </main>

      {/* ── Tira de pàgines horitzontal (C3) ── */}
      <div style={{ flexShrink: 0, background: COL.bg, borderTop: `1px solid ${COL.border}`, display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', overflowX: 'auto' }}>
        <span style={{ flexShrink: 0, color: COL.gold, fontSize: 'var(--fs-caption)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('tech_sheet.pages')}</span>
        {pages.map((p, i) => (
          <div key={p.id} onClick={() => { setCurrentPage(i); clearSelection() }} title={t('tech_sheet.page_n', { n: i + 1 })} style={{ position: 'relative', cursor: 'pointer', flexShrink: 0 }}>
            <div style={{ width: 56, height: 40, borderRadius: 3, overflow: 'hidden', background: 'var(--white)', border: currentPage === i ? `2px solid ${COL.gold}` : `1px solid ${COL.border}` }}>
              {thumbnails[i] && <img src={thumbnails[i]} alt={t('tech_sheet.page_n', { n: i + 1 })} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} />}
            </div>
            {locked && pages.length > 1 && (
              <button onClick={(e) => { e.stopPropagation(); removePage(i) }} title={t('tech_sheet.delete_page')}
                style={{ position: 'absolute', top: -4, right: -4, background: '#e74c3c', color: 'var(--white)', border: 'none', fontSize: 'var(--fs-caption)', lineHeight: '14px', width: 14, height: 14, padding: 0, borderRadius: '50%', cursor: 'pointer' }}>×</button>
            )}
          </div>
        ))}
        {locked && (
          <button onClick={addPage} title={t('tech_sheet.add_page')} style={{ flexShrink: 0, width: 56, height: 40, border: `1px dashed ${COL.gold}`, borderRadius: 4, background: 'transparent', color: COL.gold, fontFamily: FONT, cursor: 'pointer', fontSize: 18, lineHeight: 1 }}>+</button>
        )}
      </div>

      {/* ── Barra d'estat inferior (C3) ── */}
      <footer style={{ flexShrink: 0, background: COL.sidebar, borderTop: `1px solid ${COL.border}`, display: 'flex', alignItems: 'center', gap: 12, padding: '4px 12px', color: COL.textMuted, fontSize: 'var(--fs-label)' }}>
        <span style={{ fontWeight: 500, padding: '2px 8px', borderRadius: 10, background: badge.bg, color: badge.fg, whiteSpace: 'nowrap' }}>
          v{sheet?.versio ?? 1} · {badge.text}
        </span>
        {saveLabel && <span>{saveLabel}</span>}
        {notice && <span style={{ color: '#fcd34d', background: '#3a2e12', padding: '2px 8px', borderRadius: 6 }}>{notice}</span>}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4 }}>
          <button type="button" onClick={() => setZoomClamped(z => z - ZOOM_STEP)} title={t('tech_sheet.zoom_out')} style={{ ...headerBtn, padding: '3px 6px' }}>
            <i className="ti ti-minus" aria-hidden="true" style={{ fontSize: 13 }} />
          </button>
          <span title={t('tech_sheet.zoom_level')} style={{ minWidth: 42, textAlign: 'center', fontSize: 'var(--fs-body)', color: COL.textMain }}>{zoomLabel}</span>
          <button type="button" onClick={() => setZoomClamped(z => z + ZOOM_STEP)} title={t('tech_sheet.zoom_in')} style={{ ...headerBtn, padding: '3px 6px' }}>
            <i className="ti ti-plus" aria-hidden="true" style={{ fontSize: 13 }} />
          </button>
          <button type="button" onClick={() => setZoomClamped(1)} title={t('tech_sheet.zoom_reset')} style={{ ...headerBtn, padding: '3px 7px' }}>100%</button>
          <button type="button" onClick={fitZoomToViewport} title={t('tech_sheet.zoom_fit')} style={{ ...headerBtn, padding: '3px 6px' }}>
            <i className="ti ti-arrows-maximize" aria-hidden="true" style={{ fontSize: 13 }} />
          </button>
        </div>
      </footer>

      {/* Selector de size fitting (>1) */}
      {pickFitting && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }} onClick={() => setPickFitting(false)}>
          <div onClick={e => e.stopPropagation()} style={{ background: COL.bg, borderRadius: 12, padding: '1.4rem', maxWidth: 360, width: '90%', fontFamily: FONT, border: `1px solid ${COL.border}` }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 12 }}>{t('tech_sheet.pick_size_fitting')}</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {sizeFittings.map(sf => (
                <button key={sf.id} onClick={() => { setPickFitting(false); insertGradedTable(sf.id) }}
                  style={{ textAlign: 'left', fontSize: 'var(--fs-body)', padding: '8px 10px', border: `1px solid ${COL.border}`, borderRadius: 6, background: COL.field, color: COL.textMain, fontFamily: FONT, cursor: 'pointer' }}>
                  {sf.codi}{sf.tipus ? ` · ${sf.tipus}` : ''}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Selector de color ràpid (TS-4c): swatches de marca + color natiu ("Més colors").
// Literals: el color triat s'escriu a obj.fill/stroke i el pinta Konva (no resol var()).
const QUICK_COLORS = [KONVA_COL.textMain, '#185fa5', '#1d9e75', '#dc2626', KONVA_COL.gold, '#ca8a04']
export function ColorPicker({ value, onChange }) {
  const { t } = useTranslation()
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap', marginTop: 3 }}>
      {QUICK_COLORS.map(c => (
        <button key={c} type="button" onClick={() => onChange(c)} title={c}
          style={{ width: 18, height: 18, borderRadius: '50%', background: c, border: value === c ? `2px solid ${COL.textMain}` : `1px solid ${COL.border}`, cursor: 'pointer', padding: 0 }} />
      ))}
      <input type="color" value={value || KONVA_COL.textMain} onChange={e => onChange(e.target.value)} title={t('tech_sheet.more_colors')}
        style={{ width: 22, height: 22, border: 'none', borderRadius: 4, cursor: 'pointer', padding: 0, background: 'none' }} />
    </div>
  )
}

export function SectionTitle({ children }) {
  return <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, color: COL.gold, textTransform: 'uppercase', letterSpacing: '0.05em', margin: '12px 0 6px' }}>{children}</div>
}
export const propLabel = { display: 'block', fontSize: 'var(--fs-label)', color: COL.textMuted, marginBottom: 8 }
export const propInput = { width: '100%', fontFamily: FONT, fontSize: 'var(--fs-body)', padding: '4px 6px', marginTop: 3, border: `1px solid ${COL.border}`, borderRadius: 5, background: COL.field, color: COL.textMain, boxSizing: 'border-box' }
