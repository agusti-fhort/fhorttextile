// LA GRAELLA DE LLISTA DE LA CASA (NORMA_LAYOUT §8e · evidència NORMA_LLISTA_canonica.html).
//
// La §8e no descriu «la pantalla Models»: descriu **tota** llista del producte (Models,
// Suppliers, Clients, Encàrrecs, Comercial, Fittings, jocs de regles, runs…). Per això les
// mecàniques que la norma fixa viuen AQUÍ i no dins de cada pantalla:
//
//  · capçaleres `th` a 10px MAJÚSCULES amb tracking .08em, ordenables;
//  · **icona d'ordenació SVG de 12px i traç 1.75**, mai un caràcter de text — a 10px un ▲
//    no es veu. Inactiva `--text-faint` (`--text-soft` al hover de la seva capçalera), i la
//    columna ordenada amb la fletxa en `--gold` i traç 2;
//  · **amplades PER CONTINGUT, no iguals**: cada columna porta el seu min/max;
//  · **overflow: ellipsis + `title`**. Mai salt de línia (trencaria la fila d'una línia) i mai
//    scroll per columna;
//  · fila seleccionada `--sel` + filet d'or 3px a l'esquerra.
//
// El hover va amb estat de React i no amb CSS pel mateix motiu que a `PageMenu`: aquesta casa
// estila inline amb tokens, i posar-hi classes obligaria a mantenir la taula en un segon lloc.
//
// CAP LITERAL DE CARA A L'USUARI en aquest fitxer: les etiquetes de columna arriben ja
// traduïdes de la pantalla, que és qui sap de què parla.
import { useState } from 'react'

const MONO = 'IBM Plex Mono, monospace'

/**
 * Icona d'ordenació. `estat`: 'cap' (la columna es pot ordenar i no ho està) · 'asc' · 'desc'.
 * Els tres dibuixos són els de la maqueta canònica: doble fletxa quan no mana, fletxa sola
 * quan mana. `hover` només aclareix la inactiva.
 */
export function IconaOrdre({ estat = 'cap', hover = false }) {
  const mana = estat === 'asc' || estat === 'desc'
  const d = estat === 'asc' ? 'M12 19V5M6 11l6-6 6 6'
    : estat === 'desc' ? 'M12 5v14M6 13l6 6 6-6'
      : 'M8 9l4-5 4 5M8 15l4 5 4-5'
  return (
    <span style={{ display: 'inline-block', verticalAlign: -2, marginLeft: 2 }} aria-hidden="true">
      <svg viewBox="0 0 24 24" width="12" height="12" style={{ display: 'block' }}
        fill="none" strokeLinecap="round" strokeLinejoin="round"
        stroke={mana ? 'var(--gold)' : (hover ? 'var(--text-soft)' : 'var(--text-faint)')}
        strokeWidth={mana ? 2 : 1.75}>
        <path d={d} />
      </svg>
    </span>
  )
}

// L'amplada d'una columna és SEVA (§8e). `amplada` fixa les tres mides alhora (checkbox,
// paperera); `min`/`max` són el cas normal: refs estretes, la dada reina generosa.
function ampladaDe(col) {
  if (col.amplada != null) return { width: col.amplada, minWidth: col.amplada, maxWidth: col.amplada }
  return { minWidth: col.min, maxWidth: col.max }
}

function Capcalera({ col, ordre, onOrdenar }) {
  const [hover, setHover] = useState(false)
  const ordenable = !!col.sort && !!onOrdenar
  const mana = ordenable && ordre?.camp === col.sort
  return (
    <th
      scope="col"
      title={col.titolCap}
      aria-sort={mana ? (ordre.dir === 'asc' ? 'ascending' : 'descending') : undefined}
      onClick={ordenable ? () => onOrdenar(col.sort) : undefined}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        ...ampladaDe(col),
        fontSize: 'var(--fs-label)',
        lineHeight: '12px',
        letterSpacing: '.08em',
        textTransform: 'uppercase',
        color: mana ? 'var(--text-main)' : 'var(--text-soft)',
        fontWeight: 600,
        textAlign: col.align || 'left',
        whiteSpace: 'nowrap',
        padding: '8px 10px',
        borderBottomWidth: 1,
        borderBottomStyle: 'solid',
        borderBottomColor: 'var(--line)',
        background: 'var(--panel)',
        cursor: ordenable ? 'pointer' : 'default',
        userSelect: 'none',
      }}>
      {/* La capçalera d'una columna no sempre és un rètol: a la graella canònica el `th` de la
          columna `chk` porta el CONTROL de conjunt (`<th class="c-chk"><input type="checkbox">`).
          `renderCap` deixa que la columna pinti la seva pròpia capçalera; sense ell, l'etiqueta
          de sempre. El control el dona la pantalla —aquí no hi ha ni literals ni estat de
          selecció—, i la caixa del `th` (mida, filet, fons) segueix sent la de la norma. */}
      {col.renderCap ? col.renderCap() : col.label}
      {ordenable && <IconaOrdre estat={mana ? ordre.dir : 'cap'} hover={hover} />}
    </th>
  )
}

function Fila({ cols, fila, triada, onObrir, hover, setHover }) {
  return (
    <tr
      onClick={onObrir}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{ cursor: onObrir ? 'pointer' : 'default' }}>
      {cols.map((col, i) => (
        <td
          key={col.key}
          title={col.titol ? col.titol(fila) : undefined}
          style={{
            ...ampladaDe(col),
            padding: '7px 10px',
            borderBottomWidth: 1,
            borderBottomStyle: 'solid',
            borderBottomColor: 'var(--line-soft)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            verticalAlign: 'middle',
            textAlign: col.align || 'left',
            background: triada ? 'var(--sel)' : (hover ? 'var(--bg-page)' : 'var(--panel)'),
            // El filet d'or de «on soc» va al PRIMER td: a `tr` el navegador no pinta
            // box-shadow amb `border-collapse: collapse`.
            boxShadow: (triada && i === 0) ? 'inset 3px 0 0 var(--gold)' : undefined,
            ...(col.estil || {}),
          }}>
          {col.render(fila)}
        </td>
      ))}
    </tr>
  )
}

/**
 * @param {Array}    cols     [{ key, label, min, max, amplada, align, sort, estil, render,
 *                              renderCap, titol, titolCap }] — `render(fila)` pinta la cel·la i
 *                              `renderCap()`, si hi és, la CAPÇALERA en lloc de `label`
 * @param {Array}    files    les files ja carregades (la pantalla mana la paginació)
 * @param {Function} clau     fila → id estable
 * @param {Object}   ordre    { camp, dir: 'asc'|'desc' } | null
 * @param {Function} onOrdenar(camp)
 * @param {Function} triada   fila → bool (fila seleccionada, «on soc»)
 * @param {Function} onObrir  fila → void
 */
export default function TaulaLlista({ cols, files, clau, ordre = null, onOrdenar = null,
  triada = () => false, onObrir = null }) {
  const [hoverId, setHoverId] = useState(null)
  return (
    <div style={{
      background: 'var(--panel)',
      borderWidth: 1,
      borderStyle: 'solid',
      borderColor: 'var(--line)',
      borderRadius: 'var(--r-card)',
      overflow: 'auto',
      marginBottom: 16,
      // LA MIDA ES DECLARA AL CONTENIDOR, no només a la taula. Sense això la caixa computa
      // els 16px del document —el mateix defecte que la mesura va caçar a A1/A2— i qualsevol
      // cosa que hi entri sense mida pròpia (un estat buit, un peu) neix a 16.
      fontFamily: MONO,
      fontSize: 'var(--fs-body)',
      color: 'var(--text-main)',
    }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
        <thead>
          <tr>{cols.map(col => (
            <Capcalera key={col.key} col={col} ordre={ordre} onOrdenar={onOrdenar} />
          ))}</tr>
        </thead>
        <tbody>
          {files.map(fila => {
            const id = clau(fila)
            return (
              <Fila key={id} cols={cols} fila={fila} triada={triada(fila)}
                onObrir={onObrir ? () => onObrir(fila) : null}
                hover={hoverId === id} setHover={(v) => setHoverId(v ? id : null)} />
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
