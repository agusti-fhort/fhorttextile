
import { useState, useEffect } from "react"
import { EstatBadge } from "./EstatBadge"

const API = import.meta.env.VITE_API_URL || ""

const ESTAT_ORDER = ["Pendent", "En curs", "Bloquejada", "Feta"]

const STAT_STYLES = {
  "Pendent":   { header: '#1a1a2a', border: 'var(--border)', accent: '#4a4a8a' },
  "En curs":   { header: '#1a2a3a', border: '#2a4a6a', accent: '#4a7aaa' },
  "Bloquejada":{ header: '#2a1a1a', border: '#4a2020', accent: '#8a3a3a' },
  "Feta":      { header: '#1a2a1a', border: '#2a4a2a', accent: '#4a8a4a' },
}

export function KanbanTasquesModel({ modelId, token, onGenerarTasques }) {
  const [tasques, setTasques] = useState([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(null)

  const fetchTasques = () => {
    setLoading(true)
    fetch(`${API}/api/v1/model-tasques/?model=${modelId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => {
        setTasques(Array.isArray(d) ? d : (d.results || []))
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  useEffect(() => { if (modelId) fetchTasques() }, [modelId])

  const updateEstat = async (id, nouEstat) => {
    setUpdating(id)
    try {
      await fetch(`${API}/api/v1/model-tasques/${id}/`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ estat: nouEstat }),
      })
      fetchTasques()
    } catch (e) {
      console.error(e)
    }
    setUpdating(null)
  }

  const processarGate = async (id) => {
    setUpdating(id)
    try {
      const r = await fetch(`${API}/api/v1/model-tasques/${id}/processar-gate/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ resultat: 'OK' }),
      })
      const d = await r.json()
      if (d.error) alert(d.error)
      fetchTasques()
    } catch (e) {
      console.error(e)
    }
    setUpdating(null)
  }

  if (loading) return <div style={{ color: 'var(--text-main)', fontSize: 12, padding: 16 }}>Carregant tasques...</div>

  const byEstat = ESTAT_ORDER.reduce((acc, e) => {
    acc[e] = tasques.filter(t => t.estat === e)
    return acc
  }, {})

  // Agrupa per fase per mostrar separadors
  const getFaseColor = (fase) => {
    const map = {
      'Disseny': '#2a4a2a', 'Tècnic': '#2a2a4a', 'Prototip': '#4a2a1a',
      'Mostres': '#4a4a1a', 'Preproducció': '#1a4a4a', 'Producció': '#3a1a4a',
    }
    return map[fase] || 'var(--border)'
  }

  if (tasques.length === 0) {
    return (
      <div style={{ color: 'var(--text-main)', fontSize: 12, padding: '16px 0' }}>
        <p>No hi ha tasques generades.</p>
        {onGenerarTasques && (
          <button onClick={onGenerarTasques} style={btnStyle}>
            ⚡ Generar tasques des dels serveis
          </button>
        )}
      </div>
    )
  }

  return (
    <div style={{ overflowX: 'auto', paddingBottom: 8 }}>
      <div style={{ display: 'flex', gap: 12, minWidth: 600, alignItems: 'flex-start' }}>
        {ESTAT_ORDER.map(estat => {
          const col = byEstat[estat] || []
          const st = STAT_STYLES[estat]
          return (
            <div key={estat} style={{
              flex: '0 0 200px',
              background: 'var(--bg-card)',
              border: `1px solid var(--border)`,
              borderRadius: 6,
              overflow: 'hidden',
            }}>
              <div style={{
                padding: '6px 10px',
                background: st.header,
                borderBottom: `1px solid ${st.border}`,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <span style={{
                  fontSize: 11,
                  fontFamily: 'IBM Plex Mono, monospace',
                  color: st.accent,
                  fontWeight: 600,
                }}>
                  {estat.toUpperCase()}
                </span>
                <span style={{
                  fontSize: 10,
                  background: st.border,
                  color: st.accent,
                  borderRadius: 10,
                  padding: '1px 6px',
                }}>
                  {col.length}
                </span>
              </div>
              <div style={{ padding: '6px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {col.map(t => (
                  <div key={t.id} style={{
                    background: 'var(--bg-card)',
                    border: `1px solid ${t.gate ? '#3a3a1a' : '#1a1a1a'}`,
                    borderRadius: 4,
                    padding: '6px 8px',
                    opacity: updating === t.id ? 0.5 : 1,
                  }}>
                    {/* Fase tag */}
                    <div style={{ marginBottom: 4 }}>
                      <span style={{
                        fontSize: 9,
                        fontFamily: 'IBM Plex Mono, monospace',
                        color: 'var(--text-muted)',
                        background: getFaseColor(t.fase),
                        padding: '1px 5px',
                        borderRadius: 2,
                      }}>
                        {t.fase}
                      </span>
                      {t.gate && (
                        <span style={{
                          marginLeft: 4, fontSize: 9,
                          color: 'var(--gold)', background: 'var(--gold-pale)',
                          padding: '1px 5px', borderRadius: 2,
                          fontFamily: 'IBM Plex Mono, monospace',
                        }}>
                          GATE
                        </span>
                      )}
                    </div>

                    {/* Nom tasca */}
                    <div style={{
                      fontSize: 11,
                      color: 'var(--text-muted)',
                      fontFamily: 'IBM Plex Mono, monospace',
                      marginBottom: 4,
                      lineHeight: 1.3,
                    }}>
                      {t.nom_tasca}
                    </div>

                    {/* Slots */}
                    {t.slots_base > 0 && (
                      <div style={{ fontSize: 10, color: 'var(--text-main)', marginBottom: 6 }}>
                        {t.slots_reals > 0
                          ? `${t.slots_reals}/${t.slots_base} slots`
                          : `${t.slots_base} slots prev.`
                        }
                      </div>
                    )}

                    {/* Accions */}
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {t.estat === 'Pendent' && (
                        <button
                          onClick={() => updateEstat(t.id, 'En curs')}
                          style={{ ...smallBtn, color: '#4a7aaa', borderColor: '#2a3a5a' }}
                        >
                          ▶ Iniciar
                        </button>
                      )}
                      {t.estat === 'En curs' && !t.gate && (
                        <button
                          onClick={() => updateEstat(t.id, 'Feta')}
                          style={{ ...smallBtn, color: '#4a9a4a', borderColor: '#2a4a2a' }}
                        >
                          ✓ Fer
                        </button>
                      )}
                      {t.estat === 'En curs' && t.gate && (
                        <button
                          onClick={() => processarGate(t.id)}
                          style={{ ...smallBtn, color: '#c27a2a', borderColor: '#4a3010' }}
                        >
                          ⊙ Gate OK
                        </button>
                      )}
                      {t.estat === 'Feta' && (
                        <button
                          onClick={() => updateEstat(t.id, 'En curs')}
                          style={{ ...smallBtn, color: 'var(--text-muted)', borderColor: 'var(--border)' }}
                        >
                          ↩ Reobrir
                        </button>
                      )}
                    </div>
                  </div>
                ))}
                {col.length === 0 && (
                  <div style={{ color: 'var(--text-muted)', fontSize: 11, padding: '8px 4px', textAlign: 'center' }}>
                    —
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const btnStyle = {
  padding: '6px 14px',
  background: 'var(--bg-muted)',
  color: '#4a7aaa',
  border: '1px solid var(--border)',
  borderRadius: 4,
  fontSize: 11,
  fontFamily: 'IBM Plex Mono, monospace',
  cursor: 'pointer',
}

const smallBtn = {
  padding: '2px 8px',
  background: 'transparent',
  border: '1px solid var(--border)',
  borderRadius: 3,
  fontSize: 10,
  fontFamily: 'IBM Plex Mono, monospace',
  cursor: 'pointer',
  color: 'var(--text-muted)',
}
