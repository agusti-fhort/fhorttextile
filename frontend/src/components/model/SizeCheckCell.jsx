import { useState, useRef, useEffect, useCallback } from 'react'
import { sizeCheckLines } from '../../api/endpoints'

const MONO = 'IBM Plex Mono, monospace'

// Debounce d'autosave (800ms), mateix patró que la graella de fitting.
function useDebouncedSave(persist) {
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
        .catch(() => setState('error'))   // NO toquem el valor local
    }, 800)
  }, [persist])
  return [state, schedule]
}

function SaveStatus({ state }) {
  if (state === 'idle') return null
  const map = {
    saving: { txt: '…', color: 'var(--text-muted)' },
    saved:  { txt: '✓', color: 'var(--ok)' },
    error:  { txt: '!', color: 'var(--err)' },
  }
  const s = map[state]
  return <span style={{ position: 'absolute', bottom: 1, right: 4, fontSize: 8, pointerEvents: 'none', color: s.color }}>{s.txt}</span>
}

const td = { padding: '5px 8px', borderBottom: '0.5px solid var(--border)', verticalAlign: 'middle', fontVariantNumeric: 'tabular-nums' }

// Recompute LOCAL del fora-tolerància mentre s'edita (font de veritat = backend, però
// volem feedback en viu): vermell quan el valor surt de [teòric-tol_minus, teòric+tol_plus].
function isFora(valorReal, valorTeoric, tolMinus, tolPlus) {
  if (valorReal === '' || valorReal == null) return false   // null → gris
  const vr = Number(valorReal)
  if (Number.isNaN(vr)) return false
  return vr < valorTeoric - tolMinus || vr > valorTeoric + tolPlus
}

// Cel·les editables d'una línia del size check: valor_real (vermell si fora_tol), acceptat, nota.
// Retorna un fragment de <td> perquè la <table> viu al SizeCheckTab.
export default function SizeCheckCell({ line, disabled, onLocalChange }) {
  const [valor, setValor] = useState(line.valor_real ?? '')
  const [acceptat, setAcceptat] = useState(!!line.acceptat)
  const [nota, setNota] = useState(line.nota ?? '')

  const persistValor = useCallback(
    (raw) => sizeCheckLines.update(line.id, { valor_real: raw === '' ? null : Number(raw) }),
    [line.id])
  const persistNota = useCallback((raw) => sizeCheckLines.update(line.id, { nota: raw }), [line.id])

  const [valorState, saveValor] = useDebouncedSave(persistValor)
  const [notaState, saveNota] = useDebouncedSave(persistNota)

  const fora = isFora(valor, line.valor_teoric, line.tol_minus, line.tol_plus)

  const toggleAcceptat = () => {
    const next = !acceptat
    setAcceptat(next)
    sizeCheckLines.update(line.id, { acceptat: next }).catch(() => setAcceptat(!next))
    onLocalChange?.(line.id, { acceptat: next })
  }

  return (
    <>
      <td style={{ ...td, textAlign: 'right', color: 'var(--text-muted)' }}>{line.valor_teoric ?? '—'}</td>
      <td style={{ ...td, textAlign: 'right', position: 'relative' }}>
        <input
          type="number" step="0.1" value={valor} disabled={disabled}
          onChange={e => { setValor(e.target.value); saveValor(e.target.value); onLocalChange?.(line.id, { valor_real: e.target.value }) }}
          style={{
            font: 'inherit', fontFamily: MONO, width: 80, padding: '2px 4px', textAlign: 'right',
            border: '1px solid var(--border)', borderRadius: 4, background: disabled ? 'var(--gray-l)' : 'var(--white)',
            color: fora ? 'var(--err)' : 'var(--text-main)', fontWeight: fora ? 700 : 400,
            fontVariantNumeric: 'tabular-nums', boxSizing: 'border-box',
          }}
        />
        <SaveStatus state={valorState} />
      </td>
      <td style={{ ...td, textAlign: 'center' }}>
        <input type="checkbox" checked={acceptat} disabled={disabled} onChange={toggleAcceptat} />
      </td>
      <td style={{ ...td, position: 'relative' }}>
        <input
          type="text" value={nota} disabled={disabled} placeholder="…"
          onChange={e => { setNota(e.target.value); saveNota(e.target.value) }}
          style={{
            font: 'inherit', fontFamily: MONO, fontSize: 11, width: '100%', padding: '2px 4px',
            border: '1px solid var(--border)', borderRadius: 4, background: disabled ? 'var(--gray-l)' : 'var(--white)',
            color: 'var(--text-main)', boxSizing: 'border-box',
          }}
        />
        <SaveStatus state={notaState} />
      </td>
    </>
  )
}
