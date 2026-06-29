import { useTranslation } from 'react-i18next'

// Placeholder del grup "Disseny" (F6). Les pàgines reals (llistat de documents .ftt,
// editor de patró DXF) arriben en sprints posteriors; de moment l'entrada de menú existeix
// i la ruta renderitza un marcador coherent amb el design system.
export default function DissenyPlaceholder({ titleKey, icon = 'ti-tools' }) {
  const { t } = useTranslation()
  return (
    <div style={{ padding: '32px 24px', maxWidth: 720 }}>
      <h1 style={{ fontSize: 'var(--fs-title)', color: 'var(--text-main)', marginBottom: 12,
                   display: 'flex', alignItems: 'center', gap: 10 }}>
        <i className={`ti ${icon}`} aria-hidden="true" style={{ color: 'var(--gold)' }} />
        {t(titleKey)}
      </h1>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
        {t('common.coming_soon')}
      </p>
    </div>
  )
}
