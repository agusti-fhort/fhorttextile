import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { models as modelsApi, commerce } from '../api/endpoints'
import ActionsMenu from '../components/model/ActionsMenu'
import { MaduresaBadge } from '../components/model/FederacioBadge'
import BadgeLliurable from '../components/model/BadgeLliurable'
import ModelsFilterPanel from '../components/model/ModelsFilterPanel'
import { useFilterOptions, garmentTypeLabel, garmentGroupLabel } from '../components/model/filterOptions'
import Feedback from '../components/ui/Feedback'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import { useEnumeracio } from '../utils/vocabulariDominiFont'

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

// ORDENACIÓ · l'ordre per defecte de sempre (entrada més recent a dalt). Es fa servir tal qual
// com a `ordering` del backend i com a estat inicial de la icona de la capçalera.
const ORDRE_DEFECTE = { camp: 'data_entrada', dir: 'desc' }
// La «Temp.» és una columna de DUES dades (temporada + any) i el que un humà hi busca és
// l'ordre CRONOLÒGIC: primer l'any, i dins de l'any la temporada. DRF ho accepta separat per
// comes; els dos camps són a `ordering_fields` del ViewSet.
const ORDERING_API = { temporada: ['any', 'temporada'] }
const aOrdering = (o) => (ORDERING_API[o.camp] || [o.camp]).map(c => (o.dir === 'desc' ? `-${c}` : c)).join(',')

export default function Models() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const dateLocale = i18n.language === 'es' ? 'es-ES' : i18n.language === 'en' ? 'en-GB' : 'ca-ES'

  // A5 · §8e — la graella canònica NO té columna de RECURS (P7 · `studio_assignat`) ni de
  // TÈCNIC («Tècnic assignat FORA de les llistes de models: viu a Planificació»). Les dues
  // dades segueixen viatjant al serializer i vives a la fitxa del model; el que se'n va és la
  // columna. Per això aquesta pantalla ja no ha de saber si el tenant és marca o estudi.
  // Les fases del filtre venen de `/vocabulari/` (`fases_model`), no d'una constant importada
  // d'`ActionsMenu` —que era una llista escrita a mà que aquesta pantalla reexportava sense
  // saber-ho—. Sense vocabulari el filtre no ofereix cap fase: «totes» segueix funcionant.
  const { codis: fases } = useEnumeracio('fases_model')
  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  // §8e — «el comptador ÉS selecció, no KPI, i ELS VALORS MANEN»: «12/84». El primer número és
  // el resultat del filtre (`count`); el segon, el CENS SENCER del tenant, que no es pot
  // deduir d'una pàgina de 25 i per això es demana un cop, a part.
  const [total, setTotal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [feedback, setFeedback] = useState(null)
  const [selected, setSelected] = useState(() => new Set())
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

  // §8e · FILTRES RÀPIDS DE VISTA AL MENÚ: «els elements acabats NO es llisten per defecte».
  // 🚩 PROVISIONAL-DOMINI — el criteri exacte de «model acabat» encara no existeix: l'estat
  // comercial el mana el Kanban i el Kanban no hi és. Mentre no hi sigui, la vista «acabats»
  // NO endevina res: no demana res al backend i ho diu escrit. Inventar-hi un criteri (fase
  // TOP? `estat='Tancat'`? `data_tancament`?) seria posar una decisió de domini dins d'un tram
  // de pell, i la llista de «en curs» quedaria amputada sense que ningú ho hagués decidit.
  const vista = sp.get('vista') === 'acabats' ? 'acabats' : 'curs'

  // ORDENACIÓ a la URL (`ordering`), com la resta de l'estat de la llista: recarregar la
  // conserva i es pot enllaçar. Es guarda com el backend l'espera (`-camp`).
  const ordre = useMemo(() => {
    const raw = sp.get('ordering')
    if (!raw) return ORDRE_DEFECTE
    const desc = raw.startsWith('-')
    const camp = (desc ? raw.slice(1) : raw).split(',')[0]
    // «any» és el primer camp de l'ordenació composta de Temp.: la capçalera que mana és Temp.
    return { camp: camp === 'any' ? 'temporada' : camp, dir: desc ? 'desc' : 'asc' }
  }, [sp])

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

  // Clicar una capçalera: si ja mana, inverteix; si no, entra descendent (el més recent /
  // el més alt primer, que és el que s'espera d'una llista de treball).
  const ordenar = useCallback((camp) => {
    const dir = (ordre.camp === camp && ordre.dir === 'desc') ? 'asc' : 'desc'
    setParams({ ordering: aOrdering({ camp, dir }), page: undefined })
  }, [ordre, setParams])

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
    // Vista «acabats»: cap criteri de domini → cap crida i cap fila inventada (v. `vista`).
    if (vista === 'acabats') { setItems([]); setCount(0); setLoading(false); return }
    setLoading(true)
    modelsApi.list({ ...filterParams, ordering: aOrdering(ordre), page, page_size: PAGE_SIZE })
      .then(r => {
        const d = r.data
        setItems(Array.isArray(d) ? d : (d.results || []))
        setCount(d.count ?? (Array.isArray(d) ? d.length : 0))
      })
      .catch(() => { setItems([]); setCount(0) })
      .finally(() => setLoading(false))
  }, [filterParams, page, ordre, vista])

  // El DENOMINADOR del comptador: el cens sencer, sense cap filtre. Una sola fila demanada
  // (`page_size=1`): l'únic que se'n vol és el `count`.
  const carregaTotal = useCallback(() => {
    modelsApi.list({ page_size: 1 }).then(r => setTotal(r.data?.count ?? null)).catch(() => setTotal(null))
  }, [])
  useEffect(() => { carregaTotal() }, [carregaTotal])

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
  // El comptador de dalt ja NO diu «N seleccionats» (§8e: el comptador és el resultat del
  // FILTRE, «12/84»). Qui diu quants n'hi ha de triats és el mateix menú d'accions —«Accions
  // (3)»— i la banda de conjunt; el número de la capçalera té un sol significat.

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
  const afterAction = () => { setSelected(new Set()); setSelectAllFilter(false); setExcludeIds(new Set()); load(); carregaTotal() }

  const remove = async (m, e) => {
    e.stopPropagation()
    if (!window.confirm(t('models_list.confirm_delete', { codi: m.codi_intern }))) return
    try { await modelsApi.destroy(m.id); setFeedback({ type: 'ok', text: '✓' }); load(); carregaTotal() }
    catch { setFeedback({ type: 'err', text: t('models_list.delete_error') }) }
  }

  // ── LES COLUMNES DEL CANÒNIC (NORMA_LLISTA_canonica.html) ─────────────────────────────
  // Amplades PER CONTINGUT, no iguals: refs estretes, la dada reina generosa, dates fixes.
  const cols = useMemo(() => [
    {
      key: 'chk', amplada: 30,
      render: (m) => (
        <input type="checkbox" checked={rowChecked(m.id)} onClick={e => e.stopPropagation()}
          onChange={() => rowToggle(m.id)} aria-label={m.codi_intern}
          style={{ width: 14, height: 14, accentColor: 'var(--gold)', display: 'block' }} />
      ),
    },
    {
      key: 'codi_intern', label: t('models_list.col_ref_intern'), min: 118, max: 130, sort: 'codi_intern',
      estil: { fontSize: 11, color: 'var(--text-soft)' }, titol: (m) => m.codi_intern,
      render: (m) => m.codi_intern,
    },
    {
      key: 'codi_client', label: t('models_list.col_ref_client'), min: 64, max: 80, sort: 'codi_client',
      estil: { fontSize: 11, color: 'var(--text-soft)' }, titol: (m) => m.codi_client || undefined,
      render: (m) => m.codi_client || '—',
    },
    {
      // LA DADA REINA (§8e): a Models és EL NOM, i porta el pes.
      key: 'nom_prenda', label: t('models_list.col_model'), min: 170, max: 260, sort: 'nom_prenda',
      estil: { fontWeight: 600 }, titol: (m) => m.nom_prenda || m.codi_intern,
      render: (m) => (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, maxWidth: '100%' }}>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.nom_prenda || '—'}</span>
          {/* MARQUES CONDICIONALS de la fila. La graella canònica no els dona columna —i una
              columna per a una marca que gairebé cap fila porta seria una columna buida—, però
              no es poden perdre: SET-1 diu de quin CONJUNT és peça la fila, F2.7 què ha
              lliurat i RETORN-2 la maduresa que publica l'altra casa. Van enganxades a la
              reina perquè és el que qualifiquen, i només apareixen si hi són. */}
          <SetBadge m={m} t={t} />
          <MaduresaBadge model={m} t={t} />
          <BadgeLliurable rondes={m.lliurable_ronda_n} compacte locale={dateLocale} />
        </span>
      ),
    },
    {
      key: 'collection', label: t('models_filters.collection'), min: 110, max: 150, sort: 'collection',
      estil: { fontSize: 11, color: 'var(--text-soft)' }, titol: (m) => m.collection || undefined,
      render: (m) => m.collection || '—',
    },
    {
      key: 'temporada', label: t('models_list.col_temp'), min: 70, max: 80, sort: 'temporada',
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      render: (m) => `${m.temporada || ''}${m.any ? ` ${m.any}` : ''}` || '—',
    },
    {
      key: 'data_entrada', label: t('models_list.col_entrada_model'), min: 78, max: 86, sort: 'data_entrada',
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      render: (m) => fmtDate(m.data_entrada || m.created_at, dateLocale),
    },
    {
      key: 'data_objectiu', label: t('models_list.col_deadline'), min: 78, max: 86, sort: 'data_objectiu',
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      render: (m) => fmtDate(m.data_objectiu, dateLocale),
    },
    {
      // §8e: FASE = NOMÉS TEXT (sense badge). El badge daurat d'abans era marca fent de dada.
      key: 'fase_actual', label: t('models_list.col_phase'), min: 110, max: 130, sort: 'fase_actual',
      estil: { fontSize: 11, color: 'var(--text-main)' },
      render: (m) => (m.fase_actual ? t(`model_sheet.dashboard.phase.${m.fase_actual}`, m.fase_actual) : '—'),
    },
    {
      // 🚩 PROVISIONAL-DOMINI · l'ESTAT de la §8e és el COMERCIAL (el del Kanban: Començat
      // neutre · En curs taronja · Acabat verd), i el Kanban no existeix. `Model.estat`
      // (Nou/EnCurs/EnRevisio/Tancat) és l'estat INTERN i NO és aquest: pintar-lo aquí seria
      // dir una cosa per una altra. La columna hi és, buida i amb el motiu escrit.
      key: 'estat', label: t('models_list.col_estat'), min: 86, max: 100,
      titolCap: t('models_list.estat_pendent'),
      estil: { color: 'var(--text-faint)' },
      render: () => '—',
    },
    {
      key: 'del', amplada: 36,
      render: (m) => (intentMode ? null : <BotoEsborrar onClick={(e) => remove(m, e)} title={t('models_list.delete')} />),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [t, dateLocale, intentMode, selectAllFilter, excludeIds, selected])

  const VISTES = [
    ['curs', t('models_list.view_active')],
    ['acabats', t('models_list.view_done')],
  ]

  return (
    <>
      {/* §8b · MENÚ DE PANTALLA — barra blanca de costat a costat amb filet a dalt i a baix.
          Ordre de la §8e: ← · filtres de VISTA · separador · accions. Les accions van a
          l'ESQUERRA (comportament de menú) i, en pujar-hi, PERDEN el blau: «el blau viu al
          contingut; el menú té el seu llenguatge». El marge negatiu les treu dels 24px del
          `<main>` perquè la barra vagi de costat a costat. */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu
          backTo="/"
          backTitle={t('models_list.back_title')}
          items={VISTES.map(([v, label]) => ({
            key: v, label, active: vista === v,
            onClick: () => setParams({ vista: v === 'curs' ? undefined : v, page: undefined }),
          }))}
        >
          <span style={sepMenu} />
          <NewModelMenu navigate={navigate} t={t} />
          {/* Mode intenció: les accions genèriques (assignar/gate/…) no apliquen → ocult. */}
          {!intentMode && (
            <ActionsMenu
              variant="menu"
              targets={selectAllFilter ? [] : selectedModels}
              selectionSet={selectAllFilter ? { filters: filterParams, excludeIds: [...excludeIds], count: filterCount } : null}
              onChanged={afterAction} onFeedback={setFeedback} />
          )}
          <BotoMenu onClick={() => setPanelOpen(o => !o)} icona="ti-filter" actiu={advancedCount > 0}
            aria-expanded={panelOpen}
            label={advancedCount ? t('models_filters.button_n', { n: advancedCount }) : t('models_filters.button')} />
        </PageMenu>
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%' }}>
        {/* §8e · EL COMPTADOR MANA I LA CERCA HI VA AL COSTAT, mateixa línia, amb els selects
            ràpids. El nom de l'entitat ja no és títol: és element en caption. */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 0 12px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 600, color: 'var(--text-main)', whiteSpace: 'nowrap' }}>
            {intentMode ? selected.size : count}
            <small style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, color: 'var(--text-soft)' }}>
              /{intentMode ? (intent.max ?? count) : (total ?? count)}</small>
          </span>
          <span style={retol}>{t('models_list.entity')}</span>
          <input value={searchInput} onChange={e => setSearchInput(e.target.value)}
            placeholder={t('models_list.search_ph')} aria-label={t('models_list.search_ph')}
            style={{ ...camp, flex: 1, minWidth: 220 }} />
          <select value={fase} onChange={e => setParams({ fase_actual: e.target.value, page: undefined })}
            aria-label={t('models_filters.f_phase')} style={camp}>
            <option value="">{t('models_list.all_phases')}</option>
            {(fases || []).map(p => <option key={p} value={p}>{faseCounts[p] != null ? `${p} (${faseCounts[p]})` : p}</option>)}
          </select>
          <select value={temporada} onChange={e => setParams({ temporada: e.target.value, page: undefined })}
            aria-label={t('models_filters.f_season')} style={camp}>
            <option value="">{t('models_list.all_seasons')}</option>
            {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {intentMode && (
          <div style={banda}>
            <i className="ti ti-arrow-back-up" aria-hidden="true" />
            {t('models_intent.banner')}
          </div>
        )}

        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

        {panelOpen && (
          <ModelsFilterPanel sp={sp} setParams={setParams} opts={opts} garmentCounts={garmentCounts}
            lockedKeys={intentMode ? ['customer'] : []} />
        )}

        <ActiveChips filterParams={filterParams} sp={sp} setParams={setParams} opts={opts} t={t} lang={i18n.language?.slice(0, 2) || 'ca'} FILTER_KEYS={FILTER_KEYS} lockedKeys={intentMode ? ['customer'] : []} />

        {/* Banda "seleccionar tot el filtre" (patró Gmail): OCULTA en mode intenció (és l'oposat
            conceptual de "limitat a N"). Apareix quan la pàgina és plena i el filtre té més resultats. */}
        {!intentMode && (allOnPage || selectAllFilter) && hasMoreThanPage && (
          <div style={{ ...banda, justifyContent: 'center' }}>
            {selectAllFilter ? (
              <>
                <span>{t('models_list.selected_all_filter', { n: filterCount })}</span>
                <button type="button" onClick={clearConjunt} style={btnSecundari}>
                  {t('models_list.clear_selection')}
                </button>
              </>
            ) : (
              <>
                <span>{t('models_list.selected_page', { n: selectedModels.length })}</span>
                <button type="button" onClick={() => setSelectAllFilter(true)} style={btnSecundari}>
                  {t('models_list.select_all_filter', { n: count })}
                </button>
              </>
            )}
          </div>
        )}

        {/* Llistat */}
        {vista === 'acabats' ? (
          <div style={buitCaixa}>
            <span style={buit}>{t('models_list.done_pending')}</span>
          </div>
        ) : loading ? (
          <div style={buitCaixa}><span style={buit}>{t('models_list.loading')}</span></div>
        ) : visibleItems.length === 0 ? (
          <div style={buitCaixa}>
            <span style={buit}>
              {Object.keys(filterParams).length ? t('models_list.empty_filtered') : t('models_list.empty')}
            </span>
          </div>
        ) : (
          <>
            <TaulaLlista
              cols={cols}
              files={visibleItems}
              clau={(m) => m.id}
              ordre={ordre}
              onOrdenar={ordenar}
              triada={(m) => rowChecked(m.id)}
              onObrir={intentMode ? (m) => rowToggle(m.id) : (m) => navigate(`/models/${m.id}`)}
            />
            {/* §8c — l'estat buit d'una COLUMNA també s'explica; el silenci d'una columna de
                guions és pitjor que la columna. */}
            <div style={{ ...buit, margin: '-8px 0 16px 2px' }}>{t('models_list.estat_pendent')}</div>
          </>
        )}

        {/* Select all (pàgina) — sota la taula, com la resta de gestos de conjunt. OCULT en mode
            intenció (selecció individual limitada, no conjunt). */}
        {!intentMode && visibleItems.length > 0 && (
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', color: 'var(--text-soft)', fontFamily: MONO, margin: '0 0 12px 2px', cursor: 'pointer' }}>
            <input type="checkbox" checked={selectAllFilter || allOnPage} onChange={toggleAll} />
            {t('models_list.select_page')}
          </label>
        )}

        {/* Paginació */}
        {pages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 4, marginBottom: 18, fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
            <button type="button" onClick={() => setParams({ page: Math.max(1, page - 1) })} disabled={page <= 1}
              style={{ ...btnSecundari, ...(page <= 1 ? deshabilitat : null) }}>← {t('models_list.prev')}</button>
            <span style={{ color: 'var(--text-soft)' }}>{t('models_list.page_info', { page, pages })}</span>
            <button type="button" onClick={() => setParams({ page: Math.min(pages, page + 1) })} disabled={page >= pages}
              style={{ ...btnSecundari, ...(page >= pages ? deshabilitat : null) }}>{t('models_list.next')} →</button>
          </div>
        )}

        {/* Barra de confirmació fixa del mode intenció. */}
        {intentMode && (
          <div style={{ position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 50,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14, flexWrap: 'wrap',
            padding: '12px 20px', background: 'var(--panel)',
            borderTopWidth: 1, borderTopStyle: 'solid', borderTopColor: 'var(--line)',
            boxShadow: '0 -4px 16px rgba(0,0,0,0.08)', fontFamily: MONO }}>
            <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
              {intent.max != null
                ? t('models_intent.counter', { x: selected.size, n: intent.max })
                : t('models_intent.counter_open', { x: selected.size })}
            </span>
            <button type="button" onClick={cancelIntent} style={btnTerciari}>{t('models_intent.cancel')}</button>
            {/* §5 · L'ACCIÓ PRIMÀRIA de la pantalla, i l'ÚNICA: en mode intenció la pantalla té
                una cosa que has vingut a fer. En mode normal la llista no en té cap blau (§8c). */}
            <button type="button" onClick={confirmIntent} disabled={!selected.size}
              style={{ ...btnPrimari, ...(!selected.size ? deshabilitat : null) }}>
              {t('models_intent.confirm')}
            </button>
          </div>
        )}
      </div>
    </>
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
      {/* Un filtre actiu NO és «inclòs en la definició» (verd) ni «on soc» (filet d'or): és una
          condició posada, i el seu llenguatge és el de la casa — --sel amb vora daurada. */}
      {chips.map(c => (
        <span key={c.id} style={xip}>
          {c.locked && <i className="ti ti-lock" style={{ fontSize: 14 }} aria-hidden="true" />}
          {c.text}
          {!c.locked && (
            <button type="button" onClick={c.remove} aria-label={t('models_list.clear')}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: 0, lineHeight: 1 }}>
              <i className="ti ti-x" style={{ fontSize: 14 }} aria-hidden="true" />
            </button>
          )}
        </span>
      ))}
      {hasClearable && (
        <button type="button" onClick={() => setParams(Object.fromEntries(
          [...FILTER_KEYS, 'page'].filter(k => !lockedKeys.includes(k)).map(k => [k, undefined])))}
          style={btnTerciari}>
          {t('models_filters.clear_all')}
        </button>
      )}
    </div>
  )
}

// SET-1 · A4 — «SET n/N» amb el codi comercial del conjunt al title. Codis via token, mai hex.
// §1: badge = fons suau + tinta del color + VORA FINA DEL MATEIX COLOR. Aquest és neutre (la
// pertinença a un conjunt no és cap semàfor): fons de pàgina, tinta suau i filet --line.
function SetBadge({ m, t }) {
  if (!m.garment_set) return null
  const gs = m.garment_set
  return (
    <span title={t('models_list.set_hint', { codi: gs.codi_base, nom: gs.nom_comercial || '' })}
      style={{ ...badgeNeutre, flex: 'none' }}>
      {t('models_list.set_badge', { n: m.piece_number ?? '?', total: gs.num_pieces })}
    </span>
  )
}

// La paperera de fila (§8e): icona destructiva 14px, hover --err-bg. En repòs NO és vermella
// plena (§5.5: la destructiva mai plena en repòs).
function BotoEsborrar({ onClick, title }) {
  const [hover, setHover] = useState(false)
  return (
    <button type="button" onClick={onClick} title={title} aria-label={title}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        width: 26, height: 26,
        borderWidth: 1, borderStyle: 'solid', borderColor: hover ? 'var(--err)' : 'transparent',
        borderRadius: 'var(--r-ctrl)', background: hover ? 'var(--err-bg)' : 'none',
        cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        // UN BOTÓ QUE NOMÉS PORTA UNA ICONA DECLARA LA MIDA I LA TINTA DE LA ICONA. Deixar-les
        // heretades és com es cola un 16px del document dins d'un control de 26px.
        color: 'var(--err)', fontSize: 14, padding: 0,
      }}>
      <i className="ti ti-trash" aria-hidden="true" style={{ fontSize: 'inherit', color: 'currentColor' }} />
    </button>
  )
}

// Un botó amb ESTIL DE MENÚ (§8e): dins de la barra blanca, una acció no és un botó — pren la
// forma de píndola de la barra. Mateix llenguatge que `PageMenu`, hover inclòs.
function BotoMenu({ onClick, icona, label, actiu = false, ...rest }) {
  const [hover, setHover] = useState(false)
  return (
    <button type="button" onClick={onClick} {...rest}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        borderWidth: 1, borderStyle: 'solid',
        borderColor: actiu ? 'var(--gold-border)' : 'transparent',
        borderRadius: 'var(--r-pill)',
        background: actiu || hover ? 'var(--sel)' : 'none',
        padding: '6px 14px', fontFamily: MONO, fontSize: 'var(--fs-body)', lineHeight: '16px',
        color: actiu || hover ? 'var(--text-main)' : 'var(--text-soft)',
        fontWeight: actiu ? 600 : 400, cursor: 'pointer',
        display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
      }}>
      {icona && <i className={`ti ${icona}`} aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />}
      {label}
    </button>
  )
}

// §1 · ACCIONS COMPOSTES: crear a mà i importar una col·lecció són variants de la MATEIXA acció
// («donar d'alta models») → UN sol desplegable, mai dos botons a la mateixa capçalera. Les dues
// destinacions són les altes que ja existeixen; aquest tram no en toca cap.
function NewModelMenu({ navigate, t }) {
  const [open, setOpen] = useState(false)
  return (
    <span style={{ position: 'relative' }}>
      <BotoMenu onClick={() => setOpen(o => !o)} icona="ti-plus" actiu={open}
        aria-haspopup="menu" aria-expanded={open}
        label={`${t('models_list.new_model')} ▾`} />
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 40 }} />
          <div role="menu" style={caixaMenu}>
            <button type="button" role="menuitem" onClick={() => { setOpen(false); navigate('/models/nou') }} style={itemMenu}>
              <i className="ti ti-edit" aria-hidden="true" style={{ fontSize: 14 }} /> {t('models_list.manual')}
            </button>
            <button type="button" role="menuitem" onClick={() => { setOpen(false); navigate('/models/importar-colleccio') }} style={itemMenu}>
              <i className="ti ti-file-spreadsheet" aria-hidden="true" style={{ fontSize: 14 }} /> {t('nav.import_collection')}
            </button>
          </div>
        </>
      )}
    </span>
  )
}

// ── Estils de la casa (tokens de la NORMA, cap hex) ───────────────────────────────────────
const sepMenu = { width: 1, height: 20, background: 'var(--line)', margin: '0 6px', flex: 'none' }
const retol = {
  fontSize: 'var(--fs-label)', letterSpacing: '.08em', textTransform: 'uppercase',
  color: 'var(--text-soft)', fontWeight: 600, whiteSpace: 'nowrap',
}
const camp = {
  fontFamily: MONO, fontSize: 'var(--fs-body)',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
  borderRadius: 'var(--r-ctrl)', padding: '8px 12px',
  background: 'var(--panel)', color: 'var(--text-main)',
}
const buit = { fontSize: 'var(--fs-label)', fontStyle: 'italic', color: 'var(--text-faint)', fontFamily: MONO }
const buitCaixa = {
  background: 'var(--panel)', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
  borderRadius: 'var(--r-card)', padding: '40px 16px', textAlign: 'center', marginBottom: 16,
}
const banda = {
  display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
  padding: '8px 14px', margin: '0 0 12px',
  background: 'var(--sel)', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--gold-border)',
  borderRadius: 'var(--r-ctrl)', fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
}
const btnSecundari = {
  fontFamily: MONO, fontSize: 'var(--fs-body)',
  background: 'var(--panel)', color: 'var(--text-main)',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--gold-border)',
  borderRadius: 'var(--r-ctrl)', padding: '8px 16px', cursor: 'pointer',
}
const btnPrimari = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600,
  background: 'var(--accio)', color: 'var(--white)',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--accio)',
  borderRadius: 'var(--r-ctrl)', padding: '8px 16px', cursor: 'pointer',
}
const btnTerciari = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', background: 'none', color: 'var(--text-soft)',
  border: 'none', borderRadius: 'var(--r-ctrl)', padding: '8px 12px', cursor: 'pointer',
}
// §5.7 · deshabilitat: BAIXA EL FONS, no la tinta.
const deshabilitat = { background: 'var(--bg-page)', borderColor: 'var(--line)', cursor: 'not-allowed' }
const badgeNeutre = {
  fontSize: 'var(--fs-caption)', lineHeight: '12px', fontWeight: 600, letterSpacing: '.04em',
  padding: '3px 10px', borderRadius: 'var(--r-pill)', whiteSpace: 'nowrap',
  background: 'var(--bg-page)', color: 'var(--text-soft)',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
}
const xip = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '3px 10px',
  borderRadius: 'var(--r-pill)', background: 'var(--sel)', color: 'var(--text-main)',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--gold-border)',
  fontFamily: MONO, fontSize: 'var(--fs-caption)', fontWeight: 600,
}
const caixaMenu = {
  position: 'absolute', left: 0, top: 'calc(100% + 6px)', zIndex: 41, background: 'var(--panel)',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)', borderRadius: 'var(--r-ctrl)',
  boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4, minWidth: 220,
}
const itemMenu = {
  display: 'flex', alignItems: 'center', gap: 8, width: '100%', textAlign: 'left',
  background: 'none', border: 'none', padding: '8px 10px', borderRadius: 'var(--r-ctrl)',
  fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)', cursor: 'pointer',
}
