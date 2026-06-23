import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

// Botó de tornar reusable i transversal. Patró únic per a tot el sistema: s'arriba a una
// superfície i sempre s'hi pot sortir. Per defecte navega enrere (history -1); es pot forçar
// una destinació amb `to` o un handler propi amb `onClick`. Icona Tabler outline + `app.back`.
export default function BackButton({ to = null, onClick = null, label, style = null }) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const handle = onClick || (() => (to ? navigate(to) : navigate(-1)))
  return (
    <button type="button" onClick={handle} style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '6px 12px', border: '0.5px solid var(--border)', borderRadius: 6,
      background: 'transparent', cursor: 'pointer', color: 'var(--text-muted)',
      fontSize: 'var(--fs-body)', ...(style || {}),
    }}>
      <i className="ti ti-arrow-left" />
      {label ?? t('app.back')}
    </button>
  )
}
