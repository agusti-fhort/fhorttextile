import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'

// Tram 3 — Pantalla "Usuaris i rols" (gated manage_users).
// Peça A: ruta + gating. La matriu (Peça B) i l'edició/bulk (Peça C) s'hi afegeixen a sobre.
export default function UsersRoles() {
  const { t } = useTranslation()
  const user = useAuthStore(s => s.user)
  const canManage = !!user?.capabilities?.includes('manage_users')

  // user encara no carregat (fetchMe async) → evitar flash de "sense accés" als admins.
  if (user === null) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>
        {t('usersRoles.loading')}
      </div>
    )
  }

  // El backend ja enforça 403; aquí amaguem la UI per a qui no té la capacitat.
  if (!canManage) {
    return (
      <div style={{ padding: '4rem 2rem', textAlign: 'center' }}>
        <i className="ti ti-lock" style={{ fontSize: 32, color: 'var(--gray)' }} />
        <p style={{ marginTop: 12, fontSize: 13, color: 'var(--gray)' }}>
          {t('usersRoles.no_access')}
        </p>
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>
          {t('usersRoles.title')}
        </h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>
          {t('usersRoles.subtitle')}
        </p>
      </div>
      {/* Peça B: matriu (abast/gestió + tasques). Peça C: edició + filtres + bulk. */}
    </div>
  )
}
