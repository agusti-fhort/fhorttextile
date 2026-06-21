import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import Badge from '../ui/Badge'

// Timeline del model — PEÇA F2 (Q2 "què ha canviat"), columna dreta del Dashboard.
// Consumeix GET /api/v1/models/<id>/timeline/ (endpoint B2, read-only).
// NOMÉS passat (les 3 fonts `a`); el futur (sessions/planificat/arribades) és peça posterior.
// Ordre -at (recent a dalt): deixa preparat el forat del futur a dalt, sense implementar-lo.

const API = import.meta.env.VITE_API_URL || ''

// kind → icona Tabler + token semàntic d'accent (NOMÉS tokens del design system).
const KIND_META = {
  measure_change:  { icon: 'ti-ruler-2',         color: 'var(--gold)' },
  gate_advance:    { icon: 'ti-arrow-up-circle', color: 'var(--ok)' },    // progrés
  gate_regress:    { icon: 'ti-arrow-back-up',   color: 'var(--warn)' },  // enrere
  task_transition: { icon: 'ti-checkbox',        color: 'var(--text-muted)' },
}

const sectionTitle = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontWeight: 500,
  textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8,
}
const cardEmpty = {
  border: '0.5px dashed var(--border)', borderRadius: 8, padding: '0.7rem 0.9rem',
  background: 'var(--bg-muted)', color: 'var(--text-muted)', fontSize: 'var(--fs-body)',
}
const dayHeader = {
  fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--text-main)',
  margin: '14px 0 6px', position: 'sticky', top: 0, zIndex: 1,
  background: 'var(--bg-main)', padding: '2px 0',
}
const eventRow = {
  display: 'flex', gap: 10, alignItems: 'flex-start',
  border: '0.5px solid var(--border)', borderRadius: 8,
  padding: '0.6rem 0.8rem', background: 'var(--white)',
}

function startOfDay(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); return x }

export default function ModelTimeline({ modelId }) {
  const { t, i18n } = useTranslation()
  const token = localStorage.getItem('access_token')
  const [events, setEvents] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setLoading(true); setError('')
    fetch(`${API}/api/v1/models/${modelId}/timeline/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => { if (!r.ok) throw new Error('http'); return r.json() })
      .then(d => { if (alive) setEvents(Array.isArray(d.events) ? d.events : []) })
      .catch(() => { if (alive) setError(t('model_sheet.dashboard.timeline.err_load')) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [modelId])

  // temps relatiu — el que fa que sigui memòria i no log.
  const relTime = (at) => {
    const diff = Date.now() - new Date(at).getTime()
    const min = Math.floor(diff / 60000)
    if (min < 1) return t('model_sheet.dashboard.timeline.now')
    if (min < 60) return t('model_sheet.dashboard.timeline.ago_min', { n: min })
    const h = Math.floor(min / 60)
    if (h < 24) return t('model_sheet.dashboard.timeline.ago_hour', { n: h })
    return t('model_sheet.dashboard.timeline.ago_day', { n: Math.floor(h / 24) })
  }

  const dayLabel = (at) => {
    const diffDays = Math.round((startOfDay(Date.now()) - startOfDay(at)) / 86400000)
    if (diffDays <= 0) return t('model_sheet.dashboard.timeline.today')
    if (diffDays === 1) return t('model_sheet.dashboard.timeline.yesterday')
    return new Date(at).toLocaleDateString(i18n.language, { day: 'numeric', month: 'short', year: 'numeric' })
  }

  // text humà per kind (reusa phase.* i task_status.* del namespace F1).
  const lineText = (ev) => {
    const p = ev.payload || {}
    switch (ev.kind) {
      case 'measure_change': {
        const pom = p.pom_codi || p.pom_id || '—'
        return (p.valor_anterior == null)
          ? t('model_sheet.dashboard.timeline.measure_set', { pom, val: p.valor_nou })
          : t('model_sheet.dashboard.timeline.measure_change', { pom, prev: p.valor_anterior, val: p.valor_nou })
      }
      case 'gate_advance':
        return t('model_sheet.dashboard.timeline.gate_advance', {
          phase: t(`model_sheet.dashboard.phase.${p.to_phase}`, { defaultValue: p.to_phase || '—' }) })
      case 'gate_regress':
        return t('model_sheet.dashboard.timeline.gate_regress', {
          phase: t(`model_sheet.dashboard.phase.${p.to_phase}`, { defaultValue: p.to_phase || '—' }) })
      case 'task_transition':
        return t('model_sheet.dashboard.timeline.task_transition', {
          task: p.task_type_name || p.task_type_code || '—',
          status: t(`model_sheet.dashboard.task_status.${p.to_status}`, { defaultValue: p.to_status || '—' }) })
      default:
        return ev.kind
    }
  }

  let body
  if (loading) {
    body = (
      <div style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
        {t('model_sheet.loading')}
      </div>
    )
  } else if (error) {
    body = (
      <div style={{ ...cardEmpty, display: 'flex', alignItems: 'center', gap: 8,
                    borderStyle: 'solid', borderColor: 'var(--err)',
                    color: 'var(--err)', background: 'var(--err-bg)' }}>
        <i className="ti ti-alert-triangle" style={{ fontSize: 16 }} />
        {error}
      </div>
    )
  } else if (!events || events.length === 0) {
    body = <div style={cardEmpty}>{t('model_sheet.dashboard.timeline.empty')}</div>
  } else {
    // Agrupació per dia. Els events ja vénen ordenats -at del backend → el mateix dia és contigu.
    const groups = []
    for (const ev of events) {
      const key = startOfDay(ev.at).getTime()
      let g = groups.length && groups[groups.length - 1].key === key ? groups[groups.length - 1] : null
      if (!g) { g = { key, label: dayLabel(ev.at), items: [] }; groups.push(g) }
      g.items.push(ev)
    }
    body = (
      <div style={{ maxHeight: '75vh', overflowY: 'auto', paddingRight: 4 }}>
        {groups.map(g => (
          <div key={g.key}>
            <div style={dayHeader}>{g.label}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {g.items.map((ev, i) => {
                const meta = KIND_META[ev.kind] || { icon: 'ti-point', color: 'var(--text-muted)' }
                const p = ev.payload || {}
                return (
                  <div key={i} style={eventRow}>
                    <i className={`ti ${meta.icon}`} style={{ fontSize: 16, color: meta.color, marginTop: 2 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)',
                                    display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span>{lineText(ev)}</span>
                        {ev.kind === 'measure_change' && p.fora_de_tolerancia && (
                          <Badge variant="err" icon="ti-alert-triangle">
                            {t('model_sheet.dashboard.timeline.out_of_tolerance')}
                          </Badge>
                        )}
                      </div>
                      <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 2 }}>
                        {relTime(ev.at)}
                        {ev.actor && <> · {t('model_sheet.dashboard.timeline.by', { label: ev.actor.label })}</>}
                        {ev.kind === 'measure_change' && p.context && (
                          <> · {t(`model_sheet.dashboard.timeline.context.${p.context}`, { defaultValue: p.context })}</>
                        )}
                      </div>
                      {ev.kind === 'measure_change' && p.motiu && (
                        <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)',
                                      fontStyle: 'italic', marginTop: 2 }}>{p.motiu}</div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <section style={{ flex: '1 1 420px', maxWidth: 560, minWidth: 0 }}>
      <div style={sectionTitle}>{t('model_sheet.dashboard.timeline.section')}</div>
      {body}
    </section>
  )
}
