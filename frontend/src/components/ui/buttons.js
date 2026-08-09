// Estils de botó/input compartits (tokens CSS) — patró estàndard de la fase.
// selS = input/botó secundari neutre · primaryBtn = acció primària daurada.
const MONO = 'IBM Plex Mono, monospace'

// EL CONTROL DE LA CASA (§8c: «filtres en línia — cerca, selects, dates: vora --line, radi 6,
// focus daurat, alçada única, MAI blaus»). Es conforma AQUÍ i no pantalla per pantalla perquè
// són **126 usos en 24 fitxers**: la vora era `0.5px solid var(--gray-l)`, i `--gray-l` (#f0f0f0)
// és un àlies de FARCIMENT fent de vora, en gris fred, mentre la vora de la norma és `--line`.
// Mig píxel, a més, no és de cap escala: el navegador l'arrodoneix i el resultat depèn del zoom.
//
// ⚠️ TOCA PANTALLES JA CONFORMADES (`/cataleg-peces`, `/garment-types`, l'`ActionsMenu` del
// model). Va cap a la norma a totes, que és el mateix criteri amb què el bloc A va canviar
// `GroupPills` i el bloc B `ui/Badge` per a tot el producte; i per això la bidireccional es
// torna a córrer SENCERA sobre tot el que ja estava tancat. L'alçada NO s'hi fixa a posta:
// hi ha usos que ajusten el `padding` per encabir-lo dins d'una cel·la de taula, i una alçada
// única aquí els trencaria en silenci.
export const selS = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 10px',
  border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)',
  background: 'var(--panel)', color: 'var(--text-main)',
}

// L'ACCIÓ PRIMÀRIA ÉS BLAVA (NORMA_LAYOUT §5, T0-bis.2). «Blau = el que has vingut a fer, UNA per
// pantalla; vora daurada = accions i portes de la casa; gold = marca/selecció/base.» El daurat
// deixa de ser acció perquè feia dues feines alhora: marcar la casa i cridar l'acció, i quan un
// color diu dues coses no en diu cap.
//
// Substitueix la solució de S37, que era la bona MENTRE la primària fos daurada: aleshores el
// problema era el contrast (blanc sobre daurat = 3.44:1, per sota d'AA) i es va resoldre canviant
// la TINTA a `--text-main` (4.91:1) sense tocar la marca. Ara no canvia la tinta sinó el ROL: el
// fons ja no és de marca, i sobre `--accio` el blanc dóna 5.61:1 — AA amb marge.
//
// Es reescriu D'UN COP i no pantalla per pantalla (ordre d'Agus): 66 usos en 28 fitxers. L'efecte
// conegut i acceptat és que algunes pantalles ensenyaran més d'un blau alhora fins que passin la
// seva conformitat; van llistades al report de T0-bis, no s'arreglen aquí.
export const primaryBtn = {
  display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto', background: 'var(--accio)', color: 'var(--white)',
  border: 'none', borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', fontWeight: 600, cursor: 'pointer', fontFamily: MONO,
}

// ── LA FAMÍLIA SENCERA DE LA §5 (coda del bloc B) ─────────────────────────────────────────
//
// `primaryBtn` (a dalt) porta `marginLeft: 'auto'` cuit a dins i el consumeixen 28 fitxers: no
// es toca. El que faltava era LA RESTA de la família, i mentre no hi fos cada superfície se
// l'inventava — `btn('gold')` a `CheckMeasureEditor`, un altre `btn('gold')` a `SessionActions`,
// `btnPrimary`/`btnSecondary` a `EditableTable`—, i totes tres deien que l'acció primària era
// DAURADA, que és la llei anterior a la §5. Tres còpies de la mateixa decisió és com la
// pantalla d'edició de mesures va acabar amb tres botons daurats i cap blau.
//
// LES SIS FORMES, i què vol dir cadascuna:
//   PRIMÀRIA    `--accio` ple + tinta blanca. «El que has vingut a fer», UNA per pantalla i
//               estat. Si n'hi ha dues, una de les dues no ho és.
//   SECUNDÀRIA  blanc + vora `--gold-border`. Accions de la casa que no completen la feina.
//   PORTA       IDÈNTICA a la secundària (§5.3): anar a un altre lloc no compromet res, i per
//               això no pot cridar més que l'acció que sí que compromet. Té nom propi perquè
//               el motiu és un altre, no perquè es pinti diferent.
//   TERCIÀRIA   text sol, hover `--sel`. Cancel·lar, descartar canvis, tancar.
//   DESTRUCTIVA vora i tinta `--err`, **MAI plena en repòs** (§5.5).
//   DESTRUCTIVA PLENA  `--err` ple: NOMÉS al botó de confirmació d'un modal, mai a la pantalla.
//
// La vora es declara amb longhands a posta: una shorthand `border` posada després de la seva
// pròpia longhand la reescriu sencera, i és exactament el defecte que el bloc A va haver de
// caçar amb el navegador (línies negres de 3px on hi havia d'haver un filet d'1px).
const botoBase = {
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6,
  fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 500, lineHeight: '16px',
  borderRadius: 'var(--r-ctrl)', padding: '8px 16px',
  borderWidth: 1, borderStyle: 'solid', cursor: 'pointer',
}

export const botoPri = { ...botoBase, background: 'var(--accio)', borderColor: 'var(--accio)', color: 'var(--white)', fontWeight: 600 }
export const botoSec = { ...botoBase, background: 'var(--panel)', borderColor: 'var(--gold-border)', color: 'var(--text-main)' }
export const botoPorta = botoSec
export const botoTer = { ...botoBase, background: 'none', borderColor: 'transparent', color: 'var(--text-soft)' }
export const botoDestructiu = { ...botoBase, background: 'var(--panel)', borderColor: 'var(--err)', color: 'var(--err)' }
export const botoDestructiuPle = { ...botoBase, background: 'var(--err)', borderColor: 'var(--err)', color: 'var(--white)', fontWeight: 600 }

/** §5.7 · DESHABILITAT: **baixa el fons, no la tinta**. L'`opacity` que hi havia escampada
 *  apagava també el text i el deixava per sota d'AA — un botó que no es pot prémer ha de seguir
 *  sent llegible, perquè el que diu és justament el que no es pot fer ara. */
export const apagat = {
  background: 'var(--bg-page)', borderColor: 'var(--line)', color: 'var(--text-faint)',
  cursor: 'not-allowed',
}

/** Ajuda per als llocs que ja tenien `btn(variant, disabled)`: retorna l'estil sencer. */
export const boto = (variant = 'sec', disabled = false) => ({
  ...(variant === 'pri' ? botoPri
    : variant === 'ter' ? botoTer
      : variant === 'err' ? botoDestructiu
        : variant === 'err-ple' ? botoDestructiuPle
          : botoSec),
  ...(disabled ? apagat : null),
})
