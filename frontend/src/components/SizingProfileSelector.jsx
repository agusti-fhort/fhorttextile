import { useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { SizeSetCard } from "./SizeSetCard"
import { targets as targetsApi, constructionTypes, fitTypes, sizingProfiles } from "../api/endpoints"

const TARGET_ORDER = [
  "WOMAN","MAN","UNISEX_ADULT",
  "BABY_GIRL","BABY_BOY","BABY_UNISEX",
  "TODDLER_GIRL","TODDLER_BOY",
  "GIRL","BOY","TEEN_GIRL","TEEN_BOY","MATERNITY"
]

function LoadError({ onRetry, label }) {
  const { t } = useTranslation()
  return (
    <div style={{
      padding: "20px", border: "1px dashed #f0a0a0", borderRadius: 8,
      textAlign: "center", color: "#a32d2d", fontSize: 12, background: "#fff8f8",
    }}>
      {label || t("size_library.load_error")}
      <div style={{ marginTop: 10 }}>
        <button
          onClick={onRetry}
          style={{
            padding: "6px 14px", borderRadius: 4, cursor: "pointer",
            background: "var(--white)", color: "var(--gold)", border: "1px solid var(--gold)",
            fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
          }}
        >
          ↺ {t("size_library.retry")}
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
  const { t } = useTranslation()
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
        <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--gold)", marginBottom: 10 }}>
          1 · {t("size_library.step_target")}
        </div>
        {lookupsError ? (
          <LoadError onRetry={loadLookups} />
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {targets.map(tg => (
              <button
                key={tg.codi}
                onClick={() => pickTarget(tg.codi)}
                style={{
                  ...chipBase, padding: "10px 14px", borderRadius: 6, fontSize: 12,
                  background: selectedTarget === tg.codi ? "#f5e6d0" : "var(--white)",
                  color: selectedTarget === tg.codi ? "var(--gold)" : "var(--text-main)",
                  border: `1px solid ${selectedTarget === tg.codi ? "var(--gold)" : "var(--border)"}`,
                  display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
                  minWidth: 90,
                }}
              >
                <span style={{ fontWeight: selectedTarget === tg.codi ? 600 : 400 }}>{t(`model_wizard.target_${tg.codi}`, tg.nom_en)}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* NIVELL 2 — Construction */}
      {selectedTarget && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--gold)", marginBottom: 10 }}>
            2 · {t("size_library.step_construction")}
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              onClick={() => pickConstruction(selectedConstruction)}
              style={{
                ...chipBase,
                background: !selectedConstruction ? "#f5e6d0" : "var(--white)",
                color: !selectedConstruction ? "var(--gold)" : "var(--text-muted)",
                border: `1px solid ${!selectedConstruction ? "var(--gold)" : "var(--border)"}`,
              }}
            >
              {t("size_library.all")}
            </button>
            {constructions.map(c => (
              <button
                key={c.codi}
                onClick={() => pickConstruction(c.codi)}
                style={{
                  ...chipBase,
                  background: selectedConstruction === c.codi ? "#f5e6d0" : "var(--white)",
                  color: selectedConstruction === c.codi ? "var(--gold)" : "var(--text-main)",
                  border: `1px solid ${selectedConstruction === c.codi ? "var(--gold)" : "var(--border)"}`,
                }}
              >
                {t(`model_wizard.construction_${c.codi}`, c.nom_en)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* NIVELL 3 — Fit: catàleg complet; fade (no clicable) els sense perfils per a la combinació */}
      {selectedTarget && allFitTypes.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--gold)", marginBottom: 10 }}>
            3 · {t("size_library.step_fit")}
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              onClick={() => setSelectedFit(null)}
              style={{
                ...chipBase,
                background: !selectedFit ? "#f5e6d0" : "var(--white)",
                color: !selectedFit ? "var(--gold)" : "var(--text-muted)",
                border: `1px solid ${!selectedFit ? "var(--gold)" : "var(--border)"}`,
              }}
            >
              {t("size_library.all")}
            </button>
            {allFitTypes.map(ft => {
              const isActive = activeFitCodis.has(ft.codi)
              const isSel = selectedFit === ft.codi
              return (
                <button
                  key={ft.codi}
                  onClick={isActive ? () => setSelectedFit(isSel ? null : ft.codi) : undefined}
                  title={isActive ? undefined : t("size_library.fit_no_profiles")}
                  style={{
                    ...chipBase,
                    background: isSel ? "#f5e6d0" : "var(--white)",
                    color: isSel ? "var(--gold)" : "var(--text-main)",
                    border: `1px solid ${isSel ? "var(--gold)" : "var(--border)"}`,
                    ...(!isActive ? { opacity: 0.35, cursor: "default", pointerEvents: "none" } : {}),
                  }}
                >
                  {t(`model_wizard.fit_${ft.codi}`, ft.nom_en)}
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
            textTransform: "uppercase", color: "var(--gold)",
            marginBottom: 10, display: "flex", justifyContent: "space-between",
          }}>
            <span>{t("size_library.sizesets_available")}</span>
            <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>
              {loadingProfiles ? t("common.loading") : t("size_library.systems_count", { count: visibleProfiles.length })}
            </span>
          </div>

          {profilesError ? (
            <LoadError onRetry={loadProfiles} label={t("size_library.load_error_sizesets")} />
          ) : loadingProfiles ? (
            <div style={{ color: "var(--text-muted)", fontSize: 12, padding: "20px 0" }}>
              {t("size_library.loading_sizesets")}
            </div>
          ) : visibleProfiles.length === 0 ? (
            <div style={{
              padding: "20px", border: "1px dashed var(--border)", borderRadius: 8,
              textAlign: "center", color: "var(--text-muted)", fontSize: 12,
            }}>
              {t("size_library.empty_combination")}
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
          padding: "40px 24px", border: "1px dashed var(--border)", borderRadius: 8,
          textAlign: "center", color: "var(--text-muted)", fontSize: 12,
        }}>
          {t("size_library.select_target_hint")}
        </div>
      )}
    </div>
  )
}
