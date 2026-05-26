
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import useAuthStore from "../store/auth"
import { EstatBadge } from "../components/EstatBadge"
import { FaseStepper } from "../components/FaseStepper"

const API = import.meta.env.VITE_API_URL || ""

function KPICard({ label, value, sub, color = "#c27a2a", onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "#fff", border: "1px solid #e0d5c5", borderRadius: 8,
        padding: "18px 20px", cursor: onClick ? "pointer" : "default",
        transition: "all .1s", flex: 1, minWidth: 140,
      }}
      onMouseEnter={e => onClick && (e.currentTarget.style.borderColor = color)}
      onMouseLeave={e => onClick && (e.currentTarget.style.borderColor = "#e0d5c5")}
    >
      <div style={{ fontSize: 11, color: "#868685", fontFamily: "IBM Plex Mono, monospace", marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 600, color, fontFamily: "IBM Plex Mono, monospace", lineHeight: 1 }}>{value ?? "—"}</div>
      {sub && <div style={{ fontSize: 11, color: "#868685", fontFamily: "IBM Plex Mono, monospace", marginTop: 6 }}>{sub}</div>}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const token = useAuthStore.getState().token || localStorage.getItem('access_token')

  // Guard auth: redirigeix si no hi ha token (cap fetch s'executarà sense auth)
  useEffect(() => { if (!token) navigate("/login") }, [token, navigate])
  const [stats, setStats] = useState({})
  const [recents, setRecents] = useState([])
  const [avisos, setAvisos] = useState([])
  const [me, setMe] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` }
    Promise.allSettled([
      fetch(`${API}/api/v1/models/?limit=100`, { headers }).then(r => r.json()),
      fetch(`${API}/api/v1/models/?estat=En+curs&ordering=-darrera_activitat&limit=5`, { headers }).then(r => r.json()),
      fetch(`${API}/api/v1/pom-alerts/?estat=Obert&limit=100`, { headers }).then(r => r.json()),
      fetch(`${API}/api/v1/me/`, { headers }).then(r => r.json()),
    ]).then(([allRes, recentsRes, avisosRes, meRes]) => {
      // Stats
      if (allRes.status === "fulfilled") {
        const all = allRes.value
        const items = Array.isArray(all) ? all : (all.results || [])
        const total = all.count || items.length
        const enCurs = items.filter(m => m.estat === "En curs").length
        const tallesGen = items.filter(m => m.fase_actual === "Prototip" || m.fase_actual === "Mostres").length
        setStats({ total, enCurs, tallesGen })
      }
      // Recents
      if (recentsRes.status === "fulfilled") {
        const d = recentsRes.value
        setRecents(Array.isArray(d) ? d : (d.results || []))
      }
      // Avisos
      if (avisosRes.status === "fulfilled") {
        const d = avisosRes.value
        setAvisos(Array.isArray(d) ? d : (d.results || []))
      }
      // Me
      if (meRes.status === "fulfilled") setMe(meRes.value)

      setLoading(false)
    })
  }, [token])

  const hora = new Date().getHours()
  const salutacio = hora < 13 ? "Bon dia" : hora < 20 ? "Bona tarda" : "Bona nit"

  return (
    <div style={{ padding: "24px", maxWidth: 1100, margin: "0 auto" }}>
      {/* Salutació */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 500, color: "#1d1d1b", margin: "0 0 4px" }}>
          {salutacio}{me ? `, ${me.full_name?.split(" ")[0] || me.username}` : ""}.
        </h1>
        <div style={{ fontSize: 13, color: "#868685", fontFamily: "IBM Plex Mono, monospace" }}>
          {new Date().toLocaleDateString("ca-ES", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
        </div>
      </div>

      {/* KPIs */}
      <div style={{ display: "flex", gap: 12, marginBottom: 28, flexWrap: "wrap" }}>
        <KPICard
          label="Total models"
          value={loading ? "…" : stats.total}
          sub="al sistema"
          onClick={() => navigate("/models")}
        />
        <KPICard
          label="En curs"
          value={loading ? "…" : stats.enCurs}
          sub="models actius"
          color="#3b7a9a"
          onClick={() => navigate("/models?estat=En+curs")}
        />
        <KPICard
          label="Avisos oberts"
          value={loading ? "…" : avisos.length}
          sub="desviacions POM"
          color={avisos.length > 0 ? "#a32d2d" : "#868685"}
          onClick={() => navigate("/avisos")}
        />
        <KPICard
          label="En prototip/mostres"
          value={loading ? "…" : stats.tallesGen}
          sub="models en fase crítica"
          color="#854f0b"
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20, alignItems: "start" }}>
        {/* Models recents */}
        <div>
          <div style={{
            fontSize: 10, fontWeight: 600, letterSpacing: ".08em",
            textTransform: "uppercase", color: "#c27a2a",
            fontFamily: "IBM Plex Mono, monospace", marginBottom: 12,
          }}>
            Models actius recents
          </div>
          {loading ? (
            <div style={{ color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}>Carregant...</div>
          ) : recents.length === 0 ? (
            <div style={{
              padding: "20px", border: "1px dashed #e0d5c5", borderRadius: 8,
              textAlign: "center", color: "#868685", fontSize: 12,
              fontFamily: "IBM Plex Mono, monospace",
            }}>
              Sense models en curs.{" "}
              <span
                onClick={() => navigate("/models/nou")}
                style={{ color: "#c27a2a", cursor: "pointer", textDecoration: "underline" }}
              >
                Crea el primer
              </span>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {recents.map(m => (
                <div
                  key={m.id}
                  onClick={() => navigate(`/models/${m.id}`)}
                  style={{
                    border: "1px solid #e0d5c5", borderRadius: 8, padding: "12px 16px",
                    cursor: "pointer", background: "#fff",
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = "#fdf9f5"; e.currentTarget.style.borderColor = "#c27a2a" }}
                  onMouseLeave={e => { e.currentTarget.style.background = "#fff"; e.currentTarget.style.borderColor = "#e0d5c5" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <div>
                      <span style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 12, fontWeight: 700, color: "#c27a2a", marginRight: 10 }}>
                        {m.codi_intern || m.codi_client}
                      </span>
                      <span style={{ fontSize: 13, color: "#1d1d1b" }}>{m.nom_prenda}</span>
                    </div>
                    <EstatBadge estat={m.estat} size="xs" />
                  </div>
                  {m.fase_actual && (
                    <div style={{ transform: "scale(0.85)", transformOrigin: "left center" }}>
                      <FaseStepper faseActual={m.fase_actual} />
                    </div>
                  )}
                </div>
              ))}
              <button
                onClick={() => navigate("/models")}
                style={{
                  padding: "8px", border: "1px dashed #e0d5c5", borderRadius: 8,
                  background: "none", color: "#c27a2a", cursor: "pointer",
                  fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
                }}
              >
                Veure tots els models →
              </button>
            </div>
          )}
        </div>

        {/* Avisos */}
        <div>
          <div style={{
            fontSize: 10, fontWeight: 600, letterSpacing: ".08em",
            textTransform: "uppercase", color: "#c27a2a",
            fontFamily: "IBM Plex Mono, monospace", marginBottom: 12,
          }}>
            Avisos POM
          </div>
          {loading ? (
            <div style={{ color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}>Carregant...</div>
          ) : avisos.length === 0 ? (
            <div style={{
              padding: "16px", border: "1px solid #e0d5c5", borderRadius: 8,
              textAlign: "center", color: "#3b6d11", fontSize: 12,
              fontFamily: "IBM Plex Mono, monospace", background: "#f0f9f0",
            }}>
              ✓ Sense avisos oberts
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {avisos.slice(0, 6).map(a => (
                <div
                  key={a.id}
                  onClick={() => navigate("/avisos")}
                  style={{
                    padding: "8px 12px", border: "1px solid #f09595", borderRadius: 6,
                    background: "#fff5f5", cursor: "pointer",
                    fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
                  }}
                >
                  <div style={{ color: "#a32d2d", fontWeight: 500, marginBottom: 2 }}>
                    {a.pom_codi || a.pom} — {a.model_codi || a.model}
                  </div>
                  <div style={{ color: "#868685" }}>{a.missatge || a.message || "Desviació detectada"}</div>
                </div>
              ))}
              {avisos.length > 6 && (
                <button
                  onClick={() => navigate("/avisos")}
                  style={{
                    padding: "6px", border: "1px dashed #f09595", borderRadius: 6,
                    background: "none", color: "#a32d2d", cursor: "pointer",
                    fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
                  }}
                >
                  +{avisos.length - 6} avisos més →
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
