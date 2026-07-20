import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { tenantDiscovery } from '../api/endpoints'

// Porta ÚNICA (tenant-discovery). Pantalla neutra: l'usuari escriu el correu i, si té compte
// en algun espai, rep un correu amb l'accés. La resposta és SEMPRE la mateixa ("revisa el
// correu") — mai revela si l'adreça existeix (privadesa: la revelació només arriba a la bústia).
const MONO = 'IBM Plex Mono, monospace'

export default function Entrar() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [state, setState] = useState('form')   // 'form' | 'sending' | 'sent' | 'error'
  const [errKey, setErrKey] = useState('discovery.error')

  const onSubmit = async (e) => {
    e.preventDefault()
    if (!email.trim() || state === 'sending') return
    setState('sending')
    try {
      await tenantDiscovery.submit(email.trim())
      setState('sent')   // èxit uniforme: sempre "revisa el correu"
    } catch (err) {
      setErrKey(err?.response?.status === 429 ? 'discovery.throttled' : 'discovery.error')
      setState('error')
    }
  }

  return (
    <div style={wrap}>
      <div style={card}>
        {state === 'sent' ? (
          <div style={{ textAlign: 'center' }}>
            <i className="ti ti-mail-check" style={{ fontSize: 40, color: 'var(--gold)' }} aria-hidden="true" />
            <h1 style={title}>{t('discovery.sent_title')}</h1>
            <p style={sub}>{t('discovery.sent_body')}</p>
            <button type="button" onClick={() => { setEmail(''); setState('form') }} style={linkBtn}>
              {t('discovery.retry')}
            </button>
          </div>
        ) : (
          <form onSubmit={onSubmit}>
            <h1 style={title}>{t('discovery.title')}</h1>
            <p style={sub}>{t('discovery.subtitle')}</p>
            <label htmlFor="disc-email" style={lbl}>{t('discovery.email_label')}</label>
            <input id="disc-email" type="email" autoComplete="email" required autoFocus
              value={email} onChange={e => setEmail(e.target.value)}
              placeholder={t('discovery.email_ph')} style={input} />
            {state === 'error' && <div style={errBox}>{t(errKey)}</div>}
            <button type="submit" disabled={state === 'sending'} style={{
              ...submitBtn, opacity: state === 'sending' ? 0.6 : 1,
              cursor: state === 'sending' ? 'wait' : 'pointer',
            }}>
              {state === 'sending' ? t('discovery.sending') : t('discovery.submit')}
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
const errBox = { marginTop: 12, padding: '8px 12px', borderRadius: 8, background: 'var(--err-bg)', color: 'var(--err)', fontSize: 'var(--fs-body)' }
