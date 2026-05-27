import { useState, useEffect } from 'react'
import { sizeSystems, sizeDefinitions } from '../api/endpoints'
import SizeSystemDrawer from '../components/SizeSystem/SizeSystemDrawer'

export default function SizeSystems() {
  const [systems, setSystems] = useState([])
  const [definitions, setDefinitions] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedSS, setSelectedSS] = useState(null)

  useEffect(() => {
    Promise.all([
      sizeSystems.list({ page_size: 100 }),
      sizeDefinitions.list({ page_size: 500 }),
    ]).then(([sRes, dRes]) => {
      setSystems(sRes.data.results || [])
      setDefinitions(dRes.data.results || [])
    }).finally(() => setLoading(false))
  }, [])

  const tallesPerSystem = (sysId) => definitions.filter(d => {
    const ssId = d.size_system_id || d.size_system
    return String(ssId) === String(sysId)
  })

  return (
    <div>
      <div style={{marginBottom: '1.5rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Size Systems</h1>
        <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
          {systems.length} sistemes de talles
        </p>
      </div>

      {loading ? (
        <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
          Carregant...
        </div>
      ) : systems.length === 0 ? (
        <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
          No hi ha Size Systems definits.
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
          gap: '1.2rem',
        }}>
          {systems.map(s => {
            const talles = (s.talles || s.size_definitions || tallesPerSystem(s.id))
            return (
              <div key={s.id}
                onClick={() => setSelectedSS(s)}
                style={{
                  background: 'var(--white)',
                  border: '0.5px solid #e4e4e2',
                  borderRadius: 12,
                  padding: '1.2rem 1.4rem',
                  cursor: 'pointer',
                  transition: 'border-color 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = '#c27a2a'}
                onMouseLeave={e => e.currentTarget.style.borderColor = '#e4e4e2'}
              >
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  marginBottom: 4,
                }}>
                  <i className="ti ti-arrows-maximize" style={{fontSize: 16, color: 'var(--gold)'}} />
                  <span style={{fontSize: 14, fontWeight: 500}}>{s.nom}</span>
                </div>
                <div style={{fontSize: 11, color: 'var(--gray)', fontWeight: 300, marginBottom: 12}}>
                  Codi: {s.codi || '—'} · {talles.length} talles
                </div>
                <div style={{display: 'flex', flexWrap: 'wrap', gap: 6}}>
                  {talles.length === 0 ? (
                    <span style={{fontSize: 11, color: 'var(--gray)'}}>Sense talles definides</span>
                  ) : talles.map(t => (
                    <span key={t.id || t.codi} style={{
                      fontSize: 11, padding: '4px 10px',
                      borderRadius: 6,
                      background: 'var(--gold-pale)',
                      color: 'var(--gold)',
                      fontWeight: 500,
                      fontVariantNumeric: 'tabular-nums',
                    }}>
                      {t.codi || t.nom || t.label}
                    </span>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {selectedSS && (
        <SizeSystemDrawer
          sizeSystem={selectedSS}
          onClose={() => setSelectedSS(null)}
        />
      )}
    </div>
  )
}
