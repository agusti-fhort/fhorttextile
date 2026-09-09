import { apagat, botoDestructiuPle, botoPri, botoTer } from './buttons'
import { overlayBase } from './overlay'

// Modal base genèric (patró estàndard de la fase). NO inclou lògica de domini: el cos va com a children.
// Overlay tanca al clic fora; panel atura la propagació. Footer = Cancel·lar + acció primària.
// props: { title, subtitle?, children, confirmLabel, cancelLabel, onConfirm, onCancel, confirmDisabled? }
//
// ── CONFORMITAT §5 · §8c (part B · S1) ────────────────────────────────────────────────────
// Aquest modal és el crom de MITJA part B: l'alta de client, la de proveïdor, la d'oferta i
// els dos d'Encàrrecs el munten, i cadascun n'hereta la pell. Els quatre defectes que hi
// havia (censats pel lot comercial, verificats aquí):
//
//  1. **CANCEL·LAR ANAVA AMB `selS`**, que és l'estil d'un INPUT, no d'un botó. La §5.4 li
//     dona TERCIÀRIA (text sol, hover `--sel`): cancel·lar no ha de competir amb l'acció que
//     confirma. Un camp de text fent de botó, al costat del botó de debò, és soroll.
//  2. **EL DESHABILITAT ANAVA PER `opacity: 0.5`**, i la §5.7 ho prohibeix amb el motiu escrit:
//     «baixa el fons, no la tinta». L'opacitat apaga TAMBÉ el text i el deixa per sota d'AA —
//     i el que diu un botó deshabilitat és justament el que ara no es pot fer. `apagat` de la
//     casa baixa el fons i conserva la tinta llegible.
//  3. `--gray` (3.64:1, àlies legacy) al subtítol → `--text-soft`, que és l'escala de la §1b(c).
//  4. El radi anava com a literal 12 → `--r-card`; el títol anava a `--fs-h3` (14) quan un
//     títol de modal és una SUBCAPÇALERA, `--fs-h2` 18/24 (§2); i el padding 22 no és
//     múltiple de 4 (§3) → 20.
//
// La família sencera de la §5 ja vivia a `ui/buttons.js` i aquest fitxer no en consumia cap.
const MONO = 'IBM Plex Mono, monospace'

// §5.5 — «DESTRUCTIVA: vora i tinta --err, mai plena en repòs; **el vermell ple només a la
// CONFIRMACIÓ FINAL**». Aquest Modal ÉS la confirmació final, i cablejava `botoPri` (blau) per a
// tothom: «Esborrar la tasca» i «Tancar i deduir les pendents» sortien del mateix color que
// «Desar». La família ja existia a `buttons.js` i aquest component no la podia demanar.
// `confirmVariant` per defecte a 'pri' → cap dels 29 consumidors existents canvia.
export default function Modal({ title, subtitle, children, confirmLabel, cancelLabel, onConfirm, onCancel, confirmDisabled = false, confirmVariant = 'pri', nom = null }) {
  const estilConfirma = confirmVariant === 'destructiu' ? botoDestructiuPle : botoPri
  return (
    <div onClick={onCancel} style={overlayBase({ alignItems: 'center' })}>
      {/* `nom` és NOMÉS l'àncora de mesura: un modal es munta i es desmunta amb el gest, i
          sense senyal la bidireccional mesuraria la pantalla de sota creient que mesura el
          diàleg. No pinta res i és opcional. */}
      <div onClick={e => e.stopPropagation()}
        data-ftt-screen={nom ? `modal-${nom}` : undefined}
        style={{
        background: 'var(--panel)', borderRadius: 'var(--r-card)', padding: 20,
        width: 460, maxWidth: '92vw', maxHeight: '85vh', overflowY: 'auto',
      }}>
        <h2 style={{ fontSize: 'var(--fs-h2)', lineHeight: '24px', fontWeight: 500,
          color: 'var(--text-main)', marginBottom: subtitle ? 4 : 16, fontFamily: MONO }}>{title}</h2>
        {subtitle && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginBottom: 16 }}>{subtitle}</p>}
        {children}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
          <button onClick={onCancel} style={botoTer}>{cancelLabel}</button>
          <button onClick={onConfirm} disabled={confirmDisabled}
            style={{ ...estilConfirma, ...(confirmDisabled ? apagat : null) }}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}
