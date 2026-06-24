import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { watchpoints } from '../../api/endpoints'

const fmtDate = (iso) => iso ? new Date(iso).toLocaleString('ca-ES', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''
const linkBtn = { background: 'none', border: 'none', cursor: 'pointer', fontSize: 'var(--fs-caption)', color: 'var(--gold)' }

// D-12 — Watchpoints: advertències de TEXT LLIURE que viatgen amb el model a través dels gates.
// Crear (mode treball) + veure/resoldre. Origen = la tasca on es crea (`taskId`). NO van a la fitxa
// tècnica; viuen amb el model perquè un altre tècnic entengui l'advertència.
export default function WatchpointsPanel({ modelId, taskId = null, editable = false }) {
  const { t } = useTranslation()
  const [items, setItems] = useState([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [showResolved, setShowResolved] = useState(false)

  const load = useCallback(() => {
    if (!modelId) return
    watchpoints.list({ model: modelId, ordering: '-created_at', page_size: 100 })
      .then(r => setItems(r.data?.results ?? r.data ?? [])).catch(() => {})
  }, [modelId])
  useEffect(() => { load() }, [load])

  const add = () => {
    const v = text.trim()
    if (!v || busy) return
    setBusy(true)
    watchpoints.create({ model: modelId, task: taskId || null, text: v })
      .then(() => { setText(''); load() }).finally(() => setBusy(false))
  }
  const resolve = (id) => { setBusy(true); watchpoints.resolve(id).then(load).finally(() => setBusy(false)) }
  const reopen = (id) => { setBusy(true); watchpoints.reopen(id).then(load).finally(() => setBusy(false)) }

  const open = items.filter(w => w.estat === 'open')
  const resolved = items.filter(w => w.estat === 'resolved')
  const visible = showResolved ? items : open

  return (
    <div style={{ border: '0.5px solid var(--border)', borderRadius: 8, padding: '12px 16px', marginTop: 16, background: 'var(--bg-card)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <i className="ti ti-flag" style={{ color: 'var(--warn)' }} />
        <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>{t('watchpoints.title')}</span>
        <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>({open.length} {t('watchpoints.open')})</span>
        {resolved.length > 0 && (
          <button type="button" onClick={() => setShowResolved(s => !s)}
            style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
            {showResolved ? t('watchpoints.hide_resolved') : t('watchpoints.show_resolved', { n: resolved.length })}
          </button>
        )}
      </div>
      {editable && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
          <input value={text} onChange={e => setText(e.target.value)} placeholder={t('watchpoints.placeholder')}
            onKeyDown={e => { if (e.key === 'Enter') add() }}
            style={{ flex: 1, font: 'inherit', fontSize: 'var(--fs-body)', padding: '4px 8px', border: '1px solid var(--border)', borderRadius: 4, background: 'var(--white)' }} />
          <button type="button" onClick={add} disabled={busy || !text.trim()}
            style={{ padding: '4px 12px', border: '0.5px solid var(--gold)', borderRadius: 4, background: 'var(--white)', color: 'var(--gold)', cursor: busy ? 'default' : 'pointer', fontSize: 'var(--fs-body)' }}>
            + {t('watchpoints.add')}
          </button>
        </div>
      )}
      {visible.length === 0 ? (
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('watchpoints.empty')}</div>
      ) : visible.map(w => (
        <div key={w.id} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '6px 0', borderTop: '0.5px solid var(--border)' }}>
          <i className={`ti ${w.estat === 'resolved' ? 'ti-check' : 'ti-flag'}`}
            style={{ fontSize: 14, marginTop: 2, color: w.estat === 'resolved' ? 'var(--ok)' : 'var(--warn)' }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 'var(--fs-body)', whiteSpace: 'pre-wrap',
                          color: w.estat === 'resolved' ? 'var(--text-muted)' : 'var(--text-main)',
                          textDecoration: w.estat === 'resolved' ? 'line-through' : 'none' }}>{w.text}</div>
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
              {w.created_by_nom || '—'} · {fmtDate(w.created_at)}{w.task_type_code ? ` · ${w.task_type_code}` : ''}
              {w.estat === 'resolved' && w.resolved_by_nom ? ` · ${t('watchpoints.resolved_by', { who: w.resolved_by_nom })}` : ''}
            </div>
          </div>
          {editable && (w.estat === 'open'
            ? <button type="button" onClick={() => resolve(w.id)} disabled={busy} style={linkBtn}>{t('watchpoints.resolve')}</button>
            : <button type="button" onClick={() => reopen(w.id)} disabled={busy} style={linkBtn}>{t('watchpoints.reopen')}</button>)}
        </div>
      ))}
    </div>
  )
}
