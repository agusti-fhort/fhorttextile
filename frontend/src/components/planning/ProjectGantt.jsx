import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { plan, companyCalendar } from '../../api/endpoints'
import Center from '../ui/Center'
import { IconPackage, IconUser, IconFlag } from '@tabler/icons-react'

// Calendari-Gantt de projecte (LECTURA): UNA barra per model, eix=DIES. Consumeix GET plan/gantt/.
// Drag-ready: les barres es posicionen per data absoluta (x = dies des de l'inici del rang) → afegir
// el drag de prioritats (M-assist) després només cal sobre aquesta capa, sense reescriure-la.
// Tokens del DS (no canvas). CONVIU amb el tab "Calendari" (PlanningCalendar, executor/hores).
const MONO = 'IBM Plex Mono, monospace'
const LABEL_W = 320
const PX_PER_DAY = 44   // prou ample per encabir "dd/mm" a cada dia sense solapar
const ROW_H = 50
const BAR_H = 24
const AXIS_H = 26
const DEFAULT_COLOR = 'var(--gray)'

const parseISO = (s) => new Date(s + 'T00:00:00')
const dayDiff = (a, b) => Math.round((b - a) / 86400000)
const fmtDM = (d) => `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`
// PEÇA 3 — no-laborables des de CompanyCalendar (font única, MATEIXA lògica que PlanningCalendar):
// DOW alineat amb weekday() del backend (0=dilluns); un dia és no-laborable si el seu dia de setmana
// no té trams d'horari O és a festius_extra → isDayOff = slotsFor(d).length===0 || festius.includes(iso).
const DOW = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
const dowKey = (d) => DOW[(d.getDay() + 6) % 7]
const isoLocal = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const FASE_ORDER = ['Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']
// Paleta categòrica per a "pintar per" (data-viz; mateix criteri que els colors fixos de
// PlanningCalendar). El color de tècnic ve del backend (responsable_color).
const FASE_COLORS = {
  Pending: '#9aa0a6', Dev: '#3a7ca5', Proto: '#7e57c2', SizeSet: '#2a9d8f', PP: '#e07b39', TOP: '#3c9a5f',
}
const PALETTE = ['#3a7ca5', '#e07b39', '#7e57c2', '#2a9d8f', '#c0476b', '#b08900', '#5c6bc0', '#7c6f64']
function paletteColor(key) {
  let h = 0; const s = String(key || '')
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return PALETTE[h % PALETTE.length]
}

// Pròxima fita futura (>= avui) d'un model, per a l'ordre "pròxima fita". Sense fita futura → ∞.
function nextFita(m, today) {
  const fut = (m.fites || []).map(f => f.data).filter(d => !today || d >= today).sort()
  return fut.length ? fut[0] : '9999-12-31'
}

export default function ProjectGantt({ t, mine = false }) {
  const navigate = useNavigate()
  const [models, setModels] = useState([])
  const [today, setToday] = useState(null)
  const [loading, setLoading] = useState(true)
  const [order, setOrder] = useState('lliurament')   // lliurament | fita | fase
  const [riskFirst, setRiskFirst] = useState(false)
  const [onlyRisk, setOnlyRisk] = useState(false)
  const [colorBy, setColorBy] = useState('tecnic')   // tecnic | fase | risc | colleccio
  const [filterTechs, setFilterTechs] = useState(() => new Set())   // buit = tots
  const [filterColleccio, setFilterColleccio] = useState('')
  const [filterTemporada, setFilterTemporada] = useState('')
  const [horaris, setHoraris] = useState({})   // CompanyCalendar: {dia:[[a,b],...]}
  const [festius, setFestius] = useState([])   // festius_extra (dates ISO)

  useEffect(() => {
    plan.gantt(mine ? { mine: true } : {})
      .then(res => { setModels(res.data?.models || []); setToday(res.data?.today || null) })
      .catch(() => setModels([]))
      .finally(() => setLoading(false))
  }, [mine])

  // PEÇA 3 — calendari laboral (no-laborables): càrrega única, MATEIXA font que PlanningCalendar.
  useEffect(() => {
    companyCalendar.get()
      .then(res => {
        const h = res.data?.horaris || {}
        setHoraris(Object.fromEntries(DOW.map(d => [d, Array.isArray(h[d]) ? h[d] : []])))
        setFestius(Array.isArray(res.data?.festius_extra) ? res.data.festius_extra : [])
      })
      .catch(() => {})
  }, [])

  // Llistes distintes per als filtres (a partir de les dades carregades).
  const opts = useMemo(() => {
    const techs = new Map(), cols = new Set(), temps = new Set()
    for (const m of models) {
      if (m.responsable_id) techs.set(m.responsable_id, { id: m.responsable_id, nom: m.responsable_nom, color: m.responsable_color })
      if (m.collection) cols.add(m.collection)
      if (m.temporada) temps.add(m.temporada)
    }
    return { techs: [...techs.values()].sort((a, b) => (a.nom || '').localeCompare(b.nom || '')),
             cols: [...cols].sort(), temps: [...temps].sort() }
  }, [models])

  // Color d'una barra segons l'eix "pintar per" (ortogonal al filtre).
  const colorOf = (m) => {
    if (colorBy === 'fase') return FASE_COLORS[m.fase] || DEFAULT_COLOR
    if (colorBy === 'risc') return m.en_risc ? 'var(--err)' : 'var(--ok)'
    if (colorBy === 'colleccio') return m.collection ? paletteColor(m.collection) : DEFAULT_COLOR
    return m.responsable_color || DEFAULT_COLOR   // tècnic (default)
  }

  // Models a pintar: FILTRE (multi-tècnic / col·lecció / temporada / només risc) → ordre → risc primer.
  const displayed = useMemo(() => {
    let list = models.filter(m =>
      (!onlyRisk || m.en_risc) &&
      (filterTechs.size === 0 || filterTechs.has(m.responsable_id)) &&
      (!filterColleccio || m.collection === filterColleccio) &&
      (!filterTemporada || m.temporada === filterTemporada))
    const cmp = {
      lliurament: (a, b) => a.end.localeCompare(b.end) || a.codi.localeCompare(b.codi),
      fita: (a, b) => nextFita(a, today).localeCompare(nextFita(b, today)) || a.codi.localeCompare(b.codi),
      fase: (a, b) => (FASE_ORDER.indexOf(a.fase) - FASE_ORDER.indexOf(b.fase)) || a.end.localeCompare(b.end),
    }[order]
    list.sort(cmp)
    if (riskFirst) list.sort((a, b) => (b.en_risc === a.en_risc ? 0 : b.en_risc ? 1 : -1))
    return list
  }, [models, onlyRisk, order, riskFirst, today, filterTechs, filterColleccio, filterTemporada])

  // Rang temporal global: min(primera data, avui) i max(última data, avui), amb 60 dies de
  // marge a banda i banda → AVUI sempre dins el rang i prou aire perquè l'scroll horitzontal
  // existent mostri context passat i futur encara que les barres caiguin en un interval estret.
  const range = useMemo(() => {
    if (!models.length) return null
    let min = null, max = null
    for (const m of models) {
      const s = parseISO(m.start), e = parseISO(m.end)
      if (min === null || s < min) min = s
      if (max === null || e > max) max = e
      for (const f of m.fites) { const d = parseISO(f.data); if (d < min) min = d; if (d > max) max = d }
      if (m.data_objectiu) { const d = parseISO(m.data_objectiu); if (d > max) max = d; if (d < min) min = d }
    }
    const ref = today ? parseISO(today) : new Date()   // avui dins el rang sempre
    if (min === null || ref < min) min = ref
    if (max === null || ref > max) max = ref
    const MARGIN = 60 * 86400000
    min = new Date(min.getTime() - MARGIN)
    max = new Date(max.getTime() + MARGIN)
    return { min, max, days: dayDiff(min, max) + 1 }
  }, [models, today])

  const scrollRef = useRef(null)
  // Posiciona AVUI a prop de l'esquerra del viewport: track-x d'avui (la mateixa x que pinta la línia
  // daurada) menys 2 dies de marge. Idempotent; degrada net si encara no hi ha layout (guards + rAF).
  const scrollToToday = useCallback(() => {
    if (!range || !today || !scrollRef.current) return
    const tx = dayDiff(range.min, parseISO(today)) * PX_PER_DAY
    scrollRef.current.scrollLeft = Math.max(0, tx - 2 * PX_PER_DAY)
  }, [range, today])

  useEffect(() => {
    const id = requestAnimationFrame(scrollToToday)   // post-layout: el contenidor ja té amplada
    return () => cancelAnimationFrame(id)
  }, [scrollToToday])

  if (loading) return <Center>{t('planning.loading')}</Center>
  if (!range || !models.length) {
    return <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)', border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)' }}>{t('planning.gantt.empty')}</div>
  }

  const trackW = range.days * PX_PER_DAY
  const x = (iso) => dayDiff(range.min, parseISO(iso)) * PX_PER_DAY

  // PEÇA 1 — granularitat DIÀRIA: una columna i una etiqueta per dia (step=1). El scroll-X absorbeix
  // l'amplada extra (PX_PER_DAY=44).
  const step = 1
  const ticks = []
  for (let i = 0; i < range.days; i += step) {
    ticks.push({ i, d: new Date(range.min.getTime() + i * 86400000) })
  }

  // PEÇA 3 — índexs de columna no-laborables (CompanyCalendar). Buit fins que carrega l'horari
  // (evita ombrejar-ho tot mentre horaris=={}). isDayOff = sense trams al dia de setmana O festiu_extra.
  const nonWorkCols = []
  if (Object.keys(horaris).length > 0) {
    for (let i = 0; i < range.days; i++) {
      const d = new Date(range.min.getTime() + i * 86400000)
      if ((horaris[dowKey(d)] || []).length === 0 || festius.includes(isoLocal(d))) nonWorkCols.push(i)
    }
  }

  return (
    <div>
      <GanttControls t={t} order={order} setOrder={setOrder}
                     riskFirst={riskFirst} setRiskFirst={setRiskFirst}
                     onlyRisk={onlyRisk} setOnlyRisk={setOnlyRisk} />
      <ColorFilterControls t={t} colorBy={colorBy} setColorBy={setColorBy} opts={opts}
                           filterTechs={filterTechs} setFilterTechs={setFilterTechs}
                           filterColleccio={filterColleccio} setFilterColleccio={setFilterColleccio}
                           filterTemporada={filterTemporada} setFilterTemporada={setFilterTemporada} />
      <Legend t={t} />
      {/* Botó "Avui": recentra l'scroll horitzontal a la posició d'avui (pastilla outline, tokens). */}
      <div style={{ marginBottom: 8 }}>
        <button type="button" onClick={scrollToToday} style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '4px 12px', borderRadius: 999, cursor: 'pointer',
          border: '1px solid var(--gold)', background: 'transparent', color: 'var(--gold)',
          fontSize: 'var(--fs-label)', fontFamily: MONO,
        }}>
          <i className="ti ti-calendar-event" style={{ fontSize: 14 }} /> {t('planning.gantt.legend_today')}
        </button>
      </div>
      <div ref={scrollRef} style={{ maxHeight: 'calc(100vh - 220px)', overflowY: 'auto', overflowX: 'auto', border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)' }}>
        <div style={{ minWidth: LABEL_W + trackW }}>
          {/* Eix de dies */}
          {/* PEÇA 3 — header sticky-top z=8 (per sobre de les pills z=6 en scroll-Y); cantonada z=9 (màxim) */}
          <div style={{ display: 'flex', position: 'sticky', top: 0, zIndex: 8, background: 'var(--bg-muted)', borderBottom: '0.5px solid var(--gray-l)' }}>
            <div style={{ width: LABEL_W, flexShrink: 0, position: 'sticky', left: 0, background: 'var(--bg-muted)', zIndex: 9, borderRight: '0.5px solid var(--gray-l)' }} />
            <div style={{ position: 'relative', width: trackW, height: AXIS_H }}>
              {ticks.map(tk => {
                // PEÇA 2 — AVUI es distingeix NOMÉS per color daurat (sense pes extra); la resta de
                // dates van en pes normal.
                const isToday = today && isoLocal(tk.d) === today
                return (
                  <div key={tk.i} style={{ position: 'absolute', left: tk.i * PX_PER_DAY, top: 0, height: AXIS_H, borderLeft: '0.5px solid var(--gray-l)' }}>
                    {/* data centrada al MIG de la franja del dia (step=1 → PX_PER_DAY/2) */}
                    <span style={{ position: 'absolute', left: (step * PX_PER_DAY) / 2, top: '50%', transform: 'translate(-50%, -50%)',
                                   fontSize: 'var(--fs-body)', fontFamily: MONO, fontWeight: 400,
                                   color: isToday ? 'var(--gold)' : 'var(--text-main)', whiteSpace: 'nowrap' }}>{fmtDM(tk.d)}</span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Files de models */}
          {displayed.length === 0 ? (
            <div style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('planning.gantt.empty')}</div>
          ) : displayed.map(m => (
            <GanttRow key={m.model_id} m={m} color={colorOf(m)} trackW={trackW} x={x}
                      ticks={ticks} order={order} nonWorkCols={nonWorkCols}
                      onClick={() => navigate(`/models/${m.model_id}`)} t={t} />
          ))}
        </div>
      </div>
    </div>
  )
}

// Controls de l'ordre + realçat de risc. Drag-ready: no toca el layout de barres.
function GanttControls({ t, order, setOrder, riskFirst, setRiskFirst, onlyRisk, setOnlyRisk }) {
  const selS = {
    fontFamily: MONO, fontSize: 'var(--fs-label)', padding: '4px 8px',
    border: '0.5px solid var(--gray-l)', borderRadius: 6, background: 'var(--white)', cursor: 'pointer',
  }
  const chip = (active) => ({
    display: 'inline-flex', alignItems: 'center', gap: 4, cursor: 'pointer',
    fontFamily: MONO, fontSize: 'var(--fs-label)', padding: '4px 10px', borderRadius: 6,
    border: `0.5px solid ${active ? 'var(--err)' : 'var(--gray-l)'}`,
    background: active ? 'var(--err)' : 'none', color: active ? 'var(--white)' : 'var(--text-main)',
  })
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
      <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO }}>
        {t('planning.gantt.order.label')}
        <select value={order} onChange={e => setOrder(e.target.value)} style={selS}>
          <option value="lliurament">{t('planning.gantt.order.lliurament')}</option>
          <option value="fita">{t('planning.gantt.order.fita')}</option>
          <option value="fase">{t('planning.gantt.order.fase')}</option>
        </select>
      </label>
      <button type="button" onClick={() => setRiskFirst(v => !v)} style={chip(riskFirst)}>
        <i className="ti ti-flag" style={{ fontSize: 13 }} />{t('planning.gantt.risk_first')}
      </button>
      <button type="button" onClick={() => setOnlyRisk(v => !v)} style={chip(onlyRisk)}>
        <i className="ti ti-alert-triangle" style={{ fontSize: 13 }} />{t('planning.gantt.only_risk')}
      </button>
    </div>
  )
}

// "Pintar per" (color, default tècnic) + FILTRE multi-select (ortogonal al color).
function ColorFilterControls({ t, colorBy, setColorBy, opts, filterTechs, setFilterTechs,
                               filterColleccio, setFilterColleccio, filterTemporada, setFilterTemporada }) {
  const selS = {
    fontFamily: MONO, fontSize: 'var(--fs-label)', padding: '4px 8px',
    border: '0.5px solid var(--gray-l)', borderRadius: 6, background: 'var(--white)', cursor: 'pointer',
  }
  const toggleTech = (id) => setFilterTechs(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
      <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO }}>
        {t('planning.gantt.color.label')}
        <select value={colorBy} onChange={e => setColorBy(e.target.value)} style={selS}>
          <option value="tecnic">{t('planning.gantt.color.tecnic')}</option>
          <option value="fase">{t('planning.gantt.color.fase')}</option>
          <option value="risc">{t('planning.gantt.color.risc')}</option>
          <option value="colleccio">{t('planning.gantt.color.colleccio')}</option>
        </select>
      </label>

      {opts.cols.length > 0 && (
        <select value={filterColleccio} onChange={e => setFilterColleccio(e.target.value)} style={selS}>
          <option value="">{t('planning.gantt.filter.all_collections')}</option>
          {opts.cols.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      )}
      {opts.temps.length > 0 && (
        <select value={filterTemporada} onChange={e => setFilterTemporada(e.target.value)} style={selS}>
          <option value="">{t('planning.gantt.filter.all_seasons')}</option>
          {opts.temps.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      )}

      {/* multi-select de tècnics (chips); buit = tots */}
      {opts.techs.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO }}>{t('planning.gantt.filter.techs')}</span>
          {opts.techs.map(tech => {
            const on = filterTechs.has(tech.id)
            return (
              <button key={tech.id} type="button" onClick={() => toggleTech(tech.id)} title={tech.nom} style={{
                display: 'inline-flex', alignItems: 'center', gap: 5, cursor: 'pointer',
                fontFamily: MONO, fontSize: 'var(--fs-label)', padding: '3px 9px', borderRadius: 12,
                border: `0.5px solid ${on ? 'var(--text-main)' : 'var(--gray-l)'}`,
                background: on ? 'var(--bg-muted)' : 'none', opacity: (filterTechs.size === 0 || on) ? 1 : 0.5,
              }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: tech.color || DEFAULT_COLOR }} />
                {tech.nom || `#${tech.id}`}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

function GanttRow({ m, color, trackW, x, ticks, order, nonWorkCols, onClick, t }) {
  const left = x(m.start)
  const right = x(m.end) + PX_PER_DAY            // fi inclusiu (el dia de fi compta sencer)
  const width = Math.max(PX_PER_DAY * 0.7, right - left)
  const objX = m.data_objectiu ? x(m.data_objectiu) : null

  // Finestres d'espera (confecció externa): es pinten com a segment trencat ratllat.
  const esperes = (m.esperes || []).map(w => ({ l: x(w.from), r: x(w.to) + PX_PER_DAY }))
  // PEÇA 4 — text de la pastilla (tècnic · next_task[→ data] · %): desborda la barra; també title (hover).
  // La capdavantera mostra la data a la qual s'enfronta (planned_end); sense data → només el codi.
  const nextLabel = m.next_task
    ? (m.next_task_date ? `${m.next_task} → ${fmtDM(parseISO(m.next_task_date))}` : m.next_task)
    : null
  const barText = [m.responsable_nom, nextLabel, `${m.pct}%`].filter(Boolean).join(' · ')

  return (
    <div onClick={onClick} title={`${m.codi} · ${m.nom || ''}`} style={{
      display: 'flex', height: ROW_H, cursor: 'pointer', borderBottom: '0.5px solid var(--base-hairline, var(--gray-l))',
    }}>
      {/* PEÇA 1 — label en 2 LÍNIES (ordre definitiu Agus): línia 1 = codi (gris petit); línia 2 en flow
          horitzontal = nom (negre) · col·lecció · temporada (grisos petits). Tokens d'escala, sense px
          literals. z=7 (sticky-left per sobre de les pills del track z=6 en scroll-X; fons opac). */}
      <div style={{ width: LABEL_W, flexShrink: 0, position: 'sticky', left: 0, background: 'var(--white)', zIndex: 7,
                    borderRight: '0.5px solid var(--gray-l)', borderLeft: m.en_risc ? '2px solid var(--err)' : '2px solid transparent',
                    padding: '8px 14px', overflow: 'hidden', display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 2 }}>
        <div style={{ fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
          {m.en_risc && <i className="ti ti-flag" title={t('planning.gantt.risk_flag')} style={{ fontSize: 'var(--fs-label)', color: 'var(--err)', marginRight: 4 }} />}
          {m.codi}
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 5, overflow: 'hidden' }}>
          <span style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-main)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', flexShrink: 1, minWidth: 0 }}>{m.nom || '—'}</span>
          {m.collection && <span style={{ fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)', whiteSpace: 'nowrap', flexShrink: 0 }}>· {m.collection}</span>}
          {m.temporada && <span style={{ fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)', whiteSpace: 'nowrap', flexShrink: 0 }}>· {m.temporada}</span>}
        </div>
      </div>

      <div style={{ position: 'relative', width: trackW, height: ROW_H }}>
        {/* PEÇA 3 — columnes NO-LABORABLES (CompanyCalendar): cap de setmana / dies sense horari /
            festius_extra. Ombreig MOLT subtil (gris neutre --text-main a opacity 0.06) per no competir
            amb les barres — divergeix a posta del taronja del calendari (decisió Agus). A tota l'alçada
            del track i DARRERE de gridlines i barres (primer fill, sense z-index). */}
        {nonWorkCols.map(i => (
          <div key={`nw${i}`} style={{ position: 'absolute', left: i * PX_PER_DAY, top: 0, bottom: 0, width: PX_PER_DAY, background: 'var(--text-main)', opacity: 0.06 }} />
        ))}
        {/* graella vertical */}
        {ticks.map(tk => (
          <div key={tk.i} style={{ position: 'absolute', left: tk.i * PX_PER_DAY, top: 0, bottom: 0, borderLeft: '0.5px solid var(--bg-muted)' }} />
        ))}
        {/* PEÇA 2 — sense línia AVUI a la graella: el dia actual es marca només a la capçalera (daurada). */}
        {/* línia DATA OBJECTIU (vermella discontínua) */}
        {objX != null && <div style={{ position: 'absolute', left: objX, top: 0, bottom: 0, borderLeft: '1.5px dashed var(--err)' }} />}
        {/* PEÇA 6 — símbol de lliurament a la data objectiu, NOMÉS en ordre 'lliurament' (altres ordres:
            la línia es manté però sense pill). El text de la pastilla ja alinea a la dreta (Peça 4b). */}
        {objX != null && order === 'lliurament' && (
          <div title={t('planning.gantt.legend_objectiu')} style={{
            position: 'absolute', left: objX, top: 2, transform: 'translateX(-50%)', zIndex: 6,
            display: 'flex', alignItems: 'center', gap: 2, padding: '1px 4px', background: 'var(--white)',
            border: '1px solid var(--err)', borderRadius: 8,
          }}>
            <IconFlag size={11} color="var(--err)" stroke={1.75} />
            <span style={{ fontSize: 8, fontFamily: MONO, color: 'var(--err)', lineHeight: 1 }}>obj</span>
          </div>
        )}

        {/* BARRA del model (realçat vermell si en risc). title = xarxa de seguretat (PEÇA 4 opció B). */}
        <div title={barText} style={{ position: 'absolute', left, width, top: (ROW_H - BAR_H) / 2, height: BAR_H,
                      boxShadow: m.en_risc ? '0 0 0 1.5px var(--err)' : 'none', borderRadius: 5 }}>
          {/* contenidor (rang sencer): opacity 0.35 + vora 1px → el color del tècnic es veu encara amb pct=0 */}
          <div style={{ position: 'absolute', inset: 0, borderRadius: 5, background: color, opacity: 0.35, border: `1px solid ${color}` }} />
          {/* farciment % completat (fitat 0-100 per Peça 1) */}
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${m.pct}%`, borderRadius: 5, background: color, opacity: 0.85 }} />
          {/* PEÇA 4 — pastilla: punt-color tècnic · next_task · pct%. Anclada a l'esquerra; el text
              DESBORDA a la dreta de la barra sense ellipsis (overflow visible). Mai es talla. */}
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, display: 'flex', alignItems: 'center',
                        padding: '0 6px', fontSize: 'var(--fs-label)', fontFamily: MONO,
                        color: 'var(--text-main)', whiteSpace: 'nowrap', pointerEvents: 'none' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', flexShrink: 0, marginRight: 5,
                           background: m.responsable_color || DEFAULT_COLOR }} />
            <span>{barText}</span>
          </div>
        </div>

        {/* PEÇA 5 — connector d'espera (confecció externa): línia fina + fletxa ▶ a la dreta, a ROW_H/2.
            Substitueix el segment ratllat dins la barra. */}
        {esperes.map((w, i) => (
          <div key={`w${i}`} title={t('planning.gantt.legend_wait')} style={{
            position: 'absolute', left: w.l, width: Math.max(2, w.r - w.l), top: ROW_H / 2,
            borderTop: '1px solid var(--text-muted)', zIndex: 1,
          }}>
            <span style={{ position: 'absolute', right: -2, top: -6, fontSize: 9, lineHeight: 1, color: 'var(--text-muted)' }}>▶</span>
          </div>
        ))}

        {/* PEÇA 5 — FITES com a contenidor (pill): icona + data curta (dd/mm) */}
        {m.fites.map((f, i) => {
          const Icon = f.tipus === 'proto' ? IconPackage : IconUser
          const col = f.tipus === 'proto' ? 'var(--taupe, #7c6f64)' : 'var(--info, #3a7ca5)'
          return (
            <div key={i} title={`${t(`planning.gantt.legend_${f.tipus}`)} · ${f.data}`} style={{
              position: 'absolute', left: x(f.data) + PX_PER_DAY / 2, top: (ROW_H - 18) / 2, transform: 'translateX(-50%)',
              height: 18, display: 'flex', alignItems: 'center', gap: 4, padding: '2px 6px', zIndex: 6,
              background: 'var(--white)', border: '1px solid var(--gray-l)', borderRadius: 10,
            }}>
              <Icon size={12} color={col} stroke={1.75} />
              <span style={{ fontSize: 'var(--fs-caption)', fontFamily: MONO, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{fmtDM(parseISO(f.data))}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function Legend({ t }) {
  const item = (icon, color, label) => (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO }}>
      {icon === 'line' ? <span style={{ width: 12, borderTop: `1.5px dashed ${color}`, display: 'inline-block' }} />
        : <i className={`ti ti-${icon}`} style={{ fontSize: 13, color }} />}
      {label}
    </span>
  )
  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 10 }}>
      {item('package', 'var(--taupe, #7c6f64)', t('planning.gantt.legend_proto'))}
      {item('user', 'var(--info, #3a7ca5)', t('planning.gantt.legend_fitting'))}
      {item('line', 'var(--err)', t('planning.gantt.legend_objectiu'))}
      {/* PEÇA 2 — sense ítem "Avui": el dia actual es marca amb la data daurada a la capçalera. */}
    </div>
  )
}
