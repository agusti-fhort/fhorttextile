import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { commerce } from '../api/endpoints'
import Center from '../components/ui/Center'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'

// Mòdul Comercial — D6 · Informe d'ENCÀRRECS ORFES (WO desassignats d'una línia de comanda):
// pendents de reassignar. Llistat simple read-only (sense filtres avançats). Font: work-orders/orphaned/.
const MONO = 'IBM Plex Mono, monospace'
const STATUS_VARIANT = { OPEN: 'gold', CLOSED: 'gray' }
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}

export default function OrphanedWorkOrders() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])

  useEffect(() => {
    let alive = true
    commerce.workOrders.orphaned()
      .then(res => { if (alive) setItems(res.data?.orphaned || []) })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString(i18n.language || 'ca',
    { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—'

  const columns = [
    { key: 'date', label: t('orphans.col_date'),
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{fmtDate(r.created_at)}</span> },
    { key: 'wo', label: t('orphans.col_wo'),
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.number}</span> },
    { key: 'model', label: t('orphans.col_model'),
      render: r => <span style={{ fontFamily: MONO, color: 'var(--gold)' }}>{r.model?.codi_intern || '—'}</span> },
    { key: 'customer', label: t('orphans.col_customer'), render: r => r.customer || '—' },
    { key: 'order', label: t('orphans.col_order'),
      render: r => <span style={{ fontFamily: MONO }}>{r.order?.document_number || '—'}</span> },
    { key: 'total', label: t('orphans.col_total'), align: 'right',
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{r.order?.total ?? '—'}</span> },
    { key: 'status', label: t('orphans.col_status'),
      render: r => <Badge variant={STATUS_VARIANT[r.status] || 'gray'}>{t(`workorders.status_${r.status}`, r.status)}</Badge> },
    { key: '_a', label: '', align: 'right', render: r => (
      r.order
        ? <button onClick={() => navigate(`/comercial/comandes/${r.order.id}`)} style={actBtn}>{t('orphans.open_order')}</button>
        : null
    ) },
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 1000 }}>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('orphans.title')}</h1>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('orphans.subtitle')}</p>
      </div>
      {loading ? <Center>{t('orphans.loading')}</Center>
        : error ? <Center>{t('orphans.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={items} loading={false} empty={t('orphans.empty')} />
            </div>
          )}
    </div>
  )
}
