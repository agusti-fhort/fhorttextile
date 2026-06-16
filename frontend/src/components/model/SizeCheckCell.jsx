import { useState, useRef, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
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
  if (valorReal === '' || valorReal == null) return false
  const vr = Number(valorReal)
  if (Number.isNaN(vr)) return false
  return vr < valorTeoric - tolMinus || vr > valorTeoric + tolPlus
}

// Cel·les editables d'una línia del size check. SC-3:
//  - "Real (proto)" parteix del valor TEÒRIC com a prefill, però amb flag `editat`: un
//    valor NO tocat NO compta com a mesura (valor_real es manté null al backend → semàfor
//    neutre, no es propaga). Vermell només si fora tolerància I editat.
//  - "Decisió" és un <select> i18n (Tolerància acceptada / Valor descartat).
//  - Nota: en 'valor_descartat' es preescriu un text editable; en acceptat és lliure.
export default function SizeCheckCell({ line, disabled, onLocalChange }) {
  const { t } = useTranslation()
  const NOTA_DESCARTAT = t('sizecheck.note_discarded_default', 'Cenyir-se a les mesures originals')

  // editat = ja hi ha una mesura real al backend (valor_real no null).
  const [editat, setEditat] = useState(line.valor_real != null)
  const [valor, setValor] = useState(line.valor_real ?? line.valor_teoric ?? '')   // prefill des del teòric
  const [decisio, setDecisio] = useState(line.decisio ?? '')
  const [nota, setNota] = useState(line.nota ?? '')

  const persistValor = useCallback(
    (raw) => sizeCheckLines.update(line.id, { valor_real: raw === '' ? null : Number(raw) }),
    [line.id])
  const persistNota = useCallback((raw) => sizeCheckLines.update(line.id, { nota: raw }), [line.id])

  const [valorState, saveValor] = useDebouncedSave(persistValor)
  const [notaState, saveNota] = useDebouncedSave(persistNota)

  // Vermell només si el valor és EDITAT i fora de tolerància (un prefill no tocat = neutre).
  const fora = editat && isFora(valor, line.valor_teoric, line.tol_minus, line.tol_plus)

  const onValorChange = (raw) => {
    setValor(raw)
    setEditat(raw !== '')          // editat només quan hi ha valor; buidar-lo = no mesura
    saveValor(raw)
    onLocalChange?.(line.id, { valor_real: raw, editat: raw !== '' })
  }

  const onDecisioChange = (v) => {
    const next = v || null
    setDecisio(v)
    sizeCheckLines.update(line.id, { decisio: next }).catch(() => setDecisio(decisio))
    // Descartat → preescriu la nota (editable) si encara és buida; no clobberem una nota escrita.
    if (next === 'valor_descartat' && !nota) {
      setNota(NOTA_DESCARTAT)
      saveNota(NOTA_DESCARTAT)
    }
    onLocalChange?.(line.id, { decisio: next })
  }

  return (
    <>
      <td style={{ ...td, textAlign: 'right', color: 'var(--text-muted)' }}>{line.valor_teoric ?? '—'}</td>
      <td style={{ ...td, textAlign: 'right', position: 'relative' }}>
        <input
          type="number" step="0.1" value={valor} disabled={disabled}
          onChange={e => onValorChange(e.target.value)}
          style={{
            font: 'inherit', fontFamily: MONO, width: 80, padding: '2px 4px', textAlign: 'right',
            border: '1px solid var(--border)', borderRadius: 4, background: disabled ? 'var(--gray-l)' : 'var(--white)',
            color: fora ? 'var(--err)' : (editat ? 'var(--text-main)' : 'var(--text-muted)'),
            fontWeight: fora ? 700 : 400,
            fontVariantNumeric: 'tabular-nums', boxSizing: 'border-box',
          }}
        />
        <SaveStatus state={valorState} />
      </td>
      <td style={{ ...td, textAlign: 'center' }}>
        <select
          value={decisio} disabled={disabled} onChange={e => onDecisioChange(e.target.value)}
          style={{
            font: 'inherit', fontFamily: MONO, fontSize: 11, padding: '2px 4px',
            border: '1px solid var(--border)', borderRadius: 4,
            background: disabled ? 'var(--gray-l)' : 'var(--white)', color: 'var(--text-main)',
          }}
        >
          <option value="">{t('sizecheck.decisio.none', '—')}</option>
          <option value="tolerancia_acceptada">{t('sizecheck.decisio.accepted', 'Tolerància acceptada')}</option>
          <option value="valor_descartat">{t('sizecheck.decisio.discarded', 'Valor descartat')}</option>
        </select>
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
