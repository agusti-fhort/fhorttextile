import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { pieceFittingLines } from '../api/endpoints'
import { thStyle, SaveStatus, useDebouncedSave } from './fittingShared'

const COL_POM_W = 78
const COL_NOM_W = 150
const COL_REG_W = 118   // PG-4b-3c — columna de règim (select LINEAR/STEP + etiqueta de regla)

// Estil base d'una cel·la de valor. baseSize = columna d'una talla base (fons daurat).
// groupStart = primera columna del grup d'una talla (filet esquerre). groupEnd = última.
const cellTd = (baseSize, groupStart, groupEnd) => ({
  padding: '5px 8px', borderBottom: '0.5px solid var(--border)', verticalAlign: 'middle',
  textAlign: 'right', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums',
  background: baseSize ? 'var(--gold-pale)' : undefined,
  borderLeft: groupStart && baseSize ? '1px solid var(--gold)' : '0.5px solid var(--border)',
  borderRight: groupEnd && baseSize ? '1px solid var(--gold)' : undefined,
})

// Valor d'una versió (read-only). isBase = columna Base (v1) → text atenuat.
function VersionCell({ value, isBase, baseSize, groupStart }) {
  return (
    <td style={{ ...cellTd(baseSize, groupStart, false), color: isBase ? 'var(--text-muted)' : 'var(--text-main)' }}>
      {value == null ? '—' : value}
    </td>
  )
}

// Càlcul compartit: la cel·la és "modificada" (vermell) si el seu valor difereix de la Base.
// Mateixa condició a Editable i ReadOnly perquè el color coincideixi exactament en les dues vistes.
const isModified = (value, baseValue) => value !== '' && value != null && baseValue != null
  && Number(value) !== Number(baseValue)

// Fit actual (valor_real) EDITABLE: única cel·la amb input. Vermell+negreta si difereix de Base.
// Stepper natiu (fletxes); amplada suficient per "104,75" + fletxes. Sense nota per cel·la
// (el comentari és global del fitting, viu a Observacions).
// Els hooks d'autosave viuen NOMÉS aquí → en lectura no es munten (es renderitza ReadOnlyCell).
function EditableCell({ line, row, sizeLabel, baseSize, baseValue, value, edited, onValue, onAnchor, onPropagated, persistCell, focusRef }) {
  // Persist: mode SESSIÓ (per defecte) escriu PieceFittingLine; mode MODEL (persistCell injectat)
  // escriu l'override del model i re-propaga al servidor. Sense persistCell el comportament és
  // idèntic al de sessió (FittingDetail intacte, byte-compatible).
  const lineId = line?.id
  const isStep = (row?.logica ?? line?.logica) === 'STEP'
  const persist = useCallback((raw) => {
    const v = raw === '' ? null : Number(raw)
    if (persistCell) return persistCell({ row, sizeLabel, line, raw })
    if (isStep) return pieceFittingLines.update(lineId, { valor_real: v })
    return pieceFittingLines.propagar(lineId, v).then(res => {
      onPropagated(res.data?.linies || [])
      return res
    })
  }, [lineId, isStep, onPropagated, persistCell, row, sizeLabel, line])
  const [realState, saveReal] = useDebouncedSave(persist)

  const modified = isModified(value, baseValue)

  return (
    <td style={{ ...cellTd(baseSize, false, baseSize), position: 'relative' }}>
      <input
        type="number" step="0.1" value={value}
        onFocus={() => { focusRef.current = line.id }}
        onBlur={() => { if (focusRef.current === line.id) focusRef.current = null }}
        onChange={e => { onValue(line.id, e.target.value); onAnchor(line.id); saveReal(e.target.value) }}
        style={{
          font: 'inherit', width: 88, padding: '2px 4px', textAlign: 'right',
          border: '1px solid var(--border)', borderRadius: 4, background: 'var(--white)',
          color: modified ? 'var(--err)' : 'var(--text-main)',
          // Ancoratge editat a mà → negreta; germana modificada però propagada → vermell normal.
          fontWeight: modified && edited ? 700 : 400,
          fontVariantNumeric: 'tabular-nums', boxSizing: 'border-box',
        }}
      />
      <SaveStatus state={realState} absolute />
    </td>
  )
}

// Fit actual en LECTURA: text pla, mateix color 'modified' que EditableCell, SENSE negreta
// d'ancoratge i SENSE cap hook d'autosave (no hereta res de l'edició).
function ReadOnlyCell({ baseSize, baseValue, value }) {
  const modified = isModified(value, baseValue)
  return (
    <td style={{
      ...cellTd(baseSize, false, baseSize),
      color: modified ? 'var(--err)' : 'var(--text-main)', fontWeight: 400,
    }}>
      {value === '' || value == null ? '—' : value}
    </td>
  )
}

// Selector prim de cel·la de fit actual: buida si no hi ha línia; lectura o edició segons readOnly.
// Com que la tria es fa aquí, els hooks d'EditableCell només es munten en mode edició.
function CurrentFitCell({ readOnly, line, row, sizeLabel, baseSize, baseValue, value, edited, onValue, onAnchor, onPropagated, persistCell, focusRef }) {
  if (!line) return <td style={cellTd(baseSize, false, baseSize)} />
  return readOnly
    ? <ReadOnlyCell baseSize={baseSize} baseValue={baseValue} value={value} />
    : <EditableCell line={line} row={row} sizeLabel={sizeLabel} baseSize={baseSize} baseValue={baseValue} value={value} edited={edited}
        onValue={onValue} onAnchor={onAnchor} onPropagated={onPropagated} persistCell={persistCell} focusRef={focusRef} />
}

// Graella matricial editable d'un fitting (files = POM, columnes = talles × versions + fit actual).
// Tota la lògica d'estat (reals, ancoratge, propagació, règim) viu al pare i arriba per props.
export default function MeasureTable({
  pomRows, sizeLabels, baseLabel, versionNumbers,
  reals, editedIds, focusedIdRef = null, readOnly = false,
  onValue, onAnchor, onPropagated, onRegimChange,
  // Mode MODEL (opcionals): persistCell injecta l'escriptura per talla (override + re-propaga);
  // cellReadOnly(row, size) força lectura en cel·les concretes (p.ex. la talla base). Sense
  // aquests props el component es comporta exactament com en mode sessió.
  persistCell = null, cellReadOnly = null,
}) {
  const { t } = useTranslation()

  // Etiqueta de regla compacta (delta·break) per a la capçalera de fila POM.
  // LINEAR amb break: "+2 · break XXL +2.5" · LINEAR uniforme: "+2" · STEP: "lliure" · sense regla: res.
  const regleLabel = (row) => {
    if (row.logica == null) return ''
    if (row.logica === 'STEP') return t('fitting.grid.rule_free')
    if (row.increment_base == null) return ''
    if (row.increment_break != null && row.talla_break_label)
      return `+${row.increment_base} · ${t('fitting.grid.break')} ${row.talla_break_label} +${row.increment_break}`
    return `+${row.increment_base}`
  }

  // El primer (v1) és Base; els següents (v2..vM) són Fit 1..Fit (M-1). Etiqueta Fit N amb N = version_number - 1.
  const versionLabel = (vn, idx) =>
    idx === 0 ? t('fitting.grid.base') : t('fitting.grid.fit', { n: vn - 1 })
  const groupSpan = versionNumbers.length + 1  // versions read-only + fit actual

  const stickyHd = (left, w) => ({
    ...thStyle, position: 'sticky', left, zIndex: 3, minWidth: w, width: w,
    background: 'var(--bg-muted)', textAlign: 'left',
  })
  const stickyTd = (left, w, bg) => ({
    position: 'sticky', left, zIndex: 1, minWidth: w, width: w, background: bg,
    padding: '5px 10px', borderBottom: '0.5px solid var(--border)', verticalAlign: 'middle', whiteSpace: 'nowrap',
  })

  return (
    <table style={{ borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
      <thead>
        {/* Pis 1: talla (colspan = versions + fit actual) */}
        <tr>
          <th rowSpan={2} style={stickyHd(0, COL_POM_W)}>{t('fitting.grid.pom')}</th>
          <th rowSpan={2} style={stickyHd(COL_POM_W, COL_NOM_W)}>{t('fitting.grid.name')}</th>
          <th rowSpan={2} style={stickyHd(COL_POM_W + COL_NOM_W, COL_REG_W)}>{t('fitting.grid.regime')}</th>
          {sizeLabels.map(s => {
            const base = s === baseLabel
            return (
              <th key={s} colSpan={groupSpan} style={{
                ...thStyle, textAlign: 'center',
                background: base ? 'var(--gold-pale)' : 'var(--bg-muted)',
                borderLeft: base ? '1px solid var(--gold)' : '0.5px solid var(--border)',
                borderRight: base ? '1px solid var(--gold)' : undefined,
              }}>
                {s}{base && <i className="ti ti-star-filled" style={{ fontSize: 10, marginLeft: 4, color: 'var(--gold)' }} />}
              </th>
            )
          })}
        </tr>
        {/* Pis 2: Base · Fit1..Fit(M-1) · Fit actual */}
        <tr>
          {sizeLabels.flatMap(s => {
            const base = s === baseLabel
            const sub = (groupStart, groupEnd) => ({
              ...thStyle, textAlign: 'right', fontSize: 'var(--fs-caption)', padding: '3px 8px',
              background: base ? 'var(--gold-pale)' : 'var(--bg-muted)',
              borderLeft: groupStart && base ? '1px solid var(--gold)' : '0.5px solid var(--border)',
              borderRight: groupEnd && base ? '1px solid var(--gold)' : undefined,
            })
            const cols = versionNumbers.map((vn, idx) => (
              <th key={`${s}-v${vn}`} style={sub(idx === 0, false)}>{versionLabel(vn, idx)}</th>
            ))
            cols.push(
              <th key={`${s}-cur`} style={sub(false, true)}>{t('fitting.grid.fit_current')}</th>
            )
            return cols
          })}
        </tr>
      </thead>
      <tbody>
        {pomRows.map((row, i) => {
          const rowBg = i % 2 === 0 ? 'var(--white)' : 'var(--bg-card)'
          return (
            <tr key={row.pom_id} style={{ background: rowBg }}>
              <td style={stickyTd(0, COL_POM_W, rowBg)}>
                <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--gold)' }}>
                  {row.codi}{row.is_key && <i className="ti ti-star-filled" style={{ fontSize: 9, marginLeft: 3, color: 'var(--gold)' }} title={t('fitting.key_measure')} />}
                </span>
              </td>
              <td style={{ ...stickyTd(COL_POM_W, COL_NOM_W, rowBg), fontSize: 'var(--fs-body)', color: 'var(--text-muted)', whiteSpace: 'normal' }}>{row.nom}</td>
              <td style={stickyTd(COL_POM_W + COL_NOM_W, COL_REG_W, rowBg)}>
                {/* PG-4b-3c — règim del POM: select (dalt) + etiqueta de regla (sota). En lectura, text pla.
                    LINEAR/STEP són valors de DADA (row.logica), no es tradueixen. */}
                {readOnly ? (
                  <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-main)' }}>
                    {row.logica ?? '—'}
                  </div>
                ) : (
                  <select
                    value={row.logica ?? ''}
                    onChange={e => onRegimChange(row, e.target.value)}
                    style={{
                      font: 'inherit', fontSize: 'var(--fs-label)', width: '100%', padding: '1px 2px',
                      border: '1px solid var(--border)', borderRadius: 4,
                      background: 'var(--white)', color: 'var(--text-main)', boxSizing: 'border-box',
                    }}
                  >
                    {row.logica == null && <option value="">—</option>}
                    <option value="LINEAR">LINEAR</option>
                    <option value="STEP">STEP</option>
                  </select>
                )}
                {regleLabel(row) && (
                  <div style={{ fontSize: 'var(--fs-caption)', fontWeight: 400, color: 'var(--text-muted)', whiteSpace: 'nowrap', marginTop: 1 }}>
                    {regleLabel(row)}
                  </div>
                )}
              </td>
              {sizeLabels.flatMap(s => {
                const base = s === baseLabel
                const line = row.cells[s]
                const evoMap = new Map((line?.evolucio || []).map(e => [e.version_number, e.valor_cm]))
                const baseValue = line?.evolucio?.[0]?.valor_cm ?? null
                const cells = versionNumbers.map((vn, idx) => (
                  <VersionCell key={`${s}-v${vn}`}
                    value={evoMap.has(vn) ? evoMap.get(vn) : null}
                    isBase={idx === 0} baseSize={base} groupStart={idx === 0} />
                ))
                const cellRO = readOnly || (cellReadOnly ? cellReadOnly(row, s) : false)
                cells.push(
                  <CurrentFitCell key={`${s}-cur`} readOnly={cellRO} line={line} row={row} sizeLabel={s} baseSize={base} baseValue={baseValue}
                    value={line ? reals[line.id] ?? '' : ''}
                    edited={line ? editedIds.has(line.id) : false}
                    onValue={onValue} onAnchor={onAnchor} onPropagated={onPropagated} persistCell={persistCell} focusRef={focusedIdRef} />
                )
                return cells
              })}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
