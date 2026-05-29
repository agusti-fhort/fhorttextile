
import { useState, useEffect, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import useAuthStore from "../store/auth"
import { EstatBadge } from "../components/EstatBadge"

const API = import.meta.env.VITE_API_URL || ""

const FASES = ["Nou", "Disseny", "Tècnic", "Prototip", "Mostres", "Preproducció", "Producció", "Tancat"]
const TEMPORADES = ["SS", "FW", "RE", "PRE"]
const anyActual = new Date().getFullYear()
const ANYS = [anyActual, anyActual + 1, anyActual + 2, anyActual + 3]

export default function Models() {
  const navigate = useNavigate()
  const token = useAuthStore.getState().token || localStorage.getItem('access_token')

  // Guard auth: redirigeix si no hi ha token (cap fetch s'executarà sense auth)
  useEffect(() => { if (!token) navigate("/login") }, [token, navigate])
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [cerca, setCerca] = useState("")
  const [filtreFase, setFiltreFase] = useState("")
  const [filtreEstat, setFiltreEstat] = useState("")
  const [filtreAny, setFiltreAny] = useState("")
  const [filtreTemporada, setFiltreTemporada] = useState("")
  const [total, setTotal] = useState(0)

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams()
    if (cerca) params.set("search", cerca)
    if (filtreFase) params.set("fase_actual", filtreFase)
    if (filtreEstat) params.set("estat", filtreEstat)
    params.set("ordering", "-data_entrada")
    params.set("limit", "50")

    fetch(`${API}/api/v1/models/?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => {
        const results = Array.isArray(d) ? d : (d.results || [])
        setModels(results)
        setTotal(d.count || results.length)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [token, cerca, filtreFase, filtreEstat])

  // Filtrat client-side (Any / Temporada — el backend no els suporta com a query params).
  const modelsFiltered = useMemo(() => {
    return models.filter(m => {
      if (filtreAny && String(m.any) !== String(filtreAny)) return false
      if (filtreTemporada && m.temporada !== filtreTemporada) return false
      return true
    })
  }, [models, filtreAny, filtreTemporada])

  const handleDeleteModel = async (modelId, nomPrenda) => {
    if (!confirm(`Esborrar "${nomPrenda}"? Aquesta acció no es pot desfer.`)) return
    const res = await fetch(`${API}/api/v1/models/${modelId}/delete/`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      setModels(prev => prev.filter(m => m.id !== modelId))
      setTotal(t => Math.max(0, t - 1))
    } else {
      alert(`No s'ha pogut esborrar (HTTP ${res.status})`)
    }
  }

  return (
    <div style={{ padding: "24px", maxWidth: 1100, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 18, fontFamily: "IBM Plex Mono, monospace", color: "#1d1d1b", fontWeight: 500, margin: 0 }}>
            Models
          </h1>
          <div style={{ fontSize: 11, color: "#868685", fontFamily: "IBM Plex Mono, monospace", marginTop: 2 }}>
            {total} models
          </div>
        </div>
      </div>

      {/* Filtres */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <input
          value={cerca}
          onChange={e => setCerca(e.target.value)}
          placeholder="Cerca per codi o nom..."
          style={{
            padding: "6px 10px", border: "1px solid #e0d5c5", borderRadius: 4,
            fontSize: 12, fontFamily: "IBM Plex Mono, monospace", flex: 1, minWidth: 200,
            background: "#fff", color: "#1d1d1b",
          }}
        />
        <select value={filtreFase} onChange={e => setFiltreFase(e.target.value)} style={{
          padding: "6px 10px", border: "1px solid #e0d5c5", borderRadius: 4,
          fontSize: 12, fontFamily: "IBM Plex Mono, monospace", background: "#fff", color: "#1d1d1b",
        }}>
          <option value="">Totes les fases</option>
          {FASES.map(f => <option key={f} value={f}>{f}</option>)}
        </select>
        <select value={filtreEstat} onChange={e => setFiltreEstat(e.target.value)} style={{
          padding: "6px 10px", border: "1px solid #e0d5c5", borderRadius: 4,
          fontSize: 12, fontFamily: "IBM Plex Mono, monospace", background: "#fff", color: "#1d1d1b",
        }}>
          <option value="">Tots els estats</option>
          <option value="Nou">Nou</option>
          <option value="EnCurs">En curs</option>
          <option value="EnRevisio">En revisió</option>
          <option value="Tancat">Tancat</option>
        </select>
        <select value={filtreAny} onChange={e => setFiltreAny(e.target.value)} style={{
          padding: "6px 10px", border: "1px solid #e0d5c5", borderRadius: 4,
          fontSize: 12, fontFamily: "IBM Plex Mono, monospace", background: "#fff", color: "#1d1d1b",
        }}>
          <option value="">Tots els anys</option>
          {ANYS.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <select value={filtreTemporada} onChange={e => setFiltreTemporada(e.target.value)} style={{
          padding: "6px 10px", border: "1px solid #e0d5c5", borderRadius: 4,
          fontSize: 12, fontFamily: "IBM Plex Mono, monospace", background: "#fff", color: "#1d1d1b",
        }}>
          <option value="">Totes les temporades</option>
          {TEMPORADES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        {(cerca || filtreFase || filtreEstat || filtreAny || filtreTemporada) && (
          <button onClick={() => { setCerca(""); setFiltreFase(""); setFiltreEstat(""); setFiltreAny(""); setFiltreTemporada("") }} style={{
            padding: "6px 12px", border: "1px solid #e0d5c5", borderRadius: 4,
            fontSize: 11, fontFamily: "IBM Plex Mono, monospace", cursor: "pointer",
            background: "#fff", color: "#868685",
          }}>× Netejar</button>
        )}
      </div>

      {/* Llistat */}
      {loading ? (
        <div style={{ color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace", padding: "20px 0" }}>
          Carregant models...
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {modelsFiltered.map(m => (
            <div
              key={m.id}
              onClick={() => navigate(`/models/${m.id}`)}
              style={{
                border: "1px solid #e0d5c5", borderRadius: 8, padding: "14px 18px",
                cursor: "pointer", background: "#fff", transition: "all .1s",
              }}
              onMouseEnter={e => { e.currentTarget.style.background = "#fdf9f5"; e.currentTarget.style.borderColor = "#c27a2a" }}
              onMouseLeave={e => { e.currentTarget.style.background = "#fff"; e.currentTarget.style.borderColor = "#e0d5c5" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 8 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                    <span style={{
                      fontFamily: "IBM Plex Mono, monospace", fontSize: 13,
                      fontWeight: 700, color: "#c27a2a",
                    }}>{m.codi_intern || m.codi_client}</span>
                    <span style={{ fontSize: 13, color: "#1d1d1b", fontWeight: 500 }}>{m.nom_prenda}</span>
                  </div>
                  <div style={{ fontSize: 11, color: "#868685", fontFamily: "IBM Plex Mono, monospace" }}>
                    {m.temporada}{m.any ? ` ${m.any}` : ""}
                    {m.garment_type_nom && ` · ${m.garment_type_nom}`}
                    {m.responsable_nom && ` · ${m.responsable_nom}`}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
                  <EstatBadge estat={m.prioritat} size="xs" />
                  <EstatBadge estat={m.estat} size="xs" />
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDeleteModel(m.id, m.nom_prenda) }}
                    title="Esborrar model"
                    style={{
                      fontSize: 10, color: "#C0392B", background: "none",
                      border: "1px solid #FADBD8", borderRadius: 4,
                      padding: "2px 8px", cursor: "pointer",
                      fontFamily: "IBM Plex Mono, monospace",
                    }}
                  >
                    Esborrar
                  </button>
                </div>
              </div>
              {m.design_freeze_at && (
                <div style={{ fontSize: 10, color: "#3b6d11", fontFamily: "IBM Plex Mono, monospace", marginTop: 4 }}>
                  ✓ Design Freeze aprovat
                </div>
              )}
            </div>
          ))}
          {modelsFiltered.length === 0 && (
            <div style={{
              textAlign: "center", padding: "40px 0",
              color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace",
            }}>
              {cerca || filtreFase || filtreEstat || filtreAny || filtreTemporada
                ? "Sense resultats amb aquest filtre."
                : "Sense models. Crea el primer!"}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
