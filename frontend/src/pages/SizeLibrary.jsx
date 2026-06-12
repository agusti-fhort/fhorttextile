
import { useState, useEffect } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { SizeSetCard } from "../components/SizeSetCard"
import { SizeSetDetail } from "../components/SizeSetDetail"
import { targets as targetsApi, constructionTypes, sizingProfiles } from "../api/endpoints"

const TARGET_ORDER = [
  "WOMAN","MAN","UNISEX_ADULT",
  "BABY_GIRL","BABY_BOY","BABY_UNISEX",
  "TODDLER_GIRL","TODDLER_BOY",
  "GIRL","BOY","TEEN_GIRL","TEEN_BOY","MATERNITY"
]

function LoadError({ onRetry, label = "No s'han pogut carregar les dades" }) {
  return (
    <div style={{
      padding: "20px", border: "1px dashed #f0a0a0", borderRadius: 8,
      textAlign: "center", color: "#a32d2d", fontSize: 12, background: "#fff8f8",
    }}>
      {label}
      <div style={{ marginTop: 10 }}>
        <button
          onClick={onRetry}
          style={{
            padding: "6px 14px", borderRadius: 4, cursor: "pointer",
            background: "#fff", color: "#c27a2a", border: "1px solid #c27a2a",
            fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
          }}
        >
          ↺ Reintentar
        </button>
      </div>
    </div>
  )
}

export default function SizeLibrary() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [targets, setTargets] = useState([])
  const [constructions, setConstructions] = useState([])
  const [profiles, setProfiles] = useState([])
  const [loadingProfiles, setLoadingProfiles] = useState(false)

  const [selectedTarget, setSelectedTarget] = useState(searchParams.get('target') || null)
  const [selectedConstruction, setSelectedConstruction] = useState(searchParams.get('construction') || null)
  const [detailProfileId, setDetailProfileId] = useState(null)
  const [msg, setMsg] = useState(null)

  // Errors de càrrega — si la API falla es mostra l'error real + Reintentar, mai dades falses.
  const [lookupsError, setLookupsError] = useState(false)
  const [profilesError, setProfilesError] = useState(false)

  // Carregar targets i construccions
  const loadLookups = () => {
    setLookupsError(false)
    targetsApi.list()
      .then(({ data: d }) => {
        const all = Array.isArray(d) ? d : (d.results || [])
        const sorted = TARGET_ORDER
          .map(codi => all.find(t => t.codi === codi))
          .filter(Boolean)
        setTargets(sorted)
      })
      .catch(() => setLookupsError(true))

    constructionTypes.list()
      .then(({ data: d }) => setConstructions(Array.isArray(d) ? d : (d.results || [])))
      .catch(() => setLookupsError(true))
  }

  useEffect(() => { loadLookups() }, [])

  // Load profiles when the selection changes
  const loadProfiles = () => {
    if (!selectedTarget) { setProfiles([]); return }
    setLoadingProfiles(true)
    setProfilesError(false)
    const params = { target: selectedTarget }
    if (selectedConstruction) params.construction = selectedConstruction

    sizingProfiles.list(params)
      .then(({ data: d }) => {
        setProfiles(Array.isArray(d) ? d : (d.results || []))
        setLoadingProfiles(false)
      })
      .catch(() => {
        setProfiles([])
        setProfilesError(true)
        setLoadingProfiles(false)
      })
  }

  useEffect(() => { loadProfiles() }, [selectedTarget, selectedConstruction])

  const handleClone = async (profile) => {
    try {
      const { data: d } = await sizingProfiles.clone(profile.id, { nom_client: `Custom ${profile.size_system?.nom}` })
      setMsg({ type: 'ok', text: d?.missatge })
      loadProfiles()   // recarregar perfils
    } catch (e) {
      if (e.response) {
        setMsg({ type: 'error', text: e.response.data?.error || 'Error clonant el perfil' })
      } else {
        setMsg({ type: 'error', text: String(e) })
      }
    }
  }

  return (
    <div style={{ padding: "24px", maxWidth: 1100, margin: "0 auto", fontFamily: "IBM Plex Mono, monospace" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 18, fontWeight: 500, color: "#1d1d1b", margin: "0 0 4px" }}>
          Size Library
        </h1>
        <div style={{ fontSize: 12, color: "#868685" }}>
          Sistemes de talles, runs i grading disponibles per al teu catàleg.
        </div>
      </div>

      {/* Missatge global */}
      {msg && (
        <div style={{
          padding: "8px 12px", marginBottom: 16, borderRadius: 4, fontSize: 11,
          background: msg.type === 'ok' ? "#f0f9f0" : "#fff0f0",
          border: `1px solid ${msg.type === 'ok' ? "#c0dd97" : "#f09595"}`,
          color: msg.type === 'ok' ? "#3b6d11" : "#a32d2d",
          display: "flex", justifyContent: "space-between",
        }}>
          {msg.text}
          <button onClick={() => setMsg(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "inherit" }}>×</button>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: detailProfileId ? "1fr 420px" : "1fr", gap: 24, alignItems: "start" }}>
        <div>
          {/* NIVELL 1 — Target */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "#c27a2a", marginBottom: 10 }}>
              1 · Target — per a qui és la peça?
            </div>
            {lookupsError ? (
              <LoadError onRetry={loadLookups} />
            ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {targets.map(t => (
                <button
                  key={t.codi}
                  onClick={() => {
                    setSelectedTarget(t.codi === selectedTarget ? null : t.codi)
                    setSelectedConstruction(null)
                    setDetailProfileId(null)
                  }}
                  style={{
                    padding: "10px 14px", borderRadius: 6, cursor: "pointer",
                    background: selectedTarget === t.codi ? "#f5e6d0" : "#fff",
                    color: selectedTarget === t.codi ? "#c27a2a" : "#1d1d1b",
                    border: `1px solid ${selectedTarget === t.codi ? "#c27a2a" : "#e0d5c5"}`,
                    fontFamily: "IBM Plex Mono, monospace", fontSize: 12,
                    display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
                    minWidth: 90,
                  }}
                >
                  <span style={{ fontWeight: selectedTarget === t.codi ? 600 : 400 }}>{t.nom_en}</span>
                  <span style={{ fontSize: 9, color: selectedTarget === t.codi ? "#c27a2a" : "#868685" }}>{t.nom_cat}</span>
                </button>
              ))}
            </div>
            )}
          </div>

          {/* NIVELL 2 — Construction */}
          {selectedTarget && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "#c27a2a", marginBottom: 10 }}>
                2 · Construcció — tipus de teixit
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  onClick={() => setSelectedConstruction(null)}
                  style={{
                    padding: "6px 14px", borderRadius: 4, cursor: "pointer",
                    background: !selectedConstruction ? "#f5e6d0" : "#fff",
                    color: !selectedConstruction ? "#c27a2a" : "#868685",
                    border: `1px solid ${!selectedConstruction ? "#c27a2a" : "#e0d5c5"}`,
                    fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
                  }}
                >
                  Tots
                </button>
                {constructions.map(c => (
                  <button
                    key={c.codi}
                    onClick={() => setSelectedConstruction(c.codi === selectedConstruction ? null : c.codi)}
                    style={{
                      padding: "6px 14px", borderRadius: 4, cursor: "pointer",
                      background: selectedConstruction === c.codi ? "#f5e6d0" : "#fff",
                      color: selectedConstruction === c.codi ? "#c27a2a" : "#1d1d1b",
                      border: `1px solid ${selectedConstruction === c.codi ? "#c27a2a" : "#e0d5c5"}`,
                      fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
                    }}
                  >
                    {c.nom_en}
                    <span style={{ fontSize: 10, color: "#868685", marginLeft: 4 }}>{c.nom_cat}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* NIVELL 3 — Size Sets */}
          {selectedTarget && (
            <div>
              <div style={{
                fontSize: 10, fontWeight: 600, letterSpacing: ".08em",
                textTransform: "uppercase", color: "#c27a2a",
                marginBottom: 10, display: "flex", justifyContent: "space-between",
              }}>
                <span>3 · Size Sets disponibles</span>
                <span style={{ color: "#868685", fontWeight: 400 }}>
                  {loadingProfiles ? "Carregant..." : `${profiles.length} sistemes`}
                </span>
              </div>

              {profilesError ? (
                <LoadError onRetry={loadProfiles} label="No s'han pogut carregar els size sets" />
              ) : loadingProfiles ? (
                <div style={{ color: "#868685", fontSize: 12, padding: "20px 0" }}>
                  Carregant size sets...
                </div>
              ) : profiles.length === 0 ? (
                <div style={{
                  padding: "20px", border: "1px dashed #e0d5c5", borderRadius: 8,
                  textAlign: "center", color: "#868685", fontSize: 12,
                }}>
                  Sense size sets per a aquesta combinació.
                  <br />
                  Executa el seed data (S1b) per carregar els estàndards ISO.
                </div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 12 }}>
                  {profiles.map(p => (
                    <SizeSetCard
                      key={p.id}
                      profile={p}
                      onDetail={(profile) => setDetailProfileId(profile.id)}
                      onClone={handleClone}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {!selectedTarget && (
            <div style={{
              padding: "40px 24px", border: "1px dashed #e0d5c5", borderRadius: 8,
              textAlign: "center", color: "#868685", fontSize: 12,
            }}>
              Selecciona un target per veure els size sets disponibles
            </div>
          )}
        </div>

        {/* Panel de detall */}
        {detailProfileId && (
          <div style={{
            border: "1px solid #e0d5c5", borderRadius: 8,
            padding: "16px", background: "#fdf9f5",
            position: "sticky", top: 24,
            maxHeight: "calc(100vh - 120px)", overflowY: "auto",
          }}>
            <SizeSetDetail
              profileId={detailProfileId}
              onClose={() => setDetailProfileId(null)}
            />
          </div>
        )}
      </div>
    </div>
  )
}
