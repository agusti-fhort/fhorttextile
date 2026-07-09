// <LineTable> — taula de línies del sistema comercial unificat. Columnes titulades, accions de línia
// A L'ESQUERRA (patró row-btn), cel·les editables i columna interna de COST opcional (fons gris,
// NOMÉS pantalla, mai al document/PDF). Sense text propi: labels de columna i de la franja interna
// arriben per props (i18n a la pantalla). Config de columnes declarativa.
//
// columns: [{ key, label, align='left', width, render(row), editable, value(row), onEdit(row, val), inputMode }]
// rows: [{ id, ... , internal?: { minutes, tecnic, cost } }]
// renderActions(row) → node (botons row-btn a l'esquerra). showInternal → afegeix Temps·Tècnic·Cost.
// internalLabels: { time, tecnic, cost }.
import { minutesToHhMm, tecnicShort } from './format'

const MONO = 'IBM Plex Mono, monospace'
const th = { fontSize: 'var(--fs-label)', textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--gray)', fontWeight: 600, padding: '6px 10px', borderBottom: '0.5px solid var(--border)' }
const td = { fontSize: 'var(--fs-body)', color: 'var(--text-main)', padding: '7px 10px', borderBottom: '0.5px solid var(--bg-muted)', verticalAlign: 'top' }
const internCell = { background: 'var(--intern-bg)', color: 'var(--text-muted)' }
const cellInput = {
  width: '100%', fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
  padding: '3px 6px', border: '0.5px solid var(--gray-l)', borderRadius: 5, background: 'var(--white)',
}

function cellContent(col, row) {
  if (col.editable) {
    return (
      <input value={col.value ? col.value(row) : (row[col.key] ?? '')} inputMode={col.inputMode}
        onChange={e => col.onEdit && col.onEdit(row, e.target.value)}
        style={{ ...cellInput, textAlign: col.align || 'left' }} />
    )
  }
  return col.render ? col.render(row) : (row[col.key] ?? '')
}

export default function LineTable({ columns = [], rows = [], renderActions, showInternal = false, internalLabels = {} }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: MONO }}>
        <thead>
          <tr>
            {renderActions && <th style={{ ...th, width: 1, whiteSpace: 'nowrap' }} aria-hidden="true" />}
            {columns.map(c => (
              <th key={c.key} style={{ ...th, textAlign: c.align || 'left', width: c.width }}>{c.label}</th>
            ))}
            {showInternal && (
              <>
                <th style={{ ...th, ...internCell, textAlign: 'right' }}>{internalLabels.time}</th>
                <th style={{ ...th, ...internCell }}>{internalLabels.tecnic}</th>
                <th style={{ ...th, ...internCell, textAlign: 'right' }}>{internalLabels.cost}</th>
              </>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={row.id}>
              {renderActions && (
                <td style={{ ...td, whiteSpace: 'nowrap' }}>
                  <span style={{ display: 'inline-flex', gap: 4 }}>{renderActions(row)}</span>
                </td>
              )}
              {columns.map(c => (
                <td key={c.key} style={{ ...td, textAlign: c.align || 'left' }}>{cellContent(c, row)}</td>
              ))}
              {showInternal && (
                <>
                  <td style={{ ...td, ...internCell, textAlign: 'right' }}>{minutesToHhMm(row.internal?.minutes)}</td>
                  <td style={{ ...td, ...internCell }}>{tecnicShort(row.internal?.tecnic)}</td>
                  <td style={{ ...td, ...internCell, textAlign: 'right' }}>{row.internal?.cost}</td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
