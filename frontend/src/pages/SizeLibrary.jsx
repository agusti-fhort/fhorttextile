
import { useState, useEffect } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import useAuthStore from "../store/auth"
import { SizeSetCard } from "../components/SizeSetCard"
import { SizeSetDetail } from "../components/SizeSetDetail"

const API = import.meta.env.VITE_API_URL || ""

// Icones de text per a cada target
const TARGET_ICONS = {
  WOMAN: "♀", MAN: "♂", UNISEX_ADULT: "◎",
  BABY_GIRL: "♀°", BABY_BOY: "♂°", BABY_UNISEX: "◉",
  TODDLER_GIRL: "♀¹", TODDLER_BOY: "♂¹",
  GIRL: "♀²", BOY: "♂²",
  TEEN_GIRL: "♀³", TEEN_BOY: "♂³",
  MATERNITY: "♀♥",
}

const TARGET_ORDER = [
  "WOMAN","MAN","UNISEX_ADULT",
  "BABY_GIRL","BABY_BOY","BABY_UNISEX",
  "TODDLER_GIRL","TODDLER_BOY",
  "GIRL","BOY","TEEN_GIRL","TEEN_BOY","MATERNITY"
]

export default function SizeLibrary() {
  const navigate = useNavigate()
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const [searchParams, setSearchParams] = useSearchParams()

  const [targets, setTargets] = useState([])
  const [constructions, setConstructions] = useState([])
  const [profiles, setProfiles] = useState([])
  const [loadingProfiles, setLoadingProfiles] = useState(false)

  const [selectedTarget, setSelectedTarget] = useState(searchParams.get('target') || null)
  const [selectedConstruction, setSelectedConstruction] = useState(searchParams.get('construction') || null)
  const [detailProfileId, setDetailProfileId] = useState(null)
  const [msg, setMsg] = useState(null)

  // Carregar targets i construccions
  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` }

    fetch(`${API}/api/v1/targets/`, { headers })
      .then(r => r.json())
      .then(d => {
        const all = Array.isArray(d) ? d : (d.results || [])
        const sorted = TARGET_ORDER
          .map(codi => all.find(t => t.codi === codi))
          .filter(Boolean)
        setTargets(sorted)
      })
      .catch(() => {
        // Mock si API no disponible
        setTargets([
          { id: 1, codi: "WOMAN", nom_en: "Woman", nom_cat: "Dona", display_order: 1 },
          { id: 2, codi: "MAN", nom_en: "Man", nom_cat: "Home", display_order: 2 },
          { id: 4, codi: "BABY_GIRL", nom_en: "Baby Girl", nom_cat: "Nadó nena", display_order: 4 },
          { id: 5, codi: "BABY_BOY", nom_en: "Baby Boy", nom_cat: "Nadó nen", display_order: 5 },
          { id: 9, codi: "GIRL", nom_en: "Girl", nom_cat: "Nena", display_order: 9 },
          { id: 10, codi: "BOY", nom_en: "Boy", nom_cat: "Nen", display_order: 10 },
          { id: 11, codi: "TEEN_GIRL", nom_en: "Teen Girl", nom_cat: "Teen nena", display_order: 11 },
        ])
      })

    fetch(`${API}/api/v1/construction-types/`, { headers })
      .then(r => r.json())
      .then(d => setConstructions(Array.isArray(d) ? d : (d.results || [])))
      .catch(() => {
        setConstructions([
          { id: 1, codi: "WOVEN", nom_en: "Woven", nom_cat: "Teixit pla" },
          { id: 2, codi: "KNIT", nom_en: "Knit", nom_cat: "Punt jersey" },
          { id: 3, codi: "STRETCH_KNIT", nom_en: "Stretch Knit", nom_cat: "Punt elàstic" },
          { id: 4, codi: "TECHNICAL", nom_en: "Technical", nom_cat: "Tècnic" },
        ])
      })
  }, [token])

  // Carregar profiles quan canvia selecció
  useEffect(() => {
    if (!selectedTarget) { setProfiles([]); return }
    setLoadingProfiles(true)
    const params = new URLSearchParams({ target: selectedTarget })
    if (selectedConstruction) params.set('construction', selectedConstruction)

    fetch(`${API}/api/v1/sizing-profiles/?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => {
        setProfiles(Array.isArray(d) ? d : (d.results || []))
        setLoadingProfiles(false)
      })
      .catch(() => {
        // Mock data
        setProfiles([
          {
            id: 1,
            size_system: { id: 1, codi: "ALPHA_EU_W", nom: "Alpha EU — Women", base_unit: "ALPHA", norma_ref: "ISO 8559-2" },
            target: { id: 1, codi: selectedTarget, nom_en: targets.find(t => t.codi === selectedTarget)?.nom_en || selectedTarget },
            construction: { id: 1, codi: selectedConstruction || "KNIT", nom_en: "Knit" },
            fit_type_nom: "Regular",
            grading_rule_set: { id: 1, nom: "EU Knit Woman Regular", codi_sistema: "EU_KNIT_WOMAN_REGULAR", is_system_default: true, version_number: 1 },
            is_default: true, is_custom: false, version: 1,
            size_definitions: [
              { size_label: "XXS" },{ size_label: "XS" },{ size_label: "S" },
              { size_label: "M" },{ size_label: "L" },{ size_label: "XL" },{ size_label: "XXL" }
            ],
            grading_rules_preview: [
              { pom_codi: "POM-001", pom_nom_en: "Chest width", logica: "LINEAR", increment: 2.0 },
              { pom_codi: "POM-003", pom_nom_en: "Waist width", logica: "LINEAR", increment: 1.5 },
              { pom_codi: "POM-004", pom_nom_en: "Hip width", logica: "LINEAR", increment: 2.0 },
            ]
          }
        ])
        setLoadingProfiles(false)
      })
  }, [selectedTarget, selectedConstruction, token])

  const handleClone = async (profile) => {
    try {
      const r = await fetch(`${API}/api/v1/sizing-profiles/${profile.id}/clonar/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ nom_client: `Custom ${profile.size_system?.nom}` }),
      })
      const d = await r.json()
      if (r.ok) {
        setMsg({ type: 'ok', text: d.missatge })
        // Recarregar perfils
        setSelectedConstruction(c => c)
      } else {
        setMsg({ type: 'error', text: d.error })
      }
    } catch (e) {
      setMsg({ type: 'error', text: String(e) })
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
                    padding: "8px 14px", borderRadius: 6, cursor: "pointer",
                    background: selectedTarget === t.codi ? "#f5e6d0" : "#fff",
                    color: selectedTarget === t.codi ? "#c27a2a" : "#1d1d1b",
                    border: `1px solid ${selectedTarget === t.codi ? "#c27a2a" : "#e0d5c5"}`,
                    fontFamily: "IBM Plex Mono, monospace", fontSize: 12,
                    display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
                    minWidth: 80,
                  }}
                >
                  <span style={{ fontSize: 16 }}>{TARGET_ICONS[t.codi] || "◆"}</span>
                  <span style={{ fontWeight: selectedTarget === t.codi ? 600 : 400 }}>{t.nom_en}</span>
                  <span style={{ fontSize: 9, color: selectedTarget === t.codi ? "#c27a2a" : "#868685" }}>{t.nom_cat}</span>
                </button>
              ))}
            </div>
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

              {loadingProfiles ? (
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
