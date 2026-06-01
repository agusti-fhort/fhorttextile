import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { modelTasks } from '../api/endpoints'
import TimerWidget from '../components/ui/TimerWidget'

// Tram 4 — Kanban únic (reconstruït sobre l'API nova). Peça A: tauler read + timer viu.
// El backend ja acota per row-level scope (sense view_team_tasks → només les pròpies).
// Estats reals de ModelTask: Pending / Paused / InProgress / Done.

const COLUMNS = [
  { key: 'Pending',    icon: 'ti-inbox',        color: 'var(--gray)' },
  { key: 'Paused',     icon: 'ti-player-pause', color: 'var(--warn)' },
  { key: 'InProgress', icon: 'ti-player-play',  color: 'var(--gold)' },
  { key: 'Done',       icon: 'ti-circle-check', color: 'var(--ok)' },
]

// Segueix la paginació de DRF (PAGE_SIZE=25, sense override) per no truncar tasques/models.
async function fetchAllPages(apiFn) {
  const out = []
  let page = 1
  for (;;) {
    const res = await apiFn({ page })
    const data = res.data
    out.push(...(data?.results ?? (Array.isArray(data) ? data : [])))
    if (data?.next) page++
    else break
  }
  return out
}

export default function KanbanTasks() {
  const { t } = useTranslation()
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchAll = useCallback(() => {
    setLoading(true)
    fetchAllPages(modelTasks.list)
      .then(setTasks)
      .catch(() => setTasks([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  return (
    <div style={{ minWidth: 0, maxWidth: '100%' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>{t('kanban.title')}</h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('kanban.subtitle')}</p>
      </div>

      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>
          {t('kanban.loading')}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
          {COLUMNS.map(col => {
            const items = tasks.filter(tk => tk.status === col.key)
            return (
              <div key={col.key} style={{
                background: 'var(--white)', border: '0.5px solid #e4e4e2', borderRadius: 12,
                overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 360,
              }}>
                <div style={{
                  padding: '0.8rem 1rem', borderBottom: '0.5px solid #e4e4e2',
                  display: 'flex', alignItems: 'center', gap: 8, background: 'var(--gray-l)',
                }}>
                  <i className={`ti ${col.icon}`} style={{ fontSize: 14, color: col.color }} />
                  <span style={{ fontSize: 12, fontWeight: 500 }}>{t(`kanban.status.${col.key}`)}</span>
                  <span style={{
                    marginLeft: 'auto', fontSize: 11, color: 'var(--gray)',
                    padding: '2px 8px', borderRadius: 10, background: 'var(--white)',
                  }}>{items.length}</span>
                </div>
                <div style={{ flex: 1, padding: '0.6rem', display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {items.length === 0 ? (
                    <div style={{ fontSize: 11, color: 'var(--gray)', textAlign: 'center', padding: '1.5rem', fontWeight: 300 }}>
                      {t('kanban.empty_col')}
                    </div>
                  ) : items.map(tk => (
                    <TaskCard key={tk.id} task={tk} />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function TaskCard({ task }) {
  return (
    <div style={{
      border: '0.5px solid var(--gray-l)', borderRadius: 8,
      padding: '0.7rem 0.8rem', background: 'var(--white)',
    }}>
      <div style={{ fontSize: 11, color: 'var(--gold)', fontWeight: 500, marginBottom: 4 }}>
        {task.model_codi || `#${task.model}`}
      </div>
      <div style={{ fontSize: 12, lineHeight: 1.4 }}>
        {task.task_type_name || task.task_type_code}
      </div>
      {task.status === 'InProgress' && task.started_at && (
        <div style={{ marginTop: 6 }}>
          <TimerWidget inici={task.started_at} compact />
        </div>
      )}
    </div>
  )
}
