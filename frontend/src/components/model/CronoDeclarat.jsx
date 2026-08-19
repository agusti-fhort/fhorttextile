import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { modelTasks } from '../../api/endpoints'
import { selS } from '../ui/buttons'
import { overlayBase } from '../ui/overlay'
import { MODE_DURADA, MODE_FRANJA, validaTempsDeclarat } from '../../utils/tempsDeclarat'
import { cronometre, segonsDeSessio } from '../../utils/sessioActiva'

/**
 * T3 · EL CRONO DE TEMPS DECLARAT (maqueta `maqueta_temps_declarat_i_modal_v1.html`, §1).
 *
 * «Iniciar» d'una tasca externa no navega enlloc: obre això. La feina es fa FORA de l'eina
 * —dibuixant a Polipattern, parlant amb disseny— i el temps és **declarat**, no mesurat.
 *
 * ⚠️ EL CRONO NO VIU AQUÍ. Viu al servidor: engegar obre un `TimerEntrada` real amb
 * `origen='declarat'` i aquest component només el PINTA. Per això sobreviu a un F5, a canviar de
 * pestanya i a tancar el navegador, i per això no hi ha ni un `localStorage` en tot el fitxer: el
 * segon que es guardés estat al navegador, la peça deixaria de complir el que promet.
 *
 * `engegar` és IDEMPOTENT al backend, i això és el que fa que obrir el crono i re-enganxar-s'hi
 * després d'un F5 siguin el mateix gest: si ja hi ha un tram viu, el retorna en comptes d'obrir-ne
 * un altre.
 *
 * Tres cares, les de la maqueta: CORRENT → ATURAT (confirma abans de desar) → CORREGIR A MÀ.
 */
const CARA_CORRENT = 'corrent'
const CARA_ATURAT = 'aturat'
const CARA_CORREGIR = 'corregir'
const CARA_DESCARTAR = 'descartar'

export default function CronoDeclarat({ modelId, code, nomTasca, subtitol, onTancat, onCancel }) {
  const { t } = useTranslation()
  const [cara, setCara] = useState(CARA_CORRENT)
  const [tram, setTram] = useState(null)          // {timer_id, inici, fi, minuts}
  const [ara, setAra] = useState(() => Date.now())
  const [error, setError] = useState(null)
  const [enviant, setEnviant] = useState(false)
  const viu = useRef(true)

  // Correcció a mà: la MATEIXA validació XOR que el formulari de F2.5 (`utils/tempsDeclarat`,
  // pura i amb 14 tests). Aquí canvia on es desa, no què és vàlid.
  const [mode, setMode] = useState(MODE_DURADA)
  const [minuts, setMinuts] = useState('')
  const [iniciCamp, setIniciCamp] = useState('')
  const [fiCamp, setFiCamp] = useState('')

  useEffect(() => () => { viu.current = false }, [])

  const crida = (cos) => modelTasks.crono(modelId, { code, ...cos })

  // Engegar en obrir. Idempotent: si el crono ja corria (F5, una altra pestanya), el recupera.
  useEffect(() => {
    crida({ accio: 'engegar' })
      .then(({ data }) => { if (viu.current) { setTram(data); setCara(data.fi ? CARA_ATURAT : CARA_CORRENT) } })
      .catch(e => { if (viu.current) setError(e?.response?.data?.error || t('crono.err_servidor')) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelId, code])

  // El rellotge de pantalla: només pinta el que el servidor ja sap. Si aquest interval mor, el
  // temps segueix corrent igualment — que és exactament la garantia que la peça ha de donar.
  useEffect(() => {
    if (cara !== CARA_CORRENT) return undefined
    const id = setInterval(() => setAra(Date.now()), 1000)
    return () => clearInterval(id)
  }, [cara])

  // Un tram tancat ja porta la seva durada; un de viu es compta contra ARA. Els segons els
  // calcula `segonsDeSessio`, que és el que ja fa servir l'indicador de sessió.
  const segons = tram?.fi
    ? segonsDeSessio({ inici: tram.inici }, new Date(tram.fi).getTime())
    : segonsDeSessio({ inici: tram?.inici }, ara)

  const fes = (cos, seguent) => {
    setEnviant(true); setError(null)
    crida(cos)
      .then(({ data }) => {
        if (!viu.current) return
        if (data.descartat) { onTancat?.(); onCancel?.(); return }
        setTram(data); setCara(seguent)
      })
      .catch(e => { if (viu.current) setError(e?.response?.data?.error || t('crono.err_servidor')) })
      .finally(() => { if (viu.current) setEnviant(false) })
  }

  const desaCorreccio = () => {
    const r = validaTempsDeclarat({ mode, minuts, inici: iniciCamp, fi: fiCamp })
    if (!r.ok) { setError(t(r.error)); return }
    fes({ accio: 'corregir', timer_id: tram.timer_id, ...r.cos }, CARA_ATURAT)
  }

  const camp = { ...selS, width: '100%', boxSizing: 'border-box', marginTop: 4 }
  const etiqueta = { display: 'block', fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 12 }
  const pestanya = (actiu) => ({
    ...selS, cursor: 'pointer', flex: 1,
    background: actiu ? 'var(--gold)' : 'var(--white)',
    color: actiu ? 'var(--text-main)' : 'var(--text-main)',
    fontWeight: actiu ? 600 : 400,
  })
  const primari = {
    fontFamily: 'inherit', fontSize: 'var(--fs-body)', fontWeight: 600, padding: '9px 14px',
    border: 'none', borderRadius: 6, background: 'var(--accio)', color: 'var(--white)',
    cursor: enviant ? 'not-allowed' : 'pointer', opacity: enviant ? 0.5 : 1,
  }
  const secundari = { ...selS, cursor: enviant ? 'not-allowed' : 'pointer' }

  return (
    <div onClick={onCancel} style={overlayBase({ alignItems: 'center' })}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--white)', borderRadius: 12, padding: 22, width: 440, maxWidth: '92vw',
        fontFamily: 'IBM Plex Mono, monospace',
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 10 }}>
          <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, margin: 0 }}>{nomTasca}</h2>
          <span style={{
            fontSize: 'var(--fs-label)', letterSpacing: '.06em', textTransform: 'uppercase',
            color: 'var(--text-muted)', border: '0.5px solid var(--border)', borderRadius: 4,
            padding: '2px 6px',
          }}>{t('crono.externa')}</span>
        </div>
        {subtitol && (
          <p style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', margin: '4px 0 0' }}>{subtitol}</p>
        )}

        {cara !== CARA_CORREGIR && (
          <div style={{
            fontSize: '2.2rem', fontWeight: 500, color: 'var(--text-main)',
            textAlign: 'center', margin: '18px 0 6px', letterSpacing: '.04em',
          }}>{cronometre(segons)}</div>
        )}

        {cara === CARA_CORRENT && (
          <>
            <p style={{ textAlign: 'center', fontSize: 'var(--fs-body)', color: 'var(--gold)', margin: 0 }}>
              {t('crono.corre')}
            </p>
            <div style={{ display: 'flex', gap: 8, marginTop: 18 }}>
              <button onClick={() => setCara(CARA_DESCARTAR)} disabled={enviant} style={{ ...secundari, flex: 1 }}>
                {t('crono.descartar')}
              </button>
              <button onClick={() => fes({ accio: 'aturar' }, CARA_ATURAT)} disabled={enviant}
                style={{ ...primari, flex: 1 }}>
                <i className="ti ti-player-stop" style={{ fontSize: 14, marginRight: 6 }} />
                {t('crono.aturar')}
              </button>
            </div>
            <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 12 }}>
              {t('crono.nota_servidor')}
            </p>
          </>
        )}

        {cara === CARA_ATURAT && (
          <>
            <p style={{ textAlign: 'center', fontSize: 'var(--fs-body)', color: 'var(--text-muted)', margin: 0 }}>
              {t('crono.confirma')}
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 18 }}>
              <button onClick={() => { onTancat?.(); onCancel?.() }} disabled={enviant} style={primari}>
                {t('crono.acceptar')}
              </button>
              <button onClick={() => setCara(CARA_CORREGIR)} disabled={enviant} style={secundari}>
                {t('crono.corregir')}
              </button>
              <button onClick={() => setCara(CARA_DESCARTAR)} disabled={enviant}
                style={{ ...secundari, border: 'none', background: 'transparent', color: 'var(--text-muted)' }}>
                {t('crono.descartar')}
              </button>
            </div>
            <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 12 }}>
              {t('crono.nota_no_tanca')}
            </p>
          </>
        )}

        {cara === CARA_CORREGIR && (
          <>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: '14px 0 10px' }}>
              {t('crono.corregir_titol')}
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => { setMode(MODE_DURADA); setError(null) }} style={pestanya(mode === MODE_DURADA)}>
                {t('temps_declarat.mode_durada')}
              </button>
              <button onClick={() => { setMode(MODE_FRANJA); setError(null) }} style={pestanya(mode === MODE_FRANJA)}>
                {t('temps_declarat.mode_franja')}
              </button>
            </div>
            {mode === MODE_DURADA ? (
              <label style={etiqueta}>
                {t('temps_declarat.minuts')}
                <input type="number" min="1" step="1" value={minuts} inputMode="numeric"
                  onChange={e => { setMinuts(e.target.value); setError(null) }} placeholder="90" style={camp} />
              </label>
            ) : (
              <>
                <label style={etiqueta}>
                  {t('temps_declarat.inici')}
                  <input type="datetime-local" value={iniciCamp}
                    onChange={e => { setIniciCamp(e.target.value); setError(null) }} style={camp} />
                </label>
                <label style={etiqueta}>
                  {t('temps_declarat.fi')}
                  <input type="datetime-local" value={fiCamp}
                    onChange={e => { setFiCamp(e.target.value); setError(null) }} style={camp} />
                </label>
              </>
            )}
            <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 12 }}>
              {t('temps_declarat.nota')}
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <button onClick={() => setCara(CARA_ATURAT)} disabled={enviant}
                style={{ ...secundari, border: 'none', background: 'transparent', color: 'var(--text-muted)' }}>
                {t('crono.enrere')}
              </button>
              <button onClick={desaCorreccio} disabled={enviant} style={primari}>
                {t('temps_declarat.desa')}
              </button>
            </div>
          </>
        )}

        {cara === CARA_DESCARTAR && (
          <>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', margin: '14px 0 6px' }}>
              {t('crono.descartar_titol')}
            </p>
            <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
              {t('crono.descartar_nota')}
            </p>
            <div style={{ display: 'flex', gap: 8, marginTop: 18 }}>
              <button onClick={() => setCara(tram?.fi ? CARA_ATURAT : CARA_CORRENT)} disabled={enviant}
                style={{ ...secundari, flex: 1 }}>
                {t('crono.descartar_no')}
              </button>
              <button
                onClick={() => {
                  // Descartar un crono EN MARXA és aturar-lo i esborrar-lo: el backend no
                  // esborra trams vius (seria una segona manera d'aturar-los).
                  const esborra = () => fes({ accio: 'descartar', timer_id: tram.timer_id })
                  if (tram?.fi) { esborra(); return }
                  setEnviant(true)
                  crida({ accio: 'aturar' })
                    .then(({ data }) => { setTram(data); esborra() })
                    .catch(e => setError(e?.response?.data?.error || t('crono.err_servidor')))
                    .finally(() => { if (viu.current) setEnviant(false) })
                }}
                disabled={enviant}
                style={{ ...primari, flex: 1, background: 'var(--err)' }}>
                {t('crono.descartar_si')}
              </button>
            </div>
          </>
        )}

        {error && (
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--err)', marginTop: 12 }}>{error}</p>
        )}
      </div>
    </div>
  )
}
