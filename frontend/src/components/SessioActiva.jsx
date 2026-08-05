import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { modelTasks, timers } from '../api/endpoints'
import { durada, estatSessio, segonsDeSessio } from '../utils/sessioActiva'

/**
 * F2.3 · INDICADOR PERSISTENT DE SESSIÓ + EL GEST D'ACABAR (D-2).
 *
 * UN component per a tota l'app, muntat al costat de `GuardTascaOblidada` a `App.jsx`, i no un
 * botó per pantalla: el tècnic salta de Mesures a Fitxa a Escalat i la sessió és la mateixa cosa
 * a totes. Un Stop per superfície voldria dir cinc llocs on el gest que factura pot divergir.
 *
 * Per què això existeix: des de F1, **desar ja no tanca res** i el Stop és l'ÚNIC gest que porta
 * una tasca a Done — i Done és el que entra a albarà. Un gest amb aquesta conseqüència no pot
 * dependre de recordar-se'n: ha de veure's sempre, amb el nom del que està obert i des de quan.
 *
 * La confirmació és UNA FRASE, no un modal pesat: acabar és normal, i el diàleg ha de pesar el
 * que pesa el gest.
 *
 * ⚠️ DEUTE CONEGUT: aquest component sondeja `timers.list` pel seu compte, com fa
 * `GuardTascaOblidada`. Són dues preguntes diferents (ell vigila la INACTIVITAT, això mostra la
 * PRESÈNCIA) i tenen modes de fallada diferents, però llegeixen el mateix endpoint. Convergir-los
 * en una font única és feina de F3, anotada al report.
 */

const REFRESC_MS = 60_000   // el mateix ritme que el guard: la sessió no canvia més de pressa
const TICK_MS = 30_000      // només per repintar la durada; l'instant absolut mana

export default function SessioActiva() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [sessio, setSessio] = useState(null)
  const [ara, setAra] = useState(() => Date.now())
  const [confirmant, setConfirmant] = useState(false)
  const [tancant, setTancant] = useState(false)
  const viu = useRef(true)

  const llegeix = useCallback(() => {
    return timers.list({ actiu: 'true' })
      .then(res => {
        const files = res?.data?.results ?? res?.data ?? []
        const obert = (Array.isArray(files) ? files : []).find(f => f.fi == null)
        if (!obert) { if (viu.current) setSessio(null); return }
        // La font de veritat és l'ESTAT DE LA TASCA; el tram només hi posa el rellotge.
        return modelTasks.get(obert.model_task)
          .then(r => { if (viu.current) setSessio(estatSessio(obert, r?.data)) })
      })
      .catch(() => { if (viu.current) setSessio(null) })
  }, [])

  useEffect(() => {
    viu.current = true
    llegeix()
    const id = setInterval(llegeix, REFRESC_MS)
    return () => { viu.current = false; clearInterval(id) }
  }, [llegeix])

  useEffect(() => {
    const id = setInterval(() => setAra(Date.now()), TICK_MS)
    return () => clearInterval(id)
  }, [])

  const acaba = () => {
    if (!sessio || tancant) return
    setTancant(true)
    modelTasks.transition(sessio.taskId, { to_status: 'Done' })
      .then(() => { setConfirmant(false); return llegeix() })
      .catch(() => setConfirmant(false))
      .finally(() => setTancant(false))
  }

  if (!sessio) return null
  const mins = durada(segonsDeSessio({ inici: sessio.inici }, ara))

  return (
    <div style={{
      position: 'fixed', bottom: 16, right: 16, zIndex: 900,
      display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end',
      fontFamily: 'IBM Plex Mono, monospace',
    }}>
      {confirmant && (
        <div style={{
          background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 8,
          padding: '10px 14px', maxWidth: 320, boxShadow: '0 4px 18px rgba(0,0,0,0.14)',
        }}>
          <p style={{ margin: '0 0 10px', fontSize: 'var(--fs-body)', lineHeight: 1.45 }}>
            {t('sessio.confirma', { tasca: sessio.nom })}
          </p>
          <p style={{ margin: '0 0 12px', fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
            {t('sessio.confirma_nota')}
          </p>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button onClick={() => setConfirmant(false)} disabled={tancant} style={{
              fontFamily: 'inherit', fontSize: 'var(--fs-body)', padding: '5px 10px',
              border: 'none', background: 'transparent', color: 'var(--text-muted)',
              cursor: tancant ? 'not-allowed' : 'pointer',
            }}>{t('common.cancel')}</button>
            <button onClick={acaba} disabled={tancant} style={{
              fontFamily: 'inherit', fontSize: 'var(--fs-body)', fontWeight: 600,
              padding: '5px 12px', border: 'none', borderRadius: 6,
              background: 'var(--gold)', color: 'var(--white)',
              cursor: tancant ? 'not-allowed' : 'pointer', opacity: tancant ? 0.5 : 1,
            }}>{t('sessio.acabar')}</button>
          </div>
        </div>
      )}

      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 999,
        padding: '6px 8px 6px 14px', boxShadow: '0 2px 12px rgba(0,0,0,0.10)',
      }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%', background: 'var(--gold)', flexShrink: 0,
        }} />
        <button
          onClick={() => sessio.modelId && navigate(`/models/${sessio.modelId}`)}
          title={t('sessio.anar_al_model')}
          style={{
            border: 'none', background: 'transparent', padding: 0, cursor: 'pointer',
            fontFamily: 'inherit', fontSize: 'var(--fs-body)', color: 'var(--text-main)',
            display: 'flex', alignItems: 'baseline', gap: 8,
          }}
        >
          <span style={{ fontWeight: 500 }}>{sessio.nom}</span>
          <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
            {sessio.model}
          </span>
          <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--text-muted)' }}>
            {mins}
          </span>
        </button>
        <button
          onClick={() => setConfirmant(v => !v)}
          title={t('sessio.acabar')}
          style={{
            display: 'flex', alignItems: 'center', gap: 5, border: 'none', borderRadius: 999,
            background: 'var(--gold)', color: 'var(--white)', cursor: 'pointer',
            padding: '5px 12px', fontFamily: 'inherit', fontSize: 'var(--fs-body)', fontWeight: 600,
          }}
        >
          <i className="ti ti-player-stop" />
          {t('sessio.acabar')}
        </button>
      </div>
    </div>
  )
}
