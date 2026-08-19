import useToc, { anellFocus } from './toc'

/**
 * EL XIP COMMUTABLE DE LA CASA — **TRES ESTATS I CAP MÉS**.
 *
 *   repòs        vora `--line` fina · fons `--panel` · tinta `--text-main`
 *   seleccionat  `verd` → fons `--ok-bg`, vora i tinta `--ok`, pes 600  ← INCLUSIÓ (NORMA §1)
 *                sense `verd` → fons `--sel` + filet d'or  ← «ON SOC» (navegació)
 *   hover        fons `--sel`, i NO trepitja el seleccionat (el hover diu «es pot clicar»,
 *                no «està triat»)
 *
 * Viu aquí perquè és UN de sol: fins avui n'hi havia DUES còpies —`Xip` a `grading/JocsDeRegles`
 * i `XipCapa` a `SizeLibrary/RunsCataleg`— amb el MATEIX defecte a totes dues. Les mètriques de
 * cada superfície (mida de lletra, encoixinat) segueixen sent seves i entren per `style`; el que
 * és d'aquí és **la lògica dels estats**, que és on hi havia el fantasma.
 *
 * ⚠️ **EL QUART ESTAT FANTASMA I PER QUÈ NO ERA L'ANELL DE FOCUS** (QA Agus 09/08).
 *
 * En DESCLICAR un xip es quedava amb un filet fosc i gruixut: ni verd ni en repòs. La sospita
 * natural era l'anell de focus del navegador —el botó conserva el focus després del clic—, però
 * mesurat al servei viu l'`outline` era `none` als quatre estats: `ui/toc.js` ja hi arribava i
 * feia la seva feina. El culpable era un altre, i és de MECÀNICA D'ESTILS EN LÍNIA:
 *
 *     base:  { border: '1px solid var(--line)' }              ← SHORTHAND
 *     on:    { ...(on ? { borderColor: 'var(--ok)' } : null) } ← LONGHAND, per spread condicional
 *
 * En passar de seleccionat a repòs, la clau `borderColor` **desapareix de l'objecte**. React
 * neteja les claus que ja no hi són (`style.borderColor = ''`) i, com que el valor de la
 * shorthand `border` NO ha canviat entre els dos renders, **no la torna a escriure**: el
 * `border-color` es queda buit i CSS el resol per `currentColor` — la tinta del text. Vora fosca.
 * Un xip que mai no ha estat clicat no passa per aquí, i per això només es veia en DESCLICAR.
 *
 * La cura no és afegir-hi més capes: és **no barrejar la shorthand amb la seva longhand**. La
 * vora es calcula UN cop i entra sencera per `border`, que és una sola clau, sempre present i
 * amb valor diferent a cada estat — o sigui que React sempre la reescriu.
 *
 * L'anell de focus (`ui/toc.js`) es queda: només amb teclat, i la base porta `outline: 'none'`
 * perquè el de l'UA no entri per la seva porta.
 *
 * Props: `on` (triat) · `verd` (inclusió, v. NORMA §1) · `disabled` · `style` (les mètriques de
 * la superfície) · la resta van al `<button>`.
 */
export default function Xip({ on, verd, disabled, style, children, ...props }) {
  const [toc, gestos] = useToc()
  // UNA SOLA CLAU per a la vora: v. la capçalera. Mai `borderColor` a sobre d'aquesta shorthand.
  const vora = on ? (verd ? 'var(--ok)' : 'var(--gold-border)') : 'var(--line)'
  return (
    <button type="button" disabled={disabled} aria-pressed={on} {...gestos} {...props}
            style={{
              fontSize: 'var(--fs-body)', border: `1px solid ${vora}`,
              borderRadius: 'var(--r-pill)', padding: '4px 12px',
              background: 'var(--panel)', color: 'var(--text-main)',
              // `fontFamily`, MAI la shorthand `font`: `font: 'inherit'` és una shorthand i, com
              // que les claus duplicades de JS conserven la posició de la PRIMERA, acabava
              // aplicant-se DESPRÉS del `fontSize` d'aquest mateix objecte i li menjava la mida.
              fontFamily: 'inherit', cursor: disabled ? 'default' : 'pointer', outline: 'none',
              ...(toc.hover && !disabled && !on ? { background: 'var(--sel)' } : null),
              // Esmena Agus 08/08 (NORMA §1): «INCLÒS en la definició» = VERD (marcar és
              // confirmar); «on soc» = --sel + filet d'or. Són dues seleccions diferents.
              ...(on && verd ? { background: 'var(--ok-bg)', color: 'var(--ok)', fontWeight: 600 } : null),
              ...(on && !verd ? { background: 'var(--sel)', color: 'var(--text-main)', fontWeight: 600 } : null),
              ...(disabled && !on ? { background: 'var(--bg-page)', color: 'var(--text-faint)' } : null),
              ...(toc.focus ? anellFocus : null),
              ...style,
            }}>{children}</button>
  )
}
