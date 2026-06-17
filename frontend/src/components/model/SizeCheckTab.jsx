import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { sizeChecks } from '../../api/endpoints'
import SizeCheckCell from './SizeCheckCell'

const MONO = 'IBM Plex Mono, monospace'
const fmtDate = (v) => v ? new Date(v).toLocaleString('ca-ES', { dateStyle: 'medium', timeStyle: 'short' }) : '—'

// Tokens idèntics a la taula Mesures (EditableTable).
const TEXT_2 = 'var(--color-text-secondary, #868685)'
const BORDER = 'var(--color-border-tertiary, #e0d5c5)'
const th = { padding: '6px 10px', borderBottom: `1px solid ${BORDER}`, fontFamily: MONO, fontSize: 11, fontWeight: 600, color: TEXT_2, textAlign: 'left', whiteSpace: 'nowrap' }
const tdRO = { padding: '4px 10px', borderBottom: `0.5px solid ${BORDER}`, fontFamily: MONO, fontSize: 12 }

const btn = (variant) => ({
  fontFamily: MONO, fontSize: 12, padding: '6px 14px', borderRadius: 4, cursor: 'pointer',
  border: '0.5px solid var(--gray-l)',
  background: variant === 'err' ? 'var(--err)' : variant === 'plain' ? 'var(--white)' : 'var(--gold)',
  color: variant === 'plain' ? 'var(--text-main)' : 'var(--white)', fontWeight: 500,
})

const estatColor = (e) => e === 'Acceptat' ? 'var(--ok)' : (e === 'Pendent' ? 'var(--gold)' : 'var(--err)')

// SC-1..SC-5 — Tab Size Check: validació del proto a talla base, abans del fitting.
// editable=true  (ruta Kanban): treball (open-on-mount, cel·les editables, Gravar/Descartar).
// editable=false (pestanya Model): CONSULTA. Mostra l'Històric clicable + la taula read-only
//   del check seleccionat (per defecte el més recent). MAI fa open.
export default function SizeCheckTab({ model, onFeedback, editable = false }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [check, setCheck] = useState(null)        // check mostrat a la taula
  const [history, setHistory] = useState([])      // tots els checks del model (summary)
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(null)        // modal propagació (Acceptat net amb deltes)
  const [reschedule, setReschedule] = useState(null)  // {estat, descartades} → modal reagendar
  const [reDate, setReDate] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    sizeChecks.list({ model: model.id, ordering: '-created_at', page_size: 100 })
      .then(async r => {
        const rows = r.data?.results ?? r.data ?? []
        setHistory(rows)
        if (editable) {
          // Mode treball (Kanban): garanteix un check viu (open idempotent: crea o reusa).
          const full = await sizeChecks.open(model.id)
          setCheck(full.data); setSelectedId(full.data.id)
        } else if (rows.length) {
          // Mode consulta: mostra el més recent (rows[0]); NO fa open (no crea res).
          const full = await sizeChecks.get(rows[0].id)
          setCheck(full.data); setSelectedId(rows[0].id)
        } else {
          setCheck(null); setSelectedId(null)
        }
      })
      .catch(() => { setCheck(null); setHistory([]) })
      .finally(() => setLoading(false))
  }, [model.id, editable])

  useEffect(() => { load() }, [load])

  // Consulta: clic a una fila de l'Històric → mostra aquella taula.
  const selectCheck = (id) => {
    setSelectedId(id)
    sizeChecks.get(id).then(r => setCheck(r.data)).catch(() => {})
  }

  const hasDescartades = (check?.lines || []).some(l => l.decisio === 'valor_descartat')

  const onResolveClick = (estat) => {
    if (estat === 'Acceptat') {
      if (hasDescartades) { openReschedule('Acceptat', true); return }      // → Rebutjat
      if (check?.te_deltes) { setConfirm('Acceptat'); return }              // propagació
      doResolve('Acceptat'); return
    }
    openReschedule('Descartat', false)                                      // Descartar
  }

  const openReschedule = (estat, descartades) => {
    setReDate(check?.data_represa_default || '')
    setReschedule({ estat, descartades })
  }

  const doResolve = (estat, opts = {}) => {
    if (!check) return
    setConfirm(null); setReschedule(null)
    setBusy(true)
    sizeChecks.resolve(check.id, estat, opts)
      .then(r => {
        const d = r.data || {}
        const dr = d.data_represa
        let text
        if (d.estat === 'Acceptat') {
          const extra = d.regradat ? ` · grading regradat (v${d.nova_version})` : ''
          text = t('sizecheck.fb_saved', { n: d.written || 0 }) + extra
        } else if (d.estat === 'Rebutjat') {
          text = t('sizecheck.fb_rejected', { d: dr || '—' })
        } else {
          text = t('sizecheck.fb_discarded', { d: dr || '—' })
        }
        onFeedback?.({ type: 'ok', text })
        if (editable) navigate('/tasques/kanban')   // feina acabada a la superfície de treball
        else load()
      })
      .catch(e => onFeedback?.({ type: 'err', text: e.response?.data?.error || t('sizecheck.resolve_error') }))
      .finally(() => setBusy(false))
  }

  const renderGrid = (c) => (
    <table style={{ borderCollapse: 'collapse', width: '100%', marginBottom: 16 }}>
      <thead>
        <tr>
          <th style={th}>POM</th>
          <th style={th}>{t('sizecheck.col_measure')}</th>
          <th style={{ ...th, textAlign: 'right' }}>{t('sizecheck.col_theoretical')}</th>
          <th style={{ ...th, textAlign: 'right' }}>{t('sizecheck.col_tolerance')}</th>
          <th style={{ ...th, textAlign: 'right' }}>{t('sizecheck.col_real')}</th>
          <th style={{ ...th, textAlign: 'center' }}>{t('sizecheck.col_decision')}</th>
          <th style={th}>{t('sizecheck.col_note')}</th>
        </tr>
      </thead>
      <tbody>
        {(c.lines || []).map(line => (
          <tr key={line.id}>
            <td style={{ ...tdRO, fontFamily: MONO, color: 'var(--gold)', fontWeight: line.is_key ? 700 : 400 }}>{line.codi_fitxa || line.codi}</td>
            <td style={{ ...tdRO, color: TEXT_2 }}>{line.nom}</td>
            {/* En consulta sempre disabled; en treball, editable. */}
            <SizeCheckCell key={`${c.id}-${line.id}`} line={line} disabled={!editable} />
          </tr>
        ))}
      </tbody>
    </table>
  )

  const renderHistory = (clickable) => (
    history.length > 0 && (
      <div style={{ marginTop: 28 }}>
        <h3 style={{ fontSize: 13, fontWeight: 500, fontFamily: MONO, color: 'var(--text-muted)', margin: '0 0 8px' }}>{t('sizecheck.history')}</h3>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={th}>{t('sizecheck.col_date')}</th>
              <th style={th}>{t('sizecheck.col_status')}</th>
              <th style={th}>{t('sizecheck.col_resolved_by')}</th>
            </tr>
          </thead>
          <tbody>
            {history.map(h => (
              <tr key={h.id}
                  onClick={clickable ? () => selectCheck(h.id) : undefined}
                  style={{
                    cursor: clickable ? 'pointer' : 'default',
                    background: clickable && h.id === selectedId ? 'var(--color-background-secondary, #f5f0ea)' : undefined,
                  }}>
                <td style={tdRO}>{fmtDate(h.resolt_at || h.created_at)}</td>
                <td style={{ ...tdRO, fontWeight: 600, color: estatColor(h.estat) }}>{h.estat}</td>
                <td style={tdRO}>{h.resolt_per_nom || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  )

  if (loading) return <div style={{ fontFamily: MONO, fontSize: 12, color: 'var(--text-muted)' }}>{t('common.loading')}</div>

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
            ? t('sizecheck.open_error')
            : t('sizecheck.consult_empty')}
        </p>
      )}

      {/* MODE TREBALL (Kanban): graella editable + botons, després històric. */}
      {editable && check && (
        <>
          {renderGrid(check)}
          <div style={{ display: 'flex', gap: 10 }}>
            <button style={btn('gold')} disabled={busy} onClick={() => onResolveClick('Acceptat')}>{t('sizecheck.save')}</button>
            <button style={btn('err')} disabled={busy} onClick={() => onResolveClick('Descartat')}>{t('sizecheck.discard')}</button>
          </div>
        </>
      )}
      {editable && renderHistory(false)}

      {/* MODE CONSULTA: Històric clicable a dalt, taula read-only del seleccionat a sota. */}
      {!editable && (
        <>
          {renderHistory(true)}
          {check && (
            <div style={{ marginTop: 20 }}>
              <h3 style={{ fontSize: 13, fontWeight: 500, fontFamily: MONO, color: 'var(--text-muted)', margin: '0 0 8px' }}>
                {t('sizecheck.validated_table')} · <span style={{ color: estatColor(check.estat) }}>{check.estat}</span>
              </h3>
              {renderGrid(check)}
            </div>
          )}
        </>
      )}

      {/* Modal propagació (Acceptat net amb deltes). */}
      {confirm && (
        <div style={overlay} onClick={() => setConfirm(null)}>
          <div onClick={e => e.stopPropagation()} style={modal}>
            <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>{t('sizecheck.propagate_title')}</h3>
            <p style={{ margin: '0 0 18px', fontSize: 12, lineHeight: 1.5, color: 'var(--text-main)' }}>
              {t('sizecheck.propagate_warning')}
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button style={btn('plain')} disabled={busy} onClick={() => setConfirm(null)}>{t('common.cancel')}</button>
              <button style={btn('gold')} disabled={busy} onClick={() => doResolve('Acceptat')}>{t('sizecheck.confirm_propagate')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal reagendar (Gravar-amb-descartades o Descartar): data OBLIGATÒRIA de represa. */}
      {reschedule && (
        <div style={overlay} onClick={() => setReschedule(null)}>
          <div onClick={e => e.stopPropagation()} style={modal}>
            <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>{t('sizecheck.reschedule_title')}</h3>
            {reschedule.descartades && (
              <p style={{ margin: '0 0 12px', fontSize: 12, lineHeight: 1.5, color: 'var(--err)' }}>
                {t('sizecheck.reschedule_rejected')}
              </p>
            )}
            <p style={{ margin: '0 0 8px', fontSize: 12, lineHeight: 1.5, color: 'var(--text-main)' }}>
              {t('sizecheck.reschedule_help')}
            </p>
            <input type="date" value={reDate} onChange={e => setReDate(e.target.value)}
                   style={{ fontFamily: MONO, fontSize: 13, padding: '6px 8px', borderRadius: 4, border: `1px solid ${BORDER}`, marginBottom: 18, width: '100%', boxSizing: 'border-box' }} />
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button style={btn('plain')} disabled={busy} onClick={() => setReschedule(null)}>{t('common.cancel')}</button>
              <button style={btn(reschedule.estat === 'Descartat' ? 'err' : 'gold')} disabled={busy || !reDate}
                      onClick={() => doResolve(reschedule.estat, { data_represa: reDate })}>
                {t('sizecheck.reschedule_confirm')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const overlay = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex',
  alignItems: 'center', justifyContent: 'center', zIndex: 1000,
}
const modal = {
  background: 'var(--white)', borderRadius: 8, padding: 24, maxWidth: 460,
  fontFamily: MONO, boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
}
