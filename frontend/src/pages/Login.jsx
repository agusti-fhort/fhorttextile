import { useState } from 'react'
import { useNavigate, useLocation, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore, { AUTH_VALID } from '../store/auth'
import { SUPPORTED_LANGUAGES } from '../i18n'
import { CLAU_SESSIO_CADUCADA } from '../api/sessio'
import FhortLogo from '../components/brand/FhortLogo'

const LockIcon = () => (
  <svg className="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>
  </svg>
)
const MailIcon = () => (
  <svg className="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>
  </svg>
)
const EyeIcon = ({ off }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/>
    <circle cx="12" cy="12" r="3"/>
    {off && <line x1="3" y1="3" x2="21" y2="21"/>}
  </svg>
)

export default function Login() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const login = useAuthStore(s => s.login)   // flux JWT existent — NO es toca
  const estatAuth = useAuthStore(s => s.estatAuth)

  // D'ON venia (el guard hi deixa el `from` en rebotar). Tornar-hi és el que fa que un F5 sobre
  // una ruta fonda no acabi al taulell: qui anava al taller de patró vol el taller de patró,
  // no la pàgina d'inici amb la feina a mig fer a l'altra banda de tres clics.
  const desti = location.state?.from
    ? `${location.state.from.pathname}${location.state.from.search || ''}`
    : '/'

  const resetOk = !!location.state?.resetOk   // ve de ResetPassword en èxit

  // K1 — per què s'ha acabat aquí. `sessio.tancaSessio()` fa `window.location.href`, una
  // recàrrega dura que s'emporta `location.state`; el motiu viatja per sessionStorage.
  // Es llegeix UN cop en muntar i es consumeix, perquè l'avís no persegueixi la persona
  // en el proper login voluntari.
  const [sessioCaducada] = useState(() => {
    try {
      if (!sessionStorage.getItem(CLAU_SESSIO_CADUCADA)) return false
      sessionStorage.removeItem(CLAU_SESSIO_CADUCADA)
      return true
    } catch { return false }   // mode privat
  })
  const [view, setView] = useState('login')  // 'login' | 'forgot'
  const [forgotMsg, setForgotMsg] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [remember, setRemember] = useState(false)
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const currentLang = (i18n.resolvedLanguage || i18n.language || 'ca').slice(0, 2)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)   // mateixa crida que abans
      navigate(desti, { replace: true })
    } catch (err) {
      // Resposta del servidor (400/401) → credencials; sense resposta → xarxa.
      setError(err?.response ? t('login.error_invalid') : t('login.error_generic'))
    } finally {
      setLoading(false)
    }
  }

  const handleForgot = (e) => {
    e.preventDefault()
    // No hi ha SMTP: la recuperació és mediada per admin (genera un enllaç a Usuaris i rols).
    setForgotMsg(t('login.forgot_admin_msg'))
  }

  // Amb sessió VÀLIDA, el login no es pinta: se surt cap on s'anava (D10). Sense això, qualsevol
  // rebot cap aquí era un carreró sense sortida —la sessió es carregava un frame després i la
  // pantalla es quedava demanant una contrasenya que ja no calia.
  if (estatAuth === AUTH_VALID) return <Navigate to={desti} replace />

  return (
    <div className="login-screen">
      <style>{LOGIN_CSS}</style>

      {/* ===== ESQUERRA : MARCA ===== */}
      <div className="brand">
        <span className="accent a1" /><span className="accent a2" />
        <div className="brand-inner">
          <div className="logo"><FhortLogo width="100%" /></div>
          <h1 className="tagline">{t('login.tagline')}</h1>
          <p className="tagsub">{t('login.tagline_sub')}</p>
        </div>
        <div className="brand-foot">FHORTTEXTILE.TECH</div>
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
                onClick={() => i18n.changeLanguage(l)}   // i18n existent
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="panel-body">
          {view === 'login' ? (
            <form onSubmit={handleSubmit}>
              <h2 className="welcome">{t('login.welcome')}</h2>
              <p className="welcome-sub">{t('login.welcome_sub')}</p>

              {sessioCaducada && (
                <p style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, color: '#8a5a00',
                            background: '#fbf1dc', borderRadius: 8, padding: '10px 12px', marginBottom: 16 }}>
                  {t('auth.session_expired')}
                </p>
              )}

              {resetOk && (
                <p style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, color: '#3b6d11',
                            background: '#eaf3de', borderRadius: 8, padding: '10px 12px', marginBottom: 16 }}>
                  {t('login.reset_ok')}
                </p>
              )}

              <div className="field">
                <label htmlFor="login-user">{t('login.user')}</label>
                <div className="input-shell">
                  <MailIcon />
                  <input
                    id="login-user"
                    type="email"
                    autoComplete="email"
                    placeholder={t('login.user_placeholder')}
                    value={username}
                    onChange={e => setUsername(e.target.value)}
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
                <button type="button" className="forgot" onClick={() => { setError(''); setView('forgot') }}>
                  {t('login.forgot')}
                </button>
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
          ) : (
            <form onSubmit={handleForgot}>
              <h2 className="welcome">{t('login.forgot_title')}</h2>
              <p className="welcome-sub">{t('login.forgot_sub')}</p>

              <div className="field">
                <label htmlFor="login-email">{t('login.email')}</label>
                <div className="input-shell">
                  <MailIcon />
                  <input
                    id="login-email"
                    type="email"
                    autoComplete="email"
                    placeholder={t('login.email_placeholder')}
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                  />
                </div>
              </div>

              {forgotMsg && (
                <p style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, color: '#5c5c5a',
                            background: 'var(--gold-pale, #f7ede0)', borderRadius: 8, padding: '10px 12px', margin: '4px 0 8px' }}>
                  {forgotMsg}
                </p>
              )}

              {/* Sense SMTP: informa que la recuperació la genera l'administrador (vegeu handleForgot). */}
              <button className="btn" type="submit" style={{ marginTop: 8 }}>
                {t('login.send_link')}
              </button>

              <div className="divider"><span>{t('login.or')}</span></div>
              <p className="help">
                <button type="button" onClick={() => setView('login')}>{t('login.back_login')}</button>
              </p>
            </form>
          )}
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
.login-screen .logo{width:340px;max-width:62%;margin-bottom:42px}
.login-screen .logo svg{width:100%;height:auto;display:block}
.login-screen .tagline{font-family:var(--sans);font-weight:700;font-size:clamp(26px,2.6vw,40px);line-height:1.12;letter-spacing:-.02em;color:var(--ch);max-width:18ch}
.login-screen .tagsub{margin-top:18px;font-family:var(--mono);font-size:14px;font-weight:400;letter-spacing:.01em;color:#5c5c5a;max-width:46ch;line-height:1.6}
.login-screen .brand-foot{position:absolute;bottom:34px;left:7vw;z-index:1;font-family:var(--mono);font-size:12px;letter-spacing:.14em;color:var(--gray)}
.login-screen .panel{background:var(--white);display:flex;flex-direction:column;position:relative;padding:0 clamp(32px,4vw,64px);
  box-shadow:-1px 0 0 var(--gray-m),-28px 0 60px -40px rgba(29,29,27,.25);}
.login-screen .panel-top{display:flex;justify-content:flex-end;align-items:center;padding-top:30px}
.login-screen .lang{display:inline-flex;border:1px solid var(--gray-m);border-radius:9px;overflow:hidden;background:var(--gray-l)}
.login-screen .lang button{font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:.05em;border:0;background:transparent;color:var(--gray);padding:7px 13px;cursor:pointer;transition:.15s}
.login-screen .lang button+button{border-left:1px solid var(--gray-m)}
.login-screen .lang button.active{background:var(--gold);color:var(--text-main)}
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
.login-screen .forgot{font-family:var(--mono);font-size:12px;font-weight:600;color:var(--gold-d);text-decoration:none;letter-spacing:.01em;background:none;border:0;cursor:pointer;padding:0}
.login-screen .forgot:hover{text-decoration:underline}
.login-screen .btn{width:100%;font-family:var(--mono);font-size:14px;font-weight:700;letter-spacing:.06em;color:var(--white);background:var(--accio);border:0;border-radius:11px;padding:15px;cursor:pointer;transition:.18s;box-shadow:0 8px 20px -10px rgba(43,101,194,.7)}
.login-screen .btn:hover{background:var(--accio-hover);transform:translateY(-1px);box-shadow:0 12px 26px -10px rgba(43,101,194,.8)}
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
