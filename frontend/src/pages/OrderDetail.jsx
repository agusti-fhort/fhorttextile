import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce, models as modelsApi } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import { selS, primaryBtn } from '../components/ui/buttons'
import { OrderStatusBadge, allocatedPct } from './Orders'

// Mòdul Comercial — B3b · fitxa de comanda (read-only). Línies i venciments congelats (neixen de
// la conversió); l'única mutació és el `status` (OPEN/COMPLETED/CANCELLED) i el PDF. Plantilla QuoteDetail.jsx.
const MONO = 'IBM Plex Mono, monospace'
const smallBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const STATUSES = ['OPEN', 'COMPLETED', 'CANCELLED']
const money = (v) => `${Number(v ?? 0).toFixed(2)} €`
const fmtDate = (d) => d || '—'

function downloadBlob(blob, filename) {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link); link.click(); document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}
function filenameFromHeaders(res, fallback) {
  const cd = res?.headers?.['content-disposition'] || ''
  const m = /filename="?([^"]+)"?/.exec(cd)
  return (m && m[1]) || fallback
}

export default function OrderDetail() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [order, setOrder] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)
  // Modal 3 — assignar model a una línia (B4b): { line, models:[], modelId }
  const [assign, setAssign] = useState(null)

  const reload = useCallback(() => commerce.orders.get(id)
    .then(res => setOrder(res.data)).catch(() => setError(true)), [id])

  useEffect(() => {
    let alive = true
    commerce.orders.get(id).then(res => { if (alive) setOrder(res.data) })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [id])

  const doPdf = () => {
    setBusy(true); setFeedback(null)
    commerce.orders.pdf(id)
      .then(res => downloadBlob(res.data, filenameFromHeaders(res, `${order?.document_number || 'comanda'}.pdf`)))
      .catch(() => setFeedback({ type: 'err', text: t('orders.pdf_error') }))
      .finally(() => setBusy(false))
  }

  const changeStatus = (status) => {
    setBusy(true); setFeedback(null)
    commerce.orders.update(id, { status })
      .then(() => reload()).then(() => setFeedback({ type: 'ok', text: t('orders.status_saved') }))
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.detail || t('orders.error') }))
      .finally(() => setBusy(false))
  }

  // Modal 3 — obre el selector de models del client de la comanda.
  const openAssign = (line) => {
    setFeedback(null)
    modelsApi.list({ customer: order.customer, page_size: 500 })
      .then(res => {
        const list = res.data?.results ?? (Array.isArray(res.data) ? res.data : [])
        setAssign({ line, models: list, modelId: '' })
      })
      .catch(() => setFeedback({ type: 'err', text: t('orders.error') }))
  }
  const doAssign = () => {
    if (!assign?.modelId) return
    setBusy(true); setFeedback(null)
    commerce.orderLines.assignModel(assign.line.id, { model_id: Number(assign.modelId) })
      .then(res => {
        const d = res.data
        const msg = t('orders.assign_done', { wo: d.work_order?.number, n: d.migrated_tasks ?? 0 })
        setAssign(null)
        return reload().then(() => setFeedback({
          type: 'ok', text: msg + (d.warnings?.length ? ' · ' + d.warnings.join(' ') : '') }))
      })
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.detail || t('orders.error') }))
      .finally(() => setBusy(false))
  }

  if (loading) return <Center>{t('orders.loading')}</Center>
  if (error || !order) return <Center>{t('orders.error')}</Center>

  const lines = order.lines || []
  const dueDates = order.due_dates || []

  return (
    <div style={{ minWidth: 0, maxWidth: 900 }}>
      <button onClick={() => navigate('/comercial/comandes')} style={{ ...smallBtn, marginBottom: 12 }}>
        <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> {t('orders.back')}
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6, flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, fontFamily: MONO }}>{order.document_number}</h1>
        <OrderStatusBadge status={order.status} t={t} />
      </div>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 16 }}>{order.customer_nom}</p>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <button onClick={doPdf} disabled={busy} style={smallBtn}>
          <i className="ti ti-file-download" style={{ fontSize: 14 }} /> {t('orders.download_pdf')}
        </button>
        {canEdit && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)' }}>
            {t('orders.status')}:
            <select value={order.status} onChange={e => changeStatus(e.target.value)} disabled={busy} style={{ ...selS }}>
              {STATUSES.map(s => <option key={s} value={s}>{t(`orders.status_${s}`)}</option>)}
            </select>
          </label>
        )}
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      <p style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', marginBottom: 12 }}>{t('orders.readonly_note')}</p>

      {/* Traçabilitat + imputació */}
      <Section title={t('orders.details')}>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <Meta label={t('orders.source_quote')} value={order.source_quote_number || '—'} />
          <Meta label={t('orders.issued_at')} value={fmtDate(order.issued_at)} />
          <Meta label={t('orders.payment_terms')} value={order.payment_terms_name || '—'} />
          <Meta label={t('orders.allocated')} value={`${allocatedPct(order)}%`} />
        </div>
      </Section>

      {/* Línies (read-only) + totals */}
      <Section title={t('orders.lines')}>
        {lines.length === 0 && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('orders.lines_empty')}</p>}
        {lines.map(l => (
          <Row key={l.id}>
            <span style={{ flex: 1 }}>{l.description || l.product_name}</span>
            <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }} title={t('orders.allocated')}>
              {Number(l.qty_allocated).toFixed(2)}/{Number(l.quantity).toFixed(2)}
            </span>
            <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{money(l.unit_price)}</span>
            <span style={{ fontFamily: MONO, fontWeight: 600, minWidth: 90, textAlign: 'right' }}>{money(l.line_total)}</span>
            {canEdit && order.status === 'OPEN' && Number(l.qty_allocated) < Number(l.quantity) && (
              <button onClick={() => openAssign(l)} disabled={busy} style={smallBtn} title={t('orders.assign_model')}>
                <i className="ti ti-link" style={{ fontSize: 13 }} />
              </button>
            )}
          </Row>
        ))}
        <div style={{ marginTop: 12, paddingTop: 8, borderTop: '0.5px solid var(--gray-l)', display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end' }}>
          <Total label={t('orders.subtotal')} value={money(order.subtotal)} />
          {(order.tax_breakdown || []).map((b, i) => (
            <Total key={i} label={`${t('orders.vat')} ${Number(b.rate)}% · ${t('orders.base')} ${money(b.base)}`} value={money(b.tax)} />
          ))}
          {(!order.tax_breakdown || order.tax_breakdown.length === 0) &&
            <Total label={t('orders.tax_amount')} value={money(order.tax_amount)} />}
          <Total label={t('orders.total')} value={money(order.total)} strong />
        </div>
      </Section>

      {/* Venciments materialitzats */}
      <Section title={t('orders.due_dates')}>
        {dueDates.length === 0
          ? <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('orders.due_dates_empty')}</p>
          : dueDates.map(d => (
            <Row key={d.id}>
              <span style={{ flex: 1, fontFamily: MONO }}>{Number(d.percentage)}%</span>
              <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{fmtDate(d.due_date)}</span>
              <span style={{ fontFamily: MONO, fontWeight: 600, minWidth: 90, textAlign: 'right' }}>{money(d.amount)}</span>
            </Row>
          ))}
      </Section>

      {/* Modal 3 — assignar model a la línia (crea WO ORDER + migra el col·lector) */}
      {assign && (
        <div onClick={() => setAssign(null)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--white)', borderRadius: 12, padding: '1.2rem 1.4rem',
            maxWidth: 460, width: '100%', border: '0.5px solid var(--gray-l)',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>
              {t('orders.assign_title')}
            </h2>
            <p style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 12 }}>
              {assign.line.description || assign.line.product_name}
            </p>
            <select value={assign.modelId} onChange={e => setAssign({ ...assign, modelId: e.target.value })}
              style={{ ...selS, width: '100%', marginBottom: 8 }}>
              <option value="">{t('orders.assign_pick_model')}…</option>
              {assign.models.map(m => (
                <option key={m.id} value={m.id}>{m.codi_intern} · {m.nom_prenda || '—'}</option>
              ))}
            </select>
            {(() => {
              const sel = assign.models.find(m => String(m.id) === String(assign.modelId))
              return sel && !sel.garment_type_item_nom
                ? <p style={{ fontSize: 'var(--fs-label)', color: 'var(--gold)', marginBottom: 8 }}>
                    <i className="ti ti-alert-triangle" style={{ fontSize: 13, marginRight: 4 }} />{t('orders.assign_gti_warn')}</p>
                : null
            })()}
            <p style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 12 }}>
              {t('orders.assign_migrate_note')}
            </p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setAssign(null)} disabled={busy} style={smallBtn}>{t('orders.assign_cancel')}</button>
              <button onClick={doAssign} disabled={busy || !assign.modelId} style={{ ...primaryBtn }}>{t('orders.assign_confirm')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', padding: 16, marginBottom: 16 }}>
      <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, fontFamily: MONO, marginBottom: 10 }}>{title}</h2>
      {children}
    </div>
  )
}

function Row({ children }) {
  return <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderTop: '0.5px solid var(--bg-muted)' }}>{children}</div>
}

function Total({ label, value, strong }) {
  return (
    <div style={{ display: 'flex', gap: 16, minWidth: 220, justifyContent: 'space-between' }}>
      <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontWeight: strong ? 600 : 400 }}>{label}</span>
      <span style={{ fontFamily: MONO, fontWeight: strong ? 700 : 400 }}>{value}</span>
    </div>
  )
}

function Meta({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO, textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
      <div style={{ fontFamily: MONO }}>{value}</div>
    </div>
  )
}
