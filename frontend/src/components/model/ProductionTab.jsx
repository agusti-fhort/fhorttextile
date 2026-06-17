import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { productions } from '../../api/endpoints'
import Table from '../ui/Table'

const MONO = 'IBM Plex Mono, monospace'
const fmtDate = (v) => v ? new Date(v).toLocaleDateString('ca-ES', { dateStyle: 'medium' }) : '—'

// Pas 5B-fix · TRAM 3 — Tab Producció = LOG. Llista les Production del model. L'alta ("Enviar a
// confecció") viu al desplegable Accions; aquí només es gestiona l'ESTAT (confirmar recepció).
export default function ProductionTab({ model, onFeedback, onChanged }) {
  const { t } = useTranslation()
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    productions.list({ model: model.id, ordering: '-requested_at', page_size: 200 })
      .then(r => setList(r.data?.results ?? r.data ?? []))
      .catch(() => setList([]))
      .finally(() => setLoading(false))
  }, [model.id])

  useEffect(() => { load() }, [load])

  const setStatus = async (prod, status) => {
    try {
      await productions.setStatus(prod.id, { status })
      onFeedback({ type: 'ok', text: t('model_sheet.status_changed') })
      load(); onChanged && onChanged()
    } catch (e) {
      onFeedback({ type: 'err', text: e.response?.data?.error || t('model_sheet.action_error') })
    }
  }

  const columns = [
    { key: 'supplier_name', label: t('model_sheet.supplier') },
    { key: 'phase', label: t('model_sheet.phase') },
    { key: 'status', label: t('model_sheet.status'), render: r => <StatusBadge status={r.status} /> },
    { key: 'requested_at', label: t('model_sheet.requested_at'), render: r => fmtDate(r.requested_at) },
    { key: 'expected_at', label: t('model_sheet.expected_at'), render: r => fmtDate(r.expected_at) },
    { key: 'delivered_at', label: t('model_sheet.delivered_at'), render: r => fmtDate(r.delivered_at) },
    {
      key: 'actions', label: '', align: 'right', render: r => (
        <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
          {r.status === 'Requested' && (
            <button style={miniBtn} onClick={() => setStatus(r, 'InProgress')}>{t('model_sheet.mark_inprogress')}</button>
          )}
          {(r.status === 'Requested' || r.status === 'InProgress') && (
            <button style={miniBtn} onClick={() => setStatus(r, 'Delivered')}>{t('model_sheet.mark_delivered')}</button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, margin: '0 0 14px', fontFamily: MONO }}>{t('model_sheet.production_title')}</h2>
      <Table columns={columns} data={list} loading={loading} empty={t('model_sheet.no_productions')} />
    </div>
  )
}

const STATUS_COLORS = { Requested: 'var(--gold)', InProgress: '#2a5a8a', Delivered: '#3b6d11' }
function StatusBadge({ status }) {
  return <span style={{ fontSize: 'var(--fs-body)', fontWeight: 600, color: STATUS_COLORS[status] || 'var(--gray)', fontFamily: MONO }}>{status}</span>
}
const miniBtn = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '3px 8px', borderRadius: 4, cursor: 'pointer',
  background: 'var(--white)', color: 'var(--text-main)', border: '0.5px solid var(--gray-l)',
}
