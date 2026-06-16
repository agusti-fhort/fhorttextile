import { useState, useEffect } from "react"
import useAuthStore from "../store/auth"
import { EstatBadge } from "../components/EstatBadge"

// Fase catàlegs — Pas 2: Tasks.jsx aprimat. El tab "Catàleg" (mostrava el model Tasca antic, buit) i
// el tab "Paquets de servei" (descartat) s'han jubilat. El catàleg de TaskType viu ara a /task-types.
// Aquesta pàgina queda NOMÉS amb el Llistat de tasques actives.
const API = import.meta.env.VITE_API_URL || ""

const FASE_COLORS = {
  Disseny: "#e8d5b0", Tècnic: "#d0d8f0", Prototip: "#f0d8c8",
  Mostres: "#d8f0d8", Preproducció: "#d8eef0", Producció: "#ead8f0",
}

// ── Llistat: ModelTasques actives ─────────────────────────────────────────────
function ActiveTasks({ token }) {
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
            background: filtre === e ? "#f5e6d0" : "var(--white)",
            color: filtre === e ? "var(--gold)" : "var(--text-muted)",
            border: `1px solid ${filtre === e ? "var(--gold)" : "var(--border)"}`,
          }}>{e}</button>
        ))}
        <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-muted)", alignSelf: "center" }}>
          {tasques.length} tasques
        </span>
      </div>

      {loading ? (
        <div style={{ color: "var(--text-muted)", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}>Carregant...</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid var(--border)" }}>
              {["Tasca", "Model", "Fase", "Estat", "Gate", "Slots"].map(h => (
                <th key={h} style={{ textAlign: "left", padding: "6px 8px", color: "var(--text-muted)", fontWeight: 600, fontSize: 11 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tasques.map((t, i) => (
              <tr key={t.id} style={{ borderBottom: "1px solid #f5ede0", background: i % 2 === 0 ? "var(--white)" : "#fdf9f5" }}>
                <td style={{ padding: "7px 8px", color: "var(--text-main)" }}>{t.nom_tasca}</td>
                <td style={{ padding: "7px 8px", color: "var(--gold)" }}>{t.model_codi || t.model}</td>
                <td style={{ padding: "7px 8px" }}>
                  <span style={{
                    padding: "2px 7px", borderRadius: 3, fontSize: 10,
                    background: FASE_COLORS[t.fase] || "#f0ede8",
                    color: "var(--text-main)",
                  }}>{t.fase}</span>
                </td>
                <td style={{ padding: "7px 8px" }}><EstatBadge estat={t.estat} size="xs" /></td>
                <td style={{ padding: "7px 8px", textAlign: "center" }}>
                  {t.es_gate && <span style={{ color: "var(--gold)", fontSize: 13 }}>◆</span>}
                </td>
                <td style={{ padding: "7px 8px", color: "var(--text-muted)" }}>
                  {t.slots_reals > 0 ? `${t.slots_reals}/${t.slots_base}` : t.slots_base || "—"}
                </td>
              </tr>
            ))}
            {tasques.length === 0 && (
              <tr><td colSpan={6} style={{ padding: "20px 8px", textAlign: "center", color: "var(--text-muted)" }}>
                Sense tasques en estat "{filtre}"
              </td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ── Component principal ───────────────────────────────────────────────────────
export default function Tasks() {
  const token = useAuthStore.getState().token || localStorage.getItem('access_token')

  return (
    <div style={{ padding: "24px", maxWidth: 960, margin: "0 auto" }}>
      <h1 style={{ fontSize: 18, fontFamily: "IBM Plex Mono, monospace", color: "var(--text-main)", marginBottom: 20, fontWeight: 500 }}>
        Tasques
      </h1>
      <ActiveTasks token={token} />
    </div>
  )
}
