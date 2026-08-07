import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { modelTasks } from '../../api/endpoints'
import { selS } from '../ui/buttons'
import { overlayBase } from '../ui/overlay'
import { MODE_DURADA, MODE_FRANJA, validaTempsDeclarat } from '../../utils/tempsDeclarat'

/**
 * F2.5 · D-2 — DECLARAR TEMPS D'UNA TASCA EXTERNA.
 *
 * Una tasca `Externa-lliure` (patró a mà, revisió de disseny) es fa FORA de l'eina: no hi ha cap
 * escriptura que batre i el rellotge no hi arriba mai. Aquest formulari és l'únic camí pel qual
 * aquell temps entra al sistema — i és per això que existeix i que ha de ser fàcil de trobar.
 *
 * Les tasques INTERNES no el veuen mai: allà el temps es mesura sol i declarar-lo a mà seria
 * poder inventar hores facturables sobre feina observable. El guard dur és al backend
 * (`declara_temps`); aquí només s'amaga el que allà es rebutjaria.
 *
 * Dues modalitats EXCLOENTS, i el XOR es respecta fins al cos de la petició: o `{minuts}` o bé
 * `{inici, fi}`, mai els dos. La validació viu a `utils/tempsDeclarat` (pura, 14 tests).
 */
export default function TempsDeclaratForm({ tasca, onFet, onCancel }) {
  const { t } = useTranslation()
  const [mode, setMode] = useState(MODE_DURADA)
  const [minuts, setMinuts] = useState('')
  const [inici, setInici] = useState('')
  const [fi, setFi] = useState('')
  const [error, setError] = useState(null)
  const [enviant, setEnviant] = useState(false)

  const desa = () => {
    const r = validaTempsDeclarat({ mode, minuts, inici, fi })
    if (!r.ok) { setError(t(r.error)); return }
    setEnviant(true); setError(null)
    modelTasks.tempsDeclarat(tasca.id, r.cos)
      .then(({ data }) => onFet?.(data))
      .catch(e => setError(e?.response?.data?.error || t('temps_declarat.err_servidor')))
      .finally(() => setEnviant(false))
  }

  const camp = { ...selS, width: '100%', boxSizing: 'border-box', marginTop: 4 }
  const etiqueta = {
    display: 'block', fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 12,
  }
  const pestanya = (actiu) => ({
    ...selS, cursor: 'pointer', flex: 1,
    background: actiu ? 'var(--gold)' : 'var(--white)',
    color: actiu ? 'var(--text-main)' : 'var(--text-main)',
    fontWeight: actiu ? 600 : 400,
  })

  return (
    <div onClick={onCancel} style={overlayBase({ alignItems: 'center' })}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--white)', borderRadius: 12, padding: 22, width: 420, maxWidth: '92vw',
        fontFamily: 'IBM Plex Mono, monospace',
      }}>
        <h2 style={{
          fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 4,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <i className="ti ti-clock-plus" style={{ color: 'var(--gold)' }} />
          {t('temps_declarat.titol')}
        </h2>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 16 }}>
          {t('temps_declarat.subtitol', { tasca: tasca?.task_type_name || '' })}
        </p>

        {/* Les dues modalitats són EXCLOENTS: es trien, no es combinen. */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => { setMode(MODE_DURADA); setError(null) }}
                  style={pestanya(mode === MODE_DURADA)}>
            {t('temps_declarat.mode_durada')}
          </button>
          <button onClick={() => { setMode(MODE_FRANJA); setError(null) }}
                  style={pestanya(mode === MODE_FRANJA)}>
            {t('temps_declarat.mode_franja')}
          </button>
        </div>

        {mode === MODE_DURADA ? (
          <label style={etiqueta}>
            {t('temps_declarat.minuts')}
            <input type="number" min="1" step="1" value={minuts} inputMode="numeric"
                   onChange={e => { setMinuts(e.target.value); setError(null) }}
                   placeholder="90" style={camp} />
          </label>
        ) : (
          <>
            <label style={etiqueta}>
              {t('temps_declarat.inici')}
              <input type="datetime-local" value={inici}
                     onChange={e => { setInici(e.target.value); setError(null) }} style={camp} />
            </label>
            <label style={etiqueta}>
              {t('temps_declarat.fi')}
              <input type="datetime-local" value={fi}
                     onChange={e => { setFi(e.target.value); setError(null) }} style={camp} />
            </label>
          </>
        )}

        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 12 }}>
          {t('temps_declarat.nota')}
        </p>
        {error && (
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--err)', marginTop: 10 }}>{error}</p>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 18 }}>
          <button onClick={onCancel} disabled={enviant}
                  style={{ ...selS, border: 'none', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer' }}>
            {t('common.cancel')}
          </button>
          <button onClick={desa} disabled={enviant} style={{
            fontFamily: 'inherit', fontSize: 'var(--fs-body)', fontWeight: 600,
            padding: '7px 14px', border: 'none', borderRadius: 6,
            background: 'var(--gold)', color: 'var(--text-main)',
            cursor: enviant ? 'not-allowed' : 'pointer', opacity: enviant ? 0.5 : 1,
          }}>
            {t('temps_declarat.desa')}
          </button>
        </div>
      </div>
    </div>
  )
}
