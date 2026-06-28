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

const CALLIE_DEFAULT_URL = '/media/CALLIE.svg'

const PAPER_COL = {
  stroke: '#9c7a2f',
  node: '#1f6feb',
  handle: '#d97706',
  helper: '#64748b',
}

function inspectSvgText(svgText) {
  return {
    bytes: new Blob([svgText]).size,
    paths: (svgText.match(/<path\b/gi) || []).length,
    polygons: (svgText.match(/<polygon\b/gi) || []).length,
    images: (svgText.match(/<image\b/gi) || []).length,
    clipPaths: (svgText.match(/<clipPath\b/gi) || []).length,
    styleClasses: (svgText.match(/\.st\d+/gi) || []).length,
  }
}

function countPaperItems(scope) {
  return {
    paths: scope.project.getItems({ class: scope.Path }).length,
    rasters: scope.project.getItems({ class: scope.Raster }).length,
    groups: scope.project.getItems({ class: scope.Group }).length,
  }
}

function checkExportValidity(svgText) {
  const parsed = new DOMParser().parseFromString(svgText, 'image/svg+xml')
  return parsed.documentElement.nodeName === 'svg' && !parsed.querySelector('parsererror')
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
  const refreshHandlesRef = useRef(null)
  const selectPathRef = useRef(null)
  const dragRef = useRef(null)
  const modeRef = useRef('select')
  const [mode, setMode] = useState('select')
  const [paperActive, setPaperActive] = useState(true)
  const [konvaClicks, setKonvaClicks] = useState(0)
  const [lastPoint, setLastPoint] = useState(null)
  const [status, setStatus] = useState(t('poc_paper.status_loading'))
  const [selectedInfo, setSelectedInfo] = useState(t('poc_paper.none_selected'))
  const [exportedSvg, setExportedSvg] = useState('')
  const [callieMetrics, setCallieMetrics] = useState(null)

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
    refreshHandlesRef.current = refreshHandles
    selectPathRef.current = selectPath

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
      refreshHandlesRef.current = null
      selectPathRef.current = null
    }
  }, [t])

  const exportSvg = () => {
    const sketchLayer = sketchLayerRef.current
    if (!sketchLayer) return
    const started = performance.now()
    const svg = sketchLayer.exportSVG({ asString: true, bounds: 'content' })
    const durationMs = Math.round((performance.now() - started) * 10) / 10
    setExportedSvg(svg)
    setCallieMetrics((current) => current ? {
      ...current,
      export: {
        durationMs,
        validSvg: checkExportValidity(svg),
        counts: inspectSvgText(svg),
        changedMarker: current.changedMarker || svg.includes('callie-poc-edited'),
      },
    } : current)
    setStatus(t('poc_paper.status_exported'))
  }

  const importSvgText = (svgText, sourceLabel) => {
    const scope = scopeRef.current
    const sketchLayer = sketchLayerRef.current
    if (!scope || !sketchLayer) return
    const input = inspectSvgText(svgText)
    setStatus(`Important ${sourceLabel}...`)
    const started = performance.now()
    sketchLayer.activate()
    sketchLayer.removeChildren()
    if (selectedPathRef.current) selectedPathRef.current.selected = false
    selectedPathRef.current = null
    const imported = scope.project.importSVG(svgText, { insert: true, expandShapes: true })
    const importDurationMs = Math.round((performance.now() - started) * 10) / 10
    const bounds = imported.bounds
    const maxWidth = scope.view.size.width * 0.9
    const maxHeight = scope.view.size.height * 0.9
    const scale = Math.min(maxWidth / bounds.width, maxHeight / bounds.height)
    if (Number.isFinite(scale) && scale > 0) imported.scale(scale)
    imported.position = scope.view.center

    const paths = imported.getItems({ class: scope.Path })
    const firstEditablePath = paths.find((path) => path.segments?.length > 1)
    if (firstEditablePath) selectPathRef.current?.(firstEditablePath)
    refreshHandlesRef.current?.()
    scope.view.update()
    const paperCounts = countPaperItems(scope)
    setCallieMetrics({
      sourceLabel,
      input,
      import: {
        durationMs: importDurationMs,
        paperCounts,
        selectedPathSegments: firstEditablePath?.segments?.length || 0,
        colorSample: paths.slice(0, 12).map((path) => ({
          fill: path.fillColor?.toCSS?.(true) || null,
          stroke: path.strokeColor?.toCSS?.(true) || null,
        })),
      },
      edit: null,
      export: null,
    })
    setExportedSvg('')
    setStatus(`CALLIE importat en ${importDurationMs} ms · ${paperCounts.paths} paths Paper`)
  }

  const loadCallieFromUrl = async () => {
    try {
      const response = await fetch(CALLIE_DEFAULT_URL)
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
      importSvgText(await response.text(), CALLIE_DEFAULT_URL)
    } catch (error) {
      setStatus(`No s'ha pogut carregar ${CALLIE_DEFAULT_URL}: ${error.message}`)
    }
  }

  const loadCallieFromFile = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    importSvgText(await file.text(), file.name)
    event.target.value = ''
  }

  const moveSelectedNodeProbe = () => {
    const path = selectedPathRef.current
    const scope = scopeRef.current
    if (!path || !scope || !path.segments.length) return
    const started = performance.now()
    const segment = path.segments[0]
    segment.point = segment.point.add(new scope.Point(8, -6))
    path.name = 'callie-poc-edited'
    path.data = { ...path.data, calliePocEdited: true }
    refreshHandlesRef.current?.()
    scope.view.update()
    const durationMs = Math.round((performance.now() - started) * 10) / 10
    setCallieMetrics((current) => current ? {
      ...current,
      edit: {
        durationMs,
        selectedPathSegments: path.segments.length,
        paperCounts: countPaperItems(scope),
      },
    } : current)
    setStatus(`Node mogut en ${durationMs} ms`)
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
          <button type="button" style={buttonStyle()} onClick={loadCallieFromUrl}>
            <i className="ti ti-file-import" aria-hidden="true" /> Carregar CALLIE
          </button>
          <label style={buttonStyle()}>
            <i className="ti ti-upload" aria-hidden="true" /> Triar SVG
            <input
              type="file"
              accept=".svg,image/svg+xml"
              onChange={loadCallieFromFile}
              style={{ position: 'absolute', inlineSize: 1, blockSize: 1, opacity: 0, pointerEvents: 'none' }}
            />
          </label>
          <button type="button" style={buttonStyle()} onClick={moveSelectedNodeProbe}>
            <i className="ti ti-point" aria-hidden="true" /> Moure node prova
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
        {callieMetrics ? (
          <pre
            style={{
              width: '100%',
              maxWidth: 860,
              margin: 0,
              overflow: 'auto',
              border: '1px solid var(--border)',
              borderRadius: 6,
              padding: 10,
              background: 'var(--surface-soft)',
              color: 'var(--text-main)',
              fontFamily: 'IBM Plex Mono, monospace',
              fontSize: 'var(--fs-small)',
              lineHeight: 1.45,
            }}
          >
            {JSON.stringify(callieMetrics, null, 2)}
          </pre>
        ) : null}
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
