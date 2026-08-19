import { useState } from 'react'

/**
 * EL TOC D'UN CONTROL: hover i focus, amb estat de React i no amb CSS.
 *
 * Aquesta casa estila INLINE amb tokens; posar-hi classes obligaria a mantenir el CSS d'aquests
 * controls en un segon lloc. És el mateix patró —i el mateix motiu escrit— que `ui/PageMenu.jsx`.
 *
 * ⚠️ **PER QUÈ EL FOCUS ÉS `:focus-visible` I NO `:focus`, i per què això és un BUG ARREGLAT.**
 *
 * Una pastilla de capa es clicava (verda, seleccionada) i es tornava a clicar per desmarcar-la,
 * i **es quedava amb una vora fosca i gruixuda**: ni verda ni en repòs. Un QUART estat que ningú
 * no ha dissenyat. La causa no era el toggle —desmarcava bé— sinó que **el botó conserva el focus
 * després del clic**, i el que es veia era l'anell de focus (el del navegador allà on no n'hi
 * havia de propi; el nostre allà on sí).
 *
 * `:focus` és cert tant si hi has arribat amb el ratolí com amb el tabulador. `:focus-visible`
 * només ho és quan l'usuari **navega amb teclat**, que és exactament el cas en què l'anell és
 * imprescindible (AA: qui no fa servir el ratolí ha de saber on és). Amb el ratolí no cal, i
 * enganxat és un estat fantasma.
 *
 * Els controls que fan servir això han de posar `outline: 'none'` a la base: si no, l'anell del
 * navegador surt igualment i tornem a tenir el quart estat, ara per la porta de l'UA.
 *
 * @returns {[{hover: boolean, focus: boolean}, object]} l'estat i els gestos per escampar al node
 */
export default function useToc() {
  const [toc, setToc] = useState({ hover: false, focus: false })
  return [toc, {
    onMouseEnter: () => setToc(s => ({ ...s, hover: true })),
    onMouseLeave: () => setToc(s => ({ ...s, hover: false })),
    onFocus: (e) => {
      // `:focus-visible` el resol el navegador amb la seva pròpia heurística de teclat/ratolí.
      // El `try` és per als entorns de prova sense CSSOM complet, on `matches` pot llançar.
      let visible = true
      try { visible = e.currentTarget.matches(':focus-visible') } catch { visible = false }
      setToc(s => ({ ...s, focus: visible }))
    },
    onBlur: () => setToc(s => ({ ...s, focus: false })),
  }]
}

/** L'anell de focus de la casa. Només s'aplica quan el focus és de TECLAT. */
export const anellFocus = { outline: '2px solid var(--gold)', outlineOffset: 1 }
