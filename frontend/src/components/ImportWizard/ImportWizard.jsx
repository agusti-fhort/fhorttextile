import { useState, useMemo } from 'react'

const API = import.meta.env.VITE_API_URL || ''

const STEPS = [
  { n: 1, label: 'Talles' },
  { n: 2, label: 'POMs' },
  { n: 3, label: 'Mesures' },
  { n: 4, label: 'Teixit' },
  { n: 5, label: 'Guardar' },
]

const norm = (s) => (s || '').trim().toUpperCase()
const GOLD = 'var(--gold, #c79a3a)'
const BORDER = 'var(--color-border-tertiary, #e0d5c5)'

// ───────────────────────────── Stepper header ─────────────────────────────
function Stepper({ step }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, margin: '0 0 20px' }}>
      {STEPS.map((s, i) => {
        const done = s.n < step
        const active = s.n === step
        return (
          <div key={s.n} style={{ display: 'flex', alignItems: 'center', flex: i < STEPS.length - 1 ? 1 : '0 0 auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 600,
                background: active ? GOLD : done ? '#3b6d11' : 'transparent',
                color: active || done ? '#fff' : '#868685',
                border: active || done ? 'none' : `1px solid ${BORDER}`,
              }}>{done ? '✓' : s.n}</div>
              <span style={{
                fontSize: 12, fontWeight: active ? 600 : 400,
                color: active ? '#1d1d1b' : '#868685', whiteSpace: 'nowrap',
              }}>{s.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{ flex: 1, height: 1, background: done ? '#3b6d11' : BORDER, margin: '0 10px' }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ───────────────────────────── Talla chip ─────────────────────────────
function TallaChip({ label, ok, onRemove }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 8px 4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 500,
      background: ok ? '#f0f9f0' : '#fff0f0',
      border: `1px solid ${ok ? '#c0dd97' : '#f0c0c0'}`,
      color: ok ? '#3b6d11' : '#a32d2d',
    }}>
      {ok ? '✓' : '✗'} {label}
      {onRemove && (
        <button onClick={onRemove} title="Treure aquesta talla"
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit',
                   fontSize: 14, lineHeight: 1, padding: 0 }}>×</button>
      )}
    </span>
  )
}

export default function ImportWizard({ model, onCancel, onComplete }) {
  const token = localStorage.getItem('access_token')
  const authHeaders = { Authorization: `Bearer ${token}` }

  const [step, setStep] = useState(1)
  const [sessionToken, setSessionToken] = useState(null)
  const [error, setError] = useState('')

  // Pas 1 — upload + cribratge + reconciliació de talles
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [cribratge, setCribratge] = useState(null)
  const [tallesSel, setTallesSel] = useState([])      // working set de labels (columnes futures)
  const [configurat, setConfigurat] = useState([])    // run configurat del model (pot canviar amb 'alinear')
  const [savingTalles, setSavingTalles] = useState(false)

  // Pas 2 — extracció POMs + matching
  const [extracting, setExtracting] = useState(false)
  const [pomsExtrets, setPomsExtrets] = useState(null)
  const [extraccioMeta, setExtraccioMeta] = useState(null)
  const [savingPoms, setSavingPoms] = useState(false)
  const [cataleg, setCataleg] = useState(null)        // POMMaster catàleg (per afegir manual)
  const [showAddPom, setShowAddPom] = useState(false)

  // Pas 3 — taula de mesures
  const [taula, setTaula] = useState({})              // {pom_master_id: {talla: valor}}
  const [gradingLoading, setGradingLoading] = useState(false)
  const [savingMesures, setSavingMesures] = useState(false)

  // Pas 4 — teixit
  const [teixit, setTeixit] = useState({
    fabric_main: '', fabric_composition: '', shrinkage_type: 'NONE',
    shrinkage_warp: '', shrinkage_weft: '', shrinkage_pct: '', shrinkage_iso_key: '', fabric_notes: '',
  })
  const [isoTable, setIsoTable] = useState([])
  const [biaxial, setBiaxial] = useState(true)
  const [savingTeixit, setSavingTeixit] = useState(false)

  // Pas 5 — guardar
  const [confirming, setConfirming] = useState(false)

  const configuratSet = useMemo(() => new Set((configurat || []).map(norm)), [configurat])
  const teDesti = (label) => configuratSet.has(norm(label))
  const senseDesti = useMemo(() => tallesSel.filter(t => !teDesti(t)), [tallesSel, configuratSet])
  const docLabels = cribratge?.run_talles_document || []
  const configurablesNoSel = useMemo(
    () => (configurat || []).filter(c => !tallesSel.some(t => norm(t) === norm(c))),
    [configurat, tallesSel],
  )

  // ── Upload → cribratge
  const handleUpload = async () => {
    if (!file) return
    setUploading(true); setError('')
    const fd = new FormData()
    fd.append('document', file)
    fd.append('model_id', model.id)
    fd.append('garment_type_item_code', model.garment_type_item_code || '')
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/cribratge/`, {
        method: 'POST', headers: authHeaders, body: fd,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || `Error ${res.status}`); setUploading(false); return }
      setSessionToken(data.token)
      setCribratge(data)
      setTallesSel(data.run_talles_document || [])
      setConfigurat(data.run_configurat || [])
    } catch (e) {
      setError(`Error de connexió: ${String(e)}`)
    }
    setUploading(false)
  }

  const addTalla = (label) => {
    if (!tallesSel.some(t => norm(t) === norm(label))) setTallesSel([...tallesSel, label])
  }
  const removeTalla = (label) => setTallesSel(tallesSel.filter(t => norm(t) !== norm(label)))

  const patchTalles = async (accio) => {
    const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/talles/`, {
      method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify({ talles_seleccionades: tallesSel, accio }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) { setError(data.error || `Error ${res.status}`); return null }
    return data
  }

  const handleAlinear = async () => {
    setSavingTalles(true); setError('')
    const data = await patchTalles('alinear')
    if (data) setConfigurat(data.run_conciliat?.configurat || tallesSel)
    setSavingTalles(false)
  }

  const handleContinue = async () => {
    setSavingTalles(true); setError('')
    const data = await patchTalles('res')
    setSavingTalles(false)
    if (!data) return
    if (data.ready) { setStep(2); runExtraccio() }
    else setError(`Encara hi ha talles sense destí: ${(data.sense_desti || []).join(', ')}`)
  }

  const canContinue = tallesSel.length > 0 && senseDesti.length === 0 && !savingTalles

  // ── Pas 2 — extracció completa (Crida 2)
  const runExtraccio = async () => {
    setExtracting(true); setError('')
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/extraccio/`, {
        method: 'POST', headers: authHeaders,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || `Error ${res.status}`); setExtracting(false); return }
      setPomsExtrets(data.poms_extrets || [])
      setExtraccioMeta({ header: data.header, base_size: data.base_size, sizes: data.sizes,
                         grading_status: data.grading_status, avisos: data.avisos || [] })
    } catch (e) {
      setError(`Error de connexió: ${String(e)}`)
    }
    setExtracting(false)
  }

  const togglePom = (idx) => setPomsExtrets(pomsExtrets.map((p, i) =>
    i === idx ? { ...p, actiu: !p.actiu } : p))

  const loadCataleg = async () => {
    if (cataleg) { setShowAddPom(true); return }
    try {
      const res = await fetch(`${API}/api/v1/poms/`, { headers: authHeaders })
      const data = await res.json().catch(() => ({}))
      setCataleg(data.results || data || [])
      setShowAddPom(true)
    } catch (e) { setError(`Error carregant el catàleg: ${String(e)}`) }
  }

  const addPomManual = (pm) => {
    if (pomsExtrets.some(p => p.pom_master_id === pm.id)) { setShowAddPom(false); return }
    setPomsExtrets([...pomsExtrets, {
      codi_fitxa: '', descripcio: pm.nom_client || '', pom_master_id: pm.id,
      pom_codi: pm.codi_client, pom_nom: pm.nom_client, match_type: 'manual',
      confidence: 'HIGH', values: {}, actiu: true, ordre: pomsExtrets.length,
    }])
    setShowAddPom(false)
  }

  const handleContinuePoms = async () => {
    setSavingPoms(true); setError('')
    const ids = pomsExtrets.filter(p => p.actiu && p.pom_master_id).map(p => p.pom_master_id)
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/poms/`, {
        method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ poms_confirmats: ids }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || `Error ${res.status}`); setSavingPoms(false); return }
      buildTaula()
      setStep(3)
    } catch (e) { setError(`Error de connexió: ${String(e)}`) }
    setSavingPoms(false)
  }

  const pomsActius = (pomsExtrets || []).filter(p => p.actiu).length

  // ── Pas 3 — taula de mesures
  const pomsTaula = (pomsExtrets || []).filter(p => p.actiu)  // files = POMs actius
  const baseSize = (model.base_size_label && tallesSel.includes(model.base_size_label))
    ? model.base_size_label
    : (extraccioMeta?.base_size && tallesSel.includes(extraccioMeta.base_size))
      ? extraccioMeta.base_size : tallesSel[0]

  const buildTaula = () => {
    const t = {}
    for (const p of (pomsExtrets || []).filter(x => x.actiu)) {
      const row = {}
      for (const talla of tallesSel) {
        const v = (p.values || {})[talla]
        row[talla] = (v === undefined || v === null) ? '' : String(v)
      }
      t[p.pom_master_id] = row
    }
    setTaula(t)
  }

  const setCell = (pid, talla, val) =>
    setTaula(prev => ({ ...prev, [pid]: { ...(prev[pid] || {}), [talla]: val } }))

  // Columnes (talles) completament buides → ofereix generar grading.
  const emptyCols = tallesSel.filter(talla =>
    pomsTaula.every(p => !(taula[p.pom_master_id]?.[talla] ?? '').toString().trim()))
  const baseTeValors = pomsTaula.some(p => (taula[p.pom_master_id]?.[baseSize] ?? '').toString().trim())

  const handleGenerarGrading = async () => {
    setGradingLoading(true); setError('')
    const base_values = {}
    for (const p of pomsTaula) {
      const v = taula[p.pom_master_id]?.[baseSize]
      if (v !== undefined && v !== '') base_values[p.pom_master_id] = v
    }
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/grading-preview/`, {
        method: 'POST', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_values }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || `Error ${res.status}`); setGradingLoading(false); return }
      const grading = data.grading || {}
      // Omple NOMÉS les cel·les buides; preserva els valors extrets del document.
      setTaula(prev => {
        const next = { ...prev }
        for (const p of pomsTaula) {
          const g = grading[String(p.pom_master_id)] || {}
          const row = { ...(next[p.pom_master_id] || {}) }
          for (const talla of tallesSel) {
            if (!(row[talla] ?? '').toString().trim() && g[talla] !== undefined)
              row[talla] = String(g[talla])
          }
          next[p.pom_master_id] = row
        }
        return next
      })
    } catch (e) { setError(`Error de connexió: ${String(e)}`) }
    setGradingLoading(false)
  }

  const handleContinueMesures = async () => {
    setSavingMesures(true); setError('')
    const mesures = []
    for (const p of pomsTaula) {
      for (const talla of tallesSel) {
        const v = taula[p.pom_master_id]?.[talla]
        if (v !== undefined && v !== '')
          mesures.push({ pom_master_id: p.pom_master_id, talla_label: talla, valor: parseFloat(v) })
      }
    }
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/mesures/`, {
        method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ mesures }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || `Error ${res.status}`); setSavingMesures(false); return }
      loadIso()
      setStep(4)
    } catch (e) { setError(`Error de connexió: ${String(e)}`) }
    setSavingMesures(false)
  }

  // ── Pas 4 — teixit
  const loadIso = async () => {
    if (isoTable.length) return
    try {
      const res = await fetch(`${API}/api/v1/models/iso-shrinkage/`, { headers: authHeaders })
      const data = await res.json().catch(() => [])
      setIsoTable(Array.isArray(data) ? data : [])
    } catch { /* iso opcional */ }
  }

  const selectIso = (entry) => {
    setTeixit(t => ({ ...t, shrinkage_type: 'ISO', shrinkage_iso_key: entry.id,
                      shrinkage_warp: entry.warp, shrinkage_weft: entry.weft, shrinkage_pct: '' }))
    setBiaxial(true)
  }

  const buildTeixitPayload = () => {
    const p = {
      fabric_main: teixit.fabric_main, fabric_composition: teixit.fabric_composition,
      shrinkage_type: teixit.shrinkage_type, fabric_notes: teixit.fabric_notes,
      shrinkage_iso_key: teixit.shrinkage_type === 'ISO' ? teixit.shrinkage_iso_key : '',
    }
    if (biaxial) {
      p.shrinkage_warp = teixit.shrinkage_warp !== '' ? parseFloat(teixit.shrinkage_warp) : null
      p.shrinkage_weft = teixit.shrinkage_weft !== '' ? parseFloat(teixit.shrinkage_weft) : null
      p.shrinkage_pct = null
    } else {
      p.shrinkage_pct = teixit.shrinkage_pct !== '' ? parseFloat(teixit.shrinkage_pct) : null
      p.shrinkage_warp = null; p.shrinkage_weft = null
    }
    return p
  }

  const handleSaveTeixit = async (skip) => {
    setSavingTeixit(true); setError('')
    try {
      if (!skip) {
        const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/teixit/`, {
          method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
          body: JSON.stringify(buildTeixitPayload()),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) { setError(data.error || `Error ${res.status}`); setSavingTeixit(false); return }
      }
      setStep(5)
    } catch (e) { setError(`Error de connexió: ${String(e)}`) }
    setSavingTeixit(false)
  }

  // ── Pas 5 — confirmar
  const nValors = pomsTaula.reduce((acc, p) =>
    acc + tallesSel.filter(t => (taula[p.pom_master_id]?.[t] ?? '').toString().trim()).length, 0)
  const teixitInformat = !!(teixit.fabric_main || teixit.fabric_composition ||
    teixit.shrinkage_iso_key || teixit.shrinkage_warp || teixit.shrinkage_pct)

  const handleConfirmar = async () => {
    setConfirming(true); setError('')
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/confirmar/`, {
        method: 'POST', headers: authHeaders,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || `Error ${res.status}`); setConfirming(false); return }
      onComplete && onComplete(data.model_id)
    } catch (e) { setError(`Error de connexió: ${String(e)}`) }
    setConfirming(false)
  }

  // ─────────────────────────── Render ───────────────────────────
  return (
    <div style={{ fontFamily: 'IBM Plex Mono, monospace' }}>
      <Stepper step={step} />

      {error && (
        <div style={{ background: '#fff0f0', border: '1px solid #f0c0c0', color: '#a32d2d',
                      borderRadius: 8, padding: '8px 12px', fontSize: 13, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {/* ═══════════════ PAS 1 — TALLES ═══════════════ */}
      {step === 1 && !cribratge && (
        <div>
          <div
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); setFile(e.dataTransfer.files[0]) }}
            onClick={() => document.getElementById('import-wizard-file').click()}
            style={{
              border: `2px dashed ${BORDER}`, borderRadius: 12, padding: '3rem 2rem',
              textAlign: 'center', cursor: 'pointer', marginBottom: 16,
              background: file ? '#f0f9f0' : 'var(--color-background-secondary, #f5f0ea)',
            }}>
            <input id="import-wizard-file" type="file" accept=".pdf,.xlsx,.xls,image/*"
              style={{ display: 'none' }} onChange={e => setFile(e.target.files[0])} />
            <i className="ti ti-upload" style={{ fontSize: 32, color: GOLD }} />
            <div style={{ fontSize: 14, fontWeight: 500, marginTop: 8 }}>
              {file ? file.name : 'Arrossega la fitxa tècnica aquí'}
            </div>
            <div style={{ fontSize: 12, color: '#868685', marginTop: 4 }}>
              PDF, Excel o imatge · Clica per seleccionar
            </div>
          </div>
          {file && (
            <div style={{ textAlign: 'center' }}>
              <button type="button" onClick={handleUpload} disabled={uploading}
                style={{ padding: '10px 24px', borderRadius: 6, border: 'none', fontSize: 14,
                         fontWeight: 600, background: uploading ? '#ccc' : GOLD, color: '#fff',
                         cursor: uploading ? 'not-allowed' : 'pointer' }}>
                {uploading ? '⏳ Analitzant document...' : '⚡ Analitzar talles'}
              </button>
            </div>
          )}
        </div>
      )}

      {step === 1 && cribratge && (
        <div>
          {/* Avís multi-model (gating de cribratge, no bloqueja el pas de talles) */}
          {cribratge.num_models > 1 && (
            <div style={{ background: '#fdf6ee', border: '1px solid #e0c8a0', color: '#c27a2a',
                          borderRadius: 8, padding: '8px 12px', fontSize: 13, marginBottom: 12 }}>
              ⚠ El document conté {cribratge.num_models} models detectats
              ({(cribratge.model_detectat || []).map(m => m.nom).join(', ')}).
              La importació tractarà un sol model.
            </div>
          )}

          {/* Taula en construcció: columnes = talles seleccionades */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: '#868685', marginBottom: 6 }}>
              Columnes de la taula (talles confirmades):
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {tallesSel.length === 0
                ? <span style={{ fontSize: 12, color: '#a32d2d' }}>Cap talla seleccionada</span>
                : tallesSel.map(t => (
                    <TallaChip key={t} label={t} ok={teDesti(t)} onRemove={() => removeTalla(t)} />
                  ))}
            </div>
          </div>

          {/* Dues columnes: document vs configurat */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>
                Talles del document <span style={{ color: '#868685' }}>({cribratge.sistema_talles})</span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {docLabels.map(t => {
                  const sel = tallesSel.some(x => norm(x) === norm(t))
                  return (
                    <span key={t} onClick={() => sel ? removeTalla(t) : addTalla(t)}
                      style={{ cursor: 'pointer', padding: '4px 9px', borderRadius: 6, fontSize: 12,
                               border: `1px solid ${teDesti(t) ? '#c0dd97' : '#f0c0c0'}`,
                               background: !sel ? '#f5f0ea' : teDesti(t) ? '#f0f9f0' : '#fff0f0',
                               color: !sel ? '#aaa' : teDesti(t) ? '#3b6d11' : '#a32d2d',
                               textDecoration: sel ? 'none' : 'line-through' }}>
                      {teDesti(t) ? '✓' : '✗'} {t}
                    </span>
                  )
                })}
              </div>
            </div>
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>
                Talles configurades al model
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {(configurat || []).length === 0
                  ? <span style={{ fontSize: 12, color: '#868685' }}>Cap run configurat</span>
                  : configurat.map(t => (
                      <span key={t} style={{ padding: '4px 9px', borderRadius: 6, fontSize: 12,
                                             border: `1px solid ${BORDER}`, background: '#fff' }}>{t}</span>
                    ))}
              </div>
              {configurablesNoSel.length > 0 && (
                <div style={{ marginTop: 10, fontSize: 11, color: '#868685' }}>
                  Afegir a la taula:
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                    {configurablesNoSel.map(t => (
                      <button key={t} onClick={() => addTalla(t)}
                        style={{ padding: '3px 8px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
                                 border: `1px dashed ${GOLD}`, background: 'transparent', color: GOLD }}>
                        + {t}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Desajust → oferir alinear */}
          {senseDesti.length > 0 && (
            <div style={{ background: '#fff0f0', border: '1px solid #f0c0c0', borderRadius: 8,
                          padding: '10px 12px', marginBottom: 16 }}>
              <div style={{ fontSize: 13, color: '#a32d2d', marginBottom: 8 }}>
                {senseDesti.length} talla(es) del document sense destí al sistema configurat:
                <b> {senseDesti.join(', ')}</b>. Tria una talla per treure-la, o alinea el model
                al run del document.
              </div>
              <button type="button" onClick={handleAlinear} disabled={savingTalles}
                style={{ padding: '6px 14px', borderRadius: 6, fontSize: 13, cursor: 'pointer',
                         border: `1px solid ${GOLD}`, background: 'transparent', color: GOLD }}>
                {savingTalles ? '⏳...' : `⤵ Alinear: adoptar ${tallesSel.join('·')} com a run del model`}
              </button>
            </div>
          )}

          {/* Navegació */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
            <button type="button" onClick={onCancel}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 13 }}>
              ← Cancel·lar
            </button>
            <button type="button" onClick={handleContinue} disabled={!canContinue}
              title={canContinue ? '' : 'Resol el desajust de talles per continuar'}
              style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 14,
                       fontWeight: 500, color: '#fff', background: canContinue ? GOLD : '#ccc',
                       cursor: canContinue ? 'pointer' : 'not-allowed' }}>
              Continuar → POMs
            </button>
          </div>
        </div>
      )}

      {/* ═══════════════ PAS 2 — POMs ═══════════════ */}
      {step === 2 && (
        <div>
          {/* Talles confirmades (Pas 1) sempre visibles */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: '#868685', marginBottom: 6 }}>
              Talles confirmades (columnes de la taula):
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {tallesSel.map(t => (
                <span key={t} style={{ padding: '3px 9px', borderRadius: 6, fontSize: 12,
                                       border: `1px solid #c0dd97`, background: '#f0f9f0', color: '#3b6d11' }}>{t}</span>
              ))}
            </div>
          </div>

          {extracting && (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#868685' }}>
              <div style={{ fontSize: 28, marginBottom: 12 }}>⏳</div>
              <div style={{ fontSize: 14 }}>Extraient POMs del document...</div>
              <div style={{ fontSize: 12, marginTop: 4 }}>Anàlisi de visió (pot trigar uns segons)</div>
            </div>
          )}

          {!extracting && pomsExtrets && (
            <div>
              {/* Avisos d'extracció */}
              {(extraccioMeta?.avisos || []).length > 0 && (
                <div style={{ background: '#fdf6ee', border: '1px solid #e0c8a0', color: '#c27a2a',
                              borderRadius: 8, padding: '8px 12px', fontSize: 12, marginBottom: 12 }}>
                  {extraccioMeta.avisos.map((a, i) => <div key={i}>⚠ {a}</div>)}
                </div>
              )}

              <div style={{ fontSize: 12, color: '#868685', marginBottom: 8 }}>
                {pomsExtrets.length} POMs detectats · {pomsActius} actius
                {extraccioMeta?.base_size && <> · talla base: <b>{extraccioMeta.base_size}</b></>}
              </div>

              <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, overflow: 'hidden', marginBottom: 16 }}>
                {pomsExtrets.map((p, idx) => {
                  const conf = (p.confidence || '').toUpperCase()
                  const low = conf === 'LOW' || conf === 'NO_MATCH'
                  const med = conf === 'MEDIUM'
                  const noMatch = !p.pom_master_id
                  return (
                    <div key={idx} style={{
                      display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
                      borderTop: idx ? `1px solid ${BORDER}` : 'none',
                      background: !p.actiu ? '#f7f7f5' : low ? '#fdf3ee' : '#fff',
                      opacity: p.actiu ? 1 : 0.55,
                    }}>
                      <input type="checkbox" checked={!!p.actiu} onChange={() => togglePom(idx)}
                        disabled={noMatch && !p.actiu} />
                      <div style={{ flex: '0 0 90px', fontWeight: 600, fontSize: 13 }}>
                        {p.codi_fitxa || '—'}
                      </div>
                      <div style={{ fontSize: 16, color: '#868685' }}>→</div>
                      <div style={{ flex: 1, fontSize: 13 }}>
                        {noMatch
                          ? <span style={{ color: '#a32d2d' }}>Sense match — {p.descripcio || 'sense descripció'}</span>
                          : <><b>{p.pom_codi}</b> · {p.pom_nom || p.descripcio}</>}
                      </div>
                      <span style={{
                        fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 10,
                        background: noMatch ? '#fff0f0' : low ? '#fdf6ee' : med ? '#fdf6ee' : '#f0f9f0',
                        color: noMatch ? '#a32d2d' : (low || med) ? '#c27a2a' : '#3b6d11',
                      }}>{noMatch ? 'sense match' : conf.toLowerCase()}</span>
                    </div>
                  )
                })}
              </div>

              {/* Afegir POM manual del catàleg */}
              <div style={{ marginBottom: 16 }}>
                {!showAddPom ? (
                  <button type="button" onClick={loadCataleg}
                    style={{ padding: '6px 12px', borderRadius: 6, fontSize: 13, cursor: 'pointer',
                             border: `1px dashed ${GOLD}`, background: 'transparent', color: GOLD }}>
                    + Afegir POM del catàleg
                  </button>
                ) : (
                  <select onChange={e => { const pm = (cataleg || []).find(c => String(c.id) === e.target.value); if (pm) addPomManual(pm) }}
                    defaultValue=""
                    style={{ padding: '8px', borderRadius: 6, fontSize: 13, border: `1px solid ${BORDER}`,
                             fontFamily: 'inherit', minWidth: 320 }}>
                    <option value="" disabled>Tria un POM del catàleg…</option>
                    {(cataleg || []).map(c => (
                      <option key={c.id} value={c.id}>{c.codi_client} · {c.nom_client}</option>
                    ))}
                  </select>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <button type="button" onClick={() => setStep(1)}
                  style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                           background: 'transparent', cursor: 'pointer', fontSize: 13 }}>
                  ← Enrere
                </button>
                <button type="button" onClick={handleContinuePoms} disabled={pomsActius === 0 || savingPoms}
                  style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 14,
                           fontWeight: 500, color: '#fff',
                           background: pomsActius && !savingPoms ? GOLD : '#ccc',
                           cursor: pomsActius && !savingPoms ? 'pointer' : 'not-allowed' }}>
                  Continuar → Mesures
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══════════════ PAS 3 — MESURES ═══════════════ */}
      {step === 3 && (
        <div>
          <div style={{ fontSize: 12, color: '#868685', marginBottom: 10 }}>
            Taula de mesures · {pomsTaula.length} POMs × {tallesSel.length} talles ·
            talla base: <b>{baseSize}</b>. Edita qualsevol valor; les cel·les buides es poden
            omplir amb el grading automàtic.
          </div>

          {emptyCols.length > 0 && (
            <div style={{ background: '#fdf6ee', border: '1px solid #e0c8a0', color: '#c27a2a',
                          borderRadius: 8, padding: '8px 12px', fontSize: 12, marginBottom: 10,
                          display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
              <span>Talles sense valors al document: <b>{emptyCols.join(', ')}</b>.</span>
              <button type="button" onClick={handleGenerarGrading} disabled={gradingLoading || !baseTeValors}
                title={baseTeValors ? '' : 'Cal valors a la talla base primer'}
                style={{ padding: '6px 12px', borderRadius: 6, fontSize: 13, whiteSpace: 'nowrap',
                         border: `1px solid ${GOLD}`, background: 'transparent', color: GOLD,
                         cursor: baseTeValors && !gradingLoading ? 'pointer' : 'not-allowed' }}>
                {gradingLoading ? '⏳ Generant...' : '⚡ Generar grading'}
              </button>
            </div>
          )}

          <div style={{ overflowX: 'auto', border: `1px solid ${BORDER}`, borderRadius: 8, marginBottom: 16 }}>
            <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12 }}>
              <thead>
                <tr style={{ background: '#f5f0ea' }}>
                  <th style={{ padding: '8px 10px', textAlign: 'left', position: 'sticky', left: 0,
                               background: '#f5f0ea', minWidth: 160 }}>POM</th>
                  {tallesSel.map(talla => (
                    <th key={talla} style={{ padding: '8px 10px', textAlign: 'center', minWidth: 64,
                          background: talla === baseSize ? '#f0e7cf' : '#f5f0ea',
                          color: talla === baseSize ? '#7a5a00' : '#1d1d1b' }}>
                      {talla}{talla === baseSize && <div style={{ fontSize: 9 }}>base</div>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pomsTaula.map(p => (
                  <tr key={p.pom_master_id} style={{ borderTop: `1px solid ${BORDER}` }}>
                    <td style={{ padding: '6px 10px', position: 'sticky', left: 0, background: '#fff' }}>
                      <b>{p.pom_codi || p.codi_fitxa}</b>
                      <div style={{ fontSize: 10, color: '#868685' }}>{p.pom_nom || p.descripcio}</div>
                    </td>
                    {tallesSel.map(talla => (
                      <td key={talla} style={{ padding: '2px', textAlign: 'center',
                            background: talla === baseSize ? '#fbf7ec' : '#fff' }}>
                        <input type="number" step="0.1"
                          value={taula[p.pom_master_id]?.[talla] ?? ''}
                          onChange={e => setCell(p.pom_master_id, talla, e.target.value)}
                          style={{ width: 56, padding: '4px', textAlign: 'center', fontSize: 12,
                                   border: `1px solid ${BORDER}`, borderRadius: 4,
                                   fontFamily: 'inherit' }} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button type="button" onClick={() => setStep(2)}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 13 }}>
              ← Enrere
            </button>
            <button type="button" onClick={handleContinueMesures} disabled={!baseTeValors || savingMesures}
              title={baseTeValors ? '' : 'La talla base necessita almenys un valor'}
              style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 14,
                       fontWeight: 500, color: '#fff',
                       background: baseTeValors && !savingMesures ? GOLD : '#ccc',
                       cursor: baseTeValors && !savingMesures ? 'pointer' : 'not-allowed' }}>
              Continuar → Teixit
            </button>
          </div>
        </div>
      )}

      {/* ═══════════════ PAS 4 — TEIXIT ═══════════════ */}
      {step === 4 && (
        <div>
          <div style={{ fontSize: 12, color: '#868685', marginBottom: 12 }}>
            Teixit i encongiment <b>(opcional)</b> — pots ometre aquest pas.
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
            <div>
              <label style={{ fontSize: 12, color: '#868685', display: 'block', marginBottom: 4 }}>Teixit principal</label>
              <input value={teixit.fabric_main}
                onChange={e => setTeixit(t => ({ ...t, fabric_main: e.target.value }))}
                placeholder="ex: Viscose Chiffon"
                style={{ width: '100%', padding: '7px 10px', fontSize: 13, borderRadius: 6,
                         border: `1px solid ${BORDER}`, boxSizing: 'border-box', fontFamily: 'inherit' }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: '#868685', display: 'block', marginBottom: 4 }}>Composició</label>
              <input value={teixit.fabric_composition}
                onChange={e => setTeixit(t => ({ ...t, fabric_composition: e.target.value }))}
                placeholder="ex: 100% Viscose"
                style={{ width: '100%', padding: '7px 10px', fontSize: 13, borderRadius: 6,
                         border: `1px solid ${BORDER}`, boxSizing: 'border-box', fontFamily: 'inherit' }} />
            </div>
          </div>

          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 12, color: '#868685', display: 'block', marginBottom: 6 }}>
              Encongiment — ISO estàndard (clica per omplir):
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
              {isoTable.map(entry => {
                const active = teixit.shrinkage_type === 'ISO' && teixit.shrinkage_iso_key === entry.id
                return (
                  <button key={entry.id} type="button" onClick={() => selectIso(entry)}
                    style={{ padding: '4px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
                             border: active ? `1.5px solid ${GOLD}` : `0.5px solid ${BORDER}`,
                             background: active ? '#fdf6ee' : 'transparent', color: '#868685' }}>
                    {entry.nom} <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{entry.warp}%/{entry.weft}%</span>
                  </button>
                )
              })}
            </div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <button type="button" onClick={() => setBiaxial(true)}
                style={{ padding: '4px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer', border: 'none',
                         background: biaxial ? GOLD : '#f5f0ea', color: biaxial ? '#fff' : '#868685' }}>Warp / Weft</button>
              <button type="button" onClick={() => setBiaxial(false)}
                style={{ padding: '4px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer', border: 'none',
                         background: !biaxial ? GOLD : '#f5f0ea', color: !biaxial ? '#fff' : '#868685' }}>Single %</button>
            </div>
            {biaxial ? (
              <div style={{ display: 'flex', gap: 12 }}>
                <input type="number" step="0.5" min="0" max="30" value={teixit.shrinkage_warp}
                  onChange={e => setTeixit(t => ({ ...t, shrinkage_warp: e.target.value, shrinkage_type: 'SUPPLIER', shrinkage_iso_key: '' }))}
                  placeholder="Warp %" style={{ width: 90, padding: '7px 10px', fontSize: 13, borderRadius: 6, border: `1px solid ${BORDER}`, fontFamily: 'inherit' }} />
                <input type="number" step="0.5" min="0" max="30" value={teixit.shrinkage_weft}
                  onChange={e => setTeixit(t => ({ ...t, shrinkage_weft: e.target.value, shrinkage_type: 'SUPPLIER', shrinkage_iso_key: '' }))}
                  placeholder="Weft %" style={{ width: 90, padding: '7px 10px', fontSize: 13, borderRadius: 6, border: `1px solid ${BORDER}`, fontFamily: 'inherit' }} />
              </div>
            ) : (
              <input type="number" step="0.5" min="0" max="30" value={teixit.shrinkage_pct}
                onChange={e => setTeixit(t => ({ ...t, shrinkage_pct: e.target.value, shrinkage_type: 'SUPPLIER' }))}
                placeholder="Shrinkage %" style={{ width: 110, padding: '7px 10px', fontSize: 13, borderRadius: 6, border: `1px solid ${BORDER}`, fontFamily: 'inherit' }} />
            )}
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 12, color: '#868685', display: 'block', marginBottom: 4 }}>Notes</label>
            <textarea value={teixit.fabric_notes} rows={2}
              onChange={e => setTeixit(t => ({ ...t, fabric_notes: e.target.value }))}
              style={{ width: '100%', padding: '7px 10px', fontSize: 13, borderRadius: 6, resize: 'vertical',
                       border: `1px solid ${BORDER}`, boxSizing: 'border-box', fontFamily: 'inherit' }} />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button type="button" onClick={() => setStep(3)}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 13 }}>← Enrere</button>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" onClick={() => handleSaveTeixit(true)} disabled={savingTeixit}
                style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                         background: 'transparent', cursor: 'pointer', fontSize: 13 }}>Ometre →</button>
              <button type="button" onClick={() => handleSaveTeixit(false)} disabled={savingTeixit}
                style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 14, fontWeight: 500,
                         color: '#fff', background: GOLD, cursor: 'pointer' }}>Continuar → Guardar</button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════ PAS 5 — GUARDAR ═══════════════ */}
      {step === 5 && (
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Resum de la importació</div>
          <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, overflow: 'hidden', marginBottom: 16 }}>
            {[
              ['Model destí', `${model.codi_intern} · ${model.nom_prenda || ''}`],
              ['Talles', `${tallesSel.length} (${tallesSel.join('·')})`],
              ['POMs', `${pomsActius} confirmats`],
              ['Valors de mesura', `${nValors}`],
              ['Teixit', teixitInformat ? (teixit.fabric_main || 'informat') : 'no informat'],
            ].map(([k, v], i) => (
              <div key={k} style={{ display: 'flex', padding: '8px 12px', fontSize: 13,
                                    borderTop: i ? `1px solid ${BORDER}` : 'none' }}>
                <div style={{ flex: '0 0 160px', color: '#868685' }}>{k}</div>
                <div style={{ flex: 1, fontWeight: 500 }}>{v}</div>
              </div>
            ))}
          </div>

          <div style={{ background: '#f0f9f0', border: '1px solid #c0dd97', color: '#3b6d11',
                        borderRadius: 8, padding: '8px 12px', fontSize: 12, marginBottom: 16 }}>
            Mana el document: es crearan <b>només</b> els {pomsActius} POMs confirmats (sense files
            buides de plantilla), amb grading tancat (v1). El PDF es desa com a document origen.
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button type="button" onClick={() => setStep(4)}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 13 }}>← Enrere</button>
            <button type="button" onClick={handleConfirmar} disabled={confirming}
              style={{ padding: '8px 24px', borderRadius: 6, border: 'none', fontSize: 14, fontWeight: 600,
                       color: '#fff', background: confirming ? '#ccc' : GOLD,
                       cursor: confirming ? 'not-allowed' : 'pointer' }}>
              {confirming ? '⏳ Guardant...' : '✓ Confirmar i guardar'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
