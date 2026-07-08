import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Badge from '../components/ui/Badge'
import { selS, primaryBtn } from '../components/ui/buttons'
import { WOStatusBadge, WOKindBadge } from './WorkOrders'
import { formatMinutes } from '../utils/format'

// Mòdul Comercial — B4a · fitxa d'encàrrec (read-only) + tancament amb política de bloquejos.
// El detall llista les tasques (estat + minuts de timer), marca els extres off_recipe (filet grana)
// i mostra els ajustos. El botó Tancar obre un modal amb la resposta estructurada del close.
const MONO = 'IBM Plex Mono, monospace'
const smallBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const TASK_STATUS_VARIANT = { Done: 'ok', InProgress: 'gold', Paused: 'warn', Pending: 'gray' }
const sectionTitle = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontWeight: 500,
  textTransform: 'uppercase', letterSpacing: '0.04em', margin: '18px 0 8px',
}
const cell = { padding: '6px 10px', fontSize: 'var(--fs-body)', borderTop: '0.5px solid var(--gray-l)' }

export default function WorkOrderDetail() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canClose = !!me?.capabilities?.includes('define_tasks')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [wo, setWo] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)
  const [modal, setModal] = useState(null)          // resposta estructurada del close (o null)
  const [extraKinds, setExtraKinds] = useState({})  // model_task_id → EXTRA_BILL | EXTRA_ABSORB

  const reload = useCallback(() => commerce.workOrders.get(id)
    .then(res => setWo(res.data)).catch(() => setError(true)), [id])

  useEffect(() => {
    let alive = true
    commerce.workOrders.get(id).then(res => { if (alive) setWo(res.data) })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [id])

  // Crida el close amb opcions; si torna 409 (no tancat) mostra el modal amb blockers/pending.
  const doClose = (opts = {}) => {
    setBusy(true); setFeedback(null)
    return commerce.workOrders.close(id, opts)
      .then(res => {
        setModal(null); setExtraKinds({})
        return reload().then(() => setFeedback({ type: 'ok', text: t('workorders.closed_ok') }))
      })
      .catch(err => {
        const data = err?.response?.data
        if (data && (data.blockers || data.pending_proposals)) setModal(data)
        else setFeedback({ type: 'err', text: t('workorders.close_error') })
      })
      .finally(() => setBusy(false))
  }

  // Confirmar des del modal: resol els extres amb la mena triada + (opcional) cancel·la pendents.
  const confirmClose = (cancelPending) => {
    const unresolved = (modal?.blockers || []).filter(b => b.reason === 'extra_unresolved')
    const resolve_extras = unresolved.map(b => ({
      model_task: b.model_task, kind: extraKinds[b.model_task] || 'EXTRA_BILL',
    }))
    doClose({ resolve_extras, cancel_pending: cancelPending })
  }

  if (loading) return <Center>{t('workorders.loading')}</Center>
  if (error || !wo) return <Center>{t('workorders.error')}</Center>

  const tasks = wo.tasks || []
  const adjustments = wo.adjustments || []
  const isOpen = wo.status === 'OPEN'
  const hardBlockers = (modal?.blockers || []).filter(b => b.reason === 'InProgress' || b.reason === 'Paused')
  const extraBlockers = (modal?.blockers || []).filter(b => b.reason === 'extra_unresolved')
  const pending = modal?.pending_proposals || []

  return (
    <div style={{ minWidth: 0, maxWidth: 900 }}>
      <button onClick={() => navigate('/comercial/encarrecs')} style={{ ...smallBtn, marginBottom: 12 }}>
        <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> {t('workorders.back')}
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6, flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, fontFamily: MONO }}>{wo.number}</h1>
        <WOKindBadge kind={wo.kind} t={t} />
        <WOStatusBadge status={wo.status} t={t} />
      </div>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 16 }}>
        {wo.customer_nom} · {wo.kind === 'COLLECTOR' ? wo.period : (wo.model_codi || '—')}
      </p>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {canClose && isOpen && (
        <button onClick={() => doClose()} disabled={busy} style={{ ...primaryBtn, marginBottom: 8 }}>
          <i className="ti ti-lock" style={{ fontSize: 14, marginRight: 6 }} /> {t('workorders.close_action')}
        </button>
      )}

      {/* Tasques */}
      <div style={sectionTitle}>{t('workorders.tasks')}</div>
      {tasks.length === 0 ? <p style={{ color: 'var(--text-muted)' }}>{t('workorders.tasks_empty')}</p> : (
        <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 10, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '6px 10px' }}>{t('workorders.task_type')}</th>
                <th style={{ padding: '6px 10px' }}>{t('workorders.task_status')}</th>
                <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('workorders.task_minutes')}</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map(tk => (
                <tr key={tk.id} style={{ borderLeft: tk.off_recipe ? '3px solid var(--err)' : '3px solid transparent' }}>
                  <td style={cell}>
                    <span style={{ fontWeight: 500 }}>{tk.task_type_name || tk.task_type_code}</span>
                    {tk.off_recipe && (
                      <span style={{ marginLeft: 8, fontSize: 'var(--fs-label)', color: 'var(--err)' }}>
                        <i className="ti ti-flag" style={{ fontSize: 12, marginRight: 3 }} />{t('workorders.off_recipe')}
                      </span>
                    )}
                  </td>
                  <td style={cell}>
                    <Badge variant={TASK_STATUS_VARIANT[tk.status] || 'gray'}>{t(`workorders.status_task_${tk.status}`, { defaultValue: tk.status })}</Badge>
                  </td>
                  <td style={{ ...cell, textAlign: 'right', fontFamily: MONO, color: 'var(--text-muted)' }}>{formatMinutes(tk.minutes ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Ajustos */}
      {adjustments.length > 0 && (
        <>
          <div style={sectionTitle}>{t('workorders.adjustments')}</div>
          <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 10, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                {adjustments.map(a => (
                  <tr key={a.id}>
                    <td style={cell}><Badge variant="gray">{t(`workorders.adj_${a.kind}`)}</Badge></td>
                    <td style={cell}>{a.description || '—'}</td>
                    <td style={{ ...cell, textAlign: 'right', fontFamily: MONO }}>{Number(a.amount ?? 0).toFixed(2)} €</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Modal de tancament amb la resposta estructurada */}
      {modal && (
        <div onClick={() => setModal(null)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--white)', borderRadius: 12, padding: '1.2rem 1.4rem',
            maxWidth: 520, width: '100%', maxHeight: '80vh', overflowY: 'auto',
            border: '0.5px solid var(--gray-l)',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 10, fontFamily: MONO }}>
              {t('workorders.close_title')}
            </h2>

            {hardBlockers.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ color: 'var(--err)', fontWeight: 600, marginBottom: 6 }}>{t('workorders.blockers_hard')}</div>
                {hardBlockers.map((b, i) => (
                  <div key={i} style={{ fontSize: 'var(--fs-body)', color: 'var(--err)' }}>
                    · {b.task_type} — {t(`workorders.status_task_${b.reason}`, { defaultValue: b.reason })}
                  </div>
                ))}
              </div>
            )}

            {extraBlockers.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>{t('workorders.blockers_extra')}</div>
                {extraBlockers.map((b, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ flex: 1, fontSize: 'var(--fs-body)' }}>{b.task_type}</span>
                    <select value={extraKinds[b.model_task] || 'EXTRA_BILL'}
                      onChange={e => setExtraKinds(k => ({ ...k, [b.model_task]: e.target.value }))} style={{ ...selS }}>
                      <option value="EXTRA_BILL">{t('workorders.adj_EXTRA_BILL')}</option>
                      <option value="EXTRA_ABSORB">{t('workorders.adj_EXTRA_ABSORB')}</option>
                    </select>
                  </div>
                ))}
              </div>
            )}

            {pending.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>{t('workorders.pending_title')}</div>
                {pending.map((p, i) => (
                  <div key={i} style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>· {p.task_type}</div>
                ))}
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
              {hardBlockers.length === 0 && (
                <button onClick={() => confirmClose(pending.length > 0)} disabled={busy} style={{ ...primaryBtn }}>
                  {pending.length > 0 ? t('workorders.close_deduct') : t('workorders.close_confirm')}
                </button>
              )}
              <button onClick={() => setModal(null)} disabled={busy} style={smallBtn}>{t('workorders.close_cancel')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
