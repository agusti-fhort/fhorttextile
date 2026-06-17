import { useState, useRef, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { sizeCheckLines } from '../../api/endpoints'

const MONO = 'IBM Plex Mono, monospace'
const TEXT_2 = 'var(--text-muted)'
const BORDER = 'var(--border)'

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
    saving: { txt: '…', color: TEXT_2 },
    saved:  { txt: '✓', color: 'var(--ok)' },
    error:  { txt: '!', color: 'var(--err)' },
  }
  const s = map[state]
  return <span style={{ position: 'absolute', bottom: 1, right: 4, fontSize: 8, pointerEvents: 'none', color: s.color }}>{s.txt}</span>
}

// Tokens idèntics a la taula Mesures (EditableTable): td 4px 10px / fontSize 12, inputs fontSize 12.
const td = { padding: '4px 10px', verticalAlign: 'middle', fontSize: 12, borderBottom: `0.5px solid ${BORDER}` }
const inputBase = (disabled) => ({
  font: 'inherit', fontFamily: MONO, fontSize: 12, padding: '2px 4px',
  border: `1px solid ${BORDER}`, borderRadius: 3,
  background: disabled ? 'var(--bg-muted)' : 'var(--white)',
  boxSizing: 'border-box',
})

// Recompute LOCAL del fora-tolerància mentre s'edita: vermell quan surt de [teòric-minus, teòric+plus].
function isFora(valorReal, valorTeoric, tolMinus, tolPlus) {
  if (valorReal === '' || valorReal == null) return false
  const vr = Number(valorReal)
  if (Number.isNaN(vr)) return false
  return vr < valorTeoric - tolMinus || vr > valorTeoric + tolPlus
}

const fmtTol = (m, p) => `-${m ?? '?'}/+${p ?? '?'}`

// Cel·les editables d'una línia del size check. SC-3/SC-4:
//  - "Real (proto)" parteix del valor TEÒRIC com a prefill amb flag `editat`: un valor NO
//    tocat NO compta com a mesura (valor_real null al backend → neutre, no es propaga).
//    Vermell només si fora tolerància I editat.
//  - "Tolerància" informativa (read-only): -minus/+plus del BaseMeasurement.
//  - "Decisió" <select> i18n. Nota: només 'valor_descartat' preescriu text (editable);
//    'tolerancia_acceptada' → nota lliure (i treu el text preescrit si hi era).
export default function SizeCheckCell({ line, disabled }) {
  const { t } = useTranslation()
  const NOTA_DESCARTAT = t('sizecheck.note_discarded_default', 'Cenyir-se a les mesures originals')

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

  const fora = editat && isFora(valor, line.valor_teoric, line.tol_minus, line.tol_plus)

  const onValorChange = (raw) => {
    setValor(raw)
    setEditat(raw !== '')
    saveValor(raw)
  }

  const onDecisioChange = (v) => {
    const next = v || null
    setDecisio(v)
    sizeCheckLines.update(line.id, { decisio: next }).catch(() => setDecisio(decisio))
    if (next === 'valor_descartat') {
      if (!nota) { setNota(NOTA_DESCARTAT); saveNota(NOTA_DESCARTAT) }   // preescriu (editable)
    } else if (next === 'tolerancia_acceptada') {
      if (nota === NOTA_DESCARTAT) { setNota(''); saveNota('') }         // acceptada → SENSE missatge preescrit
    }
  }

  return (
    <>
      <td style={{ ...td, textAlign: 'right', color: TEXT_2 }}>{line.valor_teoric ?? '—'}</td>
      <td style={{ ...td, textAlign: 'right', color: TEXT_2, fontFamily: MONO }}>{fmtTol(line.tol_minus, line.tol_plus)}</td>
      <td style={{ ...td, textAlign: 'right', position: 'relative' }}>
        <input
          type="number" step="0.1" value={valor} disabled={disabled}
          onChange={e => onValorChange(e.target.value)}
          style={{
            ...inputBase(disabled), width: 80, textAlign: 'right', fontVariantNumeric: 'tabular-nums',
            color: fora ? 'var(--err)' : (editat ? 'var(--text-main)' : TEXT_2),
            fontWeight: fora ? 700 : 400,
          }}
        />
        <SaveStatus state={valorState} />
      </td>
      <td style={{ ...td, textAlign: 'center' }}>
        <select
          value={decisio} disabled={disabled} onChange={e => onDecisioChange(e.target.value)}
          style={{ ...inputBase(disabled), color: 'var(--text-main)' }}
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
          style={{ ...inputBase(disabled), width: '100%', color: 'var(--text-main)' }}
        />
        <SaveStatus state={notaState} />
      </td>
    </>
  )
}
