import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { models } from '../../api/endpoints'
import Table from '../ui/Table'

const MONO = 'IBM Plex Mono, monospace'
const fmt = (v) => v ? new Date(v).toLocaleString('ca-ES', { dateStyle: 'short', timeStyle: 'short' }) : '—'
const COLORS = { Done: '#3b6d11', InProgress: '#2a5a8a', Paused: 'var(--gold)', Cancelled: '#a32d2d', Pending: 'var(--gray)' }

// Pas 5B-fix · Afegit B — Log informatiu (read-only) de les transicions de tasques del model.
export default function TaskLog({ modelId }) {
  const { t } = useTranslation()
  const [log, setLog] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    models.taskLog(modelId)
      .then(r => setLog(r.data?.log ?? []))
      .catch(() => setLog([]))
      .finally(() => setLoading(false))
  }, [modelId])

  const columns = [
    { key: 'at', label: t('model_sheet.log_when'), render: r => fmt(r.at) },
    { key: 'task_type', label: t('model_sheet.log_task'), render: r => <span style={{ fontFamily: MONO }}>{r.task_type}</span> },
    { key: 'to_status', label: t('model_sheet.log_to'), render: r => <span style={{ fontWeight: 600, color: COLORS[r.to_status] || 'var(--text-main)', fontFamily: MONO, fontSize: 11 }}>{r.to_status}</span> },
    { key: 'by', label: t('model_sheet.log_who'), render: r => r.by || '—' },
  ]

  return (
    <div>
      <h3 style={{ fontSize: 13, fontWeight: 500, margin: '0 0 10px', fontFamily: MONO, color: 'var(--text-main)' }}>
        {t('model_sheet.task_log')}
      </h3>
      <Table columns={columns} data={log} loading={loading} empty={t('model_sheet.log_empty')} />
    </div>
  )
}
