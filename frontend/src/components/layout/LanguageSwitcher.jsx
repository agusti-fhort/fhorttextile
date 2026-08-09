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
      /* §8b-quater · pell de la top bar, que passa conformitat en aquest tram: `#e4e4e2` era
         un dels tres colors fora de paleta que els blocs A i B ja tenien anotats, la vora de
         mig píxel no és de cap escala i el radi de la casa per a un control és 6, no 8. */
      style={{
        height: 32,
        background: 'var(--panel)',
        border: '1px solid var(--line)',
        borderRadius: 'var(--r-ctrl)',
        padding: '0 8px',
        fontSize: 'var(--fs-body)',
        color: 'var(--text-main)',
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
