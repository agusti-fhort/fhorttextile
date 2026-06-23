import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { thStyle, SaveStatus, useDebouncedSave } from '../../pages/fittingShared'

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

const isModified = (value, baseValue) => value !== '' && value != null && baseValue != null
  && Number(value) !== Number(baseValue)

// Marcatge vermell de la cel·la activa: per defecte "difereix de base" (fitting); si l'active porta
// `tol` (check), vermell NOMÉS quan surt de la banda de tolerància [base-minus, base+plus].
const activeRed = (value, active) => {
  if (value === '' || value == null) return false
  if (active.tol && active.baseValue != null) {
    const v = Number(value)
    return v < active.baseValue - active.tol.minus || v > active.baseValue + active.tol.plus
  }
  return isModified(value, active.baseValue)
}

// Cel·la activa editable (única amb input + autosave). Vermell si difereix de baseValue; negreta si
// editada a mà (ancoratge). Buida si no hi ha línia activa per a aquest (pom, grup).
function ActiveCell({ active, editable, value, edited, onChange, onCommit, focusRef }) {
  const [state, schedule] = useDebouncedSave(onCommit)
  if (!active) return <td style={cellTd(true, false, false)} />
  const modified = activeRed(value, active)
  if (!editable) {
    return (
      <td style={{ ...cellTd(true, false, false), color: modified ? 'var(--err)' : 'var(--text-main)' }}>
        {value === '' || value == null ? '—' : value}
      </td>
    )
  }
  return (
    <td style={{ ...cellTd(true, false, false), position: 'relative' }}>
      <input
        type="number" step="0.1" value={value ?? ''}
        onFocus={() => { focusRef.current = active.lineId }}
        onBlur={() => { if (focusRef.current === active.lineId) focusRef.current = null }}
        onChange={e => { onChange(active.lineId, e.target.value); schedule(e.target.value) }}
        style={{
          font: 'inherit', width: 88, padding: '2px 4px', textAlign: 'right',
          border: '1px solid var(--border)', borderRadius: 4, background: 'var(--white)',
          color: modified ? 'var(--err)' : 'var(--text-main)',
          fontWeight: modified && edited ? 700 : 400,
          fontVariantNumeric: 'tabular-nums', boxSizing: 'border-box',
        }}
      />
      <SaveStatus state={state} absolute />
    </td>
  )
}

// Nomenclatura a 2 línies (llei de presentació): nom EN canònic a dalt + idioma usuari a sota
// (petit, cursiva, gris). Fallback al que hi hagi.
function NomCell({ nomEn, nomLocal, style }) {
  const top = nomEn || nomLocal || ''
  const bottom = nomEn && nomLocal && nomLocal !== nomEn ? nomLocal : ''
  return (
    <td style={style}>
      <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', whiteSpace: 'normal' }}>{top || '—'}</div>
      {bottom && (
        <div style={{ fontSize: 'var(--fs-caption)', fontStyle: 'italic', color: 'var(--text-muted)', whiteSpace: 'normal' }}>{bottom}</div>
      )}
    </td>
  )
}

export default function MeasureGrid({
  rows = [],
  groups = [],            // [{key, label, accent?, historyCols:[{key,label}], activeLabel, trailCols:[{key,label}]}]
  leadCols = [],          // [{key, label, width, render:(row)=>node}]  sticky després de POM/Nom (consulta: render pot ser text)
  editable = false,
  onSave,                 // (lineId, rawValue) => Promise (pot resoldre amb {lines:[{id,valor_real}]} per propagar)
  empty = null,           // node quan no hi ha files
}) {
  const { t } = useTranslation()
  const [vals, setVals] = useState({})        // buffer local lineId -> string
  const [edited, setEdited] = useState(() => new Set())  // ancoratge (editat a mà)
  const focusRef = useRef(null)

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
    return Promise.resolve(onSave(lineId, raw === '' ? null : Number(raw))).then(res => {
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
            return (
              <tr key={r.pom_id} style={{ background: rowBg }}>
                <td style={stickyTd(0, COL_POM_W, rowBg)}>
                  <span style={{ fontWeight: 500, color: 'var(--gold)' }}>
                    {r.codi}{r.is_key && <i className="ti ti-star" style={{ fontSize: 9, marginLeft: 3, color: 'var(--gold)' }} title="KEY" />}
                  </span>
                </td>
                <NomCell nomEn={r.nom_en} nomLocal={r.nom_local} style={stickyTd(COL_POM_W, COL_NOM_W, rowBg)} />
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
                        {v == null ? '—' : v}
                      </td>
                    )
                  })
                  const a = cell.active
                  out.push(
                    <ActiveCell key={`${g.key}-active`} active={a} editable={editable}
                      value={a ? (vals[a.lineId] ?? '') : ''} edited={a ? edited.has(a.lineId) : false}
                      onChange={onChange} onCommit={a ? commitFor(a.lineId) : (() => Promise.resolve())} focusRef={focusRef} />
                  )
                  for (const tcol of (g.trailCols || [])) {
                    out.push(<td key={`${g.key}-t-${tcol.key}`} style={{ padding: '5px 8px', borderBottom: '0.5px solid var(--border)', verticalAlign: 'middle' }}>{cell.trail?.[tcol.key] ?? null}</td>)
                  }
                  return out
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
