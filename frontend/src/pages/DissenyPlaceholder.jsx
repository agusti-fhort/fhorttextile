import { useTranslation } from 'react-i18next'
import PageMenu from '../components/ui/PageMenu'

// Placeholder del grup "Disseny" (F6). Les pàgines reals (llistat de documents .ftt,
// editor de patró DXF) arriben en sprints posteriors; de moment l'entrada de menú existeix
// i la ruta renderitza un marcador coherent amb el design system.
//
// ── CONFORMITAT (part B · pantalla 4 · «Documents») ────────────────────────────────────────
// Una pantalla que encara no té contingut **té estructura igualment** (§8b: «de dalt a baix,
// TOTA pantalla del producte»), i és justament on més es nota si no la té: aquí no hi ha res
// que distregui de la seva absència. El que hi havia: cap menú de pantalla —o sigui **cap
// manera de tornar enrere que no fos el menú lateral**—, i el contingut sencer era un títol
// amb la icona en daurat i una frase.
//
// 🚨 I EL TÍTOL NO TENIA MIDA. `var(--fs-title)` **no existeix a `:root`** (el token de la casa
// és `--fs-h1`): la declaració queda invàlida al càlcul, la mida cau a la de l'agent d'usuari
// per a un `h1` —2em, o sigui 32px— i el que es veia era un títol un terç més gran que el de
// qualsevol altra pantalla. És germà del `var(--bg, #faf9f7)` que va sortir a Planificació, i
// pitjor: allà el fallback amagava el forat, aquí no n'hi ha i el forat el tapa el navegador.
// Cap de les dues es veu llegint el codi de pressa; totes dues es veuen mesurant.
export default function DissenyPlaceholder({ titleKey, icon = 'ti-tools' }) {
  const { t } = useTranslation()
  return (
    <>
      {/* Sense seccions i sense acció: la barra queda amb NOMÉS la fletxa, que és exactament el
          que la §8b.2 descriu («sense seccions: només queda la fletxa»). La barra no desapareix
          mai — i en una pantalla buida és l'única cosa que hi ha per fer. */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu backTo="/" backTitle={t('disseny.back_title')} />
      </div>

      <div style={{ paddingTop: 16, maxWidth: 720 }}>
        {/* §8b.3 · identitat sobre el fons de pàgina, sense contenidor. */}
        <h1 style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500,
                     color: 'var(--text-main)', marginBottom: 12,
                     display: 'flex', alignItems: 'center', gap: 8 }}>
          <i className={`ti ${icon}`} aria-hidden="true"
            style={{ fontSize: 20, color: 'var(--text-soft)' }} />
          {t(titleKey)}
        </h1>
        {/* §8c · «estat buit = frase en --text-faint cursiva, mai caixa buida muda». Aquesta
            pantalla és, sencera, un estat buit: la frase és tot el que hi ha i ha de dir-ho
            amb el llenguatge que la casa fa servir per a «aquí encara no hi ha res». */}
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-faint)', fontStyle: 'italic' }}>
          {t('common.coming_soon')}
        </p>
      </div>
    </>
  )
}
