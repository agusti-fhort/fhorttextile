
import { useState, useEffect, useCallback, useMemo, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import useAuthStore from "../store/auth"
import { modelTasks, models as modelsApi, customers, calendar } from "../api/endpoints"
import ProjectGantt from "../components/planning/ProjectGantt"
import PageMenu from "../components/ui/PageMenu"
import { apagat, botoSec, botoTer } from "../components/ui/buttons"
import useToc, { anellFocus } from "../components/ui/toc"
import { useEnumeracio } from "../utils/vocabulariDominiFont"

const API = import.meta.env.VITE_API_URL || ""
const MONO = "IBM Plex Mono, monospace"

// Tabs de la home del tècnic. Tab 1 = vista d'acció (abast + KPIs + board); tab 2 = el meu Gantt.
const DASH_TABS = ['home', 'planning']
const DASH_TAB_LABELS = { home: 'dashboard.tab_home', planning: 'dashboard.tab_planning' }

// "Properament": horitzó del feed futur (dies). Derivat en viu de calendar/events, sense persistència.
const UPCOMING_DAYS = 60
// Data local YYYY-MM-DD (no UTC) per acotar el rang i comparar el futur.
const localISO = (d) => {
  const z = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`
}

// Sprint 5 — board per-model 4-col al Dashboard. Cada card = un MODEL, classificat per
// kanban_state (derivat al backend, by-model 1c) ∈ {pending, open, paused, done}.
// Columnes: [Pendents | En curs (Open) | Pausats | Fets]. Mateixa paleta que el Kanban jubilat
// (pending=gris, open=or, paused=àmbar, done=verd), però via tokens del design system.
// ⚠️ EL CODI DE COLORS DE LES QUATRE COLUMNES SE'N VA, i cal dir per què (report-only, §8).
// Hi havia `--gray` (àlies legacy), `--gold`, `--warn` (token vell) i `--ok` tenyint la icona
// de cada capçalera. Dos problemes: la §8 només admet QUATRE tintes d'icona (repòs --text-soft ·
// activa --gold · deshabilitada --text-faint · destructiva --err) i el daurat és MARCA, no una
// dada; i la §8c ho remata («el daurat NO pinta números»). Podria haver-hi semàfor —la §1 diu
// que «la dada porta el color»—, però la §8e només en nomena TRES estats (Començat neutre · En
// curs taronja · Acabat verd) i aquest board en té QUATRE: assignar el color del quart
// (`paused`) seria inventar domini dins d'un tram de pell. Les columnes es distingeixen pel seu
// NOM i la seva posició, que és el que de debò les distingia. Si l'Agus vol el codi de colors,
// la decisió que falta és una: quin color és «pausat».
const BOARD_COLS = [
  { key: "pending", icon: "ti-inbox" },
  { key: "open",    icon: "ti-player-play" },
  { key: "paused",  icon: "ti-player-pause" },
  { key: "done",    icon: "ti-circle-check" },
]

// §8c · KPI. «KPI/recomptes NEUTRES (--text-main). NOMÉS els KPI d'alerta porten semàfor
// (p.ex. "En risc · 1" en --err). El daurat NO pinta números.» Per això el color per defecte
// deixa de ser `--gold` i passa a `--text-main`: dels tres KPI d'aquesta pantalla, l'únic que
// és una alerta és «En risc». La vora passa de `--border` (DEPRECAT, §1b(b)) a `--line` i el
// radi de 8 a `--r-card`, que és el de la targeta de la casa.
function KPICard({ label, value, sub, color = "var(--text-main)", onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--panel)", border: "1px solid var(--line)", borderRadius: "var(--r-card)",
        // La targeta declara la MIDA DE COS. Sense això hereta els 16px del document i, encara
        // que els fills posin la seva i a ull no es noti, el contenidor computa un valor que
        // ningú ha decidit — és el defecte que la mesura del bloc A va treure a la llum a les
        // files de /poms i /size-library. La maqueta del §8b ho declara: `.card{font-size:12px}`.
        fontSize: "var(--fs-body)",
        padding: 16, cursor: onClick ? "pointer" : "default",
        transition: "all .1s", flex: 1, minWidth: 140,
      }}
      onMouseEnter={e => onClick && (e.currentTarget.style.borderColor = "var(--gold-border)")}
      onMouseLeave={e => onClick && (e.currentTarget.style.borderColor = "var(--line)")}
    >
      <div style={{ fontSize: 'var(--fs-body)', color: "var(--text-soft)", fontFamily: MONO, marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 'var(--fs-display)', fontWeight: 600, color, fontFamily: MONO, lineHeight: 1 }}>{value ?? "—"}</div>
      {sub && <div style={{ fontSize: 'var(--fs-caption)', color: "var(--text-soft)", fontFamily: MONO, marginTop: 6 }}>{sub}</div>}
    </div>
  )
}

// §8c · EL CONTROL DE FILTRE DE LA CASA: «vora --line, radi 6, alçada única, MAI blaus —
// filtrar no és l'acció de la pantalla». Aquesta còpia local anava amb `--gray-l` (un àlies de
// FARCIMENT fent de vora) i vora de mig píxel, que no és de cap escala.
const camp = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 10px', height: 32,
  border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)',
  background: 'var(--panel)', color: 'var(--text-main)',
}

// Segueix la paginació de DRF per no truncar (mateix patró que Planning/Kanban).
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

// Card de MODEL (zoom-in: clic → /models/:id). Reusa la forma de la ModelRow del Kanban,
// adaptada a navegació directa i tokens del design system.
// LA DADA REINA ÉS EL NOM, no el codi (§8e, i és el que A5 va fixar a /models: «a Models: EL
// NOM, 600/tinta principal; les refs en secundari»). Aquí el codi anava a 600 EN DAURAT i el
// nom en tinta normal: marca pintant una dada, i la jerarquia al revés de la llista germana.
// La FASE passa a text pla (§8e: «FASE = NOMÉS TEXT», sense badge) — el xip gris amb radi 6
// que hi havia no és cap de les formes de la casa.
function ModelCard({ model, onClick, t, highlight = false, innerRef = null }) {
  const c = model.counts || {}
  const total = (c.pending || 0) + (c.paused || 0) + (c.in_progress || 0) + (c.done || 0)
  const faseLabel = model.fase ? t(`model_sheet.dashboard.phase.${model.fase}`, model.fase) : null
  // El toc de la casa (`ui/toc`): hover i focus amb estat, i l'anell NOMÉS amb focus de teclat
  // — si no, la targeta es queda amb l'anell enganxat després del clic i apareix el quart estat
  // fantasma que el bloc A va haver de caçar a les pastilles de capa.
  const [toc, gestos] = useToc()
  return (
    // C4b — ressaltat de la feina ACTIVA (in_progress). Era un anell daurat de 1.5px per fora;
    // ara és la forma de «on soc» de la casa (§1 · §4): fons `--sel` + FILET D'OR de 3px a
    // l'esquerra. El filet va sempre declarat (transparent quan no toca) perquè la targeta no
    // canviï d'amplada en encendre's — una targeta que salta 3px quan algú comença una tasca
    // és el mateix defecte que la §7 evita amb el `box-shadow` del subratllat del veredicte.
    <button ref={innerRef} onClick={onClick} {...gestos} style={{
      textAlign: 'left', width: '100%',
      borderWidth: '1px 1px 1px 3px', borderStyle: 'solid',
      borderColor: `var(--line) var(--line) var(--line) ${highlight ? 'var(--gold)' : 'transparent'}`,
      background: highlight || toc.hover ? 'var(--sel)' : 'var(--panel)', borderRadius: 'var(--r-card)',
      padding: '8px 12px', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 4,
      outline: 'none', ...(toc.focus ? anellFocus : null),
    }}
    >
      {model.model_nom && (
        <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)', lineHeight: 1.3 }}>
          {model.model_nom}
        </div>
      )}
      <div style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', display: 'flex', alignItems: 'center', gap: 4 }}>
        {model.reanchored_by_start && <i className="ti ti-plus" title={t('planning.gantt.reanchored')} aria-hidden="true" style={{ fontSize: 'var(--fs-label)', color: 'currentColor' }} />}
        {model.model_codi || `#${model.model_id}`}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        {faseLabel && (
          <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontFamily: MONO }}>{faseLabel}</span>
        )}
        <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontFamily: MONO }}>{t('dashboard.board.tasks_n', { n: total })}</span>
      </div>
    </button>
  )
}

// Mini-chip de comptador per fase.
function ModelBoard({ scope }) {
  const navigate = useNavigate()
  const { t } = useTranslation()

  // Filtres de campanya (tot va al backend; consumeix by-model + fase-counts, Sprint 5 1a/1b).
  const [search, setSearch] = useState("")
  const [fTemporada, setFTemporada] = useState("")
  const [fFase, setFFase] = useState("")
  // Les fases són DADA (`Model.FASE_CHOICES`), no una llista d'aquesta pantalla. Sense
  // vocabulari el filtre no ofereix fases: no en sabem cap, i inventar-ne seria tornar-hi.
  const { codis: fasesModel } = useEnumeracio('fases_model')
  const { codis: temporades } = useEnumeracio('temporades')
  const [fCustomer, setFCustomer] = useState("")
  const [fCollection, setFCollection] = useState("")
  const [fAfter, setFAfter] = useState("")
  const [fBefore, setFBefore] = useState("")

  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [loading, setLoading] = useState(true)
  const [, setFaseCounts] = useState({ counts: {}, total: 0 })
  const [customerOpts, setCustomerOpts] = useState([])

  // Paràmetres de campanya compartits per by-model i fase-counts (mateix contracte de filtres).
  // L'abast (scope) "els meus" hi afegeix assignee=me (C1: `assignee` és el param que filtra per
  // tècnic amb tasca assignada; `responsable` ja és el director), de manera que board, chips i
  // comptadors es filtren com els KPIs en commutar l'abast.
  const buildParams = useCallback(() => {
    const p = {}
    if (scope === 'me') p.assignee = 'me'
    const s = search.trim(); if (s) p.search = s
    if (fTemporada) p.temporada = fTemporada
    if (fFase) p.fase_actual = fFase
    if (fCustomer) p.customer = fCustomer
    const col = fCollection.trim(); if (col) p.collection = col
    if (fAfter) p.data_objectiu_after = fAfter
    if (fBefore) p.data_objectiu_before = fBefore
    return p
  }, [scope, search, fTemporada, fFase, fCustomer, fCollection, fAfter, fBefore])

  // Carrega una pàgina de by-model. all=true perquè la columna "Fets" (models tot-Done,
  // ocultats per defecte) també tingui contingut. replace reinicia (canvi de filtre).
  const loadPage = useCallback((pageToLoad, replace) => {
    setLoading(true)
    modelTasks.byModel({ ...buildParams(), all: "true", page: pageToLoad })
      .then(res => {
        const data = res.data
        const results = data?.results ?? (Array.isArray(data) ? data : [])
        setRows(prev => (replace ? results : [...prev, ...results]))
        setHasNext(!!data?.next)
        setCount(typeof data?.count === "number" ? data.count : results.length)
      })
      .catch(() => { if (replace) { setRows([]); setHasNext(false); setCount(0) } })
      .finally(() => setLoading(false))
  }, [buildParams])

  // Qualsevol canvi de filtre (debounce) → pàgina 1 + recompte de fases coherent.
  useEffect(() => {
    const id = setTimeout(() => {
      setPage(1)
      loadPage(1, true)
      modelsApi.faseCounts(buildParams())
        .then(res => setFaseCounts(res.data || { counts: {}, total: 0 }))
        .catch(() => setFaseCounts({ counts: {}, total: 0 }))
    }, 300)
    return () => clearTimeout(id)
  }, [loadPage, buildParams])

  // Opcions de client per al filtre (un sol cop). NO s'envia `exclude_self` A PROPÒSIT: el client
  // propi ha de ser filtrable (en una Marca hi pengen els seus propis models, i sense ell no es
  // podrien aïllar). Només la pàgina Clients filtra, i només si el tenant és un Estudi.
  useEffect(() => {
    customers.list({ page_size: 200 })
      .then(res => setCustomerOpts(res.data?.results ?? res.data ?? []))
      .catch(() => setCustomerOpts([]))
  }, [])

  const loadMore = () => {
    if (loading || !hasNext) return
    const next = page + 1
    setPage(next)
    loadPage(next, false)
  }

  const clearFilters = () => {
    setSearch(""); setFTemporada(""); setFFase("")
    setFCustomer(""); setFCollection(""); setFAfter(""); setFBefore("")
  }

  // Classificació dels models carregats per kanban_state (derivat al backend).
  const byState = useMemo(() => {
    const groups = { pending: [], open: [], paused: [], done: [] }
    rows.forEach(m => { (groups[m.kanban_state] || groups.pending).push(m) })
    return groups
  }, [rows])

  // C4b — auto-focus del model ACTIU en entrar: primer amb tasca InProgress (fallback Paused).
  // NO reordena (l'ordre és el del pla); només fa scrollIntoView la seva targeta quan CANVIA
  // (entrar, o iniciar-ne un altre via 'plan:changed'). Ressaltat visual a la pròpia targeta.
  const firstActiveId = useMemo(() => {
    const a = rows.find(m => (m.counts?.in_progress || 0) > 0)
          || rows.find(m => (m.counts?.paused || 0) > 0)
    return a?.model_id ?? null
  }, [rows])
  const activeCardRef = useRef(null)
  const lastAnchored = useRef(null)
  useEffect(() => {
    if (firstActiveId && firstActiveId !== lastAnchored.current && activeCardRef.current) {
      lastAnchored.current = firstActiveId
      activeCardRef.current.scrollIntoView({ block: 'nearest' })
    }
  }, [firstActiveId, rows])

  // C4 — LECTOR del pla: invalidació en canvis (reorder / inici real). Recarrega la pàgina 1.
  useEffect(() => {
    const h = () => { setPage(1); loadPage(1, true) }
    window.addEventListener('plan:changed', h)
    return () => window.removeEventListener('plan:changed', h)
  }, [loadPage])

  return (
    <div>
      {/* Capçalera. El rètol de secció anava en DAURAT: la §8b reserva el daurat a marca,
          selecció i base, i un rètol de bloc no és cap de les tres (§8c: el daurat no pinta ni
          números ni etiquetes). Passa a `--text-soft`, que és el rètol de bloc de la casa. */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
        <div style={{
          fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".08em",
          textTransform: "uppercase", color: "var(--text-soft)", fontFamily: MONO,
        }}>
          {t("dashboard.board.title")}
        </div>
        <span style={{ fontSize: 'var(--fs-body)', color: "var(--text-soft)", fontFamily: MONO }}>
          {t("dashboard.board.results_n", { n: count })}
        </span>
      </div>

      {/* COMMIT 3 — fila de pastilles de comptes de fase amagada (Total · per-fase). Es conserva
          el substrat faseCounts (higiene diferida: sense ús visible després d'amagar-les). */}

      {/* Filtres de campanya */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 16 }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder={t("dashboard.board.search_ph")} aria-label={t("dashboard.board.search_ph")}
          style={{ ...camp, flex: "0 1 240px", minWidth: 160 }}
        />
        <select value={fCustomer} onChange={e => setFCustomer(e.target.value)}
          aria-label={t("dashboard.board.filter_customer")} style={camp}>
          <option value="">{t("dashboard.board.filter_customer")}</option>
          {customerOpts.map(c => (
            <option key={c.id} value={c.id}>{c.nom || c.codi || `#${c.id}`}</option>
          ))}
        </select>
        <input
          value={fCollection} onChange={e => setFCollection(e.target.value)}
          placeholder={t("dashboard.board.filter_collection")} aria-label={t("dashboard.board.filter_collection")}
          style={{ ...camp, width: 150 }}
        />
        {/* LES TEMPORADES SORTIEN D'UNA CONSTANT DEL CLIENT (`["SS","FW","CO","SP"]`) i ara
            surten de `/vocabulari/` → `temporades` (`Model.TEMPORADA_CHOICES`), com les fases.
            Llei 1: cap enumeració de domini al frontend. Sense vocabulari, el filtre no ofereix
            cap temporada — no en sabem cap, i inventar-ne seria tornar-hi (mateixa conducta
            que ja tenia el filtre de fases). 🚩 La germana `SEASONS` de `pages/Models.jsx:14`
            és pantalla CONFORMADA i intocable en aquest lot: reportada, no corregida. */}
        <select value={fTemporada} onChange={e => setFTemporada(e.target.value)}
          aria-label={t("dashboard.board.filter_temporada")} style={camp}>
          <option value="">{t("dashboard.board.filter_temporada")}</option>
          {(temporades || []).map(x => <option key={x} value={x}>{t(`kanban.temporades.${x}`)}</option>)}
        </select>
        <select value={fFase} onChange={e => setFFase(e.target.value)}
          aria-label={t("dashboard.board.filter_fase")} style={camp}>
          <option value="">{t("dashboard.board.filter_fase")}</option>
          {(fasesModel || []).map(x => <option key={x} value={x}>{t(`model_sheet.dashboard.phase.${x}`)}</option>)}
        </select>
        <label style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 'var(--fs-label)', color: "var(--text-soft)", fontFamily: MONO }}>
          {t("dashboard.board.filter_date_from")}
          <input type="date" value={fAfter} onChange={e => setFAfter(e.target.value)} style={camp} />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 'var(--fs-label)', color: "var(--text-soft)", fontFamily: MONO }}>
          {t("dashboard.board.filter_date_to")}
          <input type="date" value={fBefore} onChange={e => setFBefore(e.target.value)} style={camp} />
        </label>
        {/* §8c · «Neteja» = TERCIÀRIA. Anava amb l'estil d'un input, com el cancel·lar del
            modal de la casa: un camp de text fent de botó al costat de sis camps de debò. */}
        <button onClick={clearFilters} style={botoTer}>
          <i className="ti ti-x" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} /> {t("dashboard.board.clear")}
        </button>
      </div>

      {/* Board 4-col */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: "1rem", alignItems: "start" }}>
        {BOARD_COLS.map(col => {
          const items = byState[col.key] || []
          return (
            <div key={col.key} style={{
              background: "var(--panel)", border: "1px solid var(--line)", borderRadius: "var(--r-card)",
              fontSize: "var(--fs-body)",   // v. la nota de `KPICard`: la targeta declara el cos
              overflow: "hidden", display: "flex", flexDirection: "column", minHeight: 320, minWidth: 0,
            }}>
              {/* La capçalera anava sobre `--gray-l` (#f0f0f0, gris fred i àlies de farciment)
                  amb filets de mig píxel. Ara és panell blanc amb el filet de la casa, i el
                  recompte és un rètol neutre: la §8c vol els recomptes en tinta principal, i
                  la píndola grisa que hi havia semblava un badge d'estat sense ser-ho. */}
              <div style={{
                padding: "12px 16px", borderBottom: "1px solid var(--line)",
                display: "flex", alignItems: "center", gap: 8, background: "var(--panel)",
              }}>
                <i className={`ti ${col.icon}`} aria-hidden="true" style={{ fontSize: 16, color: "var(--text-soft)" }} />
                <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: "var(--text-main)" }}>{t(`dashboard.board.state.${col.key}`)}</span>
                <span style={{
                  marginLeft: "auto", fontSize: 'var(--fs-body)', fontWeight: 600, color: "var(--text-main)",
                  fontFamily: MONO,
                }}>{items.length}</span>
              </div>
              <div style={{ flex: 1, padding: 8, display: "flex", flexDirection: "column", gap: 8 }}>
                {loading && rows.length === 0 ? (
                  <div style={ph}>{t("common.loading")}</div>
                ) : items.length === 0 ? (
                  <div style={ph}>{t("dashboard.board.empty_col")}</div>
                ) : items.map(m => (
                  <ModelCard key={m.model_id} model={m} t={t}
                             highlight={(m.counts?.in_progress || 0) > 0}
                             innerRef={m.model_id === firstActiveId ? activeCardRef : null}
                             onClick={() => navigate(`/models/${m.model_id}`)} />
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {hasNext && (
        <div style={{ display: "flex", justifyContent: "center", marginTop: 16 }}>
          {/* §5.2 · SECUNDÀRIA (blanc + vora daurada). «Carregar-ne més» no és el que has
              vingut a fer aquí, o sigui que no és blava; i el deshabilitat baixa el FONS i no
              la tinta (§5.7) — l'`opacity: 0.6` que hi havia apagava també el text. */}
          <button onClick={loadMore} disabled={loading}
            style={{ ...botoSec, ...(loading ? apagat : null) }}>
            <i className={`ti ${loading ? "ti-loader-2" : "ti-chevron-down"}`} aria-hidden="true"
              style={{ fontSize: 14, color: 'currentColor' }} />
            {t("dashboard.board.load_more")}
          </button>
        </div>
      )}
    </div>
  )
}

// §8c · ESTAT BUIT = frase en `--text-faint` CURSIVA, mai caixa buida muda. Anava en `--gray`
// (àlies legacy, 3.64:1) amb pes 300, que no és cap pes de la casa.
const ph = { fontSize: 'var(--fs-body)', color: 'var(--text-faint)', fontStyle: 'italic', textAlign: 'center', padding: 16 }

// Selector d'abast del dashboard del tècnic: [Els meus · Tots]. Default per ROL (es deriva del
// rol/capabilities a Dashboard, NO de localStorage). Sempre visible i commutable.

export default function Dashboard() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const token = useAuthStore.getState().token || localStorage.getItem('access_token')

  // Auth guard: redirect if there is no token (no fetch will run without auth)
  useEffect(() => { if (!token) navigate("/login") }, [token, navigate])
  const [me, setMe] = useState(null)
  const [onboarding, setOnboarding] = useState(null)
  const [activeTab, setActiveTab] = useState('home')

  // Abast [me|all]. null fins que arriba `me` → default per rol (view_team_tasks → tots; si no, meus).
  // La home va SEMPRE acotada als models on l'usuari és ASSIGNEE de tasca (assignee=me →
  // ModelTask.assignee, C1). Mateix eix que el Gantt mine=. Sense selector d'abast.
  const scope = 'me'
  const [scopeRows, setScopeRows] = useState([])     // by-model de l'abast (substrat dels KPIs)
  const [scopeLoading, setScopeLoading] = useState(true)
  // Models amb ≥1 tasca en risc (planned_end > data_objectiu), de calendar/events. Es creua amb
  // l'abast (scopeRows) per al KPI 'En risc'; es carrega un sol cop (la visibilitat ja l'acota el backend).
  const [riskyModelIds, setRiskyModelIds] = useState(() => new Set())

  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` }
    Promise.allSettled([
      fetch(`${API}/api/v1/me/`, { headers }).then(r => r.json()),
      fetch(`${API}/api/v1/onboarding/status/`, { headers }).then(r => r.ok ? r.json() : null),
    ]).then(([meRes, onbRes]) => {
      if (meRes.status === "fulfilled") setMe(meRes.value)
      if (onbRes.status === "fulfilled" && onbRes.value) setOnboarding(onbRes.value)
    })
  }, [token])

  // Models en risc: calendar/events (tasca amb en_risc = planned_end > data_objectiu). Un sol cop;
  // l'abast l'aplica el creuament amb scopeRows al càlcul dels KPIs.
  useEffect(() => {
    calendar.events({})
      .then(res => {
        const ids = new Set()
        ;(res.data?.events ?? []).forEach(ev => {
          if (ev.tipus === "tasca" && ev.en_risc && ev.meta?.model_id != null) ids.add(ev.meta.model_id)
        })
        setRiskyModelIds(ids)
      })
      .catch(() => setRiskyModelIds(new Set()))
  }, [])

  // KPIs derivats de l'abast (es recalculen en commutar): senyals d'acció, no recompte de fases.
  const kpi = useMemo(() => ({
    total: scopeRows.length,
    open: scopeRows.filter(m => m.kanban_state === "open").length,
    risc: scopeRows.filter(m => riskyModelIds.has(m.model_id)).length,
  }), [scopeRows, riskyModelIds])

  // "Properament": el set dels MEUS models de l'abast (segueix el selector) + nom per id (mai codi).
  const myModelIds = useMemo(() => new Set(scopeRows.map(m => m.model_id)), [scopeRows])
  const nomById = useMemo(
    () => Object.fromEntries(scopeRows.map(m => [m.model_id, m.model_nom])), [scopeRows])

  // Feed futur derivat EN VIU de calendar/events (mateixa derivació que ModelMilestones, sense
  // persistència). Es filtra a posteriori (futur + intersecció amb els meus models) → reprogramat
  // segueix vigent perquè cada càrrega es deriva fresca.
  const [futureEvents, setFutureEvents] = useState([])
  useEffect(() => {
    const today = new Date()
    const end = new Date(); end.setDate(end.getDate() + UPCOMING_DAYS)
    calendar.events({ start: localISO(today), end: localISO(end) })
      .then(res => setFutureEvents(res.data?.events ?? []))
      .catch(() => setFutureEvents([]))
  }, [])

  const upcoming = useMemo(() => {
    const todayISO = localISO(new Date())
    return (futureEvents || [])
      // 2 tipus ara (extensible): fitting (sessió) i confecció (arribada de proto).
      .filter(ev => (ev.tipus === "fitting" || ev.tipus === "confeccio") && ev.start)
      .filter(ev => ev.start.slice(0, 10) >= todayISO)          // només futur
      .filter(ev => myModelIds.has(ev.meta?.model_id))          // intersecció amb els MEUS models
      .map(ev => ({ id: ev.id, tipus: ev.tipus, day: ev.start.slice(0, 10), model_id: ev.meta?.model_id }))
      .sort((a, b) => a.day.localeCompare(b.day))               // ascendent per data
  }, [futureEvents, myModelIds])

  // Substrat dels KPIs: by-model de TOT l'abast (scope-only, sense filtres de campanya). Es
  // recarrega en commutar l'abast. all=true per comptar també els models tot-Done. El load es
  // difereix (setTimeout) per no cridar setState síncron dins l'efecte (mateix patró que el board).
  useEffect(() => {
    if (scope === null) return
    let alive = true
    const id = setTimeout(() => {
      setScopeLoading(true)
      const params = { all: "true", ...(scope === "me" ? { assignee: "me" } : {}) }
      fetchAllPages(modelTasks.byModel, params)
        .then(rows => { if (alive) setScopeRows(rows) })
        .catch(() => { if (alive) setScopeRows([]) })
        .finally(() => { if (alive) setScopeLoading(false) })
    }, 0)
    return () => { alive = false; clearTimeout(id) }
  }, [scope])

  const hora = new Date().getHours()
  const salutacio = hora < 13 ? t("dashboard.greeting_morning") : hora < 20 ? t("dashboard.greeting_afternoon") : t("dashboard.greeting_evening")

  return (
    // §3 · el padding arrel de pàgina és 0: els 24px els dona el `<main>` del Shell, i aquí
    // n'hi havia 24 més a sobre (48 en total). El `maxWidth` del CONTINGUT es conserva, però
    // baixa un nivell: la barra del §8b ha d'anar de costat a costat, i abans quedava atrapada
    // dins de la columna centrada.
    <>
      {/* §8b · MENÚ DE PANTALLA. El que hi havia era una banda de pestanyes amb l'activa en
          DAURAT amb subratllat daurat, al mateix nivell de la pàgina: exactament el patró que
          A6 va treure del dashboard del model («ni blau ni daurat ple: navegar no és ni acció
          ni marca»). Les dues seccions de la home —Desenvolupament i Planificació— són seccions
          grans d'una entitat, o sigui píndoles del §8b-bis, no tabs de secció.
          🛑 LA FLETXA: aquesta pantalla és L'ARREL del producte i no penja d'enlloc → `backTo`
          és `null` i la fletxa surt DESHABILITADA. El motiu, a `ui/PageMenu.jsx`. Pendent
          d'Agus. El marge negatiu la treu dels 24px del `<main>`, com a la resta del producte. */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu
          backTo={null}
          backTitle={t('dashboard.back_arrel')}
          items={DASH_TABS.map(tab => ({
            key: tab, label: t(DASH_TAB_LABELS[tab]),
            active: activeTab === tab, onClick: () => setActiveTab(tab),
          }))}
        />
      </div>

      <div style={{ maxWidth: 1280, margin: "0 auto", paddingTop: 16 }}>
      {/* §8b.3 · IDENTITAT SOBRE EL FONS DE PÀGINA, sense contenidor. Aquí la identitat és de
          qui mira, no d'una entitat: la salutació fa d'`h1` (22/500) i la data de caption. */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500, color: "var(--text-main)", margin: "0 0 4px" }}>
          {salutacio}{me ? `, ${me.full_name?.split(" ")[0] || me.username}` : ""}.
        </h1>
        <div style={{ fontSize: 'var(--fs-caption)', color: "var(--text-soft)", fontFamily: MONO }}>
          {new Date().toLocaleDateString(i18n.language || "ca", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
        </div>
      </div>

      {/* PORTA a la configuració inicial (§5.3), no una franja de marca. Anava sobre
          `--gold-pale`, que la §1 ELIMINA del sistema («cap superfície ni estat»), amb el
          percentatge en daurat dins d'un cercle i un fals botó de fons daurat ple. Ara: targeta
          de la casa, el percentatge com a KPI NEUTRE (§8c: «el daurat NO pinta números») i una
          PORTA en secundari amb chevron — anar a un altre lloc no compromet res i per això no
          pot cridar més que el que sí que compromet. */}
      {onboarding && typeof onboarding.percentatge === 'number' && onboarding.percentatge < 100 && (
        <div style={{
          marginBottom: 24, padding: 16,
          borderRadius: 'var(--r-card)', background: 'var(--panel)',
          border: '1px solid var(--line)',
          display: 'flex', alignItems: 'center', gap: 16,
        }}>
          <div style={{
            fontSize: 'var(--fs-h2)', lineHeight: '24px', fontWeight: 600,
            color: 'var(--text-main)', fontFamily: MONO, whiteSpace: 'nowrap',
          }}>
            {onboarding.percentatge}%
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>
              {t('dashboard.onboarding_incomplete')}
            </div>
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', marginTop: 2 }}>
              {onboarding.passos_pendents
                ? t('dashboard.onboarding_steps_left', { count: onboarding.passos_pendents })
                : t('dashboard.onboarding_complete_setup')}
            </div>
          </div>
          <button type="button" onClick={() => navigate('/onboarding')} style={botoSec}>
            {t('dashboard.complete_setup')}
            <i className="ti ti-chevron-right" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
          </button>
        </div>
      )}

      {activeTab === 'planning' ? (
        // Tab 2 — el meu Gantt: sempre "meu" (mine), sense selector d'abast propi.
        <ProjectGantt t={t} mine />
      ) : (
      <>
      {/* Selector d'abast (DALT): Els meus · Tots. */}

      {scope === "me" && !scopeLoading && scopeRows.length === 0 ? (
        // §8c · ESTAT BUIT = frase en `--text-faint` cursiva, «mai caixa buida muda». Era una
        // caixa amb vora DISCONTÍNUA i una icona de 26px al mig — i el filet discontinu és el
        // llenguatge d'avís, no el de «aquí encara no hi ha res».
        <div style={{ padding: 16, color: "var(--text-faint)", fontStyle: "italic",
          fontSize: 'var(--fs-body)', fontFamily: MONO }}>
          {t("dashboard.scope.empty_mine")}
        </div>
      ) : (
        <>
          {/* Banda superior: ABAST (esq) · PROPERAMENT (dre) — dues meitats iguals, top-aligned,
              cadascuna sota el seu label MONO de secció. */}
          <div style={{ marginBottom: 28 }}>
            <div style={{ display: "flex", gap: 16, marginBottom: 8 }}>
              <div style={{ flex: 1, fontSize: "var(--fs-label)", fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--text-soft)", fontFamily: MONO }}>
                {t("dashboard.scope.label")}
              </div>
              <div style={{ flex: 1, fontSize: "var(--fs-label)", fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--text-soft)", fontFamily: MONO }}>
                {t("dashboard.upcoming.title")}
              </div>
            </div>
            <div style={{ display: "flex", gap: 16, alignItems: "stretch" }}>
              {/* ABAST — els 3 KPIs en HORITZONTAL; alçada = la d'un contenidor KPI. */}
              <div style={{ flex: 1, display: "flex", gap: 12 }}>
                <KPICard
                  label={t("dashboard.kpi.scope_total")}
                  value={scopeLoading ? "…" : kpi.total}
                  sub={t("dashboard.kpi_sub.scope_total")}
                />
                <KPICard
                  label={t("dashboard.kpi.at_risk")}
                  value={scopeLoading ? "…" : kpi.risc}
                  sub={t("dashboard.kpi_sub.at_risk")}
                  color="var(--err)"
                />
                {/* «En curs» perd el daurat i queda NEUTRE (§8c): dels tres KPI d'aquesta
                    pantalla, l'únic que és una alerta és «En risc», i és l'únic que porta
                    semàfor. El daurat no pinta números. */}
                <KPICard
                  label={t("dashboard.kpi.in_progress")}
                  value={scopeLoading ? "…" : kpi.open}
                  sub={t("dashboard.kpi_sub.in_progress")}
                />
              </div>
              {/* PROPERAMENT — relatiu + inner absolut: l'alçada la dicta la fila de KPIs; scroll intern. */}
              <div style={{ flex: 1, position: "relative" }}>
                <div style={{
                  position: "absolute", inset: 0, overflowY: "auto",
                  border: "1px solid var(--line)", borderRadius: "var(--r-card)",
                  background: "var(--panel)", padding: 16, fontSize: "var(--fs-body)",
                }}>
                  {upcoming.length === 0 ? (
                    <div style={{ color: "var(--text-faint)", fontSize: "var(--fs-body)", fontStyle: "italic" }}>
                      {t("dashboard.upcoming.empty")}
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {upcoming.map(it => {
                        const dataFmt = new Date(it.day + "T00:00:00").toLocaleDateString(
                          i18n.language || "ca", { day: "numeric", month: "long" })
                        return (
                          <div key={it.id} style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--text-main)" }}>
                            {/* §8 · 16px (fila de llista) i tinta de repòs `--text-soft`. Els
                                15px no són de cap de les tres mides, i `--gray` és legacy. */}
                            <i className={`ti ${it.tipus === "fitting" ? "ti-ruler-2" : "ti-building-factory"}`}
                               aria-hidden="true" style={{ fontSize: 16, color: "var(--text-soft)" }} />
                            <span style={{ flex: 1, fontSize: "var(--fs-body)" }}>
                              {it.tipus === "fitting"
                                ? t("dashboard.upcoming.fitting", { data: dataFmt })
                                : t("dashboard.upcoming.proto", { nom: nomById[it.model_id] || "—", data: dataFmt })}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Board per-model (a continuació): rep l'abast (responsable=me quan "els meus"). */}
          <ModelBoard scope={scope} />
        </>
      )}
      </>
      )}
      </div>
    </>
  )
}
