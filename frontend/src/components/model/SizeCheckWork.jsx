import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { sizeChecks, sizeCheckLines } from '../../api/endpoints'
import BaseStageTable from './BaseStageTable'

// Superfície de treball del Size Check, integrada a Mesures (no és una segona pantalla).
// El check ES MESURA i ES RESOL aquí, amb el llibre major (BaseStageTable, read-only) davant.
// La presa del proto entra com a `valor_real` de SizeCheckLine; en acceptar, el motor la propaga
// a BaseMeasurement origen='CHECKED' → UNA sola columna 'checked' (no una 'manual' + una 'checked').
// El MOTOR (resolve_size_check) i els endpoints no es toquen.

const MONO = 'IBM Plex Mono, monospace'
const TEXT_2 = 'var(--text-muted)'
const BORDER = 'var(--border)'
const th = { padding: '6px 10px', borderBottom: `1px solid ${BORDER}`, fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, color: TEXT_2, textAlign: 'left', whiteSpace: 'nowrap' }
const tdRO = { padding: '4px 10px', borderBottom: `0.5px solid ${BORDER}`, fontFamily: MONO, fontSize: 'var(--fs-body)' }
const td = { padding: '4px 10px', verticalAlign: 'middle', fontSize: 'var(--fs-body)', borderBottom: `0.5px solid ${BORDER}` }
const inputBase = (disabled) => ({
  font: 'inherit', fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '2px 4px',
  border: `1px solid ${BORDER}`, borderRadius: 3,
  background: disabled ? 'var(--bg-muted)' : 'var(--white)', boxSizing: 'border-box',
})
const fmtTol = (m, p) => `-${m ?? '?'}/+${p ?? '?'}`

// Recompute LOCAL del fora-tolerància mentre s'edita.
function isFora(valorReal, valorTeoric, tolMinus, tolPlus) {
  if (valorReal === '' || valorReal == null) return false
  const vr = Number(valorReal)
  if (Number.isNaN(vr)) return false
  return vr < valorTeoric - tolMinus || vr > valorTeoric + tolPlus
}

// Debounce d'autosave (800ms), mateix patró que la resta de graelles.
function useDebouncedSave(persist) {
  const [state, setState] = useState('idle') // idle | saving | saved | error
  const timerRef = useRef(null)
  const savedRef = useRef(null)
  useEffect(() => () => { clearTimeout(timerRef.current); clearTimeout(savedRef.current) }, [])
  const schedule = useCallback((value) => {
    setState('saving')
    clearTimeout(timerRef.current); clearTimeout(savedRef.current)
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
  const map = { saving: ['…', TEXT_2], saved: ['✓', 'var(--ok)'], error: ['!', 'var(--err)'] }
  const [txt, color] = map[state]
  return <span style={{ position: 'absolute', bottom: 1, right: 4, fontSize: 'var(--fs-caption)', pointerEvents: 'none', color }}>{txt}</span>
}

// Cel·les editables d'una línia del check (port de SizeCheckCell). `valor_real` parteix del teòric
// com a prefill amb flag `editat`: null = no tocat → no propaga. Vermell només si fora tolerància
// I editat. Decisió: 'valor_descartat' preescriu NOTA_DESCARTAT (editable); 'tolerancia_acceptada'
// treu la nota preescrita. Autosave via sizeCheckLines.update.
function CheckCell({ line, disabled }) {
  const { t } = useTranslation()
  const NOTA_DESCARTAT = t('sizecheck.note_discarded_default', 'Cenyir-se a les mesures originals')

  const [editat, setEditat] = useState(line.valor_real != null)
  const [valor, setValor] = useState(line.valor_real ?? line.valor_teoric ?? '')
  const [decisio, setDecisio] = useState(line.decisio ?? '')
  const [nota, setNota] = useState(line.nota ?? '')

  const persistValor = useCallback(
    (raw) => sizeCheckLines.update(line.id, { valor_real: raw === '' ? null : Number(raw) }),
    [line.id])
  const persistNota = useCallback((raw) => sizeCheckLines.update(line.id, { nota: raw }), [line.id])
  const [valorState, saveValor] = useDebouncedSave(persistValor)
  const [notaState, saveNota] = useDebouncedSave(persistNota)

  const fora = editat && isFora(valor, line.valor_teoric, line.tol_minus, line.tol_plus)

  const onValorChange = (raw) => { setValor(raw); setEditat(raw !== ''); saveValor(raw) }
  const onDecisioChange = (v) => {
    const next = v || null
    setDecisio(v)
    sizeCheckLines.update(line.id, { decisio: next }).catch(() => setDecisio(decisio))
    if (next === 'valor_descartat') {
      if (!nota) { setNota(NOTA_DESCARTAT); saveNota(NOTA_DESCARTAT) }
    } else if (next === 'tolerancia_acceptada') {
      if (nota === NOTA_DESCARTAT) { setNota(''); saveNota('') }
    }
  }

  return (
    <>
      <td style={{ ...td, textAlign: 'right', color: TEXT_2 }}>{line.valor_teoric ?? '—'}</td>
      <td style={{ ...td, textAlign: 'right', color: TEXT_2, fontFamily: MONO }}>{fmtTol(line.tol_minus, line.tol_plus)}</td>
      <td style={{ ...td, textAlign: 'right', position: 'relative' }}>
        <input type="number" step="0.1" value={valor} disabled={disabled}
          onChange={e => onValorChange(e.target.value)}
          style={{ ...inputBase(disabled), width: 80, textAlign: 'right', fontVariantNumeric: 'tabular-nums',
            color: fora ? 'var(--err)' : (editat ? 'var(--text-main)' : TEXT_2), fontWeight: fora ? 700 : 400 }} />
        <SaveStatus state={valorState} />
      </td>
      <td style={{ ...td, textAlign: 'center' }}>
        <select value={decisio} disabled={disabled} onChange={e => onDecisioChange(e.target.value)}
          style={{ ...inputBase(disabled), color: 'var(--text-main)' }}>
          <option value="">{t('sizecheck.decisio.none', '—')}</option>
          <option value="tolerancia_acceptada">{t('sizecheck.decisio.accepted', 'Tolerància acceptada')}</option>
          <option value="valor_descartat">{t('sizecheck.decisio.discarded', 'Valor descartat')}</option>
        </select>
      </td>
      <td style={{ ...td, position: 'relative' }}>
        <input type="text" value={nota} disabled={disabled} placeholder="…"
          onChange={e => { setNota(e.target.value); saveNota(e.target.value) }}
          style={{ ...inputBase(disabled), width: '100%', color: 'var(--text-main)' }} />
        <SaveStatus state={notaState} />
      </td>
    </>
  )
}

const btn = (variant) => ({
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 14px', borderRadius: 4, cursor: 'pointer',
  border: '0.5px solid var(--gray-l)',
  background: variant === 'err' ? 'var(--err)' : variant === 'plain' ? 'var(--white)' : 'var(--gold)',
  color: variant === 'plain' ? 'var(--text-main)' : 'var(--white)', fontWeight: 500,
})
const overlay = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }
const modal = { background: 'var(--white)', borderRadius: 8, padding: 24, maxWidth: 460, fontFamily: MONO, boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }

export default function SizeCheckWork({ model, onFeedback, onResolved }) {
  const { t } = useTranslation()
  const [check, setCheck] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(null)        // modal propagació (Acceptat net amb deltes)
  const [reschedule, setReschedule] = useState(null)  // {estat, descartades} → modal reagendar
  const [reDate, setReDate] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    // Mode treball: garanteix un check viu (open idempotent: crea o reusa el Pendent).
    sizeChecks.open(model.id)
      .then(r => setCheck(r.data))
      .catch(() => { setCheck(null); onFeedback?.({ type: 'err', text: t('sizecheck.open_error') }) })
      .finally(() => setLoading(false))
  }, [model.id, onFeedback, t])

  useEffect(() => { load() }, [load])

  // Veredicte de MODEL derivat pel motor (no es col·lapsa al front): el control accept/descarta és
  // PER LÍNIA. Semàntica preservada de SizeCheckTab: amb descartades, Acceptar esdevé Rebutjat amb
  // reagenda obligatòria; Acceptat net amb deltes demana confirmar la propagació; Descartar reagenda.
  const hasDescartades = (check?.lines || []).some(l => l.decisio === 'valor_descartat')

  const onResolveClick = (estat) => {
    if (estat === 'Acceptat') {
      if (hasDescartades) { openReschedule('Acceptat', true); return }   // → Rebutjat
      if (check?.te_deltes) { setConfirm('Acceptat'); return }           // propagació
      doResolve('Acceptat'); return
    }
    openReschedule('Descartat', false)                                   // Descartar
  }

  const openReschedule = (estat, descartades) => {
    setReDate(check?.data_represa_default || '')
    setReschedule({ estat, descartades })
  }

  const doResolve = (estat, opts = {}) => {
    if (!check) return
    setConfirm(null); setReschedule(null); setBusy(true)
    sizeChecks.resolve(check.id, estat, opts)
      .then(r => {
        const d = r.data || {}
        const dr = d.data_represa
        let text
        if (d.estat === 'Acceptat') {
          const extra = d.regradat ? t('sizecheck.fb_regraded', { v: d.nova_version }) : ''
          text = t('sizecheck.fb_saved', { n: d.written || 0 }) + extra
        } else if (d.estat === 'Rebutjat') {
          text = t('sizecheck.fb_rejected', { d: dr || '—' })
        } else {
          text = t('sizecheck.fb_discarded', { d: dr || '—' })
        }
        onFeedback?.({ type: 'ok', text })
        onResolved?.()   // feina acabada: el pare decideix (navega a Kanban) o recarrega
      })
      .catch(e => onFeedback?.({ type: 'err', text: e.response?.data?.error || t('sizecheck.resolve_error') }))
      .finally(() => setBusy(false))
  }

  if (loading) return <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>{t('common.loading')}</div>

  return (
    <div>
      {/* Llibre major: historial d'estadis read-only davant (decisió de disseny G1). */}
      <BaseStageTable model={model} editable={false} />

      {/* Graella editable del check viu: mesura del proto + decisió/nota per línia. */}
      {check && (
        <div style={{ marginTop: 24 }}>
          <h3 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, fontFamily: MONO, margin: '0 0 10px' }}>
            {t('sizecheck.work_title')}
          </h3>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                <th style={th}>POM</th>
                <th style={th}>{t('sizecheck.col_measure')}</th>
                <th style={{ ...th, textAlign: 'right' }}>{t('sizecheck.col_theoretical')}</th>
                <th style={{ ...th, textAlign: 'right' }}>{t('sizecheck.col_tolerance')}</th>
                <th style={{ ...th, textAlign: 'right' }}>{t('sizecheck.col_real')}</th>
                <th style={{ ...th, textAlign: 'center' }}>{t('sizecheck.col_decision')}</th>
                <th style={th}>{t('sizecheck.col_note')}</th>
              </tr>
            </thead>
            <tbody>
              {(check.lines || []).map(line => (
                <tr key={line.id}>
                  <td style={{ ...tdRO, color: 'var(--gold)', fontWeight: line.is_key ? 700 : 400 }}>{line.codi_fitxa || line.codi}</td>
                  <td style={{ ...tdRO, color: TEXT_2 }}>{line.nom}</td>
                  <CheckCell line={line} disabled={false} />
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button style={btn('gold')} disabled={busy} onClick={() => onResolveClick('Acceptat')}>{t('sizecheck.save')}</button>
            <button style={btn('err')} disabled={busy} onClick={() => onResolveClick('Descartat')}>{t('sizecheck.discard')}</button>
          </div>
        </div>
      )}

      {/* Modal propagació (Acceptat net amb deltes). */}
      {confirm && (
        <div style={overlay} onClick={() => setConfirm(null)}>
          <div onClick={e => e.stopPropagation()} style={modal}>
            <h3 style={{ margin: '0 0 12px', fontSize: 'var(--fs-h3)', fontWeight: 600 }}>{t('sizecheck.propagate_title')}</h3>
            <p style={{ margin: '0 0 18px', fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--text-main)' }}>
              {t('sizecheck.propagate_warning')}
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button style={btn('plain')} disabled={busy} onClick={() => setConfirm(null)}>{t('common.cancel')}</button>
              <button style={btn('gold')} disabled={busy} onClick={() => doResolve('Acceptat')}>{t('sizecheck.confirm_propagate')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal reagendar (Acceptat-amb-descartades=Rebutjat o Descartar): data OBLIGATÒRIA de represa. */}
      {reschedule && (
        <div style={overlay} onClick={() => setReschedule(null)}>
          <div onClick={e => e.stopPropagation()} style={modal}>
            <h3 style={{ margin: '0 0 12px', fontSize: 'var(--fs-h3)', fontWeight: 600 }}>{t('sizecheck.reschedule_title')}</h3>
            {reschedule.descartades && (
              <p style={{ margin: '0 0 12px', fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--err)' }}>
                {t('sizecheck.reschedule_rejected')}
              </p>
            )}
            <p style={{ margin: '0 0 8px', fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--text-main)' }}>
              {t('sizecheck.reschedule_help')}
            </p>
            <input type="date" value={reDate} onChange={e => setReDate(e.target.value)}
                   style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 8px', borderRadius: 4, border: `1px solid ${BORDER}`, marginBottom: 18, width: '100%', boxSizing: 'border-box' }} />
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button style={btn('plain')} disabled={busy} onClick={() => setReschedule(null)}>{t('common.cancel')}</button>
              <button style={btn(reschedule.estat === 'Descartat' ? 'err' : 'gold')} disabled={busy || !reDate}
                      onClick={() => doResolve(reschedule.estat, { data_represa: reDate })}>
                {t('sizecheck.reschedule_confirm')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
