
import { useState, useEffect } from "react"
import { useLocation, useNavigate } from "react-router-dom"

import useAuthStore from "../store/auth"
const API = import.meta.env.VITE_API_URL || ""

const SECCIONS = [
  { label: "General", path: "/configuracio" },
  { label: "Garment Types", path: "/configuracio/garment-types" },
  { label: "Size Systems", path: "/configuracio/size-systems" },
  { label: "Grading Rules", path: "/configuracio/grading" },
]

function TabNav({ current }) {
  const navigate = useNavigate()
  return (
    <div style={{ display: "flex", borderBottom: "1px solid #e0d5c5", marginBottom: 24 }}>
      {SECCIONS.map(s => (
        <button key={s.path} onClick={() => navigate(s.path)} style={{
          padding: "8px 18px", background: "none", border: "none",
          borderBottom: current === s.path ? "2px solid #c27a2a" : "2px solid transparent",
          color: current === s.path ? "#c27a2a" : "#868685",
          fontFamily: "IBM Plex Mono, monospace", fontSize: 12, cursor: "pointer",
          fontWeight: current === s.path ? 600 : 400,
        }}>{s.label}</button>
      ))}
    </div>
  )
}

function SeccioGeneral({ token }) {
  const [me, setMe] = useState(null)
  useEffect(() => {
    fetch(`${API}/api/v1/me/`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(setMe).catch(() => {})
  }, [token])

  return (
    <div style={{ maxWidth: 480 }}>
      <div style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 12, marginBottom: 24 }}>
        <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "#c27a2a", marginBottom: 12 }}>
          Compte
        </div>
        {me && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              ["Usuari", me.username],
              ["Nom complet", me.full_name || me.nom_complet],
              ["Email", me.email],
              ["Rol", me.rol_nom || "—"],
            ].map(([label, val]) => (
              <div key={label} style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: 8, padding: "5px 0", borderBottom: "1px solid #f5ede0" }}>
                <span style={{ color: "#868685" }}>{label}</span>
                <span style={{ color: "#1d1d1b" }}>{val || "—"}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 12 }}>
        <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "#c27a2a", marginBottom: 12 }}>
          Tenant
        </div>
        <div style={{ padding: "10px 14px", background: "#fdf9f5", border: "1px solid #e0d5c5", borderRadius: 6, color: "#868685", fontSize: 11 }}>
          Configuració avançada del tenant disponible properament.
        </div>
      </div>
    </div>
  )
}

function GarmentTypes({ token }) {
  const [types, setTypes] = useState([])
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/v1/garment-types/`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch(`${API}/api/v1/garment-groups/`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
    ]).then(([t, g]) => {
      setTypes(Array.isArray(t) ? t : (t.results || []))
      setGroups(Array.isArray(g) ? g : (g.results || []))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [token])

  if (loading) return <div style={{ color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}>Carregant...</div>

  const byGroup = types.reduce((acc, t) => {
    const g = t.garment_group_nom || t.garment_group || "Altres"
    if (!acc[g]) acc[g] = []
    acc[g].push(t)
    return acc
  }, {})

  return (
    <div>
      <div style={{ fontSize: 11, color: "#868685", fontFamily: "IBM Plex Mono, monospace", marginBottom: 16 }}>
        {types.length} tipus de prenda · {groups.length} grups
      </div>
      {Object.entries(byGroup).map(([group, items]) => (
        <div key={group} style={{ marginBottom: 20 }}>
          <div style={{
            fontSize: 10, fontWeight: 600, letterSpacing: ".08em",
            textTransform: "uppercase", color: "#c27a2a",
            fontFamily: "IBM Plex Mono, monospace", marginBottom: 8,
            padding: "4px 0", borderBottom: "1px solid #e0d5c5",
          }}>{group}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
            {items.map(t => (
              <div key={t.id} style={{
                padding: "8px 12px", border: "1px solid #e0d5c5", borderRadius: 6,
                fontFamily: "IBM Plex Mono, monospace", fontSize: 12,
                background: "#fdf9f5",
              }}>
                <div style={{ color: "#1d1d1b", fontWeight: 500 }}>{t.nom_ca || t.nom || t.name}</div>
                {t.nom_en && t.nom_en !== t.nom_ca && (
                  <div style={{ color: "#868685", fontSize: 11 }}>{t.nom_en}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function SizeSystems({ token }) {
  const [systems, setSystems] = useState([])
  const [loading, setLoading] = useState(true)
  const [obert, setObert] = useState(null)

  useEffect(() => {
    fetch(`${API}/api/v1/size-systems/`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => { setSystems(Array.isArray(d) ? d : (d.results || [])); setLoading(false) })
      .catch(() => setLoading(false))
  }, [token])

  if (loading) return <div style={{ color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}>Carregant...</div>

  return (
    <div>
      <div style={{ fontSize: 11, color: "#868685", fontFamily: "IBM Plex Mono, monospace", marginBottom: 16 }}>
        {systems.length} sistemes de tallatge
      </div>
      {systems.map(s => (
        <div key={s.id} style={{ marginBottom: 8, border: "1px solid #e0d5c5", borderRadius: 6, overflow: "hidden" }}>
          <div
            onClick={() => setObert(obert === s.id ? null : s.id)}
            style={{
              padding: "10px 16px", cursor: "pointer", background: "#fdf9f5",
              display: "flex", alignItems: "center", gap: 12,
              fontFamily: "IBM Plex Mono, monospace",
            }}
          >
            <span style={{ fontSize: 13, color: "#1d1d1b", fontWeight: 600, flex: 1 }}>{s.nom || s.name}</span>
            <span style={{ fontSize: 11, color: "#868685" }}>{s.tipus || s.type || ""}</span>
            <span style={{ color: "#c27a2a" }}>{obert === s.id ? "▴" : "▾"}</span>
          </div>
          {obert === s.id && (
            <div style={{ padding: "8px 16px 12px", background: "#fff", fontFamily: "IBM Plex Mono, monospace", fontSize: 12 }}>
              <div style={{ color: "#868685", fontSize: 11, marginBottom: 8 }}>Talles del sistema:</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {(s.size_definitions || s.sizes || []).map((sd, i) => (
                  <span key={i} style={{
                    padding: "3px 10px", borderRadius: 4, fontSize: 11,
                    background: "#f5e6d0", color: "#c27a2a", border: "1px solid #e0c8a0",
                  }}>
                    {sd.label || sd.size_label || sd}
                  </span>
                ))}
                {(!s.size_definitions && !s.sizes) && (
                  <span style={{ color: "#868685", fontSize: 11 }}>Talles no carregades</span>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function GradingRules({ token }) {
  const [sets, setSets] = useState([])
  const [loading, setLoading] = useState(true)
  const [obert, setObert] = useState(null)
  const [rules, setRules] = useState({})

  useEffect(() => {
    fetch(`${API}/api/v1/grading-rule-sets/`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => { setSets(Array.isArray(d) ? d : (d.results || [])); setLoading(false) })
      .catch(() => setLoading(false))
  }, [token])

  const loadRules = async (setId) => {
    if (rules[setId]) return
    try {
      const r = await fetch(`${API}/api/v1/grading-rules/?rule_set=${setId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const d = await r.json()
      setRules(prev => ({ ...prev, [setId]: Array.isArray(d) ? d : (d.results || []) }))
    } catch (e) {}
  }

  const handleOpen = (id) => {
    const nou = obert === id ? null : id
    setObert(nou)
    if (nou) loadRules(nou)
  }

  if (loading) return <div style={{ color: "#868685", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}>Carregant...</div>

  return (
    <div>
      <div style={{ fontSize: 11, color: "#868685", fontFamily: "IBM Plex Mono, monospace", marginBottom: 16 }}>
        {sets.length} conjunts de regles de grading
      </div>
      {sets.map(s => (
        <div key={s.id} style={{ marginBottom: 8, border: "1px solid #e0d5c5", borderRadius: 6, overflow: "hidden" }}>
          <div
            onClick={() => handleOpen(s.id)}
            style={{
              padding: "10px 16px", cursor: "pointer", background: "#fdf9f5",
              display: "flex", alignItems: "center", gap: 12,
              fontFamily: "IBM Plex Mono, monospace",
            }}
          >
            <span style={{ fontSize: 13, color: "#1d1d1b", fontWeight: 600, flex: 1 }}>{s.nom || s.name}</span>
            <span style={{ fontSize: 11, color: "#868685" }}>{s.garment_type_nom || ""}</span>
            <span style={{ color: "#c27a2a" }}>{obert === s.id ? "▴" : "▾"}</span>
          </div>
          {obert === s.id && (
            <div style={{ padding: "8px 16px 12px", background: "#fff" }}>
              {!rules[s.id] ? (
                <div style={{ color: "#868685", fontSize: 11, fontFamily: "IBM Plex Mono, monospace" }}>Carregant regles...</div>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, fontFamily: "IBM Plex Mono, monospace" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid #e0d5c5" }}>
                      {["POM", "Tipus", "Increment", "Actiu"].map(h => (
                        <th key={h} style={{ textAlign: "left", padding: "4px 8px", color: "#868685", fontWeight: 600 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rules[s.id].map(r => (
                      <tr key={r.id} style={{ borderBottom: "1px solid #f5ede0" }}>
                        <td style={{ padding: "4px 8px", color: "#c27a2a" }}>{r.pom_codi || r.pom}</td>
                        <td style={{ padding: "4px 8px", color: "#1d1d1b" }}>{r.logica || r.grading_type}</td>
                        <td style={{ padding: "4px 8px", color: "#1d1d1b" }}>{r.increment} cm</td>
                        <td style={{ padding: "4px 8px" }}>
                          <span style={{ color: r.actiu ? "#3b6d11" : "#868685" }}>{r.actiu ? "✓" : "—"}</span>
                        </td>
                      </tr>
                    ))}
                    {rules[s.id].length === 0 && (
                      <tr><td colSpan={4} style={{ padding: "8px", color: "#868685" }}>Sense regles</td></tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default function Settings() {
  const location = useLocation()
  const navigate = useNavigate()
  const token = useAuthStore.getState().token || localStorage.getItem('access_token')

  // Auth guard: redirect if there is no token (no fetch will run without auth)
  useEffect(() => { if (!token) navigate("/login") }, [token, navigate])
  const current = location.pathname

  // Redirigir sub-rutes desconegudes a general
  useEffect(() => {
    if (!SECCIONS.find(s => s.path === current)) navigate("/configuracio")
  }, [current, navigate])

  return (
    <div style={{ padding: "24px", maxWidth: 960, margin: "0 auto" }}>
      <h1 style={{ fontSize: 18, fontFamily: "IBM Plex Mono, monospace", color: "#1d1d1b", marginBottom: 20, fontWeight: 500 }}>
        Configuració
      </h1>
      <TabNav current={current} />
      {current === "/configuracio" && <SeccioGeneral token={token} />}
      {current === "/configuracio/garment-types" && <GarmentTypes token={token} />}
      {current === "/configuracio/size-systems" && <SizeSystems token={token} />}
      {current === "/configuracio/grading" && <GradingRules token={token} />}
    </div>
  )
}
