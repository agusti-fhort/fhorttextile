// <DocumentHeader> — capçalera de fitxa del sistema comercial unificat. Igual a les 4 pantalles
// (Oferta, Comanda, Encàrrec, Albarà). Sense text propi: tot arriba per props/slots (i18n a la
// pantalla que l'aplica). `reference` = títol (p.ex. document_number); `statusBadge` = node del
// badge d'estat; `customer` = nom del client; `actions` = slot de botons (PdfButton, secundaris,
// primari) alineats a la dreta segons el sistema de la casa.
const MONO = 'IBM Plex Mono, monospace'

export default function DocumentHeader({ reference, statusBadge, customer, actions }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6, flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, fontFamily: MONO, margin: 0 }}>{reference}</h1>
        {statusBadge}
        {actions && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            {actions}
          </div>
        )}
      </div>
      {customer && (
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: 0 }}>{customer}</p>
      )}
    </div>
  )
}
