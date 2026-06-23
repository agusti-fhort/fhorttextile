import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { models, sizeChecks, sizeCheckLines, baseMeasurements } from '../../api/endpoints'
import MeasureGrid from './MeasureGrid'
import EditorHeader from './EditorHeader'
import DependencyPanel from './DependencyPanel'
import WatchpointsPanel from './WatchpointsPanel'

// CHECK sobre l'editor únic MeasureGrid (substitueix SizeCheckWork): UNA graella amb l'historial
// d'estadis (base-stages, read-only) com a columnes + la columna activa 'Real' (valor_real) + el
// slot Decisió/Nota per línia. La presa entra com valor_real → en resoldre, el motor la propaga a
// BaseMeasurement origen='CHECKED' (una sola columna 'checked'). MOTOR (resolve_size_check) INTACTE.

const MONO = 'IBM Plex Mono, monospace'
const TEXT_2 = 'var(--text-muted)'
const BORDER = 'var(--border)'

// P9 — presa TIPADA per origen: cada estadi de l'historial mostra de quina presa ve, amb un punt de
// color per família d'origen (origen ja viu a MeasurementChangeLog.context). Verd = sessió de fitting;
// daurat = presa humana de taller/proto (size check / manual); gris = derivada/importada/sembra.
// L'etiqueta de text (basestage.ctx.*) ja nomena l'origen; el punt el TIPA visualment a la columna.
const stageAccent = (ctx) => ({
  fitting: 'var(--ok)',
  checked: 'var(--gold)',
  manual: 'var(--gold-l)',
  import: 'var(--gray)',
  calculated: 'var(--gray)',
  standard: 'var(--gray)',
}[ctx] || null)
const fmtStageDate = (iso) => iso ? new Date(iso).toLocaleDateString('ca-ES', { day: '2-digit', month: '2-digit' }) : ''

function StageLabel({ ctx, at, first }) {
  const { t } = useTranslation()
  const accent = stageAccent(ctx)
  return (
    <span>
      {accent && <span aria-hidden="true" style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: accent, marginRight: 4, verticalAlign: 'middle' }} />}
      {first ? t('basestage.stage_measure') : t(`basestage.ctx.${ctx}`, ctx)}
      {at && <span style={{ display: 'block', fontWeight: 400, fontSize: 'var(--fs-caption)' }}>@{fmtStageDate(at)}</span>}
    </span>
  )
}

// Slot Decisió·Nota (trail) per línia del check — port de SizeCheckCell: select de decisió +
// preescriptura/neteja de NOTA_DESCARTAT + nota; autosave via sizeCheckLines.update.
const inputBase = { font: 'inherit', fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '2px 4px', border: `1px solid ${BORDER}`, borderRadius: 3, background: 'var(--white)', boxSizing: 'border-box' }
function DecisioNotaCell({ line }) {
  const { t } = useTranslation()
  const NOTA_DESCARTAT = t('sizecheck.note_discarded_default', 'Cenyir-se a les mesures originals')
  const [decisio, setDecisio] = useState(line.decisio ?? '')
  const [nota, setNota] = useState(line.nota ?? '')
  const saveNota = useRef(null)

  const onDecisioChange = (v) => {
    const next = v || null
    setDecisio(v)
    sizeCheckLines.update(line.id, { decisio: next }).catch(() => setDecisio(line.decisio ?? ''))
    if (next === 'valor_descartat') {
      if (!nota) { setNota(NOTA_DESCARTAT); sizeCheckLines.update(line.id, { nota: NOTA_DESCARTAT }).catch(() => {}) }
    } else if (next === 'tolerancia_acceptada') {
      if (nota === NOTA_DESCARTAT) { setNota(''); sizeCheckLines.update(line.id, { nota: '' }).catch(() => {}) }
    }
  }
  const onNotaChange = (v) => {
    setNota(v)
    clearTimeout(saveNota.current)
    saveNota.current = setTimeout(() => sizeCheckLines.update(line.id, { nota: v }).catch(() => {}), 800)
  }
  useEffect(() => () => clearTimeout(saveNota.current), [])

  return (
    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      <select value={decisio} onChange={e => onDecisioChange(e.target.value)} style={{ ...inputBase, color: 'var(--text-main)' }}>
        <option value="">{t('sizecheck.decisio.none', '—')}</option>
        <option value="tolerancia_acceptada">{t('sizecheck.decisio.accepted', 'Tolerància acceptada')}</option>
        <option value="valor_descartat">{t('sizecheck.decisio.discarded', 'Valor descartat')}</option>
      </select>
      <input type="text" value={nota} placeholder="…" onChange={e => onNotaChange(e.target.value)}
        style={{ ...inputBase, minWidth: 140, color: 'var(--text-main)' }} />
    </div>
  )
}

// Slot Decisió·Nota en mode CONSULTA (read-only): text pla, mateixes etiquetes i18n.
function ReadOnlyDecisioNota({ line }) {
  const { t } = useTranslation()
  const dec = line.decisio === 'tolerancia_acceptada' ? t('sizecheck.decisio.accepted', 'Tolerància acceptada')
    : line.decisio === 'valor_descartat' ? t('sizecheck.decisio.discarded', 'Valor descartat') : '—'
  return (
    <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
      <span style={{ color: 'var(--text-main)' }}>{dec}</span>
      {line.nota && <span style={{ color: TEXT_2 }}> · {line.nota}</span>}
    </span>
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

// Etiqueta compacta de regla (delta · trencament), com el fitting (MeasureTable.regleLabel).
function regleLabel(row, t) {
  if (row.logica == null) return ''
  if (row.logica === 'STEP') return t('fitting.grid.rule_free')
  if (row.increment_base == null) return ''
  if (row.increment_break != null && row.talla_break_label)
    return `+${row.increment_base} · ${t('fitting.grid.break')} ${row.talla_break_label} +${row.increment_break}`
  return `+${row.increment_base}`
}

export default function CheckMeasureEditor({ model, onFeedback, onResolved, onBack = null, readOnly = false, taskId = null }) {
  const { t } = useTranslation()
  const [baseData, setBaseData] = useState(null)
  const [check, setCheck] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(null)
  const [reschedule, setReschedule] = useState(null)
  const [reDate, setReDate] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    // CONSULTA: NO obre cap check (només llegeix el més recent). TREBALL: open idempotent.
    const checkP = readOnly
      ? sizeChecks.list({ model: model.id, ordering: '-created_at', page_size: 1 })
          .then(r => { const rows = r.data?.results ?? r.data ?? []; return rows.length ? sizeChecks.get(rows[0].id).then(x => x.data) : null })
          .catch(() => null)
      : sizeChecks.open(model.id).then(r => r.data).catch(() => null)
    Promise.all([models.baseStages(model.id).then(r => r.data).catch(() => null), checkP])
      .then(([stages, chk]) => {
        setBaseData(stages); setCheck(chk)
        if (!chk && !readOnly) onFeedback?.({ type: 'err', text: t('sizecheck.open_error') })
      }).finally(() => setLoading(false))
  }, [model.id, readOnly, onFeedback, t])

  useEffect(() => { load() }, [load])

  const hasDescartades = (check?.lines || []).some(l => l.decisio === 'valor_descartat')
  const onResolveClick = (estat) => {
    if (estat === 'Acceptat') {
      if (hasDescartades) { openReschedule('Acceptat', true); return }
      if (check?.te_deltes) { setConfirm('Acceptat'); return }
      doResolve('Acceptat'); return
    }
    openReschedule('Descartat', false)
  }
  const openReschedule = (estat, descartades) => { setReDate(check?.data_represa_default || ''); setReschedule({ estat, descartades }) }
  const doResolve = (estat, opts = {}) => {
    if (!check) return
    setConfirm(null); setReschedule(null); setBusy(true)
    sizeChecks.resolve(check.id, estat, opts)
      .then(r => {
        const d = r.data || {}
        const dr = d.data_represa
        let text
        if (d.estat === 'Acceptat') text = t('sizecheck.fb_saved', { n: d.written || 0 }) + (d.regradat ? t('sizecheck.fb_regraded', { v: d.nova_version }) : '')
        else if (d.estat === 'Rebutjat') text = t('sizecheck.fb_rejected', { d: dr || '—' })
        else text = t('sizecheck.fb_discarded', { d: dr || '—' })
        onFeedback?.({ type: 'ok', text })
        onResolved?.()
      })
      .catch(e => onFeedback?.({ type: 'err', text: e.response?.data?.error || t('sizecheck.resolve_error') }))
      .finally(() => setBusy(false))
  }

  const onSave = useCallback((lineId, value) => sizeCheckLines.update(lineId, { valor_real: value }), [])
  // P4 — autoria del nom a nivell MODEL: desa nom_fitxa de la BaseMeasurement (NO el POM tenant).
  const onNomSave = useCallback((bmId, value) =>
    baseMeasurements.update(bmId, { nom_fitxa: value || null })
      .catch(() => onFeedback?.({ type: 'err', text: t('measuregrid.nom_save_err') })), [onFeedback, t])

  if (loading) return <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>{t('common.loading')}</div>

  const stages = baseData?.stages || []
  const lineByPom = {}
  for (const l of (check?.lines || [])) lineByPom[l.pom_id] = l
  const groups = [{
    key: 'base',
    label: baseData?.base_size || t('basestage.stage_measure'),
    accent: true,
    historyCols: stages.map((s, i) => ({ key: s.key, label: <StageLabel ctx={s.context} at={i === 0 ? null : s.at} first={i === 0} /> })),
    activeLabel: t('sizecheck.col_real'),
    trailCols: [{ key: 'dn', label: `${t('sizecheck.col_decision')} · ${t('sizecheck.col_note')}` }],
  }]
  const rows = (baseData?.rows || []).map(r => {
    const line = lineByPom[r.pom_id]
    return {
      pom_id: r.pom_id,
      codi: r.nom_fitxa || r.pom_code,
      nom_en: r.nom_en, nom_local: r.nom_ca,
      nom_fitxa: r.nom_fitxa, bm_id: r.base_measurement_id,
      is_key: r.is_key,
      logica: line?.logica, increment_base: line?.increment_base,
      increment_break: line?.increment_break, talla_break_label: line?.talla_break_label,
      tol_minus: line?.tol_minus, tol_plus: line?.tol_plus,
      cells: { base: {
        history: Object.fromEntries(stages.map(s => [s.key, (s.key in r.takes) ? r.takes[s.key] : null])),
        // SEMBRA: la columna Real parteix amb l'última mesura vàlida (valor_teoric vigent) com a
        // prefill VISUAL; com que MeasureGrid només persisteix a onChange, una columna sembrada-i-no-
        // tocada deixa valor_real=null i el motor (resolve_size_check) NO escriu base.
        active: line ? { lineId: line.id, value: line.valor_real ?? line.valor_teoric, baseValue: line.valor_teoric, tol: { minus: line.tol_minus, plus: line.tol_plus } } : null,
        trail: { dn: line ? (readOnly ? <ReadOnlyDecisioNota line={line} /> : <DecisioNotaCell line={line} />) : null },
      } },
    }
  })

  // Columna Règim (lectura): logica + etiqueta de regla a 2 línies, estil fitting. El check no
  // edita el règim (és context de grading); el fitting sí (al seu editor). MeasureGrid ja té leadCols.
  const leadCols = [{
    key: 'regim', label: t('fitting.grid.regime'), width: 118,
    render: (row) => (
      <div>
        <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-main)' }}>{row.logica ?? '—'}</div>
        {regleLabel(row, t) && (
          <div style={{ fontSize: 'var(--fs-caption)', color: TEXT_2, whiteSpace: 'nowrap', marginTop: 1 }}>{regleLabel(row, t)}</div>
        )}
      </div>
    ),
  }, {
    // Tolerància (lectura): es mostra tal com ve (-minus/+plus); NO es col·lapsa a ±únic (deute sprint POMs).
    key: 'tol', label: t('sizecheck.col_tolerance'), width: 72,
    render: (row) => (
      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>
        {row.tol_minus != null ? `-${row.tol_minus}/+${row.tol_plus}` : '—'}
      </span>
    ),
  }]

  return (
    <div>
      <EditorHeader model={model} onBack={onBack} />
      <DependencyPanel model={model} />
      <MeasureGrid rows={rows} groups={groups} leadCols={leadCols} editable={!readOnly}
        onSave={readOnly ? undefined : onSave} onNomSave={readOnly ? undefined : onNomSave}
        empty={<p style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>{t('basestage.empty')}</p>} />

      {!readOnly && check && rows.length > 0 && (
        <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
          <button style={btn('gold')} disabled={busy} onClick={() => onResolveClick('Acceptat')}>{t('sizecheck.save')}</button>
          <button style={btn('err')} disabled={busy} onClick={() => onResolveClick('Descartat')}>{t('sizecheck.discard')}</button>
        </div>
      )}

      {/* D-12 — Watchpoints del model (crear en treball, veure sempre). Origen = la tasca actual. */}
      {model?.id && <WatchpointsPanel modelId={model.id} taskId={taskId} editable={!readOnly} />}

      {confirm && (
        <div style={overlay} onClick={() => setConfirm(null)}>
          <div onClick={e => e.stopPropagation()} style={modal}>
            <h3 style={{ margin: '0 0 12px', fontSize: 'var(--fs-h3)', fontWeight: 600 }}>{t('sizecheck.propagate_title')}</h3>
            <p style={{ margin: '0 0 18px', fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--text-main)' }}>{t('sizecheck.propagate_warning')}</p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button style={btn('plain')} disabled={busy} onClick={() => setConfirm(null)}>{t('common.cancel')}</button>
              <button style={btn('gold')} disabled={busy} onClick={() => doResolve('Acceptat')}>{t('sizecheck.confirm_propagate')}</button>
            </div>
          </div>
        </div>
      )}
      {reschedule && (
        <div style={overlay} onClick={() => setReschedule(null)}>
          <div onClick={e => e.stopPropagation()} style={modal}>
            <h3 style={{ margin: '0 0 12px', fontSize: 'var(--fs-h3)', fontWeight: 600 }}>{t('sizecheck.reschedule_title')}</h3>
            {reschedule.descartades && (
              <p style={{ margin: '0 0 12px', fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--err)' }}>{t('sizecheck.reschedule_rejected')}</p>
            )}
            <p style={{ margin: '0 0 8px', fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--text-main)' }}>{t('sizecheck.reschedule_help')}</p>
            <input type="date" value={reDate} onChange={e => setReDate(e.target.value)}
              style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 8px', borderRadius: 4, border: `1px solid ${BORDER}`, marginBottom: 18, width: '100%', boxSizing: 'border-box' }} />
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button style={btn('plain')} disabled={busy} onClick={() => setReschedule(null)}>{t('common.cancel')}</button>
              <button style={btn(reschedule.estat === 'Descartat' ? 'err' : 'gold')} disabled={busy || !reDate}
                onClick={() => doResolve(reschedule.estat, { data_represa: reDate })}>{t('sizecheck.reschedule_confirm')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
