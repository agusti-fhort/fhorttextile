import { useState, useEffect, useMemo } from 'react'
import useAuthStore from '../../store/auth'
import { PomNamePair, POMDetailPanel } from './POMBrowser'

const API = import.meta.env.VITE_API_URL || ''

// Catalogue (PAS B5) — vista NOMÉS LECTURA del catàleg complet de POMs del tenant.
// Llegeix POMMasterViewSet (poms/), que ja exposa el bloc "com mesurar" flat (pom_global +
// fallback tenant-only). Cap edició: ni desar, ni crear, ni esborrar.

// Mapeja la fila de POMMaster (serializer flat) a la forma que espera POMDetailPanel.
function normalizeMaster(r) {
  return {
    pom_id: r.id,
    pom_code: r.pom_code || r.codi_client || '',
    name_en: r.name_en || r.nom_client || '',
    name_cat: r.name_cat || '',
    abbreviation: r.abbreviation || r.codi_client || '',
    category: r.categoria_nom || '',
    is_tenant_only: r.pom_global == null,   // els 19 importats per IA → forats visibles
    unitat: r.unitat || '',
    description_en: r.descripcio_en || '',
    description_ca: r.descripcio_ca || '',
    start_point: r.start_point || '',
    end_point: r.end_point || '',
    reference_point: r.reference_point || '',
    scope: r.scope || '',
    orientation: r.orientation || '',
    state: r.state || '',
    line: r.line || '',
    body_section: r.body_section || '',
    tol_prod_cm: r.tol_prod_cm,
    tol_samp_cm: r.tol_samp_cm,
    applies_woven: r.applies_woven,
    applies_knit: r.applies_knit,
    applies_swim: r.applies_swim,
    iso_ref: r.iso_ref || '',
    body_measure_iso_codi: r.body_measure_iso_codi || '',
    body_measure_iso_nom: r.body_measure_iso_nom || '',
  }
}

export default function POMCatalogue() {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)

  // Carrega TOTS els POMMaster actius del tenant (una sola pàgina gran). Sense mock.
  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ actiu: 'true', page_size: '1000', ordering: 'codi_client' })
    fetch(`${API}/api/v1/poms/?${params}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => setItems((d.results || d).map(normalizeMaster)))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [token])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return items
    return items.filter(p =>
      p.pom_code?.toLowerCase().includes(q) ||
      p.name_en?.toLowerCase().includes(q) ||
      p.name_cat?.toLowerCase().includes(q) ||
      p.abbreviation?.toLowerCase().includes(q) ||
      p.category?.toLowerCase().includes(q)
    )
  }, [items, search])

  // Agrupació visual per categoria (els tenant-only sense categoria → "Sense categoria").
  const groups = useMemo(() => {
    const map = new Map()
    for (const p of filtered) {
      const key = p.category || 'Sense categoria'
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(p)
    }
    return [...map.entries()].sort((a, b) => {
      if (a[0] === 'Sense categoria') return 1
      if (b[0] === 'Sense categoria') return -1
      return a[0].localeCompare(b[0])
    })
  }, [filtered])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Capçalera: cerca + recompte (lectura). */}
      <div style={{
        display: 'flex', gap: 12, padding: '12px 16px', alignItems: 'center', flexWrap: 'wrap',
        borderBottom: '0.5px solid #e4e4e2', background: 'var(--white)',
      }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          Catàleg de POMs · només consulta
        </span>
        <input
          type="text"
          placeholder="Cerca POM (codi, nom, categoria)..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            background: 'var(--white)', border: '0.5px solid #e4e4e2', borderRadius: 8,
            padding: '8px 12px', fontSize: 12, 
            outline: 'none', width: 280, marginLeft: 'auto',
          }}
        />
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{filtered.length} POMs</span>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {loading && <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Carregant catàleg...</p>}
          {!loading && filtered.length === 0 && (
            <p style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', marginTop: 40 }}>
              {items.length === 0 ? 'Catàleg buit.' : 'Cap POM coincideix amb la cerca.'}
            </p>
          )}

          {!loading && groups.map(([cat, rows]) => (
            <div key={cat} style={{ marginBottom: 18 }}>
              <h3 style={{
                fontSize: 9, fontWeight: 700, color: 'var(--gold)',
                textTransform: 'uppercase', letterSpacing: '.1em',
                margin: '0 0 8px', paddingBottom: 4, borderBottom: '0.5px solid #ece2d4',
              }}>
                {cat} <span style={{ color: '#b0b0ad', fontWeight: 500 }}>· {rows.length}</span>
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {rows.map(pom => {
                  const isSel = selected?.pom_id === pom.pom_id
                  return (
                    <div key={pom.pom_id}
                      onClick={() => setSelected(isSel ? null : pom)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: '7px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
                        border: `0.5px solid ${isSel ? 'var(--gold)' : '#e8e8e6'}`,
                        background: isSel ? '#fdf6ee' : 'var(--white)',
                      }}>
                      <span style={{ color: 'var(--gold)', fontWeight: 600, minWidth: 64 }}>
                        {pom.pom_code}
                      </span>
                      <span style={{ flex: 1, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        <PomNamePair en={pom.name_en} local={pom.name_cat} />
                      </span>
                      {pom.abbreviation && (
                        <span style={{
                          background: '#f5f0ea', color: 'var(--text-muted)', fontSize: 9, padding: '2px 6px',
                          borderRadius: 3, 
                        }}>{pom.abbreviation}</span>
                      )}
                      {pom.is_tenant_only && (
                        <span title="POM tenant-only importat — sense definició global completa"
                          style={{
                            background: '#fff3e0', color: '#b25a00', fontSize: 9, padding: '2px 6px',
                            borderRadius: 3, fontWeight: 600, letterSpacing: '.06em', border: '0.5px solid #f0c040',
                          }}>INCOMPLET</span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {selected && (
          <POMDetailPanel pom={selected} onClose={() => setSelected(null)} />
        )}
      </div>
    </div>
  )
}
