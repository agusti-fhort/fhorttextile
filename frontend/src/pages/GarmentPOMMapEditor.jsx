
import { useState, useEffect } from "react"
import { useParams } from "react-router-dom"
import useAuthStore from "../store/auth"
import { HTMTooltip } from "../components/HTMTooltip"
import BackButton from "../components/BackButton"

const API = import.meta.env.VITE_API_URL || ""

export default function GarmentPOMMapEditor() {
  const { id } = useParams()
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')

  const [mapData, setMapData] = useState(null)
  const [allGarmentTypes, setAllGarmentTypes] = useState([])
  const [selGT, setSelGT] = useState(id || null)
  const [loading, setLoading] = useState(false)
  const [searchPOM, setSearchPOM] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [msg, setMsg] = useState(null)

  const headers = { Authorization: `Bearer ${token}` }

  // Carregar tots els GarmentTypes
  useEffect(() => {
    fetch(`${API}/api/v1/garment-types/full/`, { headers })
      .then(r => r.json())
      .then(d => setAllGarmentTypes(Array.isArray(d) ? d : (d.results || [])))
      .catch(() => {})
  }, [token])

  // Carregar mapa del GT seleccionat
  const loadMap = () => {
    if (!selGT) return
    setLoading(true)
    fetch(`${API}/api/v1/garment-types/${selGT}/pom-map/`, { headers })
      .then(r => r.json())
      .then(d => { setMapData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }
  useEffect(loadMap, [selGT, token])

  // Cerca de POMs
  useEffect(() => {
    if (searchPOM.length < 2) { setSearchResults([]); return }
    const t = setTimeout(() => {
      fetch(`${API}/api/v1/pom-global/cerca/?q=${encodeURIComponent(searchPOM)}`, { headers })
        .then(r => r.json())
        .then(d => setSearchResults(d.results || []))
        .catch(() => {})
    }, 300)
    return () => clearTimeout(t)
  }, [searchPOM, token])

  const addPOM = async (pomId) => {
    if (!selGT) return
    try {
      const r = await fetch(`${API}/api/v1/garment-types/${selGT}/pom-map/add/`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ pom_id: pomId, obligatori: true }),
      })
      const d = await r.json()
      if (r.ok) {
        setMsg({ type: 'ok', text: d.missatge })
        setSearchPOM('')
        setSearchResults([])
        loadMap()
      } else {
        setMsg({ type: 'error', text: d.error })
      }
    } catch (e) {
      setMsg({ type: 'error', text: String(e) })
    }
  }

  const removePOM = async (pomId) => {
    if (!selGT || !window.confirm('Eliminar aquest POM del mapa?')) return
    try {
      const r = await fetch(`${API}/api/v1/garment-types/${selGT}/pom-map/${pomId}/`, {
        method: 'DELETE', headers,
      })
      const d = await r.json()
      if (r.ok) {
        setMsg({ type: 'ok', text: d.missatge })
        loadMap()
      } else {
        setMsg({ type: 'error', text: d.error })
      }
    } catch (e) {
      setMsg({ type: 'error', text: String(e) })
    }
  }

  return (
    <div style={{ padding: '24px', maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 16 }}><BackButton /></div>

      <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, color: 'var(--text-main)', margin: '0 0 4px' }}>
        Garment POM Map
      </h1>
      <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 24 }}>
        Defineix quins POMs s'apliquen a cada tipus de prenda.
      </div>

      {msg && (
        <div style={{
          padding: '8px 12px', marginBottom: 16, borderRadius: 4, fontSize: 'var(--fs-body)',
          background: msg.type === 'ok' ? '#f0f9f0' : '#fff0f0',
          border: `1px solid ${msg.type === 'ok' ? '#c0dd97' : '#f09595'}`,
          color: msg.type === 'ok' ? '#3b6d11' : '#a32d2d',
          display: 'flex', justifyContent: 'space-between',
        }}>
          {msg.text}
          <button onClick={() => setMsg(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>×</button>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 20 }}>
        {/* Selector de GarmentType */}
        <div>
          <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 8 }}>
            Tipus de prenda
          </div>
          <div style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
            {allGarmentTypes.map(gt => (
              <button
                key={gt.id}
                onClick={() => setSelGT(String(gt.id))}
                style={{
                  padding: '7px 10px', borderRadius: 4, textAlign: 'left', cursor: 'pointer',
                  background: selGT === String(gt.id) ? '#f5e6d0' : 'var(--white)',
                  color: selGT === String(gt.id) ? 'var(--gold)' : 'var(--text-main)',
                  border: `1px solid ${selGT === String(gt.id) ? 'var(--gold)' : 'var(--border)'}`,
                  fontSize: 'var(--fs-body)',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}
              >
                <span style={{ fontWeight: selGT === String(gt.id) ? 600 : 400 }}>
                  {gt.nom_ca || gt.nom_en}
                </span>
                <span style={{
                  fontSize: 'var(--fs-caption)', padding: '1px 5px', borderRadius: 3,
                  background: gt.n_poms > 0 ? '#f0f9f0' : '#f5f0ea',
                  color: gt.n_poms > 0 ? '#3b6d11' : 'var(--text-muted)',
                }}>
                  {gt.n_poms}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Editor del mapa */}
        <div>
          {!selGT ? (
            <div style={{ padding: '40px', border: '1px dashed var(--border)', borderRadius: 8, textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
              Selecciona un tipus de prenda
            </div>
          ) : loading ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>Carregant mapa...</div>
          ) : (
            <>
              {/* Afegir POM */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 8 }}>
                  Afegir POM
                </div>
                <div style={{ position: 'relative' }}>
                  <input
                    value={searchPOM}
                    onChange={e => setSearchPOM(e.target.value)}
                    placeholder="Cerca POM per codi o nom..."
                    style={{
                      width: '100%', padding: '7px 10px',
                      border: '1px solid var(--border)', borderRadius: 4,
                      fontSize: 'var(--fs-body)', 
                      boxSizing: 'border-box',
                    }}
                  />
                  {searchResults.length > 0 && (
                    <div style={{
                      position: 'absolute', top: '100%', left: 0, right: 0,
                      background: 'var(--white)', border: '1px solid var(--border)',
                      borderTop: 'none', borderRadius: '0 0 4px 4px',
                      zIndex: 100, maxHeight: 200, overflowY: 'auto',
                    }}>
                      {searchResults.map(p => (
                        <div
                          key={p.id}
                          onClick={() => addPOM(p.id)}
                          style={{
                            padding: '7px 10px', cursor: 'pointer', fontSize: 'var(--fs-body)',
                            display: 'flex', gap: 8, alignItems: 'center',
                            borderBottom: '1px solid #f5ede0',
                          }}
                          onMouseEnter={e => e.currentTarget.style.background = '#fdf6ee'}
                          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                        >
                          <span style={{ color: 'var(--gold)', fontWeight: 600, minWidth: 60 }}>{p.codi_intern}</span>
                          <span style={{ color: 'var(--text-main)', flex: 1 }}>{p.nom_en}</span>
                          <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-label)' }}>{p.categoria_nom}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* POMs actuals */}
              {mapData && (
                <div>
                  <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 8 }}>
                    POMs del mapa — {mapData.total_poms} total
                  </div>

                  {mapData.categories?.map(cat => (
                    <div key={cat.nom} style={{ marginBottom: 16 }}>
                      <div style={{
                        fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontWeight: 600,
                        textTransform: 'uppercase', letterSpacing: '.06em',
                        padding: '4px 0', borderBottom: '1px solid var(--border)',
                        marginBottom: 6,
                      }}>
                        {cat.nom}
                      </div>
                      {cat.poms.map(p => (
                        <div key={p.pom_id} style={{
                          display: 'flex', alignItems: 'center', gap: 8,
                          padding: '5px 4px', borderBottom: '1px solid #f5ede0',
                          fontSize: 'var(--fs-body)',
                        }}>
                          <HTMTooltip pomId={p.pom_id}>
                            <span style={{ color: 'var(--gold)', fontWeight: 600, minWidth: 70 }}>
                              {p.codi_intern}
                            </span>
                          </HTMTooltip>
                          <span style={{ color: 'var(--text-main)', flex: 1 }}>{p.nom_en}</span>
                          {p.is_key && (
                            <span style={{ fontSize: 'var(--fs-caption)', padding: '1px 5px', borderRadius: 3, background: '#f5e6d0', color: 'var(--gold)', border: '1px solid #e0c8a0' }}>KEY</span>
                          )}
                          {p.obligatori && (
                            <span style={{ fontSize: 'var(--fs-caption)', padding: '1px 5px', borderRadius: 3, background: '#f0f9f0', color: '#3b6d11', border: '1px solid #c0dd97' }}>OBL</span>
                          )}
                          <button
                            onClick={() => removePOM(p.pom_id)}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#cc4444', fontSize: 'var(--fs-h3)', padding: '0 4px' }}
                            title="Eliminar del mapa"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  ))}

                  {mapData.total_poms === 0 && (
                    <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)', padding: '16px 0' }}>
                      Sense POMs al mapa. Afegeix-ne des de la cerca superior.
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
