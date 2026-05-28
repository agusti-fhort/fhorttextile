import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import TaulaEditable from '../components/TaulaEditable/TaulaEditable'

const API = import.meta.env.VITE_API_URL || ''
const TABS = ['Resum', 'Mesures', 'Fitting', 'Fitxers', 'Anàlisi IA', 'Producció']

const btnSecondary = {
  background: 'transparent',
  border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
  borderRadius: 6, padding: '6px 12px', fontSize: 12,
  cursor: 'pointer', color: 'var(--color-text-primary, #1d1d1b)',
  display: 'flex', alignItems: 'center', gap: 4,
  fontFamily: 'IBM Plex Mono, monospace',
}

export default function ModelFitxa({ defaultTab = 'Mesures' }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const [model, setModel] = useState(null)
  const [activeTab, setActiveTab] = useState(defaultTab)
  const [taulaRows, setTaulaRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders }).then(r => r.json()),
      fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders }).then(r => r.json()),
    ]).then(([modelData, taulaData]) => {
      setModel(modelData)
      setTaulaRows(taulaData.rows || [])
    }).catch(() => setError('Error carregant el model'))
    .finally(() => setLoading(false))
  }, [id])

  const handleDelete = async () => {
    if (!window.confirm(`Esborrar ${model?.codi_intern}? Aquesta acció no es pot desfer.`)) return
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/`, {
        method: 'DELETE', headers: authHeaders,
      })
      if (r.ok || r.status === 204) navigate('/models')
      else setError('Error esborrant el model')
    } catch {
      setError('Error de connexió')
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center',
                    color: 'var(--color-text-secondary, #868685)',
                    fontFamily: 'IBM Plex Mono, monospace', fontSize: 13 }}>
        Carregant...
      </div>
    )
  }

  return (
    <div style={{ width: '100%', fontFamily: 'IBM Plex Mono, monospace' }}>
      <ModelFitxaHeader model={model} onDelete={handleDelete} />

      <div style={{
        display: 'flex', gap: 8, padding: '0.75rem 1.5rem',
        borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
        background: 'var(--color-background-primary)',
      }}>
        {TABS.map(tab => (
          <button key={tab} type="button"
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '6px 16px', borderRadius: 6, border: 'none',
              background: activeTab === tab ? 'var(--gold)' : 'var(--color-background-secondary, #f5f0ea)',
              color: activeTab === tab ? '#fff' : 'var(--color-text-secondary, #868685)',
              cursor: 'pointer', fontSize: 13,
              fontWeight: activeTab === tab ? 500 : 400,
              fontFamily: 'IBM Plex Mono, monospace',
            }}>
            {tab}
          </button>
        ))}
      </div>

      {error && (
        <div style={{
          margin: '1rem 1.5rem', padding: '0.75rem 1rem',
          background: '#fee', border: '1px solid #fcc', borderRadius: 8,
          fontSize: 13, color: '#c00',
        }}>{error}</div>
      )}

      <div style={{ padding: '1.5rem' }}>
        {activeTab === 'Resum' && (
          <TabResum
            model={model}
            modelId={parseInt(id)}
            onUpdated={() => {
              fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders })
                .then(r => r.json()).then(setModel)
            }}
          />
        )}
        {activeTab === 'Mesures' && (
          <TaulaEditable
            rows={taulaRows}
            sizeRun={(model?.size_run_model || '').split('·').map(s => s.trim()).filter(Boolean)}
            baseSize={model?.base_size_label}
            modelId={parseInt(id)}
            isImport={false}
            onSaved={setTaulaRows}
          />
        )}
        {activeTab === 'Fitting' && <TabFitting modelId={id} />}
        {activeTab === 'Fitxers' && <TabFitxers modelId={parseInt(id)} />}
        {activeTab === 'Anàlisi IA' && <TabAnalisiIA modelId={parseInt(id)} />}
        {activeTab === 'Producció' && <TabProduccio model={model} />}
      </div>
    </div>
  )
}

function ModelFitxaHeader({ model, onDelete }) {
  const navigate = useNavigate()
  if (!model) return null

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0.75rem 1.5rem',
      borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <button type="button" onClick={() => navigate('/models')}
          style={{ background: 'none', border: 'none', cursor: 'pointer',
                   fontSize: 13, color: 'var(--color-text-secondary, #868685)',
                   fontFamily: 'IBM Plex Mono, monospace' }}>
          ← Models
        </button>
        <span style={{ color: 'var(--color-border-tertiary, #e0d5c5)' }}>›</span>
        <span style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)',
                       fontFamily: 'monospace' }}>
          {model.codi_intern}
        </span>
        {model.codi_client && model.codi_client !== model.codi_intern && (
          <>
            <span style={{ color: 'var(--color-border-tertiary, #e0d5c5)' }}>·</span>
            <span style={{ fontSize: 13, fontFamily: 'monospace',
                           color: 'var(--color-text-primary, #1d1d1b)', fontWeight: 500 }}>
              {model.codi_client}
            </span>
          </>
        )}
        {model.nom_prenda && (
          <>
            <span style={{ color: 'var(--color-border-tertiary, #e0d5c5)' }}>·</span>
            <span style={{ fontSize: 15, fontWeight: 500,
                           color: 'var(--color-text-primary, #1d1d1b)' }}>
              {model.nom_prenda}
            </span>
          </>
        )}
        <span style={{
          fontSize: 11, padding: '2px 8px', borderRadius: 20, fontWeight: 500,
          background: 'var(--color-background-secondary, #f5f0ea)',
          color: 'var(--color-text-secondary, #868685)',
          border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
        }}>
          {model.estat}
        </span>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button type="button"
          onClick={() => navigate(`/models/${model.id}/editar`)}
          style={btnSecondary}>
          <i className="ti ti-edit" aria-hidden="true" /> Editar
        </button>
        <button type="button" onClick={onDelete}
          style={{ ...btnSecondary, color: '#c5221f', borderColor: '#f5c6c6' }}>
          <i className="ti ti-trash" aria-hidden="true" /> Esborrar
        </button>
      </div>
    </div>
  )
}

function TabResum({ model, modelId, onUpdated }) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    nom_prenda: model?.nom_prenda || '',
    codi_client: (model?.codi_client !== model?.codi_intern ? model?.codi_client : '') || '',
    descripcio: model?.descripcio || '',
  })
  const [saving, setSaving] = useState(false)
  const token = localStorage.getItem('access_token')

  const handleSave = async () => {
    setSaving(true)
    try {
      const r = await fetch(`${API}/api/v1/models/${modelId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          nom_prenda: form.nom_prenda,
          codi_client: form.codi_client || model.codi_intern,
          descripcio: form.descripcio,
        }),
      })
      if (r.ok) { setEditing(false); if (onUpdated) onUpdated() }
    } finally { setSaving(false) }
  }

  if (!model) return null

  const readOnlyFields = [
    ['Referència interna', model.codi_intern],
    ['Temporada', `${model.temporada} ${model.any}`],
    ['Target', model.target || '—'],
    ['Tipus de peça', model.garment_type_nom || '—'],
    ['Construcció', model.construction || '—'],
    ['Fit type', model.fit_type || '—'],
    ['Sistema de talles', model.size_system_nom || '—'],
    ['Talla base', model.base_size_label || '—'],
    ['Run de talles', model.size_run_model || '—'],
    ['Grading', model.grading_rule_set ? '✓ Configurat' : '—'],
    ['Estat', model.estat],
    ...(model.fabric_main ? [
      ['Main Fabric', model.fabric_main],
      ['Composition', model.fabric_composition || '—'],
      ['Shrinkage', model.shrinkage_warp != null
        ? `Warp ${model.shrinkage_warp}% / Weft ${model.shrinkage_weft}% (${model.shrinkage_type})`
        : model.shrinkage_pct != null
          ? `${model.shrinkage_pct}% (${model.shrinkage_type})`
          : '—'],
    ] : []),
  ]

  return (
    <div style={{ maxWidth: 640 }}>
      {editing ? (
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                            display: 'block', marginBottom: 4 }}>
              Nom de la peça
            </label>
            <input value={form.nom_prenda}
              onChange={e => setForm(f => ({...f, nom_prenda: e.target.value}))}
              style={{ width: '100%', padding: '6px 10px', fontSize: 13,
                       border: '1px solid var(--color-border-tertiary, #e0d5c5)', borderRadius: 6 }} />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                            display: 'block', marginBottom: 4 }}>
              Referència client
            </label>
            <input value={form.codi_client}
              onChange={e => setForm(f => ({...f, codi_client: e.target.value}))}
              style={{ width: '100%', padding: '6px 10px', fontSize: 13,
                       border: '1px solid var(--color-border-tertiary, #e0d5c5)', borderRadius: 6 }} />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                            display: 'block', marginBottom: 4 }}>
              Descripció
            </label>
            <textarea value={form.descripcio}
              onChange={e => setForm(f => ({...f, descripcio: e.target.value}))}
              rows={3}
              style={{ width: '100%', padding: '6px 10px', fontSize: 13,
                       border: '1px solid var(--color-border-tertiary, #e0d5c5)', borderRadius: 6,
                       resize: 'vertical' }} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={handleSave} disabled={saving}
              style={{ padding: '6px 16px', background: 'var(--gold)', color: '#fff',
                       border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}>
              {saving ? 'Guardant...' : '✓ Guardar'}
            </button>
            <button type="button" onClick={() => setEditing(false)}
              style={{ padding: '6px 14px', background: 'transparent', fontSize: 13,
                       border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                       borderRadius: 6, cursor: 'pointer' }}>
              Cancel·lar
            </button>
          </div>
        </div>
      ) : (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'flex-start', marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 18, fontWeight: 500 }}>
                {model.nom_prenda || <span style={{color:'var(--color-text-secondary, #868685)'}}>Sense nom</span>}
              </div>
              {model.codi_client && model.codi_client !== model.codi_intern && (
                <div style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)',
                              fontFamily: 'monospace', marginTop: 2 }}>
                  {model.codi_client}
                </div>
              )}
              {model.descripcio && (
                <div style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)',
                              marginTop: 6 }}>
                  {model.descripcio}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <tbody>
          {readOnlyFields.map(([label, value]) => (
            <tr key={label}
              style={{ borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)' }}>
              <td style={{ padding: '7px 0', color: 'var(--color-text-secondary, #868685)',
                           width: 180, fontSize: 12 }}>
                {label}
              </td>
              <td style={{ padding: '7px 0',
                           fontFamily: label === 'Referència interna' || label === 'Run de talles'
                             ? 'monospace' : undefined,
                           color: label === 'Referència interna'
                             ? 'var(--color-text-secondary, #868685)' : 'var(--color-text-primary, #1d1d1b)' }}>
                {value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TabFitting() {
  return (
    <div style={{ color: 'var(--color-text-secondary, #868685)', fontSize: 13, padding: '2rem 0' }}>
      <i className="ti ti-ruler-2" style={{ fontSize: 24, display: 'block', marginBottom: 8 }} />
      Sessions de fitting — pròximament.
    </div>
  )
}

const TIPUS_CONFIG = {
  SKETCH_FLETXES: { label: 'Sketch amb fletxes', icon: 'ti-pencil',             color: '#c27a2a' },
  SKETCH_NET:     { label: 'Sketch net',         icon: 'ti-eye',                color: '#137333' },
  PATRO:          { label: 'Patró base',         icon: 'ti-vector-triangle',    color: '#185fa5' },
  MARCADA:        { label: 'Marcada',            icon: 'ti-layout',             color: '#7a4a10' },
  ESCALAT:        { label: 'Escalat',            icon: 'ti-arrows-maximize',    color: '#5f3dc4' },
  FITXA:          { label: 'Fitxa tècnica',      icon: 'ti-file-text',          color: '#333' },
  ALTRES:         { label: 'Altres',             icon: 'ti-file',               color: '#888' },
}

function TabFitxers({ modelId }) {
  const token = localStorage.getItem('access_token')
  const authHeaders = { Authorization: `Bearer ${token}` }

  const [fitxers, setFitxers] = useState({})
  const [uploading, setUploading] = useState(null)
  const [popup, setPopup] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all(
      Object.keys(TIPUS_CONFIG).map(tipus =>
        fetch(`${API}/api/v1/model-fitxers/?model=${modelId}&tipus=${tipus}`, { headers: authHeaders })
          .then(r => r.json())
          .then(d => [tipus, d.results || d || []])
      )
    ).then(results => {
      const byTipus = {}
      results.forEach(([tipus, items]) => { byTipus[tipus] = items })
      setFitxers(byTipus)
    }).catch(() => setError('Error carregant fitxers'))
  }, [modelId])

  const handleUpload = async (tipus, file) => {
    setUploading(tipus)
    const formData = new FormData()
    formData.append('fitxer', file)
    formData.append('tipus', tipus)
    formData.append('nom', file.name)
    try {
      const r = await fetch(`${API}/api/v1/models/${modelId}/upload-fitxer/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      const d = await r.json()
      if (r.ok) {
        setFitxers(prev => ({
          ...prev,
          [tipus]: [d, ...(prev[tipus] || [])],
        }))
      } else {
        setError(JSON.stringify(d))
      }
    } catch {
      setError('Error pujant el fitxer')
    } finally {
      setUploading(null)
    }
  }

  const handleDelete = async (fitxerId, tipus) => {
    if (!window.confirm('Eliminar aquest fitxer?')) return
    await fetch(`${API}/api/v1/model-fitxers/${fitxerId}/`, {
      method: 'DELETE', headers: authHeaders,
    })
    setFitxers(prev => ({
      ...prev,
      [tipus]: (prev[tipus] || []).filter(f => f.id !== fitxerId),
    }))
  }

  return (
    <div style={{ width: '100%', fontFamily: 'IBM Plex Mono, monospace' }}>
      {error && (
        <div style={{
          background: '#fee', border: '1px solid #fcc', borderRadius: 6,
          padding: '8px 12px', marginBottom: 12, fontSize: 13, color: '#c00',
        }}>{error}</div>
      )}

      {popup && (
        <div onClick={() => setPopup(null)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
          <div onClick={e => e.stopPropagation()}
            style={{ background: '#fff', borderRadius: 8, padding: 16,
                     maxWidth: '90vw', maxHeight: '90vh' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{popup.nom}</span>
              <button type="button" onClick={() => setPopup(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18 }}>✕</button>
            </div>
            {popup.url?.match(/\.(jpg|jpeg|png|svg)$/i) ? (
              <img src={popup.url} alt={popup.nom}
                style={{ maxWidth: '80vw', maxHeight: '80vh', objectFit: 'contain' }} />
            ) : (
              <iframe src={popup.url} title={popup.nom}
                style={{ width: '80vw', height: '80vh', border: 'none' }} />
            )}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        {Object.entries(TIPUS_CONFIG).map(([tipus, config]) => (
          <div key={tipus}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <i className={`ti ${config.icon}`} aria-hidden="true"
                style={{ fontSize: 18, color: config.color }} />
              <span style={{ fontSize: 14, fontWeight: 500 }}>{config.label}</span>
              <span style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)' }}>
                ({(fitxers[tipus] || []).length})
              </span>
              <label style={{
                marginLeft: 'auto', padding: '4px 12px', fontSize: 12,
                border: '0.5px solid var(--color-border-tertiary, #e0d5c5)', borderRadius: 6,
                cursor: 'pointer', color: 'var(--color-text-secondary, #868685)',
                background: uploading === tipus ? 'var(--color-background-secondary, #f5f0ea)' : 'transparent',
              }}>
                {uploading === tipus ? 'Pujant...' : '+ Pujar'}
                <input type="file" style={{ display: 'none' }}
                  accept=".pdf,.png,.jpg,.jpeg,.svg,.dxf"
                  disabled={uploading === tipus}
                  onChange={e => e.target.files[0] && handleUpload(tipus, e.target.files[0])} />
              </label>
            </div>

            {(fitxers[tipus] || []).length === 0 ? (
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                            padding: '8px 0', fontStyle: 'italic' }}>
                Cap fitxer pujat.
              </div>
            ) : (
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                {(fitxers[tipus] || []).map(f => (
                  <FitxerCard key={f.id} fitxer={f} config={config}
                    onPreview={() => setPopup({ url: f.fitxer || f.url, nom: f.nom_fitxer })}
                    onDelete={() => handleDelete(f.id, tipus)} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function FitxerCard({ fitxer, config, onPreview, onDelete }) {
  const isImage = fitxer.nom_fitxer?.match(/\.(jpg|jpeg|png|svg)$/i)

  return (
    <div style={{
      width: 140, border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
      borderRadius: 8, overflow: 'hidden', fontSize: 12,
      fontFamily: 'IBM Plex Mono, monospace',
    }}>
      <div onClick={onPreview}
        style={{
          height: 90, background: 'var(--color-background-secondary, #f5f0ea)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', position: 'relative',
        }}>
        {isImage && (fitxer.fitxer || fitxer.url) ? (
          <img src={fitxer.fitxer || fitxer.url} alt={fitxer.nom_fitxer}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        ) : (
          <i className={`ti ${config.icon}`} aria-hidden="true"
            style={{ fontSize: 32, color: config.color }} />
        )}
        {fitxer.versio > 1 && (
          <span style={{
            position: 'absolute', top: 4, right: 4,
            background: 'rgba(0,0,0,0.6)', color: '#fff',
            fontSize: 10, padding: '1px 5px', borderRadius: 10,
          }}>
            v{fitxer.versio}
          </span>
        )}
      </div>

      <div style={{ padding: '6px 8px' }}>
        <div style={{
          fontSize: 11, color: 'var(--color-text-primary, #1d1d1b)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          marginBottom: 4,
        }} title={fitxer.nom_fitxer}>
          {fitxer.nom_fitxer}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button type="button" onClick={onPreview}
            style={{ flex: 1, padding: '3px 0', fontSize: 11, border: 'none',
                     background: 'var(--color-background-secondary, #f5f0ea)',
                     borderRadius: 4, cursor: 'pointer',
                     fontFamily: 'IBM Plex Mono, monospace' }}>
            <i className="ti ti-eye" aria-hidden="true" /> Veure
          </button>
          <button type="button" onClick={onDelete}
            style={{ padding: '3px 6px', fontSize: 11, border: 'none',
                     background: 'transparent', borderRadius: 4,
                     cursor: 'pointer', color: '#c5221f' }}>
            <i className="ti ti-trash" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  )
}

const GRAVETAT_STYLE = {
  CRITICA:     { bg: '#fce8e6', color: '#c5221f', border: '#f5c6c6' },
  IMPORTANT:   { bg: '#fff3e0', color: '#c8900a', border: '#f0c040' },
  INFORMATIVA: { bg: '#e6f4ea', color: '#137333', border: '#a8d5b5' },
}

function TabAnalisiIA({ modelId }) {
  const token = localStorage.getItem('access_token')
  const [analisi, setAnalisi] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleAnalitzar = async () => {
    setLoading(true); setError(''); setAnalisi(null)
    try {
      const r = await fetch(`${API}/api/v1/models/${modelId}/analisi-ia/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({}),
      })
      const d = await r.json()
      if (r.ok) setAnalisi(d.analisi)
      else setError(d.error || 'Error desconegut')
    } catch {
      setError('Error de connexió')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, fontFamily: 'IBM Plex Mono, monospace' }}>
      <div style={{ marginBottom: 16 }}>
        <p style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)', marginBottom: 12 }}>
          Analitza els fitxers pujats (patrons, escalats, sketches) i detecta
          discrepàncies amb les mesures registrades.
          Disponible quan hi ha patrons o escalats pujats.
        </p>
        <button type="button" onClick={handleAnalitzar} disabled={loading}
          style={{
            padding: '8px 20px', background: loading ? '#ccc' : 'var(--gold)',
            color: '#fff', border: 'none', borderRadius: 6,
            fontSize: 13, fontWeight: 500, cursor: loading ? 'not-allowed' : 'pointer',
            fontFamily: 'IBM Plex Mono, monospace',
          }}>
          {loading ? (
            <><i className="ti ti-loader" aria-hidden="true" /> Analitzant...</>
          ) : (
            <><i className="ti ti-cpu" aria-hidden="true" /> Llançar anàlisi IA</>
          )}
        </button>
      </div>

      {error && (
        <div style={{ background: '#fee', border: '1px solid #fcc', borderRadius: 6,
                      padding: '8px 12px', fontSize: 13, color: '#c00', marginBottom: 12 }}>
          {error}
        </div>
      )}

      {analisi && (
        <div>
          <div style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)',
                        marginBottom: 12 }}>
            {analisi.resum}
            {' · '}{analisi.fitxers_analitzats} fitxer(s) analitzat(s)
          </div>

          {(analisi.alertes || []).length === 0 ? (
            <div style={{ fontSize: 13, color: '#137333', padding: '12px 0' }}>
              ✓ Cap discrepància detectada.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {analisi.alertes.map((alerta, i) => {
                const style = GRAVETAT_STYLE[alerta.gravetat] || GRAVETAT_STYLE.INFORMATIVA
                return (
                  <div key={i} style={{
                    background: style.bg, border: `1px solid ${style.border}`,
                    borderRadius: 8, padding: '12px 14px',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8,
                                  marginBottom: 4 }}>
                      <span style={{ fontSize: 11, fontWeight: 500, color: style.color,
                                     padding: '1px 8px', background: 'rgba(255,255,255,0.6)',
                                     borderRadius: 20 }}>
                        {alerta.gravetat}
                      </span>
                      <span style={{ fontSize: 11, color: style.color }}>
                        {alerta.tipus?.replace(/_/g, ' ')}
                      </span>
                      {alerta.pom_afectat && (
                        <span style={{ fontFamily: 'monospace', fontSize: 12,
                                       color: style.color, fontWeight: 500 }}>
                          {alerta.pom_afectat}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--color-text-primary, #1d1d1b)',
                                  marginBottom: 6 }}>
                      {alerta.descripcio}
                    </div>
                    {(alerta.valor_taula || alerta.valor_patro) && (
                      <div style={{ fontSize: 12, color: style.color, marginBottom: 4 }}>
                        Taula: {alerta.valor_taula || '—'} → Patró: {alerta.valor_patro || '—'}
                      </div>
                    )}
                    <div style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                                  fontStyle: 'italic' }}>
                      → {alerta.accio_suggerida}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TabProduccio() {
  return (
    <div style={{ color: 'var(--color-text-secondary, #868685)', fontSize: 13, padding: '2rem 0' }}>
      <i className="ti ti-list-check" style={{ fontSize: 24, display: 'block', marginBottom: 8 }} />
      Tasques i estat de producció — pròximament.
    </div>
  )
}
