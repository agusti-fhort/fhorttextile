import { useState, useEffect, useCallback, useRef, useMemo, lazy, Suspense } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
// Els builders de prims són funcions de mòdul (les comparteixen el canvas i el generador de
// PDF): no hi arriba el hook. `i18n.t` fora d'un component ja és patró de la casa
// (POMBrowser.jsx:642, RegistreActivitat.jsx:15) i respecta l'idioma actiu igualment.
import i18n from '../i18n'
import { Stage, Layer, Rect, Text, Line, Arrow, Ellipse, Image as KonvaImage, Transformer, Group, Path, Circle } from 'react-konva'
import Konva from 'konva'
import { PDFDocument } from 'pdf-lib'
import FhortLogo from '../components/brand/FhortLogo'
import FilePicker from '../components/model/FilePicker'
import AssetNavigator from '../components/assets/AssetNavigator'
import Contenidor from '../components/ui/Contenidor'
import { PomNamePair } from '../components/POMBrowser/POMBrowser'
import { useDocumentHistory, cloneWithNewIds, offsetObjectMm } from './ftt/history'
import { SNAP_PX, buildCandidates, computeSnap } from './ftt/snapping'
import { booleanOp } from './ftt/paperbool'
import { scaleSubpath, rotateSubpath, translateSubpath } from './ftt/paperOps'

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

// C5.3 — què compta com a "geometria" avui, a l'hora de filtrar la font FTT del panell d'import.
// Són els tipus que el canvas SAP rebre ara mateix: un SVG hi entra com a path editable i una
// imatge com a dataURL. PATRO/ESCALAT/MARCADA queden fora perquè són DXF, i el motor DXF encara
// no hi és (`import_dxf_soon`): oferir-los seria oferir un carreró sense sortida.
const TIPUS_GEOMETRIA = ['SKETCH_SVG', 'SKETCH_NET', 'SKETCH_FLETXES']
const GEOMETRIA_INSERIBLE = /\.(svg|png|jpe?g|webp|gif)$/i

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
// Peça 3: conjunt reduït de fonts (només fonts ja carregades + famílies genèriques web-safe; cap
// font externa nova). El valor és el fontFamily que Konva/CSS resoldran.
const FONT_OPTIONS = [
  { value: 'IBM Plex Mono, monospace', label: 'IBM Plex Mono' },
  { value: 'Montserrat, sans-serif', label: 'Montserrat' },
  { value: 'Arial, Helvetica, sans-serif', label: 'Arial' },
  { value: 'Georgia, serif', label: 'Georgia' },
  { value: 'Courier New, monospace', label: 'Courier New' },
]
// T1 (DECISIONS §3): la pell de la closca de l'editor usa els TOKENS GLOBALS de la plataforma
// (:root a index.css) per coherència amb la resta del SaaS — substitueix els literals dark/
// SolidWorks dels commits f77309e/233f10f-9c3c0de. COL és el mapa DOM→token (var() resol al DOM);
// KONVA_COL (canvas) NO es toca.
export const COL = {
  sidebar: 'var(--white)',       // topbar/ribbon/peu: BLANC com la navbar del dashboard (no beix)
  gold: 'var(--gold)',           // accent (només per a accions principals)
  goldPale: 'var(--gold-pale)',  // estat actiu amb tint gold suau
  border: 'var(--border)',       // filet/vora subtil de la plataforma
  textMain: 'var(--text-main)',  // text principal
  textMuted: 'var(--text-muted)',// text secundari
  bg: 'var(--bg-card)',          // contenidors (paleta/dock/tira/panells): blanc-card amb filet
  // Fons de treball darrere el paper = el gris clar NEUTRE del dashboard (<main> usa --gray-l),
  // no --bg-muted (que és beix càlid i reintroduiria el to taronjós). Així el paper blanc destaca.
  work: 'var(--gray-l)',
  field: 'var(--white)',         // interior de controls: blanc net
  // Tokens compartits amb el Taller de Patró (llenguatge visual únic, diagnosi
  // DIAGNOSI_UNIFICACIO_LAYOUT_TALLER_FITXA §P4′.1): capçalera fosca de secció i semàfor
  // de veredicte. Cap hex nou — són els mateixos var() ja definits a index.css.
  charcoal: 'var(--charcoal)',   // fons de capçalera de contenidor col·lapsable
  ok: 'var(--ok)',               // verd de validació (semàfor "col·locat")
  okBg: 'var(--ok-bg)',
  err: 'var(--err)',             // vermell de marca (xip de veredicte fora de tolerància)
  errBg: 'var(--err-bg)',
}
// Paleta LITERAL del canvas: Konva pinta sobre <canvas> via ctx.fillStyle i NO resol
// CSS custom properties → var(--token) cau a #000 (negre). Els primitius Konva (ObjectNode,
// build*Primitives, Rects de fons/selecció, text_box, previews) DEUEN usar aquests literals,
// no COL (que és per al DOM, on var() sí resol). Valors = mateixos hex que els tokens de :root.
// `pom` = vermell saturat de la COTA DE POM al croquis (fletxa + fons de l'etiqueta). Reusa el
// literal que ja fa servir la columna de nomenclatura de les taules snapshot (TBL.REF, més avall)
// per no introduir un segon vermell al mateix llenç.
const KONVA_COL = { white: '#ffffff', gold: '#c27a2a', goldPale: '#f5e6d0', border: '#e0d5c5', textMain: '#1d1d1b', textMuted: '#868685', labelGray: '#777776', pom: '#dc2626' }

// F1 — la caixa on entra una peça de patró. Una peça és MOLT més gran que la pàgina (el
// TATE_FRONT fa 588×502 mm i un A4 apaïsat en fa 297×210): entra encaixada a aquesta caixa,
// mai a mida real, i des d'aquí es redimensiona a mà com qualsevol imatge.
const PIECE_BOX_W = 110
const PIECE_BOX_H = 78

const LAYER_ORDER = { template: 0, data: 1, free: 2 }
const ZOOM_MIN = 0.25
const ZOOM_MAX = 8   // F6 — més zoom per a la precisió de l'edició de nodes (abans 4)
const ZOOM_STEP = 0.1
const RULER_SIZE = 18   // S2: gruix (px) de les regles superior/esquerra
// TS-4c — eines per "família" de creació (mateixa mecànica de drag).
const RECT_TOOLS = ['rect', 'rect_round', 'ellipse']   // drag = bounding box
const LINE_TOOLS = ['line', 'line_dot', 'arrow', 'arrow2']   // drag = 2 punts
// Peça C: eines que mostren cursor de creu (dibuix + nodes). 'select' → fletxa; 'pan' → grab.
const CROSSHAIR_TOOLS = [...RECT_TOOLS, ...LINE_TOOLS, 'draw', 'pen', 'arrow_curve', 'polygon', 'note', 'cota_pom']
// S3b — dreceres de teclat de les eines (mostrades al tooltip de la paleta per a la descobribilitat).
const TOOL_SHORTCUT = { select: 'V', node: 'A', text: 'T', rect: 'R', ellipse: 'E', line: 'L', pen: 'P' }
// S8: tipus convertibles a Paper.js (objectToPaperPath) — únics vàlids per al pathfinder.
const PATHFINDER_TYPES = ['path', 'rect', 'rect_round', 'ellipse']
// S7c2: polígon regular de N costats inscrit al bbox de drag → punts (px de contingut).
const polygonPoints = (x, y, w, h, n) => {
  const cx = x + w / 2, cy = y + h / 2, rx = w / 2, ry = h / 2
  const pts = []
  for (let k = 0; k < n; k++) {
    const a = -Math.PI / 2 + (2 * Math.PI * k) / n
    pts.push(cx + rx * Math.cos(a), cy + ry * Math.sin(a))
  }
  return pts
}
const PRESET_TOOLS = ['preset_callout', 'preset_detail_circle', 'preset_legend', 'preset_cota_pom', 'preset_annotation']
export const uid = () => (crypto.randomUUID ? crypto.randomUUID() : `id-${Math.round(performance.now())}-${Math.floor(Math.random() * 1e9)}`)
// A4 — AMPLADA REAL D'UN TEXT, en mm. Konva sap mesurar (mesura amb la mateixa família i
// mida que pintarà), però enlloc del fitxer se li demanava: per això l'etiqueta de la cota
// tenia una amplada fixa i "A" ocupava el mateix que "1/2 CHEST WIDTH".
// Es mesura FORA de textBoxParts, a la inserció i en editar el text, i el resultat es desa a
// obj.width — que és el que textBoxParts ja consumeix. Així el descriptor segueix sent una
// funció pura de l'objecte i la paritat pantalla=PDF es manté per construcció.
const TEXT_PAD_X_PX = 7    // marge lateral del fons, en px de pàgina
const TEXT_PAD_Y_PX = 4    // marge vertical (l'aplica textBoxParts via bgPadding)
export function measureTextWidthMm({ text, fontSize, fontFamily, fontStyle }) {
  const node = new Konva.Text({
    text: text || '', fontSize: fontSize || 11, fontFamily: fontFamily || FONT,
    fontStyle: fontStyle || 'normal',
  })
  const w = node.getTextWidth()
  node.destroy()
  return toMm(w + TEXT_PAD_X_PX * 2)
}
export const toPx = (mm) => mm * MM_TO_PX
export const toMm = (px) => px / MM_TO_PX

// S5-1: catàleg de camps (ModelDetailSerializer §4.4). Únics vàlids — NO n'afegim d'altres
// (marca/dissenyador/patronista NO existeixen al model). Es resolen server-side en instanciar
// un document des de la plantilla (commits posteriors); aquí només s'insereixen com a xip.
const FIELD_CATALOG = [
  { key: 'nom_prenda', tk: 'field_nom_prenda' },
  { key: 'codi_intern', tk: 'field_codi_intern' },
  { key: 'codi_client', tk: 'field_codi_client' },
  { key: 'customer_nom', tk: 'field_customer_nom' },
  { key: 'collection', tk: 'field_collection' },
  { key: 'temporada_any', tk: 'field_temporada_any' },
  { key: 'color_referencia', tk: 'field_color_referencia' },
  { key: 'descripcio', tk: 'field_descripcio' },
  { key: 'responsable_nom', tk: 'field_responsable_nom' },
  { key: 'data_entrada', tk: 'field_data_entrada' },
  { key: 'base_size_label', tk: 'field_base_size_label' },
  { key: 'size_system_nom', tk: 'field_size_system_nom' },
  { key: 'fabric_main', tk: 'field_fabric_main' },
  { key: 'fabric_composition', tk: 'field_fabric_composition' },
  { key: 'customer_logo', tk: 'field_customer_logo' },
  { key: 'data_avui', tk: 'field_data_avui' },
]


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
    const pts = (obj.paths || []).flatMap(path => entrySegments(path).flatMap(seg => {
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
      guides: p.guides || [],   // S2: guies (no s'exporten a PDF)
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
      guides: p.guides || [],   // S2: guies (no s'exporten a PDF)
    })),
  }
}

// ─── (TS-2) El pipeline SVG→PNG de taules s'ha retirat: les taules ara són blocs
// Konva natius (vegeu buildTablePrimitives / GradedTableNode). Es mantenen només els
// helpers d'imatge (loadImageEl/useImage) per a croquis i fitxers del model. ───

// blob → dataURL. Els dos consumidors (assets del .ftt en carregar, bytes importats del
// tenant) necessiten el MATEIX gest, i fer-lo dos cops seria dues maneres de fallar.
function blobToDataURL(blob) {
  return new Promise((res, rej) => {
    const fr = new FileReader()
    fr.onload = () => res(fr.result)
    fr.onerror = () => rej(new Error('fr'))
    fr.readAsDataURL(blob)
  })
}

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
// T3 — padding vertical de la taula VIVA (buildTableCellPrimitives): mínim llegible, per
// guanyar densitat a les taules llargues (T1b amb moltes talles). Punt d'ajust únic: cau a
// totes les variants (T1a/T1b/T2/custom), que comparteixen aquest builder. El builder legacy
// (buildTablePrimitives) conserva T_ROW_PAD: no es toca la geometria d'una superfície morta.
const T_CELL_PAD_Y = 2
const T_ROW_H = T_FONT + T_FONT_CA + T_ROW_PAD * 3   // dalt nom_en + entre + baix nom_ca
const T_HDR_H = T_FONT + T_ROW_PAD * 2               // capçalera d'una línia
const T_REF_W = 22 * MM_TO_PX     // nomenclatura del croquis (nom_fitxa)
const T_NOM_W = 58 * MM_TO_PX     // Nom EN + CA en dues línies a la mateixa cel·la
const T_VAL_W = 18 * MM_TO_PX     // valor per talla
const T_DELTA_W = 16 * MM_TO_PX   // delta (Δ) — UNA sola columna (valor de GradingRule)
const T_PAD = 2 * MM_TO_PX
// T1 — la talla base es marca amb la paleta discreta de domini (grisos + el vermell que ja
// identifica la nomenclatura POM), NO amb el gold d'interfície: dins la taula el gold és la
// vora del bloc i confondria "columna de referència" amb "objecte seleccionat".
const TBL = {
  HDR_BG: '#111827', HDR_TEXT: KONVA_COL.white, ROW_EVEN: KONVA_COL.white, ROW_ODD: '#f7f7f7',
  ROW_BORDER: KONVA_COL.border, OUTER: KONVA_COL.gold, REF: '#dc2626', NOM: '#6b7280', VAL: KONVA_COL.textMain,
  BASE_BG: '#e5e7eb', BASE_HDR: '#dc2626', BREAK: '#dc2626', DELTA: '#185fa5',
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

// Taula genèrica (S3): columnes/files lliures (POM fitting/grading, BOM, custom) → {prims, totalW, totalH}.
// Mateix patró de primitives que buildTablePrimitives (sibling, NO la sobrecarreguem). Sense fetch:
// obj ja porta columns/rows resolts (snapshot). Cos mínim 8pt (llei fitxa tècnica).
function buildTableCellPrimitives(obj) {
  const cols = obj.columns || []
  const rows = obj.rows || []
  const st = obj.style || {}
  const pt = Math.max(8, st.fontSize || 9)
  const fontPx = Math.round(pt * 0.3528 * MM_TO_PX)   // pt → mm → px
  const subPx = Math.round(fontPx * 0.8)
  const cw = cols.map(c => Math.max(6, (c.width || 24)) * MM_TO_PX)
  const totalW = cw.reduce((a, b) => a + b, 0) || MM_TO_PX * 40
  // Cel·la = string | { text, sub?, bold? } (S3: POM bilingüe a T1a, breaks en negreta a T1b).
  // Si alguna cel·la porta `sub`, TOTA la taula passa a fila de dues línies (mateix patró
  // que buildTablePrimitives amb nom_en/nom_ca).
  const norm = (c) => (c && typeof c === 'object') ? c : { text: String(c ?? '') }
  const hasSub = rows.some(row => row.some(c => norm(c).sub))
  const rowH = hasSub ? fontPx * 2 + T_CELL_PAD_Y * 3 : fontPx + T_CELL_PAD_Y * 2
  const hdrH = fontPx + T_CELL_PAD_Y * 2
  const totalH = hdrH + rows.length * rowH
  // Offsets x acumulats per columna: els necessiten la capçalera, el contingut i el realçat
  // de la talla base (que és una franja vertical, no una cel·la).
  const cx0 = []
  cw.reduce((acc, w) => { cx0.push(acc); return acc + w }, 0)
  const baseIdx = cols.findIndex(c => c.base)   // T1 — columna de la talla base (T1b); -1 si no n'hi ha
  const prims = []

  // Capçalera
  prims.push({ t: 'r', x: 0, y: 0, w: totalW, h: hdrH, fill: st.headerFill || TBL.HDR_BG })
  if (baseIdx >= 0) prims.push({ t: 'r', x: cx0[baseIdx], y: 0, w: cw[baseIdx], h: hdrH, fill: TBL.BASE_HDR })
  cols.forEach((c, i) => {
    prims.push({ t: 't', x: cx0[i] + T_PAD, y: 0, w: cw[i] - 2 * T_PAD, h: hdrH, text: String(c.label ?? ''), fill: TBL.HDR_TEXT, size: fontPx, bold: true, mid: true })
  })

  // Fons de files (zebra opcional) en passada pròpia: la franja de la talla base ha de quedar
  // PER SOBRE dels fons i PER SOTA del text (mateix ordre que buildTablePrimitives).
  if (st.zebra) rows.forEach((row, ri) => {
    prims.push({ t: 'r', x: 0, y: hdrH + ri * rowH, w: totalW, h: rowH, fill: ri % 2 === 0 ? TBL.ROW_EVEN : TBL.ROW_ODD })
  })
  if (baseIdx >= 0 && rows.length) {
    prims.push({ t: 'r', x: cx0[baseIdx], y: hdrH, w: cw[baseIdx], h: rows.length * rowH, fill: TBL.BASE_BG })
  }

  // Contingut
  rows.forEach((row, ri) => {
    const y = hdrH + ri * rowH
    let cxR = 0
    cols.forEach((c, i) => {
      const cell = norm(row[i])
      const wCell = cw[i] - 2 * T_PAD
      // T2 — dues senyals que MAI comparteixen codificació:
      //  · ESTRUCTURAL (jerarquia de taula): capçalera i primera columna, sempre en negreta.
      //  · BREAK de grading (domini, `cell.bold` de cellForSize a T1b): negreta + subratllat
      //    + vermell. El segon tret és el que el distingeix de l'estructural; el patró és el
      //    mateix bold+underline amb què la capçalera marca la talla base al size run.
      const isBreak = !!cell.bold
      const bold = isBreak || i === 0
      const fill = isBreak ? TBL.BREAK : TBL.VAL
      if (cell.sub) {
        prims.push({ t: 't', x: cxR + T_PAD, y: y + T_CELL_PAD_Y, w: wCell, h: fontPx + 2, text: cell.text || '', fill, size: fontPx, bold, underline: isBreak, mid: false })
        prims.push({ t: 't', x: cxR + T_PAD, y: y + T_CELL_PAD_Y * 2 + fontPx, w: wCell, h: subPx + 2, text: cell.sub, fill: TBL.NOM, size: subPx, italic: true, mid: false })
      } else {
        prims.push({ t: 't', x: cxR + T_PAD, y, w: wCell, h: rowH, text: cell.text || '', fill, size: fontPx, bold, underline: isBreak, mid: true })
      }
      cxR += cw[i]
    })
    prims.push({ t: 'l', points: [0, y + rowH, totalW, y + rowH], stroke: TBL.ROW_BORDER, sw: 0.5 })
  })

  // Separadors verticals (interns) + vora exterior
  let cxV = cw[0] || 0
  cw.slice(1).forEach(w => { prims.push({ t: 'l', points: [cxV, 0, cxV, totalH], stroke: TBL.ROW_BORDER, sw: 0.5 }); cxV += w })
  prims.push({ t: 'r', x: 0, y: 0, w: totalW, h: totalH, stroke: TBL.OUTER, sw: 1.5 })
  return { prims, totalW, totalH }
}

// Camp (S5-1): xip de placeholder d'un camp del catàleg → {prims, totalW, totalH}. Es RESOL
// server-side en instanciar un document des de la plantilla (commits posteriors); aquí és
// només un xip visual (vora punejada gold) amb el label literal entre claus.
function buildFieldChipPrims(obj) {
  const label = obj.label || obj.key || ''
  const text = '{' + label + '}'
  const fontPx = Math.round((obj.style?.fontSize || 11) * 0.3528 * MM_TO_PX)   // pt → mm → px
  const w = Math.max(30 * MM_TO_PX, (text.length * fontPx * 0.6) + 8 * MM_TO_PX)
  const h = fontPx + 8
  const prims = [
    { t: 'r', x: 0, y: 0, w, h, fill: KONVA_COL.goldPale, stroke: KONVA_COL.gold, sw: 1, dash: [3, 2] },
    { t: 't', x: 4, y: 0, w: w - 8, h, text, fill: KONVA_COL.gold, size: fontPx, mid: true },
  ]
  return { prims, totalW: w, totalH: h }
}

// pt → px (via mm: 1pt=0.3528mm, MM_TO_PX px/mm). El header v2 dosifica cossos en pt reals
// (petits i densos) a diferència del legacy, que mesurava en mm.
const _ptPx = pt => Math.round(pt * 0.3528 * MM_TO_PX)

// Amples per defecte dels 4 blocs del header v2 (percentatges de 277mm). Sobreescriptibles
// per la config de la plantilla (per customer, sense hardcodejar cap client al codi).
const HDR_V2_BLOCKS = [24, 24, 32, 20]
const HDR_V2_HEIGHT_MM = 31
const HDR_V2_LOGO_MAX_MM = 10

// Rectangle del logo del customer al header v2: contingut dins el BLOC 4 (dalt-dreta),
// alçada màxima ~10mm i amplada acotada a l'ample del bloc, preservant la relació d'aspecte.
// Compartit per la vista viva (Konva React) i l'export offscreen perquè no derivin.
export function headerV2LogoRect(natW, natH, totalW, config) {
  const widths = (config && config.blocks) || HDR_V2_BLOCKS
  const maxH = ((config && config.logoMaxMm) || HDR_V2_LOGO_MAX_MM) * MM_TO_PX
  const PAD = 1.6 * MM_TO_PX
  const ratio = (natW && natH) ? natW / natH : 2.4
  let h = maxH, w = maxH * ratio
  const b4start = totalW * (widths.slice(0, 3).reduce((a, b) => a + b, 0) / 100)
  const b4w = totalW * (widths[3] / 100)
  const maxW = b4w - 2 * PAD
  if (w > maxW) { w = maxW; h = w / ratio }
  return { x: b4start + b4w - PAD - w, y: PAD, w, h }
}

// Header v2 → {prims, totalW, totalH}. Una sola caixa (fons blanc, vora 0.75pt) de 277mm
// dividida en 4 blocs per 3 filets verticals (0.5pt). Etiquetes regular gris + valors negre;
// bold només a la ref del client i al nom. Anglès (excepció i18n conscient, com l'original
// LOSAN: és una capçalera de document tècnic, no crom d'app). El logo el pinta el caller.
// El mapping de camps és EL disseny pactat; els amples/mides viuen a `config` (per customer).
function buildHeaderV2Primitives(m, versio, placeholderMode, config) {
  const C = config || {}
  const W = 277 * MM_TO_PX
  const H = (C.heightMm || HDR_V2_HEIGHT_MM) * MM_TO_PX
  const widths = C.blocks || HDR_V2_BLOCKS
  const PAD = 1.6 * MM_TO_PX
  const SZ = { head: _ptPx(9), body: _ptPx(8), small: _ptPx(7) }
  const LABEL = KONVA_COL.textMuted, VALUE = KONVA_COL.textMain
  const OUTER_SW = 0.75 * 0.3528 * MM_TO_PX, FILET_SW = 0.5 * 0.3528 * MM_TO_PX
  const bx = []; let acc = 0
  for (const w of widths) { bx.push(acc); acc += (w / 100) * W }
  const bw = i => (widths[i] / 100) * W
  const prims = []
  // Caixa: fons blanc (sense color, i alhora àrea de clic per seleccionar/moure) + vora fina.
  prims.push({ t: 'r', x: 0, y: 0, w: W, h: H, fill: KONVA_COL.white, stroke: LABEL, sw: OUTER_SW })
  for (let i = 1; i < widths.length; i++) prims.push({ t: 'l', points: [bx[i], 0, bx[i], H], stroke: LABEL, sw: FILET_SW })

  // Apila línies dins un bloc; label gris + valor negre (monospace → amplada de label determinista).
  const draw = (bi, lines) => {
    const x0 = bx[bi] + PAD, maxW = bw(bi) - 2 * PAD
    let y = PAD
    for (const ln of lines) {
      if (!ln) continue
      const size = ln.size || SZ.body, lh = Math.round(size * 1.5)
      if (ln.label) {
        const lw = ln.label.length * size * 0.62
        prims.push({ t: 't', x: x0, y, w: lw + 2, h: lh, text: ln.label, fill: LABEL, size, mid: false })
        prims.push({ t: 't', x: x0 + lw, y, w: maxW - lw, h: lh, text: ln.value, fill: VALUE, size, bold: !!ln.bold, mid: false })
      } else {
        prims.push({ t: 't', x: x0, y, w: maxW, h: lh, text: ln.value, fill: VALUE, size, bold: !!ln.bold, align: ln.align, mid: false })
      }
      y += lh
    }
  }
  const V = (real, ph) => placeholderMode ? ph : (real || '')
  const kv = (label, value, size) => value ? { label, value, size } : null

  // BLOC 1 — Identitat (ref client + nom en bold; FTT ref petit)
  draw(0, [
    V(m?.codi_client, '{ref client}') ? { value: V(m?.codi_client, '{ref client}'), bold: true, size: SZ.head } : null,
    V(m?.nom_prenda, '{nom}') ? { value: V(m?.nom_prenda, '{nom}'), bold: true, size: SZ.body } : null,
    kv('FTT ref: ', V(m?.codi_intern, '{codi FTT}'), SZ.small),
  ])
  // BLOC 2 — Context
  draw(1, [
    kv('Collection: ', V(m?.collection, '{collection}'), SZ.body),
    kv('Season: ', V(m?.temporada, '{season}'), SZ.body),
    kv('Customer: ', V(m?.customer_nom, '{customer}'), SZ.body),
    kv('Target: ', V(m?.target, '{target}'), SZ.body),
  ])
  // BLOC 3 — Definició tècnica (run sencer d'etiquetes + base; grading o "pending")
  const run = _headerSizeRun(m, placeholderMode)
  const grading = placeholderMode ? '{grading}' : (m?.grading_rule_set_nom || 'pending')
  draw(2, [
    kv('Garment: ', V(m?.garment_type_nom, '{garment}'), SZ.body),
    kv('Item: ', V(m?.garment_type_item_nom, '{item}'), SZ.body),
    kv('Sizes: ', run, SZ.small),
    kv('Grading: ', grading, SZ.small),
  ])
  // BLOC 4 — Marca i estat (logo el pinta el caller a dalt; text sota, alineat dreta)
  const b4x = bx[3] + PAD, b4w2 = bw(3) - 2 * PAD
  let y4 = ((C.logoMaxMm || HDR_V2_LOGO_MAX_MM) * MM_TO_PX) + 2 * PAD
  const today = placeholderMode ? '{date}' : new Date().toISOString().slice(0, 10)
  for (const s of [today, V(m?.fase_actual, '{phase}'), V(m?.responsable_nom, '{owner}'), `v${versio ?? 1}`]) {
    if (!s) continue
    prims.push({ t: 't', x: b4x, y: y4, w: b4w2, h: Math.round(SZ.small * 1.5), text: s, fill: VALUE, size: SZ.small, align: 'right', mid: false })
    y4 += Math.round(SZ.small * 1.5)
  }
  return { prims, totalW: W, totalH: H }
}

// Run de talles del model per a la línia "Sizes": totes les etiquetes de size_run_model
// (separades per ·/;/,) unides per " · ", amb " — base {talla}" si el model té talla base.
function _headerSizeRun(m, placeholderMode) {
  if (placeholderMode) return '{sizes}'
  const raw = (m?.size_run_model || '').trim()
  if (!raw) return ''
  const labels = raw.split(/[·;,]/).map(s => s.trim()).filter(Boolean)
  let s = labels.join(' · ')
  const base = (m?.base_size_label || '').trim()
  if (base) s += `  — base ${base}`
  return s
}

// Capçalera del model → {prims, totalW, totalH}. Amb `config.layout==='blocks4'` dibuixa el
// disseny v2 (4 blocs, per customer via config); sense config manté el header LEGACY intacte
// (dues bandes, 20mm+12mm) perquè els documents/plantilles existents no canviïn.
// placeholderMode=true (editor de plantilla): mostra `{model.codi}` etc. en lloc de valors
// reals (no hi ha model), excepte customer_nom que SÍ és real (la plantilla és per client).
// ─── Template FTT (S12) — capçalera mestra "3 caixes". REFERÈNCIA CANÒNICA:
// docs/spec/plantilla_capcalera_ftt.svg. Coordenades transcrites LITERALMENT de l'SVG (pt
// absoluts, viewBox A4L 841.9×595.3). NO s'interpreta, es MESURA. El canvas Konva té 1pt = P px
// (P = 0.3528*MM_TO_PX); a l'export P px torna a 1pt (CANVAS_W 713 ↔ PDF 841.89). Per això TANT
// geometria com cossos es multipliquen per P (el bug D5 era cossos 6/9 sense P). Els `y` de
// l'SVG són BASELINES → top Konva = baseline − ASC·cos.
const HDR_M = {
  OX: 28.6, OY: 39, W: 784.7, H: 90.2, D1: 170.3, D2: 491.8, PAD: 6,
  R1: 170.3, R2: 491.8, R3: 813.3,     // vores dretes de caixa 1/2/3
  SUB1: 105.45, SUB2: 337.05,          // subcolumnes (PAGE · SEASON)
  ASC: 0.8,                            // baseline→top ≈ 0.8·cos (IBM Plex Mono)
}
const _hdrP = () => 0.3528 * MM_TO_PX

// FONT ÚNICA de la posició/mida de l'OBJECTE capçalera mestra (mm), DERIVADA de la geometria de
// l'SVG canònic (HDR_M, en pt) × 0.3528 mm/pt. La usen l'insert manual (insertHeader) i, amb els
// MATEIXOS valors, la instanciació des de template (backend master_template._HEADER_OBJ). No
// tornar a escriure literals de posició del header en cap altre lloc.
const _PT_TO_MM = 0.3528
const _mm2 = pt => Math.round(pt * _PT_TO_MM * 100) / 100
export const MASTER_HEADER_GEOM = {
  x: _mm2(HDR_M.OX),      // 28.6pt  → 10.09mm
  y: _mm2(HDR_M.OY),      // 39pt    → 13.76mm
  width: _mm2(HDR_M.W),   // 784.7pt → 276.84mm
  height: _mm2(HDR_M.H),  // 90.2pt  → 31.82mm
}

// Logo del customer: zona x 34.6→164.3 (w 129.7) · y 42.7→81.8 (h 39.1) [alçada de les files
// 1-2 de la caixa 2: top etiqueta fila1 = 47.5−0.8·6 = 42.7 · bottom valor fila2 = 80+0.2·9 = 81.8].
// Contain amb aspecte preservat SENSE tope a la mida natural (pot fer UPSCALE fins que la primera
// dimensió topi): s = min(ZW/w_logo, ZH/h_logo). Alineat a l'ESQUERRA (x=34.6) i centrat vertical.
const HDR_LOGO = { X: 34.6, Y: 42.7, W: 129.7, H: 39.1 }
export function headerMasterLogoRect(natW, natH, _config) {
  const P = _hdrP()
  const { X, Y, W, H } = HDR_LOGO
  let wPt, hPt
  if (natW > 0 && natH > 0) {
    const s = Math.min(W / natW, H / natH)     // contain sense clamp s<=1 (creix fins a tocar)
    wPt = natW * s; hPt = natH * s
  } else {
    hPt = H; wPt = Math.min(W, H * 2.4)        // fallback aspecte 2.4 si no hi ha mida natural
  }
  return { x: (X - HDR_M.OX) * P, y: (Y - HDR_M.OY) * P + (H - hPt) * P / 2, w: wPt * P, h: hPt * P }
}

function _hdrDate(d) {
  const p = n => String(n).padStart(2, '0')
  return `${p(d.getDate())}-${p(d.getMonth() + 1)}-${d.getFullYear()}`   // DD-MM-YYYY (D7)
}

function buildMasterHeaderPrimitives(m, versio, placeholderMode, config, pageCtx) {
  const P = _hdrP()
  const { OX, OY, ASC } = HDR_M
  const W = HDR_M.W * P, H = HDR_M.H * P
  const GRAY = KONVA_COL.labelGray, INK = KONVA_COL.textMain, FRAME = KONVA_COL.textMain
  const gx = sx => (sx - OX) * P
  const prims = []
  // Marc ÚNIC + 2 divisòries (mai 3 rects — D4). Frame 0.5pt.
  prims.push({ t: 'r', x: 0, y: 0, w: W, h: H, fill: KONVA_COL.white, stroke: FRAME, sw: 0.5 * P })
  prims.push({ t: 'l', points: [gx(HDR_M.D1), 0, gx(HDR_M.D1), H], stroke: FRAME, sw: 0.5 * P })
  prims.push({ t: 'l', points: [gx(HDR_M.D2), 0, gx(HDR_M.D2), H], stroke: FRAME, sw: 0.5 * P })

  const V = (real, ph) => placeholderMode ? ph : (real == null ? '' : String(real))
  const join = parts => parts.filter(v => v != null && v !== '').join(' | ')   // UN valor per línia (D3)
  // Etiqueta 6pt a baseline `by`, x `sx`, fins a `rightPt`.
  const label = (sx, by, text, rightPt) => {
    const f = 6 * P
    prims.push({ t: 't', x: gx(sx), y: (by - OY) * P - ASC * f, w: (rightPt - HDR_M.PAD - sx) * P, h: f + 2, text, fill: GRAY, size: f })
  }
  // Valor 9pt (baixa a 8pt si no cap; el·lipsi via PrimNode). MAI desborda ni trenca línia.
  // B2 — `fk` (field key) marca les prims de VALOR que tenen una clau exacta a FIELD_CATALOG.
  // No canvia res del render (PrimNode l'ignora): serveix perquè, en materialitzar la
  // capçalera, aquell text pugui néixer com a `type:'field'` i seguir resolent-se sol en
  // instanciar una plantilla, en lloc de quedar congelat amb les dades d'aquest model.
  const value = (sx, by, text, rightPt, opts = {}) => {
    if (!text) return
    const availPt = rightPt - HDR_M.PAD - sx
    const fpt = (text.length * 9 * 0.6 > availPt) ? 8 : 9   // 9→8 = sòl de la llei
    const f = fpt * P
    prims.push({ t: 't', x: gx(sx), y: (by - OY) * P - ASC * f, w: availPt * P, h: f + 2, text, fill: INK, size: f, bold: !!opts.bold, fk: opts.fk })
  }

  // ── CAIXA 1 ── logo (files 1-2) · DATE+PAGE (fila 3) · TECHNICIAN (fila 4). DATE alineat amb MODEL.
  label(34.6, 92.5, 'DATE', HDR_M.SUB1)
  value(34.6, 102.5, placeholderMode ? '{date}' : _hdrDate(new Date()), HDR_M.SUB1, { fk: 'data_avui' })
  label(HDR_M.SUB1, 92.5, 'PAGE', HDR_M.R1)
  value(HDR_M.SUB1, 102.5, placeholderMode ? '{page}' : `${(pageCtx?.index ?? 0) + 1} / ${pageCtx?.total ?? 1}`, HDR_M.R1)
  label(34.6, 115, 'TECHNICIAN', HDR_M.R1)
  value(34.6, 125, V(m?.responsable_nom, '{technician}'), HDR_M.R1, { fk: 'responsable_nom' })

  // ── CAIXA 2 ── identificació de la peça (STYLE NAME → MODEL)
  label(176.3, 47.5, 'INTERNAL REFERENCE', HDR_M.SUB2)
  value(176.3, 57.5, V(m?.codi_intern, '{internal ref}'), HDR_M.SUB2, { fk: 'codi_intern' })
  label(HDR_M.SUB2, 47.5, 'SEASON', HDR_M.R2)
  value(HDR_M.SUB2, 57.5, placeholderMode ? '{season}' : [m?.temporada, m?.any].filter(Boolean).join(' '), HDR_M.R2, { fk: 'temporada_any' })
  label(176.3, 70, 'CLIENT REFERENCE', HDR_M.R2)
  value(176.3, 80, V(m?.codi_client, '{client ref}'), HDR_M.R2, { fk: 'codi_client' })
  label(176.3, 92.5, 'MODEL', HDR_M.R2)
  value(176.3, 102.5, V(m?.nom_prenda, '{model}'), HDR_M.R2, { fk: 'nom_prenda' })
  label(176.3, 115, 'COLLECTION', HDR_M.R2)
  value(176.3, 125, V(m?.collection, '{collection}'), HDR_M.R2, { fk: 'collection' })

  // ── CAIXA 3 ── definició tècnica · UNA etiqueta / UN valor per línia (D3)
  label(497.8, 47.5, 'GARMENT TYPE | ITEM', HDR_M.R3)
  value(497.8, 57.5, placeholderMode ? '{garment} | {item}' : join([m?.garment_type_nom, m?.garment_type_item_nom]), HDR_M.R3)
  label(497.8, 70, 'TARGET | FIT TYPE | CONSTRUCTION', HDR_M.R3)
  value(497.8, 80, placeholderMode ? '{target} | {fit} | {construction}' : join([m?.grading_target_nom, m?.grading_fit_nom, m?.grading_construction_nom]), HDR_M.R3)
  label(497.8, 92.5, 'SIZE SYSTEM', HDR_M.R3)
  value(497.8, 102.5, V(m?.size_system_nom, '{size system}'), HDR_M.R3, { fk: 'size_system_nom' })
  label(497.8, 115, 'SIZE RUN', HDR_M.R3)
  _pushSizeRun(prims, m, placeholderMode, 497.8, 125, P)

  return { prims, totalW: W, totalH: H }
}

// SIZE RUN: run compacte "·" (sense espais, com l'SVG). La talla base = segment PROPI
// bold+underline; el separador "·" NO es subratlla (D6). Mètrica mono charW=cos·0.6.
function _pushSizeRun(prims, m, placeholderMode, sx, by, P) {
  const f = 9 * P
  const OX = HDR_M.OX, y = (by - HDR_M.OY) * P - HDR_M.ASC * f
  const gx = x => (x - OX) * P
  const INK = KONVA_COL.textMain
  if (placeholderMode) {
    prims.push({ t: 't', x: gx(sx), y, w: 300 * P, h: f + 2, text: '{size run}', fill: INK, size: f })
    return
  }
  const raw = (m?.size_run_model || '').trim()
  if (!raw) return
  const labels = raw.split(/[·;,]/).map(s => s.trim()).filter(Boolean)
  const base = (m?.base_size_label || '').trim()
  const charWpt = 9 * 0.6
  let cxPt = sx
  const seg = (text, opts = {}) => {
    prims.push({ t: 't', x: gx(cxPt), y, w: text.length * charWpt * P + 4, h: f + 2, text, fill: INK, size: f, bold: !!opts.bold, underline: !!opts.underline })
    cxPt += text.length * charWpt
  }
  labels.forEach((lab, i) => {
    const isBase = base && lab === base
    seg(lab, isBase ? { bold: true, underline: true } : {})   // NOMÉS el label de la base (D6)
    if (i < labels.length - 1) seg('·')                        // separador net, sense underline
  })
}

// Capçalera del model → {prims, totalW, totalH}. `config.layout`: 'masterFtt' (Template FTT S12,
// 3 caixes, amb consciència de pàgina via pageCtx) · 'blocks4' (v2) · absent → LEGACY intacte
// (cap regressió a documents/plantilles existents).
export function buildHeaderPrimitives(m, versio, placeholderMode = false, hasLogo = false, config = null, pageCtx = null) {
  if (config && config.layout === 'masterFtt') return buildMasterHeaderPrimitives(m, versio, placeholderMode, config, pageCtx)
  if (config && config.layout === 'blocks4') return buildHeaderV2Primitives(m, versio, placeholderMode, config)
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
      stroke={p.stroke} strokeWidth={p.sw} dash={p.dash} listening={!!p.fill} />
  }
  if (p.t === 'l') {
    return <Line points={p.points} stroke={p.stroke} strokeWidth={p.sw} listening={false} />
  }
  return <Text x={p.x} y={p.y} width={p.w} height={p.h} text={p.text} fill={p.fill}
    fontSize={p.size} fontFamily={FONT} fontStyle={p.bold ? 'bold' : p.italic ? 'italic' : 'normal'}
    textDecoration={p.underline ? 'underline' : ''}
    align={p.align || 'left'} verticalAlign={p.mid ? 'middle' : 'top'}
    ellipsis wrap="none" listening={false} />
}

// Primitiva → node Konva imperatiu (render offscreen per a export/miniatures).
function addPrimsToGroup(group, prims) {
  for (const p of prims) {
    if (p.t === 'r') group.add(new Konva.Rect({ x: p.x, y: p.y, width: p.w, height: p.h, fill: p.fill, stroke: p.stroke, strokeWidth: p.sw, dash: p.dash }))
    else if (p.t === 'l') group.add(new Konva.Line({ points: p.points, stroke: p.stroke, strokeWidth: p.sw }))
    else group.add(new Konva.Text({ x: p.x, y: p.y, width: p.w, height: p.h, text: p.text, fill: p.fill, fontSize: p.size, fontFamily: FONT, fontStyle: p.bold ? 'bold' : p.italic ? 'italic' : 'normal', textDecoration: p.underline ? 'underline' : '', align: p.align || 'left', verticalAlign: p.mid ? 'middle' : 'top', ellipsis: true, wrap: 'none' }))
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

// Taula genèrica (S3) — mateix patró que GradedTableNode, columns/rows lliures (sense fetch).
function TableNode({ obj, groupProps, isSelected }) {
  const { prims, totalW, totalH } = useMemo(() => buildTableCellPrimitives(obj), [obj])
  // El rètol «per vincular» va amb els MATEIXOS prims que el PDF (addObjectToLayer).
  const pending = useMemo(
    () => (isPendentVincle(obj) ? buildPendingRibbonPrims(totalW, totalH) : []),
    [obj, totalW, totalH])
  return (
    <Group {...groupProps}>
      {prims.map((p, i) => <PrimNode key={i} p={p} />)}
      {pending.map((p, i) => <PrimNode key={`pv${i}`} p={p} />)}
      {isSelected && <Rect x={0} y={0} width={totalW} height={totalH} stroke={TBL.OUTER} strokeWidth={2} dash={[4, 3]} fill="transparent" listening={false} />}
    </Group>
  )
}

// Camp (S5-1) — xip de placeholder, mateix patró que TableNode (sense fetch: el label ja ve
// resolt a l'objecte). El valor real es resol server-side en instanciar un document.
function FieldChipNode({ obj, groupProps, isSelected }) {
  const { prims, totalW, totalH } = useMemo(() => buildFieldChipPrims(obj), [obj])
  return (
    <Group {...groupProps}>
      {prims.map((p, i) => <PrimNode key={i} p={p} />)}
      {isSelected && <Rect x={0} y={0} width={totalW} height={totalH} stroke={KONVA_COL.gold} strokeWidth={1.5} dash={[4, 3]} fill="transparent" listening={false} />}
    </Group>
  )
}

// Capçalera del model — Konva natiu. Resol els camps en render. Si hi ha logoUrl,
// es pinta el logo real (cantonada superior dreta) en lloc del placeholder "(logo)".
function HeaderBlock({ modelData, versio, placeholderMode, logoUrl, config, pageCtx, groupProps, isSelected }) {
  const logoImg = useImage(logoUrl || '')
  const hasLogo = !!logoImg
  const isV2 = !!(config && config.layout === 'blocks4')
  const isMaster = !!(config && config.layout === 'masterFtt')
  const { prims, totalW, totalH } = useMemo(
    () => buildHeaderPrimitives(modelData, versio, placeholderMode, hasLogo, config, pageCtx),
    [modelData, versio, placeholderMode, hasLogo, config, pageCtx])
  // master: logo a la caixa 1 (dalt-esq, ≤40pt); v2: logo contingut al BLOC 4; legacy: 40×16mm.
  const logoR = (hasLogo && isMaster)
    ? headerMasterLogoRect(logoImg.width, logoImg.height, config)
    : (hasLogo && isV2)
      ? headerV2LogoRect(logoImg.width, logoImg.height, totalW, config)
      : { x: totalW - 45 * MM_TO_PX, y: 2 * MM_TO_PX, w: 40 * MM_TO_PX, h: 16 * MM_TO_PX }
  return (
    <Group {...groupProps}>
      {prims.map((p, i) => <PrimNode key={i} p={p} />)}
      {hasLogo && <KonvaImage image={logoImg} x={logoR.x} y={logoR.y} width={logoR.w} height={logoR.h} listening={false} />}
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
      align: obj.align || 'left', textDecoration: obj.textDecoration || '',
    },
  }
}

function textProps(obj) {
  return {
    x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1, width: obj.width ? toPx(obj.width) : undefined,
    text: obj.text || '', fontSize: obj.fontSize || 11, fontFamily: obj.fontFamily || FONT,
    fontStyle: obj.fontStyle || 'normal', fill: obj.fill || KONVA_COL.textMain,
    align: obj.align || 'left', textDecoration: obj.textDecoration || '',
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

// Puntes per element (path i arrow). Els camps nous headStart/headEnd manen si són presents;
// si no, retrocompat: arrow2 (doble punta) = start+end, arrow simple = només end, path = cap.
function headConfig(obj) {
  if (obj.headStart !== undefined || obj.headEnd !== undefined) return { start: !!obj.headStart, end: !!obj.headEnd }
  if (obj.type === 'arrow') return { start: !!obj.arrow2, end: true }
  return { start: false, end: false }
}

function arrowProps(obj) {
  const cfg = headConfig(obj)
  return {
    x: 0, y: 0, rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1, points: [toPx(obj.x), toPx(obj.y), toPx(obj.x2), toPx(obj.y2)],
    stroke: obj.stroke || KONVA_COL.textMain, fill: obj.fill || obj.stroke || KONVA_COL.textMain,
    strokeWidth: obj.strokeWidth || 1.5, pointerLength: 8, pointerWidth: 6,
    pointerAtBeginning: cfg.start, pointerAtEnding: cfg.end,
  }
}

// Llegeix els segments d'una entrada paths[]: simple (segments) o compost (subpaths concatenats).
const entrySegments = (p) => (p.subpaths ? p.subpaths.flatMap(sp => sp.segments || []) : (p.segments || []))

function segmentsToData(segments, closed) {
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
  if (closed && segments.length > 1) {
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

// Compost (forats): concatena exterior + subpaths interiors en un sol 'd'; fillRule 'evenodd' fa el tall.
function pathToData(path) {
  if (path.subpaths?.length) return path.subpaths.map(sp => segmentsToData(sp.segments || [], !!sp.closed)).join(' ')
  return segmentsToData(path.segments || [], path.closed)
}

// COMMIT 5: geometria de puntes d'un path amb headStart/headEnd, orientades a la TANGENT.
// Retorna {x,y} (px, espai local del path) i angle (rad) de la direcció SORTINT de cada punta
// activa. Tangent d'un cúbic: a l'extrem C'(1)∝−inHandle; a l'inici C'(0)∝outHandle (invertit
// perquè la punta miri cap enfora). Fallback al parell on-curve si el tram és recte (handles 0).
function pathHeadAngles(obj) {
  const cfg = headConfig(obj)
  if (!cfg.start && !cfg.end) return []
  const segs = entrySegments((obj.paths || [])[0] || {})
  if (segs.length < 2) return []
  const heads = []
  if (cfg.end) {
    const last = segs[segs.length - 1], prev = segs[segs.length - 2]
    let dx = -(last.inX || 0), dy = -(last.inY || 0)
    if (Math.hypot(dx, dy) < 1e-6) { dx = last.x - prev.x; dy = last.y - prev.y }
    heads.push({ x: toPx(last.x), y: toPx(last.y), angle: Math.atan2(dy, dx) })
  }
  if (cfg.start) {
    const first = segs[0], next = segs[1]
    let dx = -(first.outX || 0), dy = -(first.outY || 0)
    if (Math.hypot(dx, dy) < 1e-6) { dx = first.x - next.x; dy = first.y - next.y }
    heads.push({ x: toPx(first.x), y: toPx(first.y), angle: Math.atan2(dy, dx) })
  }
  return heads
}
// Triangle de punta (px): vèrtex al tip, base retrocedida `len` al llarg de l'angle, amplada `wid`.
function headTriPoints(tipX, tipY, angle, len = 8, wid = 6) {
  const bx = tipX - Math.cos(angle) * len, by = tipY - Math.sin(angle) * len
  const nx = -Math.sin(angle) * (wid / 2), ny = Math.cos(angle) * (wid / 2)
  return [tipX, tipY, bx + nx, by + ny, bx - nx, by - ny]
}
function pathHeadColor(obj) {
  return normalizePaint((obj.paths?.[0]?.stroke) ?? obj.stroke) || KONVA_COL.textMain
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

// El peu d'una peça de patró: el nom del block, sota la imatge. Es dibuixa DINS del Group de
// la peça, i per això el Group porta width/height explícits (imageProps ja els hi posa): un
// Konva.Group sense width torna 0, i el camí genèric de transformEnd —que redimensiona amb
// node.width() × escala— li hauria clavat el mínim de 2 mm a la primera nansa que s'arrossegués.
function pieceCaptionProps(obj) {
  return {
    x: 0, y: toPx((obj.height || obj.width) + 1.2), width: toPx(obj.width),
    text: obj.piece_name || '',
    fontSize: Math.round(2.6 * MM_TO_PX), fontFamily: FONT,
    fill: KONVA_COL.textMuted, align: 'center',
  }
}

function dataBlockGroupProps(obj) {
  const scale = obj.scale || 1
  return { x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: scale * (obj.scaleX || 1), scaleY: scale * (obj.scaleY || 1) }
}

function dataBlockPlaceholderProps(obj) {
  return { width: toPx(obj.width || 120), height: toPx(obj.height || 40), fill: COL.goldPale, stroke: KONVA_COL.border, dash: [4, 4] }
}

// ── «Per vincular al model» (BIB S0) ───────────────────────────────────────────────────────
// Quan un document canvia de host, el descongelat (services_ftt_document.unfreeze_document)
// buida les taules que portaven les dades del model origen i les marca `pendent_vincle`. No
// és un error: és feina pendent, i la fa el tècnic amb un clic. El sistema no re-vincula sol.
//
// La regla dura és que ES VEGI, i que es vegi IGUAL als dos switches. Si el canvas mostrés el
// rètol i el generador de PDF s'ho callés, el document sortiria per la impressora amb un forat
// silenciós al lloc on hi havia les mesures — i un forat silenciós en un document que viatja al
// taller és pitjor que un error. Per això el rètol es construeix amb PRIMS, el llenguatge que
// ObjectNode i addObjectToLayer ja comparteixen: pintar-lo en un i no en l'altre és, per
// construcció, impossible.
const PENDING_RIBBON_H = 5 * MM_TO_PX

// Mirall de PENDING_MARK (services_ftt_document.py). El backend és qui posa la marca; el
// canvas no la dedueix mai d'un id a null, perquè un `graded_table` acabat d'inserir també
// en té un durant un instant i no és el mateix cas.
function isPendentVincle(obj) {
  return obj?.pendent_vincle === true
}

function pendingLabel() {
  return i18n.t('tech_sheet.pending_link')
}

// Bloc sense graella (graded_table desvinculada): la caixa sencera ÉS el rètol.
function buildPendingBoxPrims(obj) {
  const w = toPx(obj.width || 120)
  const h = toPx(obj.height || 40)
  return [
    { t: 'r', x: 0, y: 0, w, h, fill: KONVA_COL.goldPale, stroke: KONVA_COL.gold, sw: 1, dash: [4, 3] },
    { t: 't', x: T_PAD, y: 0, w: w - 2 * T_PAD, h, text: pendingLabel(), fill: KONVA_COL.textMain, size: Math.round(3.2 * MM_TO_PX), align: 'center', mid: true },
  ]
}

// Taula snapshot buidada: la graella es conserva (és del tècnic, no del host) i el rètol va
// SOTA, per no tapar-la. El tècnic veu l'esquelet del que hi havia i què li falta.
function buildPendingRibbonPrims(totalW, totalH) {
  const y = totalH + Math.round(1 * MM_TO_PX)
  return [
    { t: 'r', x: 0, y, w: totalW, h: PENDING_RIBBON_H, fill: KONVA_COL.goldPale, stroke: KONVA_COL.gold, sw: 1, dash: [4, 3] },
    { t: 't', x: T_PAD, y, w: totalW - 2 * T_PAD, h: PENDING_RIBBON_H, text: pendingLabel(), fill: KONVA_COL.textMain, size: Math.round(3 * MM_TO_PX), mid: true },
  ]
}

// A5 — BAKE DE LA TRANSFORMACIÓ A GEOMETRIA (llei "geometria sempre", S20).
// Un `path` amb els handles del Transformer desava l'escala i la rotació com a obj.scaleX/
// scaleY/rotation i deixava els segments intactes. Conseqüència: la geometria del model
// MENTIA (deia una cosa i se'n pintava una altra), i PaperFlatEditor havia de desfer la
// transformació a l'entrada i tornar-la a aplicar a la sortida per poder editar-hi nodes.
// Ara, en deixar anar el handle, la transformació entra als segments i l'objecte torna a
// neutre. Els primitius ja existien i són purs: només calia cridar-los des d'aquí.
function bakePathEntries(entries, sx, sy, deg) {
  const cook = (segs) => {
    let r = { segments: segs || [] }
    if (sx !== 1 || sy !== 1) r = scaleSubpath(r.segments, sx, sy, 0, 0)
    if (deg) r = rotateSubpath(r.segments, deg, 0, 0)
    return r.segments
  }
  // Una entrada pot ser simple {segments} o composta {subpaths:[{segments}]} (forats).
  return (entries || []).map(entry => (entry.subpaths
    ? { ...entry, subpaths: entry.subpaths.map(sp => ({ ...sp, segments: cook(sp.segments) })) }
    : { ...entry, segments: cook(entry.segments) }))
}

function blocksTransform(obj) {
  return obj && (obj.type === 'line' || obj.type === 'arrow' || obj.type === 'field' || (obj.type === 'text' && obj.bgFill))
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
    for (const child of orderedChildren) {
      if (child.visible === false) continue
      await addObjectToLayer(g, child, ctx)
    }
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
    // COMMIT 5: puntes de fletxa curva (path amb headStart/headEnd) orientades a la tangent.
    const headCol = pathHeadColor(obj)
    for (const h of pathHeadAngles(obj)) {
      g.add(new Konva.Line({ points: headTriPoints(h.x, h.y, h.angle), closed: true, fill: headCol, stroke: headCol, strokeWidth: 1 }))
    }
    layer.add(g)
    return
  }
  if (obj.type === 'data_block') {
    let built = null
    let logoEl = null
    if (obj.kind === 'header') {
      if (ctx?.customerLogoUrl) { try { logoEl = await loadImageEl(ctx.customerLogoUrl) } catch { logoEl = null } }
      const pageCtx = (ctx?.pageIndex != null) ? { index: ctx.pageIndex, total: ctx.pageTotal } : null
      built = buildHeaderPrimitives(ctx?.modelData, ctx?.versio, ctx?.placeholderMode, !!logoEl, obj.config, pageCtx)
    } else if (obj.kind === 'graded_table') {
      const data = ctx?.tableData?.[obj.id]
      // Desvinculada (BIB S0): no hi ha dades ni n'hi haurà fins que el tècnic la torni a
      // lligar. Abans, `built` es quedava a null i el bloc NO s'afegia a la capa: el PDF
      // sortia amb un forat mut on hi havia la taula. Ara el rètol hi va.
      if (isPendentVincle(obj)) built = { prims: buildPendingBoxPrims(obj) }
      else if (data) built = buildTablePrimitives(data)
    }
    if (built) {
      const g = new Konva.Group(dataBlockGroupProps(obj))
      addPrimsToGroup(g, built.prims)
      if (logoEl) {
        const lw = logoEl.naturalWidth || logoEl.width, lh = logoEl.naturalHeight || logoEl.height
        const isMaster = !!(obj.config && obj.config.layout === 'masterFtt')
        const isV2 = !!(obj.config && obj.config.layout === 'blocks4')
        const r = isMaster
          ? headerMasterLogoRect(lw, lh, obj.config)
          : isV2
            ? headerV2LogoRect(lw, lh, built.totalW, obj.config)
            : { x: built.totalW - 45 * MM_TO_PX, y: 2 * MM_TO_PX, w: 40 * MM_TO_PX, h: 16 * MM_TO_PX }
        g.add(new Konva.Image({ image: logoEl, x: r.x, y: r.y, width: r.w, height: r.h }))
      }
      layer.add(g)
    }
    return
  }
  if (obj.type === 'table') {
    const g = new Konva.Group(dataBlockGroupProps(obj))
    const { prims, totalW, totalH } = buildTableCellPrimitives(obj)
    addPrimsToGroup(g, prims)
    if (isPendentVincle(obj)) addPrimsToGroup(g, buildPendingRibbonPrims(totalW, totalH))
    layer.add(g)
    return
  }
  if (obj.type === 'field') {
    const g = new Konva.Group(dataBlockGroupProps(obj))
    addPrimsToGroup(g, buildFieldChipPrims(obj).prims)
    layer.add(g)
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
  if (obj.type === 'pattern_piece') {
    if (!obj.src) return
    try {
      const el = await loadImageEl(obj.src)
      const p = imageProps(obj)
      const g = new Konva.Group(p)
      g.add(new Konva.Image({ image: el, x: 0, y: 0, width: p.width, height: p.height }))
      if (obj.caption !== false) g.add(new Konva.Text(pieceCaptionProps(obj)))
      layer.add(g)
    } catch { /* peça no carregada → s'omet */ }
    return
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
    if (o.visible === false) continue
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
    guides: p.guides || [],   // S2: guies (no s'exporten a PDF)
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

// La peça de patró (F1): el render del motor, encaixat. Mateix mecanisme que una imatge
// —dataURL a `src`, per tant el backend l'extreu a asset com qualsevol altra— però amb el
// nom del block a sota i les proporcions bloquejades: una peça estirada de través ja no
// és la peça, és una mentida sobre la peça.
function PatternPieceObj({ obj, src, common }) {
  const img = useImage(src)
  const props = imageProps(obj)
  if (!img) {
    return <Rect {...common} width={props.width} height={props.height}
      scaleX={props.scaleX} scaleY={props.scaleY}
      fill={COL.goldPale} stroke={KONVA_COL.border} dash={[4, 4]} />
  }
  return (
    <Group {...common} width={props.width} height={props.height}>
      <KonvaImage image={img} x={0} y={0} width={props.width} height={props.height} />
      {obj.caption !== false && <Text {...pieceCaptionProps(obj)} />}
    </Group>
  )
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

// Bloc 1: extrems d'un line/arrow en px (espai de contingut), per pintar-hi les nanses de
// selecció i per al snap. 'arrow' porta x/y/x2/y2; 'line' el primer i últim parell de points[].
function endpointsPx(obj) {
  if (obj.type === 'arrow') return { start: { x: toPx(obj.x), y: toPx(obj.y) }, end: { x: toPx(obj.x2), y: toPx(obj.y2) } }
  const p = obj.points || []
  return { start: { x: toPx(p[0] || 0), y: toPx(p[1] || 0) }, end: { x: toPx(p[p.length - 2] || 0), y: toPx(p[p.length - 1] || 0) } }
}
// Nanses arrossegables als dos extrems (substitueixen el requadre del Transformer per a line/arrow).
function EndpointHandles({ obj, onEndpointDrag }) {
  const { start, end } = endpointsPx(obj)
  const mk = (which, p) => (
    <Circle key={which} x={p.x} y={p.y} radius={5} fill={KONVA_COL.white} stroke={KONVA_COL.gold} strokeWidth={1.5}
      draggable onMouseDown={e => { e.cancelBubble = true }}
      onDragMove={onEndpointDrag(which)} onDragEnd={onEndpointDrag(which)} />
  )
  return <>{mk('start', start)}{mk('end', end)}</>
}

function PathObj({ obj, common, onDblVector, selected, activeSubIndex, onSubSelect, subpathTool }) {
  const paths = obj.paths || []
  return (
    <Group {...common} onDblClick={onDblVector} onDblTap={onDblVector}>
      {paths.map((path, i) => {
        const props = pathChildProps(obj, path)
        if (!props.data) return null
        // S6: objecte ja seleccionat → aquest clic activa la subpath (no bombolla fins al Group).
        // S1.1: amb l'eina "Selecció de subpath" activa, el clic activa la peça EN UN SOL CLIC
        // (encara que l'objecte no estigui seleccionat) — promoció de l'antic gest de segon clic.
        const subClick = (selected || subpathTool) ? (e) => { e.cancelBubble = true; onSubSelect?.(i) } : undefined
        // Ressalt visual (només pinta): la subpath activa es mostra amb traç daurat, sense tocar les dades.
        const highlight = i === activeSubIndex ? { stroke: KONVA_COL.gold, strokeWidth: Math.max(2, props.strokeWidth || 1) } : null
        // Fix #4: un path sense fill només capta clics sobre el traç; ampliem la zona hit
        // perquè una fletxa curva fina sigui fàcil de seleccionar.
        return <Path key={i} {...props} {...highlight} hitStrokeWidth={props.fill ? 10 : 18} onClick={subClick} onTap={subClick} />
      })}
      {/* COMMIT 5: puntes de fletxa curva orientades a la tangent (mateix builder que l'export).
          Fix #4: SENSE listening={false} → la punta sòlida bombolla el clic al Group (onSelect),
          que és la part que l'usuari prem per seleccionar la fletxa. */}
      {pathHeadAngles(obj).map((h, i) => (
        <Line key={'head' + i} points={headTriPoints(h.x, h.y, h.angle)} closed
          fill={pathHeadColor(obj)} stroke={pathHeadColor(obj)} strokeWidth={1} />
      ))}
    </Group>
  )
}

export function ObjectNode({ obj, src, tableData, modelData, versio, placeholderMode, customerLogoUrl, pageCtx, onHeaderContextMenu, selected, selectable, draggable, onSelect, onDragStart, onDragMove, onDragEnd, onTransformEnd, onDblText, onDblVector, entered, onDblGroup, onChildSelect, onChildDragEnd, selectedChildId, activeSubIndex, onSubSelect, subpathTool, onEndpointDrag, hideTextChildren }) {
  const common = {
    id: obj.id,
    x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1,
    draggable,
    onClick: selectable ? onSelect : undefined,
    onTap: selectable ? onSelect : undefined,
    onDragStart,
    onDragMove,
    onDragEnd,
    onTransformEnd,
  }
  if (obj.type === 'data_block') {
    const dataCommon = { ...common, ...dataBlockGroupProps(obj) }
    if (obj.kind === 'header') {
      // Bloc ancorat (Template FTT): menú contextual (right-click) per Delete-on-page / Detach.
      const hdrProps = onHeaderContextMenu
        ? { ...dataCommon, onContextMenu: (e) => onHeaderContextMenu(e, obj) }
        : dataCommon
      return <HeaderBlock modelData={modelData} versio={versio} placeholderMode={placeholderMode} logoUrl={customerLogoUrl} config={obj.config} pageCtx={pageCtx} groupProps={hdrProps} isSelected={selected} />
    }
    // Desvinculada (BIB S0): mateixos prims que el PDF. Sense això queia al «Carregant
    // taula…» de sota i s'hi quedava per sempre — una taula desvinculada no carrega mai.
    if (isPendentVincle(obj)) {
      return (
        <Group {...dataCommon}>
          {buildPendingBoxPrims(obj).map((p, i) => <PrimNode key={i} p={p} />)}
        </Group>
      )
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
  if (obj.type === 'table') {
    const dataCommon = { ...common, ...dataBlockGroupProps(obj) }
    return <TableNode obj={obj} groupProps={dataCommon} isSelected={selected} />
  }
  if (obj.type === 'field') {
    const dataCommon = { ...common, ...dataBlockGroupProps(obj) }
    return <FieldChipNode obj={obj} groupProps={dataCommon} isSelected={selected} />
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
    const line = <Line {...common} {...lineProps(obj)} hitStrokeWidth={10} />
    if (!selected || !onEndpointDrag) return line
    return <>{line}<EndpointHandles obj={obj} onEndpointDrag={onEndpointDrag} /></>
  }
  if (obj.type === 'arrow') {
    const arrow = <Arrow {...common} {...arrowProps(obj)} hitStrokeWidth={10} />
    if (!selected || !onEndpointDrag) return arrow
    return <>{arrow}<EndpointHandles obj={obj} onEndpointDrag={onEndpointDrag} /></>
  }
  if (obj.type === 'path') {
    return <PathObj obj={obj} common={common} onDblVector={onDblVector} selected={selected} activeSubIndex={activeSubIndex} onSubSelect={onSubSelect} subpathTool={subpathTool} />
  }
  if (obj.type === 'image') {
    return <ImageObj obj={obj} src={src} common={common} />
  }
  if (obj.type === 'pattern_piece') {
    return <PatternPieceObj obj={obj} src={src} common={common} />
  }
  if (obj.type === 'sketch_svg') {
    return <SketchSvgObj obj={obj} common={common} />
  }
  if (obj.type === 'group') {
    const orderedChildren = [...(obj.children || [])].sort(
      (a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
      // Mentre es corba la fletxa d'una cota, l'etiqueta s'aparta: taparia els nodes que
      // s'estan tocant, justament al mig del traç. Torna sola en sortir de l'edició.
      .filter(child => child.visible !== false && !(hideTextChildren && child.type === 'text'))
    return (
      <Group {...common} onDblClick={onDblGroup} onDblTap={onDblGroup}>
        {orderedChildren.map(child => (
          <ObjectNode key={child.id} obj={child} src={child.src}
            tableData={tableData} modelData={modelData} versio={versio}
            placeholderMode={placeholderMode} customerLogoUrl={customerLogoUrl}
            // S1: dins d'un grup ENTRAT, els fills es poden seleccionar i moure (no rotar/redimensionar/editar).
            selected={entered ? child.id === selectedChildId : false}
            selectable={!!entered} draggable={!!entered}
            onSelect={entered ? (e) => onChildSelect(e, child.id) : undefined}
            onDragEnd={entered ? onChildDragEnd(child) : undefined}
            onTransformEnd={undefined}
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
  const mapSegs = (paperPath) => paperPath.segments.map(seg => ({
    x: (seg.point.x - bounds.x) * scaleX,
    y: (seg.point.y - bounds.y) * scaleY,
    inX: seg.handleIn.x * scaleX,
    inY: seg.handleIn.y * scaleY,
    outX: seg.handleOut.x * scaleX,
    outY: seg.handleOut.y * scaleY,
  }))
  // Recorre l'arbre importat sense aplanar els CompoundPath (que porten els forats als fills).
  const collect = (item, out) => {
    const cn = item.className
    if (cn === 'CompoundPath') out.push({ compound: item })
    else if (cn === 'Path') out.push({ path: item })
    else if (item.children) item.children.forEach(c => collect(c, out))
  }
  const collected = []
  collect(imported, collected)
  const paths = collected.map(entry => {
    if (entry.compound) {
      const compound = entry.compound
      const subpaths = compound.children
        .filter(c => c.className === 'Path' && c.segments?.length)
        .map(c => ({ closed: !!c.closed, segments: mapSegs(c) }))
      if (!subpaths.length) return null
      return {
        fill: normalizePaint(compound.fillColor ? paperColorToCss(compound.fillColor, null) : null),
        fillRule: 'evenodd',
        stroke: normalizePaint(compound.strokeColor ? paperColorToCss(compound.strokeColor, null) : null),
        strokeWidth: Math.max(0.2, (compound.strokeWidth || 1) * strokeScale),
        subpaths,
      }
    }
    const path = entry.path
    if (!path.segments?.length) return null
    return {
      closed: !!path.closed,
      stroke: normalizePaint(path.strokeColor ? paperColorToCss(path.strokeColor, null) : null),
      fill: normalizePaint(path.fillColor ? paperColorToCss(path.fillColor, null) : null),
      fillRule: normalizeFillRule(path.fillRule),
      strokeWidth: Math.max(0.2, (path.strokeWidth || 1) * strokeScale),
      segments: mapSegs(path),
    }
  }).filter(Boolean)
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
  const [, setFitxers] = useState([])
  const [filePicker, setFilePicker] = useState(false)   // S03b · P7
  // F1 — el patró VIGENT del model (o null si no en té) i el selector de peces.
  const [patternFile, setPatternFile] = useState(null)
  const [piecePicker, setPiecePicker] = useState(null)  // null | {loading} | {pieces} | {error}
  const [sizeFittings, setSizeFittings] = useState([])
  const [tableData, setTableData] = useState({})    // {objId: jsonData|null} fora del JSON
  const [notice, setNotice] = useState(null)        // toast efímer (p.ex. "ja hi ha capçalera")
  const [thumbnails, setThumbnails] = useState([])
  const [exporting, setExporting] = useState(false)
  const [, setAddingTable] = useState(false)
  const [pickFitting, setPickFitting] = useState(false)
  // S3: picker de variant de taula (T1a/T1b/T2/custom) — null | { variant?: 't1a'|'t1b'|'t2'|'custom' }.
  // Obert des del ribbon (botó "Taula", commit 4).
  const [tablePicker, setTablePicker] = useState(null)
  // B3 — menú contextual del bloc capçalera mestra ancorat: {x, y} en coords de pantalla.
  const [headerMenu, setHeaderMenu] = useState(null)
  // S4: modal "Desar com a plantilla" — null | { nom, descripcio }
  const [saveAsTpl, setSaveAsTpl] = useState(null)
  const [editingText, setEditingText] = useState(null)  // {id, value, x, y, w}
  const [editingFlatId, setEditingFlatId] = useState(null)
  // F1 — l'eina de node activa i l'estat de selecció viuen AQUÍ (barra superior contextual); el
  // sub-editor rep `nodeTool` i puja `onNodeState`. runNode() dispara accions sobre el canvas viu.
  const [nodeTool, setNodeTool] = useState('select')
  const [nodeSel, setNodeSel] = useState({ selCount: 0 })
  const [spaceHeld, setSpaceHeld] = useState(false)           // PEÇA P: barra espaiadora premuda (pan temporal)
  const [panning, setPanning] = useState(false)              // PEÇA P: arrossegant amb pan actiu
  const [zoom, setZoom] = useState(1)
  const [pageFormat, setPageFormat] = useState('A4L')   // TS-4b: format del document sencer
  // PAL-1: paleta amb flyouts (estil Adobe). flyoutOpen = id del flyout desplegat; flyoutSel =
  // última eina triada per flyout (la que queda visible al botó col·lapsat).
  const [flyoutOpen, setFlyoutOpen] = useState(null)
  const [flyoutSel, setFlyoutSel] = useState({})
  const [flyoutRect, setFlyoutRect] = useState(null)   // rect del botó (popover en position:fixed)
  const [ribbonGroup, setRibbonGroup] = useState('file')
  const [dockTab, setDockTab] = useState('properties')   // D2: pestanya activa del dock dret
  // MODE PLANTILLA — no és un estat nou de React inventat per a la sessió: és el `kind` del
  // manifest del .ftt, que el format ja escrivia des del primer dia i que ningú llegia. Amb ell
  // s'engega el mecanisme de render de placeholders (`placeholderMode`), que també estava
  // construït i mort. Sobreviu al desat i al reobrir perquè viu al document, no a la pàgina.
  const [templateMode, setTemplateMode] = useState(false)
  // POMs del model, per al contenidor del panell dret. FRONTERA G1: aquesta llista serveix per
  // DECIDIR què s'escriu; el que arriba al document és només el string. Cap id hi viatja.
  const [pomRows, setPomRows] = useState([])
  // Cota pre-carregada: {text} mentre l'usuari té un POM triat i encara no ha fet els dos clics.
  const [cotaPreset, setCotaPreset] = useState(null)
  const [importMode, setImportMode] = useState(null)     // IMP-1: null | 'image' | 'garment' (panell d'import al dock)
  const [importFile, setImportFile] = useState(null)     // IMP-2: fitxer triat (no s'insereix fins a "Inserir")
  const [importNavOpen, setImportNavOpen] = useState(false)   // C5.3: AssetNavigator com a font "FTT"
  const [importNav, setImportNav] = useState({ tab: 'models', cust: null, any: null, temp: null, modelId: null, gtId: null, gtiId: null })
  const [importDrag, setImportDrag] = useState(false)    // IMP-2: ressaltat de la drop zone
  const [ratioLocked, setRatioLocked] = useState(true)
  const [shiftHeld, setShiftHeld] = useState(false)   // S1: Shift premuda → resize proporcional
  // Grup contenidor quan el que s'edita per nodes és un FILL (cas cota de POM). null = el
  // que s'edita és un objecte de nivell superior, el cas de sempre.
  const [editingFlatGroupId, setEditingFlatGroupId] = useState(null)
  const [activeGroup, setActiveGroup] = useState(null)        // S1: id del grup on s'ha entrat (doble clic)
  const [selectedChildId, setSelectedChildId] = useState(null) // S1: fill seleccionat dins el grup entrat
  const [activeSubpath, setActiveSubpath] = useState(null)   // S6: subpath activa dins un path { objId, index } | null
  const [snapLines, setSnapLines] = useState(null)   // S2: guies de magnetisme actives {x,y} en mm (o null)
  const snapCand = useRef(null)   // S2: candidats de magnetisme calculats a l'inici del drag (no per frame)

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
  // E3: barra de menús en text (Fitxer/Edició/Objecte/Visualització) — mateix patró de tancar-per-clic-fora.
  const [menuOpen, setMenuOpen] = useState(null)   // 'file'|'edit'|'object'|'view'|null
  useEffect(() => {
    if (!menuOpen) return
    const onDown = (e) => {
      if (!(e.target.closest && e.target.closest('[data-menu]'))) setMenuOpen(null)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [menuOpen])
  const flatFileRef = useRef(null)
  const importInputRef = useRef(null)   // IMP-2: file input del panell d'importació
  const paperFlatRef = useRef(null)     // handle imperatiu de PaperFlatEditor: run(name, ...)
  const panDrag = useRef(null)          // PEÇA P: estat de l'arrossegament de pan
  const saveTimer = useRef(null)
  const skipSave = useRef(true)        // salta l'autosave del primer load
  // Mentre el document no és a la pantalla, NO es desa. `skipSave` no n'hi ha prou: només salta
  // la PRIMERA passada de l'efecte, i el lock (que arriba de seguida) el torna a disparar amb
  // `pages` encara al full en blanc del muntatge. Si la càrrega del document tarda més que el
  // debounce de 2 s, aquell full en blanc es desa A SOBRE del document bo. No saber què hi ha
  // encara i desar-hi un full buit són coses diferents.
  const docCarregat = useRef(!fttMode)
  // Mode .ftt: estat del document (assets carregats + metadata + cap de cadena actual).
  const fttAssets = useRef({})         // {nom: dataURL} dels assets, ja baixats (vegeu carregarAssets)
  const fttUrlToName = useRef({})      // {dataURL: nom} per desar (dataURL → 'assets/<nom>')
  const fttMeta = useRef({})           // metadata del document.json (es conserva en desar)
  const fttHeadId = useRef(fitxerId || null)  // cap de cadena vigent (canvia en desar: nova versió)
  const didInitialFit = useRef(false)
  const drawing = useRef(null)         // {type, points, id} mentre es dibuixa
  const [drawTemp, setDrawTemp] = useState(null)
  const [polygonSides, setPolygonSides] = useState(6)   // S7c2: costats de l'eina polígon
  // S7: eina ploma — traç multi-clic (px de contingut). null = inactiva. Independent de `drawing`.
  const penRef = useRef(null)          // {points:[{x,y,inX,inY,outX,outY}], dragging}
  const [penTemp, setPenTemp] = useState(null)   // mirall per pintar: {points, cursor}
  // E2: eines de 2 clics (nota-fletxa / cota) — mateix patró que la ploma però amb 1 sol segment.
  const twoClickRef = useRef(null)     // {tool:'note'|'cota_pom', p1:{x,y}} px de contingut, o null
  const [twoClickTemp, setTwoClickTemp] = useState(null)   // mirall per pintar: {tool, p1, cursor}
  // S1: rubber-band de selecció (marc arrossegat en tela buida amb eina 'select')
  const [marquee, setMarquee] = useState(null)   // {x,y,w,h} px de contingut, per pintar
  const marqueeStart = useRef(null)              // {x,y,shift,rect} mentre s'arrossega
  // S2: regles en mm — geometria de la pàgina relativa al viewport + posició del cursor.
  const [rulerGeo, setRulerGeo] = useState({ left: 0, top: 0 })
  const [cursorMm, setCursorMm] = useState(null)

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
  // A3: patch arbitrari sobre un fill d'un grup (generalitza handleChildDragEnd) — via
  // updatePageObjects perquè la mutació passi per la història (undo/redo).
  const updateChild = useCallback((groupId, childId, patch) => {
    updatePageObjects(currentPage, objs => objs.map(g => (
      g.id !== groupId ? g : { ...g, children: (g.children || []).map(c => (c.id !== childId ? c : { ...c, ...patch })) }
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
  const clearSelection = useCallback(() => { setSelectedIds([]); setActiveSubpath(null) }, [])
  // ── S0: història undo/redo (coalescing de ràfegues) ────────────────────────
  const { undo, redo, reset: resetHistory } = useDocumentHistory({ pages, setPages, setSelectedIds })
  // ── S0: clipboard intern (copy/paste/duplicate) — NO navigator.clipboard ──
  const clipboardRef = useRef([])
  const setZoomClamped = useCallback((next) => {
    setZoom(current => clampZoom(typeof next === 'function' ? next(current) : next))
  }, [])
  const fitZoomToViewport = useCallback(() => {
    const viewport = viewportRef.current
    if (!viewport) return
    const pad = 48
    setZoomClamped(Math.min((viewport.clientWidth - pad) / pageW, (viewport.clientHeight - pad) / pageH))
  }, [pageH, pageW, setZoomClamped])
  useEffect(() => {
    if (didInitialFit.current || !pages.length) return undefined
    const t = setTimeout(() => {
      fitZoomToViewport()
      didInitialFit.current = true
    }, 0)
    return () => clearTimeout(t)
  }, [fitZoomToViewport, pages.length])
  // S2: recalcula la posició de la pàgina (wrapRef) relativa al viewport, per alinear les regles.
  const syncRuler = useCallback(() => {
    const vp = viewportRef.current, wr = wrapRef.current
    if (!vp || !wr) return
    const vpR = vp.getBoundingClientRect(), wrR = wr.getBoundingClientRect()
    setRulerGeo({ left: wrR.left - vpR.left, top: wrR.top - vpR.top })
  }, [])
  useEffect(() => {
    const t = setTimeout(syncRuler, 0)   // post-layout (zoom/format canvien la mida del wrap)
    return () => clearTimeout(t)
  }, [zoom, pageFormat, pages.length, syncRuler])
  useEffect(() => {
    window.addEventListener('resize', syncRuler)
    return () => window.removeEventListener('resize', syncRuler)
  }, [syncRuler])
  // S2: guies — helper de mutació (via setPages → entra a la història S0, com qualsevol altre canvi).
  const setPageGuides = useCallback((updater) => {
    setPages(ps => ps.map((pg, i) => (i === currentPage ? { ...pg, guides: updater(pg.guides || []) } : pg)))
  }, [currentPage])
  const [creatingGuide, setCreatingGuide] = useState(null)   // S2: {axis,pos} mm mentre s'arrossega una guia nova des de la regla
  // S2: arrossegar una guia existent — moure-la, o esborrar-la si es deixa anar fora de la pàgina.
  const onGuideDragEnd = (axis, i, e) => {
    const node = e.target
    const newPos = axis === 'x' ? toMm(node.x()) : toMm(node.y())
    const max = axis === 'x' ? fmt.w : fmt.h
    setPageGuides(gs => (
      newPos < 0 || newPos > max ? gs.filter((_, k) => k !== i) : gs.map((g, k) => (k === i ? { ...g, pos: newPos } : g))
    ))
  }
  // S2: crear una guia arrossegant des d'una regla (mousedown a la banda → segueix el ratolí → soltar la crea).
  const startGuideCreate = (axis, e) => {
    if (!locked) return
    e.preventDefault()
    const posFrom = (ev) => {
      const wr = wrapRef.current
      if (!wr) return 0
      const r = wr.getBoundingClientRect()
      return axis === 'x' ? toMm((ev.clientX - r.left) / zoom) : toMm((ev.clientY - r.top) / zoom)
    }
    setCreatingGuide({ axis, pos: posFrom(e) })
    const onMove = (ev) => setCreatingGuide({ axis, pos: posFrom(ev) })
    const onUp = (ev) => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      const pos = posFrom(ev)
      const max = axis === 'x' ? fmt.w : fmt.h
      setCreatingGuide(null)
      if (pos >= 0 && pos <= max) setPageGuides(gs => [...gs, { axis, pos }])
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }
  const selectOnly = useCallback((objId) => setSelectedIds([objId]), [])
  const toggleSelection = useCallback((objId) => {
    setSelectedIds(ids => (ids.includes(objId) ? ids.filter(id => id !== objId) : [...ids, objId]))
  }, [])
  const handleSelectObject = useCallback((e, objId) => {
    // S6: seleccionar (un altre) objecte reinicia la subpath activa.
    setActiveSubpath(null)
    // S1: seleccionar un altre objecte de nivell superior surt del grup entrat.
    if (activeGroup && objId !== activeGroup) { setActiveGroup(null); setSelectedChildId(null) }
    if (e?.evt?.shiftKey) toggleSelection(objId)
    else selectOnly(objId)
  }, [selectOnly, toggleSelection, activeGroup])
  const handleChildSelect = useCallback((e, childId) => {
    if (e) e.cancelBubble = true
    setSelectedChildId(childId)
  }, [])
  const handleChildDragEnd = useCallback((groupId) => (child) => (e) => {
    const node = e.target
    let patch
    if (child.type === 'line') {
      const dx = toMm(node.x()), dy = toMm(node.y())
      patch = { points: (child.points || []).map((v, i) => (i % 2 === 0 ? v + dx : v + dy)) }
      node.position({ x: 0, y: 0 })
    } else if (child.type === 'arrow') {
      const dx = toMm(node.x()), dy = toMm(node.y())
      patch = { x: (child.x || 0) + dx, y: (child.y || 0) + dy, x2: (child.x2 || 0) + dx, y2: (child.y2 || 0) + dy }
      node.position({ x: 0, y: 0 })
    } else {
      patch = { x: toMm(node.x()), y: toMm(node.y()) }
    }
    updatePageObjects(currentPage, objs => objs.map(g => (
      g.id !== groupId ? g : { ...g, children: (g.children || []).map(c => (c.id !== child.id ? c : { ...c, ...patch })) }
    )))
  }, [currentPage, updatePageObjects])
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
    if (preset === 'preset_cota_pom') {
      // Cota tècnica lliure (sense binding POM, frontera G1 fora d'abast): línia + marques + text editable
      return {
        ...base,
        children: [
          { id: uid(), type: 'line', layer: 'free', x: 0, y: 0, points: [0, 12, 60, 12], stroke: KONVA_COL.textMain, strokeWidth: 1 },
          { id: uid(), type: 'line', layer: 'free', x: 0, y: 0, points: [0, 8, 0, 16], stroke: KONVA_COL.textMain, strokeWidth: 1 },
          { id: uid(), type: 'line', layer: 'free', x: 0, y: 0, points: [60, 8, 60, 16], stroke: KONVA_COL.textMain, strokeWidth: 1 },
          { id: uid(), type: 'text', layer: 'free', x: 20, y: 0, width: 24, height: 10, text: t('tech_sheet.preset_cota_text'), fontSize: 9, fontFamily: FONT, fill: KONVA_COL.textMain, align: 'center' },
        ],
      }
    }
    if (preset === 'preset_annotation') {
      return {
        ...base,
        children: [
          { id: uid(), type: 'text', layer: 'free', x: 0, y: 0, width: 48, height: 14, text: t('tech_sheet.preset_annotation_text'), fontSize: 10, fontFamily: FONT, fill: KONVA_COL.textMain, bgFill: KONVA_COL.white, bgPadding: 3 },
          { id: uid(), type: 'arrow', layer: 'free', x: 50, y: 7, x2: 80, y2: 7, stroke: KONVA_COL.textMain, fill: KONVA_COL.textMain, strokeWidth: 1 },
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
  // `explicitIds` existeix pel panell Capes: allà el z-ordre és PER FILA i la fila clicada pot no
  // ser la que hi ha seleccionada. Cridar-hi selectOnly() abans no serveix —és un setState
  // asíncron i aquest useCallback captura `selectedIds` per closure—, de manera que el botó
  // movia la selecció ANTERIOR, o res si no n'hi havia cap. Ara la fila diu qui és.
  const moveSelectionInFreeLayer = useCallback((direction, explicitIds) => {
    const ids = new Set(explicitIds || selectedIds)
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
  const moveSelectionToFreeLayerEdge = useCallback((edge) => {
    const ids = new Set(selectedIds)
    updatePageObjects(currentPage, objs => {
      const nonFree = objs.filter(o => o.layer !== 'free')
      const freeSelected = objs.filter(o => o.layer === 'free' && ids.has(o.id))
      const freeRest = objs.filter(o => o.layer === 'free' && !ids.has(o.id))
      if (!freeSelected.length) return objs
      return edge === 'front'
        ? [...nonFree, ...freeRest, ...freeSelected]
        : [...nonFree, ...freeSelected, ...freeRest]
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
  // ── B1 · AGRUPAR/DESAGRUPAR VECTORIAL ───────────────────────────────────────────────────
  // Un objecte `path` JA és un compound: `paths[]` és la llista de subpaths (el que la fletxa
  // negra en diu "formes"). Per això un SVG importat entra com un sol objecte monolític i no hi
  // ha manera de treure'n una peça. Aquí es tanca el cercle: un botó, dos motors —el de grups
  // Konva de tota la vida i aquest, que opera sobre subpaths— i el botó tria pel que hi ha
  // seleccionat. Cap superfície nova.
  //
  // Portar una entrada de paths[] a coordenades absolutes: primer es baka la transformació de
  // l'objecte origen (els .ftt vells en poden portar; els nous ja són neutres després d'A5) i
  // després es translada del seu origen al de destí. Tot amb primitius purs de paperOps.
  const entriesToOrigin = useCallback((o, ox, oy) => {
    const baked = bakePathEntries(o.paths, o.scaleX || 1, o.scaleY || 1, o.rotation || 0)
    const dx = (o.x || 0) - ox, dy = (o.y || 0) - oy
    if (!dx && !dy) return baked
    const mou = (segs) => translateSubpath(segs || [], dx, dy).segments
    return baked.map(e => (e.subpaths
      ? { ...e, subpaths: e.subpaths.map(sp => ({ ...sp, segments: mou(sp.segments) })) }
      : { ...e, segments: mou(e.segments) }))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // N objectes `path` → UN compound. L'estil viatja amb cada entrada (paths[] ja el porta), de
  // manera que formes de colors diferents segueixen sent de colors diferents dins el compound.
  const mergePathsToCompound = useCallback(() => {
    const ids = new Set(selectedIds)
    const sel = objectsOf(currentPage).filter(o => ids.has(o.id))
    if (sel.length < 2 || !sel.every(o => o.type === 'path' && Array.isArray(o.paths))) return
    const base = sel[0]
    const ox = base.x || 0, oy = base.y || 0
    const entries = sel.flatMap(o => entriesToOrigin(o, ox, oy).map(e => ({
      // Sense estil propi, l'entrada hereta el de l'objecte del qual venia: si no, en fusionar
      // es perdria el color de tot el que el tenia a nivell d'objecte.
      stroke: o.stroke, fill: o.fill, strokeWidth: o.strokeWidth, ...e,
    })))
    const nou = {
      ...base, id: uid(), x: ox, y: oy, rotation: 0, scaleX: 1, scaleY: 1, paths: entries,
    }
    updatePageObjects(currentPage, objs => {
      const firstIndex = objs.findIndex(o => ids.has(o.id))
      const rest = objs.filter(o => !ids.has(o.id))
      const next = [...rest]
      next.splice(Math.max(0, firstIndex), 0, nou)
      return next
    })
    setSelectedIds([nou.id])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, pages, selectedIds, updatePageObjects, entriesToOrigin])

  // UN compound → N objectes `path` independents, en el mateix lloc i amb el mateix ordre z
  // relatiu (les entrades de paths[] ja hi van de baix a dalt).
  const explodeCompoundPath = useCallback((objId) => {
    const o = objectsOf(currentPage).find(x => x.id === objId && x.type === 'path')
    if (!o || !Array.isArray(o.paths) || o.paths.length < 2) return
    const baked = bakePathEntries(o.paths, o.scaleX || 1, o.scaleY || 1, o.rotation || 0)
    const nous = baked.map(entry => ({
      id: uid(), type: 'path', layer: o.layer || 'free',
      x: o.x || 0, y: o.y || 0, rotation: 0, scaleX: 1, scaleY: 1,
      stroke: entry.stroke ?? o.stroke, fill: entry.fill ?? o.fill,
      strokeWidth: entry.strokeWidth ?? o.strokeWidth,
      headStart: o.headStart, headEnd: o.headEnd,
      paths: [entry],
    }))
    updatePageObjects(currentPage, objs => objs.flatMap(x => (x.id === objId ? nous : [x])))
    setSelectedIds(nous.map(n => n.id))
    setActiveSubpath(null)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, pages, updatePageObjects])

  // ── B2 · MATERIALITZAR LA CAPÇALERA ─────────────────────────────────────────────────────
  // La capçalera no és un grup: és un objecte ATÒMIC (data_block kind:'header') el contingut
  // del qual es genera per codi a cada render i es pinta amb listening={false}. Per això
  // "desvincular" mai va deixar editar-ne res: no hi havia res a seleccionar a dins.
  // Materialitzar-la és convertir aquelles primitives efímeres en objectes reals. El gest és el
  // MATEIX botó Desagrupar —no n'hi ha cap de nou— i el resultat és un grup normal, així que un
  // segon Desagrupar els deixa solts del tot.
  //
  // Els valors amb clau exacta a FIELD_CATALOG neixen com a `type:'field'`: així segueixen
  // resolent-se sols si el document es desa com a plantilla i s'instancia sobre un altre model.
  // Els que NO en tenen (PAGE, GARMENT TYPE|ITEM, TARGET|FIT|CONSTRUCTION, SIZE RUN) neixen com
  // a text estàtic amb el valor d'ara: és una pèrdua real i coneguda, i val més dir-ho aquí que
  // inventar claus que el resolutor del backend no sabria resoldre.
  //
  // SENTIT ÚNIC: no hi ha "tornar a vincular". Per recuperar la capçalera viva s'esborra i es
  // reinsereix des de la plantilla, que és un camí que ja existeix.
  const materialitzaHeader = useCallback((objId) => {
    const hdr = objectsOf(currentPage).find(o => o.id === objId && o.type === 'data_block' && o.kind === 'header')
    if (!hdr) return
    const { prims } = buildHeaderPrimitives(model, sheet?.versio, false, !!customerLogoUrl, hdr.config,
      { index: currentPage, total: pages.length })
    const fills = []
    prims.forEach(pr => {
      if (pr.t === 'r') {
        fills.push({ id: uid(), type: 'rect', layer: 'free', x: toMm(pr.x), y: toMm(pr.y),
          width: toMm(pr.w), height: toMm(pr.h), fill: pr.fill || 'transparent', stroke: pr.stroke, strokeWidth: toMm(pr.sw || 1) })
        return
      }
      if (pr.t === 'l') {
        const [x1, y1, x2, y2] = pr.points || []
        fills.push({ id: uid(), type: 'line', layer: 'free', x: 0, y: 0,
          points: [toMm(x1), toMm(y1), toMm(x2), toMm(y2)], stroke: pr.stroke, strokeWidth: toMm(pr.sw || 1) })
        return
      }
      const base = {
        id: uid(), layer: 'free', x: toMm(pr.x), y: toMm(pr.y), width: toMm(pr.w),
        fontSize: pr.size, fontFamily: FONT, fill: pr.fill,
        fontStyle: pr.bold ? 'bold' : pr.italic ? 'italic' : 'normal',
        textDecoration: pr.underline ? 'underline' : '',
      }
      fills.push(pr.fk
        ? { ...base, type: 'field', key: pr.fk, label: t('tech_sheet.' + (FIELD_CATALOG.find(f => f.key === pr.fk)?.tk || pr.fk)) }
        : { ...base, type: 'text', text: pr.text || '' })
    })
    if (customerLogoUrl) {
      const r = headerMasterLogoRect(0, 0, hdr.config)
      fills.push({ id: uid(), type: 'field', key: 'customer_logo', label: t('tech_sheet.field_customer_logo'),
        x: toMm(r.x), y: toMm(r.y), width: toMm(r.w), height: toMm(r.h), layer: 'free', fontSize: 9 })
    }
    const grup = { id: uid(), type: 'group', layer: 'free', x: hdr.x || 0, y: hdr.y || 0, rotation: 0, children: fills }
    updatePageObjects(currentPage, objs => objs.flatMap(o => (o.id === objId ? [grup] : [o])))
    setSelectedIds([grup.id])
    flash(t('tech_sheet.header_materialized', { n: fills.filter(f => f.type === 'field').length }))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, pages, model, sheet, customerLogoUrl, updatePageObjects, t])

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

  const dimensionInfo = (obj) => {
    if (!obj) return null
    const b = objectBounds(obj)
    const w = Math.max(0, b.maxX - b.minX)
    const h = Math.max(0, b.maxY - b.minY)
    const positionByBounds = obj.type === 'line' || obj.type === 'arrow'
    return {
      width: w,
      height: h,
      x: positionByBounds ? b.minX : (obj.x || 0),
      y: positionByBounds ? b.minY : (obj.y || 0),
      canResize: !['line', 'arrow'].includes(obj.type),
    }
  }
  const moveObjectTo = (obj, key, value) => {
    const next = Number(value)
    if (!Number.isFinite(next)) return
    if (obj.type === 'line' || obj.type === 'arrow') {
      const b = objectBounds(obj)
      const dx = key === 'x' ? next - b.minX : 0
      const dy = key === 'y' ? next - b.minY : 0
      updateObject(obj.id, translateObject(obj, dx, dy))
      return
    }
    updateObject(obj.id, { [key]: next })
  }
  const pathLocalBounds = (obj) => {
    const pts = (obj.paths || []).flatMap(path => entrySegments(path).flatMap(seg => [
      { x: seg.x || 0, y: seg.y || 0 },
      { x: (seg.x || 0) + (seg.inX || 0), y: (seg.y || 0) + (seg.inY || 0) },
      { x: (seg.x || 0) + (seg.outX || 0), y: (seg.y || 0) + (seg.outY || 0) },
    ]))
    if (!pts.length) return null
    return {
      minX: Math.min(...pts.map(p => p.x)),
      minY: Math.min(...pts.map(p => p.y)),
    }
  }
  const resizeObjectTo = (obj, width, height) => {
    const nextW = Number(width)
    const nextH = Number(height)
    if (!Number.isFinite(nextW) || !Number.isFinite(nextH) || nextW <= 0 || nextH <= 0) return
    const current = dimensionInfo(obj)
    if (!current || !current.canResize || current.width <= 0 || current.height <= 0) return
    const sx = nextW / current.width
    const sy = nextH / current.height
    if (obj.type === 'rect' || obj.type === 'image' || obj.type === 'sketch_svg' || obj.type === 'pattern_piece' || obj.type === 'text') {
      updateObject(obj.id, { width: nextW, ...(obj.type !== 'text' ? { height: nextH } : {}) })
      return
    }
    if (obj.type === 'ellipse') {
      updateObject(obj.id, { rx: nextW / 2, ry: nextH / 2 })
      return
    }
    if (obj.type === 'data_block' || obj.type === 'group') {
      updateObject(obj.id, {
        scaleX: (obj.scaleX || 1) * sx,
        scaleY: (obj.scaleY || 1) * sy,
      })
      return
    }
    if (obj.type === 'path') {
      const lb = pathLocalBounds(obj)
      if (!lb) return
      updateObject(obj.id, {
        paths: (obj.paths || []).map(path => ({
          ...path,
          segments: (path.segments || []).map(seg => ({
            ...seg,
            x: lb.minX + ((seg.x || 0) - lb.minX) * sx,
            y: lb.minY + ((seg.y || 0) - lb.minY) * sy,
            inX: (seg.inX || 0) * sx,
            inY: (seg.inY || 0) * sy,
            outX: (seg.outX || 0) * sx,
            outY: (seg.outY || 0) * sy,
          })),
        })),
      })
    }
  }
  const resizeObjectAxis = (obj, axis, rawValue) => {
    const current = dimensionInfo(obj)
    const next = Number(rawValue)
    if (!current || !current.canResize || !Number.isFinite(next) || next <= 0) return
    const ratio = current.width > 0 && current.height > 0 ? current.width / current.height : 1
    const nextW = axis === 'width' ? next : (ratioLocked ? next * ratio : current.width)
    const nextH = axis === 'height' ? next : (ratioLocked ? next / ratio : current.height)
    resizeObjectTo(obj, nextW, nextH)
  }

  // Els assets del .ftt es publiquen com a URL AUTENTICADA (ftt-documents/<id>/asset/<nom>/,
  // IsAuthenticated). Cap dels dos carregadors d'imatge —useImage al canvas viu i loadImageEl
  // a l'export— pot enviar-hi el Bearer: tots dos van amb `new Image()`, i un <img> no porta
  // capçaleres. El 401 acabava a l'`onerror`, que aquí és SILENCI: la imatge desapareixia del
  // canvas i del PDF sense dir-ho. Per això els assets es baixen AMB capçalera i entren al
  // document ja com a dataURL. La inversa (dataURL → 'assets/<nom>') la fa fttUrlToName en
  // desar, de manera que els bytes no es reescriuen mai: el .ftt no engreixa.
  const carregarAssets = async (assets) => {
    const parells = await Promise.all(Object.entries(assets).map(async ([nom, url]) => {
      try {
        const r = await fetch(url, { headers: uploadHeaders })
        if (!r.ok) return null
        return [nom, await blobToDataURL(await r.blob())]
      } catch { return null }
    }))
    return Object.fromEntries(parells.filter(Boolean))
  }

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

    // F1: el patró vigent. Es demana en carregar (no al clic) perquè l'eina ha de poder dir
    // que no n'hi ha ABANS que ningú l'obri: una opció que s'obre buida no explica res.
    fetch(`${API}/api/v1/patterns/pattern-files/?model=${id}`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(d => {
        if (cancelled || !d) return
        const list = d.results || d || []
        setPatternFile(list.find(f => f.is_current) || null)
      }).catch(() => {})

    if (fttMode) {
      // Mode .ftt (F1): carrega el document des de ftt-documents/<fitxerId>/ i el porta a v2.
      // El lock i el desat els afegeix F2; F1 obre en consulta.
      fetch(`${API}/api/v1/ftt-documents/${fitxerId}/`, { headers: authHeaders })
        .then(r => (r.ok ? r.json() : null))
        .then(async data => {
          if (cancelled || !data) return
          const assets = await carregarAssets(data.assets || {})
          if (cancelled) return
          fttAssets.current = assets
          fttUrlToName.current = Object.fromEntries(Object.entries(assets).map(([n, u]) => [u, n]))
          fttMeta.current = data.document_json?.metadata || {}
          fttHeadId.current = data.fitxer?.id || fitxerId
          setTemplateMode(data.manifest?.kind === 'template')
          setSheet(data.fitxer)   // versio ve de ModelFitxer.versio
          hydrate({ template_json: documentToV2(data.document_json, assets) })
          docCarregat.current = true   // a partir d'ara, i no abans, es pot desar
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

  // ── POMs del model per al contenidor del panell dret ──────────────────────
  // Mateix endpoint que ja alimenta les taules snapshot (ara amb `nom_en`, F5-backend): no
  // s'obre cap segon consumidor de dades de POM des de l'editor.
  useEffect(() => {
    if (!id) return undefined
    let cancelled = false
    fetch(`${API}/api/v1/models/${id}/base-measurements/`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (!cancelled && d) setPomRows(d.results || d || []) })
      .catch(() => {})
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // ── Heartbeat del lock: renova locked_at cada 10min independent de l'autosave ──
  // (tanca el forat "obert però inactiu >30min → lock caduca"; TTL backend = 30min).
  useEffect(() => {
    if (!locked) return undefined
    const iv = setInterval(() => {
      // Re-adquirir com a propietari actualitza locked_at sense afectar el document.
      fetch(`${API}/api/v1/ftt-documents/${fttHeadId.current}/lock/`, { method: 'POST', headers: authHeaders }).catch(() => {})
    }, 10 * 60 * 1000)   // 10 min < TTL 30 min
    return () => clearInterval(iv)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked])

  // ── Allibera el lock (best-effort) en tancar/recarregar la pestanya bruscament ──
  // (complementa, no substitueix, l'alliberament al cleanup de desmuntatge de dalt).
  useEffect(() => {
    if (!locked) return undefined
    const onUnload = () => {
      try {
        const url = `${API}/api/v1/ftt-documents/${fttHeadId.current}/unlock/`
        // keepalive perquè la petició sobrevisqui al tancament de la pestanya.
        fetch(url, { method: 'POST', headers: authHeaders, keepalive: true }).catch(() => {})
      } catch { /* best effort */ }
    }
    window.addEventListener('beforeunload', onUnload)
    return () => window.removeEventListener('beforeunload', onUnload)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked])

  // Carrega el template_json v2 a l'estat. tj buit/absent → 1 pàgina buida.
  function hydrate(sheetData) {
    const tj = sheetData?.template_json
    skipSave.current = true
    let rawPages = null
    if (tj && tj.version === 2 && Array.isArray(tj.pages) && tj.pages.length) {
      rawPages = tj.pages.map(p => ({ id: p.id || uid(), objects: (p.objects || []).map(o => ({ ...o, id: o.id || uid() })), guides: p.guides || [] }))
    } else {
      rawPages = [{ id: uid(), objects: [] }]
    }
    setPages(rawPages)
    resetHistory(rawPages)
    convertLegacySketchSvgs(rawPages).then(converted => {
      if (converted !== rawPages) { setPages(converted); resetHistory(converted) }
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
    if (!docCarregat.current) return   // el document encara no hi és: desar ara seria desar un full en blanc
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
          // `kind` viatja a cada desat: és el que fa que el mode plantilla sobrevisqui al
          // tancar l'editor (abans, cada desat el tornava a "document" en silenci).
          method: 'PATCH', headers, body: JSON.stringify({ document_json: documentJson, kind: templateMode ? 'template' : 'document' }),
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
        const thumbs = []
        for (let pi = 0; pi < pages.length; pi++) {
          const ctx = { tableData, modelData: model, versio: sheet?.versio, pageW, pageH, customerLogoUrl, pageIndex: pi, pageTotal: pages.length }
          thumbs.push(await renderPageToDataURL(pages[pi], 0.18, ctx))
        }
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
      .filter(o => selectedSet.has(o.id) && o.layer !== 'template' && !blocksTransform(o) && !o.locked && o.visible !== false)
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
      if (!locked) return
      // S1.2 — Delete SENSIBLE AL CONTEXT: si hi ha una subpath activa, esborra NOMÉS la subpath
      // (l'entrada paths[index]); si en queda 0, cau a l'esborrat de l'objecte sencer.
      if (activeSubpath) {
        const o = objectsOf(currentPage).find(x => x.id === activeSubpath.objId)
        if (o?.type === 'path' && Array.isArray(o.paths)) {
          e.preventDefault()
          if (o.paths.length <= 1) { deleteObject(o.id) }
          else { updateObject(o.id, { paths: o.paths.filter((_, i) => i !== activeSubpath.index) }) }
          setActiveSubpath(null)
          return
        }
      }
      if (!selectedIds.length) return
      const deletable = objectsOf(currentPage).filter(o => selectedIds.includes(o.id) && o.layer === 'free' && !o.locked).map(o => o.id)
      if (deletable.length) { e.preventDefault(); deleteObjects(deletable) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIds, currentPage, pages, locked, editingText, editingFlatId, activeSubpath])

  // ── S0 — Teclat: Cmd/Ctrl+Z desfés · Shift+Z/Ctrl+Y refés · C/V/D clipboard ─
  useEffect(() => {
    const onKey = (e) => {
      // Ja no surt d'hora amb editingFlatId: ⌘Z és un de sol per a tot el document.
      if (editingText) return
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (!locked) return
      if (!(e.metaKey || e.ctrlKey)) return
      const key = e.key.toLowerCase()
      if (key === 'z') {
        e.preventDefault()
        if (e.shiftKey) redo(); else undo()
        return
      }
      if (key === 'y') {
        e.preventDefault()
        redo()
        return
      }
      if (key === 'c') {
        if (!objectsOf(currentPage).some(o => selectedIds.includes(o.id) && o.layer === 'free')) return
        e.preventDefault()
        copySelection()
        return
      }
      if (key === 'v') {
        if (!clipboardRef.current.length) return
        e.preventDefault()
        pasteClipboard()
        return
      }
      if (key === 'd') {
        if (!objectsOf(currentPage).some(o => selectedIds.includes(o.id) && o.layer === 'free')) return
        e.preventDefault()
        duplicateSelection()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked, editingText, editingFlatId, undo, redo, selectedIds, currentPage, pages, updatePageObjects])

  // ── S1 — Teclat: Escape surt del grup entrat ────────────────────────────────
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'Escape') return
      if (editingText || editingFlatId) return
      setActiveSubpath(null)   // S6: Escape també surt de l'edició de subpath
      if (!activeGroup) return
      setActiveGroup(null); setSelectedChildId(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeGroup, editingText, editingFlatId])

  // ── A1 — SORTIDA DEL MODE D'EDICIÓ DE NODES ────────────────────────────────
  // Amb l'edició contínua (F6a) ja no hi ha res a cancel·lar: tot està escrit al document a
  // mesura que es fa. Sortir vol dir només "deixa d'editar aquest objecte". Hi ha tres portes,
  // i totes tres acaben aquí: Escape, el clic al buit dins el canvas de Paper (que el fill ens
  // demana per `onExitEdit`) i el clic fora de l'abast del canvas.
  const exitFlatEdit = useCallback(() => setEditingFlatId(null), [])
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'Escape') return
      if (!editingFlatId) return
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      setEditingFlatId(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingFlatId])

  // ── S1 — Teclat: dreceres d'eina V/T/R/E/L (sense Cmd/Ctrl/Alt) ────────────
  useEffect(() => {
    const onKey = (e) => {
      if (editingFlatId) return
      if (editingText) return
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (!locked) return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const map = { v: 'select', t: 'text', r: 'rect', e: 'ellipse', l: 'line', p: 'pen' }
      const next = map[e.key.toLowerCase()]
      if (!next) return
      e.preventDefault()
      setTool(next)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked, editingText, editingFlatId])

  // ── S7 — Teclat de la ploma: Enter tanca obert, Escape cancel·la TOT el traç
  // (el simple guanya — no treu punt a punt), Backspace treu l'últim ancoratge ──
  useEffect(() => {
    const onKey = (e) => {
      if ((tool !== 'pen' && tool !== 'arrow_curve') || !penRef.current) return
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (e.key === 'Enter') {
        e.preventDefault()
        if (penRef.current.points.length >= 2) finishPen(false)
      } else if (e.key === 'Escape') {
        e.preventDefault()
        penRef.current = null
        setPenTemp(null)
        setTool('select')   // Bloc 2 (ii): cancel·lar també surt de l'eina, no la deixa activa.
      } else if (e.key === 'Backspace') {
        e.preventDefault()
        penRef.current.points.pop()
        if (!penRef.current.points.length) { penRef.current = null; setPenTemp(null) }
        else setPenTemp({ points: [...penRef.current.points], cursor: stagePoint() })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tool])

  // Bloc 2 (iii): en commutar d'eina, mata qualsevol traç/preview fantasma en curs
  // (ploma/fletxa curva i nota/cota de 2 clics) perquè no persisteixi ni resusciti.
  useEffect(() => {
    penRef.current = null
    setPenTemp(null)
    twoClickRef.current = null
    setTwoClickTemp(null)
    // El POM pre-carregat viu MENTRE l'eina cota és activa: canviar d'eina és desdir-se'n.
    if (tool !== 'cota_pom') setCotaPreset(null)
  }, [tool])

  // ── E2 — Teclat de nota-fletxa/cota: Escape cancel·la el 1r clic pendent ──
  useEffect(() => {
    const onKey = (e) => {
      if (!twoClickRef.current) return
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (e.key === 'Escape') {
        e.preventDefault()
        twoClickRef.current = null
        setTwoClickTemp(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tool])

  // ── PEÇA P: barra espaiadora = pan temporal (independent de l'eina activa) ──
  useEffect(() => {
    if (!locked) return undefined
    const typing = () => { const tag = document.activeElement?.tagName; return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' }
    const onDown = (e) => { if (e.code === 'Space' && !editingText && !typing()) { e.preventDefault(); setSpaceHeld(true) } }
    const onUp = (e) => { if (e.code === 'Space') { setSpaceHeld(false); setPanning(false) } }
    window.addEventListener('keydown', onDown)
    window.addEventListener('keyup', onUp)
    return () => { window.removeEventListener('keydown', onDown); window.removeEventListener('keyup', onUp) }
  }, [locked, editingText])

  // ── S1: Shift premuda → Transformer proporcional (resize) ───────────────────
  useEffect(() => {
    const onDown = (e) => { if (e.key === 'Shift') setShiftHeld(true) }
    const onUp = (e) => { if (e.key === 'Shift') setShiftHeld(false) }
    const onBlur = () => setShiftHeld(false)
    window.addEventListener('keydown', onDown)
    window.addEventListener('keyup', onUp)
    window.addEventListener('blur', onBlur)
    return () => {
      window.removeEventListener('keydown', onDown)
      window.removeEventListener('keyup', onUp)
      window.removeEventListener('blur', onBlur)
    }
  }, [])

  // ── S1: nudge amb fletxes — translada un objecte (dx,dy en mm) segons el seu tipus ──
  const translate = (o, dx, dy) => {
    if (o.type === 'line') return { ...o, points: (o.points || []).map((v, i) => (i % 2 === 0 ? v + dx : v + dy)) }
    if (o.type === 'arrow') return { ...o, x: (o.x || 0) + dx, y: (o.y || 0) + dy, x2: (o.x2 || 0) + dx, y2: (o.y2 || 0) + dy }
    return { ...o, x: (o.x || 0) + dx, y: (o.y || 0) + dy }
  }
  // ── S1 — Teclat: fletxes mouen la selecció (±1mm, ±10mm amb Shift) ──────────
  useEffect(() => {
    const onKey = (e) => {
      if (editingFlatId) return
      if (editingText) return
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (!locked) return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const s = e.shiftKey ? 10 : 1
      let dx = 0, dy = 0
      if (e.key === 'ArrowLeft') dx = -s
      else if (e.key === 'ArrowRight') dx = s
      else if (e.key === 'ArrowUp') dy = -s
      else if (e.key === 'ArrowDown') dy = s
      else return
      e.preventDefault()
      const ids = new Set(objectsOf(currentPage).filter(o => o.layer === 'free' && selectedIds.includes(o.id) && !o.locked).map(o => o.id))
      if (!ids.size) return
      updatePageObjects(currentPage, objs => objs.map(o => (ids.has(o.id) ? translate(o, dx, dy) : o)))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked, editingText, editingFlatId, selectedIds, currentPage, updatePageObjects])

  // ── Handlers de node (drag / transform) ────────────────────────────────────
  // S2: bbox (mm) d'un objecte a partir del seu node Konva en viu (rect real, no obj.x/y).
  const nodeRectMm = (id) => {
    const n = stageRef.current?.findOne('#' + id)
    if (!n) return null
    const r = n.getClientRect({ relativeTo: n.getLayer() })
    return { x: toMm(r.x), y: toMm(r.y), w: toMm(r.width), h: toMm(r.height) }
  }
  // S2: candidats de magnetisme calculats UN COP a l'inici del drag (no per frame).
  const handleDragStart = (obj) => () => {
    const rects = objectsOf(currentPage)
      .filter(o => o.id !== obj.id && o.layer === 'free' && o.visible !== false)
      .map(o => nodeRectMm(o.id)).filter(Boolean)
    const p = pages[currentPage] || {}
    snapCand.current = buildCandidates({ rectsMm: rects, pageWmm: fmt.w, pageHmm: fmt.h, guides: p.guides || [] })
  }
  // S2: a cada frame de drag, magnetitza el node contra els candidats (Cmd/Ctrl ho desactiva).
  const handleDragMove = (obj) => (e) => {
    if (!snapCand.current) return
    if (e.evt?.ctrlKey || e.evt?.metaKey) { setSnapLines(null); return }
    const node = e.target
    const r = node.getClientRect({ relativeTo: node.getLayer() })
    const rectMm = { x: toMm(r.x), y: toMm(r.y), w: toMm(r.width), h: toMm(r.height) }
    const thr = SNAP_PX / (MM_TO_PX * zoom)
    const { dx, dy, lineX, lineY } = computeSnap(rectMm, snapCand.current, thr)
    if (dx) node.x(node.x() + dx * MM_TO_PX)
    if (dy) node.y(node.y() + dy * MM_TO_PX)
    setSnapLines((lineX != null || lineY != null) ? { x: lineX, y: lineY } : null)
  }
  const handleDragEnd = (obj) => (e) => {
    setSnapLines(null); snapCand.current = null
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
  // Bloc 1: arrossegar una nansa mou NOMÉS aquell extrem. Shift encaixa a 45° respecte
  // l'altre extrem (reutilitza snap45, com ploma/cota). No toca la resta de l'objecte.
  const handleEndpointDrag = (obj) => (which) => (e) => {
    const node = e.target
    let px = { x: node.x(), y: node.y() }
    if (e.evt?.shiftKey) {
      const ep = endpointsPx(obj)
      const other = which === 'start' ? ep.end : ep.start
      px = snap45(other.x, other.y, px.x, px.y)
    }
    const mx = toMm(px.x), my = toMm(px.y)
    if (obj.type === 'arrow') {
      updateObject(obj.id, which === 'start' ? { x: mx, y: my } : { x2: mx, y2: my })
    } else {
      const pts = [...(obj.points || [])]
      if (which === 'start') { pts[0] = mx; pts[1] = my }
      else { pts[pts.length - 2] = mx; pts[pts.length - 1] = my }
      updateObject(obj.id, { points: pts })
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
      // Un grup només es pot bakejar si TOTS els fills són paths: si n'hi ha cap altre tipus
      // (text, imatge, taula), neutralitzar el grup li trauria la transformació i el trencaria.
      // En aquest cas es conserva el comportament de sempre. Decisió acotada a posta.
      const kids = obj.children || []
      const totPaths = kids.length > 0 && kids.every(c => c.type === 'path' && Array.isArray(c.paths))
      if (totPaths) {
        updateObject(obj.id, {
          x: toMm(node.x()), y: toMm(node.y()), rotation: 0, scaleX: 1, scaleY: 1,
          children: kids.map(c => ({
            ...c, rotation: 0, scaleX: 1, scaleY: 1,
            // El fill també porta el seu propi offset local: escalar i girar el conjunt vol dir
            // moure'n l'origen igual que la geometria.
            ...(() => {
              const r0 = scaleSubpath([{ x: c.x || 0, y: c.y || 0, inX: 0, inY: 0, outX: 0, outY: 0 }], sx, sy, 0, 0)
              const r1 = rotation ? rotateSubpath(r0.segments, rotation, 0, 0) : r0
              return { x: r1.segments[0].x, y: r1.segments[0].y }
            })(),
            paths: bakePathEntries(c.paths, sx, sy, rotation),
          })),
        })
        return
      }
      updateObject(obj.id, { x: toMm(node.x()), y: toMm(node.y()), rotation, scaleX: sx, scaleY: sy })
      return
    }
    if (obj.type === 'path') {
      updateObject(obj.id, {
        x: toMm(node.x()), y: toMm(node.y()), rotation: 0, scaleX: 1, scaleY: 1,
        paths: bakePathEntries(obj.paths, sx, sy, rotation),
      })
      return
    }
    // Blocs de dades: el resize baka l'escala a obj.scale (coherent amb l'auto-fit),
    // no a width/height. node.scaleX() ja és l'escala absoluta nova (Konva multiplica
    // sobre l'escala base del Group), per tant s'hi assigna directament.
    if (obj.type === 'data_block' || obj.type === 'table') {
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

  // ── S1: Shift durant el dibuix de línia/fletxa → encaixa l'angle a múltiples de 45° ──
  const snap45 = (sx, sy, x, y) => {
    const dx = x - sx, dy = y - sy
    const a = Math.atan2(dy, dx)
    const step = Math.PI / 4
    const sa = Math.round(a / step) * step
    const len = Math.hypot(dx, dy)
    return { x: sx + Math.cos(sa) * len, y: sy + Math.sin(sa) * len }
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
  // ── S7: tanca el traç de ploma → un sol objecte type:'path' amb segments editables (mm) ──
  const finishPen = (closed) => {
    const points = penRef.current?.points || []
    if (points.length >= 2) {
      const segments = points.map(p => ({ x: toMm(p.x), y: toMm(p.y), inX: toMm(p.inX), inY: toMm(p.inY), outX: toMm(p.outX), outY: toMm(p.outY) }))
      // COMMIT 5: la fletxa curva reutilitza la màquina de ploma, però surt oberta, amb
      // gruix de fletxa i headEnd:true (la punta la dibuixa el render sobre la tangent final).
      const isArrow = tool === 'arrow_curve'
      addObject({
        id: uid(), type: 'path', layer: 'free', x: 0, y: 0,
        // Fix #2: stroke a nivell d'OBJECTE (no de subpath) → el selector "Color de traç" de
        // nivell superior recolora línia I punta alhora; el per-subpath segueix com a override.
        stroke: KONVA_COL.textMain,
        ...(isArrow ? { headEnd: true } : {}),
        paths: [{ closed: isArrow ? false : closed, fill: 'transparent', strokeWidth: isArrow ? 1.5 : 1.2, fillRule: 'nonzero', segments }],
      })
    }
    penRef.current = null
    setPenTemp(null)
    setTool('select')
  }
  // Bloc 2 (i): doble-clic al llenç = final descobrible d'un traç obert (ploma/fletxa curva),
  // equivalent a Enter. Només actua si hi ha un traç en curs amb ≥2 punts.
  const finishPenOnDblClick = () => {
    // Aquest era l'únic handler del Stage SENSE guard: amb el sub-editor obert, un doble-clic
    // per entrar a selecció directa també tancava el traç de la ploma que hi hagués en curs.
    if (!konvaOwnsPointer) return
    if (penRef.current && penRef.current.points.length >= 2) finishPen(false)
  }
  // ── E2: 2n clic de nota-fletxa/cota → construeix el GRUP (children relatius a l'origen del grup) ──
  const finishTwoClick = (kind, p1, p2) => {
    if (kind === 'note') {
      // p1 = PUNTA (el punt assenyalat), p2 = ORIGEN (cua, on viu el text) → grup ancorat a l'origen.
      const ox = toMm(p2.x), oy = toMm(p2.y)
      const dx = toMm(p1.x) - ox, dy = toMm(p1.y) - oy
      const TW = 42
      // El text mai trepitja la fletxa: si la punta és a la DRETA (dx>0) el text va a l'ESQUERRA de l'origen, i viceversa.
      const textX = dx > 0 ? -TW : 0
      const arrow = { id: uid(), type: 'arrow', layer: 'free', x: 0, y: 0, x2: dx, y2: dy, stroke: KONVA_COL.textMain, fill: KONVA_COL.textMain, strokeWidth: 1 }
      const text = { id: uid(), type: 'text', layer: 'free', x: textX, y: -7, width: TW, height: 14, text: t('tech_sheet.preset_annotation_text'), fontSize: 10, fontFamily: FONT, fill: KONVA_COL.textMain, bgFill: KONVA_COL.white, bgPadding: 3 }
      addObject({ id: uid(), type: 'group', layer: 'free', x: ox, y: oy, rotation: 0, children: [arrow, text] })
      return
    }
    // 'cota_pom': p1 = A, p2 = B → grup ancorat a A. A4: la línia és una fletxa de doble
    // punta (arrow2) que marca els extrems A→B; substitueix els ticks perpendiculars.
    const ax = toMm(p1.x), ay = toMm(p1.y)
    const dx = toMm(p2.x) - ax, dy = toMm(p2.y) - ay
    const len = Math.hypot(dx, dy) || 1
    const px = -dy / len, py = dx / len   // perpendicular unitari (per desplaçar el text)
    // Cota PRE-CARREGADA des del contenidor de POMs: la fletxa i l'etiqueta van en vermell
    // saturat i el text és el `nom_fitxa` del POM — la nomenclatura amb què el patronista
    // anomena aquesta mesura al croquis. FRONTERA G1: entra com a STRING LITERAL, sense cap
    // pom_id ni bm_id a l'objecte. La cota no és un binding viu; és un dibuix.
    const pom = cotaPreset
    const col = pom ? KONVA_COL.pom : KONVA_COL.textMain
    // La fletxa de la cota de POM és un `path` de dos nodes amb punta als dos extrems, no un
    // `arrow`: es veu igual, però un path SÍ es pot corbar (l'editor de nodes només sap
    // treballar amb paths). Corbar la cota per esquivar el croquis és el gest que demanava.
    // La cota lliure segueix sent `arrow`, per no canviar res dels documents ja fets.
    const linia = pom
      ? { id: uid(), type: 'path', layer: 'free', x: 0, y: 0, headStart: true, headEnd: true, stroke: col, fill: null, strokeWidth: 1,
          paths: [{ closed: false, segments: [{ x: 0, y: 0, inX: 0, inY: 0, outX: 0, outY: 0 }, { x: dx, y: dy, inX: 0, inY: 0, outX: 0, outY: 0 }], stroke: col, strokeWidth: 1, fill: null }] }
      : { id: uid(), type: 'arrow', layer: 'free', x: 0, y: 0, x2: dx, y2: dy, stroke: col, fill: col, strokeWidth: 1, arrow2: true }
    // A4 — l'amplada surt de MESURAR el text, no d'un literal: una cota de POM pot dir "A" o
    // "1/2 CHEST WIDTH" i el fons vermell s'hi ha d'ajustar. Es mesura un cop, aquí, i es desa.
    const etiqueta = pom ? pom.text : t('tech_sheet.preset_cota_text')
    const TW = measureTextWidthMm({ text: etiqueta, fontSize: 9, fontFamily: FONT, fontStyle: pom ? 'bold' : 'normal' })
    const mx = dx / 2 + px * 3, my = dy / 2 + py * 3   // punt mig desplaçat 3mm perpendicular
    const text = pom
      ? { id: uid(), type: 'text', layer: 'free', x: mx - TW / 2, y: my - 5, width: TW, height: 10, text: etiqueta, fontSize: 9, fontFamily: FONT, fill: KONVA_COL.white, fontStyle: 'bold', align: 'center', bgFill: KONVA_COL.pom, bgPadding: toMm(TEXT_PAD_Y_PX) }
      : { id: uid(), type: 'text', layer: 'free', x: mx - TW / 2, y: my - 5, width: TW, height: 10, text: etiqueta, fontSize: 9, fontFamily: FONT, fill: KONVA_COL.textMain, align: 'center' }
    addObject({ id: uid(), type: 'group', layer: 'free', x: ax, y: ay, rotation: 0, children: [linia, text] })
    setCotaPreset(null)
  }
  const onStageMouseDown = (e) => {
    if (!konvaOwnsPointer) return
    if (tool === 'pan' || spaceHeld) return   // PEÇA P: el pan el gestiona el viewport, no el Stage
    if (!locked) { if (e.target === e.target.getStage()) clearSelection(); return }
    const pos = stagePoint()
    if (!pos) return
    if (tool === 'note' || tool === 'cota_pom') {
      // E2: 1r clic fixa p1 i mostra el preview elàstic; 2n clic tanca el grup i torna a 'select'.
      if (!twoClickRef.current) {
        twoClickRef.current = { tool, p1: pos }
        setTwoClickTemp({ tool, p1: pos, cursor: pos })
        return
      }
      const p1 = twoClickRef.current.p1
      // A2: Shift encaixa la cota (2n punt) a múltiples de 45°, coherent amb el preview.
      const p2 = (twoClickRef.current.tool === 'cota_pom' && e?.evt?.shiftKey)
        ? snap45(p1.x, p1.y, pos.x, pos.y) : pos
      finishTwoClick(twoClickRef.current.tool, p1, p2)
      twoClickRef.current = null
      setTwoClickTemp(null)
      setTool('select')
      return
    }
    if (tool === 'pen' || tool === 'arrow_curve') {
      // Clic a prop del 1r punt (amb ≥2 punts) tanca el traç; si no, afegeix un nou ancoratge.
      const pts = penRef.current?.points
      if (pts && pts.length >= 2 && Math.hypot(pos.x - pts[0].x, pos.y - pts[0].y) <= 8) { finishPen(true); return }
      if (!penRef.current) penRef.current = { points: [], dragging: false }
      penRef.current.points.push({ x: pos.x, y: pos.y, inX: 0, inY: 0, outX: 0, outY: 0 })
      penRef.current.dragging = true
      setPenTemp({ points: [...penRef.current.points], cursor: pos })
      return
    }
    if (tool === 'select') {
      // S1: en tela buida no deseleccionem al mousedown — comencem un marc de rubber-band
      // i la deselecció (si no hi ha arrossegament) es resol al mouseup.
      if (e.target === e.target.getStage()) {
        // S1: clic en tela buida surt del grup entrat.
        if (activeGroup) { setActiveGroup(null); setSelectedChildId(null) }
        marqueeStart.current = { x: pos.x, y: pos.y, shift: !!e.evt?.shiftKey, rect: { x: pos.x, y: pos.y, w: 0, h: 0 } }
        setMarquee({ x: pos.x, y: pos.y, w: 0, h: 0 })
      }
      return
    }
    if (tool === 'text' || tool === 'text_box') {
      const obj = {
        id: uid(), type: 'text', layer: 'free', x: toMm(pos.x), y: toMm(pos.y),
        width: 120, height: 30, text: 'Doble clic per editar', fontSize: 11,
        fontFamily: FONT, fill: KONVA_COL.textMain,
        // PAL-2: el text_box neix TRANSPARENT (com el rect), no blanc opac. Segueix sent un
        // text_box (bgFill present → caixa amb Rect darrere) i el color és editable a la barra.
        ...(tool === 'text_box' ? { bgFill: 'transparent', bgPadding: 4 } : {}),
      }
      addObject(obj); setTool('select'); return
    }
    if (PRESET_TOOLS.includes(tool)) {
      addObject(createPreset(tool, toMm(pos.x), toMm(pos.y)))
      setTool('select')
      return
    }
    if (RECT_TOOLS.includes(tool) || LINE_TOOLS.includes(tool) || tool === 'draw' || tool === 'polygon') {
      drawing.current = { type: tool, startX: pos.x, startY: pos.y, points: [pos.x, pos.y] }
      setDrawTemp({ type: tool, x: pos.x, y: pos.y, w: 0, h: 0, points: [pos.x, pos.y] })
    }
  }
  const onStageMouseMove = (e) => {
    if (!konvaOwnsPointer) return
    // S2: marcador de cursor a les regles (mm) — no interfereix amb marquee/dibuix, que
    // recalculen `pos` pel seu compte més avall.
    const cur = stagePoint()
    if (cur) setCursorMm({ x: toMm(cur.x), y: toMm(cur.y) })
    if (twoClickRef.current) {
      // E2: preview elàstic del 2n punt — p1 ja fixat, només movem el cursor.
      // A2: Shift encaixa la cota a múltiples de 45° (reutilitza snap45, com ploma/línia).
      if (cur) {
        const p1 = twoClickRef.current.p1
        const c = (twoClickRef.current.tool === 'cota_pom' && e?.evt?.shiftKey)
          ? snap45(p1.x, p1.y, cur.x, cur.y) : cur
        setTwoClickTemp({ ...twoClickRef.current, cursor: c })
      }
      return
    }
    if ((tool === 'pen' || tool === 'arrow_curve') && penRef.current) {
      if (!cur) return
      const points = penRef.current.points
      if (penRef.current.dragging && points.length) {
        const last = points[points.length - 1]
        const p = e?.evt?.shiftKey ? snap45(last.x, last.y, cur.x, cur.y) : cur
        last.outX = p.x - last.x; last.outY = p.y - last.y
        last.inX = -last.outX; last.inY = -last.outY
      }
      setPenTemp({ points: [...points], cursor: cur })
      return
    }
    if (marqueeStart.current) {
      const start = marqueeStart.current
      const pos = stagePoint()
      if (!pos) return
      const rect = { x: Math.min(start.x, pos.x), y: Math.min(start.y, pos.y), w: Math.abs(pos.x - start.x), h: Math.abs(pos.y - start.y) }
      start.rect = rect
      setMarquee(rect)
      return
    }
    if (!drawing.current) return
    const pos = stagePoint()
    if (!pos) return
    const d = drawing.current
    if (RECT_TOOLS.includes(d.type) || d.type === 'polygon') {
      setDrawTemp({ type: d.type, x: Math.min(d.startX, pos.x), y: Math.min(d.startY, pos.y), w: Math.abs(pos.x - d.startX), h: Math.abs(pos.y - d.startY) })
    } else if (LINE_TOOLS.includes(d.type)) {
      const p = e?.evt?.shiftKey ? snap45(d.startX, d.startY, pos.x, pos.y) : pos
      setDrawTemp({ type: d.type, points: [d.startX, d.startY, p.x, p.y] })
    } else if (d.type === 'draw') {
      d.points = [...d.points, pos.x, pos.y]
      setDrawTemp({ type: 'draw', points: d.points })
    }
  }
  const onStageMouseUp = (e) => {
    if (!konvaOwnsPointer) return
    if ((tool === 'pen' || tool === 'arrow_curve') && penRef.current) {
      penRef.current.dragging = false
      const pos = stagePoint()
      setPenTemp({ points: [...penRef.current.points], cursor: pos })
      return
    }
    if (marqueeStart.current) {
      const m = marqueeStart.current
      marqueeStart.current = null
      setMarquee(null)
      const rect = m.rect || { x: m.x, y: m.y, w: 0, h: 0 }
      // Marc menyspreable → es tracta com un clic simple (deselecció, tret que sigui shift).
      if (rect.w <= 3 && rect.h <= 3) {
        if (!m.shift) clearSelection()
        return
      }
      const stage = stageRef.current
      const hits = []
      if (stage) {
        objectsOf(currentPage).filter(o => o.layer === 'free' && !o.locked && o.visible !== false).forEach(o => {
          const node = stage.findOne('#' + o.id)
          if (!node) return
          const r = node.getClientRect({ relativeTo: node.getLayer() })
          const overlap = !(r.x > rect.x + rect.w || r.x + r.width < rect.x || r.y > rect.y + rect.h || r.y + r.height < rect.y)
          if (overlap) hits.push(o.id)
        })
      }
      setSelectedIds(m.shift ? Array.from(new Set([...selectedIds, ...hits])) : hits)
      return
    }
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
    } else if (d.type === 'polygon') {
      // S7c2: N costats inscrits al bbox → path tancat (sense tipus nou d'objecte).
      const x = Math.min(d.startX, pos.x), y = Math.min(d.startY, pos.y)
      const w = Math.abs(pos.x - d.startX), h = Math.abs(pos.y - d.startY)
      if (w > 3 && h > 3) {
        const pts = polygonPoints(x, y, w, h, polygonSides)
        const segments = []
        for (let k = 0; k < pts.length; k += 2) segments.push({ x: toMm(pts[k]), y: toMm(pts[k + 1]), inX: 0, inY: 0, outX: 0, outY: 0 })
        obj = { ...base, type: 'path', x: 0, y: 0, paths: [{ closed: true, fill: 'transparent', stroke: KONVA_COL.textMain, strokeWidth: 1.2, fillRule: 'nonzero', segments }] }
      }
    } else if (d.type === 'line' || d.type === 'line_dot') {
      const p = e?.evt?.shiftKey ? snap45(d.startX, d.startY, pos.x, pos.y) : pos
      obj = { ...base, type: 'line', x: 0, y: 0, points: [toMm(d.startX), toMm(d.startY), toMm(p.x), toMm(p.y)], stroke: KONVA_COL.textMain, strokeWidth: 1, ...(d.type === 'line_dot' ? { dash: [4, 4] } : {}) }
    } else if (d.type === 'arrow' || d.type === 'arrow2') {
      const p = e?.evt?.shiftKey ? snap45(d.startX, d.startY, pos.x, pos.y) : pos
      const dist = Math.hypot(p.x - d.startX, p.y - d.startY)
      if (dist > 5) obj = { ...base, type: 'arrow', x: toMm(d.startX), y: toMm(d.startY), x2: toMm(p.x), y2: toMm(p.y), stroke: KONVA_COL.textMain, fill: KONVA_COL.textMain, strokeWidth: 1.5, ...(d.type === 'arrow2' ? { arrow2: true } : {}) }
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
  // ── PEÇA P: pan arrossegant el viewport (eina 'pan' o barra espaiadora) ──
  const onViewportMouseDown = (e) => {
    // A1 · clic FORA de l'abast del canvas de Paper (marge gris o zona de pàgina no coberta).
    // Allà no hi ha res a deseleccionar, així que no cal el patró de dos temps: se surt i prou.
    // Va abans del guard de pan perquè aquest handler, fins ara, ignorava tot el que no fos pan
    // i el gris de treball era una zona morta on clicar no feia absolutament res.
    if (editingFlatId && !(tool === 'pan' || spaceHeld) && !e.target?.closest?.('canvas')) {
      exitFlatEdit()
      return
    }
    if (!(tool === 'pan' || spaceHeld) || !locked) return
    const vp = viewportRef.current
    if (!vp) return
    e.preventDefault()
    panDrag.current = { x: e.clientX, y: e.clientY, sl: vp.scrollLeft, st: vp.scrollTop }
    setPanning(true)
  }
  const onViewportMouseMove = (e) => {
    const d = panDrag.current
    const vp = viewportRef.current
    if (!d || !vp) return
    vp.scrollLeft = d.sl - (e.clientX - d.x)
    vp.scrollTop = d.st - (e.clientY - d.y)
  }
  const endPan = () => { if (panDrag.current) { panDrag.current = null; setPanning(false) } }

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
    if (!locked) return
    // Cas normal: un path/sketch de nivell superior.
    if (['sketch_svg', 'path'].includes(selObj?.type)) {
      setEditingText(null); setTool('select')
      setEditingFlatGroupId(null); setEditingFlatId(selObj.id)
      return
    }
    // Cas cota: el path viu DINS d'un grup. S'hi entra igual, recordant el grup contenidor
    // perquè el commit sàpiga a qui torna la geometria.
    if (selObj?.type === 'group' && groupPathChild) {
      setEditingText(null); setTool('select')
      setEditingFlatGroupId(selObj.id); setEditingFlatId(groupPathChild.id)
    }
  }
  const startVectorEdit = (obj) => {
    if (!locked || !['sketch_svg', 'path'].includes(obj?.type)) return
    setEditingText(null)
    setTool('select')
    selectOnly(obj.id)
    setEditingFlatGroupId(null)
    setEditingFlatId(obj.id)
  }
  // F1 — dispara una acció sobre el canvas viu del sub-editor (close/open/split/removeSelection…).
  const runNode = (name, ...args) => paperFlatRef.current?.run?.(name, ...args)
  // ARBITRATGE DE PUNTER (Camí 1). Fins ara la separació entre Konva i Paper era una exclusió
  // total: tres handlers del Stage que sortien d'hora amb `editingFlatId` i un objecte que
  // desapareixia de l'escena. Ara hi ha un MODE explícit i el punter se li assigna:
  //   'objecte' → mana Konva (el canvas de Paper deixa passar el punter)
  //   'forma'   → Paper, selecció de subpaths sencers (fletxa negra)
  //   'node'    → Paper, selecció directa de nodes/segments/nanses (fletxa blanca)
  // L'objecte editat ja NO surt de l'escena de Konva: es queda visible i al seu lloc, i Paper
  // hi pinta les nanses per damunt. És el que fa que l'edició se senti in-place.
  const pointerMode = !editingFlatId ? 'objecte' : (nodeTool === 'shape' ? 'forma' : 'node')
  const konvaOwnsPointer = pointerMode === 'objecte'
  // F4 — mode edició de nodes actiu: cap acció d'abast OBJECTE (ribbon/menú/panell dret) hi és clicable.
  const nodeMode = !!editingFlatId
  // G1 — en entrar/sortir del mode edició, el mode per defecte és FORMA (fletxa negra): el primer gest
  // natural és agafar una forma, no un node. Reinicia també l'estat de selecció.
  useEffect(() => {
    setNodeTool('shape'); setNodeSel({ mode: 'shape', shapeCount: 0, selCount: 0 })
    // En entrar a editar nodes, el ribbon es planta a "Editar": abans la barra contextual
    // apareixia sola, ara les eines viuen a la tab i cal portar-hi l'usuari.
    if (editingFlatId) setRibbonGroup('editar')
    // Sortir de l'edició (Escape, Cancel·lar, esborrar l'objecte…) també deixa anar el grup
    // contenidor: així no cal recordar-ho a cadascuna de les sortides.
    if (!editingFlatId) setEditingFlatGroupId(null)
  }, [editingFlatId])
  // F1/F3 — teclat del mode edició de nodes, centralitzat al PARE (finestra, independent del focus).
  // El context GUANYA: el Delete d'objecte del nivell superior ja surt d'hora amb editingFlatId, i
  // aquí Delete/Backspace operen SEMPRE sobre la selecció fina (node/segment), mai sobre l'objecte.
  useEffect(() => {
    if (!editingFlatId) return
    const onKey = (e) => {
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      // F3 — ESBORRAR: tant Delete (fn+delete a Mac) com Backspace (la tecla gran de Mac).
      if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); runNode('removeSelection'); return }
      // ⌘Z NO s'intercepta: amb l'edició contínua l'undo és el del document i ha de funcionar
      // igual dins i fora del mode nodes. Només Cmd+A segueix sent contextual (tots els nodes).
      if (e.metaKey || e.ctrlKey) {
        const k = e.key.toLowerCase()
        if (k === 'a') { e.preventDefault(); runNode('selectAll'); return }
        return
      }
      if (e.altKey) return
      // F6 — nudge: fletxes = 1px, Shift+fletxes = 10px sobre la selecció de nodes/segment.
      if (e.key.startsWith('Arrow')) {
        const s = e.shiftKey ? 10 : 1
        const d = { ArrowLeft: [-s, 0], ArrowRight: [s, 0], ArrowUp: [0, -s], ArrowDown: [0, s] }[e.key]
        if (d) { e.preventDefault(); runNode('nudge', d[0], d[1]); return }
      }
      // G1 — V = fletxa negra (selecció de FORMA) · A = fletxa blanca (selecció DIRECTA de nodes).
      const map = { v: 'shape', a: 'select', '+': 'add', '=': 'add', '-': 'remove', _: 'remove', b: 'convert', c: 'scissors' }
      const next = map[e.key] ?? map[e.key?.toLowerCase()]
      if (next) { e.preventDefault(); setNodeTool(next) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [editingFlatId])
  // ── S7 — Teclat: A obre l'editor de nodes (PaperFlatEditor) del path sol seleccionat ──
  useEffect(() => {
    const onKey = (e) => {
      if (editingFlatId || editingText) return
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (!locked) return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key.toLowerCase() !== 'a') return
      const sel = objectsOf(currentPage).filter(o => selectedIds.includes(o.id))
      if (sel.length === 1 && (sel[0].type === 'path' || sel[0].type === 'sketch_svg')) {
        e.preventDefault()
        startVectorEdit(sel[0])
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked, editingText, editingFlatId, selectedIds, currentPage])
  // S2b — el sub-editor separa/talla la path viva: la peça B arriba en espai LOCAL i es crea com a
  // OBJECTE nou de primer nivell, heretant la transformació de l'objecte en edició (perquè quedi al lloc).
  const handleSplitObject = (piece) => {
    if (!editingFlatId || !piece?.segments?.length) return
    const base = objectsOf(currentPage).find(o => o.id === editingFlatId)
    if (!base) return
    const newObj = {
      id: uid(), type: 'path', layer: 'free',
      x: base.x || 0, y: base.y || 0, rotation: base.rotation, scaleX: base.scaleX, scaleY: base.scaleY,
      stroke: base.stroke, fill: base.fill, strokeWidth: base.strokeWidth,
      paths: [{ closed: !!piece.closed, fill: 'transparent', fillRule: 'nonzero', strokeWidth: base.strokeWidth || 1.2, segments: piece.segments }],
    }
    addObject(newObj)
  }
  const commitFlatEdit = (payload) => {
    if (!editingFlatId) return
    if (payload && typeof payload === 'object' && Array.isArray(payload.paths)) {
      // Escriu i NO tanca: l'edició és contínua. Cada escriptura entra a la història del
      // document com qualsevol altra acció (mateix debounce, mateix límit).
      if (editingFlatGroupId) updateChild(editingFlatGroupId, editingFlatId, { paths: payload.paths })
      else updateObject(editingFlatId, { paths: payload.paths })
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
  }
  const addModelFitxer = async (f) => {
    if (!locked) return
    // D13: aquest fetch SÍ pot portar Authorization → va per l'endpoint AUTENTICAT, no pel
    // signat. Abans apuntava directament a /media/ (servit per nginx, sense cap gate).
    // url_extern viu en un altre origen: s'hi va sense capçalera (no li enviem el token).
    const extern = !!f.url_extern
    const url = extern ? f.url_extern : (f.id ? `${API}/api/v1/model-fitxers/${f.id}/download/` : null)
    if (!url) return
    try {
      const blob = await fetch(url, extern ? undefined : { headers: uploadHeaders })
        .then(r => { if (!r.ok) throw new Error('fetch'); return r.blob() })
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
  // LEGACY: substituït pel picker de taules snapshot S3; el RENDER de graded_table
  // es conserva per a docs existents; candidat a poda futura.
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
  // LEGACY: substituïts pel picker de taules snapshot S3; el RENDER de graded_table
  // es conserva per a docs existents; candidats a poda futura.
  // ── S3: taules snapshot (T1a/T1b) — valors CONGELATS a la inserció (llei de disseny:
  // cap binding viu; obj.snapshot només serveix per traçabilitat). Auto-fit igual que
  // insertGradedTable: es construeix un cop amb buildTableCellPrimitives per obtenir
  // totalW/totalH i calcular l'escala que hi cap al format actual.
  const fitTableObj = (obj) => {
    const { totalW, totalH } = buildTableCellPrimitives(obj)
    const wMm = totalW / MM_TO_PX, hMm = totalH / MM_TO_PX
    const scale = Math.min(1, (fmt.w - 20) / wMm, (fmt.h - 20) / hMm)
    return { ...obj, scale, width: wMm * scale, height: hMm * scale }
  }

  // T1a — fitxa de treball fitting (POM base + regla de grading). Tol± queda buit: la
  // serialització de base-measurements no exposa tolerància (només impressió+anotació manual).
  const insertTableT1a = async (sfId) => {
    if (!locked) return
    let bms, rules
    try {
      const [rBm, rRules] = await Promise.all([
        fetch(`${API}/api/v1/models/${model.id}/base-measurements/`, { headers: authHeaders }),
        fetch(`${API}/api/v1/grading-rules/?rule_set=${model.grading_rule_set}`, { headers: authHeaders }),
      ])
      if (!rBm.ok || !rRules.ok) { flash(t('tech_sheet.flash_table_fetch_error')); return }
      const dBm = await rBm.json()
      const dRules = await rRules.json()
      bms = dBm.results || dBm || []
      rules = dRules.results || dRules || []
    } catch { flash(t('tech_sheet.flash_table_fetch_error')); return }
    if (!bms.length) { flash(t('tech_sheet.flash_empty_table')); return }

    const rulesByPom = {}
    rules.forEach(r => { rulesByPom[r.pom] = r })
    const columns = [
      { key: 'ref', label: t('tech_sheet.tbl_col_nomenclatura'), width: 22 },
      { key: 'pom', label: t('tech_sheet.tbl_col_pom'), width: 46 },
      { key: 'base', label: t('tech_sheet.tbl_col_base_cm'), width: 18 },
      { key: 'rule', label: t('tech_sheet.tbl_col_rule'), width: 18 },
      { key: 'break', label: t('tech_sheet.tbl_col_break'), width: 18 },
      { key: 'tol', label: t('tech_sheet.tbl_col_tol'), width: 14 },
      { key: 'nova', label: t('tech_sheet.tbl_col_new_measure'), width: 34 },
      { key: 'coment', label: t('tech_sheet.tbl_col_comments'), width: 60 },
    ]
    const rows = bms.map(bm => {
      const rule = rulesByPom[bm.pom_id]
      return [
        bm.nom_fitxa || bm.pom_abbreviation || '',
        { text: rule?.pom_nom_en || bm.nom_client || bm.pom_code_global || '', sub: bm.nom_ca || '' },
        bm.base_value_cm != null ? String(bm.base_value_cm) : '',
        rule?.increment_base != null ? String(rule.increment_base) : '',
        rule?.talla_break_label || '',
        '', '', '',
      ]
    })
    const obj = fitTableObj({
      id: uid(), type: 'table', layer: 'free', x: 10, y: 14,
      kind: 'pom_fitting', columns, rows,
      style: { fontSize: 9, headerFill: TBL.HDR_BG, zebra: true },
      snapshot: { model_id: model.id, size_fitting_id: sfId, snapshot_at: new Date().toISOString() },
    })
    addObject(obj)
    setTablePicker(null)
  }

  // T1b — grading final: talles + Δ, amb els breaks (canvi d'increment) en negreta.
  const insertTableT1b = async (sfId) => {
    if (!locked) return
    let data
    try {
      const r = await fetch(`${API}/api/v1/fitting/${sfId}/graded-table/`, { headers: authHeaders })
      if (!r.ok) { flash(t('tech_sheet.flash_table_fetch_error')); return }
      data = await r.json()
    } catch { flash(t('tech_sheet.flash_table_fetch_error')); return }
    if (!data.rows || !data.rows.length) { flash(t('tech_sheet.flash_empty_table')); return }

    const sizeLabels = data.size_labels || []
    const columns = [
      { key: 'ref', label: t('tech_sheet.tbl_col_nomenclatura'), width: 22 },
      { key: 'nom', label: t('tech_sheet.tbl_col_pom'), width: 46 },
      // T1 — la columna de la talla base porta marca al MODEL (`base`), no només el sufix `*`:
      // el builder la necessita per pintar-hi la franja de realçat. El `*` es manté perquè
      // sobreviu a l'imprès en blanc i negre.
      ...sizeLabels.map(sl => (sl === data.base_size
        ? { key: sl, label: `${sl}*`, width: 16, base: true }
        : { key: sl, label: sl, width: 16 })),
      { key: 'delta', label: 'Δ', width: 16 },
    ]
    // Break = talla on el delta CANVIA respecte a la talla anterior (ordre de size_labels).
    const cellForSize = (row, sl, prevSl) => {
      const v = row.valors?.[sl]
      const text = v != null ? String(v) : '–'
      const d = row.deltas?.[sl]
      const dPrev = prevSl != null ? row.deltas?.[prevSl] : undefined
      const isBreak = prevSl != null && d != null && dPrev != null && d !== dPrev
      return isBreak ? { text, bold: true } : text
    }
    const rows = data.rows.map(row => [
      row.ref || row.abbreviation || row.codi || '',
      { text: row.nom_en || '', sub: row.nom_ca || '' },
      ...sizeLabels.map((sl, si) => cellForSize(row, sl, si > 0 ? sizeLabels[si - 1] : null)),
      rowDelta(row, data.base_size, sizeLabels),
    ])
    const obj = fitTableObj({
      id: uid(), type: 'table', layer: 'free', x: 10, y: 14,
      kind: 'pom_grading', columns, rows,
      style: { fontSize: 9, headerFill: TBL.HDR_BG, zebra: true },
      snapshot: { model_id: model.id, size_fitting_id: sfId, snapshot_at: new Date().toISOString() },
    })
    addObject(obj)
    setTablePicker(null)
  }

  // T2 — BOM: neix buida (sense snapshot de fitting), 100% editable a mà.
  const insertTableT2 = () => {
    if (!locked) return
    const columns = [
      { key: 'material', label: t('tech_sheet.tbl_col_material'), width: 50 },
      { key: 'ref', label: t('tech_sheet.tbl_col_ref'), width: 32 },
      { key: 'supplier', label: t('tech_sheet.tbl_col_supplier'), width: 44 },
      { key: 'consumption', label: t('tech_sheet.tbl_col_consumption'), width: 28 },
      { key: 'notes', label: t('tech_sheet.tbl_col_notes'), width: 56 },
    ]
    const rows = Array.from({ length: 4 }, () => columns.map(() => ''))
    const obj = fitTableObj({
      id: uid(), type: 'table', layer: 'free', x: 10, y: 14,
      kind: 'bom', columns, rows,
      style: { fontSize: 9, headerFill: TBL.HDR_BG, zebra: true },
      snapshot: { model_id: model.id, snapshot_at: new Date().toISOString() },
    })
    addObject(obj)
    setTablePicker(null)
  }

  // Personalitzada — graella genèrica buida, mida a tria (files×columnes).
  const insertTableCustom = (nRows, nCols) => {
    if (!locked) return
    const columns = Array.from({ length: nCols }, (_, i) => ({
      key: 'c' + i, label: t('tech_sheet.tbl_col_default', { n: i + 1 }), width: Math.max(20, Math.floor(240 / nCols)),
    }))
    const rows = Array.from({ length: nRows }, () => columns.map(() => ''))
    const obj = fitTableObj({
      id: uid(), type: 'table', layer: 'free', x: 10, y: 14,
      kind: 'custom', columns, rows,
      style: { fontSize: 9, headerFill: TBL.HDR_BG, zebra: true },
      snapshot: { model_id: model.id, snapshot_at: new Date().toISOString() },
    })
    addObject(obj)
    setTablePicker(null)
  }

  // Punt d'entrada del picker (encara sense botó al ribbon — commit 4): tria de variant →
  // si cal, sub-selector de size fitting → insereix.
  const runTableVariant = (variant, sfId) => {
    if (variant === 't1a') insertTableT1a(sfId)
    else if (variant === 't1b') insertTableT1b(sfId)
  }
  const onPickTableVariant = (variant) => {
    if (variant === 't2') { insertTableT2(); return }
    if (variant === 'custom') { setTablePicker({ variant: 'custom', rows: 3, cols: 3 }); return }
    if (!sizeFittings.length) return   // ribbon el desactiva (commit 4); sense fitting no hi ha què inserir
    if (sizeFittings.length === 1) { runTableVariant(variant, sizeFittings[0].id); return }
    setTablePicker({ variant })
  }

  // ── Bloc de dades: capçalera del model (màxim 1 per pàgina) ─────────────────
  // S12-UNIF/POS: "Capçalera del model" insereix la Template FTT (masterFtt) com a bloc ANCORAT
  // (locked + layer template → no draggable/seleccionable) + menú contextual delete-on-page/detach,
  // MATEIX tractament i MATEIXA posició que la instanciada des de template. La geometria ve de la
  // font única MASTER_HEADER_GEOM (posició de l'SVG canònic, x=10.09 y=13.76mm). Cap camí nou crea
  // header legacy.
  const insertHeader = () => {
    if (!locked) return
    if (objectsOf(currentPage).some(o => o.type === 'data_block' && o.kind === 'header')) {
      flash(t('tech_sheet.flash_header_exists')); return
    }
    addObject({
      id: uid(), type: 'data_block', kind: 'header', layer: 'template', locked: true,
      ...MASTER_HEADER_GEOM, config: { layout: 'masterFtt' },
    })
  }

  // ── Pàgines ────────────────────────────────────────────────────────────────
  // Instància fresca de la capçalera mestra (Template FTT) per a una pàgina nova: el mateix
  // bloc ANCORAT (locked, layer template, config masterFtt) amb un id nou. Font: la primera
  // capçalera mestra que trobi al document. Si no n'hi ha cap (document en blanc o esborrada
  // a totes les pàgines), la pàgina nova neix buida.
  const masterHeaderInstance = () => {
    for (const pg of pages) {
      const h = (pg.objects || []).find(o => o.type === 'data_block' && o.kind === 'header' && o.config?.layout === 'masterFtt' && !o.detached)
      if (h) return { ...h, id: uid() }
    }
    return null
  }
  const addPage = () => {
    if (!locked) return
    const hdr = masterHeaderInstance()
    setPages(ps => [...ps, { id: uid(), objects: hdr ? [hdr] : [] }])
    setCurrentPage(pages.length)
  }
  // B3 — "Delete on this page": treu la instància de la capçalera mestra NOMÉS d'aquesta
  // pàgina (les altres intactes; les pàgines noves la tornen a portar via masterHeaderInstance).
  const deleteHeaderOnPage = (pageIdx) => {
    if (!locked) return
    updatePageObjects(pageIdx, objs => objs.filter(o => !(o.type === 'data_block' && o.kind === 'header')))
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
      const [pdfW, pdfH] = fmt.pdf
      for (let pi = 0; pi < pages.length; pi++) {
        const ctx = { tableData, modelData: model, versio: sheet?.versio, pageW, pageH, customerLogoUrl, pageIndex: pi, pageTotal: pages.length }
        const dataUrl = await renderPageToDataURL(pages[pi], 3.5, ctx)
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

  // S4: desa el document .ftt vigent (cap de cadena) com a plantilla del tenant.
  const submitSaveAsTpl = async () => {
    if (!saveAsTpl?.nom.trim()) return
    try {
      const r = await fetch(`${API}/api/v1/ftt-documents/${fttHeadId.current}/save-as-template/`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ nom: saveAsTpl.nom.trim(), descripcio: saveAsTpl.descripcio || '' }),
      })
      if (r.ok) {
        // El backend descongela abans d'empaquetar; el seu report diu QUÈ ha desmaterialitzat.
        // Es diu, no es calla: si les taules han quedat buides, l'usuari ho ha de saber ara.
        const rep = (await r.json())?.unfreeze_report
        const parts = []
        if (rep?.camps_descongelats) parts.push(t('tech_sheet.tpl_unfroze_fields', { n: rep.camps_descongelats }))
        if (rep?.taules_desvinculades) parts.push(t('tech_sheet.tpl_unfroze_tables', { n: rep.taules_desvinculades }))
        if (rep?.peces_despenjades) parts.push(t('tech_sheet.tpl_unfroze_pieces', { n: rep.peces_despenjades }))
        flash(parts.length
          ? `${t('tech_sheet.saved_as_template_ok')} · ${parts.join(' · ')}`
          : t('tech_sheet.saved_as_template_ok'))
        setSaveAsTpl(null)
      }
      else flash(t('tech_sheet.save_as_template_error'))
    } catch { flash(t('tech_sheet.save_as_template_error')) }
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
    borderRadius: 6, border: `1px solid ${COL.border}`, background: COL.field,
    cursor: 'pointer', color: COL.textMain, fontFamily: FONT,
  }
  // Botó de la paleta d'eines vertical (C2): icona quadrada; eina activa ressaltada amb accent gold.
  const paletteBtn = {
    display: 'flex', alignItems: 'center', justifyContent: 'center', width: 30, height: 30,
    borderRadius: 6, border: `1px solid transparent`, background: 'transparent',
    cursor: 'pointer', color: COL.textMain, fontFamily: FONT,
  }
  // Doble intensitat d'actiu (P-C): la paleta fixa una EINA, no selecciona un element →
  // gold PLE + text blanc (mateix tractament que el botó de mode del Taller). El goldPale
  // queda reservat per a "element seleccionat" (fila de POM, forma activa).
  const paletteBtnOn = { borderColor: COL.gold, background: COL.gold, color: 'var(--white)' }
  // Barra contextual (C4): mateixa pell que la resta de la closca (tokens globals, T1), discreta,
  // separada de la topbar i del viewport per un filet molt fi (1px COL.border) — com el peu d'estat.
  const CTX_BG = COL.sidebar, CTX_BORDER = COL.border, CTX_TEXT = COL.textMain
  const curObjs = objectsOf(currentPage)

  // Quins POMs ja tenen cota al document. Sense cap referència desada (G1), l'única prova
  // possible és la que veu l'ull: hi ha un text amb aquell `nom_fitxa`. És exacte per al cas
  // real (els nom_fitxa són curts i únics dins un model) i no obliga a inventar cap binding.
  // Es mira TOT el document, no la pàgina activa: una cota a la pàgina 2 també és col·locada.
  // C3 · PALETA DEL DOCUMENT — els colors que ja es fan servir en aquesta fitxa, en ordre
  // d'aparició i sense repetits. Es recorren els objectes de totes les pàgines i, dins d'un
  // path, també cada entrada de paths[] i cada subpath: en un croquis importat el color viu
  // allà, no a l'objecte. No es persisteix res: és una lectura del document, no una
  // preferència, i es recalcula sola quan el document canvia.
  const docPalette = useMemo(() => {
    const vist = []
    const afegeix = (c) => {
      if (!c || c === 'transparent' || c === 'none') return
      const k = String(c).toLowerCase()
      if (!vist.includes(k)) vist.push(k)
    }
    for (const pg of pages) {
      for (const o of flattenObjects(pg.objects || [])) {
        afegeix(o.fill); afegeix(o.stroke); afegeix(o.bgFill)
        for (const e of (o.paths || [])) {
          afegeix(e.fill); afegeix(e.stroke)
          for (const sp of (e.subpaths || [])) { afegeix(sp.fill); afegeix(sp.stroke) }
        }
      }
    }
    return vist
  }, [pages])

  const cotesColocades = useMemo(() => {
    const noms = new Set()
    for (const p of pages) {
      for (const o of flattenObjects(p.objects || [])) {
        if (o.type === 'text' && o.text) noms.add(String(o.text).trim())
      }
    }
    return noms
  }, [pages])
  const curGuides = pages[currentPage]?.guides || []   // S2: guies de la pàgina activa
  const ordered = [...curObjs].sort((a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
  const selectedSet = new Set(selectedIds)
  const selectedObjects = curObjs.filter(o => selectedSet.has(o.id))
  const selObj = selectedObjects.length === 1 ? selectedObjects[0] : null
  // A3: text editable pel panell — el propi objecte 'text', o bé el fill 'text' d'un grup
  // (cas cota). Prioritza el fill actiu si s'ha entrat al grup; si no, l'únic fill text.
  const groupTextChild = (() => {
    if (!selObj || selObj.type !== 'group') return null
    const kids = selObj.children || []
    if (activeGroup === selObj.id && selectedChildId) {
      const c = kids.find(k => k.id === selectedChildId)
      return c?.type === 'text' ? c : null
    }
    const texts = kids.filter(k => k.type === 'text')
    return texts.length === 1 ? texts[0] : null
  })()
  const textObj = selObj?.type === 'text' ? selObj : groupTextChild
  const textGroupId = selObj?.type === 'group' ? selObj.id : null
  // A4 — si el que canvia és el CONTINGUT (o la tipografia) d'un text amb fons, l'amplada es
  // torna a mesurar: si no, editar l'etiqueta d'una cota deixaria el fons de la mida antiga.
  // Els texts SENSE fons no s'hi toquen: allà l'amplada és la caixa de composició que ha triat
  // l'usuari (i on el text ha d'ajustar-se o partir), no un ajust al contingut.
  const updateText = (patch) => {
    if (!textObj) return
    const p = { ...patch }
    const tocaMida = 'text' in p || 'fontSize' in p || 'fontFamily' in p || 'fontStyle' in p
    if (tocaMida && (textObj.bgFill || p.bgFill)) {
      p.width = measureTextWidthMm({
        text: p.text ?? textObj.text,
        fontSize: p.fontSize ?? textObj.fontSize,
        fontFamily: p.fontFamily ?? textObj.fontFamily,
        fontStyle: p.fontStyle ?? textObj.fontStyle,
      })
    }
    return textGroupId ? updateChild(textGroupId, textObj.id, p) : updateObject(textObj.id, p)
  }
  // Fix #3: forma amb traç editable — el propi objecte (rect/ellipse/line/arrow/path) o bé el
  // fill 'arrow'/'path' d'un grup (cas cota: conviu amb textObj, tots dos blocs alhora).
  const STROKE_TYPES = ['rect', 'ellipse', 'line', 'arrow', 'path']
  const groupShapeChild = (() => {
    if (!selObj || selObj.type !== 'group') return null
    const kids = selObj.children || []
    if (activeGroup === selObj.id && selectedChildId) {
      const c = kids.find(k => k.id === selectedChildId)
      return (c && (c.type === 'arrow' || c.type === 'path')) ? c : null
    }
    const shapes = kids.filter(k => k.type === 'arrow' || k.type === 'path')
    return shapes.length === 1 ? shapes[0] : null
  })()
  // El fill PATH d'un grup: l'únic que l'editor de nodes sap corbar (una `arrow` no té nodes).
  const groupPathChild = (() => {
    if (!selObj || selObj.type !== 'group') return null
    const kids = (selObj.children || []).filter(k => k.type === 'path')
    if (activeGroup === selObj.id && selectedChildId) return kids.find(k => k.id === selectedChildId) || null
    return kids.length === 1 ? kids[0] : null
  })()
  const shapeObj = STROKE_TYPES.includes(selObj?.type) ? selObj : groupShapeChild
  const shapeGroupId = (selObj?.type === 'group' && groupShapeChild) ? selObj.id : null
  const updateShape = (patch) => (shapeObj && (shapeGroupId ? updateChild(shapeGroupId, shapeObj.id, patch) : updateObject(shapeObj.id, patch)))
  const subActive = shapeObj?.type === 'path' && activeSubpath?.objId === shapeObj.id ? activeSubpath.index : null   // S6
  // ROTAR UN FILL DINS D'UN GRUP (deute SPRINT_EDITOR_ESTAT §260). Fins ara els fills d'un
  // grup entrat es podien seleccionar i moure, però no girar: la rotació sempre anava a
  // l'objecte de nivell superior. El cas que ho demana és la cota de POM — separar l'etiqueta
  // de la fletxa i posar-la a l'angle de la mesura. El render ja ho sabia fer (`common` aplica
  // obj.rotation a qualsevol node, fills inclosos): només faltava encaminar-hi el panell.
  const rotChildId = (selObj?.type === 'group' && activeGroup === selObj.id && selectedChildId) ? selectedChildId : null
  const rotObj = (rotChildId && (selObj.children || []).find(c => c.id === rotChildId)) || selObj
  const updateRotation = (deg) => (rotChildId
    ? updateChild(selObj.id, rotChildId, { rotation: deg })
    : updateObject(selObj.id, { rotation: deg }))
  // B3 — GATE DEL PANELL DRET. Mentre s'estan manipulant nodes o formes d'un objecte, el panell
  // no pot escriure sobre AQUEST MATEIX objecte: serien dues mans a la mateixa geometria (el
  // model per una banda, el canvas viu per l'altra) i la que arribés segona guanyaria per atzar.
  // Abans quedava amagat perquè l'edició era una transacció i el panell escrivia sobre una còpia
  // que ningú tornava a llegir; sense transacció, el forat és visible. Els blocs afectats es
  // deshabiliten amb un <fieldset disabled> i s'expliquen, en lloc d'ignorar el clic en silenci.
  const panelLockedForEdit = !!editingFlatId && !!selObj
    && (selObj.id === editingFlatId || selObj.id === editingFlatGroupId)
  const multiSelected = selectedObjects.length > 1
  const multiStroke = selectedObjects.filter(o => ['rect', 'ellipse', 'line', 'arrow', 'path'].includes(o.type))
  const multiFill = selectedObjects.filter(o => ['text', 'rect', 'ellipse', 'path'].includes(o.type))
  const multiPosition = selectedObjects.filter(o => o.type !== 'line' && o.type !== 'arrow')
  // B1 · UN BOTÓ, DOS MOTORS. Agrupar i Desagrupar no canvien de lloc ni es dupliquen: miren
  // què hi ha seleccionat i trien el motor. Tots els seleccionats són paths → compound
  // vectorial; barreja de tipus → grup Konva de sempre. A l'inrevés igual.
  const canGroupCompound = selectedObjects.length >= 2 && selectedObjects.every(o => o.type === 'path' && Array.isArray(o.paths))
  const canGroup = selectedObjects.length >= 2
  const doGroup = () => (canGroupCompound ? mergePathsToCompound() : groupSelection())
  const ungroupKind = selObj?.type === 'group' ? 'group'
    : (selObj?.type === 'path' && (selObj.paths?.length || 0) > 1) ? 'compound'
    : (selObj?.type === 'data_block' && selObj.kind === 'header') ? 'header'
    : null
  const doUngroup = () => {
    if (ungroupKind === 'group') ungroupObject(selObj.id)
    else if (ungroupKind === 'compound') explodeCompoundPath(selObj.id)
    else if (ungroupKind === 'header') materialitzaHeader(selObj.id)
  }
  const ungroupTitle = ungroupKind === 'compound' ? t('tech_sheet.ungroup_compound_title')
    : ungroupKind === 'header' ? t('tech_sheet.ungroup_header_title')
    : t('tech_sheet.ungroup')
  const mirrorableIds = selectedObjects.filter(o => !blocksTransform(o)).map(o => o.id)
  const freeSelectedIds = selectedObjects.filter(o => o.layer === 'free').map(o => o.id)

  // S2: regles en mm — ticks alineats amb la posició real de la pàgina (rulerGeo) i el zoom.
  const sx = (mm) => rulerGeo.left + mm * MM_TO_PX * zoom
  const sy = (mm) => rulerGeo.top + mm * MM_TO_PX * zoom
  const topTicks = []
  for (let mm = 0; mm <= Math.ceil(fmt.w); mm += 5) {
    const x = sx(mm)
    if (x < -2 || x > 4000) continue
    const major = mm % 20 === 0
    topTicks.push(<line key={`t${mm}`} x1={x} y1={major ? RULER_SIZE * 0.2 : RULER_SIZE * 0.55} x2={x} y2={RULER_SIZE} stroke={COL.textMuted} strokeWidth={0.5} />)
    if (major) topTicks.push(<text key={`tl${mm}`} x={x + 2} y={RULER_SIZE * 0.7} fontSize={8} fill={COL.textMuted}>{mm}</text>)
  }
  if (cursorMm) topTicks.push(<line key="cur" x1={sx(cursorMm.x)} y1={0} x2={sx(cursorMm.x)} y2={RULER_SIZE} stroke={COL.gold} strokeWidth={1} />)
  const leftTicks = []
  for (let mm = 0; mm <= Math.ceil(fmt.h); mm += 5) {
    const y = sy(mm)
    if (y < -2 || y > 4000) continue
    const major = mm % 20 === 0
    leftTicks.push(<line key={`t${mm}`} x1={major ? RULER_SIZE * 0.2 : RULER_SIZE * 0.55} y1={y} x2={RULER_SIZE} y2={y} stroke={COL.textMuted} strokeWidth={0.5} />)
    if (major) leftTicks.push(<text key={`tl${mm}`} x={1} y={y + 8} fontSize={7} fill={COL.textMuted}>{mm}</text>)
  }
  if (cursorMm) leftTicks.push(<line key="cur" x1={0} y1={sy(cursorMm.y)} x2={RULER_SIZE} y2={sy(cursorMm.y)} stroke={COL.gold} strokeWidth={1} />)
  const multiStrokeValue = commonValue(multiStroke, 'stroke')
  const multiFillValue = commonValue(multiFill, 'fill')
  const multiX = commonValue(multiPosition, 'x')
  const multiY = commonValue(multiPosition, 'y')
  const editingFlat = editingFlatId
    ? (editingFlatGroupId
        ? (curObjs.find(o => o.id === editingFlatGroupId)?.children || []).find(c => c.id === editingFlatId && c.type === 'path')
        : curObjs.find(o => o.id === editingFlatId && ['sketch_svg', 'path'].includes(o.type)))
    : null
  const selectedDeletableIds = selectedObjects.filter(o => o.layer === 'free' || o.type === 'data_block').map(o => o.id)
  const deleteSelection = () => {
    if (!selectedDeletableIds.length) return
    deleteObjects(selectedDeletableIds)
  }
  // S8: buscatraços — calen 2+ objectes seleccionats i tots convertibles a Paper.js.
  const pathfinderReady = locked && selectedObjects.length >= 2 && selectedObjects.every(o => PATHFINDER_TYPES.includes(o.type))
  const applyPathfinder = (op) => {
    if (!pathfinderReady) return
    const ordered = curObjs.filter(o => selectedIds.includes(o.id))   // z-order (baix→dalt) per a 'subtract'
    const style = ordered[0]
    const result = booleanOp(ordered, op, style, uid)
    if (!result) { flash(t('tech_sheet.pathfinder_error')); return }
    const ids = new Set(selectedIds)
    // Una sola updatePageObjects → un sol setPages → S0 coalesceix a UNA entrada d'historial.
    updatePageObjects(currentPage, objs => [...objs.filter(o => !ids.has(o.id)), result])
    setSelectedIds([result.id])
  }
  // ── S2.3 — TOPOLOGIA de subpath al nivell superior (sobre la subpath activa) ────────────
  const activeSubObj = activeSubpath ? curObjs.find(o => o.id === activeSubpath.objId && o.type === 'path') : null
  // Extreu la subpath activa (entrada paths[index]) com a OBJECTE independent de primer nivell.
  const extractActiveSubpath = () => {
    if (!activeSubObj || !Array.isArray(activeSubObj.paths) || activeSubObj.paths.length <= 1) return
    const entry = activeSubObj.paths[activeSubpath.index]
    const newObj = {
      id: uid(), type: 'path', layer: 'free', x: activeSubObj.x || 0, y: activeSubObj.y || 0,
      rotation: activeSubObj.rotation, scaleX: activeSubObj.scaleX, scaleY: activeSubObj.scaleY,
      stroke: activeSubObj.stroke, fill: activeSubObj.fill, strokeWidth: activeSubObj.strokeWidth,
      paths: [entry],
    }
    updatePageObjects(currentPage, objs => [
      ...objs.map(x => x.id === activeSubObj.id ? { ...x, paths: x.paths.filter((_, i) => i !== activeSubpath.index) } : x),
      newObj,
    ])
    setActiveSubpath(null)
    setSelectedIds([newObj.id])
  }
  // Tanca/obre la subpath activa (commuta el flag closed de l'entrada; simple o compost exterior).
  const toggleActiveSubpathClosed = () => {
    if (!activeSubObj) return
    const flip = (e) => e.subpaths
      ? { ...e, subpaths: e.subpaths.map((sp, i) => (i === 0 ? { ...sp, closed: !sp.closed } : sp)) }
      : { ...e, closed: !e.closed }
    updateObject(activeSubObj.id, { paths: activeSubObj.paths.map((p, i) => (i === activeSubpath.index ? flip(p) : p)) })
  }
  // Esborra la subpath activa (mateixa lògica que el Delete sensible al context; botó descobrible).
  const deleteActiveSubpath = () => {
    if (!activeSubObj) return
    if (activeSubObj.paths.length <= 1) deleteObject(activeSubObj.id)
    else updateObject(activeSubObj.id, { paths: activeSubObj.paths.filter((_, i) => i !== activeSubpath.index) })
    setActiveSubpath(null)
  }
  // E3: pre-extracció — mateixa lògica exacta que abans vivia dins el keydown c/v/d; ara
  // teclat i menú "Edició" criden les mateixes funcions (zero canvi de comportament).
  const copySelection = () => {
    const toCopy = objectsOf(currentPage).filter(o => selectedIds.includes(o.id) && o.layer === 'free')
    if (!toCopy.length) return
    clipboardRef.current = toCopy
  }
  const pasteClipboard = () => {
    if (!clipboardRef.current.length) return
    const pasted = clipboardRef.current.map(o => offsetObjectMm(cloneWithNewIds(o, uid), 5, 5))
    updatePageObjects(currentPage, objs => [...objs, ...pasted])
    setSelectedIds(pasted.map(o => o.id))
  }
  const duplicateSelection = () => {
    const toDup = objectsOf(currentPage).filter(o => selectedIds.includes(o.id) && o.layer === 'free')
    if (!toDup.length) return
    const duped = toDup.map(o => offsetObjectMm(cloneWithNewIds(o, uid), 5, 5))
    updatePageObjects(currentPage, objs => [...objs, ...duped])
    setSelectedIds(duped.map(o => o.id))
  }
  // E3: pre-extracció dels botons visible/lock del panell de capes.
  const toggleVisible = (id) => {
    const o = curObjs.find(x => x.id === id)
    if (!o) return
    updateObject(id, { visible: o.visible === false ? true : false })
  }
  const toggleLock = (id) => {
    const o = curObjs.find(x => x.id === id)
    if (!o) return
    updateObject(id, { locked: o.locked === true ? false : true })
  }
  const selDim = dimensionInfo(selObj)
  const paperFlatLabels = {
    loading: t('tech_sheet.flat_loading'),
    pathSelected: t('tech_sheet.flat_path_selected'),
    noPath: t('tech_sheet.flat_no_path'),
    changed: t('tech_sheet.flat_changed'),
    importError: t('tech_sheet.flat_import_error'),
    // G1 — els dos cursors (selecció de forma / selecció directa).
    shape_select: t('tech_sheet.node_tool_shape'),
    direct_select: t('tech_sheet.node_tool_direct'),
    // S1.3 — barra contextual d'edició de nodes del sub-editor.
    node_select: t('tech_sheet.node_tool_select'),
    node_add: t('tech_sheet.node_tool_add'),
    node_remove: t('tech_sheet.node_tool_remove'),
    node_convert: t('tech_sheet.node_tool_convert'),
    node_scissors: t('tech_sheet.node_tool_scissors'),
    node_close: t('tech_sheet.node_close'),
    node_open: t('tech_sheet.node_open'),
    node_split: t('tech_sheet.node_split'),
    node_editing: t('tech_sheet.node_editing'),
  }

  // PAL-1: PALETA D'EINES (estil Adobe) — 6 categories amb separadors; els grups amb múltiples
  // eines són FLYOUTS (icona + ▸; clic al triangle o press-and-hold desplega; l'última usada queda
  // visible). Es conserven els tool keys i TOTS els handlers (RECT_TOOLS/LINE_TOOLS/PRESET_TOOLS,
  // onStageMouseDown…): això és només presentació + agrupació. Cap eina de la paleta és un
  // placeholder: totes tenen handler (el suport de `soon` era codi mort, retirat a F7).
  const PALETTE = [
    // `node` i `subpath` han marxat a la tab "Editar" del ribbon: són les úniques dues eines de
    // la paleta que no creen res —seleccionen més fi dins d'un objecte que ja existeix— i el
    // seu lloc és al costat de la resta d'eines d'edició, no entre les de dibuix.
    { cat: 'select', items: [
      { kind: 'tool', k: 'select', icon: 'ti-pointer-2', label: t('tech_sheet.tool_select') },
    ] },
    { cat: 'draw', items: [
      { kind: 'tool', k: 'draw', icon: 'ti-pencil', label: t('tech_sheet.tool_draw') },
      { kind: 'tool', k: 'pen', icon: 'ti-vector-bezier', label: t('tech_sheet.tool_pen') },
      { kind: 'flyout', id: 'shapes', label: t('tech_sheet.tool_group_shapes'), tools: [
        { k: 'rect', icon: 'ti-square', label: t('tech_sheet.tool_rect') },
        { k: 'rect_round', icon: 'ti-square-rounded', label: t('tech_sheet.tool_rect_round') },
        { k: 'ellipse', icon: 'ti-circle', label: t('tech_sheet.tool_ellipse') },
        { k: 'polygon', icon: 'ti-hexagon', label: t('tech_sheet.tool_polygon') },
      ] },
      { kind: 'flyout', id: 'lines', label: t('tech_sheet.tool_group_lines'), tools: [
        { k: 'line', icon: 'ti-line', label: t('tech_sheet.tool_line') },
        { k: 'line_dot', icon: 'ti-line-dashed', label: t('tech_sheet.tool_line_dot') },
      ] },
      { kind: 'flyout', id: 'arrows', label: t('tech_sheet.tool_group_arrows'), tools: [
        { k: 'arrow', icon: 'ti-arrow-right', label: t('tech_sheet.tool_arrow') },
        { k: 'arrow2', icon: 'ti-arrows-horizontal', label: t('tech_sheet.tool_arrow2') },
        { k: 'arrow_curve', icon: 'ti-vector-spline', label: t('tech_sheet.tool_arrow_curve') },
      ] },
    ] },
    { cat: 'text', items: [
      { kind: 'flyout', id: 'text', label: t('tech_sheet.tool_group_text'), tools: [
        { k: 'text', icon: 'ti-text-recognition', label: t('tech_sheet.tool_text') },
        { k: 'text_box', icon: 'ti-text-scan-2', label: t('tech_sheet.tool_text_box') },
      ] },
    ] },
    { cat: 'annot', items: [
      { kind: 'tool', k: 'cota_pom', icon: 'ti-ruler-measure', label: t('tech_sheet.tool_cota_pom') },
      { kind: 'tool', k: 'note', icon: 'ti-arrow-guide', label: t('tech_sheet.tool_note') },
      { kind: 'flyout', id: 'presets', label: t('tech_sheet.tool_group_presets'), tools: [
        { k: 'preset_callout', icon: 'ti-message-2-share', label: t('tech_sheet.preset_callout') },
        { k: 'preset_detail_circle', icon: 'ti-circle-dashed', label: t('tech_sheet.preset_detail_circle') },
        { k: 'preset_legend', icon: 'ti-list-details', label: t('tech_sheet.preset_legend') },
      ] },
    ] },
    { cat: 'nav', items: [
      // PEÇA P: pan funcional (arrossega el llenç). També s'activa amb la barra espaiadora.
      { kind: 'tool', k: 'pan', icon: 'ti-hand-stop', label: t('tech_sheet.tool_pan') },
    ] },
  ]
  // Eines funcionals planes (per resoldre icona/etiqueta de l'eina activa a la barra contextual).
  const flatTools = PALETTE.flatMap(c => c.items.flatMap(it => it.kind === 'flyout' ? it.tools : (it.kind === 'tool' ? [it] : [])))
  const activeToolDef = flatTools.find(tl => tl.k === tool) || { icon: 'ti-pointer-2', label: t('tech_sheet.tool_select') }
  // Flyout: eina visible (col·lapsada) = l'activa si pertany al grup, si no l'última triada, si no la 1a.
  const flyoutVisible = (fl) => fl.tools.find(tl => tl.k === tool) || fl.tools.find(tl => tl.k === flyoutSel[fl.id]) || fl.tools[0]
  const cancelHold = () => { if (holdTimer.current) { clearTimeout(holdTimer.current); holdTimer.current = null } }
  const openFlyout = (id, rect) => { setFlyoutRect(rect); setFlyoutOpen(id) }
  const startHold = (id, rect) => { cancelHold(); holdTimer.current = setTimeout(() => { suppressClick.current = true; openFlyout(id, rect) }, 300) }
  const pickFlyoutTool = (fl, k) => { setFlyoutSel(s => ({ ...s, [fl.id]: k })); setTool(k); setFlyoutOpen(null); cancelHold() }
  // IMP-1/2: panell d'importació al dock dret. openImport substitueix els tabs; closeImport hi torna.
  const openImport = (mode) => { setImportFile(null); setImportDrag(false); setImportMode(mode) }
  const closeImport = () => { setImportMode(null); setImportFile(null); setImportDrag(false) }
  // IMP-2: "Inserir" — reaprofita els handlers existents (no vinculem fitxers, els importem).
  const handleImportInsert = () => {
    if (!importFile) return
    if (importMode === 'image') {
      handleFile(importFile)            // crea type:'image' amb dataURL
      closeImport()
      return
    }
    const name = (importFile.name || '').toLowerCase()
    if (name.endsWith('.svg') || importFile.type === 'image/svg+xml') {
      handleFlatSvgFile(importFile)     // converteix SVG → path editable
      closeImport()
    } else {
      flash(t('tech_sheet.import_dxf_soon'))   // DXF (i altres) encara no suportats
    }
  }
  const onImportPick = (file) => { if (file) setImportFile(file) }
  const onImportDrop = (e) => {
    e.preventDefault(); setImportDrag(false)
    onImportPick(e.dataTransfer.files?.[0])
  }

  // S03c · C5.3 — l'ALTRA font del panell d'import: el tenant sencer, no la màquina local.
  // Aquí NO hi ha `usar-al-model`: no vinculem el fitxer, n'importem els BYTES (un SVG es
  // converteix en paths editables; una imatge s'encasta com a dataURL). El document no en
  // guarda cap referència, de manera que no hi ha sobirania a defensar — al contrari que a C5.2.
  const importarDelTenant = async (f) => {
    if (!locked || !f) return
    setImportNavOpen(false)
    const nom = (f.nom_fitxer || '').toLowerCase()
    // Un ItemFitxer porta `garment_type_item`; un ModelFitxer, `model`. Cada mon te el seu
    // endpoint de descarrega autenticat (D13); `url_extern` viu fora i no li enviem el token.
    const extern = !!f.url_extern
    const mon = f.garment_type_item != null ? 'item-fitxers' : 'model-fitxers'
    const url = extern ? f.url_extern : `${API}/api/v1/${mon}/${f.id}/download/`
    try {
      const r = await fetch(url, extern ? undefined : { headers: uploadHeaders })
      if (!r.ok) throw new Error('fetch')
      if (nom.endsWith('.svg')) {
        await importFlatSvgText(await r.text())     // SVG → path editable, com el camí local
      } else if (nom.endsWith('.dxf')) {
        flash(t('tech_sheet.import_dxf_soon'))      // el motor DXF segueix pendent
      } else {
        addImageFromDataURL(await blobToDataURL(await r.blob()))
      }
      closeImport()
    } catch {
      flash(t('tech_sheet.flat_import_error'))
    }
  }
  // ── F1 — Peces del patró vigent ────────────────────────────────────────────
  // El llistat no porta les peces (el serializer de llista les treu a posta: un llistat no ha
  // d'arrossegar milers de punts), o sigui que el detall es demana en obrir el selector.
  const obrirPeces = async () => {
    if (!locked || !patternFile) return
    setPiecePicker({ loading: true })
    try {
      const r = await fetch(`${API}/api/v1/patterns/pattern-files/${patternFile.id}/`, { headers: authHeaders })
      if (!r.ok) throw new Error('http')
      const d = await r.json()
      setPiecePicker({ pieces: d.pieces || [] })
    } catch { setPiecePicker({ error: true }) }
  }

  // El render del motor NO es pot clavar a `src`: l'endpoint va gated per Authorization i un
  // <img> no pot portar capçaleres (el mateix mur que els assets del .ftt). Es baixa amb
  // capçalera i s'encasta com a dataURL — exactament el que ja fa importarDelTenant.
  //
  // L'aspecte surt de l'SVG, no del bounding box de la peça: el render hi posa marges, i fer
  // servir el bbox deformaria el dibuix just per l'amplada d'aquest marge.
  const inserirPeca = async (peca) => {
    if (!locked || !patternFile) return
    try {
      const url = `${API}/api/v1/patterns/pattern-files/${patternFile.id}/render.svg/?piece=${encodeURIComponent(peca.nom_block)}`
      const r = await fetch(url, { headers: uploadHeaders })
      if (!r.ok) throw new Error('http')
      const svgText = await r.text()
      const ratio = svgAspectRatio(svgText)
      if (!ratio) throw new Error('svg')
      const width = ratio >= PIECE_BOX_W / PIECE_BOX_H ? PIECE_BOX_W : PIECE_BOX_H * ratio
      // Blob → readAsDataURL dona un dataURL BASE64, que és el que el backend sap extreure a
      // asset (un dataURL amb `charset=utf-8` no li casa el patró i es quedaria inline).
      const src = await blobToDataURL(new Blob([svgText], { type: 'image/svg+xml' }))
      // En cascada: dues peces seguides a la mateixa cantonada es tapen l'una a l'altra, i qui
      // n'insereix dues creu que n'hi ha una. Cada peça nova entra una mica més avall.
      const n = objectsOf(currentPage).filter(o => o.type === 'pattern_piece').length
      addObject({
        id: uid(), type: 'pattern_piece', layer: 'free',
        x: 20 + (n % 5) * 10, y: 20 + (n % 5) * 10, width, height: width / ratio,
        src, piece_name: peca.nom_block, pattern_file_id: patternFile.id, caption: true,
      })
      setPiecePicker(null)
    } catch {
      flash(t('tech_sheet.piece_insert_error'))
    }
  }

  const ribbonTabs = [
    { id: 'file', label: t('tech_sheet.ribbon_file') },
    { id: 'page', label: t('tech_sheet.ribbon_page') },
    { id: 'insert', label: t('tech_sheet.ribbon_insert') },
    { id: 'organize', label: t('tech_sheet.ribbon_organize') },
    { id: 'editar', label: t('tech_sheet.ribbon_edit') },
  ]
  const ribbonTabStyle = (active) => ({
    minWidth: 86, height: 28, border: `1px solid ${active ? COL.gold : 'transparent'}`,
    // Una tab és una superfície SELECCIONADA, no una eina activa → goldPale (P-C).
    borderBottomColor: active ? COL.gold : COL.border, borderRadius: '6px 6px 0 0',
    background: active ? COL.goldPale : 'transparent', color: active ? COL.gold : COL.textMain,
    fontFamily: FONT, fontSize: 'var(--fs-body)', fontWeight: active ? 700 : 500,
    cursor: 'pointer',
  })
  const ribbonToolStyle = (disabled = false, active = false) => ({
    width: 72, flexShrink: 0, minHeight: 50, display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', gap: 3, padding: '5px 3px', border: `1px solid ${active ? COL.gold : COL.border}`,
    // `active` al ribbon marca EINA/MODE engegat (no element seleccionat) → gold ple + blanc (P-C).
    borderRadius: 6, background: active ? COL.gold : COL.field, color: active ? 'var(--white)' : COL.textMain,
    fontFamily: FONT, fontSize: 'var(--fs-caption)', lineHeight: 1.1, textAlign: 'center', overflow: 'hidden',
    cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.45 : 1,
  })
  // Peça 4: etiqueta del botó del ribbon — màx 2 línies, trunca amb ellipsis (títol complet al hover).
  const ribbonLabelStyle = { display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 2, overflow: 'hidden', width: '100%', wordBreak: 'break-word' }
  // Separador de grup i camp etiquetat del ribbon: fins ara el separador era un literal inline
  // usat una sola vegada; amb la tab Editar passen a ser cinc grups i mereix un nom.
  const ribbonSep = { width: 1, height: 50, background: COL.border, flexShrink: 0, alignSelf: 'center' }
  const ribbonFieldStyle = {
    display: 'inline-flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    gap: 3, minHeight: 50, flexShrink: 0, padding: '5px 3px',
    fontSize: 'var(--fs-caption)', color: COL.textMain, fontFamily: FONT,
  }
  const ribbonMiniInput = {
    width: 56, height: 24, border: `1px solid ${COL.border}`, borderRadius: 6,
    background: COL.field, color: COL.textMain, fontFamily: FONT, fontSize: 'var(--fs-label)', padding: '0 6px',
  }
  const ribbonSelectStyle = {
    height: 50, minWidth: 86, border: `1px solid ${COL.border}`, borderRadius: 6,
    background: COL.field, color: COL.textMain, fontFamily: FONT, fontSize: 'var(--fs-body)',
    padding: '0 6px',
  }
  const ribbonTool = ({ key, icon, label, onClick, disabled, active, title }) => (
    <button key={key} type="button" onClick={onClick} disabled={disabled} title={title || label}
      style={ribbonToolStyle(disabled, active)}>
      <i className={`ti ${icon}`} aria-hidden="true" style={{ fontSize: 18, flexShrink: 0 }} />
      <span style={ribbonLabelStyle}>{label}</span>
    </button>
  )
  const renderRibbonContent = () => {
    if (!locked) {
      return <span style={{ color: COL.textMuted, padding: '0 8px' }}><i className="ti ti-eye" aria-hidden="true" style={{ marginRight: 5 }} />{t('tech_sheet.readonly_overlay')}</span>
    }
    if (ribbonGroup === 'file') {
      return [
        ribbonTool({ key: 'export', icon: 'ti-file-download', label: t('tech_sheet.export_pdf'), onClick: onExport, disabled: exporting }),
        ribbonTool({ key: 'save-template', icon: 'ti-template', label: t('tech_sheet.save_as_template'), onClick: () => setSaveAsTpl({ nom: '', descripcio: '' }), disabled: !locked }),
        // Interruptor del MODE PLANTILLA: canvia el `kind` del document (es desa al proper
        // autosave) i, amb ell, el render de placeholders i la disponibilitat del tab Camps.
        ribbonTool({ key: 'template-mode', icon: 'ti-forms', label: t('tech_sheet.template_mode'), onClick: () => setTemplateMode(v => { if (v) setDockTab(d => (d === 'fields' ? 'properties' : d)); return !v }), active: templateMode, title: t('tech_sheet.template_mode_title'), disabled: !locked }),
        ribbonTool({ key: 'autosave', icon: saveState === 'error' ? 'ti-alert-triangle' : 'ti-device-floppy', label: saveLabel || t('tech_sheet.autosave'), disabled: true, title: t('tech_sheet.autosave_title') }),
        ribbonTool({ key: 'version', icon: 'ti-history', label: `v${sheet?.versio ?? 1}`, disabled: true, title: t('tech_sheet.version_current') }),
      ]
    }
    if (ribbonGroup === 'page') {
      return [
        ribbonTool({ key: 'add-page', icon: 'ti-file-plus', label: t('tech_sheet.add_page'), onClick: addPage }),
        ribbonTool({ key: 'delete-page', icon: 'ti-file-minus', label: t('tech_sheet.delete_page'), onClick: () => removePage(currentPage), disabled: pages.length <= 1 }),
        <select key="format" value={pageFormat} onChange={e => setPageFormat(e.target.value)} title={t('tech_sheet.page_format')} style={ribbonSelectStyle}>
          {Object.entries(PAGE_FORMATS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>,
        ribbonTool({ key: 'zoom-out', icon: 'ti-minus', label: t('tech_sheet.zoom_out'), onClick: () => setZoomClamped(z => z - ZOOM_STEP) }),
        ribbonTool({ key: 'zoom-in', icon: 'ti-plus', label: t('tech_sheet.zoom_in'), onClick: () => setZoomClamped(z => z + ZOOM_STEP) }),
        ribbonTool({ key: 'zoom-100', icon: 'ti-zoom-reset', label: '100%', onClick: () => setZoomClamped(1), active: zoom === 1 }),
        ribbonTool({ key: 'zoom-fit', icon: 'ti-arrows-maximize', label: t('tech_sheet.zoom_fit'), onClick: fitZoomToViewport }),
      ]
    }
    if (ribbonGroup === 'insert') {
      return [
        ribbonTool({ key: 'header', icon: 'ti-layout-navbar', label: t('tech_sheet.model_header'), onClick: insertHeader }),
        ribbonTool({ key: 'logo', icon: 'ti-photo', label: t('tech_sheet.client_logo'), onClick: insertLogo, title: customerLogoUrl ? t('tech_sheet.insert_logo_title') : t('tech_sheet.no_logo_title') }),
        ribbonTool({ key: 'table', icon: 'ti-table', label: t('tech_sheet.ribbon_table'), onClick: () => setTablePicker({}), disabled: !locked }),
        ribbonTool({ key: 'flat', icon: 'ti-vector', label: t('tech_sheet.flat_insert'), onClick: insertFlatSketch }),
        // F1: si el model no té patró, l'eina es veu però no s'obre — i diu per què.
        ribbonTool({
          key: 'pattern-piece', icon: 'ti-shirt', label: t('tech_sheet.piece_insert'),
          onClick: obrirPeces, disabled: !locked || !patternFile,
          title: patternFile ? t('tech_sheet.piece_insert_title') : t('tech_sheet.piece_no_pattern'),
        }),
        ribbonTool({ key: 'import-flat', icon: 'ti-file-import', label: t('tech_sheet.flat_import'), onClick: () => openImport('garment') }),
        // R1: placeholder — el flux d'import de mesures es dissenyarà més endavant (sense handler).
        ribbonTool({ key: 'image', icon: 'ti-photo-plus', label: t('tech_sheet.tool_image'), onClick: () => openImport('image') }),
        // S03b · P7 — el "futur tab Components" que anunciava la NOTA (R1): un sol botó que obre
        // el FilePicker (Model / Catàleg / Importar), en lloc dels N botons de fitxer d'abans.
        ribbonTool({ key: 'files', icon: 'ti-folder', label: t('tech_sheet.tool_files'), onClick: () => setFilePicker(true), disabled: !locked }),
      ]
    }
    // TAB "EDITAR" — superfície única de l'edició fina. Substitueix la barra contextual F1 (que
    // vivia entre els menús i el ribbon, apareixia i desapareixia, i feia wrap a dues files amb
    // els nou grups oberts). Les eines es reindexen per ABAST, no per superfície d'origen:
    //   ENTRADA  → les dues eines que venien de la paleta (node, subpath)
    //   NODE     → dos cursors + afegir/treure/convertir/tisores + topologia
    //   FORMA    → booleanes · alinear · distribuir · mirall · rotar · escalar · z-ordre
    //   APARENÇA → emplenat · traç · gruix (transversal)
    // Els grups de FORMA només es pinten quan hi ha formes seleccionades, com abans; el que
    // canvia és que ara viuen sempre al mateix lloc i amb etiqueta llegible (72×50).
    if (ribbonGroup === 'editar') {
      const shapeMode = nodeSel.mode === 'shape'
      const nShapes = nodeSel.shapeCount || 0
      const out = [
        ribbonTool({ key: 'tool-node', icon: 'ti-vector', label: t('tech_sheet.tool_node'), onClick: () => setTool('node'), active: tool === 'node', disabled: !locked }),
        ribbonTool({ key: 'tool-subpath', icon: 'ti-vector-triangle', label: t('tech_sheet.tool_subpath'), onClick: () => setTool('subpath'), active: tool === 'subpath', disabled: !locked }),
        <span key="sep-entrada" style={ribbonSep} />,
      ]
      if (!editingFlatId) {
        out.push(<span key="hint" style={{ color: COL.textMuted, fontSize: 'var(--fs-label)', padding: '0 8px', alignSelf: 'center' }}>{t('tech_sheet.edit_tab_hint')}</span>)
        return out
      }
      SHAPE_TOOL_ITEMS.forEach(it => out.push(ribbonTool({
        key: `nt-${it.k}`, icon: it.icon, label: paperFlatLabels[it.label],
        onClick: () => setNodeTool(it.k), active: nodeTool === it.k, title: `${paperFlatLabels[it.label]} · ${it.sc}`,
      })))
      NODE_TOOL_ITEMS.forEach(it => out.push(ribbonTool({
        key: `nt-${it.k}`, icon: it.icon, label: paperFlatLabels[it.label],
        onClick: () => setNodeTool(it.k), active: nodeTool === it.k, title: `${paperFlatLabels[it.label]} · ${it.sc}`,
      })))
      out.push(<span key="sep-topo" style={ribbonSep} />)
      out.push(ribbonTool({ key: 'n-close', icon: 'ti-link', label: t('tech_sheet.node_close'), onClick: () => runNode('close') }))
      out.push(ribbonTool({ key: 'n-open', icon: 'ti-link-off', label: t('tech_sheet.node_open'), onClick: () => runNode('open') }))
      out.push(ribbonTool({ key: 'n-split', icon: 'ti-arrows-split', label: t('tech_sheet.node_split'), onClick: () => runNode('split') }))
      if (shapeMode && nShapes >= 2) {
        out.push(<span key="sep-bool" style={ribbonSep} />)
        ;[
          { op: 'unite', icon: 'ti-layers-union', label: 'pathfinder_unite' },
          { op: 'subtract', icon: 'ti-layers-subtract', label: 'pathfinder_subtract_hint' },
          { op: 'intersect', icon: 'ti-layers-intersect', label: 'pathfinder_intersect' },
          { op: 'exclude', icon: 'ti-layers-difference', label: 'pathfinder_exclude' },
        ].forEach(pf => out.push(ribbonTool({ key: `pf-${pf.op}`, icon: pf.icon, label: t(`tech_sheet.${pf.label}`), onClick: () => runNode('booleanShapes', pf.op) })))
        out.push(<span key="sep-align" style={ribbonSep} />)
        ;[
          { m: 'left', icon: 'ti-layout-align-left', label: 'align_left_short' },
          { m: 'center', icon: 'ti-layout-align-center', label: 'align_center_short' },
          { m: 'right', icon: 'ti-layout-align-right', label: 'align_right_short' },
          { m: 'top', icon: 'ti-layout-align-top', label: 'align_top_short' },
          { m: 'middle', icon: 'ti-layout-align-middle', label: 'align_middle_short' },
          { m: 'bottom', icon: 'ti-layout-align-bottom', label: 'align_bottom_short' },
        ].forEach(a => out.push(ribbonTool({ key: `al-${a.m}`, icon: a.icon, label: t(`tech_sheet.${a.label}`), onClick: () => runNode('alignShapes', a.m) })))
        out.push(ribbonTool({ key: 'sh-dist-h', icon: 'ti-layout-distribute-horizontal', label: t('tech_sheet.distribute_h_short'), onClick: () => runNode('distributeShapes', 'h'), disabled: nShapes < 3 }))
        out.push(ribbonTool({ key: 'sh-dist-v', icon: 'ti-layout-distribute-vertical', label: t('tech_sheet.distribute_v_short'), onClick: () => runNode('distributeShapes', 'v'), disabled: nShapes < 3 }))
      }
      if (shapeMode && nShapes >= 1) {
        out.push(<span key="sep-tr" style={ribbonSep} />)
        out.push(ribbonTool({ key: 'sh-mir-h', icon: 'ti-flip-horizontal', label: t('tech_sheet.mirror_h'), onClick: () => runNode('mirrorShapes', 'h') }))
        out.push(ribbonTool({ key: 'sh-mir-v', icon: 'ti-flip-vertical', label: t('tech_sheet.mirror_v'), onClick: () => runNode('mirrorShapes', 'v') }))
        out.push(
          <label key="sh-rot" style={ribbonFieldStyle} title={t('tech_sheet.shape_rotate')}>
            <span>{t('tech_sheet.shape_rotate')}</span>
            <input type="number" step="1" placeholder="°"
              onKeyDown={e => { if (e.key === 'Enter') { const v = parseFloat(e.target.value); if (!Number.isNaN(v)) { runNode('rotateShapes', v); e.target.value = '' } } }}
              style={ribbonMiniInput} />
          </label>,
          <label key="sh-sc" style={ribbonFieldStyle} title={t('tech_sheet.shape_scale')}>
            <span>{t('tech_sheet.shape_scale')}</span>
            <input type="number" step="1" min="1" placeholder="%"
              onKeyDown={e => { if (e.key === 'Enter') { const v = parseFloat(e.target.value); if (!Number.isNaN(v) && v > 0) { runNode('scaleShapes', v); e.target.value = '' } } }}
              style={ribbonMiniInput} />
          </label>,
        )
        out.push(<span key="sep-z" style={ribbonSep} />)
        out.push(ribbonTool({ key: 'sh-z-back', icon: 'ti-chevrons-down', label: t('tech_sheet.send_to_back'), onClick: () => runNode('reorderShape', 'back') }))
        out.push(ribbonTool({ key: 'sh-z-bwd', icon: 'ti-arrow-down', label: t('tech_sheet.send_backward'), onClick: () => runNode('reorderShape', 'backward') }))
        out.push(ribbonTool({ key: 'sh-z-fwd', icon: 'ti-arrow-up', label: t('tech_sheet.bring_forward'), onClick: () => runNode('reorderShape', 'forward') }))
        out.push(ribbonTool({ key: 'sh-z-front', icon: 'ti-chevrons-up', label: t('tech_sheet.bring_to_front'), onClick: () => runNode('reorderShape', 'front') }))
      }
      // C3 — la pintura NO és aquí. El bloc "Color i traç" del panell dret opera sempre sobre
      // la selecció activa (objecte, forma o subpath), també durant l'edició de nodes: tenir-la
      // duplicada al ribbon era la quarta superfície per a la mateixa acció.
      return out
    }
    return [
      ribbonTool({ key: 'align-left', icon: 'ti-layout-align-left', label: t('tech_sheet.align_left_short'), onClick: () => alignSelection('left'), disabled: nodeMode || selectedObjects.length < 2 }),
      ribbonTool({ key: 'align-center', icon: 'ti-layout-align-center', label: t('tech_sheet.align_center_short'), onClick: () => alignSelection('center'), disabled: nodeMode || selectedObjects.length < 2 }),
      ribbonTool({ key: 'align-right', icon: 'ti-layout-align-right', label: t('tech_sheet.align_right_short'), onClick: () => alignSelection('right'), disabled: nodeMode || selectedObjects.length < 2 }),
      ribbonTool({ key: 'align-top', icon: 'ti-layout-align-top', label: t('tech_sheet.align_top_short'), onClick: () => alignSelection('top'), disabled: nodeMode || selectedObjects.length < 2 }),
      ribbonTool({ key: 'align-middle', icon: 'ti-layout-align-middle', label: t('tech_sheet.align_middle_short'), onClick: () => alignSelection('middle'), disabled: nodeMode || selectedObjects.length < 2 }),
      ribbonTool({ key: 'align-bottom', icon: 'ti-layout-align-bottom', label: t('tech_sheet.align_bottom_short'), onClick: () => alignSelection('bottom'), disabled: nodeMode || selectedObjects.length < 2 }),
      ribbonTool({ key: 'dist-h', icon: 'ti-layout-distribute-horizontal', label: t('tech_sheet.distribute_h_short'), onClick: () => distributeSelection('h'), disabled: nodeMode || selectedObjects.length < 3 }),
      ribbonTool({ key: 'dist-v', icon: 'ti-layout-distribute-vertical', label: t('tech_sheet.distribute_v_short'), onClick: () => distributeSelection('v'), disabled: nodeMode || selectedObjects.length < 3 }),
      ribbonTool({ key: 'group', icon: 'ti-box-multiple', label: t('tech_sheet.group'), onClick: doGroup, disabled: nodeMode || !canGroup, title: canGroupCompound ? t('tech_sheet.group_compound_title') : t('tech_sheet.group') }),
      ribbonTool({ key: 'ungroup', icon: 'ti-unlink', label: t('tech_sheet.ungroup'), onClick: doUngroup, disabled: nodeMode || !ungroupKind, title: ungroupTitle }),
      ribbonTool({ key: 'mirror-h', icon: 'ti-flip-horizontal', label: t('tech_sheet.mirror_h'), onClick: () => mirrorObjects(mirrorableIds, 'scaleX'), disabled: nodeMode || mirrorableIds.length === 0 }),
      ribbonTool({ key: 'mirror-v', icon: 'ti-flip-vertical', label: t('tech_sheet.mirror_v'), onClick: () => mirrorObjects(mirrorableIds, 'scaleY'), disabled: nodeMode || mirrorableIds.length === 0 }),
      ribbonTool({ key: 'send-back', icon: 'ti-chevrons-down', label: t('tech_sheet.send_to_back'), onClick: () => moveSelectionToFreeLayerEdge('back'), disabled: nodeMode || freeSelectedIds.length === 0 }),
      ribbonTool({ key: 'backward', icon: 'ti-arrow-down', label: t('tech_sheet.send_backward'), onClick: () => moveSelectionInFreeLayer('backward'), disabled: nodeMode || freeSelectedIds.length === 0 }),
      ribbonTool({ key: 'forward', icon: 'ti-arrow-up', label: t('tech_sheet.bring_forward'), onClick: () => moveSelectionInFreeLayer('forward'), disabled: nodeMode || freeSelectedIds.length === 0 }),
      ribbonTool({ key: 'bring-front', icon: 'ti-chevrons-up', label: t('tech_sheet.bring_to_front'), onClick: () => moveSelectionToFreeLayerEdge('front'), disabled: nodeMode || freeSelectedIds.length === 0 }),
      ribbonTool({ key: 'delete', icon: 'ti-trash', label: t('app.delete'), onClick: deleteSelection, disabled: nodeMode || selectedDeletableIds.length === 0 }),
      // S8: buscatraços (unir/restar/intersecar/excloure) — grup separat al final de l'organize.
      <span key="sep-pathfinder" style={{ width: 1, height: 50, background: COL.border, flexShrink: 0 }} />,
      ribbonTool({ key: 'pf-unite', icon: 'ti-layers-union', label: t('tech_sheet.pathfinder_unite'), onClick: () => applyPathfinder('unite'), disabled: nodeMode || !pathfinderReady }),
      ribbonTool({ key: 'pf-subtract', icon: 'ti-layers-subtract', label: t('tech_sheet.pathfinder_subtract'), onClick: () => applyPathfinder('subtract'), disabled: nodeMode || !pathfinderReady }),
      ribbonTool({ key: 'pf-intersect', icon: 'ti-layers-intersect', label: t('tech_sheet.pathfinder_intersect'), onClick: () => applyPathfinder('intersect'), disabled: nodeMode || !pathfinderReady }),
      ribbonTool({ key: 'pf-exclude', icon: 'ti-layers-difference', label: t('tech_sheet.pathfinder_exclude'), onClick: () => applyPathfinder('exclude'), disabled: nodeMode || !pathfinderReady }),
    ]
  }

  // E3: barra de menús en text (Fitxer/Edició/Objecte/Visualització), cortines desplegables sobre
  // el ribbon. Conviu amb el ribbon — no el substitueix, reutilitza els mateixos handlers.
  const menuItem = (key, { label, shortcut, onClick, disabled }) => (
    <div key={key} onClick={() => { if (disabled) return; onClick(); setMenuOpen(null) }}
      style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, padding: '5px 14px', color: disabled ? COL.textMuted : COL.textMain, cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.4 : 1, whiteSpace: 'nowrap' }}
      onMouseEnter={e => { if (!disabled) e.currentTarget.style.background = COL.goldPale }}
      onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}>
      <span>{label}</span>
      {shortcut && <span style={{ color: COL.textMuted, fontSize: 'var(--fs-label)', marginLeft: 12 }}>{shortcut}</span>}
    </div>
  )
  const menuSep = (key) => <div key={key} style={{ borderTop: `1px solid ${COL.border}`, margin: '4px 0' }} />
  // OBJECTE: totes les entrades, a més de la seva condició pròpia, es deshabiliten si !locked.
  // F4 — en mode edició de nodes, cap acció d'ABAST OBJECTE (grup, z-order, alinear, mirall,
  // buscatraços, bloquejar…) és clicable: la barra superior contextual mana sobre node/segment/subpath.
  const objDisabled = (cond) => !locked || !!editingFlatId || cond
  const menuEditItems = [
    menuItem('me-undo', { label: t('tech_sheet.menu_undo'), shortcut: '⌘Z', onClick: undo }),
    menuItem('me-redo', { label: t('tech_sheet.menu_redo'), shortcut: '⇧⌘Z', onClick: redo }),
    menuSep('me-sep1'),
    menuItem('me-copy', { label: t('tech_sheet.menu_copy'), shortcut: '⌘C', onClick: copySelection, disabled: objDisabled(freeSelectedIds.length === 0) }),
    menuItem('me-paste', { label: t('tech_sheet.menu_paste'), shortcut: '⌘V', onClick: pasteClipboard, disabled: objDisabled(!clipboardRef.current.length) }),
    menuItem('me-dup', { label: t('tech_sheet.menu_duplicate'), shortcut: '⌘D', onClick: duplicateSelection, disabled: objDisabled(freeSelectedIds.length === 0) }),
    menuItem('me-delete', { label: t('app.delete'), shortcut: '⌫', onClick: deleteSelection, disabled: objDisabled(selectedDeletableIds.length === 0) }),
  ]
  // BARRA DE MENÚS — només EDICIÓ (F7). Dels 33 comandaments que hi havia, 28 eren duplicats
  // exactes del ribbon, del panell Capes o de la barra d'estat; el menú no hi aportava ni icona
  // (menuItem no en sap pintar). Els menús Fitxer, Objecte i Visualització desapareixen sencers.
  // Es conserva EDICIÓ perquè les seves 5 entrades —desfés, refés, copia, enganxa, duplica— són
  // l'ÚNICA superfície visible d'aquestes accions: a tot arreu més només existeixen com a
  // drecera de teclat, i una drecera que ningú anuncia no existeix per a qui no la sap.
  const menuBar = [
    { id: 'edit', label: t('tech_sheet.menu_edit'), items: menuEditItems },
  ]

  // PEÇA P/C: pan actiu (eina 'pan' o espai) i cursor del viewport segons l'eina activa.
  const panActive = locked && (tool === 'pan' || spaceHeld)
  const viewportCursor = !locked ? 'default'
    : panActive ? (panning ? 'grabbing' : 'grab')
    : (tool === 'node' || tool === 'subpath') ? 'pointer'   // S3b: eines de selecció, no de dibuix
    : CROSSHAIR_TOOLS.includes(tool) ? 'crosshair'
    : 'default'

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', background: COL.bg, fontFamily: FONT }}>
      {/* ── Topbar (patró navbar del dashboard: blanc, logo + breadcrumb, gold per a l'acció
            principal) ── */}
      <header style={{ flexShrink: 0, height: 56, display: 'flex', alignItems: 'center', gap: 14, padding: '0 1.2rem', borderBottom: `1px solid ${COL.border}`, background: COL.sidebar, color: COL.textMain }}>
        <button onClick={() => navigate(`/models/${id}`)} title={t('tech_sheet.back_to_model')}
          style={{ ...headerBtn, padding: '5px 8px' }}>
          <i className="ti ti-arrow-left" style={{ fontSize: 15 }} />
        </button>
        <FhortLogo width={92} />
        <span style={{ width: 1, height: 24, background: COL.border }} />
        {/* Breadcrumb: model → editor (com "Models → Blusa CALLIE" al dashboard) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', color: COL.textMuted, minWidth: 0 }}>
          <span onClick={() => navigate(`/models/${id}`)} style={{ cursor: 'pointer', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {model?.codi_intern || `#${id}`}{model?.nom_prenda ? ` · ${model.nom_prenda}` : ''}
          </span>
          <i className="ti ti-chevron-right" style={{ fontSize: 14 }} />
          <strong style={{ color: COL.textMain, fontWeight: 600, whiteSpace: 'nowrap' }}>{t('tech_sheet.doc_editor')}</strong>
          {/* En mode plantilla el llenç menteix a posta (mostra {codi} en lloc del codi real):
              cal dir-ho a la barra, o algú pensarà que la fitxa ha perdut les dades. */}
          {templateMode && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, flexShrink: 0, padding: '2px 8px', borderRadius: 6, background: COL.goldPale, border: `1px solid ${COL.gold}`, color: COL.gold, fontSize: 'var(--fs-label)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.03em', whiteSpace: 'nowrap' }}>
              <i className="ti ti-forms" aria-hidden="true" style={{ fontSize: 12 }} />{t('tech_sheet.template_mode_badge')}
            </span>
          )}
        </div>
        {/* Dreta: context reaprofitat (pàgina, versió, save) + acció principal gold */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 'var(--fs-body)', color: COL.textMuted, whiteSpace: 'nowrap' }}>{t('tech_sheet.page_of', { n: currentPage + 1, total: pages.length })}</span>
          <span style={{ fontSize: 'var(--fs-body)', color: COL.textMuted }}>v{sheet?.versio ?? 1}</span>
          {saveLabel && <span style={{ fontSize: 'var(--fs-label)', color: COL.textMuted }}>{saveLabel}</span>}
          <button onClick={onExport} disabled={exporting}
            style={{ display: 'flex', alignItems: 'center', gap: 6, background: COL.gold, color: 'var(--white)', border: 'none', borderRadius: 8, padding: '0 0.9rem', height: 32, fontSize: 'var(--fs-body)', fontWeight: 500, cursor: exporting ? 'default' : 'pointer', opacity: exporting ? 0.5 : 1, fontFamily: FONT }}>
            <i className="ti ti-file-download" style={{ fontSize: 15 }} />
            {exporting ? t('tech_sheet.exporting') : t('tech_sheet.export_pdf')}
          </button>
        </div>
      </header>

      {/* ── E3: barra de menús en text (Fitxer/Edició/Objecte/Visualització) — cortines desplegables ── */}
      <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', height: 26, background: COL.sidebar, borderBottom: `1px solid ${COL.border}`, padding: '0 8px', fontFamily: FONT, fontSize: 'var(--fs-body)' }}>
        {menuBar.map(m => (
          <div key={m.id} data-menu style={{ position: 'relative' }}>
            <button type="button" onClick={() => setMenuOpen(o => o === m.id ? null : m.id)}
              style={{ border: 'none', background: menuOpen === m.id ? COL.goldPale : 'transparent', color: menuOpen === m.id ? COL.gold : COL.textMain, fontFamily: FONT, fontSize: 'var(--fs-body)', padding: '0 10px', height: 26, cursor: 'pointer' }}>
              {m.label}
            </button>
            {menuOpen === m.id && (
              <div style={{ position: 'absolute', top: '100%', left: 0, zIndex: 70, minWidth: 210, background: COL.bg, border: `1px solid ${COL.border}`, borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.12)', padding: '4px 0' }}>
                {m.items}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ── Ribbon SolidWorks: fila 1 grups, fila 2 comandaments ── */}
      <div style={{ flexShrink: 0, background: CTX_BG, borderBottom: `1px solid ${CTX_BORDER}`, color: CTX_TEXT }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, minHeight: 31, padding: '3px 12px 0' }}>
          {ribbonTabs.map(tab => (
            <button key={tab.id} type="button" onClick={() => setRibbonGroup(tab.id)}
              style={ribbonTabStyle(ribbonGroup === tab.id)}>
              {tab.label}
            </button>
          ))}
          <span style={{ marginLeft: 'auto', color: COL.textMuted, fontSize: 'var(--fs-label)' }}>
            {editingFlatId ? t('tech_sheet.node_edit_mode') : multiSelected ? t('tech_sheet.selected_objects', { n: selectedObjects.length }) : selObj ? `${t('tech_sheet.element')} · ${selObj.type}` : tool !== 'select' ? t('tech_sheet.ctx_tool', { tool: activeToolDef.label }) : t('tech_sheet.ctx_idle')}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, minHeight: 64, padding: '6px 12px 8px', overflowX: 'auto' }}>
          {renderRibbonContent()}
        </div>
      </div>

      {/* position:relative → àncora del FilePicker. El drawer viu DINS de <main>, no al root:
          si s'ancorés al root taparia el botó d'Exportar PDF de la capçalera i els controls de
          zoom del peu (són position:static i qualsevol element posicionat els cobreix). */}
      <main style={{ flex: 1, display: 'flex', minHeight: 0, position: 'relative' }}>
        {filePicker && (
          <FilePicker
            modelId={id}
            garmentTypeItemId={model?.garment_type_item}
            onClose={() => setFilePicker(false)}
            onInsert={(f) => { addModelFitxer(f); setFilePicker(false) }}
          />
        )}
        {importNavOpen && (
          <AssetNavigator
            mode="files"
            filterTipus={TIPUS_GEOMETRIA}
            pickable={(f) => GEOMETRIA_INSERIBLE.test(f.nom_fitxer || '')}
            nav={importNav}
            onNav={setImportNav}
            onClose={() => setImportNavOpen(false)}
            onPick={importarDelTenant}
            actionLabel={t('tech_sheet.import_btn_insert')}
          />
        )}
        {/* ── Paleta d'eines vertical (C2) — 6 categories + flyouts estil Adobe (PAL-1) ── */}
        {locked && (
          <div style={{ width: 46, flexShrink: 0, background: COL.bg, borderRight: `1px solid ${COL.border}`, overflowY: 'auto', overflowX: 'visible', padding: '8px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
            {PALETTE.flatMap((cat, ci) => [
              ci > 0 ? <div key={`sep-${cat.cat}`} style={{ width: 26, height: 1, background: COL.border, margin: '3px 0' }} /> : null,
              ...cat.items.map((it, ii) => {
                const key = `${cat.cat}-${ii}`
                if (it.kind === 'tool') {
                  return (
                    <button key={key} onClick={() => setTool(it.k)}
                      title={TOOL_SHORTCUT[it.k] ? `${it.label} · ${TOOL_SHORTCUT[it.k]}` : it.label}
                      style={{ ...paletteBtn, ...(tool === it.k ? paletteBtnOn : {}) }}>
                      <i className={`ti ${it.icon}`} style={{ fontSize: 17 }} />
                    </button>
                  )
                }
                // flyout
                const vis = flyoutVisible(it)
                const groupActive = it.tools.some(tl => tl.k === tool)
                return (
                  <div key={key} data-flyout={it.id} style={{ position: 'relative' }}>
                    <button
                      onMouseDown={e => startHold(it.id, e.currentTarget.getBoundingClientRect())}
                      onMouseUp={cancelHold} onMouseLeave={cancelHold}
                      onClick={() => { if (suppressClick.current) { suppressClick.current = false; return } pickFlyoutTool(it, vis.k) }}
                      title={`${it.label} — ${vis.label}`}
                      style={{ ...paletteBtn, ...(groupActive ? paletteBtnOn : {}) }}>
                      <i className={`ti ${vis.icon}`} style={{ fontSize: 17 }} />
                      {/* triangle ▸ indicador de flyout — visible per descobribilitat (E1a) */}
                      {it.tools && it.tools.length > 1 && (
                        <i className="ti ti-caret-right-filled" title={t('tech_sheet.flyout_hint')}
                          onClick={e => { e.stopPropagation(); cancelHold(); suppressClick.current = false; openFlyout(it.id, e.currentTarget.parentElement.getBoundingClientRect()) }}
                          style={{ position: 'absolute', right: 0, bottom: 0, fontSize: 11, lineHeight: 1, color: COL.gold, opacity: 0.9 }} />
                      )}
                    </button>
                    {flyoutOpen === it.id && flyoutRect && (
                      <div data-flyout={it.id} style={{ position: 'fixed', left: flyoutRect.right + 4, top: flyoutRect.top, zIndex: 60, display: 'flex', gap: 2, padding: 4, background: COL.bg, border: `1px solid ${COL.border}`, borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.12)' }}>
                        {it.tools.map(tl => (
                          <button key={tl.k} onClick={() => pickFlyoutTool(it, tl.k)}
                            title={tl.label}
                            style={{ ...paletteBtn, ...(tool === tl.k ? paletteBtnOn : {}) }}>
                            <i className={`ti ${tl.icon}`} style={{ fontSize: 17 }} />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )
              }),
            ])}
          </div>
        )}

        {/* ── Centre: Stage Konva, envoltat per un marc amb regles en mm (S2) ── */}
        <div style={{ flex: 1, minWidth: 0, display: 'grid', gridTemplateColumns: `${RULER_SIZE}px 1fr`, gridTemplateRows: `${RULER_SIZE}px 1fr`, background: COL.work, position: 'relative' }}>
          {/* Cantonada */}
          <div style={{ background: COL.sidebar, borderRight: `1px solid ${COL.border}`, borderBottom: `1px solid ${COL.border}` }} />
          {/* Regla superior — arrossegar-ne crea una guia vertical (S2) */}
          <div onMouseDown={(e) => startGuideCreate('x', e)}
            style={{ overflow: 'hidden', background: COL.sidebar, borderBottom: `1px solid ${COL.border}` }}>
            <svg width="100%" height={RULER_SIZE} style={{ display: 'block' }}>{topTicks}</svg>
          </div>
          {/* Regla esquerra — arrossegar-ne crea una guia horitzontal (S2) */}
          <div onMouseDown={(e) => startGuideCreate('y', e)}
            style={{ overflow: 'hidden', background: COL.sidebar, borderRight: `1px solid ${COL.border}` }}>
            <svg width={RULER_SIZE} height="100%" style={{ display: 'block' }}>{leftTicks}</svg>
          </div>
        <div ref={viewportRef} onWheel={onViewportWheel} onScroll={syncRuler}
          onMouseDown={onViewportMouseDown} onMouseMove={onViewportMouseMove} onMouseUp={endPan} onMouseLeave={endPan}
          style={{ background: COL.work, minWidth: 0, overflow: 'auto', position: 'relative', padding: 24, boxSizing: 'border-box', cursor: viewportCursor }}>
          {lockState === 'readonly' && (
            <div style={{ position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)', zIndex: 5, background: COL.sidebar, border: `1px solid ${COL.border}`, borderRadius: 6, padding: '4px 12px', fontSize: 'var(--fs-body)', color: COL.textMuted }}>
              <i className="ti ti-eye" style={{ marginRight: 6 }} />{t('tech_sheet.readonly_overlay')}
            </div>
          )}
          <div style={{ width: pageW * zoom, height: pageH * zoom, position: 'relative', margin: '0 auto' }}>
          <div ref={wrapRef} onDrop={onDrop} onDragOver={e => e.preventDefault()}
            style={{ position: 'relative', width: pageW * zoom, height: pageH * zoom, outline: `1px solid ${COL.border}`, background: 'var(--white)', cursor: viewportCursor }}>
            {/* R1: el zoom el fa Konva (scaleX/scaleY) re-pintant els vectors a la mida real ×
                devicePixelRatio → NÍTID a qualsevol zoom. Ja no s'escala el bitmap per CSS. */}
            <Stage ref={stageRef} width={pageW * zoom} height={pageH * zoom} scaleX={zoom} scaleY={zoom}
              onMouseDown={onStageMouseDown} onMouseMove={onStageMouseMove} onMouseUp={onStageMouseUp}
              onDblClick={finishPenOnDblClick} onDblTap={finishPenOnDblClick}>
              {/* Fons blanc + 3 capes en ordre z. Konva no agrupa per `layer`:
                  ordenem els objectes i pintem en una sola Layer (z per ordre d'array). */}
              <Layer>
                <Rect x={0} y={0} width={pageW} height={pageH} fill={KONVA_COL.white} listening={false} />
                {ordered.filter(o => o.visible !== false).map(o => (
                  <ObjectNode key={o.id} obj={o} src={o.src}
                    tableData={tableData} modelData={model} versio={sheet?.versio} customerLogoUrl={customerLogoUrl}
                    placeholderMode={templateMode}
                    hideTextChildren={editingFlatGroupId === o.id}
                    pageCtx={{ index: currentPage, total: pages.length }}
                    onHeaderContextMenu={locked ? ((e, ho) => { e.evt.preventDefault(); setHeaderMenu(ho.detached ? null : { x: e.evt.clientX, y: e.evt.clientY }) }) : undefined}
                    selected={selectedIds.includes(o.id)}
                    selectable={locked && o.layer !== 'template' && !o.locked}
                    draggable={locked && tool === 'select' && !panActive && o.layer !== 'template' && !o.locked && activeGroup !== o.id}
                    onSelect={(e) => (tool === 'node' && (o.type === 'path' || o.type === 'sketch_svg'))
                      ? startVectorEdit(o)                         // S1.1: eina "Selecció directa (nodes)" → obre l'editor de nodes
                      : handleSelectObject(e, o.id)}
                    onDragStart={handleDragStart(o)}
                    onDragMove={handleDragMove(o)}
                    onDragEnd={handleDragEnd(o)}
                    onTransformEnd={handleTransformEnd(o)}
                    onDblText={() => startTextEdit(o)}
                    onDblVector={() => startVectorEdit(o)}
                    entered={locked && activeGroup === o.id}
                    onDblGroup={() => { if (o.type === 'group') { setActiveGroup(o.id); setSelectedChildId(null); clearSelection() } }}
                    onChildSelect={handleChildSelect}
                    onChildDragEnd={handleChildDragEnd(o.id)}
                    selectedChildId={activeGroup === o.id ? selectedChildId : null}
                    activeSubIndex={activeSubpath?.objId === o.id ? activeSubpath.index : null}
                    subpathTool={tool === 'subpath'}
                    onSubSelect={(i) => { if (!selectedIds.includes(o.id)) selectOnly(o.id); setActiveSubpath({ objId: o.id, index: i }) }}
                    onEndpointDrag={handleEndpointDrag(o)} />
                ))}
                {/* Forma temporal mentre es dibuixa */}
                {(drawTemp?.type === 'rect' || drawTemp?.type === 'rect_round') && <Rect x={drawTemp.x} y={drawTemp.y} width={drawTemp.w} height={drawTemp.h} stroke={KONVA_COL.gold} strokeWidth={1} dash={[4, 4]} cornerRadius={drawTemp.type === 'rect_round' ? 8 : 0} listening={false} />}
                {drawTemp?.type === 'ellipse' && <Ellipse x={drawTemp.x + drawTemp.w / 2} y={drawTemp.y + drawTemp.h / 2} radiusX={drawTemp.w / 2} radiusY={drawTemp.h / 2} stroke={KONVA_COL.textMain} strokeWidth={1} dash={[4, 4]} listening={false} />}
                {drawTemp?.type === 'polygon' && drawTemp.w > 1 && drawTemp.h > 1 && <Line points={polygonPoints(drawTemp.x, drawTemp.y, drawTemp.w, drawTemp.h, polygonSides)} closed stroke={KONVA_COL.textMain} strokeWidth={1} dash={[4, 4]} listening={false} />}
                {(drawTemp?.type === 'line' || drawTemp?.type === 'line_dot' || drawTemp?.type === 'draw') && <Line points={drawTemp.points} stroke={KONVA_COL.textMain} strokeWidth={1} dash={[4, 4]} listening={false} />}
                {(drawTemp?.type === 'arrow' || drawTemp?.type === 'arrow2') && <Arrow points={drawTemp.points} stroke={KONVA_COL.textMain} fill={KONVA_COL.textMain} strokeWidth={1.5} pointerLength={8} pointerWidth={6} pointerAtBeginning={drawTemp.type === 'arrow2'} listening={false} />}
                {/* S7: previsualització del traç de ploma — traç fet (mm→pathToData) + goma fins al cursor (px) */}
                {penTemp && penTemp.points.length >= 2 && (
                  <Path data={pathToData({ closed: false, segments: penTemp.points.map(p => ({ x: toMm(p.x), y: toMm(p.y), inX: toMm(p.inX), inY: toMm(p.inY), outX: toMm(p.outX), outY: toMm(p.outY) })) })}
                    stroke={KONVA_COL.gold} strokeWidth={1.2} listening={false} />
                )}
                {penTemp?.cursor && penTemp.points.length > 0 && (() => {
                  const last = penTemp.points[penTemp.points.length - 1]
                  return <Line points={[last.x, last.y, penTemp.cursor.x, penTemp.cursor.y]} stroke={KONVA_COL.gold} strokeWidth={1} dash={[4, 4]} listening={false} />
                })()}
                {penTemp?.points.map((p, i) => <Rect key={'pen' + i} x={p.x - 2} y={p.y - 2} width={4} height={4} fill={KONVA_COL.gold} listening={false} />)}
                {/* E2: previsualització elàstica de nota-fletxa (punta fixada a p1) i cota (A fixat a p1) */}
                {twoClickTemp?.tool === 'note' && (
                  <Arrow points={[twoClickTemp.p1.x, twoClickTemp.p1.y, twoClickTemp.cursor.x, twoClickTemp.cursor.y]}
                    stroke={KONVA_COL.textMain} fill={KONVA_COL.textMain} strokeWidth={1} pointerLength={8} pointerWidth={6} pointerAtBeginning listening={false} />
                )}
                {twoClickTemp?.tool === 'cota_pom' && (
                  <Line points={[twoClickTemp.p1.x, twoClickTemp.p1.y, twoClickTemp.cursor.x, twoClickTemp.cursor.y]}
                    stroke={KONVA_COL.textMain} strokeWidth={1} dash={[4, 4]} listening={false} />
                )}
                {/* S1: marc de rubber-band mentre s'arrossega en tela buida */}
                {marquee && <Rect x={marquee.x} y={marquee.y} width={marquee.w} height={marquee.h} fill={KONVA_COL.gold} opacity={0.15} stroke={KONVA_COL.gold} strokeWidth={1} dash={[4, 4]} listening={false} />}
                {/* S2: guies daurades temporals de magnetisme (drag) */}
                {snapLines?.x != null && <Line points={[toPx(snapLines.x), 0, toPx(snapLines.x), pageH]} stroke={KONVA_COL.gold} strokeWidth={1} strokeScaleEnabled={false} listening={false} />}
                {snapLines?.y != null && <Line points={[0, toPx(snapLines.y), pageW, toPx(snapLines.y)]} stroke={KONVA_COL.gold} strokeWidth={1} strokeScaleEnabled={false} listening={false} />}
                {/* S2: guies persistents de la pàgina — arrossegables (moure) o expulsables (esborrar) */}
                {curGuides.map((g, i) => (g.axis === 'x'
                  ? <Line key={'g' + i} x={toPx(g.pos)} y={0} points={[0, 0, 0, pageH]} stroke={KONVA_COL.gold} strokeWidth={1} strokeScaleEnabled={false} dash={[6, 3]} hitStrokeWidth={8} draggable dragBoundFunc={(pos) => ({ x: pos.x, y: 0 })} onDragEnd={(e) => onGuideDragEnd('x', i, e)} />
                  : <Line key={'g' + i} x={0} y={toPx(g.pos)} points={[0, 0, pageW, 0]} stroke={KONVA_COL.gold} strokeWidth={1} strokeScaleEnabled={false} dash={[6, 3]} hitStrokeWidth={8} draggable dragBoundFunc={(pos) => ({ x: 0, y: pos.y })} onDragEnd={(e) => onGuideDragEnd('y', i, e)} />
                ))}
                {/* S2: previsualització de la guia en creació (arrossegant des de la regla) */}
                {creatingGuide && creatingGuide.pos >= 0 && creatingGuide.pos <= (creatingGuide.axis === 'x' ? fmt.w : fmt.h) && (
                  creatingGuide.axis === 'x'
                    ? <Line x={toPx(creatingGuide.pos)} y={0} points={[0, 0, 0, pageH]} stroke={KONVA_COL.gold} strokeWidth={1} strokeScaleEnabled={false} dash={[6, 3]} listening={false} />
                    : <Line x={0} y={toPx(creatingGuide.pos)} points={[0, 0, pageW, 0]} stroke={KONVA_COL.gold} strokeWidth={1} strokeScaleEnabled={false} dash={[6, 3]} listening={false} />
                )}
                <Transformer ref={trRef} rotateEnabled ignoreStroke keepRatio={shiftHeld || (selectedObjects.length === 1 && (selObj?.type === 'data_block' || selObj?.type === 'table' || selObj?.type === 'pattern_piece'))}
                  padding={5}
                  borderStroke={KONVA_COL.textMuted} borderStrokeWidth={0.5} borderDash={[4, 4]}
                  anchorSize={6} anchorStroke={KONVA_COL.textMuted} anchorStrokeWidth={1} anchorFill={KONVA_COL.white} anchorCornerRadius={2}
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
                ref={paperFlatRef}
                flat={editingFlat}
                pageW={pageW}
                pageH={pageH}
                zoom={zoom}
                toPx={toPx}
                nodeTool={nodeTool}
                pointerActive={!konvaOwnsPointer}
                onNodeState={setNodeSel}
                onCommit={commitFlatEdit}
                onSplitObject={handleSplitObject}
                onEnterDirect={() => setNodeTool('select')}
                onExitEdit={exitFlatEdit}
              />
            </Suspense>
          )}
          </div>
        </div>
        </div>

        {/* ── Dreta: capes / inserir / propietats ── */}
        <aside style={{ width: 270, flexShrink: 0, borderLeft: `1px solid ${COL.border}`, background: COL.bg, display: 'flex', flexDirection: 'column', minHeight: 0, fontFamily: FONT }}>
          {/* IMP-1/2: panell d'importació — substitueix temporalment els tabs Propietats/Capes */}
          {importMode && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px', borderBottom: `1px solid ${COL.border}`, flexShrink: 0 }}>
                <span style={{ fontSize: 'var(--fs-body)', fontWeight: 700, color: COL.textMain }}>
                  {importMode === 'image' ? t('tech_sheet.import_panel_title_image') : t('tech_sheet.import_panel_title_garment')}
                </span>
                <button type="button" onClick={closeImport} title={t('app.close')}
                  style={{ border: 'none', background: 'transparent', color: COL.textMuted, cursor: 'pointer', fontSize: 18, lineHeight: 1, padding: 2 }}>
                  <i className="ti ti-x" />
                </button>
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '12px 10px 64px' }}>
                {/* D'ON? — origen del fitxer */}
                <div style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: 6 }}>{t('tech_sheet.import_source')}</div>
                <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
                  <button type="button"
                    style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '8px 6px', border: `1px solid ${COL.gold}`, borderRadius: 6, background: COL.goldPale, color: COL.gold, fontFamily: FONT, fontSize: 'var(--fs-body)', fontWeight: 600, cursor: 'default' }}>
                    <i className="ti ti-folder" /> {t('tech_sheet.import_from_local')}
                  </button>
                  {/* C5.3 — font "FTT": el tenant sencer. Nomes per a `garment`: en mode `image`
                      no hi ha cap tipus de fitxer que el filtre de geometria sapiga oferir. */}
                  {importMode === 'garment' ? (
                    <button type="button" onClick={() => setImportNavOpen(true)}
                      style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '8px 6px', border: `1px solid ${COL.gold}`, borderRadius: 6, background: 'transparent', color: COL.gold, fontFamily: FONT, fontSize: 'var(--fs-body)', fontWeight: 600, cursor: 'pointer' }}>
                      <i className="ti ti-building-warehouse" /> {t('tech_sheet.import_from_ftt')}
                    </button>
                  ) : (
                    <button type="button" disabled title={t('tech_sheet.import_soon')}
                      style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '8px 6px', border: `1px solid ${COL.border}`, borderRadius: 6, background: 'transparent', color: COL.textMuted, fontFamily: FONT, fontSize: 'var(--fs-body)', opacity: 0.45, cursor: 'default' }}>
                      <i className="ti ti-building-warehouse" /> {t('tech_sheet.import_from_ftt')} ({t('tech_sheet.import_soon')})
                    </button>
                  )}
                </div>

                {/* Drop zone (origen local) */}
                <div onDragOver={e => { e.preventDefault(); setImportDrag(true) }}
                  onDragLeave={() => setImportDrag(false)} onDrop={onImportDrop}
                  style={{ border: `1.5px dashed ${importDrag ? COL.gold : COL.border}`, borderRadius: 8, background: importDrag ? COL.goldPale : 'var(--white)', padding: '18px 12px', textAlign: 'center', marginBottom: 12 }}>
                  <i className="ti ti-cloud-upload" style={{ fontSize: 26, color: COL.textMuted }} />
                  <div style={{ fontSize: 'var(--fs-body)', color: COL.textMuted, margin: '6px 0 10px' }}>{t('tech_sheet.import_drop_zone')}</div>
                  <button type="button" onClick={() => importInputRef.current?.click()}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', border: `1px solid ${COL.gold}`, borderRadius: 6, background: 'transparent', color: COL.gold, fontFamily: FONT, fontSize: 'var(--fs-body)', fontWeight: 600, cursor: 'pointer' }}>
                    <i className="ti ti-file-upload" /> {t('tech_sheet.import_choose_file')}
                  </button>
                  {importFile && (
                    <div style={{ marginTop: 10, fontSize: 'var(--fs-label)', color: COL.textMain, fontWeight: 600, wordBreak: 'break-all' }}>
                      <i className="ti ti-file-check" style={{ marginRight: 4, color: COL.gold }} />{importFile.name}
                    </div>
                  )}
                  <div style={{ marginTop: 10, fontSize: 'var(--fs-caption)', color: COL.textMuted, letterSpacing: '0.04em' }}>
                    {importMode === 'image' ? 'JPG · PNG · GIF' : 'SVG · DXF'}
                  </div>
                </div>

                {/* input ocult del panell (selecciona, no insereix fins a "Inserir") */}
                <input ref={importInputRef} type="file" hidden
                  accept={importMode === 'image' ? 'image/*' : '.svg,.dxf,image/svg+xml'}
                  onChange={e => { const f = e.target.files[0]; e.target.value = ''; onImportPick(f) }} />

                {/* Accions */}
                <div style={{ display: 'flex', gap: 8 }}>
                  <button type="button" onClick={handleImportInsert} disabled={!importFile}
                    style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '8px', border: 'none', borderRadius: 6, background: COL.gold, color: 'var(--white)', fontFamily: FONT, fontSize: 'var(--fs-body)', fontWeight: 600, cursor: importFile ? 'pointer' : 'default', opacity: importFile ? 1 : 0.45 }}>
                    <i className="ti ti-check" /> {t('tech_sheet.import_btn_insert')}
                  </button>
                  <button type="button" onClick={closeImport}
                    style={{ flex: 1, padding: '8px', border: `1px solid ${COL.border}`, borderRadius: 6, background: 'transparent', color: COL.textMain, fontFamily: FONT, fontSize: 'var(--fs-body)', cursor: 'pointer' }}>
                    {t('app.cancel')}
                  </button>
                </div>
              </div>
            </div>
          )}
          {!importMode && (<>
          {/* D2: pestanyes del dock. Arquitectura oberta: afegir aquí un futur tab 'components'. */}
          <div style={{ display: 'flex', flexShrink: 0, borderBottom: `1px solid ${COL.border}` }}>
            {/* El tab Camps només existeix en mode plantilla: un xip {camp} dins un document
                normal no té cap significat i el PDF l'imprimiria literalment. */}
            {[{ id: 'properties', icon: 'ti-adjustments', label: t('tech_sheet.dock_properties') }, { id: 'layers', icon: 'ti-stack-2', label: t('tech_sheet.dock_layers') }, ...(templateMode ? [{ id: 'fields', icon: 'ti-forms', label: t('tech_sheet.dock_fields') }] : [])].map(tb => {
              const on = dockTab === tb.id
              return (
                <button key={tb.id} type="button" onClick={() => setDockTab(tb.id)}
                  style={{ flex: 1, padding: '8px 6px', border: 'none', borderBottom: `2px solid ${on ? COL.gold : 'transparent'}`, background: on ? COL.goldPale : 'transparent', color: on ? COL.gold : COL.textMain, fontFamily: FONT, fontSize: 'var(--fs-body)', fontWeight: on ? 700 : 500, cursor: 'pointer' }}>
                  <i className={`ti ${tb.icon}`} style={{ marginRight: 5, fontSize: 14 }} />{tb.label}
                </button>
              )
            })}
          </div>
          {/* padding inferior extra: clearança per als botons flotants de Chrome (IA/cerca) */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 10px 64px' }}>
            {/* TAB CAPES: llista d'objectes de la pàgina (front a dalt) + z-order. */}
            {dockTab === 'layers' && (ordered.length === 0 ? (
              <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, margin: '0 0 8px' }}>{t('tech_sheet.layers_empty')}</p>
            ) : (
              <div style={{ marginBottom: 8, border: `1px solid ${COL.border}`, borderRadius: 5, overflow: 'hidden' }}>
                {[...ordered].reverse().map(o => {
                  const on = selectedIds.includes(o.id)
                  const icon = { text: 'ti-cursor-text', rect: 'ti-square', ellipse: 'ti-circle', line: 'ti-minus', arrow: 'ti-arrow-right', image: 'ti-photo', path: 'ti-vector', sketch_svg: 'ti-vector', pattern_piece: 'ti-shirt', data_block: 'ti-table', group: 'ti-box-multiple', field: 'ti-forms' }[o.type] || 'ti-shape'
                  const label = o.type === 'text' ? (o.text || t('tech_sheet.tool_text')) : o.type === 'field' ? (o.label || o.type) : o.type === 'pattern_piece' ? (o.piece_name || o.type) : o.type
                  return (
                    <div key={o.id} onClick={() => selectOnly(o.id)}
                      style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 6px', cursor: 'pointer', background: on ? COL.goldPale : 'transparent', color: on ? COL.gold : COL.textMain, borderBottom: `1px solid ${COL.border}`, opacity: o.visible === false ? 0.45 : 1 }}>
                      <i className={`ti ${icon}`} style={{ fontSize: 13, flexShrink: 0 }} />
                      <span style={{ flex: 1, fontSize: 'var(--fs-label)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</span>
                      {locked && o.layer === 'free' && (
                        <>
                          <button onClick={(e) => { e.stopPropagation(); toggleVisible(o.id) }}
                            title={o.visible === false ? t('tech_sheet.layer_show') : t('tech_sheet.layer_hide')}
                            style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', padding: 0, lineHeight: 1 }}><i className={`ti ${o.visible === false ? 'ti-eye-off' : 'ti-eye'}`} style={{ fontSize: 13 }} /></button>
                          <button onClick={(e) => { e.stopPropagation(); toggleLock(o.id) }}
                            title={o.locked === true ? t('tech_sheet.layer_unlock') : t('tech_sheet.layer_lock')}
                            style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', padding: 0, lineHeight: 1 }}><i className={`ti ${o.locked === true ? 'ti-lock' : 'ti-lock-open'}`} style={{ fontSize: 13 }} /></button>
                          <button disabled={nodeMode} onClick={(e) => { e.stopPropagation(); selectOnly(o.id); moveSelectionInFreeLayer('forward', [o.id]) }} title={nodeMode ? t('tech_sheet.obj_action_node_mode') : t('tech_sheet.bring_forward')}
                            style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', padding: 0, lineHeight: 1 }}><i className="ti ti-arrow-up" style={{ fontSize: 13 }} /></button>
                          <button disabled={nodeMode} onClick={(e) => { e.stopPropagation(); selectOnly(o.id); moveSelectionInFreeLayer('backward', [o.id]) }} title={nodeMode ? t('tech_sheet.obj_action_node_mode') : t('tech_sheet.send_backward')}
                            style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', padding: 0, lineHeight: 1 }}><i className="ti ti-arrow-down" style={{ fontSize: 13 }} /></button>
                        </>
                      )}
                    </div>
                  )
                })}
              </div>
            ))}

            {/* input SVG sempre muntat: el referencien el ribbon (Inserir) i el panell de selecció */}
            <input ref={flatFileRef} type="file" accept=".svg,image/svg+xml" hidden
              onChange={e => { const f = e.target.files[0]; e.target.value = ''; handleFlatSvgFile(f) }} />

            {/* CONTENIDOR DE POMS. Calca la fila del Taller de Patró (ModelPomList): semàfor
                de borderLeft, codi de client en mono manant, nom canònic EN al costat, badge
                amb el nom_fitxa. Ve plegat per defecte perquè el dock és per a propietats;
                s'obre quan toca acotar. Un clic arma l'eina de cota amb el text ja resolt. */}
            {dockTab === 'properties' && locked && pomRows.length > 0 && (
              <Contenidor
                titol={t('tech_sheet.poms_of_model', { n: pomRows.length })}
                icona="ti-ruler-measure" defaultOpen={false} fitContent
              >
                <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, margin: '0 0 6px' }}>{t('tech_sheet.poms_hint')}</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {pomRows.map(bm => {
                    const etiqueta = bm.nom_fitxa || bm.pom_abbreviation || bm.codi_client || ''
                    const colocat = !!etiqueta && cotesColocades.has(etiqueta)
                    const armat = cotaPreset?.text === etiqueta && tool === 'cota_pom'
                    return (
                      <button key={bm.id} type="button"
                        onClick={() => { setCotaPreset({ text: etiqueta }); setTool('cota_pom') }}
                        aria-pressed={armat}
                        title={t('tech_sheet.pom_cota_hint', { nom: etiqueta })}
                        style={{
                          textAlign: 'left', width: '100%', cursor: 'pointer',
                          background: armat ? 'var(--gold-pale)' : 'var(--bg-card)',
                          border: `1px solid ${armat ? COL.gold : COL.border}`,
                          borderLeft: `3px solid ${colocat ? COL.ok : armat ? COL.gold : COL.border}`,
                          borderRadius: 4, padding: '0.3rem 0.5rem',
                          display: 'flex', alignItems: 'center', gap: '0.4rem',
                          fontFamily: FONT,
                        }}>
                        <i className={`ti ${colocat ? 'ti-circle-check' : armat ? 'ti-crosshair' : 'ti-circle-dashed'}`}
                          style={{ color: colocat ? COL.ok : armat ? COL.gold : COL.textMuted, flexShrink: 0, fontSize: 14 }} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.3rem', fontSize: 'var(--fs-body)', fontWeight: 600 }}>
                            <span>{bm.codi_client}</span>
                            <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              <PomNamePair en={bm.nom_en} local={bm.nom_ca || bm.nom_client} />
                            </span>
                            {bm.nom_fitxa && (
                              <span style={{ fontSize: 'var(--fs-caption)', fontWeight: 400, color: COL.textMuted, border: `1px solid ${COL.border}`, borderRadius: 8, padding: '0 5px', flexShrink: 0 }}>
                                {bm.nom_fitxa}
                              </span>
                            )}
                          </div>
                        </div>
                        {/* La xifra no es tenyeix mai: el color el porta el semàfor de l'esquerra. */}
                        {bm.base_value_cm != null && (
                          <span style={{ fontSize: 'var(--fs-label)', color: COL.textMain, flexShrink: 0 }}>{bm.base_value_cm}</span>
                        )}
                      </button>
                    )
                  })}
                </div>
              </Contenidor>
            )}
            {/* TAB PROPIETATS: propietats de la selecció (W/H/X/Y, stroke/fill, …). Els blocs
                d'inserció i de fitxers del model viuen ara al ribbon (pestanya Inserir). */}
            {dockTab === 'properties' && !multiSelected && !selObj && (
              <>
                <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted }}>{t('tech_sheet.dock_no_selection')}</p>
                {tool === 'polygon' && (
                  <label style={propLabel}>{t('tech_sheet.polygon_sides')}
                    <input type="number" min={3} max={20} value={polygonSides}
                      onChange={e => setPolygonSides(Math.max(3, Math.min(20, parseInt(e.target.value, 10) || 6)))}
                      style={propInput} />
                  </label>
                )}
              </>
            )}
            {dockTab === 'properties' && multiSelected && locked && (
              <>
                <SectionTitle>{t('tech_sheet.selected_objects', { n: selectedObjects.length })}</SectionTitle>
                {multiStroke.length > 0 && (
                  <div style={propLabel}>{t('tech_sheet.stroke_color')}
                    {!multiStrokeValue && <span style={{ display: 'block', color: COL.textMuted, marginTop: 2 }}>{t('tech_sheet.mixed_values')}</span>}
                    <ColorPicker docColors={docPalette} value={multiStrokeValue || KONVA_COL.textMain}
                      onChange={c => updateObjects(multiStroke.map(o => o.id), o => ({ stroke: c, ...(o.type === 'arrow' ? { fill: c } : {}) }))} />
                  </div>
                )}
                {multiFill.length > 0 && (
                  <div style={propLabel}>{t('tech_sheet.fill')}
                    {!multiFillValue && <span style={{ display: 'block', color: COL.textMuted, marginTop: 2 }}>{t('tech_sheet.mixed_values')}</span>}
                    <ColorPicker docColors={docPalette} value={multiFillValue || KONVA_COL.white}
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
            {dockTab === 'properties' && selObj && locked && (
              <>
                <SectionTitle>{t('tech_sheet.element')} · {selObj.type}</SectionTitle>
                {selDim && (
                  <Contenidor titol={t('tech_sheet.dimensions_position')} icona="ti-ruler-2" fitContent>
                    <BlocEnPausa pausa={panelLockedForEdit} motiu={t('tech_sheet.panel_paused_editing')}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', marginBottom: 6 }}>
                      <button type="button" onClick={() => setRatioLocked(v => !v)} title={t('tech_sheet.keep_ratio')}
                        style={{ width: 24, height: 22, border: `1px solid ${ratioLocked ? COL.gold : COL.border}`, borderRadius: 4, background: ratioLocked ? COL.goldPale : COL.field, color: ratioLocked ? COL.gold : COL.textMuted, cursor: 'pointer' }}>
                        <i className={`ti ${ratioLocked ? 'ti-lock' : 'ti-lock-open'}`} aria-hidden="true" />
                      </button>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                      <label style={propLabel}>W
                        <input type="number" min={0.1} step={1} disabled={!selDim.canResize}
                          value={selDim.canResize ? Math.round(selDim.width * 10) / 10 : ''}
                          placeholder="—"
                          onChange={e => resizeObjectAxis(selObj, 'width', e.target.value)} style={propInput} />
                      </label>
                      <label style={propLabel}>H
                        <input type="number" min={0.1} step={1} disabled={!selDim.canResize}
                          value={selDim.canResize ? Math.round(selDim.height * 10) / 10 : ''}
                          placeholder="—"
                          onChange={e => resizeObjectAxis(selObj, 'height', e.target.value)} style={propInput} />
                      </label>
                      <label style={propLabel}>{t('tech_sheet.pos_x')}
                        <input type="number" step={1} value={Math.round(selDim.x * 10) / 10}
                          onChange={e => moveObjectTo(selObj, 'x', e.target.value)} style={propInput} />
                      </label>
                      <label style={propLabel}>{t('tech_sheet.pos_y')}
                        <input type="number" step={1} value={Math.round(selDim.y * 10) / 10}
                          onChange={e => moveObjectTo(selObj, 'y', e.target.value)} style={propInput} />
                      </label>
                    </div>
                    </BlocEnPausa>
                  </Contenidor>
                )}
                {textObj && (() => {
                  // Peça 3 / A3: tipografia completa. Opera sobre textObj (pot ser el fill 'text'
                  // d'un grup, cas cota) via updateText, que enruta a updateChild o updateObject.
                  const fstyle = textObj.fontStyle || 'normal'
                  const isBold = fstyle.includes('bold')
                  const isItalic = fstyle.includes('italic')
                  const isUnderline = (textObj.textDecoration || '').includes('underline')
                  const align = textObj.align || 'left'
                  const hasBg = !!textObj.bgFill
                  const setStyle = (bold, italic) => updateText({ fontStyle: [bold && 'bold', italic && 'italic'].filter(Boolean).join(' ') || 'normal' })
                  const tbtn = (on) => ({ flex: 1, height: 28, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${on ? COL.gold : COL.border}`, borderRadius: 5, background: on ? COL.goldPale : COL.field, color: on ? COL.gold : COL.textMain, cursor: 'pointer', fontFamily: FONT, fontSize: 'var(--fs-body)' })
                  return (
                    <Contenidor titol={t('tech_sheet.sec_typography')} icona="ti-typography" fitContent>
                      {textGroupId && <div style={{ fontSize: 'var(--fs-label)', color: COL.gold, marginBottom: 4 }}>{t('tech_sheet.group_text')}</div>}
                      {/* Fix #2: contingut del text editable des del panell (via updateText → història). */}
                      <label style={propLabel}>{t('tech_sheet.group_text_content')}
                        <textarea value={textObj.text || ''} onChange={e => updateText({ text: e.target.value })}
                          rows={2} style={{ ...propInput, resize: 'vertical', minHeight: 44 }} />
                      </label>
                      <label style={propLabel}>{t('tech_sheet.font_family')}
                        <select value={textObj.fontFamily || FONT} onChange={e => updateText({ fontFamily: e.target.value })} style={propInput}>
                          {FONT_OPTIONS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
                        </select>
                      </label>
                      <label style={propLabel}>{t('tech_sheet.font_size')}
                        <input type="number" min={6} max={48} value={textObj.fontSize || 11}
                          onChange={e => updateText({ fontSize: Number(e.target.value) || 11 })} style={propInput} />
                      </label>
                      <div style={propLabel}>{t('tech_sheet.font_style')}
                        <div style={{ display: 'flex', gap: 4, marginTop: 3 }}>
                          <button type="button" title={t('tech_sheet.bold')} onClick={() => setStyle(!isBold, isItalic)} style={{ ...tbtn(isBold), fontWeight: 700 }}>B</button>
                          <button type="button" title={t('tech_sheet.italic')} onClick={() => setStyle(isBold, !isItalic)} style={{ ...tbtn(isItalic), fontStyle: 'italic' }}>I</button>
                          <button type="button" title={t('tech_sheet.underline')} onClick={() => updateText({ textDecoration: isUnderline ? '' : 'underline' })} style={{ ...tbtn(isUnderline), textDecoration: 'underline' }}>U</button>
                        </div>
                      </div>
                      <div style={propLabel}>{t('tech_sheet.text_align')}
                        <div style={{ display: 'flex', gap: 4, marginTop: 3 }}>
                          <button type="button" title={t('tech_sheet.align_left')} onClick={() => updateText({ align: 'left' })} style={tbtn(align === 'left')}><i className="ti ti-align-left" /></button>
                          <button type="button" title={t('tech_sheet.align_center')} onClick={() => updateText({ align: 'center' })} style={tbtn(align === 'center')}><i className="ti ti-align-center" /></button>
                          <button type="button" title={t('tech_sheet.align_right')} onClick={() => updateText({ align: 'right' })} style={tbtn(align === 'right')}><i className="ti ti-align-right" /></button>
                        </div>
                      </div>
                      <div style={propLabel}>{t('tech_sheet.text_color')}
                        <ColorPicker docColors={docPalette} value={textObj.fill || KONVA_COL.textMain} onChange={c => updateText({ fill: c })} />
                      </div>
                      {/* A3(d): fons blanc darrere el text (tapa la línia de la cota) + color de fons. */}
                      <div style={propLabel}>{t('tech_sheet.text_bg')}
                        <div style={{ display: 'flex', gap: 4, marginTop: 3 }}>
                          <button type="button" title={t('tech_sheet.text_bg')}
                            onClick={() => updateText(hasBg ? { bgFill: null } : { bgFill: KONVA_COL.white, bgPadding: textObj.bgPadding || 3 })}
                            style={tbtn(hasBg)}><i className="ti ti-square-rounded" /></button>
                        </div>
                      </div>
                      {hasBg && (
                        <div style={propLabel}>{t('tech_sheet.text_bg_color')}
                          <ColorPicker docColors={docPalette} value={textObj.bgFill && textObj.bgFill !== 'transparent' ? textObj.bgFill : KONVA_COL.white}
                            onChange={c => updateText({ bgFill: c })} />
                        </div>
                      )}
                    </Contenidor>
                  )
                })()}
                {/* Fix #3: un sol bloc de traç/puntes que apunta a shapeObj — l'objecte de nivell
                    superior o el fill arrow/path d'un grup (cota) — i muta via updateShape. */}
                {shapeObj && (
                  <Contenidor titol={t('tech_sheet.sec_stroke')} icona="ti-line" fitContent>
                    <BlocEnPausa pausa={panelLockedForEdit} motiu={t('tech_sheet.panel_paused_editing')}>
                    {shapeObj.type === 'path' && subActive != null && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-label)', color: COL.gold, marginBottom: 4 }}>
                        <span>{t('tech_sheet.subpath_active', { n: subActive + 1 })}</span>
                        <button type="button" onClick={() => setActiveSubpath(null)}
                          style={{ border: `1px solid ${COL.border}`, borderRadius: 5, background: COL.field, color: COL.textMain, fontFamily: FONT, fontSize: 'var(--fs-label)', padding: '2px 6px', cursor: 'pointer' }}>
                          {t('tech_sheet.subpath_whole')}
                        </button>
                      </div>
                    )}
                    {/* S2.3 — accions de topologia de la subpath activa (descobribilitat per botó) */}
                    {shapeObj.type === 'path' && subActive != null && (
                      <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
                        <button type="button" onClick={toggleActiveSubpathClosed} title={t('tech_sheet.subpath_toggle_closed')}
                          style={miniBtn}><i className="ti ti-link" style={{ fontSize: 14 }} /></button>
                        <button type="button" onClick={extractActiveSubpath} disabled={(shapeObj.paths?.length || 0) <= 1}
                          title={t('tech_sheet.subpath_extract')} style={miniBtn}><i className="ti ti-arrows-split" style={{ fontSize: 14 }} /></button>
                        <button type="button" onClick={deleteActiveSubpath} title={t('tech_sheet.subpath_delete')}
                          style={{ ...miniBtn, color: 'var(--grana)' }}><i className="ti ti-trash" style={{ fontSize: 14 }} /></button>
                      </div>
                    )}
                    {shapeGroupId && <div style={{ fontSize: 'var(--fs-label)', color: COL.gold, marginBottom: 4 }}>{t('tech_sheet.group_shape')}</div>}
                    <div style={propLabel}>{t('tech_sheet.stroke_color')}
                      <ColorPicker
                        value={subActive != null ? (shapeObj.paths[subActive]?.stroke || shapeObj.stroke || KONVA_COL.textMain) : (shapeObj.stroke || KONVA_COL.textMain)}
                        onChange={c => subActive != null
                          ? updateShape({ paths: shapeObj.paths.map((p, i) => i === subActive ? { ...p, stroke: c } : p) })
                          : updateShape({ stroke: c, ...(shapeObj.type === 'arrow' ? { fill: c } : {}) })} />
                    </div>
                    <label style={propLabel}>{t('tech_sheet.stroke_width')}
                      <input type="number" min={0.5} max={5} step={0.5} value={shapeObj.strokeWidth || (shapeObj.type === 'arrow' ? 1.5 : 1)}
                        onChange={e => updateShape({ strokeWidth: Number(e.target.value) || 1 })} style={propInput} />
                    </label>
                    {/* COMMIT 4: puntes per element (arrow i path). Escriu ambdós camps perquè
                        prevalguin sobre el legacy arrow2 (retrocompat via headConfig). */}
                    {(shapeObj.type === 'arrow' || shapeObj.type === 'path') && (() => {
                      const cfg = headConfig(shapeObj)
                      const hbtn = (on) => ({ flex: 1, height: 28, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${on ? COL.gold : COL.border}`, borderRadius: 5, background: on ? COL.goldPale : COL.field, color: on ? COL.gold : COL.textMain, cursor: 'pointer', fontFamily: FONT, fontSize: 'var(--fs-body)' })
                      return (
                        <div style={propLabel}>{t('tech_sheet.arrow_heads')}
                          <div style={{ display: 'flex', gap: 4, marginTop: 3 }}>
                            <button type="button" title={t('tech_sheet.head_start')} onClick={() => updateShape({ headStart: !cfg.start, headEnd: cfg.end })} style={hbtn(cfg.start)}><i className="ti ti-arrow-narrow-left" /></button>
                            <button type="button" title={t('tech_sheet.head_end')} onClick={() => updateShape({ headStart: cfg.start, headEnd: !cfg.end })} style={hbtn(cfg.end)}><i className="ti ti-arrow-narrow-right" /></button>
                          </div>
                        </div>
                      )
                    })()}
                    </BlocEnPausa>
                  </Contenidor>
                )}
                {(selObj.type === 'rect' || selObj.type === 'ellipse' || selObj.type === 'path') && (
                  <Contenidor titol={t('tech_sheet.sec_fill')} icona="ti-color-swatch" fitContent>
                    <BlocEnPausa pausa={panelLockedForEdit} motiu={t('tech_sheet.panel_paused_editing')}>
                    <div style={propLabel}>{t('tech_sheet.fill')}
                      <ColorPicker
                        value={subActive != null ? (selObj.paths[subActive]?.fill || selObj.fill || KONVA_COL.white) : (selObj.fill && selObj.fill !== 'transparent' ? selObj.fill : KONVA_COL.white)}
                        onChange={c => subActive != null
                          ? updateObject(selObj.id, { paths: selObj.paths.map((p, i) => i === subActive ? { ...p, fill: c } : p) })
                          : updateObject(selObj.id, { fill: c })} />
                    </div>
                    </BlocEnPausa>
                  </Contenidor>
                )}
                {selObj.type === 'data_block' && (
                  <label style={propLabel}>{t('tech_sheet.scale_pct')}
                    <input type="number" min={10} max={200} step={5} value={Math.round((selObj.scale || 1) * 100)}
                      onChange={e => updateObject(selObj.id, { scale: Math.max(0.1, (Number(e.target.value) || 100) / 100) })} style={propInput} />
                  </label>
                )}
                {selObj.type === 'table' && (selObj.kind === 'bom' || selObj.kind === 'custom') && (() => {
                  // T2/personalitzada: EDITABLES a mà (llei: T1a/T1b congelades, aquestes no).
                  const tblBtn = (disabled) => ({ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 'var(--fs-label)', padding: '4px 7px', border: `1px solid ${COL.border}`, borderRadius: 5, background: COL.field, color: COL.textMain, fontFamily: FONT, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.4 : 1 })
                  const cellInput = { ...propInput, marginTop: 0, flex: 1, minWidth: 0, fontSize: 'var(--fs-label)' }
                  return (
                    <>
                      <SectionTitle>{t('tech_sheet.table_edit')}</SectionTitle>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 6 }}>
                        {selObj.columns.map((c, i) => (
                          <input key={c.key} type="text" value={c.label}
                            onChange={e => updateObject(selObj.id, { columns: selObj.columns.map((cc, k) => k === i ? { ...cc, label: e.target.value } : cc) })}
                            style={{ ...cellInput, fontWeight: 600 }} />
                        ))}
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 8 }}>
                        {selObj.rows.map((row, r) => (
                          <div key={r} style={{ display: 'flex', gap: 4 }}>
                            {row.map((cell, ci) => (
                              <input key={ci} type="text" value={String(cell ?? '')}
                                onChange={e => updateObject(selObj.id, { rows: selObj.rows.map((rr, rk) => rk === r ? rr.map((cc, ck) => ck === ci ? e.target.value : cc) : rr) })}
                                style={cellInput} />
                            ))}
                          </div>
                        ))}
                      </div>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        <button type="button" onClick={() => updateObject(selObj.id, { rows: [...selObj.rows, selObj.columns.map(() => '')] })} style={tblBtn(false)}>
                          <i className="ti ti-plus" aria-hidden="true" />{t('tech_sheet.table_add_row')}
                        </button>
                        <button type="button" onClick={() => {
                            const len = selObj.columns.length
                            updateObject(selObj.id, {
                              columns: [...selObj.columns, { key: 'c' + len, label: t('tech_sheet.tbl_col_default', { n: len + 1 }), width: 28 }],
                              rows: selObj.rows.map(row => [...row, '']),
                            })
                          }} style={tblBtn(false)}>
                          <i className="ti ti-plus" aria-hidden="true" />{t('tech_sheet.table_add_col')}
                        </button>
                        <button type="button" disabled={selObj.rows.length <= 1}
                          onClick={() => selObj.rows.length > 1 && updateObject(selObj.id, { rows: selObj.rows.slice(0, -1) })}
                          style={tblBtn(selObj.rows.length <= 1)}>
                          <i className="ti ti-minus" aria-hidden="true" />{t('tech_sheet.table_del_row')}
                        </button>
                        <button type="button" disabled={selObj.columns.length <= 1}
                          onClick={() => selObj.columns.length > 1 && updateObject(selObj.id, { columns: selObj.columns.slice(0, -1), rows: selObj.rows.map(row => row.slice(0, -1)) })}
                          style={tblBtn(selObj.columns.length <= 1)}>
                          <i className="ti ti-minus" aria-hidden="true" />{t('tech_sheet.table_del_col')}
                        </button>
                      </div>
                    </>
                  )
                })()}
                {/* `groupPathChild` afegeix el cas de la cota de POM: la fletxa és un path
                    dins un grup i s'ha de poder corbar sense desagrupar res. */}
                {(selObj.type === 'sketch_svg' || selObj.type === 'path' || groupPathChild) && (
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
                {!blocksTransform(rotObj) && (
                  <Contenidor titol={t('tech_sheet.sec_rotation')} icona="ti-rotate" fitContent>
                    <BlocEnPausa pausa={panelLockedForEdit} motiu={t('tech_sheet.panel_paused_editing')}>
                    {rotChildId && <div style={{ fontSize: 'var(--fs-label)', color: COL.gold, marginBottom: 4 }}>{t('tech_sheet.rotation_of_child')}</div>}
                    <label style={propLabel}>{t('tech_sheet.rotation_deg')}
                      <input type="number" min={0} max={360} step={1} value={Math.round(rotObj.rotation || 0)}
                        onChange={e => updateRotation(((Number(e.target.value) || 0) % 360 + 360) % 360)} style={propInput} />
                    </label>
                    </BlocEnPausa>
                  </Contenidor>
                )}
                {(selObj.layer === 'free' || selObj.type === 'data_block') && (
                  // Coherència d'abast: amb una selecció fina viva (forma, node o segment), el
                  // botó d'esborrar ELEMENT no pot estar clicable — el que la mà toca és una part
                  // de l'objecte, no l'objecte. Es diu per què (tooltip), no s'amaga.
                  <button onClick={() => deleteObject(selObj.id)} disabled={nodeMode}
                    title={nodeMode ? t('tech_sheet.obj_action_node_mode') : ''}
                    style={{ width: '100%', fontSize: 'var(--fs-body)', padding: '5px 8px', marginTop: 6, border: `1px solid var(--grana)`, borderRadius: 5, background: 'transparent', color: 'var(--grana)', fontFamily: FONT, cursor: nodeMode ? 'not-allowed' : 'pointer', opacity: nodeMode ? 0.4 : 1 }}>
                    <i className="ti ti-trash" style={{ fontSize: 12, marginRight: 5 }} />{t('app.delete')}
                  </button>
                )}
              </>
            )}
            {/* TAB CAMPS (S5-1): catàleg clicable → insereix un xip {label} a (20,20)mm.
                Es resol server-side en instanciar un document des de la plantilla. */}
            {dockTab === 'fields' && locked && templateMode && (
              <>
                <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, margin: '0 0 8px' }}>{t('tech_sheet.fields_hint')}</p>
                <div style={{ border: `1px solid ${COL.border}`, borderRadius: 5, overflow: 'hidden' }}>
                  {FIELD_CATALOG.map(f => (
                    <button key={f.key} type="button"
                      onClick={() => addObject({ id: uid(), type: 'field', key: f.key, label: t('tech_sheet.' + f.tk), layer: 'free', x: 20, y: 20, style: { fontSize: 11 } })}
                      style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%', padding: '6px 8px', border: 'none', borderBottom: `1px solid ${COL.border}`, background: 'transparent', color: COL.textMain, fontFamily: FONT, fontSize: 'var(--fs-label)', textAlign: 'left', cursor: 'pointer' }}>
                      <i className="ti ti-forms" style={{ fontSize: 13, color: COL.gold, flexShrink: 0 }} />
                      <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t('tech_sheet.' + f.tk)}</span>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
          </>)}
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

      {/* ── Menú contextual del bloc capçalera mestra ancorat (B3) ── */}
      {headerMenu && (<>
        <div onClick={() => setHeaderMenu(null)} onContextMenu={(e) => { e.preventDefault(); setHeaderMenu(null) }} style={{ position: 'fixed', inset: 0, zIndex: 998 }} />
        <div style={{ position: 'fixed', left: headerMenu.x, top: headerMenu.y, zIndex: 999, background: 'var(--white)', border: `1px solid ${COL.border}`, borderRadius: 6, boxShadow: '0 4px 16px rgba(0,0,0,0.15)', padding: 4, minWidth: 190, fontFamily: FONT }}>
          {/* "Desvincular" ha marxat: el gest per obrir la capçalera és ara Desagrupar (B2), que
              a més la materialitza de veritat en lloc de canviar-li tres flags. */}
          {[{ ic: 'ti-square-off', tk: 'header_delete_on_page', fn: () => deleteHeaderOnPage(currentPage) }].map(mi => (
            <button key={mi.tk} type="button" onClick={() => { mi.fn(); setHeaderMenu(null) }}
              style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '7px 10px', border: 'none', background: 'transparent', color: COL.textMain, fontFamily: FONT, fontSize: 'var(--fs-label)', textAlign: 'left', cursor: 'pointer', borderRadius: 4 }}
              onMouseEnter={(e) => { e.currentTarget.style.background = COL.bg }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}>
              <i className={`ti ${mi.ic}`} style={{ fontSize: 14, color: COL.gold, flexShrink: 0 }} />
              <span>{t('tech_sheet.' + mi.tk)}</span>
            </button>
          ))}
        </div>
      </>)}

      {/* ── Barra d'estat inferior (C3) ── */}
      <footer style={{ flexShrink: 0, background: COL.sidebar, borderTop: `1px solid ${COL.border}`, display: 'flex', alignItems: 'center', gap: 12, padding: '4px 12px', color: COL.textMuted, fontSize: 'var(--fs-label)' }}>
        <span style={{ fontWeight: 500, padding: '2px 8px', borderRadius: 10, background: badge.bg, color: badge.fg, whiteSpace: 'nowrap' }}>
          v{sheet?.versio ?? 1} · {badge.text}
        </span>
        {/* D10 — sense task_id l'editor desa igual però NO imputa temps (guard a :1862). Fins ara
            era silenciós; ara es fa visible. NO bloqueja cap acció d'edició. */}
        {!taskId && (
          <span title={t('tech_sheet.consultation_hint')}
            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 8px', borderRadius: 10,
                     border: `1px solid ${COL.border}`, color: COL.textMuted, whiteSpace: 'nowrap' }}>
            <i className="ti ti-clock-off" aria-hidden="true" style={{ fontSize: 12 }} />
            {t('tech_sheet.consultation_badge')}
          </span>
        )}
        {saveLabel && <span>{saveLabel}</span>}
        {notice && <span style={{ color: 'var(--warn)', background: 'var(--gold-pale)', border: `1px solid ${COL.gold}`, padding: '2px 8px', borderRadius: 5 }}>{notice}</span>}
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

      {/* S3: picker de variant de taula (T1a/T1b/T2/personalitzada) + sub-selector de size
          fitting (T1a/T1b) o de mida (personalitzada). Mateix look que el modal pickFitting
          de dalt. Obert des del ribbon (botó "Taula", commit 4); T1a/T1b es deshabiliten
          sense size-fittings, T2/Custom sempre disponibles. */}
      {/* F1 — selector de peces del patró vigent. La peça hi entra encaixada; el nom del
          block és el que en dirà el peu i el panell de capes. */}
      {piecePicker && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }} onClick={() => setPiecePicker(null)}>
          <div onClick={e => e.stopPropagation()} style={{ background: COL.bg, borderRadius: 12, padding: '1.4rem', maxWidth: 380, width: '90%', maxHeight: '70vh', overflowY: 'auto', fontFamily: FONT, border: `1px solid ${COL.border}` }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 4 }}>{t('tech_sheet.piece_picker_title')}</h2>
            <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, marginBottom: 12 }}>{patternFile?.nom_fitxer}</p>
            {piecePicker.loading && <p style={{ fontSize: 'var(--fs-body)', color: COL.textMuted }}>{t('app.loading')}</p>}
            {piecePicker.error && <p style={{ fontSize: 'var(--fs-body)', color: COL.textMuted }}>{t('tech_sheet.piece_insert_error')}</p>}
            {piecePicker.pieces && !piecePicker.pieces.length && (
              <p style={{ fontSize: 'var(--fs-body)', color: COL.textMuted }}>{t('tech_sheet.piece_none')}</p>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {(piecePicker.pieces || []).map(p => (
                <button key={p.id} type="button" onClick={() => inserirPeca(p)}
                  style={{ textAlign: 'left', fontSize: 'var(--fs-body)', padding: '8px 10px', border: `1px solid ${COL.border}`, borderRadius: 6, background: COL.field, color: COL.textMain, fontFamily: FONT, cursor: 'pointer' }}>
                  {p.nom_block}
                  {p.bounding_box_mm && (
                    <div style={{ fontSize: 'var(--fs-label)', color: COL.textMuted }}>
                      {Math.round(p.bounding_box_mm.ample)} × {Math.round(p.bounding_box_mm.alt)} mm
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
      {tablePicker && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }} onClick={() => setTablePicker(null)}>
          <div onClick={e => e.stopPropagation()} style={{ background: COL.bg, borderRadius: 12, padding: '1.4rem', maxWidth: 360, width: '90%', fontFamily: FONT, border: `1px solid ${COL.border}` }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 12 }}>{t('tech_sheet.table_picker_title')}</h2>
            {!tablePicker.variant ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <button type="button" disabled={!sizeFittings.length} onClick={() => onPickTableVariant('t1a')}
                  style={{ textAlign: 'left', fontSize: 'var(--fs-body)', padding: '8px 10px', border: `1px solid ${COL.border}`, borderRadius: 6, background: COL.field, color: COL.textMain, fontFamily: FONT, cursor: sizeFittings.length ? 'pointer' : 'default', opacity: sizeFittings.length ? 1 : 0.5 }}>
                  {t('tech_sheet.table_variant_t1a')}
                </button>
                <button type="button" disabled={!sizeFittings.length} onClick={() => onPickTableVariant('t1b')}
                  style={{ textAlign: 'left', fontSize: 'var(--fs-body)', padding: '8px 10px', border: `1px solid ${COL.border}`, borderRadius: 6, background: COL.field, color: COL.textMain, fontFamily: FONT, cursor: sizeFittings.length ? 'pointer' : 'default', opacity: sizeFittings.length ? 1 : 0.5 }}>
                  {t('tech_sheet.table_variant_t1b')}
                </button>
                <button type="button" onClick={() => onPickTableVariant('t2')}
                  style={{ textAlign: 'left', fontSize: 'var(--fs-body)', padding: '8px 10px', border: `1px solid ${COL.border}`, borderRadius: 6, background: COL.field, color: COL.textMain, fontFamily: FONT, cursor: 'pointer' }}>
                  {t('tech_sheet.table_variant_t2')}
                </button>
                <button type="button" onClick={() => onPickTableVariant('custom')}
                  style={{ textAlign: 'left', fontSize: 'var(--fs-body)', padding: '8px 10px', border: `1px solid ${COL.border}`, borderRadius: 6, background: COL.field, color: COL.textMain, fontFamily: FONT, cursor: 'pointer' }}>
                  {t('tech_sheet.table_variant_custom')}
                </button>
              </div>
            ) : tablePicker.variant === 'custom' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <label style={propLabel}>{t('tech_sheet.table_custom_rows')}
                  <input type="number" min={1} max={20} value={tablePicker.rows}
                    onChange={e => setTablePicker(p => ({ ...p, rows: Math.min(20, Math.max(1, Number(e.target.value) || 1)) }))} style={propInput} />
                </label>
                <label style={propLabel}>{t('tech_sheet.table_custom_cols')}
                  <input type="number" min={1} max={20} value={tablePicker.cols}
                    onChange={e => setTablePicker(p => ({ ...p, cols: Math.min(20, Math.max(1, Number(e.target.value) || 1)) }))} style={propInput} />
                </label>
                <button type="button" onClick={() => insertTableCustom(tablePicker.rows, tablePicker.cols)}
                  style={{ textAlign: 'center', fontSize: 'var(--fs-body)', padding: '8px 10px', border: `1px solid ${COL.gold}`, borderRadius: 6, background: COL.goldPale, color: COL.gold, fontWeight: 600, fontFamily: FONT, cursor: 'pointer' }}>
                  {t('tech_sheet.table_custom_create')}
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, marginBottom: 4 }}>{t('tech_sheet.table_pick_fitting')}</p>
                {sizeFittings.map(sf => (
                  <button key={sf.id} type="button" onClick={() => runTableVariant(tablePicker.variant, sf.id)}
                    style={{ textAlign: 'left', fontSize: 'var(--fs-body)', padding: '8px 10px', border: `1px solid ${COL.border}`, borderRadius: 6, background: COL.field, color: COL.textMain, fontFamily: FONT, cursor: 'pointer' }}>
                    {sf.codi || sf.nom || sf.talla_base || `#${sf.id}`}{sf.tipus ? ` · ${sf.tipus}` : ''}
                  </button>
                ))}
              </div>
            )}
            <button type="button" onClick={() => setTablePicker(null)}
              style={{ marginTop: 12, fontSize: 'var(--fs-label)', color: COL.textMuted, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
              {t('tech_sheet.table_picker_cancel')}
            </button>
          </div>
        </div>
      )}

      {/* S4: modal "Desar com a plantilla" — mateix look que pickFitting/tablePicker */}
      {saveAsTpl && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }} onClick={() => setSaveAsTpl(null)}>
          <div onClick={e => e.stopPropagation()} style={{ background: COL.bg, borderRadius: 12, padding: '1.4rem', maxWidth: 360, width: '90%', fontFamily: FONT, border: `1px solid ${COL.border}` }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 12 }}>{t('tech_sheet.save_as_template')}</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <label style={propLabel}>
                <input type="text" value={saveAsTpl.nom} placeholder={t('tech_sheet.save_as_template_name')}
                  onChange={e => setSaveAsTpl(p => ({ ...p, nom: e.target.value }))} style={propInput} />
              </label>
              <label style={propLabel}>
                <input type="text" value={saveAsTpl.descripcio} placeholder={t('tech_sheet.save_as_template_desc')}
                  onChange={e => setSaveAsTpl(p => ({ ...p, descripcio: e.target.value }))} style={propInput} />
              </label>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 4 }}>
                <button type="button" onClick={() => setSaveAsTpl(null)}
                  style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, background: 'none', border: 'none', cursor: 'pointer', padding: '6px 10px' }}>
                  {t('tech_sheet.table_picker_cancel')}
                </button>
                <button type="button" onClick={submitSaveAsTpl} disabled={!saveAsTpl.nom.trim()}
                  style={{ fontSize: 'var(--fs-body)', padding: '6px 14px', border: `1px solid ${COL.gold}`, borderRadius: 6, background: COL.goldPale, color: COL.gold, fontWeight: 600, fontFamily: FONT, cursor: saveAsTpl.nom.trim() ? 'pointer' : 'default', opacity: saveAsTpl.nom.trim() ? 1 : 0.5 }}>
                  {t('tech_sheet.save_as_template')}
                </button>
              </div>
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
export function ColorPicker({ value, onChange, docColors }) {
  const { t } = useTranslation()
  const isNone = value == null || value === 'transparent' || value === 'none'
  // C3 — la PALETA DEL DOCUMENT va en una fila pròpia, sota els colors ràpids: són els colors
  // que ja s'han fet servir en aquesta fitxa. És el que fa que la segona peça d'un croquis
  // surti del mateix color que la primera sense haver de recordar cap hex.
  const propis = (docColors || []).filter(c => !QUICK_COLORS.includes(c))
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap', marginTop: 3 }}>
      {/* Fix #3-5: swatch "cap color" (transparent) — compartit a traç/emplenat/text/fons/puntes. */}
      <button type="button" onClick={() => onChange('transparent')} title={t('tech_sheet.no_color')}
        style={{ width: 18, height: 18, borderRadius: '50%', background: 'transparent', border: isNone ? `2px solid ${COL.textMain}` : `1px solid ${COL.border}`, cursor: 'pointer', padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: COL.textMuted, fontSize: 12 }}>
        <i className="ti ti-ban" aria-hidden="true" />
      </button>
      {QUICK_COLORS.map(c => (
        <button key={c} type="button" onClick={() => onChange(c)} title={c}
          style={{ width: 18, height: 18, borderRadius: '50%', background: c, border: value === c ? `2px solid ${COL.textMain}` : `1px solid ${COL.border}`, cursor: 'pointer', padding: 0 }} />
      ))}
      <input type="color" value={value || KONVA_COL.textMain} onChange={e => onChange(e.target.value)} title={t('tech_sheet.more_colors')}
        style={{ width: 22, height: 22, border: 'none', borderRadius: 4, cursor: 'pointer', padding: 0, background: 'none' }} />
      {propis.length > 0 && (
        <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap', width: '100%', marginTop: 4, paddingTop: 4, borderTop: `1px solid ${COL.border}` }}>
          <span style={{ fontSize: 'var(--fs-caption)', color: COL.textMuted, width: '100%' }}>{t('tech_sheet.doc_palette')}</span>
          {propis.map(c => (
            <button key={c} type="button" onClick={() => onChange(c)} title={c}
              style={{ width: 18, height: 18, borderRadius: '50%', background: c, border: value === c ? `2px solid ${COL.textMain}` : `1px solid ${COL.border}`, cursor: 'pointer', padding: 0 }} />
          ))}
        </div>
      )}
    </div>
  )
}

// B3 — embolcall que deixa un bloc del panell EN LECTURA mentre el canvas té la mà a la
// mateixa geometria. `fieldset disabled` desactiva d'una tacada inputs, selects i botons de
// dins (ColorPicker inclòs), que és exactament el que cal i sense tocar cap control un per un.
export function BlocEnPausa({ pausa, motiu, children }) {
  if (!pausa) return children
  return (
    <fieldset disabled style={{ border: 'none', margin: 0, padding: 0, minWidth: 0, opacity: 0.45 }}>
      <div style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, marginBottom: 4 }}>{motiu}</div>
      {children}
    </fieldset>
  )
}

export function SectionTitle({ children }) {
  return <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, color: COL.gold, textTransform: 'uppercase', letterSpacing: '0.03em', margin: '12px 0 6px' }}>{children}</div>
}
export const propLabel = { display: 'block', fontSize: 'var(--fs-label)', color: COL.textMuted, marginBottom: 8 }
// S2.3 — botó compacte per a accions de topologia de subpath (icona Tabler outline).
const miniBtn = { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 30, height: 26, border: `1px solid ${COL.border}`, borderRadius: 6, background: COL.field, color: COL.textMuted, cursor: 'pointer' }
// F1 — barra superior contextual del mode edició de nodes: eines + estil de botó.
// G1 — els DOS CURSORS (jerarquia Illustrator), primers del grup: fletxa negra = selecció de FORMA
// (subpath sencer), fletxa blanca = selecció DIRECTA (nodes/segments/nanses, tot el ja construït).
const SHAPE_TOOL_ITEMS = [
  { k: 'shape', icon: 'ti-pointer', label: 'shape_select', sc: 'V' },
  { k: 'select', icon: 'ti-vector-triangle', label: 'direct_select', sc: 'A' },
]
// Sub-eines de la selecció DIRECTA (afegir/treure/convertir node, tisores).
const NODE_TOOL_ITEMS = [
  { k: 'add', icon: 'ti-plus', label: 'node_add', sc: '+' },
  { k: 'remove', icon: 'ti-minus', label: 'node_remove', sc: '-' },
  { k: 'convert', icon: 'ti-vector-bezier-2', label: 'node_convert', sc: 'B' },
  { k: 'scissors', icon: 'ti-scissors', label: 'node_scissors', sc: 'C' },
]
export const propInput = { width: '100%', fontFamily: FONT, fontSize: 'var(--fs-body)', padding: '4px 6px', marginTop: 3, border: `1px solid ${COL.border}`, borderRadius: 6, background: COL.field, color: COL.textMain, boxSizing: 'border-box' }
