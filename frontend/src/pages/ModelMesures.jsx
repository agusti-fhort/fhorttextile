import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import TaulaEditable from '../components/TaulaEditable/TaulaEditable'
import XatMesures from '../components/XatMesures/XatMesures'

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

  // Import
  const [importFile, setImportFile] = useState(null)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)

  // Taula final
  const [taulaRows, setTaulaRows] = useState([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    Promise.all([
      fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders }).then(r => r.json()),
      fetch(`${API}/api/v1/models/${id}/poms-suggerits/`, { headers: authHeaders }).then(r => r.json()),
    ]).then(([modelData, pomsData]) => {
      setModel(modelData)
      setPomsSuggerits(pomsData.poms || [])
    }).catch(() => setError('Error carregant les dades'))
  }, [id])

  useEffect(() => {
    if (!id) return
    fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
      .then(r => r.json())
      .then(d => {
        if (d.rows && d.rows.length > 0) {
          setTaulaRows(d.rows)
          setMode('manual')
        }
      })
      .catch(() => {})
  }, [id])

  const handleImport = async () => {
    if (!importFile) return
    setImporting(true); setError('')
    try {
      const formData = new FormData()
      formData.append('file', importFile)
      formData.append('target_codi',       model?.target || '')
      formData.append('garment_type_codi', model?.garment_type_nom || String(model?.garment_type || ''))
      formData.append('garment_type_nom',  model?.garment_type_nom || '')
      formData.append('construction_codi', model?.construction || '')
      formData.append('size_system_codi',  model?.size_system_nom || String(model?.size_system || ''))
      formData.append('size_run',          model?.size_run_model || '')
      formData.append('base_size',         model?.base_size_label || '')
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
      setMode('resultat')
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

          <TaulaEditable
            rows={taulaRows.length > 0 ? taulaRows : pomsSuggerits
              .filter(p => p.is_key)
              .map((p, i) => ({
                id: `tmp-${p.pom_id}`,
                pom_id: p.pom_id, pom_code: p.pom_code,
                nom_ca: p.nom_ca, nom_en: p.nom_en, nom_fitxa: '',
                base_value_cm: null, graded: {}, ordre: i,
              }))}
            sizeRun={model?.size_run_model?.split('·').map(s => s.trim()) || []}
            baseSize={model?.base_size_label}
            modelId={parseInt(id)}
            isImport={false}
            onSaved={(newRows) => setTaulaRows(newRows)}
          />

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 24 }}>
            <button type="button" onClick={() => setMode('selector')}
              style={{ padding: '8px 16px', border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                       borderRadius: 6, background: 'transparent', cursor: 'pointer', fontSize: 13 }}>
              ← Enrere
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
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16 }}>
              <ImportPreview
                result={importResult}
                model={model}
                onConfirm={handleConfirmImport}
                onReject={() => { setImportResult(null); setImportFile(null) }}
              />
              <XatMesures
                modelId={parseInt(id)}
                onMesuresUpdated={() => {
                  fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
                    .then(r => r.json())
                    .then(d => setTaulaRows(d.rows || []))
                }}
              />
            </div>
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

          <TaulaEditable
            rows={taulaRows}
            sizeRun={model?.size_run_model?.split('·').map(s => s.trim()) || []}
            baseSize={model?.base_size_label}
            modelId={parseInt(id)}
            isImport={importResult != null}
            onSaved={(newRows) => setTaulaRows(newRows)}
          />

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
            <button type="button" onClick={() => navigate(`/models/${id}`)}
              style={{
                padding: '8px 20px', borderRadius: 6, border: 'none',
                fontSize: 14, fontWeight: 500,
                background: 'var(--gold)', color: '#fff', cursor: 'pointer',
                fontFamily: 'IBM Plex Mono, monospace',
              }}>
              Continuar a la fitxa →
            </button>
          </div>
        </div>
      )}
    </>
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
