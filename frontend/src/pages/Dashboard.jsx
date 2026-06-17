
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import useAuthStore from "../store/auth"
import { EstatBadge } from "../components/EstatBadge"
import { PhaseStepper } from "../components/PhaseStepper"

const API = import.meta.env.VITE_API_URL || ""

function KPICard({ label, value, sub, color = "var(--gold)", onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--white)", border: "1px solid var(--border)", borderRadius: 8,
        padding: "18px 20px", cursor: onClick ? "pointer" : "default",
        transition: "all .1s", flex: 1, minWidth: 140,
      }}
      onMouseEnter={e => onClick && (e.currentTarget.style.borderColor = color)}
      onMouseLeave={e => onClick && (e.currentTarget.style.borderColor = "var(--border)")}
    >
      <div style={{ fontSize: 'var(--fs-body)', color: "var(--text-muted)", fontFamily: "IBM Plex Mono, monospace", marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 'var(--fs-display)', fontWeight: 600, color, fontFamily: "IBM Plex Mono, monospace", lineHeight: 1 }}>{value ?? "—"}</div>
      {sub && <div style={{ fontSize: 'var(--fs-body)', color: "var(--text-muted)", fontFamily: "IBM Plex Mono, monospace", marginTop: 6 }}>{sub}</div>}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const token = useAuthStore.getState().token || localStorage.getItem('access_token')

  // Auth guard: redirect if there is no token (no fetch will run without auth)
  useEffect(() => { if (!token) navigate("/login") }, [token, navigate])
  const [stats, setStats] = useState({})
  const [recents, setRecents] = useState([])
  const [avisos, setAvisos] = useState([])
  const [avisosSummary, setAvisosSummary] = useState(null)
  const [me, setMe] = useState(null)
  const [loading, setLoading] = useState(true)
  const [onboarding, setOnboarding] = useState(null)

  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` }
    Promise.allSettled([
      fetch(`${API}/api/v1/models/?limit=100`, { headers }).then(r => r.json()),
      fetch(`${API}/api/v1/models/?estat=EnCurs&ordering=-darrera_activitat&limit=5`, { headers }).then(r => r.json()),
      fetch(`${API}/api/v1/alerts/summary/?dies=30`, { headers })
        .then(r => r.ok ? r.json() : Promise.reject(r))
        .catch(() => fetch(`${API}/api/v1/pom-alerts/?estat=Obert&limit=100`, { headers }).then(r => r.json())),
      fetch(`${API}/api/v1/me/`, { headers }).then(r => r.json()),
      fetch(`${API}/api/v1/onboarding-status/`, { headers }).then(r => r.ok ? r.json() : null),
    ]).then(([allRes, recentsRes, avisosRes, meRes, onbRes]) => {
      // Stats
      if (allRes.status === "fulfilled") {
        const all = allRes.value
        const items = Array.isArray(all) ? all : (all.results || [])
        const total = all.count || items.length
        const enCurs = items.filter(m => m.estat === "EnCurs").length
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
        const items = Array.isArray(d) ? d : (d.results || d.items || [])
        setAvisos(items)
        // New summary format (S11): { oberts, resolts, top_poms, ... }
        if (d && typeof d === 'object' && !Array.isArray(d) && (d.oberts != null || d.top_poms)) {
          setAvisosSummary(d)
        }
      }
      // Me
      if (meRes.status === "fulfilled") setMe(meRes.value)
      // Onboarding
      if (onbRes.status === "fulfilled" && onbRes.value) setOnboarding(onbRes.value)

      setLoading(false)
    })
  }, [token])

  const hora = new Date().getHours()
  const salutacio = hora < 13 ? t("dashboard.greeting_morning") : hora < 20 ? t("dashboard.greeting_afternoon") : t("dashboard.greeting_evening")

  return (
    <div style={{ padding: "24px", maxWidth: 1100, margin: "0 auto" }}>
      {/* Onboarding banner */}
      {onboarding && typeof onboarding.percentatge === 'number' && onboarding.percentatge < 100 && (
        <div
          onClick={() => navigate('/onboarding')}
          style={{
            marginBottom: 20, padding: '12px 16px',
            borderRadius: 8, background: '#fdf6ee',
            border: '1px solid #e0c8a0',
            display: 'flex', alignItems: 'center', gap: 14,
            cursor: 'pointer',
          }}
        >
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            background: '#f5e6d0', color: 'var(--gold)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 'var(--fs-body)', fontWeight: 600,
          }}>
            {onboarding.percentatge}%
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>
              {t('dashboard.onboarding_incomplete')}
            </div>
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginTop: 2 }}>
              {onboarding.passos_pendents
                ? t('dashboard.onboarding_steps_left', { count: onboarding.passos_pendents })
                : t('dashboard.onboarding_complete_setup')}
            </div>
          </div>
          <span style={{
            padding: '6px 12px', borderRadius: 6, fontSize: 'var(--fs-body)',
            background: 'var(--gold)', color: 'var(--white)', fontWeight: 500,
          }}>
            {t('dashboard.complete_setup')} →
          </span>
        </div>
      )}

      {/* Greeting */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, color: "var(--text-main)", margin: "0 0 4px" }}>
          {salutacio}{me ? `, ${me.full_name?.split(" ")[0] || me.username}` : ""}.
        </h1>
        <div style={{ fontSize: 'var(--fs-body)', color: "var(--text-muted)", fontFamily: "IBM Plex Mono, monospace" }}>
          {new Date().toLocaleDateString(i18n.language || "ca", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
        </div>
      </div>

      {/* KPIs */}
      <div style={{ display: "flex", gap: 12, marginBottom: 28, flexWrap: "wrap" }}>
        <KPICard
          label={t("dashboard.kpi.total_models")}
          value={loading ? "…" : stats.total}
          sub={t("dashboard.kpi_sub.in_system")}
          onClick={() => navigate("/models")}
        />
        <KPICard
          label={t("model.estats.EnCurs")}
          value={loading ? "…" : stats.enCurs}
          sub={t("dashboard.kpi_sub.active_models")}
          color="#3b7a9a"
          onClick={() => navigate("/models?estat=EnCurs")}
        />
        <KPICard
          label={t("dashboard.kpi.open_alerts")}
          value={loading ? "…" : avisos.length}
          sub={t("dashboard.kpi_sub.pom_deviations")}
          color={avisos.length > 0 ? "#a32d2d" : "var(--text-muted)"}
          onClick={() => navigate("/avisos")}
        />
        <KPICard
          label={t("dashboard.kpi.prototype_samples")}
          value={loading ? "…" : stats.tallesGen}
          sub={t("dashboard.kpi_sub.critical_phase")}
          color="#854f0b"
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20, alignItems: "start" }}>
        {/* Models recents */}
        <div>
          <div style={{
            fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".08em",
            textTransform: "uppercase", color: "var(--gold)",
            fontFamily: "IBM Plex Mono, monospace", marginBottom: 12,
          }}>
            {t("dashboard.recent_active_models")}
          </div>
          {loading ? (
            <div style={{ color: "var(--text-muted)", fontSize: 'var(--fs-body)', fontFamily: "IBM Plex Mono, monospace" }}>{t("common.loading")}</div>
          ) : recents.length === 0 ? (
            <div style={{
              padding: "20px", border: "1px dashed var(--border)", borderRadius: 8,
              textAlign: "center", color: "var(--text-muted)", fontSize: 'var(--fs-body)',
              fontFamily: "IBM Plex Mono, monospace",
            }}>
              {t("dashboard.no_models_in_progress")}{" "}
              <span
                onClick={() => navigate("/models/nou")}
                style={{ color: "var(--gold)", cursor: "pointer", textDecoration: "underline" }}
              >
                {t("dashboard.create_first")}
              </span>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {recents.map(m => (
                <div
                  key={m.id}
                  onClick={() => navigate(`/models/${m.id}`)}
                  style={{
                    border: "1px solid var(--border)", borderRadius: 8, padding: "12px 16px",
                    cursor: "pointer", background: "var(--white)",
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = "#fdf9f5"; e.currentTarget.style.borderColor = "var(--gold)" }}
                  onMouseLeave={e => { e.currentTarget.style.background = "var(--white)"; e.currentTarget.style.borderColor = "var(--border)" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <div>
                      <span style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 'var(--fs-body)', fontWeight: 700, color: "var(--gold)", marginRight: 10 }}>
                        {m.codi_intern || m.codi_client}
                      </span>
                      <span style={{ fontSize: 'var(--fs-body)', color: "var(--text-main)" }}>{m.nom_prenda}</span>
                    </div>
                    <EstatBadge estat={m.estat} size="xs" />
                  </div>
                  {m.fase_actual && (
                    <div style={{ transform: "scale(0.85)", transformOrigin: "left center" }}>
                      <PhaseStepper faseActual={m.fase_actual} />
                    </div>
                  )}
                </div>
              ))}
              <button
                onClick={() => navigate("/models")}
                style={{
                  padding: "8px", border: "1px dashed var(--border)", borderRadius: 8,
                  background: "none", color: "var(--gold)", cursor: "pointer",
                  fontFamily: "IBM Plex Mono, monospace", fontSize: 'var(--fs-body)',
                }}
              >
                {t("dashboard.see_all_models")} →
              </button>
            </div>
          )}
        </div>

        {/* Avisos */}
        <div>
          <div style={{
            fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".08em",
            textTransform: "uppercase", color: "var(--gold)",
            fontFamily: "IBM Plex Mono, monospace", marginBottom: 12,
          }}>
            {t("dashboard.pom_alerts")}
          </div>
          {avisosSummary && (
            <div style={{
              marginBottom: 10, padding: "8px 10px",
              border: "1px solid var(--border)", borderRadius: 6,
              background: "var(--white)", fontFamily: "IBM Plex Mono, monospace", fontSize: 'var(--fs-body)',
            }}>
              <div style={{ display: "flex", gap: 12, marginBottom: 6 }}>
                <span style={{ color: "#a32d2d" }}>● {t("dashboard.summary_open", { count: avisosSummary.oberts ?? 0 })}</span>
                <span style={{ color: "#3b6d11" }}>● {t("dashboard.summary_resolved", { count: avisosSummary.resolts ?? 0 })}</span>
                <span style={{ color: "var(--text-muted)" }}>· {t("dashboard.summary_days", { days: avisosSummary.dies ?? 30 })}</span>
              </div>
              {avisosSummary.top_poms?.length > 0 && (
                <div style={{ color: "var(--text-muted)", fontSize: 'var(--fs-label)' }}>
                  {t("dashboard.summary_top")}: {avisosSummary.top_poms.slice(0, 3).map(p =>
                    `${p.pom_codi || p.pom} (${p.count})`
                  ).join(" · ")}
                </div>
              )}
            </div>
          )}
          {loading ? (
            <div style={{ color: "var(--text-muted)", fontSize: 'var(--fs-body)', fontFamily: "IBM Plex Mono, monospace" }}>{t("common.loading")}</div>
          ) : avisos.length === 0 ? (
            <div style={{
              padding: "16px", border: "1px solid var(--border)", borderRadius: 8,
              textAlign: "center", color: "#3b6d11", fontSize: 'var(--fs-body)',
              fontFamily: "IBM Plex Mono, monospace", background: "#f0f9f0",
            }}>
              ✓ {t("dashboard.no_open_alerts")}
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
                    fontFamily: "IBM Plex Mono, monospace", fontSize: 'var(--fs-body)',
                  }}
                >
                  <div style={{ color: "#a32d2d", fontWeight: 500, marginBottom: 2 }}>
                    {a.pom_codi || a.pom} — {a.model_codi || a.model}
                  </div>
                  <div style={{ color: "var(--text-muted)" }}>{a.missatge || a.message || t("dashboard.deviation_detected")}</div>
                </div>
              ))}
              {avisos.length > 6 && (
                <button
                  onClick={() => navigate("/avisos")}
                  style={{
                    padding: "6px", border: "1px dashed #f09595", borderRadius: 6,
                    background: "none", color: "#a32d2d", cursor: "pointer",
                    fontFamily: "IBM Plex Mono, monospace", fontSize: 'var(--fs-body)',
                  }}
                >
                  +{t("dashboard.more_alerts", { count: avisos.length - 6 })} →
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
