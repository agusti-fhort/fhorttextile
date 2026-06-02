import { useState, useEffect, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { companyCalendar } from '../api/endpoints'

// Tram 3 — Peça 2B-cal-2 · CALENDARI propi estil agenda (fet a mà, sense llibreries).
// AQUESTA subpeça: NOMÉS la graella laboral + 4 vistes + lectura del CompanyCalendar real.
// SENSE esdeveniments (entren a 2B-cal-3, via GET calendar/events amb color per tècnic).
//
// La graella reflecteix el calendari laboral REAL (company-calendar/): trams per dia de la setmana
// (mon..sun, format {dia:[["HH:MM","HH:MM"],...]}, pausa = forat entre trams). Les cel·les NO
// laborables (pausa, fora d'horari, divendres tarda, cap de setmana, festius_extra) s'ombregen.
// LIMITACIÓ ANOTADA: company-calendar/ només exposa festius_extra, NO els festius oficials de
// Catalunya (els resol el motor al backend via workalendar). Per tant la graella NO ombreja els
// festius oficials de Catalunya — només cap de setmana + festius_extra. (No afegim workalendar al front.)
const MONO = 'IBM Plex Mono, monospace'
const DOW = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']   // alineat amb weekday() (0=dilluns)
const DAY_LABELS = ['Dl', 'Dt', 'Dc', 'Dj', 'Dv', 'Ds', 'Dg']

// ── helpers de data (tot en LOCAL del navegador) ─────────────────────────────
const cap = (s) => s ? s.charAt(0).toUpperCase() + s.slice(1) : s
const toMin = (hhmm) => { const [h, m] = hhmm.split(':').map(Number); return h * 60 + m }
const dowKey = (d) => DOW[(d.getDay() + 6) % 7]
const isoDate = (d) => {
  const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0'), dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}
const sameDay = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x }
const startOfWeek = (d) => { const x = new Date(d); x.setHours(0, 0, 0, 0); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return x }
const monthName = (d) => cap(new Intl.DateTimeFormat('ca-ES', { month: 'long' }).format(d))
const weekdayLong = (d) => cap(new Intl.DateTimeFormat('ca-ES', { weekday: 'long' }).format(d))

export default function PlanningCalendar() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [horaris, setHoraris] = useState({})
  const [festius, setFestius] = useState([])
  const [date, setDate] = useState(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d })
  const [view, setView] = useState('week')
  const [tecnic, setTecnic] = useState('')   // reservat per a 2B-cal-3 (filtre per tècnic dels events)

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
  // Una franja horària h (h:00→h+1:00) és laborable si està CONTINGUDA en algun tram del dia i no és festiu.
  const isWorkingHour = useCallback((d, h) => {
    if (isHoliday(d)) return false
    const cs = h * 60, ce = (h + 1) * 60
    return slotsFor(d).some(([a, b]) => toMin(a) <= cs && toMin(b) >= ce)
  }, [slotsFor, isHoliday])
  // Un DIA és no laborable si no té cap tram (cap de setmana) o és festiu_extra.
  const isDayOff = useCallback((d) => slotsFor(d).length === 0 || isHoliday(d), [slotsFor, isHoliday])
  // Classifica una franja NO laborable: 'pausa' (forat intern d'un dia que sí es treballa, p.ex.
  // dinar 13-14) vs 'off' (cap de setmana, divendres tarda, fora d'horari, festiu_extra).
  const offKind = useCallback((d, h) => {
    const slots = slotsFor(d)
    if (slots.length === 0 || isHoliday(d)) return 'off'
    const firstStart = Math.min(...slots.map(s => toMin(s[0])))
    const lastEnd = Math.max(...slots.map(s => toMin(s[1])))
    const cs = h * 60, ce = (h + 1) * 60
    return (cs >= firstStart && ce <= lastEnd) ? 'pausa' : 'off'   // entre trams = pausa; altrament no laborable
  }, [slotsFor, isHoliday])

  const today = useMemo(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d }, [])

  const navigate = (dir) => setDate(prev => {
    if (view === 'day') return addDays(prev, dir)
    if (view === 'week' || view === 'list') return addDays(prev, dir * 7)
    return new Date(prev.getFullYear(), prev.getMonth() + dir, 1)   // month
  })
  const goToday = () => { const d = new Date(); d.setHours(0, 0, 0, 0); setDate(d) }

  const title = useMemo(() => {
    if (view === 'day') return `${weekdayLong(date)} ${date.getDate()} de ${monthName(date)} ${date.getFullYear()}`
    if (view === 'month') return `${monthName(date)} ${date.getFullYear()}`
    // week / list → rang dilluns–diumenge
    const a = startOfWeek(date), b = addDays(a, 6)
    const sameM = a.getMonth() === b.getMonth()
    return sameM
      ? `${a.getDate()}–${b.getDate()} de ${monthName(a)} ${a.getFullYear()}`
      : `${a.getDate()} de ${monthName(a)} – ${b.getDate()} de ${monthName(b)} ${b.getFullYear()}`
  }, [view, date])

  return (
    <div style={{ minWidth: 0, maxWidth: '100%' }}>
      <style>{CSS}</style>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('planning_calendar.title')}</h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('planning_calendar.subtitle')}</p>
      </div>

      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', border: '0.5px solid var(--gray-l)', borderRadius: 8, overflow: 'hidden' }}>
          <button onClick={() => navigate(-1)} style={navBtn} title="Anterior"><i className="ti ti-chevron-left" /></button>
          <button onClick={goToday} style={{ ...navBtn, fontWeight: 600 }}>{t('planning_calendar.today')}</button>
          <button onClick={() => navigate(1)} style={navBtn} title="Següent"><i className="ti ti-chevron-right" /></button>
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

      {loading ? <Center>{t('planning_calendar.loading')}</Center>
        : error ? <Center>{t('planning_calendar.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, overflow: 'auto', background: 'var(--white)' }}>
              {view === 'list'
                ? <Center>{t('planning_calendar.empty_list')}</Center>
                : view === 'month'
                  ? <MonthGrid date={date} today={today} isDayOff={isDayOff} />
                  : <TimeGrid days={view === 'day' ? [date] : weekDays(date)} hours={hours} today={today} isWorkingHour={isWorkingHour} offKind={offKind} />}
            </div>
          )}
    </div>
  )
}

function weekDays(date) { const a = startOfWeek(date); return Array.from({ length: 7 }, (_, i) => addDays(a, i)) }

// ── Graella DIA/SETMANA: columna hores × dies ────────────────────────────────
function TimeGrid({ days, hours, today, isWorkingHour, offKind }) {
  const cols = `56px repeat(${days.length}, minmax(90px, 1fr))`
  return (
    <div className="pcal-grid" style={{ gridTemplateColumns: cols }}>
      {/* capçalera */}
      <div className="pcal-corner" />
      {days.map((d, i) => (
        <div key={i} className={`pcal-dayhead${sameDay(d, today) ? ' pcal-today' : ''}`}>
          <span className="pcal-dow">{DAY_LABELS[(d.getDay() + 6) % 7]}</span>
          <span className="pcal-num">{d.getDate()}</span>
        </div>
      ))}
      {/* files d'hores */}
      {hours.map(h => (
        <Row key={h} h={h} days={days} today={today} isWorkingHour={isWorkingHour} offKind={offKind} />
      ))}
    </div>
  )
}
function Row({ h, days, today, isWorkingHour, offKind }) {
  return (
    <>
      <div className="pcal-timecol">{String(h).padStart(2, '0')}:00</div>
      {days.map((d, i) => {
        const kind = isWorkingHour(d, h) ? '' : ` pcal-${offKind(d, h)}`   // '' | ' pcal-pausa' | ' pcal-off'
        const isToday = sameDay(d, today)
        return <div key={i} className={`pcal-cell${kind}${isToday ? ' pcal-todaycol' : ''}`} />
      })}
    </>
  )
}

// ── Graella MES: 7×6 ─────────────────────────────────────────────────────────
function MonthGrid({ date, today, isDayOff }) {
  const first = new Date(date.getFullYear(), date.getMonth(), 1)
  const start = startOfWeek(first)
  const cells = Array.from({ length: 42 }, (_, i) => addDays(start, i))
  const month = date.getMonth()
  return (
    <div className="pcal-month">
      {DAY_LABELS.map((l, i) => <div key={i} className="pcal-mhead">{l}</div>)}
      {cells.map((d, i) => {
        const out = d.getMonth() !== month
        const off = isDayOff(d)
        const isToday = sameDay(d, today)
        return (
          <div key={i} className={`pcal-mcell${off ? ' pcal-off' : ''}${out ? ' pcal-dim' : ''}${isToday ? ' pcal-today' : ''}`}>
            <span className="pcal-mnum">{d.getDate()}</span>
          </div>
        )
      })}
    </div>
  )
}

function Center({ children }) {
  return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>{children}</div>
}
const navBtn = {
  fontFamily: MONO, fontSize: 12, padding: '7px 14px', border: 'none', cursor: 'pointer',
  background: 'var(--white)', color: 'var(--text-main)',
}

// CSS propi de la graella (estil agenda, coherent amb el tema).
const CSS = `
.pcal-grid { display: grid; min-width: 640px; }
.pcal-corner, .pcal-dayhead, .pcal-timecol, .pcal-cell { border-right: 0.5px solid var(--gray-l); border-bottom: 0.5px solid var(--gray-l); }
.pcal-corner { background: var(--white); position: sticky; left: 0; z-index: 2; }
.pcal-dayhead { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; padding: 8px 4px; font-family: ${MONO}; background: var(--white); }
.pcal-dayhead .pcal-dow { font-size: 10px; text-transform: uppercase; letter-spacing: .04em; color: var(--text-muted); }
.pcal-dayhead .pcal-num { font-size: 15px; font-weight: 500; color: var(--text-main); }
.pcal-dayhead.pcal-today { background: rgba(194,122,42,0.10); }
.pcal-dayhead.pcal-today .pcal-num { color: var(--warn); font-weight: 700; }
.pcal-timecol { font-family: ${MONO}; font-size: 10px; color: var(--text-muted); padding: 4px 6px; text-align: right; background: var(--white); position: sticky; left: 0; z-index: 1; }
.pcal-cell { height: 38px; }
/* PAUSA (forat entre trams, p.ex. dinar 13-14): gris neutre molt clar, ratllat discret → "aquí es para". */
.pcal-cell.pcal-pausa { background-image: repeating-linear-gradient(45deg, transparent, transparent 5px, rgba(0,0,0,0.05) 5px, rgba(0,0,0,0.05) 10px); }
/* NO LABORABLE (cap de setmana, divendres tarda, fora d'horari, festius_extra): taronja pàl·lid,
   família del daurat de l'"avui" però molt diluït → "aquí no es treballa". */
.pcal-cell.pcal-off { background: #f7ede0; }
.pcal-cell.pcal-todaycol:not(.pcal-off):not(.pcal-pausa) { background: rgba(194,122,42,0.05); }
.pcal-month { display: grid; grid-template-columns: repeat(7, 1fr); min-width: 560px; }
.pcal-mhead { text-align: center; padding: 8px 4px; font-family: ${MONO}; font-size: 10px; text-transform: uppercase; letter-spacing: .04em; color: var(--text-muted); border-right: 0.5px solid var(--gray-l); border-bottom: 0.5px solid var(--gray-l); background: var(--white); }
.pcal-mcell { min-height: 84px; padding: 6px; border-right: 0.5px solid var(--gray-l); border-bottom: 0.5px solid var(--gray-l); background: var(--white); }
.pcal-mcell .pcal-mnum { font-family: ${MONO}; font-size: 12px; color: var(--text-main); }
.pcal-mcell.pcal-off { background: #f7ede0; }
.pcal-mcell.pcal-dim .pcal-mnum { color: var(--gray-l); }
.pcal-mcell.pcal-today { box-shadow: inset 0 0 0 2px rgba(194,122,42,0.45); }
.pcal-mcell.pcal-today .pcal-mnum { color: var(--warn); font-weight: 700; }
`
