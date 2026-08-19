import { useTranslation } from 'react-i18next'

// SUB-TABS — les seccions germanes DINS d'un panell.
//
// D'ON VE: vivia com a markup inline dins de `ModelSheet` (el commutador «Taula de mesures |
// Repàs | Comprovació»), i quan l'Escalat n'ha necessitat un (E2c-bis/C1) la temptació era
// escriure'n un segon. Dos commutadors amb el mateix paper i dos codis és com neixen les dues
// veritats de crom que aquesta casa acaba pagant: n'hi ha prou que algú toqui el subratllat d'un
// per tenir dues seccions germanes que es veuen diferent. Això és el trasllat, LITERAL.
//
// ── LA FORMA, SEGONS NORMA_LAYOUT §8b-bis ───────────────────────────────────────────────────
// Seccions germanes dins d'un panell = TABS AMB SUBRATLLAT D'OR. Mai píndoles, i molt menys
// daurat PLE, que és marca fent de navegació: el menú de PANTALLA ja és el de dalt i barrejar
// els dos patrons al mateix nivell és el que la norma prohibeix explícitament.
//
// El BADGE (E2c-bis/C1) és l'única cosa que el trasllat afegeix, i és opcional: un número al
// costat del rètol que diu quanta feina queda en aquella secció. Amb `badge` nul o 0 no es
// pinta res — un «0» permanent al costat d'un tab és soroll, no informació.
const MONO = 'IBM Plex Mono, monospace'

/**
 * @param {{items: Array<{key: string, label: string, icon?: string, badge?: number|null}>,
 *          actiu: string, onTria: (key: string) => void, dreta?: React.ReactNode}} props
 *   `label` és una CLAU i18n (es tradueix aquí dins).
 *   `dreta` és contingut opcional alineat a la dreta de la barra de tabs (p.ex. l'ancoratge de
 *   la presa a l'Escalat); no és una acció i no s'hi posen botons.
 */
export default function SubTabs({ items, actiu, onTria, dreta = null }) {
  const { t } = useTranslation()
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, borderBottomWidth: 1,
                  borderBottomStyle: 'solid', borderBottomColor: 'var(--line)' }}>
      {items.map(({ key, label, icon, badge }) => (
        <button key={key} type="button" onClick={() => onTria(key)}
          aria-current={actiu === key ? 'true' : undefined}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '8px 14px', border: 'none', background: 'none', cursor: 'pointer',
            fontFamily: MONO,
            color: actiu === key ? 'var(--text-main)' : 'var(--text-soft)',
            fontSize: 'var(--fs-body)', fontWeight: actiu === key ? 600 : 400,
            boxShadow: actiu === key ? 'inset 0 -2px 0 var(--gold)' : undefined,
          }}>
          {icon && <i className={`ti ${icon}`} aria-hidden="true"
                      style={{ fontSize: 14, color: 'currentColor' }} />}
          {t(label)}
          {/* §1 — BADGE: fons suau + tinta del color + vora fina del mateix color, píndola.
              Mai fons ple. Aquí en to neutre: diu QUANTA feina queda, no que hi hagi cap alarma. */}
          {badge ? (
            <span style={{ display: 'inline-flex', alignItems: 'center', borderRadius: 999,
                           padding: '1px 7px', fontSize: 'var(--fs-caption)',
                           background: 'var(--panel)', color: 'var(--text-soft)',
                           border: '1px solid var(--line)' }}>{badge}</span>
          ) : null}
        </button>
      ))}
      {dreta && <span style={{ marginLeft: 'auto', paddingRight: 4 }}>{dreta}</span>}
    </div>
  )
}
