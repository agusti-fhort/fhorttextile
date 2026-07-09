import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { commerce, customers as customersApi } from '../api/endpoints'
import Center from '../components/ui/Center'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'
import { selS, primaryBtn } from '../components/ui/buttons'

// Mòdul Comercial — B4c/v2 · Albarans (llista). L'albarà v2 es COMPON per model des de la safata
// d'albaranables d'un client ("Compondre albarà" → obre/crea el DRAFT del client). Cicle
// DRAFT→ISSUED→INVOICED. Plantilla Orders.jsx.
const MONO = 'IBM Plex Mono, monospace'
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const STATUSES = ['DRAFT', 'ISSUED', 'INVOICED']
const STATUS_VARIANT = { DRAFT: 'gold', ISSUED: 'ok', INVOICED: 'gate' }
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
  const [composeFor, setComposeFor] = useState('')   // customer id seleccionat al modal de composició
  const [composing, setComposing] = useState(false)
  const [showCompose, setShowCompose] = useState(false)

  const doCompose = () => {
    if (!composeFor) return
    setComposing(true)
    commerce.deliveryNotes.draft({ customer: composeFor })
      .then(res => navigate(`/comercial/albarans/${res.data.id}`))
      .catch(() => { setComposing(false); setError(true) })
  }

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
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('deliverynotes.title')}</h1>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('deliverynotes.subtitle')}</p>
        </div>
        <button onClick={() => { setComposeFor(''); setShowCompose(true) }} style={{ ...primaryBtn }}>
          <i className="ti ti-layout-grid-add" style={{ fontSize: 14, marginRight: 6 }} />{t('deliverynotes.compose_action')}
        </button>
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

      {showCompose && (
        <div onClick={() => !composing && setShowCompose(false)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--white)', borderRadius: 12, padding: '1.2rem 1.4rem',
            maxWidth: 460, width: '100%', border: '0.5px solid var(--gray-l)',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 6, fontFamily: MONO }}>
              {t('deliverynotes.compose_title')}
            </h2>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 14 }}>
              {t('deliverynotes.compose_hint')}
            </p>
            <select value={composeFor} onChange={e => setComposeFor(e.target.value)}
              style={{ ...selS, width: '100%', marginBottom: 16 }} disabled={composing}>
              <option value="">{t('deliverynotes.compose_pick_customer')}</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
            </select>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={doCompose} disabled={composing || !composeFor} style={{ ...primaryBtn }}>
                {t('deliverynotes.compose_confirm')}
              </button>
              <button onClick={() => setShowCompose(false)} disabled={composing} style={actBtn}>
                {t('deliverynotes.issue_cancel')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
