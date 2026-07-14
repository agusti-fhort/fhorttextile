
import { useState, useEffect } from "react"
import useAuthStore from "../store/auth"

const API = import.meta.env.VITE_API_URL || ""

export function UnitToggle() {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const [unit, setUnit] = useState('CM')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch(`${API}/api/v1/tenant-config/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => setUnit(d.unitat_mesura || 'CM'))
      .catch(() => {})
  }, [token])

  const toggle = async () => {
    const nou = unit === 'CM' ? 'INCH' : 'CM'
    setSaving(true)
    try {
      const r = await fetch(`${API}/api/v1/tenant-config/`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ unitat_mesura: nou }),
      })
      if (r.ok) {
        setUnit(nou)
        // Notificar la resta de l'app
        window.dispatchEvent(new CustomEvent('unit-changed', { detail: { unit: nou } }))
      }
    } catch { /* preferència d'unitats: no poder-la desar no és fatal */ }
    setSaving(false)
  }

  return (
    <button
      onClick={toggle}
      disabled={saving}
      title={`Canviar a ${unit === 'CM' ? 'Polzades (inch)' : 'Centímetres (cm)'}`}
      style={{
        display: 'flex', alignItems: 'center', gap: 4,
        padding: '4px 10px', borderRadius: 4,
        background: unit === 'INCH' ? '#f5e6d0' : '#f5f0ea',
        color: unit === 'INCH' ? 'var(--gold)' : 'var(--text-muted)',
        border: `1px solid ${unit === 'INCH' ? 'var(--gold)' : 'var(--border)'}`,
        fontSize: 'var(--fs-body)',
        cursor: saving ? 'not-allowed' : 'pointer',
        transition: 'all .15s',
      }}
    >
      <span style={{ fontWeight: 600 }}>{unit === 'CM' ? 'cm' : 'inch'}</span>
      <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
        {unit === 'CM' ? '→ inch' : '→ cm'}
      </span>
    </button>
  )
}

// Hook per consumir la unitat actual
export function useUnit() {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const [unit, setUnit] = useState('CM')

  useEffect(() => {
    fetch(`${API}/api/v1/tenant-config/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => setUnit(d.unitat_mesura || 'CM'))
      .catch(() => {})

    const handler = (e) => setUnit(e.detail.unit)
    window.addEventListener('unit-changed', handler)
    return () => window.removeEventListener('unit-changed', handler)
  }, [token])

  const format = (val_cm) => {
    if (val_cm == null) return '—'
    if (unit === 'INCH') return `${(val_cm * 0.393701).toFixed(2)}"` 
    return `${val_cm}cm`
  }

  return { unit, format }
}
