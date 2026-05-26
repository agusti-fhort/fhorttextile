
import { useState, useEffect } from "react"

const API = import.meta.env.VITE_API_URL || ""

export function TaulaMesures({ sfId, token, onUpdate }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editingCell, setEditingCell] = useState(null)
  const [editValue, setEditValue] = useState("")

  useEffect(() => {
    if (!sfId) return
    fetch(`${API}/api/v1/size-fittings/${sfId}/taula-mesures/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(`Error ${e}`); setLoading(false) })
  }, [sfId, token])

  if (loading) return <div style={styles.msg}>Carregant mesures...</div>
  if (error) return <div style={{ ...styles.msg, color: '#cc4444' }}>{error}</div>
  if (!data || !data.poms?.length) return (
    <div style={styles.msg}>
      No hi ha mesures. Entra els valors de la talla base per als POMs del model.
    </div>
  )

  const { poms, size_run, cells, base_size } = data

  const handleCellClick = (pomId, talla, currentVal) => {
    setEditingCell(`${pomId}_${talla}`)
    setEditValue(currentVal ?? "")
  }

  const handleCellSave = async (pomId, talla) => {
    const val = parseFloat(editValue)
    if (isNaN(val)) { setEditingCell(null); return }

    try {
      // Per la talla base: actualitza BaseMeasurement
      // Per altres talles: actualitza GradedSpec via PATCH
      const endpoint = talla === base_size
        ? `${API}/api/v1/base-measurements/`
        : null  // Implementar si cal editar GradedSpec directament

      if (onUpdate) onUpdate(pomId, talla, val)
    } catch (e) {
      console.error(e)
    }
    setEditingCell(null)
  }

  return (
    <div style={{ overflowX: 'auto', fontSize: 12, fontFamily: 'IBM Plex Mono, monospace' }}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={{ ...styles.th, width: 40 }}>#</th>
            <th style={{ ...styles.th, minWidth: 160 }}>POM</th>
            <th style={{ ...styles.th, minWidth: 60 }}>Codi</th>
            {size_run.map(t => (
              <th
                key={t}
                style={{
                  ...styles.th,
                  minWidth: 64,
                  background: t === base_size ? '#1a2a1a' : '#111',
                  color: t === base_size ? '#4a9a4a' : '#666',
                }}
              >
                {t}
                {t === base_size && <span title="Talla base"> ●</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {poms.map((pom, rowIdx) => (
            <tr key={pom.id} style={{ background: rowIdx % 2 === 0 ? '#111' : '#0e0e0e' }}>
              <td style={{ ...styles.td, color: 'var(--text-main)', textAlign: 'right' }}>
                {pom.display_order || rowIdx + 1}
              </td>
              <td style={{ ...styles.td, color: pom.is_key_measure ? '#c27a2a' : '#888' }}>
                {pom.is_key_measure && <span title="Key measure" style={{ marginRight: 4 }}>★</span>}
                {pom.nom_cat || pom.nom_en}
              </td>
              <td style={{ ...styles.td, color: 'var(--text-muted)' }}>{pom.codi}</td>
              {size_run.map(talla => {
                const cellKey = `${pom.id}_${talla}`
                const cellData = cells[pom.id]?.[talla]
                const val = cellData?.value
                const isBase = talla === base_size
                const isEditing = editingCell === cellKey

                return (
                  <td
                    key={talla}
                    style={{
                      ...styles.td,
                      textAlign: 'right',
                      background: isBase ? '#0f1a0f' : 'transparent',
                      color: val != null ? (isBase ? '#5aaa5a' : '#888') : '#222',
                      cursor: 'pointer',
                      padding: '4px 6px',
                    }}
                    onClick={() => handleCellClick(pom.id, talla, val)}
                  >
                    {isEditing ? (
                      <input
                        autoFocus
                        type="number"
                        step="0.1"
                        value={editValue}
                        onChange={e => setEditValue(e.target.value)}
                        onBlur={() => handleCellSave(pom.id, talla)}
                        onKeyDown={e => {
                          if (e.key === 'Enter') handleCellSave(pom.id, talla)
                          if (e.key === 'Escape') setEditingCell(null)
                        }}
                        style={{
                          width: 52, background: 'var(--bg-muted)', color: '#5aaa5a',
                          border: '1px solid #2a4a2a', borderRadius: 2,
                          fontFamily: 'IBM Plex Mono, monospace', fontSize: 11,
                          textAlign: 'right', padding: '1px 3px',
                        }}
                      />
                    ) : (
                      val != null ? val.toFixed(1) : '—'
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ padding: '8px 0', color: 'var(--text-main)', fontSize: 10 }}>
        ● talla base &nbsp;·&nbsp; ★ key measure &nbsp;·&nbsp; clic per editar
      </div>
    </div>
  )
}

const styles = {
  msg: { color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, padding: '16px 0' },
  table: { borderCollapse: 'collapse', width: '100%', minWidth: 500 },
  th: {
    padding: '6px 8px', textAlign: 'left', fontSize: 11,
    fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600,
    color: 'var(--text-muted)', borderBottom: '1px solid var(--border)',
    background: 'var(--bg-card)', whiteSpace: 'nowrap',
  },
  td: {
    padding: '3px 8px', fontSize: 11, color: 'var(--text-muted)',
    borderBottom: '1px solid #1a1a1a',
    fontFamily: 'IBM Plex Mono, monospace',
  },
}
