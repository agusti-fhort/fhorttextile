import { useState, useEffect } from 'react'

export default function SizeSystemDrawer({ sizeSystem, onClose, onDeleted }) {
  const [definitions, setDefinitions] = useState([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState(null)
  const [draft, setDraft] = useState({})

  const authHeaders = () => {
    const token = localStorage.getItem('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  useEffect(() => {
    if (!sizeSystem) return
    console.log('SizeSystem prop:', sizeSystem)
    console.log('Fetching definitions for id:', sizeSystem?.id)
    setLoading(true)
    fetch(`/api/v1/size-definitions/?size_system=${sizeSystem.id}&page_size=50`, {
      headers: authHeaders(),
    })
      .then(r => r.json())
      .then(d => {
        const items = d.results || d || []
        items.sort((a, b) => (a.ordre ?? 0) - (b.ordre ?? 0))
        setDefinitions(items)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [sizeSystem?.id])

  const handleEdit = (def) => {
    setEditingId(def.id)
    setDraft({ ...def })
  }

  const handleSave = async () => {
    const res = await fetch(`/api/v1/size-definitions/${editingId}/`, {
      method: 'PATCH',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(draft),
    })
    if (res.ok) {
      const updated = await res.json()
      setDefinitions(prev => prev.map(d => (d.id === editingId ? updated : d)))
      setEditingId(null)
    }
  }

  const handleDelete = async (defId) => {
    if (!confirm('Esborrar aquesta talla?')) return
    const res = await fetch(`/api/v1/size-definitions/${defId}/`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (res.ok) {
      setDefinitions(prev => prev.filter(d => d.id !== defId))
    }
  }

  const handleDeleteSystem = async () => {
    const nom = sizeSystem.nom || sizeSystem.codi
    if (!confirm(`Esborrar el sistema de talles ${nom}? Aquesta acció és irreversible.`)) return
    const res = await fetch(`/api/v1/size-systems/${sizeSystem.id}/`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (res.ok) {
      const deletedId = sizeSystem.id
      onClose()
      if (onDeleted) onDeleted(deletedId)
    } else {
      let msg = 'No s\'ha pogut esborrar el sistema'
      try {
        const d = await res.json()
        msg = d.detail || d.error || msg
      } catch {}
      alert(msg)
    }
  }

  const handleAdd = async () => {
    const newDef = {
      size_system: sizeSystem.id,
      etiqueta: 'NOVA',
      ordre: definitions.length + 1,
    }
    const res = await fetch('/api/v1/size-definitions/', {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(newDef),
    })
    if (res.ok) {
      const created = await res.json()
      setDefinitions(prev => [...prev, created])
      setEditingId(created.id)
      setDraft({ ...created })
    }
  }

  if (!sizeSystem) return null

  const COLS = [
    { key: 'etiqueta',       label: 'Talla',    width: 60 },
    { key: 'body_height_cm', label: 'Alçada',   width: 70 },
    { key: 'body_bust_cm',   label: 'Pit',      width: 60 },
    { key: 'body_waist_cm',  label: 'Cintura',  width: 70 },
    { key: 'body_hip_cm',    label: 'Maluc',    width: 60 },
    { key: 'age_months_min', label: 'Edat min', width: 70 },
    { key: 'age_months_max', label: 'Edat max', width: 70 },
  ]

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)',
          zIndex: 200, transition: 'opacity 0.2s',
        }}
      />

      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0,
        width: 'min(680px, 90vw)',
        background: '#fff', zIndex: 201,
        boxShadow: '-4px 0 24px rgba(0,0,0,0.15)',
        display: 'flex', flexDirection: 'column',
        fontFamily: 'IBM Plex Sans, sans-serif',
      }}>
        <div style={{
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, fontFamily: 'IBM Plex Mono' }}>
              {sizeSystem.nom || sizeSystem.codi}
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: '#888' }}>
              Codi: {sizeSystem.codi} · {definitions.length} talles definides
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', fontSize: '1.5rem',
              cursor: 'pointer', color: '#888', lineHeight: 1, padding: '0 0.25rem',
            }}
          >
            ×
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '1.25rem 1.5rem' }}>
          {loading ? (
            <p style={{ color: '#888', fontSize: '0.85rem' }}>Carregant talles...</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ background: '#f8f9fa' }}>
                  {COLS.map(c => (
                    <th key={c.key} style={{
                      padding: '0.4rem 0.5rem', textAlign: 'left',
                      fontWeight: 600, color: '#666', fontSize: '0.7rem',
                      borderBottom: '1px solid #e5e7eb', textTransform: 'uppercase',
                      width: c.width,
                    }}>
                      {c.label}
                    </th>
                  ))}
                  <th style={{ width: 60 }} />
                </tr>
              </thead>
              <tbody>
                {definitions.map((def, i) => (
                  <tr key={def.id} style={{ background: i % 2 === 0 ? '#fff' : '#fafafa' }}>
                    {COLS.map(c => (
                      <td key={c.key} style={{
                        padding: '0.35rem 0.5rem',
                        borderBottom: '1px solid #f0f0f0',
                      }}>
                        {editingId === def.id ? (
                          <input
                            value={draft[c.key] ?? ''}
                            onChange={e => setDraft(d => ({ ...d, [c.key]: e.target.value }))}
                            style={{
                              width: '100%', border: '1px solid #c27a2a',
                              borderRadius: 4, padding: '0.15rem 0.3rem',
                              fontSize: '0.78rem', fontFamily: 'IBM Plex Mono',
                              boxSizing: 'border-box',
                            }}
                          />
                        ) : (
                          <span style={{
                            fontFamily: c.key === 'etiqueta' ? 'IBM Plex Mono' : 'inherit',
                            fontWeight: c.key === 'etiqueta' ? 600 : 400,
                            color: c.key === 'etiqueta' ? '#c27a2a' : '#444',
                          }}>
                            {def[c.key] != null ? def[c.key] : '—'}
                            {c.key.includes('cm') && def[c.key] != null ? ' cm' : ''}
                          </span>
                        )}
                      </td>
                    ))}
                    <td style={{
                      padding: '0.35rem 0.5rem', borderBottom: '1px solid #f0f0f0',
                      textAlign: 'right', whiteSpace: 'nowrap',
                    }}>
                      {editingId === def.id ? (
                        <>
                          <button onClick={handleSave}
                            style={{
                              fontSize: '0.7rem', padding: '0.15rem 0.4rem',
                              background: '#c27a2a', color: '#fff', border: 'none',
                              borderRadius: 3, cursor: 'pointer', marginRight: 4,
                            }}>
                            ✓
                          </button>
                          <button onClick={() => setEditingId(null)}
                            style={{
                              fontSize: '0.7rem', padding: '0.15rem 0.4rem',
                              background: '#eee', color: '#666', border: 'none',
                              borderRadius: 3, cursor: 'pointer',
                            }}>
                            ✗
                          </button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => handleEdit(def)}
                            style={{
                              fontSize: '0.7rem', padding: '0.15rem 0.4rem',
                              background: 'none', color: '#888', border: '1px solid #ddd',
                              borderRadius: 3, cursor: 'pointer', marginRight: 4,
                            }}>
                            Editar
                          </button>
                          <button onClick={() => handleDelete(def.id)}
                            style={{
                              fontSize: '0.7rem', padding: '0.15rem 0.4rem',
                              background: 'none', color: '#C0392B', border: '1px solid #FADBD8',
                              borderRadius: 3, cursor: 'pointer',
                            }}>
                            ×
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}

                {definitions.length === 0 && (
                  <tr>
                    <td colSpan={COLS.length + 1}
                      style={{
                        padding: '1rem', color: '#aaa',
                        textAlign: 'center', fontSize: '0.85rem',
                      }}>
                      Sense talles definides
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>

        <div style={{
          padding: '0.75rem 1.5rem',
          borderTop: '1px solid #e5e7eb',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <button onClick={handleAdd}
            style={{
              padding: '0.4rem 0.85rem', border: '1px solid #c27a2a',
              borderRadius: 6, background: '#fff', color: '#c27a2a',
              cursor: 'pointer', fontSize: '0.82rem', fontWeight: 500,
            }}>
            + Afegir talla
          </button>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={handleDeleteSystem}
              style={{
                padding: '0.4rem 0.85rem', border: '1px solid #C0392B',
                borderRadius: 6, background: '#fff', color: '#C0392B',
                cursor: 'pointer', fontSize: '0.82rem',
              }}>
              Esborrar sistema
            </button>
            <button onClick={onClose}
              style={{
                padding: '0.4rem 0.85rem', border: '1px solid #ddd',
                borderRadius: 6, background: '#fff', color: '#666',
                cursor: 'pointer', fontSize: '0.82rem',
              }}>
              Tancar
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
