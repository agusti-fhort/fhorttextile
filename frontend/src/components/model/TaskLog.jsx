import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { models } from '../../api/endpoints'
import Table from '../ui/Table'

const MONO = 'IBM Plex Mono, monospace'
const fmt = (v) => v ? new Date(v).toLocaleString('ca-ES', { dateStyle: 'short', timeStyle: 'short' }) : '—'
const COLORS = { Done: '#3b6d11', InProgress: '#2a5a8a', Paused: 'var(--gold)', Cancelled: '#a32d2d', Pending: 'var(--gray)' }

// TaskTransition.auto: null = gest del tècnic; slug = el guard que ha actuat. Un slug futur
// que encara no tingui clau es mostra tal qual (prefixat) en comptes de desaparèixer.
const AUTO_I18N = {
  guard_30min: 'guard_tasca.log_auto_guard',
  cron_40min: 'guard_tasca.log_auto_cron',
  exclusio_inprogress: 'guard_tasca.log_auto_exclusio',
}
const etiquetaAuto = (t, auto) =>
  AUTO_I18N[auto] ? t(AUTO_I18N[auto]) : `auto · ${auto}`

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
    { key: 'to_status', label: t('model_sheet.log_to'), render: r => <span style={{ fontWeight: 600, color: COLORS[r.to_status] || 'var(--text-main)', fontFamily: MONO, fontSize: 'var(--fs-body)' }}>{r.to_status}</span> },
    // Qui: `by` sol és mentida quan la transició la va fer un guard — el nom del tècnic hi
    // consta perquè la tasca era seva, no perquè ell l'hagués pausada. La marca ho desfà.
    { key: 'by', label: t('model_sheet.log_who'), render: r => (
      <span>
        {r.by || '—'}
        {r.auto && (
          <span style={{ marginLeft: 6, fontFamily: MONO, fontSize: 'var(--fs-caption, 11px)',
                         color: 'var(--gold)', whiteSpace: 'nowrap' }}>
            {etiquetaAuto(t, r.auto)}
          </span>
        )}
      </span>
    ) },
  ]

  return (
    <div>
      <h3 style={{ fontSize: 'var(--fs-body)', fontWeight: 500, margin: '0 0 10px', fontFamily: MONO, color: 'var(--text-main)' }}>
        {t('model_sheet.task_log')}
      </h3>
      <Table columns={columns} data={log} loading={loading} empty={t('model_sheet.log_empty')} />
    </div>
  )
}
