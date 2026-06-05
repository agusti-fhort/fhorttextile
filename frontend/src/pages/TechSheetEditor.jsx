import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

const API = import.meta.env.VITE_API_URL || ''

// Editor de fitxa tècnica — pantalla full-screen, FORA del layout principal (sense sidebar).
// Al muntar: carrega l'estat (GET) i adquireix el lock (POST .../lock/).
// Al desmontar: allibera el lock (POST .../unlock/) — fire-and-forget.
export default function TechSheetEditor() {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const [sheet, setSheet] = useState(null)
  const [model, setModel] = useState(null)
  const [lockState, setLockState] = useState('loading') // 'loading' | 'owned' | 'conflict' | 'error'
  const [conflict, setConflict] = useState(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false

    // Nom del model per a la capçalera (paral·lel, no bloqueja l'editor).
    fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(data => { if (!cancelled && data) setModel(data) })
      .catch(() => {})

    // Estat + adquisició del lock.
    fetch(`${API}/api/v1/models/${id}/tech-sheet/`, { headers: authHeaders })
      .then(r => r.json())
      .then(data => { if (!cancelled) setSheet(data) })
      .catch(() => {})

    fetch(`${API}/api/v1/models/${id}/tech-sheet/lock/`, { method: 'POST', headers: authHeaders })
      .then(async r => {
        if (cancelled) return
        if (r.ok) {
          setSheet(await r.json())
          setLockState('owned')
        } else if (r.status === 409) {
          setConflict(await r.json())
          setLockState('conflict')
        } else {
          setLockState('error')
        }
      })
      .catch(() => { if (!cancelled) setLockState('error') })

    // Cleanup: alliberar el lock en sortir (fire-and-forget; keepalive perquè surti
    // encara que el navegador estigui descarregant la pàgina).
    return () => {
      cancelled = true
      fetch(`${API}/api/v1/models/${id}/tech-sheet/unlock/`, {
        method: 'POST', headers: authHeaders, keepalive: true,
      }).catch(() => {})
    }
  }, [id])

  const badge = (() => {
    if (lockState === 'loading') return { text: 'Carregant…', bg: 'var(--gray-l)', fg: 'var(--text-main)' }
    if (lockState === 'owned') return { text: 'Editant', bg: 'var(--gold)', fg: 'var(--white)' }
    if (lockState === 'conflict') return {
      text: `Bloquejada per ${conflict?.locked_by || 'un altre usuari'}`,
      bg: 'var(--warn-bg)', fg: 'var(--warn)',
    }
    return { text: 'Error de bloqueig', bg: 'var(--warn-bg)', fg: 'var(--warn)' }
  })()

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg, #faf7f2)' }}>
      <header style={{
        display: 'flex', alignItems: 'center', gap: 16,
        padding: '0.7rem 1.2rem', borderBottom: '0.5px solid var(--gray-l)',
        background: 'var(--white)',
      }}>
        <button onClick={() => navigate(`/models/${id}`)} style={{
          display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, padding: '6px 10px',
          borderRadius: 6, border: '0.5px solid var(--gray-l)', background: 'var(--white)',
          cursor: 'pointer', color: 'var(--text-main)',
        }}>
          <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> Tornar al model
        </button>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-main)' }}>
          {model?.codi_intern || `#${id}`}{model?.nom_prenda ? ` · ${model.nom_prenda}` : ''}
        </span>
        <span style={{
          marginLeft: 'auto', fontSize: 11, fontWeight: 500, padding: '3px 10px',
          borderRadius: 10, background: badge.bg, color: badge.fg, whiteSpace: 'nowrap',
        }}>
          {badge.text}
        </span>
      </header>

      <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-muted, #999)' }}>
          <i className="ti ti-file-text" style={{ fontSize: 40, opacity: 0.5 }} />
          <p style={{ marginTop: 12, fontSize: 15 }}>Editor de fitxa tècnica — en construcció</p>
        </div>
      </main>
    </div>
  )
}
