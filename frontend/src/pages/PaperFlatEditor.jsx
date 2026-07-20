import { useEffect, useImperativeHandle, useRef, useState, forwardRef } from 'react'
import paper from 'paper'
import { removeNode, toCorner, toSmooth, addNodeAt, mirrorHandle, closeSegments, openAtNode, splitAtNode, splitAtLocation, moveSegment, deleteSegment } from './ftt/paperOps'

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
const PaperFlatEditor = forwardRef(function PaperFlatEditor({ flat, pageW, pageH, toPx, zoom = 1, onCommit, onSplitObject, onNodeState, nodeTool = 'select', onCanCommitChange }, ref) {
  const canvasRef = useRef(null)
  const scopeRef = useRef(null)
  const sketchLayerRef = useRef(null)
  const uiLayerRef = useRef(null)
  const selectedPathRef = useRef(null)
  const selectedSegsRef = useRef(new Set())   // S1.3: multi-selecció d'índexs de node
  const selectedSegRef = useRef(null)         // F2: índex de corba del SEGMENT (tram) seleccionat, o null
  const dragRef = useRef(null)
  const marqueeRef = useRef(null)             // {x0,y0,rect} mentre s'arrossega una marquesina
  const paintRef = useRef({})                 // F5: overrides de pintura pendents per índex de subpath {fill,stroke,strokeWidth}
  const zoomRef = useRef(zoom)
  const refreshHandlesRef = useRef(null)
  const opsRef = useRef(null)                 // accions exposades al pare via run() (close/open/split/removeSelection…)
  const onNodeStateRef = useRef(onNodeState)  // callback per pujar {selCount} al pare
  const nodeToolRef = useRef(nodeTool)        // eina activa (llegida dins els handlers de Paper)
  const [, setStatus] = useState('')
  const [canCommit, setCanCommit] = useState(false)
  const isStructuredPath = flat?.type === 'path'

  useEffect(() => { onNodeStateRef.current = onNodeState }, [onNodeState])
  useEffect(() => { nodeToolRef.current = nodeTool }, [nodeTool])

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
      dragRef.current = null
      marqueeRef.current = null
      paintRef.current = {}
      refreshHandlesRef.current = null
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
    refreshHandlesRef.current = refreshHandles

    // Puja l'estat al pare per a la barra contextual: selecció (nodes/segment) + PINTURA de la subpath
    // activa (fill/stroke en CSS o null=cap; gruix en mm) perquè els swatches reflecteixin l'estat viu.
    const pushState = () => {
      const path = selectedPathRef.current
      const idx = path?.data?.index ?? 0
      const ov = paintRef.current[idx] || {}
      const fill = ov.fill != null ? (ov.fill === 'transparent' ? null : ov.fill) : (path?.fillColor ? path.fillColor.toCSS(true) : null)
      const stroke = ov.stroke != null ? (ov.stroke === 'transparent' ? null : ov.stroke) : (path?.strokeColor ? path.strokeColor.toCSS(true) : null)
      const swMm = ov.strokeWidth != null ? ov.strokeWidth : ((path?.strokeWidth || 0) / (toPx(1) * (zoomRef.current || 1)))
      onNodeStateRef.current?.({
        selCount: selectedSegsRef.current.size, seg: selectedSegRef.current != null,
        fill, stroke, strokeWidth: Math.round(swMm * 100) / 100,
      })
    }
    // F5 — aplica pintura a la subpath ACTIVA: viu al canvas Paper + registrat a paintRef per al commit.
    const applyPaint = (kind, value) => {
      const path = selectedPathRef.current
      if (!path) return
      pushHistory()
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
      scope.view.update(); pushState()
    }

    // F6 — HISTÒRIA INTERNA de la sessió d'edició (undo/redo sense sortir del mode). Instantànies de
    // la path activa (segments view px + closed) + pintura pendent. En sortir amb "Fet" → 1 sol commit
    // al model; Escape cancel·la tot (sense aplicar). Les operacions que creen objectes nous al pare
    // (split/tisores obertes) van a la història del MODEL, no aquí.
    const historyRef = { past: [], future: [] }
    const snapshot = () => { const p = selectedPathRef.current; return { index: p?.data?.index ?? 0, segments: readSegs(p), closed: !!p?.closed, paint: JSON.parse(JSON.stringify(paintRef.current)) } }
    const pushHistory = () => { historyRef.past.push(snapshot()); if (historyRef.past.length > 100) historyRef.past.shift(); historyRef.future = [] }
    const syncPaintLive = (p) => {
      const ov = paintRef.current[p?.data?.index ?? 0] || {}
      if (ov.fill != null) p.fillColor = ov.fill === 'transparent' ? null : ov.fill
      if (ov.stroke != null) p.strokeColor = ov.stroke === 'transparent' ? null : ov.stroke
      if (ov.strokeWidth != null) p.strokeWidth = toViewPx(ov.strokeWidth)
    }
    const restore = (snap) => {
      if (!snap) return
      const target = sketchLayer.getItems({ class: scope.Path }).find(p => (p.data?.index ?? 0) === snap.index)
      if (target) selectedPathRef.current = target
      paintRef.current = snap.paint || {}
      rebuild(snap.segments, snap.closed)
      if (selectedPathRef.current) syncPaintLive(selectedPathRef.current)
      setSelection([])
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

    // Reconstrueix la geometria de la path activa a partir d'un array de segments (mateix espai view px).
    const rebuild = (segs, closed) => {
      const path = selectedPathRef.current
      if (!path) return
      path.removeSegments()
      ;(segs || []).forEach(s => path.add(new scope.Segment(
        new scope.Point(s.x, s.y),
        new scope.Point(s.inX || 0, s.inY || 0),
        new scope.Point(s.outX || 0, s.outY || 0),
      )))
      path.closed = !!closed
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

    const firstPath = imported.getItems({ class: scope.Path }).find(path => path.segments?.length)
    if (firstPath) selectPath(firstPath)
    else setStatus('')

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

    // Esborrat sensible al context de la selecció fina (F2/F3): si hi ha un SEGMENT seleccionat →
    // obre el path per allà (deleteSegment); si no, treu els NODES seleccionats (removeNode).
    const removeSelection = () => {
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
      setFill: (c) => applyPaint('fill', c),
      setStroke: (c) => applyPaint('stroke', c),
      setStrokeWidth: (w) => applyPaint('strokeWidth', w),
      // F6 — Cmd+A: tots els nodes del path actiu.
      selectAll: () => { const p = selectedPathRef.current; if (p) setSelection(p.segments.map((_, i) => i)) },
      // F6 — nudge (fletxes 1px · Shift 10px) sobre els nodes seleccionats (o el segment).
      nudge: (dx, dy) => {
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
