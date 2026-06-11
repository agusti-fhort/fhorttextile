import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { Stage, Layer, Rect, Text, Line, Image as KonvaImage, Transformer, Group } from 'react-konva'
import Konva from 'konva'
import { PDFDocument } from 'pdf-lib'

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
const MM_TO_PX = 2.4
const A4_W_MM = 297
const A4_H_MM = 210
const CANVAS_W = Math.round(A4_W_MM * MM_TO_PX)   // 713
const CANVAS_H = Math.round(A4_H_MM * MM_TO_PX)   // 504
// A4 horitzontal en punts PostScript (pdf-lib).
const PDF_W_PT = 841.89
const PDF_H_PT = 595.28

const FONT = 'IBM Plex Mono, monospace'
const COL = {
  sidebar: '#f0dfc0', gold: '#c27a2a', goldPale: '#f5e6d0',
  border: '#e0d5c5', textMain: '#1d1d1b', textMuted: '#868685', bg: '#f5f0e8',
}

const LAYER_ORDER = { template: 0, data: 1, free: 2 }
const uid = () => (crypto.randomUUID ? crypto.randomUUID() : `id-${Math.round(performance.now())}-${Math.floor(Math.random() * 1e9)}`)
const toPx = (mm) => mm * MM_TO_PX
const toMm = (px) => px / MM_TO_PX

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
const T_ROW_H = 14 * MM_TO_PX
const T_HDR_H = 16 * MM_TO_PX
const T_FONT = Math.round(6.5 * MM_TO_PX)
const T_REF_W = 28 * MM_TO_PX
const T_NAME_W = 52 * MM_TO_PX
const T_NOM_W = 52 * MM_TO_PX
const T_VAL_W = 20 * MM_TO_PX
const T_PAD = 2 * MM_TO_PX
const TBL = {
  HDR_BG: '#111827', HDR_TEXT: '#ffffff', ROW_EVEN: '#ffffff', ROW_ODD: '#f7f7f7',
  ROW_BORDER: '#e0d5c5', OUTER: '#c27a2a', REF: '#dc2626', NOM: '#6b7280', VAL: '#1d1d1b',
}

// graded-table JSON → {prims, totalW, totalH}. Camps reals: size_labels / rows[{codi,
// abbreviation,nom_en,nom_ca,valors}]. (NO sizes/base_size/is_base — no existeixen.)
function buildTablePrimitives(d) {
  const sizes = d?.size_labels || []
  const rows = d?.rows || []
  const totalW = T_REF_W + T_NAME_W + T_NOM_W + sizes.length * T_VAL_W
  const totalH = T_HDR_H + rows.length * T_ROW_H
  const valX0 = T_REF_W + T_NAME_W + T_NOM_W
  const prims = []
  // Capçalera
  prims.push({ t: 'r', x: 0, y: 0, w: totalW, h: T_HDR_H, fill: TBL.HDR_BG })
  prims.push({ t: 't', x: 0, y: 0, w: T_REF_W, h: T_HDR_H, text: 'REF', fill: TBL.HDR_TEXT, size: T_FONT, align: 'center', mid: true })
  prims.push({ t: 't', x: T_REF_W + T_PAD, y: 0, w: T_NAME_W - T_PAD, h: T_HDR_H, text: 'Name (EN)', fill: TBL.HDR_TEXT, size: T_FONT, mid: true })
  prims.push({ t: 't', x: T_REF_W + T_NAME_W + T_PAD, y: 0, w: T_NOM_W - T_PAD, h: T_HDR_H, text: 'Nom (CA)', fill: TBL.HDR_TEXT, size: T_FONT, mid: true })
  sizes.forEach((sl, si) => prims.push({ t: 't', x: valX0 + si * T_VAL_W, y: 0, w: T_VAL_W, h: T_HDR_H, text: sl, fill: TBL.HDR_TEXT, size: T_FONT, align: 'center', mid: true }))
  // Files
  rows.forEach((row, ri) => {
    const y = T_HDR_H + ri * T_ROW_H
    prims.push({ t: 'r', x: 0, y, w: totalW, h: T_ROW_H, fill: ri % 2 === 0 ? TBL.ROW_EVEN : TBL.ROW_ODD })
    const ref = [row.abbreviation, row.codi].filter(Boolean).join(' ') || row.codi || ''
    prims.push({ t: 't', x: 0, y, w: T_REF_W, h: T_ROW_H, text: ref, fill: TBL.REF, size: T_FONT, bold: true, align: 'center', mid: true })
    prims.push({ t: 't', x: T_REF_W + T_PAD, y, w: T_NAME_W - T_PAD, h: T_ROW_H, text: row.nom_en || '', fill: TBL.VAL, size: T_FONT, mid: true })
    prims.push({ t: 't', x: T_REF_W + T_NAME_W + T_PAD, y, w: T_NOM_W - T_PAD, h: T_ROW_H, text: row.nom_ca || '', fill: TBL.NOM, size: T_FONT, italic: true, mid: true })
    sizes.forEach((sl, si) => {
      const v = row.valors?.[sl]
      prims.push({ t: 't', x: valX0 + si * T_VAL_W, y, w: T_VAL_W, h: T_ROW_H, text: v != null ? String(v) : '–', fill: TBL.VAL, size: T_FONT, align: 'center', mid: true })
    })
    prims.push({ t: 'l', points: [0, y + T_ROW_H, totalW, y + T_ROW_H], stroke: TBL.ROW_BORDER, sw: 0.5 })
  })
  // Separadors verticals + vora exterior
  let cx = T_REF_W
  ;[T_NAME_W, T_NOM_W, ...sizes.map(() => T_VAL_W)].forEach(w => {
    prims.push({ t: 'l', points: [cx, 0, cx, totalH], stroke: TBL.ROW_BORDER, sw: 0.5 }); cx += w
  })
  prims.push({ t: 'r', x: 0, y: 0, w: totalW, h: totalH, stroke: TBL.OUTER, sw: 1.5 })
  return { prims, totalW, totalH }
}

// Capçalera del model → {prims, totalW, totalH}. Dues bandes (20mm + 12mm), 277mm d'ample.
function buildHeaderPrimitives(m, versio) {
  const W = 277 * MM_TO_PX
  const B1 = 20 * MM_TO_PX, B2 = 12 * MM_TO_PX
  const totalH = B1 + B2
  const PAD = 2 * MM_TO_PX
  const prims = []
  prims.push({ t: 'r', x: 0, y: 0, w: W, h: B1, fill: '#f5e6d0', stroke: '#c27a2a', sw: 1 })
  prims.push({ t: 't', x: PAD, y: 0, w: W * 0.4 - PAD, h: B1, text: [m?.codi_intern, m?.nom_prenda].filter(Boolean).join(' · '), fill: '#1d1d1b', size: Math.round(9 * MM_TO_PX), bold: true, mid: true })
  prims.push({ t: 't', x: W * 0.4, y: 0, w: W * 0.42, h: B1, text: [m?.customer_nom, m?.temporada, m?.collection].filter(Boolean).join(' · '), fill: '#1d1d1b', size: Math.round(7 * MM_TO_PX), align: 'center', mid: true })
  prims.push({ t: 't', x: W * 0.82, y: 0, w: W * 0.18 - PAD, h: B1, text: '(logo)', fill: '#868685', size: Math.round(7 * MM_TO_PX), align: 'right', mid: true })
  prims.push({ t: 'r', x: 0, y: B1, w: W, h: B2, fill: '#fafafa', stroke: '#e0d5c5', sw: 1 })
  const line2 = [m?.garment_type_item_nom, m?.size_system_nom, m?.responsable_nom, `v${versio ?? 1}`].filter(Boolean).join(' · ')
  prims.push({ t: 't', x: PAD, y: B1, w: W - 2 * PAD, h: B2, text: line2, fill: '#6b7280', size: Math.round(6.5 * MM_TO_PX), mid: true })
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

// Capçalera del model — Konva natiu. Resol els camps del model en render (sempre fresc).
function HeaderBlock({ modelData, versio, groupProps, isSelected }) {
  const { prims, totalW, totalH } = useMemo(() => buildHeaderPrimitives(modelData, versio), [modelData, versio])
  return (
    <Group {...groupProps}>
      {prims.map((p, i) => <PrimNode key={i} p={p} />)}
      {isSelected && <Rect x={0} y={0} width={totalW} height={totalH} stroke="#c27a2a" strokeWidth={2} dash={[4, 3]} fill="transparent" listening={false} />}
    </Group>
  )
}

// ─── Render offscreen d'una pàgina a dataURL (export PDF + miniatures) ───
// ctx = { tableData:{objId:json}, modelData, versio }. Dibuixa els blocs de dades
// natius amb les mateixes primitives que el canvas viu (cap PNG congelat).
async function renderPageToDataURL(page, pixelRatio, ctx) {
  const container = document.createElement('div')
  const stage = new Konva.Stage({ container, width: CANVAS_W, height: CANVAS_H })
  const layer = new Konva.Layer()
  stage.add(layer)
  layer.add(new Konva.Rect({ x: 0, y: 0, width: CANVAS_W, height: CANVAS_H, fill: '#ffffff' }))
  const ordered = [...(page.objects || [])].sort(
    (a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
  for (const o of ordered) {
    if (o.type === 'text') {
      layer.add(new Konva.Text({
        x: toPx(o.x), y: toPx(o.y), width: o.width ? toPx(o.width) : undefined,
        text: o.text || '', fontSize: o.fontSize || 11, fontFamily: o.fontFamily || FONT,
        fill: o.fill || COL.textMain,
      }))
    } else if (o.type === 'rect') {
      layer.add(new Konva.Rect({
        x: toPx(o.x), y: toPx(o.y), width: toPx(o.width), height: toPx(o.height),
        fill: o.fill && o.fill !== 'transparent' ? o.fill : undefined,
        stroke: o.stroke || COL.gold, strokeWidth: o.strokeWidth || 1,
      }))
    } else if (o.type === 'line') {
      layer.add(new Konva.Line({
        points: (o.points || []).map(toPx), stroke: o.stroke || COL.textMain,
        strokeWidth: o.strokeWidth || 1, lineCap: 'round', lineJoin: 'round',
      }))
    } else if (o.type === 'data_block') {
      // Blocs vius natius: mateixes primitives que el canvas. Group posicionat en px.
      let built = null
      if (o.kind === 'header') built = buildHeaderPrimitives(ctx?.modelData, ctx?.versio)
      else if (o.kind === 'graded_table') {
        const data = ctx?.tableData?.[o.id]
        if (data) built = buildTablePrimitives(data)
      }
      if (built) {
        const g = new Konva.Group({ x: toPx(o.x), y: toPx(o.y) })
        addPrimsToGroup(g, built.prims)
        layer.add(g)
      }
    } else if (o.type === 'image') {
      const src = o.src
      if (!src) continue
      try {
        const el = await loadImageEl(src)
        layer.add(new Konva.Image({
          x: toPx(o.x), y: toPx(o.y),
          width: toPx(o.width), height: toPx(o.height || o.width), image: el,
        }))
      } catch { /* imatge no carregada → s'omet */ }
    }
  }
  layer.draw()
  const url = stage.toDataURL({ pixelRatio, mimeType: 'image/png' })
  stage.destroy()
  return url
}

// Serialitza pages per a desar: els data_block graded_table NO desen el dataURL
// (es re-genera des de size_fitting_id en obrir); la resta es desa tal qual.
function serializePages(pages) {
  return pages.map(p => ({
    id: p.id,
    objects: (p.objects || []).map(o => {
      if (o.type === 'data_block') { const { src, ...rest } = o; return rest }
      return o
    }),
  }))
}

// ════════════════════════ Nodes Konva interactius (live) ════════════════════
function ImageObj({ obj, src, common }) {
  const img = useImage(src)
  if (!img) {
    // Placeholder mentre carrega / si falla.
    return <Rect {...common} width={toPx(obj.width)} height={toPx(obj.height || obj.width)}
      fill={COL.goldPale} stroke={COL.border} dash={[4, 4]} />
  }
  return <KonvaImage {...common} image={img}
    width={toPx(obj.width)} height={toPx(obj.height || obj.width)} />
}

function ObjectNode({ obj, src, tableData, modelData, versio, selected, selectable, draggable, onSelect, onDragEnd, onTransformEnd, onDblText }) {
  const common = {
    id: obj.id,
    x: toPx(obj.x), y: toPx(obj.y),
    draggable,
    onClick: selectable ? onSelect : undefined,
    onTap: selectable ? onSelect : undefined,
    onDragEnd,
    onTransformEnd,
  }
  if (obj.type === 'data_block') {
    if (obj.kind === 'header') {
      return <HeaderBlock modelData={modelData} versio={versio} groupProps={common} isSelected={selected} />
    }
    const data = tableData?.[obj.id]
    if (!data) {
      return (
        <Group {...common}>
          <Rect width={toPx(obj.width || 120)} height={toPx(obj.height || 40)} fill={COL.goldPale} stroke={COL.border} dash={[4, 4]} />
          <Text x={6} y={6} text={data === null ? 'Sense grading actiu' : 'Carregant taula…'} fontSize={12} fontFamily={FONT} fill={COL.textMuted} listening={false} />
        </Group>
      )
    }
    return <GradedTableNode tableData={data} groupProps={common} isSelected={selected} />
  }
  if (obj.type === 'text') {
    return <Text {...common} text={obj.text || ''} width={obj.width ? toPx(obj.width) : undefined}
      fontSize={obj.fontSize || 11} fontFamily={obj.fontFamily || FONT}
      fill={obj.fill || COL.textMain}
      onDblClick={onDblText} onDblTap={onDblText} />
  }
  if (obj.type === 'rect') {
    return <Rect {...common} width={toPx(obj.width)} height={toPx(obj.height)}
      fill={obj.fill && obj.fill !== 'transparent' ? obj.fill : undefined}
      stroke={obj.stroke || COL.gold} strokeWidth={obj.strokeWidth || 1} />
  }
  if (obj.type === 'line') {
    return <Line {...common} x={0} y={0} points={(obj.points || []).map(toPx)}
      stroke={obj.stroke || COL.textMain} strokeWidth={obj.strokeWidth || 1}
      lineCap="round" lineJoin="round" hitStrokeWidth={10} />
  }
  if (obj.type === 'image') {
    return <ImageObj obj={obj} src={src} common={common} />
  }
  return null
}

// ════════════════════════════════ Component ═════════════════════════════════
export default function TechSheetEditor() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const taskId = searchParams.get('task_id')
  const isEditMode = !!taskId
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
  const uploadHeaders = { Authorization: `Bearer ${token}` }

  const [model, setModel] = useState(null)
  const [sheet, setSheet] = useState(null)
  const [pages, setPages] = useState([{ id: uid(), objects: [] }])
  const [currentPage, setCurrentPage] = useState(0)
  const [selectedId, setSelectedId] = useState(null)
  const [tool, setTool] = useState('select')
  // 'loading' | 'owned' | 'conflict' | 'error' | 'readonly'
  const [lockState, setLockState] = useState(isEditMode ? 'loading' : 'readonly')
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

  const locked = lockState === 'owned'
  const stageRef = useRef(null)
  const trRef = useRef(null)
  const wrapRef = useRef(null)
  const fileRef = useRef(null)
  const saveTimer = useRef(null)
  const skipSave = useRef(true)        // salta l'autosave del primer load
  const drawing = useRef(null)         // {type, points, id} mentre es dibuixa
  const [drawTemp, setDrawTemp] = useState(null)

  // ── Helpers de mutació de pàgines ──────────────────────────────────────────
  const objectsOf = (pi) => pages[pi]?.objects || []
  const updatePageObjects = useCallback((pi, updater) => {
    setPages(ps => ps.map((p, i) => (i === pi ? { ...p, objects: updater(p.objects || []) } : p)))
  }, [])
  const addObject = useCallback((obj) => {
    updatePageObjects(currentPage, objs => [...objs, obj])
    setSelectedId(obj.id)
  }, [currentPage, updatePageObjects])
  const updateObject = useCallback((objId, patch) => {
    updatePageObjects(currentPage, objs => objs.map(o => (o.id === objId ? { ...o, ...patch } : o)))
  }, [currentPage, updatePageObjects])
  const deleteObject = useCallback((objId) => {
    updatePageObjects(currentPage, objs => objs.filter(o => o.id !== objId))
    setSelectedId(null)
  }, [currentPage, updatePageObjects])

  // ── Càrrega inicial: model, sheet, fitxers, size fittings, lock ────────────
  useEffect(() => {
    if (!id) return
    let cancelled = false

    fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (!cancelled && d) setModel(d) }).catch(() => {})

    fetch(`${API}/api/v1/model-fitxers/?model=${id}&ordering=-data_pujada`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (!cancelled && d) setFitxers(d.results || d || []) }).catch(() => {})

    fetch(`${API}/api/v1/size-fittings/?model=${id}`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (!cancelled && d) setSizeFittings(d.results || d || []) }).catch(() => {})

    fetch(`${API}/api/v1/models/${id}/tech-sheet/`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (cancelled || !data) return
        setSheet(data)
        // En mode consulta hidratem aquí; en edició ho fa la resposta del lock.
        // NOTA: el TechSheetSerializer actual NO exposa `template_json` als seus fields,
        // així que `data.template_json` és undefined i hydrate cau a "pàgina buida".
        // hydrate és forward-compatible: en quant el backend exposi template_json
        // (clau v2 `pages`), la càrrega funcionarà sense tocar el frontend. (Vegeu informe.)
        if (!isEditMode) hydrate(data)
      }).catch(() => {})

    if (isEditMode) {
      fetch(`${API}/api/v1/models/${id}/tech-sheet/lock/`, { method: 'POST', headers: authHeaders })
        .then(async r => {
          if (cancelled) return
          if (r.ok) { const d = await r.json(); setSheet(d); hydrate(d); setLockState('owned') }
          else if (r.status === 409) { setConflict(await r.json()); setLockState('conflict') }
          else setLockState('error')
        })
        .catch(() => { if (!cancelled) setLockState('error') })
    }

    return () => {
      cancelled = true
      if (isEditMode) {
        if (taskId) {
          fetch(`${API}/api/v1/model-task-items/${taskId}/transition/`, {
            method: 'POST', headers: authHeaders,
            body: JSON.stringify({ to_status: 'Paused' }), keepalive: true,
          }).catch(() => {})
        }
        fetch(`${API}/api/v1/models/${id}/tech-sheet/unlock/`, {
          method: 'POST', headers: authHeaders, keepalive: true,
        }).catch(() => {})
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // Carrega el template_json v2 a l'estat. tj buit/absent → 1 pàgina buida.
  function hydrate(sheetData) {
    const tj = sheetData?.template_json
    skipSave.current = true
    if (tj && tj.version === 2 && Array.isArray(tj.pages) && tj.pages.length) {
      setPages(tj.pages.map(p => ({ id: p.id || uid(), objects: (p.objects || []).map(o => ({ ...o, id: o.id || uid() })) })))
    } else {
      setPages([{ id: uid(), objects: [] }])
    }
    setCurrentPage(0)
  }

  // ── Re-fetch dels data_block (taula graduada) en carregar → cache JSON viu ──
  useEffect(() => {
    const pending = pages.flatMap(p => (p.objects || []))
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
        const r = await fetch(`${API}/api/v1/models/${id}/tech-sheet/update/`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` },
          body: JSON.stringify({ template_json: { version: 2, pages: serializePages(pages) } }),
        })
        setSaveState(r.ok ? 'saved' : 'error')
      } catch { setSaveState('error') }
    }, 2000)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pages, locked])

  // ── Miniatures: re-render offscreen de totes les pàgines (debounce) ────────
  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const ctx = { tableData, modelData: model, versio: sheet?.versio }
        const thumbs = []
        for (const p of pages) thumbs.push(await renderPageToDataURL(p, 0.18, ctx))
        setThumbnails(thumbs)
      } catch { /* noop */ }
    }, 300)
    return () => clearTimeout(t)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pages, tableData, model, sheet?.versio])

  // ── Transformer: lliga el node seleccionat ─────────────────────────────────
  useEffect(() => {
    const tr = trRef.current
    const stage = stageRef.current
    if (!tr || !stage) return
    const obj = objectsOf(currentPage).find(o => o.id === selectedId)
    // No transformem línies (resize de punts complex) ni blocs de dades (auto-dimensionats)
    // ni objectes de plantilla. Aquests es mouen (drag) però no es redimensionen.
    if (selectedId && obj && obj.layer !== 'template' && obj.type !== 'line' && obj.type !== 'data_block') {
      const node = stage.findOne('#' + selectedId)
      tr.nodes(node ? [node] : [])
    } else {
      tr.nodes([])
    }
    tr.getLayer()?.batchDraw()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, currentPage, pages])

  // ── Teclat: Delete/Backspace esborra l'objecte free seleccionat ────────────
  useEffect(() => {
    const onKey = (e) => {
      if (editingText) return
      if (e.key !== 'Delete' && e.key !== 'Backspace') return
      if (!selectedId || !locked) return
      const obj = objectsOf(currentPage).find(o => o.id === selectedId)
      if (obj && obj.layer === 'free') { e.preventDefault(); deleteObject(selectedId) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, currentPage, pages, locked, editingText])

  // ── Handlers de node (drag / transform) ────────────────────────────────────
  const handleDragEnd = (obj) => (e) => {
    const node = e.target
    if (obj.type === 'line') {
      const dx = toMm(node.x()), dy = toMm(node.y())
      const pts = (obj.points || []).map((v, i) => (i % 2 === 0 ? v + dx : v + dy))
      node.position({ x: 0, y: 0 })
      updateObject(obj.id, { points: pts })
    } else {
      updateObject(obj.id, { x: toMm(node.x()), y: toMm(node.y()) })
    }
  }
  const handleTransformEnd = (obj) => (e) => {
    const node = e.target
    const sx = node.scaleX(), sy = node.scaleY()
    node.scaleX(1); node.scaleY(1)
    const patch = {
      x: toMm(node.x()), y: toMm(node.y()),
      width: Math.max(2, toMm(node.width() * sx)),
    }
    if (obj.type !== 'text') patch.height = Math.max(2, toMm(node.height() * sy))
    updateObject(obj.id, patch)
  }

  // ── Stage: dibuix de rect/línia/draw + crear text + deselecció ─────────────
  const stagePoint = () => {
    const stage = stageRef.current
    return stage ? stage.getPointerPosition() : null
  }
  const onStageMouseDown = (e) => {
    if (!locked) { if (e.target === e.target.getStage()) setSelectedId(null); return }
    const pos = stagePoint()
    if (!pos) return
    if (tool === 'select') {
      if (e.target === e.target.getStage()) setSelectedId(null)
      return
    }
    if (tool === 'text') {
      const obj = {
        id: uid(), type: 'text', layer: 'free', x: toMm(pos.x), y: toMm(pos.y),
        width: 120, height: 30, text: 'Doble clic per editar', fontSize: 11,
        fontFamily: FONT, fill: COL.textMain,
      }
      addObject(obj); setTool('select'); return
    }
    if (tool === 'rect' || tool === 'line' || tool === 'draw') {
      drawing.current = { type: tool, startX: pos.x, startY: pos.y, points: [pos.x, pos.y] }
      setDrawTemp({ type: tool, x: pos.x, y: pos.y, w: 0, h: 0, points: [pos.x, pos.y] })
    }
  }
  const onStageMouseMove = () => {
    if (!drawing.current) return
    const pos = stagePoint()
    if (!pos) return
    const d = drawing.current
    if (d.type === 'rect') {
      setDrawTemp({ type: 'rect', x: Math.min(d.startX, pos.x), y: Math.min(d.startY, pos.y), w: Math.abs(pos.x - d.startX), h: Math.abs(pos.y - d.startY) })
    } else if (d.type === 'line') {
      setDrawTemp({ type: 'line', points: [d.startX, d.startY, pos.x, pos.y] })
    } else if (d.type === 'draw') {
      d.points = [...d.points, pos.x, pos.y]
      setDrawTemp({ type: 'draw', points: d.points })
    }
  }
  const onStageMouseUp = () => {
    const d = drawing.current
    if (!d) return
    drawing.current = null
    const pos = stagePoint() || { x: d.startX, y: d.startY }
    let obj = null
    if (d.type === 'rect') {
      const x = Math.min(d.startX, pos.x), y = Math.min(d.startY, pos.y)
      const w = Math.abs(pos.x - d.startX), h = Math.abs(pos.y - d.startY)
      if (w > 3 && h > 3) obj = { id: uid(), type: 'rect', layer: 'free', x: toMm(x), y: toMm(y), width: toMm(w), height: toMm(h), fill: 'transparent', stroke: COL.gold, strokeWidth: 1 }
    } else if (d.type === 'line') {
      obj = { id: uid(), type: 'line', layer: 'free', x: 0, y: 0, points: [toMm(d.startX), toMm(d.startY), toMm(pos.x), toMm(pos.y)], stroke: COL.textMain, strokeWidth: 1 }
    } else if (d.type === 'draw') {
      if (d.points.length >= 4) obj = { id: uid(), type: 'line', layer: 'free', x: 0, y: 0, points: d.points.map(toMm), stroke: COL.textMain, strokeWidth: 1 }
    }
    setDrawTemp(null)
    if (obj) { addObject(obj); setTool('select') }
  }

  // ── Edició inline de text (textarea overlay) ───────────────────────────────
  const startTextEdit = (obj) => {
    if (!locked) return
    setSelectedId(obj.id)
    setEditingText({ id: obj.id, value: obj.text || '', x: toPx(obj.x), y: toPx(obj.y), w: toPx(obj.width || 120) })
  }
  const commitTextEdit = () => {
    if (!editingText) return
    updateObject(editingText.id, { text: editingText.value })
    setEditingText(null)
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
      if (!r.ok) { flash('Aquest size fitting no té grading actiu.'); return }
      const data = await r.json()
      if (!data.rows || !data.rows.length) { flash('Taula buida.'); return }
      const { totalW, totalH } = buildTablePrimitives(data)
      const objId = uid()
      const obj = {
        id: objId, type: 'data_block', kind: 'graded_table', size_fitting_id: sfId,
        layer: 'data', x: 50, y: 50, width: totalW / MM_TO_PX, height: totalH / MM_TO_PX,
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
      flash('Ja hi ha una capçalera en aquesta pàgina.'); return
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
    if (!window.confirm('Esborrar aquesta pàgina?')) return
    setPages(ps => ps.filter((_, i) => i !== index))
    setCurrentPage(ci => Math.min(ci, pages.length - 2))
    setSelectedId(null)
  }

  // ── Export PDF (pdf-lib) ───────────────────────────────────────────────────
  const onExport = async () => {
    setExporting(true)
    try {
      const pdf = await PDFDocument.create()
      const ctx = { tableData, modelData: model, versio: sheet?.versio }
      for (const p of pages) {
        const dataUrl = await renderPageToDataURL(p, 3.5, ctx)
        const png = await pdf.embedPng(dataUrl)
        const page = pdf.addPage([PDF_W_PT, PDF_H_PT])
        page.drawImage(png, { x: 0, y: 0, width: PDF_W_PT, height: PDF_H_PT })
      }
      const bytes = await pdf.save()
      const blob = new Blob([bytes], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${model?.codi_intern || id}_fitxa_v${sheet?.versio ?? 1}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch { /* silenci */ }
    finally { setExporting(false) }
  }

  // ── UI ───────────────────────────────────────────────────────────────────
  const badge = (() => {
    if (lockState === 'loading') return { text: 'Carregant…', bg: COL.bg, fg: COL.textMuted }
    if (lockState === 'readonly') return { text: 'Mode consulta', bg: COL.bg, fg: COL.textMuted }
    if (lockState === 'owned') return { text: 'Editant', bg: COL.gold, fg: '#fff' }
    if (lockState === 'conflict') return { text: `Bloquejada per ${conflict?.locked_by || 'un altre usuari'}`, bg: COL.bg, fg: COL.textMuted }
    return { text: 'Error de bloqueig', bg: COL.bg, fg: COL.textMuted }
  })()
  const saveLabel = saveState === 'saving' ? 'Desant…' : saveState === 'saved' ? 'Desat ✓' : saveState === 'error' ? 'Error desant' : null

  const headerBtn = {
    display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, padding: '5px 10px',
    borderRadius: 6, border: `1px solid ${COL.border}`, background: 'transparent',
    cursor: 'pointer', color: COL.textMain, fontFamily: FONT,
  }
  const curObjs = objectsOf(currentPage)
  const ordered = [...curObjs].sort((a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
  const selObj = curObjs.find(o => o.id === selectedId) || null

  const TOOLS = [
    { k: 'select', icon: 'ti-pointer', label: 'Seleccionar' },
    { k: 'text', icon: 'ti-typography', label: 'Text' },
    { k: 'rect', icon: 'ti-square', label: 'Rectangle' },
    { k: 'line', icon: 'ti-line', label: 'Línia' },
    { k: 'draw', icon: 'ti-pencil', label: 'Dibuix' },
  ]

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', background: '#faf7f2', fontFamily: FONT }}>
      {/* ── Topbar ── */}
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '0.7rem 1.2rem', borderBottom: `1px solid #e3cfa3`, background: COL.sidebar, color: COL.textMain }}>
        <button onClick={() => navigate(`/models/${id}`)} style={headerBtn}>
          <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> Tornar al model
        </button>
        <button onClick={onExport} disabled={exporting}
          style={{ ...headerBtn, background: COL.gold, border: 'none', color: '#fff', opacity: exporting ? 0.5 : 1 }}>
          <i className="ti ti-file-download" style={{ fontSize: 14 }} /> {exporting ? 'Exportant…' : 'Exportar PDF'}
        </button>
        <span style={{ fontSize: 14, fontWeight: 600 }}>
          {model?.codi_intern || `#${id}`}{model?.nom_prenda ? ` · ${model.nom_prenda}` : ''}
        </span>
        <span style={{ fontSize: 11, color: COL.textMuted }}>Pàgina {currentPage + 1} de {pages.length}</span>
        {saveLabel && <span style={{ fontSize: 11, color: COL.textMuted }}>{saveLabel}</span>}
        {notice && <span style={{ fontSize: 11, color: '#b45309', background: '#fef3c7', padding: '2px 8px', borderRadius: 6 }}>{notice}</span>}

        {/* Eines (només en edició) */}
        {locked && (
          <div style={{ display: 'flex', gap: 4, marginLeft: 16 }}>
            {TOOLS.map(tl => (
              <button key={tl.k} onClick={() => setTool(tl.k)} title={tl.label}
                style={{ ...headerBtn, padding: '5px 8px', borderColor: tool === tl.k ? COL.gold : COL.border, background: tool === tl.k ? COL.goldPale : 'transparent', color: tool === tl.k ? COL.gold : COL.textMain }}>
                <i className={`ti ${tl.icon}`} style={{ fontSize: 15 }} />
              </button>
            ))}
            <button onClick={() => fileRef.current?.click()} title="Imatge" style={{ ...headerBtn, padding: '5px 8px' }}>
              <i className="ti ti-photo" style={{ fontSize: 15 }} />
            </button>
            <input ref={fileRef} type="file" accept="image/*" hidden
              onChange={e => { const f = e.target.files[0]; e.target.value = ''; handleFile(f) }} />
          </div>
        )}

        <span style={{ marginLeft: 'auto', fontSize: 10, fontWeight: 500, padding: '2px 8px', borderRadius: 10, background: badge.bg, color: badge.fg, whiteSpace: 'nowrap' }}>
          v{sheet?.versio ?? 1} · {badge.text}
        </span>
      </header>

      <main style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* ── Esquerra: pàgines ── */}
        <div style={{ width: 96, flexShrink: 0, background: COL.bg, borderRight: `1px solid ${COL.border}`, overflowY: 'auto', padding: '8px 5px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ color: COL.gold, fontSize: 9, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Pàgines</div>
          {locked && (
            <button onClick={addPage} style={{ fontSize: 9, padding: '3px 4px', border: `1px solid ${COL.gold}`, borderRadius: 4, background: 'transparent', color: COL.gold, fontFamily: FONT, cursor: 'pointer' }}>+ Pàgina</button>
          )}
          {pages.map((p, i) => (
            <div key={p.id} onClick={() => { setCurrentPage(i); setSelectedId(null) }} style={{ position: 'relative', cursor: 'pointer' }}>
              <div style={{ width: 84, height: 60, borderRadius: 3, overflow: 'hidden', background: '#fff', border: currentPage === i ? `2px solid ${COL.gold}` : `1px solid ${COL.border}` }}>
                {thumbnails[i] && <img src={thumbnails[i]} alt={`Pàg ${i + 1}`} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} />}
              </div>
              <div style={{ fontSize: 9, color: COL.textMuted, textAlign: 'center', marginTop: 1 }}>Pàg. {i + 1}</div>
              {locked && pages.length > 1 && (
                <button onClick={(e) => { e.stopPropagation(); removePage(i) }} title="Eliminar pàgina"
                  style={{ position: 'absolute', top: 2, right: 2, background: '#e74c3c', color: '#fff', border: 'none', fontSize: 9, lineHeight: '14px', width: 14, height: 14, padding: 0, borderRadius: 2, cursor: 'pointer' }}>×</button>
              )}
            </div>
          ))}
        </div>

        {/* ── Centre: Stage Konva ── */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: COL.bg, minWidth: 0, overflow: 'auto', position: 'relative' }}>
          {lockState === 'readonly' && (
            <div style={{ position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)', zIndex: 5, background: '#fff', border: `1px solid ${COL.border}`, borderRadius: 6, padding: '4px 12px', fontSize: 11, color: COL.textMuted }}>
              <i className="ti ti-eye" style={{ marginRight: 6 }} />Mode consulta — només lectura
            </div>
          )}
          <div ref={wrapRef} onDrop={onDrop} onDragOver={e => e.preventDefault()}
            style={{ position: 'relative', width: CANVAS_W, height: CANVAS_H, boxShadow: '0 4px 24px rgba(0,0,0,0.12)', background: '#fff', cursor: (locked && tool !== 'select') ? 'crosshair' : 'default' }}>
            <Stage ref={stageRef} width={CANVAS_W} height={CANVAS_H}
              onMouseDown={onStageMouseDown} onMouseMove={onStageMouseMove} onMouseUp={onStageMouseUp}>
              {/* Fons blanc + 3 capes en ordre z. Konva no agrupa per `layer`:
                  ordenem els objectes i pintem en una sola Layer (z per ordre d'array). */}
              <Layer>
                <Rect x={0} y={0} width={CANVAS_W} height={CANVAS_H} fill="#ffffff" listening={false} />
                {ordered.map(o => (
                  <ObjectNode key={o.id} obj={o} src={o.src}
                    tableData={tableData} modelData={model} versio={sheet?.versio}
                    selected={selectedId === o.id}
                    selectable={locked && o.layer !== 'template'}
                    draggable={locked && tool === 'select' && o.layer !== 'template'}
                    onSelect={() => setSelectedId(o.id)}
                    onDragEnd={handleDragEnd(o)}
                    onTransformEnd={handleTransformEnd(o)}
                    onDblText={() => startTextEdit(o)} />
                ))}
                {/* Forma temporal mentre es dibuixa */}
                {drawTemp?.type === 'rect' && <Rect x={drawTemp.x} y={drawTemp.y} width={drawTemp.w} height={drawTemp.h} stroke={COL.gold} strokeWidth={1} dash={[4, 4]} listening={false} />}
                {(drawTemp?.type === 'line' || drawTemp?.type === 'draw') && <Line points={drawTemp.points} stroke={COL.textMain} strokeWidth={1} dash={[4, 4]} listening={false} />}
                <Transformer ref={trRef} rotateEnabled={false} ignoreStroke
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
                style={{ position: 'absolute', left: editingText.x, top: editingText.y, width: Math.max(80, editingText.w), fontFamily: FONT, fontSize: 11, color: COL.textMain, border: `1px solid ${COL.gold}`, padding: 2, resize: 'none', outline: 'none', background: '#fff', zIndex: 10 }}
              />
            )}
          </div>
        </div>

        {/* ── Dreta: capes / inserir / propietats ── */}
        <aside style={{ width: 180, flexShrink: 0, borderLeft: `1px solid ${COL.border}`, background: COL.bg, display: 'flex', flexDirection: 'column', minHeight: 0, fontFamily: FONT }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 10px' }}>
            {/* Inserir blocs de dades */}
            <SectionTitle>Inserir bloc de dades</SectionTitle>
            <button onClick={insertHeader} disabled={!locked}
              style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, padding: '6px 8px', marginBottom: 6, border: 'none', borderRadius: 5, background: COL.gold, color: '#fff', fontFamily: FONT, cursor: !locked ? 'default' : 'pointer', opacity: !locked ? 0.45 : 1 }}>
              <i className="ti ti-layout-navbar" style={{ fontSize: 13 }} /> Capçalera del model
            </button>
            <button onClick={onAddTableClick} disabled={!locked || addingTable || !sizeFittings.length}
              style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, padding: '6px 8px', marginBottom: 6, border: 'none', borderRadius: 5, background: COL.gold, color: '#fff', fontFamily: FONT, cursor: (!locked || !sizeFittings.length) ? 'default' : 'pointer', opacity: (!locked || addingTable || !sizeFittings.length) ? 0.45 : 1 }}>
              <i className="ti ti-table" style={{ fontSize: 13 }} /> {addingTable ? 'Afegint…' : 'Taula graduada'}
            </button>
            {!sizeFittings.length && <p style={{ fontSize: 10, color: COL.textMuted, margin: '0 0 8px' }}>Cap size fitting.</p>}

            {/* Fitxers del model */}
            <SectionTitle>Fitxers del model ({fitxers.length})</SectionTitle>
            {fitxers.length === 0 ? (
              <p style={{ fontSize: 10, color: COL.textMuted }}>Cap fitxer.</p>
            ) : fitxers.map(f => {
              const hasUrl = !!(f.url_extern || f.fitxer)
              return (
                <button key={f.id} onClick={() => addModelFitxer(f)} disabled={!hasUrl || !locked}
                  title={f.nom_fitxer}
                  style={{ width: '100%', textAlign: 'left', fontSize: 10, padding: '5px 6px', marginBottom: 3, border: `1px solid ${COL.border}`, borderRadius: 4, background: '#fafafa', color: COL.textMain, fontFamily: FONT, cursor: (!hasUrl || !locked) ? 'default' : 'pointer', opacity: (!hasUrl || !locked) ? 0.5 : 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  <i className="ti ti-photo-plus" style={{ fontSize: 11, marginRight: 5 }} />{f.nom_fitxer}
                </button>
              )
            })}

            {/* Propietats de l'objecte seleccionat */}
            {selObj && locked && (
              <>
                <SectionTitle>Element · {selObj.type}</SectionTitle>
                {selObj.type === 'text' && (
                  <label style={propLabel}>Mida font
                    <input type="number" min={6} max={48} value={selObj.fontSize || 11}
                      onChange={e => updateObject(selObj.id, { fontSize: Number(e.target.value) || 11 })}
                      style={propInput} />
                  </label>
                )}
                {(selObj.type === 'rect' || selObj.type === 'line') && (
                  <label style={propLabel}>Color traç
                    <input type="color" value={selObj.stroke || '#1d1d1b'}
                      onChange={e => updateObject(selObj.id, { stroke: e.target.value })}
                      style={{ ...propInput, padding: 0, height: 26 }} />
                  </label>
                )}
                {selObj.type === 'rect' && (
                  <label style={propLabel}>Emplenat
                    <input type="color" value={selObj.fill && selObj.fill !== 'transparent' ? selObj.fill : '#ffffff'}
                      onChange={e => updateObject(selObj.id, { fill: e.target.value })}
                      style={{ ...propInput, padding: 0, height: 26 }} />
                  </label>
                )}
                {(selObj.layer === 'free' || selObj.type === 'data_block') && (
                  <button onClick={() => deleteObject(selObj.id)}
                    style={{ width: '100%', fontSize: 11, padding: '5px 8px', marginTop: 6, border: `1px solid #e74c3c`, borderRadius: 5, background: 'transparent', color: '#e74c3c', fontFamily: FONT, cursor: 'pointer' }}>
                    <i className="ti ti-trash" style={{ fontSize: 12, marginRight: 5 }} />Eliminar
                  </button>
                )}
              </>
            )}
          </div>
        </aside>
      </main>

      {/* Selector de size fitting (>1) */}
      {pickFitting && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }} onClick={() => setPickFitting(false)}>
          <div onClick={e => e.stopPropagation()} style={{ background: '#fff', borderRadius: 12, padding: '1.4rem', maxWidth: 360, width: '90%', fontFamily: FONT }}>
            <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Tria un size fitting</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {sizeFittings.map(sf => (
                <button key={sf.id} onClick={() => { setPickFitting(false); insertGradedTable(sf.id) }}
                  style={{ textAlign: 'left', fontSize: 12, padding: '8px 10px', border: `1px solid ${COL.border}`, borderRadius: 6, background: '#fafafa', color: COL.textMain, fontFamily: FONT, cursor: 'pointer' }}>
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

function SectionTitle({ children }) {
  return <div style={{ fontSize: 10, fontWeight: 600, color: COL.gold, textTransform: 'uppercase', letterSpacing: '0.05em', margin: '12px 0 6px' }}>{children}</div>
}
const propLabel = { display: 'block', fontSize: 10, color: COL.textMuted, marginBottom: 8 }
const propInput = { width: '100%', fontFamily: FONT, fontSize: 12, padding: '4px 6px', marginTop: 3, border: `1px solid ${COL.border}`, borderRadius: 5, background: '#fff', color: COL.textMain, boxSizing: 'border-box' }
