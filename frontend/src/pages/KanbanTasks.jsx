import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { modelTasks, gates, models, garmentTypes, users } from '../api/endpoints'
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
  Pending:    [{ to: 'InProgress', key: 'start',  icon: 'ti-player-play' }],
  Paused:     [{ to: 'InProgress', key: 'resume', icon: 'ti-player-play' }],
  InProgress: [{ to: 'Paused', key: 'pause', icon: 'ti-player-pause' },
               { to: 'Done', key: 'finish', icon: 'ti-check' }],
  Done:       [{ to: 'InProgress', key: 'reopen', icon: 'ti-rotate-clockwise' }],
}

// Un model és ACTIU si té alguna tasca InProgress o Paused (dades ja al by-model).
const isActiveModel = (m) => (m?.counts?.in_progress > 0 || m?.counts?.paused > 0)

// Ordenació (whitelist mirall del backend) i choices reals del Model per als filtres ràpids.
const SORT_FIELDS = ['codi_intern', 'nom_prenda', 'prioritat', 'data_objectiu', 'data_entrada', 'temporada']
const TEMPORADES = ['SS', 'FW', 'CO', 'SP']
const ESTATS = ['Nou', 'EnCurs', 'EnRevisio', 'Tancat']

// Fases del gate (Proto→…→TOP). Validar avança a la següent.
const PHASES = ['Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']
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
  const canViewTeam = !!user?.capabilities?.includes('view_team_tasks')

  // Columna 1 — models (paginada) + cartes de gate (Prioritat A).
  const [search, setSearch] = useState('')
  const [modelRows, setModelRows] = useState([])
  const [modelsCount, setModelsCount] = useState(0)   // total de la resposta (no només la pàgina)
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [loadingModels, setLoadingModels] = useState(true)

  // Ordenació + filtres ràpids (tot passa al backend; el front no filtra/ordena → escala 600+).
  const [sortField, setSortField] = useState('')      // '' = ordre per defecte del backend
  const [sortDir, setSortDir] = useState('asc')
  const [fTemporada, setFTemporada] = useState('')
  const [fEstat, setFEstat] = useState('')
  const [fResponsable, setFResponsable] = useState('') // '' = tots · 'me' = l'usuari actual
  const [fGarmentType, setFGarmentType] = useState('')
  const [fAny, setFAny] = useState('')
  const [fPrioritat, setFPrioritat] = useState('')
  const [showMore, setShowMore] = useState(false)
  const [garmentTypeOpts, setGarmentTypeOpts] = useState([])
  const [gateCards, setGateCards] = useState([])
  const [selected, setSelected] = useState(null)   // { type:'model'|'gate', id, ... }
  const [allUsers, setAllUsers] = useState([])     // selector de tècnic (només amb view_team_tasks)

  // Detall — tasques del model seleccionat (alimenten les 4 columnes de treball).
  const [detailTasks, setDetailTasks] = useState([])
  const [loadingDetail, setLoadingDetail] = useState(false)

  const [toast, setToast] = useState(null)          // { type, text }
  const toastTimer = useRef(null)
  const loadingRef = useRef(false)                  // guard anti-doble-càrrega del scroll infinit
  const sentinelRef = useRef(null)                  // observat per l'IntersectionObserver
  function showToast(type, text) {
    setToast({ type, text })
    if (toastTimer.current) clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 3000)
  }

  // Càrrega d'una pàgina de by-model amb cerca+ordenació+filtres. replace=true reinicia
  // (canvi de qualsevol criteri); si no, hi afegeix (load more / scroll).
  const loadPage = useCallback((pageToLoad, replace) => {
    loadingRef.current = true
    setLoadingModels(true)
    const p = { page: pageToLoad }
    const s = search.trim(); if (s) p.search = s
    if (sortField) p.ordering = (sortDir === 'desc' ? '-' : '') + sortField
    if (fTemporada) p.temporada = fTemporada
    if (fEstat) p.estat = fEstat
    if (fResponsable) p.responsable = fResponsable
    if (fGarmentType) p.garment_type = fGarmentType
    if (fAny) p.any = fAny
    if (fPrioritat) p.prioritat = fPrioritat
    modelTasks.byModel(p)
      .then(res => {
        const data = res.data
        const results = data?.results ?? (Array.isArray(data) ? data : [])
        setModelRows(prev => (replace ? results : [...prev, ...results]))
        setHasNext(!!data?.next)
        setModelsCount(typeof data?.count === 'number' ? data.count : results.length)
      })
      .catch(() => { if (replace) { setModelRows([]); setHasNext(false); setModelsCount(0) } })
      .finally(() => { loadingRef.current = false; setLoadingModels(false) })
  }, [search, sortField, sortDir, fTemporada, fEstat, fResponsable, fGarmentType, fAny, fPrioritat])

  // Qualsevol canvi de criteri (debounce) → reinicia a pàgina 1 i recarrega.
  useEffect(() => {
    const id = setTimeout(() => { setPage(1); loadPage(1, true) }, 300)
    return () => clearTimeout(id)
  }, [loadPage])

  // Opcions de tipus de peça per al filtre "Més filtres" (un sol cop).
  useEffect(() => {
    garmentTypes.list().then(res => setGarmentTypeOpts(res.data?.results ?? res.data ?? [])).catch(() => {})
  }, [])

  // Usuaris actius per al selector de tècnic (només amb view_team_tasks; lectura IsAuthenticated).
  useEffect(() => {
    if (!canViewTeam) return
    users.list({ page_size: 100 })
      .then(res => setAllUsers(res.data?.results ?? res.data ?? []))
      .catch(() => setAllUsers([]))
  }, [canViewTeam])

  // FIX orfes: si el model seleccionat ja no és a la llista filtrada (canvi de filtre/cerca),
  // neteja la selecció perquè les columnes de detall no mostrin tasques d'un model fora de l'abast.
  // Només per a seleccions de tipus 'model' (les gates viuen en una llista a part).
  useEffect(() => {
    if (selected?.type !== 'model' || modelRows.length === 0) return
    if (!modelRows.some(r => r.model_id === selected.id)) {
      setSelected(null)
      setDetailTasks([])
    }
  }, [modelRows, selected])

  function clearFilters() {
    setSortField(''); setSortDir('asc')
    setFTemporada(''); setFEstat(''); setFResponsable('')
    setFGarmentType(''); setFAny(''); setFPrioritat('')
  }

  // Prioritat A: cartes de gate (només si close_gates).
  const loadGates = useCallback(() => {
    gates.ready().then(res => setGateCards(res.data?.ready ?? [])).catch(() => setGateCards([]))
  }, [])
  useEffect(() => { if (canCloseGates) loadGates() }, [canCloseGates, loadGates])

  const loadMore = useCallback(() => {
    if (loadingRef.current || !hasNext) return
    const next = page + 1
    setPage(next)
    loadPage(next, false)
  }, [hasNext, page, loadPage])

  // Scroll infinit: quan el sentinella entra a la vista i hi ha `next`, carrega la pàgina següent.
  useEffect(() => {
    const el = sentinelRef.current
    if (!el || !hasNext) return
    const obs = new IntersectionObserver(
      entries => { if (entries[0].isIntersecting) loadMore() },
      { rootMargin: '150px' },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [hasNext, loadMore])

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

  // (b) Auto-obrir en entrar: si cap model seleccionat i n'hi ha amb tasques actives
  // (InProgress/Paused), obre directament el primer (l'ordre ja els posa a dalt).
  useEffect(() => {
    if (selected || modelRows.length === 0) return
    const firstActive = modelRows.find(isActiveModel)
    if (firstActive) setSelected({ type: 'model', id: firstActive.model_id, ...firstActive })
  }, [modelRows, selected])

  // Polling: refresca dades cada 30s si la pestanya és visible (entorn multi-usuari).
  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === 'visible') {
        loadPage(1, true)            // recarrega la 1a pàgina de models
        if (selectedId) loadDetail(selectedId)
      }
    }
    const id = setInterval(tick, 30000)
    return () => clearInterval(id)
  }, [selectedId, loadPage, loadDetail])

  // (a) Ordre de visualització: models ACTIUS (InProgress/Paused) a dalt, preservant la resta
  // de l'ordre del backend (sort estable). Sense canvi backend; dades ja al by-model.
  const displayRows = [...modelRows].sort(
    (a, b) => (isActiveModel(b) ? 1 : 0) - (isActiveModel(a) ? 1 : 0))

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
        // Re-sincronitza el detall amb l'estat real del backend (la tasca pot haver canviat
        // per un altre usuari → la targeta local era obsoleta).
        if (selectedId) loadDetail(selectedId)
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
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4 }}>{t('kanban.title')}</h1>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('kanban.subtitle')}</p>
      </div>

      {/* Barra SOBRE el grid: cerca + ordenació + filtres ràpids (tot va al backend). */}
      <div style={{ marginBottom: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder={t('kanban.search_ph')}
            style={{ ...selS, flex: '0 1 300px', minWidth: 200 }}
          />
          {/* Ordenació */}
          <select value={sortField} onChange={e => setSortField(e.target.value)} style={selS} title={t('kanban.sort_by')}>
            <option value="">{t('kanban.sort_default')}</option>
            {SORT_FIELDS.map(f => <option key={f} value={f}>{t(`kanban.sort.${f}`)}</option>)}
          </select>
          <button
            onClick={() => setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))}
            disabled={!sortField} title={t(sortDir === 'desc' ? 'kanban.sort_desc' : 'kanban.sort_asc')}
            style={{ ...selS, cursor: sortField ? 'pointer' : 'default', opacity: sortField ? 1 : 0.5, padding: '6px 9px' }}
          >
            <i className={`ti ${sortDir === 'desc' ? 'ti-sort-descending' : 'ti-sort-ascending'}`} style={{ fontSize: 14 }} />
          </button>
          {/* Any (primera línia, abans de Temporada) */}
          <input
            type="number" value={fAny} onChange={e => setFAny(e.target.value)}
            placeholder={t('kanban.filter_any')} style={{ ...selS, width: 100 }}
          />
          {/* Temporada */}
          <select value={fTemporada} onChange={e => setFTemporada(e.target.value)} style={selS}>
            <option value="">{t('kanban.filter_temporada')}</option>
            {TEMPORADES.map(x => <option key={x} value={x}>{t(`kanban.temporades.${x}`)}</option>)}
          </select>
          {/* Estat */}
          <select value={fEstat} onChange={e => setFEstat(e.target.value)} style={selS}>
            <option value="">{t('kanban.filter_estat')}</option>
            {ESTATS.map(x => <option key={x} value={x}>{t(`kanban.estats.${x}`)}</option>)}
          </select>
          {/* Responsable (models on l'usuari triat és ASSIGNEE, no director): només amb
              view_team_tasks. Tots / Jo / [selector de tècnic]. Sense la capability l'usuari
              ja veu només les seves tasques → toggle sense sentit. */}
          {canViewTeam && (() => {
            // El selector està actiu quan fResponsable és un profile_id (numèric).
            const techSelected = !!fResponsable && fResponsable !== 'me'
            return (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }} title={t('kanban.resp_hint')}>
                <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('kanban.filter_responsable')}</span>
                <div style={{ display: 'flex', border: '0.5px solid var(--gray-l)', borderRadius: 8, overflow: 'hidden' }}>
                  {[['', 'resp_all'], ['me', 'resp_me']].map(([val, key]) => (
                    <button key={key} onClick={() => setFResponsable(val)} style={{
                      fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 10px', border: 'none', cursor: 'pointer',
                      background: fResponsable === val ? CREMA : 'var(--white)',
                      color: fResponsable === val ? AMBER_TEXT : 'var(--gray)',
                      fontWeight: fResponsable === val ? 600 : 400,
                    }}>{t(`kanban.${key}`)}</button>
                  ))}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  {techSelected && (
                    <ColorDot color={allUsers.find(u => String(u.profile_id) === fResponsable)?.color_avatar} />
                  )}
                  <select
                    value={techSelected ? fResponsable : ''}
                    onChange={e => setFResponsable(e.target.value)}
                    style={{
                      ...selS, minWidth: 120, padding: '6px 9px',
                      background: techSelected ? CREMA : 'var(--white)',
                      color: techSelected ? AMBER_TEXT : 'var(--gray)',
                    }}>
                    <option value="">{t('kanban.resp_tech_placeholder')}</option>
                    {allUsers.filter(u => u.profile_id).map(u => (
                      <option key={u.profile_id} value={String(u.profile_id)}>{u.full_name || u.username}</option>
                    ))}
                  </select>
                </div>
              </div>
            )
          })()}
          <button onClick={() => setShowMore(s => !s)} style={{
            ...selS, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
          }}>
            <i className={`ti ${showMore ? 'ti-chevron-up' : 'ti-adjustments-horizontal'}`} style={{ fontSize: 13 }} />
            {t('kanban.more_filters')}
          </button>
          <button onClick={clearFilters} style={{
            fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 10px', borderRadius: 8,
            border: '0.5px solid var(--gray-l)', background: 'var(--white)', color: 'var(--gray)', cursor: 'pointer',
          }}>
            <i className="ti ti-x" style={{ fontSize: 12 }} /> {t('kanban.clear_filters')}
          </button>
          <span style={{ marginLeft: 'auto', fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>
            {t('kanban.results_n', { n: modelsCount })}
          </span>
        </div>

        {/* Més filtres */}
        {showMore && (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <select value={fGarmentType} onChange={e => setFGarmentType(e.target.value)} style={selS}>
              <option value="">{t('kanban.filter_garment_type')}</option>
              {garmentTypeOpts.map(g => (
                <option key={g.id} value={g.id}>{g.nom_client || g.global_nom || `#${g.id}`}</option>
              ))}
            </select>
            <select value={fPrioritat} onChange={e => setFPrioritat(e.target.value)} style={selS}>
              <option value="">{t('kanban.filter_prioritat')}</option>
              {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        )}
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
            <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500 }}>{t('kanban.col_models')}</span>
            <span style={{
              marginLeft: 'auto', fontSize: 'var(--fs-body)', color: AMBER_TEXT,
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
              ) : displayRows.map(m => (
                <ModelRow
                  key={m.model_id} model={m} t={t}
                  selected={selected?.type === 'model' && selected.id === m.model_id}
                  onClick={() => setSelected({ type: 'model', id: m.model_id, ...m })}
                />
              ))}
            </div>
            {/* Scroll infinit: sentinella observat + indicador discret de càrrega al peu */}
            {hasNext && <div ref={sentinelRef} style={{ height: 1 }} aria-hidden="true" />}
            {loadingModels && modelRows.length > 0 && (
              <div style={{ ...ph, padding: '0.6rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                <i className="ti ti-loader-2" style={{ fontSize: 12 }} /> {t('kanban.loading')}
              </div>
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
                <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500 }}>{t(`kanban.status.${col.key}`)}</span>
                <span style={{
                  marginLeft: 'auto', fontSize: 'var(--fs-body)', color: 'var(--gray)',
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
          fontSize: 'var(--fs-body)', padding: '10px 16px', borderRadius: 8, boxShadow: '0 6px 24px rgba(0,0,0,0.18)',
          background: toast.type === 'err' ? 'var(--err-bg)' : toast.type === 'warn' ? 'var(--warn-bg)' : 'var(--ok-bg)',
          color: toast.type === 'err' ? 'var(--err)' : toast.type === 'warn' ? 'var(--warn)' : 'var(--ok)',
        }}>{toast.text}</div>
      )}
    </div>
  )
}

const ph = { fontSize: 'var(--fs-body)', color: 'var(--gray)', textAlign: 'center', padding: '1.2rem', fontWeight: 300 }
const selS = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 9px', border: '0.5px solid var(--gray-l)',
  borderRadius: 8, background: 'var(--white)', color: 'var(--text-main)',
}

// Punt de color (avatar de tècnic) per al selector de responsable.
function ColorDot({ color }) {
  return (
    <span style={{
      width: 12, height: 12, borderRadius: '50%', flexShrink: 0,
      background: color || '#888888', display: 'inline-block',
    }} />
  )
}

function ColTitle({ icon, text, amber }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8,
      fontFamily: MONO, fontSize: 'var(--fs-label)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.04em',
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
      fontSize: 'var(--fs-label)', fontVariantNumeric: 'tabular-nums', color,
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
      <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--gold)' }}>
        {model.model_codi || `#${model.model_id}`}
      </div>
      {model.model_nom && (
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', lineHeight: 1.3 }}>{model.model_nom}</div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>{t('kanban.tasks_n', { n: total })}</span>
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
    fontFamily: MONO, fontSize: 'var(--fs-label)', padding: '4px 8px', borderRadius: 6, cursor: 'pointer',
  }
  return (
    <div style={{
      border: `${selected ? '1px' : '0.5px'} solid ${AMBER_BORDER}`,
      background: selected ? CREMA : 'var(--gate)', borderRadius: 8, overflow: 'hidden',
    }}>
      <button onClick={onClick} style={{
        textAlign: 'left', width: '100%', border: 'none', background: 'transparent',
        padding: '8px 10px', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 4,
      }}>
        <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, color: AMBER_TEXT }}>
          {gate.codi_intern || `#${gate.model_id}`}
        </div>
        <div style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>
          {t('kanban.phase')}: {gate.fase_actual} · {t('kanban.tasks_n', { n: gate.task_count })}
        </div>
      </button>
      {selected && to && (
        <div style={{ padding: '0 10px 10px', display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {confirming ? (
            <>
              <span style={{ fontSize: 'var(--fs-label)', color: AMBER_TEXT, flex: '1 1 100%' }}>
                {t('kanban.gate_confirm', { phase: to })}
              </span>
              <button onClick={() => { setConfirming(false); onValidate(gate, to) }}
                style={{ ...miniBtn, border: 'none', background: 'var(--gold)', color: 'var(--white)', fontWeight: 600 }}>
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
  const navigate = useNavigate()
  // Tasca de POM: porta d'entrada a la pantalla de mides de l'item (materialitza la pertinença).
  const isPom = task.task_type_code === 'pom'
  // Tasca de fitxa tècnica: porta d'entrada a l'editor full-screen de la fitxa.
  const isTechSheet = task.task_type_code === 'tech_sheet'
  // Tasca de size check: porta d'entrada a la graella de validació del proto a talla base.
  const isSizeCheck = task.task_type_code === 'size_check'
  return (
    <div style={{
      border: '0.5px solid var(--gray-l)', borderRadius: 8,
      padding: '0.7rem 0.8rem', background: 'var(--white)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--gold)', fontWeight: 500 }}>
          {task.model_codi || `#${task.model}`}
        </span>
        {task.rectifications > 0 && (
          <span title={t('kanban.rect', { n: task.rectifications })} style={{
            fontSize: 'var(--fs-label)', color: 'var(--warn)', background: 'var(--warn-bg)',
            padding: '1px 6px', borderRadius: 8, whiteSpace: 'nowrap',
          }}>
            <i className="ti ti-rotate-clockwise" style={{ fontSize: 10 }} /> {task.rectifications}
          </span>
        )}
      </div>
      <div style={{ fontSize: 'var(--fs-body)', lineHeight: 1.4 }}>
        {task.task_type_name || task.task_type_code}
      </div>
      {task.status === 'InProgress' && task.started_at && (
        <div style={{ marginTop: 6 }}>
          <TimerWidget inici={task.started_at} compact />
        </div>
      )}
      {isPom && (
        <div style={{ marginTop: 8 }}>
          <button onClick={() => {
            // Sprint B · auto-iniciar: obrir mides posa la tasca pom En curs si estava
            // Pending/Paused (l'exclusió mútua — auto-pausar l'altra InProgress — la fa
            // transition_task al backend). Fire-and-forget: navega igualment sense bloquejar,
            // i si la transició falla no atura l'obertura de la pantalla de mides.
            if (canExecute && (task.status === 'Pending' || task.status === 'Paused')) {
              onTransition(task, 'InProgress')
            }
            navigate(`/models/${task.model}/mesures`)
          }} style={{
            display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--fs-body)', padding: '4px 8px',
            borderRadius: 6, border: '0.5px solid var(--gold)', background: 'var(--white)',
            cursor: 'pointer', color: 'var(--gold)', fontWeight: 500,
          }}>
            <i className="ti ti-ruler-2" style={{ fontSize: 12 }} />
            {t('kanban.action.open_poms', 'Obrir mides')}
          </button>
        </div>
      )}
      {isTechSheet && (
        <div style={{ marginTop: 8 }}>
          <button onClick={() => {
            // Mateix patró que isPom: auto-iniciar (fire-and-forget) i obrir l'editor de fitxa.
            if (canExecute && (task.status === 'Pending' || task.status === 'Paused')) {
              onTransition(task, 'InProgress')
            }
            navigate(`/models/${task.model}/fitxa?task_id=${task.id}`)
          }} style={{
            display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--fs-body)', padding: '4px 8px',
            borderRadius: 6, border: '0.5px solid var(--gold)', background: 'var(--white)',
            cursor: 'pointer', color: 'var(--gold)', fontWeight: 500,
          }}>
            <i className="ti ti-file-text" style={{ fontSize: 12 }} />
            {t('kanban.action.open_tech_sheet', 'Obrir fitxa')}
          </button>
        </div>
      )}
      {isSizeCheck && (
        <div style={{ marginTop: 8 }}>
          <button onClick={() => {
            // Mateix patró que isPom: auto-iniciar (fire-and-forget) i obrir la graella
            // del size check en mode treball (editable). L'exclusió mútua i el timer els fa
            // transition_task al backend (cicle genèric, cap codi especial per size_check).
            if (canExecute && (task.status === 'Pending' || task.status === 'Paused')) {
              onTransition(task, 'InProgress')
            }
            navigate(`/models/${task.model}/size-check`)
          }} style={{
            display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--fs-body)', padding: '4px 8px',
            borderRadius: 6, border: '0.5px solid var(--gold)', background: 'var(--white)',
            cursor: 'pointer', color: 'var(--gold)', fontWeight: 500,
          }}>
            <i className="ti ti-ruler-measure" style={{ fontSize: 12 }} />
            {t('kanban.action.open_size_check', 'Obrir size check')}
          </button>
        </div>
      )}
      {canExecute && actions.length > 0 && (
        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
          {actions.map(a => (
            <button key={a.key} onClick={() => onTransition(task, a.to)} style={{
              display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--fs-body)', padding: '4px 8px',
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
