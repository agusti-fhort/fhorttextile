import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { commerce, customers as customersApi } from '../api/endpoints'
import Center from '../components/ui/Center'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'
import { selS } from '../components/ui/buttons'

// Mòdul Comercial — B4c · Albarans (llista). Document derivat que agrega 1..N WorkOrder CLOSED
// del mateix client. No es creen aquí: neixen de "Generar albarà" a la fitxa d'Encàrrec.
// Plantilla Orders.jsx.
const MONO = 'IBM Plex Mono, monospace'
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const STATUSES = ['DRAFT', 'ISSUED']
const STATUS_VARIANT = { DRAFT: 'gold', ISSUED: 'ok' }
const money = (v) => `${Number(v ?? 0).toFixed(2)} €`

export function DNStatusBadge({ status, t }) {
  return <Badge variant={STATUS_VARIANT[status] || 'gray'}>{t(`deliverynotes.status_${status}`)}</Badge>
}

export default function DeliveryNotes() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [customers, setCustomers] = useState([])
  const [statusF, setStatusF] = useState('')
  const [customerF, setCustomerF] = useState('')

  const rows = (res) => res.data?.results ?? (Array.isArray(res.data) ? res.data : [])
  const fetchList = useCallback(() => commerce.deliveryNotes.list({ ordering: '-created_at', page_size: 500 }).then(rows), [])

  useEffect(() => {
    let alive = true
    Promise.all([
      fetchList(),
      customersApi.list({ active: true, page_size: 500 }).then(rows).catch(() => []),
    ])
      .then(([ds, cs]) => { if (alive) { setItems(ds); setCustomers(cs) } })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [fetchList])

  const shown = items.filter(d =>
    (!statusF || d.status === statusF) && (!customerF || String(d.customer) === String(customerF)))

  const columns = [
    { key: 'document_number', label: t('deliverynotes.col_number'),
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.document_number}</span> },
    { key: 'customer', label: t('deliverynotes.col_customer'), render: r => r.customer_nom },
    { key: 'status', label: t('deliverynotes.col_status'), render: r => <DNStatusBadge status={r.status} t={t} /> },
    { key: 'total', label: t('deliverynotes.col_total'), align: 'right',
      render: r => <span style={{ fontFamily: MONO }}>{money(r.total)}</span> },
    { key: 'date', label: t('deliverynotes.col_date'),
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{(r.issued_at || r.created_at || '').slice(0, 10)}</span> },
    { key: '_a', label: '', align: 'right', render: r => (
      <button onClick={() => navigate(`/comercial/albarans/${r.id}`)} style={actBtn}>{t('deliverynotes.open')}</button>
    ) },
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 1000 }}>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('deliverynotes.title')}</h1>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('deliverynotes.subtitle')}</p>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <select value={statusF} onChange={e => setStatusF(e.target.value)} style={{ ...selS }}>
          <option value="">{t('deliverynotes.filter_status_all')}</option>
          {STATUSES.map(s => <option key={s} value={s}>{t(`deliverynotes.status_${s}`)}</option>)}
        </select>
        <select value={customerF} onChange={e => setCustomerF(e.target.value)} style={{ ...selS }}>
          <option value="">{t('deliverynotes.filter_customer_all')}</option>
          {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
        </select>
      </div>

      {loading ? <Center>{t('deliverynotes.loading')}</Center>
        : error ? <Center>{t('deliverynotes.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={shown} loading={false} empty={t('deliverynotes.empty')} />
            </div>
          )}
    </div>
  )
}
