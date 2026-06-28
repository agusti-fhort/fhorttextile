import { useEffect, useRef, useState } from 'react'
import paper from 'paper'

const PAPER_COL = {
  node: '#185fa5',
  handle: '#c27a2a',
  helper: '#868685',
}

function flatBounds(flat) {
  if (flat?.type !== 'path') {
    return {
      minX: flat?.x || 0,
      minY: flat?.y || 0,
      maxX: (flat?.x || 0) + (flat?.width || 80),
      maxY: (flat?.y || 0) + (flat?.height || 60),
    }
  }
  const pts = (flat.paths || []).flatMap(path => (path.segments || []).flatMap(seg => {
    const p = { x: seg.x || 0, y: seg.y || 0 }
    return [
      p,
      { x: p.x + (seg.inX || 0), y: p.y + (seg.inY || 0) },
      { x: p.x + (seg.outX || 0), y: p.y + (seg.outY || 0) },
    ]
  }))
  if (!pts.length) return { minX: flat.x || 0, minY: flat.y || 0, maxX: flat.x || 0, maxY: flat.y || 0 }
  const sx = Math.abs(flat.scaleX || 1)
  const sy = Math.abs(flat.scaleY || 1)
  return {
    minX: (flat.x || 0) + Math.min(...pts.map(p => p.x)) * sx,
    minY: (flat.y || 0) + Math.min(...pts.map(p => p.y)) * sy,
    maxX: (flat.x || 0) + Math.max(...pts.map(p => p.x)) * sx,
    maxY: (flat.y || 0) + Math.max(...pts.map(p => p.y)) * sy,
  }
}

export default function PaperFlatEditor({ flat, pageW, pageH, toPx, zoom = 1, onCommit, onCancel, labels }) {
  const canvasRef = useRef(null)
  const scopeRef = useRef(null)
  const sketchLayerRef = useRef(null)
  const uiLayerRef = useRef(null)
  const selectedPathRef = useRef(null)
  const dragRef = useRef(null)
  const labelsRef = useRef(labels)
  const zoomRef = useRef(zoom)
  const refreshHandlesRef = useRef(null)
  const [status, setStatus] = useState(labels?.loading || '')
  const [canCommit, setCanCommit] = useState(false)
  const isStructuredPath = flat?.type === 'path'
  const bounds = flatBounds(flat)
  const pad = 18
  const left = Math.max(0, toPx(bounds.minX) * zoom - pad)
  const top = Math.max(0, toPx(bounds.minY) * zoom - pad)
  const right = Math.min(pageW * zoom, toPx(bounds.maxX) * zoom + pad)
  const bottom = Math.min(pageH * zoom, toPx(bounds.maxY) * zoom + pad)
  const overlayW = Math.max(48, right - left)
  const overlayH = Math.max(48, bottom - top)

  useEffect(() => {
    labelsRef.current = labels
  }, [labels])

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
      dragRef.current = null
      refreshHandlesRef.current = null
    }

    const clearHandles = () => {
      uiLayer.removeChildren()
      scope.project.getItems({ selected: true }).forEach(item => { item.selected = false })
    }

    const refreshHandles = () => {
      clearHandles()
      const path = selectedPathRef.current
      if (!path) {
        scope.view.update()
        return
      }
      path.selected = true
      uiLayer.activate()
      path.segments.forEach((segment, index) => {
        const point = segment.point
        const handleInPoint = point.add(segment.handleIn)
        const handleOutPoint = point.add(segment.handleOut)
        const anchor = new scope.Path.Circle({
          center: point,
          radius: 4,
          fillColor: PAPER_COL.node,
          strokeColor: 'white',
          strokeWidth: 1,
        })
        anchor.data = { kind: 'segment', index }
        if (!segment.handleIn.isZero()) {
          new scope.Path.Line({ from: point, to: handleInPoint, strokeColor: PAPER_COL.helper, strokeWidth: 1, dashArray: [4, 4] })
          const handle = new scope.Path.Circle({ center: handleInPoint, radius: 3.5, fillColor: PAPER_COL.handle })
          handle.data = { kind: 'handleIn', index }
        }
        if (!segment.handleOut.isZero()) {
          new scope.Path.Line({ from: point, to: handleOutPoint, strokeColor: PAPER_COL.helper, strokeWidth: 1, dashArray: [4, 4] })
          const handle = new scope.Path.Circle({ center: handleOutPoint, radius: 3.5, fillColor: PAPER_COL.handle })
          handle.data = { kind: 'handleOut', index }
        }
      })
      sketchLayer.activate()
      scope.view.update()
    }
    refreshHandlesRef.current = refreshHandles

    const selectPath = (item) => {
      selectedPathRef.current = item
      refreshHandles()
      setStatus(labelsRef.current?.pathSelected || '')
    }

    const toViewPx = (mm) => toPx(mm) * zoomRef.current
    const rotation = ((flat.rotation || 0) * Math.PI) / 180
    const scaleX = flat.scaleX || 1
    const scaleY = flat.scaleY || 1
    const cos = Math.cos(rotation)
    const sin = Math.sin(rotation)
    const transformVector = (x = 0, y = 0) => {
      const sx = x * scaleX
      const sy = y * scaleY
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
          closed: !!pathData.closed,
          strokeColor: flat.stroke || pathData.stroke || '#1f2937',
          strokeWidth: toViewPx(flat.strokeWidth || pathData.strokeWidth || 1.2),
          fillColor: (flat.fill ?? pathData.fill) && (flat.fill ?? pathData.fill) !== 'transparent' ? (flat.fill ?? pathData.fill) : null,
        })
        path.data = { index }
        ;(pathData.segments || []).forEach(seg => {
          path.add(new scope.Segment(
            localToView(seg.x, seg.y),
            handleToView(seg.inX, seg.inY),
            handleToView(seg.outX, seg.outY),
          ))
        })
        imported.addChild(path)
      })
    } else {
      try {
        imported = scope.project.importSVG(flat.svg, { insert: true, expandShapes: true })
      } catch {
        setStatus(labelsRef.current?.importError || '')
        sketchLayerRef.current = null
        return cleanup
      }
      const bounds = imported.bounds
      const targetW = Math.max(1, toViewPx(flat.width || 80))
      const targetH = Math.max(1, toViewPx(flat.height || 60))
      const scale = Math.min(targetW / bounds.width, targetH / bounds.height)
      if (Number.isFinite(scale) && scale > 0) imported.scale(scale)
      imported.position = new scope.Point(
        toViewPx(flat.x || 0) + targetW / 2,
        toViewPx(flat.y || 0) + targetH / 2,
      )
    }
    setCanCommit(true)

    const firstPath = imported.getItems({ class: scope.Path }).find(path => path.segments?.length)
    if (firstPath) selectPath(firstPath)
    else setStatus(labelsRef.current?.noPath || '')

    const tool = new scope.Tool()
    tool.onMouseDown = (event) => {
      const uiHit = uiLayer.hitTest(event.point, { fill: true, stroke: true, tolerance: 8 })
      if (uiHit?.item?.data?.kind) {
        dragRef.current = uiHit.item.data
        return
      }
      const hit = sketchLayer.hitTest(event.point, { fill: true, stroke: true, tolerance: 8 })
      const hitItem = hit?.item
      const path = hitItem?.className === 'Path' && hitItem.layer === sketchLayer
        ? hitItem
        : hitItem?.parent?.getItem?.({ class: scope.Path })
      if (path) selectPath(path)
    }
    tool.onMouseDrag = (event) => {
      const drag = dragRef.current
      const path = selectedPathRef.current
      if (!drag || !path) return
      const segment = path.segments[drag.index]
      if (!segment) return
      if (drag.kind === 'segment') segment.point = segment.point.add(event.delta)
      if (drag.kind === 'handleIn') segment.handleIn = segment.handleIn.add(event.delta)
      if (drag.kind === 'handleOut') segment.handleOut = segment.handleOut.add(event.delta)
      setStatus(labelsRef.current?.changed || '')
      refreshHandles()
    }
    tool.onMouseUp = () => {
      dragRef.current = null
    }
    tool.activate()

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
      const scaleX = flat.scaleX || 1
      const scaleY = flat.scaleY || 1
      const cos = Math.cos(rotation)
      const sin = Math.sin(rotation)
      const fromViewMm = (point) => ({ x: point.x / toPx(1) / z, y: point.y / toPx(1) / z })
      const pointToLocal = (point) => {
        const p = fromViewMm(point)
        const dx = p.x - (flat.x || 0)
        const dy = p.y - (flat.y || 0)
        return { x: (dx * cos - dy * sin) / scaleX, y: (dx * sin + dy * cos) / scaleY }
      }
      const handleToLocal = (point) => {
        const p = fromViewMm(point)
        return { x: (p.x * cos - p.y * sin) / scaleX, y: (p.x * sin + p.y * cos) / scaleY }
      }
      const paths = sketchLayer.getItems({ class: scope.Path }).filter(path => path.segments?.length).map((path, index) => {
        const source = flat.paths?.[path.data?.index ?? index] || {}
        return {
          ...source,
          closed: path.closed,
          segments: path.segments.map(seg => {
            const p = pointToLocal(seg.point)
            const hin = handleToLocal(seg.handleIn)
            const hout = handleToLocal(seg.handleOut)
            return { x: p.x, y: p.y, inX: hin.x, inY: hin.y, outX: hout.x, outY: hout.y }
          }),
        }
      })
      onCommit({ paths })
      return
    }
    const svg = sketchLayer.exportSVG({ asString: true, bounds: 'content' })
    onCommit(svg)
  }

  return (
    <div style={{ position: 'absolute', left, top, width: overlayW, height: overlayH, zIndex: 20, overflow: 'hidden' }}>
      <canvas
        ref={canvasRef}
        width={pageW * zoom}
        height={pageH * zoom}
        style={{ position: 'absolute', left: -left, top: -top, width: pageW * zoom, height: pageH * zoom, touchAction: 'none', cursor: 'crosshair' }}
      />
      <div style={{ position: 'absolute', top: 8, left: 8, display: 'flex', alignItems: 'center', gap: 6, padding: 6, border: '1px solid var(--border)', borderRadius: 6, background: 'var(--white)', boxShadow: '0 2px 8px rgba(0,0,0,.08)' }}>
        <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', minWidth: 120 }}>{status}</span>
        <button type="button" onClick={commit} disabled={!canCommit} style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 'var(--fs-body)', border: 'none', borderRadius: 5, background: 'var(--gold)', color: 'var(--white)', padding: '5px 8px', cursor: canCommit ? 'pointer' : 'default', opacity: canCommit ? 1 : 0.45 }}>
          <i className="ti ti-check" aria-hidden="true" /> {labels?.done}
        </button>
        <button type="button" onClick={onCancel} style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 'var(--fs-body)', border: '1px solid var(--border)', borderRadius: 5, background: 'var(--white)', color: 'var(--text-main)', padding: '5px 8px', cursor: 'pointer' }}>
          <i className="ti ti-x" aria-hidden="true" /> {labels?.cancel}
        </button>
      </div>
    </div>
  )
}
