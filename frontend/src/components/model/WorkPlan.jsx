import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import Badge from '../ui/Badge'
import { formatMinutes } from '../../utils/format'

// Pla de treball — PEÇA P2a (Q4 crescut): l'encàrrec del model com a procés.
// Consumeix dashboard.tasques (compositor enriquit a P1, JA ordenat canònic) — NO reordena.
// Transport (Play/Pause/Stop) en PLACEHOLDER: estat visual correcte, onClick no-op (TODO P3).
// Tres rendings (§5) per scope viewer: meva / d'altri / fora d'encàrrec.

const API = import.meta.env.VITE_API_URL || ''

// task_type.code → icona Tabler (no hi havia mapa compartit; design system).
const TASK_ICON = {
  pattern_digit: 'ti-vector', pattern_cad: 'ti-vector-bezier', pattern_hand: 'ti-pencil',
  pattern_review: 'ti-eye-check', pom: 'ti-ruler-2', size_check: 'ti-ruler-measure',
  tech_sheet: 'ti-file-text', bom: 'ti-list-details', scaling: 'ti-resize',
  marking: 'ti-layout-grid', Audit: 'ti-checklist',
}

// status → variant del Badge del design system (mateix criteri que el dashboard F1).
const STATUS_VARIANT = { Done: 'ok', InProgress: 'gold', Paused: 'warn', Pending: 'gray' }

// Transport actiu per estat (mirall d'ACTIONS de KanbanTasks: quins botons toquen a cada estat).
// play = Pending/Paused/Done (start/resume/reopen) · pause+stop = InProgress.
const TRANSPORT = {
  Pending:    { play: true,  pause: false, stop: false },
  Paused:     { play: true,  pause: false, stop: false },
  InProgress: { play: false, pause: true,  stop: true  },
  Done:       { play: true,  pause: false, stop: false },
}

// Fora d'encàrrec: a v1 cap dada ho marca (les externes són P4). Rending definit però inert.
function isOutOfCharge(_task) { return false }   // TODO P4: derivar de l'origen/flag de tasca externa

const containerStyle = { background: 'transparent', width: '100%' }
const cardsGrid = { display: 'flex', flexWrap: 'wrap', gap: 12 }
const sectionTitle = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontWeight: 500,
  textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10,
}

function TransportBtn({ icon, active, title }) {
  return (
    <button type="button" title={title} disabled={!active}
      onClick={() => { /* TODO P3: cablejar modelTasks.transition */ }}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: 28, height: 28, borderRadius: 6,
        border: '0.5px solid var(--border)',
        background: active ? 'var(--bg-muted)' : 'transparent',
        color: active ? 'var(--text-main)' : 'var(--text-muted)',
        cursor: active ? 'pointer' : 'not-allowed', opacity: active ? 1 : 0.4,
      }}>
      <i className={`ti ${icon}`} style={{ fontSize: 15 }} />
    </button>
  )
}

function TaskCard({ task, mine }) {
  const { t } = useTranslation()
  const out = isOutOfCharge(task)
  const transport = TRANSPORT[task.status] || TRANSPORT.Pending
  const icon = TASK_ICON[task.task_type_code] || 'ti-checkbox'
  // Renderings §5: meva = nítida + transport operable; d'altri = fade + transport apagat.
  const otherTech = !mine && task.assignee_id != null
  return (
    <div style={{
      flex: '1 1 220px', maxWidth: 320, minWidth: 0,
      border: out ? '1px solid var(--err)' : '0.5px solid var(--border)',
      borderLeft: out ? '3px solid var(--err)' : '0.5px solid var(--border)',
      borderRadius: 8, padding: '0.7rem 0.8rem', background: 'var(--white)',
      opacity: otherTech ? 0.55 : 1,
    }}>
      {/* Capçalera: icona + nom del tipus (truncat, mai desborda) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
        <i className={`ti ${icon}`} style={{ fontSize: 16, color: 'var(--gold)', flexShrink: 0 }} />
        <span style={{ fontWeight: 500, color: 'var(--text-main)', overflow: 'hidden',
                       textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {task.task_type_name || task.task_type_code || '—'}
        </span>
      </div>

      {/* Cos: temps consumit (helper existent) + obertures */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8,
                    fontFamily: 'var(--mono)', fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
        <span><i className="ti ti-clock" style={{ fontSize: 13, marginRight: 3 }} />{formatMinutes(task.temps_consumit_min ?? 0)}</span>
        <span><i className="ti ti-repeat" style={{ fontSize: 13, marginRight: 3 }} />{t('model_sheet.dashboard.workplan.openings', { n: task.obertures ?? 0 })}</span>
      </div>

      {/* d'altri: qui la duu */}
      {otherTech && task.assignee_nom && (
        <div style={{ marginTop: 4, fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
          {t('model_sheet.dashboard.timeline.by', { label: task.assignee_nom })}
        </div>
      )}
      {out && (
        <div style={{ marginTop: 4, fontSize: 'var(--fs-label)', color: 'var(--err)',
                      overflowWrap: 'anywhere' }}>
          {t('model_sheet.dashboard.workplan.out_of_charge')}
        </div>
      )}

      {/* Peu: transport (placeholder) + badge d'estat */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 4, opacity: mine ? 1 : 0.5 }}>
          <TransportBtn icon="ti-player-play-filled"  active={mine && transport.play}  title={t('model_sheet.dashboard.workplan.play')} />
          <TransportBtn icon="ti-player-pause-filled" active={mine && transport.pause} title={t('model_sheet.dashboard.workplan.pause')} />
          <TransportBtn icon="ti-player-stop-filled"  active={mine && transport.stop}  title={t('model_sheet.dashboard.workplan.stop')} />
        </div>
        <Badge variant={STATUS_VARIANT[task.status] || 'gray'} style={{ maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {t(`model_sheet.dashboard.task_status.${task.status}`, { defaultValue: task.status })}
        </Badge>
      </div>
    </div>
  )
}

export default function WorkPlan({ tasques }) {
  const { t } = useTranslation()
  const token = localStorage.getItem('access_token')
  const [myProfileId, setMyProfileId] = useState(null)

  useEffect(() => {
    let alive = true
    // scope viewer: "meva" = assignee_id === me.profile_id (UserProfile.id), NO me.id (P1.5).
    fetch(`${API}/api/v1/me/`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (alive && d) setMyProfileId(d.profile_id ?? null) })
      .catch(() => {})
    return () => { alive = false }
  }, [])

  const list = Array.isArray(tasques) ? tasques : []

  return (
    <section style={containerStyle}>
      <div style={sectionTitle}>{t('model_sheet.dashboard.workplan.title')}</div>
      {list.length === 0 ? (
        <div style={{ border: '0.5px dashed var(--border)', borderRadius: 8, padding: '0.7rem 0.9rem',
                      background: 'var(--bg-muted)', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
          {t('model_sheet.dashboard.workplan.empty')}
        </div>
      ) : (
        <div style={cardsGrid}>
          {list.map(task => (
            <TaskCard key={task.id} task={task}
              mine={task.assignee_id != null && task.assignee_id === myProfileId} />
          ))}
        </div>
      )}
    </section>
  )
}
