import { useState, useEffect } from 'react'
import { poms, garmentGroups } from '../api/endpoints'

export default function POMs() {
  const [data, setData] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [nextPage, setNextPage] = useState(null)
  const [prevPage, setPrevPage] = useState(null)

  useEffect(() => {
    setLoading(true)
    poms.list({ search, page, page_size: 25 })
      .then(res => {
        setData(res.data.results)
        setCount(res.data.count)
        setNextPage(res.data.next)
        setPrevPage(res.data.previous)
      })
      .finally(() => setLoading(false))
  }, [search, page])

  const handleSearch = (e) => {
    setSearch(e.target.value)
    setPage(1)
  }

  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1.5rem',
      }}>
        <div>
          <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>POMs & Grading</h1>
          <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
            {count} punts de mesura al catàleg
          </p>
        </div>
        <input
          placeholder="Cercar per codi o nom..."
          value={search}
          onChange={handleSearch}
          style={{
            background: 'var(--white)',
            border: '0.5px solid #e4e4e2',
            borderRadius: 8,
            padding: '8px 14px',
            fontSize: 12,
            fontFamily: 'var(--font)',
            width: 260,
            outline: 'none',
          }}
        />
      </div>

      <div style={{
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 12,
        overflow: 'hidden',
        marginBottom: '1rem',
      }}>
        {loading ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            Carregant...
          </div>
        ) : (
          <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <thead>
              <tr>
                {['Codi', 'Nom', 'Categoria', 'Estat'].map(h => (
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
              {data.map((p, i) => (
                <tr key={p.id}
                  style={{
                    borderBottom: i < data.length - 1 ? '0.5px solid var(--gray-l)' : 'none',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--gray-l)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'none'}
                >
                  <td style={{padding: '0.75rem 1rem'}}>
                    <span style={{
                      fontSize: 12, color: 'var(--gold)',
                      fontWeight: 500, fontVariantNumeric: 'tabular-nums',
                    }}>
                      {p.codi_client}
                    </span>
                  </td>
                  <td style={{padding: '0.75rem 1rem', fontSize: 13, fontWeight: 400}}>
                    {p.nom_client}
                  </td>
                  <td style={{padding: '0.75rem 1rem', fontSize: 11, color: 'var(--gray)', fontWeight: 300}}>
                    {p.categoria || '—'}
                  </td>
                  <td style={{padding: '0.75rem 1rem'}}>
                    <span style={{
                      fontSize: 11, padding: '3px 8px', borderRadius: 6,
                      background: p.actiu ? 'var(--ok-bg)' : 'var(--gray-l)',
                      color: p.actiu ? 'var(--ok)' : 'var(--gray)',
                    }}>
                      {p.actiu ? 'Actiu' : 'Inactiu'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Paginació */}
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: 12, color: 'var(--gray)',
      }}>
        <span>
          Pàgina {page} · {count} resultats
        </span>
        <div style={{display: 'flex', gap: '0.5rem'}}>
          <button
            onClick={() => setPage(p => p - 1)}
            disabled={!prevPage}
            style={{
              background: prevPage ? 'var(--white)' : 'var(--gray-l)',
              border: '0.5px solid #e4e4e2',
              borderRadius: 8, padding: '6px 14px',
              fontSize: 12, cursor: prevPage ? 'pointer' : 'not-allowed',
              color: prevPage ? 'var(--charcoal)' : 'var(--gray)',
              fontFamily: 'var(--font)',
            }}
          >
            ← Anterior
          </button>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={!nextPage}
            style={{
              background: nextPage ? 'var(--white)' : 'var(--gray-l)',
              border: '0.5px solid #e4e4e2',
              borderRadius: 8, padding: '6px 14px',
              fontSize: 12, cursor: nextPage ? 'pointer' : 'not-allowed',
              color: nextPage ? 'var(--charcoal)' : 'var(--gray)',
              fontFamily: 'var(--font)',
            }}
          >
            Següent →
          </button>
        </div>
      </div>
    </div>
  )
}
