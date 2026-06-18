import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { passwordReset } from '../api/endpoints'

// Pàgina PÚBLICA (fora del guard d'auth) per a la recuperació mediada per admin.
// L'schema del tenant es resol pel domini de la request (django-tenants); cap token JWT.
export default function ResetPassword() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { uid, token } = useParams()

  const [status, setStatus] = useState('checking')   // 'checking' | 'valid' | 'invalid'
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let alive = true
    passwordReset.validate(uid, token)
      .then(res => { if (alive) setStatus(res.data?.valid ? 'valid' : 'invalid') })
      .catch(() => { if (alive) setStatus('invalid') })
    return () => { alive = false }
  }, [uid, token])

  function submit(e) {
    e.preventDefault()
    setError('')
    if (pw !== pw2) { setError(t('reset.mismatch')); return }
    setSaving(true)
    passwordReset.confirm({ uid, token, new_password: pw })
      .then(() => navigate('/login', { state: { resetOk: true } }))
      .catch(err => {
        const data = err?.response?.data
        setError(data?.error || data?.detail || t('reset.error_generic'))
        setSaving(false)
      })
  }

  const card = {
    background: 'var(--white)', borderRadius: 12, padding: '2rem',
    maxWidth: 400, width: '90%', boxShadow: '0 10px 40px rgba(0,0,0,0.12)',
    fontFamily: 'IBM Plex Mono, monospace',
  }
  const wrap = {
    minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'var(--gray-l, #f4f4f3)', padding: 20,
  }
  const field = {
    width: '100%', boxSizing: 'border-box', fontFamily: 'IBM Plex Mono, monospace',
    fontSize: 'var(--fs-body)', padding: '10px 12px', marginTop: 4,
    border: '0.5px solid var(--gray-l)', borderRadius: 8, background: 'var(--white)', color: 'var(--text-main)',
  }
  const label = { fontSize: 'var(--fs-label)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.04em' }

  return (
    <div style={wrap}>
      <div style={card}>
        <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 600, marginBottom: 16 }}>{t('reset.title')}</h1>

        {status === 'checking' && (
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('reset.checking')}</p>
        )}

        {status === 'invalid' && (
          <>
            <div style={{ padding: '12px 14px', borderRadius: 8, background: 'var(--err-bg)', color: 'var(--err)',
                          fontSize: 'var(--fs-body)', lineHeight: 1.5 }}>
              {t('reset.invalid')}
            </div>
            <button onClick={() => navigate('/login')} style={{
              marginTop: 18, width: '100%', fontFamily: 'IBM Plex Mono, monospace', fontSize: 'var(--fs-body)',
              fontWeight: 600, padding: '11px', borderRadius: 8, border: 'none',
              background: 'var(--gold)', color: 'var(--white)', cursor: 'pointer',
            }}>{t('reset.back_login')}</button>
          </>
        )}

        {status === 'valid' && (
          <form onSubmit={submit}>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 18 }}>{t('reset.subtitle')}</p>
            <div style={{ marginBottom: 14 }}>
              <label style={label}>{t('reset.new_password')}</label>
              <input type="password" autoFocus autoComplete="new-password" value={pw}
                     onChange={e => setPw(e.target.value)} style={field} />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={label}>{t('reset.confirm_password')}</label>
              <input type="password" autoComplete="new-password" value={pw2}
                     onChange={e => setPw2(e.target.value)} style={field} />
            </div>
            {error && (
              <div style={{ fontSize: 'var(--fs-body)', padding: '8px 10px', borderRadius: 6,
                            background: 'var(--err-bg)', color: 'var(--err)', marginBottom: 12 }}>{error}</div>
            )}
            <button type="submit" disabled={saving || !pw || !pw2} style={{
              width: '100%', fontFamily: 'IBM Plex Mono, monospace', fontSize: 'var(--fs-body)',
              fontWeight: 600, padding: '11px', borderRadius: 8, border: 'none',
              background: 'var(--gold)', color: 'var(--white)', cursor: saving ? 'default' : 'pointer',
              opacity: (saving || !pw || !pw2) ? 0.6 : 1,
            }}>{saving ? t('reset.saving') : t('reset.submit')}</button>
          </form>
        )}
      </div>
    </div>
  )
}
