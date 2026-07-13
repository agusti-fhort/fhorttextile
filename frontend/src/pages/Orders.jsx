import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { commerce, customers as customersApi } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'
import { selS } from '../components/ui/buttons'

// Mòdul Comercial — B3b · Comandes de venda (llista). Les comandes neixen de la conversió d'una
// oferta (irreversible); aquí només es consulten. Plantilla Quotes.jsx.
const MONO = 'IBM Plex Mono, monospace'
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const STATUSES = ['OPEN', 'COMPLETED', 'CANCELLED']
const STATUS_VARIANT = { OPEN: 'gold', COMPLETED: 'ok', CANCELLED: 'err' }
const money = (v) => `${Number(v ?? 0).toFixed(2)} €`

export function OrderStatusBadge({ status, t }) {
  return <Badge variant={STATUS_VARIANT[status] || 'gray'}>{t(`orders.status_${status}`)}</Badge>
}

// % imputat = Σ qty_allocated / Σ quantity (control de cartera). Sense línies → 0%.
export function allocatedPct(order) {
  const lines = order?.lines || []
  const ordered = lines.reduce((s, l) => s + Number(l.quantity || 0), 0)
  if (ordered <= 0) return 0
  const allocated = lines.reduce((s, l) => s + Number(l.qty_allocated || 0), 0)
  return Math.round((allocated / ordered) * 100)
}

export default function Orders() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [customers, setCustomers] = useState([])
  const [feedback, setFeedback] = useState(null)
  const [statusF, setStatusF] = useState('')
  const [customerF, setCustomerF] = useState('')

  const rows = (res) => res.data?.results ?? (Array.isArray(res.data) ? res.data : [])
  const fetchList = () => commerce.orders.list({ ordering: '-created_at', page_size: 500 }).then(rows)

  useEffect(() => {
    let alive = true
    Promise.all([
      fetchList(),
      customersApi.list({ active: true, page_size: 500 }).then(rows).catch(() => []),
    ])
      .then(([os, cs]) => { if (alive) { setItems(os); setCustomers(cs) } })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  const shown = items.filter(o =>
    (!statusF || o.status === statusF) && (!customerF || String(o.customer) === String(customerF)))

  const columns = [
    { key: 'document_number', label: t('orders.col_number'),
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.document_number}</span> },
    { key: 'customer', label: t('orders.col_customer'), render: r => r.customer_nom },
    { key: 'status', label: t('orders.col_status'), render: r => <OrderStatusBadge status={r.status} t={t} /> },
    { key: 'allocated', label: t('orders.col_allocated'), align: 'right',
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{allocatedPct(r)}%</span> },
    { key: 'total', label: t('orders.col_total'), align: 'right',
      render: r => <span style={{ fontFamily: MONO }}>{money(r.total)}</span> },
    { key: 'created_at', label: t('orders.col_created'),
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{(r.created_at || '').slice(0, 10)}</span> },
    { key: '_a', label: '', align: 'right', render: r => (
      <button onClick={() => navigate(`/comercial/comandes/${r.id}`)} style={actBtn}>{t('orders.open')}</button>
    ) },
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 1000 }}>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('orders.title')}</h1>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('orders.subtitle')}</p>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <select value={statusF} onChange={e => setStatusF(e.target.value)} style={{ ...selS }}>
          <option value="">{t('orders.filter_status_all')}</option>
          {STATUSES.map(s => <option key={s} value={s}>{t(`orders.status_${s}`)}</option>)}
        </select>
        <select value={customerF} onChange={e => setCustomerF(e.target.value)} style={{ ...selS }}>
          <option value="">{t('orders.filter_customer_all')}</option>
          {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
        </select>
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('orders.loading')}</Center>
        : error ? <Center>{t('orders.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={shown} loading={false} empty={t('orders.empty')} />
            </div>
          )}
    </div>
  )
}
