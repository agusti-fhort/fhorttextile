import { useEffect, useImperativeHandle, useRef, useState, forwardRef } from 'react'
import paper from 'paper'
import { removeNode, toCorner, toSmooth, addNodeAt, mirrorHandle, closeSegments, openAtNode, splitAtNode, splitAtLocation, moveSegment, deleteSegment, translateSubpath, booleanSubpaths, mirrorSubpath, scaleSubpath, rotateSubpath } from './ftt/paperOps'

const PAPER_COL = {
  node: '#185fa5',
  nodeSel: '#c0392b',
  handle: '#c27a2a',
  helper: '#868685',
  segSel: '#2e8b57',   // F2 — tram (segment) seleccionat: verd, diferenciat del node (vermell)
  segHover: '#7cc0a0', // F2 — preressalt de segment en hover
  white: '#ffffff',
}

const NODE_SIZE = 7
const HANDLE_SIZE = 6
const HIT_SIZE = 18
const DEFAULT_HANDLE_OFFSET = 22

// F1 — el sub-editor NO té UI pròpia: les eines viuen a la barra superior del pare. Aquí només el
// canvas Paper + la lògica. El pare controla l'eina activa (prop `nodeTool`), rep l'estat de selecció
// (`onNodeState`) i dispara accions per l'API imperativa `run(name, ...args)` (ref).
const PaperFlatEditor = forwardRef(function PaperFlatEditor({ flat, pageW, pageH, toPx, zoom = 1, onCommit, onSplitObject, onNodeState, nodeTool = 'shape', onCanCommitChange, onEnterDirect }, ref) {
  const canvasRef = useRef(null)
  const scopeRef = useRef(null)
  const sketchLayerRef = useRef(null)
  const uiLayerRef = useRef(null)
  const selectedPathRef = useRef(null)
  const selectedSegsRef = useRef(new Set())   // S1.3: multi-selecció d'índexs de node
  const selectedSegRef = useRef(null)         // F2: índex de corba del SEGMENT (tram) seleccionat, o null
  const selectedShapesRef = useRef(new Set()) // G1: multi-selecció de FORMES (data.index de subpath) — fletxa negra
  const lastShapeClickRef = useRef({ index: null, t: 0 })  // G1: detecció de doble-clic per entrar a selecció directa
  const dragRef = useRef(null)
  const marqueeRef = useRef(null)             // {x0,y0,rect} mentre s'arrossega una marquesina
  const paintRef = useRef({})                 // F5: overrides de pintura pendents per índex de subpath {fill,stroke,strokeWidth}
  const zoomRef = useRef(zoom)
  const refreshHandlesRef = useRef(null)      // dispatcher de refresc (node o forma segons el mode)
  const pushStateRef = useRef(null)           // puja l'estat (mode/selecció/pintura) al pare fora dels handlers
  const opsRef = useRef(null)                 // accions exposades al pare via run() (close/open/split/removeSelection…)
  const onNodeStateRef = useRef(onNodeState)  // callback per pujar {selCount} al pare
  const onEnterDirectRef = useRef(onEnterDirect)  // G1: demana al pare passar a selecció directa (doble-clic forma)
  const nodeToolRef = useRef(nodeTool)        // eina activa (llegida dins els handlers de Paper)
  const [, setStatus] = useState('')
  const [canCommit, setCanCommit] = useState(false)
  const isStructuredPath = flat?.type === 'path'

  useEffect(() => { onNodeStateRef.current = onNodeState }, [onNodeState])
  useEffect(() => { onEnterDirectRef.current = onEnterDirect }, [onEnterDirect])
  // G1 — en canviar d'eina, si es creua la frontera forma↔nodes cal repintar la capa UI (les àncores
  // de node i el ressaltat de forma són superfícies excloents) I re-sincronitzar l'estat al pare (mode
  // + comptador), perquè l'indicador i els grups d'eina de forma de la barra depenen de nodeSel.mode.
  useEffect(() => { nodeToolRef.current = nodeTool; refreshHandlesRef.current?.(); pushStateRef.current?.() }, [nodeTool])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || (!flat?.svg && !isStructuredPath)) return undefined
    setCanCommit(false)

    const scope = new paper.PaperScope()
    scope.setup(canvas)
    scopeRef.current = scope
    const sketchLayer = new scope.Layer({ name: 'flat-sketch' })
    const uiLayer = new scope.Layer({ name: 'flat-ui' })
    sketchLayerRef.current = sketchLayer
    uiLayerRef.current = uiLayer
    const cleanup = () => {
      scope.remove()
      scopeRef.current = null
      sketchLayerRef.current = null
      uiLayerRef.current = null
      selectedPathRef.current = null
      selectedSegsRef.current = new Set()
      selectedSegRef.current = null
      selectedShapesRef.current = new Set()
      lastShapeClickRef.current = { index: null, t: 0 }
      dragRef.current = null
      marqueeRef.current = null
      paintRef.current = {}
      refreshHandlesRef.current = null
      pushStateRef.current = null
    }

    const clearHandles = () => {
      uiLayer.removeChildren()
      scope.project.getItems({ selected: true }).forEach(item => { item.selected = false })
    }

    // Dibuixa àncores de TOTS els nodes + nanses dels nodes SELECCIONATS (multi-selecció).
    const refreshHandles = () => {
      clearHandles()
      const path = selectedPathRef.current
      if (!path) { scope.view.update(); return }
      path.selected = true
      uiLayer.activate()
      const sel = selectedSegsRef.current
      path.segments.forEach((segment, index) => {
        const point = segment.point
        const selected = sel.has(index)
        const anchor = new scope.Path.Rectangle({
          point: point.subtract(new scope.Point(NODE_SIZE / 2, NODE_SIZE / 2)),
          size: new scope.Size(NODE_SIZE, NODE_SIZE),
          fillColor: selected ? PAPER_COL.nodeSel : PAPER_COL.white,
          strokeColor: selected ? PAPER_COL.nodeSel : PAPER_COL.node,
          strokeWidth: 1.2,
        })
        anchor.data = { kind: 'segment', index }
        const hit = new scope.Path.Rectangle({
          point: point.subtract(new scope.Point(HIT_SIZE / 2, HIT_SIZE / 2)),
          size: new scope.Size(HIT_SIZE, HIT_SIZE),
          fillColor: PAPER_COL.white, opacity: 0.001,
        })
        hit.data = { kind: 'segment', index }; hit.sendToBack()
        if (selected) {
          const handleInVector = segment.handleIn.isZero() ? new scope.Point(-DEFAULT_HANDLE_OFFSET, 0) : segment.handleIn
          const handleOutVector = segment.handleOut.isZero() ? new scope.Point(DEFAULT_HANDLE_OFFSET, 0) : segment.handleOut
          const inPt = point.add(handleInVector)
          const outPt = point.add(handleOutVector)
          new scope.Path.Line({ from: point, to: inPt, strokeColor: PAPER_COL.helper, strokeWidth: 1, dashArray: [4, 4] })
          const inHandle = new scope.Path.Rectangle({
            point: inPt.subtract(new scope.Point(HANDLE_SIZE / 2, HANDLE_SIZE / 2)),
            size: new scope.Size(HANDLE_SIZE, HANDLE_SIZE),
            fillColor: PAPER_COL.white, strokeColor: PAPER_COL.handle, strokeWidth: 1.2,
          })
          inHandle.data = { kind: 'handleIn', index }
          const inHit = new scope.Path.Rectangle({
            point: inPt.subtract(new scope.Point(HIT_SIZE / 2, HIT_SIZE / 2)),
            size: new scope.Size(HIT_SIZE, HIT_SIZE), fillColor: PAPER_COL.white, opacity: 0.001,
          })
          inHit.data = inHandle.data
          new scope.Path.Line({ from: point, to: outPt, strokeColor: PAPER_COL.helper, strokeWidth: 1, dashArray: [4, 4] })
          const outHandle = new scope.Path.Rectangle({
            point: outPt.subtract(new scope.Point(HANDLE_SIZE / 2, HANDLE_SIZE / 2)),
            size: new scope.Size(HANDLE_SIZE, HANDLE_SIZE),
            fillColor: PAPER_COL.white, strokeColor: PAPER_COL.handle, strokeWidth: 1.2,
          })
          outHandle.data = { kind: 'handleOut', index }
          const outHit = new scope.Path.Rectangle({
            point: outPt.subtract(new scope.Point(HIT_SIZE / 2, HIT_SIZE / 2)),
            size: new scope.Size(HIT_SIZE, HIT_SIZE), fillColor: PAPER_COL.white, opacity: 0.001,
          })
          outHit.data = outHandle.data
        }
      })
      // F2 — realça el SEGMENT seleccionat (tram entre dos nodes) amb un color diferenciat del node.
      if (selectedSegRef.current != null) drawCurveHighlight(uiLayer, scope, path, selectedSegRef.current, PAPER_COL.segSel, 3.5)
      sketchLayer.activate()
      scope.view.update()
    }
    // ── G1 · MODE FORMA (fletxa negra) ────────────────────────────────────────────────────────
    const isShapeMode = () => nodeToolRef.current === 'shape'
    const allPaths = () => sketchLayer.getItems({ class: scope.Path }).filter(p => p.segments?.length)
    const pathByIndex = (idx) => allPaths().find(p => (p.data?.index ?? 0) === idx)
    // Ressalta les FORMES seleccionades (subpaths sencers) clonant-ne el traç a la capa UI en color
    // de selecció. No dibuixa àncores de node (superfície excloent de la selecció directa).
    const drawShapeSelection = () => {
      clearHandles()
      uiLayer.activate()
      const sel = selectedShapesRef.current
      allPaths().forEach(p => {
        if (!sel.has(p.data?.index ?? 0)) return
        const hl = p.clone({ insert: false })
        hl.strokeColor = PAPER_COL.nodeSel
        hl.strokeWidth = Math.max(2, (p.strokeWidth || 1) + 1)
        hl.fillColor = null
        hl.dashArray = null
        hl.data = { shapeHl: true }
        uiLayer.addChild(hl)
      })
      sketchLayer.activate()
      scope.view.update()
    }
    // Dispatcher de refresc: mode forma → ressaltat de forma; mode nodes → àncores/nanses.
    const refresh = () => { if (isShapeMode()) drawShapeSelection(); else refreshHandles() }
    refreshHandlesRef.current = refresh

    // Extreu un color CSS sòlid d'un Paper.Color de forma SEGURA: null si és nul, gradient o si toCSS
    // llança (SVG importat amb degradats). Evita petar el snapshot/pushState i degrada a "sense color".
    const cssColor = (c) => { try { return c && c.type !== 'gradient' ? c.toCSS(true) : null } catch { return null } }

    // Puja l'estat al pare per a la barra contextual: MODE (forma/nodes) + selecció + PINTURA de la
    // superfície activa (fill/stroke en CSS o null=cap; gruix en mm) perquè els swatches reflecteixin l'estat viu.
    const pushState = () => {
      const path = selectedPathRef.current
      const idx = path?.data?.index ?? 0
      const ov = paintRef.current[idx] || {}
      const fill = ov.fill != null ? (ov.fill === 'transparent' ? null : ov.fill) : cssColor(path?.fillColor)
      const stroke = ov.stroke != null ? (ov.stroke === 'transparent' ? null : ov.stroke) : cssColor(path?.strokeColor)
      const swMm = ov.strokeWidth != null ? ov.strokeWidth : ((path?.strokeWidth || 0) / (toPx(1) * (zoomRef.current || 1)))
      onNodeStateRef.current?.({
        mode: isShapeMode() ? 'shape' : 'nodes',
        shapeCount: selectedShapesRef.current.size,
        selCount: selectedSegsRef.current.size, seg: selectedSegRef.current != null,
        fill, stroke, strokeWidth: Math.round(swMm * 100) / 100,
      })
    }
    pushStateRef.current = pushState
    // F5 — aplica pintura a UN path: viu al canvas Paper + registrat a paintRef per al commit.
    const applyPaintTo = (path, kind, value) => {
      const idx = path.data?.index ?? 0
      const ov = (paintRef.current[idx] = paintRef.current[idx] || {})
      if (kind === 'strokeWidth') {
        const wMm = Math.max(0, Number(value) || 0)
        path.strokeWidth = toViewPx(wMm); ov.strokeWidth = wMm
      } else {
        const none = !value || value === 'transparent' || value === 'none'
        path[kind === 'fill' ? 'fillColor' : 'strokeColor'] = none ? null : value
        ov[kind] = none ? 'transparent' : value
      }
    }
    // F5/G4 — la pintura de la barra opera sobre la selecció del MODE ACTIU: mode forma → totes les
    // FORMES seleccionades (multi); selecció directa → la subpath activa (comportament F5 original).
    const applyPaint = (kind, value) => {
      const primary = selectedPathRef.current
      if (!primary) return
      pushHistory()
      const targets = isShapeMode() && selectedShapesRef.current.size
        ? [...selectedShapesRef.current].map(pathByIndex).filter(Boolean)
        : [primary]
      targets.forEach(p => applyPaintTo(p, kind, value))
      scope.view.update()
      if (isShapeMode()) drawShapeSelection()
      pushState()
    }

    // F6/G2 — HISTÒRIA INTERNA de la sessió d'edició (undo/redo sense sortir del mode). Instantània de
    // TOTA l'escena (totes les formes: segments view px + closed + estil) + pintura pendent + forma
    // primària. Full-scene perquè les operacions de FORMA (moure/esborrar/duplicar/booleanes) canvien
    // el CONJUNT de subpaths, no només la path activa. En sortir amb "Fet" → 1 sol commit al model;
    // Escape cancel·la tot. Les operacions que bombollen objectes al pare (split/tisores) van a la
    // història del MODEL, no aquí.
    const historyRef = { past: [], future: [] }
    const snapshot = () => ({
      primary: selectedPathRef.current?.data?.index ?? null,
      paths: allPaths().map(p => ({
        index: p.data?.index ?? 0, segments: readSegs(p), closed: !!p.closed,
        fill: cssColor(p.fillColor), stroke: cssColor(p.strokeColor),
        strokeWidth: p.strokeWidth || 0,
      })),
      paint: JSON.parse(JSON.stringify(paintRef.current)),
    })
    const pushHistory = () => { historyRef.past.push(snapshot()); if (historyRef.past.length > 100) historyRef.past.shift(); historyRef.future = [] }
    const restore = (snap) => {
      if (!snap) return
      sketchLayer.getItems({ class: scope.Path }).forEach(p => p.remove())
      sketchLayer.activate()
      snap.paths.forEach(sp => {
        const p = new scope.Path({ closed: sp.closed, strokeColor: sp.stroke, strokeWidth: sp.strokeWidth, fillColor: sp.fill })
        sp.segments.forEach(s => p.add(new scope.Segment(new scope.Point(s.x, s.y), new scope.Point(s.inX || 0, s.inY || 0), new scope.Point(s.outX || 0, s.outY || 0))))
        p.data = { index: sp.index }
        sketchLayer.addChild(p)
      })
      paintRef.current = snap.paint || {}
      selectedPathRef.current = (snap.primary != null ? pathByIndex(snap.primary) : null) || allPaths()[0] || null
      selectedShapesRef.current = new Set([...selectedShapesRef.current].filter(i => pathByIndex(i) != null))
      selectedSegsRef.current = new Set()
      selectedSegRef.current = null
      refresh()
      pushState()
    }

    const setSelection = (indices) => {
      selectedSegsRef.current = new Set(indices)
      selectedSegRef.current = null   // seleccionar nodes esborra la selecció de segment (excloents)
      refreshHandles()
      pushState()
    }
    // F2 — selecciona un SEGMENT (tram) per índex de corba; esborra la selecció de nodes.
    const selectSegment = (curveIndex) => {
      selectedSegsRef.current = new Set()
      selectedSegRef.current = curveIndex
      refreshHandles()
      pushState()
    }

    const selectPath = (item) => {
      selectedPathRef.current = item
      setSelection(item ? [0] : [])
    }
    // G1 — selecció de FORMES (mode fletxa negra): fixa el conjunt de subpaths seleccionats i el path
    // primari (l'últim tocat), sobre el qual operen pintura/transformacions d'una sola forma.
    const setShapeSelection = (indices, primaryIndex) => {
      selectedShapesRef.current = new Set(indices)
      if (primaryIndex != null) { const p = pathByIndex(primaryIndex); if (p) selectedPathRef.current = p }
      drawShapeSelection()
      pushState()
    }

    // Reconstrueix la geometria d'UN path concret a partir d'un array de segments (mateix espai view px).
    const rebuildPath = (path, segs, closed) => {
      if (!path) return
      path.removeSegments()
      ;(segs || []).forEach(s => path.add(new scope.Segment(
        new scope.Point(s.x, s.y),
        new scope.Point(s.inX || 0, s.inY || 0),
        new scope.Point(s.outX || 0, s.outY || 0),
      )))
      if (closed != null) path.closed = !!closed
    }
    // Reconstrueix la path ACTIVA (compat amb els handlers de node existents).
    const rebuild = (segs, closed) => rebuildPath(selectedPathRef.current, segs, closed)

    // ── G2 · OPERACIONS SOBRE FORMES (mode fletxa negra) ────────────────────────────────────────
    const toMm = (px) => (px || 0) / (toPx(1) * (zoomRef.current || 1))
    const nextShapeIndex = () => allPaths().reduce((m, p) => Math.max(m, p.data?.index ?? 0), -1) + 1
    // Registra l'estil viu d'un path a paintRef (fill/stroke CSS + gruix mm) perquè el commit el
    // conservi en una forma NOVA (duplicat/booleana) sense entrada d'origen a flat.paths.
    const registerPaint = (p) => {
      const idx = p.data?.index ?? 0
      paintRef.current[idx] = {
        fill: cssColor(p.fillColor) || 'transparent',
        stroke: cssColor(p.strokeColor) || 'transparent',
        strokeWidth: Math.round(toMm(p.strokeWidth) * 100) / 100,
      }
    }
    // Duplica les formes seleccionades (clons amb índex nou + estil registrat). Retorna els índexs nous.
    const duplicateSelectedShapes = () => {
      const created = []
      ;[...selectedShapesRef.current].forEach(idx => {
        const src = pathByIndex(idx)
        if (!src) return
        const dup = src.clone({ insert: false })
        dup.data = { index: nextShapeIndex() }
        sketchLayer.addChild(dup)
        registerPaint(dup)
        created.push(dup.data.index)
      })
      return created
    }
    // Esborra les formes seleccionades (Delete en mode forma). Neteja la pintura pendent associada.
    const deleteSelectedShapes = () => {
      const sel = selectedShapesRef.current
      if (!sel.size) return
      pushHistory()
      allPaths().forEach(p => { const i = p.data?.index ?? 0; if (sel.has(i)) { delete paintRef.current[i]; p.remove() } })
      selectedShapesRef.current = new Set()
      selectedPathRef.current = allPaths()[0] || null
      drawShapeSelection(); pushState()
    }
    // G3 — BOOLEANA entre les formes seleccionades (2+). Substitueix in-place les formes operades pel
    // resultat DINS el mateix path compost (el flat segueix sent un objecte; canvia la geometria
    // interna). Ordre z baix→dalt (la forma inferior resta les superiors, com el buscatraços d'objecte).
    const booleanSelectedShapes = (op) => {
      const sel = selectedShapesRef.current
      if (sel.size < 2) return
      const ordered = allPaths().filter(p => sel.has(p.data?.index ?? 0))   // z-order baix→dalt
      if (ordered.length < 2) return
      const subpaths = ordered.map(p => ({ segments: readSegs(p), closed: p.closed }))
      const res = booleanSubpaths(subpaths, op)
      // M1 — si el resultat és buit (formes obertes o disjuntes: intersecar sense solapament, restar que
      // s'anul·la…) NO esborris les formes font: seria una desaparició silenciosa. No-op segur.
      if (!res || !res.length) return
      pushHistory()   // instantània amb les formes originals encara a l'escena
      const base = ordered[0]
      const style = { stroke: cssColor(base.strokeColor), fill: cssColor(base.fillColor), sw: base.strokeWidth || 0 }
      ordered.forEach(p => { delete paintRef.current[p.data?.index ?? 0]; p.remove() })
      const created = []
      ;(res || []).forEach(r => {
        const np = new scope.Path({ closed: r.closed, strokeColor: style.stroke, strokeWidth: style.sw, fillColor: style.fill })
        r.segments.forEach(s => np.add(new scope.Segment(new scope.Point(s.x, s.y), new scope.Point(s.inX || 0, s.inY || 0), new scope.Point(s.outX || 0, s.outY || 0))))
        np.data = { index: nextShapeIndex() }
        sketchLayer.addChild(np)
        registerPaint(np)
        created.push(np.data.index)
      })
      selectedPathRef.current = created.length ? pathByIndex(created[created.length - 1]) : (allPaths()[0] || null)
      setShapeSelection(created, selectedPathRef.current?.data?.index)
    }
    // G5 — ALINEAR les formes seleccionades (2+) sobre els bounds del conjunt (mateixa lògica que
    // l'alinear d'objectes, aplicada a bounds de subpath). mode ∈ left/center/right/top/middle/bottom.
    const alignShapes = (mode) => {
      const paths = [...selectedShapesRef.current].map(pathByIndex).filter(Boolean)
      if (paths.length < 2) return
      pushHistory()
      const bs = paths.map(p => p.bounds)
      const minX = Math.min(...bs.map(b => b.left)), maxX = Math.max(...bs.map(b => b.right))
      const minY = Math.min(...bs.map(b => b.top)), maxY = Math.max(...bs.map(b => b.bottom))
      paths.forEach(p => {
        const b = p.bounds
        let dx = 0, dy = 0
        if (mode === 'left') dx = minX - b.left
        if (mode === 'center') dx = (minX + maxX) / 2 - (b.left + b.right) / 2
        if (mode === 'right') dx = maxX - b.right
        if (mode === 'top') dy = minY - b.top
        if (mode === 'middle') dy = (minY + maxY) / 2 - (b.top + b.bottom) / 2
        if (mode === 'bottom') dy = maxY - b.bottom
        if (dx || dy) p.translate(new scope.Point(dx, dy))
      })
      drawShapeSelection(); pushState()
    }
    // G5 — DISTRIBUIR les formes seleccionades (3+) amb espais iguals (axis 'h'/'v').
    const distributeShapes = (axis) => {
      const paths = [...selectedShapesRef.current].map(pathByIndex).filter(Boolean)
      if (paths.length < 3) return
      pushHistory()
      const entries = paths.map(p => ({ p, b: p.bounds })).sort((a, b) => axis === 'h' ? a.b.left - b.b.left : a.b.top - b.b.top)
      const start = axis === 'h' ? entries[0].b.left : entries[0].b.top
      const end = axis === 'h' ? entries[entries.length - 1].b.right : entries[entries.length - 1].b.bottom
      const totalSize = entries.reduce((s, e) => s + (axis === 'h' ? e.b.width : e.b.height), 0)
      const gap = (end - start - totalSize) / (entries.length - 1)
      let cursor = start
      entries.forEach(e => {
        const cur = axis === 'h' ? e.b.left : e.b.top
        const d = cursor - cur
        if (d) e.p.translate(axis === 'h' ? new scope.Point(d, 0) : new scope.Point(0, d))
        cursor += (axis === 'h' ? e.b.width : e.b.height) + gap
      })
      drawShapeSelection(); pushState()
    }
    // G5 — TRANSFORMA cada forma seleccionada respecte del SEU centre (mirall/escalar/rotar). `fn` és
    // una funció pura de paperOps que rep (segments, cx, cy) i retorna {segments}. Bounds via Paper
    // (inclou extrems bezier). S'ha triat accions de barra en lloc de nanses de bbox dins Paper (cost alt).
    const transformShapes = (fn) => {
      const paths = [...selectedShapesRef.current].map(pathByIndex).filter(Boolean)
      if (!paths.length) return
      pushHistory()
      paths.forEach(p => { const c = p.bounds.center; const r = fn(readSegs(p), c.x, c.y); rebuildPath(p, r.segments) })
      drawShapeSelection(); pushState()
    }
    // G5 — Z-ORDRE de la forma primària dins el compost (reordena l'ordre de subpaths, que és el que
    // llegeix el commit i el que fa servir el subtract de G3). insertAbove/insertBelow ordenen segons
    // la seqüència de getItems (allPaths), robust encara que les formes tinguin pares diferents.
    const reorderShape = (dir) => {
      const p = selectedPathRef.current
      const order = allPaths()
      const pos = order.indexOf(p)
      if (!p || pos < 0 || order.length < 2) return
      pushHistory()
      if (dir === 'front') { const top = order[order.length - 1]; if (top !== p) p.insertAbove(top) }
      else if (dir === 'back') { const bot = order[0]; if (bot !== p) p.insertBelow(bot) }
      else if (dir === 'forward') { const nx = order[pos + 1]; if (nx) p.insertAbove(nx) }
      else if (dir === 'backward') { const pv = order[pos - 1]; if (pv) p.insertBelow(pv) }
      drawShapeSelection(); pushState()
    }

    const toViewPx = (mm) => toPx(mm) * zoomRef.current
    const rotation = ((flat.rotation || 0) * Math.PI) / 180
    const scaleX = flat.scaleX || 1
    const scaleY = flat.scaleY || 1
    const cos = Math.cos(rotation)
    const sin = Math.sin(rotation)
    const transformVector = (x = 0, y = 0) => {
      const sx = x * scaleX, sy = y * scaleY
      return { x: sx * cos - sy * sin, y: sx * sin + sy * cos }
    }
    const localToView = (x = 0, y = 0) => {
      const v = transformVector(x, y)
      return new scope.Point(toViewPx((flat.x || 0) + v.x), toViewPx((flat.y || 0) + v.y))
    }
    const handleToView = (x = 0, y = 0) => {
      const v = transformVector(x, y)
      return new scope.Point(toViewPx(v.x), toViewPx(v.y))
    }

    sketchLayer.activate()
    let imported
    if (isStructuredPath) {
      imported = new scope.Group()
      ;(flat.paths || []).forEach((pathData, index) => {
        const path = new scope.Path({
          closed: !!(pathData.subpaths ? pathData.subpaths[0]?.closed : pathData.closed),
          strokeColor: flat.stroke || pathData.stroke || '#1f2937',
          strokeWidth: toViewPx(flat.strokeWidth || pathData.strokeWidth || 1.2),
          fillColor: (flat.fill ?? pathData.fill) && (flat.fill ?? pathData.fill) !== 'transparent' ? (flat.fill ?? pathData.fill) : null,
        })
        path.data = { index }
        const segs = pathData.subpaths ? (pathData.subpaths[0]?.segments || []) : (pathData.segments || [])
        segs.forEach(seg => path.add(new scope.Segment(localToView(seg.x, seg.y), handleToView(seg.inX, seg.inY), handleToView(seg.outX, seg.outY))))
        imported.addChild(path)
      })
    } else {
      try {
        imported = scope.project.importSVG(flat.svg, { insert: true, expandShapes: true })
      } catch {
        setStatus('')
        sketchLayerRef.current = null
        return cleanup
      }
      const bounds = imported.bounds
      const targetW = Math.max(1, toViewPx(flat.width || 80))
      const targetH = Math.max(1, toViewPx(flat.height || 60))
      const scale = Math.min(targetW / bounds.width, targetH / bounds.height)
      if (Number.isFinite(scale) && scale > 0) imported.scale(scale)
      imported.position = new scope.Point(toViewPx(flat.x || 0) + targetW / 2, toViewPx(flat.y || 0) + targetH / 2)
    }
    setCanCommit(true)
    // G1/G2 — garanteix un ÍNDEX de forma estable per subpath: les importacions SVG no en porten
    // (queden totes a 0 i col·lapsarien la selecció de forma). No afecta el commit d'SVG, que exporta
    // la capa sencera; sí que habilita selecció/moviment/duplicat/booleanes per forma.
    imported.getItems({ class: scope.Path }).filter(p => p.segments?.length).forEach((p, i) => { if (p.data?.index == null) p.data = { ...(p.data || {}), index: i } })

    const firstPath = imported.getItems({ class: scope.Path }).find(path => path.segments?.length)
    if (firstPath) {
      selectPath(firstPath)
      // G1 — el mode per defecte en entrar al sub-editor és FORMA: el primer gest natural és agafar una
      // forma, no un node. Sembra la primera forma seleccionada i pinta el ressaltat de forma.
      if (isShapeMode()) setShapeSelection([firstPath.data?.index ?? 0], firstPath.data?.index ?? 0)
    } else setStatus('')

    // Aplica una operació de paperOps (retorna {segments,closed?}) i refresca; nextSel = índexs a seleccionar.
    const applyOp = (result, nextSel) => {
      if (!result) return
      const path = selectedPathRef.current
      pushHistory()
      rebuild(result.segments, result.closed != null ? result.closed : path.closed)
      setSelection(nextSel != null ? nextSel : [])
      setStatus('')
    }

    // Conversió d'un segment de l'espai VIEW px a l'espai LOCAL del flat (mateixa matemàtica que commit),
    // per bombollar una peça separada al pare com a objecte nou (split/tisores).
    const invRot = -(((flat.rotation || 0) * Math.PI) / 180)
    const icos = Math.cos(invRot), isin = Math.sin(invRot)
    const fromViewMm = (pt) => ({ x: pt.x / toPx(1) / (zoomRef.current || 1), y: pt.y / toPx(1) / (zoomRef.current || 1) })
    const ptToLocal = (x, y) => { const p = fromViewMm({ x, y }); const dx = p.x - (flat.x || 0), dy = p.y - (flat.y || 0); return { x: (dx * icos - dy * isin) / scaleX, y: (dx * isin + dy * icos) / scaleY } }
    const hToLocal = (x, y) => { const p = fromViewMm({ x, y }); return { x: (p.x * icos - p.y * isin) / scaleX, y: (p.x * isin + p.y * icos) / scaleY } }
    const segViewToLocal = (s) => {
      const pt = ptToLocal(s.x, s.y), hin = hToLocal(s.inX, s.inY), hout = hToLocal(s.outX, s.outY)
      return { x: pt.x, y: pt.y, inX: hin.x, inY: hin.y, outX: hout.x, outY: hout.y }
    }
    // Divideix la path viva en dues: la peça A es queda; la B es bombolla al pare com a objecte nou.
    const splitInTwo = (pieces) => {
      if (!pieces || !pieces.length) return
      if (pieces.length === 1) { applyOp(pieces[0], []); return }
      rebuild(pieces[0].segments, pieces[0].closed)
      setSelection([])
      onSplitObject?.({ segments: pieces[1].segments.map(segViewToLocal), closed: pieces[1].closed })
      setStatus('')
    }

    // Esborrat sensible al MODE i al context de la selecció (G2/G4): mode forma → esborra la/les
    // FORMA/ES; mode nodes → si hi ha un SEGMENT seleccionat, obre el path per allà (deleteSegment);
    // si no, treu els NODES seleccionats (removeNode). Mai sorpreses d'abast.
    const removeSelection = () => {
      if (isShapeMode()) { deleteSelectedShapes(); return }
      const path = selectedPathRef.current
      if (!path) return
      if (selectedSegRef.current != null) {   // F2 — esborrar segment = obrir el path per allà
        splitInTwo(deleteSegment(readSegs(path), path.closed, selectedSegRef.current))
        selectedSegRef.current = null
        return
      }
      const sel = [...selectedSegsRef.current].sort((a, b) => b - a)
      if (!sel.length) return
      let segs = readSegs(path), closed = path.closed, ok = true
      for (const idx of sel) { const r = removeNode(segs, closed, idx); if (!r) { ok = false; break } segs = r.segments; closed = r.closed }
      if (ok) { rebuild(segs, closed); setSelection([]) }
    }

    // Accions exposades al pare (barra superior contextual) via run(name). (S2b + F1)
    opsRef.current = {
      close: () => { const p = selectedPathRef.current; if (p && !p.closed) applyOp(closeSegments(readSegs(p)), [...selectedSegsRef.current]) },
      open: () => { const p = selectedPathRef.current; const sel = [...selectedSegsRef.current]; if (p && p.closed && sel.length === 1) applyOp(openAtNode(readSegs(p), true, sel[0]), []) },
      split: () => { const p = selectedPathRef.current; const sel = [...selectedSegsRef.current]; if (p && sel.length === 1) splitInTwo(splitAtNode(readSegs(p), p.closed, sel[0])) },
      removeSelection,
      booleanShapes: (op) => booleanSelectedShapes(op),   // G3 — buscatraços entre formes seleccionades
      alignShapes: (mode) => alignShapes(mode),           // G5 — alinear formes seleccionades
      distributeShapes: (axis) => distributeShapes(axis), // G5 — distribuir formes seleccionades
      mirrorShapes: (axis) => transformShapes((s, cx, cy) => mirrorSubpath(s, axis, cx, cy)),   // G5 — mirall H/V
      scaleShapes: (pct) => { const f = (Number(pct) || 0) / 100; if (f > 0) transformShapes((s, cx, cy) => scaleSubpath(s, f, f, cx, cy)) },  // G5 — escalar %
      rotateShapes: (deg) => { const d = Number(deg) || 0; if (d) transformShapes((s, cx, cy) => rotateSubpath(s, d, cx, cy)) },   // G5 — rotar angle
      reorderShape: (dir) => reorderShape(dir),   // G5 — z-ordre de la forma dins el compost (front/back/forward/backward)
      setFill: (c) => applyPaint('fill', c),
      setStroke: (c) => applyPaint('stroke', c),
      setStrokeWidth: (w) => applyPaint('strokeWidth', w),
      // F6/G4 — Cmd+A sensible al mode: forma → totes les FORMES; nodes → tots els nodes del path actiu.
      selectAll: () => {
        if (isShapeMode()) { setShapeSelection(allPaths().map(p => p.data?.index ?? 0), selectedPathRef.current?.data?.index); return }
        const p = selectedPathRef.current; if (p) setSelection(p.segments.map((_, i) => i))
      },
      // F6/G2 — nudge (fletxes 1px · Shift 10px) sensible al mode: forma → translada la/les forma/es
      // (translateSubpath); nodes → mou el segment o els nodes seleccionats.
      nudge: (dx, dy) => {
        if (isShapeMode()) {
          const sel = [...selectedShapesRef.current]
          if (!sel.length) return
          pushHistory()
          sel.forEach(i => { const p = pathByIndex(i); if (p) { const r = translateSubpath(readSegs(p), dx, dy); rebuildPath(p, r.segments) } })
          drawShapeSelection(); return
        }
        const path = selectedPathRef.current
        if (!path) return
        if (selectedSegRef.current != null) { pushHistory(); const r = moveSegment(readSegs(path), path.closed, selectedSegRef.current, dx, dy); rebuild(r.segments, path.closed); refreshHandles(); return }
        const sel = [...selectedSegsRef.current]
        if (!sel.length) return
        pushHistory()
        sel.forEach(i => { const s = path.segments[i]; if (s) s.point = s.point.add(new scope.Point(dx, dy)) })
        refreshHandles()
      },
      // F6 — undo/redo INTERN (no surt del mode). Escape segueix cancel·lant tot.
      undo: () => { if (!historyRef.past.length) return; historyRef.future.push(snapshot()); restore(historyRef.past.pop()) },
      redo: () => { if (!historyRef.future.length) return; historyRef.past.push(snapshot()); restore(historyRef.future.pop()) },
    }

    const tool = new scope.Tool()
    tool.onMouseDown = (event) => {
      const path = selectedPathRef.current
      const active = nodeToolRef.current
      const uiHit = uiLayer.hitTest(event.point, { fill: true, stroke: true, tolerance: 8 })
      const data = uiHit?.item?.data
      const shift = !!event.modifiers?.shift

      // ── G1 · MODE FORMA (fletxa negra): clic = selecciona la forma sencera; shift = multi;
      // doble-clic sobre una forma = entra a selecció directa amb aquella forma activa. ──────────
      if (active === 'shape') {
        const hit = sketchLayer.hitTest(event.point, { fill: true, stroke: true, tolerance: 8 })
        const hitPath = hit?.item?.className === 'Path' ? hit.item : hit?.item?.parent?.getItem?.({ class: scope.Path })
        if (hitPath && hitPath.segments?.length) {
          const idx = hitPath.data?.index ?? 0
          const now = Date.now()
          const last = lastShapeClickRef.current
          if (!shift && last.index === idx && (now - last.t) < 350) {   // doble-clic → selecció directa
            lastShapeClickRef.current = { index: null, t: 0 }
            selectPath(hitPath)
            onEnterDirectRef.current?.()
            return
          }
          lastShapeClickRef.current = { index: idx, t: now }
          const sel = selectedShapesRef.current
          if (shift) { sel.has(idx) ? sel.delete(idx) : sel.add(idx); setShapeSelection([...sel], idx) }
          else if (!sel.has(idx)) setShapeSelection([idx], idx)
          else selectedPathRef.current = hitPath   // ja seleccionada: refixa el primari
          // G2 — inicia el moviment de forma (Alt = duplicar en arrossegar, estàndard Illustrator).
          dragRef.current = { kind: 'shape', alt: !!(event.modifiers?.option || event.modifiers?.alt) }
        } else if (!shift) {
          lastShapeClickRef.current = { index: null, t: 0 }
          setShapeSelection([])
        }
        return
      }

      // ── Sobre un NODE (àncora) ──────────────────────────────────────────────
      if (data?.kind === 'segment') {
        if (active === 'remove') {   // eina treure: clic directe elimina el node
          applyOp(removeNode(readSegs(path), path.closed, data.index), [])
          return
        }
        if (active === 'convert') {  // eina convertir: cantonada↔suau
          const seg = path.segments[data.index]
          const hasHandles = !seg.handleIn.isZero() || !seg.handleOut.isZero()
          applyOp(hasHandles ? toCorner(readSegs(path), data.index) : toSmooth(readSegs(path), path.closed, data.index), [data.index])
          return
        }
        // eina select (o qualsevol): gestiona selecció + inici de drag.
        const sel = selectedSegsRef.current
        if (shift) { sel.has(data.index) ? sel.delete(data.index) : sel.add(data.index); setSelection([...sel]) }
        else if (!sel.has(data.index)) setSelection([data.index])
        dragRef.current = { kind: 'segment' }
        return
      }
      // ── Sobre una NANSA ─────────────────────────────────────────────────────
      if (data?.kind === 'handleIn' || data?.kind === 'handleOut') {
        dragRef.current = { kind: data.kind, index: data.index }
        return
      }
      // ── Sobre el TRAÇ (corba) ───────────────────────────────────────────────
      const strokeHit = sketchLayer.hitTest(event.point, { stroke: true, tolerance: 8 })
      if (active === 'add' && strokeHit?.location && strokeHit.item === path) {
        const r = addNodeAt(readSegs(path), path.closed, strokeHit.location.curve.index, strokeHit.location.time)
        applyOp(r, r && r.index != null ? [r.index] : [])   // selecciona el node nou
        return
      }
      if (active === 'scissors' && strokeHit?.location && strokeHit.item === path) {   // tisores: tall arbitrari
        splitInTwo(splitAtLocation(readSegs(path), path.closed, strokeHit.location.curve.index, strokeHit.location.time))
        return
      }
      // F2 — eina moure: clic sobre el TRAÇ entre dos nodes selecciona el SEGMENT i n'inicia el drag.
      if (active === 'select' && strokeHit?.location && strokeHit.item === path) {
        selectSegment(strokeHit.location.curve.index)
        dragRef.current = { kind: 'segmentBody', curveIndex: strokeHit.location.curve.index }
        return
      }
      // Canviar de path (clic sobre una altra subpath) o iniciar marquesina.
      const anyHit = sketchLayer.hitTest(event.point, { fill: true, stroke: true, tolerance: 8 })
      const hitPath = anyHit?.item?.className === 'Path' ? anyHit.item : anyHit?.item?.parent?.getItem?.({ class: scope.Path })
      if (hitPath && hitPath !== path) { selectPath(hitPath); return }
      if (active === 'select') { marqueeRef.current = { x0: event.point.x, y0: event.point.y }; if (!shift) setSelection([]) }
    }

    tool.onMouseDrag = (event) => {
      const path = selectedPathRef.current
      const drag = dragRef.current
      if (marqueeRef.current) {   // marquesina de selecció
        marqueeRef.current.now = event.point
        drawMarquee(uiLayer, scope, marqueeRef.current)
        return
      }
      if (!drag || !path) return
      if (!drag.pushed) { pushHistory(); drag.pushed = true }   // F6 — 1 sola instantània per gest de drag
      if (drag.kind === 'shape') {   // G2 — mou la/les FORMA/ES seleccionada/es (translació del subpath)
        if (drag.alt && !drag.duped) {   // Alt+arrossegar = duplica i mou la còpia (estàndard Illustrator)
          drag.duped = true
          const created = duplicateSelectedShapes()
          if (created.length) { selectedShapesRef.current = new Set(created); selectedPathRef.current = pathByIndex(created[created.length - 1]) }
        }
        selectedShapesRef.current.forEach(i => { const p = pathByIndex(i); if (p) p.translate(event.delta) })
        drawShapeSelection()
        return
      }
      if (drag.kind === 'segmentBody') {   // F2 — mou el SEGMENT (recte: translació; corb: deforma nanses)
        const r = moveSegment(readSegs(path), path.closed, drag.curveIndex, event.delta.x, event.delta.y)
        rebuild(r.segments, path.closed)
        refreshHandles()
        return
      }
      if (drag.kind === 'segment') {   // mou TOTS els nodes seleccionats
        selectedSegsRef.current.forEach(i => { const s = path.segments[i]; if (s) s.point = s.point.add(event.delta) })
      } else {   // nansa: per defecte simètrica; Alt = independent
        const seg = path.segments[drag.index]
        if (!seg) return
        const alt = !!event.modifiers?.option || !!event.modifiers?.alt
        seg[drag.kind] = seg[drag.kind].add(event.delta)
        if (!alt) {
          const opp = drag.kind === 'handleIn' ? 'handleOut' : 'handleIn'
          const m = mirrorHandle(seg[drag.kind].x, seg[drag.kind].y)
          seg[opp] = new scope.Point(m.x, m.y)
        }
      }
      setStatus('')
      refreshHandles()
    }

    // Feedback de hover: amb les eines afegir/tisores, mostra ON caurà l'acció ABANS de clicar.
    tool.onMouseMove = (event) => {
      uiLayer.children.filter(c => c.data?.hover || c.data?.segHover).forEach(c => c.remove())
      const active = nodeToolRef.current
      // G1 — mode forma: preressalt de la FORMA sencera sota el cursor (si no ja seleccionada).
      if (active === 'shape') {
        const h = sketchLayer.hitTest(event.point, { fill: true, stroke: true, tolerance: 8 })
        const hp = h?.item?.className === 'Path' ? h.item : h?.item?.parent?.getItem?.({ class: scope.Path })
        if (hp && hp.segments?.length && !selectedShapesRef.current.has(hp.data?.index ?? 0)) {
          uiLayer.activate()
          const hl = hp.clone({ insert: false })
          hl.strokeColor = PAPER_COL.segHover; hl.strokeWidth = Math.max(2, (hp.strokeWidth || 1) + 1); hl.fillColor = null; hl.dashArray = null
          hl.data = { hover: true }
          uiLayer.addChild(hl)
          sketchLayer.activate()
        }
        scope.view.update(); return
      }
      const path = selectedPathRef.current
      if (!path) { scope.view.update(); return }
      const hit = sketchLayer.hitTest(event.point, { stroke: true, tolerance: 8 })
      const onCurve = hit?.location && hit.item === path
      if ((active === 'add' || active === 'scissors') && onCurve) {   // marcador d'ON caurà l'acció
        uiLayer.activate()
        const dot = new scope.Path.Circle({ center: hit.location.point, radius: 5, strokeColor: PAPER_COL.handle, strokeWidth: 1.5, fillColor: PAPER_COL.white })
        dot.data = { hover: true }
        sketchLayer.activate()
      } else if (active === 'select' && onCurve) {   // F2 — preressalt del SEGMENT sota el cursor
        const uiHit = uiLayer.hitTest(event.point, { fill: true, stroke: true, tolerance: 8 })
        if (!uiHit?.item?.data?.kind) {   // no sobre un node/nansa
          drawCurveHighlight(uiLayer, scope, path, hit.location.curve.index, PAPER_COL.segHover, 3, 'segHover')
        }
      }
      scope.view.update()
    }

    tool.onMouseUp = () => {
      if (marqueeRef.current?.now) {   // tanca la marquesina: selecciona els nodes dins el rectangle
        const path = selectedPathRef.current
        const m = marqueeRef.current
        const r = new scope.Rectangle(new scope.Point(m.x0, m.y0), new scope.Point(m.now.x, m.now.y))
        const picked = []
        path?.segments.forEach((s, i) => { if (r.contains(s.point)) picked.push(i) })
        setSelection(picked)
      }
      marqueeRef.current = null
      dragRef.current = null
    }
    tool.activate()

    // Utilitats internes (readSegs llegeix la path viva en espai view px per passar a paperOps).
    function readSegs(p) {
      return (p?.segments || []).map(seg => ({
        x: seg.point.x, y: seg.point.y,
        inX: seg.handleIn.x, inY: seg.handleIn.y,
        outX: seg.handleOut.x, outY: seg.handleOut.y,
      }))
    }

    // F1/F3 — el teclat (dreceres d'eina, Delete, nudge, Cmd+A, undo/redo) viu ARA al pare (barra
    // superior), que crida run(...) sobre aquest ref. Un sol lloc de teclat → context sempre guanya.
    return cleanup
  }, [flat, pageW, pageH, toPx, isStructuredPath])

  useEffect(() => {
    const previousZoom = zoomRef.current
    if (previousZoom === zoom) return
    zoomRef.current = zoom
    const scope = scopeRef.current
    const sketchLayer = sketchLayerRef.current
    const canvas = canvasRef.current
    if (!scope || !sketchLayer || !canvas) return
    const ratio = zoom / previousZoom
    canvas.width = pageW * zoom
    canvas.height = pageH * zoom
    scope.view.viewSize = new scope.Size(pageW * zoom, pageH * zoom)
    sketchLayer.scale(ratio, new scope.Point(0, 0))
    refreshHandlesRef.current?.()
    scope.view.update()
  }, [pageH, pageW, zoom])

  const commit = () => {
    const sketchLayer = sketchLayerRef.current
    if (!sketchLayer || !canCommit) return
    if (isStructuredPath) {
      const scope = scopeRef.current
      if (!scope) return
      const z = zoomRef.current || 1
      const rotation = -(((flat.rotation || 0) * Math.PI) / 180)
      const scaleX = flat.scaleX || 1, scaleY = flat.scaleY || 1
      const cos = Math.cos(rotation), sin = Math.sin(rotation)
      const fromViewMm = (point) => ({ x: point.x / toPx(1) / z, y: point.y / toPx(1) / z })
      const pointToLocal = (point) => {
        const p = fromViewMm(point)
        const dx = p.x - (flat.x || 0), dy = p.y - (flat.y || 0)
        return { x: (dx * cos - dy * sin) / scaleX, y: (dx * sin + dy * cos) / scaleY }
      }
      const handleToLocal = (point) => {
        const p = fromViewMm(point)
        return { x: (p.x * cos - p.y * sin) / scaleX, y: (p.x * sin + p.y * cos) / scaleY }
      }
      const segsOf = (pp) => pp.segments.map(seg => {
        const p = pointToLocal(seg.point), hin = handleToLocal(seg.handleIn), hout = handleToLocal(seg.handleOut)
        return { x: p.x, y: p.y, inX: hin.x, inY: hin.y, outX: hout.x, outY: hout.y }
      })
      const paths = sketchLayer.getItems({ class: scope.Path }).filter(path => path.segments?.length).map((path, index) => {
        const srcIdx = path.data?.index ?? index
        const source = flat.paths?.[srcIdx] || {}
        // F5 — fusiona la pintura pendent (fill/stroke/strokeWidth) de la subpath a l'entrada del model.
        const ov = paintRef.current[srcIdx] || {}
        const paint = {}
        if (ov.fill != null) paint.fill = ov.fill
        if (ov.stroke != null) paint.stroke = ov.stroke
        if (ov.strokeWidth != null) paint.strokeWidth = ov.strokeWidth
        if (source.subpaths) {
          return { ...source, ...paint, subpaths: source.subpaths.map((sp, si) => (si === 0 ? { ...sp, closed: path.closed, segments: segsOf(path) } : sp)) }
        }
        return { ...source, ...paint, closed: path.closed, segments: segsOf(path) }
      })
      onCommit({ paths })
      return
    }
    const svg = sketchLayer.exportSVG({ asString: true, bounds: 'content' })
    onCommit(svg)
  }
  // API imperativa per al pare: commit + run(name,...args) que delega a les accions del scope viu.
  useImperativeHandle(ref, () => ({ commit, run: (name, ...args) => opsRef.current?.[name]?.(...args) }))
  useEffect(() => { onCanCommitChange?.(canCommit) }, [canCommit, onCanCommitChange])

  // F1 — cap UI pròpia: només el canvas (les eines viuen a la barra superior del pare). Cursor per eina.
  const cursor = nodeTool === 'add' ? 'copy' : nodeTool === 'remove' ? 'not-allowed'
    : nodeTool === 'convert' ? 'cell' : nodeTool === 'scissors' ? 'crosshair' : 'default'
  return (
    <div style={{ position: 'absolute', left: 0, top: 0, width: pageW * zoom, height: pageH * zoom, zIndex: 20, overflow: 'hidden' }}>
      <canvas ref={canvasRef} width={pageW * zoom} height={pageH * zoom}
        style={{ position: 'absolute', left: 0, top: 0, width: pageW * zoom, height: pageH * zoom, touchAction: 'none', cursor }} />
    </div>
  )
})

// F2 — realça una CORBA (segment entre dos nodes) clonant-ne els anchors+handles a la capa UI.
function drawCurveHighlight(uiLayer, scope, path, curveIndex, color, width, tag = 'segHl') {
  const curve = path.curves?.[curveIndex]
  if (!curve) return
  uiLayer.activate()
  const hl = new scope.Path()
  hl.add(new scope.Segment(curve.segment1.point, curve.segment1.handleIn, curve.segment1.handleOut))
  hl.add(new scope.Segment(curve.segment2.point, curve.segment2.handleIn, curve.segment2.handleOut))
  hl.strokeColor = color
  hl.strokeWidth = width
  hl.data = { [tag]: true }
  hl.sendToBack()
}

// Marquesina de selecció (rectangle discontinu) dibuixada a la capa UI durant l'arrossegament.
function drawMarquee(uiLayer, scope, m) {
  const existing = uiLayer.children.find(c => c.data?.marquee)
  if (existing) existing.remove()
  if (!m.now) return
  uiLayer.activate()
  const rect = new scope.Path.Rectangle(new scope.Rectangle(new scope.Point(m.x0, m.y0), new scope.Point(m.now.x, m.now.y)))
  rect.strokeColor = PAPER_COL.node
  rect.strokeWidth = 1
  rect.dashArray = [3, 3]
  rect.data = { marquee: true }
  scope.view.update()
}

export default PaperFlatEditor
