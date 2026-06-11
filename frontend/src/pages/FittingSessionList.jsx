import { useState, useEffect, useMemo, Fragment } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fittingSessions } from '../api/endpoints'
import StatCard from '../components/ui/StatCard'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'

// Backend enums (línia divisòria sagrada — valors en català, no es toquen).
const FASES = ['', 'Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']
const ESTATS = ['', 'Oberta', 'Programada', 'Tancada', 'Anullada']

const estatVariant = {
  Programada: 'gate',   // planificada, encara no oberta (sense variant 'blue' → 'gate' distint)
  Oberta:   'warn',
  Tancada:  'ok',
  Anullada: 'gray',
}

const filterBtn = (active) => ({
  background: active ? 'var(--charcoal)' : 'var(--white)',
  color:      active ? 'var(--white)' : 'var(--gray)',
  border: '0.5px solid #e4e4e2', borderRadius: 8,
  padding: '5px 12px', fontSize: 11, cursor: 'pointer',
  fontFamily: 'var(--font)',
})

// Cercle de color d'assignació (color_avatar). Fallback --gold si null.
const ColorDot = ({ color, size = 14 }) => (
  <span style={{ display: 'inline-block', width: size, height: size, borderRadius: '50%',
    background: color || 'var(--gold)', border: '0.5px solid var(--gray-l)', flexShrink: 0 }} />
)

// Assistents → ColorDots (màx 4 + "+N"). Rep [{id, nom, color_avatar}].
const AttendeeDots = ({ attendees }) => {
  if (!attendees || !attendees.length) return <span style={{ color: 'var(--gray)' }}>—</span>
  const shown = attendees.slice(0, 4)
  const extra = attendees.length - shown.length
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
      {shown.map(a => <ColorDot key={a.id} color={a.color_avatar} />)}
      {extra > 0 && <span style={{ fontSize: 10, color: 'var(--gray)' }}>+{extra}</span>}
    </span>
  )
}

const thStyle = (align) => ({
  padding: '0.7rem 1rem', fontSize: 10, letterSpacing: '0.1em',
  textTransform: 'uppercase', color: 'var(--gray)', fontWeight: 400,
  borderBottom: '0.5px solid var(--gray-l)', textAlign: align || 'left', whiteSpace: 'nowrap',
})
const tdStyle = (align, extra) => ({
  padding: '0.75rem 1rem', fontSize: 12, textAlign: align || 'left', ...extra,
})

export default function FittingSessionList() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [fase, setFase] = useState('')
  const [estat, setEstat] = useState('')
  const [stats, setStats] = useState({ total: 0, Oberta: 0, Tancada: 0, Anullada: 0 })
  const [openGroups, setOpenGroups] = useState(() => new Set())   // UUIDs desplegats (default: tot plegat)

  useEffect(() => {
    setLoading(true)
    const params = { page_size: 100 }
    if (fase) params.fase = fase
    if (estat) params.estat = estat
    fittingSessions.list(params)
      .then(res => setData(res.data.results || []))
      .finally(() => setLoading(false))
  }, [fase, estat])

  useEffect(() => {
    Promise.all([
      fittingSessions.list({ page_size: 1 }),
      fittingSessions.list({ estat: 'Oberta', page_size: 1 }),
      fittingSessions.list({ estat: 'Tancada', page_size: 1 }),
      fittingSessions.list({ estat: 'Anullada', page_size: 1 }),
    ]).then(([a, b, c, d]) => {
      setStats({
        total: a.data.count,
        Oberta: b.data.count,
        Tancada: c.data.count,
        Anullada: d.data.count,
      })
    })
  }, [])

  // Partició: sessions amb convocatoria → grups (ordenats per data+start_time); resta → individuals.
  const { grups, individuals } = useMemo(() => {
    const conv = {}
    const ind = []
    const key = s => `${s.data || ''}${s.start_time || ''}`
    data.forEach(s => {
      if (s.convocatoria) {
        (conv[s.convocatoria] = conv[s.convocatoria] || []).push(s)
      } else {
        ind.push(s)
      }
    })
    Object.values(conv).forEach(g => g.sort((a, b) => (key(a) > key(b) ? 1 : -1)))
    const grups = Object.entries(conv)
      .map(([uuid, sessions]) => ({ uuid, sessions }))
      .sort((a, b) => (key(a.sessions[0]) > key(b.sessions[0]) ? 1 : -1))
    return { grups, individuals: ind }
  }, [data])

  const toggleGrup = (uuid) => setOpenGroups(prev => {
    const next = new Set(prev)
    next.has(uuid) ? next.delete(uuid) : next.add(uuid)
    return next
  })

  // Estat agregat d'un grup: si tots igual → aquell estat; si mixt → "En curs (X/N tancades)".
  const estatAgregat = (sessions) => {
    const estats = new Set(sessions.map(s => s.estat))
    if (estats.size === 1) {
      const e = [...estats][0]
      return { text: sessions[0].estat_display || e, variant: estatVariant[e] || 'gray' }
    }
    const tancades = sessions.filter(s => s.estat === 'Tancada').length
    return { text: `En curs (${tancades}/${sessions.length} tancades)`, variant: 'gate' }
  }

  // Unió d'assistents d'un grup (dedup per id).
  const attendeesUnio = (sessions) => {
    const m = new Map()
    sessions.forEach(s => (s.attendees_info || []).forEach(a => m.set(a.id, a)))
    return [...m.values()]
  }

  const sum = (sessions, f) => sessions.reduce((acc, s) => acc + (s[f] || 0), 0)
  const hasRows = grups.length > 0 || individuals.length > 0

  return (
    <div>
      <div style={{display: 'flex', alignItems: 'flex-start', marginBottom: '1.5rem'}}>
        <div>
          <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>{t('fitting.sessions.title')}</h1>
          <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
            {stats.total}
          </p>
        </div>
        <button onClick={() => navigate('/fittings/new')} style={{
          marginLeft: 'auto',
          background: 'var(--charcoal)', color: 'var(--white)',
          border: 'none', borderRadius: 8, padding: '8px 16px',
          fontSize: 12, cursor: 'pointer', fontFamily: 'var(--font)',
        }}>
          + {t('fitting.sessions.new')}
        </button>
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '1rem', marginBottom: '1.5rem',
      }}>
        <StatCard icon="ti-clipboard-list" label={t('fitting.sessions.title')} value={stats.total} />
        <StatCard icon="ti-folder-open"    label={t('fitting.estats.Oberta')}   value={stats.Oberta}   subColor="var(--warn)" />
        <StatCard icon="ti-circle-check"   label={t('fitting.estats.Tancada')}  value={stats.Tancada}  subColor="var(--ok)" />
        <StatCard icon="ti-ban"            label={t('fitting.estats.Anullada')} value={stats.Anullada} subColor="var(--gray)" />
      </div>

      <div style={{display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap'}}>
        <span style={{fontSize: 11, color: 'var(--gray)', alignSelf: 'center', marginRight: 4}}>
          {t('fitting.session.fase')}:
        </span>
        {FASES.map(f => (
          <button key={`f-${f}`} onClick={() => setFase(f)} style={filterBtn(fase === f)}>
            {f || t('fitting.sessions.all')}
          </button>
        ))}
        <span style={{fontSize: 11, color: 'var(--gray)', alignSelf: 'center', marginLeft: 12, marginRight: 4}}>
          {t('fitting.session.estat')}:
        </span>
        {ESTATS.map(e => (
          <button key={`e-${e}`} onClick={() => setEstat(e)} style={filterBtn(estat === e)}>
            {e ? t(`fitting.estats.${e}`, e) : t('fitting.sessions.all')}
          </button>
        ))}
      </div>

      <Card padding={0}>
        {loading ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            {t('common.loading', 'Carregant...')}
          </div>
        ) : !hasRows ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            {t('fitting.sessions.empty')}
          </div>
        ) : (
          <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <thead>
              <tr>
                <th style={thStyle()}>{t('fitting.session.date')}</th>
                <th style={thStyle()}>{t('fitting.session.target')}</th>
                <th style={thStyle()}>{t('fitting.session.fase')}</th>
                <th style={thStyle()}>{t('fitting.session.estat')}</th>
                <th style={thStyle()}>{t('fitting.session.attendees', 'Assistents')}</th>
                <th style={thStyle('right')}>{t('fitting.session.min', 'Min')}</th>
                <th style={thStyle('right')}>{t('fitting.session.n_peces')}</th>
              </tr>
            </thead>
            <tbody>
              {/* ── GRUPS (convocatòries) ── */}
              {grups.map(({ uuid, sessions }) => {
                const isOpen = openGroups.has(uuid)
                const primera = sessions[0]
                const ea = estatAgregat(sessions)
                return (
                  <Fragment key={uuid}>
                    <tr onClick={() => toggleGrup(uuid)}
                      style={{ background: 'var(--bg-muted)', cursor: 'pointer', fontWeight: 500,
                               borderBottom: '0.5px solid var(--gray-l)' }}>
                      <td style={tdStyle()}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                          <i className="ti ti-chevron-right" style={{
                            fontSize: 14, transition: 'transform 0.15s',
                            transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }} />
                          <span>{primera.data || '—'}{primera.start_time ? ` · ${primera.start_time.slice(0, 5)}` : ''}</span>
                        </span>
                      </td>
                      <td style={tdStyle()}>
                        <span style={{ fontWeight: 500 }}>
                          {t('fitting.convocatoria', 'Convocatòria')} · {sessions.length} {t('fitting.models', 'models')}
                        </span>
                      </td>
                      <td style={tdStyle()}><Badge variant="gate">{primera.fase_display || primera.fase}</Badge></td>
                      <td style={tdStyle()}><Badge variant={ea.variant}>{ea.text}</Badge></td>
                      <td style={tdStyle()}><AttendeeDots attendees={attendeesUnio(sessions)} /></td>
                      <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{sum(sessions, 'duracio_minuts')}</td>
                      <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{sum(sessions, 'n_peces')}</td>
                    </tr>
                    {isOpen && sessions.map((s, j) => (
                      <tr key={`${uuid}-${s.id}`} onClick={() => navigate(`/fittings/${s.id}`)}
                        style={{ background: 'var(--bg-card)', cursor: 'pointer', fontSize: 13,
                                 borderBottom: j < sessions.length - 1 ? '0.5px solid var(--gray-l)' : '0.5px solid var(--gray-l)' }}>
                        <td style={tdStyle(null, { paddingLeft: 24, borderLeft: '2px solid var(--gold-pale)', color: 'var(--gray)' })}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                            <i className="ti ti-corner-down-right" style={{ fontSize: 12, color: 'var(--gray)' }} />
                            {s.start_time ? s.start_time.slice(0, 5) : '—'}
                          </span>
                        </td>
                        <td style={tdStyle(null, { fontSize: 11, color: 'var(--gold)', fontWeight: 500 })}>{s.target?.label || '—'}</td>
                        <td style={tdStyle(null, { color: 'var(--gray)' })}>—</td>
                        <td style={tdStyle()}><Badge variant={estatVariant[s.estat] || 'gray'}>{s.estat_display || s.estat}</Badge></td>
                        <td style={tdStyle(null, { color: 'var(--gray)' })}>—</td>
                        <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{s.duracio_minuts || '—'}</td>
                        <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{s.n_peces ?? 0}</td>
                      </tr>
                    ))}
                  </Fragment>
                )
              })}

              {/* ── INDIVIDUALS (convocatoria=None) — format pla ── */}
              {individuals.map((r, i) => (
                <tr key={r.id} onClick={() => navigate(`/fittings/${r.id}`)}
                  style={{ cursor: 'pointer',
                           borderBottom: i < individuals.length - 1 ? '0.5px solid var(--gray-l)' : 'none' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--gray-l)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'none'}>
                  <td style={tdStyle(null, { color: 'var(--gray)', fontWeight: 300 })}>
                    {r.data || '—'}{r.start_time ? ` · ${r.start_time.slice(0, 5)}` : ''}
                  </td>
                  <td style={tdStyle(null, { fontSize: 11, color: 'var(--gold)', fontWeight: 500 })}>{r.target?.label || '—'}</td>
                  <td style={tdStyle()}><Badge variant="gate">{r.fase_display || r.fase}</Badge></td>
                  <td style={tdStyle()}><Badge variant={estatVariant[r.estat] || 'gray'}>{r.estat_display || r.estat}</Badge></td>
                  <td style={tdStyle()}><AttendeeDots attendees={r.attendees_info} /></td>
                  <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{r.duracio_minuts || '—'}</td>
                  <td style={tdStyle('right', { fontVariantNumeric: 'tabular-nums' })}>{r.n_peces ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
