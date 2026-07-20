import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { models as modelsApi, commerce } from '../api/endpoints'
import ActionsMenu, { PHASES } from '../components/model/ActionsMenu'
import ModelsFilterPanel from '../components/model/ModelsFilterPanel'
import { useFilterOptions, garmentTypeLabel, garmentGroupLabel } from '../components/model/filterOptions'
import Feedback from '../components/ui/Feedback'

const MONO = 'IBM Plex Mono, monospace'
const SEASONS = ['SS', 'FW', 'CO', 'SP']
const PAGE_SIZE = 25
// Tots els keys de filtre que viuen a la URL (font de veritat + contracte de conjunt C2). Barra:
// search/fase_actual/temporada. Panell avançat: la resta.
const FILTER_KEYS = [
  'search', 'fase_actual', 'temporada', 'customer', 'collection', 'any',
  'garment_type__in', 'garment_type_item__in', 'garment_group_codi__in',
  'size_system', 'grading_rule_set', 'target', 'fit', 'construction',
  'responsable', 'assignee', 'task_type', 'task_status',
  'data_objectiu_after', 'data_objectiu_before', 'watchpoints_open', 'in_plan',
]
const fmtDate = (v, locale) => v ? new Date(v).toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: '2-digit' }) : '—'

export default function Models() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const dateLocale = i18n.language === 'es' ? 'es-ES' : i18n.language === 'en' ? 'en-GB' : 'ca-ES'

  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [feedback, setFeedback] = useState(null)
  const [selected, setSelected] = useState(() => new Set())
  const [newOpen, setNewOpen] = useState(false)
  // Selecció de CONJUNT filtrat (patró Gmail, C2): "tots els N del filtre" amb exclusions.
  const [selectAllFilter, setSelectAllFilter] = useState(false)
  const [excludeIds, setExcludeIds] = useState(() => new Set())

  // URL = FONT DE VERITAT dels filtres (useSearchParams): recarregar conserva l'estat i el contracte
  // de conjunt (C2) llegeix la URL tal qual. `search` té un mirall local per a la resposta de teclat;
  // se sincronitza a la URL amb debounce.
  const [sp, setSp] = useSearchParams()
  const search = sp.get('search') || ''
  const fase = sp.get('fase_actual') || ''
  const temporada = sp.get('temporada') || ''
  const page = Math.max(1, parseInt(sp.get('page') || '1', 10))
  const [searchInput, setSearchInput] = useState(search)

  // Escriu params a la URL (replace: sense inundar l'historial). Buit/undefined → esborra el key.
  const setParams = useCallback((patch) => {
    setSp(prev => {
      const next = new URLSearchParams(prev)
      Object.entries(patch).forEach(([k, v]) => {
        if (v === undefined || v === null || v === '') next.delete(k)
        else next.set(k, v)
      })
      return next
    }, { replace: true })
  }, [setSp])

  // Params de filtre enviats al backend (i base del contracte C2). Deriven NOMÉS de la URL.
  const spStr = sp.toString()
  const filterParams = useMemo(() => {
    const f = {}
    FILTER_KEYS.forEach(k => { const v = sp.get(k); if (v && v.trim()) f[k] = v.trim() })
    return f
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spStr])
  const filterKey = useMemo(() => JSON.stringify(filterParams), [filterParams])

  // MODE INTENCIÓ (Sprint C): s'hi arriba amb propòsit des d'una comanda/oferta.
  // ?select_for=<order_line|quote_line>:<id> & select_max=<N> & return=<path>. Aquests params NO
  // són a FILTER_KEYS → no viatgen al backend de list. El prefiltre customer sí (l'injecta l'origen).
  const intent = useMemo(() => {
    const raw = sp.get('select_for')
    if (!raw) return null
    const [kind, id] = raw.split(':')
    if (!['order_line', 'quote_line'].includes(kind) || !id) return null
    const max = parseInt(sp.get('select_max') || '', 10)
    return { kind, id, max: Number.isFinite(max) ? max : null, returnTo: sp.get('return') || '/models' }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spStr])
  const intentMode = !!intent

  // Per quote_line: models ja intencionats → s'exclouen de la llista (paritat E6, sense duplicats).
  const [intentExistingIds, setIntentExistingIds] = useState(() => new Set())
  useEffect(() => {
    if (!intent || intent.kind !== 'quote_line') { setIntentExistingIds(new Set()); return }
    let alive = true
    commerce.quoteLineIntents.list({ quote_line: intent.id, page_size: 500 })
      .then(r => { if (alive) setIntentExistingIds(new Set((r.data?.results ?? r.data ?? []).map(i => i.model))) })
      .catch(() => {})
    return () => { alive = false }
  }, [intent?.kind, intent?.id])

  // Opcions dels selects del panell (una sola càrrega, compartida amb els chips). Panell desplegable.
  const opts = useFilterOptions()
  const [panelOpen, setPanelOpen] = useState(false)

  // Comptador de filtres avançats actius (per al botó "Filtres · N"): agrupa els parells lligats.
  const advancedCount = useMemo(() => {
    const k = Object.keys(filterParams)
    let n = 0
    ;['customer', 'collection', 'any', 'size_system', 'grading_rule_set', 'target', 'fit',
      'construction', 'responsable', 'assignee', 'watchpoints_open', 'in_plan'].forEach(x => { if (k.includes(x)) n++ })
    if (k.some(x => x.startsWith('garment_'))) n++
    if (k.includes('task_type') || k.includes('task_status')) n++
    if (k.includes('data_objectiu_after') || k.includes('data_objectiu_before')) n++
    return n
  }, [filterParams])

  // garment-counts (facet: exclou la pròpia Peça) — només quan el panell és obert. fase-counts
  // (facet: exclou la fase) per anotar el select de fase amb el conjunt actiu.
  const [garmentCounts, setGarmentCounts] = useState({ by_type: {}, by_item: {} })
  const [faseCounts, setFaseCounts] = useState({})
  const countsKey = useMemo(() => {
    const p = { ...filterParams }
    delete p.garment_type__in; delete p.garment_type_item__in; delete p.garment_group_codi__in
    return JSON.stringify(p)
  }, [filterParams])
  const faseKey = useMemo(() => {
    const p = { ...filterParams }; delete p.fase_actual; return JSON.stringify(p)
  }, [filterParams])
  useEffect(() => {
    if (!panelOpen) return
    modelsApi.garmentCounts(JSON.parse(countsKey))
      .then(r => setGarmentCounts(r.data || { by_type: {}, by_item: {} })).catch(() => {})
  }, [countsKey, panelOpen])
  useEffect(() => {
    modelsApi.faseCounts(JSON.parse(faseKey)).then(r => setFaseCounts(r.data?.counts || {})).catch(() => {})
  }, [faseKey])

  const load = useCallback(() => {
    setLoading(true)
    modelsApi.list({ ...filterParams, ordering: '-data_entrada', page, page_size: PAGE_SIZE })
      .then(r => {
        const d = r.data
        setItems(Array.isArray(d) ? d : (d.results || []))
        setCount(d.count ?? (Array.isArray(d) ? d.length : 0))
      })
      .catch(() => { setItems([]); setCount(0) })
      .finally(() => setLoading(false))
  }, [filterParams, page])

  // Sincronitza l'input de cerca (mirall local) → URL amb debounce; reseteja pàgina en canviar.
  useEffect(() => { setSearchInput(search) }, [search])
  useEffect(() => {
    const id = setTimeout(() => { if (searchInput !== search) setParams({ search: searchInput, page: undefined }) }, 250)
    return () => clearTimeout(id)
  }, [searchInput])   // eslint-disable-line react-hooks/exhaustive-deps

  // Canviar qualsevol filtre invalida la selecció de conjunt (es defineix pels filtres actius). En
  // mode intenció NO es buida `selected`: la selecció individual persisteix mentre l'usuari refina
  // filtres per trobar més models (multi-select fins a N a través del filtratge).
  useEffect(() => {
    setSelectAllFilter(false); setExcludeIds(new Set())
    if (!intentMode) setSelected(new Set())
  }, [filterKey, intentMode])
  useEffect(() => { const id = setTimeout(load, 200); return () => clearTimeout(id) }, [load])

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))
  const selectedModels = useMemo(() => items.filter(m => selected.has(m.id)), [items, selected])
  const allOnPage = items.length > 0 && items.every(m => selected.has(m.id))
  const hasMoreThanPage = count > items.length

  const filterCount = Math.max(0, count - (selectAllFilter ? excludeIds.size : 0))
  const selCount = selectAllFilter ? filterCount : selected.size

  const toggle = (id) => setSelected(s => {
    const n = new Set(s)
    if (n.has(id)) { n.delete(id); return n }
    if (intent?.max != null && n.size >= intent.max) {   // cap a select_max (feedback visual)
      setFeedback({ type: 'err', text: t('models_intent.cap_reached', { n: intent.max }) })
      return n
    }
    n.add(id); return n
  })
  const clearConjunt = () => { setSelectAllFilter(false); setExcludeIds(new Set()); setSelected(new Set()) }

  // Confirmació del mode intenció: order_line → batch d'assignació; quote_line → bulk d'intents.
  // Èxit → torna a l'origen (els params es consumeixen en sortir). Error (p.ex. 400 de capacitat) →
  // mostra el missatge i NO navega (l'usuari ajusta la selecció).
  const confirmIntent = async () => {
    const ids = [...selected]
    if (!ids.length) return
    try {
      if (intent.kind === 'order_line') await commerce.orderLines.assignModels(intent.id, { model_ids: ids })
      else await commerce.quoteLineIntents.bulk({ quote_line: intent.id, model_ids: ids })
      navigate(intent.returnTo)
    } catch (e) {
      setFeedback({ type: 'err', text: e?.response?.data?.detail || t('models_intent.confirm_error') })
    }
  }
  const cancelIntent = () => navigate(intent.returnTo)

  // Per quote_line, exclou de la llista visible els models ja intencionats (paritat E6).
  const visibleItems = (intentMode && intent.kind === 'quote_line')
    ? items.filter(m => !intentExistingIds.has(m.id)) : items

  // Estat i acció del checkbox per fila (respecta el mode conjunt: marcat = no exclòs).
  const rowChecked = (id) => selectAllFilter ? !excludeIds.has(id) : selected.has(id)
  const rowToggle = (id) => {
    if (selectAllFilter) setExcludeIds(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
    else toggle(id)
  }
  const toggleAll = () => {
    if (selectAllFilter) { clearConjunt(); return }   // sortir del mode conjunt
    setSelected(s => {
      const n = new Set(s)
      if (allOnPage) items.forEach(m => n.delete(m.id)); else items.forEach(m => n.add(m.id))
      return n
    })
  }
  const afterAction = () => { setSelected(new Set()); setSelectAllFilter(false); setExcludeIds(new Set()); load() }

  const remove = async (m, e) => {
    e.stopPropagation()
    if (!window.confirm(t('models_list.confirm_delete', { codi: m.codi_intern }))) return
    try { await modelsApi.destroy(m.id); setFeedback({ type: 'ok', text: '✓' }); load() }
    catch { setFeedback({ type: 'err', text: t('models_list.delete_error') }) }
  }

  return (
    <div style={{ padding: '24px', maxWidth: 1240, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: 'var(--fs-h2)', fontFamily: MONO, color: 'var(--text-main)', fontWeight: 500, margin: 0 }}>{t('models_list.title')}</h1>
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, marginTop: 2 }}>
            {intentMode
              ? (intent.max != null
                  ? t('models_intent.counter', { x: selected.size, n: intent.max })
                  : t('models_intent.counter_open', { x: selected.size }))
              : (selCount > 0 ? t('models_list.selected', { n: selCount }) : t('models_list.count', { n: count }))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <NewModelMenu open={newOpen} setOpen={setNewOpen} navigate={navigate} t={t} />
          {/* Mode intenció: les accions genèriques (assignar/gate/…) no apliquen → ActionsMenu ocult. */}
          {!intentMode && (
            <ActionsMenu
              targets={selectAllFilter ? [] : selectedModels}
              selectionSet={selectAllFilter ? { filters: filterParams, excludeIds: [...excludeIds], count: filterCount } : null}
              onChanged={afterAction} onFeedback={setFeedback} />
          )}
        </div>
      </div>

      {intentMode && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', margin: '0 0 12px',
          background: 'var(--gold-pale)', border: '0.5px solid var(--gold)', borderRadius: 8,
          fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
          <i className="ti ti-arrow-back-up" aria-hidden="true" />
          {t('models_intent.banner')}
        </div>
      )}

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {/* Toolbar de filtres */}
      <div style={{ display: 'flex', gap: 8, margin: '12px 0', flexWrap: 'wrap', alignItems: 'center' }}>
        <input value={searchInput} onChange={e => setSearchInput(e.target.value)} placeholder={t('models_list.search_ph')}
          style={{ ...inp, flex: 1, minWidth: 220 }} />
        <select value={fase} onChange={e => setParams({ fase_actual: e.target.value, page: undefined })} style={inp}>
          <option value="">{t('models_list.all_phases')}</option>
          {PHASES.map(p => <option key={p} value={p}>{faseCounts[p] != null ? `${p} (${faseCounts[p]})` : p}</option>)}
        </select>
        <select value={temporada} onChange={e => setParams({ temporada: e.target.value, page: undefined })} style={inp}>
          <option value="">{t('models_list.all_seasons')}</option>
          {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button onClick={() => setPanelOpen(o => !o)}
          style={{ ...inp, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6,
            color: advancedCount ? 'var(--gold)' : 'var(--text-main)',
            borderColor: advancedCount ? 'var(--gold)' : 'var(--gray-l)', fontWeight: advancedCount ? 600 : 400 }}>
          <i className="ti ti-adjustments-horizontal" />
          {advancedCount ? t('models_filters.button_n', { n: advancedCount }) : t('models_filters.button')}
          <i className={`ti ti-chevron-${panelOpen ? 'up' : 'down'}`} />
        </button>
        {Object.keys(filterParams).length > 0 && (
          <button onClick={() => setParams(Object.fromEntries([...FILTER_KEYS, 'page']
            .filter(k => !(intentMode && k === 'customer')).map(k => [k, undefined])))}
            style={{ ...inp, cursor: 'pointer', color: 'var(--gray)' }}>× {t('models_list.clear')}</button>
        )}
      </div>

      {panelOpen && (
        <ModelsFilterPanel sp={sp} setParams={setParams} opts={opts} garmentCounts={garmentCounts}
          lockedKeys={intentMode ? ['customer'] : []} />
      )}

      <ActiveChips filterParams={filterParams} sp={sp} setParams={setParams} opts={opts} t={t} lang={i18n.language?.slice(0, 2) || 'ca'} FILTER_KEYS={FILTER_KEYS} lockedKeys={intentMode ? ['customer'] : []} />

      {/* Select all (pàgina) — OCULT en mode intenció (selecció individual limitada, no conjunt). */}
      {!intentMode && items.length > 0 && (
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, margin: '0 0 8px 2px', cursor: 'pointer' }}>
          <input type="checkbox" checked={selectAllFilter || allOnPage} onChange={toggleAll} />
          {(selectAllFilter || allOnPage) ? '✓' : ''}
        </label>
      )}

      {/* Banda "seleccionar tot el filtre" (patró Gmail): OCULTA en mode intenció (és l'oposat
          conceptual de "limitat a N"). Apareix quan la pàgina és plena i el filtre té més resultats. */}
      {!intentMode && (allOnPage || selectAllFilter) && hasMoreThanPage && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, flexWrap: 'wrap',
          background: 'var(--gold-pale)', border: '0.5px solid var(--gold)', borderRadius: 8,
          padding: '8px 14px', margin: '0 0 10px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-main)' }}>
          {selectAllFilter ? (
            <>
              <span>{t('models_list.selected_all_filter', { n: filterCount })}</span>
              <button onClick={clearConjunt} style={{ ...inp, cursor: 'pointer', color: 'var(--gold)', border: '0.5px solid var(--gold)', background: 'var(--white)' }}>
                {t('models_list.clear_selection')}
              </button>
            </>
          ) : (
            <>
              <span>{t('models_list.selected_page', { n: selectedModels.length })}</span>
              <button onClick={() => setSelectAllFilter(true)} style={{ ...inp, cursor: 'pointer', color: 'var(--gold)', border: '0.5px solid var(--gold)', background: 'var(--white)', fontWeight: 600 }}>
                {t('models_list.select_all_filter', { n: count })}
              </button>
            </>
          )}
        </div>
      )}

      {/* Llistat */}
      {loading ? (
        <div style={{ color: 'var(--gray)', fontSize: 'var(--fs-body)', fontFamily: MONO, padding: '20px 0' }}>{t('models_list.loading')}</div>
      ) : visibleItems.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--gray)', fontSize: 'var(--fs-body)', fontFamily: MONO }}>
          {(search || fase || temporada) ? t('models_list.empty_filtered') : t('models_list.empty')}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, paddingBottom: intentMode ? 64 : 0 }}>
          {visibleItems.map(m => (
            <ModelRow key={m.id} m={m} selected={rowChecked(m.id)} onToggle={() => rowToggle(m.id)}
              onOpen={intentMode ? () => rowToggle(m.id) : () => navigate(`/models/${m.id}`)}
              onDelete={(e) => remove(m, e)} t={t} locale={dateLocale} intentMode={intentMode} />
          ))}
        </div>
      )}

      {/* Paginació */}
      {pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 18, fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
          <button onClick={() => setParams({ page: Math.max(1, page - 1) })} disabled={page <= 1} style={{ ...inp, cursor: page <= 1 ? 'not-allowed' : 'pointer', opacity: page <= 1 ? 0.4 : 1 }}>← {t('models_list.prev')}</button>
          <span style={{ color: 'var(--gray)' }}>{t('models_list.page_info', { page, pages })}</span>
          <button onClick={() => setParams({ page: Math.min(pages, page + 1) })} disabled={page >= pages} style={{ ...inp, cursor: page >= pages ? 'not-allowed' : 'pointer', opacity: page >= pages ? 0.4 : 1 }}>{t('models_list.next')} →</button>
        </div>
      )}

      {/* Barra de confirmació fixa del mode intenció. */}
      {intentMode && (
        <div style={{ position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 50,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14, flexWrap: 'wrap',
          padding: '12px 20px', background: 'var(--white)', borderTop: '1px solid var(--gold)',
          boxShadow: '0 -4px 16px rgba(0,0,0,0.08)', fontFamily: MONO }}>
          <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
            {intent.max != null
              ? t('models_intent.counter', { x: selected.size, n: intent.max })
              : t('models_intent.counter_open', { x: selected.size })}
          </span>
          <button onClick={cancelIntent}
            style={{ ...inp, cursor: 'pointer', color: 'var(--gray)' }}>{t('models_intent.cancel')}</button>
          <button onClick={confirmIntent} disabled={!selected.size}
            style={{ ...inp, cursor: selected.size ? 'pointer' : 'not-allowed', opacity: selected.size ? 1 : 0.5,
              background: 'var(--gold)', color: 'var(--white)', border: '0.5px solid var(--gold)', fontWeight: 600 }}>
            {t('models_intent.confirm')}
          </button>
        </div>
      )}
    </div>
  )
}

// Chips de filtres actius sota la barra: cada filtre amb esborrat individual + "netejar tot". Els
// noms es resolen de les opcions carregades (opts), no del payload de la llista.
function ActiveChips({ filterParams, sp, setParams, opts, t, lang, FILTER_KEYS, lockedKeys = [] }) {
  const CSV = (v) => (v || '').split(',').filter(Boolean)
  const LABEL = {
    search: t('models_filters.f_search'), fase_actual: t('models_filters.f_phase'),
    temporada: t('models_filters.f_season'), customer: t('models_filters.customer'),
    collection: t('models_filters.collection'), any: t('models_filters.any'),
    size_system: t('models_filters.size_system'), grading_rule_set: t('models_filters.ruleset'),
    target: t('models_filters.target'), fit: t('models_filters.fit'),
    construction: t('models_filters.construction'), responsable: t('models_filters.responsable'),
    assignee: t('models_filters.assignee'), task_type: t('models_filters.task_type'),
    task_status: t('models_filters.task_status'), data_objectiu_after: t('models_filters.date_from'),
    data_objectiu_before: t('models_filters.date_to'), watchpoints_open: t('models_filters.watchpoints_open'),
    in_plan: t('models_filters.in_plan'),
  }
  const resolve = (k, v) => {
    const by = (list, idKey, labelKey) => list.find(x => String(x[idKey]) === String(v))?.[labelKey] || v
    switch (k) {
      case 'customer': return by(opts.customers, 'id', 'nom')
      case 'size_system': return opts.sizeSystems.find(s => String(s.id) === v)?.nom || v
      case 'grading_rule_set': return opts.rulesets.find(r => String(r.id) === v)?.nom || v
      case 'target': return opts.targets.find(x => x.codi === v)?.nom_en || v
      case 'fit': return opts.fits.find(x => x.codi === v)?.nom_en || v
      case 'construction': return opts.constructions.find(x => x.codi === v)?.nom_en || v
      case 'responsable': case 'assignee': return by(opts.users, 'profile_id', 'nom_complet')
      case 'task_type': return opts.taskTypes.find(tt => tt.code === v)?.name || v
      default: return v
    }
  }
  const removeCsv = (key, member) =>
    setParams({ [key]: CSV(sp.get(key)).filter(x => x !== String(member)).join(',') || undefined, page: undefined })

  const chips = []
  Object.keys(filterParams).forEach(k => {
    if (k.startsWith('garment_')) return
    if (!LABEL[k]) return
    const bool = k === 'watchpoints_open' || k === 'in_plan'
    chips.push({ id: k, text: bool ? LABEL[k] : `${LABEL[k]}: ${resolve(k, filterParams[k])}`,
      locked: lockedKeys.includes(k), remove: () => setParams({ [k]: undefined, page: undefined }) })
  })
  CSV(sp.get('garment_group_codi__in')).forEach(c => chips.push({ id: `gg${c}`, text: garmentGroupLabel(opts, c), remove: () => removeCsv('garment_group_codi__in', c) }))
  CSV(sp.get('garment_type__in')).forEach(id => chips.push({ id: `gt${id}`, text: garmentTypeLabel(opts, id, lang), remove: () => removeCsv('garment_type__in', id) }))
  CSV(sp.get('garment_type_item__in')).forEach(id => chips.push({ id: `gti${id}`, text: `#${id}`, remove: () => removeCsv('garment_type_item__in', id) }))

  if (!chips.length) return null
  const hasClearable = chips.some(c => !c.locked)
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', margin: '0 0 12px' }}>
      {chips.map(c => (
        <span key={c.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '3px 10px', borderRadius: 999,
          background: 'var(--gold-pale)', color: 'var(--gold)', border: '0.5px solid var(--gold)', fontFamily: MONO, fontSize: 'var(--fs-caption)', fontWeight: 600 }}>
          {c.locked && <i className="ti ti-lock" style={{ fontSize: 12 }} aria-hidden="true" />}
          {c.text}
          {!c.locked && (
            <button type="button" onClick={c.remove} aria-label={t('models_list.clear')}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: 0, lineHeight: 1 }}>
              <i className="ti ti-x" style={{ fontSize: 12 }} aria-hidden="true" />
            </button>
          )}
        </span>
      ))}
      {hasClearable && (
        <button type="button" onClick={() => setParams(Object.fromEntries(
          [...FILTER_KEYS, 'page'].filter(k => !lockedKeys.includes(k)).map(k => [k, undefined])))}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--gray)', fontFamily: MONO, fontSize: 'var(--fs-caption)', textDecoration: 'underline' }}>
          {t('models_filters.clear_all')}
        </button>
      )}
    </div>
  )
}

function ModelRow({ m, selected, onToggle, onOpen, onDelete, t, locale, intentMode }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'stretch', gap: 12, borderRadius: 8, background: 'var(--white)',
      border: `1px solid ${selected ? 'var(--gold)' : 'var(--gray-l)'}`,
      boxShadow: selected ? 'inset 0 0 0 1px var(--gold)' : 'none',
    }}>
      {/* Checkbox amb "rowspan" sobre les 2 files */}
      <label onClick={e => e.stopPropagation()} style={{ display: 'flex', alignItems: 'center', padding: '0 4px 0 14px', cursor: 'pointer' }}>
        <input type="checkbox" checked={selected} onChange={onToggle} style={{ width: 15, height: 15 }} />
      </label>

      <div onClick={onOpen} style={{ flex: 1, minWidth: 0, padding: '12px 16px 12px 0', cursor: 'pointer' }}>
        {/* Fila 1 — descriptiva */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
          <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 700, color: 'var(--gold)' }}>{m.codi_intern}</span>
          {m.nom_prenda && <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', fontWeight: 500 }}>{m.nom_prenda}</span>}
          {m.codi_client && <span style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO }}>· {m.codi_client}</span>}
          {m.collection && <span style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>· {m.collection}</span>}
          <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO }}>{m.temporada}{m.any ? ` ${m.any}` : ''}</span>
          <span title={t(m.has_order ? 'models_list.with_order_hint' : 'models_list.direct_hint')} style={{
            fontSize: 'var(--fs-caption)', padding: '2px 7px', borderRadius: 5, fontFamily: MONO,
            background: m.has_order ? 'var(--ok-bg)' : 'var(--gray-l)',
            color: m.has_order ? 'var(--ok)' : 'var(--gray)',
          }}>{t(m.has_order ? 'models_list.with_order' : 'models_list.direct')}</span>
          {!intentMode && <button onClick={onDelete} title={t('models_list.delete')} style={delBtn}><i className="ti ti-trash" /></button>}
        </div>
        {/* Fila 2 — operativa */}
        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr 1fr 1fr 1.4fr', gap: 12, alignItems: 'center', fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
          <span style={faseBadge}>{m.fase_actual ? t(`model_sheet.dashboard.phase.${m.fase_actual}`, m.fase_actual) : '—'}</span>
          <Cell label={t('models_list.col_entrada')} value={fmtDate(m.entrada_prod, locale)} />
          <Cell label={t('models_list.col_proto')} value={fmtDate(m.arribada_proto, locale)} />
          <Cell label={t('models_list.col_fitting')} value={fmtDate(m.fitting_prev, locale)} />
          <Tecnic label={t('models_list.col_tecnic')} tecnics={m.tecnics} />
        </div>
      </div>
    </div>
  )
}

function Cell({ label, value }) {
  return (
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 'var(--fs-caption)', textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--gray)' }}>{label}</div>
      <div style={{ color: value === '—' ? 'var(--gray-l)' : 'var(--text-main)' }}>{value}</div>
    </div>
  )
}

function Tecnic({ label, tecnics }) {
  const list = tecnics || []
  const principal = list[0]
  return (
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 'var(--fs-caption)', textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--gray)' }}>{label}</div>
      {principal ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: principal.color || 'var(--gray)', flex: 'none' }} />
          <span style={{ color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{principal.nom}</span>
          {list.length > 1 && <span style={{ color: 'var(--gray)' }}>+{list.length - 1}</span>}
        </div>
      ) : <div style={{ color: 'var(--gray-l)' }}>—</div>}
    </div>
  )
}

function NewModelMenu({ open, setOpen, navigate, t }) {
  return (
    <div style={{ position: 'relative' }}>
      <button onClick={() => setOpen(o => !o)} style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--white)', color: 'var(--gold)', border: '0.5px solid var(--gold)', borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', fontWeight: 600, cursor: 'pointer', fontFamily: MONO }}>
        <i className="ti ti-plus" /> {t('models_list.new_model')} <i className="ti ti-chevron-down" />
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 40 }} />
          <div style={{ position: 'absolute', right: 0, top: 'calc(100% + 4px)', zIndex: 41, background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4, minWidth: 200 }}>
            <button onClick={() => { setOpen(false); navigate('/models/nou') }} style={menuItem}><i className="ti ti-edit" /> {t('models_list.manual')}</button>
            <button onClick={() => { setOpen(false); navigate('/models/importar-colleccio') }} style={menuItem}>
              <i className="ti ti-file-spreadsheet" /> {t('nav.import_collection')}
            </button>
          </div>
        </>
      )}
    </div>
  )
}

const inp = { padding: '6px 10px', border: '0.5px solid var(--gray-l)', borderRadius: 6, fontSize: 'var(--fs-body)', fontFamily: MONO, background: 'var(--white)', color: 'var(--text-main)' }
const faseBadge = { fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, padding: '2px 8px', borderRadius: 12, background: 'var(--gold)', color: 'var(--white)', justifySelf: 'start' }
const delBtn = { fontSize: 'var(--fs-body)', color: '#C0392B', background: 'none', border: '0.5px solid #FADBD8', borderRadius: 4, padding: '2px 7px', cursor: 'pointer', fontFamily: MONO }
const menuItem = { display: 'flex', alignItems: 'center', gap: 8, width: '100%', textAlign: 'left', background: 'none', border: 'none', padding: '8px 10px', borderRadius: 6, fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)', cursor: 'pointer' }
