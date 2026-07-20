import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import PdfButton from '../components/ui/PdfButton'
import { selS, primaryBtn } from '../components/ui/buttons'
import { DocumentHeader, LineTable, RowBtn, DocumentSummary } from '../components/commercial'
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
  const location = useLocation()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [order, setOrder] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)
  // P4 — desplegable read-only per línia: models assignats + tasques + % imputat (lazy).
  const [expanded, setExpanded] = useState(() => new Set())
  const [alloc, setAlloc] = useState({})   // { [lineId]: { loading | error | data } }

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

  // Sprint C — l'assignació de models va a la superfície universal de selecció (mode intenció):
  // arriba a /models amb propòsit + prefiltre customer bloquejat, multi-selecciona fins a la
  // capacitat restant (quantity − qty_allocated) i torna aquí per confirmar el batch (H1).
  const goSelect = (line) => {
    const remaining = Math.max(0, Math.floor(Number(line.quantity) - Number(line.qty_allocated)))
    const params = new URLSearchParams({
      select_for: `order_line:${line.id}`,
      select_max: String(remaining),
      customer: String(order.customer),
      return: location.pathname + location.search,
    })
    navigate(`/models?${params.toString()}`)
  }

  // Carrega (o recarrega) l'expansió d'una línia. force=true reomple encara que ja hi hagi cache
  // (p.ex. després de desassignar un WO, per refrescar els models/estat de la línia).
  const loadAlloc = useCallback((lineId, force = false) => {
    if (!force && alloc[lineId]?.data) return
    setAlloc(a => ({ ...a, [lineId]: { loading: true } }))
    commerce.orderLines.allocation(lineId)
      .then(res => setAlloc(a => ({ ...a, [lineId]: { data: res.data } })))
      .catch(() => setAlloc(a => ({ ...a, [lineId]: { error: true } })))
  }, [alloc])

  // P4 — plega/desplega una línia; carrega l'expansió el primer cop (lazy).
  const toggleLine = (line) => {
    const id = line.id
    const isOpen = expanded.has(id)
    setExpanded(s => { const n = new Set(s); isOpen ? n.delete(id) : n.add(id); return n })
    if (!isOpen) loadAlloc(id)
  }

  // D5 — desassignar un WO d'una línia (orfandat). Confirmació prèvia (trenca vincle); en confirmar,
  // recarrega la comanda (qty_allocated) i l'expansió de la línia afectada.
  const [confirmUnassign, setConfirmUnassign] = useState(null)   // { woId, lineId, codi }
  const doUnassign = () => {
    if (!confirmUnassign) return
    const { woId, lineId } = confirmUnassign
    setBusy(true); setFeedback(null)
    commerce.workOrders.unassign(woId)
      .then(() => { setConfirmUnassign(null); return reload() })
      .then(() => { loadAlloc(lineId, true); setFeedback({ type: 'ok', text: t('orders.unassign_done') }) })
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.detail || t('orders.error') }))
      .finally(() => setBusy(false))
  }

  if (loading) return <Center>{t('orders.loading')}</Center>
  if (error || !order) return <Center>{t('orders.error')}</Center>

  const lines = order.lines || []
  const dueDates = order.due_dates || []
  // Línies encara pendents d'imputar (qty_allocated < quantity). En tornar del mode selecció,
  // reload() les refresca; si en queda alguna, s'ofereix continuar amb la primera (no s'imposa).
  const pendingLines = order.status === 'OPEN'
    ? lines.filter(l => Number(l.qty_allocated) < Number(l.quantity)) : []

  // Columnes de línia del sistema unificat. Read-only; l'expansió (models·tasques·%) va sota la fila.
  const orderColumns = [
    { key: 'desc', label: t('orders.col_concept'), render: l => l.description || l.product_name },
    { key: 'alloc', label: t('orders.col_import_imputat'), align: 'right', width: 100,
      render: l => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }} title={t('orders.allocated')}>{Number(l.qty_allocated).toFixed(2)}/{Number(l.quantity).toFixed(2)}</span> },
    { key: 'price', label: t('orders.col_price'), align: 'right', width: 100,
      render: l => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{money(l.unit_price)}</span> },
    { key: 'total', label: t('orders.col_import'), align: 'right', width: 100,
      render: l => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{money(l.line_total)}</span> },
  ]
  const renderLineActions = (l) => {
    const open = expanded.has(l.id)
    return (
      <>
        <RowBtn icon={open ? 'ti-chevron-down' : 'ti-chevron-right'} active={open}
          title={t(open ? 'orders.collapse' : 'orders.expand')} onClick={() => toggleLine(l)} />
        {canEdit && order.status === 'OPEN' && Number(l.qty_allocated) < Number(l.quantity) && (
          <RowBtn icon="ti-link" disabled={busy} title={t('orders.assign_model')} onClick={() => goSelect(l)} />
        )}
      </>
    )
  }

  return (
    <div style={{ minWidth: 0, maxWidth: 900 }}>
      <button onClick={() => navigate('/comercial/comandes')} style={{ ...smallBtn, marginBottom: 12 }}>
        <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> {t('orders.back')}
      </button>

      <DocumentHeader
        reference={order.document_number}
        statusBadge={<OrderStatusBadge status={order.status} t={t} />}
        customer={order.customer_nom}
        actions={<>
          <PdfButton onClick={doPdf} disabled={busy} label={t('orders.download_pdf')} />
          {canEdit && (
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)' }}>
              {t('orders.status')}:
              <select value={order.status} onChange={e => changeStatus(e.target.value)} disabled={busy} style={{ ...selS }}>
                {STATUSES.map(s => <option key={s} value={s}>{t(`orders.status_${s}`)}</option>)}
              </select>
            </label>
          )}
        </>}
      />

      <div style={{ marginTop: 12 }}>
        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />
      </div>

      {canEdit && pendingLines.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', margin: '0 0 12px',
          padding: '8px 14px', background: 'var(--gold-pale)', border: '0.5px solid var(--gold)', borderRadius: 8,
          fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
          <i className="ti ti-arrow-back-up" aria-hidden="true" />
          <span>{t('orders.pending_lines', { n: pendingLines.length })}</span>
          <button onClick={() => goSelect(pendingLines[0])}
            style={{ ...smallBtn, cursor: 'pointer', color: 'var(--gold)', border: '0.5px solid var(--gold)', fontWeight: 600 }}>
            {t('orders.continue_selecting')}
          </button>
        </div>
      )}

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

      {/* Línies (read-only, desplegables) */}
      <Section title={t('orders.lines')}>
        {lines.length === 0
          ? <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('orders.lines_empty')}</p>
          : <LineTable columns={orderColumns} rows={lines} renderActions={renderLineActions}
              renderExpansion={l => expanded.has(l.id)
                ? <LineExpansion a={alloc[l.id]} t={t} canEdit={canEdit}
                    onUnassign={(wo) => setConfirmUnassign({ woId: wo.id, lineId: l.id, codi: wo.model?.codi_intern || wo.number })} />
                : null} />}
      </Section>
      <div style={{ marginBottom: 16 }}>
        <DocumentSummary lines={orderSummaryLines(order, t)} />
      </div>

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

      {/* Modal — confirmar desassignació (orfandat del WO): trenca el vincle amb la línia */}
      {confirmUnassign && (
        <div onClick={() => setConfirmUnassign(null)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--white)', borderRadius: 12, padding: '1rem 1.2rem',
            maxWidth: 440, width: '100%', border: '0.5px solid var(--gray-l)',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 8, fontFamily: MONO }}>
              {t('orders.unassign_title')}
            </h2>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', marginBottom: 16, lineHeight: 1.4 }}>
              {t('orders.unassign_confirm', { codi: confirmUnassign.codi })}
            </p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setConfirmUnassign(null)} disabled={busy} style={selS}>{t('common.cancel')}</button>
              <button onClick={doUnassign} disabled={busy}
                style={{ ...primaryBtn, background: 'var(--err)', borderColor: 'var(--err)' }}>
                {t('orders.unassign')}
              </button>
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
      <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, fontFamily: MONO, marginBottom: 10 }}>{title}</h2>
      {children}
    </div>
  )
}

function Row({ children }) {
  return <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderTop: '0.5px solid var(--bg-muted)' }}>{children}</div>
}

// P4 — panell read-only d'una línia: models assignats (via WO), tasques amb estat, % imputat.
const TASK_COL = { Done: 'var(--ok)', InProgress: 'var(--gold)', Paused: 'var(--warn)', Pending: 'var(--gray)' }
function LineExpansion({ a, t, canEdit = false, onUnassign = null }) {
  if (!a || a.loading) return <div style={expBox}><span style={expMuted}>{t('orders.alloc_loading')}</span></div>
  if (a.error) return <div style={expBox}><span style={expMuted}>{t('orders.alloc_error')}</span></div>
  const d = a.data || {}
  const wos = d.work_orders || []
  return (
    <div style={expBox}>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: wos.length ? 10 : 0 }}>
        <span style={expMeta}>{t('orders.alloc_pct')}: <b style={{ color: 'var(--text-main)' }}>{d.pct_allocated}%</b></span>
        <span style={expMeta}>{Number(d.qty_allocated ?? 0).toFixed(2)}/{Number(d.quantity ?? 0).toFixed(2)}</span>
      </div>
      {wos.length === 0
        ? <span style={expMuted}>{t('orders.alloc_no_models')}</span>
        : wos.map(wo => (
          <div key={wo.id} style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
              <span style={{ fontFamily: MONO, fontWeight: 700, color: 'var(--gold)', fontSize: 'var(--fs-caption)' }}>{wo.model ? wo.model.codi_intern : '—'}</span>
              {wo.model?.nom_prenda && <span style={{ fontSize: 'var(--fs-caption)' }}>{wo.model.nom_prenda}</span>}
              <span style={{ fontFamily: MONO, color: 'var(--gray)', fontSize: 'var(--fs-caption)' }}>· {wo.number}</span>
              <span style={{ ...woPill, borderColor: wo.status === 'CLOSED' ? 'var(--ok)' : 'var(--gold)', color: wo.status === 'CLOSED' ? 'var(--ok)' : 'var(--gold)' }}>{t(`orders.wo_${wo.status}`, wo.status)}</span>
              {canEdit && wo.can_unassign && onUnassign && (
                <button type="button" onClick={() => onUnassign(wo)} title={t('orders.unassign')}
                  style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 4,
                           background: 'none', border: '0.5px solid var(--err)', borderRadius: 8,
                           color: 'var(--err)', cursor: 'pointer', fontFamily: MONO, fontSize: 'var(--fs-caption)',
                           padding: '1px 8px' }}>
                  <i className="ti ti-unlink" style={{ fontSize: 12 }} />{t('orders.unassign')}
                </button>
              )}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, paddingLeft: 4 }}>
              {wo.tasks.length === 0
                ? <span style={expMuted}>—</span>
                : wo.tasks.map(tk => (
                  <span key={tk.id} style={taskChip} title={tk.code}>
                    <span style={{ width: 7, height: 7, borderRadius: '50%', background: TASK_COL[tk.status] || 'var(--gray)', flex: 'none' }} />
                    {tk.name}
                    {tk.off_recipe && <span style={{ color: 'var(--gold)', fontWeight: 600 }}>· {t('orders.alloc_extra')}</span>}
                    <span style={{ color: TASK_COL[tk.status] || 'var(--gray)', fontWeight: 600 }}>{t(`model_sheet.dashboard.task_status.${tk.status}`, tk.status)}</span>
                  </span>
                ))}
            </div>
          </div>
        ))}
    </div>
  )
}
const expBox = { padding: '10px 12px', margin: '0 0 2px', background: 'var(--bg-muted)', borderRadius: 8, fontSize: 'var(--fs-caption)' }
const expMuted = { fontSize: 'var(--fs-caption)', color: 'var(--gray)', fontFamily: MONO }
const expMeta = { fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', fontFamily: MONO }
const woPill = { fontFamily: MONO, fontSize: 'var(--fs-caption)', fontWeight: 600, padding: '0 6px', borderRadius: 10, border: '0.5px solid var(--gold)' }
const taskChip = { display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 8px', borderRadius: 12, background: 'var(--white)', border: '0.5px solid var(--gray-l)', fontSize: 'var(--fs-caption)', fontFamily: MONO }

// Línies del resum fiscal de la comanda (subtotal · desglossament IVA per tipus · total).
function orderSummaryLines(order, t) {
  const rows = [{ label: t('orders.subtotal'), value: money(order.subtotal) }]
  if ((order.tax_breakdown || []).length) {
    order.tax_breakdown.forEach(b => rows.push({
      label: `${t('orders.vat')} ${Number(b.rate)}% · ${t('orders.base')} ${money(b.base)}`, value: money(b.tax),
    }))
  } else {
    rows.push({ label: t('orders.tax_amount'), value: money(order.tax_amount) })
  }
  rows.push({ label: t('orders.total'), value: money(order.total), strong: true })
  return rows
}

function Meta({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO, textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
      <div style={{ fontFamily: MONO }}>{value}</div>
    </div>
  )
}
