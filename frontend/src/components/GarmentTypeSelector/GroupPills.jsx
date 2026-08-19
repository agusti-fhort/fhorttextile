import { useTranslation } from 'react-i18next'
import useToc, { anellFocus } from '../ui/toc'
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

// ⚠️ EL TARONJA SE'N VA, I NO ÉS COSMÈTICA (NORMA_LAYOUT §1 · auditoria de computats 08/08).
// Aquestes pills són un FILTRE: triar-ne una és dir «on soc», no marcar un avís. El semàfor és
// NOMÉS tinta de dades, i `--warn` com a fons de selecció era la deriva que la norma combat —
// l'auditoria el va computar com a `rgb(133,79,11)`, fora de paleta, a `/garment-types`.
// La selecció de la casa és `--sel` + vora `--gold-border` (i el filet d'or 3px quan és una fila).
//
// AIXÒ TOCA TRES SUPERFÍCIES (Garment Types, el selector de peça del wizard i el Navegador de
// POM Systems) perquè el component és ÚNIC a posta. El canvi va cap a la norma a totes tres,
// però queda ANOTAT al report: les altres dues encara no han passat la seva conformitat.
export function groupPillStyle(active) {
  return {
    padding: '6px 14px', borderRadius: 'var(--r-ctrl)', cursor: 'pointer', fontFamily: MONO,
    fontSize: 'var(--fs-body)', fontWeight: active ? 600 : 400,
    background: active ? 'var(--sel)' : 'var(--panel)',
    color: 'var(--text-main)',
    border: `1px solid ${active ? 'var(--gold-border)' : 'var(--line)'}`,
  }
}

// TRES ESTATS I CAP MÉS (repòs · triada · hover). L'anell de focus, NOMÉS amb teclat: en clicar
// una pill amb el ratolí el botó conserva el focus, i l'anell de l'UA hi deixava una vora fosca
// i gruixuda que no és cap dels tres estats. V. `ui/toc.js`.
function Pill({ active, onClick, children }) {
  const [toc, gestos] = useToc()
  return (
    <button type="button" onClick={onClick} aria-pressed={active} {...gestos}
            style={{
              ...groupPillStyle(active), outline: 'none',
              ...(toc.hover && !active ? { background: 'var(--sel)' } : null),
              ...(toc.focus ? anellFocus : null),
            }}>{children}</button>
  )
}

export default function GroupPills({ groups = PECA_GRUPS, value, onChange, allLabel }) {
  const { i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {allLabel != null && (
        <Pill active={!value} onClick={() => onChange('')}>{allLabel}</Pill>
      )}
      {groups.map(g => (
        <Pill key={g.codi} active={value === g.codi} onClick={() => onChange(g.codi)}>
          {nomLocal(g, lang) || g.codi}
        </Pill>
      ))}
    </div>
  )
}
