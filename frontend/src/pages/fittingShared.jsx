import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'

// Estil base de capçalera de taula (compartit entre la graella editable <MeasureTable>,
// la taula "Canvis" de la pantalla de revisió i els headers sticky).
export const thStyle = {
  padding: '0.5rem 0.8rem', fontSize: 'var(--fs-label)', letterSpacing: '0.08em',
  textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500,
  borderBottom: '0.5px solid var(--border)', whiteSpace: 'nowrap',
}

// Debounce genèric d'autosave (800ms). Cada instància té el seu propi timer.
export function useDebouncedSave(persist) {
  const [state, setState] = useState('idle') // idle | saving | saved | error
  const timerRef = useRef(null)
  const savedRef = useRef(null)
  useEffect(() => () => { clearTimeout(timerRef.current); clearTimeout(savedRef.current) }, [])
  const schedule = useCallback((value) => {
    setState('saving')
    clearTimeout(timerRef.current)
    clearTimeout(savedRef.current)
    timerRef.current = setTimeout(() => {
      persist(value)
        .then(() => { setState('saved'); savedRef.current = setTimeout(() => setState('idle'), 2000) })
        .catch(() => setState('error')) // NO toquem el valor local: es preserva
    }, 800)
  }, [persist])
  return [state, schedule]
}

export function SaveStatus({ state, inline, absolute }) {
  const { t } = useTranslation()
  if (state === 'idle') return null
  const map = {
    saving: { txt: t('fitting.grid.saving'), color: 'var(--text-muted)' },
    saved:  { txt: t('fitting.grid.saved'),  color: 'var(--ok)' },
    error:  { txt: t('fitting.grid.save_error'), color: 'var(--err)' },
  }
  const s = map[state]
  // absolute = no ocupa espai (no altera l'alçada de la fila de la graella).
  const pos = absolute
    ? { position: 'absolute', bottom: 1, left: 4, fontSize: 'var(--fs-caption)', pointerEvents: 'none' }
    : { display: inline ? 'inline-block' : 'block', marginLeft: inline ? 6 : 0, marginTop: inline ? 0 : 1, fontSize: 'var(--fs-caption)' }
  return <span style={{ color: s.color, ...pos }}>{s.txt}</span>
}
