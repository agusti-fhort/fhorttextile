import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

const API = import.meta.env.VITE_API_URL || ''

// Helper: schema pdfme complet = default del plugin + overrides (posició, mida, contingut...).
const mk = (def, over) => ({ ...def, ...over })

// ---- Template base de la fitxa (funció pura) --------------------------------
// Geometria A4 horitzontal (297×210). padding [24,10,24,10]: top 24 (header 18mm + 6 marge),
// bottom 24, laterals 10 de seguretat. staticSchema = capçalera/peu/caixa repetits a cada
// pàgina i NO movibles pel tècnic (readOnly). schemas: [[]] = una pàgina buida per editar.
// NOTA: pdfme no té prop "bold" al text (el negreta requereix registrar una font bold);
// amb la font per defecte s'aproxima amb mida/color. Els tokens de número de pàgina al peu
// dret necessiten el motor d'expressions de pdfme (no activat aquí) → text de crèdit fix.
// Nom del rectangle-guia de la caixa útil (s'elimina del PDF a l'export — només guia d'editor).
const USEFUL_BOX_NAME = 'useful_box_border'

// Miniatures de pàgina (canvas 30%): fons blanc + bandes staticSchema + placeholders de blocs.
// Pura (no Date/random); usa canvas. Retorna array de dataURL, un per pàgina.
function generateThumbnails(template) {
  const pages = template?.schemas || []
  const bp = template?.basePdf
  const W = (bp && bp.width) || 297
  const H = (bp && bp.height) || 210
  const staticS = (bp && Array.isArray(bp.staticSchema)) ? bp.staticSchema : []
  const thumbW = 89
  const scale = thumbW / W
  const thumbH = Math.round(H * scale)
  return pages.map(pageSchemas => {
    const c = document.createElement('canvas')
    c.width = thumbW; c.height = thumbH
    const ctx = c.getContext('2d')
    ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, thumbW, thumbH)
    // Bandes/caixa de la capçalera i peu (només rectangles, sense text).
    staticS.forEach(s => {
      if (s.type !== 'rectangle') return
      const x = (s.position?.x || 0) * scale, y = (s.position?.y || 0) * scale
      const w = (s.width || 0) * scale, h = (s.height || 0) * scale
      if (s.color) { ctx.fillStyle = s.color; ctx.fillRect(x, y, w, h) }
      if (s.borderColor) { ctx.strokeStyle = s.borderColor; ctx.lineWidth = 0.5; ctx.strokeRect(x, y, w, h) }
    })
    // Blocs de contingut → placeholders crema/gold.
    ;(pageSchemas || []).forEach(b => {
      const x = (b.position?.x || 0) * scale, y = (b.position?.y || 0) * scale
      const w = (b.width || 0) * scale, h = (b.height || 0) * scale
      ctx.fillStyle = '#f0dfc0'; ctx.fillRect(x, y, w, h)
      ctx.strokeStyle = '#c27a2a'; ctx.lineWidth = 0.5; ctx.strokeRect(x, y, w, h)
    })
    return c.toDataURL('image/png')
  })
}

// pdfme 6 no té API per navegar a una pàgina → fallback: troba el contenidor scrollable del Designer.
function findScroller(root) {
  const all = root.querySelectorAll('*')
  for (const el of all) {
    if (el.scrollHeight > el.clientHeight + 4) {
      const oy = getComputedStyle(el).overflowY
      if (oy === 'auto' || oy === 'scroll') return el
    }
  }
  return null
}

const joinDot = (...xs) => xs.map(x => (x == null ? '' : String(x)).trim()).filter(Boolean).join(' · ')
const pad2 = (n) => String(n).padStart(2, '0')
const formatDateDDMMYYYY = (d) => `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`

function buildBaseTemplate(meta, defs) {
  const { textDef, rectDef } = defs
  const fileName = `${meta.codiIntern}_fitxa_v${meta.versio}.pdf`
  const today = formatDateDDMMYYYY(new Date()) // data de creació de la pàgina (es congela al template desat)
  const staticSchema = [
    // ── Capçalera · línia 1 (y10 h14) — client / model / temporada ──
    mk(rectDef, { name: 'hdr_band1', position: { x: 10, y: 10 }, width: 277, height: 14, color: '#f0dfc0', borderColor: '#e3cfa3', borderWidth: 0.3, readOnly: true }),
    mk(textDef, { name: 'hdr_client', position: { x: 13, y: 12 }, width: 84, height: 6, content: joinDot(meta.customerNom, meta.codiClient) || '—', fontSize: 8, fontColor: '#1d1d1b', readOnly: true }),
    mk(textDef, { name: 'hdr_model', position: { x: 100, y: 12 }, width: 100, height: 6, content: joinDot(meta.codiIntern, meta.nomPrenda), fontSize: 9, alignment: 'center', fontColor: '#1d1d1b', readOnly: true }),
    mk(textDef, { name: 'hdr_season', position: { x: 240, y: 12 }, width: 45, height: 6, content: joinDot(`${meta.temporada || ''}${meta.any || ''}`, meta.collection), fontSize: 8, alignment: 'right', fontColor: '#1d1d1b', readOnly: true }),
    // ── Capçalera · línia 2 (y20 h10) — tipus / sistema talles / versió ──
    mk(rectDef, { name: 'hdr_band2', position: { x: 10, y: 20 }, width: 277, height: 10, color: '#f5f0e8', borderColor: '#e3cfa3', borderWidth: 0.3, readOnly: true }),
    mk(textDef, { name: 'hdr_type', position: { x: 13, y: 21 }, width: 120, height: 5, content: joinDot(meta.garmentTypeNom, meta.garmentTypeItemNom), fontSize: 7, fontColor: '#868685', readOnly: true }),
    mk(textDef, { name: 'hdr_sizesys', position: { x: 140, y: 21 }, width: 80, height: 5, content: joinDot(meta.sizeSystemCodi, meta.sizeSystemNom), fontSize: 7, alignment: 'center', fontColor: '#868685', readOnly: true }),
    mk(textDef, { name: 'hdr_ver', position: { x: 240, y: 21 }, width: 45, height: 5, content: joinDot(`v${meta.versio}`, meta.responsableNom), fontSize: 7, alignment: 'right', fontColor: '#868685', readOnly: true }),
    // ── Peu (y192 h10) ──
    mk(rectDef, { name: 'ftr_band', position: { x: 10, y: 192 }, width: 277, height: 10, color: '#f0dfc0', borderColor: '#e3cfa3', borderWidth: 0.3, readOnly: true }),
    mk(textDef, { name: 'page_name', position: { x: 13, y: 194 }, width: 60, height: 5, content: '', fontSize: 7, fontColor: '#1d1d1b', readOnly: false }),
    mk(textDef, { name: 'ftr_date', position: { x: 100, y: 194 }, width: 40, height: 5, content: today, fontSize: 7, alignment: 'center', fontColor: '#868685', readOnly: true }),
    mk(textDef, { name: 'ftr_page', position: { x: 190, y: 194 }, width: 18, height: 5, content: '1 de 1', fontSize: 7, alignment: 'center', fontColor: '#1d1d1b', readOnly: true }),
    mk(textDef, { name: 'ftr_file', position: { x: 210, y: 194 }, width: 28, height: 5, content: fileName, fontSize: 6.5, fontColor: '#868685', readOnly: true }),
    mk(textDef, { name: 'ftr_gen', position: { x: 240, y: 194 }, width: 45, height: 5, content: 'Generated by FHORT Textile Tech', fontSize: 6, alignment: 'right', fontColor: '#c27a2a', readOnly: true }),
    // ── Caixa útil — guia d'editor (border gris clar). S'elimina del PDF a l'export. ──
    mk(rectDef, { name: USEFUL_BOX_NAME, position: { x: 10, y: 28 }, width: 277, height: 162, color: '', borderColor: '#cccccc', borderWidth: 0.3, readOnly: true }),
  ]
  // padding: top 28 (18mm header + 10mm marge), bottom 14 (10mm peu + 4mm marge), laterals 10.
  return { basePdf: { width: 297, height: 210, padding: [28, 10, 14, 10], staticSchema }, schemas: [[]] }
}

const hasSavedTemplate = (tj) =>
  tj && typeof tj === 'object' && Array.isArray(tj.schemas) && tj.schemas.length > 0

// ---- Taules graduades (F3) — SVG → PNG → image schema -----------------------
// Geometria de columnes (px de disseny). 'finals' omet la columna nom_ca per estalviar espai.
const TBL = { codiW: 24, nomEnW: 80, nomCaW: 80, sizeW: 18, rowH: 12, headerH: 12 }

const escXml = (s) => String(s ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

// Dimensions px de la taula (compartides entre el render SVG i el càlcul de mida en mm).
function tableDims(data, tableType) {
  const showCa = tableType !== 'finals'
  const leftW = TBL.codiW + TBL.nomEnW + (showCa ? TBL.nomCaW : 0)
  const w = leftW + (data.size_labels?.length || 0) * TBL.sizeW
  const h = TBL.headerH + (data.rows?.length || 0) * TBL.rowH
  return { w, h }
}

// Funció pura: { size_labels, rows } + tableType → SVG string (estil fix decidit).
function generateTableSVG(data, tableType) {
  const showCa = tableType !== 'finals'
  const sizes = data.size_labels || []
  const rows = data.rows || []
  const left = showCa
    ? [{ label: 'POM', w: TBL.codiW, kind: 'codi' }, { label: 'Name (EN)', w: TBL.nomEnW, kind: 'en' }, { label: 'Nom (CA)', w: TBL.nomCaW, kind: 'ca' }]
    : [{ label: 'POM', w: TBL.codiW, kind: 'codi' }, { label: 'Name (EN)', w: TBL.nomEnW, kind: 'en' }]
  const cols = [...left, ...sizes.map(s => ({ label: s, w: TBL.sizeW, kind: 'size', size: s }))]
  const { w: totalW, h: totalH } = tableDims(data, tableType)

  // x acumulat per columna
  let acc = 0
  const colX = cols.map(c => { const x = acc; acc += c.w; return x })

  let body = `<rect x="0" y="0" width="${totalW}" height="${TBL.headerH}" fill="#c27a2a"/>`
  cols.forEach((c, i) => {
    body += `<text x="${colX[i] + c.w / 2}" y="${TBL.headerH / 2 + 2.5}" font-family="sans-serif" font-size="7" fill="#ffffff" text-anchor="middle">${escXml(c.label)}</text>`
  })
  rows.forEach((row, ri) => {
    const y = TBL.headerH + ri * TBL.rowH
    const ty = y + TBL.rowH / 2 + 2.5
    body += `<rect x="0" y="${y}" width="${totalW}" height="${TBL.rowH}" fill="${ri % 2 === 0 ? '#ffffff' : '#f5f0e8'}"/>`
    cols.forEach((c, i) => {
      const x = colX[i]
      if (c.kind === 'codi') {
        body += `<text x="${x + 3}" y="${ty}" font-family="sans-serif" font-size="7" font-weight="bold" fill="#c27a2a">${escXml(row.codi)}</text>`
      } else if (c.kind === 'en') {
        body += `<text x="${x + 3}" y="${ty}" font-family="sans-serif" font-size="7" fill="#111827">${escXml(row.nom_en)}</text>`
      } else if (c.kind === 'ca') {
        body += `<text x="${x + 3}" y="${ty}" font-family="sans-serif" font-size="6.5" font-style="italic" fill="#6b7280">${escXml(row.nom_ca)}</text>`
      } else {
        const v = row.valors ? row.valors[c.size] : undefined
        body += `<text x="${x + c.w / 2}" y="${ty}" font-family="sans-serif" font-size="7" fill="#111827" text-anchor="middle">${escXml(v === undefined || v === null ? '–' : v)}</text>`
      }
    })
  })
  body += `<rect x="0" y="0" width="${totalW}" height="${totalH}" fill="none" stroke="#e0d5c5" stroke-width="1"/>`
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${totalW}" height="${totalH}" viewBox="0 0 ${totalW} ${totalH}">${body}</svg>`
}

// Rasteritza un SVG string a PNG dataURL (mateix patró que P4 del spike), x3 per nitidesa.
function svgToPngDataURL(svgStr) {
  return new Promise((resolve, reject) => {
    const url = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgStr)))
    const img = new Image()
    img.onload = () => {
      const scale = 3
      const w = img.naturalWidth || 1
      const h = img.naturalHeight || 1
      const c = document.createElement('canvas')
      c.width = w * scale; c.height = h * scale
      const ctx = c.getContext('2d')
      ctx.scale(scale, scale)
      ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, w, h)
      ctx.drawImage(img, 0, 0)
      try { resolve(c.toDataURL('image/png')) } catch (e) { reject(e) }
    }
    img.onerror = () => reject(new Error('SVG → Image load failed'))
    img.src = url
  })
}

// Editor de fitxa tècnica — pantalla full-screen, FORA del layout principal (sense sidebar).
// pdfme es carrega amb dynamic import() dins useEffect (lazy: el bundle pesat només entra
// quan aquest component es munta, no afecta la resta de l'app).
export default function TechSheetEditor() {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
  const uploadHeaders = { Authorization: `Bearer ${token}` }

  const [sheet, setSheet] = useState(null)
  const [model, setModel] = useState(null)
  const [lockState, setLockState] = useState('loading') // 'loading' | 'owned' | 'conflict' | 'error'
  const [conflict, setConflict] = useState(null)

  const [fitxers, setFitxers] = useState([])
  const [uploading, setUploading] = useState(false)
  const [sizeFittings, setSizeFittings] = useState([])
  const [addingTable, setAddingTable] = useState(null) // `${sfId}-${tableType}` en curs

  // pdfme Designer
  const canvasRef = useRef(null)
  const designerRef = useRef(null)
  const pdfmeRef = useRef(null)      // { generate, getInputFromTemplate, plugins, defs }
  const saveTimer = useRef(null)
  const ownedRef = useRef(false)     // té el lock? (per evitar PATCH 403 en bucle)
  const assetSeq = useRef(0)         // comptador per noms únics d'asset (sense Date.now/random)
  const [designerState, setDesignerState] = useState('idle') // 'idle'|'loading'|'ready'|'error'
  const [designerErr, setDesignerErr] = useState('')
  const [saveState, setSaveState] = useState(null) // null|'saving'|'saved'|'error'|'readonly'
  const [secsSinceAuto, setSecsSinceAuto] = useState(null) // segons des de l'últim autoguardat (null=mai)
  const [manualSave, setManualSave] = useState(null) // null|'saving'|'saved' (botó Desar explícit)
  const [exporting, setExporting] = useState(false)
  const [addingId, setAddingId] = useState(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [fsHover, setFsHover] = useState(false)
  const [currentPageIndex, setCurrentPageIndex] = useState(0)
  const [pageThumbnails, setPageThumbnails] = useState([]) // array de dataURL, un per pàgina
  const [hoveredPage, setHoveredPage] = useState(null)

  useEffect(() => { ownedRef.current = lockState === 'owned' }, [lockState])

  // Rellotge d'autoguardat (sense Date: comptador incremental). Reset a 0 a cada autoguardat OK.
  useEffect(() => {
    const t = setInterval(() => setSecsSinceAuto(s => (s == null ? s : s + 10)), 10000)
    return () => clearInterval(t)
  }, [])

  // Fullscreen: sincronitza l'estat amb l'API del navegador.
  useEffect(() => {
    const onFsChange = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', onFsChange)
    return () => document.removeEventListener('fullscreenchange', onFsChange)
  }, [])

  const loadFitxers = useCallback(() => {
    return fetch(`${API}/api/v1/model-fitxers/?model=${id}&ordering=-data_pujada`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (d) setFitxers(d.results || d || []) })
      .catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // Autosave amb debounce real de 2s. Només desa si tenim el lock (sinó PATCH → 403).
  const debouncedSave = useCallback((template) => {
    if (!ownedRef.current) { setSaveState('readonly'); return }
    setSaveState('saving')
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(async () => {
      try {
        const r = await fetch(`${API}/api/v1/models/${id}/tech-sheet/update/`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` },
          body: JSON.stringify({ template_json: template }),
        })
        if (r.ok) { setSaveState('saved'); setSecsSinceAuto(0) } else { setSaveState('error') }
      } catch { setSaveState('error') }
    }, 2000)
  }, [id])

  // Desar explícit (sense debounce): PATCH immediat. "Desant…" → "Desat ✓" (2s) → "Desar".
  const onSave = async () => {
    const designer = designerRef.current
    if (!designer || !ownedRef.current || manualSave === 'saving') return
    setManualSave('saving')
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/tech-sheet/update/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        body: JSON.stringify({ template_json: designer.getTemplate() }),
      })
      if (r.ok) {
        setManualSave('saved'); setSaveState('saved'); setSecsSinceAuto(0)
        setTimeout(() => setManualSave(null), 2000)
      } else { setManualSave(null) }
    } catch { setManualSave(null) }
  }

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.()
    else document.exitFullscreen?.()
  }

  // Càrrega de dades (model, estat, lock, assets) — efecte original.
  useEffect(() => {
    if (!id) return
    let cancelled = false

    fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(data => { if (!cancelled && data) setModel(data) })
      .catch(() => {})

    // Size fittings del model (per a la secció "Taules disponibles").
    fetch(`${API}/api/v1/size-fittings/?model=${id}`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (!cancelled && d) setSizeFittings(d.results || d || []) })
      .catch(() => {})

    fetch(`${API}/api/v1/models/${id}/tech-sheet/`, { headers: authHeaders })
      .then(r => r.json())
      .then(data => { if (!cancelled) setSheet(data) })
      .catch(() => {})

    fetch(`${API}/api/v1/models/${id}/tech-sheet/lock/`, { method: 'POST', headers: authHeaders })
      .then(async r => {
        if (cancelled) return
        if (r.ok) { setSheet(await r.json()); setLockState('owned') }
        else if (r.status === 409) { setConflict(await r.json()); setLockState('conflict') }
        else { setLockState('error') }
      })
      .catch(() => { if (!cancelled) setLockState('error') })

    loadFitxers()

    return () => {
      cancelled = true
      fetch(`${API}/api/v1/models/${id}/tech-sheet/unlock/`, {
        method: 'POST', headers: authHeaders, keepalive: true,
      }).catch(() => {})
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // Inicialització del Designer: una sola vegada, quan model + sheet estan llestos.
  const canInit = !!sheet && !!model
  useEffect(() => {
    if (!canInit || designerRef.current || !canvasRef.current) return
    let disposed = false
    setDesignerState('loading')

    ;(async () => {
      try {
        const [uiMod, genMod, schemasMod, commonMod] = await Promise.all([
          import('@pdfme/ui'),
          import('@pdfme/generator'),
          import('@pdfme/schemas'),
          import('@pdfme/common'),
        ])
        if (disposed) return
        const { Designer } = uiMod
        const { generate } = genMod
        const { getInputFromTemplate } = commonMod
        const { text, image, rectangle } = schemasMod
        // Tipografia per defecte (punt de partida de cada bloc nou): fontSize 9, Roboto built-in.
        // pdfme 6 NO té options.defaultSchema → la via real és personalitzar el defaultSchema del
        // plugin text. L'usuari pot canviar font/mida després des del panell dret (natiu).
        const textPlugin = {
          ...text,
          propPanel: {
            ...text.propPanel,
            defaultSchema: { ...text.propPanel.defaultSchema, fontSize: 9, fontName: 'Roboto' },
          },
        }
        const plugins = { Text: textPlugin, Image: image, Rectangle: rectangle }
        const defs = {
          textDef: text.propPanel.defaultSchema,
          rectDef: rectangle.propPanel.defaultSchema,
          imageDef: image.propPanel.defaultSchema,
        }
        pdfmeRef.current = { generate, getInputFromTemplate, plugins, defs }

        const meta = {
          customerNom: model?.customer_nom || '',
          codiClient: model?.codi_client || '',
          codiIntern: model?.codi_intern || `#${id}`,
          nomPrenda: model?.nom_prenda || '',
          temporada: model?.temporada || '',
          any: model?.any || '',
          collection: model?.collection || '',
          garmentTypeNom: model?.garment_type_nom || '',
          garmentTypeItemNom: model?.garment_type_item_nom || '',
          sizeSystemCodi: model?.size_system_codi || '',
          sizeSystemNom: model?.size_system_nom || '',
          versio: sheet?.versio ?? 1,
          responsableNom: model?.responsable_nom || model?.created_by_nom || '',
        }
        const tpl = hasSavedTemplate(sheet?.template_json)
          ? sheet.template_json
          : buildBaseTemplate(meta, defs)

        const designer = new Designer({
          domContainer: canvasRef.current,
          template: tpl,
          plugins,
          // pdfme 6: el theme va sota options.theme (no top-level), sinó és un no-op.
          options: {
            theme: {
              token: {
                colorPrimary: '#c27a2a',
                colorBgContainer: '#ffffff',
                colorBgLayout: '#f5f0e8',
                fontFamily: 'IBM Plex Mono, monospace',
              },
            },
          },
        })
        designer.onChangeTemplate(t => { debouncedSave(t); setPageThumbnails(generateThumbnails(t)) })
        // Sincronitza el highlight de miniatures quan l'usuari canvia de pàgina (scroll/UI pdfme).
        designer.onPageChange?.(({ currentPage }) => setCurrentPageIndex((currentPage || 1) - 1))
        designerRef.current = designer
        setPageThumbnails(generateThumbnails(tpl)) // miniatures inicials
        setDesignerState('ready')
      } catch (e) {
        if (!disposed) { setDesignerErr(String(e?.message || e)); setDesignerState('error') }
      }
    })()

    return () => {
      disposed = true
      if (saveTimer.current) clearTimeout(saveTimer.current)
      try { designerRef.current?.destroy?.() } catch { /* noop */ }
      designerRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canInit])

  // Pujada de fitxer (multipart). Refresca la llista en acabar.
  const handleUpload = async (file) => {
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('fitxer', file)
    fd.append('nom', file.name)
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/upload-fitxer/`, {
        method: 'POST', headers: uploadHeaders, body: fd,
      })
      if (r.ok) await loadFitxers()
    } finally {
      setUploading(false)
    }
  }

  // Aplica una template nova: actualitza el Designer, refresca miniatures i dispara autosave.
  // (updateTemplate programàtic no dispara onChangeTemplate, així que ho fem aquí explícitament.)
  const applyTemplate = (next) => {
    const designer = designerRef.current
    if (!designer) return
    designer.updateTemplate(next)
    setPageThumbnails(generateThumbnails(next))
    debouncedSave(next)
  }

  // Afegeix una imatge (dataURL) com a image schema a la pàgina ACTUAL del Designer. Compartit
  // entre croquis (fitxers) i taules graduades.
  const addImageToCanvas = (dataURL, width, height) => {
    const designer = designerRef.current
    const P = pdfmeRef.current
    if (!designer || !P) return
    const tpl = designer.getTemplate()
    // Nom únic: avança el comptador fins a un nom lliure (evita col·lisió amb assets desats).
    const used = new Set(tpl.schemas.flat().map(s => s.name))
    while (used.has(`asset_${assetSeq.current}`)) assetSeq.current += 1
    const asset = mk(P.defs.imageDef, {
      name: `asset_${assetSeq.current}`, type: 'image',
      position: { x: 15, y: 35 }, width, height, content: dataURL,
    })
    assetSeq.current += 1
    const pages = tpl.schemas.length ? tpl.schemas : [[]]
    const target = Math.min(currentPageIndex, pages.length - 1)
    const next = { ...tpl, schemas: pages.map((pg, i) => (i === target ? [...pg, asset] : pg)) }
    applyTemplate(next)
  }

  // Afegeix una pàgina buida al final i hi navega.
  const addPage = () => {
    const designer = designerRef.current
    if (!designer || !ownedRef.current) return
    const tpl = designer.getTemplate()
    const next = { ...tpl, schemas: [...tpl.schemas, []] }
    applyTemplate(next)
    setCurrentPageIndex(next.schemas.length - 1)
  }

  // Esborra una pàgina (mai l'última). Confirmació.
  const removePage = (index) => {
    const designer = designerRef.current
    if (!designer || !ownedRef.current) return
    const tpl = designer.getTemplate()
    if (tpl.schemas.length <= 1) return
    if (!window.confirm('Esborrar aquesta pàgina?')) return
    const next = { ...tpl, schemas: tpl.schemas.filter((_, i) => i !== index) }
    applyTemplate(next)
    setCurrentPageIndex(ci => Math.min(ci, next.schemas.length - 1))
  }

  // Navega a una pàgina. pdfme 6 no té API de navegació → scroll proporcional al contenidor.
  const navigateToPage = (index) => {
    setCurrentPageIndex(index)
    const cont = canvasRef.current
    const scroller = cont && findScroller(cont)
    if (scroller) {
      const total = designerRef.current?.getTotalPages?.() || pageThumbnails.length || 1
      scroller.scrollTo({ top: (scroller.scrollHeight / total) * index, behavior: 'smooth' })
    }
  }

  // Croquis: afegir un asset (fitxer) com a image schema al llenç.
  const addAssetToCanvas = async (f) => {
    if (!designerRef.current || !pdfmeRef.current) return
    let url = f.url_extern
    if (!url && f.fitxer) url = f.fitxer.startsWith('http') ? f.fitxer : `${API}${f.fitxer}`
    if (!url) return
    setAddingId(f.id)
    try {
      const blob = await fetch(url).then(r => { if (!r.ok) throw new Error('fetch ' + r.status); return r.blob() })
      const dataURL = await new Promise((res, rej) => {
        const fr = new FileReader()
        fr.onload = () => res(fr.result)
        fr.onerror = () => rej(new Error('FileReader error'))
        fr.readAsDataURL(blob)
      })
      addImageToCanvas(dataURL, 80, 60)
    } catch { /* silenci: el croquis no s'afegeix; no trenca l'editor */ }
    finally { setAddingId(null) }
  }

  // Taula graduada / talles finals: GET graded-table → SVG → PNG → image schema al llenç.
  const handleAddTable = async (sfId, tableType) => {
    if (!designerRef.current || !pdfmeRef.current) return
    const key = `${sfId}-${tableType}`
    setAddingTable(key)
    try {
      const r = await fetch(`${API}/api/v1/fitting/${sfId}/graded-table/`, { headers: authHeaders })
      if (!r.ok) return // 404 si no hi ha GradingVersion activa → silenci
      const data = await r.json()
      if (!data.rows || data.rows.length === 0) return
      const png = await svgToPngDataURL(generateTableSVG(data, tableType))
      // px de disseny → mm, mantenint proporció, acotat a l'amplada de la caixa útil.
      const { w: pxW, h: pxH } = tableDims(data, tableType)
      const PX_TO_MM = 0.34
      let wmm = pxW * PX_TO_MM
      let hmm = pxH * PX_TO_MM
      const MAXW = 257
      if (wmm > MAXW) { const k = MAXW / wmm; wmm = MAXW; hmm *= k }
      addImageToCanvas(png, wmm, hmm)
    } catch { /* silenci: la taula no s'afegeix; no trenca l'editor */ }
    finally { setAddingTable(null) }
  }

  // Exportar PDF (WYSIWYG: la mateixa template del Designer).
  const onExport = async () => {
    const designer = designerRef.current
    const P = pdfmeRef.current
    if (!designer || !P) return
    setExporting(true)
    try {
      const live = designer.getTemplate()
      // La caixa útil és només guia d'editor → s'elimina del staticSchema abans de generar el PDF.
      const bp = live.basePdf
      const template = (bp && typeof bp === 'object' && Array.isArray(bp.staticSchema))
        ? { ...live, basePdf: { ...bp, staticSchema: bp.staticSchema.filter(s => s.name !== USEFUL_BOX_NAME) } }
        : live
      const inputs = P.getInputFromTemplate(template)
      const pdf = await P.generate({ template, inputs, plugins: P.plugins })
      const blob = new Blob([pdf.buffer], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${model?.codi_intern || id}_fitxa_v${sheet?.versio ?? 1}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setDesignerErr('Export: ' + String(e?.message || e))
    } finally {
      setExporting(false)
    }
  }

  const READONLY_BADGE = { bg: '#f5f0e8', fg: '#868685', border: '1px solid #e0d5c5' }
  const badge = (() => {
    if (lockState === 'loading') return { text: 'Carregant…', ...READONLY_BADGE }
    if (lockState === 'owned') return { text: 'Editant', bg: '#c27a2a', fg: '#ffffff', border: 'none' }
    if (lockState === 'conflict') return {
      text: `Bloquejada per ${conflict?.locked_by || 'un altre usuari'}`,
      ...READONLY_BADGE,
    }
    return { text: 'Error de bloqueig', ...READONLY_BADGE }
  })()

  // Indicador d'autoguardat (diferenciat del Desar manual). "ara" si <60s, "fa X min" si més.
  const saveLabel = (() => {
    if (saveState === 'saving') return 'Desant…'
    if (saveState === 'error') return 'Error desant'
    if (saveState === 'readonly') return 'Només lectura'
    if (saveState === 'saved') {
      return (secsSinceAuto == null || secsSinceAuto < 60)
        ? 'Autoguardat · ara'
        : `Autoguardat · fa ${Math.floor(secsSinceAuto / 60)} min`
    }
    return null
  })()

  const manualSaveLabel = manualSave === 'saving' ? 'Desant…' : manualSave === 'saved' ? 'Desat ✓' : 'Desar'

  const headerBtn = {
    display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, padding: '5px 10px',
    borderRadius: 6, border: '1px solid #e0d5c5', background: 'transparent',
    cursor: 'pointer', color: '#1d1d1b', fontFamily: 'IBM Plex Mono, monospace',
  }

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg, #faf7f2)', fontFamily: 'IBM Plex Mono, monospace' }}>
      <header style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '0.7rem 1.2rem', borderBottom: '1px solid #e3cfa3', background: '#f0dfc0',
        fontFamily: 'IBM Plex Mono, monospace', color: '#1d1d1b',
      }}>
        <button onClick={() => navigate(`/models/${id}`)} style={headerBtn}>
          <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> Tornar al model
        </button>
        <button onClick={onSave} disabled={designerState !== 'ready' || lockState !== 'owned' || manualSave === 'saving'}
          style={{
            ...headerBtn, borderColor: '#c27a2a', color: '#c27a2a',
            opacity: designerState !== 'ready' || lockState !== 'owned' ? 0.5 : 1,
          }}>
          <i className="ti ti-device-floppy" style={{ fontSize: 14 }} /> {manualSaveLabel}
        </button>
        <button onClick={onExport} disabled={designerState !== 'ready' || exporting}
          style={{
            ...headerBtn, background: '#c27a2a', border: 'none', color: '#ffffff',
            opacity: designerState !== 'ready' || exporting ? 0.5 : 1,
          }}>
          <i className="ti ti-file-download" style={{ fontSize: 14 }} /> {exporting ? 'Exportant…' : 'Exportar PDF'}
        </button>
        <span style={{ fontSize: 14, fontWeight: 600, color: '#1d1d1b' }}>
          {model?.codi_intern || `#${id}`}{model?.nom_prenda ? ` · ${model.nom_prenda}` : ''}
        </span>
        {pageThumbnails.length > 0 && (
          <span style={{ fontSize: 11, color: '#868685', fontFamily: 'IBM Plex Mono, monospace' }}>
            Pàgina {currentPageIndex + 1} de {pageThumbnails.length}
          </span>
        )}
        {sheet?.estat === 'tancat' && (
          <span style={{ fontSize: 11, color: 'var(--text-muted, #999)' }}>
            <i className="ti ti-lock" style={{ fontSize: 11, marginRight: 4 }} />Fitxa tancada
          </span>
        )}
        {saveLabel && (
          <span style={{ fontSize: 11, color: '#868685', fontFamily: 'IBM Plex Mono, monospace' }}>
            {saveLabel}
          </span>
        )}
        <button onClick={toggleFullscreen}
          onMouseEnter={() => setFsHover(true)} onMouseLeave={() => setFsHover(false)}
          title={isFullscreen ? 'Sortir de pantalla completa' : 'Pantalla completa'}
          style={{
            marginLeft: 'auto', background: 'transparent', border: 'none', padding: 0,
            color: fsHover ? '#c27a2a' : '#868685', fontSize: 18, cursor: 'pointer',
            display: 'flex', alignItems: 'center',
          }}>
          <i className={`ti ${isFullscreen ? 'ti-arrows-minimize' : 'ti-arrows-maximize'}`} />
        </button>
        <span style={{
          fontSize: 10, fontWeight: 500, padding: '2px 7px',
          borderRadius: 10, background: badge.bg, color: badge.fg, border: badge.border,
          whiteSpace: 'nowrap', fontFamily: 'IBM Plex Mono, monospace',
        }}>
          {badge.text}
        </span>
      </header>

      <main style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* Panell de miniatures de pàgines — a l'esquerra del Designer. */}
        <div style={{
          width: 110, flexShrink: 0, background: '#f5f0e8', borderRight: '1px solid #e0d5c5',
          overflowY: 'auto', padding: '8px 6px', display: 'flex', flexDirection: 'column', gap: 6,
        }}>
          <div style={{
            color: '#c27a2a', fontSize: 9, fontWeight: 600, textTransform: 'uppercase',
            letterSpacing: '0.05em', marginBottom: 4,
          }}>
            Pàgines
          </div>
          <button onClick={addPage}
            disabled={designerState !== 'ready' || lockState !== 'owned'}
            style={{
              fontSize: 9, padding: '3px 6px', border: '1px solid #c27a2a', borderRadius: 4,
              background: 'transparent', color: '#c27a2a', fontFamily: 'IBM Plex Mono, monospace',
              marginBottom: 4, cursor: (designerState !== 'ready' || lockState !== 'owned') ? 'default' : 'pointer',
              opacity: (designerState !== 'ready' || lockState !== 'owned') ? 0.45 : 1,
            }}>
            + Pàgina
          </button>
          {pageThumbnails.map((src, i) => (
            <div key={i}
              onClick={() => navigateToPage(i)}
              onMouseEnter={() => setHoveredPage(i)} onMouseLeave={() => setHoveredPage(null)}
              style={{ position: 'relative', cursor: 'pointer' }}>
              <div style={{
                width: 98, borderRadius: 3, overflow: 'hidden',
                border: currentPageIndex === i ? '2px solid #c27a2a' : '1px solid #e0d5c5',
              }}>
                <img src={src} alt={`Pàgina ${i + 1}`} style={{ width: '100%', height: 'auto', display: 'block' }} />
              </div>
              <div style={{ fontSize: 9, color: '#868685', textAlign: 'center', marginTop: 2 }}>
                Pàg. {i + 1}
              </div>
              {pageThumbnails.length > 1 && hoveredPage === i && lockState === 'owned' && (
                <button onClick={(e) => { e.stopPropagation(); removePage(i) }}
                  title="Esborrar pàgina"
                  style={{
                    position: 'absolute', top: 2, right: 2, background: '#e74c3c', color: '#ffffff',
                    border: 'none', fontSize: 9, lineHeight: '14px', width: 14, height: 14, padding: 0,
                    borderRadius: 2, cursor: 'pointer',
                  }}>
                  ×
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Cos central — el Designer pdfme es munta a canvasRef. */}
        <div style={{ flex: 1, position: 'relative', minWidth: 0 }}>
          <div ref={canvasRef} style={{ position: 'absolute', inset: 0, '--pdf-ui-non-printable-bg': '#f9f9f9' }} />
          {designerState !== 'ready' && (
            <div style={{
              position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'var(--bg, #faf7f2)', pointerEvents: designerState === 'error' ? 'auto' : 'none',
            }}>
              <div style={{ textAlign: 'center', color: 'var(--text-muted, #999)' }}>
                <i className={`ti ${designerState === 'error' ? 'ti-alert-triangle' : 'ti-file-text'}`} style={{ fontSize: 40, opacity: 0.5 }} />
                <p style={{ marginTop: 12, fontSize: 15 }}>
                  {designerState === 'error' ? `Error carregant l'editor: ${designerErr}` : 'Carregant editor de fitxa…'}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Panell d'assets inline — fitxers del model + pujada + afegir al llenç (croquis). */}
        <aside style={{
          width: 320, flexShrink: 0, borderLeft: '1px solid #e0d5c5',
          background: '#f5f0e8', display: 'flex', flexDirection: 'column', minHeight: 0,
          fontFamily: 'IBM Plex Mono, monospace',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '0.7rem 1rem', borderBottom: '1px solid #e3cfa3',
          }}>
            <span style={{
              fontSize: 11, fontWeight: 600, color: '#c27a2a',
              textTransform: 'uppercase', letterSpacing: '0.05em',
            }}>
              <i className="ti ti-paperclip" style={{ fontSize: 13, marginRight: 6 }} />
              Assets del model
            </span>
            <span style={{ fontSize: 11, color: '#868685' }}>{fitxers.length}</span>
          </div>

          <label style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            margin: '0.8rem 1rem', padding: '8px', fontSize: 12, fontWeight: 500,
            borderRadius: 6, border: '0.5px dashed var(--gold)', color: 'var(--gold)',
            cursor: uploading ? 'default' : 'pointer',
            background: uploading ? 'var(--gray-l)' : 'transparent',
          }}>
            <i className="ti ti-upload" style={{ fontSize: 13 }} />
            {uploading ? 'Pujant…' : 'Pujar fitxer'}
            <input type="file" hidden disabled={uploading}
              onChange={e => { const f = e.target.files[0]; e.target.value = ''; handleUpload(f) }} />
          </label>

          <div style={{ flex: 1, overflowY: 'auto', padding: '0 1rem 1rem' }}>
            {fitxers.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--text-muted, #999)', textAlign: 'center', marginTop: 8 }}>
                Cap fitxer encara.
              </p>
            ) : (
              fitxers.map(f => {
                const hasUrl = !!(f.url_extern || f.fitxer)
                return (
                  <div key={f.id} style={{
                    background: '#fafafa', border: '1px solid #e0d5c5', padding: '6px 8px',
                    marginBottom: 4, fontSize: 11, fontFamily: 'IBM Plex Mono, monospace',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <i className="ti ti-file" style={{ fontSize: 14, color: '#868685', flexShrink: 0 }} />
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontSize: 11, color: '#1d1d1b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={f.nom_fitxer}>
                          {f.nom_fitxer}
                        </div>
                        <div style={{ fontSize: 10, color: '#868685' }}>
                          {f.tipus}{f.versio ? ` · v${f.versio}` : ''}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => addAssetToCanvas(f)}
                      disabled={!hasUrl || designerState !== 'ready' || addingId === f.id}
                      title={hasUrl ? 'Afegir al llenç' : 'Sense URL de fitxer'}
                      style={{
                        marginTop: 4, marginRight: 4, display: 'inline-flex', alignItems: 'center', gap: 4,
                        fontSize: 10, padding: '3px 8px', border: 'none', borderRadius: 5,
                        background: '#c27a2a', color: '#ffffff', fontFamily: 'IBM Plex Mono, monospace',
                        cursor: (!hasUrl || designerState !== 'ready') ? 'default' : 'pointer',
                        opacity: (!hasUrl || designerState !== 'ready') ? 0.45 : 1,
                      }}>
                      <i className="ti ti-photo-plus" style={{ fontSize: 12 }} />
                      {addingId === f.id ? 'Afegint…' : 'Afegir al llenç'}
                    </button>
                  </div>
                )
              })
            )}

            {/* Taules disponibles (F3) — size fittings del model → taula graduada / talles finals. */}
            <section style={{ borderTop: '1px solid #e3cfa3', margin: '12px 0', paddingTop: 12 }}>
              <div style={{
                fontSize: 11, fontWeight: 600, color: '#c27a2a',
                textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8,
              }}>
                <i className="ti ti-table" style={{ fontSize: 13, marginRight: 6 }} />
                Taules disponibles
              </div>
              {sizeFittings.length === 0 ? (
                <p style={{ fontSize: 11, color: '#868685' }}>Cap size fitting.</p>
              ) : (
                sizeFittings.map(sf => {
                  const gradedKey = `${sf.id}-graded`
                  const finalsKey = `${sf.id}-finals`
                  const tableBtn = (busy) => ({
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                    fontSize: 10, padding: '3px 8px', borderRadius: 5, border: 'none',
                    background: '#c27a2a', color: '#ffffff', fontFamily: 'IBM Plex Mono, monospace',
                    marginTop: 4, marginRight: 4,
                    cursor: designerState !== 'ready' ? 'default' : 'pointer',
                    opacity: designerState !== 'ready' || busy ? 0.45 : 1,
                  })
                  return (
                    <div key={sf.id} style={{
                      background: '#fafafa', border: '1px solid #e0d5c5', padding: '6px 8px',
                      marginBottom: 4, fontSize: 11, fontFamily: 'IBM Plex Mono, monospace',
                    }}>
                      <div style={{ fontSize: 11, color: '#1d1d1b' }}>
                        {sf.codi}{sf.tipus ? ` · ${sf.tipus}` : ''}
                      </div>
                      <div style={{ display: 'flex', gap: 4, marginTop: 1 }}>
                        <button onClick={() => handleAddTable(sf.id, 'graded')}
                          disabled={designerState !== 'ready' || addingTable === gradedKey}
                          style={tableBtn(addingTable === gradedKey)}>
                          <i className="ti ti-table" style={{ fontSize: 12 }} />
                          {addingTable === gradedKey ? 'Afegint…' : 'Taula graduada'}
                        </button>
                        <button onClick={() => handleAddTable(sf.id, 'finals')}
                          disabled={designerState !== 'ready' || addingTable === finalsKey}
                          style={tableBtn(addingTable === finalsKey)}>
                          <i className="ti ti-ruler" style={{ fontSize: 12 }} />
                          {addingTable === finalsKey ? 'Afegint…' : 'Talles finals'}
                        </button>
                      </div>
                    </div>
                  )
                })
              )}
            </section>
          </div>
        </aside>
      </main>
    </div>
  )
}
