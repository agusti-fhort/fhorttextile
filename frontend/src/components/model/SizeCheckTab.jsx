import { useState, useEffect, useCallback } from 'react'
import { sizeChecks } from '../../api/endpoints'
import SizeCheckCell from './SizeCheckCell'

const MONO = 'IBM Plex Mono, monospace'
const fmtDate = (v) => v ? new Date(v).toLocaleString('ca-ES', { dateStyle: 'medium', timeStyle: 'short' }) : '—'

const th = { padding: '6px 8px', borderBottom: '1px solid var(--border)', fontFamily: MONO, fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textAlign: 'left', whiteSpace: 'nowrap' }
const tdRO = { padding: '5px 8px', borderBottom: '0.5px solid var(--border)', fontFamily: MONO, fontSize: 12 }

const btn = (variant) => ({
  fontFamily: MONO, fontSize: 12, padding: '6px 14px', borderRadius: 4, cursor: 'pointer',
  border: '0.5px solid var(--gray-l)',
  background: variant === 'ok' ? 'var(--ok)' : variant === 'err' ? 'var(--err)' : 'var(--gold)',
  color: '#fff', fontWeight: 500,
})

// SC-1 — Tab Size Check: validació del proto a talla base, abans del fitting.
// 1 columna (talla base) editable amb tolerància; el tècnic anota valor_real per POM,
// accepta/descarta cada línia i resol el check (Acceptat/Descartat + missatge fabricant).
export default function SizeCheckTab({ model, onFeedback }) {
  const [check, setCheck] = useState(null)        // check viu (Pendent) amb lines
  const [history, setHistory] = useState([])      // checks resolts (summary)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [missatge, setMissatge] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    sizeChecks.list({ model: model.id, ordering: '-created_at', page_size: 100 })
      .then(async r => {
        const rows = r.data?.results ?? r.data ?? []
        setHistory(rows.filter(c => c.estat !== 'Pendent'))
        const live = rows.find(c => c.estat === 'Pendent')
        if (live) {
          const full = await sizeChecks.get(live.id)
          setCheck(full.data)
          setMissatge(full.data.missatge_fabricant || '')
        } else {
          setCheck(null)
        }
      })
      .catch(() => { setCheck(null); setHistory([]) })
      .finally(() => setLoading(false))
  }, [model.id])

  useEffect(() => { load() }, [load])

  const handleOpen = () => {
    setBusy(true)
    sizeChecks.open(model.id)
      .then(r => { setCheck(r.data); setMissatge(r.data.missatge_fabricant || '') })
      .catch(e => onFeedback?.({ type: 'err', text: e.response?.data?.error || 'No s\'ha pogut obrir el size check' }))
      .finally(() => setBusy(false))
  }

  const handleResolve = (estat) => {
    if (!check) return
    setBusy(true)
    sizeChecks.resolve(check.id, estat, missatge)
      .then(r => {
        onFeedback?.({ type: 'ok', text: `Check ${estat.toLowerCase()} · ${r.data.written} mesura(es) escrita(es)` })
        load()
      })
      .catch(e => onFeedback?.({ type: 'err', text: e.response?.data?.error || 'No s\'ha pogut resoldre' }))
      .finally(() => setBusy(false))
  }

  if (loading) return <div style={{ fontFamily: MONO, fontSize: 12, color: 'var(--text-muted)' }}>Carregant…</div>

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 14 }}>
        <h2 style={{ fontSize: 15, fontWeight: 500, margin: 0, fontFamily: MONO }}>
          Size Check · talla base {model.base_size_label ? `(${model.base_size_label})` : ''}
        </h2>
        {!check && <button style={btn('gold')} disabled={busy} onClick={handleOpen}>Obrir size check</button>}
      </div>

      {!check && (
        <p style={{ fontFamily: MONO, fontSize: 12, color: 'var(--text-muted)' }}>
          Cap check viu. Obre'n un per validar el proto contra les mesures base vigents.
        </p>
      )}

      {check && (
        <>
          <table style={{ borderCollapse: 'collapse', width: '100%', marginBottom: 16 }}>
            <thead>
              <tr>
                <th style={th}>POM</th>
                <th style={th}>Mesura</th>
                <th style={{ ...th, textAlign: 'right' }}>Teòric</th>
                <th style={{ ...th, textAlign: 'right' }}>Real (proto)</th>
                <th style={{ ...th, textAlign: 'center' }}>Accepta</th>
                <th style={th}>Nota</th>
              </tr>
            </thead>
            <tbody>
              {(check.lines || []).map(line => (
                <tr key={line.id}>
                  <td style={{ ...tdRO, fontWeight: line.is_key ? 700 : 400 }}>{line.codi}</td>
                  <td style={{ ...tdRO, color: 'var(--text-muted)' }}>{line.nom}</td>
                  <SizeCheckCell line={line} disabled={false} />
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 520 }}>
            <label style={{ fontFamily: MONO, fontSize: 11, color: 'var(--text-muted)' }}>Missatge al fabricant</label>
            <textarea
              value={missatge} onChange={e => setMissatge(e.target.value)} rows={3}
              placeholder="Observacions per al fabricant…"
              style={{ fontFamily: MONO, fontSize: 12, padding: 8, borderRadius: 4, border: '1px solid var(--border)', resize: 'vertical' }}
            />
            <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
              <button style={btn('ok')} disabled={busy} onClick={() => handleResolve('Acceptat')}>Acceptar</button>
              <button style={btn('err')} disabled={busy} onClick={() => handleResolve('Descartat')}>Descartar</button>
            </div>
          </div>
        </>
      )}

      {history.length > 0 && (
        <div style={{ marginTop: 28 }}>
          <h3 style={{ fontSize: 13, fontWeight: 500, fontFamily: MONO, color: 'var(--text-muted)', margin: '0 0 8px' }}>Històric</h3>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                <th style={th}>Data</th>
                <th style={th}>Estat</th>
                <th style={th}>Resolt per</th>
                <th style={th}>Missatge</th>
              </tr>
            </thead>
            <tbody>
              {history.map(h => (
                <tr key={h.id}>
                  <td style={tdRO}>{fmtDate(h.resolt_at || h.created_at)}</td>
                  <td style={{ ...tdRO, fontWeight: 600, color: h.estat === 'Acceptat' ? 'var(--ok)' : 'var(--err)' }}>{h.estat}</td>
                  <td style={tdRO}>{h.resolt_per_nom || '—'}</td>
                  <td style={{ ...tdRO, color: 'var(--text-muted)' }}>{h.missatge_fabricant || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
