import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { models, taskTypes } from '../../api/endpoints'
import { taskTypeLabel } from '../../utils/taskType'

// B2 — Arbre per INICIAR tasques des del Model Sheet (fase → TaskType → "Iniciar").
// Complementa el WorkPlan (que llista només les ModelTask ja existents): aquí es pot iniciar
// qualsevol TaskType actiu encara que no estigui assignat. El backend (open-task) és idempotent:
// crea la ModelTask si no existeix i la posa InProgress. Referència sempre per `code` slug (G9).

// Ordre canònic de fases — mirall de TaskType.FASE_CHOICES (backend tasks/models.py).
const PHASE_ORDER = ['Disseny', 'Dev. tècnic', 'Prototip', 'Mostres', 'Preproducció', 'Producció']
const PHASE_I18N = {
  'Disseny': 'model_sheet.tasks.tree_phase_design',
  'Dev. tècnic': 'model_sheet.tasks.tree_phase_dev',
  'Prototip': 'model_sheet.tasks.tree_phase_prototype',
  'Mostres': 'model_sheet.tasks.tree_phase_samples',
  'Preproducció': 'model_sheet.tasks.tree_phase_preprod',
  'Producció': 'model_sheet.tasks.tree_phase_prod',
}

// Patró d'eina (duplicació mínima conscient, mirall de WorkPlan.jsx): code → ruta + tab.
function toolRoute(code, taskId, modelId) {
  switch (code) {
    case 'pom':        return `/models/${modelId}?tab=Mesures&mode=entry`
    case 'tech_sheet': return `/models/${modelId}/fitxa?task_id=${taskId}`
    case 'size_check': return `/models/${modelId}?tab=Mesures&task_id=${taskId}`
    case 'grading':    return `/models/${modelId}/escalat?task_id=${taskId}`
    default:           return null
  }
}
function toolTab(code) { return (code === 'pom' || code === 'size_check') ? 'Mesures' : null }

const sectionTitle = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontWeight: 500,
  textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10,
}
const phaseTitle = {
  fontSize: 'var(--fs-caption)', color: 'var(--gold)', fontWeight: 700,
  textTransform: 'uppercase', letterSpacing: '0.05em', margin: '14px 0 6px',
}
const rowStyle = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
  border: '0.5px solid var(--border)', borderRadius: 8, padding: '0.55rem 0.8rem',
  background: 'var(--white)', marginBottom: 6,
}
const startBtn = {
  display: 'inline-flex', alignItems: 'center', gap: 6, flexShrink: 0,
  border: '1px solid var(--gold)', borderRadius: 6, background: 'transparent',
  color: 'var(--gold)', fontFamily: 'inherit', fontSize: 'var(--fs-body)', fontWeight: 600,
  padding: '5px 12px', cursor: 'pointer',
}

export default function TaskTree({ modelId, modelTaskRows = [], onTaskStarted, onOpenTab }) {  // eslint-disable-line no-unused-vars
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [types, setTypes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(null)   // code en curs d'iniciar

  useEffect(() => {
    let alive = true
    setLoading(true)
    taskTypes.list({ active: true, page_size: 200 })
      .then(res => {
        const d = res?.data
        const list = Array.isArray(d?.results) ? d.results : (Array.isArray(d) ? d : [])
        if (alive) setTypes(list)
      })
      .catch(() => { if (alive) setError(t('model_sheet.tasks.tree_start_error')) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelId])

  const start = (tt) => {
    setError(''); setStarting(tt.code)
    models.openTask(modelId, tt.code)
      .then(res => {
        onTaskStarted?.()
        const taskId = res?.data?.task_id
        const route = toolRoute(tt.code, taskId, modelId)
        if (route) {
          const tab = toolTab(tt.code)
          if (tab) onOpenTab?.(tab)
          navigate(route)
        }
      })
      .catch(err => {
        if (err?.response?.status === 403) setError(t('model_sheet.tasks.tree_no_permission'))
        else setError(t('model_sheet.tasks.tree_start_error'))
      })
      .finally(() => setStarting(null))
  }

  // Agrupa per fase respectant l'ordre canònic; les fases sense tipus no es mostren.
  const byPhase = {}
  for (const tt of types) { (byPhase[tt.fase] = byPhase[tt.fase] || []).push(tt) }
  const ordered = [...PHASE_ORDER, ...Object.keys(byPhase).filter(p => !PHASE_ORDER.includes(p))]
    .filter(p => byPhase[p] && byPhase[p].length)

  return (
    <div style={{ width: '100%' }}>
      <div style={sectionTitle}>{t('model_sheet.tasks.tree_title')}</div>
      {error && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
          border: '0.5px solid var(--err)', background: 'var(--err-bg)', color: 'var(--err)',
          borderRadius: 8, padding: '0.5rem 0.8rem', fontSize: 'var(--fs-body)' }}>
          <i className="ti ti-alert-triangle" style={{ fontSize: 15 }} />{error}
        </div>
      )}
      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('model_sheet.loading')}</div>
      ) : ordered.map(phase => (
        <div key={phase}>
          <div style={phaseTitle}>{t(PHASE_I18N[phase], { defaultValue: phase })}</div>
          {byPhase[phase].slice().sort((a, b) => (a.default_order - b.default_order)).map(tt => (
            <div key={tt.code} style={rowStyle}>
              <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {taskTypeLabel(t, tt.code, tt.name)}
              </span>
              <button type="button" style={{ ...startBtn, opacity: starting === tt.code ? 0.5 : 1, cursor: starting ? 'default' : 'pointer' }}
                disabled={!!starting} onClick={() => start(tt)}>
                <i className="ti ti-player-play" style={{ fontSize: 14 }} />
                {t('model_sheet.tasks.tree_start_task')}
              </button>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
