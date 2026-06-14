
import { useState } from "react"
import useAuthStore from "../store/auth"

const API = import.meta.env.VITE_API_URL || ""

export function SizeSetCard({ profile, onUse, onDetail, onClone, compact = false }) {
  const [cloning, setCloning] = useState(false)

  const sysName = profile?.size_system?.nom || "—"
  const sysUnit = profile?.size_system?.base_unit || ""
  const sizes = profile?.size_definitions || []
  const baseSize = sizes.find((_, i) => i === Math.floor(sizes.length / 2))?.size_label
  const rules = profile?.grading_rules_preview || []
  const isCustom = profile?.is_custom
  const isDefault = profile?.is_default
  const name = profile?.grading_rule_set?.nom || sysName

  const handleClone = async () => {
    if (!onClone) return
    setCloning(true)
    await onClone(profile)
    setCloning(false)
  }

  return (
    <div style={{
      border: `1px solid ${isCustom ? "#c27a2a" : "#e0d5c5"}`,
      borderRadius: 8, padding: "16px 18px",
      background: "#fff", fontFamily: "IBM Plex Mono, monospace",
      transition: "box-shadow .15s",
    }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = "0 2px 8px rgba(194,122,42,.12)"}
      onMouseLeave={e => e.currentTarget.style.boxShadow = "none"}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#1d1d1b" }}>{name}</div>
          {!compact && (
            <div style={{ fontSize: 11, color: "#868685", marginTop: 2 }}>
              {name !== sysName && <>{sysName} · </>}
              {profile?.target?.nom_en} · {profile?.construction?.nom_en} · {profile?.fit_type_nom}
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
          {isCustom ? (
            <span style={{
              padding: "2px 8px", borderRadius: 3, fontSize: 10,
              background: "#f5e6d0", color: "#c27a2a", border: "1px solid #e0c8a0",
            }}>Personalitzat</span>
          ) : (
            <span style={{
              padding: "2px 8px", borderRadius: 3, fontSize: 10,
              background: "#f0f9f0", color: "#3b6d11", border: "1px solid #c0dd97",
            }}>Estàndard ISO</span>
          )}
        </div>
      </div>

      {/* Size run */}
      {sizes.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 10 }}>
          {sizes.map((s, i) => {
            const isBase = s.size_label === baseSize
            return (
              <span key={i} style={{
                padding: "3px 9px", borderRadius: 4, fontSize: 11,
                background: isBase ? "#f5e6d0" : "#f5f0ea",
                color: isBase ? "#c27a2a" : "#1d1d1b",
                border: `1px solid ${isBase ? "#c27a2a" : "#e0d5c5"}`,
                fontWeight: isBase ? 600 : 400,
              }}>
                {s.size_label}{isBase ? " ★" : ""}
              </span>
            )
          })}
        </div>
      )}

      {/* Preview grading */}
      {!compact && rules.length > 0 && (
        <div style={{
          fontSize: 10, color: "#868685", marginBottom: 12,
          padding: "6px 8px", background: "#fdf9f5", borderRadius: 4,
          border: "1px solid #f0e8d8", lineHeight: 1.8,
        }}>
          {rules.map((r, i) => (
            <span key={i}>
              {r.pom_codi} <span style={{ color: "#c27a2a" }}>+{r.increment}cm</span>
              {i < rules.length - 1 ? " · " : ""}
            </span>
          ))}
        </div>
      )}

      {/* Botons */}
      <div style={{ display: "flex", gap: 6 }}>
        {onUse && (
          <button onClick={() => onUse(profile)} style={{
            flex: 1, padding: "6px 10px", borderRadius: 4, fontSize: 11,
            background: "#f5e6d0", color: "#c27a2a", border: "1px solid #c27a2a",
            cursor: "pointer", fontFamily: "IBM Plex Mono, monospace",
          }}>
            Usar
          </button>
        )}
        {onDetail && (
          <button onClick={() => onDetail(profile)} style={{
            padding: "6px 10px", borderRadius: 4, fontSize: 11,
            background: "#fff", color: "#868685", border: "1px solid #e0d5c5",
            cursor: "pointer", fontFamily: "IBM Plex Mono, monospace",
          }}>
            Detall
          </button>
        )}
        {onClone && !isCustom && (
          <button onClick={handleClone} disabled={cloning} style={{
            padding: "6px 10px", borderRadius: 4, fontSize: 11,
            background: "#fff", color: "#868685", border: "1px solid #e0d5c5",
            cursor: "pointer", fontFamily: "IBM Plex Mono, monospace",
          }}>
            {cloning ? "..." : "Clonar"}
          </button>
        )}
      </div>
    </div>
  )
}
