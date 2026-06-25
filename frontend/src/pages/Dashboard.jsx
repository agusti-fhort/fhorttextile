
import { useState, useEffect, useCallback, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import useAuthStore from "../store/auth"
import { modelTasks, models as modelsApi, customers, calendar } from "../api/endpoints"

const API = import.meta.env.VITE_API_URL || ""
const MONO = "IBM Plex Mono, monospace"

// Sprint 5 — board per-model 4-col al Dashboard. Cada card = un MODEL, classificat per
// kanban_state (derivat al backend, by-model 1c) ∈ {pending, open, paused, done}.
// Columnes: [Pendents | En curs (Open) | Pausats | Fets]. Mateixa paleta que el Kanban jubilat
// (pending=gris, open=or, paused=àmbar, done=verd), però via tokens del design system.
const BOARD_COLS = [
  { key: "pending", icon: "ti-inbox",        color: "var(--gray)" },
  { key: "open",    icon: "ti-player-play",  color: "var(--gold)" },
  { key: "paused",  icon: "ti-player-pause", color: "var(--warn)" },
  { key: "done",    icon: "ti-circle-check", color: "var(--ok)" },
]
// Fases del cicle de disseny (eix independent del kanban_state) per als comptadors per fase.
const PHASES = ["Pending", "Dev", "Proto", "SizeSet", "PP", "TOP"]
const TEMPORADES = ["SS", "FW", "CO", "SP"]
const ESTATS = ["Nou", "EnCurs", "EnRevisio", "Tancat"]

function KPICard({ label, value, sub, color = "var(--gold)", onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--white)", border: "1px solid var(--border)", borderRadius: 8,
        padding: "18px 20px", cursor: onClick ? "pointer" : "default",
        transition: "all .1s", flex: 1, minWidth: 140,
      }}
      onMouseEnter={e => onClick && (e.currentTarget.style.borderColor = color)}
      onMouseLeave={e => onClick && (e.currentTarget.style.borderColor = "var(--border)")}
    >
      <div style={{ fontSize: 'var(--fs-body)', color: "var(--text-muted)", fontFamily: MONO, marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 'var(--fs-display)', fontWeight: 600, color, fontFamily: MONO, lineHeight: 1 }}>{value ?? "—"}</div>
      {sub && <div style={{ fontSize: 'var(--fs-body)', color: "var(--text-muted)", fontFamily: MONO, marginTop: 6 }}>{sub}</div>}
    </div>
  )
}

const selS = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 9px',
  border: '0.5px solid var(--gray-l)', borderRadius: 8,
  background: 'var(--white)', color: 'var(--text-main)',
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
function ModelCard({ model, onClick, t }) {
  const c = model.counts || {}
  const total = (c.pending || 0) + (c.paused || 0) + (c.in_progress || 0) + (c.done || 0)
  const faseLabel = model.fase ? t(`model_sheet.dashboard.phase.${model.fase}`, model.fase) : null
  return (
    <button onClick={onClick} style={{
      textAlign: 'left', width: '100%', border: '0.5px solid var(--gray-l)',
      background: 'var(--white)', borderRadius: 8, padding: '8px 10px',
      cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 4,
    }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--gray-l)' }}
    >
      <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--gold)' }}>
        {model.model_codi || `#${model.model_id}`}
      </div>
      {model.model_nom && (
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', lineHeight: 1.3 }}>{model.model_nom}</div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
        {faseLabel && (
          <span style={{
            fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO,
            padding: '1px 6px', borderRadius: 6, background: 'var(--gray-l)',
          }}>{faseLabel}</span>
        )}
        <span style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>{t('dashboard.board.tasks_n', { n: total })}</span>
      </div>
    </button>
  )
}

// Mini-chip de comptador per fase.
function FaseChip({ label, n }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)',
      padding: '3px 9px', borderRadius: 10, background: 'var(--white)', border: '0.5px solid var(--gray-l)',
    }}>
      <span>{label}</span>
      <span style={{ fontWeight: 600, color: 'var(--text-main)', fontVariantNumeric: 'tabular-nums' }}>{n}</span>
    </span>
  )
}

function ModelBoard({ scope }) {
  const navigate = useNavigate()
  const { t } = useTranslation()

  // Filtres de campanya (tot va al backend; consumeix by-model + fase-counts, Sprint 5 1a/1b).
  const [search, setSearch] = useState("")
  const [fTemporada, setFTemporada] = useState("")
  const [fEstat, setFEstat] = useState("")
  const [fCustomer, setFCustomer] = useState("")
  const [fCollection, setFCollection] = useState("")
  const [fAfter, setFAfter] = useState("")
  const [fBefore, setFBefore] = useState("")

  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [loading, setLoading] = useState(true)
  const [faseCounts, setFaseCounts] = useState({ counts: {}, total: 0 })
  const [customerOpts, setCustomerOpts] = useState([])

  // Paràmetres de campanya compartits per by-model i fase-counts (mateix contracte de filtres).
  // L'abast (scope) "els meus" hi afegeix responsable=me (assignee), de manera que board, chips i
  // comptadors es filtren com els KPIs en commutar l'abast.
  const buildParams = useCallback(() => {
    const p = {}
    if (scope === 'me') p.responsable = 'me'
    const s = search.trim(); if (s) p.search = s
    if (fTemporada) p.temporada = fTemporada
    if (fEstat) p.estat = fEstat
    if (fCustomer) p.customer = fCustomer
    const col = fCollection.trim(); if (col) p.collection = col
    if (fAfter) p.data_objectiu_after = fAfter
    if (fBefore) p.data_objectiu_before = fBefore
    return p
  }, [scope, search, fTemporada, fEstat, fCustomer, fCollection, fAfter, fBefore])

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

  // Opcions de client per al filtre (un sol cop).
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
    setSearch(""); setFTemporada(""); setFEstat("")
    setFCustomer(""); setFCollection(""); setFAfter(""); setFBefore("")
  }

  // Classificació dels models carregats per kanban_state (derivat al backend).
  const byState = useMemo(() => {
    const groups = { pending: [], open: [], paused: [], done: [] }
    rows.forEach(m => { (groups[m.kanban_state] || groups.pending).push(m) })
    return groups
  }, [rows])

  return (
    <div>
      {/* Capçalera + comptadors per fase */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
        <div style={{
          fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".08em",
          textTransform: "uppercase", color: "var(--gold)", fontFamily: MONO,
        }}>
          {t("dashboard.board.title")}
        </div>
        <span style={{ fontSize: 'var(--fs-body)', color: "var(--text-muted)", fontFamily: MONO }}>
          {t("dashboard.board.results_n", { n: count })}
        </span>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <FaseChip label={t("dashboard.board.total")} n={faseCounts.total ?? 0} />
        {PHASES.map(ph => (
          <FaseChip key={ph} label={t(`model_sheet.dashboard.phase.${ph}`, ph)} n={faseCounts.counts?.[ph] ?? 0} />
        ))}
      </div>

      {/* Filtres de campanya */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 16 }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder={t("dashboard.board.search_ph")}
          style={{ ...selS, flex: "0 1 240px", minWidth: 160 }}
        />
        <select value={fCustomer} onChange={e => setFCustomer(e.target.value)} style={selS}>
          <option value="">{t("dashboard.board.filter_customer")}</option>
          {customerOpts.map(c => (
            <option key={c.id} value={c.id}>{c.nom || c.codi || `#${c.id}`}</option>
          ))}
        </select>
        <input
          value={fCollection} onChange={e => setFCollection(e.target.value)}
          placeholder={t("dashboard.board.filter_collection")}
          style={{ ...selS, width: 150 }}
        />
        <select value={fTemporada} onChange={e => setFTemporada(e.target.value)} style={selS}>
          <option value="">{t("dashboard.board.filter_temporada")}</option>
          {TEMPORADES.map(x => <option key={x} value={x}>{t(`kanban.temporades.${x}`)}</option>)}
        </select>
        <select value={fEstat} onChange={e => setFEstat(e.target.value)} style={selS}>
          <option value="">{t("dashboard.board.filter_estat")}</option>
          {ESTATS.map(x => <option key={x} value={x}>{t(`kanban.estats.${x}`)}</option>)}
        </select>
        <label style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 'var(--fs-label)', color: "var(--text-muted)", fontFamily: MONO }}>
          {t("dashboard.board.filter_date_from")}
          <input type="date" value={fAfter} onChange={e => setFAfter(e.target.value)} style={selS} />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 'var(--fs-label)', color: "var(--text-muted)", fontFamily: MONO }}>
          {t("dashboard.board.filter_date_to")}
          <input type="date" value={fBefore} onChange={e => setFBefore(e.target.value)} style={selS} />
        </label>
        <button onClick={clearFilters} style={{ ...selS, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
          <i className="ti ti-x" style={{ fontSize: 12 }} /> {t("dashboard.board.clear")}
        </button>
      </div>

      {/* Board 4-col */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: "1rem", alignItems: "start" }}>
        {BOARD_COLS.map(col => {
          const items = byState[col.key] || []
          return (
            <div key={col.key} style={{
              background: "var(--white)", border: "0.5px solid var(--border)", borderRadius: 12,
              overflow: "hidden", display: "flex", flexDirection: "column", minHeight: 320, minWidth: 0,
            }}>
              <div style={{
                padding: "0.8rem 1rem", borderBottom: "0.5px solid var(--border)",
                display: "flex", alignItems: "center", gap: 8, background: "var(--gray-l)",
              }}>
                <i className={`ti ${col.icon}`} style={{ fontSize: 14, color: col.color }} />
                <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500 }}>{t(`dashboard.board.state.${col.key}`)}</span>
                <span style={{
                  marginLeft: "auto", fontSize: 'var(--fs-body)', color: "var(--gray)",
                  padding: "2px 8px", borderRadius: 10, background: "var(--white)",
                }}>{items.length}</span>
              </div>
              <div style={{ flex: 1, padding: "0.6rem", display: "flex", flexDirection: "column", gap: 6 }}>
                {loading && rows.length === 0 ? (
                  <div style={ph}>{t("common.loading")}</div>
                ) : items.length === 0 ? (
                  <div style={ph}>{t("dashboard.board.empty_col")}</div>
                ) : items.map(m => (
                  <ModelCard key={m.model_id} model={m} t={t} onClick={() => navigate(`/models/${m.model_id}`)} />
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {hasNext && (
        <div style={{ display: "flex", justifyContent: "center", marginTop: 16 }}>
          <button onClick={loadMore} disabled={loading} style={{
            ...selS, cursor: loading ? "default" : "pointer", opacity: loading ? 0.6 : 1,
            display: "flex", alignItems: "center", gap: 6, padding: "8px 16px",
          }}>
            <i className={`ti ${loading ? "ti-loader-2" : "ti-chevron-down"}`} style={{ fontSize: 13 }} />
            {t("dashboard.board.load_more")}
          </button>
        </div>
      )}
    </div>
  )
}

const ph = { fontSize: 'var(--fs-body)', color: 'var(--gray)', textAlign: 'center', padding: '1.2rem', fontWeight: 300 }

// Finestra (dies) de "Properes fites" que es consulta a calendar/events.
const MILESTONES_DAYS = 14
const MILESTONE_ICON = { tasca: "ti-subtask", confeccio: "ti-building-factory", fitting: "ti-ruler-2" }
// Data local YYYY-MM-DD (no UTC) per acotar el rang de l'endpoint.
function localISO(d) {
  const z = n => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`
}

// Sprint 5 — "Properes fites": arribada de proto / fitting / tasca en risc en els propers
// MILESTONES_DAYS dies, agrupades per data. Reusa GET /calendar/events/ (unifica tasca +
// confecció + fitting); cap view nova.
function UpcomingMilestones() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const today = new Date()
    const end = new Date(); end.setDate(end.getDate() + MILESTONES_DAYS)
    calendar.events({ start: localISO(today), end: localISO(end) })
      .then(res => {
        const events = res.data?.events ?? []
        // Agrupa per dia (prefix YYYY-MM-DD, vàlid tant per ISO datetime com per date-only).
        const byDay = {}
        events.forEach(ev => {
          if (!ev.start) return
          const day = ev.start.slice(0, 10)
          ;(byDay[day] ||= []).push(ev)
        })
        const sorted = Object.keys(byDay).sort().map(day => ({
          day,
          events: byDay[day].sort((a, b) => (a.start || "").localeCompare(b.start || "")),
        }))
        setGroups(sorted)
      })
      .catch(() => setGroups([]))
      .finally(() => setLoading(false))
  }, [])

  const fmtDay = (day) => new Date(day + "T00:00:00").toLocaleDateString(
    i18n.language || "ca", { weekday: "long", day: "numeric", month: "long" })

  return (
    <div style={{ marginTop: 32 }}>
      <div style={{
        fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".08em",
        textTransform: "uppercase", color: "var(--gold)", fontFamily: MONO, marginBottom: 12,
      }}>
        {t("dashboard.milestones.title")}
      </div>
      {loading ? (
        <div style={{ color: "var(--text-muted)", fontSize: 'var(--fs-body)', fontFamily: MONO }}>{t("common.loading")}</div>
      ) : groups.length === 0 ? (
        <div style={{
          padding: "20px", border: "1px dashed var(--border)", borderRadius: 8,
          textAlign: "center", color: "var(--text-muted)", fontSize: 'var(--fs-body)', fontFamily: MONO,
        }}>
          {t("dashboard.milestones.empty", { days: MILESTONES_DAYS })}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {groups.map(g => (
            <div key={g.day}>
              <div style={{
                fontSize: 'var(--fs-label)', fontFamily: MONO, color: "var(--text-muted)",
                textTransform: "capitalize", marginBottom: 6,
              }}>
                {fmtDay(g.day)}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {g.events.map(ev => (
                  <button key={ev.id} onClick={() => ev.link && navigate(ev.link)} style={{
                    textAlign: "left", width: "100%", border: "0.5px solid var(--gray-l)",
                    background: "var(--white)", borderRadius: 8, padding: "8px 12px", cursor: ev.link ? "pointer" : "default",
                    display: "flex", alignItems: "center", gap: 10,
                  }}
                    onMouseEnter={e => ev.link && (e.currentTarget.style.borderColor = "var(--gold)")}
                    onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--gray-l)")}
                  >
                    <i className={`ti ${MILESTONE_ICON[ev.tipus] || "ti-point"}`} style={{ fontSize: 15, color: ev.color || "var(--gray)" }} />
                    <span style={{ flex: 1, fontSize: 'var(--fs-body)', color: "var(--text-main)" }}>{ev.titol}</span>
                    <span style={{ fontSize: 'var(--fs-label)', fontFamily: MONO, color: "var(--text-muted)" }}>
                      {t(`dashboard.milestones.type.${ev.tipus}`, ev.tipus)}
                    </span>
                    {ev.en_risc && (
                      <span style={{
                        fontSize: 'var(--fs-label)', color: "var(--err)", background: "var(--err-bg)",
                        padding: "1px 7px", borderRadius: 8, whiteSpace: "nowrap",
                      }}>
                        <i className="ti ti-alert-triangle" style={{ fontSize: 11 }} /> {t("dashboard.milestones.at_risk")}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Selector d'abast del dashboard del tècnic: [Els meus · Tots]. Default per ROL (es deriva del
// rol/capabilities a Dashboard, NO de localStorage). Sempre visible i commutable.
const SCOPES = [["me", "scope_mine"], ["all", "scope_all"]]
function ScopeSelector({ scope, onChange, t }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
      <span style={{ fontSize: 'var(--fs-label)', fontFamily: MONO, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: ".06em" }}>
        {t("dashboard.scope.label")}
      </span>
      <div style={{ display: "flex", border: "0.5px solid var(--gray-l)", borderRadius: 8, overflow: "hidden" }}>
        {SCOPES.map(([val, key]) => {
          const active = scope === val
          return (
            <button key={val} onClick={() => onChange(val)} style={{
              fontFamily: MONO, fontSize: 'var(--fs-body)', padding: "7px 16px", border: "none", cursor: "pointer",
              background: active ? "var(--gold-pale)" : "var(--white)",
              color: active ? "var(--gold)" : "var(--gray)", fontWeight: active ? 600 : 400,
            }}>{t(`dashboard.scope.${key}`)}</button>
          )
        })}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const token = useAuthStore.getState().token || localStorage.getItem('access_token')

  // Auth guard: redirect if there is no token (no fetch will run without auth)
  useEffect(() => { if (!token) navigate("/login") }, [token, navigate])
  const [me, setMe] = useState(null)
  const [onboarding, setOnboarding] = useState(null)

  // Abast [me|all]. null fins que arriba `me` → default per rol (view_team_tasks → tots; si no, meus).
  const [scope, setScope] = useState(null)
  const [scopeRows, setScopeRows] = useState([])     // by-model de l'abast (substrat dels KPIs)
  const [scopeLoading, setScopeLoading] = useState(true)
  // Models amb ≥1 tasca en risc (planned_end > data_objectiu), de calendar/events. Es creua amb
  // l'abast (scopeRows) per al KPI 'En risc'; es carrega un sol cop (la visibilitat ja l'acota el backend).
  const [riskyModelIds, setRiskyModelIds] = useState(() => new Set())

  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` }
    Promise.allSettled([
      fetch(`${API}/api/v1/me/`, { headers }).then(r => r.json()),
      fetch(`${API}/api/v1/onboarding-status/`, { headers }).then(r => r.ok ? r.json() : null),
    ]).then(([meRes, onbRes]) => {
      if (meRes.status === "fulfilled") {
        setMe(meRes.value)
        // Default d'abast per rol (només si encara no s'ha fixat): qui veu l'equip
        // (view_team_tasks) → "tots"; la resta (tècnic) → "els meus". Substrat: §16.C. NO localStorage.
        const caps = meRes.value?.capabilities || []
        setScope(prev => prev ?? (caps.includes("view_team_tasks") ? "all" : "me"))
      }
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

  // Substrat dels KPIs: by-model de TOT l'abast (scope-only, sense filtres de campanya). Es
  // recarrega en commutar l'abast. all=true per comptar també els models tot-Done. El load es
  // difereix (setTimeout) per no cridar setState síncron dins l'efecte (mateix patró que el board).
  useEffect(() => {
    if (scope === null) return
    let alive = true
    const id = setTimeout(() => {
      setScopeLoading(true)
      const params = { all: "true", ...(scope === "me" ? { responsable: "me" } : {}) }
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
    <div style={{ padding: "24px", maxWidth: 1280, margin: "0 auto" }}>
      {/* Onboarding banner */}
      {onboarding && typeof onboarding.percentatge === 'number' && onboarding.percentatge < 100 && (
        <div
          onClick={() => navigate('/onboarding')}
          style={{
            marginBottom: 20, padding: '12px 16px',
            borderRadius: 8, background: 'var(--gold-pale)',
            border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', gap: 14,
            cursor: 'pointer',
          }}
        >
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            background: 'var(--white)', color: 'var(--gold)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 'var(--fs-body)', fontWeight: 600,
          }}>
            {onboarding.percentatge}%
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>
              {t('dashboard.onboarding_incomplete')}
            </div>
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginTop: 2 }}>
              {onboarding.passos_pendents
                ? t('dashboard.onboarding_steps_left', { count: onboarding.passos_pendents })
                : t('dashboard.onboarding_complete_setup')}
            </div>
          </div>
          <span style={{
            padding: '6px 12px', borderRadius: 6, fontSize: 'var(--fs-body)',
            background: 'var(--gold)', color: 'var(--white)', fontWeight: 500,
          }}>
            {t('dashboard.complete_setup')} →
          </span>
        </div>
      )}

      {/* Greeting */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, color: "var(--text-main)", margin: "0 0 4px" }}>
          {salutacio}{me ? `, ${me.full_name?.split(" ")[0] || me.username}` : ""}.
        </h1>
        <div style={{ fontSize: 'var(--fs-body)', color: "var(--text-muted)", fontFamily: MONO }}>
          {new Date().toLocaleDateString(i18n.language || "ca", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
        </div>
      </div>

      {/* Selector d'abast (DALT): Els meus · Tots. */}
      {scope !== null && <ScopeSelector scope={scope} onChange={setScope} t={t} />}

      {scope === "me" && !scopeLoading && scopeRows.length === 0 ? (
        // Estat buit de "els meus": NO cau a tots; convida a mirar tot l'abast.
        <div style={{
          padding: "32px 20px", border: "1px dashed var(--border)", borderRadius: 8,
          textAlign: "center", color: "var(--text-muted)", fontSize: 'var(--fs-body)', fontFamily: MONO,
        }}>
          <i className="ti ti-inbox-off" style={{ fontSize: 26, color: "var(--gray)", display: "block", marginBottom: 8 }} />
          {t("dashboard.scope.empty_mine")}
        </div>
      ) : (
        <>
          {/* KPIs (SOTA el selector) — derivats de l'abast. Senyals d'acció, no recompte de fases. */}
          <div style={{ display: "flex", gap: 12, marginBottom: 28, flexWrap: "wrap" }}>
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
            <KPICard
              label={t("dashboard.kpi.in_progress")}
              value={scopeLoading ? "…" : kpi.open}
              sub={t("dashboard.kpi_sub.in_progress")}
              color="var(--gold)"
            />
          </div>

          {/* Board per-model (a continuació): rep l'abast (responsable=me quan "els meus"). */}
          <ModelBoard scope={scope} />
        </>
      )}

      {/* Properes fites: arribades de proto / fittings / tasques en risc (calendar/events). */}
      <UpcomingMilestones />
    </div>
  )
}
