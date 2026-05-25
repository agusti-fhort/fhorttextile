import { useState, useEffect } from 'react'
import { tasks, timers, me } from '../api/endpoints'
import TimerWidget from '../components/ui/TimerWidget'
import Badge from '../components/ui/Badge'

const COLUMNES = [
  { key: 'Pendent',    label: 'Pendent',    color: 'var(--gray)',  icon: 'ti-clock' },
  { key: 'EnCurs',     label: 'En curs',    color: 'var(--warn)',  icon: 'ti-player-play' },
  { key: 'Feta',       label: 'Feta',       color: 'var(--ok)',    icon: 'ti-circle-check' },
  { key: 'Bloquejada', label: 'Bloquejada', color: 'var(--err)',   icon: 'ti-lock' },
]

export default function KanbanTasques() {
  const [all, setAll] = useState([])
  const [activeTimers, setActiveTimers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      me.get().catch(() => null),
      timers.list({ actiu: true, page_size: 50 }).catch(() => ({ data: { results: [] } })),
    ]).then(([meRes, tRes]) => {
      const responsable = meRes?.data?.id
      setActiveTimers(tRes.data.results || [])
      const params = { page_size: 200 }
      if (responsable) params.responsable = responsable
      return tasks.list(params)
    }).then(res => {
      setAll(res.data.results || [])
    }).finally(() => setLoading(false))
  }, [])

  const timerForTask = (taskId) =>
    activeTimers.find(t => String(t.tasca) === String(taskId) || String(t.model_tasca) === String(taskId))

  return (
    <div>
      <div style={{marginBottom: '1.5rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Kanban de tasques</h1>
        <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
          Les meves tasques organitzades per estat
        </p>
      </div>

      {loading ? (
        <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
          Carregant...
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1rem',
        }}>
          {COLUMNES.map(col => {
            const items = all.filter(t => t.estat === col.key)
            return (
              <div key={col.key} style={{
                background: 'var(--white)',
                border: '0.5px solid #e4e4e2',
                borderRadius: 12,
                overflow: 'hidden',
                display: 'flex', flexDirection: 'column',
                minHeight: 360,
              }}>
                <div style={{
                  padding: '0.8rem 1rem',
                  borderBottom: '0.5px solid #e4e4e2',
                  display: 'flex', alignItems: 'center', gap: 8,
                  background: 'var(--gray-l)',
                }}>
                  <i className={`ti ${col.icon}`} style={{fontSize: 14, color: col.color}} />
                  <span style={{fontSize: 12, fontWeight: 500}}>{col.label}</span>
                  <span style={{
                    marginLeft: 'auto', fontSize: 11, color: 'var(--gray)',
                    padding: '2px 8px', borderRadius: 10,
                    background: 'var(--white)',
                  }}>
                    {items.length}
                  </span>
                </div>
                <div style={{flex: 1, padding: '0.6rem', display: 'flex', flexDirection: 'column', gap: 6}}>
                  {items.length === 0 ? (
                    <div style={{
                      fontSize: 11, color: 'var(--gray)', textAlign: 'center',
                      padding: '1.5rem', fontWeight: 300,
                    }}>
                      Sense tasques
                    </div>
                  ) : items.map(t => {
                    const timer = col.key === 'EnCurs' ? timerForTask(t.id) : null
                    return (
                      <div key={t.id} style={{
                        border: '0.5px solid var(--gray-l)',
                        borderRadius: 8,
                        padding: '0.7rem 0.8rem',
                        background: 'var(--white)',
                      }}>
                        <div style={{
                          display: 'flex', alignItems: 'center',
                          justifyContent: 'space-between', marginBottom: 4,
                        }}>
                          <span style={{fontSize: 11, color: 'var(--gold)', fontWeight: 500}}>
                            {t.model_codi || t.model}
                          </span>
                          {t.es_gate && <Badge variant="gate" icon="ti-flag">GATE</Badge>}
                        </div>
                        <div style={{fontSize: 12, marginBottom: 6, lineHeight: 1.4}}>
                          {t.nom_tasca || t.tasca}
                        </div>
                        <div style={{
                          display: 'flex', alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: 10, color: 'var(--gate)',
                        }}>
                          <span>{t.fase || '—'}</span>
                          {timer && <TimerWidget inici={timer.data_inici || timer.created_at} compact />}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
