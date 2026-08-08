// EL BADGE D'ESTAT DE LA CASA (NORMA_LAYOUT §1, esmenes d'Agus del 08/08).
//
// La regla és d'una peça i no té excepcions: **fons suau + tinta del color + VORA FINA DEL
// MATEIX COLOR**, i sempre PÍNDOLA (radi 999, §3). Mai fons ple de color, mai badge de color
// sense filet. El que hi havia eren cinc parells fons/tinta sense cap vora, en radi 6 i a mida
// de cos: la forma que la norma descarta.
//
// TRES CANVIS QUE ARRIBEN A TOT EL PRODUCTE (21 fitxers el munten), i que van al component
// perquè és on viu la regla:
//  1. **La vora fina** hi entra a totes cinc variants.
//  2. **`gold` deixa de ser marca pintant una dada.** `--gold-pale` està ELIMINAT del sistema
//     (§1) i el daurat és marca/selecció, no semàfor. Passa a la forma «de la casa» que la
//     mateixa §1 nomena: `--sel` + filet `--gold-border` + tinta principal. Segueix sent
//     distingible del neutre pla, i ja no diu «alerta» amb el color del logo.
//  3. **`warn` es parteix segons la §1b(d).** `--warn-state` sobre `--warn-state-bg` dona
//     1.86:1 com a text —inadmissible, i contrari al vet de C5—: el fons i la vora són
//     `--warn-state`/`--warn-state-bg`, i el TEXT va en `--warn-ink` (5.32:1, AA).
//
// La mida baixa de 12 a 10 (§2: «badge 10px»), que és el sostre que el guardià mesura.
const VARIANTS = {
  ok:   { bg: 'var(--ok-bg)',        color: 'var(--ok)',        vora: 'var(--ok)' },
  warn: { bg: 'var(--warn-state-bg)', color: 'var(--warn-ink)', vora: 'var(--warn-state)' },
  err:  { bg: 'var(--err-bg)',       color: 'var(--err)',       vora: 'var(--err)' },
  // `gate` («llest per a la porta») ja era un àlies del verd d'èxit: mateix significat, mateix color.
  gate: { bg: 'var(--gate-bg)',      color: 'var(--gate)',      vora: 'var(--gate)' },
  gold: { bg: 'var(--sel)',          color: 'var(--text-main)', vora: 'var(--gold-border)' },
  gray: { bg: 'var(--sel)',          color: 'var(--text-main)', vora: 'var(--line)' },
}

export default function Badge({ variant = 'gray', icon, children, style }) {
  const v = VARIANTS[variant] || VARIANTS.gray
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      fontSize: 'var(--fs-caption)', lineHeight: '12px', letterSpacing: '.04em',
      padding: '3px 10px', borderRadius: 'var(--r-pill)',
      background: v.bg, color: v.color,
      borderWidth: 1, borderStyle: 'solid', borderColor: v.vora,
      fontWeight: 600, whiteSpace: 'nowrap',
      ...style,
    }}>
      {/* §8 · icona dins d'un badge: la mida del text que l'acompanya i SEMPRE `currentColor`. */}
      {icon && <i className={`ti ${icon}`} aria-hidden="true"
        style={{ fontSize: 'inherit', color: 'currentColor' }} />}
      {children}
    </span>
  )
}
