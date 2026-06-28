import { useEffect, useRef, useState } from 'react'
import paper from 'paper'

const PAPER_COL = {
  node: '#185fa5',
  handle: '#c27a2a',
  helper: '#868685',
}

export default function PaperFlatEditor({ flat, pageW, pageH, toPx, onCommit, onCancel, labels }) {
  const canvasRef = useRef(null)
  const scopeRef = useRef(null)
  const sketchLayerRef = useRef(null)
  const uiLayerRef = useRef(null)
  const selectedPathRef = useRef(null)
  const dragRef = useRef(null)
  const labelsRef = useRef(labels)
  const [status, setStatus] = useState(labels?.loading || '')

  useEffect(() => {
    labelsRef.current = labels
  }, [labels])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !flat?.svg) return undefined

    const scope = new paper.PaperScope()
    scope.setup(canvas)
    scopeRef.current = scope
    const sketchLayer = new scope.Layer({ name: 'flat-sketch' })
    const uiLayer = new scope.Layer({ name: 'flat-ui' })
    sketchLayerRef.current = sketchLayer
    uiLayerRef.current = uiLayer

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

    const selectPath = (item) => {
      selectedPathRef.current = item
      refreshHandles()
      setStatus(labelsRef.current?.pathSelected || '')
    }

    sketchLayer.activate()
    const imported = scope.project.importSVG(flat.svg, { insert: true, expandShapes: true })
    const bounds = imported.bounds
    const targetW = Math.max(1, toPx(flat.width || 80))
    const targetH = Math.max(1, toPx(flat.height || 60))
    const scale = Math.min(targetW / bounds.width, targetH / bounds.height)
    if (Number.isFinite(scale) && scale > 0) imported.scale(scale)
    imported.position = new scope.Point(
      toPx(flat.x || 0) + targetW / 2,
      toPx(flat.y || 0) + targetH / 2,
    )

    const firstPath = imported.getItems({ class: scope.Path }).find(path => path.segments?.length)
    if (firstPath) selectPath(firstPath)
    else setStatus(labelsRef.current?.noPath || '')

    const tool = new scope.Tool()
    tool.onMouseDown = (event) => {
      const hit = scope.project.hitTest(event.point, { fill: true, stroke: true, segments: true, tolerance: 8 })
      const hitItem = hit?.item
      if (hitItem?.data?.kind) {
        dragRef.current = hitItem.data
        return
      }
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

    return () => {
      scope.remove()
      scopeRef.current = null
      sketchLayerRef.current = null
      uiLayerRef.current = null
      selectedPathRef.current = null
      dragRef.current = null
    }
  }, [flat, pageW, pageH, toPx])

  const commit = () => {
    const sketchLayer = sketchLayerRef.current
    if (!sketchLayer) return
    const svg = sketchLayer.exportSVG({ asString: true, bounds: 'content' })
    onCommit(svg)
  }

  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 20 }}>
      <canvas
        ref={canvasRef}
        width={pageW}
        height={pageH}
        style={{ position: 'absolute', inset: 0, width: pageW, height: pageH, touchAction: 'none', cursor: 'crosshair' }}
      />
      <div style={{ position: 'absolute', top: 8, left: 8, display: 'flex', alignItems: 'center', gap: 6, padding: 6, border: '1px solid var(--border)', borderRadius: 6, background: 'var(--white)', boxShadow: '0 2px 8px rgba(0,0,0,.08)' }}>
        <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', minWidth: 120 }}>{status}</span>
        <button type="button" onClick={commit} style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 'var(--fs-body)', border: 'none', borderRadius: 5, background: 'var(--gold)', color: 'var(--white)', padding: '5px 8px', cursor: 'pointer' }}>
          <i className="ti ti-check" aria-hidden="true" /> {labels?.done}
        </button>
        <button type="button" onClick={onCancel} style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 'var(--fs-body)', border: '1px solid var(--border)', borderRadius: 5, background: 'var(--white)', color: 'var(--text-main)', padding: '5px 8px', cursor: 'pointer' }}>
          <i className="ti ti-x" aria-hidden="true" /> {labels?.cancel}
        </button>
      </div>
    </div>
  )
}
