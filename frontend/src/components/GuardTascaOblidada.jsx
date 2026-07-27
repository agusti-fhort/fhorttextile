import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { modelTasks, timers } from '../api/endpoints'
import { taskTypeLabel } from '../utils/taskType'
import { primaryBtn, selS } from './ui/buttons'
import { overlayBase, Z_GUARD } from './ui/overlay'

/**
 * Guard de tasca oblidada — global, muntat dins de ProtectedRoute.
 *
 * Una tasca que es queda En curs tota la nit contamina el temps real del model i, per
 * `record_actual_time`, l'estadística Welford de la cel·la. El guard hi posa un límit: als 30
 * minuts pregunta si la persona hi segueix, i si no respon en 3 minuts, pausa.
 *
 * TRES DECISIONS QUE MANEN AQUÍ:
 *
 * 1. **Tot es deriva de l'ÀNCORA, mai d'un comptador acumulat.** L'àncora és el segell del
 *    servidor (`last_heartbeat`, o `inici` si no n'hi ha hagut cap) i els dos terminis en surten
 *    com a instants absoluts. Un `setInterval` que sumés segons mentiria: les pestanyes en segon
 *    pla se'ls throttlegen i el rellotge quedaria endarrerit exactament en el cas que el guard ha
 *    de cobrir. Aquí el tick només serveix per REPINTAR; qui decideix és `Date.now()` contra els
 *    instants. Per això tornar el focus després de dues hores no necessita cap lògica especial:
 *    el termini ja ha vençut i es pausa, sense dependre de quan es va arribar a pintar el modal.
 *
 * 2. **El disparador és la DURADA des de l'obertura, no la inactivitat.** No s'escolta ni teclat
 *    ni ratolí: es compta des del senyal, i confirmar el modal rearma 30 minuts més.
 *
 * 3. **L'auto-pausa MAI és Done.** El Stop és humà (llei intacta). Passa pel MATEIX
 *    `transition_task` que el kanban, amb `auto='guard_30min'` perquè el log no digui que la
 *    pausa la va fer el tècnic.
 *
 * QA: per no esperar 30 minuts reals, els llindars es poden escurçar per sessió de navegador
 *   localStorage.setItem('ftt_guard_llindar_min', '1')
 *   localStorage.setItem('ftt_guard_gracia_min', '0.5')
 * i recarregar. Sense les claus, els valors de producció.
 */

const LLINDAR_MIN = llegeixMinuts('ftt_guard_llindar_min', 30)   // fins a l'avís
const GRACIA_MIN = llegeixMinuts('ftt_guard_gracia_min', 3)      // per respondre'l
const REFRESC_MS = 60_000   // re-llegeix quin és el tram obert (pot haver-ne començat un altre)
const TICK_MS = 1_000

function llegeixMinuts(clau, defecte) {
  try {
    const cru = Number(window.localStorage.getItem(clau))
    return Number.isFinite(cru) && cru > 0 ? cru : defecte
  } catch {
    return defecte   // localStorage bloquejat (mode privat): el guard no es queda sense llindar
  }
}

const MONO = 'IBM Plex Mono, monospace'
const msDeMinuts = (m) => Math.round(m * 60_000)

/** Compte enrere en mm:ss, mai negatiu. */
function compteEnrere(ms) {
  const s = Math.max(0, Math.ceil(ms / 1000))
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

export default function GuardTascaOblidada() {
  const { t } = useTranslation()
  const [tram, setTram] = useState(null)      // {timerId, taskId, ancora} del tram obert
  const [tasca, setTasca] = useState(null)    // etiqueta de la tasca, carregada en calent
  const [ara, setAra] = useState(() => Date.now())
  const [avis, setAvis] = useState(null)      // {type:'ok'|'err', text} — toast informatiu
  const pausant = useRef(false)               // el venciment no pot disparar dues pauses

  // ── Àncora: quin tram tinc obert i des de quin senyal es compta ─────────────
  const llegeixTram = useCallback(() => {
    return timers.list({ actiu: 'true' })
      .then(res => {
        const files = res?.data?.results ?? res?.data ?? []
        const obert = (Array.isArray(files) ? files : []).find(f => f.fi == null)
        if (!obert) { setTram(null); setTasca(null); return }
        // El segell mana sobre l'obertura: confirmar el modal rearma des d'aquí.
        const ancora = new Date(obert.last_heartbeat || obert.inici).getTime()
        setTram(prev => {
          if (prev && prev.timerId === obert.id && prev.ancora === ancora) return prev
          pausant.current = false
          return { timerId: obert.id, taskId: obert.model_task, ancora }
        })
      })
      .catch(() => { /* xarxa caiguda: el cron de servidor és la xarxa de sota */ })
  }, [])

  useEffect(() => {
    llegeixTram()
    const id = setInterval(llegeixTram, REFRESC_MS)
    // En tornar el focus es rellegeix I es reposiciona el rellotge: si la pestanya ha estat
    // hores en segon pla, el termini pot haver vençut mentre ningú no mirava.
    const alTornar = () => {
      if (document.visibilityState !== 'visible') return
      setAra(Date.now())
      llegeixTram()
    }
    document.addEventListener('visibilitychange', alTornar)
    window.addEventListener('focus', alTornar)
    return () => {
      clearInterval(id)
      document.removeEventListener('visibilitychange', alTornar)
      window.removeEventListener('focus', alTornar)
    }
  }, [llegeixTram])

  // El tick NOMÉS repinta. Cap suma acumulada: el que decideix és Date.now() (vegeu §1).
  useEffect(() => {
    if (!tram) return undefined
    const id = setInterval(() => setAra(Date.now()), TICK_MS)
    return () => clearInterval(id)
  }, [tram])

  // Instants absoluts derivats de l'àncora.
  const instantAvis = tram ? tram.ancora + msDeMinuts(LLINDAR_MIN) : null
  const instantVenciment = tram ? instantAvis + msDeMinuts(GRACIA_MIN) : null
  const calAvisar = tram != null && ara >= instantAvis && ara < instantVenciment
  const haVencut = tram != null && ara >= instantVenciment

  // ── Etiqueta de la tasca: es demana només quan cal ensenyar-la ──────────────
  useEffect(() => {
    if (!calAvisar || !tram || tasca?.id === tram.taskId) return
    modelTasks.get(tram.taskId)
      .then(res => setTasca({
        id: tram.taskId,
        nom: taskTypeLabel(t, res?.data?.task_type_code, res?.data?.task_type_name),
        model: res?.data?.model_codi || '',
      }))
      .catch(() => setTasca({ id: tram.taskId, nom: `#${tram.taskId}`, model: '' }))
  }, [calAvisar, tram, tasca, t])

  // ── Auto-pausa: mateixa porta que el kanban, amb la marca del guard ─────────
  useEffect(() => {
    if (!haVencut || !tram || pausant.current) return
    pausant.current = true
    const taskId = tram.taskId
    modelTasks.transition(taskId, { to_status: 'Paused', auto: 'guard_30min' })
      .then(() => setAvis({ type: 'ok', text: t('guard_tasca.pausada') }))
      .catch(() => {
        // Ja pausada des d'una altra pestanya, o xarxa caiguda: no insistim, el cron ho recull.
        setAvis({ type: 'err', text: t('guard_tasca.pausa_fallida') })
      })
      .finally(() => { setTram(null); setTasca(null); llegeixTram() })
  }, [haVencut, tram, llegeixTram, t])

  // Confirmar = batec: el segell nou torna com a àncora i rearma el llindar sencer.
  function confirma() {
    timers.heartbeat()
      .then(() => llegeixTram())
      .catch(() => { setTram(null); llegeixTram() })   // 404: la tasca ja no és En curs → resync
  }

  function pausaAra() {
    if (!tram) return
    pausant.current = true
    modelTasks.transition(tram.taskId, { to_status: 'Paused' })   // gest HUMÀ: sense marca
      .catch(() => { /* el toast d'error no aporta res: la pausa manual es veu al kanban */ })
      .finally(() => { setTram(null); setTasca(null); llegeixTram() })
  }

  useEffect(() => {
    if (!avis) return undefined
    const id = setTimeout(() => setAvis(null), 6000)
    return () => clearTimeout(id)
  }, [avis])

  return (
    <>
      {avis && (
        <div role="status" style={{
          position: 'fixed', bottom: 20, left: '50%', transform: 'translateX(-50%)',
          zIndex: Z_GUARD, fontFamily: MONO, fontSize: 'var(--fs-body)',
          padding: '10px 16px', borderRadius: 6, maxWidth: '90vw',
          background: avis.type === 'ok' ? 'var(--ok-bg)' : 'var(--err-bg)',
          color: avis.type === 'ok' ? 'var(--ok)' : 'var(--err)',
        }}>
          {avis.text}
        </div>
      )}

      {calAvisar && (
        // Sense tancar al clic fora: la pregunta demana una resposta, i deixar-la esquivar per
        // accident amb un clic al costat és tornar al problema que el guard resol.
        <div role="dialog" aria-modal="true" style={overlayBase({ alignItems: 'center', zIndex: Z_GUARD })}>
          <div style={{
            background: 'var(--white)', borderRadius: 12, padding: 22,
            width: 460, maxWidth: '92vw',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 4, fontFamily: MONO,
                         display: 'flex', alignItems: 'center', gap: 8 }}>
              <i className="ti ti-clock-exclamation" style={{ color: 'var(--warn)' }} />
              {t('guard_tasca.titol', { minuts: Math.round(LLINDAR_MIN) })}
            </h2>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 14 }}>
              {t('guard_tasca.cos', {
                tasca: tasca?.nom || '—',
                model: tasca?.model || '—',
                minuts: Math.round(LLINDAR_MIN),
              })}
            </p>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
              padding: '10px 0 4px', fontFamily: MONO,
            }}>
              <span style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>
                {t('guard_tasca.compte_enrere')}
              </span>
              <span style={{ fontSize: '1.6rem', fontWeight: 500, color: 'var(--warn)',
                             fontVariantNumeric: 'tabular-nums' }}>
                {compteEnrere(instantVenciment - ara)}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <button onClick={pausaAra} style={{ ...selS, cursor: 'pointer' }}>
                {t('guard_tasca.pausar')}
              </button>
              <button onClick={confirma} style={{ ...primaryBtn, marginLeft: 0 }}>
                {t('guard_tasca.segueixo')}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
