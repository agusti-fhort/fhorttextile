import { useTranslation } from 'react-i18next'
import { GARMENT_GROUPS, nomLocal } from '../grading/gradingAxes'

// GroupPills — pestanyes/pills de GRUP de peça, patró visual ÚNIC (rectificació 2026-07-17). Abans
// vivia inline al selector de peça (GarmentTypeSelector); s'ha extret aquí perquè Garment Types i el
// Navegador de POM Systems facin servir EXACTAMENT el mateix (cap còpia divergent). Font d'ordre i
// etiquetes: el vocabulari únic GARMENT_GROUPS (grading/gradingAxes).
//
// Props: groups (llista GARMENT_GROUPS-shaped) · value (codi actiu, '' = tots) · onChange(codi) ·
//        allLabel (opcional: renderitza una pill «Tots» com a PRIMERA, mateix estil).

const MONO = 'IBM Plex Mono, monospace'

// El grup de peça (sense ACCESSORIES: no té famílies actives al selector). Font única per a totes
// les superfícies → mateix ordre a tot arreu.
export const PECA_GRUPS = GARMENT_GROUPS.filter(g => g.codi !== 'ACCESSORIES')

export function groupPillStyle(active) {
  return {
    padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontFamily: MONO,
    fontSize: 'var(--fs-body)', fontWeight: active ? 600 : 400,
    background: active ? 'var(--warn-bg)' : 'var(--white)',
    color: active ? 'var(--warn)' : 'var(--text-main)',
    border: `1px solid ${active ? 'var(--warn)' : 'var(--gray-l)'}`,
  }
}

export default function GroupPills({ groups = PECA_GRUPS, value, onChange, allLabel }) {
  const { i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {allLabel != null && (
        <button type="button" onClick={() => onChange('')} style={groupPillStyle(!value)}>{allLabel}</button>
      )}
      {groups.map(g => (
        <button key={g.codi} type="button" onClick={() => onChange(g.codi)} style={groupPillStyle(value === g.codi)}>
          {nomLocal(g, lang) || g.codi}
        </button>
      ))}
    </div>
  )
}
