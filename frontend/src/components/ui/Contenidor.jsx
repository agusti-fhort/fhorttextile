import { useState } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * Contenidor col·lapsable compartit. Capçalera fixa i cos amb scroll PROPI: el contingut
 * desborda per dins, mai la pàgina.
 *
 * Origen: era local a `pages/TallerPatro.jsx` amb tres consumidors del mateix fitxer.
 * S'extreu aquí perquè el panell dret de l'editor de fitxa faci el MATEIX patró en lloc de
 * clonar-lo (llei "no més pedaços: unificar el ja construït").
 *
 * La capçalera va en FOSC (QA-TALLER E · T1). Abans era gris clar sobre card gris clar: un
 * títol que pesa el mateix que el seu contingut no separa res. El contrast no és estètica
 * —és el que fa que «on sóc» es respongui sense llegir.
 *
 * Dos règims d'alçada, segons on es munta:
 *  · `pes` (per defecte 1) reparteix l'alçada quan el pare és una columna flex d'alçada
 *    fixa (Taller: 1 / 1.5 / 1). Plegat NO creix, deixa la seva alçada als altres.
 *  · En un pare scrollable (panell dret de l'editor) el `pes` no té efecte: el bloc creix
 *    amb el contingut. Per això `fitContent` treu el `flex` repartit i el `overflowY:auto`
 *    del cos — un scroll dins d'un scroll no serveix ningú.
 *
 * Convenció de chevron única del component: avall = plegat, amunt = obert.
 * L'estat NO es persisteix: és context de sessió, no preferència d'usuari
 * (precedent explícit a `AssetNavigator.jsx`).
 */
export default function Contenidor({ titol, icona, pes = 1, defaultOpen = true, fitContent = false, children }) {
  const { t } = useTranslation()
  const [plegat, setPlegat] = useState(!defaultOpen)

  return (
    <div style={{
      // Plegat NO creix: deixa tota la seva alçada als altres, que és per això que es plega.
      flex: fitContent ? '0 0 auto' : (plegat ? '0 0 auto' : `${pes} 1 0`),
      minHeight: 0, display: 'flex', flexDirection: 'column',
      borderBottom: '1px solid var(--border)',
    }}>
      <button
        onClick={() => setPlegat(p => !p)}
        aria-expanded={!plegat}
        style={{
          flexShrink: 0, display: 'flex', alignItems: 'center', gap: '0.4rem',
          padding: '0.45rem 0.7rem', background: 'var(--charcoal)',
          border: 'none', borderBottom: '1px solid var(--border)',
          cursor: 'pointer', textAlign: 'left', width: '100%',
          fontSize: 'var(--fs-label)', fontWeight: 600, textTransform: 'uppercase',
          letterSpacing: '0.03em', color: 'var(--white)',
        }}
      >
        {icona && <i className={`ti ${icona}`} />}
        <span style={{ flex: 1 }}>{titol}</span>
        <i
          className={`ti ${plegat ? 'ti-chevron-down' : 'ti-chevron-up'}`}
          title={plegat ? t('pattern.taller.expand') : t('pattern.taller.collapse')}
        />
      </button>
      {!plegat && (
        <div style={{
          flex: fitContent ? '0 0 auto' : 1, minHeight: 0,
          overflowY: fitContent ? 'visible' : 'auto', padding: '0.5rem 0.6rem',
        }}>
          {children}
        </div>
      )}
    </div>
  )
}
