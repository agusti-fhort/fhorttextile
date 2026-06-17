import { useState, useEffect, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import i18n from '../i18n'
import { companyCalendar, calendar } from '../api/endpoints'
import Center from '../components/ui/Center'

// Tram 3 — Peça 2B-cal · CALENDARI propi estil agenda (fet a mà, sense llibreries).
// 2B-cal-2: graella laboral + 4 vistes + lectura del CompanyCalendar real.
// 2B-cal-3 (aquesta): pinta els ESDEVENIMENTS de GET calendar/events sobre la graella —
//   blocs amb alçada per durada, color per tècnic (color_avatar), marcador de risc (overlay),
//   clic → /models/<id>, barra de pills per tècnic (filtre client-side), vista Llista.
//
// La graella reflecteix el calendari laboral REAL (company-calendar/): trams per dia (mon..sun,
// {dia:[["HH:MM","HH:MM"],...]}, pausa = forat entre trams). Cel·les pausa (gris) / no laborable
// (taronja pàl·lid) ombrejades.
// LIMITACIÓ ANOTADA: company-calendar/ NOMÉS exposa festius_extra, NO els festius oficials de
// Catalunya (els resol el motor al backend via workalendar). Per tant la graella NO ombreja els
// festius CAT (p.ex. 24-juny Sant Joan): es veu una columna laboral buida aquell dia (el motor no
// hi posa tasques). No és un bug; no afegim workalendar al front.
// FUS: els events vénen ISO amb offset (+02:00); new Date() els situa en local (Europe/Madrid).
// NO es fa cap altra manipulació de fus (un 08:00+02:00 cau a la franja 08:00, no desplaçat).
const MONO = 'IBM Plex Mono, monospace'
// Colors FIXOS per tipus d'estadi (han de coincidir amb calendar_events_view del backend).
const COLOR_CONFECCIO = '#7c6f64'   // taupe (confecció/taller extern)
const COLOR_FITTING = '#3a7ca5'     // blau (sessió de fitting)
const WARN_YELLOW = '#d9a300'       // avís TOVA (fitting abans de la confecció) — groc, NO vermell
const DOW = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']   // alineat amb weekday() (0=dilluns)
const HOUR_PX = 60   // 1px = 1min exacte (tasca 90min = 90px). Coherent amb l'alçada de fila.

// ── helpers de data (tot en LOCAL del navegador) ─────────────────────────────
const cap = (s) => s ? s.charAt(0).toUpperCase() + s.slice(1) : s
const pad2 = (n) => String(n).padStart(2, '0')
const toMin = (hhmm) => { const [h, m] = hhmm.split(':').map(Number); return h * 60 + m }
const fmtHM = (d) => `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
const dowKey = (d) => DOW[(d.getDay() + 6) % 7]
const isoDate = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
const sameDay = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x }
const startOfDay = (d) => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x }
const startOfWeek = (d) => { const x = startOfDay(d); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return x }
const lang = () => i18n.language || 'ca'
const monthName = (d) => cap(new Intl.DateTimeFormat(lang(), { month: 'long' }).format(d))
const weekdayLong = (d) => cap(new Intl.DateTimeFormat(lang(), { weekday: 'long' }).format(d))
const weekdayShort = (d) => cap(new Intl.DateTimeFormat(lang(), { weekday: 'short' }).format(d).replace(/\.$/, ''))
// Short weekday headers Mon→Sun (2024-01-01 is a Monday), localised via i18n.language.
const monthDowLabels = () => { const mon = new Date(2024, 0, 1); return Array.from({ length: 7 }, (_, i) => weekdayShort(addDays(mon, i))) }

// Parseja 'YYYY-MM-DD' com a data LOCAL (mitjanit local), SENSE passar per new Date(iso) — que
// interpretaria el date-only com a mitjanit UTC i a Europe/Madrid el desplaçaria al dia anterior.
function parseLocalDate(s) {
  const [y, m, d] = String(s).split('-').map(Number)
  return new Date(y, m - 1, d)
}

// Enriqueix un event amb camps derivats, sense alterar l'original.
//  - all-day (confecció/fitting): _start/_end són dates LOCALS (via parseLocalDate); _allDay=true.
//    NO calcula minuts horaris → no entra mai a la graella horària (layoutDay/EventBlock).
//  - horari (tasca): camí clàssic, _sMin/_eMin = minuts des de mitjanit.
function enrich(e) {
  if (e.all_day) {
    const s = parseLocalDate(e.start), en = parseLocalDate(e.end || e.start)
    return { ...e, _start: s, _end: en, _allDay: true }
  }
  const s = new Date(e.start), en = new Date(e.end)
  let sMin = s.getHours() * 60 + s.getMinutes()
  let eMin = en.getHours() * 60 + en.getMinutes()
  if (eMin <= sMin) eMin = sMin + 15   // defensiu (no hauria de passar: events dins d'un dia)
  return { ...e, _start: s, _end: en, _sMin: sMin, _eMin: eMin, _allDay: false }
}

// Reparteix els events d'un dia en "lanes" perquè els solapaments no es tapin (width/left = 100/N%).
// Per clúster de solapament: total lanes = màx d'ocupació simultània dins el clúster.
function layoutDay(evs) {
  const sorted = [...evs].sort((a, b) => a._sMin - b._sMin || a._eMin - b._eMin)
  const out = []
  let cluster = [], lanes = [], clusterEnd = -1
  const flush = () => { const cols = lanes.length; cluster.forEach(c => { c.cols = cols }); out.push(...cluster); cluster = []; lanes = []; clusterEnd = -1 }
  for (const e of sorted) {
    if (clusterEnd !== -1 && e._sMin >= clusterEnd) flush()
    let lane = lanes.findIndex(end => end <= e._sMin)
    if (lane === -1) { lane = lanes.length; lanes.push(e._eMin) } else lanes[lane] = e._eMin
    cluster.push({ ev: e, lane })
    clusterEnd = Math.max(clusterEnd, e._eMin)
  }
  flush()
  return out
}

export default function PlanningCalendar() {
  const { t } = useTranslation()
  const navigateRouter = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [horaris, setHoraris] = useState({})
  const [festius, setFestius] = useState([])
  const [events, setEvents] = useState([])
  const [date, setDate] = useState(() => startOfDay(new Date()))
  const [view, setView] = useState('week')
  const [tecnic, setTecnic] = useState('')   // '' = tots; filtre CLIENT-SIDE per tecnic_id

  // Calendari laboral: càrrega ÚNICA (no depèn de la data).
  useEffect(() => {
    let alive = true
    companyCalendar.get()
      .then(res => {
        if (!alive) return
        const h = res.data?.horaris || {}
        setHoraris(Object.fromEntries(DOW.map(d => [d, Array.isArray(h[d]) ? h[d] : []])))
        setFestius(Array.isArray(res.data?.festius_extra) ? res.data.festius_extra : [])
      })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  // Rang [start,end] (ISO) segons la vista — per acotar la consulta d'events (com currentRange).
  const range = useMemo(() => {
    if (view === 'day') return [isoDate(date), isoDate(date)]
    if (view === 'month') { const s = startOfWeek(new Date(date.getFullYear(), date.getMonth(), 1)); return [isoDate(s), isoDate(addDays(s, 41))] }
    const s = startOfWeek(date); return [isoDate(s), isoDate(addDays(s, 6))]   // week / list
  }, [view, date])

  // Esdeveniments: es recarreguen quan canvia la data o la vista (rang).
  useEffect(() => {
    let alive = true
    calendar.events({ start: range[0], end: range[1] })
      .then(res => { if (alive) setEvents((res.data?.events ?? []).map(enrich)) })
      .catch(() => { if (alive) setEvents([]) })
    return () => { alive = false }
  }, [range])

  // Rang horari de files derivat dels trams reals (min inici → max fi). Fallback 8–17.
  const [minHour, maxHour] = useMemo(() => {
    let lo = Infinity, hi = -Infinity
    for (const d of DOW) for (const [a, b] of (horaris[d] || [])) { lo = Math.min(lo, toMin(a)); hi = Math.max(hi, toMin(b)) }
    if (!isFinite(lo)) return [8, 17]
    return [Math.floor(lo / 60), Math.ceil(hi / 60)]
  }, [horaris])
  const hours = useMemo(() => Array.from({ length: Math.max(0, maxHour - minHour) }, (_, i) => minHour + i), [minHour, maxHour])

  const slotsFor = useCallback((d) => horaris[dowKey(d)] || [], [horaris])
  const isHoliday = useCallback((d) => festius.includes(isoDate(d)), [festius])
  const isWorkingHour = useCallback((d, h) => {
    if (isHoliday(d)) return false
    const cs = h * 60, ce = (h + 1) * 60
    return slotsFor(d).some(([a, b]) => toMin(a) <= cs && toMin(b) >= ce)
  }, [slotsFor, isHoliday])
  const isDayOff = useCallback((d) => slotsFor(d).length === 0 || isHoliday(d), [slotsFor, isHoliday])
  const offKind = useCallback((d, h) => {
    const slots = slotsFor(d)
    if (slots.length === 0 || isHoliday(d)) return 'off'
    const firstStart = Math.min(...slots.map(s => toMin(s[0])))
    const lastEnd = Math.max(...slots.map(s => toMin(s[1])))
    const cs = h * 60, ce = (h + 1) * 60
    return (cs >= firstStart && ce <= lastEnd) ? 'pausa' : 'off'
  }, [slotsFor, isHoliday])

  const today = useMemo(() => startOfDay(new Date()), [])

  // Filtre client-side per tècnic. Els estadis SENSE tècnic (confecció/fitting, tecnic_id null)
  // queden SEMPRE visibles encara que es filtri per un tècnic (no s'amaguen).
  const shown = useMemo(() => tecnic === '' ? events : events.filter(e => e.tecnic_id === tecnic || e.tecnic_id == null), [events, tecnic])
  const techs = useMemo(() => {
    const m = new Map()
    // EXCLOU tecnic_id null (confecció/fitting) → no genera pill brossa amb nom undefined.
    for (const e of events) if (e.tecnic_id != null && !m.has(e.tecnic_id)) m.set(e.tecnic_id, { id: e.tecnic_id, nom: e.tecnic_nom, color: e.color })
    return [...m.values()].sort((a, b) => (a.nom || '').localeCompare(b.nom || ''))
  }, [events])
  // Rang de dies inclusiu (per als all-day, que poden travessar N dies): _start ≤ d ≤ _end.
  const inRange = useCallback((e, d) => {
    const ds = startOfDay(d).getTime()
    return startOfDay(e._start).getTime() <= ds && ds <= startOfDay(e._end).getTime()
  }, [])
  // Horaris (tasca) per dia exacte; all-day per RANG. Mes = unió de tots dos.
  const timedByDay = useCallback((d) => shown.filter(e => !e._allDay && sameDay(e._start, d)), [shown])
  const allDayByDay = useCallback((d) => shown.filter(e => e._allDay && inRange(e, d)), [shown, inRange])
  const monthByDay = useCallback((d) => shown.filter(e => e._allDay ? inRange(e, d) : sameDay(e._start, d)), [shown, inRange])

  const openEvent = useCallback((ev) => { if (ev?.link) navigateRouter(ev.link) }, [navigateRouter])
  const openDay = useCallback((d) => { setDate(startOfDay(d)); setView('day') }, [])

  const navigate = (dir) => setDate(prev => {
    if (view === 'day') return addDays(prev, dir)
    if (view === 'week' || view === 'list') return addDays(prev, dir * 7)
    return new Date(prev.getFullYear(), prev.getMonth() + dir, 1)
  })
  const goToday = () => setDate(startOfDay(new Date()))

  const title = useMemo(() => {
    if (view === 'day') return t('planning_calendar.date_day', { weekday: weekdayLong(date), day: date.getDate(), month: monthName(date), year: date.getFullYear() })
    if (view === 'month') return `${monthName(date)} ${date.getFullYear()}`
    const a = startOfWeek(date), b = addDays(a, 6)
    return a.getMonth() === b.getMonth()
      ? t('planning_calendar.date_range_same', { d1: a.getDate(), d2: b.getDate(), month: monthName(a), year: a.getFullYear() })
      : t('planning_calendar.date_range', { d1: a.getDate(), m1: monthName(a), d2: b.getDate(), m2: monthName(b), year: b.getFullYear() })
  }, [view, date, t, i18n.language])

  return (
    <div style={{ minWidth: 0, maxWidth: '100%' }}>
      <style>{CSS}</style>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('planning_calendar.title')}</h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('planning_calendar.subtitle')}</p>
      </div>

      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', border: '0.5px solid var(--gray-l)', borderRadius: 8, overflow: 'hidden' }}>
          <button onClick={() => navigate(-1)} style={navBtn} title={t('app.previous')}><i className="ti ti-chevron-left" /></button>
          <button onClick={goToday} style={{ ...navBtn, fontWeight: 600 }}>{t('planning_calendar.today')}</button>
          <button onClick={() => navigate(1)} style={navBtn} title={t('app.next')}><i className="ti ti-chevron-right" /></button>
        </div>
        <span style={{ fontFamily: MONO, fontSize: 14, fontWeight: 500, minWidth: 200 }}>{title}</span>
        <div style={{ display: 'flex', border: '0.5px solid var(--gray-l)', borderRadius: 8, overflow: 'hidden', marginLeft: 'auto' }}>
          {[['day', 'view_day'], ['week', 'view_week'], ['month', 'view_month'], ['list', 'view_list']].map(([v, key]) => (
            <button key={v} onClick={() => setView(v)} style={{
              ...navBtn, fontWeight: view === v ? 600 : 400,
              background: view === v ? 'var(--warn-bg)' : 'var(--white)', color: view === v ? 'var(--warn)' : 'var(--gray)',
            }}>{t(`planning_calendar.${key}`)}</button>
          ))}
        </div>
      </div>

      {/* Pills de filtre per tècnic (client-side) */}
      {techs.length > 0 && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
          <Pill active={tecnic === ''} onClick={() => setTecnic('')} label={t('planning_calendar.all')} />
          {techs.map(tc => (
            <Pill key={tc.id} active={tecnic === tc.id} onClick={() => setTecnic(tc.id)} label={tc.nom} color={tc.color} />
          ))}
        </div>
      )}

      {/* Llegenda dels estadis sense tècnic (color per tipus) */}
      <div style={{ display: 'flex', gap: 14, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', fontFamily: MONO, fontSize: 11, color: 'var(--gray)' }}>
        <LegendDot color={COLOR_CONFECCIO} label={t('planning_calendar.type_confeccio')} />
        <LegendDot color={COLOR_FITTING} label={t('planning_calendar.type_fitting')} />
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <i className="ti ti-alert-triangle" style={{ color: WARN_YELLOW, fontSize: 13 }} />
          {t('planning_calendar.warn_before_production')}
        </span>
      </div>

      {loading ? <Center>{t('planning_calendar.loading')}</Center>
        : error ? <Center>{t('planning_calendar.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, overflow: 'auto', background: 'var(--white)', maxHeight: 'calc(100vh - 230px)' }}>
              {view === 'list'
                ? <ListView events={shown} onOpen={openEvent} t={t} />
                : view === 'month'
                  ? <MonthGrid date={date} today={today} isDayOff={isDayOff} eventsByDay={monthByDay} onOpen={openEvent} onOpenDay={openDay} t={t} />
                  : <TimeGrid days={view === 'day' ? [date] : weekDays(date)} hours={hours} minHour={minHour}
                              today={today} isWorkingHour={isWorkingHour} offKind={offKind}
                              timedByDay={timedByDay} allDayByDay={allDayByDay} onOpen={openEvent} t={t} />}
            </div>
          )}
    </div>
  )
}

function weekDays(date) { const a = startOfWeek(date); return Array.from({ length: 7 }, (_, i) => addDays(a, i)) }

// ── Graella DIA/SETMANA: columnes-dia relatives (events absoluts per durada) ──
//  + FRANJA ALL-DAY a dalt (confecció/fitting): estadis sense hora / de dies, fora de la graella horària.
function TimeGrid({ days, hours, minHour, today, isWorkingHour, offKind, timedByDay, allDayByDay, onOpen, t }) {
  const bodyH = hours.length * HOUR_PX
  const hasAllDay = days.some(d => allDayByDay(d).length > 0)
  return (
    <div className="pcal-tg">
      <div className="pcal-tg-head">
        <div className="pcal-corner" />
        {days.map((d, i) => (
          <div key={i} className={`pcal-dayhead${sameDay(d, today) ? ' pcal-today' : ''}`}>
            <span className="pcal-dow">{weekdayShort(d)}</span>
            <span className="pcal-num">{d.getDate()}</span>
          </div>
        ))}
      </div>
      {hasAllDay && (
        <div className="pcal-tg-allday">
          <div className="pcal-corner pcal-allday-corner">{t('planning_calendar.all_day')}</div>
          {days.map((d, i) => (
            <div key={i} className={`pcal-allday-col${sameDay(d, today) ? ' pcal-today' : ''}`}>
              {allDayByDay(d).map(ev => <AllDayChip key={ev.id} ev={ev} onOpen={onOpen} t={t} />)}
            </div>
          ))}
        </div>
      )}
      <div className="pcal-tg-body">
        <div className="pcal-gutter">
          {hours.map(h => <div key={h} className="pcal-timecol" style={{ height: HOUR_PX }}>{pad2(h)}:00</div>)}
        </div>
        {days.map((d, i) => {
          const placed = layoutDay(timedByDay(d))
          const isToday = sameDay(d, today)
          return (
            <div key={i} className="pcal-daycol" style={{ height: bodyH }}>
              {/* fons d'hora (ombrejat pausa/off/avui reaprofitant la lògica laboral) */}
              {hours.map(h => {
                const kind = isWorkingHour(d, h) ? '' : ` pcal-${offKind(d, h)}`
                return <div key={h} className={`pcal-hcell${kind}${isToday ? ' pcal-todaycol' : ''}`} style={{ height: HOUR_PX }} />
              })}
              {/* events absoluts */}
              {placed.map(({ ev, lane, cols }) => (
                <EventBlock key={ev.id} ev={ev} lane={lane} cols={cols} minHour={minHour} onOpen={onOpen} />
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function EventBlock({ ev, lane, cols, minHour, onOpen }) {
  // Bloc CONTINU per durada: top/height proporcionals (1px=1min). SIMPLIFICACIÓ de presentació —
  // un event que travessa la pausa de dinar o diversos trams es dibuixa com un sol rectangle
  // (visualment cobreix la cel·la de pausa). El MOTOR sí respecta la pausa al càlcul; això és només
  // la pintura. NO és deute pendent.
  const top = (ev._sMin - minHour * 60) * (HOUR_PX / 60)
  const height = Math.max((ev._eMin - ev._sMin) * (HOUR_PX / 60) - 2, 16)
  const w = 100 / cols, left = lane * w
  return (
    <div className="pcal-ev" title={`${fmtHM(ev._start)}–${fmtHM(ev._end)} · ${ev.titol}${ev.en_risc ? ' (en risc)' : ''}`}
      onClick={() => onOpen(ev)}
      style={{
        top, height, left: `calc(${left}% + 1px)`, width: `calc(${w}% - 2px)`,
        background: ev.color + '22', borderLeft: `3px solid ${ev.color}`, color: ev.color,
        boxShadow: ev.en_risc ? 'inset 0 0 0 1.5px var(--err, #e5484d)' : 'none',
      }}>
      {ev.en_risc && <span className="pcal-ev-dot" />}
      <span className="pcal-ev-time">{fmtHM(ev._start)}</span>
      <span className="pcal-ev-title">{ev.titol}</span>
    </div>
  )
}

// Chip d'estadi all-day (franja superior de setmana/dia). Color de tipus; avís TOVA = icona groga.
function AllDayChip({ ev, onOpen, t }) {
  const avis = ev.meta?.avis_abans_confeccio
  return (
    <div className="pcal-adchip" onClick={() => onOpen(ev)}
      title={`${ev.titol}${avis ? ' · ' + t('planning_calendar.warn_before_production') : ''}`}
      style={{ background: ev.color + '22', borderLeft: `3px solid ${ev.color}`, color: ev.color }}>
      {avis && <i className="ti ti-alert-triangle pcal-adchip-warn" style={{ color: WARN_YELLOW }} />}
      <span className="pcal-adchip-txt">{ev.titol}</span>
    </div>
  )
}

function LegendDot({ color, label }) {
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
      <span style={{ width: 9, height: 9, borderRadius: 2, background: color, flex: 'none' }} />
      {label}
    </span>
  )
}

// ── Graella MES: 7×6 amb fins a 3 events/dia + "+N" ──────────────────────────
function MonthGrid({ date, today, isDayOff, eventsByDay, onOpen, onOpenDay, t }) {
  const first = new Date(date.getFullYear(), date.getMonth(), 1)
  const start = startOfWeek(first)
  const cells = Array.from({ length: 42 }, (_, i) => addDays(start, i))
  const month = date.getMonth()
  // Ordre: all-day primer (sense hora), després horaris per minut d'inici.
  const sortKey = (e) => e._allDay ? -1 : e._sMin
  return (
    <div className="pcal-month">
      {monthDowLabels().map((l, i) => <div key={i} className="pcal-mhead">{l}</div>)}
      {cells.map((d, i) => {
        const out = d.getMonth() !== month
        const off = isDayOff(d)
        const isToday = sameDay(d, today)
        const evs = eventsByDay(d).sort((a, b) => sortKey(a) - sortKey(b))
        return (
          <div key={i} className={`pcal-mcell${off ? ' pcal-off' : ''}${out ? ' pcal-dim' : ''}${isToday ? ' pcal-today' : ''}`}
            onClick={() => onOpenDay(d)} title={t('planning_calendar.open_day')}>
            <span className="pcal-mnum">{d.getDate()}</span>
            <div className="pcal-mevs">
              {evs.slice(0, 3).map(ev => {
                const avis = ev.meta?.avis_abans_confeccio
                return (
                  <div key={ev.id} className="pcal-mev" style={{ color: ev.color }}
                    onClick={(e) => { e.stopPropagation(); onOpen(ev) }}
                    title={`${ev.titol}${avis ? ' · ' + t('planning_calendar.warn_before_production') : ''}`}>
                    <span className="pcal-mev-dot" style={{ background: ev.color }} />
                    {ev.en_risc && <span className="pcal-mev-risc" />}
                    {avis && <i className="ti ti-alert-triangle pcal-mev-warn" style={{ color: WARN_YELLOW }} />}
                    <span className="pcal-mev-txt">{ev._allDay ? ev.titol : `${fmtHM(ev._start)} ${ev.titol}`}</span>
                  </div>
                )
              })}
              {evs.length > 3 && <div className="pcal-more">+{evs.length - 3}</div>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Vista LLISTA: agrupada per dia ───────────────────────────────────────────
function ListView({ events, onOpen, t }) {
  if (!events.length) return <Center>{t('planning_calendar.empty_list')}</Center>
  const sorted = [...events].sort((a, b) => a._start - b._start)
  const groups = []
  let cur = null
  for (const ev of sorted) {
    const key = isoDate(ev._start)
    if (!cur || cur.key !== key) { cur = { key, date: ev._start, items: [] }; groups.push(cur) }
    cur.items.push(ev)
  }
  return (
    <div className="pcal-list">
      {groups.map(g => (
        <div key={g.key}>
          <div className="pcal-list-day">{t('planning_calendar.date_day', { weekday: weekdayLong(g.date), day: g.date.getDate(), month: monthName(g.date), year: g.date.getFullYear() })}</div>
          {g.items.map(ev => (
            <div key={ev.id} className="pcal-list-item" onClick={() => onOpen(ev)}>
              <span className="pcal-list-time">{ev._allDay ? t('planning_calendar.all_day') : `${fmtHM(ev._start)}–${fmtHM(ev._end)}`}</span>
              <span className="pcal-list-bar" style={{ background: ev.color }} />
              <span className="pcal-list-title">{ev.titol}</span>
              <span className="pcal-list-tech">{ev.tecnic_nom}</span>
              {ev.en_risc && <span className="pcal-badge-risc">{t('planning_calendar.at_risk')}</span>}
              {ev.meta?.avis_abans_confeccio && (
                <span className="pcal-badge-warn" title={t('planning_calendar.warn_before_production')}>
                  <i className="ti ti-alert-triangle" /> {t('planning_calendar.warn_short')}
                </span>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

function Pill({ active, onClick, label, color }) {
  return (
    <button onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 6, fontFamily: MONO, fontSize: 11, cursor: 'pointer',
      padding: '5px 12px', borderRadius: 999, border: `0.5px solid ${active ? 'var(--warn)' : 'var(--gray-l)'}`,
      background: active ? 'var(--warn-bg)' : 'var(--white)', color: active ? 'var(--warn)' : 'var(--text-main)',
      fontWeight: active ? 600 : 400,
    }}>
      {color && <span style={{ width: 9, height: 9, borderRadius: '50%', background: color, flex: 'none' }} />}
      {label}
    </button>
  )
}

const navBtn = {
  fontFamily: MONO, fontSize: 12, padding: '7px 14px', border: 'none', cursor: 'pointer',
  background: 'var(--white)', color: 'var(--text-main)',
}

// CSS propi de la graella (estil agenda, coherent amb el tema).
const CSS = `
.pcal-tg { min-width: 640px; }
.pcal-tg-head { display: flex; position: sticky; top: 0; z-index: 3; background: var(--white); }
.pcal-corner { width: 56px; flex: none; border-right: 0.5px solid var(--gray-l); border-bottom: 0.5px solid var(--gray-l); }
.pcal-dayhead { flex: 1; min-width: 90px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; padding: 8px 4px; font-family: ${MONO}; background: var(--white); border-right: 0.5px solid var(--gray-l); border-bottom: 0.5px solid var(--gray-l); }
.pcal-dayhead .pcal-dow { font-size: 10px; text-transform: uppercase; letter-spacing: .04em; color: var(--text-muted); }
.pcal-dayhead .pcal-num { font-size: 15px; font-weight: 500; color: var(--text-main); }
.pcal-dayhead.pcal-today { background: rgba(194,122,42,0.10); }
.pcal-dayhead.pcal-today .pcal-num { color: var(--warn); font-weight: 700; }
.pcal-tg-body { display: flex; }
.pcal-gutter { width: 56px; flex: none; }
.pcal-timecol { box-sizing: border-box; font-family: ${MONO}; font-size: 10px; color: var(--text-muted); padding: 2px 6px 0 0; text-align: right; border-right: 0.5px solid var(--gray-l); border-bottom: 0.5px solid var(--gray-l); }
.pcal-daycol { flex: 1; min-width: 90px; position: relative; }
.pcal-hcell { box-sizing: border-box; border-right: 0.5px solid var(--gray-l); border-bottom: 0.5px solid var(--gray-l); }
/* PAUSA (forat entre trams, p.ex. dinar 13-14): gris neutre, ratllat discret → "aquí es para". */
.pcal-hcell.pcal-pausa { background-image: repeating-linear-gradient(45deg, transparent, transparent 5px, rgba(0,0,0,0.05) 5px, rgba(0,0,0,0.05) 10px); }
/* NO LABORABLE (cap de setmana, divendres tarda, fora d'horari, festius_extra): taronja pàl·lid. */
.pcal-hcell.pcal-off { background: #f7ede0; }
.pcal-hcell.pcal-todaycol:not(.pcal-off):not(.pcal-pausa) { background: rgba(194,122,42,0.05); }
/* Event (bloc absolut per durada). */
.pcal-ev { position: absolute; box-sizing: border-box; overflow: hidden; border-radius: 4px; padding: 2px 5px; font-family: ${MONO}; font-size: 10px; line-height: 1.25; cursor: pointer; z-index: 1; }
.pcal-ev:hover { filter: brightness(0.97); z-index: 2; }
.pcal-ev-time { font-weight: 700; }
.pcal-ev-title { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pcal-ev-dot { position: absolute; top: 3px; right: 3px; width: 7px; height: 7px; border-radius: 50%; background: var(--err, #e5484d); }
/* FRANJA ALL-DAY (confecció/fitting) — sobre la graella horària, alineada amb les columnes-dia. */
.pcal-tg-allday { display: flex; border-bottom: 0.5px solid var(--gray-l); background: var(--white); }
.pcal-allday-corner { display: flex; align-items: center; justify-content: flex-end; padding: 2px 6px 0 0; font-family: ${MONO}; font-size: 9px; text-transform: uppercase; letter-spacing: .03em; color: var(--text-muted); }
.pcal-allday-col { flex: 1; min-width: 90px; display: flex; flex-direction: column; gap: 2px; padding: 3px; border-right: 0.5px solid var(--gray-l); }
.pcal-allday-col.pcal-today { background: rgba(194,122,42,0.06); }
.pcal-adchip { display: flex; align-items: center; gap: 4px; box-sizing: border-box; border-radius: 4px; padding: 2px 5px; font-family: ${MONO}; font-size: 10px; line-height: 1.25; cursor: pointer; overflow: hidden; }
.pcal-adchip:hover { filter: brightness(0.97); }
.pcal-adchip-txt { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pcal-adchip-warn { font-size: 12px; flex: none; }
.pcal-month { display: grid; grid-template-columns: repeat(7, 1fr); min-width: 560px; }
.pcal-mhead { text-align: center; padding: 8px 4px; font-family: ${MONO}; font-size: 10px; text-transform: uppercase; letter-spacing: .04em; color: var(--text-muted); border-right: 0.5px solid var(--gray-l); border-bottom: 0.5px solid var(--gray-l); background: var(--white); }
.pcal-mcell { min-height: 96px; padding: 6px; border-right: 0.5px solid var(--gray-l); border-bottom: 0.5px solid var(--gray-l); background: var(--white); cursor: pointer; }
.pcal-mcell .pcal-mnum { font-family: ${MONO}; font-size: 12px; color: var(--text-main); }
.pcal-mcell.pcal-off { background: #f7ede0; }
.pcal-mcell.pcal-dim .pcal-mnum { color: var(--gray-l); }
.pcal-mcell.pcal-today { box-shadow: inset 0 0 0 2px rgba(194,122,42,0.45); }
.pcal-mcell.pcal-today .pcal-mnum { color: var(--warn); font-weight: 700; }
.pcal-mevs { display: flex; flex-direction: column; gap: 2px; margin-top: 4px; }
.pcal-mev { display: flex; align-items: center; gap: 4px; font-family: ${MONO}; font-size: 9.5px; white-space: nowrap; overflow: hidden; }
.pcal-mev-dot { width: 6px; height: 6px; border-radius: 50%; flex: none; }
.pcal-mev-risc { width: 6px; height: 6px; border-radius: 50%; background: var(--err, #e5484d); flex: none; }
.pcal-mev-warn { font-size: 11px; flex: none; }
.pcal-mev-txt { overflow: hidden; text-overflow: ellipsis; }
.pcal-more { font-family: ${MONO}; font-size: 9.5px; color: var(--text-muted); }
.pcal-list { padding: 4px 0; }
.pcal-list-day { font-family: ${MONO}; font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .03em; padding: 12px 16px 6px; }
.pcal-list-item { display: flex; align-items: center; gap: 10px; padding: 8px 16px; border-top: 0.5px solid var(--gray-l); cursor: pointer; font-size: 12px; }
.pcal-list-item:hover { background: rgba(0,0,0,0.02); }
.pcal-list-time { font-family: ${MONO}; font-size: 11px; color: var(--text-muted); min-width: 96px; }
.pcal-list-bar { width: 4px; height: 18px; border-radius: 2px; flex: none; }
.pcal-list-title { font-family: ${MONO}; font-weight: 500; }
.pcal-list-tech { color: var(--gray); margin-left: auto; }
.pcal-badge-risc { font-family: ${MONO}; font-size: 10px; font-weight: 600; color: var(--err, #e5484d); border: 0.5px solid var(--err, #e5484d); border-radius: 999px; padding: 1px 8px; }
.pcal-badge-warn { display: inline-flex; align-items: center; gap: 4px; font-family: ${MONO}; font-size: 10px; font-weight: 600; color: ${WARN_YELLOW}; border: 0.5px solid ${WARN_YELLOW}; border-radius: 999px; padding: 1px 8px; }
`
