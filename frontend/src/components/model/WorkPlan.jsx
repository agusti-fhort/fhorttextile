import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Badge from '../ui/Badge'
import Modal from '../ui/Modal'
import { modelTasks } from '../../api/endpoints'
import { formatMinutes } from '../../utils/format'
import { taskTypeLabel } from '../../utils/taskType'

// Pla de treball — PEÇA P3 + P4a (Q4 crescut): l'encàrrec del model com a procés.
// Consumeix dashboard.tasques (compositor enriquit a P1, JA ordenat canònic) — NO reordena.
// Transport (Play/Pause/Stop) CABLEJAT a modelTasks.transition (P3). "Play obre l'eina"
// (decisió Agus): Play = anar a treballar → transition InProgress + navega a l'eina; si la
// tasca no en té (pattern_*, bom, scaling, marking, Audit) → InProgress sense navegar (§4).
// P4a — handoff (§6): Play sobre tasca d'ALTRI obre un diàleg de reassignació; en confirmar fa
// modelTasks.claim (self-only, gated execute_tasks) i després el mateix camí de Play de P3.
// Pause/Stop segueixen apagats a d'altri. Tres rendings (§5): meva / d'altri / fora d'encàrrec.

const API = import.meta.env.VITE_API_URL || ''

// task_type_code → ruta de l'eina al frontend. Mini-taula LOCAL (mirall del kanban
// KanbanTasks.jsx pom/tech_sheet/size_check; duplicació mínima conscient, deute anotat a P0 §B —
// NO importem ACTIONS del kanban). null = tipus sense eina → transport manual (§4).
function toolRoute(task, modelId) {
  switch (task.task_type_code) {
    // J1+: "Definició POM" (pom) → el TAB Mesures en mode ENTRADA (mode=entry): obre la genesi/wizard
    // d'entrada per definir/afegir POMs, encara que el model JA tingui mesures (no consulta). Sense
    // task_id (la definició de POMs no en porta). Ja NO la pàgina standalone.
    case 'pom':        return `/models/${modelId}?tab=Mesures&mode=entry`
    case 'tech_sheet': return `/models/${modelId}/fitxa?task_id=${task.id}`
    // J1: "Mesurar prenda" (size_check) → el TAB Mesures del ModelSheet amb task_id (el tab el consumeix
    // sense encunyar-ne cap de nova). Ja NO va a la pàgina standalone (jubilada).
    case 'size_check': return `/models/${modelId}?tab=Mesures&task_id=${task.id}`
    // "Escalat" (grading = definir la regla de gradació) → editor propagat editable, amb task_id
    // (compta temps). scaling ("Escalat CAD" = aplicar al patró) és tasca diferent, eina futura → null.
    case 'grading':    return `/models/${modelId}/escalat?task_id=${task.id}`
    default:           return null
  }
}

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

// Fora d'encàrrec: tasca iniciada fora de l'encàrrec del PM (arbre global / externa lliure),
// marcada al backend amb origen='ad_hoc' (les 'prevista' són d'encàrrec). Activa el filet grana.
function isOutOfCharge(task) { return task?.origen === 'ad_hoc' }

const containerStyle = { background: 'transparent', width: '100%' }
const cardsGrid = { display: 'flex', flexWrap: 'wrap', gap: 12 }
const sectionTitle = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontWeight: 500,
  textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10,
}
const footerWrap = { width: '100%', marginTop: 14 }

function TransportBtn({ icon, active, title, onClick }) {
  return (
    <button type="button" title={title} disabled={!active}
      onClick={() => { if (active) onClick?.() }}
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

function TaskCard({ task, mine, onPlay, onPause, onStop }) {
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
          {taskTypeLabel(t, task.task_type_code, task.task_type_name)}
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
        <div style={{ display: 'flex', gap: 4 }}>
          {/* P4a: Play disponible també a d'altri (obre diàleg de handoff). Pause/Stop només meves. */}
          <TransportBtn icon="ti-player-play"  active={mine ? transport.play : true} title={mine ? t('model_sheet.dashboard.workplan.play') : t('model_sheet.dashboard.workplan.handoff_play')} onClick={() => onPlay(task)} />
          <TransportBtn icon="ti-player-pause" active={mine && transport.pause} title={t('model_sheet.dashboard.workplan.pause')} onClick={() => onPause(task)} />
          <TransportBtn icon="ti-player-stop"  active={mine && transport.stop}  title={t('model_sheet.dashboard.workplan.stop')}  onClick={() => onStop(task)} />
        </div>
        <Badge variant={STATUS_VARIANT[task.status] || 'gray'} style={{ maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {t(`model_sheet.dashboard.task_status.${task.status}`, { defaultValue: task.status })}
        </Badge>
      </div>
    </div>
  )
}

export default function WorkPlan({ tasques, modelId, onRefresh }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const [myProfileId, setMyProfileId] = useState(null)
  const [toast, setToast] = useState(null)        // { type, text }
  const [handoff, setHandoff] = useState(null)     // task pendent de reassignar (diàleg §6)
  const [claiming, setClaiming] = useState(false)  // guard anti-doble-clic del claim
  const toastTimer = useRef(null)

  useEffect(() => {
    let alive = true
    // scope viewer: "meva" = assignee_id === me.profile_id (UserProfile.id), NO me.id (P1.5).
    fetch(`${API}/api/v1/me/`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (alive && d) setMyProfileId(d.profile_id ?? null) })
      .catch(() => {})
    return () => { alive = false }
  }, [])

  useEffect(() => () => { if (toastTimer.current) clearTimeout(toastTimer.current) }, [])

  const list = Array.isArray(tasques) ? tasques : []
  const isMine = (task) => task.assignee_id != null && task.assignee_id === myProfileId

  // Peu (P5, §1): progrés (% Done sobre el total) + temps real acumulat sobre el MODEL. La suma
  // frontend de temps_consumit_min quadra EXACTAMENT amb el rollup de l'albarà (ambdós sumen els
  // minuts de timers consolidats de TOTES les tasques del model; el compositor no scopa) → suma
  // local, zero crides noves (P5 PAS 0.2). Degradació amb gràcia: 0 tasques → 0% / 0h 00m.
  const total = list.length
  const done = list.filter(task => task.status === 'Done').length
  const pct = total ? Math.round((100 * done) / total) : 0
  const totalMin = list.reduce((s, task) => s + (task.temps_consumit_min || 0), 0)

  function showToast(type, text) {
    setToast({ type, text })
    if (toastTimer.current) clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 3000)
  }

  // Exclusió un-InProgress-per-tècnic: si la resposta porta paused_task_id, el servei n'ha
  // pausat una altra del mateix tècnic → avisem amb el nom (la cerquem a la llista actual).
  function notifyPaused(res) {
    const pausedId = res?.data?.paused_task_id
    if (!pausedId) return
    const p = list.find(x => x.id === pausedId)
    const name = p ? taskTypeLabel(t, p.task_type_code, p.task_type_name) : `#${pausedId}`
    showToast('warn', t('model_sheet.dashboard.workplan.toast_paused', { name }))
  }

  // Transició que NO navega (Play sense eina §4, Pause, Stop): després refresca el dashboard
  // perquè estat/temps/obertures de la targeta reflecteixin el canvi.
  function doTransition(task, toStatus) {
    modelTasks.transition(task.id, { to_status: toStatus })
      .then(res => { notifyPaused(res); onRefresh?.() })
      .catch(err => {
        const msg = err?.response?.data?.error
          || (err?.response?.status === 403
            ? t('model_sheet.dashboard.workplan.not_allowed')
            : t('model_sheet.dashboard.workplan.transition_error'))
        showToast('err', msg)
        onRefresh?.()   // re-sincronitza amb el backend (la targeta local podia ser obsoleta)
      })
  }

  // Camí de Play de P3 (sobre tasca PRÒPIA): anar a treballar (decisió Agus). Amb eina: transition
  // InProgress + navega (idèntic al kanban; Done = reobertura §3.8). Fire-and-forget: navega
  // igualment. Sense eina: InProgress sense navegar (§4) — la targeta passa a "en curs".
  function playMine(task) {
    const route = toolRoute(task, modelId)
    // PUNT COMÚ d'obertura: porta la tasca a InProgress NOMÉS si cal, comprovant l'estat ACTUAL. Si ja
    // és InProgress NO demanem la transició — ALLOWED no permet InProgress→InProgress (services_c.py)
    // i tornaria 400, deixant la tasca sense obrir. Pending/Paused/Done → InProgress (Done = reobertura,
    // ja permesa). Qualsevol camí de Play (propi, handoff acceptat, futur Q2) hereta aquest guard.
    const needsStart = task.status !== 'InProgress'
    if (route) {
      // Amb eina: transiciona si cal (fire-and-forget) i navega IGUALMENT — si la transició falla, la
      // UI no queda penjada (l'eina s'obre; la tasca ja era En curs).
      if (needsStart) modelTasks.transition(task.id, { to_status: 'InProgress' }).catch(() => {})
      navigate(route)
    } else if (needsStart) {
      doTransition(task, 'InProgress')   // sense eina: transiciona + refresca (gestiona l'error visible)
    } else {
      onRefresh?.()   // ja En curs i sense eina: només re-sincronitza la targeta, sense demanar res
    }
  }

  // P4a — Play segons qui té la tasca. Meva → camí de P3 directe. D'altri → diàleg de handoff (§6).
  function handlePlay(task) {
    if (isMine(task)) { playMine(task); return }
    setHandoff(task)
  }

  // Confirmar handoff: claim (self-only, gated execute_tasks) i, si OK, el camí de Play de P3 amb
  // la tasca JA reassignada. El recompute es dispara sol al backend. 403 = allow-list (tipus que no
  // executo) → toast clar, sense navegar. La tasca ja és meva → playMine aplica net (mine=true).
  function confirmHandoff() {
    if (!handoff || claiming) return
    const task = handoff
    setClaiming(true)
    modelTasks.claim(task.id)
      .then(() => {
        setHandoff(null)
        playMine({ ...task, assignee_id: myProfileId })
        onRefresh?.()
      })
      .catch(err => {
        setHandoff(null)
        const denied = err?.response?.status === 403
        showToast('err', denied
          ? t('model_sheet.dashboard.workplan.claim_denied')
          : t('model_sheet.dashboard.workplan.claim_error'))
      })
      .finally(() => setClaiming(false))
  }

  // Pause = pauso, no he acabat. Stop = gest humà explícit "feta, 100%" (MAI automàtic). Cap navega.
  const handlePause = (task) => doTransition(task, 'Paused')
  const handleStop  = (task) => doTransition(task, 'Done')

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
            <TaskCard key={task.id} task={task} mine={isMine(task)}
              onPlay={handlePlay} onPause={handlePause} onStop={handleStop} />
          ))}
        </div>
      )}

      {/* Peu (§1): barra de progrés (% Done) + temps acumulat sobre el model (ample total) */}
      <div style={footerWrap}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
                      gap: 12, flexWrap: 'wrap', marginBottom: 6, fontSize: 'var(--fs-label)',
                      color: 'var(--text-muted)' }}>
          <span>{t('model_sheet.dashboard.workplan.progress_label', { done, total })} · {pct}%</span>
          <span>{t('model_sheet.dashboard.workplan.time_total')}:{' '}
            <span style={{ fontFamily: 'var(--mono)', color: 'var(--text-main)' }}>{formatMinutes(totalMin)}</span>
          </span>
        </div>
        <div style={{ height: 8, borderRadius: 6, background: 'var(--bg-muted)',
                      border: '0.5px solid var(--border)', overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: 'var(--ok)',
                        transition: 'width 200ms' }} />
        </div>
      </div>
      {handoff && (
        <Modal
          title={t('model_sheet.dashboard.workplan.handoff_title')}
          subtitle={handoff.assignee_nom
            ? t('model_sheet.dashboard.workplan.handoff_body', { name: handoff.assignee_nom })
            : t('model_sheet.dashboard.workplan.handoff_body_unassigned')}
          confirmLabel={t('model_sheet.dashboard.workplan.handoff_confirm')}
          cancelLabel={t('model_sheet.dashboard.workplan.handoff_cancel')}
          confirmDisabled={claiming}
          onConfirm={confirmHandoff}
          onCancel={() => { if (!claiming) setHandoff(null) }}
        />
      )}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', zIndex: 60,
          fontSize: 'var(--fs-body)', padding: '10px 16px', borderRadius: 8, boxShadow: '0 6px 24px rgba(0,0,0,0.18)',
          background: toast.type === 'err' ? 'var(--err-bg)' : toast.type === 'warn' ? 'var(--warn-bg)' : 'var(--ok-bg)',
          color: toast.type === 'err' ? 'var(--err)' : toast.type === 'warn' ? 'var(--warn)' : 'var(--ok)',
        }}>{toast.text}</div>
      )}
    </section>
  )
}
