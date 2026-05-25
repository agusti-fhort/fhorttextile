import { useState, useEffect } from 'react'
import { tasks } from '../api/endpoints'

const estatColors = {
  'Pendent':   { bg: 'var(--gray-l)',   color: 'var(--gray)',  icon: 'ti-clock' },
  'EnCurs':    { bg: 'var(--warn-bg)',  color: 'var(--warn)',  icon: 'ti-player-play' },
  'Feta':      { bg: 'var(--ok-bg)',    color: 'var(--ok)',    icon: 'ti-circle-check' },
  'Bloquejada':{ bg: 'var(--err-bg)',   color: 'var(--err)',   icon: 'ti-lock' },
}

export default function Tasques() {
  const [data, setData] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [filtre, setFiltre] = useState('')

  useEffect(() => {
    setLoading(true)
    const params = { page_size: 50 }
    if (filtre) params.estat = filtre
    tasks.list(params)
      .then(res => {
        setData(res.data.results)
        setCount(res.data.count)
      })
      .finally(() => setLoading(false))
  }, [filtre])

  const filtres = ['', 'Pendent', 'EnCurs', 'Feta', 'Bloquejada']

  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1.5rem',
      }}>
        <div>
          <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Tasques</h1>
          <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
            {count} tasques en total
          </p>
        </div>
        <div style={{display: 'flex', gap: '0.5rem'}}>
          {filtres.map(f => (
            <button
              key={f}
              onClick={() => setFiltre(f)}
              style={{
                background: filtre === f ? 'var(--charcoal)' : 'var(--white)',
                color: filtre === f ? 'var(--white)' : 'var(--gray)',
                border: '0.5px solid #e4e4e2',
                borderRadius: 8,
                padding: '6px 14px',
                fontSize: 12,
                cursor: 'pointer',
                fontFamily: 'var(--font)',
              }}
            >
              {f || 'Totes'}
            </button>
          ))}
        </div>
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
        ) : data.length === 0 ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            <i className="ti ti-checklist" style={{fontSize: 32, display: 'block', marginBottom: 12, color: 'var(--gray-l)'}} />
            No hi ha tasques amb aquest filtre.
          </div>
        ) : (
          <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <thead>
              <tr>
                {['Model', 'Tasca', 'Fase', 'Estat', 'Responsable', 'Temps', 'Gate'].map(h => (
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
              {data.map((t, i) => {
                const ec = estatColors[t.estat] || estatColors['Pendent']
                return (
                  <tr key={t.id}
                    style={{
                      borderBottom: i < data.length - 1 ? '0.5px solid var(--gray-l)' : 'none',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--gray-l)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'none'}
                  >
                    <td style={{padding: '0.75rem 1rem'}}>
                      <span style={{fontSize: 11, color: 'var(--gold)', fontWeight: 500}}>
                        {t.model_codi || t.model}
                      </span>
                    </td>
                    <td style={{padding: '0.75rem 1rem', fontSize: 13}}>
                      {t.nom_tasca || t.tasca}
                    </td>
                    <td style={{padding: '0.75rem 1rem', fontSize: 12, color: 'var(--gate)'}}>
                      {t.fase || '—'}
                    </td>
                    <td style={{padding: '0.75rem 1rem'}}>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 5,
                        fontSize: 11, padding: '3px 8px', borderRadius: 6,
                        background: ec.bg, color: ec.color,
                      }}>
                        <i className={`ti ${ec.icon}`} style={{fontSize: 12}} />
                        {t.estat}
                      </span>
                    </td>
                    <td style={{padding: '0.75rem 1rem', fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
                      {t.responsable || '—'}
                    </td>
                    <td style={{padding: '0.75rem 1rem', fontSize: 12, fontVariantNumeric: 'tabular-nums'}}>
                      {t.minuts_reals ? `${t.minuts_reals}min` : '—'}
                    </td>
                    <td style={{padding: '0.75rem 1rem'}}>
                      {t.es_gate && (
                        <span style={{
                          fontSize: 10, padding: '2px 7px', borderRadius: 4,
                          background: t.resultat_gate === 'OK' ? 'var(--ok-bg)' : 'var(--gate-bg)',
                          color: t.resultat_gate === 'OK' ? 'var(--ok)' : 'var(--gate)',
                          fontWeight: 500, letterSpacing: '0.06em',
                        }}>
                          {t.resultat_gate || 'GATE'}
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
