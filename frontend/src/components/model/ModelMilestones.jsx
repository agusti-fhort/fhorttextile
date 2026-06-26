import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { calendar } from '../../api/endpoints'

// Properes fites del MODEL ACTUAL (arribada de proto / fitting / tasca) en els propers
// MILESTONES_DAYS dies, agrupades per dia. Reusa GET /calendar/events/ acotat amb model_id
// (filtre afegit a la Peça 1). Mateix patró de grouping que tenia el bloc del Dashboard, però
// amb l'estil del dashboard del model: capçalera sectionTitle (passada com a prop, font única),
// sense capsa per ítem, tokens DS. Estat buit discret.
const MONO = 'IBM Plex Mono, monospace'
const MILESTONES_DAYS = 14
const MILESTONE_ICON = { tasca: 'ti-subtask', confeccio: 'ti-building-factory', fitting: 'ti-ruler-2' }
// Mateix contenidor que els blocs germans del dashboard del model (rèplica EXACTA de `stateBox`
// a DashboardTab.jsx): filet --border, radius 8, padding, fons --bg-card. La capçalera
// (sectionTitle) va a FORA de la capsa, igual que fan ON SÓC / QUÈ TINC FET / AVISOS.
const box = {
  border: '0.5px solid var(--border)', borderRadius: 8, padding: '1rem 1.1rem',
  background: 'var(--bg-card)',
}

// Data local YYYY-MM-DD (no UTC) per acotar el rang de l'endpoint.
function localISO(d) {
  const z = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`
}

export default function ModelMilestones({ modelId, navigate, sectionTitle }) {
  const { t, i18n } = useTranslation()
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    const today = new Date()
    const end = new Date(); end.setDate(end.getDate() + MILESTONES_DAYS)
    calendar.events({ model_id: modelId, start: localISO(today), end: localISO(end) })
      .then(res => {
        if (!alive) return
        const events = res.data?.events ?? []
        // Agrupa per dia (prefix YYYY-MM-DD, vàlid tant per ISO datetime com per date-only).
        const byDay = {}
        events.forEach(ev => {
          if (!ev.start) return
          const day = ev.start.slice(0, 10)
          ;(byDay[day] ||= []).push(ev)
        })
        const sorted = Object.keys(byDay).sort().map(day => ({
          day,
          events: byDay[day].sort((a, b) => (a.start || '').localeCompare(b.start || '')),
        }))
        setGroups(sorted)
      })
      .catch(() => { if (alive) setGroups([]) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelId])

  const fmtDay = (day) => new Date(day + 'T00:00:00').toLocaleDateString(
    i18n.language || 'ca', { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <section>
      <div style={sectionTitle}>{t('model_sheet.dashboard.milestones.section')}</div>
      <div style={box}>
      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)', fontFamily: MONO }}>
          {t('model_sheet.loading')}
        </div>
      ) : groups.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)', fontStyle: 'italic' }}>
          {t('model_sheet.dashboard.milestones.empty')}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {groups.map(g => (
            <div key={g.day}>
              <div style={{ fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)',
                            textTransform: 'capitalize', marginBottom: 4 }}>
                {fmtDay(g.day)}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {g.events.map(ev => (
                  <button key={ev.id} type="button" onClick={() => ev.link && navigate(ev.link)} style={{
                    textAlign: 'left', width: '100%', border: 'none', background: 'transparent',
                    padding: '4px 0', cursor: ev.link ? 'pointer' : 'default',
                    display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-main)',
                  }}>
                    <i className={`ti ${MILESTONE_ICON[ev.tipus] || 'ti-point'}`}
                       style={{ fontSize: 15, color: ev.color || 'var(--gray)' }} />
                    <span style={{ flex: 1, fontSize: 'var(--fs-body)' }}>{ev.titol}</span>
                    <span style={{ fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)' }}>
                      {t(`model_sheet.dashboard.milestones.type.${ev.tipus}`, ev.tipus)}
                    </span>
                    {ev.en_risc && (
                      <span style={{ fontSize: 'var(--fs-label)', color: 'var(--err)', whiteSpace: 'nowrap' }}>
                        <i className="ti ti-alert-triangle" style={{ fontSize: 11 }} /> {t('model_sheet.dashboard.milestones.at_risk')}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      </div>
    </section>
  )
}
