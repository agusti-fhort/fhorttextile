// Botó unificat de descàrrega de PDF dels documents comercials (P7). Mateix component, mateixa
// posició (capçalera de la fitxa, dreta), icona Tabler outline file-type-pdf i color --pdf-accent
// (token semàntic = var(--grana)). L'usa Oferta i Comanda; l'albarà v2 el reutilitzarà igual.
const MONO = 'IBM Plex Mono, monospace'

export default function PdfButton({ onClick, disabled, label }) {
  return (
    <button onClick={onClick} disabled={disabled} title={label} style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      background: 'none', border: '0.5px solid var(--pdf-accent)', borderRadius: 6,
      padding: '5px 11px', cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.5 : 1,
      fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--pdf-accent)',
    }}>
      <i className="ti ti-file-type-pdf" style={{ fontSize: 15 }} aria-hidden="true" />
      {label}
    </button>
  )
}
