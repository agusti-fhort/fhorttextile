// <DocumentHeader> — LA IDENTITAT d'una fitxa de document (NORMA_LAYOUT §8b.3). Igual a les
// quatre pantalles: Oferta · Comanda · Encàrrec · Albarà.
//
// §8b.3 la descriu sencera: **sobre el fons de pàgina, SENSE CONTENIDOR** (és informativa, no un
// panell), amb el codi en CAPTION a dalt, el nom a 22/500, el badge d'estat i les accions a la
// dreta. El que hi havia era un `h1` a `--fs-h2` (18) amb el número, i el nom del client com a
// `<p>` gris a sota: dues desviacions petites que, multiplicades per quatre pantalles, són el
// que fa que una fitxa de document no s'assembli a una fitxa de model.
//
// **EL NÚMERO ÉS EL QUE VA A CAPTION I EL CLIENT AL TÍTOL**, i no a l'inrevés. A la LLISTA la
// dada reina és el número (allà se cerca per número); a la FITXA ja saps quin document mires, i
// el que has de reconèixer d'un cop d'ull és DE QUI és. Mateixa lògica que la fitxa d'un article
// (el codi a caption, el nom com a h1) i que la d'un client.
//
// Sense text propi: tot arriba per props/slots — la i18n viu a la pantalla que l'aplica.
const MONO = 'IBM Plex Mono, monospace'

export default function DocumentHeader({ reference, statusBadge, customer, actions }) {
  return (
    <div style={{ padding: '16px 0 12px' }}>
      <div style={{
        fontSize: 'var(--fs-caption)', lineHeight: '12px', letterSpacing: '.08em',
        textTransform: 'uppercase', color: 'var(--text-soft)', fontFamily: MONO,
        fontWeight: 600, marginBottom: 4,
      }}>
        {reference}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <h1 style={{
          fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500,
          fontFamily: MONO, color: 'var(--text-main)', margin: 0,
        }}>
          {customer}
        </h1>
        {statusBadge}
        {actions && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            {actions}
          </div>
        )}
      </div>
    </div>
  )
}
