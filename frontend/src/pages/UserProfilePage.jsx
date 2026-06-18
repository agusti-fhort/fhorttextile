import { useState, useEffect } from 'react'
import { me } from '../api/endpoints'
import useAuthStore from '../store/auth'
import Card from '../components/ui/Card'

export default function UserProfilePage() {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const logout = useAuthStore(s => s.logout)

  // Canvi de contrasenya autoservei (la sessió JWT segueix vàlida després).
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')
  const [pwSaving, setPwSaving] = useState(false)
  const [pwMsg, setPwMsg] = useState(null)   // { type: 'ok'|'err', text }

  function changePassword(e) {
    e.preventDefault()
    setPwMsg(null)
    if (pw !== pw2) { setPwMsg({ type: 'err', text: 'Les contrasenyes no coincideixen.' }); return }
    setPwSaving(true)
    me.changePassword({ new_password: pw, new_password_confirm: pw2 })
      .then(() => { setPwMsg({ type: 'ok', text: 'Contrasenya actualitzada.' }); setPw(''); setPw2('') })
      .catch(err => {
        const data = err?.response?.data
        setPwMsg({ type: 'err', text: data?.error || data?.detail || 'No s\'ha pogut actualitzar la contrasenya.' })
      })
      .finally(() => setPwSaving(false))
  }

  useEffect(() => {
    me.get()
      .then(res => setProfile(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 'var(--fs-body)'}}>
      Carregant…
    </div>
  )
  if (!profile) return (
    <div style={{padding: '3rem', textAlign: 'center', color: 'var(--err)', fontSize: 'var(--fs-body)'}}>
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
        <h1 style={{fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4}}>El meu perfil</h1>
        <p style={{fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300}}>
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
            color: 'white', fontSize: 'var(--fs-h1)', fontWeight: 500,
            flexShrink: 0,
          }}>
            {initials}
          </div>
          <div>
            <h2 style={{fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4}}>
              {profile.nom_complet || profile.username}
            </h2>
            <div style={{fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300}}>
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
            fontSize: 'var(--fs-body)',
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
            padding: '10px 16px', fontSize: 'var(--fs-body)', fontWeight: 500,
            cursor: 'pointer', 
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          }}
        >
          <i className="ti ti-logout" style={{fontSize: 14}} />
          Tancar sessió
        </button>
      </Card>

      <Card style={{marginTop: '1.5rem'}}>
        <h2 style={{fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4}}>Canviar contrasenya</h2>
        <p style={{fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300, marginBottom: '1.2rem'}}>
          Introdueix la teva nova contrasenya. La sessió actual continua activa.
        </p>
        <form onSubmit={changePassword} style={{display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 360}}>
          <div>
            <label style={pwLabelS}>Nova contrasenya</label>
            <input type="password" autoComplete="new-password" value={pw}
                   onChange={e => setPw(e.target.value)} style={pwInputS} />
          </div>
          <div>
            <label style={pwLabelS}>Confirma la contrasenya</label>
            <input type="password" autoComplete="new-password" value={pw2}
                   onChange={e => setPw2(e.target.value)} style={pwInputS} />
          </div>
          {pwMsg && (
            <div style={{
              fontSize: 'var(--fs-body)', padding: '8px 10px', borderRadius: 6,
              background: pwMsg.type === 'ok' ? 'var(--ok-bg)' : 'var(--err-bg)',
              color: pwMsg.type === 'ok' ? 'var(--ok)' : 'var(--err)',
            }}>{pwMsg.text}</div>
          )}
          <button type="submit" disabled={pwSaving || !pw || !pw2} style={{
            background: 'var(--gold)', color: 'white', border: 'none', borderRadius: 8,
            padding: '10px 16px', fontSize: 'var(--fs-body)', fontWeight: 500,
            cursor: pwSaving ? 'default' : 'pointer', opacity: (pwSaving || !pw || !pw2) ? 0.6 : 1,
            alignSelf: 'flex-start',
          }}>{pwSaving ? 'Desant…' : 'Actualitzar contrasenya'}</button>
        </form>
      </Card>
    </div>
  )
}

const pwInputS = {
  width: '100%', boxSizing: 'border-box', fontFamily: 'IBM Plex Mono, monospace',
  fontSize: 'var(--fs-body)', padding: '9px 11px', marginTop: 4,
  border: '0.5px solid var(--gray-l)', borderRadius: 8, background: 'var(--white)', color: 'var(--text-main)',
}
const pwLabelS = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.04em',
}
