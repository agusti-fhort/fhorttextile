import { useState, useEffect } from 'react'
import { models } from '../api/endpoints'

const estatColors = {
  'Nou':        { bg: 'var(--gray-l)',   color: 'var(--gray)'  },
  'EnCurs':     { bg: 'var(--warn-bg)',  color: 'var(--warn)'  },
  'EnRevisió':  { bg: 'var(--gate-bg)', color: 'var(--gate)'  },
  'Tancat':     { bg: 'var(--ok-bg)',    color: 'var(--ok)'    },
}

const faseIcons = {
  'Proto':    'ti-scissors',
  'Fit':      'ti-user-check',
  'SizeSet':  'ti-arrows-maximize',
  'PP':       'ti-checklist',
  'TOP':      'ti-circle-check',
}

function EstatBadge({ estat }) {
  const style = estatColors[estat] || estatColors['Nou']
  return (
    <span style={{
      ...style,
      fontSize: 11, padding: '3px 8px',
      borderRadius: 6, fontWeight: 400,
      whiteSpace: 'nowrap',
    }}>
      {estat}
    </span>
  )
}

export default function Models() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [count, setCount] = useState(0)

  useEffect(() => {
    setLoading(true)
    models.list({ search })
      .then(res => {
        setData(res.data.results)
        setCount(res.data.count)
      })
      .catch(() => setError('Error carregant models'))
      .finally(() => setLoading(false))
  }, [search])

  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1.5rem',
      }}>
        <div>
          <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Models</h1>
          <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
            {count} models en total
          </p>
        </div>
        <input
          placeholder="Cercar per codi, nom..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            background: 'var(--white)',
            border: '0.5px solid #e4e4e2',
            borderRadius: 8,
            padding: '8px 14px',
            fontSize: 12,
            fontFamily: 'var(--font)',
            width: 240,
            outline: 'none',
          }}
        />
      </div>

      <div style={{
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 12,
        overflow: 'hidden',
      }}>
        {loading ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            Carregant...
          </div>
        ) : error ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--err)', fontSize: 13}}>
            {error}
          </div>
        ) : data.length === 0 ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            No hi ha models encara.
          </div>
        ) : (
          <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <thead>
              <tr>
                {['Codi intern', 'Ref. client', 'Prenda', 'Fase', 'Estat', 'Responsable'].map(h => (
                  <th key={h} style={{
                    padding: '0.7rem 1rem',
                    fontSize: 10, letterSpacing: '0.1em',
                    textTransform: 'uppercase',
                    color: 'var(--gray)', fontWeight: 400,
                    borderBottom: '0.5px solid #e4e4e2',
                    textAlign: 'left', whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((m, i) => (
                <tr key={m.id} style={{
                  borderBottom: i < data.length - 1 ? '0.5px solid var(--gray-l)' : 'none',
                  cursor: 'pointer',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--gray-l)'}
                onMouseLeave={e => e.currentTarget.style.background = 'none'}
                >
                  <td style={{padding: '0.75rem 1rem'}}>
                    <span style={{fontSize: 11, color: 'var(--gold)', fontWeight: 500}}>
                      {m.codi_intern}
                    </span>
                  </td>
                  <td style={{padding: '0.75rem 1rem', fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
                    {m.codi_client || '—'}
                  </td>
                  <td style={{padding: '0.75rem 1rem', fontSize: 13, fontWeight: 400}}>
                    {m.nom_prenda}
                  </td>
                  <td style={{padding: '0.75rem 1rem'}}>
                    {m.fase_actual ? (
                      <span style={{display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--gate)'}}>
                        <i className={`ti ${faseIcons[m.fase_actual] || 'ti-point'}`} style={{fontSize: 14}} />
                        {m.fase_actual}
                      </span>
                    ) : <span style={{color: 'var(--gray)', fontSize: 12}}>—</span>}
                  </td>
                  <td style={{padding: '0.75rem 1rem'}}>
                    <EstatBadge estat={m.estat} />
                  </td>
                  <td style={{padding: '0.75rem 1rem', fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
                    {m.responsable || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
