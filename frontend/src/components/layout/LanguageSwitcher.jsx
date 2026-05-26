import { useTranslation } from 'react-i18next'
import { SUPPORTED_LANGUAGES } from '../../i18n'

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const current = (i18n.resolvedLanguage || i18n.language || 'ca').slice(0, 2)

  const change = (e) => {
    const lng = e.target.value
    i18n.changeLanguage(lng)
  }

  return (
    <select
      value={current}
      onChange={change}
      aria-label={t('lang.ca')}
      style={{
        height: 32,
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 8,
        padding: '0 8px',
        fontSize: 12,
        fontFamily: 'var(--font)',
        color: 'var(--charcoal)',
        cursor: 'pointer',
        outline: 'none',
      }}
    >
      {SUPPORTED_LANGUAGES.map(l => (
        <option key={l} value={l}>{l.toUpperCase()}</option>
      ))}
    </select>
  )
}
