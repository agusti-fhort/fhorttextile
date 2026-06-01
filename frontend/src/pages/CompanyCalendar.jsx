import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { companyCalendar } from '../api/endpoints'

// Pantalla "Calendari d'empresa" (gated configure):
//   - Tram 1A.2: editor de trams horaris per dia. Format `horaris`:
//     {"mon":[["08:00","13:00"],["14:00","17:00"]], ..., "sat":[], "sun":[]} (hores HH:MM, cap UTC).
//   - Tram 1B: editor de FESTIUS EXTRA propis del tenant. Format `festius_extra`: llista de dates ISO
//     ["2026-12-24", ...] (el backend valida date.fromisoformat → NOMÉS dates, sense descripció). Són
//     festius PROPIS, a sobre dels oficials de Catalunya que el motor ja aplica via workalendar.
// El PUT de company-calendar/ és PARCIAL, però en desar enviem {horaris, festius_extra} (els dos camps)
// per evitar qualsevol regressió. Dates de calendari, no datetimes → cap conversió UTC.

const MONO = 'IBM Plex Mono, monospace'
const DOW = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

const inputS = {
  fontFamily: MONO, fontSize: 12, padding: '5px 8px',
  border: '0.5px solid var(--gray-l)', borderRadius: 6, background: 'var(--white)',
  color: 'var(--text-main)',
}

// Validació: cada tram inici<fi; trams del dia ordenats i sense solapament.
function validateHoraris(horaris, t) {
  for (const day of DOW) {
    const trams = horaris[day] || []
    const sorted = [...trams].sort((a, b) => (a[0] || '').localeCompare(b[0] || ''))
    let prevEnd = ''
    for (const [ini, fi] of sorted) {
      if (!ini || !fi) return t('companyCalendar.err_incomplete', { day: t(`companyCalendar.days.${day}`) })
      if (ini >= fi) return t('companyCalendar.err_start_end', { day: t(`companyCalendar.days.${day}`) })
      if (prevEnd && ini < prevEnd) return t('companyCalendar.err_overlap', { day: t(`companyCalendar.days.${day}`) })
      prevEnd = fi
    }
  }
  return null
}

export default function CompanyCalendar() {
  const { t } = useTranslation()
  const me = useAuthStore(s => s.user)
  const canConfigure = !!me?.capabilities?.includes('configure')

  const [horaris, setHoraris] = useState(null)
  const [festius, setFestius] = useState([])   // [{key, date:'YYYY-MM-DD'}]
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null)   // { type:'ok'|'err', text }
  const keyRef = useRef(0)
  const nextKey = () => (keyRef.current += 1)

  const load = useCallback(() => {
    setLoading(true)
    companyCalendar.get()
      .then(res => {
        const h = res.data?.horaris || {}
        // Garantir les 7 claus (dia sense trams = []).
        setHoraris(Object.fromEntries(DOW.map(d => [d, Array.isArray(h[d]) ? h[d] : []])))
        const fx = Array.isArray(res.data?.festius_extra) ? res.data.festius_extra : []
        setFestius(fx.map(date => ({ key: nextKey(), date })))
      })
      .catch(() => setFeedback({ type: 'err', text: t('companyCalendar.load_error') }))
      .finally(() => setLoading(false))
  }, [t])

  useEffect(() => { if (canConfigure) load() }, [canConfigure, load])

  // --- mutacions immutables de l'estat (horaris) ---
  const setTram = (day, idx, pos, value) => setHoraris(h => ({
    ...h, [day]: h[day].map((tr, i) => i === idx ? (pos === 0 ? [value, tr[1]] : [tr[0], value]) : tr),
  }))
  const addTram = (day) => setHoraris(h => ({ ...h, [day]: [...h[day], ['09:00', '13:00']] }))
  const removeTram = (day, idx) => setHoraris(h => ({ ...h, [day]: h[day].filter((_, i) => i !== idx) }))

  // --- mutacions de festius extra ---
  const setFestiuDate = (key, date) => setFestius(f => f.map(x => x.key === key ? { ...x, date } : x))
  const addFestiu = () => setFestius(f => [...f, { key: nextKey(), date: '' }])
  const removeFestiu = (key) => setFestius(f => f.filter(x => x.key !== key))

  const save = () => {
    const err = validateHoraris(horaris, t)
    if (err) { setFeedback({ type: 'err', text: err }); return }
    const dates = festius.map(f => f.date)
    if (dates.some(d => !d)) { setFeedback({ type: 'err', text: t('companyCalendar.err_holiday_empty') }); return }
    if (new Set(dates).size !== dates.length) { setFeedback({ type: 'err', text: t('companyCalendar.err_holiday_dup') }); return }
    const festius_extra = [...dates].sort()   // ISO → ordre ascendent
    setSaving(true)
    setFeedback(null)
    companyCalendar.update({ horaris, festius_extra })
      .then(() => setFeedback({ type: 'ok', text: t('companyCalendar.saved_ok') }))
      .catch(e => {
        // Mostrar l'error 400 del backend de forma llegible.
        const data = e?.response?.data
        const msg = typeof data === 'string' ? data
          : data?.horaris?.[0] || data?.festius_extra?.[0] || data?.detail || data?.error
          || (data ? JSON.stringify(data) : t('companyCalendar.save_error'))
        setFeedback({ type: 'err', text: msg })
      })
      .finally(() => setSaving(false))
  }

  if (me == null) {
    return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>{t('companyCalendar.loading')}</div>
  }
  if (!canConfigure) {
    return (
      <div style={{ padding: '4rem 2rem', textAlign: 'center' }}>
        <i className="ti ti-lock" style={{ fontSize: 32, color: 'var(--gray)' }} />
        <p style={{ marginTop: 12, fontSize: 13, color: 'var(--gray)' }}>{t('companyCalendar.no_access')}</p>
      </div>
    )
  }

  return (
    <div style={{ minWidth: 0, maxWidth: 720 }}>
      <div style={{ marginBottom: '1.2rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('companyCalendar.title')}</h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('companyCalendar.subtitle')}</p>
      </div>

      {feedback && (
        <div style={{
          fontSize: 12, padding: '8px 12px', borderRadius: 6, marginBottom: 12,
          background: feedback.type === 'ok' ? 'var(--ok-bg)' : 'var(--err-bg)',
          color: feedback.type === 'ok' ? 'var(--ok)' : 'var(--err)',
        }}>{feedback.text}</div>
      )}

      {loading || horaris == null ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>{t('companyCalendar.loading')}</div>
      ) : (
        <>
          <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflow: 'hidden' }}>
            {DOW.map((day, di) => (
              <div key={day} style={{
                display: 'flex', alignItems: 'flex-start', gap: 12, padding: '12px 16px',
                borderBottom: di < DOW.length - 1 ? '0.5px solid var(--gray-l)' : 'none',
              }}>
                <div style={{
                  fontFamily: MONO, fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
                  letterSpacing: '.04em', width: 92, paddingTop: 6, color: 'var(--text-muted)',
                }}>{t(`companyCalendar.days.${day}`)}</div>

                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {(horaris[day] || []).length === 0 && (
                    <span style={{ fontSize: 12, color: 'var(--gray)', fontStyle: 'italic', paddingTop: 6 }}>
                      {t('companyCalendar.no_work')}
                    </span>
                  )}
                  {(horaris[day] || []).map((tr, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <input type="time" value={tr[0] || ''} style={inputS}
                             onChange={e => setTram(day, idx, 0, e.target.value)} />
                      <span style={{ fontSize: 12, color: 'var(--gray)' }}>→</span>
                      <input type="time" value={tr[1] || ''} style={inputS}
                             onChange={e => setTram(day, idx, 1, e.target.value)} />
                      <button onClick={() => removeTram(day, idx)} title={t('companyCalendar.remove_tram')}
                              style={{
                                background: 'none', border: 'none', cursor: 'pointer', padding: 4,
                                color: 'var(--err)', display: 'flex', alignItems: 'center',
                              }}>
                        <i className="ti ti-trash" style={{ fontSize: 15 }} />
                      </button>
                    </div>
                  ))}
                  <button onClick={() => addTram(day)} style={{
                    alignSelf: 'flex-start', marginTop: 2, background: 'none',
                    border: '0.5px dashed var(--gray-l)', borderRadius: 6, cursor: 'pointer',
                    padding: '4px 10px', fontSize: 11, fontFamily: MONO, color: 'var(--text-muted)',
                    display: 'flex', alignItems: 'center', gap: 5,
                  }}>
                    <i className="ti ti-plus" style={{ fontSize: 13 }} />{t('companyCalendar.add_tram')}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* ── Festius extra (Tram 1B) ───────────────────────────────── */}
          <div style={{ marginTop: 28, marginBottom: '1rem' }}>
            <h2 style={{ fontSize: 15, fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('companyCalendar.holidays_title')}</h2>
            <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('companyCalendar.holidays_subtitle')}</p>
          </div>

          <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', padding: '14px 16px' }}>
            {festius.length === 0 && (
              <span style={{ fontSize: 12, color: 'var(--gray)', fontStyle: 'italic' }}>
                {t('companyCalendar.holidays_empty')}
              </span>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {[...festius].sort((a, b) => (a.date || '').localeCompare(b.date || '')).map(f => (
                <div key={f.key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input type="date" value={f.date || ''} style={inputS}
                         onChange={e => setFestiuDate(f.key, e.target.value)} />
                  <button onClick={() => removeFestiu(f.key)} title={t('companyCalendar.remove_holiday')}
                          style={{
                            background: 'none', border: 'none', cursor: 'pointer', padding: 4,
                            color: 'var(--err)', display: 'flex', alignItems: 'center',
                          }}>
                    <i className="ti ti-trash" style={{ fontSize: 15 }} />
                  </button>
                </div>
              ))}
            </div>
            <button onClick={addFestiu} style={{
              marginTop: festius.length ? 8 : 10, background: 'none',
              border: '0.5px dashed var(--gray-l)', borderRadius: 6, cursor: 'pointer',
              padding: '4px 10px', fontSize: 11, fontFamily: MONO, color: 'var(--text-muted)',
              display: 'flex', alignItems: 'center', gap: 5,
            }}>
              <i className="ti ti-plus" style={{ fontSize: 13 }} />{t('companyCalendar.add_holiday')}
            </button>
          </div>

          <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
            <button onClick={save} disabled={saving} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 6,
              padding: '8px 18px', fontSize: 12, fontWeight: 600,
              cursor: saving ? 'default' : 'pointer', opacity: saving ? 0.6 : 1, fontFamily: MONO,
            }}>
              <i className="ti ti-device-floppy" style={{ fontSize: 14 }} />
              {saving ? t('companyCalendar.saving') : t('companyCalendar.save')}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
