import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Stage, Layer, Rect, Text, Line, Arrow, Ellipse, Image as KonvaImage, Transformer, Group } from 'react-konva'
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
export const COL = {
  sidebar: '#f0dfc0', gold: 'var(--gold)', goldPale: '#f5e6d0',
  border: 'var(--border)', textMain: 'var(--text-main)', textMuted: 'var(--text-muted)', bg: '#f5f0e8',
}

const LAYER_ORDER = { template: 0, data: 1, free: 2 }
// TS-4c — eines per "família" de creació (mateixa mecànica de drag).
const RECT_TOOLS = ['rect', 'rect_round', 'ellipse']   // drag = bounding box
const LINE_TOOLS = ['line', 'line_dot', 'arrow', 'arrow2']   // drag = 2 punts
export const uid = () => (crypto.randomUUID ? crypto.randomUUID() : `id-${Math.round(performance.now())}-${Math.floor(Math.random() * 1e9)}`)
export const toPx = (mm) => mm * MM_TO_PX
export const toMm = (px) => px / MM_TO_PX

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
  HDR_BG: '#111827', HDR_TEXT: 'var(--white)', ROW_EVEN: 'var(--white)', ROW_ODD: '#f7f7f7',
  ROW_BORDER: 'var(--border)', OUTER: 'var(--gold)', REF: '#dc2626', NOM: '#6b7280', VAL: 'var(--text-main)',
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
    prims.push({ t: 't', x: sizesX0 + si * T_VAL_W, y: 0, w: T_VAL_W, h: T_HDR_H, text: isBase ? `${sl}*` : sl, fill: isBase ? 'var(--white)' : TBL.HDR_TEXT, size: T_FONT, align: 'center', mid: true })
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
  const PH = 'var(--text-muted)'   // color dels placeholders (--text-muted)
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
  const main = 'var(--text-main)'
  const prims = []
  prims.push({ t: 'r', x: 0, y: 0, w: W, h: B1, fill: '#f5e6d0', stroke: 'var(--gold)', sw: 1 })
  prims.push({ t: 't', x: PAD, y: 0, w: W * 0.4 - PAD, h: B1, text: [f.codi, f.nom].filter(Boolean).join(' · '), fill: placeholderMode ? PH : main, size: Math.round(9 * MM_TO_PX), bold: !placeholderMode, italic: placeholderMode, mid: true })
  prims.push({ t: 't', x: W * 0.4, y: 0, w: W * 0.42, h: B1, text: [m?.customer_nom, f.temporada, f.collection].filter(Boolean).join(' · '), fill: placeholderMode ? PH : 'var(--text-main)', italic: placeholderMode, size: Math.round(7 * MM_TO_PX), align: 'center', mid: true })
  // Placeholder "(logo)" només si NO hi ha logo real (es pinta a sobre com a imatge).
  if (!hasLogo) prims.push({ t: 't', x: W * 0.82, y: 0, w: W * 0.18 - PAD, h: B1, text: '(logo)', fill: 'var(--text-muted)', size: Math.round(7 * MM_TO_PX), align: 'right', mid: true })
  prims.push({ t: 'r', x: 0, y: B1, w: W, h: B2, fill: '#fafafa', stroke: 'var(--border)', sw: 1 })
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
function GradedTableNode({ tableData, scale = 1, groupProps, isSelected }) {
  const { prims, totalW, totalH } = useMemo(() => buildTablePrimitives(tableData), [tableData])
  return (
    <Group {...groupProps} scaleX={scale} scaleY={scale}>
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
      {isSelected && <Rect x={0} y={0} width={totalW} height={totalH} stroke="var(--gold)" strokeWidth={2} dash={[4, 3]} fill="transparent" listening={false} />}
    </Group>
  )
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
  layer.add(new Konva.Rect({ x: 0, y: 0, width: pageW, height: pageH, fill: 'var(--white)' }))
  const ordered = [...(page.objects || [])].sort(
    (a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
  for (const o of ordered) {
    if (o.type === 'text') {
      // text_box: rect de fons darrere el text.
      if (o.bgFill) {
        const pad = o.bgPadding || 4, fs = o.fontSize || 11, w = toPx(o.width || 120)
        layer.add(new Konva.Rect({ x: toPx(o.x) - pad, y: toPx(o.y) - pad, width: w + pad * 2, height: fs * 1.6 + pad * 2, fill: o.bgFill, cornerRadius: 3 }))
      }
      layer.add(new Konva.Text({
        x: toPx(o.x), y: toPx(o.y), width: o.width ? toPx(o.width) : undefined,
        text: o.text || '', fontSize: o.fontSize || 11, fontFamily: o.fontFamily || FONT,
        fontStyle: o.fontStyle || 'normal', fill: o.fill || COL.textMain,
      }))
    } else if (o.type === 'rect') {
      layer.add(new Konva.Rect({
        x: toPx(o.x), y: toPx(o.y), width: toPx(o.width), height: toPx(o.height),
        fill: o.fill && o.fill !== 'transparent' ? o.fill : undefined,
        stroke: o.stroke || COL.gold, strokeWidth: o.strokeWidth || 1, cornerRadius: o.cornerRadius || 0,
      }))
    } else if (o.type === 'ellipse') {
      layer.add(new Konva.Ellipse({
        x: toPx(o.x), y: toPx(o.y), radiusX: toPx(o.rx), radiusY: toPx(o.ry),
        fill: o.fill && o.fill !== 'transparent' ? o.fill : undefined,
        stroke: o.stroke || COL.textMain, strokeWidth: o.strokeWidth || 1.5,
      }))
    } else if (o.type === 'line') {
      layer.add(new Konva.Line({
        points: (o.points || []).map(toPx), stroke: o.stroke || COL.textMain,
        strokeWidth: o.strokeWidth || 1, dash: o.dash || undefined, lineCap: 'round', lineJoin: 'round',
      }))
    } else if (o.type === 'arrow') {
      layer.add(new Konva.Arrow({
        points: [toPx(o.x), toPx(o.y), toPx(o.x2), toPx(o.y2)],
        stroke: o.stroke || COL.textMain, fill: o.fill || o.stroke || COL.textMain,
        strokeWidth: o.strokeWidth || 1.5, pointerLength: 8, pointerWidth: 6, pointerAtBeginning: !!o.arrow2,
      }))
    } else if (o.type === 'data_block') {
      // Blocs vius natius: mateixes primitives que el canvas. Group posicionat en px.
      let built = null
      let logoEl = null
      if (o.kind === 'header') {
        if (ctx?.customerLogoUrl) { try { logoEl = await loadImageEl(ctx.customerLogoUrl) } catch { logoEl = null } }
        built = buildHeaderPrimitives(ctx?.modelData, ctx?.versio, ctx?.placeholderMode, !!logoEl)
      } else if (o.kind === 'graded_table') {
        const data = ctx?.tableData?.[o.id]
        if (data) built = buildTablePrimitives(data)
      }
      if (built) {
        const g = new Konva.Group({ x: toPx(o.x), y: toPx(o.y), scaleX: o.scale || 1, scaleY: o.scale || 1 })
        addPrimsToGroup(g, built.prims)
        if (logoEl) g.add(new Konva.Image({ image: logoEl, x: built.totalW - 45 * MM_TO_PX, y: 2 * MM_TO_PX, width: 40 * MM_TO_PX, height: 16 * MM_TO_PX }))
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
export function serializePages(pages) {
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

export function ObjectNode({ obj, src, tableData, modelData, versio, placeholderMode, customerLogoUrl, selected, selectable, draggable, onSelect, onDragEnd, onTransformEnd, onDblText }) {
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
      return <HeaderBlock modelData={modelData} versio={versio} placeholderMode={placeholderMode} logoUrl={customerLogoUrl} groupProps={common} isSelected={selected} />
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
    return <GradedTableNode tableData={data} scale={obj.scale || 1} groupProps={common} isSelected={selected} />
  }
  if (obj.type === 'text') {
    // Text amb fons (text_box): Group amb un Rect darrere; no redimensionable per Transformer.
    if (obj.bgFill) {
      const w = toPx(obj.width || 120), fs = obj.fontSize || 11, pad = obj.bgPadding || 4
      return (
        <Group {...common} onDblClick={onDblText} onDblTap={onDblText}>
          <Rect x={-pad} y={-pad} width={w + pad * 2} height={fs * 1.6 + pad * 2} fill={obj.bgFill} cornerRadius={3} />
          <Text text={obj.text || ''} width={w} fontSize={fs} fontFamily={obj.fontFamily || FONT}
            fontStyle={obj.fontStyle || 'normal'} fill={obj.fill || COL.textMain} listening={false} />
        </Group>
      )
    }
    return <Text {...common} text={obj.text || ''} width={obj.width ? toPx(obj.width) : undefined}
      fontSize={obj.fontSize || 11} fontFamily={obj.fontFamily || FONT} fontStyle={obj.fontStyle || 'normal'}
      fill={obj.fill || COL.textMain}
      onDblClick={onDblText} onDblTap={onDblText} />
  }
  if (obj.type === 'rect') {
    return <Rect {...common} width={toPx(obj.width)} height={toPx(obj.height)}
      fill={obj.fill && obj.fill !== 'transparent' ? obj.fill : undefined}
      stroke={obj.stroke || COL.gold} strokeWidth={obj.strokeWidth || 1} cornerRadius={obj.cornerRadius || 0} />
  }
  if (obj.type === 'ellipse') {
    return <Ellipse {...common} radiusX={toPx(obj.rx)} radiusY={toPx(obj.ry)}
      fill={obj.fill && obj.fill !== 'transparent' ? obj.fill : undefined}
      stroke={obj.stroke || COL.textMain} strokeWidth={obj.strokeWidth || 1.5} />
  }
  if (obj.type === 'line') {
    return <Line {...common} x={0} y={0} points={(obj.points || []).map(toPx)}
      stroke={obj.stroke || COL.textMain} strokeWidth={obj.strokeWidth || 1} dash={obj.dash || undefined}
      lineCap="round" lineJoin="round" hitStrokeWidth={10} />
  }
  if (obj.type === 'arrow') {
    return <Arrow {...common} x={0} y={0}
      points={[toPx(obj.x), toPx(obj.y), toPx(obj.x2), toPx(obj.y2)]}
      stroke={obj.stroke || COL.textMain} fill={obj.fill || obj.stroke || COL.textMain}
      strokeWidth={obj.strokeWidth || 1.5} pointerLength={8} pointerWidth={6}
      pointerAtBeginning={!!obj.arrow2} hitStrokeWidth={10} />
  }
  if (obj.type === 'image') {
    return <ImageObj obj={obj} src={src} common={common} />
  }
  return null
}

// ════════════════════════════════ Component ═════════════════════════════════
export default function TechSheetEditor() {
  const { t } = useTranslation()
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
  const [pageFormat, setPageFormat] = useState('A4L')   // TS-4b: format del document sencer
  const [openGroup, setOpenGroup] = useState(null)      // TS-4c: grup d'eines desplegat
  const toolbarRef = useRef(null)

  const locked = lockState === 'owned'
  const fmt = PAGE_FORMATS[pageFormat] || PAGE_FORMATS.A4L
  const pageW = Math.round(fmt.w * MM_TO_PX)
  const pageH = Math.round(fmt.h * MM_TO_PX)
  const customerLogoUrl = model?.customer_logo || null   // TS-4c
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
    setPageFormat((tj && tj.pageFormat) || 'A4L')
    setCurrentPage(0)
  }

  // Tanca el desplegable d'eines en clicar fora de la toolbar.
  useEffect(() => {
    if (!openGroup) return
    const onDocDown = (e) => { if (toolbarRef.current && !toolbarRef.current.contains(e.target)) setOpenGroup(null) }
    document.addEventListener('mousedown', onDocDown)
    return () => document.removeEventListener('mousedown', onDocDown)
  }, [openGroup])

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
          body: JSON.stringify({ template_json: { version: 2, pages: serializePages(pages), pageFormat } }),
        })
        setSaveState(r.ok ? 'saved' : 'error')
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
    const obj = objectsOf(currentPage).find(o => o.id === selectedId)
    // Transformable: text, rect, ellipse, image, data_block (keepRatio). NO: línies, fletxes
    // (resize de punts), text amb fons (Group), plantilla.
    const noResize = obj && (obj.type === 'line' || obj.type === 'arrow' || (obj.type === 'text' && obj.bgFill))
    if (selectedId && obj && obj.layer !== 'template' && !noResize) {
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
      // No esborrar mentre s'escriu en un camp del panell (X/Y, escala, format…).
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
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
    node.scaleX(1); node.scaleY(1)
    // Blocs de dades: el resize baka l'escala a obj.scale (coherent amb l'auto-fit),
    // no a width/height. node.scaleX() ja és l'escala absoluta nova (Konva multiplica
    // sobre l'escala base del Group), per tant s'hi assigna directament.
    if (obj.type === 'data_block') {
      updateObject(obj.id, { x: toMm(node.x()), y: toMm(node.y()), scale: Math.max(0.1, Math.max(sx, sy)) })
      return
    }
    if (obj.type === 'ellipse') {
      updateObject(obj.id, { x: toMm(node.x()), y: toMm(node.y()), rx: Math.max(1, toMm(node.radiusX() * sx)), ry: Math.max(1, toMm(node.radiusY() * sy)) })
      return
    }
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
    if (tool === 'text' || tool === 'text_box') {
      const obj = {
        id: uid(), type: 'text', layer: 'free', x: toMm(pos.x), y: toMm(pos.y),
        width: 120, height: 30, text: 'Doble clic per editar', fontSize: 11,
        fontFamily: FONT, fill: COL.textMain,
        ...(tool === 'text_box' ? { bgFill: 'var(--white)', bgPadding: 4 } : {}),
      }
      addObject(obj); setTool('select'); return
    }
    if (RECT_TOOLS.includes(tool) || LINE_TOOLS.includes(tool) || tool === 'draw') {
      drawing.current = { type: tool, startX: pos.x, startY: pos.y, points: [pos.x, pos.y] }
      setDrawTemp({ type: tool, x: pos.x, y: pos.y, w: 0, h: 0, points: [pos.x, pos.y] })
    }
  }
  const onStageMouseMove = () => {
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
    const d = drawing.current
    if (!d) return
    drawing.current = null
    const pos = stagePoint() || { x: d.startX, y: d.startY }
    const base = { id: uid(), layer: 'free' }
    let obj = null
    if (d.type === 'rect' || d.type === 'rect_round') {
      const x = Math.min(d.startX, pos.x), y = Math.min(d.startY, pos.y)
      const w = Math.abs(pos.x - d.startX), h = Math.abs(pos.y - d.startY)
      if (w > 3 && h > 3) obj = { ...base, type: 'rect', x: toMm(x), y: toMm(y), width: toMm(w), height: toMm(h), fill: 'transparent', stroke: COL.gold, strokeWidth: 1, ...(d.type === 'rect_round' ? { cornerRadius: 8 } : {}) }
    } else if (d.type === 'ellipse') {
      const w = Math.abs(pos.x - d.startX), h = Math.abs(pos.y - d.startY)
      if (w > 3 && h > 3) obj = { ...base, type: 'ellipse', x: toMm((d.startX + pos.x) / 2), y: toMm((d.startY + pos.y) / 2), rx: toMm(w / 2), ry: toMm(h / 2), stroke: COL.textMain, strokeWidth: 1.5, fill: 'transparent' }
    } else if (d.type === 'line' || d.type === 'line_dot') {
      obj = { ...base, type: 'line', x: 0, y: 0, points: [toMm(d.startX), toMm(d.startY), toMm(pos.x), toMm(pos.y)], stroke: COL.textMain, strokeWidth: 1, ...(d.type === 'line_dot' ? { dash: [4, 4] } : {}) }
    } else if (d.type === 'arrow' || d.type === 'arrow2') {
      const dist = Math.hypot(pos.x - d.startX, pos.y - d.startY)
      if (dist > 5) obj = { ...base, type: 'arrow', x: toMm(d.startX), y: toMm(d.startY), x2: toMm(pos.x), y2: toMm(pos.y), stroke: COL.textMain, fill: COL.textMain, strokeWidth: 1.5, ...(d.type === 'arrow2' ? { arrow2: true } : {}) }
    } else if (d.type === 'draw') {
      if (d.points.length >= 4) obj = { ...base, type: 'line', x: 0, y: 0, points: d.points.map(toMm), stroke: COL.textMain, strokeWidth: 1 }
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
  // Insereix el logo del client com a imatge lliure (redimensionable). TS-4c.
  const insertLogo = () => {
    if (!locked) return
    if (!customerLogoUrl) { flash(t('tech_sheet.flash_no_logo')); return }
    addObject({ id: uid(), type: 'image', kind: 'logo', layer: 'free', x: 10, y: 8, width: 40, height: 20, src: customerLogoUrl })
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
    setSelectedId(null)
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
    if (lockState === 'loading') return { text: t('model_sheet.loading'), bg: COL.bg, fg: COL.textMuted }
    if (lockState === 'readonly') return { text: t('tech_sheet.badge_readonly'), bg: COL.bg, fg: COL.textMuted }
    if (lockState === 'owned') return { text: t('tech_sheet.badge_editing'), bg: COL.gold, fg: 'var(--white)' }
    if (lockState === 'conflict') return { text: t('tech_sheet.badge_locked_by', { user: conflict?.locked_by || t('tech_sheet.another_user') }), bg: COL.bg, fg: COL.textMuted }
    return { text: t('tech_sheet.badge_lock_error'), bg: COL.bg, fg: COL.textMuted }
  })()
  const saveLabel = saveState === 'saving' ? t('tech_sheet.saving') : saveState === 'saved' ? t('tech_sheet.saved') : saveState === 'error' ? t('tech_sheet.save_error') : null

  const headerBtn = {
    display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', padding: '5px 10px',
    borderRadius: 6, border: `1px solid ${COL.border}`, background: 'transparent',
    cursor: 'pointer', color: COL.textMain, fontFamily: FONT,
  }
  const curObjs = objectsOf(currentPage)
  const ordered = [...curObjs].sort((a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
  const selObj = curObjs.find(o => o.id === selectedId) || null

  // Eines agrupades en desplegables (TS-4c). 'select' és standalone.
  const TOOL_GROUPS = [
    { g: 'shapes', icon: 'ti-shape', label: t('tech_sheet.tool_group_shapes'), tools: [
      { k: 'rect', icon: 'ti-square', label: t('tech_sheet.tool_rect') },
      { k: 'rect_round', icon: 'ti-square-rounded', label: t('tech_sheet.tool_rect_round') },
      { k: 'ellipse', icon: 'ti-circle', label: t('tech_sheet.tool_ellipse') },
    ] },
    { g: 'draw', icon: 'ti-pencil', label: t('tech_sheet.tool_group_draw'), tools: [
      { k: 'line', icon: 'ti-minus', label: t('tech_sheet.tool_line') },
      { k: 'line_dot', icon: 'ti-line-dashed', label: t('tech_sheet.tool_line_dot') },
      { k: 'arrow', icon: 'ti-arrow-right', label: t('tech_sheet.tool_arrow') },
      { k: 'arrow2', icon: 'ti-arrows-horizontal', label: t('tech_sheet.tool_arrow2') },
      { k: 'draw', icon: 'ti-scribble', label: t('tech_sheet.tool_draw') },
    ] },
    { g: 'text', icon: 'ti-typography', label: t('tech_sheet.tool_group_text'), tools: [
      { k: 'text', icon: 'ti-cursor-text', label: t('tech_sheet.tool_text') },
      { k: 'text_box', icon: 'ti-text-caption', label: t('tech_sheet.tool_text_box') },
    ] },
  ]
  const activeTool = (grp) => grp.tools.some(tl => tl.k === tool)

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', background: '#faf7f2', fontFamily: FONT }}>
      {/* ── Topbar ── */}
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '0.7rem 1.2rem', borderBottom: `1px solid #e3cfa3`, background: COL.sidebar, color: COL.textMain }}>
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
        {saveLabel && <span style={{ fontSize: 'var(--fs-body)', color: COL.textMuted }}>{saveLabel}</span>}
        {notice && <span style={{ fontSize: 'var(--fs-body)', color: '#b45309', background: '#fef3c7', padding: '2px 8px', borderRadius: 6 }}>{notice}</span>}

        {/* Eines (només en edició): select + grups desplegables + imatge */}
        {locked && (
          <div ref={toolbarRef} style={{ display: 'flex', gap: 4, marginLeft: 16 }}>
            <button onClick={() => { setTool('select'); setOpenGroup(null) }} title={t('tech_sheet.tool_select')}
              style={{ ...headerBtn, padding: '5px 8px', borderColor: tool === 'select' ? COL.gold : COL.border, background: tool === 'select' ? COL.goldPale : 'transparent', color: tool === 'select' ? COL.gold : COL.textMain }}>
              <i className="ti ti-pointer" style={{ fontSize: 15 }} />
            </button>
            {TOOL_GROUPS.map(grp => {
              const on = activeTool(grp)
              return (
                <div key={grp.g} style={{ position: 'relative', display: 'inline-block' }}>
                  <button onClick={() => setOpenGroup(openGroup === grp.g ? null : grp.g)} title={grp.label}
                    style={{ ...headerBtn, padding: '5px 7px', borderColor: on ? COL.gold : COL.border, background: on ? COL.goldPale : 'transparent', color: on ? COL.gold : COL.textMain }}>
                    <i className={`ti ${grp.icon}`} style={{ fontSize: 15 }} />
                    <i className="ti ti-chevron-down" style={{ fontSize: 10 }} />
                  </button>
                  {openGroup === grp.g && (
                    <div style={{ position: 'absolute', top: '100%', left: 0, marginTop: 4, background: 'var(--white)', border: `1px solid ${COL.border}`, borderRadius: 6, zIndex: 50, minWidth: 160, boxShadow: '0 2px 8px rgba(0,0,0,.08)', overflow: 'hidden' }}>
                      {grp.tools.map(tl => (
                        <button key={tl.k} onClick={() => { setTool(tl.k); setOpenGroup(null) }}
                          style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '6px 10px', background: tool === tl.k ? COL.goldPale : 'transparent', border: 'none', cursor: 'pointer', fontSize: 'var(--fs-body)', fontFamily: FONT, color: COL.textMain }}>
                          <i className={`ti ${tl.icon}`} style={{ fontSize: 14 }} />{tl.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
            <button onClick={() => fileRef.current?.click()} title={t('tech_sheet.tool_image')} style={{ ...headerBtn, padding: '5px 8px' }}>
              <i className="ti ti-photo" style={{ fontSize: 15 }} />
            </button>
            <input ref={fileRef} type="file" accept="image/*" hidden
              onChange={e => { const f = e.target.files[0]; e.target.value = ''; handleFile(f) }} />
          </div>
        )}

        {/* Format de pàgina (tot el document) */}
        <select value={pageFormat} onChange={e => setPageFormat(e.target.value)} disabled={!locked}
          title={t('tech_sheet.page_format')} style={{ ...headerBtn, padding: '5px 8px', marginLeft: locked ? 0 : 16, cursor: locked ? 'pointer' : 'default' }}>
          {Object.entries(PAGE_FORMATS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>

        <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-label)', fontWeight: 500, padding: '2px 8px', borderRadius: 10, background: badge.bg, color: badge.fg, whiteSpace: 'nowrap' }}>
          v{sheet?.versio ?? 1} · {badge.text}
        </span>
      </header>

      <main style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* ── Esquerra: pàgines ── */}
        <div style={{ width: 96, flexShrink: 0, background: COL.bg, borderRight: `1px solid ${COL.border}`, overflowY: 'auto', padding: '8px 5px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ color: COL.gold, fontSize: 'var(--fs-caption)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('tech_sheet.pages')}</div>
          {locked && (
            <button onClick={addPage} style={{ fontSize: 'var(--fs-caption)', padding: '3px 4px', border: `1px solid ${COL.gold}`, borderRadius: 4, background: 'transparent', color: COL.gold, fontFamily: FONT, cursor: 'pointer' }}>{t('tech_sheet.add_page')}</button>
          )}
          {pages.map((p, i) => (
            <div key={p.id} onClick={() => { setCurrentPage(i); setSelectedId(null) }} style={{ position: 'relative', cursor: 'pointer' }}>
              <div style={{ width: 84, height: 60, borderRadius: 3, overflow: 'hidden', background: 'var(--white)', border: currentPage === i ? `2px solid ${COL.gold}` : `1px solid ${COL.border}` }}>
                {thumbnails[i] && <img src={thumbnails[i]} alt={t('tech_sheet.page_n', { n: i + 1 })} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} />}
              </div>
              <div style={{ fontSize: 'var(--fs-caption)', color: COL.textMuted, textAlign: 'center', marginTop: 1 }}>{t('tech_sheet.page_n', { n: i + 1 })}</div>
              {locked && pages.length > 1 && (
                <button onClick={(e) => { e.stopPropagation(); removePage(i) }} title={t('tech_sheet.delete_page')}
                  style={{ position: 'absolute', top: 2, right: 2, background: '#e74c3c', color: 'var(--white)', border: 'none', fontSize: 'var(--fs-caption)', lineHeight: '14px', width: 14, height: 14, padding: 0, borderRadius: 2, cursor: 'pointer' }}>×</button>
              )}
            </div>
          ))}
        </div>

        {/* ── Centre: Stage Konva ── */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: COL.bg, minWidth: 0, overflow: 'auto', position: 'relative' }}>
          {lockState === 'readonly' && (
            <div style={{ position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)', zIndex: 5, background: 'var(--white)', border: `1px solid ${COL.border}`, borderRadius: 6, padding: '4px 12px', fontSize: 'var(--fs-body)', color: COL.textMuted }}>
              <i className="ti ti-eye" style={{ marginRight: 6 }} />{t('tech_sheet.readonly_overlay')}
            </div>
          )}
          <div ref={wrapRef} onDrop={onDrop} onDragOver={e => e.preventDefault()}
            style={{ position: 'relative', width: pageW, height: pageH, boxShadow: '0 4px 24px rgba(0,0,0,0.12)', background: 'var(--white)', cursor: (locked && tool !== 'select') ? 'crosshair' : 'default' }}>
            <Stage ref={stageRef} width={pageW} height={pageH}
              onMouseDown={onStageMouseDown} onMouseMove={onStageMouseMove} onMouseUp={onStageMouseUp}>
              {/* Fons blanc + 3 capes en ordre z. Konva no agrupa per `layer`:
                  ordenem els objectes i pintem en una sola Layer (z per ordre d'array). */}
              <Layer>
                <Rect x={0} y={0} width={pageW} height={pageH} fill="var(--white)" listening={false} />
                {ordered.map(o => (
                  <ObjectNode key={o.id} obj={o} src={o.src}
                    tableData={tableData} modelData={model} versio={sheet?.versio} customerLogoUrl={customerLogoUrl}
                    selected={selectedId === o.id}
                    selectable={locked && o.layer !== 'template'}
                    draggable={locked && tool === 'select' && o.layer !== 'template'}
                    onSelect={() => setSelectedId(o.id)}
                    onDragEnd={handleDragEnd(o)}
                    onTransformEnd={handleTransformEnd(o)}
                    onDblText={() => startTextEdit(o)} />
                ))}
                {/* Forma temporal mentre es dibuixa */}
                {(drawTemp?.type === 'rect' || drawTemp?.type === 'rect_round') && <Rect x={drawTemp.x} y={drawTemp.y} width={drawTemp.w} height={drawTemp.h} stroke={COL.gold} strokeWidth={1} dash={[4, 4]} cornerRadius={drawTemp.type === 'rect_round' ? 8 : 0} listening={false} />}
                {drawTemp?.type === 'ellipse' && <Ellipse x={drawTemp.x + drawTemp.w / 2} y={drawTemp.y + drawTemp.h / 2} radiusX={drawTemp.w / 2} radiusY={drawTemp.h / 2} stroke={COL.textMain} strokeWidth={1} dash={[4, 4]} listening={false} />}
                {(drawTemp?.type === 'line' || drawTemp?.type === 'line_dot' || drawTemp?.type === 'draw') && <Line points={drawTemp.points} stroke={COL.textMain} strokeWidth={1} dash={[4, 4]} listening={false} />}
                {(drawTemp?.type === 'arrow' || drawTemp?.type === 'arrow2') && <Arrow points={drawTemp.points} stroke={COL.textMain} fill={COL.textMain} strokeWidth={1.5} pointerLength={8} pointerWidth={6} pointerAtBeginning={drawTemp.type === 'arrow2'} listening={false} />}
                <Transformer ref={trRef} rotateEnabled={false} ignoreStroke keepRatio={selObj?.type === 'data_block'}
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
                style={{ position: 'absolute', left: editingText.x, top: editingText.y, width: Math.max(80, editingText.w), fontFamily: FONT, fontSize: 'var(--fs-body)', color: COL.textMain, border: `1px solid ${COL.gold}`, padding: 2, resize: 'none', outline: 'none', background: 'var(--white)', zIndex: 10 }}
              />
            )}
          </div>
        </div>

        {/* ── Dreta: capes / inserir / propietats ── */}
        <aside style={{ width: 180, flexShrink: 0, borderLeft: `1px solid ${COL.border}`, background: COL.bg, display: 'flex', flexDirection: 'column', minHeight: 0, fontFamily: FONT }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 10px' }}>
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
                  style={{ width: '100%', textAlign: 'left', fontSize: 'var(--fs-label)', padding: '5px 6px', marginBottom: 3, border: `1px solid ${COL.border}`, borderRadius: 4, background: '#fafafa', color: COL.textMain, fontFamily: FONT, cursor: (!hasUrl || !locked) ? 'default' : 'pointer', opacity: (!hasUrl || !locked) ? 0.5 : 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  <i className="ti ti-photo-plus" style={{ fontSize: 11, marginRight: 5 }} />{f.nom_fitxer}
                </button>
              )
            })}

            {/* Propietats de l'objecte seleccionat (TS-4b) */}
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
                      <ColorPicker value={selObj.fill || 'var(--text-main)'} onChange={c => updateObject(selObj.id, { fill: c })} />
                    </div>
                  </>
                )}
                {(selObj.type === 'rect' || selObj.type === 'ellipse' || selObj.type === 'line' || selObj.type === 'arrow') && (
                  <>
                    <div style={propLabel}>{t('tech_sheet.stroke_color')}
                      <ColorPicker value={selObj.stroke || 'var(--text-main)'} onChange={c => updateObject(selObj.id, { stroke: c, ...(selObj.type === 'arrow' ? { fill: c } : {}) })} />
                    </div>
                    <label style={propLabel}>{t('tech_sheet.stroke_width')}
                      <input type="number" min={0.5} max={5} step={0.5} value={selObj.strokeWidth || (selObj.type === 'arrow' ? 1.5 : 1)}
                        onChange={e => updateObject(selObj.id, { strokeWidth: Number(e.target.value) || 1 })} style={propInput} />
                    </label>
                  </>
                )}
                {(selObj.type === 'rect' || selObj.type === 'ellipse') && (
                  <div style={propLabel}>{t('tech_sheet.fill')}
                    <ColorPicker value={selObj.fill && selObj.fill !== 'transparent' ? selObj.fill : 'var(--white)'} onChange={c => updateObject(selObj.id, { fill: c })} />
                  </div>
                )}
                {selObj.type === 'data_block' && (
                  <label style={propLabel}>{t('tech_sheet.scale_pct')}
                    <input type="number" min={10} max={200} step={5} value={Math.round((selObj.scale || 1) * 100)}
                      onChange={e => updateObject(selObj.id, { scale: Math.max(0.1, (Number(e.target.value) || 100) / 100) })} style={propInput} />
                  </label>
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

      {/* Selector de size fitting (>1) */}
      {pickFitting && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }} onClick={() => setPickFitting(false)}>
          <div onClick={e => e.stopPropagation()} style={{ background: 'var(--white)', borderRadius: 12, padding: '1.4rem', maxWidth: 360, width: '90%', fontFamily: FONT }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 12 }}>{t('tech_sheet.pick_size_fitting')}</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {sizeFittings.map(sf => (
                <button key={sf.id} onClick={() => { setPickFitting(false); insertGradedTable(sf.id) }}
                  style={{ textAlign: 'left', fontSize: 'var(--fs-body)', padding: '8px 10px', border: `1px solid ${COL.border}`, borderRadius: 6, background: '#fafafa', color: COL.textMain, fontFamily: FONT, cursor: 'pointer' }}>
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
const QUICK_COLORS = ['var(--text-main)', '#185fa5', '#1d9e75', '#dc2626', 'var(--gold)', '#ca8a04']
export function ColorPicker({ value, onChange }) {
  const { t } = useTranslation()
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap', marginTop: 3 }}>
      {QUICK_COLORS.map(c => (
        <button key={c} type="button" onClick={() => onChange(c)} title={c}
          style={{ width: 18, height: 18, borderRadius: '50%', background: c, border: value === c ? '2px solid var(--text-main)' : '1px solid var(--border)', cursor: 'pointer', padding: 0 }} />
      ))}
      <input type="color" value={value || 'var(--text-main)'} onChange={e => onChange(e.target.value)} title={t('tech_sheet.more_colors')}
        style={{ width: 22, height: 22, border: 'none', borderRadius: 4, cursor: 'pointer', padding: 0, background: 'none' }} />
    </div>
  )
}

export function SectionTitle({ children }) {
  return <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, color: COL.gold, textTransform: 'uppercase', letterSpacing: '0.05em', margin: '12px 0 6px' }}>{children}</div>
}
export const propLabel = { display: 'block', fontSize: 'var(--fs-label)', color: COL.textMuted, marginBottom: 8 }
export const propInput = { width: '100%', fontFamily: FONT, fontSize: 'var(--fs-body)', padding: '4px 6px', marginTop: 3, border: `1px solid ${COL.border}`, borderRadius: 5, background: 'var(--white)', color: COL.textMain, boxSizing: 'border-box' }
