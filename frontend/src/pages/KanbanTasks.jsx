import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { modelTasks, gates, models } from '../api/endpoints'
import TimerWidget from '../components/ui/TimerWidget'

// Tram 4 — Kanban mestre-detall en un sol grid de 5 columnes (sempre visibles):
//   [ models (crema) | Pendents | Pausades | En curs | Fetes ].
// Seleccionar un model a la columna 1 omple les 4 columnes de treball amb les seves tasques.
// El backend acota per row-level scope (sense view_team_tasks → només les pròpies).
// Estats reals de ModelTask: Pending / Paused / InProgress / Done.

const MONO = 'IBM Plex Mono, monospace'
const CREMA = 'var(--warn-bg)'        // #faeeda — selecció ambre/crema (marcada)
const COL1_BG = '#fdf6ee'             // crema suau de la columna de models
const AMBER_BORDER = '#ba7517'
const AMBER_TEXT = 'var(--warn)'      // #854f0b

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

// Fases del gate (Proto→…→TOP). Validar avança a la següent.
const PHASES = ['Proto', 'Fit', 'SizeSet', 'PP', 'TOP']
const nextPhase = (p) => { const i = PHASES.indexOf(p); return i >= 0 && i < PHASES.length - 1 ? PHASES[i + 1] : null }

// Segueix la paginació de DRF (PAGE_SIZE=25, sense override) per no truncar tasques/models.
async function fetchAllPages(apiFn, baseParams = {}) {
  const out = []
  let page = 1
  for (;;) {
    const res = await apiFn({ ...baseParams, page })
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
  const canCloseGates = !!user?.capabilities?.includes('close_gates')

  // Columna 1 — models (paginada) + cartes de gate (Prioritat A).
  const [search, setSearch] = useState('')
  const [modelRows, setModelRows] = useState([])
  const [modelsCount, setModelsCount] = useState(0)   // total de la resposta (no només la pàgina)
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [loadingModels, setLoadingModels] = useState(true)
  const [gateCards, setGateCards] = useState([])
  const [selected, setSelected] = useState(null)   // { type:'model'|'gate', id, ... }

  // Detall — tasques del model seleccionat (alimenten les 4 columnes de treball).
  const [detailTasks, setDetailTasks] = useState([])
  const [loadingDetail, setLoadingDetail] = useState(false)

  const [toast, setToast] = useState(null)          // { type, text }
  const toastTimer = useRef(null)
  function showToast(type, text) {
    setToast({ type, text })
    if (toastTimer.current) clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 3000)
  }

  // Càrrega d'una pàgina de by-model. replace=true reinicia (canvi de cerca); si no, hi afegeix (load more).
  const loadPage = useCallback((pageToLoad, replace) => {
    setLoadingModels(true)
    modelTasks.byModel({ search: search.trim() || undefined, page: pageToLoad })
      .then(res => {
        const data = res.data
        const results = data?.results ?? (Array.isArray(data) ? data : [])
        setModelRows(prev => (replace ? results : [...prev, ...results]))
        setHasNext(!!data?.next)
        setModelsCount(typeof data?.count === 'number' ? data.count : results.length)
      })
      .catch(() => { if (replace) { setModelRows([]); setHasNext(false); setModelsCount(0) } })
      .finally(() => setLoadingModels(false))
  }, [search])

  // Cerca amb debounce → reinicia a pàgina 1.
  useEffect(() => {
    const id = setTimeout(() => { setPage(1); loadPage(1, true) }, 300)
    return () => clearTimeout(id)
  }, [loadPage])

  // Prioritat A: cartes de gate (només si close_gates).
  const loadGates = useCallback(() => {
    gates.ready().then(res => setGateCards(res.data?.ready ?? [])).catch(() => setGateCards([]))
  }, [])
  useEffect(() => { if (canCloseGates) loadGates() }, [canCloseGates, loadGates])

  function loadMore() {
    const next = page + 1
    setPage(next)
    loadPage(next, false)
  }

  // Detall: carrega les tasques del model seleccionat (buit si cap selecció).
  const loadDetail = useCallback((modelId) => {
    if (!modelId) { setDetailTasks([]); return }
    setLoadingDetail(true)
    fetchAllPages(modelTasks.list, { model: modelId })
      .then(setDetailTasks)
      .catch(() => setDetailTasks([]))
      .finally(() => setLoadingDetail(false))
  }, [])
  const selectedId = selected?.id ?? null
  useEffect(() => { loadDetail(selectedId) }, [selectedId, loadDetail])

  // Transició d'una tasca (reutilitza paused_task_id + 403). Refresca el detall en acabar.
  function doTransition(task, toStatus) {
    modelTasks.transition(task.id, { to_status: toStatus })
      .then(res => {
        const pausedId = res.data?.paused_task_id
        if (pausedId) {
          const p = detailTasks.find(x => x.id === pausedId)
          const name = p ? `${p.model_codi || '#' + p.model} · ${p.task_type_name || p.task_type_code}` : `#${pausedId}`
          showToast('warn', t('kanban.toast_paused', { name }))
        }
        loadDetail(selectedId)
      })
      .catch(err => {
        const msg = err?.response?.data?.error
          || (err?.response?.status === 403 ? t('kanban.not_allowed') : t('kanban.transition_error'))
        showToast('err', msg)
      })
  }

  // Validar gate (close_gates): avança fase via models.gate (NO transition).
  function validateGate(gate, toPhase) {
    models.gate(gate.model_id, { to_phase: toPhase })
      .then(() => {
        showToast('ok', t('kanban.gate_done', { phase: toPhase }))
        setSelected(null)
        loadGates()
      })
      .catch(err => showToast('err', err?.response?.data?.error || t('kanban.gate_error')))
  }

  return (
    <div style={{ minWidth: 0, maxWidth: '100%' }}>
      <div style={{ marginBottom: '1.2rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>{t('kanban.title')}</h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('kanban.subtitle')}</p>
      </div>

      {/* Contenidor de cerca SOBRE el grid (aquí hi aniran després filtres rics). */}
      <div style={{ marginBottom: 14 }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder={t('kanban.search_ph')}
          style={{
            fontFamily: MONO, fontSize: 12, padding: '8px 12px', width: '100%', maxWidth: 420,
            border: '0.5px solid var(--gray-l)', borderRadius: 8, background: 'var(--white)',
            color: 'var(--text-main)',
          }}
        />
      </div>

      {/* Grid únic: columna de models + 4 columnes de treball, sempre visibles. */}
      <div style={{
        display: 'grid', gridTemplateColumns: '230px repeat(4, minmax(0, 1fr))',
        gap: '1rem', alignItems: 'start',
      }}>
        {/* Columna 1 — Models (mateixa forma que les d'estat; capçalera taronja pàlid) */}
        <div style={{
          background: 'var(--white)', border: '0.5px solid #e4e4e2', borderRadius: 12,
          overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 360, minWidth: 0,
        }}>
          <div style={{
            padding: '0.8rem 1rem', borderBottom: '0.5px solid #e4e4e2',
            display: 'flex', alignItems: 'center', gap: 8, background: COL1_BG,
          }}>
            <i className="ti ti-shirt" style={{ fontSize: 14, color: AMBER_TEXT }} />
            <span style={{ fontSize: 12, fontWeight: 500 }}>{t('kanban.col_models')}</span>
            <span style={{
              marginLeft: 'auto', fontSize: 11, color: AMBER_TEXT,
              padding: '2px 8px', borderRadius: 10, background: 'var(--white)',
            }}>{modelsCount}</span>
          </div>
          <div style={{ flex: 1, padding: '0.6rem', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {/* Prioritat A · per validar (gates) */}
            {canCloseGates && gateCards.length > 0 && (
              <div>
                <ColTitle icon="ti-flag-3" text={t('kanban.priority_a')} amber />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {gateCards.map(g => (
                    <GateRow
                      key={`gate-${g.model_id}`} gate={g} t={t}
                      selected={selected?.type === 'gate' && selected.id === g.model_id}
                      onClick={() => setSelected({ type: 'gate', id: g.model_id, ...g })}
                      onValidate={validateGate}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Llista de models */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {loadingModels && modelRows.length === 0 ? (
                <div style={ph}>{t('kanban.loading')}</div>
              ) : modelRows.length === 0 ? (
                <div style={ph}>{t('kanban.no_models')}</div>
              ) : modelRows.map(m => (
                <ModelRow
                  key={m.model_id} model={m} t={t}
                  selected={selected?.type === 'model' && selected.id === m.model_id}
                  onClick={() => setSelected({ type: 'model', id: m.model_id, ...m })}
                />
              ))}
            </div>
            {hasNext && (
              <button onClick={loadMore} disabled={loadingModels} style={{
                width: '100%', fontFamily: MONO, fontSize: 11, padding: '6px 10px',
                borderRadius: 6, border: '0.5px solid var(--gray-l)', background: 'var(--white)',
                cursor: loadingModels ? 'default' : 'pointer', color: 'var(--text-main)',
              }}>
                {t('kanban.load_more')}
              </button>
            )}
          </div>
        </div>

        {/* Columnes 2-5 — tasques del model seleccionat (buides si cap selecció) */}
        {COLUMNS.map(col => {
          const items = detailTasks.filter(tk => tk.status === col.key)
          return (
            <div key={col.key} style={{
              background: 'var(--white)', border: '0.5px solid #e4e4e2', borderRadius: 12,
              overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 360, minWidth: 0,
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
                {loadingDetail && detailTasks.length === 0 ? (
                  <div style={ph}>{t('kanban.loading')}</div>
                ) : items.length === 0 ? (
                  <div style={ph}>{t('kanban.empty_col')}</div>
                ) : items.map(tk => (
                  <TaskCard key={tk.id} task={tk} canExecute={canExecute} onTransition={doTransition} t={t} />
                ))}
              </div>
            </div>
          )
        })}
      </div>

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

const ph = { fontSize: 11, color: 'var(--gray)', textAlign: 'center', padding: '1.2rem', fontWeight: 300 }

function ColTitle({ icon, text, amber }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8,
      fontFamily: MONO, fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.04em',
      color: amber ? AMBER_TEXT : 'var(--text-muted)',
    }}>
      <i className={`ti ${icon}`} style={{ fontSize: 13 }} />
      <span>{text}</span>
    </div>
  )
}

// Mini-badge de comptador per estat.
function Count({ n, color }) {
  if (!n) return null
  return (
    <span style={{
      fontSize: 10, fontVariantNumeric: 'tabular-nums', color,
      padding: '0 5px', borderRadius: 6, background: 'var(--gray-l)',
    }}>{n}</span>
  )
}

function ModelRow({ model, selected, onClick, t }) {
  const c = model.counts || {}
  const total = (c.pending || 0) + (c.paused || 0) + (c.in_progress || 0) + (c.done || 0)
  return (
    <button onClick={onClick} style={{
      textAlign: 'left', width: '100%',
      border: `${selected ? '1px' : '0.5px'} solid ${selected ? AMBER_BORDER : 'var(--gray-l)'}`,
      background: selected ? CREMA : 'var(--white)', borderRadius: 8, padding: '8px 10px',
      cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 4,
    }}>
      <div style={{ fontFamily: MONO, fontSize: 12, fontWeight: 600, color: 'var(--gold)' }}>
        {model.model_codi || `#${model.model_id}`}
      </div>
      {model.model_nom && (
        <div style={{ fontSize: 11, color: 'var(--text-main)', lineHeight: 1.3 }}>{model.model_nom}</div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 10, color: 'var(--gray)' }}>{t('kanban.tasks_n', { n: total })}</span>
        <Count n={c.pending} color="var(--gray)" />
        <Count n={c.in_progress} color="var(--gold)" />
        <Count n={c.done} color="var(--ok)" />
      </div>
    </button>
  )
}

function GateRow({ gate, selected, onClick, onValidate, t }) {
  const [confirming, setConfirming] = useState(false)
  const to = nextPhase(gate.fase_actual)
  const miniBtn = {
    fontFamily: MONO, fontSize: 10, padding: '4px 8px', borderRadius: 6, cursor: 'pointer',
  }
  return (
    <div style={{
      border: `${selected ? '1px' : '0.5px'} solid ${AMBER_BORDER}`,
      background: selected ? CREMA : 'var(--gate, #fff8ec)', borderRadius: 8, overflow: 'hidden',
    }}>
      <button onClick={onClick} style={{
        textAlign: 'left', width: '100%', border: 'none', background: 'transparent',
        padding: '8px 10px', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 4,
      }}>
        <div style={{ fontFamily: MONO, fontSize: 12, fontWeight: 600, color: AMBER_TEXT }}>
          {gate.codi_intern || `#${gate.model_id}`}
        </div>
        <div style={{ fontSize: 10, color: 'var(--gray)' }}>
          {t('kanban.phase')}: {gate.fase_actual} · {t('kanban.tasks_n', { n: gate.task_count })}
        </div>
      </button>
      {selected && to && (
        <div style={{ padding: '0 10px 10px', display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {confirming ? (
            <>
              <span style={{ fontSize: 10, color: AMBER_TEXT, flex: '1 1 100%' }}>
                {t('kanban.gate_confirm', { phase: to })}
              </span>
              <button onClick={() => { setConfirming(false); onValidate(gate, to) }}
                style={{ ...miniBtn, border: 'none', background: 'var(--gold)', color: '#fff', fontWeight: 600 }}>
                {t('kanban.confirm')}
              </button>
              <button onClick={() => setConfirming(false)}
                style={{ ...miniBtn, border: '0.5px solid var(--gray-l)', background: 'var(--white)', color: 'var(--gray)' }}>
                {t('kanban.cancel')}
              </button>
            </>
          ) : (
            <button onClick={() => setConfirming(true)}
              style={{ ...miniBtn, border: `0.5px solid ${AMBER_BORDER}`, background: 'var(--white)', color: AMBER_TEXT, fontWeight: 600 }}>
              <i className="ti ti-check" style={{ fontSize: 11 }} /> {t('kanban.gate_validate')} → {to}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// Targeta de tasca (transicions + timer started_at + rectificació + 403). Reutilitzada del tauler previ.
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
