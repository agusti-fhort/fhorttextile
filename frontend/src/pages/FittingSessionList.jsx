import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fittingSessions } from '../api/endpoints'
import StatCard from '../components/ui/StatCard'
import Card from '../components/ui/Card'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'

// Backend enums (línia divisòria sagrada — valors en català, no es toquen).
const FASES = ['', 'Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']
const ESTATS = ['', 'Oberta', 'Tancada', 'Anullada']

const estatVariant = {
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

export default function FittingSessionList() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [fase, setFase] = useState('')
  const [estat, setEstat] = useState('')
  const [stats, setStats] = useState({ total: 0, Oberta: 0, Tancada: 0, Anullada: 0 })

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

  const columns = [
    { key: 'data', label: t('fitting.session.date'), render: r => (
      <span style={{color: 'var(--gray)', fontWeight: 300}}>{r.data || '—'}</span>
    )},
    { key: 'fase', label: t('fitting.session.fase'), render: r => (
      <Badge variant="gate">{r.fase_display || r.fase}</Badge>
    )},
    { key: 'estat', label: t('fitting.session.estat'), render: r => (
      <Badge variant={estatVariant[r.estat] || 'gray'}>{r.estat_display || r.estat}</Badge>
    )},
    { key: 'target', label: t('fitting.session.target'), render: r => (
      <span style={{fontSize: 11, color: 'var(--gold)', fontWeight: 500}}>
        {r.target?.label || '—'}
      </span>
    )},
    { key: 'responsable', label: t('fitting.session.responsable'), render: r => (
      <span>{r.responsable_nom || '—'}</span>
    )},
    { key: 'n_peces', label: t('fitting.session.n_peces'), align: 'right', render: r => (
      <span style={{fontVariantNumeric: 'tabular-nums'}}>{r.n_peces ?? 0}</span>
    )},
  ]

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
            {e ? t(`fitting.estats.${e}`) : t('fitting.sessions.all')}
          </button>
        ))}
      </div>

      <Card padding={0}>
        <Table
          columns={columns}
          data={data}
          loading={loading}
          empty={t('fitting.sessions.empty')}
          onRowClick={r => navigate(`/fittings/${r.id}`)}
        />
      </Card>
    </div>
  )
}
