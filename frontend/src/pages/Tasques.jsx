
import { useState, useEffect } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import useAuthStore from "../store/auth"
import { EstatBadge } from "../components/EstatBadge"

const API = import.meta.env.VITE_API_URL || ""

const TABS = [
  { label: "Tasques actives", path: "/tasques" },
  { label: "Catàleg", path: "/tasques/catalog" },
  { label: "Paquets de servei", path: "/tasques/paquets" },
]

const FASE_COLORS = {
  Disseny: "#e8d5b0", Tècnic: "#d0d8f0", Prototip: "#f0d8c8",
  Mostres: "#d8f0d8", Preproducció: "#d8eef0", Producció: "#ead8f0",
}

function TabNav({ current }) {
  const navigate = useNavigate()
  return (
    <div style={{ display: "flex", borderBottom: "1px solid #e0d5c5", marginBottom: 20 }}>
      {TABS.map(t => (
        <button key={t.path} onClick={() => navigate(t.path)} style={{
          padding: "8px 18px", background: "none", border: "none",
          borderBottom: current === t.path ? "2px solid #c27a2a" : "2px solid transparent",
          color: current === t.path ? "#c27a2a" : "#868685",
          fontFamily: "IBM Plex Mono, monospace", fontSize: 12, cursor: "pointer",
          fontWeight: current === t.path ? 600 : 400,
        }}>{t.label}</button>
      ))}
    </div>
  )
}

// ── Vista 1: ModelTasques actives ─────────────────────────────────────────────
function TasquesActives({ token }) {
  const [tasques, setTasques] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtre, setFiltre] = useState("En curs")

  useEffect(() => {
    setLoading(true)
    fetch(`${API}/api/v1/model-tasques/?estat=${encodeURIComponent(filtre)}&ordering=ordre`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => { setTasques(Array.isArray(d) ? d : (d.results || [])); setLoading(false) })
      .catch(() => setLoading(false))
  }, [token, filtre])

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {["Pendent", "En curs", "Bloquejada", "Feta"].map(e => (
          <button key={e} onClick={() => setFiltre(e)} style={{
            padding: "4px 12px", borderRadius: 4, fontSize: 11,
            fontFamily: "IBM Plex Mono, monospace", cursor: "pointer",
            background: filtre === e ? "#f5e6d0" : "#fff",
            color: filtre === e ? "#c27a2a" : "#868685",
            border: `1px solid ${filtre === e ? "#c27a2a" : "#e0d5c5"}`,
          }}>{e}</button>
        ))}
        <span style={{ marginLeft: "auto", fontSize: 11, color: "#868685", alignSelf: "center" }}>
          {tasques.length} tasques
        </span>
      </div>

      {loading ? (
        <div style={{ color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}>Carregant...</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e0d5c5" }}>
              {["Tasca", "Model", "Fase", "Estat", "Gate", "Slots"].map(h => (
                <th key={h} style={{ textAlign: "left", padding: "6px 8px", color: "#868685", fontWeight: 600, fontSize: 11 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tasques.map((t, i) => (
              <tr key={t.id} style={{ borderBottom: "1px solid #f5ede0", background: i % 2 === 0 ? "#fff" : "#fdf9f5" }}>
                <td style={{ padding: "7px 8px", color: "#1d1d1b" }}>{t.nom_tasca}</td>
                <td style={{ padding: "7px 8px", color: "#c27a2a" }}>{t.model_codi || t.model}</td>
                <td style={{ padding: "7px 8px" }}>
                  <span style={{
                    padding: "2px 7px", borderRadius: 3, fontSize: 10,
                    background: FASE_COLORS[t.fase] || "#f0ede8",
                    color: "#1d1d1b",
                  }}>{t.fase}</span>
                </td>
                <td style={{ padding: "7px 8px" }}><EstatBadge estat={t.estat} size="xs" /></td>
                <td style={{ padding: "7px 8px", textAlign: "center" }}>
                  {t.es_gate && <span style={{ color: "#c27a2a", fontSize: 13 }}>◆</span>}
                </td>
                <td style={{ padding: "7px 8px", color: "#868685" }}>
                  {t.slots_reals > 0 ? `${t.slots_reals}/${t.slots_base}` : t.slots_base || "—"}
                </td>
              </tr>
            ))}
            {tasques.length === 0 && (
              <tr><td colSpan={6} style={{ padding: "20px 8px", textAlign: "center", color: "#868685" }}>
                Sense tasques en estat "{filtre}"
              </td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ── Vista 2: Catàleg de Tasques ───────────────────────────────────────────────
function CatalegTasques({ token }) {
  const [tasques, setTasques] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/api/v1/tasques/?ordering=ordre_base`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => { setTasques(Array.isArray(d) ? d : (d.results || [])); setLoading(false) })
      .catch(() => setLoading(false))
  }, [token])

  const byFase = tasques.reduce((acc, t) => {
    if (!acc[t.fase]) acc[t.fase] = []
    acc[t.fase].push(t)
    return acc
  }, {})

  if (loading) return <div style={{ color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}>Carregant...</div>

  return (
    <div>
      <div style={{ fontSize: 11, color: "#868685", fontFamily: "IBM Plex Mono, monospace", marginBottom: 16 }}>
        {tasques.length} tasques al catàleg
      </div>
      {Object.entries(byFase).map(([fase, items]) => (
        <div key={fase} style={{ marginBottom: 20 }}>
          <div style={{
            fontSize: 10, fontWeight: 600, letterSpacing: ".08em",
            textTransform: "uppercase", color: "#c27a2a",
            fontFamily: "IBM Plex Mono, monospace", marginBottom: 8,
            padding: "4px 0", borderBottom: "1px solid #e0d5c5",
          }}>
            {fase}
          </div>
          {items.map(t => (
            <div key={t.id} style={{
              display: "grid", gridTemplateColumns: "40px 1fr 80px 60px 50px",
              gap: 8, padding: "6px 4px", borderBottom: "1px solid #f5ede0",
              fontFamily: "IBM Plex Mono, monospace", fontSize: 12, alignItems: "center",
            }}>
              <span style={{ color: "#868685", fontSize: 11 }}>#{t.ordre_base}</span>
              <span style={{ color: "#1d1d1b" }}>
                {t.gate && <span style={{ color: "#c27a2a", marginRight: 6 }}>◆</span>}
                {t.nom_tasca}
              </span>
              <span style={{ fontSize: 10, color: "#868685" }}>{t.tipus_tasca}</span>
              <span style={{ fontSize: 11, color: t.facturable ? "#3b6d11" : "#868685" }}>
                {t.facturable ? "Facturable" : "No fact."}
              </span>
              <span style={{ fontSize: 11, color: "#868685", textAlign: "right" }}>
                {t.slots_base > 0 ? `${t.slots_base}sl` : ""}
              </span>
            </div>
          ))}
        </div>
      ))}
      {tasques.length === 0 && (
        <div style={{ color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace", padding: "20px 0" }}>
          Catàleg de tasques buit. Crea tasques des de Configuració.
        </div>
      )}
    </div>
  )
}

// ── Vista 3: Paquets de Servei ────────────────────────────────────────────────
function PaquetsServei({ token }) {
  const [paquets, setPaquets] = useState([])
  const [loading, setLoading] = useState(true)
  const [obert, setObert] = useState(null)

  useEffect(() => {
    fetch(`${API}/api/v1/paquets-servei/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => { setPaquets(Array.isArray(d) ? d : (d.results || [])); setLoading(false) })
      .catch(() => setLoading(false))
  }, [token])

  if (loading) return <div style={{ color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}>Carregant...</div>

  return (
    <div>
      <div style={{ fontSize: 11, color: "#868685", fontFamily: "IBM Plex Mono, monospace", marginBottom: 16 }}>
        {paquets.length} paquets de servei
      </div>
      {paquets.map(p => (
        <div key={p.id} style={{ marginBottom: 8, border: "1px solid #e0d5c5", borderRadius: 6, overflow: "hidden" }}>
          <div
            onClick={() => setObert(obert === p.id ? null : p.id)}
            style={{
              padding: "10px 16px", cursor: "pointer", background: "#fdf9f5",
              display: "flex", alignItems: "center", gap: 12,
              fontFamily: "IBM Plex Mono, monospace",
            }}
          >
            <span style={{ fontSize: 13, color: "#1d1d1b", fontWeight: 600, flex: 1 }}>{p.nom}</span>
            <span style={{
              padding: "2px 8px", borderRadius: 3, fontSize: 10,
              background: "#f5e6d0", color: "#c27a2a",
            }}>{p.grup || "General"}</span>
            <span style={{ fontSize: 11, color: "#868685" }}>
              {p.tasques?.length || 0} tasques
            </span>
            <span style={{ color: "#c27a2a" }}>{obert === p.id ? "▴" : "▾"}</span>
          </div>
          {obert === p.id && (
            <div style={{ padding: "8px 16px 12px", background: "#fff" }}>
              {p.descripcio && (
                <div style={{ fontSize: 12, color: "#868685", fontFamily: "IBM Plex Mono, monospace", marginBottom: 10 }}>
                  {p.descripcio}
                </div>
              )}
              {(p.tasques || []).map((t, i) => (
                <div key={i} style={{
                  display: "flex", gap: 10, padding: "4px 0",
                  borderBottom: "1px solid #f5ede0",
                  fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
                  alignItems: "center",
                }}>
                  <span style={{ color: "#868685", minWidth: 24 }}>#{t.ordre}</span>
                  <span style={{ color: "#1d1d1b", flex: 1 }}>
                    {t.tasca_detail?.gate && <span style={{ color: "#c27a2a", marginRight: 6 }}>◆</span>}
                    {t.tasca_detail?.nom_tasca || `Tasca ${t.tasca}`}
                  </span>
                  <span style={{ color: "#868685" }}>{t.tasca_detail?.fase}</span>
                  {t.opcional && <span style={{ color: "#868685", fontSize: 10 }}>opcional</span>}
                </div>
              ))}
              {(!p.tasques || p.tasques.length === 0) && (
                <div style={{ color: "#868685", fontSize: 11, fontFamily: "IBM Plex Mono, monospace" }}>
                  Sense tasques definides
                </div>
              )}
            </div>
          )}
        </div>
      ))}
      {paquets.length === 0 && (
        <div style={{ color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace", padding: "20px 0" }}>
          Sense paquets de servei. Crea'n des de Configuració.
        </div>
      )}
    </div>
  )
}

// ── Component principal ───────────────────────────────────────────────────────
export default function Tasques() {
  const location = useLocation()
  const token = useAuthStore.getState().token || localStorage.getItem('access_token')

  // Guard auth: redirigeix si no hi ha token (cap fetch s'executarà sense auth)
  useEffect(() => { if (!token) navigate("/login") }, [token, navigate])
  const current = location.pathname

  return (
    <div style={{ padding: "24px", maxWidth: 960, margin: "0 auto" }}>
      <h1 style={{ fontSize: 18, fontFamily: "IBM Plex Mono, monospace", color: "#1d1d1b", marginBottom: 20, fontWeight: 500 }}>
        Tasques
      </h1>
      <TabNav current={current} />
      {current === "/tasques" && <TasquesActives token={token} />}
      {current === "/tasques/catalog" && <CatalegTasques token={token} />}
      {current === "/tasques/paquets" && <PaquetsServei token={token} />}
    </div>
  )
}
