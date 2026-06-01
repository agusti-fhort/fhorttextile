import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
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

// Transicions vàlides (mirall d'ALLOWED al backend services_c.py). Done→InProgress = rectificació.
const ACTIONS = {
  Pending:    [{ to: 'InProgress', key: 'start',  icon: 'ti-player-play-filled' }],
  Paused:     [{ to: 'InProgress', key: 'resume', icon: 'ti-player-play-filled' }],
  InProgress: [{ to: 'Paused', key: 'pause', icon: 'ti-player-pause-filled' },
               { to: 'Done', key: 'finish', icon: 'ti-check' }],
  Done:       [{ to: 'InProgress', key: 'reopen', icon: 'ti-rotate-clockwise' }],
}

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
  const user = useAuthStore(s => s.user)
  const canExecute = !!user?.capabilities?.includes('execute_tasks')
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)   // { type, text }
  const toastTimer = useRef(null)

  function showToast(type, text) {
    setToast({ type, text })
    if (toastTimer.current) clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 3000)
  }

  const fetchAll = useCallback(() => {
    setLoading(true)
    fetchAllPages(modelTasks.list)
      .then(setTasks)
      .catch(() => setTasks([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  function doTransition(task, toStatus) {
    modelTasks.transition(task.id, { to_status: toStatus })
      .then(res => {
        const pausedId = res.data?.paused_task_id
        if (pausedId) {
          const p = tasks.find(x => x.id === pausedId)
          const name = p ? `${p.model_codi || '#' + p.model} · ${p.task_type_name || p.task_type_code}` : `#${pausedId}`
          showToast('warn', t('kanban.toast_paused', { name }))
        }
        fetchAll()
      })
      .catch(err => {
        const msg = err?.response?.data?.error
          || (err?.response?.status === 403 ? t('kanban.not_allowed') : t('kanban.transition_error'))
        showToast('err', msg)
      })
  }

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
                    <TaskCard key={tk.id} task={tk} canExecute={canExecute} onTransition={doTransition} t={t} />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', zIndex: 60,
          fontSize: 12, padding: '10px 16px', borderRadius: 8, boxShadow: '0 6px 24px rgba(0,0,0,0.18)',
          background: toast.type === 'err' ? 'var(--err-bg)' : toast.type === 'warn' ? 'var(--warn-bg)' : 'var(--ok-bg)',
          color: toast.type === 'err' ? 'var(--err)' : toast.type === 'warn' ? 'var(--warn)' : 'var(--ok)',
        }}>{toast.text}</div>
      )}
    </div>
  )
}

function TaskCard({ task, canExecute, onTransition, t }) {
  const actions = ACTIONS[task.status] || []
  return (
    <div style={{
      border: '0.5px solid var(--gray-l)', borderRadius: 8,
      padding: '0.7rem 0.8rem', background: 'var(--white)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: 'var(--gold)', fontWeight: 500 }}>
          {task.model_codi || `#${task.model}`}
        </span>
        {task.rectifications > 0 && (
          <span title={t('kanban.rect', { n: task.rectifications })} style={{
            fontSize: 10, color: 'var(--warn)', background: 'var(--warn-bg)',
            padding: '1px 6px', borderRadius: 8, whiteSpace: 'nowrap',
          }}>
            <i className="ti ti-rotate-clockwise" style={{ fontSize: 10 }} /> {task.rectifications}
          </span>
        )}
      </div>
      <div style={{ fontSize: 12, lineHeight: 1.4 }}>
        {task.task_type_name || task.task_type_code}
      </div>
      {task.status === 'InProgress' && task.started_at && (
        <div style={{ marginTop: 6 }}>
          <TimerWidget inici={task.started_at} compact />
        </div>
      )}
      {canExecute && actions.length > 0 && (
        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
          {actions.map(a => (
            <button key={a.key} onClick={() => onTransition(task, a.to)} style={{
              display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, padding: '4px 8px',
              borderRadius: 6, border: '0.5px solid var(--gray-l)', background: 'var(--white)',
              cursor: 'pointer', color: 'var(--text-main)',
            }}>
              <i className={`ti ${a.icon}`} style={{ fontSize: 12 }} />
              {t(`kanban.action.${a.key}`)}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
