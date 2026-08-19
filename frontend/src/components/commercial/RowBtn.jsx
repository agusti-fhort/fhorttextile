// <RowBtn> — el botó d'acció d'una LÍNIA de document: icona Tabler outline, sense text, amb
// títol accessible. `icon` és la classe Tabler; `danger` el pinta en to d'error; `active` en to
// de marca (el cas de «està inclòs»).
//
// Tres coses que canvien respecte del que hi havia, i totes són de la norma:
//  · **la vora era `0.5px solid --gray-l` SEMPRE encesa**, a cada botó de cada línia. La §8e dona
//    a la paperera de fila una vora que **només apareix al hover** —en repòs el botó és la icona
//    i prou—, i amb tres o quatre botons per línia una graella de caixetes grises és soroll que
//    competeix amb la dada.
//  · **el deshabilitat anava per `opacity: 0.4`**, que la §5.7 prohibeix: apaga també la icona i
//    la deixa per sota d'AA. Baixa el fons i conserva la tinta.
//  · **`--text-muted` és DEPRECAT** (§1b(c)): la tinta d'una icona en repòs és `--text-soft` (§8).
//
// El hover i el focus van amb `ui/toc`: anell NOMÉS a `:focus-visible`, o el botó es queda amb
// el focus després del clic i apareix un quart estat que ningú ha dissenyat.
import useToc, { anellFocus } from '../ui/toc'

export default function RowBtn({ icon, title, onClick, disabled, danger, active }) {
  const [toc, gestos] = useToc()
  const tinta = danger ? 'var(--err)' : active ? 'var(--gold)' : 'var(--text-soft)'
  const encès = toc.hover && !disabled
  return (
    <button type="button" onClick={onClick} disabled={disabled} title={title} aria-label={title}
      {...gestos}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: 26, height: 26, padding: 0,
        borderWidth: 1, borderStyle: 'solid',
        borderColor: encès ? (danger ? 'var(--err)' : 'var(--gold-border)') : 'transparent',
        borderRadius: 'var(--r-ctrl)',
        background: encès ? (danger ? 'var(--err-bg)' : 'var(--sel)') : 'none',
        cursor: disabled ? 'not-allowed' : 'pointer',
        // §5.7 · deshabilitat: baixa el FONS, no la tinta.
        color: disabled ? 'var(--text-faint)' : tinta,
        // UN BOTÓ QUE NOMÉS PORTA UNA ICONA DECLARA LA SEVA MIDA I LA SEVA TINTA, i la icona les
        // hereta amb `currentColor`: si es queden només a la icona, el botó computa els 16px del
        // document i la mesura hi troba un valor que ningú ha decidit.
        fontSize: 14,
        outline: 'none',
        ...(toc.focus ? anellFocus : null),
      }}>
      <i className={`ti ${icon}`} style={{ fontSize: 'inherit', color: 'currentColor' }} aria-hidden="true" />
    </button>
  )
}
