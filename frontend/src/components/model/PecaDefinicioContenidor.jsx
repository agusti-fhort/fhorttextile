// UN CONTENIDOR PER PRENDA A LA DEFINICIÓ DEL MODEL — SET-2/T7-B1.
//
// El Resum tenia UN contenidor «Definició del model» amb tres subespais a dins. Des que un
// model pot tenir més d'una prenda, aquell contenidor no és del MODEL: és de la PEÇA. El que
// abans era una targeta passa a ser-ne N, apilades, i la mare —que no té fila a la base de
// dades (D3)— hi és la primera, sintètica, servida pel mateix endpoint que les altres.
//
// ── EL FRONT NO RESOL HERÈNCIES ───────────────────────────────────────────────────────────
// Cada camp arriba com `{valor, etiqueta, heretat}` amb el valor JA EFECTIU. Aquí NO hi ha cap
// `peca.X || model.X`: aquella frase és codi una sola vegada, a `services_garment.valor_efectiu`
// (v. el revert de `7cc133b5`). El que aquest component decideix és com es LLEGEIX el que ja ve
// resolt, i la decisió viu a `utils/pecaDefinicio`, que té banc.
//
// ── I EL BUIT ÉS INFORMACIÓ ───────────────────────────────────────────────────────────────
// Una peça que hereta, o que no té joc de graduació, ho ha de DIR. La fila no s'amaga mai:
// amagar-la faria que «no en té» i «no ho hem carregat» s'assemblessin, que és el defecte que
// la llei del vocabulari (F22) ja va tancar en una altra superfície.
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ORIGEN, anclaDeLaPeca, nomDeLaPeca, presentacioCamp } from '../../utils/pecaDefinicio'
import useToc, { anellFocus } from '../ui/toc'

const MONO = 'IBM Plex Mono, monospace'

/** El check d'estat de la capçalera: el mateix llenguatge que el numeral del subespai (§6). */
function Check({ fet }) {
  return (
    <span style={{
      width: 20, height: 20, borderRadius: '50%', flex: 'none',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      borderWidth: 1, borderStyle: 'solid',
      borderColor: fet ? 'var(--ok)' : 'var(--text-soft)',
      background: fet ? 'var(--ok)' : 'transparent',
      color: fet ? 'var(--white)' : 'var(--text-soft)',
      fontSize: 11, lineHeight: '11px',
    }}>
      {fet ? <i className="ti ti-check" /> : null}
    </span>
  )
}

/**
 * Un botó-icona de la capçalera de la targeta (llapis, paperera).
 *
 * `onClick` absent = INERT a posta, i es nota (cursor per defecte, sense hover daurat): un botó
 * que sembla viu i no fa res menteix més que un que es veu apagat. Des de SET-2/T7-B3 el llapis
 * ÉS viu a totes les targetes —la porta d'escriptura existeix—, però la propietat es queda:
 * la paperera segueix sense arribar a la mare, que no té fila (D3).
 */
function BotoIcona({ onClick, titol, icona, perill = false }) {
  const [toc, gestos] = useToc()
  const viu = typeof onClick === 'function'
  return (
    <button type="button" onClick={onClick} disabled={!viu} title={titol} aria-label={titol}
      {...gestos}
      style={{
        width: 26, height: 26, flex: 'none', display: 'inline-flex',
        alignItems: 'center', justifyContent: 'center',
        borderRadius: 'var(--r-ctrl)', borderWidth: 1, borderStyle: 'solid',
        borderColor: viu && toc.hover ? (perill ? 'var(--err)' : 'var(--gold)') : 'var(--line)',
        background: 'var(--panel)',
        color: !viu ? 'var(--text-faint)' : (perill && toc.hover ? 'var(--err)' : 'var(--text-soft)'),
        cursor: viu ? 'pointer' : 'default', outline: 'none', padding: 0,
        ...(toc.focus ? anellFocus : null),
      }}>
      <i className={`ti ti-${icona}`} style={{ fontSize: 14 }} />
    </button>
  )
}

/**
 * El bateig, editat AL MATEIX LLOC on després es llegeix (§8f), no en un modal.
 *
 * Enter desa i Escape cancel·la, perquè un camp d'una sola línia que obliga a buscar el botó és
 * un camp que fa perdre temps. El desat el fa qui ens ha donat `onDesar`: aquí no se sap si
 * darrere hi ha el PATCH d'una peça o el del model —la mare no té fila i es bateja pel seu
 * `nom_prenda`— i és exactament el que aquest component no ha de saber.
 */
function BateigNom({ valorInicial, onDesar, onCancel }) {
  const { t } = useTranslation()
  const [text, setText] = useState(valorInicial || '')
  const [desant, setDesant] = useState(false)
  const ref = useRef(null)

  useEffect(() => { ref.current?.focus(); ref.current?.select() }, [])

  const desa = async () => {
    if (desant) return
    setDesant(true)
    const ok = await onDesar(text.trim())
    setDesant(false)
    if (ok) onCancel()
  }

  return (
    <>
      <input ref={ref} value={text} disabled={desant}
        onChange={e => setText(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter') { e.preventDefault(); desa() }
          if (e.key === 'Escape') { e.preventDefault(); onCancel() }
        }}
        style={{
          flex: 1, minWidth: 0, fontFamily: MONO, fontSize: 13, fontWeight: 600,
          borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--gold-border)',
          borderRadius: 'var(--r-ctrl)', padding: '4px 8px',
          background: 'var(--panel)', color: 'var(--text-main)',
        }} />
      <span style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
        <BotoIcona onClick={desant ? undefined : desa} titol={t('model_wizard.save')} icona="check" />
        <BotoIcona onClick={desant ? undefined : onCancel} titol={t('model_wizard.cancel')} icona="x" />
      </span>
    </>
  )
}

/**
 * Una fila compacta de la definició: rètol, contingut i la seva pròpia acció.
 *
 * `heretat` no és un estil: és el que separa «hereta S·M·L» de «declara S·M·L», que pinten el
 * mateix text. Quan és cert, la fila ho escriu i abaixa la tinta del valor — el valor segueix
 * sent el que governa, però la seva autoria és d'un altre lloc.
 */
export function FilaDefinicio({ etiqueta, origen = ORIGEN.PROPI, accio, children }) {
  const { t } = useTranslation()
  // Tres origens, tres lectures, i «del model» NO és una variant d'«hereta»: la primera parla
  // d'un override que existeix i ara és NULL, la segona d'un camp que la peça no té i no tindrà.
  // Pintar-les igual prometria una porta d'edició que no ha d'arribar mai.
  const heretat = origen === ORIGEN.HERETAT
  const delModel = origen === ORIGEN.DEL_MODEL
  const apagat = heretat || delModel
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'start',
      padding: '9px 16px',
      borderTopWidth: 1, borderTopStyle: 'solid', borderTopColor: 'var(--line-soft)',
    }}>
      <div style={{ minWidth: 0 }}>
        <span style={{
          fontSize: 'var(--fs-label)', lineHeight: '12px', letterSpacing: '.05em',
          textTransform: 'uppercase', color: 'var(--text-soft)',
        }}>{etiqueta}</span>
        {heretat && (
          <span style={{ marginLeft: 8, fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>
            {t('resum_wizard.inherits')}
          </span>
        )}
        <div style={{ marginTop: 4, color: apagat ? 'var(--text-soft)' : 'var(--text-main)' }}>
          {/* El prefix va DINS de la línia del valor, no al rètol: qualifica el que es llegeix
              a continuació, no el nom de l'apartat. */}
          {delModel && (
            <span style={{ color: 'var(--text-soft)' }}>{t('resum_wizard.from_model')} · </span>
          )}
          {children}
        </div>
      </div>
      {accio}
    </div>
  )
}

/** El «Canviar» d'una fila: secundari i petit — el blau és d'un pas obert de sol (§8f). */
export function BotoCanviar({ onClick, disabled, children }) {
  const [toc, gestos] = useToc()
  return (
    <button type="button" onClick={onClick} disabled={disabled} {...gestos}
      style={{
        fontFamily: MONO, fontSize: 11, lineHeight: '14px', fontWeight: 500,
        padding: '4px 10px', borderRadius: 'var(--r-ctrl)',
        borderWidth: 1, borderStyle: 'solid',
        borderColor: disabled ? 'var(--line)' : 'var(--gold-border)',
        background: disabled ? 'var(--bg-page)' : (toc.hover ? 'var(--sel)' : 'var(--panel)'),
        color: disabled ? 'var(--text-faint)' : 'var(--text-main)',
        cursor: disabled ? 'not-allowed' : 'pointer', outline: 'none', whiteSpace: 'nowrap',
        ...(toc.focus ? anellFocus : null),
      }}>
      {children}
    </button>
  )
}

/** El valor d'un camp resolt, amb el seu buit escrit. */
export function ValorCamp({ camp, buit }) {
  const p = presentacioCamp(camp)
  if (p.buit && !p.text) return <span style={{ color: 'var(--text-faint)', fontStyle: 'italic' }}>{buit}</span>
  return <b style={{ fontWeight: 600 }}>{p.text}</b>
}

/**
 * El contenidor d'una prenda. La mare i les peces es pinten amb el MATEIX component: si la mare
 * tingués el seu, el dia que canviï una regla d'aquestes n'hi hauria dues per actualitzar.
 */
export default function PecaDefinicioContenidor({ peca, fet, onDesarNom, onEsborrar, children }) {
  const { t } = useTranslation()
  const [batejant, setBatejant] = useState(false)
  const nom = nomDeLaPeca(peca, t('resum_wizard.model_base'))
  // El que hi ha al camp en obrir NO és el rètol: la mare es diu «Model base» quan no té
  // `nom_prenda`, i portar aquell text a l'input el desaria com si fos un bateig de debò. El
  // contracte ja serveix el valor cru a `nom` per a totes dues (el `nom_prenda` per a la mare).
  const nomCru = peca?.nom || ''
  return (
    <section id={anclaDeLaPeca(peca)} style={{
      background: 'var(--panel)', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
      borderRadius: 'var(--r-card)', overflow: 'hidden',
      fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
      scrollMarginTop: 16,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px' }}>
        <Check fet={fet} />
        {batejant ? (
          <BateigNom valorInicial={nomCru} onDesar={onDesarNom}
            onCancel={() => setBatejant(false)} />
        ) : (
          <>
            <span style={{ fontSize: 13, fontWeight: 600, lineHeight: '18px' }}>{nom}</span>
            {/* El CODI, al costat del nom i en to menor: dues peces batejades igual per error
                deixarien la targeta sense manera de distingir-les, i el codi és el que les
                taules de mesura porten. La mare no en té: el seu és `''` (D3). */}
            {peca?.codi
              ? <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>{peca.codi}</span>
              : null}
            <span style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
              <BotoIcona onClick={onDesarNom ? () => setBatejant(true) : undefined}
                titol={t('resum_wizard.rename_piece')} icona="pencil" />
              {/* SECUNDÀRIA I MAI PRIMÀRIA (T7-B3): esborrar una prenda no és el que s'ha vingut
                  a fer aquí. La mare no la porta —no té fila— i el 409 de mesures el mostra qui
                  la crida, tal com el servidor el redacta. */}
              {onEsborrar
                ? <BotoIcona onClick={onEsborrar} titol={t('resum_wizard.delete_piece')}
                    icona="trash" perill />
                : null}
            </span>
          </>
        )}
      </div>
      {children}
    </section>
  )
}
