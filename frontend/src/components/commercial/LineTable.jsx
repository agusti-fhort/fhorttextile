// <LineTable> — taula de línies del sistema comercial unificat. Columnes titulades, accions de línia
// A L'ESQUERRA (patró row-btn), cel·les editables i columna interna de COST opcional (fons gris,
// NOMÉS pantalla, mai al document/PDF). Sense text propi: labels de columna i de la franja interna
// arriben per props (i18n a la pantalla). Config de columnes declarativa.
//
// columns: [{ key, label, align='left', width, render(row), editable, value(row), onEdit(row, val), inputMode }]
// rows: [{ id, ... , internal?: { minutes, tecnic, cost } }]
// renderActions(row) → node (botons row-btn a l'esquerra). showInternal → afegeix Temps·Tècnic·Cost.
// internalLabels: { time, tecnic, cost }. rowStyle(row) → estil extra de la fila (p.ex. fade d'una
// línia amagada). renderExpansion(row) → node desplegat sota la fila (l'estat d'obertura el controla
// el pare; retorna null si tancada) per a línies expansibles (p.ex. comanda: models·tasques·%).
import { Fragment } from 'react'
import { minutesToHhMm, tecnicShort } from './format'

//
// ── LA PELL, POSADA EN NORMA (i per què cada cosa) ────────────────────────────────────────
// · `th` anava amb tracking **.05em** i tinta `--gray`. La §2 fixa la capçalera de llista a
//   **10px MAJÚSCULES tracking .08em** «a tot arreu», i l'escala de tintes de la §1b(c) hi posa
//   `--text-soft`. Que aquesta sigui una taula de LÍNIES i no una llista principal no li canvia
//   la capçalera: la capçalera és la mateixa a tota la casa.
// · Els filets anaven a **`0.5px`** amb `--border` (DEPRECAT, §1b(b)) i `--bg-muted`. Passen a
//   1px `--line` (extern) i `--line-soft` (intern), que és la parella que la casa fa servir per
//   distingir el marc de la taula de la separació entre files.
// · El **radi 5** de la cel·la editable no és cap dels tres del sistema (6 · 12 · 999): `--r-ctrl`.
// · `--intern-bg` (#edeff0) és un gris **FRED** fora de la paleta de la §1. La columna interna ha
//   de dir «això no ho veurà el client», i per dir-ho no cal un color nou: la superfície neutra
//   de la casa i el fet que sigui una columna a part ja ho diuen.
// · Les vores en **LONGHAND**: una shorthand `border` col·locada després de la seva pròpia
//   longhand la reescriu sencera, i és el defecte que el bloc A va haver de caçar amb el
//   navegador (línies negres de 3px on hi havia d'haver un filet d'1px).
const MONO = 'IBM Plex Mono, monospace'
const th = {
  fontSize: 'var(--fs-label)', lineHeight: '12px', textTransform: 'uppercase',
  letterSpacing: '.08em', color: 'var(--text-soft)', fontWeight: 600, padding: '8px 10px',
  borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line)',
}
const td = {
  fontSize: 'var(--fs-body)', color: 'var(--text-main)', padding: '7px 10px',
  borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line-soft)',
  verticalAlign: 'top',
}
const internCell = { background: 'var(--bg-page)', color: 'var(--text-soft)' }
const cellInput = {
  width: '100%', fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
  padding: '3px 6px', borderRadius: 'var(--r-ctrl)', background: 'var(--panel)',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
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

export default function LineTable({ columns = [], rows = [], renderActions, showInternal = false, internalLabels = {}, rowStyle, renderExpansion }) {
  const colCount = (renderActions ? 1 : 0) + columns.length + (showInternal ? 3 : 0)
  return (
    <div style={{ overflowX: 'auto' }}>
      {/* LA MIDA I LA TINTA ES DECLAREN AL CONTENIDOR, no només a les cel·les: sense això
          qualsevol cosa que hi entri sense mida pròpia neix als 16px del document — el mateix
          defecte que la mesura va caçar a A1/A2 i que `ui/TaulaLlista` ja declara. */}
      <table style={{
        width: '100%', borderCollapse: 'collapse',
        fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
      }}>
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
          {rows.map(row => {
            const expansion = renderExpansion ? renderExpansion(row) : null
            return (
              <Fragment key={row.id}>
                <tr style={rowStyle ? rowStyle(row) : undefined}>
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
                      <td style={{ ...td, ...internCell, textAlign: 'right' }}>{row.internal?.minutes != null ? minutesToHhMm(row.internal.minutes) : '—'}</td>
                      <td style={{ ...td, ...internCell }}>{tecnicShort(row.internal?.tecnic)}</td>
                      <td style={{ ...td, ...internCell, textAlign: 'right' }}>{row.internal?.cost ?? '—'}</td>
                    </>
                  )}
                </tr>
                {expansion && (
                  <tr>
                    <td colSpan={colCount} style={{
                      padding: 0,
                      borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line-soft)',
                    }}>{expansion}</td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
