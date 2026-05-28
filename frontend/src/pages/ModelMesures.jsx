import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

const API = import.meta.env.VITE_API_URL || ''

const thStyle = {
  padding: '8px 12px', textAlign: 'left', fontSize: 12,
  fontWeight: 500, borderBottom: '1px solid var(--color-border-tertiary, #e0d5c5)',
}
const tdStyle = { padding: '6px 12px', verticalAlign: 'middle' }

export default function ModelMesures() {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const [model, setModel] = useState(null)
  const [mode, setMode] = useState('selector') // 'selector' | 'manual' | 'import' | 'resultat'

  // Manual
  const [pomsSuggerits, setPomsSuggerits] = useState([])
  const [measurements, setMeasurements] = useState({}) // { pom_id: value }
  const [selectedPoms, setSelectedPoms] = useState([])

  // Import
  const [importFile, setImportFile] = useState(null)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)

  // Taula final
  const [taulaRows, setTaulaRows] = useState([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!id) return
    Promise.all([
      fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders }).then(r => r.json()),
      fetch(`${API}/api/v1/models/${id}/poms-suggerits/`, { headers: authHeaders }).then(r => r.json()),
    ]).then(([modelData, pomsData]) => {
      setModel(modelData)
      const poms = pomsData.poms || []
      setPomsSuggerits(poms)
      setSelectedPoms(poms.filter(p => p.is_key).map(p => p.pom_id))
    }).catch(() => setError('Error carregant les dades'))
  }, [id])

  useEffect(() => {
    if (!id) return
    fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
      .then(r => r.json())
      .then(d => {
        if (d.rows && d.rows.length > 0) {
          setTaulaRows(d.rows)
          const meas = {}
          d.rows.forEach(r => { meas[r.pom_id] = r.base_value_cm })
          setMeasurements(meas)
          setSelectedPoms(d.rows.map(r => r.pom_id))
          setMode('manual')
        }
      })
      .catch(() => {})
  }, [id])

  const handleSaveMeasurements = async () => {
    const selected = pomsSuggerits.filter(p => selectedPoms.includes(p.pom_id))
    const toSave = selected
      .filter(p => measurements[p.pom_id] != null && measurements[p.pom_id] !== '')
      .map(p => ({ pom_id: p.pom_id, base_value_cm: parseFloat(measurements[p.pom_id]) }))

    if (toSave.length === 0) { setError('Introdueix almenys un valor'); return }

    setSaving(true); setError('')
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/set-measurements/`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ measurements: toSave }),
      })
      const d = await r.json()
      if (!r.ok) { setError(JSON.stringify(d)); return }

      const taula = await fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders }).then(r => r.json())
      setTaulaRows(taula.rows || [])
      setMode('resultat')
    } catch {
      setError('Error de connexió')
    } finally {
      setSaving(false)
    }
  }

  const handleImport = async () => {
    if (!importFile) return
    setImporting(true); setError('')
    try {
      const formData = new FormData()
      formData.append('file', importFile)
      formData.append('wizard_context', JSON.stringify({
        target: model?.target,
        garment_type: model?.garment_type,
        construction: model?.construction,
        size_system: model?.size_system,
        size_run: model?.size_run_model,
        base_size: model?.base_size_label,
      }))
      const r = await fetch(`${API}/api/v1/models/extract-from-file/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      const d = await r.json()
      if (!r.ok) { setError(JSON.stringify(d)); return }
      setImportResult(d)
    } catch {
      setError('Error analitzant el document')
    } finally {
      setImporting(false)
    }
  }

  const handleConfirmImport = async () => {
    setSaving(true); setError('')
    try {
      const r = await fetch(`${API}/api/v1/models/create-from-extraction/`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          extracted: importResult.extracted,
          wizard_context: importResult.wizard_context,
          overrides: { model_id: parseInt(id) },
        }),
      })
      const d = await r.json()
      if (!r.ok) { setError(JSON.stringify(d)); return }
      const taula = await fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders }).then(r => r.json())
      setTaulaRows(taula.rows || [])
      setMode('manual')
      setSaved(true)
    } catch {
      setError('Error creant les mesures')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      {error && (
        <div style={{
          maxWidth: 1000, margin: '1rem auto 0',
          background: '#fee', border: '1px solid #fcc', borderRadius: 8,
          padding: '0.75rem 1rem', fontSize: 13, color: '#c00',
          fontFamily: 'IBM Plex Mono, monospace',
        }}>{error}</div>
      )}

      {mode === 'selector' && (
        <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1rem' }}>
          <ModelSummaryBar model={model} />

          <h2 style={{ fontSize: 18, fontWeight: 500, margin: '1.5rem 0 0.5rem' }}>
            Mesures i grading
          </h2>
          <p style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)', marginBottom: '1.5rem' }}>
            Introdueix les mesures de la talla base. El sistema calcularà el grading per a totes les talles.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div onClick={() => setMode('manual')}
              style={{
                background: 'var(--color-background-primary, #fff)',
                border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                borderRadius: 12, padding: '1.5rem', cursor: 'pointer',
              }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>
                <i className="ti ti-pencil" style={{ color: 'var(--gold)' }} />
              </div>
              <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 6 }}>Introduir manualment</div>
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)' }}>
                El sistema proposa els POMs estàndard per a {model?.garment_type_nom || 'aquest tipus de peça'}.
                Introdueix els valors de la talla base.
              </div>
              {pomsSuggerits.length > 0 && (
                <div style={{ marginTop: 12, fontSize: 12, color: 'var(--gold)' }}>
                  {pomsSuggerits.length} POMs disponibles · {pomsSuggerits.filter(p => p.is_key).length} KEY
                </div>
              )}
            </div>

            <div onClick={() => setMode('import')}
              style={{
                background: 'var(--color-background-primary, #fff)',
                border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                borderRadius: 12, padding: '1.5rem', cursor: 'pointer',
              }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>
                <i className="ti ti-bolt" style={{ color: 'var(--gold)' }} />
              </div>
              <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 6 }}>Importar de fitxa tècnica</div>
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)' }}>
                Puja un PDF o imatge de la fitxa tècnica del client.
                La IA extraurà les mesures, talles i grading automàticament.
              </div>
            </div>
          </div>
        </div>
      )}

      {mode === 'manual' && (
        <div style={{ maxWidth: 1000, margin: '0 auto', padding: '2rem 1rem' }}>
          <ModelSummaryBar model={model} />

          <POMSelector
            poms={pomsSuggerits}
            selected={selectedPoms}
            onToggle={(pomId) => setSelectedPoms(prev =>
              prev.includes(pomId) ? prev.filter(x => x !== pomId) : [...prev, pomId]
            )}
          />

          <MeasurementsTable
            poms={pomsSuggerits.filter(p => selectedPoms.includes(p.pom_id))}
            measurements={measurements}
            baseSize={model?.base_size_label}
            sizeRun={model?.size_run_model ? model.size_run_model.split('·') : []}
            taulaRows={taulaRows}
            onChange={(pomId, value) => setMeasurements(prev => ({ ...prev, [pomId]: value }))}
          />

          {saved && (
            <div style={{
              marginTop: 16, padding: '8px 14px', borderRadius: 8,
              background: '#EBF8EC', border: '1px solid #A9DFBF',
              fontSize: 13, color: '#1E8449', fontFamily: 'IBM Plex Mono, monospace',
            }}>
              ✓ Mesures guardades.
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 24 }}>
            <button type="button" onClick={() => setMode('selector')}
              style={{ padding: '8px 16px', border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                       borderRadius: 6, background: 'transparent', cursor: 'pointer', fontSize: 13 }}>
              ← Enrere
            </button>
            <button type="button" onClick={handleSaveMeasurements} disabled={saving}
              style={{
                padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 14, fontWeight: 500,
                background: saving ? '#ccc' : 'var(--gold)', color: '#fff',
                cursor: saving ? 'not-allowed' : 'pointer',
              }}>
              {saving ? 'Guardant...' : 'Guardar mesures →'}
            </button>
          </div>
        </div>
      )}

      {mode === 'import' && (
        <div style={{ maxWidth: 1000, margin: '0 auto', padding: '2rem 1rem' }}>
          <ModelSummaryBar model={model} />

          <div
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); setImportFile(e.dataTransfer.files[0]) }}
            onClick={() => document.getElementById('file-input-mesures').click()}
            style={{
              border: '2px dashed var(--color-border-tertiary, #e0d5c5)', borderRadius: 12,
              padding: '3rem 2rem', textAlign: 'center', cursor: 'pointer', marginBottom: 16,
              background: importFile ? '#f0f9f0' : 'var(--color-background-secondary, #f5f0ea)',
            }}>
            <input id="file-input-mesures" type="file" accept=".pdf,image/*"
              style={{ display: 'none' }}
              onChange={e => setImportFile(e.target.files[0])} />
            <i className="ti ti-upload" style={{ fontSize: 32, color: 'var(--gold)', marginBottom: 8 }} />
            <div style={{ fontSize: 14, fontWeight: 500 }}>
              {importFile ? importFile.name : 'Arrossega la fitxa tècnica aquí'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)', marginTop: 4 }}>
              PDF o imatge · Clica per seleccionar
            </div>
          </div>

          {importFile && !importResult && (
            <div style={{ textAlign: 'center' }}>
              <button type="button" onClick={handleImport} disabled={importing}
                style={{
                  padding: '10px 24px', borderRadius: 6, border: 'none', fontSize: 14, fontWeight: 600,
                  background: importing ? '#ccc' : 'var(--gold)', color: '#fff',
                  cursor: importing ? 'not-allowed' : 'pointer',
                }}>
                {importing
                  ? <><ImportSpinner /> Analitzant...</>
                  : '⚡ Analitzar amb IA'}
              </button>
            </div>
          )}

          {importResult && (
            <ImportPreview
              result={importResult}
              model={model}
              onConfirm={handleConfirmImport}
              onReject={() => { setImportResult(null); setImportFile(null) }}
            />
          )}

          <div style={{ marginTop: 16 }}>
            <button type="button" onClick={() => setMode('selector')}
              style={{ padding: '6px 14px', border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                       borderRadius: 6, background: 'transparent', cursor: 'pointer', fontSize: 13 }}>
              ← Enrere
            </button>
          </div>
        </div>
      )}

      {mode === 'resultat' && (
        <div style={{ width: '100%', padding: '1rem' }}>
          <ModelSummaryBar model={model} />

          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ fontSize: 16, fontWeight: 500, margin: 0 }}>
              Taula de mesures i grading
            </h2>
            <button type="button" onClick={() => setMode('manual')}
              style={{ padding: '6px 14px', border: '0.5px solid var(--color-border-tertiary)',
                       borderRadius: 6, background: 'transparent', cursor: 'pointer', fontSize: 13 }}>
              ✏ Editar mesures
            </button>
          </div>

          <TaulaResultat rows={taulaRows}
                         sizeRun={model?.size_run_model?.split('·') || []}
                         baseSize={model?.base_size_label} />
        </div>
      )}
    </>
  )
}

const thResult = { padding: '8px 12px', textAlign: 'left', fontSize: 12, fontWeight: 500 }
const tdResult = { padding: '6px 12px', verticalAlign: 'middle', fontSize: 13 }

function TaulaResultat({ rows, sizeRun, baseSize }) {
  if (!rows || rows.length === 0) {
    return <p style={{ color: 'var(--color-text-secondary)', fontSize: 13 }}>
      Cap mesura guardada.
    </p>
  }

  return (
    <div style={{ overflowX: 'auto', width: '100%' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: 'var(--color-background-secondary)',
                       borderBottom: '1px solid var(--color-border-tertiary)' }}>
            <th style={thResult}>Codi POM</th>
            <th style={thResult}>Nomenclatura</th>
            <th style={thResult}>Descripció</th>
            {sizeRun.map(s => (
              <th key={s} style={{
                ...thResult, textAlign: 'right', fontFamily: 'monospace',
                background: s.trim() === baseSize ? '#fdf6ee' : undefined,
                color: s.trim() === baseSize ? '#7a4a10' : undefined,
              }}>
                {s.trim()} {s.trim() === baseSize ? '★' : ''}
              </th>
            ))}
            <th style={{ ...thResult, textAlign: 'right', color: 'var(--color-text-secondary)' }}>
              Δ S→L
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => {
            const sizes = sizeRun.map(s => s.trim())
            const firstVal = row.graded?.[sizes[0]]
            const lastVal = row.graded?.[sizes[sizes.length - 1]]
            const delta = (firstVal != null && lastVal != null)
              ? (lastVal - firstVal).toFixed(1)
              : '—'

            return (
              <tr key={row.pom_id}
                style={{ borderBottom: '0.5px solid var(--color-border-tertiary)' }}>
                <td style={{ ...tdResult, fontFamily: 'monospace',
                             fontSize: 12, color: 'var(--color-text-secondary)' }}>
                  {row.pom_code}
                </td>
                <td style={{ ...tdResult, fontFamily: 'monospace', color: 'var(--gold)' }}>
                  <NomFitxaEdit pomId={row.pom_id} value={row.nom_fitxa} />
                </td>
                <td style={tdResult}>{row.nom_ca || row.nom_en}</td>
                {sizeRun.map(s => {
                  const sl = s.trim()
                  const val = sl === baseSize
                    ? row.base_value_cm
                    : row.graded?.[sl]
                  return (
                    <td key={sl} style={{
                      ...tdResult, textAlign: 'right', fontFamily: 'monospace',
                      background: sl === baseSize ? '#fefaf5' : undefined,
                      fontWeight: sl === baseSize ? 500 : 400,
                    }}>
                      {val != null ? Number(val).toFixed(1) : '—'}
                    </td>
                  )
                })}
                <td style={{ ...tdResult, textAlign: 'right', fontFamily: 'monospace',
                             color: 'var(--color-text-secondary)' }}>
                  {delta}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function NomFitxaEdit({ pomId, value }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value || '')
  const token = localStorage.getItem('access_token')

  const handleSave = async () => {
    await fetch(`${API}/api/v1/base-measurements/?pom=${pomId}&page_size=1`, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.json()).then(async d => {
      const bm = d.results?.[0] || d[0]
      if (bm) {
        await fetch(`${API}/api/v1/base-measurements/${bm.id}/`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ nom_fitxa: val }),
        })
      }
    })
    setEditing(false)
  }

  if (editing) {
    return (
      <input
        autoFocus
        value={val}
        onChange={e => setVal(e.target.value)}
        onBlur={handleSave}
        onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setEditing(false) }}
        style={{
          width: 60, padding: '2px 6px', border: '1px solid var(--gold)',
          borderRadius: 4, fontSize: 12, fontFamily: 'monospace', background: '#fdf6ee',
        }}
      />
    )
  }

  return (
    <span onClick={() => setEditing(true)}
      style={{ cursor: 'pointer', padding: '2px 4px', borderRadius: 4,
               minWidth: 40, display: 'inline-block',
               color: val ? 'var(--gold)' : 'var(--color-text-secondary)',
               borderBottom: '1px dashed var(--color-border-tertiary)' }}
      title="Clic per editar nomenclatura">
      {val || '—'}
    </span>
  )
}

function ModelSummaryBar({ model }) {
  if (!model) return null
  return (
    <div style={{
      display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap',
      background: 'var(--color-background-secondary, #f5f0ea)',
      border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
      borderRadius: 8, padding: '10px 16px', marginBottom: 16, fontSize: 13,
      fontFamily: 'IBM Plex Mono, monospace',
    }}>
      <span><strong>{model.codi_intern}</strong></span>
      {model.nom_prenda && <span>{model.nom_prenda}</span>}
      {model.target && <span style={{ color: 'var(--color-text-secondary, #868685)' }}>{model.target}</span>}
      {model.construction && <span style={{ color: 'var(--color-text-secondary, #868685)' }}>{model.construction}</span>}
      {model.base_size_label && (
        <span style={{ color: 'var(--gold)' }}>Base: {model.base_size_label}</span>
      )}
      {model.size_run_model && (
        <span style={{ color: 'var(--color-text-secondary, #868685)', fontFamily: 'monospace' }}>
          {model.size_run_model}
        </span>
      )}
    </div>
  )
}

function POMSelector({ poms, selected, onToggle }) {
  const keyPoms = poms.filter(p => p.is_key)
  const otherPoms = poms.filter(p => !p.is_key)

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)', marginBottom: 8 }}>
        PUNTS DE MESURA — selecciona els que vols incloure
      </div>
      {keyPoms.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <span style={{ fontSize: 11, color: 'var(--gold)', marginRight: 8 }}>KEY</span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
            {keyPoms.map(p => (
              <POMChip key={p.pom_id} pom={p} active={selected.includes(p.pom_id)} onToggle={onToggle} />
            ))}
          </div>
        </div>
      )}
      {otherPoms.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {otherPoms.map(p => (
            <POMChip key={p.pom_id} pom={p} active={selected.includes(p.pom_id)} onToggle={onToggle} />
          ))}
        </div>
      )}
    </div>
  )
}

function POMChip({ pom, active, onToggle }) {
  return (
    <button type="button" onClick={() => onToggle(pom.pom_id)}
      style={{
        padding: '4px 10px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
        border: active ? '1.5px solid var(--gold)' : '0.5px solid var(--color-border-tertiary, #e0d5c5)',
        background: active ? '#fdf6ee' : 'transparent',
        color: active ? '#7a4a10' : 'var(--color-text-secondary, #868685)',
        fontFamily: 'IBM Plex Mono, monospace',
      }}>
      <span style={{ fontFamily: 'monospace', marginRight: 4 }}>{pom.pom_code}</span>
      {pom.nom_ca || pom.nom_en}
    </button>
  )
}

function MeasurementsTable({ poms, measurements, baseSize, sizeRun, taulaRows, onChange }) {
  const gradedByPom = {}
  taulaRows.forEach(r => { gradedByPom[r.pom_id] = r.graded || {} })

  return (
    <div style={{ overflowX: 'auto', marginTop: 16 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: 'var(--color-background-secondary, #f5f0ea)' }}>
            <th style={thStyle}>Codi</th>
            <th style={thStyle}>Descripció</th>
            <th style={{ ...thStyle, background: '#fdf6ee', color: '#7a4a10' }}>
              {baseSize} ★ (base)
            </th>
            {sizeRun.filter(s => s !== baseSize).map(s => (
              <th key={s} style={thStyle}>{s}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {poms.map(p => (
            <tr key={p.pom_id} style={{ borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)' }}>
              <td style={{ ...tdStyle, fontFamily: 'monospace', color: 'var(--gold)' }}>
                {p.pom_code}
              </td>
              <td style={tdStyle}>{p.nom_ca || p.nom_en}</td>
              <td style={{ ...tdStyle, background: '#fefaf5' }}>
                <input
                  type="number" step="0.5" min="0"
                  value={measurements[p.pom_id] ?? ''}
                  onChange={e => onChange(p.pom_id, e.target.value)}
                  style={{
                    width: 70, padding: '4px 6px',
                    border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                    borderRadius: 4, fontSize: 13, textAlign: 'right', fontFamily: 'monospace',
                  }}
                  placeholder="—"
                />
              </td>
              {sizeRun.filter(s => s !== baseSize).map(s => (
                <td key={s} style={{
                  ...tdStyle, textAlign: 'right', fontFamily: 'monospace',
                  color: 'var(--color-text-secondary, #868685)',
                }}>
                  {gradedByPom[p.pom_id]?.[s] != null
                    ? gradedByPom[p.pom_id][s].toFixed(1)
                    : '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ImportSpinner() {
  return (
    <>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      <span style={{
        display: 'inline-block', width: 14, height: 14,
        border: '2px solid rgba(255,255,255,0.3)',
        borderTopColor: '#fff', borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
        verticalAlign: 'middle', marginRight: 6,
      }} />
    </>
  )
}

function ImportPreview({ result, model, onConfirm, onReject }) {
  const ext = result?.extracted || {}
  const poms = ext.poms || []
  const sizeRunRaw = ext.size_run?.value ?? ext.size_run ?? ''
  const sizeRun = (typeof sizeRunRaw === 'string' ? sizeRunRaw : '').split('·').map(s => s.trim()).filter(Boolean)
  const baseSize = (ext.base_size?.value ?? ext.base_size ?? model?.base_size_label) || ''
  const gradingTable = ext.grading_table || []
  const gradedByCode = {}
  gradingTable.forEach(g => { gradedByCode[g.code] = g.values_by_size || {} })

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{
        background: 'var(--color-background-secondary, #f5f0ea)',
        border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
        borderRadius: 8, padding: '12px 16px', marginBottom: 16,
      }}>
        <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8 }}>Dades extretes</div>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', fontSize: 12, color: 'var(--color-text-secondary, #868685)' }}>
          {ext.brand?.value && <span>Marca: <strong>{ext.brand.value}</strong></span>}
          {ext.style_name?.value && <span>Estil: <strong>{ext.style_name.value}</strong></span>}
          {baseSize && <span>Talla base: <strong>{baseSize}</strong></span>}
          {sizeRun.length > 0 && <span>Run: <strong>{sizeRun.join('·')}</strong></span>}
        </div>
        {ext.size_discrepancy && (
          <div style={{
            marginTop: 8, padding: '6px 10px', background: '#fff9e6',
            border: '1px solid #f0c040', borderRadius: 6, fontSize: 12,
          }}>
            ⚠ Run de talles diferent: document [{ext.size_discrepancy.document_sizes?.join('·')}]
            vs configurat [{ext.size_discrepancy.configured_sizes?.join('·')}]
          </div>
        )}
      </div>

      <div style={{ overflowX: 'auto', marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)', marginBottom: 8 }}>
          {poms.length} POMs detectats · grading de {sizeRun.length} talles
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: 'var(--color-background-secondary, #f5f0ea)' }}>
              <th style={thStyle}>Codi fitxa</th>
              <th style={thStyle}>Descripció</th>
              <th style={thStyle}>Confiança</th>
              {sizeRun.map(s => (
                <th key={s} style={{
                  ...thStyle,
                  background: s === baseSize ? '#fdf6ee' : undefined,
                }}>{s}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {poms.map((p, i) => (
              <tr key={i} style={{ borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)' }}>
                <td style={{ ...tdStyle, fontFamily: 'monospace', color: 'var(--gold)' }}>{p.code}</td>
                <td style={tdStyle}>{p.description}</td>
                <td style={tdStyle}>
                  <span style={{
                    fontSize: 11, padding: '2px 8px', borderRadius: 20, fontWeight: 500,
                    background: p.confidence === 'HIGH' ? '#e6f4ea' : p.confidence === 'MEDIUM' ? '#fff3e0' : '#fce8e6',
                    color: p.confidence === 'HIGH' ? '#137333' : p.confidence === 'MEDIUM' ? '#e65100' : '#c5221f',
                  }}>{p.confidence}</span>
                </td>
                {sizeRun.map(s => (
                  <td key={s} style={{
                    ...tdStyle, textAlign: 'right', fontFamily: 'monospace',
                    background: s === baseSize ? '#fefaf5' : undefined,
                  }}>
                    {gradedByCode[p.code]?.[s] != null
                      ? parseFloat(gradedByCode[p.code][s]).toFixed(1)
                      : (s === baseSize ? p.base_value_cm?.toFixed(1) : '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ fontSize: 11, color: 'var(--color-text-secondary, #868685)', marginTop: 6 }}>
          L'assignació de POMs es resoldrà automàticament en confirmar.
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
        <button type="button" onClick={onReject}
          style={{ padding: '8px 16px', border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                   borderRadius: 6, background: 'transparent', cursor: 'pointer', fontSize: 13 }}>
          Tornar a pujar
        </button>
        <button type="button" onClick={onConfirm}
          style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 14,
                   fontWeight: 500, background: 'var(--gold)', color: '#fff', cursor: 'pointer' }}>
          ✓ Confirmar i guardar
        </button>
      </div>
    </div>
  )
}
