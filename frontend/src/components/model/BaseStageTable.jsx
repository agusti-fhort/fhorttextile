import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { models, baseMeasurements, sizeChecks } from '../../api/endpoints'

const MONO = 'IBM Plex Mono, monospace'
const TEXT_2 = 'var(--text-muted)'
const BORDER = 'var(--border)'
const th = { padding: '6px 10px', borderBottom: `1px solid ${BORDER}`, fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, color: TEXT_2, textAlign: 'left', whiteSpace: 'nowrap' }
const td = { padding: '4px 10px', borderBottom: `0.5px solid ${BORDER}`, fontFamily: MONO, fontSize: 'var(--fs-body)', verticalAlign: 'middle' }
const inputBase = (disabled) => ({
  font: 'inherit', fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '2px 4px',
  border: `1px solid ${BORDER}`, borderRadius: 3,
  background: disabled ? 'var(--bg-muted)' : 'var(--white)', boxSizing: 'border-box',
})

const fmtTol = (m, p) => `-${m ?? '?'}/+${p ?? '?'}`
const fmtStageDate = (iso) => iso ? new Date(iso).toLocaleDateString('ca-ES', { day: '2-digit', month: '2-digit' }) : ''

// B1: accent de color per diferenciar estadis del llibre major. 'checked' (proto a taller) i
// 'fitting' (prova amb model) són processos DISTINTS: cada un té el seu punt de color (tokens
// existents; un punt no és icona → la regla outline-only no hi aplica).
const stageAccent = (ctx) => ctx === 'checked' ? 'var(--gold)' : ctx === 'fitting' ? 'var(--ok)' : null

// Debounce d'autosave (800ms), mateix patró que SizeCheckCell / la graella de fitting.
function useDebouncedSave(persist) {
  const [state, setState] = useState('idle')
  const timerRef = useRef(null)
  const savedRef = useRef(null)
  useEffect(() => () => { clearTimeout(timerRef.current); clearTimeout(savedRef.current) }, [])
  const schedule = useCallback((value) => {
    setState('saving')
    clearTimeout(timerRef.current); clearTimeout(savedRef.current)
    timerRef.current = setTimeout(() => {
      persist(value)
        .then(() => { setState('saved'); savedRef.current = setTimeout(() => setState('idle'), 1500) })
        .catch(() => setState('error'))
    }, 800)
  }, [persist])
  return [state, schedule]
}

function SaveDot({ state }) {
  if (state === 'idle' || state == null) return null
  const map = { saving: ['…', TEXT_2], saved: ['✓', 'var(--ok)'], error: ['!', 'var(--err)'] }
  const [txt, color] = map[state]
  return <span style={{ position: 'absolute', bottom: 1, right: 3, fontSize: 'var(--fs-caption)', pointerEvents: 'none', color }}>{txt}</span>
}

// Cel·la editable de nom_fitxa (per-POM, compartida per talles). Escriu NOMÉS BaseMeasurement.
// Nomenclatura (per-POM, compartida per talles). Si no hi ha nom_fitxa, el codi POM importat
// ÉS la nomenclatura (una sola columna). Edició LLIGADA A TASCA: editable només quan editable=true
// (vista de consulta = read-only); escriu NOMÉS BaseMeasurement.
function NomenclaturaCell({ baseMeasurementId, value, fallback, isKey, title, editable }) {
  const [val, setVal] = useState(value ?? '')
  useEffect(() => { setVal(value ?? '') }, [value])
  const persist = useCallback((raw) => baseMeasurements.update(baseMeasurementId, { nom_fitxa: raw }), [baseMeasurementId])
  const [state, save] = useDebouncedSave(persist)
  const star = isKey ? <span title="KEY" style={{ color: 'var(--gold)' }}> ★</span> : null
  if (!editable) {
    return (
      <td style={{ ...td, color: 'var(--gold)', fontWeight: 500, whiteSpace: 'nowrap' }} title={title}>
        {val || fallback || '—'}{star}
      </td>
    )
  }
  return (
    <td style={{ ...td, position: 'relative', whiteSpace: 'nowrap' }} title={title}>
      <input type="text" value={val} placeholder={fallback || '…'}
        onChange={e => { setVal(e.target.value); save(e.target.value) }}
        style={{ ...inputBase(false), width: 96, color: 'var(--gold)', fontWeight: 500 }} />
      {star}
      <SaveDot state={state} />
    </td>
  )
}

// Decisió + Nota de la columna d'estadi SELECCIONADA (consulta read-only; l'edició viu a la tasca).
// `line` = la SizeCheckLine de l'estadi seleccionat per a aquest POM (o null si l'estadi seleccionat
// no és un check amb dades carregades).
function DecisioNotaCells({ line }) {
  const { t } = useTranslation()
  if (!line) {
    return (<>
      <td style={{ ...td, textAlign: 'center', color: TEXT_2 }}>—</td>
      <td style={{ ...td, color: TEXT_2 }}>—</td>
    </>)
  }
  const dec = line.decisio === 'tolerancia_acceptada' ? t('sizecheck.decisio.accepted', 'Tolerància acceptada')
    : line.decisio === 'valor_descartat' ? t('sizecheck.decisio.discarded', 'Valor descartat')
      : '—'
  return (<>
    <td style={{ ...td, textAlign: 'center', color: 'var(--text-main)' }}>{dec}</td>
    <td style={{ ...td, color: TEXT_2, whiteSpace: 'normal' }}>{line.nota || '—'}</td>
  </>)
}

// PEÇA 3 — Taula base amb ESTADIS: el Size Check ampliat. Suma sobre la mateixa graella:
//  Tolerància (RO) · Teòric 1..N (creixen amb cada presa que escriu base, de l'històric) ·
//  Δ (vigent vs teòric anterior, acolorit contra tolerància) · nom_fitxa editable (per-POM) ·
//  Real · Decisió · Nota (estadi actiu = size check). Escriu NOMÉS BaseMeasurement.
//  La fitting session és un ESTADI més d'aquesta taula (futur), no una pantalla a part.
export default function BaseStageTable({ model, editable = false }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [lineByPom, setLineByPom] = useState({})
  const [checkEditable, setCheckEditable] = useState(false)
  const [loading, setLoading] = useState(true)
  // PEÇA C: estadi seleccionat per a Decisió/Nota (default: l'últim/vigent).
  const [selectedIdx, setSelectedIdx] = useState(null)

  const ctxLabel = (ctx) => t(`basestage.ctx.${ctx}`, ctx)

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([
      models.baseStages(model.id).then(r => r.data).catch(() => null),
      // Estadi actiu = el size check més recent (no en crea cap: només llegeix).
      sizeChecks.list({ model: model.id, ordering: '-created_at', page_size: 1 })
        .then(async r => {
          const rows = r.data?.results ?? r.data ?? []
          if (!rows.length) return null
          const full = await sizeChecks.get(rows[0].id)
          return full.data
        }).catch(() => null),
    ]).then(([stages, check]) => {
      setData(stages)
      const map = {}
      // El serializer (SizeCheckGridSerializer) emet `pom_id`, no `pom`: cal indexar per pom_id
      // perquè selLine(row.pom_id) lligui (abans sempre donava undefined → Decisió/Nota a '—').
      for (const l of (check?.lines || [])) map[l.pom_id] = l
      setLineByPom(map)
      // Principi rector: edició LLIGADA A TASCA. La pestanya és CONSULTA read-only; només
      // és editable quan s'arriba des d'una tasca (editable=true via ruta de treball).
      setCheckEditable(editable)
    }).finally(() => setLoading(false))
  }, [model.id, editable])

  useEffect(() => { load() }, [load])

  if (loading) return <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>{t('common.loading')}</div>
  if (!data || !data.rows?.length) {
    return <p style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>{t('basestage.empty')}</p>
  }

  const stages = data.stages || []
  const lastIdx = stages.length - 1
  // PEÇA C: columna d'estadi seleccionada (default = vigent). L'estadi de check amb dades
  // carregades (lineByPom = el check més recent) és l'últim estadi amb context 'checked'.
  const sel = selectedIdx == null ? lastIdx : selectedIdx
  const checkIdx = stages.reduce((acc, s, i) => (s.context === 'checked' ? i : acc), -1)
  const selLine = (pomId) => (sel === checkIdx ? lineByPom[pomId] : null)

  const deltaOf = (row) => {
    const seq = stages.map(s => (s.key in row.takes ? row.takes[s.key] : null))
    const vigent = row.base_value_cm
    const prev = seq.length >= 2 ? seq[seq.length - 2] : null
    if (vigent == null || prev == null) return { d: null, within: true }
    const d = Math.round((vigent - prev) * 100) / 100
    const within = d >= 0 ? d <= row.tol_plus : -d <= row.tol_minus
    return { d, within }
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 12 }}>
        <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, margin: 0, fontFamily: MONO }}>
          {t('basestage.title')} {data.base_size ? `· ${data.base_size}` : ''}
        </h2>
        <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: TEXT_2 }}>
          {checkEditable ? t('basestage.stage_live') : t('basestage.stage_readonly')}
        </span>
      </div>

      <div style={{ overflowX: 'auto', width: '100%' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ ...th, width: 26, padding: '6px 4px' }}>#</th>
              <th style={th}>{t('basestage.col_nomenclatura')}</th>
              <th style={{ ...th, textAlign: 'right', padding: '6px 6px' }}>{t('sizecheck.col_tolerance')}</th>
              {stages.map((s, i) => {
                const accent = stageAccent(s.context)
                return (
                <th key={s.key} onClick={() => setSelectedIdx(i)} title={t('basestage.select_stage')} style={{
                  ...th, textAlign: 'right', cursor: 'pointer',
                  background: i === sel ? '#f3e8d0' : (i === lastIdx ? '#fdf6ee' : undefined),
                  color: i === lastIdx ? '#7a4a10' : TEXT_2,
                  boxShadow: i === sel ? 'inset 0 -2px 0 var(--gold)' : undefined,
                }}>
                  {accent && <span aria-hidden="true" style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: accent, marginRight: 5, verticalAlign: 'middle' }} />}
                  {i === 0 ? t('basestage.stage_measure') : ctxLabel(s.context)}<br />
                  <span style={{ fontWeight: 400, fontSize: 'var(--fs-caption)' }}>
                    {[i === 0 ? null : `@${fmtStageDate(s.at)}`, i === lastIdx ? t('basestage.current') : null].filter(Boolean).join(' · ') || ' '}
                  </span>
                </th>
                )
              })}
              <th style={{ ...th, textAlign: 'right', padding: '6px 6px' }}>Δ</th>
              <th style={{ ...th, textAlign: 'center' }}>{t('sizecheck.col_decision')}</th>
              <th style={th}>{t('sizecheck.col_note')}</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, idx) => {
              const { d, within } = deltaOf(row)
              return (
                <tr key={row.pom_id}>
                  <td style={{ ...td, color: TEXT_2, width: 26, padding: '4px 4px' }}>{idx + 1}</td>
                  <NomenclaturaCell
                    baseMeasurementId={row.base_measurement_id}
                    value={row.nom_fitxa}
                    fallback={row.pom_code}
                    isKey={row.is_key}
                    title={row.nom_ca || row.nom_en}
                    editable={checkEditable} />
                  <td style={{ ...td, textAlign: 'right', color: TEXT_2, padding: '4px 6px' }}>{fmtTol(row.tol_minus, row.tol_plus)}</td>
                  {stages.map((s, i) => (
                    <td key={s.key} style={{
                      ...td, textAlign: 'right', fontVariantNumeric: 'tabular-nums',
                      background: i === sel ? '#f7eeda' : (i === lastIdx ? '#fefaf5' : undefined),
                      color: i === lastIdx ? 'var(--text-main)' : TEXT_2,
                    }}>
                      {s.key in row.takes ? row.takes[s.key] : '—'}
                    </td>
                  ))}
                  <td style={{
                    ...td, textAlign: 'right', fontVariantNumeric: 'tabular-nums',
                    color: d == null ? TEXT_2 : (within ? 'var(--ok)' : 'var(--err)'),
                    fontWeight: d != null && !within ? 700 : 400,
                  }}>
                    {d == null ? '—' : (d > 0 ? `+${d}` : `${d}`)}
                  </td>
                  <DecisioNotaCells line={selLine(row.pom_id)} />
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
