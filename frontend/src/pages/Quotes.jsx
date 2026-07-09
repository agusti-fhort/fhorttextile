import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce, customers as customersApi } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'
import { selS, primaryBtn } from '../components/ui/buttons'

// Mòdul Comercial Studio — B2 · Ofertes (llista). Plantilla Products.jsx.
// Escriptura gated CONFIGURE (backend); el gate de tier del mòdul arriba a B5.
const MONO = 'IBM Plex Mono, monospace'
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}

const STATUSES = ['DRAFT', 'SENT', 'ACCEPTED', 'REJECTED', 'EXPIRED']
const STATUS_VARIANT = { DRAFT: 'gray', SENT: 'gold', ACCEPTED: 'ok', REJECTED: 'err', EXPIRED: 'warn' }

export function StatusBadge({ status, t }) {
  return <Badge variant={STATUS_VARIANT[status] || 'gray'}>{t(`quotes.status_${status}`)}</Badge>
}

const money = (v) => `${Number(v ?? 0).toFixed(2)} €`

export default function Quotes() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [customers, setCustomers] = useState([])
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [creating, setCreating] = useState(false)
  const [statusF, setStatusF] = useState('')
  const [customerF, setCustomerF] = useState('')

  const rows = (res) => res.data?.results ?? (Array.isArray(res.data) ? res.data : [])
  const fetchList = () => commerce.quotes.list({ ordering: '-created_at', page_size: 500 }).then(rows)

  const load = useCallback(() => {
    setError(false)
    return fetchList().then(setItems).catch(() => setError(true))
  }, [])

  useEffect(() => {
    let alive = true
    Promise.all([
      fetchList(),
      customersApi.list({ active: true, page_size: 500 }).then(rows).catch(() => []),
    ])
      .then(([qs, cs]) => { if (alive) { setItems(qs); setCustomers(cs) } })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  const remove = (q) => {
    if (!window.confirm(t('quotes.confirm_delete', { number: q.document_number }))) return
    setSaving(true); setFeedback(null)
    commerce.quotes.remove(q.id)
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('quotes.deleted') }))
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.detail || t('quotes.error') }))
      .finally(() => setSaving(false))
  }

  const shown = items.filter(q =>
    (!statusF || q.status === statusF) && (!customerF || String(q.customer) === String(customerF)))

  const columns = [
    { key: 'document_number', label: t('quotes.col_number'),
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.document_number}</span> },
    { key: 'customer', label: t('quotes.col_customer'), render: r => r.customer_nom },
    { key: 'status', label: t('quotes.col_status'), render: r => <StatusBadge status={r.status} t={t} /> },
    { key: 'total', label: t('quotes.col_total'), align: 'right',
      render: r => <span style={{ fontFamily: MONO }}>{money(r.total)}</span> },
    { key: 'created_at', label: t('quotes.col_created'),
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{(r.created_at || '').slice(0, 10)}</span> },
    { key: '_a', label: '', align: 'right', render: r => (
      <span style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
        <button onClick={() => navigate(`/comercial/ofertes/${r.id}`)} disabled={saving} style={actBtn}>{t('quotes.open')}</button>
        {canEdit && <button onClick={() => remove(r)} disabled={saving} style={{ ...actBtn, color: 'var(--err)', borderColor: 'var(--err)' }}>{t('quotes.delete')}</button>}
      </span>) },
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 1000 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('quotes.title')}</h1>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('quotes.subtitle')}</p>
        </div>
        {canEdit && (
          <button onClick={() => setCreating(true)} style={{ ...primaryBtn, marginLeft: 0 }}>
            <i className="ti ti-plus" style={{ fontSize: 14 }} />{t('quotes.new')}
          </button>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <select value={statusF} onChange={e => setStatusF(e.target.value)} style={{ ...selS }}>
          <option value="">{t('quotes.filter_status_all')}</option>
          {STATUSES.map(s => <option key={s} value={s}>{t(`quotes.status_${s}`)}</option>)}
        </select>
        <select value={customerF} onChange={e => setCustomerF(e.target.value)} style={{ ...selS }}>
          <option value="">{t('quotes.filter_customer_all')}</option>
          {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
        </select>
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('quotes.loading')}</Center>
        : error ? <Center>{t('quotes.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={shown} loading={false} empty={t('quotes.empty')} />
            </div>
          )}

      {creating && (
        <NewQuoteModal customers={customers} t={t}
          onCancel={() => setCreating(false)}
          onCreated={(id) => navigate(`/comercial/ofertes/${id}`)}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </div>
  )
}

function NewQuoteModal({ customers, t, onCancel, onCreated, onError }) {
  const [customer, setCustomer] = useState('')
  const [validUntil, setValidUntil] = useState('')
  const [busy, setBusy] = useState(false)
  const invalid = !customer

  const submit = () => {
    if (invalid) { onError(t('quotes.required')); return }
    setBusy(true)
    commerce.quotes.create({ customer, valid_until: validUntil || null })
      .then(res => onCreated(res.data.id))
      .catch(e => onError(e?.response?.data?.detail || t('quotes.error')))
      .finally(() => setBusy(false))
  }

  return (
    <Modal title={t('quotes.new_title')} cancelLabel={t('quotes.cancel')} confirmLabel={t('quotes.create')}
      onCancel={onCancel} onConfirm={submit} confirmDisabled={busy || invalid}>
      <div style={{ marginBottom: 14 }}>
        <label style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{t('quotes.customer')}</label>
        <select value={customer} onChange={e => setCustomer(e.target.value)} style={{ ...selS, width: '100%' }}>
          <option value="">{t('quotes.select_customer')}</option>
          {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
        </select>
      </div>
      <div style={{ marginBottom: 4 }}>
        <label style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{t('quotes.valid_until')}</label>
        <input type="date" value={validUntil} onChange={e => setValidUntil(e.target.value)} style={{ ...selS, width: '100%' }} />
      </div>
    </Modal>
  )
}
