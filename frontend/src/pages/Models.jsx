
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import useAuthStore from "../store/auth"
import { EstatBadge } from "../components/EstatBadge"
import { FaseStepper } from "../components/FaseStepper"
import ImportFromSheetWizard from "../components/ImportFromSheet/ImportFromSheetWizard"

const API = import.meta.env.VITE_API_URL || ""

const FASES = ["Nou", "Disseny", "Tècnic", "Prototip", "Mostres", "Preproducció", "Producció", "Tancat"]

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
  const [total, setTotal] = useState(0)
  const [showImport, setShowImport] = useState(false)

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
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => setShowImport(true)} style={{
            padding: "7px 14px", borderRadius: 4, fontSize: 11, cursor: "pointer",
            background: "#fff", color: "#c27a2a", border: "1px solid #c27a2a",
            fontFamily: "IBM Plex Mono, monospace",
          }}>
            Importar fitxa tècnica
          </button>
          <button onClick={() => navigate("/models/nou-des-de-fitxer")} style={{
            padding: "7px 14px", borderRadius: 4, fontSize: 11, cursor: "pointer",
            background: "#fff", color: "#868685", border: "1px solid #e0d5c5",
            fontFamily: "IBM Plex Mono, monospace",
          }}>
            ⬆ Des de fitxer
          </button>
          <button onClick={() => navigate("/models/nou")} style={{
            padding: "7px 16px", borderRadius: 4, fontSize: 11, cursor: "pointer",
            background: "#f5e6d0", color: "#c27a2a", border: "1px solid #c27a2a",
            fontFamily: "IBM Plex Mono, monospace", fontWeight: 600,
          }}>
            + Nou model
          </button>
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
          {["Nou", "En curs", "Bloquejat", "Tancat"].map(e => <option key={e} value={e}>{e}</option>)}
        </select>
        {(cerca || filtreFase || filtreEstat) && (
          <button onClick={() => { setCerca(""); setFiltreFase(""); setFiltreEstat("") }} style={{
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
          {models.map(m => (
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
                </div>
              </div>
              {m.fase_actual && (
                <div style={{ transform: "scale(0.9)", transformOrigin: "left center", marginTop: 4 }}>
                  <FaseStepper faseActual={m.fase_actual} />
                </div>
              )}
              {m.design_freeze_at && (
                <div style={{ fontSize: 10, color: "#3b6d11", fontFamily: "IBM Plex Mono, monospace", marginTop: 4 }}>
                  ✓ Design Freeze aprovat
                </div>
              )}
            </div>
          ))}
          {models.length === 0 && (
            <div style={{
              textAlign: "center", padding: "40px 0",
              color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace",
            }}>
              {cerca || filtreFase || filtreEstat ? "Sense resultats amb aquest filtre." : "Sense models. Crea el primer!"}
            </div>
          )}
        </div>
      )}

      {showImport && (
        <ImportFromSheetWizard
          onModelCreated={(modelId) => navigate(`/models/${modelId}`)}
          onClose={() => setShowImport(false)}
        />
      )}
    </div>
  )
}
