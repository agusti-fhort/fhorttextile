import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { sizeChecks } from '../../api/endpoints'
import SizeCheckCell from './SizeCheckCell'

const MONO = 'IBM Plex Mono, monospace'
const fmtDate = (v) => v ? new Date(v).toLocaleString('ca-ES', { dateStyle: 'medium', timeStyle: 'short' }) : '—'

const th = { padding: '6px 8px', borderBottom: '1px solid var(--border)', fontFamily: MONO, fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textAlign: 'left', whiteSpace: 'nowrap' }
const tdRO = { padding: '5px 8px', borderBottom: '0.5px solid var(--border)', fontFamily: MONO, fontSize: 12 }

const btn = (variant) => ({
  fontFamily: MONO, fontSize: 12, padding: '6px 14px', borderRadius: 4, cursor: 'pointer',
  border: '0.5px solid var(--gray-l)',
  background: variant === 'ok' ? 'var(--ok)' : variant === 'err' ? 'var(--err)' : variant === 'plain' ? 'var(--white)' : 'var(--gold)',
  color: variant === 'plain' ? 'var(--text-main)' : '#fff', fontWeight: 500,
})

// SC-1/SC-2/SC-3 — Tab Size Check: validació del proto a talla base, abans del fitting.
// Dos modes segons `editable`:
//  - editable=true  (ruta Kanban /models/:id/size-check): treball. open-on-mount
//    (crea/reusa el check viu), cel·les editables, resoldre visible.
//  - editable=false (pestanya Model, default): CONSULTA pura. NOMÉS list+get, MAI
//    open → visitar-la no crea cap check. Cel·les read-only, sense resoldre ni obrir.
export default function SizeCheckTab({ model, onFeedback, editable = false }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [check, setCheck] = useState(null)        // check viu (Pendent) amb lines
  const [history, setHistory] = useState([])      // checks resolts (summary)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(null)    // estat pendent de confirmació (modal propagació)

  const load = useCallback(() => {
    setLoading(true)
    sizeChecks.list({ model: model.id, ordering: '-created_at', page_size: 100 })
      .then(async r => {
        const rows = r.data?.results ?? r.data ?? []
        setHistory(rows.filter(c => c.estat !== 'Pendent'))
        const live = rows.find(c => c.estat === 'Pendent')
        if (editable) {
          // Mode treball (Kanban): garanteix un check viu (open idempotent: crea o reusa).
          const full = await sizeChecks.open(model.id)
          setCheck(full.data)
        } else if (live) {
          // Mode consulta (pestanya Model): NOMÉS list+get, MAI open → no crea res.
          const full = await sizeChecks.get(live.id)
          setCheck(full.data)
        } else {
          setCheck(null)
        }
      })
      .catch(() => { setCheck(null); setHistory([]) })
      .finally(() => setLoading(false))
  }, [model.id, editable])

  useEffect(() => { load() }, [load])

  // Acceptar amb propagació: si el model té deltes, avís+confirma abans de resoldre.
  const onResolveClick = (estat) => {
    if (estat === 'Acceptat' && check?.te_deltes) { setConfirm('Acceptat'); return }
    doResolve(estat)
  }

  const doResolve = (estat) => {
    if (!check) return
    setConfirm(null)
    setBusy(true)
    sizeChecks.resolve(check.id, estat)
      .then(r => {
        const d = r.data || {}
        const extra = d.regradat ? ` · grading regradat (v${d.nova_version})` : ''
        onFeedback?.({ type: 'ok', text: `Check ${estat.toLowerCase()} · ${d.written || 0} mesura(es) a la base${extra}` })
        // Resolt = feina acabada a la superfície de treball → torna al Kanban (el tècnic marca Done allà).
        if (editable) navigate('/tasques/kanban')
        else load()
      })
      .catch(e => onFeedback?.({ type: 'err', text: e.response?.data?.error || t('sizecheck.resolve_error', 'No s\'ha pogut resoldre') }))
      .finally(() => setBusy(false))
  }

  if (loading) return <div style={{ fontFamily: MONO, fontSize: 12, color: 'var(--text-muted)' }}>{t('common.loading', 'Carregant…')}</div>

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 14 }}>
        <h2 style={{ fontSize: 15, fontWeight: 500, margin: 0, fontFamily: MONO }}>
          Size Check · talla base {model.base_size_label ? `(${model.base_size_label})` : ''}
        </h2>
      </div>

      {!check && (
        <p style={{ fontFamily: MONO, fontSize: 12, color: 'var(--text-muted)' }}>
          {editable
            ? t('sizecheck.open_error', 'No s\'ha pogut obrir el size check.')
            : t('sizecheck.consult_empty', 'No hi ha cap size check per a aquest model. Inicia\'l des del Kanban (tasca Size Check).')}
        </p>
      )}

      {check && (
        <>
          <table style={{ borderCollapse: 'collapse', width: '100%', marginBottom: 16 }}>
            <thead>
              <tr>
                <th style={th}>POM</th>
                <th style={th}>{t('sizecheck.col_measure', 'Mesura')}</th>
                <th style={{ ...th, textAlign: 'right' }}>{t('sizecheck.col_theoretical', 'Teòric')}</th>
                <th style={{ ...th, textAlign: 'right' }}>{t('sizecheck.col_real', 'Real (proto)')}</th>
                <th style={{ ...th, textAlign: 'center' }}>{t('sizecheck.col_decision', 'Decisió')}</th>
                <th style={th}>{t('sizecheck.col_note', 'Nota')}</th>
              </tr>
            </thead>
            <tbody>
              {(check.lines || []).map(line => (
                <tr key={line.id}>
                  <td style={{ ...tdRO, fontWeight: line.is_key ? 700 : 400 }}>{line.codi}</td>
                  <td style={{ ...tdRO, color: 'var(--text-muted)' }}>{line.nom}</td>
                  <SizeCheckCell line={line} disabled={!editable} />
                </tr>
              ))}
            </tbody>
          </table>

          {editable && (
            <div style={{ display: 'flex', gap: 10 }}>
              <button style={btn('ok')} disabled={busy} onClick={() => onResolveClick('Acceptat')}>{t('sizecheck.accept', 'Acceptar')}</button>
              <button style={btn('err')} disabled={busy} onClick={() => onResolveClick('Descartat')}>{t('sizecheck.discard', 'Descartar')}</button>
            </div>
          )}
        </>
      )}

      {history.length > 0 && (
        <div style={{ marginTop: 28 }}>
          <h3 style={{ fontSize: 13, fontWeight: 500, fontFamily: MONO, color: 'var(--text-muted)', margin: '0 0 8px' }}>{t('sizecheck.history', 'Històric')}</h3>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                <th style={th}>{t('sizecheck.col_date', 'Data')}</th>
                <th style={th}>{t('sizecheck.col_status', 'Estat')}</th>
                <th style={th}>{t('sizecheck.col_resolved_by', 'Resolt per')}</th>
              </tr>
            </thead>
            <tbody>
              {history.map(h => (
                <tr key={h.id}>
                  <td style={tdRO}>{fmtDate(h.resolt_at || h.created_at)}</td>
                  <td style={{ ...tdRO, fontWeight: 600, color: h.estat === 'Acceptat' ? 'var(--ok)' : 'var(--err)' }}>{h.estat}</td>
                  <td style={tdRO}>{h.resolt_per_nom || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {confirm && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }} onClick={() => setConfirm(null)}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--white)', borderRadius: 8, padding: 24, maxWidth: 460,
            fontFamily: MONO, boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
          }}>
            <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>{t('sizecheck.propagate_title', 'Propagar correccions al grading?')}</h3>
            <p style={{ margin: '0 0 18px', fontSize: 12, lineHeight: 1.5, color: 'var(--text-main)' }}>
              {t('sizecheck.propagate_warning', 'Les correccions acceptades s\'escriuran a la talla base i es propagaran al grading segons els deltes informats.')}
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button style={btn('plain')} disabled={busy} onClick={() => setConfirm(null)}>{t('common.cancel', 'Cancel·lar')}</button>
              <button style={btn('ok')} disabled={busy} onClick={() => doResolve('Acceptat')}>{t('sizecheck.confirm_propagate', 'Acceptar i propagar')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
