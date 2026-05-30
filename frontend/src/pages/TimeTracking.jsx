import { useState, useEffect } from 'react'
import { timers } from '../api/endpoints'
import TimerWidget from '../components/ui/TimerWidget'
import Card from '../components/ui/Card'

function format(secs) {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  return `${h}h ${String(m).padStart(2, '0')}m`
}

function diffMins(start, end) {
  const s = new Date(start).getTime()
  const e = end ? new Date(end).getTime() : Date.now()
  return Math.max(0, Math.floor((e - s) / 60000))
}

export default function TimeTracking() {
  const [allTimers, setAllTimers] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const loadTimers = () => {
    setLoading(true)
    timers.list({ page_size: 200, ordering: '-data_inici' })
      .then(res => setAllTimers(res.data.results || []))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadTimers()
  }, [])

  const actiu = allTimers.find(t => t.actiu || !t.data_fi)
  const today = new Date().toISOString().slice(0, 10)
  const dayTimers = allTimers.filter(t => {
    const d = (t.data_inici || t.created_at || '').slice(0, 10)
    return d === today && (t.data_fi || !t.actiu)
  })

  const closeActive = async () => {
    if (!actiu) return
    setSubmitting(true)
    try {
      await timers.tancar(actiu.id)
      loadTimers()
    } finally {
      setSubmitting(false)
    }
  }

  const last7Days = (() => {
    const days = []
    for (let i = 6; i >= 0; i--) {
      const d = new Date()
      d.setDate(d.getDate() - i)
      const key = d.toISOString().slice(0, 10)
      const mins = allTimers
        .filter(t => (t.data_inici || t.created_at || '').slice(0, 10) === key)
        .reduce((acc, t) => acc + diffMins(t.data_inici || t.created_at, t.data_fi), 0)
      days.push({ key, mins, label: d.toLocaleDateString('ca-ES', { weekday: 'short', day: 'numeric' }) })
    }
    return days
  })()

  const totalSetmana = last7Days.reduce((acc, d) => acc + d.mins, 0)
  const maxMins = Math.max(1, ...last7Days.map(d => d.mins))

  return (
    <div>
      <div style={{marginBottom: '1.5rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Temps</h1>
        <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
          Control de timers del tècnic
        </p>
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr',
        gap: '1.2rem', marginBottom: '1.2rem',
      }}>
        <Card title="Timer actiu" icon="ti-player-play" padding={0}>
          {loading ? (
            <div style={{padding: '2rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
              Carregant...
            </div>
          ) : !actiu ? (
            <div style={{
              padding: '3rem 1rem', textAlign: 'center',
              color: 'var(--gray)', fontSize: 13,
            }}>
              <i className="ti ti-clock-off" style={{fontSize: 32, display: 'block', marginBottom: 12, color: 'var(--gray-l)'}} />
              Cap tasca en curs
            </div>
          ) : (
            <>
              <TimerWidget
                tasca={actiu.tasca_nom || actiu.nom_tasca || `Tasca #${actiu.tasca}`}
                model={actiu.model_codi || actiu.model}
                inici={actiu.data_inici || actiu.created_at}
              />
              <div style={{
                display: 'flex', justifyContent: 'center',
                gap: '0.6rem', padding: '0 1rem 1.5rem',
              }}>
                <button disabled style={{
                  background: 'var(--white)', color: 'var(--gray)',
                  border: '0.5px solid #e4e4e2', borderRadius: 8,
                  padding: '8px 18px', fontSize: 12,
                  cursor: 'not-allowed', fontFamily: 'var(--font)',
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <i className="ti ti-player-pause" style={{fontSize: 14}} />
                  Pausa
                </button>
                <button
                  onClick={closeActive}
                  disabled={submitting}
                  style={{
                    background: submitting ? 'rgba(163,45,45,0.5)' : 'var(--err)',
                    color: 'white', border: 'none', borderRadius: 8,
                    padding: '8px 18px', fontSize: 12,
                    cursor: submitting ? 'not-allowed' : 'pointer',
                    fontFamily: 'var(--font)',
                    display: 'flex', alignItems: 'center', gap: 6,
                  }}
                >
                  <i className="ti ti-player-stop" style={{fontSize: 14}} />
                  {submitting ? 'Aturant...' : 'Aturar'}
                </button>
              </div>
            </>
          )}
        </Card>

        <Card title={`Avui (${dayTimers.length} entrades)`} icon="ti-calendar-event" padding={0}>
          {dayTimers.length === 0 ? (
            <div style={{padding: '2rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
              Sense entrades avui
            </div>
          ) : (
            <div>
              {dayTimers.map(t => (
                <div key={t.id} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '0.7rem 1.2rem',
                  borderBottom: '0.5px solid var(--gray-l)',
                  fontSize: 12,
                }}>
                  <div>
                    <div style={{marginBottom: 2}}>
                      <span style={{color: 'var(--gold)', fontWeight: 500, marginRight: 8}}>
                        {t.model_codi || t.model}
                      </span>
                      {t.tasca_nom || t.nom_tasca || `Tasca #${t.tasca}`}
                    </div>
                    <div style={{fontSize: 10, color: 'var(--gray)'}}>
                      {(t.data_inici || '').slice(11, 16)} – {(t.data_fi || '').slice(11, 16)}
                    </div>
                  </div>
                  <span style={{
                    fontSize: 12, fontWeight: 500,
                    fontVariantNumeric: 'tabular-nums',
                  }}>
                    {t.minuts ?? diffMins(t.data_inici || t.created_at, t.data_fi)}min
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title="Resum setmanal" icon="ti-chart-bar">
        <div style={{
          display: 'flex', alignItems: 'flex-end',
          justifyContent: 'space-between', gap: '0.6rem',
          height: 140, marginBottom: '1rem',
        }}>
          {last7Days.map(d => (
            <div key={d.key} style={{
              flex: 1, display: 'flex', flexDirection: 'column',
              alignItems: 'center', gap: 6,
            }}>
              <div style={{
                fontSize: 10, color: 'var(--gray)',
                fontVariantNumeric: 'tabular-nums',
              }}>
                {d.mins > 0 ? format(d.mins * 60) : '—'}
              </div>
              <div style={{
                width: '70%',
                height: `${(d.mins / maxMins) * 100}%`,
                minHeight: d.mins > 0 ? 4 : 0,
                background: d.mins > 0 ? 'var(--gold)' : 'var(--gray-l)',
                borderRadius: '4px 4px 0 0',
                transition: 'height 0.3s',
              }} />
              <div style={{fontSize: 10, color: 'var(--gray)', textTransform: 'capitalize'}}>
                {d.label}
              </div>
            </div>
          ))}
        </div>
        <div style={{
          borderTop: '0.5px solid var(--gray-l)',
          paddingTop: '0.8rem',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{fontSize: 11, color: 'var(--gray)'}}>Total setmanal</span>
          <span style={{
            fontSize: 22, fontWeight: 500, color: 'var(--gold)',
            fontVariantNumeric: 'tabular-nums',
          }}>
            {format(totalSetmana * 60)}
          </span>
        </div>
      </Card>
    </div>
  )
}
