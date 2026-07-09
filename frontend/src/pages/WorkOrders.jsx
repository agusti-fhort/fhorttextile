import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { commerce, customers as customersApi } from '../api/endpoints'
import Center from '../components/ui/Center'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'
import { selS } from '../components/ui/buttons'

// Mòdul Comercial — B4a · Encàrrecs / ordres de treball (llista). Contenidors d'execució: ORDER
// (encàrrec d'un model) i COLLECTOR (col·lector mensual per client). No es creen aquí (ORDER =
// wizard B4b, COLLECTOR = hook lazy). Plantilla Orders.jsx.
const MONO = 'IBM Plex Mono, monospace'
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const KINDS = ['ORDER', 'COLLECTOR']
const STATUSES = ['OPEN', 'CLOSED']
const STATUS_VARIANT = { OPEN: 'gold', CLOSED: 'gray' }
const KIND_VARIANT = { ORDER: 'ok', COLLECTOR: 'warn' }

export function WOStatusBadge({ status, t }) {
  return <Badge variant={STATUS_VARIANT[status] || 'gray'}>{t(`workorders.status_${status}`)}</Badge>
}
export function WOKindBadge({ kind, t }) {
  return <Badge variant={KIND_VARIANT[kind] || 'gray'}>{t(`workorders.kind_${kind}`)}</Badge>
}

export default function WorkOrders() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [customers, setCustomers] = useState([])
  const [kindF, setKindF] = useState('')
  const [statusF, setStatusF] = useState('')
  const [customerF, setCustomerF] = useState('')

  const rows = (res) => res.data?.results ?? (Array.isArray(res.data) ? res.data : [])
  const fetchList = useCallback(() => commerce.workOrders.list({ page_size: 500 }).then(rows), [])

  useEffect(() => {
    let alive = true
    Promise.all([
      fetchList(),
      customersApi.list({ active: true, page_size: 500 }).then(rows).catch(() => []),
    ])
      .then(([ws, cs]) => { if (alive) { setItems(ws); setCustomers(cs) } })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [fetchList])

  const shown = items.filter(w =>
    (!kindF || w.kind === kindF) && (!statusF || w.status === statusF) &&
    (!customerF || String(w.customer) === String(customerF)))

  const columns = [
    { key: 'number', label: t('workorders.col_number'),
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.number}</span> },
    { key: 'kind', label: t('workorders.col_kind'), render: r => <WOKindBadge kind={r.kind} t={t} /> },
    { key: 'customer', label: t('workorders.col_customer'), render: r => r.customer_nom },
    { key: 'target', label: t('workorders.col_target'),
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{r.kind === 'COLLECTOR' ? r.period : (r.model_codi || '—')}</span> },
    { key: 'status', label: t('workorders.col_status'), render: r => <WOStatusBadge status={r.status} t={t} /> },
    { key: 'n_tasks', label: t('workorders.col_tasks'), align: 'right',
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{r.n_tasks ?? 0}</span> },
    { key: '_a', label: '', align: 'right', render: r => (
      <button onClick={() => navigate(`/comercial/encarrecs/${r.id}`)} style={actBtn}>{t('workorders.open')}</button>
    ) },
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 1000 }}>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('workorders.title')}</h1>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('workorders.subtitle')}</p>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <select value={kindF} onChange={e => setKindF(e.target.value)} style={{ ...selS }}>
          <option value="">{t('workorders.filter_kind_all')}</option>
          {KINDS.map(k => <option key={k} value={k}>{t(`workorders.kind_${k}`)}</option>)}
        </select>
        <select value={statusF} onChange={e => setStatusF(e.target.value)} style={{ ...selS }}>
          <option value="">{t('workorders.filter_status_all')}</option>
          {STATUSES.map(s => <option key={s} value={s}>{t(`workorders.status_${s}`)}</option>)}
        </select>
        <select value={customerF} onChange={e => setCustomerF(e.target.value)} style={{ ...selS }}>
          <option value="">{t('workorders.filter_customer_all')}</option>
          {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
        </select>
      </div>

      {loading ? <Center>{t('workorders.loading')}</Center>
        : error ? <Center>{t('workorders.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={shown} loading={false} empty={t('workorders.empty')} />
            </div>
          )}
    </div>
  )
}
