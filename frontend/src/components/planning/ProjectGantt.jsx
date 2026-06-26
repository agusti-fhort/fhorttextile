import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { plan } from '../../api/endpoints'
import Center from '../ui/Center'

// Calendari-Gantt de projecte (LECTURA): UNA barra per model, eix=DIES. Consumeix GET plan/gantt/.
// Drag-ready: les barres es posicionen per data absoluta (x = dies des de l'inici del rang) → afegir
// el drag de prioritats (M-assist) després només cal sobre aquesta capa, sense reescriure-la.
// Tokens del DS (no canvas). CONVIU amb el tab "Calendari" (PlanningCalendar, executor/hores).
const MONO = 'IBM Plex Mono, monospace'
const LABEL_W = 190
const PX_PER_DAY = 26
const ROW_H = 36
const BAR_H = 20
const AXIS_H = 26
const DEFAULT_COLOR = 'var(--gray)'

const parseISO = (s) => new Date(s + 'T00:00:00')
const dayDiff = (a, b) => Math.round((b - a) / 86400000)
const fmtDM = (d) => `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`
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

export default function ProjectGantt({ t }) {
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

  useEffect(() => {
    plan.gantt({})
      .then(res => { setModels(res.data?.models || []); setToday(res.data?.today || null) })
      .catch(() => setModels([]))
      .finally(() => setLoading(false))
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

  // Rang temporal global (min start, max end) amb 1 dia de marge a banda i banda.
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
    min = new Date(min.getTime() - 86400000)
    max = new Date(max.getTime() + 86400000)
    return { min, max, days: dayDiff(min, max) + 1 }
  }, [models])

  if (loading) return <Center>{t('planning.loading')}</Center>
  if (!range || !models.length) {
    return <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)', border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)' }}>{t('planning.gantt.empty')}</div>
  }

  const trackW = range.days * PX_PER_DAY
  const x = (iso) => dayDiff(range.min, parseISO(iso)) * PX_PER_DAY
  const todayX = today ? x(today) : null

  // Ticks de l'eix (densitat segons amplada del rang).
  const step = range.days > 40 ? 7 : (range.days > 14 ? 3 : 1)
  const ticks = []
  for (let i = 0; i < range.days; i += step) {
    ticks.push({ i, d: new Date(range.min.getTime() + i * 86400000) })
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
      <div style={{ maxHeight: 'calc(100vh - 220px)', overflowY: 'auto', overflowX: 'auto', border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)' }}>
        <div style={{ minWidth: LABEL_W + trackW }}>
          {/* Eix de dies */}
          <div style={{ display: 'flex', position: 'sticky', top: 0, zIndex: 3, background: 'var(--bg-muted)', borderBottom: '0.5px solid var(--gray-l)' }}>
            <div style={{ width: LABEL_W, flexShrink: 0, position: 'sticky', left: 0, background: 'var(--bg-muted)', zIndex: 4, borderRight: '0.5px solid var(--gray-l)' }} />
            <div style={{ position: 'relative', width: trackW, height: AXIS_H }}>
              {ticks.map(tk => (
                <div key={tk.i} style={{ position: 'absolute', left: tk.i * PX_PER_DAY, top: 0, height: AXIS_H, borderLeft: '0.5px solid var(--gray-l)', paddingLeft: 3 }}>
                  <span style={{ fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)' }}>{fmtDM(tk.d)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Files de models */}
          {displayed.length === 0 ? (
            <div style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('planning.gantt.empty')}</div>
          ) : displayed.map(m => (
            <GanttRow key={m.model_id} m={m} color={colorOf(m)} trackW={trackW} x={x} todayX={todayX}
                      ticks={ticks} onClick={() => navigate(`/models/${m.model_id}`)} t={t} />
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

function GanttRow({ m, color, trackW, x, todayX, ticks, onClick, t }) {
  const left = x(m.start)
  const right = x(m.end) + PX_PER_DAY            // fi inclusiu (el dia de fi compta sencer)
  const width = Math.max(PX_PER_DAY * 0.7, right - left)
  const objX = m.data_objectiu ? x(m.data_objectiu) : null

  // Finestres d'espera (confecció externa): es pinten com a segment trencat ratllat.
  const esperes = (m.esperes || []).map(w => ({ l: x(w.from), r: x(w.to) + PX_PER_DAY }))

  // PEÇA 3b — línia de context (col·lecció · any · temporada). L'any es deriva de temporada
  // ("FW26"→"26"); si temporada ja conté l'any (cas habitual) no el dupliquem. Sense col·lecció → s'omet.
  const anyTxt = m.temporada ? (String(m.temporada).match(/\d+/) || [''])[0] : ''
  const seasonCtx = (anyTxt && m.temporada && !m.temporada.includes(anyTxt)) ? [anyTxt, m.temporada] : [m.temporada]
  const ctxLine = m.collection ? [m.collection, ...seasonCtx].filter(Boolean).join(' · ') : null

  return (
    <div onClick={onClick} title={`${m.codi} · ${m.nom || ''}`} style={{
      display: 'flex', height: ROW_H, cursor: 'pointer', borderBottom: '0.5px solid var(--base-hairline, var(--gray-l))',
    }}>
      <div style={{ width: LABEL_W, flexShrink: 0, position: 'sticky', left: 0, background: 'var(--white)', zIndex: 2,
                    borderRight: '0.5px solid var(--gray-l)', borderLeft: m.en_risc ? '2px solid var(--err)' : '2px solid transparent',
                    padding: '2px 10px', overflow: 'hidden', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        {ctxLine && (
          <div style={{ fontSize: 12, fontFamily: MONO, lineHeight: 1.05, color: 'var(--text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{ctxLine}</div>
        )}
        <div style={{ fontSize: 14, fontFamily: MONO, fontWeight: 700, lineHeight: 1.1, color: 'var(--text-main)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
          {m.en_risc && <i className="ti ti-flag" title={t('planning.gantt.risk_flag')} style={{ fontSize: 12, color: 'var(--err)', marginRight: 4 }} />}
          {m.nom || '—'}
        </div>
        <div style={{ fontSize: 11, fontFamily: MONO, lineHeight: 1.05, color: 'var(--text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{m.codi}</div>
      </div>

      <div style={{ position: 'relative', width: trackW, height: ROW_H }}>
        {/* graella vertical */}
        {ticks.map(tk => (
          <div key={tk.i} style={{ position: 'absolute', left: tk.i * PX_PER_DAY, top: 0, bottom: 0, borderLeft: '0.5px solid var(--bg-muted)' }} />
        ))}
        {/* línia AVUI */}
        {todayX != null && <div style={{ position: 'absolute', left: todayX, top: 0, bottom: 0, borderLeft: '1px solid var(--gold)', opacity: 0.6 }} />}
        {/* línia DATA OBJECTIU (vermella discontínua) */}
        {objX != null && <div style={{ position: 'absolute', left: objX, top: 0, bottom: 0, borderLeft: '1.5px dashed var(--err)' }} />}

        {/* BARRA del model (realçat vermell si en risc) */}
        <div style={{ position: 'absolute', left, width, top: (ROW_H - BAR_H) / 2, height: BAR_H,
                      boxShadow: m.en_risc ? '0 0 0 1.5px var(--err)' : 'none', borderRadius: 5 }}>
          {/* contenidor (rang sencer, color tènue) */}
          <div style={{ position: 'absolute', inset: 0, borderRadius: 5, background: color, opacity: 0.22, border: `0.5px solid ${color}` }} />
          {/* farciment % completat */}
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${m.pct}%`, borderRadius: 5, background: color, opacity: 0.85 }} />
          {/* finestres d'espera (ratllat = barra trencada) */}
          {esperes.map((w, i) => (
            <div key={i} title={t('planning.gantt.legend_wait')} style={{
              position: 'absolute', top: 0, bottom: 0, left: w.l - left, width: Math.max(2, w.r - w.l),
              background: 'repeating-linear-gradient(45deg, var(--white), var(--white) 3px, var(--gray-l) 3px, var(--gray-l) 5px)',
              border: '0.5px dashed var(--text-muted)', borderRadius: 2,
            }} />
          ))}
          {/* etiqueta fase · % */}
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-main)', whiteSpace: 'nowrap', pointerEvents: 'none' }}>
            {t(`model_sheet.dashboard.phase.${m.fase}`, { defaultValue: m.fase })} · {m.pct}%
          </div>
        </div>

        {/* FITES (marcadors) */}
        {m.fites.map((f, i) => (
          <div key={i} title={`${t(`planning.gantt.legend_${f.tipus}`)} · ${f.data}`} style={{
            position: 'absolute', left: x(f.data) + PX_PER_DAY / 2 - 7, top: 1, width: 14, height: 14,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <i className={`ti ti-${f.tipus === 'proto' ? 'package' : 'ruler-2'}`}
               style={{ fontSize: 13, color: f.tipus === 'proto' ? 'var(--taupe, #7c6f64)' : 'var(--info, #3a7ca5)' }} />
          </div>
        ))}
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
      {item('ruler-2', 'var(--info, #3a7ca5)', t('planning.gantt.legend_fitting'))}
      {item('line', 'var(--err)', t('planning.gantt.legend_objectiu'))}
      {item('line', 'var(--gold)', t('planning.gantt.legend_today'))}
    </div>
  )
}
