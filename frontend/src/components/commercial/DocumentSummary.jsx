// <DocumentSummary> — el resum de totals d'un document, en contenidor propi, a baix a la dreta.
// `lines` = [{ label, value, strong }] (base imposable · IVA · total; el total va `strong`).
//
// Si `showInternal`, hi afegeix un peu de COST INTERN — **només pantalla, mai al PDF**. Aquest
// peu anava sobre `--intern-bg` (#edeff0), un gris FRED que no és de la paleta de la §1. El que
// el peu ha de dir és «això és d'una altra naturalesa: no ho veurà el client», i per dir-ho no
// cal un color nou: n'hi ha prou amb la superfície neutra de la casa (`--bg-page`) i el filet
// que ja el separa. Un color fora de paleta per a una distinció que la jerarquia ja fa és
// exactament la deriva que el bloc A va anar a buscar amb el navegador.
//
// El pes 700 del total baixa a 600, que és el pes fort del sistema (§2). Sense text propi.
const MONO = 'IBM Plex Mono, monospace'

export default function DocumentSummary({ lines = [], showInternal = false, internalLabel, internalValue }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
      <div style={{
        minWidth: 280,
        borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
        borderRadius: 'var(--r-card)', background: 'var(--panel)', overflow: 'hidden',
      }}>
        <div style={{ padding: '12px 16px' }}>
          {lines.map((l, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: '3px 0' }}>
              <span style={{
                fontFamily: MONO, color: l.strong ? 'var(--text-main)' : 'var(--text-soft)',
                fontWeight: l.strong ? 600 : 400,
                fontSize: l.strong ? 'var(--fs-h3)' : 'var(--fs-body)',
              }}>{l.label}</span>
              <span style={{
                fontFamily: MONO, color: 'var(--text-main)',
                fontWeight: l.strong ? 600 : 400,
                fontSize: l.strong ? 'var(--fs-h3)' : 'var(--fs-body)',
              }}>{l.value}</span>
            </div>
          ))}
        </div>
        {showInternal && (
          <div style={{
            display: 'flex', justifyContent: 'space-between', gap: 16, padding: '8px 16px',
            background: 'var(--bg-page)',
            borderTopWidth: 1, borderTopStyle: 'solid', borderTopColor: 'var(--line)',
          }}>
            <span style={{ color: 'var(--text-soft)', fontSize: 'var(--fs-caption)', fontFamily: MONO }}>{internalLabel}</span>
            <span style={{ color: 'var(--text-soft)', fontSize: 'var(--fs-caption)', fontFamily: MONO }}>{internalValue}</span>
          </div>
        )}
      </div>
    </div>
  )
}
