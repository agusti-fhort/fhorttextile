
import { useState, useEffect } from "react"
import useAuthStore from "../store/auth"
import { useUnit } from "./UnitToggle"

const API = import.meta.env.VITE_API_URL || ""

export function GradingHistoryPanel({ ruleSetId, onClose }) {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const { unit, format } = useUnit()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!ruleSetId) return
    fetch(`${API}/api/v1/grading-rule-sets/${ruleSetId}/historial/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => { setHistory(d.results || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [ruleSetId, token])

  return (
    <div style={{ fontFamily: 'IBM Plex Mono, monospace' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 14, paddingBottom: 10, borderBottom: '1px solid #e0d5c5',
      }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#1d1d1b' }}>
          Historial de canvis
        </div>
        {onClose && (
          <button onClick={onClose} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: '#868685', fontSize: 18,
          }}>×</button>
        )}
      </div>

      {loading ? (
        <div style={{ color: '#868685', fontSize: 12 }}>Carregant...</div>
      ) : history.length === 0 ? (
        <div style={{
          padding: '16px', border: '1px dashed #e0d5c5', borderRadius: 6,
          textAlign: 'center', color: '#868685', fontSize: 12,
        }}>
          Sense canvis registrats
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {history.map((h, i) => (
            <div key={i} style={{
              padding: '8px 10px', borderRadius: 5,
              background: '#fdf9f5', border: '1px solid #f0e8d8',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ fontWeight: 600, color: '#c27a2a', fontSize: 11 }}>
                  {h.pom_codi}
                </span>
                <span style={{ fontSize: 10, color: '#868685' }}>
                  {new Date(h.modificat_at).toLocaleDateString('ca-ES', {
                    day: '2-digit', month: '2-digit', year: '2-digit',
                    hour: '2-digit', minute: '2-digit',
                  })}
                </span>
              </div>
              <div style={{ fontSize: 11, color: '#1d1d1b' }}>
                <span style={{ color: '#868685' }}>+{format(h.valor_anterior)}</span>
                <span style={{ margin: '0 6px', color: '#c27a2a' }}>→</span>
                <span style={{ fontWeight: 500 }}>+{format(h.valor_nou)}</span>
                {h.nota && (
                  <span style={{ marginLeft: 8, color: '#868685', fontSize: 10 }}>
                    "{h.nota}"
                  </span>
                )}
              </div>
              <div style={{ fontSize: 10, color: '#868685', marginTop: 2 }}>
                {h.modificat_per}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
