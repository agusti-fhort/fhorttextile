import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { sizeFittings } from '../api/endpoints'
import StatCard from '../components/ui/StatCard'
import Card from '../components/ui/Card'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'

const TIPUS = ['', 'Proto', 'Fit', 'SizeSet', 'PP', 'TOP']
const ESTATS = ['', 'Pendent', 'BaseOberta', 'TallesGenerades', 'Tancat']

const statusVariant = {
  'Pendent':         'gray',
  'BaseOberta':      'warn',
  'TallesGenerades': 'gate',
  'Tancat':          'ok',
}

export default function SizeFittingList() {
  const navigate = useNavigate()
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [tipus, setTipus] = useState('')
  const [estat, setEstat] = useState('')
  const [stats, setStats] = useState({ total: 0, Pendent: 0, BaseOberta: 0, TallesGenerades: 0, Tancat: 0 })

  useEffect(() => {
    setLoading(true)
    const params = { page_size: 100 }
    if (tipus) params.tipus = tipus
    if (estat) params.estat = estat
    sizeFittings.list(params)
      .then(res => {
        setData(res.data.results || [])
      })
      .finally(() => setLoading(false))
  }, [tipus, estat])

  useEffect(() => {
    Promise.all([
      sizeFittings.list({ page_size: 1 }),
      sizeFittings.list({ estat: 'Pendent', page_size: 1 }),
      sizeFittings.list({ estat: 'BaseOberta', page_size: 1 }),
      sizeFittings.list({ estat: 'TallesGenerades', page_size: 1 }),
      sizeFittings.list({ estat: 'Tancat', page_size: 1 }),
    ]).then(([a, b, c, d, e]) => {
      setStats({
        total: a.data.count,
        Pendent: b.data.count,
        BaseOberta: c.data.count,
        TallesGenerades: d.data.count,
        Tancat: e.data.count,
      })
    })
  }, [])

  const columns = [
    { key: 'model', label: 'Model', render: r => (
      <span style={{fontSize: 11, color: 'var(--gold)', fontWeight: 500}}>
        {r.model_codi || r.model_codi_intern || r.model}
      </span>
    )},
    { key: 'numero', label: 'Núm. SF', render: r => (
      <span style={{fontVariantNumeric: 'tabular-nums'}}>SF #{r.numero ?? '—'}</span>
    )},
    { key: 'tipus', label: 'Tipus', render: r => (
      <Badge variant="gate">{r.tipus}</Badge>
    )},
    { key: 'estat', label: 'Estat', render: r => (
      <Badge variant={statusVariant[r.estat] || 'gray'}>{r.estat}</Badge>
    )},
    { key: 'data_creacio', label: 'Data creació', render: r => (
      <span style={{color: 'var(--gray)', fontWeight: 300}}>
        {r.data_creacio || r.created_at || '—'}
      </span>
    )},
  ]

  return (
    <div>
      <div style={{marginBottom: '1.5rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Size & Fitting</h1>
        <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
          {stats.total} Size Fittings al tenant
        </p>
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '1rem', marginBottom: '1.5rem',
      }}>
        <StatCard icon="ti-ruler-2"     label="Total SF"          value={stats.total} />
        <StatCard icon="ti-clock"        label="Pendent"            value={stats.Pendent}         subColor="var(--gray)" />
        <StatCard icon="ti-folder-open"  label="Base oberta"        value={stats.BaseOberta}      subColor="var(--warn)" />
        <StatCard icon="ti-arrows-maximize" label="Talles generades" value={stats.TallesGenerades} subColor="var(--gate)" />
        <StatCard icon="ti-circle-check" label="Tancat"             value={stats.Tancat}          subColor="var(--ok)" />
      </div>

      <div style={{display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap'}}>
        <span style={{fontSize: 11, color: 'var(--gray)', alignSelf: 'center', marginRight: 4}}>Tipus:</span>
        {TIPUS.map(t => (
          <button key={`t-${t}`} onClick={() => setTipus(t)} style={{
            background: tipus === t ? 'var(--charcoal)' : 'var(--white)',
            color:      tipus === t ? 'var(--white)' : 'var(--gray)',
            border: '0.5px solid #e4e4e2', borderRadius: 8,
            padding: '5px 12px', fontSize: 11, cursor: 'pointer',
            fontFamily: 'var(--font)',
          }}>
            {t || 'Tots'}
          </button>
        ))}
        <span style={{fontSize: 11, color: 'var(--gray)', alignSelf: 'center', marginLeft: 12, marginRight: 4}}>Estat:</span>
        {ESTATS.map(e => (
          <button key={`e-${e}`} onClick={() => setEstat(e)} style={{
            background: estat === e ? 'var(--charcoal)' : 'var(--white)',
            color:      estat === e ? 'var(--white)' : 'var(--gray)',
            border: '0.5px solid #e4e4e2', borderRadius: 8,
            padding: '5px 12px', fontSize: 11, cursor: 'pointer',
            fontFamily: 'var(--font)',
          }}>
            {e || 'Tots'}
          </button>
        ))}
      </div>

      <Card padding={0}>
        <Table
          columns={columns}
          data={data}
          loading={loading}
          empty="No hi ha Size Fittings amb aquests filtres."
          onRowClick={r => navigate(`/fitting/${r.id}`)}
        />
      </Card>
    </div>
  )
}
