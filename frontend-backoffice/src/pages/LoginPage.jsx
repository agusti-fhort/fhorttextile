import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { login as loginApi, me as meApi } from '../api/auth'
import useAuthStore from '../store/authStore'
import { SUPPORTED_LANGUAGES } from '../i18n'

// Logotip vectorial Fhort Textile Tech (còpia literal del component del producte;
// font única a Login.jsx / Sidebar.jsx). Sobre fons clar: "Fhort" en or (#c27a2a),
// "Textile Tech" en charcoal (#1d1d1b).
const Logo = () => (
  <svg viewBox="0 0 222.7 79.76" xmlns="http://www.w3.org/2000/svg">
    <path fill="#c27a2a" d="M31.22,0H1.07C.48,0,0,.48,0,1.07v38.22c0,.59.48,1.07,1.07,1.07h9.04c.59,0,1.07-.48,1.07-1.07v-12.27c0-.59.48-1.07,1.07-1.07h16.94c.59,0,1.07-.48,1.07-1.07v-7.14c0-.59-.48-1.07-1.07-1.07H12.26c-.59,0-1.07-.48-1.07-1.07v-4.72c0-.59.48-1.07,1.07-1.07h18.96c.59,0,1.07-.48,1.07-1.07V1.07c0-.59-.48-1.07-1.07-1.07Z"/>
    <path fill="#c27a2a" d="M54.21,8.48c-4.38,0-7.24,2.3-9.25,4.85-.03.04-.09.02-.09-.03V1.07c0-.59-.48-1.07-1.07-1.07h-8.81c-.59,0-1.07.48-1.07,1.07v38.22c0,.59.48,1.07,1.07,1.07h8.81c.59,0,1.07-.48,1.07-1.07v-15.82c0-3.46,1.96-5.31,4.61-5.31s4.44,1.85,4.44,5.31v15.82c0,.59.48,1.07,1.07,1.07h8.75c.59,0,1.07-.48,1.07-1.07v-19.34c0-7.09-3.98-11.48-10.61-11.48Z"/>
    <path fill="#c27a2a" d="M83.62,8.48c-9.98,0-17.24,7.44-17.24,16.32v.12c0,8.88,7.21,16.2,17.13,16.2s17.3-7.44,17.3-16.32v-.12c0-8.88-7.21-16.2-17.18-16.2ZM90.19,24.91c0,3.75-2.59,6.92-6.57,6.92s-6.63-3.23-6.63-7.04v-.12c0-3.39,2.02-6.28,5.27-6.87,4.16-.75,7.93,2.62,7.93,6.84v.26Z"/>
    <path fill="#c27a2a" d="M137.24,20.18h6.14c.59,0,1.07-.48,1.07-1.07v-9.39c0-.59-.48-1.07-1.07-1.07h-6.14s-.05-.02-.05-.05V1.07c0-.59-.48-1.07-1.07-1.07h-8.75c-.59,0-1.07.48-1.07,1.07v7.53s-.02.05-.05.05h-2.89c-5.22,0-7.98,2.45-9.77,6.58-.02.05-.1.04-.1-.02v-4.97c0-.59-.48-1.07-1.07-1.07h-8.81c-.59,0-1.07.48-1.07,1.07v29.05c0,.59.48,1.07,1.07,1.07h8.81c.59,0,1.07-.48,1.07-1.07v-8.67c0-7.15,3.23-10.44,8.94-10.44h3.81s.05.02.05.05v10.45c0,7.44,3.86,10.32,10.44,10.32h6.54c.59,0,1.07-.48,1.07-1.07v-8.76c0-.59-.48-1.07-1.07-1.07-1.07,0-1.91-.02-3.08-.02-2.02,0-3-.92-3-3.11v-6.73s.02-.05.05-.05Z"/>
    <path fill="#1d1d1b" d="M10.21,51.84H0v-1.27h21.86v1.27h-10.25v27.43h-1.39v-27.43Z"/>
    <path fill="#1d1d1b" d="M20.83,68.94v-.08c0-6.07,4.18-10.74,9.88-10.74,6.23,0,9.47,5.33,9.47,10.87v.45h-17.92c.25,5.62,4.22,9.1,8.86,9.1,3.2,0,5.78-1.68,7.42-3.81l.98.78c-1.89,2.46-4.67,4.26-8.45,4.26-5.58,0-10.25-4.22-10.25-10.83ZM38.75,68.24c-.2-4.51-2.95-8.9-8.12-8.9-4.68,0-8.12,3.81-8.37,8.9h16.48Z"/>
    <path fill="#1d1d1b" d="M52.44,67.87l7.75-9.27h1.56l-8.49,10.13,8.82,10.54h-1.64l-8.04-9.64-8.04,9.64h-1.56l8.82-10.5-8.49-10.17h1.64l7.67,9.27Z"/>
    <path fill="#1d1d1b" d="M68.55,73.98v-14.19h-3.16v-1.19h3.16v-6.93h1.31v6.93h7.5v1.19h-7.5v14.07c0,3.03,1.6,4.55,4.3,4.55,1.03,0,2.05-.25,3.12-.74v1.27c-1.03.49-2.09.7-3.24.7-3.32,0-5.49-1.93-5.49-5.66Z"/>
    <path fill="#1d1d1b" d="M83.22,50.4h1.77v2.5h-1.77v-2.5ZM83.43,58.6h1.35v20.67h-1.35v-20.67Z"/>
    <path fill="#1d1d1b" d="M92.9,49.34h1.35v29.94h-1.35v-29.94Z"/>
    <path fill="#1d1d1b" d="M100.69,68.94v-.08c0-6.07,4.18-10.74,9.88-10.74,6.23,0,9.47,5.33,9.47,10.87v.45h-17.92c.25,5.62,4.22,9.1,8.86,9.1,3.2,0,5.78-1.68,7.42-3.81l.98.78c-1.89,2.46-4.68,4.26-8.45,4.26-5.58,0-10.25-4.22-10.25-10.83ZM118.61,68.24c-.2-4.51-2.95-8.9-8.12-8.9-4.68,0-8.12,3.81-8.37,8.9h16.48Z"/>
    <path fill="#1d1d1b" d="M145.78,51.84h-10.21v-1.27h21.86v1.27h-10.25v27.43h-1.39v-27.43Z"/>
    <path fill="#1d1d1b" d="M156.4,68.94v-.08c0-6.07,4.18-10.74,9.88-10.74,6.23,0,9.47,5.33,9.47,10.87v.45h-17.92c.25,5.62,4.22,9.1,8.86,9.1,3.2,0,5.78-1.68,7.42-3.81l.98.78c-1.89,2.46-4.68,4.26-8.45,4.26-5.58,0-10.25-4.22-10.25-10.83ZM174.32,68.24c-.2-4.51-2.95-8.9-8.12-8.9-4.68,0-8.12,3.81-8.37,8.9h16.48Z"/>
    <path fill="#1d1d1b" d="M180.3,68.98v-.08c0-5.82,4.59-10.79,10.58-10.79,3.81,0,6.23,1.72,8.24,3.81l-.94.94c-1.8-1.93-4.06-3.53-7.34-3.53-5.21,0-9.15,4.31-9.15,9.52v.08c0,5.21,4.06,9.6,9.23,9.6,3.28,0,5.62-1.68,7.42-3.69l.94.82c-2.01,2.34-4.59,4.1-8.45,4.1-5.95,0-10.54-4.92-10.54-10.79Z"/>
    <path fill="#1d1d1b" d="M204.9,49.34h1.31v14.19c.94-2.46,3.53-5.41,7.96-5.41,5.45,0,8.53,3.69,8.53,9.06v12.1h-1.31v-11.89c0-4.8-2.58-8.04-7.38-8.04-4.35,0-7.79,3.57-7.79,8.28v11.65h-1.31v-29.94Z"/>
  </svg>
)

// Iconografia inline (mateixos traçats que el login del producte).
const MailIcon = () => (
  <svg className="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>
  </svg>
)
const LockIcon = () => (
  <svg className="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>
  </svg>
)
const EyeIcon = ({ off }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/>
    <circle cx="12" cy="12" r="3"/>
    {off && <line x1="3" y1="3" x2="21" y2="21"/>}
  </svg>
)

export default function LoginPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const setAuth = useAuthStore(s => s.setAuth)   // flux backoffice (bo_access_token) — NO es toca

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [remember, setRemember] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const currentLang = (i18n.resolvedLanguage || i18n.language || 'ca').slice(0, 2)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await loginApi(email, password)
      // El backend pot retornar el token amb claus diferents; siguem tolerants.
      const token = data.token || data.access || data.access_token
      let user = data.user || null
      let rol = data.rol || data.user?.rol || null
      setAuth({ token })

      // Si el login no inclou el perfil, el recuperem de /auth/me/.
      if (!user) {
        try {
          const profile = await meApi()
          user = profile
          rol = profile.rol || rol
        } catch {
          // No bloquegem l'accés si /me/ falla; ja tenim token vàlid.
        }
      }
      setAuth({ user, rol })
      navigate('/dashboard')
    } catch (err) {
      // Resposta del servidor (400/401) → credencials; sense resposta → xarxa.
      setError(err?.response ? t('login.error_invalid') : t('login.error_generic'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-screen">
      <style>{LOGIN_CSS}</style>

      {/* ===== ESQUERRA : MARCA ===== */}
      <div className="brand">
        <span className="accent a1" /><span className="accent a2" />
        <div className="brand-inner">
          <div className="brand-logo">
            <div className="logo"><Logo /></div>
            <span className="lb">Backoffice</span>
          </div>
          <h1 className="tagline">{t('login.tagline')}</h1>
          <p className="tagsub">{t('login.tagline_sub')}</p>
        </div>
        <div className="brand-foot">BACKOFFICE.FHORTTEXTILE.TECH</div>
      </div>

      {/* ===== DRETA : ACCÉS ===== */}
      <div className="panel">
        <div className="panel-top">
          <div className="lang" role="group" aria-label="Idioma">
            {SUPPORTED_LANGUAGES.map(l => (
              <button
                key={l}
                type="button"
                className={l === currentLang ? 'active' : ''}
                onClick={() => i18n.changeLanguage(l)}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="panel-body">
          <form onSubmit={handleSubmit}>
            <h2 className="welcome">{t('login.welcome')}</h2>
            <p className="welcome-sub">{t('login.welcome_sub')}</p>

            <div className="field">
              <label htmlFor="login-email">{t('login.email')}</label>
              <div className="input-shell">
                <MailIcon />
                <input
                  id="login-email"
                  type="email"
                  autoComplete="username"
                  placeholder={t('login.email_placeholder')}
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div className="field">
              <label htmlFor="login-pw">{t('login.password')}</label>
              <div className="input-shell">
                <LockIcon />
                <input
                  id="login-pw"
                  type={showPw ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                />
                <button
                  className="pw-toggle"
                  type="button"
                  aria-label={t('login.password')}
                  onClick={() => setShowPw(s => !s)}
                >
                  <EyeIcon off={showPw} />
                </button>
              </div>
            </div>

            <div className="row-aux">
              <label className="remember">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={e => setRemember(e.target.checked)}
                />
                {t('login.remember')}
              </label>
            </div>

            {error && <p className="err">{error}</p>}

            <button className="btn" type="submit" disabled={loading}>
              {loading ? t('login.loading') : t('login.submit')}
            </button>

            <div className="divider"><span>{t('login.or')}</span></div>
            <p className="help">
              {t('login.no_access')}<br />
              <a href="#" onClick={e => e.preventDefault()}>{t('login.contact_admin')}</a>
            </p>
          </form>
        </div>

        <div className="panel-foot">© 2026 FHORT Management SL</div>
      </div>
    </div>
  )
}

// Estils del login. Variables de marca scoped a `.login-screen` (ombregen els tokens
// globals només dins d'aquest subarbre); pseudo-elements, focus, hover, màscara de
// textura, keyframes i el breakpoint responsive no es poden fer amb estils inline.
const LOGIN_CSS = `
.login-screen{
  --gold:#c27a2a;--gold-d:#a8651f;--gold-l:#d18b3e;--gold-pale:#f7ede0;--gold-xpale:#fdf8f2;
  --ch:#1d1d1b;--gray:#868685;--gray-l:#f4f4f3;--gray-m:#e6e6e4;--white:#fff;
  --mono:'IBM Plex Mono',monospace;--sans:'Montserrat',sans-serif;
  display:grid;grid-template-columns:60% 40%;width:100%;min-height:100vh;
  font-family:var(--mono);color:var(--ch);background:var(--gray-l);-webkit-font-smoothing:antialiased;
}
.login-screen *,.login-screen *::before,.login-screen *::after{box-sizing:border-box}
.login-screen .brand{position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;padding:0 7vw;
  background:radial-gradient(120% 90% at 12% 18%,var(--gold-xpale) 0%,transparent 55%),radial-gradient(130% 120% at 92% 96%,var(--gold-pale) 0%,transparent 48%),linear-gradient(135deg,#fff 0%,#fbfbfa 60%,var(--gold-xpale) 100%);}
.login-screen .brand::before{content:"";position:absolute;inset:0;pointer-events:none;opacity:.20;background-size:56px 56px;
  background-image:linear-gradient(var(--gray-m) 1px,transparent 1px),linear-gradient(90deg,var(--gray-m) 1px,transparent 1px);
  -webkit-mask-image:radial-gradient(80% 80% at 30% 40%,#000 0%,transparent 75%);mask-image:radial-gradient(80% 80% at 30% 40%,#000 0%,transparent 75%);}
.login-screen .accent{position:absolute;border-radius:50%;filter:blur(2px);pointer-events:none}
.login-screen .accent.a1{width:14px;height:14px;background:var(--gold);top:14%;left:62%;opacity:.35}
.login-screen .accent.a2{width:8px;height:8px;background:var(--gold-l);top:74%;left:22%;opacity:.4}
.login-screen .brand-inner{position:relative;z-index:1;max-width:560px;animation:login-rise .7s cubic-bezier(.2,.7,.2,1) both}
.login-screen .brand-logo{margin-bottom:40px}
.login-screen .logo{width:340px;max-width:62%}
.login-screen .logo svg{width:100%;height:auto;display:block}
.login-screen .brand-logo .lb{display:block;font-family:var(--mono);font-weight:400;font-size:clamp(14px,1.4vw,19px);letter-spacing:.34em;text-transform:uppercase;color:var(--ch);margin-top:16px;padding-left:.06em}
.login-screen .tagline{font-family:var(--sans);font-weight:700;font-size:clamp(26px,2.6vw,40px);line-height:1.12;letter-spacing:-.02em;color:var(--ch);max-width:18ch}
.login-screen .tagsub{margin-top:18px;font-family:var(--mono);font-size:14px;font-weight:400;letter-spacing:.01em;color:#5c5c5a;max-width:46ch;line-height:1.6}
.login-screen .brand-foot{position:absolute;bottom:34px;left:7vw;z-index:1;font-family:var(--mono);font-size:12px;letter-spacing:.14em;color:var(--gray)}
.login-screen .panel{background:var(--white);display:flex;flex-direction:column;position:relative;padding:0 clamp(32px,4vw,64px);
  box-shadow:-1px 0 0 var(--gray-m),-28px 0 60px -40px rgba(29,29,27,.25);}
.login-screen .panel-top{display:flex;justify-content:flex-end;align-items:center;padding-top:30px}
.login-screen .lang{display:inline-flex;border:1px solid var(--gray-m);border-radius:9px;overflow:hidden;background:var(--gray-l)}
.login-screen .lang button{font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:.05em;border:0;background:transparent;color:var(--gray);padding:7px 13px;cursor:pointer;transition:.15s}
.login-screen .lang button+button{border-left:1px solid var(--gray-m)}
.login-screen .lang button.active{background:var(--gold);color:#fff}
.login-screen .lang button:not(.active):hover{color:var(--ch);background:var(--gray-m)}
.login-screen .panel-body{flex:1;display:flex;flex-direction:column;justify-content:center;max-width:380px;width:100%;margin:0 auto;padding-bottom:40px;animation:login-rise .7s .08s cubic-bezier(.2,.7,.2,1) both}
.login-screen .welcome{font-family:var(--sans);font-weight:800;font-size:27px;letter-spacing:-.01em;margin-bottom:6px}
.login-screen .welcome-sub{font-family:var(--mono);font-size:13px;color:var(--gray);margin-bottom:34px;letter-spacing:.01em}
.login-screen .field{margin-bottom:18px}
.login-screen .field label{display:block;font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:#5c5c5a;margin-bottom:8px}
.login-screen .input-shell{position:relative;display:flex;align-items:center}
.login-screen .input-shell .ico{position:absolute;left:14px;width:16px;height:16px;color:var(--gray);pointer-events:none}
.login-screen .field input{width:100%;font-family:var(--mono);font-size:14px;color:var(--ch);background:var(--gray-l);border:1.5px solid var(--gray-m);border-radius:11px;padding:13px 14px 13px 40px;transition:.15s;outline:none}
.login-screen .field input::placeholder{color:#a8a8a6}
.login-screen .field input:focus{border-color:var(--gold);background:#fff;box-shadow:0 0 0 3px var(--gold-pale)}
.login-screen .pw-toggle{position:absolute;right:10px;background:transparent;border:0;cursor:pointer;color:var(--gray);padding:6px;display:flex;border-radius:6px;transition:.15s}
.login-screen .pw-toggle:hover{color:var(--gold);background:var(--gold-pale)}
.login-screen .pw-toggle svg{width:17px;height:17px}
.login-screen .row-aux{display:flex;justify-content:space-between;align-items:center;margin:-2px 0 26px}
.login-screen .remember{display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:12px;color:#5c5c5a;cursor:pointer;user-select:none}
.login-screen .remember input{accent-color:var(--gold);width:15px;height:15px;cursor:pointer}
.login-screen .btn{width:100%;font-family:var(--mono);font-size:14px;font-weight:700;letter-spacing:.06em;color:#fff;background:var(--gold);border:0;border-radius:11px;padding:15px;cursor:pointer;transition:.18s;box-shadow:0 8px 20px -10px rgba(194,122,42,.7)}
.login-screen .btn:hover{background:var(--gold-d);transform:translateY(-1px);box-shadow:0 12px 26px -10px rgba(194,122,42,.8)}
.login-screen .btn:active{transform:translateY(0)}
.login-screen .btn:disabled{opacity:.6;cursor:not-allowed;transform:none;box-shadow:none}
.login-screen .err{font-family:var(--mono);font-size:12px;color:#a32d2d;text-align:center;margin:-8px 0 16px}
.login-screen .divider{display:flex;align-items:center;gap:14px;margin:26px 0 22px;color:var(--gray)}
.login-screen .divider::before,.login-screen .divider::after{content:"";flex:1;height:1px;background:var(--gray-m)}
.login-screen .divider span{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase}
.login-screen .help{font-family:var(--mono);font-size:12px;color:var(--gray);text-align:center;line-height:1.7}
.login-screen .help a,.login-screen .help button{color:var(--gold-d);text-decoration:none;font-weight:600;font-family:var(--mono);font-size:12px;background:none;border:0;cursor:pointer;padding:0}
.login-screen .help a:hover,.login-screen .help button:hover{text-decoration:underline}
.login-screen .panel-foot{font-family:var(--mono);font-size:11px;color:var(--gray);text-align:center;padding-bottom:26px;letter-spacing:.05em}
@keyframes login-rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@media (max-width:920px){.login-screen{grid-template-columns:1fr}.login-screen .brand{display:none}.login-screen .panel{box-shadow:none}}
`
