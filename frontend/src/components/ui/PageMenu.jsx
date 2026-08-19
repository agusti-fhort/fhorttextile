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
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { FORAT_CROM } from '../layout/chromeSlot'

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

// L'ARREL (`backTo === null`): la fletxa HI ÉS I ESTÀ DESHABILITADA. Ni desapareix —això
// contradiria la lletra de la §8b i, pitjor, la seva raó: «la posició del ← és fixa a tot el
// producte, i és justament el que la fa trobable sense mirar»— ni apunta a la pantalla on ja
// ets, que és una mentida que es descobreix al primer clic i que el `backTo` obligatori existeix
// per evitar. Deshabilitada diu la veritat exacta: el botó existeix, és al seu lloc de sempre, i
// des d'aquí no hi ha on pujar.
// La forma no s'inventa: §5.7 «deshabilitat, baixa el fons, no la tinta», amb l'excepció que el
// bloc B ja va haver de resoldre DINS d'aquesta mateixa barra blanca —«a la barra no hi ha fons
// que baixar; donar-li --bg-page el deixa a un pas de --sel, que allà vol dir el contrari»— i
// que va concloure que al menú mana la §1: `--text-faint` és «només deshabilitat».
function Enrere({ to, title }) {
  const navigate = useNavigate()
  const [hover, setHover] = useState(false)
  const arrel = to === null
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      disabled={arrel}
      aria-disabled={arrel || undefined}
      onClick={arrel ? undefined : () => navigate(to)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        width: 32,
        height: 32,
        flex: 'none',
        border: '1px solid var(--line)',
        borderRadius: 'var(--r-ctrl)',
        background: hover && !arrel ? 'var(--sel)' : 'var(--panel)',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: arrel ? 'not-allowed' : 'pointer',
        // 16px: la mida que la norma (§8) dona a les icones fora de botó de text; i la tinta
        // de repòs, `--text-soft`. Les DUES es declaren AL BOTÓ i la icona les hereta: si es
        // queden només a la icona, el botó computa els 16px i el negre del document i la
        // mesura hi troba un valor que ningú ha decidit (bidireccional d'A5).
        fontSize: 16,
        color: arrel ? 'var(--text-faint)' : 'var(--text-soft)',
      }}
    >
      <i className="ti ti-arrow-left" aria-hidden="true"
        style={{ fontSize: 'inherit', color: 'currentColor', lineHeight: 1 }} />
    </button>
  )
}

const Separador = () => (
  <span style={{ width: 1, height: 20, background: 'var(--line)', margin: '0 6px', flex: 'none' }} />
)

/**
 * @param {string}   backTo        destí EXPLÍCIT de la fletxa (obligatori) · `null` = ARREL
 * @param {string}   backTitle     títol/aria-label de la fletxa — ja traduït pel qui crida
 * @param {Array}    items         [{ key, label, to, active, onClick, title }] píndoles de secció
 * @param {node}     children      contingut extra a l'esquerra (desplegables, botons de menú)
 * @param {node}     rightChildren portes transversals a l'extrem dret
 */
export default function PageMenu({ backTo, backTitle, items = [], children = null, rightChildren = null }) {
  const navigate = useNavigate()
  // 🚨 EL FORAT POT EXISTIR I NO ESTAR ENGANXAT ENLLOC. `FORAT_CROM` és un node de mòdul: viu
  // des que es carrega el bundle, i qui l'enganxa al document és el Shell. Hi ha rutes FORA del
  // Shell (l'editor de fitxa tècnica, el taller de patró); si una d'elles muntés aquest
  // component, el portal aniria a un node desenganxat i **la barra no es pintaria, en silenci**
  // — el mateix mode de fallada que el `:has()` que aquesta mateixa peça va haver de treure
  // (§8b-quater(2)): quan falla, no falla res.
  // Es tanca mirant `isConnected` DESPRÉS del muntatge i no durant el render: dins del Shell,
  // el pare fa `commit` després que els fills hagin renderitzat, o sigui que al primer render
  // el forat encara no està enganxat i comprovar-ho allà pintaria la barra al mig de la pàgina
  // una passada. Així el cas normal no parpelleja i el cas anòmal degrada VISIBLEMENT.
  const [forat, setForat] = useState(FORAT_CROM)
  useEffect(() => { if (FORAT_CROM && !FORAT_CROM.isConnected) setForat(null) }, [])
  // Cap literal de cara a l'usuari en aquest fitxer: les etiquetes i el títol de la fletxa
  // arriben ja traduïts des de la pantalla, que és qui sap de què parla.
  //
  // §8b-quater · LA BARRA NO ES PINTA ON ES DECLARA. Es teletransporta al forat que el Shell
  // obre just sota la top bar, i així les dues queden enganxades com UN SOL BLOC. El motiu
  // llarg —i per què no es fa amb `position: sticky` + `:has()`, que Firefox < 121 ignora en
  // silenci— és a `components/layout/chromeSlot.js`.
  // El `<div>` de marge negatiu que cada pantalla posa al voltant d'aquest component es queda
  // BUIT i **conserva el seu marge**: és el que cancel·la el padding del `<main>` i deixa el
  // contingut exactament on era. Cap pantalla ha de canviar res.
  const barra = (
    // `data-ftt-pagemenu` es conserva com a ÀNCORA DE MESURA: els arnesos de QA (§8b-quater)
    // hi troben la barra sense dependre de cap classe interna. Ja no hi penja cap regla de CSS.
    // El fons és `--panel` OPAC i el filet inferior `--line`: la norma els demana des del §8b i
    // és el que fa que el contingut hi passi per sota sense transparentar-se.
    <div data-ftt-pagemenu="" style={{
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
        {/* 🛑 L'ARREL (part B · pantalla 1) — PROPOSTA CONJUNTA DE LES DUES SESSIONS, PENDENT
            DE LA PARAULA D'AGUS. `backTo={null}` és una declaració EXPLÍCITA («aquesta pantalla
            és arrel i no penja d'enlloc»), no un valor per defecte que es pugui colar per
            oblit: `undefined` segueix pintant la fletxa i, sense destí, falla de seguida. La
            fletxa es queda i es deshabilita; el perquè, al comentari d'`Enrere`. Si l'Agus ho
            vol d'una altra manera —arrel sense barra, o fletxa cap a algun lloc—, és una línia. */}
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
  // Sense forat (proves unitàries, o un `PageMenu` muntat fora del Shell) es pinta al seu lloc:
  // val més una barra al mig de la pàgina que cap barra.
  return forat ? createPortal(barra, forat) : barra
}
