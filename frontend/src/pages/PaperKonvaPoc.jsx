import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Stage, Layer, Rect, Text, Line } from 'react-konva'
import paper from 'paper'

const MM_TO_PX = 96 / 25.4
const toPx = (mm) => mm * MM_TO_PX
const toMm = (px) => px / MM_TO_PX

const SAMPLE_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 260">
  <path id="sample-sketch" d="M70 160 C135 60 205 70 258 140 C318 222 390 72 488 150" fill="none" stroke="#9c7a2f" stroke-width="4" stroke-linecap="round"/>
  <path d="M432 112 L488 150 L420 166" fill="none" stroke="#9c7a2f" stroke-width="3" stroke-linecap="round"/>
</svg>`

const PAPER_COL = {
  stroke: '#9c7a2f',
  node: '#1f6feb',
  handle: '#d97706',
  helper: '#64748b',
}

function buttonStyle(active = false) {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    border: `1px solid ${active ? 'var(--gold)' : 'var(--border)'}`,
    borderRadius: 6,
    padding: '7px 10px',
    background: active ? 'var(--gold-soft)' : 'var(--surface)',
    color: 'var(--text-main)',
    cursor: 'pointer',
    fontSize: 'var(--fs-small)',
  }
}

export default function PaperKonvaPoc() {
  const { t } = useTranslation()
  const canvasRef = useRef(null)
  const scopeRef = useRef(null)
  const sketchLayerRef = useRef(null)
  const uiLayerRef = useRef(null)
  const selectedPathRef = useRef(null)
  const dragRef = useRef(null)
  const modeRef = useRef('select')
  const [mode, setMode] = useState('select')
  const [paperActive, setPaperActive] = useState(true)
  const [konvaClicks, setKonvaClicks] = useState(0)
  const [lastPoint, setLastPoint] = useState(null)
  const [status, setStatus] = useState(t('poc_paper.status_loading'))
  const [selectedInfo, setSelectedInfo] = useState(t('poc_paper.none_selected'))
  const [exportedSvg, setExportedSvg] = useState('')

  const setEditMode = (nextMode) => {
    modeRef.current = nextMode
    setMode(nextMode)
    setStatus(t(`poc_paper.mode_${nextMode}`))
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return undefined

    const scope = new paper.PaperScope()
    scope.setup(canvas)
    scopeRef.current = scope

    const sketchLayer = new scope.Layer({ name: 'sketch' })
    const uiLayer = new scope.Layer({ name: 'paper-ui' })
    sketchLayerRef.current = sketchLayer
    uiLayerRef.current = uiLayer

    sketchLayer.activate()
    const imported = scope.project.importSVG(SAMPLE_SVG, { insert: true, expandShapes: true })
    imported.position = scope.view.center
    imported.scale(0.92)
    imported.getItems({ class: scope.Path }).forEach((path) => {
      path.strokeColor = PAPER_COL.stroke
      path.strokeWidth = path.strokeWidth || 3
      path.fillColor = null
    })
    selectedPathRef.current = imported.getItem({ class: scope.Path, id: 'sample-sketch' })

    const refreshHandles = () => {
      const selectedPath = selectedPathRef.current
      uiLayer.removeChildren()
      if (!selectedPath) {
        setSelectedInfo(t('poc_paper.none_selected'))
        scope.view.update()
        return
      }
      selectedPath.selected = true
      selectedPath.segments.forEach((segment, index) => {
        const point = segment.point
        const handleInPoint = point.add(segment.handleIn)
        const handleOutPoint = point.add(segment.handleOut)
        const anchor = new scope.Path.Circle({
          center: point,
          radius: 5,
          fillColor: PAPER_COL.node,
          strokeColor: 'white',
          strokeWidth: 1,
        })
        anchor.data = { kind: 'segment', index }
        if (!segment.handleIn.isZero()) {
          new scope.Path.Line({ from: point, to: handleInPoint, strokeColor: PAPER_COL.helper, strokeWidth: 1, dashArray: [4, 4] })
          const handle = new scope.Path.Circle({ center: handleInPoint, radius: 4, fillColor: PAPER_COL.handle })
          handle.data = { kind: 'handleIn', index }
        }
        if (!segment.handleOut.isZero()) {
          new scope.Path.Line({ from: point, to: handleOutPoint, strokeColor: PAPER_COL.helper, strokeWidth: 1, dashArray: [4, 4] })
          const handle = new scope.Path.Circle({ center: handleOutPoint, radius: 4, fillColor: PAPER_COL.handle })
          handle.data = { kind: 'handleOut', index }
        }
      })
      setSelectedInfo(t('poc_paper.path_selected', { n: selectedPath.segments.length }))
      scope.view.update()
    }

    const selectPath = (item) => {
      if (selectedPathRef.current) selectedPathRef.current.selected = false
      selectedPathRef.current = item
      refreshHandles()
    }

    const addPoint = (point) => {
      const path = selectedPathRef.current
      if (!path) return
      const location = path.getNearestLocation(point)
      if (!location) return
      const segment = path.insert(location.index + 1, location.point)
      segment.handleIn = new scope.Point(-16, 0)
      segment.handleOut = new scope.Point(16, 0)
      setStatus(t('poc_paper.status_point_added'))
      refreshHandles()
    }

    const deletePoint = (hitItem) => {
      const path = selectedPathRef.current
      const index = hitItem?.data?.kind === 'segment' ? hitItem.data.index : null
      if (!path || index === null || path.segments.length <= 2) return
      path.segments[index].remove()
      setStatus(t('poc_paper.status_point_deleted'))
      refreshHandles()
    }

    const tool = new scope.Tool()
    tool.onMouseDown = (event) => {
      setLastPoint({ x: event.point.x, y: event.point.y })
      const hit = scope.project.hitTest(event.point, { fill: true, stroke: true, segments: true, tolerance: 8 })
      const hitItem = hit?.item
      if (modeRef.current === 'add') {
        addPoint(event.point)
        return
      }
      if (modeRef.current === 'delete') {
        deletePoint(hitItem)
        return
      }
      if (hitItem?.data?.kind) {
        dragRef.current = hitItem.data
        return
      }
      const path = hitItem?.className === 'Path' && hitItem.layer === sketchLayer ? hitItem : hitItem?.parent?.getItem?.({ class: scope.Path })
      if (path) {
        selectPath(path)
        setStatus(t('poc_paper.status_path_selected'))
      }
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
      setStatus(t('poc_paper.status_path_changed'))
      refreshHandles()
    }
    tool.onMouseUp = () => {
      dragRef.current = null
    }
    tool.activate()

    refreshHandles()
    setStatus(t('poc_paper.status_ready'))

    return () => {
      scope.remove()
      scopeRef.current = null
      sketchLayerRef.current = null
      uiLayerRef.current = null
      selectedPathRef.current = null
    }
  }, [t])

  const exportSvg = () => {
    const sketchLayer = sketchLayerRef.current
    if (!sketchLayer) return
    const svg = sketchLayer.exportSVG({ asString: true, bounds: 'content' })
    setExportedSvg(svg)
    setStatus(t('poc_paper.status_exported'))
  }

  return (
    <main style={{ padding: 24, display: 'grid', gap: 16 }}>
      <header style={{ display: 'grid', gap: 6 }}>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: 'var(--fs-small)' }}>
          {t('poc_paper.kicker')}
        </p>
        <h1 style={{ margin: 0, color: 'var(--text-main)', fontSize: 'var(--fs-title)' }}>
          {t('poc_paper.title')}
        </h1>
        <p style={{ margin: 0, maxWidth: 760, color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
          {t('poc_paper.description')}
        </p>
      </header>

      <section
        style={{
          display: 'grid',
          gap: 10,
          width: 'min(100%, 960px)',
          padding: 12,
          border: '1px solid var(--border)',
          borderRadius: 8,
          background: 'var(--surface)',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <strong style={{ color: 'var(--text-main)', fontSize: 'var(--fs-body)' }}>
            {t('poc_paper.paper_canvas')}
          </strong>
          <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-small)' }}>{status}</span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          <button type="button" style={buttonStyle(paperActive)} onClick={() => setPaperActive(v => !v)}>
            <i className="ti ti-layers-intersect" aria-hidden="true" /> {paperActive ? t('poc_paper.paper_overlay_on') : t('poc_paper.paper_overlay_off')}
          </button>
          <button type="button" style={buttonStyle(mode === 'select')} onClick={() => setEditMode('select')}>
            <i className="ti ti-pointer" aria-hidden="true" /> {t('poc_paper.mode_select')}
          </button>
          <button type="button" style={buttonStyle(mode === 'add')} onClick={() => setEditMode('add')}>
            <i className="ti ti-circle-plus" aria-hidden="true" /> {t('poc_paper.mode_add')}
          </button>
          <button type="button" style={buttonStyle(mode === 'delete')} onClick={() => setEditMode('delete')}>
            <i className="ti ti-circle-minus" aria-hidden="true" /> {t('poc_paper.mode_delete')}
          </button>
          <button type="button" style={buttonStyle()} onClick={exportSvg}>
            <i className="ti ti-file-export" aria-hidden="true" /> {t('poc_paper.export_svg')}
          </button>
        </div>
        <div
          style={{
            position: 'relative',
            width: '100%',
            maxWidth: 860,
            height: 360,
            border: '1px solid var(--border)',
            borderRadius: 6,
            overflow: 'hidden',
            background: 'var(--cream)',
          }}
        >
          <Stage
            width={760}
            height={360}
            onMouseDown={() => setKonvaClicks(c => c + 1)}
            style={{ width: '100%', height: '100%', background: 'var(--cream)' }}
          >
            <Layer>
              <Rect x={toPx(18)} y={toPx(18)} width={toPx(162)} height={toPx(68)} fill="#f7f1df" stroke="#d8c58d" strokeWidth={1} />
              <Line points={[toPx(28), toPx(72), toPx(168), toPx(72)]} stroke="#d8c58d" strokeWidth={1} dash={[6, 6]} />
              <Text x={toPx(24)} y={toPx(24)} text={t('poc_paper.konva_underlay')} fontFamily="IBM Plex Mono" fontSize={13} fill="#3f3a2d" />
              <Text x={toPx(24)} y={toPx(32)} text={t('poc_paper.mm_probe', { px: Math.round(toPx(10) * 10) / 10 })} fontFamily="IBM Plex Mono" fontSize={11} fill="#6b654f" />
            </Layer>
          </Stage>
          <canvas
            ref={canvasRef}
            width={760}
            height={360}
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              pointerEvents: paperActive ? 'auto' : 'none',
              touchAction: 'none',
            }}
          />
        </div>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: 'var(--fs-small)' }}>
          {selectedInfo} · {t('poc_paper.konva_clicks', { n: konvaClicks })}
          {lastPoint ? ` · ${t('poc_paper.last_point', { x: Math.round(toMm(lastPoint.x) * 10) / 10, y: Math.round(toMm(lastPoint.y) * 10) / 10 })}` : ''}
        </p>
        <textarea
          readOnly
          value={exportedSvg}
          placeholder={t('poc_paper.export_placeholder')}
          style={{
            width: '100%',
            maxWidth: 860,
            minHeight: 118,
            resize: 'vertical',
            border: '1px solid var(--border)',
            borderRadius: 6,
            padding: 10,
            background: 'var(--surface-soft)',
            color: 'var(--text-main)',
            fontFamily: 'IBM Plex Mono, monospace',
            fontSize: 'var(--fs-small)',
          }}
        />
      </section>
    </main>
  )
}
