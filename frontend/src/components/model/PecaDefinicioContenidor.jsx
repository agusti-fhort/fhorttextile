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
 * El llapis que bateja la peça.
 *
 * `onEditar` absent = INERT a posta, i es nota (cursor per defecte, sense hover daurat): el
 * PATCH d'una peça encara no existeix, i un botó que sembla viu i no fa res menteix més que un
 * que es veu apagat. El dia que la porta aterri, arriba el gest i prou.
 */
function Llapis({ onEditar, titol }) {
  const [toc, gestos] = useToc()
  const viu = typeof onEditar === 'function'
  return (
    <button type="button" onClick={onEditar} disabled={!viu} title={titol} aria-label={titol}
      {...gestos}
      style={{
        width: 26, height: 26, flex: 'none', display: 'inline-flex',
        alignItems: 'center', justifyContent: 'center',
        borderRadius: 'var(--r-ctrl)', borderWidth: 1, borderStyle: 'solid',
        borderColor: viu && toc.hover ? 'var(--gold)' : 'var(--line)',
        background: 'var(--panel)',
        color: viu ? 'var(--text-soft)' : 'var(--text-faint)',
        cursor: viu ? 'pointer' : 'default', outline: 'none', padding: 0,
        ...(toc.focus ? anellFocus : null),
      }}>
      <i className="ti ti-pencil" style={{ fontSize: 14 }} />
    </button>
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
export default function PecaDefinicioContenidor({ peca, fet, onEditarNom, children }) {
  const { t } = useTranslation()
  const nom = nomDeLaPeca(peca, t('resum_wizard.model_base'))
  return (
    <section id={anclaDeLaPeca(peca)} style={{
      background: 'var(--panel)', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
      borderRadius: 'var(--r-card)', overflow: 'hidden',
      fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
      scrollMarginTop: 16,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px' }}>
        <Check fet={fet} />
        <span style={{ fontSize: 13, fontWeight: 600, lineHeight: '18px' }}>{nom}</span>
        <span style={{ marginLeft: 'auto' }}>
          <Llapis onEditar={onEditarNom} titol={t('resum_wizard.rename_piece')} />
        </span>
      </div>
      {children}
    </section>
  )
}
