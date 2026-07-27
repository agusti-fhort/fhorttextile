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
// X2 — el contracte de pintura d'un `path` (qui mana entre objecte i subpath) viu en un sol
// lloc, perquè el llenç, el PDF i el sub-editor de Paper l'han de llegir IGUAL.
import { normalizePaint, normalizeFillRule, resolStroke, resolFill, resolStrokeWidth, sensePintura } from './ftt/paint'
import { useUnit, fmtMeasure } from './fittingShared'

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
// `pom` = vermell saturat de la COTA DE POM al croquis (traç de la fletxa + text de l'etiqueta). Reusa el
// literal que ja fa servir la columna de nomenclatura de les taules snapshot (TBL.REF, més avall)
// per no introduir un segon vermell al mateix llenç.
// Y2 — SNAP DE ROTACIÓ A 45° AMB SHIFT, el gest d'Illustrator/Figma: sense Shift, l'angle és
// lliure; amb Shift, discret. El Transformer de Konva ja sap ancorar angles (`rotationSnaps`);
// el que no sabia és fer-ho NOMÉS mentre la tecla està premuda, i per això la llista de snaps
// entra i surt amb `shiftHeld` en comptes de posar-s'hi fixa.
// La tolerància és mitja passa i UNA MICA MÉS. Konva compara amb `dif < tol` (estricte), o sigui
// que amb 22,5 clavats els vuit punts mitjos —22,5°, 67,5°…— no ancoraven a res i es quedaven
// lliures enmig d'un gest que l'usuari ha demanat que sigui discret. Comprovat fora del
// navegador replicant `getSnap`: amb 22,5 queden 8 angles lliures; amb 22,5001, cap. L'empat
// exacte del punt mig el resol l'ordre de la llista (guanya l'últim, el de dalt).
const ROT_SNAPS = [0, 45, 90, 135, 180, 225, 270, 315]
const ROT_SNAP_TOL = 22.5001
const SENSE_SNAP = []
const KONVA_COL = { white: '#ffffff', gold: '#c27a2a', goldPale: '#f5e6d0', border: '#e0d5c5', textMain: '#1d1d1b', textMuted: '#868685', labelGray: '#777776', pom: '#dc2626' }

// F1 — la caixa on entra una peça de patró. Una peça és MOLT més gran que la pàgina (el
// TATE_FRONT fa 588×502 mm i un A4 apaïsat en fa 297×210): entra encaixada a aquesta caixa,
// mai a mida real, i des d'aquí es redimensiona a mà com qualsevol imatge.
const PIECE_BOX_W = 110
const PIECE_BOX_H = 78

// La caixa on entra una IMATGE ràster (PNG/JPG) importada, i la del logo lliure. Mateixa
// naturalesa que PIECE_BOX_*: un MÀXIM dins el qual `containBox` encaixa la mida nativa
// preservant-ne la ràtio, no una talla imposada als dos eixos. Els valors són els nominals
// històrics (120×80 i 40×20) per no barrejar el fix de proporció amb un canvi de mida.
const IMG_BOX_W = 120
const IMG_BOX_H = 80
const LOGO_BOX_W = 40
const LOGO_BOX_H = 20

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

// F1 (cota viva) — etiqueta VISIBLE d'un POM a la cota: àlies de client si n'hi ha, si
// no el codi canònic (pom_code_global). El codi canònic sempre queda com a metadada +
// tooltip. Últim fallback a codi_client per no deixar mai l'etiqueta buida en POMs
// tenant-only sense canònic ni àlies.
export const cotaLabelDe = (bm) => (bm && (bm.client_alias || bm.pom_code_global || bm.codi_client)) || ''

// F2 (precedent de col·locació) — objectes del croquis als quals el tècnic assigna una vista
// (viewSlot) i sobre la bbox dels quals es normalitzen les cotes.
export const SKETCH_OBJ_TYPES = ['path', 'image', 'sketch_svg', 'pattern_piece']

// Extrems A→B (i centre d'etiqueta) d'una cota VIVA de F1, en mm de document. null si no ho és.
export function cotaEndsMm(g) {
  if (!g || g.type !== 'group' || g.pomId == null) return null
  const kids = g.children || []
  const linia = kids.find(k => k.type === 'path' || k.type === 'arrow')
  const text = kids.find(k => k.type === 'text')
  if (!linia) return null
  let dx = 0, dy = 0
  if (linia.type === 'path') {
    const segs = (linia.paths && linia.paths[0] && linia.paths[0].segments) || []
    if (segs.length >= 2) { dx = segs[1].x || 0; dy = segs[1].y || 0 }
  } else { dx = (linia.x2 || 0) - (linia.x || 0); dy = (linia.y2 || 0) - (linia.y || 0) }
  const ax = g.x || 0, ay = g.y || 0
  const lc = text
    ? { x: ax + (text.x || 0) + (text.width || 0) / 2, y: ay + (text.y || 0) + (text.height || 0) / 2 }
    : null
  return { ax, ay, bx: ax + dx, by: ay + dy, lc }
}

// C1-fix — l'etiqueta d'una cota MAI solapa el traç: es col·loca desplaçada PERPENDICULARMENT
// del punt mig, del costat superior (horitzontal → a sobre; obliqua → perpendicular amunt) i a la
// DRETA si la cota és vertical (mai girada 90°). El gap és constant en mm de document; `halfW/halfH`
// són les mitges extensions REALS de l'etiqueta (mm) perquè el text quedi net del traç a qualsevol
// angle (una cota vertical necessita netejar l'AMPLADA; una d'horitzontal, l'ALÇADA).
const COTA_LABEL_GAP_MM = 1.5
export const textHalfHeightMm = (fontSize) => toMm((fontSize || 9) * 1.2) / 2
export function cotaLabelOffset(dx, dy, halfW, halfH) {
  const len = Math.hypot(dx, dy) || 1
  let nx = -dy / len, ny = dx / len
  const EPS = 1e-6
  if (ny > EPS || (Math.abs(ny) <= EPS && nx < 0)) { nx = -nx; ny = -ny }
  const dist = COTA_LABEL_GAP_MM + Math.abs(nx) * halfW + Math.abs(ny) * halfH
  return { x: nx * dist, y: ny * dist }
}

// F2 — construeix una cota VIVA (mateixa forma que l'eina cota_pom de F1: grup amb path de
// doble punta + etiqueta de TEXT VERMELL sense requadre) a partir dels extrems en mm. Un precedent
// de peça GERMANA es marca amb traç discontinu (`derivat`).
export function buildLiveCota({ ax, ay, dx, dy, label, pomId, bmId, canonical, viewSlot, derivat }) {
  const col = KONVA_COL.pom
  const dash = derivat ? [3, 2] : undefined
  const TW = measureTextWidthMm({ text: label, fontSize: 9, fontFamily: FONT, fontStyle: 'bold' })
  // C1-fix: posició INICIAL de l'etiqueta = offset perpendicular automàtic (mai sobre el traç).
  const hh = textHalfHeightMm(9)
  const off = cotaLabelOffset(dx, dy, TW / 2, hh)
  const cx = dx / 2 + off.x, cy = dy / 2 + off.y
  const linia = {
    id: uid(), type: 'path', layer: 'free', x: 0, y: 0, headStart: true, headEnd: true,
    stroke: col, fill: null, strokeWidth: 1, dash,
    paths: [{ closed: false, segments: [
      { x: 0, y: 0, inX: 0, inY: 0, outX: 0, outY: 0 },
      { x: dx, y: dy, inX: 0, inY: 0, outX: 0, outY: 0 }], stroke: col, strokeWidth: 1, fill: null }],
  }
  // C2 (Patró C) — text vermell SENSE fons: cap camp per-cota fixa el requadre (l'estil de la
  // cota és de render, no de dades). El color vermell viu al `fill` per coherència amb el traç.
  const text = {
    id: uid(), type: 'text', layer: 'free', x: cx - TW / 2, y: cy - hh, width: TW, height: 10,
    text: label, fontSize: 9, fontFamily: FONT, fill: KONVA_COL.pom, fontStyle: 'bold',
    align: 'center',
  }
  return {
    id: uid(), type: 'group', layer: 'free', x: ax, y: ay, rotation: 0,
    pomId, bmId, pomCanonical: canonical || '', viewSlot, precedentGermana: !!derivat,
    children: [linia, text],
  }
}

// C1 — extrems REALS d'una cota (primer i últim node on-curve de la línia) i centre de
// l'etiqueta, en mm de document. Serveix per pintar les nanses. Un `path` corbat pot tenir >2
// nodes: l'extrem és el primer i l'últim, no segs[1] (cotaEndsMm assumeix recte, per al precedent).
function cotaHandleEnds(g) {
  if (!g || g.type !== 'group' || g.pomId == null) return null
  const kids = g.children || []
  const linia = kids.find(k => k.type === 'path' || k.type === 'arrow')
  const text = kids.find(k => k.type === 'text')
  if (!linia) return null
  const ax = g.x || 0, ay = g.y || 0
  let a, b
  if (linia.type === 'path') {
    const segs = (linia.paths && linia.paths[0] && linia.paths[0].segments) || []
    if (segs.length < 2) return null
    a = { x: ax + (segs[0].x || 0), y: ay + (segs[0].y || 0) }
    b = { x: ax + (segs[segs.length - 1].x || 0), y: ay + (segs[segs.length - 1].y || 0) }
  } else {
    a = { x: ax + (linia.x || 0), y: ay + (linia.y || 0) }
    b = { x: ax + (linia.x2 || 0), y: ay + (linia.y2 || 0) }
  }
  // Centre real de l'etiqueta: mitja alçada REAL del text (no el camp nominal `height`), coherent
  // amb com es col·loca a buildLiveCota/resize/auto-place → la nansa cau sobre el text de debò.
  const lc = text
    ? { x: ax + (text.x || 0) + (text.width || 0) / 2, y: ay + (text.y || 0) + textHalfHeightMm(text.fontSize) }
    : null
  return { a, b, lc }
}

// C1-fix — reposiciona l'etiqueta d'una cota al seu offset perpendicular automàtic (posició
// INICIAL i de re-càlcul). Respecta `labelMoved`: si l'usuari l'ha arrossegada a mà, no la toca.
// Migra les cotes existents (sense flag) en re-renderitzar. Retorna la MATEIXA cota si no cal
// cap canvi (idempotent, perquè l'efecte que la crida no entri en bucle).
function autoPlaceCotaLabel(cota) {
  if (!cota || cota.type !== 'group' || cota.pomId == null || cota.labelMoved) return cota
  const ends = cotaHandleEnds(cota)
  if (!ends) return cota
  const kids = cota.children || []
  const ti = kids.findIndex(k => k.type === 'text')
  if (ti < 0) return cota
  const t = kids[ti]
  const ax = cota.x || 0, ay = cota.y || 0
  const dx = ends.b.x - ends.a.x, dy = ends.b.y - ends.a.y
  const midX = (ends.a.x + ends.b.x) / 2, midY = (ends.a.y + ends.b.y) / 2
  const hw = (t.width || 0) / 2, hh = textHalfHeightMm(t.fontSize)
  const off = cotaLabelOffset(dx, dy, hw, hh)
  const nx = (midX + off.x - ax) - hw, ny = (midY + off.y - ay) - hh
  if (Math.abs((t.x || 0) - nx) < 0.05 && Math.abs((t.y || 0) - ny) < 0.05) return cota
  const nk = kids.slice()
  nk[ti] = { ...t, x: nx, y: ny }
  return { ...cota, children: nk }
}

// C1 — moure UN extrem d'una cota (which='start'|'end') a la posició global (nx,ny) mm, movent
// NOMÉS la geometria de la línia i mai escalant res. Manté l'invariant «origen del grup = extrem
// A» (re-localitza tots els nodes) i reposiciona l'etiqueta al nou punt mig CONSERVANT el seu
// desplaçament manual respecte del centre (el text no es deforma mai). Retorna el patch o null.
function resizeCotaEndpoint(cota, which, nx, ny) {
  const kids = cota.children || []
  const ax = cota.x || 0, ay = cota.y || 0
  const linia = kids.find(k => k.type === 'path' || k.type === 'arrow')
  const text = kids.find(k => k.type === 'text')
  if (!linia) return null
  const isPath = linia.type === 'path'
  // Nodes en GLOBAL (mm) abans de moure.
  let origG
  if (isPath) {
    const segs = (linia.paths && linia.paths[0] && linia.paths[0].segments) || []
    if (segs.length < 2) return null
    origG = segs.map(s => ({ x: ax + (s.x || 0), y: ay + (s.y || 0) }))
  } else {
    origG = [{ x: ax + (linia.x || 0), y: ay + (linia.y || 0) }, { x: ax + (linia.x2 || 0), y: ay + (linia.y2 || 0) }]
  }
  const oldA = origG[0], oldB = origG[origG.length - 1]
  const oldMid = { x: (oldA.x + oldB.x) / 2, y: (oldA.y + oldB.y) / 2 }
  const tw = text ? (text.width || 0) : 0, hh = textHalfHeightMm(text && text.fontSize)
  const oldLc = text
    ? { x: ax + (text.x || 0) + tw / 2, y: ay + (text.y || 0) + hh }
    : oldMid
  // Desplaçament MANUAL a conservar només si l'usuari ha mogut l'etiqueta; si no, es re-col·loca
  // amb l'offset perpendicular automàtic sobre la nova orientació (C1-fix).
  const manualOff = { x: oldLc.x - oldMid.x, y: oldLc.y - oldMid.y }
  // Mou l'extrem triat; l'origen nou és el primer node (invariant).
  const moveIdx = which === 'start' ? 0 : origG.length - 1
  const newG = origG.map((n, i) => (i === moveIdx ? { x: nx, y: ny } : n))
  const origin = newG[0]
  const newA = newG[0], newB = newG[newG.length - 1]
  const newMid = { x: (newA.x + newB.x) / 2, y: (newA.y + newB.y) / 2 }
  const autoOff = cotaLabelOffset(newB.x - newA.x, newB.y - newA.y, tw / 2, hh)
  const off = cota.labelMoved ? manualOff : autoOff
  const newLc = { x: newMid.x + off.x, y: newMid.y + off.y }
  const local = newG.map(n => ({ x: n.x - origin.x, y: n.y - origin.y }))
  const children = kids.map(k => {
    if (k === linia) {
      if (isPath) {
        const segs = k.paths[0].segments
        return { ...k, paths: [{ ...k.paths[0], segments: segs.map((s, i) => ({ ...s, x: local[i].x, y: local[i].y })) }] }
      }
      return { ...k, x: local[0].x, y: local[0].y, x2: local[1].x, y2: local[1].y }
    }
    if (k === text) {
      return { ...k, x: (newLc.x - origin.x) - tw / 2, y: (newLc.y - origin.y) - hh }
    }
    return k
  })
  return { x: origin.x, y: origin.y, children }
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

// Carrega un HTMLImageElement (promesa) — per a l'export offscreen i per llegir la mida
// nativa d'un ràster abans d'encaixar-lo (`containBox`, sota). Exportada perquè
// TechSheetTemplateEditor comparteix el motor i no n'ha de tenir una còpia.
export function loadImageEl(src) {
  return new Promise((res, rej) => {
    const i = new window.Image()
    i.crossOrigin = 'anonymous'
    i.onload = () => res(i)
    i.onerror = () => rej(new Error('img load'))
    i.src = src
  })
}

// Encaixa una mida nativa dins una caixa PRESERVANT-NE la ràtio (contain). La caixa és un
// MÀXIM, no una talla: un sol factor `Math.min` toca un eix i deixa l'altre curt, mai estira
// els dos per separat.
//
// Aquest és l'idioma que els camins VECTORIALS de l'editor ja fan servir —`importFlatSvgText`
// (via `svgAspectRatio`), `inserirPeca` (PIECE_BOX_W×PIECE_BOX_H) i `headerMasterLogoRect`
// (`Math.min(W/natW, H/natH)`)—; el camí RÀSTER era l'únic que no preguntava mai la ràtio i
// clavava la caixa nominal als dos eixos, deformant tot PNG/JPG que no fos exactament 3:2.
// Sense clamp a s<=1: una imatge petita creix fins a tocar la caixa, igual que un SVG petit
// (mateix criteri que `headerMasterLogoRect`, comentari «contain sense clamp»).
//
// Mida natural il·legible (0/NaN) → es retorna la caixa nominal: el comportament d'abans, que
// per a una imatge que no es pot mesurar és l'únic honest.
export function containBox(natW, natH, maxW, maxH) {
  if (!(natW > 0) || !(natH > 0)) return { width: maxW, height: maxH }
  const s = Math.min(maxW / natW, maxH / natH)
  return { width: natW * s, height: natH * s }
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
  ROW_BORDER: KONVA_COL.border, REF: '#dc2626', NOM: '#6b7280', VAL: KONVA_COL.textMain,
  // X3 — el marc exterior de la taula era gold i cridava més que la taula: el gold és el
  // color de SELECCIÓ de l'editor, i una taula sempre emmarcada en gold semblava sempre
  // seleccionada. Passa a la tinta discreta de la taula (la mateixa negra de la capçalera),
  // amb el gruix mínim dels filets interiors: el marc tanca, no decora.
  FRAME: '#111827', FRAME_SW: 0.5,
  BASE_HDR_BG: KONVA_COL.gold,
  BASE_BG: '#e5e7eb', BASE_HDR: '#dc2626', BREAK: '#dc2626', DELTA: '#185fa5',
}

// R4 — una cel·la és NUMÈRICA si tot el que hi ha és un nombre, amb el signe i els decimals
// que el domini hi posa: '+1', '−0.5' (menys tipogràfic de rowDelta), '37.5', o buida amb '—'.
// No s'hi val un heurístic per tipus: les cel·les viatgen com a string des de la inserció.
const NUM_RE = /^[+\-−]?\d+(?:[.,]\d+)?$/
const esNumeric = (v) => NUM_RE.test(String(v ?? '').trim())

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
    if (isBase) prims.push({ t: 'r', x: sizesX0 + si * T_VAL_W, y: 0, w: T_VAL_W, h: T_HDR_H, fill: TBL.BASE_HDR_BG })
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
  prims.push({ t: 'r', x: 0, y: 0, w: totalW, h: totalH, stroke: TBL.FRAME, sw: TBL.FRAME_SW })
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
  // R4 · LA CAPÇALERA NO ES TALLA MAI. Un títol de columna amb ellipsi no es pot endevinar
  // (i en una taula de mesures, endevinar què mesura una columna és exactament el que no pot
  // passar). Si no hi cap, parteix en línies i la fila creix. La font és monoespaiada, així
  // que comptar caràcters n'és una mesura exacta, no una estimació.
  const charW = fontPx * 0.6
  const hdrLines = cols.map((c, i) => {
    const cabenPerLinia = Math.max(1, Math.floor((cw[i] - 2 * T_PAD) / charW))
    return Math.max(1, Math.ceil(String(c.label ?? '').length / cabenPerLinia))
  })
  const hdrH = Math.max(...hdrLines, 1) * fontPx + T_CELL_PAD_Y * 2
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
    prims.push({ t: 't', x: cx0[i] + T_PAD, y: 0, w: cw[i] - 2 * T_PAD, h: hdrH, text: String(c.label ?? ''), fill: TBL.HDR_TEXT, size: fontPx, bold: true, mid: true, align: 'center', wrap: true })
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
      // ESTRUCTURAL (jerarquia de taula): capçalera i primera columna, sempre en negreta.
      // `cell.bold` = marca de BREAK per-cel·la (vermell + subratllat). LEGACY des de S4: les T1b
      // noves ja no la posen (les xifres van totes en negre i el break viu a la seva columna); es
      // manté aquí perquè els SNAPSHOTS ja inserits abans de S4 segueixin pintant-se igual (no es
      // migren). Cap taula nova entra per aquesta branca.
      const isBreak = !!cell.bold
      const bold = isBreak || i === 0
      const fill = isBreak ? TBL.BREAK : TBL.VAL
      // R4 · les XIFRES van centrades a la cel·la. Alineades a l'esquerra, una columna de
      // talles es llegeix com un serrell; centrades, la columna es llegeix d'un cop d'ull.
      // El text (nomenclatura, nom de POM, material) es queda a l'esquerra, que és on es llegeix.
      const align = esNumeric(cell.text) ? 'center' : 'left'
      if (cell.sub) {
        prims.push({ t: 't', x: cxR + T_PAD, y: y + T_CELL_PAD_Y, w: wCell, h: fontPx + 2, text: cell.text || '', fill, size: fontPx, bold, underline: isBreak, mid: false, align })
        prims.push({ t: 't', x: cxR + T_PAD, y: y + T_CELL_PAD_Y * 2 + fontPx, w: wCell, h: subPx + 2, text: cell.sub, fill: TBL.NOM, size: subPx, italic: true, mid: false })
      } else {
        prims.push({ t: 't', x: cxR + T_PAD, y, w: wCell, h: rowH, text: cell.text || '', fill, size: fontPx, bold, underline: isBreak, mid: true, align })
      }
      cxR += cw[i]
    })
    prims.push({ t: 'l', points: [0, y + rowH, totalW, y + rowH], stroke: TBL.ROW_BORDER, sw: 0.5 })
  })

  // Separadors verticals (interns) + vora exterior
  let cxV = cw[0] || 0
  cw.slice(1).forEach(w => { prims.push({ t: 'l', points: [cxV, 0, cxV, totalH], stroke: TBL.ROW_BORDER, sw: 0.5 }); cxV += w })
  prims.push({ t: 'r', x: 0, y: 0, w: totalW, h: totalH, stroke: TBL.FRAME, sw: TBL.FRAME_SW })
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
  // R4 — `p.wrap` deixa que una prim demani salt de línia en lloc d'ellipsi. Per defecte es
  // manté el comportament de sempre (una línia, ellipsi): només les capçaleres de taula ho
  // demanen, perquè un títol de columna tallat no es pot endevinar.
  return <Text x={p.x} y={p.y} width={p.w} height={p.h} text={p.text} fill={p.fill}
    fontSize={p.size} fontFamily={FONT} fontStyle={p.bold ? 'bold' : p.italic ? 'italic' : 'normal'}
    textDecoration={p.underline ? 'underline' : ''}
    align={p.align || 'left'} verticalAlign={p.mid ? 'middle' : 'top'}
    ellipsis={!p.wrap} wrap={p.wrap ? 'word' : 'none'} listening={false} />
}

// Primitiva → node Konva imperatiu (render offscreen per a export/miniatures).
function addPrimsToGroup(group, prims) {
  for (const p of prims) {
    if (p.t === 'r') group.add(new Konva.Rect({ x: p.x, y: p.y, width: p.w, height: p.h, fill: p.fill, stroke: p.stroke, strokeWidth: p.sw, dash: p.dash }))
    else if (p.t === 'l') group.add(new Konva.Line({ points: p.points, stroke: p.stroke, strokeWidth: p.sw }))
    else group.add(new Konva.Text({ x: p.x, y: p.y, width: p.w, height: p.h, text: p.text, fill: p.fill, fontSize: p.size, fontFamily: FONT, fontStyle: p.bold ? 'bold' : p.italic ? 'italic' : 'normal', textDecoration: p.underline ? 'underline' : '', align: p.align || 'left', verticalAlign: p.mid ? 'middle' : 'top', ellipsis: !p.wrap, wrap: p.wrap ? 'word' : 'none' }))
  }
}

// Bloc de taula graduada — Konva natiu (no imatge). NO fa fetch: rep tableData del pare.
function GradedTableNode({ tableData, groupProps, isSelected }) {
  const { prims, totalW, totalH } = useMemo(() => buildTablePrimitives(tableData), [tableData])
  return (
    <Group {...groupProps}>
      {prims.map((p, i) => <PrimNode key={i} p={p} />)}
      {isSelected && <Rect x={0} y={0} width={totalW} height={totalH} stroke={KONVA_COL.gold} strokeWidth={2} dash={[4, 3]} fill="transparent" listening={false} />}
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
      {isSelected && <Rect x={0} y={0} width={totalW} height={totalH} stroke={KONVA_COL.gold} strokeWidth={2} dash={[4, 3]} fill="transparent" listening={false} />}
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
  // R2 — CENTRAT VERTICAL REAL. La caixa feia `fs * 1.6 + pad * 2` d'alt però el text es
  // pintava des de dalt (sense height ni verticalAlign): quedava `pad` de marge a sobre i
  // `0.6 * fs + pad` a sota, és a dir tota la sobra avall. Es veia sobretot a l'etiqueta de
  // la cota de POM, que és petita i té el fons pintat.
  // Ara la caixa de línia és explícita i el text s'hi centra: mateixa alçada per als dos i
  // una sola font de veritat. `height` i `verticalAlign` viatgen dins `text`, que és el que
  // el llenç i l'export a PDF fan servir tots dos → la paritat es manté per construcció.
  const lineH = fs * 1.2
  return {
    group: { x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1 },
    bg: { x: -pad, y: -pad, width: w + pad * 2, height: lineH + pad * 2, fill: obj.bgFill, cornerRadius: 3 },
    text: {
      text: obj.text || '', width: w, height: lineH, fontSize: fs, fontFamily: obj.fontFamily || FONT,
      fontStyle: obj.fontStyle || 'normal', fill: obj.fill || KONVA_COL.textMain,
      align: obj.align || 'left', verticalAlign: 'middle', textDecoration: obj.textDecoration || '',
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
// La punta d'una fletxa curva es pinta del color del traç que remata: la seva PRIMERA
// subpath, resolta amb la llei de sempre. Si aquell traç no pinta res, la punta tampoc
// (abans queia a negre, que era inventar-se un color que ningú havia demanat).
function pathHeadColor(obj) {
  return resolStroke(obj, obj.paths?.[0])
}

function pathChildProps(obj, path) {
  const stroke = resolStroke(obj, path)
  const fill = resolFill(obj, path)
  return {
    data: pathToData(path),
    fill: fill || undefined,
    stroke: stroke || undefined,
    // Sense color de traç no hi ha traç: el gruix no s'ha ni de mirar.
    strokeWidth: stroke ? resolStrokeWidth(obj, path) : undefined,
    // El dash (repunts) es desa en mm com la geometria; a px amb toPx, com el `data`. Només
    // pinta si hi ha traç. Mateixa porta per al llenç viu i el PDF (tots dos passen per aquí).
    ...(stroke && path.dash?.length ? { dash: path.dash.map(toPx) } : {}),
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
  // C1 — una cota (grup amb pomId) NO fa servir el Transformer d'escala/rotació: s'edita amb
  // nanses d'extrem (no escalat lliure que distorsioni el text ni la geometria).
  return obj && (obj.type === 'line' || obj.type === 'arrow' || obj.type === 'field'
    || (obj.type === 'text' && obj.bgFill) || (obj.type === 'group' && obj.pomId != null))
}

function commonValue(objects, key) {
  if (!objects.length) return ''
  const first = objects[0]?.[key] ?? ''
  return objects.every(o => (o?.[key] ?? '') === first) ? first : ''
}

// ── S3 · Propietats de pintura comunes en multiselecció ─────────────────────────────────
// Quins types suporten cada canal (REGLA 3 · aplicabilitat per type). Idèntics als filtres
// que ja feia servir el panell, ara hoisted per compartir-los amb la lògica recursiva.
const STROKE_PAINT_TYPES = ['rect', 'ellipse', 'line', 'arrow', 'path']
const FILL_PAINT_TYPES = ['text', 'rect', 'ellipse', 'path']
const paintTypeSupports = (type, key) => (key === 'fill' ? FILL_PAINT_TYPES : STROKE_PAINT_TYPES).includes(type)
// Un grup (sketch inclòs) suporta un canal si algun descendent el suporta.
function supportsPaint(o, key) {
  return paintTypeSupports(o.type, key) || (o.type === 'group' && (o.children || []).some(c => supportsPaint(c, key)))
}
// Aplica un patch de pintura {stroke?|fill?|strokeWidth?} a un objecte respectant el contracte
// de ftt/paint i, en grups, RECURSIVAMENT als fills (comportament Illustrator, REGLA 4). Només
// escriu les claus del patch → canviar el color no arrossega gruix ni dash (REGLA 2). Els fills
// que no suporten una clau l'ometen (REGLA 3). A un `path`, netejar els sobreescrits de subpath
// perquè el valor nou no quedi amagat (mateixa llei que patchPintura del panell d'1 sol objecte).
function applyPaintTree(o, patch) {
  if (o.type === 'group') return { ...o, children: (o.children || []).map(c => applyPaintTree(c, patch)) }
  const keys = {}
  for (const k of Object.keys(patch)) if (paintTypeSupports(o.type, k)) keys[k] = patch[k]
  if (o.type === 'arrow' && 'stroke' in keys) keys.fill = keys.stroke   // la punta segueix el traç
  if (!Object.keys(keys).length) return o
  return Array.isArray(o.paths)
    ? { ...o, ...keys, paths: o.paths.map(p => sensePintura(p, Object.keys(keys))) }
    : { ...o, ...keys }
}
// Lectura INDETERMINADA (REGLA 1): aplana l'arbre a fulles pintables i compara el valor RESOLT
// (no el camp cru: un `path` hereta del subpath, un grup no té pintura pròpia). Difereixen → ''.
const paintLeaves = (o) => (o.type === 'group' ? (o.children || []).flatMap(paintLeaves) : [o])
function commonPaint(objects, key) {
  const leaves = objects.flatMap(paintLeaves).filter(o => paintTypeSupports(o.type, key))
  if (!leaves.length) return ''
  const read = (o) => (key === 'fill' ? resolFill(o, o.paths?.[0])
    : key === 'strokeWidth' ? resolStrokeWidth(o, o.paths?.[0])
    : resolStroke(o, o.paths?.[0])) ?? ''
  const first = read(leaves[0])
  return leaves.every(o => read(o) === first) ? first : ''
}

async function addObjectToLayer(layer, obj, ctx, cotaLabel) {
  if (obj.type === 'group') {
    const g = new Konva.Group({
      x: toPx(obj.x || 0), y: toPx(obj.y || 0), rotation: obj.rotation || 0,
      scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1,
    })
    const orderedChildren = [...(obj.children || [])].sort(
      (a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
    // C2: els fills text d'una cota (grup amb pomId) es marquen com a etiqueta → estil de render.
    const esCota = obj.pomId != null
    for (const child of orderedChildren) {
      if (child.visible === false) continue
      await addObjectToLayer(g, child, ctx, esCota && child.type === 'text')
    }
    layer.add(g)
    return
  }
  if (obj.type === 'text') {
    // C2 — etiqueta de cota: text vermell sense requadre, ignorant bgFill/fill desats (migració
    // visual de les cotes antigues). Paritat live↔PDF: aquest és el camí d'export/miniatura.
    if (cotaLabel) {
      const p = textBoxParts(obj)
      const g = new Konva.Group(p.group)
      g.add(new Konva.Text({ ...p.text, fill: KONVA_COL.pom, listening: false }))
      layer.add(g)
      return
    }
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
    if (o.iaProposada) continue   // F3: cota PROPOSADA (pendent de revisió) — mai a l'export ni a miniatures
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
    // F3: les cotes PROPOSADES per la IA (iaProposada) són NOMÉS pantalla fins a acceptar-les;
    // no sobreviuen la sessió (decisió de codi mínim) → no entren al .ftt.
    objects: (p.objects || []).filter(o => !o.iaProposada).map(serializeObject),
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

// C1 — nanses d'una COTA seleccionada: dos extrems (cercles, com line/arrow) + una nansa
// quadrada per arrossegar l'ETIQUETA sense tocar la línia. Substitueixen el Transformer d'escala
// (que distorsionaria el text). Es pinten a l'espai del Layer (px de pàgina), sobre la cota.
function CotaHandles({ obj, onEndpointDrag, onLabelDrag }) {
  const ends = cotaHandleEnds(obj)
  if (!ends) return null
  const A = { x: toPx(ends.a.x), y: toPx(ends.a.y) }
  const B = { x: toPx(ends.b.x), y: toPx(ends.b.y) }
  const mk = (which, p) => (
    <Circle key={which} x={p.x} y={p.y} radius={5} fill={KONVA_COL.white} stroke={KONVA_COL.gold} strokeWidth={1.5}
      draggable onMouseDown={ev => { ev.cancelBubble = true }}
      onDragMove={onEndpointDrag(which)} onDragEnd={onEndpointDrag(which)} />
  )
  return (
    <>
      {mk('start', A)}{mk('end', B)}
      {ends.lc && onLabelDrag && (
        <Rect x={toPx(ends.lc.x) - 4} y={toPx(ends.lc.y) - 4} width={8} height={8} cornerRadius={2}
          fill={KONVA_COL.gold} stroke={KONVA_COL.white} strokeWidth={1}
          draggable onMouseDown={ev => { ev.cancelBubble = true }}
          onDragMove={onLabelDrag} onDragEnd={onLabelDrag} />
      )}
    </>
  )
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

export function ObjectNode({ obj, src, tableData, modelData, versio, placeholderMode, customerLogoUrl, pageCtx, onHeaderContextMenu, selected, selectable, draggable, onSelect, onDragStart, onDragMove, onDragEnd, onTransformEnd, onDblText, onDblVector, entered, onDblGroup, onChildSelect, onChildDragEnd, selectedChildId, activeSubIndex, onSubSelect, subpathTool, onEndpointDrag, onCotaEndpointDrag, onCotaLabelDrag, cotaLabel, hideTextChildren }) {
  const common = {
    id: obj.id,
    x: toPx(obj.x), y: toPx(obj.y), rotation: obj.rotation || 0, scaleX: obj.scaleX || 1, scaleY: obj.scaleY || 1,
    // F3: una cota PROPOSADA per la IA es pinta ATENUADA (encara no acceptada). Només al llenç viu.
    opacity: obj.iaProposada ? 0.5 : undefined,
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
    // C2 (Patró C) — l'etiqueta d'una cota es pinta com a TEXT VERMELL SENSE requadre (la
    // convenció real de les fitxes del client). És estil de RENDER: ignora qualsevol bgFill/fill
    // desat a la dada, així les cotes antigues (fons vermell + text blanc) migren soles. Mateixa
    // geometria que la caixa (textBoxParts) però sense el Rect → la posició no es mou.
    if (cotaLabel) {
      const p = textBoxParts(obj)
      // Sense el Rect de fons, el text ha de seguir captant el clic (bombolla al grup-cota per
      // seleccionar-lo, com feia abans la caixa vermella): per això NO va amb listening={false}.
      return (
        <Group {...common} onDblClick={onDblText} onDblTap={onDblText}>
          <Text {...p.text} fill={KONVA_COL.pom} />
        </Group>
      )
    }
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
    const groupNode = (
      <Group {...common} onDblClick={onDblGroup} onDblTap={onDblGroup}>
        {orderedChildren.map(child => (
          <ObjectNode key={child.id} obj={child} src={child.src}
            tableData={tableData} modelData={modelData} versio={versio}
            placeholderMode={placeholderMode} customerLogoUrl={customerLogoUrl}
            // S1: dins d'un grup ENTRAT, els fills es poden seleccionar i moure (no rotar/redimensionar/editar).
            selected={entered ? child.id === selectedChildId : false}
            selectable={!!entered} draggable={!!entered}
            // C2: el fill text d'una cota (grup amb pomId) es pinta amb l'estil d'etiqueta.
            cotaLabel={obj.pomId != null && child.type === 'text'}
            onSelect={entered ? (e) => onChildSelect(e, child.id) : undefined}
            onDragEnd={entered ? onChildDragEnd(child) : undefined}
            onTransformEnd={undefined}
            onDblText={undefined} onDblVector={undefined} />
        ))}
      </Group>
    )
    // C1 — cota seleccionada (i NO entrada per editar nodes): nanses d'extrem + drag d'etiqueta,
    // mai el Transformer d'escala global. S'aplica a TOTES les cotes (manual, precedent o IA).
    if (selected && !entered && obj.pomId != null && onCotaEndpointDrag) {
      return <>{groupNode}<CotaHandles obj={obj} onEndpointDrag={onCotaEndpointDrag} onLabelDrag={onCotaLabelDrag} /></>
    }
    return groupNode
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
  // `clip-path` s'inline perquè Paper importSVG NO llegeix classes CSS del <style>: sense
  // inline-ar-lo, el clip d'un <g class> es perd i el que amagava (p.ex. la cua de la cremallera
  // sota el baix) es fa visible. `g` entra a la llista perquè el clip viu típicament al grup.
  const paintAttrs = ['fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'fill-rule', 'clip-rule', 'clip-path']
  const clipAttrs = ['clip-path', 'clip-rule']
  doc.querySelectorAll('path, polygon, polyline, line, rect, g').forEach(el => {
    const merged = {}
    ;(el.getAttribute('class') || '').split(/\s+/).filter(Boolean).forEach(className => {
      Object.assign(merged, classStyles[className] || {})
    })
    // Els <g> reben NOMÉS el clip (no la pintura, per no alterar l'herència de color dels fills);
    // les formes reben tota la pintura + el clip. Acotat: cap atribut nou fora de clip-path.
    const attrs = el.tagName.toLowerCase() === 'g' ? clipAttrs : paintAttrs
    attrs.forEach(attr => {
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
  // Escala UNIFORME (fix proporció, DIAGNOSI_IMPORT_SVG_PROPORCIO): abans la caixa es
  // dimensionava amb la ràtio del viewBox però el contingut s'hi encaixava amb scaleX/scaleY
  // INDEPENDENTS (imported.bounds), deformant els SVG amb marge (exports Illustrator
  // responsive). Un sol factor encaixa el contingut dins width×height PRESERVANT-NE la ràtio
  // real; com que el retorn descarta width/height (type 'path' → manen les coordenades), la
  // caixa de l'objecte queda amb la mida real del contingut escalat.
  const scale = Math.min(width / bounds.width, height / bounds.height)
  const scaleX = scale
  const scaleY = scale
  const strokeScale = scale
  const mapSegs = (paperPath) => {
    // globalMatrix inclou els transforms que Paper conserva SENSE bakejar (p.ex. un <rect> rotat
    // no pot ser una Shape paramètrica → li queda la matriu). Sense això, translate/rotate es
    // perdien i l'element sortia desplaçat (cas cremallera VEGA-3, ANNEX de la diagnosi). És
    // identitat si Paper ja havia coït el transform → no-op per als elements sense transform. Les
    // nanses són VECTORS: transformar punt+nansa i restar el punt transformat.
    const m = paperPath.globalMatrix
    return paperPath.segments.map(seg => {
      const p = m.transform(seg.point)
      const hi = m.transform(seg.point.add(seg.handleIn)).subtract(p)
      const ho = m.transform(seg.point.add(seg.handleOut)).subtract(p)
      return {
        x: (p.x - bounds.x) * scaleX,
        y: (p.y - bounds.y) * scaleY,
        inX: hi.x * scaleX,
        inY: hi.y * scaleY,
        outX: ho.x * scaleX,
        outY: ho.y * scaleY,
      }
    })
  }
  // ── Retall del clipPath a l'IMPORT (cua de cremallera) ──────────────────────
  // Paper conserva el clip com un Group amb `clipped=true` i una màscara (primer fill,
  // `clipMask`). El clip NO es baixa a geometria en render → l'hem de COURE aquí (booleana)
  // perquè el resultat sigui fidel als dos renders, al round-trip i al PDF de franc. Triatge per
  // bounds (contenció): només els fills que CREUEN la vora fan intersect. Mai perdre geometria en
  // silenci: si una booleana falla, es conserva el fill sencer i es compta.
  let clipDins = 0, clipFora = 0, clipCreua = 0, clipFallits = 0
  const retallaAmbMascara = (item, mask) => {
    if (!mask) return item
    let ib, mb
    try { ib = item.bounds; mb = mask.bounds } catch { return item }
    if (!mb.intersects(ib)) { clipFora += 1; return null }        // totalment FORA → descartar
    if (mb.contains(ib)) { clipDins += 1; return item }           // totalment DINS → tal qual
    clipCreua += 1
    try {
      const res = item.intersect(mask, { insert: false, trace: true })
      if (!res) return null
      if (typeof res.isEmpty === 'function' && res.isEmpty()) return null
      res.style = item.style   // la booleana no sempre hereta la pintura de l'original
      return res
    } catch { clipFallits += 1; return item }                     // fallada → conservar sencer
  }
  // Recorre l'arbre sense aplanar els CompoundPath (forats als fills). En entrar en un grup
  // clipat, aplica la seva màscara als fills; la màscara mai s'emet com a traç.
  const collect = (item, out, mask) => {
    if (item.clipMask) return                                     // una màscara no és contingut
    const cn = item.className
    if (cn === 'CompoundPath' || cn === 'Path') {
      const r = retallaAmbMascara(item, mask)
      if (r) out.push(r.className === 'CompoundPath' ? { compound: r } : { path: r })
      return
    }
    const kids = item.children
    if (!kids) return
    // Grup clipat: 1r fill = màscara (clipMask), la resta = contingut que l'hereta. Sense clip,
    // hereta la màscara del context. Nested-clip: preval la interior (aquest fitxer en té 1).
    const teMascara = item.clipped && kids.length && kids[0].clipMask
    const m = teMascara ? kids[0] : mask
    ;(teMascara ? kids.slice(1) : kids).forEach(c => collect(c, out, m))
  }
  const collected = []
  collect(imported, collected, null)
  if (clipDins + clipFora + clipCreua + clipFallits > 0) {
    // Report del triatge (visible a la consola del navegador; mai perdre geometria en silenci).
    console.info(`[import SVG · clip] dins=${clipDins} fora=${clipFora} creuen=${clipCreua} fallits=${clipFallits}`)
  }
  // El dasharray de l'SVG viu en unitats d'usuari; s'escala com la geometria (→ mm) i el render
  // el passa a px amb toPx, igual que les coordenades. Recupera el bug conegut de pèrdua del dash
  // (els repunts sortien continus); en abast NOMÉS per als traços que en porten (capa repunts).
  const dashDe = (item) => {
    const dash = item.dashArray
    if (!Array.isArray(dash) || !dash.length) return undefined
    const d = dash.map(v => v * strokeScale).filter(v => v > 0)
    return d.length ? d : undefined
  }
  // ── Descriptor de pintura+geometria d'una entrada (path simple o compost amb forats) ──
  const descriptorDe = (entry) => {
    if (entry.compound) {
      const compound = entry.compound
      const subpaths = compound.children
        .filter(c => c.className === 'Path' && c.segments?.length)
        .map(c => ({ closed: !!c.closed, segments: mapSegs(c) }))
      if (!subpaths.length) return null
      const dash = dashDe(compound)
      return {
        fill: normalizePaint(compound.fillColor ? paperColorToCss(compound.fillColor, null) : null),
        fillRule: 'evenodd',
        stroke: normalizePaint(compound.strokeColor ? paperColorToCss(compound.strokeColor, null) : null),
        strokeWidth: Math.max(0.2, (compound.strokeWidth || 1) * strokeScale),
        ...(dash ? { dash } : {}),
        subpaths,
      }
    }
    const path = entry.path
    if (!path.segments?.length) return null
    const dash = dashDe(path)
    return {
      closed: !!path.closed,
      stroke: normalizePaint(path.strokeColor ? paperColorToCss(path.strokeColor, null) : null),
      fill: normalizePaint(path.fillColor ? paperColorToCss(path.fillColor, null) : null),
      fillRule: normalizeFillRule(path.fillRule),
      strokeWidth: Math.max(0.2, (path.strokeWidth || 1) * strokeScale),
      ...(dash ? { dash } : {}),
      segments: mapSegs(path),
    }
  }

  // ── Classificació per ROL (heurística d'ESTILS, determinista — mai geometria, mai IA) ──
  // Cada traç recollit es reparteix a una de tres capes segons els atributs Paper resolts
  // (post-inline de les classes CSS). RES es descarta: en cas de dubte, SILUETA (el pitjor cas
  // és soroll dins la silueta, no un traç de peça perdut dins detall). Vegeu la diagnosi
  // DIAGNOSI_IMPORT_SVG_PROPORCIO (§editabilitat / monolitisme). Llindars afinables:
  const ROL = { SILUETA: 'silueta', REPUNTS: 'repunts', DETALL: 'detall' }
  const DASH_MIN_GUIO = 0.01   // longitud mínima (unitats SVG) d'un guió perquè un traç sigui repunt
  const teDash = (item) => Array.isArray(item.dashArray) && item.dashArray.some(d => d > DASH_MIN_GUIO)
  const rolDe = (item) => {
    if (teDash(item)) return ROL.REPUNTS                                   // stroke-dasharray → repunts
    const teFill = !!(item.fillColor && (item.fillColor.gradient || paperColorToCss(item.fillColor, null)))
    if (teFill) return ROL.DETALL                                         // fill sòlid o gradient → detall
    return ROL.SILUETA                                                    // stroke + fill:none, i el dubte
  }

  const buckets = { [ROL.SILUETA]: [], [ROL.REPUNTS]: [], [ROL.DETALL]: [] }
  for (const entry of collected) {
    const desc = descriptorDe(entry)
    if (!desc) continue
    buckets[rolDe(entry.compound || entry.path)].push(desc)
  }
  const total = buckets.silueta.length + buckets.repunts.length + buckets.detall.length
  if (!total) return obj

  // Metadada comuna a tornar (id, x/y, sourceItemFitxer/viewSlot de F2a…), sense la forma vella.
  const meta = { ...obj, stroke: undefined, fill: undefined, strokeWidth: undefined, svg: undefined, width: undefined, height: undefined }
  // Ordre de pintat de les capes: DETALL al fons (cremallera/hardware plens), després la SILUETA
  // i els REPUNTS al davant (traços i costures visibles sobre l'ompliment) — flat tècnic net.
  const nonEmpty = [ROL.DETALL, ROL.SILUETA, ROL.REPUNTS].filter(rol => buckets[rol].length)

  // Un sol rol (o res a separar) → 1 path monolític, EXACTAMENT com abans (mai un grup d'un fill).
  if (nonEmpty.length <= 1) {
    return { ...meta, type: 'path', paths: buckets[nonEmpty[0]], children: undefined, kind: undefined }
  }
  // Diversos rols → GRUP de capes-path, cada capa ciutadana normal del llenç (seleccionable/
  // amagable/esborrable per separat en entrar al grup). Els fills neixen a x:0,y:0 amb les
  // mateixes coordenades locals → objectBounds(grup) == bbox del contingut sencer, i F2a
  // («Cotes des de precedent») opera sobre el grup igual que abans sobre el path (commit previ).
  const children = nonEmpty.map(rol => ({
    id: uid(), type: 'path', layer: 'free', role: rol, x: 0, y: 0, paths: buckets[rol],
  }))
  return { ...meta, type: 'group', kind: 'sketch', children, paths: undefined }
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
  const [multiOutlines, setMultiOutlines] = useState([])  // C1: filets per membre en multiselecció (overlay VIU, mai export/.ftt)
  const [tool, setTool] = useState('select')
  // 'loading' | 'owned' | 'conflict' | 'error' | 'readonly'
  const [lockState, setLockState] = useState((isEditMode || fttMode) ? 'loading' : 'readonly')
  const [conflict, setConflict] = useState(null)
  const [saveState, setSaveState] = useState(null)  // null|'saving'|'saved'|'error'
  // Fitxers del model. Es demanaven i es llençaven (l'estat era `[, setFitxers]`): ara els
  // llegeix la biblioteca de l'esquerra (C1), que és qui els ofereix per inserir.
  const [fitxers, setFitxers] = useState([])
  const [filePicker, setFilePicker] = useState(false)   // S03b · P7
  // F1 — el patró VIGENT del model (o null si no en té) i el selector de peces.
  const [patternFile, setPatternFile] = useState(null)
  // Y1 — les peces del patró viuen a la PERSIANA, no en un popup: {loading}|{pieces}|{error}.
  const [peces, setPeces] = useState({ loading: true })
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
  // R4 — unitat del tenant (CM|INCH). Les taules són SNAPSHOTS: el valor es formata quan es
  // congela, no a cada render. Formatar-lo al builder el convertiria en un binding viu i
  // contradiria la llei de la taula congelada; llegir el toggle a la inserció, en canvi, és
  // respectar-lo. Mateixa font que la resta del sistema (utils/format via fittingShared).
  const unit = useUnit()
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
  const [ribbonGroup, setRibbonGroup] = useState('file')
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
  // F2 (precedent de col·locació): enllaç OBJECT-LEVEL — la procedència viu a cada objecte
  // sketch (`sourceItemFitxer`, posat a l'import des del catàleg), no al document.
  const [f2Msg, setF2Msg] = useState(null)   // resultat de col·locar/desar precedents
  // F2 · propostes de col·locació agregades per pom_id (cascada del catàleg). El panell de POMs
  // les llegeix per marcar cada POM com a PROPOSABLE; mai una crida per POM (agregació client).
  const [propostes, setPropostes] = useState(() => new Map())   // pom_id → { p, derivat, hostId }
  const [proposantIA, setProposantIA] = useState(false)   // F3: crida de visió en curs (segons, no ms)
  const [importMode, setImportMode] = useState(null)     // IMP-1: null | 'image' | 'garment' (panell d'import al dock)
  const [importFile, setImportFile] = useState(null)     // IMP-2: fitxer triat (no s'insereix fins a "Inserir")
  const [importNavOpen, setImportNavOpen] = useState(false)   // C5.3: AssetNavigator com a font "FTT"
  const [importNav, setImportNav] = useState({ tab: 'models', cust: null, any: null, temp: null, modelId: null, gtId: null, gtiId: null })
  const [importDrag, setImportDrag] = useState(false)    // IMP-2: ressaltat de la drop zone
  const [ratioLocked, setRatioLocked] = useState(true)
  const [shiftHeld, setShiftHeld] = useState(false)   // S1: Shift premuda → resize proporcional
  const [zoomModHeld, setZoomModHeld] = useState(false)  // C1: Ctrl/⌘ premut → cursor lupa (zoom amb roda)
  const [zoomOutMod, setZoomOutMod] = useState(false)    // C1: Alt addicional → lupa d'allunyar
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
    // C1 — una cota (grup amb pomId) no és redimensionable pel panell (W/H escalarien i
    // distorsionarien el text): s'edita amb nanses d'extrem. La posició X/Y sí mou tota la cota.
    const esCota = obj.type === 'group' && obj.pomId != null
    return {
      width: w,
      height: h,
      x: positionByBounds ? b.minX : (obj.x || 0),
      y: positionByBounds ? b.minY : (obj.y || 0),
      canResize: !['line', 'arrow'].includes(obj.type) && !esCota,
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
        if (cancelled || !d) return null
        const list = d.results || d || []
        const vigent = list.find(f => f.is_current) || null
        setPatternFile(vigent)
        if (!vigent) { setPeces({ pieces: [] }); return null }
        // Y1 — i tot seguit les seves PECES. El llistat no les porta (el serializer de llista
        // les treu a posta), així que cal el detall; però és el detall amb RECOMPTES, no amb
        // els milers de punts, i n'hi ha un per model. Es demanen ara i no en obrir res
        // perquè la persiana ha de poder llistar-les —o dir que no n'hi ha— sense que
        // ningú l'hagi hagut de destapar abans, igual que la de taules i la d'arxius.
        return fetch(`${API}/api/v1/patterns/pattern-files/${vigent.id}/`, { headers: authHeaders })
          .then(r => (r.ok ? r.json() : null))
          .then(det => { if (!cancelled) setPeces(det ? { pieces: det.pieces || [] } : { error: true }) })
      }).catch(() => { if (!cancelled) setPeces({ error: true }) })

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

  // ── F1 (cota viva) — re-deriva l'etiqueta de cada cota vinculada des del POM viu ──
  // En carregar el document (o si canvia l'àlies del client) refresquem el text visible
  // de la cota des de pomRows. Si el POM/BM ja no existeix, la cota DEGRADA a dibuix mort
  // amb l'últim text conegut: mai crasha ni s'esborra. NOMÉS LECTURA: no toca cap dada del
  // POM. Depèn de [pomRows, pages] perquè document i pomRows carreguen en ordre no
  // determinista; és idempotent (si el text ja quadra, no hi ha setPages) i salta l'autosave
  // (skipSave) per no encadenar una versió nova del .ftt en cada obertura.
  useEffect(() => {
    if (!pomRows.length) return
    const bmById = new Map(pomRows.map(bm => [bm.id, bm]))
    const bmByPom = new Map(pomRows.map(bm => [bm.pom_id, bm]))
    let canvis = false
    const nextPages = pages.map(p => {
      const objects = (p.objects || []).map(o => {
        if (o.type !== 'group' || o.pomId == null) return o
        const bm = bmById.get(o.bmId) || bmByPom.get(o.pomId)
        if (!bm) return o   // degradació elegant: el POM/BM ja no hi és
        const nouText = cotaLabelDe(bm)
        if (!nouText) return o
        const kids = o.children || []
        const ti = kids.findIndex(k => k.type === 'text')
        if (ti < 0 || kids[ti].text === nouText) return o
        const oldText = kids[ti]
        const TW = measureTextWidthMm({ text: nouText, fontSize: 9, fontFamily: FONT, fontStyle: 'bold' })
        const cx = (oldText.x || 0) + (oldText.width || 0) / 2   // manté el centre del text
        const nouKids = kids.slice()
        nouKids[ti] = { ...oldText, text: nouText, width: TW, x: cx - TW / 2 }
        canvis = true
        return { ...o, children: nouKids, pomCanonical: bm.pom_code_global || o.pomCanonical || '' }
      })
      return objects === p.objects ? p : { ...p, objects }
    })
    if (canvis) { skipSave.current = true; setPages(nextPages) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pomRows, pages])

  // ── C1-fix — auto-col·locació de l'etiqueta de cada cota (offset perpendicular, mai sobre el
  // traç). Migra les cotes existents sense flag de moviment manual en re-renderitzar (mateix
  // patró que la re-derivació de text: idempotent + skipSave). `labelMoved` la deixa quieta.
  useEffect(() => {
    let canvis = false
    const nextPages = pages.map(p => {
      let pageCanvi = false
      const objects = (p.objects || []).map(o => {
        const no = autoPlaceCotaLabel(o)
        if (no !== o) { pageCanvi = true; canvis = true }
        return no
      })
      return pageCanvi ? { ...p, objects } : p
    })
    if (canvis) { skipSave.current = true; setPages(nextPages) }
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

  // ── C1: filet fi per element en multiselecció (estil Illustrator). Overlay VIU per BOUNDS
  //    de cada membre (getClientRect, barat — no re-estil del path), a més del marc del
  //    Transformer. Amb 1 sol objecte no fa res. Viu només al Stage viu: mai entra al camí
  //    d'export (renderPageToDataURL) ni al .ftt. Es recalcula en canviar la selecció, la
  //    geometria (pages) o la pàgina, i durant el drag (handleDragMove) perquè segueixi.
  const syncMultiOutlines = useCallback(() => {
    const stage = stageRef.current
    if (!stage || editingFlatId || selectedIds.length < 2) { setMultiOutlines([]); return }
    const outlines = selectedIds.map(id => {
      const n = stage.findOne('#' + id)
      if (!n) return null
      const r = n.getClientRect({ relativeTo: n.getLayer() })
      return { id, x: r.x, y: r.y, w: r.width, h: r.height }
    }).filter(Boolean)
    setMultiOutlines(outlines)
  }, [selectedIds, editingFlatId])
  useEffect(() => { syncMultiOutlines() }, [syncMultiOutlines, currentPage, pages])

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

  // ── C1: modificador de zoom (Ctrl/⌘) premut → cursor lupa al llenç (senyala «roda = zoom»).
  //    Alt addicional → lupa d'allunyar. Reutilitza el mecanisme de cursor-per-eina (Peça C):
  //    viewportCursor mira aquest estat i, en deixar anar, torna al cursor de l'eina activa.
  useEffect(() => {
    if (!locked) return undefined
    const sync = (e) => { setZoomModHeld(e.ctrlKey || e.metaKey); setZoomOutMod(e.altKey) }
    const clear = () => { setZoomModHeld(false); setZoomOutMod(false) }
    window.addEventListener('keydown', sync)
    window.addEventListener('keyup', sync)
    window.addEventListener('blur', clear)
    return () => {
      window.removeEventListener('keydown', sync)
      window.removeEventListener('keyup', sync)
      window.removeEventListener('blur', clear)
    }
  }, [locked])

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
    if (selectedIds.length >= 2) syncMultiOutlines()   // C1: els filets segueixen el moviment
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
  // C1 — arrossegar la nansa d'un extrem de cota mou NOMÉS aquell extrem (la línia), mantenint
  // l'etiqueta ancorada al punt mig sense deformar-la. Shift encaixa a 45° respecte l'altre extrem.
  const handleCotaEndpointDrag = (obj) => (which) => (e) => {
    const node = e.target
    let px = { x: node.x(), y: node.y() }
    if (e.evt?.shiftKey) {
      const ends = cotaHandleEnds(obj)
      if (ends) {
        const other = which === 'start' ? ends.b : ends.a
        px = snap45(toPx(other.x), toPx(other.y), px.x, px.y)
      }
    }
    const patch = resizeCotaEndpoint(obj, which, toMm(px.x), toMm(px.y))
    if (patch) updateObject(obj.id, patch)
  }
  // C1 — arrossegar la nansa de l'etiqueta la reposiciona (el text segueix l'ancoratge) sense
  // tocar la línia. Es desa a l'offset local del fill text; mai n'escala la mida.
  const handleCotaLabelDrag = (obj) => (e) => {
    const node = e.target
    const cx = toMm(node.x() + 4), cy = toMm(node.y() + 4)   // centre de la nansa (8×8)
    const kids = obj.children || []
    const ti = kids.findIndex(k => k.type === 'text')
    if (ti < 0) return
    const tobj = kids[ti]
    const tw = tobj.width || 0, hh = textHalfHeightMm(tobj.fontSize)
    const nk = kids.slice()
    nk[ti] = { ...tobj, x: (cx - (obj.x || 0)) - tw / 2, y: (cy - (obj.y || 0)) - hh }
    // C1-fix: marca la cota com moguda a mà → l'offset automàtic ja no la re-col·loca (ni en
    // estirar extrems ni la migració). Respectar on l'usuari l'ha deixada.
    updateObject(obj.id, { children: nk, labelMoved: true })
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
    // Cota PRE-CARREGADA des del contenidor de POMs: la fletxa i l'etiqueta van en vermell
    // (C2 · text sense requadre) i el text és l'ÀLIES DE CLIENT (o el codi canònic) del POM — la nomenclatura
    // amb què el patronista anomena aquesta mesura al croquis.
    // FRONTERA G1 (F1 cota viva): el grup guarda pomId i bmId com a VINCLE DE NOMÉS LECTURA.
    // L'etiqueta es re-deriva del POM viu en carregar el document, però la cota MAI escriu
    // cap valor de mesura ni res al POM/BaseMeasurement: el valor numèric no hi viu. Segueix
    // sent un dibuix, ara vinculat per id — mai una escriptura de dades.
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
    // "1/2 CHEST WIDTH". Es mesura un cop, aquí, i es desa. C2 · l'etiqueta va en vermell SENSE
    // requadre (cap camp per-cota fixa el fons): estil de convenció real de les fitxes.
    const etiqueta = pom ? pom.text : t('tech_sheet.preset_cota_text')
    const TW = measureTextWidthMm({ text: etiqueta, fontSize: 9, fontFamily: FONT, fontStyle: pom ? 'bold' : 'normal' })
    // C1-fix: posició INICIAL de l'etiqueta = offset perpendicular automàtic (mai sobre el traç),
    // dimensionat amb les extensions reals del text perquè netegi el traç a qualsevol orientació.
    const hh = textHalfHeightMm(9)
    const off = cotaLabelOffset(dx, dy, TW / 2, hh)
    const mx = dx / 2 + off.x, my = dy / 2 + off.y
    const text = pom
      ? { id: uid(), type: 'text', layer: 'free', x: mx - TW / 2, y: my - hh, width: TW, height: 10, text: etiqueta, fontSize: 9, fontFamily: FONT, fill: KONVA_COL.pom, fontStyle: 'bold', align: 'center' }
      : { id: uid(), type: 'text', layer: 'free', x: mx - TW / 2, y: my - hh, width: TW, height: 10, text: etiqueta, fontSize: 9, fontFamily: FONT, fill: KONVA_COL.textMain, align: 'center' }
    addObject({
      id: uid(), type: 'group', layer: 'free', x: ax, y: ay, rotation: 0,
      // F1: vincle de només-lectura al POM viu (escalars → round-trip .ftt lliure, no host-ref).
      ...(pom?.pomId != null ? { pomId: pom.pomId, bmId: pom.bmId, pomCanonical: pom.canonical || '' } : {}),
      children: [linia, text],
    })
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
  // PROPORCIÓ (fix ràster, germà de 95823a0 per als SVG): IMG_BOX_* és un MÀXIM, no una talla.
  // Abans width/height eren 120×80 CLAVATS: un PNG vertical entrava estirat horitzontalment i
  // un apaïsat comprimit, perquè ningú no llegia `naturalWidth/naturalHeight`. Ara la mida
  // natural manda i `containBox` l'encaixa amb un sol factor.
  const addImageFromDataURL = async (dataURL, extra = {}) => {
    let box = { width: IMG_BOX_W, height: IMG_BOX_H }
    try {
      const el = await loadImageEl(dataURL)
      box = containBox(el.naturalWidth || el.width, el.naturalHeight || el.height,
                       IMG_BOX_W, IMG_BOX_H)
    } catch { /* mida natural il·legible → caixa nominal (comportament d'abans) */ }
    // F2: `extra` pot portar sourceItemFitxer (procedència de catàleg de l'sketch importat).
    const obj = { id: uid(), type: 'image', layer: 'free', x: 50, y: 50, ...box, src: dataURL, ...extra }
    addObject(obj)
  }
  const handleFile = (file) => {
    if (!file || !locked) return
    const fr = new FileReader()
    fr.onload = () => { addImageFromDataURL(fr.result) }
    fr.readAsDataURL(file)
  }
  const onDrop = (e) => {
    e.preventDefault()
    if (!locked) return
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('image/')) handleFile(file)
  }
  // Insereix el logo del client com a imatge lliure (redimensionable). TS-4c.
  // Mateixa llei de proporció: un logo és un ràster i 40×20 clavats l'estiraven igual que un
  // PNG qualsevol. El logo de la CAPÇALERA ja es respectava (`headerMasterLogoRect`); el logo
  // LLIURE era l'excepció que quedava.
  const insertLogo = async () => {
    if (!locked) return
    if (!customerLogoUrl) { flash(t('tech_sheet.flash_no_logo')); return }
    let box = { width: LOGO_BOX_W, height: LOGO_BOX_H }
    try {
      const el = await loadImageEl(customerLogoUrl)
      box = containBox(el.naturalWidth || el.width, el.naturalHeight || el.height,
                       LOGO_BOX_W, LOGO_BOX_H)
    } catch { /* mida natural il·legible → caixa nominal */ }
    addObject({ id: uid(), type: 'image', kind: 'logo', layer: 'free', x: 10, y: 8, ...box, src: customerLogoUrl })
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
  const importFlatSvgText = async (svgText, extra = {}) => {
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
    // Reemplaçar l'SVG in-situ: també un grup-sketch (import amb rols separats) es pot rebuscar.
    // El convertit clara les claus de la forma contrària (`paths`/`children` a `undefined`), així
    // que el merge d'`updateObject` no deixa geometria rància ni de path ni de grup.
    if (['sketch_svg', 'path'].includes(selObj?.type) || (selObj?.type === 'group' && selObj?.kind === 'sketch')) {
      const source = {
        id: selObj.id, type: 'sketch_svg', layer: selObj.layer || 'free',
        x: selObj.x || 54, y: selObj.y || 44,
        width: selObj.width || width, height: selObj.height || height,
        svg: svgText,
      }
      const converted = await convertLegacySketchSvgObject(source)
      updateObject(selObj.id, { ...converted, ...extra })
      setEditingText(null)
      setTool('select')
      // Un grup no és editable per nodes directament (cal entrar-hi i triar un fill): no hi obrim
      // el sub-editor. Un path sí.
      setEditingFlatId(converted.type === 'group' ? null : selObj.id)
      return
    }
    const source = {
      id: uid(), type: 'sketch_svg', layer: 'free',
      x: 54, y: 44, width, height,
      svg: svgText,
    }
    const obj = await convertLegacySketchSvgObject(source)
    addObject({ ...obj, ...extra })   // addObject ja deixa l'objecte SELECCIONAT
    // Un import amb rols separats retorna un GRUP. Un grup NO és editable per nodes directament
    // (cal entrar-hi i triar un fill-path); deixar-hi `editingFlatId` posava l'editor en mode
    // node SENSE objectiu vàlid (`editingFlat` no resol un 'group'), i aquest estat suprimeix el
    // Transformer (:2962) i els filets de multiselecció (:2986) → el grup importat quedava sense
    // cap contenidor de selecció. Només un path/sketch entra al sub-editor; el grup queda
    // seleccionat i prou (el Transformer s'hi lliga tot sol).
    if (obj.type !== 'group') setEditingFlatId(obj.id)
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
    const nom = (f.nom_fitxer || '').toLowerCase()
    // D13: aquest fetch SÍ pot portar Authorization → va per l'endpoint AUTENTICAT, no pel
    // signat. Abans apuntava directament a /media/ (servit per nginx, sense cap gate).
    // url_extern viu en un altre origen: s'hi va sense capçalera (no li enviem el token).
    const extern = !!f.url_extern
    const url = extern ? f.url_extern : (f.id ? `${API}/api/v1/model-fitxers/${f.id}/download/` : null)
    if (!url) return
    // F2a — procedència de catàleg: per a un fitxer de MODEL viu a `derivat_de_item` (l'ItemFitxer
    // origen), NO a f.id (que és un ModelFitxer). Consistent amb importarDelTenant, que per a un
    // ItemFitxer usa f.id. Sense origen de catàleg → sense procedència. (Abans, aquest camí no en
    // portava mai.)
    const extra = f.derivat_de_item ? { sourceItemFitxer: f.derivat_de_item } : {}
    try {
      const r = await fetch(url, extern ? undefined : { headers: uploadHeaders })
      if (!r.ok) throw new Error('fetch')
      if (nom.endsWith('.svg')) {
        // Q1: un .svg entra VECTORIAL (importFlatSvgText → escala uniforme, editable), no ràster.
        // Mateixa bifurcació que importarDelTenant; abans aquí tot queia a addImageFromDataURL.
        await importFlatSvgText(await r.text(), extra)
      } else {
        await addImageFromDataURL(await blobToDataURL(await r.blob()), extra)
      }
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
        fmtMeasure(bm.base_value_cm, unit) ?? '',
        fmtMeasure(rule?.increment_base, unit) ?? '',
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

  // T1b — grading final: talles + Δ + columna Break. Les xifres graduades van TOTES en negre
  // (Patró C, deroga T2): el break ja no es codifica a la cel·la (ni vermell ni subratllat ni
  // negreta), sinó que es resumeix en una columna pròpia al final. Es conserva la negreta
  // estructural (capçalera + 1a columna) i les franges de la talla base. El color a les dades
  // queda reservat per a senyals d'EXCEPCIÓ futures. Snapshot congelat: només afecta reinsercions.
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
      // Ordre final: ...talles... · Δ · Break. Amplada mínima suficient per a un resum curt.
      { key: 'break', label: t('tech_sheet.tbl_col_break'), width: 22 },
    ]
    // Break = talla on el delta CANVIA respecte a la talla anterior (ordre de size_labels). Ara
    // NOMÉS alimenta la columna resum; la cel·la de la talla es queda en negre pla (C1).
    const esBreak = (row, sl, prevSl) => {
      const d = row.deltas?.[sl]
      const dPrev = prevSl != null ? row.deltas?.[prevSl] : undefined
      return prevSl != null && d != null && dPrev != null && d !== dPrev
    }
    const cellForSize = (row, sl) => fmtMeasure(row.valors?.[sl], unit) ?? '–'
    // Resum de breaks de la fila: buit si cap · una talla ("9/10") · llista compacta ("6 · 9/10").
    const breakResum = (row) => sizeLabels
      .filter((sl, si) => esBreak(row, sl, si > 0 ? sizeLabels[si - 1] : null))
      .join(' · ')
    const rows = data.rows.map(row => [
      row.ref || row.abbreviation || row.codi || '',
      { text: row.nom_en || '', sub: row.nom_ca || '' },
      ...sizeLabels.map(sl => cellForSize(row, sl)),
      rowDelta(row, data.base_size, sizeLabels),
      breakResum(row),
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
    setTablePicker(null)
    if (variant === 't1a') insertTableT1a(sfId)
    else if (variant === 't1b') insertTableT1b(sfId)
  }
  const onPickTableVariant = (variant) => {
    if (variant === 't2') { insertTableT2(); return }
    // R3 — la personalitzada s'insereix ja, 3×3. Preguntar files i columnes abans de veure res
    // no aporta: el panell dret ja té els controls d'afegir i treure files i columnes, i allà
    // es decideix VEIENT la taula, que és quan se sap quantes en calen.
    if (variant === 'custom') { insertTableCustom(3, 3); return }
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
  // C1 · Partició dels fitxers del model per a la biblioteca: el que és geometria inserible
  // (croquis/flats) va a la seva persiana; la resta, a Arxius. Mateix criteri que ja fa servir
  // l'AssetNavigator de l'import, no un de nou.
  // R3 · les quatre variants de taula amb la seva DISPONIBILITAT. La detecció és la que el
  // popup ja feia (sizeFittings per a les dues taules de mesures); aquí, en comptes de
  // deshabilitar un botó dins un modal, s'ensenya sempre i es diu el motiu.
  const TABLE_VARIANTS = [
    { k: 't1a', icon: 'ti-ruler-measure', label: t('tech_sheet.table_variant_t1a'), ok: sizeFittings.length > 0, motiu: t('tech_sheet.lib_table_no_fitting') },
    { k: 't1b', icon: 'ti-chart-grid-dots', label: t('tech_sheet.table_variant_t1b'), ok: sizeFittings.length > 0, motiu: t('tech_sheet.lib_table_no_fitting') },
    { k: 't2', icon: 'ti-list-details', label: t('tech_sheet.table_variant_t2'), ok: true, motiu: '' },
    { k: 'custom', icon: 'ti-table-plus', label: t('tech_sheet.table_variant_custom'), ok: true, motiu: '' },
  ]

  // R5 — a la biblioteca NOMÉS hi entra el que es pot inserir de veritat. `addModelFitxer`
  // fabrica un objecte `image` a partir dels bytes del fitxer: oferir-hi un PDF, un XLSX o un
  // .ftt no era una llista incompleta, era un botó que no podia funcionar. El sedàs és
  // l'extensió (svg/png/jpg/jpeg/webp/gif), el mateix que ja fa servir l'AssetNavigator.
  const fitxersInseribles = useMemo(
    () => (fitxers || []).filter(f => GEOMETRIA_INSERIBLE.test(f.nom_fitxer || '')),
    [fitxers])
  // Dins dels inseribles, els marcats com a geometria van a la seva persiana i la resta
  // (fotos, referències) a Arxius. Cap fitxer pot sortir a les dues ni a cap.
  const fitxersSketch = useMemo(
    () => fitxersInseribles.filter(f => TIPUS_GEOMETRIA.includes(f.tipus)),
    [fitxersInseribles])
  const fitxersAltres = useMemo(
    () => fitxersInseribles.filter(f => !TIPUS_GEOMETRIA.includes(f.tipus)),
    [fitxersInseribles])

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

  // F1 (cota viva): una cota compta com a col·locada pel seu pomId (vincle viu), no pel
  // text. Les cotes antigues sense pomId (pre-F1) no hi compten — degradació acceptada.
  const cotesColocades = useMemo(() => {
    const ids = new Set()
    for (const p of pages) {
      for (const o of flattenObjects(p.objects || [])) {
        // F3: una proposta IA pendent NO compta com a col·locada — encara ha de passar revisió.
        if (o.pomId != null && !o.iaProposada) ids.add(o.pomId)
      }
    }
    return ids
  }, [pages])
  // F3: pomIds amb una cota PROPOSADA-IA viva a la pàgina actual (pendent d'acceptar/descartar).
  const iaCotesByPom = useMemo(() => {
    const ids = new Set()
    for (const o of (pages[currentPage]?.objects || [])) {
      if (o.type === 'group' && o.pomId != null && o.iaProposada) ids.add(o.pomId)
    }
    return ids
  }, [pages, currentPage])
  const iaPropostesVives = useMemo(
    () => (pages[currentPage]?.objects || []).filter(o => o.type === 'group' && o.pomId != null && o.iaProposada),
    [pages, currentPage])

  // ── F2 (precedent de col·locació de cotes) · enllaç OBJECT-LEVEL ────────────
  // Objectes del croquis de la pàgina actual. Un objecte participa en F2 si porta la seva
  // procedència de catàleg (`sourceItemFitxer`, posada a l'import) i una vista assignada.
  // Un import SVG amb rols separables retorna un GRUP (`kind:'sketch'`) en comptes d'un path
  // monolític; la seva metadata de procedència viu al grup i `objectBounds` ja en calcula la
  // bbox del contingut, així que compta com a croquis igual que un path. El discriminant
  // `kind==='sketch'` deixa fora les cotes (grups amb `pomId`) i els grups d'usuari.
  const isSketchObj = (o) => SKETCH_OBJ_TYPES.includes(o.type) || (o.type === 'group' && o.kind === 'sketch')
  const sketchObjs = curObjs.filter(isSketchObj)
  // Assignar la vista a un objecte sketch (des de Propietats de l'objecte, UX-COTES). El col·locar
  // i el desar massius de l'antic contenidor «Cotes des de precedent» han mort: el col·locar viu
  // ara per-POM al panell (posarProposta/posarTotesPropostes) i el desar per-cota (desarUnaPrecedent).
  const assignaVista = (objId, slot) => updateObject(objId, { viewSlot: slot || undefined })

  // ── F2 · PROPOSTES agregades per pom_id ─────────────────────────────────────
  // Fonts = objectes sketch amb procedència de catàleg + vista assignada (la vista viu a
  // Propietats de l'objecte, no a cap llista). Signatura estable (id+item+vista) perquè l'efecte
  // re-demani NOMÉS quan canvien les fonts, no a cada render ni a cada tecleig de geometria.
  const propFontsSig = JSON.stringify(
    sketchObjs.filter(o => o.sourceItemFitxer && o.viewSlot).map(o => [o.id, o.sourceItemFitxer, o.viewSlot]))
  const propFonts = useMemo(
    () => sketchObjs.filter(o => o.sourceItemFitxer && o.viewSlot)
      .map(o => ({ hostId: o.id, item: o.sourceItemFitxer, slot: o.viewSlot })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [propFontsSig])
  useEffect(() => {
    if (!id || !propFonts.length) { setPropostes(new Map()); return undefined }
    let cancelled = false
    ;(async () => {
      const acc = new Map()   // pom_id → { p, derivat, hostId }; l'EXACTE (derivat=false) guanya la germana
      for (const f of propFonts) {
        try {
          const r = await fetch(
            `${API}/api/v1/item-fitxers/${f.item}/pom-placements/`
            + `?view_slot=${encodeURIComponent(f.slot)}&model_id=${id}`, { headers: authHeaders })
          if (!r.ok) continue
          const data = await r.json()
          for (const p of (data.placements || [])) {
            const prev = acc.get(p.pom_id)
            if (prev && !prev.derivat) continue      // ja hi ha exacte per aquest POM → no el trepitgem
            acc.set(p.pom_id, { p, derivat: !!p.derivat, hostId: f.hostId })
          }
        } catch { /* continua amb la següent font */ }
      }
      if (!cancelled) setPropostes(acc)
    })()
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, propFonts])

  // Construeix la cota VIVA de F1 d'una proposta, desnormalitzant sobre la bbox ACTUAL del seu
  // objecte-sketch host (si s'ha mogut/redimensionat, la cota hi cau bé igualment). null si el
  // host ja no hi és. La vista es resol SOLA: la del host, mai demanada per endavant.
  const buildCotaDeProposta = useCallback((pomId, prop) => {
    const host = curObjs.find(o => o.id === prop.hostId)
    if (!host) return null
    const bb = objectBounds(host)
    const bw = (bb.maxX - bb.minX) || 1, bh = (bb.maxY - bb.minY) || 1
    const bm = pomRows.find(r => r.pom_id === pomId)
    const p = prop.p
    const ax = bb.minX + p.x1 * bw, ay = bb.minY + p.y1 * bh
    const bx = bb.minX + p.x2 * bw, by = bb.minY + p.y2 * bh
    return buildLiveCota({
      ax, ay, dx: bx - ax, dy: by - ay,
      label: cotaLabelDe(bm) || p.codi, pomId, bmId: p.bm_id,
      canonical: p.codi, viewSlot: host.viewSlot, derivat: prop.derivat,
      // C1-fix: l'etiqueta es col·loca amb l'offset perpendicular automàtic (buildLiveCota), no
      // amb la posició normalitzada del precedent → mai sobre el traç.
    })
  }, [curObjs, pomRows])

  // «Posar» LA cota d'un POM proposable (mecànica de colocarDesPrecedent, però per POM). La cota
  // neix VIVA de F1: arrossegable, editable; el panell la veurà tot seguit com a COL·LOCAT.
  const posarProposta = useCallback((pomId) => {
    const prop = propostes.get(pomId)
    if (!prop) return
    const cota = buildCotaDeProposta(pomId, prop)
    if (cota) updatePageObjects(currentPage, objs => [...objs, cota])
  }, [propostes, buildCotaDeProposta, currentPage, updatePageObjects])

  // Acció de grup: posar TOTES les proposables que encara no són al document.
  const posarTotesPropostes = useCallback(() => {
    const nous = []
    for (const [pomId, prop] of propostes) {
      if (cotesColocades.has(pomId)) continue
      const cota = buildCotaDeProposta(pomId, prop)
      if (cota) nous.push(cota)
    }
    if (nous.length) updatePageObjects(currentPage, objs => [...objs, ...nous])
    setF2Msg(t('tech_sheet.pom_posades', { n: nous.length }))
  }, [propostes, cotesColocades, buildCotaDeProposta, currentPage, updatePageObjects, t])
  // Nombre de POMs proposables encara NO col·locats (per a l'acció de grup del panell).
  const proposablesCount = pomRows.filter(
    bm => bm.pom_id != null && !cotesColocades.has(bm.pom_id) && propostes.has(bm.pom_id)).length

  // Desar UNA cota com a precedent del catàleg (acte CONSCIENT, D1) — des de Propietats de la
  // cota. Resol el host sketch pel punt mig de la cota; la vista es pren del host. Substitueix
  // l'antic «Desar col·locació» massiu del contenidor mort.
  // Nucli compartit: resol el host sketch (per contenció del punt mig) i normalitza els extrems
  // sobre la seva bbox. null si la cota no cau sobre cap croquis de catàleg amb vista → sense
  // precedent (i sense error). El fan servir tant «desar precedent» (conscient) com l'acceptació
  // d'una proposta IA (llei de convivència: acceptar escriu precedent).
  const construirPrecedentCota = useCallback((cota) => {
    const e = cotaEndsMm(cota)
    if (!e) return null
    const mid = { x: (e.ax + e.bx) / 2, y: (e.ay + e.by) / 2 }
    const dins = (bb, pt) => pt.x >= bb.minX && pt.x <= bb.maxX && pt.y >= bb.minY && pt.y <= bb.maxY
    const host = sketchObjs.find(o => o.sourceItemFitxer && o.viewSlot && dins(objectBounds(o), mid))
    if (!host) return null
    const bb = objectBounds(host)
    const bw = (bb.maxX - bb.minX) || 1, bh = (bb.maxY - bb.minY) || 1
    return {
      host,
      body: {
        pom_id: cota.pomId, view_slot: host.viewSlot,
        x1: (e.ax - bb.minX) / bw, y1: (e.ay - bb.minY) / bh,
        x2: (e.bx - bb.minX) / bw, y2: (e.by - bb.minY) / bh,
        label_dx: e.lc ? (e.lc.x - mid.x) / bw : 0,
        label_dy: e.lc ? (e.lc.y - mid.y) / bh : 0,
        source_kind: host.type === 'image' ? 'raster' : 'vector',
      },
    }
  }, [sketchObjs])
  const desarUnaPrecedent = useCallback(async (cota) => {
    const built = construirPrecedentCota(cota)
    if (!built) { setF2Msg(t('tech_sheet.f2_desar_sense_host')); return }
    try {
      const r = await fetch(`${API}/api/v1/item-fitxers/${built.host.sourceItemFitxer}/pom-placements/`, {
        method: 'POST', headers: authHeaders, body: JSON.stringify(built.body) })
      setF2Msg(r.ok ? t('tech_sheet.f2_desar_ok') : t('tech_sheet.f2_desar_err'))
    } catch { setF2Msg(t('tech_sheet.f2_desar_err')) }
  }, [construirPrecedentCota, authHeaders, t])
  // Llei de convivència (D1): ACCEPTAR una proposta escriu precedent al catàleg — SILENCIÓS i
  // sense error si no hi ha origen (només queda la cota viva). El sistema aprèn de l'acceptació.
  const escriurePrecedentSilent = useCallback(async (cota) => {
    const built = construirPrecedentCota(cota)
    if (!built) return
    try {
      await fetch(`${API}/api/v1/item-fitxers/${built.host.sourceItemFitxer}/pom-placements/`, {
        method: 'POST', headers: authHeaders, body: JSON.stringify(built.body) })
    } catch { /* acceptar no ha de petar si el precedent no es pot desar */ }
  }, [construirPrecedentCota, authHeaders])

  // ── F3 · PROPOSAR cotes amb IA de visió ─────────────────────────────────────
  // Rasteritza la pàgina SENSE cotes (ni col·locades ni proposades) ni overlays, envia els
  // objectes sketch (bbox 0..1 de la pàgina) + els POMs PENDENT, i materialitza les propostes
  // com a cotes VIVES en estat PROPOSAT (iaProposada): atenuades, NOMÉS pantalla, manipulables.
  const proposarCotesIA = useCallback(async () => {
    const pendents = pomRows.filter(bm => bm.pom_id != null
      && !cotesColocades.has(bm.pom_id) && !iaCotesByPom.has(bm.pom_id))
    if (!pendents.length) { setF2Msg(t('tech_sheet.ia_cap_pendent')); return }
    const hosts = sketchObjs
    if (!hosts.length) { setF2Msg(t('tech_sheet.ia_cap_sketch')); return }
    setProposantIA(true)
    setF2Msg(t('tech_sheet.ia_proposant'))
    try {
      const netaObjs = (curObjs || []).filter(o => !(o.type === 'group' && o.pomId != null))
      const ctx = { tableData, modelData: model, versio: sheet?.versio, pageW, pageH, customerLogoUrl }
      const pageImage = await renderPageToDataURL({ ...pages[currentPage], objects: netaObjs }, 1.5, ctx)
      const sketches = hosts.map(o => {
        const bb = objectBounds(o)
        return {
          object_id: o.id, view_slot: o.viewSlot || null,
          bbox_norm: { x: bb.minX / fmt.w, y: bb.minY / fmt.h,
            w: (bb.maxX - bb.minX) / fmt.w, h: (bb.maxY - bb.minY) / fmt.h },
        }
      })
      const poms = pendents.map(bm => ({
        pom_id: bm.pom_id, code: bm.codi_client,
        canonical_name: bm.nom_en || bm.pom_code_global || '',
        client_alias: bm.client_alias || null, definition: bm.definicio || null,
      }))
      const r = await fetch(`${API}/api/v1/models/${id}/proposar-cotes/`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ page_image: pageImage, sketches, poms }) })
      if (!r.ok) {
        const e = await r.json().catch(() => ({}))
        setF2Msg(e.error || t('tech_sheet.ia_error')); return
      }
      const data = await r.json()
      const hostById = new Map(hosts.map(o => [o.id, o]))
      const bmByPom = new Map(pomRows.map(bm => [bm.pom_id, bm]))
      const nous = []
      for (const p of (data.placements || [])) {
        const host = hostById.get(p.object_id)
        if (!host || cotesColocades.has(p.pom_id) || iaCotesByPom.has(p.pom_id)) continue
        const bb = objectBounds(host)
        const bw = (bb.maxX - bb.minX) || 1, bh = (bb.maxY - bb.minY) || 1
        const bm = bmByPom.get(p.pom_id)
        const ax = bb.minX + (p.x1 || 0) * bw, ay = bb.minY + (p.y1 || 0) * bh
        const bx = bb.minX + (p.x2 || 0) * bw, by = bb.minY + (p.y2 || 0) * bh
        const cota = buildLiveCota({
          ax, ay, dx: bx - ax, dy: by - ay,
          label: cotaLabelDe(bm) || String(p.pom_id), pomId: p.pom_id, bmId: bm?.id,
          canonical: bm?.pom_code_global || '', viewSlot: host.viewSlot,
          // C1-fix: offset perpendicular automàtic (buildLiveCota), no la posició proposada per la IA.
        })
        nous.push({ ...cota, iaProposada: true, iaConfidence: p.confidence || 'mitjana' })
      }
      if (nous.length) updatePageObjects(currentPage, objs => [...objs, ...nous])
      const skip = (data.skip || []).length
      setF2Msg(t('tech_sheet.ia_proposades', { n: nous.length, s: skip }))
    } catch {
      setF2Msg(t('tech_sheet.ia_error'))
    } finally {
      setProposantIA(false)
    }
  }, [pomRows, cotesColocades, iaCotesByPom, sketchObjs, curObjs, pages, currentPage,
      tableData, model, sheet, pageW, pageH, customerLogoUrl, fmt, id, authHeaders, updatePageObjects, t])

  // Acceptar UNA proposta: la cota esdevé cota viva normal (F1) I, si el seu croquis ve del
  // catàleg amb vista, escriu precedent (el sistema aprèn de l'acceptació).
  const acceptarProposta = useCallback((cota) => {
    updateObject(cota.id, { iaProposada: undefined, iaConfidence: undefined })
    escriurePrecedentSilent(cota)
  }, [updateObject, escriurePrecedentSilent])
  const descartarProposta = useCallback((cotaId) => { deleteObject(cotaId) }, [deleteObject])
  const acceptarTotesPropostes = useCallback(() => {
    iaPropostesVives.forEach(escriurePrecedentSilent)
    updatePageObjects(currentPage, objs => objs.map(o => (
      o.iaProposada ? { ...o, iaProposada: undefined, iaConfidence: undefined } : o)))
    setF2Msg(t('tech_sheet.ia_acceptades'))
  }, [iaPropostesVives, escriurePrecedentSilent, currentPage, updatePageObjects, t])
  const descartarTotesPropostes = useCallback(() => {
    updatePageObjects(currentPage, objs => objs.filter(o => !o.iaProposada))
    setF2Msg(t('tech_sheet.ia_descartades'))
  }, [currentPage, updatePageObjects, t])

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
  // C2 · EL GATE ES FA SELECTIU. Bloquejar-ho tot era massa: el conflicte de dues mans només
  // existeix a la GEOMETRIA (W/H/X/Y i rotació escriuen el mateix que el canvas està movent).
  // La PINTURA no hi té cap conflicte —el color no és geometria— i és justament el que més es
  // vol tocar mentre s'edita una forma. Segueix disponible, però enrutada per mode: amb el
  // canvas obert, el color va al canvas viu (runNode, que el fusiona al desat) i no al model,
  // que és el motor que la Fase 6 ja havia construït.
  // Retornen TRUE si se n'han fet càrrec (i llavors el model no s'ha de tocar). Abans
  // retornaven el resultat de runNode —que és undefined— i el `??` del cridador deixava passar
  // TAMBÉ l'escriptura al model: es pintava dues vegades, i el valor del model competia amb la
  // pintura pendent que el desat fusiona des del canvas.
  const pintaEnCanvas = (accio, valor) => {
    if (!panelLockedForEdit) return false
    // X2 — i si el sub-editor encara no s'ha muntat (`lazy` dins d'un <Suspense>), NO diguem
    // que ens n'hem fet càrrec: `runNode` seria un no-op i el gest de l'usuari es perdria en
    // silenci. Sense canvas obert no hi ha dues mans, i escriure al model és el correcte.
    if (!paperFlatRef.current?.run) return false
    runNode(accio, valor)
    return true
  }
  const pintaFill = (c) => pintaEnCanvas('setFill', c)
  const pintaStroke = (c) => pintaEnCanvas('setStroke', c)
  const pintaStrokeWidth = (w) => pintaEnCanvas('setStrokeWidth', w)
  // X2 — ESCRIURE PINTURA. Una sola porta per als tres canals i per als dos nivells, perquè
  // el que s'escriu i el que es llegeix (`ftt/paint.js`) siguin la mateixa llei:
  //   · amb una subpath activa → s'escriu NOMÉS en aquella subpath;
  //   · sense subpath activa → s'escriu a l'objecte I s'esborren els sobreescrits que els
  //     seus subpaths tinguessin d'aquesta clau.
  // El segon punt és el que faltava. El subpath mana sobre l'objecte, o sigui que escriure
  // a l'objecte sense netejar el subpath deixava l'ordre de l'usuari amagada per sempre. Al
  // color gairebé no es notava (els subpaths solen tenir-lo buit i heretaven), però el gruix
  // el porten SEMPRE escrit tots els productors —la ploma hi posa 1,2; l'SVG,
  // `Math.max(0.2, …)`— i per això el gruix no es movia mai des del panell.
  const patchPintura = (obj, patch) => (Array.isArray(obj?.paths)
    ? { ...patch, paths: obj.paths.map(p => sensePintura(p, Object.keys(patch))) }
    : patch)
  const patchSubpath = (obj, i, patch) => ({ paths: obj.paths.map((p, k) => (k === i ? { ...p, ...patch } : p)) })
  const pintaShape = (patch) => updateShape(subActive != null && Array.isArray(shapeObj?.paths)
    ? patchSubpath(shapeObj, subActive, patch)
    : patchPintura(shapeObj, patch))
  // Pintura VIVA: amb el canvas obert els controls no poden llegir el model (allà no s'hi
  // escriu res fins al desat) o rebotarien al valor antic a cada pulsació. L'estat el puja el
  // sub-editor a `nodeSel` — ja hi era i no el llegia ningú.
  const pinturaViva = panelLockedForEdit && nodeSel?.strokeWidth != null ? nodeSel : null
  const multiSelected = selectedObjects.length > 1
  // S3 · inclou grups (sketch inclòs): la pintura s'hi aplica recursivament (applyPaintTree).
  const multiStroke = selectedObjects.filter(o => supportsPaint(o, 'stroke'))
  const multiFill = selectedObjects.filter(o => supportsPaint(o, 'fill'))
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
  const multiStrokeValue = commonPaint(multiStroke, 'stroke')
  const multiFillValue = commonPaint(multiFill, 'fill')
  const multiStrokeWValue = commonPaint(multiStroke, 'strokeWidth')   // S3 · gruix comú (indeterminat = '')
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
    // X2 — el resultat hereta la pintura del de sota, i s'ha de RESOLDRE amb la llei del
    // contracte: el color d'un dibuix vingut d'SVG viu al subpath, no a l'objecte. Mirar
    // només `ordered[0].stroke` el trobava buit i el buscatraços tornava el resultat negre.
    const base = ordered[0]
    const style = {
      stroke: resolStroke(base, base?.paths?.[0]),
      fill: resolFill(base, base?.paths?.[0]),
      strokeWidth: resolStrokeWidth(base, base?.paths?.[0]),
    }
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

  // D1 — Del `PALETTE` amb categories i flyouts que alimentava la paleta vertical només queda
  // el que encara fa falta: resoldre icona i etiqueta de l'EINA ACTIVA per a l'indicador de
  // context del ribbon. Les eines s'ofereixen al tab Inserir (C1), i és allà on viu l'ordre.
  const TOOL_DEFS = [
    { k: 'select', icon: 'ti-pointer-2', label: t('tech_sheet.tool_select') },
    { k: 'pan', icon: 'ti-hand-stop', label: t('tech_sheet.tool_pan') },
    { k: 'node', icon: 'ti-vector', label: t('tech_sheet.tool_node') },
    { k: 'subpath', icon: 'ti-vector-triangle', label: t('tech_sheet.tool_subpath') },
    { k: 'draw', icon: 'ti-pencil', label: t('tech_sheet.tool_draw') },
    { k: 'pen', icon: 'ti-vector-bezier', label: t('tech_sheet.tool_pen') },
    { k: 'rect', icon: 'ti-square', label: t('tech_sheet.tool_rect') },
    { k: 'rect_round', icon: 'ti-square-rounded', label: t('tech_sheet.tool_rect_round') },
    { k: 'ellipse', icon: 'ti-circle', label: t('tech_sheet.tool_ellipse') },
    { k: 'polygon', icon: 'ti-hexagon', label: t('tech_sheet.tool_polygon') },
    { k: 'line', icon: 'ti-line', label: t('tech_sheet.tool_line') },
    { k: 'line_dot', icon: 'ti-line-dashed', label: t('tech_sheet.tool_line_dot') },
    { k: 'arrow', icon: 'ti-arrow-right', label: t('tech_sheet.tool_arrow') },
    { k: 'arrow2', icon: 'ti-arrows-horizontal', label: t('tech_sheet.tool_arrow2') },
    { k: 'arrow_curve', icon: 'ti-vector-spline', label: t('tech_sheet.tool_arrow_curve') },
    { k: 'text', icon: 'ti-text-recognition', label: t('tech_sheet.tool_text') },
    { k: 'text_box', icon: 'ti-text-scan-2', label: t('tech_sheet.tool_text_box') },
    { k: 'cota_pom', icon: 'ti-ruler-measure', label: t('tech_sheet.tool_cota_pom') },
    { k: 'note', icon: 'ti-arrow-guide', label: t('tech_sheet.tool_note') },
    { k: 'preset_callout', icon: 'ti-message-2-share', label: t('tech_sheet.preset_callout') },
    { k: 'preset_detail_circle', icon: 'ti-circle-dashed', label: t('tech_sheet.preset_detail_circle') },
    { k: 'preset_legend', icon: 'ti-list-details', label: t('tech_sheet.preset_legend') },
  ]
  const activeToolDef = TOOL_DEFS.find(tl => tl.k === tool) || TOOL_DEFS[0]
  // Flyout: eina visible (col·lapsada) = l'activa si pertany al grup, si no l'última triada, si no la 1a.
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
    // F2 (enllaç object-level): si l'sketch ve del CATÀLEG (ItemFitxer), l'objecte guarda la
    // seva procedència. És la granularitat unívoca: una fitxa pot dur sketches de dos items. Un
    // sketch pujat localment no en porta → «Desar precedent» hi queda deshabilitat amb motiu.
    const extra = f.garment_type_item != null ? { sourceItemFitxer: f.id } : {}
    const url = extern ? f.url_extern : `${API}/api/v1/${mon}/${f.id}/download/`
    try {
      const r = await fetch(url, extern ? undefined : { headers: uploadHeaders })
      if (!r.ok) throw new Error('fetch')
      if (nom.endsWith('.svg')) {
        await importFlatSvgText(await r.text(), extra)   // SVG → path editable, com el camí local
      } else if (nom.endsWith('.dxf')) {
        flash(t('tech_sheet.import_dxf_soon'))      // el motor DXF segueix pendent
      } else {
        await addImageFromDataURL(await blobToDataURL(await r.blob()), extra)
      }
      closeImport()
    } catch {
      flash(t('tech_sheet.flat_import_error'))
    }
  }
  // ── F1 — Peces del patró vigent ────────────────────────────────────────────
  // El render del motor NO es pot clavar a `src`: l'endpoint va gated per Authorization i un
  // <img> no pot portar capçaleres (el mateix mur que els assets del .ftt). Es baixa amb
  // capçalera i s'encasta com a dataURL — exactament el que ja fa importarDelTenant.
  //
  // L'aspecte surt de l'SVG, no del bounding box de la peça: el render hi posa marges, i fer
  // servir el bbox deformaria el dibuix just per l'amplada d'aquest marge.
  const inserirPeca = async (peca) => {
    if (!locked || !patternFile) return
    try {
      // `fons=0` — X1. El render porta un rectangle de fons de sagnat complet (200000×200000)
      // que, com a IMATGE, el viewBox retallava i ningú veia. Vectoritzat ja no hi ha retall:
      // entrava com una forma BLANCA OPACA que tapava la pàgina sencera i feia semblar que
      // inserir una peça havia esborrat el document. Sobre la fitxa, una peça hi va
      // transparent; el fons només el vol qui l'ensenya com a imatge.
      const url = `${API}/api/v1/patterns/pattern-files/${patternFile.id}/render.svg/?piece=${encodeURIComponent(peca.nom_block)}&fons=0`
      const r = await fetch(url, { headers: uploadHeaders })
      if (!r.ok) throw new Error('http')
      const svgText = await r.text()
      const ratio = svgAspectRatio(svgText)
      if (!ratio) throw new Error('svg')
      const width = ratio >= PIECE_BOX_W / PIECE_BOX_H ? PIECE_BOX_W : PIECE_BOX_H * ratio
      // Blob → readAsDataURL dona un dataURL BASE64, que és el que el backend sap extreure a
      // asset (un dataURL amb `charset=utf-8` no li casa el patró i es quedaria inline).
      // R6 — LA PEÇA ENTRA COM A VECTOR, no com a imatge. El render del backend
      // (`patterns/svg.py:_path_data`) escriu NOMÉS `M … L … Z`: el DXF ja arriba aplanat a
      // punts i no hi ha ni una corba de Bézier per triangular. Per tant el pas a `path` és el
      // convertidor d'SVG que l'editor ja tenia, sense res a inventar: el color de traç per
      // capa DXF (tall, costura, piquets, fil) viatja sol perquè el conversor llegeix el
      // stroke de cada subpath, i els punts de gir/corba i els piquets, que a l'SVG són
      // circles i rects, els aplana `expandShapes`.
      // Guany: la peça es pot desagrupar, editar per nodes, pintar i escalar amb bake, com
      // qualsevol altre vector. Abans era un PNG dins un rectangle.
      // En cascada: dues peces seguides a la mateixa cantonada es tapen l'una a l'altra, i qui
      // n'insereix dues creu que n'hi ha una. Cada peça nova entra una mica més avall.
      const n = objectsOf(currentPage).filter(o => o.type === 'path' && o.piece_name).length
      const x = 20 + (n % 5) * 10, y = 20 + (n % 5) * 10
      const vector = await convertLegacySketchSvgObject({
        id: uid(), type: 'sketch_svg', layer: 'free', x, y, width, height: width / ratio, svg: svgText,
      })
      if (vector.type !== 'path') { flash(t('tech_sheet.piece_insert_error')); return }
      // `piece_name` i `pattern_file_id` es conserven: són la traça de d'on ve el dibuix, i
      // el descongelat de plantilla ja els sap despenjar (`_unfreeze_pattern_piece`).
      addObject({ ...vector, piece_name: peca.nom_block, pattern_file_id: patternFile.id })
    } catch {
      flash(t('tech_sheet.piece_insert_error'))
    }
  }

  // C4 — set tabs. `insert` portava 27 botons i `organize` 21: cap dels dos cabia en una fila
  // i tots dos barrejaven famílies. Es parteixen per allò que fa l'eina, no per omplir.
  const ribbonTabs = [
    { id: 'file', label: t('tech_sheet.ribbon_file') },
    { id: 'page', label: t('tech_sheet.ribbon_page') },
    { id: 'draw', label: t('tech_sheet.ribbon_draw') },
    { id: 'annot', label: t('tech_sheet.ribbon_annot') },
    { id: 'insert', label: t('tech_sheet.ribbon_insert') },
    { id: 'transform', label: t('tech_sheet.ribbon_transform') },
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
        ribbonTool({ key: 'template-mode', icon: 'ti-forms', label: t('tech_sheet.template_mode'), onClick: () => setTemplateMode(v => !v), active: templateMode, title: t('tech_sheet.template_mode_title'), disabled: !locked }),
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
    // C1+C4 — les eines de creació que vivien a la paleta vertical es reparteixen en tres
    // tabs per FAMÍLIA (dibuixar · anotar · inserir), no en una llista de 27. Allà eren icones
    // de 30 px sense etiqueta, amb flyouts de press-and-hold que n'amagaven dues de cada tres;
    // aquí són botons de 72×50 amb el nom escrit i totes visibles alhora.
    const eina = (k, icon, label) => ribbonTool({
      key: `t-${k}`, icon, label, onClick: () => setTool(k), active: tool === k, disabled: !locked,
    })
    if (ribbonGroup === 'draw') {
      return [
        eina('select', 'ti-pointer-2', t('tech_sheet.tool_select')),
        eina('pan', 'ti-hand-stop', t('tech_sheet.tool_pan')),
        <span key="sep-crea" style={ribbonSep} />,
        eina('draw', 'ti-pencil', t('tech_sheet.tool_draw')),
        eina('pen', 'ti-vector-bezier', t('tech_sheet.tool_pen')),
        eina('rect', 'ti-square', t('tech_sheet.tool_rect')),
        eina('rect_round', 'ti-square-rounded', t('tech_sheet.tool_rect_round')),
        eina('ellipse', 'ti-circle', t('tech_sheet.tool_ellipse')),
        eina('polygon', 'ti-hexagon', t('tech_sheet.tool_polygon')),
        <span key="sep-lin" style={ribbonSep} />,
        eina('line', 'ti-line', t('tech_sheet.tool_line')),
        eina('line_dot', 'ti-line-dashed', t('tech_sheet.tool_line_dot')),
        eina('arrow', 'ti-arrow-right', t('tech_sheet.tool_arrow')),
        eina('arrow2', 'ti-arrows-horizontal', t('tech_sheet.tool_arrow2')),
        eina('arrow_curve', 'ti-vector-spline', t('tech_sheet.tool_arrow_curve')),
      ]
    }
    if (ribbonGroup === 'annot') {
      return [
        eina('text', 'ti-text-recognition', t('tech_sheet.tool_text')),
        eina('text_box', 'ti-text-scan-2', t('tech_sheet.tool_text_box')),
        <span key="sep-cota" style={ribbonSep} />,
        eina('cota_pom', 'ti-ruler-measure', t('tech_sheet.tool_cota_pom')),
        eina('note', 'ti-arrow-guide', t('tech_sheet.tool_note')),
        // F3 · proposar cotes amb IA (decisió Agus: també aquí, no només al panell). Mateix handler.
        ribbonTool({ key: 'ia-cotes', icon: proposantIA ? 'ti-loader-2' : 'ti-sparkles',
          label: t('tech_sheet.ia_proposar'), onClick: proposarCotesIA,
          disabled: !locked || proposantIA || sketchObjs.length === 0 }),
        <span key="sep-pre" style={ribbonSep} />,
        eina('preset_callout', 'ti-message-2-share', t('tech_sheet.preset_callout')),
        eina('preset_detail_circle', 'ti-circle-dashed', t('tech_sheet.preset_detail_circle')),
        eina('preset_legend', 'ti-list-details', t('tech_sheet.preset_legend')),
      ]
    }
    // INSERIR es queda amb el que posa BLOCS al document (no eines de dibuix).
    if (ribbonGroup === 'insert') {
      return [
        ribbonTool({ key: 'header', icon: 'ti-layout-navbar', label: t('tech_sheet.model_header'), onClick: insertHeader }),
        ribbonTool({ key: 'logo', icon: 'ti-photo', label: t('tech_sheet.client_logo'), onClick: insertLogo, title: customerLogoUrl ? t('tech_sheet.insert_logo_title') : t('tech_sheet.no_logo_title') }),
        ribbonTool({ key: 'flat', icon: 'ti-vector', label: t('tech_sheet.flat_insert'), onClick: insertFlatSketch }),
        ribbonTool({ key: 'import-flat', icon: 'ti-file-import', label: t('tech_sheet.flat_import'), onClick: () => openImport('garment') }),
        ribbonTool({ key: 'image', icon: 'ti-photo-plus', label: t('tech_sheet.tool_image'), onClick: () => openImport('image') }),
        ribbonTool({ key: 'files', icon: 'ti-folder', label: t('tech_sheet.tool_files'), onClick: () => setFilePicker(true), disabled: !locked }),
      ]
    }
    // TRANSFORMAR — el que canvia la POSICIÓ RELATIVA d'objectes entre ells (alinear,
    // distribuir, mirall). Organitzar es queda amb el que canvia l'ESTRUCTURA (agrupar,
    // z-ordre, booleanes, eliminar). Abans eren 21 botons a la mateixa fila.
    if (ribbonGroup === 'transform') {
      return [
        ribbonTool({ key: 'align-left', icon: 'ti-layout-align-left', label: t('tech_sheet.align_left_short'), onClick: () => alignSelection('left'), disabled: nodeMode || selectedObjects.length < 2 }),
        ribbonTool({ key: 'align-center', icon: 'ti-layout-align-center', label: t('tech_sheet.align_center_short'), onClick: () => alignSelection('center'), disabled: nodeMode || selectedObjects.length < 2 }),
        ribbonTool({ key: 'align-right', icon: 'ti-layout-align-right', label: t('tech_sheet.align_right_short'), onClick: () => alignSelection('right'), disabled: nodeMode || selectedObjects.length < 2 }),
        ribbonTool({ key: 'align-top', icon: 'ti-layout-align-top', label: t('tech_sheet.align_top_short'), onClick: () => alignSelection('top'), disabled: nodeMode || selectedObjects.length < 2 }),
        ribbonTool({ key: 'align-middle', icon: 'ti-layout-align-middle', label: t('tech_sheet.align_middle_short'), onClick: () => alignSelection('middle'), disabled: nodeMode || selectedObjects.length < 2 }),
        ribbonTool({ key: 'align-bottom', icon: 'ti-layout-align-bottom', label: t('tech_sheet.align_bottom_short'), onClick: () => alignSelection('bottom'), disabled: nodeMode || selectedObjects.length < 2 }),
        <span key="sep-dist" style={ribbonSep} />,
        ribbonTool({ key: 'dist-h', icon: 'ti-layout-distribute-horizontal', label: t('tech_sheet.distribute_h_short'), onClick: () => distributeSelection('h'), disabled: nodeMode || selectedObjects.length < 3 }),
        ribbonTool({ key: 'dist-v', icon: 'ti-layout-distribute-vertical', label: t('tech_sheet.distribute_v_short'), onClick: () => distributeSelection('v'), disabled: nodeMode || selectedObjects.length < 3 }),
        <span key="sep-mir" style={ribbonSep} />,
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
    // ORGANITZAR — el que canvia l'ESTRUCTURA del document. Alinear, distribuir i mirall han
    // marxat a Transformar (C4): allà canvien la posició relativa, aquí l'estructura.
    return [
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
      <span key="sep-pathfinder" style={ribbonSep} />,
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
    : zoomModHeld ? (zoomOutMod ? 'zoom-out' : 'zoom-in')   // C1: modificador de zoom → lupa
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
        {/* C4 · les eines MAI fan scroll: si no caben, la fila creix. Un scroll horitzontal
            amaga eines darrere d'un gest que ningú fa, i el ribbon existeix justament per
            no haver d'anar a buscar res. Amb els tabs partits, el cas normal és una fila. */}
        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6, minHeight: 64, padding: '6px 12px 8px' }}>
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
        {/* ── C1 · ESQUERRA = BIBLIOTECA D'INSERCIÓ ──────────────────────────────────────────
            La paleta vertical d'eines ha desaparegut: eren icones de 30 px sense etiqueta amb
            flyouts que n'amagaven dues de cada tres, i les seves eines de creació viuen ara al
            tab Inserir del ribbon, totes visibles i amb el nom escrit.
            Aquesta columna passa a ser el que el llenç necessita a mà: QUÈ es pot posar al
            document. Mateixes persianes que el Taller de Patró (Contenidor compartit, capçalera
            fosca), perquè les dues pantalles s'assemblin de veritat i no per casualitat. */}
        {locked && (
          <aside style={{ width: 300, flexShrink: 0, display: 'flex', flexDirection: 'column', minHeight: 0, borderRight: `1px solid ${COL.border}`, background: 'var(--bg-page)' }}>
          {/* CONTENIDOR DE POMS. Calca la fila del Taller de Patró (ModelPomList): semàfor
              de borderLeft, codi de client en mono manant, nom canònic EN al costat, badge
              amb el nom_fitxa. És la primera persiana de la biblioteca i ve
              OBERTA: acotar és la feina que porta algú a obrir aquesta fitxa. Un clic arma l'eina de cota amb el text ja resolt. */}
          {/* El vell contenidor «Cotes des de precedent» (llista massiva per objecte + selects de
              vista) ha mort: exposava l'esquelet tècnic. La superfície de l'usuari és el panell de
              POMs (proposta per-POM), la vista viu a Propietats de l'objecte i «desar precedent» a
              Propietats de la cota. Vegeu DECISIÓ Agus 2026-07-26 (Patró C). */}

          {pomRows.length > 0 && (
            <Contenidor
              titol={t('tech_sheet.poms_of_model', { n: pomRows.length })}
              icona="ti-ruler-measure" pes={2}
            >
              <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, margin: '0 0 6px' }}>{t('tech_sheet.poms_hint')}</p>
              {/* Acció de grup: posar TOTES les proposables que encara no són al document. */}
              {proposablesCount > 0 && (
                <button type="button" onClick={posarTotesPropostes}
                  title={t('tech_sheet.pom_posar_totes', { n: proposablesCount })}
                  style={{ width: '100%', marginBottom: 6, cursor: 'pointer', padding: '0.35rem 0.5rem', background: COL.goldPale, border: `1px solid ${COL.gold}`, borderRadius: 4, color: COL.gold, fontFamily: FONT, fontSize: 'var(--fs-body)', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                  <i className="ti ti-copy" /> {t('tech_sheet.pom_posar_totes', { n: proposablesCount })}
                </button>
              )}
              {/* F3 · proposar cotes amb IA per als PENDENT (sobre els croquis de la pàgina). */}
              {sketchObjs.length > 0 && (
                <button type="button" onClick={proposarCotesIA} disabled={proposantIA}
                  title={t('tech_sheet.ia_proposar')}
                  style={{ width: '100%', marginBottom: 6, cursor: proposantIA ? 'default' : 'pointer', opacity: proposantIA ? 0.6 : 1, padding: '0.35rem 0.5rem', background: COL.bg, border: `1px solid ${COL.border}`, borderRadius: 4, color: COL.textMain, fontFamily: FONT, fontSize: 'var(--fs-body)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                  <i className={`ti ${proposantIA ? 'ti-loader-2' : 'ti-sparkles'}`} /> {proposantIA ? t('tech_sheet.ia_proposant') : t('tech_sheet.ia_proposar')}
                </button>
              )}
              {/* Barra de revisió de propostes IA vives (acceptar/descartar en bloc). */}
              {iaPropostesVives.length > 0 && (
                <div style={{ marginBottom: 6, padding: '0.35rem 0.5rem', background: COL.goldPale, border: `1px dashed ${COL.gold}`, borderRadius: 4 }}>
                  <p style={{ fontSize: 'var(--fs-caption)', color: COL.textMain, margin: '0 0 5px', fontWeight: 600 }}>{t('tech_sheet.ia_revisio', { n: iaPropostesVives.length })}</p>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button type="button" onClick={acceptarTotesPropostes} title={t('tech_sheet.ia_acceptar_totes')}
                      style={{ flex: 1, cursor: 'pointer', padding: '0.25rem', background: COL.bg, border: `1px solid ${COL.ok}`, borderRadius: 4, color: COL.ok, fontFamily: FONT, fontSize: 'var(--fs-label)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
                      <i className="ti ti-check" /> {t('tech_sheet.ia_acceptar_totes')}
                    </button>
                    <button type="button" onClick={descartarTotesPropostes} title={t('tech_sheet.ia_descartar_totes')}
                      style={{ flex: 1, cursor: 'pointer', padding: '0.25rem', background: COL.bg, border: `1px solid ${COL.border}`, borderRadius: 4, color: COL.textMuted, fontFamily: FONT, fontSize: 'var(--fs-label)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
                      <i className="ti ti-x" /> {t('tech_sheet.ia_descartar_totes')}
                    </button>
                  </div>
                </div>
              )}
              {f2Msg && <p style={{ fontSize: 'var(--fs-caption)', color: COL.textMain, margin: '0 0 6px' }}>{f2Msg}</p>}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {pomRows.map(bm => {
                  // F1 (cota viva): etiqueta = àlies de client || codi canònic; el vincle
                  // viatja per pom_id/bm_id, no pel text.
                  const etiqueta = cotaLabelDe(bm)
                  const esAlies = !!bm.client_alias
                  const canonic = bm.pom_code_global || ''
                  // NOMENCLATURA UNIFICADA — mateixa llei que l'etiqueta de la cota (F1: client_alias
                  // || canònic || codi_client, via cotaLabelDe) i que la taula de Mesures: la línia 1
                  // porta el CODI CLIENT + nom canònic EN (PomNamePair). El badge mostra el codi que
                  // NO és a la línia 1 — el canònic quan la línia porta client — mai un tercer
                  // vocabulari (el nom_fitxa del croquis ja no hi surt: no és nomenclatura de POM).
                  const canonicBadge = esAlies && canonic && canonic !== etiqueta ? canonic : ''
                  const colocat = bm.pom_id != null && cotesColocades.has(bm.pom_id)
                  const armat = cotaPreset?.bmId === bm.id && tool === 'cota_pom'
                  // PROPOSADA-IA: hi ha una cota de visió pendent de revisió per aquest POM.
                  const iaProp = !colocat && bm.pom_id != null && iaCotesByPom.has(bm.pom_id)
                  // PROPOSABLE (precedent): la cascada en té col·locació i la cota encara no hi és.
                  // Fiabilitat: exacte (precedent del mateix item) > germana (transposat).
                  const prop = !colocat && !iaProp && bm.pom_id != null ? propostes.get(bm.pom_id) : null
                  const exacte = prop && !prop.derivat
                  // Semàfor: col·locat (verd) · IA/proposable/armat (gold) · pendent (gris).
                  const accent = colocat ? COL.ok : (armat || iaProp || prop) ? COL.gold : COL.border
                  const stateIcon = colocat ? 'ti-circle-check' : armat ? 'ti-crosshair' : iaProp ? 'ti-sparkles' : prop ? 'ti-copy' : 'ti-circle-dashed'
                  const stateCol = colocat ? COL.ok : (armat || iaProp || prop) ? COL.gold : COL.textMuted
                  return (
                    <div key={bm.id} style={{ display: 'flex', alignItems: 'stretch', gap: 4 }}>
                      <button type="button"
                        // C3 · GUARD DE DUPLICATS: un POM amb cota viva al document no es pot
                        // re-acotar. La fila COL·LOCAT queda no-clicable (el «selector» de l'eina
                        // Cota POM l'exclou); esborrar la cota el torna PENDENT/PROPOSABLE. No es fa
                        // servir `disabled` per no perdre el tooltip explicatiu (Chrome l'amaga en
                        // botons disabled): click a buit + cursor per defecte.
                        onClick={colocat ? undefined : () => { setCotaPreset({ text: etiqueta, pomId: bm.pom_id, bmId: bm.id, canonical: canonic }); setTool('cota_pom') }}
                        aria-pressed={armat}
                        title={colocat
                          ? t('tech_sheet.pom_cota_ja_colocat')
                          : esAlies && canonic
                            ? `${t('tech_sheet.pom_cota_hint', { nom: etiqueta })} · ${t('tech_sheet.pom_canonical_tip', { codi: canonic })}`
                            : t('tech_sheet.pom_cota_hint', { nom: etiqueta })}
                        style={{
                          textAlign: 'left', flex: 1, minWidth: 0, cursor: colocat ? 'default' : 'pointer',
                          background: armat ? 'var(--gold-pale)' : 'var(--bg-card)',
                          border: `1px solid ${armat ? COL.gold : COL.border}`,
                          borderLeft: `3px solid ${accent}`,
                          borderRadius: 4, padding: '0.3rem 0.5rem',
                          display: 'flex', alignItems: 'center', gap: '0.4rem',
                          fontFamily: FONT,
                        }}>
                        <i className={`ti ${stateIcon}`} style={{ color: stateCol, flexShrink: 0, fontSize: 14 }} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.3rem', fontSize: 'var(--fs-body)', fontWeight: 600 }}>
                            <span>{etiqueta || bm.codi_client}</span>
                            <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              <PomNamePair en={bm.nom_en} local={bm.nom_ca || bm.nom_client} />
                            </span>
                            {/* Badge PROPOSADA-IA (pendent de revisió): distint d'exacte/germana. */}
                            {iaProp && (
                              <span title={t('tech_sheet.ia_badge_tip')}
                                style={{ fontSize: 'var(--fs-caption)', fontWeight: 500, color: COL.gold, border: `1px solid ${COL.gold}`, borderRadius: 8, padding: '0 5px', flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                                <i className="ti ti-sparkles" style={{ fontSize: 11 }} />{t('tech_sheet.ia_badge')}
                              </span>
                            )}
                            {/* Badge de fiabilitat DISCRET (mai percentatge): exacte vs germana. */}
                            {prop && (
                              <span title={t(exacte ? 'tech_sheet.pom_rel_exacte_tip' : 'tech_sheet.pom_rel_germana_tip')}
                                style={{ fontSize: 'var(--fs-caption)', fontWeight: 500, color: exacte ? COL.gold : COL.textMuted, border: `1px solid ${exacte ? COL.gold : COL.border}`, borderRadius: 8, padding: '0 5px', flexShrink: 0 }}>
                                {t(exacte ? 'tech_sheet.pom_rel_exacte' : 'tech_sheet.pom_rel_germana')}
                              </span>
                            )}
                            {/* Badge = codi CANÒNIC (l'altre codi), només quan la línia 1 porta el
                                client. Mai el nom_fitxa (nomenclatura del croquis, no del POM). */}
                            {canonicBadge && (
                              <span title={t('tech_sheet.pom_canonical_tip', { codi: canonicBadge })}
                                style={{ fontSize: 'var(--fs-caption)', fontWeight: 400, color: COL.textMuted, border: `1px solid ${COL.border}`, borderRadius: 8, padding: '0 5px', flexShrink: 0 }}>
                                {canonicBadge}
                              </span>
                            )}
                          </div>
                        </div>
                        {/* La xifra no es tenyeix mai: el color el porta el semàfor de l'esquerra. */}
                        {bm.base_value_cm != null && (
                          <span style={{ fontSize: 'var(--fs-label)', color: COL.textMain, flexShrink: 0 }}>{bm.base_value_cm}</span>
                        )}
                      </button>
                      {/* «Posar»: col·loca LA cota des del precedent (queda viva F1, arrossegable). */}
                      {prop && (
                        <button type="button" onClick={() => posarProposta(bm.pom_id)}
                          title={t('tech_sheet.pom_posar')}
                          style={{ flexShrink: 0, width: 32, cursor: 'pointer', border: `1px solid ${COL.gold}`, borderRadius: 4, background: COL.goldPale, color: COL.gold, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <i className="ti ti-copy" style={{ fontSize: 15 }} />
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
            </Contenidor>
          )}
            <Contenidor titol={t('tech_sheet.lib_sketches', { n: fitxersSketch.length })} icona="ti-vector" defaultOpen={false} pes={1}>
              {fitxersSketch.length === 0
                ? <p style={libEmpty}>{t('tech_sheet.lib_sketches_empty')}</p>
                : fitxersSketch.map(f => (
                  <button key={f.id} type="button" onClick={() => addModelFitxer(f)} title={f.nom_fitxer} style={libRow}>
                    <i className="ti ti-vector" style={libIcon} />
                    <span style={libName}>{f.nom_fitxer}</span>
                  </button>
                ))}
            </Contenidor>

            {/* R3 — les quatre variants són ÍTEMS DIRECTES, no un popup que et pregunta què
                vols abans de deixar-te veure què hi ha. La que el model no pot servir es veu
                igualment, en fade i dient per què: una opció que desapareix no s'aprèn. */}
            <Contenidor titol={t('tech_sheet.lib_tables')} icona="ti-table" defaultOpen={false} pes={1}>
              {TABLE_VARIANTS.map(v => (
                <button key={v.k} type="button" disabled={!v.ok}
                  onClick={() => onPickTableVariant(v.k)}
                  title={v.ok ? t('tech_sheet.lib_table_insert', { nom: v.label }) : v.motiu}
                  style={{ ...libRow, opacity: v.ok ? 1 : 0.45, cursor: v.ok ? 'pointer' : 'default' }}>
                  <i className={`ti ${v.icon}`} style={libIcon} />
                  <span style={libName}>{v.label}</span>
                </button>
              ))}
            </Contenidor>

            <Contenidor titol={t('tech_sheet.lib_files', { n: fitxersAltres.length })} icona="ti-folder" defaultOpen={false} pes={1}>
              {fitxersAltres.length === 0
                ? <p style={libEmpty}>{t('tech_sheet.lib_files_none_insertable')}</p>
                : fitxersAltres.map(f => (
                  <button key={f.id} type="button" onClick={() => addModelFitxer(f)} title={f.nom_fitxer} style={libRow}>
                    <i className="ti ti-file" style={libIcon} />
                    <span style={libName}>{f.nom_fitxer}</span>
                  </button>
                ))}
              <button type="button" onClick={() => setFilePicker(true)} style={{ ...libRow, border: `1.5px dashed ${COL.border}`, marginTop: 4 }}>
                <i className="ti ti-folder-search" style={libIcon} />
                <span style={libName}>{t('tech_sheet.tool_files')}</span>
              </button>
            </Contenidor>

            {/* Y1 — les peces es llisten AQUÍ, com les taules i els arxius: un ítem per peça,
                amb el seu nom i la seva mida, i el clic la insereix. El popup que hi havia al
                mig no decidia res —ensenyava la mateixa llista i el mateix clic—, només
                afegia un pas. Sense patró, o amb un patró sense peces, la persiana s'obre
                igualment i diu per què és buida. */}
            <Contenidor titol={t('tech_sheet.lib_pieces')} icona="ti-shirt" defaultOpen={false} pes={1}>
              {!patternFile ? <p style={libEmpty}>{t('tech_sheet.piece_no_pattern')}</p>
                : peces.loading ? <p style={libEmpty}>{t('app.loading')}</p>
                  : peces.error ? <p style={libEmpty}>{t('tech_sheet.piece_insert_error')}</p>
                    : !peces.pieces?.length ? <p style={libEmpty}>{t('tech_sheet.lib_pieces_none')}</p>
                      : peces.pieces.map(p => (
                        <button key={p.id} type="button" onClick={() => inserirPeca(p)} title={p.nom_block} style={libRow}>
                          <i className="ti ti-shirt" style={libIcon} />
                          <span style={libName}>{p.nom_block}</span>
                          {p.bounding_box_mm && (
                            <span style={libMeta}>
                              {Math.round(p.bounding_box_mm.ample)} × {Math.round(p.bounding_box_mm.alt)} mm
                            </span>
                          )}
                        </button>
                      ))}
            </Contenidor>
          </aside>
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
                    onEndpointDrag={handleEndpointDrag(o)}
                    onCotaEndpointDrag={handleCotaEndpointDrag(o)}
                    onCotaLabelDrag={handleCotaLabelDrag(o)} />
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
                {/* C1: filet fi per membre en multiselecció (>1) — a més del marc del Transformer.
                    Overlay del render VIU, per bounds (getClientRect); MAI a l'export ni al .ftt. */}
                {multiOutlines.map(b => (
                  <Rect key={'sel-' + b.id} x={b.x} y={b.y} width={b.w} height={b.h}
                    stroke={KONVA_COL.gold} strokeWidth={1} strokeScaleEnabled={false} listening={false} />
                ))}
                <Transformer ref={trRef} rotateEnabled ignoreStroke keepRatio={shiftHeld || (selectedObjects.length === 1 && (selObj?.type === 'data_block' || selObj?.type === 'table' || selObj?.type === 'pattern_piece'))}
                  rotationSnaps={shiftHeld ? ROT_SNAPS : SENSE_SNAP} rotationSnapTolerance={ROT_SNAP_TOL}
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
          {/* C2 — CAP TAB INTERN. El dock tenia una tira de pestanyes (Propietats · Capes ·
              Camps) que amagava dues terceres parts del panell darrere d'un clic i obligava a
              recordar on era cada cosa. Ara tot són PERSIANES del mateix Contenidor compartit,
              com a l'esquerra i com al Taller: una gramàtica de zones, no tres. */}
          {/* padding inferior extra: clearança per als botons flotants de Chrome (IA/cerca) */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 10px 64px' }}>
            {/* PÀGINES (C2) — abans una tira inferior horitzontal; ara una persiana del dock,
                la mateixa gramàtica de zones que Capes/Camps (D2). Miniatures VERTICALS, pàgina
                activa marcada, +afegeix i esborrar. Cap lògica nova: reutilitza els handlers
                existents (setCurrentPage/clearSelection/addPage/removePage). El plegat es recorda
                mentre l'editor viu (estat intern del Contenidor), com a la resta de persianes. */}
            <Contenidor titol={t('tech_sheet.dock_pages')} icona="ti-files" defaultOpen fitContent>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {pages.map((p, i) => (
                  <div key={p.id} onClick={() => { setCurrentPage(i); clearSelection() }}
                    title={t('tech_sheet.page_n', { n: i + 1 })}
                    style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 8, padding: 5, borderRadius: 5, cursor: 'pointer', background: currentPage === i ? COL.goldPale : 'transparent', border: `1px solid ${currentPage === i ? COL.gold : COL.border}` }}>
                    <div style={{ width: 48, height: 34, flexShrink: 0, borderRadius: 3, overflow: 'hidden', background: 'var(--white)', border: `1px solid ${COL.border}` }}>
                      {thumbnails[i] && <img src={thumbnails[i]} alt={t('tech_sheet.page_n', { n: i + 1 })} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} />}
                    </div>
                    <span style={{ flex: 1, fontSize: 'var(--fs-label)', color: currentPage === i ? COL.gold : COL.textMain, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t('tech_sheet.page_n', { n: i + 1 })}</span>
                    {locked && pages.length > 1 && (
                      <button onClick={(e) => { e.stopPropagation(); removePage(i) }} title={t('tech_sheet.delete_page')}
                        style={{ flexShrink: 0, border: 'none', background: 'transparent', color: COL.textMuted, cursor: 'pointer', padding: 0, lineHeight: 1 }}><i className="ti ti-trash" style={{ fontSize: 14 }} /></button>
                    )}
                  </div>
                ))}
                {locked && (
                  <button onClick={addPage} title={t('tech_sheet.add_page')}
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, width: '100%', padding: '7px 8px', border: `1px dashed ${COL.gold}`, borderRadius: 5, background: 'transparent', color: COL.gold, fontFamily: FONT, fontSize: 'var(--fs-label)', cursor: 'pointer' }}>
                    <i className="ti ti-plus" style={{ fontSize: 14 }} /><span>{t('tech_sheet.add_page')}</span>
                  </button>
                )}
              </div>
            </Contenidor>

            {/* CAPES — llista d'objectes de la pàgina (front a dalt) + z-order. */}
            <Contenidor titol={t('tech_sheet.dock_layers')} icona="ti-stack-2" defaultOpen={false} fitContent>
            {(ordered.length === 0 ? (
              <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, margin: '0 0 8px' }}>{t('tech_sheet.layers_empty')}</p>
            ) : (
              <div style={{ marginBottom: 8, border: `1px solid ${COL.border}`, borderRadius: 5, overflow: 'hidden' }}>
                {[...ordered].reverse().map(o => {
                  const on = selectedIds.includes(o.id)
                  const icon = (o.piece_name ? 'ti-shirt' : { text: 'ti-cursor-text', rect: 'ti-square', ellipse: 'ti-circle', line: 'ti-minus', arrow: 'ti-arrow-right', image: 'ti-photo', path: 'ti-vector', sketch_svg: 'ti-vector', pattern_piece: 'ti-shirt', data_block: 'ti-table', group: 'ti-box-multiple', field: 'ti-forms' }[o.type] || 'ti-shape')
                  // R6 — una peça vectoritzada és un `path` amb `piece_name`: la llista ha de dir com es diu la peça, no "path".
                  const label = o.type === 'text' ? (o.text || t('tech_sheet.tool_text')) : o.type === 'field' ? (o.label || o.type) : (o.piece_name || o.type)
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
            </Contenidor>

            {/* input SVG sempre muntat: el referencien el ribbon (Inserir) i el panell de selecció */}
            <input ref={flatFileRef} type="file" accept=".svg,image/svg+xml" hidden
              onChange={e => { const f = e.target.files[0]; e.target.value = ''; handleFlatSvgFile(f) }} />

            {/* TAB PROPIETATS: propietats de la selecció (W/H/X/Y, stroke/fill, …). Els blocs
                d'inserció i de fitxers del model viuen ara al ribbon (pestanya Inserir). */}
            {!multiSelected && !selObj && (
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
            {multiSelected && locked && (
              <>
                <SectionTitle>{t('tech_sheet.selected_objects', { n: selectedObjects.length })}</SectionTitle>
                {multiStroke.length > 0 && (
                  <>
                    <div style={propLabel}>{t('tech_sheet.stroke_color')}
                      {!multiStrokeValue && <span style={{ display: 'block', color: COL.textMuted, marginTop: 2 }}>{t('tech_sheet.mixed_values')}</span>}
                      <ColorPicker docColors={docPalette} value={multiStrokeValue || KONVA_COL.textMain}
                        onChange={c => updateObjects(multiStroke.map(o => o.id), o => applyPaintTree(o, { stroke: c }))} />
                    </div>
                    {/* S3 · gruix comú: buit si difereixen (placeholder «—»), s'escriu només en tocar-lo. */}
                    <label style={propLabel}>{t('tech_sheet.stroke_width')}
                      <input type="number" min={0.1} max={5} step={0.1}
                        value={multiStrokeWValue === '' ? '' : Math.round(Number(multiStrokeWValue) * 10) / 10}
                        placeholder={t('tech_sheet.mixed_values')}
                        onChange={e => { const n = Number(e.target.value)
                          if (e.target.value === '' || !Number.isFinite(n)) return
                          updateObjects(multiStroke.map(o => o.id), o => applyPaintTree(o, { strokeWidth: Math.max(0, n) })) }} style={propInput} />
                    </label>
                  </>
                )}
                {multiFill.length > 0 && (
                  <div style={propLabel}>{t('tech_sheet.fill')}
                    {!multiFillValue && <span style={{ display: 'block', color: COL.textMuted, marginTop: 2 }}>{t('tech_sheet.mixed_values')}</span>}
                    <ColorPicker docColors={docPalette} value={multiFillValue || KONVA_COL.white}
                      onChange={c => updateObjects(multiFill.map(o => o.id), o => applyPaintTree(o, { fill: c }))} />
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
                {/* F2 · vista de l'objecte sketch de catàleg (view_slot). Abans vivia en una llista
                    massiva al panell esquerre; ara és un camp discret aquí, on es toca l'objecte. */}
                {isSketchObj(selObj) && selObj.sourceItemFitxer && (
                  <Contenidor titol={t('tech_sheet.sketch_view')} icona="ti-arrow-guide" fitContent>
                    <datalist id="sketch-view-slots"><option value="front" /><option value="back" /><option value="detail" /></datalist>
                    <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, margin: '0 0 4px' }}>{t('tech_sheet.sketch_view_hint')}</p>
                    <input list="sketch-view-slots" value={selObj.viewSlot || ''} placeholder={t('tech_sheet.sketch_view_ph')}
                      onChange={e => assignaVista(selObj.id, e.target.value.trim())} style={propInput} />
                  </Contenidor>
                )}
                {/* F3 · revisió d'una cota PROPOSADA per la IA: acceptar (→ cota viva) o descartar.
                    Es poden ajustar els extrems abans d'acceptar (ja és un objecte manipulable). */}
                {selObj.type === 'group' && selObj.pomId != null && selObj.iaProposada && (
                  <Contenidor titol={t('tech_sheet.ia_cota_titol')} icona="ti-sparkles" fitContent>
                    <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, margin: '0 0 6px' }}>{t('tech_sheet.ia_cota_hint')}</p>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button type="button" onClick={() => acceptarProposta(selObj)}
                        style={{ flex: 1, cursor: 'pointer', padding: '0.35rem', background: COL.bg, border: `1px solid ${COL.ok}`, borderRadius: 4, color: COL.ok, fontFamily: FONT, fontSize: 'var(--fs-body)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
                        <i className="ti ti-check" /> {t('tech_sheet.ia_acceptar')}
                      </button>
                      <button type="button" onClick={() => descartarProposta(selObj.id)}
                        style={{ flex: 1, cursor: 'pointer', padding: '0.35rem', background: COL.bg, border: `1px solid ${COL.border}`, borderRadius: 4, color: COL.textMuted, fontFamily: FONT, fontSize: 'var(--fs-body)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
                        <i className="ti ti-x" /> {t('tech_sheet.ia_descartar')}
                      </button>
                    </div>
                  </Contenidor>
                )}
                {/* F2 · desar AQUESTA cota com a precedent del catàleg (acte conscient, D1). Una cota
                    encara PROPOSADA no es pot desar com a precedent: primer s'accepta. */}
                {selObj.type === 'group' && selObj.pomId != null && !selObj.iaProposada && (
                  <Contenidor titol={t('tech_sheet.cota_precedent')} icona="ti-bookmark" fitContent>
                    <p style={{ fontSize: 'var(--fs-label)', color: COL.textMuted, margin: '0 0 4px' }}>{t('tech_sheet.cota_precedent_hint')}</p>
                    <button type="button" onClick={() => desarUnaPrecedent(selObj)}
                      style={{ width: '100%', cursor: 'pointer', padding: '0.35rem 0.5rem', background: COL.bg, border: `1px solid ${COL.border}`, borderRadius: 4, fontFamily: FONT, fontSize: 'var(--fs-body)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                      <i className="ti ti-bookmark" /> {t('tech_sheet.cota_desar_precedent')}
                    </button>
                    {f2Msg && <p style={{ fontSize: 'var(--fs-caption)', color: COL.textMain, margin: '4px 0 0' }}>{f2Msg}</p>}
                  </Contenidor>
                )}
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
                        value={(pinturaViva ? pinturaViva.stroke : resolStroke(shapeObj, shapeObj.paths?.[subActive ?? 0])) || KONVA_COL.textMain}
                        onChange={c => { if (pintaStroke(c)) return
                          pintaShape({ stroke: c, ...(shapeObj.type === 'arrow' ? { fill: c } : {}) }) }} />
                    </div>
                    <label style={propLabel}>{t('tech_sheet.stroke_width')}
                      <input type="number" min={0.1} max={5} step={0.1}
                        value={pinturaViva ? pinturaViva.strokeWidth
                          : shapeObj.type === 'path' ? resolStrokeWidth(shapeObj, shapeObj.paths?.[subActive ?? 0])
                            /* rect/ellipse/line/arrow no tenen subpaths i cadascun porta el seu
                               propi valor per defecte al render (rectProps/lineProps/arrowProps). */
                            : (shapeObj.strokeWidth || (shapeObj.type === 'arrow' ? 1.5 : 1))}
                        onChange={e => { if (pintaStrokeWidth(e.target.value)) return
                          const n = Number(e.target.value)
                          if (e.target.value === '' || !Number.isFinite(n)) return
                          pintaShape({ strokeWidth: Math.max(0, n) }) }} style={propInput} />
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
                  </Contenidor>
                )}
                {(selObj.type === 'rect' || selObj.type === 'ellipse' || selObj.type === 'path') && (
                  <Contenidor titol={t('tech_sheet.sec_fill')} icona="ti-color-swatch" fitContent>
                    <div style={propLabel}>{t('tech_sheet.fill')}
                      <ColorPicker
                        value={(pinturaViva ? pinturaViva.fill : resolFill(selObj, selObj.paths?.[subActive ?? 0])) || KONVA_COL.white}
                        onChange={c => { if (pintaFill(c)) return
                          updateObject(selObj.id, subActive != null && Array.isArray(selObj.paths)
                            ? patchSubpath(selObj, subActive, { fill: c })
                            : patchPintura(selObj, { fill: c })) }} />
                    </div>
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
            {/* CAMPS (S5-1): catàleg clicable → insereix un xip {label} a (20,20)mm. Es resol
                server-side en instanciar un document des de la plantilla. Només en mode
                plantilla: un xip {camp} dins un document normal no significa res i el PDF
                l'imprimiria literalment. */}
            {locked && templateMode && (
              <Contenidor titol={t('tech_sheet.dock_fields')} icona="ti-forms" defaultOpen={false} fitContent>
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
              </Contenidor>
            )}
          </div>
          </>)}
        </aside>
      </main>

      {/* Tira de pàgines horitzontal retirada (C2): les pàgines viuen ara a la persiana
          PÀGINES del dock dret. No es duplica l'afordança. */}

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
      {/* R3 — d'aquest modal només en queda el TRIA-FITTING: apareix quan el model té més d'un
          SizeFitting i cal saber de quin es fa la taula. El menú de variants ha marxat a la
          persiana TAULES de la biblioteca, i la personalitzada s'insereix directament. */}
      {tablePicker?.variant && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }} onClick={() => setTablePicker(null)}>
          <div onClick={e => e.stopPropagation()} style={{ background: COL.bg, borderRadius: 12, padding: '1.4rem', maxWidth: 360, width: '90%', fontFamily: FONT, border: `1px solid ${COL.border}` }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 12 }}>{t('tech_sheet.table_pick_fitting')}</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {sizeFittings.map(sf => (
                <button key={sf.id} type="button" onClick={() => runTableVariant(tablePicker.variant, sf.id)}
                  style={{ textAlign: 'left', fontSize: 'var(--fs-body)', padding: '8px 10px', border: `1px solid ${COL.border}`, borderRadius: 6, background: COL.field, color: COL.textMain, fontFamily: FONT, cursor: 'pointer' }}>
                  {sf.codi || sf.nom || sf.talla_base || `#${sf.id}`}{sf.tipus ? ` · ${sf.tipus}` : ''}
                </button>
              ))}
            </div>
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
// C1 — fila de la biblioteca d'inserció: mateixa geometria que la fila de POM (radi 4, filet
// subtil) perquè les cinc persianes es llegeixin com una sola llista i no com cinc widgets.
const libRow = { display: 'flex', alignItems: 'center', gap: 6, width: '100%', textAlign: 'left', padding: '0.3rem 0.5rem', marginBottom: 3, border: `1px solid ${COL.border}`, borderRadius: 4, background: 'var(--bg-card)', color: COL.textMain, fontFamily: FONT, fontSize: 'var(--fs-label)', cursor: 'pointer' }
const libIcon = { fontSize: 14, color: COL.gold, flexShrink: 0 }
const libName = { flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }
// Y1 — la mida de la peça: dada secundària a la mateixa fila, sense robar-li el nom.
const libMeta = { flexShrink: 0, color: COL.textMuted, fontSize: 'var(--fs-caption)' }
const libEmpty = { fontSize: 'var(--fs-caption)', color: COL.textMuted, margin: '0 0 6px' }
export const propInput = { width: '100%', fontFamily: FONT, fontSize: 'var(--fs-body)', padding: '4px 6px', marginTop: 3, border: `1px solid ${COL.border}`, borderRadius: 6, background: COL.field, color: COL.textMain, boxSizing: 'border-box' }
