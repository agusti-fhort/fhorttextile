import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { models, sizeChecks, sizeCheckLines, baseMeasurements } from '../../api/endpoints'
import { effectiveRegime } from '../../utils/gradingRegime'
import MeasureGrid from './MeasureGrid'
import EditorHeader from './EditorHeader'
import DependencyPanel from './DependencyPanel'
import WatchpointsPanel from './WatchpointsPanel'
import SessionPanel from './SessionPanel'
import SessionActions from './SessionActions'
import PromoteToItemButton from './PromoteToItemButton'

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
  // LINEAR+0 sense break = FIXED: no té delta a ensenyar (§LLEI a utils/gradingRegime).
  if (effectiveRegime(row) === 'FIXED') return ''
  if (row.increment_base == null) return ''
  if (row.increment_break != null && row.talla_break_label)
    return `+${row.increment_base} · ${t('fitting.grid.break')} ${row.talla_break_label} +${row.increment_break}`
  return `+${row.increment_base}`
}

// P3 — editor de la REGLA VIVA del model (delta + break) a la talla base. La regla és patrimoni del
// MODEL: s'escriu a ModelGradingRule (origen='MANUAL') via models.setPomRule i el motor la llegeix
// tal qual (NO es toca el càlcul). Sense break → delta uniforme (talla_break_label null = LINEAR pur).
// Amb break (talla + valor) → LINEAR amb trencament. STEP (irregular) no s'edita aquí; es mostra inert.
const regleInput = {
  font: 'inherit', fontFamily: MONO, fontSize: 'var(--fs-caption)', width: 46, padding: '1px 3px',
  textAlign: 'right', border: `1px solid ${BORDER}`, borderRadius: 3, background: 'var(--white)',
  color: 'var(--text-main)', boxSizing: 'border-box',
}
function RegleEditCell({ modelId, row, sizeRun, onFeedback }) {
  const { t } = useTranslation()
  const [delta, setDelta] = useState(row.increment_base ?? '')
  const [brk, setBrk] = useState(row.increment_break ?? '')
  const [brkSize, setBrkSize] = useState(row.talla_break_label ?? '')
  useEffect(() => {
    setDelta(row.increment_base ?? ''); setBrk(row.increment_break ?? '')
    setBrkSize(row.talla_break_label ?? '')
  }, [row.pom_id, row.increment_base, row.increment_break, row.talla_break_label])

  const save = (d, b, bs) => {
    models.setPomRule(modelId, row.pom_id, {
      logica: 'LINEAR',
      increment_base: d === '' ? null : d,
      talla_break_label: bs || null,
      increment_break: bs ? (b === '' ? null : b) : null,
    }).catch(() => onFeedback?.({ type: 'err', text: t('measuregrid.regle_save_err') }))
  }
  if (row.logica === 'STEP') {
    // Règim irregular (STEP): no es desglossa a delta+break; es mostra inert (s'edita al fitting).
    return <div style={{ fontSize: 'var(--fs-caption)', color: TEXT_2 }}>{t('fitting.grid.rule_free')}</div>
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--fs-caption)', color: TEXT_2 }}>
        <span style={{ width: 30 }}>{t('measuregrid.regle_delta')}</span>
        <input type="text" inputMode="decimal" value={delta} aria-label={t('measuregrid.regle_delta')}
          onChange={e => setDelta(e.target.value)} onBlur={() => save(delta, brk, brkSize)}
          style={regleInput} />
      </label>
      <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--fs-caption)', color: TEXT_2 }}>
        <span style={{ width: 30 }}>{t('measuregrid.regle_break')}</span>
        <input type="text" inputMode="decimal" value={brk} aria-label={t('measuregrid.regle_break')}
          disabled={!brkSize} onChange={e => setBrk(e.target.value)} onBlur={() => save(delta, brk, brkSize)}
          style={{ ...regleInput, opacity: brkSize ? 1 : 0.5 }} />
        <span>{t('measuregrid.regle_from')}</span>
        <select value={brkSize} aria-label={t('measuregrid.regle_from')}
          onChange={e => { const v = e.target.value; setBrkSize(v); save(delta, brk, v) }}
          style={{ font: 'inherit', fontSize: 'var(--fs-caption)', padding: '1px 2px', border: `1px solid ${BORDER}`,
                   borderRadius: 3, background: 'var(--white)', color: 'var(--text-main)' }}>
          <option value="">{t('measuregrid.regle_none')}</option>
          {(sizeRun || []).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
    </div>
  )
}

// FONT per defecte: el CHECK. Encapsula els 4 seams (load · buildGroups/buildRows · makeOnSave ·
// buildLeadCols) reusant els sub-components d'aquest fitxer. El comportament és idèntic al d'abans
// de Sprint Y; el component només l'orquestra a través de la font (cap `if (mode)` escampat).
const checkSource = {
  kind: 'check',
  supportsResolve: true,
  supportsReorder: true,
  supportsPoda: true,     // C1 — la taula de mesures del model és seva: aquí sí s'hi pot podar.

  load(model, ctx) {
    // CONSULTA: NO obre cap check (només llegeix el més recent). TREBALL: open idempotent.
    const checkP = ctx.readOnly
      ? sizeChecks.list({ model: model.id, ordering: '-created_at', page_size: 1 })
          .then(r => { const rows = r.data?.results ?? r.data ?? []; return rows.length ? sizeChecks.get(rows[0].id).then(x => x.data) : null })
          .catch(() => null)
      : sizeChecks.open(model.id).then(r => r.data).catch(() => null)
    return Promise.all([models.baseStages(model.id).then(r => r.data).catch(() => null), checkP])
      .then(([stages, chk]) => {
        if (!chk && !ctx.readOnly) ctx.onFeedback?.({ type: 'err', text: ctx.t('sizecheck.open_error') })
        return { baseData: stages, check: chk }
      })
  },

  buildGroups(raw, ctx) {
    const stages = raw.baseData?.stages || []
    return [{
      key: 'base',
      label: raw.baseData?.base_size || ctx.t('basestage.stage_measure'),
      accent: true,
      historyCols: stages.map((s, i) => ({ key: s.key, label: <StageLabel ctx={s.context} at={i === 0 ? null : s.at} first={i === 0} /> })),
      activeLabel: ctx.t('sizecheck.col_real'),
      trailCols: [{ key: 'dn', label: `${ctx.t('sizecheck.col_decision')} · ${ctx.t('sizecheck.col_note')}` }],
    }]
  },

  buildRows(raw, ctx) {
    const stages = raw.baseData?.stages || []
    const lineByPom = {}
    for (const l of (raw.check?.lines || [])) lineByPom[l.pom_id] = l
    return (raw.baseData?.rows || []).map(r => {
      const line = lineByPom[r.pom_id]
      return {
        pom_id: r.pom_id,
        codi: r.nom_fitxa || r.pom_code,
        pom_code: r.pom_code,
        nom_en: r.nom_en, nom_local: r.nom_ca,
        nom_fitxa: r.nom_fitxa, bm_id: r.base_measurement_id,
        is_key: r.is_key,
        logica: line?.logica, increment_base: line?.increment_base,
        increment_break: line?.increment_break, talla_break_label: line?.talla_break_label,
        tol_minus: line?.tol_minus, tol_plus: line?.tol_plus,
        cells: { base: {
          history: Object.fromEntries(stages.map(s => [s.key, (s.key in r.takes) ? r.takes[s.key] : null])),
          active: line ? { lineId: line.id, value: line.valor_real ?? line.valor_teoric, baseValue: line.valor_teoric, tol: { minus: line.tol_minus, plus: line.tol_plus } } : null,
          trail: { dn: line ? (ctx.readOnly ? <ReadOnlyDecisioNota line={line} /> : <DecisioNotaCell line={line} />) : null },
        } },
      }
    })
  },

  makeOnSave() {
    return (lineId, value) => sizeCheckLines.update(lineId, { valor_real: value })
  },

  onNomSave(bmId, value) {
    return baseMeasurements.update(bmId, { nom_fitxa: value || null })
  },

  onReorder(model, orderedBmIds) {
    return baseMeasurements.reorder(model.id, orderedBmIds)
  },

  // Règim: en CONSULTA (o lockRules), lectura (logica + etiqueta de regla). En TREBALL, la regla
  // (delta + break) és EDITABLE — patrimoni viu del model (P3). Sprint Y: lockRules la posa en
  // lectura sense fer read-only les preses (mode sessió de fitting sobre la font check no s'usa avui,
  // però la branca és coherent amb la font fitting).
  buildLeadCols(raw, ctx) {
    const lockRegle = ctx.readOnly || ctx.lockRules
    return [{
      key: 'regim', label: ctx.t('fitting.grid.regime'), width: lockRegle ? 118 : 184,
      render: (row) => (lockRegle ? (
        <div>
          <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-main)' }}>{row.logica ?? '—'}</div>
          {regleLabel(row, ctx.t) && (
            <div style={{ fontSize: 'var(--fs-caption)', color: TEXT_2, whiteSpace: 'nowrap', marginTop: 1 }}>{regleLabel(row, ctx.t)}</div>
          )}
        </div>
      ) : (
        <RegleEditCell modelId={ctx.model.id} row={row} sizeRun={ctx.sizeRun} onFeedback={ctx.onFeedback} />
      )),
    }, {
      key: 'tol', label: ctx.t('sizecheck.col_tolerance'), width: 72,
      render: (row) => (
        <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>
          {row.tol_minus != null ? `-${row.tol_minus}/+${row.tol_plus}` : '—'}
        </span>
      ),
    }]
  },
}

export default function CheckMeasureEditor({ model, onFeedback, onResolved, onBack = null, readOnly = false, taskId = null, source = null, sourceCtx = null, lockRules = false, onSessionSaved = null }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const src = source || checkSource
  const [raw, setRaw] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(null)
  const [reschedule, setReschedule] = useState(null)
  const [reDate, setReDate] = useState('')

  // Run de talles del model (per al desplegable "a partir de" del break de la regla).
  const sizeRun = (model?.size_run_model || '').split('·').map(s => s.trim()).filter(Boolean)
  const ctx = { t, model, readOnly, lockRules, onFeedback, sizeRun, fittingSession: sourceCtx?.fittingSession }

  const load = useCallback(() => {
    setLoading(true)
    Promise.resolve(src.load(model, { t, readOnly, onFeedback, fittingSession: sourceCtx?.fittingSession }))
      .then(r => setRaw(r))
      // El 400 de create-piece («el model no té cap GradingVersion activa») és un diagnòstic
      // accionable, no un error de xarxa: cal DIR-LO. Però el text del backend és català fix, i
      // aquesta superfície la miren tenants EN/ES → el cas conegut passa per clau i18n; la resta
      // d'errors mostren el text del servidor (patró de doResolve), amb el genèric de xarxa de
      // seguretat. Amb raw=null la graella surt buida i la pantalla queda viva.
      .catch(e => {
        setRaw(null)
        const msg = e?.response?.data?.error || ''
        onFeedback?.({
          type: 'err',
          text: /GradingVersion|talles/i.test(msg)
            ? t('fitting.save.no_grading', { codi: model.codi_intern })
            : (msg || t('sizecheck.open_error')),
        })
      })
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [model.id, readOnly, src, sourceCtx?.fittingSession])

  useEffect(() => { load() }, [load])

  const check = raw?.check || null
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

  // onSave el fa la font (check: PATCH size-check-line; fitting: despatx STEP/LINEAR). Depèn de raw
  // (el fitting hi llegeix el mapa de règims). onNomSave/onReorder: comuns, delegats a la font i
  // rellegint (mirall del comportament anterior). lockRules bloqueja el nom (mode sessió).
  const onSave = useCallback((lineId, value) => (raw ? src.makeOnSave(raw, ctx)(lineId, value) : Promise.resolve()),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [raw, src])
  const onNomSave = useCallback((bmId, value) =>
    Promise.resolve(src.onNomSave?.(bmId, value))
      .then(() => load())
      .catch(() => onFeedback?.({ type: 'err', text: t('measuregrid.nom_save_err') })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [src, load, onFeedback, t])
  const onReorder = useCallback((orderedBmIds) =>
    Promise.resolve(src.onReorder?.(model, orderedBmIds))
      .then(() => load())
      .catch(() => onFeedback?.({ type: 'err', text: t('measuregrid.reorder_err') })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [src, model.id, load, onFeedback, t])
  // C1 (PRINCIPI DEL SOROLL) — poda d'un POM del model des de la graella: SOFT (is_active=False)
  // + registre al log de mesures. La UI diu «treure»; la BD guarda memòria. Mai DELETE dur.
  const onPodar = useCallback((row) =>
    models.desactivarPom(model.id, row.pom_id)
      .then(() => load())
      .then(() => onFeedback?.({ type: 'ok', text: t('measuregrid.poda_ok', { codi: row.codi || row.pom_code || '' }) }))
      .catch(() => onFeedback?.({ type: 'err', text: t('measuregrid.poda_err') })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [model.id, load, onFeedback, t])

  if (loading) return <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>{t('common.loading')}</div>

  // Els 4 seams de dades venen SEMPRE de la font — cap `if (mode)` escampat pel render.
  const groups = raw ? src.buildGroups(raw, ctx) : []
  const rows = raw ? src.buildRows(raw, ctx) : []
  const leadCols = raw ? src.buildLeadCols(raw, ctx) : []
  const canReorder = !readOnly && src.supportsReorder
  // Només la superfície de MESURES del model (font check) és propietària de la taula de POMs:
  // al fitting la fila és una presa d'una sessió, no patrimoni que es pugui podar des d'allà.
  const canPodar = !readOnly && src.supportsPoda
  const canEditNom = !readOnly && !lockRules   // lockRules: nomenclatura read-only, preses editables

  return (
    <div>
      <EditorHeader model={model} onBack={onBack} />
      <DependencyPanel model={model} />
      {/* Sprint Y — en mode sessió (font fitting), el panell de la sessió: context + Canvis/Observacions/Imatges. */}
      {ctx.fittingSession && <SessionPanel session={ctx.fittingSession} pieceFittingId={raw?.pieceFittingId} grid={raw?.grid} />}
      {/* P0 — la PROMOCIÓ viu aquí, sobre la taula de mesures del model: és el material que
          promou i el lloc on el tècnic ja hi és. Acte separat i explícit, mai un pas d'un flux
          (llei D-PROM). El component s'auto-amaga sense capability CONFIGURE o sense item. */}
      {src.kind === 'check' && !readOnly && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
          <PromoteToItemButton model={model} onFeedback={onFeedback} />
        </div>
      )}
      <MeasureGrid rows={rows} groups={groups} leadCols={leadCols} editable={!readOnly}
        onSave={readOnly ? undefined : onSave} onNomSave={canEditNom ? onNomSave : undefined}
        editCodi reorderable={canReorder} onReorder={canReorder ? onReorder : undefined}
        onPodar={canPodar ? onPodar : undefined}
        empty={
          // Estat buit GUIAT: un model sense BaseMeasurement (POM per definir) no pot ser un
          // cul-de-sac. En mode treball sobre la superfície de mesures (font check) expliquem
          // el pas que falta i oferim la CTA a Definició POM (mode entrada). Fora d'això, el text pla.
          (src.kind === 'check' && !readOnly) ? (
            <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2, padding: '8px 0', display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'flex-start' }}>
              <span>{t('basestage.no_base_title')}</span>
              <button type="button" onClick={() => navigate(`/models/${model.id}?tab=Mesures&mode=entry`)}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 4, border: '0.5px solid var(--gold)', background: 'var(--white)', color: 'var(--gold)', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
                <i className="ti ti-ruler-2" aria-hidden="true" style={{ fontSize: 16 }} />
                {t('basestage.no_base_cta')}
              </button>
            </div>
          ) : (
            <p style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>{t('basestage.empty')}</p>
          )
        } />

      {src.supportsResolve && !readOnly && check && rows.length > 0 && (
        <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
          <button style={btn('gold')} disabled={busy} onClick={() => onResolveClick('Acceptat')}>{t('sizecheck.save')}</button>
          <button style={btn('err')} disabled={busy} onClick={() => onResolveClick('Descartat')}>{t('sizecheck.discard')}</button>
        </div>
      )}

      {/* D-12 — Watchpoints del model (crear en treball, veure sempre). Origen = la tasca actual. */}
      {/* Sprint Y — accions del mode sessió (gravar-i-tornar + reobertura + descartar). Y6 cablarà
          el retorn a la fulla via onSessionSaved; per defecte surt de l'edició (onResolved). */}
      {ctx.fittingSession && !readOnly && (
        <SessionActions session={ctx.fittingSession} pieceFittingId={raw?.pieceFittingId} taskId={taskId}
          onSaved={() => (onSessionSaved || onResolved)?.()} onReload={load} onFeedback={onFeedback} />
      )}

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
