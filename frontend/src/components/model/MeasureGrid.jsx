import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { thStyle, SaveStatus, useDebouncedSave, fmtMeasure, useUnit } from '../../pages/fittingShared'

// MeasureGrid — editor únic de mesures (un component, dos modes treball/consulta) que serveix els
// DOS eixos via SLOTS, reusant l'esquelet del fitting editor (MeasureTable):
//  · files = POMs amb nomenclatura a 2 línies (nom EN canònic dalt · nom idioma usuari sota).
//  · columnes en GRUPS: cada grup = N columnes d'història READ-ONLY + 1 columna ACTIVA editable.
//      - check: 1 grup 'base', història = estadis (import/manual/checked), activa = Real.
//      - fitting: N grups (talles), història = versions, activa = Fit actual.
//  · slots: leadCols (sticky, p.ex. Règim del fitting), trailCols per grup (p.ex. Decisió/Nota del check),
//      i `actions` (barra de resolució). El proveïdor d'EIX construeix `groups`+`rows`; aquí no se'n sap res.
// Controlat: els valors arriben per `rows`; en desar es crida onSave(lineId, value) i, si retorna línies
// propagades (fitting), s'actualitzen les germanes (excepte la cel·la amb focus). Motors INTACTES.

const COL_POM_W = 78
const COL_NOM_W = 160

// `filled` = gold-pale (NOMÉS la columna activa destaca); groupStart/End = filet subtil de
// delimitació del grup (no daurat, per no competir amb el destacat de l'activa).
const cellTd = (filled, groupStart, groupEnd) => ({
  padding: '5px 8px', borderBottom: '0.5px solid var(--border)', verticalAlign: 'middle',
  textAlign: 'right', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums',
  background: filled ? 'var(--gold-pale)' : undefined,
  borderLeft: groupStart ? '1px solid var(--border)' : '0.5px solid var(--border)',
  borderRight: groupEnd ? '1px solid var(--border)' : undefined,
})

// Parse numèric tolerant amb la COMA decimal (60,5 == 60.5). Buit → null; no-numèric → NaN.
// L'input editable és type=text inputMode=decimal perquè la coma s'hi pugui escriure (type=number la
// rebutja segons locale abans d'arribar a onChange).
const toNum = (v) => (v === '' || v == null) ? null : Number(String(v).replace(',', '.'))

const isModified = (value, baseValue) => value !== '' && value != null && baseValue != null
  && toNum(value) !== Number(baseValue)

// C2 (PRINCIPI DEL SOROLL) — fila CANDIDATA A PODA: cap valor real enlloc (base i talles totes a
// zero o buides, història inclosa). El model s'alimenta de realitat; una fila així no n'aporta cap.
// És un INDICADOR, no un automatisme: qui decideix és el tècnic, amb la columna d'acció.
const isNoiseRow = (row, groups) => {
  let vist = false
  for (const g of groups) {
    const cell = row.cells?.[g.key]
    if (!cell) continue
    const vals = []
    for (const h of (g.historyCols || [])) {
      const hv = cell.history?.[h.key]
      vals.push(hv && typeof hv === 'object' ? hv.value : hv)
    }
    if (cell.active) vals.push(cell.active.value)
    for (const v of vals) {
      if (v === null || v === undefined || v === '') continue
      vist = true
      if (Number(v) !== 0) return false
    }
  }
  // Sense cap valor llegit no es pot afirmar res: no es marca (millor callar que acusar).
  return vist
}

// Marcatge vermell de la cel·la activa: per defecte "difereix de base" (fitting); si l'active porta
// `tol` (check), vermell NOMÉS quan surt de la banda de tolerància [base-minus, base+plus].
const activeRed = (value, active) => {
  if (value === '' || value == null) return false
  if (active.tol && active.baseValue != null) {
    const v = toNum(value)
    return v < active.baseValue - active.tol.minus || v > active.baseValue + active.tol.plus
  }
  return isModified(value, active.baseValue)
}

// Cel·la activa editable (única amb input + autosave). Vermell si difereix de baseValue; negreta si
// editada a mà (ancoratge). Buida si no hi ha línia activa per a aquest (pom, grup).
const stepBtnStyle = {
  display: 'flex', alignItems: 'center', justifyContent: 'center', height: 11, width: 16,
  padding: 0, border: '1px solid var(--border)', background: 'var(--white)',
  color: 'var(--text-muted)', cursor: 'pointer', lineHeight: 1, fontSize: 9,
}

function ActiveCell({ active, editable, value, edited, onChange, onCommit, focusRef, unit }) {
  const [state, schedule] = useDebouncedSave(onCommit)
  const [focused, setFocused] = useState(false)
  if (!active) return <td style={cellTd(true, false, false)} />
  const modified = activeRed(value, active)
  // `active.readonly` força lectura en una cel·la concreta encara que la graella sigui editable
  // (p.ex. la talla base de l'Escalat, que no s'edita com a override).
  if (!editable || active.readonly) {
    // Lectura: format de presentació (1 decimal cm · 2 inch).
    return (
      <td style={{ ...cellTd(true, false, false), color: modified ? 'var(--err)' : 'var(--text-main)' }}>
        {fmtMeasure(value, unit) ?? '—'}
      </td>
    )
  }
  // Edició: mentre s'escriu (focus) es mostra el valor CRU per teclejar lliure (coma inclosa); en
  // perdre el focus es mostra FORMATAT (1 decimal cm · 2 inch), coherent amb les cel·les de lectura.
  // Es desa sempre el valor canònic (toNum normalitza la coma al commit). type=text + fletxes pròpies
  // (type=number no admet coma; les fletxes natives només existeixen a type=number → es recreen aquí).
  const num = toNum(value)
  const shown = focused
    ? (value ?? '')
    : (num == null || Number.isNaN(num) ? (value ?? '') : fmtMeasure(num, unit))
  const bump = (dir) => {
    const baseN = (num == null || Number.isNaN(num)) ? 0 : num
    const next = String(Math.round((baseN + dir * 0.1) * 100) / 100)   // pas 0.1 (cm canònic)
    onChange(active.lineId, next)
    schedule(next)
  }
  return (
    <td style={{ ...cellTd(true, false, false), position: 'relative' }}>
      <span style={{ display: 'inline-flex', alignItems: 'stretch', gap: 2 }}>
        <input
          type="text" inputMode="decimal" value={shown}
          onFocus={() => { setFocused(true); focusRef.current = active.lineId }}
          onBlur={() => { setFocused(false); if (focusRef.current === active.lineId) focusRef.current = null }}
          onChange={e => { onChange(active.lineId, e.target.value); schedule(e.target.value) }}
          style={{
            font: 'inherit', width: 70, padding: '2px 4px', textAlign: 'right',
            border: '1px solid var(--border)', borderRadius: 4, background: 'var(--white)',
            color: modified ? 'var(--err)' : 'var(--text-main)',
            fontWeight: modified && edited ? 700 : 400,
            fontVariantNumeric: 'tabular-nums', boxSizing: 'border-box',
          }}
        />
        <span style={{ display: 'inline-flex', flexDirection: 'column', justifyContent: 'center' }}>
          <button type="button" tabIndex={-1} title="+0.1" aria-label="+0.1"
            onMouseDown={e => e.preventDefault()} onClick={() => bump(1)}
            style={{ ...stepBtnStyle, borderRadius: '4px 4px 0 0', borderBottom: 'none' }}>
            <i className="ti ti-chevron-up" />
          </button>
          <button type="button" tabIndex={-1} title="-0.1" aria-label="-0.1"
            onMouseDown={e => e.preventDefault()} onClick={() => bump(-1)}
            style={{ ...stepBtnStyle, borderRadius: '0 0 4px 4px' }}>
            <i className="ti ti-chevron-down" />
          </button>
        </span>
      </span>
      <SaveStatus state={state} absolute />
    </td>
  )
}

// Nomenclatura a 2 línies (llei de presentació): nom EN canònic a dalt (sembra, read-only) + nom
// local a sota (petit, cursiva, gris). Aquesta cel·la és DESCRIPTIVA (només noms); la nomenclatura
// CURTA (nom_fitxa, CH/WA/HI) s'edita a la columna POM (CodiCell) quan `editCodi`. Llegat: quan
// `editCodi` és fals (fitting), la 2a línia mostra nom_fitxa amb precedència i és EDITABLE via
// `onNomSave(bmId, value)` (P4: NO toca el POM tenant compartit).
function NomCell({ nomEn, nomLocal, nomFitxa, bmId, editable, onNomSave, editCodi = false, style }) {
  const top = nomEn || nomLocal || ''
  const canon = nomEn && nomLocal && nomLocal !== nomEn ? nomLocal : (nomLocal || '')
  // editCodi → la 2a línia és el nom LOCAL (la nomenclatura curta viu a la columna POM, no aquí).
  const modelName = editCodi ? canon : ((nomFitxa != null && nomFitxa !== '') ? nomFitxa : canon)
  const canEdit = !!(editable && bmId != null && onNomSave && !editCodi)
  const [val, setVal] = useState(modelName ?? '')
  const [focused, setFocused] = useState(false)
  useEffect(() => { if (!focused) setVal(modelName ?? '') }, [modelName, focused])
  const commit = () => {
    setFocused(false)
    const v = (val ?? '').trim()
    if (v !== (modelName ?? '')) onNomSave(bmId, v)
  }
  return (
    <td style={style}>
      <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', whiteSpace: 'normal' }}>{top || '—'}</div>
      {canEdit ? (
        <input
          value={val ?? ''} onChange={e => setVal(e.target.value)}
          onFocus={() => setFocused(true)} onBlur={commit}
          onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.blur() }}
          placeholder={canon || ''}
          style={{
            font: 'inherit', fontSize: 'var(--fs-caption)', fontStyle: 'italic',
            color: 'var(--text-muted)', width: '100%', padding: '0 2px', boxSizing: 'border-box',
            borderRadius: 3, background: focused ? 'var(--white)' : 'transparent',
            // Affordance: subratllat tènue en repòs (pista d'editabilitat) → vora completa en focus.
            border: '1px solid transparent',
            borderBottom: focused ? '1px solid var(--border)' : '1px dashed var(--border)',
            ...(focused && { borderColor: 'var(--border)' }),
          }}
        />
      ) : (modelName && (
        <div style={{ fontSize: 'var(--fs-caption)', fontStyle: 'italic', color: 'var(--text-muted)', whiteSpace: 'normal' }}>{modelName}</div>
      ))}
    </td>
  )
}

// Columna POM = nomenclatura CURTA del model (nom_fitxa: CH/WA/HI). En lectura mostra `codi`
// (nom_fitxa || pom_code global). En edició (`editCodi` + bmId + onNomSave) és un input que desa
// nom_fitxa per-model via onNomSave (NO toca el POM global; placeholder = codi global per defecte).
// Mateix patró que el llegat del NomCell: buffer local, commit on blur, affordance només si editable.
function CodiCell({ codi, nomFitxa, pomCode, bmId, isKey, editable, editCodi, onNomSave, reorderable, style, title }) {
  const { t } = useTranslation()
  const canEdit = !!(editable && editCodi && bmId != null && onNomSave)
  const [val, setVal] = useState(nomFitxa ?? '')
  const [focused, setFocused] = useState(false)
  useEffect(() => { if (!focused) setVal(nomFitxa ?? '') }, [nomFitxa, focused])
  const commit = () => {
    setFocused(false)
    const v = (val ?? '').trim()
    if (v !== (nomFitxa ?? '')) onNomSave(bmId, v)
  }
  return (
    <td style={style} title={title}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
        {reorderable && (
          <i className="ti ti-grip-vertical" title={t('measuregrid.reorder')}
            style={{ fontSize: 12, color: 'var(--text-muted)', cursor: 'grab' }} />
        )}
        {canEdit ? (
          <input
            value={val ?? ''} onChange={e => setVal(e.target.value)}
            onFocus={() => setFocused(true)} onBlur={commit}
            onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.blur() }}
            placeholder={pomCode || ''}
            style={{
              font: 'inherit', fontWeight: 500, color: 'var(--gold)', width: 52,
              padding: '0 2px', boxSizing: 'border-box', borderRadius: 3,
              background: focused ? 'var(--white)' : 'transparent',
              // Affordance: subratllat tènue en repòs → vora completa en focus.
              border: '1px solid transparent',
              borderBottom: focused ? '1px solid var(--border)' : '1px dashed var(--border)',
              ...(focused && { borderColor: 'var(--border)' }),
            }}
          />
        ) : (
          <span style={{ fontWeight: 500, color: 'var(--gold)' }}>{codi}</span>
        )}
        {isKey && <i className="ti ti-star" style={{ fontSize: 9, marginLeft: 3, color: 'var(--gold)' }} title="KEY" />}
      </span>
    </td>
  )
}

export default function MeasureGrid({
  rows = [],
  groups = [],            // [{key, label, accent?, historyCols:[{key,label}], activeLabel, trailCols:[{key,label}]}]
  leadCols = [],          // [{key, label, width, render:(row)=>node}]  sticky després de POM/Nom (consulta: render pot ser text)
  editable = false,
  onSave,                 // (lineId, rawValue) => Promise (pot resoldre amb {lines:[{id,valor_real}]} per propagar)
  onNomSave = null,       // (bmId, value) => Promise — desa la nomenclatura curta del MODEL (nom_fitxa, P4); null = no editable
  editCodi = false,       // on s'edita nom_fitxa: true → columna POM (codi curt CH/WA/HI, Mesures); false → 2a línia del Nom (fitting, llegat)
  reorderable = false,    // DnD de files (NOMÉS Mesures-edició); default false → Escalat/fitting/consulta intactes
  onReorder = null,       // (orderedBmIds) => Promise — desa el nou ordre global del model
  onPodar = null,         // C1 — (row) => Promise: treu el POM del model (SOFT). null = cap columna d'acció
  empty = null,           // node quan no hi ha files
}) {
  const { t } = useTranslation()
  const unit = useUnit()                       // unitat del tenant (CM|INCH) → format de presentació
  const [vals, setVals] = useState({})        // buffer local lineId -> string
  const [edited, setEdited] = useState(() => new Set())  // ancoratge (editat a mà)
  const focusRef = useRef(null)
  const dragFrom = useRef(null)
  // C1 — confirmació LLEUGERA (dos temps a la mateixa fila, sense modal): el primer clic arma
  // la fila, el segon la poda. Treure una mesura del model no ha de ser un clic distret.
  const [podaArmada, setPodaArmada] = useState(null)   // pom_id
  const [podant, setPodant] = useState(false)
  const canPodar = !!(editable && onPodar)
  // Reordena (DnD): en deixar anar, calcula el nou ordre de bm_id i ho delega a onReorder (que desa +
  // refresca). Sense estat visual local: la fila es recol·loca en rellegir (simple i sense desincronies).
  const onRowDrop = (toIdx) => {
    const from = dragFrom.current
    dragFrom.current = null
    if (from == null || from === toIdx || !onReorder) return
    const ids = rows.map(r => r.bm_id)
    const [moved] = ids.splice(from, 1)
    ids.splice(toIdx, 0, moved)
    onReorder(ids.filter(x => x != null))
  }

  // Sincronitza el buffer des de les props quan canvien els valors actius (excepte la cel·la amb focus,
  // perquè la propagació/refresc no trepitgi el que l'usuari està escrivint).
  useEffect(() => {
    setVals(prev => {
      const next = { ...prev }
      for (const r of rows) {
        for (const g of groups) {
          const a = r.cells?.[g.key]?.active
          if (a && a.lineId !== focusRef.current && next[a.lineId] === undefined) {
            next[a.lineId] = a.value ?? ''
          }
        }
      }
      return next
    })
  }, [rows, groups])

  const onChange = useCallback((lineId, raw) => {
    setVals(prev => ({ ...prev, [lineId]: raw }))
    setEdited(prev => { const n = new Set(prev); n.add(lineId); return n })
  }, [])

  const commitFor = useCallback((lineId) => (raw) => {
    if (!onSave) return Promise.resolve()
    const num = toNum(raw)
    if (Number.isNaN(num)) return Promise.resolve()   // entrada incompleta/no-numèrica → no desa
    return Promise.resolve(onSave(lineId, num)).then(res => {
      const propagated = res && res.data ? res.data.linies || res.data.lines : (res && (res.linies || res.lines))
      if (Array.isArray(propagated)) {
        setVals(prev => {
          const next = { ...prev }
          for (const l of propagated) {
            if (l.id !== focusRef.current) next[l.id] = l.valor_real ?? ''
          }
          return next
        })
      }
      return res
    })
  }, [onSave])

  if (!rows.length) return empty

  // Offsets sticky acumulats: POM(0) · Nom · leadCols… (sense mutació, per al react-compiler).
  const baseLeft = COL_POM_W + COL_NOM_W
  const leadLefts = leadCols.map((_, i) => baseLeft + leadCols.slice(0, i).reduce((s, c) => s + c.width, 0))

  const stickyHd = (left, w) => ({ ...thStyle, position: 'sticky', left, zIndex: 3, minWidth: w, width: w, background: 'var(--bg-muted)', textAlign: 'left' })
  const stickyTd = (left, w, bg) => ({ position: 'sticky', left, zIndex: 1, minWidth: w, width: w, background: bg, padding: '5px 10px', borderBottom: '0.5px solid var(--border)', verticalAlign: 'middle', whiteSpace: 'nowrap' })

  return (
    <div style={{ overflow: 'auto', maxHeight: '70vh', width: '100%' }}>
      <table style={{ borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
        <thead>
          <tr>
            <th rowSpan={2} style={stickyHd(0, COL_POM_W)}>{t('measuregrid.col_pom')}</th>
            <th rowSpan={2} style={stickyHd(COL_POM_W, COL_NOM_W)}>{t('measuregrid.col_nom')}</th>
            {leadCols.map((c, i) => (
              <th key={c.key} rowSpan={2} style={stickyHd(leadLefts[i], c.width)}>{c.label}</th>
            ))}
            {groups.map(g => {
              const span = (g.historyCols?.length || 0) + 1 + (g.trailCols?.length || 0)
              return (
                <th key={g.key} colSpan={span} style={{
                  ...thStyle, textAlign: 'center',
                  background: 'var(--bg-muted)',
                  borderLeft: '1px solid var(--border)',
                }}>{g.label}</th>
              )
            })}
            {canPodar && (
              <th rowSpan={2} style={{ ...thStyle, textAlign: 'center', width: 64, minWidth: 64,
                                       background: 'var(--bg-muted)', borderLeft: '1px solid var(--border)' }}>
                {t('measuregrid.col_accions')}
              </th>
            )}
          </tr>
          <tr>
            {groups.flatMap(g => {
              const sub = (start) => ({ ...thStyle, textAlign: 'right', fontSize: 'var(--fs-caption)', padding: '3px 8px',
                background: 'var(--bg-muted)',
                borderLeft: start ? '1px solid var(--border)' : '0.5px solid var(--border)' })
              const activeSub = { ...sub(false), background: 'var(--gold-pale)' }   // NOMÉS la columna activa destaca
              const hs = (g.historyCols || []).map((h, idx) => <th key={`${g.key}-h-${h.key}`} style={sub(idx === 0)}>{h.label}</th>)
              hs.push(<th key={`${g.key}-active`} style={activeSub}>{g.activeLabel}</th>)
              for (const tcol of (g.trailCols || [])) hs.push(<th key={`${g.key}-t-${tcol.key}`} style={{ ...sub(false), textAlign: 'center' }}>{tcol.label}</th>)
              return hs
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const rowBg = i % 2 === 0 ? 'var(--white)' : 'var(--bg-card)'
            // C2 — candidata a poda: indicador SUBTIL (un filet a l'esquerra), mai un automatisme.
            const soroll = isNoiseRow(r, groups)
            return (
              <tr key={r.pom_id} style={{ background: rowBg }}
                draggable={reorderable || undefined}
                onDragStart={reorderable ? (() => { dragFrom.current = i }) : undefined}
                onDragOver={reorderable ? (e => e.preventDefault()) : undefined}
                onDrop={reorderable ? (() => onRowDrop(i)) : undefined}>
                <CodiCell codi={r.codi} nomFitxa={r.nom_fitxa} pomCode={r.pom_code} bmId={r.bm_id}
                  isKey={r.is_key} editable={editable} editCodi={editCodi} onNomSave={onNomSave}
                  reorderable={reorderable}
                  style={soroll
                    ? { ...stickyTd(0, COL_POM_W, rowBg), boxShadow: 'inset 3px 0 0 var(--border)' }
                    : stickyTd(0, COL_POM_W, rowBg)}
                  title={soroll ? t('measuregrid.poda_candidata') : undefined} />
                <NomCell nomEn={r.nom_en} nomLocal={r.nom_local} nomFitxa={r.nom_fitxa} bmId={r.bm_id}
                  editable={editable} onNomSave={onNomSave} editCodi={editCodi} style={stickyTd(COL_POM_W, COL_NOM_W, rowBg)} />
                {leadCols.map((c, idx) => (
                  <td key={c.key} style={stickyTd(leadLefts[idx], c.width, rowBg)}>{c.render(r)}</td>
                ))}
                {groups.flatMap(g => {
                  const cell = r.cells?.[g.key] || {}
                  const out = (g.historyCols || []).map((h, idx) => {
                    const hv = cell.history?.[h.key]
                    const v = hv && typeof hv === 'object' ? hv.value : hv
                    return (
                      <td key={`${g.key}-h-${h.key}`} style={{ ...cellTd(false, idx === 0, false), color: 'var(--text-main)' }}>
                        {fmtMeasure(v, unit) ?? '—'}
                      </td>
                    )
                  })
                  const a = cell.active
                  out.push(
                    <ActiveCell key={`${g.key}-active`} active={a} editable={editable} unit={unit}
                      value={a ? (vals[a.lineId] ?? '') : ''} edited={a ? edited.has(a.lineId) : false}
                      onChange={onChange} onCommit={a ? commitFor(a.lineId) : (() => Promise.resolve())} focusRef={focusRef} />
                  )
                  for (const tcol of (g.trailCols || [])) {
                    out.push(<td key={`${g.key}-t-${tcol.key}`} style={{ padding: '5px 8px', borderBottom: '0.5px solid var(--border)', verticalAlign: 'middle' }}>{cell.trail?.[tcol.key] ?? null}</td>)
                  }
                  return out
                })}
                {canPodar && (
                  <td style={{ padding: '5px 8px', borderBottom: '0.5px solid var(--border)',
                               borderLeft: '1px solid var(--border)', textAlign: 'center',
                               verticalAlign: 'middle', whiteSpace: 'nowrap' }}>
                    {podaArmada === r.pom_id ? (
                      <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                        <button type="button" title={t('measuregrid.poda_confirma')}
                          aria-label={t('measuregrid.poda_confirma')} disabled={podant}
                          onClick={() => {
                            setPodant(true)
                            Promise.resolve(onPodar(r))
                              .finally(() => { setPodant(false); setPodaArmada(null) })
                          }}
                          style={{ border: 'none', background: 'transparent', cursor: podant ? 'wait' : 'pointer',
                                   color: 'var(--err)', padding: 2, lineHeight: 1 }}>
                          <i className="ti ti-check" aria-hidden="true" style={{ fontSize: 15 }} />
                        </button>
                        <button type="button" title={t('common.cancel')} aria-label={t('common.cancel')}
                          onClick={() => setPodaArmada(null)}
                          style={{ border: 'none', background: 'transparent', cursor: 'pointer',
                                   color: 'var(--text-muted)', padding: 2, lineHeight: 1 }}>
                          <i className="ti ti-x" aria-hidden="true" style={{ fontSize: 15 }} />
                        </button>
                      </span>
                    ) : (
                      <button type="button" title={t('measuregrid.poda_title')}
                        aria-label={t('measuregrid.poda_title')}
                        onClick={() => setPodaArmada(r.pom_id)}
                        style={{ border: 'none', background: 'transparent', cursor: 'pointer',
                                 color: 'var(--text-muted)', padding: 2, lineHeight: 1 }}>
                        <i className="ti ti-trash" aria-hidden="true" style={{ fontSize: 14 }} />
                      </button>
                    )}
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
