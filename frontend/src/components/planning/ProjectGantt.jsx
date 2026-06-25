import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { plan } from '../../api/endpoints'
import Center from '../ui/Center'

// Calendari-Gantt de projecte (LECTURA): UNA barra per model, eix=DIES. Consumeix GET plan/gantt/.
// Drag-ready: les barres es posicionen per data absoluta (x = dies des de l'inici del rang) → afegir
// el drag de prioritats (M-assist) després només cal sobre aquesta capa, sense reescriure-la.
// Tokens del DS (no canvas). CONVIU amb el tab "Calendari" (PlanningCalendar, executor/hores).
const MONO = 'IBM Plex Mono, monospace'
const LABEL_W = 190
const PX_PER_DAY = 26
const ROW_H = 36
const BAR_H = 20
const AXIS_H = 26
const DEFAULT_COLOR = 'var(--gray)'

const parseISO = (s) => new Date(s + 'T00:00:00')
const dayDiff = (a, b) => Math.round((b - a) / 86400000)
const fmtDM = (d) => `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`

export default function ProjectGantt({ t }) {
  const navigate = useNavigate()
  const [models, setModels] = useState([])
  const [today, setToday] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    plan.gantt({})
      .then(res => { setModels(res.data?.models || []); setToday(res.data?.today || null) })
      .catch(() => setModels([]))
      .finally(() => setLoading(false))
  }, [])

  // Rang temporal global (min start, max end) amb 1 dia de marge a banda i banda.
  const range = useMemo(() => {
    if (!models.length) return null
    let min = null, max = null
    for (const m of models) {
      const s = parseISO(m.start), e = parseISO(m.end)
      if (min === null || s < min) min = s
      if (max === null || e > max) max = e
      for (const f of m.fites) { const d = parseISO(f.data); if (d < min) min = d; if (d > max) max = d }
      if (m.data_objectiu) { const d = parseISO(m.data_objectiu); if (d > max) max = d; if (d < min) min = d }
    }
    min = new Date(min.getTime() - 86400000)
    max = new Date(max.getTime() + 86400000)
    return { min, max, days: dayDiff(min, max) + 1 }
  }, [models])

  if (loading) return <Center>{t('planning.loading')}</Center>
  if (!range || !models.length) {
    return <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)', border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)' }}>{t('planning.gantt.empty')}</div>
  }

  const trackW = range.days * PX_PER_DAY
  const x = (iso) => dayDiff(range.min, parseISO(iso)) * PX_PER_DAY
  const todayX = today ? x(today) : null

  // Ticks de l'eix (densitat segons amplada del rang).
  const step = range.days > 40 ? 7 : (range.days > 14 ? 3 : 1)
  const ticks = []
  for (let i = 0; i < range.days; i += step) {
    ticks.push({ i, d: new Date(range.min.getTime() + i * 86400000) })
  }

  return (
    <div>
      <Legend t={t} />
      <div style={{ overflowX: 'auto', border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)' }}>
        <div style={{ minWidth: LABEL_W + trackW }}>
          {/* Eix de dies */}
          <div style={{ display: 'flex', position: 'sticky', top: 0, zIndex: 3, background: 'var(--bg-muted)', borderBottom: '0.5px solid var(--gray-l)' }}>
            <div style={{ width: LABEL_W, flexShrink: 0, position: 'sticky', left: 0, background: 'var(--bg-muted)', zIndex: 4, borderRight: '0.5px solid var(--gray-l)' }} />
            <div style={{ position: 'relative', width: trackW, height: AXIS_H }}>
              {ticks.map(tk => (
                <div key={tk.i} style={{ position: 'absolute', left: tk.i * PX_PER_DAY, top: 0, height: AXIS_H, borderLeft: '0.5px solid var(--gray-l)', paddingLeft: 3 }}>
                  <span style={{ fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)' }}>{fmtDM(tk.d)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Files de models */}
          {models.map(m => (
            <GanttRow key={m.model_id} m={m} trackW={trackW} x={x} todayX={todayX}
                      ticks={ticks} onClick={() => navigate(`/models/${m.model_id}`)} t={t} />
          ))}
        </div>
      </div>
    </div>
  )
}

function GanttRow({ m, trackW, x, todayX, ticks, onClick, t }) {
  const color = m.responsable_color || DEFAULT_COLOR
  const left = x(m.start)
  const right = x(m.end) + PX_PER_DAY            // fi inclusiu (el dia de fi compta sencer)
  const width = Math.max(PX_PER_DAY * 0.7, right - left)
  const objX = m.data_objectiu ? x(m.data_objectiu) : null

  // Finestres d'espera (confecció externa): es pinten com a segment trencat ratllat.
  const esperes = (m.esperes || []).map(w => ({ l: x(w.from), r: x(w.to) + PX_PER_DAY }))

  return (
    <div onClick={onClick} title={`${m.codi} · ${m.nom || ''}`} style={{
      display: 'flex', height: ROW_H, cursor: 'pointer', borderBottom: '0.5px solid var(--base-hairline, var(--gray-l))',
    }}>
      <div style={{ width: LABEL_W, flexShrink: 0, position: 'sticky', left: 0, background: 'var(--white)', zIndex: 2,
                    borderRight: '0.5px solid var(--gray-l)', padding: '4px 10px', overflow: 'hidden' }}>
        <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: 'var(--fs-body)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{m.codi}</div>
        <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{m.responsable_nom || '—'}</div>
      </div>

      <div style={{ position: 'relative', width: trackW, height: ROW_H }}>
        {/* graella vertical */}
        {ticks.map(tk => (
          <div key={tk.i} style={{ position: 'absolute', left: tk.i * PX_PER_DAY, top: 0, bottom: 0, borderLeft: '0.5px solid var(--bg-muted)' }} />
        ))}
        {/* línia AVUI */}
        {todayX != null && <div style={{ position: 'absolute', left: todayX, top: 0, bottom: 0, borderLeft: '1px solid var(--gold)', opacity: 0.6 }} />}
        {/* línia DATA OBJECTIU (vermella discontínua) */}
        {objX != null && <div style={{ position: 'absolute', left: objX, top: 0, bottom: 0, borderLeft: '1.5px dashed var(--err)' }} />}

        {/* BARRA del model */}
        <div style={{ position: 'absolute', left, width, top: (ROW_H - BAR_H) / 2, height: BAR_H }}>
          {/* contenidor (rang sencer, color tènue) */}
          <div style={{ position: 'absolute', inset: 0, borderRadius: 5, background: color, opacity: 0.22, border: `0.5px solid ${color}` }} />
          {/* farciment % completat */}
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${m.pct}%`, borderRadius: 5, background: color, opacity: 0.85 }} />
          {/* finestres d'espera (ratllat = barra trencada) */}
          {esperes.map((w, i) => (
            <div key={i} title={t('planning.gantt.legend_wait')} style={{
              position: 'absolute', top: 0, bottom: 0, left: w.l - left, width: Math.max(2, w.r - w.l),
              background: 'repeating-linear-gradient(45deg, var(--white), var(--white) 3px, var(--gray-l) 3px, var(--gray-l) 5px)',
              border: '0.5px dashed var(--text-muted)', borderRadius: 2,
            }} />
          ))}
          {/* etiqueta fase · % */}
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-main)', whiteSpace: 'nowrap', pointerEvents: 'none' }}>
            {t(`model_sheet.dashboard.phase.${m.fase}`, { defaultValue: m.fase })} · {m.pct}%
          </div>
        </div>

        {/* FITES (marcadors) */}
        {m.fites.map((f, i) => (
          <div key={i} title={`${t(`planning.gantt.legend_${f.tipus}`)} · ${f.data}`} style={{
            position: 'absolute', left: x(f.data) + PX_PER_DAY / 2 - 7, top: 1, width: 14, height: 14,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <i className={`ti ti-${f.tipus === 'proto' ? 'package' : 'ruler-2'}`}
               style={{ fontSize: 13, color: f.tipus === 'proto' ? 'var(--taupe, #7c6f64)' : 'var(--info, #3a7ca5)' }} />
          </div>
        ))}
      </div>
    </div>
  )
}

function Legend({ t }) {
  const item = (icon, color, label) => (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO }}>
      {icon === 'line' ? <span style={{ width: 12, borderTop: `1.5px dashed ${color}`, display: 'inline-block' }} />
        : <i className={`ti ti-${icon}`} style={{ fontSize: 13, color }} />}
      {label}
    </span>
  )
  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 10 }}>
      {item('package', 'var(--taupe, #7c6f64)', t('planning.gantt.legend_proto'))}
      {item('ruler-2', 'var(--info, #3a7ca5)', t('planning.gantt.legend_fitting'))}
      {item('line', 'var(--err)', t('planning.gantt.legend_objectiu'))}
      {item('line', 'var(--gold)', t('planning.gantt.legend_today'))}
    </div>
  )
}
