import { useState } from "react"
import useAuthStore from "../store/auth"

const API = import.meta.env.VITE_API_URL || ""

// Minimal stub: loads the POM data on first hover and shows it as a
// native tooltip via title. Replace with a floating panel when needed.
export function HTMTooltip({ pomId, children }) {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const [info, setInfo] = useState(null)
  const [loaded, setLoaded] = useState(false)

  const load = () => {
    if (loaded || !pomId) return
    setLoaded(true)
    fetch(`${API}/api/v1/poms/${pomId}/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setInfo(d))
      .catch(() => {})
  }

  const title = info
    ? [info.codi_intern, info.nom_en, info.metode_mesura]
        .filter(Boolean).join(' · ')
    : 'Carregant POM...'

  return (
    <span
      onMouseEnter={load}
      title={info ? title : undefined}
      style={{ cursor: 'help' }}
    >
      {children}
    </span>
  )
}
