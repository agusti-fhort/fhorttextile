// EL CROM DE LES LLISTES DE LA CASA (NORMA_LAYOUT §8b · §8c · §8e).
//
// **PER QUÈ EXISTEIX.** `ui/TaulaLlista.jsx` va treure de la pantalla Models la GRAELLA —les
// capçaleres, l'ordenació, les amplades per contingut, l'ellipsis— perquè la §8e no descriu «la
// pantalla Models» sinó *tota* llista del producte. Però al voltant de la graella hi ha una
// segona capa que la §8e fixa igual de bé i que es va quedar DINS de `Models.jsx`: el botó amb
// estil de menú, el desplegable d'acció composta, el comptador «12/84», el camp de filtre, la
// paginació, l'estat buit i la paperera de fila.
//
// Aquest lot són ONZE pantalles. Copiar-hi aquella capa vuit vegades és exactament el pedaç que
// la llei de mètode prohibeix («no més pedaços: unificar el ja construït»), i el mode de fallada
// és conegut: nou còpies d'una decisió divergeixen sense que falli res, només es pinten diferent
// —és el que va passar amb les tres famílies de botó que la coda del bloc B va haver d'unificar.
//
// ⚠️ **ELS VALORS SÓN ELS DE `Models.jsx`, NO ELS MEUS.** Cada mida, cada token i cada padding
// d'aquest fitxer surt de la pantalla A5 ja conformada i mesurada (auditoria de computats +
// bidireccional contra `NORMA_LLISTA_canonica.html`). Això no és un component nou amb criteri
// propi: és el crom d'A5, extret perquè la pantalla dotze el trobi fet i no se l'hagi d'inventar.
// Si algun dia un valor ha de canviar, canvia AQUÍ i a `Models.jsx` alhora — o millor, `Models`
// passa a consumir això.
//
// 🔒 **CAP LITERAL DE CARA A L'USUARI.** Mateixa llei que `ui/PageMenu` i `ui/TaulaLlista`: les
// etiquetes arriben ja traduïdes de la pantalla, que és qui sap de què parla.
//
// El hover i el focus van amb estat de React (`ui/toc`) i no amb CSS perquè aquesta casa estila
// inline amb tokens; posar-hi classes obligaria a mantenir-ho en un segon lloc.
import { useState } from 'react'
import useToc, { anellFocus } from '../ui/toc'

const MONO = 'IBM Plex Mono, monospace'

// ── Estils compartits (tokens de la NORMA, cap hex) ───────────────────────────────────────

/** §8c · FILTRES EN LÍNIA: control de la casa, alçada única, MAI blaus — filtrar no és l'acció
 *  de la pantalla. La TINTA es declara: sense `color`, un `<input>` es queda amb el negre de
 *  l'agent d'usuari i la mesura hi troba un valor que ningú ha decidit (bidireccional d'A5). */
export const camp = {
  fontFamily: MONO, fontSize: 'var(--fs-body)',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
  borderRadius: 'var(--r-ctrl)', padding: '8px 12px',
  background: 'var(--panel)', color: 'var(--text-main)',
}

/** El rètol de l'entitat al costat del comptador (§8e: «el nom de l'entitat ja no és títol»). */
export const retol = {
  fontSize: 'var(--fs-label)', letterSpacing: '.08em', textTransform: 'uppercase',
  color: 'var(--text-soft)', fontWeight: 600, whiteSpace: 'nowrap',
}

/** §8c · ESTAT BUIT = frase en `--text-faint` CURSIVA, mai caixa buida muda. */
export const buit = {
  fontSize: 'var(--fs-label)', fontStyle: 'italic', color: 'var(--text-faint)', fontFamily: MONO,
}

/** §5.7 · DESHABILITAT: baixa el FONS, no la tinta. */
export const apagat = { background: 'var(--bg-page)', borderColor: 'var(--line)', cursor: 'not-allowed' }

const caixaMenu = {
  position: 'absolute', left: 0, top: 'calc(100% + 6px)', zIndex: 41, background: 'var(--panel)',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)', borderRadius: 'var(--r-ctrl)',
  boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4, minWidth: 220,
}

const itemMenu = {
  display: 'flex', alignItems: 'center', gap: 8, width: '100%', textAlign: 'left',
  background: 'none', border: 'none', padding: '8px 10px', borderRadius: 'var(--r-ctrl)',
  fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)', cursor: 'pointer',
}

// ── Peces ─────────────────────────────────────────────────────────────────────────────────

/** El separador vertical del menú de pantalla (§8b: «← · separador · píndoles · …»). */
export const SepMenu = () => (
  <span style={{ width: 1, height: 20, background: 'var(--line)', margin: '0 6px', flex: 'none' }} />
)

/**
 * §8e · UN BOTÓ AMB ESTIL DE MENÚ. «L'acció primària PUJADA AL MENÚ deixa de ser botó i deixa
 * de ser blava»: dins de la barra blanca, una acció pren la forma de píndola de la barra —el
 * blau viu al contingut, el menú té el seu llenguatge. Mateix dibuix que les píndoles de secció
 * de `ui/PageMenu`, hover inclòs.
 */
export function BotoMenu({ onClick, icona, label, actiu = false, disabled = false, ...rest }) {
  const [toc, gestos] = useToc()
  const encès = actiu || (toc.hover && !disabled)
  return (
    <button type="button" onClick={onClick} disabled={disabled} {...gestos} {...rest}
      style={{
        borderWidth: 1, borderStyle: 'solid',
        borderColor: actiu ? 'var(--gold-border)' : 'transparent',
        borderRadius: 'var(--r-pill)',
        background: encès ? 'var(--sel)' : 'none',
        padding: '6px 14px', fontFamily: MONO, fontSize: 'var(--fs-body)', lineHeight: '16px',
        // §5.7 diu «baixa el fons, no la tinta», però a la barra blanca NO HI HA fons que baixar
        // —donar-li `--bg-page` el deixaria a un pas de `--sel`, que allà vol dir el contrari
        // (píndola activa). Al menú mana la §1: `--text-faint` és «només deshabilitat».
        color: disabled ? 'var(--text-faint)' : (encès ? 'var(--text-main)' : 'var(--text-soft)'),
        fontWeight: actiu ? 600 : 400,
        cursor: disabled ? 'not-allowed' : 'pointer',
        display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
        // `outline: none` a la base + anell NOMÉS a `:focus-visible`: sense això el botó conserva
        // el focus després del clic i queda un QUART ESTAT que ningú ha dissenyat (v. `ui/toc`).
        outline: 'none',
        ...(toc.focus ? anellFocus : null),
      }}>
      {icona && <i className={`ti ${icona}`} aria-hidden="true"
        style={{ fontSize: 14, color: 'currentColor' }} />}
      {label}
    </button>
  )
}

/**
 * §1 · ACCIONS COMPOSTES: «si una acció primària té variants, UN sol botó amb desplegable — mai
 * dos botons d'acció directa a la mateixa capçalera».
 *
 * @param {Array} items [{ key, label, icona, onClick, disabled }] — ja traduïts
 */
export function MenuDesplegable({ label, icona, items = [], disabled = false, ...rest }) {
  const [open, setOpen] = useState(false)
  const oberts = items.filter(Boolean)
  return (
    <span style={{ position: 'relative' }}>
      <BotoMenu onClick={() => setOpen(o => !o)} icona={icona} actiu={open} disabled={disabled}
        aria-haspopup="menu" aria-expanded={open} label={`${label} ▾`} {...rest} />
      {open && !disabled && (
        <>
          {/* Capa de tancament: clicar fora tanca. `fixed inset:0` i no un listener global —
              el mateix patró que el desplegable «Nou model ▾» d'A5. */}
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 40 }} />
          <div role="menu" style={caixaMenu}>
            {oberts.map(it => (
              <ItemMenu key={it.key ?? it.label} {...it} onClick={() => { setOpen(false); it.onClick() }} />
            ))}
          </div>
        </>
      )}
    </span>
  )
}

function ItemMenu({ label, icona, onClick, disabled = false }) {
  const [toc, gestos] = useToc()
  return (
    <button type="button" role="menuitem" onClick={onClick} disabled={disabled} {...gestos}
      style={{
        ...itemMenu,
        background: (toc.hover && !disabled) ? 'var(--sel)' : 'none',
        color: disabled ? 'var(--text-faint)' : 'var(--text-main)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        outline: 'none',
        ...(toc.focus ? anellFocus : null),
      }}>
      {icona && <i className={`ti ${icona}`} aria-hidden="true"
        style={{ fontSize: 14, color: 'currentColor' }} />}
      {label}
    </button>
  )
}

/**
 * §8e · EL COMPTADOR ÉS SELECCIÓ, NO KPI, I ELS VALORS MANEN: «12/84» gran, amb el denominador
 * menor i suau, i el nom de l'entitat en caption al costat — ja no és títol, és element.
 *
 * `total` és el CENS SENCER i no es dedueix mai de la pàgina carregada: qui el pinta l'ha
 * d'haver demanat a part (a A5, amb `page_size=1`).
 */
export function Comptador({ valor, total, etiqueta }) {
  return (
    <>
      <span style={{
        fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 600,
        color: 'var(--text-main)', whiteSpace: 'nowrap',
      }}>
        {valor}
        <small style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, color: 'var(--text-soft)' }}>
          /{total}
        </small>
      </span>
      <span style={retol}>{etiqueta}</span>
    </>
  )
}

/** La fila d'identitat de la §8e: comptador + cerca + selects ràpids, TOTS a la mateixa línia. */
export function FilaIdentitat({ children }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '16px 0 12px', flexWrap: 'wrap',
    }}>
      {children}
    </div>
  )
}

/** §8c · L'estat buit, amb la seva caixa. La frase arriba traduïda; mai una caixa muda. */
export function EstatBuit({ children }) {
  return (
    <div style={{
      background: 'var(--panel)', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
      borderRadius: 'var(--r-card)', padding: '40px 16px', textAlign: 'center', marginBottom: 16,
    }}>
      <span style={buit}>{children}</span>
    </div>
  )
}

/**
 * §8e · LA PAPERERA DE FILA: icona destructiva de 14px, hover `--err-bg`. En repòs NO és
 * vermella plena (§5.5: la destructiva mai plena en repòs).
 *
 * UN BOTÓ QUE NOMÉS PORTA UNA ICONA DECLARA LA MIDA I LA TINTA DE LA ICONA, i la icona les
 * hereta amb `currentColor`: deixar-les heretades és com es cola un 16px del document dins d'un
 * control de 26px (és el defecte que la bidireccional d'A5 va caçar a la maqueta canònica).
 */
export function BotoEsborrar({ onClick, title, disabled = false }) {
  const [toc, gestos] = useToc()
  const encès = toc.hover && !disabled
  return (
    <button type="button" onClick={onClick} disabled={disabled} title={title} aria-label={title} {...gestos}
      style={{
        width: 26, height: 26,
        borderWidth: 1, borderStyle: 'solid', borderColor: encès ? 'var(--err)' : 'transparent',
        borderRadius: 'var(--r-ctrl)', background: encès ? 'var(--err-bg)' : 'none',
        cursor: disabled ? 'not-allowed' : 'pointer',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        color: disabled ? 'var(--text-faint)' : 'var(--err)', fontSize: 14, padding: 0,
        outline: 'none',
        ...(toc.focus ? anellFocus : null),
      }}>
      <i className="ti ti-trash" aria-hidden="true" style={{ fontSize: 'inherit', color: 'currentColor' }} />
    </button>
  )
}

/**
 * La paginació de sota la llista. Els dos botons són SECUNDARIS de la casa (§5.2) i el text del
 * mig, tinta suau. Les tres etiquetes arriben traduïdes.
 */
export function Paginacio({ page, pages, onPage, labelPrev, labelNext, info }) {
  if (pages <= 1) return null
  const btn = {
    fontFamily: MONO, fontSize: 'var(--fs-body)',
    background: 'var(--panel)', color: 'var(--text-main)',
    borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--gold-border)',
    borderRadius: 'var(--r-ctrl)', padding: '8px 16px', cursor: 'pointer',
  }
  return (
    <div style={{
      display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12,
      marginTop: 4, marginBottom: 18, fontFamily: MONO, fontSize: 'var(--fs-body)',
    }}>
      <button type="button" onClick={() => onPage(Math.max(1, page - 1))} disabled={page <= 1}
        style={{ ...btn, ...(page <= 1 ? apagat : null) }}>← {labelPrev}</button>
      <span style={{ color: 'var(--text-soft)' }}>{info}</span>
      <button type="button" onClick={() => onPage(Math.min(pages, page + 1))} disabled={page >= pages}
        style={{ ...btn, ...(page >= pages ? apagat : null) }}>{labelNext} →</button>
    </div>
  )
}

/**
 * El marge negatiu que treu el menú de pantalla dels 24px del `<main>` del Shell, perquè la
 * barra blanca vagi DE COSTAT A COSTAT (§8b.2). Va aquí i no copiat a cada pantalla perquè és
 * una propietat del bastiment, no una decisió de cap llista.
 */
export const forceBarra = { margin: '-1.5rem -1.5rem 0' }
