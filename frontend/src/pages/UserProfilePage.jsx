import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { me } from '../api/endpoints'
import useAuthStore from '../store/auth'
import Card from '../components/ui/Card'
import PageMenu from '../components/ui/PageMenu'
import { apagat, botoPri, botoSec } from '../components/ui/buttons'

export default function UserProfilePage() {
  const { t } = useTranslation()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const logout = useAuthStore(s => s.logout)

  // Canvi de contrasenya autoservei (la sessió JWT segueix vàlida després).
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')
  const [pwSaving, setPwSaving] = useState(false)
  const [pwMsg, setPwMsg] = useState(null)   // { type: 'ok'|'err', text }

  useEffect(() => {
    me.get()
      .then(res => setProfile(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  function changePassword(e) {
    e.preventDefault()
    setPwMsg(null)
    if (pw !== pw2) { setPwMsg({ type: 'err', text: t('userProfile.pw_mismatch') }); return }
    setPwSaving(true)
    me.changePassword({ new_password: pw, new_password_confirm: pw2 })
      .then(() => { setPwMsg({ type: 'ok', text: t('userProfile.pw_ok') }); setPw(''); setPw2('') })
      .catch(err => {
        // Errors del backend (validadors de password): literal del servidor via firstError.
        const data = err?.response?.data
        setPwMsg({ type: 'err', text: data?.error || data?.detail || t('userProfile.pw_error') })
      })
      .finally(() => setPwSaving(false))
  }

  if (loading) return (
    <div style={{padding: '3rem', textAlign: 'center', color: 'var(--text-soft)', fontSize: 'var(--fs-body)'}}>
      {t('userProfile.st_loading')}
    </div>
  )
  if (!profile) return (
    <div style={{padding: '3rem', textAlign: 'center', color: 'var(--err)', fontSize: 'var(--fs-body)'}}>
      {t('userProfile.st_error')}
    </div>
  )

  const initials = (profile.nom_complet || profile.username || '?')
    .split(' ')
    .map(s => s[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  // [clau i18n, valor]; 'pf_color' té tractament especial (mostra el cercle de color).
  const fields = [
    ['pf_nom_complet', profile.nom_complet],
    ['pf_username',    profile.username],
    ['pf_email',       profile.email],
    ['pf_rol',         profile.rol_nom],
    ['pf_cost_hora',   profile.cost_hora != null ? `${profile.cost_hora} €` : null],
    ['pf_color',       profile.color_avatar],
  ]

  return (
    <>
      {/* §8b · menú de pantalla; sense seccions, queda la fletxa (§8b.2). */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu backTo="/" backTitle={t('userProfile.back_title')} />
      </div>

    <div style={{maxWidth: 640, paddingTop: 16}}>
      <div style={{marginBottom: 16}}>
        <h1 style={{fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500, marginBottom: 4, color: 'var(--text-main)'}}>{t('userProfile.hd_title')}</h1>
        <p style={{fontSize: 'var(--fs-caption)', color: 'var(--text-soft)'}}>
          {t('userProfile.hd_subtitle')}
        </p>
      </div>

      <Card>
        <div style={{
          display: 'flex', alignItems: 'center', gap: '1.4rem',
          paddingBottom: '1.2rem',
          borderBottom: '1px solid var(--line)',
          marginBottom: '1.2rem',
        }}>
          <div style={{
            width: 72, height: 72, borderRadius: '50%',
            background: profile.color_avatar || 'var(--gold)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--text-main)', fontSize: 'var(--fs-h1)', fontWeight: 500,
            flexShrink: 0,
          }}>
            {initials}
          </div>
          <div>
            <h2 style={{fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4}}>
              {profile.nom_complet || profile.username}
            </h2>
            <div style={{fontSize: 'var(--fs-body)', color: 'var(--text-soft)'}}>
              {profile.rol_nom || t('userProfile.pf_no_role')}
            </div>
          </div>
        </div>

        {fields.map(([key, v]) => (
          <div key={key} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '0.6rem 0', borderBottom: '1px solid var(--line)',
            fontSize: 'var(--fs-body)',
          }}>
            <span style={{color: 'var(--text-soft)'}}>{t(`userProfile.${key}`)}</span>
            <span style={{display: 'flex', alignItems: 'center', gap: 8, fontWeight: 400}}>
              {key === 'pf_color' && v && (
                <span style={{
                  width: 16, height: 16, borderRadius: '50%',
                  background: v, border: '1px solid var(--line)',
                }} />
              )}
              {v || '—'}
            </span>
          </div>
        ))}

        {/* §5 · TANCAR SESSIÓ NO ÉS L'ACCIÓ PRIMÀRIA d'aquesta pantalla —el que hi has vingut
            a fer és canviar la contrasenya— i tampoc és destructiva: és una PORTA de sortida.
            Anava en daurat ple i a tota amplada, cridant més que res del producte. Secundària
            de la casa (§5.2/§5.3), i sense ocupar la línia sencera. */}
        <button onClick={logout} style={{ ...botoSec, marginTop: 16 }}>
          <i className="ti ti-logout" aria-hidden="true" style={{fontSize: 14, color: 'currentColor'}} />
          {t('userProfile.pf_logout')}
        </button>
      </Card>

      <Card style={{marginTop: '1.5rem'}}>
        <h2 style={{fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4}}>{t('userProfile.pw_title')}</h2>
        <p style={{fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginBottom: '1.2rem'}}>
          {t('userProfile.pw_subtitle')}
        </p>
        <form onSubmit={changePassword} style={{display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 360}}>
          <div>
            <label style={pwLabelS}>{t('userProfile.pw_new')}</label>
            <input type="password" autoComplete="new-password" value={pw}
                   onChange={e => setPw(e.target.value)} style={pwInputS} />
          </div>
          <div>
            <label style={pwLabelS}>{t('userProfile.pw_confirm')}</label>
            <input type="password" autoComplete="new-password" value={pw2}
                   onChange={e => setPw2(e.target.value)} style={pwInputS} />
          </div>
          {pwMsg && (
            <div style={{
              fontSize: 'var(--fs-body)', padding: '8px 10px', borderRadius: 'var(--r-ctrl)',
              background: pwMsg.type === 'ok' ? 'var(--ok-bg)' : 'var(--err-bg)',
              color: pwMsg.type === 'ok' ? 'var(--ok)' : 'var(--err)',
            }}>{pwMsg.text}</div>
          )}
          {/* §5.1 · AQUESTA sí que és l'acció primària de la pantalla, i és l'única: blava.
              I el deshabilitat baixa el FONS, no la tinta (§5.7). */}
          <button type="submit" disabled={pwSaving || !pw || !pw2}
            style={{ ...botoPri, alignSelf: 'flex-start',
                     ...((pwSaving || !pw || !pw2) ? apagat : null) }}>
            {pwSaving ? t('userProfile.pw_saving') : t('userProfile.pw_submit')}</button>
        </form>
      </Card>
    </div>
    </>
  )
}

const pwInputS = {
  width: '100%', boxSizing: 'border-box', fontFamily: 'IBM Plex Mono, monospace',
  fontSize: 'var(--fs-body)', padding: '8px 12px', marginTop: 4,
  border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)',
  background: 'var(--panel)', color: 'var(--text-main)',
}
const pwLabelS = {
  fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--text-soft)',
  textTransform: 'uppercase', letterSpacing: '.08em',
}
