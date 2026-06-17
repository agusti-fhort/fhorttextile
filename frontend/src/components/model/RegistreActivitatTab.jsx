import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import StatCard from '../ui/StatCard'
import Table from '../ui/Table'
import Badge from '../ui/Badge'

const API = import.meta.env.VITE_API_URL || ''
const MONO = 'IBM Plex Mono, monospace'
const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` })

const fmtDateTime = (v) => v ? new Date(v).toLocaleString('ca-ES', { dateStyle: 'medium', timeStyle: 'short' }) : '—'
const toHours = (m) => (m == null ? '—' : Math.round((m / 60) * 10) / 10 + ' h')

// Estat → variant de Badge (fallback gris).
const STATUS_VARIANT = {
  Done: 'ok', Completed: 'ok', Delivered: 'ok',
  InProgress: 'gold', Requested: 'gate',
  Blocked: 'err', Rectification: 'warn',
}

// 4.4 — Tab "Registre d'activitat" = albarà read-only del model (capçalera immutable,
// resum, passos, repartiment per tècnic, historial col·lapsable). Sense escriptura.
export default function RegistreActivitatTab({ modelId }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    let alive = true
    setLoading(true); setError(null)
    fetch(`${API}/api/v1/models/${modelId}/albara/`, { headers: authHeaders() })
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json() })
      .then(d => { if (alive) { setData(d); setLoading(false) } })
      .catch(e => { if (alive) { setError(e.message); setLoading(false) } })
    return () => { alive = false }
  }, [modelId])

  if (loading) {
    return <div style={{ padding: 24, color: 'var(--text-muted)', fontFamily: MONO }}>{t('common.loading')}</div>
  }
  if (error) {
    return <div style={{ padding: 24, color: 'var(--err, #c0392b)', fontFamily: MONO }}>{t('common.error')}: {error}</div>
  }

  // Estat NO meritat — encara no ha iniciat activitat.
  if (data && data.merited === false) {
    return (
      <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontFamily: MONO }}>
        <i className="ti ti-clock-off" style={{ fontSize: 32, display: 'block', marginBottom: 8 }} />
        {t('albara.notMerited')}
      </div>
    )
  }

  const { header, steps = [], totals = {}, per_technician = [], history = [] } = data || {}

  const stepCols = [
    { key: 'task_type', label: t('albara.taskType'), render: r => r.task_type || '—' },
    { key: 'status', label: t('albara.status'), render: r => <Badge variant={STATUS_VARIANT[r.status] || 'gray'}>{r.status || '—'}</Badge> },
    { key: 'minutes', label: t('albara.time'), align: 'right', render: r => toHours(r.minutes) },
    { key: 'started_at', label: t('albara.start'), render: r => fmtDateTime(r.started_at) },
    { key: 'finished_at', label: t('albara.end'), render: r => fmtDateTime(r.finished_at) },
  ]

  const techCols = [
    { key: 'label', label: t('albara.technician'), render: r => r.label || '—' },
    { key: 'minutes', label: t('albara.time'), align: 'right', render: r => toHours(r.minutes) },
  ]

  const historyCols = [
    { key: 'task_type', label: t('albara.taskType'), render: r => r.task_type || '—' },
    { key: 'transition', label: t('albara.status'), render: r => `${r.from ?? '—'} → ${r.to ?? '—'}` },
    { key: 'by', label: t('albara.technician'), render: r => r.by || '—' },
    { key: 'at', label: t('albara.end'), render: r => fmtDateTime(r.at) },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, fontFamily: MONO }}>
      {/* 1. Capçalera immutable */}
      <div style={{
        background: 'var(--bg-card, #fafafa)',
        border: '0.5px solid var(--border)',
        borderRadius: 8, padding: 16,
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16,
      }}>
        <div>
          <span style={{ color: 'var(--gold)', fontWeight: 600 }}>{header?.code}</span>
          {header?.name && <span style={{ marginLeft: 8 }}>{header.name}</span>}
        </div>
        <div style={{ textAlign: 'right', color: 'var(--text-muted)', fontSize: 13 }}>
          <div>{t('albara.period')}: {header?.period || '—'}</div>
          <div>{t('albara.meritedAt')}: {fmtDateTime(header?.merited_at)}</div>
        </div>
      </div>

      {/* 2. Resum — tres StatCard */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <StatCard icon="ti-clock" label={t('albara.totalTime')} value={toHours(totals.total_minutes)} />
        <StatCard icon="ti-list-check" label={t('albara.steps')} value={steps.length} />
        <StatCard icon="ti-rotate" label={t('albara.rectifications')} value={totals.rectifications ?? 0} />
      </div>

      {/* 3. Taula de passos */}
      <Table columns={stepCols} data={steps} empty={t('albara.notMerited')} />

      {/* 4. Repartiment per tècnic */}
      <Table columns={techCols} data={per_technician} empty="—" />

      {/* 5. Historial col·lapsable */}
      <div>
        <button
          onClick={() => setShowHistory(v => !v)}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--gold)', fontFamily: MONO, fontSize: 13,
            display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 0',
          }}>
          <i className={`ti ti-chevron-${showHistory ? 'up' : 'down'}`} />
          {t('albara.history')}
        </button>
        {showHistory && (
          <Table columns={historyCols} data={history} empty="—" />
        )}
      </div>
    </div>
  )
}
