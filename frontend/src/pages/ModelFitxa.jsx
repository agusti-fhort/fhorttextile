import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import TaulaEditable from '../components/TaulaEditable/TaulaEditable'

const API = import.meta.env.VITE_API_URL || ''
const TABS = ['Resum', 'Mesures', 'Fitting', 'Fitxers', 'Producció']

const btnSecondary = {
  background: 'transparent',
  border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
  borderRadius: 6, padding: '6px 12px', fontSize: 12,
  cursor: 'pointer', color: 'var(--color-text-primary, #1d1d1b)',
  display: 'flex', alignItems: 'center', gap: 4,
  fontFamily: 'IBM Plex Mono, monospace',
}

export default function ModelFitxa() {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const [model, setModel] = useState(null)
  const [activeTab, setActiveTab] = useState('Mesures')
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
            sizeRun={model?.size_run_model?.split('·').map(s => s.trim()) || []}
            baseSize={model?.base_size_label}
            modelId={parseInt(id)}
            isImport={false}
            onSaved={setTaulaRows}
          />
        )}
        {activeTab === 'Fitting' && <TabFitting modelId={id} />}
        {activeTab === 'Fitxers' && <TabFitxers modelId={id} />}
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
            <button type="button" onClick={() => setEditing(true)}
              style={{ padding: '5px 12px', background: 'transparent', fontSize: 12,
                       border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                       borderRadius: 6, cursor: 'pointer', whiteSpace: 'nowrap' }}>
              <i className="ti ti-edit" aria-hidden="true" /> Editar
            </button>
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

function TabFitxers() {
  return (
    <div style={{ color: 'var(--color-text-secondary, #868685)', fontSize: 13, padding: '2rem 0' }}>
      <i className="ti ti-files" style={{ fontSize: 24, display: 'block', marginBottom: 8 }} />
      Sketches, patrons i fitxers tècnics — Pas 4 pròximament.
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
