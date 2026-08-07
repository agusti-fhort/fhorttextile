import { useTranslation } from "react-i18next"
import { groupLabel } from "./grading/gradingAxes"

// RunRestrictionTags (N1/N2 · 2026-08-06 nit) — les 4 capes de restricció d'un RUN de talles,
// pintades amb el tag que la casa ja fa servir. NOMÉS les capes informades: una capa buida vol
// dir «no declarada», i pintar-la buida seria afirmar que el run no serveix per a res.
//
// Font única de les etiquetes: les mateixes claus i18n que ja resolen aquests vocabularis a la
// resta del sistema (`model_wizard.target_*`, `..._construction_*`, `..._fit_*`) i `groupLabel`
// per al grup. Cap còpia nova de vocabulari: el codi és la identitat, el nom és presentació.

const tagBase = {
  padding: "2px 8px", borderRadius: 3, fontSize: 'var(--fs-label)',
  background: "var(--white)", color: "var(--text-muted)",
  border: "1px solid var(--border)", whiteSpace: "nowrap",
}

export function RunRestrictionTags({ run, compact = false }) {
  const { t, i18n } = useTranslation()
  if (!run) return null

  const capes = [
    (run.target_codis || []).map(c => t(`model_wizard.target_${c}`, c)),
    (run.grup_codis || []).map(c => groupLabel(c, i18n.language) || c),
    (run.construccio_codis || []).map(c => t(`model_wizard.construction_${c}`, c)),
    (run.fit_codis || []).map(c => t(`model_wizard.fit_${c}`, c)),
  ]
  const etiquetes = capes.flat()
  if (etiquetes.length === 0) return null

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: compact ? 8 : 10 }}>
      {etiquetes.map((e, i) => (
        <span key={i} style={tagBase}>{e}</span>
      ))}
    </div>
  )
}

// Badge del tipus d'escala (ALPHA · NUM · MESOS · ALTURA). Buit = no deduïble sol: no es pinta
// res, perquè un run sense escala classificada no és un run d'escala desconeguda, és un run del
// qual encara no ho sabem (i el report de la nit el porta a la llista de l'Agus).
export function ScaleBadge({ tipus }) {
  const { t } = useTranslation()
  if (!tipus) return null
  return (
    <span style={{
      padding: "2px 8px", borderRadius: 3, fontSize: 'var(--fs-label)',
      background: "#f5f0ea", color: "var(--text-main)", border: "1px solid var(--border)",
      letterSpacing: ".04em",
    }}>
      {t(`size_library.scale_${tipus}`, tipus)}
    </span>
  )
}

// Badge de client del RUN. Mateixa caixa que els altres badges de la targeta.
export function RunCustomerBadge({ codi, nom }) {
  if (!codi) return null
  return (
    <span title={nom || codi} style={{
      padding: "2px 8px", borderRadius: 3, fontSize: 'var(--fs-label)',
      background: "#f5e6d0", color: "var(--gold)", border: "1px solid var(--gold-border)",
    }}>
      {codi}
    </span>
  )
}
