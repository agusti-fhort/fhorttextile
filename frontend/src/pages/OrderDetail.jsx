import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce, models as modelsApi } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import PdfButton from '../components/ui/PdfButton'
import { selS, primaryBtn } from '../components/ui/buttons'
import { OrderStatusBadge, allocatedPct } from './Orders'

// Mòdul Comercial — B3b · fitxa de comanda (read-only). Línies i venciments congelats (neixen de
// la conversió); l'única mutació és el `status` (OPEN/COMPLETED/CANCELLED) i el PDF. Plantilla QuoteDetail.jsx.
const MONO = 'IBM Plex Mono, monospace'
const smallBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
// Picker de models (Modal 3) — input/select i files denses.
const pInp = {
  padding: '5px 9px', border: '0.5px solid var(--gray-l)', borderRadius: 6,
  fontSize: 'var(--fs-caption)', fontFamily: MONO, background: 'var(--white)', color: 'var(--text-main)',
}
const pickMsg = { padding: '18px 10px', textAlign: 'center', color: 'var(--gray)', fontSize: 'var(--fs-caption)', fontFamily: MONO }
const pickFase = { fontFamily: MONO, fontSize: 'var(--fs-caption)', fontWeight: 600, padding: '1px 7px', borderRadius: 10, background: 'var(--gold)', color: 'var(--white)' }
const STATUSES = ['OPEN', 'COMPLETED', 'CANCELLED']
const SEASONS = ['SS', 'FW', 'CO', 'SP']
const PICK_PAGE = 40
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
  // Modal 3 — assignar model a una línia (B4b). Picker patró pàgina Models: cerca (codi/nom) +
  // filtres (temporada/col·lecció) + llista densa; filtre implícit pel customer de la comanda.
  const [assign, setAssign] = useState(null)               // { line } | null
  const [pq, setPq] = useState({ search: '', temporada: '', collection: '' })
  const [picker, setPicker] = useState({ models: [], count: 0, loading: false, modelId: '' })
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

  // Modal 3 — obre el picker de models (filtre implícit pel client de la comanda).
  const openAssign = (line) => {
    setFeedback(null)
    setPq({ search: '', temporada: '', collection: '' })
    setPicker({ models: [], count: 0, loading: true, modelId: '' })
    setAssign({ line })
  }
  // Cerca server-side amb debounce: recarrega quan canvien cerca/filtres (mai el flat de 2000).
  useEffect(() => {
    if (!assign) return
    const params = { customer: order.customer, ordering: '-data_entrada', page_size: PICK_PAGE }
    if (pq.search) params.search = pq.search
    if (pq.temporada) params.temporada = pq.temporada
    if (pq.collection) params.collection = pq.collection
    setPicker(p => ({ ...p, loading: true }))
    const id = setTimeout(() => {
      modelsApi.list(params)
        .then(res => {
          const d = res.data
          const list = Array.isArray(d) ? d : (d.results || [])
          setPicker(p => ({ ...p, models: list, count: d.count ?? list.length, loading: false }))
        })
        .catch(() => setPicker(p => ({ ...p, models: [], count: 0, loading: false })))
    }, 200)
    return () => clearTimeout(id)
  }, [assign, pq, order?.customer])

  // P4 — plega/desplega una línia; carrega l'expansió el primer cop (lazy).
  const toggleLine = (line) => {
    const id = line.id
    const isOpen = expanded.has(id)
    setExpanded(s => { const n = new Set(s); isOpen ? n.delete(id) : n.add(id); return n })
    if (!isOpen && !alloc[id]) {
      setAlloc(a => ({ ...a, [id]: { loading: true } }))
      commerce.orderLines.allocation(id)
        .then(res => setAlloc(a => ({ ...a, [id]: { data: res.data } })))
        .catch(() => setAlloc(a => ({ ...a, [id]: { error: true } })))
    }
  }

  const doAssign = () => {
    if (!picker.modelId) return
    setBusy(true); setFeedback(null)
    commerce.orderLines.assignModel(assign.line.id, { model_id: Number(picker.modelId) })
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
        <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, fontFamily: MONO }}>{order.document_number}</h1>
        <OrderStatusBadge status={order.status} t={t} />
        <span style={{ marginLeft: 'auto' }}>
          <PdfButton onClick={doPdf} disabled={busy} label={t('orders.download_pdf')} />
        </span>
      </div>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 16 }}>{order.customer_nom}</p>

      {canEdit && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)' }}>
            {t('orders.status')}:
            <select value={order.status} onChange={e => changeStatus(e.target.value)} disabled={busy} style={{ ...selS }}>
              {STATUSES.map(s => <option key={s} value={s}>{t(`orders.status_${s}`)}</option>)}
            </select>
          </label>
        </div>
      )}

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
        {lines.map(l => {
          const open = expanded.has(l.id)
          return (
            <div key={l.id}>
              <Row>
                <button onClick={() => toggleLine(l)} style={chevBtn}
                  title={t(open ? 'orders.collapse' : 'orders.expand')}>
                  <i className={`ti ti-chevron-${open ? 'down' : 'right'}`} style={{ fontSize: 14 }} />
                </button>
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
              {open && <LineExpansion a={alloc[l.id]} t={t} />}
            </div>
          )
        })}
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
            background: 'var(--white)', borderRadius: 12, padding: '1rem 1.2rem',
            maxWidth: 560, width: '100%', border: '0.5px solid var(--gray-l)',
            display: 'flex', flexDirection: 'column', maxHeight: '82vh',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 2, fontFamily: MONO }}>
              {t('orders.assign_title')}
            </h2>
            <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginBottom: 10 }}>
              {assign.line.description || assign.line.product_name}
            </p>

            {/* Toolbar de cerca + filtres (patró pàgina Models) */}
            <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
              <input value={pq.search} autoFocus onChange={e => setPq({ ...pq, search: e.target.value })}
                placeholder={t('orders.assign_search_ph')} style={{ ...pInp, flex: 1, minWidth: 160 }} />
              <select value={pq.temporada} onChange={e => setPq({ ...pq, temporada: e.target.value })} style={pInp}>
                <option value="">{t('orders.assign_all_seasons')}</option>
                {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <input value={pq.collection} onChange={e => setPq({ ...pq, collection: e.target.value })}
                placeholder={t('orders.assign_collection_ph')} style={{ ...pInp, width: 130 }} />
            </div>

            {/* Llista densa amb scroll — clic per seleccionar */}
            <div style={{ flex: 1, overflowY: 'auto', border: '0.5px solid var(--gray-l)', borderRadius: 8, minHeight: 120 }}>
              {picker.loading ? (
                <div style={pickMsg}>{t('orders.assign_loading')}</div>
              ) : picker.models.length === 0 ? (
                <div style={pickMsg}>{t('orders.assign_empty')}</div>
              ) : picker.models.map(m => {
                const sel = String(m.id) === String(picker.modelId)
                return (
                  <div key={m.id} onClick={() => setPicker(p => ({ ...p, modelId: m.id }))} style={{
                    display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', cursor: 'pointer',
                    borderBottom: '0.5px solid var(--bg-muted)',
                    background: sel ? 'var(--gold-pale)' : 'transparent',
                  }}>
                    <span style={{ fontFamily: MONO, fontWeight: 700, color: 'var(--gold)', fontSize: 'var(--fs-caption)' }}>{m.codi_intern}</span>
                    <span style={{ flex: 1, minWidth: 0, fontSize: 'var(--fs-caption)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.nom_prenda || '—'}</span>
                    <span style={pickFase}>{m.fase_actual ? t(`model_sheet.dashboard.phase.${m.fase_actual}`, m.fase_actual) : '—'}</span>
                    {sel && <i className="ti ti-check" style={{ fontSize: 13, color: 'var(--gold)' }} />}
                  </div>
                )
              })}
            </div>
            {!picker.loading && picker.count > picker.models.length && (
              <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--gray)', margin: '6px 0 0' }}>
                {t('orders.assign_more', { n: picker.count })}
              </p>
            )}

            {(() => {
              const sel = picker.models.find(m => String(m.id) === String(picker.modelId))
              return sel && !sel.garment_type_item_nom
                ? <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--gold)', margin: '8px 0 0' }}>
                    <i className="ti ti-alert-triangle" style={{ fontSize: 13, marginRight: 4 }} />{t('orders.assign_gti_warn')}</p>
                : null
            })()}
            <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: '8px 0 10px' }}>
              {t('orders.assign_migrate_note')}
            </p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setAssign(null)} disabled={busy} style={smallBtn}>{t('orders.assign_cancel')}</button>
              <button onClick={doAssign} disabled={busy || !picker.modelId} style={{ ...primaryBtn }}>{t('orders.assign_confirm')}</button>
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
function LineExpansion({ a, t }) {
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
const chevBtn = { background: 'none', border: 'none', cursor: 'pointer', color: 'var(--gray)', padding: '0 2px', display: 'flex', alignItems: 'center' }
const expBox = { padding: '10px 12px', margin: '0 0 2px', background: 'var(--bg-muted)', borderRadius: 8, fontSize: 'var(--fs-caption)' }
const expMuted = { fontSize: 'var(--fs-caption)', color: 'var(--gray)', fontFamily: MONO }
const expMeta = { fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', fontFamily: MONO }
const woPill = { fontFamily: MONO, fontSize: 'var(--fs-caption)', fontWeight: 600, padding: '0 6px', borderRadius: 10, border: '0.5px solid var(--gold)' }
const taskChip = { display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 8px', borderRadius: 12, background: 'var(--white)', border: '0.5px solid var(--gray-l)', fontSize: 'var(--fs-caption)', fontFamily: MONO }

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
