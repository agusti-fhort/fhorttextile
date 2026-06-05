import { useState, useEffect, useCallback } from 'react'
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
  // Multipart: NOMÉS Authorization (sense Content-Type) perquè el browser posi el boundary.
  const uploadHeaders = { Authorization: `Bearer ${token}` }

  const [sheet, setSheet] = useState(null)
  const [model, setModel] = useState(null)
  const [lockState, setLockState] = useState('loading') // 'loading' | 'owned' | 'conflict' | 'error'
  const [conflict, setConflict] = useState(null)

  // Panell d'assets inline: tots els fitxers del model (sense filtre de tipus).
  const [fitxers, setFitxers] = useState([])
  const [uploading, setUploading] = useState(false)

  const loadFitxers = useCallback(() => {
    return fetch(`${API}/api/v1/model-fitxers/?model=${id}&ordering=-data_pujada`, { headers: authHeaders })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (d) setFitxers(d.results || d || []) })
      .catch(() => {})
  // authHeaders es recrea cada render però depèn només de id/token estables aquí.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

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

    // Assets del model.
    loadFitxers()

    // Cleanup: alliberar el lock en sortir (fire-and-forget; keepalive perquè surti
    // encara que el navegador estigui descarregant la pàgina).
    return () => {
      cancelled = true
      fetch(`${API}/api/v1/models/${id}/tech-sheet/unlock/`, {
        method: 'POST', headers: authHeaders, keepalive: true,
      }).catch(() => {})
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // Pujada de fitxer (replicant handleUpload de ModelSheet). tipus per defecte 'ALTRES'
  // (el backend ja l'assumeix si no s'envia). Refresca la llista en acabar.
  const handleUpload = async (file) => {
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('fitxer', file)
    fd.append('nom', file.name)
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/upload-fitxer/`, {
        method: 'POST', headers: uploadHeaders, body: fd,
      })
      if (r.ok) await loadFitxers()
    } finally {
      setUploading(false)
    }
  }

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
        {sheet?.estat === 'tancat' && (
          <span style={{ fontSize: 11, color: 'var(--text-muted, #999)' }}>
            <i className="ti ti-lock" style={{ fontSize: 11, marginRight: 4 }} />Fitxa tancada
          </span>
        )}
        <span style={{
          marginLeft: 'auto', fontSize: 11, fontWeight: 500, padding: '3px 10px',
          borderRadius: 10, background: badge.bg, color: badge.fg, whiteSpace: 'nowrap',
        }}>
          {badge.text}
        </span>
      </header>

      <main style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* Cos central — placeholder de l'editor (en construcció). */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center', color: 'var(--text-muted, #999)' }}>
            <i className="ti ti-file-text" style={{ fontSize: 40, opacity: 0.5 }} />
            <p style={{ marginTop: 12, fontSize: 15 }}>Editor de fitxa tècnica — en construcció</p>
          </div>
        </div>

        {/* Panell d'assets inline — tots els fitxers del model + pujada. */}
        <aside style={{
          width: 320, flexShrink: 0, borderLeft: '0.5px solid var(--gray-l)',
          background: 'var(--white)', display: 'flex', flexDirection: 'column', minHeight: 0,
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '0.7rem 1rem', borderBottom: '0.5px solid var(--gray-l)',
          }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)' }}>
              <i className="ti ti-paperclip" style={{ fontSize: 13, marginRight: 6 }} />
              Assets del model
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-muted, #999)' }}>{fitxers.length}</span>
          </div>

          <label style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            margin: '0.8rem 1rem', padding: '8px', fontSize: 12, fontWeight: 500,
            borderRadius: 6, border: '0.5px dashed var(--gold)', color: 'var(--gold)',
            cursor: uploading ? 'default' : 'pointer',
            background: uploading ? 'var(--gray-l)' : 'transparent',
          }}>
            <i className="ti ti-upload" style={{ fontSize: 13 }} />
            {uploading ? 'Pujant…' : 'Pujar fitxer'}
            <input type="file" hidden disabled={uploading}
              onChange={e => { const f = e.target.files[0]; e.target.value = ''; handleUpload(f) }} />
          </label>

          <div style={{ flex: 1, overflowY: 'auto', padding: '0 1rem 1rem' }}>
            {fitxers.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--text-muted, #999)', textAlign: 'center', marginTop: 8 }}>
                Cap fitxer encara.
              </p>
            ) : (
              fitxers.map(f => (
                <div key={f.id} style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '7px 0',
                  borderBottom: '0.5px solid var(--gray-l)',
                }}>
                  <i className="ti ti-file" style={{ fontSize: 14, color: 'var(--text-muted, #999)', flexShrink: 0 }} />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{
                      fontSize: 12, color: 'var(--text-main)', whiteSpace: 'nowrap',
                      overflow: 'hidden', textOverflow: 'ellipsis',
                    }} title={f.nom_fitxer}>
                      {f.nom_fitxer}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted, #999)' }}>
                      {f.tipus}{f.versio ? ` · v${f.versio}` : ''}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>
      </main>
    </div>
  )
}
