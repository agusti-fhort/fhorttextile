// EL MENÚ DE PANTALLA de la casa (NORMA_LAYOUT §8b · evidència PROPOSTA_menu_pantalla_v3.html).
//
// És la segona franja de TOTA pantalla del producte, sota la top bar: barra BLANCA de costat a
// costat amb filet a dalt i a baix, sempre reconeixible. Dins hi van, per aquest ordre:
//
//     ←  │  píndoles de secció …                              portes transversals
//
// TRES REGLES QUE NO SÓN NEGOCIABLES i que per això viuen al component i no a cada pantalla:
//
//  1. LA FLETXA VA SEMPRE PRIMERA i el seu destí és EXPLÍCIT (`backTo`). Mai `history.back()`:
//     la norma ho prohibeix a pèl perquè el botó ha de dir on porta abans de clicar-lo, i
//     l'històric no ho pot garantir (s'hi pot arribar per enllaç, per recàrrega o per una
//     pestanya nova). `backTo` és obligatori a posta: si una pantalla no sap d'on penja, això
//     és una pregunta de navegació, no un valor per defecte que es pugui endevinar aquí.
//  2. LA BARRA NO DESAPAREIX MAI. Sense seccions queda només la fletxa — la seva posició és
//     fixa a tot el producte, i és justament el que la fa trobable sense mirar.
//  3. LES PÍNDOLES NO SÓN ACCIONS: navegar no és ni acció ni marca. Per això l'activa és
//     `--sel` + vora `--gold-border`, i mai blau (`--accio` és NOMÉS del botó primari, §5) ni
//     daurat ple. L'extrem dret porta portes en secundari petit, MAI l'acció primària.
//
// El hover va amb estat de React i no amb CSS perquè aquesta casa estila inline amb tokens;
// posar-hi classes obligaria a mantenir el CSS de la píndola en un segon lloc.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const MONO = 'IBM Plex Mono, monospace'

function Pindola({ label, active, onClick, title }) {
  const [hover, setHover] = useState(false)
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-current={active ? 'page' : undefined}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        border: '1px solid transparent',
        borderColor: active ? 'var(--gold-border)' : 'transparent',
        borderRadius: 'var(--r-pill)',
        background: active || hover ? 'var(--sel)' : 'none',
        padding: '6px 14px',
        fontFamily: MONO,
        fontSize: 'var(--fs-body)',
        lineHeight: '16px',
        color: active || hover ? 'var(--text-main)' : 'var(--text-soft)',
        fontWeight: active ? 600 : 400,
        cursor: 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </button>
  )
}

function Enrere({ to, title }) {
  const navigate = useNavigate()
  const [hover, setHover] = useState(false)
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={() => navigate(to)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        width: 32,
        height: 32,
        flex: 'none',
        border: '1px solid var(--line)',
        borderRadius: 'var(--r-ctrl)',
        background: hover ? 'var(--sel)' : 'var(--panel)',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
      }}
    >
      {/* 16px: la mida que la norma (§8) dona a les icones fora de botó de text. */}
      <i className="ti ti-arrow-left" aria-hidden="true"
        style={{ fontSize: 16, color: 'var(--text-soft)', lineHeight: 1 }} />
    </button>
  )
}

const Separador = () => (
  <span style={{ width: 1, height: 20, background: 'var(--line)', margin: '0 6px', flex: 'none' }} />
)

/**
 * @param {string}   backTo        destí EXPLÍCIT de la fletxa (obligatori)
 * @param {string}   backTitle     títol/aria-label de la fletxa — ja traduït pel qui crida
 * @param {Array}    items         [{ key, label, to, active, onClick, title }] píndoles de secció
 * @param {node}     children      contingut extra a l'esquerra (desplegables, botons de menú)
 * @param {node}     rightChildren portes transversals a l'extrem dret
 */
export default function PageMenu({ backTo, backTitle, items = [], children = null, rightChildren = null }) {
  const navigate = useNavigate()
  // Cap literal de cara a l'usuari en aquest fitxer: les etiquetes i el títol de la fletxa
  // arriben ja traduïts des de la pantalla, que és qui sap de què parla.
  return (
    <div style={{
      background: 'var(--panel)',
      borderTop: '1px solid var(--line)',
      borderBottom: '1px solid var(--line)',
    }}>
      <div style={{
        padding: '8px 20px',
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        flexWrap: 'wrap',
      }}>
        <Enrere to={backTo} title={backTitle} />
        {(items.length > 0 || children) && <Separador />}
        {items.map((it) => (
          <Pindola
            key={it.key ?? it.label}
            label={it.label}
            title={it.title}
            active={it.active}
            onClick={it.onClick ?? (it.to ? () => navigate(it.to) : undefined)}
          />
        ))}
        {children}
        {rightChildren && (
          <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
            {rightChildren}
          </span>
        )}
      </div>
    </div>
  )
}
