import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { llegeixExpMs } from '../api/jwt'
import { sessio } from '../api/sessio'
import { calAvisar, ESTAT_CADUCADA, estatSessio, TICK_AVIS_MS } from '../api/avisSessio'
import useAuthStore from '../store/auth'
import { overlayBase, Z_GUARD } from './ui/overlay'

/**
 * K5 · Avís de caducitat de SESSIÓ (no d'access token).
 *
 * L'access token caduca cada hora i es refresca sol: això no és cap esdeveniment per a
 * ningú i no s'ha d'anunciar. El que sí que s'acaba de debò és la SESSIÓ — el refresh
 * token—, i fins ara s'acabava sense avís: la persona es trobava expulsada.
 *
 * D'ON SURT LA DATA: es decodifica el refresh token i se'n llegeix `exp` (vegeu `api/jwt.js`
 * per què aquest camí i no el proxy sobre l'access). La sessió és LLISCANT: cada refresh en
 * rota un de nou amb 7 dies més, així que l'`exp` que val és sempre el del token que hi ha
 * ara al localStorage — per això es rellegeix a cada tick i no es memoritza.
 *
 * UN MODAL PER CICLE: `expVist` recorda l'`exp` pel qual ja s'ha preguntat. Prémer «Continua
 * treballant» refresca i el token nou porta un `exp` nou → el modal es tornarà a armar per a
 * aquell cicle, no per a aquest. Si es tanca sense respondre, tampoc reapareix: quan venci,
 * mana K1 (missatge humà a /login, mai el JSON).
 *
 * Es raona amb instants absoluts i sondeig curt, no amb un `setTimeout` llarg: un timer de
 * dies no sobreviu a la suspensió del portàtil, que és justament quan això ha de servir.
 */
const MONO = 'IBM Plex Mono, monospace'

export default function AvisSessio() {
  const { t } = useTranslation()
  const logout = useAuthStore(s => s.logout)
  const [obert, setObert] = useState(false)
  const [ocupat, setOcupat] = useState(false)
  // `exp` pel qual ja s'ha preguntat (o que s'ha decidit no tornar a preguntar).
  const expVist = useRef(null)

  useEffect(() => {
    const mira = () => {
      let refresh = null
      try { refresh = localStorage.getItem('refresh_token') } catch { /* mode privat */ }
      if (!refresh) return                       // sense sessió: res a avisar
      const expMs = llegeixExpMs(refresh)
      const ara = Date.now()

      // Ja caducada: no és feina d'aquest modal preguntar res. El primer 401 dispararà K1,
      // que ja acaba amb missatge humà. Es marca com a vist per no obrir-lo a destemps.
      if (estatSessio(expMs, ara) === ESTAT_CADUCADA) { expVist.current = expMs; return }

      if (calAvisar(expMs, ara, expVist.current)) {
        expVist.current = expMs   // aquest cicle ja queda preguntat: mai en bucle
        setObert(true)
      }
    }
    mira()
    const id = setInterval(mira, TICK_AVIS_MS)
    // En tornar el focus es mira de seguida: la pestanya pot haver estat hores en segon pla.
    const alTornar = () => { if (document.visibilityState === 'visible') mira() }
    document.addEventListener('visibilitychange', alTornar)
    return () => { clearInterval(id); document.removeEventListener('visibilitychange', alTornar) }
  }, [])

  // «Continua treballant» — refresh EXPLÍCIT pel mateix mutex compartit que tota la resta.
  // Si falla, `sessio.refresca()` ja tanca la sessió i redirigeix amb el missatge de K1;
  // aquí no cal fer-hi res més que no quedar-se amb el modal obert per sobre.
  const continua = async () => {
    setOcupat(true)
    try { await sessio.refresca() } catch { /* K1 se n'ocupa */ }
    finally { setOcupat(false); setObert(false) }
  }

  // «Tancar sessió» — sortida NETA amb el token encara viu: `logout` pausa la tasca En curs
  // abans de marxar (K6, cas fiable).
  const surt = async () => {
    setOcupat(true)
    try { await logout() } catch { setOcupat(false) }
  }

  if (!obert) return null

  return (
    // Sense tancar al clic fora: la pregunta demana una resposta. Mateix criteri que el
    // guard de tasca oblidada, i mateixa capa z (per sobre dels editors a pantalla completa).
    <div role="dialog" aria-modal="true" style={overlayBase({ alignItems: 'center', zIndex: Z_GUARD })}>
      <div style={{ background: 'var(--white)', borderRadius: 12, padding: 22, width: 460, maxWidth: '92vw' }}>
        <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 4, fontFamily: MONO,
                     display: 'flex', alignItems: 'center', gap: 8 }}>
          <i className="ti ti-clock-exclamation" style={{ color: 'var(--warn)' }} />
          {t('auth.session_expiring_title')}
        </h2>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 18 }}>
          {t('auth.session_expiring_body')}
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
          <button type="button" disabled={ocupat} onClick={surt}
            style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '7px 14px', borderRadius: 6,
                     border: '0.5px solid var(--gray-l)', background: 'var(--white)',
                     color: 'var(--text-main)', cursor: ocupat ? 'wait' : 'pointer' }}>
            {t('auth.session_logout')}
          </button>
          <button type="button" disabled={ocupat} onClick={continua}
            style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '7px 14px', borderRadius: 6,
                     border: 'none', background: 'var(--gold)', color: 'var(--text-main)',
                     fontWeight: 600, cursor: ocupat ? 'wait' : 'pointer' }}>
            {t('auth.session_keep')}
          </button>
        </div>
      </div>
    </div>
  )
}
