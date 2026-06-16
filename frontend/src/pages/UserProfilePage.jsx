import { useState, useEffect } from 'react'
import { me } from '../api/endpoints'
import useAuthStore from '../store/auth'
import Card from '../components/ui/Card'

export default function UserProfilePage() {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const logout = useAuthStore(s => s.logout)

  useEffect(() => {
    me.get()
      .then(res => setProfile(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
      Carregant…
    </div>
  )
  if (!profile) return (
    <div style={{padding: '3rem', textAlign: 'center', color: 'var(--err)', fontSize: 13}}>
      No s'ha pogut carregar el perfil.
    </div>
  )

  const initials = (profile.nom_complet || profile.username || '?')
    .split(' ')
    .map(s => s[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <div style={{maxWidth: 640}}>
      <div style={{marginBottom: '1.5rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>El meu perfil</h1>
        <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
          Informació de l'usuari autenticat
        </p>
      </div>

      <Card>
        <div style={{
          display: 'flex', alignItems: 'center', gap: '1.4rem',
          paddingBottom: '1.2rem',
          borderBottom: '0.5px solid var(--gray-l)',
          marginBottom: '1.2rem',
        }}>
          <div style={{
            width: 72, height: 72, borderRadius: '50%',
            background: profile.color_avatar || 'var(--gold)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'white', fontSize: 24, fontWeight: 500,
            flexShrink: 0,
          }}>
            {initials}
          </div>
          <div>
            <h2 style={{fontSize: 18, fontWeight: 500, marginBottom: 4}}>
              {profile.nom_complet || profile.username}
            </h2>
            <div style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
              {profile.rol_nom || 'Sense rol'}
            </div>
          </div>
        </div>

        {[
          ['Nom complet', profile.nom_complet],
          ['Usuari',      profile.username],
          ['Email',       profile.email],
          ['Rol',         profile.rol_nom],
          ['Cost/hora',   profile.cost_hora != null ? `${profile.cost_hora} €` : null],
          ['Color avatar', profile.color_avatar],
        ].map(([k, v]) => (
          <div key={k} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '0.6rem 0', borderBottom: '0.5px solid var(--gray-l)',
            fontSize: 12,
          }}>
            <span style={{color: 'var(--gray)', fontWeight: 300}}>{k}</span>
            <span style={{display: 'flex', alignItems: 'center', gap: 8, fontWeight: 400}}>
              {k === 'Color avatar' && v && (
                <span style={{
                  width: 16, height: 16, borderRadius: '50%',
                  background: v, border: '0.5px solid var(--gray-l)',
                }} />
              )}
              {v || '—'}
            </span>
          </div>
        ))}

        <button
          onClick={logout}
          style={{
            marginTop: '1.5rem', width: '100%',
            background: 'var(--gold)', color: 'white',
            border: 'none', borderRadius: 8,
            padding: '10px 16px', fontSize: 12, fontWeight: 500,
            cursor: 'pointer', 
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          }}
        >
          <i className="ti ti-logout" style={{fontSize: 14}} />
          Tancar sessió
        </button>
      </Card>
    </div>
  )
}
