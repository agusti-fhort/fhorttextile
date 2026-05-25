import { useState, useEffect } from 'react'
import { models, alerts, poms } from '../api/endpoints'

function StatCard({ icon, label, value, sub, subColor }) {
  return (
    <div style={{
      background: 'var(--white)',
      border: '0.5px solid #e4e4e2',
      borderRadius: 12,
      padding: '1.2rem 1.4rem',
    }}>
      <div style={{
        fontSize: 11, color: 'var(--gray)',
        marginBottom: '0.5rem',
        display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <i className={`ti ${icon}`} style={{fontSize: 14, color: 'var(--gold)'}} />
        {label}
      </div>
      <div style={{fontSize: '2rem', fontWeight: 500, color: 'var(--charcoal)', lineHeight: 1, marginBottom: '0.3rem'}}>
        {value}
      </div>
      {sub && (
        <div style={{fontSize: 11, color: subColor || 'var(--gray)', fontWeight: 300}}>
          {sub}
        </div>
      )}
    </div>
  )
}

function AlertItem({ alert }) {
  const colors = {
    desviacio:      { bg: 'var(--warn-bg)', color: 'var(--warn)', icon: 'ti-ruler-2' },
    fora_rang:      { bg: 'var(--err-bg)',  color: 'var(--err)',  icon: 'ti-alert-triangle' },
    manca_mesura:   { bg: 'var(--gate-bg)', color: 'var(--gate)', icon: 'ti-question-mark' },
    conflicte:      { bg: 'var(--warn-bg)', color: 'var(--warn)', icon: 'ti-git-merge' },
  }
  const c = colors[alert.tipus] || colors.desviacio

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: '0.8rem',
      padding: '0.8rem 1.2rem',
      borderBottom: '0.5px solid var(--gray-l)',
    }}>
      <div style={{
        width: 30, height: 30, borderRadius: 7,
        background: c.bg, color: c.color,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 16, flexShrink: 0,
      }}>
        <i className={`ti ${c.icon}`} />
      </div>
      <div style={{flex: 1}}>
        <strong style={{display: 'block', fontSize: 12, fontWeight: 500, marginBottom: 2}}>
          {alert.tipus?.replace('_', ' ')} — POM {alert.pom_codi || alert.pom}
        </strong>
        <span style={{fontSize: 11, color: 'var(--gray)', fontWeight: 300}}>
          Detectat: {alert.valor_detectat} · Esperat: {alert.valor_esperat}
        </span>
      </div>
      <span style={{fontSize: 10, color: 'var(--gray)', flexShrink: 0}}>
        {alert.estat}
      </span>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState({ total: 0, en_curs: 0, tancats: 0 })
  const [alertsList, setAlertsList] = useState([])
  const [pomCount, setPomCount] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      models.list({ page_size: 1 }),
      models.list({ estat: 'EnCurs', page_size: 1 }),
      models.list({ estat: 'Tancat', page_size: 1 }),
      alerts.list({ estat: 'Pendent', page_size: 5 }),
      poms.list({ page_size: 1 }),
    ]).then(([all, enCurs, tancats, alertsRes, pomsRes]) => {
      setStats({
        total: all.data.count,
        en_curs: enCurs.data.count,
        tancats: tancats.data.count,
      })
      setAlertsList(alertsRes.data.results || [])
      setPomCount(pomsRes.data.count)
    }).finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div style={{marginBottom: '1.5rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Dashboard</h1>
        <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
          Resum general del sistema
        </p>
      </div>

      {/* Stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        <StatCard
          icon="ti-shirt"
          label="Models actius"
          value={loading ? '—' : stats.en_curs}
          sub="En curs"
          subColor="var(--warn)"
        />
        <StatCard
          icon="ti-circle-check"
          label="Models tancats"
          value={loading ? '—' : stats.tancats}
          sub="Completats"
          subColor="var(--ok)"
        />
        <StatCard
          icon="ti-ruler-2"
          label="POMs al catàleg"
          value={loading ? '—' : pomCount}
          sub="Master data"
        />
        <StatCard
          icon="ti-alert-triangle"
          label="Avisos POM"
          value={loading ? '—' : alertsList.length}
          sub="Pendents de revisió"
          subColor={alertsList.length > 0 ? 'var(--err)' : 'var(--ok)'}
        />
      </div>

      {/* Grid principal */}
      <div style={{display: 'grid', gridTemplateColumns: '1fr 340px', gap: '1.2rem'}}>

        {/* Models recents */}
        <div style={{
          background: 'var(--white)',
          border: '0.5px solid #e4e4e2',
          borderRadius: 12,
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '1rem 1.4rem',
            borderBottom: '0.5px solid #e4e4e2',
            display: 'flex', alignItems: 'center', gap: '0.8rem',
          }}>
            <i className="ti ti-shirt" style={{fontSize: 18, color: 'var(--gold)'}} />
            <span style={{fontSize: 14, fontWeight: 500}}>Models recents</span>
            <span style={{fontSize: 11, color: 'var(--gray)', marginLeft: 'auto'}}>
              {stats.total} en total
            </span>
          </div>
          {loading ? (
            <div style={{padding: '2rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
              Carregant...
            </div>
          ) : stats.total === 0 ? (
            <div style={{padding: '2rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
              Encara no hi ha models. Crea el primer amb "Nou model".
            </div>
          ) : (
            <ModelsList />
          )}
        </div>

        {/* Avisos */}
        <div style={{
          background: 'var(--white)',
          border: '0.5px solid #e4e4e2',
          borderRadius: 12,
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '1rem 1.2rem',
            borderBottom: '0.5px solid #e4e4e2',
            display: 'flex', alignItems: 'center', gap: '0.8rem',
          }}>
            <i className="ti ti-alert-triangle" style={{fontSize: 18, color: 'var(--gold)'}} />
            <span style={{fontSize: 14, fontWeight: 500}}>Avisos POM</span>
            <span style={{fontSize: 11, color: 'var(--gray)', marginLeft: 'auto'}}>
              {alertsList.length} pendents
            </span>
          </div>
          {alertsList.length === 0 ? (
            <div style={{padding: '2rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
              <i className="ti ti-circle-check" style={{fontSize: 24, color: 'var(--ok)', display: 'block', marginBottom: 8}} />
              Cap avís pendent
            </div>
          ) : (
            <div>
              {alertsList.map(a => <AlertItem key={a.id} alert={a} />)}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}

function ModelsList() {
  const [data, setData] = useState([])

  useEffect(() => {
    models.list({ page_size: 8, ordering: '-data_entrada' })
      .then(res => setData(res.data.results))
  }, [])

  const estatColor = {
    'Nou':       'var(--gray)',
    'EnCurs':    'var(--warn)',
    'EnRevisió': 'var(--gate)',
    'Tancat':    'var(--ok)',
  }

  return (
    <table style={{width: '100%', borderCollapse: 'collapse'}}>
      <thead>
        <tr>
          {['Codi', 'Prenda', 'Estat', 'Fase'].map(h => (
            <th key={h} style={{
              padding: '0.7rem 1rem',
              fontSize: 10, letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: 'var(--gray)', fontWeight: 400,
              borderBottom: '0.5px solid #e4e4e2',
              textAlign: 'left',
            }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((m, i) => (
          <tr key={m.id}
            style={{borderBottom: i < data.length-1 ? '0.5px solid var(--gray-l)' : 'none', cursor: 'pointer'}}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--gray-l)'}
            onMouseLeave={e => e.currentTarget.style.background = 'none'}
          >
            <td style={{padding: '0.7rem 1rem'}}>
              <span style={{fontSize: 11, color: 'var(--gold)', fontWeight: 500}}>{m.codi_intern}</span>
            </td>
            <td style={{padding: '0.7rem 1rem', fontSize: 12}}>{m.nom_prenda}</td>
            <td style={{padding: '0.7rem 1rem'}}>
              <span style={{
                fontSize: 11, padding: '2px 7px', borderRadius: 5,
                color: estatColor[m.estat] || 'var(--gray)',
                background: 'var(--gray-l)',
              }}>{m.estat}</span>
            </td>
            <td style={{padding: '0.7rem 1rem', fontSize: 11, color: 'var(--gate)'}}>
              {m.fase_actual || '—'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
