import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import TaulaEditable from '../components/TaulaEditable/TaulaEditable'

const API = import.meta.env.VITE_API_URL || ''
const TABS = ['Resum', 'Mesures', 'Fitting', 'Fitxers', 'Producció']
const FASES = ['Proto', 'Fit', 'SizeSet', 'PP', 'TOP']

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
      <FaseBar fase={model?.fase_actual} />

      <div style={{
        borderBottom: '1px solid var(--color-border-tertiary, #e0d5c5)',
        display: 'flex', gap: 0, paddingLeft: '1.5rem',
      }}>
        {TABS.map(tab => (
          <button key={tab} type="button"
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '10px 20px', border: 'none',
              borderBottom: activeTab === tab
                ? '2px solid var(--gold)' : '2px solid transparent',
              background: 'transparent', cursor: 'pointer', fontSize: 13,
              fontWeight: activeTab === tab ? 500 : 400,
              color: activeTab === tab ? 'var(--gold)' : 'var(--color-text-secondary, #868685)',
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
        {activeTab === 'Resum' && <TabResum model={model} />}
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
      gap: 16, flexWrap: 'wrap',
      padding: '1rem 1.5rem',
      borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button type="button" onClick={() => navigate('/models')}
          style={{ background: 'none', border: 'none', cursor: 'pointer',
                   fontSize: 13, color: 'var(--color-text-secondary, #868685)',
                   fontFamily: 'IBM Plex Mono, monospace' }}>
          ← Models
        </button>
        <span style={{ color: 'var(--color-border-tertiary, #e0d5c5)' }}>›</span>
        <span style={{ fontSize: 16, fontWeight: 500 }}>
          {model.nom_prenda || model.codi_intern}
        </span>
        <span style={{
          fontSize: 11, padding: '2px 8px', borderRadius: 20, fontWeight: 500,
          background: model.estat === 'Nou' ? 'var(--color-background-secondary, #f5f0ea)' : '#e6f4ea',
          color: model.estat === 'Nou' ? 'var(--color-text-secondary, #868685)' : '#137333',
          border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
        }}>
          {model.estat}
        </span>
      </div>

      <div style={{
        display: 'flex', gap: 20, fontSize: 12, flexWrap: 'wrap',
        color: 'var(--color-text-secondary, #868685)', alignItems: 'center',
      }}>
        <span style={{ fontFamily: 'monospace', fontWeight: 500,
                       color: 'var(--color-text-primary, #1d1d1b)' }}>
          {model.codi_intern}
        </span>
        {model.codi_client && model.codi_client !== model.codi_intern && (
          <span>{model.codi_client}</span>
        )}
        <span>{model.temporada} {model.any}</span>
        {model.target && <span>{model.target}</span>}
        {model.garment_type_nom && <span>{model.garment_type_nom}</span>}
        {model.construction && <span>{model.construction}</span>}
        {model.base_size_label && (
          <span style={{ color: 'var(--gold)' }}>Base: {model.base_size_label}</span>
        )}
        {model.size_run_model && (
          <span style={{ fontFamily: 'monospace' }}>{model.size_run_model}</span>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button type="button"
          onClick={() => navigate(`/models/${model.id}/editar`)}
          style={btnSecondary}>
          <i className="ti ti-edit" /> Editar
        </button>
        <button type="button"
          onClick={() => navigate(`/models/${model.id}/mesures`)}
          style={btnSecondary}>
          <i className="ti ti-ruler" /> Mesures
        </button>
        <button type="button" onClick={onDelete}
          style={{ ...btnSecondary, color: '#c5221f', borderColor: '#f5c6c6' }}>
          <i className="ti ti-trash" /> Esborrar
        </button>
      </div>
    </div>
  )
}

function FaseBar({ fase }) {
  const idx = FASES.indexOf(fase)
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      padding: '8px 1.5rem',
      background: 'var(--color-background-secondary, #f5f0ea)',
      borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
      fontSize: 12, gap: 0,
      fontFamily: 'IBM Plex Mono, monospace',
    }}>
      {FASES.map((f, i) => (
        <div key={f} style={{ display: 'flex', alignItems: 'center' }}>
          <span style={{
            padding: '3px 12px', borderRadius: 20,
            background: f === fase ? 'var(--gold)' : 'transparent',
            color: f === fase ? '#fff' : 'var(--color-text-secondary, #868685)',
            fontWeight: f === fase ? 500 : 400,
          }}>
            {i < idx ? '✓ ' : ''}{f}
          </span>
          {i < FASES.length - 1 && (
            <span style={{ color: 'var(--color-border-tertiary, #e0d5c5)', margin: '0 4px' }}>—</span>
          )}
        </div>
      ))}
    </div>
  )
}

function TabResum({ model }) {
  if (!model) return null
  const fields = [
    ['Referència interna', model.codi_intern],
    ['Referència client', model.codi_client && model.codi_client !== model.codi_intern ? model.codi_client : '—'],
    ['Nom de la peça', model.nom_prenda || '—'],
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
    ['Fase', model.fase_actual],
  ]

  return (
    <div style={{ maxWidth: 600 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <tbody>
          {fields.map(([label, value]) => (
            <tr key={label} style={{ borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)' }}>
              <td style={{ padding: '8px 0', color: 'var(--color-text-secondary, #868685)',
                           width: 180, fontSize: 12 }}>
                {label}
              </td>
              <td style={{ padding: '8px 0',
                           fontWeight: label === 'Referència interna' ? 500 : 400,
                           fontFamily: label.includes('Ref') ? 'monospace' : undefined }}>
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
