import { useState, useEffect } from "react"
import { SizeSetCard } from "./SizeSetCard"
import { targets as targetsApi, constructionTypes, fitTypes, sizingProfiles } from "../api/endpoints"

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

const chipBase = {
  padding: "6px 14px", borderRadius: 4, cursor: "pointer",
  fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
}

/**
 * Selector reutilitzable del domini de talles: Target → Construcció → Fit → Size Sets.
 * El filtre de Fit és CLIENT-side (deriva els chips dels perfils carregats; filtrar al
 * servidor trencaria el faceting fent desaparèixer els altres chips).
 *
 * Props:
 *   onSelect(profile)        — callback "Usar" (només si selectable)
 *   initialTarget            — codi de target per preseleccionar
 *   customerCodi             — ordena runs d'aquest client primer
 *   selectable (false)       — mostra el botó "Usar" a les cards
 *   compact (false)          — es passa a SizeSetCard
 *   onDetail(profile)        — obre el detall (opcional)
 *   onClone(profile)         — clona; el selector recarrega després (opcional)
 *   onSelectionChange()      — es crida en canviar target/construcció (opcional)
 */
export function SizingProfileSelector({
  onSelect,
  initialTarget = null,
  customerCodi,
  selectable = false,
  compact = false,
  onDetail,
  onClone,
  onSelectionChange,
}) {
  const [targets, setTargets] = useState([])
  const [constructions, setConstructions] = useState([])
  const [allFitTypes, setAllFitTypes] = useState([])
  const [profiles, setProfiles] = useState([])
  const [loadingProfiles, setLoadingProfiles] = useState(false)

  const [selectedTarget, setSelectedTarget] = useState(initialTarget)
  const [selectedConstruction, setSelectedConstruction] = useState(null)
  const [selectedFit, setSelectedFit] = useState(null)

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

    // FitTypes del catàleg complet (no bloquejant: si falla, no hi ha chips Fit).
    fitTypes.list()
      .then(({ data: d }) => setAllFitTypes(Array.isArray(d) ? d : (d.results || [])))
      .catch(() => {})
  }

  useEffect(() => { loadLookups() }, [])

  // Carrega perfils per target+construcció (SENSE fit: el filtre de Fit és client-side).
  const loadProfiles = () => {
    if (!selectedTarget) { setProfiles([]); return }
    setLoadingProfiles(true)
    setProfilesError(false)
    const params = { target: selectedTarget }
    if (selectedConstruction) params.construction = selectedConstruction
    if (customerCodi) params.customer_codi = customerCodi

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

  // Fits amb perfils per a la combinació actual (la resta del catàleg surt en fade).
  const activeFitCodis = new Set(profiles.map(p => p.fit_type_codi).filter(Boolean))

  // Si el fit seleccionat ja no té perfils per a la combinació, reset.
  useEffect(() => {
    if (selectedFit && !activeFitCodis.has(selectedFit)) setSelectedFit(null)
  }, [profiles])  // eslint-disable-line react-hooks/exhaustive-deps

  const visibleProfiles = selectedFit
    ? profiles.filter(p => p.fit_type_codi === selectedFit)
    : profiles

  const pickTarget = (codi) => {
    setSelectedTarget(codi === selectedTarget ? null : codi)
    setSelectedConstruction(null)
    setSelectedFit(null)
    onSelectionChange && onSelectionChange()
  }

  const pickConstruction = (codi) => {
    setSelectedConstruction(codi === selectedConstruction ? null : codi)
    setSelectedFit(null)
    onSelectionChange && onSelectionChange()
  }

  // Clonar: delega al pare i recarrega els perfils del selector.
  const handleCardClone = onClone
    ? async (profile) => { await onClone(profile); loadProfiles() }
    : undefined

  return (
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
                onClick={() => pickTarget(t.codi)}
                style={{
                  ...chipBase, padding: "10px 14px", borderRadius: 6, fontSize: 12,
                  background: selectedTarget === t.codi ? "#f5e6d0" : "#fff",
                  color: selectedTarget === t.codi ? "#c27a2a" : "#1d1d1b",
                  border: `1px solid ${selectedTarget === t.codi ? "#c27a2a" : "#e0d5c5"}`,
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
              onClick={() => pickConstruction(selectedConstruction)}
              style={{
                ...chipBase,
                background: !selectedConstruction ? "#f5e6d0" : "#fff",
                color: !selectedConstruction ? "#c27a2a" : "#868685",
                border: `1px solid ${!selectedConstruction ? "#c27a2a" : "#e0d5c5"}`,
              }}
            >
              Tots
            </button>
            {constructions.map(c => (
              <button
                key={c.codi}
                onClick={() => pickConstruction(c.codi)}
                style={{
                  ...chipBase,
                  background: selectedConstruction === c.codi ? "#f5e6d0" : "#fff",
                  color: selectedConstruction === c.codi ? "#c27a2a" : "#1d1d1b",
                  border: `1px solid ${selectedConstruction === c.codi ? "#c27a2a" : "#e0d5c5"}`,
                }}
              >
                {c.nom_en}
                <span style={{ fontSize: 10, color: "#868685", marginLeft: 4 }}>{c.nom_cat}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* NIVELL 3 — Fit: catàleg complet; fade (no clicable) els sense perfils per a la combinació */}
      {selectedTarget && allFitTypes.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "#c27a2a", marginBottom: 10 }}>
            3 · Fit — caiguda de la peça
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              onClick={() => setSelectedFit(null)}
              style={{
                ...chipBase,
                background: !selectedFit ? "#f5e6d0" : "#fff",
                color: !selectedFit ? "#c27a2a" : "#868685",
                border: `1px solid ${!selectedFit ? "#c27a2a" : "#e0d5c5"}`,
              }}
            >
              Tots
            </button>
            {allFitTypes.map(ft => {
              const isActive = activeFitCodis.has(ft.codi)
              const isSel = selectedFit === ft.codi
              return (
                <button
                  key={ft.codi}
                  onClick={isActive ? () => setSelectedFit(isSel ? null : ft.codi) : undefined}
                  title={isActive ? undefined : "Sense perfils per a aquesta combinació"}
                  style={{
                    ...chipBase,
                    background: isSel ? "#f5e6d0" : "#fff",
                    color: isSel ? "#c27a2a" : "#1d1d1b",
                    border: `1px solid ${isSel ? "#c27a2a" : "#e0d5c5"}`,
                    ...(!isActive ? { opacity: 0.35, cursor: "default", pointerEvents: "none" } : {}),
                  }}
                >
                  {ft.nom_en}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* NIVELL 4 — Size Sets */}
      {selectedTarget && (
        <div>
          <div style={{
            fontSize: 10, fontWeight: 600, letterSpacing: ".08em",
            textTransform: "uppercase", color: "#c27a2a",
            marginBottom: 10, display: "flex", justifyContent: "space-between",
          }}>
            <span>Size Sets disponibles</span>
            <span style={{ color: "#868685", fontWeight: 400 }}>
              {loadingProfiles ? "Carregant..." : `${visibleProfiles.length} sistemes`}
            </span>
          </div>

          {profilesError ? (
            <LoadError onRetry={loadProfiles} label="No s'han pogut carregar els size sets" />
          ) : loadingProfiles ? (
            <div style={{ color: "#868685", fontSize: 12, padding: "20px 0" }}>
              Carregant size sets...
            </div>
          ) : visibleProfiles.length === 0 ? (
            <div style={{
              padding: "20px", border: "1px dashed #e0d5c5", borderRadius: 8,
              textAlign: "center", color: "#868685", fontSize: 12,
            }}>
              Sense size sets per a aquesta combinació.
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 12 }}>
              {visibleProfiles.map(p => (
                <SizeSetCard
                  key={p.id}
                  profile={p}
                  compact={compact}
                  onUse={selectable && onSelect ? onSelect : undefined}
                  onDetail={onDetail}
                  onClone={handleCardClone}
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
  )
}
