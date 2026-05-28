import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'

const API = import.meta.env.VITE_API_URL || ''

const SEASONS = [
  { codi: 'SS',  label: 'SS',  sub: 'Spring/Summer' },
  { codi: 'FW',  label: 'FW',  sub: 'Fall/Winter' },
  { codi: 'RE',  label: 'RE',  sub: 'Resort' },
  { codi: 'PRE', label: 'PRE', sub: 'Pre-collection' },
]

const anyActual = new Date().getFullYear()
const YEARS = [anyActual, anyActual + 1, anyActual + 2, anyActual + 3]

const BORDER_INACTIVE = '0.5px solid var(--color-border-tertiary, var(--border))'

const chipStyle = (active) => ({
  padding: '10px 16px',
  borderRadius: 6,
  cursor: 'pointer',
  background: active ? 'var(--gold)' : '#fff',
  color: active ? '#fff' : 'var(--text-main)',
  border: active ? '0.5px solid var(--gold)' : BORDER_INACTIVE,
  fontFamily: 'IBM Plex Mono, monospace',
  fontSize: 12,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: 2,
  minWidth: 72,
  fontWeight: active ? 600 : 400,
})

const inputStyle = {
  width: '100%',
  padding: '8px 10px',
  borderRadius: 4,
  border: BORDER_INACTIVE,
  fontFamily: 'IBM Plex Mono, monospace',
  fontSize: 12,
  background: '#fff',
  color: 'var(--text-main)',
}

const labelStyle = {
  display: 'block',
  fontSize: 10,
  color: 'var(--text-muted)',
  marginBottom: 4,
  textTransform: 'uppercase',
  letterSpacing: '.04em',
}

export default function ModelWizard() {
  const navigate = useNavigate()
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')

  const [year, setYear] = useState(null)
  const [season, setSeason] = useState(null)
  const [refClient, setRefClient] = useState('')
  const [nomPrenda, setNomPrenda] = useState('')
  const [descripcio, setDescripcio] = useState('')
  const [previewRef, setPreviewRef] = useState('—')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!year || !season) { setPreviewRef('—'); return }
    let aborted = false
    fetch(`${API}/api/v1/models/next-ref/?year=${year}&season=${season}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => { if (!aborted) setPreviewRef(d.codi_intern || '—') })
      .catch(() => { if (!aborted) setPreviewRef('—') })
    return () => { aborted = true }
  }, [year, season, token])

  const handleCreate = async () => {
    setSubmitting(true)
    setError('')
    try {
      const payload = {
        any: year,
        temporada: season,
        codi_client: refClient || null,
        nom_prenda: nomPrenda || null,
        descripcio: descripcio || null,
      }
      const r = await fetch(`${API}/api/v1/models/create-wizard/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      })
      const data = await r.json()
      if (!r.ok) {
        throw new Error(data.detail || JSON.stringify(data))
      }
      navigate(`/models/${data.id}/editar`)
    } catch (e) {
      setError(e.message)
      setSubmitting(false)
    }
  }

  return (
    <div style={{ fontFamily: 'IBM Plex Mono, monospace', maxWidth: 680, padding: 24 }}>
      <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 24 }}>Nou model</h1>

      <div style={{ marginBottom: 24 }}>
        <label style={labelStyle}>Any</label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {YEARS.map(y => (
            <button key={y} onClick={() => setYear(y)} style={chipStyle(year === y)}>
              <span>{y}</span>
            </button>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 24 }}>
        <label style={labelStyle}>Temporada</label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {SEASONS.map(s => (
            <button key={s.codi} onClick={() => setSeason(s.codi)} style={chipStyle(season === s.codi)}>
              <span>{s.label}</span>
              <span style={{ fontSize: 9, opacity: 0.85 }}>{s.sub}</span>
            </button>
          ))}
        </div>
      </div>

      <div style={{
        marginBottom: 24,
        padding: '12px 14px',
        borderRadius: 6,
        background: 'var(--bg-muted)',
        border: BORDER_INACTIVE,
      }}>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>
          Referència interna
        </div>
        <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--gold)' }}>
          {previewRef}
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Referència client (opcional)</label>
        <input
          type="text"
          value={refClient}
          onChange={e => setRefClient(e.target.value)}
          style={inputStyle}
          placeholder="ex: AB-1234"
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Nom de la peça (opcional)</label>
        <input
          type="text"
          value={nomPrenda}
          onChange={e => setNomPrenda(e.target.value)}
          style={inputStyle}
          placeholder="ex: Brusa màniga llarga"
        />
      </div>

      <div style={{ marginBottom: 24 }}>
        <label style={labelStyle}>Descripció (opcional)</label>
        <textarea
          value={descripcio}
          onChange={e => setDescripcio(e.target.value)}
          style={{ ...inputStyle, minHeight: 80, resize: 'vertical' }}
        />
      </div>

      {error && (
        <div style={{
          marginBottom: 16, padding: '8px 12px', borderRadius: 4,
          background: 'var(--err-bg)', color: 'var(--err)', fontSize: 11,
        }}>{error}</div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={handleCreate}
          disabled={submitting}
          style={{
            padding: '10px 20px',
            borderRadius: 6,
            background: 'var(--gold)',
            color: '#fff',
            border: '0.5px solid var(--gold)',
            fontFamily: 'IBM Plex Mono, monospace',
            fontSize: 12,
            fontWeight: 600,
            cursor: submitting ? 'wait' : 'pointer',
            opacity: submitting ? 0.6 : 1,
          }}
        >
          Crear model →
        </button>
      </div>
    </div>
  )
}
