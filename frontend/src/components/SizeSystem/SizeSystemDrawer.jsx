import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

export default function SizeSystemDrawer({ sizeSystem, onClose, onDeleted, onTargetsSaved }) {
  const { t, i18n } = useTranslation()
  const [definitions, setDefinitions] = useState([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState(null)
  const [draft, setDraft] = useState({})
  // Sprint TARGETS-EDITABLES (2026-07-26) — targets aplicables del sistema (M2M editable).
  const [allTargets, setAllTargets] = useState([])
  const [selectedCodis, setSelectedCodis] = useState([])
  const [savingTargets, setSavingTargets] = useState(false)
  const [targetsMsg, setTargetsMsg] = useState(null)

  const authHeaders = () => {
    const token = localStorage.getItem('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  // Nom del target en l'idioma actiu (fallback a l'anglès).
  const targetName = (tg) => (
    i18n.language?.startsWith('ca') ? (tg.nom_cat || tg.nom_en)
      : i18n.language?.startsWith('es') ? (tg.nom_es || tg.nom_en)
        : tg.nom_en
  )

  useEffect(() => {
    if (!sizeSystem) return
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

  // Carrega el catàleg de targets i precarrega els ja assignats. La precàrrega ve del registre
  // AUTORITATIU del sistema (GET /size-systems/{id}/), no del prop niat (pot no portar
  // target_codis) — així «desar» mai buida targets per una precàrrega incompleta.
  useEffect(() => {
    if (!sizeSystem) return
    setTargetsMsg(null)
    setSelectedCodis(sizeSystem.target_codis || [])
    fetch('/api/v1/targets/', { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setAllTargets(d.results || d || []))
      .catch(() => setAllTargets([]))
    fetch(`/api/v1/size-systems/${sizeSystem.id}/`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => { if (Array.isArray(d?.target_codis)) setSelectedCodis(d.target_codis) })
      .catch(() => { /* fallback al prop ja aplicat sobre */ })
  }, [sizeSystem?.id])

  const toggleTarget = (codi) => {
    setTargetsMsg(null)
    setSelectedCodis(prev => (
      prev.includes(codi) ? prev.filter(c => c !== codi) : [...prev, codi]
    ))
  }

  const handleSaveTargets = async () => {
    setSavingTargets(true)
    setTargetsMsg(null)
    try {
      const res = await fetch(`/api/v1/size-systems/${sizeSystem.id}/`, {
        method: 'PATCH',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_codis: selectedCodis }),
      })
      if (res.ok) {
        const updated = await res.json()
        setSelectedCodis(updated.target_codis || [])
        setTargetsMsg({ ok: true, text: t('size_system.targets_saved') })
        if (onTargetsSaved) onTargetsSaved(updated)
      } else {
        setTargetsMsg({ ok: false, text: t('size_system.err_save_targets') })
      }
    } catch {
      setTargetsMsg({ ok: false, text: t('size_system.err_save_targets') })
    } finally {
      setSavingTargets(false)
    }
  }

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
    if (!confirm(t('size_system.confirm_delete_size'))) return
    const res = await fetch(`/api/v1/size-definitions/${defId}/`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (res.ok) {
      setDefinitions(prev => prev.filter(d => d.id !== defId))
    }
  }

  const handleDeleteSystem = async () => {
    const name = sizeSystem.nom || sizeSystem.codi
    if (!confirm(t('size_system.confirm_delete_system', { name }))) return
    const res = await fetch(`/api/v1/size-systems/${sizeSystem.id}/`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (res.ok) {
      const deletedId = sizeSystem.id
      onClose()
      if (onDeleted) onDeleted(deletedId)
    } else {
      let msg = t('size_system.err_delete_system')
      try {
        const d = await res.json()
        msg = d.detail || d.error || msg
      } catch { /* si això falla, el drawer no ha de petar */ }
      alert(msg)
    }
  }

  const handleAdd = async () => {
    // `ordre` és ÚNIC per run des de C4 (pom/0067), i els forats a `ordre` són LEGÍTIMS
    // (grading_utils.py:374). Comptar files (`length + 1`) dona un número que ja existeix
    // en qualsevol run amb forat — p. ex. 1·2·4 → proposaria 4, que ja hi és. El següent
    // lliure surt del MÀXIM, no del recompte.
    const seguent = definitions.reduce((m, d) => Math.max(m, Number(d.ordre) || 0), 0) + 1
    const newDef = {
      size_system: sizeSystem.id,
      etiqueta: 'NOVA',
      ordre: seguent,
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
      return
    }
    // Sense aquest `else` el botó no feia res i no deia res: el 400 de la unicitat (o el de
    // l'etiqueta 'NOVA' repetida) es perdia sencer. Mateixa manera d'avisar que la resta del
    // drawer.
    let msg = t('size_system.add_error')
    try {
      const d = await res.json()
      msg = d.detail || d.error || d.non_field_errors?.[0] || d.ordre?.[0] || d.etiqueta?.[0] || msg
    } catch { /* si això falla, el drawer no ha de petar */ }
    alert(msg)
  }

  if (!sizeSystem) return null

  const COLS = [
    { key: 'etiqueta',       labelKey: 'size_system.col.size',    width: 60 },
    { key: 'body_height_cm', labelKey: 'size_system.col.height',  width: 70 },
    { key: 'body_bust_cm',   labelKey: 'size_system.col.bust',    width: 60 },
    { key: 'body_waist_cm',  labelKey: 'size_system.col.waist',   width: 70 },
    { key: 'body_hip_cm',    labelKey: 'size_system.col.hip',     width: 60 },
    { key: 'age_months_min', labelKey: 'size_system.col.age_min', width: 70 },
    { key: 'age_months_max', labelKey: 'size_system.col.age_max', width: 70 },
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
        background: 'var(--white)', zIndex: 201,
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
            <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>
              {sizeSystem.nom || sizeSystem.codi}
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: '#888' }}>
              {t('size_system.code')}: {sizeSystem.codi} · {t('size_system.sizes_defined', { count: definitions.length })}
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
          {/* Sprint TARGETS-EDITABLES — targets aplicables (M2M). Un sistema pot servir-ne
              diversos sense clonar-se; buit NO vol dir universal (el wizard només mostra
              escales amb el target de la peça assignat). */}
          <div style={{ marginBottom: '1.25rem' }}>
            <p style={{
              margin: '0 0 0.4rem', fontSize: '0.7rem', fontWeight: 600,
              color: '#666', textTransform: 'uppercase',
            }}>
              {t('size_system.targets_label')}
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
              {allTargets.map(tg => {
                const on = selectedCodis.includes(tg.codi)
                return (
                  <button
                    key={tg.codi}
                    type="button"
                    onClick={() => toggleTarget(tg.codi)}
                    style={{
                      padding: '0.25rem 0.6rem', borderRadius: 999,
                      border: `1px solid ${on ? 'var(--gold)' : '#ddd'}`,
                      background: on ? 'var(--gold)' : 'var(--white)',
                      color: on ? 'var(--white)' : '#666',
                      cursor: 'pointer', fontSize: '0.75rem',
                      fontWeight: on ? 600 : 400,
                    }}
                  >
                    {targetName(tg)}
                  </button>
                )
              })}
              {allTargets.length === 0 && (
                <span style={{ color: '#aaa', fontSize: '0.8rem' }}>{t('common.loading')}</span>
              )}
            </div>
            <p style={{ margin: '0.45rem 0 0', fontSize: '0.7rem', color: '#999' }}>
              {t('size_system.targets_hint')}
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginTop: '0.5rem' }}>
              <button
                type="button"
                onClick={handleSaveTargets}
                disabled={savingTargets}
                style={{
                  padding: '0.35rem 0.8rem', border: '1px solid var(--gold)',
                  borderRadius: 6, background: 'var(--gold)', color: 'var(--white)',
                  cursor: savingTargets ? 'default' : 'pointer',
                  opacity: savingTargets ? 0.6 : 1,
                  fontSize: '0.8rem', fontWeight: 500,
                }}
              >
                {savingTargets ? t('common.loading') : t('size_system.save_targets')}
              </button>
              {targetsMsg && (
                <span style={{
                  fontSize: '0.75rem',
                  color: targetsMsg.ok ? 'var(--gold)' : '#C0392B',
                }}>
                  {targetsMsg.text}
                </span>
              )}
            </div>
          </div>

          {loading ? (
            <p style={{ color: '#888', fontSize: '0.85rem' }}>{t('common.loading')}</p>
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
                      {t(c.labelKey)}
                    </th>
                  ))}
                  <th style={{ width: 60 }} />
                </tr>
              </thead>
              <tbody>
                {definitions.map((def, i) => (
                  <tr key={def.id} style={{ background: i % 2 === 0 ? 'var(--white)' : '#fafafa' }}>
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
                              width: '100%', border: '1px solid var(--gold)',
                              borderRadius: 4, padding: '0.15rem 0.3rem',
                              fontSize: '0.78rem', 
                              boxSizing: 'border-box',
                            }}
                          />
                        ) : (
                          <span style={{
                            fontFamily: c.key === 'etiqueta' ? 'IBM Plex Mono' : 'inherit',
                            fontWeight: c.key === 'etiqueta' ? 600 : 400,
                            color: c.key === 'etiqueta' ? 'var(--gold)' : '#444',
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
                              background: 'var(--gold)', color: 'var(--white)', border: 'none',
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
                            {t('app.edit')}
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
                      {t('size_system.empty')}
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
              padding: '0.4rem 0.85rem', border: '1px solid var(--gold)',
              borderRadius: 6, background: 'var(--white)', color: 'var(--gold)',
              cursor: 'pointer', fontSize: '0.82rem', fontWeight: 500,
            }}>
            {t('size_system.add_size')}
          </button>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={handleDeleteSystem}
              style={{
                padding: '0.4rem 0.85rem', border: '1px solid #C0392B',
                borderRadius: 6, background: 'var(--white)', color: '#C0392B',
                cursor: 'pointer', fontSize: '0.82rem',
              }}>
              {t('size_system.delete_system')}
            </button>
            <button onClick={onClose}
              style={{
                padding: '0.4rem 0.85rem', border: '1px solid #ddd',
                borderRadius: 6, background: 'var(--white)', color: '#666',
                cursor: 'pointer', fontSize: '0.82rem',
              }}>
              {t('app.close')}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
