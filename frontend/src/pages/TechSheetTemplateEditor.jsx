import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Stage, Layer, Rect, Line, Transformer } from 'react-konva'
import { PDFDocument } from 'pdf-lib'
import useAuthStore from '../store/auth'
import { customers as customersApi, techSheetTemplate as tmplApi } from '../api/endpoints'
// Motor de canvas compartit amb TechSheetEditor (TS-3): reutilitzem els components de
// render i els helpers per no duplicar-los ni fer drift. NOMÉS dupliquem la "glue" del
// contenidor (estat, handlers, layout), que aquí difereix (sense lock/task/model).
import {
  MM_TO_PX, CANVAS_W, CANVAS_H, PDF_W_PT, PDF_H_PT, FONT, COL,
  uid, toMm, ObjectNode, renderPageToDataURL, serializePages, buildHeaderPrimitives,
  SectionTitle, propLabel, propInput,
} from './TechSheetEditor'

// ════════════════════════════════════════════════════════════════════════════
// TechSheetTemplateEditor — editor de PLANTILLA de fitxa per Customer (TS-3).
// Mateix motor que TechSheetEditor, però:
//   · Font de dades: TechSheetTemplate (per customer), no TechSheet (per model).
//   · Sense lock ni task (gated `configure` al backend).
//   · HeaderBlock en mode placeholder ({model.codi}…), customer_nom real.
//   · Sense taula graduada ni fitxers de model (depenen d'un model concret).
// ════════════════════════════════════════════════════════════════════════════

const LAYER_ORDER = { template: 0, data: 1, free: 2 }

export default function TechSheetTemplateEditor() {
  const { id: customerId } = useParams()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [customerData, setCustomerData] = useState(null)
  const [pages, setPages] = useState([{ id: uid(), objects: [] }])
  const [currentPage, setCurrentPage] = useState(0)
  const [selectedId, setSelectedId] = useState(null)
  const [tool, setTool] = useState('select')
  const [saveState, setSaveState] = useState(null)   // null|'saving'|'saved'|'error'
  const [thumbnails, setThumbnails] = useState([])
  const [exporting, setExporting] = useState(false)
  const [notice, setNotice] = useState(null)
  const [editingText, setEditingText] = useState(null)
  const [loading, setLoading] = useState(true)

  const stageRef = useRef(null)
  const trRef = useRef(null)
  const wrapRef = useRef(null)
  const fileRef = useRef(null)
  const saveTimer = useRef(null)
  const skipSave = useRef(true)
  const drawing = useRef(null)
  const [drawTemp, setDrawTemp] = useState(null)

  // ── Mutació de pàgines ─────────────────────────────────────────────────────
  const objectsOf = (pi) => pages[pi]?.objects || []
  const updatePageObjects = useCallback((pi, updater) => {
    setPages(ps => ps.map((p, i) => (i === pi ? { ...p, objects: updater(p.objects || []) } : p)))
  }, [])
  const addObject = useCallback((obj) => {
    updatePageObjects(currentPage, objs => [...objs, obj]); setSelectedId(obj.id)
  }, [currentPage, updatePageObjects])
  const updateObject = useCallback((objId, patch) => {
    updatePageObjects(currentPage, objs => objs.map(o => (o.id === objId ? { ...o, ...patch } : o)))
  }, [currentPage, updatePageObjects])
  const deleteObject = useCallback((objId) => {
    updatePageObjects(currentPage, objs => objs.filter(o => o.id !== objId)); setSelectedId(null)
  }, [currentPage, updatePageObjects])

  const flash = (text) => { setNotice(text); setTimeout(() => setNotice(null), 2500) }

  // ── Càrrega inicial: customer + plantilla ──────────────────────────────────
  useEffect(() => {
    if (!customerId) return
    let cancelled = false
    Promise.all([
      customersApi.get(customerId).then(r => r.data).catch(() => null),
      tmplApi.detail(customerId).then(r => r.data).catch(() => null),
    ]).then(([cust, tmpl]) => {
      if (cancelled) return
      setCustomerData(cust)
      hydrate(tmpl?.template_json)
      setLoading(false)
    })
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId])

  function hydrate(tj) {
    skipSave.current = true
    if (tj && tj.version === 2 && Array.isArray(tj.pages) && tj.pages.length) {
      setPages(tj.pages.map(p => ({ id: p.id || uid(), objects: (p.objects || []).map(o => ({ ...o, id: o.id || uid() })) })))
    } else {
      setPages([{ id: uid(), objects: [] }])
    }
    setCurrentPage(0)
  }

  // ── Autosave debounce 2s (sense lock; desa sempre si pot editar) ───────────
  useEffect(() => {
    if (skipSave.current) { skipSave.current = false; return }
    if (!canEdit) return
    setSaveState('saving')
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      tmplApi.update(customerId, { template_json: { version: 2, pages: serializePages(pages) } })
        .then(() => setSaveState('saved'))
        .catch(() => setSaveState('error'))
    }, 2000)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pages, canEdit])

  // ── Miniatures offscreen (placeholder header) ──────────────────────────────
  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const ctx = { tableData: {}, modelData: { customer_nom: customerData?.nom }, placeholderMode: true }
        const thumbs = []
        for (const p of pages) thumbs.push(await renderPageToDataURL(p, 0.18, ctx))
        setThumbnails(thumbs)
      } catch { /* noop */ }
    }, 300)
    return () => clearTimeout(t)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pages, customerData])

  // ── Transformer (exclou línies, blocs de dades i plantilla) ────────────────
  useEffect(() => {
    const tr = trRef.current, stage = stageRef.current
    if (!tr || !stage) return
    const obj = objectsOf(currentPage).find(o => o.id === selectedId)
    if (selectedId && obj && obj.layer !== 'template' && obj.type !== 'line' && obj.type !== 'data_block') {
      const node = stage.findOne('#' + selectedId)
      tr.nodes(node ? [node] : [])
    } else { tr.nodes([]) }
    tr.getLayer()?.batchDraw()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, currentPage, pages])

  // ── Teclat: esborra l'objecte free seleccionat ─────────────────────────────
  useEffect(() => {
    const onKey = (e) => {
      if (editingText) return
      if (e.key !== 'Delete' && e.key !== 'Backspace') return
      if (!selectedId || !canEdit) return
      const obj = objectsOf(currentPage).find(o => o.id === selectedId)
      if (obj && obj.layer === 'free') { e.preventDefault(); deleteObject(selectedId) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, currentPage, pages, canEdit, editingText])

  // ── Handlers de node ───────────────────────────────────────────────────────
  const handleDragEnd = (obj) => (e) => {
    const node = e.target
    if (obj.type === 'line') {
      const dx = toMm(node.x()), dy = toMm(node.y())
      const pts = (obj.points || []).map((v, i) => (i % 2 === 0 ? v + dx : v + dy))
      node.position({ x: 0, y: 0 }); updateObject(obj.id, { points: pts })
    } else {
      updateObject(obj.id, { x: toMm(node.x()), y: toMm(node.y()) })
    }
  }
  const handleTransformEnd = (obj) => (e) => {
    const node = e.target
    const sx = node.scaleX(), sy = node.scaleY()
    node.scaleX(1); node.scaleY(1)
    const patch = { x: toMm(node.x()), y: toMm(node.y()), width: Math.max(2, toMm(node.width() * sx)) }
    if (obj.type !== 'text') patch.height = Math.max(2, toMm(node.height() * sy))
    updateObject(obj.id, patch)
  }

  // ── Stage: dibuix + text + deselecció ──────────────────────────────────────
  const stagePoint = () => (stageRef.current ? stageRef.current.getPointerPosition() : null)
  const onStageMouseDown = (e) => {
    if (!canEdit) { if (e.target === e.target.getStage()) setSelectedId(null); return }
    const pos = stagePoint(); if (!pos) return
    if (tool === 'select') { if (e.target === e.target.getStage()) setSelectedId(null); return }
    if (tool === 'text') {
      addObject({ id: uid(), type: 'text', layer: 'free', x: toMm(pos.x), y: toMm(pos.y), width: 120, height: 30, text: 'Doble clic per editar', fontSize: 11, fontFamily: FONT, fill: COL.textMain })
      setTool('select'); return
    }
    if (tool === 'rect' || tool === 'line' || tool === 'draw') {
      drawing.current = { type: tool, startX: pos.x, startY: pos.y, points: [pos.x, pos.y] }
      setDrawTemp({ type: tool, x: pos.x, y: pos.y, w: 0, h: 0, points: [pos.x, pos.y] })
    }
  }
  const onStageMouseMove = () => {
    if (!drawing.current) return
    const pos = stagePoint(); if (!pos) return
    const d = drawing.current
    if (d.type === 'rect') setDrawTemp({ type: 'rect', x: Math.min(d.startX, pos.x), y: Math.min(d.startY, pos.y), w: Math.abs(pos.x - d.startX), h: Math.abs(pos.y - d.startY) })
    else if (d.type === 'line') setDrawTemp({ type: 'line', points: [d.startX, d.startY, pos.x, pos.y] })
    else if (d.type === 'draw') { d.points = [...d.points, pos.x, pos.y]; setDrawTemp({ type: 'draw', points: d.points }) }
  }
  const onStageMouseUp = () => {
    const d = drawing.current; if (!d) return
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

  // ── Edició inline de text ──────────────────────────────────────────────────
  const startTextEdit = (obj) => {
    if (!canEdit) return
    setSelectedId(obj.id)
    setEditingText({ id: obj.id, value: obj.text || '', x: obj.x * MM_TO_PX, y: obj.y * MM_TO_PX, w: (obj.width || 120) * MM_TO_PX })
  }
  const commitTextEdit = () => {
    if (!editingText) return
    updateObject(editingText.id, { text: editingText.value }); setEditingText(null)
  }

  // ── Imatge (fitxer local + drop) ───────────────────────────────────────────
  const addImageFromDataURL = (dataURL) => addObject({ id: uid(), type: 'image', layer: 'free', x: 50, y: 50, width: 120, height: 80, src: dataURL })
  const handleFile = (file) => {
    if (!file || !canEdit) return
    const fr = new FileReader(); fr.onload = () => addImageFromDataURL(fr.result); fr.readAsDataURL(file)
  }
  const onDrop = (e) => {
    e.preventDefault(); if (!canEdit) return
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('image/')) handleFile(file)
  }

  // ── Capçalera (placeholder) — màxim 1 per pàgina ───────────────────────────
  const insertHeader = () => {
    if (!canEdit) return
    if (objectsOf(currentPage).some(o => o.type === 'data_block' && o.kind === 'header')) {
      flash('Ja hi ha una capçalera en aquesta pàgina.'); return
    }
    const { totalW, totalH } = buildHeaderPrimitives({ customer_nom: customerData?.nom }, undefined, true)
    addObject({ id: uid(), type: 'data_block', kind: 'header', layer: 'data', x: 10, y: 8, width: totalW / MM_TO_PX, height: totalH / MM_TO_PX })
  }

  // ── Pàgines ────────────────────────────────────────────────────────────────
  const addPage = () => { if (!canEdit) return; setPages(ps => [...ps, { id: uid(), objects: [] }]); setCurrentPage(pages.length) }
  const removePage = (index) => {
    if (!canEdit || pages.length <= 1) return
    if (!window.confirm('Esborrar aquesta pàgina?')) return
    setPages(ps => ps.filter((_, i) => i !== index)); setCurrentPage(ci => Math.min(ci, pages.length - 2)); setSelectedId(null)
  }

  // ── Export PDF ─────────────────────────────────────────────────────────────
  const onExport = async () => {
    setExporting(true)
    try {
      const pdf = await PDFDocument.create()
      const ctx = { tableData: {}, modelData: { customer_nom: customerData?.nom }, placeholderMode: true }
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
      a.href = url; a.download = `plantilla_${customerData?.codi || customerId}.pdf`; a.click()
      URL.revokeObjectURL(url)
    } catch { /* silenci */ }
    finally { setExporting(false) }
  }

  // ── UI ───────────────────────────────────────────────────────────────────
  const saveLabel = saveState === 'saving' ? 'Desant…' : saveState === 'saved' ? 'Desat ✓' : saveState === 'error' ? 'Error desant' : null
  const headerBtn = {
    display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, padding: '5px 10px',
    borderRadius: 6, border: `1px solid ${COL.border}`, background: 'transparent', cursor: 'pointer', color: COL.textMain, fontFamily: FONT,
  }
  const curObjs = objectsOf(currentPage)
  const ordered = [...curObjs].sort((a, b) => (LAYER_ORDER[a.layer] ?? 2) - (LAYER_ORDER[b.layer] ?? 2))
  const selObj = curObjs.find(o => o.id === selectedId) || null
  const TOOLS = [
    { k: 'select', icon: 'ti-pointer' }, { k: 'text', icon: 'ti-typography' },
    { k: 'rect', icon: 'ti-square' }, { k: 'line', icon: 'ti-line' }, { k: 'draw', icon: 'ti-pencil' },
  ]

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', background: '#faf7f2', fontFamily: FONT }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '0.7rem 1.2rem', borderBottom: '1px solid #e3cfa3', background: COL.sidebar, color: COL.textMain }}>
        <button onClick={() => navigate('/clients')} style={headerBtn}>
          <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> Tornar
        </button>
        <button onClick={onExport} disabled={exporting} style={{ ...headerBtn, background: COL.gold, border: 'none', color: '#fff', opacity: exporting ? 0.5 : 1 }}>
          <i className="ti ti-file-download" style={{ fontSize: 14 }} /> {exporting ? 'Exportant…' : 'Exportar PDF'}
        </button>
        <span style={{ fontSize: 14, fontWeight: 600 }}>Plantilla · {customerData?.nom || `#${customerId}`}</span>
        <span style={{ fontSize: 11, color: COL.textMuted }}>Pàgina {currentPage + 1} de {pages.length}</span>
        {saveLabel && <span style={{ fontSize: 11, color: COL.textMuted }}>{saveLabel}</span>}
        {notice && <span style={{ fontSize: 11, color: '#b45309', background: '#fef3c7', padding: '2px 8px', borderRadius: 6 }}>{notice}</span>}
        {canEdit && (
          <div style={{ display: 'flex', gap: 4, marginLeft: 16 }}>
            {TOOLS.map(tl => (
              <button key={tl.k} onClick={() => setTool(tl.k)} style={{ ...headerBtn, padding: '5px 8px', borderColor: tool === tl.k ? COL.gold : COL.border, background: tool === tl.k ? COL.goldPale : 'transparent', color: tool === tl.k ? COL.gold : COL.textMain }}>
                <i className={`ti ${tl.icon}`} style={{ fontSize: 15 }} />
              </button>
            ))}
            <button onClick={() => fileRef.current?.click()} title="Imatge" style={{ ...headerBtn, padding: '5px 8px' }}>
              <i className="ti ti-photo" style={{ fontSize: 15 }} />
            </button>
            <input ref={fileRef} type="file" accept="image/*" hidden onChange={e => { const f = e.target.files[0]; e.target.value = ''; handleFile(f) }} />
          </div>
        )}
        <span style={{ marginLeft: 'auto', fontSize: 10, fontWeight: 500, padding: '2px 8px', borderRadius: 10, background: COL.gold, color: '#fff', whiteSpace: 'nowrap' }}>
          mode plantilla
        </span>
      </header>

      <main style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* Pàgines */}
        <div style={{ width: 96, flexShrink: 0, background: COL.bg, borderRight: `1px solid ${COL.border}`, overflowY: 'auto', padding: '8px 5px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ color: COL.gold, fontSize: 9, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Pàgines</div>
          {canEdit && <button onClick={addPage} style={{ fontSize: 9, padding: '3px 4px', border: `1px solid ${COL.gold}`, borderRadius: 4, background: 'transparent', color: COL.gold, fontFamily: FONT, cursor: 'pointer' }}>+ Pàgina</button>}
          {pages.map((p, i) => (
            <div key={p.id} onClick={() => { setCurrentPage(i); setSelectedId(null) }} style={{ position: 'relative', cursor: 'pointer' }}>
              <div style={{ width: 84, height: 60, borderRadius: 3, overflow: 'hidden', background: '#fff', border: currentPage === i ? `2px solid ${COL.gold}` : `1px solid ${COL.border}` }}>
                {thumbnails[i] && <img src={thumbnails[i]} alt={`Pàg ${i + 1}`} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} />}
              </div>
              <div style={{ fontSize: 9, color: COL.textMuted, textAlign: 'center', marginTop: 1 }}>Pàg. {i + 1}</div>
              {canEdit && pages.length > 1 && (
                <button onClick={(e) => { e.stopPropagation(); removePage(i) }} title="Eliminar pàgina" style={{ position: 'absolute', top: 2, right: 2, background: '#e74c3c', color: '#fff', border: 'none', fontSize: 9, lineHeight: '14px', width: 14, height: 14, padding: 0, borderRadius: 2, cursor: 'pointer' }}>×</button>
              )}
            </div>
          ))}
        </div>

        {/* Stage */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: COL.bg, minWidth: 0, overflow: 'auto', position: 'relative' }}>
          {!canEdit && (
            <div style={{ position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)', zIndex: 5, background: '#fff', border: `1px solid ${COL.border}`, borderRadius: 6, padding: '4px 12px', fontSize: 11, color: COL.textMuted }}>
              <i className="ti ti-eye" style={{ marginRight: 6 }} />Només lectura (cal `configure`)
            </div>
          )}
          <div ref={wrapRef} onDrop={onDrop} onDragOver={e => e.preventDefault()} style={{ position: 'relative', width: CANVAS_W, height: CANVAS_H, boxShadow: '0 4px 24px rgba(0,0,0,0.12)', background: '#fff', cursor: (canEdit && tool !== 'select') ? 'crosshair' : 'default' }}>
            <Stage ref={stageRef} width={CANVAS_W} height={CANVAS_H} onMouseDown={onStageMouseDown} onMouseMove={onStageMouseMove} onMouseUp={onStageMouseUp}>
              <Layer>
                <Rect x={0} y={0} width={CANVAS_W} height={CANVAS_H} fill="#ffffff" listening={false} />
                {ordered.map(o => (
                  <ObjectNode key={o.id} obj={o} src={o.src}
                    tableData={{}} modelData={{ customer_nom: customerData?.nom }} placeholderMode
                    selected={selectedId === o.id}
                    selectable={canEdit && o.layer !== 'template'}
                    draggable={canEdit && tool === 'select' && o.layer !== 'template'}
                    onSelect={() => setSelectedId(o.id)}
                    onDragEnd={handleDragEnd(o)}
                    onTransformEnd={handleTransformEnd(o)}
                    onDblText={() => startTextEdit(o)} />
                ))}
                {drawTemp?.type === 'rect' && <Rect x={drawTemp.x} y={drawTemp.y} width={drawTemp.w} height={drawTemp.h} stroke={COL.gold} strokeWidth={1} dash={[4, 4]} listening={false} />}
                {(drawTemp?.type === 'line' || drawTemp?.type === 'draw') && <Line points={drawTemp.points} stroke={COL.textMain} strokeWidth={1} dash={[4, 4]} listening={false} />}
                <Transformer ref={trRef} rotateEnabled={false} ignoreStroke boundBoxFunc={(oldB, newB) => (newB.width < 10 || newB.height < 10 ? oldB : newB)} />
              </Layer>
            </Stage>
            {editingText && (
              <textarea autoFocus value={editingText.value}
                onChange={e => setEditingText(s => ({ ...s, value: e.target.value }))}
                onBlur={commitTextEdit}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commitTextEdit() } if (e.key === 'Escape') setEditingText(null) }}
                style={{ position: 'absolute', left: editingText.x, top: editingText.y, width: Math.max(80, editingText.w), fontFamily: FONT, fontSize: 11, color: COL.textMain, border: `1px solid ${COL.gold}`, padding: 2, resize: 'none', outline: 'none', background: '#fff', zIndex: 10 }} />
            )}
          </div>
        </div>

        {/* Panell dret */}
        <aside style={{ width: 180, flexShrink: 0, borderLeft: `1px solid ${COL.border}`, background: COL.bg, display: 'flex', flexDirection: 'column', minHeight: 0, fontFamily: FONT }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 10px' }}>
            <SectionTitle>Inserir bloc de dades</SectionTitle>
            <button onClick={insertHeader} disabled={!canEdit} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, padding: '6px 8px', marginBottom: 6, border: 'none', borderRadius: 5, background: COL.gold, color: '#fff', fontFamily: FONT, cursor: !canEdit ? 'default' : 'pointer', opacity: !canEdit ? 0.45 : 1 }}>
              <i className="ti ti-layout-navbar" style={{ fontSize: 13 }} /> Capçalera del model
            </button>
            <p style={{ fontSize: 10, color: COL.textMuted, margin: '0 0 8px' }}>
              La capçalera mostra placeholders (<i>{'{model.codi}'}</i>…) que es resoldran a cada model que usi aquesta plantilla.
            </p>

            {selObj && canEdit && (
              <>
                <SectionTitle>Element · {selObj.type}</SectionTitle>
                {selObj.type === 'text' && (
                  <label style={propLabel}>Mida font
                    <input type="number" min={6} max={48} value={selObj.fontSize || 11} onChange={e => updateObject(selObj.id, { fontSize: Number(e.target.value) || 11 })} style={propInput} />
                  </label>
                )}
                {(selObj.type === 'rect' || selObj.type === 'line') && (
                  <label style={propLabel}>Color traç
                    <input type="color" value={selObj.stroke || '#1d1d1b'} onChange={e => updateObject(selObj.id, { stroke: e.target.value })} style={{ ...propInput, padding: 0, height: 26 }} />
                  </label>
                )}
                {selObj.type === 'rect' && (
                  <label style={propLabel}>Emplenat
                    <input type="color" value={selObj.fill && selObj.fill !== 'transparent' ? selObj.fill : '#ffffff'} onChange={e => updateObject(selObj.id, { fill: e.target.value })} style={{ ...propInput, padding: 0, height: 26 }} />
                  </label>
                )}
                {(selObj.layer === 'free' || selObj.type === 'data_block') && (
                  <button onClick={() => deleteObject(selObj.id)} style={{ width: '100%', fontSize: 11, padding: '5px 8px', marginTop: 6, border: '1px solid #e74c3c', borderRadius: 5, background: 'transparent', color: '#e74c3c', fontFamily: FONT, cursor: 'pointer' }}>
                    <i className="ti ti-trash" style={{ fontSize: 12, marginRight: 5 }} />Eliminar
                  </button>
                )}
              </>
            )}
          </div>
        </aside>
      </main>

      {loading && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(255,255,255,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT, color: COL.textMuted, fontSize: 13 }}>Carregant plantilla…</div>
      )}
    </div>
  )
}
