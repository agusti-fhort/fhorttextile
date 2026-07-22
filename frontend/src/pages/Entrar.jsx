import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { authCentral } from '../api/endpoints'
import useAuthStore from '../store/auth'

/**
 * PORTA ÚNICA — email + contrasenya un sol cop i s'acaba DINS del propi espai de treball.
 *
 * És una RUTA de l'únic build, no una aplicació a part: aquesta pantalla no sap ni ha de
 * saber en quin domini viu (client.js:3-19). A PROD el host neutre hi arribarà per un rewrite
 * de nginx; a staging s'hi arriba per la ruta directa. El mateix codi serveix els dos casos.
 *
 * El flux té tres estacions i la persona només en veu dues:
 *   1. credencials → POST /api/auth/central/ (prova la contrasenya a cada schema on hi és)
 *   2. si té MÉS D'UN espai, tria (la contrasenya ja no torna a viatjar: va amb un tiquet)
 *   3. codi d'un sol ús → sessió. Si l'espai és aquest mateix host, aquí mateix; si no,
 *      redirecció al seu domini amb ?code= i el bescanvi es fa allà, same-origin.
 *
 * QUI DECIDEIX EL DOMÍNI ÉS EL BACKEND. `workspace.host` i `workspace.mateix_host` venen de la
 * resposta; aquí no es construeix cap URL a partir del que es veu per la finestra. A staging el
 * domini primari del tenant és el de PRODUCCIÓ, i un client que "deduís" el destí ens hi hauria
 * enviat.
 */
const MONO = 'IBM Plex Mono, monospace'

export default function Entrar() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const entraAmbCodi = useAuthStore(s => s.entraAmbCodi)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [estat, setEstat] = useState('form')   // 'form' | 'enviant' | 'tria' | 'entrant' | 'error'
  const [errKey, setErrKey] = useState('entrar.error_generic')
  const [tria, setTria] = useState(null)       // { seleccio, workspaces } quan n'hi ha més d'un

  // L'aterratge amb ?code= ha de córrer UN SOL COP. En dev, StrictMode munta dos cops i el
  // segon bescanvi trobaria el codi ja cremat (és d'un sol ús a posta) → error fals.
  const codiConsumit = useRef(false)

  const falla = (key) => { setErrKey(key); setEstat('error') }

  // Un codi a la URL vol dir que això no és un formulari: és l'última passa d'un login que ja
  // ha passat. No es pinta res que convidi a re-escriure credencials.
  const bescanvia = async (code) => {
    setEstat('entrant')
    try {
      await entraAmbCodi(code)
      // El codi fora de la barra d'adreces abans de continuar: ja no val per res, però no ha
      // de quedar a l'historial ni viatjar en un Referer.
      window.history.replaceState({}, '', '/entrar')
      navigate('/', { replace: true })
    } catch {
      falla('entrar.error_codi')
    }
  }

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get('code')
    if (code && !codiConsumit.current) {
      codiConsumit.current = true
      bescanvia(code)
    }
  }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  // Un workspace resolt (ve del login directe o de la tria): o s'hi entra aquí, o s'hi va.
  const entraAlWorkspace = (workspace, code) => {
    if (workspace?.mateix_host) return bescanvia(code)   // C5: ja hi som, no cal sortir
    if (!workspace?.host) return falla('entrar.error_generic')
    setEstat('entrant')
    window.location.href = `https://${workspace.host}/entrar?code=${encodeURIComponent(code)}`
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    if (!email.trim() || !password || estat === 'enviant') return
    setEstat('enviant')
    try {
      const { data } = await authCentral.entra(email.trim(), password)
      setPassword('')   // no es reté: la tria mai la necessita
      if (data.mena === 'seleccio') {
        setTria({ seleccio: data.seleccio, workspaces: data.workspaces || [] })
        setEstat('tria')
      } else {
        entraAlWorkspace(data.workspace, data.code)
      }
    } catch (err) {
      const codi = err?.response?.status
      falla(codi === 429 ? 'entrar.error_throttled'
        : codi === 401 || codi === 400 ? 'entrar.error_credencials'
        : 'entrar.error_generic')
    }
  }

  const onTria = async (schema) => {
    setEstat('entrant')
    try {
      const { data } = await authCentral.tria(tria.seleccio, schema)
      entraAlWorkspace(data.workspace, data.code)
    } catch {
      falla('entrar.error_codi')
    }
  }

  const tornaAlFormulari = () => {
    setTria(null); setPassword(''); setEstat('form')
    window.history.replaceState({}, '', '/entrar')
  }

  const entrant = estat === 'entrant'

  return (
    <div style={wrap}>
      <div style={card}>
        {entrant ? (
          <div style={{ textAlign: 'center' }}>
            <i className="ti ti-loader-2" style={icona} aria-hidden="true" />
            <h1 style={title}>{t('entrar.entrant')}</h1>
            <p style={sub}>{t('entrar.entrant_sub')}</p>
          </div>
        ) : estat === 'tria' ? (
          <>
            <h1 style={title}>{t('entrar.tria_title')}</h1>
            <p style={sub}>{t('entrar.tria_sub')}</p>
            <ul style={llista}>
              {tria.workspaces.map(w => (
                <li key={w.schema}>
                  <button type="button" onClick={() => onTria(w.schema)} style={targeta}>
                    <i className="ti ti-building-store" style={iconaTargeta} aria-hidden="true" />
                    <span style={{ flex: 1, textAlign: 'left' }}>
                      <span style={nomWs}>{w.nom}</span>
                      <span style={hostWs}>{w.host}</span>
                    </span>
                    <i className="ti ti-chevron-right" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
            <button type="button" onClick={tornaAlFormulari} style={linkBtn}>
              {t('entrar.tria_enrere')}
            </button>
          </>
        ) : (
          <form onSubmit={onSubmit}>
            <h1 style={title}>{t('entrar.title')}</h1>
            <p style={sub}>{t('entrar.subtitle')}</p>

            <label htmlFor="entrar-email" style={lbl}>{t('entrar.email_label')}</label>
            <input id="entrar-email" type="email" autoComplete="email" required autoFocus
              value={email} onChange={e => setEmail(e.target.value)}
              placeholder={t('entrar.email_ph')} style={input} />

            <label htmlFor="entrar-pw" style={{ ...lbl, marginTop: 14 }}>{t('entrar.password_label')}</label>
            <input id="entrar-pw" type="password" autoComplete="current-password" required
              value={password} onChange={e => setPassword(e.target.value)}
              placeholder={t('entrar.password_ph')} style={input} />

            {estat === 'error' && <div style={errBox} role="alert">{t(errKey)}</div>}

            <button type="submit" disabled={estat === 'enviant'} style={{
              ...submitBtn, opacity: estat === 'enviant' ? 0.6 : 1,
              cursor: estat === 'enviant' ? 'wait' : 'pointer',
            }}>
              {estat === 'enviant' ? t('entrar.submitting') : t('entrar.submit')}
            </button>

            {/* Fallback «no sé quin és el meu espai»: la peça de backend hi és (discovery) però
                el correu no surt — no hi ha SMTP (DIAGNOSI_LOGIN_UNIC §B2.3). Es mostra
                desactivat en comptes d'amagat perquè la sortida existeixi a la vista de qui
                s'hi encalla; s'activarà quan el correu sigui real. */}
            <button type="button" disabled title={t('entrar.oblidat_aviat')}
              style={linkDeshabilitat} aria-disabled="true">
              {t('entrar.oblidat')}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

const wrap = { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-page)', padding: 24 }
const card = { width: 400, maxWidth: '92vw', background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 12, padding: 32, boxShadow: '0 8px 32px rgba(0,0,0,0.08)', fontFamily: MONO }
const title = { fontSize: 'var(--fs-h2)', fontFamily: MONO, fontWeight: 500, color: 'var(--text-main)', margin: '8px 0 6px' }
const sub = { fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: '0 0 20px', lineHeight: 1.5 }
const lbl = { display: 'block', fontSize: 'var(--fs-label)', textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--gray)', marginBottom: 6 }
const input = { width: '100%', padding: '10px 12px', border: '0.5px solid var(--gray-l)', borderRadius: 8, fontSize: 'var(--fs-body)', fontFamily: MONO, background: 'var(--white)', color: 'var(--text-main)', boxSizing: 'border-box' }
const submitBtn = { width: '100%', marginTop: 18, padding: '11px 14px', background: 'var(--gold)', color: 'var(--white)', border: 'none', borderRadius: 8, fontSize: 'var(--fs-body)', fontWeight: 600, fontFamily: MONO }
const linkBtn = { marginTop: 18, background: 'none', border: 'none', color: 'var(--gold)', fontSize: 'var(--fs-body)', fontFamily: MONO, cursor: 'pointer', textDecoration: 'underline' }
const linkDeshabilitat = { ...linkBtn, display: 'block', width: '100%', marginTop: 16, color: 'var(--gray)', cursor: 'not-allowed', textDecoration: 'none' }
const errBox = { marginTop: 12, padding: '8px 12px', borderRadius: 8, background: 'var(--err-bg)', color: 'var(--err)', fontSize: 'var(--fs-body)' }
const icona = { fontSize: 40, color: 'var(--gold)' }
const llista = { listStyle: 'none', margin: '0 0 4px', padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }
const targeta = { width: '100%', display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 8, fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)', cursor: 'pointer' }
const iconaTargeta = { fontSize: 20, color: 'var(--gold)' }
const nomWs = { display: 'block', fontWeight: 600 }
const hostWs = { display: 'block', fontSize: 'var(--fs-label)', color: 'var(--gray)' }
