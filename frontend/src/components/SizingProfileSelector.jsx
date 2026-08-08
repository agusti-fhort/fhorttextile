import { useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { SizeSetCard } from "./SizeSetCard"
import { sizingProfiles } from "../api/endpoints"
import { groupLabel } from "./grading/gradingAxes"
import { useEixos } from "./grading/eixosFont"
import TargetLabel from "./grading/TargetLabel"

// Els targets (ordre + etiquetes) surten del CATÀLEG de la BD (`/targets/`, ordenat per
// `display_order`) — fora la còpia TARGET_ORDER + la crida
// a targets/ (Onada 2). Les cerques de perfils van per CODI de target, no cal l'objecte de BD.

function LoadError({ onRetry, label }) {
  const { t } = useTranslation()
  return (
    <div style={{
      padding: "20px", border: "1px dashed #f0a0a0", borderRadius: 8,
      textAlign: "center", color: "#a32d2d", fontSize: 'var(--fs-body)', background: "#fff8f8",
    }}>
      {label || t("size_library.load_error")}
      <div style={{ marginTop: 10 }}>
        <button
          onClick={onRetry}
          style={{
            padding: "6px 14px", borderRadius: 4, cursor: "pointer",
            background: "var(--white)", color: "var(--gold)", border: "1px solid var(--gold)",
            fontFamily: "IBM Plex Mono, monospace", fontSize: 'var(--fs-body)',
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
  fontFamily: "IBM Plex Mono, monospace", fontSize: 'var(--fs-body)',
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
  const { t, i18n } = useTranslation()
  // ELS TRES EIXOS, D'UNA SOLA FONT. Aquesta pantalla ja anava a buscar construccions i fits pel
  // seu compte (dues peticions pròpies) i els targets se'ls escrivia amb una constant importada:
  // tres camins per a tres taules germanes del mateix catàleg. Ara és `useEixos()`, que memoritza
  // a nivell de mòdul — o sigui que això no afegeix cap petició, en treu dues.
  const { targets, constructions: catConstructions, fits: catFits, error: lookupsError,
          reintenta: recarregaEixos } = useEixos()
  const constructions = catConstructions || []
  const allFitTypes = catFits || []
  const [profiles, setProfiles] = useState([])
  const [loadingProfiles, setLoadingProfiles] = useState(false)

  const [selectedTarget, setSelectedTarget] = useState(initialTarget)
  const [selectedConstruction, setSelectedConstruction] = useState(null)
  const [selectedFit, setSelectedFit] = useState(null)
  // N2 — filtres que llegeixen les etiquetes del RUN (N1), no els eixos del perfil.
  const [selectedEscala, setSelectedEscala] = useState(null)
  const [selectedGrup, setSelectedGrup] = useState(null)

  const [profilesError, setProfilesError] = useState(false)

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

  // N2 — filtres del RUN (no del perfil): tipus d'escala i grup de peça. Client-side pel mateix
  // motiu que el de Fit: filtrar-los al servidor trencaria el faceting i faria desaparèixer els
  // altres chips. Els vocabularis són els mateixos de sempre; només canvia d'on surt el valor.
  const perfilsAmbFit = selectedFit
    ? profiles.filter(p => p.fit_type_codi === selectedFit)
    : profiles

  const escalesDisponibles = [...new Set(
    perfilsAmbFit.map(p => p.size_system?.tipus_escala).filter(Boolean))].sort()
  const grupsDisponibles = [...new Set(
    perfilsAmbFit.flatMap(p => p.size_system?.grup_codis || []))].sort()

  // Si el valor triat deixa d'existir per a la combinació, s'ignora. DERIVAT, no un reset dins
  // d'un efecte: el que val és el valor viu, i un `setState` en efecte només hi afegiria un
  // render en cascada per arribar al mateix lloc.
  const escalaActiva = escalesDisponibles.includes(selectedEscala) ? selectedEscala : null
  const grupActiu = grupsDisponibles.includes(selectedGrup) ? selectedGrup : null

  const visibleProfiles = perfilsAmbFit
    .filter(p => !escalaActiva || p.size_system?.tipus_escala === escalaActiva)
    .filter(p => !grupActiu || (p.size_system?.grup_codis || []).includes(grupActiu))

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
        <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--gold)", marginBottom: 10 }}>
          1 · {t("size_library.step_target")}
        </div>
        {/* Targets del vocabulari únic (estàtics): no depenen de cap càrrega. */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {(targets || []).map(tg => (
            <button
              key={tg.codi}
              onClick={() => pickTarget(tg.codi)}
              style={{
                ...chipBase, padding: "10px 14px", borderRadius: 6, fontSize: 'var(--fs-body)',
                background: selectedTarget === tg.codi ? "#f5e6d0" : "var(--white)",
                color: selectedTarget === tg.codi ? "var(--gold)" : "var(--text-main)",
                border: `1px solid ${selectedTarget === tg.codi ? "var(--gold)" : "var(--border)"}`,
                display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
                minWidth: 90,
              }}
            >
              <TargetLabel
                codi={tg.codi}
                nomFallback={tg.nom_en}
                fontWeight={selectedTarget === tg.codi ? 600 : 400}
              />
            </button>
          ))}
        </div>
      </div>

      {/* NIVELL 2 — Construction */}
      {selectedTarget && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--gold)", marginBottom: 10 }}>
            2 · {t("size_library.step_construction")}
          </div>
          {lookupsError && <LoadError onRetry={recarregaEixos} label={t("size_library.load_error")} />}
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
          <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--gold)", marginBottom: 10 }}>
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
            fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".08em",
            textTransform: "uppercase", color: "var(--gold)",
            marginBottom: 10, display: "flex", justifyContent: "space-between",
          }}>
            <span>{t("size_library.sizesets_available")}</span>
            <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>
              {loadingProfiles ? t("common.loading") : t("size_library.systems_count", { count: visibleProfiles.length })}
            </span>
          </div>
          {/* LLEI 5 CAPES: aclarir que això és la biblioteca de PRESETS de graduació (capa 4),
              no el selector de talles del model (escala pura, que viu al pas «Talles» del model). */}
          <div style={{ fontSize: 'var(--fs-caption)', color: "var(--text-muted)", marginBottom: 12, textTransform: "none", letterSpacing: "normal", fontWeight: 400 }}>
            {t("size_library.sizesets_help")}
          </div>

          {/* N2 — filtres del RUN. Només surten les capes que els runs d'aquesta combinació
              declaren: una fila de filtres amb un sol valor no filtra res i seria soroll. */}
          {(escalesDisponibles.length > 1 || grupsDisponibles.length > 1) && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 16, marginBottom: 14 }}>
              {escalesDisponibles.length > 1 && (
                <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 'var(--fs-caption)', color: "var(--text-muted)", textTransform: "none", letterSpacing: "normal", fontWeight: 400 }}>
                    {t("size_library.filter_scale")}
                  </span>
                  {escalesDisponibles.map(e => (
                    <button
                      key={e}
                      onClick={() => setSelectedEscala(escalaActiva === e ? null : e)}
                      style={{
                        ...chipBase, padding: "4px 10px", fontSize: 'var(--fs-label)',
                        background: escalaActiva === e ? "#f5e6d0" : "var(--white)",
                        color: escalaActiva === e ? "var(--gold)" : "var(--text-main)",
                        border: `1px solid ${escalaActiva === e ? "var(--gold)" : "var(--border)"}`,
                      }}
                    >
                      {t(`size_library.scale_${e}`, e)}
                    </button>
                  ))}
                </div>
              )}
              {grupsDisponibles.length > 1 && (
                <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 'var(--fs-caption)', color: "var(--text-muted)", textTransform: "none", letterSpacing: "normal", fontWeight: 400 }}>
                    {t("size_library.filter_group")}
                  </span>
                  {grupsDisponibles.map(g => (
                    <button
                      key={g}
                      onClick={() => setSelectedGrup(grupActiu === g ? null : g)}
                      style={{
                        ...chipBase, padding: "4px 10px", fontSize: 'var(--fs-label)',
                        background: grupActiu === g ? "#f5e6d0" : "var(--white)",
                        color: grupActiu === g ? "var(--gold)" : "var(--text-main)",
                        border: `1px solid ${grupActiu === g ? "var(--gold)" : "var(--border)"}`,
                      }}
                    >
                      {groupLabel(g, i18n.language) || g}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {profilesError ? (
            <LoadError onRetry={loadProfiles} label={t("size_library.load_error_sizesets")} />
          ) : loadingProfiles ? (
            <div style={{ color: "var(--text-muted)", fontSize: 'var(--fs-body)', padding: "20px 0" }}>
              {t("size_library.loading_sizesets")}
            </div>
          ) : visibleProfiles.length === 0 ? (
            <div style={{
              padding: "20px", border: "1px dashed var(--border)", borderRadius: 8,
              textAlign: "center", color: "var(--text-muted)", fontSize: 'var(--fs-body)',
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
          textAlign: "center", color: "var(--text-muted)", fontSize: 'var(--fs-body)',
        }}>
          {t("size_library.select_target_hint")}
        </div>
      )}
    </div>
  )
}
